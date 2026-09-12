# External beta testing

This document is for **beta testers** installing High School Sports Scores through HACS on real Home Assistant OS (or other) environments — without developer bind mounts, git checkouts, or npm on the Home Assistant host.

Published beta builds are **GitHub Releases** with the **`high_school_sports_scores.zip`** asset (version names like `0.1.0-beta.2`). Use normal HACS **Download** after adding the custom repository.

User-facing overview and limitations: [README](../README.md).

---

## Before you start

- Home Assistant **2025.8.0** or newer  
- HACS installed and working  
- A test school and at least one supported sport you can verify (Football, Baseball, Basketball, or Volleyball)

---

## 1. Add the custom repository

1. **HACS** → **Integrations**.  
2. Menu (⋮) → **Custom repositories**.  
3. Repository: `https://github.com/willbur83/hacs-highschoolscores`  
4. Category: **Integration**  
5. **Add**, then dismiss the dialog.

Optional link helper: [my.home-assistant.io custom repository link](https://my.home-assistant.io/create-link/?redirect=hacs_repository&owner=willbur83&repository=hacs-highschoolscores&category=integration).

---

## 2. Install the beta release

1. In **HACS** → **Integrations**, open **High School Sports Scores**.  
2. Use **Download** (first install) or **Redownload** (upgrade). HACS should install the latest GitHub Release (for example **`v0.1.0-beta.2`**).  
3. If **Download** fails with a commit hash (such as `e497188`) instead of a release tag, the GitHub Release may still be marked **pre-release** — that blocks default HACS install for this repo; use a release published without the pre-release flag or ask the maintainer to fix it.  
4. **Restart Home Assistant** when HACS requests it.

After install, the integration folder on disk should include **`www/high-school-sports-scores-card.js`** (bundled inside the release ZIP). You should **not** need to run npm on the Home Assistant machine.

Install a **published release** through HACS only. The development branch is not a supported end-user source (it does not ship the built card bundle).

---

## 3. Configure the integration

1. **Settings** → **Devices & services** → **Add integration** → **High School Sports Scores**.  
2. Search with a **short school name**; select the correct school from the list.  
3. Subscribe to at least one supported sport.  
4. Confirm program **sensors** appear under the school device (one entity per subscribed program).  
5. Open **Configure** on the integration entry to try **adding/removing** a sport and, optionally, a **school logo override**.

---

## 4. Verify the Lovelace card

1. Edit a dashboard → **Add card** → **High School Sports Scores**, bound to a program entity.  
2. Exercise all three modes if you can (dashboard YAML or UI card editor):
   - **`both`** (default): collapsed last/next, expand for full schedule.  
   - **`last_next`**: last/next only.  
   - **`schedule`**: full schedule only.  
3. **Restart Home Assistant** and confirm entities, integration config, and the card still work.

---

## 5. Upgrade between betas (if applicable)

When a newer beta pre-release is published:

1. **HACS** → **Integrations** → **High School Sports Scores** → **Redownload**.  
2. Select the newer pre-release version if it is not the default offer.  
3. Restart when prompted; confirm existing config entries and entities remain correct.

Report any broken upgrade path as a **release-blocking** issue.

---

## 6. Report findings

Open a [GitHub Issue](https://github.com/willbur83/hacs-highschoolscores/issues) using the **Bug report** template when something fails.

Include (sanitized):

- Home Assistant version  
- High School Sports Scores version (from HACS or integration **About**)  
- How you installed (custom repo + which release/pre-release you selected)  
- School / program / sport involved, if relevant  
- Expected vs actual behavior and steps to reproduce  
- A **short, redacted** log snippet if useful  

**Never include** private hostnames or IPs, full filesystem paths, compose files, secrets, tokens, cookies, or broad configuration dumps. See the issue template for the full list.

Cosmetic or “nice to have” items are fine to note but may be deferred; focus on install failures, missing card JS, config flow errors, wrong or missing data for supported sports, and card mode regressions.

---

## Coverage intent

The project aims for meaningful validation across **multiple independent** Home Assistant OS (or equivalent) installs and schools. If you cannot finish testing, say so in your issue or a short comment so coverage can be planned explicitly — silent drop-off is not assumed as PASS.
