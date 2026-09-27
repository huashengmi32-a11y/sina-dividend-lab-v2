// @ts-check
const { test, expect } = require("@playwright/test");

const VIEWPORTS = [
  { name: "手机 375", width: 375, height: 812 },
  { name: "平板 768", width: 768, height: 1024 },
  { name: "笔记本 1024", width: 1024, height: 768 },
  { name: "桌面 1440", width: 1440, height: 900 }
];

async function openPage(page) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/site/index.html");
  await page.waitForFunction(() => document.documentElement.dataset.ready === "true");
}

VIEWPORTS.forEach((viewport) => {
  test.describe("响应式布局 · " + viewport.name, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("页面没有横向滚动条", async ({ page }) => {
      await openPage(page);
      const overflow = await page.evaluate(() => {
        const root = document.documentElement;
        return {
          rootScroll: root.scrollWidth - root.clientWidth,
          bodyScroll: document.body.scrollWidth - document.body.clientWidth
        };
      });
      expect(overflow.rootScroll).toBeLessThanOrEqual(1);
      expect(overflow.bodyScroll).toBeLessThanOrEqual(1);
    });

    test("卡片与说明文字不溢出容器", async ({ page }) => {
      await openPage(page);
      const offenders = await page.evaluate(() => {
        const selectors = [".metric-card", ".card", ".kv-list dd", ".pipeline-grid li", ".rule-card", ".gallery figure"];
        const result = [];
        selectors.forEach((selector) => {
          document.querySelectorAll(selector).forEach((node) => {
            if (node.scrollWidth - node.clientWidth > 1) {
              result.push(selector + " :: " + node.textContent.trim().slice(0, 40));
            }
          });
        });
        return result;
      });
      expect(offenders).toEqual([]);
    });

    test("触控目标尺寸满足 44 像素基准", async ({ page }) => {
      test.skip(viewport.width > 768, "触控基准只在移动与平板视口检查");
      await openPage(page);
      const small = await page.evaluate(() => {
        const selectors = [".site-nav a", ".tabs button", ".pager .btn", ".download-row .chip", ".search-field"];
        const result = [];
        selectors.forEach((selector) => {
          document.querySelectorAll(selector).forEach((node) => {
            const rect = node.getBoundingClientRect();
            if (rect.height > 0 && rect.height < 44) {
              result.push(selector + " 高度 " + rect.height.toFixed(1) + "px");
            }
          });
        });
        return result;
      });
      expect(small).toEqual([]);
    });

    test("锚点导航不会被吸顶页头遮挡", async ({ page }) => {
      await openPage(page);
      const headerHeight = await page.evaluate(() => {
        return document.querySelector(".site-header").getBoundingClientRect().height;
      });
      await page.locator('.site-nav a[href="#dataset"]').click();
      await page.waitForTimeout(600);
      const top = await page.evaluate(() => {
        return document.querySelector("#dataset").getBoundingClientRect().top;
      });
      expect(top).toBeGreaterThanOrEqual(headerHeight - 8);
    });

    test("正文与次要文字对比度满足 WCAG AA", async ({ page }) => {
      await openPage(page);
      const samples = await page.evaluate(() => {
        function parseColor(value) {
          const match = value.match(/rgba?\(([^)]+)\)/);
          if (!match) { return null; }
          const parts = match[1].split(/[,\s/]+/).filter(Boolean).map(Number);
          return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
        }
        function channel(value) {
          const v = value / 255;
          return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
        }
        function luminance(color) {
          return 0.2126 * channel(color.r) + 0.7152 * channel(color.g) + 0.0722 * channel(color.b);
        }
        function ratio(a, b) {
          const l1 = luminance(a), l2 = luminance(b);
          const hi = Math.max(l1, l2), lo = Math.min(l1, l2);
          return (hi + 0.05) / (lo + 0.05);
        }
        function effectiveBackground(node) {
          let current = node;
          while (current) {
            const bg = parseColor(getComputedStyle(current).backgroundColor);
            if (bg && bg.a >= 0.99) { return bg; }
            current = current.parentElement;
          }
          return { r: 255, g: 255, b: 255, a: 1 };
        }
        const targets = [
          [document.querySelector(".lead"), "概述段落"],
          [document.querySelector(".metric-card dt"), "指标标签"],
          [document.querySelector(".metric-card dd"), "指标数值"],
          [document.querySelector(".data-table tbody td"), "表格正文"],
          [document.querySelector(".rule-card p"), "规则说明"],
          [document.querySelector(".site-footer p"), "页脚文字"]
        ];
        return targets.filter((item) => item[0]).map((item) => {
          const style = getComputedStyle(item[0]);
          return {
            label: item[1],
            ratio: ratio(parseColor(style.color), effectiveBackground(item[0]))
          };
        });
      });
      samples.forEach((sample) => {
        expect(sample.ratio, sample.label + " 对比度").toBeGreaterThanOrEqual(4.5);
      });
    });
  });
});
