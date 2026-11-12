"""Прогон эталонных пар «резюме + вакансия» через одну или несколько моделей.

    python -m evals.run_eval --models deepseek-flash deepseek-v4-pro
    LLM_MODE=mock python -m evals.run_eval      # проверка харнесса без ключа

Метрики на пару:
- keyword_coverage — доля must_keywords (то, что в резюме ЕСТЬ и нужно вакансии), попавших в адаптированное резюме;
- forbidden_hits — сколько требований, которых в резюме НЕТ, модель «приписала» кандидату;
- faithfulness_flags — новые цифры и названия в кавычках (bot/faithfulness.py);
- cost_usd, latency_ms.
Пары синтетические (выдуманные люди), см. evals/README.md.
"""
import argparse
import asyncio
import csv
import json
from datetime import datetime
from pathlib import Path

from bot import faithfulness
from bot.config import load_config
from bot.llm import make_adapter

HERE = Path(__file__).parent


def load_pairs(path: Path = HERE / "pairs.jsonl") -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def score(pair: dict, answer: str) -> dict:
    section = faithfulness.resume_section(answer).lower()
    must = pair["must_keywords"]
    covered = sum(1 for k in must if k.lower() in section)
    forbidden = [k for k in pair["forbidden"] if k.lower() in section and k.lower() not in pair["resume"].lower()]
    rep = faithfulness.check(pair["resume"], answer)
    return {
        "keyword_coverage": round(covered / len(must), 3) if must else 1.0,
        "forbidden_hits": len(forbidden),
        "forbidden_list": ";".join(forbidden),
        "faithfulness_flags": rep.flags,
    }


async def run(models: list[str], out_dir: Path) -> list[dict]:
    cfg = load_config(require_telegram=False)
    rows = []
    for model in models:
        adapter = make_adapter(cfg.llm_mode, cfg.deepseek_api_key, cfg.deepseek_base_url, model)
        for pair in load_pairs():
            res = await adapter.adapt(pair["resume"], pair["vacancy"])
            rows.append({
                "model": res.model, "pair": pair["id"], **score(pair, res.text),
                "input_tokens": res.input_tokens, "output_tokens": res.output_tokens,
                "cost_usd": round(res.cost_usd, 6), "latency_ms": res.latency_ms,
            })
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{datetime.now():%Y%m%d-%H%M}-{cfg.llm_mode}.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(summary(rows))
    print(f"\nПодробно: {out}")
    return rows


def summary(rows: list[dict]) -> str:
    lines = ["| Модель | Пар | Покрытие ключевых слов | Приписано лишнего | Флаги честности | $ / пара | мс / пара |",
             "|---|---|---|---|---|---|---|"]
    for model in dict.fromkeys(r["model"] for r in rows):
        rs = [r for r in rows if r["model"] == model]
        n = len(rs)
        lines.append(
            f"| {model} | {n} | {sum(r['keyword_coverage'] for r in rs) / n:.0%} | "
            f"{sum(r['forbidden_hits'] for r in rs)} | {sum(r['faithfulness_flags'] for r in rs)} | "
            f"{sum(r['cost_usd'] for r in rs) / n:.5f} | {sum(r['latency_ms'] for r in rs) // n} |"
        )
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["deepseek-flash"])
    ap.add_argument("--out", default=str(HERE / "results"))
    a = ap.parse_args()
    asyncio.run(run(a.models, Path(a.out)))


if __name__ == "__main__":
    main()
