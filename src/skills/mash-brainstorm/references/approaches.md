# Phase 2 and 2.5: Approaches and Synthesis

## Phase 2: Explore Approaches

If multiple plausible directions remain, propose **2-3 concrete approaches** based on research and conversation. Otherwise state the recommended direction directly.

Use at least one non-obvious angle — inversion (what if we did the opposite?), constraint removal (what if X weren't a limitation?), or analogy from how another domain solves this. The first approaches that come to mind are usually variations on the same axis. Hold each approach to an anti-genericness test: if it would appear in a generic listicle for this problem category, sharpen it against what the Phase 1.1 scan actually found in this repo, or drop it.

Present approaches first, then evaluate. Let the user see all options before hearing which one is recommended — leading with a recommendation before the user has seen alternatives anchors the conversation prematurely.

When useful, include one deliberately higher-upside alternative:

- Identify what adjacent addition or reframing would most increase usefulness, compounding value, or durability without disproportionate carrying cost. Present it as a challenger option alongside the baseline, not as the default. Omit it when the work is already obviously over-scoped or the baseline request is clearly the right move.

When product shape is unresolved, alternatives differ on what is built (product shape, actor set, positioning). When product shape is already established, alternatives differ on mechanism. Implementation specifics belong in `mash-plan` either way.

For each approach, provide:

- Brief description (2-3 sentences)
- Pros and cons
- Key risks or unknowns
- When it's best suited

**Approach granularity: mechanism / product shape, not architecture.** Approach descriptions name mechanism-level distinctions ("pause as a rule property" vs "pause as an event filter" vs "pause as a separate entity") and product-relevant trade-offs (plan-tier coupling, complexity surface, migration difficulty). They do NOT name implementation specifics — column names, table names, file paths, service classes, JSON shapes, exact method names. Those are mash-plan's job. Bringing architecture forward at brainstorm time forces the user to make architectural decisions on mash-brainstorm's intentionally-shallow research, Phase 3's requirements document stays at that same granularity.

After presenting all approaches, state your recommendation and explain why. Prefer simpler solutions when added complexity creates real carrying cost, but do not reject low-cost, high-value polish just because it is not strictly necessary.

If one approach is clearly best and alternatives are not meaningful, skip the menu and state the recommendation directly.

If relevant, call out whether the choice is:

- Reuse an existing pattern
- Extend an existing capability
- Build something net new

In non-interactive mode, do not present an approach menu. Choose the approach the evidence best supports, state it in the requirements document, and record the rejected alternatives and the reason under Key Decisions.

## Phase 2.6: Claim Verification

When the requirements document will assert checkable claims about the repo — absence claims ("no retry logic exists"), references to specific files, config, or dependencies, anything planning would build on — verify them with a **fresh-context sub-agent** before Phase 3 writes.

Why a separate agent rather than self-review: the author confirming its own claims is anchored on the reasoning that produced them. The verifier never saw the dialogue, so it checks the claim rather than the story behind it. Phase 1.1's verify-before-claiming rule is the first line of defense; this is the one that catches what survived it.

Read `~/.config/mash/references/model-tiers.md` for the tier and dispatch rules. Pass the verifier: the claim list, one line each; the grounding dossier path when one exists; and this instruction:

> Verify each claim directly against the codebase — budget roughly 15 targeted reads. Return a per-claim verdict: **confirmed** (with `file:line`), **refuted** (with the contradicting evidence), or **unverifiable** (with what you looked for). Do not evaluate whether the claims are good ideas; only whether they are true.

Consume the verdicts at Phase 3: correct refuted claims before writing, and label unverifiable ones as explicit assumptions.

**Dispatch blocking**, immediately before the Phase 3 write.

Skip when the document will make no checkable claims. When no sub-agent primitive is available, verify the claims inline before the Phase 3 write with the same read budget.
