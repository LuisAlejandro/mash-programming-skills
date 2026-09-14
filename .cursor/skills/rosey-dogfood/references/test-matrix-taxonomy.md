# Test Matrix Taxonomy

Use these dimensions to turn clustered journeys into a browser test matrix. Not every dimension applies to every cluster — pick the ones the shipped change actually touches, but err toward coverage. The goal is to test **complete user journeys**, not isolated widgets and not one script per PR.

## 1. Journeys (the spine of the matrix)

For each clustered user-visible change, trace the full path a real user takes, end to end:

- **Entry** — how does the user arrive? (link, redirect, notification, deep link)
- **Action** — what do they do? (click, fill, submit, upload, drag)
- **Result** — what should happen? (navigation, state change, message, side effect)
- **Destination** — does it land them in the *right* place, with the *right* item focused/scrolled into view, showing the *right* data?
- **Aftermath** — follow side effects to their real end state. If an email/notification/job fires, did it reach the right recipient with sensible content? If a record was created, does it appear correctly everywhere it should?

The email test is the canonical example: "an email sends" is not a pass. Right recipient, click-through scrolls to the right message, content makes sense, whole flow coheres.

## 2. Functional checks — "does it work?"

- Primary content renders; headings/titles present.
- Forms have the expected fields; validation accepts good input and rejects bad input with clear messages.
- Buttons/links go where they claim; nothing dead-ends.
- Data shown matches data saved (round-trip create → view → edit → view).
- No console errors or failed network requests during the journey.
- Auth/permission boundaries hold (the right users can/can't do the thing).

## 3. Experiential checks — "does it feel right?"

- Does it align with the product's vision and existing UX patterns?
- Is the copy clear and consistent with the rest of the app?
- Are loading, success, and transition states present and unsurprising?
- Does the layout look intentional, or is something visibly broken/misaligned?
- Would a real user understand what to do without explanation?

### Persona paper cuts

Walk each flow as each primary persona from Phase 1. A **paper cut** is small friction that passes functional tests but degrades the experience for that persona: confusing label, extra click, unexpected jump, slow-feeling step, missing feedback, copy that doesn't match how they think. Record the paper cut, which persona feels it, and severity. Functionally-passing scenarios can still carry paper cuts.

## 4. Edge, error, and empty states

- **Empty:** no data yet — is there a sensible empty state, not a blank/broken page?
- **Boundary:** very long text, zero, max values, special characters, unicode.
- **Error:** server error, validation failure, expired session, lost network — handled gracefully?
- **Concurrency / re-entry:** double-submit, back button, refresh mid-flow, stale tab.

## 5. Cross-cutting

- **Responsiveness:** key pages at mobile and desktop widths.
- **Accessibility:** focus order, labels on inputs, keyboard operability of new interactive elements.
- **Regression:** adjacent journeys a shared layout or component could plausibly have broken. One scenario per shared surface, not a tour of the app.

## 6. Non-page scenarios

Some shipped work never paints a route. Still cover it, without inventing a page:

| Surface | How to test |
| --- | --- |
| API contract | Drive the user-visible consumer if one exists; otherwise one scenario that names the request/response and marks `Skipped` if it cannot be driven in the browser |
| Agent tool / agent-native path | Invoke the same action an agent would take, if the host exposes it; otherwise `Skipped` with reason |
| Email / SMS / payment / OAuth | Drive to the trigger, then `Blocked (needs human verify)` for the external leg |
| Background job | Trigger it from the UI if possible; confirm the user-visible aftermath |

## Mapping files to routes

| Changed file | Routes to test |
| --- | --- |
| `app/views/<x>/*`, `src/app/<x>/*`, `app/<x>/page.*` | The pages for `<x>` (index, show, new, edit) |
| component files | Pages that render the component — one primary plus adjacent regression if shared |
| layout / global stylesheet | One key page (homepage or the cluster's primary route), not every page |
| controller / route handler / API route | The routes it serves |
| helper / util used in views | Pages relying on it |
| JS / client controller | Pages where that behavior is wired |

Build the URL list from this mapping, attach those URLs to the clusters from `scope-extraction.md`, then expand each cluster into the journeys above.
