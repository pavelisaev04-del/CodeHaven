"""
Скрипт напоминаний о консультациях.
Запускается по крону: каждые 30 минут.
  crontab: */30 * * * * python /app/reminders.py

Логика:
  - За 24 часа: отправить email + Telegram
  - За 1 час:   отправить email + Telegram
"""
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from app.database import AsyncSessionLocal
from app.models.consultation import Consultation, ConsultationStatus
from app.services.notification_service import (
    send_consultation_reminder_email,
    send_telegram_message,
)


async def send_reminders():
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)

        # Консультации, которым нужно напоминание за 24 часа
        window_24h_start = now + timedelta(hours=23, minutes=30)
        window_24h_end = now + timedelta(hours=24, minutes=30)

        # Консультации, которым нужно напоминание за 1 час
        window_1h_start = now + timedelta(minutes=50)
        window_1h_end = now + timedelta(hours=1, minutes=10)

        active_statuses = [ConsultationStatus.SCHEDULED, ConsultationStatus.REMINDER_SENT]

        # 24-часовые напоминания
        result = await db.execute(
            select(Consultation).where(
                Consultation.status.in_(active_statuses),
                Consultation.scheduled_at >= window_24h_start,
                Consultation.scheduled_at <= window_24h_end,
                Consultation.reminder_24h_sent == False,
            )
        )
        for c in result.scalars():
            scheduled_str = c.scheduled_at.strftime("%d.%m.%Y %H:%M")
            await send_consultation_reminder_email(
                to_email=c.client_email,
                to_name=c.client_name,
                scheduled_at=f"{scheduled_str} (МСК)",
                zoom_url=c.zoom_meeting_url or "",
                time_label="24 часа",
            )
            if c.user and hasattr(c.user, "telegram_id") and c.user.telegram_id:
                await send_telegram_message(
                    c.user.telegram_id,
                    f"⏰ Напоминание: завтра в {scheduled_str} у вас консультация.\n"
                    f"Zoom: {c.zoom_meeting_url}",
                )
            c.reminder_24h_sent = True
            print(f"[24h reminder] {c.id} → {c.client_email}")

        # 1-часовые напоминания
        result = await db.execute(
            select(Consultation).where(
                Consultation.status.in_(active_statuses),
                Consultation.scheduled_at >= window_1h_start,
                Consultation.scheduled_at <= window_1h_end,
                Consultation.reminder_1h_sent == False,
            )
        )
        for c in result.scalars():
            scheduled_str = c.scheduled_at.strftime("%d.%m.%Y %H:%M")
            await send_consultation_reminder_email(
                to_email=c.client_email,
                to_name=c.client_name,
                scheduled_at=f"{scheduled_str} (МСК)",
                zoom_url=c.zoom_meeting_url or "",
                time_label="1 час",
            )
            if c.user and hasattr(c.user, "telegram_id") and c.user.telegram_id:
                await send_telegram_message(
                    c.user.telegram_id,
                    f"🔔 Ваша консультация через 1 час!\n"
                    f"Время: {scheduled_str}\n"
                    f"Zoom: {c.zoom_meeting_url}",
                )
            c.reminder_1h_sent = True
            print(f"[1h reminder] {c.id} → {c.client_email}")

        await db.commit()
        print(f"[{now.strftime('%H:%M')}] Reminder check done.")


if __name__ == "__main__":
    asyncio.run(send_reminders())
