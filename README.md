# High School Sports Scores

A Home Assistant custom integration and optional Lovelace card for high school sports schedules and final scores from publicly available MaxPreps data.

> **Status:** Pre-release development. The first public beta has not been published yet.

High School Sports Scores is an independent, open-source Home Assistant integration and is not affiliated with, endorsed by, sponsored by, or associated with MaxPreps. The integration retrieves publicly available sports schedule and score data from MaxPreps.com. MaxPreps remains the original source of that data. Users are encouraged to visit and support MaxPreps and the services they provide to high school sports communities.

**Requirements:** Home Assistant **2025.8.0** or newer and [HACS](https://hacs.xyz/docs/setup/download) (Home Assistant Community Store).

---

## Installation (HACS custom repository)

This project is **not** in the HACS default store. Install it by adding a **custom repository**, then downloading a **published GitHub Release** through HACS.

When the first beta is published (see [Beta testing](docs/BETA.md)), the supported path is:

1. In Home Assistant, open **HACS** → **Integrations**.
2. Open the menu (⋮) → **Custom repositories**.
3. Add repository **`https://github.com/willbur83/hacs-highschoolscores`**, category **Integration**, then **Add**.
4. Find **High School Sports Scores** in HACS → **Integrations** → **Download** (or **Redownload** when upgrading).
5. Choose the **release version** you want (beta/pre-release versions are not selected by default — see [docs/BETA.md](docs/BETA.md)).
6. **Restart Home Assistant** when HACS prompts you to.

Optional shortcut to add the custom repository on a phone or tablet: [Create my.home-assistant.io link](https://my.home-assistant.io/create-link/?redirect=hacs_repository&owner=willbur83&repository=hacs-highschoolscores&category=integration).

Install a **published release** through HACS. The development branch does not contain the built Lovelace card bundle and is **not** a supported end-user installation source. Release ZIPs attach **`high_school_sports_scores.zip`** (see [`hacs.json`](hacs.json)).

**Developers:** bind-mount, Core container pins, npm builds, and CI are documented in [docs/HA_DEVELOPMENT.md](docs/HA_DEVELOPMENT.md) — not in this README.

---

## First-time setup

1. **Settings** → **Devices & services** → **Add integration**.
2. Search for **High School Sports Scores** and start the flow.
3. **Find your school:** enter a **short school name** (for example `Centennial`). Avoid long qualified strings such as `Centennial High School, Roswell GA` — they often return no results on MaxPreps.
4. Pick your school from the disambiguated list (school name, city, and state when available).
5. Subscribe to one or more **supported sports** (see below). You can add or remove sports later.

**Options (per school):** open the integration’s **Configure** entry to add/remove subscribed sports and optionally set a **school logo override** (HTTPS image URL or a `/local/` path). Leave the override blank to use the automatic school logo from MaxPreps when available.

Each school is a **separate** config entry. Adding the integration again configures another school.

---

## Supported sports

Only formats validated against real MaxPreps data are offered in the picker:

| Sport        | Supported |
|-------------|-----------|
| Football    | Yes       |
| Baseball    | Yes       |
| Basketball  | Yes       |
| Volleyball  | Yes       |

Sports outside the currently supported list are **omitted** from the subscription picker until their MaxPreps schedule format has been validated. They are not shown as disabled choices.

**School year:** schedules use the July 1–June 30 school year in Home Assistant’s configured local timezone. Subscriptions stay stable across rollover; until MaxPreps publishes the new year, the integration keeps the last good data and polls less often (see limitations).

---

## Lovelace card

After a **GitHub Release** install, the card JavaScript is included in the ZIP — **no npm build** on your Home Assistant host.

1. Edit a dashboard → **Add card**.
2. Choose **High School Sports Scores** from the card picker (recommended when you already have program sensors), **or** add manually in YAML/raw configuration.

Card type:

```yaml
type: custom:high-school-sports-scores-card
entity: sensor.<your_program_entity>
```

Optional **`mode`**:

| Mode | Behavior |
|------|----------|
| `both` (default) | Collapsed last/next games; expand for the full current school-year schedule. |
| `last_next` | Last/next only; no full schedule panel. |
| `schedule` | Full schedule only. |

Collapsed last/next reads entity attributes. Expanded and schedule-only views load the full schedule through the integration’s websocket API while the card is visible.

---

## Known limitations

- **Game dates and times:** Values from the provider do not include reliable timezone information. High School Sports Scores shows the provider’s date and time **without** converting them to an absolute local kickoff time. Do not rely on them for precise “game starts in 30 minutes” automations or countdowns.
- **Game status:** Live or in-progress games are **not** supported today. Program entities use compact status **`scheduled`**, **`final`**, or **`unknown`** based on the last coordinator refresh — not a live scoreboard.
- **Update frequency:** Normal refresh is about **every 12 hours**. While waiting for a **new school year** to appear on MaxPreps, polling slows to about **once per day** until schedules are published again.

One subscribed sport failing to load does not remove your other sports for that school. Entry-wide discovery failures keep the last successful snapshot when possible.

---

## Troubleshooting

| Symptom | What to try |
|--------|-------------|
| Card missing after **git clone** | Expected. End users should install a **GitHub Release** via HACS so `www/high-school-sports-scores-card.js` is on disk. Developers build the frontend locally — see [docs/HA_DEVELOPMENT.md](docs/HA_DEVELOPMENT.md). |
| School search returns nothing | Use a **short** name; pick from the result list. Try alternate spelling or a nearby city name if your school shares a common name. |
| Entities stale or `unknown` | Wait for the next coordinator refresh (\~12h, or daily during new-year wait). If data still appears stuck, try **Reload** on the integration. Restart Home Assistant after installing or upgrading the integration when HACS prompts you to. |
| HACS download fails or no release listed | The first beta may not be published yet, or you need to select a **release version** (including pre-release). Do not install from the development branch — use a GitHub Release ZIP. Watch [GitHub Releases](https://github.com/willbur83/hacs-highschoolscores/releases). |
| Wrong or missing logo | Options → optional **school logo override**, or leave blank for automatic MaxPreps logo when available. Missing logos never block scores. |

Check **Settings** → **System** → **Logs** for errors mentioning `high_school_sports_scores` after a restart.

---

## Beta feedback and issues

Pre-release testing steps: [docs/BETA.md](docs/BETA.md).

Report bugs and feedback on [GitHub Issues](https://github.com/willbur83/hacs-highschoolscores/issues). Use the bug report template when possible.

**Do not paste** into public issues:

- Private hostnames, internal IP addresses, or VPN-only URLs  
- Full paths like `/home/...` or operator paths such as `/srv/...` (sanitize or redact)  
- Docker Compose files, secrets, API tokens, cookies, or `.storage` dumps  
- Unrelated Home Assistant configuration  

A short, redacted log excerpt around the error is enough — not a full unredacted diagnostics export.

---

## Development

Contributors and integration developers: [docs/HA_DEVELOPMENT.md](docs/HA_DEVELOPMENT.md) (test layers, version pins, release ZIP layout, bind-mount sandbox).

Product behavior and open product questions: [docs/PRODUCT.md](docs/PRODUCT.md).

Source: [github.com/willbur83/hacs-highschoolscores](https://github.com/willbur83/hacs-highschoolscores)

---

## License

This project is licensed under the [MIT License](LICENSE). MIT applies to **this repository’s source code** only. It does **not** grant rights to MaxPreps content, trademarks, imagery, or other provider-owned material.
