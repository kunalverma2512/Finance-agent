"""Decimal helpers. All money maths in the app goes through here (never float)."""
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def q2(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def q2_ceil(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_CEILING)


def pct(part: Decimal, whole: Decimal) -> Decimal | None:
    """Percentage rounded to 2 dp, or None when the whole is zero."""
    if whole == 0:
        return None
    return q2(part / whole * 100)
