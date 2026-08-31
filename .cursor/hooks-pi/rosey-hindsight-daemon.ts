/**
 * Rosey Hindsight warm-start for Pi.
 * Registered via .pi/extensions/ (auto-discovered after project trust).
 * Runs .pi/hooks/ensure-hindsight-daemon.sh on session_start — fail-open.
 */
import { spawn } from "node:child_process";
import { join } from "node:path";
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  pi.on("session_start", async () => {
    const script = join(process.cwd(), ".pi/hooks/ensure-hindsight-daemon.sh");
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
