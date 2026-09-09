"""Home Assistant websocket commands for Phase 4 schedule access."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from custom_components.maxpreps.const import DOMAIN
from custom_components.maxpreps.coordinator import MaxPrepsDataUpdateCoordinator
from custom_components.maxpreps.program_identity import (
    ParsedProgramUniqueId,
    parse_program_unique_id,
)
from custom_components.maxpreps.schedule_payload import (
    build_program_schedule_payload,
    find_program_snapshot,
)

if TYPE_CHECKING:
    from homeassistant.components.websocket_api import ActiveConnection

ERR_ENTITY_NOT_FOUND = "entity_not_found"
ERR_NOT_MAXPREPS_PROGRAM = "not_maxpreps_program"
ERR_NO_COORDINATOR = "no_coordinator_data"


@dataclass(frozen=True, slots=True)
class ResolvedProgramEntity:
    """Registry-owned MaxPreps program sensor resolution."""

    entity_id: str
    entity_entry: er.RegistryEntry
    identity: ParsedProgramUniqueId
    coordinator: MaxPrepsDataUpdateCoordinator


def resolve_program_entity(
    hass: HomeAssistant,
    entity_id: str,
) -> ResolvedProgramEntity | str:
    """Resolve and verify registry ownership for a program sensor entity."""
    entity_registry = er.async_get(hass)
    entity_entry = entity_registry.async_get(entity_id)
    if entity_entry is None:
        return ERR_ENTITY_NOT_FOUND

    if entity_entry.platform != DOMAIN:
        return ERR_NOT_MAXPREPS_PROGRAM

    if entity_entry.config_entry_id is None:
        return ERR_NOT_MAXPREPS_PROGRAM

    config_entry = hass.config_entries.async_get_entry(entity_entry.config_entry_id)
    if config_entry is None or config_entry.domain != DOMAIN:
        return ERR_NOT_MAXPREPS_PROGRAM

    if entity_entry.unique_id is None:
        return ERR_NOT_MAXPREPS_PROGRAM

    identity = parse_program_unique_id(entity_entry.unique_id)
    if identity is None:
        return ERR_NOT_MAXPREPS_PROGRAM

    coordinator = config_entry.runtime_data
    if not isinstance(coordinator, MaxPrepsDataUpdateCoordinator):
        return ERR_NO_COORDINATOR

    data = coordinator.data
    if data is None:
        return ERR_NO_COORDINATOR

    program = find_program_snapshot(data.programs, identity)
    if program is None:
        return ERR_NOT_MAXPREPS_PROGRAM

    return ResolvedProgramEntity(
        entity_id=entity_id,
        entity_entry=entity_entry,
        identity=identity,
        coordinator=coordinator,
    )


def _send_resolution_error(
    connection: ActiveConnection,
    msg: dict[str, Any],
    error_code: str,
) -> None:
    messages = {
        ERR_ENTITY_NOT_FOUND: "Entity not found",
        ERR_NOT_MAXPREPS_PROGRAM: "Entity is not a MaxPreps program sensor",
        ERR_NO_COORDINATOR: "MaxPreps coordinator data is unavailable",
    }
    connection.send_error(
        msg["id"],
        error_code,
        messages.get(error_code, "Request failed"),
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/get_program_schedule",
        vol.Required("entity_id"): str,
    }
)
@websocket_api.async_response
async def ws_get_program_schedule(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the program schedule DTO from coordinator runtime data."""
    resolved = resolve_program_entity(hass, msg["entity_id"])
    if isinstance(resolved, str):
        _send_resolution_error(connection, msg, resolved)
        return

    data = resolved.coordinator.data
    assert data is not None
    program = find_program_snapshot(data.programs, resolved.identity)
    if program is None:
        _send_resolution_error(connection, msg, ERR_NOT_MAXPREPS_PROGRAM)
        return

    connection.send_result(
        msg["id"],
        build_program_schedule_payload(
            msg["entity_id"],
            school_id=data.school.school_id,
            school_name=data.school.name,
            applicable_school_year=data.applicable_school_year,
            program=program,
        ),
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/subscribe_program_schedule_updates",
        vol.Required("entity_id"): str,
    }
)
@websocket_api.async_response
async def ws_subscribe_program_schedule_updates(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Subscribe to lightweight schedule invalidation events for one program."""
    resolved = resolve_program_entity(hass, msg["entity_id"])
    if isinstance(resolved, str):
        _send_resolution_error(connection, msg, resolved)
        return

    entity_id = msg["entity_id"]
    subscription_id = msg["id"]

    @callback
    def _coordinator_updated() -> None:
        current = resolve_program_entity(hass, entity_id)
        if isinstance(current, str) or current.coordinator is not resolved.coordinator:
            return
        connection.send_message(
            websocket_api.event_message(
                subscription_id,
                {"entity_id": entity_id, "event": "schedule_updated"},
            )
        )

    unsub_coordinator = resolved.coordinator.async_add_listener(_coordinator_updated)

    @callback
    def cancel_subscription() -> None:
        unsub_coordinator()

    connection.subscriptions[subscription_id] = cancel_subscription
    connection.send_result(subscription_id, {"entity_id": entity_id})


def async_register_websocket_handlers(hass: HomeAssistant) -> None:
    """Register MaxPreps websocket commands once per integration."""
    websocket_api.async_register_command(hass, ws_get_program_schedule)
    websocket_api.async_register_command(hass, ws_subscribe_program_schedule_updates)


__all__ = [
    "ERR_ENTITY_NOT_FOUND",
    "ERR_NOT_MAXPREPS_PROGRAM",
    "ERR_NO_COORDINATOR",
    "ResolvedProgramEntity",
    "async_register_websocket_handlers",
    "resolve_program_entity",
]
