# Phase 1: Understand the Idea

If `INTERACTION_MODE=non-interactive`, skip collaborative dialogue. Use the feature description, repo scan, and any caller-provided issue context as the source material for Phase 2. Record any unvalidated product bets under assumptions or blockers in the requirements document.

## 1.1 Existing Context Scan

Scan the repo before substantive brainstorming. Match depth to scope:

**Lightweight** — Search for the topic, check if something similar already exists, and move on.

**Standard and Deep** — Two passes:

*Constraint Check* — Check project instruction files (`AGENTS.md`, and `CLAUDE.md` only if retained as compatibility context) for workflow, product, or scope constraints that affect the brainstorm. Also read `STRATEGY.md` if it exists — the product's target problem, approach, persona, and active tracks are direct input to what this brainstorm should deliver and should shape scope, success criteria, and which approaches are aligned vs out-of-scope. If these add nothing, move on.

*Topic Scan (grounding scout)* — Dispatch a sub-agent to do the topic scan in its own context, so the quoted material never enters this conversation.

Read `references/model-tiers.md` before dispatching. Then, **only at this point** — the directory is created lazily, so a run that never dispatches a scout leaves no scratch behind — create the per-run scratch directory and capture its absolute path:

```bash
ROOT="$(git rev-parse --show-toplevel)/rosey/brainstorms/scratch";
RUN_ID="$(head -c4 /dev/urandom | od -An -tx1 | tr -d ' ')";
SCRATCH_DIR="$ROOT/$RUN_ID";
mkdir -p "$SCRATCH_DIR" || exit 1;
echo "$SCRATCH_DIR";
```

Use the echoed absolute path as `<scratch-dir>` for the rest of the run; the dossier is `<scratch-dir>/grounding.md`. Pass that **resolved absolute path** to the sub-agent — never an unresolved shell-variable string. The directory is not cleaned up: `rosey/brainstorms/` is gitignored, and the Phase 4 handoff gives the dossier path to `rosey-plan`, so deleting it would hand off a dead path.

Read `references/agents/grounding-scout.md` and seed a generic sub-agent with that prompt. Carry only the returned gist into the dialogue; read the dossier on demand when the conversation needs specifics the gist cannot answer.

**Lightweight skips the scout entirely** per the Lightweight rule in `references/phase-0.md` — search for the topic inline, check whether something similar exists, and move on. The non-software route skips it too. When no sub-agent primitive is available, do the scan inline and still write the dossier to `<scratch-dir>`, per the degradation rule in `references/model-tiers.md`.

If nothing obvious appears after a short scan, say so and continue. Two rules govern technical depth during the scan:

1. **Verify before claiming** — When the brainstorm touches checkable infrastructure (database tables, routes, config files, dependencies, model definitions), read the relevant source files to confirm what actually exists. Any claim that something is absent — a missing table, an endpoint that doesn't exist, a dependency not in the Gemfile, a config option with no current support — must be verified against the codebase first; if not verified, label it as an unverified assumption. This applies to every brainstorm regardless of topic.

2. **Defer design decisions to planning** — Implementation details like schemas, migration strategies, endpoint structure, or deployment topology belong in planning, not here — unless the brainstorm is itself about a technical or architectural decision, in which case those details are the subject of the brainstorm and should be explored.

## 1.2 Product Pressure Test

Read `references/product-pressure-test.md` for the per-tier lens catalog (Lightweight / Standard / Deep / Deep-product) and the synthesis questions the agent weighs in its own reasoning. Match depth to the Phase 0.3 scope. Phase 1.3 below owns how each found gap fires as a probe.

## 1.3 Collaborative Dialogue

Follow the Interaction Rules in `references/interaction-rules.md`. Use the platform's blocking question tool when available.

**Conflict gate — surface it when it would change a product decision.** If the user uses a term that conflicts with the project's established vocabulary, or claims how the system works in a way that conflicts with verified code, put that conflict to them before treating their wording as settled.

**Blindspot gate — check it before probing flagged territory.** If the Phase 0.3 unfamiliarity tripwire fired, fire the blindspot offer from `references/blindspot-pass.md` before the first substantive question into the flagged territory. Questions about the user's own problem, users, and evidence proceed normally — the gate is territory-scoped. The gate also arms mid-dialogue without a tripwire: when two consecutive answers show the user *cannot evaluate* the question's substance — not merely has not decided — read the reference and offer the pass then. Never silently switch into teaching; the offer is a blocking question. Skipped entirely in non-interactive mode, where flagged territory is handled as a declined offer.

**Guidelines:**

- Ask what the user is already thinking before offering your own ideas. This surfaces hidden context and prevents fixation on AI-generated framings.
- Start broad (problem, users, value) then narrow (constraints, exclusions, edge cases)
- **Rigor probes fire before Phase 2 and are open-ended, not menus.** Narrowing is legitimate, but Phase 1 cannot end with un-probed rigor gaps. Each scope-appropriate gap from Phase 1.2 fires as a **separate** direct open-ended probe — one probe satisfies one gap, not multiple. Standard brainstorms scan four gap lenses (evidence, specificity, counterfactual, attachment); Deep-product adds durability (five total), but only the gaps actually present in the opening must be probed. Surface those probes progressively across the conversation — interleaving with narrowing moves is fine, as long as every scope-appropriate gap that was found in Phase 1.2 has been probed open-ended before Phase 2. Rigor probes map to Interaction Rule 5(b): a 4-option menu signals which kinds of evidence count and lets the user pick rather than produce. Open-ended questions force them to produce real observation or surface their uncertainty. Examples (one per gap): *evidence — "What's the most concrete thing someone's already done about this — paid, built a workaround, quit a tool over it?"* / *specificity — "Can you name a team you've actually watched hit this, or are you reasoning?"* / *counterfactual — "What do teams do today when this breaks — who reconciles?"* / *attachment — "Before we move to shapes or approaches — what's the smallest version that would still prove the bet right, and what's excluded?"* — **attachment is the final rigor probe before Phase 2 when the attachment gap is present. Fire it regardless of whether a specific shape has emerged through narrowing; its job is to pressure-test the user's implicit framing of the product before Phase 2 inherits it** / *durability — "Under the most plausible near-term shifts, how does this bet hold?"* If the answer reveals genuine uncertainty, record it as an explicit assumption in the requirements document rather than skipping the probe.
- Clarify the problem frame, validate assumptions, and ask about success criteria
- Make requirements concrete enough that planning will not need to invent behavior
- Surface dependencies or prerequisites only when they materially affect scope
- Resolve product decisions here; leave technical implementation choices for planning
- Bring ideas, alternatives, and challenges instead of only interviewing

**Before exiting Phase 1.3: integration check.** Mentally combine what the user has said so far and surface any non-obvious consequences the dialogue hasn't probed. If user-stated X plus user-stated Y plus your-default-Z produces a downstream effect the user is unlikely to have tracked through one-question-at-a-time dialogue ("if mute lives on the rule AND we don't warn on delete, then rule-delete silently loses pause state"), probe it now while you're still in dialogue. One probe per genuine combination effect, asked open-ended, same discipline as rigor probes. Phase 2.5's call-outs are a safety net for residuals (silent agent inferences, pre-loaded contexts with no dialogue) — NOT a punt list for consequences you could have asked about now.

**Exit condition:** Exit Phase 1.3 when each of these holds, OR the user explicitly wants to proceed:

- the primary actor or user is identified, or explicitly marked unknown;
- the desired outcome is stated;
- the in-scope and out-of-scope boundaries that matter are known;
- success criteria or acceptance signals are known, or recorded as assumptions;
- every Phase 1.2 gap that was found has been probed, or recorded as an assumption;
- no integration-check question is pending.

A decision the conversation already settled counts as already-probed toward every clause — never re-ask it.

In non-interactive mode, evaluate the same clauses against the supplied context and record every unmet one as an assumption or blocker rather than asking.
