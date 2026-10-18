<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts/core";
import { BarChart, CandlestickChart, LineChart } from "echarts/charts";
import {
  AxisPointerComponent,
  DataZoomComponent,
  GridComponent,
  TooltipComponent
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  BarChart,
  CandlestickChart,
  LineChart,
  AxisPointerComponent,
  DataZoomComponent,
  GridComponent,
  TooltipComponent,
  CanvasRenderer
]);

const props = defineProps({
  rows: {
    type: Array,
    required: true
  },
  mode: {
    type: String,
    default: "candle"
  },
  period: {
    type: String,
    default: "all"
  },
  showMA: {
    type: Boolean,
    default: true
  }
});

const chartRoot = ref(null);
let chart;
let resizeObserver;

const periodLength = {
  "1m": 22,
  "3m": 66,
  "6m": 126,
  all: 242
};

const visibleRows = computed(() =>
  props.rows.slice(-(periodLength[props.period] ?? props.rows.length))
);

const chartLabel = computed(() => {
  const first = visibleRows.value[0];
  const last = visibleRows.value.at(-1);
  return `比亚迪后复权价格图，${first.date}至${last.date}，共${visibleRows.value.length}个交易日。可在下方交易日明细中查看数值。`;
});

const movingAverage = (rows, windowSize) =>
  rows.map((row, index) => {
    if (index < windowSize - 1) return "-";
    const windowRows = rows.slice(index - windowSize + 1, index + 1);
    return Number(
      (
        windowRows.reduce((total, current) => total + current.close, 0) /
        windowSize
      ).toFixed(2)
    );
  });

const escapeHtml = (value) =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

const formatNumber = (value, digits = 2) =>
  Number(value).toLocaleString("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  });

const formatSigned = (value) => `${value > 0 ? "+" : ""}${formatNumber(value)}%`;

const tooltipFormatter = (params) => {
  const index = params[0]?.dataIndex;
  const row = visibleRows.value[index];
  if (!row) return "";
  const previous = visibleRows.value[index - 1];
  const change = previous ? (row.close / previous.close - 1) * 100 : row.changePercent;
  const trendClass = change >= 0 ? "up" : "down";
  const trendLabel = change >= 0 ? "上涨" : "下跌";

  return `
    <div class="chart-tooltip">
      <div class="chart-tooltip__date">${escapeHtml(row.date)}</div>
      <div class="chart-tooltip__row">
        <span>收盘</span>
        <strong>¥${formatNumber(row.close)}</strong>
      </div>
      <div class="chart-tooltip__row ${trendClass}">
        <span>${trendLabel}</span>
        <strong>${formatSigned(change)}</strong>
      </div>
      <div class="chart-tooltip__ohlc">
        开 ${formatNumber(row.open)} · 高 ${formatNumber(row.high)}
        <br />
        低 ${formatNumber(row.low)} · 量 ${(row.volume / 10000).toFixed(1)}万
      </div>
    </div>
  `;
};

const buildOption = () => {
  const rows = visibleRows.value;
  const dates = rows.map((row) => row.date.slice(5));
  const closeSeries = rows.map((row) => row.close);
  const candleSeries = rows.map((row) => [
    row.open,
    row.close,
    row.low,
    row.high
  ]);
  const volumeSeries = rows.map((row) => ({
    value: row.volume,
    itemStyle: {
      color: row.close >= row.open ? "#ef6257" : "#2ab7a5",
      opacity: 0.58
    }
  }));
  const ma5 = movingAverage(rows, 5);
  const ma20 = movingAverage(rows, 20);
  const ma60 = movingAverage(rows, 60);
  const reduceMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  const priceSeries =
    props.mode === "candle"
      ? {
          name: "日K",
          type: "candlestick",
          data: candleSeries,
          barMaxWidth: 9,
          itemStyle: {
            color: "#ef6257",
            color0: "#2ab7a5",
            borderColor: "#ef6257",
            borderColor0: "#2ab7a5"
          },
          emphasis: {
            itemStyle: {
              borderWidth: 2
            }
          }
        }
      : {
          name: "收盘价",
          type: "line",
          data: closeSeries,
          showSymbol: false,
          smooth: 0.12,
          lineStyle: {
            color: "#f3b43f",
            width: 2.2
          },
          itemStyle: {
            color: "#f3b43f"
          },
          areaStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: "rgba(243, 180, 63, 0.24)" },
                { offset: 1, color: "rgba(243, 180, 63, 0.01)" }
              ]
            }
          }
        };

  const maSeries = props.showMA
    ? [
        {
          name: "MA5",
          type: "line",
          data: ma5,
          showSymbol: false,
          connectNulls: false,
          lineStyle: { width: 1.1, color: "#f0d186" },
          itemStyle: { color: "#f0d186" },
          emphasis: { disabled: true }
        },
        {
          name: "MA20",
          type: "line",
          data: ma20,
          showSymbol: false,
          connectNulls: false,
          lineStyle: { width: 1.1, color: "#79a7ff" },
          itemStyle: { color: "#79a7ff" },
          emphasis: { disabled: true }
        },
        {
          name: "MA60",
          type: "line",
          data: ma60,
          showSymbol: false,
          connectNulls: false,
          lineStyle: { width: 1.1, color: "#d7c5ff" },
          itemStyle: { color: "#d7c5ff" },
          emphasis: { disabled: true }
        }
      ]
    : [];

  return {
    animation: !reduceMotion,
    animationDuration: reduceMotion ? 0 : 260,
    animationDurationUpdate: reduceMotion ? 0 : 180,
    aria: {
      enabled: true,
      description: chartLabel.value
    },
    grid: [
      { left: 10, right: 14, top: 16, height: "61%" },
      { left: 10, right: 14, top: "73%", height: "14%" }
    ],
    axisPointer: {
      link: [{ xAxisIndex: "all" }],
      label: {
        backgroundColor: "#35302a",
        color: "#f7f1e8",
        borderColor: "rgba(255,255,255,0.12)"
      }
    },
    tooltip: {
      trigger: "axis",
      confine: true,
      backgroundColor: "rgba(24, 22, 19, 0.97)",
      borderColor: "rgba(255, 255, 255, 0.12)",
      borderWidth: 1,
      padding: 0,
      textStyle: {
        color: "#f7f1e8",
        fontFamily: "IBM Plex Sans, Microsoft YaHei, sans-serif"
      },
      extraCssText:
        "border-radius:8px;box-shadow:0 12px 32px rgba(0,0,0,.34);",
      formatter: tooltipFormatter
    },
    xAxis: [
      {
        type: "category",
        data: dates,
        boundaryGap: true,
        axisLine: { lineStyle: { color: "rgba(255,255,255,0.12)" } },
        axisTick: { show: false },
        axisLabel: {
          color: "#918a81",
          fontSize: 10,
          interval: Math.max(0, Math.floor(dates.length / 5) - 1)
        },
        splitLine: { show: false }
      },
      {
        type: "category",
        gridIndex: 1,
        data: dates,
        boundaryGap: true,
        axisLine: { lineStyle: { color: "rgba(255,255,255,0.08)" } },
        axisTick: { show: false },
        axisLabel: { show: false },
        splitLine: { show: false }
      }
    ],
    yAxis: [
      {
        scale: true,
        position: "right",
        splitNumber: 4,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: "#918a81",
          fontFamily: "IBM Plex Mono, monospace",
          fontSize: 10,
          margin: 8
        },
        splitLine: {
          lineStyle: { color: "rgba(255,255,255,0.055)", type: "dashed" }
        }
      },
      {
        scale: true,
        gridIndex: 1,
        position: "right",
        splitNumber: 1,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: "#6f6961",
          fontSize: 9,
          formatter: (value) => `${(value / 10000).toFixed(0)}万`
        },
        splitLine: { show: false }
      }
    ],
    dataZoom: [
      {
        type: "inside",
        xAxisIndex: [0, 1],
        start: 0,
        end: 100,
        zoomOnMouseWheel: false,
        moveOnMouseMove: true,
        moveOnMouseWheel: false
      }
    ],
    series: [
      {
        ...priceSeries,
        xAxisIndex: 0,
        yAxisIndex: 0
      },
      ...maSeries.map((series) => ({
        ...series,
        xAxisIndex: 0,
        yAxisIndex: 0
      })),
      {
        name: "成交量",
        type: "bar",
        data: volumeSeries,
        xAxisIndex: 1,
        yAxisIndex: 1,
        barMaxWidth: 7,
        emphasis: { itemStyle: { opacity: 0.9 } }
      }
    ]
  };
};

const renderChart = () => {
  if (!chart) return;
  chart.setOption(buildOption(), { notMerge: true });
};

onMounted(async () => {
  await nextTick();
  chart = echarts.init(chartRoot.value, null, {
    renderer: "canvas",
    useDirtyRect: true
  });
  renderChart();
  resizeObserver = new ResizeObserver(() => chart?.resize());
  resizeObserver.observe(chartRoot.value);
});

watch(
  () => [props.mode, props.period, props.showMA, props.rows],
  () => renderChart(),
  { deep: true }
);

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  chart?.dispose();
});
</script>

<template>
  <div
    ref="chartRoot"
    class="stock-chart"
    role="img"
    :aria-label="chartLabel"
  ></div>
</template>

