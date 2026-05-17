"""
Обработчик продажи шаблонов через Telegram.
Каталог → детали → оплата → автодоставка файла.
"""
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from keyboards import template_catalog_keyboard, template_detail_keyboard

API_BASE = "http://localhost:8000/api"


async def show_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает каталог шаблонов."""
    msg = update.message or update.callback_query.message

    async with httpx.AsyncClient() as http:
        resp = await http.get(f"{API_BASE}/templates/")

    if resp.status_code != 200:
        await msg.reply_text("❌ Не удалось загрузить каталог. Попробуйте позже.")
        return

    templates = resp.json()
    if not templates:
        await msg.reply_text("📭 Шаблоны ещё не добавлены.")
        return

    # Сохраняем шаблоны в контекст для быстрого доступа
    context.user_data["templates"] = {t["id"]: t for t in templates}

    await msg.reply_text(
        "📄 <b>Шаблоны документов</b>\n\nВыберите шаблон:",
        parse_mode="HTML",
        reply_markup=template_catalog_keyboard(templates),
    )


async def show_template_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает детали шаблона."""
    query = update.callback_query
    template_id = query.data.replace("template_", "")

    templates = context.user_data.get("templates", {})
    template = templates.get(template_id)

    if not template:
        # Загружаем из API если нет в кэше
        async with httpx.AsyncClient() as http:
            resp = await http.get(f"{API_BASE}/templates/{template_id}")
        if resp.status_code != 200:
            await query.message.reply_text("❌ Шаблон не найден.")
            return
        template = resp.json()

    price_text = f"~~{template['original_price']} ₽~~ → " if template.get("original_price") else ""
    price_text += f"<b>{template['price']} ₽</b>"

    text = (
        f"📄 <b>{template['name']}</b>\n\n"
        f"{template['description']}\n\n"
    )
    if template.get("preview_text"):
        text += f"<i>Фрагмент:</i>\n<code>{template['preview_text'][:200]}...</code>\n\n"

    text += (
        f"💰 Стоимость: {price_text}\n"
        f"📁 Формат: {template['file_format'].upper()}\n"
        f"📦 Продаж: {template['sales_count']}"
    )

    await query.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=template_detail_keyboard(template_id),
    )


async def buy_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Инициирует покупку шаблона.
    Запрашивает email если не известен, затем создаёт платёж.
    """
    query = update.callback_query
    template_id = query.data.replace("buy_", "")

    chat_id = str(update.effective_chat.id)
    user = update.effective_user

    # Сохраняем выбранный шаблон
    context.user_data["pending_purchase_template_id"] = template_id

    # Если email неизвестен — просим ввести
    if not context.user_data.get("email"):
        context.user_data["awaiting_email_for"] = "template_purchase"
        await query.message.reply_text(
            "📧 Введите ваш email для получения шаблона:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("← Отмена", callback_data=f"template_{template_id}")]
            ])
        )
        return

    await _create_template_payment(query.message, context, template_id, chat_id, user)


async def _create_template_payment(message, context, template_id, chat_id, user):
    """Создаёт платёж и отправляет ссылку."""
    email = context.user_data.get("email", f"tg_{chat_id}@telegram.local")
    name = user.full_name if user else "Клиент"

    async with httpx.AsyncClient(timeout=15) as http:
        resp = await http.post(f"{API_BASE}/templates/{template_id}/purchase", json={
            "buyer_email": email,
            "buyer_name": name,
            "telegram_chat_id": chat_id,
            "payment_provider": "yookassa",
        })

    if resp.status_code != 201:
        await message.reply_text("❌ Ошибка при создании платежа. Попробуйте позже.")
        return

    data = resp.json()
    checkout_url = data["checkout_url"]

    await message.reply_text(
        "💳 <b>Оплата</b>\n\n"
        "Нажмите кнопку ниже для перехода к оплате.\n"
        "После успешной оплаты шаблон будет отправлен вам автоматически в этот чат.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Оплатить", url=checkout_url)],
            [InlineKeyboardButton("← К шаблону", callback_data=f"template_{template_id}")],
        ])
    )
