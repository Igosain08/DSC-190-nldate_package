from datetime import date

import pytest

from nldate import parse

TODAY = date(2026, 11, 11)  # a Wednesday


def test_absolute_date() -> None:
    assert parse("December 1st, 2025") == date(2025, 12, 1)


def test_iso_date() -> None:
    assert parse("2025-12-01") == date(2025, 12, 1)


def test_year_first_slash_date() -> None:
    assert parse("2025/12/04") == date(2025, 12, 4)
    assert parse("2025.12.04") == date(2025, 12, 4)
    assert parse("2 days after 2025/12/04") == date(2025, 12, 6)


def test_today_tomorrow_yesterday() -> None:
    assert parse("today", today=TODAY) == date(2026, 11, 11)
    assert parse("tomorrow", today=TODAY) == date(2026, 11, 12)
    assert parse("yesterday", today=TODAY) == date(2026, 11, 10)


def test_case_insensitive() -> None:
    assert parse("Tomorrow", today=TODAY) == date(2026, 11, 12)


def test_in_n_days() -> None:
    assert parse("in 3 days", today=TODAY) == date(2026, 11, 14)


def test_days_before_absolute_date() -> None:
    assert parse("5 days before December 1st, 2025") == date(2025, 11, 26)


def test_weeks_after_relative_date() -> None:
    assert parse("2 weeks after tomorrow", today=TODAY) == date(2026, 11, 26)


def test_compound_offset() -> None:
    result = parse("1 year and 2 months after yesterday", today=TODAY)
    assert result == date(2028, 1, 10)


def test_next_weekday() -> None:
    assert parse("next Tuesday", today=TODAY) == date(2026, 11, 17)


def test_last_weekday() -> None:
    assert parse("last Friday", today=TODAY) == date(2026, 11, 6)


@pytest.mark.parametrize("bad", ["", "   ", "banana", "next Blursday"])
def test_invalid_input_raises(bad: str) -> None:
    with pytest.raises(ValueError):
        parse(bad, today=TODAY)


def test_month_end_clamping() -> None:
    assert parse("1 month after January 31, 2025") == date(2025, 2, 28)


def test_impossible_date_raises() -> None:
    with pytest.raises(ValueError):
        parse("February 30, 2025")


def test_day_after_tomorrow() -> None:
    assert parse("the day after tomorrow", today=TODAY) == date(2026, 11, 13)


def test_ago_and_word_numbers() -> None:
    assert parse("three weeks ago", today=TODAY) == date(2026, 10, 21)
    assert parse("a fortnight from now", today=TODAY) == date(2026, 11, 25)


def test_next_weekday_when_today_is_that_weekday() -> None:
    assert parse("next Wednesday", today=TODAY) == date(2026, 11, 18)
