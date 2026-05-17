"""
Роутер заявок.
POST /applications/           — создать заявку и запустить квалификацию
POST /applications/{id}/answer — ответить на вопрос квалификации
GET  /applications/{id}       — статус заявки
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.database import get_db
from app.models.application import Application, ApplicationMessage, ApplicationStatus
from app.services import ai_service

router = APIRouter(prefix="/applications", tags=["applications"])


class CreateApplicationRequest(BaseModel):
    contact_name: str
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    problem_description: str
    telegram_chat_id: Optional[str] = None


class AnswerQuestionRequest(BaseModel):
    question_id: int
    answer: str


class ApplicationResponse(BaseModel):
    id: str
    status: str
    legal_category: Optional[str]
    ai_summary: Optional[str]
    ai_preliminary_answer: Optional[str]
    current_question: Optional[dict]
    qualification_step: int
    total_questions: int = 5
    completed: bool

    class Config:
        from_attributes = True


@router.post("/", response_model=ApplicationResponse, status_code=201)
async def create_application(
    data: CreateApplicationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Шаг 1: Клиент подаёт заявку.
    AI сразу классифицирует проблему и генерирует 5 вопросов.
    """
    # Запускаем AI-анализ
    ai_result = await ai_service.classify_and_analyze(data.problem_description)

    app = Application(
        contact_name=data.contact_name,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        problem_description=data.problem_description,
        telegram_chat_id=data.telegram_chat_id,
        status=ApplicationStatus.QUALIFYING,
        legal_category=ai_result.get("category"),
        ai_summary=ai_result.get("summary"),
        ai_preliminary_answer=ai_result.get("preliminary_answer"),
        ai_questions=ai_result.get("questions", []),
        qualification_step=0,
        qualification_answers={},
    )
    db.add(app)
    await db.flush()

    # Сохраняем первое сообщение клиента
    db.add(ApplicationMessage(
        application_id=app.id,
        role="user",
        content=data.problem_description,
    ))
    # Сохраняем AI-ответ
    db.add(ApplicationMessage(
        application_id=app.id,
        role="assistant",
        content=ai_result.get("preliminary_answer", ""),
    ))

    await db.commit()
    await db.refresh(app)

    questions = app.ai_questions or []
    current_q = questions[0] if questions else None

    return ApplicationResponse(
        id=app.id,
        status=app.status,
        legal_category=app.legal_category,
        ai_summary=app.ai_summary,
        ai_preliminary_answer=app.ai_preliminary_answer,
        current_question=current_q,
        qualification_step=0,
        completed=False,
    )


@router.post("/{application_id}/answer", response_model=ApplicationResponse)
async def answer_question(
    application_id: str,
    data: AnswerQuestionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Шаг 2–6: Клиент отвечает на уточняющий вопрос.
    После 5-го ответа генерируется итоговый анализ.
    """
    app = await db.get(Application, application_id)
    if not app:
        raise HTTPException(404, "Application not found")

    if app.status == ApplicationStatus.CLASSIFIED:
        raise HTTPException(400, "Qualification already completed")

    questions = app.ai_questions or []
    step = app.qualification_step
    answers = app.qualification_answers or {}

    if step >= len(questions):
        raise HTTPException(400, "All questions already answered")

    current_q = questions[step]

    # Сохраняем ответ
    answers[str(step)] = {
        "question": current_q["text"],
        "answer": data.answer,
    }
    app.qualification_answers = answers
    app.qualification_step = step + 1

    # Сохраняем в историю сообщений
    db.add(ApplicationMessage(application_id=app.id, role="user",
                               content=f"[Q{step+1}] {current_q['text']}\n{data.answer}"))

    is_last = app.qualification_step >= 5

    if is_last:
        # Все вопросы отвечены — получаем итоговый анализ
        qa_list = [
            {"question": v["question"], "answer": v["answer"]}
            for v in answers.values()
        ]
        final = await ai_service.generate_clarifying_answer(app.problem_description, qa_list)

        app.ai_summary = final.get("detailed_summary")
        app.ai_preliminary_answer = final.get("recommendations")
        app.status = ApplicationStatus.CLASSIFIED

        db.add(ApplicationMessage(
            application_id=app.id, role="assistant",
            content=final.get("detailed_summary", ""),
        ))

    await db.commit()
    await db.refresh(app)

    next_q = None
    if not is_last and app.qualification_step < len(questions):
        next_q = questions[app.qualification_step]

    return ApplicationResponse(
        id=app.id,
        status=app.status,
        legal_category=app.legal_category,
        ai_summary=app.ai_summary,
        ai_preliminary_answer=app.ai_preliminary_answer,
        current_question=next_q,
        qualification_step=app.qualification_step,
        completed=is_last,
    )


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(application_id: str, db: AsyncSession = Depends(get_db)):
    app = await db.get(Application, application_id)
    if not app:
        raise HTTPException(404, "Application not found")

    questions = app.ai_questions or []
    step = app.qualification_step
    current_q = questions[step] if step < len(questions) else None

    return ApplicationResponse(
        id=app.id,
        status=app.status,
        legal_category=app.legal_category,
        ai_summary=app.ai_summary,
        ai_preliminary_answer=app.ai_preliminary_answer,
        current_question=current_q,
        qualification_step=step,
        completed=app.status == ApplicationStatus.CLASSIFIED,
    )
