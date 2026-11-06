#!/usr/bin/env node
// Run axe-core against a saved HTML document.
//
// ponytail: jsdom does not layout, paint, or execute the page's own scripts.
// color-contrast stays disabled. landmark-one-main and page-has-heading-one
// are reported as jsdomUndecided, not as failures. Upgrade path: keep capture
// on the agent-browser skill and teach this runner to read a browser
// accessibility tree if that ceiling hides a real defect.

import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { JSDOM, VirtualConsole } from "jsdom";

const require = createRequire(import.meta.url);
const axe = require("axe-core");

const IMPACT_SEVERITY = {
  critical: "P0",
  serious: "P1",
  moderate: "P2",
  minor: "P3",
};

// jsdom has no canvas, so axe's contrast measurement throws and cannot pass.
// The manual contrast check is the one that records a result.
const DISABLED_RULES = ["color-contrast"];

// These two rules return incomplete in jsdom even when the landmark and heading
// are present, because jsdom does not resolve visibility. They are reported
// separately so a scan does not look blocked on every page.
const JSDOM_UNDECIDED = new Set(["landmark-one-main", "page-has-heading-one"]);

const FAILING_FIXTURE = `<!DOCTYPE html><html lang="en"><head><title>Bad</title></head><body><main><h1>Bad</h1><button></button><img src="x.png"></main></body></html>`;
const CLEAN_FIXTURE = `<!DOCTYPE html><html lang="en"><head><title>Ok</title></head><body><main><h1>Ok</h1><button>Save</button></main></body></html>`;

function usage() {
  console.error(
    "Usage: node scripts/run_axe.mjs --html <file> --url <absolute-page-url>\n" +
      "       node scripts/run_axe.mjs --self-check",
  );
  process.exit(1);
}

function parseArgs(argv) {
  const out = { html: null, url: null, selfCheck: false };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--self-check") out.selfCheck = true;
    else if (arg === "--html") out.html = argv[++i];
    else if (arg === "--url") out.url = argv[++i];
    else usage();
  }
  return out;
}

function requireHttpUrl(url) {
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    console.error("url must be an absolute http(s) URL");
    process.exit(1);
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    console.error("url must be an absolute http(s) URL");
    process.exit(1);
  }
  return url;
}

async function runAxe(html, url) {
  const virtualConsole = new VirtualConsole();
  virtualConsole.sendTo(console, { omitJSDOMErrors: true });
  const dom = new JSDOM(html, {
    url,
    pretendToBeVisual: true,
    runScripts: "outside-only",
    virtualConsole,
  });
  try {
    dom.window.eval(axe.source);
    return await dom.window.axe.run(dom.window.document, {
      resultTypes: ["violations", "incomplete", "passes"],
      rules: Object.fromEntries(DISABLED_RULES.map((id) => [id, { enabled: false }])),
    });
  } finally {
    dom.window.close();
  }
}

function summarize(results, url) {
  const mapRule = (rule) => ({
    id: rule.id,
    impact: rule.impact,
    help: rule.help,
    nodes: rule.nodes.length,
  });
  const violations = results.violations.map((rule) => ({
    ...mapRule(rule),
    severity: IMPACT_SEVERITY[rule.impact] || "P2",
    wcag: (rule.tags || []).filter((tag) => String(tag).startsWith("wcag")),
    targets: rule.nodes.slice(0, 5).map((node) => node.target),
  }));
  const jsdomUndecided = results.incomplete.filter((rule) => JSDOM_UNDECIDED.has(rule.id)).map(mapRule);
  const incomplete = results.incomplete.filter((rule) => !JSDOM_UNDECIDED.has(rule.id)).map(mapRule);
  return {
    url,
    axeVersion: results.testEngine?.version || axe.version,
    violations,
    incomplete,
    jsdomUndecided,
    passCount: results.passes.length,
    disabledRules: DISABLED_RULES,
  };
}

function printHuman(summary) {
  console.log(`axe ${summary.axeVersion} on ${summary.url}`);
  console.log(
    `violations: ${summary.violations.length}; incomplete: ${summary.incomplete.length}; jsdom undecided: ${summary.jsdomUndecided.length}; passes: ${summary.passCount}`,
  );
  for (const rule of summary.violations) {
    console.log(
      `FAIL ${rule.severity} ${rule.id} (${rule.impact}) nodes=${rule.nodes} ${rule.help}`,
    );
  }
  for (const rule of summary.incomplete) {
    console.log(`INCOMPLETE ${rule.id} nodes=${rule.nodes} ${rule.help}`);
  }
}

function printMachine(summary) {
  console.log("AXE_JSON");
  console.log(JSON.stringify(summary));
  console.log("END_AXE_JSON");
}

async function selfCheck() {
  const bad = summarize(
    await runAxe(FAILING_FIXTURE, "http://localhost/bad"),
    "http://localhost/bad",
  );
  const good = summarize(
    await runAxe(CLEAN_FIXTURE, "http://localhost/ok"),
    "http://localhost/ok",
  );
  const badIds = new Set(bad.violations.map((rule) => rule.id));
  if (!badIds.has("button-name") || !badIds.has("image-alt")) {
    console.error("self-check: expected button-name and image-alt violations");
    console.error(JSON.stringify(bad));
    process.exit(1);
  }
  if (good.violations.length > 0 || good.incomplete.length > 0) {
    console.error("self-check: clean fixture reported a violation or a real incomplete");
    console.error(JSON.stringify(good));
    process.exit(1);
  }
  const undecided = new Set(good.jsdomUndecided.map((rule) => rule.id));
  if (!undecided.has("landmark-one-main") || !undecided.has("page-has-heading-one")) {
    console.error("self-check: expected jsdom-undecided landmark and heading rules");
    console.error(JSON.stringify(good));
    process.exit(1);
  }
  const unlabeled = bad.violations.find((rule) => rule.id === "button-name");
  if (unlabeled.severity !== "P0" && unlabeled.severity !== "P1") {
    console.error("self-check: button-name severity must be P0 or P1");
    process.exit(1);
  }
  console.log("self-check ok");
}

const args = parseArgs(process.argv.slice(2));

if (args.selfCheck) {
  await selfCheck();
} else {
  if (!args.html || !args.url) usage();
  const url = requireHttpUrl(args.url);
  const html = readFileSync(args.html, "utf8");
  const summary = summarize(await runAxe(html, url), url);
  printMachine(summary);
  printHuman(summary);
  if (summary.violations.length > 0) process.exit(2);
}
