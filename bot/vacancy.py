"""Вакансия по ссылке hh.ru через публичный API (https://api.hh.ru/vacancies/{id})."""
import html
import re

import httpx

HH_RE = re.compile(r"https?://(?:[\w-]+\.)?hh\.(?:ru|kz|by|uz)/vacancy/(\d+)")
TAG_RE = re.compile(r"<[^>]+>")
HH_API = "https://api.hh.ru/vacancies/{id}"
USER_AGENT = "job-assistant-bot/0.1 (+https://github.com/GoldenDime/job-assistant-bot)"


class VacancyFetchError(Exception):
    pass


def hh_vacancy_id(text: str) -> str | None:
    m = HH_RE.search(text)
    return m.group(1) if m else None


def html_to_text(s: str) -> str:
    s = re.sub(r"</(p|li|ul|ol|h\d)>|<br\s*/?>", "\n", s, flags=re.I)
    s = html.unescape(TAG_RE.sub("", s))
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def format_hh_vacancy(data: dict) -> str:
    parts = [data.get("name", "")]
    if emp := (data.get("employer") or {}).get("name"):
        parts.append(f"Компания: {emp}")
    if exp := (data.get("experience") or {}).get("name"):
        parts.append(f"Опыт: {exp}")
    parts.append(html_to_text(data.get("description", "")))
    if skills := [s["name"] for s in data.get("key_skills", []) if s.get("name")]:
        parts.append("Ключевые навыки: " + ", ".join(skills))
    return "\n\n".join(p for p in parts if p)


async def fetch_hh(vacancy_id: str, client: httpx.AsyncClient | None = None) -> str:
    own = client is None
    client = client or httpx.AsyncClient(timeout=15)
    try:
        resp = await client.get(HH_API.format(id=vacancy_id), headers={"HH-User-Agent": USER_AGENT, "User-Agent": USER_AGENT})
        if resp.status_code != 200:
            raise VacancyFetchError(f"hh_status_{resp.status_code}")
        return format_hh_vacancy(resp.json())
    except httpx.HTTPError as exc:
        raise VacancyFetchError("hh_network") from exc
    finally:
        if own:
            await client.aclose()
