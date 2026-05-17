"""
AI-сервис на базе Claude API.
Отвечает за:
  - классификацию юридических проблем
  - генерацию уточняющих вопросов
  - предварительную оценку ситуации
  - формирование краткого ответа клиенту
"""
import json
from anthropic import AsyncAnthropic
from app.config import get_settings
from app.models.application import LegalCategory

settings = get_settings()
client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

# Системный промпт для юридического ассистента
SYSTEM_PROMPT = """Ты — профессиональный юридический ассистент, работающий в России.
Твоя задача:
1. Классифицировать юридическую проблему клиента по категориям.
2. Задавать точные уточняющие вопросы для полного понимания ситуации.
3. Давать предварительную оценку ситуации (не юридическую консультацию, а общую ориентацию).

Категории проблем:
- consumer_rights: права потребителя, претензии к продавцам/исполнителям
- labor_dispute: трудовые споры, увольнение, зарплата
- tax: налоговые вопросы
- family_law: развод, алименты, раздел имущества
- property: недвижимость, аренда, покупка/продажа
- criminal: уголовные дела
- administrative: административные правонарушения, штрафы
- business: корпоративное право, договоры, ИП/ООО
- housing: ЖКХ, управляющие компании, соседи
- other: прочее

Отвечай ТОЛЬКО на русском языке. Будь кратким, профессиональным и доброжелательным.
Не давай конкретных юридических советов — только ориентацию и рекомендацию обратиться к консультанту."""


async def classify_and_analyze(problem_description: str) -> dict:
    """
    Основная функция первичного анализа.
    Возвращает: category, questions, summary, preliminary_answer
    """
    prompt = f"""Клиент описал свою проблему:

"{problem_description}"

Выполни следующие задачи и верни ответ строго в JSON формате:
{{
    "category": "<одна из категорий>",
    "confidence": <0.0-1.0>,
    "summary": "<краткое описание проблемы в 1-2 предложениях>",
    "preliminary_answer": "<предварительная ориентация для клиента, 2-4 предложения>",
    "questions": [
        {{"id": 1, "text": "<вопрос 1>", "hint": "<подсказка к вопросу>"}},
        {{"id": 2, "text": "<вопрос 2>", "hint": "..."}},
        {{"id": 3, "text": "<вопрос 3>", "hint": "..."}},
        {{"id": 4, "text": "<вопрос 4>", "hint": "..."}},
        {{"id": 5, "text": "<вопрос 5>", "hint": "..."}}
    ],
    "recommended_templates": ["<название шаблона 1 если применимо>"],
    "urgency": "low|medium|high"
}}"""

    response = await client.messages.create(
        model=settings.AI_MODEL,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text
    # Извлекаем JSON из ответа (Claude иногда добавляет текст вокруг)
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])


async def generate_clarifying_answer(
    problem_description: str,
    qa_pairs: list[dict],  # [{"question": "...", "answer": "..."}]
) -> dict:
    """
    После получения ответов на 5 вопросов генерирует итоговый анализ.
    Возвращает: detailed_summary, recommendations, next_steps
    """
    qa_text = "\n".join(
        f"В: {qa['question']}\nО: {qa['answer']}" for qa in qa_pairs
    )

    prompt = f"""Первоначальное описание проблемы:
"{problem_description}"

Уточняющие ответы клиента:
{qa_text}

На основе полной информации верни JSON:
{{
    "detailed_summary": "<подробный анализ ситуации, 3-5 предложений>",
    "key_facts": ["<ключевой факт 1>", "<ключевой факт 2>"],
    "risks": ["<риск или сложность 1>"],
    "recommendations": "<что рекомендуется сделать клиенту>",
    "next_steps": "<следующий шаг: записаться на консультацию / купить шаблон / ...>",
    "suggested_documents": ["<документ 1 который может понадобиться>"],
    "consultation_value": "<почему консультация специалиста важна в этом случае>"
}}"""

    response = await client.messages.create(
        model=settings.AI_MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])


async def get_next_question(
    problem_description: str,
    previous_qa: list[dict],
    question_number: int,
) -> dict:
    """
    Динамически генерирует следующий вопрос с учётом предыдущих ответов.
    Используется для адаптивного диалога (вместо статичного списка из 5 вопросов).
    """
    history = "\n".join(
        f"В{i+1}: {qa['question']}\nО: {qa['answer']}"
        for i, qa in enumerate(previous_qa)
    )

    prompt = f"""Проблема клиента: "{problem_description}"

Уже заданные вопросы и ответы:
{history}

Это вопрос №{question_number} из 5. Задай ОДИН наиболее важный следующий уточняющий вопрос.
Верни JSON: {{"question": "...", "hint": "..."}}"""

    response = await client.messages.create(
        model=settings.AI_MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])


async def match_templates_to_problem(
    problem_description: str,
    available_templates: list[dict],
) -> list[str]:
    """
    Подбирает подходящие шаблоны документов к описанной проблеме.
    Возвращает список ID подходящих шаблонов (до 3).
    """
    template_list = "\n".join(
        f"- ID: {t['id']}, Название: {t['name']}, Описание: {t['description']}"
        for t in available_templates
    )

    prompt = f"""Проблема клиента: "{problem_description}"

Доступные шаблоны документов:
{template_list}

Верни JSON со списком ID подходящих шаблонов (максимум 3, только если реально применимы):
{{"template_ids": ["id1", "id2"], "explanation": "краткое пояснение почему эти шаблоны подходят"}}"""

    response = await client.messages.create(
        model=settings.AI_MODEL,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text
    start = text.find("{")
    end = text.rfind("}") + 1
    result = json.loads(text[start:end])
    return result.get("template_ids", [])
