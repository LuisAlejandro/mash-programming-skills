const DEFAULT_VIEWPORTS = ["1440x900", "1024x768", "390x844"];
const BLOCKING = new Set(["blocking", "major"]);

function loadParityReports(reviewDir, viewports = DEFAULT_VIEWPORTS) {
  const fs = require("fs");
  const path = require("path");
  const reports = [];
  for (const viewport of viewports) {
    const filePath = path.join(reviewDir, `parity-${viewport}.json`);
    if (!fs.existsSync(filePath)) {
      reports.push({ viewport, missing: true, findings: [] });
      continue;
    }
    const data = JSON.parse(fs.readFileSync(filePath, "utf8"));
    reports.push({ viewport, missing: false, ...data });
  }
  return reports;
}

function mergeParityFindings(reports) {
  const merged = [];
  const seen = new Set();
  for (const report of reports) {
    if (report.missing) {
      merged.push({
        id: `parity-missing-${report.viewport}`,
        severity: "blocking",
        element: report.viewport,
        expected: "parity report",
        observed: "missing",
        recommendation: `Run compare-parity for viewport ${report.viewport}.`,
        viewport: report.viewport,
      });
      continue;
    }
    for (const finding of report.findings || []) {
      const key = `${finding.id}|${report.viewport}`;
      if (seen.has(key)) continue;
      seen.add(key);
      merged.push({ ...finding, viewport: report.viewport });
    }
  }
  return merged;
}

function assessAlignmentFromFindings(findings, options = {}) {
  const allowedMinor = options.allowMinor ?? true;
  const blocking = findings.filter((f) => f.severity === "blocking");
  const major = findings.filter((f) => f.severity === "major");
  const minor = findings.filter((f) => f.severity === "minor");

  if (blocking.length > 0) {
    return { aligned: false, reason: "blocking-findings", blocking, major, minor };
  }
  if (major.length > 0) {
    return { aligned: false, reason: "major-findings", blocking, major, minor };
  }
  if (!allowedMinor && minor.length > 0) {
    return { aligned: false, reason: "minor-findings", blocking, major, minor };
  }
  return { aligned: true, reason: "aligned", blocking, major, minor };
}

function assessAlignmentFromReports(reviewDir, viewports = DEFAULT_VIEWPORTS) {
  const reports = loadParityReports(reviewDir, viewports);
  const findings = mergeParityFindings(reports);
  return { reports, findings, ...assessAlignmentFromFindings(findings) };
}

function assessReviewerAlignment(reviewerReport) {
  const findings = reviewerReport?.findings || [];
  return assessAlignmentFromFindings(findings);
}

function hasBlockingOrMajor(findings) {
  return findings.some((f) => BLOCKING.has(f.severity));
}

module.exports = {
  DEFAULT_VIEWPORTS,
  loadParityReports,
  mergeParityFindings,
  assessAlignmentFromFindings,
  assessAlignmentFromReports,
  assessReviewerAlignment,
  hasBlockingOrMajor,
};
