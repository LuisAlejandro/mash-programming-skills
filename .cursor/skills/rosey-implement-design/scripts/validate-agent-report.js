#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const Ajv = require("ajv");
const addFormats = require("ajv-formats");

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

function loadSchema(schemaName) {
  const schemaPath = path.join(__dirname, "../../../agents", schemaName);
  const schema = JSON.parse(fs.readFileSync(schemaPath, "utf8"));
  delete schema.$schema;
  return schema;
}

function compileValidator(schemaName) {
  const ajv = new Ajv({ allErrors: true, strict: false });
  addFormats(ajv);
  const schema = loadSchema(schemaName);
  return ajv.compile(schema);
}

function readJson(filePath) {
  if (!fs.existsSync(filePath)) throw new Error(`Missing report: ${filePath}`);
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function validate(validateFn, data, label) {
  if (!validateFn(data)) {
    const details = (validateFn.errors || []).map((e) => `${e.instancePath} ${e.message}`).join("; ");
    throw new Error(`${label} failed schema validation: ${details}`);
  }
}

function main() {
  try {
    const args = parseArgs(process.argv.slice(2));
    if (!args.type || !args.report) {
      console.error(
        "Usage: node validate-agent-report.js --type reviewer|sync|iterator --report <path.json>",
      );
      process.exit(1);
    }

    const reportPath = path.resolve(args.report);
    const data = readJson(reportPath);
    const schemaByType = {
      reviewer: "rosey-reviewer-report.schema.json",
      sync: "rosey-sync-report.schema.json",
      iterator: "rosey-iterator-report.schema.json",
    };
    const schemaName = schemaByType[args.type];
    if (!schemaName) throw new Error(`Unknown report type: ${args.type}`);

    validate(compileValidator(schemaName), data, args.type);
    process.stdout.write(`${args.type} report validation passed: ${reportPath}\n`);
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}

if (require.main === module) main();
