# Planning Research

Phase 1 of `mash-plan`. Read this before gathering context or dispatching any research agent.

### Phase 1: Gather Context

#### 1.1 Local Research

Dispatch the research agents below when the origin and the files it names do not already show where the code changes and which patterns to follow. When they do, read those files and their tests inline, plus any `.mash/solutions/` entry whose title matches the topic, and skip the dispatch.

The skip is about **dispatch, not reading**. A grounding dossier handed off at Phase 0.2 is still read — it costs one file read and is the cheapest grounding available.

When dispatching, prepare a concise planning context summary (a paragraph or two) to pass as input to the research agents:
- Summarize the problem frame, requirements, and key decisions from the origin document
- If `STRATEGY.md` exists, read it and include the relevant pieces (target problem, approach, active tracks) in the summary so downstream research and planning decisions are anchored to product strategy
- If `CONCEPTS.md` exists at the repo root, read it — its definitions are the canonical names for domain entities, named processes, and status concepts. Plan in those terms rather than synonyms.

If the Phase 0 gate already ran, fold that recall into planning context; do not recall again. If Hindsight was unavailable at Phase 0, record it and do not retry because research begins. Treat useful recall output as additional planning context, alongside but separate from `.mash/solutions/` institutional learnings. If Hindsight is unavailable or not configured, continue Phase 1 and note memory unavailability only when it materially affects the plan context.

When the inline read was not enough, run these agents in parallel:

- Task mash-repo-research-analyst(Scope: technology, architecture, patterns. {planning context summary})
- Task mash-learnings-researcher(planning context summary). Skip when both `.mash/solutions/` and `.mash/insights/` are missing or contain no markdown files.

Dispatch tiering and the degradation ladder (no model override → inherit and keep the read budgets; no subagent primitive → run the work inline) follow `~/.config/mash/references/model-tiers.md`; the win is context isolation, not cost, so the budgets matter more than the tier.

Collect:
- Technology stack and versions (used in section 1.2 to make sharper external research decisions)
- Architectural patterns and conventions to follow
- Implementation patterns, relevant files, modules, and tests
- AGENTS.md guidance that materially affects the plan, with CLAUDE.md used only as compatibility fallback when present
- Institutional learnings from `.mash/solutions/`
- Product strategy context when `STRATEGY.md` is present — flag any plan decisions that pull away from the active tracks or the stated approach

#### 1.1b Detect Execution Posture Signals

Decide whether the plan should carry a lightweight execution posture signal.

Look for signals such as:
- The user explicitly asks for TDD, test-first, or characterization-first work
- The origin document calls for test-first implementation or exploratory hardening of legacy code
- Local research shows the target area is legacy, weakly tested, or historically fragile, suggesting characterization coverage before changing behavior
- The work is mostly configuration, packaging, UI styling, or environment setup, where the right first proof is a smoke or runtime check rather than unit coverage

When the signal is clear, carry it forward silently in the relevant implementation units.

Ask the user only if the posture would materially change sequencing or risk and cannot be responsibly inferred.

#### 1.2 Decide on External Research

Based on the origin document, user signals, and local findings, decide **whether** external research adds value and, if so, **what kind**. Resolve this in three stages: explicit-request priority, intent classification, then the implicit signals below.

**Stage 1 — An explicit request takes precedence.** If the user prompt **or** the origin requirements document explicitly asks for external input — a signal that the answer lives outside the repo, such as competitor/prior-art comparison, "what should we borrow", "from the web", "best practices", "official docs", "alternatives to", a market scan, or naming a specific external technology to consult — external research is **required**, regardless of how strong local patterns look. The list is illustrative; key on the signal, not the exact phrase — any wording that clearly points outside the repo qualifies. The skip conditions below do **not** apply to an explicit request. The only thing that overrides it is an explicit opt-out ("no web research", "skip external research"): honor that, skip, and note it. Improvement or quality verbs ("improve", "make better") carry no external signal on their own and never trigger research by themselves.

**Stage 2 — Classify the research intent** (whenever external research will run, from Stage 1 or the implicit signals below) so Phase 1.3 routes correctly. Use this mechanical test, not a fixed phrase list:
- **Implementation-guidance** — the approach or technology is already settled; the question is *how to build it well* (best practices, version-specific docs, API constraints, known pitfalls, deprecations).
- **Landscape / option-discovery** — the question is *what options or prior art exist* (competitor scans, build-vs-buy, library/provider selection, prior art, market signals, cross-domain analogies).
- **Mixed** — both: discover an unsettled external option set first, then research the shortlisted choice for implementation guidance.

**Stage 3 — Implicit signals** decide the call when no explicit request fired.

**Read between the lines.** Pay attention to signals from the conversation so far:
- **User familiarity** — Are they pointing to specific files or patterns? They likely know the codebase well.
- **User intent** — Do they want speed or thoroughness? Exploration or execution?
- **Topic risk** — Security, payments, external APIs warrant more caution regardless of user signals.
- **Uncertainty level** — Is the approach clear or still open-ended?

**Leverage mash-repo-research-analyst's technology context:**

The mash-repo-research-analyst output includes a structured Technology & Infrastructure summary. Use it to make sharper external research decisions:

- If specific frameworks and versions were detected (e.g., Rails 7.2, Next.js 14, Go 1.22), pass those exact identifiers to mash-framework-docs-researcher so it fetches version-specific documentation
- If the feature touches a technology layer the scan found well-established in the repo (e.g., existing Sidekiq jobs when planning a new background job), lean toward skipping external research -- local patterns are likely sufficient
- If the feature touches a technology layer the scan found absent or thin (e.g., no existing proto files when planning a new gRPC service), lean toward external research -- there are no local patterns to follow
- If the scan detected deployment infrastructure (Docker, K8s, serverless), note it in the planning context passed to downstream agents so they can account for deployment constraints
- If the scan detected a monorepo and scoped to a specific service, pass that service's tech context to downstream research agents -- not the aggregate of all services. If the scan surfaced the workspace map without scoping, use the feature description to identify the relevant service before proceeding with research

**Always lean toward external research when:**
- The topic is high-risk: security, payments, privacy, external APIs, migrations, compliance
- The codebase lacks relevant local patterns -- fewer than 3 direct examples of the pattern this plan needs
- Local patterns exist for an adjacent domain but not the exact one -- e.g., the codebase has HTTP clients but not webhook receivers, or has background jobs but not event-driven pub/sub. Adjacent patterns suggest the team is comfortable with the technology layer but may not know domain-specific pitfalls. When this signal is present, frame the external research query around the domain gap specifically, not the general technology
- The user is exploring unfamiliar territory
- The technology scan found the relevant layer absent or thin in the codebase
- The plan's recommendations depend on a genuinely external, **unsettled** option set — which library, provider, or approach to adopt, or what competitors and prior art do — **even when local implementation patterns are strong** (intent: landscape). Bound this implicit landscape trigger by three gates: (a) the option set genuinely lives outside the repo, (b) the decision materially shapes the plan (a KTD, dependency, or architecture choice — not an incidental detail), and (c) no settled local or team choice already exists. Improvement verbs alone never satisfy this.

**Skip external research when** (only when Stage 1 found no explicit request — an explicit request is never skipped):
- The codebase already shows a strong local pattern -- multiple direct examples (not adjacent-domain), recently touched, following current conventions
- The user already knows the intended shape
- Additional external context would add little practical value
- The technology scan found the relevant layer well-established with existing examples to follow

When an explicit request *did* fire but a settled local or team choice already exists, **narrow the research rather than skipping it** — research the current pitfalls, docs, and practices for the chosen library/pattern instead of re-surveying the whole option set.

Announce the decision and the intent briefly before continuing. Examples:
- "Your codebase has solid patterns for this. Proceeding without external research."
- "This involves payment processing, so I'll research current best practices first (implementation-guidance)."
- "You asked what to borrow from competitors, so I'll run a landscape scan first (landscape/option-discovery)."

#### 1.3 External Research (Conditional)

If Step 1.2 indicates external research is useful, dispatch by the **intent** classified in Stage 2, using the platform's subagent primitive (`subagent` in Pi, `default.task` in OpenCode, the Task-equivalent in Cursor — match by capability, not by another harness's tool name). For `mash-web-researcher`, pass a focus hint plus the planning context summary and do **not** pass codebase content — it operates externally.

- **Implementation-guidance** — run in parallel:
  - Task mash-best-practices-researcher(planning context summary)
  - Task mash-framework-docs-researcher(planning context summary, with exact frameworks/versions from Phase 1.1 where available)
- **Landscape / option-discovery** — Task mash-web-researcher(focus hint, planning context summary). When the request targets projects on a code host (e.g., "competitors on GitHub"), name the discovery dimensions in the focus hint: project names and URLs, release recency and activity, CLI/UX shape, install path, docs and examples, plugin/extension surfaces, recurring issue themes, and license — treating star counts as a weak signal only.
- **Mixed** — **sequential, not parallel**: run `mash-web-researcher` first to map the landscape and produce a shortlist; then run `mash-framework-docs-researcher` and/or `mash-best-practices-researcher` against the shortlisted technologies only when their details materially shape the plan.

**Tool-unavailable handling.** `mash-web-researcher` self-checks for web tools and stops if they are missing. Never block on this: if it reports research unavailable, or any researcher fails, warn and proceed, and carry the gap into Phase 1.4 so the plan records it honestly — especially when the user explicitly requested external research, where a silent skip would leave the plan looking evidence-based when it is not.

#### 1.4 Consolidate Research

Summarize:
- Relevant codebase patterns and file paths
- Relevant institutional learnings
- Organizational context from Slack conversations, if gathered (prior discussions, decisions, or domain knowledge relevant to the feature)
- External references, prior art, competitor/landscape findings, and best practices, if gathered
- Related issues, PRs, or prior art
- Any constraints that should materially shape the plan

**Land external findings in decisions, not an appendix.** Any external research that ran must surface where it changes a choice — Key Technical Decisions rationale, Alternatives, Risks, or Sources & Research — not as a detached list with no bearing on the plan. If a finding shaped nothing, do not pad the plan with it.

**Record requested-but-unavailable.** If the user explicitly requested external research but it could not run (web tools unavailable, researcher failed), state that in the plan as an assumption or open question rather than presenting the plan as externally grounded.

#### 1.5 Flow and Edge-Case Analysis (Conditional)

When user flow completeness is still unclear, run:

- Task mash-spec-flow-analyzer(planning context summary, research findings)

Use the output to:
- Identify missing edge cases, state transitions, or handoff gaps
- Tighten requirements trace or verification strategy
- Add only the flow details that materially improve the plan

