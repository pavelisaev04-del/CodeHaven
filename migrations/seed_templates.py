"""
Начальное наполнение каталога шаблонов.
Запускать: python migrations/seed_templates.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import AsyncSessionLocal, init_db
from app.models.template import Template, TemplateCategory

CATEGORIES = [
    {"name": "Права потребителя", "slug": "consumer", "icon": "⚖️", "sort_order": 1},
    {"name": "Трудовые споры",    "slug": "labor",    "icon": "👷", "sort_order": 2},
    {"name": "Недвижимость",      "slug": "property", "icon": "🏠", "sort_order": 3},
    {"name": "Семейное право",    "slug": "family",   "icon": "👨‍👩‍👧", "sort_order": 4},
    {"name": "ЖКХ",              "slug": "housing",  "icon": "🏢", "sort_order": 5},
]

TEMPLATES = [
    # Права потребителя
    {
        "category_slug": "consumer",
        "name": "Претензия к продавцу о возврате товара",
        "slug": "pretenziya-vozvrat-tovara",
        "description": "Универсальная претензия для возврата товара ненадлежащего качества. Ссылки на ст. 18, 22, 23 Закона о защите прав потребителей.",
        "preview_text": "Руководителю ООО «___»\nот ___\n\nПРЕТЕНЗИЯ\n\nЯ, ___, приобрёл(а) у Вас ____ (дата: ___), стоимостью ____ рублей. Товар оказался ненадлежащего качества...",
        "price": 500,
        "original_price": 800,
        "file_format": "docx",
        "tags": ["претензия", "возврат", "покупка", "товар"],
        "is_featured": True,
    },
    {
        "category_slug": "consumer",
        "name": "Претензия в страховую компанию (ОСАГО/КАСКО)",
        "slug": "pretenziya-strakhovaya",
        "description": "Готовая претензия к страховщику с требованием о выплате страхового возмещения в срок.",
        "preview_text": "В АО «Страховая компания ___»\nот ___\n\nПРЕТЕНЗИЯ О ВЫПЛАТЕ СТРАХОВОГО ВОЗМЕЩЕНИЯ\n\nМежду мной и Вашей организацией заключён договор страхования...",
        "price": 700,
        "file_format": "docx",
        "tags": ["страховая", "ОСАГО", "КАСКО", "претензия"],
    },
    {
        "category_slug": "consumer",
        "name": "Чек-лист: как вернуть товар в магазин",
        "slug": "chek-list-vozvrat-tovara",
        "description": "Пошаговый чек-лист с законными основаниями, сроками и шаблонами обращений.",
        "preview_text": "ЧЕК-ЛИСТ ВОЗВРАТА ТОВАРА\n\n□ Шаг 1. Определите основание для возврата\n  - Надлежащего качества (14 дней)\n  - Ненадлежащего качества (гарантийный срок)\n□ Шаг 2...",
        "price": 500,
        "file_format": "pdf",
        "tags": ["чек-лист", "возврат", "права потребителя"],
        "is_featured": True,
    },
    # Трудовые споры
    {
        "category_slug": "labor",
        "name": "Заявление о незаконном увольнении в трудовую инспекцию",
        "slug": "zayavlenie-trudovaya-inspekciya",
        "description": "Заявление в Государственную инспекцию труда с требованием проверки законности увольнения.",
        "preview_text": "В Государственную инспекцию труда\nпо г. ___\nот ___\n\nЗАЯВЛЕНИЕ\n\nПрошу провести проверку по факту незаконного увольнения...",
        "price": 600,
        "file_format": "docx",
        "tags": ["увольнение", "трудовая инспекция", "жалоба"],
    },
    {
        "category_slug": "labor",
        "name": "Претензия работодателю о невыплате зарплаты",
        "slug": "pretenziya-nevyplata-zarplaty",
        "description": "Претензия с расчётом задолженности и ссылками на ст. 140, 236 ТК РФ об ответственности.",
        "preview_text": "Директору ___\nот ___\n\nПРЕТЕНЗИЯ\n\nВ нарушение ст. 136 ТК РФ вам не выплачена заработная плата за период...",
        "price": 600,
        "file_format": "docx",
        "tags": ["зарплата", "задолженность", "трудовой кодекс"],
    },
    # Недвижимость
    {
        "category_slug": "property",
        "name": "Претензия арендодателю о возврате залога",
        "slug": "pretenziya-vozvrat-zaloga",
        "description": "Претензия к арендодателю с требованием вернуть обеспечительный платёж при отсутствии ущерба.",
        "preview_text": "___\nот ___\n\nПРЕТЕНЗИЯ О ВОЗВРАТЕ ОБЕСПЕЧИТЕЛЬНОГО ПЛАТЕЖА\n\nМежду нами заключён договор аренды жилого помещения...",
        "price": 700,
        "file_format": "docx",
        "tags": ["аренда", "залог", "депозит"],
    },
    # ЖКХ
    {
        "category_slug": "housing",
        "name": "Жалоба в жилищную инспекцию на управляющую компанию",
        "slug": "zhaloba-zhilischnaya-inspekciya",
        "description": "Шаблон жалобы на бездействие УК: протечки, отключения, ненадлежащее содержание.",
        "preview_text": "В Государственную жилищную инспекцию\nпо г. ___\nот ___\n\nЖАЛОБА\n\nПрошу провести проверку деятельности управляющей компании ООО «___»...",
        "price": 500,
        "file_format": "docx",
        "tags": ["УК", "жилищная инспекция", "ЖКХ"],
    },
]


async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        # Категории
        cat_map = {}
        for cat_data in CATEGORIES:
            cat = TemplateCategory(**cat_data, is_active=True)
            db.add(cat)
            await db.flush()
            cat_map[cat_data["slug"]] = cat.id
            print(f"  Category: {cat_data['name']}")

        # Шаблоны
        for t_data in TEMPLATES:
            slug = t_data.pop("category_slug")
            t = Template(
                category_id=cat_map[slug],
                file_path=f"./uploads/templates/{t_data['slug']}.{t_data['file_format']}",
                currency="RUB",
                is_active=True,
                is_featured=t_data.pop("is_featured", False),
                **t_data,
            )
            db.add(t)
            print(f"  Template: {t.name}")

        await db.commit()
        print("Seed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
