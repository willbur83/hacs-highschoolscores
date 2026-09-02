"""Home Assistant integration load smoke tests."""

from __future__ import annotations

import pytest

pytest.importorskip("homeassistant")

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.maxpreps.const import CONF_GENDER, CONF_LEVEL, CONF_SPORT
from tests.helpers.coordinator_test_helpers import centennial_entry
from tests.test_coordinator import coordinator_client, frozen_applicable_date


@pytest.mark.asyncio
async def test_setup_and_unload(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    coordinator_client,
    frozen_applicable_date,
) -> None:
    """Integration setup and unload succeed with fixture-injected coordinator."""
    entry = centennial_entry(
        [
            {
                CONF_SPORT: "Football",
                CONF_GENDER: "Boys",
                CONF_LEVEL: "Varsity",
            }
        ]
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is not None
    assert entry.runtime_data.data is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
