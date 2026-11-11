"""Natural-language date parsing."""

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta

MONTHS: dict[str, int] = {}
for _i, (_full, _abbr) in enumerate(
    zip(calendar.month_name[1:], calendar.month_abbr[1:], strict=True), start=1
):
    MONTHS[_full.lower()] = _i
    MONTHS[_abbr.lower()] = _i
MONTHS["sept"] = 9

WEEKDAYS: dict[str, int] = {}
for _i, (_full, _abbr) in enumerate(
    zip(calendar.day_name, calendar.day_abbr, strict=True)
):
    WEEKDAYS[_full.lower()] = _i
    WEEKDAYS[_abbr.lower()] = _i
WEEKDAYS.update({"tues": 1, "wednes": 2, "thur": 3, "thurs": 3})

NUMBER_WORDS: dict[str, int] = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}

UNITS: dict[str, str] = {
    "day": "days",
    "days": "days",
    "week": "weeks",
    "weeks": "weeks",
    "fortnight": "fortnights",
    "fortnights": "fortnights",
    "month": "months",
    "months": "months",
    "year": "years",
    "years": "years",
}

_MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))
_ORD = r"(?:st|nd|rd|th)?"

# Year-first: "2025-12-04", "2025/12/04", "2025.12.04"
_ISO = re.compile(r"(\d{4})([-/.])(\d{1,2})\2(\d{1,2})")
_SLASH = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
# "December 1st, 2025", "Dec 1 2025", "December 1st" (current year)
_MONTH_DAY_YEAR = re.compile(
    rf"(?:the\s+)?({_MONTH_RE})\.?\s+(\d{{1,2}}){_ORD}(?:\s*,?\s*(\d{{4}}))?"
)
# "1st December 2025", "the 1st of December, 2025"
_DAY_MONTH_YEAR = re.compile(
    rf"(?:the\s+)?(\d{{1,2}}){_ORD}\s+(?:of\s+)?({_MONTH_RE})\.?(?:\s*,?\s*(\d{{4}}))?"
)
_TERM = re.compile(r"(\d+|[a-z]+)\s+([a-z]+)")
_OFFSET_SPLIT = re.compile(r"\s*(?:,\s*and|,|\band\b)\s*")
_RELATIVE = re.compile(
    r"(?P<offset>.+?)\s+(?P<dir>before|after|from|until)\s+(?P<base>.+)"
)


@dataclass
class _Offset:
    years: int = 0
    months: int = 0
    days: int = 0

    def apply(self, d: date, sign: int) -> date:
        total_months = (
            d.year * 12 + (d.month - 1) + sign * (self.years * 12 + self.months)
        )
        year, month0 = divmod(total_months, 12)
        if not 1 <= year <= 9999:
            raise ValueError("resulting date is out of range")
        month = month0 + 1
        day = min(d.day, calendar.monthrange(year, month)[1])
        try:
            return date(year, month, day) + timedelta(days=sign * self.days)
        except OverflowError as e:
            raise ValueError("resulting date is out of range") from e


def _make_date(year: int, month: int, day: int) -> date:
    try:
        return date(year, month, day)
    except ValueError as e:
        raise ValueError(f"invalid date: {year}-{month}-{day}") from e


def _parse_offset(s: str) -> _Offset:
    """Parse e.g. '1 year and 2 months' or 'three weeks'."""
    offset = _Offset()
    parts = [p for p in _OFFSET_SPLIT.split(s) if p]
    if not parts:
        raise ValueError(f"unrecognized offset: {s!r}")
    for part in parts:
        m = _TERM.fullmatch(part)
        if m is None:
            raise ValueError(f"unrecognized offset: {s!r}")
        qty_s, unit_s = m.groups()
        qty = int(qty_s) if qty_s.isdigit() else NUMBER_WORDS.get(qty_s)
        unit = UNITS.get(unit_s)
        if qty is None or unit is None:
            raise ValueError(f"unrecognized offset: {s!r}")
        if unit == "days":
            offset.days += qty
        elif unit == "weeks":
            offset.days += 7 * qty
        elif unit == "fortnights":
            offset.days += 14 * qty
        elif unit == "months":
            offset.months += qty
        else:
            offset.years += qty
    return offset


def _parse_absolute(s: str, today: date) -> date | None:
    if m := _ISO.fullmatch(s):
        return _make_date(int(m[1]), int(m[3]), int(m[4]))
    if m := _SLASH.fullmatch(s):
        return _make_date(int(m[3]), int(m[1]), int(m[2]))
    if m := _MONTH_DAY_YEAR.fullmatch(s):
        year = int(m[3]) if m[3] else today.year
        return _make_date(year, MONTHS[m[1]], int(m[2]))
    if m := _DAY_MONTH_YEAR.fullmatch(s):
        year = int(m[3]) if m[3] else today.year
        return _make_date(year, MONTHS[m[2]], int(m[1]))
    return None


def _parse_simple(s: str, today: date) -> date | None:
    if s in ("today", "now"):
        return today
    if s == "tomorrow":
        return today + timedelta(days=1)
    if s == "yesterday":
        return today - timedelta(days=1)
    if s == "the day after tomorrow":
        return today + timedelta(days=2)
    if s == "the day before yesterday":
        return today - timedelta(days=2)

    words = s.split()
    if len(words) == 2 and words[0] in ("next", "last", "this"):
        which, target = words
        if target in WEEKDAYS:
            wd = WEEKDAYS[target]
            if which == "next":
                return today + timedelta(days=(wd - today.weekday() - 1) % 7 + 1)
            if which == "last":
                return today - timedelta(days=(today.weekday() - wd - 1) % 7 + 1)
            # "this <weekday>": the given weekday in the current Mon-Sun week
            return today + timedelta(days=wd - today.weekday())
        if target in UNITS and which != "this":
            sign = 1 if which == "next" else -1
            return _parse_offset(f"1 {target}").apply(today, sign)
        if target in UNITS:
            return today

    if words and words[0] == "in" and len(words) > 1:
        return _parse_offset(" ".join(words[1:])).apply(today, 1)
    if len(words) > 1 and words[-1] == "ago":
        return _parse_offset(" ".join(words[:-1])).apply(today, -1)
    if len(words) > 2 and words[-2:] == ["from", "now"]:
        return _parse_offset(" ".join(words[:-2])).apply(today, 1)
    return None


def _parse(s: str, today: date) -> date:
    result = _parse_simple(s, today)
    if result is not None:
        return result
    result = _parse_absolute(s, today)
    if result is not None:
        return result
    if m := _RELATIVE.fullmatch(s):
        offset = _parse_offset(m["offset"])
        base = _parse(m["base"], today)
        sign = -1 if m["dir"] in ("before", "until") else 1
        return offset.apply(base, sign)
    raise ValueError(f"unrecognized date: {s!r}")


def parse(s: str, today: date | None = None) -> date:
    """Parse a natural-language date expression into a :class:`datetime.date`.

    Args:
        s: The expression, e.g. ``"next Tuesday"`` or
            ``"5 days before December 1st, 2025"``.
        today: Reference date for relative expressions. Defaults to
            :meth:`datetime.date.today`.

    Raises:
        ValueError: If the string is not a recognized date expression.
    """
    if today is None:
        today = date.today()
    normalized = " ".join(s.strip().lower().split())
    normalized = normalized.rstrip(".")
    if not normalized:
        raise ValueError("empty date string")
    return _parse(normalized, today)
