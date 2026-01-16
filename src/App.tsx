import "./App.css";

type Status = "GOOD" | "WARN" | "DELAYED";

type Gauge = {
  key: string;
  title: string;
  status: Status;
  valueText: string;   // e.g. "142 bp"
  updatedText: string; // e.g. "2h 8m ago"
  // 0..100 where 0=far left, 100=far right
  pct: number;
  // labels around dial
  minLabel?: string;
  midLabel?: string;
  maxLabel?: string;
  tooltip: string;
};

const gauges: Gauge[] = [
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

function GaugeCard({ g }: { g: Gauge }) {
  const rot = needleRotationFromPct(g.pct);

  return (
    <div className="card" title={g.tooltip}>
      <div className="cardTop">
        <div className="cardTitle">{g.title.toUpperCase()}</div>
        <div className={statusClass(g.status)}>{g.status}</div>
      </div>

      <div className="cardBody">
        <div className="gaugeWrap">
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

        <div className="readout">
          <div className="value">{g.valueText}</div>
          <div className="updated">Updated • {g.updatedText}</div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <div className="page">
      <header className="hero">
        <div className="brand">
          <div className="brandTitle">IN METU VERITAS</div>
          <div className="brandSub"></div>
        </div>
      </header>

      <main className="grid">
        {gauges.map((g) => (
          <GaugeCard key={g.key} g={g} />
        ))}
      </main>
    </div>
  );
}
