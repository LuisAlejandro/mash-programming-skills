---
name: rosey-pr
description: Commit, push, and open or update a GitHub PR with an adaptive, value-first description. Uses local git for branch/commit/push and GitHub MCP for PR actions. Use when the user says "commit and PR", "ship this", "create a PR", or "open a pull request". Also handles description-only flows.
---

# Rosey PR

**Asking the user:** When this skill says "ask the user", use the platform's blocking question tool: `AskUserQuestion` in Claude Code (call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded), `AskQuestion` in Cursor, `vscode_askQuestions` in VS Code, `question` in OpenCode, `request_user_input` in Codex, `ask_user` in Gemini, `ask_user` in Pi (requires the `pi-ask-user` extension). Fall back to presenting the question in chat only when no blocking tool exists in the harness or the call errors (e.g., Codex edit modes) — not because a schema load is required. Never silently skip the question.

## Communication while using this skill

**Caveman ultra** for workflow status prose while this skill runs: abbreviate routine workflow words, strip conjunctions where safe, use arrows for causality, and keep one word when one word is enough. Technical accuracy unchanged; git commands, GitHub API names, quoted errors, and command output unchanged. Drop ultra for security warnings, irreversible confirmations, ambiguous multi-step instructions, user confusion, branch/PR decisions that need careful wording, or when the user asks for normal or long-form wording.

This applies to workflow chat, status, and final status reports. PR previews, PR bodies, and commit messages follow their own contracts below: concise and value-led, but normal enough for reviewers and future maintainers.

## Rosey Overlay

This skill follows the Rosey-native commit/push/PR workflow, with Rosey transport and traceability rules:

- Use local `git` for branch creation, staging, commits, and push.
- Use GitHub MCP for GitHub actions: `search_pull_requests`, `pull_request_read`, `create_pull_request`, and `update_pull_request`.
- Do **not** use the GitHub CLI.
- Do **not** assign or bootstrap PR labels.
- For app repos: push the current feature branch and create or update a pull request against `develop`.
- Use `develop` as the fixed Rosey workspace integration/base branch unless the user explicitly overrides with `base:<branch>` for an exceptional manual case. PRs not targeting `develop` are out of `pr-auto-merge.yml` scope (gate skips).
- Integration PR head branches must be `feature/<slug>` (git-flow) so static-synced auto-merge head filters match. Dependabot uses `dependabot/**`.
- Receive completed work after `rosey-work` and usually after `rosey-qa`.
- Stop at PR create/update. Do not merge PRs, watch or fix CI, create milestones, or run releases; auto-merge workflows and `rosey-release` own those later steps.
- Create PRs **ready for review** only (`draft: false`). Never open draft PRs — `pr.yml` and `pr-auto-merge.yml` expect a normal PR on `feature/*` → `develop`. If the user asks for a draft, explain and create ready-for-review instead.
- Do not use the old product-document mode. Prefer `plan:<path>` metadata when supplied; otherwise derive title/body from branch commits and diff.
- After a successful PR create/update, write a PR summary artifact beside the source plan when a plan path is known.

## Mode

- **Description-only** — user wants _just_ a description ("write/draft a PR description", "describe this PR", or pasted a PR URL/number alone). Run Step 4 only; print the result. Apply only if the user asks. If a PR ref was pasted, pass it to Step 4 so Pre-A resolves the right range.
- **Description update** — user wants to refresh/rewrite an existing PR's description with no commit/push intent. If no open PR, report and stop. Otherwise run Step 4 (PR mode using the existing PR's URL), then Step 5 to preview, confirm, and apply via GitHub MCP `update_pull_request`.
- **Full workflow** — otherwise. Run Steps 1-5 in order.

### Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default for direct chat invocation. The skill may ask blocking questions and preview PR body updates.
- `mode:non-interactive` — scripted or skill-to-skill execution. The skill must not ask blocking questions, wait for confirmations, or pause for PR description previews.

Strip the interaction mode token before interpreting remaining text as description focus, PR URL/number, or user instructions. If no interaction mode token is present, set `INTERACTION_MODE=interactive`.

If multiple interaction mode tokens appear, stop and report the conflict.

## Argument Parsing

Parse `$ARGUMENTS` for:

| Token                  | Example                                                 | Effect                                                                                                     |
| ---------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `mode:non-interactive` | `mode:non-interactive`                                  | Run without prompts or confirmation gates                                                                  |
| `mode:interactive`     | `mode:interactive`                                      | Explicit default interactive behavior                                                                      |
| `plan:<path>`          | `plan:rosey/plans/2026-05-29-001-feat-workflow-plan.md` | Source plan for PR title/body context and PR summary location                                              |
| `base:<branch>`        | `base:release`                                          | Explicit base branch override. Default is `develop`. Auto-merge does not apply when base is not `develop`. |

Strip recognized tokens before interpreting remaining text as description focus, PR URL/number, or user instructions.

## Context

**On platforms other than Claude Code**, run the Context fallback below. **In Claude Code**, the labeled sections contain pre-populated data — use them directly.

**Git status:**
!`git status`

**Working tree diff:**
!`git diff HEAD`

**Current branch:**
!`git branch --show-current`

**Recent commits:**
!`git log --oneline -10`

**Develop branch status:**
!`git rev-parse --verify origin/develop >/dev/null 2>&1 && echo HAS_ORIGIN_DEVELOP || echo MISSING_ORIGIN_DEVELOP`

### Context fallback

```bash
printf '=== STATUS ===\n'; git status; printf '\n=== DIFF ===\n'; git diff HEAD; printf '\n=== BRANCH ===\n'; git branch --show-current; printf '\n=== LOG ===\n'; git log --oneline -10; printf '\n=== DEVELOP ===\n'; git rev-parse --verify origin/develop >/dev/null 2>&1 && echo HAS_ORIGIN_DEVELOP || echo MISSING_ORIGIN_DEVELOP
```

---

## Step 1: Resolve branch and PR state

Resolve `<base>` as `base:<branch>` when supplied, otherwise `develop`. If `origin/<base>` is unavailable, stop and report that the integration branch could not be verified.

Resolve `owner/repo` from `git remote -v`. Before calling any GitHub MCP tool, read the tool descriptor and call the enabled GitHub MCP server with the exact schema.

Branch routing:

- **Detached HEAD** — in interactive mode, explain a branch is required and ask whether to create a `feature/<slug>` branch. If yes, derive `<slug>` per **Branch naming** below and run git-flow feature start. If no, stop. In non-interactive mode, auto-create a feature branch when a safe base can be resolved; otherwise stop with a blocker.
- **On `<base>` with work to do** (uncommitted, unpushed, or no upstream) — automatically create a `feature/<slug>` branch via git-flow. Pushing the integration branch directly is not supported.
- **On `<base>` with no work** — report no feature branch work and stop.
- **Feature branch** — if the branch is meaningful but not `feature/<slug>`, suggest `git branch -m feature/<slug>` before push (mirror `rosey-work` rename guidance). If the name is opaque, derive a slug and rename. Then continue.

**Plan ↔ branch guard** (when `plan:<path>` is supplied or `ROSEY_WORK_HANDOFF` includes `PLAN_OR_REQUIREMENTS`):

- Derive expected slug from the plan basename (same rule as **Branch naming** below).
- If `feature/<expected-slug>` ≠ current branch and `BRANCH_DECISION` is not `continued` with an explicit carryover note, **stop before commit** and report the mismatch. Do not stack a distinct plan onto a prior-phase branch unless the user confirms "add to existing PR" or "ship on current branch."
- When an open PR exists on the current branch and the plan slug differs, treat as stacked scope — require the same explicit confirmation before commit/push.

**Branch naming** (integration PRs only):

- Format: `feature/<slug>` via `git flow feature start <slug>` (see `references/branch-creation.md`).
- Slug from a plan path: basename without extension, strip the leading date and sequence/type tokens (`YYYY-MM-DD-NNN-<type>-`) and any trailing `-plan` suffix, kebab-case, max ~50 characters.
  Example: `rosey/plans/2026-05-29-001-feat-seo-phase-2-content-plan.md` → `seo-phase-2-content`.
- Otherwise: kebab-case summary of the change.
- Do not use `test/`, `chore/`, or `release/` prefixes for integration PRs.

This rule is duplicated verbatim in `references/branch-creation.md` and `rosey-work`'s branch setup. All three must agree — the plan ↔ branch guard above stops before commit when they diverge.

Use GitHub MCP `search_pull_requests` to detect an existing open PR for the current branch. Step 5 uses it to route between new-PR and existing-PR application.

## Step 2: Determine conventions

Match repo style for commit messages and PR titles in this order: project instructions in context → if `.gitchangelog.rc` exists at repo root, use gitchangelog tags → recent commits → Conventional Commits as fallback. The user may override.

**When `.gitchangelog.rc` exists** (Rosey product repos that ship HISTORY):

- Commit subjects: `[ADD]` / `[FIX]` / `[REF]` / `[DEL]` plus an imperative user-facing summary (see `.cursor/rules/gitchangelog-commits.mdc`).
- Ambiguous ADD vs FIX → default to `[FIX]`.
- Non-user-facing work → append `!cosmetic` / `!refactor` / `!wip`, or use a `CI:` prefix, so gitchangelog ignores them.
- PR titles may stay Conventional-style (`type: description`); only commit subjects feed HISTORY / release notes.

**Otherwise (Conventional Commits fallback):**

- Default to `fix:` over `feat:` when ambiguous — adding code to remedy broken or missing behavior is `fix:`. Reserve `feat:` for capabilities the user could not previously accomplish.

Commit messages follow Caveman-commit principles:

- Subject: terse imperative (gitchangelog-tagged when applicable, else conventional), ideally <=50 chars and hard-capped at 72.
- Body: omit unless the why is non-obvious.
- Always include a body for breaking changes, security fixes, data migrations, reversions, and migration notes.
- Do not add AI attribution, filler phrases, or file-by-file restatements.

If `plan:<path>` was supplied, read the plan for title, type, summary, requirements, and key decisions. Do not look for legacy product requirement documents.

## Step 3: Commit and push

If on `<base>`, branch creation needs to handle stale local `<base>`, unpushed commits on local `<base>`, and uncommitted changes that collide with the fresh remote base. Read `references/branch-creation.md` and follow its decision flow before continuing.

Scan changed files for naturally distinct concerns. If they clearly group into separate logical changes, create separate commits (2-3 max). Group at file level only — no `git add -p`. When ambiguous, one commit is fine.

Stage and commit each group. **Avoid `git add -A` and `git add .`** — they sweep in `.env`, build artifacts, and generated files:

```bash
git add file1 file2 file3 && git commit -m "$(cat <<'EOF'
commit message here
EOF
)"
```

Then bring the feature branch up to date with the base branch to avoid "behind" merge blocks:

```bash
git fetch origin <base>
git merge origin/<base>
```

If the merge produces conflicts: in interactive mode, stop and report them to the user. In non-interactive mode, abort the merge (`git merge --abort`), skip the update, push the branch as-is, and note in the final status that the feature branch is behind `<base>` due to conflicts — the auto-merge workflow will attempt `updateBranch` as a fallback.

Then push:

```bash
git push -u origin HEAD
```

If the working tree is clean and all commits are already pushed, the fetch/merge/push sequence is still required to ensure the branch is not behind `<base>` before the PR is created or updated.

## Step 4: Compose the PR title and body

**You MUST read `references/pr-description-writing.md`** in full — the core principle at the top governs every step. The only input it needs from this skill is the PR ref, if one was identified by mode dispatch (description-only with a pasted URL, or description update).

**Evidence decision** before composition. Two short-circuits, then the full decision:

1. **User explicitly asked for evidence** ("ship with a demo", "include a screenshot") — proceed directly to capture. If capture is impossible or clearly not useful, note briefly and proceed without.
2. **Agent judgment on authored changes** — if you authored the commits and know the change is non-observable (internal plumbing, type-only, backend refactor without user-facing effect, docs/markdown/changelog/CI/test-only, pure refactors), skip the prompt without asking.

Otherwise, if the branch diff changes observable behavior (UI, CLI output, API behavior with runnable code, generated artifacts, workflow output) and evidence is not blocked (unavailable credentials, paid services, deploy-only infrastructure, hardware), ask: "This PR has observable behavior. Capture evidence for the PR description?"

- **Capture now** — use the applicable evidence-capture workflow with a target description from the branch diff. If it returns a URL, splice it as a `## Demo` section. If it returns a local path, note in the body that a demo was recorded but is not embedded. If skipped, proceed without evidence.
- **Use existing evidence** — ask for the URL or markdown embed; splice as a `## Demo` section.
- **Skip** — proceed without an evidence section.

In non-interactive mode, skip this evidence prompt. Include a Demo section only when the caller supplied evidence explicitly.

Then continue with the rest of the reference (Steps A through G) to compose the title and body.

## Step 5: Apply and report

**Description-only mode** — print the title and body. Stop unless the user asks to apply.

**New PR** (full workflow, no existing PR from Step 1) — apply per "Applying via GitHub MCP" below using `create_pull_request`. Report the URL.

**Existing PR** (full workflow, found in Step 1) — the new commits are already on the PR from Step 3. If the PR is a draft, mark it ready for review via `update_pull_request` with `draft: false` before reporting. In interactive mode, report the PR URL, then ask whether to rewrite the description. In non-interactive mode, update the description automatically from the current plan and diff context.

- **No** — done.
- **Yes** — run Step 4 if not already done, then preview and apply (see below).

**Description update mode, or existing-PR rewrite confirmed** — in interactive mode, preview before applying. Ask: "New title: `<title>` (`<N>` chars). Summary leads with: `<first two sentences>`. Total body: `<L>` lines. Apply?" If declined, the user may pass focus text back for a regenerate; do not apply. If confirmed, apply per "Applying via GitHub MCP" below using `update_pull_request` and report the URL. In non-interactive mode, apply without preview once the title and body are composed.

---

## Applying via GitHub MCP

Use GitHub MCP for all GitHub writes. Do not use the GitHub CLI.

For new PRs, call `create_pull_request` with:

- `owner`
- `repo`
- `title`
- `body`
- `head`: current pushed feature branch
- `base`: `develop` unless explicitly overridden
- `draft`: `false` always — ready for review; never create draft PRs

For existing PR description updates, call `update_pull_request` with:

- `owner`
- `repo`
- `pullNumber`
- `title`
- `body`
- `draft`: `false` when the PR is still a draft (mark ready for review)

Do not assign labels.

## Step 6: PR Summary Artifact

After a successful PR create or update, if `plan:<path>` is known, create a summary artifact beside the plan:

```text
<plan-basename>.pr-summary.md
```

Include:

- Source plan path
- PR title
- PR URL and number
- Base branch
- Head branch
- Commit SHAs or summary of commits included
- Date created/updated
- Short value-led description of what changed. Keep it to 1-3 bullets or one short paragraph; do not restate file names unless needed for traceability.

If no plan path is known, skip the artifact and report that no plan-linked summary was written.
