#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { pageDir, readJsonIfExists } = require("./lib/rosey-paths");
const {
  DEFAULT_VIEWPORTS,
  mergeParityFindings,
  loadParityReports,
  assessAlignmentFromFindings,
} = require("./lib/viewport-merge");

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

function buildControlInventoryStatus(context, checklist) {
  const inventory = context?.serialized?.controlInventory || [];
  const checklistByStable = new Map((checklist?.items || []).map((item) => [item.stableId, item]));
  const checklistById = new Map((checklist?.items || []).map((item) => [item.id, item]));

  return inventory.map((control) => {
    const row = checklistByStable.get(control.stableId) || checklistById.get(control.id);
    return {
      id: control.stableId || control.id,
      status: row?.status && row.status !== "pending" ? row.status : "missing",
      notes: row?.notes || "",
    };
  });
}

function main() {
  try {
    const args = parseArgs(process.argv.slice(2));
    if (!args["project-root"] || !args["page-slug"]) {
      console.error(
        "Usage: node merge-parity-report.js --project-root <root> --page-slug <slug> --baseline-url <url> --target-url <url> [--review-dir <dir>] [--out <path>] [--viewports 1440x900,1024x768,390x844]",
      );
      process.exit(1);
    }

    const projectRoot = path.resolve(args["project-root"]);
    const pageSlug = args["page-slug"];
    const reviewDir = path.resolve(args["review-dir"] || path.join(pageDir(projectRoot, pageSlug), "review"));
    const viewports = args.viewports ? args.viewports.split(",").map((v) => v.trim()).filter(Boolean) : DEFAULT_VIEWPORTS;

    const reports = loadParityReports(reviewDir, viewports);
    const findings = mergeParityFindings(reports);
    const alignment = assessAlignmentFromFindings(findings);

    const contextPath = args.context
      ? path.resolve(args.context)
      : path.join(pageDir(projectRoot, pageSlug), "design-context.json");
    const checklistPath = path.join(pageDir(projectRoot, pageSlug), "implementation-checklist.json");
    const context = readJsonIfExists(contextPath);
    const checklist = readJsonIfExists(checklistPath);

    const comparisonMethod = reports.some((r) => r.comparisonMethod === "dom-css-screenshots")
      ? "dom-css-screenshots"
      : "dom-css";

    const reviewerReport = {
      generatedAt: new Date().toISOString(),
      comparisonMethod,
      baselineUrl: args["baseline-url"] || reports.find((r) => r.baselineUrl)?.baselineUrl || "",
      targetUrl: args["target-url"] || reports.find((r) => r.targetUrl)?.targetUrl || "",
      viewports,
      findings: findings.map(({ viewport, stableId, ...finding }) => finding),
      controlInventoryStatus: buildControlInventoryStatus(context, checklist),
    };

    const outPath = args.out
      ? path.resolve(args.out)
      : path.join(reviewDir, "merged-reviewer-findings.json");
    const alignmentPath = path.join(reviewDir, "parity-alignment-summary.json");

    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, `${JSON.stringify(reviewerReport, null, 2)}\n`);
    fs.writeFileSync(
      alignmentPath,
      `${JSON.stringify(
        {
          generatedAt: new Date().toISOString(),
          aligned: alignment.aligned,
          reason: alignment.reason,
          blocking: alignment.blocking,
          major: alignment.major,
          minor: alignment.minor,
          parityReports: reports.map((r) => ({
            viewport: r.viewport,
            missing: Boolean(r.missing),
            comparisonMethod: r.comparisonMethod || null,
          })),
        },
        null,
        2,
      )}\n`,
    );

    process.stdout.write(
      `${JSON.stringify(
        {
          outPath: path.relative(projectRoot, outPath),
          aligned: alignment.aligned,
          reason: alignment.reason,
          findingCount: findings.length,
          blocking: alignment.blocking.length,
          major: alignment.major.length,
          minor: alignment.minor.length,
        },
        null,
        2,
      )}\n`,
    );
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}

if (require.main === module) main();
