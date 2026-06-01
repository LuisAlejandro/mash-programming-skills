#!/usr/bin/env node

const path = require("path");
const { execFileSync } = require("child_process");
const { pageDir } = require("./lib/rosey-paths");
const { DEFAULT_VIEWPORTS } = require("./lib/viewport-merge");

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

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args["baseline-url"] || !args["target-url"] || !args["project-root"] || !args["page-slug"]) {
    console.error(
      "Usage: node run-parity-viewports.js --project-root <root> --page-slug <slug> --baseline-url <url> --target-url <url> [--viewports 1440x900,1024x768,390x844] [--wait-selector <sel>]",
    );
    process.exit(1);
  }

  const projectRoot = path.resolve(args["project-root"]);
  const pageSlug = args["page-slug"];
  const reviewDir = path.resolve(args["review-dir"] || path.join(pageDir(projectRoot, pageSlug), "review"));
  const screenshotDir = path.resolve(args["screenshot-dir"] || path.join(reviewDir, "screenshots"));
  const viewports = args.viewports ? args.viewports.split(",").map((v) => v.trim()).filter(Boolean) : DEFAULT_VIEWPORTS;
  const compareScript = path.join(__dirname, "compare-parity.js");

  const outputs = [];
  for (const viewport of viewports) {
    const outPath = path.join(reviewDir, `parity-${viewport}.json`);
    const cmdArgs = [
      compareScript,
      "--baseline-url",
      args["baseline-url"],
      "--target-url",
      args["target-url"],
      "--viewport",
      viewport,
      "--screenshot-dir",
      screenshotDir,
      "--out",
      outPath,
    ];
    if (args["wait-selector"]) cmdArgs.push("--wait-selector", args["wait-selector"]);
    if (args["settle-ms"]) cmdArgs.push("--settle-ms", args["settle-ms"]);

    execFileSync(process.execPath, cmdArgs, { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
    outputs.push(path.relative(projectRoot, outPath));
  }

  process.stdout.write(`${JSON.stringify({ reviewDir: path.relative(projectRoot, reviewDir), outputs }, null, 2)}\n`);
}

if (require.main === module) main();
