# High School Sports for Home Assistant

A Home Assistant custom integration for exposing public high school sports schedules and results as native Home Assistant data.

## Status

**Phase 2 (complete):** fixture-driven MaxPreps Python client in `custom_components/maxpreps/`. School search, team enumeration, and head-to-head schedule decoding are implemented and tested against committed fixtures only. Football and baseball share one contest parser; volleyball is a regression fixture.

**Not yet available:** Home Assistant integration, HACS install metadata, config flow, entities, cards, coordinators, or live MaxPreps HTTP polling. Game `date` values are timezone-naive local datetimes from the payload — not offset-correct kickoff times.

See [docs/PHASE2_PLAN.md](docs/PHASE2_PLAN.md) Implementation Notes and [docs/PHASE2_PRODUCT_DRIFT.md](docs/PHASE2_PRODUCT_DRIFT.md) for implementation vs product gaps awaiting owner review.

## Development

Source repository: https://github.com/willbur83/hacs-highschoolscores

Runtime development data and secrets are intentionally kept outside this repository.

### Tests

```bash
pip install -e ".[dev]"
pytest
python scripts/demo_client.py --fixtures
```

## License

TBD
