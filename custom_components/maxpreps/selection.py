"""Pure helpers for supported-format filtering and current-cohort selection."""

from __future__ import annotations

import re
from collections import Counter
from urllib.parse import urlparse

from custom_components.maxpreps.const import SUPPORTED_SPORTS
from custom_components.maxpreps.exceptions import (
    CurrentCohortAmbiguousError,
    CurrentCohortEmptyError,
)
from custom_components.maxpreps.models import TeamSeason

_URL_YEAR_SEGMENT = re.compile(r"^\d{2}-\d{2}$")
_SCHOOL_YEAR = re.compile(r"^(\d{1,2})-(\d{1,2})$")


def is_supported_format(team_season: TeamSeason) -> bool:
    """Return whether ``team_season`` is on the evidence-based supported-format allowlist."""
    return team_season.sport in SUPPORTED_SPORTS


def canonical_url_year_segments(canonical_url: str) -> tuple[str, ...]:
    """Return every ``YY-YY`` path segment in ``canonical_url`` (may be empty)."""
    path = urlparse(canonical_url).path
    segments = (segment for segment in path.split("/") if segment)
    return tuple(
        segment for segment in segments if _URL_YEAR_SEGMENT.fullmatch(segment)
    )


def canonical_url_year_segment(canonical_url: str) -> str | None:
    """Return the sole ``YY-YY`` path segment, or ``None`` when absent.

    When multiple ``YY-YY`` segments appear, returns the first (corroborating
    evidence is ambiguous; callers treat multi-segment URLs as contradictory).
    """
    segments = canonical_url_year_segments(canonical_url)
    if not segments:
        return None
    return segments[0]


def current_cohort_year(team_seasons: list[TeamSeason]) -> str:
    """Return the current school-year cohort string (e.g. ``26-27``).

    Raises:
        CurrentCohortEmptyError: ``team_seasons`` is empty.
        CurrentCohortAmbiguousError: rows do not identify one cohort conservatively.
    """
    if not team_seasons:
        raise CurrentCohortEmptyError("team_seasons is empty")

    for team_season in team_seasons:
        _school_year_start(team_season.year)

    year_counts = Counter(team_season.year for team_season in team_seasons)
    unique_years = set(year_counts)

    if len(unique_years) == 1:
        cohort_year = next(iter(unique_years))
        _raise_if_any_row_has_contradictory_url_evidence(team_seasons)
        return cohort_year

    max_count = max(year_counts.values())
    modes = [year for year, count in year_counts.items() if count == max_count]
    if len(modes) > 1:
        raise CurrentCohortAmbiguousError("tied modal years among team-season rows")

    if max_count <= len(team_seasons) / 2:
        raise CurrentCohortAmbiguousError(
            "no unambiguous majority year among team-season rows"
        )

    majority_year = modes[0]
    minority_years = unique_years - {majority_year}

    if _has_adjacent_school_years({majority_year, *minority_years}):
        for year in minority_years:
            if not _is_clearly_older_school_year(year, majority_year):
                raise CurrentCohortAmbiguousError(
                    "adjacent school years without a safe historical-leftover pattern"
                )

    for team_season in team_seasons:
        if team_season.year == majority_year:
            if _majority_row_has_ambiguous_url_evidence(team_season):
                raise CurrentCohortAmbiguousError(
                    "current-cohort row has contradictory canonical_url year-segment evidence"
                )
            continue

        if not _is_historical_leftover(team_season, majority_year):
            raise CurrentCohortAmbiguousError(
                "minority-year row is not a clearly identified historical leftover"
            )

    return majority_year


def _raise_if_any_row_has_contradictory_url_evidence(
    team_seasons: list[TeamSeason],
) -> None:
    for team_season in team_seasons:
        if _majority_row_has_ambiguous_url_evidence(team_season):
            raise CurrentCohortAmbiguousError(
                "current-cohort row has contradictory canonical_url year-segment evidence"
            )


def in_current_cohort(team_seasons: list[TeamSeason]) -> list[TeamSeason]:
    """Return rows in the resolved current cohort, preserving input order."""
    cohort_year = current_cohort_year(team_seasons)
    return [
        team_season
        for team_season in team_seasons
        if team_season.year == cohort_year
    ]


def selectable_team_seasons(team_seasons: list[TeamSeason]) -> list[TeamSeason]:
    """Return current-cohort rows on the supported-format allowlist."""
    return [
        team_season
        for team_season in in_current_cohort(team_seasons)
        if is_supported_format(team_season)
    ]


def _school_year_start(year: str) -> int:
    match = _SCHOOL_YEAR.fullmatch(year)
    if match is None:
        raise CurrentCohortAmbiguousError(
            f"malformed school year value among team-season rows: {year!r}"
        )
    return int(match.group(1))


def _is_clearly_older_school_year(year: str, reference_year: str) -> bool:
    return _school_year_start(year) < _school_year_start(reference_year)


def _has_adjacent_school_years(years: set[str]) -> bool:
    starts = sorted(_school_year_start(year) for year in years)
    return any(right - left == 1 for left, right in zip(starts, starts[1:]))


def _is_historical_leftover(team_season: TeamSeason, majority_year: str) -> bool:
    if not _is_clearly_older_school_year(team_season.year, majority_year):
        return False

    url_year = canonical_url_year_segment(team_season.canonical_url)
    if url_year is None:
        return False

    if len(canonical_url_year_segments(team_season.canonical_url)) > 1:
        return False

    return url_year == team_season.year


def _majority_row_has_ambiguous_url_evidence(team_season: TeamSeason) -> bool:
    url_segments = canonical_url_year_segments(team_season.canonical_url)
    if not url_segments:
        return False

    if len(url_segments) > 1:
        return True

    url_year = url_segments[0]
    return url_year != team_season.year
