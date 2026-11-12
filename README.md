# AI-ассистент для соискателей

Telegram-бот, который адаптирует резюме под конкретную вакансию на базе LLM (DeepSeek) и честно показывает пробелы: чего из требований вакансии в резюме нет.

**Статус:** в работе (ноябрь–декабрь 2026). Код MVP готов и покрыт тестами, впереди интервью с пользователями и пилот. Результаты и юнит-экономика появятся здесь после пилота на реальных пользователях — до этого никаких цифр.

## Продуктовые вопросы

1. Решает ли бот реальную боль соискателя? Проверяем интервью до запуска ([заметки](docs/interview-notes.md)).
2. Где отвал в воронке активации? Меряем событиями ([трекинг-план](docs/tracking-plan.md)).
3. При какой цене продукт окупает инференс? Считаем по токенам каждого запроса ([бюджет](docs/budget.md), `reports/unit_economics.py`).

## Сценарий

`/start` → резюме (PDF, DOCX, TXT или текст) → вакансия текстом или ссылкой hh.ru → адаптированное резюме + что изменено + пробелы → скачать / переделать / оценить / следующая вакансия. `/privacy` — как обрабатываются данные.

## Что внутри

| Часть | Файл | Зачем |
|---|---|---|
| Бот | `bot/main.py` | сценарий на aiogram 3 |
| LLM | `bot/llm.py` | DeepSeek через OpenAI SDK, мок-режим без ключа |
| Стоимость | `bot/pricing.py` | цена запроса с учётом кэша и часов пик |
| Честность | `bot/faithfulness.py` | ищет цифры и названия, которых не было в резюме |
| Вакансии hh.ru | `bot/vacancy.py` | текст вакансии по ссылке через API hh |
| Аналитика | `bot/analytics.py` | 10 событий в Amplitude и в `data/events.jsonl` |
| Evals | `evals/` | эталонные пары и сравнение моделей по качеству и цене |
| Юнит-экономика | `reports/unit_economics.py` | воронка, себестоимость активного, безубыточная цена |

## Документы

[Трекинг-план](docs/tracking-plan.md) · [Бюджет](docs/budget.md) · [План пилота](docs/pilot-plan.md) · [Интервью](docs/interview-notes.md) · [Запуск и деплой](docs/deploy.md)

## Быстрый старт

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                        # без ключа DeepSeek — мок-режим
python -m bot.cli resume.txt vacancy.txt    # без Telegram
python -m bot.main                          # бот (нужен TELEGRAM_BOT_TOKEN)
pytest
python -m evals.run_eval --models deepseek-flash deepseek-v4-pro
```

## Стек

Python 3.11, aiogram 3, DeepSeek API, SQLite, Amplitude HTTP API, Docker, GitHub Actions.
