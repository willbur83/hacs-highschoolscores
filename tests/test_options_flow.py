"""Options flow tests using fixture transport only."""

from __future__ import annotations

from unittest.mock import patch

import pytest

pytest.importorskip("homeassistant")

from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

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
from custom_components.maxpreps.coordinator import TermRefreshStatus
from pytest_homeassistant_custom_component.common import MockConfigEntry
from tests.helpers.async_fixture_transport import AsyncFixtureTransport
from tests.helpers.coordinator_test_helpers import FROZEN_APPLICABLE_DATE, centennial_entry
from tests.test_config_flow import (
    ALLOWLISTED_SPORTS,
    EXCLUDED_SPORTS,
    FRESHMAN_BASEBALL_SUBSCRIPTION_KEY,
    FOOTBALL_SUBSCRIPTION_KEY,
    VARSITY_BASEBALL_SUBSCRIPTION_KEY,
    _selector_options,
    _sport_from_subscription_key,
)
from tests.test_coordinator import (
    FRESHMAN_BASEBALL_SPRING_SCHEDULE_URL,
    FRESHMAN_BASEBALL_SUBSCRIPTION,
    FOOTBALL_SUBSCRIPTION,
    UNRESOLVED_SUBSCRIPTION,
    CoordinatorTestTransport,
)
from tests.test_search import CENTENNIAL_ROSWELL_ID, PIKE_COUNTY_GA_ID, PIKE_COUNTY_GA_URL

VARSITY_BASEBALL_SUBSCRIPTION = {
    CONF_SPORT: "Baseball",
    CONF_GENDER: "Boys",
    CONF_LEVEL: "Varsity",
}


@pytest.fixture
def fixture_client():
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
        patch(
            "custom_components.maxpreps.client_factory.create_async_client",
            return_value=client,
        ),
    ):
        yield client, transport


def _sensor_entities(hass, entry):
    registry = er.async_get(hass)
    return [
        entity
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
        if entity.domain == "sensor"
    ]


def _program_sensor_states(hass, entry):
    return [
        state
        for state in hass.states.async_all("sensor")
        if state.attributes.get("school_id") == entry.data[CONF_SCHOOL_ID]
    ]


async def _init_options(hass, entry):
    return await hass.config_entries.options.async_init(entry.entry_id)


@pytest.mark.asyncio
async def test_add_baseball_to_football_only_entry_keeps_football_unique_id(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """Adding varsity baseball via options creates a second sensor; football ID unchanged."""
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    entities_before = _sensor_entities(hass, entry)
    assert len(entities_before) == 1
    football_unique_id = f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Football"
    assert entities_before[0].unique_id == football_unique_id

    result = await _init_options(hass, entry)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "subscriptions": [
                FOOTBALL_SUBSCRIPTION_KEY,
                VARSITY_BASEBALL_SUBSCRIPTION_KEY,
            ]
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    entities_after = _sensor_entities(hass, entry)
    assert len(entities_after) == 2
    unique_ids = {entity.unique_id for entity in entities_after}
    assert football_unique_id in unique_ids
    assert f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Baseball" in unique_ids
    assert entry.options[CONF_SUBSCRIPTIONS] == [
        FOOTBALL_SUBSCRIPTION,
        VARSITY_BASEBALL_SUBSCRIPTION,
    ]


@pytest.mark.asyncio
async def test_remove_baseball_drops_sensor_after_reload(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """Removing baseball via options unloads that sensor; football unique_id unchanged."""
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION, VARSITY_BASEBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    football_unique_id = f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Football"
    baseball_unique_id = f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Baseball"
    assert {entity.unique_id for entity in _sensor_entities(hass, entry)} == {
        football_unique_id,
        baseball_unique_id,
    }

    result = await _init_options(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"subscriptions": [FOOTBALL_SUBSCRIPTION_KEY]},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    coordinator = entry.runtime_data
    assert len(coordinator.data.programs) == 1
    assert coordinator.data.programs[0].sport == "Football"

    sensor_states = _program_sensor_states(hass, entry)
    assert len(sensor_states) == 1
    assert sensor_states[0].attributes["sport"] == "Football"

    football_entities = [
        entity
        for entity in _sensor_entities(hass, entry)
        if entity.unique_id == football_unique_id
    ]
    assert len(football_entities) == 1
    assert football_entities[0].unique_id == football_unique_id
    assert not any(
        state.attributes.get("sport") == "Baseball"
        and state.attributes.get("level") == "Varsity"
        for state in sensor_states
    )


@pytest.mark.asyncio
async def test_options_schema_is_allowlisted_only(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """Options picker omits tennis and other non-allowlisted sports entirely."""
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)

    result = await _init_options(hass, entry)
    options = _selector_options(result, "subscriptions")
    labels = list(options.values())

    for key in options:
        sport = _sport_from_subscription_key(key)
        assert sport in ALLOWLISTED_SPORTS
        assert sport not in EXCLUDED_SPORTS

    assert "Tennis" not in labels
    assert "Soccer" not in labels


@pytest.mark.asyncio
async def test_pike_options_exclude_historical_rows(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """Pike County options never list historical 11-12 rows."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=PIKE_COUNTY_GA_ID,
        data={
            CONF_SCHOOL_ID: PIKE_COUNTY_GA_ID,
            CONF_CANONICAL_URL: PIKE_COUNTY_GA_URL,
            CONF_NAME: "Pike County",
        },
        options={CONF_SUBSCRIPTIONS: [FOOTBALL_SUBSCRIPTION]},
    )
    entry.add_to_hass(hass)

    result = await _init_options(hass, entry)
    assert result["type"] == FlowResultType.FORM
    labels = list(_selector_options(result, "subscriptions").values())

    assert "11-12" not in labels
    assert not any(excluded in label for label in labels for excluded in EXCLUDED_SPORTS)


@pytest.mark.asyncio
async def test_freshman_baseball_one_option_without_entity_parenthetical(
    hass, enable_custom_integrations, frozen_applicable_date
) -> None:
    """Freshman baseball is one picker option; entity name and unique_id stay short."""
    transport = CoordinatorTestTransport()
    client = AsyncMaxPrepsClient(transport)
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.maxpreps.config_flow.client_factory.create_async_client",
            return_value=client,
        ),
        patch(
            "custom_components.maxpreps.client_factory.create_async_client",
            return_value=client,
        ),
    ):
        result = await _init_options(hass, entry)
        options = _selector_options(result, "subscriptions")
        freshman_labels = [
            label for label in options.values() if label.startswith("Boys Freshman Baseball")
        ]
        assert freshman_labels == ["Boys Freshman Baseball (Fall, Spring 26-27)"]
        assert FRESHMAN_BASEBALL_SUBSCRIPTION_KEY in options

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"subscriptions": [FRESHMAN_BASEBALL_SUBSCRIPTION_KEY]},
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED

    sensor_states = _program_sensor_states(hass, entry)
    assert len(sensor_states) == 1
    state = sensor_states[0]
    assert state.attributes["display_label"] == "Boys Freshman Baseball"
    assert state.attributes["sport"] == "Baseball"
    assert state.attributes["level"] == "Freshman"
    assert "Fall" not in state.entity_id
    assert "26-27" not in state.entity_id

    entity = next(
        item
        for item in _sensor_entities(hass, entry)
        if item.unique_id == f"{CENTENNIAL_ROSWELL_ID}:Boys:Freshman:Baseball"
    )
    assert entity.unique_id == f"{CENTENNIAL_ROSWELL_ID}:Boys:Freshman:Baseball"


@pytest.mark.asyncio
async def test_empty_selection_rejected(hass, enable_custom_integrations, fixture_client) -> None:
    """Options flow requires at least one sport."""
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)

    result = await _init_options(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"subscriptions": []},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"] == {"subscriptions": "required"}


@pytest.mark.asyncio
async def test_unresolved_subscription_stays_in_picker_until_removed(
    hass, enable_custom_integrations, fixture_client
) -> None:
    """Configured subscriptions without provider rows stay pre-selected with a waiting label."""
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION, UNRESOLVED_SUBSCRIPTION])
    entry.add_to_hass(hass)

    result = await _init_options(hass, entry)
    options = _selector_options(result, "subscriptions")
    girls_football_key = "\x1e".join(("Football", "Girls", "Varsity"))
    assert options[girls_football_key] == "Girls Varsity Football (waiting for 26-27)"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"subscriptions": [FOOTBALL_SUBSCRIPTION_KEY, girls_football_key]},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SUBSCRIPTIONS] == [
        FOOTBALL_SUBSCRIPTION,
        UNRESOLVED_SUBSCRIPTION,
    ]


@pytest.mark.asyncio
async def test_availability_matrix_after_options_add_program(
    hass, enable_custom_integrations, frozen_applicable_date
) -> None:
    """One-good-term availability still holds after options reload adds a program."""
    transport = CoordinatorTestTransport(
        fail_urls=frozenset({FRESHMAN_BASEBALL_SPRING_SCHEDULE_URL})
    )
    client = AsyncMaxPrepsClient(transport)
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)

    with patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=client,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        result = await _init_options(hass, entry)
        with patch(
            "custom_components.maxpreps.config_flow.client_factory.create_async_client",
            return_value=client,
        ):
            result = await hass.config_entries.options.async_configure(
                result["flow_id"],
                {
                    "subscriptions": [
                        FOOTBALL_SUBSCRIPTION_KEY,
                        FRESHMAN_BASEBALL_SUBSCRIPTION_KEY,
                    ]
                },
            )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()

    sensor_states = _program_sensor_states(hass, entry)
    assert len(sensor_states) == 2

    football_state = next(
        state for state in sensor_states if state.attributes["sport"] == "Football"
    )
    freshman_state = next(
        state for state in sensor_states if state.attributes["level"] == "Freshman"
    )
    assert football_state.state != "unavailable"
    assert freshman_state.state != "unavailable"

    coordinator = entry.runtime_data
    freshman = next(
        program
        for program in coordinator.data.programs
        if program.sport == "Baseball" and program.level == "Freshman"
    )
    by_season = {term.team_season.season: term for term in freshman.terms}
    assert by_season["Spring"].status == TermRefreshStatus.ERROR
    assert by_season["Fall"].status == TermRefreshStatus.REFRESHED
    assert by_season["Fall"].schedule is not None


@pytest.fixture
def frozen_applicable_date():
    with patch(
        "custom_components.maxpreps.school_year.homeassistant_local_date",
        return_value=FROZEN_APPLICABLE_DATE,
    ):
        yield FROZEN_APPLICABLE_DATE
