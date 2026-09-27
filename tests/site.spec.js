// @ts-check
const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..");
const report = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "quality_report.json"), "utf8"));
const shotsDir = path.join(ROOT, "docs", "screenshots");
const issues = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "issues.json"), "utf8"));
const shotFiles = fs.existsSync(shotsDir)
  ? fs.readdirSync(shotsDir).filter((name) => name.endsWith(".png"))
  : [];

/** 等待页面脚本渲染完成（app.js 会设置 data-ready）。 */
async function openPage(page) {
  await page.goto("/site/index.html");
  await page.waitForFunction(() => document.documentElement.dataset.ready === "true");
}

test.describe("页面功能", () => {
  test.beforeEach(async ({ page }) => {
    await openPage(page);
  });

  test("标题与首屏指标与数据管线一致", async ({ page }) => {
    await expect(page).toHaveTitle(/新浪财经历史分红数据获取与预处理/);
    await expect(page.locator("h1")).toHaveText("从新浪财经网页到可分析数据集");

    const cards = page.locator("#hero-metrics .metric-card");
    await expect(cards).toHaveCount(6);
    await expect(cards.filter({ hasText: "目标股票" })).toContainText(String(report.counts.stocks));
    await expect(cards.filter({ hasText: "分红记录" })).toContainText(String(report.counts.dividend_records));
    await expect(cards.filter({ hasText: "配股记录" })).toContainText(String(report.counts.rights_records));
  });

  test("五步实现过程完整渲染且带证据文件", async ({ page }) => {
    const steps = page.locator("#pipeline-list > li");
    await expect(steps).toHaveCount(5);
    await expect(steps.first()).toContainText("需求确认");
    await expect(steps.nth(1)).toContainText("原始数据抓取");
    await expect(page.locator("#pipeline-list .evidence code").first()).toContainText("docs/");
  });

  test("抓取清单展示页面数与请求抽样", async ({ page }) => {
    await expect(page.locator("#fetch-stats")).toContainText(String(report.counts.detail_pages));
    await expect(page.locator("#fetch-table tbody tr")).toHaveCount(8);
    await expect(page.locator("#fetch-table tbody tr").first()).toContainText("list_");
  });

  test("分红明细表默认展示第一页且总数正确", async ({ page }) => {
    await expect(page.locator("#dataset-table tbody tr")).toHaveCount(12);
    await expect(page.locator("#table-count")).toContainText(String(report.counts.dividend_records) + " 条记录");
    await expect(page.locator("#dataset-table thead th").first()).toHaveText("代码");
  });

  test("搜索可以过滤表格内容", async ({ page }) => {
    await page.fill("#table-search", "茅台");
    await expect
      .poll(async () => page.locator("#dataset-table tbody tr td:nth-child(2)").allTextContents())
      .not.toHaveLength(0);
    const names = await page.locator("#dataset-table tbody tr td:nth-child(2)").allTextContents();
    names.forEach((name) => expect(name).toContain("茅台"));
    await expect(page.locator("#table-count")).toContainText("当前表 31 条记录");
  });

  test("分页按钮切换页码并正确禁用", async ({ page }) => {
    await expect(page.locator('[data-page="prev"]')).toBeDisabled();
    await page.locator('[data-page="next"]').click();
    await expect(page.locator("#pager-info")).toHaveText(/第 2 \/ \d+ 页/);
    await expect(page.locator('[data-page="prev"]')).toBeEnabled();
  });

  test("标签页切换到年度汇总与股票汇总", async ({ page }) => {
    await page.locator("#tab-yearly").click();
    await expect(page.locator("#table-count")).toContainText(String(report.counts.yearly_rows) + " 条记录");
    await expect(page.locator("#dataset-table thead th").nth(2)).toHaveText("分红年度");

    await page.locator("#tab-stocks").click();
    await expect(page.locator("#dataset-table tbody tr")).toHaveCount(report.counts.stocks);
    await expect(page.locator("#dataset-table thead th").nth(2)).toHaveText("行业");
  });

  test("质量报告渲染十条规则与命中统计", async ({ page }) => {
    const cards = page.locator("#rule-grid .rule-card");
    await expect(cards).toHaveCount(report.checks.length);
    const passed = report.checks.filter((check) => check.passed).length;
    await expect(page.locator("#quality-summary")).toContainText("通过规则：" + passed);
    await expect(page.locator("#rule-grid")).toContainText("方案内容有效性");
  });

  test("问题清单行数与质量报告一致", async ({ page }) => {
    await expect(page.locator("#issue-table tbody tr")).toHaveCount(report.counts.issues);
    expect(issues.length).toBe(report.counts.issues);
    if (issues.length > 0) {
      await expect(page.locator("#issue-table tbody tr").first()).toContainText(issues[0].rule);
    }
  });

  test("三张图表渲染为带标题的 SVG", async ({ page }) => {
    await expect(page.locator("#chart-cash svg rect.bar")).toHaveCount(report.counts.stocks);
    await expect(page.locator("#chart-yearly svg")).toHaveCount(report.counts.stocks);
    await expect(page.locator("#chart-structure svg rect")).toHaveCount(report.counts.stocks * 3);
    await expect(page.locator("#chart-cash svg title")).toContainText("累计每股税前派息");
  });

  test("字段字典列出全部字段并给出覆盖率", async ({ page }) => {
    const dictionary = report.field_dictionary;
    const keys = Object.keys(dictionary);
    await expect(page.locator("#dictionary-table tbody tr")).toHaveCount(keys.length);
    await expect(page.locator("#dictionary-table tbody tr").first()).toContainText("%");
    await expect(page.locator("#dictionary-table")).toContainText("每股派息税前(元)");
  });

  test("测试结果与截图墙渲染", async ({ page }) => {
    const figures = page.locator("#shot-gallery figure");
    if (shotFiles.length > 0) {
      await expect(figures).toHaveCount(shotFiles.length);
      const firstImage = figures.first().locator("img");
      await expect(firstImage).toHaveAttribute("src", /assets\/screenshots\/.+\.png/);
      // 截图使用懒加载：滚动到可视区后再等待图片真正解码完成
      await firstImage.scrollIntoViewIfNeeded();
      await expect
        .poll(async () => firstImage.evaluate((img) => img.complete && img.naturalWidth > 0), { timeout: 10_000 })
        .toBe(true);
    } else {
      await expect(page.locator("#shot-gallery .hint")).toBeVisible();
    }
    await expect(page.locator("#test-hint")).toContainText("tests/report/index.html");
  });

  test("页面不发起任何外部网络请求", async ({ page }) => {
    const external = [];
    page.on("request", (request) => {
      const url = new URL(request.url());
      if (url.protocol === "data:") { return; }
      if (url.hostname !== "127.0.0.1" && url.hostname !== "localhost") { external.push(request.url()); }
    });
    await page.reload();
    await page.waitForLoadState("networkidle");
    expect(external).toEqual([]);
  });

  test("加载过程无控制台错误", async ({ page }) => {
    const errors = [];
    page.on("console", (message) => {
      if (message.type() === "error") { errors.push(message.text()); }
    });
    page.on("pageerror", (error) => errors.push(error.message));
    await page.reload();
    await page.waitForFunction(() => document.documentElement.dataset.ready === "true");
    expect(errors).toEqual([]);
  });
});
