# Manual checklist

WCAG 2.2 AA is the orientation for these questions. The answers are observations. Never claim the target is WCAG compliant.

Interactive runs: the person performs the check and reports Pass or Fail. Non-interactive runs: every row is `Blocked (needs human verify)` with reason "manual check needs a person".

| Check id | What the person checks |
| --- | --- |
| `a11y.manual.keyboard-path` | A full keyboard path exists for the primary journey. Every interactive control is reachable without a pointer. |
| `a11y.manual.focus-visible` | The focused control shows a visible indicator at each stop. |
| `a11y.manual.no-trap` | Focus can leave every component. No keyboard trap. |
| `a11y.manual.accessible-names` | Form controls have accessible names. The visible label is included in the accessible name where a label is shown. |
| `a11y.manual.errors-associated` | An error is associated with its field, and the person can tell which field failed. |
| `a11y.manual.image-alt-spot` | Images that convey meaning have a text alternative. Decorative images are not announced as content. Spot-check the primary journey. |
| `a11y.manual.contrast-spot` | Primary text and buttons have enough contrast to read. Name the tool used (browser contrast picker, a platform checker, or a stated manual judgment). |
| `a11y.manual.screen-reader` | One screen-reader pass on the primary journey with VoiceOver, NVDA, or Orca. The person drives it. Record the tool name. |
| `a11y.manual.reduced-motion` | If the UI animates, `prefers-reduced-motion` is respected. If nothing animates, `Skipped` with that reason. |
| `a11y.manual.reflow-390` | At 390px width the primary journey reflows: no clipped focus, no overlapping controls that block the action. |
| `a11y.manual.reflow-1440` | At 1440px width the same journey still shows a visible focus indicator and the primary action. |

Severity when the person reports a failure: keyboard trap, missing name on the primary control, or a screen-reader block on the primary action is `P1`. A contrast or reflow problem that still leaves the action operable is `P2`. Record the person's words in the note. Their confirmation is the evidence for a manual Fail. Do not invent a command block for a check that had no command.
