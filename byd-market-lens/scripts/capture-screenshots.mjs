import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium } from "playwright";

const root = resolve(import.meta.dirname, "..");
const screenshotsDirectory = resolve(root, "screenshots");
const baseUrl = process.env.BASE_URL ?? "http://127.0.0.1:4173";
const executablePath =
  process.env.CHROME_PATH ??
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

await mkdir(screenshotsDirectory, { recursive: true });

const browser = await chromium.launch({
  executablePath,
  headless: true
});

const consoleErrors = [];
const pageErrors = [];
const checks = {};

try {
  const mobileContext = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 1,
    isMobile: true,
    hasTouch: true
  });
  const mobilePage = await mobileContext.newPage();
  mobilePage.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  mobilePage.on("pageerror", (error) => pageErrors.push(error.message));

  await mobilePage.goto(baseUrl, { waitUntil: "networkidle" });
  await mobilePage.waitForSelector(".stock-chart canvas");
  await mobilePage.evaluate(() => document.fonts.ready);
  await mobilePage.waitForTimeout(450);

  checks.mobileOverflow = await mobilePage.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth
  );
  checks.chartCanvasCount = await mobilePage.locator(".stock-chart canvas").count();
  checks.tdesignControls = await mobilePage.evaluate(() => ({
    button: document.querySelectorAll(".t-button").length,
    segmented: document.querySelectorAll(".t-segmented").length,
    switch: document.querySelectorAll(".t-switch").length,
    tag: document.querySelectorAll(".t-tag").length,
    cell: document.querySelectorAll(".t-cell").length
  }));
  checks.heading = await mobilePage.locator("h1").innerText();
  checks.periodReturn = await mobilePage.locator(".hero .t-tag").innerText();
  checks.chartAriaLabel = await mobilePage
    .locator(".stock-chart")
    .getAttribute("aria-label");
  checks.clippedTextElements = await mobilePage.evaluate(() =>
    [...document.querySelectorAll(".t-button, .t-segmented__item, .metric-value")]
      .filter((element) => element.scrollWidth > element.clientWidth + 1)
      .map((element) => element.textContent.trim())
  );

  await mobilePage.screenshot({
    path: resolve(screenshotsDirectory, "byd-mobile-overview.png"),
    fullPage: false
  });

  await mobilePage.locator(".chart-panel").scrollIntoViewIfNeeded();
  await mobilePage.waitForTimeout(250);
  await mobilePage.screenshot({
    path: resolve(screenshotsDirectory, "byd-mobile-chart.png"),
    fullPage: false
  });

  await mobilePage.getByText("近3月", { exact: true }).click();
  await mobilePage.getByText("收盘", { exact: true }).click();
  await mobilePage.waitForTimeout(300);
  await mobilePage.screenshot({
    path: resolve(screenshotsDirectory, "byd-mobile-interaction.png"),
    fullPage: false
  });

  await mobilePage.locator('button[aria-label="查看数据与计算口径"]').click();
  await mobilePage.getByText("数据与计算口径", { exact: true }).waitFor();
  await mobilePage.waitForTimeout(350);
  checks.methodDialogVisible = await mobilePage
    .getByText("最大回撤基于每日收盘价的滚动历史高点计算", {
      exact: false
    })
    .isVisible();
  await mobilePage.screenshot({
    path: resolve(screenshotsDirectory, "byd-mobile-method.png"),
    fullPage: false
  });
  await mobilePage.getByText("关闭", { exact: true }).click();
  await mobilePage.waitForTimeout(350);

  await mobilePage.reload({ waitUntil: "networkidle" });
  await mobilePage.waitForSelector(".stock-chart canvas");
  await mobilePage.evaluate(() => document.fonts.ready);
  await mobilePage.waitForTimeout(300);
  await mobilePage.screenshot({
    path: resolve(screenshotsDirectory, "byd-mobile-full.png"),
    fullPage: true
  });

  await mobileContext.close();

  const desktopContext = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    deviceScaleFactor: 1
  });
  const desktopPage = await desktopContext.newPage();
  desktopPage.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  desktopPage.on("pageerror", (error) => pageErrors.push(error.message));
  await desktopPage.goto(baseUrl, { waitUntil: "networkidle" });
  await desktopPage.waitForSelector(".stock-chart canvas");
  await desktopPage.evaluate(() => document.fonts.ready);
  await desktopPage.waitForTimeout(350);
  checks.desktopOverflow = await desktopPage.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth
  );
  await desktopPage.screenshot({
    path: resolve(screenshotsDirectory, "byd-desktop.png"),
    fullPage: false
  });

  checks.responsive = {};
  for (const width of [320, 375, 768, 1024, 1440]) {
    await desktopPage.setViewportSize({ width, height: 900 });
    await desktopPage.waitForTimeout(160);
    checks.responsive[width] = await desktopPage.evaluate(() => ({
      overflow: document.documentElement.scrollWidth - window.innerWidth,
      chartWidth: Math.round(
        document.querySelector(".stock-chart").getBoundingClientRect().width
      )
    }));
  }
  await desktopContext.close();

  const report = {
    generatedAt: new Date().toISOString(),
    baseUrl,
    checks,
    consoleErrors,
    pageErrors,
    screenshots: [
      "screenshots/byd-mobile-overview.png",
      "screenshots/byd-mobile-chart.png",
      "screenshots/byd-mobile-interaction.png",
      "screenshots/byd-mobile-method.png",
      "screenshots/byd-mobile-full.png",
      "screenshots/byd-desktop.png"
    ]
  };
  await writeFile(
    resolve(root, "deliverables", "browser-verification.json"),
    JSON.stringify(report, null, 2) + "\n",
    "utf8"
  );

  if (consoleErrors.length || pageErrors.length) {
    throw new Error(
      `Browser errors detected. console=${consoleErrors.length}, page=${pageErrors.length}`
    );
  }
  const responsiveOverflow = Object.values(checks.responsive).some(
    (entry) => entry.overflow > 0
  );
  if (checks.mobileOverflow > 0 || checks.desktopOverflow > 0 || responsiveOverflow) {
    throw new Error(
      `Horizontal overflow detected. mobile=${checks.mobileOverflow}, desktop=${checks.desktopOverflow}`
    );
  }
  if (checks.clippedTextElements.length) {
    throw new Error(
      `Clipped interactive text: ${checks.clippedTextElements.join(", ")}`
    );
  }

  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}
