---
name: rosey-maintainer-automations
description: >-
  Restore live Cursor Automations at cursor.com to fleet-correct saved state:
  create if missing, then set every header, trigger, tool, model, and Agent
  Instructions knob. Use when the user asks to update, sync, check, paste,
  restore, or recreate fleet Cursor automations, PR CI fixes, or Rosey PR fix
  (@cursor), after they have logged in at https://cursor.com/automations.
argument-hint: "[all | automation name]"
---

# Rosey Maintainer Automations

Restore each catalog automation in the live Cursor Automations UI to the
**fleet-correct saved state**. Treat the editor as arbitrarily mutated: every
knob may be wrong, extra, or missing. After this skill, the saved page must
match the expected profile — not “mostly right.”

There is no API to patch existing automations. Drive the browser tab the user
already opened.

Inventory source (2026-08-12): adding a GitHub **Checks completed** trigger
always replaces the header repo/branch/Cloud chips with the locked span
**Repository from Git Trigger**. Fleet consistency is that locked header on
**every** catalog row. The catalog **Owner/slug** is chosen on the trigger
`in` picker, not in the header. **Rosey PR fix (@cursor)** uses the comment
profile for trigger type and multi-repo `in` — do not apply the
Checks-completed checklist to it.

## Communication

**Caveman lite** for status while this skill runs. Drop lite for login walls,
irreversible deletes of the **automation itself**, or user confusion.

## Prerequisite (hard stop)

The user **must** already:

1. Open a Cursor browser tab
2. Authenticate to Cursor
3. Land on **https://cursor.com/automations** (logged-in Automations list:
   **Mine**, **New Automation**, search box)

If the tab is a login wall, SSO, or any URL other than the Automations app,
**stop**. Tell the user to log in and open that URL, then re-run. Do **not**
type credentials. Do **not** `browser_navigate` to a login URL.

## Workspace

Run from **rosey-maintainer-tools** (or resolve that folder in the multi-root
workspace). Instruction files:

`docs/cursor-automations/<file>.md`

If those files are missing, stop.

## Catalog

Match live UI **Name** to the doc. Names are exact (copy from each file’s
`**Cursor automation name:**`).

The live chip often shows **slug only**, but the picker menuitem is
`{slug} {owner}` (e.g. `wholmaster CollageLabs`). Restore must match
**owner + slug**, not slug alone — leftover `LuisAlejandro/{slug}` after a
move to CollageLabs is the wrong repo.

**by** users are GitHub **PR authors**, not the repo owner.

| Live name | Doc | Owner | Repo slug | Branch | **by** users |
|-----------|-----|-------|-----------|--------|--------------|
| `Agoras PR CI fixes` | `docs/cursor-automations/agoras.md` | `LuisAlejandro` | `agoras` | `develop` | `LuisAlejandro`, `dependabot[bot]` |
| `Agoras Actions PR CI fixes` | `docs/cursor-automations/agoras-actions.md` | `LuisAlejandro` | `agoras-actions` | `develop` | `LuisAlejandro`, `dependabot[bot]` |
| `Dockershelf PR CI fixes` | `docs/cursor-automations/dockershelf.md` | `Dockershelf` | `dockershelf` | `develop` | `Dockershelf`, `dependabot[bot]` |
| `Spices PR CI fixes` | `docs/cursor-automations/spices.md` | `LuisAlejandro` | `spices` | `develop` | `LuisAlejandro`, `dependabot[bot]` |
| `Helpmarket PR CI fixes` | `docs/cursor-automations/helpmarket.md` | `CollageLabs` | `helpmarket` | `develop` | `LuisAlejandro`, `dependabot[bot]` |
| `luisalejandro.org PR CI fixes` | `docs/cursor-automations/luisalejandro.org.md` | `LuisAlejandro` | `luisalejandro.org` | `develop` | `LuisAlejandro`, `dependabot[bot]` |
| `Morphile PR CI fixes` | `docs/cursor-automations/morphile.md` | `CollageLabs` | `morphile` | `develop` | `LuisAlejandro`, `dependabot[bot]` |
| `Nuncia PR CI fixes` | `docs/cursor-automations/nuncia.md` | `CollageLabs` | `nuncia` | `develop` | `LuisAlejandro`, `dependabot[bot]` |
| `Whol PR CI fixes` | `docs/cursor-automations/whol.md` | `CollageLabs` | `whol` | `develop` | `LuisAlejandro`, `dependabot[bot]` |
| `Wholmaster PR CI fixes` | `docs/cursor-automations/wholmaster.md` | `CollageLabs` | `wholmaster` | `develop` | `LuisAlejandro`, `dependabot[bot]` |
| `Wholmaster Website PR CI fixes` | `docs/cursor-automations/wholmaster-website.md` | `CollageLabs` | `wholmaster-website` | `develop` | `LuisAlejandro`, `dependabot[bot]` |
| `Frontdesk PR CI fixes` | `docs/cursor-automations/frontdesk.md` | `LuisAlejandro` | `frontdesk` | `master` | `LuisAlejandro`, `dependabot[bot]` |
| `Rosey PR fix (@cursor)` | `docs/cursor-automations/fleet-fix-comment.md` | each catalog owner | multi-repo | n/a | comment profile |

Default: process **every** catalog row. If `$ARGUMENTS` names one automation,
process only that row.

Skip UI rows that are not in this catalog (Bugbot, Security Agents, templates,
unrelated automations). If a **catalog** row is missing from **Mine**,
**create it** (see **Create missing automation**), then restore.

Two different CollageLabs rules — do not mix them:

- **Repo picker** (trigger `in` only — not the header): CollageLabs apps
  **must** be `CollageLabs/{slug}`. If `LuisAlejandro/{slug}` is still
  selected (pre-move leftover), **deselect** it and select
  `CollageLabs/{slug}`. Example: deselect `wholmaster LuisAlejandro`,
  select `wholmaster CollageLabs`.
- **by picker** (PR authors): still **LuisAlejandro** + `dependabot[bot]`.
  Never add **CollageLabs** as a **by** user — the org cannot open PRs.

The catalog **Branch** column is the PR base in the instruction doc
(`develop`, Frontdesk `master`). It is **not** a live header chip under
this contract.

## Restore contract (mandatory)

Assume a child flipped every control and saved, **or deleted the automation**.
Running this skill must put it back. **Create if missing. Add missing knobs.
Remove extras. Retune chips. Paste instructions. Save. Re-inventory until the
saved page matches. Then Test run on each single-repo PR-CI row.

Do not stop at “chips look close” or “extra trigger recorded, left in place.”
An extra trigger, extra tool, wrong model, disabled Active switch, wrong
name, extra GitHub username, a header that is **not** locked to
**Repository from Git Trigger**, the **wrong owner** on trigger `in` for
the same slug (e.g. `LuisAlejandro/wholmaster` instead of
`CollageLabs/wholmaster`), or a catalog row **absent from the list** is a
**failed restore**.

Loop per row:

1. Inventory (CDP + snapshot).
2. Diff against the expected profile for this row.
3. Apply every fix in **Restore order**.
4. Click **Save** if enabled. Wait until the label is **Save** and **disabled**.
5. Re-inventory. If anything still mismatches, go to step 3.
6. When inventory matches, run **Test run after Save** (PR-CI single-repo only).
   If the test fails, troubleshoot, then return to step 3.

Cap: **four** restore cycles. Then record **blocked** with the remaining
diff, skip that row, continue the rest.

Stay on tab **Settings** except while the **Run Test** dialog is open.
A **passed** test navigates to **Run History** (`/runs`) — that is expected.
Do **not** click **Stop All Runs**. After recording pass/fail, go back to
the list (`https://cursor.com/automations`) before the next row.

## Expected UI (PR CI rows)

Every `{Repo} PR CI fixes` row must match this shape, with catalog owner /
slug / **by** substituted. Header is the same locked Git-trigger span on
every catalog row. The repo is the trigger `in` chip.

### Header

| Control | Expected | How it appears / restore |
|---------|----------|--------------------------|
| Name | Catalog live name | Button `Edit automation name: …`. If wrong, click it, replace with the catalog name, confirm. |
| Enabled | **Active** | Switch `Toggle automation enabled state` **checked**. If unchecked, click it so it is checked. |
| Environment target | **Repository from Git Trigger** | Locked `span.automations-header-target-locked-label` (title `Use the repository that triggers the automation`). Branch and Cloud chips are **gone**. Snapshot omits header repo/branch/Cloud buttons. |
| Author line | informational | `By Luis Alejandro Martínez Faneyth` — do not edit. |

The catalog **Owner + slug** is **not** a header chip. It is the trigger
`in` picker (see **Triggers**).

**Failed restore:** header shows three buttons (slug, branch, **Cursor
Cloud**) or **Select repository** instead of the locked span. Do **not**
Remove trigger to bring those chips back — that is the discarded contract.

**How the lock is the desired state:** Recents in the header picker includes
menuitem **Repository from Git Trigger**. Selecting it, adding a GitHub
Checks completed trigger, or leaving **zero** explicit header repos, swaps
the three chips for that locked span. Fleet restore **wants** that span.

Do **not**:

- Pick `{slug} {owner}` (or `a1apps1 LuisAlejandro`, **No Repository**) in
  the **header** picker — the catalog repo belongs on trigger `in`
- Click the locked span — it is not a picker (`cursor: auto`, no
  `aria-haspopup`, no onClick)
- Remove trigger solely to “unlock” the header

`browser_click` on a repo `menuitem` usually **focuses** it. It does **not**
set `data-selected`. Press **Enter**, then CDP-check `data-selected` before
Escape.

**Header picker** (click **Select repository** or the first repo **button** —
only exists when the header is **not** locked):

- Search box: `Search repositories and environments` (`placeholder: Search repositories, environments...`).
- Recents includes **Repository from Git Trigger**. That is the **only**
  header menuitem to select for catalog rows.
- Do not click the first unfiltered Recents repo (often `a1apps1
  LuisAlejandro`). Do not click **No Repository**.
- Footer: **+ Add Repositories** / Refresh — do not click from the header
  picker (connect missing repos from trigger `in` if needed).
- Restore when chips or **Select repository** are visible:
  1. Open the header picker.
  2. Click menuitem **Repository from Git Trigger**, then **Enter**.
  3. Confirm the locked span **Repository from Git Trigger**. Branch and
     Cloud chips must be gone.
- If the span is already visible, skip the header picker. Set the repo on
  trigger `in`.

Adding **Checks completed** while the header is **Select repository** also
produces the locked span. That is OK. Then set trigger `in` to
`{slug} {catalog owner}`.

### Triggers

Exactly **one** trigger. Visible sentence:

`Checks completed` `in` `{slug}` `On Failure` `On PRs` `by` `2 people` `Ignoring Failures on Main`

| Chip | Expected | Wrong values (fix) |
|------|----------|--------------------|
| Event | **Checks completed** (static text, not a button) | Missing → **Add expected trigger**. Wrong type → **Remove** that row, then add Checks completed. |
| `in` repo | Catalog **Owner** + slug — **this is the repo selector** | Open the chip (`Select Repos` / slug / `N repositories`). Pick `{slug} {catalog owner}`. Deselect leftover `{slug} {old owner}` and any extra repos until one remains. Search the slug if needed. Do not pick Recents **Repository from Git Trigger** here. |
| Outcome | **On Failure** | Menu: `On Failure` / `On Success` / `On Any Completion` |
| Scope | **On PRs** | Menu: `On PRs` / `On Branch` |
| `by` | **2 people** = both catalog **by** users, **only** those two | Extra usernames → **Remove {username}**. Missing → add via the textbox. |
| Main policy | **Ignoring Failures on Main** | Menu: `Ignoring Failures on Main` / `Including Failures on Main` |

**Extra triggers:** every trigger row that is not this Checks-completed row
must be deleted. Click that row’s **Remove trigger**. Confirm the Triggers
section has exactly one **Remove trigger** button and the sentence above.

**by** picker (click `2 people` / `by Me` / `by N people`):

- Expected selected users show as `Remove LuisAlejandro` and
  `Remove dependabot[bot]` (Dockershelf: `Remove Dockershelf` +
  `Remove dependabot[bot]`).
- Any other `Remove {name}` is extra — click it to drop that user.
- Textbox: `Add GitHub username`. Type the missing username and add it.
- Do **not** click **Reset** (clears the list; you would have to rebuild).
- Dismiss with Escape after verifying. Overlay `ui-menu__backdrop` blocks
  other clicks until closed.

### Agent Instructions

Contenteditable `[contenteditable="true"]` must equal the **entire** matching
doc file (do not strip headings).

Model button under the editor: **Composer 2.5**.

**Model picker** (click the model chip):

- Search box: `Search menu items` (`placeholder: Search models`).
- Visible items include `Composer 2.5`, plus others (`Cursor Grok 4.6 High Fast`,
  `GPT-5.6 Sol Medium`, …). Search `Composer 2.5` if the list is long.
- Click menuitem **Composer 2.5**. Escape if the menu stays open.
- Chip name must be `Composer 2.5`.

### Tools

Allow-list (order as inventoried). Anything else is extra and must be removed.

| Tool | Expected | Signals |
|------|----------|---------|
| **Open Pull Request** | On | `Remove Open Pull Request` present. Add-menu item reads `Open Pull Request Added` |
| **Memories** | On | `Remove Memories` + **Manage**. Add-menu: `Memories Added` |
| **Comment on Pull Request** | On, **Don't Allow PR Approval** | Menu: `Don't Allow PR Approval` (checked) / `Allow PR Approval` |
| **GitHub** MCP | **Connected** | Row label `GitHub`, buttons **Disconnect**, **Edit MCP server**, **Remove MCP server** |

**Remove extras:** if a row exists for **Request Reviewers**, Slack, Teams, or
any other non-allow-list tool, click that row’s `Remove …` control (trash).
Never use **Remove MCP server** to drop GitHub when GitHub is the expected MCP.

**GitHub MCP:** if **Disconnect** is visible, the MCP is connected — leave it.
Never click **Disconnect**, **Edit MCP server**, or **Remove MCP server** on a
connected GitHub row. If GitHub is **missing**, add via **Add Tool or MCP** →
**MCP Server** and complete connect if the UI requires it (do not type
credentials; if an OAuth wall appears, stop that step and tell the user to
finish GitHub MCP auth, then re-run). Do not disconnect afterward.

Add-menu labels when opening **Add Tool or MCP**: `Memories`, `MCP Server`,
`Send to Slack`, `Read Public Slack Channels`, `Send to Microsoft Teams`,
`Read Microsoft Teams Channels`, `Open Pull Request`, `Comment on Pull Request`,
`Request Reviewers`. Items already on show `Added`. Click only missing
allow-list items (not Slack/Teams/Request Reviewers).

## Expected UI (comment row)

`Rosey PR fix (@cursor)` only:

| Field | Expected |
|-------|----------|
| Name | `Rosey PR fix (@cursor)` |
| Enabled | **Active** |
| Trigger | Exactly one: **Comment added** (PR conversation comments). Live add-menu: **`GitHub > Comment added`**. |
| Repository | Header: locked **Repository from Git Trigger** (same as PR-CI). Trigger repos: every catalog **Owner/slug** (CollageLabs apps under CollageLabs, personal under LuisAlejandro, Dockershelf under Dockershelf). Deselect leftover `LuisAlejandro/{slug}` when the catalog owner is CollageLabs. Do **not** put those repos in the header picker. |
| Model | **Composer 2.5** |
| Tools | Same allow-list as PR CI: Open PR, Memories, Comment on PR + **Don't Allow PR Approval**, GitHub MCP **connected**. Remove extras. |
| Instructions | Entire `docs/cursor-automations/fleet-fix-comment.md` |

Do **not** require `On Failure` / `On PRs` / `Ignoring Failures on Main` /
`by 2 people` on this row.

If a Checks-completed (or any other) trigger is present, **Remove trigger**
on those rows. If Comment added is missing, add it (see **Add expected
trigger**). Do not use `GitHub > GitHub Only > PR review comment` or
`GitHub > GitHub Only > PR review submitted > Comment ed`.

## Create missing automation

Inventoried 2026-08-12: **New Automation** on the list page **immediately
creates** a persisted editor at `/automations/<uuid>` (even before Save).
Do not use gallery templates.

Wait until the list is loaded: **New Automation** button + **Mine** tab
(the first paint is often a spinner). Stay on **Mine**, not Team.

1. Clear the **Search...** box if it still has a previous query.
2. `browser_fill` **Search...** with the catalog live name.
3. Confirm absence: no list row / `a[href*="/automations/"]` whose visible
   name equals the catalog name. A search miss is not enough if search is
   stale — clear and search once more.
4. Click **New Automation** (top right). Do **not** click **Get Started**,
   Bugbot / Security banners, or **Use … template** (`Use Find critical bugs
   template`, `Use Scan codebase for vulnerabilities template`,
   `Use Generate docs template`, `Use Add test coverage template`).
5. Wait until URL is `/automations/<uuid>` and the name button is
   `Edit automation name: Untitled`.
6. Blank-editor defaults (all wrong vs fleet — restore all of them):

   | Control | New-automation default |
   |---------|------------------------|
   | Name | **Untitled** |
   | Enabled | **Inactive** (switch unchecked) |
   | Repository | **Select repository** (no branch / Cloud chips yet) — restore to **Repository from Git Trigger**, not a catalog slug |
   | Triggers | empty (`Add Trigger` only) |
   | Instructions | empty (`Type @ for tools, / for commands...`) |
   | Model | **Cursor Grok 4.6 High Fast** (not Composer 2.5) |
   | Tools | **Memories** only |

7. Run **Restore order** on this editor (name, Active, header **Repository
   from Git Trigger**, expected trigger with `in` = catalog owner+slug,
   Composer 2.5, allow-list tools + GitHub MCP, paste doc, Save).
8. Re-inventory until it matches. Record **created**.

If create is abandoned before the catalog name is saved: **More actions** →
**Delete** → confirm (Enter if Delete is focused). Toast: `Agent deleted
successfully`. Only delete an **Untitled** draft created in **this run**.
Never Delete a named catalog automation.

## Restore order

Apply in this order so overlays do not fight each other. **Escape** after
every menu before the next click.

1. **Name** — catalog live name.
2. **Active** — switch checked.
3. **Header** — locked span **Repository from Git Trigger**. If three chips
   or **Select repository** are visible, open the header picker and select
   Recents **Repository from Git Trigger** (Enter). Adding the expected
   GitHub trigger also locks the header — that is OK. Never pick
   `{slug} {owner}` in the **header**. Comment row: same locked header.
4. **Triggers** — remove every extra row; add the expected event if missing;
   set remaining chips. PR-CI `in` = exactly one catalog `{slug} {owner}`.
   Comment row `in` = every catalog owner/slug pair.
5. **Model** — **Composer 2.5**.
6. **Tools** — add missing allow-list tools; remove every non-allow-list row;
   set Comment on PR to **Don't Allow PR Approval**; add GitHub MCP only if
   missing.
7. **Instructions** — paste the entire doc if the editor text differs.
8. **Save** — click if enabled; wait until **Save** is disabled.
9. **Re-inventory** — if any expected field still mismatches, repeat from
   the first failing step.
10. **Test run** — PR-CI single-repo only (see **Test run after Save**).

## Add expected trigger

Inventoried 2026-08-12 on Agoras Actions: **Add Trigger** → `Search Triggers...`
(do **not** click the **GitHub** parent — it collapses instead of expanding).

**PR CI rows** (only when `Checks completed` is absent):

1. Click **Add Trigger**.
2. `browser_fill` the **Search menu items** box (`placeholder: Search Triggers...`)
   with `Checks completed`.
3. Click the menuitem named exactly **`GitHub > GitHub Only > Checks completed`**.
   That click **adds** the trigger — do not click it if Checks completed already
   exists.
4. Escape if the menu stays open. Wait until **Remove trigger** exists and
   trigger text includes `Checks completed`.
5. Set chips to catalog values (`in` = `{slug} {catalog owner}`, **On Failure**,
   **On PRs**, **by** both users, **Ignoring Failures on Main**). New rows
   often default to **Select Repos** and **by Anyone** / **by Me** — open
   `in` and pick the catalog owner+slug; open the people picker and add the
   missing username(s). Header should now be the locked Git-trigger span.

**Comment row** (only when Comment added is absent):

1. Click **Add Trigger**.
2. Search `Comment` (full phrase `Comment on pull request` returns **No triggers found**).
3. Click **`GitHub > Comment added`**.

## Never click

These destroy the automation or undo a correct MCP connection. They are **not**
part of restore:

- **More actions** → **Duplicate**, **Copy as JSON**
- **More actions** → **Delete** on a **named catalog** automation (Delete is
  allowed only for an **Untitled** draft created this run that you must
  abandon — see **Create missing automation**)
- **Disconnect**, **Edit MCP server**, **Remove MCP server** on a connected
  GitHub row
- **Reset** in the people picker
- The **GitHub** parent menuitem in Add Trigger (use search instead)
- Login / SSO fields
- **Test run** on **Rosey PR fix (@cursor)** / **On Demand PR fix** (multi-repo,
  not bound to one repository — the Run Test dialog has no usable repo)
- Recents menuitem **Repository from Git Trigger** in the **trigger `in`**
  picker (header Recents is the correct place for that item)
- Picking a catalog `{slug} {owner}` in the **header** picker (use trigger
  `in` instead)
- **Stop All Runs** on Run History (kills the test you just started)
- Gallery **Use … template** / Bugbot **Get Started** when creating a fleet row

**Remove trigger** and tool **Remove …** (trash) **are required** for extras.
That is restore, not “delete the automation.”

## Browser procedure

Discover schemas with `GetMcpTools` before `CallMcpTool`. Use `cursor-ide-browser`.

1. `browser_tabs` `list`. Prefer the tab already on `https://cursor.com/automations`.
2. `browser_lock` `{ action: "lock" }` on that tab **before** any other interaction.
3. `browser_snapshot`. Confirm logged-in list (not login). If not, unlock and stop.
4. For each catalog row (or the one named in `$ARGUMENTS`):
   1. `Read` the doc file. The **entire file** is the prompt to paste.
   2. On the list page, `browser_fill` the **Search...** box with the live name.
   3. Confirm the row exists (`Runtime.evaluate` on `document.body.innerText` /
      `a[href*="/automations/"]` with the exact live name). After search, the
      interactive snapshot often **omits** the row link — CDP `a[href]` is
      the source of truth. If missing, run
      **Create missing automation**, then continue from Inventory on the new
      editor (do not skip restore).
   4. If the row already exists, open the editor: `browser_navigate` to the
      row’s `/automations/<uuid>` URL (from the `a[href]`). Do not guess UUIDs.
   5. Wait until **Save** exists (poll `Runtime.evaluate`; the first snapshot
      after navigate is often empty/busy). Confirm tab **Settings** is selected.
      New Untitled editors have an empty instructions box — that is expected.
   6. Run **Inventory**. Diff against the expected profile.
   7. Run **Restore order** until inventory matches or four cycles are exhausted.
      Dismiss menus with **Escape** before the next click (`ui-menu__backdrop`
      intercepts otherwise).
   8. When inventory matches, run **Test run after Save**. If it fails,
      troubleshoot (restore again if chrome drifted), then re-test.
   9. Record **ok** / **restored** / **created** / **blocked** plus test
      **passed** / **failed** / **skipped**. If the tab is on `/runs`, that is
      a passed test — do not click **Stop All Runs**. Navigate back to
      `https://cursor.com/automations` before the next row (clear search if it
      persists).
5. `browser_lock` `{ action: "unlock" }` when **all** rows are done (or on hard stop).

If four restore cycles fail on one row, record **blocked** with the remaining
diff, skip that row, continue the rest.

### Inventory (CDP)

`browser_cdp` `Runtime.evaluate` with `returnByValue: true`:

```javascript
(() => {
  const txt = document.body.innerText || "";
  const nameBtn = document.querySelector('[aria-label^="Edit automation name"]');
  const enabled = document.querySelector('[aria-label="Toggle automation enabled state"]');
  const buttons = [...document.querySelectorAll("button")].map((b) =>
    (b.getAttribute("aria-label") || b.innerText || "").trim()
  );
  const trigger = (txt.match(/Triggers[\s\S]*?Add Trigger/) || [""])[0];
  const tools = (txt.match(/Tools[\s\S]*?Add Tool or MCP/) || [""])[0];
  const removeTriggerCount = buttons.filter((t) => t === "Remove trigger").length;
  const extraToolRemoves = buttons.filter((t) =>
    /^Remove /.test(t) &&
    !/Remove Open Pull Request|Remove Memories|Remove Comment on Pull Request|Remove MCP server|Remove trigger/.test(t)
  );
  const envHeader = document.querySelector(".automations-environment-header");
  const locked = document.querySelector(".automations-header-target-locked-label");
  const headerBtns = [...(envHeader?.querySelectorAll("button") || [])].map((b) => ({
    text: (b.innerText || "").trim(),
    title: b.getAttribute("title") || "",
    aria: b.getAttribute("aria-label") || "",
  }));
  const cloudChip = headerBtns.some((b) =>
    /Cursor Cloud/.test(`${b.title} ${b.aria} ${b.text}`)
  );
  return {
    url: location.href,
    name: nameBtn ? nameBtn.innerText.trim() : null,
    active: enabled ? enabled.getAttribute("aria-checked") : null,
    trigger,
    tools,
    removeTriggerCount,
    extraToolRemoves,
    hasDisconnect: buttons.includes("Disconnect"),
    hasOpenPR: buttons.some((t) => t.includes("Remove Open Pull Request")),
    hasMemories: buttons.some((t) => t.includes("Remove Memories")),
    hasComment: buttons.some((t) => t.includes("Remove Comment on Pull Request")),
    approval: buttons.includes("Don't Allow PR Approval")
      ? "Don't Allow PR Approval"
      : buttons.includes("Allow PR Approval")
        ? "Allow PR Approval"
        : null,
    model: buttons.includes("Composer 2.5") ? "Composer 2.5" : buttons.find((t) => /Composer|GPT|Opus|Sonnet|Grok/i.test(t)) || null,
    headerLocked: locked ? (locked.innerText || "").trim() : null,
    headerRepoChip: headerBtns.map((b) => b.text).find((t) => t && t !== "develop" && t !== "master") || null,
    headerBranchChip: headerBtns.map((b) => b.text).find((t) => t === "develop" || t === "master") || null,
    env: cloudChip ? "Cursor Cloud" : (locked ? "Repository from Git Trigger" : null),
    saveDisabled: !![...document.querySelectorAll("button")].find((b) => b.innerText.trim() === "Save" && b.disabled),
  };
})();
```

Then snapshot. For **by** users, click the people chip and confirm `Remove …`
buttons for **exactly** the expected usernames; Escape when done.

PR-CI success: `removeTriggerCount === 1`, trigger text matches the Checks
completed sentence, `extraToolRemoves` is empty, `active === "true"`, model
`Composer 2.5`, `headerLocked === "Repository from Git Trigger"`,
`env === "Repository from Git Trigger"`, header repo/branch/Cloud chips
absent (`headerRepoChip` / `headerBranchChip` / Cloud button all null),
approval `Don't Allow PR Approval`, `hasDisconnect` true, name equals
catalog, trigger `in` picker shows catalog `{slug} {owner}` selected (not
the pre-move owner). Three header chips (slug, branch, Cloud) is a **miss**
— select **Repository from Git Trigger** in the header picker (or add
Checks completed, then set `in`).

The locked span is the environment target. Do not treat missing Cloud /
branch chips as a failure.

Trigger `in` vs header: the slug chip after `Checks completed in` is the
repo. Open that picker to confirm `{slug} {catalog owner}` is
`data-selected`. The closed chip may still read `wholmaster` while
`LuisAlejandro` is selected. The header span is not a substitute for a
correct `in` selection, and a correct `in` does not require header chips.

### Fixing a dropdown

1. Fresh snapshot. Click the chip whose **name** is the current (wrong or right) value.
2. Click the `menuitem` with the expected label, then **Enter** for repo
   pickers (click often only focuses). Do not click a nearby wrong item
   (`On Branch`, `On Success`, `Including Failures on Main`, `Allow PR Approval`,
   a feature branch, a non-Composer model, `{slug} LuisAlejandro` when the
   catalog owner is CollageLabs, `{slug} {owner}` in the **header** picker,
   Recents **Repository from Git Trigger** in the **trigger `in`** picker,
   the first unfiltered Recents repo).
3. For repo pickers, CDP-check `data-selected` before Escape. Escape if the
   menu stays open. Confirm the chip **name** is now the expected label.
   After locking the header, confirm the span **Repository from Git Trigger**
   and that trigger `in` still has the catalog owner+slug.

### Paste (this SPA)

`browser_fill` on the instructions editor is **unreliable** (stale refs). Use this instead:

1. Click the instructions **textbox** (ref from a **fresh** snapshot; `element`
   must match the snapshot name).
2. `browser_cdp` `Runtime.evaluate` with `returnByValue: true`:

```javascript
(() => {
  const el = document.querySelector('[contenteditable="true"]');
  if (!el) return { ok: false, reason: "no editable" };
  el.focus();
  const sel = window.getSelection();
  const range = document.createRange();
  range.selectNodeContents(el);
  sel.removeAllRanges();
  sel.addRange(range);
  const text = PROMPT_JSON; // JSON.stringify of the full doc
  const ok = document.execCommand("insertText", false, text);
  el.dispatchEvent(new InputEvent("input", { bubbles: true, data: text, inputType: "insertText" }));
  return { ok, len: el.innerText.length };
})();
```

Build the expression so `PROMPT_JSON` is a JSON-quoted string (markdown
backticks must not break JS). Confirm `ok === true` and length is in the
expected range.

Do **not** use CDP `Input.*` methods.

After insert, snapshot: **Save** must **not** be disabled. Click **Save**.
Poll until **Saving...** is gone.

## Test run after Save

Inventoried 2026-08-12 on **Agoras Actions PR CI fixes** (single-repo). Do
**not** click Test run on **Rosey PR fix (@cursor)** / **On Demand PR fix**:
that row is multi-repo (trigger `in` lists every catalog owner/slug) and the
Run Test dialog has no bound repository.

After inventory matches and **Save** is **disabled**:

1. Click **Test run** — topbar ghost play button **next to Save**.
   Snapshot name: **Test run**. Selectors: `button[aria-label="Test run"]`,
   `data-vr="form-test"`. Do **not** use generated ids (`base-ui-_r_*`).
2. Clicking can flash **Saving...** and disable Test run. Wait until **Save**
   is **Save** + disabled and Test run is enabled. If no dialog yet, click
   Test run again.
3. Wait for dialog **Run Test** (`role="dialog"`, heading **Run Test**).
   Readonly fields:
   - **Trigger** — `Checks completed`
   - **Repository** — `https://github.com/{owner}/{slug}` matching the catalog
     (Agoras Actions: `https://github.com/LuisAlejandro/agoras-actions`)
   - **PR Number** — textbox placeholder `e.g., 123` (ref name **e.g., 123**)
   Footer: **Cancel**, **Run Now**.
4. If **Repository** is empty, wrong owner, or Trigger is not Checks completed:
   **Cancel**, treat as restore miss, return to Restore order, Save, re-test.
5. `gh pr list --repo {owner}/{slug} --state open --limit 10` (include
   `statusCheckRollup`).
   - **No open PRs** (empty list): confirm Trigger + Repository in the dialog,
     then **Cancel**. Do **not** invent a number. Do **not** click **Run Now**.
     Record test **skipped** (no open PR). That is not a restore failure.
   - Open PRs exist: prefer one with at least one check `conclusion: FAILURE`
     and `status: COMPLETED` (matches **On Failure** **On PRs**). Mixed
     CANCELLED/SKIPPED on other jobs is OK. If every open PR is all-SUCCESS,
     still pick one and expect a possible CI-filter error. Do **not** Run Now
     with an empty field.
6. When a PR number was chosen: `browser_fill` the PR Number box. Click
   **Run Now**. The button becomes **Running...** (disabled).
7. **Pass** (inventoried 2026-08-12 on Agoras PR CI, PR **748**): toast
   **Test run started.** Dialog closes. URL becomes
   `/automations/<uuid>/runs` with tab **Run History** selected. Newest row:
   Trigger **Test run**, Status **Running**. Record **passed**. Do **not** wait
   for the cloud agent to finish (minutes). Do **not** click **Stop All Runs**.
8. **Fail:** red `.ui-automations-test-modal__error` /
   `.automations-test-modal__error-message` (empty PR → `[not_found] Error`),
   or no toast and still on Settings. Troubleshoot below. **Cancel** if the
   dialog is still open before navigating away.

### Troubleshoot a failed test

Read the error text in the dialog. Then:

| Signal | What to do |
|--------|------------|
| `[not_found] Error` | Empty or unknown PR. If `gh pr list` is empty, **Cancel** and record **skipped** — do not retry with a fake number. Otherwise fill a real number and Run Now again. |
| Repository URL wrong / missing | Cancel. Restore trigger `in` to catalog `{slug} {owner}`. Confirm header is locked **Repository from Git Trigger**. Save. Test run again. |
| Header shows slug / branch / Cloud chips | Restore miss. Open the header picker and select **Repository from Git Trigger**. Set trigger `in` to catalog `{slug} {owner}`. Save. Test run again. |
| Trigger not `Checks completed` | Cancel. Restore the trigger row. Save. Test run again. |
| `Failed to test pull request automation` / CI not completed | PR does not match **On Failure** (checks still running or all green). Pick a PR with **completed failed** checks, or restore chips (**On Failure**, **On PRs**, **by**). |
| Dialog never opens | Save first. Click `data-vr="form-test"` again after Saving... clears. A **Close toast** button can appear after Saving — dismiss it if it blocks the click. |
| GitHub MCP shows Connect (not Disconnect) | Restore tools (add GitHub MCP if missing). Never click Disconnect on a connected row. Save. Test run again. |
| Landed on `/runs` without toast `Test run started.` | Treat as unknown; snapshot Run History. If no new **Test run** / **Running** row, go back to Settings and retry once. |

After a chrome fix: Cancel if the dialog is still open → Restore order → Save
→ Test run again.

Cap: **two** Test run attempts after inventory is golden. Then record
**blocked** with the exact error string and continue the catalog. A Cursor-side
test-run outage is not a reason to mutate a correct saved editor.

## Report

End with a table: name, settings (`ok` / `restored` / `created` / `mismatch` /
`blocked`), instructions (`saved` / `unchanged` / `skipped`), test (`passed` /
`failed` / `skipped`), one-line note (what was wrong → what you set, including
extras removed, that the row was created from Untitled, Test run error, or
**skipped** because no open PR / multi-repo comment row).

Unlock the browser before the final message.
