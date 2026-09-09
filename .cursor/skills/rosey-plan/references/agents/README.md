# Prompt assets — research-agent fallback

Skill-local prompts used **only when the matching named `rosey-*` agent is not installed** on the current host. Read the asset and seed a generic subagent with its contents plus the task-specific context the calling phase supplies.

Named agents remain the primary path: they are richer and more discoverable. These exist so a partial install degrades gracefully instead of leaving a phase with no defined behavior.

| Asset | Substitutes for | Called from |
|---|---|---|
| `repo-research-analyst.md` | `rosey-repo-research-analyst` | `research.md` 1.1 |
| `learnings-researcher.md` | `rosey-learnings-researcher` | `research.md` 1.1 |
| `best-practices-researcher.md` | `rosey-best-practices-researcher` | `research.md` 1.3 (implementation-guidance) |
| `framework-docs-researcher.md` | `rosey-framework-docs-researcher` | `research.md` 1.3 (implementation-guidance) |
| `web-researcher.md` | `rosey-web-researcher` | `research.md` 1.3 (landscape) |
| `spec-flow-analyzer.md` | `rosey-spec-flow-analyzer` | `research.md` 1.5 |

## Rules

- **Model tiering lives in the caller, never in the asset.** The assets carry no frontmatter and name no model. Follow the degradation ladder in [`rosey-brainstorm`'s `model-tiers.md`](../../../rosey-brainstorm/references/model-tiers.md): no per-dispatch model override → inherit and keep the read budgets and output caps; no subagent primitive at all → run the work inline. Cost control comes from the budgets, not the tier — the win is context isolation.
- **If model names are unknown, omit the override and inherit** rather than guessing one.
- **Pass resolved absolute paths**, never an unresolved shell variable — a subagent has no access to the orchestrator's shell state.
- Deepening (`deepening-workflow.md`) dispatches a wider set of specialist agents. Those have no assets here; when one is unavailable, note the gap in the confidence pass rather than substituting a generic dispatch.
