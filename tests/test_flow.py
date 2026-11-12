"""Сквозной сценарий через хендлеры бота без Telegram: мок-LLM, SQLite в памяти, события в файл."""
import asyncio
import json
from types import SimpleNamespace

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

import bot.main as m
from bot.analytics import Analytics
from bot.llm import MockAdapter
from bot.storage import Storage

RESUME = "Опыт: аналитик, SQL, Jira, интервью с пользователями. " * 6


class FakeMessage:
    def __init__(self, text=""):
        self.text = text
        self.from_user = SimpleNamespace(id=42, language_code="ru")
        self.answers = []
        self.message = self

    async def answer(self, text, **kw):
        self.answers.append((text, kw))

    async def answer_document(self, doc, **kw):
        self.answers.append(("<document>", {"doc": doc}))


class FakeCallback:
    def __init__(self, data, msg):
        self.data, self.message, self.from_user = data, msg, msg.from_user

    async def answer(self, *a, **kw):
        pass


def test_full_flow(tmp_path):
    log = tmp_path / "events.jsonl"
    m.analytics = Analytics("", "salt", str(log))
    m.adapter = MockAdapter()
    m.storage = Storage(":memory:")
    state = FSMContext(MemoryStorage(), StorageKey(bot_id=1, chat_id=42, user_id=42))

    async def scenario():
        msg = FakeMessage("/start")
        await m.start(msg, SimpleNamespace(args="interview"), state)
        assert await state.get_state() == m.Flow.resume.state
        await m.resume_text(FakeMessage(RESUME), state)
        out = FakeMessage("Нужен аналитик: SQL, Jira, Amplitude")
        await m.vacancy(out, state)
        assert await state.get_state() == m.Flow.done.state
        assert out.answers[-1][0].startswith("## Адаптированное резюме")
        await m.export(FakeCallback("export", out), state)
        assert out.answers[-1][0] == "<document>"
        await m.revise(FakeCallback("revise", out), state)
        await m.rate(FakeCallback("rate:4", out))

    asyncio.run(scenario())
    events = [json.loads(l)["event_type"] for l in log.read_text().splitlines()]
    assert events == ["bot_started", "resume_uploaded", "vacancy_submitted", "generation_completed",
                      "result_exported", "revision_requested", "generation_completed", "feedback_given"]
