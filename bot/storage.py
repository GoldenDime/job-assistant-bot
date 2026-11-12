"""Статистика пользователя в SQLite: нужна для return_session и переживает рестарт.
Тексты резюме не храним — только счётчики и время."""
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class UserStats:
    first_seen: float
    last_vacancy_at: float
    vacancies_total: int


class Storage:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            " user_hash TEXT PRIMARY KEY, first_seen REAL NOT NULL,"
            " last_vacancy_at REAL NOT NULL DEFAULT 0, vacancies_total INTEGER NOT NULL DEFAULT 0)"
        )
        self._db.commit()

    def get_or_create(self, user_hash: str, now: float | None = None) -> UserStats:
        now = now or time.time()
        self._db.execute(
            "INSERT OR IGNORE INTO users (user_hash, first_seen) VALUES (?, ?)", (user_hash, now)
        )
        self._db.commit()
        row = self._db.execute(
            "SELECT first_seen, last_vacancy_at, vacancies_total FROM users WHERE user_hash=?",
            (user_hash,),
        ).fetchone()
        return UserStats(*row)

    def register_vacancy(self, user_hash: str, now: float | None = None) -> tuple[UserStats, bool]:
        """Возвращает (статистику до вакансии, это возврат через 24+ ч)."""
        now = now or time.time()
        before = self.get_or_create(user_hash, now)
        is_return = bool(before.last_vacancy_at) and now - before.last_vacancy_at >= 24 * 3600
        self._db.execute(
            "UPDATE users SET last_vacancy_at=?, vacancies_total=vacancies_total+1 WHERE user_hash=?",
            (now, user_hash),
        )
        self._db.commit()
        return before, is_return
