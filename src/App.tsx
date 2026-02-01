import { useEffect, useMemo, useState } from "react";
import "./App.css";

type Status = "GOOD" | "WARN" | "DELAYED";

export type Gauge = {
  key: string;
  title: string;
  status: Status;

  valueText: string; // e.g. "142 bp"

  /**
   * Prefer this for real updates:
   * ISO timestamp like "2026-01-20T19:45:00Z"
   */
  updatedAt?: string;

  /**
   * Back-compat / fallback: if you still provide "2h 8m ago" in JSON,
   * we will display it as-is.
   */
  updatedText?: string;

  // 0..100 where 0=far left, 100=far right
  pct: number;

  // labels around dial
  minLabel?: string;
  midLabel?: string;
  maxLabel?: string;

  tooltip: string;
};

// This matches your current indicators.json schema (id/type/value/min/max/etc.)
// and also supports the "native gauge" schema (pct/valueText) if you later use it.
type RawCard = {
  id?: string;
  key?: string;
  type?: string;

  title?: string;
  status?: Status;

  value?: number;
  unit?: string;

  min?: number;
  max?: number;

  // Optional overrides
  valueText?: string;
  pct?: number;

  minLabel?: string;
  midLabel?: string;
  maxLabel?: string;

  tooltip?: string;

  updatedAt?: string;
  updatedText?: string;
};

type IndicatorsPayload = {
  asOf?: string; // optional global timestamp
  cards?: RawCard[];
};

// NDJSON rows: {"week":"YYYY-MM-DD", ...metric fields...}
type HistoryRow = {
  week: string;
  [k: string]: unknown;
};

type HistoryPoint = { week: string; value: number };

type HistoryMap = Record<string, HistoryPoint[]>;

// --- Your current placeholders (used as initial state + fallback) ---
const defaultGauges: Gauge[] = [
  {
    key: "credit",
    title: "Credit Stress",
    status: "WARN",
    valueText: "142 bp",
    updatedText: "2h 8m ago",
    pct: 72,
    minLabel: "0",
    midLabel: "50",
    maxLabel: "100",
    tooltip: "Credit spread stress proxy (placeholder). Higher = worse.",
  },
  {
    key: "vol",
    title: "Volatility Regime",
    status: "GOOD",
    valueText: "18.7",
    updatedText: "55m ago",
    pct: 35,
    minLabel: "10",
    midLabel: "20",
    maxLabel: "40",
    tooltip: "Volatility regime indicator (placeholder). Higher = riskier.",
  },
  {
    key: "liq",
    title: "Liquidity Conditions",
    status: "GOOD",
    valueText: "Adequate",
    updatedText: "2h 20m ago",
    pct: 30,
    minLabel: "Tight",
    midLabel: "OK",
    maxLabel: "Ample",
    tooltip: "Market liquidity conditions (placeholder).",
  },
  {
    key: "banks",
    title: "Regional Bank Stress",
    status: "DELAYED",
    valueText: "Elevated",
    updatedText: "4h 20m ago",
    pct: 62,
    minLabel: "Low",
    midLabel: "Med",
    maxLabel: "High",
    tooltip: "Regional bank stress composite (placeholder).",
  },
  {
    key: "pos",
    title: "Positioning / Crowding",
    status: "DELAYED",
    valueText: "Crowded",
    updatedText: "1d 0h ago",
    pct: 66,
    minLabel: "Light",
    midLabel: "OK",
    maxLabel: "Crowded",
    tooltip: "Crowding / positioning indicator (placeholder).",
  },
  {
    key: "recession",
    title: "Recession Probability",
    status: "GOOD",
    valueText: "13%",
    updatedText: "3h 0m ago",
    pct: 22,
    minLabel: "0%",
    midLabel: "25%",
    maxLabel: "50%",
    tooltip: "Model-based recession probability (placeholder).",
  },
  {
    key: "cmbs",
    title: "CMBS / CRE Stress",
    status: "DELAYED",
    valueText: "21",
    updatedText: "8m ago",
    pct: 48,
    minLabel: "10",
    midLabel: "20",
    maxLabel: "40",
    tooltip: "Commercial real estate stress proxy (placeholder).",
  },
  {
    key: "flows",
    title: "Equity Fund Flows",
    status: "WARN",
    valueText: "-$22bn",
    updatedText: "1h 9m ago",
    pct: 70,
    minLabel: "In",
    midLabel: "Flat",
    maxLabel: "Out",
    tooltip: "Net equity fund flows (placeholder). Outflows = risk-off.",
  },
  {
    key: "earnings",
    title: "Earnings Deterioration",
    status: "DELAYED",
    valueText: "19",
    updatedText: "18m ago",
    pct: 58,
    minLabel: "OK",
    midLabel: "Soft",
    maxLabel: "Bad",
    tooltip: "Earnings revisions / deterioration proxy (placeholder).",
  },
  {
    key: "integrity",
    title: "Data Integrity",
    status: "GOOD",
    valueText: "96%",
    updatedText: "Just now",
    pct: 96,
    minLabel: "0%",
    midLabel: "50%",
    maxLabel: "100%",
    tooltip: "Overall freshness / integrity (placeholder).",
  },
];

function statusClass(s: Status) {
  if (s === "GOOD") return "pill pillGood";
  if (s === "WARN") return "pill pillWarn";
  return "pill pillDelayed";
}

function needleRotationFromPct(pct: number) {
  // Map 0..100 to -120deg .. +120deg (240-degree sweep)
  const clamped = Math.max(0, Math.min(100, pct));
  return -120 + (240 * clamped) / 100;
}

function timeAgo(iso: string) {
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return "—";
  const seconds = Math.max(0, Math.floor((Date.now() - t) / 1000));

  if (seconds < 15) return "Just now";

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ${minutes % 60}m ago`;

  const days = Math.floor(hours / 24);
  return `${days}d ${hours % 24}h ago`;
}

/**
 * Convert your indicators.json card (RawCard) into a proper Gauge the UI can render.
 * - If pct/valueText already exist, we use them directly.
 * - Otherwise we compute pct from value/min/max and build valueText.
 */
function toGauge(c: RawCard): Gauge | null {
  const key = (c.key ?? c.id ?? "").toString().trim();
  if (!key) return null;

  const title = (c.title ?? "UNTITLED").toString();
  const status: Status = (c.status ?? "DELAYED") as Status;

  // If JSON already provides pct + valueText, accept it as-is
  if (typeof c.pct === "number" && typeof c.valueText === "string") {
    return {
      key,
      title,
      status,
      valueText: c.valueText,
      pct: Math.max(0, Math.min(100, c.pct)),
      minLabel: c.minLabel,
      midLabel: c.midLabel,
      maxLabel: c.maxLabel,
      tooltip: c.tooltip ?? "",
      updatedAt: c.updatedAt,
      updatedText: c.updatedText,
    };
  }

  const min = typeof c.min === "number" ? c.min : 0;
  const max = typeof c.max === "number" ? c.max : 100;

  let pct = 50;
  if (typeof c.value === "number" && max !== min) {
    pct = ((c.value - min) / (max - min)) * 100;
  }
  pct = Math.max(0, Math.min(100, pct));

  const valueText =
    typeof c.valueText === "string"
      ? c.valueText
      : typeof c.value === "number"
        ? `${c.value}${c.unit ?? ""}`
        : "—";

  return {
    key,
    title,
    status,
    valueText,
    pct,
    minLabel: c.minLabel ?? String(min),
    midLabel: c.midLabel ?? "",
    maxLabel: c.maxLabel ?? String(max),
    tooltip: c.tooltip ?? "",
    updatedAt: c.updatedAt,
    updatedText: c.updatedText,
  };
}

// ---- Sparkline helpers ----

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

function buildSparkPolyline(points: number[], w: number, h: number, pad = 6) {
  const n = points.length;
  if (n < 2) return "";

  let minV = Infinity;
  let maxV = -Infinity;
  for (const v of points) {
    if (v < minV) minV = v;
    if (v > maxV) maxV = v;
  }
  if (!Number.isFinite(minV) || !Number.isFinite(maxV)) return "";
  if (maxV - minV < 1e-9) {
    // flat line
    const y = pad + (h - 2 * pad) * 0.5;
    return Array.from({ length: n }, (_, i) => {
      const x = pad + ((w - 2 * pad) * i) / (n - 1);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
  }

  const pts: string[] = [];
  for (let i = 0; i < n; i++) {
    const x = pad + ((w - 2 * pad) * i) / (n - 1);
    const t = (points[i] - minV) / (maxV - minV); // 0..1
    const y = h - pad - (h - 2 * pad) * t;
    pts.push(`${x.toFixed(1)},${y.toFixed(1)}`);
  }
  return pts.join(" ");
}

function Sparkline({
  series,
  status,
}: {
  series: HistoryPoint[] | undefined;
  status: Status;
}) {
  // Keep it tiny and fast
  const w = 150;
  const h = 54;

  if (!series || series.length < 2) {
    return (
      <div
        style={{
          width: w,
          height: h,
          borderRadius: 12,
          background: "rgba(0,0,0,0.25)",
          border: "1px solid rgba(255,255,255,0.10)",
        }}
        title="No history yet"
      />
    );
  }

  // Use last ~60 points max for readability (still covers >1y if weekly)
  const tail = series.slice(-60);
  const values = tail.map((p) => p.value);

  const poly = buildSparkPolyline(values, w, h, 7);
  const last = tail[tail.length - 1];

  // Colour by status (subtle)
  const stroke =
    status === "GOOD"
      ? "rgba(90, 235, 170, 0.90)"
      : status === "WARN"
        ? "rgba(255, 205, 120, 0.90)"
        : "rgba(255, 120, 120, 0.90)";

  return (
    <div
      style={{
        width: w,
        height: h,
        borderRadius: 12,
        background: "rgba(0,0,0,0.30)",
        border: "1px solid rgba(255,255,255,0.10)",
        padding: 0,
        position: "relative",
        overflow: "hidden",
      }}
      title={`Weekly history (last ${tail.length} points). Latest: ${last.week} = ${last.value}`}
    >
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden="true">
        {/* faint baseline grid */}
        <line x1="0" y1={h - 1} x2={w} y2={h - 1} stroke="rgba(255,255,255,0.06)" />
        <polyline
          points={poly}
          fill="none"
          stroke={stroke}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* last point dot */}
        <circle
          cx={w - 7}
          cy={(() => {
            // approximate last y by rebuilding quickly from last value using local min/max
            let minV = Math.min(...values);
            let maxV = Math.max(...values);
            if (maxV - minV < 1e-9) return h / 2;
            const t = (values[values.length - 1] - minV) / (maxV - minV);
            return h - 7 - (h - 14) * t;
          })()}
          r="3.2"
          fill={stroke}
        />
        {/* tiny axis labels */}
        <text x="7" y={h - 6} fontSize="10" fill="rgba(255,255,255,0.55)">
          1y
        </text>
        <text x={w - 26} y={h - 6} fontSize="10" fill="rgba(255,255,255,0.55)">
          now
        </text>
      </svg>
    </div>
  );
}

// ---- NDJSON fetch + parsing ----

function parseNdjson(text: string): HistoryRow[] {
  const rows: HistoryRow[] = [];
  for (const line of text.split("\n")) {
    const s = line.trim();
    if (!s) continue;
    try {
      rows.push(JSON.parse(s));
    } catch {
      // ignore
    }
  }
  return rows;
}

function buildHistoryMap(rows: HistoryRow[]): HistoryMap {
  // Keys in your weekly history file match your indicator ids:
  // vix, hy_oas, ig_oas, curve_10y2y, spy_dd_1m, kre_dd_3m, recession_risk, credit_stress
  const map: HistoryMap = {};

  for (const r of rows) {
    const wk = typeof r.week === "string" ? r.week : "";
    if (!wk) continue;

    for (const [k, v] of Object.entries(r)) {
      if (k === "week") continue;
      if (typeof v !== "number" || !Number.isFinite(v)) continue;

      if (!map[k]) map[k] = [];
      map[k].push({ week: wk, value: v });
    }
  }

  // Ensure sorted by week
  for (const k of Object.keys(map)) {
    map[k].sort((a, b) => (a.week < b.week ? -1 : a.week > b.week ? 1 : 0));
  }

  return map;
}

function GaugeCard({
  g,
  fallbackAsOf,
  history,
}: {
  g: Gauge;
  fallbackAsOf?: string | null;
  history?: HistoryPoint[];
}) {
  const rot = needleRotationFromPct(g.pct);

  // Prefer per-card updatedAt, otherwise use global asOf, otherwise use existing updatedText
  const updatedLine =
    g.updatedAt ? timeAgo(g.updatedAt) : fallbackAsOf ? timeAgo(fallbackAsOf) : g.updatedText ?? "—";

  return (
    <div className="card" title={g.tooltip}>
      <div className="cardTop">
        <div className="cardTitle">{g.title.toUpperCase()}</div>
        <div className={statusClass(g.status)}>{g.status}</div>
      </div>

      <div
        className="cardBody"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          justifyContent: "space-between",
        }}
      >
        <div className="gaugeWrap" style={{ flex: "0 0 auto" }}>
          <div className="gauge">
            {/* arc */}
            <svg className="arc" viewBox="0 0 200 140" aria-hidden="true">
              {/* Background arc */}
              <path
                d="M 30 110 A 70 70 0 1 1 170 110"
                fill="none"
                stroke="rgba(255,255,255,0.10)"
                strokeWidth="16"
                strokeLinecap="round"
              />
              {/* Green segment */}
              <path
                d="M 30 110 A 70 70 0 0 1 110 42"
                fill="none"
                stroke="rgba(90, 235, 170, 0.85)"
                strokeWidth="16"
                strokeLinecap="round"
              />
              {/* Amber segment */}
              <path
                d="M 110 42 A 70 70 0 0 1 150 68"
                fill="none"
                stroke="rgba(255, 205, 120, 0.80)"
                strokeWidth="16"
                strokeLinecap="round"
              />
              {/* Red segment */}
              <path
                d="M 150 68 A 70 70 0 0 1 170 110"
                fill="none"
                stroke="rgba(255, 120, 120, 0.75)"
                strokeWidth="16"
                strokeLinecap="round"
              />
            </svg>

            {/* labels */}
            <div className="lbl lblMin">{g.minLabel ?? "0"}</div>
            <div className="lbl lblMid">{g.midLabel ?? "50"}</div>
            <div className="lbl lblMax">{g.maxLabel ?? "100"}</div>

            {/* needle */}
            <div className="needleBase">
              <div className="needle" style={{ transform: `rotate(${rot}deg)` }}>
                <div className="needleStem" />
              </div>
              <div className="hub" />
            </div>
          </div>
        </div>

        <div className="readout" style={{ flex: "1 1 auto", minWidth: 0 }}>
          <div className="value">{g.valueText}</div>
          <div className="updated">Updated • {updatedLine}</div>
        </div>

        {/* Sparkline sits on the right */}
        <div style={{ flex: "0 0 auto" }}>
          <Sparkline series={history} status={g.status} />
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [gauges, setGauges] = useState<Gauge[]>(defaultGauges);
  const [asOf, setAsOf] = useState<string | null>(null);

  const [historyMap, setHistoryMap] = useState<HistoryMap>({});

  // Keep the "Updated • x ago" text fresh even if data hasn't changed
  const [, forceTick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => forceTick((x) => x + 1), 60_000); // every minute
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadIndicators() {
      const res = await fetch(`/indicators.json?cb=${Date.now()}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`Fetch indicators.json failed: ${res.status}`);

      const data = (await res.json()) as IndicatorsPayload;
      if (cancelled) return;

      if (Array.isArray(data.cards) && data.cards.length) {
        const mapped = data.cards.map(toGauge).filter(Boolean) as Gauge[];
        if (mapped.length) setGauges(mapped);
      }

      if (typeof data.asOf === "string") setAsOf(data.asOf);
    }

    async function loadHistory() {
      // history_weekly.ndjson is optional early on — fail silently
      const res = await fetch(`/history_weekly.ndjson?cb=${Date.now()}`, { cache: "no-store" });
      if (!res.ok) return;

      const text = await res.text();
      if (cancelled) return;

      const rows = parseNdjson(text);
      const map = buildHistoryMap(rows);
      setHistoryMap(map);
    }

    // initial load
    loadIndicators().catch((e) => console.warn(e));
    loadHistory().catch((e) => console.warn(e));

    // refresh every 5 minutes (indicators), and every 30 minutes (history)
    const t1 = setInterval(() => {
      loadIndicators().catch((e) => console.warn(e));
    }, 5 * 60 * 1000);

    const t2 = setInterval(() => {
      loadHistory().catch((e) => console.warn(e));
    }, 30 * 60 * 1000);

    return () => {
      cancelled = true;
      clearInterval(t1);
      clearInterval(t2);
    };
  }, []);

  const subtitle = useMemo(() => {
    // optional: show something useful later; leaving blank keeps your design clean.
    return "";
  }, []);

  return (
    <div className="page">
      <header className="hero">
        <div className="brand">
          <div className="brandTitle">IN METU VERITAS</div>
          <div className="brandSub">{subtitle}</div>
        </div>
      </header>

      <main className="grid">
        {gauges.map((g) => (
          <GaugeCard
            key={g.key}
            g={g}
            fallbackAsOf={asOf}
            history={historyMap[g.key] ?? historyMap[g.key.toLowerCase()]}
          />
        ))}
      </main>
    </div>
  );
}
