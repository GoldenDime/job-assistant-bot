import pytest

from bot.parsing import ParseError, extract_text


def test_txt_ok():
    text, fmt = extract_text("cv.txt", ("Опыт работы " * 30).encode())
    assert fmt == "txt" and len(text) > 200


def test_too_short():
    with pytest.raises(ParseError, match="too_short"):
        extract_text("cv.txt", b"hello")


def test_unsupported():
    with pytest.raises(ParseError, match="unsupported_format"):
        extract_text("cv.png", b"x" * 500)
