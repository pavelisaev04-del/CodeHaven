"""
Роутер онлайн-консультаций.
POST /consultations/          — создать бронь + оплату
GET  /consultations/slots     — доступные слоты (Calendly)
POST /consultations/webhook/calendly — Calendly webhook (событие забронировано)
POST /consultations/webhook/yookassa — ЮКасса webhook (оплата)
GET  /consultations/{id}      — статус консультации
"""
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models.consultation import Consultation, ConsultationStatus
from app.models.payment import Payment, PaymentStatus, PaymentType, PaymentProvider
from app.services import payment_service, notification_service, calendar_service
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/consultations", tags=["consultations"])

# Цены на консультации (минуты → цена в рублях)
CONSULTATION_PRICES = {30: 2500, 60: 4500, 90: 6500}


class BookConsultationRequest(BaseModel):
    client_name: str
    client_email: EmailStr
    client_phone: Optional[str] = None
    duration_minutes: int = 60
    scheduled_at: str           # ISO 8601
    timezone: str = "Europe/Moscow"
    application_id: Optional[str] = None
    payment_provider: str = "yookassa"


class ConsultationOut(BaseModel):
    id: str
    status: str
    client_name: str
    scheduled_at: Optional[str]
    zoom_url: Optional[str]
    price: float
    checkout_url: Optional[str]


@router.get("/slots")
async def get_available_slots(
    event_type_uri: Optional[str] = None,
    days_ahead: int = 14,
):
    """
    Возвращает доступные слоты из Calendly.
    Если Calendly не настроен — возвращает заглушку.
    """
    if not settings.CALENDLY_API_KEY:
        # DEV: генерируем демо-слоты
        from datetime import date, timedelta
        slots = []
        now = datetime.now(timezone.utc)
        for day in range(1, days_ahead + 1):
            d = now + timedelta(days=day)
            if d.weekday() < 5:   # рабочие дни
                for hour in [10, 12, 14, 16, 18]:
                    slots.append({
                        "start_time": d.replace(hour=hour, minute=0, second=0, microsecond=0).isoformat(),
                        "status": "available",
                    })
        return {"slots": slots[:20]}

    uri = event_type_uri or settings.CALENDLY_USER_URI
    start = datetime.now(timezone.utc).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).isoformat()
    slots = await calendar_service.get_calendly_available_slots(uri, start, end)
    return {"slots": slots}


@router.post("/", response_model=ConsultationOut, status_code=201)
async def book_consultation(
    data: BookConsultationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Создаёт запись на консультацию и возвращает ссылку на оплату.
    Zoom-встреча создаётся автоматически после успешной оплаты.
    """
    price = CONSULTATION_PRICES.get(data.duration_minutes)
    if not price:
        raise HTTPException(400, f"Unsupported duration. Use: {list(CONSULTATION_PRICES.keys())}")

    consultation = Consultation(
        application_id=data.application_id,
        client_name=data.client_name,
        client_email=data.client_email,
        client_phone=data.client_phone,
        duration_minutes=data.duration_minutes,
        scheduled_at=datetime.fromisoformat(data.scheduled_at),
        timezone=data.timezone,
        status=ConsultationStatus.PENDING_PAYMENT,
        price=price,
        currency="RUB",
    )
    db.add(consultation)
    await db.flush()

    base_url = str(request.base_url).rstrip("/")
    provider = PaymentProvider(data.payment_provider)

    pay_result = await payment_service.create_payment(
        payment_type=PaymentType.CONSULTATION,
        amount=price,
        currency="RUB",
        description=f"Юридическая консультация {data.duration_minutes} мин.",
        reference_id=consultation.id,
        success_url=f"{base_url}/payment/success?consultation={consultation.id}",
        cancel_url=f"{base_url}/payment/cancel?consultation={consultation.id}",
        provider=provider,
    )

    db.add(Payment(
        payment_type=PaymentType.CONSULTATION,
        provider=provider,
        status=PaymentStatus.PENDING,
        amount=price,
        currency="RUB",
        external_id=pay_result["external_id"],
        checkout_url=pay_result["checkout_url"],
        reference_id=consultation.id,
    ))
    consultation.payment_id = pay_result["external_id"]

    await db.commit()

    return ConsultationOut(
        id=consultation.id,
        status=consultation.status,
        client_name=consultation.client_name,
        scheduled_at=data.scheduled_at,
        zoom_url=None,
        price=float(price),
        checkout_url=pay_result["checkout_url"],
    )


@router.post("/webhook/yookassa")
async def consultation_payment_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """После успешной оплаты автоматически создаёт Zoom и отправляет письмо."""
    data = await request.json()

    if not payment_service.verify_yookassa_webhook(data):
        raise HTTPException(400, "Invalid webhook")

    if data.get("type") != "payment.succeeded":
        return {"status": "ignored"}

    external_id = data["object"]["id"]
    result = await db.execute(select(Payment).where(Payment.external_id == external_id))
    payment = result.scalar_one_or_none()

    if not payment or payment.status == PaymentStatus.SUCCEEDED:
        return {"status": "already_processed"}

    if payment.payment_type != PaymentType.CONSULTATION:
        return {"status": "not_consultation"}

    payment.status = PaymentStatus.SUCCEEDED
    payment.completed_at = datetime.now(timezone.utc)

    consultation = await db.get(Consultation, payment.reference_id)
    if consultation:
        consultation.status = ConsultationStatus.SCHEDULED
        background_tasks.add_task(_setup_consultation, consultation.id, db)

    await db.commit()
    return {"status": "ok"}


@router.get("/{consultation_id}", response_model=ConsultationOut)
async def get_consultation(consultation_id: str, db: AsyncSession = Depends(get_db)):
    c = await db.get(Consultation, consultation_id)
    if not c:
        raise HTTPException(404, "Consultation not found")
    return ConsultationOut(
        id=c.id,
        status=c.status,
        client_name=c.client_name,
        scheduled_at=c.scheduled_at.isoformat() if c.scheduled_at else None,
        zoom_url=c.zoom_meeting_url,
        price=float(c.price),
        checkout_url=None,
    )


async def _setup_consultation(consultation_id: str, db: AsyncSession):
    """
    Фоновая задача после оплаты:
    1. Создаёт Zoom-встречу
    2. Отправляет письмо с подтверждением
    """
    c = await db.get(Consultation, consultation_id)
    if not c:
        return

    # Создаём Zoom
    if settings.ZOOM_ACCOUNT_ID:
        zoom = await calendar_service.create_zoom_meeting(
            topic=f"Юридическая консультация — {c.client_name}",
            start_time=c.scheduled_at.isoformat(),
            duration_minutes=c.duration_minutes,
            timezone=c.timezone,
        )
        c.zoom_meeting_url = zoom["join_url"]
        c.zoom_meeting_id = zoom["meeting_id"]
        c.zoom_password = zoom["password"]
    else:
        # Fallback: Google Meet или заглушка
        c.zoom_meeting_url = "https://meet.google.com/placeholder"

    # Отправляем письмо с подтверждением
    scheduled_str = c.scheduled_at.strftime("%d.%m.%Y %H:%M") if c.scheduled_at else "—"
    await notification_service.send_consultation_confirmation_email(
        to_email=c.client_email,
        to_name=c.client_name,
        scheduled_at=f"{scheduled_str} (МСК)",
        zoom_url=c.zoom_meeting_url,
        zoom_password=c.zoom_password,
    )

    await db.commit()
