"""Slice 10 — graceful degradation, reload, and unload (fixture transport only)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

pytest.importorskip("homeassistant")

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er

from custom_components.high_school_sports_scores.async_client import AsyncMaxPrepsClient
from custom_components.high_school_sports_scores.coordinator import TermRefreshStatus
from custom_components.high_school_sports_scores.exceptions import NextDataNotFoundError
from tests.helpers.coordinator_test_helpers import bainbridge_entry, centennial_entry
from tests.test_coordinator import (
    FRESHMAN_BASEBALL_SPRING_SCHEDULE_URL,
    FRESHMAN_BASEBALL_SUBSCRIPTION,
    FOOTBALL_SUBSCRIPTION,
    CoordinatorTestTransport,
    _program_by_subscription,
    frozen_applicable_date,
)
from tests.test_multi_school import (
    BAINBRIDGE_FOOTBALL_UNIQUE_ID,
    MultiSchoolTestTransport,
    _setup_two_football_entries,
    _state_for_unique_id,
)
from tests.test_search import CENTENNIAL_ROSWELL_ID


def _sensor_entities(hass, entry):
    registry = er.async_get(hass)
    return [
        entity
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
        if entity.domain == "sensor"
    ]


def _state_for_centennial_football(hass, entry):
    return _state_for_unique_id(
        hass,
        entry,
        f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Football",
    )


@pytest.mark.asyncio
async def test_school_home_no_next_data_after_success_retains_football_games(
    hass, enable_custom_integrations, frozen_applicable_date
) -> None:
    """Malformed school-home HTML raises UpdateFailed; last football last/next remain."""
    transport = CoordinatorTestTransport()
    client = AsyncMaxPrepsClient(transport)
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION, FRESHMAN_BASEBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)

    with patch(
        "custom_components.high_school_sports_scores.client_factory.create_async_client",
        return_value=client,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    coordinator = entry.runtime_data
    prior = coordinator.data
    assert prior is not None
    football_before = _program_by_subscription(coordinator, FOOTBALL_SUBSCRIPTION)
    assert football_before.terms[0].schedule is not None
    assert football_before.terms[0].schedule.games

    state_before = _state_for_centennial_football(hass, entry)
    assert state_before.state == "scheduled"
    assert "last_game" in state_before.attributes
    assert "next_game" in state_before.attributes

    failing_transport = CoordinatorTestTransport(school_home_no_next_data=True)
    failing_client = AsyncMaxPrepsClient(failing_transport)
    with patch(
        "custom_components.high_school_sports_scores.client_factory.create_async_client",
        return_value=failing_client,
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    assert coordinator.data == prior
    assert not coordinator.last_update_success

    football_after = _program_by_subscription(coordinator, FOOTBALL_SUBSCRIPTION)
    assert football_after.terms[0].schedule is football_before.terms[0].schedule
    assert football_after.terms[0].schedule.games

    state_after = _state_for_centennial_football(hass, entry)
    assert state_after.state == state_before.state
    assert state_after.attributes["last_game"] == state_before.attributes["last_game"]
    assert state_after.attributes["next_game"] == state_before.attributes["next_game"]
    assert state_after.state != "unavailable"


@pytest.mark.asyncio
async def test_first_setup_school_home_no_next_data_raises_config_entry_not_ready(
    hass, enable_custom_integrations, frozen_applicable_date
) -> None:
    """First school-home fetch without __NEXT_DATA__ surfaces NextDataNotFoundError at setup."""
    transport = CoordinatorTestTransport(school_home_no_next_data=True)
    client = AsyncMaxPrepsClient(transport)
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)

    with patch(
        "custom_components.high_school_sports_scores.client_factory.create_async_client",
        return_value=client,
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.SETUP_RETRY

    with pytest.raises(NextDataNotFoundError):
        await client.get_school_teams(
            __import__(
                "custom_components.high_school_sports_scores.coordinator",
                fromlist=["school_from_entry"],
            ).school_from_entry(entry)
        )


@pytest.mark.asyncio
async def test_429_on_one_freshman_term_isolates_siblings(
    hass, enable_custom_integrations, frozen_applicable_date
) -> None:
    """HTTP 429 on one schedule URL follows ERROR/STALE rules without affecting siblings."""
    transport = CoordinatorTestTransport()
    client = AsyncMaxPrepsClient(transport)
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION, FRESHMAN_BASEBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)

    with patch(
        "custom_components.high_school_sports_scores.client_factory.create_async_client",
        return_value=client,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    coordinator = entry.runtime_data
    spring_before = next(
        term
        for term in _program_by_subscription(
            coordinator, FRESHMAN_BASEBALL_SUBSCRIPTION
        ).terms
        if term.team_season.season == "Spring"
    )
    assert spring_before.status == TermRefreshStatus.REFRESHED

    failing_transport = CoordinatorTestTransport(
        http_429_urls=frozenset({FRESHMAN_BASEBALL_SPRING_SCHEDULE_URL})
    )
    failing_client = AsyncMaxPrepsClient(failing_transport)
    with patch(
        "custom_components.high_school_sports_scores.client_factory.create_async_client",
        return_value=failing_client,
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    freshman = _program_by_subscription(coordinator, FRESHMAN_BASEBALL_SUBSCRIPTION)
    football = _program_by_subscription(coordinator, FOOTBALL_SUBSCRIPTION)
    by_season = {term.team_season.season: term for term in freshman.terms}

    assert by_season["Spring"].status == TermRefreshStatus.STALE
    assert by_season["Spring"].schedule is spring_before.schedule
    assert by_season["Spring"].error_type == "TransportHttpError"
    assert by_season["Fall"].status == TermRefreshStatus.REFRESHED
    assert football.terms[0].status == TermRefreshStatus.REFRESHED

    football_state = _state_for_centennial_football(hass, entry)
    freshman_entity = next(
        entity
        for entity in _sensor_entities(hass, entry)
        if entity.unique_id.endswith(":Freshman:Baseball")
    )
    freshman_state = hass.states.get(freshman_entity.entity_id)
    assert football_state.state != "unavailable"
    assert freshman_state.state != "unavailable"


@pytest.mark.asyncio
async def test_empty_contests_program_refreshed_with_unknown_state(
    hass, enable_custom_integrations, frozen_applicable_date
) -> None:
    """Empty contests[] is a valid refresh with zero games; football sibling unaffected."""
    transport = CoordinatorTestTransport()
    client = AsyncMaxPrepsClient(transport)
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION, FRESHMAN_BASEBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)

    with patch(
        "custom_components.high_school_sports_scores.client_factory.create_async_client",
        return_value=client,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    coordinator = entry.runtime_data
    freshman = _program_by_subscription(coordinator, FRESHMAN_BASEBALL_SUBSCRIPTION)
    assert len(freshman.terms) == 2
    for term in freshman.terms:
        assert term.status == TermRefreshStatus.REFRESHED
        assert term.schedule is not None
        assert len(term.schedule.games) == 0
        assert term.last_success_at is not None

    freshman_entity = next(
        entity
        for entity in _sensor_entities(hass, entry)
        if entity.unique_id.endswith(":Freshman:Baseball")
    )
    freshman_state = hass.states.get(freshman_entity.entity_id)
    assert freshman_state.state == "unknown"
    assert "last_game" not in freshman_state.attributes
    assert "next_game" not in freshman_state.attributes

    football_state = _state_for_centennial_football(hass, entry)
    assert football_state.state == "scheduled"
    assert "last_game" in football_state.attributes
    assert "next_game" in football_state.attributes


@pytest.mark.asyncio
async def test_reload_keeps_entity_unique_ids(
    hass, enable_custom_integrations, frozen_applicable_date
) -> None:
    """Reload through the config-entry manager preserves entity-registry unique IDs."""
    transport = CoordinatorTestTransport()
    client = AsyncMaxPrepsClient(transport)
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION, FRESHMAN_BASEBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)

    with patch(
        "custom_components.high_school_sports_scores.client_factory.create_async_client",
        return_value=client,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    registry = er.async_get(hass)
    entities_before = _sensor_entities(hass, entry)
    unique_ids_before = {entity.unique_id for entity in entities_before}
    entity_ids_before = {entity.entity_id for entity in entities_before}
    assert unique_ids_before == {
        f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Football",
        f"{CENTENNIAL_ROSWELL_ID}:Boys:Freshman:Baseball",
    }

    with patch(
        "custom_components.high_school_sports_scores.client_factory.create_async_client",
        return_value=client,
    ):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    entities_after = _sensor_entities(hass, entry)
    unique_ids_after = {entity.unique_id for entity in entities_after}
    entity_ids_after = {entity.entity_id for entity in entities_after}
    assert unique_ids_after == unique_ids_before
    assert entity_ids_after == entity_ids_before
    assert len(entities_after) == len(entities_before)
    assert (
        len(er.async_entries_for_config_entry(registry, entry.entry_id))
        == len(entities_before)
    )


@pytest.mark.asyncio
async def test_unload_not_loaded_then_setup_leaves_second_school_untouched(
    hass, enable_custom_integrations, frozen_applicable_date
) -> None:
    """Unload unloads sensors; re-setup works; a loaded sibling school is untouched."""
    working_transport = MultiSchoolTestTransport()
    working_client = AsyncMaxPrepsClient(working_transport)
    with patch(
        "custom_components.high_school_sports_scores.client_factory.create_async_client",
        return_value=working_client,
    ):
        centennial, bainbridge = await _setup_two_football_entries(
            hass, (working_client, working_transport)
        )

    bainbridge_state_before = _state_for_unique_id(
        hass, bainbridge, BAINBRIDGE_FOOTBALL_UNIQUE_ID
    )
    assert bainbridge_state_before.state == "scheduled"
    bainbridge_runtime_before = bainbridge.runtime_data

    assert await hass.config_entries.async_unload(centennial.entry_id)
    await hass.async_block_till_done()
    assert centennial.state is ConfigEntryState.NOT_LOADED
    centennial_entity = next(
        entity
        for entity in _sensor_entities(hass, centennial)
        if entity.unique_id.endswith(":Varsity:Football")
    )
    centennial_state_unloaded = hass.states.get(centennial_entity.entity_id)
    assert centennial_state_unloaded is not None
    assert centennial_state_unloaded.state == "unavailable"

    assert bainbridge.state is ConfigEntryState.LOADED
    assert bainbridge.runtime_data is bainbridge_runtime_before
    bainbridge_state_mid = _state_for_unique_id(
        hass, bainbridge, BAINBRIDGE_FOOTBALL_UNIQUE_ID
    )
    assert bainbridge_state_mid.state == "scheduled"

    with patch(
        "custom_components.high_school_sports_scores.client_factory.create_async_client",
        return_value=working_client,
    ):
        assert await hass.config_entries.async_setup(centennial.entry_id)
        await hass.async_block_till_done()

    assert centennial.state is ConfigEntryState.LOADED
    assert centennial.runtime_data is not None
    assert centennial.runtime_data.data is not None
    assert len(_sensor_entities(hass, centennial)) == 1

    football_state = _state_for_centennial_football(hass, centennial)
    assert football_state.state == "scheduled"

    bainbridge_state_after = _state_for_unique_id(
        hass, bainbridge, BAINBRIDGE_FOOTBALL_UNIQUE_ID
    )
    assert bainbridge_state_after.state == "scheduled"
    assert bainbridge.state is ConfigEntryState.LOADED
