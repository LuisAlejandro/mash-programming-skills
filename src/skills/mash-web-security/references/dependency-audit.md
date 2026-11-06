# Dependency audit

Run each matching auditor. More than one lockfile means more than one audit. Do not skip an ecosystem because another one ran.

| Present in the project root | Command | No manifest |
| --- | --- | --- |
| `package-lock.json` | `npm audit --json` | |
| `pnpm-lock.yaml` | `pnpm audit --json` | |
| `yarn.lock` | `yarn npm audit --json` (Yarn Berry) or `yarn audit --json` (classic Yarn, if the Berry command is rejected) | |
| `requirements.txt` | `pip-audit -r requirements.txt -f json` | |
| `pyproject.toml` plus `uv.lock`, `poetry.lock`, `Pipfile.lock`, or `pdm.lock` | `pip-audit -f json` from the project root | |
| `pyproject.toml` with none of those lockfiles | | `Skipped`, reason "Python manifest has no lockfile" |
| None of the rows above for an ecosystem | | `Skipped`, reason "no Node manifest" or "no Python manifest" |

A lockfile that is not in the table is `Skipped` with the filename as the reason. Do not guess an auditor for it.

## When the tool is missing

The manifest exists and the auditor is not on `PATH` (and, in container mode, not invocable through Make or Compose): `Blocked (needs human verify)`.

- npm, pnpm, or yarn: install that package manager, or use the project's documented Make or Compose target. Do not switch ecosystems to force a result.
- pip-audit: install `pip-audit` into the environment the docker-via-make rule allows. Do not substitute `pip list` or a manual reading of the lockfile as if it were an audit.

## Reading the output

npm, pnpm, and yarn JSON: one Fail row per package name under the vulnerability map. Severity is the advisory severity, mapped by the mash-project-review status vocabulary (`critical` → `P0`, `high` → `P1`, `moderate` → `P2`, `low` → `P3`). Check id: `deps.npm.<package>`, `deps.pnpm.<package>`, or `deps.yarn.<package>`.

`npm audit` exits non-zero when it finds vulnerabilities. That exit is a set of Fail rows when stdout is JSON. Stdout that is not JSON is `Blocked (needs human verify)` with the stderr tail.

pip-audit JSON: one Fail row `deps.pip.<package>` per dependency that has a vulnerability. No dependencies with vulnerabilities, and a clean exit, is `Pass` on `deps.pip-audit`.

Info-level npm entries are `Skipped` with the package name, not Fail rows.

Paste the command and the JSON object for each Fail into an evidence block. Redact registry tokens if the tool echoed them.
