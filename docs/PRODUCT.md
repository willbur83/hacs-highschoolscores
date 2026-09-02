## Product Requirements & Technical Direction

### Draft v0.1

## 1. Product Summary

Build a public, open-source Home Assistant custom integration that connects Home Assistant to public MaxPreps school sports data.

The integration should make it easy for a Home Assistant user to select their school and one or more teams/sports, then expose schedule and score/result data as Home Assistant entities suitable for dashboards, automations, and notifications.

The primary product goal is:

> Make school sports schedules and final scores feel like native Home Assistant data.

The integration should be as sport-agnostic as the MaxPreps data allows. Sport-specific behavior should only be introduced where actual MaxPreps data differences require it.

Initial development should focus on understanding and normalizing MaxPreps data rather than prematurely defining a supported-sports list.

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

The integration itself does not necessarily need to ship a custom Lovelace card in the first release. It must expose data in a way that supports a polished dashboard card using native or existing Home Assistant frontend components.

A custom dashboard card may be considered later if necessary.

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
    

The exact frontend implementation is TBD.

The integration should provide sufficient structured schedule data to support any of these approaches.

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

The data model should not assume the "current game card" is the only presentation.

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

A custom event such as:

```
maxpreps_game_final
```

may eventually be useful, but is not required for the initial version if normal entity state transitions provide the same functionality.

---

# 3. Installation and Configuration

## 3.1 Distribution

Initial distribution:

```
GitHub public repository
    ↓
HACS custom repository
    ↓
HACS default repository/listing if accepted
```

Long-term Home Assistant Core inclusion is not an initial goal.

The integration should behave like a normal Home Assistant integration after installation.

No YAML should be required for normal configuration.

---

## 3.2 Configuration Flow

Configuration should be school-first.

Desired user experience:

```
Settings
→ Devices & Services
→ Add Integration
→ MaxPreps
```

Then:

### Step 1: Find School

User searches using information such as:

```
Centennial
```

Potential additional inputs if needed:

- City
    
- State
    
- ZIP code
    

Results should clearly disambiguate schools.

The Home Assistant school picker should show each result approximately as **`School Name | City, State`**, with an optional mascot when present (for example `Centennial | Roswell, GA · Knights`). When MaxPreps omits city or state, the picker degrades gracefully (state-only, city-only, or “Location unavailable”) rather than dropping the school or failing the search.

Example:

```
Centennial High School
Roswell, Georgia
```

### Step 2: Discover Teams

After selecting the school, the integration should retrieve the teams/sports MaxPreps exposes for that school.

Example:

```
Varsity Football
JV Football
Boys Varsity Basketball
Girls Varsity Basketball
Varsity Baseball
Varsity Softball
Boys Varsity Soccer
Girls Varsity Soccer
...
```

### Step 3: Select Teams

User may select one or more teams.

The integration should not require separate setup flows for each selected team unless Home Assistant architecture strongly favors that implementation.

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

Preferred conceptual model:

```
Device:
Centennial High School
```

The device represents the physical school/program.

Selected sports/teams become entities associated with that device.

Example:

```
Centennial High School

sensor.centennial_varsity_football
sensor.centennial_varsity_baseball
sensor.centennial_varsity_softball
```

This is preferred over creating a separate Home Assistant device for every team.

This decision should be validated against Home Assistant entity/device best practices during implementation.

---

# 5. Team Entity

Each selected team should expose a primary entity representing the most contextually relevant game.

Example:

```
sensor.centennial_varsity_football
```

## 5.1 Relevant Game Selection

The integration should determine a "relevant game" based on time and game status.

Possible states:

```
PRE
IN
POST
OFF
UNKNOWN
```

Exact state terminology is TBD.

Desired behavior conceptually mirrors Team Tracker:

### PRE

Upcoming scheduled game.

### IN

Game appears to be actively in progress.

This state is dependent on whether MaxPreps provides sufficiently reliable live/in-progress information.

Live tracking is not a core v1 requirement.

### POST

Most recently completed game.

The integration should remain in POST long enough for dashboards and automations to react.

### OFF

No relevant scheduled/current/recent game.

This may occur:

- out of season
    
- schedule unavailable
    
- no upcoming game known
    

---

# 6. Team Entity Attributes

The primary team/game entity should expose normalized attributes where available.

Proposed core attributes:

```
school_name:
school_id:

team_name:
team_id:
sport:
level:
gender:

team_logo:
team_record:

opponent_name:
opponent_id:
opponent_logo:

game_id:
game_url:

date:
status:

home_away:
venue:
location:

team_score:
opponent_score:
result:
```

Potential additional attributes:

```
season:
conference:
region:
rank:
record:
last_updated:
source_url:
```

Attributes should only be populated when supported by MaxPreps data.

Missing data should not cause the entity to fail.

---

# 7. Schedule Data

The integration must expose full season schedule/result data.

A normalized game object should look conceptually like:

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

The integration should not maintain a hardcoded list such as:

```
football
baseball
softball
basketball
```

unless MaxPreps itself requires such identifiers.

Instead:

1. Discover available teams from the selected school.
    
2. Treat sport, gender, level, and team name as metadata.
    
3. Pass all compatible teams through the same schedule/result normalization pipeline.
    
4. Identify actual exceptions empirically.
    

The default assumption is:

> If MaxPreps represents a team's season as dated contests with an opponent and result, the integration should support it automatically.

Potential exceptions requiring investigation:

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
    

These sports should not be excluded in advance.

Exploration should determine whether MaxPreps exposes a usable team-level schedule/result representation.

If they do, they should work through the same generic integration.

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

The client should eventually support:

## School Search

```
search_schools(query, state=None)
```

Returns normalized school results.

## School Team Discovery

```
get_school_teams(school_id)
```

Returns teams/sports available for the selected school.

## Team Schedule

```
get_schedule(team_id, season=None)
```

Returns normalized games.

## Team Metadata

Potentially:

```
get_team(team_id)
```

Provides:

- name
    
- sport
    
- level
    
- gender
    
- logo
    
- record
    
- season
    
- school
    

Exact methods may change based on how MaxPreps data is actually exposed.

---

# 11. Polling Strategy

The integration should intentionally avoid frequent MaxPreps requests.

Normal operation should require only a small number of requests per day.

Initial default target:

```
approximately 2-4 refreshes per day per configured school/team set
```

The exact implementation should attempt to minimize duplicate requests where multiple selected teams can share upstream calls.

---

# 12. Adaptive Game-Day Polling

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

---

# 13. Final Score Detection

Final score detection is a key automation use case.

The integration should distinguish:

```
scheduled
in progress, if supported
final
postponed
cancelled
unknown
```

When a game transitions to final, the entity should update in a way that Home Assistant automations can reliably detect.

Example:

```
PRE → POST
```

with:

```
team_score: 54
opponent_score: 18
result: W
```

Automations should be able to trigger from that change without special polling logic written by the user.

---

# 14. Game Start Notifications

Game start notifications should be primarily schedule-driven.

If MaxPreps provides:

```
Friday 7:30 PM
```

Home Assistant already has enough information to trigger:

```
30 minutes before game
at game time
```

This does not require MaxPreps to report that the game has actually started.

The integration must clearly distinguish:

```
scheduled start time
```

from:

```
confirmed live/in-progress state
```

if both eventually exist.

---

# 15. Live Score Support

Live scoring is explicitly not a core requirement.

If MaxPreps exposes usable live state/score data through the same connector, the integration may expose it.

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

Team Tracker-like display.

## Pattern B: Full Schedule

Season schedule/results.

## Pattern C: Both

Primary card that leads to or accompanies full schedule.

The integration should expose enough structured data to support all three without requiring users to create REST sensors or templates themselves.

---

# 18. Custom Lovelace Card

A custom frontend card is not required for initial implementation.

Preferred sequencing:

### Phase 1

Expose excellent Home Assistant entities and attributes.

### Phase 2

Determine whether native cards, Mushroom, Auto Entities, or other existing frontend tools can create the desired experience.

### Phase 3

Only create a custom MaxPreps Lovelace card if it meaningfully improves usability.

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

The integration should retain last successful data where appropriate while marking freshness/availability accurately.

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
    
- PRE → POST transition
    
- reload
    
- options changes
    
- removal
    

## Layer 3: Manual HA Sandbox

Run a disposable Home Assistant development instance.

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

Proposed repository:

```
ha-maxpreps/
├── custom_components/
│   └── maxpreps/
│       ├── __init__.py
│       ├── api.py
│       ├── config_flow.py
│       ├── const.py
│       ├── coordinator.py
│       ├── manifest.json
│       ├── models.py
│       ├── sensor.py
│       └── translations/
│
├── tests/
│   └── fixtures/
│
├── .github/
├── .devcontainer/
├── hacs.json
├── LICENSE
├── README.md
└── pyproject.toml
```

The MaxPreps parsing/client layer should remain as independent from Home Assistant as practical so it can later be extracted into a standalone Python library if useful.

Do not create a separate Python package/repository initially unless implementation evidence shows a strong reason.

---

# 23. Development Environment

Primary development environment:

```
Mustang
  Cursor
    ↓ Remote SSH
Lightning
  repository
  tests
  devcontainer
  Home Assistant development instance
```

The repository should live on Lightning.

A disposable Home Assistant Core development environment should be used rather than another full HAOS VM.

---

# 24. V1 Success Criteria

The first public release is successful if:

1. A user can install MaxPreps for Home Assistant through HACS/custom repository.
    
2. A user can configure it entirely through the Home Assistant UI.
    
3. A user can search for and select their school.
    
4. The integration automatically discovers available teams/sports.
    
5. A user can select one or more teams.
    
6. Compatible sports work without sport-specific configuration.
    
7. The integration retrieves season schedules.
    
8. Completed games show final scores/results.
    
9. Upcoming games show scheduled date/time/opponent.
    
10. Data is usable in a Team Tracker-style dashboard experience.
    
11. Full season schedule data is available for dashboard display.
    
12. Home Assistant automations can trigger around scheduled games and newly discovered final scores.
    
13. MaxPreps is queried conservatively.
    
14. Temporary MaxPreps failures do not destroy last-known schedule data.
    
15. Another Home Assistant user with HAOS and HACS can install and use the integration without any separate server, Docker host, API service, or YAML configuration.
    

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

Do not hardcode differences until the source data requires them.

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

The following decisions should be resolved through initial data exploration and product review rather than assumed during implementation.

## A. Config Entry Scope

**Question:** Is one config entry a school, or one team?

Preferred assumption:

> One config entry represents a school and contains multiple selected teams.

This seems like the better user experience but must be validated against HA entity/device architecture and update behavior.

---

## B. Schedule Representation

**Question:** Should the full schedule exist:

- as attributes on the primary team entity
    
- as a separate schedule entity
    
- through calendar entities
    
- through event entities
    
- through another Home Assistant-native mechanism
    

No decision should be made until current HA entity capabilities and dashboard behavior are evaluated.

A Calendar entity may be especially worth investigating because sports schedules are inherently calendar data.

---

## C. Primary Team Entity State

Possible model:

```
PRE
IN
POST
OFF
```

Alternative:

The entity state could be something intrinsically useful such as:

```
Next game date
Final score
Record
```

and game lifecycle could exist as attributes.

Need to determine which model produces the best combination of:

- dashboard usability
    
- automation usability
    
- HA conventions
    
- Team Tracker compatibility/style
    

---

## D. POST Retention Window

If Friday's game becomes final Friday night, how long should the primary card continue displaying that completed game before switching to next Friday?

Possible options:

- 12 hours
    
- 24 hours
    
- until next morning
    
- configurable
    
- Team Tracker-like behavior
    

Initial assumption:

> Approximately 24 hours.

Not yet decided.

---

## E. Adaptive Polling Window

Need empirical MaxPreps data to determine:

- whether MaxPreps reports game duration/status
    
- how quickly final scores normally appear
    
- whether start times are reliable
    
- whether polling should accelerate before, during, or only after expected completion
    
- how long accelerated polling should continue
    

Do not optimize this until the data source behavior is understood.

---

## F. Notification Specificity

The integration should provide data suitable for notifications.

Open question:

Should it itself create device/event entities specifically for:

```
game starting
game final
schedule changed
```

or should consumers use ordinary state triggers?

Initial assumption:

> Ordinary HA state changes are sufficient for v1.

---

## G. Schedule Changes

Need to determine whether the integration should explicitly expose:

```
game rescheduled
game cancelled
opponent changed
```

as events, or simply update the schedule attributes.

Potentially valuable but not core.

---

## H. Multiple Seasons

**Decided (2026-09-02).**

- **Applicable school year:** July 1 through June 30 in the Home Assistant instance’s local timezone. `2026-07-01`–`2027-06-30` is `26-27`.
- Subscriptions automatically follow that school year. No annual reconfiguration. No historical year picker in v1.
- Provider rows and published schedules for that year are separate from the calendar rule. Do not invent a schedule merely because the calendar rolled over. Until the new year is published, keep prior data and check conservatively (daily is acceptable), then return to the normal low-frequency refresh.
- MaxPreps Spring/Fall (or Winter) terms inside one school year are **not** separate user seasons; see §3.2 program subscriptions.

Prior-season browsing and manual season selection remain out of scope.

---

## I. School Identity

Need to determine the most stable MaxPreps identifier for a school.

Do not use display name or URL slug as the sole identity if MaxPreps exposes a stable internal ID.

---

## J. Team Identity

**Decided (2026-09-02) for user-facing subscriptions:**

```
school + sport + gender + level
```

School identity remains MaxPreps `schoolId`. Do not persist MaxPreps `sportSeasonId`, `allSeasonId`, term, year, or team-season URL as the subscription key. Those remain provider-side metadata used to fetch and match rows for the applicable school year (one or more `TeamSeason` rows per subscription).

---

## K. HACS Scope

Initial assumption:

> Build to HACS quality from the beginning.

But do not optimize prematurely for Home Assistant Core acceptance.

---

# 28. Significant Assumptions

The current product direction assumes the following. These must be validated.

1. MaxPreps exposes public schedule/result data that can be retrieved without authentication.
    
2. School search can be implemented reliably enough that users do not need to paste URLs.
    
3. MaxPreps exposes a stable-enough identifier for schools and teams.
    
4. Most sports use a sufficiently similar contest model that one normalized schedule parser can support them.
    
5. Final scores are generally available within a useful timeframe after games.
    
6. MaxPreps request volume can remain extremely low.
    
7. Home Assistant can dynamically vary coordinator polling frequency around expected game completion without introducing unnecessary complexity.
    
8. Full schedule data is small enough to expose conveniently within Home Assistant.
    
9. Logos/images can either be referenced directly or cached/represented without violating HA frontend expectations.
    
10. Existing Home Assistant cards can provide an acceptable first dashboard experience.
    
11. A custom frontend card is optional rather than necessary for initial adoption.
    
12. MaxPreps's public data mechanism may change and therefore parsing logic must be isolated from HA behavior.
    

---

# 29. Initial Exploration Phase

Before building the full Home Assistant integration, perform a dedicated MaxPreps connector exploration.

Use several real schools/teams and sports.

At minimum investigate:

- football
    
- basketball
    
- baseball
    
- softball
    
- soccer
    
- volleyball
    
- one individual/multi-participant sport such as tennis or golf
    
- one meet-based sport such as track or swimming if available
    

For each, determine:

1. How schools are discovered.
    
2. How teams are enumerated.
    
3. Stable identifiers.
    
4. Schedule payload structure.
    
5. Final result representation.
    
6. Status values.
    
7. Score orientation.
    
8. Home/away representation.
    
9. Tournament/multi-team handling.
    
10. Cancelled/postponed behavior.
    
11. Season identifiers.
    
12. Logo availability.
    
13. Record/standing availability.
    
14. Request/caching requirements.
    
15. Whether the same parser can normalize the data.
    

The output of this phase should be a short technical findings document and fixture set.

Only after this exploration should supported-sport limitations be defined.

---

# 30. First Engineering Milestone

Do not begin by building Home Assistant entities.

The first executable milestone is:

```
Given a school search:
"Centennial High School, Roswell GA"

↓ find school

↓ enumerate available teams

↓ select a team

↓ fetch current schedule

↓ normalize games

↓ print structured result

↓ automated tests pass
```

Example normalized output:

```
{
  "school": {
    "name": "Centennial High School",
    "location": "Roswell, GA"
  },
  "team": {
    "name": "Centennial Knights",
    "sport": "Football",
    "level": "Varsity"
  },
  "games": [
    {
      "date": "2026-08-20T16:30:00-04:00",
      "opponent": "Dunwoody",
      "status": "final",
      "team_score": 23,
      "opponent_score": 21,
      "result": "W"
    }
  ]
}
```

Once that layer is stable and tested across materially different sports, begin the Home Assistant wrapper.

---

# 31. Working Definition of Done

The project is not "done" because MaxPreps data can be scraped.

The first release is done when a normal Home Assistant user can:

> Install it, find their school, select their teams, see schedules and scores, put that information on a dashboard, and build useful game-related automations without needing to understand MaxPreps internals.