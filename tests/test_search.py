import pytest

from custom_components.maxpreps.exceptions import SearchSchemaError
from custom_components.maxpreps.models import School
from custom_components.maxpreps.parsing.search import parse_search_page_props
from tests.helpers.fixtures import load_search_page_props

CENTENNIAL = "centennial"
PIKE_COUNTY = "pike-county"
BAINBRIDGE = "bainbridge"
ST_EDWARD = "st-edward"

CENTENNIAL_ROSWELL_ID = "52dea55b-3988-4979-b5fd-20376058997f"
CENTENNIAL_ROSWELL_URL = "https://www.maxpreps.com/ga/roswell/centennial-knights/"
BAINBRIDGE_GA_ID = "cc2897b8-106d-45b3-a9cf-5e2aca708668"
BAINBRIDGE_GA_URL = "https://www.maxpreps.com/ga/bainbridge/bainbridge-bearcats/"
PIKE_COUNTY_GA_ID = "84dd878e-671b-40d4-83de-e73ab301f92e"
PIKE_COUNTY_GA_URL = "https://www.maxpreps.com/ga/zebulon/pike-county-pirates/"
ST_EDWARD_OH_ID = "2f510683-5829-4d1e-9a93-703a82f12a58"
ST_EDWARD_OH_URL = "https://www.maxpreps.com/oh/lakewood/st-edward-eagles/"


def _find_school(schools: list[School], school_id: str) -> School:
    for school in schools:
        if school.school_id == school_id:
            return school
    raise AssertionError(f"school_id {school_id!r} not found")


def test_parse_centennial_fixture_raises_on_blank_city():
    page_props = load_search_page_props(f"{CENTENNIAL}/search-centennial.json")
    with pytest.raises(SearchSchemaError, match=r"initialSchoolResults\[28\] missing required field 'city'"):
        parse_search_page_props(page_props)


def test_parse_centennial_roswell_row():
    page_props = load_search_page_props(f"{CENTENNIAL}/search-centennial.json")
    roswell_row = next(
        row
        for row in page_props["initialSchoolResults"]
        if row["schoolId"] == CENTENNIAL_ROSWELL_ID
    )
    schools = parse_search_page_props({"initialSchoolResults": [roswell_row]})

    assert len(schools) == 1
    target = schools[0]
    assert target.canonical_url == CENTENNIAL_ROSWELL_URL
    assert target.name == "Centennial"
    assert target.city == "Roswell"
    assert target.state == "GA"
    assert target.mascot == "Knights"
    assert target.zip == "30076-3417"
    assert target.mascot_url is not None


def test_parse_bainbridge_fixture():
    page_props = load_search_page_props(f"{BAINBRIDGE}/search-bainbridge.json")
    schools = parse_search_page_props(page_props)

    assert len(schools) == 3
    target = _find_school(schools, BAINBRIDGE_GA_ID)
    assert target.canonical_url == BAINBRIDGE_GA_URL
    assert target.name == "Bainbridge"
    assert target.city == "Bainbridge"
    assert target.state == "GA"
    assert target.mascot == "Bearcats"


def test_parse_pike_county_fixture():
    page_props = load_search_page_props(f"{PIKE_COUNTY}/search-pike-county.json")
    schools = parse_search_page_props(page_props)

    assert len(schools) == 3
    target = _find_school(schools, PIKE_COUNTY_GA_ID)
    assert target.canonical_url == PIKE_COUNTY_GA_URL
    assert target.name == "Pike County"
    assert target.city == "Zebulon"
    assert target.state == "GA"
    assert target.mascot == "Pirates"


def test_parse_st_edward_fixture():
    page_props = load_search_page_props(f"{ST_EDWARD}/search-st-edward.json")
    schools = parse_search_page_props(page_props)

    assert len(schools) == len(page_props["initialSchoolResults"])
    target = _find_school(schools, ST_EDWARD_OH_ID)
    assert target.canonical_url == ST_EDWARD_OH_URL
    assert target.name == "St. Edward"
    assert target.city == "Lakewood"
    assert target.state == "OH"
    assert target.mascot == "Eagles"


def test_empty_results_null():
    assert parse_search_page_props({"initialSchoolResults": None}) == []


def test_empty_results_empty_list():
    assert parse_search_page_props({"initialSchoolResults": []}) == []


def test_missing_initial_school_results_key():
    assert parse_search_page_props({"query": "centennial"}) == []


def test_career_results_are_ignored():
    page_props = {
        "initialSchoolResults": [
            {
                "schoolId": CENTENNIAL_ROSWELL_ID,
                "canonicalUrl": CENTENNIAL_ROSWELL_URL,
                "name": "Centennial",
                "city": "Roswell",
                "state": "GA",
            }
        ],
        "initialCareerResults": [
            {
                "careerId": "athlete-uuid",
                "name": "Example Athlete",
                "schoolName": "Centennial",
            }
        ],
    }
    schools = parse_search_page_props(page_props)

    assert len(schools) == 1
    assert schools[0].school_id == CENTENNIAL_ROSWELL_ID
    assert all(not isinstance(school, str) for school in schools)
    assert all(school.name != "Example Athlete" for school in schools)


def test_malformed_row_missing_required_field_raises():
    page_props = {
        "initialSchoolResults": [
            {
                "schoolId": CENTENNIAL_ROSWELL_ID,
                "canonicalUrl": CENTENNIAL_ROSWELL_URL,
                "name": "Centennial",
                "city": "Roswell",
                "state": "GA",
            },
            {
                "schoolId": "bad-row-uuid",
                "canonicalUrl": "https://www.maxpreps.com/example/",
                "name": "Incomplete",
                "city": "Roswell",
            },
        ]
    }
    with pytest.raises(SearchSchemaError, match=r"initialSchoolResults\[1\] missing required field 'state'"):
        parse_search_page_props(page_props)


def test_malformed_initial_school_results_type():
    with pytest.raises(SearchSchemaError, match="must be a list"):
        parse_search_page_props({"initialSchoolResults": "not-a-list"})
