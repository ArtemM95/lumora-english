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
                    ("Hello [хэлоу]", "Привет / Здравствуйте"),
                    ("My name is [май нэйм из]", "Меня зовут"),
                    ("I work as [ай вёрк эз]", "Я работаю как"),
                    ("Nice to meet you [найс ту мит ю]", "Рад познакомиться"),
                    ("Company [кампани]", "Компания"),
                    ("Producer [продьюсэр]", "Продюсер"),
                    ("Agency [эйдженси]", "Агентство"),
                    ("Project [проджект]", "Проект"),
                    ("Experience [икспириэнс]", "Опыт"),
                    ("Specialize in [спэшэлайз ин]", "Специализируюсь на"),
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
                    ("Video production [видео продакшн]", "Видеопроизводство"),
                    ("Content [контент]", "Контент"),
                    ("Corporate video [корпорэт видео]", "Корпоративное видео"),
                    ("Brand film [брэнд фильм]", "Брендовый фильм"),
                    ("Budget [баджит]", "Бюджет"),
                    ("Deadline [дедлайн]", "Дедлайн"),
                    ("Deliver [дэливэр]", "Доставить / Сдать"),
                    ("Quality [куолити]", "Качество"),
                    ("Client [клайент]", "Клиент"),
                    ("Portfolio [портфолио]", "Портфолио"),
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
                    ("Schedule a call [скэджул э кол]", "Назначить звонок"),
                    ("Available [эвэйлэбл]", "Доступен"),
                    ("Time zone [тайм зоун]", "Часовой пояс"),
                    ("Zoom call [зум кол]", "Звонок в Zoom"),
                    ("Follow up [фолоу ап]", "Связаться снова"),
                    ("Proposal [пропоузэл]", "Предложение"),
                    ("Brief [бриф]", "Бриф"),
                    ("Requirements [рикуайэрмэнтс]", "Требования"),
                    ("Discuss [дискас]", "Обсудить"),
                    ("Details [дитэйлз]", "Детали"),
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
                    ("Goal [гоул]", "Цель"),
                    ("Target audience [таргет одиэнс]", "Целевая аудитория"),
                    ("Message [мэсидж]", "Сообщение / Посыл"),
                    ("Vision [вижн]", "Видение"),
                    ("Feedback [фидбэк]", "Обратная связь"),
                    ("Revision [ривижн]", "Правка"),
                    ("Approval [эпрувэл]", "Утверждение"),
                    ("Timeline [тайmlайн]", "Сроки"),
                    ("Milestone [майлстоун]", "Этап / Веха"),
                    ("Scope [скоуп]", "Объём работ"),
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
                    ("Proposal [пропоузэл]", "Коммерческое предложение"),
                    ("Package [пэкидж]", "Пакет"),
                    ("Include [инклюд]", "Включать"),
                    ("Deliverable [дэливэрэбл]", "Результат работы"),
                    ("Turnaround [тёрнэраунд]", "Срок выполнения"),
                    ("Invest [инвест]", "Инвестировать"),
                    ("Value [вэлью]", "Ценность"),
                    ("Solution [солюшн]", "Решение"),
                    ("Offer [офэр]", "Предложение"),
                    ("Competitive [компэтитив]", "Конкурентный"),
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
                    ("Concern [консёрн]", "Беспокойство / Возражение"),
                    ("Understand [андэстэнд]", "Понимать"),
                    ("However [хауэвэр]", "Однако"),
                    ("Actually [эктюэли]", "На самом деле"),
                    ("Guarantee [гэрэнти]", "Гарантировать"),
                    ("Prove [прув]", "Доказать"),
                    ("Trust [траст]", "Доверие"),
                    ("Risk [риск]", "Риск"),
                    ("Confident [конфидэнт]", "Уверенный"),
                    ("Result [ризалт]", "Результат"),
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
                    ("Quote [куоут]", "Смета / Цитата"),
                    ("Rate [рэйт]", "Ставка"),
                    ("Invoice [инвойс]", "Счёт"),
                    ("Payment [пэймэнт]", "Оплата"),
                    ("Deposit [дипозит]", "Предоплата"),
                    ("Discount [дискаунт]", "Скидка"),
                    ("Negotiate [нэгоушиэйт]", "Переговоры / Торговаться"),
                    ("Contract [контрэкт]", "Договор"),
                    ("Terms [тёрмз]", "Условия"),
                    ("Per project [пэр проджект]", "За проект"),
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
                    ("Agreement [эгримэнт]", "Соглашение"),
                    ("Sign [сайн]", "Подписать"),
                    ("Move forward [мув форвэрд]", "Двигаться вперёд"),
                    ("Confirm [конфёрм]", "Подтвердить"),
                    ("Next steps [некст степс]", "Следующие шаги"),
                    ("Kick off [кик оф]", "Начать"),
                    ("Excited [иксайтид]", "Взволнован / В предвкушении"),
                    ("Partnership [партнэршип]", "Партнёрство"),
                    ("Looking forward [лукинг форвэрд]", "С нетерпением жду"),
                    ("Pleasure [плэжэр]", "Удовольствие"),
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
                    ("Attached [этэчт]", "Во вложении"),
                    ("Please find [плиз файнд]", "Пожалуйста, найдите"),
                    ("As discussed [эз дискаст]", "Как обсуждали"),
                    ("Looking forward to [лукинг форвэрд ту]", "С нетерпением жду"),
                    ("Best regards [бест ригардз]", "С уважением"),
                    ("Let me know [лет ми ноу]", "Дайте знать"),
                    ("Feel free [фил фри]", "Не стесняйтесь"),
                    ("Reach out [рич аут]", "Связаться"),
                    ("Update [апдэйт]", "Обновление"),
                    ("Clarify [клэрифай]", "Уточнить"),
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
                    ("Relationship [рилэйшншип]", "Отношения"),
                    ("Long-term [лонг тёрм]", "Долгосрочный"),
                    ("Referral [рифёрэл]", "Рекомендация"),
                    ("Repeat client [рипит клайент]", "Постоянный клиент"),
                    ("Satisfaction [сэтисфэкшн]", "Удовлетворённость"),
                    ("Recommend [рэкэмэнд]", "Рекомендовать"),
                    ("Network [нэтвёрк]", "Сеть контактов"),
                    ("Testimonial [тэстимониэл]", "Отзыв"),
                    ("Loyalty [лойэлти]", "Лояльность"),
                    ("Collaboration [колэборэйшн]", "Сотрудничество"),
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
                    ("AI-generated [эй-ай джэнэрэйтид]", "Созданный ИИ"),
                    ("Pipeline [пайплайн]", "Пайплайн / Процесс"),
                    ("Automation [отомэйшн]", "Автоматизация"),
                    ("Render [рэндэр]", "Рендеринг"),
                    ("Workflow [вёркфлоу]", "Рабочий процесс"),
                    ("Algorithm [элгэритм]", "Алгоритм"),
                    ("Generate [джэнэрэйт]", "Генерировать"),
                    ("Output [аутпут]", "Результат / Выход"),
                    ("Process [просэс]", "Процесс"),
                    ("Efficient [ифишэнт]", "Эффективный"),
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
                    ("Platform [плэтформ]", "Платформа"),
                    ("Software [софтвэр]", "Программное обеспечение"),
                    ("Tool [тул]", "Инструмент"),
                    ("Integration [интигрэйшн]", "Интеграция"),
                    ("Cloud [клауд]", "Облако"),
                    ("Upload [апloud]", "Загрузить"),
                    ("Download [даунloud]", "Скачать"),
                    ("Access [эксэс]", "Доступ"),
                    ("Version [вёржн]", "Версия"),
                    ("Format [формат]", "Формат"),
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
                    ("Step [стэп]", "Шаг"),
                    ("Phase [фэйз]", "Фаза"),
                    ("Pre-production [при-продакшн]", "Подготовительный этап"),
                    ("Production [продакшн]", "Производство"),
                    ("Post-production [поуст-продакшн]", "Постпроизводство"),
                    ("Script [скрипт]", "Сценарий"),
                    ("Storyboard [сторибоард]", "Раскадровка"),
                    ("Edit [эдит]", "Монтаж"),
                    ("Review [ривью]", "Проверка"),
                    ("Final cut [файнэл кат]", "Финальная версия"),
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
                    ("Percentage [пэрсэнтидж]", "Процент"),
                    ("Increase [инкрис]", "Увеличение"),
                    ("Reduce [ридьюс]", "Уменьшить"),
                    ("ROI [ар-оу-ай]", "Возврат инвестиций"),
                    ("Metrics [мэтрикс]", "Показатели"),
                    ("Views [вьюз]", "Просмотры"),
                    ("Engagement [ингэйджмэнт]", "Вовлечённость"),
                    ("Conversion [конвёршн]", "Конверсия"),
                    ("Performance [пэрформэнс]", "Производительность"),
                    ("Data-driven [дэйта дривэн]", "На основе данных"),
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
                    ("Present [призэнт]", "Представить"),
                    ("Showcase [шоукэйс]", "Показать"),
                    ("Demonstrate [дэмонстрэйт]", "Продемонстрировать"),
                    ("Example [игзампэл]", "Пример"),
                    ("Case study [кэйс стади]", "Кейс"),
                    ("Sample [сампэл]", "Образец"),
                    ("Highlight [хайлайт]", "Выделить"),
                    ("Feature [фичэр]", "Функция / Особенность"),
                    ("Benefit [бэнэфит]", "Преимущество"),
                    ("Advantage [эдвантидж]", "Преимущество"),
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
                    ("Absolutely [эбсолютли]", "Абсолютно"),
                    ("Certainly [сёртэнли]", "Конечно"),
                    ("Definitely [дэфинэтли]", "Определённо"),
                    ("Without a doubt [видаут э даут]", "Без сомнения"),
                    ("I'm confident that [айм конфидэнт дэт]", "Я уверен, что"),
                    ("I believe [ай билив]", "Я считаю"),
                    ("In my experience [ин май икспириэнс]", "По моему опыту"),
                    ("I'd recommend [айд рэкэмэнд]", "Я бы рекомендовал"),
                    ("The best approach [дэ бэст эпроуч]", "Лучший подход"),
                    ("Clearly [клирли]", "Очевидно"),
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
                    ("Could you clarify [куд ю клэрифай]", "Не могли бы вы уточнить"),
                    ("What do you mean by [уот ду ю мин бай]", "Что вы имеете в виду под"),
                    ("Could you elaborate [куд ю илэборэйт]", "Подробнее расскажите"),
                    ("What's your priority [уотс ёр прайорити]", "Каков ваш приоритет"),
                    ("What's the main challenge [уотс дэ мэйн челиндж]", "В чём главная проблема"),
                    ("How does that sound [хау даз дэт саунд]", "Как вам это звучит"),
                    ("Does that make sense [даз дэт мэйк сэнс]", "Это понятно"),
                    ("Any questions [эни куэсчэнс]", "Есть вопросы"),
                    ("What are your thoughts [уот ар ёр соутс]", "Каково ваше мнение"),
                    ("Is that clear [из дэт клир]", "Это ясно"),
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
                    ("Unfortunately [анфорчунэтли]", "К сожалению"),
                    ("Not possible [нот пасэбл]", "Невозможно"),
                    ("Outside our scope [аутсайд аур скоуп]", "Вне нашего объёма"),
                    ("Alternative [олтёрнэтив]", "Альтернатива"),
                    ("Instead [инстэд]", "Вместо этого"),
                    ("Suggest [сэджэст]", "Предложить"),
                    ("Capacity [кэпэсити]", "Возможности / Мощность"),
                    ("Priority [прайорити]", "Приоритет"),
                    ("Reconsider [рикэнсидэр]", "Пересмотреть"),
                    ("Adjust [эджаст]", "Скорректировать"),
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
                    ("Check in [чек ин]", "Связаться / Проверить"),
                    ("Touch base [тач бэйс]", "Переговорить"),
                    ("Reconnect [риконэкт]", "Восстановить связь"),
                    ("Update [апдэйт]", "Обновить"),
                    ("Status [стэйтэс]", "Статус"),
                    ("Progress [прогрэс]", "Прогресс"),
                    ("On track [он трэк]", "По плану"),
                    ("Delay [дилэй]", "Задержка"),
                    ("Ahead of schedule [эхэд оф скэджул]", "Впереди графика"),
                    ("Wrap up [рэп ап]", "Завершить"),
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
                    ("Can you hear me [кэн ю хир ми]", "Вы меня слышите"),
                    ("You're on mute [юр он мьют]", "Вы отключены"),
                    ("Share your screen [шэр ёр скрин]", "Поделитесь экраном"),
                    ("Connection issue [конэкшн ишью]", "Проблема с соединением"),
                    ("Let me know if [лет ми ноу иф]", "Дайте знать если"),
                    ("Drop off [дроп оф]", "Отключиться"),
                    ("Rejoin [риджойн]", "Подключиться снова"),
                    ("Wrap up [рэп ап]", "Завершить"),
                    ("Take notes [тэйк ноутс]", "Делать заметки"),
                    ("Action items [экшн айтэмс]", "Задачи / Пункты действий"),
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
    # НЕДЕЛЯ 5 — Презентации и питчи
    {
        "title": "Week 5 — Presenting & Pitching",
        "days": [
            {
                "topic": "Opening a presentation",
                "words": [
                    ("Good morning everyone [гуд морнинг эвриуан]", "Доброе утро всем"),
                    ("Thank you for joining [сэнк ю фор джойнинг]", "Спасибо что присоединились"),
                    ("Today I'd like to [тудэй айд лайк ту]", "Сегодня я хотел бы"),
                    ("Let me start by [лет ми старт бай]", "Позвольте начать с"),
                    ("The agenda [дэ эджэнда]", "Повестка дня"),
                    ("Briefly [брифли]", "Кратко"),
                    ("Overview [оувэрвью]", "Обзор"),
                    ("Key points [ки поинтс]", "Ключевые пункты"),
                    ("Structure [стракчэр]", "Структура"),
                    ("Introduction [интрэдакшн]", "Введение"),
                ],
                "phrase": {"text": "Here's looking at you, kid.", "movie": "Casablanca (1942)", "meaning": "Держи контакт с аудиторией. На презентации: смотри на людей, не на слайды."},
                "dialogue": [("You", "Good morning everyone. Thank you for joining today."), ("You", "I'd like to present our AI video production capabilities."), ("Client", "Great, we're excited to hear more.")]
            },
            {
                "topic": "Describing your USP",
                "words": [
                    ("Unique [юник]", "Уникальный"),
                    ("Distinguish [дистингуиш]", "Отличать"),
                    ("Competitor [компэтитэр]", "Конкурент"),
                    ("Faster [фастэр]", "Быстрее"),
                    ("Cost-effective [кост-эфэктив]", "Экономически эффективный"),
                    ("Scalable [скэйлэбл]", "Масштабируемый"),
                    ("Proven [прувэн]", "Проверенный"),
                    ("Track record [трэк рэкорд]", "Послужной список"),
                    ("Expertise [экспёртиз]", "Экспертиза"),
                    ("Cutting-edge [катинг-эдж]", "Передовой"),
                ],
                "phrase": {"text": "We're the best and we know it.", "movie": "Mad Men inspired", "meaning": "Говори о преимуществах уверенно. Скромность в питче — враг продаж."},
                "dialogue": [("You", "What distinguishes us is our AI pipeline."), ("You", "We deliver videos 3x faster at 40% lower cost."), ("Client", "Impressive. Can you share examples?")]
            },
            {
                "topic": "Handling questions",
                "words": [
                    ("Great question [грэйт куэсчэн]", "Отличный вопрос"),
                    ("I'm glad you asked [айм глэд ю аскт]", "Рад что спросили"),
                    ("To answer that [ту ансэр дэт]", "Чтобы ответить на это"),
                    ("In other words [ин адэр вёрдз]", "Другими словами"),
                    ("Let me clarify [лет ми клэрифай]", "Позвольте уточнить"),
                    ("That's a fair point [дэтс э фэр поинт]", "Справедливое замечание"),
                    ("I'll get back to you [айл гет бэк ту ю]", "Вернусь с ответом"),
                    ("Off the top of my head [оф дэ топ оф май хэд]", "Навскидку"),
                    ("To summarize [ту самэрайз]", "Подводя итог"),
                    ("Any other questions [эни адэр куэсчэнс]", "Ещё вопросы"),
                ],
                "phrase": {"text": "I love it when a plan comes together.", "movie": "The A-Team (2010)", "meaning": "Когда Q&A проходит гладко — это результат подготовки."},
                "dialogue": [("Client", "How do you ensure quality with AI?"), ("You", "Great question. We have human review at every stage."), ("You", "AI speeds up the process but humans control quality.")]
            },
            {
                "topic": "Closing a pitch",
                "words": [
                    ("To wrap up [ту рэп ап]", "Подводя итог"),
                    ("In conclusion [ин конклюжн]", "В заключение"),
                    ("Call to action [кол ту экшн]", "Призыв к действию"),
                    ("Next steps [некст степс]", "Следующие шаги"),
                    ("Proposal [пропоузэл]", "Предложение"),
                    ("Decision [дисижн]", "Решение"),
                    ("Timeline [тайmlайн]", "Сроки"),
                    ("Ready to proceed [рэди ту просид]", "Готов к работе"),
                    ("Questions [куэсчэнс]", "Вопросы"),
                    ("Thank you [сэнк ю]", "Спасибо"),
                ],
                "phrase": {"text": "Make it so.", "movie": "Star Trek: TNG", "meaning": "Короткий уверенный призыв к действию. Лучшие питчи заканчиваются чётким следующим шагом."},
                "dialogue": [("You", "To wrap up — we can deliver your first video in 7 days."), ("You", "Are you ready to proceed?"), ("Client", "Yes. Send us the proposal.")]
            },
            {
                "topic": "Storytelling in business",
                "words": [
                    ("Story [стори]", "История"),
                    ("Challenge [челиндж]", "Вызов / Проблема"),
                    ("Solution [солюшн]", "Решение"),
                    ("Outcome [аутком]", "Результат"),
                    ("Impact [импакт]", "Влияние"),
                    ("Transformation [трансформэйшн]", "Трансформация"),
                    ("Before and after [бифор энд афтэр]", "До и после"),
                    ("Journey [джёрни]", "Путь"),
                    ("Success [саксэс]", "Успех"),
                    ("Inspire [инспайэр]", "Вдохновлять"),
                ],
                "phrase": {"text": "Stories are data with a soul.", "movie": "Brené Brown TED Talk", "meaning": "Данные убеждают разум. История убеждает сердце. Используй оба в питче."},
                "dialogue": [("You", "Let me share a quick story about one of our clients."), ("You", "They needed content fast. After our AI pipeline — 5x more content at half the cost."), ("Client", "That's exactly our situation.")]
            },
        ]
    },
    # НЕДЕЛЯ 6 — Сложные ситуации
    {
        "title": "Week 6 — Difficult Situations",
        "days": [
            {
                "topic": "When client is unhappy",
                "words": [
                    ("Apologize [эполэджайз]", "Извиниться"),
                    ("Responsibility [риспонсэбилити]", "Ответственность"),
                    ("Fix [фикс]", "Исправить"),
                    ("Resolve [ризолв]", "Решить"),
                    ("Compensate [компэнсэйт]", "Компенсировать"),
                    ("Miscommunication [мискомьюникэйшн]", "Недопонимание"),
                    ("Expectation [экспэктэйшн]", "Ожидание"),
                    ("Disappoint [дисэпойнт]", "Разочаровать"),
                    ("Assure [эшуэр]", "Заверить"),
                    ("Priority [прайорити]", "Приоритет"),
                ],
                "phrase": {"text": "Stay calm and carry on.", "movie": "WWII British poster", "meaning": "Не паникуй когда клиент недоволен — спокойствие решает проблемы."},
                "dialogue": [("Client", "This is not what we discussed. I'm disappointed."), ("You", "I completely understand and apologize for the miscommunication."), ("You", "Let me make this right. Revised version by tomorrow.")]
            },
            {
                "topic": "Managing scope creep",
                "words": [
                    ("Scope [скоуп]", "Объём работ"),
                    ("Additional [эдишэнэл]", "Дополнительный"),
                    ("Out of scope [аут оф скоуп]", "Вне объёма"),
                    ("Extra charge [экстра чардж]", "Дополнительная плата"),
                    ("Amendment [эмэндмэнт]", "Поправка"),
                    ("Original agreement [оридженэл эгримэнт]", "Первоначальное соглашение"),
                    ("Change request [чэйндж рикуэст]", "Запрос на изменение"),
                    ("Quote [куоут]", "Смета"),
                    ("Adjust [эджаст]", "Скорректировать"),
                    ("Boundaries [баундэриз]", "Границы"),
                ],
                "phrase": {"text": "Good fences make good neighbours.", "movie": "Robert Frost", "meaning": "Чёткие границы объёма работ — основа хороших клиентских отношений."},
                "dialogue": [("Client", "Can you also add subtitles and a shorter version?"), ("You", "Those are outside our original scope."), ("You", "I'd be happy to quote the extra work separately.")]
            },
            {
                "topic": "Delayed payments",
                "words": [
                    ("Overdue [оувэрдью]", "Просроченный"),
                    ("Reminder [риmaйндэр]", "Напоминание"),
                    ("Outstanding [аутстэндинг]", "Неоплаченный"),
                    ("Invoice [инвойс]", "Счёт"),
                    ("Due date [дью дэйт]", "Срок оплаты"),
                    ("Follow up [фолоу ап]", "Связаться снова"),
                    ("Payment terms [пэймэнт тёрмз]", "Условия оплаты"),
                    ("Late fee [лэйт фи]", "Штраф за просрочку"),
                    ("Settle [сэтл]", "Урегулировать"),
                    ("Appreciate [эпришиэйт]", "Ценить"),
                ],
                "phrase": {"text": "Show me the money!", "movie": "Jerry Maguire (1996)", "meaning": "Следи за оплатами — даже лучшие клиенты забывают платить вовремя."},
                "dialogue": [("You", "Hi, I wanted to follow up on invoice 102. It's currently outstanding."), ("Client", "Sorry about that! I'll process it today."), ("You", "Thank you, I appreciate it.")]
            },
            {
                "topic": "Setting professional boundaries",
                "words": [
                    ("Boundary [баундэри]", "Граница"),
                    ("Availability [эвэйлэбилити]", "Доступность"),
                    ("Business hours [бизнэс ауэрз]", "Рабочие часы"),
                    ("Response time [риспонс тайм]", "Время ответа"),
                    ("Urgent [ёрджэнт]", "Срочный"),
                    ("Reasonable [ризэнэбл]", "Разумный"),
                    ("Respect [риспэкт]", "Уважать"),
                    ("Policy [полиси]", "Политика"),
                    ("Workload [вёрклоуд]", "Рабочая нагрузка"),
                    ("Balance [бэлэнс]", "Баланс"),
                ],
                "phrase": {"text": "Respect yourself enough to say no.", "movie": "Wisdom", "meaning": "Профессионал умеет говорить нет — это признак уверенности, не слабости."},
                "dialogue": [("Client", "Can you call me at 10pm tonight?"), ("You", "I'm not available after 7pm."), ("You", "I'd be happy to schedule a call tomorrow morning instead.")]
            },
            {
                "topic": "Offering alternatives",
                "words": [
                    ("Decline [диклайн]", "Отказать"),
                    ("Alternative [олтёрнэтив]", "Альтернатива"),
                    ("Instead [инстэд]", "Вместо этого"),
                    ("Suggest [сэджэст]", "Предложить"),
                    ("Compromise [компромайз]", "Компромисс"),
                    ("Feasible [физэбл]", "Осуществимый"),
                    ("Realistic [риэлистик]", "Реалистичный"),
                    ("Limitations [лимитэйшэнс]", "Ограничения"),
                    ("Best option [бэст опшн]", "Лучший вариант"),
                    ("Work around [вёрк эраунд]", "Обходное решение"),
                ],
                "phrase": {"text": "When one door closes, another opens.", "movie": "Alexander Graham Bell", "meaning": "Отказывая в одном — предлагай альтернативу. Клиент запомнит решение, а не отказ."},
                "dialogue": [("Client", "We need this in 24 hours."), ("You", "That's not feasible right now."), ("You", "However, I can deliver a quality draft in 48 hours. Would that work?")]
            },
        ]
    },
    # НЕДЕЛЯ 7 — Управление проектами
    {
        "title": "Week 7 — Project Management",
        "days": [
            {
                "topic": "Kickoff meeting",
                "words": [
                    ("Kickoff [кикоф]", "Начало проекта"),
                    ("Stakeholder [стэйкхолдэр]", "Заинтересованная сторона"),
                    ("Objective [обджэктив]", "Цель"),
                    ("Deliverable [дэливэрэбл]", "Результат работы"),
                    ("Responsibility [риспонсэбилити]", "Ответственность"),
                    ("Point of contact [поинт оф контэкт]", "Контактное лицо"),
                    ("Sign off [сайн оф]", "Утвердить"),
                    ("Workflow [вёркфлоу]", "Рабочий процесс"),
                    ("Milestone [майлстоун]", "Этап"),
                    ("Expectations [экспэктэйшнс]", "Ожидания"),
                ],
                "phrase": {"text": "Houston, we have a problem.", "movie": "Apollo 13 (1995)", "meaning": "Лучше выявить проблему на кикоффе чем в конце проекта."},
                "dialogue": [("You", "Welcome to the kickoff. Let's align on objectives."), ("You", "Who is the main point of contact on your side?"), ("Client", "That would be me. I'll sign off on all deliverables.")]
            },
            {
                "topic": "Project updates",
                "words": [
                    ("On schedule [он скэджул]", "По графику"),
                    ("Behind schedule [бихайнд скэджул]", "Позади графика"),
                    ("Ahead of schedule [эхэд оф скэджул]", "Впереди графика"),
                    ("Update [апдэйт]", "Обновление"),
                    ("Status report [стэйтэс рипорт]", "Отчёт о статусе"),
                    ("Blocker [блокэр]", "Блокирующая проблема"),
                    ("Dependency [дипэндэнси]", "Зависимость"),
                    ("Risk [риск]", "Риск"),
                    ("Mitigation [митигэйшн]", "Снижение риска"),
                    ("ETA [и-ти-эй]", "Ожидаемая дата сдачи"),
                ],
                "phrase": {"text": "Keep moving forward.", "movie": "Meet the Robinsons (2007)", "meaning": "Даже если тормозит — информируй клиента и двигайся вперёд."},
                "dialogue": [("You", "Quick update — we're on schedule."), ("You", "First draft ready by Thursday as planned."), ("Client", "Perfect. Let us know if there are blockers.")]
            },
            {
                "topic": "Feedback and revisions",
                "words": [
                    ("Feedback [фидбэк]", "Обратная связь"),
                    ("Revision [ривижн]", "Правка"),
                    ("Round [раунд]", "Раунд"),
                    ("Incorporate [инкорпорэйт]", "Включить"),
                    ("Amendment [эмэндмэнт]", "Поправка"),
                    ("Version [вёржн]", "Версия"),
                    ("Final [файнэл]", "Финальный"),
                    ("Approval [эпрувэл]", "Утверждение"),
                    ("Note [ноут]", "Заметка"),
                    ("Turnaround [тёрнэраунд]", "Срок выполнения"),
                ],
                "phrase": {"text": "The first draft is just the beginning.", "movie": "Writing wisdom", "meaning": "Первый вариант никогда не финальный. Управляй ожиданиями с самого начала."},
                "dialogue": [("Client", "Here's our feedback on version 1."), ("You", "Thank you. I'll incorporate all notes in the next revision."), ("You", "Turnaround is 48 hours. Does that work?")]
            },
            {
                "topic": "Deadline management",
                "words": [
                    ("Deadline [дедлайн]", "Крайний срок"),
                    ("Extension [икстэншн]", "Продление"),
                    ("Rush [раш]", "Срочно"),
                    ("Buffer [бафэр]", "Запас времени"),
                    ("Realistic [риэлистик]", "Реалистичный"),
                    ("Commit [комит]", "Взять обязательство"),
                    ("Deliver [дэливэр]", "Сдать"),
                    ("Overrun [оувэррун]", "Превысить сроки"),
                    ("Flexible [флэксэбл]", "Гибкий"),
                    ("Hard deadline [хард дедлайн]", "Жёсткий дедлайн"),
                ],
                "phrase": {"text": "Time is money.", "movie": "Benjamin Franklin", "meaning": "В продакшне время буквально равно деньгам. Управляй дедлайнами как профессионал."},
                "dialogue": [("Client", "Is Friday a hard deadline?"), ("You", "Yes, I can commit to Friday delivery."), ("You", "I always build in a buffer so there are no surprises.")]
            },
            {
                "topic": "Project closure",
                "words": [
                    ("Wrap up [рэп ап]", "Завершить"),
                    ("Final delivery [файнэл дэливэри]", "Финальная сдача"),
                    ("Assets [эссэтс]", "Материалы"),
                    ("Hand over [хэнд оувэр]", "Передать"),
                    ("Archive [архив]", "Архив"),
                    ("Lessons learned [лэсэнс лёрнд]", "Усвоенные уроки"),
                    ("Testimonial [тэстимониэл]", "Отзыв"),
                    ("Referral [рифёрэл]", "Рекомендация"),
                    ("Retainer [ритэйнэр]", "Абонемент"),
                    ("Ongoing [онгоинг]", "Продолжающийся"),
                ],
                "phrase": {"text": "That's a wrap!", "movie": "Film set expression", "meaning": "Классическая фраза со съёмочной площадки. Используй при финальной сдаче."},
                "dialogue": [("You", "That's a wrap! Here are all final assets."), ("Client", "We're very happy with the result."), ("You", "Thank you! Would you be open to leaving a testimonial?")]
            },
        ]
    },
    # НЕДЕЛИ 8-16 — продолжение
    {
        "title": "Week 8 — Marketing & Content Strategy",
        "days": [
            {"topic": "Content marketing basics", "words": [("Content marketing [контент маркетинг]", "Контент-маркетинг"), ("Brand awareness [брэнд эвэрнэс]", "Осведомлённость о бренде"), ("Lead generation [лид джэнэрэйшн]", "Лидогенерация"), ("Funnel [фанэл]", "Воронка"), ("Touchpoint [тачпоинт]", "Точка контакта"), ("Audience [одиэнс]", "Аудитория"), ("Persona [пёрсона]", "Персона покупателя"), ("Journey [джёрни]", "Путь клиента"), ("Conversion [конвёршн]", "Конверсия"), ("Retention [ритэншн]", "Удержание")], "phrase": {"text": "Content is king.", "movie": "Bill Gates, 1996", "meaning": "Контент правит. AI-контент правит ещё быстрее и дешевле."}, "dialogue": [("Client", "We need more content but have a limited budget."), ("You", "AI production lets us scale content without scaling costs."), ("You", "We can produce 10x more within your budget.")]},
            {"topic": "Video marketing terms", "words": [("Explainer video [эксплэйнэр видео]", "Объясняющее видео"), ("Testimonial video [тэстимониэл видео]", "Видео-отзыв"), ("Product demo [продакт демо]", "Демонстрация продукта"), ("Brand video [брэнд видео]", "Брендовое видео"), ("Case study video [кэйс стади видео]", "Видео-кейс"), ("Tutorial [тьюториэл]", "Обучающее видео"), ("Webinar [вэбинар]", "Вебинар"), ("Live stream [лайв стрим]", "Прямая трансляция"), ("Short form [шорт форм]", "Короткий формат"), ("Long form [лонг форм]", "Длинный формат")], "phrase": {"text": "A picture is worth a thousand words.", "movie": "Ancient proverb", "meaning": "Видео стоит миллион слов. Именно поэтому твой бизнес самый ценный для клиентов."}, "dialogue": [("Client", "What type of video works best for us?"), ("You", "For B2B SaaS, I'd recommend an explainer video first."), ("You", "Then testimonial videos as you get clients.")]},
            {"topic": "Social media distribution", "words": [("Platform [плэтформ]", "Платформа"), ("Organic [органик]", "Органический"), ("Paid [пэйд]", "Платный"), ("Algorithm [элгэритм]", "Алгоритм"), ("Reach [рич]", "Охват"), ("Impressions [импрэшэнс]", "Показы"), ("Click-through rate [клик-фру рэйт]", "Кликабельность"), ("Subscribe [сэбскрайб]", "Подписаться"), ("Share [шэр]", "Поделиться"), ("Viral [вайрэл]", "Вирусный")], "phrase": {"text": "Build it and they will come.", "movie": "Field of Dreams (1989)", "meaning": "Хороший контент находит аудиторию. Дистрибуция помогает найти её быстрее."}, "dialogue": [("Client", "Where should we distribute the video?"), ("You", "LinkedIn for B2B reach, YouTube for organic growth."), ("You", "We can cut shorter versions for Instagram too.")]},
            {"topic": "Analytics and reporting", "words": [("Analytics [энэлитикс]", "Аналитика"), ("Report [рипорт]", "Отчёт"), ("KPI [кэй-пи-ай]", "Ключевой показатель"), ("Benchmark [бэнчмарк]", "Эталон"), ("Dashboard [дэшборд]", "Дашборд"), ("Data [дэйта]", "Данные"), ("Insight [инсайт]", "Инсайт"), ("Trend [трэнд]", "Тренд"), ("Measure [мэжэр]", "Измерять"), ("Optimize [оптимайз]", "Оптимизировать")], "phrase": {"text": "What gets measured gets managed.", "movie": "Peter Drucker", "meaning": "Без аналитики нет роста. Предлагай клиентам отчёты — это повышает ценность работы."}, "dialogue": [("Client", "How will we know if the video is working?"), ("You", "We'll track views, engagement, and conversion."), ("You", "I'll send a monthly analytics report.")]},
            {"topic": "Content strategy", "words": [("Strategy [стрэтэджи]", "Стратегия"), ("Roadmap [роудмэп]", "Дорожная карта"), ("Quarter [куортэр]", "Квартал"), ("Annual [эниюэл]", "Ежегодный"), ("Initiative [инишэтив]", "Инициатива"), ("Prioritize [прайоритайз]", "Расставить приоритеты"), ("Resource [ризорс]", "Ресурс"), ("Allocate [элокэйт]", "Распределить"), ("Strategic [стрэтиджик]", "Стратегический"), ("Vision [вижн]", "Видение")], "phrase": {"text": "Plans are nothing; planning is everything.", "movie": "Eisenhower", "meaning": "Процесс планирования важнее самого плана. Предлагай клиентам стратегические сессии."}, "dialogue": [("You", "Have you thought about a content strategy for Q3?"), ("Client", "Not really. We've been reactive."), ("You", "I'd love to help you build a quarterly video roadmap.")]},
        ]
    },
    {"title": "Week 9 — Advanced Production", "days": [
        {"topic": "Pre-production", "words": [("Concept [концэпт]", "Концепция"), ("Treatment [тритмэнт]", "Тритмент"), ("Shot list [шот лист]", "Список кадров"), ("Location [локэйшн]", "Локация"), ("Casting [кастинг]", "Кастинг"), ("Talent [тэлэнт]", "Актёр"), ("Voice over [войс оувэр]", "Закадровый голос"), ("Narration [нэрэйшн]", "Повествование"), ("Mood board [муд борд]", "Мудборд"), ("References [рэфэрэнсэс]", "Референсы")], "phrase": {"text": "Lights, camera, action!", "movie": "Classic film expression", "meaning": "Подготовка + инструменты + действие = результат."}, "dialogue": [("Client", "What do you need to start?"), ("You", "A brief, brand guidelines, and references."), ("You", "I'll prepare a treatment within 2 days.")]},
        {"topic": "Post-production", "words": [("Editing [эдитинг]", "Монтаж"), ("Color grading [колэр грэйдинг]", "Цветокоррекция"), ("Sound design [саунд дизайн]", "Звуковое оформление"), ("Motion graphics [моушн грэфикс]", "Моушн-графика"), ("Visual effects [вижуэл ифэктс]", "Визуальные эффекты"), ("Subtitles [сабтайтлс]", "Субтитры"), ("Export [экспорт]", "Экспорт"), ("Compression [компрэшн]", "Сжатие"), ("Resolution [рэзолюшн]", "Разрешение"), ("Aspect ratio [эспэкт рэйшо]", "Соотношение сторон")], "phrase": {"text": "The magic is in the edit.", "movie": "Walter Murch", "meaning": "Монтаж — где рождается история. Объясняй клиентам ценность постпродакшна."}, "dialogue": [("Client", "Why does post-production take so long?"), ("You", "Color grading, sound design, and motion graphics each take time."), ("You", "With our AI workflow, we've cut this by 50%.")]},
        {"topic": "Technical specs", "words": [("Frame rate [фрэйм рэйт]", "Частота кадров"), ("Codec [кодэк]", "Кодек"), ("Bitrate [битрэйт]", "Битрейт"), ("File size [файл сайз]", "Размер файла"), ("Delivery format [дэливэри формат]", "Формат сдачи"), ("Master file [мастэр файл]", "Мастер-файл"), ("Proxy [прокси]", "Прокси"), ("Raw footage [ро футидж]", "Исходники"), ("Archive [архив]", "Архив"), ("4K [фор-кэй]", "4K разрешение")], "phrase": {"text": "The devil is in the details.", "movie": "German proverb", "meaning": "Технические детали решают качество. Всегда уточняй спецификации заранее."}, "dialogue": [("Client", "What format will you deliver in?"), ("You", "Master in 4K ProRes, plus H.264 for web."), ("You", "What are your platform requirements?")]},
        {"topic": "AI workflow", "words": [("Prompt [промпт]", "Запрос / Промпт"), ("Generate [джэнэрэйт]", "Генерировать"), ("Iteration [итэрэйшн]", "Итерация"), ("Refine [рифайн]", "Улучшить"), ("Upscale [апскэйл]", "Улучшить качество"), ("Synthesize [синсэсайз]", "Синтезировать"), ("Model [модэл]", "Модель"), ("Training [трэйнинг]", "Обучение"), ("Output quality [аутпут куолити]", "Качество результата"), ("Human review [хьюмэн ривью]", "Проверка человеком")], "phrase": {"text": "It's not magic, it's technology.", "movie": "Arthur C. Clarke inspired", "meaning": "AI кажется магией клиентам. Объясняй процесс просто — это строит доверие."}, "dialogue": [("Client", "How does AI work in your production?"), ("You", "We use AI to generate visuals based on your script."), ("You", "Then our team refines and quality-checks every frame.")]},
        {"topic": "Client presentations", "words": [("Showcase [шоукэйс]", "Показать"), ("Demonstrate [дэмонстрэйт]", "Продемонстрировать"), ("Case study [кэйс стади]", "Кейс"), ("Sample [сампэл]", "Образец"), ("Highlight [хайлайт]", "Выделить"), ("Feature [фичэр]", "Функция"), ("Benefit [бэнэфит]", "Преимущество"), ("Advantage [эдвантидж]", "Преимущество"), ("Portfolio [портфолио]", "Портфолио"), ("Demo reel [демо рил]", "Демо-ролик")], "phrase": {"text": "Seeing is believing.", "movie": "English proverb", "meaning": "Покажи работу — не рассказывай о ней. Портфолио продаёт лучше любых слов."}, "dialogue": [("You", "I'd like to showcase some examples from our portfolio."), ("Client", "Sure, go ahead."), ("You", "This case study shows how we increased engagement by 35%.")]},
    ]},
    {"title": "Week 10 — Finance & Contracts", "days": [
        {"topic": "Pricing models", "words": [("Fixed price [фикст прайс]", "Фиксированная цена"), ("Hourly rate [аурли рэйт]", "Почасовая ставка"), ("Retainer [ритэйнэр]", "Абонентская плата"), ("Package deal [пэкидж дил]", "Пакетное предложение"), ("Custom quote [кастом куоут]", "Индивидуальная смета"), ("Milestone payment [майлстоун пэймэнт]", "Поэтапная оплата"), ("Upfront [апфронт]", "Авансом"), ("Upon delivery [эпон дэливэри]", "При сдаче"), ("Net 30 [нет 30]", "Оплата за 30 дней"), ("Recurring [рикёринг]", "Регулярный")], "phrase": {"text": "Price is what you pay. Value is what you get.", "movie": "Warren Buffett", "meaning": "Не конкурируй по цене — конкурируй по ценности. Объясняй ROI клиента."}, "dialogue": [("Client", "Do you offer monthly retainers?"), ("You", "Yes. Our retainer includes 4 videos per month at a fixed rate."), ("You", "It's more cost-effective than individual project pricing.")]},
        {"topic": "Contract essentials", "words": [("Agreement [эгримэнт]", "Соглашение"), ("Terms and conditions [тёрмс энд кэндишэнс]", "Условия"), ("Intellectual property [интэлэктюэл проперти]", "Интеллектуальная собственность"), ("Confidentiality [конфидэншиэлити]", "Конфиденциальность"), ("Liability [лаябилити]", "Ответственность"), ("Termination [тёрминэйшн]", "Расторжение"), ("Clause [клоз]", "Пункт"), ("Binding [байндинг]", "Обязывающий"), ("Execute [экзэкьют]", "Подписать"), ("Jurisdiction [джурисдикшн]", "Юрисдикция")], "phrase": {"text": "Get it in writing.", "movie": "Business wisdom", "meaning": "Всегда фиксируй договорённости письменно. Хорошие отношения не заменяют контракт."}, "dialogue": [("Client", "Do we really need a formal contract?"), ("You", "Absolutely. It protects both of us and sets clear expectations."), ("You", "I'll send a simple one-page agreement today.")]},
        {"topic": "International payments", "words": [("Wire transfer [вайэр трэнсфэр]", "Банковский перевод"), ("Exchange rate [икстчэйндж рэйт]", "Обменный курс"), ("Currency [карэнси]", "Валюта"), ("Transaction fee [трэнзэкшн фи]", "Комиссия"), ("SWIFT [свифт]", "SWIFT"), ("PayPal [пэйпэл]", "PayPal"), ("Wise [вайз]", "Wise"), ("Invoice [инвойс]", "Счёт"), ("VAT [вэт]", "НДС"), ("Tax [тэкс]", "Налог")], "phrase": {"text": "Money makes the world go round.", "movie": "Cabaret (1972)", "meaning": "Платёжная инфраструктура критична для международного бизнеса."}, "dialogue": [("Client", "How do we pay you?"), ("You", "We accept bank transfer or Wise for international payments."), ("You", "Wise is fastest with the best exchange rates.")]},
        {"topic": "Negotiating prices", "words": [("Negotiate [нэгоушиэйт]", "Переговоры"), ("Counter offer [каунтэр офэр]", "Встречное предложение"), ("Bottom line [ботом лайн]", "Предел"), ("Flexibility [флэксэбилити]", "Гибкость"), ("Trade off [трэйд оф]", "Компромисс"), ("Concession [консэшн]", "Уступка"), ("Win-win [вин-вин]", "Взаимовыгодный"), ("Walk away [вок эвэй]", "Уйти"), ("BATNA [батна]", "Лучшая альтернатива"), ("Anchor [энкэр]", "Якорь цены")], "phrase": {"text": "He who speaks first loses.", "movie": "Negotiation wisdom", "meaning": "После озвучивания цены — молчи. Пауза давит на покупателя сильнее слов."}, "dialogue": [("You", "Our price for this project is $4,500."), ("Client", "That's above our budget."), ("You", "What's your budget? Let's see what we can work out.")]},
        {"topic": "ROI conversations", "words": [("ROI [ар-оу-ай]", "Возврат инвестиций"), ("Break even [брэйк ивэн]", "Выйти в ноль"), ("Profitable [профитэбл]", "Прибыльный"), ("Revenue [рэвэнью]", "Выручка"), ("Margin [марджин]", "Маржа"), ("Cost [кост]", "Стоимость"), ("Afford [эфорд]", "Позволить себе"), ("Invest [инвест]", "Инвестировать"), ("Return [ритёрн]", "Возврат"), ("Expense [икспэнс]", "Расход")], "phrase": {"text": "It takes money to make money.", "movie": "Business proverb", "meaning": "Инвестиция в качественный контент приносит больше клиентов. Помогай клиентам считать ROI."}, "dialogue": [("Client", "Is this a good investment?"), ("You", "If one new client comes from this video, it pays for itself."), ("You", "Our clients typically see 3-5x return on video investment.")]},
    ]},
    {"title": "Week 11 — Networking", "days": [
        {"topic": "Introducing at events", "words": [("Networking [нэтвёркинг]", "Нетворкинг"), ("Event [ивэнт]", "Мероприятие"), ("Conference [конфэрэнс]", "Конференция"), ("Attendee [этэнди]", "Участник"), ("Speaker [спикэр]", "Спикер"), ("Booth [бус]", "Стенд"), ("Badge [бэдж]", "Бейдж"), ("Business card [бизнэс кард]", "Визитная карточка"), ("Follow up [фолоу ап]", "Связаться после"), ("Connect [конэкт]", "Установить контакт")], "phrase": {"text": "It's not what you know, it's who you know.", "movie": "Business wisdom", "meaning": "Нетворкинг — инвестиция. Каждый человек на конференции — потенциальный клиент."}, "dialogue": [("Person", "Hi, I'm Sarah from TechCorp."), ("You", "Hi Sarah, I'm Artem. I run Lumora — AI video production."), ("Person", "Interesting! We've been looking for someone like you.")]},
        {"topic": "Small talk", "words": [("How's it going [хауз ит гоинг]", "Как дела"), ("What brings you here [уот брингс ю хир]", "Что привело вас"), ("First time here [фёрст тайм хир]", "Впервые здесь"), ("Great turnout [грэйт тёрнаут]", "Хорошая явка"), ("What's your take [уотс ёр тэйк]", "Ваше мнение"), ("Catch up [кэч ап]", "Пообщаться"), ("Exchange contacts [икстчэйндж контэктс]", "Обменяться контактами"), ("Stay in touch [стэй ин тач]", "Оставаться на связи"), ("Pleasure meeting you [плэжэр митинг ю]", "Приятно познакомиться"), ("Enjoyed the session [энджойд дэ сэшн]", "Понравилась сессия")], "phrase": {"text": "You never get a second chance to make a first impression.", "movie": "Will Rogers", "meaning": "Первые 30 секунд знакомства решают всё. Готовь elevator pitch заранее."}, "dialogue": [("You", "First time at this conference?"), ("Person", "No, I come every year. What's your take on the AI panel?"), ("You", "Very relevant to what we do. What's your take?")]},
        {"topic": "Elevator pitch", "words": [("Elevator pitch [элевэйтэр питч]", "Краткая презентация"), ("Hook [хук]", "Зацепка"), ("Value proposition [вэлью пропозишн]", "Ценностное предложение"), ("Problem [проблем]", "Проблема"), ("Solution [солюшн]", "Решение"), ("Memorable [мэморэбл]", "Запоминающийся"), ("Concise [консайс]", "Лаконичный"), ("Compelling [компэлинг]", "Убедительный"), ("Call to action [кол ту экшн]", "Призыв к действию"), ("Target [таргет]", "Целевая аудитория")], "phrase": {"text": "If you can't explain it simply, you don't understand it.", "movie": "Albert Einstein", "meaning": "Лучший питч — простой. Практикуй объяснение бизнеса за 30 секунд."}, "dialogue": [("Person", "So what do you do exactly?"), ("You", "We help B2B companies produce professional videos 3x faster using AI."), ("You", "Instead of weeks, we deliver in days at half the cost."), ("Person", "That's exactly what we need. Can I get your card?")]},
        {"topic": "LinkedIn networking", "words": [("Connection [конэкшн]", "Контакт"), ("Mutual [мьючуэл]", "Общий"), ("Endorse [индорс]", "Рекомендовать навык"), ("Recommend [рэкэмэнд]", "Рекомендовать"), ("Message [мэсидж]", "Сообщение"), ("Post [поуст]", "Публикация"), ("Engage [ингэйдж]", "Взаимодействовать"), ("Comment [комэнт]", "Комментировать"), ("Profile [профайл]", "Профиль"), ("Headline [хэдлайн]", "Заголовок")], "phrase": {"text": "Your network is your net worth.", "movie": "Timothy Ferriss", "meaning": "Сеть контактов = капитал. Каждое LinkedIn-соединение — потенциальный клиент."}, "dialogue": [("You", "It was great meeting you at the conference."), ("You", "I'd love to connect on LinkedIn and stay in touch."), ("Person", "Absolutely. I'll send a request today.")]},
        {"topic": "Follow up after events", "words": [("Follow up [фолоу ап]", "Связаться после"), ("Recap [рикэп]", "Краткое резюме"), ("As promised [эз промист]", "Как обещал"), ("Reach out [рич аут]", "Связаться"), ("Schedule [скэджул]", "Запланировать"), ("Demo [демо]", "Демонстрация"), ("Interested [интэрэстид]", "Заинтересованный"), ("Opportunity [опортьюнити]", "Возможность"), ("Partnership [партнэршип]", "Партнёрство"), ("It was great meeting [ит воз грэйт митинг]", "Было приятно познакомиться")], "phrase": {"text": "The fortune is in the follow-up.", "movie": "Sales wisdom", "meaning": "80% продаж происходит после 5-го контакта. Follow-up — самый недооценённый инструмент."}, "dialogue": [("You", "Hi Sarah, great meeting you at the conference."), ("You", "As promised, here's our portfolio. Open to a 20-min call?"), ("Person", "Sure! I'm available Thursday at 2pm.")]},
    ]},
    {"title": "Week 12 — Advanced Expressions", "days": [
        {"topic": "Business idioms", "words": [("Get the ball rolling [гет дэ бол ролинг]", "Начать дело"), ("Touch base [тач бэйс]", "Переговорить"), ("On the same page [он дэ сэйм пэйдж]", "Думать одинаково"), ("Low hanging fruit [лоу хэнгинг фрут]", "Лёгкие победы"), ("Move the needle [мув дэ нидл]", "Сдвинуть с места"), ("Circle back [сёркл бэк]", "Вернуться к теме"), ("Game changer [гэйм чэйнджэр]", "Меняющий правила"), ("Think outside the box [синк аутсайд дэ бокс]", "Мыслить нестандартно"), ("Hit the ground running [хит дэ граунд ранинг]", "Сразу взяться за дело"), ("Raise the bar [рэйз дэ бар]", "Поднять планку")], "phrase": {"text": "Let's not reinvent the wheel.", "movie": "Business expression", "meaning": "Используй проверенные подходы и масштабируй их."}, "dialogue": [("Client", "We need to think outside the box."), ("You", "Let's get the ball rolling with a brainstorm call."), ("You", "I'll circle back with ideas by end of week.")]},
        {"topic": "Agreement and enthusiasm", "words": [("Absolutely [эбсолютли]", "Абсолютно"), ("Exactly [игзэктли]", "Именно"), ("Precisely [присайсли]", "Точно"), ("That makes sense [дэт мэйкс сэнс]", "Это имеет смысл"), ("I couldn't agree more [ай кудэнт эгри мор]", "Полностью согласен"), ("Well said [вэл сэд]", "Хорошо сказано"), ("Great idea [грэйт айдиа]", "Отличная идея"), ("I love that [ай лав дэт]", "Мне это нравится"), ("That's spot on [дэтс спот он]", "Прямо в точку"), ("You're right [юр райт]", "Вы правы")], "phrase": {"text": "Yes, and...", "movie": "Improv comedy rule", "meaning": "Соглашайся и добавляй. Лучшая техника для переговоров."}, "dialogue": [("Client", "We want something bold and unexpected."), ("You", "I love that. And we could add motion graphics to amplify it."), ("Client", "That's spot on!")]},
        {"topic": "Diplomatic disagreement", "words": [("I see your point [ай си ёр поинт]", "Понимаю вашу точку"), ("However [хауэвэр]", "Однако"), ("With respect [вид риспэкт]", "С уважением"), ("I'd like to suggest [айд лайк ту сэджэст]", "Я бы предложил"), ("From my experience [фром май икспириэнс]", "По моему опыту"), ("Consider [консидэр]", "Рассмотреть"), ("Alternative approach [олтёрнэтив эпроуч]", "Альтернативный подход"), ("Might be worth [майт би вёрс]", "Возможно стоит"), ("Respectfully [риспэктфули]", "С уважением"), ("Push back [пуш бэк]", "Возразить")], "phrase": {"text": "I hear you, but...", "movie": "Negotiation technique", "meaning": "Сначала подтверди что слышишь — потом выражай несогласие. Снижает конфликтность."}, "dialogue": [("Client", "We want it done in 2 days."), ("You", "I hear you, and I understand the urgency."), ("You", "However, rushing would compromise quality. 4 days gives the best result.")]},
        {"topic": "Professional email phrases", "words": [("I hope this finds you well [ай хоуп дис файндс ю вэл]", "Надеюсь у вас всё хорошо"), ("Per our conversation [пэр аур конвёрсэйшн]", "По нашему разговору"), ("Please don't hesitate [плиз доунт хэзитэйт]", "Не стесняйтесь"), ("I wanted to follow up [ай уонтид ту фолоу ап]", "Хотел уточнить"), ("As per your request [эз пэр ёр рикуэст]", "По вашей просьбе"), ("Kind regards [кайнд ригардз]", "С уважением"), ("At your earliest convenience [эт ёр ёрлиэст конвиниэнс]", "При первой возможности"), ("Please advise [плиз эдвайз]", "Прошу уточнить"), ("Pending your approval [пэндинг ёр эпрувэл]", "Ожидаю согласования"), ("Attached herewith [этэчт хирвид]", "Прилагаю")], "phrase": {"text": "The pen is mightier than the sword.", "movie": "E. Bulwer-Lytton", "meaning": "Хорошо написанное письмо закрывает сделки. Инвестируй в письменную коммуникацию."}, "dialogue": [("You", "I hope this finds you well."), ("You", "Per our conversation, I've attached the revised proposal."), ("You", "Please don't hesitate to reach out with questions.")]},
        {"topic": "Confidence language", "words": [("I'll take ownership [айл тэйк оунэршип]", "Беру ответственность"), ("Count on me [каунт он ми]", "Рассчитывайте на меня"), ("I'll make it happen [айл мэйк ит хэпэн]", "Я это сделаю"), ("Accountability [экаунтэбилити]", "Подотчётность"), ("Leadership [лидэршип]", "Лидерство"), ("Initiative [инишэтив]", "Инициатива"), ("Proactive [проэктив]", "Проактивный"), ("Drive [драйв]", "Стремление"), ("Commitment [комитмэнт]", "Обязательство"), ("No excuses [ноу иксьюзэс]", "Никаких оправданий")], "phrase": {"text": "The buck stops here.", "movie": "Harry S. Truman", "meaning": "Я несу ответственность. Клиенты платят больше тем кто берёт ownership."}, "dialogue": [("Client", "What if something goes wrong?"), ("You", "I'll take full ownership. You have my commitment."), ("You", "Count on me to deliver — no excuses.")]},
    ]},
    {"title": "Week 13 — Fluency & Natural Speech", "days": [
        {"topic": "Filler phrases", "words": [("Well [вэл]", "Ну / Итак"), ("You know [ю ноу]", "Знаете"), ("I mean [ай мин]", "Я имею в виду"), ("Let me think [лет ми синк]", "Дайте подумать"), ("So basically [соу бэйсикли]", "В основном"), ("As I was saying [эз ай воз сэйинг]", "Как я говорил"), ("In a nutshell [ин э натшэл]", "В двух словах"), ("To be honest [ту би онест]", "Честно говоря"), ("Frankly speaking [фрэнкли спикинг]", "Откровенно говоря"), ("That's a good point [дэтс э гуд поинт]", "Хорошее замечание")], "phrase": {"text": "Speak slowly, think quickly.", "movie": "Communication wisdom", "meaning": "Не бойся пауз. Медленная уверенная речь звучит профессиональнее быстрой нервной."}, "dialogue": [("Client", "What's your honest opinion on our content?"), ("You", "Well, to be honest — great material but needs better distribution."), ("You", "In a nutshell — better video + right platform = much bigger reach.")]},
        {"topic": "Active listening", "words": [("I see [ай си]", "Понятно"), ("I understand [ай андэстэнд]", "Понимаю"), ("Go on [гоу он]", "Продолжайте"), ("Tell me more [тэл ми мор]", "Расскажите подробнее"), ("That's interesting [дэтс интэрэстинг]", "Это интересно"), ("Could you elaborate [куд ю илэборэйт]", "Не могли бы вы пояснить"), ("I hear you [ай хир ю]", "Я вас слышу"), ("Makes sense [мэйкс сэнс]", "Имеет смысл"), ("Interesting perspective [интэрэстинг пэрспэктив]", "Интересная точка"), ("What do you mean by [уот ду ю мин бай]", "Что вы имеете в виду")], "phrase": {"text": "You have two ears and one mouth for a reason.", "movie": "Ancient wisdom", "meaning": "Слушай вдвое больше чем говоришь. Лучшие продавцы — лучшие слушатели."}, "dialogue": [("Client", "We've tried video before but it didn't work."), ("You", "I see. Tell me more about what you tried."), ("You", "What specifically disappointed you?")]},
        {"topic": "Expressing uncertainty", "words": [("I'm not sure [айм нот шуэр]", "Я не уверен"), ("I'd have to check [айд хэв ту чэк]", "Нужно проверить"), ("I'll get back to you [айл гет бэк ту ю]", "Вернусь с ответом"), ("Let me confirm [лет ми конфёрм]", "Позвольте уточнить"), ("Approximately [эпроксимэтли]", "Приблизительно"), ("Roughly [рафли]", "Примерно"), ("It depends [ит дипэндс]", "Зависит от"), ("Subject to [сабджэкт ту]", "При условии"), ("To be confirmed [ту би конфёрмд]", "Требует подтверждения"), ("Off the top of my head [оф дэ топ оф май хэд]", "Навскидку")], "phrase": {"text": "I don't know, but I'll find out.", "movie": "Professional wisdom", "meaning": "Признать незнание и найти ответ — признак профессионализма, не слабости."}, "dialogue": [("Client", "What's the turnaround for a 5-minute video?"), ("You", "Roughly 7-10 days. Let me confirm and get back to you today."), ("Client", "Thanks for being upfront.")]},
        {"topic": "Transitions", "words": [("Furthermore [фёрдэрмор]", "Кроме того"), ("In addition [ин эдишн]", "Вдобавок"), ("On the other hand [он дэ адэр хэнд]", "С другой стороны"), ("As a result [эз э ризалт]", "В результате"), ("Therefore [дэрэфор]", "Следовательно"), ("Nevertheless [нэвэрдэлэс]", "Тем не менее"), ("In contrast [ин контраст]", "В отличие от"), ("Similarly [симэлэрли]", "Аналогично"), ("Consequently [консэквэнтли]", "Следовательно"), ("To summarize [ту самэрайз]", "Подводя итог")], "phrase": {"text": "First... then... finally.", "movie": "Presentation structure", "meaning": "Структура делает речь понятной на любом языке."}, "dialogue": [("You", "First, we align on the brief. Then we produce."), ("You", "Finally, you review and we deliver the final cut."), ("You", "As a result, professional content without the usual overhead.")]},
        {"topic": "Power adverbs", "words": [("Specifically [спэсификли]", "Конкретно"), ("Particularly [партикьюлэрли]", "В особенности"), ("Essentially [исэншэли]", "По сути"), ("Ultimately [алтимэтли]", "В конечном счёте"), ("Effectively [ифэктивли]", "Эффективно"), ("Efficiently [ифишэнтли]", "Продуктивно"), ("Professionally [профэшэнэли]", "Профессионально"), ("Strategically [стрэтиджикли]", "Стратегически"), ("Comprehensively [комприхэнсивли]", "Всесторонне"), ("Consistently [консистэнтли]", "Последовательно")], "phrase": {"text": "Practice makes perfect.", "movie": "Universal wisdom", "meaning": "Читай эти слова вслух каждый день. Произношение приходит только через практику."}, "dialogue": [("You", "Specifically, we focus on B2B video content."), ("You", "Essentially, we make your message clear and compelling."), ("You", "Ultimately, this drives more clients to your business.")]},
    ]},
    {"title": "Week 14 — Interviews & Podcasts", "days": [
        {"topic": "Being a guest speaker", "words": [("Guest [гэст]", "Гость"), ("Host [хоуст]", "Ведущий"), ("Episode [эписоуд]", "Эпизод"), ("Record [рэкорд]", "Записать"), ("Microphone [майкрофоун]", "Микрофон"), ("Interview [интэрвью]", "Интервью"), ("Audience [одиэнс]", "Аудитория"), ("Topic [топик]", "Тема"), ("Insight [инсайт]", "Инсайт"), ("Expertise [экспёртиз]", "Экспертиза")], "phrase": {"text": "Be yourself. Everyone else is already taken.", "movie": "Oscar Wilde", "meaning": "На интервью — будь собой. Аутентичность привлекает нужных клиентов."}, "dialogue": [("Host", "Welcome to the show, Artem. Tell us about Lumora."), ("You", "Thank you for having me. Lumora is an AI video production studio."), ("You", "We help B2B companies create professional content faster than ever.")]},
        {"topic": "Telling your story", "words": [("Background [бэкграунд]", "Предыстория"), ("Founded [фаундид]", "Основал"), ("Journey [джёрни]", "Путь"), ("Pivot [пивот]", "Изменение направления"), ("Challenge [челиндж]", "Вызов"), ("Breakthrough [брэйксру]", "Прорыв"), ("Lesson [лэсэн]", "Урок"), ("Inspire [инспайэр]", "Вдохновлять"), ("Mission [мишн]", "Миссия"), ("Vision [вижн]", "Видение")], "phrase": {"text": "Every master was once a disaster.", "movie": "T. Harv Eker", "meaning": "Твоя история начала пути делает тебя человечным и вдохновляет других."}, "dialogue": [("Host", "How did you get into AI video production?"), ("You", "I've been in video production for 10 years. When AI emerged, I saw an opportunity."), ("You", "The breakthrough came when I realized AI could cut production time by 70%.")]},
        {"topic": "Sharing expertise", "words": [("In my experience [ин май икспириэнс]", "По моему опыту"), ("The key insight [дэ ки инсайт]", "Ключевой инсайт"), ("What I've found [уот айв фаунд]", "То что я обнаружил"), ("Counterintuitive [каунтэринтьюитив]", "Контринтуитивный"), ("Debunk [дибанк]", "Развенчать миф"), ("Myth [мис]", "Миф"), ("Reality [риэлити]", "Реальность"), ("Practical [прэктикэл]", "Практический"), ("Research shows [рисёрч шоуз]", "Исследования показывают"), ("Nuanced [ньюэнст]", "Нюансированный")], "phrase": {"text": "Share what you know. It will come back to you.", "movie": "Wisdom", "meaning": "Делись экспертизой публично. Это привлекает клиентов лучше чем реклама."}, "dialogue": [("Host", "What's a common myth about AI video?"), ("You", "People think AI means low quality. That's a myth."), ("You", "AI + human review produces better results than traditional methods.")]},
        {"topic": "Handling tough questions", "words": [("That's fair [дэтс фэр]", "Справедливо"), ("Legitimate concern [лэджитимэт консёрн]", "Законная озабоченность"), ("Transparent [трэнспэрэнт]", "Прозрачный"), ("Honest answer [онэст ансэр]", "Честный ответ"), ("Acknowledge [экнолидж]", "Признать"), ("Address [эдрэс]", "Ответить на"), ("Nuance [ньюэнс]", "Нюанс"), ("Context [контэкст]", "Контекст"), ("Clarify [клэрифай]", "Уточнить"), ("Stand by [стэнд бай]", "Придерживаться")], "phrase": {"text": "The truth will set you free.", "movie": "John 8:32", "meaning": "Честность строит доверие. Не избегай сложных вопросов — отвечай уверенно."}, "dialogue": [("Host", "Isn't AI taking jobs from video professionals?"), ("You", "That's a legitimate concern and I want to be transparent."), ("You", "AI changes the work but creates more demand for video overall.")]},
        {"topic": "Media calls to action", "words": [("Find us at [файнд ас эт]", "Найдите нас на"), ("Reach out [рич аут]", "Свяжитесь"), ("DM me [ди-эм ми]", "Напишите мне"), ("Check out [чэк аут]", "Посмотрите"), ("Free consultation [фри консалтэйшн]", "Бесплатная консультация"), ("Portfolio [портфолио]", "Портфолио"), ("Case study [кэйс стади]", "Кейс"), ("Website [вэбсайт]", "Сайт"), ("Subscribe [сэбскрайб]", "Подпишитесь"), ("Social media [соушэл мидиа]", "Социальные сети")], "phrase": {"text": "Don't just listen — act.", "movie": "Action bias", "meaning": "Каждое медиавыступление должно заканчиваться чётким призывом к действию."}, "dialogue": [("Host", "Where can listeners find you?"), ("You", "Find us at lumora.studio. Free portfolio and case studies there."), ("You", "Or DM me on LinkedIn — I respond to everyone personally.")]},
    ]},
    {"title": "Week 15 — Advanced Business English", "days": [
        {"topic": "Executive communication", "words": [("C-suite [си-сьют]", "Топ-менеджмент"), ("Stakeholder [стэйкхолдэр]", "Заинтересованная сторона"), ("Board [борд]", "Совет директоров"), ("Executive [игзэкьютив]", "Руководитель"), ("Decision maker [дисижн мэйкэр]", "Лицо принимающее решения"), ("Buy-in [бай-ин]", "Поддержка"), ("Sign off [сайн оф]", "Утвердить"), ("Escalate [эскэлэйт]", "Эскалировать"), ("Strategic alignment [стрэтэджик элайнмэнт]", "Стратегическое согласование"), ("Chain of command [чэйн оф команд]", "Иерархия")], "phrase": {"text": "Dress for the job you want, not the job you have.", "movie": "Career wisdom", "meaning": "Общайся с C-suite как равный. Уверенность открывает двери к топ-клиентам."}, "dialogue": [("CEO", "Why choose Lumora over traditional agencies?"), ("You", "Speed, cost, and quality. We deliver faster at 40% lower cost."), ("You", "I'd be happy to present a business case if that helps with buy-in.")]},
        {"topic": "Industry terms", "words": [("B2B [би-ту-би]", "Бизнес для бизнеса"), ("SaaS [сас]", "Программное обеспечение как услуга"), ("Fintech [финтэк]", "Финансовые технологии"), ("Startup [стартап]", "Стартап"), ("Scale-up [скэйл-ап]", "Растущая компания"), ("Enterprise [энтэрпрайз]", "Корпоративный"), ("SME [эс-эм-и]", "Малый и средний бизнес"), ("Vertical [вёртикэл]", "Отраслевой сегмент"), ("Martech [мартэк]", "Маркетинговые технологии"), ("B2C [би-ту-си]", "Бизнес для потребителя")], "phrase": {"text": "Know your customer.", "movie": "Business principle", "meaning": "Разговаривай на языке клиента. Fintech — про compliance. SaaS — про onboarding."}, "dialogue": [("Client", "Do you have experience with SaaS companies?"), ("You", "Yes, we've worked with several B2B SaaS startups."), ("You", "We understand product demos and onboarding videos well.")]},
        {"topic": "Presenting data", "words": [("According to [экординг ту]", "Согласно"), ("The data shows [дэ дэйта шоуз]", "Данные показывают"), ("Significant increase [сигнификэнт инкрис]", "Значительный рост"), ("Compared to [компэрд ту]", "По сравнению с"), ("Year over year [ёр оувэр ёр]", "Год к году"), ("Percentage points [пёрсэнтидж поинтс]", "Процентные пункты"), ("Baseline [бэйслайн]", "Базовый показатель"), ("Outperform [аутпэрформ]", "Превзойти"), ("Benchmark [бэнчмарк]", "Контрольный показатель"), ("Quarter on quarter [куортэр он куортэр]", "Квартал к кварталу")], "phrase": {"text": "In God we trust. All others bring data.", "movie": "W. Edwards Deming", "meaning": "Данные убеждают лучше слов. Подкрепляй предложения цифрами."}, "dialogue": [("You", "According to our data, video gets 3x more engagement."), ("You", "Compared to last quarter, our clients saw 40% more leads."), ("Client", "Those numbers are impressive. Tell me more.")]},
        {"topic": "Crisis communication", "words": [("Issue [ишью]", "Проблема"), ("Transparent [трэнспэрэнт]", "Прозрачный"), ("Communicate proactively [комьюникэйт проэктивли]", "Сообщать заблаговременно"), ("Mitigation plan [митигэйшн плэн]", "План снижения рисков"), ("Contain [контэйн]", "Сдержать"), ("Resolution [рэзолюшн]", "Решение"), ("Post-mortem [поуст-мортэм]", "Разбор полётов"), ("Preventive [привэнтив]", "Превентивный"), ("Accountability [экаунтэбилити]", "Подотчётность"), ("Escalate [эскэлэйт]", "Эскалировать")], "phrase": {"text": "Bad news doesn't get better with time.", "movie": "Management wisdom", "meaning": "Сообщай о проблемах немедленно. Клиенты прощают ошибки — но не скрытность."}, "dialogue": [("You", "I need to communicate proactively — we hit a technical issue."), ("You", "The good news: we have a plan and can deliver by Friday."), ("Client", "I appreciate the transparency. Thanks for letting us know early.")]},
        {"topic": "Long-term partnerships", "words": [("Strategic partner [стрэтэджик партнэр]", "Стратегический партнёр"), ("Long-term relationship [лонг-тёрм рилэйшншип]", "Долгосрочные отношения"), ("Mutual benefit [мьючуэл бэнэфит]", "Взаимная выгода"), ("Synergy [синэрджи]", "Синергия"), ("Trusted advisor [трастид эдвайзэр]", "Доверенный советник"), ("Preferred vendor [прифёрд вэндэр]", "Предпочтительный поставщик"), ("Renewal [ринюэл]", "Продление"), ("Co-create [коу-криэйт]", "Создавать совместно"), ("Exclusive [икслюсив]", "Эксклюзивный"), ("Collaborate [колэборэйт]", "Сотрудничать")], "phrase": {"text": "Go fast alone, go far together.", "movie": "African proverb", "meaning": "Лучшие клиенты становятся партнёрами. Стремись к долгосрочным отношениям."}, "dialogue": [("Client", "We're happy with the work. What would a long-term partnership look like?"), ("You", "I'd love to become your trusted video partner."), ("You", "A retainer gives you priority access and the best rates.")]},
    ]},
    {"title": "Week 16 — Final Review & Mastery", "days": [
        {"topic": "Complete client conversation", "words": [("Comprehensive [комприхэнсив]", "Всесторонний"), ("End-to-end [энд-ту-энд]", "От начала до конца"), ("Full cycle [фул сайкл]", "Полный цикл"), ("Seamless [симлэс]", "Безупречный"), ("Holistic [холистик]", "Целостный"), ("Integrated [интигрэйтид]", "Интегрированный"), ("Turnkey [тёрнки]", "Под ключ"), ("White glove [уайт глав]", "Премиум сервис"), ("Bespoke [биспоук]", "Индивидуальный"), ("Tailor-made [тэйлэр-мэйд]", "Сделанный на заказ")], "phrase": {"text": "Excellence is not a destination but a continuous journey.", "movie": "Brian Tracy", "meaning": "4 месяца учёбы — это начало, не конец. Продолжай практиковать с реальными клиентами."}, "dialogue": [("Client", "What makes Lumora different?"), ("You", "We offer an end-to-end, turnkey solution. Brief to delivery."), ("You", "Every project is tailor-made. No templates, no shortcuts.")]},
        {"topic": "Top power phrases", "words": [("Let's make it happen [летс мэйк ит хэпэн]", "Давайте это сделаем"), ("I'm confident we can [айм конфидэнт ви кэн]", "Я уверен что мы можем"), ("Here's what I propose [хирз уот ай пропоуз]", "Вот что я предлагаю"), ("Based on your needs [бэйст он ёр нидс]", "Исходя из ваших потребностей"), ("What matters most [уот мэтэрс моуст]", "Что важнее всего"), ("The bottom line is [дэ ботом лайн из]", "Суть в том что"), ("Moving forward [мувинг форвэрд]", "Двигаясь вперёд"), ("I'll take care of it [айл тэйк кэр оф ит]", "Я займусь этим"), ("You can count on us [ю кэн каунт он ас]", "На нас можно рассчитывать"), ("The way I see it [дэ вэй ай си ит]", "Как я это вижу")], "phrase": {"text": "You've come a long way.", "movie": "Common expression", "meaning": "160 дней практики — ты готов к международным переговорам."}, "dialogue": [("Client", "Can you handle our entire video marketing?"), ("You", "Absolutely. Based on your needs, here's what I propose."), ("You", "Moving forward, you can count on us for everything video-related.")]},
        {"topic": "Your personal pitch final", "words": [("Passionate [пэшэнэт]", "Увлечённый"), ("Dedicated [дэдикэйтид]", "Преданный делу"), ("Results-driven [ризалтс-дривэн]", "Ориентированный на результат"), ("Client-focused [клайент-фокэст]", "Клиентоориентированный"), ("Innovative [инновэтив]", "Инновационный"), ("Reliable [рилайэбл]", "Надёжный"), ("Creative [криэтив]", "Креативный"), ("Professional [профэшэнэл]", "Профессиональный"), ("International [интэрнэшэнэл]", "Международный"), ("Expert [экспёрт]", "Эксперт")], "phrase": {"text": "The best time to start was yesterday. The second best is now.", "movie": "Chinese proverb", "meaning": "Не жди идеального английского. Начни говорить сейчас — с каждым звонком становишься лучше."}, "dialogue": [("You", "Hi, I'm Artem from Lumora Studio."), ("You", "We're a dedicated, results-driven AI video production company."), ("You", "We help international B2B brands communicate professionally and efficiently.")]},
        {"topic": "Graduation vocabulary", "words": [("Achievement [эчивмэнт]", "Достижение"), ("Progress [прогрэс]", "Прогресс"), ("Milestone [майлстоун]", "Веха"), ("Fluent [флуэнт]", "Свободно владеющий"), ("Confident [конфидэнт]", "Уверенный"), ("Communicate [комьюникэйт]", "Общаться"), ("International [интэрнэшэнэл]", "Международный"), ("Professional [профэшэнэл]", "Профессиональный"), ("Ready [рэди]", "Готовый"), ("Success [саксэс]", "Успех")], "phrase": {"text": "This is not the end. It is the end of the beginning.", "movie": "Winston Churchill", "meaning": "Поздравляем! Программа завершена. Настоящая учёба только начинается с реальными клиентами."}, "dialogue": [("Client", "Your English is very good! Where did you learn?"), ("You", "Thank you! I've been studying business English intensively."), ("You", "Communication is as important as the work itself.")]},
        {"topic": "Final essential phrases", "words": [("How can I help you [хау кэн ай хэлп ю]", "Чем могу помочь"), ("What are your goals [уот ар ёр гоулс]", "Каковы ваши цели"), ("I understand your needs [ай андэстэнд ёр нидс]", "Понимаю ваши потребности"), ("Here's my proposal [хирз май пропоузэл]", "Вот моё предложение"), ("We can start immediately [ви кэн старт имидиэтли]", "Можем начать немедленно"), ("You're in good hands [юр ин гуд хэндс]", "Вы в надёжных руках"), ("I guarantee quality [ай гэрэнти куолити]", "Гарантирую качество"), ("Thank you for your trust [сэнк ю фор ёр траст]", "Спасибо за доверие"), ("Looking forward to working together [лукинг форвэрд ту вёркинг тугэдэр]", "С нетерпением жду работы"), ("Let's build something great [летс билд самсинг грэйт]", "Давайте создадим нечто великое")], "phrase": {"text": "And so the adventure begins.", "movie": "Universal", "meaning": "Программа завершена. Международный рынок ждёт. Вперёд, Lumora!"}, "dialogue": [("Client", "We'd like to work with you."), ("You", "Thank you for your trust. You're in good hands."), ("You", "I guarantee quality and look forward to working together."), ("You", "Let's build something great!")]},
    ]},

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
