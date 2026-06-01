#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const { pageDir } = require("./lib/rosey-paths");
const { DEFAULT_VIEWPORTS, assessReviewerAlignment } = require("./lib/viewport-merge");

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

function assertExists(filePath, label) {
  if (!fs.existsSync(filePath)) throw new Error(`Missing ${label}: ${filePath}`);
}

function runValidate(scriptPath, type, reportPath) {
  execFileSync(process.execPath, [scriptPath, "--type", type, "--report", reportPath], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
}

function main() {
  try {
    const args = parseArgs(process.argv.slice(2));
    if (!args["project-root"] || !args["page-slug"] || !args.cycle) {
      console.error(
        "Usage: node validate-iteration-cycle.js --project-root <root> --page-slug <slug> --cycle <N> [--require-sync] [--viewports 1440x900,1024x768,390x844]",
      );
      process.exit(1);
    }

    const projectRoot = path.resolve(args["project-root"]);
    const pageSlug = args["page-slug"];
    const cycle = String(args.cycle);
    const reviewDir = path.resolve(args["review-dir"] || path.join(pageDir(projectRoot, pageSlug), "review"));
    const viewports = args.viewports ? args.viewports.split(",").map((v) => v.trim()).filter(Boolean) : DEFAULT_VIEWPORTS;
    const validateScript = path.join(__dirname, "validate-agent-report.js");

    const reviewerReportPath = path.join(reviewDir, `cycle-${cycle}-reviewer-report.json`);
    const syncReportPath = path.join(reviewDir, `cycle-${cycle}-sync-report.json`);

    assertExists(reviewerReportPath, "reviewer report");
    for (const viewport of viewports) {
      assertExists(path.join(reviewDir, `parity-${viewport}.json`), `parity report (${viewport})`);
    }

    runValidate(validateScript, "reviewer", reviewerReportPath);

    const reviewerReport = JSON.parse(fs.readFileSync(reviewerReportPath, "utf8"));
    const alignment = assessReviewerAlignment(reviewerReport);
    if (alignment.blocking.length > 0 || alignment.major.length > 0) {
      process.stdout.write(
        `${JSON.stringify(
          {
            cycle: Number(cycle),
            aligned: false,
            reason: alignment.reason,
            blocking: alignment.blocking.length,
            major: alignment.major.length,
            requiresSync: true,
          },
          null,
          2,
        )}\n`,
      );
    } else {
      process.stdout.write(
        `${JSON.stringify(
          {
            cycle: Number(cycle),
            aligned: true,
            reason: alignment.reason,
            requiresSync: false,
          },
          null,
          2,
        )}\n`,
      );
    }

    if (args["require-sync"]) {
      assertExists(syncReportPath, "sync report");
      runValidate(validateScript, "sync", syncReportPath);
    } else if (fs.existsSync(syncReportPath)) {
      runValidate(validateScript, "sync", syncReportPath);
    }

    process.stdout.write(`Iteration cycle ${cycle} validation passed\n`);
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}

if (require.main === module) main();
