"""Layer 1 tests for websocket schedule DTO serialization (no Home Assistant)."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from custom_components.maxpreps.models import GameStatus, TeamSeason
from custom_components.maxpreps.parsing.schedule import parse_schedule_page_props
from custom_components.maxpreps.parsing.sport_seasons import parse_sport_seasons
from custom_components.maxpreps.schedule_payload import (
    SCHEMA_VERSION,
    build_program_schedule_payload,
    sort_term_snapshots_for_presentation,
)
from custom_components.maxpreps.snapshots import (
    ProgramResolutionStatus,
    ProgramSnapshot,
    TermRefreshStatus,
    TermSnapshot,
)
from tests.helpers.fixtures import load_schedule_page_props, load_sport_seasons
from tests.helpers.schedule_page_props_builder import build_minimal_schedule_page_props
from tests.helpers.team_season_builders import make_team_season
from tests.test_search import CENTENNIAL, CENTENNIAL_ROSWELL_ID

FRESHMAN_BASEBALL_SPRING_ID = "631feb7b-f4f4-44d1-96b7-a75a2b6507ed"
FRESHMAN_BASEBALL_FALL_ID = "519650ec-c701-4eee-ab7f-1b3026a0e2b3"

ENTITY_ID = "sensor.centennial_boys_varsity_football"


def _freshman_baseball_team_season(sport_season_id: str) -> TeamSeason:
    rows = load_sport_seasons(f"{CENTENNIAL}/sport-seasons-26-27.json")
    for team_season in parse_sport_seasons(rows):
        if team_season.sport_season_id == sport_season_id:
            return team_season
    raise AssertionError(f"freshman baseball row not found: {sport_season_id}")


def _term_from_schedule(schedule_path: str, *, status: TermRefreshStatus = TermRefreshStatus.REFRESHED) -> TermSnapshot:
    page_props = load_schedule_page_props(schedule_path)
    assert page_props is not None
    schedule = parse_schedule_page_props(page_props)
    return TermSnapshot(
        team_season=schedule.team_season,
        schedule=schedule,
        status=status,
        error_type=None,
        error_message=None,
        last_success_at=datetime(2026, 9, 2, 12, 0, 0),
    )


def _program(
    *,
    sport: str,
    gender: str,
    level: str,
    resolution_status: ProgramResolutionStatus,
    terms: tuple[TermSnapshot, ...],
) -> ProgramSnapshot:
    return ProgramSnapshot(
        sport=sport,
        gender=gender,
        level=level,
        resolution_status=resolution_status,
        terms=terms,
    )


def _payload_for_program(program: ProgramSnapshot, *, applicable_school_year: str = "26-27") -> dict:
    return build_program_schedule_payload(
        ENTITY_ID,
        school_id=CENTENNIAL_ROSWELL_ID,
        school_name="Centennial",
        applicable_school_year=applicable_school_year,
        program=program,
    )


def test_football_payload_has_ten_non_deleted_games() -> None:
    program = _program(
        sport="Football",
        gender="Boys",
        level="Varsity",
        resolution_status=ProgramResolutionStatus.RESOLVED,
        terms=(_term_from_schedule(f"{CENTENNIAL}/schedule-26-27.json"),),
    )
    payload = _payload_for_program(program)

    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["entity_id"] == ENTITY_ID
    assert payload["school_id"] == CENTENNIAL_ROSWELL_ID
    assert payload["school_name"] == "Centennial"
    assert payload["applicable_school_year"] == "26-27"
    assert payload["sport"] == "Football"
    assert payload["gender"] == "Boys"
    assert payload["level"] == "Varsity"
    assert payload["display_label"] == "Boys Varsity Football"
    assert payload["resolution_status"] == "resolved"
    assert len(payload["terms"]) == 1
    assert payload["terms"][0]["season"] == "Fall"
    assert payload["terms"][0]["year"] == "26-27"
    assert payload["terms"][0]["status"] == "refreshed"
    assert len(payload["terms"][0]["games"]) == 10
    assert all(game["status"] != "deleted" for game in payload["terms"][0]["games"])


def test_baseball_payload_has_thirty_non_deleted_games() -> None:
    program = _program(
        sport="Baseball",
        gender="Boys",
        level="Varsity",
        resolution_status=ProgramResolutionStatus.RESOLVED,
        terms=(_term_from_schedule(f"{CENTENNIAL}/baseball-schedule-26-27.json"),),
    )
    payload = _payload_for_program(program)

    assert len(payload["terms"]) == 1
    assert len(payload["terms"][0]["games"]) == 30


def test_freshman_multi_term_ordered_fall_before_spring() -> None:
    fall = _freshman_baseball_team_season(FRESHMAN_BASEBALL_FALL_ID)
    spring = _freshman_baseball_team_season(FRESHMAN_BASEBALL_SPRING_ID)
    fall_schedule = parse_schedule_page_props(build_minimal_schedule_page_props(fall))
    spring_schedule = parse_schedule_page_props(build_minimal_schedule_page_props(spring))

    # Input in school-home encounter order (Spring before Fall in sport-seasons fixture).
    terms = (
        TermSnapshot(
            team_season=spring_schedule.team_season,
            schedule=spring_schedule,
            status=TermRefreshStatus.REFRESHED,
            error_type=None,
            error_message=None,
            last_success_at=None,
        ),
        TermSnapshot(
            team_season=fall_schedule.team_season,
            schedule=fall_schedule,
            status=TermRefreshStatus.REFRESHED,
            error_type=None,
            error_message=None,
            last_success_at=None,
        ),
    )
    program = _program(
        sport="Baseball",
        gender="Boys",
        level="Freshman",
        resolution_status=ProgramResolutionStatus.RESOLVED,
        terms=terms,
    )
    payload = _payload_for_program(program)

    assert [term["season"] for term in payload["terms"]] == ["Fall", "Spring"]
    assert payload["terms"][0]["year"] == "26-27"
    assert payload["terms"][1]["year"] == "26-27"


def test_sort_term_snapshots_for_presentation_matches_dto_order() -> None:
    fall = TermSnapshot(
        team_season=make_team_season(season="Fall", sport_season_id=FRESHMAN_BASEBALL_FALL_ID),
        schedule=None,
        status=TermRefreshStatus.REFRESHED,
        error_type=None,
        error_message=None,
        last_success_at=None,
    )
    spring = TermSnapshot(
        team_season=make_team_season(season="Spring", sport_season_id=FRESHMAN_BASEBALL_SPRING_ID),
        schedule=None,
        status=TermRefreshStatus.REFRESHED,
        error_type=None,
        error_message=None,
        last_success_at=None,
    )
    ordered = sort_term_snapshots_for_presentation((spring, fall))
    assert [term.team_season.season for term in ordered] == ["Fall", "Spring"]


def test_empty_contests_yields_empty_games_list() -> None:
    team_season = make_team_season()
    schedule = parse_schedule_page_props(build_minimal_schedule_page_props(team_season))
    program = _program(
        sport="Football",
        gender="Boys",
        level="Varsity",
        resolution_status=ProgramResolutionStatus.RESOLVED,
        terms=(
            TermSnapshot(
                team_season=schedule.team_season,
                schedule=schedule,
                status=TermRefreshStatus.REFRESHED,
                error_type=None,
                error_message=None,
                last_success_at=None,
            ),
        ),
    )
    payload = _payload_for_program(program)

    assert len(payload["terms"]) == 1
    assert payload["terms"][0]["games"] == []


def test_stale_rollover_retained_term_serializes_games_and_status() -> None:
    term = _term_from_schedule(f"{CENTENNIAL}/schedule-26-27.json", status=TermRefreshStatus.STALE)
    program = _program(
        sport="Football",
        gender="Boys",
        level="Varsity",
        resolution_status=ProgramResolutionStatus.WAITING_FOR_APPLICABLE_YEAR,
        terms=(term,),
    )
    payload = _payload_for_program(program, applicable_school_year="27-28")

    assert payload["applicable_school_year"] == "27-28"
    assert payload["resolution_status"] == "waiting_for_applicable_year"
    assert payload["terms"][0]["status"] == "stale"
    assert payload["terms"][0]["year"] == "26-27"
    assert len(payload["terms"][0]["games"]) == 10


def test_unresolved_program_has_empty_terms() -> None:
    program = _program(
        sport="Football",
        gender="Girls",
        level="Varsity",
        resolution_status=ProgramResolutionStatus.UNRESOLVED,
        terms=(),
    )
    payload = _payload_for_program(program)

    assert payload["resolution_status"] == "unresolved"
    assert payload["terms"] == []


def test_deleted_games_excluded_from_games_list() -> None:
    term = _term_from_schedule(f"{CENTENNIAL}/schedule-26-27.json")
    assert term.schedule is not None
    deleted_game = replace(term.schedule.games[0], id="deleted-game-id", status=GameStatus.DELETED)
    schedule_with_deleted = replace(
        term.schedule,
        games=[deleted_game, *term.schedule.games],
    )
    term_with_deleted = replace(term, schedule=schedule_with_deleted)

    program = _program(
        sport="Football",
        gender="Boys",
        level="Varsity",
        resolution_status=ProgramResolutionStatus.RESOLVED,
        terms=(term_with_deleted,),
    )
    payload = _payload_for_program(program)

    games = payload["terms"][0]["games"]
    assert len(games) == 10
    assert all(game["status"] != "deleted" for game in games)
    assert all(game["id"] != "deleted-game-id" for game in games)


def test_error_term_without_schedule_serializes_metadata_and_empty_games() -> None:
    """Per-term isolation: one ERROR sibling must not drop a REFRESHED term."""
    fall = _freshman_baseball_team_season(FRESHMAN_BASEBALL_FALL_ID)
    spring = _freshman_baseball_team_season(FRESHMAN_BASEBALL_SPRING_ID)
    varsity_schedule = parse_schedule_page_props(
        load_schedule_page_props(f"{CENTENNIAL}/baseball-schedule-26-27.json")
    )
    assert varsity_schedule is not None
    fall_schedule = replace(varsity_schedule, team_season=fall)

    fall_term = TermSnapshot(
        team_season=fall,
        schedule=fall_schedule,
        status=TermRefreshStatus.REFRESHED,
        error_type=None,
        error_message=None,
        last_success_at=datetime(2026, 9, 2, 12, 0, 0),
    )
    spring_error_term = TermSnapshot(
        team_season=spring,
        schedule=None,
        status=TermRefreshStatus.ERROR,
        error_type="ContestSchemaError",
        error_message="simulated schedule failure",
        last_success_at=None,
    )
    program = _program(
        sport="Baseball",
        gender="Boys",
        level="Freshman",
        resolution_status=ProgramResolutionStatus.RESOLVED,
        terms=(spring_error_term, fall_term),
    )
    payload = _payload_for_program(program)

    assert len(payload["terms"]) == 2
    fall_payload = payload["terms"][0]
    spring_payload = payload["terms"][1]
    assert fall_payload["season"] == "Fall"
    assert fall_payload["year"] == "26-27"
    assert fall_payload["status"] == "refreshed"
    assert len(fall_payload["games"]) == 30
    assert spring_payload["season"] == "Spring"
    assert spring_payload["year"] == "26-27"
    assert spring_payload["status"] == "error"
    assert spring_payload["games"] == []


def test_games_are_chronological_by_provider_naive_date() -> None:
    term = _term_from_schedule(f"{CENTENNIAL}/schedule-26-27.json")
    program = _program(
        sport="Football",
        gender="Boys",
        level="Varsity",
        resolution_status=ProgramResolutionStatus.RESOLVED,
        terms=(term,),
    )
    payload = _payload_for_program(program)
    dates = [game["date"] for game in payload["terms"][0]["games"]]
    assert dates == sorted(dates)
