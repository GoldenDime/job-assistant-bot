import asyncio
import json

import pytest

from bot.analytics import Analytics


def test_local_log_and_hashing(tmp_path):
    log = tmp_path / "e.jsonl"
    a = Analytics("", "salt", str(log))
    asyncio.run(a.track(123, "bot_started", source="direct"))
    row = json.loads(log.read_text())
    assert row["event_type"] == "bot_started" and "123" not in row["user_id"]
    with pytest.raises(ValueError):
        asyncio.run(a.track(1, "unknown_event"))
