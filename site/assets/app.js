/* ==========================================================================
   展示页交互脚本：读取内嵌数据 → 渲染指标 / 表格 / 图表 / 测试结果
   页面不发起任何网络请求，所有内容来自 assets/data.js
   ========================================================================== */
(function () {
  "use strict";

  var DATA = window.__DIVIDEND_LAB__;
  if (!DATA) {
    document.body.innerHTML = '<p style="padding:24px">数据文件缺失：请先运行 python scripts/preprocess.py 与 python scripts/build_site.py</p>';
    return;
  }

  /* ---------------------------------------------------------------- 工具 */
  function $(selector, root) { return (root || document).querySelector(selector); }

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (key) {
        var value = attrs[key];
        if (value === null || value === undefined) { return; }
        if (key === "class") { node.className = value; }
        else if (key === "text") { node.textContent = value; }
        else if (key === "html") { node.innerHTML = value; }
        else if (key.indexOf("on") === 0 && typeof value === "function") { node.addEventListener(key.slice(2), value); }
        else { node.setAttribute(key, value); }
      });
    }
    (children || []).forEach(function (child) {
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    });
    return node;
  }

  function clear(node) { while (node.firstChild) { node.removeChild(node.firstChild); } }

  var numberFormat = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 4 });
  var intFormat = new Intl.NumberFormat("zh-CN");

  function isMissing(value) {
    return value === null || value === undefined || (typeof value === "number" && isNaN(value));
  }

  function fmt(value, options) {
    var opts = options || {};
    if (isMissing(value)) { return "—"; }
    if (typeof value === "boolean") { return value ? "是" : "否"; }
    if (typeof value === "number") {
      return opts.digits === 0 ? intFormat.format(Math.round(value)) : numberFormat.format(value);
    }
    return String(value);
  }

  function fmtBytes(bytes) {
    if (isMissing(bytes)) { return "—"; }
    if (bytes < 1024) { return bytes + " B"; }
    if (bytes < 1024 * 1024) { return (bytes / 1024).toFixed(1) + " KB"; }
    return (bytes / 1024 / 1024).toFixed(2) + " MB";
  }

  function fmtDuration(ms) {
    if (isMissing(ms)) { return "—"; }
    if (ms < 1000) { return ms + " ms"; }
    if (ms < 60000) { return (ms / 1000).toFixed(1) + " s"; }
    return (ms / 60000).toFixed(1) + " min";
  }

  function metricCard(label, value, unit) {
    var dd = el("dd", { text: fmt(value) });
    if (unit) { dd.appendChild(el("small", { text: unit })); }
    return el("div", { class: "metric-card" }, [el("dt", { text: label }), dd]);
  }

  function kvRow(label, valueNode) {
    return el("div", {}, [el("dt", { text: label }), el("dd", {}, [valueNode])]);
  }

  function kvText(label, text) { return kvRow(label, document.createTextNode(text || "—")); }

  /* ---------------------------------------------------------------- 概览 */
  function renderMeta() {
    var meta = DATA.meta || {};
    var quality = DATA.quality || {};
    var counts = quality.counts || {};
    var manifest = DATA.manifest || {};
    var summary = manifest.summary || {};

    Array.prototype.forEach.call(document.querySelectorAll('[data-bind="sourceName"]'), function (node) {
      node.textContent = meta.source_name || "新浪财经";
    });
    var generated = (meta.generated_at || "").replace("T", " ").slice(0, 19);
    Array.prototype.forEach.call(document.querySelectorAll('[data-bind="generatedAt"]'), function (node) {
      node.textContent = generated || "—";
    });
    var fetchElapsed = $('[data-bind="fetchElapsed"]');
    if (fetchElapsed) { fetchElapsed.textContent = fmtDuration((manifest.elapsed_seconds || 0) * 1000); }

    var metrics = $("#hero-metrics");
    clear(metrics);
    metrics.appendChild(metricCard("目标股票", counts.stocks, "只"));
    metrics.appendChild(metricCard("分红记录", counts.dividend_records, "条"));
    metrics.appendChild(metricCard("配股记录", counts.rights_records, "条"));
    metrics.appendChild(metricCard("字段口径", Object.keys(quality.field_dictionary || {}).length, "个"));
    metrics.appendChild(metricCard("存档页面", summary.pages, "个"));
    metrics.appendChild(metricCard("质量规则", (quality.checks || []).length, "条"));
  }

  /* ---------------------------------------------------------------- 流程 */
  function renderPipeline() {
    var list = $("#pipeline-list");
    clear(list);
    (DATA.pipeline || []).forEach(function (step, index) {
      var evidence = el("div", { class: "evidence" }, (step.evidence || []).map(function (item) {
        return el("code", { text: item });
      }));
      list.appendChild(el("li", {}, [
        el("span", { class: "step-index", text: String(index + 1).padStart(2, "0") }),
        el("h3", { text: step.title }),
        el("p", { text: step.summary }),
        el("ul", {}, (step.points || []).map(function (point) { return el("li", { text: point }); })),
        evidence
      ]));
    });
  }

  /* ------------------------------------------------------------ 来源与抓取 */
  function renderSource() {
    var meta = DATA.meta || {};
    var manifest = DATA.manifest || {};
    var settings = manifest.settings || {};
    var info = $("#source-info");
    clear(info);

    var homeLink = el("a", { href: meta.source_home || "#", rel: "noreferrer noopener", target: "_blank", text: meta.source_name || "新浪财经" });
    info.appendChild(kvRow("数据源", homeLink));
    info.appendChild(kvText("列表页模板", "vISSUE_ShareBonus/stockid/{code}.phtml"));
    info.appendChild(kvText("明细页", "vISSUE_ShareBonusDetail.php?stockid=…&end_date=…"));
    info.appendChild(kvText("页面编码", "源站 GB2312 → 统一转存为 UTF-8"));
    info.appendChild(kvText("抓取参数", settings.delay_seconds + " 秒间隔 · 超时 " + settings.timeout_seconds + " 秒 · 最多重试 " + settings.retries + " 次"));
    info.appendChild(kvText("合规说明", meta.source_license));

    var stats = $("#fetch-stats");
    clear(stats);
    var summary = manifest.summary || {};
    stats.appendChild(kvText("存档页面", fmt(summary.pages || 0, { digits: 0 }) + " 个（列表页 5 + 明细页 " + fmt(summary.detail_pages || 0, { digits: 0 }) + "）"));
    stats.appendChild(kvText("联网请求 / 缓存命中", fmt(summary.network_requests || 0, { digits: 0 }) + " / " + fmt(summary.cache_hits || 0, { digits: 0 })));
    stats.appendChild(kvText("存档总字节", fmtBytes(summary.total_bytes)));
    stats.appendChild(kvText("抓取耗时", fmtDuration((manifest.elapsed_seconds || 0) * 1000)));
    stats.appendChild(kvText("开始时间", (manifest.started_at || "—").replace("T", " ").slice(0, 19)));
    stats.appendChild(kvText("留痕字段", "URL / 状态码 / 字节数 / SHA-256 / 耗时 / 缓存标记"));

    var table = $("#fetch-table");
    var head = $("thead", table);
    var body = $("tbody", table);
    clear(head); clear(body);
    head.appendChild(el("tr", {}, [
      el("th", { text: "#" }), el("th", { text: "文件" }), el("th", { text: "状态" }),
      el("th", { text: "字节" }), el("th", { text: "耗时" }), el("th", { text: "来源地址" })
    ]));
    (manifest.requests || []).slice(0, 8).forEach(function (row) {
      body.appendChild(el("tr", {}, [
        el("td", { class: "num", text: row.index }),
        el("td", { class: "nowrap", text: (row.file || "").replace("data/raw/", "") }),
        el("td", { text: row.status }),
        el("td", { class: "num", text: fmtBytes(row.bytes) }),
        el("td", { class: "num", text: row.elapsed_ms + " ms" }),
        el("td", { class: "ellipsis", text: row.url })
      ]));
    });
  }

  /* ---------------------------------------------------------------- 数据表 */
  var TABLES = {
    dividends: {
      label: "分红明细",
      rows: DATA.dividends || [],
      pageSize: 12,
      columns: [
        ["stock_code", "代码", "nowrap"], ["stock_name", "名称"],
        ["announce_date", "公告日期"], ["dividend_year", "分红年度"],
        ["allocation_type", "分配类型"],
        ["bonus_share_per10", "送股(股/10)", "num"],
        ["transfer_share_per10", "转增(股/10)", "num"],
        ["cash_per10_pretax", "派息(元/10股)", "num"],
        ["ex_dividend_date", "除权除息日"], ["record_date", "股权登记日"],
        ["status", "进度"]
      ],
      search: ["stock_code", "stock_name", "announce_date", "status", "allocation_type"]
    },
    yearly: {
      label: "年度汇总",
      rows: DATA.yearly || [],
      pageSize: 12,
      columns: [
        ["stock_code", "代码", "nowrap"], ["stock_name", "名称"],
        ["dividend_year", "分红年度"], ["records", "记录数", "num"],
        ["cash_records", "含现金记录数", "num"],
        ["cash_per_share_sum", "每股派息合计(元)", "num"],
        ["bonus_share_per10_sum", "送股合计(股/10)", "num"],
        ["transfer_share_per10_sum", "转增合计(股/10)", "num"]
      ],
      search: ["stock_code", "stock_name", "dividend_year"]
    },
    stocks: {
      label: "股票汇总",
      rows: DATA.stocks || [],
      pageSize: 10,
      columns: [
        ["stock_code", "代码", "nowrap"], ["stock_name", "名称"],
        ["industry", "行业"], ["market", "板块"],
        ["dividend_records", "分红记录", "num"], ["rights_records", "配股记录", "num"],
        ["cash_total_pretax", "累计每股派息(元)", "num"],
        ["dividend_years", "含现金年度数", "num"],
        ["cash_avg_per_year", "年均每股派息(元)", "num"],
        ["first_announce_date", "最早公告"], ["latest_announce_date", "最近公告"],
        ["latest_status", "最近进度"]
      ],
      search: ["stock_code", "stock_name", "industry", "market", "latest_status"]
    },
    rights: {
      label: "配股记录",
      rows: DATA.rights || [],
      pageSize: 10,
      columns: [
        ["stock_code", "代码", "nowrap"], ["stock_name", "名称"],
        ["announce_date", "公告日期"],
        ["rights_per10", "配股(股/10股)", "num"],
        ["rights_price", "配股价(元)", "num"],
        ["base_share_capital", "基准股本(股)", "num"],
        ["ex_rights_date", "除权日"], ["record_date", "股权登记日"],
        ["payment_start", "缴款起始日"], ["payment_end", "缴款终止日"],
        ["listing_date", "配股上市日"], ["raised_funds", "募集资金(元)", "num"]
      ],
      search: ["stock_code", "stock_name", "announce_date"]
    }
  };

  var tableState = { key: "dividends", query: "", page: 1 };

  function currentRows() {
    var config = TABLES[tableState.key];
    var query = tableState.query.trim().toLowerCase();
    if (!query) { return config.rows; }
    return config.rows.filter(function (row) {
      return config.search.some(function (field) {
        var value = row[field];
        return value !== null && value !== undefined && String(value).toLowerCase().indexOf(query) !== -1;
      });
    });
  }

  function renderTable() {
    var config = TABLES[tableState.key];
    var rows = currentRows();
    var pageSize = config.pageSize;
    var pages = Math.max(1, Math.ceil(rows.length / pageSize));
    tableState.page = Math.min(Math.max(1, tableState.page), pages);
    var start = (tableState.page - 1) * pageSize;
    var pageRows = rows.slice(start, start + pageSize);

    var table = $("#dataset-table");
    var head = $("thead", table);
    var body = $("tbody", table);
    clear(head); clear(body);

    head.appendChild(el("tr", {}, config.columns.map(function (column) {
      return el("th", { text: column[1], class: column[2] === "num" ? "num" : null });
    })));
    pageRows.forEach(function (row) {
      body.appendChild(el("tr", {}, config.columns.map(function (column) {
        var key = column[0];
        var value = row[key];
        var classes = [];
        if (column[2]) { classes.push(column[2]); }
        if (isMissing(value)) { classes.push("cell-empty"); }
        return el("td", { class: classes.join(" "), text: fmt(value) });
      })));
    });

    $("#dataset-caption").textContent = config.label + "（共 " + rows.length + " 条记录）";
    $("#table-count").textContent = "当前表 " + rows.length + " 条记录，第 " + tableState.page + " / " + pages + " 页";
    $("#pager-info").textContent = "第 " + tableState.page + " / " + pages + " 页";
    $('[data-page="prev"]').disabled = tableState.page <= 1;
    $('[data-page="next"]').disabled = tableState.page >= pages;
  }

  function renderTabs() {
    var container = $("#dataset-tabs");
    clear(container);
    Object.keys(TABLES).forEach(function (key) {
      var config = TABLES[key];
      var button = el("button", {
        type: "button",
        role: "tab",
        id: "tab-" + key,
        "aria-selected": String(key === tableState.key),
        "aria-controls": "dataset-table",
        onclick: function () {
          tableState.key = key;
          tableState.page = 1;
          Array.prototype.forEach.call(container.children, function (node) {
            node.setAttribute("aria-selected", String(node.id === "tab-" + key));
          });
          renderTable();
        }
      }, [
        document.createTextNode(config.label),
        el("span", { class: "tab-count", text: String(config.rows.length) })
      ]);
      container.appendChild(button);
    });
  }

  function setupTableControls() {
    var input = $("#table-search");
    var timer = null;
    input.addEventListener("input", function () {
      window.clearTimeout(timer);
      timer = window.setTimeout(function () {
        tableState.query = input.value;
        tableState.page = 1;
        renderTable();
      }, 150);
    });
    $('[data-page="prev"]').addEventListener("click", function () { tableState.page -= 1; renderTable(); });
    $('[data-page="next"]').addEventListener("click", function () { tableState.page += 1; renderTable(); });
  }

  /* ---------------------------------------------------------------- 质量 */
  function renderQuality() {
    var quality = DATA.quality || {};
    var checks = quality.checks || [];
    var issues = DATA.issues || [];
    var summary = quality.issue_summary || {};

    var badgeRow = $("#quality-summary");
    clear(badgeRow);
    [
      ["错误", summary.error || 0, "badge-error"],
      ["提示", summary.warning || 0, "badge-warning"],
      ["信息", summary.info || 0, "badge-info"],
      ["规则总数", checks.length, "badge-neutral"],
      ["通过规则", checks.filter(function (check) { return check.passed; }).length, "badge-pass"]
    ].forEach(function (item) {
      badgeRow.appendChild(el("span", { class: "badge " + item[2], text: item[0] + "：" + item[1] }));
    });

    var grid = $("#rule-grid");
    clear(grid);
    checks.forEach(function (check) {
      var badge = check.passed
        ? el("span", { class: "badge badge-pass", text: "通过" })
        : el("span", {
            class: "badge " + (check.level === "error" ? "badge-error" : check.level === "info" ? "badge-info" : "badge-warning"),
            text: "命中 " + check.hits
          });
      grid.appendChild(el("article", { class: "rule-card" }, [
        el("header", {}, [el("h3", { text: check.name }), badge]),
        el("span", { class: "rule-id", text: check.id + " · " + check.level }),
        el("p", { text: check.description })
      ]));
    });

    var table = $("#issue-table");
    var head = $("thead", table);
    var body = $("tbody", table);
    clear(head); clear(body);
    head.appendChild(el("tr", {}, [
      el("th", { text: "级别" }), el("th", { text: "规则" }), el("th", { text: "股票" }),
      el("th", { text: "记录编号" }), el("th", { text: "字段" }), el("th", { text: "说明" })
    ]));
    issues.forEach(function (issue) {
      var levelClass = issue.level === "error" ? "badge-error" : issue.level === "info" ? "badge-info" : "badge-warning";
      body.appendChild(el("tr", {}, [
        el("td", {}, [el("span", { class: "badge " + levelClass, text: issue.level })]),
        el("td", { text: issue.rule }),
        el("td", { class: "nowrap", text: issue.stock_code }),
        el("td", { class: "nowrap", text: issue.record_id }),
        el("td", { text: issue.field }),
        el("td", { class: "ellipsis", text: issue.message })
      ]));
    });
  }

  /* ---------------------------------------------------------------- 图表 */
  var SVG_NS = "http://www.w3.org/2000/svg";

  function svgEl(tag, attrs, text) {
    var node = document.createElementNS(SVG_NS, tag);
    Object.keys(attrs || {}).forEach(function (key) { node.setAttribute(key, attrs[key]); });
    if (text) { node.textContent = text; }
    return node;
  }

  function renderCashChart() {
    var container = $("#chart-cash");
    clear(container);
    var stocks = (DATA.stocks || []).slice().sort(function (a, b) {
      return b.cash_total_pretax - a.cash_total_pretax;
    });
    if (!stocks.length) { container.appendChild(el("p", { text: "暂无数据" })); return; }

    var width = 720, rowHeight = 44, top = 28, labelWidth = 96, valueWidth = 116;
    var height = top + stocks.length * rowHeight + 16;
    var max = Math.max.apply(null, stocks.map(function (item) { return item.cash_total_pretax; })) || 1;
    var barWidth = width - labelWidth - valueWidth;

    var svg = svgEl("svg", { viewBox: "0 0 " + width + " " + height, role: "img" });
    svg.appendChild(svgEl("title", {}, "各股票累计每股税前派息"));
    svg.appendChild(svgEl("desc", {}, "横向柱状图，展示 " + stocks.length + " 只股票的累计每股税前派息（元）。"));

    stocks.forEach(function (stock, index) {
      var y = top + index * rowHeight;
      var length = Math.max(3, (stock.cash_total_pretax / max) * barWidth);
      svg.appendChild(svgEl("text", { x: labelWidth - 10, y: y + 21, "text-anchor": "end", class: "axis-label" }, stock.stock_name));
      svg.appendChild(svgEl("rect", { x: labelWidth, y: y + 6, width: barWidth, height: 20, rx: 3, class: "grid-line", opacity: "0.35" }));
      svg.appendChild(svgEl("rect", { x: labelWidth, y: y + 6, width: length, height: 20, rx: 3, class: "bar" }));
      svg.appendChild(svgEl("text", { x: labelWidth + length + 8, y: y + 21, class: "value-label" },
        numberFormat.format(stock.cash_total_pretax)));
    });

    svg.appendChild(svgEl("text", { x: labelWidth - 10, y: 16, "text-anchor": "end", class: "axis-label" }, "股票"));
    svg.appendChild(svgEl("text", { x: width - valueWidth + 4, y: 16, class: "axis-label" }, "元 / 股（税前）"));
    container.appendChild(svg);

    var table = $("#chart-cash-table");
    var head = $("thead", table);
    var body = $("tbody", table);
    clear(head); clear(body);
    head.appendChild(el("tr", {}, [
      el("th", { text: "股票" }), el("th", { class: "num", text: "累计每股派息(元)" }),
      el("th", { class: "num", text: "年均每股派息(元)" }), el("th", { class: "num", text: "含现金分红年度数" })
    ]));
    stocks.forEach(function (stock) {
      body.appendChild(el("tr", {}, [
        el("td", { text: stock.stock_name + "（" + stock.stock_code + "）" }),
        el("td", { class: "num", text: fmt(stock.cash_total_pretax) }),
        el("td", { class: "num", text: fmt(stock.cash_avg_per_year) }),
        el("td", { class: "num", text: fmt(stock.dividend_years, { digits: 0 }) })
      ]));
    });
  }

  function renderYearlyChart() {
    var container = $("#chart-yearly");
    clear(container);
    var yearly = DATA.yearly || [];
    var stocks = DATA.stocks || [];
    if (!yearly.length) { container.appendChild(el("p", { text: "暂无数据" })); return; }

    var years = Array.from(new Set(yearly.map(function (row) { return row.dividend_year; })))
      .sort(function (a, b) { return a - b; });
    var grid = el("div", { class: "small-multiples" });

    stocks.forEach(function (stock) {
      var series = yearly.filter(function (row) { return row.stock_code === stock.stock_code; })
        .slice().sort(function (a, b) { return a.dividend_year - b.dividend_year; });
      var byYear = {};
      series.forEach(function (row) { byYear[row.dividend_year] = row.cash_per_share_sum; });

      var width = 320, height = 168;
      var pad = { left: 40, right: 44, top: 24, bottom: 24 };
      var maxValue = Math.max.apply(null, series.map(function (row) { return row.cash_per_share_sum; }).concat([0.1]));
      var max = Math.ceil(maxValue * 1.15 * 10) / 10;
      var plotWidth = width - pad.left - pad.right;
      var plotHeight = height - pad.top - pad.bottom;
      var x = function (year) {
        var index = years.indexOf(year);
        return pad.left + (years.length <= 1 ? plotWidth / 2 : (index / (years.length - 1)) * plotWidth);
      };
      var y = function (value) { return pad.top + plotHeight - (value / max) * plotHeight; };

      var svg = svgEl("svg", { viewBox: "0 0 " + width + " " + height, role: "img" });
      svg.appendChild(svgEl("title", {}, stock.stock_name + " 年度每股派息趋势"));
      svg.appendChild(svgEl("desc", {}, "折线图，纵轴 0 至 " + max + " 元，横轴为 " + years[0] + " 至 " + years[years.length - 1] + " 年。"));

      svg.appendChild(svgEl("line", { x1: pad.left, y1: pad.top, x2: pad.left, y2: pad.top + plotHeight, class: "grid-line" }));
      svg.appendChild(svgEl("line", { x1: pad.left, y1: pad.top + plotHeight, x2: width - pad.right, y2: pad.top + plotHeight, class: "grid-line" }));
      svg.appendChild(svgEl("text", { x: pad.left - 6, y: pad.top + 4, "text-anchor": "end", class: "axis-label" }, String(max)));
      svg.appendChild(svgEl("text", { x: pad.left - 6, y: pad.top + plotHeight + 4, "text-anchor": "end", class: "axis-label" }, "0"));
      svg.appendChild(svgEl("text", { x: pad.left, y: height - 6, class: "axis-label" }, String(years[0])));
      svg.appendChild(svgEl("text", { x: width - pad.right, y: height - 6, "text-anchor": "end", class: "axis-label" }, String(years[years.length - 1])));
      svg.appendChild(svgEl("text", { x: pad.left, y: 14, class: "axis-label" }, stock.stock_name + " · " + stock.industry));

      var plotted = years.filter(function (year) { return byYear[year] !== undefined; });
      var points = plotted.map(function (year) { return x(year) + "," + y(byYear[year]); });
      svg.appendChild(svgEl("polyline", {
        points: points.join(" "), fill: "none", stroke: "var(--color-accent)",
        "stroke-width": "2", "stroke-linejoin": "round", "stroke-linecap": "round"
      }));
      plotted.forEach(function (year) {
        svg.appendChild(svgEl("circle", { cx: x(year), cy: y(byYear[year]), r: "2.4", fill: "var(--color-accent)" }));
      });

      var lastRow = series[series.length - 1];
      if (lastRow) {
        svg.appendChild(svgEl("text", {
          x: Math.min(x(lastRow.dividend_year) + 6, width - 4),
          y: y(lastRow.cash_per_share_sum) + 4, class: "value-label"
        }, numberFormat.format(lastRow.cash_per_share_sum)));
      }
      grid.appendChild(el("div", { class: "sm-panel" }, [svg]));
    });

    container.appendChild(grid);
    container.appendChild(el("p", { class: "chart-note", text: "每个面板独立纵轴，避免高派息公司压低其他曲线；末端数字为最新年度的每股派息合计。" }));

    var table = $("#chart-yearly-table");
    var head = $("thead", table);
    var body = $("tbody", table);
    clear(head); clear(body);
    head.appendChild(el("tr", {}, [
      el("th", { text: "股票" }), el("th", { text: "分红年度" }),
      el("th", { class: "num", text: "每股派息合计(元)" }), el("th", { class: "num", text: "记录数" })
    ]));
    yearly.slice().sort(function (a, b) {
      return a.stock_code === b.stock_code
        ? a.dividend_year - b.dividend_year
        : a.stock_code.localeCompare(b.stock_code);
    }).forEach(function (row) {
      body.appendChild(el("tr", {}, [
        el("td", { text: row.stock_name }), el("td", { text: row.dividend_year }),
        el("td", { class: "num", text: fmt(row.cash_per_share_sum) }),
        el("td", { class: "num", text: fmt(row.records, { digits: 0 }) })
      ]));
    });
  }

  function renderStructureChart() {
    var container = $("#chart-structure");
    clear(container);
    var dividends = DATA.dividends || [];
    var stocks = DATA.stocks || [];
    if (!dividends.length) { container.appendChild(el("p", { text: "暂无数据" })); return; }

    var stats = stocks.map(function (stock) {
      var rows = dividends.filter(function (row) { return row.stock_code === stock.stock_code; });
      var total = rows.length || 1;
      var ratio = function (field) {
        return rows.filter(function (row) { return row[field] === true; }).length / total * 100;
      };
      return {
        name: stock.stock_name,
        cash: ratio("has_cash"),
        bonus: ratio("has_bonus_share"),
        transfer: ratio("has_transfer_share"),
        total: rows.length
      };
    });

    var width = 720, rowHeight = 62, top = 34, labelWidth = 96, barArea = width - labelWidth - 76;
    var height = top + stats.length * rowHeight;
    var svg = svgEl("svg", { viewBox: "0 0 " + width + " " + height, role: "img" });
    svg.appendChild(svgEl("title", {}, "各股票分红形态构成"));
    svg.appendChild(svgEl("desc", {}, "分组条形图，展示每只股票记录中含现金分红、含送股、含转增的比例。"));

    ["现金分红", "送股", "转增"].forEach(function (label, index) {
      svg.appendChild(svgEl("text", { x: labelWidth + index * 150, y: 16, class: "axis-label" }, label));
    });

    stats.forEach(function (stat, index) {
      var y = top + index * rowHeight;
      svg.appendChild(svgEl("text", { x: labelWidth - 10, y: y + 34, "text-anchor": "end", class: "axis-label" }, stat.name));
      [["cash", "bar"], ["bonus", "bar-alt"], ["transfer", "bar-transfer"]].forEach(function (item, i) {
        var length = Math.max(2, (stat[item[0]] / 100) * barArea);
        svg.appendChild(svgEl("rect", { x: labelWidth, y: y + 6 + i * 16, width: length, height: 10, rx: 2, class: item[1] }));
        svg.appendChild(svgEl("text", { x: labelWidth + length + 6, y: y + 15 + i * 16, class: "axis-label" }, stat[item[0]].toFixed(0) + "%"));
      });
    });
    container.appendChild(svg);
    container.appendChild(el("p", { class: "chart-note", text: "分母为各股票的全部分红记录；同一条记录可能既含现金分红，也同时含送股或转增。" }));

    var table = $("#chart-structure-table");
    var head = $("thead", table);
    var body = $("tbody", table);
    clear(head); clear(body);
    head.appendChild(el("tr", {}, [
      el("th", { text: "股票" }), el("th", { class: "num", text: "含现金分红" }),
      el("th", { class: "num", text: "含送股" }), el("th", { class: "num", text: "含转增" }),
      el("th", { class: "num", text: "记录数" })
    ]));
    stats.forEach(function (stat) {
      body.appendChild(el("tr", {}, [
        el("td", { text: stat.name }),
        el("td", { class: "num", text: stat.cash.toFixed(0) + "%" }),
        el("td", { class: "num", text: stat.bonus.toFixed(0) + "%" }),
        el("td", { class: "num", text: stat.transfer.toFixed(0) + "%" }),
        el("td", { class: "num", text: String(stat.total) })
      ]));
    });
  }

  /* ------------------------------------------------------------ 字段字典 */
  function renderDictionary() {
    var quality = DATA.quality || {};
    var dictionary = quality.field_dictionary || {};
    var coverage = quality.field_coverage || {};
    var table = $("#dictionary-table");
    var head = $("thead", table);
    var body = $("tbody", table);
    clear(head); clear(body);
    head.appendChild(el("tr", {}, [
      el("th", { text: "字段" }), el("th", { text: "中文名" }),
      el("th", { class: "num", text: "覆盖率" }), el("th", { text: "说明" })
    ]));
    Object.keys(dictionary).forEach(function (key) {
      var item = dictionary[key];
      body.appendChild(el("tr", {}, [
        el("td", { class: "nowrap", text: key }),
        el("td", { text: item.label || "" }),
        el("td", { class: "num", text: coverage[key] !== undefined ? (coverage[key] * 100).toFixed(1) + "%" : "—" }),
        el("td", { class: "ellipsis", text: item.description || "" })
      ]));
    });
  }

  /* ---------------------------------------------------------------- 测试 */
  function renderTests() {
    var tests = DATA.tests || { available: false, cases: [] };
    var stats = tests.stats || {};
    var summary = $("#test-summary");
    clear(summary);
    summary.appendChild(metricCard("用例总数", stats.total || 0, "条"));
    summary.appendChild(metricCard("通过", stats.passed || 0, "条"));
    summary.appendChild(metricCard("失败", stats.failed || 0, "条"));
    summary.appendChild(metricCard("测试耗时", fmtDuration(stats.duration_ms)));
    summary.appendChild(metricCard("截图", (DATA.screenshots || []).length, "张"));

    $("#test-hint").textContent = tests.available
      ? "报告文件：tests/report/index.html · 运行命令：npx playwright test"
      : "尚未生成测试报告，运行 npx playwright test 后刷新页面";

    var table = $("#test-table");
    var head = $("thead", table);
    var body = $("tbody", table);
    clear(head); clear(body);
    head.appendChild(el("tr", {}, [
      el("th", { text: "用例文件" }), el("th", { text: "用例" }),
      el("th", { text: "视口" }), el("th", { text: "结果" }), el("th", { class: "num", text: "耗时" })
    ]));
    (tests.cases || []).forEach(function (item) {
      var ok = item.status === "passed";
      body.appendChild(el("tr", {}, [
        el("td", { class: "nowrap", text: item.suite }),
        el("td", { text: item.title }),
        el("td", { class: "nowrap", text: item.project }),
        el("td", {}, [el("span", { class: "badge " + (ok ? "badge-pass" : "badge-error"), text: item.status })]),
        el("td", { class: "num", text: fmtDuration(item.duration_ms) })
      ]));
    });

    var gallery = $("#shot-gallery");
    clear(gallery);
    var shots = DATA.screenshots || [];
    if (!shots.length) {
      gallery.appendChild(el("p", { class: "hint", text: "运行 npx playwright test 后，截图会出现在这里。" }));
      return;
    }
    shots.forEach(function (shot) {
      gallery.appendChild(el("figure", {}, [
        el("img", {
          src: shot.file, alt: shot.caption, loading: "lazy",
          width: shot.width || null, height: shot.height || null
        }),
        el("figcaption", {}, [
          el("strong", { text: shot.caption }),
          el("small", {
            text: [shot.width && shot.height ? shot.width + " × " + shot.height : null, fmtBytes(shot.bytes)]
              .filter(Boolean).join(" · ")
          })
        ])
      ]));
    });
  }

  /* ------------------------------------------------------------ 动效与导航 */
  function setupReveal() {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { return; }
    document.documentElement.classList.add("reveal-ready");
    var targets = document.querySelectorAll(".band > .container > *, .pipeline-grid > li, .rule-card");
    Array.prototype.forEach.call(targets, function (node) { node.setAttribute("data-reveal", ""); });
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
    Array.prototype.forEach.call(targets, function (node) { observer.observe(node); });
  }

  function setupNav() {
    var links = Array.prototype.slice.call(document.querySelectorAll(".site-nav a"));
    var sections = links
      .map(function (link) { return document.querySelector(link.getAttribute("href")); })
      .filter(Boolean);
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) { return; }
        var active = links.find(function (item) { return item.getAttribute("href") === "#" + entry.target.id; });
        if (!active) { return; }
        links.forEach(function (item) { item.removeAttribute("aria-current"); });
        active.setAttribute("aria-current", "true");
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    sections.forEach(function (section) { observer.observe(section); });
  }

  /* ---------------------------------------------------------------- 启动 */
  function init() {
    renderMeta();
    renderPipeline();
    renderSource();
    renderTabs();
    setupTableControls();
    renderTable();
    renderQuality();
    renderCashChart();
    renderYearlyChart();
    renderStructureChart();
    renderDictionary();
    renderTests();
    setupReveal();
    setupNav();
    document.documentElement.setAttribute("data-ready", "true");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
