async function gotoReady(page, url, options = {}) {
  const waitUntil = options.waitUntil || "domcontentloaded";
  const timeout = options.timeout ?? 45000;
  const settleMs = options.settleMs ?? 500;

  await page.goto(url, { waitUntil, timeout });

  if (options.waitSelector) {
    await page.waitForSelector(options.waitSelector, { timeout });
  }

  if (settleMs > 0) {
    await page.waitForTimeout(settleMs);
  }
}

module.exports = { gotoReady };
