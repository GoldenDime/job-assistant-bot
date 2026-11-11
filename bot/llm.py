import time
from dataclasses import dataclass

from openai import AsyncOpenAI

from .pricing import is_peak, request_cost_usd
from .prompts import SYSTEM_PROMPT, build_user_message


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
        self._model = model

    async def adapt(self, resume: str, vacancy: str) -> GenerationResult:
        peak = is_peak()
        started = time.monotonic()
        resp = await self._client.chat.completions.create(
            model=self._model,
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
            model=self._model,
            input_tokens=usage.prompt_tokens,
            cached_tokens=hit,
            output_tokens=usage.completion_tokens,
            cost_usd=request_cost_usd(self._model, hit, miss, usage.completion_tokens, peak),
            latency_ms=latency_ms,
            is_peak=peak,
        )
