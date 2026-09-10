"""High School Sports Scores Home Assistant integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.high_school_sports_scores.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

__all__ = ["DOMAIN", "async_setup", "async_setup_entry", "async_unload_entry"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the High School Sports Scores integration."""
    from custom_components.high_school_sports_scores.frontend_register import async_register_frontend
    from custom_components.high_school_sports_scores.websocket import async_register_websocket_handlers

    async_register_websocket_handlers(hass)
    await async_register_frontend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up High School Sports Scores from a config entry."""
    from homeassistant.const import Platform

    from custom_components.high_school_sports_scores.coordinator import MaxPrepsDataUpdateCoordinator

    coordinator = MaxPrepsDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    from homeassistant.const import Platform

    return await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])
