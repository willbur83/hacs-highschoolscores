# Phase 3

This file has two parts:

1. **Approved plan** — the Phase 3 plan as approved after planning review, **plus owner amendments dated 2026-09-02 (post-Slice 4)** that supersede earlier open questions on subscription identity, multi-term programs, picker labels, and school-year rollover. Remaining slices follow the amended plan.
2. **Implementation Notes** — what completed slices actually did. Do not rewrite historical notes as though later owner decisions existed at the time. Differences from the then-current plan belong there.

Do not treat Implementation Notes as amendments to the approved plan.
Do not rewrite historical Phase 2 notes in [docs/PHASE2_PLAN.md](PHASE2_PLAN.md).

### Owner amendments (2026-09-02, post-Slice 4)

These decisions supersede Q2, the “no wall-clock cohort” constraint, singular “resolve one TeamSeason per subscription,” and any “omit or pick one term when keys collide” behavior.

- **Subscription identity** is the school-year program `{sport, gender, level}` (plus the school config entry). Do not persist `season`, `sport_season_id`, `all_season_id`, year, or team-season `canonical_url` as subscription identity. `all_season_id` may be provider matching metadata only.
- **Multiple MaxPreps terms in one school year are one subscription.** Example: Centennial Boys Freshman Baseball Fall 26-27 and Spring 26-27 (distinct `sportSeasonId` / `canonicalUrl`, same `allSeasonId`) are one program. Do not omit the program, do not pick one term, do not expose a term picker, do not create separate Fall/Spring subscriptions.
- A subscription **resolves to one or more** current-school-year `TeamSeason` rows matching `{sport, gender, level}`. Coordinator and later UI must not assume one row / one schedule URL.
- **Picker labels** show informational term(s) and school year, e.g. `Boys Varsity Football (Fall 26-27)`, `Boys Freshman Baseball (Fall, Spring 26-27)`. The parenthetical is not a filter. Build aggregated labels in the config/options flow; do not globally change `TeamSeason.display_label` unless a later slice proves that is the model-level behavior.
- **Term order** in labels: Fall, Winter, Spring, Summer, then any unknown term names sorted case-insensitive. This is conventional US school-year order, not a sport→season table.
- **Runtime:** gather every matching `TeamSeason` for the applicable school year and fetch each term’s schedule. Preserve term/source internally so a later expanded view can section Fall / Spring. Do not flatten away term distinction. Do not build the card in Slice 5.
- **Applicable school year** is a wall-clock product rule: **July 1 through June 30** in Home Assistant’s configured local timezone (`2026-07-01`–`2027-06-30` → `26-27`). This supersedes the earlier ban on any wall-clock current-cohort rule. Distinguish (1) applicable school year, (2) provider rows present for that year, (3) whether those schedules are published. Do not invent a schedule because the calendar rolled over.
- **Rollover:** subscriptions survive without reconfiguration. Re-resolve the same `{sport, gender, level}` against the new year’s rows. Until new-year schedules exist, keep prior data and check conservatively (daily is acceptable) then return to ~12h polling. Slice 11 owns the daily-until-published behavior; Slice 5 must not destroy last-good data when the new year is unpublished.
- **Scope unchanged:** evidence-based allowlist; no historical browsing, term picker, meet sports, live scores, YAML, or pasted provider IDs.

---

# Phase 3 — Home Assistant custom integration

## 1. Phase objective and completion criteria

**Objective:** Turn the completed Phase 2 MaxPreps Python client into a functioning Home Assistant custom integration so that a user can:

1. Install and configure it through the normal Home Assistant UI (no YAML).
2. Search for a school using short-name search and pick the intended school from disambiguated results.
3. Configure multiple schools (one Add Integration action per school is acceptable).
4. Subscribe each school to one or more supported head-to-head team sports through HA-native configuration/options UX.
5. Receive stable current-season schedule/result data through HA entities backed by a production async transport and a coordinator.

Football and baseball are the intended Phase 3 acceptance targets. Do **not** preemptively narrow to football-only. If live-validation or implementation evidence shows baseball (or another intended head-to-head sport) needs materially different behavior, stop and report to the product owner.

This is backend/integration functionality. A polished custom Lovelace card belongs to Phase 4. Phase 3 must expose a clean enough HA data contract that the future last-game / next-game card is straightforward.

This is **not**:

- a historical MaxPreps browser
- tennis/golf/track schedule implementation
- HACS/public-release polish (Phase 5), except the minimum `manifest.json` / translations required for a custom component to load
- live-score guarantees, invented timezone correctness, or aggressive polling

**Phase 3 is complete when the completion gate in section 8 is satisfied.** Do not mark that gate completed in this planning document.

---

## 2. Authority and baseline

Treat these as authorities, in this order:

| Authority | Role |
|-----------|------|
| [docs/PRODUCT.md](PRODUCT.md) | Product behavior, except where the completed Phase 2 owner-review drift disposition supersedes stale wording |
| [docs/PHASE2_PRODUCT_DRIFT.md](PHASE2_PRODUCT_DRIFT.md) owner review | Explicitly supersedes PRODUCT search-example and `team_id` client sketches; leaves timezone, HA lifecycle, cohort/rollover, and unsupported-sport UI open |
| [docs/MAXPREPS_RESEARCH.md](MAXPREPS_RESEARCH.md) | Empirical MaxPreps behavior |
| Completed Phase 2 code and tests | Technical evidence of the client that Phase 3 must wrap |
| This plan | Phase 3 implementation intent |

**Do not invent product behavior to resolve ambiguity.** Surface those questions in section 6.

### 2.1 What actually landed in Phase 2

Public GitHub repo `https://github.com/willbur83/hacs-highschoolscores` (`main` tracks `origin/main`).

Delivered:

```
MaxPreps SSR pages
    → Next.js extraction
    → search / sportSeasons / contest parsers
    → School / TeamSeason / Game / Schedule
    → MaxPrepsClient
    → fixture-driven cross-school golden tests
```

Package: `custom_components/maxpreps/` — HA-free client (no `manifest.json`, config flow, coordinator, entities, or HACS metadata).

Standing invariants that Phase 3 must not casually replace:

- School identity is `school_id`.
- Selected team-season identity is `(school_id, sport_season_id)`; `sport_season_id` is not a globally unique team key.
- Payload `canonical_url` is authoritative; do not reconstruct provider URL grammar.
- Schedule fetch uses only the established safe `schedule/` child join.
- `get_school_teams` returns **all** `sportSeasons[]` rows; Phase 2 did not implement current-season filtering.
- `contests[]` is authoritative schedule data; `featuredGameData` is optional validation/consistency evidence.
- Participant identity/orientation comes from `row[0]` participant data; `row[37]` / `row[38]` are score views only.
- `Game.date` remains timezone-naive.
- Unknown contest states remain `unknown`.
- Missing `__NEXT_DATA__` is `NextDataNotFoundError` (not an ASPX/legacy classifier).
- No production live HTTP transport exists yet.
- Phase 2 CI/tests make zero live MaxPreps requests.
- Football and baseball passed the shared head-to-head parser acceptance gate.
- Volleyball is regression evidence only.
- Generic team enumeration includes other sports/formats; tennis/golf/track schedule decoding is unsupported/deferred.

Client API (drift-confirmed; do not revive PRODUCT §10 `team_id` sketches):

- `search_schools(query: str) -> list[School]`
- `get_school_teams(school: School) -> list[TeamSeason]`
- `get_schedule(team: TeamSeason) -> Schedule`

Transport: injectable sync `Transport.fetch(url) -> str`. Tests use `FixtureTransport` only.

Planning-time git note: owner review of `docs/PHASE2_PRODUCT_DRIFT.md` is recorded on disk (Slice 12 Implementation Notes + drift report). Those documentation updates may still be uncommitted relative to `origin/main`. Coding slices must not rewrite that historical record; they may assume the owner-review disposition described in the drift report.

### 2.2 Public-repo discipline

The repository is public. Standing rule: [`.cursor/rules/public-repo-hygiene.mdc`](../.cursor/rules/public-repo-hygiene.mdc).

Phase 3 must not commit secrets, cookies, credentials, emails, private/local IPs, User-Agent strings in fixtures, raw HTML-in-JSON, or private filesystem/operator details. Development-host paths belong in unpublished operator notes, not in this public plan.

Do not add legal/ToS/release-gating language.

---

## 3. Recommended Phase 3 architecture

Keep the Phase 2 client as the MaxPreps boundary. Home Assistant wraps it; it does not reimplement parsers.

```
Home Assistant UI (config flow / options)
        ↓
Config entry per school (unique_id = school_id)
        ↓
DataUpdateCoordinator (one per config entry)
        ↓
Async HA transport  →  existing parsers / MaxPrepsClient pipeline
        ↓
Normalized School / TeamSeason / Schedule / Game
        ↓
Device = school
Entities = one sensor per subscribed program
```

### 3.1 Config-entry model

**Recommendation:** one config entry per school.

| User action | HA mechanism |
|-------------|--------------|
| Add a school | Standard **Add Integration** config flow (`async_step_user`) |
| Search / pick school | Config flow steps using `search_schools` |
| Subscribe sports at setup | Config flow multi-select after current-season + supported-format filtering |
| Add/remove sports later | **Options flow** (`OptionsFlowWithReload`) |
| Duplicate school | `async_set_unique_id(school_id)` then `_abort_if_unique_id_configured()` |

Entry `data` (identity; stable):

- `school_id`, `canonical_url`, `name`, optional `city` / `state` / `mascot` / `mascot_url`

Entry `options` (subscriptions; mutable):

- `subscriptions`: list of program keys `{sport, gender, level}` only (Q2 decided 2026-09-02). Never persist `season`, `sport_season_id`, `all_season_id`, year, or team-season URL as identity.

Do **not** use rotating `sport_season_id` as the config-entry unique ID or as the entity unique ID. At coordinator refresh, resolve **all** school-home `sportSeasons[]` rows whose `{sport, gender, level}` match the subscription **and** whose `year` equals the applicable school year (July 1–June 30). One subscription may map to multiple `TeamSeason` rows (multi-term programs).

HA subentries (one subentry per sport) are a technically valid alternative with different UX. They are **not** the recommended default. See section 6 Q4.

### 3.2 Device / entity / data contract

**Recommendation (validates the product hypothesis against HA conventions):**

- **Device:** the school. `DeviceInfo.identifiers = {(DOMAIN, school_id)}`. Name from `School.name`. `configuration_url` = payload school `canonical_url`.
- **Entity:** one `sensor` per subscribed program, associated with that device.
- **Coordinator:** owns all network I/O for the entry. Entities are `CoordinatorEntity` and never fetch.
- **Manifest:** `integration_type: service`, `iot_class: cloud_polling`, `config_flow: true`, custom-integration `version` required.

Entity unique ID (stable across school-year rollover):

```
{school_id}:{gender}:{level}:{sport}
```

Do **not** append `:{season}`. Multi-term programs are one entity / one subscription.

`has_entity_name = True`. Translated name from `display_label` placeholders (e.g. `Boys Varsity Football`), producing entity IDs in the spirit of `sensor.centennial_boys_varsity_football` without hard-coding slugs as identity. Config-flow option labels may add informational `(Fall, Spring 26-27)` context; that is not part of the entity unique ID.

**State (product checkpoint Q1 — do not implement until decided):**

Do **not** invent `PRE` / `IN` / `POST` / `OFF` merely because PRODUCT mentions them as a future Team Tracker-like sketch. Phase 2 already normalizes provider state to `scheduled | final | deleted | unknown`. Slice 6 must **wait** for owner disposition of Q1. Planning recommendation (A) is recorded in section 6; it is not a default to implement if Q1 is still open.

Regardless of Q1, attributes should expose **both** `last_game` and `next_game` when derivable, so Phase 4 does not depend on a single “relevant game” state.

**Attributes (minimum contract for Phase 4 and automations):**

School/program chrome: `school_id`, `school_name`, `sport`, `gender`, `level`, `year`, `display_label`, `team_record` (omit if untrustworthy), `team_logo`, `attribution`. Do not assume a single `season` string: a program may have multiple provider terms. Later slices may expose `terms` / per-term schedules on the coordinator contract; Slice 5 must keep that structure internally even if entities are not built yet.

`last_game` / `next_game` objects, when present:

- `id`, naive `date` ISO string, `status`, `opponent_name`, `opponent_id`, `home_away`, `team_score`, `opponent_score`, `result`, `venue`, `game_url`, optional `opponent_logo`

**Full-season `schedule` on a sensor attribute is a hypothesis, not the locked contract.** Spike E (executed in Slice 6 before landing the entity schema) must verify the HA-native implications of serializing a 10–30+ game list into entity attributes even if those attributes are unrecorded: state-machine size, recorder/history side effects, more-info UX, and frontend consumers. Evaluate keeping the full `Schedule` on coordinator / `runtime_data` and exposing only concise attributes (`last_game`, `next_game`, chrome). Put bulky/volatile fields that *are* exposed on the entity in `_unrecorded_attributes`. Entity **state** remains short (HA state is not a document store).

Do not create one HA entity per contest.

### 3.3 Current-season detection (Spike B / Slice 1)

**Production applicable school year (owner, 2026-09-02):** July 1 through June 30 in Home Assistant’s configured local timezone. Example: `2026-07-01` through `2027-06-30` is `26-27`. This is the user-facing school year for subscriptions, config-flow filtering, and coordinator resolve.

Still do **not** hardcode Football=Fall / Baseball=Spring (term labels come from provider rows). Do **not** treat four-school fixture patterns as a proven production current-season rule.

The Slice 1 conservative **modal-year** helper remains test/regression evidence for leftover rows (Pike `11-12`) and ambiguity synthetics. It is **not** the production answer to “which school year applies.” Config flow and coordinator must filter allowlisted rows to `year == applicable_school_year`, not fail-closed on adjacent years when both `26-27` and `27-28` exist around rollover.

Distinguish:

1. Applicable school year (calendar rule above).
2. Provider `sportSeasons[]` rows whose `year` equals that string.
3. Whether schedule pages for those rows are published (missing/`NextDataNotFoundError`/empty `contests[]` ≠ “invent a season”).

**Candidate signals** (existing research/fixtures; not yet a production algorithm):

- Modal `year` on school-home `sportSeasons[]` (Pike County leftovers are two `11-12` rows beside a `26-27` majority).
- Historical leftovers observed so far often embed `YY-YY` in `canonical_url`; many current rows omit that segment (research Slice 05; Pike `…/soccer/winter/11-12/schedule/` vs current `…/football/`).
- `mostRecentPublicGenderSportSeasonLevel` is proven on **team/schedule pages only**. Do not fetch N team pages during config just to read it. After a schedule fetch, it may optionally be used as a consistency check, not as the discovery source.
- `teamSeasonPickerData[]` is historical within one sport. Do not use it for normal subscriptions.
- `isPublished: false` remains unused as a filter (no `false` samples). Pike leftovers are `isPublished: true`.
- Football Fall and baseball Spring can both be `year: "26-27"`: “current” means **school-year cohort**, not “in-season this week.”
- `allSeasonId` is a rollover *hint* for `(sport, gender, level)`, never a unique ID without `school_id`.

**Slice 1 must** encode a dedicated helper (keep `get_school_teams` returning all rows) and **explicitly test** rollover / partial-population ambiguity with synthetic fixtures, including at least:

- mixed years without a clear majority
- tied modal years
- disagreement between modal year and URL year-segment
- mid-rollover mix of adjacent school years (e.g. `26-27` + `27-28`)
- historical leftovers that omit a year segment, or current-looking rows that include one

**Slice 4 already shipped** against the Slice 1 helper. Remaining slices follow the July 1 applicable-year rule (owner 2026-09-02). The Slice 1 helper may still exclude historical leftovers in tests; production matching is `year == applicable_school_year` ∩ allowlist.

Standing constraints:

- Normal UI lists only allowlisted programs that have **at least one** provider row for the applicable school year. Omit unvalidated sports; do not gray them out.
- Subscription identity is the **program** `{sport, gender, level}` only. Multiple terms in that year are one option / one entity.
- Picker/options labels aggregate term names + year as informational context (see owner amendments).
- At refresh/rollover: re-fetch school home; match subscriptions by `{sport, gender, level}` against **all** rows for the applicable year; keep every matching `TeamSeason` (do not pick one term). `all_season_id` may corroborate program class but is not identity. If the new year has no rows yet, keep last-good data and do not delete the subscription.

### 3.4 Supported-format allowlist

Normal selection UI shows supported head-to-head team formats only. Do **not** show tennis/golf/track or other unvalidated sports as disabled/grayed-out choices — omit them.

**Owner-approved rule:** a sport appears in normal setup only once its schedule representation has been empirically validated against the shared supported `contests[]` parser. Adding another sport later requires fixture/parser evidence and tests, not a product redesign.

**Current allowlist** (`sport` strings):

- `Football` — Phase 3 **acceptance** target
- `Baseball` — Phase 3 **acceptance** target
- `Basketball` — empirically validated Next.js `contests[]` decode; may appear in the selector; **not** a Phase 3 acceptance target
- `Volleyball` — empirically validated Next.js `contests[]` decode (Phase 2 regression fixture); may appear in the selector; **not** a Phase 3 acceptance target

Do **not** show merely “likely” conventional team sports such as soccer, lacrosse, flag football, or softball until they have the same class of fixture/parser evidence.

If an allowlisted sport later returns `NextDataNotFoundError` or `ContestSchemaError`, that program must fail in isolation (section 3.6) without taking down the school device or sibling sports.

Do not implement tennis/golf/track parsers in Phase 3.

### 3.5 Transport

Keep parsers synchronous. Add an async transport boundary for HA:

- `AsyncTransport` protocol: `async def fetch(url: str) -> str`
- HA implementation uses `homeassistant.helpers.aiohttp_client.async_get_clientsession(hass)` (shared session; do not add `httpx` as a production dependency)
- Per-request `User-Agent` override (HA default session UA is frozen as Home Assistant `SERVER_SOFTWARE`; MaxPreps exploration succeeded with a dedicated UA). Production UA must **not** reuse `hacs-highschoolscores-explore/0.1`. Use an integration identifier such as `HomeAssistant-MaxPreps/<version> (+<public repo URL>)` on the request, not by mutating session defaults.
- Timeouts via `asyncio.timeout` (start at 20s; HTML payloads in research were hundreds of KB)
- No cookies
- No retry on HTTP 403, 429, or challenge-like responses
- No retry storm on parser errors
- Optional single retry only for clearly transient network/timeout failures — default **off** until production evidence appears
- Basic validation: HTTP 200, `text/html` (or HTML-ish) body, size cap (recommend 5 MiB), then existing `extract_page_props`
- Map HTTP failures to typed transport errors; let parsers continue to raise `NextDataNotFoundError` / schema errors
- Test double: async wrapper around `FixtureTransport` (zero live network)

`MaxPrepsClient` remains the sync facade for Phase 2 tests. Add a thin `async_` method set or small `AsyncMaxPrepsClient` that `await`s fetch then calls the same parsers. Do not rewrite `parsing/`.

### 3.6 Coordinator polling

MVP: conservative fixed interval, about **two coordinator cycles per day** (`timedelta(hours=12)`), `always_update=False` if snapshot equality is defined.

One cycle per school:

1. Fetch school home (shared).
2. Resolve **all** `TeamSeason` rows for each subscription `{sport, gender, level}` whose `year` equals the applicable school year (July 1–June 30).
3. Fetch **each** matching term’s schedule (one HTTP GET per `TeamSeason.canonical_url` schedule join). Keep term/source on the snapshot. Do not arbitrarily drop terms or concatenate games into a term-less list as the only stored form.

MVP interval remains ~12h. After school-year rollover, if the applicable year has no published rows/schedules yet, Slice 11 may poll daily until they appear, then return to ~12h. Slice 5 must still isolate per-program failures and retain last-good snapshots when the new year is unpublished.

Entities must not poll independently (`should_poll` False via `CoordinatorEntity`).

Adaptive game-window polling and live scores are **NICE TO HAVE**, blocked on timezone/live-score evidence (Spikes G/H). Do not build them into production in Phase 3.

Distinguish **entry-wide** failure from **per-program** failure:

- **Entry-wide** (shared school-home / discovery refresh fails): raise `UpdateFailed` so the coordinator’s last successful snapshot is retained. First-setup failure: `ConfigEntryNotReady`. Do **not** replace coordinator data with empty schedules.
- **Per-program** (one subscribed schedule fetch or parse fails): do **not** raise entry-wide `UpdateFailed` and do **not** mark successfully refreshed sibling sports unavailable. Preserve that program’s last good schedule where appropriate and expose per-program error/availability state. Other subscriptions update normally.

Entities remain `CoordinatorEntity`; availability of a team sensor must be able to reflect **that program’s** success/failure, not only the coordinator’s `last_update_success`.

### 3.7 Logos

Configured-school logo is MUST DO; opponent logos are NICE TO HAVE.

**Automatic school logo (preferred):**

- Search: `School.mascot_url`
- Schedule: `Schedule.team_logo` ← `teamContext.data.schoolMascotUrl`
- Same CDN pattern: `https://image.maxpreps.io/school-mascot/…/{school_uuid}.gif?version=…`
- `version=` is a cache-buster; not identity

Expose as `entity_picture` on team sensors. If browser hotlink is unreliable (research did not HEAD the CDN), add an `image` entity that fetches through the HA session (server-side proxy) so the future card can use a stable HA image URL. Logo failure must not fail schedule setup.

**Opponent logos (cheap, no extra requests):** participant `teams[*][20]` is proven as mascot URL (research Slice 10). Phase 2 `Game` does not yet expose it. Add optional `Game.opponent_logo` from that slot when it is an `https` URL. Do not fetch opponent school pages.

**User-supplied fallback (MUST exist if automatic provider logo delivery is missing or unreliable):** configured-school logo remains a Phase 3 MUST DO. Investigate an **HA-native user-supplied image/media selection or upload flow first**. Local `/local` paths or externally hosted HTTPS URLs may be secondary mechanisms; they are **not** the preferred UX and must not be assumed as the primary fallback. “No fallback” is **not** an acceptable final disposition if automatic logos fail. Do not invent file-size/dimension caps in this plan; apply whatever HA selectors/docs require when implementing. Missing/failed logos must still never prevent schedules/scores from functioning.

### 3.8 Timezone / last-next derivation

Preserve naive `Game.date`. Do not attach school, state, or user timezone.

Safe to expose: naive ISO date/time strings for display and ordering.

Not safe to claim: absolute kickoff instants, Calendar entities, or “30 minutes before kickoff” as a guaranteed automation.

Last/next derivation for **display**:

- Sort current-season games by naive `date`
- `last_game`: latest `status == final`
- `next_game`: earliest `status == scheduled` whose calendar date is `>=` Home Assistant’s local date (`dt_util.now().date()` vs `game.date.date()`)
- Document this as a **display heuristic**, not timezone-correct scheduling
- A user-configured school timezone would **not** repair the Pensacola mismatch (naive `row[11]` aligned to Eastern while school TZ fields said Central). Do not offer TZ config as a correctness fix.

Calendar support is deferred (NICE TO HAVE blocked by this policy).

### 3.9 What Phase 3 must not do

- Custom Lovelace card
- Tennis/golf/track schedule parsers
- Historical-season picker / 20 years of `teamSeasonPickerData`
- YAML setup, pasted URLs, or provider IDs as user input
- Manual opponent-logo management
- Rosters, player stats, articles, rankings pages
- Invented live/postponed/cancelled mappings
- Hardcoded sport→term / wall-clock current-season policy unless Slice 1 stops with an owner-approved fallback
- Football-only narrowing without owner decision
- HACS listing polish (`hacs.json`, default-repo metadata) unless a later slice proves it is required to load the component (it is not)

---

## 4. Required spikes — planning findings

Each spike lists the question, existing evidence, extra evidence still needed, exit criterion, technical decisions, and product-owner triggers.

Implementation slices that **execute** remaining spike work are in section 7. This section records what planning could already answer without creating the HA environment or performing live research.

### Spike A — HA development environment and conventions

**Question:** What is the minimal conventional HA Core development setup for this repository, and which test/lint tooling should Phase 3 add?

**Existing repo evidence:**

- `pyproject.toml`: Python `>=3.12`, pytest-only `[dev]`, package `custom_components*`
- No `manifest.json`, no `.github/` workflows, no HA test plugin
- `.gitignore` already excludes HA runtime (`.storage/`, `.homeassistant/`, `*.db*`)
- `.cursor/` is gitignored except the force-tracked hygiene rule
- Client tests: `pip install -e ".[dev]"` then `pytest` (112 tests at Slice 12)

**Extra evidence required (implementation, not this planning task):**

- Pin a specific Home Assistant Core **stable** image/tag and matching `homeassistant` Python package version
- Confirm Python version of that pin (PyPI `homeassistant` 2026.x currently requires **Python ≥ 3.14.2**, which is **newer** than this repo’s `>=3.12` client floor)
- Operator bind-mounts and UI port live in unpublished compose, not in this public document

**Recommend (do not create during planning):**

- Official **Home Assistant Core container** (`ghcr.io/home-assistant/home-assistant` pinned tag), not a new HAOS VM
- Bind-mount this checkout’s `custom_components/maxpreps` to HA `/config/custom_components/maxpreps`
- Persistent HA config and secrets **outside git**, explicit bind mounts only, no anonymous/named volumes, Compose CLI as source of truth, no GPU, never `chmod 777`
- Dev UI on container port 8123 published to a dedicated host port chosen by the operator
- Test extras split: keep `[dev]` as client/pytest; add `[ha]` with a **pinned** `pytest-homeassistant-custom-component` / `homeassistant` pair
- HA tests use `hass`, `enable_custom_integrations`, `MockConfigEntry`, and an async fixture transport — never live MaxPreps
- Lint: `ruff` for the integration package is worth adding; full core `hassfest` in CI is optional and heavy — do not require a core checkout
- Persistent Cursor rule: yes (section 10)

**Technical decisions:** Core container + bind mount; Python 3.12 remains valid for **client** tests until the owner bumps the floor; HA integration tests run in a 3.14-capable environment (container or dedicated venv).

**Product-owner review:** none unless they reject a Core container in favor of HAOS.

**Exit criterion:** documented pin (HA version + Python), `custom_components/maxpreps` visible in a running HA instance, `pytest` client suite still green without HA extra, one smoke HA test that the domain loads.

### Spike B — current/default team-season and rollover

**Question:** Can current/default team-season be identified from existing MaxPreps payloads without wall-clock + hardcoded sport→term rules?

**Existing evidence (candidate signals only — not a production rule):**

| Signal | Scope | Finding |
|--------|-------|---------|
| Explicit `isCurrent` / `isDefault` on `sportSeasons[]` | School home | **Not present** on observed row keys |
| Modal `year` | School home | Centennial/Bainbridge/St. Edward: all current-year; Pike: majority `26-27` plus two `11-12` leftovers |
| Year segment in `canonical_url` | School home / picker | Current omits `YY-YY`; historical embeds it (research Slice 05; Pike leftover URLs) |
| `teamSeasonPickerData[]` | Team page only | Multi-year history for **one sport**; current rows first in Centennial football picker (`…/football/` vs `…/football/25-26/schedule/`) |
| `mostRecentPublicGenderSportSeasonLevel` | Team page only | Points at current football **and** current baseball 26-27 rows in fixtures — corroboration after schedule fetch, not a school-home discovery API |
| Football Fall vs baseball Spring | Same school year | Both `year: "26-27"` in `sportSeasons[]`. “Current” means **current school-year cohort**, not “in-season this week” |
| `allSeasonId` | Cross-year program class | Stable per (sport, gender, level); **shared across schools**; useful rollover hint, never a unique ID without `school_id` |

**Extra evidence required:** no live HTTP. Slice 1 must add **synthetic** fixtures covering rollover and partial-population ambiguity (mixed years without a clear majority; tied modal years; modal year vs URL year-segment disagreement; mid-rollover adjacent years; leftovers without a year segment and current-looking rows with one). Four-school committed fixtures remain regression evidence for candidate signals, not proof.

**Exit criterion:** a conservative current-cohort helper that survives those tests **or** a tightly defined owner checkpoint **before Slice 4**. *(Slice 1 shipped the modal helper; Slice 4 used it. 2026-09-02 owner amendment: production applicable year is July 1–June 30; see section 3.3.)*

**Technical decisions:** candidate signals listed above; Slice 1 helper remains leftover/ambiguity evidence; production year is the owner calendar rule.

**Product-owner review:** Q2 **decided** 2026-09-02 (one subscription per program; all terms retained). Calendar school-year boundary **decided** (July 1–June 30).

### Spike C — production transport

**Question:** What HA-native production transport should wrap `Transport` / `MaxPrepsClient`?

**Existing evidence:**

- Research: `GET` HTML, no cookies, no JS, custom explore UA, stop on 403/429/challenge, ≥2s delay **during exploration** (not a production poll interval)
- Phase 2: sync `Transport` protocol; no live client; 403/429 policy untested in code
- Schedule HTML sizes in research were on the order of 10^5 bytes

**Extra evidence required:** none to start. If the first owner-supervised live HA fetch returns 403, treat UA/header policy as a bounded follow-up — do not build a bypass.

**Exit criterion:** async transport + tests for 200 HTML, timeout, 403/429 no-retry, oversized body, and fixture-mapped URLs; client parsers unchanged.

**Technical decisions:** section 3.5. Keep sync client for Phase 2 tests.

**Product-owner review:** none unless UA changes are proposed as product-facing.

### Spike D — config-entry architecture

**Question:** Conventional HA representation for multiple schools and multiple sports?

**Existing evidence:** PRODUCT §27.A preferred one entry per school; Phase 3 working spec allows Add Integration per additional school; HA docs: unique IDs, options flows, `OptionsFlowWithReload`, newer subentry flows.

**Recommendation:** section 3.1. Options flow is the conventional “which things on this hub” pattern. Subentries mimic weather-location UX and are more clever than needed.

**Exit criterion:** duplicate-school abort; two entries for two schools; options add/remove sports reloads entities.

**Product-owner review:** Q4 only if they want subentry UX instead of options.

### Spike E — entity/device/data architecture

**Question:** How do School / TeamSeason / Schedule / Game map into HA without abusing state or exploding entities?

**Existing evidence:** HA entity state is not for documents; `_unrecorded_attributes` is the supported recorder exclusion; `DeviceInfo` + `has_entity_name` are current conventions; PRODUCT §5 PRE/IN/POST/OFF is explicitly TBD; Phase 2 statuses are `scheduled|final|deleted|unknown`; full season lists are small but non-trivial (football ~10 games, baseball 30 non-deleted in the Centennial fixture).

**Hypothesis (not locked):** putting the full current-season schedule on a sensor attribute (even unrecorded) plus last/next objects.

**Slice 6 must verify before landing the schema:**

- HA-native implications of serializing 10–30+ games into entity attributes even if unrecorded (state-machine size, recorder/history side effects, more-info UX, frontend consumers)
- Alternative: keep richer `Schedule` on coordinator / `runtime_data`; expose concise entity attributes (`last_game`, `next_game`, chrome)
- Do **not** create one entity per contest
- Calendar remains deferred (Spike G)

**Exit criterion:** written Spike E disposition in Slice 6 Implementation Notes; stable device/entity IDs across reload and simulated rollover; last+next available on entities; full schedule available to future card consumers via the chosen contract (attributes **or** coordinator/runtime data).

**Product-owner review:** Q1 (entity state vocabulary) **must** be decided before Slice 6 lands sensors. Schedule-placement is a technical Spike E decision unless it would change user-visible behavior (then stop and report).

### Spike F — logos

**Question:** Reliable HA-appropriate configured-school logo path, and what to do for opponents?

**Existing evidence:** research Slice 10; `School.mascot_url`; `Schedule.team_logo`; opponent participant `[20]`; hotlink reliability **untested**.

**Extra evidence:** optional HEAD/GET of a mascot URL **through the HA session** during Slice 9 manual sandbox (not CI). If blocked or missing, implement HA `image` entity fetch **and** investigate HA-native user-supplied media selection/upload before URL or `/local` fallbacks.

**Exit criterion:** school logo URL (or proxied image entity) on the device/entities when the provider supplies one; if automatic delivery is missing/unreliable, an HA-native user-supplied image/media selection or upload path exists (URL/`/local` only as lesser fallbacks); missing logo does not fail setup; opponent logo attribute when `[20]` is present.

**Product-owner review:** Q5 if automatic logos fail — choose among HA-native media selector/upload vs lesser URL/`/local` fallbacks. “No fallback” is not acceptable.

### Spike G — timezone/date semantics

**Question:** What can Phase 3 safely expose without claiming absolute kickoff correctness?

**Existing evidence:** research Slice 08 including Pensacola probe. Naive `row[11]` + JSON-LD UTC aligned to **Eastern** even when school TZ fields were Central. `stateData` is state-level EST. Non-featured rows have no per-contest TZ.

**Extra evidence:** optional game-day observation (Spike H) may collect more naive-vs-UTC pairs; it is **not** required to ship Phase 3 display.

**Exit criterion:** naive ISO strings in attributes; no `tzinfo`; Calendar not implemented; limitations documented in README.

**Technical decisions:** section 3.8.

**Product-owner review:** none unless they want to block Phase 3 on kickoff automations (that would expand scope).

### Spike H — polling and game-day observation

**Question:** What production polling is justified, and what optional observation could teach us about scores/TZ?

**Existing evidence:** no measured final-score latency; contestState live/postponed/cancelled unobserved; product target ~2 cycles/day; four gold football fixtures; Centennial football fixture includes a scheduled Alpharetta contest on `2026-09-04T19:30:00` (naive).

**Production MVP:** 12-hour coordinator interval. No adaptive polling.

**Optional observation experiment (not production):**

- Owner-approved research script only
- Temporary 5–10 minute interval during a **narrow** game window
- Reuse capture discipline: no cookies, stop on 403/429, public-repo hygiene
- Observe: `contestState`, scores, `featuredGameData` vs `contests[]`, posting latency
- A non-Eastern school (Pensacola was already probed) only if it materially helps TZ; do not expand the school set casually
- Do **not** merge the interval into the coordinator because the script existed

**Exit criterion for Phase 3:** conservative polling shipped; observation script optional and gated; live scores remain undocumented as guaranteed.

**Product-owner review:** whether to **run** the observation script, and which game window. Not required for the completion gate.

---

## 5. Layering — what may change in the client vs HA-only

Allowed client-adjacent additions (keep parsers intact):

- Current-cohort / supported-format **helpers** consuming `list[TeamSeason]` (allowlist; current-cohort algorithm from Slice 1)
- `AsyncTransport` + thin async client facade
- Optional `Game.opponent_logo`
- Typed transport HTTP errors

Not allowed without new evidence:

- Replacing `contests[]` decoding
- Filtering inside `get_school_teams` (helpers wrap it)
- Timezone localization of `Game.date`
- Mapping unknown `contestState` to live/postponed/cancelled
- Reconstructing URLs

---

## 6. Product-owner decisions required before/during implementation

Do not resolve these silently in a coding slice.

### Q1 — Primary entity state vocabulary

- **Question:** What should `sensor.*` **state** be, given that last game and next game must both be available?
- **Why it matters:** Automations trigger on state. PRE/IN/POST/OFF would match Team Tracker folklore but is not a Phase 2 provider enum and would invent `IN`/`OFF` without evidence. A provider-status state is honest but less dashboard-icon friendly.
- **Choices:** (A) Provider status of next game, else last final, with last+next attributes — **planning recommendation**. (B) Team Tracker `PRE`/`IN`/`POST`/`OFF` with `IN` unused until evidence. (C) Record string as state. (D) Naive next-game datetime string as state (implies more kickoff-automation confidence than Spike G supports).
- **Decide by:** Slice 6 (entities). Slice 6 **must wait** for owner disposition. Do **not** implement A (or any other choice) if Q1 is still open.

### Q2 — Multi-term current programs

**Decided (owner, 2026-09-02).** Not A/B/C as originally sketched.

- **Question (historical):** When one school year contains two MaxPreps terms for the same sport/gender/level, are those two subscriptions, one picked term, or hidden?
- **Decision:** They are **one school-year program subscription** `{sport, gender, level}` that **resolves to all matching `TeamSeason` rows**. Fixture evidence: Centennial Boys Freshman Baseball Spring 26-27 and Fall 26-27 (different `sportSeasonId` / `canonicalUrl`, same `allSeasonId`).
- **Do not:** persist `season` on the subscription; append `:{season}` to entity unique IDs; expose a term picker; omit the program when keys collide; arbitrarily select one term; flatten away term distinction in coordinator data.
- **UI:** one selectable option; label includes informational terms + year (`Boys Freshman Baseball (Fall, Spring 26-27)`).
- **Scope:** does not add soccer/softball to the allowlist. JV soccer remains non-selectable until that sport is evidence-validated.

### Q3 — Selector allowlist vs denylist

**Decided (owner correction):** evidence-based **allowlist** (section 3.4). Not an open question.

### Q4 — Options flow vs subentries for sports

**Decided (Slice 4, silent A):** OptionsFlowWithReload; one config entry per school; subscriptions in `entry.options`. Options-flow UI is Slice 7. Not subentries.

### Q5 — Logo fallback UX (if automatic logos fail)

- **Question:** If `mascotUrl` / `schoolMascotUrl` cannot be displayed reliably, which **user-supplied** configured-school logo path should Phase 3 ship? Logo support remains MUST DO; “no fallback” is not acceptable.
- **Why it matters:** Automatic CDN hotlink reliability is untested. Users must still be able to attach a school logo.
- **Choices:** (A) HA-native image/media selection or upload — **preferred investigation**. (B) Local `/local` media path as a lesser fallback. (C) Externally hosted HTTPS URL as a lesser fallback. B and C must not be assumed as the preferred UX.
- **Decide by:** Slice 9, if the automatic path fails the sandbox check (or is missing).

---

## 7. Ordered implementation slices

Optimize for clean boundaries, not fewest slices. Each slice: one objective; tests; PRODUCT drift check; Implementation Notes; leave the tree green.

**Git protocol:** Confirm existing `origin` / `main`. Remaining Phase 3 slices: after tests are green and public-repo hygiene on the staged diff passes, commit and push without waiting for another owner OK. Never `git init`, rewrite remotes, skip hooks, or force-push `main`. Public-repo hygiene on every staged diff.

**Live MaxPreps:** Automated tests remain fixtures-only. Owner-supervised live traffic is allowed only for Slice 0 HA sandbox clicks, Slice 9 optional logo HEAD, and Slice 12 optional observation. No live calls in CI.

### Slice 0 — HA Core dev/test scaffold (Spike A)

- **Objective:** Make the integration loadable and testable in HA without product behavior.
- **Touch:** `custom_components/maxpreps/manifest.json`, `const.py`, `strings.json`, `translations/en.json`, expand `__init__.py` with no-op/`async_setup_entry` placeholder if required to load, `pyproject.toml` `[ha]` extra, `tests/conftest.py` HA fixtures, `.cursor/rules/ha-integration.mdc`, generic `docs/HA_DEVELOPMENT.md` (no operator host paths). Unpublished Compose lives outside git.
- **Tests:** domain constant import; `manifest.json` required keys (`domain`, `name`, `version`, `config_flow`, `iot_class`, `integration_type`); client pytest suite still passes without `[ha]`.
- **Do not:** config flow logic, coordinator fetches, entities, httpx production dependency, HACS listing.
- **Operator setup (specify, execute in this slice when authorized):** Core container, bind-mount component, persistent config/secrets outside git, UI port, Python pin vs `[ha]` extra.

### Slice 1 — Current-season and supported-format helpers (Spike B)

- **Objective:** Pure-Python helpers over `list[TeamSeason]`: allowlist filter plus a **conservative current-cohort algorithm** (or owner checkpoint if ambiguity cannot be resolved conservatively).
- **Touch:** new module under `custom_components/maxpreps/` (e.g. `selection.py`); `tests/test_selection.py`; synthetic sport-season fixtures as needed (not live HTTP).
- **Tests:** four-school committed fixtures as regression (Pike `11-12` vs majority `26-27`; Centennial football+baseball present); allowlist includes Football/Baseball/Basketball/Volleyball and excludes soccer/lacrosse/flag football/tennis/golf/track; multi-term rows still present in the unfiltered list; **ambiguity synthetics** (mixed years without majority; tied modal years; modal vs URL-segment disagreement; mid-rollover adjacent years; leftover without year segment / current-looking row with year segment); no wall-clock or sport→term table.
- **Do not:** change `get_school_teams`; HA UI; live HTTP; declare modal year a production rule; proceed to Slice 4 if the helper is still ambiguous without an owner checkpoint.

### Slice 2 — Production async transport (Spike C)

- **Objective:** Mockable async HTTP boundary.
- **Touch:** `transport.py` (keep sync protocol); new `ha_transport.py` or `async_transport.py`; transport exceptions; `tests/test_async_transport.py`; async fixture adapter.
- **Tests:** mapped fixture URL; 403/429 raise typed error and do not retry; timeout; oversize body; no network.
- **Do not:** change parsers; add retries on 403/429; call MaxPreps.

### Slice 3 — Async client facade

- **Objective:** `await` fetch → existing parsers.
- **Touch:** `client.py` or `async_client.py`; reuse Slice 2 transport.
- **Tests:** Centennial search → teams → football/baseball schedules via async fixture transport (same assertions as Phase 2 client tests, not a second parser).
- **Do not:** duplicate parse logic.

### Slice 4 — Config flow: school search + sport subscription

- **Objective:** UI flow from short-name search to a school config entry with subscriptions.
- **Touch:** `config_flow.py`, `strings.json` / translations, `const.py`.
- **Flow:** `user` (query) → results picker (`School Name | City, State` · mascot; degrade location) → filtered multi-select → `async_create_entry`.
- **Tests:** empty query; no results; Saint retry still happens in client; pick Centennial Roswell; duplicate `school_id` abort; subscriptions stored; selector options are allowlisted sports only (football/baseball/basketball/volleyball as present); tennis/soccer/lacrosse/flag football/softball absent; Pike historical not in schema options; Q4 = options not subentries; multi-term allowlisted programs are **one** option (not omitted). *(Post-Slice-4 owner amendment: option labels must show term(s)+year — corrective slice before Slice 5.)*
- **Do not:** YAML; pasted URLs; grayed-out unsupported sports; historical year picker.

### Slice 5 — Coordinator

- **Objective:** One coordinator per school entry; school-home + **all term schedules** for each subscribed `{sport, gender, level}` in the **applicable school year (July 1–June 30)**; **entry-wide vs per-program** failure isolation. Snapshot must retain per-term `TeamSeason` / `Schedule` (not one flattened term-less list as the only structure).
- **Touch:** `coordinator.py`; `__init__.py` `async_setup_entry` / unload; `runtime_data`; small `applicable_school_year` helper; switch config-flow selectable filter from Slice 1 modal cohort to `year == applicable_school_year` ∩ allowlist (same grouping helper as the label corrective slice).
- **Tests:** success snapshot with football **and** multi-term freshman baseball (two schedule fetches, both terms present); **one term or one sport** schema/transport error does not mark sibling sports unavailable or drop their refreshed data; school-home/discovery failure raises `UpdateFailed` and retains the last successful **entry** snapshot; first-setup discovery failure → `ConfigEntryNotReady`; unresolved subscription (no rows for applicable year) → documented per-program unavailable payload **without** deleting the subscription; interval constant ~12h; do not invent games when the new year is unpublished.
- **Do not:** per-entity fetch; adaptive/game-day polling; live HTTP; treat a single schedule failure as entry-wide `UpdateFailed`; pick one term; persist `season` on the config entry; build sensors or the card; implement Slice 11 daily-until-published (keep last-good + 12h is enough here).

### Slice 6 — Device and team sensors (Spike E)

- **Objective:** School device + one sensor per subscription; last+next; **Spike E verification** of whether the full schedule belongs on entity attributes vs coordinator/`runtime_data`. **Blocked on Q1.**
- **Touch:** `sensor.py`; `__init__.py` forward setup; translations; Slice 6 Implementation Notes for Spike E disposition.
- **Tests:** unique IDs; `device_info` identifiers; `has_entity_name`; football+baseball entities for one school; deleted games absent; unknown status preserved; naive dates have no offset; last+next present when derivable; schedule exposure matches the Spike E-chosen contract (do **not** assume `_unrecorded_attributes` includes `schedule` until Spike E exits); per-program availability when one sport failed in Slice 5 isolation tests.
- **Do not:** land sensors without owner Q1 disposition; calendar; custom card; PRE/IN/POST/OFF unless Q1 explicitly chose B; one entity per contest.

### Slice 7 — Options flow: add/remove sports

- **Objective:** HA-native subscription edits with reload and stable IDs for remaining entities.
- **Touch:** `config_flow.py` options handler (`OptionsFlowWithReload` unless Q4 chose subentries).
- **Tests:** add baseball to football-only entry; remove a sport; entity registry unique IDs of remaining sensors unchanged; cannot add tennis or other non-allowlisted sports; cannot add Pike `11-12`; multi-term programs still one option with aggregated term/year label.
- **Do not:** require YAML or manual entity editing.

### Slice 8 — Multi-school behavior

- **Objective:** Two config entries, two devices, independent coordinators.
- **Tests:** Centennial + Bainbridge (or Pike) football fixtures loaded together; unique IDs do not collide despite shared football `sport_season_id`; unloading one entry does not remove the other.
- **Do not:** one giant multi-school wizard.

### Slice 9 — Logos (Spike F)

- **Objective:** Configured-school logo on entities; optional opponent logo from contest participant `[20]`; no setup failure without logos.
- **Touch:** `models.py` / `parsing/contests.py` for `opponent_logo` if not done earlier; `sensor.py` `entity_picture`; optional `image.py`; Q5 fallback using HA-native media selection/upload first if automatic logos fail.
- **Tests:** mascot URL from search/schedule fixtures; missing `schoolMascotUrl` still creates sensors **and** still offers a user-supplied configured-school logo path (not “no fallback”); opponent logo present on a football row with `[20]`; baseball Centennial logo path still school UUID GIF.
- **Do not:** download binaries into git; per-opponent user management; extra HTTP in CI.

### Slice 10 — Failure, recovery, unload/reload

- **Objective:** Graceful degradation matching PRODUCT §19.
- **Tests:** malformed `__NEXT_DATA__` on **school home** → entry-wide `UpdateFailed` / `ConfigEntryNotReady` as appropriate, last entry snapshot retained; `ContestSchemaError` or 429 on **one schedule** → that program error/unavailable, siblings stay available with refreshed or last-good data; reload; unload; empty `contests[]` schedule (valid empty, not a sibling-killer); subsequent entry-wide failure preserves last games.
- **Do not:** destructive empty replacement; collapsing per-program failures into entry-wide unavailable.

### Slice 11 — Rollover

- **Objective:** Subscriptions survive the July 1 school-year boundary without entity unique_id churn or user reconfiguration.
- **Tests:** freeze/synthetic clock across July 1; applicable year becomes `27-28`; football `{sport, gender, level}` still matches; entity unique_id unchanged; coordinator fetches new-year schedule URL(s) when mapped. When new-year rows/schedules are unpublished, last-good prior-year snapshot is retained and refresh may run daily until they appear, then return to ~12h. Multi-term programs still resolve to **all** matching new-year rows (not one term).
- **Do not:** require reconfiguration; persist only `ssid` as identity; invent a schedule because the calendar rolled over; use the Slice 1 modal-year helper as the production year.

### Slice 12 — Optional game-day observation script (Spike H)

- **Objective:** Owner-run research script, not production polling.
- **Touch:** `scripts/explore/` (or similar) using existing capture discipline.
- **Do not:** wire into coordinator; commit private captures; run from CI.
- **Gate:** explicit owner approval of school list, window, and interval before any live run.

### Slice 13 — Documentation and Phase 3 completion gate

- **Objective:** README + this file’s Implementation Notes + documented limitations (timezone, live scores, supported-format allowlist). PRODUCT.md still not silently rewritten.
- **Touch:** `README.md` (status/test/dev only in touched sections), Implementation Notes, maybe `docs/HA_DEVELOPMENT.md`.
- **Do not:** mark the gate complete unless section 8 items are actually true; do not start Phase 4 card work.

### Slice dependencies

```
S0 scaffold
S1 selection helpers
S2 async transport → S3 async client
S0 + S3 + S1 → S4 config flow
S3 + S1 → S5 coordinator
S5 → S6 sensors
S6 → S7 options
S6 → S8 multi-school
S6 → S9 logos
S5 → S10 failure
S5 + S6 → S11 rollover
S2 → S12 observation (optional, parallel after S2)
S7 + S8 + S9 + S10 + S11 → S13 wrap-up
```

Q1 **must** be decided before Slice 6 lands sensors (no silent default). Q2 **decided** (one program subscription → one or more `TeamSeason` rows). Q4 **decided** (options). Q5 in Slice 9 if automatic logos fail. Q3 is decided (allowlist). Production applicable year is July 1–June 30 (not the Slice 1 modal helper).

---

## 8. Proposed Phase 3 completion gate

Recommend Phase 4 card work **only if** all of the following are true. Do not check these off during planning.

1. HA Core development environment is reproducible from public docs plus unpublished operator compose (Core container, bind-mounted component, config/secrets outside git).
2. Custom integration loads and unloads normally in that HA instance.
3. User can complete setup through the HA UI (search → school → supported current-season sports). No YAML.
4. Multiple schools work as separate config entries/devices.
5. Multiple subscribed sports per school work.
6. Adding/removing sports uses HA options (or owner-chosen Q4 equivalent), not YAML or manual entity edits.
7. Current-season selection uses the applicable school year (July 1–June 30) ∩ allowlist; historical Pike-style rows (`year` ≠ applicable year) are not normal subscriptions. Slice 1 modal helper is leftover/ambiguity evidence, not the production year.
8. Season rollover re-resolves `{sport, gender, level}` against the new year’s provider rows (one or more `TeamSeason` per subscription) without changing entity unique IDs (Slice 11 tests). Unpublished new-year schedules do not destroy last-good data or require reconfiguration.
9. Production async transport exists; entities do not fetch; coordinator polling is conservative (~2 cycles/day).
10. Entry-wide school-home/discovery failure does not wipe last successful entry data. A single subscribed-sport fetch/parse failure does not make sibling sports unavailable; the failed program preserves last good data and exposes per-program error/availability.
11. Stable device identifiers `(domain, school_id)` and program entity unique IDs.
12. Current-season results exposed, including previous and next game objects for consumers. Full-season schedule is available via the Spike E-chosen contract (concise entity attributes and/or coordinator/`runtime_data`) — not one entity per contest.
13. Configured-school logo support: automatic provider imagery when reliable; if not, an HA-native user-supplied image/media path exists (URL/`/local` only as lesser fallbacks). Missing logo does not break scores. “No fallback” is not acceptable if automatic logos fail.
14. Football **and** baseball acceptance on the shared parser path (Centennial baseball fixture + football gold schools as HA-level tests).
15. Automated tests make **zero** live MaxPreps requests.
16. README documents timezone-naive dates, no live-score guarantee, and the supported-format allowlist (unvalidated sports omitted, not grayed out).
17. No custom card required for completion.
18. No tennis/golf/track schedule implementation.
19. Implementation Notes filled; PRODUCT.md not silently rewritten; public-repo hygiene held.

---

## 9. Testing strategy

Three layers, matching PRODUCT §21 with Phase 2 constraints:

**Layer 1 — Client (existing + Slice 1–3):** pytest, `FixtureTransport` / async adapter, no HA import required for `[dev]`.

**Layer 2 — Integration:** `pytest-homeassistant-custom-component` fixtures; mock transport; `MockConfigEntry`.

**Layer 3 — Manual HA sandbox:** owner/dev instance; real UI; live MaxPreps only when intentionally testing config search/schedule in that sandbox — never from CI.

Coverage list for Layer 2 (minimum):

- Config flow happy path and errors
- Duplicate school
- Multiple schools
- Multiple sports under one school
- Options add/remove
- Current-season selection (applicable school year July 1–June 30 ∩ allowlist; Slice 1 helper is not the production year)
- Historical rows excluded from normal subscriptions
- Coordinator success / **entry-wide** failure / **per-program** failure isolation / recovery
- Malformed provider data
- Transport 403/429/timeout/oversize
- Stable entity/device IDs
- Simulated season rollover
- Football + baseball
- Missing logo / user-supplied configured-school logo path (no “no fallback”)
- Unknown game states
- Timezone-naive dates
- Unload/reload
- No destructive empty state on transient failure

Do not assert against live MaxPreps availability.

---

## 10. Cursor / Home Assistant development rule

**Recommend adding** `.cursor/rules/ha-integration.mdc` (force-track like the hygiene rule; `.cursor/` is gitignored).

**Apply when:** files under `custom_components/maxpreps/**` and `tests/test_{config,coordinator,sensor,init}*`.

**Enforce:**

- MaxPreps HTML/JSON parsing stays in `parsing/` and the existing client; HA modules consume normalized models only
- All network I/O goes through the injectable async transport + coordinator; entities do not fetch
- Automated tests must not perform live MaxPreps HTTP
- Do not invent `contestState` mappings, timezone offsets, or sport→calendar tables
- Do not treat a denylist of “likely” sports as the selector; use the evidence-based allowlist in the approved Phase 3 plan
- Do not treat one subscribed-sport fetch/parse failure as entry-wide unavailability (including one term of a multi-term program)
- A subscription `{sport, gender, level}` may resolve to multiple `TeamSeason` rows; do not pick one term or persist `season` as identity
- Applicable school year is July 1–June 30 (HA local date); do not invent schedules when that year is unpublished
- Do not add YAML as a required user configuration path
- Do not start a custom Lovelace card in Phase 3
- Public-repo hygiene still applies
- Prefer HA helpers (`DataUpdateCoordinator`, `CoordinatorEntity`, `async_get_clientsession`, `DeviceInfo`, `OptionsFlowWithReload`) over clever substitutes

Do **not** duplicate the entire Phase 3 plan in the rule. Keep it short enough to apply every session.

---

## 11. Documentation this phase should create or update

| File | When |
|------|------|
| [docs/PHASE3_PLAN.md](PHASE3_PLAN.md) | This planning deliverable |
| `docs/HA_DEVELOPMENT.md` | Slice 0 — generic Core container / test extras; **no** private host paths |
| `.cursor/rules/ha-integration.mdc` | Slice 0 |
| `README.md` | Slice 13 — Phase 3 status, test commands, timezone/live-score/unsupported-format limitations |
| `custom_components/maxpreps/strings.json` + `translations/en.json` | Config/entity copy |
| Implementation Notes below | Each coding slice |
| [docs/PRODUCT.md](PRODUCT.md) | Owner-driven. Post-Slice-4 (2026-09-02): §3.2 program subscriptions, §27 H school year, §27 J identity. Drift section A search/client signatures remain a separate owner edit. |
| `hacs.json` | Phase 5 unless later evidence shows HA cannot load without it (unexpected) |

Unpublished operator Compose/secrets remain outside this repository.

---

## 12. Risks (likelihood × impact)

| Risk | L | I | Notes |
|------|---|---|-------|
| MaxPreps 403/UA/challenge on HA production UA | M | H | Exploration UA worked; HA session UA is different. Bounded header experiment only; no bypass. |
| Python 3.12 client vs HA 3.14 test/runtime | H | M | Split extras; do not break fixture client tests. |
| Hotlink logos blocked in Lovelace | M | M | Fallback: HA `image` entity via shared session, then HA-native user-supplied media; not “no logo support.” |
| Current-cohort helper fails on rollover/partial-population ambiguity | M | H | Slice 1 stop/report; no calendar fallback without owner. Four-school modal-year pattern is a candidate signal only. |
| Baseball in-season payload diverges from football | L | H | Shared parser already accepted on committed baseball fixture; if live baseball differs, owner checkpoint — do not silently drop baseball. |
| Unknown `contestState` during real games | M | M | Keep `unknown`; observation script may later inform product. |
| Timezone-naive last/next vs HA local date is “wrong” for some schools | H | M | Documented limitation; do not fake offsets. |
| Full-season schedule in entity attributes | M | M | Hypothesis until Spike E; prefer concise attributes + coordinator data if HA-native costs are high. |
| Config-flow live search latency/empty results | M | M | Already a researched UX (short name + picker). |
| Coordinator 12h interval misses Friday-night finals until Saturday | H | M | Accepted for MVP; adaptive polling is NICE TO HAVE after Spike H. |
| `sport_season_id` reused as entity unique ID | L | H | Plan forbids it; tests in Slices 6 and 11. |

---

## 13. Future Phase 4 data contract (do not implement)

The future stacked last/next card needs, per subscribed program:

- Header: school name, sport, season/year
- School logo URL or HA image entity, record if trustworthy
- Last game and next game simultaneously (opponent, home/away, naive date/time, status, scores/result)
- Optional opponent logo URL
- Full schedule list for expanded view (via the Spike E-chosen contract: entity attributes and/or coordinator/`runtime_data` — not one entity per contest)

Phase 3 last/next attributes plus the Spike E schedule contract are what Phase 4 should consume. Do not overfit entity schema to one card implementation.

---

# Implementation Notes

_Template only. Coding slices append below this heading. Do not edit the approved plan text above to match later implementation._

Each slice note should include: what landed, decisions, pytest command/result, deviations (technical correction vs newly discovered constraint vs **proposed** product change), and PRODUCT drift check.

## Slice 0 — HA Core dev/test scaffold (Spike A)

**What landed**

- `custom_components/maxpreps/manifest.json`, `const.py`, `strings.json`, `translations/en.json`
- Stub `config_flow.py` (`async_step_user` aborts with `not_implemented`)
- `__init__.py` with `async_setup` / `async_setup_entry` / `async_unload_entry` placeholders (no coordinator, entities, or HTTP)
- `custom_components/__init__.py` so pytest-homeassistant can load the package tree
- `pyproject.toml` `[ha]` extra; `[dev]` unchanged (pytest only)
- `tests/conftest.py`, `tests/test_manifest.py`, `tests/test_init.py`
- `docs/HA_DEVELOPMENT.md` (generic Core container + bind-mount + test layers)
- `.cursor/rules/ha-integration.mdc` (force-tracked)

**Decisions**

- **HA pin:** `homeassistant==2026.9.0` with `pytest-homeassistant-custom-component==0.13.362` (closest published phacc; upgrade phacc when a release pins `2026.9.0`). Container image: `ghcr.io/home-assistant/home-assistant:2026.9.0`. Requested `2026.9.1` is not on PyPI/GitHub as of pin date — September 2026 stable is `2026.9.0`.
- **Python split:** Client/fixture tests remain on `requires-python >=3.12` without importing Home Assistant. `__init__.py` avoids top-level `homeassistant` imports so `from custom_components.maxpreps.client import …` still works without `[ha]`. HA smoke tests require Python 3.14+ (Home Assistant 2026.9.x floor).
- **Operator compose:** Unpublished bind-mount compose used to verify visibility; not committed.
- **phacc lag:** After a monthly stable release, phacc may trail by hours. Until a matched phacc ships, Layer 2 install is two-step (`phacc` then `homeassistant==2026.9.0` upgrade); see `docs/HA_DEVELOPMENT.md`.

**Pytest**

| Layer | Command | Result |
|-------|---------|--------|
| Client (`[dev]`, Python 3.12) | `pip install -e ".[dev]" && pytest` | 114 passed, 1 skipped (`test_init` skipped without HA) |
| Client demo | `python scripts/demo_client.py --fixtures` | OK |
| HA smoke (`[ha]`, Python 3.14) | `pip install pytest-homeassistant-custom-component==0.13.362 && pip install homeassistant==2026.9.0 && pip install -e . && pytest tests/test_manifest.py tests/test_init.py` | 3 passed |

**HA sandbox**

- Core container bind-mounted `custom_components/maxpreps` → `/config/custom_components/maxpreps`; loader logged custom integration `maxpreps` warning (expected for unpublished components).

**Deviations**

- Pin bumped post-initial commit from `2026.3.4` to `2026.9.0` (September 2026 stable). `HA_DEVELOPMENT.md` manual-check wording narrowed: confirm discovery/load without import or manifest errors (config flow still aborts `not_implemented`).

**PRODUCT drift check**

- None. No product behavior implemented; `PRODUCT.md` untouched.

## Slice 1 — Current-season and supported-format helpers (Spike B)

**What landed**

- `custom_components/maxpreps/selection.py` — pure helpers over `list[TeamSeason]`:
  - `is_supported_format`, `selectable_team_seasons`, `in_current_cohort`, `current_cohort_year`
  - `canonical_url_year_segment` / `canonical_url_year_segments` (isolated `YY-YY` path-segment parsing)
- `custom_components/maxpreps/const.py` — `SUPPORTED_SPORTS` allowlist (`Football`, `Baseball`, `Basketball`, `Volleyball`)
- `custom_components/maxpreps/exceptions.py` — `CurrentCohortError`, `CurrentCohortEmptyError`, `CurrentCohortAmbiguousError`
- `tests/test_selection.py` — four-school fixture regressions + ambiguity synthetics
- `tests/helpers/team_season_builders.py` — synthetic `TeamSeason` factory for synthetics

**Conservative current-cohort rule (no owner checkpoint required)**

Given school-home `sportSeasons[]` rows (input order preserved; no mutation):

1. **Empty input** → `CurrentCohortEmptyError` (not `None`, not an empty selectable list).
2. **Uniform `year`** on all rows → that year is the cohort, unless any row’s `canonical_url` contains a `YY-YY` path segment that **contradicts** the row’s `year` → `CurrentCohortAmbiguousError`.
3. **Multiple years:**
   - Tied modal counts → `CurrentCohortAmbiguousError`.
   - No strict majority (`count ≤ n/2`) → `CurrentCohortAmbiguousError`.
   - Otherwise let `majority_year` be the unique mode.
   - If adjacent school years are present (start years differ by 1) and any minority year is **not** clearly older than `majority_year` → `CurrentCohortAmbiguousError` (mid-rollover guard).
   - Each majority-year row: a single `YY-YY` URL segment must match the row’s `year` or be absent; mismatch or multiple segments → `CurrentCohortAmbiguousError`.
   - Each minority-year row must be a **historical leftover**: clearly older than `majority_year` **and** exactly one `YY-YY` path segment in `canonical_url` matching the row’s `year`. Otherwise → `CurrentCohortAmbiguousError`.
4. Return `majority_year`. No wall-clock, sport→term table, or URL-only cohort inference.

`selectable_team_seasons` = `in_current_cohort` ∩ `SUPPORTED_SPORTS`. Soccer and other unvalidated sports may remain in `in_current_cohort` but are omitted from selectable output.

**Decisions**

- Q2 not decided; multi-term JV soccer remains in cohort tests only.
- `get_school_teams` unchanged — still returns every parsed row.
- URL year segment = path component matching `^\d{2}-\d{2}$` (not loose substring search).

**Pytest**

| Layer | Command | Result |
|-------|---------|--------|
| Client (`[dev]`, Python 3.12) | `pip install -e ".[dev]" && pytest` | 137 passed, 1 skipped (`test_init` without HA) |
| Client demo | `python scripts/demo_client.py --fixtures` | OK |

**Deviations**

- Uniform-year cohort still validates contradictory URL segments (required by ambiguity synthetic where all rows share `26-27` but one URL embeds `25-26`).
- Tied-modal check runs before the strict-majority check so 50/50 splits surface as tied-modal, not a generic no-majority message.
- School-year ordering uses numeric start-year parsing (`(\d{1,2})-(\d{1,2})` → int), not lexical string compare; malformed `year` values raise `CurrentCohortAmbiguousError`.

**PRODUCT drift check**

- None. `PRODUCT.md` untouched. Allowlist matches approved §3.4; no config flow or UI behavior added.

## Slice 2 — Production async transport (Spike C)

**What landed**

- `custom_components/maxpreps/transport.py` — added `AsyncTransport` protocol; sync `Transport` unchanged
- `custom_components/maxpreps/async_transport.py` — `AiohttpTransport` with bounded streaming read, HTML validation, `asyncio.timeout`, per-request `User-Agent`
- `custom_components/maxpreps/ha_transport.py` — `create_ha_transport(hass)` using `async_get_clientsession` (lazy HA import)
- `custom_components/maxpreps/const.py` — `VERSION`, `USER_AGENT`, `REQUEST_TIMEOUT_SECONDS`, `MAX_RESPONSE_BYTES`
- `custom_components/maxpreps/exceptions.py` — `TransportError`, `TransportHttpError`, `TransportTimeoutError`, `TransportResponseTooLargeError`, `TransportInvalidResponseError`
- `tests/helpers/async_fixture_transport.py` — `AsyncFixtureTransport` wrapping `FixtureTransport`
- `tests/test_async_transport.py` — fake-session coverage for 200/403/429/500/timeout/oversize/invalid HTML/network client error; fixture-mapped URL; no live network
- `tests/test_ha_transport.py` — HA shared-session factory smoke (skipped without `[ha]`)
- `tests/test_manifest.py` — `VERSION` constant matches `manifest.json`
- `pyproject.toml` — added `pytest-asyncio` to `[dev]` (required by existing `asyncio_mode = "auto"`)

**Decisions**

- **User-Agent:** `HomeAssistant-MaxPreps/0.0.0 (+https://github.com/willbur83/hacs-highschoolscores)` — per-request header only; session default headers not mutated
- **Timeout:** 20 seconds via `asyncio.timeout`
- **Size cap:** 5 MiB (`MAX_RESPONSE_BYTES`); enforced while streaming (`iter_chunked`); `Content-Length` used as early rejection when present
- **HTML validation:** non-empty body with `text/html` content type, or absent/nonstandard content type with `<!doctype html` / `<html` prefix check
- **Retries:** none — 403, 429, timeout, and other failures raise on first attempt (optional transient retry remains off)
- **No httpx** production dependency; no `__NEXT_DATA__` parsing or challenge-page detection at transport layer

**Pytest**

| Layer | Command | Result |
|-------|---------|--------|
| Client (`[dev]`, Python 3.12) | `pip install -e ".[dev]" && pytest` | 152 passed, 2 skipped (`test_init`, `test_ha_transport` without HA) |
| Client demo | `python scripts/demo_client.py --fixtures` | OK |
| HA smoke (`[ha]`, Python 3.14) | `pip install pytest-homeassistant-custom-component==0.13.362 && pip install homeassistant==2026.9.0 && pip install -e . && pytest tests/test_manifest.py tests/test_init.py tests/test_ha_transport.py` | 5 passed |

**Deviations**

- Added `pytest-asyncio>=0.24` to `[dev]` so async transport tests and the pre-existing `asyncio_mode = "auto"` config work on a clean `[dev]` install.

**PRODUCT drift check**

- None. `PRODUCT.md` untouched. No async client facade, config flow, coordinator, or parser changes.

## Slice 3 — Async client facade

**What landed**

- `custom_components/maxpreps/async_client.py` — `AsyncMaxPrepsClient` taking `AsyncTransport`; mirrors sync `MaxPrepsClient` method signatures (`search_schools`, `get_school_teams`, `get_schedule`) with `async def` / `await`
- `MaxPrepsClient` unchanged (sync-only); no async methods added to the sync class
- Shared `extract_sport_seasons` in `custom_components/maxpreps/school_home.py` (used by both facades; no second parser or URL grammar)
- `tests/test_async_client.py` — Centennial search → teams → football/baseball pipeline, Saint retry / single-fetch / error-no-retry, tennis `NextDataNotFoundError`, girls basketball gender path, sync-vs-async equivalence for Centennial football; `AsyncFixtureTransport` only
- Async tests reuse constants and helpers from `tests/test_client.py` (`_centennial_roswell_school`, `_find_team`, URL constants) — no parallel async-only golden constants

**Decisions**

- **Shape:** separate `AsyncMaxPrepsClient` class (approved plan §3.5) rather than `async_` methods on `MaxPrepsClient`
- **Parse sharing:** thin duplicated orchestration (await fetch → `extract_page_props` → existing parsers); sport-season row extraction via shared `school_home.extract_sport_seasons`
- **Saint retry:** same empty-result-only retry as sync; parser/transport errors on first fetch do not retry
- **Not wired:** no `__init__.py`, config flow, coordinator, or HA imports in the async client module

**Pytest**

| Layer | Command | Result |
|-------|---------|--------|
| Client (`[dev]`, Python 3.12) | `pip install -e ".[dev]" && pytest` | 162 passed, 2 skipped (`test_init`, `test_ha_transport` without HA) |
| Client demo | `python scripts/demo_client.py --fixtures` | OK |

**Deviations**

- None.

**PRODUCT drift check**

- None. `PRODUCT.md` untouched. No config flow, coordinator, entities, parser changes, or live HTTP.

## Slice 4 — Config flow: school search + sport subscription

**What landed**

- `custom_components/maxpreps/config_flow.py` — three-step flow: `user` (short-name search) → `school` (results picker) → `subscriptions` (multi-select)
- `custom_components/maxpreps/client_factory.py` — `create_async_client(hass)` via `create_ha_transport` (Slice 5 coordinator reuse)
- `custom_components/maxpreps/const.py` — config entry data/options keys (`school_id`, `canonical_url`, `name`, optional `city`/`state`/`mascot`/`mascot_url`; `subscriptions` list of `{sport, gender, level}`)
- `custom_components/maxpreps/strings.json` + `translations/en.json` — search/school/subscriptions steps, errors, abort reasons
- `tests/test_config_flow.py` — fixture-transport coverage for empty query, no results, Centennial Roswell picker/subscriptions, duplicate abort, Saint retry, Pike County, invalid selector, zero sports

**Flow steps**

| Step | Purpose |
|------|---------|
| `user` | Short-name query; empty → field error (no fetch); zero results → `no_results`; transport/parser → `search_failed` |
| `school` | Picker label `Name \| City, State` · mascot (location degraded when city/state absent); `async_set_unique_id` + `_abort_if_unique_id_configured` before school-home fetch; stale selector values rejected by HA schema (no fetch) |
| `subscriptions` | Multi-select of `TeamSeason.display_label`; at least one required; `async_create_entry` with identity in `data`, subscriptions in `options` |

**Entry shape (Q4 = options, not subentries)**

- `unique_id` = `school_id`
- `data`: stable school identity (no `sport_season_id`)
- `options.subscriptions`: `[{sport, gender, level}, …]` only — no season, no rotating provider IDs

**Q2 (decided)**

- Subscription key remains `{sport, gender, level}` without season.
- When multiple current-cohort rows share the same key (Centennial Boys Freshman Baseball Spring + Fall), they are **one user-facing school-year program**. Spring/Fall are provider partitions, not competing subscriptions.
- Config flow collapses duplicate keys to **one** selectable row (first in school-home order). Coordinator refresh (Slice 5) resolves the live `TeamSeason` from school-home rows for that subscription.

**Decisions**

- Q2 → one subscription per `(sport, gender, level)`; multi-term provider rows collapsed at config-flow display, not exposed as separate subscriptions and not omitted entirely.
- Q4 silent → one config entry per school; subscriptions in `entry.options` (not HA subentries). Options-flow UI deferred to Slice 7.
- Saint retry stays in `AsyncMaxPrepsClient`; config flow does not reimplement it.
- Invalid school selector values outside the current search-result mapping are rejected by HA `SelectSelector` validation (`InvalidData`) before `get_school_teams` runs.

**Pytest**

| Layer | Command | Result |
|-------|---------|--------|
| Client (`[dev]`, Python 3.12) | `pip install -e ".[dev]" && pytest` | 159 passed (`test_config_flow` / `test_init` / `test_ha_transport` skipped without HA import) |
| Client demo | `python scripts/demo_client.py --fixtures` | OK |
| HA smoke (`[ha]` pins, Python 3.14 required) | `pip install -e ".[ha]" && pytest tests/test_manifest.py tests/test_init.py tests/test_ha_transport.py tests/test_config_flow.py` | Not run on pinned `2026.9.0` here (host has Python 3.12 only). Dev check: `pytest-homeassistant-custom-component==0.13.205` + `homeassistant==2025.1.4` → 17 passed (config flow + manifest + init + ha_transport) |

**Deviations**

- None beyond the post-land Q2 correction: duplicate subscription keys collapse to one option (replacing the interim “omit entire duplicate-key group” behavior).

**PRODUCT drift check**

- None. `PRODUCT.md` untouched. No coordinator, entities, options-flow UI, parser changes, or live HTTP.

## Post-Slice-4 owner clarification (2026-09-02)

The Slice 4 notes above describe what shipped at `d645bc7`. They are **not** rewritten.

What that commit already got right:

- Persisted subscriptions are `{sport, gender, level}` only.
- Duplicate keys are **one** option (collapse), not omitted entirely (the interim omit-all behavior was already replaced).
- Q4 = one school entry; subscriptions in `options`.

What owner review still requires (do not treat Slice 4 notes as the forward contract):

- Option labels still use a **single** row’s `TeamSeason.display_label` (`Boys Freshman Baseball`), not aggregated `(Fall, Spring 26-27)`. Collapse-to-first is the wrong internal model for labels even though persist shape is correct.
- The note “Coordinator refresh resolves the live `TeamSeason`” (singular) is **superseded**. Slice 5 must resolve **all** matching rows for the applicable school year and keep per-term schedules.
- Production applicable year is July 1–June 30 (HA local), not the Slice 1 modal helper. Config flow still used `selectable_team_seasons` at Slice 4; Slice 5 switches picker + coordinator to `year == applicable_school_year` ∩ allowlist.

A narrow **Slice 4a** lands aggregated picker labels + a grouping helper before Slice 5. Owner PRODUCT updates for §3.2 / §27 H / §27 J landed in this documentation sweep, not in Slice 4’s commit.

## Slice 4a

**Goal:** Config-flow picker labels list every MaxPreps term + school year for multi-term programs while persisted subscriptions remain `{sport, gender, level}` only.

**Delivered**

- `custom_components/maxpreps/programs.py`: `SchoolYearProgram` value object and `group_school_year_programs()` grouping helper.
- Label format: `{gender} {level} {sport} ({terms} {year})` with terms ordered Fall → Winter → Spring → Summer → other names (case-insensitive), deduplicated.
- `config_flow.py` uses grouped programs instead of collapse-to-first + `TeamSeason.display_label`.
- `TeamSeason.display_label` unchanged (short model label without parenthetical).
- `tests/test_programs.py` helper unit tests; `tests/test_config_flow.py` updated for parenthetical labels and subscription-key sport parsing.

**Persist shape:** unchanged — `options[CONF_SUBSCRIPTIONS]` entries are `{sport, gender, level}` only.

**Not in this slice:** July 1 applicable-school-year switching, coordinator, options-flow UI, parsers, live MaxPreps HTTP.

**Tests:** Layer 1 (`[dev]`, Python 3.12): 186 passed; fixture demo OK.

Legacy HA dev check (`homeassistant==2025.1.4`): functional HA tests passed, but pytest-homeassistant-custom-component teardown hit a pre-existing background-thread cleanup assertion. This environment is not the Phase 3 compatibility target.

Target Layer 2 (`homeassistant==2026.9.0`, Python 3.14): not yet run on this host.

## Slice 5

**Goal:** One `DataUpdateCoordinator` per school entry; resolve each subscribed `{sport, gender, level}` to **all** matching `TeamSeason` rows for the applicable school year; fetch each term’s schedule; entry-wide vs per-program/per-term failure isolation; 12h polling.

**Delivered**

- `custom_components/maxpreps/school_year.py`: pure `applicable_school_year(date)` (July 1–June 30) and `homeassistant_local_date(hass)` via `get_time_zone(hass.config.time_zone)`.
- `custom_components/maxpreps/selection.py`: `team_seasons_for_applicable_year()` (allowlist ∩ `year == applicable_year`).
- `custom_components/maxpreps/coordinator.py`: `MaxPrepsDataUpdateCoordinator`, per-program `ProgramSnapshot`, per-term `TermSnapshot` with `TermRefreshStatus` (`refreshed` / `stale` / `error`) and `ProgramResolutionStatus` (`resolved` / `unresolved`).
- `config_flow.py`: picker filter switched from Slice 1 modal cohort to applicable year ∩ allowlist; removed `CurrentCohortAmbiguousError` abort path.
- `__init__.py`: `async_setup_entry` stores coordinator on `entry.runtime_data`, first refresh, unload (lazy HA imports to keep Layer 1 import-safe).
- `const.py`: `UPDATE_INTERVAL = timedelta(hours=12)`.
- Tests: `tests/test_school_year.py`, `tests/test_coordinator.py`, config-flow date freeze + future-year `no_supported_sports`; `tests/test_init.py` fixture-injected entry.

**Snapshot shape:** `MaxPrepsCoordinatorData` holds `programs[]` each with `terms[]` carrying `team_season`, optional `schedule`, status, typed error metadata, and `last_success_at`. Freshman baseball keeps **two** `TeamSeason` rows (Fall + Spring) with separate schedule fetches — never collapsed to `[0]`.

**Preflight (before coordinator wiring)**

- Interpreter: Python 3.14.6 (`ghcr.io/home-assistant/home-assistant:2026.9.0` image; host has no native `python3.14`).
- Commands (two-step install per `HA_DEVELOPMENT.md`):

  ```bash
  python3 -m pip install pytest-homeassistant-custom-component==0.13.362
  python3 -m pip install homeassistant==2026.9.0
  python3 -m pip install -e .
  PYTHONPATH=<repo> python3 -m pytest --import-mode=importlib --rootdir=<repo> \
    tests/test_manifest.py tests/test_init.py tests/test_ha_transport.py \
    tests/test_config_flow.py tests/test_programs.py
  ```

- Preflight result: **28 passed** (green before coordinator). HA-compat fix during Slice 5: `homeassistant_local_date` must pass `get_time_zone(hass.config.time_zone)` to `dt_util.now`, not `hass.config`.

**Tests (post-coordinator)**

- Layer 1 (`[dev]`, Python 3.12 Docker): **172 passed**, 4 skipped (HA tests); `python scripts/demo_client.py --fixtures` OK.
- Layer 2 (`homeassistant==2026.9.0`, Python 3.14.6 Docker, `PYTHONPATH` + `--import-mode=importlib`): preflight 28 passed; full slice suite including `test_coordinator.py` **41 passed**.

**Deferred:** sensors (Slice 6), options-flow UI (Slice 7), daily-until-published rollover polling (Slice 11), Lovelace card, PRE/IN/POST/OFF entity states.

**PRODUCT drift check:** None. `PRODUCT.md` untouched. No parser/signature/`display_label` changes, no live MaxPreps HTTP.
