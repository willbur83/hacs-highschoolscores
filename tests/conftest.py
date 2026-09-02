"""Shared pytest configuration."""

from __future__ import annotations

import importlib.util

if importlib.util.find_spec("pytest_homeassistant_custom_component") is not None:
    pytest_plugins = "pytest_homeassistant_custom_component"
