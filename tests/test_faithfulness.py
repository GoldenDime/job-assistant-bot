from bot.faithfulness import check

SRC = "Стажёр, ООО «Ромашка», 2025. Провёл 12 интервью."


def test_clean_answer():
    ans = "## Адаптированное резюме\nООО «Ромашка», 2025: провёл 12 интервью.\n\n## Пробелы\n- 3 года опыта"
    assert check(SRC, ans).flags == 0  # цифра из «Пробелов» не считается


def test_invented_number_and_company():
    ans = "## Адаптированное резюме\nПровёл 40 интервью в «Яндексе», рост конверсии на 15%.\n\n## Что изменено\n- x"
    rep = check(SRC, ans)
    assert "40" in rep.new_numbers and "15" in rep.new_numbers
    assert rep.new_quoted_names == ["Яндексе"]
