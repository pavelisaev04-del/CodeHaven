from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Подать заявку", callback_data="menu_apply")],
        [InlineKeyboardButton("📄 Шаблоны документов", callback_data="menu_templates")],
        [InlineKeyboardButton("🗓 Записаться на консультацию", callback_data="menu_consultation")],
    ])


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("← Главное меню", callback_data="menu_main")]
    ])


def consultation_duration_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("30 мин — 2 500 ₽", callback_data="consult_duration_30")],
        [InlineKeyboardButton("60 мин — 4 500 ₽", callback_data="consult_duration_60")],
        [InlineKeyboardButton("90 мин — 6 500 ₽", callback_data="consult_duration_90")],
        [InlineKeyboardButton("← Назад", callback_data="menu_main")],
    ])


def template_catalog_keyboard(templates: list[dict]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"📄 {t['name']} — {t['price']} ₽", callback_data=f"template_{t['id']}")]
        for t in templates
    ]
    buttons.append([InlineKeyboardButton("← Назад", callback_data="menu_main")])
    return InlineKeyboardMarkup(buttons)


def template_detail_keyboard(template_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Купить", callback_data=f"buy_{template_id}")],
        [InlineKeyboardButton("← К списку", callback_data="menu_templates")],
    ])


def slots_keyboard(slots: list[dict]) -> InlineKeyboardMarkup:
    """Клавиатура выбора слота (показываем первые 8)."""
    from datetime import datetime
    buttons = []
    for i, slot in enumerate(slots[:8]):
        dt = datetime.fromisoformat(slot["start_time"])
        label = dt.strftime("%d.%m %H:%M")
        buttons.append([InlineKeyboardButton(label, callback_data=f"consult_slot_{i}")])
    buttons.append([InlineKeyboardButton("← Назад", callback_data="menu_consultation")])
    return InlineKeyboardMarkup(buttons)
