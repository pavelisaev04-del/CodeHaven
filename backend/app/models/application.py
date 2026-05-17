from sqlalchemy import String, ForeignKey, Text, DateTime, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base
import enum
import uuid


class ApplicationStatus(str, enum.Enum):
    NEW = "new"
    QUALIFYING = "qualifying"           # бот задаёт вопросы
    CLASSIFIED = "classified"           # тип определён
    AWAITING_CONSULTATION = "awaiting_consultation"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class LegalCategory(str, enum.Enum):
    CONSUMER_RIGHTS = "consumer_rights"         # права потребителя
    LABOR_DISPUTE = "labor_dispute"             # трудовой спор
    TAX = "tax"                                 # налоги
    FAMILY_LAW = "family_law"                   # семейное право
    PROPERTY = "property"                       # имущественные споры
    CRIMINAL = "criminal"                       # уголовное
    ADMINISTRATIVE = "administrative"           # административное
    BUSINESS = "business"                       # бизнес/корпоративное
    HOUSING = "housing"                         # жилищные вопросы
    OTHER = "other"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), index=True)

    # Контактные данные (заполняются без регистрации)
    contact_name: Mapped[str] = mapped_column(String(255))
    contact_email: Mapped[str] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(20))

    # Суть проблемы
    problem_description: Mapped[str] = mapped_column(Text)

    # Результат квалификации
    status: Mapped[ApplicationStatus] = mapped_column(
        SAEnum(ApplicationStatus), default=ApplicationStatus.NEW
    )
    legal_category: Mapped[LegalCategory | None] = mapped_column(SAEnum(LegalCategory))
    ai_summary: Mapped[str | None] = mapped_column(Text)           # краткий AI-анализ
    ai_questions: Mapped[list | None] = mapped_column(JSON)         # вопросы от AI
    ai_preliminary_answer: Mapped[str | None] = mapped_column(Text) # предварительный ответ

    # Сессия квалификации (шаги диалога)
    qualification_step: Mapped[int] = mapped_column(default=0)
    qualification_answers: Mapped[dict | None] = mapped_column(JSON)

    # Telegram source
    telegram_chat_id: Mapped[str | None] = mapped_column(String(50))

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="applications")
    messages: Mapped[list["ApplicationMessage"]] = relationship(back_populates="application")
    consultation: Mapped["Consultation | None"] = relationship(back_populates="application")


class ApplicationMessage(Base):
    """История переписки по заявке (для AI-контекста и консультанта)."""
    __tablename__ = "application_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id: Mapped[str] = mapped_column(String(36), ForeignKey("applications.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))   # "user" | "assistant" | "consultant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application: Mapped["Application"] = relationship(back_populates="messages")
