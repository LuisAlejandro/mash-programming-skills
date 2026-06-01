#!/usr/bin/env node

const fs = require("fs");
const http = require("http");
const path = require("path");
const { spawn } = require("child_process");

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

function contentType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  return {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
  }[ext] || "application/octet-stream";
}

function safeResolve(root, requestPath) {
  const cleaned = decodeURIComponent(requestPath.split("?")[0]).replace(/^\/+/, "");
  const target = cleaned === "" ? root : path.resolve(root, cleaned);
  const relative = path.relative(root, target);
  if (relative.startsWith("..") || path.isAbsolute(relative)) return null;
  return target;
}

function startServer(htmlPath, assetRoot, port) {
  const htmlRoot = path.dirname(htmlPath);
  const htmlFile = path.basename(htmlPath);
  const server = http.createServer((request, response) => {
    const requested = request.url === "/" ? htmlFile : request.url;
    const htmlTarget = safeResolve(htmlRoot, requested);
    const assetTarget = assetRoot === htmlRoot ? null : safeResolve(assetRoot, requested);
    const target = [htmlTarget, assetTarget].find(
      (candidate) => candidate && fs.existsSync(candidate) && fs.statSync(candidate).isFile(),
    );
    if (!target) {
      response.writeHead(404);
      response.end("Not found");
      return;
    }
    response.writeHead(200, { "Content-Type": contentType(target) });
    fs.createReadStream(target).pipe(response);
  });

  return new Promise((resolve, reject) => {
    server.on("error", reject);
    server.listen(port, "127.0.0.1", () => {
      const address = server.address();
      resolve({ server, url: `http://127.0.0.1:${address.port}/` });
    });
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.html) {
    console.error(
      "Usage: node serve-artifact.js --html <path> [--assets-dir <dir>] [--port <port>] [--background] [--pid-file <path>]",
    );
    process.exit(1);
  }

  const htmlPath = path.resolve(args.html);
  if (!fs.existsSync(htmlPath) || !fs.statSync(htmlPath).isFile()) {
    console.error(`HTML artifact not found: ${htmlPath}`);
    process.exit(1);
  }

  const assetRoot = args["assets-dir"] ? path.resolve(args["assets-dir"]) : path.dirname(htmlPath);
  const port = Number(args.port || 0);

  if (args.background) {
    const stateFile = path.resolve(
      args["state-file"] || path.join(path.dirname(htmlPath), ".baseline-server.json"),
    );
    if (fs.existsSync(stateFile)) fs.unlinkSync(stateFile);

    const childArgs = [
      __filename,
      "--html",
      htmlPath,
      "--port",
      String(port || 0),
      "--state-file",
      stateFile,
      ...(args["assets-dir"] ? ["--assets-dir", assetRoot] : []),
    ];
    const child = spawn(process.execPath, childArgs, {
      detached: true,
      stdio: "ignore",
    });
    child.unref();

    const deadline = Date.now() + 8000;
    let state = null;
    while (Date.now() < deadline) {
      if (fs.existsSync(stateFile)) {
        try {
          state = JSON.parse(fs.readFileSync(stateFile, "utf8"));
          if (state.baselineUrl) break;
        } catch {
          // retry while server starts
        }
      }
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    if (!state?.baselineUrl) {
      console.error("Timed out waiting for baseline server to start.");
      process.exit(1);
    }

    if (args["pid-file"]) {
      fs.mkdirSync(path.dirname(path.resolve(args["pid-file"])), { recursive: true });
      fs.writeFileSync(path.resolve(args["pid-file"]), `${state.pid}\n`);
    }

    process.stdout.write(`OD_ARTIFACT_URL=${state.baselineUrl}\n`);
    process.stdout.write(`OD_ARTIFACT_PID=${state.pid}\n`);
    process.stdout.write(`OD_ARTIFACT_STATE_FILE=${stateFile}\n`);
    return;
  }

  const { server, url } = await startServer(htmlPath, assetRoot, port);
  process.stdout.write(`OD_ARTIFACT_URL=${url}\n`);
  process.stdout.write(`OD_ARTIFACT_PID=${process.pid}\n`);

  if (args["pid-file"]) {
    fs.mkdirSync(path.dirname(path.resolve(args["pid-file"])), { recursive: true });
    fs.writeFileSync(path.resolve(args["pid-file"]), `${process.pid}\n`);
  }

  if (args["state-file"]) {
    fs.mkdirSync(path.dirname(path.resolve(args["state-file"])), { recursive: true });
    fs.writeFileSync(
      path.resolve(args["state-file"]),
      `${JSON.stringify({ pid: process.pid, baselineUrl: url, htmlPath, assetsDir: assetRoot }, null, 2)}\n`,
    );
  }

  const shutdown = () => {
    server.close(() => process.exit(0));
  };
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error.message);
    process.exit(1);
  });
}
