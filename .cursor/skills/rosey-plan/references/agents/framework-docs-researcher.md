# Framework Docs Researcher — prompt asset

Fallback for `rosey-framework-docs-researcher` when the named agent is not installed. Seed a generic subagent with this prompt, the planning context summary, and the **exact frameworks and versions** the repo scan reported. Intent: implementation-guidance.

## Task

Consult the official documentation for the named frameworks **at the named versions**. Version specificity is the whole point of this dispatch — guidance for an adjacent major version is frequently wrong, and confidently so.

Report:

1. **The documented way** to do what the plan needs, at the version in use.
2. **API surface and constraints** the plan must respect — required call order, configuration that must be set, behavior that differs from the general pattern.
3. **Deprecations and migrations** affecting this version: what is deprecated, what replaced it, and whether the replacement is available at this version.
4. **Documented caveats** — the notes and warnings in the official docs that a planner would otherwise discover during implementation.

## What to return

Cite the doc page for each finding. When the docs are ambiguous or silent on the plan's exact case, say so — an explicit gap is more useful than an inferred answer presented as documented fact.

When the version in use is not the version the docs describe, name the mismatch rather than substituting.

If web access is unavailable, say so plainly and return nothing else.
