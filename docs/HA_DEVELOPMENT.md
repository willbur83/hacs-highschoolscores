# Home Assistant development

This document describes how to develop and test the High School Sports Scores custom integration using the official Home Assistant Core container and the repository's split Python extras.

## CI validation

GitHub Actions ([`.github/workflows/validate.yml`](../.github/workflows/validate.yml)) reproduces the same commands documented below — not a parallel test stack:

| Job | Command |
|-----|---------|
| Layer 1 | `pip install -e ".[dev]"` then `pytest` (Python 3.12; HA modules skip as on host) |
| Frontend | `cd frontend && npm ci && npm test` |
| Layer 2 | `ghcr.io/home-assistant/home-assistant:2026.9.0` container with the two-step phacc + `homeassistant==2026.9.0` install and the canonical pytest file list |
| Packaging dry-run | `cd frontend && npm ci && npm run build`, then `scripts/ci/pack_release_zip.sh` + `scripts/ci/assert_release_zip.sh` |
| hassfest / HACS | `home-assistant/actions/hassfest@master` and `hacs/action@main` (`category: integration`, no ignores) |

Version-syntax evidence for the first beta tag ↔ manifest mapping is in [PHASE5_PLAN.md](PHASE5_PLAN.md) Slice 3 Implementation Notes and re-checked by `tests/test_version_mapping.py`.

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

These tests exercise parsers, models, `MaxPrepsClient`, school-logo helpers, schedule DTO serialization (`tests/test_schedule_payload.py`), and the Spike H observation script with `FixtureTransport` / mocks only. They must pass without installing the `[ha]` extra. HA-dependent modules are skipped when `homeassistant` is not importable.

### Frontend unit (no Home Assistant)

Phase 4 Lovelace card tests run with Vitest only — zero Home Assistant Core, zero live MaxPreps HTTP:

```bash
cd frontend
npm ci    # package-lock.json is committed
npm test
```

Build output (gitignored):

```bash
cd frontend && npm run build
```

Writes `custom_components/high_school_sports_scores/www/high-school-sports-scores-card.js`. The existing `custom_components/high_school_sports_scores` bind-mount is enough when that file is present; no separate frontend mount.

**Missing bundle (non-fatal):** `frontend_register.py` checks for the built file at startup. If absent, it logs a warning and skips `StaticPathConfig` + `frontend.add_extra_js_url`. Config entries, coordinators, and sensors load normally. Layer 2 tests in `tests/test_init.py` cover missing-bundle and registration-unavailable paths. The integration does **not** declare `frontend` / `http` manifest dependencies (avoids `hass_frontend` import failures under `pytest-homeassistant-custom-component`).

### Layer 2 — integration (Home Assistant, no live MaxPreps)

Install pins (two-step until phacc matches stable):

```bash
pip install pytest-homeassistant-custom-component==0.13.362
pip install homeassistant==2026.9.0
pip install -e .
```

Canonical Layer 2 command (fixture/mock transport only; zero live MaxPreps HTTP):

```bash
pytest tests/test_manifest.py tests/test_init.py tests/test_ha_transport.py \
  tests/test_config_flow.py tests/test_programs.py tests/test_coordinator.py \
  tests/test_sensor.py tests/test_options_flow.py tests/test_multi_school.py \
  tests/test_failure.py tests/test_rollover.py tests/test_websocket.py
```

This is the command used in Phase 3 and Phase 4 Implementation Notes. Individual file names document the current HA-dependent suites; new Layer 2 modules should be added to this invocation when they require `homeassistant`. When phacc catches up to stable, `pip install -e ".[ha]"` may work as a single command.

**Current Layer 2 modules and what they cover:**

| Module | Coverage (summary) |
|--------|-------------------|
| `test_manifest.py` | `manifest.json` keys; `VERSION` sync |
| `test_init.py` | Domain load/unload smoke; **missing built card bundle** (integration still loads); **bundle present but frontend/http registration unavailable** |
| `test_ha_transport.py` | HA shared-session async transport factory |
| `test_config_flow.py` | School search, subscriptions, duplicate abort, allowlist picker |
| `test_programs.py` | Program grouping, aggregated labels, subscription keys |
| `test_coordinator.py` | Coordinator refresh, per-term isolation, applicable school year |
| `test_sensor.py` | Device/entity wiring, compact state, last/next attributes, logos on entities |
| `test_options_flow.py` | Add/remove subscriptions, logo override (`school_logo_override`) |
| `test_multi_school.py` | Multiple config entries, coordinator isolation, unload isolation |
| `test_failure.py` | Entry-wide vs per-program failure, reload, last-good retention |
| `test_rollover.py` | July 1 school-year rollover, daily-until-published interval, stable `unique_id` |
| `test_websocket.py` | Registry-owned `high_school_sports_scores/get_program_schedule` DTO; `high_school_sports_scores/subscribe_program_schedule_updates` notify |

Layer 1-only HA-adjacent tests (not in the Layer 2 command): `test_schedule_payload.py` (pure schedule DTO serializer), `test_school_logo.py` (logo resolution helpers), `test_observe_gameday.py` (Spike H observation script gates).

`pytest-homeassistant-custom-component` may trail the monthly stable `homeassistant` release by a few hours. Until a phacc release pins `2026.9.0`, install phacc first, then upgrade `homeassistant` to the stable pin above (pip may report a version conflict warning; the two-step install is intentional).

### Layer 3 — manual HA sandbox

Owner-operated Home Assistant Core instance with bind-mounted `custom_components/high_school_sports_scores`. Real UI clicks (config flow, options, entity states) and optional live MaxPreps traffic for search/logo checks belong here — never in CI.

**Owner Layer 3 verification (2026-09-09) — Phase 3 gate closed.** Home Assistant Core 2026.9.0 sandbox passed:

- Live config flow (short-name search → school → allowlisted program)
- Options flow add/remove sport (remaining program entity identity unchanged)
- Two schools as independent config entries and devices
- Reload isolation (reloading one school did not disturb the other)
- Duplicate-school rejection
- Automatic `entity_picture` from the provider school logo

Removed-program entities may remain in the Home Assistant entity registry as unavailable; that is registry behavior, not a failed unsubscribe.

See [docs/PHASE3_PLAN.md](PHASE3_PLAN.md) Implementation Notes (Slice 13 and the owner Layer 3 gate closure) for the Phase 3 completion-gate record.

**Owner Layer 3 verification (2026-09-09) — Phase 4 gate closed.** Home Assistant Core 2026.9.0 sandbox passed:

- YAML-free JS load when a local build exists (`/high_school_sports_scores/high-school-sports-scores-card.js` HTTP 200, card picker after `window.customCards` type fix)
- Collapsed stacked last/next with hero/secondary relevance
- Whole-card expand/collapse for `mode: both` with full schedule table
- Expanded card receives `schedule_updated` notify and refetches DTO after coordinator refresh that does not change last/next
- Explicit `mode: last_next` and `mode: schedule` owner checks
- Light theme, dark theme, and narrow/mobile layout

Stale/rollover notice appearance is deferred and non-blocking (implemented in code; owner visual not required for gate closure). Build the card bundle (`cd frontend && npm ci && npm run build`) before card picker testing.

See [docs/PHASE4_PLAN.md](PHASE4_PLAN.md) Implementation Notes (Slice 6 owner Layer 3 checklist) for the Phase 4 completion-gate record.

## Core container and bind mount

Use the official Home Assistant Core container (not HAOS). Bind-mount this repository's `custom_components/high_school_sports_scores` directory into the container config tree:

| Host path (your checkout) | Container path |
|---------------------------|----------------|
| `<checkout>/custom_components/high_school_sports_scores` | `/config/custom_components/high_school_sports_scores` |

Keep persistent Home Assistant configuration and secrets **outside** this git repository. Operator compose files, host ports, and machine-specific paths belong in unpublished operator notes — not in committed documentation.

Recommended container settings:

- Image: `ghcr.io/home-assistant/home-assistant:2026.9.0`
- Publish UI port `8123` to a host port of your choice
- Use explicit bind mounts only (no anonymous or named volumes for config)
- Do not use GPU passthrough
- Do not `chmod 777` config directories

Enable custom integrations in the container configuration when loading unpublished components from the bind mount.

After the container starts, add the integration through **Settings → Devices & services → Add integration → High School Sports Scores**. Config flow supports school search and sport subscription; options flow supports add/remove subscriptions and an optional school logo override (HTTPS URL or `/local/` path). Confirm entities appear for subscribed programs and check the Core log for import or manifest errors.

To use the Phase 4 Lovelace card, build `frontend/` first so `custom_components/high_school_sports_scores/www/high-school-sports-scores-card.js` exists inside the bind mount, then add the card from the Lovelace card picker or with type `custom:high-school-sports-scores-card`.

## Phase 3 scope reference

Implemented in Phase 3: config flow, options flow, coordinator, program sensors, multi-school entries, failure isolation, school-year rollover polling, configured-school logos (automatic + user override), production async transport. Owner Layer 3 sandbox verification closed the Phase 3 completion gate on 2026-09-09.

Not in Phase 3: HACS metadata (`hacs.json`), live-score mapping, tennis/golf/track schedules, YAML configuration. Phase 3 did not include a Lovelace card; **Phase 4** added the optional `custom:high-school-sports-scores-card` (requires a local frontend build; bundle not committed).

See [docs/PHASE3_PLAN.md](PHASE3_PLAN.md) for the full slice breakdown, §8 completion gate, and owner Layer 3 gate closure. See [docs/PHASE4_PLAN.md](PHASE4_PLAN.md) for the custom card, websocket schedule DTO, and Phase 4 completion gate closure (2026-09-09).
