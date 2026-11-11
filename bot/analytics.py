"""Отправка событий трекинг-плана в Amplitude (HTTP API v2).

Тексты резюме и вакансий сюда не передаём: это персональные данные.
"""
import hashlib
import logging
import time

import httpx

log = logging.getLogger("analytics")
AMPLITUDE_URL = "https://api2.amplitude.com/2/httpapi"
BOT_VERSION = "0.1.0"

EVENTS = {
    "bot_started",
    "resume_uploaded",
    "resume_parse_failed",
    "vacancy_submitted",
    "generation_completed",
    "generation_failed",
    "result_exported",
    "revision_requested",
    "feedback_given",
    "return_session",
}


class Analytics:
    def __init__(self, api_key: str, salt: str):
        self._api_key = api_key
        self._salt = salt
        self._client = httpx.AsyncClient(timeout=10)

    def user_id(self, telegram_id: int) -> str:
        return hashlib.sha256(f"{self._salt}:{telegram_id}".encode()).hexdigest()[:32]

    async def track(self, telegram_id: int, event: str, **props) -> None:
        if event not in EVENTS:
            raise ValueError(f"Событие {event!r} не описано в трекинг-плане")
        props["bot_version"] = BOT_VERSION
        payload = {
            "user_id": self.user_id(telegram_id),
            "event_type": event,
            "time": int(time.time() * 1000),
            "event_properties": props,
        }
        log.info("event %s %s", event, props)
        if not self._api_key:
            return
        try:
            await self._client.post(
                AMPLITUDE_URL, json={"api_key": self._api_key, "events": [payload]}
            )
        except httpx.HTTPError:
            log.exception("Amplitude недоступен, событие %s потеряно", event)
