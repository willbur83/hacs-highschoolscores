import copy
from datetime import datetime

import pytest

from custom_components.maxpreps.exceptions import ContestSchemaError
from custom_components.maxpreps.models import GameStatus, HomeAway
from custom_components.maxpreps.parsing.contests import (
    CONTEST_ROW_ARITY,
    check_featured_game_consistency,
    decode_contest_row,
    validate_contests_shape,
)
from tests.helpers.fixtures import load_schedule_page_props
from tests.test_search import (
    BAINBRIDGE,
    CENTENNIAL,
    CENTENNIAL_ROSWELL_ID,
    PIKE_COUNTY,
    ST_EDWARD,
)

SCHEDULE_FIXTURES_WITH_ROWS = [
    f"{CENTENNIAL}/schedule-26-27.json",
    f"{BAINBRIDGE}/schedule-26-27.json",
    f"{PIKE_COUNTY}/schedule-26-27.json",
    f"{ST_EDWARD}/schedule-26-27.json",
    f"{CENTENNIAL}/baseball-schedule-26-27.json",
    f"{CENTENNIAL}/volleyball-schedule-26-27.json",
    f"{CENTENNIAL}/basketball-girls-schedule-26-27.json",
]


def _sample_contest_row() -> list:
    page_props = load_schedule_page_props(f"{CENTENNIAL}/schedule-26-27.json")
    return copy.deepcopy(page_props["contests"][3])


@pytest.mark.parametrize("fixture_path", SCHEDULE_FIXTURES_WITH_ROWS)
def test_real_fixture_contests_shape_and_featured_consistency(fixture_path: str):
    page_props = load_schedule_page_props(fixture_path)
    contests = page_props["contests"]
    assert len(contests) >= 1

    validate_contests_shape(contests)

    featured = page_props.get("featuredGameData")
    if featured is not None:
        check_featured_game_consistency(contests, featured)


def test_valid_contests_without_featured_passes_shape_only():
    contests = [_sample_contest_row()]
    validate_contests_shape(contests)


def test_empty_contests_list_is_valid_shape():
    validate_contests_shape([])


def test_empty_contests_with_featured_fails_consistency_check():
    page_props = load_schedule_page_props(f"{CENTENNIAL}/schedule-26-27.json")
    featured = page_props["featuredGameData"]

    with pytest.raises(
        ContestSchemaError,
        match=r"featuredGameData contestId .+ not found in contests",
    ):
        check_featured_game_consistency([], featured)


def test_wrong_row_arity_raises():
    row = _sample_contest_row()[: CONTEST_ROW_ARITY - 1]
    with pytest.raises(
        ContestSchemaError,
        match=rf"contests\[0\] must have length {CONTEST_ROW_ARITY}, got {CONTEST_ROW_ARITY - 1}",
    ):
        validate_contests_shape([row])


def test_wrong_participant_width_raises():
    row = _sample_contest_row()
    row[0][0] = row[0][0][:31]
    with pytest.raises(
        ContestSchemaError,
        match=r"contests\[0\]\[0\]\[0\] must have length 32, got 31",
    ):
        validate_contests_shape([row])


def test_featured_contest_id_not_in_contests_raises():
    contests = [_sample_contest_row()]
    featured = {
        "contestId": "00000000-0000-0000-0000-000000000000",
        "location": contests[0][5],
        "date": contests[0][11],
        "contestState": contests[0][15],
        "canonicalUrl": contests[0][18],
    }
    with pytest.raises(
        ContestSchemaError,
        match=r"featuredGameData contestId '00000000-0000-0000-0000-000000000000' not found",
    ):
        check_featured_game_consistency(contests, featured)


def test_featured_date_mismatch_raises():
    page_props = load_schedule_page_props(f"{CENTENNIAL}/schedule-26-27.json")
    contests = page_props["contests"]
    featured = copy.deepcopy(page_props["featuredGameData"])
    featured["date"] = "2099-01-01T00:00:00"

    with pytest.raises(
        ContestSchemaError,
        match=r"featuredGameData 'date' does not match contests\[\]\[11\]",
    ):
        check_featured_game_consistency(contests, featured)


def _centennial_football_contests() -> list:
    page_props = load_schedule_page_props(f"{CENTENNIAL}/schedule-26-27.json")
    return page_props["contests"]


def test_decode_johns_creek_final_home():
    row = _centennial_football_contests()[2]
    game = decode_contest_row(row, CENTENNIAL_ROSWELL_ID)

    assert game.id == "6f7a550c-040a-4f1c-824e-3d0d3b873cef"
    assert game.date == datetime(2026, 8, 28, 19, 30)
    assert game.date.tzinfo is None
    assert game.status == GameStatus.FINAL
    assert game.team_name == "Centennial"
    assert game.opponent_name == "Johns Creek"
    assert game.opponent_id == "efadaef4-8fb1-469b-b110-218621e68254"
    assert game.home_away == HomeAway.HOME
    assert game.team_score == 54
    assert game.opponent_score == 18
    assert game.result == "W"
    assert game.venue == "Centennial High School"
    assert game.status_message is None


def test_decode_alpharetta_scheduled_home():
    row = _centennial_football_contests()[3]
    game = decode_contest_row(row, CENTENNIAL_ROSWELL_ID)

    assert game.id == "30b79240-4c41-4e25-b850-0052d1221fbd"
    assert game.status == GameStatus.SCHEDULED
    assert game.home_away == HomeAway.HOME
    assert game.team_score is None
    assert game.opponent_score is None
    assert game.result is None
    assert game.status_message == "ContestState is Pregame."


def test_decode_dunwoody_final_neutral():
    row = _centennial_football_contests()[1]
    game = decode_contest_row(row, CENTENNIAL_ROSWELL_ID)

    assert game.id == "3925a0d5-d65a-45b1-bd65-e86d8d021af0"
    assert game.status == GameStatus.FINAL
    assert game.home_away == HomeAway.NEUTRAL
    assert game.team_score == 23
    assert game.opponent_score == 21
    assert game.result == "W"
    assert game.venue == "Blessed Trinity High School"
    assert game.status_message is None


def test_decode_riverwood_deleted_away():
    row = _centennial_football_contests()[0]
    game = decode_contest_row(row, CENTENNIAL_ROSWELL_ID)

    assert game.id == "e1ab4e49-c66c-4b86-becf-c2fe9e91a7c6"
    assert game.status == GameStatus.DELETED
    assert game.home_away == HomeAway.AWAY
    assert game.game_url is None
    assert game.team_score is None
    assert game.opponent_score is None
    assert game.result is None
    assert game.status_message == "ContestState is Deleted."


def test_decode_baseball_row_is_timezone_naive():
    page_props = load_schedule_page_props(f"{CENTENNIAL}/baseball-schedule-26-27.json")
    row = page_props["contests"][0]
    game = decode_contest_row(row, CENTENNIAL_ROSWELL_ID)

    assert game.date.tzinfo is None
    assert game.status == GameStatus.SCHEDULED


def test_decode_unobserved_contest_state_is_unknown_with_message():
    row = copy.deepcopy(_centennial_football_contests()[3])
    row[15] = 99
    row[28] = "Unexpected contest state."

    game = decode_contest_row(row, CENTENNIAL_ROSWELL_ID)

    assert game.status == GameStatus.UNKNOWN
    assert game.status_message == "Unexpected contest state."


def test_decode_contest_state_four_without_has_result_is_unknown():
    row = copy.deepcopy(_centennial_football_contests()[2])
    row[4] = False
    row[28] = "Awaiting result."

    game = decode_contest_row(row, CENTENNIAL_ROSWELL_ID)

    assert game.status == GameStatus.UNKNOWN
    assert game.status_message == "Awaiting result."
    assert game.team_score is None
    assert game.opponent_score is None
    assert game.result is None


def test_decode_timezone_aware_date_raises():
    row = copy.deepcopy(_centennial_football_contests()[3])
    row[11] = "2026-09-04T19:30:00+00:00"

    with pytest.raises(ContestSchemaError, match="timezone-naive"):
        decode_contest_row(row, CENTENNIAL_ROSWELL_ID)


def test_decode_missing_school_raises():
    row = _centennial_football_contests()[2]

    with pytest.raises(ContestSchemaError, match="not found in contests teams"):
        decode_contest_row(row, "00000000-0000-0000-0000-000000000000")


def test_decode_volleyball_tba_opponent_id_is_none():
    page_props = load_schedule_page_props(f"{CENTENNIAL}/volleyball-schedule-26-27.json")
    row = page_props["contests"][14]
    game = decode_contest_row(row, CENTENNIAL_ROSWELL_ID)

    assert game.opponent_id is None
