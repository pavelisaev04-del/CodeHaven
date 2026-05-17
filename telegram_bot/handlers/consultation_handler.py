"""
Обработчик записи на консультацию через Telegram.
Поток: выбор длительности → выбор слота → подтверждение → оплата → Zoom-ссылка.
"""
import httpx
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from keyboards import consultation_duration_keyboard, slots_keyboard

API_BASE = "http://localhost:8000/api"


async def show_consultation_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовый экран: выбор длительности."""
    msg = update.message or update.callback_query.message
    await msg.reply_text(
        "🗓 <b>Онлайн-консультация с юристом</b>\n\n"
        "Консультация проходит в Zoom. После оплаты вы автоматически получите ссылку.\n\n"
        "Выберите длительность:",
        parse_mode="HTML",
        reply_markup=consultation_duration_keyboard(),
    )


async def handle_duration_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пользователь выбрал длительность → загружаем слоты."""
    query = update.callback_query
    await query.answer()

    duration = int(query.data.replace("consult_duration_", ""))
    context.user_data["consult_duration"] = duration

    await query.message.reply_text("⏳ Загружаю доступные слоты...")

    async with httpx.AsyncClient(timeout=15) as http:
        resp = await http.get(f"{API_BASE}/consultations/slots")

    if resp.status_code != 200:
        await query.message.reply_text("❌ Не удалось загрузить расписание. Попробуйте позже.")
        return

    slots = resp.json().get("slots", [])
    if not slots:
        await query.message.reply_text(
            "😔 К сожалению, свободных слотов нет. Напишите нам, мы подберём время.",
        )
        return

    context.user_data["consult_slots"] = slots

    await query.message.reply_text(
        f"📅 Доступные слоты для консультации ({duration} мин):\nВыберите удобное время:",
        reply_markup=slots_keyboard(slots),
    )


async def handle_slot_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пользователь выбрал слот → показываем подтверждение."""
    query = update.callback_query
    await query.answer()

    slot_idx = int(query.data.replace("consult_slot_", ""))
    slots = context.user_data.get("consult_slots", [])

    if slot_idx >= len(slots):
        await query.message.reply_text("❌ Слот недоступен. Выберите другой.")
        return

    selected_slot = slots[slot_idx]
    context.user_data["consult_slot"] = selected_slot

    dt = datetime.fromisoformat(selected_slot["start_time"])
    slot_label = dt.strftime("%d.%m.%Y в %H:%M (МСК)")
    duration = context.user_data.get("consult_duration", 60)
    prices = {30: 2500, 60: 4500, 90: 6500}
    price = prices.get(duration, 4500)

    await query.message.reply_text(
        f"✅ <b>Подтверждение записи</b>\n\n"
        f"📅 Дата и время: <b>{slot_label}</b>\n"
        f"⏱ Длительность: <b>{duration} минут</b>\n"
        f"💰 Стоимость: <b>{price:,} ₽</b>\n\n"
        "После оплаты вы получите ссылку на Zoom-звонок.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Оплатить и подтвердить", callback_data="consult_confirm")],
            [InlineKeyboardButton("← Изменить время", callback_data=f"consult_duration_{duration}")],
        ])
    )


async def confirm_consultation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение → создаём запись + платёж."""
    query = update.callback_query
    await query.answer()

    slot = context.user_data.get("consult_slot")
    duration = context.user_data.get("consult_duration", 60)
    chat_id = str(update.effective_chat.id)
    user = update.effective_user

    if not slot:
        await query.message.reply_text("❌ Выберите время сначала.")
        return

    email = context.user_data.get("email", f"tg_{chat_id}@telegram.local")
    name = user.full_name if user else "Клиент"

    async with httpx.AsyncClient(timeout=15) as http:
        resp = await http.post(f"{API_BASE}/consultations/", json={
            "client_name": name,
            "client_email": email,
            "duration_minutes": duration,
            "scheduled_at": slot["start_time"],
            "timezone": "Europe/Moscow",
            "payment_provider": "yookassa",
        })

    if resp.status_code != 201:
        await query.message.reply_text("❌ Ошибка бронирования. Попробуйте позже.")
        return

    data = resp.json()

    await query.message.reply_text(
        "🎉 <b>Бронь создана!</b>\n\n"
        "Перейдите к оплате. После оплаты Zoom-ссылка придёт на почту и в этот чат.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Оплатить", url=data["checkout_url"])],
        ])
    )

    # Сохраняем consultation_id для последующих уведомлений
    context.user_data["consultation_id"] = data["id"]
