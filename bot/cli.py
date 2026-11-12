"""Консольная проверка без Telegram:
    python -m bot.cli resume.txt vacancy.txt
    python -m bot.cli resume.pdf https://hh.ru/vacancy/123456
Без DEEPSEEK_API_KEY работает в мок-режиме."""
import argparse
import asyncio
from pathlib import Path

from . import faithfulness
from .config import load_config
from .llm import make_adapter
from .parsing import extract_text
from .vacancy import fetch_hh, hh_vacancy_id


async def run(resume_path: str, vacancy_arg: str, model: str | None) -> None:
    cfg = load_config(require_telegram=False)
    resume, _ = extract_text(resume_path, Path(resume_path).read_bytes())
    if vid := hh_vacancy_id(vacancy_arg):
        vacancy = await fetch_hh(vid)
    else:
        vacancy = Path(vacancy_arg).read_text(encoding="utf-8")
    adapter = make_adapter(cfg.llm_mode, cfg.deepseek_api_key, cfg.deepseek_base_url, model or cfg.deepseek_model)
    res = await adapter.adapt(resume, vacancy)
    rep = faithfulness.check(resume, res.text)
    print(res.text)
    print("\n---")
    print(
        f"model={res.model} in={res.input_tokens} cached={res.cached_tokens} out={res.output_tokens} "
        f"cost=${res.cost_usd:.5f} (~{res.cost_usd * cfg.usd_rub:.2f} ₽) latency={res.latency_ms}ms peak={res.is_peak}"
    )
    print(f"faithfulness flags={rep.flags} numbers={rep.new_numbers} names={rep.new_quoted_names}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("resume")
    ap.add_argument("vacancy", help="путь к .txt или ссылка hh.ru")
    ap.add_argument("--model")
    a = ap.parse_args()
    asyncio.run(run(a.resume, a.vacancy, a.model))


if __name__ == "__main__":
    main()
