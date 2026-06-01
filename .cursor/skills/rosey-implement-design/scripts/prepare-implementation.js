#!/usr/bin/env node

const path = require("path");
const fs = require("fs");
const { execFileSync } = require("child_process");
const { loadLatestRosey, pageDir, readJsonIfExists } = require("./lib/rosey-paths");

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

function runJson(scriptPath, args) {
  const output = execFileSync(process.execPath, [scriptPath, ...args], { encoding: "utf8" });
  return JSON.parse(output);
}

function run(scriptPath, args) {
  execFileSync(process.execPath, [scriptPath, ...args], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
}

function buildImplementationChecklist(context, mappingResult) {
  const inventory = context?.serialized?.controlInventory || [];
  const mappingById = new Map((mappingResult.mappings || []).map((entry) => [entry.id, entry]));
  const mappingByStableId = new Map(
    (mappingResult.mappings || []).filter((entry) => entry.stableId).map((entry) => [entry.stableId, entry]),
  );
  return {
    generatedAt: new Date().toISOString(),
    pageSlug: context?.pageSlug || mappingResult.pageSlug,
    items: inventory.map((control) => {
      const mapping = mappingByStableId.get(control.stableId) || mappingById.get(control.id);
      return {
        id: control.id,
        stableId: control.stableId,
        kind: control.kind,
        tag: control.tag,
        status: "pending",
        candidate: mapping?.candidate?.name || null,
        fallback: mapping?.fallback || null,
        notes: "",
      };
    }),
  };
}

function main() {
  try {
    const args = parseArgs(process.argv.slice(2));
    if (!args["project-root"]) {
      console.error(
        "Usage: node prepare-implementation.js --project-root <root> [--page-slug <slug>] [--target-file <path>] [--dry-run]",
      );
      process.exit(1);
    }

    const projectRoot = path.resolve(args["project-root"]);
    const latest = loadLatestRosey(projectRoot, args["page-slug"] || null);
    const pageSlug = latest.pageSlug;
    const scriptsDir = __dirname;
    const pageRoot = pageDir(projectRoot, pageSlug);

    const copyArgs = [
      "--project-root",
      projectRoot,
      "--page-slug",
      pageSlug,
      ...(args["dry-run"] ? ["--dry-run"] : []),
    ];
    const assetResult = runJson(path.join(scriptsDir, "copy-assets.js"), copyArgs);

    const mappingArgs = [
      "--project-root",
      projectRoot,
      "--page-slug",
      pageSlug,
      ...(args["target-file"] ? ["--target-file", args["target-file"]] : []),
    ];
    run(path.join(scriptsDir, "component-mapping.js"), mappingArgs);
    const componentMappingPath = path.join(pageRoot, "component-mapping.json");
    const mappingResult = JSON.parse(fs.readFileSync(componentMappingPath, "utf8"));
    const context = readJsonIfExists(latest.contextPathAbs);

    const checklist = buildImplementationChecklist(context, mappingResult);
    const checklistPath = path.join(pageRoot, "implementation-checklist.json");
    if (!args["dry-run"]) {
      fs.mkdirSync(pageRoot, { recursive: true });
      fs.writeFileSync(checklistPath, `${JSON.stringify(checklist, null, 2)}\n`);
    }

    process.stdout.write(
      `${JSON.stringify(
        {
          pageSlug,
          contextPath: path.relative(projectRoot, latest.contextPathAbs),
          assetMapPath: assetResult.assetMapPath,
          componentMappingPath: path.relative(projectRoot, componentMappingPath),
          implementationChecklistPath: path.relative(projectRoot, checklistPath),
          copiedAssets: assetResult.copied?.length || 0,
          skippedAssets: assetResult.skipped || [],
          controlInventoryCount: checklist.items.length,
          mappings: mappingResult.mappings?.length || 0,
          dryRun: Boolean(args["dry-run"]),
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
