"""MaxPreps Home Assistant integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.maxpreps.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

__all__ = ["DOMAIN", "async_setup", "async_setup_entry", "async_unload_entry"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the MaxPreps integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MaxPreps from a config entry."""
    from custom_components.maxpreps.coordinator import MaxPrepsDataUpdateCoordinator

    coordinator = MaxPrepsDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True
