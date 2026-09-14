# Phase 1: Ground the Epic

If `INTERACTION_MODE=non-interactive`, skip the collaborative dialogue. Use the epic description and repo scan as the source material for Phase 2, and record unvalidated bets as assumptions in the affected area's document.

## 1.1 Repo Scan

Scan the repo before substantive dialogue, in two passes.

*Constraint Check* — Read project instruction files (`AGENTS.md`, and `CLAUDE.md` only if retained as compatibility context) for workflow, product, or scope constraints. Also read `STRATEGY.md` if it exists — the product's target problem, personas, and active tracks shape which areas are in scope and which are not. If these add nothing, move on.

*Topic Scan (grounding scout)* — Dispatch a sub-agent to scan the repo in its own context, so quoted material never enters this conversation.

Read `.agents/shared/references/model-tiers/model-tiers.md` before dispatching. Then, **only at this point** — the directory is created lazily, so a run that never dispatches leaves no scratch behind — create the per-run scratch directory and capture its absolute path:

```bash
ROOT="$(git rev-parse --show-toplevel)/rosey/brainstorms/scratch";
RUN_ID="$(head -c4 /dev/urandom | od -An -tx1 | tr -d ' ')";
SCRATCH_DIR="$ROOT/$RUN_ID";
mkdir -p "$SCRATCH_DIR" || exit 1;
echo "$SCRATCH_DIR";
```

Use the echoed absolute path as `<scratch-dir>`; the dossier is `<scratch-dir>/grounding.md`. Pass that **resolved absolute path** to the sub-agent — never an unresolved shell-variable string.

**Dispatch one scout for the epic, not one per candidate area.** The areas are still provisional at this point, and a per-area fan-out would scan overlapping ground several times. Ask the scout for the shape of each surface the ambition names — where the existing equivalents live, what patterns are established, what already exists that this would extend. Carry only the returned gist into the dialogue; read the dossier on demand.

When no sub-agent primitive is available, do the scan inline and still write the dossier, per the degradation rule in `.agents/shared/references/model-tiers/model-tiers.md`.

Two rules govern depth during the scan:

1. **Verify before claiming** — when the epic touches checkable infrastructure (tables, routes, config, dependencies, existing components), read the relevant source to confirm what actually exists. Any claim that something is absent must be verified first; if not verified, label it an unverified assumption.
2. **Defer implementation to planning** — schemas, endpoint shapes, file layouts, and component structure belong downstream. Establish only what changes which areas exist or where their boundaries fall.

## 1.2 Collaborative Dialogue

Ask one question at a time. Use the platform's blocking question tool when available (see Interaction Method in `SKILL.md`).

**Ask only decisions.** A question whose answer is in the repo or the grounding dossier is not put to the user — look it up. Decisions stay on the user.

**Probe per area, not per epic.** A question that resolves the whole ambition at once is usually too coarse to act on. Work area by area: for each candidate area, establish who it serves, what outcome it delivers, and where its boundary sits. An area whose answers keep pulling in another area's concerns is a merge signal — carry it to Phase 2 rather than forcing the split now.

**Ask what the user is already thinking before offering your own framing.** This surfaces hidden context and prevents fixation on agent-generated shapes.

**Bring alternatives and challenges, not just extraction.** When a proposed seam looks wrong — an area that cannot ship alone, or two areas that are really one — say so and propose the alternative.

### Cross-area integration check

**Before exiting Phase 1, run this check.** It is this skill's highest-value probe, because it catches what per-area questioning structurally cannot.

Combine what the user has said across areas and surface consequences no single area's dialogue would reach. When area A's decisions plus area B's decisions plus an agent default produce a shared surface neither area named — a type both need, a schema both write, a route both register — probe it now. That surface is usually a missing area, and finding it here is what prevents `/rosey-epic-decompose` from collapsing two tracks into one.

One probe per genuine combination effect, asked open-ended.

### Exit condition

Exit Phase 1 when each of these holds, or the user explicitly wants to proceed:

- every candidate area has an identified actor or user, or is explicitly marked unknown;
- every area's desired outcome is stated;
- every area's in-scope and out-of-scope boundaries are known;
- every area's success criteria or acceptance signals are known, or recorded as assumptions;
- the dependency relationships between areas are stated — which consume what from which;
- the cross-area integration check has run and any surface it found has been placed.

A decision the conversation already settled counts as already-probed toward every clause — never re-ask it.

In non-interactive mode, evaluate the same clauses against the supplied context and record every unmet one as an assumption or blocker rather than asking.
