from bot.storage import Storage


def test_return_session_after_24h():
    s = Storage(":memory:")
    s.get_or_create("u", now=1000)
    _, ret = s.register_vacancy("u", now=2000)
    assert not ret
    _, ret = s.register_vacancy("u", now=2000 + 3600)
    assert not ret
    before, ret = s.register_vacancy("u", now=2000 + 3600 + 25 * 3600)
    assert ret and before.vacancies_total == 2 and before.first_seen == 1000
