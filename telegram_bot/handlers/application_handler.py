"""
Обработчик подачи заявки через Telegram.
Диалог: описание проблемы → 5 AI-вопросов → итоговый анализ → CTA
"""
import httpx
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from keyboards import back_to_menu_keyboard

API_BASE = "http://localhost:8000/api"

# Состояния ConversationHandler
APPLICATION_PROBLEM = 1
APPLICATION_ANSWERING = 2


async def start_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога — просим описать проблему."""
    msg = update.message or update.callback_query.message
    await msg.reply_text(
        "📋 <b>Опишите вашу юридическую ситуацию</b>\n\n"
        "Пишите подробно: что произошло, когда, кто участвует, что вы хотите получить.\n\n"
        "<i>Например: «Купил телефон в интернет-магазине, он сломался через 2 недели. "
        "Магазин отказывается делать ремонт по гарантии»</i>",
        parse_mode="HTML",
    )
    return APPLICATION_PROBLEM


async def receive_problem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем описание → отправляем в API → получаем первый вопрос."""
    problem = update.message.text
    chat_id = str(update.effective_chat.id)

    await update.message.reply_text("⏳ Анализирую ситуацию...")

    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.post(f"{API_BASE}/applications/", json={
            "contact_name": update.effective_user.full_name or "Клиент",
            "contact_email": f"tg_{chat_id}@telegram.local",
            "problem_description": problem,
            "telegram_chat_id": chat_id,
        })

    if resp.status_code != 201:
        await update.message.reply_text("❌ Ошибка. Попробуйте позже или напишите нам напрямую.")
        return ConversationHandler.END

    data = resp.json()
    context.user_data["application_id"] = data["id"]
    context.user_data["qualification_step"] = 0

    # Отправляем предварительный анализ
    category_labels = {
        "consumer_rights": "⚖️ Права потребителя",
        "labor_dispute": "👷 Трудовой спор",
        "tax": "💰 Налоги",
        "family_law": "👨‍👩‍👧 Семейное право",
        "property": "🏠 Имущественные споры",
        "criminal": "🔒 Уголовное дело",
        "administrative": "📜 Административное",
        "business": "💼 Бизнес / договоры",
        "housing": "🏢 ЖКХ / жилищные",
        "other": "❓ Другое",
    }
    cat = category_labels.get(data.get("legal_category", "other"), "❓ Другое")

    await update.message.reply_text(
        f"✅ <b>Предварительный анализ</b>\n\n"
        f"Категория: {cat}\n\n"
        f"<i>{data.get('ai_preliminary_answer', '')}</i>",
        parse_mode="HTML",
    )

    # Задаём первый уточняющий вопрос
    q = data.get("current_question")
    if q:
        await update.message.reply_text(
            f"❓ <b>Вопрос 1 из 5:</b>\n\n{q['text']}\n\n"
            f"<i>💡 {q.get('hint', '')}</i>",
            parse_mode="HTML",
        )
        return APPLICATION_ANSWERING

    return ConversationHandler.END


async def receive_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем ответ на вопрос → отправляем в API → следующий вопрос или итог."""
    app_id = context.user_data.get("application_id")
    step = context.user_data.get("qualification_step", 0)

    if not app_id:
        await update.message.reply_text("Что-то пошло не так. Начните заново: /apply")
        return ConversationHandler.END

    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.post(f"{API_BASE}/applications/{app_id}/answer", json={
            "question_id": step + 1,
            "answer": update.message.text,
        })

    if resp.status_code != 200:
        await update.message.reply_text("❌ Ошибка. Попробуйте позже.")
        return ConversationHandler.END

    data = resp.json()
    context.user_data["qualification_step"] = data["qualification_step"]

    if data["completed"]:
        # Квалификация завершена — показываем итог
        await update.message.reply_text(
            "✅ <b>Анализ завершён!</b>\n\n"
            f"<b>Ваша ситуация:</b>\n{data.get('ai_summary', '')}\n\n"
            f"<b>Рекомендация:</b>\n{data.get('ai_preliminary_answer', '')}\n\n"
            "Что дальше?",
            parse_mode="HTML",
            reply_markup=_post_qualification_keyboard(),
        )
        return ConversationHandler.END

    # Следующий вопрос
    q = data.get("current_question")
    step_num = data["qualification_step"] + 1
    if q:
        await update.message.reply_text(
            f"❓ <b>Вопрос {step_num} из 5:</b>\n\n{q['text']}\n\n"
            f"<i>💡 {q.get('hint', '')}</i>",
            parse_mode="HTML",
        )
        return APPLICATION_ANSWERING

    return ConversationHandler.END


def _post_qualification_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗓 Записаться на консультацию", callback_data="menu_consultation")],
        [InlineKeyboardButton("📄 Подобрать шаблон документа", callback_data="menu_templates")],
        [InlineKeyboardButton("← Главное меню", callback_data="menu_main")],
    ])
