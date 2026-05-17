"""
Сервис платежей.
Поддерживает Stripe и ЮКасса.
Легко расширяется на новые провайдеры.
"""
import stripe
from yookassa import Configuration as YooConfig, Payment as YooPayment
from decimal import Decimal
from typing import Optional
from app.config import get_settings
from app.models.payment import PaymentProvider, PaymentType

settings = get_settings()
stripe.api_key = settings.STRIPE_SECRET_KEY

if settings.YOOKASSA_SHOP_ID:
    YooConfig.account_id = settings.YOOKASSA_SHOP_ID
    YooConfig.secret_key = settings.YOOKASSA_SECRET_KEY


async def create_stripe_session(
    amount: Decimal,
    currency: str,
    description: str,
    success_url: str,
    cancel_url: str,
    metadata: dict,
) -> dict:
    """Создаёт Stripe Checkout Session."""
    amount_cents = int(amount * 100)
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": currency.lower(),
                "product_data": {"name": description},
                "unit_amount": amount_cents,
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
    )
    return {"external_id": session.id, "checkout_url": session.url}


async def create_yookassa_payment(
    amount: Decimal,
    currency: str,
    description: str,
    return_url: str,
    metadata: dict,
    idempotency_key: str,
) -> dict:
    """Создаёт платёж в ЮКасса."""
    payment = YooPayment.create({
        "amount": {"value": str(amount), "currency": currency},
        "confirmation": {"type": "redirect", "return_url": return_url},
        "description": description,
        "metadata": metadata,
        "capture": True,
    }, idempotency_key)

    return {
        "external_id": payment.id,
        "checkout_url": payment.confirmation.confirmation_url,
    }


async def create_payment(
    payment_type: PaymentType,
    amount: Decimal,
    currency: str,
    description: str,
    reference_id: str,
    success_url: str,
    cancel_url: str,
    user_id: Optional[str] = None,
    provider: PaymentProvider = PaymentProvider.YOOKASSA,
) -> dict:
    """
    Унифицированный метод создания платежа.
    Возвращает: {external_id, checkout_url, provider}
    """
    metadata = {
        "payment_type": payment_type,
        "reference_id": reference_id,
        "user_id": user_id or "",
    }

    if provider == PaymentProvider.STRIPE:
        result = await create_stripe_session(
            amount, currency, description, success_url, cancel_url, metadata
        )
    elif provider == PaymentProvider.YOOKASSA:
        result = await create_yookassa_payment(
            amount, currency, description, success_url, metadata,
            idempotency_key=reference_id
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    return {**result, "provider": provider}


def verify_stripe_webhook(payload: bytes, sig_header: str) -> dict:
    """Верифицирует и парсит Stripe webhook."""
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )


def verify_yookassa_webhook(data: dict) -> bool:
    """Базовая проверка события ЮКасса (по IP и структуре)."""
    # В production добавить проверку IP ЮКасса: 185.71.76.0/27
    return data.get("type") in ("payment.succeeded", "payment.canceled", "refund.succeeded")
