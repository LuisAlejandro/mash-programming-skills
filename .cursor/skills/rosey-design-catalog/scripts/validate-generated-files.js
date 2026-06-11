#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const Ajv = require("ajv");
const addFormats = require("ajv-formats");
const {
  fileChecksum,
  readJsonIfExists,
  latestPath,
  pageDir,
  componentCatalogPath,
  designSystemManifestPath,
} = require("../../rosey-implement-design/scripts/lib/rosey-paths");

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

function loadSchema(name) {
  const schemaPath = path.join(__dirname, "..", "templates", `${name}.schema.json`);
  return JSON.parse(fs.readFileSync(schemaPath, "utf8"));
}

function compileValidator() {
  const ajv = new Ajv({ allErrors: true, strict: false, validateSchema: false });
  addFormats(ajv);
  const templatesDir = path.join(__dirname, "..", "templates");
  for (const file of fs.readdirSync(templatesDir)) {
    if (!file.endsWith(".schema.json")) continue;
    const schema = JSON.parse(fs.readFileSync(path.join(templatesDir, file), "utf8"));
    delete schema.$schema;
    ajv.addSchema(schema);
  }
  return ajv;
}

function validateSchema(ajv, schemaId, data, label) {
  const validate = ajv.getSchema(schemaId);
  if (!validate) throw new Error(`Schema not registered: ${schemaId}`);
  if (!validate(data)) {
    const details = (validate.errors || []).map((e) => `${e.instancePath} ${e.message}`).join("; ");
    throw new Error(`${label} failed schema validation: ${details}`);
  }
}

function resolvePageEntry(latest, pageSlug) {
  if (latest.pages?.[pageSlug]) return latest.pages[pageSlug];
  if (latest.pageSlug === pageSlug || !latest.pages) return latest;
  throw new Error(`Page slug not in latest.json: ${pageSlug}`);
}

function main() {
  try {
    const args = parseArgs(process.argv.slice(2));
    const root = path.resolve(args["project-root"] || process.cwd());
    const latest = readJson(latestPath(root));
    const pageSlug = args["page-slug"] || latest.activePageSlug || latest.pageSlug || "opendesign-page";
    const pageEntry = resolvePageEntry(latest, pageSlug);
    const pageRoot = pageDir(root, pageSlug);

    const artifact = readJson(path.join(pageRoot, "artifact.json"));
    const catalog = readJson(componentCatalogPath(root));
    const context = readJson(path.join(pageRoot, "design-context.json"));
    const baseRules = readText(path.join(root, ".cursor", "rules", "rosey-design-system.mdc"));
    const ajv = compileValidator();

    validateSchema(ajv, "rosey-artifact.schema.json", artifact, "artifact");
    validateSchema(ajv, "rosey-component-catalog.schema.json", catalog, "catalog");
    validateSchema(ajv, "rosey-design-context.schema.json", context, "design-context");

    assert(artifact.source === "opendesign-export", "artifact.source must be opendesign-export");
    assert(fs.existsSync(artifact.htmlPath), `artifact.htmlPath does not exist: ${artifact.htmlPath}`);
    assert(baseRules.includes("Rosey Design System"), "base rules missing Rosey heading");
    assert(context.pageSlug === pageSlug, `context.pageSlug must match ${pageSlug}`);
    assert(context.htmlChecksum, "context.htmlChecksum is required");
    assert(fileChecksum(artifact.htmlPath) === context.htmlChecksum, "HTML checksum does not match design-context");

    if (context.designSystem) {
      const designPath = path.resolve(root, context.designSystem.path);
      assert(fs.existsSync(designPath), `DESIGN.md does not exist: ${designPath}`);
      if (context.designSystem.checksum) {
        assert(fileChecksum(designPath) === context.designSystem.checksum, "DESIGN.md checksum does not match context");
      }
    } else if (!args["allow-missing-design"]) {
      throw new Error("context.designSystem is required unless --allow-missing-design is set");
    }

    const dsManifest = readJsonIfExists(designSystemManifestPath(root));
    if (dsManifest?.designChecksum && context.designSystem?.checksum) {
      const manifestPath = path.resolve(root, dsManifest.designPath || "rosey/design-system/DESIGN.md");
      if (fs.existsSync(manifestPath)) {
        const current = fileChecksum(manifestPath);
        if (current !== dsManifest.designChecksum) {
          console.warn("Warning: design-system.json checksum differs from copied DESIGN.md on disk.");
        }
      }
    }

    if (args["expect-component"]) {
      assert(Boolean(catalog.components[args["expect-component"]]), `Expected component missing: ${args["expect-component"]}`);
    }

    if (args["expect-control-kind"]) {
      assert(
        context.serialized.controlInventory.some((item) => item.kind === args["expect-control-kind"]),
        `Expected control kind missing: ${args["expect-control-kind"]}`,
      );
    }

    assert(latest.pages?.[pageSlug] || pageEntry.contextPath, "latest.json missing page entry");
    assert(
      pageEntry.catalogPath === context.componentCatalogPath,
      "latest page catalogPath must match design-context componentCatalogPath",
    );
    process.stdout.write("Rosey generated files validation passed\n");
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}

if (require.main === module) main();
