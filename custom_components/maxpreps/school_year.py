"""Applicable school-year helpers (July 1–June 30, HA local timezone)."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def applicable_school_year(local_date: date) -> str:
    """Return the school-year label (``YY-YY``) for ``local_date``.

    School years run July 1 through June 30 in Home Assistant's configured
    local timezone. Examples:

    - ``2026-06-30`` → ``25-26``
    - ``2026-07-01`` → ``26-27``
    - ``2027-06-30`` → ``26-27``
    - ``2027-07-01`` → ``27-28``
    """
    if local_date.month >= 7:
        start_year = local_date.year % 100
        end_year = start_year + 1
    else:
        end_year = local_date.year % 100
        start_year = end_year - 1
    return f"{start_year:02d}-{end_year:02d}"


def homeassistant_local_date(hass: HomeAssistant) -> date:
    """Return today's date in Home Assistant's configured local timezone."""
    from homeassistant.util.dt import get_time_zone, now

    time_zone = get_time_zone(hass.config.time_zone)
    return now(time_zone).date()


__all__ = ["applicable_school_year", "homeassistant_local_date"]
