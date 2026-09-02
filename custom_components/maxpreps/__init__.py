"""MaxPreps Home Assistant integration."""

from __future__ import annotations

from .const import DOMAIN

__all__ = ["DOMAIN", "async_setup", "async_setup_entry", "async_unload_entry"]


async def async_setup(hass, config: dict) -> bool:
    """Set up the MaxPreps integration."""
    return True


async def async_setup_entry(hass, entry) -> bool:
    """Set up MaxPreps from a config entry."""
    return True


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry."""
    return True
