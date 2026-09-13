"""Lovelace card registration helpers and storage-mode resource wiring."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("homeassistant")

from homeassistant.core import HomeAssistant

from custom_components.high_school_sports_scores import async_setup
from custom_components.high_school_sports_scores.const import VERSION
from custom_components.high_school_sports_scores.frontend_register import (
    module_resource_url,
    resource_path_from_url,
    resource_version_from_url,
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


@pytest.mark.asyncio
async def test_async_setup_creates_lovelace_module_resource(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Storage-mode Lovelace gets a versioned module resource; no add_extra_js_url."""
    mock_resources = MagicMock()
    mock_resources.loaded = True
    mock_resources.async_items.return_value = []
    mock_resources.async_create_item = AsyncMock()
    mock_resources.async_update_item = AsyncMock()

    mock_lovelace = MagicMock()
    mock_lovelace.mode = "storage"
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

    mock_resources.async_create_item.assert_awaited_once_with(
        {
            "res_type": "module",
            "url": module_resource_url(VERSION),
        }
    )
    mock_extra_js.assert_not_called()


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
            "res_type": "module",
        }
    ]
    mock_resources.async_create_item = AsyncMock()
    mock_resources.async_update_item = AsyncMock()

    mock_lovelace = MagicMock()
    mock_lovelace.mode = "storage"
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

    mock_resources.async_create_item.assert_not_called()
    mock_resources.async_update_item.assert_awaited_once_with(
        existing_id,
        {
            "res_type": "module",
            "url": module_resource_url(VERSION),
        },
    )
