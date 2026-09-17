"""Lovelace card registration helpers and storage-mode resource wiring."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("homeassistant")

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant

from custom_components.high_school_sports_scores import async_setup
from custom_components.high_school_sports_scores.const import VERSION
from custom_components.high_school_sports_scores.frontend_register import (
    _lovelace_resource_mode,
    module_resource_url,
    picker_module_url,
    resource_path_from_url,
    resource_version_from_url,
)


def test_picker_module_url_includes_version() -> None:
    assert picker_module_url("0.1.0-beta.10") == (
        "/high_school_sports_scores/high-school-sports-scores-card.module.js?v=0.1.0-beta.10"
    )


def test_module_resource_url_includes_version() -> None:
    assert module_resource_url("0.1.0-beta.3") == (
        "/high_school_sports_scores/high-school-sports-scores-card.js?v=0.1.0-beta.3"
    )


def test_resource_url_parsing() -> None:
    url = module_resource_url("1.2.3")
    assert resource_path_from_url(url) == (
        "/high_school_sports_scores/high-school-sports-scores-card.js"
    )
    assert resource_version_from_url(url) == "1.2.3"
    assert resource_version_from_url(resource_path_from_url(url)) is None


def test_lovelace_resource_mode_uses_resource_mode_on_ha_2026_9() -> None:
    legacy = MagicMock()
    legacy.resource_mode = "storage"
    legacy.mode = "yaml"
    assert _lovelace_resource_mode(legacy) == "storage"

    older = MagicMock(spec=[])
    older.mode = "storage"
    assert _lovelace_resource_mode(older) == "storage"


@pytest.mark.asyncio
async def test_async_setup_waits_for_lovelace_storage_mode(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Registration waits until Lovelace mode is storage, not only until hass.data exists."""
    mock_resources = MagicMock()
    mock_resources.loaded = True
    mock_resources.async_items.return_value = []
    mock_resources.async_create_item = AsyncMock()

    mock_lovelace = MagicMock()
    mock_lovelace.resources = mock_resources
    mode_values = iter([None, "storage"])
    type(mock_lovelace).resource_mode = property(lambda _self: next(mode_values))
    hass.data["lovelace"] = mock_lovelace

    with (
        patch(
            "custom_components.high_school_sports_scores.frontend_register.card_bundle_available",
            return_value=True,
        ),
        patch(
            "custom_components.high_school_sports_scores.frontend_register._register_static_http_path",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.high_school_sports_scores.frontend_register._LOVELACE_RESOURCE_RETRY_SECONDS",
            0,
        ),
    ):
        assert await async_setup(hass, {})
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()

    mock_resources.async_create_item.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_setup_creates_lovelace_module_resource(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Storage-mode Lovelace gets IIFE js resource plus ES module picker bootstrap."""
    mock_resources = MagicMock()
    mock_resources.loaded = True
    mock_resources.async_items.return_value = []
    mock_resources.async_create_item = AsyncMock()
    mock_resources.async_update_item = AsyncMock()

    mock_lovelace = MagicMock()
    mock_lovelace.resource_mode = "storage"
    mock_lovelace.resources = mock_resources
    hass.data["lovelace"] = mock_lovelace

    with (
        patch(
            "custom_components.high_school_sports_scores.frontend_register.card_bundle_available",
            return_value=True,
        ),
        patch(
            "custom_components.high_school_sports_scores.frontend_register._register_static_http_path",
            new_callable=AsyncMock,
        ),
        patch(
            "homeassistant.components.frontend.add_extra_js_url",
        ) as mock_extra_js,
    ):
        assert await async_setup(hass, {})
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()

    mock_resources.async_create_item.assert_awaited_once_with(
        {
            "res_type": "js",
            "url": module_resource_url(VERSION),
        }
    )
    mock_extra_js.assert_called_once_with(hass, picker_module_url(VERSION), es5=False)


@pytest.mark.asyncio
async def test_async_setup_updates_lovelace_resource_when_version_changes(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Existing integration resource row is updated when manifest version changes."""
    existing_id = "abc123"
    mock_resources = MagicMock()
    mock_resources.loaded = True
    mock_resources.async_items.return_value = [
        {
            "id": existing_id,
            "url": module_resource_url("0.1.0-beta.1"),
            "res_type": "js",
        }
    ]
    mock_resources.async_create_item = AsyncMock()
    mock_resources.async_update_item = AsyncMock()

    mock_lovelace = MagicMock()
    mock_lovelace.resource_mode = "storage"
    mock_lovelace.resources = mock_resources
    hass.data["lovelace"] = mock_lovelace

    with (
        patch(
            "custom_components.high_school_sports_scores.frontend_register.card_bundle_available",
            return_value=True,
        ),
        patch(
            "custom_components.high_school_sports_scores.frontend_register._register_static_http_path",
            new_callable=AsyncMock,
        ),
    ):
        assert await async_setup(hass, {})
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()

    mock_resources.async_create_item.assert_not_called()
    mock_resources.async_update_item.assert_awaited_once_with(
        existing_id,
        {
            "res_type": "js",
            "url": module_resource_url(VERSION),
        },
    )
