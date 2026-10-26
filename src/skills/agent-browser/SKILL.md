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

A session this skill drives is detectable. Chrome reports `navigator.webdriver` as `true` whenever automation is attached, and stricter Cloudflare Turnstile deployments reject that flag alone — a sign-in a human could complete fails under automation. Swapping the browser binary changes the fingerprint but not the flag: a challenge cannot be passed inside a window this skill is driving.

The fix is two phases. **Phase 1, human, no automation:**

```bash
open -na "Google Chrome" --args --user-data-dir="<dedicated-dir>"
```

This window has no debugging port and no automation flag, so it is a normal browser. The human signs in and passes the challenge there. Do not attach to it, do not drive it, and do not type credentials.

**Phase 2, after the wall is passed:** quit that instance, then start the same profile yourself and attach — do **not** let agent-browser launch it:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir=<same dedicated-dir> --remote-debugging-port=<port> <url>
agent-browser connect <port>
```

agent-browser's own launch passes `--password-store=basic --use-mock-keychain`. A mock keychain cannot decrypt cookies written under the OS keychain, so a profile logged in by real Chrome comes back signed out and Chrome drops those cookies on exit. Never launch agent-browser on a profile that holds a human login. Check the flags before trusting a session: `ps -Ao args | grep -- --user-data-dir | tr ' ' '\n' | grep mock-keychain` must be empty.

macOS binary: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`.

- Run phase 2 only after the human reports the wall is passed. Close only the process this skill started, identified by its `--user-data-dir`, never by generic name.
- Headed in both phases. Headless reports `HeadlessChrome` in `navigator.userAgent`, a bot signal by itself.
- Before blaming content or credentials, check the transport signals: `agent-browser eval 'navigator.webdriver'` must be `true` for a driven session, and `navigator.userAgent` must name no `HeadlessChrome` token. Do not conclude "the swap is enough" without reading them.
- Never ask the human to solve a challenge in a window this skill drives. If a challenge appears in a driven window, close it and return to phase 1.
- The dedicated profile directory carries that login into later runs. Never copy a Chrome profile or cookie store into another browser: the cookies are encrypted to the binary that wrote them and stay unreadable.
- Never reuse the human's live profile, and close only the session this skill started.
- If the challenge fails again in phase 1, stop and report it. Do not loop retries.

Rendered text is not proof of state. A page that looks signed in can still be answering with failed requests, so read the response body before reporting an empty page as fact.
