# Live-home contract

This workspace is a **live-home**: a personal, always-on checkout (agent home, not a product repo). The sole user is the owner. Git exists for **backup and sync between two machines**, not for collaboration.

Slash commands keep the same names (`/rosey-brainstorm`, `/rosey-plan`, `/rosey-work`, `/rosey-qa`, `/rosey-lint`). Each live-home `SKILL.md` is a full copy with this contract baked in.

## Git

- Stay on `master` (or `main` if that is the only default). Never create `feature/*` branches. Never use git-flow.
- Never stash. Never `git stash push` / `pop` / `apply`.
- Never open, update, or mention PRs. Do not invoke `rosey-pr`. Do not use GitHub MCP pull-request tools.
- Mixed uncommitted work is expected. Files are written continuously. Do not try to isolate features, clean the tree, or pause other in-progress edits.
- Touch and commit **only files from this session** (`FILES_CHANGED`). Leave unrelated dirty and untracked files alone.
- Do not `git add .`. Do not `git restore` / `checkout --` files you did not change this session.
- Optional sync: `git fetch` is fine. `git pull` only when the working tree has **no** unrelated conflicts you would need a stash to survive — if pull would require a stash, skip pull and note it. After a user-requested commit, `git push` to origin for backup.
- Commit messages: conventional / gitchangelog tags only if `.gitchangelog.rc` exists; otherwise a short imperative subject. No PR attribution footers.

## Collaboration and process

- No reviewers, no teammates, no issue trackers, no "split into PRs."
- Plan and implement as one person landing on master. Follow-up work is later commits on the same branch, not a separate PR.
- Repo-relative paths still matter (two machines). Do not use absolute paths in artifacts.

## Tooling

- These homes run **on the host**. Docker-via-Make does not apply. Host `node` / `python` / package managers are allowed when the home already uses them.
- Prefer serial, in-place execution. No worktrees (they hide the live files). No parallel writers in the same git index.
- `rosey-pr`, `rosey-parallel`, and `rosey-epic-decompose` are **not installed** here. Never attempt PR creation or parallel/worktree orchestration; if a plan is too large for one run, reduce its scope instead.

## Dirty-tree rule

A non-empty `git status` is normal. Never stop a skill because the tree is dirty. Never ask the user to stash or commit unrelated files before continuing.
