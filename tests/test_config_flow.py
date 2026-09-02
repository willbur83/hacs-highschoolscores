"""Config flow tests using fixture transport only."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest

pytest.importorskip("homeassistant")

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType, InvalidData

from custom_components.maxpreps.async_client import AsyncMaxPrepsClient
from custom_components.maxpreps.const import (
    CONF_CANONICAL_URL,
    CONF_GENDER,
    CONF_LEVEL,
    CONF_NAME,
    CONF_SCHOOL_ID,
    CONF_SPORT,
    CONF_SUBSCRIPTIONS,
    DOMAIN,
)
from custom_components.maxpreps.urls import build_search_url
from pytest_homeassistant_custom_component.common import MockConfigEntry
from tests.helpers.async_fixture_transport import AsyncFixtureTransport
from tests.test_search import (
    CENTENNIAL_ROSWELL_ID,
    CENTENNIAL_ROSWELL_URL,
    PIKE_COUNTY_GA_ID,
    PIKE_COUNTY_GA_URL,
    ST_EDWARD_OH_ID,
)

EXCLUDED_SPORTS = {
    "Soccer",
    "Lacrosse",
    "Flag Football",
    "Softball",
    "Tennis",
    "Golf",
    "Track",
}
ALLOWLISTED_SPORTS = {"Football", "Baseball", "Basketball", "Volleyball"}
WELLAND_ID = "e283add5-4dde-4aa5-876b-65e2fc628a43"
CENTENNIAL_SEARCH_URL = build_search_url("Centennial")
CENTENNIAL_HIGH_SCHOOL_SEARCH_URL = build_search_url("Centennial High School")
SAINT_EDWARD_SEARCH_URL = build_search_url("Saint Edward")
ST_EDWARD_SEARCH_URL = build_search_url("St. Edward")
FOOTBALL_SUBSCRIPTION_KEY = "\x1e".join(("Football", "Boys", "Varsity"))
FRESHMAN_BASEBALL_SUBSCRIPTION_KEY = "\x1e".join(("Baseball", "Boys", "Freshman"))
VARSITY_BASEBALL_SUBSCRIPTION_KEY = "\x1e".join(("Baseball", "Boys", "Varsity"))


def _sport_from_subscription_key(key: str) -> str:
    return key.split("\x1e", maxsplit=1)[0]


def _get_selector(result: dict, field_name: str):
    """Return the HA selector object for ``field_name`` from a flow form result."""
    schema = result["data_schema"].schema
    for marker, selector_obj in schema.items():
        if marker.schema == field_name:
            return selector_obj
    raise KeyError(f"selector field {field_name!r} not found in flow schema")


def _selector_options(result: dict, field_name: str) -> dict[str, str]:
    selector_obj = _get_selector(result, field_name)
    return {
        option["value"]: option["label"]
        for option in selector_obj.config["options"]
    }


FROZEN_APPLICABLE_DATE = date(2026, 9, 2)
FUTURE_APPLICABLE_DATE = date(2027, 7, 1)


@pytest.fixture
def fixture_client():
    """Inject AsyncFixtureTransport-backed client into the config flow."""
    transport = AsyncFixtureTransport()
    client = AsyncMaxPrepsClient(transport)

    with (
        patch(
            "custom_components.maxpreps.school_year.homeassistant_local_date",
            return_value=FROZEN_APPLICABLE_DATE,
        ),
        patch(
            "custom_components.maxpreps.config_flow.client_factory.create_async_client",
            return_value=client,
        ),
    ):
        yield client, transport


async def _init_user(hass, enable_custom_integrations):
    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )


@pytest.mark.asyncio
async def test_empty_query_errors_without_fetch(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """Empty search query shows a field error and does not fetch."""
    _, transport = fixture_client

    result = await _init_user(hass, enable_custom_integrations)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"query": "   "}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"query": "required"}
    assert transport.requested_urls == []


@pytest.mark.asyncio
async def test_no_results_stays_on_search_form(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """Qualified empty search shows no_results and does not open the school picker."""
    _, transport = fixture_client

    result = await _init_user(hass, enable_custom_integrations)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"query": "Centennial High School"}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "no_results"}
    assert transport.requested_urls == [CENTENNIAL_HIGH_SCHOOL_SEARCH_URL]


@pytest.mark.asyncio
async def test_centennial_search_shows_roswell_picker_label(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """Centennial search lists Roswell with location and mascot in the picker."""
    _, transport = fixture_client

    result = await _init_user(hass, enable_custom_integrations)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"query": "Centennial"}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "school"
    assert transport.requested_urls == [CENTENNIAL_SEARCH_URL]

    options = _selector_options(result, "school")

    assert CENTENNIAL_ROSWELL_ID in options
    assert options[CENTENNIAL_ROSWELL_ID] == "Centennial | Roswell, GA · Knights"


@pytest.mark.asyncio
async def test_location_degraded_search_row_remains_listed(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """School rows without city/state stay pickable with degraded location text."""
    _, transport = fixture_client

    result = await _init_user(hass, enable_custom_integrations)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"query": "Centennial"}
    )

    options = _selector_options(result, "school")

    assert WELLAND_ID in options
    assert "Location unavailable" in options[WELLAND_ID]


@pytest.mark.asyncio
async def test_centennial_subscriptions_are_allowlisted_only(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """After picking Roswell Centennial, only allowlisted current-cohort sports appear."""
    _, transport = fixture_client

    result = await _init_user(hass, enable_custom_integrations)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"query": "Centennial"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"school": CENTENNIAL_ROSWELL_ID}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "subscriptions"

    options = _selector_options(result, "subscriptions")
    labels = list(options.values())

    assert ALLOWLISTED_SPORTS.issubset(
        {_sport_from_subscription_key(key) for key in options}
    )
    for key in options:
        sport = _sport_from_subscription_key(key)
        assert sport in ALLOWLISTED_SPORTS
        assert sport not in EXCLUDED_SPORTS

    assert "Tennis" not in labels
    assert "Soccer" not in labels
    assert "Lacrosse" not in labels
    assert "Flag Football" not in labels
    assert "Softball" not in labels


@pytest.mark.asyncio
async def test_create_entry_stores_identity_and_subscriptions(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """Completed flow stores school data, subscription options, and school_id unique_id."""
    _, transport = fixture_client

    result = await _init_user(hass, enable_custom_integrations)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"query": "Centennial"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"school": CENTENNIAL_ROSWELL_ID}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"subscriptions": [FOOTBALL_SUBSCRIPTION_KEY]},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    entry = result["result"]
    assert entry.unique_id == CENTENNIAL_ROSWELL_ID
    assert entry.data[CONF_SCHOOL_ID] == CENTENNIAL_ROSWELL_ID
    assert entry.data[CONF_CANONICAL_URL] == CENTENNIAL_ROSWELL_URL
    assert entry.data[CONF_NAME] == "Centennial"
    assert entry.options[CONF_SUBSCRIPTIONS] == [
        {
            CONF_SPORT: "Football",
            CONF_GENDER: "Boys",
            CONF_LEVEL: "Varsity",
        }
    ]
    assert "sport_season_id" not in entry.options[CONF_SUBSCRIPTIONS][0]


@pytest.mark.asyncio
async def test_duplicate_school_aborts_without_school_home_fetch(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """Duplicate school_id aborts immediately after selection without school-home fetch."""
    _, transport = fixture_client

    existing = MockConfigEntry(
        domain=DOMAIN,
        unique_id=CENTENNIAL_ROSWELL_ID,
        data={CONF_SCHOOL_ID: CENTENNIAL_ROSWELL_ID},
    )
    existing.add_to_hass(hass)

    result = await _init_user(hass, enable_custom_integrations)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"query": "Centennial"}
    )

    school_home_urls_before = [
        url for url in transport.requested_urls if url == CENTENNIAL_ROSWELL_URL
    ]
    assert school_home_urls_before == []

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"school": CENTENNIAL_ROSWELL_ID}
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert CENTENNIAL_ROSWELL_URL not in transport.requested_urls


@pytest.mark.asyncio
async def test_invalid_school_selection_rejected_without_fetch(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """Stale school selector values are rejected and do not trigger a school-home fetch."""
    _, transport = fixture_client

    result = await _init_user(hass, enable_custom_integrations)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"query": "Centennial"}
    )
    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {"school": "not-in-search-results"}
        )

    assert CENTENNIAL_ROSWELL_URL not in transport.requested_urls


@pytest.mark.asyncio
async def test_saint_edward_search_uses_client_retry(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """Saint Edward search relies on client Saint retry, not config-flow logic."""
    _, transport = fixture_client

    result = await _init_user(hass, enable_custom_integrations)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"query": "Saint Edward"}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "school"
    assert transport.requested_urls == [SAINT_EDWARD_SEARCH_URL, ST_EDWARD_SEARCH_URL]

    options = _selector_options(result, "school")
    assert ST_EDWARD_OH_ID in options
    assert options[ST_EDWARD_OH_ID].startswith("St. Edward | Lakewood, OH")


@pytest.mark.asyncio
async def test_pike_county_excludes_historical_and_non_allowlisted(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """Pike County shows current-cohort allowlisted sports only (no 11-12 leftovers)."""
    _, transport = fixture_client

    result = await _init_user(hass, enable_custom_integrations)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"query": "Pike County"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"school": PIKE_COUNTY_GA_ID}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "subscriptions"
    assert PIKE_COUNTY_GA_URL in transport.requested_urls

    options = _selector_options(result, "subscriptions")
    labels = list(options.values())

    for key in options:
        sport = _sport_from_subscription_key(key)
        assert sport in ALLOWLISTED_SPORTS

    assert "11-12" not in labels
    assert not any(
        excluded in label for label in labels for excluded in EXCLUDED_SPORTS
    )


@pytest.mark.asyncio
async def test_zero_sports_selected_stays_on_subscriptions_form(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """Subscriptions step requires at least one sport."""
    _, transport = fixture_client

    result = await _init_user(hass, enable_custom_integrations)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"query": "Centennial"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"school": CENTENNIAL_ROSWELL_ID}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"subscriptions": []}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "subscriptions"
    assert result["errors"] == {"subscriptions": "required"}


@pytest.mark.asyncio
async def test_centennial_subscriptions_include_gender_distinct_basketball(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """Boys and girls basketball are distinct subscription options."""
    _, transport = fixture_client

    result = await _init_user(hass, enable_custom_integrations)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"query": "Centennial"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"school": CENTENNIAL_ROSWELL_ID}
    )

    labels = list(_selector_options(result, "subscriptions").values())

    assert any(label.startswith("Boys Varsity Basketball") for label in labels)
    assert any(label.startswith("Girls Varsity Basketball") for label in labels)


@pytest.mark.asyncio
async def test_duplicate_subscription_key_collapses_to_one_option(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """Spring/Fall rows for the same program collapse to one subscription option."""
    _, transport = fixture_client

    result = await _init_user(hass, enable_custom_integrations)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"query": "Centennial"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"school": CENTENNIAL_ROSWELL_ID}
    )

    options = _selector_options(result, "subscriptions")
    labels = list(options.values())
    values = list(options.keys())

    freshman_baseball_labels = [
        label for label in labels if label.startswith("Boys Freshman Baseball")
    ]
    assert freshman_baseball_labels == ["Boys Freshman Baseball (Fall, Spring 26-27)"]
    assert FRESHMAN_BASEBALL_SUBSCRIPTION_KEY in values
    assert len(labels) == 16


@pytest.mark.asyncio
async def test_varsity_football_label_includes_term_and_year(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """Varsity football option label shows the fixture row's season and school year."""
    _, _ = fixture_client

    result = await _init_user(hass, enable_custom_integrations)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"query": "Centennial"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"school": CENTENNIAL_ROSWELL_ID}
    )

    options = _selector_options(result, "subscriptions")
    assert options[FOOTBALL_SUBSCRIPTION_KEY] == "Boys Varsity Football (Fall 26-27)"


@pytest.mark.asyncio
async def test_varsity_baseball_label_includes_term_and_year(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """Varsity baseball option label shows the fixture row's season and school year."""
    _, _ = fixture_client

    result = await _init_user(hass, enable_custom_integrations)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"query": "Centennial"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"school": CENTENNIAL_ROSWELL_ID}
    )

    options = _selector_options(result, "subscriptions")
    assert options[VARSITY_BASEBALL_SUBSCRIPTION_KEY] == "Boys Varsity Baseball (Spring 26-27)"


@pytest.mark.asyncio
async def test_freshman_baseball_subscription_stores_program_identity_only(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """Selecting multi-term freshman baseball persists sport/gender/level only."""
    _, _ = fixture_client

    result = await _init_user(hass, enable_custom_integrations)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"query": "Centennial"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"school": CENTENNIAL_ROSWELL_ID}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"subscriptions": [FRESHMAN_BASEBALL_SUBSCRIPTION_KEY]},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    entry = result["result"]
    assert entry.options[CONF_SUBSCRIPTIONS] == [
        {
            CONF_SPORT: "Baseball",
            CONF_GENDER: "Boys",
            CONF_LEVEL: "Freshman",
        }
    ]


@pytest.mark.asyncio
async def test_applicable_year_without_provider_rows_aborts_no_supported_sports(
    hass, enable_custom_integrations
) -> None:
    """When the applicable year has no provider rows, abort no_supported_sports."""
    transport = AsyncFixtureTransport()
    client = AsyncMaxPrepsClient(transport)

    with (
        patch(
            "custom_components.maxpreps.school_year.homeassistant_local_date",
            return_value=FUTURE_APPLICABLE_DATE,
        ),
        patch(
            "custom_components.maxpreps.config_flow.client_factory.create_async_client",
            return_value=client,
        ),
    ):
        result = await _init_user(hass, enable_custom_integrations)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"query": "Centennial"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"school": CENTENNIAL_ROSWELL_ID}
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_supported_sports"
