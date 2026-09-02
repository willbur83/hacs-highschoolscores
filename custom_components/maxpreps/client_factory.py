"""Factory for AsyncMaxPrepsClient wired to Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.maxpreps.async_client import AsyncMaxPrepsClient

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def create_async_client(hass: HomeAssistant) -> AsyncMaxPrepsClient:
    """Return an async MaxPreps client using Home Assistant's shared HTTP session."""
    from custom_components.maxpreps.ha_transport import create_ha_transport

    return AsyncMaxPrepsClient(create_ha_transport(hass))


__all__ = ["create_async_client"]
