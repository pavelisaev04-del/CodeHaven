from sqlalchemy import String, ForeignKey, Text, DateTime, Integer, Numeric, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid


class TemplateCategory(Base):
    __tablename__ = "template_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(50))   # emoji или имя иконки
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    templates: Mapped[list["Template"]] = relationship(back_populates="category")


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("template_categories.id"))

    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    preview_text: Mapped[str | None] = mapped_column(Text)   # фрагмент для предпросмотра

    # Файл шаблона
    file_path: Mapped[str] = mapped_column(String(500))      # путь к файлу (.docx/.pdf)
    file_format: Mapped[str] = mapped_column(String(10), default="docx")
    file_size_kb: Mapped[int | None] = mapped_column(Integer)

    # Ценообразование
    price: Mapped[Numeric] = mapped_column(Numeric(10, 2))
    original_price: Mapped[Numeric | None] = mapped_column(Numeric(10, 2))  # цена до скидки
    currency: Mapped[str] = mapped_column(String(3), default="RUB")

    # Теги для поиска
    tags: Mapped[list | None] = mapped_column(JSON)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)

    # Статистика
    sales_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[Numeric | None] = mapped_column(Numeric(3, 2))

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    category: Mapped["TemplateCategory"] = relationship(back_populates="templates")
    purchases: Mapped[list["TemplatePurchase"]] = relationship(back_populates="template")


class TemplatePurchase(Base):
    __tablename__ = "template_purchases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    template_id: Mapped[str] = mapped_column(String(36), ForeignKey("templates.id"), index=True)

    # Данные покупателя (если без регистрации)
    buyer_email: Mapped[str] = mapped_column(String(255))
    buyer_name: Mapped[str | None] = mapped_column(String(255))

    amount_paid: Mapped[Numeric] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    payment_id: Mapped[str | None] = mapped_column(String(100), index=True)

    # Ссылка для скачивания (временный токен)
    download_token: Mapped[str] = mapped_column(String(100), unique=True, index=True,
                                                default=lambda: str(uuid.uuid4()))
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    download_expires_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))

    telegram_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    purchased_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User | None"] = relationship(back_populates="purchases")
    template: Mapped["Template"] = relationship(back_populates="purchases")
    payment: Mapped["Payment | None"] = relationship(
        "Payment", primaryjoin="TemplatePurchase.payment_id == Payment.external_id",
        foreign_keys="TemplatePurchase.payment_id", viewonly=True
    )
