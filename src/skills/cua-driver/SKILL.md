---
name: cua-driver
description: Thin loader for native desktop control through CUA Driver. Use for native apps, browser chrome, permission dialogs, file pickers, and webviews with no page endpoint.
---

# CUA Driver

Native apps, browser chrome, permission dialogs, file pickers, and webviews with no page endpoint. Do not use this skill for ordinary page content.

Before acting, run `cua-driver --version` and stop if a reported token is not `0.33.3`. Load the version-matched guide by reading the directory printed by `cua-driver skills path`. Stop if that command is missing or the directory is absent. The remediation is `cua-driver skills install` for the pinned release. Do not pass `--from main`, and do not copy the guide into this repository.

Start `CuaDriver.app` on demand when the daemon is down. Do not install a login item. If Accessibility or Screen Recording is missing on that app, stop and name the human grant. Do not request the grant from the installer or this skill.

CLI fallback is `cua-driver call` only when MCP transport is unavailable.
