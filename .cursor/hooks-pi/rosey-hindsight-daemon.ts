/**
 * Rosey Hindsight warm-start for Pi.
 * Installed in ~/.pi/agent/extensions/ and auto-discovered globally.
 * Runs ~/.pi/agent/scripts/ensure-hindsight-daemon.sh on session_start — fail-open.
 */
import { spawn } from "node:child_process";
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  pi.on("session_start", async () => {
    const script = `${process.env.HOME ?? ""}/.pi/agent/scripts/ensure-hindsight-daemon.sh`;
    try {
      const child = spawn(script, [], {
        detached: true,
        stdio: "ignore",
        env: {
          ...process.env,
          PATH: `${process.env.HOME ?? ""}/.local/bin:${process.env.PATH ?? ""}`,
        },
      });
      child.unref();
    } catch {
      // fail open — Hindsight is optional
    }
  });
}
