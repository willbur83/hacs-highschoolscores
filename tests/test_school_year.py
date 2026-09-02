"""Applicable school-year helper unit tests (no Home Assistant import)."""

from __future__ import annotations

from datetime import date

from custom_components.maxpreps.school_year import applicable_school_year


def test_applicable_school_year_june_30_2026():
    assert applicable_school_year(date(2026, 6, 30)) == "25-26"


def test_applicable_school_year_july_1_2026():
    assert applicable_school_year(date(2026, 7, 1)) == "26-27"


def test_applicable_school_year_june_30_2027():
    assert applicable_school_year(date(2027, 6, 30)) == "26-27"


def test_applicable_school_year_july_1_2027():
    assert applicable_school_year(date(2027, 7, 1)) == "27-28"
