"""Layer 2 websocket command tests (fixture transport only)."""

from __future__ import annotations

from dataclasses import replace

import pytest

pytest.importorskip("homeassistant")

from homeassistant.components.websocket_api.const import TYPE_RESULT
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er

from custom_components.maxpreps import async_setup
from custom_components.maxpreps.const import CONF_GENDER, CONF_LEVEL, CONF_SPORT, DOMAIN
from custom_components.maxpreps.models import GameStatus
from custom_components.maxpreps.program_sensor import find_next_game
from custom_components.maxpreps.websocket import (
    ERR_ENTITY_NOT_FOUND,
    ERR_NOT_MAXPREPS_PROGRAM,
)
from tests.helpers.coordinator_test_helpers import centennial_entry
from tests.test_coordinator import FOOTBALL_SUBSCRIPTION, coordinator_client, frozen_applicable_date
from tests.test_search import CENTENNIAL_ROSWELL_ID


def _football_entity(hass, entry):
    registry = er.async_get(hass)
    return next(
        entity
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
        if entity.domain == "sensor"
        and entity.unique_id == f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Football"
    )


@pytest.mark.asyncio
async def test_get_program_schedule_football_fixture(
    hass,
    enable_custom_integrations,
    coordinator_client,
    frozen_applicable_date,
    hass_ws_client,
) -> None:
    """Happy path returns the full schedule DTO for a real program sensor."""
    websocket_client = await hass_ws_client(hass)
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    entity = _football_entity(hass, entry)
    await websocket_client.send_json(
        {
            "id": 1,
            "type": "maxpreps/get_program_schedule",
            "entity_id": entity.entity_id,
        }
    )
    msg = await websocket_client.receive_json()

    assert msg["id"] == 1
    assert msg["type"] == TYPE_RESULT
    assert msg["success"] is True
    result = msg["result"]
    assert result["schema_version"] == 1
    assert result["entity_id"] == entity.entity_id
    assert result["school_id"] == CENTENNIAL_ROSWELL_ID
    assert result["school_name"] == "Centennial"
    assert result["applicable_school_year"] == "26-27"
    assert result["sport"] == "Football"
    assert result["gender"] == "Boys"
    assert result["level"] == "Varsity"
    assert result["display_label"] == "Boys Varsity Football"
    assert result["resolution_status"] == "resolved"
    assert len(result["terms"]) == 1
    assert result["terms"][0]["season"] == "Fall"
    assert result["terms"][0]["year"] == "26-27"
    assert result["terms"][0]["status"] == "refreshed"
    assert len(result["terms"][0]["games"]) == 10
    assert all(game["status"] != "deleted" for game in result["terms"][0]["games"])


@pytest.mark.asyncio
async def test_get_program_schedule_rejects_unknown_entity(
    hass,
    enable_custom_integrations,
    hass_ws_client,
) -> None:
    assert await async_setup(hass, {})
    websocket_client = await hass_ws_client(hass)
    await websocket_client.send_json(
        {
            "id": 2,
            "type": "maxpreps/get_program_schedule",
            "entity_id": "sensor.does_not_exist",
        }
    )
    msg = await websocket_client.receive_json()

    assert msg["success"] is False
    assert msg["error"]["code"] == ERR_ENTITY_NOT_FOUND


@pytest.mark.asyncio
async def test_get_program_schedule_rejects_non_maxpreps_registry_owner(
    hass,
    enable_custom_integrations,
    coordinator_client,
    frozen_applicable_date,
    hass_ws_client,
) -> None:
    """Registry platform ownership is required; attributes alone are insufficient."""
    websocket_client = await hass_ws_client(hass)
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    foreign = registry.async_get_or_create(
        "sensor",
        "template",
        "foreign-football",
        suggested_object_id="foreign_football",
    )
    registry.async_update_entity(
        foreign.entity_id,
        new_unique_id=f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Football",
    )

    await websocket_client.send_json(
        {
            "id": 3,
            "type": "maxpreps/get_program_schedule",
            "entity_id": foreign.entity_id,
        }
    )
    msg = await websocket_client.receive_json()

    assert msg["success"] is False
    assert msg["error"]["code"] == ERR_NOT_MAXPREPS_PROGRAM


@pytest.mark.asyncio
async def test_subscribe_notifies_when_schedule_changes_without_last_next_delta(
    hass,
    enable_custom_integrations,
    coordinator_client,
    frozen_applicable_date,
    hass_ws_client,
) -> None:
    """Coordinator refresh can change mid-schedule rows without entity last/next churn."""
    websocket_client = await hass_ws_client(hass)
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity = _football_entity(hass, entry)
    state_before = hass.states.get(entity.entity_id)
    assert state_before is not None

    await websocket_client.send_json(
        {
            "id": 10,
            "type": "maxpreps/subscribe_program_schedule_updates",
            "entity_id": entity.entity_id,
        }
    )
    sub_msg = await websocket_client.receive_json()
    assert sub_msg["success"] is True

    coordinator = entry.runtime_data
    data = coordinator.data
    assert data is not None
    program = data.programs[0]
    next_ref = find_next_game(program)
    assert next_ref is not None

    term = program.terms[0]
    schedule = term.schedule
    assert schedule is not None
    target = next(
        game
        for game in schedule.games
        if game.status is GameStatus.SCHEDULED and game.id != next_ref.game.id
    )
    games = list(schedule.games)
    games[games.index(target)] = replace(target, venue="Updated far-future venue")
    new_term = replace(term, schedule=replace(schedule, games=games))
    new_program = replace(program, terms=(new_term,))
    new_data = replace(data, programs=(new_program,))

    coordinator.async_set_updated_data(new_data)
    event_msg = await websocket_client.receive_json()

    assert event_msg["id"] == 10
    assert event_msg["type"] == "event"
    assert event_msg["event"]["event"] == "schedule_updated"
    assert event_msg["event"]["entity_id"] == entity.entity_id

    state_after = hass.states.get(entity.entity_id)
    assert state_after is not None
    assert state_after.state == state_before.state
    assert state_after.attributes["last_game"] == state_before.attributes["last_game"]
    assert state_after.attributes["next_game"] == state_before.attributes["next_game"]
