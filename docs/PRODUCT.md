## Product Requirements & Technical Direction

**Document role:** Current product truth — resolved product decisions, future goals, and explicitly open questions. This is not a Phase 1 exploration draft and not a Phase 3 implementation log.

**Status labels** used below:

- **Current / Decided** — landed in Phase 2 (MaxPreps client) and/or Phase 3 (Home Assistant integration) and owner-approved.
- **Future / Desired** — still a product goal; **not** implemented. Do not treat as shipped behavior.
- **Open / TBD** — unresolved. Do not invent an answer during implementation.

Phase 3 closed its completion gate on 2026-09-09 (Layer 3 owner sandbox). Historical implementation detail lives in [PHASE3_PLAN.md](PHASE3_PLAN.md). Empirical MaxPreps findings live in [MAXPREPS_RESEARCH.md](MAXPREPS_RESEARCH.md).

### Current product snapshot (Phase 3)

| Topic | Status | Landed behavior |
|-------|--------|-----------------|
| Config entry | **Current / Decided** | One config entry per school (`unique_id` = MaxPreps `school_id`). Duplicate school → abort. Multiple schools are independent entries. |
| Subscription identity | **Current / Decided** | Persist `{sport, gender, level}` only. Not `sportSeasonId`, term, year, or team-season URL. |
| Multi-term programs | **Current / Decided** | One program may resolve to multiple `TeamSeason` rows in the applicable school year (e.g. Freshman Baseball Fall + Spring). One subscription, one entity. |
| Supported formats | **Current / Decided** | Evidence-based allowlist: **Football, Baseball, Basketball, Volleyball**. Unvalidated sports are omitted from the picker, not grayed out. |
| School year | **Current / Decided** | July 1–June 30 in Home Assistant’s local timezone (`2026-07-01`–`2027-06-30` → `26-27`). Subscriptions survive rollover. Until the new year is published, retain last-good data and poll daily, then return to 12h. |
| Device / entity | **Current / Decided** | Device = school. One sensor per subscribed program. Unique ID `{school_id}:{gender}:{level}:{sport}`. Entity name `{gender} {level} {sport}` (no term/year parenthetical). |
| Compact entity state | **Current / Decided** (interim) | `scheduled` \| `final` \| `unknown` derived from last/next. **Open / TBD:** Q1 Team Tracker `PRE` / `IN` / `POST` / `OFF` — do **not** invent that mapping. |
| last_game / next_game | **Current / Decided** | Both exposed as attributes when derivable, across all terms of the program. `last_game` = latest `final`; `next_game` = earliest `scheduled` (provider-naive datetime order; not compared to wall clock). |
| Full schedule | **Current / Decided** | Source of truth is coordinator `programs[].terms[]` (`runtime_data`). Never serialize the full schedule into entity **state**. |
| Logos | **Current / Decided** | Automatic school `entity_picture` (search `mascot_url`, else first `Schedule.team_logo`). Optional override: HTTPS URL or `/local/` path (override wins). Opponent logo is optional on last/next when the provider supplies it. Missing logos never fail scores. |
| Polling | **Current / Decided** | ~12h normal coordinator interval; daily only while waiting for unpublished new-year schedules. Entities do not fetch. |
| Failure / retention | **Current / Decided** | Entry-wide discovery failure retains last successful snapshot. One program (or one term) failing does not collapse the school or sibling sports. Last-good schedules are retained. |
| Datetimes | **Current / Decided** | Provider `Game.date` is timezone-naive. Not school-local wall time; not offset-correct kickoff. Do not invent TZ correction. |
| Live scores | **Current / Decided** | No live-score guarantee. Unknown `contestState` stays `unknown`. |
| Multi-school | **Current / Decided** | Independent config entries, devices, and coordinators. Reload of one school does not disturb another. |
| Custom Lovelace card | **Future / Desired** | Phase 4. Phase 3 exposes the data contract only. |
| Adaptive / game-day polling | **Future / Desired** | Not implemented. Conservative 12h polling is current. |
| Calendar entities | **Future / Desired** | Blocked by timezone-naive provider datetimes. |
| HACS store listing | **Future / Desired** | Phase 5. Manual/custom-component install only today. |

---

## 1. Product Summary

Build a public, open-source Home Assistant custom integration that connects Home Assistant to public MaxPreps school sports data.

The integration should make it easy for a Home Assistant user to select their school and one or more teams/sports, then expose schedule and score/result data as Home Assistant entities suitable for dashboards, automations, and notifications.

The primary product goal is:

> Make school sports schedules and final scores feel like native Home Assistant data.

The integration should be as sport-agnostic as the MaxPreps data allows. Sport-specific behavior should only be introduced where actual MaxPreps data differences require it.

**Current / Decided:** Phase 1 research and Phase 2 client work defined an evidence-based supported-format allowlist (Football, Baseball, Basketball, Volleyball). Adding another sport later requires fixture/parser evidence, not a product redesign.

**Future / Desired:** Keep the same generic schedule/result pipeline as more sports are validated. Do not treat the current allowlist as a permanent sport ceiling.

---

# 2. Primary Use Cases

## 2.1 Team Tracker-Style Dashboard

A user should be able to display a selected team's current or next relevant game in a dashboard card similar in concept to Home Assistant Team Tracker.

Typical display information:

- School/team name
    
- Team logo, if available
    
- Opponent
    
- Opponent logo, if available
    
- Game date/time
    
- Home/away designation
    
- Venue/location, if available
    
- Team record, if available
    
- Current result or final score
    
- Win/loss result
    
- Relevant game status
    

Example:

```
Centennial Knights
Varsity Football

vs Alpharetta
Friday, September 4
7:30 PM

Centennial: 2-0
```

After the game:

```
FINAL

Centennial 54
Johns Creek 18

W
```

**Current / Decided:** Program sensors expose compact state plus `last_game` / `next_game` attributes (and school `entity_picture`) so native or existing Home Assistant cards can show a current/next game without a custom frontend.

**Future / Desired:** A polished Team Tracker-style Lovelace card (project Phase 4). The integration itself does not ship a custom card today. The `PRE` / `FINAL` prose in the examples above is illustrative dashboard copy, **not** the current entity state vocabulary (see §5 and Q1).

---

## 2.2 Full Schedule View

A user should be able to view the team's full season schedule and results.

Preferred UX:

- The primary game card is visible on the dashboard.
    
- Clicking or tapping the card can lead to a full schedule view.
    

Possible implementations include:

- More-info dialog populated with schedule data
    
- A secondary schedule entity/card
    
- Navigation to a dedicated dashboard/subview
    
- A future custom card with expandable schedule support
    

**Current / Decided:** Full school-year schedule/result data lives on the coordinator contract `programs[].terms[]` (one term = one `TeamSeason` + schedule). Entity **state** is compact and does not contain the schedule list.

**Future / Desired:** more-info, a dedicated subview, or a custom card that reads that coordinator contract.

The exact frontend implementation is **Open / TBD**. Calendar entities are **Future / Desired** and are blocked by timezone-naive provider datetimes — do not treat calendar support as shipped.

---

## 2.3 Schedule-Only Dashboard

A user should be able to ignore the Team Tracker-style current-game card and display only a schedule.

Example:

```
Centennial Varsity Football

Aug 20  Dunwoody         W 23-21
Aug 28  Johns Creek      W 54-18
Sep 4   Alpharetta       7:30 PM
Sep 11  @ South Forsyth  7:30 PM
...
```

The data model should not assume the "current game card" is the only presentation. A schedule-only dashboard can consume `programs[].terms[]` (and last/next attributes) without a custom card.

---

## 2.4 Game Notifications and Automations

Users should be able to build standard Home Assistant automations around game data.

Examples:

- Notify 30 minutes before kickoff.
    
- Announce that a game is starting.
    
- Notify when a final score becomes available.
    
- Announce the final score over Sonos.
    
- Trigger lighting or other home automations after a win.
    
- Display today's game on another dashboard.
    
- Notify if a scheduled game date/time changes.
    

The integration should favor ordinary Home Assistant state and attribute changes rather than requiring custom automation APIs.

**Current / Decided:** Automations can trigger on compact state (`scheduled` / `final` / `unknown`) and on `last_game` / `next_game` attribute changes after a coordinator refresh. Provider datetimes are timezone-naive, so “30 minutes before kickoff” is **not** a guaranteed absolute-time automation.

**Future / Desired:** A custom event such as `maxpreps_game_final` may eventually be useful, but is not required while normal entity state/attribute transitions provide the same functionality. Adaptive polling to detect finals sooner is also **Future / Desired** (see §12).

---

# 3. Installation and Configuration

## 3.1 Distribution

**Current / Decided:** Public GitHub repository (`willbur83/hacs-highschoolscores`). The integration is a Home Assistant custom component configured entirely through the UI. No YAML is required.

**Future / Desired:**

```
GitHub public repository
    ↓
HACS custom repository
    ↓
HACS default repository/listing if accepted
```

HACS packaging and store listing are Phase 5. Long-term Home Assistant Core inclusion is not an initial goal.

The integration should behave like a normal Home Assistant integration after installation.

---

## 3.2 Configuration Flow

Configuration should be school-first.

**Current / Decided:** One **Add Integration** action creates one config entry for one school. The user then subscribes that school to one or more allowlisted programs. Additional schools are additional Add Integration runs (independent entries). Duplicate `school_id` is rejected.

Desired user experience:

```
Settings
→ Devices & Services
→ Add Integration
→ MaxPreps
```

Then:

### Step 1: Find School

**Current / Decided:** The user searches with a **short school name** (for example `Centennial`), then picks from disambiguated results. Qualified strings such as `"Centennial High School, Roswell GA"` or `"High School"` often return empty on MaxPreps and are **not** the intended query.

Potential additional city / state / ZIP filter fields are **Future / Desired** — not shipped. Disambiguation is the result picker.

The Home Assistant school picker should show each result approximately as **`School Name | City, State`**, with an optional mascot when present (for example `Centennial | Roswell, GA · Knights`). When MaxPreps omits city or state, the picker degrades gracefully (state-only, city-only, or “Location unavailable”) rather than dropping the school or failing the search.

Example result row:

```
Centennial High School
Roswell, Georgia
```

### Step 2: Discover Teams

After selecting the school, the integration lists **allowlisted** programs that have at least one MaxPreps `sportSeasons[]` row for the applicable school year.

**Current / Decided:** Football, Baseball, Basketball, Volleyball only. Unvalidated sports (soccer, softball, tennis, golf, track, …) are omitted, not shown disabled.

### Step 3: Select Teams

User may select one or more **programs**. Separate setup flows per program are not required.

**Current / Decided:** Sports are added or removed later through the options flow (`OptionsFlowWithReload`), not YAML or manual entity edits.

### Subscriptions are school-year programs (decided 2026-09-02)

A user subscription is:

```
school + sport + gender + level
```

Examples: Centennial Boys Varsity Football; Centennial Boys Freshman Baseball.

It is **not** an individual MaxPreps `sportSeasonId`, Spring/Fall term, or team-season URL. Persist `{sport, gender, level}` only.

When MaxPreps lists multiple terms in the same school year for that program (for example Boys Freshman Baseball Fall 26-27 and Spring 26-27), those are **one subscription**. Do not make the user pick Fall vs Spring. Do not omit the program because multiple terms exist.

The setup picker should show informational term(s) and school year, for example:

```
Boys Varsity Football (Fall 26-27)
Boys Varsity Baseball (Spring 26-27)
Boys Freshman Baseball (Fall, Spring 26-27)
```

The parenthetical is context only. It does not create extra subscriptions.

At refresh, the integration gathers **all** matching current-school-year team-season rows and their schedules, preserving term/source so a later expanded schedule view can section by term. Do not flatten away the term distinction internally.

Supported sports in the picker remain the evidence-based head-to-head allowlist; this decision does not add soccer, softball, or individual/meet sports.

---

# 4. Home Assistant Device and Entity Model

## 4.1 School as Device

**Current / Decided:**

```
Device:
Centennial High School
```

The device represents the school (`DeviceInfo.identifiers = {(domain, school_id)}`). `configuration_url` is the school’s MaxPreps `canonical_url`.

Selected **programs** become sensors on that device. Example (allowlisted programs only):

```
Centennial High School

sensor.centennial_boys_varsity_football
sensor.centennial_boys_varsity_baseball
sensor.centennial_boys_freshman_baseball
```

One Home Assistant device per school, not per team or per MaxPreps term. Multi-term programs (Fall + Spring) are still **one** sensor. Entity unique ID is `{school_id}:{gender}:{level}:{sport}` and is stable across school-year rollover.

---

# 5. Team Entity

Each selected program exposes a primary sensor.

Example:

```
sensor.centennial_boys_varsity_football
```

## 5.1 Compact state and last / next games

**Current / Decided (interim — Q1 still open):** Entity **state** is compact provider vocabulary only:

```
scheduled
final
unknown
```

Derivation:

- If `next_game` exists → `scheduled`
- Else if `last_game` exists → `final`
- Else → `unknown`

`last_game` and `next_game` are **both** attributes when derivable (across all terms of the program). Phase 4 must not depend on a single “relevant game” state. Deleted contests are excluded from last/next. Compact state does **not** use `deleted`.

`last_game` / `next_game` ordering uses provider-naive datetimes only (not compared to Home Assistant wall clock). That is a display heuristic, not timezone-correct scheduling.

**Open / TBD (Q1):** Do **not** invent `PRE` / `IN` / `POST` / `OFF`. Those labels remain a Team Tracker-style sketch, not landed entity state. Owner disposition of Q1 is required before changing compact state.

The sketch below is **Future / Desired** only, retained so Q1 is not silently discarded:

### PRE (not implemented)

Upcoming scheduled game.

### IN (not implemented)

Game appears to be actively in progress.

This state is dependent on whether MaxPreps provides sufficiently reliable live/in-progress information.

Live tracking is not a core v1 requirement. **Current / Decided:** no live-score guarantee; unknown `contestState` stays `unknown`.

### POST (not implemented)

Most recently completed game.

### OFF (not implemented)

No relevant scheduled/current/recent game (out of season, schedule unavailable, or no upcoming game known).

Current compact `unknown` covers “nothing derivable,” which is **not** the same as a decided `OFF` mapping.

---

# 6. Team Entity Attributes

**Current / Decided** attributes on the program sensor (omit when unsupported; missing data must not fail the entity):

```
school_id
school_name
sport
gender
level
year                 # applicable school year (e.g. 26-27); not a MaxPreps term
display_label        # "{gender} {level} {sport}" — no term/year parenthetical
team_record          # omit if untrustworthy
attribution
last_game            # object when derivable
next_game            # object when derivable
```

School logo is `entity_picture` on the sensor (not a required state attribute). Do not assume a single `season` string: a program may have multiple provider terms.

`last_game` / `next_game` objects, when present, include:

```
id
date                 # naive ISO string
status
opponent_name
opponent_id          # optional
home_away
team_score           # optional
opponent_score       # optional
result               # optional
venue                # optional
game_url             # optional
opponent_logo        # optional
season               # optional MaxPreps term name of the source row
```

**Future / Desired** additional chrome (not required on the entity today):

```
team_name
conference
region
rank
source_url
```

Attributes should only be populated when supported by MaxPreps data.

Missing data should not cause the entity to fail.

---

# 7. Schedule Data

**Current / Decided:** The integration exposes full school-year schedule/result data on the coordinator:

```
MaxPrepsCoordinatorData.programs[].terms[]
```

Each term carries a `TeamSeason`, optional `Schedule` (`games[]`), and refresh status. Multi-term programs keep Fall/Spring (etc.) distinct internally so a later expanded view can section by term. Do not flatten away term distinction as the only stored form.

Entity **state** must stay compact. Do not serialize `terms[]` or the full games list into HA entity state. Slice/Phase 4 card work should read coordinator / `runtime_data` (and last/next attributes), not invent one entity per contest.

A normalized game object looks conceptually like:

```
id:
date:          # timezone-naive
status:        # scheduled | final | deleted | unknown  (provider)

team_name:
opponent_name:

home_away:

team_score:
opponent_score:

result:

venue:

game_url:
opponent_logo: # optional
```

```
id:
date:
status:

team_name:
opponent_name:

home_away:

team_score:
opponent_score:

result:

venue:
location:

game_url:
```

The model should avoid sport-specific fields unless they are necessary.

Optional sport-specific detail can later be represented separately, for example:

```
details:
  inning:
  quarter:
  period:
```

The generic schedule/result model should remain usable without those fields.

---

# 8. Sport-Agnostic Design

**Current / Decided:** Normal setup lists only sports whose schedule representation has been empirically validated against the shared `contests[]` parser:

```
Football
Baseball
Basketball
Volleyball
```

Football and baseball are the Phase 3 acceptance targets; basketball and volleyball may appear in the selector. Soccer, softball, lacrosse, and other “likely” team sports are **not** in the picker until they have the same class of fixture evidence. Tennis, golf, track, and other meet/individual formats are omitted (schedule decode unproven).

**Future / Desired:** Remain as sport-agnostic as the MaxPreps data allows. Do not hardcode sport-specific behavior until the source data requires it. Adding a sport is an evidence/test change, not a product redesign.

The default assumption remains:

> If MaxPreps represents a team's season as dated contests with an opponent and result **on the validated Next.js `contests[]` path**, the integration should support it through the same pipeline.

Potential exceptions requiring investigation before they can join the allowlist:

- Golf
    
- Tennis
    
- Wrestling
    
- Swimming
    
- Track and field
    
- Cross country
    
- Gymnastics
    
- Multi-team meets
    
- Tournaments
    
- Invitationals
    

These sports should not be excluded from **future** investigation, but they are **not** in the current picker.

Exploration (Phase 1) determined that Centennial tennis/track schedule pages were legacy ASPX without `__NEXT_DATA__` contests. They remain out of the allowlist until a populated Next.js (or other proven) decode path exists.

---

# 9. MaxPreps Data Connector

The most important early engineering work is the MaxPreps client.

The client should be independent of Home Assistant wherever practical.

Conceptual boundary:

```
MaxPreps
   ↓
MaxPrepsClient
   ↓
Normalized Python models
   ↓
Home Assistant DataUpdateCoordinator
   ↓
Entities
```

The Home Assistant layer should not contain raw parsing logic for MaxPreps payloads.

---

# 10. MaxPreps Client Responsibilities

**Current / Decided** (Phase 2 client; HA uses the same models via an async facade):

## School Search

```
search_schools(query: str) -> list[School]
```

Short-name search. No `state=` facet. Returns normalized `School` rows (`school_id`, `canonical_url`, name, optional city/state/mascot/`mascot_url`).

## School Team Discovery

```
get_school_teams(school: School) -> list[TeamSeason]
```

Fetches `school.canonical_url` and returns **all** `sportSeasons[]` rows. Current-school-year and allowlist filtering belong to the Home Assistant config flow / coordinator, not this method.

## Team Schedule

```
get_schedule(team: TeamSeason) -> Schedule
```

Fetches the established `schedule/` child of the team-season `canonical_url`. Identity is `(school_id, sport_season_id)` plus payload `canonical_url`. There is no `team_id` or `season=` fetch key.

`Schedule` carries `games[]`, optional `team_logo`, optional `team_record`. `Game.date` is timezone-naive. `Game.status` is `scheduled | final | deleted | unknown`. Optional `opponent_logo` when the provider supplies an HTTPS mascot URL.

Do not revive `team_id`-centric sketches. Exact transport is injectable (sync `Transport` for tests; async HA session in production).

---

# 11. Polling Strategy

**Current / Decided:** Conservative fixed coordinator interval.

```
Normal operation: timedelta(hours=12)   # ~2 cycles per day per school entry
Rollover wait:    timedelta(days=1)     # only while the applicable year has no published schedules
```

Entities do not poll (`CoordinatorEntity`). One cycle per school fetches school home once, then each matching term’s schedule. Multiple programs on the same school share the school-home request.

Do not treat undocumented public web data as a real-time sports API.

**Future / Desired:** Further request sharing or HTTP caching if evidence shows duplicate upstream work. Adaptive game-window polling is **not** current (see §12).

---

# 12. Adaptive Game-Day Polling

**Future / Desired — not implemented.** Do not treat this section as production behavior.

More frequent polling may be useful after a scheduled game is expected to have finished.

Example concept:

```
Normal:
refresh every ~6 hours

Known game scheduled:
7:30 PM

Before game:
normal cadence

Expected completion window reached:
begin temporary result checks

Result still not posted:
retry periodically

Final result discovered:
stop accelerated polling
return to normal cadence
```

Potential result-check interval:

```
15-30 minutes
```

Exact values are TBD and should be conservative.

The purpose is not live score tracking.

The purpose is:

> Detect a final result within a reasonably useful period after it becomes available.

**Current / Decided:** Production polling stays at ~12h (daily during unpublished new-year wait). Optional Spike H observation (`scripts/explore/observe_gameday.py`) is research-only and is not wired into the coordinator.

---

# 13. Final Score Detection

Final score detection is a key automation use case.

**Current / Decided:** Provider `Game.status` is `scheduled | final | deleted | unknown`. Compact entity state is `scheduled | final | unknown`. When a game becomes `final` on a refresh, `last_game` (and compact state, if no `next_game` remains) update so ordinary Home Assistant automations can fire. Detection latency is bounded by the 12h (or daily rollover-wait) interval — not by adaptive polling.

**Open / TBD:** `in progress`, `postponed`, and `cancelled` are **not** mapped. Those `contestState` values were not observed in research fixtures. Unknown enums stay `unknown`. Do not invent mappings.

The following `PRE → POST` example is **not** current entity behavior (Q1 still open). Current automations should trigger on `scheduled` / `final` / `unknown` and on `last_game` / `next_game` attribute changes:

```
team_score: 54
opponent_score: 18
result: W
```

---

# 14. Game Start Notifications

Game start notifications should be primarily schedule-driven.

**Current / Decided:** `next_game.date` is a timezone-naive ISO string suitable for **display and ordering**. It is **not** a reliable school-local or event-local wall time and is **not** an offset-correct kickoff timestamp. Automations that treat it as an absolute instant (including “30 minutes before kickoff”) are best-effort and may be wrong for some schools (Pensacola-style research mismatch). Do not offer a user timezone setting as a correctness fix.

If MaxPreps provides a naive datetime such as Friday 7:30 PM, Home Assistant may still *attempt* schedule-driven triggers, but the integration must not document that as guaranteed.

The integration must clearly distinguish:

```
scheduled start time (naive provider datetime)
```

from:

```
confirmed live/in-progress state
```

if both eventually exist. Confirmed live state is **not** current.

---

# 15. Live Score Support

**Current / Decided:** Live scoring is not supported and is not documented as guaranteed. Compact state has no `IN`. Unknown `contestState` stays `unknown`.

If MaxPreps later exposes usable live state/score data through the same connector, the integration **may** expose it (**Future / Desired**).

However:

- no aggressive polling
    
- no promise of real-time updates
    
- no design decisions should depend on live scoring being available
    
- documentation should clearly describe live data as best-effort if supported
    

Primary guaranteed behavior should focus on:

- schedules
    
- results
    
- final scores
    

---

# 16. Standings, Rankings, and Other Data

**Future / Desired** (not required for Phase 3 success; not shipped as entities):

Potential future/bonus features include:

- standings
    
- region standings
    
- rankings
    
- playoff brackets
    
- roster
    
- team statistics
    
- player statistics
    

These are not required for initial success.

However, the client architecture should avoid making them unnecessarily difficult to add later.

If standings or rankings fall naturally out of the same MaxPreps data exploration and require little incremental work, they may be included.

Schedule and score reliability takes priority.

---

# 17. Dashboard Requirements

The integration should support at least three presentation patterns.

## Pattern A: Current/Next Game Card

Team Tracker-like display. **Current / Decided:** `last_game` + `next_game` + compact state + `entity_picture` exist for this. **Future / Desired:** a polished custom card (project Phase 4).

## Pattern B: Full Schedule

Season schedule/results. **Current / Decided:** coordinator `programs[].terms[]`. **Future / Desired:** a user-visible expanded view.

## Pattern C: Both

Primary card that leads to or accompanies full schedule. **Future / Desired.**

The integration should expose enough structured data to support all three without requiring users to create REST sensors or templates themselves.

---

# 18. Custom Lovelace Card

**Future / Desired.** A custom frontend card is not required for Phase 3 and was not built. Project **Phase 4** is where a last/next card may be planned. Do not confuse the card-sequencing sketch below with project Phase 1/2/3 (research / client / HA integration).

Preferred sequencing:

1. Expose excellent Home Assistant entities and attributes. (**Current / Decided** for Phase 3.)
2. Determine whether native cards, Mushroom, Auto Entities, or other existing frontend tools can create the desired experience. (**Future / Desired.**)
3. Only create a custom Lovelace card if it meaningfully improves usability. (**Future / Desired** — project Phase 4.)

Do not couple the backend integration to a custom frontend component.

---

# 19. Error Handling

The integration should fail gracefully.

Expected conditions include:

- MaxPreps unavailable
    
- changed MaxPreps data structure
    
- school search returns nothing
    
- team disappears
    
- schedule unavailable
    
- schedule temporarily empty
    
- game missing score
    
- date/time missing
    
- opponent unknown
    
- cancelled/postponed contests
    
- duplicated contests
    
- changed scheduled game time
    
- MaxPreps deployment changes internal identifiers/build metadata
    

A temporary upstream failure should not erase previously known schedule information.

**Current / Decided:**

- Entry-wide school-home / discovery failure raises `UpdateFailed` and retains the last successful coordinator snapshot (first setup: `ConfigEntryNotReady`).
- A single subscribed program (or one term of a multi-term program) fetch/parse failure does **not** make sibling sports or the school device unavailable.
- Last-good term schedules are retained (`TermRefreshStatus.STALE`); sensors with retained data stay available.
- Unresolved subscriptions (no provider rows for the applicable year) are unavailable as entities, but the subscription itself is kept.
- Missing logos never fail setup or scores.
- Cancelled/postponed remain **Open / TBD** (not observed); deleted contests are excluded from last/next.

---

# 20. Caching

The integration should cache upstream results appropriately.

Goals:

- minimize MaxPreps traffic
    
- avoid duplicate requests
    
- survive temporary upstream failures
    
- avoid unnecessarily re-fetching unchanged schedules
    

Home Assistant's DataUpdateCoordinator should own refresh coordination at the integration level.

Low-level HTTP caching may also be appropriate.

---

# 21. Testing Strategy

Development should use three layers.

## Layer 1: MaxPreps Client Unit Tests

Test the data connector independently from Home Assistant.

Use captured fixtures where practical.

Examples:

```
football
basketball
baseball
softball
soccer
volleyball
non-head-to-head sport
missing result
postponed game
cancelled game
```

Fixtures should allow development and CI to run without repeatedly contacting MaxPreps.

## Layer 2: Home Assistant Integration Tests

Test:

- config flow
    
- school search
    
- team selection
    
- entity creation
    
- coordinator refresh
    
- unavailable upstream
    
- compact state `scheduled` / `final` / `unknown` (not PRE → POST; Q1 still open)
    
- last_game / next_game attributes
    
- per-program vs entry-wide failure
    
- reload
    
- options changes
    
- removal
    

## Layer 3: Manual HA Sandbox

Run a disposable Home Assistant Core development instance (see [HA_DEVELOPMENT.md](HA_DEVELOPMENT.md)).

**Current / Decided:** Owner Layer 3 verification on 2026-09-09 closed the Phase 3 completion gate (live config flow, add/remove sport, two schools, reload isolation, duplicate-school rejection, automatic `entity_picture`).

Test:

- initial installation
    
- configuration UI
    
- school lookup
    
- team discovery
    
- dashboards
    
- entity naming
    
- automation behavior
    
- upgrades
    

Production Home Assistant should not be the primary development environment.

---

# 22. Repository Structure

**Current / Decided:** Public repo `willbur83/hacs-highschoolscores`. Package root is `custom_components/maxpreps/` (client, `parsing/`, coordinator, config/options flow, sensors). Tests live under `tests/` with MaxPreps fixtures. There is **no** `hacs.json` yet (Phase 5). There is no top-level `api.py` — parsers live under `parsing/`.

The original sketch (including `hacs.json` and `api.py`) is retained only as historical intent:

```
hacs-highschoolscores/
├── custom_components/
│   └── maxpreps/
│       ├── parsing/
│       ├── client.py
│       ├── config_flow.py
│       ├── coordinator.py
│       ├── sensor.py
│       └── ...
├── tests/
│   └── fixtures/
├── docs/
├── README.md
└── pyproject.toml
```

The MaxPreps parsing/client layer should remain as independent from Home Assistant as practical so it can later be extracted into a standalone Python library if useful.

Do not create a separate Python package/repository initially unless implementation evidence shows a strong reason.

---

# 23. Development Environment

**Current / Decided:** Develop against a disposable Home Assistant **Core container** with this repository’s `custom_components/maxpreps` bind-mounted. Pins, test layers, and the sandbox workflow are in [HA_DEVELOPMENT.md](HA_DEVELOPMENT.md). Keep HA config and secrets **outside** this git repository. Operator compose files and machine-specific paths belong in unpublished operator notes.

Do not use another full HAOS VM as the primary development environment. Do not commit host names, local filesystem paths, or compose contents here.

---

# 24. V1 Success Criteria

The first **public** release (HACS-installable) is successful if the list below is true. Phase 3 already satisfies the integration-behavior items for allowlisted sports; HACS distribution (item 1 / 15) remains **Future / Desired** (Phase 5).

1. A user can install MaxPreps for Home Assistant through HACS/custom repository. (**Future / Desired** — Phase 5. Today: manual/custom-component copy or bind-mount.)
    
2. A user can configure it entirely through the Home Assistant UI. (**Current / Decided.**)
    
3. A user can search for and select their school. (**Current / Decided** — short name + picker.)
    
4. The integration automatically discovers available teams/sports. (**Current / Decided** — allowlisted programs for the applicable school year.)
    
5. A user can select one or more teams. (**Current / Decided** — programs `{sport, gender, level}`.)
    
6. Compatible sports work without sport-specific configuration. (**Current / Decided** for the allowlist.)
    
7. The integration retrieves season schedules. (**Current / Decided** — coordinator `programs[].terms[]`.)
    
8. Completed games show final scores/results. (**Current / Decided** — `last_game` / schedule games with `final`.)
    
9. Upcoming games show scheduled date/time/opponent. (**Current / Decided** — `next_game`; naive datetime.)
    
10. Data is usable in a Team Tracker-style dashboard experience. (**Current / Decided** as a data contract; polished custom card is **Future / Desired**.)
    
11. Full season schedule data is available for dashboard display. (**Current / Decided** on the coordinator; frontend expanded view is **Future / Desired**.)
    
12. Home Assistant automations can trigger around scheduled games and newly discovered final scores. (**Current / Decided** at coordinator-refresh granularity; timezone-correct “minutes before kickoff” is **not** guaranteed.)
    
13. MaxPreps is queried conservatively. (**Current / Decided** — 12h / daily rollover wait.)
    
14. Temporary MaxPreps failures do not destroy last-known schedule data. (**Current / Decided.**)
    
15. Another Home Assistant user with HAOS and HACS can install and use the integration without any separate server, Docker host, API service, or YAML configuration. (**Future / Desired** for HACS; YAML-free UI config is **Current / Decided.**)
    

---

# 25. Non-Goals for Initial Release

Unless exploration proves they are trivial, initial release does not require:

- real-time score tracking
    
- play-by-play
    
- player statistics
    
- roster management
    
- custom Lovelace frontend
    
- Home Assistant Core inclusion
    
- MaxPreps account authentication
    
- cloud service operated by this project
    
- webhook infrastructure
    
- separate server/container outside Home Assistant
    
- guaranteed immediate final-score detection
    

---

# 26. Product Principles

## Sport-Agnostic First

Do not hardcode sport-specific behavior until the source data requires it. The current evidence-based allowlist is a validation gate for the shared parser, not a permanent sport ceiling.

## School-First UX

Users should think:

> "Add my school."

Not:

> "Find a MaxPreps URL."

## Native Home Assistant Experience

After installation, configuration and use should feel like a normal Home Assistant integration.

## Conservative External Requests

Do not treat an undocumented/public web data source like a real-time sports API.

## Useful Without a Custom Card

Entities should remain useful for automations and normal Home Assistant dashboards independently of any future frontend card.

## Data Quality Over Feature Breadth

Schedules and final scores should be dependable before adding standings, statistics, rankings, or other features.

---

# 27. Open Product Decisions / Ambiguities

Items marked **Decided** are current product truth. Items still open must not be silently resolved in implementation.

## A. Config Entry Scope

**Decided (Phase 3).** One config entry represents a school and contains multiple selected programs. Duplicate `school_id` is rejected. Multiple schools are independent entries.

---

## B. Schedule Representation

**Decided (Phase 3) for the data contract:**

- Full school-year schedule lives on coordinator `programs[].terms[]` (`runtime_data`).
- Program sensors expose compact state plus concise `last_game` / `next_game` attributes.
- Not one entity per contest. Full schedule is **not** dumped into entity state.

**Future / Desired / still open for presentation:**

- more-info vs dedicated dashboard vs custom card (project Phase 4)
- Calendar entities (blocked by timezone-naive provider datetimes — do not ship calendar as if kickoff instants were correct)
- event entities for reschedule/cancel

---

## C. Primary Team Entity State

**Open / TBD (Q1).** Do **not** implement `PRE` / `IN` / `POST` / `OFF` until the owner disposes Q1.

**Current / Decided (interim):** compact state `scheduled | final | unknown` from last/next, with both last and next as attributes. This is the Phase 3 planning recommendation (provider status of next else last final), not a closed Q1 decision.

Possible future models (not shipped):

```
PRE
IN
POST
OFF
```

or an intrinsically useful state such as next-game datetime, final score, or record.

Need owner disposition for dashboard vs automation vs Team Tracker-style naming.

---

## D. POST Retention Window

**Open / TBD** as a Q1/card concern. Not applicable to current compact state: `last_game` and `next_game` are both exposed when derivable; compact state prefers `scheduled` whenever a next game exists. There is no implemented POST-display timer.

---

## E. Adaptive Polling Window

**Future / Desired.** Not implemented. Production remains 12h (daily during unpublished new-year wait).

Need empirical MaxPreps data (optional Spike H observation) to determine:

- whether MaxPreps reports game duration/status
    
- how quickly final scores normally appear
    
- whether start times are reliable
    
- whether polling should accelerate before, during, or only after expected completion
    
- how long accelerated polling should continue
    

Do not optimize this until the data source behavior is understood. Do not treat adaptive polling as current.

---

## F. Notification Specificity

The integration should provide data suitable for notifications.

**Current / Decided (v1 assumption, still standing):** ordinary HA state and attribute changes are sufficient.

**Open / TBD:** dedicated events for `game starting` / `game final` / `schedule changed` remain optional future work.

---

## G. Schedule Changes

**Open / TBD.** Provider `deleted` contests are excluded from last/next; postponed/cancelled were **not observed**. The coordinator updates schedule data in place. Explicit rescheduled/cancelled/opponent-changed events are not shipped.

Potentially valuable but not core.

---

## H. Multiple Seasons

**Decided (2026-09-02).** Landed in Phase 3.

- **Applicable school year:** July 1 through June 30 in the Home Assistant instance’s local timezone. `2026-07-01`–`2027-06-30` is `26-27`.
- Subscriptions automatically follow that school year. No annual reconfiguration. No historical year picker in v1.
- Provider rows and published schedules for that year are separate from the calendar rule. Do not invent a schedule merely because the calendar rolled over. Until the new year is published, keep prior data and check conservatively (daily), then return to the 12h refresh.
- MaxPreps Spring/Fall (or Winter) terms inside one school year are **not** separate user seasons; see §3.2 program subscriptions.

Prior-season browsing and manual season selection remain out of scope.

---

## I. School Identity

**Decided.** Persist MaxPreps `school_id` (UUID) plus payload `canonical_url`. Display name and URL slug are not identity.

---

## J. Team Identity

**Decided (2026-09-02) for user-facing subscriptions:**

```
school + sport + gender + level
```

School identity remains MaxPreps `schoolId`. Do not persist MaxPreps `sportSeasonId`, `allSeasonId`, term, year, or team-season URL as the subscription key. Those remain provider-side metadata used to fetch and match rows for the applicable school year (one or more `TeamSeason` rows per subscription). Provider row identity remains `(school_id, sport_season_id)` plus `canonical_url`.

---

## K. HACS Scope

**Future / Desired.** Build toward HACS quality, but do not treat HACS listing or Core inclusion as Phase 3 work. `hacs.json` is Phase 5.

---

# 28. Significant Assumptions

Status after Phase 1–3. “Validated” means research + landed client/integration behavior; it does not reopen the item as an implementation task.

1. MaxPreps exposes public schedule/result data that can be retrieved without authentication. **Validated.**
    
2. School search can be implemented reliably enough that users do not need to paste URLs. **Validated** as short name + picker (not a qualified “School, City ST” string).
    
3. MaxPreps exposes a stable-enough identifier for schools and teams. **Validated** as `school_id` and `(school_id, sport_season_id)` plus payload `canonical_url`. User subscriptions use `{sport, gender, level}`.
    
4. Most sports use a sufficiently similar contest model that one normalized schedule parser can support them. **Partial** — true for the allowlist; tennis/track/meets deferred.
    
5. Final scores are generally available within a useful timeframe after games. **Plausible, unmeasured.** Decode is reliable; posting latency is not benchmarked. 12h polling is the current detection bound.
    
6. MaxPreps request volume can remain extremely low. **Validated** as the 12h / daily-rollover-wait design.
    
7. Home Assistant can dynamically vary coordinator polling frequency around expected game completion without introducing unnecessary complexity. **Future / Desired — not implemented.** Do not treat as current.
    
8. Full schedule data is small enough to expose conveniently within Home Assistant. **Validated** on the coordinator contract (not entity state).
    
9. Logos/images can either be referenced directly or cached/represented without violating HA frontend expectations. **Current / Decided** for automatic `entity_picture` plus HTTPS/`/local/` override. Owner sandbox confirmed automatic logo rendering. MediaSelector upload remains deferred.
    
10. Existing Home Assistant cards can provide an acceptable first dashboard experience. **Unchanged / Future** — custom card is optional (Phase 4).
    
11. A custom frontend card is optional rather than necessary for initial adoption. **Unchanged.**
    
12. MaxPreps's public data mechanism may change and therefore parsing logic must be isolated from HA behavior. **Validated** — parsers stay in `parsing/`; HA consumes normalized models.

---

# 29. Initial Exploration Phase

**Historical — complete.** Phase 1 research is recorded in [MAXPREPS_RESEARCH.md](MAXPREPS_RESEARCH.md). Do not treat this section as unfinished work.

Investigation covered football, basketball, baseball, volleyball, tennis, track, plus cross-school validation (Centennial, Bainbridge, Pike County, St. Edward) and a timezone probe (Pensacola). Softball/soccer schedule decode was not promoted into the allowlist.

The output was the research document plus fixtures under `tests/fixtures/maxpreps/`. Supported-format limitations were then defined as the evidence-based allowlist in §8.

---

# 30. First Engineering Milestone

**Historical — complete (Phase 2).** The MaxPreps client, fixture tests, and `scripts/demo_client.py --fixtures` exist. The Home Assistant wrapper is Phase 3 and is also complete.

Correct search example (do **not** use a qualified city/state string as the query):

```
Given a school search:
"Centennial"

↓ pick Centennial High School, Roswell, GA from results

↓ enumerate allowlisted programs for the applicable school year

↓ select a program {sport, gender, level}

↓ fetch matching TeamSeason schedule(s)

↓ normalize games (timezone-naive dates)

↓ print structured result

↓ automated tests pass
```

Example normalized game date is naive, not offset-correct:

```
{
  "school": {
    "name": "Centennial High School",
    "location": "Roswell, GA"
  },
  "team": {
    "name": "Boys Varsity Football",
    "sport": "Football",
    "gender": "Boys",
    "level": "Varsity"
  },
  "games": [
    {
      "date": "2026-08-20T19:30:00",
      "opponent": "Dunwoody",
      "status": "final",
      "team_score": 23,
      "opponent_score": 21,
      "result": "W"
    }
  ]
}
```

The `"date"` value above is illustrative of **naive** ISO form. Do not copy an offset such as `-04:00` as if kickoff TZ were solved.

---

# 31. Working Definition of Done

The project is not "done" because MaxPreps data can be scraped.

The first **public** release is done when a normal Home Assistant user can:

> Install it, find their school, select their teams, see schedules and scores, put that information on a dashboard, and build useful game-related automations without needing to understand MaxPreps internals.

**Current / Decided:** That loop works as a custom component (UI config, allowlisted programs, coordinator schedules, last/next, conservative polling). **Future / Desired:** HACS install path (Phase 5) and a polished last/next card (Phase 4).