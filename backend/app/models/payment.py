from sqlalchemy import String, ForeignKey, Numeric, DateTime, Enum as SAEnum, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base
import enum
import uuid


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentProvider(str, enum.Enum):
    STRIPE = "stripe"
    YOOKASSA = "yookassa"
    TELEGRAM = "telegram"   # Telegram Stars / Payments


class PaymentType(str, enum.Enum):
    TEMPLATE = "template"
    CONSULTATION = "consultation"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), index=True)

    payment_type: Mapped[PaymentType] = mapped_column(SAEnum(PaymentType))
    provider: Mapped[PaymentProvider] = mapped_column(SAEnum(PaymentProvider))
    status: Mapped[PaymentStatus] = mapped_column(SAEnum(PaymentStatus), default=PaymentStatus.PENDING)

    amount: Mapped[Numeric] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="RUB")

    # ID платежа у провайдера
    external_id: Mapped[str | None] = mapped_column(String(200), index=True)
    # URL для редиректа на оплату
    checkout_url: Mapped[str | None] = mapped_column(Text)
    # Сырой ответ провайдера
    provider_data: Mapped[dict | None] = mapped_column(JSON)

    # Ссылка на то, что оплачивается
    reference_id: Mapped[str | None] = mapped_column(String(36))   # template_purchase.id или consultation.id

    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User | None"] = relationship(back_populates="payments")
