import pytest

from custom_components.maxpreps.exceptions import MalformedNextDataError, NextDataNotFoundError
from custom_components.maxpreps.parsing.next_data import extract_page_props
from tests.helpers.fixtures import (
    load_schedule_page_props,
    load_search_page_props,
    load_sport_seasons,
    wrap_page_props_in_html,
)

CENTENNIAL = "centennial"
PIKE_COUNTY = "pike-county"
BAINBRIDGE = "bainbridge"
ST_EDWARD = "st-edward"


def test_extract_page_props_round_trip_from_schedule_fixture():
    page_props = load_schedule_page_props(f"{CENTENNIAL}/schedule-26-27.json")
    assert page_props is not None
    html = wrap_page_props_in_html(page_props)
    extracted = extract_page_props(html)
    assert extracted["canonicalUrl"] == page_props["canonicalUrl"]
    assert len(extracted["contests"]) == len(page_props["contests"])


def test_extract_page_props_round_trip_from_small_dict():
    page_props = {"query": "centennial", "initialSchoolResults": []}
    extracted = extract_page_props(wrap_page_props_in_html(page_props))
    assert extracted == page_props


def test_extract_page_props_missing_next_data():
    with pytest.raises(NextDataNotFoundError) as exc_info:
        extract_page_props("<html><body>No Next.js payload here.</body></html>")
    message = str(exc_info.value).lower()
    assert "aspx" not in message
    assert "legacy" not in message


def test_extract_page_props_missing_page_props_key():
    html = (
        '<html><body><script id="__NEXT_DATA__" type="application/json">'
        '{"props": {}}</script></body></html>'
    )
    with pytest.raises(NextDataNotFoundError) as exc_info:
        extract_page_props(html)
    assert "aspx" not in str(exc_info.value).lower()


def test_extract_page_props_malformed_json():
    html = (
        '<html><body><script id="__NEXT_DATA__" type="application/json">'
        "{not valid json</script></body></html>"
    )
    with pytest.raises(MalformedNextDataError):
        extract_page_props(html)


def test_tennis_fixture_does_not_manufacture_page_props():
    page_props = load_schedule_page_props(f"{CENTENNIAL}/tennis-schedule-26-27.json")
    assert page_props is None


def test_track_fixture_does_not_manufacture_page_props():
    page_props = load_schedule_page_props(
        f"{CENTENNIAL}/track-field-girls-schedule-26-27.json"
    )
    assert page_props is None


def test_load_search_page_props_centennial():
    page_props = load_search_page_props(f"{CENTENNIAL}/search-centennial.json")
    assert page_props["query"] == "centennial"
    assert len(page_props["initialSchoolResults"]) > 0


def test_load_sport_seasons_centennial_envelope():
    seasons = load_sport_seasons(f"{CENTENNIAL}/sport-seasons-26-27.json")
    assert any(row["sport"] == "Baseball" for row in seasons)


def test_load_sport_seasons_pike_county_envelope():
    seasons = load_sport_seasons(f"{PIKE_COUNTY}/sport-seasons-26-27.json")
    assert any(row["year"] == "11-12" for row in seasons)


def test_load_sport_seasons_bainbridge_envelope():
    seasons = load_sport_seasons(f"{BAINBRIDGE}/sport-seasons-26-27.json")
    assert all(row["year"] == "26-27" for row in seasons)


def test_load_sport_seasons_st_edward_envelope():
    seasons = load_sport_seasons(f"{ST_EDWARD}/sport-seasons-26-27.json")
    assert len(seasons) > 0


def test_load_schedule_page_props_football():
    page_props = load_schedule_page_props(f"{CENTENNIAL}/schedule-26-27.json")
    assert page_props is not None
    assert "contests" in page_props


def test_load_schedule_page_props_baseball():
    page_props = load_schedule_page_props(f"{CENTENNIAL}/baseball-schedule-26-27.json")
    assert page_props is not None
    assert len(page_props["contests"]) == 30
