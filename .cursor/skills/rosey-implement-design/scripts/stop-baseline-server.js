#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (!key.startsWith("--")) continue;
    const name = key.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) args[name] = true;
    else {
      args[name] = next;
      i += 1;
    }
  }
  return args;
}

function readPid(pidFile) {
  if (!pidFile || !fs.existsSync(pidFile)) return null;
  const raw = fs.readFileSync(pidFile, "utf8").trim();
  const pid = Number(raw);
  return Number.isFinite(pid) && pid > 0 ? pid : null;
}

function isRunning(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

function stopPid(pid) {
  if (!isRunning(pid)) return { pid, status: "not-running" };
  try {
    process.kill(pid, "SIGTERM");
    return { pid, status: "terminated" };
  } catch (error) {
    return { pid, status: "failed", error: error.message };
  }
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const pidFile = args["pid-file"] ? path.resolve(args["pid-file"]) : null;
  const stateFile = args["state-file"] ? path.resolve(args["state-file"]) : null;

  let pid = readPid(pidFile);
  if (!pid && stateFile && fs.existsSync(stateFile)) {
    try {
      const state = JSON.parse(fs.readFileSync(stateFile, "utf8"));
      pid = state.pid || null;
    } catch {
      pid = null;
    }
  }

  if (!pid) {
    process.stdout.write("Baseline server not running (no pid found)\n");
    if (pidFile && fs.existsSync(pidFile)) fs.unlinkSync(pidFile);
    return;
  }

  const result = stopPid(pid);
  if (pidFile && fs.existsSync(pidFile)) fs.unlinkSync(pidFile);

  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
}

if (require.main === module) main();
