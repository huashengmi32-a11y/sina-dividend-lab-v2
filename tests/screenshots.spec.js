// @ts-check
const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const SHOT_DIR = path.join(__dirname, "..", "docs", "screenshots");

async function openPage(page) {
  // 关闭动效，保证截图稳定、可复现
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/site/index.html");
  await page.waitForFunction(() => document.documentElement.dataset.ready === "true");
  await page.evaluate(async () => { await document.fonts.ready; });
  await warmUp(page);
}

/** 先滚到底再回到顶部，确保懒加载图片全部加载完成。 */
async function warmUp(page) {
  await page.evaluate(async () => {
    const step = Math.max(320, window.innerHeight);
    for (let y = 0; y < document.body.scrollHeight; y += step) {
      window.scrollTo(0, y);
      await new Promise((resolve) => setTimeout(resolve, 40));
    }
    window.scrollTo(0, 0);
    await new Promise((resolve) => setTimeout(resolve, 150));
  });
  await page.waitForLoadState("networkidle");
}

async function captureSection(page, selector, fileName) {
  await page.evaluate((target) => {
    document.querySelector(target).scrollIntoView({ block: "start", behavior: "instant" });
  }, selector);
  await page.waitForTimeout(320);
  const target = path.join(SHOT_DIR, fileName);
  await page.screenshot({ path: target });
  expect(fs.existsSync(target)).toBeTruthy();
}

test.describe("截图留档", () => {
  test("桌面端分区截图", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "桌面截图仅在桌面项目执行");
    fs.mkdirSync(SHOT_DIR, { recursive: true });
    await openPage(page);

    const first = path.join(SHOT_DIR, "desktop-01-hero.png");
    await page.screenshot({ path: first });
    expect(fs.existsSync(first)).toBeTruthy();

    await captureSection(page, "#process", "desktop-02-pipeline.png");
    await captureSection(page, "#source", "desktop-03-source.png");
    await captureSection(page, "#dataset", "desktop-04-dataset.png");
    await captureSection(page, "#quality", "desktop-05-quality.png");
    await captureSection(page, "#charts", "desktop-06-charts.png");
    await captureSection(page, "#tests", "desktop-07-tests.png");
  });

  test("移动端截图与整页长图", async ({ page }, testInfo) => {
    test.skip(!testInfo.project.name.includes("mobile"), "移动截图仅在移动项目执行");
    fs.mkdirSync(SHOT_DIR, { recursive: true });
    await openPage(page);

    const hero = path.join(SHOT_DIR, "mobile-01-hero.png");
    await page.screenshot({ path: hero });
    expect(fs.existsSync(hero)).toBeTruthy();

    await captureSection(page, "#dataset", "mobile-02-tables.png");

    const full = path.join(SHOT_DIR, "mobile-03-full.png");
    await page.screenshot({ path: full, fullPage: true });
    expect(fs.existsSync(full)).toBeTruthy();
  });
});
