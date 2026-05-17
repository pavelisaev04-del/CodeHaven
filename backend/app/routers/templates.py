"""
Роутер шаблонов документов.
GET  /templates/              — каталог
GET  /templates/{id}          — детали шаблона
POST /templates/{id}/purchase — создать платёж для покупки
GET  /templates/download/{token} — скачать файл по токену
GET  /templates/webhook/payment  — webhook от платёжной системы
"""
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta, timezone
import uuid

from app.database import get_db
from app.models.template import Template, TemplateCategory, TemplatePurchase
from app.models.payment import Payment, PaymentStatus, PaymentType, PaymentProvider
from app.services import payment_service, notification_service
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/templates", tags=["templates"])


class PurchaseRequest(BaseModel):
    buyer_email: EmailStr
    buyer_name: str
    telegram_chat_id: Optional[str] = None
    # "stripe" | "yookassa"
    payment_provider: str = "yookassa"


class TemplateOut(BaseModel):
    id: str
    name: str
    description: str
    preview_text: Optional[str]
    price: float
    original_price: Optional[float]
    currency: str
    category_name: str
    tags: Optional[list]
    sales_count: int
    is_featured: bool
    file_format: str


class PurchaseOut(BaseModel):
    purchase_id: str
    checkout_url: str


@router.get("/", response_model=list[TemplateOut])
async def list_templates(
    category_slug: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Template, TemplateCategory)
        .join(TemplateCategory)
        .where(Template.is_active == True)
    )
    if category_slug:
        stmt = stmt.where(TemplateCategory.slug == category_slug)
    stmt = stmt.order_by(Template.is_featured.desc(), Template.sales_count.desc())

    result = await db.execute(stmt)
    rows = result.all()

    return [
        TemplateOut(
            id=t.id,
            name=t.name,
            description=t.description,
            preview_text=t.preview_text,
            price=float(t.price),
            original_price=float(t.original_price) if t.original_price else None,
            currency=t.currency,
            category_name=c.name,
            tags=t.tags,
            sales_count=t.sales_count,
            is_featured=t.is_featured,
            file_format=t.file_format,
        )
        for t, c in rows
    ]


@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Template, TemplateCategory)
        .join(TemplateCategory)
        .where(Template.id == template_id, Template.is_active == True)
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "Template not found")
    t, c = row
    # Увеличиваем счётчик просмотров
    await db.execute(update(Template).where(Template.id == t.id).values(view_count=t.view_count + 1))
    return TemplateOut(
        id=t.id, name=t.name, description=t.description,
        preview_text=t.preview_text, price=float(t.price),
        original_price=float(t.original_price) if t.original_price else None,
        currency=t.currency, category_name=c.name,
        tags=t.tags, sales_count=t.sales_count,
        is_featured=t.is_featured, file_format=t.file_format,
    )


@router.post("/{template_id}/purchase", response_model=PurchaseOut)
async def purchase_template(
    template_id: str,
    data: PurchaseRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Создаёт покупку и возвращает ссылку на оплату.
    После успешной оплаты webhook автоматически выдаёт шаблон.
    """
    template = await db.get(Template, template_id)
    if not template or not template.is_active:
        raise HTTPException(404, "Template not found")

    # Создаём запись покупки со статусом "ожидание оплаты"
    purchase = TemplatePurchase(
        template_id=template_id,
        buyer_email=data.buyer_email,
        buyer_name=data.buyer_name,
        amount_paid=template.price,
        currency=template.currency,
        download_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        telegram_sent=False,
        email_sent=False,
    )
    db.add(purchase)
    await db.flush()

    base_url = str(request.base_url).rstrip("/")
    provider = PaymentProvider(data.payment_provider)

    pay_result = await payment_service.create_payment(
        payment_type=PaymentType.TEMPLATE,
        amount=template.price,
        currency=template.currency,
        description=f"Шаблон «{template.name}»",
        reference_id=purchase.id,
        success_url=f"{base_url}/payment/success?purchase={purchase.id}",
        cancel_url=f"{base_url}/payment/cancel?purchase={purchase.id}",
        provider=provider,
    )

    # Создаём запись платежа
    payment = Payment(
        payment_type=PaymentType.TEMPLATE,
        provider=provider,
        status=PaymentStatus.PENDING,
        amount=template.price,
        currency=template.currency,
        external_id=pay_result["external_id"],
        checkout_url=pay_result["checkout_url"],
        reference_id=purchase.id,
    )
    db.add(payment)
    purchase.payment_id = pay_result["external_id"]

    await db.commit()
    return PurchaseOut(purchase_id=purchase.id, checkout_url=pay_result["checkout_url"])


@router.get("/download/{token}")
async def download_template(token: str, db: AsyncSession = Depends(get_db)):
    """Скачивание шаблона по одноразовому токену."""
    result = await db.execute(
        select(TemplatePurchase, Template)
        .join(Template)
        .where(TemplatePurchase.download_token == token)
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "Download link not found or expired")

    purchase, template = row

    if purchase.download_expires_at and purchase.download_expires_at < datetime.now(timezone.utc):
        raise HTTPException(410, "Download link expired")

    await db.execute(
        update(TemplatePurchase)
        .where(TemplatePurchase.id == purchase.id)
        .values(download_count=purchase.download_count + 1)
    )

    filename = f"{template.slug}.{template.file_format}"
    return FileResponse(
        template.file_path,
        media_type="application/octet-stream",
        filename=filename,
    )


@router.post("/webhook/yookassa")
async def yookassa_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Webhook от ЮКасса — обрабатывает успешную оплату шаблона."""
    data = await request.json()

    if not payment_service.verify_yookassa_webhook(data):
        raise HTTPException(400, "Invalid webhook")

    if data.get("type") != "payment.succeeded":
        return {"status": "ignored"}

    yoo_payment = data["object"]
    payment = await db.execute(
        select(Payment).where(Payment.external_id == yoo_payment["id"])
    )
    payment = payment.scalar_one_or_none()

    if not payment or payment.status == PaymentStatus.SUCCEEDED:
        return {"status": "already_processed"}

    payment.status = PaymentStatus.SUCCEEDED
    payment.completed_at = datetime.now(timezone.utc)
    await db.flush()

    purchase = await db.get(TemplatePurchase, payment.reference_id)
    if purchase:
        template = await db.get(Template, purchase.template_id)
        background_tasks.add_task(
            _deliver_template, purchase.id, template.id, db
        )

    await db.commit()
    return {"status": "ok"}


async def _deliver_template(purchase_id: str, template_id: str, db: AsyncSession):
    """Фоновая задача: отправить шаблон после оплаты."""
    purchase = await db.get(TemplatePurchase, purchase_id)
    template = await db.get(Template, template_id)
    if not purchase or not template:
        return

    base_url = "https://yourdomain.com"
    download_url = f"{base_url}/api/templates/download/{purchase.download_token}"

    # Email
    if not purchase.email_sent:
        sent = await notification_service.send_template_purchase_email(
            to_email=purchase.buyer_email,
            to_name=purchase.buyer_name or "Клиент",
            template_name=template.name,
            download_url=download_url,
        )
        if sent:
            purchase.email_sent = True

    # Telegram (если клиент пришёл через бота)
    # Ищем пользователя по email
    # (в боте telegram_chat_id сохраняется в purchase)

    # Обновляем счётчик продаж
    await db.execute(
        update(Template)
        .where(Template.id == template_id)
        .values(sales_count=template.sales_count + 1)
    )
    await db.commit()
