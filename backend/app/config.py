from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "LegalService"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "https://yourdomain.com"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/legalservice"

    # Claude AI
    ANTHROPIC_API_KEY: str = ""
    AI_MODEL: str = "claude-sonnet-4-6"

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: Optional[str] = None

    # Stripe payments
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # YooKassa (alternative RU payment)
    YOOKASSA_SHOP_ID: Optional[str] = None
    YOOKASSA_SECRET_KEY: Optional[str] = None

    # Calendly / TidyCal
    CALENDLY_API_KEY: Optional[str] = None
    CALENDLY_USER_URI: Optional[str] = None
    TIDYCAL_API_KEY: Optional[str] = None

    # Zoom
    ZOOM_ACCOUNT_ID: Optional[str] = None
    ZOOM_CLIENT_ID: Optional[str] = None
    ZOOM_CLIENT_SECRET: Optional[str] = None

    # Email (SendGrid / SMTP)
    SENDGRID_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "noreply@yourdomain.com"
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    # File storage
    STORAGE_BACKEND: str = "local"  # "local" | "s3"
    UPLOAD_DIR: str = "./uploads"
    AWS_BUCKET_NAME: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "eu-central-1"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
