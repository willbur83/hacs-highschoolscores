#!/usr/bin/env python3
"""Fixtures-only MaxPreps client demo (Slice 11 PRODUCT §30 intent)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from custom_components.maxpreps.client import MaxPrepsClient
from custom_components.maxpreps.models import Game, Schedule, School, TeamSeason
from tests.helpers.fixture_transport import FixtureTransport
from tests.test_schedule import BASEBALL_SPORT_SEASON_ID, FOOTBALL_SPORT_SEASON_ID
from tests.test_search import CENTENNIAL_ROSWELL_ID

CURRENT_YEAR = "26-27"


def _select_school_by_id(schools: list[School], school_id: str) -> School:
    matches = [school for school in schools if school.school_id == school_id]
    if len(matches) != 1:
        raise SystemExit(
            f"expected exactly one school for {school_id!r}, found {len(matches)}"
        )
    return matches[0]


def _select_team(
    team_seasons: list[TeamSeason],
    *,
    year: str,
    sport: str,
    gender: str,
    level: str,
    sport_season_id: str,
) -> TeamSeason:
    matches = [
        team
        for team in team_seasons
        if team.year == year
        and team.sport == sport
        and team.gender == gender
        and team.level == level
        and team.sport_season_id == sport_season_id
    ]
    if len(matches) != 1:
        raise SystemExit(
            f"expected exactly one {year} {gender} {level} {sport} team, found {len(matches)}"
        )
    return matches[0]


def _format_location(school: School) -> str | None:
    if school.city and school.state:
        return f"{school.city}, {school.state}"
    if school.city:
        return school.city
    if school.state:
        return school.state
    return None


def _serialize_game(game: Game) -> dict[str, Any]:
    if game.date.tzinfo is not None:
        raise SystemExit(f"game {game.id!r} date must be timezone-naive")
    return {
        "date": game.date.isoformat(),
        "opponent": game.opponent_name,
        "status": game.status.value,
        "team_score": game.team_score,
        "opponent_score": game.opponent_score,
        "result": game.result,
    }


def _serialize_schedule(school: School, schedule: Schedule) -> dict[str, Any]:
    team = schedule.team_season
    return {
        "school": {
            "name": school.name,
            "location": _format_location(school),
        },
        "team": {
            "display_label": team.display_label,
            "sport": team.sport,
            "level": team.level,
            "gender": team.gender,
        },
        "games": [_serialize_game(game) for game in schedule.games],
    }


def _run_fixtures_demo() -> list[dict[str, Any]]:
    client = MaxPrepsClient(FixtureTransport())
    school = _select_school_by_id(
        client.search_schools("Centennial"),
        CENTENNIAL_ROSWELL_ID,
    )
    team_seasons = client.get_school_teams(school)

    football = _select_team(
        team_seasons,
        year=CURRENT_YEAR,
        sport="Football",
        gender="Boys",
        level="Varsity",
        sport_season_id=FOOTBALL_SPORT_SEASON_ID,
    )
    baseball = _select_team(
        team_seasons,
        year=CURRENT_YEAR,
        sport="Baseball",
        gender="Boys",
        level="Varsity",
        sport_season_id=BASEBALL_SPORT_SEASON_ID,
    )

    return [
        _serialize_schedule(school, client.get_schedule(football)),
        _serialize_schedule(school, client.get_schedule(baseball)),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MaxPreps client fixtures demo")
    parser.add_argument(
        "--fixtures",
        action="store_true",
        help="Run against committed fixtures only (no live HTTP)",
    )
    args = parser.parse_args(argv)

    if not args.fixtures:
        parser.error("only --fixtures mode is supported")

    output = _run_fixtures_demo()
    json.dump(output, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
