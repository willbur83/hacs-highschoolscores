# Home Assistant development

This document describes how to develop and test the MaxPreps custom integration using the official Home Assistant Core container and the repository's split Python extras.

## Version pins

| Component | Pin | Notes |
|-----------|-----|-------|
| Home Assistant Core (container) | `ghcr.io/home-assistant/home-assistant:2026.9.0` | Stable Core image tag matching the Python test pin |
| `homeassistant` (Python package) | `2026.9.0` | Installed via the `[ha]` extra in `pyproject.toml` |
| `pytest-homeassistant-custom-component` | `0.13.362` | Closest published match; upgrade when a release pins `homeassistant==2026.9.0` |
| Client / fixture tests | Python `>=3.12` | `[dev]` extra; no Home Assistant import required |
| HA integration tests | Python `>=3.14` | Required by Home Assistant 2026.9.x |

The Phase 2 MaxPreps client remains runnable on Python 3.12+. Home Assistant 2026.x requires Python 3.14.2 or newer; use a Python 3.14 environment (or the Core container) for `[ha]` tests and manual UI work.

## Test layers

### Layer 1 — client (no Home Assistant)

```bash
pip install -e ".[dev]"
pytest
python scripts/demo_client.py --fixtures
```

These tests exercise parsers, models, and `MaxPrepsClient` with `FixtureTransport` only. They must pass without installing the `[ha]` extra.

### Layer 2 — integration smoke (Home Assistant, no live MaxPreps)

```bash
pip install pytest-homeassistant-custom-component==0.13.362
pip install homeassistant==2026.9.0
pip install -e .
pytest tests/test_manifest.py tests/test_init.py
```

Smoke tests verify `manifest.json`, `DOMAIN`, and that the integration loads and unloads via `enable_custom_integrations` with no network I/O.

`pytest-homeassistant-custom-component` may trail the monthly stable `homeassistant` release by a few hours. Until a phacc release pins `2026.9.0`, install phacc first, then upgrade `homeassistant` to the stable pin above (pip cannot resolve both in one step yet). When phacc catches up, `pip install -e ".[ha]"` should work as a single command.

## Core container and bind mount

Use the official Home Assistant Core container (not HAOS). Bind-mount this repository's `custom_components/maxpreps` directory into the container config tree:

| Host path (your checkout) | Container path |
|---------------------------|----------------|
| `<checkout>/custom_components/maxpreps` | `/config/custom_components/maxpreps` |

Keep persistent Home Assistant configuration and secrets **outside** this git repository. Operator compose files, host ports, and machine-specific paths belong in unpublished operator notes — not in committed documentation.

Recommended container settings:

- Image: `ghcr.io/home-assistant/home-assistant:2026.9.0`
- Publish UI port `8123` to a host port of your choice
- Use explicit bind mounts only (no anonymous or named volumes for config)
- Do not use GPU passthrough
- Do not `chmod 777` config directories

Enable custom integrations in the container configuration when loading unpublished components from the bind mount (for example `homeassistant:` → `customize:` is not required; use the developer/custom-integration settings appropriate to your Core version).

After the container starts, confirm Home Assistant discovers and loads the custom integration without import or manifest errors (check the Core log for the expected custom-integration warning). Slice 0 does not implement school search or entity setup; the config flow deliberately aborts as `not_implemented`.

## What Slice 0 does not include

- Config flow product logic (school search, team selection)
- Coordinator, entities, sensors, or live MaxPreps HTTP
- HACS metadata (`hacs.json`) or a Lovelace card

See [docs/PHASE3_PLAN.md](PHASE3_PLAN.md) for the full Phase 3 slice breakdown.
