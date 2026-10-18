<script setup>
import { computed, ref } from "vue";
import StockChart from "./components/StockChart.vue";
import marketData from "./data/byd.json";

const { summary, monthlyReturns, rows } = marketData;

const period = ref("all");
const chartMode = ref("candle");
const showMA = ref(true);
const showMethod = ref(false);
const showTable = ref(false);

const periodOptions = [
  { label: "近1月", value: "1m" },
  { label: "近3月", value: "3m" },
  { label: "近半年", value: "6m" },
  { label: "全年", value: "all" }
];

const chartModeOptions = [
  { label: "K线", value: "candle" },
  { label: "收盘", value: "line" }
];

const latestRows = computed(() => rows.slice(-8).reverse());
const maxMonthReturn = computed(() =>
  Math.max(...monthlyReturns.map((item) => Math.abs(item.return)))
);
const positiveMonths = computed(
  () => monthlyReturns.filter((item) => item.return >= 0).length
);
const negativeMonths = computed(() => monthlyReturns.length - positiveMonths.value);
const pricePosition = computed(
  () =>
    ((summary.lastClose - summary.low) / (summary.high - summary.low)) * 100
);
const isUp = computed(() => summary.periodReturn >= 0);
const periodTone = computed(() => (isUp.value ? "gain" : "loss"));

const formatNumber = (value, digits = 2) =>
  Number(value).toLocaleString("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  });

const formatSigned = (value, suffix = "%") =>
  `${value > 0 ? "+" : ""}${formatNumber(value)}${suffix}`;

const formatVolume = (value) =>
  value >= 100000000
    ? `${formatNumber(value / 100000000, 2)}亿`
    : `${formatNumber(value / 10000, 1)}万`;

const formatAmount = (value) => `${formatNumber(value / 100000000, 1)}亿元`;
const formatDate = (value) => value.slice(5).replace("-", "/");
const monthBarWidth = (value) =>
  `${Math.max(8, (Math.abs(value) / maxMonthReturn.value) * 100)}%`;
</script>

<template>
  <div class="page-shell">
    <header class="topbar">
      <div class="brand">
        <span class="brand-mark">BYD</span>
        <span class="brand-name">市场透视</span>
      </div>
      <div class="topbar-actions">
        <span class="as-of">2023 · 历史</span>
        <t-button
          class="info-button"
          theme="default"
          variant="outline"
          shape="square"
          aria-label="查看数据与计算口径"
          @click="showMethod = true"
        >
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
          >
            <circle cx="12" cy="12" r="8.5" />
            <path d="M12 10.8v5.1" />
            <circle cx="12" cy="7.8" r=".7" fill="currentColor" stroke="none" />
          </svg>
        </t-button>
      </div>
    </header>

    <main>
      <section class="hero" aria-labelledby="page-title">
        <div class="eyebrow">
          <span>002594.SZ</span>
          <span class="eyebrow-dot"></span>
          <span>后复权</span>
        </div>
        <div class="hero-title-row">
          <div>
            <h1 id="page-title">比亚迪</h1>
            <p class="hero-period">
              {{ summary.startDate }} — {{ summary.endDate }}
              <span>·</span>
              {{ summary.tradingDays }} 个交易日
            </p>
          </div>
          <t-tag
            :theme="isUp ? 'danger' : 'success'"
            variant="light-outline"
            size="large"
            shape="round"
          >
            {{ formatSigned(summary.periodReturn) }}
          </t-tag>
        </div>

        <div class="price-line">
          <span class="currency">¥</span>
          <strong>{{ formatNumber(summary.lastClose) }}</strong>
          <span class="last-move" :class="periodTone">
            {{ summary.lastChange >= 0 ? "▲" : "▼" }}
            {{ formatNumber(Math.abs(summary.lastChange)) }}
            ({{ formatSigned(summary.lastChangePercent) }})
          </span>
        </div>

        <div class="quote-strip" aria-label="最新交易日行情摘要">
          <div>
            <span>最高</span>
            <strong>{{ formatNumber(summary.high) }}</strong>
          </div>
          <div>
            <span>最低</span>
            <strong>{{ formatNumber(summary.low) }}</strong>
          </div>
          <div>
            <span>成交额</span>
            <strong>{{ formatAmount(summary.totalAmount) }}</strong>
          </div>
        </div>
      </section>

      <section class="chart-panel" aria-labelledby="chart-title">
        <div class="section-heading">
          <div>
            <p class="section-kicker">价格与成交量</p>
            <h2 id="chart-title">全年走势</h2>
          </div>
          <span class="chart-badge">日线</span>
        </div>

        <div class="controls" aria-label="图表控制">
          <t-segmented
            v-model="period"
            class="period-control"
            :options="periodOptions"
            block
            aria-label="选择行情时间范围"
          />
          <div class="control-row">
            <t-segmented
              v-model="chartMode"
              :options="chartModeOptions"
              aria-label="选择图表显示方式"
            />
            <label class="ma-switch">
              <span>均线</span>
              <t-switch
                v-model="showMA"
                size="small"
                aria-label="显示或隐藏移动平均线"
              />
            </label>
          </div>
        </div>

        <StockChart
          :rows="rows"
          :mode="chartMode"
          :period="period"
          :show-ma="showMA"
        />

        <div class="chart-legend" :class="{ 'is-muted': !showMA }">
          <span><i class="legend-line ma5"></i>MA5</span>
          <span><i class="legend-line ma20"></i>MA20</span>
          <span><i class="legend-line ma60"></i>MA60</span>
          <span class="legend-note">红涨 · 绿跌</span>
        </div>
      </section>

      <section class="performance-section" aria-labelledby="performance-title">
        <div class="section-heading">
          <div>
            <p class="section-kicker">全年快照</p>
            <h2 id="performance-title">表现概览</h2>
          </div>
          <span class="section-meta">收盘价口径</span>
        </div>

        <div class="metric-grid">
          <article class="metric">
            <div class="metric-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M4 17.5 9.2 12l3.3 3.2L20 6.8" />
                <path d="M15.7 6.8H20v4.3" />
              </svg>
            </div>
            <span class="metric-label">最大回撤</span>
            <strong class="metric-value loss">{{ formatSigned(summary.maxDrawdown) }}</strong>
            <span class="metric-note">
              {{ formatDate(summary.drawdownPeakDate) }} →
              {{ formatDate(summary.drawdownTroughDate) }}
            </span>
          </article>

          <article class="metric">
            <div class="metric-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M4 17.5 9 13l3 2.2 8-8.7" />
                <path d="M4 20h16" />
              </svg>
            </div>
            <span class="metric-label">年化波动率</span>
            <strong class="metric-value">{{ formatNumber(summary.annualizedVolatility) }}%</strong>
            <span class="metric-note">日收益标准差 × √252</span>
          </article>

          <article class="metric">
            <div class="metric-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M6 5v14" />
                <rect x="8.5" y="7" width="3" height="10" rx="1" />
                <rect x="14" y="4" width="3" height="13" rx="1" />
              </svg>
            </div>
            <span class="metric-label">上涨交易日</span>
            <strong class="metric-value">{{ summary.upDays }}</strong>
            <span class="metric-note">下跌 {{ summary.downDays }} 天</span>
          </article>

          <article class="metric">
            <div class="metric-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <circle cx="12" cy="12" r="8.5" />
                <path d="M12 7.5v5l3 1.8" />
              </svg>
            </div>
            <span class="metric-label">平均换手率</span>
            <strong class="metric-value">{{ formatNumber(summary.averageTurnoverRate) }}%</strong>
            <span class="metric-note">全部交易日均值</span>
          </article>
        </div>

        <div class="price-range">
          <div class="range-heading">
            <span>区间位置</span>
            <strong>{{ pricePosition.toFixed(0) }}%</strong>
          </div>
          <div
            class="range-track"
            role="img"
            :aria-label="`年末收盘价位于全年最低价和最高价区间的${pricePosition.toFixed(0)}%位置`"
          >
            <span class="range-fill" :style="{ width: `${pricePosition}%` }"></span>
            <span class="range-marker" :style="{ left: `${pricePosition}%` }"></span>
          </div>
          <div class="range-labels">
            <span>低 {{ formatNumber(summary.low) }}</span>
            <span>高 {{ formatNumber(summary.high) }}</span>
          </div>
        </div>
      </section>

      <section class="monthly-section" aria-labelledby="monthly-title">
        <div class="section-heading">
          <div>
            <p class="section-kicker">月度收益</p>
            <h2 id="monthly-title">涨跌节奏</h2>
          </div>
          <span class="section-meta">
            {{ positiveMonths }} 涨 · {{ negativeMonths }} 跌
          </span>
        </div>

        <div class="monthly-list">
          <div
            v-for="month in monthlyReturns"
            :key="month.month"
            class="month-row"
          >
            <span class="month-label">{{ month.label }}</span>
            <div class="month-track" aria-hidden="true">
              <span
                class="month-bar"
                :class="month.return >= 0 ? 'gain' : 'loss'"
                :style="{ width: monthBarWidth(month.return) }"
              ></span>
            </div>
            <strong :class="month.return >= 0 ? 'gain-text' : 'loss-text'">
              {{ formatSigned(month.return) }}
            </strong>
          </div>
        </div>
      </section>

      <section class="insight-section" aria-labelledby="insight-title">
        <div class="section-heading">
          <div>
            <p class="section-kicker">历史观察</p>
            <h2 id="insight-title">三个关键节点</h2>
          </div>
          <span class="section-meta">仅描述数据</span>
        </div>

        <div class="insight-list">
          <article>
            <span class="insight-index">01</span>
            <div>
              <h3>高点出现在 2 月初</h3>
              <p>
                盘中最高价 {{ formatNumber(summary.high) }} 出现在
                {{ summary.highDate }}；收盘价口径的最大回撤随后持续至
                {{ summary.drawdownTroughDate }}。
              </p>
            </div>
          </article>
          <article>
            <span class="insight-index">02</span>
            <div>
              <h3>11 月跌幅最集中</h3>
              <p>
                月度表现中，11 月为 {{ formatSigned(-16.35) }}；全年有
                {{ negativeMonths }} 个月收跌，{{ positiveMonths }} 个月收涨。
              </p>
            </div>
          </article>
          <article>
            <span class="insight-index">03</span>
            <div>
              <h3>单日波动两端</h3>
              <p>
                最大单日涨幅 {{ formatSigned(summary.bestDay.value) }}，发生在
                {{ summary.bestDay.date }}；最大单日跌幅
                {{ formatSigned(summary.worstDay.value) }}，发生在
                {{ summary.worstDay.date }}。
              </p>
            </div>
          </article>
        </div>
      </section>

      <section class="recent-section" aria-labelledby="recent-title">
        <div class="section-heading">
          <div>
            <p class="section-kicker">最近 8 个交易日</p>
            <h2 id="recent-title">交易日明细</h2>
          </div>
        </div>

        <div class="recent-list">
          <t-cell
            v-for="row in latestRows"
            :key="row.date"
            :title="row.date"
            :description="`成交额 ${formatAmount(row.amount)} · 换手 ${formatNumber(row.turnoverRate)}%`"
            :note="formatNumber(row.close)"
            :bordered="true"
          >
            <template #note>
              <span class="cell-note">
                <strong>{{ formatNumber(row.close) }}</strong>
                <span :class="row.changePercent >= 0 ? 'gain-text' : 'loss-text'">
                  {{ formatSigned(row.changePercent) }}
                </span>
              </span>
            </template>
          </t-cell>
        </div>

        <t-button
          class="table-button"
          block
          variant="outline"
          theme="default"
          @click="showTable = !showTable"
        >
          {{ showTable ? "收起完整交易日" : "查看完整交易日" }}
        </t-button>

        <div v-if="showTable" class="table-wrap" tabindex="0">
          <table>
            <caption class="sr-only">
              比亚迪 2023 年后复权逐日行情
            </caption>
            <thead>
              <tr>
                <th scope="col">日期</th>
                <th scope="col">收盘</th>
                <th scope="col">涨跌幅</th>
                <th scope="col">成交量</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in rows" :key="`table-${row.date}`">
                <th scope="row">{{ row.date }}</th>
                <td>{{ formatNumber(row.close) }}</td>
                <td :class="row.changePercent >= 0 ? 'gain-text' : 'loss-text'">
                  {{ formatSigned(row.changePercent) }}
                </td>
                <td>{{ formatVolume(row.volume) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>

    <footer class="footer">
      <p>数据范围 {{ summary.startDate }} — {{ summary.endDate }}</p>
      <p>历史行情分析，不构成投资建议</p>
    </footer>

    <t-dialog
      :visible="showMethod"
      title="数据与计算口径"
      :cancel-btn="null"
      confirm-btn="关闭"
      :close-btn="true"
      :close-on-overlay-click="true"
      @close="showMethod = false"
      @confirm="showMethod = false"
    >
      <div class="method-copy">
        <p>
          价格使用提供方给出的后复权日线数据。区间收益按首个交易日收盘价与
          最后一个交易日收盘价计算。
        </p>
        <p>
          最大回撤基于每日收盘价的滚动历史高点计算；年化波动率为日收益样本
          标准差乘以 √252。
        </p>
        <p>
          页面只描述 2023 年历史数据，不预测未来价格，也不提供买卖建议。
        </p>
      </div>
    </t-dialog>
  </div>
</template>

