"""Build minimal parser-valid schedule pageProps for coordinator tests."""

from __future__ import annotations

from typing import Any

from custom_components.maxpreps.models import TeamSeason
from custom_components.maxpreps.urls import build_schedule_url


def build_minimal_schedule_page_props(team_season: TeamSeason) -> dict[str, Any]:
    """Return pageProps sufficient for ``parse_schedule_page_props`` with empty contests."""
    return {
        "teamContext": {
            "data": {
                "teamId": team_season.school_id,
                "sportSeasonId": team_season.sport_season_id,
                "canonicalUrl": build_schedule_url(team_season.canonical_url),
                "sport": team_season.sport,
                "gender": team_season.gender,
                "level": team_season.level,
                "year": team_season.year,
                "season": team_season.season,
            }
        },
        "contests": [],
    }
