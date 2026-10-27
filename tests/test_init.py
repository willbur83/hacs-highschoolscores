"""Home Assistant integration load smoke tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("homeassistant")

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.high_school_sports_scores import async_setup
from custom_components.high_school_sports_scores.const import CONF_GENDER, CONF_LEVEL, CONF_SPORT
from tests.helpers.coordinator_test_helpers import centennial_entry
from tests.test_coordinator import coordinator_client, frozen_applicable_date


@pytest.mark.asyncio
async def test_config_entry_setup_registers_frontend(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    coordinator_client,
    frozen_applicable_date,
) -> None:
    """Config entry load retries Lovelace registration after domain async_setup."""
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

    with patch(
        "custom_components.high_school_sports_scores.frontend_register.async_register_frontend",
        new_callable=AsyncMock,
    ) as mock_register:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    mock_register.assert_awaited()


@pytest.mark.asyncio
async def test_config_entry_registers_frontend_before_first_refresh(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    coordinator_client,
    frozen_applicable_date,
) -> None:
    """Kiosks must be able to fetch the card before the first MaxPreps refresh returns."""
    from custom_components.high_school_sports_scores.coordinator import MaxPrepsDataUpdateCoordinator

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
    order: list[str] = []
    original_refresh = MaxPrepsDataUpdateCoordinator.async_config_entry_first_refresh

    async def _register(*_args, **_kwargs) -> None:
        order.append("frontend")

    async def _refresh(self):
        order.append("refresh")
        return await original_refresh(self)

    with (
        patch(
            "custom_components.high_school_sports_scores.frontend_register.async_register_frontend",
            new=_register,
        ),
        patch.object(
            MaxPrepsDataUpdateCoordinator,
            "async_config_entry_first_refresh",
            new=_refresh,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert order.index("frontend") < order.index("refresh")


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


@pytest.mark.asyncio
async def test_domain_setup_without_built_js_bundle(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Missing www/*.js must not prevent domain setup (Spike 0A)."""
    with patch(
        "custom_components.high_school_sports_scores.frontend_register.card_bundle_available",
        return_value=False,
    ):
        assert await async_setup(hass, {})


@pytest.mark.asyncio
async def test_config_entry_loads_without_built_js_bundle(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    coordinator_client,
    frozen_applicable_date,
) -> None:
    """Missing www/*.js must not prevent config entry coordinators and sensors."""
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

    with patch(
        "custom_components.high_school_sports_scores.frontend_register.card_bundle_available",
        return_value=False,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is not None
    assert entry.runtime_data.data is not None


@pytest.mark.asyncio
async def test_domain_setup_succeeds_when_frontend_registration_unavailable(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Bundle present but http/frontend unavailable must not fail domain setup."""
    with (
        patch(
            "custom_components.high_school_sports_scores.frontend_register.card_bundle_available",
            return_value=True,
        ),
        patch(
            "custom_components.high_school_sports_scores.frontend_register._register_static_http_path",
            side_effect=ImportError("No module named 'hass_frontend'"),
        ),
    ):
        assert await async_setup(hass, {})


@pytest.mark.asyncio
async def test_config_entry_loads_when_frontend_registration_unavailable(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    coordinator_client,
    frozen_applicable_date,
) -> None:
    """Bundle present but registration failure must not block coordinators/sensors."""
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

    with (
        patch(
            "custom_components.high_school_sports_scores.frontend_register.card_bundle_available",
            return_value=True,
        ),
        patch(
            "custom_components.high_school_sports_scores.frontend_register._register_static_http_path",
            side_effect=ImportError("No module named 'hass_frontend'"),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is not None
    assert entry.runtime_data.data is not None


@pytest.mark.asyncio
async def test_domain_setup_succeeds_when_frontend_not_initialized(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Bundle present but frontend extras unset must not fail domain setup."""
    with (
        patch(
            "custom_components.high_school_sports_scores.frontend_register.card_bundle_available",
            return_value=True,
        ),
        patch(
            "custom_components.high_school_sports_scores.frontend_register._register_static_http_path",
            side_effect=KeyError("lovelace"),
        ),
    ):
        assert await async_setup(hass, {})


@pytest.mark.asyncio
async def test_config_entry_loads_when_frontend_not_initialized(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    coordinator_client,
    frozen_applicable_date,
) -> None:
    """Bundle present but frontend extras unset must not block coordinators/sensors."""
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

    with (
        patch(
            "custom_components.high_school_sports_scores.frontend_register.card_bundle_available",
            return_value=True,
        ),
        patch(
            "custom_components.high_school_sports_scores.frontend_register._register_static_http_path",
            side_effect=KeyError("lovelace"),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is not None
    assert entry.runtime_data.data is not None
