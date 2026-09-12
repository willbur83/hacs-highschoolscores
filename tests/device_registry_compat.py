"""Device registry lookups compatible with HA 2025.8+ and 2026.9+ test harnesses."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.helpers import device_registry as dr


def async_get_device_for_config_entry(
    device_registry: dr.DeviceRegistry,
    identifier: tuple[str, str],
    config_entry_id: str,
) -> dr.DeviceEntry | None:
    """Return the device for ``identifier`` owned by ``config_entry_id``.

    Home Assistant 2026.9+ exposes ``async_get_device_by_identifier``; 2025.8 uses
    ``async_get_device`` plus a config-entry membership check. Integration runtime
    does not call either API — this helper is Layer 2 test compatibility only.
    """
    by_identifier = getattr(
        device_registry, "async_get_device_by_identifier", None
    )
    if by_identifier is not None:
        return by_identifier(identifier, config_entry_id)

    device = device_registry.async_get_device(identifiers={identifier})
    if device is None or config_entry_id not in device.config_entries:
        return None
    return device
