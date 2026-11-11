"""Стоимость запроса к DeepSeek.

Цены в $ за 1 млн токенов в часы пик, по https://api-docs.deepseek.com/quick_start/pricing
(проверено 11.11.2026). Вне пика всё вдвое дешевле.
Пик: пн–пт 01:00–04:00 и 06:00–10:00 UTC.
"""
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Price:
    cache_hit: float
    cache_miss: float
    output: float


PEAK_PRICES = {
    "deepseek-flash": Price(cache_hit=0.006, cache_miss=0.30, output=1.20),
    "deepseek-v4-pro": Price(cache_hit=0.044, cache_miss=1.32, output=3.96),
}


def is_peak(moment: datetime | None = None) -> bool:
    moment = (moment or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if moment.weekday() >= 5:
        return False
    h = moment.hour
    return 1 <= h < 4 or 6 <= h < 10


def request_cost_usd(
    model: str,
    cache_hit_tokens: int,
    cache_miss_tokens: int,
    output_tokens: int,
    peak: bool,
) -> float:
    price = PEAK_PRICES[model]
    cost = (
        cache_hit_tokens * price.cache_hit
        + cache_miss_tokens * price.cache_miss
        + output_tokens * price.output
    ) / 1_000_000
    return cost if peak else cost / 2
