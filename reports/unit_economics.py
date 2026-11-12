"""Воронка и юнит-экономика по событиям бота.

    python -m reports.unit_economics data/events.jsonl
    python -m reports.unit_economics amplitude_export.jsonl --price-rub 199 --paying-share 0.05

Вход — JSON Lines с полями user_id, event_type, event_properties
(так пишет бот в data/events.jsonl и так же выглядит выгрузка Amplitude Export API).
Все параметры монетизации — допущения, задаются флагами и печатаются в отчёте.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

FUNNEL = [
    "bot_started",
    "resume_uploaded",
    "vacancy_submitted",
    "generation_completed",
    "result_exported",
    "return_session",
]
# Отношение цен pro/flash (выход, пик) — для чувствительности к выбору модели
MODEL_COST_RATIO = {"deepseek-flash": 1.0, "deepseek-v4-pro": 3.96 / 1.20}


def load_events(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            props = e.get("event_properties") or {}
            if isinstance(props, str):
                props = json.loads(props)
            out.append({"user": e["user_id"], "event": e["event_type"], "props": props})
    return out


def funnel(events: list[dict]) -> list[tuple[str, int]]:
    users = defaultdict(set)
    for e in events:
        users[e["event"]].add(e["user"])
    reached: set | None = None
    rows = []
    for step in FUNNEL:
        reached = users[step] if reached is None else reached & users[step]
        rows.append((step, len(reached)))
    return rows


def economics(events: list[dict], usd_rub: float, price_rub: float, paying_share: float) -> dict:
    gens = [e for e in events if e["event"] == "generation_completed"]
    cost_usd = sum(float(e["props"].get("cost_usd", 0)) for e in gens)
    activated = {e["user"] for e in events if e["event"] == "result_exported"}
    cost_rub = cost_usd * usd_rub
    per_active = cost_rub / len(activated) if activated else 0.0
    cached = sum(int(e["props"].get("cached_tokens", 0)) for e in gens)
    inp = sum(int(e["props"].get("input_tokens", 0)) for e in gens)
    # Выручка на активного = цена × доля платящих; маржа = выручка − инференс
    revenue_per_active = price_rub * paying_share
    return {
        "generations": len(gens),
        "activated_users": len(activated),
        "inference_cost_rub": cost_rub,
        "cost_per_generation_rub": cost_rub / len(gens) if gens else 0.0,
        "cost_per_active_rub": per_active,
        "cache_hit_share": cached / inp if inp else 0.0,
        "revenue_per_active_rub": revenue_per_active,
        "margin_per_active_rub": revenue_per_active - per_active,
        "break_even_price_rub": per_active / paying_share if paying_share else float("inf"),
    }


def report(path: Path, usd_rub: float, price_rub: float, paying_share: float) -> str:
    events = load_events(path)
    lines = ["## Воронка (уникальные пользователи, прошедшие все шаги до этого)", "",
             "| Шаг | Пользователей | От старта | От прошлого шага |", "|---|---|---|---|"]
    rows = funnel(events)
    start = rows[0][1] or 1
    prev = None
    for step, n in rows:
        step_conv = f"{n / prev:.0%}" if prev else "—"
        lines.append(f"| {step} | {n} | {n / start:.0%} | {step_conv} |")
        prev = n or None
    ec = economics(events, usd_rub, price_rub, paying_share)
    lines += ["", "## Юнит-экономика", "",
              f"Допущения: курс {usd_rub} ₽/$, цена подписки {price_rub} ₽/мес, доля платящих {paying_share:.0%}.", "",
              "| Показатель | Значение |", "|---|---|",
              f"| Генераций | {ec['generations']} |",
              f"| Активированных пользователей | {ec['activated_users']} |",
              f"| Инференс всего, ₽ | {ec['inference_cost_rub']:.2f} |",
              f"| Себестоимость генерации, ₽ | {ec['cost_per_generation_rub']:.3f} |",
              f"| Себестоимость активного пользователя, ₽ | {ec['cost_per_active_rub']:.2f} |",
              f"| Доля входа из кэша | {ec['cache_hit_share']:.0%} |",
              f"| Выручка на активного, ₽ | {ec['revenue_per_active_rub']:.2f} |",
              f"| Маржа на активного (только инференс), ₽ | {ec['margin_per_active_rub']:.2f} |",
              f"| Безубыточная цена подписки, ₽ | {ec['break_even_price_rub']:.2f} |",
              "", "## Чувствительность к модели", "",
              "| Модель | Себестоимость активного, ₽ | Безубыточная цена, ₽ |", "|---|---|---|"]
    for model, ratio in MODEL_COST_RATIO.items():
        c = ec["cost_per_active_rub"] * ratio
        be = c / paying_share if paying_share else float("inf")
        lines.append(f"| {model} | {c:.2f} | {be:.2f} |")
    lines.append("\nМасштабирование pro/flash — по соотношению цен выхода; точнее — прогнать evals на обеих моделях.")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("events", type=Path)
    ap.add_argument("--usd-rub", type=float, default=80)
    ap.add_argument("--price-rub", type=float, default=199)
    ap.add_argument("--paying-share", type=float, default=0.05)
    a = ap.parse_args()
    print(report(a.events, a.usd_rub, a.price_rub, a.paying_share))


if __name__ == "__main__":
    main()
