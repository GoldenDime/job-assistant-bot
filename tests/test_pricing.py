from datetime import datetime, timezone

from bot.pricing import is_peak, request_cost_usd


def test_peak_hours():
    assert is_peak(datetime(2026, 11, 11, 7, 0, tzinfo=timezone.utc))  # среда 07:00
    assert not is_peak(datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc))
    assert not is_peak(datetime(2026, 11, 14, 7, 0, tzinfo=timezone.utc))  # суббота


def test_typical_request_cost():
    # 3500 токенов входа без кэша + 1500 выхода на flash в пик ≈ $0.00285
    cost = request_cost_usd("deepseek-flash", 0, 3500, 1500, peak=True)
    assert abs(cost - 0.00285) < 1e-9
    assert request_cost_usd("deepseek-flash", 0, 3500, 1500, peak=False) == cost / 2
