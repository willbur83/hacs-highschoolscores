"""High School Sports Scores Home Assistant integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers import config_validation as cv

from custom_components.high_school_sports_scores.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

# Config entries only. YAML under this domain is rejected by the helper.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

__all__ = [
    "CONFIG_SCHEMA",
    "DOMAIN",
    "async_setup",
    "async_setup_entry",
    "async_unload_entry",
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the High School Sports Scores integration."""
    from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
    from homeassistant.core import CoreState

    from custom_components.high_school_sports_scores.frontend_register import (
        async_register_card_static,
        async_register_frontend,
    )
    from custom_components.high_school_sports_scores.websocket import async_register_websocket_handlers

    async_register_websocket_handlers(hass)
    # The HTTP view has to exist before dashboards load. Resource registration can
    # wait for Lovelace; a kiosk that fetches the card during startup must not 404.
    await async_register_card_static(hass)

    async def _register_frontend_when_ready(_event=None) -> None:
        await async_register_frontend(hass)

    if hass.state is CoreState.running:
        await _register_frontend_when_ready()
    else:
        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED,
            _register_frontend_when_ready,
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up High School Sports Scores from a config entry."""
    from homeassistant.const import Platform
    from homeassistant.core import CoreState

    from custom_components.high_school_sports_scores.coordinator import MaxPrepsDataUpdateCoordinator
    from custom_components.high_school_sports_scores.frontend_register import async_register_frontend

    # Publish the loader URL before the MaxPreps refresh. Waiting on that refresh
    # left the card path unregistered while always-on kiosks loaded the dashboard.
    await async_register_frontend(hass, prompt_browser_reload=hass.state is CoreState.running)

    coordinator = MaxPrepsDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    from homeassistant.const import Platform

    return await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])
