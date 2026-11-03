# Branch creation from default branch

Local `<base>` may have stale commits (another session/worktree advanced it) or commits the user authored intending to branch from later. Local git can't distinguish these — ask when unpushed commits are present in interactive mode. In non-interactive mode, never ask; stop when preserving or excluding local commits would materially change the PR.

Integration PRs use git-flow feature branches: `feature/<slug>`.

**The feature branch is created in a worktree, never by checking it out in the shared checkout.** The user stays on `<base>`. `SHIP_ROOT` is the worktree path; every commit, merge, and push in `SKILL.md` Step 3 runs there.

## Decision flow

### 1. Fetch fresh remote base

```bash
git fetch --no-tags origin <base>
```

If fetch fails (network, auth, no remote), use the fallback at the bottom.

### 2. Check for unpushed local commits on `<base>`

```bash
git log origin/<base>..HEAD --oneline
```

- **Empty output:** set `BASE_REF=origin/<base>` and proceed to step 3.
- **Non-empty output:** show the commit list and ask (per the "Asking the user" convention in `SKILL.md`):

  > "Local `<base>` has N unpushed commits not on `origin/<base>`. Carry them onto the new feature branch, or leave them on local `<base>`?"

  - **Carry forward** → `BASE_REF=HEAD`. The worktree starts from local HEAD, preserving the commits.
  - **Leave on `<base>`** → `BASE_REF=origin/<base>`. The worktree starts clean; commits remain on local `<base>` and the primary checkout is not touched.

  Never default silently in interactive mode — carrying foreign commits into a PR is worse than asking again. In non-interactive mode, stop with a blocker instead of choosing.

### 3. Derive feature slug

- From `plan:<path>`: basename without extension, strip the leading date and sequence/type tokens (`YYYY-MM-DD-NNN-<type>-`) and any trailing `-plan` suffix, kebab-case, max ~50 characters.
  Example: `.mash/plans/2026-05-29-001-feat-seo-phase-2-content-plan.md` → `seo-phase-2-content`.
- Otherwise: kebab-case summary of the change.
- Do not use `test`, `chore`, or `release` as the slug prefix.

This rule is duplicated verbatim in `SKILL.md`. Both copies must agree — `mash-pr`'s plan ↔ branch guard stops before commit when they diverge.

### 4. Create the feature worktree

Uncommitted work has to travel from the shared checkout into the worktree, because a new worktree starts from a commit. Check for it first:

```bash
git status --porcelain --untracked-files=all
```

- **Clean tree:** `SHIP_BASE="$BASE_REF"`, no stash.
- **Dirty tree:** stash it, so the working copy the user was preparing is the one that lands on the feature branch:

  ```bash
  STASH_MSG="mash-pr: ship feature/<slug>"
  git stash push -u -m "$STASH_MSG"
  SHIP_BASE="$BASE_REF"
  ```

  The stash rides on `$BASE_REF`, the same ref the branch starts from, because the stash was taken against local `HEAD`: its diff assumes those commits are present. Carry-forward therefore applies it cleanly. Leaving the commits on `<base>` can conflict when the stash touches the same files — that is the `status: conflict` path below, which keeps the stash and names it, never a silent loss.

Then create the worktree:

`HELPER` is this skill's directory joined with `../mash-brainstorm/scripts/feature_worktree.py`, resolved to an absolute path once (relative skill paths do not survive an arbitrary working directory). `REPO` is `git rev-parse --show-toplevel` of the shared checkout.

```bash
SHIP_JSON=$(python3 "$HELPER" ship-create <slug> --base "$SHIP_BASE" --repo "$REPO")
SHIP_ROOT=$(printf '%s' "$SHIP_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["worktree"])')
```

`status: blocked` means the branch or worktree path already exists. Report the blocker and stop; do not fall back to `git checkout` in the shared checkout.

If a stash was created, apply it inside the worktree:

```bash
python3 "$HELPER" stash-apply "$SHIP_ROOT" --message "$STASH_MSG"
```

- `status: applied` — the edits are in the worktree, staged state preserved. Continue.
- `status: conflict` — the worktree holds conflict markers, the stash is still intact, and the shared checkout is clean. Stop, name both paths, and give the recovery commands (`git -C "$SHIP_ROOT" status`, `git stash list`). Do not auto-resolve.
- `status: blocked` — no matching stash. Stop and report; the stash may have been consumed or renamed.

A clean apply is required before continuing. The stash is dropped only after the commit succeeds (Step 3), never here:

```bash
python3 "$HELPER" stash-drop --message "$STASH_MSG" --repo "$REPO"
```

### 5. Work in the worktree

From here `SKILL.md` Step 3 changes directory semantics, not steps: stage, commit, merge `<base>`, and push all run with the worktree as the working directory. The shared checkout stays on `<base>` with a clean tree.

Report the worktree path in the final summary. Never leave the user guessing where their branch went.

## Fetch failure fallback

If `git fetch` fails, branch from the current local HEAD when it is not `<base>` (`SHIP_BASE=HEAD`); otherwise stop with a blocker in non-interactive mode or ask in interactive mode.

```bash
SHIP_JSON=$(python3 "$HELPER" ship-create <slug> --base HEAD --repo "$REPO")
```

Note in the user-facing summary that base freshness was not verified. Skip the unpushed-commits check — without a fresh `origin/<base>`, the answer is unreliable.

## Cleanup

The worktree outlives the push: it holds the branch until the PR is created, and the user may want to keep editing there. Remove it only after a successful push, and only when its tree is clean:

```bash
python3 "$HELPER" remove "$SHIP_ROOT"
```

Interactive: offer removal once the PR exists. Non-interactive: keep the worktree and report the path. The helper refuses a dirty worktree without `--force`, and refuses any path outside `.mash/`.
