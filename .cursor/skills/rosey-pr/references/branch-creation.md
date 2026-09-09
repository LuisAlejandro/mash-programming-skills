# Branch creation from default branch

Local `<base>` may have stale commits (another session/worktree advanced it) or commits the user authored intending to branch from later. Local git can't distinguish these — ask when unpushed commits are present in interactive mode. In non-interactive mode, never ask; stop when preserving or excluding local commits would materially change the PR.

Integration PRs use git-flow feature branches: `feature/<slug>`. This matches `pr-auto-merge.yml` head filters (`feature/**`).

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

  - **Carry forward** → `BASE_REF=HEAD`. The new branch starts from local HEAD, preserving the commits.
  - **Leave on `<base>`** → `BASE_REF=origin/<base>`. The new branch starts clean; commits remain on local `<base>`.

  Never default silently in interactive mode — carrying foreign commits into a PR is worse than asking again. In non-interactive mode, stop with a blocker instead of choosing.

### 3. Derive feature slug

- From `plan:<path>`: basename without extension, strip the leading date and sequence/type tokens (`YYYY-MM-DD-NNN-<type>-`) and any trailing `-plan` suffix, kebab-case, max ~50 characters.
  Example: `rosey/plans/2026-05-29-001-feat-seo-phase-2-content-plan.md` → `seo-phase-2-content`.
- Otherwise: kebab-case summary of the change.
- Do not use `test`, `chore`, or `release` as the slug prefix.

This rule is duplicated verbatim in `SKILL.md` and `rosey-work`'s branch setup. All three must agree — `rosey-pr`'s plan ↔ branch guard stops before commit when they diverge.

### 4. Create the feature branch

Ensure git-flow is initialized, check out the base ref, then start the feature:

```bash
git config --get gitflow.branch.master >/dev/null 2>&1 || git flow init -d
git checkout "$BASE_REF"
git flow feature start <slug>
```

`git flow feature start` creates and checks out `feature/<slug>`.

If checkout fails because uncommitted changes would be overwritten, stash and retry from step 4:

```bash
git stash push -u -m "rosey-pr: pre-branch feature/<slug>"
git checkout "$BASE_REF"
git flow feature start <slug>
git stash pop
```

If `git stash pop` reports conflicts, surface the conflict output and the stash ref — do not auto-resolve. In non-interactive mode, stop with a blocker.

## Fetch failure fallback

If `git fetch` fails, branch from current local HEAD when it is not `<base>`; otherwise stop with a blocker in non-interactive mode or ask in interactive mode.

```bash
git config --get gitflow.branch.master >/dev/null 2>&1 || git flow init -d
git flow feature start <slug>
```

Note in the user-facing summary that base freshness was not verified. Skip the unpushed-commits check — without a fresh `origin/<base>`, the answer is unreliable.
