const fs = require("fs");
const path = require("path");

function loadPng(filePath) {
  const { PNG } = require("pngjs");
  return PNG.sync.read(fs.readFileSync(filePath));
}

function compareScreenshotPair(baselinePath, targetPath, diffPath, options = {}) {
  const threshold = options.threshold ?? 0.1;
  const mismatchBlockRatio = options.mismatchBlockRatio ?? 0.01;
  const mismatchMajorRatio = options.mismatchMajorRatio ?? 0.05;

  let pixelmatch;
  try {
    pixelmatch = require("pixelmatch");
  } catch {
    return {
      available: false,
      note: "pixelmatch not installed",
      findings: [],
    };
  }

  const baseline = loadPng(baselinePath);
  const target = loadPng(targetPath);

  if (baseline.width !== target.width || baseline.height !== target.height) {
    return {
      available: true,
      width: baseline.width,
      height: baseline.height,
      targetWidth: target.width,
      targetHeight: target.height,
      mismatchRatio: 1,
      findings: [
        {
          id: "pixel-dimension-mismatch",
          severity: "blocking",
          element: "screenshot",
          expected: `${baseline.width}x${baseline.height}`,
          observed: `${target.width}x${target.height}`,
          recommendation: "Fix layout overflow or viewport sizing so screenshots share dimensions.",
        },
      ],
    };
  }

  const { PNG } = require("pngjs");
  const { width, height } = baseline;
  const diff = new PNG({ width, height });
  const numDiffPixels = pixelmatch(baseline.data, target.data, diff.data, width, height, { threshold });

  if (diffPath) {
    fs.mkdirSync(path.dirname(diffPath), { recursive: true });
    fs.writeFileSync(diffPath, PNG.sync.write(diff));
  }

  const mismatchRatio = numDiffPixels / (width * height);
  const findings = [];
  if (mismatchRatio > mismatchBlockRatio) {
    findings.push({
      id: "pixel-visual-diff",
      severity: mismatchRatio > mismatchMajorRatio ? "blocking" : "major",
      element: "full-page screenshot",
      expected: `<= ${(mismatchBlockRatio * 100).toFixed(2)}% pixel drift`,
      observed: `${(mismatchRatio * 100).toFixed(2)}% pixel drift (${numDiffPixels} px)`,
      recommendation: "Adjust spacing, typography, colors, or layout until visual parity is within threshold.",
    });
  }

  return {
    available: true,
    width,
    height,
    numDiffPixels,
    mismatchRatio,
    diffPath: diffPath || null,
    findings,
  };
}

module.exports = { compareScreenshotPair };
