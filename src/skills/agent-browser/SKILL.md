---
name: agent-browser
description: Thin loader for page automation through agent-browser. Use for navigation, snapshots, interaction, uploads, downloads, screenshots, console, and network.
---

# agent-browser

Page navigation, snapshots, interaction, uploads, downloads, screenshots, console, and network.

Before acting, run `agent-browser --version` and stop if a reported token is not `0.38.2`. Load the version-matched guide with `agent-browser skills get`. Stop if that command is missing or the reported version is not the pin.

Require a named session. Refuse a profile named `Default` and refuse auto-connect. Persistent state is an explicit profile directory. Credentials do not appear in prompts, reports, or repository files.

After a native dialog or file picker, hand only that surface to the CUA Driver skill, observe again, then continue on the page. Stop if the binary or schema does not match the pin.

## Auth walls and bot checks

A site may detect browser automation and refuse sign-in or a challenge even when a person can sign in. A different browser binary, user agent, or profile is not a guaranteed solution; do not treat an auth wall as a missing binary or try to defeat the site's checks.

If the site permits continued automation, use two phases:

1. **Human sign-in, without automation.** Ask the human to open a headed Chrome window with a dedicated, non-default profile and sign in themselves. Never attach to this window, drive it, ask for credentials, or use their everyday browser profile. Ask the human to close this specific window when finished.
2. **Optional automation, with consent.** Only after the human confirms sign-in and permits the session to be automated, relaunch that dedicated profile in a headed browser with a local debugging port, then use the pinned `agent-browser connect <port>` under a named session. If the login disappears or the site challenges the automated session again, stop and report it; do not retry a bypass. Do not copy a profile or cookie store between browsers. Browser launch flags and OS credential storage can affect whether login survives a relaunch.

**macOS example only** (not a command for Linux or Windows). Give the human a dedicated path for phase 1; they run this themselves:

```bash
open -na "Google Chrome" --args --user-data-dir="/path/to/dedicated-profile"
```

Only after the human closes that window and approves phase 2, run this with the **same** profile path and an unused local port:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir="/path/to/dedicated-profile" \
  --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 "https://example.com"
agent-browser --session auth-handoff connect 9222
```

On Linux or Windows use only a verified equivalent for the installed Chrome and a dedicated profile. If the platform procedure or the pinned tool's connection method cannot be verified, stop and ask instead of running the macOS commands. Never launch a second browser against an already-open profile.

A driven browser may expose automation signals such as `navigator.webdriver`, and user agents may differ between headed and headless runs; neither signal alone proves whether a particular site will accept the session. Use a headed browser for human sign-in. Never ask the human to solve a challenge in a window this skill drives. Close only the browser process associated with the dedicated profile; never kill browsers by generic process name.

Rendered text is not proof of state. A page that looks signed in can still be answering with failed requests, so read the response body before reporting an empty page as fact.
