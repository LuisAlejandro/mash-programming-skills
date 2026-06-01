#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { pageDir, readJsonIfExists } = require("./lib/rosey-paths");
const {
  DEFAULT_VIEWPORTS,
  assessAlignmentFromReports,
  assessReviewerAlignment,
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

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function validateChecklist(checklist, options = {}) {
  if (!checklist?.items?.length) {
    if (options.requireChecklist) throw new Error("implementation-checklist.json is missing or empty");
    return { pending: [], complete: true };
  }
  const pending = checklist.items.filter((item) => item.status === "pending");
  if (options.requireChecklistComplete && pending.length > 0) {
    throw new Error(
      `implementation-checklist has ${pending.length} pending control(s): ${pending
        .slice(0, 5)
        .map((item) => item.stableId || item.id)
        .join(", ")}`,
    );
  }
  return { pending, complete: pending.length === 0 };
}

function validateIteratorReport(iteratorReport, options = {}) {
  if (!iteratorReport) {
    if (options.requireIterator) throw new Error("iterator-report.json is missing");
    return null;
  }
  if (options.requireAligned) {
    assert(iteratorReport.status === "aligned", `iterator status must be aligned, got ${iteratorReport.status}`);
  }
  if (options.requireAligned) {
    const remaining = iteratorReport.remainingFindings || [];
    const blockingRemaining = remaining.filter((f) => f.severity === "blocking" || f.severity === "major");
    assert(
      blockingRemaining.length === 0,
      `iterator remainingFindings still has ${blockingRemaining.length} blocking/major item(s)`,
    );
  }
  return iteratorReport;
}

function main() {
  try {
    const args = parseArgs(process.argv.slice(2));
    if (!args["project-root"] || !args["page-slug"]) {
      console.error(
        "Usage: node validate-implementation-state.js --project-root <root> --page-slug <slug> [--require-checklist-complete] [--require-aligned] [--review-dir <dir>] [--reviewer-report <path>]",
      );
      process.exit(1);
    }

    const projectRoot = path.resolve(args["project-root"]);
    const pageSlug = args["page-slug"];
    const pageRoot = pageDir(projectRoot, pageSlug);
    const reviewDir = path.resolve(args["review-dir"] || path.join(pageRoot, "review"));
    const viewports = args.viewports ? args.viewports.split(",").map((v) => v.trim()).filter(Boolean) : DEFAULT_VIEWPORTS;

    const checklist = readJsonIfExists(path.join(pageRoot, "implementation-checklist.json"));
    const mapping = readJsonIfExists(path.join(pageRoot, "component-mapping.json"));
    const assetMap = readJsonIfExists(path.join(pageRoot, "asset-map.json"));
    const iteratorReport = readJsonIfExists(path.join(reviewDir, "iterator-report.json"));

    assert(fs.existsSync(path.join(pageRoot, "design-context.json")), "design-context.json is required");
    assert(mapping, "component-mapping.json is required");
    assert(assetMap !== null, "asset-map.json is required");

    const checklistResult = validateChecklist(checklist, {
      requireChecklist: args["require-checklist-complete"],
      requireChecklistComplete: args["require-checklist-complete"],
    });

    validateIteratorReport(iteratorReport, {
      requireIterator: args["require-aligned"],
      requireAligned: args["require-aligned"],
    });

    const viewportAlignment = assessAlignmentFromReports(reviewDir, viewports);
    if (args["require-aligned"]) {
      assert(viewportAlignment.aligned, `viewport parity not aligned: ${viewportAlignment.reason}`);
    }

    if (args["reviewer-report"]) {
      const reviewerReport = readJsonIfExists(path.resolve(args["reviewer-report"]));
      assert(reviewerReport, "reviewer report path is missing or invalid");
      const reviewerAlignment = assessReviewerAlignment(reviewerReport);
      if (args["require-aligned"]) {
        assert(reviewerAlignment.aligned, `reviewer report not aligned: ${reviewerAlignment.reason}`);
      }
    }

    if (args["require-checklist-complete"] && checklist) {
      const missingControls = (checklist.items || []).filter((item) => item.status === "missing");
      if (missingControls.length > 0 && args["require-aligned"]) {
        throw new Error(`checklist still has ${missingControls.length} missing control(s)`);
      }
    }

    const summary = {
      pageSlug,
      checklistComplete: checklistResult.complete,
      pendingControls: checklistResult.pending.length,
      viewportAligned: viewportAlignment.aligned,
      viewportReason: viewportAlignment.reason,
      iteratorStatus: iteratorReport?.status || null,
    };

    process.stdout.write(`Implementation state validation passed\n${JSON.stringify(summary, null, 2)}\n`);
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}

if (require.main === module) main();
