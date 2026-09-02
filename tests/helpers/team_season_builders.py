"""Synthetic TeamSeason builders for selection helper tests."""

from __future__ import annotations

from custom_components.maxpreps.models import TeamSeason

_DEFAULT_SCHOOL_ID = "test-school-id"


def make_team_season(
    *,
    school_id: str = _DEFAULT_SCHOOL_ID,
    sport_season_id: str = "ssid-1",
    canonical_url: str = "https://www.maxpreps.com/ga/roswell/centennial-knights/football/",
    sport: str = "Football",
    gender: str = "Boys",
    level: str = "Varsity",
    year: str = "26-27",
    season: str = "Fall",
    all_season_id: str | None = None,
    is_published: bool | None = None,
) -> TeamSeason:
    return TeamSeason(
        school_id=school_id,
        sport_season_id=sport_season_id,
        canonical_url=canonical_url,
        sport=sport,
        gender=gender,
        level=level,
        year=year,
        season=season,
        all_season_id=all_season_id,
        is_published=is_published,
    )
