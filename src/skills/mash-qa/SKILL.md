---
name: mash-qa
description: "Structured code review using tiered persona agents, confidence-gated findings, and a merge/dedup pipeline. Use when reviewing this session's changes, a branch, or a PR."
argument-hint: "[blank to review this session's uncommitted changes, or provide a PR link / base:<ref>]"
---

# Code Review

Reviews code changes using dynamically selected reviewer personas. Spawns parallel sub-agents that return structured JSON, then merges and deduplicates findings into a single report.

## Communication while using this skill

Caveman level, drop conditions, and what stays uncompressed are in the caveman rule.

## Mash Programming Skills Overlay

This skill follows the upstream code-review workflow, with Mash Programming Skills handoff and Sentrux additions:

- Accept Mash Programming Skills work handoff context when supplied: `FILES_CHANGED`, `WHAT_WAS_IMPLEMENTED`, `PLAN_OR_REQUIREMENTS`, and `SENTRUX_REVIEW_CONTEXT`.
- When `SENTRUX_REVIEW_CONTEXT` is present, include it in reviewer context and synthesis. Structural regression is a first-class review axis alongside logic, requirements, tests, and maintainability.
- Treat a failed Sentrux `session_end`, quality-signal drop, new import cycle, or behavior-critical `test_gaps` entry as a P1/P2 finding depending on impact. If the context documents `override sentrux handoff block`, keep the concern visible as residual risk but do not block solely because of the override.
- When `FILES_CHANGED` is provided, use it as the authoritative file list to cross-check the computed git diff. If the computed diff misses any provided file, include that mismatch in the review scope notes.
- Run the Hindsight gate (always-on Hindsight guideline; CLI in [`mash-hindsight`](../mash-hindsight/SKILL.md)) before Stage 1 when review may be affected by prior preferences, conventions, or session context.
- Use GitHub MCP tools for GitHub PR metadata and comments. Do not rely on the GitHub CLI.

## When to Use

- Before creating a PR
- After completing a task during iterative implementation
- When feedback is needed on any code changes
- Can be invoked standalone
- Can run as a read-only or headless review step inside larger workflows

## Argument Parsing

Parse `$ARGUMENTS` for the following optional tokens. Strip each recognized token before interpreting the remainder as the PR number, GitHub URL, or branch name.

| Token | Example | Effect |
|-------|---------|--------|
| `mode:report-only` | `mode:report-only` | Select report-only mode |
| `mode:headless` | `mode:headless` | Select headless mode for programmatic callers (see Mode Detection below) |
| `mode:autofix` | `mode:autofix` | Accepted as `mode:headless`. Not a separate mode. |
| `base:<sha-or-ref>` | `base:abc1234` or `base:origin/main` | Skip scope detection — use this as the diff base directly |
| `plan:<path>` | `plan:.mash/plans/2026-03-25-001-feat-foo-plan.md` | Load this plan for requirements verification |

All tokens are optional. Each one present means one less thing to infer. When absent, fall back to existing behavior for that stage.

**Conflicting mode flags:** `mode:autofix` is `mode:headless`. Those two together are one mode. Any other pair of mode tokens stops the run before agents are dispatched. If `mode:headless` is one of the conflicting tokens, emit `Review failed (headless mode). Reason: conflicting mode flags — <mode_a> and <mode_b> cannot be combined.` Otherwise emit `Review failed. Reason: conflicting mode flags — <mode_a> and <mode_b> cannot be combined.`

## Quick Tier

When `$ARGUMENTS` indicates the user wants a quick, fast, or light code review, run a **reduced roster** instead of the full team. Same pipeline, same schema, same synthesis — fewer reviewers.

**Announce the chosen path** before any other work (Quick review vs Multi-agent review), naming the roster. Programmatic callers (`mode:report-only`, `mode:headless`) skip the announcement — the orchestrator owns user-facing messaging.

**Roster:** `mash-correctness-reviewer` plus **at most one** conditional persona, selected by the same diff judgment the full flow uses (Stage 4) — `security` for an auth or input-handling diff, `data-migration` for migration artifacts, and so on. When no conditional clearly fits, correctness alone is the roster. Two reviewers is the ceiling, not a target.

Correctness is non-negotiable because it is the only persona whose findings are *defects* rather than improvements; everything else in the catalog is quality signal that a quick pass is explicitly trading away.

Everything downstream is unchanged: confidence anchors, the synthesis pipeline, `safe_auto` application, and the output template all run normally. A quick review is a smaller team, not a different contract.

**The quick tier never applies when:**

- `mode:report-only` or `mode:headless` is present — programmatic callers always get the full roster. A quick pass is a human convenience, and an automated caller that wanted one would ask for a narrower review, not a cheaper one.
- The diff trips the `adversarial` gate (>=50 substantive changed lines, or auth / payments / data mutations / external API integrations). **Say so and run the full roster** — the request is declined explicitly, never silently upgraded. Quick is for small and boring; a risky diff is neither.

## Mode Detection

| Mode | When | Behavior |
|------|------|----------|
| **Interactive** (default) | No mode token present | Review, apply safe_auto fixes automatically, present findings, ask for policy decisions on gated/manual findings, and optionally offer the next step (a fix pass, or a `mash-pr` invocation the user runs themselves) |
| **Report-only** | `mode:report-only` in arguments | Strictly read-only. Review and report only, then stop with no edits, artifacts, commits, pushes, or PR actions |
| **Headless** | `mode:headless` in arguments, or `mode:autofix` as that same mode | Programmatic mode for skill-to-skill invocation. Apply `safe_auto` fixes silently (single pass), return all other findings as structured text output, write run artifacts, and return "Review complete" signal. No interactive prompts. |

Parent workflows that run in `mode:non-interactive` and want safe fixes applied invoke `mode:headless`. `mode:non-interactive` is not a standalone `mash-qa` mode.

### Report-only mode rules

- **Skip all user questions.** Infer intent conservatively if the diff metadata is thin.
- **Never edit files or externalize work.** Do not write `.mash/qa/<run-id>/`, do not file tickets, and do not commit, push, or create a PR.
- **Safe for parallel read-only verification.** `mode:report-only` is the only mode that is safe to run concurrently with browser testing on the same checkout.
- **Do not switch the shared checkout.** If the caller passes an explicit PR or branch target, `mode:report-only` must run in an isolated checkout/worktree or stop instead of changing branches.
- **Do not overlap mutating review with browser testing on the same checkout.** If a future orchestrator wants fixes, run the mutating review phase after browser testing or in an isolated checkout/worktree.

### Headless mode rules

- **Skip all user questions.** Never use the platform question tool (`AskUserQuestion` in Claude Code, `AskQuestion` in Cursor, `question` in OpenCode, `request_user_input` in Codex, `ask_user` in Gemini, `ask_user` in Pi (requires the `pi-ask-user` extension)) or other interactive prompts. Infer intent conservatively if the diff metadata is thin.
- **Require a determinable diff scope.** If headless mode cannot determine a diff scope (no branch, PR, or `base:` ref determinable without user interaction), emit `Review failed (headless mode). Reason: no diff scope detected. Re-invoke with a branch name, PR number, or base:<ref>.` and stop without dispatching agents.
- **Apply only `safe_auto -> review-fixer` findings in a single pass.** No bounded re-review rounds. Leave `gated_auto`, `manual`, `human`, and `release` work unresolved and return them in the structured output.
- **Return all non-auto findings as structured text output.** Use the headless output envelope format in `references/synthesis-and-followup.md` (Stage 6) preserving severity, autofix_class, owner, requires_verification, confidence, pre_existing, and suggested_fix per finding. Enrich with detail-tier fields (why_it_matters, evidence[]) from the per-agent artifact files on disk (see Detail enrichment in that Stage 6).
- **Write a run artifact** under `.mash/qa/<run-id>/` summarizing findings, applied fixes, and advisory outputs. Include the artifact path in the structured output.
- **Do not file tickets or externalize work.** The caller receives structured findings and routes downstream work itself.
- **Do not switch the shared checkout.** If the caller passes an explicit PR or branch target, `mode:headless` must run in an isolated checkout/worktree or stop instead of changing branches. When stopping, emit `Review failed (headless mode). Reason: cannot switch shared checkout. Re-invoke with base:<ref> to review the current checkout, or run from an isolated worktree.`
- **Not safe for concurrent use on a shared checkout.** Unlike `mode:report-only`, headless mutates files (applies `safe_auto` fixes). Callers must not run headless concurrently with other mutating operations on the same checkout.
- **Never commit, push, or create a PR** from headless mode. The caller owns those decisions.
- **End with "Review complete" as the terminal signal** so callers can detect completion. If all reviewers fail or time out, emit `Code review degraded (headless mode). Reason: 0 of N reviewers returned results.` followed by "Review complete".

### Interactive mode rules

- **Pre-load the platform question tool before any question fires.** In Claude Code, `AskUserQuestion` is a deferred tool — its schema is not available at session start. At the start of Interactive-mode work (before Stage 2 intent-ambiguity questions, the After-Review routing question, walk-through per-finding questions, bulk-preview Proceed/Cancel, and tracker-defer failure sub-questions), call `ToolSearch` with query `select:AskUserQuestion` to load the schema. Load it **once, eagerly, at the top of the Interactive flow** — do not wait for the first question site and do not decide it on a per-site basis. The preload applies to Claude Code only; on Cursor, OpenCode, Codex, Gemini, and Pi the question tool is directly available.
- **The numbered-list fallback only applies when the harness genuinely lacks a blocking question tool** — `ToolSearch` returns no match, the tool call explicitly fails, or the runtime mode does not expose it (e.g., Codex edit modes where `request_user_input` is unavailable). A pending schema load is not a fallback trigger; call `ToolSearch` first per the pre-load rule. Rendering a question as narrative text because the tool feels inconvenient, because the model is in report-formatting mode, or because the instruction was buried in a long skill is a bug. A question that calls for a user decision must either fire the tool or fall back loudly.

## Compact Finding Presentation

For chat, headless envelopes, bulk previews, and completion reports, render findings as path-first terse clauses:

```text
#<id> <severity> <file:line> -- <title>. Fix: <suggested_fix>.
```

Keep metadata tokens exact (`#`, severity, `autofix_class`, owner, confidence, `requires_verification`). Keep each title and fix line short. Do not move `why_it_matters` or full `evidence` into parent-context returns unless the mode explicitly requires detail enrichment; when enrichment is required, use the shortest artifact-backed excerpt that explains the observable risk.

## Severity Scale

All reviewers use P0-P3:

| Level | Meaning | Action |
|-------|---------|--------|
| **P0** | Critical breakage, exploitable vulnerability, data loss/corruption | Must fix before merge |
| **P1** | High-impact defect likely hit in normal usage, breaking contract | Should fix |
| **P2** | Moderate issue with meaningful downside (edge case, perf regression, maintainability trap) | Fix if straightforward |
| **P3** | Low-impact, narrow scope, minor improvement | User's discretion |

## Action Routing

Severity answers **urgency**. Routing answers **who acts next** and **whether this skill may mutate the checkout**.

| `autofix_class` | Default owner | Meaning |
|-----------------|---------------|---------|
| `safe_auto` | `review-fixer` | Local, deterministic fix suitable for the in-skill fixer when the current mode allows mutation |
| `gated_auto` | `downstream-resolver` or `human` | Concrete fix exists, but it changes behavior, contracts, permissions, or another sensitive boundary that should not be auto-applied by default |
| `manual` | `downstream-resolver` or `human` | Actionable work that should be handed off rather than fixed in-skill |
| `advisory` | `human` or `release` | Report-only output such as learnings, rollout notes, or residual risk |

Routing rules:

- **Synthesis owns the final route.** Persona-provided routing metadata is input, not the last word.
- **Choose the more conservative route on disagreement.** A merged finding may move from `safe_auto` to `gated_auto` or `manual`, but never the other way without stronger evidence.
- **Only `safe_auto -> review-fixer` enters the in-skill fixer queue automatically.**
- **`requires_verification: true` means a fix is not complete without targeted tests, a focused re-review, or operational validation.**

## Reviewers

The persona catalog included below is the only roster. Select always-on personas, conditional personas, and Mash Programming Skills agents from that catalog. Schema drift detection is folded into `mash-data-migration-reviewer` and surfaces as P1 findings.

## Review Scope

Every full review spawns the 5 always-on personas, then adds the conditional personas and Mash Programming Skills agents the catalog selects. A small config change can be the 5 personas alone. A Rails auth feature might add security, reliability, and adversarial.

**Exception: the quick tier** (see above) runs `correctness` plus at most one conditional persona. It does not spawn `mash-agent-native-reviewer` or `mash-learnings-researcher`.

## Protected Artifacts

The following paths are Mash Programming Skills pipeline artifacts and must never be flagged for deletion, removal, or gitignore by any reviewer:

- `.mash/brainstorms/*` -- requirements documents created by mash-brainstorm
- `.mash/plans/*.md` -- plan files created by mash-plan (decision artifacts; execution progress is derived from git, not stored in plan bodies)
- `.mash/solutions/*.md` -- solution documents created during the pipeline
- `.mash/insights/*.md` -- durable repo lessons surfaced by mash-learnings-researcher
- `.mash/dogfood/*` -- post-merge dogfood reports created by mash-dogfood

If a reviewer flags any file in these directories for cleanup or removal, discard that finding during synthesis.

## How to Run

### Stage 0: Hindsight gate (hard)

Before computing diff scope:

1. Read [`mash-hindsight`](../mash-hindsight/SKILL.md)
2. Run its availability check — daemon status **and** the `/version` fingerprint (prepend `~/.local/bin` to PATH) — OR emit `Hindsight: unavailable — <reason>`

Recall happens once, after scope is known (Stage 1). Do not recall at Stage 0 and again later: reviewers need module- and diff-scoped context, which does not exist before scope is computed.

`mode:report-only`: gate still runs; no file edits.

### Stage 1: Determine scope

Compute the diff range, file list, and diff. Minimize permission prompts by combining into as few commands as possible.

**If `base:` argument is provided (fast path):**

The caller already knows the diff base. Skip all base-branch detection, remote resolution, and merge-base computation. Use the provided value directly:

```
BASE_ARG="{base_arg}"
BASE=$(git merge-base HEAD "$BASE_ARG" 2>/dev/null) || BASE="$BASE_ARG"
```

Then produce the same output as the other paths:

```
echo "BASE:$BASE" && echo "FILES:" && git diff --name-only $BASE && echo "DIFF:" && git diff -U10 $BASE && echo "UNTRACKED:" && git ls-files --others --exclude-standard
```

This path works with any ref — a SHA, `origin/main`, a branch name. Automated callers (for example `mash-work`) should prefer this to avoid the detection overhead. **Do not combine `base:` with a PR number or branch target.** If both are present, stop with an error: "Cannot use `base:` with a PR number or branch target — `base:` implies the current checkout is already the correct branch. Pass `base:` alone, or pass the target alone and let scope detection resolve the base." This avoids scope/intent mismatches where the diff base comes from one source but the code and metadata come from another.

**If a PR number or GitHub URL is provided as an argument:**

`mash-qa` never switches the shared checkout, in any mode. Continue to the skip-condition pre-check below — PR metadata is read-only and needs no checkout. If no skip rule fires and the checkout is not already positioned on the PR head, stop and tell the caller: "`mash-qa` does not switch branches. Check out this PR yourself (`gh pr checkout <n>`), then re-run with `base:<pr-base-branch>`; or run from an isolated worktree/checkout for that PR." In `mode:headless`, emit `Review failed (headless mode). Reason: cannot switch shared checkout. Re-invoke with base:<ref> to review the current checkout, or run from an isolated worktree.` When the checkout is already on the PR head (or the review runs in an isolated worktree), continue with scope detection below.

**Skip-condition pre-check.** Before checkout or scope detection, run a PR-state probe to decide whether the review should proceed:

Use GitHub MCP `pull_request_read` with `method: "get"` and `method: "get_files"` for the PR state, title, body, and changed file paths.

Apply skip rules in order:

- `state` is `CLOSED` or `MERGED` -> stop with message `PR is closed/merged; not reviewing.`
- **Trivial-PR judgment**: spawn a lightweight sub-agent with the PR title, body, and changed file paths. Follow `~/.config/mash/references/model-tiers.md` — use the platform's cheapest capable model where a per-dispatch override exists, otherwise omit the override and inherit. The agent's task: "Is this an automated or trivial PR that does not warrant a code review? Consider: dependency lock-file or manifest-only bumps, automated release commits, chore version increments with no substantive code changes. When in doubt, answer no — false negatives (skipped reviews that should have run) are more costly than false positives (unnecessary reviews)." If the judgment returns yes: stop with message `PR appears to be a trivial automated PR; not reviewing. Run without a PR argument to review this session's changes, or pass base:<ref> if review is intended.`

When any skip rule fires, emit the message and stop without dispatching reviewers, switching the checkout, or running scope detection. **Standalone branch mode and `base:` mode are unaffected** -- they always run the full review. **Draft PRs are reviewed normally** -- draft status is not a skip condition; early feedback on in-progress work is valuable.

If no skip rule fires, resolve PR metadata and proceed.

Resolve the head branch from GitHub MCP metadata for PR title, body, base branch, URL, and prior-comment detection only — persona agents read the current checkout, which is the PR head the caller already checked out. Never run `git checkout` and never ask the user to stash or commit.

Then fetch PR metadata. Capture the base branch name and the PR base repository identity, not just the branch name. Project `reviews` and `comments` to a `hasPriorComments` boolean via `--jq` -- counting only, not materializing review or comment bodies into the orchestrator's context. The reviews filter excludes approval-state submissions with empty bodies (approvals are not feedback to verify), so PRs with only approval clicks correctly fall through the gate. Stage 3 uses `hasPriorComments` to decide whether to spawn `previous-comments`:

Use GitHub MCP `pull_request_read`:

- `method: "get"` for title, body, base branch, head branch, URL, and state.
- `method: "get_reviews"` and `method: "get_comments"` for prior-feedback detection.

Use the repository portion of the returned PR URL as `<base-repo>` (for example, `EveryInc/mash-programming-skills` from `https://github.com/EveryInc/mash-programming-skills/pull/348`).

Then compute a local diff against the PR's base branch so re-reviews also include local fix commits and uncommitted edits. Substitute the PR base branch from metadata (shown here as `<base>`) and the PR base repository identity derived from the PR URL (shown here as `<base-repo>`). Resolve the base ref from the PR's actual base repository, not by assuming `origin` points at that repo:

```
PR_BASE_REMOTE=$(git remote -v | awk 'index($2, "github.com:<base-repo>") || index($2, "github.com/<base-repo>") {print $1; exit}')
if [ -n "$PR_BASE_REMOTE" ]; then PR_BASE_REMOTE_REF="$PR_BASE_REMOTE/<base>"; else PR_BASE_REMOTE_REF=""; fi
PR_BASE_REF=$(git rev-parse --verify "$PR_BASE_REMOTE_REF" 2>/dev/null || git rev-parse --verify <base> 2>/dev/null || true)
if [ -z "$PR_BASE_REF" ]; then
  if [ -n "$PR_BASE_REMOTE_REF" ]; then
    git fetch --no-tags "$PR_BASE_REMOTE" <base>:refs/remotes/"$PR_BASE_REMOTE"/<base> 2>/dev/null || git fetch --no-tags "$PR_BASE_REMOTE" <base> 2>/dev/null || true
    PR_BASE_REF=$(git rev-parse --verify "$PR_BASE_REMOTE_REF" 2>/dev/null || git rev-parse --verify <base> 2>/dev/null || true)
  else
    if git fetch --no-tags https://github.com/<base-repo>.git <base> 2>/dev/null; then
      PR_BASE_REF=$(git rev-parse --verify FETCH_HEAD 2>/dev/null || true)
    fi
    if [ -z "$PR_BASE_REF" ]; then PR_BASE_REF=$(git rev-parse --verify <base> 2>/dev/null || true); fi
  fi
fi
if [ -n "$PR_BASE_REF" ]; then BASE=$(git merge-base HEAD "$PR_BASE_REF" 2>/dev/null) || BASE=""; else BASE=""; fi
```

```
if [ -n "$BASE" ]; then echo "BASE:$BASE" && echo "FILES:" && git diff --name-only $BASE && echo "DIFF:" && git diff -U10 $BASE && echo "UNTRACKED:" && git ls-files --others --exclude-standard; else echo "ERROR: Unable to resolve PR base branch <base> locally. Fetch the base branch and rerun so the review scope stays aligned with the PR."; fi
```

Extract PR title/body, base branch, and PR URL from GitHub MCP metadata, then extract the base marker, file list, diff content, and `UNTRACKED:` list from the local command. Do not use remote-only PR diffs as the review scope after checkout -- they miss local fix commits until pushed. If the base ref still cannot be resolved from the PR's actual base repository after the fetch attempt, stop instead of falling back to `git diff HEAD`; a PR review without the PR base branch is incomplete.

**If a branch name is provided as an argument:**

`mash-qa` never switches the shared checkout, in any mode. The caller positions the checkout: tell them "`mash-qa` does not switch branches. Check out `<branch>` yourself, then re-run with `base:<base-ref>`; or run from an isolated worktree/checkout for `<branch>`." In `mode:headless`, emit `Review failed (headless mode). Reason: cannot switch shared checkout. Re-invoke with base:<ref> to review the current checkout, or run from an isolated worktree.` Do not run `git checkout <branch>` and do not ask the user to stash or commit. Stop here unless the review runs in an isolated checkout already positioned on `<branch>`.

Then detect the review base branch and compute the merge-base.

**If a PR exists for `<branch>`** (check with GitHub MCP `search_pull_requests` scoped to the repo and branch): reuse PR mode's `PR_BASE_REMOTE` block above. Use the PR base branch as `<base>` and derive `<base-repo>` from the PR URL (e.g., `EveryInc/foo` from `https://github.com/EveryInc/foo/pull/123`). The block already sets `$BASE` to the merge-base SHA — `origin` may point at the user's fork, which is why naive `origin/<base>` is unsafe and the fork-safe block is required.

**If no PR exists**: derive the default branch. Primary source is `git symbolic-ref --quiet --short refs/remotes/origin/HEAD | sed 's#^origin/##'`; then try the first of `main`/`master`/`develop`/`trunk` that exists as `origin/<name>` or bare `<name>` locally. Compute `BASE=$(git merge-base HEAD <base-ref>)`, where `<base-ref>` is `origin/<base-branch>` when available, otherwise the bare local `<base-branch>` (covers single-branch clones, missing origin remote, and unfetched defaults). If `BASE` is empty and the clone is shallow (`git rev-parse --is-shallow-repository`), run `git fetch --unshallow origin` and retry.

If no base can be resolved, **stop**. Do not fall back to `git diff HEAD` — a branch review without the base would only show uncommitted changes and silently miss all committed work.

On success, produce the diff:

```
echo "BASE:$BASE" && echo "FILES:" && git diff --name-only $BASE && echo "DIFF:" && git diff -U10 $BASE && echo "UNTRACKED:" && git ls-files --others --exclude-standard
```

You may still fetch additional PR metadata with GitHub MCP for title, body, linked issues, and a projected `hasPriorComments` boolean. Do not fail if no PR exists -- leave `hasPriorComments=false`.

**If no argument (standalone — this session's changes):**

Review the working tree as-is. Diff `HEAD` (staged + unstaged) — this is the default and covers exactly this session's changes. To review a branch or PR instead, pass a PR link or `base:<ref>`.

On success, produce the diff:

```
echo "BASE:HEAD" && echo "FILES:" && git diff --name-only HEAD && echo "DIFF:" && git diff -U10 HEAD && echo "UNTRACKED:" && git ls-files --others --exclude-standard
```

Using `git diff $BASE` (without `..HEAD`) diffs the merge-base against the working tree, which includes committed, staged, and unstaged changes together.

**Untracked file handling:** Always inspect the `UNTRACKED:` list, even when `FILES:`/`DIFF:` are non-empty. Untracked files are outside review scope until staged. If the list is non-empty, tell the user which files are excluded. If any of them should be reviewed, stop and tell the user to `git add` them first and rerun. Only continue when the user is intentionally reviewing tracked changes only. In `mode:headless`, do not stop to ask — proceed with tracked changes only and note the excluded untracked files in the Coverage section of the output.

**Hindsight recall (the single recall for this run):** After the diff scope is known, run `memory recall` now — per [`mash-hindsight`](../mash-hindsight/SKILL.md) — for the reviewed modules, PR scope, intent hints, and base marker. Do not recall again later in the run. Use relevant memory as additional review context, separate from `.mash/solutions/` results surfaced by `mash-learnings-researcher`. If Hindsight is unavailable or not configured, continue the review without blocking.

### Stage 2: Intent discovery

Understand what the change is trying to accomplish. The source of intent depends on which Stage 1 path was taken:

**PR/URL mode:** Use the PR title, body, and linked issues from GitHub MCP metadata. Supplement with commit messages from the PR if the body is sparse.

**Branch mode:** Run `git log --oneline ${BASE}..<branch>` using the resolved merge-base from Stage 1.

**Standalone (current branch):** Run:

```
echo "BRANCH:" && git rev-parse --abbrev-ref HEAD && echo "COMMITS:" && git log --oneline ${BASE}..HEAD
```

Combined with conversation context (plan section summary, PR description), write a 2-3 line intent summary:

```
Intent: Simplify tax calculation by replacing the multi-tier rate lookup
with a flat-rate computation. Must not regress edge cases in tax-exempt handling.
```

Pass this to every reviewer in their spawn prompt. Intent shapes *how hard each reviewer looks*, not which reviewers are selected.

**When intent is ambiguous:**

- **Interactive mode:** Ask one question using the platform's blocking question tool (`AskUserQuestion` in Claude Code, `AskQuestion` in Cursor, `question` in OpenCode, `request_user_input` in Codex, `ask_user` in Gemini, `ask_user` in Pi (requires the `pi-ask-user` extension)): "What is the primary goal of these changes?" Do not spawn reviewers until intent is established. **Claude Code only:** if `AskUserQuestion` has not yet been loaded this session (per the Interactive mode rules pre-load), call `ToolSearch` with query `select:AskUserQuestion` first before asking. Fall back to numbered options in chat only when the harness genuinely lacks a blocking tool or the call errors (e.g., Codex edit modes) — not because a schema load is required. Never silently skip the question.
- **Report-only and headless modes:** Infer intent conservatively from the branch name, diff, PR metadata, and caller context. Note the uncertainty in Coverage or Verdict reasoning instead of blocking.

### Stage 2b: Plan discovery (requirements verification)

Locate the plan document so Stage 6 can verify requirements completeness. Check these sources in priority order — stop at the first hit:

1. **`plan:` argument.** If the caller passed a plan path, use it directly. Read the file to confirm it exists.
2. **PR body.** If PR metadata was fetched in Stage 1, scan the body for paths matching `.mash/plans/*.md`. If exactly one match is found and the file exists, use it as `plan_source: explicit`. If multiple plan paths appear, treat as ambiguous — demote to `plan_source: inferred` for the most recent match that exists on disk, or skip if none exist or none clearly relate to the PR title/intent. Always verify the selected file exists before using it — stale or copied plan links in PR descriptions are common.
3. **Auto-discover.** Extract 2-3 keywords from the branch name (e.g., `feat/onboarding-skill` -> `onboarding`, `skill`). Glob `.mash/plans/*` and filter filenames containing those keywords. If exactly one match, use it. If multiple matches or the match looks ambiguous (e.g., generic keywords like `review`, `fix`, `update` that could hit many plans), **skip auto-discovery** — a wrong plan is worse than no plan. If zero matches, skip.

   This step exists for PRs that arrive without pipeline context — someone else's branch, or a PR opened outside `mash-pr`. A Mash Programming Skills-produced PR carries the plan path in its body, and `mash-work` and `mash-pr` always pass it explicitly, so steps 1-2 should resolve it. Everything auto-discovery finds is tagged `inferred` and never blocks a verdict on its own.

**Confidence tagging:** Record how the plan was found:
- `plan:` argument -> `plan_source: explicit` (high confidence)
- Single unambiguous PR body match -> `plan_source: explicit` (high confidence)
- Multiple/ambiguous PR body matches -> `plan_source: inferred` (lower confidence)
- Auto-discover with single unambiguous match -> `plan_source: inferred` (lower confidence)

If a plan is found, read its **Requirements** section — the R-IDs (R1, R2, etc.) listed there, plus **Implementation Units** (numeric subsections such as `### U1.`, `### U2.`, or `### Unit 1:` under `## Implementation Units`).

Also read these three sections when present — they carry the contracts the plan agreed to, and reviewing against a stated bar beats re-deriving one:

- **`## Goal Capsule`** — Objective, Means, and stop conditions. Use it to judge whether an omission is intentional (Stage 6 verdict) and whether the diff drifted past what the plan committed to.
- **`## Verification Contract`** — the repo's actual commands and quality gates. Where the diff's test and gate coverage falls short of what the plan named, that gap is concrete rather than a reviewer's opinion about adequacy.
- **`## Definition of Done`** — global and per-unit completion criteria, including the **cleanup criterion** (abandoned-approach code removed, not left in the diff).

Do **not** read a `Unit Index` table as a file footprint if the plan carries one — it is a navigation aid and deliberately non-exhaustive. Unit bodies are authoritative.

Store the extracted requirements list, the three contract sections when found, and `plan_source` for Stage 6. Do not block the review if no plan is found, or if a plan predates these sections — all of this is additive, not required.

### Stage 3: Select reviewers

Read the diff and file list from Stage 1. The 5 always-on personas are automatic. For each conditional persona and Mash Programming Skills agent in the persona catalog, decide whether the diff warrants it. This is agent judgment, not keyword matching.

**File-type awareness for conditional selection:** Instruction-prose files (Markdown skill definitions, JSON schemas, config files) are product code but do not benefit from runtime-focused reviewers. The adversarial reviewer's techniques (race conditions, cascade failures, abuse cases) target executable code behavior. For diffs that only change instruction-prose files, skip adversarial unless the prose describes auth, payment, or data-mutation behavior. Count only executable code lines toward line-count thresholds.

**`previous-comments` is PR-only AND comment-gated.** Only select this persona when both conditions hold:

1. Stage 1 gathered PR metadata (PR number or URL was provided as an argument, or GitHub MCP returned metadata for the current branch).
2. `hasPriorComments` from Stage 1 is true (the PR has at least one review submission or issue comment).

Skip it for standalone branch reviews with no associated PR, and skip it for PRs with no prior feedback yet -- there is nothing for the persona to verify, and a spawned subagent that returns empty findings still costs the full subagent startup overhead.

Cross-cutting personas are additive when the diff warrants them. A TypeScript API diff may warrant `api-contract` and `reliability`; a Hotwire UI change may warrant `reliability` when async or error-handling behavior changes. Structural and maintainability concerns are handled by the always-on `maintainability` persona — do not spawn extra reviewers for convention or philosophy passes.

**`data-migration` spawn gate.** Select `mash-data-migration-reviewer` only when the diff includes at least one migration or schema artifact: `db/migrate/*`, `db/schema.rb`, `db/structure.sql`, Alembic/Flyway/Liquibase migration paths, or explicit backfill/data-transform scripts (rake tasks, one-off data migration classes). **Do not spawn** for model-only changes, query-only refactors, serializers/controllers that reference columns without a migration or schema dump in the diff, or migration tests alone.

For `mash-deployment-verification-agent`, use the same migration-artifact gate when the change is risky (destructive DDL, backfills, NOT NULL without default, column renames/drops).

Announce the team before spawning:

```
Review team:
- correctness (always)
- testing (always)
- maintainability (always)
- ponytail (always)
- project-standards (always)
- mash-agent-native-reviewer -- diff adds a UI flow and an agent tool
- mash-learnings-researcher -- .mash/insights/ has markdown for this module
- security -- new endpoint in routes.rb accepts user-provided redirect URL
- data-migration -- adds migration 20260303_add_index_to_orders
- mash-deployment-verification-agent -- destructive migration with backfill
```

This is progress reporting, not a blocking confirmation.

### Stage 3b: Discover project standards paths

Before spawning, find relevant standards file paths for the `project-standards` persona:

1. Use the harness's native file-search/glob tool to find all `**/CLAUDE.md` and `**/AGENTS.md` in the repo.
2. Filter to those whose directory is an ancestor of at least one changed file. A standards file governs all files below it (e.g., `AGENTS.md` at a plugin root applies to everything under that plugin).

Pass the path list in a `<standards-paths>` block. The persona reads only relevant sections, keeping orchestrator context cheap.

### Stage 4: Spawn sub-agents

#### Model inheritance

**Never override the model on reviewer or validator sub-agents.** Always inherit the parent session model (agent frontmatter `model: inherit`, and omit any `model` / model-slug parameter on the dispatch primitive).

This applies to every persona, Mash Programming Skills agent, and Stage 5b validator — including correctness, security, adversarial, testing, maintainability, and the rest. Do not pass mid-tier, sonnet, mini, sol, xhigh, or any other model slug to reduce or increase cost (or perceived review quality).

The orchestrator also inherits the session model for intent discovery, reviewer selection, merge/dedup, and synthesis.

#### Run ID

Generate a unique run ID before dispatch. It scopes reviewer artifacts and the run artifact to one directory.

```bash
RUN_ID=$(date +%Y%m%d-%H%M%S)-$(head -c4 /dev/urandom | od -An -tx1 | tr -d ' ')
mkdir -p ".mash/qa/$RUN_ID"
```

Pass `{run_id}` to every persona sub-agent so they can write their full analysis to `.mash/qa/{run_id}/{reviewer_name}.json`.

**Report-only mode:** Skip run-id generation and directory creation. Do not pass `{run_id}` to agents. Agents return compact JSON only with no file write, consistent with report-only's no-write contract.

#### Spawning

Omit the `mode` parameter when dispatching sub-agents so the user's configured permission settings apply. Do not pass `mode: "auto"`.

**Model at dispatch time.** Do not set `model` (or any model-slug argument) on any subagent dispatch. Leave inheritance to the harness and each agent's `model: inherit` frontmatter so reviewers run on the same model as the parent session (e.g. Grok 4.5 when that is the session model).

**Bounded parallel dispatch.** Respect the current harness's active-subagent limit. Queue selected reviewers, dispatch only as many as the harness accepts, and fill freed slots as reviewers complete. Treat active-agent/thread/concurrency-limit spawn errors as backpressure, not reviewer failure: leave the reviewer queued and retry after a slot frees. Record a reviewer as failed only after a successful dispatch times out/fails, or when dispatch fails for a non-capacity reason.

Spawn each selected persona reviewer using the subagent template included below. Each persona sub-agent receives:

1. Their persona file content (identity, failure modes, calibration, suppress conditions)
2. Shared diff-scope rules from the diff-scope reference included below
3. The JSON output contract from the findings schema included below
4. PR metadata: title, body, and URL when reviewing a PR (empty string otherwise). Passed in a `<pr-context>` block so reviewers can verify code against stated intent
5. Review context: intent summary, file list, diff
6. Run ID and reviewer name for the artifact file path
7. **For `project-standards` only:** the standards file path list from Stage 3b, wrapped in a `<standards-paths>` block appended to the review context
8. **For `data-migration` only:** the resolved review base ref from Stage 1 (`BASE:` marker), wrapped in `<review-base>` inside the review context so schema drift checks never assume `main`

Persona sub-agents are project-read-only: review and return structured JSON. The only permitted write is their full analysis artifact under `.mash/qa/<run-id>/`.

Read-only here means **non-mutating**, not "no shell access." Reviewer sub-agents may use non-mutating inspection commands when needed to gather evidence or verify scope, including read-oriented `git` commands such as `git diff`, `git show`, `git blame`, and `git log`, plus GitHub MCP read tools. They must not edit project files, change branches, commit, push, create PRs, or otherwise mutate the checkout or repository state.

Each persona sub-agent writes full JSON (all schema fields) to `.mash/qa/{run_id}/{reviewer_name}.json` and returns compact JSON with merge-tier fields only:

```json
{
  "reviewer": "security",
  "findings": [
    {
      "title": "User-supplied ID in account lookup without ownership check",
      "severity": "P0",
      "file": "orders_controller.rb",
      "line": 42,
      "confidence": 100,
      "autofix_class": "gated_auto",
      "owner": "downstream-resolver",
      "requires_verification": true,
      "pre_existing": false,
      "suggested_fix": "Add current_user.owns?(account) guard before lookup"
    }
  ],
  "residual_risks": [...],
  "testing_gaps": [...]
}
```

Detail-tier fields (`why_it_matters`, `evidence`) are in the artifact file only. `suggested_fix` is optional in both tiers -- included in compact returns when present so the orchestrator has fix context for auto-apply decisions. If the file write fails, the compact return still provides everything the merge needs.

**Mash Programming Skills agents** (`mash-agent-native-reviewer`, `mash-learnings-researcher`, `mash-deployment-verification-agent`) are dispatched, when the persona catalog selects them, as standard Agent calls through the same bounded parallel scheduler as the persona agents. Give them the same review context bundle the personas receive: entry mode, any PR metadata gathered in Stage 1, intent summary, review base branch name when known, `BASE:` marker, file list, diff, and `UNTRACKED:` scope notes. Do not invoke them with a generic "review this" prompt. For `mash-deployment-verification-agent`, also pass the applicability reason (for example, which migration files triggered the agent). Their output is unstructured and synthesized separately in Stage 6. Schema drift is handled by the `data-migration` persona as structured findings.

### After reviewers return

When every selected reviewer has returned or failed, read `references/synthesis-and-followup.md` and follow it through merge, validation, synthesis, quality gates, and post-review routing. Do not read that file before dispatch finishes.

## Fallback

If the platform doesn't support parallel sub-agents, run reviewers sequentially. If the platform supports sub-agents but caps active concurrency, use the bounded queueing rules in Stage 4 rather than treating cap-related spawn failures as reviewer failures. Everything else (stages, output format, merge pipeline) stays the same.

---

## Included References

### Persona Catalog

@./references/persona-catalog.md

### Subagent Template

@./references/subagent-template.md

### Diff Scope Rules

@./references/diff-scope.md

### Findings Schema

@./references/findings-schema.json

