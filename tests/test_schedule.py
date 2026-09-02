import copy

import pytest

from custom_components.maxpreps.exceptions import ContestSchemaError
from custom_components.maxpreps.models import GameStatus
from custom_components.maxpreps.parsing.contests import CONTEST_ROW_ARITY
from custom_components.maxpreps.parsing.schedule import parse_schedule_page_props
from tests.helpers.fixtures import load_schedule_page_props
from tests.test_search import (
    BAINBRIDGE,
    BAINBRIDGE_GA_ID,
    CENTENNIAL,
    CENTENNIAL_ROSWELL_ID,
    PIKE_COUNTY,
    PIKE_COUNTY_GA_ID,
    ST_EDWARD,
    ST_EDWARD_OH_ID,
)

FOOTBALL_SPORT_SEASON_ID = "2286cd80-c46d-4739-8dd1-92a67ca8daa7"
FOOTBALL_ALL_SEASON_ID = "22e2b335-334e-4d4d-9f67-a0f716bb1ccd"
BASEBALL_SPORT_SEASON_ID = "0e872276-ae3c-4868-8b66-cb53e9727cfb"
RIVERWOOD_CONTEST_ID = "e1ab4e49-c66c-4b86-becf-c2fe9e91a7c6"

SCHEDULE_FIXTURES = [
    f"{CENTENNIAL}/schedule-26-27.json",
    f"{CENTENNIAL}/baseball-schedule-26-27.json",
    f"{ST_EDWARD}/schedule-26-27.json",
    f"{CENTENNIAL}/volleyball-schedule-26-27.json",
    f"{CENTENNIAL}/basketball-girls-schedule-26-27.json",
    f"{BAINBRIDGE}/schedule-26-27.json",
    f"{PIKE_COUNTY}/schedule-26-27.json",
]


def _non_deleted_contest_count(page_props: dict) -> int:
    return sum(1 for row in page_props["contests"] if row[15] != 1)


def test_centennial_football_schedule():
    page_props = load_schedule_page_props(f"{CENTENNIAL}/schedule-26-27.json")
    schedule = parse_schedule_page_props(page_props)

    assert len(page_props["contests"]) == 11
    assert len(schedule.games) == 10
    assert all(game.status is not GameStatus.DELETED for game in schedule.games)
    assert RIVERWOOD_CONTEST_ID not in {game.id for game in schedule.games}

    assert schedule.team_season.school_id == CENTENNIAL_ROSWELL_ID
    assert schedule.team_season.sport_season_id == FOOTBALL_SPORT_SEASON_ID
    assert schedule.team_season.all_season_id == FOOTBALL_ALL_SEASON_ID
    assert schedule.team_season.sport == "Football"
    assert schedule.team_season.gender == "Boys"
    assert schedule.team_season.level == "Varsity"
    assert schedule.team_season.year == "26-27"
    assert schedule.team_season.season == "Fall"
    assert schedule.team_season.canonical_url.endswith("/centennial-knights/football/")

    assert schedule.team_record == "2-0"
    assert schedule.team_logo == page_props["teamContext"]["data"]["schoolMascotUrl"]


def test_centennial_baseball_schedule_matches_non_deleted_contests():
    page_props = load_schedule_page_props(f"{CENTENNIAL}/baseball-schedule-26-27.json")
    schedule = parse_schedule_page_props(page_props)

    assert len(schedule.games) == _non_deleted_contest_count(page_props) == 30
    assert schedule.team_season.sport_season_id == BASEBALL_SPORT_SEASON_ID
    assert schedule.team_season.sport == "Baseball"
    assert schedule.team_record is None


def test_st_edward_schedule_without_page_props_query():
    page_props = load_schedule_page_props(f"{ST_EDWARD}/schedule-26-27.json")
    assert page_props.get("query") is None

    schedule = parse_schedule_page_props(page_props)

    assert schedule.team_season.school_id == ST_EDWARD_OH_ID
    assert len(schedule.games) == _non_deleted_contest_count(page_props)
    assert schedule.team_record == "2-0"


def test_volleyball_schedule_regression():
    page_props = load_schedule_page_props(f"{CENTENNIAL}/volleyball-schedule-26-27.json")
    schedule = parse_schedule_page_props(page_props)

    assert len(schedule.games) == _non_deleted_contest_count(page_props) == 30
    assert schedule.team_record == "3-14"


def test_basketball_girls_schedule():
    page_props = load_schedule_page_props(
        f"{CENTENNIAL}/basketball-girls-schedule-26-27.json"
    )
    schedule = parse_schedule_page_props(page_props)

    assert len(schedule.games) == 6
    assert schedule.team_season.sport == "Basketball"
    assert schedule.team_season.gender == "Girls"
    assert schedule.team_record is None


@pytest.mark.parametrize("fixture_path", SCHEDULE_FIXTURES)
def test_schedule_identity_from_team_context_not_contests(fixture_path: str):
    page_props = load_schedule_page_props(fixture_path)
    schedule = parse_schedule_page_props(page_props)

    data = page_props["teamContext"]["data"]
    assert schedule.team_season.school_id == data["teamId"]
    assert schedule.team_season.sport_season_id == data["sportSeasonId"]

    for game in schedule.games:
        assert game.team_name


def test_swapped_participant_order_still_orients_by_school_id():
    page_props = load_schedule_page_props(f"{CENTENNIAL}/schedule-26-27.json")
    row = copy.deepcopy(page_props["contests"][2])
    row[0] = [row[0][1], row[0][0]]

    modified = copy.deepcopy(page_props)
    modified["contests"] = [row]
    modified.pop("featuredGameData", None)

    schedule = parse_schedule_page_props(modified)
    game = schedule.games[0]

    assert game.id == "6f7a550c-040a-4f1c-824e-3d0d3b873cef"
    assert game.team_name == "Centennial"
    assert game.opponent_name == "Johns Creek"
    assert game.home_away.value == "home"
    assert game.team_score == 54
    assert game.opponent_score == 18


def test_empty_contests_returns_empty_games():
    page_props = load_schedule_page_props(f"{CENTENNIAL}/schedule-26-27.json")
    page_props = copy.deepcopy(page_props)
    page_props["contests"] = []
    page_props.pop("featuredGameData", None)

    schedule = parse_schedule_page_props(page_props)

    assert schedule.games == []
    assert schedule.team_season.school_id == CENTENNIAL_ROSWELL_ID


def test_missing_team_context_raises():
    page_props = load_schedule_page_props(f"{CENTENNIAL}/schedule-26-27.json")
    page_props = copy.deepcopy(page_props)
    del page_props["teamContext"]

    with pytest.raises(ContestSchemaError, match="teamContext must be an object"):
        parse_schedule_page_props(page_props)


def test_missing_contests_raises():
    page_props = load_schedule_page_props(f"{CENTENNIAL}/schedule-26-27.json")
    page_props = copy.deepcopy(page_props)
    del page_props["contests"]

    with pytest.raises(ContestSchemaError, match="contests must be a list"):
        parse_schedule_page_props(page_props)


def test_bainbridge_and_pike_county_schedules_decode():
    for fixture_path, school_id in (
        (f"{BAINBRIDGE}/schedule-26-27.json", BAINBRIDGE_GA_ID),
        (f"{PIKE_COUNTY}/schedule-26-27.json", PIKE_COUNTY_GA_ID),
    ):
        page_props = load_schedule_page_props(fixture_path)
        schedule = parse_schedule_page_props(page_props)

        assert schedule.team_season.school_id == school_id
        assert len(schedule.games) == _non_deleted_contest_count(page_props)
        assert schedule.team_record is not None


def test_wrong_contests_arity_raises_through_adapter():
    page_props = copy.deepcopy(
        load_schedule_page_props(f"{CENTENNIAL}/schedule-26-27.json")
    )
    page_props["contests"][0] = page_props["contests"][0][: CONTEST_ROW_ARITY - 1]

    with pytest.raises(
        ContestSchemaError,
        match=rf"contests\[0\] must have length {CONTEST_ROW_ARITY}",
    ):
        parse_schedule_page_props(page_props)


@pytest.mark.parametrize(
    ("fixture_path", "expected_game_count"),
    [
        (f"{CENTENNIAL}/schedule-26-27.json", 10),
        (f"{CENTENNIAL}/baseball-schedule-26-27.json", 30),
    ],
)
def test_full_schedule_decodes_without_featured(fixture_path: str, expected_game_count: int):
    page_props = copy.deepcopy(load_schedule_page_props(fixture_path))
    page_props.pop("featuredGameData", None)

    schedule = parse_schedule_page_props(page_props)

    assert len(schedule.games) == expected_game_count
    assert all(game.status is not GameStatus.DELETED for game in schedule.games)


def test_contradictory_featured_raises_through_adapter():
    page_props = copy.deepcopy(
        load_schedule_page_props(f"{CENTENNIAL}/schedule-26-27.json")
    )
    page_props["featuredGameData"]["date"] = "2099-01-01T00:00:00"

    with pytest.raises(
        ContestSchemaError,
        match=r"featuredGameData 'date' does not match contests\[\]\[11\]",
    ):
        parse_schedule_page_props(page_props)


def test_unknown_contest_state_on_one_row_preserves_other_games():
    page_props = copy.deepcopy(
        load_schedule_page_props(f"{CENTENNIAL}/schedule-26-27.json")
    )
    unknown_row = copy.deepcopy(page_props["contests"][2])
    unknown_row[15] = 99
    unknown_row[28] = "Unexpected contest state."
    page_props["contests"][2] = unknown_row

    schedule = parse_schedule_page_props(page_props)

    assert len(schedule.games) == 10
    unknown_game = next(game for game in schedule.games if game.id == unknown_row[1])
    assert unknown_game.status == GameStatus.UNKNOWN
    assert unknown_game.status_message == "Unexpected contest state."

    scheduled_game = next(
        game for game in schedule.games if game.id == page_props["contests"][3][1]
    )
    assert scheduled_game.status == GameStatus.SCHEDULED
    assert RIVERWOOD_CONTEST_ID not in {game.id for game in schedule.games}
