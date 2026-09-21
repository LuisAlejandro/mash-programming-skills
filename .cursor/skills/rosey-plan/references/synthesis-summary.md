# Scoping Synthesis

**Read `~/.config/rosey/references/scoping-synthesis.md` first.** It carries the mechanism: the two-stage shape, the three-bucket internal draft, the affirmability and keep tests, the detail test, the re-cut rule, the anti-patterns, revision-vs-confirmation discipline, soft-cut behavior, self-redirect, non-interactive routing, and the artifact-shape rules. This file carries only what is specific to `rosey-plan`.

**Scoping synthesis ≠ plan doc.** The synthesis is the scope/decisions checkpoint that plan-write (Phase 5.2) consumes as input. It surfaces decisions the agent CAN make at synthesis time: scope-level (does this plan cover the full brainstorm or narrow to a subset?), posture (extend existing pattern vs. introduce new abstraction), test approach. It does NOT surface decisions plan-write produces: PR count, commit/branch sequencing, effort or time estimates, Implementation Unit lists, exact file paths, test command recipes. If the synthesis claims any of those, it has leaked plan-write thinking and must be re-cut to scope-decisions only. Even when the agent has formed plan-write opinions earlier in the session, the synthesis stays at scope altitude — the user is being asked to affirm scope, not to rubber-stamp implementation.

---

## When it fires

Phase 5.1.5 — after Phase 1 research, before Phase 5.2 plan-write. Fires on every run except the Phase 0.1 fast paths (resume normal, deepen-intent). Resume and deepen fast paths do not re-run the scoping synthesis.

Every plan is brainstorm-sourced: the missing-origin stop at Phase 0.3b guarantees an origin document, so the synthesis always has a validated WHAT behind it.

**Content focus: plan-time decisions only.** The brainstorm already validated what to build; the internal draft and stage 2 surface *how* the plan will execute that work — decisions the brainstorm did not make. Items to consider in the internal draft:

- **Files/modules to touch (and not touch)** — what the implementation reaches into
- **Patterns extended vs. introduced new** — architectural decisions made within confirmed scope
- **Test scope** — which existing-but-untested code is in or out of scope for this work
- **Refactor scope** — adjacent cleanup, if any, going to deferred items vs. the active diff
- **Cross-cutting impact** — auth, migrations, shared types when they're touched

Most will not survive the keep test as separate call-outs. Surface only the forks where another reasonable agent might choose differently and the user can correct cheaply now.

**Reads from the doc body, not a synthesis section.** Brainstorm docs have no `## Synthesis` section — the synthesis is a chat-time artifact in `rosey-brainstorm`, and only its prose summary embeds, as `## Summary`. Derive plan-time decisions from the origin's body sections (Summary, Problem Frame, Requirements, Key Decisions, Scope Boundaries) plus Phase 1 research. Older brainstorms carrying a legacy `## Synthesis` section work fine; treat that content as supplementary, not authoritative.

**Why pre-write, not pre-research:** the brainstorm doc already validated WHAT, so research is well-targeted. Plan-time decisions emerge during research and structuring (Phases 1–4), so pre-write catches them at the latest cheap moment — before Phase 5.2 commits the plan to disk.

---

## Stage 2 shape

Two content sections plus call-outs.

1. **Brainstorm-scope restatement** (1–2 sentences, prose). Restates the brainstorm's scope as orientation. The user wrote this content, but the synthesis may be read days later or alongside other plans — the restatement is the topic anchor that says "this is the artifact we're planning against." Stay in the brainstorm's own vocabulary. Do NOT enumerate Implementation Units, restate constraints back at the user, or list acceptance examples.

2. **Plan-specific scoping decisions** (prose, or bullets when multi-faceted). Scope-level commitments the agent made that the brainstorm did not: full brainstorm coverage vs. narrowed subset; adjacent refactors pulled in or held out; test scope at scenario level. Each must pass the affirmability test. This is scope claims at affirm-or-redirect level — NOT a description of where the implementation reaches, NOT PR count or sequencing, NOT Implementation Unit lists, NOT file paths or test commands. If the plan covers the full brainstorm scope with no narrowing or adjacent work, this section stays short.

3. **Call outs** (zero or more, capped below). Each a real fork where the user's input materially changes the plan. Omit the `Call outs:` header entirely when zero survive the keep test.

### Budgets

Ceilings, not targets.

| Plan depth | Restatement | Plan-specific scoping | Call-outs (typical / cap) |
|---|---|---|---|
| Lightweight | 1 sentence | 1-3 lines prose | 0-2 / 3 |
| Standard | 1-2 sentences | up to 3-5 lines or 2-4 bullets | 1-3 / 4 |
| Deep | 1-2 sentences | up to 4-6 lines or 3-6 bullets | 2-5 / 6 |

Form within each section (prose, bullets, mix) follows whatever communicates best.

### Plan-specific rules

- **No "Stated" bucket in chat** — the restatement covers it.
- **No "Out of scope" bucket as a separate list** — fold a non-obvious exclusion into a call-out when it survives the keep test, otherwise drop it.
- **Source-document vocabulary.** Use the brainstorm's terms. Don't invent agent-coded shorthand ("skill-instruction shape", "hooks engine selection at Step 2a entry"). Name acceptance examples, requirements, and flows in plain terms ("the install-prompt acceptance case") — never bare IDs.
- **Pre-emit mechanical scans.** Before emitting, scan the output:
  - **Bare ID references** (`AE\d+`, `R\d+`, `F\d+`, `A\d+`, `U\d+`) → replace with plain names. Mixed forms (case named AND ID cited) still violate the rule — the ID adds noise without information.
  - **File paths** (`path/like.md`, `internal/cli/...`) → cut unless the path IS the topic of an explicit fork. Allowed: "cleanup hook in the existing archive step vs. a new dedicated phase" (path implicit in the decision). Forbidden: paths listed to demonstrate completeness or preview Implementation Units.

---

## Granularity: name the decision; don't expand it

Each call-out must be affirmable or rejectable **without reading code**. Name the decision at the granularity that lets the user say "yes" or "I want X instead." Anything more specific is plan-body content.

**Allowed** (when these ARE the decisions being made):
- File / module names — "skip filter in the matcher" when *where to put it* is the choice
- Pattern names — "extends the existing event-skip pattern" when *extend vs. introduce* is the choice
- Column / table names — "user-TZ" or "destination-calendar TZ" when *which source* is the choice
- Approach posture — "DB-side query with Google-side fallback" when *which strategy* is the choice

**Not allowed** — line numbers, exact method signatures, implementation flow, JSON shapes, HTTP status codes, exact event or type names, error or UI wording, SQL syntax. These are plan-body content in every case.

### Bad-vs-good

| Plan-body in call-out (wrong) | Decision-level (right) |
|---|---|
| Timezone source: `users.timezone` (IANA), fallback to destination calendar TZ if null. Research found `useTimezoneSync` and `ProtectionStatsCalculator` establish the pattern. | Timezone source: user-TZ (reverses brainstorm's tentative lean — research found established infra and pattern precedent) |
| Skip filter goes in `RuleMatcher.eventMatchesRule` at the top, before include/exclude evaluation, using the existing `filteredReason` mechanism. | Skip filter extends the existing event-skip pattern in the matcher (vs. introducing a new mechanism) |
| Reactivation guard: explicit safety in `[ruleId]/route.ts` PATCH — when `isActive: false → true`, the existing handler clears `status/pausedAt/pausedReason`. | Reactivation guard: pause window state preserved through the isActive toggle's existing system-pause-clearing path |
| Partial cleanup failure response: `{pause, cleanup: {eventsDeleted, eventsFailed, errors}}`; pause window persists regardless of cleanup outcome. | Partial cleanup failure: pause window persists; partial-failure response mirrors the existing rule-edit precedent |

The test: a reader should affirm or reject a call-out without needing to read code. If they would have to look up a column name, method name, or call graph, the granularity is wrong.

---

## When to skip the blocking confirmation

The auto-proceed path fires **only when plan depth is Lightweight AND zero call-outs survive the keep test.** For Standard or Deep, always fire the confirmation gate even with zero call-outs — substance earns the checkpoint, not interaction history. A Deep plan with rich silent decisions and a short summary is exactly where rubber-stamping is most likely.

The announcement is mandatory when skipping. Silent proceeding is not allowed: the "why" (no forks worth flagging) must be visible.

For Standard/Deep with zero call-outs, the confirmation template still fires and the `Call outs:` header is simply omitted.

---

## Templates

**Summary discipline (required):** describe **how the implementation approaches the work** at a high level — files/modules touched, patterns extended vs. introduced, scope boundaries the plan honors. Forward-looking, not retrospective. Brainstorm-validated WHAT is assumed; the summary covers HOW. Lead with the actual implementation shape in plain words. No qualifiers ("comprehensive," "thoughtful," "substantive"). If the summary just restates the brainstorm's Problem Frame, rewrite it to focus on plan-time decisions.

**Confirmation template (fires for Standard/Deep regardless of call-out count, or for any tier with one or more call-outs surviving):**

```
The brainstorm scopes [1-2 sentence restatement of the brainstorm's scope as orientation; in the brainstorm's own vocabulary; NOT an enumeration of Implementation Units, constraints, or acceptance examples].

This plan [plan-specific scoping: what's covered vs. deferred vs. expanded relative to the brainstorm; test scope; any adjacent refactors pulled in or held out. Prose or bullets per substance].

**Call outs:** (omit this header when zero forks survived the keep test)
- [plan-time fork in 1-2 lines: name the choice and optional one-clause trade-off in parens. NO multi-sentence rationale, NO "my default is X" pitch — those belong in Key Technical Decisions in the plan body, not the synthesis]

Confirm and I'll write the plan next, drawing on the brainstorm, research, and this synthesis.
```

Wait for user confirmation before continuing to Phase 5.2.

**Auto-proceed template (fires only for Lightweight with zero call-outs):**

```
Planning [brief brainstorm-scope restatement] — [plan-specific shape in one clause].

No open decisions to weigh in on — proceeding to plan-write. Interrupt if I have the scope wrong.
```

Then continue to Phase 5.2 without waiting. Use prose for any user response that does arrive — the announcement is not a question.

---

## Worked example: compression from internal draft to call-outs

For a PII redaction gate proposal where the internal draft had 4 Stated items, 7 Inferred, and 3 Out-of-scope, the compressed stage 2 looks like:

```
Planning a mechanical PII redaction gate before promote (the unguarded leak path from the amazon-orders retro) and alongside the existing vendor-prefix scanner at publish. Phase-1 detectors are shape-only — card last-4, postal address, JSON person names. Default halts; per-finding ack via flag.

**Call outs:**
- Person-name filter works by JSON key (allowlist of attribution keys: `printer`, `printer_name`, `owner_name`, `author`), not by name value.
- Promote scans the working-dir snapshot before the copy step, not the staged copy.
- Publish combines PII + vendor-prefix findings into one report, not fail-fast on first.

Confirm and I'll write the plan next, drawing on the brainstorm, research, and this synthesis.
```

What got cut and why:

- "Module name: `internal/artifacts/pii.go`" — plan-body content (file path), fails affirmability
- "Flag name: `--accept-redaction-list=<finding-id,...>`" — plan-body content (exact flag string)
- "No new dependencies — stdlib regexp + filepath.WalkDir only" — mechanical, no real alternative
- "Detector regex precision tuned during implementation" — deferred-impl, not a plan-time fork
- All three Out-of-scope items — either restated in prose or implicitly excluded by scope

What survived: three real forks where another reasonable agent might choose differently and the user can correct cheaply now. Each is affirmable in one sentence without reading code.

---

## Plan-body routing

After confirmation (or after the soft-cut proceeds), Phase 5.2 writes the plan. The internal draft does NOT carry in as a `## Synthesis` section. Only the stage-2 summary embeds, in the `## Summary` slot.

| Internal-draft element | Where it goes in the plan |
|---|---|
| Summary (stage 2) | `## Summary` (1-3 lines prose, forward-looking) — rewrite to plan convention if the chat-time summary used bullets |
| Stated bullets | `## Requirements` (R-IDs) and where relevant `## Problem Frame` for narrative context |
| Inferred bullets | `## Key Technical Decisions` (with rationale) and Implementation Units when the bet drives a structural choice. In non-interactive mode, route to `## Assumptions` instead |
| Out-of-scope bullets | `## Scope Boundaries` — including the `### Deferred to Follow-Up Work` subsection when relevant |

**Non-interactive mode:** compose the internal draft, skip stage 2, proceed to Phase 5.2. Inferred content routes to `## Assumptions`. See the shared reference for the full routing rationale.
