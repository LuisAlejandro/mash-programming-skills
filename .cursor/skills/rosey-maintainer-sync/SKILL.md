---
name: rosey-maintainer-sync
description: Sync maintainer ops to every repo, then coordinate batched subagents to generate repo-specific maintainer files. Use when the user asks to sync all repos, roll out maintainer-tools templates, refresh fleet-wide ops files, or generate common repo docs, Docker, env, bumpversion, Makefile dedup, release preflight targets, and optional pr.yml CI security patches (never full workflow rewrites).
argument-hint: "[--force] (fleet-wide static sync; dynamic phase has no CLI flag)"
---

# Rosey Maintainer Sync

Fleet sync from this repo (`rosey-maintainer-tools`) has two phases:

1. **Static sync:** run `rosey-maintain sync` through the local wrapper. This writes deterministic templates, updates `rosey/maintainer-manifest.json`, and runs agentic install in every registered repo.
2. **Dynamic generation:** launch Cursor subagents in batches of 4 **after** static sync completes. Each repo gets fresh context for repo-specific files.

Do not invoke LLMs from Python. The skill is the LLM entrypoint; the Python CLI stays deterministic.

## Virtualenv and CLI

Always run from the **repository root**. Use the wrapper — it creates `virtualenv/` if missing, installs this package editable, then runs `rosey-maintain`:

```bash
bash scripts/rosey-maintain.sh sync
```

`rosey-maintain sync` processes **every** repo in `registry/repos.yaml` — there is no per-repo sync flag. To sync one repo only, use `rosey-maintainer-add` on a fresh registration or temporarily narrow the registry (debug only).

With `--force` when sync skips drifted managed files:

```bash
bash scripts/rosey-maintain.sh sync --force
```

**Drift and `--force`:** sync compares each managed file to hashes in `rosey/maintainer-manifest.json`. If a file was edited after the last sync, it is skipped unless `--force`. **`rosey/maintainer-manifest.json`** is always rewritten. **`Makefile`**, **`.github/workflows/pr.yml`**, **`.github/workflows/push.yml`**, **`.github/workflows/release.yml`**, and **`.semgrepignore`** are repo-owned and are **not** synced.

Requires **Python 3.11+** on PATH (`python3.11`, `python3.12`, …). The wrapper picks the first match.

Do **not** call a global `rosey-maintain`, `pip install -e .` on the system Python, or `PYTHONPATH=src` unless the wrapper fails and you are debugging.

Manual venv refresh (only if dependencies changed and wrapper behaves oddly):

```bash
bash scripts/ensure-venv.sh
virtualenv/bin/rosey-maintain sync
```

**Agentic install:** after writing ops files, sync runs `agentic_env_path/install.sh --write-pin --agents` in each repo (`agentic_env_path` in `registry/repos.yaml`, default `../rosey-agentic-env`). Failure aborts that repo's sync.

## Workflow

1. `cd` to `rosey-maintainer-tools` root.
2. Read `registry/repos.yaml` and, for each repo, resolve **profile**, **history_file** (profile defaults + `overrides`), **release_template**, and **open_source** — same merge order as `repo_context()` in `cli.py`.
3. Run `bash scripts/rosey-maintain.sh sync` (add `--force` only if requested or prior run reported skipped drifted files).
4. **After static sync succeeds**, launch dynamic generation subagents (`generalPurpose` or equivalent) in batches of **4 repos at a time**. Wait for a batch to finish before launching the next batch.
5. After all batches complete, summarize per repo: static sync result, dynamic files changed, evidence used, blockers, and uncommitted changes.
6. Do **not** commit in app repos unless the user asks.

## Profiles and registry

Every registered repo should use **`python`** or **`node`** (see `profiles/*.yaml`).

| Profile | Bundles (static sync) |
|---------|------------------------|
| **python** | `ops-release`, `ops-legal`, `ops-python`, `ops-vscode`, `ci-base` |
| **node** | `ops-release`, `ops-legal`, `ops-vscode`, `ci-base` |

**Profile defaults (not exhaustive):**

| Setting | python | node |
|---------|--------|------|
| `history_file` | `HISTORY.rst` | `HISTORY.md` (CLI default when profile omits it) |
| `dependabot_ecosystem` | pip | npm |
| `semgrep_language_ruleset` | p/python | p/javascript |
| `release_template` | `verify-only` | `verify-only` (registry metadata; repo owns `release.yml`) |
| `release_ci_workflow` | `push.yml` | `push.yml` (CLI default) |

Preflight is **repo-owned** via Makefile `release-preflight` (chains `image` → `dependencies` →
`build` → `format` → `lint` → `test`). `scripts/lib.sh` calls that target once and fails if the
working tree is dirty afterward. PR CI uses a different order (lint/test before build) — do not
reorder either sequence to match the other.

### Doc-format family

Resolved `history_file` drives the whole documentation set (static + dynamic):

| `history_file` | MAINTAINER | README | RELEASE_DESCRIPTION | `.gitchangelog.tpl` |
|----------------|------------|--------|---------------------|---------------------|
| `HISTORY.rst` | `MAINTAINER.rst` | `README.rst` | `RELEASE_DESCRIPTION.rst` | `gitchangelog.rst.tpl` |
| `HISTORY.md` | `MAINTAINER.md` | `README.md` | `RELEASE_DESCRIPTION.md` | `gitchangelog.md.tpl` |

Fleet examples: most **python** repos use RST; **agoras-actions** and **dockershelf** override to `HISTORY.md` → full MD family. **Node** repos default to MD.

**Exceptions:** `AUTHORS` / `CLA` follow the same rst/md rule (`AUTHORS.rst` vs `AUTHORS.md`). OSS PR/issue templates (`.github/PULL_REQUEST_TEMPLATE.md`, issue templates) are **always Markdown**, even on RST python repos.

When `history_file` changes, dynamic generation must **delete orphan siblings** in the wrong extension (`MAINTAINER.*`, `README.*`, `RELEASE_DESCRIPTION.*`).

### `release_template` (repo-owned `release.yml`)

Registry `release_template` documents which release workflow shape the repo uses. Static sync **does not** write `.github/workflows/release.yml`.

| Value | Typical use |
|-------|-------------|
| `verify-only` | Default — post-publish verify on `release: published` |
| `single-pypi` | e.g. spices — single-package PyPI publish |
| `monorepo-pypi` | e.g. agoras — multi-package PyPI publish |

`release.yml` does **not** reference `push.yml`. The **release script** (`scripts/lib.sh`) waits for `release_ci_workflow` (default **`push.yml`**) on `release/*` branches before tagging — for **all** `ops-release` repos (python and node). Each repo must maintain its own `push.yml` (or override `release_ci_workflow`).

### Registry rules

- Set `profile: python` or `profile: node` — prefer fixing the repo over per-repo preflight overrides.
- `bundles:` on a repo entry **replaces** the profile's bundle list entirely.
- **Allowed overrides:** `history_file`, `release_template`, `pypi_packages`, `dependabot_updates`, `dependabot_extra_directories`.
- **`dependabot_updates`:** list of `{ecosystem, directory}` (replaces the default root entry). Use for nested manifests or mixed ecosystems (`npm` + `gomod`). `dependabot_extra_directories` still appends same-ecosystem folders when `dependabot_updates` is unset.
- **Deprecated overrides** (do not add): `post_bump_commands` — use `.bumpversion.cfg` `[rosey-maintainer]` instead.

The legacy **`minimal`** profile remains in `profiles/minimal.yaml` for edge cases; fleet repos should not use it.

Repos with **`open_source: true`** in registry get OSS PR/issue templates on static sync and `CONTRIBUTING.*` in dynamic generation.

## Preflight contract

Python and node profiles share the same **release preflight** shape (repo-owned Makefile):

`release-preflight` chains `make image` → `make dependencies` → `make build` → `make format` →
`make lint` → `make test`. That local sequence writes format then verifies. PR CI on tetra node
apps is `make image` → `make dependencies` → `make lint` → `make test` → `make build` (fail cheap).
Do not reorder Makefile preflight to match CI, or CI to match Makefile.

`scripts/release.sh` runs **`make release-preflight`** via `lib.sh`, then **stops** if the working
tree is dirty — otherwise release continues to bumpversion.

- **Python:** `make test` runs **coverage** (typically `tox -e coverage`); `make dependencies` may be `@:`.
- **Node:** tools are repo-specific (ESLint, Prettier, `tsc`, Jest, `go test`, etc.).

Static sync does **not** generate Makefile target bodies. Dynamic generation **must verify** all required targets exist and **implement them** when missing.

See `references/preflight-conventions.md` and `references/makefile-dedup.md`.

## Static Sync Scope

`rosey-maintain sync` owns deterministic files only:

- release scripts (`lib.sh`, `release.sh`, `rollback.sh`) — replaces legacy `hotfix.sh`; `release.sh` reads `[rosey-maintainer] post_bump_commands` from `.bumpversion.cfg` at runtime
- changelog config (`.gitchangelog.rc`, `.gitchangelog.tpl` — md vs rst from `history_file`)
- **MAINTAINER docs** — only when `ops-release` is in bundles; path from doc-format family above (**static only** — do not regenerate in dynamic phase)
- legal files (`ops-legal`: LICENSE, `.editorconfig`, `AUTHORS.rst`/`.md`, `CLA.rst`/`.md` per `history_file`)
- `.vscode/settings.json` (`ops-vscode` — python vs node template)
- Python tooling config when `ops-python` in bundles: `setup.cfg`, `pyproject.toml`
- GitHub workflows: `cache-cleanup.yml`, `dependabot.yml`, `pr-auto-merge.yml` (`ci-base`)
- open-source PR and issue templates when `open_source: true` (always Markdown)
- `rosey/maintainer-manifest.json` (local drift manifest; gitignored)
- `.gitignore` — adds `# Rosey Maintainer Tools` header and `rosey/maintainer-manifest.json` when missing

If the manifest was previously committed, run `git rm --cached rosey/maintainer-manifest.json` once per repo after sync.

- `.bumpversion.cfg` bootstrap stub when missing (minimal; not the full file list)

**Repo-owned (not static sync):** `Makefile` (docker, release, preflight targets), `.github/workflows/pr.yml` (including Semgrep — named **Code Quality** job *or* a Semgrep step inside **Repository Checks**), `.github/workflows/push.yml`, `.github/workflows/release.yml`, `.semgrepignore`.

`pr-auto-merge.yml` is static-synced (`ci-base`). The dynamic phase may **patch** existing `pr.yml` for CI trigger/checkout security only; it must not rewrite workflow jobs wholesale.

## Dynamic Generation Scope

Each subagent should overwrite or create these repo-specific files (paths from resolved doc-format family):

- `README.md` or `README.rst` (include `Current version: …` when `.bumpversion.cfg` tracks README)
- `RELEASE_DESCRIPTION.md` or `RELEASE_DESCRIPTION.rst`
- `.env.example`
- `.bumpversion.cfg` (full version file list + optional `[rosey-maintainer] post_bump_commands`)
- `HISTORY.md` or `HISTORY.rst` when missing and `ops-release` applies
- `tox.ini` (`lint` / `format` / `coverage` envs) for **python** repos using tox
- **Makefile:** deduplication and preflight/docker/release targets per `makefile-dedup.md` and `preflight-conventions.md`
- `.github/workflows/pr.yml` — CI security patch only when profile includes `ci-base` and file exists (see `workflow-generation.md`); never touch `push.yml` or `pr-auto-merge.yml`
- `CONTRIBUTING.md` or `CONTRIBUTING.rst` only when `open_source: true`
- `Dockerfile` and `docker-compose.yml` when profile is `python` or `node` and compose is required for `make start`

**Do not regenerate** `MAINTAINER.md` / `MAINTAINER.rst` — static sync owns that file.

**Fleet migration cleanup** (when present; static sync will not remove these):

- Delete orphan `scripts/hotfix.sh` (replaced by `rollback.sh` + `make undo-release`)
- Remove `hotfix` / `make hotfix` from README, CONTRIBUTING, and non-managed Makefile help
- Delete orphan `MAINTAINER.*`, `README.*`, `RELEASE_DESCRIPTION.*` in the wrong extension for resolved `history_file`
- Delete stale `.github/workflows/keepalive.yml` if present (no longer generated)

**Semgrep (verify-only — do not implement a missing named job):**

| Placement | Repos |
|-----------|-------|
| Named **Code Quality** job | agoras, agoras-actions, dockershelf, spices, luisalejandro.org |
| Semgrep step inside **Repository Checks** | helpmarket, morphile, nuncia, whol, wholmaster, wholmaster-website |

`.semgrepignore` is **repo-owned**. Do not recreate CodeQL or a separate `code-quality.yml`. Do **not** extract Semgrep from tetra **Repository Checks** onto GitHub-hosted runners. Do **not** run `protect-github --apply` during fleet sync — that is operator follow-up after reviewing required-check names.

If a file already exists, replace it with the regenerated version after preserving any still-accurate project-specific details.

For `.bumpversion.cfg`, always overwrite with the complete discovered file list. For `Makefile`, implement or verify required targets; remove duplicate definitions only.

Makefile target bodies stay repo-specific. Do not rewrite existing CI workflow jobs to call `make lint` / `make test` unless the user asks. Do not reorder CI `lint`/`test`/`build` to match Makefile preflight.

## Subagent Run Order

Within each repo, generate files in this order:

1. `.env.example` and Docker files (when applicable)
2. Makefile: preflight targets (`image`, `dependencies`, `build`, `lint`, `format`, `test`, `release-preflight`) then deduplication
3. `.bumpversion.cfg`, `HISTORY.*`, and docs (`README`, `CONTRIBUTING`, etc.)
4. `tox.ini` (python, when using tox)
5. Orphan cleanup (`hotfix.sh`, wrong-extension doc-family files)
6. Optional `pr.yml` CI security patch last (when `ci-base` and file exists)

## Subagent Prompt Contract

For each repo subagent, include:

- repo name
- absolute repo path
- profile
- resolved `history_file`, `readme_file`, `release_description_file`, and maintainer filename (for reference only — **do not edit MAINTAINER**)
- `release_template` (resolved)
- `open_source` value
- this instruction: "Do not commit changes."
- contents of `references/repo-generation-prompt.md`
- contents of `references/preflight-conventions.md` when profile is `python` or `node`
- contents of `references/workflow-generation.md` when profile includes `ci-base`
- contents of `references/ci-npm-cache.md` when profile is `node` (verify-only; do not insert caches)
- contents of `references/bumpversion-generation.md` when profile includes `ops-release`
- contents of `references/makefile-dedup.md` when profile is `python` or `node`
- contents of `references/contributing-baseline.md` when `open_source: true`
- contents of `references/docker-generation.md` when profile is `python` or `node`

Subagents must return:

- files changed
- source evidence used (metadata files, Makefile targets, version file paths, env-var references, current Docker files, existing workflows)
- env vars discovered and whether `.env.example` was empty or overwritten
- `.bumpversion.cfg` sections added, current version source, `[rosey-maintainer] post_bump_commands` (Y/N)
- preflight targets present (image/dependencies/build/lint/format/test/release-preflight Y/N); docker/release targets present (Y/N); tools used for each
- Makefile targets removed as duplicates (list names)
- orphan files removed (`hotfix.sh`, wrong-extension doc-family files) (Y/N)
- `pr.yml` patched (Y/N), trigger is `pull_request` only (no `workflow_dispatch`) (Y/N), approve/merge removed (Y/N), Semgrep present as named Code Quality job **or** Repository Checks step (Y/N), placement matches repo family (Y/N), cost-opt PR structure preserved (filter / skip twins / draft `if` / timeouts / concurrency) (Y/N), `pr-auto-merge.yml` synced (Y/N); Cursor automation retrigger is `synchronize` (Y/N); `protect-github --apply` skipped (operator follow-up) (Y/N)
- `push.yml` left untouched (confirm)
- assumptions or blockers

## Batch Size

Use batches of 4 repos:

1. Launch up to 4 subagents concurrently (`generalPurpose` or equivalent).
2. Wait for those subagents to complete.
3. Review their summaries for blockers or collisions.
4. Continue with the next batch.

If a repo blocks on missing context or an ambiguous destructive change, leave that repo untouched where possible and report the blocker.

## Failure handling

- **Repo path missing** — stop and report; fix `registry/repos.yaml` path.
- **Skip drifted file** — re-run with `--force` or fix the file manually first.
- **Partial fleet sync** — if one repo's agentic install fails, earlier repos may already be updated; report which repos completed.
- **Agentic install failed** — report repo name and `install.sh` stderr; check `agentic_env_path`.
- **`python3 -m venv` failed** — report Python version (`requires-python >= 3.11` in `pyproject.toml`).
- **Missing `push.yml`** — release script cannot complete gate 2; do not create via static sync — repo must have an existing push workflow or override `release_ci_workflow`.
- **Missing preflight targets** — implement `image`, `dependencies`, `build`, `lint`, `format`, `test`, and `release-preflight` in repo Makefile (and `tox.ini` for python).
- **Wrong doc family on disk** — regenerate canonical files and delete orphan MAINTAINER/README/RELEASE_DESCRIPTION siblings.
- **Subagent failed** — report repo name, partial files changed if known, and the next safest retry.

## Out of scope

- Registering new repos (`rosey-maintainer-add`)
- Invoking LLMs from Python or `rosey-maintain`
- Rewriting `dependabot.yml` or `cache-cleanup.yml` (static sync); creating a keepalive workflow
- Running `protect-github --apply` during fleet sync (operator follow-up)
- Registry `post_bump_commands` overrides (use `.bumpversion.cfg` instead)
- Rewriting or creating `pr.yml`, `push.yml`, or `release.yml` CI jobs (patch CI trigger/checkout on existing `pr.yml` only; never edit `pr-auto-merge.yml` by hand in app repos)
- Regenerating `MAINTAINER.md` / `MAINTAINER.rst` in the dynamic phase
