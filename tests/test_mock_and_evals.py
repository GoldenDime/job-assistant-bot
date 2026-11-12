import asyncio

from bot.llm import MockAdapter
from evals.run_eval import load_pairs, score


def test_mock_adapter_format_and_cost():
    res = asyncio.run(MockAdapter().adapt("Опыт: Python, SQL. " * 20, "Нужен Kafka и Python"))
    assert res.text.startswith("## Адаптированное резюме")
    assert res.model == "mock:deepseek-flash" and res.cost_usd > 0 and res.input_tokens > 0


def test_pairs_valid():
    pairs = load_pairs()
    assert len(pairs) >= 6
    for p in pairs:
        assert len(p["resume"]) >= 200
        for k in p["forbidden"]:
            assert k.lower() not in p["resume"].lower(), (p["id"], k)
        for k in p["must_keywords"]:
            assert k.lower() in p["resume"].lower(), (p["id"], k)


def test_score_catches_forbidden():
    pair = load_pairs()[0]
    bad = "## Адаптированное резюме\n" + pair["resume"] + " Проводил A/B-тесты в Amplitude."
    s = score(pair, bad)
    assert s["forbidden_hits"] == 2 and s["keyword_coverage"] == 1.0
