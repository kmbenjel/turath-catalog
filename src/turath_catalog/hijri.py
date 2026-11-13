"""Hijri (AH) years to Gregorian (CE) years with the tabular Islamic calendar.

A Hijri year is about 354 days, so it overlaps one or two Gregorian years. The dataset gives
both ends (`death_ce_from`, `death_ce_to`) rather than a single guessed year. The tabular
calendar can differ from the observed one by a day or two, which matters only at year edges.
"""

from __future__ import annotations

import math

_ISLAMIC_EPOCH = 1948439.5  # Julian day of 1 Muharram 1 AH (civil epoch, 16 July 622 CE)


def _islamic_to_jd(year: int, month: int, day: int) -> float:
    return day + math.ceil(29.5 * (month - 1)) + (year - 1) * 354 + math.floor((3 + 11 * year) / 30) + _ISLAMIC_EPOCH - 1


def _jd_to_gregorian_year(jd: float) -> int:
    z = math.floor(jd + 0.5)
    a = math.floor((z - 1867216.25) / 36524.25)
    a = z + 1 + a - math.floor(a / 4)
    b = a + 1524
    c = math.floor((b - 122.1) / 365.25)
    d = math.floor(365.25 * c)
    e = math.floor((b - d) / 30.6001)
    month = e - 1 if e < 14 else e - 13
    return c - 4716 if month > 2 else c - 4715


def ah_to_ce_range(year_ah: int) -> tuple[int, int]:
    """The first and last Gregorian (proleptic) years that Hijri year `year_ah` overlaps."""
    if year_ah < 1:
        raise ValueError(f"Hijri year must be >= 1, got {year_ah}")
    start = _islamic_to_jd(year_ah, 1, 1)
    end = _islamic_to_jd(year_ah + 1, 1, 1) - 1
    return _jd_to_gregorian_year(start), _jd_to_gregorian_year(end)


def ce_to_ah_range(year_ce: int) -> tuple[int, int]:
    """The Hijri years that Gregorian year `year_ce` overlaps (inverse of `ah_to_ce_range`)."""
    guess = max(1, int((year_ce - 622) * 1.0307) + 1)
    hits = [y for y in range(max(1, guess - 3), guess + 4) if ah_to_ce_range(y)[0] <= year_ce <= ah_to_ce_range(y)[1]]
    if not hits:
        raise ValueError(f"no Hijri year overlaps {year_ce} CE")
    return min(hits), max(hits)


def century_ah(year_ah: int) -> int:
    """Hijri century of a year: 1–100 → 1, 101–200 → 2."""
    return (year_ah - 1) // 100 + 1
