import logging
import asyncio
import os
import random
import json
from datetime import datetime, timedelta
import pytz
import asyncpg
import httpx

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
TIMEZONE = pytz.timezone("Europe/Belgrade")

# ─── УЧЕБНЫЙ КОНТЕНТ ───────────────────────────────────────────────

from curriculum_data import WEEKS


def lesson_id_at(week_idx: int, day_idx: int) -> str:
    if week_idx < 0 or week_idx >= len(WEEKS):
        return ""
    if day_idx < 0 or day_idx >= len(WEEKS[week_idx]["days"]):
        return ""
    return WEEKS[week_idx]["days"][day_idx]["lesson_id"]


def migrate_completed_keys(raw_keys: str) -> str:
    """Convert legacy `week_day` progress to stable lesson IDs."""
    migrated = []
    for key in (raw_keys or "").split(","):
        if not key:
            continue
        if key.startswith("M"):
            migrated.append(key)
            continue
        try:
            old_week, old_day = (int(part) for part in key.split("_", 1))
            lesson_id = lesson_id_at(old_week, min(old_day, 6))
            if lesson_id:
                migrated.append(lesson_id)
        except ValueError:
            logger.warning("Skipping invalid legacy lesson key: %s", key)
    return ",".join(dict.fromkeys(migrated))

QUIZ_TYPES = ["translate_to_en", "translate_to_ru", "choose_correct", "fill_blank"]

LEVELS = [
    (0, "Beginner 🌱"),
    (100, "Elementary 📚"),
    (300, "Pre-Intermediate 💬"),
    (600, "Intermediate 🎯"),
    (1000, "Upper-Intermediate 🚀"),
    (1500, "Advanced ⭐"),
]

# ─── БАЗА ДАННЫХ ───────────────────────────────────────────────────

async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            xp INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            last_day TEXT DEFAULT '',
            total_days INTEGER DEFAULT 0,
            current_week INTEGER DEFAULT 0,
            current_day INTEGER DEFAULT 0,
            current_lesson_id TEXT DEFAULT 'M01-W01-D01',
            opened_lesson_id TEXT DEFAULT '',
            opened_date TEXT DEFAULT '',
            quiz_state JSONB DEFAULT '{}'::jsonb,
            completed_lessons TEXT DEFAULT '',
            joined_at TIMESTAMP DEFAULT NOW()
        )
    """)
    # ─── FIX 1: автоматически добавляем колонку если не существует ─
    try:
        await conn.execute("ALTER TABLE users ADD COLUMN completed_lessons TEXT DEFAULT ''")
        logger.info("Added completed_lessons column")
    except Exception:
        pass  # Колонка уже есть — ок
    for column in (
        "current_lesson_id TEXT DEFAULT 'M01-W01-D01'",
        "opened_lesson_id TEXT DEFAULT ''",
        "opened_date TEXT DEFAULT ''",
    ):
        try:
            await conn.execute(f"ALTER TABLE users ADD COLUMN {column}")
        except Exception:
            pass
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS weekly_results (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            week_number INTEGER,
            score INTEGER,
            total INTEGER,
            completed_at TIMESTAMP DEFAULT NOW()
        )
    """)
    # Migrate legacy week/day keys without resetting anyone's position or XP.
    users = await conn.fetch(
        "SELECT user_id, current_week, current_day, current_lesson_id, completed_lessons FROM users"
    )
    for user in users:
        week_idx = max(0, min(user["current_week"] or 0, len(WEEKS) - 1))
        day_idx = max(0, min(user["current_day"] or 0, 6))
        current_id = WEEKS[week_idx]["days"][day_idx]["lesson_id"]
        completed = migrate_completed_keys(user["completed_lessons"] or "")
        await conn.execute(
            """
            UPDATE users
            SET current_lesson_id=$2, completed_lessons=$3
            WHERE user_id=$1
            """,
            user["user_id"], current_id, completed,
        )
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS dialogue_translations (
            source_text TEXT PRIMARY KEY,
            translation_ru TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    await conn.close()
    logger.info("Database initialized")

async def get_user(user_id: int):
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    await conn.close()
    return dict(row) if row else None

async def create_user(user_id: int, username: str, first_name: str):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        INSERT INTO users (user_id, username, first_name)
        VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
    """, user_id, username, first_name)
    await conn.close()

async def update_user(user_id: int, **kwargs):
    if not kwargs:
        return
    conn = await asyncpg.connect(DATABASE_URL)
    sets = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(kwargs.keys())])
    values = list(kwargs.values())
    await conn.execute(f"UPDATE users SET {sets} WHERE user_id = $1", user_id, *values)
    await conn.close()

async def get_leaderboard():
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("SELECT first_name, xp, streak, current_week FROM users ORDER BY xp DESC LIMIT 10")
    await conn.close()
    return [dict(r) for r in rows]

async def save_weekly_result(user_id: int, week: int, score: int, total: int):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute(
        "INSERT INTO weekly_results (user_id, week_number, score, total) VALUES ($1, $2, $3, $4)",
        user_id, week, score, total
    )
    await conn.close()

async def get_dialogue_translations(lines):
    """Return cached Russian translations, generating only missing lines."""
    source_lines = list(dict.fromkeys(line for _, line in lines))
    if not source_lines:
        return {}

    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch(
        """
        SELECT source_text, translation_ru
        FROM dialogue_translations
        WHERE source_text = ANY($1::text[])
        """,
        source_lines,
    )
    translations = {row["source_text"]: row["translation_ru"] for row in rows}
    missing = [line for line in source_lines if line not in translations]

    if missing:
        try:
            api_key = os.environ.get("OPENAI_API_KEY", "")
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "temperature": 0,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "Translate English business dialogue lines into "
                                    "clear, natural Russian for a beginner English "
                                    "learner. Preserve meaning and tone. Return only "
                                    'JSON: {\"translations\": [\"...\", \"...\"]}, '
                                    "in exactly the same order as the input."
                                ),
                            },
                            {
                                "role": "user",
                                "content": json.dumps(missing, ensure_ascii=False),
                            },
                        ],
                    },
                )
                response.raise_for_status()
                payload = response.json()
                generated = json.loads(
                    payload["choices"][0]["message"]["content"]
                ).get("translations", [])

            if len(generated) != len(missing):
                raise ValueError("Unexpected translation count")

            for source, translation in zip(missing, generated):
                translation = str(translation).strip()
                if not translation:
                    continue
                translations[source] = translation
                await conn.execute(
                    """
                    INSERT INTO dialogue_translations (source_text, translation_ru)
                    VALUES ($1, $2)
                    ON CONFLICT (source_text)
                    DO UPDATE SET translation_ru = EXCLUDED.translation_ru
                    """,
                    source,
                    translation,
                )
        except Exception as exc:
            logger.error(f"Dialogue translation error: {exc}")
        finally:
            await conn.close()
    else:
        await conn.close()

    return translations

async def build_dialogue_text(dialogue):
    translations = await get_dialogue_translations(dialogue)
    blocks = []
    for role, line in dialogue:
        translation = translations.get(line, "Перевод временно недоступен")
        blocks.append(f"_{role}_: {line}\n↳ {translation}")
    return "\n\n".join(blocks)

# ─── ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ──────────────────────────────────────

def today_str():
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d")

def get_level(xp):
    level = 0
    for i, (threshold, _) in enumerate(LEVELS):
        if xp >= threshold:
            level = i
    return level

def xp_bar(xp, length=10):
    max_xp = 1500
    pct = min(xp / max_xp, 1.0)
    filled = round(length * pct)
    return "▓" * filled + "░" * (length - filled)

def get_current_lesson(week_idx, day_idx):
    if week_idx < 0 or week_idx >= len(WEEKS):
        return None
    days = WEEKS[week_idx]["days"]
    if day_idx < 0 or day_idx >= len(days):
        return None
    return days[day_idx]

def get_lesson_by_position(week_idx: int, day_idx: int):
    """Return a stable lesson by its course position."""
    if week_idx < 0 or week_idx >= len(WEEKS):
        return None
    days = WEEKS[week_idx]["days"]
    if day_idx < 0 or day_idx >= len(days):
        return None
    return days[day_idx]

def resolve_lesson_day(week_idx: int, requested_day: int, lesson) -> int:
    """Resolve weekend random lessons to their real day index."""
    days = WEEKS[week_idx]["days"]
    if 0 <= requested_day < len(days) and days[requested_day] is lesson:
        return requested_day
    for index, candidate in enumerate(days):
        if candidate is lesson:
            return index
    return 0

def clean_english(raw: str) -> str:
    return raw.split(" [", 1)[0] if " [" in raw else raw

def lesson_audio_keyboard(week_idx: int, day_idx: int, lesson):
    """Create one audio callback button for every lesson item."""
    keyboard = []
    words = lesson.get("words", [])
    for index in range(0, len(words), 2):
        row = []
        for word_index in range(index, min(index + 2, len(words))):
            label = clean_english(words[word_index][0])
            if len(label) > 24:
                label = label[:21] + "…"
            row.append(InlineKeyboardButton(
                f"🔊 {label}",
                callback_data=f"audio_w_{week_idx}_{day_idx}_{word_index}"
            ))
        keyboard.append(row)

    if lesson.get("phrase"):
        keyboard.append([InlineKeyboardButton(
            "🎬 Фраза",
            callback_data=f"audio_p_{week_idx}_{day_idx}_0"
        )])

    dialogue = lesson.get("dialogue", [])
    if dialogue:
        keyboard.append([
            InlineKeyboardButton(
                f"💬 {role} {line_index + 1}",
                callback_data=f"audio_d_{week_idx}_{day_idx}_{line_index}"
            )
            for line_index, (role, _) in enumerate(dialogue)
        ])
    return keyboard

def generate_quiz(lesson, quiz_type=None):
    words = lesson["words"]
    if not quiz_type:
        quiz_type = random.choice(["translate_to_en", "translate_to_ru"])
    word_en, word_ru = random.choice(words)
    word_en_clean = word_en.split(" [")[0] if " [" in word_en else word_en
    if quiz_type == "translate_to_ru":
        question = f"Переведи на русский:\n\n🇬🇧 *{word_en_clean}*"
        correct = word_ru
        wrong_pool = [w[1] for w in words if w[1] != word_ru]
        options = [correct] + random.sample(wrong_pool, min(3, len(wrong_pool)))
        random.shuffle(options)
    else:
        question = f"Переведи на английский:\n\n🇷🇺 *{word_ru}*"
        correct = word_en_clean
        wrong_pool = [w[0].split(" [")[0] if " [" in w[0] else w[0] for w in words if w[0] != word_en]
        options = [correct] + random.sample(wrong_pool, min(3, len(wrong_pool)))
        random.shuffle(options)
    correct_short = correct[:20] if len(correct) > 20 else correct
    options_short = []
    for o in options:
        s = o[:20] if len(o) > 20 else o
        options_short.append(s)
    return {"question": question, "correct": correct_short, "options": options_short, "type": quiz_type}

def generate_quiz_session(lesson):
    """Generate a deterministic-size daily, weekly, monthly or final test."""
    lesson_type = lesson.get("lesson_type", "new_material")
    week_number = lesson.get("week", 1)
    month_number = lesson.get("month", 1)
    if lesson_type == "final_exam":
        words = [
            word for week in WEEKS for day in week["days"][:5]
            for word in day["words"]
        ]
        target = 100
    elif lesson_type == "monthly_exam":
        month_weeks = WEEKS[(month_number - 1) * 4:month_number * 4]
        words = [
            word for week in month_weeks for day in week["days"][:5]
            for word in day["words"]
        ]
        target = 80
    elif lesson_type in {"weekly_review", "practical_review"}:
        words = [
            word for day in WEEKS[week_number - 1]["days"][:5]
            for word in day["words"]
        ]
        target = 20
    else:
        words = lesson["words"]
        target = 10

    # Preserve order while removing accidental exact duplicates from review pools.
    unique = {}
    for word in words:
        unique.setdefault(clean_english(word[0]).lower(), word)
    words = list(unique.values())
    questions = []
    all_words = list(words)
    random.shuffle(all_words)
    for i, (word_en, word_ru) in enumerate(all_words[:target]):
        word_en_clean = word_en.split(" [")[0] if " [" in word_en else word_en
        if i % 2 == 0:
            question = f"🇬🇧 *{word_en_clean}* → русский?"
            correct = word_ru[:25] if len(word_ru) > 25 else word_ru
            wrong_pool = [w[1][:25] if len(w[1]) > 25 else w[1] for w in words if w[0] != word_en]
        else:
            question = f"🇷🇺 *{word_ru}* → английский?"
            correct = word_en_clean[:25] if len(word_en_clean) > 25 else word_en_clean
            wrong_pool = [w[0].split(" [")[0][:25] for w in words if w[0] != word_en]
        wrong_pool = [w for w in wrong_pool if w != correct]
        if len(wrong_pool) < 3:
            continue
        options = [correct] + random.sample(wrong_pool, 3)
        random.shuffle(options)
        questions.append({"question": question, "correct": correct, "options": options, "num": i + 1})
    return questions[:target]


QUIZ_MOTIVATIONS_PERFECT = [
    "🔥 10/10! Ты машина! Lumora говорит по-английски!",
    "⭐ Идеальный результат! Клиенты оценят твой профессионализм!",
    "🏆 10 из 10! Вот это уровень! Продолжай в том же духе!",
]
QUIZ_MOTIVATIONS_GOOD = [
    "💪 Отличный результат! Ещё пара повторений и будет идеально!",
    "📈 Хорошо! С каждым днём становишься увереннее!",
    "✅ Молодец! Эти слова уже в твоей памяти!",
]
QUIZ_MOTIVATIONS_OK = [
    "📚 Неплохо! Повтори урок и результат будет выше!",
    "💡 Хороший старт! Повторение — мать учения!",
    "🎯 Продолжай! С каждым тестом становится легче!",
]

# ─── ВЕЧЕРНИЕ НАПОМИНАНИЯ (20:00 МСК) ────────────────────────────
EVENING_REMINDERS = [
    "🔍 Агент Lumora докладывает: человек планирует переезд, мечтает о клиентах из Лондона — но английский сегодня не открывал. Подозреваемый найден на диване. Мечта под угрозой.",
    "🩺 Симптомы: хочет работать с командами из Дубая, жить у моря и строить международный бизнес. Но урок пропустил. Рецепт: 10 минут — и Барселона станет чуть ближе.",
    "🏋️ Ты собираешься переехать. Новая страна, пляж, свобода. А английский сегодня? Клиенты из Амстердама не будут ждать пока ты раскачаешься.",
    "🤌 Дон Lumora напоминает: ты собрался уехать и работать с командами из Сингапура. Урок сегодня пропущен. Это неуважение к собственной мечте.",
    "🚀 Миссия: море, солнце, клиенты со всего мира. Старт запланирован. Сегодняшний урок: не выполнен. До Майами, Лиссабона или Бали — осталось меньше времени чем кажется.",
    "📺 Previously on Lumora: герой мечтает бросить всё, уехать к морю и работать с клиентами из Токио и Лондона. Сегодняшняя серия: он не открыл бот. Спойлер — так мечты не сбываются.",
    "🌤 Ты планируешь уехать туда где солнце и море. В Ницце солнце. В Валенсии солнце. Везде там говорят по-английски. Урок сегодня пропущен — совпадение?",
    "⚖️ Заседание открыто. Обвиняемый планирует покорять мировой рынок, мечтает о клиентах из Дубая — и пропустил урок английского. Приговор: открыть бот прямо сейчас.",
    "🛰 Спутник Lumora фиксирует: переезд запланирован. До Лиссабона — перелёт. До Бангкока — перелёт. До уверенного английского — 10 минут в день. Сегодня они не были потрачены.",
    "📋 Ты планируешь переехать, смотреть на море и работать с кем хочешь. Клиенты из Берлина, Дубая и Майами ждут именно таких. Но 10 минут английского сегодня — пропущены. Море подождёт. Мечта — не очень.",
]

# ─── ХЭНДЛЕРЫ ─────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await create_user(user.id, user.username or "", user.first_name or "")
    keyboard = [
        [InlineKeyboardButton("📚 Урок дня", callback_data="lesson")],
        [InlineKeyboardButton("🎯 Тест", callback_data="quiz")],
        [InlineKeyboardButton("🔄 Повторить урок", callback_data="review")],
        [InlineKeyboardButton("📖 Мой словарик", callback_data="vocab")],
        [InlineKeyboardButton("🏆 Лидерборд", callback_data="leaderboard")],
        [InlineKeyboardButton("📊 Мой прогресс", callback_data="progress")],
    ]
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        f"Добро пожаловать в *Lumora English* — систему изучения бизнес-английского для команды.\n\n"
        f"Цель: через 4 месяца уверенно общаться с клиентами на английском.\n\n"
        f"📅 Программа: 16 недель × 5 уроков\n"
        f"⏱ В день: 10-15 минут\n"
        f"🎯 Фокус: слова, диалоги, фразы из фильмов\n\n"
        f"Начнём?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def lesson_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("Напиши /start чтобы начать.")
        return
    week_idx = user["current_week"]
    day_idx = user["current_day"]
    lesson = get_current_lesson(week_idx, day_idx)
    if not lesson:
        await query.edit_message_text("🎉 Ты прошёл всю программу! Напиши /start.")
        return
    week = WEEKS[week_idx]
    opened_today = (
        user.get("opened_date") == today_str()
        and user.get("opened_lesson_id") == lesson["lesson_id"]
    )
    if not opened_today:
        await update_user(
            user_id,
            opened_date=today_str(),
            opened_lesson_id=lesson["lesson_id"],
            current_lesson_id=lesson["lesson_id"],
        )
    phrase = lesson["phrase"]
    words_text = "\n".join([f"• *{en.split(chr(32)+chr(91))[0]}* — {ru}" for en, ru in lesson["words"]])
    dialogue_text = await build_dialogue_text(lesson["dialogue"])
    text = (
        ("ℹ️ _Сегодняшний урок уже открыт_\n\n" if opened_today else "")
        +
        f"📚 *{week['title']}*\n"
        f"День {day_idx + 1}/7{' 🔄 Повторение' if day_idx >= 5 else ''} — {lesson['topic']}\n\n"
        f"*🔤 Слова дня:*\n{words_text}\n\n"
        f"*🎬 Фраза из фильма:*\n"
        f"_{phrase['text']}_\n"
        f"📽 {phrase['movie']}\n"
        f"💡 {phrase['meaning']}\n\n"
        f"*💬 Диалог:*\n{dialogue_text}"
    )
    audio_day_idx = resolve_lesson_day(week_idx, day_idx, lesson)
    keyboard = lesson_audio_keyboard(week_idx, audio_day_idx, lesson) + [
        [InlineKeyboardButton("🎯 Пройти тест по уроку", callback_data="quiz_lesson")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="menu")],
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def quiz_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("Напиши /start чтобы начать.")
        return
    lesson = get_current_lesson(user["current_week"], user["current_day"])
    if not lesson:
        await query.edit_message_text("Уроки закончились! Напиши /start.")
        return
    questions = generate_quiz_session(lesson)
    if not questions:
        await query.edit_message_text("Ошибка генерации теста.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Меню", callback_data="menu")]]))
        return
    import json
    session = {"questions": questions, "current": 0, "score": 0, "total": len(questions)}
    await update_user(user_id, quiz_state=json.dumps(session))
    q = questions[0]
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"qa_{opt[:20]}")] for opt in q["options"]]
    await query.edit_message_text(
        f"🎯 *Тест — {lesson['topic']}*\n"
        f"Вопрос 1/{len(questions)}\n\n"
        f"{q['question']}\n\nВыбери правильный ответ:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def quiz_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ответы в 10-вопросном тесте"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chosen = query.data.replace("qa_", "", 1)
    user = await get_user(user_id)
    if not user:
        return
    import json
    try:
        session = json.loads(user["quiz_state"]) if user["quiz_state"] else {}
    except Exception:
        session = {}
    if not session or "questions" not in session:
        await query.edit_message_text(
            "Сессия истекла. Начни новый тест.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎯 Новый тест", callback_data="quiz")]])
        )
        return
    questions = session["questions"]
    current = session["current"]
    score = session["score"]
    total = session["total"]

    # Защита от выхода за границы
    if current >= len(questions):
        await query.edit_message_text(
            "Тест завершён!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Меню", callback_data="menu")]])
        )
        return

    q = questions[current]
    correct = q["correct"]
    correct_short = correct[:20] if len(correct) > 20 else correct
    is_correct = chosen == correct_short
    if is_correct:
        score += 1
    current += 1
    session["current"] = current
    session["score"] = score

    result_icon = "✅" if is_correct else "❌"
    result_text = f"{result_icon} {'Верно!' if is_correct else f'Неверно. Правильно: *{correct}*'}"

    if current >= len(questions):
        # ─── ТЕСТ ЗАВЕРШЁН ───────────────────────────────────────────
        pct = round(score / total * 100)
        if score == total:
            motivation = random.choice(QUIZ_MOTIVATIONS_PERFECT)
        elif score >= total * 0.7:
            motivation = random.choice(QUIZ_MOTIVATIONS_GOOD)
        else:
            motivation = random.choice(QUIZ_MOTIVATIONS_OK)

        today = today_str()
        yesterday = (datetime.now(TIMEZONE) - timedelta(days=1)).strftime("%Y-%m-%d")
        last_day = user.get("last_day") or ""

        # ─── FIX 2: streak/days обновляем НЕЗАВИСИМО от других взаимодействий ──
        # answer_handler (одиночный вопрос) НЕ меняет last_day
        # Только quiz_answer_handler (полный тест) управляет last_day
        streak = user["streak"]
        total_days = user["total_days"]
        first_completion_today = (last_day != today)

        # XP только если урок не пройден ранее
        lesson = get_current_lesson(user["current_week"], user["current_day"])
        lesson_key = (
            lesson["lesson_id"]
            if lesson else f"{user['current_week']}_{user['current_day']}"
        )
        completed_lessons_str = user.get("completed_lessons") or ""
        lessons_list = [l for l in completed_lessons_str.split(",") if l]
        already_done = lesson_key in lessons_list
        should_advance = first_completion_today and not already_done

        if should_advance:
            streak = streak + 1 if last_day == yesterday else 1
            total_days += 1

        if already_done:
            xp_gain = 0
            bonus_text = "\n_Этот урок уже пройден — XP за повторение не начисляется._"
        else:
            xp_gain = score * 5
            bonus_text = ""
            lessons_list.append(lesson_key)

        new_xp = user["xp"] + xp_gain
        new_completed = ",".join(lessons_list)

        new_day = user["current_day"]
        new_week = user["current_week"]
        if should_advance:
            new_day += 1
            if new_day >= 7:
                new_day = 0
                new_week += 1
        new_lesson_id = (
            WEEKS[new_week]["days"][new_day]["lesson_id"]
            if new_week < len(WEEKS) else ""
        )

        # Сохраняем с fallback если колонки completed_lessons ещё нет
        try:
            await update_user(
                user_id,
                xp=new_xp, streak=streak, total_days=total_days,
                last_day=today if should_advance else last_day,
                current_day=new_day, current_week=new_week,
                current_lesson_id=new_lesson_id,
                quiz_state=json.dumps({}), completed_lessons=new_completed
            )
        except Exception as e:
            logger.error(f"update_user failed for {user_id}: {e}")
            try:
                await update_user(
                    user_id,
                    xp=new_xp, streak=streak, total_days=total_days,
                    last_day=today, current_day=new_day, current_week=new_week,
                    quiz_state=json.dumps({})
                )
            except Exception as e2:
                logger.error(f"Fallback update also failed: {e2}")

        bar = xp_bar(new_xp)
        level = get_level(new_xp)
        level_name = LEVELS[level][1]
        keyboard = [
            [InlineKeyboardButton("📚 Следующий урок", callback_data="lesson")],
            [InlineKeyboardButton("🔄 Повторить тест", callback_data="quiz")],
            [InlineKeyboardButton("🏠 Меню", callback_data="menu")],
        ]
        xp_text = f"+{xp_gain} XP" if xp_gain > 0 else "0 XP (повтор)"
        await query.edit_message_text(
            f"{result_text}\n\n"
            f"{'─'*22}\n"
            f"🎯 *Результат теста*\n"
            f"Правильных ответов: *{score}/{total}* ({pct}%)\n\n"
            f"{motivation}\n\n"
            f"{xp_text}\n"
            f"{level_name}\n"
            f"{bar}  {new_xp} XP{bonus_text}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # ─── СЛЕДУЮЩИЙ ВОПРОС ────────────────────────────────────────
        await update_user(user_id, quiz_state=json.dumps(session))
        next_q = questions[current]
        keyboard = [[InlineKeyboardButton(opt, callback_data=f"qa_{opt[:20]}")] for opt in next_q["options"]]
        await query.edit_message_text(
            f"{result_text}\n\n"
            f"{'─'*22}\n"
            f"Вопрос {current + 1}/{total}\n\n"
            f"{next_q['question']}\n\nВыбери правильный ответ:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Одиночный вопрос для повторения уроков.
    FIX 3: НЕ меняет last_day, streak, total_days — только XP.
    Иначе блокирует streak у полного теста."""
    query = update.callback_query
    await query.answer()
    data = query.data.replace("answer_", "", 1)
    parts = data.rsplit("_", 1)
    if len(parts) != 2:
        return
    chosen, correct = parts[0], parts[1]
    user_id = query.from_user.id
    user = await get_user(user_id)
    if not user:
        return

    if chosen == correct:
        xp_gain = 5
        new_xp = user["xp"] + xp_gain
        # ─── FIX 3: только XP, без last_day/streak/days ────────────
        await update_user(user_id, xp=new_xp)
        level = get_level(new_xp)
        level_name = LEVELS[level][1]
        bar = xp_bar(new_xp)
        motivations = [
            "Отлично! Так и строится словарный запас 🔥",
            "Правильно! Ещё один шаг к уверенному английскому 💪",
            "Верно! Клиенты оценят твой профессионализм ⭐",
            "Молодец! Каждое слово — это инвестиция в бизнес 📈",
            "Правильно! Lumora говорит по-английски 🌍",
        ]
        keyboard = [
            [InlineKeyboardButton("➡️ Следующий вопрос", callback_data="quiz")],
            [InlineKeyboardButton("📚 К уроку", callback_data="lesson")],
            [InlineKeyboardButton("🏠 Меню", callback_data="menu")],
        ]
        await query.edit_message_text(
            f"✅ *+{xp_gain} XP!*\n\n"
            f"{random.choice(motivations)}\n\n"
            f"{level_name}\n"
            f"{bar}  {new_xp} XP",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        keyboard = [
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data="quiz")],
            [InlineKeyboardButton("📚 К уроку", callback_data="lesson")],
            [InlineKeyboardButton("🏠 Меню", callback_data="menu")],
        ]
        await query.edit_message_text(
            f"❌ Неправильно\n\n"
            f"Ты ответил: *{chosen}*\n"
            f"Правильный ответ: *{correct}*\n\n"
            f"Не сдавайся — повтори урок и попробуй снова!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def leaderboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    rows = await get_leaderboard()
    if not rows:
        text = "🏆 Лидерборд пока пустой. Начни учиться первым!"
    else:
        medals = ["🥇", "🥈", "🥉"] + ["4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        lines = []
        for i, row in enumerate(rows):
            medal = medals[i] if i < len(medals) else f"{i+1}."
            week = row["current_week"] + 1
            lines.append(f"{medal} *{row['first_name']}* — {row['xp']} XP | Неделя {week} | 🔥{row['streak']}дн")
        text = "🏆 *Лидерборд команды*\n\n" + "\n".join(lines)
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="menu")]]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def progress_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("Напиши /start чтобы начать.")
        return
    xp = user["xp"]
    level = get_level(xp)
    level_name = LEVELS[level][1]
    bar = xp_bar(xp)
    completed_lessons_str = user.get("completed_lessons") or ""
    completed_count = len([l for l in completed_lessons_str.split(",") if l])
    total_words = completed_count * 10
    week_name = WEEKS[min(user["current_week"], len(WEEKS)-1)]["title"]
    next_level_xp = LEVELS[level + 1][0] if level + 1 < len(LEVELS) else LEVELS[level][0]
    xp_to_next = next_level_xp - xp
    text = (
        f"📊 *Твой прогресс*\n\n"
        f"{level_name}\n"
        f"{bar}  {xp} XP\n"
        f"До след. уровня: {xp_to_next} XP\n\n"
        f"🔥 Серия: {user['streak']} дн.\n"
        f"📅 Дней активности: {user['total_days']}\n"
        f"📚 Слов изучено: ~{total_words}\n"
        f"📖 Уроков пройдено: {completed_count}\n\n"
        f"📌 Текущая тема:\n{week_name}\n"
        f"День {user['current_day'] + 1}/7"
    )
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="menu")]]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📚 Урок дня", callback_data="lesson")],
        [InlineKeyboardButton("🎯 Тест", callback_data="quiz")],
        [InlineKeyboardButton("🔄 Повторить урок", callback_data="review")],
        [InlineKeyboardButton("📖 Мой словарик", callback_data="vocab")],
        [InlineKeyboardButton("🏆 Лидерборд", callback_data="leaderboard")],
        [InlineKeyboardButton("📊 Мой прогресс", callback_data="progress")],
    ]
    await query.edit_message_text(
        "🌍 *Lumora English*\n\nЧто хочешь делать?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def morning_reminder(app):
    while True:
        now = datetime.now(TIMEZONE)
        target = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            users = await conn.fetch("SELECT user_id, first_name, current_week, current_day FROM users")
            await conn.close()
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📚 Урок дня", callback_data="lesson")],
                [InlineKeyboardButton("🎯 Тест", callback_data="quiz")],
            ])
            for user in users:
                lesson = get_current_lesson(user["current_week"], user["current_day"])
                if lesson:
                    try:
                        await app.bot.send_message(
                            chat_id=user["user_id"],
                            text=(
                                f"☀️ Доброе утро, {user['first_name']}!\n\n"
                                f"Сегодняшняя тема: *{lesson['topic']}*\n"
                                f"10 новых слов ждут тебя. Это всего 10 минут 💪"
                            ),
                            parse_mode="Markdown",
                            reply_markup=keyboard
                        )
                    except Exception as e:
                        logger.error(f"Reminder error for {user['user_id']}: {e}")
        except Exception as e:
            logger.error(f"Morning reminder error: {e}")

async def evening_reminder(app):
    """Напоминание в 20:00 МСК тем кто не прошёл урок сегодня"""
    MSK = pytz.timezone("Europe/Moscow")
    while True:
        now = datetime.now(MSK)
        target = now.replace(hour=20, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())

        today = datetime.now(MSK).strftime("%Y-%m-%d")
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            users = await conn.fetch("SELECT user_id, first_name, last_day FROM users")
            await conn.close()

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📚 Урок дня", callback_data="lesson")],
                [InlineKeyboardButton("🎯 Тест", callback_data="quiz")],
            ])

            for user in users:
                if (user["last_day"] or "") == today:
                    continue
                try:
                    message = random.choice(EVENING_REMINDERS)
                    await app.bot.send_message(
                        chat_id=user["user_id"],
                        text=f"{message}\n\n👇 Пройди урок — это 10 минут.",
                        reply_markup=keyboard
                    )
                except Exception as e:
                    logger.error(f"Evening reminder error for {user['user_id']}: {e}")
        except Exception as e:
            logger.error(f"Evening reminder DB error: {e}")

async def post_init(app):
    await init_db()
    asyncio.create_task(morning_reminder(app))
    asyncio.create_task(evening_reminder(app))

async def openai_tts(
    text: str,
    voice: str = "cedar",
    instructions: str = "",
    speed: float = 1.0,
) -> bytes:
    """Generate natural educational speech with the instruction-capable TTS model."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    payload = {
        "model": "gpt-4o-mini-tts",
        "input": text,
        "voice": voice,
        "speed": speed,
        "response_format": "mp3",
    }
    if instructions:
        payload["instructions"] = instructions
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        return response.content

async def generate_word_audio(word: str) -> bytes:
    """Word x2 with safe leading, middle and trailing silence."""
    import io
    from pydub import AudioSegment

    audio_bytes = await openai_tts(
        word,
        voice="cedar",
        speed=1.0,
        instructions=(
            "Pronounce exactly the supplied English word or short phrase. "
            "Speak slowly and very clearly for an A1-A2 English learner, "
            "with careful natural articulation and a neutral accent. "
            "Do not add explanations or any extra words."
        ),
    )

    spoken = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
    leading_silence = AudioSegment.silent(duration=1000)
    repetition_pause = AudioSegment.silent(duration=3500)
    trailing_silence = AudioSegment.silent(duration=2000)
    combined = (
        leading_silence
        + spoken
        + repetition_pause
        + spoken
        + trailing_silence
    )

    buf = io.BytesIO()
    combined.export(buf, format="mp3")
    buf.seek(0)
    return buf.read()

async def pronunciation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate only the lesson audio item selected by the user."""
    query = update.callback_query
    await query.answer("Генерирую выбранное аудио… 🎵")

    try:
        _, item_type, week_raw, day_raw, item_raw = query.data.split("_")
        week_idx = int(week_raw)
        day_idx = int(day_raw)
        item_index = int(item_raw)
    except (ValueError, TypeError):
        await query.message.reply_text("Не удалось определить аудиофрагмент.")
        return

    lesson = get_lesson_by_position(week_idx, day_idx)
    if not lesson:
        await query.message.reply_text("Урок не найден.")
        return

    import io

    if item_type == "w":
        if item_index < 0 or item_index >= len(lesson.get("words", [])):
            await query.message.reply_text("Слово не найдено.")
            return
        word_en, word_ru = lesson["words"][item_index]
        clean = clean_english(word_en)
        try:
            audio_bytes = await generate_word_audio(clean)
            buf = io.BytesIO(audio_bytes)
            buf.name = "word.mp3"
            await query.message.reply_voice(
                voice=buf,
                caption=f"🔤 *{clean}* — {word_ru}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"TTS word error ({clean}): {e}")
            await query.message.reply_text("Не удалось создать аудио. Попробуй ещё раз.")
        return

    if item_type == "p":
        phrase_data = lesson.get("phrase", {})
        phrase = phrase_data.get("text", "")
        if not phrase:
            await query.message.reply_text("Фраза не найдена.")
            return
        try:
            audio_phrase = await openai_tts(
                phrase,
                voice="marin",
                speed=0.78,
                instructions=(
                    "This is listening practice for a beginner A1-A2 English "
                    "learner. Speak much slower than normal conversation, at "
                    "approximately 80 to 90 words per minute. Articulate every "
                    "word fully and insert clear natural pauses between meaning "
                    "groups. Keep the voice natural, not stretched or robotic. "
                    "Do not add any extra words."
                ),
            )
            buf = io.BytesIO(audio_phrase)
            buf.name = "phrase.mp3"
            await query.message.reply_voice(
                voice=buf,
                caption=f"🎬 _{phrase}_\n📽 {phrase_data.get('movie', '')}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"TTS phrase error: {e}")
            await query.message.reply_text("Не удалось создать аудио. Попробуй ещё раз.")
        return

    if item_type == "d":
        dialogue = lesson.get("dialogue", [])
        if item_index < 0 or item_index >= len(dialogue):
            await query.message.reply_text("Реплика не найдена.")
            return
        role, line = dialogue[item_index]
        voice = "marin" if role == "You" else "cedar"
        icon = "🗣" if role == "You" else "👤"
        try:
            audio_line = await openai_tts(
                line,
                voice=voice,
                speed=0.78,
                instructions=(
                    "This is a beginner A1-A2 classroom dialogue. Speak much "
                    "slower than normal conversation, at approximately 80 to 90 "
                    "words per minute. Articulate every word fully and pause "
                    "clearly between meaning groups while keeping natural "
                    "conversational intonation. Do not sound rushed or robotic. "
                    "Do not add any extra words."
                ),
            )
            buf = io.BytesIO(audio_line)
            buf.name = "line.mp3"
            translations = await get_dialogue_translations([(role, line)])
            translation = translations.get(line, "Перевод временно недоступен")
            await query.message.reply_voice(
                voice=buf,
                caption=f"{icon} *{role}:* _{line}_\n↳ {translation}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"TTS dialogue error ({role}): {e}")
            await query.message.reply_text("Не удалось создать аудио. Попробуй ещё раз.")
        return

    await query.message.reply_text("Неизвестный тип аудио.")

async def vocab_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("Напиши /start чтобы начать.")
        return

    # Используем completed_lessons — обновляется сразу после теста
    completed_lessons_str = user.get("completed_lessons") or ""
    completed_list = sorted([l for l in completed_lessons_str.split(",") if l])

    if not completed_list:
        await query.edit_message_text(
            "Ты ещё не прошёл ни одного урока!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="menu")]])
        )
        return

    lines = ["📖 *Твой словарик*\n"]
    prev_week = None
    for lesson_key in completed_list:
        try:
            w, d = map(int, lesson_key.split("_"))
        except ValueError:
            continue
        if w >= len(WEEKS) or d >= len(WEEKS[w]["days"]):
            continue
        if w != prev_week:
            lines.append(f"\n*{WEEKS[w]['title']}*")
            prev_week = w
        lesson = WEEKS[w]["days"][d]
        lines.append(f"\n_{lesson['topic']}_")
        for en, ru in lesson["words"]:
            lines.append(f"• *{en.split(chr(32)+chr(91))[0]}* — {ru}")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n\n_...показаны первые слова_"
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="menu")]]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def review_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("Напиши /start чтобы начать.")
        return
    week_idx = user["current_week"]
    day_idx = user["current_day"]
    if week_idx == 0 and day_idx == 0:
        await query.edit_message_text("Ты ещё не прошёл ни одного урока!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="menu")]]))
        return
    keyboard = []
    for w in range(week_idx + 1):
        week = WEEKS[w]
        max_day = day_idx if w == week_idx else 5
        for d in range(max_day):
            lesson = week["days"][d]
            keyboard.append([InlineKeyboardButton(f"W{w+1}D{d+1} — {lesson['topic']}", callback_data=f"review_{w}_{d}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu")])
    await query.edit_message_text(
        "📚 *Пройденные уроки*\n\nВыбери урок для повторения:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def review_lesson_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    week_idx = int(parts[1])
    day_idx = int(parts[2])
    lesson = get_current_lesson(week_idx, day_idx)
    if not lesson:
        await query.edit_message_text("Урок не найден.")
        return
    week = WEEKS[week_idx]
    phrase = lesson["phrase"]
    words_text = "\n".join([f"• *{en.split(chr(32)+chr(91))[0]}* — {ru}" for en, ru in lesson["words"]])
    dialogue_text = await build_dialogue_text(lesson["dialogue"])
    text = (
        f"🔄 *Повторение*\n"
        f"*{week['title']}* — {lesson['topic']}\n\n"
        f"*🔤 Слова:*\n{words_text}\n\n"
        f"*🎬 Фраза из фильма:*\n"
        f"_{phrase['text']}_\n"
        f"📽 {phrase['movie']}\n"
        f"💡 {phrase['meaning']}\n\n"
        f"*💬 Диалог:*\n{dialogue_text}"
    )
    keyboard = lesson_audio_keyboard(week_idx, day_idx, lesson) + [
        [InlineKeyboardButton("🎯 Тест по этому уроку", callback_data=f"quiz_review_{week_idx}_{day_idx}")],
        [InlineKeyboardButton("⬅️ К списку уроков", callback_data="review")],
        [InlineKeyboardButton("🏠 Меню", callback_data="menu")],
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def quiz_review_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    week_idx = int(parts[2])
    day_idx = int(parts[3])
    lesson = get_current_lesson(week_idx, day_idx)
    if not lesson:
        await query.edit_message_text("Урок не найден.")
        return
    quiz = generate_quiz(lesson)
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"answer_{opt}_{quiz['correct']}")] for opt in quiz["options"]]
    keyboard.append([InlineKeyboardButton("⬅️ К уроку", callback_data=f"review_{week_idx}_{day_idx}")])
    await query.edit_message_text(
        f"🎯 *Тест — повторение*\n\n{quiz['question']}\n\nВыбери правильный ответ:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def lesson_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Напиши /start чтобы начать.")
        return
    lesson = get_current_lesson(user["current_week"], user["current_day"])
    if not lesson:
        await update.message.reply_text("Ты прошёл всю программу! Напиши /start.")
        return
    week = WEEKS[user["current_week"]]
    phrase = lesson["phrase"]
    words_text = "\n".join([f"• *{en.split(chr(32)+chr(91))[0]}* — {ru}" for en, ru in lesson["words"]])
    dialogue_text = await build_dialogue_text(lesson["dialogue"])
    text = (
        f"📚 *{week['title']}*\n"
        f"День {user['current_day'] + 1}/7 — {lesson['topic']}\n\n"
        f"*🔤 Слова дня:*\n{words_text}\n\n"
        f"*🎬 Фраза из фильма:*\n"
        f"_{phrase['text']}_\n"
        f"📽 {phrase['movie']}\n"
        f"💡 {phrase['meaning']}\n\n"
        f"*💬 Диалог:*\n{dialogue_text}"
    )
    audio_day_idx = resolve_lesson_day(user["current_week"], user["current_day"], lesson)
    keyboard = lesson_audio_keyboard(user["current_week"], audio_day_idx, lesson) + [
        [InlineKeyboardButton("🎯 Пройти тест по уроку", callback_data="quiz_lesson")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="menu")],
    ]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Напиши /start чтобы начать.")
        return
    lesson = get_current_lesson(user["current_week"], user["current_day"])
    if not lesson:
        await update.message.reply_text("Уроки закончились!")
        return
    quiz = generate_quiz(lesson)
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"answer_{opt}_{quiz['correct']}")] for opt in quiz["options"]]
    keyboard.append([InlineKeyboardButton("⬅️ Меню", callback_data="menu")])
    import json
    await update_user(user_id, quiz_state=json.dumps({"correct": quiz["correct"]}))
    await update.message.reply_text(
        f"🎯 *Тест*\n\n{quiz['question']}\n\nВыбери правильный ответ:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Напиши /start чтобы начать.")
        return
    xp = user["xp"]
    level = get_level(xp)
    level_name = LEVELS[level][1]
    bar = xp_bar(xp)
    completed_lessons_str = user.get("completed_lessons") or ""
    completed_count = len([l for l in completed_lessons_str.split(",") if l])
    total_words = completed_count * 10
    week_name = WEEKS[min(user["current_week"], len(WEEKS)-1)]["title"]
    next_level_xp = LEVELS[level + 1][0] if level + 1 < len(LEVELS) else LEVELS[level][0]
    xp_to_next = next_level_xp - xp
    await update.message.reply_text(
        f"📊 *Твой прогресс*\n\n"
        f"{level_name}\n"
        f"{bar}  {xp} XP\n"
        f"До след. уровня: {xp_to_next} XP\n\n"
        f"🔥 Серия: {user['streak']} дн.\n"
        f"📅 Дней активности: {user['total_days']}\n"
        f"📚 Слов изучено: ~{total_words}\n"
        f"📖 Уроков пройдено: {completed_count}\n\n"
        f"📌 {week_name}\n"
        f"День {user['current_day'] + 1}/7",
        parse_mode="Markdown"
    )

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = await get_leaderboard()
    if not rows:
        await update.message.reply_text("🏆 Лидерборд пока пустой.")
        return
    medals = ["🥇", "🥈", "🥉"] + ["4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    lines = []
    for i, row in enumerate(rows):
        medal = medals[i] if i < len(medals) else f"{i+1}."
        lines.append(f"{medal} *{row['first_name']}* — {row['xp']} XP | 🔥{row['streak']}дн")
    await update.message.reply_text("🏆 *Лидерборд команды*\n\n" + "\n".join(lines), parse_mode="Markdown")

async def vocab_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Напиши /start чтобы начать.")
        return

    completed_lessons_str = user.get("completed_lessons") or ""
    completed_list = sorted([l for l in completed_lessons_str.split(",") if l])

    if not completed_list:
        await update.message.reply_text("Ты ещё не прошёл ни одного урока. Начни с /start!")
        return

    lines = ["📖 *Твой словарик*\n"]
    prev_week = None
    for lesson_key in completed_list:
        try:
            w, d = map(int, lesson_key.split("_"))
        except ValueError:
            continue
        if w >= len(WEEKS) or d >= len(WEEKS[w]["days"]):
            continue
        if w != prev_week:
            lines.append(f"\n*{WEEKS[w]['title']}*")
            prev_week = w
        lesson = WEEKS[w]["days"][d]
        lines.append(f"\n_{lesson['topic']}_")
        for en, ru in lesson["words"]:
            lines.append(f"• *{en.split(chr(32)+chr(91))[0]}* — {ru}")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n\n_...показаны первые слова_"
    await update.message.reply_text(text, parse_mode="Markdown")


def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lesson", lesson_command))
    app.add_handler(CommandHandler("quiz", quiz_command))
    app.add_handler(CommandHandler("progress", progress_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    app.add_handler(CommandHandler("vocab", vocab_command))
    app.add_handler(CallbackQueryHandler(lesson_handler, pattern="^lesson$"))
    app.add_handler(CallbackQueryHandler(quiz_handler, pattern="^quiz_lesson$"))
    app.add_handler(CallbackQueryHandler(quiz_handler, pattern="^quiz$"))
    app.add_handler(CallbackQueryHandler(quiz_answer_handler, pattern="^qa_"))
    app.add_handler(CallbackQueryHandler(answer_handler, pattern="^answer_"))
    app.add_handler(CallbackQueryHandler(leaderboard_handler, pattern="^leaderboard$"))
    app.add_handler(CallbackQueryHandler(progress_handler, pattern="^progress$"))
    app.add_handler(CallbackQueryHandler(menu_handler, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(review_handler, pattern="^review$"))
    app.add_handler(CallbackQueryHandler(review_lesson_handler, pattern="^review_\\d+_\\d+$"))
    app.add_handler(CallbackQueryHandler(quiz_review_handler, pattern="^quiz_review_"))
    app.add_handler(CallbackQueryHandler(vocab_handler, pattern="^vocab$"))
    app.add_handler(CallbackQueryHandler(
        pronunciation_handler,
        pattern=r"^audio_[wpd]_\d+_\d+_\d+$"
    ))
    logger.info("Lumora English Bot started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
