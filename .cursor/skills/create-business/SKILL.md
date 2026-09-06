---
name: create-business
description: 'Guided journey from raw idea to a validated, positioned, priced business with a chosen beachhead. Runs ten phases in sequence, each carrying its full method inline under references/ so it runs standalone, asking the user questions at every decision point and recording results in the project rosey/foundation/ folder (CUSTOMER.md, POSITIONING.md, OFFER.md, CREATE-BUSINESS-PLAN.md) so the journey resumes across sessions. Use when the user wants to start a new business, validate a startup idea, find product-market fit before building, or says ''I have an idea for a company''. Do not use once the business has paying customers: use grow-business to add revenue and customers, or improve-business to fix strategy and operations.'
---

# Create a Business

Take a raw idea to a business you can defend on every axis: who it is for, what job it does, why it is different, why it wins, what it costs, and why anyone would pay. This journey runs ten phases in sequence, looping back as evidence accumulates. It is interactive — the agent asks before every decision — and resumable: all state lives in `rosey/foundation/` so you can stop and restart across sessions. The order is the point: demand before building, strategy before scale, price before product.

## Core Principle

**Earn your evidence before you spend your runway: demand before building, strategy before scale, price before product.** You can be wrong about your product in a week, or wrong about your business in a year — pick the week. This skill sequences the phases, asks the questions at every decision point, and records what you decide in `rosey/foundation/`. The references under `references/` carry the method — read them rather than improvising their frameworks.

## Journey Map

| Phase | Skill | Question it answers | Artifact |
|---|---|---|---|
| 1 | jobs-to-be-done | What progress is the customer really hiring us for? | Creates rosey/foundation/CUSTOMER.md |
| 2 | mom-test | Is the job real, painful, and worth paying to solve? | Extends rosey/foundation/CUSTOMER.md — GATE |
| 3 | design-sprint | Does the concept survive contact with five real customers? | Creates rosey/foundation/EXPERIMENTS.md |
| 4 | lean-startup | What is the smallest MVP that tests the riskiest assumption? | Creates rosey/foundation/PRODUCT.md; extends rosey/foundation/EXPERIMENTS.md |
| 5 | good-strategy-bad-strategy | What is the one critical challenge, and how do we win? | Creates rosey/foundation/STRATEGY.md |
| 6 | blue-ocean-strategy | Where is the uncontested space we can own? | Extends rosey/foundation/STRATEGY.md |
| 7 | obviously-awesome | What are we, and why does that matter, in 30 seconds? | Creates rosey/foundation/POSITIONING.md |
| 8 | hundred-million-offers | What makes this offer impossible to refuse? | Creates rosey/foundation/OFFER.md |
| 9 | monetizing-innovation | What will people actually pay, and per what? | Extends rosey/foundation/OFFER.md |
| 10 | crossing-the-chasm | Which single segment do we dominate first? | Extends rosey/foundation/STRATEGY.md |

## Operating Rules

1. **Resume first.** Before anything else, read `rosey/foundation/CREATE-BUSINESS-PLAN.md` and every artifact in the Journey Map. If the tracker exists, summarize the journey state in 3-5 lines and ask which phase to enter. Done when the user has confirmed an entry point. A journey with a tracker is resumed, never restarted.
2. **Intake on first run only.** No tracker: run the Intake below, then create `rosey/foundation/CREATE-BUSINESS-PLAN.md` with every phase statused `pending | in-progress | awaiting-evidence | done | deferred: reason | skipped: reason`. Done when the tracker exists and the user has confirmed the phase plan.
3. **Phase entry.** Announce: what the phase does, the decision it forces, the artifact it produces, rough effort. Offer proceed / skip / defer — phases marked GATE may be deferred, never skipped. Mark the phase `in-progress` on proceed. Done when the user chose.
4. **Reference invocation and fallback.** Read the phase's reference and apply it: each phase's Invoke line names the reference path under `references/` — read that reference to run the phase. If the user declines, run the phase from its Brief — the minimum viable method. State which mode you are in.
5. **In-phase decisions.** Ask every question under "Decide with the user" — with concrete options and your recommendation. Record the choice in the tracker's Key Decisions. A decision made silently is a defect.
6. **Phase exit.** Present the draft artifact content for sign-off before writing. On approval: write or extend the rosey/foundation/ files, update the tracker (status, Key Decisions, Next Actions). Done when the files are written and the phase row shows `done`.
7. **Artifact discipline.** Read before writing; create a file only if missing, otherwise extend — add or update your sections, preserve everyone else's. Files are UPPERCASE in `rosey/foundation/`. Every recommendation lands as a checkbox or a table row with owner and priority. See [references/artifact-templates.md](references/artifact-templates.md) when creating a rosey/foundation/ file for the first time — create it from the full skeleton (all section headings), then fill the sections your phase names.
8. **The agent prepares and processes; only the human talks to customers.** Draft interview guides and score transcripts, then pause with status `awaiting-evidence` until the user returns with notes. Never simulate a customer — a role-played interview confirms whatever you hope is true.

## Intake

Ask these before creating the tracker (skip any already answered):

1. What is the raw idea, in one or two sentences? (seeds the job reconstruction in Phase 1)
2. Who do you imagine the customer is, and how do they solve this today? (feeds Competing Alternatives; a tight segment speeds Phases 7 and 10)
3. What customer access do you have — a list, a community, warm intros? (gates Phases 2-4; without access the human-only interview phases stall)
4. What evidence already exists — past interviews, a waitlist, sales, a prototype? (lets us fast-track or skip discovery already done)
5. Is this B2B or B2C — and if B2B, sales-led or self-serve? Is it a marketplace or network product? (routes optional predictable-revenue and cold-start-problem)
6. What is your runway and deadline? (sets phase depth and whether to defer strategy phases)
7. Is any product already built? (if so this may be the wrong journey — route to grow-business or improve-business)

Phase-skip heuristics: skip Phase 1 when a validated job statement with three dimensions already exists in CUSTOMER.md; skip Phase 3 when a working prototype has already been tested with 5+ target users; defer Phase 6 for a clearly-differentiated niche until the kernel is set; defer Phases 5-10 until Phase 2 returns real commitments — no strategy on unvalidated demand. Then create `rosey/foundation/CREATE-BUSINESS-PLAN.md` from the template, status every phase, and confirm the plan. Done when `rosey/foundation/CREATE-BUSINESS-PLAN.md` exists with every phase statused and the user has confirmed the plan.

## Phases

### Phase 1 — Find the real job (.agents/shared/references/jobs-to-be-done/jobs-to-be-done.md)

**Purpose:** Reframe the raw idea as the progress a customer is trying to make, so the business survives even if the first solution dies.

**Brief (fallback):** A job is progress in context, not a goal or a task — write it as `When [situation], I want to [motivation], so I can [outcome]`, solution-agnostic. Every job has functional, emotional, and social dimensions; the differentiated product usually lives in the last two. Real competition includes workarounds and non-consumption — name the hire you must beat.

**Invoke:** Read `.agents/shared/references/jobs-to-be-done/jobs-to-be-done.md` and apply its framework with the raw idea and customer guess from Intake. Ask for a When/I-want-to/so-I-can job statement, all three dimensions, and the full competing-alternatives set including non-consumption.

**Decide with the user:** Which job statement is the real one, and which competing hire you must beat first. Recommend the tightest statement that still names an emotional or social dimension.

**Artifact:** Create rosey/foundation/CUSTOMER.md with `## Job Statement`, `## Job Dimensions`, and `## Competing Alternatives`. Update the tracker.

**Done when:** CUSTOMER.md holds a solution-agnostic job statement, all three dimensions, and the competing set with the hire-to-beat named.

### Phase 2 — Validate the job with real conversations (references/mom-test/mom-test.md) — GATE

**Purpose:** Replace opinions with facts — evidence the Phase 1 job is real, painful, and worth paying to solve. Phases 5-10 stay locked until this returns a proceed verdict.

**Brief (fallback):** Three rules — talk about their life not your idea; ask about specifics in the past not hypotheticals; talk less (they speak 80%). Compliments are not data; only commitments (time, reputation, money) count. A good question could destroy the imagined business.

**Invoke:** Read `references/mom-test/mom-test.md` and apply its framework with the job statement and competing alternatives from rosey/foundation/CUSTOMER.md. Ask for (a) a 10-12 question interview guide obeying the three rules, then later (b) transcript scoring that flags leading questions and zombie leads. Hand the guide to the user and pause with status `awaiting-evidence`; record the approved guide in rosey/foundation/CUSTOMER.md under a `### Interview Guide` subsection of `## Interview Evidence` so it survives the pause.

**Decide with the user (on return):** Does the evidence confirm the job? Proceed (3+ concrete commitments), revise the job statement (loop to Phase 1), or stop (no pain found — a cheap win).

**Artifact:** Extend rosey/foundation/CUSTOMER.md: add `## Interview Evidence` (date | who | facts | commitment) and `## Validation Verdict` with the decision and reasoning. Update the tracker.

**Done when:** CUSTOMER.md holds 5+ evidence rows, the verdict is recorded, the user chose proceed / revise / stop, and — on proceed — Phases 5-10 are unlocked.

### Phase 3 — Test the riskiest assumption in five days (references/design-sprint/design-sprint.md)

**Purpose:** Before committing months, prove the riskiest part of the concept in one week with five real customer reactions.

**Brief (fallback):** Five days — Map, Sketch, Decide, Prototype, Test. Pick one target moment (the riskiest step); sketch alone (no group brainstorms); a single Decider breaks ties; build a facade, not working code; test with exactly five target customers. On Friday, shut up and let them struggle — explaining the prototype invalidates the test.

**Invoke:** Read `references/design-sprint/design-sprint.md` and apply its framework with the validated job and riskiest open question. Ask for the Monday map with sprint questions and target moment, and a Friday five-act interview script that does not explain the prototype. Hand the recruiting brief to the user and pause `awaiting-evidence` for real sessions; record the approved script and brief under the sprint card in rosey/foundation/EXPERIMENTS.md so they survive the pause.

**Decide with the user:** What single assumption to test this week and who is the Decider. On return: does the concept survive — build, fix, or walk away (a one-week win)?

**Artifact:** Create rosey/foundation/EXPERIMENTS.md with `## Experiment Cards` (EXP-001, type sprint, pre-committed metric, decision rule, result and verdict) and `## Experiment Backlog`. Update the tracker.

**Done when:** EXPERIMENTS.md holds the sprint card with a recorded verdict from five sessions, and the user chose build / fix / walk away.

### Phase 4 — Run the loop and pick the smallest MVP (references/lean-startup/lean-startup.md)

**Purpose:** Turn discovery into a repeatable engine of validated learning and ship the smallest MVP that tests the riskiest leap-of-faith assumption.

**Brief (fallback):** Plan Build-Measure-Learn backward: decide what to learn, then the metric that proves it, then the minimum build. MVP types — smoke test, concierge, Wizard of Oz — each test a different leap-of-faith assumption; test the riskiest first. Measure actionable metrics, not vanity ones. Set pivot-or-persevere criteria before running. Pick one engine of growth: sticky, viral, or paid.

**Invoke:** Read `references/lean-startup/lean-startup.md` and apply its framework with the feature wish list and surviving concept. Ask for the single riskiest leap-of-faith assumption, an MVP type with a Build-Measure-Learn experiment card, and pivot-or-persevere thresholds set in advance.

**Decide with the user:** Which MVP type, which single engine of growth to optimize first, and the pre-committed pivot/persevere thresholds. Recommend the sticky engine (retention above churn) before paid acquisition.

**Artifact:** Create rosey/foundation/PRODUCT.md with `## Vision` and `## MVP Definition`; extend rosey/foundation/EXPERIMENTS.md with a new card and its decision rule. Update the tracker.

**Done when:** rosey/foundation/PRODUCT.md defines the MVP and what it excludes, EXPERIMENTS.md holds the card with pre-committed thresholds and the chosen engine, and the user approved the MVP scope.

### Phase 5 — Turn ambition into a strategy kernel (.agents/shared/references/good-strategy-bad-strategy/good-strategy-bad-strategy.md)

**Purpose:** Replace a wish list of goals with a real strategy — a diagnosis, a guiding policy, and coherent actions.

**Brief (fallback):** A goal names ambition; a strategy explains how you win given the obstacles. The kernel: a diagnosis naming the single critical challenge; a guiding policy that is a genuine choice with losers (if a rival could paste it in, it is a platitude); coherent actions, each with an owner and date. Detect bad strategy by the four hallmarks — fluff, dodging the challenge, goals-as-strategy, dog's-dinner objective lists. Concentrate force on one pivot point.

**Invoke:** Read `.agents/shared/references/good-strategy-bad-strategy/good-strategy-bad-strategy.md` and apply its framework with the validated demand evidence and any one-page plan. Ask for a four-hallmarks audit, then a kernel — a one-paragraph diagnosis, a guiding policy that rules whole classes of action out, three coherent actions with owners — plus an explicit no-list.

**Decide with the user:** What is the single critical challenge (the diagnosis), and what does the guiding policy explicitly refuse to do? Recommend concentrating on one pivot point over spreading thin.

**Artifact:** If `rosey/foundation/STRATEGY.md` already exists (e.g. written by `improve-business` or a prior run), **extend** it — merge the captured kernel into the existing `## Diagnosis`, `## Guiding Policy`, `## Coherent Actions`, and `## No-List` sections, preserving any other sections and headings already in the file. Otherwise **create** `rosey/foundation/STRATEGY.md` with those four sections. Update the tracker.

**Done when:** rosey/foundation/STRATEGY.md names one critical challenge, a guiding policy with losers, coherent actions with owners, and an explicit no-list.

### Phase 6 — Find uncontested space (.agents/shared/references/blue-ocean-strategy/blue-ocean-strategy.md)

**Purpose:** Choose where to win by creating uncontested space instead of fighting head-on on the same factors as everyone else.

**Brief (fallback):** Value innovation pursues differentiation and low cost at once. The ERRC grid — Eliminate, Reduce, Raise, Create — lifts buyer value while cutting cost. Plot a strategy canvas: a different offering diverges from the industry curve. Blue oceans convert non-customers (soon-to-be, refusing, unexplored), not rivals' customers — find the common barrier to remove. Do not eliminate factors customers genuinely value (trust, security, accuracy).

**Invoke:** Read `.agents/shared/references/blue-ocean-strategy/blue-ocean-strategy.md` and apply its framework with the competing alternatives from CUSTOMER.md and the kernel from rosey/foundation/STRATEGY.md. Ask for a strategy canvas of current factors and an ERRC grid for a value-innovation move within resource limits.

**Decide with the user:** Which factors to eliminate / reduce / raise / create, and which tier of non-customers to convert first. Confirm no trust, security, or accuracy factor is being cut.

**Artifact:** Extend rosey/foundation/STRATEGY.md: add `## Strategy Canvas & ERRC Grid`. Update the tracker.

**Done when:** rosey/foundation/STRATEGY.md holds a filled ERRC grid and a strategy canvas showing a divergent curve, with the target non-customer tier chosen.

### Phase 7 — Position so prospects instantly get it (.agents/shared/references/obviously-awesome/obviously-awesome.md)

**Purpose:** Set the context that makes the product's strengths obvious within thirty seconds.

**Brief (fallback):** Positioning is context, not messaging — customers judge you relative to alternatives, so choose the comparison. Five steps: true competitive alternatives (often a spreadsheet or doing nothing); unique attributes (pass the "only we" test); value via the "so what?" test; best-fit customers (tight, by title and firm traits, never everyone); market category (existing / subcategory / new — a new one pays an education tax).

**Invoke:** Read `.agents/shared/references/obviously-awesome/obviously-awesome.md` and apply its framework with unique attributes from rosey/foundation/STRATEGY.md and CUSTOMER.md. Ask for the full five-step exercise and an internal positioning statement: "For [best-fit customer], we are the [category] that [key value]."

**Decide with the user:** Which market category to compete in (existing / subcategory / new) and who the best-fit customer is. Recommend existing or subcategory unless there is traction to spare for a new category.

**Artifact:** Create rosey/foundation/POSITIONING.md with `## Competitive Alternatives`, `## Unique Attributes → Value Themes`, `## Best-Fit Customer`, `## Market Category`, and `## One-Liner`. Update the tracker.

**Done when:** POSITIONING.md holds the five-step canvas and a one-liner an outsider grasps in 30 seconds.

### Phase 8 — Build an offer people feel stupid refusing (.agents/shared/references/hundred-million-offers/hundred-million-offers.md)

**Purpose:** Turn understanding into buying with a Grand Slam Offer that makes price comparison impossible.

**Brief (fallback):** The offer is the number one lever. Value = (dream outcome × perceived likelihood) / (time delay × effort) — maximize the top, minimize the bottom. Assemble a Grand Slam Offer: core offer, named bonuses (each kills an objection, each with a defensible value), a risk-reversing guarantee, ethical scarcity. Name it with MAGIC. Keep every value honest and every guarantee honorable.

**Invoke:** Read `.agents/shared/references/hundred-million-offers/hundred-million-offers.md` and apply its framework with the positioning and best-fit customer from POSITIONING.md. Ask for a Grand Slam Offer built on the Value Equation, three named bonuses each killing an objection, a guarantee, ethical scarcity, and a MAGIC name.

**Decide with the user:** Which dream outcome to anchor on and which objections the bonuses must kill. Confirm every dollar value and every scarcity claim is genuinely true — replace any tactic that would need invented evidence.

**Artifact:** Create rosey/foundation/OFFER.md with `## Offer Stack` (core · bonuses · guarantee · scarcity · name). Update the tracker.

**Done when:** OFFER.md holds a complete offer stack with honest values, a real guarantee, and a name — no invented evidence.

### Phase 9 — Price against validated willingness to pay (.agents/shared/references/monetizing-innovation/monetizing-innovation.md)

**Purpose:** Design the product around the price by testing willingness to pay while it is still a concept.

**Brief (fallback):** Customers reveal a range: ask what feels acceptable, expensive, prohibitive; trust only the top-box purchase probability. Avoid the four failures — feature shock, minivation (near-100% win rate with no pushback), hidden gem, undead. Segment by value and willingness to pay, never demographics. Package leader / filler / killer; design the middle tier first; pull killer features into add-ons. Choose the price metric before the price level.

**Invoke:** Read `.agents/shared/references/monetizing-innovation/monetizing-innovation.md` and apply its framework with the offer from OFFER.md and segments from CUSTOMER.md. Ask for a willingness-to-pay interview script (acceptable / expensive / prohibitive), a leader/filler/killer classification, good-better-best tiers, and a price metric. Hand the WTP script to the user and pause `awaiting-evidence` for real calls; record the approved script in rosey/foundation/OFFER.md under a `### WTP Interview Script` subsection of `## Willingness-to-Pay Evidence` so it survives the pause.

**Decide with the user:** Which price metric to charge on (per seat / per unit of value) and the good-better-best tier boundaries. Recommend a metric that tracks delivered value so revenue compounds.

**Artifact:** Extend rosey/foundation/OFFER.md: add `## Willingness-to-Pay Evidence`, `## Leader / Filler / Killer Features`, `## Tiers (Good / Better / Best)`, and `## Price Metric`. Update the tracker.

**Done when:** OFFER.md holds WTP evidence, feature classes, tiers with the middle designed first, and a price metric chosen before the level.

### Phase 10 — Pick the beachhead you will dominate first (.agents/shared/references/crossing-the-chasm/crossing-the-chasm.md)

**Purpose:** Choose one narrow segment to dominate and assemble the whole product it needs to cross from visionaries to pragmatists.

**Brief (fallback):** The chasm sits between visionary early adopters and pragmatist early majority — what wins one repels the other. Do not be everything to everyone: pick one narrow beachhead with urgent, expensive pain, reachable channels, customers who talk to each other, small enough to own yet big enough to matter. Assemble the whole product (integrations, onboarding, support, partners). References are the currency; shift positioning from "revolutionary" to "proven."

**Invoke:** Read `.agents/shared/references/crossing-the-chasm/crossing-the-chasm.md` and apply its framework with POSITIONING.md and rosey/foundation/STRATEGY.md. Ask to score candidate niches on pain, reachability, word-of-mouth, and dominability, then map the whole-product requirements a pragmatist needs before buying.

**Decide with the user:** Which single beachhead segment to own first. Recommend the highest-scoring niche small enough to dominate; resist chasing several at once.

**Artifact:** Extend rosey/foundation/STRATEGY.md: add `## Beachhead` (target segment, scoring rationale) and `## Whole-Product Checklist` (each gap with owner and priority). Update the tracker.

**Done when:** rosey/foundation/STRATEGY.md names one beachhead with scoring, and the whole-product checklist lists each gap with owner and priority.

## Optional Phases

| Skill | Add when | Artifact |
|---|---|---|
| `references/storybrand-messaging/storybrand-messaging.md` | a website or pitch needs customer-as-hero copy before launch | Extends rosey/foundation/POSITIONING.md |
| `.agents/shared/references/one-page-marketing/one-page-marketing.md` | go-to-market planning starts before the beachhead phase closes | Creates rosey/foundation/MARKETING.md |
| `.agents/shared/references/lean-analytics/lean-analytics.md` | the MVP is live and needs a first metrics baseline | Creates rosey/foundation/METRICS.md |
| `.agents/shared/references/cold-start-problem/cold-start-problem.md` | the product is a marketplace or network product | Extends rosey/foundation/STRATEGY.md |
| `.agents/shared/references/predictable-revenue/predictable-revenue.md` | B2B with a sales-led motion | Extends rosey/foundation/MARKETING.md |
| `references/continuous-discovery/continuous-discovery.md` | post-launch, to make discovery a weekly habit | Extends rosey/foundation/CUSTOMER.md |

Optional phases follow the same operating rules — read each listed reference and apply its framework exactly as a core phase would; insert where the Add-when condition first becomes true.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Building before validating | Buy evidence with the smallest MVP — smoke test or concierge — before writing real code; run Phases 1-4 first (references/lean-startup/lean-startup.md). |
| Pitching during discovery | Keep interviews about their life and past behavior; save the idea for the very end, if at all (references/mom-test/mom-test.md). |
| Mistaking compliments and signups for validation | Chase commitments — a deposit, pre-order, scheduled pilot — and record them in CUSTOMER.md Interview Evidence. |
| Confusing goals for strategy | Write the diagnosis of the one critical challenge first; audit against the four hallmarks (.agents/shared/references/good-strategy-bad-strategy/good-strategy-bad-strategy.md). |
| Positioning for everyone | Tighten the best-fit definition until it is uncomfortably narrow, then go narrower (.agents/shared/references/obviously-awesome/obviously-awesome.md). |
| Pricing on cost or competitors | Price from validated willingness-to-pay ranges and choose the price metric before the level (.agents/shared/references/monetizing-innovation/monetizing-innovation.md). |

## Completing the Journey

Exit checklist — every box tied to an artifact that must exist:

- [ ] CUSTOMER.md holds a validated job statement and 5+ evidence rows with real commitments
- [ ] EXPERIMENTS.md shows the riskiest assumption tested with a recorded verdict
- [ ] rosey/foundation/STRATEGY.md has a kernel (diagnosis, guiding policy, coherent actions), a no-list, an ERRC grid, and a chosen beachhead with its whole-product checklist
- [ ] POSITIONING.md one-liner passes the 30-second outsider test
- [ ] OFFER.md holds a priced Grand Slam offer backed by willingness-to-pay evidence and a price metric

Close the tracker: every phase `done` or `skipped: reason`, and any open Next Actions carried into the relevant artifacts. Forward routing: when the beachhead is chosen and first customers are paying, continue with the `grow-business` skill to add revenue and customers.
