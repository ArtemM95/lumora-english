import logging
import asyncio
import os
import random
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

WEEKS = [
    # НЕДЕЛЯ 1 — Знакомство и основы
    {
        "title": "Week 1 — Introductions & Basics",
        "days": [
            {
                "topic": "Introducing yourself",
                "words": [
                    ("Hello", "Привет / Здравствуйте"),
                    ("My name is", "Меня зовут"),
                    ("I work as", "Я работаю как"),
                    ("Nice to meet you", "Рад познакомиться"),
                    ("Company", "Компания"),
                    ("Producer", "Продюсер"),
                    ("Agency", "Агентство"),
                    ("Project", "Проект"),
                    ("Experience", "Опыт"),
                    ("Specialize in", "Специализируюсь на"),
                ],
                "phrase": {
                    "text": "You had me at hello.",
                    "movie": "Jerry Maguire (1996)",
                    "meaning": "Ты убедил меня с первого слова. Используй в переговорах: первое впечатление решает всё."
                },
                "dialogue": [
                    ("You", "Hi, I'm Artem. I'm a video producer from Lumora Studio."),
                    ("Client", "Nice to meet you, Artem. What do you specialize in?"),
                    ("You", "I specialize in AI-powered video production for B2B companies."),
                ]
            },
            {
                "topic": "Your company & services",
                "words": [
                    ("Video production", "Видеопроизводство"),
                    ("Content", "Контент"),
                    ("Corporate video", "Корпоративное видео"),
                    ("Brand film", "Брендовый фильм"),
                    ("Budget", "Бюджет"),
                    ("Deadline", "Дедлайн"),
                    ("Deliver", "Доставить / Сдать"),
                    ("Quality", "Качество"),
                    ("Client", "Клиент"),
                    ("Portfolio", "Портфолио"),
                ],
                "phrase": {
                    "text": "Show me the money.",
                    "movie": "Jerry Maguire (1996)",
                    "meaning": "Покажи результат. В бизнесе: клиент хочет видеть реальную ценность, не слова."
                },
                "dialogue": [
                    ("You", "We produce corporate videos and brand films."),
                    ("Client", "What's your typical budget range?"),
                    ("You", "It depends on the project. Can you share more about what you need?"),
                ]
            },
            {
                "topic": "First call essentials",
                "words": [
                    ("Schedule a call", "Назначить звонок"),
                    ("Available", "Доступен"),
                    ("Time zone", "Часовой пояс"),
                    ("Zoom call", "Звонок в Zoom"),
                    ("Follow up", "Связаться снова"),
                    ("Proposal", "Предложение"),
                    ("Brief", "Бриф"),
                    ("Requirements", "Требования"),
                    ("Discuss", "Обсудить"),
                    ("Details", "Детали"),
                ],
                "phrase": {
                    "text": "I'll make him an offer he can't refuse.",
                    "movie": "The Godfather (1972)",
                    "meaning": "Сделай предложение от которого не откажутся. В продажах: твой оффер должен быть настолько ценным, что отказ невозможен."
                },
                "dialogue": [
                    ("You", "Could we schedule a call this week to discuss the details?"),
                    ("Client", "Sure. I'm available Thursday at 3 PM CET."),
                    ("You", "Perfect. I'll send a Zoom link right away."),
                ]
            },
            {
                "topic": "Understanding client needs",
                "words": [
                    ("Goal", "Цель"),
                    ("Target audience", "Целевая аудитория"),
                    ("Message", "Сообщение / Посыл"),
                    ("Vision", "Видение"),
                    ("Feedback", "Обратная связь"),
                    ("Revision", "Правка"),
                    ("Approval", "Утверждение"),
                    ("Timeline", "Сроки"),
                    ("Milestone", "Этап / Веха"),
                    ("Scope", "Объём работ"),
                ],
                "phrase": {
                    "text": "What we've got here is failure to communicate.",
                    "movie": "Cool Hand Luke (1967)",
                    "meaning": "Проблема в коммуникации. В B2B: большинство провалов проектов — из-за плохо понятого брифа."
                },
                "dialogue": [
                    ("You", "What's the main goal of this video?"),
                    ("Client", "We want to explain our product to new customers."),
                    ("You", "Got it. Who is your target audience?"),
                ]
            },
            {
                "topic": "Presenting your offer",
                "words": [
                    ("Proposal", "Коммерческое предложение"),
                    ("Package", "Пакет"),
                    ("Include", "Включать"),
                    ("Deliverable", "Результат работы"),
                    ("Turnaround", "Срок выполнения"),
                    ("Invest", "Инвестировать"),
                    ("Value", "Ценность"),
                    ("Solution", "Решение"),
                    ("Offer", "Предложение"),
                    ("Competitive", "Конкурентный"),
                ],
                "phrase": {
                    "text": "You're going to need a bigger boat.",
                    "movie": "Jaws (1975)",
                    "meaning": "Тебе нужен больший масштаб. В продажах: иногда нужно предложить клиенту более полное решение."
                },
                "dialogue": [
                    ("You", "Our proposal includes the full video production package."),
                    ("Client", "What exactly is included?"),
                    ("You", "Script, filming, editing, and two rounds of revisions."),
                ]
            },
        ]
    },
    # НЕДЕЛЯ 2 — Переговоры и закрытие
    {
        "title": "Week 2 — Negotiations & Closing",
        "days": [
            {
                "topic": "Handling objections",
                "words": [
                    ("Concern", "Беспокойство / Возражение"),
                    ("Understand", "Понимать"),
                    ("However", "Однако"),
                    ("Actually", "На самом деле"),
                    ("Guarantee", "Гарантировать"),
                    ("Prove", "Доказать"),
                    ("Trust", "Доверие"),
                    ("Risk", "Риск"),
                    ("Confident", "Уверенный"),
                    ("Result", "Результат"),
                ],
                "phrase": {
                    "text": "That's the most ridiculous thing I've ever heard.",
                    "movie": "Suits (TV)",
                    "meaning": "Так говорят когда слышат слабый аргумент. Учись отвечать на возражения уверенно, не агрессивно."
                },
                "dialogue": [
                    ("Client", "Your price seems too high."),
                    ("You", "I understand your concern. However, our AI pipeline cuts production time by 3x."),
                    ("Client", "Can you prove that?"),
                    ("You", "Absolutely. I can share case studies from similar projects."),
                ]
            },
            {
                "topic": "Pricing conversations",
                "words": [
                    ("Quote", "Смета / Цитата"),
                    ("Rate", "Ставка"),
                    ("Invoice", "Счёт"),
                    ("Payment", "Оплата"),
                    ("Deposit", "Предоплата"),
                    ("Discount", "Скидка"),
                    ("Negotiate", "Переговоры / Торговаться"),
                    ("Contract", "Договор"),
                    ("Terms", "Условия"),
                    ("Per project", "За проект"),
                ],
                "phrase": {
                    "text": "Money is not the only commodity that is fun to give.",
                    "movie": "Wall Street (1987)",
                    "meaning": "Ценность не только в деньгах. В переговорах: иногда быстрый срок или бонус важнее скидки."
                },
                "dialogue": [
                    ("Client", "Can we get a discount?"),
                    ("You", "Our rate is $3,000 per project. We include two revisions."),
                    ("Client", "We were thinking more around $2,500."),
                    ("You", "Let me see what we can do to make it work for both sides."),
                ]
            },
            {
                "topic": "Closing the deal",
                "words": [
                    ("Agreement", "Соглашение"),
                    ("Sign", "Подписать"),
                    ("Move forward", "Двигаться вперёд"),
                    ("Confirm", "Подтвердить"),
                    ("Next steps", "Следующие шаги"),
                    ("Kick off", "Начать"),
                    ("Excited", "Взволнован / В предвкушении"),
                    ("Partnership", "Партнёрство"),
                    ("Looking forward", "С нетерпением жду"),
                    ("Pleasure", "Удовольствие"),
                ],
                "phrase": {
                    "text": "We're going to need you to go ahead and come in on Saturday.",
                    "movie": "Office Space (1999)",
                    "meaning": "Классика корпоративного давления. Знай как вежливо отказать или согласовать условия."
                },
                "dialogue": [
                    ("You", "Are you ready to move forward?"),
                    ("Client", "Yes, let's do it. What are the next steps?"),
                    ("You", "I'll send the contract today. Once signed, we kick off on Monday."),
                ]
            },
            {
                "topic": "Email & written communication",
                "words": [
                    ("Attached", "Во вложении"),
                    ("Please find", "Пожалуйста, найдите"),
                    ("As discussed", "Как обсуждали"),
                    ("Looking forward to", "С нетерпением жду"),
                    ("Best regards", "С уважением"),
                    ("Let me know", "Дайте знать"),
                    ("Feel free", "Не стесняйтесь"),
                    ("Reach out", "Связаться"),
                    ("Update", "Обновление"),
                    ("Clarify", "Уточнить"),
                ],
                "phrase": {
                    "text": "You've got mail.",
                    "movie": "You've Got Mail (1998)",
                    "meaning": "Письма важны. В B2B: хорошо написанный follow-up email часто закрывает сделку."
                },
                "dialogue": [
                    ("You", "Hi Sarah, as discussed, please find the proposal attached."),
                    ("You", "Let me know if you have any questions. Looking forward to working together."),
                    ("Client", "Thanks! I'll review it and get back to you by Friday."),
                ]
            },
            {
                "topic": "Building long-term relationships",
                "words": [
                    ("Relationship", "Отношения"),
                    ("Long-term", "Долгосрочный"),
                    ("Referral", "Рекомендация"),
                    ("Repeat client", "Постоянный клиент"),
                    ("Satisfaction", "Удовлетворённость"),
                    ("Recommend", "Рекомендовать"),
                    ("Network", "Сеть контактов"),
                    ("Testimonial", "Отзыв"),
                    ("Loyalty", "Лояльность"),
                    ("Collaboration", "Сотрудничество"),
                ],
                "phrase": {
                    "text": "It's not personal. It's strictly business.",
                    "movie": "The Godfather (1972)",
                    "meaning": "Бизнес отдельно от эмоций. Но в реальности: личные отношения делают бизнес крепче."
                },
                "dialogue": [
                    ("You", "We really enjoyed working on this project with you."),
                    ("Client", "Same here. The video turned out great."),
                    ("You", "We'd love to collaborate again. Do you have upcoming projects?"),
                ]
            },
        ]
    },
    # НЕДЕЛЯ 3 — AI и технологии
    {
        "title": "Week 3 — AI & Tech Vocabulary",
        "days": [
            {
                "topic": "AI video production terms",
                "words": [
                    ("AI-generated", "Созданный ИИ"),
                    ("Pipeline", "Пайплайн / Процесс"),
                    ("Automation", "Автоматизация"),
                    ("Render", "Рендеринг"),
                    ("Workflow", "Рабочий процесс"),
                    ("Algorithm", "Алгоритм"),
                    ("Generate", "Генерировать"),
                    ("Output", "Результат / Выход"),
                    ("Process", "Процесс"),
                    ("Efficient", "Эффективный"),
                ],
                "phrase": {
                    "text": "The machines are taking over.",
                    "movie": "Terminator 2 (1991)",
                    "meaning": "ИИ меняет правила. В твоём бизнесе: AI — это твоё конкурентное преимущество, не угроза."
                },
                "dialogue": [
                    ("Client", "How do you use AI in your production?"),
                    ("You", "We use AI to automate the editing workflow. It cuts delivery time by 60%."),
                    ("Client", "That sounds impressive. Can you show me an example?"),
                ]
            },
            {
                "topic": "Tech & tools",
                "words": [
                    ("Platform", "Платформа"),
                    ("Software", "Программное обеспечение"),
                    ("Tool", "Инструмент"),
                    ("Integration", "Интеграция"),
                    ("Cloud", "Облако"),
                    ("Upload", "Загрузить"),
                    ("Download", "Скачать"),
                    ("Access", "Доступ"),
                    ("Version", "Версия"),
                    ("Format", "Формат"),
                ],
                "phrase": {
                    "text": "Roads? Where we're going, we don't need roads.",
                    "movie": "Back to the Future (1985)",
                    "meaning": "Мы движемся в будущее. AI меняет индустрию — те кто адаптируется первыми, выигрывают."
                },
                "dialogue": [
                    ("Client", "What format do you deliver the final video in?"),
                    ("You", "We deliver in MP4, 4K resolution. We can also provide other formats if needed."),
                    ("Client", "Perfect. We'll need it compatible with our platform."),
                ]
            },
            {
                "topic": "Explaining your process",
                "words": [
                    ("Step", "Шаг"),
                    ("Phase", "Фаза"),
                    ("Pre-production", "Подготовительный этап"),
                    ("Production", "Производство"),
                    ("Post-production", "Постпроизводство"),
                    ("Script", "Сценарий"),
                    ("Storyboard", "Раскадровка"),
                    ("Edit", "Монтаж"),
                    ("Review", "Проверка"),
                    ("Final cut", "Финальная версия"),
                ],
                "phrase": {
                    "text": "Every frame counts.",
                    "movie": "Cinema Paradiso (1988)",
                    "meaning": "Каждый кадр важен. В клиентском разговоре: объясни что твой процесс гарантирует качество на каждом этапе."
                },
                "dialogue": [
                    ("Client", "Walk me through your production process."),
                    ("You", "We start with a brief and script, then storyboard, production, and editing."),
                    ("You", "You'll review at each phase before we move to the next step."),
                ]
            },
            {
                "topic": "Numbers & data",
                "words": [
                    ("Percentage", "Процент"),
                    ("Increase", "Увеличение"),
                    ("Reduce", "Уменьшить"),
                    ("ROI", "Возврат инвестиций"),
                    ("Metrics", "Показатели"),
                    ("Views", "Просмотры"),
                    ("Engagement", "Вовлечённость"),
                    ("Conversion", "Конверсия"),
                    ("Performance", "Производительность"),
                    ("Data-driven", "На основе данных"),
                ],
                "phrase": {
                    "text": "Numbers never lie.",
                    "movie": "Moneyball (2011)",
                    "meaning": "Данные не лгут. В продажах: подкрепляй слова цифрами — клиенты доверяют конкретике."
                },
                "dialogue": [
                    ("You", "Our AI pipeline reduces production costs by up to 40%."),
                    ("Client", "That's a significant number. How do you measure that?"),
                    ("You", "We track hours saved and compare to traditional production timelines."),
                ]
            },
            {
                "topic": "Presentations & demos",
                "words": [
                    ("Present", "Представить"),
                    ("Showcase", "Показать"),
                    ("Demonstrate", "Продемонстрировать"),
                    ("Example", "Пример"),
                    ("Case study", "Кейс"),
                    ("Sample", "Образец"),
                    ("Highlight", "Выделить"),
                    ("Feature", "Функция / Особенность"),
                    ("Benefit", "Преимущество"),
                    ("Advantage", "Преимущество"),
                ],
                "phrase": {
                    "text": "I'm going to make you an offer you can't refuse... in the form of a presentation.",
                    "movie": "Inspired by The Godfather",
                    "meaning": "Хорошая презентация — это оффер от которого не откажутся. Готовь её под конкретного клиента."
                },
                "dialogue": [
                    ("You", "I'd like to showcase some examples from our portfolio."),
                    ("Client", "Sure, go ahead."),
                    ("You", "This case study shows how we helped a fintech company increase engagement by 35%."),
                ]
            },
        ]
    },
    # НЕДЕЛЯ 4 — Продвинутые переговоры
    {
        "title": "Week 4 — Advanced Business English",
        "days": [
            {
                "topic": "Confident speaking",
                "words": [
                    ("Absolutely", "Абсолютно"),
                    ("Certainly", "Конечно"),
                    ("Definitely", "Определённо"),
                    ("Without a doubt", "Без сомнения"),
                    ("I'm confident that", "Я уверен, что"),
                    ("I believe", "Я считаю"),
                    ("In my experience", "По моему опыту"),
                    ("I'd recommend", "Я бы рекомендовал"),
                    ("The best approach", "Лучший подход"),
                    ("Clearly", "Очевидно"),
                ],
                "phrase": {
                    "text": "You talking to me?",
                    "movie": "Taxi Driver (1976)",
                    "meaning": "Уверенность в себе. В переговорах: говори прямо, смотри в глаза, не извиняйся за своё мнение."
                },
                "dialogue": [
                    ("Client", "Are you sure you can deliver by Friday?"),
                    ("You", "Absolutely. In my experience, this type of project takes 3 days maximum."),
                    ("Client", "That's reassuring. Let's proceed."),
                ]
            },
            {
                "topic": "Asking the right questions",
                "words": [
                    ("Could you clarify", "Не могли бы вы уточнить"),
                    ("What do you mean by", "Что вы имеете в виду под"),
                    ("Could you elaborate", "Не могли бы вы рассказать подробнее"),
                    ("What's your priority", "Каков ваш приоритет"),
                    ("What's the main challenge", "В чём главная проблема"),
                    ("How does that sound", "Как вам это звучит"),
                    ("Does that make sense", "Это понятно"),
                    ("Any questions", "Есть вопросы"),
                    ("What are your thoughts", "Каково ваше мнение"),
                    ("Is that clear", "Это ясно"),
                ],
                "phrase": {
                    "text": "Elementary, my dear Watson.",
                    "movie": "Sherlock Holmes (2009)",
                    "meaning": "Правильный вопрос раскрывает всё. В продажах: тот кто задаёт лучшие вопросы — контролирует разговор."
                },
                "dialogue": [
                    ("You", "What's your main challenge with video content right now?"),
                    ("Client", "We produce a lot but engagement is low."),
                    ("You", "Could you elaborate on what types of content you're producing?"),
                ]
            },
            {
                "topic": "Saying no professionally",
                "words": [
                    ("Unfortunately", "К сожалению"),
                    ("Not possible", "Невозможно"),
                    ("Outside our scope", "Вне нашего объёма"),
                    ("Alternative", "Альтернатива"),
                    ("Instead", "Вместо этого"),
                    ("Suggest", "Предложить"),
                    ("Capacity", "Возможности / Мощность"),
                    ("Priority", "Приоритет"),
                    ("Reconsider", "Пересмотреть"),
                    ("Adjust", "Скорректировать"),
                ],
                "phrase": {
                    "text": "I'm gonna make him an offer he can't refuse — and if he does, that's on him.",
                    "movie": "Inspired by The Godfather",
                    "meaning": "Умей отказывать. В бизнесе: знать когда сказать нет — признак профессионала, а не слабость."
                },
                "dialogue": [
                    ("Client", "Can you deliver 5 videos in one week?"),
                    ("You", "Unfortunately, that's outside our current capacity."),
                    ("You", "I'd suggest starting with 2 videos. We can scale up from there."),
                ]
            },
            {
                "topic": "Follow-up & relationship maintenance",
                "words": [
                    ("Check in", "Связаться / Проверить"),
                    ("Touch base", "Переговорить"),
                    ("Reconnect", "Восстановить связь"),
                    ("Update", "Обновить"),
                    ("Status", "Статус"),
                    ("Progress", "Прогресс"),
                    ("On track", "По плану"),
                    ("Delay", "Задержка"),
                    ("Ahead of schedule", "Впереди графика"),
                    ("Wrap up", "Завершить"),
                ],
                "phrase": {
                    "text": "I'll be back.",
                    "movie": "The Terminator (1984)",
                    "meaning": "Всегда возвращайся. В продажах: follow-up — это то что отличает закрытые сделки от потерянных."
                },
                "dialogue": [
                    ("You", "Hi Mark, just checking in on the proposal I sent last week."),
                    ("Client", "Oh yes, I've been meaning to touch base with you."),
                    ("You", "No rush. I just wanted to make sure everything was clear."),
                ]
            },
            {
                "topic": "Zoom & video call mastery",
                "words": [
                    ("Can you hear me", "Вы меня слышите"),
                    ("You're on mute", "Вы отключены"),
                    ("Share your screen", "Поделитесь экраном"),
                    ("Connection issue", "Проблема с соединением"),
                    ("Let me know if", "Дайте знать если"),
                    ("Drop off", "Отключиться"),
                    ("Rejoin", "Подключиться снова"),
                    ("Wrap up", "Завершить"),
                    ("Take notes", "Делать заметки"),
                    ("Action items", "Задачи / Пункты действий"),
                ],
                "phrase": {
                    "text": "We're not in Kansas anymore.",
                    "movie": "The Wizard of Oz (1939)",
                    "meaning": "Мы в новом мире. Zoom-звонки с международными клиентами — это новая реальность. Будь готов к техническим проблемам."
                },
                "dialogue": [
                    ("Client", "Sorry, I think I was on mute."),
                    ("You", "No problem. I was saying — let me share my screen to show the portfolio."),
                    ("Client", "Great. And can you send the action items after the call?"),
                    ("You", "Absolutely. I'll email a summary within an hour."),
                ]
            },
        ]
    },
]

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
            last_day TEXT,
            total_days INTEGER DEFAULT 0,
            current_week INTEGER DEFAULT 0,
            current_day INTEGER DEFAULT 0,
            quiz_state JSONB DEFAULT '{}'::jsonb,
            joined_at TIMESTAMP DEFAULT NOW()
        )
    """)
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
    await conn.execute("""
        INSERT INTO weekly_results (user_id, week_number, score, total) VALUES ($1, $2, $3, $4)
    """, user_id, week, score, total)
    await conn.close()

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
    if week_idx >= len(WEEKS):
        return None
    week = WEEKS[week_idx]
    if day_idx >= len(week["days"]):
        return None
    return week["days"][day_idx]

def generate_quiz(lesson, quiz_type=None):
    words = lesson["words"]
    if not quiz_type:
        quiz_type = random.choice(QUIZ_TYPES)
    
    word_en, word_ru = random.choice(words)
    
    if quiz_type == "translate_to_en":
        question = f"Переведи на английский:\n\n🇷🇺 *{word_ru}*"
        correct = word_en
        wrong_pool = [w[0] for w in words if w[0] != word_en]
        options = [correct] + random.sample(wrong_pool, min(3, len(wrong_pool)))
        random.shuffle(options)
        return {"question": question, "correct": correct, "options": options, "type": quiz_type}
    
    elif quiz_type == "translate_to_ru":
        question = f"Переведи на русский:\n\n🇬🇧 *{word_en}*"
        correct = word_ru
        wrong_pool = [w[1] for w in words if w[1] != word_ru]
        options = [correct] + random.sample(wrong_pool, min(3, len(wrong_pool)))
        random.shuffle(options)
        return {"question": question, "correct": correct, "options": options, "type": quiz_type}
    
    else:
        question = f"Переведи на английский:\n\n🇷🇺 *{word_ru}*"
        correct = word_en
        wrong_pool = [w[0] for w in words if w[0] != word_en]
        options = [correct] + random.sample(wrong_pool, min(3, len(wrong_pool)))
        random.shuffle(options)
        return {"question": question, "correct": correct, "options": options, "type": quiz_type}

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
        f"📅 Программа: 4 недели × 5 уроков\n"
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
    phrase = lesson["phrase"]
    
    words_text = "\n".join([f"• *{en}* — {ru}" for en, ru in lesson["words"]])
    dialogue_text = "\n".join([f"_{role}_: {line}" for role, line in lesson["dialogue"]])
    
    text = (
        f"📚 *{week['title']}*\n"
        f"День {day_idx + 1}/5 — {lesson['topic']}\n\n"
        f"*🔤 Слова дня:*\n{words_text}\n\n"
        f"*🎬 Фраза из фильма:*\n"
        f"_{phrase['text']}_\n"
        f"📽 {phrase['movie']}\n"
        f"💡 {phrase['meaning']}\n\n"
        f"*💬 Диалог:*\n{dialogue_text}"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎯 Пройти тест по уроку", callback_data=f"quiz_lesson")],
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
    
    week_idx = user["current_week"]
    day_idx = user["current_day"]
    lesson = get_current_lesson(week_idx, day_idx)
    
    if not lesson:
        await query.edit_message_text("Уроки закончились! Напиши /start.")
        return
    
    quiz = generate_quiz(lesson)
    
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"answer_{opt}_{quiz['correct']}")] 
                for opt in quiz["options"]]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu")])
    
    import json
    await update_user(user_id, quiz_state=json.dumps({
        "correct": quiz["correct"],
        "week": week_idx,
        "day": day_idx,
        "lesson_topic": lesson["topic"]
    }))
    
    await query.edit_message_text(
        f"🎯 *Тест*\n\n{quiz['question']}\n\nВыбери правильный ответ:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.replace("answer_", "", 1)
    parts = data.rsplit("_", 1)
    if len(parts) != 2:
        return
    chosen, correct = parts[0], parts[1]
    
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    if chosen == correct:
        xp_gain = 10
        new_xp = user["xp"] + xp_gain
        
        today = today_str()
        streak = user["streak"]
        total_days = user["total_days"]
        
        if user["last_day"] != today:
            yesterday = (datetime.now(TIMEZONE) - timedelta(days=1)).strftime("%Y-%m-%d")
            streak = streak + 1 if user["last_day"] == yesterday else 1
            total_days += 1
        
        # Day advances only once per day
        new_day = user["current_day"]
        new_week = user["current_week"]
        day_advanced = False
        
        if user["last_day"] != today:
            new_day = user["current_day"] + 1
            day_advanced = True
            if new_day >= 5:
                new_day = 0
                new_week += 1
        
        await update_user(user_id, 
            xp=new_xp, streak=streak, total_days=total_days,
            last_day=today, current_day=new_day, current_week=new_week
        )
        
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
        
        extra = ""
        if day_advanced and new_day == 0 and new_week > user["current_week"]:
            extra = f"\n\n🎉 *Неделя {user['current_week'] + 1} завершена!* Отличная работа!\nНачинаем неделю {new_week + 1}."
        elif day_advanced:
            extra = f"\n\n📅 День {new_day}/5 — продолжай завтра!"
        
        await query.edit_message_text(
            f"✅ *+{xp_gain} XP!*\n\n"
            f"{random.choice(motivations)}\n\n"
            f"{level_name}\n"
            f"{bar}  {new_xp} XP{extra}",
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
    
    total_words = (user["current_week"] * 5 + user["current_day"]) * 10
    week_name = WEEKS[min(user["current_week"], len(WEEKS)-1)]["title"]
    
    text = (
        f"📊 *Твой прогресс*\n\n"
        f"{level_name}\n"
        f"{bar}  {xp} XP\n\n"
        f"🔥 Серия: {user['streak']} дн.\n"
        f"📅 Всего дней: {user['total_days']}\n"
        f"📚 Слов изучено: ~{total_words}\n\n"
        f"📌 Текущая тема:\n{week_name}\n"
        f"День {user['current_day'] + 1}/5"
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
                week_idx = user["current_week"]
                day_idx = user["current_day"]
                lesson = get_current_lesson(week_idx, day_idx)
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

async def post_init(app):
    await init_db()
    asyncio.create_task(morning_reminder(app))

async def vocab_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    lines = ["📖 *Твой словарик*\n"]
    for w in range(week_idx + 1):
        week = WEEKS[w]
        max_day = day_idx if w == week_idx else 5
        if max_day == 0 and w == week_idx:
            continue
        lines.append(f"\n*{week['title']}*")
        for d in range(max_day):
            lesson = week["days"][d]
            lines.append(f"\n_{lesson['topic']}_")
            for en, ru in lesson["words"]:
                lines.append(f"• *{en}* — {ru}")
    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n\n_...показаны первые слова_"
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="menu")]]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def vocab_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all words learned so far"""
    user_id = update.effective_user.id if hasattr(update, 'effective_user') else update.callback_query.from_user.id
    
    if hasattr(update, 'message') and update.message:
        send = update.message.reply_text
    else:
        send = update.callback_query.edit_message_text
    
    user = await get_user(user_id)
    if not user:
        await send("Напиши /start чтобы начать.")
        return
    
    week_idx = user["current_week"]
    day_idx = user["current_day"]
    
    if week_idx == 0 and day_idx == 0:
        await send("Ты ещё не прошёл ни одного урока. Начни с /start → Урок дня!")
        return
    
    lines = ["📖 *Твой словарик*\n"]
    
    for w in range(week_idx + 1):
        week = WEEKS[w]
        max_day = day_idx if w == week_idx else 5
        
        if max_day == 0 and w == week_idx:
            continue
            
        lines.append(f"\n*{week['title']}*")
        
        for d in range(max_day):
            lesson = week["days"][d]
            lines.append(f"\n_{lesson['topic']}_")
            for en, ru in lesson["words"]:
                lines.append(f"• *{en}* — {ru}")
    
    text = "\n".join(lines)
    
    # Split if too long
    if len(text) > 4000:
        text = text[:4000] + "\n\n_...показаны первые слова_"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="menu")]]
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def review_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of completed lessons to review"""
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
            keyboard.append([InlineKeyboardButton(
                f"W{w+1}D{d+1} — {lesson['topic']}",
                callback_data=f"review_{w}_{d}"
            )])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu")])
    
    await query.edit_message_text(
        "📚 *Пройденные уроки*\n\nВыбери урок для повторения:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def review_lesson_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show a specific completed lesson for review"""
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
    words_text = "\n".join([f"• *{en}* — {ru}" for en, ru in lesson["words"]])
    dialogue_text = "\n".join([f"_{role}_: {line}" for role, line in lesson["dialogue"]])
    
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
    
    keyboard = [
        [InlineKeyboardButton("🎯 Тест по этому уроку", callback_data=f"quiz_review_{week_idx}_{day_idx}")],
        [InlineKeyboardButton("⬅️ К списку уроков", callback_data="review")],
        [InlineKeyboardButton("🏠 Меню", callback_data="menu")],
    ]
    
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def quiz_review_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quiz on a specific reviewed lesson"""
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
    
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"answer_{opt}_{quiz['correct']}")] 
                for opt in quiz["options"]]
    keyboard.append([InlineKeyboardButton("⬅️ К уроку", callback_data=f"review_{week_idx}_{day_idx}")])
    
    await query.edit_message_text(
        f"🎯 *Тест — повторение*\n\n{quiz['question']}\n\nВыбери правильный ответ:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(lesson_handler, pattern="^lesson$"))
    app.add_handler(CallbackQueryHandler(quiz_handler, pattern="^quiz_lesson$"))
    app.add_handler(CallbackQueryHandler(quiz_handler, pattern="^quiz$"))
    app.add_handler(CallbackQueryHandler(answer_handler, pattern="^answer_"))
    app.add_handler(CallbackQueryHandler(leaderboard_handler, pattern="^leaderboard$"))
    app.add_handler(CallbackQueryHandler(progress_handler, pattern="^progress$"))
    app.add_handler(CallbackQueryHandler(menu_handler, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(review_handler, pattern="^review$"))
    app.add_handler(CallbackQueryHandler(review_lesson_handler, pattern="^review_\\d+_\\d+$"))
    app.add_handler(CallbackQueryHandler(quiz_review_handler, pattern="^quiz_review_"))
    app.add_handler(CallbackQueryHandler(vocab_handler, pattern="^vocab$"))
    app.add_handler(CommandHandler("vocab", vocab_command))
    logger.info("Lumora English Bot started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
