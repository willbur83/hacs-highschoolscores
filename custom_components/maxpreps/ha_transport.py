"""Home Assistant wiring for the production aiohttp transport."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.maxpreps.async_transport import AiohttpTransport

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def create_ha_transport(hass: HomeAssistant) -> AiohttpTransport:
    """Return a transport backed by Home Assistant's shared client session."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    return AiohttpTransport(async_get_clientsession(hass))


__all__ = ["create_ha_transport"]
