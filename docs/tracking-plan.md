# Трекинг-план

Активация = пользователь получил адаптированное резюме и скачал его (`result_exported`).

| # | Событие | Когда шлём | Свойства |
|---|---|---|---|
| 1 | bot_started | /start | source (deep-link), language |
| 2 | resume_uploaded | резюме принято | format (pdf/docx/txt/text), length_chars |
| 3 | resume_parse_failed | файл не прочитан | format, error_type |
| 4 | vacancy_submitted | вакансия прислана | input_type (link/text), site (hh.ru — текст тянется через API hh) |
| 5 | generation_completed | LLM ответила | model, input_tokens, cached_tokens, output_tokens, cost_usd, latency_ms, is_peak, faithfulness_flags |
| 6 | generation_failed | ошибка/таймаут LLM | error_type |
| 7 | result_exported | скачал .txt (активация) | format |
| 8 | revision_requested | «Переделать» | reason, attempt_n |
| 9 | feedback_given | оценка 1–5 | rating, has_comment |
| 10 | return_session | новая вакансия через 24+ ч | days_since_first, vacancies_total |

На всех событиях: `user_id` (солёный SHA-256 от Telegram id), `bot_version`. Тексты резюме и вакансий в аналитику не уходят.

**Воронка:** bot_started → resume_uploaded → vacancy_submitted → generation_completed → result_exported → return_session.

**Себестоимость на активного пользователя:** Σ cost_usd по generation_completed / число пользователей с result_exported.

`faithfulness_flags` — число новых цифр и названий в кавычках, которых не было в исходном резюме (`bot/faithfulness.py`). Эвристика: флаг означает «проверить глазами».

Каждое событие дублируется в `data/events.jsonl`, отчёт: `python -m reports.unit_economics data/events.jsonl`.
