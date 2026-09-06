# Outstanding Asks

Track requests that originated outside the loop. This file is append-only. An ask is not
finished until it is both satisfied and communicated; a satisfied ask that was never
communicated is an unresolved blocker, so `SUCCESS` cannot be declared while one exists.

## {{ASK_TITLE}}

- Recorded: {{TIMESTAMP}}
- Asked by: {{ASKED_BY}}
- Where it was asked / anchored: {{ANCHOR}}
- Ask restated as testable work: {{TESTABLE_WORK}}
- What satisfied it: {{SATISFIED_BY}}
- Evidence: {{EVIDENCE}}
- Communicated: {{COMMUNICATED_YES_NO}}
- Communicated to: {{COMMUNICATED_TO}}
- Channel: {{CHANNEL}}
- Link sent: {{LINK_SENT}}
- Confirmation observed: {{CONFIRMATION_OBSERVED}}

<!-- Append a dated resolution beneath the original item; do not delete or rewrite the ask.

Communication needs the same standard of evidence as a passing check. Record who it went to,
over what channel, the exact link sent, and the observation confirming it was sent — the
message identifier, timestamp, or equivalent. An intended message, a drafted message, a pushed
document nobody was pointed at, and a merge are all still NO. A request closed without building
— declined or superseded — still needs communicating; silence is the failure, not the decision.
-->
