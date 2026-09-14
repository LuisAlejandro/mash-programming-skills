# Scope extraction

Required read at Phase 1. Turns the merged-PR locator list into clustered user-visible journeys. PRs are evidence of change. Journeys are the unit of test.

## Skip rules

Judge each PR before it enters a cluster. Record every skip in the report's **Out of scope** table. A skipped PR is auditable; a silently dropped PR is a bug.

**Skip** (do not matrix) when the change is only:

- lockfile or manifest-only (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `Pipfile.lock`, `poetry.lock`, `uv.lock`, version bumps in `package.json` / `pyproject.toml` with no other product files)
- automated release / changelog-only / tag chore
- CI-only (`.github/workflows/*` with no product code or user-facing copy)
- docs-only (`README.md`, `docs/**`, skill/agent markdown) with no product UI copy
- generated noise (lockfiles plus formatter config) with no user-visible surface

When in doubt, **do not skip**. A false skip hides shipped behavior. A false keep costs one extra cluster row, which Phase 2c can drop.

## Classify survivors

For each remaining PR, assign one or more surfaces from title, body, and file paths:

| Kind | Signal | What it becomes |
| --- | --- | --- |
| **User-visible** | routes, views, pages, components, copy, CSS that paints a screen, permissions that gate a screen | candidate journey surfaces (route / flow / job) |
| **Non-UI, user-affecting** | API, agent tool, email template, background job, webhook | a non-page scenario, or `Blocked (needs human verify)` if it cannot be driven |
| **Shared** | layout, global stylesheet, design tokens, shared component | adjacent-regression on pages that render it |

A PR may be both user-visible and shared. Backend-only with no user-affecting surface stays skipped with a reason.

## Union, then cluster

Union the surviving file lists. GitHub `get_files` paths are enough. Optional: if merge SHAs exist locally, `git show --name-only <sha>` can corroborate; do not fetch a full clone to get them.

**Cluster by user-visible surface, not by PR number.** Three PRs that all touch checkout are one `checkout` journey. Attach originating PR numbers to the cluster so the matrix can cite them.

Clustering cues, in order:

1. Same route, page, or named user job (checkout, settings, onboarding)
2. Same primary component or view directory
3. Same permission boundary (role X can now do Y)

Do not keep a cluster whose only files are tests or fixtures unless those tests describe a user-visible contract you will drive.

**Adjacent regression:** a changed layout, global stylesheet, or shared component earns **one** extra scenario on a page that renders it, even when that page was not in any PR. Cap at one adjacent scenario per shared surface — this is not whole-app visual QA.

## Personas

Ground 1–3 primary personas so Phase 4 can judge paper cuts. Check, in order:

1. `rosey/foundation/STRATEGY.md` — `## Users` (Primary + job-to-be-done)
2. `rosey/foundation/PRODUCT.md` — `## Users` / "Who it's for"
3. `VISION.md` or `PERSONAS.md` at repo root
4. `<repo-root>/personas/` if present

If none exist, infer one reasonable primary persona from the product and the clustered surfaces, and mark the source as `inferred` in the report.

## What Phase 2 receives

- **Clusters:** name, originating PR numbers, file paths, candidate routes, kind (user-visible / non-UI / adjacent)
- **Skip table:** PR number, title, reason
- **Personas:** name, job-to-be-done, source

Phase 2 maps each cluster to a flowchart. It does not re-split by PR.
