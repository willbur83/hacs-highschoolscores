# High School Sports for Home Assistant

A Home Assistant custom integration for exposing public high school sports schedules and results as native Home Assistant data.

## Status

Early feasibility and data-source exploration.

Initial engineering work is focused on understanding and normalizing the public MaxPreps data model before building the Home Assistant integration layer.

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
