# Intake

Required read at Phase 0. Resolves the merged-PR set this run will extract journeys from. GitHub MCP only — never `gh`.

Read each GitHub MCP tool descriptor before the first call (`GetDynamicTools` / the host equivalent). Call with that schema. Do not guess argument names.

## 1. Resolve owner/repo

From `git remote -v` (prefer `origin`). Accept `git@github.com:owner/repo.git`, `https://github.com/owner/repo.git`, and `https://github.com/owner/repo`. Strip `.git`. If no GitHub remote exists, stop: this skill cannot list PRs without a GitHub repo identity.

## 2. Parse the intake remainder

After `SKILL.md` tokens are stripped, the remainder is one of:

| Form | Window slug | Set |
| --- | --- | --- |
| Empty | `7d` | Merged PRs with `merged >= today-7d` (UTC date) |
| `Nd` (`7d`, `14d`, `30d`) | that token | Trailing N days of merges |
| `YYYY-MM-DD..YYYY-MM-DD` | `YYYY-MM-DD-YYYY-MM-DD` | Merge date in the closed range |
| PR numbers and/or URLs | `prs-<n>-<n>-…` sorted numerically | Those PRs only |

A pasted list always wins over a window. Mixed remainder (a window *and* numbers) is unparseable — ask or stop per interaction mode.

**PR identity:** a URL keeps its `owner/repo` and number. A bare number uses the resolved origin `owner/repo`. Do not collapse a PR to its head branch name.

## 3. Fetch

### Explicit list

For each PR number, GitHub MCP `pull_request_read`:

- `method: "get"` — title, body, html URL, state, merged-at / merge commit, base, head
- `method: "get_files"` — paginate `perPage: 100` until a short page

v1 is merged-only. If `state` is not merged (open, draft, closed unmerged), record one skip line (`#412 open — not merged; v1 skipped`) and do not include it in the extract set.

### Window search

GitHub MCP `search_pull_requests` is already scoped to pull requests. Query shape:

```text
is:merged merged:>=YYYY-MM-DD repo:OWNER/REPO
```

Date-range end bound:

```text
is:merged merged:>=YYYY-MM-DD merged:<=YYYY-MM-DD repo:OWNER/REPO
```

Pass `owner` and `repo`. Paginate `page` / `perPage: 100` until a page returns fewer than 100 hits. Request a small field set (`number`, `title`, `html_url`, `state`, `closed_at`, `pull_request`) so bodies do not flood context.

Then `pull_request_read` `get` + `get_files` for each hit, same as the explicit list.

If search returns zero hits, the extract set is empty. Continue — do not invent PRs.

## 4. Empty set

An empty extract set (no merged PRs, or every PR skipped as not-merged) still produces a report. Phase 1 records the skip table. Phase 2 writes an empty matrix. Do not invent journeys to fill the page.

## 5. Resume

After the window slug is known, glob `<repo-root>/rosey/dogfood/*-<window-slug>.md`. If a report exists with any scenario still `Pending` (or otherwise unfinished) and none of the remaining rows are only `Blocked (needs human verify)`:

- **Interactive:** ask resume vs start fresh.
- **Non-interactive:** resume the newest unfinished report.

On resume, re-hydrate the task list from the matrix: `Pass` / `Skipped` stay done; `Pending` is remaining work. `Blocked (needs human verify)` is **not** auto-runnable — surface those rows and leave them blocked unless the user explicitly asks to retry a named scenario.

If the only unfinished rows are blocked, do not treat the file as a resumable matrix. Start a new dated report or ask (interactive) whether to retry blocked legs.

## 6. What Phase 1 receives

A list of merged PRs, each with:

- number, title, body, URL
- merge date / merge SHA when present
- changed file paths from `get_files`

That list is the locator. Clustering happens in `scope-extraction.md`.
