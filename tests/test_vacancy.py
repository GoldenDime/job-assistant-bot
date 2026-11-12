import asyncio

import httpx
import pytest

from bot.vacancy import VacancyFetchError, fetch_hh, hh_vacancy_id

HH_JSON = {
    "name": "Junior PM",
    "employer": {"name": "Тест"},
    "experience": {"name": "Нет опыта"},
    "description": "<p>Вести <strong>бэклог</strong></p><ul><li>SQL</li></ul>",
    "key_skills": [{"name": "Jira"}, {"name": "SQL"}],
}


def test_id_parsing():
    assert hh_vacancy_id("https://hh.ru/vacancy/123456?from=x") == "123456"
    assert hh_vacancy_id("https://spb.hh.ru/vacancy/42") == "42"
    assert hh_vacancy_id("https://superjob.ru/vakansii/1") is None


def _client(status: int, body: dict) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(status, json=body)))


def test_fetch_ok():
    text = asyncio.run(fetch_hh("1", _client(200, HH_JSON)))
    assert "Junior PM" in text and "бэклог" in text and "<" not in text and "Jira, SQL" in text


def test_fetch_404():
    with pytest.raises(VacancyFetchError, match="hh_status_404"):
        asyncio.run(fetch_hh("1", _client(404, {})))
