---
name: rosey-pr
description: "Creates a pull request for the repository with modified files. Previews PR for user confirmation, then creates local branch, commits, pushes, opens GitHub PR via MCP, and assigns the AI Assisted label on the PR (issue_write update — see §7h)."
---

## Communication while using this skill

**Caveman lite** for all assistant prose while this skill runs: strip filler and hedging; keep articles and full sentences; stay professional and tight. Technical accuracy unchanged; quoted errors and code unchanged. Drop lite only for security warnings, irreversible confirmations, or when the user asks for normal or long-form wording.

# Rosey PR — Pull Request Creation

## Purpose

Automate PR creation after implementation work. Scans for uncommitted changes in the repository, previews what will be committed, gets user confirmation, then **creates a local branch and commits with real git**, pushes the branch, opens a GitHub PR via the GitHub MCP, and **tags the opened PR with the `AI Assisted` label** via MCP `issue_write` (see §7h).

**Local git is the primary path. MCP opens the PR and sets `AI Assisted` on that new PR** (`create_pull_request` has no labels field; labeling is a separate `issue_write` update). This preserves atomicity, runs pre-commit hooks (lint, format, commitlint), and leaves the feature branch checked out so you can amend or push follow-up commits after review.

## Prerequisites

- Local `git` available, authenticated for `push` to the remote (SSH or HTTPS)
- GitHub MCP server connected (`user-github`) — PR creation and labeling
- The repository has a valid `origin` remote pointing to GitHub
- Optional: `gh` CLI — only to **bootstrap** the `AI Assisted` label in a repo if it does not exist yet (`gh label create …`; there is no MCP tool to create repository labels)

## Inputs

Exactly one of the following MUST be resolvable for each run:

1. **PRD mode (default)**: a PRD exists at `docs/plans/<prd-slug>/YYYY-MM-DD-*-prd.md`
   → title, description, and branch slug are derived from the PRD.
2. **Ad-hoc mode**: the user provides an explicit `title` and short `description`
   (optionally a `slug` for the branch name).
   → Use when the work isn't tied to a PRD (tooling, hotfixes, spikes, dev-flow improvements).

The skill MUST ask the user to choose the mode if it's ambiguous (e.g. a PRD exists but the user said "no PRD").

## Process Flow

```text
1. Check repository → find uncommitted/staged changes
2. Resolve inputs → PRD (auto) OR user-provided title/description/slug
3. Preview PR → list files, branch name, commit message
4. Get explicit confirmation (yes / no)
5. Execution (LOCAL git, no MCP yet):
   a. Pre-flight checks (correct base, up-to-date with remote, expected files)
   b. Optional pre-PR QA (lint / typecheck / build) — see Pre-PR Quality Gate
   c. git checkout -b <branch> from the base
   d. git add <explicit paths>
   e. git commit -m "<conventional commit message>"
   f. git push -u origin <branch>
6. Execution (MCP, GitHub writes):
   - create_pull_request with title, body, head, base
   - issue_write (update) — set **`AI Assisted`** on that new PR (see §7h; mandatory for every opened PR)
7. Report results with PR URL (stays on the pushed feature branch)
8. Create PR summary document — generate a markdown file (same format and location as the PRD) with a summary of the created PR, branch, and date; see step 9.
```

## Execution Steps

### 1. Scan Repository

Check `git status --porcelain` for modified, staged, and untracked entries.

- If clean, skip.
- If dirty, collect:
  - GitHub `owner/repo` from `git remote -v` (origin)
  - Current branch (this is the intended base)
  - Full list of modified, staged, and untracked files (from `git status --porcelain`)

### 2. Resolve Inputs

**PRD mode** (default when a PRD exists and the user did not say otherwise):

Look for PRDs in `docs/plans/*/YYYY-MM-DD-*-prd.md`:

- Read the most recent PRD (by date in filename)
- If multiple PRDs exist, prefer the one with a matching implementation plan progress file (indicates recent work)
- Extract:
  - Title: from `# PRD: [Title]` line
  - Description: first paragraph of `## Overview` section
  - Slug: from the containing directory name
  - Jira Ticket (optional): Look for mentions of Jira tickets (e.g., `ROSEY-123`) in the PRD.

**Ad-hoc mode** (when the user says "no PRD" or provides explicit title/description):

- Ask the user (one structured prompt) for:
  - `title` — short, imperative; becomes the PR title
  - `description` — 1–3 sentences for the PR body overview
  - `slug` (optional) — hyphenated ASCII; defaults to a short slug derived from the title
  - `jira_ticket` (optional) — e.g., `ROSEY-123`. If not provided, proceed without it.
- Validate: title ≤ 72 chars, slug matches `^[a-z0-9][a-z0-9-]*[a-z0-9]$`

### 3. Generate Branch Name

First, determine the `<type>` of the changes:
- `feat` — new capability
- `fix` — bug fix
- `chore` — tooling, config, dev flow
- `refactor`, `docs`, `perf`, `build`, `ci`, `test` — as applicable

Default to `feat` when ambiguous. Respect the repo's commitlint rules if a config is present (`commitlint.config.*`, `package.json#commitlint`).

Format: `<type>/<slug>-YYYYMMDD-HHMMSS`

- `<type>`: The change type determined above
- `<slug>`: PRD slug (PRD mode) or provided/derived slug (ad-hoc mode)
- Timestamp: UTC preferred
- If the branch already exists **locally OR on the remote**, append `-2`, `-3`, …

### 4. Derive Conventional Commit Message

Build a single commit message:

```text
<type>(<scope>): [<jira_ticket>] <title>

<one short paragraph — PRD overview, user description, or technical context>

- Patterns: <New patterns or conventions introduced, if any>
- Architecture: <Changes to folder structure or architecture, if any>
- Dependencies: <New dependencies or tooling added, if any>
- Blockers: <New or resolved blockers, if any>
- Tasks: <Completed tasks or new work started>

Changes:
- <file1>
- <file2>
```

Notes:
- `<type>`: Use the same type determined in Step 3.
- `[<jira_ticket>]`: Include if provided or found (e.g., `[ROSEY-123]`). If no Jira ticket is provided, omit this part entirely (e.g., `<type>(<scope>): <title>`).
- `(<scope>)`: Optional, but recommended if applicable (e.g., `api`, `ui`, `auth`).

### 5. Preview

Display to the user:

```text
WARNING: This will create a new branch, commit ONLY the files
listed below on that branch, then push and open a PR. Unlisted dirty files
stay in your working tree untouched.

Files to commit:
  - src/index.ts                                         [M]
  - src/auth.ts                                          [A]
  - docs/plans/user-auth/2026-04-23-user-auth-prd.md     [??]

Base branch: main
New branch: feat/user-auth-20260423-143052
Commit message: feat(auth): [ROSEY-123] Add user authentication feature
```

`[M]` = modified, `[A]` = staged add, `[??]` = untracked (will be added by explicit path).

### 6. Confirmation

Ask: **"Proceed with PR creation? (yes / no)"**

- `yes`: Run the flow
- `no`: Cancel, do nothing

Ambiguous replies are not `yes`.

### 7. Execution (LOCAL git first, MCP last)

#### 7a. Pre-flight checks

```bash
git rev-parse --abbrev-ref HEAD          # must equal <base-branch>
git fetch origin <base-branch>
git rev-list --count HEAD..origin/<base-branch>   # must be 0
git status --porcelain                   # must match the preview
```

If any check fails, STOP and report. Do not auto-fix.

#### 7b. Optional Pre-PR Quality Gate

See "Pre-PR Quality Gate" below. When enabled and a QA entrypoint is discoverable,
run it and STOP on failure.

#### 7c. Create local branch

```bash
git checkout -b <branch-name>
```

If the branch already exists locally or on remote, increment the suffix
(`-2`, `-3`, …) and retry. Uncommitted working-tree changes carry over to the
new branch automatically.

#### 7d. Stage only the previewed files (explicit paths — NEVER `git add .`)

```bash
git add -- <file1> <file2> ...
```

Untracked files from the preview MUST be added by explicit path. Unrelated dirty
files in the working tree are deliberately left unstaged.

#### 7e. Commit with the derived conventional message

Use a HEREDOC to preserve multi-line messages:

```bash
git commit -m "$(cat <<'EOF'
<type>(<scope>): [<jira_ticket>] <title>

<short overview>

- Patterns: <if applicable>
- Architecture: <if applicable>
- Dependencies: <if applicable>
- Tasks: <if applicable>

Changes:
- <file1>
- <file2>
EOF
)"
```

If a pre-commit hook fails (husky, commitlint, prettier, lint-staged):

- Print the hook output verbatim
- **NEVER** pass `--no-verify` / `-n`
- STOP and let the user fix and re-run

#### 7f. Push to remote

```bash
git push -u origin <branch-name>
```

If the push is rejected:

- "Already exists" on remote → increment branch suffix (back to 7c) and retry
- Auth failure → report `gh auth status` suggestion and STOP
- Never `--force` or `--force-with-lease`

#### 7g. Open the PR (FIRST GitHub MCP write)

```text
CallMcpTool user-github create_pull_request
  owner: <from origin>
  repo:  <from origin>
  title: <title>
  head:  <branch-name>
  base:  <base-branch>
  draft: false
  body:  <see template>
```

Initial PR body template:

```text
<overview — one paragraph from PRD or user description>
```

Do not add a **Modified files** section; GitHub already lists changed files on the PR.

**Do not** check out the base branch after opening the PR. Keep the clone on `<branch-name>` so review feedback can be addressed with additional commits on the same branch.

#### 7h. Apply **`AI Assisted`** label (mandatory)

Every PR opened via this skill **must** carry the repository label **`AI Assisted`**. Do this **immediately** after a successful `create_pull_request`, using the **PR number** from the MCP response (same as the issue number).

**Primary path — MCP `issue_write` (update):**

```text
CallMcpTool user-github issue_write
  method: update
  owner: <from origin>
  repo:  <from origin>
  issue_number: <pr_number>
  labels: ["AI Assisted"]
```

If `issue_write` fails because the label **does not exist** in the repository yet, **bootstrap it once** (then retry `issue_write`):

```bash
gh label create "AI Assisted" --repo "<owner>/<repo>" \
  --color "5319E7" \
  --description "Work assisted by AI tools (e.g. Cursor)" 2>/dev/null || true
```

If labeling still fails after bootstrap, **STOP**, report the MCP error verbatim, and do not treat the PR run as complete until the user fixes permissions or adds the label manually. Optional fallback: `gh pr edit "<pr_number>" --repo "<owner>/<repo>" --add-label "AI Assisted"`.

### 8. Report Results

```text
OK  PR #42 opened; label `AI Assisted` applied
    https://github.com/rosey-corp/target-repo/pull/42
    Local: still on branch `user-auth-20260423-143052` (ready for follow-up commits)

FAIL Commit failed (pre-commit hook)
    Hook output:
      .../commitlint: subject may not be empty
    To fix:
      # edit staged changes, then re-run the skill
```

After the run, the repo should be:

- On the **feature branch** that was pushed (not checked out back to base), with unrelated dirty files (if any) still present
- With that branch present both locally and on `origin`

### 9. Create PR Summary Document

After everything is completed, create a final PR summary document.

- **Location and Naming:** The document must be created in the same directory as the PRD.
  - In **PRD mode**, use the PRD's directory. Name the file `YYYY-MM-DD-<slug>-pr-summary.md` using the current date.
  - In **Ad-hoc mode**, if there's no PRD directory, place it in `docs/plans/<slug>/YYYY-MM-DD-<slug>-pr-summary.md` (create the folder if it doesn't exist).
- **Format:** The document should follow the same markdown structure/style as the PRD.
- **Content:** It must include a summary of the created PR, listing:
  - Date
  - Title and Description
  - Branch name used
  - Link to the created GitHub PR
  - Confirmation that the **`AI Assisted`** label was applied to the opened PR
  - Any notes

## Pre-PR Quality Gate (optional)

Before step 7d (stage files), offer to run the repo's own QA entrypoint.
Discovery order:

1. `Makefile`: `make check`, `make lint`, `make ci`
2. `package.json` scripts: `lint`, `typecheck`, `test`, `build` (prefer `build` when `prebuild` runs lint)
3. `pre-commit run --all-files` if `.pre-commit-config.yaml` exists

If a gate fails, STOP and report the failure verbatim. The user can
opt out for a specific run with `skip_qa: true`.

## Error Handling

All failures STOP the flow and report. **Never silently fall back to a different transport**
(no GitHub REST Contents API, no MCP `push_files` / `create_branch` /
`create_or_update_file`).

### Pre-flight check fails

Report which check failed (wrong branch / base behind remote / unexpected files)
and stop.

### Branch already exists (local or remote)

Append `-2`, `-3`, … and retry from 7c.

### Pre-commit hook fails

Print the hook output. Do NOT `--no-verify`. Let the user fix and re-run.

### Push fails

Report the `git push` error verbatim. Suggest:

- Manual retry: `git push -u origin <branch>`
- Auth check: `gh auth status`

### PR creation fails via MCP

Report the MCP error. Manual fallback:

```bash
gh pr create --title "<title>" --body-file <path-to-body> \
             --base <base-branch> --head <branch-name>
```

Then apply **`AI Assisted`** with MCP `issue_write` (§7h) if you have tooling access, or `gh pr edit <number> --repo "<owner>/<repo>" --add-label "AI Assisted"`. Bootstrap the repo label with `gh label create` from §7h if needed.

### `AI Assisted` label fails (after MCP PR succeeded)

Report the MCP (or `gh`) error verbatim. The PR exists but the skill run is incomplete until labeling succeeds — fix token permissions, bootstrap the repo label (§7h), or apply the label in the GitHub UI for that PR number.

## Parameters (optional)

| Parameter     | Description                                        | Default                   |
|---------------|----------------------------------------------------|---------------------------|
| `title`       | PR title (triggers ad-hoc mode)                    | PRD title                 |
| `description` | PR body overview (ad-hoc mode)                     | PRD overview              |
| `slug`        | Explicit branch slug                               | PRD slug or title-derived |
| `base_branch` | Override base branch                           | Current branch            |
| `draft`       | Create PR as draft                                 | `false`                   |
| `skip_qa`     | Skip Pre-PR Quality Gate                           | `false`                   |
| `commit_type` | Force conventional commit type (`feat`, `fix`, …)  | Inferred                  |

## Safety Rules

1. **Never commit without preview** — show the preview and get explicit confirmation
2. **Never auto-proceed** — `yes` is required; ambiguous replies are not `yes`
3. **No silent transport fallback** — never switch from local git + MCP to REST API or MCP `push_files`
4. **Explicit file paths only** — never `git add .` or `git add -A`
5. **No history rewrite on pushed branches** — no `--amend`, no `--force`, no `--force-with-lease`
6. **No hook bypass** — never `--no-verify` / `-n`
7. **Create PR Summary Document** — generate a summary markdown file logging the created PR per step 9.
8. **`AI Assisted` label** — after each successful `create_pull_request`, run §7h (`issue_write` with `labels: ["AI Assisted"]`; optional `gh label create` if the repo label is missing). Every PR must have this label.
9. **Stay on the PR branch** — after a successful PR, do **not** check out the base branch; the user may need to push follow-up commits from the same branch

## Git Policy

**Required (local git is the primary path):**

- `git checkout -b`, `git add -- <paths>`, `git commit`, `git push -u origin <branch>` (optionally `git checkout <base>` only if the user explicitly wants to leave the feature branch)
- Pre-flight reads: `git status`, `git fetch`, `git rev-parse`, `git rev-list`, `git remote -v`
- Respect all pre-commit hooks

**GitHub MCP (`user-github`) is used ONLY for:**

- `create_pull_request`
- `issue_write` (**update** only, **§7h only**) — pass **only** `labels: ["AI Assisted"]` and `issue_number` equal to the number returned by **`create_pull_request`** in the same pass (same run as §7g). Do not use `issue_write` for any other purpose in this skill.

**`gh` CLI (optional):**

- `gh label create "AI Assisted"` — only when the repo does not have that label yet (§7h); no MCP equivalent
- `gh pr edit … --add-label` — optional manual fallback if `issue_write` labeling fails

**Forbidden:**

- MCP `create_branch`, `push_files`, `create_or_update_file`, `delete_file`
- GitHub REST Contents API (`PUT /repos/…/contents/…`) as a fallback
- `git push --force`, `git push --force-with-lease`
- `git commit --amend` once the branch is pushed
- `git add .`, `git add -A`
- `git commit --no-verify` / `-n`

**Rationale:** local git gives us one atomic commit, runs pre-commit
hooks (lint / format / commitlint), keeps you on the feature branch for iterative PR updates, and avoids the encoding fragility of passing multi-KB file contents
through tool-call JSON arguments.

## Example Usage

### PRD mode

```text
User: Create a PR for my changes

→ Detected PRD: docs/plans/user-auth/2026-04-23-user-auth-prd.md
  Title: "Add user authentication feature"
→ Preview shown (branch user-auth-20260423-143052, commit message)

User: yes

→ pre-flight OK → checkout -b → add → commit → push → PR #42 → `issue_write` **AI Assisted** label (stays on feature branch)

OK PR opened (labeled `AI Assisted`)
   - PR #42

→ ### Create PR Summary
   Create docs/plans/user-auth/2026-04-23-user-auth-pr-summary.md summarizing the PR.
```

### Ad-hoc mode (no PRD)

```text
User: /rosey-pr create a PR. No PRD.

→ No PRD will be used. Please provide:
  • title (short, imperative)
  • description (1–3 sentences)
  • slug (optional)

User: title="Improve local development flow"
      description="Tightens dev defaults and helpers across services."
      slug="local-dev-flow"

→ Preview (branch local-dev-flow-YYYYMMDD-HHMMSS)

User: yes

→ ... → PR opened → `issue_write` **AI Assisted** label (stays on feature branch)

→ ### Create PR Summary
   Create docs/plans/local-dev-flow/2026-04-23-local-dev-flow-pr-summary.md summarizing the PR.
```