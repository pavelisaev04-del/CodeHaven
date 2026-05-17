from sqlalchemy import String, ForeignKey, Text, DateTime, Numeric, Enum as SAEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base
import enum
import uuid


class ConsultationStatus(str, enum.Enum):
    PENDING_PAYMENT = "pending_payment"
    SCHEDULED = "scheduled"
    REMINDER_SENT = "reminder_sent"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class ConsultationDuration(int, enum.Enum):
    MIN_30 = 30
    MIN_60 = 60
    MIN_90 = 90


class Consultation(Base):
    __tablename__ = "consultations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    application_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("applications.id"))

    # Клиент (без регистрации)
    client_name: Mapped[str] = mapped_column(String(255))
    client_email: Mapped[str] = mapped_column(String(255))
    client_phone: Mapped[str | None] = mapped_column(String(20))

    # Тип и время
    duration_minutes: Mapped[int] = mapped_column(default=60)
    scheduled_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")

    # Статус
    status: Mapped[ConsultationStatus] = mapped_column(
        SAEnum(ConsultationStatus), default=ConsultationStatus.PENDING_PAYMENT
    )

    # Оплата
    price: Mapped[Numeric] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    payment_id: Mapped[str | None] = mapped_column(String(100))

    # Ссылки
    calendly_event_uri: Mapped[str | None] = mapped_column(String(500))  # URI события в Calendly
    zoom_meeting_url: Mapped[str | None] = mapped_column(String(500))
    zoom_meeting_id: Mapped[str | None] = mapped_column(String(50))
    zoom_password: Mapped[str | None] = mapped_column(String(50))

    # Контент
    consultant_notes: Mapped[str | None] = mapped_column(Text)   # заметки консультанта
    client_feedback: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[int | None] = mapped_column()

    # Напоминания
    reminder_24h_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    reminder_1h_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    user: Mapped["User | None"] = relationship(back_populates="consultations")
    application: Mapped["Application | None"] = relationship(back_populates="consultation")
