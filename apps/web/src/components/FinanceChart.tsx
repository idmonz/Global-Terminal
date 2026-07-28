"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Row = Record<string, unknown>;
type LightweightChartsModule = typeof import("lightweight-charts");
type LightweightChartApi = {
  addSeries: (definition: unknown, options?: Row) => { setData: (data: unknown[]) => void };
  priceScale: (id: string) => { applyOptions: (options: Row) => void };
  remove: () => void;
  resize: (width: number, height: number) => void;
  timeScale: () => { fitContent: () => void };
};

interface FinanceChartProps {
  chart: Row;
}

interface SeriesModel {
  name: string;
  color: string;
  points: ChartPoint[];
}

interface ChartPoint {
  label: string;
  time: number;
  value: number;
}

interface ChartModel {
  chartType: string;
  series: SeriesModel[];
  normalizedAxis: boolean;
  intraday: boolean;
  categories: string[];
  candles: CandlePoint[];
  volume: VolumePoint[];
  height: number | null;
}

interface CandlePoint { time: number; open: number; high: number; low: number; close: number; }
interface VolumePoint { time: number; value: number; color: string; }

const PALETTE = ["#2dd4bf", "#f4b740", "#93c5fd", "#fb7185", "#86efac", "#c4b5fd"];
const SYNTHETIC_START = Date.UTC(2026, 0, 1);

export function FinanceChart({ chart }: FinanceChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<LightweightChartApi | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "fallback">("loading");
  const [message, setMessage] = useState("Loading chart renderer");
  const model = useMemo(() => buildChartModel(chart), [chart]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || model.series.length === 0) {
      setStatus("fallback");
      setMessage("No plottable chart points");
      return;
    }

    let cancelled = false;
    let resizeObserver: ResizeObserver | null = null;
    let localChart: LightweightChartApi | null = null;
    let resizeTimer: ReturnType<typeof setTimeout> | null = null;
    let settleTimer: ReturnType<typeof setTimeout> | null = null;

    const syncSize = () => {
      if (cancelled || !localChart || !container) return;
      const width = Math.max(280, Math.floor(container.getBoundingClientRect().width));
      localChart.resize(width, chartHeightForContainer(container, model.height));
      localChart.timeScale().fitContent();
    };

    async function renderChart() {
      try {
        const lightweightCharts = await import("lightweight-charts");
        if (cancelled || !container) {
          return;
        }

        const chartApi = createFinanceChart(lightweightCharts, container, model);
        localChart = chartApi;
        chartRef.current = chartApi;
        setStatus("ready");
        setMessage("TradingView Lightweight Charts renderer active");

        resizeTimer = setTimeout(syncSize, 0);
        settleTimer = setTimeout(syncSize, 250);
        window.addEventListener("resize", syncSize);

        resizeObserver = new ResizeObserver((entries) => {
          const entry = entries[0];
          if (!entry || cancelled || !localChart) {
            return;
          }
          const width = Math.max(280, Math.floor(entry.contentRect.width));
          localChart.resize(width, chartHeightForContainer(container, model.height));
          localChart.timeScale().fitContent();
        });
        resizeObserver.observe(container);
      } catch (error) {
        setStatus("fallback");
        setMessage(error instanceof Error ? error.message : "Chart renderer failed");
      }
    }

    renderChart();

    return () => {
      cancelled = true;
      resizeObserver?.disconnect();
      if (resizeTimer) clearTimeout(resizeTimer);
      if (settleTimer) clearTimeout(settleTimer);
      window.removeEventListener("resize", syncSize);
      const chartToRemove = localChart;
      localChart = null;
      if (chartRef.current === chartToRemove) {
        chartRef.current = null;
      }
      chartToRemove?.remove();
    };
  }, [model]);

  if (model.series.length === 0) {
    return (
      <div
        className="finance-chart-shell fallback"
        data-renderer="lightweight-finance-chart"
        data-chart-state="fallback"
        data-chart-points="0"
      >
        <div className="finance-chart-status">No plottable chart points</div>
      </div>
    );
  }

  return (
    <div
      className={`finance-chart-shell ${status}`}
      data-renderer="lightweight-finance-chart"
      data-source-status={text(chart.source_status, "unknown")}
      data-normalized-axis={model.normalizedAxis ? "true" : "false"}
      data-chart-state={status}
      data-chart-points={String(model.series.reduce((total, series) => total + series.points.length, 0))}
      data-chart-candles={String(model.candles.length)}
      data-chart-volume={String(model.volume.length)}
    >
      <div ref={containerRef} className="finance-chart-container" aria-label={text(chart.title, "Financial chart")} />
      <div className="finance-chart-footer">
        <span className={`finance-chart-status ${status}`}>{message}</span>
        <a className="finance-chart-attribution" href="https://www.tradingview.com/" target="_blank" rel="noreferrer">
          Charts by TradingView
        </a>
      </div>
      {model.normalizedAxis ? (
        <div className="finance-chart-category-strip" aria-label="Normalized category axis">
          {model.categories.slice(0, 10).map((category) => (
            <span key={category}>{category}</span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function createFinanceChart(lightweightCharts: LightweightChartsModule, container: HTMLDivElement, model: ChartModel): LightweightChartApi {
  container.replaceChildren();
  const chart = lightweightCharts.createChart(container, {
    width: Math.max(280, Math.floor(container.getBoundingClientRect().width || 360)),
    height: chartHeightForContainer(container, model.height),
    layout: {
      background: { type: lightweightCharts.ColorType.Solid, color: "rgba(12, 13, 15, 0)" },
      textColor: "rgba(231, 225, 213, 0.72)",
      fontFamily: 'Consolas, "Liberation Mono", monospace',
      fontSize: 11,
    },
    grid: {
      vertLines: { color: "rgba(231, 225, 213, 0.06)" },
      horzLines: { color: "rgba(231, 225, 213, 0.08)" },
    },
    rightPriceScale: {
      borderColor: "rgba(231, 225, 213, 0.18)",
      scaleMargins: { top: 0.12, bottom: 0.18 },
    },
    timeScale: {
      borderColor: "rgba(231, 225, 213, 0.18)",
      timeVisible: model.intraday,
      secondsVisible: false,
    },
    crosshair: {
      vertLine: { color: "rgba(244, 183, 64, 0.36)", labelBackgroundColor: "#16171a" },
      horzLine: { color: "rgba(244, 183, 64, 0.28)", labelBackgroundColor: "#16171a" },
    },
  }) as LightweightChartApi;

  if (model.chartType.includes("candlestick") && model.candles.length) {
    const candles = chart.addSeries(lightweightCharts.CandlestickSeries, {
      upColor: "#2dd4bf",
      downColor: "#fb7185",
      borderUpColor: "#2dd4bf",
      borderDownColor: "#fb7185",
      wickUpColor: "rgba(45, 212, 191, 0.78)",
      wickDownColor: "rgba(251, 113, 133, 0.78)",
      priceLineVisible: false,
    });
    candles.setData(model.candles);
    model.series.slice(1).forEach((series, index) => {
      const overlay = chart.addSeries(lightweightCharts.LineSeries, {
        color: series.color,
        lineWidth: index === 0 ? 2 : 1,
        priceLineVisible: false,
      });
      overlay.setData(series.points.map((point) => ({ time: point.time, value: point.value })));
    });
  } else if (model.chartType.includes("bar") || model.chartType.includes("heat")) {
    const points = model.series[0]?.points ?? [];
    const histogram = chart.addSeries(lightweightCharts.HistogramSeries, {
      color: PALETTE[0],
      priceFormat: { type: "price", precision: 2, minMove: 0.01 },
      priceLineVisible: false,
    });
    histogram.setData(
      points.map((point) => ({
        time: point.time,
        value: point.value,
        color: point.value < 0 ? "rgba(251, 113, 133, 0.82)" : "rgba(45, 212, 191, 0.78)",
      })),
    );
  } else {
    model.series.forEach((series, index) => {
      const useArea = model.series.length === 1 && (model.chartType.includes("line") || model.chartType.includes("price"));
      const seriesApi = chart.addSeries(useArea ? lightweightCharts.AreaSeries : lightweightCharts.LineSeries, {
        lineColor: series.color,
        color: series.color,
        topColor: withAlpha(series.color, 0.28),
        bottomColor: withAlpha(series.color, 0.02),
        lineWidth: index === 0 ? 2 : 1,
        priceLineVisible: false,
      });
      seriesApi.setData(series.points.map((point) => ({ time: point.time, value: point.value })));
    });
  }

  if (model.volume.length) {
    const volume = chart.addSeries(lightweightCharts.HistogramSeries, {
      priceScaleId: "volume",
      priceFormat: { type: "volume" },
      priceLineVisible: false,
      lastValueVisible: false,
    });
    volume.setData(model.volume);
    chart.priceScale("volume").applyOptions({ visible: false, autoScale: true, scaleMargins: { top: 0.78, bottom: 0 } });
  }

  chart.timeScale().fitContent();
  return chart;
}

function buildChartModel(chart: Row): ChartModel {
  const chartType = text(chart.chart_type, "line").toLowerCase();
  const rawSeries = asRecordArray(chart.series);
  const allLabels = new Set<string>();
  let normalizedAxis = false;
  let intraday = false;
  const candles = normalizeCandles(asRecordArray(chart.candles));
  const volume = normalizeVolume(asRecordArray(chart.volume));
  const height = number(chart.height_px);

  const series = rawSeries
    .map((item, seriesIndex) => {
      const points = normalizeTimeSeries(asRecordArray(item.points)
        .map((point, pointIndex) => {
          const value = number(point.y);
          if (value === null) {
            return null;
          }
          const label = text(point.x, `p${pointIndex + 1}`);
          const parsedTime = timeLabel(label);
          if (!parsedTime) {
            normalizedAxis = true;
          }
          if (/[T ]\d{2}:\d{2}/.test(label)) {
            intraday = true;
          }
          allLabels.add(label);
          return {
            label,
            time: parsedTime ?? syntheticTime(pointIndex),
            value,
          };
        })
        .filter((point): point is ChartPoint => Boolean(point)));

      return {
        name: text(item.name, `series ${seriesIndex + 1}`),
        color: PALETTE[seriesIndex % PALETTE.length],
        points,
      };
    })
    .filter((item) => item.points.length > 0);

  return {
    chartType,
    series,
    normalizedAxis,
    intraday,
    categories: Array.from(allLabels),
    candles,
    volume,
    height: height === null ? null : Math.max(150, Math.min(520, Math.round(height))),
  };
}

function chartHeightForContainer(container: HTMLElement, heightHint: number | null): number {
  const bounds = container.getBoundingClientRect();
  const width = bounds.width || 360;
  const responsiveLimit = Math.max(210, Math.min(420, Math.round(width * 0.5)));
  const layoutLimit = bounds.height >= 150 ? Math.round(bounds.height) : responsiveLimit;
  return heightHint === null
    ? Math.min(responsiveLimit, layoutLimit)
    : Math.min(heightHint, responsiveLimit, layoutLimit);
}

function normalizeCandles(rows: Row[]): CandlePoint[] {
  const byTime = new Map<number, CandlePoint>();
  rows.forEach((row) => {
    const time = timeLabel(text(row.time, ""));
    const open = number(row.open); const high = number(row.high); const low = number(row.low); const close = number(row.close);
    if (time === null || open === null || high === null || low === null || close === null) return;
    if (high < Math.max(open, close) || low > Math.min(open, close)) return;
    byTime.set(time, { time, open, high, low, close });
  });
  return Array.from(byTime.values()).sort((left, right) => left.time - right.time);
}

function normalizeVolume(rows: Row[]): VolumePoint[] {
  const byTime = new Map<number, VolumePoint>();
  rows.forEach((row) => {
    const time = timeLabel(text(row.time, ""));
    const value = number(row.value);
    if (time === null || value === null || value < 0) return;
    byTime.set(time, { time, value, color: text(row.direction) === "down" ? "rgba(251, 113, 133, 0.42)" : "rgba(45, 212, 191, 0.38)" });
  });
  return Array.from(byTime.values()).sort((left, right) => left.time - right.time);
}

function asRecordArray(value: unknown): Row[] {
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

function isRecord(value: unknown): value is Row {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function number(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function text(value: unknown, fallback = "none"): string {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  if (typeof value === "object") {
    return fallback;
  }
  return String(value);
}

function timeLabel(value: string): number | null {
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return Math.floor(parsed / 1000);
}

function syntheticTime(index: number): number {
  return Math.floor((SYNTHETIC_START + index * 86_400_000) / 1000);
}

function normalizeTimeSeries(points: ChartPoint[]): ChartPoint[] {
  const byTime = new Map<number, ChartPoint>();
  points.forEach((point) => byTime.set(point.time, point));
  return Array.from(byTime.values()).sort((left, right) => left.time - right.time);
}

function withAlpha(hex: string, alpha: number): string {
  const normalized = hex.replace("#", "");
  if (normalized.length !== 6) {
    return hex;
  }
  const r = Number.parseInt(normalized.slice(0, 2), 16);
  const g = Number.parseInt(normalized.slice(2, 4), 16);
  const b = Number.parseInt(normalized.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
