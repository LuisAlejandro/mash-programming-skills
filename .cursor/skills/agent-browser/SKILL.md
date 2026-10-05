---
name: agent-browser
description: Thin loader for page automation through agent-browser. Use for navigation, snapshots, interaction, uploads, downloads, screenshots, console, and network.
---

# agent-browser

Page navigation, snapshots, interaction, uploads, downloads, screenshots, console, and network.

Before acting, run `agent-browser --version` and stop if a reported token is not `0.38.2`. Load the version-matched guide with `agent-browser skills get`. Stop if that command is missing or the reported version is not the pin.

Require a named session. Refuse a profile named `Default` and refuse auto-connect. Persistent state is an explicit profile directory. Credentials do not appear in prompts, reports, or repository files.

After a native dialog or file picker, hand only that surface to the CUA Driver skill, observe again, then continue on the page. Stop if the binary or schema does not match the pin.
