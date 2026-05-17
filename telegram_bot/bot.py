"""
Telegram-бот юридического сервиса.
Функции:
  /start       — приветствие и главное меню
  /apply       — подать заявку (квалификация через AI)
  /templates   — каталог шаблонов документов
  /consultation — записаться на консультацию
  /help        — помощь
"""
import asyncio
import logging
import os
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters, ContextTypes,
)

from handlers.application_handler import (
    start_application, receive_problem, receive_answer,
    APPLICATION_PROBLEM, APPLICATION_ANSWERING,
)
from handlers.template_handler import (
    show_catalog, show_template_detail, buy_template,
)
from handlers.consultation_handler import (
    show_consultation_menu, handle_duration_selection,
    handle_slot_selection, confirm_consultation,
)
from keyboards import main_menu_keyboard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 <b>Добро пожаловать в юридический сервис!</b>\n\n"
        "Я помогу вам:\n"
        "• 📋 Подать заявку и получить первичную оценку ситуации\n"
        "• 📄 Купить шаблон документа (претензия, заявление и др.)\n"
        "• 🗓 Записаться на консультацию с юристом\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ <b>Как работает сервис:</b>\n\n"
        "1. Опишите вашу проблему → AI задаст 5 уточняющих вопросов\n"
        "2. Получите предварительную оценку ситуации\n"
        "3. Если нужен документ — купите готовый шаблон (500–1000 ₽)\n"
        "4. Для глубокого анализа — запишитесь на консультацию\n\n"
        "Команды:\n"
        "/apply — подать заявку\n"
        "/templates — шаблоны документов\n"
        "/consultation — записаться к юристу",
        parse_mode="HTML",
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок главного меню."""
    query = update.callback_query
    await query.answer()

    if query.data == "menu_apply":
        await start_application(update, context)
    elif query.data == "menu_templates":
        await show_catalog(update, context)
    elif query.data == "menu_consultation":
        await show_consultation_menu(update, context)
    elif query.data.startswith("template_"):
        await show_template_detail(update, context)
    elif query.data.startswith("buy_"):
        await buy_template(update, context)
    elif query.data.startswith("consult_duration_"):
        await handle_duration_selection(update, context)
    elif query.data.startswith("consult_slot_"):
        await handle_slot_selection(update, context)
    elif query.data == "consult_confirm":
        await confirm_consultation(update, context)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Конверсация для подачи заявки
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("apply", start_application),
            CallbackQueryHandler(start_application, pattern="^menu_apply$"),
        ],
        states={
            APPLICATION_PROBLEM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_problem)
            ],
            APPLICATION_ANSWERING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_answer)
            ],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("templates", show_catalog))
    app.add_handler(CommandHandler("consultation", show_consultation_menu))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot started")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
