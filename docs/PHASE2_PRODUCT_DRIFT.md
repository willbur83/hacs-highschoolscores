# Phase 2 — PRODUCT.md drift report

Facts for product-owner review. This document does not amend [PRODUCT.md](PRODUCT.md); open items stay open until the owner decides.

Phase 2 delivered a fixture-driven MaxPreps Python client (`custom_components/maxpreps/`) with tests and a fixtures-only demo. Home Assistant integration work has not started.

---

## A. Confirmed PRODUCT ↔ empirical/implementation mismatches

### Search query and picker (PRODUCT §30, §3.2)

- **PRODUCT §30** example search string: `"Centennial High School, Roswell GA"`.
- **Empirical (MAXPREPS_RESEARCH.md):** short-name search (`Centennial`) plus disambiguation picker; qualified strings with city/state or `"High School"` often return empty results (fixture transport maps `Centennial High School` → empty).
- **Implementation:** `MaxPrepsClient.search_schools(query)` with no `state=` facet; Saint → St. retry for leading `Saint` only (research 16b); city/state optional on `School` rows (§3 picker updated in PRODUCT for incomplete location display).

### Client method signatures (PRODUCT §10 vs Phase 2 client)

| PRODUCT §10 (eventual) | Phase 2 implementation |
|------------------------|---------------------------|
| `search_schools(query, state=None)` | `search_schools(query: str) -> list[School]` — no `state=` parameter |
| `get_school_teams(school_id)` | `get_school_teams(school: School) -> list[TeamSeason]` — uses payload `canonical_url`, not a bare `school_id` string |
| `get_schedule(team_id, season=None)` | `get_schedule(team: TeamSeason) -> Schedule` — composite `(school_id, sport_season_id)` identity; no `team_id` or `season=` fetch key |

Normalized models are `School`, `TeamSeason`, `Game`, `Schedule` — not PRODUCT’s eventual `team_id`-centric API.

### Timestamps (PRODUCT §30 example vs implementation)

- **PRODUCT §30** example game `date`: `"2026-08-20T16:30:00-04:00"` (offset-aware).
- **Implementation:** `Game.date` is timezone-**naive** `datetime`; no school/state/JSON-LD timezone attachment (PHASE2_PLAN §6 item 1 remains unresolved).

### Sport-agnostic ambition vs Phase 2 scope (PRODUCT §8, §15)

- **PRODUCT:** integration should be as sport-agnostic as MaxPreps data allows.
- **Phase 2:** generic team discovery from `sportSeasons[]` (all sports listed, including tennis/golf/track); schedule decoding validated for conventional head-to-head columnar `contests[]` (arity 41 / participant width 32). Football + baseball are acceptance evidence; volleyball is regression-only; girls basketball fixture is optional extra coverage. Tennis/golf/track schedule pages in fixtures lack `__NEXT_DATA__` / `contests[]` — no schedule decode for those sports.

### Game status vocabulary (PRODUCT §7 / HA PRE·IN·POST·OFF vs client)

- **PRODUCT / HA direction:** `PRE`, `IN`, `POST`, `OFF` lifecycle states with POST retention semantics.
- **Phase 2 client:** `GameStatus` = `deleted` \| `scheduled` \| `final` \| `unknown` only. Unknown `contestState` → `unknown` + `status_message`; no live/in-progress/postponed/cancelled mapping.

### Default cohort / historical seasons

- **PRODUCT** implies user-facing current-team selection and season UX (config flow not built).
- **Implementation:** `get_school_teams` returns **all** `sportSeasons[]` rows (including historical e.g. Pike County `11-12`). Tests and `scripts/demo_client.py --fixtures` explicitly pick `year == "26-27"` — not a product default-season policy.

### Saint → St. search retry (research 16b)

- **Implementation:** one retry when first search is empty and query matches leading `Saint` (rewritten to `St.`).
- **PRODUCT.md:** not described in search or client sections.

### Demo / test output shape (PRODUCT §30 example)

- **PRODUCT §30** team example: `"name": "Centennial Knights"`.
- **Demo (`scripts/demo_client.py --fixtures`):** team block uses `display_label` (e.g. `"Boys Varsity Football"`) from `TeamSeason.display_label`, not school mascot nickname.

---

## B. Product decisions / implementation questions still open

Items from [PHASE2_PLAN.md](PHASE2_PLAN.md) §6 — intentionally unresolved in Phase 2 code:

1. **Kickoff timezone / offset** — naive `date` only; Pensacola-style inconsistencies documented in research; no localization policy.
2. **Live / in-progress, postponed, cancelled** — not observed in fixtures; unknown enum must not be mapped to those states.
3. **HA entity model** — config-entry scope, schedule representation, `PRE`/`POST` retention, adaptive polling, notifications vs state triggers (PRODUCT §27).
4. **Default team-season cohort / school-year rollover / historical-season UX** — enumeration returns all rows; no `teamSeasonPickerData` API or default filter.
5. **UI handling for unsupported sports** — tennis/golf/track enumerated on school home; schedule fetch fails with `NextDataNotFoundError` when Next.js schedule data is absent.
6. **`isPublished: false` semantics** — field stored on `TeamSeason` when present; no production filter from absent samples.
7. **Logo hotlink / HA media behavior** — URL strings only (`team_logo`); no CDN reliability test or image fetch.
8. **Final-score posting latency** — unmeasured; no polling intervals in client.
9. **PRODUCT §30 example query and offsets** — owner may revise PRODUCT or accept demo/research divergence (short name + naive dates).
10. **Qualified search vs short name** — whether PRODUCT §30 should be rewritten to match researched search behavior.

Additional open product questions surfaced during Phase 2:

- Whether HA layer should hide tennis/golf/track after enumeration when schedule decode is unsupported.
- How `PRE`/`IN`/`POST`/`OFF` map from MaxPreps `contestState` when/if live and post-game states are observed.
- HTTP 403/429 transport policy (no-retry) — not exercised in Phase 2 (fixture-only); live transport deferred.

---

*Generated at Phase 2 Slice 12 completion for owner review. Item resolution belongs in PRODUCT.md or a future planning slice, not silent code changes.*
