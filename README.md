# ЮрСервис — Платформа юридических услуг онлайн

Полностью автоматизированная платформа: AI-квалификация обращений, продажа шаблонов документов,
онлайн-консультации с автоматической Zoom-ссылкой.

## Архитектура

```
┌─────────────┐    ┌──────────────────────────────────────────────┐
│  React SPA  │───▶│            FastAPI Backend                   │
│  (Vite)     │    │                                              │
│  /src/      │    │  /api/applications   ← AI-квалификация       │
└─────────────┘    │  /api/templates      ← каталог + продажи     │
                   │  /api/consultations  ← бронирование          │
┌─────────────┐    └──────────────────────────────────────────────┘
│  Telegram   │              │        │         │         │
│    Bot      │──────────────┘        │         │         │
└─────────────┘                       ▼         ▼         ▼
                              Claude AI  ЮКасса/  Calendly
                              (Anthropic) Stripe   + Zoom
                                                   + SendGrid
```

## Стек технологий

| Слой          | Технология                      |
|---------------|---------------------------------|
| Backend       | Python 3.12, FastAPI, SQLAlchemy |
| База данных   | PostgreSQL 16                   |
| AI            | Claude claude-sonnet-4-6 (Anthropic API) |
| Платежи РФ    | ЮКасса                          |
| Платежи INT   | Stripe                          |
| Расписание    | Calendly API                    |
| Видеосвязь    | Zoom Server-to-Server OAuth     |
| Email         | SendGrid                        |
| Telegram      | python-telegram-bot v21         |
| Frontend      | React 18, Vite, Tailwind CSS    |
| Деплой        | Docker Compose                  |

## Структура проекта

```
CodeHaven/
├── backend/
│   ├── app/
│   │   ├── main.py                      # FastAPI app
│   │   ├── config.py                    # Настройки (pydantic-settings)
│   │   ├── database.py                  # Async SQLAlchemy
│   │   ├── models/                      # ORM-модели
│   │   │   ├── application.py           # Заявки + история диалога
│   │   │   ├── template.py              # Шаблоны + покупки
│   │   │   ├── consultation.py          # Консультации
│   │   │   └── payment.py               # Платежи
│   │   ├── routers/
│   │   │   ├── applications.py          # POST /applications, POST /answer
│   │   │   ├── templates.py             # GET /templates, POST /purchase, webhook
│   │   │   └── consultations.py         # GET /slots, POST /, webhook
│   │   └── services/
│   │       ├── ai_service.py            # Claude API: классификация, вопросы
│   │       ├── payment_service.py       # ЮКасса + Stripe
│   │       ├── notification_service.py  # Email + Telegram
│   │       └── calendar_service.py      # Calendly + Zoom
│   ├── reminders.py                     # Крон-скрипт напоминаний
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── telegram_bot/
│   ├── bot.py                           # ConversationHandler + команды
│   ├── handlers/
│   │   ├── application_handler.py       # /apply → AI-квалификация
│   │   ├── template_handler.py          # Каталог + покупка
│   │   └── consultation_handler.py      # Бронирование
│   ├── keyboards/__init__.py            # InlineKeyboard-кнопки
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── pages/                       # Home, Templates, Consultation
│       ├── components/
│       │   ├── ApplicationForm/         # AI-квалификация пошагово
│       │   ├── TemplateCatalog/         # Каталог + покупка
│       │   └── ConsultationBooking/     # Слоты + бронирование
│       └── services/api.js              # Axios-клиент
├── migrations/
│   └── seed_templates.py               # Начальные данные (7 шаблонов)
└── docker-compose.yml
```

## Быстрый старт

```bash
# 1. Настройка переменных окружения
cp backend/.env.example backend/.env
# Заполните ключи: ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, YOOKASSA_*, ZOOM_*, SENDGRID_*

# 2. Запуск
docker-compose up -d

# 3. Заполнение каталога шаблонов
docker-compose exec backend python migrations/seed_templates.py

# 4. Открыть
# Frontend:  http://localhost:3000
# API docs:  http://localhost:8000/docs
```

## Ключевые API эндпоинты

### AI-квалификация заявок
```
POST /api/applications/
  Body: { contact_name, contact_email, problem_description }
  → { id, ai_preliminary_answer, current_question }  ← вопрос 1 из 5

POST /api/applications/{id}/answer
  Body: { question_id, answer }
  → следующий вопрос  или  completed=true + итоговый анализ
```

### Шаблоны документов
```
GET  /api/templates/                         — каталог
POST /api/templates/{id}/purchase            — создать платёж → checkout_url
GET  /api/templates/download/{token}         — скачать файл (токен из письма)
POST /api/templates/webhook/yookassa         — автодоставка после оплаты
```

### Консультации
```
GET  /api/consultations/slots                — доступные слоты
POST /api/consultations/                     — забронировать → checkout_url
GET  /api/consultations/{id}                 — статус + zoom_url
POST /api/consultations/webhook/yookassa     — создаёт Zoom-встречу автоматически
```

## Поток квалификации (AI)

```
Клиент описывает проблему
     ↓
Claude: категория + предварительный ответ + 5 вопросов
     ↓
Диалог: вопросы 1–5 (адаптивно)
     ↓
Claude: итоговый анализ + риски + рекомендации
     ↓
CTA: "Записаться на консультацию" | "Купить шаблон"
```

## Поток оплаты (шаблон)

```
Клиент → POST /purchase → ЮКасса checkout → оплата
     ↓ webhook
Автоматически: email с токен-ссылкой + файл в Telegram
```

## Поток оплаты (консультация)

```
Клиент → POST /consultations → ЮКасса checkout → оплата
     ↓ webhook
Автоматически: Zoom meeting API → email с ссылкой
     ↓ крон каждые 30 мин
Напоминание за 24ч → напоминание за 1ч
```

## Рекомендации по развитию

| Направление   | Идея                                                       |
|---------------|------------------------------------------------------------|
| Конверсия     | После AI-анализа показывать релевантные шаблоны сразу       |
| Конверсия     | Таймер скидки 10% на первую консультацию (24ч)              |
| Автоматизация | Webhook Calendly → автосоздание Consultation в БД           |
| Автоматизация | Follow-up email через 3 дня после консультации             |
| AI            | Саммари для консультанта перед встречей (из заявки)         |
| Техническое   | Redis для кэша слотов Calendly (TTL 5 мин)                 |
| Техническое   | Celery Beat вместо крон-контейнера                         |
| Техническое   | S3/Yandex Object Storage для шаблонов в production         |
| Аналитика     | Воронка: заявка → шаблон / консультация, LTV клиента        |
