import copy

import pytest

from custom_components.maxpreps.exceptions import ContestSchemaError
from custom_components.maxpreps.parsing.contests import (
    CONTEST_ROW_ARITY,
    check_featured_game_consistency,
    validate_contests_shape,
)
from tests.helpers.fixtures import load_schedule_page_props
from tests.test_search import (
    BAINBRIDGE,
    CENTENNIAL,
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
