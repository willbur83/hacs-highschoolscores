# MaxPreps test fixtures

Committed fixtures contain **sanitized public MaxPreps page data only**. Strip cookies, Authorization headers, tokens, Set-Cookie headers, local paths, IP addresses, machine names, and personal information before committing. Do not include rosters, player stats, or athlete pages unless a research slice explicitly requires them.

## Naming

```
<school>/<page>-<season>.json
<school>/<page>-<season>.html
```

Example: `centennial/schedule-2025.json`

Private raw captures belong in `captures/private/` (gitignored) and are never committed.
