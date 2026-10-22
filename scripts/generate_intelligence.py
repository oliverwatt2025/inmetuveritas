#!/usr/bin/env python3
"""Evidence-first market intelligence report from existing dashboard snapshots.

No network calls, AI guesses or modifications to existing indicators.
Run: python3 scripts/generate_intelligence.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "public" / "indicators.json"
OUTPUT = ROOT / "public" / "market_intelligence.json"

def build_report(payload: dict, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    cards = {c.get("id"): c for c in payload.get("cards", []) if isinstance(c, dict)}
    asof = payload.get("asOf")
    if not isinstance(asof, str):
        raise ValueError("Missing indicator snapshot timestamp")
    source_time = datetime.fromisoformat(asof.replace("Z", "+00:00"))
    if source_time.tzinfo is None:
        raise ValueError("Source timestamp must include timezone")
    age_hours = max(0.0, (now - source_time).total_seconds() / 3600)
    stale_snapshot = age_hours > 36

    def numeric(key):
        c = cards.get(key)
        if not c or type(c.get("value")) not in (float, int):
            return None
        if c.get("status") == "DELAYED" and key not in ("credit_stress", "recession_risk"):
            return None
        return float(c["value"])

    signals = []
    def add(code, family, severity, headline, explanation, ids):
        signals.append({"id":code,"family":family,"severity":severity,
                        "headline":headline,"explanation":explanation,
                        "evidence":[{"indicator":key,"value":numeric(key),"unit":cards[key].get("unit",""),
                                     "observedAt":cards[key].get("updatedAt") or asof}
                                    for key in ids]})

    breadth, spy = numeric("breadth"), numeric("spy_dd_1m")
    vix, hy, ig = numeric("vix"), numeric("hy_oas"), numeric("ig_oas")
    banks = numeric("kre_dd_3m")
    if breadth is not None and spy is not None:
        if breadth <= -1.5 and spy >= -4:
            add("narrow_leadership","equities","attention","Index resilience has narrow participation",
                "Equal-weight equities trail the cap-weighted index even as its recent drawdown remains modest.",
                ["breadth","spy_dd_1m"])
        elif breadth >= 1.5:
            add("broad_participation","equities","supportive","Equal-weight participation is supportive",
                "Equal-weight equities have outperformed the cap-weighted benchmark over the measurement window.",
                ["breadth"])
    if hy is not None and ig is not None:
        if hy >= 500 or ig >= 160:
            add("credit_pressure","credit","attention","Credit pricing shows elevated pressure",
                "One or more corporate-bond spread measures is above a predetermined watch threshold.",
                ["hy_oas","ig_oas"])
        elif hy <= 400 and ig <= 120:
            add("credit_contained","credit","supportive","Corporate credit spreads remain contained",
                "Both investment-grade and high-yield spreads are below the defined watch thresholds.",
                ["hy_oas","ig_oas"])
    if vix is not None:
        if vix >= 25:
            add("volatility_elevated","volatility","attention","Equity-implied volatility is elevated",
                "VIX exceeds the stated watch threshold; this is not a forecast of future returns.",["vix"])
        elif vix <= 20:
            add("volatility_calm","volatility","supportive","Options markets imply relatively calm conditions",
                "VIX is below the defined watch threshold.",["vix"])
    if banks is not None and banks <= -12:
        add("regional_banks_weak","banks","attention","Regional-bank equities are under pressure",
            "The KRE drawdown breaches the monitoring threshold; this is an equity proxy, not direct proof of banking-system distress.",
            ["kre_dd_3m"])

    attention = [x for x in signals if x["severity"] == "attention"]
    supportive = [x for x in signals if x["severity"] == "supportive"]
    families = sorted({x["family"] for x in attention})
    if stale_snapshot or len(signals) < 2:
        regime = "INSUFFICIENT CURRENT EVIDENCE"
        summary = "The available observations are too old or incomplete for a current cross-market conclusion."
    elif len(families) >= 2 and (vix is not None and vix >= 25 or hy is not None and hy >= 500):
        regime = "ELEVATED CAUTION"
        summary = "Multiple market areas show concern; compare the confirming evidence before interpreting this as systemic stress."
    elif attention and supportive:
        regime = "MIXED SIGNALS"
        summary = "Some measures suggest vulnerability while other market areas remain comparatively resilient."
    elif attention:
        regime = "SELECTIVE CAUTION"
        summary = "At least one risk signal warrants attention, without enough independent evidence for a broader stress conclusion."
    else:
        regime = "NO BROAD STRESS CONFIRMATION"
        summary = "The monitored signals do not currently show broad stress; this is not a forecast or assurance."

    watch = []
    if hy is not None and hy < 500: watch.append("Watch for sustained high-yield spread widening, not just a one-day move.")
    if vix is not None and vix < 25: watch.append("Watch whether a sustained VIX increase confirms weakness elsewhere.")
    if breadth is not None: watch.append("Compare equal-weight participation with headline index moves and credit pricing.")

    report = {
        "schemaVersion":1, "sourceAsOf":asof, "generatedAt":now.isoformat().replace("+00:00","Z"),
        "dataAgeHours":round(age_hours,1), "dataQuality":"STALE" if stale_snapshot else "CURRENT",
        "regime":regime, "summary":summary,
        "keyFindings":(attention+supportive)[:5],
        "whatWouldChangeTheView":watch[:3],
        "methodology":"Transparent illustrative rules, not a calibrated prediction or investment advice.",
        "limitations":["Scores and thresholds are provisional and require historical validation.",
                       "Credit-stress and recession composite scores are excluded from independent evidence counts.",
                       "No conclusions about causality are inferred from coincident indicator movements.",
                       "Input card values are snapshot-level, not necessarily underlying observation publication dates."]
    }
    return report

def main():
    payload = json.loads(INPUT.read_text(encoding="utf-8"))
    report = build_report(payload)
    OUTPUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(report["regime"], "from", report["sourceAsOf"], "quality:", report["dataQuality"])

if __name__ == "__main__":
    main()
