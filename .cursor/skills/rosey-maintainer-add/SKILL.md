---
name: rosey-maintainer-add
description: Register a new app repo in rosey-maintainer-tools, add it to rosey.code-workspace, and sync maintainer ops plus agentic env. Use when onboarding a new repo to the Rosey fleet or adding a repo to the maintainer registry.
argument-hint: "<name> <path> --profile python|node|minimal> [--force]"
---

# Rosey Maintainer Add

Onboard one app repo into the maintainer fleet.

## Virtualenv and CLI

Always run from the **repository root**. Use the wrapper — it creates `virtualenv/` if missing, installs this package editable, then runs `rosey-maintain`:

```bash
bash scripts/rosey-maintain.sh add <name> <path> --profile <python|node|minimal>
```

Example:

```bash
bash scripts/rosey-maintain.sh add myapp ../rosey/myapp --profile python
```

Optional `--force` if managed files already exist and drifted from the manifest.

Requires **Python 3.11+** on PATH (`python3.11`, `python3.12`, …). The wrapper picks the first match.

Do **not** call a global `rosey-maintain`, `pip install -e .` on the system Python, or `PYTHONPATH=src` unless the wrapper fails and you are debugging.

Manual venv refresh (only if dependencies changed and wrapper behaves oddly):

```bash
bash scripts/ensure-venv.sh
virtualenv/bin/rosey-maintain add myapp ../rosey/myapp --profile python
```

## What `add` does

1. Appends the repo to `registry/repos.yaml` (`path` + `profile`).
2. Inserts the repo folder into `rosey.code-workspace` (before `rosey-agentic-env`).
3. Syncs that repo: managed ops files, `rosey/maintainer-manifest.json` (gitignored), agentic install.

**Makefile**, **`.github/workflows/pr.yml`**, and **`.semgrepignore`** are repo-owned. Dynamic generation must verify docker/release/preflight targets and the Semgrep **Code Quality** job exist (see `preflight-conventions.md`, `workflow-generation.md`). CodeQL is **not** used.

## After add (python / node)

Remind the user to apply GitHub rulesets once the repo is on GitHub Pro (or public):

```bash
bash scripts/rosey-maintain.sh protect-github --apply --repo <name>
```

Use `--owner <org>` when the registry entry overrides `github_owner` (e.g. Dockershelf). Rulesets require **Code Quality** and PR job checks only — no `code_scanning` / CodeQL merge rule.

## Workflow

1. `cd` to `rosey-maintainer-tools` root.
2. Confirm **name**, **path**, and **profile** with the user if not provided in `$ARGUMENTS`.
3. Verify the path exists and is a git repo (recommended, not enforced by CLI).
4. Run `bash scripts/rosey-maintain.sh add …`.
5. Summarize: registry entry, workspace folder added (or already present), sync output (including managed **Code Quality** block in `pr.yml` when profile is python/node).
6. For python/node repos, remind the user to run `protect-github --apply` on GitHub when ready (see **After add** above).
7. Remind the user to commit in this repo (`registry/repos.yaml`, `rosey.code-workspace`) when ready. Do not commit unless asked.

## New profiles

`add` only assigns existing profiles. To create a new profile type, add `profiles/<name>.yaml` here first, then use `--profile <name>`.

## Out of scope

- Fleet-wide sync (`rosey-maintainer-sync`)
- Per-repo overrides (`bundles`, `overrides` in registry) — edit `registry/repos.yaml` by hand after add if needed
