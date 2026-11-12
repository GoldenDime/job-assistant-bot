# Запуск и деплой

## 1. Что понадобится (делает владелец, не коммитить в репозиторий)

1. Токен бота: в Telegram написать @BotFather → `/newbot` → скопировать токен.
2. Ключ DeepSeek: platform.deepseek.com → API keys. Для пилота хватит минимального пополнения (оценка — в [budget.md](budget.md)). Без ключа бот работает в мок-режиме.
3. Ключ Amplitude (необязательно): бесплатный проект → Settings → API key. Без него события пишутся только в `data/events.jsonl`.

Всё это вписывается в `.env` (шаблон — `.env.example`).

## 2. Локально

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # заполнить
python -m bot.main          # бот в Telegram
python -m bot.cli resume.pdf vacancy.txt   # проверка без Telegram
```

Пока бот запущен на вашем компьютере, он отвечает пользователям. Для пилота на 2 недели этого мало: нужен сервер.

## 3. На VPS через Docker

Подойдёт любой VPS с 1 ГБ RAM (≈ 200–400 ₽/мес). Бот работает через long polling, домен и HTTPS не нужны.

```bash
git clone https://github.com/GoldenDime/job-assistant-bot && cd job-assistant-bot
nano .env                                   # заполнить по .env.example
docker build -t job-bot .
docker run -d --name job-bot --restart unless-stopped --env-file .env -v $PWD/data:/app/data job-bot
docker logs -f job-bot                      # в логе: "LLM mode: real"
```

Обновление: `git pull && docker build -t job-bot . && docker rm -f job-bot && docker run ...` (та же команда).

## 4. Отчёт по пилоту

```bash
docker cp job-bot:/app/data/events.jsonl .
python -m reports.unit_economics events.jsonl --price-rub 199 --paying-share 0.05
```
