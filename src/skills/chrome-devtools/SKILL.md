---
name: chrome-devtools
description: Thin loader for one Lighthouse audit or one memory diagnostic through the chrome-devtools command line tool. Ordinary page journeys stay on agent-browser.
---

# Chrome DevTools

One sequence for Lighthouse, or one sequence for memory. This skill does not call a binary guide. Stop if `mash-chrome-devtools` is missing.

The tool keeps its browser in a background server that nothing expires on its own, so the server is this skill's to start and this skill's to stop. Run the sequence in order and stop the server even when the diagnostic fails:

```bash
mash-chrome-devtools start --categoryInput=false --categoryEmulation=false \
  --categoryNetwork=false --categoryPerformance=false \
  --memoryDebugging=true --isolated=true
mash-chrome-devtools new_page "<url>"
mash-chrome-devtools lighthouse_audit <pageId> [--mode snapshot|navigation] [--device desktop|mobile]
mash-chrome-devtools stop
```

For memory, replace the audit line with `take_heapsnapshot <pageId> <file.heapsnapshot>`, then read it with `get_heapsnapshot_summary`, `get_heapsnapshot_retainers` or `compare_heapsnapshots`, and still finish with `stop`.

`start` must carry the flags above: a tool command on its own starts a server with default categories, and the heap tools are then missing. Page ids come from the `new_page` listing and start at 1, so the id is never `0`. `status` reports the running server, and a second `start` restarts it, discarding the pages the first one held.

Navigation exists only to reach the audit target and obtain a page id. Do not use click, fill, or general browsing with this tool. Do not use it for Dogfood. Ordinary page journeys stay on agent-browser.

Do not fall back to agent-browser for the diagnostic, and do not fall back to this tool for a page journey.
