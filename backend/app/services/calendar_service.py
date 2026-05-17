"""
Интеграция с Calendly и Zoom.
Calendly: получение слотов, создание событий, webhook.
Zoom: автоматическое создание meeting при подтверждении записи.
"""
import httpx
import base64
from datetime import datetime
from app.config import get_settings

settings = get_settings()

CALENDLY_BASE = "https://api.calendly.com"
ZOOM_BASE = "https://api.zoom.us/v2"


# ─── Calendly ────────────────────────────────────────────────────────────────

async def get_calendly_event_types() -> list[dict]:
    """Возвращает типы событий (продолжительности консультаций)."""
    headers = {"Authorization": f"Bearer {settings.CALENDLY_API_KEY}"}
    async with httpx.AsyncClient() as http:
        resp = await http.get(
            f"{CALENDLY_BASE}/event_types",
            headers=headers,
            params={"user": settings.CALENDLY_USER_URI, "active": True},
        )
        resp.raise_for_status()
    return resp.json().get("collection", [])


async def get_calendly_available_slots(event_type_uri: str, start_time: str, end_time: str) -> list[dict]:
    """
    Возвращает доступные слоты для записи.
    start_time / end_time в формате ISO 8601.
    """
    headers = {"Authorization": f"Bearer {settings.CALENDLY_API_KEY}"}
    async with httpx.AsyncClient() as http:
        resp = await http.get(
            f"{CALENDLY_BASE}/event_type_available_times",
            headers=headers,
            params={
                "event_type": event_type_uri,
                "start_time": start_time,
                "end_time": end_time,
            },
        )
        resp.raise_for_status()
    return resp.json().get("collection", [])


async def schedule_calendly_event(
    event_type_uri: str,
    start_time: str,
    invitee_name: str,
    invitee_email: str,
    questions_answers: list[dict] | None = None,
) -> dict:
    """
    Создаёт событие в Calendly от имени клиента.
    Используется для программной записи (без виджета).
    """
    headers = {
        "Authorization": f"Bearer {settings.CALENDLY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "start_time": start_time,
        "event_type_uuid": event_type_uri.split("/")[-1],
        "invitee": {
            "name": invitee_name,
            "email": invitee_email,
            "questions_and_answers": questions_answers or [],
        },
    }
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            f"{CALENDLY_BASE}/scheduled_events",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
    return resp.json()


async def cancel_calendly_event(event_uuid: str, reason: str = "Cancelled by client") -> bool:
    headers = {
        "Authorization": f"Bearer {settings.CALENDLY_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            f"{CALENDLY_BASE}/scheduled_events/{event_uuid}/cancellation",
            headers=headers,
            json={"reason": reason},
        )
    return resp.status_code in (200, 201, 204)


# ─── Zoom ────────────────────────────────────────────────────────────────────

_zoom_token_cache: dict = {}


async def _get_zoom_token() -> str:
    """
    Получает OAuth access token для Zoom Server-to-Server App.
    Кэширует до истечения срока.
    """
    import time
    if _zoom_token_cache.get("expires_at", 0) > time.time() + 60:
        return _zoom_token_cache["token"]

    credentials = base64.b64encode(
        f"{settings.ZOOM_CLIENT_ID}:{settings.ZOOM_CLIENT_SECRET}".encode()
    ).decode()

    async with httpx.AsyncClient() as http:
        resp = await http.post(
            "https://zoom.us/oauth/token",
            params={
                "grant_type": "account_credentials",
                "account_id": settings.ZOOM_ACCOUNT_ID,
            },
            headers={"Authorization": f"Basic {credentials}"},
        )
        resp.raise_for_status()
    data = resp.json()

    import time
    _zoom_token_cache.update({
        "token": data["access_token"],
        "expires_at": time.time() + data["expires_in"],
    })
    return data["access_token"]


async def create_zoom_meeting(
    topic: str,
    start_time: str,   # ISO 8601
    duration_minutes: int,
    timezone: str = "Europe/Moscow",
    agenda: str = "",
) -> dict:
    """
    Создаёт Zoom-встречу и возвращает join_url и password.
    """
    token = await _get_zoom_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "topic": topic,
        "type": 2,   # scheduled
        "start_time": start_time,
        "duration": duration_minutes,
        "timezone": timezone,
        "agenda": agenda,
        "settings": {
            "host_video": True,
            "participant_video": True,
            "waiting_room": True,
            "auto_recording": "none",
        },
    }

    async with httpx.AsyncClient() as http:
        resp = await http.post(
            f"{ZOOM_BASE}/users/me/meetings",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()

    data = resp.json()
    return {
        "meeting_id": str(data["id"]),
        "join_url": data["join_url"],
        "password": data.get("password", ""),
    }
