# Scoping Synthesis

The shared mechanism behind every Mash Programming Skills scope checkpoint: the compressed, chat-time summary a skill presents to the user before it commits an artifact to disk.

This reference is IDE-agnostic and artifact-agnostic. It never names a phase number, a tier, or a document type — the calling skill supplies those. Read it alongside the skill's own `synthesis-summary.md`, which carries the parameters: when the synthesis fires, what it is about, the tier budgets, the literal templates, and where the content routes in the artifact.

**The synthesis is not the artifact.** It is the scope checkpoint the artifact write consumes as input. It never previews the document's body, and the document has no parallel `## Synthesis` section.

---

## Two-stage shape

The synthesis is composed in two stages.

**Stage 1 — internal draft.** A three-bucket draft the agent uses to think comprehensively about scope. Internal only.

**Stage 2 — the chat-time synthesis.** The compressed output the user actually sees, shaped like what two collaborators would confirm before committing to work — not a comprehensive audit, and not a one-line preview.

The user only sees stage 2. The internal draft still informs the artifact body through the skill's routing table; it just never reaches the user verbatim. This split exists because the comprehensive-audit shape produced too much detail for the user to weigh in on, even when the granularity rules were followed.

### Stage 1: the three-bucket draft

Three labeled buckets. An item may appear in two when meaningfully both — flag the inclusion-then-exclusion as Inferred so the reasoning is captured.

- **Stated** — what the user said directly: the original prompt, prior conversation, dialogue answers, or the upstream document when one exists. Items here have explicit user-language anchors.
- **Inferred** — what the agent assumed to fill gaps. Scope boundaries never explicitly named, success criteria extrapolated from intent, technical assumptions made because the interview didn't probe them. This is the most actionable bucket: items here are the agent's bets.
- **Out of scope** — deliberately excluded items. Adjacent work considered and set aside, refactors, nice-to-haves, future work. Making exclusions explicit lets the agent spot anything that should actually be included.

**Never paste the internal draft verbatim into chat.** That was the old shape, and the volume problem it produced is why stage 2 exists. Compose it as a thinking step, then derive stage 2 from it.

---

## The keep test

Before keeping any candidate item in stage 2, run the **affirmability test**: would the user need to read code to evaluate this? If yes, it is artifact-body content — cut it.

If no, one of these must hold:

- **Real fork** — another reasonable agent might choose differently on this dimension.
- **Non-obvious inclusion** — something the agent assumed is in scope that the user might want excluded.
- **Non-obvious exclusion** — something moved to deferred that the user might want back in scope.
- **Non-obvious behavioral choice** — a default the user would not see by reading the summary alone, but that materially changes what gets built.
- **Cheap-now-expensive-later correction** — a bet the user is well-placed to redirect now that would be expensive to undo after the artifact lands.
- **Non-obvious consequence of multi-turn answers** — a downstream effect of combining the user's own answers that they are unlikely to have tracked. Surface it forward-looking ("X means Y"), not retrospectively ("you said X"). Do not filter these out as "already implied by Stated."

Cut everything else, including:

- Mechanical items where no real alternative exists.
- Implementation choices that will be settled later.
- Items already implied by the summary prose.
- Re-statements of question-and-answer turns — that is transcript, not a checkpoint.

---

## The detail test

Every surviving item runs a second test: **1–2 lines maximum, conversational not documentary.** An item that runs to four or more lines of dense prose is naming an implementation consequence rather than a decision — re-cut at a higher level of abstraction.

The keep test governs *which* items survive. The detail test governs *how much* each one says. Without it the count cap is gameable: an agent can hit its budget while each item is a six-line paragraph, and the synthesis reads as an artifact preview instead of a checkpoint.

Two checks:

- **Read-aloud test** — would two collaborators *say* this, or *write* it in a spec? Say is right. Write means re-cut to a sentence, or cut entirely.
- **Single-sentence test** — can it land in one sentence? If it needs semicolons stringing clauses together, it is probably two decisions sharing a line: split it (then re-cut for count) or keep only the higher-level one.

---

## Over the ceiling: re-cut, do not raise the cap

Tier budgets are **ceilings, not targets**. Less is correct when there isn't more to say — filling the budget produces noise.

When the pass exceeds its cap, or any single item runs long, the synthesis is misshapen. Do not raise the cap and do not accept the bloat: re-cut at a higher level of abstraction. Almost always, several items are sub-decisions of one larger decision. Collapse them into a single item named at the level the user actually weighs in on. The user's job is to redirect forks, not to validate every consequence of a fork they already accepted implicitly.

A useful check: read the items aloud. If two or more sound like "and also" extensions of the same idea, they belong as one.

---

## Anti-patterns

Each of these produces an item that fails the affirmability test, or a synthesis that drifts back toward the comprehensive-audit failure mode. If a candidate matches one, it is artifact-body content — cut it, do not rephrase it.

- **Implementation detail anywhere in the synthesis** — file paths, module names, line numbers, method signatures, call graphs, JSON or response shapes, HTTP status codes, event or type names, exact error or UI wording, SQL syntax. This holds regardless of position: inside the summary, inside an item, or nested in a sub-bullet. A structurally legal placement does not legitimize the content.
- **Re-stating a question-and-answer turn verbatim** — transcript, not synthesis. Reframe it forward-looking or cut it.
- **Re-stating a choice the user already made** — it belongs in one sentence of the summary, not as its own item.
- **Padding a section to meet a count** — sections are render-conditional. Omit an empty one rather than filling it with weak items.
- **Numerical attestation** — "all nine requirements covered," "five acceptance examples addressed." These are the agent showing its work, not naming a scope decision. The scope claim already conveys it; the count adds nothing the user can affirm or redirect.
- **Pasting the internal draft verbatim into chat.**
- **Floating questions adjacent to stage 2** — if a question genuinely cannot be defaulted, pause the synthesis and resolve it first. Pick the shape that fits: a blocking multiple-choice tool when the options are bounded and meaningfully distinct, open-ended when a menu would bias the answer. Integrate the answer, then present. Never present a synthesis with unresolved questions floating beside it — that leaves the user no clear resolution path.
- **Synthesis as artifact-pitch** — extensive content placed *above* the synthesis (an approach pitch, a files-touched list, a rationale block) inverts the structure: the synthesis becomes a footnote to the proposal instead of the proposal being a budgeted summary the items depend on. The summary leads; the items follow.

### Counter-warning for rich-context invocations

When the inference source is richer than a brief interview — a prior validation agent, completed sibling work earlier in the session, an artifact already in the conversation — the temptation is to dump that material into the synthesis verbatim. **The granularity rules tighten in this case, not loosen.** The agent has more material to compress, not more material to expose. A bet already validated upstream is Stated (internal), not Inferred. A bet whose specifics belong in the artifact body is named at decision level regardless of how much detail the upstream context provided. If recent turns produced detailed code, file paths, or research artifacts, expect the internal draft to over-share and compress proactively before stage 2.

---

## A revision is not a confirmation

After any user revision — even a trivially understood swap — integrate the change, re-present the revised stage 2 with the change reflected, and wait for explicit confirmation before writing. The loop:

1. Present stage 2 → user responds
2. User confirms → write the artifact
3. User revises → integrate, re-present, return to step 1

The write fires only on explicit confirmation, or after the soft-cut's "proceed" option below. Never write immediately after a revision, even when it was small enough that the agent feels it understood. The confirmation step is what makes the synthesis **confirmed** rather than "the agent's last proposal."

---

## Soft-cut on circularity

Track which items the user touched per round. The soft-cut fires **only when the same item is revised twice** (or a third-round revision targets an item already revised in round two). Revisions to *different* items proceed without limit — revising several aspects of a wrong synthesis is exactly what the mechanism should support.

**Identity across rounds is by decision dimension, not by surface wording or section.** A revision may cause stage 2 to re-derive, so the same underlying decision can return rephrased, merged with another item, or moved to a different section. "Same item" means the same underlying decision regardless of where it now sits. When a re-cut collapses several prior items into one, the combined item inherits the touched status of any constituent — the soft-cut fires if any underlying decision was already revised once.

When it fires, use the platform's blocking question tool with two options: proceed and write, or hold off and keep discussing. Fall back to a numbered list in chat only when no blocking tool exists or a real call errors. **Never silently skip it.**

---

## Self-redirect

If the user's response signals they are in the wrong skill or want a different workflow — "this is bigger than I thought," "this is just a fix," "I need to investigate first" — stop, name the skill that appears to fit, and offer to load it in-session. Do not push back or argue: the redirect signal is a deliberate choice.

This support exists because the synthesis is an honest checkpoint. If the user discovers the skill choice was wrong by reading it, redirecting is the right move.

---

## Non-interactive mode

**Stage 2 is moot when there is no synchronous user.** Compose the internal draft as usual, then skip the chat-time compression entirely: no items to derive, no confirmation, no announcement. Route the internal draft directly into the artifact body via the skill's routing table.

The buckets route with mode-aware shape:

- **Stated** → the artifact's requirements, traced to the origin's IDs when present.
- **Out of scope** → the artifact's scope boundaries.
- **Inferred** → a dedicated `## Assumptions` section, explicitly labeled as un-validated agent bets. Do **not** route Inferred content into decisions or work units — that would make un-validated bets indistinguishable from user-confirmed ones.

The `## Assumptions` section appears in non-interactive artifacts only. Interactive runs don't need it: Inferred bets either get corrected by the user and become documented decisions, are revised away, or were judged not-fork material by the keep test and dissolved silently. Keeping them under their own label preserves audit visibility for downstream review rather than hiding them.

---

## Artifact shape after confirmation

The internal draft does **not** carry into the artifact as a `## Synthesis` section. Only the stage-2 summary embeds, as `## Summary`. Everything else dissolves into the body sections per the skill's own routing table.

Two rules hold everywhere:

- **No capture-context note.** Never annotate the artifact with where or when the synthesis happened. It leaks engineering process into a document whose readers do not need that signal.
- **Summary and Problem Frame serve distinct purposes.** Summary answers "what is this proposing?" — forward-looking, a few lines. Problem Frame answers "why does this proposal exist?" — backward-looking, paragraphs. Don't restate the proposal in Problem Frame; don't pad Summary with situational context.

---

## What never belongs in the synthesis

- Implementation code or code-shaped specifics — in chat output *or* in the internal draft.
- A re-statement of the entire upstream document. The synthesis is this skill's perspective, not a copy.
- Defensive what-ifs and hedges. If a concern is real, state it as Inferred; if it is speculation, drop it.
- Open questions floating outside the buckets. By synthesis time every scope-shaping question is Stated (asked and answered), Inferred (the agent's bet, which surfaces if it survives the keep test), or Out (deliberately excluded). There is no fourth status.
