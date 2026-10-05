/**
 * Mash Programming Skills Hindsight warm-start for OpenCode.
 * Installed in ~/.config/opencode/plugin/ and loaded as a native global plugin.
 * The hook is fail-open: Hindsight must never block an OpenCode session.
 */

import { spawn } from "node:child_process";

const script = `${process.env.HOME ?? ""}/.pi/agent/scripts/ensure-hindsight-daemon.sh`;

function startDaemonCheck(): void {
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
    // Hindsight is optional; never block OpenCode startup.
  }
}

export default async function () {
  let started = false;
  return {
    event: async ({ event }: { event: { type?: string } }) => {
      if (!started && event?.type === "session.created") {
        started = true;
        startDaemonCheck();
      }
    },
  };
}
