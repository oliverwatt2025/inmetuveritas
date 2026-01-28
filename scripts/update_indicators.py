#!/usr/bin/env python3
"""
Update public/indicators.json with daily macro dials.

Dials included (v1):
1) VIX level (proxy for vol regime)               -> Stooq
2) US HY OAS spread (BAMLH0A0HYM2)                -> FRED
3) US IG OAS spread (BAMLC0A0CM)                  -> FRED
4) 10Y-2Y yield curve spread (T10Y2Y)             -> FRED
5) SPY 1M drawdown (21 trading days)              -> Stooq
6) KRE 3M drawdown (63 trading days)              -> Stooq

Notes:
- FRED usually requires an API key. Set env var FRED_API_KEY.
- Stooq is used for price series because it's simple and free.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import urllib.request


ROOT = Path(__file__).resolve().parents[1]
OUTFILE = ROOT / "public" / "indicators.json"


# ----------------------------
# Utilities
# ----------------------------

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def http_get_text(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "inmetuveritas/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


# ----------------------------
# Stooq (prices) helpers
# ----------------------------

@dataclass
class PriceBar:
    date: str
    close: float


def stooq_daily_closes(symbol: str) -> List[PriceBar]:
    """
    Fetch daily OHLC from Stooq CSV and return closes sorted ascending by date.
    Example symbols:
      - "^vix" for VIX
      - "spy.us" for SPY ETF
      - "kre.us" for KRE ETF
    """
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    txt = http_get_text(url)
    rows = list(csv.DictReader(txt.splitlines()))
    bars: List[PriceBar] = []
    for r in rows:
        # Stooq uses columns: Date, Open, High, Low, Close, Volume
        try:
            bars.append(PriceBar(date=r["Date"], close=float(r["Close"])))
        except Exception:
            continue
    bars.sort(key=lambda b: b.date)
    return bars


def drawdown_pct(bars: List[PriceBar], lookback_days: int) -> Optional[float]:
    """
    Drawdown from the max close in the last lookback_days to the latest close.
    Returns negative percent (e.g., -6.2) or 0 if at highs.
    """
    if len(bars) < max(5, lookback_days):
        return None
    window = bars[-lookback_days:]
    closes = [b.close for b in window]
    peak = max(closes)
    last = closes[-1]
    if peak <= 0:
        return None
    dd = (last / peak - 1.0) * 100.0
    return dd


# ----------------------------
# FRED helpers
# ----------------------------

def fred_latest(series_id: str, api_key: Optional[str]) -> Optional[Tuple[str, float]]:
    """
    Fetch latest observation for a FRED series_id.
    Returns (date, value) or None if unavailable.
    """
    # FRED API:
    # https://api.stlouisfed.org/fred/series/observations?series_id=...&api_key=...&file_type=json&sort_order=desc&limit=1
    base = "https://api.stlouisfed.org/fred/series/observations"
    params = f"?series_id={series_id}&file_type=json&sort_order=desc&limit=1"
    if api_key:
        params += f"&api_key={api_key}"
    url = base + params
    try:
        data = json.loads(http_get_text(url))
        obs = data.get("observations", [])
        if not obs:
            return None
        o = obs[0]
        v = o.get("value", ".")
        if v in (".", "", None):
            return None
        return (o.get("date", ""), float(v))
    except Exception:
        return None


# ----------------------------
# Dial construction
# ----------------------------

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def status_from_band(value: float, good_max: float, warn_max: float, higher_is_worse: bool = True) -> str:
    """
    Simple thresholding:
    - GOOD if within good band
    - WARN if within warn band
    - DELAYED if worse
    """
    if higher_is_worse:
        if value <= good_max:
            return "GOOD"
        if value <= warn_max:
            return "WARN"
        return "DELAYED"
    else:
        # lower is worse
        if value >= good_max:
            return "GOOD"
        if value >= warn_max:
            return "WARN"
        return "DELAYED"


def dial_from_minmax(value: float, min_v: float, max_v: float) -> float:
    if max_v == min_v:
        return 50.0
    pct = (value - min_v) / (max_v - min_v) * 100.0
    return clamp(pct, 0.0, 100.0)


def make_cards() -> Dict:
    as_of = utc_now_iso()
    fred_key = os.environ.get("FRED_API_KEY", "").strip() or None

    cards = []

    # 1) VIX (Stooq)
    try:
        vix = stooq_daily_closes("^vix")
        vix_last = vix[-1].close
        cards.append({
            "id": "vix",
            "type": "gauge",
            "title": "VOLATILITY (VIX)",
            "status": status_from_band(vix_last, good_max=18, warn_max=28, higher_is_worse=True),
            "value": round(vix_last, 1),
            "unit": "",
            "min": 10,
            "max": 40,
            "minLabel": "10",
            "midLabel": "20",
            "maxLabel": "40",
            "tooltip": "VIX level (proxy for risk aversion / vol regime). Higher = riskier.",
            "updatedAt": as_of
        })
    except Exception as e:
        cards.append({
            "id": "vix",
            "type": "gauge",
            "title": "VOLATILITY (VIX)",
            "status": "DELAYED",
            "valueText": "—",
            "pct": 50,
            "minLabel": "10",
            "midLabel": "20",
            "maxLabel": "40",
            "tooltip": f"VIX fetch failed: {e}",
            "updatedAt": as_of
        })

    # 2) HY OAS (FRED)
    hy = fred_latest("BAMLH0A0HYM2", fred_key)  # ICE BofA US High Yield OAS
    if hy:
        _, hy_val = hy
        hy_bp = hy_val * 100.0  # percent -> bp
        cards.append({
            "id": "hy_oas",
            "type": "gauge",
            "title": "HIGH YIELD SPREAD (OAS)",
            "status": status_from_band(hy_bp, good_max=350, warn_max=500, higher_is_worse=True),
            "value": round(hy_bp, 0),
            "unit": " bp",
            "min": 250,
            "max": 800,
            "minLabel": "250",
            "midLabel": "500",
            "maxLabel": "800",
            "tooltip": "HY OAS from FRED (ICE BofA). Higher = tighter financial conditions / more stress.",
            "updatedAt": as_of
        })
    else:
        cards.append({
            "id": "hy_oas",
            "type": "gauge",
            "title": "HIGH YIELD SPREAD (OAS)",
            "status": "DELAYED",
            "valueText": "FRED key?",
            "pct": 50,
            "minLabel": "250",
            "midLabel": "500",
            "maxLabel": "800",
            "tooltip": "Could not fetch FRED series BAMLH0A0HYM2. Set env var FRED_API_KEY.",
            "updatedAt": as_of
        })

    # 3) IG OAS (FRED)
    ig = fred_latest("BAMLC0A0CM", fred_key)  # ICE BofA US Corporate OAS
    if ig:
        _, ig_val = ig
        ig_bp = ig_val * 100.0
        cards.append({
            "id": "ig_oas",
            "type": "gauge",
            "title": "INVESTMENT GRADE SPREAD (OAS)",
            "status": status_from_band(ig_bp, good_max=130, warn_max=200, higher_is_worse=True),
            "value": round(ig_bp, 0),
            "unit": " bp",
            "min": 80,
            "max": 300,
            "minLabel": "80",
            "midLabel": "180",
            "maxLabel": "300",
            "tooltip": "IG OAS from FRED (ICE BofA). Higher = tighter conditions / credit stress.",
            "updatedAt": as_of
        })
    else:
        cards.append({
            "id": "ig_oas",
            "type": "gauge",
            "title": "INVESTMENT GRADE SPREAD (OAS)",
            "status": "DELAYED",
            "valueText": "FRED key?",
            "pct": 50,
            "minLabel": "80",
            "midLabel": "180",
            "maxLabel": "300",
            "tooltip": "Could not fetch FRED series BAMLC0A0CM. Set env var FRED_API_KEY.",
            "updatedAt": as_of
        })

    # 4) 10Y-2Y curve (FRED)
    curve = fred_latest("T10Y2Y", fred_key)  # 10-Year Treasury Constant Maturity Minus 2-Year
    if curve:
        _, c_val = curve
        c_bp = c_val * 100.0  # percent -> bp
        # Here, more negative is worse; we treat "higher is better"
        status = status_from_band(c_bp, good_max=0, warn_max=-50, higher_is_worse=False)
        cards.append({
            "id": "curve_10y2y",
            "type": "gauge",
            "title": "YIELD CURVE (10Y–2Y)",
            "status": status,
            "value": round(c_bp, 0),
            "unit": " bp",
            "min": -200,
            "max": 200,
            "minLabel": "-200",
            "midLabel": "0",
            "maxLabel": "200",
            "tooltip": "10Y–2Y spread from FRED. More negative (inversion) = growth risk signal.",
            "updatedAt": as_of
        })
    else:
        cards.append({
            "id": "curve_10y2y",
            "type": "gauge",
            "title": "YIELD CURVE (10Y–2Y)",
            "status": "DELAYED",
            "valueText": "FRED key?",
            "pct": 50,
            "minLabel": "-200",
            "midLabel": "0",
            "maxLabel": "200",
            "tooltip": "Could not fetch FRED series T10Y2Y. Set env var FRED_API_KEY.",
            "updatedAt": as_of
        })

    # 5) SPY 1M drawdown (Stooq, 21 trading days)
    try:
        spy = stooq_daily_closes("spy.us")
        dd1m = drawdown_pct(spy, lookback_days=21)
        if dd1m is None:
            raise RuntimeError("not enough SPY data")
        # drawdown is negative or 0
        dd1m = float(dd1m)
        # Status: bigger drawdown = worse
        status = "GOOD"
        if dd1m <= -6:
            status = "WARN"
        if dd1m <= -10:
            status = "DELAYED"
        cards.append({
            "id": "spy_dd_1m",
            "type": "gauge",
            "title": "EQUITY DRAWdown (SPY, 1M)",
            "status": status,
            "value": round(dd1m, 1),
            "unit": "%",
            "min": -20,
            "max": 0,
            "minLabel": "-20%",
            "midLabel": "-10%",
            "maxLabel": "0%",
            "tooltip": "SPY drawdown from 1M peak (21 trading days). More negative = risk-off.",
            "updatedAt": as_of
        })
    except Exception as e:
        cards.append({
            "id": "spy_dd_1m",
            "type": "gauge",
            "title": "EQUITY DRAWDOWN (SPY, 1M)",
            "status": "DELAYED",
            "valueText": "—",
            "pct": 50,
            "minLabel": "-20%",
            "midLabel": "-10%",
            "maxLabel": "0%",
            "tooltip": f"SPY fetch failed: {e}",
            "updatedAt": as_of
        })

    # 6) KRE 3M drawdown (Stooq, 63 trading days)
    try:
        kre = stooq_daily_closes("kre.us")
        dd3m = drawdown_pct(kre, lookback_days=63)
        if dd3m is None:
            raise RuntimeError("not enough KRE data")
        dd3m = float(dd3m)
        status = "GOOD"
        if dd3m <= -8:
            status = "WARN"
        if dd3m <= -15:
            status = "DELAYED"
        cards.append({
            "id": "kre_dd_3m",
            "type": "gauge",
            "title": "REGIONAL BANKS DRAWDOWN (KRE, 3M)",
            "status": status,
            "value": round(dd3m, 1),
            "unit": "%",
            "min": -30,
            "max": 0,
            "minLabel": "-30%",
            "midLabel": "-15%",
            "maxLabel": "0%",
            "tooltip": "KRE drawdown from 3M peak (63 trading days). More negative = bank stress proxy.",
            "updatedAt": as_of
        })
    except Exception as e:
        cards.append({
            "id": "kre_dd_3m",
            "type": "gauge",
            "title": "REGIONAL BANKS DRAWDOWN (KRE, 3M)",
            "status": "DELAYED",
            "valueText": "—",
            "pct": 50,
            "minLabel": "-30%",
            "midLabel": "-15%",
            "maxLabel": "0%",
            "tooltip": f"KRE fetch failed: {e}",
            "updatedAt": as_of
        })

    # Build payload
    return {
        "asOf": as_of,
        "cards": cards
    }


def main() -> int:
    payload = make_cards()
    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTFILE} with asOf={payload['asOf']} and {len(payload['cards'])} cards.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
