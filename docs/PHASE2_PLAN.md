# Phase 2 implementation record

This file is the living implementation log for Phase 2. The approved plan is **Phase 2 Slice 0–12 as written**. Do not treat this document as a restatement of that architecture. Slice 1 may land fuller plan text later.

---

## Implementation Notes — Slice 0 (fixture acquisition)

### What was captured

- **Acceptance:** one sanitized Centennial Boys Varsity Baseball schedule fixture from a single live GET of the payload `canonicalUrl` + established `schedule/` child:
  `https://www.maxpreps.com/ga/roswell/centennial-knights/baseball/schedule/`
  (`sportSeasonId` `0e872276-ae3c-4868-8b66-cb53e9727cfb` from `tests/fixtures/maxpreps/centennial/sport-seasons-26-27.json`; URL not reconstructed; not fetched by `ssid`).
- **Optional extra coverage:** Centennial Girls Varsity Basketball schedule fixture promoted from the Slice 14 private cache (`captures/private/www.maxpreps.com/a89b0d585a1ebd0c.*`) with **zero new live requests**.
- Softball, boys basketball, other schools, and additional sports were not fetched.
- No MaxPreps client, parsers, models, HA integration, or tests beyond inspecting the captured JSON.

### Decisions

- Baseball was not in the private cache (`8f65b1d976c5408b` absent), so one live GET via `scripts/explore/capture.py` was required.
- Slice 14 girls basketball cache still existed, so it was sanitized and committed without a live refetch.
- Fixture envelope matches `tests/fixtures/maxpreps/centennial/schedule-26-27.json`: `description`, `source_url`, `captured_at`, `status_code`, `content_type`, `transport`, `buildId`, `page`, `query`, `pageProps`.
- `query` recorded from `__NEXT_DATA__.query` (present). `pageProps.query` key was absent — not invented, not recorded as `null`.
- Raw HTML stays in gitignored `captures/private/`; committed fixtures contain sanitized `pageProps` JSON only.

### Exact commands

Git protocol check (passed: `origin` is `https://github.com/willbur83/hacs-highschoolscores.git`; `main` tracks `origin/main`):

```
git remote -v && git status -sb && git branch -vv
```

Live baseball capture (existing User-Agent `hacs-highschoolscores-explore/0.1`; no cookies/auth; `capture.py` sleeps ≥2s on cache miss). Stdout was piped through a local inspector that dropped `body` from the terminal dump; `capture.py` still wrote the full private cache:

```
python3 scripts/explore/capture.py "https://www.maxpreps.com/ga/roswell/centennial-knights/baseball/schedule/" --slice "phase2-0" --notes "Centennial Boys Varsity Baseball schedule HTML; Phase 2 Slice 0 fixture acquisition"
```

Private cache written: `captures/private/www.maxpreps.com/8f65b1d976c5408b.{raw,json}` (`cache: miss`, status 200, 383386 bytes).

Basketball: no `capture.py` invocation. Fixture extracted from existing `captures/private/www.maxpreps.com/a89b0d585a1ebd0c.json`.

Fixture extraction was a one-off local Python inspect/`__NEXT_DATA__` parse (not committed as client code): regex `<script id="__NEXT_DATA__"[^>]*>…</script>`, envelope + redaction of IPs/local paths/emails, write:

- `tests/fixtures/maxpreps/centennial/baseball-schedule-26-27.json`
- `tests/fixtures/maxpreps/centennial/basketball-girls-schedule-26-27.json`

### Test/inspection results

| Check | Baseball | Girls basketball (promoted) |
|-------|----------|-----------------------------|
| HTTP status | 200 | 200 (cached) |
| Challenge / 403 / 429 | None | n/a (no live GET) |
| `__NEXT_DATA__` | Present | Present |
| `contests[]` | Present, length **30** | Present, length **6** |
| `len(row)` | **41** (all rows) | **41** (all rows) |
| `len(row[0][0])` / `len(row[0][1])` | **32** / **32** | **32** / **32** |
| `featuredGameData` | Present | Present |

**Pass/stop verdict:** **Pass.** Baseball is the second-sport parser fixture (Next.js `contests[]` with ≥1 row, arity 41, two participants width 32). Later slices may use it. Basketball is extra coverage only, not a substitute for baseball.

### Deviations

- `capture.py` full JSON (including HTML `body`) was not printed to the terminal; private cache files are complete.
- Optional basketball was promoted from Slice 14 cache rather than captured live (allowed; cache still present).
- `buildId` retained a trailing newline from the `__NEXT_DATA__` blob (`7e0e0dba-22c4d787\n`), same class of artifact as the volleyball Slice 14 fixture.
- Research artifacts that were still untracked (`docs/MAXPREPS_RESEARCH.md`, `scripts/`, `tests/fixtures/`) are included in this slice’s commit as continuation of this repo.

### PRODUCT.md drift check

Slice 0 did **not** change product behavior and did **not** edit `docs/PRODUCT.md`. PRODUCT.md still lists baseball as an example entity / exploration sport / Layer 1 fixture name, but has no baseball-specific schedule or parser text. That gap is not a reason to edit PRODUCT.md in this slice.
