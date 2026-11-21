"""Calendar-month helpers shared by services and agent tools."""
import calendar
import re
from datetime import date

from app.core.errors import ValidationFailedError

_MONTH_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def month_bounds(year: int, month: int) -> tuple[date, date]:
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def shift_month(first_of_month: date, delta: int) -> date:
    idx = first_of_month.year * 12 + (first_of_month.month - 1) + delta
    return date(idx // 12, idx % 12 + 1, 1)


def label(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def resolve_month(value: str | None, today: date) -> tuple[date, date, str]:
    """'this_month' | 'last_month' | 'YYYY-MM' | None(=this month) -> (first, last, 'YYYY-MM')."""
    if value in (None, "", "this_month"):
        first = today.replace(day=1)
    elif value == "last_month":
        first = shift_month(today.replace(day=1), -1)
    else:
        m = _MONTH_RE.match(value)
        if not m:
            raise ValidationFailedError("Month must be 'YYYY-MM', 'this_month' or 'last_month'",
                                        code="INVALID_PERIOD")
        first = date(int(m.group(1)), int(m.group(2)), 1)
    _, last = month_bounds(first.year, first.month)
    return first, last, label(first)


def add_months(d: date, n: int) -> date:
    """Same day-of-month n months later (clamped to the end of shorter months)."""
    first = shift_month(d.replace(day=1), n)
    return first.replace(day=min(d.day, calendar.monthrange(first.year, first.month)[1]))
