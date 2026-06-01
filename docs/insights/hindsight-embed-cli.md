---
title: Hindsight uses embed CLI, not MCP
module: rosey-memory
problem_type: durable_insight
component: rosey-hindsight
tags:
  - hindsight
  - memory
  - cursor
  - workflow
applies_when:
  - Adding or modifying Rosey memory behavior
severity: medium
---

## Insight

- Rosey skills use Hindsight via `uvx hindsight-embed`, not `.cursor/mcp.json`.

## When It Applies

- Adding or modifying Rosey memory behavior.

## What To Do

- Update `rosey-hindsight` and workflow skill references instead of adding a Hindsight MCP server.

## Evidence

- `.cursor/skills/rosey-hindsight/SKILL.md`
