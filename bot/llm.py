import asyncio
import re
import time
from dataclasses import dataclass

from openai import AsyncOpenAI

from .pricing import is_peak, request_cost_usd
from .prompts import SYSTEM_PROMPT, build_user_message

# Грубая оценка для мок-режима: ~3,5 символа кириллицы на токен
CHARS_PER_TOKEN = 3.5


@dataclass
class GenerationResult:
    text: str
    model: str
    input_tokens: int
    cached_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    is_peak: bool


class ResumeAdapter:
    def __init__(self, api_key: str, base_url: str, model: str):
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=120)
        self.model = model

    async def adapt(self, resume: str, vacancy: str) -> GenerationResult:
        peak = is_peak()
        started = time.monotonic()
        resp = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_message(resume, vacancy)},
            ],
            temperature=0.3,
        )
        latency_ms = int((time.monotonic() - started) * 1000)
        usage = resp.usage
        # DeepSeek отдаёт разбивку входа на кэш-хит и кэш-мисс
        hit = getattr(usage, "prompt_cache_hit_tokens", 0) or 0
        miss = getattr(usage, "prompt_cache_miss_tokens", None)
        if miss is None:
            miss = usage.prompt_tokens - hit
        return GenerationResult(
            text=resp.choices[0].message.content or "",
            model=self.model,
            input_tokens=usage.prompt_tokens,
            cached_tokens=hit,
            output_tokens=usage.completion_tokens,
            cost_usd=request_cost_usd(self.model, hit, miss, usage.completion_tokens, peak),
            latency_ms=latency_ms,
            is_peak=peak,
        )


class MockAdapter:
    """Работает без ключа: возвращает исходное резюме в нужном формате и
    честно помечает, что это заглушка. Токены и стоимость оцениваются по длине текста,
    чтобы воронка и расчёт себестоимости проверялись end-to-end."""

    def __init__(self, model: str = "deepseek-flash", delay_s: float = 0.0):
        self.model = model
        self._delay = delay_s

    async def adapt(self, resume: str, vacancy: str) -> GenerationResult:
        started = time.monotonic()
        if self._delay:
            await asyncio.sleep(self._delay)
        words = {w.lower() for w in re.findall(r"[A-Za-zА-Яа-яЁё]{4,}", vacancy)}
        missing = sorted(w for w in words if w not in resume.lower())[:5]
        text = (
            "## Адаптированное резюме\n"
            f"{resume.strip()}\n\n"
            "## Что изменено\n"
            "- [мок-режим] ничего: ключ DeepSeek не задан, это заглушка для проверки сценария\n\n"
            "## Пробелы\n"
            + ("\n".join(f"- {w}" for w in missing) or "- не найдено")
        )
        prompt = SYSTEM_PROMPT + build_user_message(resume, vacancy)
        inp = int(len(prompt) / CHARS_PER_TOKEN)
        out = int(len(text) / CHARS_PER_TOKEN)
        peak = is_peak()
        return GenerationResult(
            text=text,
            model=f"mock:{self.model}",
            input_tokens=inp,
            cached_tokens=0,
            output_tokens=out,
            cost_usd=request_cost_usd(self.model, 0, inp, out, peak),
            latency_ms=int((time.monotonic() - started) * 1000),
            is_peak=peak,
        )


def make_adapter(mode: str, api_key: str, base_url: str, model: str):
    if mode == "real":
        if not api_key:
            raise SystemExit("LLM_MODE=real, но DEEPSEEK_API_KEY пуст")
        return ResumeAdapter(api_key, base_url, model)
    return MockAdapter(model)
