"""
Сервис уведомлений: email (SendGrid) + Telegram.
"""
import httpx
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To, Attachment, FileContent, FileName, FileType, Disposition
import base64
from pathlib import Path
from app.config import get_settings

settings = get_settings()


# ─── Email ───────────────────────────────────────────────────────────────────

async def send_email(
    to_email: str,
    to_name: str,
    subject: str,
    html_content: str,
    attachment_path: str | None = None,
    attachment_name: str | None = None,
) -> bool:
    """Отправляет письмо через SendGrid."""
    if not settings.SENDGRID_API_KEY:
        print(f"[DEV] Email to {to_email}: {subject}")
        return True

    message = Mail(
        from_email=settings.EMAIL_FROM,
        to_emails=To(to_email, to_name),
        subject=subject,
        html_content=html_content,
    )

    if attachment_path and attachment_name:
        data = Path(attachment_path).read_bytes()
        message.attachment = Attachment(
            file_content=FileContent(base64.b64encode(data).decode()),
            file_name=FileName(attachment_name),
            file_type=FileType("application/octet-stream"),
            disposition=Disposition("attachment"),
        )

    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
    response = sg.send(message)
    return response.status_code in (200, 202)


async def send_template_purchase_email(
    to_email: str,
    to_name: str,
    template_name: str,
    download_url: str,
) -> bool:
    html = f"""
    <h2>Ваш шаблон готов!</h2>
    <p>Здравствуйте, {to_name}!</p>
    <p>Спасибо за покупку шаблона <strong>«{template_name}»</strong>.</p>
    <p>
        <a href="{download_url}" style="
            background:#2563eb;color:white;padding:12px 24px;
            text-decoration:none;border-radius:6px;display:inline-block;
        ">Скачать шаблон</a>
    </p>
    <p><small>Ссылка действительна 7 дней. Если нужна помощь с заполнением —
    <a href="https://yourdomain.com/consultation">запишитесь на консультацию</a>.</small></p>
    """
    return await send_email(to_email, to_name, f"Шаблон «{template_name}» — скачать", html)


async def send_consultation_confirmation_email(
    to_email: str,
    to_name: str,
    scheduled_at: str,
    zoom_url: str,
    zoom_password: str | None,
) -> bool:
    pwd = f"<p>Пароль: <strong>{zoom_password}</strong></p>" if zoom_password else ""
    html = f"""
    <h2>Консультация подтверждена</h2>
    <p>Здравствуйте, {to_name}!</p>
    <p>Ваша консультация запланирована на <strong>{scheduled_at}</strong>.</p>
    <p><a href="{zoom_url}" style="
        background:#059669;color:white;padding:12px 24px;
        text-decoration:none;border-radius:6px;display:inline-block;
    ">Подключиться к Zoom</a></p>
    {pwd}
    <p><small>Напоминание придёт за 24 часа и за 1 час до начала.</small></p>
    """
    return await send_email(
        to_email, to_name,
        f"Консультация {scheduled_at} — Zoom-ссылка",
        html
    )


async def send_consultation_reminder_email(
    to_email: str,
    to_name: str,
    scheduled_at: str,
    zoom_url: str,
    time_label: str,  # "24 часа" | "1 час"
) -> bool:
    html = f"""
    <h2>Напоминание о консультации</h2>
    <p>Здравствуйте, {to_name}!</p>
    <p>Ваша консультация начнётся через <strong>{time_label}</strong> — {scheduled_at}.</p>
    <p><a href="{zoom_url}">Подключиться к Zoom</a></p>
    """
    return await send_email(to_email, to_name, f"Напоминание: консультация через {time_label}", html)


# ─── Telegram ────────────────────────────────────────────────────────────────

async def send_telegram_message(chat_id: str | int, text: str) -> bool:
    """Отправляет сообщение через Telegram Bot API."""
    if not settings.TELEGRAM_BOT_TOKEN:
        print(f"[DEV] Telegram to {chat_id}: {text[:80]}")
        return True

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as http:
        resp = await http.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        })
    return resp.status_code == 200


async def send_telegram_document(chat_id: str | int, file_path: str, caption: str = "") -> bool:
    """Отправляет файл через Telegram."""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument"
    async with httpx.AsyncClient() as http:
        with open(file_path, "rb") as f:
            resp = await http.post(url, data={"chat_id": chat_id, "caption": caption},
                                   files={"document": f})
    return resp.status_code == 200


async def send_template_via_telegram(
    chat_id: str | int,
    template_name: str,
    file_path: str,
) -> bool:
    caption = (
        f"✅ <b>Ваш шаблон «{template_name}»</b>\n\n"
        "Если нужна помощь с заполнением — нажмите /consultation"
    )
    return await send_telegram_document(chat_id, file_path, caption)
