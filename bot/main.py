"""MVP: один сценарий — резюме + вакансия -> адаптированное резюме.

Резюме и вакансия живут в памяти процесса (FSM) и после рестарта теряются —
пользователь просто загружает их заново. Счётчики для return_session лежат в SQLite.
Без ключа DeepSeek бот работает в мок-режиме.
"""
import asyncio
import logging
import time

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from .analytics import Analytics
from . import faithfulness
from .config import load_config
from .llm import make_adapter
from .parsing import MAX_CHARS, ParseError, extract_text
from .storage import Storage
from .vacancy import VacancyFetchError, fetch_hh, hh_vacancy_id

logging.basicConfig(level=logging.INFO)
router = Router()
TG_LIMIT = 4000


class Flow(StatesGroup):
    resume = State()
    vacancy = State()
    done = State()


analytics: Analytics
adapter = None
storage: Storage


def result_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Скачать .txt", callback_data="export")],
            [InlineKeyboardButton(text="Переделать", callback_data="revise")],
            [InlineKeyboardButton(text=f"{i}", callback_data=f"rate:{i}") for i in range(1, 6)],
            [InlineKeyboardButton(text="Другая вакансия", callback_data="new_vacancy")],
        ]
    )


@router.message(CommandStart())
async def start(message: Message, command: CommandObject, state: FSMContext):
    uid = message.from_user.id
    storage.get_or_create(analytics.user_id(uid))
    await analytics.track(
        uid,
        "bot_started",
        source=command.args or "direct",
        language=message.from_user.language_code or "unknown",
    )
    await state.set_state(Flow.resume)
    await message.answer(
        "Привет! Я адаптирую резюме под конкретную вакансию и честно покажу, "
        "чего в нём не хватает. Ничего не выдумываю.\n\n"
        "Пришлите резюме файлом (PDF, DOCX, TXT) или вставьте текстом.\n"
        "Как обрабатываются данные: /privacy"
    )


PRIVACY_TEXT = (
    "Резюме и вакансия отправляются в модель DeepSeek для обработки и хранятся только в памяти бота "
    "до его перезапуска. На диск и в аналитику тексты не пишутся: в аналитику уходят только события "
    "(например, «резюме загружено») с обезличенным id. Уберите из резюме телефон и почту, если не хотите их передавать."
)


@router.message(Command("privacy"))
async def privacy(message: Message):
    await message.answer(PRIVACY_TEXT)


async def _save_resume(message: Message, state: FSMContext, text: str, fmt: str):
    await state.update_data(resume=text)
    await analytics.track(message.from_user.id, "resume_uploaded", format=fmt, length_chars=len(text))
    await state.set_state(Flow.vacancy)
    await message.answer("Резюме получил. Теперь вставьте текст вакансии.")


@router.message(Flow.resume, F.document)
async def resume_file(message: Message, state: FSMContext, bot: Bot):
    doc = message.document
    file = await bot.download(doc)
    try:
        text, fmt = extract_text(doc.file_name or "", file.read())
    except ParseError as err:
        await analytics.track(
            message.from_user.id,
            "resume_parse_failed",
            format=(doc.file_name or "").rsplit(".", 1)[-1].lower(),
            error_type=str(err),
        )
        await message.answer(
            "Не получилось прочитать файл. Пришлите PDF/DOCX/TXT с текстом "
            "(не скан) или вставьте резюме текстом."
        )
        return
    await _save_resume(message, state, text, fmt)


@router.message(Flow.resume, F.text)
async def resume_text(message: Message, state: FSMContext):
    if len(message.text) < 200:
        await message.answer("Похоже, это не всё резюме. Пришлите полный текст или файл.")
        return
    await _save_resume(message, state, message.text[:MAX_CHARS], "text")


def _detect_site(text: str) -> str:
    low = text.lower()
    for site in ("hh.ru", "superjob", "linkedin", "habr"):
        if site in low:
            return site
    return "other"


async def _generate(message: Message, state: FSMContext, uid: int):
    data = await state.get_data()
    await message.answer("Адаптирую, это займёт до минуты…")
    try:
        result = await adapter.adapt(data["resume"], data["vacancy"])
    except Exception as exc:
        logging.exception("LLM error")
        await analytics.track(uid, "generation_failed", error_type=type(exc).__name__)
        await message.answer("Модель не ответила. Попробуйте ещё раз через минуту: /start")
        return
    await analytics.track(
        uid,
        "generation_completed",
        model=result.model,
        input_tokens=result.input_tokens,
        cached_tokens=result.cached_tokens,
        output_tokens=result.output_tokens,
        cost_usd=round(result.cost_usd, 6),
        latency_ms=result.latency_ms,
        is_peak=result.is_peak,
        faithfulness_flags=faithfulness.check(data["resume"], result.text).flags,
    )
    await state.update_data(result=result.text)
    await state.set_state(Flow.done)
    text = result.text
    if len(text) > TG_LIMIT:
        text = text[:TG_LIMIT] + "\n\n…полная версия — по кнопке «Скачать .txt»"
    await message.answer(text, reply_markup=result_keyboard())


@router.message(Flow.vacancy, F.text)
async def vacancy(message: Message, state: FSMContext):
    uid = message.from_user.id
    before, is_return = storage.register_vacancy(analytics.user_id(uid))
    if is_return:
        await analytics.track(
            uid,
            "return_session",
            days_since_first=int((time.time() - before.first_seen) // 86400),
            vacancies_total=before.vacancies_total,
        )
    text = message.text.strip()
    input_type = "link" if text.startswith("http") else "text"
    await analytics.track(uid, "vacancy_submitted", input_type=input_type, site=_detect_site(text))
    if input_type == "link":
        vid = hh_vacancy_id(text)
        if not vid:
            await message.answer("Пока умею открывать только ссылки hh.ru. Вставьте текст вакансии.")
            return
        try:
            text = await fetch_hh(vid)
        except VacancyFetchError:
            logging.exception("hh fetch failed")
            await message.answer("Не получилось открыть вакансию на hh.ru. Вставьте её текст.")
            return
    await state.update_data(vacancy=text[:MAX_CHARS], attempt=1)
    await _generate(message, state, uid)


@router.callback_query(Flow.done, F.data == "export")
async def export(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await analytics.track(cb.from_user.id, "result_exported", format="txt")
    await cb.message.answer_document(
        BufferedInputFile(data["result"].encode("utf-8"), filename="resume_adapted.txt")
    )
    await cb.answer()


@router.callback_query(Flow.done, F.data == "revise")
async def revise(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    attempt = data.get("attempt", 1) + 1
    await state.update_data(attempt=attempt)
    await analytics.track(cb.from_user.id, "revision_requested", reason="button", attempt_n=attempt)
    await cb.answer()
    await _generate(cb.message, state, cb.from_user.id)


@router.callback_query(F.data.startswith("rate:"))
async def rate(cb: CallbackQuery):
    rating = int(cb.data.split(":")[1])
    await analytics.track(cb.from_user.id, "feedback_given", rating=rating, has_comment=False)
    await cb.answer("Спасибо за оценку!")


@router.callback_query(Flow.done, F.data == "new_vacancy")
async def new_vacancy(cb: CallbackQuery, state: FSMContext):
    await state.set_state(Flow.vacancy)
    await cb.answer()
    await cb.message.answer("Вставьте текст следующей вакансии. Резюме то же.")


async def main():
    global analytics, adapter, storage
    cfg = load_config()
    analytics = Analytics(cfg.amplitude_api_key, cfg.user_id_salt)
    adapter = make_adapter(cfg.llm_mode, cfg.deepseek_api_key, cfg.deepseek_base_url, cfg.deepseek_model)
    storage = Storage(cfg.db_path)
    logging.info("LLM mode: %s, model: %s", cfg.llm_mode, cfg.deepseek_model)
    bot = Bot(cfg.telegram_token)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
