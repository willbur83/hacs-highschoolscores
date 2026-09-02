# Phase 2 — PRODUCT.md drift report

Owner review completed (Slice 12 follow-up). This document does not amend [PRODUCT.md](PRODUCT.md); PRODUCT edits belong in a separate owner-driven update.

Phase 2 delivered a fixture-driven MaxPreps Python client (`custom_components/maxpreps/`) with tests and a fixtures-only demo. Home Assistant integration work has not started.

---

## A. Confirmed PRODUCT ↔ empirical mismatches (PRODUCT should change)

Items where researched MaxPreps behavior and the Phase 2 client show PRODUCT.md wording is out of date. The owner confirmed **PRODUCT should change** — these are not implementation defects.

### §30 search example (also §3.2 picker flow)

- **PRODUCT §30** example search: `"Centennial High School, Roswell GA"`.
- **Empirical:** short-name search (`Centennial`) plus disambiguation picker; qualified strings with city/state or `"High School"` often return empty (fixture transport maps `Centennial High School` → empty).
- **Phase 2 client:** `search_schools(query)` with no `state=` facet; city/state optional on `School` rows (§3 picker display already updated for incomplete location).
- **Owner decision:** Short school name → result picker is the intended UX. **Revise PRODUCT §30** (and related search examples) to match researched behavior.

### §10 client method signatures

| PRODUCT §10 (current wording) | Phase 2 client (researched model) |
|-------------------------------|-----------------------------------|
| `search_schools(query, state=None)` | `search_schools(query: str) -> list[School]` |
| `get_school_teams(school_id)` | `get_school_teams(school: School) -> list[TeamSeason]` — fetch via payload `canonical_url` |
| `get_schedule(team_id, season=None)` | `get_schedule(team: TeamSeason) -> Schedule` — identity `(school_id, sport_season_id)`; no `team_id` or `season=` fetch key |

Normalized models are `School`, `TeamSeason`, `Game`, `Schedule`.

- **Owner decision:** Current `School` / `TeamSeason` API reflects the discovered identity and fetch model better than §10’s `team_id`-centric sketch. **Revise PRODUCT §10** when the client API is next documented in PRODUCT.

---

## B. Open decisions — later layers and unresolved technical policy

Not PRODUCT drift against Phase 2 code. These stay open for a future slice; Phase 2 correctly left them unresolved ([PHASE2_PLAN.md](PHASE2_PLAN.md) §6).

### Technical policy (client / normalization)

1. **Kickoff timezone / offset** — `Game.date` is timezone-naive today. PRODUCT’s offset-aware kickoff intent is desirable; localization policy is unsolved (Pensacola-style inconsistencies in research). **Owner decision:** keep open.
2. **Live / in-progress, postponed, cancelled** — not observed in fixtures; unknown `contestState` must not be mapped to those states without evidence.
3. **`isPublished: false` semantics** — stored on `TeamSeason` when present; no production filter from absent samples.
4. **Logo hotlink reliability** — URL strings only (`team_logo`); no CDN test or image fetch.
5. **Final-score posting latency** — unmeasured; no polling intervals in the client.
6. **HTTP 403/429 transport** — no-retry policy not exercised in Phase 2 (`FixtureTransport` only); live transport deferred.

### Home Assistant layer (Phase 3+)

7. **HA entity model** — config-entry scope, schedule representation, adaptive polling, notifications vs state triggers (PRODUCT §27).
8. **HA lifecycle (`PRE` / `IN` / `POST` / `OFF`)** — Phase 2 normalizes provider state to `scheduled | final | deleted | unknown`. Mapping to HA-facing lifecycle is **Phase 3 product/design**, not current client drift. **Owner decision:** open HA-layer design.
9. **Default team-season cohort / school-year rollover / historical-season UX** — `get_school_teams` returns all `sportSeasons[]` rows; tests and demo explicitly pick `year == "26-27"`. Default-season policy belongs in config flow / UI, not Phase 2 client. **Phase 3 owner decision (2026-09-02):** applicable school year is July 1–June 30; subscriptions are `{sport, gender, level}` and may match multiple provider terms. See [PHASE3_PLAN.md](PHASE3_PLAN.md) owner amendments and [PRODUCT.md](PRODUCT.md) §3.2 / §27 H / §27 J. This bullet is not rewritten as a Phase 2 result.
10. **UI for unsupported sports** — tennis/golf/track enumerated on school home; schedule fetch fails with `NextDataNotFoundError` when Next.js schedule data is absent. **Owner decision:** intentionally deferred; not a Phase 2 defect.

### Phase 2 implementation boundaries (document, do not treat as PRODUCT weakness)

- **Sport-agnostic ambition (PRODUCT §8):** team discovery from `sportSeasons[]` is sport-agnostic; v1 schedule decode is intentionally limited to conventional head-to-head columnar `contests[]` (arity 41 / width 32). Football + baseball are acceptance evidence; volleyball regression-only; tennis/golf/track have no schedule decode in fixtures. **Owner decision:** not product drift — document the implementation boundary without weakening PRODUCT ambition.
- **Saint → St. search retry (research 16b):** one retry when the first empty result matches leading `Saint`. **Owner decision:** implementation detail; PRODUCT need not prescribe it.
- **Demo output (`scripts/demo_client.py --fixtures`):** uses `display_label` (e.g. `"Boys Varsity Football"`), not PRODUCT §30’s `"Centennial Knights"` example. **Owner decision:** demo artifact only — do not infer product behavior from the demo; eventual UI should expose both school/team identity and sport label.

---

*Owner review recorded in PHASE2_PLAN Slice 12 Implementation Notes. PRODUCT.md updates for section A items are owner-driven; section B items remain open for Phase 3 planning.*
