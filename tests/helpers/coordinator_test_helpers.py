"""Shared coordinator test helpers."""

from __future__ import annotations

from datetime import date

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.maxpreps.const import (
    CONF_CANONICAL_URL,
    CONF_NAME,
    CONF_SCHOOL_ID,
    CONF_SUBSCRIPTIONS,
    DOMAIN,
)
from tests.test_search import CENTENNIAL_ROSWELL_ID, CENTENNIAL_ROSWELL_URL

FROZEN_APPLICABLE_DATE = date(2026, 9, 2)


def centennial_entry(subscriptions: list[dict[str, str]]) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=CENTENNIAL_ROSWELL_ID,
        data={
            CONF_SCHOOL_ID: CENTENNIAL_ROSWELL_ID,
            CONF_CANONICAL_URL: CENTENNIAL_ROSWELL_URL,
            CONF_NAME: "Centennial",
        },
        options={CONF_SUBSCRIPTIONS: subscriptions},
    )
