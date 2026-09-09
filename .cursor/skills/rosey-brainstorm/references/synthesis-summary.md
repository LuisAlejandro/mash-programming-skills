# Scoping Synthesis

**Read `.agents/shared/references/scoping-synthesis/scoping-synthesis.md` first.** It carries the mechanism: the two-stage shape, the three-bucket internal draft, the affirmability and keep tests, the detail test, the re-cut rule, the anti-patterns, revision-vs-confirmation discipline, soft-cut behavior, self-redirect, non-interactive routing, and the artifact-shape rules. This file carries only what is specific to `rosey-brainstorm`.

**Synthesis ≠ requirements doc.** The synthesis is NOT a preview, draft, or substitute for the requirements doc — it is the scope checkpoint that doc-write consumes as input. The doc itself is written in Phase 3 from the confirmed synthesis. Both stay scope-only: implementation detail (file paths, code shapes, exact error wording) is `rosey-plan`'s job, not the requirements doc's.

---

## When it fires

Phase 2.5 — after Phase 2 (approaches chosen), before Phase 3 (write requirements doc). This is the user's last opportunity to correct the agent's interpretation before the doc lands. It serves two purposes: synthesis confirmation (the user agreed to many individual things in dialogue but never saw the whole) and a transition checkpoint ("about to write a doc").

Fires on **every interactive run**. Skip Phase 2.5 entirely on the Phase 0.1b non-software (universal-brainstorming) route.

In `mode:non-interactive`, skip the chat-time synthesis and confirmation. Compose the internal draft, route its content directly into the requirements document, and stop with a blocker if a material scope decision cannot be defaulted safely.

**Internal-draft sources for this skill:** Stated content comes from the original prompt, prior conversation, dialogue answers, and the Phase 2 approach selection.

---

## Stage 2 shape

The scoping synthesis reflects the dialogue's substance back so the user can pattern-match — long enough to serve a multi-turn conversation, short enough to stay high-impact. The reference shape is what two product collaborators would say after a real discussion: "OK, so we're doing X, with Y trade-off, deferring Z, and one thing I want to double-check is W. Sound right?"

Up to four named sections, each **render-conditional** on having something to say. Empty sections are omitted, not padded.

1. **What we're building** (always present) — 1–3 sentences. The shape that emerged from dialogue, forward-looking, plain words. Not a transcript of "you said X."
2. **Key trade-offs** (conditional) — 1–3 bullets, each with a brief why. Render only when real trade-offs were made in dialogue.
3. **What's not in scope** (conditional) — 1–3 bullets, or fold into a single sentence. Render only when deferred items would surprise a downstream reader if absent.
4. **Call outs** (conditional) — 0–3 bullets. Residual forks the dialogue didn't resolve: post-dialogue consequences, silent agent inferences, or — in pre-loaded contexts with no dialogue — scope bets the user is seeing for the first time. **Not "questions the agent could have asked during Phase 1.3 but didn't"** — if a call-out reads like a missed dialogue question, Phase 1.3's integration check failed; flag the gap rather than padding the section.

Each section answers a different question:

- **What's being built?** → shape
- **What did we trade off?** → explicit choices made in conversation
- **What did we cut?** → deferred items a reader would expect to see acknowledged
- **Where might you redirect?** → residual forks: post-dialogue consequences, silent inferences, late-cycle bets

Then the confirmation, which names **what actually happens next** so the user knows what is coming and can interrupt without ambiguity. That is always the artifact write: *"Confirm and I'll write the requirements doc next, drawing on our dialogue and this synthesis. Or tell me what to change."*

Do not hardcode any other destination. This phase writes no commit message and hands off at Phase 4, so asserting a downstream action the run will not take is overreach.

### The confirmation gate is unconditional

Every interactive run gets the full scoping synthesis and a confirmation question — there is no announce-only mode and no signal that thins the checkpoint. The confirmation is unconditional even when zero call-outs survive the keep test, and even when the opening prompt was richly pre-loaded and needed no dialogue.

*Historical note: an earlier design had an announce-only path for the smallest tier, gated on tier plus whether any blocking question had fired. It produced one-sentence checkpoints on substantive scope. The tier it depended on no longer exists and the path was removed — do not reintroduce an announce-only shortcut.*

### Keep tests per section

The shared reference carries the general keep test. These are the per-section specializations; a section is render-conditional, so an empty one is omitted rather than padded.

**Trade-offs:** would the user be surprised if I didn't surface this acknowledgment? Real trade-offs are choices the user explicitly weighed alternatives on, or structural choices the agent made that the user would expect to see named. Mechanical or inevitable choices ("uses the existing rule entity") fail and dissolve into the doc body.

**Deferred:** is a reasonable downstream reader likely to ask "why isn't X here?" Items the user explicitly deferred, or items adjacent enough that a reader will look for them. Mechanical excludes ("no rate limiting because it's not in scope") fail and stay in the internal draft.

**Call-outs:** the shared reference's keep test applies unchanged. One category is load-bearing here and easy to over-filter: **non-obvious consequences of multi-turn answers.** These are the multi-turn-dialogue reason call-outs exist at all in this skill — do not filter them as "already implied by Stated."

Also cut, specific to this skill:

- Re-statements of the Phase 2 approach the user already picked — that belongs in one sentence of "What we're building."
- Items already implied by the scoping synthesis prose.

### Total bullet budget across sections 2–4

The cap is heuristic; the real discipline is each section's keep test. Bounds count bullets across Trade-offs + Deferred + Call outs combined.

| Tier | Typical total | Hard ceiling |
|---|---|---|
| Standard | 2–4 | 5 |
| Deep — feature | 3–5 | 7 |
| Deep — product | 4–7 | 9 |

Zero call-outs is sometimes right for Standard, almost never for Deep. If a Deep scoping synthesis produces zero call-outs after rich content (whether from dialogue or pre-loaded context), double-check the agent hasn't filtered consequence-class call-outs as "already implied."

### Granularity for this skill

**Scope-only, always.** No file paths, module names, JSON keys, HTTP status codes, error wording, or SQL — implementation is `rosey-plan`'s job, and unlike plan-time synthesis there is no case where naming a path *is* the decision. This applies to every bullet in every section.

The "What we're building" prose obeys the same discipline: 1–3 sentences describing the shape, not an enumeration of requirements. If the prose lists what's in / what's out / what's how, it has become a doc preview — cut to shape only.

Bad vs. good, detail level:

| Too detailed (wrong) | Conversational (right) |
|---|---|
| Per-channel mute scoped to notification rules; mute applies to all events through that rule including @mentions, DMs forwarded as notifications, and bot messages; persists 24h with extension | Per-channel over per-user — support team isn't a single user |
| Rule-delete loss path is silent and could surprise users who configured extended mutes; consider a confirmation dialog, soft-delete with state preservation, or a 7-day undo window | Rule-delete silently loses pause state — confirm no warning needed |

---

## Template

Directional guidance — adjust phrasing to fit dialogue context. Ask open-ended, with no blocking-question menu: per Interaction Rule 5(a) in `references/interaction-rules.md`, an option menu would unintentionally influence the user's feedback toward the parts the menu lists.

**Prose discipline for "What we're building" (required):** forward-looking (what *will* be in the doc), not retrospective (what's been discussed). Lead with the actual thing being built in plain words. No qualifiers ("comprehensive," "thoughtful," "substantive"). No re-stating dialogue context the user just lived through. If the work can't be said in 1–3 sentences without filler, the synthesis isn't ready yet.

```
Based on our dialogue, here's the scope I'm proposing for the requirements doc:

**What we're building:** [1–3 sentences — the shape that emerged from dialogue, forward-looking, plain words]

**Key trade-offs:** [render only when real trade-offs exist]
- [explicit choice + brief why]
- [explicit choice + brief why]

**What's not in scope:** [render only when deferred items would surprise a reader]
- [deferred item]
- [deferred item]

**Call outs:** [render only when one or more survived the keep test]
- [scope-level fork or non-obvious consequence the user can affirm or redirect]
- [same]

Confirm and I'll write the requirements doc next, drawing on our dialogue and this synthesis. Or tell me what to change — even something I captured correctly earlier is fair game to revise (you may have changed your mind or want to correct an unstated assumption).
```

### Worked example: compression from internal draft to scoping synthesis (Standard tier)

For a notification-mute feature where the internal draft had 5 Stated items, 4 Inferred, and 3 Out-of-scope:

```
Based on our dialogue, here's the scope I'm proposing for the requirements doc:

**What we're building:** Per-channel mute on notification rules, with a 24h preset for the support team's 3 AM ping problem. Mute lives on the rule itself and survives rule edits.

**Key trade-offs:**
- Per-channel over per-user — support team isn't a single user
- Mute on the rule, not a separate entity — pause state survives edits

**What's not in scope:**
- Presence-based mute and quiet-hours schedules — deferred for later
- Cross-rule mute groups — would force a rule-grouping concept we don't have

**Call outs:**
- Rule-delete silently loses pause state — confirm no warning needed

Confirm and I'll write the requirements doc next, drawing on our dialogue and this synthesis. Or tell me what to change.
```

What got cut from the 12-item internal draft and why:

- Stated items already covered by the "What we're building" prose dissolved silently
- "Use existing rule entity" — mechanical, no real trade-off
- "Use Postgres for persistence" — implementation detail (`rosey-plan`'s job), failed granularity
- One Out-of-scope item ("no rate limiting") — mechanical exclude, no reader would ask about it
- Three Inferred items rolled into Trade-offs as the explicit choices behind them

What survived: substance proportional to the dialogue, bounded at the Standard ceiling of 5 bullets across the three conditional sections.

---

## Pre-flight re-review

Before emitting, re-read the draft as a user would. Two failure modes to catch:

- **It reads like a requirements-doc preview.** Prose enumerates what's in and out; bullets are documentary instead of conversational. The synthesis is a shape-confirmation checkpoint, not a doc preview — if it reads as preview, Phase 2.5 and Phase 3 have collapsed into one step.
- **The bullet count fits the cap but each bullet is over-detailed.** Hitting 5 bullets in Standard while each is a paragraph means the agent compressed horizontally without compressing vertically. Re-cut to sentence-level bullets.

This is one mental act — re-read as the user — not a checklist to run mechanically. Revise before emitting if either fires.

---

## Doc shape after confirmation

After confirmation (or after the soft-cut proceeds), Phase 3 writes the requirements doc. The internal draft does NOT carry in as a `## Synthesis` section. Only the "What we're building" prose embeds, as `## Summary`.

| Internal-draft element | Where it goes in the doc |
|---|---|
| "What we're building" prose | `## Summary` (1–3 lines, forward-looking, what's proposed) |
| Stated bullets | `## Requirements` (numbered R-IDs, full detail) and where relevant `## Problem Frame` for narrative context |
| Inferred bullets | `## Key Decisions` (with rationale) — bets the user accepted in dialogue become decisions in the doc |
| Out-of-scope bullets | `## Scope Boundaries` |

The chat-time Trade-offs section dissolves into `## Key Decisions`; What's-not-in-scope dissolves into `## Scope Boundaries`.

The doc's `## Summary` and `## Problem Frame` must serve distinct purposes — see `references/brainstorm-sections.md` "Discipline: Summary vs Problem Frame".
