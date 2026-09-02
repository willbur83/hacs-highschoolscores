# MaxPreps Research

This document tracks feasibility research for retrieving public MaxPreps school sports data to inform [PRODUCT.md](PRODUCT.md). Home Assistant integration code (custom components, config flows, coordinators, entities, HACS metadata) is **out of scope** until this research phase is complete and the interim feasibility gate is passed.

## Test schools

| Role | School | Location |
|------|--------|----------|
| Primary | Centennial High School | Roswell, Georgia |
| Validation | Bainbridge High School | Bainbridge, Georgia |
| Validation | Pike County High School | Zebulon, Georgia |
| Late sanity check only | Saint Edward High School (St. Edward) | Lakewood, Ohio |

## Traffic policy

- **Budget:** Target fewer than ~40 live requests for the entire exploration. This is a budget, not a quota — prefer correctness and cache reuse over minimizing requests at the cost of bad data.
- **Rate limit:** Wait ≥2 seconds between live requests. No parallel fetching.
- **Stop conditions:** Stop immediately on HTTP 429, 403, challenge pages, or other blocking signals. Do not retry aggressively or attempt bypasses.
- **No refetch:** Never refetch a URL already recorded in the Request Log unless the prior response is documented as unusable (corrupt cache, wrong page, truncated body, etc.).

## Checkpoint / skip policy

Slices are investigation **checkpoints**, not mandatory units of work. A later agent may:

- Combine multiple slices in one session when efficient.
- **Skip live requests** when cached data in `captures/private/` or committed fixtures in `tests/fixtures/maxpreps/` already answers the question — but must still write the corresponding section with findings and references to the cache/fixture used.

Every slice section must eventually contain written findings, even if no new live traffic was needed.

## Sanitization checklist (committed fixtures)

Fixtures that may be committed to the repository must contain **only public MaxPreps page data**. Before committing:

- [ ] Remove cookies, `Authorization` headers, tokens, and `Set-Cookie` response headers.
- [ ] Strip local file paths, IP addresses, and machine/host names from bodies and metadata.
- [ ] Remove personal information unrelated to public team/school/game data.
- [ ] Do not capture rosters, player stats, or athlete pages unless a later slice explicitly requires them.
- [ ] Keep: HTTP status, `Content-Type`, and the public response body (HTML or JSON as observed).
- [ ] Verify the fixture answers a specific research question documented in the slice section.

Private raw captures live in `captures/private/` (gitignored) and may retain more detail for local debugging, but committed fixtures must pass the checklist above.

## Fixture naming

```
tests/fixtures/maxpreps/<school>/<page>-<season>.json
tests/fixtures/maxpreps/<school>/<page>-<season>.html
```

Use a short, filesystem-safe school slug (e.g. `centennial`, `bainbridge`, `pike-county`, `st-edward`).

## Cache location

- **Private cache:** `captures/private/` — gitignored; never commit.
- **Committed fixtures:** `tests/fixtures/maxpreps/` — sanitized public data only.

## Request Log

| timestamp (UTC) | slice | method | URL | status | bytes | cache hit/miss | notes |
|-----------------|-------|--------|-----|--------|-------|----------------|-------|
| 2026-09-01T17:50:00Z | 01 | GET | https://www.maxpreps.com/ | 200 | 238607 | miss | homepage HTML; `text/html`; no cookies; cache `captures/private/www.maxpreps.com/fd17e40e5105fefd.*` |
| 2026-09-01T17:50:08Z | 01 | GET | https://www.maxpreps.com/ga/roswell/centennial-knights/football/ | 200 | 399706 | miss | team home HTML; `text/html`; no cookies; cache `captures/private/www.maxpreps.com/2d2db64f2397299e.*` |
| 2026-09-01T17:50:15Z | 01 | GET | https://www.maxpreps.com/ga/roswell/centennial-knights/football/schedule/ | 200 | 302833 | miss | schedule HTML; `text/html`; no cookies; cache `captures/private/www.maxpreps.com/a9fd9f8193667e1d.*` |
| 2026-09-01T18:08:02Z | 02 | GET | https://www.maxpreps.com/search/?q=centennial&q2=Centennial | 200 | 201597 | miss | school search HTML; `initialSchoolResults` in `__NEXT_DATA__`; cache `captures/private/www.maxpreps.com/fa53b72527c52da4.*` |
| 2026-09-01T18:08:10Z | 02 | GET | https://www.maxpreps.com/search/?q=centennial%20roswell&q2=Centennial%20Roswell | 200 | 126817 | miss | disambiguation test; 0 school results; cache `captures/private/www.maxpreps.com/7067e8ce16a34c25.*` |
| 2026-09-01T18:08:18Z | 02 | GET | https://www.maxpreps.com/search/?q=centennial%20high%20school&q2=Centennial%20High%20School | 200 | 126845 | miss | qualifier test; 0 school results; cache `captures/private/www.maxpreps.com/7b8861cab6a5ca6e.*` |
| 2026-09-01T18:48:15Z | 03 | GET | https://www.maxpreps.com/ga/roswell/centennial-knights/ | 200 | 428174 | miss | school home HTML; `schoolContext.schoolId`; `pagetype=school_home`; no cookies; cache `captures/private/www.maxpreps.com/ad4dcfdcad97c61a.*` |
| 2026-09-01T21:01:45Z | 14 | GET | https://www.maxpreps.com/ga/roswell/centennial-knights/volleyball/schedule/ | 200 | 407642 | miss | Girls Varsity Volleyball schedule; `contests` (32 rows, arity 41) + `featuredGameData`; cache `captures/private/www.maxpreps.com/c1a5eb088efb16a4.*` |
| 2026-09-01T21:01:48Z | 14 | GET | https://www.maxpreps.com/ga/roswell/centennial-knights/softball/schedule/ | 404 | 6995 | miss | **Wrong path** — `sportSeasons[]` canonical is `…/softball/fall/`; not refetched; cache `captures/private/www.maxpreps.com/746fbcd69d15c1b6.*` |
| 2026-09-01T21:02:11Z | 14 | GET | https://www.maxpreps.com/ga/roswell/centennial-knights/basketball/girls/schedule/ | 200 | 231257 | miss | Girls Varsity Basketball schedule; `contests` (6 rows) + `featuredGameData`; sparse pre-season; cache `captures/private/www.maxpreps.com/a89b0d585a1ebd0c.*` |
| 2026-09-01T21:11:24Z | 08-probe | GET | https://www.maxpreps.com/search/?q=pensacola&q2=Pensacola | 200 | 175502 | miss | Pensacola timezone probe — school search; target `60e92873-…` Pensacola Tigers; cache `captures/private/www.maxpreps.com/61a2b3dbdb9eb797.*` |
| 2026-09-01T21:11:41Z | 08-probe | GET | https://www.maxpreps.com/fl/pensacola/pensacola-tigers/football/schedule/ | 200 | 300787 | miss | Pensacola HS varsity football schedule; TZ cross-check vs Centennial; cache `captures/private/www.maxpreps.com/4acd39e363b6d8ab.*` |
| 2026-09-01T21:31:05Z | 15 | GET | https://www.maxpreps.com/ga/roswell/centennial-knights/tennis/schedule/ | 200 | 139681 | miss | Boys Varsity Tennis schedule; **legacy ASPX** — no `__NEXT_DATA__`, empty schedule; cache `captures/private/www.maxpreps.com/aa6eaaf00a2767ec.*` |
| 2026-09-01T21:31:14Z | 15 | GET | https://www.maxpreps.com/ga/roswell/centennial-knights/track-field/girls/schedule/ | 200 | 139075 | miss | Girls Varsity Track & Field schedule; **legacy ASPX** — no `__NEXT_DATA__`, empty schedule; cache `captures/private/www.maxpreps.com/55e4248e9d63ee2a.*` |
| 2026-09-01T21:43:35Z | 16 | GET | https://www.maxpreps.com/search/?q=bainbridge&q2=Bainbridge | 200 | 294637 | miss | Bainbridge HS school search; target GA Bainbridge; cache `captures/private/www.maxpreps.com/67d0801fc17fa39f.*` |
| 2026-09-01T21:43:43Z | 16 | GET | https://www.maxpreps.com/search/?q=pike%20county&q2=Pike%20County | 200 | 134118 | miss | Pike County HS school search; target GA Zebulon; cache `captures/private/www.maxpreps.com/00fbada789999b45.*` |
| 2026-09-01T21:43:59Z | 16 | GET | https://www.maxpreps.com/ga/bainbridge/bainbridge-bearcats/ | 200 | 324640 | miss | Bainbridge HS school home; `sportSeasons` enumeration; cache `captures/private/www.maxpreps.com/181ca9858af0f153.*` |
| 2026-09-01T21:44:10Z | 16 | GET | https://www.maxpreps.com/ga/zebulon/pike-county-pirates/ | 200 | 318183 | miss | Pike County HS school home; `sportSeasons` enumeration; cache `captures/private/www.maxpreps.com/690de41094ee2669.*` |
| 2026-09-01T21:44:30Z | 16 | GET | https://www.maxpreps.com/ga/bainbridge/bainbridge-bearcats/football/schedule/ | 200 | 271934 | miss | Bainbridge Boys Varsity Football schedule; Next.js `contests` + `featuredGameData`; cache `captures/private/www.maxpreps.com/225e0d52acf7718f.*` |
| 2026-09-01T21:44:39Z | 16 | GET | https://www.maxpreps.com/ga/zebulon/pike-county-pirates/football/schedule/ | 200 | 288290 | miss | Pike County Boys Varsity Football schedule; Next.js `contests` + `featuredGameData`; cache `captures/private/www.maxpreps.com/acceee095433f433.*` |
| 2026-09-01T21:56:53Z | 16b | GET | https://www.maxpreps.com/search/?q=saint%20edward&q2=Saint%20Edward | 200 | 143846 | miss | Saint Edward search — **0 school results** (`initialSchoolResults: null`); cache `captures/private/www.maxpreps.com/cf0bc5d235ed1691.*` |
| 2026-09-01T21:57:08Z | 16b | GET | https://www.maxpreps.com/search/?q=st.%20edward&q2=St.%20Edward | 200 | 158731 | miss | St. Edward search retry — 5 schools; target Lakewood OH Eagles; cache `captures/private/www.maxpreps.com/1ee2c1692cdaae80.*` |
| 2026-09-01T21:57:27Z | 16b | GET | https://www.maxpreps.com/oh/lakewood/st-edward-eagles/ | 200 | 376254 | miss | St. Edward school home; `sportSeasons` enumeration; private all-boys OH; cache `captures/private/www.maxpreps.com/0a523fce58763315.*` |
| 2026-09-01T21:57:42Z | 16b | GET | https://www.maxpreps.com/oh/lakewood/st-edward-eagles/football/schedule/ | 200 | 272087 | miss | St. Edward Boys Varsity Football schedule; Next.js `contests` + `featuredGameData`; cache `captures/private/www.maxpreps.com/ea50c28fc13dd099.*` |
| 2026-09-01T22:28:05Z | 18 | GET | https://www.maxpreps.com/robots.txt | 200 | 5094 | miss | `text/plain`; Slice 18 policy facts; cache `captures/private/www.maxpreps.com/6b4f0efe27101bec.*` |
| 2026-09-01T22:28:07Z | 18 | GET | https://www.maxpreps.com/terms-of-use/ | 200 | 155373 | miss | Terms of Use (footer link from Slice 01 homepage); Next.js `page: /concordia/terms-of-use`; cache `captures/private/www.maxpreps.com/ff46cdd961286d3a.*` |
| 2026-09-02T01:45:00Z | phase2-0 | GET | https://www.maxpreps.com/ga/roswell/centennial-knights/baseball/schedule/ | 200 | 383386 | miss | Centennial Boys Varsity Baseball schedule; Next.js `contests` (30 rows, arity 41, participants width 32) + `featuredGameData`; cache `captures/private/www.maxpreps.com/8f65b1d976c5408b.*` |

---

## Slice 01 — How data is exposed (transport)

**Evidence mode:** Browser DevTools Network tab was **not available** in this session. Findings below come from three plain `GET` captures of the public page URLs (degraded substitute per traffic policy). No separate XHR/fetch URLs were discovered in the HTML; only embedded payloads and static assets were inspected.

### 1. How the data is exposed (plain language)

MaxPreps serves Centennial pages as **server-rendered Next.js HTML documents**. School, team, and schedule information arrives **inside the initial document response**, primarily as a large JSON blob in `<script id="__NEXT_DATA__">` → `props.pageProps`. There is **no evidence in these captures** of a follow-on JSON API, GraphQL gateway, `/_next/data/...` prefetch, or RSC flight payload for these pages.

Secondary public payloads in the same HTML response:

- **`application/ld+json`** (`<script id="ld+json">`) — on the schedule page, nine `SportsEvent` entries with opponents, dates, scores in descriptions, and game URLs.
- **`<meta name="targeting">`** — HTML-escaped JSON with ad/page context including `mpschoolid`, `activity`, `gnd`, `state`, `zip`.
- **Rendered HTML** in `<div id="__next">` — human-visible schedule rows; redundant with `__NEXT_DATA__` for machine use.

The schedule page’s richest structured data is `pageProps.contests` (11 rows, compact columnar encoding) plus `pageProps.featuredGameData` and `pageProps.teamContext` (full team/school metadata, season picker, menu).

### 2. Observed request patterns

| Mechanism | Used? | Notes |
|-----------|-------|-------|
| JSON/API (XHR/fetch) | **Not observed** | No `/_next/data/...`, `production.api.maxpreps.com`, or similar URLs in HTML |
| Next.js `__NEXT_DATA__` / `pageProps` | **Yes — primary** | Present on all three pages; schedule `pageProps` ≈ 106 KB |
| GraphQL | **No** | Not referenced in HTML |
| `production.api.maxpreps.com` or gateway | **No** | Not referenced in HTML |
| RSC / App Router flight | **No** | No `text/x-component` or flight markers |
| Embedded HTML | **Yes — supplementary** | Rendered schedule in DOM; not the richest source |
| JSON-LD (`ld+json`) | **Yes — supplementary** | Schedule page events; fewer fields than `pageProps` |
| `meta targeting` JSON | **Yes — supplementary** | Identifiers for ads/routing |

**HTTP pattern:** single `GET` per public page URL → `200 text/html; charset=utf-8`. Path-stable public URLs:

- `/` (homepage; internal Next route `page: /concordia`)
- `/ga/roswell/centennial-knights/football/` (`page: /team`)
- `/ga/roswell/centennial-knights/football/schedule/` (`page: /team/schedule`)

**Deploy-specific identifiers** (present in every capture, same across the three pages):

- `buildId`: `92628a14-f7050eaf` (also in `asset.maxpreps.io/_next/static/<buildId>/...` stylesheet URLs)
- Static asset hashes under `/_next/static/chunks/...`

**Path-stable / content identifiers** (in `__NEXT_DATA__` and/or `meta targeting`):

| Identifier | Example (Centennial football 26-27) | Where seen |
|------------|-------------------------------------|------------|
| `mpschoolid` / `teamId` | `52dea55b-3988-4979-b5fd-20376058997f` | `meta targeting`, `teamContext.data.teamId`, `query.schoolid` |
| `ssid` / `sportSeasonId` | `2286cd80-c46d-4739-8dd1-92a67ca8daa7` | `meta targeting` (as ssid via rewrite), `tracking.ssid`, `teamContext.data.sportSeasonId`, `query.ssid` |
| `allSeasonId` | `22e2b335-334e-4d4d-9f67-a0f716bb1ccd` | `query`, `teamContext.data.allSeasonId` |
| `contestId` | e.g. `30b79240-4c41-4e25-b850-0052d1221fbd` | `featuredGameData`, game URLs (`?c=` query param) |
| URL slug path | `ga/roswell/centennial-knights/football/` | `canonicalUrl`, links |

Response header `x-middleware-rewrite` on team pages reveals legacy ASPX routing parameters (`schoolid`, `ssid`, `gendersport`, `allSeasonId`) — useful context but **not** a separate endpoint we called.

### 3. Python HTTP reproducibility

| Step | Result |
|------|--------|
| `GET` page URLs with `scripts/explore/capture.py` (stdlib `urllib` fallback; `User-Agent: hacs-highschoolscores-explore/0.1`) | **Pass** — all three returned `200` |
| Cookies sent | **None** |
| Browser-specific headers | **None** beyond User-Agent |
| JavaScript execution required | **No** — `__NEXT_DATA__` is in the initial HTML |
| Challenge / 403 / 429 | **None encountered** |

**Conclusion:** A normal Python HTTP client with **no browser state** can retrieve the same data-bearing payloads by fetching the public HTML URLs and parsing `__NEXT_DATA__` (or JSON-LD). This satisfies the HACS architecture constraint for the pages examined in Slice 01.

**Not tested (and not guessed):** `/_next/data/<buildId>/...` JSON routes — no such URLs appeared in the captured HTML. Client-side calls after hydration were not observable without a browser Network tab.

### 4. Fragility notes

- **`buildId` is deploy-specific** (`92628a14-f7050eaf` at capture time). It appears in `__NEXT_DATA__` and static asset paths. A client keyed only on `buildId` would break on redeploy; **page URL paths appear stable** and already return fresh `__NEXT_DATA__`.
- **`pageProps` shape** is large and page-type-specific (`/team` vs `/team/schedule`). `contests` uses a compact columnar list-of-lists encoding that may change without notice.
- **JSON-LD** is easier to parse but incomplete (9 events vs 11 `contests` rows on the schedule page).
- **Caching headers:** team schedule responses included `cache-control: no-store` and short edge TTL metadata (`x-mp-caching-rules`); treat live fetches as uncached from the client’s perspective.
- **Cookie consent / OneTrust** scripts are referenced (`cdn.cookielaw.org`) but were not required to receive full HTML payloads in these captures.

### 5. Cache and fixture pointers

| Artifact | Path |
|----------|------|
| Homepage raw + sidecar | `captures/private/www.maxpreps.com/fd17e40e5105fefd.{raw,json}` |
| Football team page | `captures/private/www.maxpreps.com/2d2db64f2397299e.{raw,json}` |
| Football schedule page | `captures/private/www.maxpreps.com/a9fd9f8193667e1d.{raw,json}` |
| Committed fixture (richest payload) | `tests/fixtures/maxpreps/centennial/schedule-26-27.json` — sanitized `__NEXT_DATA__.props.pageProps` plus metadata |

---

## Slice 02 — School search / discovery

**Evidence mode:** Headless Chromium (Playwright) was used to observe the search UI and Network tab. Browser observation identified the search-results URL pattern; three search pages were then captured with `scripts/explore/capture.py` and parsed from `__NEXT_DATA__`. The Slice 01 homepage cache was inspected first and did **not** expose `/search`, `name="q"`, or autocomplete API URLs — the search box is a client-hydrated overlay (`SearchButton` component) not present in the static homepage HTML.

### 1. How school search is exposed

MaxPreps school discovery is a **server-rendered HTML search-results page**, not a standalone JSON/XHR search API.

| Layer | Role |
|-------|------|
| Search UI | Header overlay: button `aria-label="Open search"` → `input[name="q"]` (`placeholder="Search teams + athletes"`) |
| Submit | Enter (or equivalent form submit) navigates to the search-results page |
| Results transport | `GET` HTML document with embedded `__NEXT_DATA__` → `props.pageProps.initialSchoolResults` (schools) and `initialCareerResults` (athletes) |
| Autocomplete while typing | **Not observed** — no MaxPreps `fetch`/`xhr` fired while typing in the overlay before submit (Playwright Network tab) |
| Separate search API | **Not observed** for results — `production.api.maxpreps.com` calls on the search page were for homepage/video widgets, not school lookup |

Internal Next route: `page: /discovery/search` (legacy tracking name `/search/default.aspx`).

### 2. Observed request pattern

| Step | Method | URL pattern | Notes |
|------|--------|-------------|-------|
| Open search | — | (client UI only) | No network call |
| Type query | — | (client UI only) | No autocomplete XHR observed |
| Submit search | `GET` | `https://www.maxpreps.com/search/?q=<normalized>&q2=<display>` | `q` is lowercased/normalized; `q2` preserves user casing |
| Redirect | `308` → `200` | Browser observed `GET /search/?q=Centennial` → `GET /search/?q=centennial&q2=Centennial` | Python `capture.py` followed redirect to final URL |

**Examples captured (Slice 02):**

| User query | Final URL | School results |
|------------|-----------|----------------|
| `Centennial` | `/search/?q=centennial&q2=Centennial` | 32 schools (includes target) |
| `Centennial Roswell` | `/search/?q=centennial%20roswell&q2=Centennial%20Roswell` | **0** schools |
| `Centennial High School` | `/search/?q=centennial%20high%20school&q2=Centennial%20High%20School` | **0** schools |

`buildId` at capture time: `92628a14-f7050eaf` (same deploy as Slice 01). Search does **not** require `/_next/data/<buildId>/...` for results — data is in the HTML document's `__NEXT_DATA__`.

### 3. Result shape (`initialSchoolResults`)

Each school object (32 entries for query `Centennial`):

| Field | Example (Centennial, Roswell, GA — target school) |
|-------|---------------------------------------------------|
| `schoolId` | `52dea55b-3988-4979-b5fd-20376058997f` |
| `name` | `Centennial` |
| `city` | `Roswell` |
| `state` | `GA` |
| `zip` | `30076-3417` |
| `mascot` | `Knights` |
| `mascotUrl` | `https://image.maxpreps.io/school-mascot/5/2/d/52dea55b-...gif` |
| `canonicalUrl` | `https://www.maxpreps.com/ga/roswell/centennial-knights/` |
| `ranking` | `143835` |

`initialCareerResults` is a parallel athlete list (38 entries for `Centennial`); config Step 1 should filter to schools only. `pageProps.signals` (`location`, `gender`, `sport`, `state`, `tab`) were all `false` on captured pages — no active facet filters in these requests.

`__NEXT_DATA__.query` carries `{ "q": "centennial", "q2": "Centennial" }`.

### 4. Disambiguation and qualifier behavior

**Disambiguation for `Centennial`:** Works. Results list many same-name schools differentiated by **city, state, zip, and mascot** (e.g. Corona CA Huskies vs Roswell GA Knights). The target Centennial High School (Roswell, GA) appears in the list with `schoolId` matching Slice 01 (`52dea55b-3988-4979-b5fd-20376058997f`).

**City qualifier hurts:** `Centennial Roswell` returned **zero** school results and rendered “No results for centennial roswell”. The page suggests “Search instead for” a quoted variant — not investigated live (budget).

**“High school” qualifier hurts:** `Centennial High School` returned **zero** school results. MaxPreps stores/display names as short names (`Centennial`, not `Centennial High School`) despite `schoolShouldAppendHighSchoolString: true` on team pages (Slice 01 fixture).

**Implication for PRODUCT.md §3.2:** Users should search by **school name alone** (e.g. `Centennial`) and pick the correct row using city/state/mascot shown in results — not by typing `Centennial High School, Roswell GA` as a single query.

### 5. Python HTTP reproducibility

| Step | Result |
|------|--------|
| `GET /search/?q=centennial&q2=Centennial` via `capture.py` | **Pass** — `200 text/html`; 32 schools in `initialSchoolResults` |
| Cookies / browser state | **None required** |
| JavaScript execution | **Not required** for search results — SSR `__NEXT_DATA__` in initial HTML |
| Discovering the URL pattern | **Required browser** (or prior documentation) — homepage cache alone does not reveal `/search` |

**Conclusion:** A normal Python HTTP client can perform school search **after** knowing the `/search/?q=&q2=` pattern. Parsing `__NEXT_DATA__.props.pageProps.initialSchoolResults` is sufficient. No headless browser is needed for the search-results fetch itself.

### 6. Feasibility for school-first UX (PRODUCT.md §3.2, §10, §28 assumption 2)

| Question | Answer |
|----------|--------|
| Can a user type a school name and get disambiguated results without a URL? | **Yes**, for queries MaxPreps accepts (e.g. `Centennial`) |
| Is config Step 1 feasible without pasting a URL? | **Yes**, via HTML search page + `initialSchoolResults` parsing |
| What extra inputs help? | **City/state/ZIP are for disambiguation in the results picker**, not as query string qualifiers. Advise users not to append city or “High School” to the search box. Optional state filter UI (“States” tab) exists on the search page but was not captured as a URL parameter in this slice. |
| Stop-risk signals? | **Low for fetch** (SSR HTML works from Python). **Medium for UX guidance** — naive queries like “Centennial Roswell” or “Centennial High School” fail silently (0 results). Integration config flow should use short name search + structured result selection. |

### 7. Fragility notes

- **Query sensitivity:** Multi-token queries with city or “high school” can return empty results even when the school exists.
- **`q` / `q2` dual parameters:** Both appear required in practice; normalization behavior may change.
- **Mixed result types:** Search returns schools and athletes; client must ignore `initialCareerResults` for school config.
- **`buildId`:** Present but search results do not depend on `/_next/data/<buildId>/search.json` (not observed for this flow).
- **Ranking field:** Opaque sort key; do not rely on it for disambiguation logic.
- **Homepage HTML insufficient:** Search endpoint/pattern is not discoverable from Slice 01 homepage capture alone.

### 8. Cache and fixture pointers

| Artifact | Path |
|----------|------|
| Search `Centennial` (primary) | `captures/private/www.maxpreps.com/fa53b72527c52da4.{raw,json}` |
| Search `Centennial Roswell` (0 results) | `captures/private/www.maxpreps.com/7067e8ce16a34c25.{raw,json}` |
| Search `Centennial High School` (0 results) | `captures/private/www.maxpreps.com/7b8861cab6a5ca6e.{raw,json}` |
| Committed fixture | `tests/fixtures/maxpreps/centennial/search-centennial.json` — `initialSchoolResults` for query `Centennial` |

---

## Slice 03 — School identifiers

**Evidence mode:** Fixture analysis from Slices 01–02 (`search-centennial.json`, `schedule-26-27.json`) plus one live school-home capture (`/ga/roswell/centennial-knights/`). No additional sport/team pages fetched (Slice 04 deferred).

**Target school:** Centennial (Roswell, GA) — UUID `52dea55b-3988-4979-b5fd-20376058997f`.

### 1. Identifier inventory

| Field name | JSON path (page) | Example value | Appears to identify | Classification |
|------------|------------------|---------------|---------------------|----------------|
| `schoolId` | Search → `initialSchoolResults[]` | `52dea55b-…` | The school | **appears to be Stable school identity** |
| `schoolId` | School home → `schoolContext.schoolId` | `52dea55b-…` | The school | **Stable school identity** |
| `schoolId` | School home → `schoolContext.schoolInfo.schoolId` | `52dea55b-…` | The school | **Stable school identity** |
| `schoolId` | School home → `schoolContext.sportSeasons[]` | `52dea55b-…` (constant across 47 rows) | The school (same UUID for every sport/level/year row) | **Stable school identity** |
| `schoolId` | Football schedule → `teamContext.teamSeasonPickerData[]` | `52dea55b-…` (constant across 55 football season rows) | The school | **Stable school identity** |
| `schoolId` | Football schedule → `mostRecentAdminGenderSportSeasonLevel` / `mostRecentPublicGenderSportSeasonLevel` | `52dea55b-…` | The school | **Stable school identity** |
| `mpschoolid` | Team/schedule/school HTML → `<meta name="targeting">` | `52dea55b-…` | The school (ad/routing context) | **Stable school identity** (alias) |
| `schoolid` | Team/schedule/school → `__NEXT_DATA__.query.schoolid` | `52dea55b-…` | The school (legacy ASPX rewrite param) | **Stable school identity** (alias) |
| `teamId` | Football team/schedule → `teamContext.data.teamId` | `52dea55b-…` | **The school**, not the sport/team — see §2 | **Stable value, misnamed field** |
| `teamId` | Football schedule → `teamContext.tda.teamId` | `52dea55b-…` | The school (paired with `sportSeasonId` for TDA flags) | **Stable value, misnamed field** |
| `teamId` | Football schedule → `featuredGameData.teams[]` / contest rows | `52dea55b-…` (Centennial); opponents use their own school UUIDs | School of each contest participant | **School UUID in contest context** — not a team-season key |
| `teamId` | School home → `schoolContestsWithStreamingLinks[].currentTeam.teamId` | `52dea55b-…` | Centennial school | **School UUID** |
| `teamId` | School home → `schoolContestsWithStreamingLinks[].opponentTeam.teamId` | e.g. `1d429384-…` (St. Pius X) | Opponent school | **School UUID** (opponent’s) |
| `sportSeasonId` / `ssid` | Team/schedule `query`, `teamContext.data`, picker rows, contests | e.g. `2286cd80-…` (varsity football 26-27) | A specific team-season (gender + sport + level + year) | **Team-season identity** — varies per sport/level/year; **not** school identity |
| `allSeasonId` | Team/schedule `query`, picker rows | e.g. `22e2b335-…` | MaxPreps “team program” scope (school + gender + sport + level; spans years; **not** shared across levels — see Slice 05) | **Program scope** — not school identity; optional metadata for integration |
| `canonicalUrl` | Search, school home, team pages | `https://www.maxpreps.com/ga/roswell/centennial-knights/` | School’s public URL | **Stable path** — good secondary key / link target |
| `canonicalUrl` (team) | Football schedule → `teamContext.data.canonicalUrl` | `…/centennial-knights/football/` | Team-season page path | **Display / navigation** — sport-specific |
| Mascot image path | `mascotUrl`, `schoolMascotUrl` | `…/school-mascot/5/2/d/52dea55b-…gif` | School (UUID embedded in path) | **Derived from school UUID**; `?version=` params are cache-busters |
| `name`, `city`, `state`, `zip`, `mascot` | Search results, `schoolInfo` | `Centennial`, `Roswell`, `GA`, `30076-3417`, `Knights` | Human display / disambiguation | **Display** — not stable keys (many “Centennial” schools) |
| `ranking` | Search results | `143835` | Opaque sort/rank key | **Display / SEO** — do not use for identity |
| URL slug segments | Path | `ga/roswell/centennial-knights` | SEO routing | **Display / SEO** — prefer `canonicalUrl` or UUID over slug alone |
| `buildId` | `__NEXT_DATA__.buildId` | `92628a14-f7050eaf` | Next.js deploy | **Deploy-specific** — not school identity |

### 2. Reconciliation: `schoolId` vs `mpschoolid` vs `teamId`

All three names carry the **same UUID** (`52dea55b-3988-4979-b5fd-20376058997f`) for Centennial on every page examined, but they appear in **different contexts** with different semantics:

| Name | Where it appears | Surrounding object describes |
|------|------------------|------------------------------|
| `schoolId` | Search `initialSchoolResults[]`; school home `schoolContext`; `teamSeasonPickerData[]`; `schoolLinksData` | A **school** record |
| `mpschoolid` | HTML `<meta name="targeting">` on school home, football team, and football schedule | Page ad/targeting context for a **school** (`pagetype`: `school_home` or team pages with school zip/state) |
| `schoolid` (lowercase) | `__NEXT_DATA__.query` on all three page types | Legacy routing parameter naming a **school** (`currentContext`: `School` or `Team`) |
| `teamId` | `teamContext.data` on football team/schedule pages only; contest participant objects; `tda` block | On **team pages**, the object is a team-season view (`sport`, `level`, `sportSeasonId` vary) but `teamId` equals the school UUID and sits beside `schoolName`, `schoolCanonicalUrl`, etc. On **school home**, there is no `teamContext.data.teamId` — school identity is `schoolContext.schoolId` instead. |

**Counter-evidence that `teamId` is sport-specific (it is not):**

1. **Search** assigns the UUID as `schoolId` on school objects before any sport is selected.
2. **School home** (`pagetype: school_home`) exposes `schoolContext.schoolId` and **no** `teamId` at the school root. `schoolContext.sportSeasons` lists 47 team-season rows (Baseball, Basketball, Football, Softball, … across levels) that all share the same `schoolId` while each row has a distinct `sportSeasonId`.
3. **Football schedule** `teamSeasonPickerData` (55 rows: varsity/JV/freshman × multiple years) keeps `schoolId` constant; only `sportSeasonId`, `sport`, `level`, and `year` change.
4. **Opponents** in contest data use **different** `teamId` values (e.g. Riverwood `249b3bdb-…`, St. Pius X `1d429384-…`) — the field distinguishes **schools**, not sport variants of the same school.
5. The actual per-team-season key is consistently **`sportSeasonId`** (`ssid` in query/meta), which changes when sport, level, or year changes.

### 3. What the UUID represents

**Conclusion:** This UUID identifies the **MaxPreps school** (the institution/program). Field `teamId` on team pages **is a misnomer** for that school UUID — MaxPreps overloads the name `teamId` in team-page `teamContext` and some contest objects, but the value is the school’s primary key, not a sport/team-season key. The sport/team-season key is **`sportSeasonId`** (`ssid`).

Evidence summary:

- Same UUID in search `schoolId`, school-home `schoolContext.schoolId`, `mpschoolid`, `query.schoolid`, and football `teamContext.data.teamId`.
- `sportSeasonId` varies across sports/levels/years while `schoolId` / `teamId` (school sense) stays fixed.
- Mascot CDN paths embed the school UUID (`/school-mascot/5/2/d/52dea55b-…`).
- Legacy URLs use `schoolid=<uuid>` (`home.aspx?schoolid=…`, `schedule.aspx?schoolid=…&ssid=…`).

### 4. Recommended persisted school identity (PRODUCT.md §27.I, §28 assumption 3)

**Config entry should store:**

| Key | Source | Purpose |
|-----|--------|---------|
| `school_id` (primary) | Search result `schoolId` | Stable MaxPreps school UUID — use for all upstream lookups that accept `schoolid` / `mpschoolid` |
| `canonical_url` (secondary) | Search result `canonicalUrl` | Human-readable link, URL construction fallback, config-entry title context |
| Display fields (cached, refreshable) | `name`, `city`, `state`, `zip`, `mascot` | Config UI and entity friendly names — not identity keys |

**Do not use as school identity:**

- URL slug or path segments alone (`centennial-knights`, `ga/roswell/…`)
- Display `name` alone (32 schools named “Centennial” in search)
- `city` / `state` / `zip` / `mascot` as keys (disambiguation display only)
- `ranking`
- `buildId` or any Next.js deploy metadata
- `teamContext.data.teamId` as a *semantic* team key — treat it as an alias of `school_id` if encountered on team pages, but prefer `schoolId` from search/school-home payloads
- `sportSeasonId` / `ssid` / `allSeasonId` — these are team-season scope (Slice 05), not school scope

**Canonical path vs UUID:** Store **both**. The UUID is the authoritative stable identifier; `canonicalUrl` is a stable-enough public path observed in search and school-home data and is needed for user-facing links. Slugs alone are insufficient (no internal ID; collision risk across same-name schools).

**Image URLs:** `mascotUrl` / `schoolMascotUrl` may be cached for display; strip or ignore `?version=` query params for identity purposes.

### 5. Fragility / misnomer risks

- **`teamId` naming collision:** Code that maps MaxPreps `teamId` → “team entity ID” will conflate school and team-season. Always pair contest `teamId` with `sportSeasonId` for team-season context; for school config, use `schoolId` from search/school-home.
- **Field name inconsistency:** `schoolId` vs `schoolid` (casing) vs `mpschoolid` vs `teamId` — same UUID, four names. A future client should normalize to one internal `school_id`.
- **`teamSeasonPickerData` scope:** On the football schedule page, picker rows are football-only (55 rows). Full cross-sport enumeration comes from school-home `sportSeasons` (47 rows for 26-27 alone) — Slice 04 scope.
- **Slug/path changes:** Not observed for Centennial; validation schools (Slice 16) should confirm UUID/path pairing holds elsewhere.
- **`buildId`:** Changes on redeploy; never key config on it.

### 6. Cache and fixture pointers

| Artifact | Path |
|----------|------|
| Search results (primary `schoolId` source) | `tests/fixtures/maxpreps/centennial/search-centennial.json` |
| Football schedule (`teamId` misnomer, picker, contests) | `tests/fixtures/maxpreps/centennial/schedule-26-27.json` |
| Football team page (private) | `captures/private/www.maxpreps.com/2d2db64f2397299e.{raw,json}` |
| Football schedule page (private) | `captures/private/www.maxpreps.com/a9fd9f8193667e1d.{raw,json}` |
| School home (private; cross-sport `sportSeasons`) | `captures/private/www.maxpreps.com/ad4dcfdcad97c61a.{raw,json}` |

---

## Slice 04 — Team enumeration

**Evidence mode:** Fixture analysis from school-home capture (`/ga/roswell/centennial-knights/`). **Zero live requests** — Slice 03 cache reused. Football `teamSeasonPickerData` from `schedule-26-27.json` compared for field alignment only (football-only, multi-year scope).

**Target school:** Centennial (Roswell, GA) — `school_id` `52dea55b-3988-4979-b5fd-20376058997f`.

### 1. How enumeration is sourced

After config Step 1 (school selected), team discovery should fetch the **school home page** (`canonicalUrl` from search) and parse:

```
GET <school canonicalUrl>
  → __NEXT_DATA__.props.pageProps.schoolContext.sportSeasons[]
```

| Source | Scope | Suitable for Step 2? |
|--------|-------|---------------------|
| **`schoolContext.sportSeasons[]`** (school home) | All sports/levels for the **current school year** (47 rows for Centennial 26-27 observed, we cannot assume client invariant) | **Yes — primary** |
| `teamContext.teamSeasonPickerData[]` (team page) | **Single sport only** (e.g. 55 football rows spanning 04-05…26-27) | **No** for cross-sport enumeration; useful for season history within one sport (Slice 12) |
| `schoolContext.menu` | Navigation chrome, not a team list | **No** |

Transport is the same as Slices 01–03: one SSR HTML `GET`, no separate JSON API, no cookies. Internal route: `page: /school` (`pagetype: school_home`); legacy rewrite `school/home.aspx?schoolid=<uuid>`.

### 2. `sportSeasons[]` suitability for config Step 2

Centennial school home (`sportSeasons`, 47 rows):

| Question | Finding |
|----------|---------|
| **Current season only?** | **Yes** — all 47 rows are `year: "26-27"`. No prior-year rows in this array (contrast football `teamSeasonPickerData`, which lists 23 years of football alone). |
| **Historical rows?** | **Not in `sportSeasons`** at capture time. Historical team-season selection would require per-sport team pages (out of Slice 04 scope). |
| **Duplicate representations?** | **Two cases** where the same `sport` + `gender` + `level` + `year` appears twice — differentiated by `season` and `sportSeasonId`: Boys JV Soccer (Spring vs Winter URLs) and Boys Freshman Baseball (Spring vs Fall URLs). These are **distinct team-seasons**, not accidental dupes. |
| **Inactive / empty / leftover teams?** | All rows have `isPublished: true`. No `isDeleted`, empty schedule flags, or unpublished rows observed. Cannot confirm whether unpublished seasons are omitted from the array vs listed with `isPublished: false` — only `true` seen here. |
| **Missing sports?** | Only **Girls Varsity Track & Field** appears; no Boys Track & Field row. May reflect what MaxPreps lists for this school, not a parsing gap. |
| **Misnamed `schoolId`?** | Every row carries `schoolId: 52dea55b-…` — the **school UUID** (Slice 03). Constant across all 47 rows. **Not a team key.** |

**Conclusion:** `sportSeasons[]` can drive PRODUCT.md §3.2 Step 2 (“Discover Teams”) for the **current school year** without extra filtering for year or inactive rows. Present **one selectable row per `sportSeasonId`** (47 choices at Centennial). Do **not** collapse the two Spring/Winter or Spring/Fall JV/freshman pairs — they have different `sportSeasonId` values and URLs.

Optional UX grouping: sort or section by `sport`, then `gender`, then `level` — no deduplication beyond `sportSeasonId` uniqueness.

### 3. Field map (select-teams UI)

There is **no** dedicated `displayName` field. Compose display label from structured fields (PRODUCT.md §8: treat sport, gender, level as metadata).

| UI need | `sportSeasons[]` field | Notes |
|---------|------------------------|-------|
| **Display name** | *(derived)* | `{gender} {level} {sport}` — e.g. `Boys Varsity Football`, `Girls JV Basketball`. Matches PRODUCT.md §3.2 examples. `teamLevel` duplicates `level` (always equal in this capture). |
| **Sport** | `sport` | Canonical string: `Football`, `Track & Field`, `Flag Football`, … |
| **Gender** | `gender` | `Boys` or `Girls`. Always present in this capture; never empty or `Coed`. |
| **Level** | `level` | `Varsity`, `JV`, or `Freshman`. |
| **Current season (school year)** | `year` | Format `YY-YY` (e.g. `26-27`). Single value across all rows here. |
| **Season term** | `season` | `Fall`, `Winter`, or `Spring` — disambiguates multi-term sports and the two “duplicate” rows. |
| **URL** | `canonicalUrl` | Team home page (trailing slash). Schedule is `{canonicalUrl}schedule/`. |
| **Team-season identity** | `sportSeasonId` | UUID — **primary key for a selected team** (`ssid` on team/schedule pages). Unique across all 47 rows. |
| **Season cohort** | `allSeasonId` | UUID shared by some related rows (e.g. all varsity football levels do **not** share one `allSeasonId` — varsity/JV/freshman football each have distinct values). See Slice 05. |
| **Published flag** | `isPublished` | All `true` here; may be useful if `false` rows appear at other schools. |
| **School identity** | `schoolId` | School UUID — **same on every row**; use config `school_id` from Step 1, not this field as team identity. |

**Do not use as team key:** `schoolId` on these rows (school scope), URL slug segments alone, or `teamId` from team pages (Slice 03 — misnamed school UUID).

### 4. URL path conventions (unusual segments)

Gender and season are **sometimes** encoded in the path rather than separate query params:

| Pattern | Examples |
|---------|----------|
| Default boys varsity | `football`, `basketball`, `lacrosse` |
| Level suffix | `football/jv`, `baseball/freshman` |
| Gender in path | `basketball/girls`, `cross-country/girls`, `volleyball/boys`, `wrestling/girls` |
| Season in path | `golf/spring`, `golf/girls/spring`, `softball/fall`, `soccer/spring`, `soccer/jv/winter` |
| Combined | `flag-football/girls/jv/fall`, `tennis/girls/jv/spring`, `soccer/freshman/spring` |

A client should use `canonicalUrl` from the payload, not reconstruct paths from sport/gender/level.

### 5. Centennial teams (26-27)

Grouped by sport (47 rows → 45 unique `sport`+`gender`+`level` combos; `x2` = two `sportSeasonId`s differing by `season`):

| Sport | Teams (gender / level) |
|-------|------------------------|
| Baseball | Boys: Freshman x2, JV, Varsity |
| Basketball | Boys: Freshman, JV, Varsity; Girls: Freshman, JV, Varsity |
| Cross Country | Boys Varsity; Girls Varsity |
| Flag Football | Girls: JV, Varsity |
| Football | Boys: Freshman, JV, Varsity |
| Golf | Boys Varsity; Girls Varsity |
| Lacrosse | Boys: Freshman, JV, Varsity; Girls: Freshman, JV, Varsity |
| Soccer | Boys: Freshman, JV x2, Varsity; Girls: Freshman, JV, Varsity |
| Softball | Girls: JV, Varsity |
| Swimming | Boys Varsity; Girls Varsity |
| Tennis | Boys: JV, Varsity; Girls: JV, Varsity |
| Track & Field | Girls Varsity only |
| Volleyball | Boys Varsity; Girls: Freshman, JV, Varsity |
| Wrestling | Boys Varsity; Girls Varsity |

**Football cross-check** (varsity 26-27): `sportSeasons` `sportSeasonId` `2286cd80-c46d-4739-8dd1-92a67ca8daa7` matches football schedule `teamContext.data.sportSeasonId` and `query.ssid` in `schedule-26-27.json`. Football `teamSeasonPickerData` 26-27 rows (3 levels) are a **subset** of `sportSeasons` with identical field values.

Full row-level table (all `sportSeasonId`s): see committed fixture `tests/fixtures/maxpreps/centennial/sport-seasons-26-27.json`.

### 6. What a future client should persist per selected team

Config entry stores **school** identity from Step 1 (`school_id`, `canonical_url`). Each **selected team** (PRODUCT.md §4.1 entities) should persist:

| Key | Source | Purpose |
|-----|--------|---------|
| `sport_season_id` (primary) | `sportSeasonId` | Stable team-season key for schedule fetches (`ssid` / `query.ssid`) |
| `all_season_id` | `allSeasonId` | Optional program-scope metadata (Slice 05) — not a fetch key |
| `canonical_url` | `canonicalUrl` | Team home URL; append `schedule/` for schedule page |
| `sport`, `gender`, `level` | same-named fields | Entity naming and sport-agnostic pipeline (§8) |
| `year` | `year` | School year label (`26-27`) |
| `season` | `season` | Term within year (`Fall` / `Winter` / `Spring`) |
| Display label (cached) | derived `{gender} {level} {sport}` | Config UI and `friendly_name` — not an identity key |

**Do not persist** `schoolId` from `sportSeasons[]` rows as the team identifier — it is always the school UUID. **Never** use `teamContext.data.teamId` as a team key (Slice 03).

### 7. `sportSeasons[]` vs `teamSeasonPickerData[]`

| Aspect | `sportSeasons[]` (school home) | `teamSeasonPickerData[]` (team page) |
|--------|-------------------------------|--------------------------------------|
| Sports covered | All (14 at Centennial) | One sport (football on schedule capture) |
| Years | Current only (`26-27`) | Many (football: 04-05…26-27) |
| Row shape | Identical field set | Identical field set |
| Use in integration | **Step 2 team picker** | Per-sport season history / re-validation (later slices) |

Shared fields: `sportSeasonId`, `allSeasonId`, `canonicalUrl`, `gender`, `sport`, `level`, `teamLevel`, `season`, `year`, `isPublished`, `schoolId`.

### 8. Feasibility for PRODUCT.md §3.2 Step 2 and §8

| Question | Answer |
|----------|--------|
| Can we list teams after school selection? | **Yes** — one school-home `GET` → `sportSeasons[]` |
| Sport-agnostic? | **Yes** — 14 sports without hardcoding; metadata fields present on every row |
| Python HTTP only? | **Yes** — same SSR pattern as Slices 01–03 |
| Filtering required? | **Minimal** — use all rows with unique `sportSeasonId`; no year filtering needed when only current year is present. Re-fetch school home when user re-runs config to pick up new seasons. |
| Stop-risk? | **Low** — no extra endpoints discovered; 47-row array is practical for a multi-select config UI |

### 9. Cache and fixture pointers

| Artifact | Path |
|----------|------|
| School home (private; full HTML) | `captures/private/www.maxpreps.com/ad4dcfdcad97c61a.{raw,json}` |
| Committed fixture (`sportSeasons` extract) | `tests/fixtures/maxpreps/centennial/sport-seasons-26-27.json` |
| Football schedule (picker cross-check) | `tests/fixtures/maxpreps/centennial/schedule-26-27.json` |

---

## Slice 05 — Team and season identifiers

**Evidence mode:** Fixture analysis only — **zero live requests**. Sources: `sport-seasons-26-27.json` (47 `sportSeasons[]` rows), `schedule-26-27.json` (football `teamSeasonPickerData` 55 rows spanning 04-05…26-27, schedule `query`, `teamContext.data`, contest rows). Slice 03 school identity not re-proved.

**Target example:** Centennial Varsity Football (Boys) — `school_id` `52dea55b-3988-4979-b5fd-20376058997f`; 26-27 `sportSeasonId` / `ssid` `2286cd80-c46d-4739-8dd1-92a67ca8daa7`; `allSeasonId` `22e2b335-334e-4d4d-9f67-a0f716bb1ccd`.

Addresses PRODUCT.md §27.J (team identity) and §28 assumption 3.

### 1. Recommended identity — Centennial Varsity Football

**What the user selects** in config Step 2 is a **team program** (school + gender + sport + level), e.g. “Boys Varsity Football.” **What MaxPreps uses to fetch one season’s schedule** is a **team-season instance** keyed by `sportSeasonId` (`ssid`).

| Layer | Persist? | Key / fields | Role |
|-------|----------|--------------|------|
| **School** (Step 1) | Yes | `school_id`, `canonical_url` | Already decided in Slice 03 |
| **Team program** (Step 2 selection) | Yes | `sport`, `gender`, `level` | Stable human/program identity across school years; matches what the user picked |
| **Current team-season** (fetch) | Yes | `sport_season_id` (`sportSeasonId` / `ssid`) | **Primary upstream key** for schedule/team pages (`query.ssid`, legacy `schedule.aspx?…&ssid=`) |
| **Navigation** | Yes | `canonical_url` | Team home path from `sportSeasons[]` / picker (append `schedule/` for schedule). Do not reconstruct from sport/gender/level alone (Slice 04 path quirks). |
| **School year + term** | Yes (display + rollover) | `year` (`YY-YY`), `season` (`Fall` / `Winter` / `Spring`) | Disambiguates multi-term sports; required when matching a new `sportSeasonId` after year rollover |
| **Program metadata** | Optional | `all_season_id` (`allSeasonId`) | See §2 — useful correlation, not a fetch key |
| **Display** | Cached | derived `{gender} {level} {sport}`, school name | Friendly names — not identity keys |

Primary team-season identity: sport_season_id (ssid). The observed HTTP fetch mechanism is the payload-provided canonical_url; use sport_season_id to identify and validate the intended team-season rather than assuming a direct public ssid endpoint exists.Not `(school_id + sport + gender + level)` alone — that tuple identifies the program but does not name a specific season without resolving a new `sportSeasonId`.

**Path vs UUID:** Store **both** `sport_season_id` and `canonical_url`. UUID is authoritative for `ssid` query params; path is needed for public links and URL construction. Slug/path segments are not sufficient identity (Slice 03).

**Never use as team key:** `teamContext.data.teamId` or contest `teamId` — misnamed **school** UUID (Slice 03). `schoolId` on `sportSeasons[]` rows is the same school UUID on every row.

**Conventions that must survive into the client** (from Slices 03–05):

- Normalize MaxPreps field names to internal snake_case (`school_id`, `sport_season_id`, `all_season_id`, `canonical_url`).
- Treat `ssid`, `sportSeasonId`, and `query.ssid` as the same identifier.
- Treat `teamId` on team pages as `school_id` if encountered — never as a per-team entity key.
- Prefer payload `canonicalUrl` over hand-built paths.

### 2. `allSeasonId` grouping analysis

Slice 03 hypothesized `allSeasonId` might group a broad sport/year cohort shared across levels. Slice 04 falsified level-sharing for football. This slice determines what it actually groups.

#### 2a. `sportSeasons[]` (26-27) — group by `allSeasonId`

47 rows → **45 unique** `allSeasonId` values. Only **two** `allSeasonId`s are shared by multiple rows (same school year):

| `allSeasonId` (prefix) | Rows sharing | Sport / gender / level | `season` values | Distinct `sportSeasonId`s |
|------------------------|--------------|------------------------|-----------------|---------------------------|
| `0ce4c0c7-…` | 2 | Boys JV Soccer | Spring, Winter | 2 (`bac8b420-…`, `90673742-…`) |
| `526e1ebe-…` | 2 | Boys Freshman Baseball | Spring, Fall | 2 (`631feb7b-…`, `519650ec-…`) |

The other **43** `allSeasonId`s each map **1:1** to a single `sportSeasonId` in this capture (one row each). Football varsity, JV, and freshman each have **different** `allSeasonId`s (`22e2b335-…`, `42e4927a-…`, `c6d2f5e9-…`).

Spring/Winter soccer: only **Boys JV** pairs share an `allSeasonId` (Spring + Winter). Girls JV Soccer has only Spring in `sportSeasons[]`; Boys/Girls Varsity Soccer each have a single Spring row. No other cross-`season` sharing observed in 26-27.

#### 2b. Football `teamSeasonPickerData` — varsity across years

Varsity football picker: **23** rows (`04-05` … `26-27`), **one** `allSeasonId` (`22e2b335-…`) for all years, **23 distinct** `sportSeasonId`s (new UUID every school year). JV (`42e4927a-…`, 17 years) and Freshman (`c6d2f5e9-…`, 15 years) show the same pattern — stable `allSeasonId` per level, rotating `sportSeasonId` per year.

#### 2c. Where `allSeasonId` appears

| Location | Example (varsity football 26-27) |
|----------|-------------------------------------|
| Schedule `query.allSeasonId` | `22e2b335-…` |
| `teamContext.data.allSeasonId` | `22e2b335-…` (matches query) |
| `teamSeasonPickerData[]` rows | Per row; constant across years for a given level |
| `sportSeasons[]` (school home) | Per row; matches picker for 26-27 football rows |
| `mostRecentPublicGenderSportSeasonLevel` / `mostRecentAdminGenderSportSeasonLevel` | Current season row incl. both IDs |
| Admin gateway URLs (`accessid2=`) | `22e2b335-…` paired with `school_id` as `accessid1` |
| Contest columnar rows | **`ssid` / `sportSeasonId` present** (`2286cd80-…`); `allSeasonId` **not** observed on contest rows — Slice 06 |

#### 2d. Conclusion

**It groups the MaxPreps “team program”** at a school: **school + gender + sport + level**, spanning multiple school years and (for a few sports) multiple season terms within one school year.

Sharing pattern:

- **Same `allSeasonId`:** same school, gender, sport, level — possibly multiple `year` values and/or multiple `season` terms (only Boys JV Soccer and Boys Freshman Baseball in 26-27).
- **Different `allSeasonId`:** different level, sport, or gender — even within the same sport and school year (football varsity vs JV vs freshman).
- **Not** a school-year cohort across levels. **Not** interchangeable with `sportSeasonId` for schedule fetch.

**Integration use:** `allSeasonId` is **more durable across school years** than `sportSeasonId` for the same program (varsity football unchanged since at least `04-05`), but it does **not** identify a single season’s schedule. **Persist as optional metadata** (`all_season_id`) for correlation, admin-URL context, and program-level grouping — optional for individual schedule fetches, but useful as the preferred program-correlation/rollover key when available; retain semantic fields as fallback and validation.Do not rely on it as the primary team or team-season key.

### 3. `sportSeasonId` vs `allSeasonId` durability

| Identifier | Year-specific? | Evidence |
|------------|----------------|----------|
| `sportSeasonId` / `ssid` | **Yes** — new UUID each school year (and each season term when multi-term) | 23 varsity football years → 23 distinct `sportSeasonId`s; Boys JV Soccer Spring vs Winter → two `sportSeasonId`s, one `allSeasonId` |
| `allSeasonId` | **No** (for a given program) — stable across years for football varsity/JV/freshman | Varsity `22e2b335-…` constant from `04-05` through `26-27`; only 3 football `allSeasonId`s across 55 picker rows (one per level) |

For identifying **“Centennial Varsity Football, 26-27 season”**, use (`school_id`, `sport_season_id`) together. `sportSeasonId` alone does not uniquely identify the school/team-season across MaxPreps. For **“the Centennial varsity football program regardless of year”**, `(school_id, sport, gender, level)` or `allSeasonId` express the same program — but only `sportSeasonId` selects which season’s contests to load.

### 4. Current vs prior season selection

| Mechanism | Scope | Current season | Prior seasons |
|-----------|-------|----------------|---------------|
| `schoolContext.sportSeasons[]` | All sports | **Yes** — all 47 Centennial rows are `year: "26-27"` only (Slice 04) | **Not listed** |
| `teamContext.teamSeasonPickerData[]` | One sport per team page | Includes current year row | **Yes** — football 04-05…26-27 (55 rows) |
| `mostRecentPublicGenderSportSeasonLevel` | One sport (team page) | Points at latest published season for that sport/gender/level | N/A |

**URL convention (football picker evidence):**

- **Current** school year: path **without** year segment — e.g. `…/football/`, schedule `…/football/schedule/`.
- **Prior** years: `…/football/{YY-YY}/schedule/` (e.g. `…/football/25-26/schedule/`). Picker `canonicalUrl` for non-current years points at the schedule path with year embedded.

**Legacy rewrite** (schedule page `query.url`): `schedule.aspx?schoolid=<school_id>&ssid=<sportSeasonId>` — `ssid` always identifies the specific team-season regardless of path year segment.

**Recommended runtime behavior for a “current season” integration:**

1. **Config (Step 2):** User picks a row from `sportSeasons[]`; persist `sport_season_id`, `canonical_url`, `sport`, `gender`, `level`, `year`, `season`, optional `all_season_id`.
2. **Schedule fetch:** `GET {canonical_url}schedule/` (or equivalent with `ssid` in rewrite query) using stored `sport_season_id`.
3. **School-year rollover:** Re-fetch school home `sportSeasons[]`; first attempt to locate the new row using stored `all_season_id`. Validate the match against sport, gender, and level, and account for season where multiple current rows share a program. If `all_season_id` is unavailable or no longer matches, fall back to the semantic program fields. Update `sport_season_id`, year, season, `canonical_url`, and upstream metadata from the selected row.
4. **Prior-season / historical views** (later slice): Use `teamSeasonPickerData[]` from the team page for that sport — not `sportSeasons[]`. Select row by `year` (and `season` if needed); use that row’s `sportSeasonId` and year-bearing `canonicalUrl`.

**Default product assumption:** Track the **current** school-year team-season unless the user explicitly opts into historical season selection (Slice 12).

### 5. Persist vs display (summary)

**Persist per selected team entity:**

- `sport_season_id` — school-scoped team-season identifier — use together with `school_id`; it is not globally unique across schools.
- `canonical_url` — navigation / URL construction
- `sport`, `gender`, `level` — program identity + rollover matching
- `year`, `season` — current team-season context
- `all_season_id` — optional; safe to store, not required for v1 fetches

**Display only (refreshable from upstream):**

- Derived label (`Boys Varsity Football`), school name, logos, record, league names
- `teamId` from MaxPreps payloads (school UUID — expose as `school_id` if needed on entities, not as `team_id` semantic)

**Do not persist as identity:** URL slug segments, `ranking`, `buildId`, `teamContext.data.teamId` as a team key.

### 6. PRODUCT.md §27.J / §28 assumption 3

**Answer:** MaxPreps exposes **stable-enough identifiers** for integration:

- **School:** `school_id` UUID (Slice 03) — validated.
- **Team program:** `sport` + `gender` + `level` at a school — stable user intent; `allSeasonId` appears to identify a MaxPreps-wide sport program classification, roughly sport + gender + level, rather than a school-specific team program. The same Boys Varsity Football `allSeasonId` was observed across four unrelated schools in Georgia and Ohio. Its exact upstream semantics remain inferred rather than contractual.
- **Team-season (fetch):** `sportSeasonId` / `ssid` — stable for a given season; rotates each school year.

Storing `sport_season_id` plus program fields (`sport`, `gender`, `level`) satisfies assumption 3 for a current-season integration with school-year rollover via school-home refresh. `allSeasonId` adds optional durability signal but is not required to identify “Centennial Varsity Football.”

### 7. Cache and fixture pointers

| Artifact | Path |
|----------|------|
| School home `sportSeasons[]` (26-27, 47 rows) | `tests/fixtures/maxpreps/centennial/sport-seasons-26-27.json` |
| Football schedule + picker + contests | `tests/fixtures/maxpreps/centennial/schedule-26-27.json` |
| School home HTML (private) | `captures/private/www.maxpreps.com/ad4dcfdcad97c61a.{raw,json}` |
| Football schedule HTML (private) | `captures/private/www.maxpreps.com/a9fd9f8193667e1d.{raw,json}` |
| Football team HTML (private) | `captures/private/www.maxpreps.com/2d2db64f2397299e.{raw,json}` |

**Slice 06 (complete):** Contest columnar rows decoded in Slice 06 — `sportSeasonId` at participant `[2]`; full field map and gate answer there.

---

## Slice 06 — Schedules (payload structure)

**Evidence mode:** Fixture analysis only — **zero live requests**. Sources: `tests/fixtures/maxpreps/centennial/schedule-26-27.json` (`pageProps`) and schedule HTML cache `captures/private/www.maxpreps.com/a9fd9f8193667e1d.{raw,json}` (JSON-LD cross-check). Positional indices were **not** copied from third-party key lists; they were derived by aligning `pageProps.contests` rows with the named sibling object `pageProps.featuredGameData` (same response, same deploy).

### 1. Payload structure

Schedule data for Centennial varsity football 26-27 lives in `__NEXT_DATA__.props.pageProps` on `GET …/football/schedule/` (Slice 01). Relevant keys:

| Key | Role | Named vs positional |
|-----|------|---------------------|
| `contests` | Full season game list | **Positional** — array of 11 contest rows |
| `featuredGameData` | “Next/featured” game detail box | **Named** — object with `contestId`, `date`, `teams[]`, `canonicalUrl`, etc. |
| `teamContext.data` | School/team chrome (name, record context, `sportSeasonId`) | **Named** — not per-game |
| `tournaments` | Tournament metadata | **Named** — empty array in this capture |
| JSON-LD `ProfilePage.mainEntity.event[]` | Supplementary `SportsEvent` list in HTML | **Named** — incomplete vs `contests` |

**`contests` nesting (arity fixed in this capture):**

```
contests[]                         # 11 rows
└─ row[41]                         # fixed length 41 per row
   ├─ [0]  teams[2]                # two participant sub-arrays
   │        └─ participant[32]     # base width; score fields populate when final
   ├─ [1]  contestId               # UUID
   ├─ [2]  createdOn
   ├─ [3]  isScheduleImport
   ├─ [4]  hasResult
   ├─ [5]  location                # venue name
   ├─ [11] date                    # ISO local datetime (no offset)
   ├─ [14] sportSeasonId           # ssid — not allSeasonId
   ├─ [15] contestState            # int enum (see below)
   ├─ [17] hasContestPage
   ├─ [18] canonicalUrl            # game page URL
   ├─ [21] contestAlias            # e.g. "Game"
   ├─ [24] overtimeShortAlias
   ├─ [28] reasonWhyCannotEnterScores  # human status string
   ├─ [29] description             # prose summary / score line
   ├─ [35] goFanUrl                # optional
   ├─ [36] nfhsStreamUrl           # optional
   ├─ [37] currentTeam             # extended participant (selected school’s view)
   └─ [38] opponentTeam            # extended participant
```

**Participant sub-array** (`teams[0|1]`, width 32): indices aligned to `featuredGameData.teams[]` / `currentTeam` / `opponentTeam` by value match on the Alpharetta (row 3) game:

| Index | Meaning | Evidence |
|-------|---------|----------|
| `[0]` | Row id (internal) | **Proven** — matches `teams[].id` |
| `[1]` | `teamId` → **`school_id`** (school UUID) | **Proven** — matches `teams[].teamId`; Slice 03 misnomer |
| `[2]` | `sportSeasonId` | **Proven** — matches `teams[].sportSeasonId` |
| `[4]` | `index` (1 or 2) | **Proven** — matches `teams[].index` |
| `[11]` | `homeAwayType` | **Proven** — matches `teams[].homeAwayType` (`0` = home, `1` = away) |
| `[13]`–`[24]` | School display fields (`teamCanonicalUrl`, `name`, `city`, `state`, address, mascot, colors, acronym) | **Proven** — field-by-field match to `featuredGameData.teams[]` |
| `[26]` | `contestId` | **Proven** |
| `[3]`, `[5]`, `[6]` | `resultString`, `result` (`W`/`L`), `score` | **Inferred** — absent on upcoming rows; populated on finals in `[37]`/`[38]` copies (e.g. Dunwoody `W` + `23`) |
| `[11] = 2` | Neutral site | **Inferred** — Dunwoody row: `homeAwayType` 2 + description “neutral non-conference game” |

`allSeasonId` does **not** appear on contest rows (Slice 05). Contest participants carry `sportSeasonId` only.

**`contestState` observed (row `[15]` + message `[28]`):**

| Value | Meaning in fixture | Evidence |
|-------|-------------------|----------|
| `1` | Deleted/hidden | **Proven** — row 0: `[28]` = `"ContestState is Deleted."` |
| `2` | Pregame / scheduled | **Proven** — `featuredGameData.contestState: 2` + `"ContestState is Pregame."` |
| `4` | Final (with result) | **Inferred** — rows 1–2: `hasResult: true`, scores present; `[28]` empty |

Other enum values (live, postponed, cancelled) were **not** observed in this fixture.

### 2. Field map — conceptual game object (PRODUCT §7)

Target fields mapped from `contests` + `teamContext` (+ optional JSON-LD for cross-check only). Internal names follow Slice 03–05 conventions (`school_id`, `sport_season_id`).

| Conceptual field | Source | Evidence tier | Notes |
|------------------|--------|---------------|-------|
| `id` | `row[1]` (`contestId`) | **Proven** | Same key in `featuredGameData.contestId` |
| `date` | `row[11]` | **Proven** | `featuredGameData.date`; no TZ offset in payload — localize in client (Slice 08) |
| `status` | `row[15]` `contestState` + `row[4]` `hasResult` + `row[28]` | **Proven** for raw enum; **Inferred** for normalized `deleted` / `scheduled` / `final` labels | Filter `contestState === 1` for deleted rows |
| `team_name` | `teamContext.data.schoolName` | **Proven** | Named key; constant for schedule page |
| `opponent_name` | Opponent participant `teams[*][14]` (`name`) | **Proven** | Matches `featuredGameData.opponentTeam.name` |
| `home_away` | Selected-school participant `teams[*][11]` | **Proven** for `home`/`away` (`0`/`1`); **Inferred** for `neutral` (`2`) | Derive from participant where `[1] === school_id` |
| `team_score` | `row[37][6]` when `row[4]` | **Inferred** | `row[37]` = `featuredGameData.currentTeam` positional twin |
| `opponent_score` | `row[38][6]` when `row[4]` | **Inferred** | `row[38]` = `featuredGameData.opponentTeam` twin |
| `result` | `row[37][5]` (`W` / `L` / …) | **Inferred** | Also available as `row[37][3]` result string (`"W 54-18"`) |
| `venue` | `row[5]` (`location`) | **Proven** | `featuredGameData.location`; may be empty on away games |
| `location` | Participant `city` + `state` (`[15]`, `[16]`) | **Inferred** | UDo not infer game location solely from home/away participant city/state. Use row[5] venue/location plus any explicit game/venue timezone/location metadata when available. Participant city/state describes the school, not necessarily the contest venue, especially for neutral-site or tournament games. |
| `game_url` | `row[18]` (`canonicalUrl`) | **Proven** | `featuredGameData.canonicalUrl`; null on deleted row 0 |

**Not required for gate; remain positional/unknown:** participant `[3]`, `[5]`–`[10]`, `[12]`, `[27]`–`[28]`, `[29]`–`[31]` on base copies; contest row `[6]`–`[10]`, `[12]`–`[13]`, `[16]`, `[19]`–`[20]`, `[22]`–`[27]`, `[30]`–`[34]`, `[39]`–`[40]`.

**Hashed JS bundle dependence:** **Not required.** The named `featuredGameData` object in the same `pageProps` documents the contest-row and participant layout for this deploy. A production client should treat index maps as **versioned fixture-tested constants**, not scrape `asset.maxpreps.io/_next/static/...` chunks.

### 3. Worked examples

**Completed game — Johns Creek (row 2, `contestState` 4):**

```json
{
  "id": "6f7a550c-040a-4f1c-824e-3d0d3b873cef",
  "date": "2026-08-28T19:30:00",
  "status": "final",
  "team_name": "Centennial",
  "opponent_name": "Johns Creek",
  "home_away": "home",
  "team_score": 54,
  "opponent_score": 18,
  "result": "W",
  "venue": "Centennial High School",
  "location": "Roswell, GA",
  "game_url": "https://www.maxpreps.com/ga/football/game/centennial-roswell-vs-johns-creek/8-28-2026/?c=6f7a550c-040a-4f1c-824e-3d0d3b873cef"
}
```

**Upcoming game — Alpharetta (row 3, `contestState` 2; same game as `featuredGameData`):**

```json
{
  "id": "30b79240-4c41-4e25-b850-0052d1221fbd",
  "date": "2026-09-04T19:30:00",
  "status": "scheduled",
  "team_name": "Centennial",
  "opponent_name": "Alpharetta",
  "home_away": "home",
  "team_score": null,
  "opponent_score": null,
  "result": null,
  "venue": "Centennial High School",
  "location": "Roswell, GA",
  "game_url": "https://www.maxpreps.com/ga/football/game/alpharetta-vs-centennial-roswell/9-4-2026/?c=30b79240-4c41-4e25-b850-0052d1221fbd"
}
```

### 4. Row coverage (11 expected)

| Row | Date | Opponent | `contestState` | Decoded? | Notes |
|-----|------|----------|----------------|----------|-------|
| 0 | 2026-08-07 | Riverwood | 1 (deleted) | Yes | Hidden/scrimmage; no `canonicalUrl`; filter from user schedule |
| 1 | 2026-08-20 | Dunwoody | 4 (final) | Yes | Neutral site (`homeAwayType` 2); W 23-21 |
| 2 | 2026-08-28 | Johns Creek | 4 (final) | Yes | Home; W 54-18 |
| 3 | 2026-09-04 | Alpharetta | 2 (pregame) | Yes | Featured game |
| 4 | 2026-09-11 | South Forsyth | 2 | Yes | Away |
| 5 | 2026-09-18 | Cambridge | 2 | Yes | Home |
| 6 | 2026-10-02 | Blessed Trinity | 2 | Yes | Away |
| 7 | 2026-10-09 | St. Pius X Catholic | 2 | Yes | Away |
| 8 | 2026-10-23 | Sprayberry | 2 | Yes | Home |
| 9 | 2026-10-30 | Marist | 2 | Yes | Away |
| 10 | 2026-11-06 | Chattahoochee | 2 | Yes | Home |

**Count confirmed: 11 rows.** All decode to the conceptual game object; row 0 is intentionally excluded from a user-facing schedule (`deleted`).

### 5. Tournaments / hidden rows

- **`pageProps.tournaments`:** `[]` — no tournament bracket metadata in this capture.
- **Hidden/deleted:** Row 0 (Riverwood, 2026-08-07) — `contestState` 1, message `"ContestState is Deleted."`, no game URL. Still decodable; client should drop or mark `status: deleted`.
- **JSON-LD gap (Slice 01):** HTML `ProfilePage.mainEntity.event` lists **9** `SportsEvent` entries — omits deleted Riverwood (expected) **and** completed Dunwoody (neutral final). `contests` remains authoritative; JSON-LD is supplementary only.

### 6. Fragility

| Risk | Impact |
|------|--------|
| **Columnar `contests` encoding** | Any deploy may reorder or resize positional arrays without notice. Mitigation: named `featuredGameData` in the same payload re-anchors indices; fixture tests on `schedule-26-27.json`. |
| **`contestState` enum** | Only values `1`, `2`, `4` observed. Live/postponed/cancelled may add new ints — map unknowns to `unknown` and surface `row[28]` message. |
| **`featuredGameData` scope** | Single game only (next/featured). Full schedule **must** use `contests`, not `featuredGameData` alone. |
| **`buildId` / static chunks** | Irrelevant if client parses `__NEXT_DATA__` from HTML URLs (Slice 01). |
| **Date timezone** | `row[11]` lacks offset; JSON-LD uses UTC (`startDate` with `+00:00`). row[11] lacks an offset. Slice 08 found no per-contest event/venue timezone in contests[]; timezone localization policy remains unresolved for non-featured games. |
| **Participant `teamId`** | Always `school_id` UUID — do not use as per-team-season key (Slices 03–05). |

### 7. Core feasibility gate answer

**Yes-with-caveats.**

Every `contests` row in the Centennial football fixture decodes deterministically into the PRODUCT §7 game object using:

1. Named keys in `featuredGameData` + `teamContext` (same response) to prove positional layout, and  
2. A maintainable index map (fixture-tested), **without** reading hashed `_next/static` bundles.

**Caveats:** positional fragility on redeploy; `contestState` enum incomplete; score fields inferred from extended `[37]`/`[38]` copies (not separate named keys on the row); timezone normalization deferred; deleted row filtering required.

**Hashed-bundle dependence:** **No** — not required for this slice.

---

## Interim feasibility gate

After Slice 06, the following questions must be answered affirmatively (or with documented workarounds) before continuing to Slices 07–18:

| # | Question | Verdict | Evidence (Slices 01–06) |
|---|----------|---------|-------------------------|
| 1 | **Can we find a school?** | **Pass** | Slice 02: `GET /search/?q=…` → `initialSchoolResults[]` with `schoolId`; Centennial Roswell GA disambiguated by city/mascot. |
| 2 | **Can we enumerate teams?** | **Pass** | Slice 04: school-home `sportSeasons[]` lists 47 teams for 26-27; football picker cross-check on schedule page. |
| 3 | **Can we identify a team/season?** | **Pass** | Slice 05: `sport_season_id` (`ssid` / `sportSeasonId`) + `canonical_url`; `allSeasonId` is program metadata only, not a schedule fetch key. |
| 4 | **Can we retrieve a schedule?** | **Pass** | Slice 01: `GET …/football/schedule/` → `pageProps.contests` (11 rows) in `__NEXT_DATA__`. |
| 5 | **Is the schedule data practical to decode?** | **Pass (with caveats)** | Slice 06: columnar `contests` decodes via `featuredGameData`-anchored index map; no browser automation; positional fragility documented. |
| 6 | **Can a normal Python HTTP client make those calls?** | **Pass** | Slice 01: stdlib HTTP, no cookies/JS; search (Slice 02) and schedule pages return full payloads. |

**Gate summary:** All six questions **pass**. Core existential risk (can we normalize games?) is cleared for team-schedule pages of this shape. Remaining slices are validation, edge cases, and multi-school scope — not blockers to a throwaway normalization prototype.

**Slices 07–13:** Expanded in full below (cache-only; zero additional live requests).

### Stop-and-reassess conditions

If any of the following are required to proceed past this gate, **stop and reassess** the HACS integration approach before investing in Slices 07–18:

- Authenticated MaxPreps sessions or account login
- Brittle browser automation (headless browser required for core flows)
- Anti-bot bypasses (CAPTCHA solving, fingerprint spoofing, etc.)
- Reverse engineering that is unsuitable for a maintainable, normal HACS integration

---

## Slice 07 — Final scores, results, and game status

**Evidence mode:** Fixture analysis only — **zero live requests**. Source: `tests/fixtures/maxpreps/centennial/schedule-26-27.json` (Slice 06 field map). Addresses PRODUCT.md §§5–6 (entity attributes and relevant-game states), §13 (final score detection), §14 (scheduled vs live start), and §15 (live score support).

### 1. Normalized status model

Map `contests` row fields to integration-facing `status` and primary-entity lifecycle. Use **team-oriented** score slots — never parse winner-first prose from `row[29]` (`description`).

| MaxPreps source | Normalized `status` | Primary entity state (PRODUCT §5) | Evidence |
|-----------------|---------------------|-----------------------------------|----------|
| `row[15]` `contestState` **1** + `row[28]` `"ContestState is Deleted."` | `deleted` | *(exclude from user schedule)* | **Proven** — row 0 (Riverwood scrimmage) |
| `row[15]` **2** + `row[28]` `"ContestState is Pregame."` | `scheduled` | `PRE` | **Proven** — rows 3–10; matches `featuredGameData.contestState: 2` |
| `row[15]` **4** + `row[4]` `hasResult: true` | `final` | `POST` | **Inferred** — rows 1–2; `[28]` empty on finals |
| `contestState` not in `{1,2,4}` | `unknown` | `UNKNOWN` | **Uncertain** — no samples; surface `row[28]` |
| Live / in-progress | *(do not emit `in_progress`)* | `IN` **not supported** | **Not observed** — see §4 |

**Deleted rows:** Row 0 remains fully decodable (date, opponent, participant data) but must be **filtered from user-facing schedule** and must not become the “relevant game.” Retain internally if needed for debugging or change detection.

**Unknown enums:** Any other `contestState` integer → `status: unknown` and expose `row[28]` (`reasonWhyCannotEnterScores`) as a diagnostic attribute. Do not guess postponed/cancelled/live from enum alone.

### 2. Scores and result — team-oriented (`row[37]` / `row[38]`)

Scores and win/loss are read from the **selected-school view** copies at the end of each contest row, not from display-order strings.

| PRODUCT attribute | Source | When populated | Evidence |
|-------------------|--------|----------------|----------|
| `team_score` | `row[37][6]` (`currentTeam.score`) | `row[4]` `hasResult: true` | **Inferred** — aligned to `featuredGameData.currentTeam` |
| `opponent_score` | `row[38][6]` (`opponentTeam.score`) | same | **Inferred** |
| `result` | `row[37][5]` (`currentTeam.result` → `W` / `L`) | same | **Inferred** |
| `team_score` / `opponent_score` / `result` | — | `hasResult: false` | **Proven** — null/absent on scheduled rows 3–10 |

**Orientation rule:** `row[37]` is always the configured school’s participant (`school_id` at `[37][1]`); `row[38]` is the opponent. This is **not** winner-first ordering.

| Game | `row[37]` score | `row[38]` score | `result` | `row[29]` description (do **not** use for scores) |
|------|-----------------|-----------------|----------|-----------------------------------------------------|
| Dunwoody (row 1, neutral) | 23 | 21 | W | “…won…23-21” — winner-first prose |
| Johns Creek (row 2, home) | 54 | 18 | W | “…lost…54-18” — opponent-centric prose |
| Alpharetta (row 3, scheduled) | — | — | — | “…@ 7:30p.” — no scores |

`row[37][3]` (`resultString`, e.g. `"W 54-18"`) is a display string; prefer discrete `[5]`/`[6]` for entity attributes.

### 3. PRODUCT §6 / §7 attribute mapping (game object)

| Attribute | Source | Notes |
|-----------|--------|-------|
| `game_id` | `row[1]` `contestId` | **Proven** |
| `date` | `row[11]` | Naive local ISO — Slice 08 |
| `status` | §1 table above | |
| `team_score`, `opponent_score`, `result` | `row[37]`/`[38]` when final | Team-oriented |
| `game_url` | `row[18]` `canonicalUrl` | Null on deleted row 0 |
| `status_message` *(optional)* | `row[28]` | Human enum explanation |

### 4. Live / in-progress (PRODUCT §5 `IN`, §15)

| Field | Observed value | Conclusion |
|-------|----------------|------------|
| `featuredGameData.teamsCalculated[].currentLiveScore` | `null` on both teams | **Not observed** |
| `contestState` for live play | No sample | **Not observed** |
| `row[28]` messages | `"Deleted."`, `"Pregame."`, or empty | No in-progress message |

**Integration stance:** Do **not** promise `IN` state or live score updates. PRODUCT §15 is satisfied by treating schedules and finals as primary; live data is explicitly out of scope for v1. If a future deploy adds a new `contestState` with non-null `currentLiveScore`, map cautiously as best-effort — not required for feasibility.

### 5. Final score detection and automations (PRODUCT §13–§14)

**Final detection:** A game becomes `final` when `contestState === 4` and `hasResult === true` with populated `row[37]`/`[38]` scores. Home Assistant can trigger on attribute transition (e.g. `status: scheduled → final`, or `team_score` populated) without custom integration events.

**Scheduled start (PRODUCT §14):** `status: scheduled` + `row[11]` datetime is sufficient for schedule-driven automations (“30 minutes before kickoff”). This is **scheduled start time**, not confirmed in-progress state — consistent with §14’s distinction.

**Adaptive polling (PRODUCT §12):** After the naive-local `row[11]` time passes, increased polling may discover `contestState` 4 — timing of real-world posting not measured in this slice.

### 6. Cache and fixture pointers

| Artifact | Path |
|----------|------|
| Full schedule + scores | `tests/fixtures/maxpreps/centennial/schedule-26-27.json` |
| Field map (Slice 06) | Same fixture — `contests`, `featuredGameData` |

---

## Slice 08 — Dates, times, timezones

**Evidence mode:** Primarily fixture analysis (Centennial `schedule-26-27.json`; JSON-LD from Slice 01 HTML cache). **Pensacola Central-Time probe** added two live requests — see subsection below. Addresses PRODUCT §§6–7 (`date`), §14 (kickoff automations), and §27.E (start-time reliability).

### 1. Raw datetime fields

| Field | Location | Format | Evidence |
|-------|----------|--------|----------|
| Contest datetime | `contests[][11]` | Naive local ISO, no offset — e.g. `2026-09-04T19:30:00` | **Proven** — all 11 rows include time component |
| Featured game datetime | `featuredGameData.date` | Same as row 3 `row[11]` | **Proven** |
| JSON-LD event time | HTML `SportsEvent.startDate` | UTC with offset — e.g. `…+00:00` (Slice 01) | **Proven** (HTML cache) — supplementary only |
| Standings timestamp | `teamContext.teamSettings.standingsUpdatedOn` | Naive local | Not contest time |

All 10 user-visible games in this fixture carry a **specific clock time** (mostly `19:30`, Dunwoody `16:30`). **TBA** and **date-only** contests were **not observed** (`isTeamTBA: false` on `featuredGameData.teams[]`; no date-only flag found on contest rows).

### 2. Timezone metadata inventory

| Scope | Fields | Where | Per-contest in `contests[]`? | Classification |
|-------|--------|-------|------------------------------|----------------|
| **Event / venue timezone** | *(none found)* | — | **No** | **Not observed** — no field ties TZ to `row[5]` venue or game site |
| **School participant timezone** | `timeZoneId`, `utcOffset`, `dstOffset` | `featuredGameData.teams[]`, `featuredGameData.currentTeam` / `opponentTeam` | **No** — only on featured-game named objects | **Proven** for featured game only — values are per-**school** (`EDT`, `utcOffset: -18000`, `dstOffset: 3600`), not venue-specific |
| **Featured game UTC** | `contestDateInGMT` | `featuredGameData` only | **No** — featured game only | **Proven** (Centennial fixture; Pensacola probe) — naive UTC/GMT anchor; aligns with JSON-LD `startDate` on matched games |
| **State / governing-body timezone** | `timeZoneCode`, `timeZoneName`, `timeZoneOffset`, `timeZoneOffsetText`, `timeZoneObservesDayLightSavings` | `teamContext.stateData` (Georgia → `EST`, offset `-5:00`) | Page-level, not per contest | **Proven** — **state-level fallback candidate**, not school-address-specific |
| **Contest row participants** | Base `teams[*]` and extended `[37]`/`[38]` | Positional participant arrays | **No** `timeZoneId` / offset fields found on any of 11 rows | **Proven absence** |

**Key finding:** Non-featured contests expose **only** naive `row[11]` with **no event-specific timezone metadata** in `contests[]`. The featured game adds **school-level** timezone on its named team objects, not a separate event/venue zone.

### 3. Localization strategy (evidence-based, not locked client behavior)

| Approach | Feasibility in this fixture | Label |
|----------|----------------------------|-------|
| Parse `row[11]` as local wall time in **venue** timezone | **Unsupported** — no venue TZ field | **Unknown** |
| Apply **school** timezone from opponent/home school objects | Only available for **featured** game’s `teams[]`; absent on other contest rows | **Featured-game only** |
| Apply **state** timezone from `teamContext.stateData` | Available once per schedule page for GA schools | **Fallback candidate** — state-level, not guaranteed for every contest (away games in other states, neutral sites) |
| Convert JSON-LD UTC `startDate` | Possible for 9 JSON-LD events (Slice 01) but incomplete vs 11 `contests` rows | **Supplementary / uncertain** |

**Do not lock** “use school TZ for all games” as final client behavior. Current evidence supports:

1. **Featured game:** `row[11]` + school `timeZoneId`/`utcOffset`/`dstOffset` on `featuredGameData` teams → automations **fully specified** for that one contest.
2. **Other contests:** `row[11]` only → kickoff automations require a **fallback candidate** (e.g. state TZ from `teamContext.stateData`, or configured user TZ). MaxPreps does not supply per-contest TZ on these rows — treat offset application as **integration policy**, not proven upstream fact.

### 4. Cross-check: local time vs JSON-LD UTC (Slice 01)

Slice 01 observed JSON-LD `startDate` in UTC while `row[11]` is naive local Eastern. For Alpharetta (`2026-09-04T19:30:00` local), JSON-LD UTC conversion aligns with Eastern offset at that date — but JSON-LD omits two contests (deleted Riverwood, neutral Dunwoody final). **`contests` + explicit TZ policy is authoritative**; JSON-LD is not a complete alternate clock source.

### Pensacola timezone validation probe

**Evidence mode:** Two live requests (school search + varsity football schedule). Target: Pensacola High School (`schoolId` `60e92873-90b6-4627-9746-8dd57b1f0473`, zip `32501`, Pensacola FL — **Central Time** panhandle). Private caches: `61a2b3dbdb9eb797.*` (search), `4acd39e363b6d8ab.*` (schedule). Compared against Centennial football fixture + Slice 01 HTML cache.

**Discovery:** `GET /search/?q=pensacola&q2=Pensacola` → `initialSchoolResults[]` entry `name: Pensacola`, `city: Pensacola`, `state: FL`, `canonicalUrl: …/fl/pensacola/pensacola-tigers/`. Schedule: `GET …/football/schedule/` → same `pageProps` shape as Centennial (10 user-visible contests + 1 deleted row).

**Featured game (row matching `featuredGameData.contestId` `73c8abf8-…`, Pensacola at Booker T. Washington):**

| Field | Value |
|-------|-------|
| `contests[][11]` / `featuredGameData.date` | `2026-09-04T19:00:00` |
| `featuredGameData.contestDateInGMT` | `2026-09-04T23:00:00` |
| JSON-LD `startDate` (matched by `contestId` in event URL) | `2026-09-04T23:00:00+00:00` |
| `teamContext.stateData` | `timeZoneCode: EST`, `timeZoneName: Eastern Standard Time`, `timeZoneOffset: -5`, `timeZoneOffsetText: -5:00`, `timeZoneObservesDayLightSavings: true` |
| `featuredGameData.teams[]` (both schools) | `timeZoneId: CDT`, `utcOffset: -21600` (−6 h standard), `dstOffset: 3600` → effective **−5 h** (CDT) |

**Naive vs UTC cross-check (all 10 JSON-LD-matched contests):** Treating naive `row[11]` as wall time and comparing to JSON-LD UTC, offset **−4 h** (EDT) yields **0 s** difference on every matched game; **−5 h** (CDT/CST+DST) yields **3600 s** (1 h) error on every game. Same pattern as Centennial Eastern alignment (Slice 08 §4).
Participant timezone appears geographically accurate for the school, but is not sufficient to determine contest timezone.

Example: UTC `23:00` → Eastern local **19:00** (matches naive); Central (CDT) local would be **18:00** — does not match naive `19:00`.

#### Probe answers

| Question | Answer | Evidence |
|----------|--------|----------|
| Does MaxPreps identify Pensacola as **Central** rather than Eastern? | **Mixed / inconsistent** | School-level `featuredGameData.teams[]` → **CDT** (Central). `stateData` → **EST** (same statewide Eastern default as Georgia). Naive `row[11]` + JSON-LD/`contestDateInGMT` → encoded with **Eastern (EDT)** offset. |
| Does `stateData` correctly represent Pensacola's timezone despite Florida spanning two zones? | **No** | `stateData` is **state-level EST** — same failure mode as Georgia Slice 08 §2. Pensacola (panhandle) is geographically Central; `stateData` does not reflect that. |
| Do featured-game participant TZ fields provide the correct Central zone? | **Yes** | Both participants: `timeZoneId: CDT`, `utcOffset: -21600`, `dstOffset: 3600` — geographically correct for Pensacola schools. |
| Does naive `row[11]` represent local **Central** wall time? | **No** (evidence supports Eastern offset) | All 10 JSON-LD-matched games: naive + EDT (−4 h) = JSON-LD UTC; naive is **not** Central wall time for these rows. |
| Additional TZ metadata missed in Centennial payload? | **`contestDateInGMT`** on `featuredGameData` | Present in Centennial fixture (`2026-09-04T23:30:00` for Alpharetta) but **not listed** in Slice 08 §2 inventory. Provides UTC/GMT for the **featured game only** — aligns with JSON-LD on both schools. No new per-contest TZ fields found on `contests[]` rows. |

#### Implications for Slice 08 fallback assumptions (evidence only — no implementation decision)

1. **State `stateData` fallback** — Confirmed weak for dual-timezone states: Florida panhandle schools get EST in `stateData` despite Central geography (parallel to Georgia all-EST).
2. **School TZ on `featuredGameData.teams[]`** — Can be **correct** (CDT for Pensacola) but **does not match** how naive `row[11]` is offset-encoded (Eastern) in this capture — do not assume naive wall time + school `timeZoneId` are internally consistent without cross-check.
3. **`contestDateInGMT`** — Featured-game UTC anchor; matches JSON-LD. Still **featured-only**; not on non-featured contest rows.
4. **Non-featured contests** — Still only naive `row[11]` with no per-row TZ metadata; Pensacola probe does not improve the partial-automation case from Slice 08 §5.

### 5. PRODUCT §14 — “30 minutes before kickoff”

| Contest set | `row[11]` | TZ metadata | Automation-ready? |
|-------------|-----------|-------------|-------------------|
| Featured (Alpharetta, row 3) | Yes | School `timeZoneId` + offsets on `featuredGameData` | **Yes** — for this one game in the fixture |
| Other scheduled rows (4–10) | Yes | None in `contests[]` | **Partial** — time known, offset **not** specified per contest; fallback candidate required |
| Finals (rows 1–2) | Yes | N/A for pre-kickoff | Past games |
| Deleted (row 0) | Yes | N/A | Exclude |

### 6. Cache and fixture pointers

| Artifact | Path |
|----------|------|
| Contest dates + featured TZ | `tests/fixtures/maxpreps/centennial/schedule-26-27.json` |
| JSON-LD UTC cross-check | `captures/private/www.maxpreps.com/a9fd9f8193667e1d.{raw,json}` (Slice 01) |
| Pensacola Central-Time probe (private) | `captures/private/www.maxpreps.com/4acd39e363b6d8ab.{raw,json}` |

---

## Slice 09 — Opponent identity and home/away

**Evidence mode:** Fixture analysis only — **zero live requests**. Source: `schedule-26-27.json` (Slice 06 participant map). Addresses PRODUCT.md §§6–7 (`opponent_*`, `home_away`, `venue`, `location`).

### 1. Opponent identification

For each `contests` row, participants live in `row[0]` (two `teams[*]` sub-arrays, width 32) plus extended copies `row[37]`/`row[38]`.

| Concept | Source | Evidence |
|---------|--------|----------|
| Configured school participant | `teams[*]` where `[1] === school_id` | **Proven** — `school_id` is contest participant `teamId` (Slice 03), not a team-season key |
| Opponent participant | The other `teams[*]` entry | **Proven** |
| `opponent_id` | Opponent `teams[*][1]` | **Proven** — opponent **school UUID** (e.g. Alpharetta `6b615161-…`) |
| `opponent_name` | Opponent `teams[*][14]` (`name`) | **Proven** — matches `featuredGameData.opponentTeam.name` on row 3 |
| `team_name` (context) | `teamContext.data.schoolName` | **Proven** — page-level constant |

Participant `[2]` is `sportSeasonId` for that side — generally the opponent’s own team-season when populated; do not confuse with `school_id`.

### 2. Home / away / neutral

Read `homeAwayType` from the **selected-school** participant (`teams[*][11]` where `[1] === school_id`):

| `homeAwayType` | Normalized `home_away` | Evidence |
|----------------|------------------------|----------|
| `0` | `home` | **Proven** — Johns Creek, Alpharetta rows |
| `1` | `away` | **Proven** — South Forsyth, deleted Riverwood row |
| `2` | `neutral` | **Inferred** — Dunwoody row 1; `[29]` says “neutral non-conference game” |

Do not infer home/away from `row[29]` prose or opponent name order.

### 3. Venue vs school location

| Field | Source | Meaning | Evidence |
|-------|--------|---------|----------|
| `venue` | `row[5]` (`location`) | Contest venue name | **Proven** — e.g. `"Centennial High School"`, `"Hughes Spalding Stadium - Marist School"`, empty string on some away games |
| `location` *(display)* | Participant `city` + `state` (`[15]`, `[16]`) | **School address metadata** | **Inferred** — describes the school, not necessarily where the game is played |

**Convention (from Slice 06):** Use `row[5]` for venue. Participant city/state is the **school’s** city/state — misleading for neutral sites (Dunwoody at Blessed Trinity) and away games with empty `row[5]`. Do not infer game location solely from home/away participant address.

### 4. Worked examples (Centennial football 26-27)

| Row | Opponent | `opponent_id` (prefix) | `home_away` | `venue` (`row[5]`) |
|-----|----------|------------------------|-------------|-------------------|
| 1 | Dunwoody | *(Dunwoody school UUID)* | `neutral` | `Blessed Trinity High School` |
| 2 | Johns Creek | *(Johns Creek UUID)* | `home` | `Centennial High School` |
| 4 | South Forsyth | *(South Forsyth UUID)* | `away` | `""` (empty) |
| 9 | Marist | *(Marist UUID)* | `away` | `Hughes Spalding Stadium - Marist School` |

### 5. Cache and fixture pointers

| Artifact | Path |
|----------|------|
| Contest participants | `tests/fixtures/maxpreps/centennial/schedule-26-27.json` — `contests`, `featuredGameData` |

---

## Slice 10 — Logos

**Evidence mode:** Fixture analysis only — **zero live requests**; no logo `HEAD` performed (URLs are already public in page payloads). Sources: `schedule-26-27.json`, `search-centennial.json`. Addresses PRODUCT.md §§6 (`team_logo`, `opponent_logo`) and §28 assumption 9.

### 1. URL sources

| Entity | Field | Example path pattern | Evidence |
|--------|-------|----------------------|----------|
| Configured school (team entity) | `teamContext.data.schoolMascotUrl` | `https://image.maxpreps.io/school-mascot/5/2/d/{school_uuid}.gif?version=…&width=1024&height=1024` | **Proven** |
| School search results | `initialSchoolResults[].mascotUrl` | Same CDN host + UUID-sharded path | **Proven** — `search-centennial.json` |
| Per-game opponent | Opponent participant `teams[*][20]` | Opponent school UUID in path | **Proven** — present on all 11 contest rows |
| Featured game (named) | `featuredGameData.teams[].mascotUrl` | Same pattern | **Proven** |
| Selected school in contest | Participant `teams[*][20]` where `[1] === school_id` | Centennial Knights GIF on every row | **Proven** |

CDN path embeds the **school UUID** (`/school-mascot/{n}/{n}/{n}/{uuid}.gif`). This matches `school_id` identity (Slice 03).

### 2. `version=` query parameter

Observed on every logo URL — e.g. `?version=638883757819641160`. Values differ by school and capture time.

**Treatment:** Cache-busting / content-version hint. Strip or ignore for identity and deduplication; pass through or normalize for display caching. Updating `version=` alone should not require re-identifying the school.

### 3. Home Assistant hotlink feasibility

| Question | Answer | Evidence tier |
|----------|--------|---------------|
| Are URLs absolute HTTPS on a MaxPreps-controlled host? | **Yes** — `image.maxpreps.io` | **Proven** |
| Are they present without authentication in public HTML payloads? | **Yes** | **Proven** |
| Will HA frontend / `picture` entities load them reliably? | **Uncertain** — referrer policy, hotlink protection, and CDN headers not tested (no `HEAD` in this slice) | **Uncertain** |
| Fallback if hotlink fails | Integration may proxy-cache locally later; out of scope for research slice | — |

**Practical guidance:** Expose `team_logo` / `opponent_logo` as the observed `mascotUrl` strings. Document for users that images are third-party hotlinks subject to CDN behavior. No binary download required for feasibility — URLs are stable in structure given `school_id`.

### 4. Cache and fixture pointers

| Artifact | Path |
|----------|------|
| Team + opponent logos on schedule | `tests/fixtures/maxpreps/centennial/schedule-26-27.json` |
| School search logos | `tests/fixtures/maxpreps/centennial/search-centennial.json` |

---

## Slice 11 — Records

**Evidence mode:** Fixture analysis only — **zero live requests**. Source: `schedule-26-27.json`. Standings **pages** not fetched (per traffic policy). Addresses PRODUCT.md §§6 (`team_record`, `record`), §16 (standings as bonus).

### 1. Season record — primary source

**Authoritative for current team-season record:** `teamContext.standingsData` (named object on the schedule page).

| Field | Path | Example (capture) | Evidence |
|-------|------|-------------------|----------|
| Overall W-L-T | `standingsData.overallStanding.overallWinLossTies` | `"2-0"` | **Proven** |
| Home / away / neutral splits | `…homeWinLossTies`, `awayWinLossTies`, `neutralWinLossTies` | `"1-0"`, `"0-0"`, `"1-0"` | **Proven** |
| Points for/against | `points`, `pointsAgainst` | `77`, `39` | **Proven** |
| Streak | `streak`, `streakResult` | `2`, `W` | **Proven** |
| Conference | `standingsData.leagueStanding.*` | `"AAAAA Region 6"`, `"0-0"`, `"1st"` | **Proven** |
| School year | `standingsData.year` | `"26-27"` | **Proven** |

Map to PRODUCT `team_record` / `record` attribute (e.g. `"2-0"`). **`lastYearStandingsData`** also exists on the page for prior-year display — not required for current-season entity.

### 2. What is *not* on each contest row

`contests[]` rows do **not** carry season record fields. Per-game record strings are **not** available schedule-wide from columnar contests alone.

### 3. Featured-game-only snapshot — `featuredGameData.teamsCalculated`

| Field | Scope | Example | Evidence |
|-------|-------|---------|----------|
| `teamsCalculated[].standings` | **Featured game only** (pre-game Alpharetta contest) | Centennial `"2-0"`, Alpharetta `"0-2"` | **Proven** |
| `currentTeam.standings` / `opponentTeam.standings` | Same featured game | Same values | **Proven** |

These are **point-in-time** standings as of the featured/next game — useful for a Team Tracker card, redundant with `teamContext.standingsData` for the configured school. Do not use for historical games or non-featured rows.

### 4. Standings pages

`teamContext` menu links expose `…/football/standings/` URLs. **`tda.hasStandings: false`** on this capture despite `standingsData` being populated inline — standings arrive in `__NEXT_DATA__` without a separate fetch in this slice. Do not add standings-page traffic for v1 record display.

### 5. Cache and fixture pointers

| Artifact | Path |
|----------|------|
| Season + league record | `tests/fixtures/maxpreps/centennial/schedule-26-27.json` — `teamContext.standingsData` |

---

## Slice 12 — Seasons

**Evidence mode:** Fixture analysis only — **zero live requests**. Restates and extends Slice 05 for PRODUCT.md §27.H (multiple seasons) and §3.2 config flow. Sources: `schedule-26-27.json`, `sport-seasons-26-27.json`.

### 1. Identity vs fetch path (conventions)

| Concept | Key | Role | Rotates yearly? |
|---------|-----|------|-----------------|
| Team-season **identity** | `sport_season_id` (`sportSeasonId` / `ssid`) | Primary key for which season’s contests to load | **Yes** — new UUID each school year |
| Program metadata | `all_season_id` (`allSeasonId`) | Optional correlation across years (Slice 05) | **No** for a given program |
| Public **fetch path** | `canonical_url` | Observed HTTP path for team home / schedule HTML | Current year omits `YY-YY`; prior years embed it |
| School identity | `school_id` | Constant across all seasons | **No** |

**Do not** call `sport_season_id` the fetch key in documentation — the observed mechanism is `GET {canonical_url}schedule/` (which returns `__NEXT_DATA__` containing `query.ssid`). The UUID validates the intended team-season.

### 2. Current season discovery

| Source | Scope | Current year? | Evidence |
|--------|-------|---------------|----------|
| `schoolContext.sportSeasons[]` | All sports at school | **Yes** — all 47 Centennial rows are `year: "26-27"` | **Proven** — `sport-seasons-26-27.json` |
| `teamContext.mostRecentPublicGenderSportSeasonLevel` | One sport on team page | Points at 26-27 varsity football | **Proven** |
| Schedule `query.ssid` | Active fetch | `2286cd80-…` matches varsity football `sportSeasonId` | **Proven** |

**Default product behavior:** Track the **current** school-year team-season from `sportSeasons[]` at config time; re-fetch school home on rollover to resolve the new `sport_season_id` for the same `(sport, gender, level[, season])` program (Slice 05 §4).

### 3. Historical seasons

| Source | Scope | Evidence |
|--------|-------|----------|
| `teamContext.teamSeasonPickerData[]` | **One sport per team page** — football shows 55 rows (`04-05`…`26-27`) | **Proven** |
| `schoolContext.sportSeasons[]` | Current year only | **Proven** — no prior-year rows |

**Prior-season URL pattern** (football picker):

- Current: `…/football/schedule/` (no year segment)
- Prior: `…/football/25-26/schedule/` (year embedded)

Legacy rewrite always includes `ssid=<sportSeasonId>` regardless of path year segment.

### 4. Empty / idle preseason

All 47 `sportSeasons[]` rows have `isPublished: true`. An **empty preseason schedule with no published team-season row** was **not observed** — do not fetch idle sport URLs speculatively.

### 5. Contest-level season key

`contests[][14]` carries `sportSeasonId` for the contest’s team-season context — matches the page `query.ssid` for normal schedule games. `allSeasonId` does **not** appear on contest rows (Slice 05).

### 6. Cache and fixture pointers

| Artifact | Path |
|----------|------|
| Cross-sport current seasons | `tests/fixtures/maxpreps/centennial/sport-seasons-26-27.json` |
| Football picker + schedule | `tests/fixtures/maxpreps/centennial/schedule-26-27.json` |

---

## Slice 13 — Cancelled / postponed

**Evidence mode:** Fixture analysis only — **zero live requests**. Source: `schedule-26-27.json`. No hunting other teams or sports (per scope). Addresses PRODUCT.md §13 (`postponed` / `cancelled` status), §19 (error handling), §27.G (schedule changes).

### 1. Observed non-final states

| Condition | `contestState` | `row[28]` message | Row | Evidence |
|-----------|----------------|-----------------|-----|----------|
| **Deleted / hidden** | `1` | `"ContestState is Deleted."` | 0 — Riverwood scrimmage `2026-08-07` | **Proven** |
| **Scheduled / pregame** | `2` | `"ContestState is Pregame."` | 3–10 | **Proven** |
| **Final** | `4` | `""` (empty) | 1–2 | **Inferred** |

### 2. Deleted contests — client behavior

Row 0 decodes fully but lacks `row[18]` `canonicalUrl`. Integration should:

- **Filter** from user-facing schedule and “next game” selection (Slice 07)
- Optionally retain for diagnostics or “schedule changed” detection
- Map to normalized `status: deleted` if kept in internal model

This is **not** the same as postponed or cancelled — MaxPreps labels it **Deleted** explicitly.

### 3. Postponed / cancelled — gap

| Status | Observed? | Evidence |
|--------|-----------|----------|
| `postponed` | **No** | No `contestState` sample; no `"Postponed"` in `row[28]` across 11 rows |
| `cancelled` | **No** | No sample; distinct from `contestState` 1 (deleted) in this fixture |
| `forfeit` | **No** on contests | `isForfeit: false` on `featuredGameData.teams[]` only |

**Unknown enum handling:** Any future `contestState` → `status: unknown` + `row[28]` message (Slice 07). Do not map `contestState` 1 to “cancelled” — MaxPreps uses **Deleted** wording.

### 4. Schedule-change signals (PRODUCT §27.G)

This fixture is a single point in time. **Reschedule / opponent-change detection** would require diffing `contestId` + `row[11]` across refreshes — not demonstrated here. Deleted row 0 proves MaxPreps can remove contests from the public schedule while leaving them decodable in `contests[]`.

### 5. Cache and fixture pointers

| Artifact | Path |
|----------|------|
| Deleted + scheduled examples | `tests/fixtures/maxpreps/centennial/schedule-26-27.json` — `contests[0]`, `contests[3]` |

## Slice 14 — Head-to-head sports differences

**Evidence mode:** Two live schedule fetches (volleyball + basketball) after volleyball matched football; one mistaken softball path logged as 404 (path-construction lesson, not refetched). Sources: live captures above; committed fixture `volleyball-schedule-26-27.json`; football baseline `schedule-26-27.json` (Slice 06).

**Question:** Is the football decode strategy sport-specific, or does the same `contests` + `featuredGameData` columnar parser apply to other head-to-head varsity schedules?

**Answer:** **Same parser likely** — not sport-specific. Volleyball and basketball schedule pages use the identical `pageProps` shape, contest row arity (41), participant width (32), and `featuredGameData` anchor pattern validated on football in Slice 06. Differences are cosmetic (alias strings, URL slug `match` vs `game`) or sparse-schedule volume — not structural breaks.

### 1. What was fetched

| Sport | `sportSeasons[]` row | Fetch URL | Status | Cache / fixture |
|-------|----------------------|-----------|--------|-----------------|
| **Girls Varsity Volleyball** (primary) | `canonicalUrl` `…/volleyball/`, `ssid` `9f2e0dd1-…` | `https://www.maxpreps.com/ga/roswell/centennial-knights/volleyball/schedule/` | 200 | Private `c1a5eb088efb16a4.*`; fixture `tests/fixtures/maxpreps/centennial/volleyball-schedule-26-27.json` |
| **Girls Varsity Basketball** (confirmatory) | `canonicalUrl` `…/basketball/girls/`, `ssid` `e3e91f97-…` | `https://www.maxpreps.com/ga/roswell/centennial-knights/basketball/girls/schedule/` | 200 | Private `a89b0d585a1ebd0c.*` (not committed — sparse 6-game pre-season schedule) |
| Softball (mistaken path) | canonical is `…/softball/fall/` | `…/softball/schedule/` (hand-built, **not** from `canonicalUrl`) | 404 | Private `746fbcd69d15c1b6.*` — reinforces Slice 04/05 rule: append `schedule/` to payload `canonicalUrl`, never guess slug segments |

All fetches: `scripts/explore/capture.py`, ≥2s delay, `User-Agent: hacs-highschoolscores-explore/0.1`, no cookies. `buildId` at capture: `d8af3013-00483cf1` (volleyball/basketball) vs `92628a14-f7050eaf` (football fixture) — deploy rotated; shape unchanged.

### 2. Check results vs football (Slice 06)

| # | Check | Volleyball | Basketball | Verdict |
|---|-------|------------|------------|---------|
| 1 | `pageProps.contests` exists, same nesting/usable arity | **Yes** — 32 rows, arity **41**; `row[0]` = two participants width **32** | **Yes** — 6 rows, arity **41**, participants width **32** | **Same** |
| 2 | Named `featuredGameData` present and usable as index anchor | **Yes** — featured `contestId` `554d9edd-…` matches `contests[18]`; `row[1]`, `[5]`, `[11]`, `[15]` align to named `contestId`, `location`, `date`, `contestState` | **Yes** — featured matches `contests[0]`; same index alignment | **Same** |
| 3 | Participant `teamId` is school UUID | **Yes** — Centennial `52dea55b-…` at `[1]` on school side; opponents are distinct school UUIDs (e.g. North Clayton `b8d5f8c6-…`) | **Yes** — same pattern | **Same** |
| 4 | PRODUCT §7 game object via evidence tiers | **Yes** — finals (`contestState` 4, `hasResult: true`): `row[37]`/`[38]` scores/results (e.g. `L`/`1` vs `W`/`2`); scheduled rows: `contestState` 2 + `row[28]` `"Pregame."`; deleted: `contestState` 1 (2 rows) | **Yes** — all 6 rows scheduled (`contestState` 2); no finals in capture | **Same approach** |
| 5 | Sport-specific contest fields breaking generic model | **No structural breaks** — see §3 | **No structural breaks** | **Generic model holds** |

**`featuredGameData`:** **Present** on both non-football captures. Missing it would have been a real finding; it is not missing.

**`contests` sameness:** Row arity 41 and participant arity 32 match football exactly. Non-null index sets on scheduled rows match football (e.g. volleyball scheduled row: indices `[0,1,2,4,11,12,13,14,15,17,18,21,24,27,29,35,37,38]` — same pattern as football Slice 06).

### 3. Differences vs football (non-breaking)

| Area | Football (Slice 06) | Volleyball / basketball (Slice 14) | Impact on parser |
|------|---------------------|-------------------------------------|------------------|
| `contestAlias` (`row[21]`) | `"Game"` | Volleyball: `"Match"`; basketball: `"Game"` | Display only — same index |
| Game page URL (`row[18]`) | `…/ga/football/game/…` | Volleyball: `…/ga/volleyball/match/…` | Absolute URL — no path template needed |
| Schedule volume | 11 contests | Volleyball 32 (in-season); basketball 6 (pre-season sparse) | Empty/sparse OK — shape validated |
| `contestState` samples | 1, 2, 4 | Volleyball: 1 (2), 2 (13), 4 (17); basketball: 2 only | Same enum usage as Slice 07 |
| Venue `row[5]` | School name or empty | Volleyball featured: `"Senior Night"` (event label, not school city) | Confirms Slice 09 — use `row[5]`, not participant city |
| Opponent `sportSeasonId` at participant `[2]` | Opponent’s own team-season UUID | **Same** on most rows; occasional duplicate of configured school’s `ssid` on featured opponent named object — prefer positional participant `[2]` per side | No new field; same index |
| `buildId` | `92628a14-…` | `d8af3013-…` | Page URL fetch still works — do not key on `buildId` |

No new top-level `pageProps` keys. `featuredGameData` key set is identical to football (no volleyball-only or basketball-only named keys). `tournaments` empty on volleyball as on football.

### 4. Same parser likely — evidence summary

A single columnar decoder keyed off `featuredGameData` for index validation can serve **football, volleyball, and basketball** schedule pages observed here:

1. **Transport:** `GET {canonical_url}schedule/` → `__NEXT_DATA__.props.pageProps` (Slice 01 pattern).
2. **Anchor:** `featuredGameData.contestId` → locate row; verify `row[1]`, `[5]`, `[11]`, `[15]`, `[18]` against named fields.
3. **Participants:** Width-32 arrays; `school_id` at `[1]`; `home_away` at `[11]`; opponent at other `row[0]` entry.
4. **Scores/status:** `row[15]`, `row[4]`, `row[28]` for status; `row[37]`/`[38]` for team-oriented finals.
5. **Venue:** `row[5]` only.

Sport-specific logic is **not** required for decode — only display aliases and URL slug segments differ.

### 5. Cache and fixture pointers

| Artifact | Path |
|----------|------|
| Girls Varsity Volleyball schedule (committed) | `tests/fixtures/maxpreps/centennial/volleyball-schedule-26-27.json` |
| Football schedule baseline | `tests/fixtures/maxpreps/centennial/schedule-26-27.json` |
| Volleyball private raw | `captures/private/www.maxpreps.com/c1a5eb088efb16a4.{raw,json}` |
| Basketball private raw | `captures/private/www.maxpreps.com/a89b0d585a1ebd0c.{raw,json}` |

**Stopped after Slice 14.** Slice 15 follows (individual/meet sports). No production client.

---

## Slice 15 — Individual and meet-based sports

**Evidence mode:** Two live schedule fetches (tennis + track) per `sportSeasons[]` `canonicalUrl` + `schedule/` (Slice 04/05 convention). Sources: live captures above; committed fixtures `tennis-schedule-26-27.json`, `track-field-girls-schedule-26-27.json`. Football/volleyball/basketball baseline from Slices 06 and 14.

**Question:** Do individual (tennis) and meet-based (track) varsity schedules use the same `pageProps.contests` + `featuredGameData` model as head-to-head sports, and can PRODUCT §7 fields be filled?

**Answer:** **Cannot validate the generic pipeline on these captures.** Both sports return **legacy ASPX HTML** (not Next.js `__NEXT_DATA__`), with **empty schedules** (“No Schedule Available”). No `contests[]`, no `featuredGameData`, no contest rows to decode. Transport differs from football/volleyball/basketball (Slice 14). Verdict per sport: **Defer** — do not exclude, but do not assume the Slice 06/14 parser applies until a populated capture confirms payload shape.

### 1. What was fetched

| Sport | `sportSeasons[]` row | Fetch URL | Status | Cache / fixture |
|-------|----------------------|-----------|--------|-----------------|
| **Boys Varsity Tennis** (individual) | `canonicalUrl` `…/tennis/`, `ssid` `7a9c6e6c-…` | `https://www.maxpreps.com/ga/roswell/centennial-knights/tennis/schedule/` | 200 | Private `aa6eaaf00a2767ec.*`; fixture `tests/fixtures/maxpreps/centennial/tennis-schedule-26-27.json` |
| **Girls Varsity Track & Field** (meet-based) | `canonicalUrl` `…/track-field/girls/`, `ssid` `6f5eefe6-…` | `https://www.maxpreps.com/ga/roswell/centennial-knights/track-field/girls/schedule/` | 200 | Private `55e4248e9d63ee2a.*`; fixture `tests/fixtures/maxpreps/centennial/track-field-girls-schedule-26-27.json` |

Fetch policy: `scripts/explore/capture.py`, ≥2s delay, `User-Agent: hacs-highschoolscores-explore/0.1`, no cookies. No 429/403/challenge. URLs taken from fixture `canonicalUrl` — not hand-built.

### 2. Payload model — same as Slice 06/14?

| Check | Boys Varsity Tennis | Girls Varsity Track & Field | Head-to-head baseline (Slice 14) |
|-------|---------------------|----------------------------|----------------------------------|
| `__NEXT_DATA__` present | **No** | **No** | **Yes** (`page: /team/schedule`) |
| `pageProps.contests` | **Absent** | **Absent** | Present; arity **41** |
| `pageProps.featuredGameData` | **Absent** | **Absent** | Present; named anchor |
| `pageProps.teamContext` | **Absent** | **Absent** | Present |
| Response routing | Legacy `/local/team/schedule.aspx` (`x-mp-caching-rules: File system rule:/local/team/`) | Same | Next.js `/team/schedule` (`x-middleware-rewrite: /team/schedule?…`) |
| Page size | ~140 KB | ~139 KB | 230–410 KB |
| JS stack | jQuery 2.2 + Prototype (`asset.maxpreps.io/includes/`) | Same | Next.js chunks (`asset.maxpreps.io/_next/static/`) |
| Visible schedule rows | **0** — “No Schedule Available” | **0** — “No Schedule Available” | Volleyball 32; basketball 6 (sparse) |

**Model verdict:** **Different transport**, not merely a different contest shape. These pages are **not** the Next.js schedule route validated in Slices 01, 06, and 14. Whether populated tennis/track schedules would (a) migrate to Next.js with `contests[]`, (b) remain legacy with a different embedded structure, or (c) require client-side loading is **unknown** — this slice had no contest payload to inspect.

### 3. Empty schedule state (still useful)

Both pages render an explicit empty state:

- Message: **“No Schedule Available”**
- Coach prompt: login to admin and enter schedule (`source=desktop_team_missingschedule` on create-account link)
- School address chrome present (9310 Scott Rd, Roswell, GA)
- Identifiers recoverable from page: `school_id` `52dea55b-…`, `ssid`, `allSeasonId`, `gendersport` (`boys,tennis` / `girls,trackfield`), `season=spring`
- Legacy rewrite URL in `meta encoded-url` (base64): `/local/team/schedule.aspx?gendersport=…&schoolid=…&ssid=…`

Spring 26-27 preseason — schedules not yet entered at capture time. **Sparse/empty head-to-head schedules still expose `contests[]`** (Slice 14: basketball 6 rows on Next.js). Tennis/track emptiness does **not** by itself explain the legacy transport — the structural break is the absence of `__NEXT_DATA__`, not row count.

### 4. PRODUCT §7 mapping — can fields be filled?

Target game object (Slice 06): `id`, `date`, `opponent`, `home_away`, `scores`, `result`, `venue`, `url`.

| Field | Tennis (this capture) | Track & Field (this capture) | Notes |
|-------|----------------------|------------------------------|-------|
| `id` | **N/A** — no contests | **N/A** — no contests | — |
| `date` | **N/A** | **N/A** | — |
| `opponent` | **Unvalidated** | **Likely breaks head-to-head model** if meets are multi-school | PRODUCT §8 lists meets as a potential exception; no rows to test |
| `home_away` | **Unvalidated** | **Likely breaks** for invitational/meet events | — |
| `scores` / `result` | **Unvalidated** | **Unvalidated** — team meet scores vs individual event results unknown | — |
| `venue` | **Unvalidated** | **Unvalidated** | — |
| `url` | **Unvalidated** | **Unvalidated** | — |
| Participant `teamId` = `school_id`? | **Unvalidated** | **Unvalidated** | Slice 03–05 convention not testable without participant arrays |

**Mapping verdict:** **No evidence** either way for populated seasons. Meet-based track would plausibly need multi-opponent or event-list semantics (PRODUCT §8), but this capture provides **zero contest rows** — cannot confirm or falsify.

### 5. Transport comparison (evidence)

| Signal | Next.js head-to-head (football / volleyball / basketball) | Tennis / track (this slice) |
|--------|----------------------------------------------------------|----------------------------|
| `x-middleware-rewrite` | `/team/schedule?url=%2Flocal%2Fteam%2Fschedule.aspx%3F…` | **Absent** |
| `x-mp-caching-rules` | `Pattern match: /team/schedule{/*}?` | `File system rule:/local/team/` + `schedule.aspx` path |
| `__NEXT_DATA__.page` | `/team/schedule` | **Not present** |
| `pagetype` | Via Next route | `teamschedule` (legacy) |
| Machine-readable schedule | `pageProps.contests` | **None observed** |

Slice 01’s “`__NEXT_DATA__` present on all three pages” applied to homepage, team home, and **football** schedule only. Tennis and track schedule URLs at Centennial **do not** follow that pattern at capture time.

### 6. Per-sport verdict

| Sport | Type | Verdict | Rationale |
|-------|------|---------|-----------|
| **Boys Varsity Tennis** | Individual / dual-match sport | **Defer** | Legacy ASPX transport; no `contests[]` or `featuredGameData`; empty schedule. Cannot apply or reject Slice 06/14 parser. Dual-match tennis *might* fit head-to-head semantics if Next.js `contests[]` appears when populated — **unproven**. |
| **Girls Varsity Track & Field** | Meet-based | **Defer** | Same transport break and empty schedule. Meet/invitational semantics (multi-opponent, no single opponent, team point totals) are plausible PRODUCT §8 exceptions — **unvalidated**. |

**Not recommended now:**

- **Keep on generic pipeline** — no `contests[]` payload; transport differs from validated sports.
- **Special-case (implement now)** — insufficient data to design a parser; would be guessing at legacy HTML scrape or undisclosed API.

**Follow-up (out of scope for Slice 15):** A school with **populated** tennis and/or track schedules on the **current** MaxPreps stack would answer whether (1) Next.js migration occurs when data exists, (2) legacy pages embed a decodable contest list, or (3) a separate fetch is required. Do not infer from this slice alone.

### 7. Cache and fixture pointers

| Artifact | Path |
|----------|------|
| Boys Varsity Tennis schedule (legacy empty) | `tests/fixtures/maxpreps/centennial/tennis-schedule-26-27.json` |
| Girls Varsity Track & Field schedule (legacy empty) | `tests/fixtures/maxpreps/centennial/track-field-girls-schedule-26-27.json` |
| Tennis private raw | `captures/private/www.maxpreps.com/aa6eaaf00a2767ec.{raw,json}` |
| Track private raw | `captures/private/www.maxpreps.com/55e4248e9d63ee2a.{raw,json}` |
| Head-to-head baseline (Slice 14) | `tests/fixtures/maxpreps/centennial/volleyball-schedule-26-27.json` |

**Stopped after Slice 15.** No Slice 16. No production client.

---

## Slice 16 — Additional Georgia public schools (Bainbridge; Pike County)

**Evidence mode:** Six live requests (2 search + 2 school home + 2 football schedule) via `scripts/explore/capture.py`, ≥2s between requests, no cookies. No 429/403/challenge. Football schedule URLs taken from `sportSeasons[]` `canonicalUrl` + `schedule/` (Slice 04/05 convention). Tennis/track not fetched (Slice 15 scope).

**Question:** Is the Centennial model (search → `school_id` → `sportSeasons[]` → Next.js `contests` + `featuredGameData`) specific to one school, or does it generalize to other Georgia public schools?

**Answer:** **Centennial model survived** — both validation schools follow the same discovery, enumeration, and schedule-decode pipeline. Minor revisions: `sportSeasonId` is **not globally unique** (same UUID for Boys Varsity Football 26-27 across all three GA schools examined); Pike County `sportSeasons[]` can include **prior-year rows** alongside current-year rows.

### 1. Search disambiguation

| School | Query (`q` / `q2`) | Results | Target row | `schoolId` | `canonicalUrl` |
|--------|-------------------|---------|------------|------------|----------------|
| **Bainbridge High School** | `bainbridge` / `Bainbridge` | 3 schools | Bainbridge, **Bainbridge, GA**, 39819, **Bearcats** | `cc2897b8-106d-45b3-a9cf-5e2aca708668` | `https://www.maxpreps.com/ga/bainbridge/bainbridge-bearcats/` |
| **Pike County High School** | `pike county` / `Pike County` | 3 schools | Pike County, **Zebulon, GA**, 30295, **Pirates** | `84dd878e-671b-40d4-83de-e73ab301f92e` | `https://www.maxpreps.com/ga/zebulon/pike-county-pirates/` |

**Disambiguation pattern matches Slice 02:** Short school name alone returns results; city/state/mascot distinguish the GA target from same-name or similar-name schools in other states.

| Query | Other results (not selected) |
|-------|------------------------------|
| `Bainbridge` | Bainbridge, Bainbridge Island, **WA** (Spartans); Bainbridge-Guilford, Bainbridge, **NY** (Bobcats) |
| `Pike County` | Pike County, Brundidge, **AL** (Bulldogs); Pike County Central, Pikeville, **KY** (Hawks) |

No city or “High School” qualifier appended (per Slice 02 — those return 0 results).

### 2. School home — `school_id` and `sportSeasons[]`

| Check | Bainbridge | Pike County | Centennial (baseline) |
|-------|------------|-------------|---------------------|
| `__NEXT_DATA__` present | **Yes** (`page: /school`) | **Yes** | Yes |
| `schoolContext.schoolId` | `cc2897b8-…` (school UUID) | `84dd878e-…` (school UUID) | `52dea55b-…` |
| Matches search `schoolId` | **Yes** | **Yes** | Yes |
| `sportSeasons[]` present | **Yes** — 39 rows | **Yes** — 48 rows | Yes — 47 rows |
| Current-year rows only? | **Yes** — all `26-27` | **No** — 46 × `26-27` + **2 × `11-12`** (Boys/Girls Varsity Soccer Winter) | Yes — all `26-27` |
| `schoolId` constant on all rows | **Yes** — school UUID, not team key | **Yes** | Yes |
| One row per `sportSeasonId` | **Yes** (39 unique) | **Yes** (48 unique) | Yes (47 unique) |
| Distinct sports (26-27) | 12 | 15 | 14 |
| `buildId` | `c4253631-315fb3c5` | `c4253631-315fb3c5` | `017e4b0f-3e4349b7` (older capture) |

**Enumeration verdict:** Same transport and field shape as Slice 04. Smaller schools list fewer sports (Bainbridge 39 rows / 12 sports vs Centennial 47 / 14). Pike County adds Flag Football, Gymnastics, and Lacrosse not present at Bainbridge; Bainbridge lacks those three.

**Pike County historical rows:** Two `11-12` soccer rows remain in `sportSeasons[]` with `isPublished: true` and year-embedded URLs (`…/soccer/winter/11-12/schedule/`). Config Step 2 must not assume every `sportSeasons[]` row belongs to the current school year. Determine the active/latest school-year cohort from the payload and prefer published rows from that cohort; retain older rows only for explicit historical-season selection.

### 3. Football schedule — transport and decode model

Both schools: Boys Varsity Football from `sportSeasons[]` → `{canonicalUrl}schedule/`.

| Check | Bainbridge | Pike County | Centennial |
|-------|------------|-------------|------------|
| Fetch URL | `…/bainbridge-bearcats/football/schedule/` | `…/pike-county-pirates/football/schedule/` | `…/centennial-knights/football/schedule/` |
| Status | 200 | 200 | 200 |
| Transport | **Next.js** (`page: /team/schedule`) | **Next.js** | Next.js |
| Legacy ASPX? | **No** | **No** | No |
| `x-middleware-rewrite` | Present | Present | Present |
| `pageProps.contests` | **Yes** — 11 rows, arity **41** | **Yes** — 11 rows, arity **41** | Yes — 11 rows, arity 41 |
| Participant width | **32** per side (2 sides) | **32** | 32 |
| `featuredGameData` | **Yes** — named anchor | **Yes** | Yes |
| Featured ↔ contests alignment | **Yes** — `contestId` matches row | **Yes** | Yes |
| `teamContext.data.teamId` === `school_id` | **Yes** (`cc2897b8-…`) | **Yes** (`84dd878e-…`) | Yes |
| Contest participant `teamId` === `school_id` | **Yes** on school side | **Yes** | Yes |
| `query.ssid` === `sportSeasons` row `sportSeasonId` | **Yes** | **Yes** | Yes |
| `sportSeasonId` value (26-27 varsity football) | `2286cd80-c46d-4739-8dd1-92a67ca8daa7` | `2286cd80-c46d-4739-8dd1-92a67ca8daa7` | `2286cd80-c46d-4739-8dd1-92a67ca8daa7` |

**Schedule transport verdict:** Identical Next.js pipeline to Centennial football (Slice 06) — not legacy ASPX (contrast Slice 15 tennis/track at Centennial only).

**Contest state samples (football):** Both schools: `contestState` 1 (deleted, 1 row), 2 (pregame, 8 rows), 4 (final, 2 rows) — same enum usage as Slice 07.

### 4. Differences vs Centennial (non-breaking)

| Area | Bainbridge | Pike County | Impact |
|------|------------|-------------|--------|
| School size / sport count | 39 team-season rows, 12 sports | 46 current + 2 historical rows, 15 sports | Fewer config choices at smaller schools; filter by year |
| `sportSeasons[]` year scope | Current year only | Current + 2 prior-year soccer rows | Step 2 must filter `year` or prefer most recent per program |
| `sportSeasonId` global uniqueness | Same football `ssid` as Centennial and Pike County | Same | **`sportSeasonId` is not globally unique** — always pair with `school_id` (or `canonical_url`) for identity; fetch still works via school-scoped URL |
| Path grammar | Gender/season/level in path (e.g. `soccer/girls/spring/`, `golf/spring/`) — 30/39 rows | Same pattern — 37/46 current rows | Reinforces Slice 04: use payload `canonicalUrl`, never reconstruct |
| `buildId` | `c4253631-315fb3c5` (same deploy as Pike County) | Same | Deploy rotated since Centennial captures; shape unchanged |
| Zip in search | `39819` (no +4) | `30295` (no +4) | Display only |

No new top-level `pageProps` keys. No structural break in `contests` columnar encoding or `featuredGameData` anchor pattern.

### 5. Convention revision — `sportSeasonId` scope

Slices 03–05 treated `sportSeasonId` as the team-season primary key. Slice 16 proves it is **primary only in combination with `school_id`**:

- Boys Varsity Football 26-27 `sportSeasonId` `2286cd80-c46d-4739-8dd1-92a67ca8daa7` is **identical** at Centennial, Bainbridge, and Pike County.
- `query.schoolid` on the schedule page disambiguates which school’s contests are returned.
- **Client convention (addendum):** Persist `(school_id, sport_season_id)` as the composite team-season identity. Never look up a schedule by `sportSeasonId` alone across schools. `canonical_url` from `sportSeasons[]` remains the safe fetch path.

### 6. Verdict

| Aspect | Verdict |
|--------|---------|
| Search → `school_id` + `canonicalUrl` | **Survived** |
| School home → `sportSeasons[]` enumeration | **Survived** (with year-filter caveat for Pike County) |
| Schedule → Next.js `contests` + `featuredGameData` | **Survived** for varsity football |
| `teamId` === `school_id` on team pages | **Survived** |
| Slice 06/14 columnar parser | **Likely applies unchanged** (arity 41, participant width 32, featured anchor) |
| Overall Centennial model | **Survived with minor revision** (`sportSeasonId` requires `school_id` pairing; `sportSeasons[]` may include non-current years) |

### 7. Cache and fixture pointers

| Artifact | Path |
|----------|------|
| Bainbridge search | `tests/fixtures/maxpreps/bainbridge/search-bainbridge.json` |
| Bainbridge `sportSeasons` | `tests/fixtures/maxpreps/bainbridge/sport-seasons-26-27.json` |
| Bainbridge football schedule | `tests/fixtures/maxpreps/bainbridge/schedule-26-27.json` |
| Pike County search | `tests/fixtures/maxpreps/pike-county/search-pike-county.json` |
| Pike County `sportSeasons` (incl. 11-12 rows) | `tests/fixtures/maxpreps/pike-county/sport-seasons-26-27.json` |
| Pike County football schedule | `tests/fixtures/maxpreps/pike-county/schedule-26-27.json` |
| Bainbridge search private | `captures/private/www.maxpreps.com/67d0801fc17fa39f.{raw,json}` |
| Pike County search private | `captures/private/www.maxpreps.com/00fbada789999b45.{raw,json}` |
| Bainbridge school home private | `captures/private/www.maxpreps.com/181ca9858af0f153.{raw,json}` |
| Pike County school home private | `captures/private/www.maxpreps.com/690de41094ee2669.{raw,json}` |
| Bainbridge football schedule private | `captures/private/www.maxpreps.com/225e0d52acf7718f.{raw,json}` |
| Pike County football schedule private | `captures/private/www.maxpreps.com/acceee095433f433.{raw,json}` |

**Stopped after Slice 16.** Six live requests. No Slice 16b (Saint Edward). No production client. **Pause for human review.**

---

## Slice 16b — Private out-of-state sanity check (Saint Edward High School, Lakewood, OH)

**Evidence mode:** Four live requests (2 search + 1 school home + 1 football schedule) via `scripts/explore/capture.py`, ≥2s between requests, no cookies. No 429/403/challenge. Football schedule URL from `sportSeasons[]` `canonicalUrl` + `schedule/` (Slice 04/05 convention).

**Question:** After three Georgia public schools (Slice 16), does the Centennial model survive a **private, all-boys** school in another state?

**Answer:** **Centennial model survived with minor revision** — same discovery → enumeration → Next.js schedule-decode pipeline. Revision: search must use abbreviated **`St. Edward`** (not `Saint Edward`, which returns 0 schools). No Georgia `St. Edward` appeared in results; Lakewood OH disambiguation matched the Slice 02/16 city/state/mascot pattern.

### 1. Search disambiguation

| Attempt | Query (`q` / `q2`) | School results | Outcome |
|---------|-------------------|----------------|---------|
| 1 | `saint edward` / `Saint Edward` | **0** (`initialSchoolResults: null`) | Retry required |
| 2 | `st. edward` / `St. Edward` | **5** schools | Target found |

**Target row (attempt 2):**

| Field | Value |
|-------|-------|
| `name` | St. Edward |
| `city` | **Lakewood** |
| `state` | **OH** |
| `zip` | `44107-4602` |
| `mascot` | **Eagles** |
| `schoolId` | `2f510683-5829-4d1e-9a93-703a82f12a58` |
| `canonicalUrl` | `https://www.maxpreps.com/oh/lakewood/st-edward-eagles/` |

**Other results (not selected):**

| Name | City | State | Mascot |
|------|------|-------|--------|
| St. Edward | Elgin | IL | Green Wave |
| St. Edward's | Vero Beach | FL | Pirates |
| St. Edward | St. Edward | NE | Beavers |
| Newman Grove/St. Edward | Newman Grove | NE | Panthers |

No Georgia school in the result set. Disambiguation: **Lakewood, OH, Eagles** — not city-qualified search, same as Bainbridge/Pike County (short name + scan city/state/mascot).

**Search revision vs Slice 02/16:** `Saint Edward` (spelled out) is a **dead query** for this school; MaxPreps indexes it as `St. Edward` (`schoolInfo.searchName`: `" st edward"`). Client search should retry abbreviated `St.` when a spelled-out saint name returns 0 schools. Did **not** append `High School` (Slice 02 — returns 0).

### 2. School home — `school_id`, private/boys-only, `sportSeasons[]`

| Check | St. Edward (OH) | GA baseline (Slice 16) |
|-------|-----------------|------------------------|
| `__NEXT_DATA__` present | **Yes** (`page: /school`) | Yes |
| `schoolContext.schoolId` | `2f510683-…` | school UUID |
| Matches search `schoolId` | **Yes** | Yes |
| `schoolInfo.type` | **`Private`** | Public (GA schools) |
| `schoolInfo.gender` | **`Boys`** (all-boys school) | Coed (typical public) |
| `sportSeasons[]` present | **Yes** — 32 rows | Yes |
| Current-year rows only? | **Yes** — all `26-27` | Bainbridge yes; Pike County had 2 × `11-12` leftovers |
| `schoolId` constant on all rows | **Yes** — school UUID | Yes |
| One row per `sportSeasonId` | **Yes** (32 unique) | Yes |
| Distinct sports (26-27) | **14** (13 boys + 1 girls rugby) | 12–15 at GA schools |
| `buildId` | `c4253631-315fb3c5` (same deploy as Slice 16 GA) | Same |

**All-boys / gender notes:**

- `schoolInfo.gender` = `Boys`; **31/32** `sportSeasons[]` rows are `gender: Boys`.
- **One exception:** Girls Varsity Rugby (`…/rugby/girls/`) — co-ed sport at an all-boys school; same pattern risk as any single cross-gender row.
- Boys sports with **gender in path** (Slice 04 grammar): Boys Volleyball at `…/volleyball/boys/` (Varsity, JV, Freshman) — 3 rows. Girls Rugby at `…/rugby/girls/`. Other boys sports use default paths (e.g. `…/football/`, `…/basketball/`).

**Levels:** Varsity 14, JV 10, Freshman 8 — larger program than Bainbridge (39 rows) but smaller than Pike County (48 rows).

### 3. Football schedule — transport and decode model

Boys Varsity Football from `sportSeasons[]` → `https://www.maxpreps.com/oh/lakewood/st-edward-eagles/football/schedule/`.

| Check | St. Edward | GA schools (Slice 16) |
|-------|------------|----------------------|
| Status | 200 | 200 |
| Transport | **Next.js** (`page: /team/schedule`) | Next.js |
| Legacy ASPX? | **No** | No |
| `x-middleware-rewrite` | Present (legacy `schedule.aspx` params) | Present |
| `pageProps.query` in HTML | **`null`** | Populated (`schoolid`, `ssid`, …) |
| `query` params recoverable | **Yes** — from `x-middleware-rewrite` header + `teamContext` / `tracking` | In `pageProps.query` |
| `pageProps.contests` | **Yes** — 11 rows, arity **41** | 11 rows, arity 41 |
| Participant width | **32** per side (2 sides) | 32 |
| `featuredGameData` | **Yes** — named anchor | Yes |
| Featured ↔ contests alignment | **Yes** — `contestId` matches row | Yes |
| `teamContext.data.teamId` === `school_id` | **Yes** (`2f510683-…`) | Yes |
| Contest participant `teamId` === `school_id` | **Yes** on school side (columnar cols 37/38) | Yes |
| `ssid` === `sportSeasons` football row | **Yes** | Yes |
| `sportSeasonId` (26-27 varsity football) | `2286cd80-c46d-4739-8dd1-92a67ca8daa7` | **Same UUID** |

**Schedule transport verdict:** Identical Next.js pipeline to GA football (Slice 06/16). Not legacy ASPX.

**Minor shape difference:** `pageProps.query` was `null` in the embedded `__NEXT_DATA__` for this capture, while GA schedule pages had a populated `query` object. Legacy routing parameters (`schoolid`, `ssid`, `allSeasonId`, `gendersport`) remain available in the `x-middleware-rewrite` response header and in `teamContext.data` / `tracking.ssid`. Client should not assume `pageProps.query` is always present — treat `teamContext` and `tracking` as fallbacks.

### 4. `sportSeasonId` collision check (Slice 16 follow-up)

Boys Varsity Football 26-27 `sportSeasonId` **`2286cd80-c46d-4739-8dd1-92a67ca8daa7`** is **identical** at Centennial, Bainbridge, Pike County, **and St. Edward**.

- Confirms Slice 16 revision: **`sportSeasonId` is not globally unique** — composite identity `(school_id, sport_season_id)` required.
- Fetch remains school-scoped via `canonical_url` from `sportSeasons[]`; `query.schoolid` in middleware rewrite disambiguates.

`allSeasonId` for varsity football: `22e2b335-334e-4d4d-9f67-a0f716bb1ccd` — also matches GA schools (program-level ID, not school-unique).

### 5. Differences vs Georgia public schools (non-breaking)

| Area | St. Edward | Impact |
|------|------------|--------|
| School type | `schoolInfo.type: Private` | Metadata only; no transport break |
| All-boys | `schoolInfo.gender: Boys`; 31/32 rows Boys | Config Step 2 may show almost exclusively boys teams; expect rare girls rows (rugby) |
| Search spelling | `Saint Edward` → 0; `St. Edward` → 5 | Add abbreviated retry for saint names |
| `sportSeasons[]` year scope | Current year only (32 × `26-27`) | No Pike County-style historical rows |
| `pageProps.query` on schedule | `null` in HTML | Use `teamContext` / middleware rewrite / `tracking` |
| Path grammar | Boys volleyball uses `…/volleyball/boys/`; girls rugby `…/rugby/girls/` | Reinforces Slice 04: use payload `canonicalUrl` |
| State / association | OHSAA (`associationGoverningBodyAbbreviation: OHSAA`) | Display/metadata; same field shapes |

No new top-level `pageProps` keys. No structural break in `contests` columnar encoding or `featuredGameData` anchor pattern.

### 6. Verdict — private out-of-state

| Aspect | Verdict |
|--------|---------|
| Search → `school_id` + `canonicalUrl` | **Survived** (with `St.` abbreviation retry) |
| School home → `sportSeasons[]` enumeration | **Survived** |
| Schedule → Next.js `contests` + `featuredGameData` | **Survived** for varsity football |
| `teamId` === `school_id` on team pages | **Survived** |
| Slice 06/14 columnar parser | **Likely applies unchanged** (arity 41, participant width 32, featured anchor) |
| Overall Centennial model | **Pass with minor revision** (search abbreviation; optional `pageProps.query` null fallback) |

Slice 17 (stability vs fragility) deferred — see placeholder below; no full writeup in this session.

### 7. Cache and fixture pointers

| Artifact | Path |
|----------|------|
| St. Edward search (failed `Saint Edward` note in fixture) | `tests/fixtures/maxpreps/st-edward/search-st-edward.json` |
| St. Edward `sportSeasons` | `tests/fixtures/maxpreps/st-edward/sport-seasons-26-27.json` |
| St. Edward football schedule | `tests/fixtures/maxpreps/st-edward/schedule-26-27.json` |
| Saint Edward search (0 results) private | `captures/private/www.maxpreps.com/cf0bc5d235ed1691.{raw,json}` |
| St. Edward search private | `captures/private/www.maxpreps.com/1ee2c1692cdaae80.{raw,json}` |
| St. Edward school home private | `captures/private/www.maxpreps.com/0a523fce58763315.{raw,json}` |
| St. Edward football schedule private | `captures/private/www.maxpreps.com/ea50c28fc13dd099.{raw,json}` |

**Stopped after Slice 16b.** Four live requests. No production client. No Slice 17–18 architecture chapter.

---

## Slice 17 — Stability vs fragility

**Evidence mode:** Fixture analysis only — **zero live requests**. Sources: four schools’ `sportSeasons[]` fixtures (`centennial`, `bainbridge`, `pike-county`, `st-edward`); Centennial `schedule-26-27.json` (football picker durability); Centennial `volleyball-schedule-26-27.json` (cross-sport `ssid` on schedule page). Prior slices cited for transport, search, TZ, and legacy ASPX findings.

**Question:** Which identifiers and payload conventions are safe to persist in config vs must be resolved at runtime? Does the `allSeasonId` / `sportSeasonId` split match a global sport-classification vs time-bounded team-season model?

### 1. Hypothesis under test

> `allSeasonId` represents a **sport / gender / level classification independent of school**, while `sportSeasonId` represents a **time-bounded variant** of that classification (school year and/or seasonal term such as Fall vs Spring).

Slice 05 described `allSeasonId` as grouping a school’s “team program.” Cross-school comparison (Slices 16–16b) already showed identical football IDs at four schools. This slice tests the hypothesis systematically across sports, levels, and seasonal terms using all four `sportSeasons[]` fixtures.

**Persist guidance unchanged pending this test:** Continue recommending `(school_id, sport_season_id)` + `canonical_url` — Slice 16 proved `sportSeasonId` is not globally unique and fetch is school-scoped.

### 2. Cross-school / cross-sport comparison

**Method:** For each `sportSeasons[]` row with `year: "26-27"`, group by `(sport, gender, level)` and by `(sport, gender, level, year, season)`. Compare `allSeasonId` and `sportSeasonId` across Centennial, Bainbridge, Pike County, and St. Edward.

#### 2a. Same sport + gender + level across schools — shared `allSeasonId`?

**Yes — when the program exists at multiple schools, `allSeasonId` is identical.** Zero mismatches across 43 Centennial programs that also appear at ≥1 other school. Examples:

| Program (26-27) | Schools with row | `allSeasonId` (prefix) | Match? |
|-----------------|------------------|------------------------|--------|
| Boys Varsity Football | 4/4 | `22e2b335` | **Yes** |
| Girls Varsity Volleyball | 3/3 GA *(St. Edward all-boys — no row)* | `2059473e` | **Yes** |
| Boys Varsity Basketball | 4/4 | `a42c7ea4` | **Yes** |
| Girls Varsity Basketball | 3/3 GA | `81d2a4ab` | **Yes** |
| Boys Varsity Soccer | 4/4 | `aba295df` | **Yes** |
| Boys Varsity Tennis | 4/4 | `e6fc52ec` | **Yes** |
| Boys Varsity Baseball | 4/4 | `94f7be29` | **Yes** |
| Boys Varsity Cross Country | 4/4 | `917605c1` | **Yes** |
| Boys Varsity Wrestling | 4/4 | `7a2d0490` | **Yes** |

**64** distinct `allSeasonId` values across all four fixtures; **each maps 1:1 to a unique `(sport, gender, level)` tuple** — no `allSeasonId` shared by different sport classes. This strongly supports `allSeasonId` as a school-independent MaxPreps sport classification ID, rather than a per-school identifier. Across the four schools examined, each observed `allSeasonId` maps 1:1 to a (sport, gender, level) tuple with no conflicts..

#### 2b. Same sport + gender + level + year across schools — shared `sportSeasonId`?

**Depends on seasonal term (`season` field), not just school year.**

| Case | `sportSeasonId` across schools | Evidence |
|------|-------------------------------|----------|
| Same `(sport, gender, level, year, season)` at 2+ schools | **Always identical** — **47/47** tuples | Football, volleyball, basketball, tennis, baseball, etc. |
| Same `(sport, gender, level, year)` but **different `season`** | **Differs** | Boys Varsity Soccer: GA schools `season: Spring` → `59787111-…`; St. Edward `season: Fall` → `ca5a6045-…` — **same `allSeasonId`** (`aba295df-…`) |

Football 26-27 varsity `sportSeasonId` `2286cd80-c46d-4739-8dd1-92a67ca8daa7` is identical at all four schools (confirmed). Volleyball `9f2e0dd1-…` and Girls Basketball `e3e91f97-…` match across all three GA schools that field those teams.

**Implication:** `sportSeasonId` encodes **school year + seasonal term** (when MaxPreps splits a program into multiple terms within one school year). It is **not** school-specific, but **is** insufficient alone — always pair with `school_id` (or `canonical_url`) because the same `sportSeasonId` appears at every school offering that exact team-season.

#### 2c. Within one school — levels and multi-term sports

| Check | Result | Evidence (Centennial 26-27) |
|-------|--------|----------------------------|
| Varsity vs JV vs Freshman football — different `allSeasonId`? | **Yes** | `22e2b335` / `42e4927a` / `c6d2f5e9` |
| Boys JV Soccer Spring vs Winter — same `allSeasonId`, different `sportSeasonId`? | **Yes** | `allSeasonId` `0ce4c0c7-…`; Spring `ssid` `bac8b420-…`, Winter `ssid` `90673742-…` |
| Boys Freshman Baseball Spring vs Fall — same pattern? | **Yes** | `allSeasonId` `526e1ebe-…`; two distinct `sportSeasonId`s |
| Bainbridge Girls Softball Spring vs Fall varsity — same `allSeasonId`? | **Yes** | `allSeasonId` `53b3ee46-…`; Spring `ssid` `a6ccb887-…`, Fall `ssid` `7142dd83-…` |
| Pike County Girls Gymnastics Spring vs Winter varsity — same `allSeasonId`? | **Yes** | `allSeasonId` `f088d76c-…`; two `sportSeasonId`s |

Slice 05 within-school findings **survive**; the revision is that `allSeasonId` is **not school-scoped**.

#### 2d. Cross-sport — global catalog vs per-school IDs?

| Identifier | Scope | Evidence |
|------------|-------|----------|
| `allSeasonId` | School-independent classification ID — observed consistently for the same (sport, gender, level) across all four schools tested. | 64 unique values, 0 conflicts; same Boys Varsity Football `allSeasonId` at GA and OH schools |
| `sportSeasonId` | School-independent time-bounded classification ID | 47/47 full-tuple matches identical; 12 `sportSeasonId`s appear at all four schools |
| `school_id` | **Per school** | Constant within a school’s `sportSeasons[]`; differs across schools |

Cross-sport: football `22e2b335` ≠ volleyball `2059473e` ≠ basketball `a42c7ea4` — each sport class has its own catalog entry.

### 3. Hypothesis verdict

**Supported, with refinement.**

| Claim | Verdict | Notes |
|-------|---------|-------|
| `allSeasonId` = sport/gender/level classification, school-independent | **Supported** | Identical across all schools that offer the program; 1:1 with sport class globally |
| `sportSeasonId` = time-bounded variant (school year ± seasonal term) | **Supported** | New UUID each school year (Slice 05 football picker); multiple `sportSeasonId`s per `allSeasonId` when Spring/Winter or Spring/Fall terms coexist in one school year |
| Slice 05 “team program at one school” wording | **Reject** | `allSeasonId` is **not** school-specific; revise to “global MaxPreps sport/gender/level class” |
| Exact upstream semantics | **Still open** | Inferred from payloads only — no MaxPreps API contract. Whether `season` is always part of `sportSeasonId` encoding for single-term sports is untested at prior school years. |
| Multi-term rollover | **Open** | When refreshing `sportSeasons[]`, matching on `all_season_id` alone may return **multiple** current-year rows (e.g. Boys JV Soccer Spring + Winter). Client must also match `season` or prefer the canonical row from stored `canonical_url`. |

**Persist guidance (unchanged):** Store `(school_id, sport_season_id)` + `canonical_url` as composite team-season identity. Optionally store `all_season_id` for rollover hint — but validate with `sport`, `gender`, `level`, and `season` when multiple rows share one `allSeasonId`.

### 4. Stability classification (three buckets)

Evidence from Slices 01–17 is grouped into three integration tiers. **Safe** means repeatedly observed across pages and schools with named fields and stable UUID/path behavior — reasonable to treat as a **core contract** for config and fetch. **Useful** means the field is real and decodable, but enum meanings, rollover rules, timezone policy, or global ID semantics are **partially inferred** from fixtures, not documented by MaxPreps. **Fragile** means deploy-specific layout, undocumented positional encoding, transport breaks, or proven failure modes — **do not depend on** for identity or primary parsing.

#### SAFE / CORE CONTRACT

Persist or key fetches on these. Evidence tier **Proven** unless noted.

| Item | Role | Evidence |
|------|------|----------|
| `school_id` | Primary school identity | Same UUID in search `schoolId`, `schoolContext.schoolId`, `mpschoolid`, `query.schoolid` (Slice 03). Survived GA + OH, public + private (Slices 16–16b). |
| `(school_id, sport_season_id)` | Primary team-season identity | `sportSeasonId` / `ssid` on `sportSeasons[]`, schedule `query`, `teamContext`, contest rows (Slices 05–06). Required composite — `sportSeasonId` alone is not school-unique (Slice 16). |
| `canonical_url` (school + team) | Fetch path and user links | From search and `sportSeasons[]`; survives deploy rotation (Slices 03–04, 16). Append `schedule/` — never hand-build slug segments. |
| `sport`, `gender`, `level`, `year`, `season` | Program + team-season context | Named fields on every `sportSeasons[]` row (Slice 04). Required when multiple rows share one `allSeasonId` (Slice 17 §3). |
| `sportSeasons[]` on school home | Step 2 team enumeration | `GET` school `canonicalUrl` → `schoolContext.sportSeasons[]` (Slices 04, 16–16b). One row per `sportSeasonId`. |
| `contestId` | Per-game identity / game URLs | Named on `featuredGameData`; `row[1]` on contest rows; `?c=` query param (Slices 01, 06). |
| Contest `date` (`row[11]`) | Kickoff wall time (naive) | **Proven** on all observed contest rows; matches `featuredGameData.date` (Slices 06, 08). Preserve as the raw naive MaxPreps schedule datetime. Do not localize it using school or state timezone without additional evidence; normalized automation datetime remains a separate concern. (see Useful). |
| Contest `venue` (`row[5]`) | Game site label | **Proven** — `featuredGameData.location` (Slices 06, 09). |
| Contest `canonicalUrl` (`row[18]`) | Game page link | **Proven** — `featuredGameData.canonicalUrl` (Slice 06). |
| Opponent `school_id` (`teams[*][1]`) | Opponent identity | **Proven** — school UUID on participant arrays (Slices 03, 06, 09). |
| Opponent `name` (`teams[*][14]`) | Display | **Proven** — matches `featuredGameData.opponentTeam.name` (Slice 06). |
| `homeAwayType` `0` / `1` | Home / away | **Proven** — `0` = home, `1` = away (Slices 06, 09). |
| SSR `GET` + `__NEXT_DATA__` | Schedule transport (head-to-head) | **Proven** for football, volleyball, basketball at Centennial + GA validation schools (Slices 01, 14, 16–16b). |
| Search → `initialSchoolResults[]` | School discovery (when query accepted) | **Proven** for short-name queries (Slices 02, 16–16b). |
| `teamId` on team pages | Alias of `school_id` | **Proven** misnomer — normalize to `school_id` (Slice 03). |

#### USEFUL BUT SEMANTICS PARTIALLY INFERRED

Use for decode, display, and rollover — but treat mappings and edge behavior as **best-effort**, not guaranteed upstream contract.

| Item | Role | What is proven vs inferred |
|------|------|------------------------------|
| `allSeasonId` / `all_season_id` | Global sport/gender/level catalog | **Proven:** identical across schools for same class; stable across school years per level (Slice 05 picker, Slice 17). **Inferred:** exact upstream name/semantics; not a fetch key; multi-term sports share one `allSeasonId` with multiple `sportSeasonId`s. |
| `contestState` (`row[15]`) | Game status enum | **Proven:** `1` = deleted (`row[28]` message), `2` = pregame/scheduled. **Inferred:** `4` = final (with `hasResult` + scores). **Not observed:** live, postponed, cancelled — map unknown ints to `unknown` (Slices 06–07). |
| `hasResult`, `row[28]` | Status corroboration | **Proven** on observed rows. Human strings supplement enum — do not parse prose for primary status. |
| Scores / `result` (`row[37]`/`[38]`) | Final scores | **Inferred** from extended participant copies aligned to `featuredGameData` (Slice 06). Absent on scheduled rows — **proven**. |
| `homeAwayType` `2` | Neutral site | **Inferred** — one row + description text (Slice 09). |
| Kickoff timezone | Automation offset | **Proven:** naive `row[11]`; featured-game school TZ fields; state `stateData` TZ. **Inferred / policy:** which TZ applies to non-featured rows; Pensacola mismatch (Slice 08). |
| `featuredGameData` | Columnar index anchor | **Proven** present on Next.js head-to-head schedules (Slices 06, 14). **Inferred** as stable decode strategy — not a named MaxPreps API. |
| `teamSeasonPickerData[]` | Prior seasons within one sport | **Proven** on team pages (Slice 05). Historical selection behavior **inferred** for product (Slice 12). |
| `sportSeasons[]` year scope | Current vs leftover rows | **Proven:** mostly current year; Pike County includes `11-12` rows (Slice 16). Filter policy **inferred** for Step 2. |
| `sportSeasonId` rotation | School-year rollover | **Proven:** new UUID each football school year (Slice 05 picker). Refresh match via `all_season_id` + semantic fields **inferred** (Slice 17 §3). |
| Standings (`standingsData`, featured `teamsCalculated`) | W-L, streak, conference | **Proven** on football schedule page (Slice 11). Refresh cadence and cross-sport presence **not fully validated**. |
| Logo URLs (`mascotUrl`, participant `[20]`) | Display images | **Proven** absolute URLs in payload (Slice 10). Hotlink reliability **uncertain** (no `HEAD` test). |
| `pageProps.query` | Legacy routing params in HTML | **Proven** populated on most GA schedule pages. **Proven exception:** `null` on St. Edward — fall back to `teamContext` / middleware rewrite (Slice 16b). |
| JSON-LD `SportsEvent` | Supplementary events | **Proven** in HTML. **Inferred** as secondary — incomplete vs `contests[]`, TZ encoding questionable (Slices 01, 08). |
| Participant `sportSeasonId` (`[2]`) | Opponent team-season | **Proven** index. Occasional duplicate of configured school `ssid` on featured named object — prefer positional participant per side (Slice 14). |
| Search spelling (`St.` vs `Saint`) | Discovery UX | **Proven** behavior difference (Slice 16b). Retry policy **inferred** — not an upstream guarantee. |
| `contestAlias` (`row[21]`) | Display ("Game" vs "Match") | **Proven** varies by sport (Slice 14). Cosmetic only. |

#### FRAGILE / DO NOT DEPEND ON

Never persist as identity keys; never assume availability without a fallback path.

| Item | Why fragile | Evidence |
|------|-------------|----------|
| `buildId` | Changes every deploy | `92628a14` → `d8af3013` → `c4253631` across captures; page URLs work without it (Slices 01, 14, 16). |
| `contests[]` positional indices (arity 41, width 32) | Undocumented columnar layout | Indices derived by anchoring to `featuredGameData` (Slice 06). Shape held football/volleyball/basketball (Slice 14) but **no named per-game schema** — redeploy may reorder. |
| `featuredGameData` absence | Decode anchor missing | **Absent** on legacy ASPX tennis/track pages (Slice 15). Parser cannot assume it on all sports. |
| Guessed / hand-built URLs | Wrong paths 404 | Softball `…/softball/schedule/` vs `…/softball/fall/` (Slice 14). |
| Legacy ASPX schedule transport | Different stack, no `contests[]` | Tennis and track at Centennial — jQuery/ASPX, empty schedule (Slice 15). |
| Search query qualifiers | Silent empty results | `Centennial Roswell`, `Centennial High School` → 0 schools (Slice 02). |
| `ranking` | Opaque sort key | Search only (Slice 02). |
| URL slug segments alone | Not identity | Collision risk; grammar varies (Slices 03–04). |
| `/_next/data/<buildId>/…` JSON routes | Not observed | Slice 01 — not in captured HTML; do not build client around them. |
| `contestState` for live / postponed / cancelled | No samples | Slice 07 — only `1`, `2`, `4` observed; do not promise `IN` or postponed states. |
| JSON-LD as primary schedule source | Incomplete + TZ issues | 9 vs 11 contests (Slice 01); Pensacola offset mismatch (Slice 08). |
| Static asset chunk hashes | Deploy-coupled | Same class as `buildId` (Slice 01). |

**Persist summary (unchanged):** Core config = `school_id` + `(school_id, sport_season_id)` + `canonical_url` + semantic program fields. Optional = `all_season_id`. Decode contests at runtime using Useful-tier fields; treat positional maps and absent `featuredGameData` as Fragile-tier risks.

### 5. Conventions that must survive into the client (Slices 03–17)

Prior list (Slices 03–05) **plus Slice 17 addenda:**

- Normalize MaxPreps field names to internal snake_case (`school_id`, `sport_season_id`, `all_season_id`, `canonical_url`).
- Treat `ssid`, `sportSeasonId`, and `query.ssid` as the same identifier.
- Treat `teamId` on team pages as `school_id` if encountered — never as a per-team entity key.
- Prefer payload `canonicalUrl` over hand-built paths.
- **Persist `(school_id, sport_season_id)`** — `sportSeasonId` alone is not globally unique (Slice 16).
- **`allSeasonId` is a global sport/gender/level catalog ID**, not school-specific. Optional for rollover; when used, also match `season` if multi-term rows exist.
- Do not assume `pageProps.query` is populated. Prefer the client’s known `school_id` / selected team metadata and named `teamContext` / tracking fields. Treat x-middleware-rewrite as research/diagnostic evidence, not a required production dependency.
- Retry abbreviated `St.` when saint-name search returns 0 schools (Slice 16b).
- Do not assume `sportSeasons[]` contains only the active school year. Determine the active/latest school-year cohort from the returned rows for normal team selection; preserve older rows only for explicit historical-season behavior.

### 6. Cache and fixture pointers

| Artifact | Path |
|----------|------|
| Centennial `sportSeasons` (47 rows) | `tests/fixtures/maxpreps/centennial/sport-seasons-26-27.json` |
| Bainbridge `sportSeasons` (39 rows) | `tests/fixtures/maxpreps/bainbridge/sport-seasons-26-27.json` |
| Pike County `sportSeasons` (48 rows, incl. 11-12) | `tests/fixtures/maxpreps/pike-county/sport-seasons-26-27.json` |
| St. Edward `sportSeasons` (32 rows) | `tests/fixtures/maxpreps/st-edward/sport-seasons-26-27.json` |
| Football picker durability (`allSeasonId` across years) | `tests/fixtures/maxpreps/centennial/schedule-26-27.json` |
| Volleyball schedule (`ssid` / `allSeasonId` on team page) | `tests/fixtures/maxpreps/centennial/volleyball-schedule-26-27.json` |

**Stopped after Slice 17.** Zero live requests. No production client. Slice 18 is the architecture and feasibility capstone below.

---

## Slice 18 — Client architecture and feasibility

**Evidence mode:** Synthesis of Slices 01–17 (fixtures + prior captures). **Two live requests** in this slice only: `robots.txt` and `/terms-of-use/` (linked from cached Slice 01 homepage footer). No new schedule/search/school pages fetched. **No production client** — this section is the spec PRODUCT.md §30 will follow.

**Purpose:** Consolidate transport, identity, parsing, polling, PRODUCT.md mapping, recommended client layering, and a go/no-go verdict so §30 can start without rereading every slice.

---

### 1. How data is exposed

MaxPreps serves the integration-relevant surfaces as **server-rendered Next.js HTML** with embedded JSON in `<script id="__NEXT_DATA__">` → `props.pageProps` (Slice 01). There is **no observed standalone JSON API** for school search, team enumeration, or head-to-head schedules on the pages validated in Slices 01–16b.

| Surface | Transport | Primary payload path | Notes |
|---------|-----------|---------------------|-------|
| School search | `GET /search/?q=<normalized>&q2=<display>` → HTML | `pageProps.initialSchoolResults[]` | Internal route `page: /discovery/search` (Slice 02). Playwright was used once to discover the URL pattern; results themselves are SSR. |
| School home / team enumeration | `GET {school canonicalUrl}` → HTML | `pageProps.schoolContext.sportSeasons[]` | One GET lists all current team-season rows (Slice 04). |
| Team schedule (head-to-head) | `GET {team canonicalUrl}schedule/` → HTML | `pageProps.contests[]` + `pageProps.featuredGameData` | Columnar contests (arity **41**); decode anchored on featured game (Slices 06, 14). |
| Legacy exception | `GET {canonicalUrl}schedule/` → ASPX HTML | **No** `__NEXT_DATA__` | Observed for Centennial boys tennis and girls track (Slice 15) — jQuery/ASPX stack, empty schedules. |

**Supplementary payloads** (do not build the client on these alone): `application/ld+json` `SportsEvent` (incomplete vs `contests[]`, TZ questionable — Slices 01, 08), `meta name="targeting"` ad context, rendered DOM rows.

**Not used:** `/_next/data/<buildId>/…` JSON routes — not observed in HTML; `buildId` changes every deploy (Slice 01, 17). Client fetches **stable public page URLs**, not buildId-keyed data routes.

---

### 2. Endpoints and request patterns

**Invariant:** Every fetch uses a **school-scoped canonical URL** from search or `sportSeasons[]`. Append `schedule/` for schedules. **Never** construct paths from sport names, gender, or season segments alone (Slice 14 softball 404: `…/softball/schedule/` vs correct `…/softball/fall/`).

| Operation | Method | URL source | Identity in request |
|-----------|--------|------------|---------------------|
| `search_schools(query)` | `GET` | `/search/?q={lower(query)}&q2={query}` | None — query string only |
| `get_school_teams(school)` | `GET` | `school.canonical_url` from search or config | Path encodes school; `schoolContext.schoolId` in response |
| `get_schedule(team)` | `GET` | `{team.canonical_url}schedule/` | Path encodes school + team program; **not** `ssid`-only |

**Never:**

- `GET` by `sport_season_id` / `ssid` alone — same `ssid` appears at multiple schools (Slice 16–16b).
- Guess URL grammar (`/football/` vs `/basketball/girls/` vs `/softball/fall/`) — always use payload `canonicalUrl`.
- Depend on `pageProps.query` — populated on most GA pages, **`null` on St. Edward**; use `teamContext` / `x-middleware-rewrite` fallback (Slice 16b).

**HTTP shape:** Single `GET` per page → `200 text/html; charset=utf-8`. No cookies, no JS execution, no auth (Slices 01–02, gate Slice 06). `User-Agent: hacs-highschoolscores-explore/0.1` succeeded throughout exploration.

**Search UX pattern:** Short name only (`centennial`, `bainbridge`, `st. edward`) + user picks city/state/mascot from `initialSchoolResults[]`. Qualifiers like `Centennial Roswell` or `Centennial High School` return **0** schools (Slice 02). Retry `St.` when spelled-out saint names fail (Slice 16b).

---

### 3. Stable identifiers (Slice 17 semantics — do not relitigate)

Use Slice 17 three-bucket classification. **Core contract** for config and storage:

| Identifier | Role | Persist? | Fetch key? |
|------------|------|----------|------------|
| `school_id` | School UUID (`schoolId`, `schoolContext.schoolId`, `mpschoolid`) | **Yes** — primary school key | Indirect — embedded in canonical path |
| `(school_id, sport_season_id)` | Team-season identity (`sportSeasonId` / `ssid`) | **Yes** — composite team key | **No** — metadata only; `ssid` is **not** school-unique (shared across all four test schools for varsity football) |
| `canonical_url` | School or team base URL from payload | **Yes** — fetch path + user links | **Yes** — schedule = `{canonical_url}schedule/` |
| `all_season_id` | Global sport/gender/level catalog (`allSeasonId`) | **Optional** — rollover hint | **No** — not school-specific; multiple `sportSeasonId`s can share one `allSeasonId` when Spring/Winter or Spring/Fall terms coexist (Slice 17) |
| `teamId` on team pages | Misnomer | **Normalize immediately** to `school_id` | Never expose as team key |
| `contestId` | Per-game UUID | Runtime / game objects | From `featuredGameData` or `contests[][1]` |
| `contestAlias` | Display ("Game" vs "Match") | Display only | — |

**Semantic fields** required alongside IDs when disambiguating: `sport`, `gender`, `level`, `year`, `season` (Slice 04–05, 17).

**Storage rule:** Never key durable storage on `ssid` alone. Never treat `teamId` as a per-team entity ID.

---

### 4. Payload structures

#### Search — `initialSchoolResults[]` (Slice 02)

Per school: `schoolId`, `name`, `city`, `state`, `zip`, `mascot`, `canonicalUrl`, `mascotUrl`, `ranking` (opaque). Ignore `initialCareerResults` for config.

#### Enumeration — `sportSeasons[]` on school home (Slice 04)

One row per `sportSeasonId`. Fields: `schoolId`, `sportSeasonId`, `allSeasonId`, `sport`, `gender`, `level`, `year`, `season`, `canonicalUrl`, `isPublished`, … Filter to **current school year** for Step 2 — Pike County includes `11-12` leftovers (Slice 16). Compose display: `{gender} {level} {sport}`.

#### Schedule — `contests[]` + `featuredGameData` (Slices 06, 14)

- `contests`: list of rows, each **arity 41**, two participant blobs width **32**.
- `featuredGameData`: named object for one contest — **re-anchor** decode by matching `contestId` to `row[1]`, then verify indices `[5]`, `[11]`, `[15]`, `[18]`, participants, `[37]`/`[38]` scores.
- `teamContext`: team/school metadata, season picker, standings snippets.
- `teamSeasonPickerData[]`: prior seasons within one sport program (Slice 05, 12).

**Deleted rows:** `contestState` `1` — filter from user-facing schedule (Slice 13).

---

### 5. Sport differences

| Category | Sports observed | Parser | Verdict |
|----------|-----------------|--------|---------|
| Head-to-head (validated) | Football, volleyball, basketball (+ GA/OH validation football) | **Same columnar decoder** — sport-specific logic is display/URL only (Slice 14) | **Supported for v1** |
| Legacy / empty | Centennial boys tennis, girls track | ASPX HTML, no `contests[]`, no `featuredGameData` (Slice 15) | **Defer** — do not assume Slice 06 parser |
| Meet / individual (unvalidated) | Track meets, tennis duals when populated | Unknown payload; PRODUCT §8 meet exception plausible | **Defer** — need populated capture |
| Not fetched in exploration | Baseball, softball (schedule), soccer, golf, swimming, … | Likely Next.js for team sports with `canonicalUrl` paths; softball path needs `fall/` segment | **Assume same as football until proven otherwise**; always use `canonicalUrl` |

**v1 supported-sports stance:** Ship generic head-to-head parser; document tennis/track/meets as **out of scope until validated**. Do not block §30 on them.

---

### 6. Fragility and risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Positional `contests[]` map (arity 41) | Redeploy may reorder columns | Anchor every index change to `featuredGameData`; fixture tests; treat map as **Fragile** tier (Slice 17) |
| `featuredGameData` absent | Cannot decode contests | Legacy ASPX sports (Slice 15); detect absence and surface “unsupported transport” |
| Kickoff TZ | `row[11]` is naive local; offset policy **not locked** | Featured game + `stateData` TZ exist; Pensacola cross-check showed JSON-LD UTC mismatch (Slice 08). §30 must not hard-code offset without product decision |
| `pageProps.query` null | Missing legacy params in JSON | Fall back to `teamContext`, `tracking`, middleware rewrite header (Slice 16b) |
| Search query sensitivity | Empty results for reasonable-looking queries | Short-name search + picker; `St.` retry; never require “School, City ST” single string (revises PRODUCT §30 example) |
| `sportSeasons[]` year mix | Stale rows in picker | Filter by `year` cohort (Slice 16) |
| `sportSeasonId` shared across schools | Wrong school if keyed on `ssid` alone | Composite `(school_id, sport_season_id)` + school-scoped `canonical_url` |
| `contestState` enum gaps | No live/postponed/cancelled samples | Map unknown → `unknown`; only promise `scheduled` and `final` for v1 (Slice 07, 13) |
| `buildId` / static hashes | Break buildId-keyed clients | Ignore — use page URLs |
| Blocking / rate limits | 429/403 ends exploration | ≥2s between requests; 2–4 refreshes/day target; stop on challenge (traffic policy) |
| robots.txt / ToS | Published restrictions on automated access | See § below — **project risk**, not parsed here as legal advice |

---

### 7. Rate and request budget

PRODUCT.md §11 target **~2–4 refreshes per day** per configured school/team set is **feasible**.

| Refresh cycle | Requests (typical) | Notes |
|---------------|-------------------|-------|
| School-level poll | **1** `GET` school home | Re-enumerates all `sportSeasons[]` — shared across teams at that school |
| Per selected team schedule | **1** `GET` `{canonical_url}schedule/` | Independent per team-season |
| Search (config only) | **1** `GET` per search attempt | Not on polling path |

Example: 1 school, 3 teams → **1 + 3 = 4** schedule refresh URLs per cycle; at 4 cycles/day ≈ **16 GETs/day** — well within conservative integration behavior. Adaptive game-day polling (PRODUCT §12) adds temporary schedule re-fetches only around expected completion — no live-score polling required (Slice 07).

**Deduplication:** Coordinator should cache school home and fan out team schedule fetches; multiple teams at same school must not each trigger separate enumeration GETs unless school home TTL expired.

---

### 8. PRODUCT.md support matrix

| PRODUCT capability | Supported? | Evidence / caveat |
|--------------------|------------|-------------------|
| School-first config (§3.2) | **Yes** | Search + picker (Slices 02, 16–16b) |
| Team discovery (§3.2 Step 2, §24.4) | **Yes** | `sportSeasons[]` on one school-home GET (Slice 04) |
| Season schedules (§24.7, §2.2) | **Yes** | `contests[]` decodes to game list (Slice 06) |
| Final scores (§24.8, §13) | **Yes** | `contestState` 4 + `row[37]`/`[38]` (Slice 07) |
| Upcoming game date/opponent (§24.9) | **Yes** | `contestState` 2 + `row[11]`, participants (Slices 06, 09) |
| Live / in-progress `IN` (§5, §15) | **No** | No live `contestState` observed; do not promise (Slice 07) |
| Kickoff automations (§14) | **Partial** | Naive `row[11]` works for ordering; **TZ offset for non-featured games not fully specified** (Slice 08) — product must choose policy |
| Schedule-change / postponed / cancelled (§27.G, §13) | **Partial** | Deleted rows (`contestState` 1) detectable; postponed/cancelled **not observed** (Slice 13) |
| Records / standings (§6, §16) | **Bonus** | `standingsData` on schedule page (Slice 11) |
| Logos (§6, §28.9) | **Unproven** | URLs in payload (Slice 10); no hotlink/HEAD validation |
| Conservative requests (§24.13) | **Yes** | Low daily volume achievable (§7 above) |
| Last-known data on failure (§24.14) | **Design** | Client/coordinator concern — transport supports stale cache |
| Sport-agnostic config (§24.6) | **Yes with scope limit** | One parser for validated head-to-head sports; tennis/track deferred |

**§30 example query revision:** Do not use `"Centennial High School, Roswell GA"` as the search string. Use **`centennial`** (or user short name) → pick Roswell, GA, Knights from results.

---

### 9. Recommended client architecture

**Confirm** the layered model (revised method signatures vs PRODUCT §10):

```
MaxPreps (public HTTPS page URLs)
  → thin HTTP + cache (per-URL TTL; page URLs only — not buildId-keyed _next/data)
  → adapters
       · HTML → parse __NEXT_DATA__.props.pageProps
       · search → initialSchoolResults[]
       · school home → sportSeasons[]
       · schedule → contests[] decoded via featuredGameData re-anchor
       · teamId → school_id immediately
  → normalized models: School, Team (team-season), Game
  → (later) Home Assistant DataUpdateCoordinator + entities
```

**Methods (conceptual — not implemented in this slice):**

| Method | Input | Output | Fetch |
|--------|-------|--------|-------|
| `search_schools(query)` | Short name string | `list[School]` | `GET /search/?q=&q2=` |
| `get_school_teams(school)` | `school_id` + `canonical_url` | `list[Team]` from `sportSeasons[]` | `GET canonical_url` |
| `get_schedule(team)` | `canonical_url` (+ stored identity metadata) | `list[Game]` | `GET {canonical_url}schedule/` |

`sport_season_id` is **identity metadata** carried on `Team` for storage and rollover — **not** a schedule fetch key. Optional `get_team_metadata` can merge `teamContext` from the schedule response (logo, record).

**Parsing isolation (PRODUCT §9, §28.12):** All MaxPreps-specific decoding stays below the coordinator. HA layer sees only normalized models and stable enums.

**Conventions that must survive** (Slice 17 §5 — full list there): snake_case internals; composite `(school_id, sport_season_id)`; payload `canonicalUrl` only; `all_season_id` optional global class; filter `sportSeasons[]` by year; `St.` search retry; `pageProps.query` fallback.

---

### 10. Feasibility verdict

**Go — with revised assumptions.**

Technical feasibility for a **personal, low-volume, head-to-head-sports** Home Assistant integration is **established**. The Slice 06 gate passed; Slices 14 and 16–16b generalized the model. Remaining gaps are **product scope and policy** choices, not existential blockers — except where explicitly deferred (live scores, tennis/track transport, kickoff TZ policy).

**Not go** as originally drafted in PRODUCT.md without these revisions.

#### PRODUCT.md §28 assumptions — validation map

| # | Assumption | Verdict | Research answer |
|---|------------|---------|-----------------|
| 1 | Public schedule/results without auth | **Validated** | All captures unauthenticated (Slices 01–16b) |
| 2 | School search without pasted URLs | **Validated with UX revision** | Short name + picker; not full “School, City ST” string (Slices 02, 16b) |
| 3 | Stable school/team identifiers | **Validated with composite revision** | `school_id` + `(school_id, sport_season_id)` + `canonical_url` (Slices 03–05, 16–17) |
| 4 | One parser for most sports | **Partial** | Football/volleyball/basketball: yes (Slice 14). Tennis/track/meets: **defer** (Slice 15) |
| 5 | Finals within useful timeframe | **Plausible, unmeasured** | Finals decode reliably; posting latency not benchmarked (Slice 07) |
| 6 | Extremely low request volume | **Validated** | §7 above |
| 7 | Adaptive coordinator polling | **Validated conceptually** | No live state needed; post-game result checks sufficient (Slices 07, 12) |
| 8 | Schedule data small enough for HA | **Validated** | ~11–32 contests per page in fixtures |
| 9 | Logos referenceable | **Unproven** | URLs exist; hotlink reliability not tested (Slice 10) |
| 10 | Existing HA cards sufficient | **Unchanged** | Out of research scope; reasonable |
| 11 | Custom card optional | **Unchanged** | Product principle |
| 12 | Parsing isolated from HA | **Validated** | Architecture in §9 |

#### Open decisions answered (§27)

| Decision | Answer |
|----------|--------|
| **I. School identity** | Persist `school_id` (UUID) + `canonical_url`. Do not use slug or display name alone (Slice 03). |
| **J. Team identity** | Persist `(school_id, sport_season_id)` + team `canonical_url` + semantic fields (`sport`, `gender`, `level`, `year`, `season`). Optional `all_season_id` for rollover. Sport+gender+level alone is insufficient when multiple seasonal terms exist (Slices 05, 17). |
| **H. Multiple seasons** | Default: current school year from `sportSeasons[]` (filter `year`). Historical: `teamSeasonPickerData[]` on schedule page changes fetch URL to prior `canonicalUrl` + `schedule/` (Slice 12). Auto-rollover: refresh school home and match `all_season_id` + semantics — not `ssid` alone (Slice 17). |

#### Assumptions that must change before §30 / v1

1. **Search string** — short name + disambiguation picker, not `"Centennial High School, Roswell GA"`.
2. **Team key** — `(school_id, sport_season_id)`, never `ssid` or `teamId` alone.
3. **Live `IN` state** — out of scope v1 (PRODUCT §25 aligned).
4. **Kickoff TZ** — naive `row[11]` proven; offset policy **open** — §30 tests should use naive or explicit product-chosen rule, not assume JSON-LD UTC (Slice 08).
5. **Tennis / track / meets** — defer from v1 “compatible sports” until populated Next.js or legacy decode path is proven.
6. **`allSeasonId`** — global catalog, not per-school program ID (Slice 17 refinement).
7. **Supported sports list** — define after §30 milestone across head-to-head samples; do not claim all MaxPreps sports.

#### What §30 should implement (pointer only)

Per PRODUCT.md §30: `search_schools` → `get_school_teams` → `get_schedule(canonical_url)` → normalize → print → tests. Use fixtures in `tests/fixtures/maxpreps/`. Do **not** start HA entities until that layer is stable across materially different head-to-head sports.

---

### Python HTTP without browser state (Slices 01–16b)

Restated for the capstone record:

| Flow | Browser required? | Python HTTP sufficient? | Notes |
|------|-------------------|---------------------------|-------|
| Homepage / school / schedule pages | **No** | **Yes** | `__NEXT_DATA__` in initial HTML (Slice 01) |
| Discover `/search` URL pattern | **Once** (Playwright) | **Yes after pattern known** | Homepage cache does not expose search endpoint (Slice 02) |
| Search results fetch | **No** | **Yes** | `GET /search/?q=&q2=` → `initialSchoolResults` |
| Team enumeration | **No** | **Yes** | School home `sportSeasons[]` |
| Schedule decode | **No** | **Yes** | `contests[]` + `featuredGameData` in HTML |
| Tennis/track schedules (Centennial) | **No** | **Yes for fetch** — **No for parse** | ASPX HTML returned but no machine-readable contests (Slice 15) |

**Client requirements:** stdlib `urllib` or `httpx`; custom `User-Agent`; no cookies; no JS; parse HTML JSON blob (or promote to fixture-driven tests). **Stop** on 429/403/challenge (traffic policy).

**Playwright scope:** Discovery only for search UI — not part of the production client architecture.

---

### robots.txt and Terms of Use — published facts (Slice 18 fetches)

**Not legal conclusions.** Facts recorded for maintainer review. Compliance is a **project risk** outside this research doc.

#### robots.txt (`GET https://www.maxpreps.com/robots.txt`, 200, 5094 bytes, 2026-09-01)

- Declares sitemap: `https://www.maxpreps.com/Index-Sitemap.xml`.
- `User-agent: *` rules include **`Disallow: /school/`**, **`Disallow: /team/`**, **`Disallow: /discovery/`**, **`Disallow: /contest/`**, **`Disallow: /local/`** (with narrow `Allow` exceptions for legacy `home.aspx` paths), **`Disallow: /scores/`** (with limited `Allow`), and query-param disallows (`apptype`, `fe`).
- **`/search/` is not listed** in the `User-agent: *` block captured.
- Exploration URLs use **state/city/slug paths** (e.g. `/ga/roswell/centennial-knights/…`) — not the `/school/` or `/team/` prefix paths disallowed above.
- `User-agent: Googlebot` block adds historical year disallows and sport-path disallows (e.g. `/*/tennis`, `/*/track-field`) not present in the `*` block.
- `User-agent: Exabot` → `Disallow: /`.

**Project risk (factual):** Published robots rules target several path prefixes; integration URLs may or may not fall under those rules depending on how crawlers interpret MaxPreps routing. Maintainers should review robots.txt alongside intended fetch URLs.

#### Terms of Use (`GET https://www.maxpreps.com/terms-of-use/`, 200, linked from homepage footer `href="/terms-of-use/"`, Next.js `page: /concordia/terms-of-use`)

Published text (paraphrased for index — see capture for verbatim):

- Platform provided for **“informational, noncommercial”** / **“personal, non-commercial use”**.
- **Limited, revocable, nonexclusive** license; prohibits **republication, distribution, commercial exploitation** of Content.
- **RESTRICTIONS ON USE** include (verbatim themes): do not use **“any robot, spider, scraper, or other automatic or manual means to access, monitor, or copy the Platform or its Content or data”**; do not **“Engage in unauthorized spidering, ‘scraping,’ data mining, or harvesting”** or **“any other unauthorized automated means to gather data”**; access Content only through the Site/App interface; no deep linking except homepage without authorization.
- Operator: **MaxPreps Inc.**, **2080 Media, Inc.** family; copyright/IP retained by MaxPreps.
- Terms may change; continued use after posted changes constitutes acceptance (page references a “Last Updated” mechanism; no specific date extracted from this capture body).

**Project risk (factual):** Published Terms describe restrictions on automated access and copying that overlap with how a polling integration would operate. Maintainers must reconcile integration behavior with these Terms and robots.txt before public distribution — this research does not resolve that question.

#### Cache pointers (Slice 18 only)

| Artifact | Path |
|----------|------|
| robots.txt | `captures/private/www.maxpreps.com/6b4f0efe27101bec.{raw,json}` |
| Terms of Use | `captures/private/www.maxpreps.com/ff46cdd961286d3a.{raw,json}` |
| Homepage footer links (Terms, Privacy) | `captures/private/www.maxpreps.com/fd17e40e5105fefd.raw` (Slice 01) |

---

**Stopped after Slice 18.** Two live requests (robots.txt, terms-of-use). **No production client.** Research phase complete for PRODUCT.md §30.

---

## Phase 2 Slice 0 — Fixture addendum (Centennial baseball schedule)

**Evidence mode:** One live `GET` of the Boys Varsity Baseball schedule URL already recorded on the Centennial `sportSeasons[]` row (`canonicalUrl` `…/baseball/` + established `schedule/` child; `sportSeasonId` `0e872276-ae3c-4868-8b66-cb53e9727cfb`). No sports-research reopening. Optional girls basketball fixture promoted from the existing Slice 14 private cache with **zero new live requests**. Softball was not fetched.

| Field | Baseball (acceptance) | Girls basketball (optional coverage) |
|-------|----------------------|--------------------------------------|
| URL | `https://www.maxpreps.com/ga/roswell/centennial-knights/baseball/schedule/` | `https://www.maxpreps.com/ga/roswell/centennial-knights/basketball/girls/schedule/` |
| Timestamp (UTC) | 2026-09-02T01:45:00.701070+00:00 | 2026-09-01T21:02:11.313820+00:00 (Slice 14 cache) |
| Status | 200 | 200 (no new GET) |
| Transport | Next.js `__NEXT_DATA__` in HTML (`page`: `/team/schedule`) | Same (Slice 14 cache) |
| `__NEXT_DATA__` | **Present** | **Present** |
| `contests[]` length | **30** | **6** |
| Row arity / participant width | **41** / two participants width **32** (`len(row[0][0])` = `len(row[0][1])` = 32; all 30 rows) | **41** / two participants width **32** (all 6 rows) |
| `featuredGameData` | **Present** (`contestId` `09b97c19-df68-49c8-b3af-a154178f6c5e`) | **Present** (`contestId` `c55a65ce-2c9b-42eb-8fb8-01b6f657fc93`) |
| Fixture | `tests/fixtures/maxpreps/centennial/baseball-schedule-26-27.json` | `tests/fixtures/maxpreps/centennial/basketball-girls-schedule-26-27.json` |

**Pass/stop verdict:** **Pass.** Next.js `__NEXT_DATA__` with `contests[]` containing at least one row, row arity **41**, two participants width **32**. Baseball is the second-sport parser fixture. Later slices may use it. This does not reopen Slice 14/15 sports investigation and does not substitute basketball for baseball.

`pageProps.query` was **absent** as a key (not `null`); envelope `query` was taken from `__NEXT_DATA__.query`, matching the football/volleyball fixture style. `buildId` in this capture is `7e0e0dba-22c4d787` with a trailing newline in the JSON blob (same class of artifact as the volleyball Slice 14 fixture).
