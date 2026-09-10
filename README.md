# High School Sports Scores for Home Assistant

A Home Assistant custom integration for exposing public high school sports schedules and results as native Home Assistant data.

## Status

**Phase 3 (complete; Layer 3 owner sandbox closed the completion gate on 2026-09-09):** A functioning Home Assistant custom integration backed by the Phase 2 MaxPreps Python client. One config entry per school; options subscriptions are `{sport, gender, level}`; one sensor per subscribed program with `unique_id` `{school_id}:{gender}:{level}:{sport}`. Entities never fetch — a `DataUpdateCoordinator` drives all network I/O through an injectable async transport.

**Applicable school year** is July 1 through June 30 in Home Assistant’s configured local timezone (for example `2026-07-01`–`2027-06-30` → `26-27`). The Slice 1 modal-year helper is leftover research evidence, not the production year rule.

**Polling** is conservative: about every 12 hours in normal operation; daily only while waiting for unpublished new-year schedules (Slice 11 rollover behavior).

Phase 3 is **not** a finished HACS release. The integration is developed and manually installable as a custom component; it is **not** published or listed in the HACS default store, and Phase 5 release packaging (`hacs.json`, store polish) has not been completed. Do not treat this as production-certified, HACS-store available, or feature-complete beyond what Phase 3 tests and documentation describe.

**Phase 4 (complete):** An optional custom Lovelace card (`custom:high-school-sports-scores-card`) lives in this repository under `frontend/`. It presents stacked last/next games from entity attributes and a full current-school-year schedule via an integration websocket when expanded or in schedule-only mode. **This is still not a HACS release** — the same Phase 3 backend install path applies, and the generated card bundle is **not** committed to git (see [Phase 4 packaging](#phase-4-lovelace-card-packaging) below).

See [docs/PHASE4_PLAN.md](docs/PHASE4_PLAN.md) for Phase 4 slice history, completion gate, and owner Layer 3 checklist.

**Phase 2 (complete):** fixture-driven MaxPreps client — school search, team enumeration, and head-to-head schedule decoding tested against committed fixtures only. Football and baseball share one contest parser; volleyball is regression evidence.

See [docs/PHASE3_PLAN.md](docs/PHASE3_PLAN.md) for slice breakdown, the §8 completion gate, and Implementation Notes. Phase 2 history: [docs/PHASE2_PLAN.md](docs/PHASE2_PLAN.md), [docs/PHASE2_PRODUCT_DRIFT.md](docs/PHASE2_PRODUCT_DRIFT.md).

### Known limitations

1. **Game dates and times:** Provider-supplied timezone-naive datetimes with unresolved timezone semantics. They are **not** reliable school-local or event-local wall times, and are **not** offset-correct kickoff timestamps. Do not assume state- or school-based timezone correction. The Lovelace card displays naive date/time strings without inventing a timezone.
2. **No live-score guarantee:** `contestState` live/in-progress values are not mapped. Compact entity state is `scheduled`, `final`, or `unknown` derived from last/next game objects on the last coordinator refresh (~12h, or daily during rollover wait). The optional Spike H observation script (`scripts/explore/observe_gameday.py`) is research-only and is not production polling.
3. **Supported formats only:** Evidence-based allowlist — Football, Baseball, Basketball, Volleyball. Unvalidated sports (tennis, golf, track, and others) are **omitted** from the subscription picker, not grayed out. Meet-sport schedules are not implemented.
4. **Q1 Team Tracker states:** `PRE` / `IN` / `POST` / `OFF` remain open. Compact entity state stays `scheduled` | `final` | `unknown`.

## Install (development / manual)

Copy or bind-mount this repository’s `custom_components/high_school_sports_scores` directory into your Home Assistant configuration tree at `custom_components/high_school_sports_scores`. See [docs/HA_DEVELOPMENT.md](docs/HA_DEVELOPMENT.md) for Core container setup, version pins, and test layers. This is **not** a HACS default-store install.

Keep Home Assistant configuration and secrets outside this git repository.

The Phase 3 backend (config flow, coordinators, program sensors) works from a fresh checkout **without** building the Lovelace card. The card is optional and requires a local frontend build (below).

## Phase 4 Lovelace card

### Packaging

- Frontend **source** is in this repository (`frontend/`).
- The built bundle (`custom_components/high_school_sports_scores/www/high-school-sports-scores-card.js`) is **gitignored** and intentionally **not committed** in Phase 4.
- **Developers must run `npm run build` locally** for the card to exist on disk.
- When the bundle is present, the integration registers it automatically at startup — no YAML Lovelace resource entry is normally required.
- When the bundle is absent, the integration logs a warning and skips frontend registration; config entries, coordinators, and sensors continue normally.
- **Phase 5** owns HACS release packaging and whether end users receive a pre-built bundle without running npm.

**Do not assume** that cloning this repository gives you a ready-to-use Lovelace card without building it.

### Adding the card to a dashboard

1. Build the bundle (see [Frontend development](#frontend-development) below) and restart or reload Home Assistant so registration runs.
2. Edit a Lovelace dashboard → **Add card** → choose **High School Sports Scores** from the card picker (suggested for program sensors).
3. Or add manually in YAML/raw config with type `custom:high-school-sports-scores-card` and configure `entity` (required) and optional `mode`.

### Card modes

| `mode` | Behavior |
|--------|----------|
| `both` (default) | Collapsed stacked last/next; click or Enter/Space to expand the full schedule; click again to collapse. |
| `last_next` | Collapsed last/next only; no schedule fetch or expand. |
| `schedule` | Full current-school-year schedule only (websocket); no collapsed last/next chrome. |

Collapsed last/next reads entity attributes only. Expanded and schedule-only views fetch the schedule DTO via `high_school_sports_scores/get_program_schedule` and subscribe to `high_school_sports_scores/subscribe_program_schedule_updates` for refresh while visible.

## Development

Source repository: https://github.com/willbur83/hacs-highschoolscores

Runtime development data and secrets are intentionally kept outside this repository.

### Frontend development

Requires Node.js and npm. From the repository root:

```bash
cd frontend
npm ci          # package-lock.json is committed — use npm ci for reproducible installs
npm test        # Vitest; no Home Assistant Core, zero live MaxPreps
npm run build   # writes gitignored custom_components/high_school_sports_scores/www/high-school-sports-scores-card.js
```

After building, the existing `custom_components/high_school_sports_scores` bind-mount is sufficient — no separate frontend mount. Restart Home Assistant (or reload the integration) so `frontend_register.py` picks up the bundle.

See [docs/HA_DEVELOPMENT.md](docs/HA_DEVELOPMENT.md) for frontend test details, missing-bundle behavior, and Layer 3 sandbox notes.

### Tests

**Layer 1 — client (Python ≥3.12, no Home Assistant):**

```bash
pip install -e ".[dev]"
pytest
python scripts/demo_client.py --fixtures
```

**Frontend unit (no Home Assistant, zero live MaxPreps):**

```bash
cd frontend && npm ci && npm test
```

**Layer 2 — integration (Python 3.14 + pinned Home Assistant; no live MaxPreps):**

```bash
pip install pytest-homeassistant-custom-component==0.13.362
pip install homeassistant==2026.9.0
pip install -e .
pytest tests/test_manifest.py tests/test_init.py tests/test_ha_transport.py \
  tests/test_config_flow.py tests/test_programs.py tests/test_coordinator.py \
  tests/test_sensor.py tests/test_options_flow.py tests/test_multi_school.py \
  tests/test_failure.py tests/test_rollover.py tests/test_websocket.py
```

See [docs/HA_DEVELOPMENT.md](docs/HA_DEVELOPMENT.md) for the canonical Layer 2 command, Core container bind-mount workflow, and why the two-step `pip` install is required.

## License

This project is licensed under the [MIT License](LICENSE). MIT applies to **this repository’s source code** only; it does **not** grant rights to MaxPreps content, trademarks, imagery, or other provider-owned material.
