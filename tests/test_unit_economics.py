import json

from reports.unit_economics import economics, funnel, load_events, report


def _write(tmp_path):
    ev = []
    for u in ("a", "b", "c", "d"):
        ev.append({"user_id": u, "event_type": "bot_started", "event_properties": {}})
    for u in ("a", "b", "c"):
        ev.append({"user_id": u, "event_type": "resume_uploaded", "event_properties": {}})
    for u in ("a", "b"):
        ev.append({"user_id": u, "event_type": "vacancy_submitted", "event_properties": {}})
        ev.append({"user_id": u, "event_type": "generation_completed",
                   "event_properties": {"cost_usd": 0.01, "input_tokens": 100, "cached_tokens": 50}})
    ev.append({"user_id": "a", "event_type": "result_exported", "event_properties": {}})
    p = tmp_path / "events.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in ev))
    return p


def test_funnel_and_economics(tmp_path):
    events = load_events(_write(tmp_path))
    assert funnel(events)[:5] == [("bot_started", 4), ("resume_uploaded", 3), ("vacancy_submitted", 2),
                                  ("generation_completed", 2), ("result_exported", 1)]
    ec = economics(events, usd_rub=80, price_rub=199, paying_share=0.05)
    assert abs(ec["cost_per_active_rub"] - 1.6) < 1e-9  # 2 × $0.01 × 80 / 1 активный
    assert abs(ec["break_even_price_rub"] - 32.0) < 1e-9
    assert ec["cache_hit_share"] == 0.5


def test_report_renders(tmp_path):
    assert "Безубыточная цена" in report(_write(tmp_path), 80, 199, 0.05)
