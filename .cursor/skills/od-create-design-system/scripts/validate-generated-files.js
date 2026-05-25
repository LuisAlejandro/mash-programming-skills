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

function readJson(filePath) {
  if (!fs.existsSync(filePath)) throw new Error(`Missing JSON file: ${filePath}`);
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function readText(filePath) {
  if (!fs.existsSync(filePath)) throw new Error(`Missing file: ${filePath}`);
  return fs.readFileSync(filePath, "utf8");
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function main() {
  try {
    const args = parseArgs(process.argv.slice(2));
    const root = path.resolve(args["project-root"] || process.cwd());
    const pageSlug = args["page-slug"] || "opendesign-page";
    const cursorDir = path.join(root, ".cursor");

    const artifact = readJson(path.join(cursorDir, "od-artifact.json"));
    const catalog = readJson(path.join(cursorDir, "od-component-catalog.json"));
    const context = readJson(path.join(cursorDir, "od-design-context.json"));
    const baseRules = readText(path.join(cursorDir, "rules", "od-design-system.mdc"));
    const pageRules = readText(path.join(cursorDir, "rules", `od-ds-${pageSlug}.mdc`));

    assert(artifact.source === "opendesign-export", "artifact.source must be opendesign-export");
    assert(/\.html?$/i.test(artifact.htmlPath), "artifact.htmlPath must be an HTML file");
    assert(catalog.components && typeof catalog.components === "object", "catalog.components must exist");
    assert(Array.isArray(context.serialized?.controlInventory), "context serialized control inventory must be an array");
    assert(baseRules.includes("OpenDesign Design System"), "base rules missing OpenDesign heading");
    assert(baseRules.includes("Source artifact is exported OpenDesign HTML/CSS"), "base rules missing source contract");
    assert(pageRules.includes("Control Inventory"), "page rules missing control inventory section");

    if (args["expect-component"]) {
      assert(
        Boolean(catalog.components[args["expect-component"]]),
        `Expected component missing from catalog: ${args["expect-component"]}`,
      );
    }

    if (args["expect-control-kind"]) {
      assert(
        context.serialized.controlInventory.some((item) => item.kind === args["expect-control-kind"]),
        `Expected control kind missing: ${args["expect-control-kind"]}`,
      );
    }

    process.stdout.write("OpenDesign generated files validation passed\n");
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}

if (require.main === module) main();
