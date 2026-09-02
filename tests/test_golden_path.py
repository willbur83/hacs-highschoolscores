"""Slice 11 cross-school client golden paths (FixtureTransport only)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from custom_components.maxpreps.client import MaxPrepsClient
from custom_components.maxpreps.models import GameStatus, School, Schedule, TeamSeason
from tests.helpers.fixture_transport import FixtureTransport
from tests.test_schedule import (
    BASEBALL_SPORT_SEASON_ID,
    FOOTBALL_SPORT_SEASON_ID,
    RIVERWOOD_CONTEST_ID,
)
from tests.test_search import (
    BAINBRIDGE_GA_ID,
    BAINBRIDGE_GA_URL,
    CENTENNIAL_ROSWELL_ID,
    CENTENNIAL_ROSWELL_URL,
    PIKE_COUNTY_GA_ID,
    PIKE_COUNTY_GA_URL,
    ST_EDWARD_OH_ID,
    ST_EDWARD_OH_URL,
)

CURRENT_YEAR = "26-27"
REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_SCRIPT = REPO_ROOT / "scripts" / "demo_client.py"

CENTENNIAL_FOOTBALL_CANONICAL = (
    "https://www.maxpreps.com/ga/roswell/centennial-knights/football/"
)
CENTENNIAL_BASEBALL_CANONICAL = (
    "https://www.maxpreps.com/ga/roswell/centennial-knights/baseball/"
)
CENTENNIAL_VOLLEYBALL_CANONICAL = (
    "https://www.maxpreps.com/ga/roswell/centennial-knights/volleyball/"
)

FOOTBALL_SCHOOL_CASES = [
    (
        "Centennial",
        CENTENNIAL_ROSWELL_ID,
        CENTENNIAL_ROSWELL_URL,
        10,
        "2-0",
    ),
    (
        "Bainbridge",
        BAINBRIDGE_GA_ID,
        BAINBRIDGE_GA_URL,
        10,
        "0-2",
    ),
    (
        "Pike County",
        PIKE_COUNTY_GA_ID,
        PIKE_COUNTY_GA_URL,
        10,
        "1-1",
    ),
    (
        "Saint Edward",
        ST_EDWARD_OH_ID,
        ST_EDWARD_OH_URL,
        10,
        "2-0",
    ),
]

FOOTBALL_GOLDEN_CASES = [
    pytest.param(*case, id=case[0].lower().replace(" ", "_").replace(".", ""))
    for case in FOOTBALL_SCHOOL_CASES
]


def _select_school_by_id(schools: list[School], school_id: str) -> School:
    matches = [school for school in schools if school.school_id == school_id]
    assert len(matches) == 1, f"expected exactly one school for {school_id!r}, got {len(matches)}"
    return matches[0]


def _select_team(
    team_seasons: list[TeamSeason],
    *,
    year: str,
    sport: str,
    gender: str,
    level: str,
    sport_season_id: str | None = None,
) -> TeamSeason:
    matches = [
        team
        for team in team_seasons
        if team.year == year
        and team.sport == sport
        and team.gender == gender
        and team.level == level
        and (sport_season_id is None or team.sport_season_id == sport_season_id)
    ]
    assert len(matches) == 1, (
        f"expected exactly one {year} {gender} {level} {sport} team, got {len(matches)}"
    )
    return matches[0]


def _assert_football_schedule(schedule: Schedule, *, school_id: str, expected_games: int, team_record: str) -> None:
    assert schedule.team_season.school_id == school_id
    assert schedule.team_season.sport_season_id == FOOTBALL_SPORT_SEASON_ID
    assert schedule.team_season.year == CURRENT_YEAR
    assert schedule.team_season.sport == "Football"
    assert schedule.team_season.gender == "Boys"
    assert schedule.team_season.level == "Varsity"
    assert len(schedule.games) == expected_games
    assert all(game.status is not GameStatus.DELETED for game in schedule.games)
    assert all(game.date.tzinfo is None for game in schedule.games)
    assert schedule.team_record == team_record


@pytest.fixture
def transport() -> FixtureTransport:
    return FixtureTransport()


@pytest.fixture
def client(transport: FixtureTransport) -> MaxPrepsClient:
    return MaxPrepsClient(transport)


@pytest.mark.parametrize(
    ("search_query", "school_id", "canonical_url", "expected_games", "team_record"),
    FOOTBALL_GOLDEN_CASES,
)
def test_football_golden_path_search_to_schedule(
    client: MaxPrepsClient,
    search_query: str,
    school_id: str,
    canonical_url: str,
    expected_games: int,
    team_record: str,
) -> None:
    school = _select_school_by_id(client.search_schools(search_query), school_id)
    assert school.canonical_url == canonical_url

    football = _select_team(
        client.get_school_teams(school),
        year=CURRENT_YEAR,
        sport="Football",
        gender="Boys",
        level="Varsity",
        sport_season_id=FOOTBALL_SPORT_SEASON_ID,
    )
    schedule = client.get_schedule(football)
    _assert_football_schedule(
        schedule,
        school_id=school_id,
        expected_games=expected_games,
        team_record=team_record,
    )


def test_football_sport_season_id_shared_across_schools_via_client(
    client: MaxPrepsClient,
) -> None:
    football_teams: list[TeamSeason] = []
    for search_query, school_id, _, _, _ in FOOTBALL_SCHOOL_CASES:
        school = _select_school_by_id(client.search_schools(search_query), school_id)
        football = _select_team(
            client.get_school_teams(school),
            year=CURRENT_YEAR,
            sport="Football",
            gender="Boys",
            level="Varsity",
            sport_season_id=FOOTBALL_SPORT_SEASON_ID,
        )
        assert football.school_id == school_id
        football_teams.append(football)

    sport_season_ids = {team.sport_season_id for team in football_teams}
    school_ids = {team.school_id for team in football_teams}
    assert sport_season_ids == {FOOTBALL_SPORT_SEASON_ID}
    assert school_ids == {
        CENTENNIAL_ROSWELL_ID,
        BAINBRIDGE_GA_ID,
        PIKE_COUNTY_GA_ID,
        ST_EDWARD_OH_ID,
    }
    assert len({team.identity_key() for team in football_teams}) == 4


def test_centennial_baseball_golden_path(client: MaxPrepsClient) -> None:
    school = _select_school_by_id(
        client.search_schools("Centennial"),
        CENTENNIAL_ROSWELL_ID,
    )
    baseball = _select_team(
        client.get_school_teams(school),
        year=CURRENT_YEAR,
        sport="Baseball",
        gender="Boys",
        level="Varsity",
        sport_season_id=BASEBALL_SPORT_SEASON_ID,
    )
    assert baseball.canonical_url == CENTENNIAL_BASEBALL_CANONICAL

    schedule = client.get_schedule(baseball)
    assert schedule.team_season.school_id == CENTENNIAL_ROSWELL_ID
    assert schedule.team_season.sport_season_id == BASEBALL_SPORT_SEASON_ID
    assert len(schedule.games) == 30
    assert all(game.status is not GameStatus.DELETED for game in schedule.games)
    assert all(game.date.tzinfo is None for game in schedule.games)
    assert schedule.team_record is None


def test_centennial_football_excludes_deleted_contest(client: MaxPrepsClient) -> None:
    school = _select_school_by_id(
        client.search_schools("Centennial"),
        CENTENNIAL_ROSWELL_ID,
    )
    football = _select_team(
        client.get_school_teams(school),
        year=CURRENT_YEAR,
        sport="Football",
        gender="Boys",
        level="Varsity",
        sport_season_id=FOOTBALL_SPORT_SEASON_ID,
    )
    schedule = client.get_schedule(football)
    assert RIVERWOOD_CONTEST_ID not in {game.id for game in schedule.games}


def test_volleyball_schedule_client_regression(client: MaxPrepsClient) -> None:
    school = _select_school_by_id(
        client.search_schools("Centennial"),
        CENTENNIAL_ROSWELL_ID,
    )
    volleyball = _select_team(
        client.get_school_teams(school),
        year=CURRENT_YEAR,
        sport="Volleyball",
        gender="Girls",
        level="Varsity",
    )
    assert volleyball.canonical_url == CENTENNIAL_VOLLEYBALL_CANONICAL

    schedule = client.get_schedule(volleyball)
    assert len(schedule.games) == 30
    assert schedule.team_record == "3-14"
    assert all(game.date.tzinfo is None for game in schedule.games)


def test_demo_fixtures_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, str(DEMO_SCRIPT), "--fixtures"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
