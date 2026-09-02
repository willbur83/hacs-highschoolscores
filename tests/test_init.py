"""Home Assistant integration load smoke tests."""

from __future__ import annotations

import pytest

pytest.importorskip("homeassistant")

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.maxpreps.const import DOMAIN


@pytest.mark.asyncio
async def test_setup_and_unload(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Integration setup and unload succeed without network I/O."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="MaxPreps")
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
