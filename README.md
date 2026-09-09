# High School Sports for Home Assistant

A Home Assistant custom integration for exposing public high school sports schedules and results as native Home Assistant data.

## Status

**Phase 3 (complete; Layer 3 owner sandbox closed the completion gate on 2026-09-09):** A functioning Home Assistant custom integration backed by the Phase 2 MaxPreps Python client. One config entry per school; options subscriptions are `{sport, gender, level}`; one sensor per subscribed program with `unique_id` `{school_id}:{gender}:{level}:{sport}`. Entities never fetch — a `DataUpdateCoordinator` drives all network I/O through an injectable async transport.

**Applicable school year** is July 1 through June 30 in Home Assistant’s configured local timezone (for example `2026-07-01`–`2027-06-30` → `26-27`). The Slice 1 modal-year helper is leftover research evidence, not the production year rule.

**Polling** is conservative: about every 12 hours in normal operation; daily only while waiting for unpublished new-year schedules (Slice 11 rollover behavior).

Phase 3 is **not** a finished HACS release. The integration is developed and manually installable as a custom component; it is **not** published or listed in the HACS default store, and Phase 5 release packaging (`hacs.json`, store polish) has not been completed. Do not treat this as production-certified, HACS-store available, or feature-complete beyond what Phase 3 tests and documentation describe.

**Phase 2 (complete):** fixture-driven MaxPreps client — school search, team enumeration, and head-to-head schedule decoding tested against committed fixtures only. Football and baseball share one contest parser; volleyball is regression evidence.

See [docs/PHASE3_PLAN.md](docs/PHASE3_PLAN.md) for slice breakdown, the §8 completion gate, and Implementation Notes. Phase 2 history: [docs/PHASE2_PLAN.md](docs/PHASE2_PLAN.md), [docs/PHASE2_PRODUCT_DRIFT.md](docs/PHASE2_PRODUCT_DRIFT.md).

### Known limitations

1. **Game dates and times:** Provider-supplied timezone-naive datetimes with unresolved timezone semantics. They are **not** reliable school-local or event-local wall times, and are **not** offset-correct kickoff timestamps. Do not assume state- or school-based timezone correction.
2. **No live-score guarantee:** `contestState` live/in-progress values are not mapped. Compact entity state is `scheduled`, `final`, or `unknown` derived from last/next game objects on the last coordinator refresh (~12h, or daily during rollover wait). The optional Spike H observation script (`scripts/explore/observe_gameday.py`) is research-only and is not production polling.
3. **Supported formats only:** Evidence-based allowlist — Football, Baseball, Basketball, Volleyball. Unvalidated sports (tennis, golf, track, and others) are **omitted** from the subscription picker, not grayed out. Meet-sport schedules are not implemented.

## Install (development / manual)

Copy or bind-mount this repository’s `custom_components/maxpreps` directory into your Home Assistant configuration tree at `custom_components/maxpreps`. See [docs/HA_DEVELOPMENT.md](docs/HA_DEVELOPMENT.md) for Core container setup, version pins, and test layers. This is **not** a HACS default-store install.

Keep Home Assistant configuration and secrets outside this git repository.

## Development

Source repository: https://github.com/willbur83/hacs-highschoolscores

Runtime development data and secrets are intentionally kept outside this repository.

### Tests

**Layer 1 — client (Python ≥3.12, no Home Assistant):**

```bash
pip install -e ".[dev]"
pytest
python scripts/demo_client.py --fixtures
```

**Layer 2 — integration (Python 3.14 + pinned Home Assistant; no live MaxPreps):**

```bash
pip install pytest-homeassistant-custom-component==0.13.362
pip install homeassistant==2026.9.0
pip install -e .
pytest tests/test_manifest.py tests/test_init.py tests/test_ha_transport.py \
  tests/test_config_flow.py tests/test_programs.py tests/test_coordinator.py \
  tests/test_sensor.py tests/test_options_flow.py tests/test_multi_school.py \
  tests/test_failure.py tests/test_rollover.py
```

See [docs/HA_DEVELOPMENT.md](docs/HA_DEVELOPMENT.md) for the canonical Layer 2 command, Core container bind-mount workflow, and why the two-step `pip` install is required.

## License

TBD
