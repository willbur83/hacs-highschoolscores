"""Slice 8 multi-school integration tests (fixture transport only)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

pytest.importorskip("homeassistant")

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.maxpreps.async_client import AsyncMaxPrepsClient
from custom_components.maxpreps.const import CONF_GENDER, CONF_LEVEL, CONF_SPORT, DOMAIN
from custom_components.maxpreps.exceptions import MaxPrepsError
from tests.helpers.async_fixture_transport import AsyncFixtureTransport
from tests.helpers.coordinator_test_helpers import (
    bainbridge_entry,
    centennial_entry,
)
from tests.test_coordinator import FOOTBALL_SUBSCRIPTION, frozen_applicable_date
from tests.test_schedule import FOOTBALL_SPORT_SEASON_ID
from tests.test_search import (
    BAINBRIDGE_GA_ID,
    BAINBRIDGE_GA_URL,
    CENTENNIAL_ROSWELL_ID,
    CENTENNIAL_ROSWELL_URL,
)

CENTENNIAL_FOOTBALL_UNIQUE_ID = f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Football"
BAINBRIDGE_FOOTBALL_UNIQUE_ID = f"{BAINBRIDGE_GA_ID}:Boys:Varsity:Football"


class MultiSchoolTestTransport:
    """Fixture transport with optional per-school-home failure injection."""

    def __init__(self, *, fail_school_urls: frozenset[str] = frozenset()) -> None:
        self._base = AsyncFixtureTransport()
        self._fail_school_urls = fail_school_urls

    @property
    def requested_urls(self) -> list[str]:
        return self._base.requested_urls

    async def fetch(self, url: str) -> str:
        if url in self._fail_school_urls:
            raise MaxPrepsError(f"simulated school-home failure for {url}")
        return await self._base.fetch(url)


@pytest.fixture
def multi_school_client():
    transport = MultiSchoolTestTransport()
    client = AsyncMaxPrepsClient(transport)
    with patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=client,
    ):
        yield client, transport


def _sensor_entities(hass, entry):
    registry = er.async_get(hass)
    return [
        entity
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
        if entity.domain == "sensor"
    ]


def _state_for_unique_id(hass, entry, unique_id: str):
    entity = next(
        item for item in _sensor_entities(hass, entry) if item.unique_id == unique_id
    )
    state = hass.states.get(entity.entity_id)
    assert state is not None
    return state


async def _setup_two_football_entries(hass, multi_school_client):
    centennial = centennial_entry([FOOTBALL_SUBSCRIPTION])
    centennial.add_to_hass(hass)
    assert await hass.config_entries.async_setup(centennial.entry_id)
    await hass.async_block_till_done()

    bainbridge = bainbridge_entry([FOOTBALL_SUBSCRIPTION])
    bainbridge.add_to_hass(hass)
    assert await hass.config_entries.async_setup(bainbridge.entry_id)
    await hass.async_block_till_done()

    assert centennial.state is ConfigEntryState.LOADED
    assert bainbridge.state is ConfigEntryState.LOADED
    return centennial, bainbridge


def _football_program(coordinator):
    data = coordinator.data
    assert data is not None
    assert len(data.programs) == 1
    return data.programs[0]


@pytest.mark.asyncio
async def test_two_schools_two_devices_non_colliding_football_unique_ids(
    hass,
    enable_custom_integrations,
    multi_school_client,
    frozen_applicable_date,
) -> None:
    """Two loaded entries expose distinct devices and football entity unique IDs."""
    centennial, bainbridge = await _setup_two_football_entries(hass, multi_school_client)

    device_registry = dr.async_get(hass)
    centennial_device = device_registry.async_get_device_by_identifier(
        (DOMAIN, CENTENNIAL_ROSWELL_ID),
        centennial.entry_id,
    )
    bainbridge_device = device_registry.async_get_device_by_identifier(
        (DOMAIN, BAINBRIDGE_GA_ID),
        bainbridge.entry_id,
    )
    assert centennial_device is not None
    assert bainbridge_device is not None
    assert centennial_device.id != bainbridge_device.id
    assert centennial_device.name == "Centennial"
    assert bainbridge_device.name == "Bainbridge"
    assert str(centennial_device.configuration_url) == CENTENNIAL_ROSWELL_URL
    assert str(bainbridge_device.configuration_url) == BAINBRIDGE_GA_URL

    centennial_entities = _sensor_entities(hass, centennial)
    bainbridge_entities = _sensor_entities(hass, bainbridge)
    assert len(centennial_entities) == 1
    assert len(bainbridge_entities) == 1

    centennial_unique_id = centennial_entities[0].unique_id
    bainbridge_unique_id = bainbridge_entities[0].unique_id
    assert centennial_unique_id == CENTENNIAL_FOOTBALL_UNIQUE_ID
    assert bainbridge_unique_id == BAINBRIDGE_FOOTBALL_UNIQUE_ID
    assert centennial_unique_id != bainbridge_unique_id

    entity_registry = er.async_get(hass)
    registered_unique_ids = {
        entity.unique_id
        for entity in entity_registry.entities.values()
        if entity.platform == DOMAIN and entity.domain == "sensor"
    }
    assert centennial_unique_id in registered_unique_ids
    assert bainbridge_unique_id in registered_unique_ids


@pytest.mark.asyncio
async def test_shared_football_sport_season_id_on_both_programs(
    hass,
    enable_custom_integrations,
    multi_school_client,
    frozen_applicable_date,
) -> None:
    """Shared provider sport_season_id does not collapse entity unique IDs."""
    centennial, bainbridge = await _setup_two_football_entries(hass, multi_school_client)

    centennial_program = _football_program(centennial.runtime_data)
    bainbridge_program = _football_program(bainbridge.runtime_data)

    centennial_ssid = centennial_program.terms[0].team_season.sport_season_id
    bainbridge_ssid = bainbridge_program.terms[0].team_season.sport_season_id
    assert centennial_ssid == FOOTBALL_SPORT_SEASON_ID
    assert bainbridge_ssid == FOOTBALL_SPORT_SEASON_ID
    assert centennial_ssid == bainbridge_ssid

    centennial_entities = _sensor_entities(hass, centennial)
    bainbridge_entities = _sensor_entities(hass, bainbridge)
    assert centennial_entities[0].unique_id != bainbridge_entities[0].unique_id


@pytest.mark.asyncio
async def test_coordinators_are_independent(
    hass,
    enable_custom_integrations,
    multi_school_client,
    frozen_applicable_date,
) -> None:
    """Each entry owns a distinct coordinator and data object; refresh is isolated."""
    centennial, bainbridge = await _setup_two_football_entries(hass, multi_school_client)

    centennial_coordinator = centennial.runtime_data
    bainbridge_coordinator = bainbridge.runtime_data
    assert centennial_coordinator is not bainbridge_coordinator
    assert centennial.runtime_data is not bainbridge.runtime_data

    centennial_data_before = centennial_coordinator.data
    bainbridge_data_before = bainbridge_coordinator.data
    assert centennial_data_before is not bainbridge_data_before
    assert centennial_data_before.school.school_id == CENTENNIAL_ROSWELL_ID
    assert bainbridge_data_before.school.school_id == BAINBRIDGE_GA_ID

    await centennial_coordinator.async_refresh()
    await hass.async_block_till_done()

    assert bainbridge_coordinator.data is bainbridge_data_before
    assert bainbridge_coordinator.data.school.school_id == BAINBRIDGE_GA_ID
    assert centennial_coordinator.data is not bainbridge_coordinator.data
    assert centennial_coordinator.data.school.school_id == CENTENNIAL_ROSWELL_ID


@pytest.mark.asyncio
async def test_unload_centennial_leaves_bainbridge_loaded(
    hass,
    enable_custom_integrations,
    multi_school_client,
    frozen_applicable_date,
) -> None:
    """Unloading one school entry does not unload the other."""
    centennial, bainbridge = await _setup_two_football_entries(hass, multi_school_client)

    bainbridge_state_before = _state_for_unique_id(
        hass, bainbridge, BAINBRIDGE_FOOTBALL_UNIQUE_ID
    )
    assert bainbridge_state_before.state == "scheduled"
    bainbridge_runtime_data_before = bainbridge.runtime_data

    assert await hass.config_entries.async_unload(centennial.entry_id)
    await hass.async_block_till_done()

    assert centennial.state is ConfigEntryState.NOT_LOADED
    assert bainbridge.state is ConfigEntryState.LOADED
    assert bainbridge.runtime_data is bainbridge_runtime_data_before
    assert bainbridge.runtime_data.data is not None
    assert bainbridge.runtime_data.data.school.school_id == BAINBRIDGE_GA_ID

    bainbridge_state_after = _state_for_unique_id(
        hass, bainbridge, BAINBRIDGE_FOOTBALL_UNIQUE_ID
    )
    assert bainbridge_state_after.state == "scheduled"

    assert await hass.config_entries.async_unload(bainbridge.entry_id)
    await hass.async_block_till_done()
    assert bainbridge.state is ConfigEntryState.NOT_LOADED


@pytest.mark.asyncio
async def test_unload_bainbridge_leaves_centennial_loaded(
    hass,
    enable_custom_integrations,
    multi_school_client,
    frozen_applicable_date,
) -> None:
    """Unloading Bainbridge does not disturb a loaded Centennial entry."""
    centennial, bainbridge = await _setup_two_football_entries(hass, multi_school_client)

    centennial_state_before = _state_for_unique_id(
        hass, centennial, CENTENNIAL_FOOTBALL_UNIQUE_ID
    )
    assert centennial_state_before.state == "scheduled"
    centennial_runtime_data_before = centennial.runtime_data

    assert await hass.config_entries.async_unload(bainbridge.entry_id)
    await hass.async_block_till_done()

    assert bainbridge.state is ConfigEntryState.NOT_LOADED
    assert centennial.state is ConfigEntryState.LOADED
    assert centennial.runtime_data is centennial_runtime_data_before
    assert centennial.runtime_data.data is not None
    assert centennial.runtime_data.data.school.school_id == CENTENNIAL_ROSWELL_ID

    centennial_state_after = _state_for_unique_id(
        hass, centennial, CENTENNIAL_FOOTBALL_UNIQUE_ID
    )
    assert centennial_state_after.state == "scheduled"


@pytest.mark.asyncio
async def test_school_home_failure_on_one_entry_does_not_affect_other(
    hass,
    enable_custom_integrations,
    frozen_applicable_date,
) -> None:
    """Centennial school-home failure retains its snapshot and leaves Bainbridge refreshable."""
    working_transport = MultiSchoolTestTransport()
    working_client = AsyncMaxPrepsClient(working_transport)
    with patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=working_client,
    ):
        centennial, bainbridge = await _setup_two_football_entries(
            hass, (working_client, working_transport)
        )

    centennial_coordinator = centennial.runtime_data
    bainbridge_coordinator = bainbridge.runtime_data
    centennial_data_before = centennial_coordinator.data
    bainbridge_data_before = bainbridge_coordinator.data
    assert centennial_data_before is not None
    assert bainbridge_data_before is not None

    failing_transport = MultiSchoolTestTransport(
        fail_school_urls=frozenset({CENTENNIAL_ROSWELL_URL})
    )
    failing_client = AsyncMaxPrepsClient(failing_transport)
    with patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=failing_client,
    ):
        await centennial_coordinator.async_refresh()
        await bainbridge_coordinator.async_refresh()
        await hass.async_block_till_done()

    assert centennial_coordinator.data == centennial_data_before
    assert not centennial_coordinator.last_update_success
    assert bainbridge_coordinator.data != bainbridge_data_before
    assert bainbridge_coordinator.last_update_success
    assert bainbridge_coordinator.data.school.school_id == BAINBRIDGE_GA_ID

    bainbridge_state = _state_for_unique_id(hass, bainbridge, BAINBRIDGE_FOOTBALL_UNIQUE_ID)
    assert bainbridge_state.state == "scheduled"
