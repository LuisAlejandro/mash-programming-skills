---
name: chrome-devtools
description: Thin loader for one Lighthouse audit or one memory diagnostic through Chrome DevTools MCP. Ordinary page journeys stay on agent-browser.
---

# Chrome DevTools

One sequence for Lighthouse, or one sequence for memory. This skill does not call a binary guide. Stop if the chrome-devtools MCP server is missing.

Navigation exists only to reach the audit target and obtain a page id. Do not use click, fill, or general browsing on this server. Do not use it for Dogfood. Ordinary page journeys stay on agent-browser.

Do not fall back to agent-browser for the diagnostic, and do not fall back to this server for a page journey.
