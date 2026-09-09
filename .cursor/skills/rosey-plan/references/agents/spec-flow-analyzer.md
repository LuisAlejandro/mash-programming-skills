# Spec Flow Analyzer — prompt asset

Fallback for `rosey-spec-flow-analyzer` when the named agent is not installed. Seed a generic subagent with this prompt, the planning context summary, and the consolidated research findings. Runs at Phase 1.5 for Standard and Deep plans, or when flow completeness is unclear.

## Task

Work through the behavior the plan proposes and find what the plan has not accounted for.

Look for:

1. **Missing edge cases** — boundary values, empty and null states, concurrent access, the second call, the retry.
2. **State transitions** the plan implies but does not name, including the ones that go backwards or fail partway.
3. **Handoff gaps** — where control passes between actors, layers, services, or processes and the plan does not say what happens if the other side is slow, absent, or wrong.
4. **Error and failure paths** for each step that can fail, and what the user or caller sees when it does.
5. **Flows that are described but never verified** — behavior the plan asserts with no corresponding test scenario.

## What to return

Only findings that would **materially improve the plan**: a missing case that would change a requirement, a unit boundary, a test scenario, or a risk. For each, say where in the plan it belongs.

Do not restate the flows the plan already covers correctly. Do not invent product behavior — where a gap is a genuine product question rather than an oversight, flag it as an open question for the user instead of answering it.
