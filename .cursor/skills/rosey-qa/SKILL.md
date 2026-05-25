---
name: rosey-qa
description: Use when completing tasks, implementing major features, before merging to verify work meets requirements, or as the final step of the feature workflow handed off from rosey-developer.
---

## Communication while using this skill

**Caveman lite** for all assistant prose while this skill runs: strip filler and hedging; keep articles and full sentences; stay professional and tight. Technical accuracy unchanged; quoted errors and code unchanged. Drop lite only for security warnings, irreversible confirmations, or when the user asks for normal or long-form wording.

# Requesting Code Review

Dispatch a code-reviewer subagent to catch issues before they cascade.

**Core principle:** Review early, review often.

## When to Request Review

**Mandatory:**

- As the final step of the **rosey-developer** workflow (handoff)
- After each task in subagent-driven development
- After completing major feature
- Before merge to main

**Optional but valuable:**

- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After fixing complex bug

## How to Request

**1. Collect changed files and Sentrux context:**

Get the list of files changed by the implementer's report. When handoff includes **`SENTRUX_REVIEW_CONTEXT`** (from `sentrux-review-brief.json`), pass it to the reviewer. If the brief is missing but topology exists, note that structural review may be incomplete.

**2. Dispatch code-reviewer subagent:**

Use Task tool with `generalPurpose` type, fill template at `code-reviewer.md`

**No Git diff** — the workspace root is not assumed to be a Git repo. Reviewers **read the listed files** from disk and use `{WHAT_WAS_IMPLEMENTED}` plus optional `{CHANGE_SUMMARY}` for context.

**Placeholders:**

- `{WHAT_WAS_IMPLEMENTED}` - What you just built
- `{PLAN_OR_REQUIREMENTS}` - What it should do
- `{FILES_CHANGED}` - List of files to read (paths you created or modified)
- `{DESCRIPTION}` - Brief summary
- `{CHANGE_SUMMARY}` - Optional; per-file notes, line ranges, or excerpts for large files
- `{SENTRUX_REVIEW_CONTEXT}` - Structural session deltas, test_gaps, and override notes from rosey-developer (required when Sentrux brief exists; see [rosey-sentrux](../rosey-sentrux/SKILL.md))

**3. Act on feedback:**

- Fix Critical issues immediately
- Fix Important issues before proceeding
- Note Minor issues for later
- Push back if reviewer is wrong (with reasoning)

**4. Final Handoff (if from rosey-developer):**

If you were invoked as the final step of the **rosey-developer** workflow, after all Critical and Important issues are resolved (or if none were found), report to the user: **"Plan complete."**

## Example

```
[Just completed Task 2: Add verification function]

You: Let me request code review before proceeding.

[Dispatch generalPurpose subagent with code-reviewer.md template]
  WHAT_WAS_IMPLEMENTED: Verification and repair functions for conversation index
  PLAN_OR_REQUIREMENTS: Task 2 from docs/plans/deployment-plan.md
  FILES_CHANGED: src/backend/internal/services/verifier.go, src/backend/internal/controllers/verify_controller.go
  DESCRIPTION: Added verifyIndex() and repairIndex() with 4 issue types

[Subagent returns]:
  Strengths: Clean architecture, good separation of concerns
  Issues:
    Important: Missing progress indicators
    Minor: Magic number (100) for reporting interval
  Assessment: Ready to proceed

You: [Fix progress indicators]
[Continue to Task 3]
```

## Integration with Workflows

**Subagent-Driven Development:**

- Review after EACH task
- Catch issues before they compound
- Fix before moving to next task

**Executing Plans:**

- Review after each batch (3 tasks)
- Get feedback, apply, continue

**Ad-Hoc Development:**

- Review before merge
- Review when stuck

## Red Flags

**Never:**

- Skip review because "it's simple"
- Ignore Critical issues
- Proceed with unfixed Important issues
- Argue with valid technical feedback

**If reviewer wrong:**

- Push back with technical reasoning
- Show code/tests that prove it works
- Request clarification

See template at: rosey-qa/code-reviewer.md
