#!/usr/bin/env python3
"""
Update public/indicators.json with daily macro dials.

Dials included (v1):
1) VIX level (proxy for vol regime)               -> FRED (VIXCLS)  ✅ (replaces Stooq)
2) US HY OAS spread (BAMLH0A0HYM2)                -> FRED
3) US IG OAS spread (BAMLC0A0CM)                  -> FRED
4) 10Y-2Y yield curve spread (T10Y2Y)             -> FRED
5) SPY 1M drawdown (21 trading days)              -> Stooq
6) KRE 3M drawdown (63 trading days)              -> Stooq

Added (v2):
7) RECESSION RISK (0–100 composite)               -> FRED (T10Y3M, SAHMREALTIME, RECPROUSM156N)
8) CREDIT STRESS (0–100 composite)                -> FRED (HY/IG/BBB OAS, CPFF, STLFSI4, NFCIRISK)

Notes:
- FRED requires an API key. Set env var FRED_API_KEY (your GitHub Action already does).
- Stooq is used for price series because it's simple and free.
- Composite dials are percentile-based and smoothed using yesterday's indicators.json
  (no database required).
"""

from __future__ import annotations

import bisect
import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone, date
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


def load_previous_payload() -> Dict:
    """Read yesterday's indicators.json if present (for smoothing / continuity)."""
    if OUTFILE.exists():
        try:
            return json.loads(OUTFILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def prev_card_value(prev_payload: Dict, card_id: str) -> Optional[float]:
    """Get previous numeric 'value' for a given card id, if available."""
    try:
        for c in prev_payload.get("cards", []):
            if c.get("id") == card_id:
                v = c.get("value", None)
                if v is None:
                    return None
                return float(v)
    except Exception:
        return None
    return None


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
      - "spy.us" for SPY ETF
      - "kre.us" for KRE ETF
    """
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    txt = http_get_text(url)
    # Stooq returns "No data" sometimes; csv.DictReader will then yield no rows.
    rows = list(csv.DictReader(txt.splitlines()))
    bars: List[PriceBar] = []
    for r in rows:
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
    Fetch latest *valid* observation for a FRED series_id.
    Returns (date, value) or None if unavailable.

    We request multiple observations then pick the first non-missing value,
    because sometimes the latest observation can be ".".
    """
    base = "https://api.stlouisfed.org/fred/series/observations"
    params = f"?series_id={series_id}&file_type=json&sort_order=desc&limit=10"
    if api_key:
        params += f"&api_key={api_key}"
    url = base + params

    try:
        data = json.loads(http_get_text(url))
        obs = data.get("observations", [])
        if not obs:
            return None

        for o in obs:
            v = o.get("value", ".")
            if v in (".", "", None):
                continue
            return (o.get("date", ""), float(v))

        return None
    except Exception:
        return None


def fred_series(series_id: str, api_key: Optional[str], limit: int = 6000, sort_order: str = "asc") -> List[Tuple[str, float]]:
    """
    Fetch up to `limit` observations for a FRED series.
    Returns list of (date, value) sorted ascending by date (default).
    """
    base = "https://api.stlouisfed.org/fred/series/observations"
    params = f"?series_id={series_id}&file_type=json&sort_order={sort_order}&limit={limit}"
    if api_key:
        params += f"&api_key={api_key}"
    url = base + params

    data = json.loads(http_get_text(url))
    out: List[Tuple[str, float]] = []
    for o in data.get("observations", []):
        v = o.get("value", ".")
        if v in (".", "", None):
            continue
        try:
            out.append((o.get("date", ""), float(v)))
        except Exception:
            continue
    out.sort(key=lambda x: x[0])
    return out


def _to_date(s: str) -> date:
    y, m, d = s.split("-")
    return date(int(y), int(m), int(d))


def tail_since(series: List[Tuple[str, float]], years: int = 10) -> List[Tuple[str, float]]:
    """Keep last N years using a date cutoff."""
    if not series:
        return series
    last_d = _to_date(series[-1][0])
    cutoff = last_d.replace(year=last_d.year - years)
    return [(d, v) for (d, v) in series if _to_date(d) >= cutoff]


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


def percentile_score(current: float, history_vals: List[float], invert: bool = False) -> float:
    """
    Map current value to 0-100 percentile in history.
    invert=True means lower is worse (e.g., curve slope), so low values map to high scores.
    """
    if not history_vals:
        return 50.0
    vals = sorted(history_vals)
    r = bisect.bisect_right(vals, current) / len(vals)  # fraction <= current
    if invert:
        r = 1.0 - r
    return clamp(r * 100.0, 0.0, 100.0)


def smooth_with_previous(current: float, prev: Optional[float], alpha: float = 0.20) -> float:
    """
    Simple EWMA smoothing: new = alpha*current + (1-alpha)*prev
    alpha~0.2 gives a calm-ish dial without becoming too laggy.
    """
    if prev is None:
        return current
    return alpha * current + (1.0 - alpha) * prev


def align_by_date(a: List[Tuple[str, float]], b: List[Tuple[str, float]]) -> List[Tuple[str, float, float]]:
    """Inner join by date on two (date,val) series."""
    db = {d: v for d, v in b}
    out = []
    for d, va in a:
        vb = db.get(d)
        if vb is None:
            continue
        out.append((d, va, vb))
    return out


# ----------------------------
# Composite dial builders
# ----------------------------

def build_recession_dial(fred_key: Optional[str]) -> Tuple[Optional[float], str, List[str]]:
    """
    Returns (score_0_100, tooltip, warnings)

    Practical composite:
      - Curve stress: inverted percentile of 10y-3m (T10Y3M) [leading]
      - Sahm Rule realtime (SAHMREALTIME) mapped to 0-100 [near-coincident]
      - Smoothed recession probability (RECPROUSM156N) [coincident-ish]

    Too-early antidote:
      If Sahm < 20 and Coincident < 15, cap curve contribution at 35.
    """
    warnings: List[str] = []

    # 1) Curve: 10y-3m
    curve_score: Optional[float]
    try:
        curve_series = tail_since(fred_series("T10Y3M", fred_key, limit=6000), years=15)
        if not curve_series:
            raise RuntimeError("empty series")
        curve_vals = [v for _, v in curve_series]
        _, curve_now = curve_series[-1]
        curve_score = percentile_score(curve_now, curve_vals, invert=True)
    except Exception as e:
        curve_score = None
        warnings.append(f"Curve(T10Y3M) unavailable: {e}")

    # 2) Sahm Rule realtime
    sahm_score: Optional[float]
    try:
        sahm_series = tail_since(fred_series("SAHMREALTIME", fred_key, limit=5000), years=20)
        if not sahm_series:
            raise RuntimeError("empty series")
        _, sahm_now = sahm_series[-1]
        sahm_score = clamp((sahm_now / 1.0) * 100.0, 0.0, 100.0)
    except Exception as e:
        sahm_score = None
        warnings.append(f"Sahm(SAHMREALTIME) unavailable: {e}")

    # 3) Coincident-ish recession probability
    coin_score: Optional[float]
    try:
        recp_series = tail_since(fred_series("RECPROUSM156N", fred_key, limit=5000), years=20)
        if not recp_series:
            raise RuntimeError("empty series")
        _, recp_now = recp_series[-1]
        coin_score = clamp(recp_now, 0.0, 100.0)
    except Exception as e:
        coin_score = None
        warnings.append(f"Coincident(RECPROUSM156N) unavailable: {e}")

    components: List[Tuple[str, Optional[float], float]] = [
        ("curve", curve_score, 0.50),
        ("sahm", sahm_score, 0.30),
        ("coin", coin_score, 0.20),
    ]
    available = [(name, val, w) for (name, val, w) in components if val is not None]
    if not available:
        return None, "Recession dial unavailable (all components missing).", warnings

    wsum = sum(w for _, _, w in available)
    norm = [(name, float(val), w / wsum) for (name, val, w) in available]

    # Too-early antidote
    sahm_ok = (sahm_score is not None and sahm_score >= 20)
    coin_ok = (coin_score is not None and coin_score >= 15)
    curve_effective = curve_score
    if curve_score is not None and (not sahm_ok) and (not coin_ok):
        curve_effective = min(curve_score, 35.0)

    score = 0.0
    for name, val, w in norm:
        if name == "curve" and curve_effective is not None:
            score += w * curve_effective
        else:
            score += w * val

    tooltip = (
        "Composite recession risk dial (0–100). "
        "Blend: inverted curve stress (T10Y3M), Sahm Rule realtime, and smoothed recession probability. "
        "Curve is capped when labour/coincident confirmation is low."
    )
    if warnings:
        tooltip += " Warnings: " + " | ".join(warnings)

    return clamp(score, 0.0, 100.0), tooltip, warnings


def build_credit_stress_dial(fred_key: Optional[str]) -> Tuple[Optional[float], str, List[str]]:
    """
    Composite 0-100 credit stress using percentiles over ~15y history:
      - HY OAS (BAMLH0A0HYM2)       30%
      - BBB OAS (BAMLC0A4CBBB)     10%
      - HY-IG differential          10%
      - CPFF funding stress         20%
      - STLFSI4                     15%
      - NFCIRISK                    15%

    Momentum kicker:
      If HY OAS ~1m widening is top-decile, add +5 (capped overall).
    """
    warnings: List[str] = []

    def get_pct_score(series_id: str, years: int = 15) -> Optional[float]:
        try:
            s = tail_since(fred_series(series_id, fred_key, limit=6000), years=years)
            if not s:
                return None
            vals = [v for _, v in s]
            _, now = s[-1]
            return percentile_score(now, vals, invert=False)
        except Exception as e:
            warnings.append(f"{series_id} unavailable: {e}")
            return None

    hy_score = get_pct_score("BAMLH0A0HYM2", years=15)
    bbb_score = get_pct_score("BAMLC0A4CBBB", years=15)

    # HY-IG differential
    hy_ig_score: Optional[float] = None
    try:
        hy_s = tail_since(fred_series("BAMLH0A0HYM2", fred_key, limit=6000), years=15)
        ig_s = tail_since(fred_series("BAMLC0A0CM", fred_key, limit=6000), years=15)
        joined = align_by_date(hy_s, ig_s)
        diffs = [(d, (hy - ig)) for (d, hy, ig) in joined]
        if diffs:
            vals = [v for _, v in diffs]
            _, now = diffs[-1]
            hy_ig_score = percentile_score(now, vals, invert=False)
    except Exception as e:
        warnings.append(f"HY-IG diff unavailable: {e}")

    cpff_score = get_pct_score("CPFF", years=15)
    stlfsi_score = get_pct_score("STLFSI4", years=15)
    nfci_risk_score = get_pct_score("NFCIRISK", years=15)

    weights = [
        ("HY OAS", hy_score, 0.30),
        ("BBB OAS", bbb_score, 0.10),
        ("HY-IG", hy_ig_score, 0.10),
        ("CPFF", cpff_score, 0.20),
        ("STLFSI4", stlfsi_score, 0.15),
        ("NFCIRISK", nfci_risk_score, 0.15),
    ]
    available = [(n, v, w) for (n, v, w) in weights if v is not None]
    if not available:
        return None, "Credit stress dial unavailable (all components missing).", warnings

    wsum = sum(w for _, _, w in available)
    score = sum((w / wsum) * float(v) for _, v, w in available)

    # Momentum kicker: HY OAS widening over ~1 month
    try:
        hy_s = tail_since(fred_series("BAMLH0A0HYM2", fred_key, limit=6000), years=15)
        if len(hy_s) > 40:
            now = hy_s[-1][1]
            prev = hy_s[-31][1]  # rough 1 month (calendar obs in daily series)
            chg = now - prev
            chgs = []
            for i in range(31, len(hy_s)):
                chgs.append(hy_s[i][1] - hy_s[i - 31][1])
            pct = percentile_score(chg, chgs, invert=False)
            if pct >= 90.0:
                score += 5.0
    except Exception as e:
        warnings.append(f"HY momentum kicker unavailable: {e}")

    score = clamp(score, 0.0, 100.0)

    tooltip = (
        "Composite credit stress dial (0–100, percentile-based). "
        "Blend of HY/BBB spreads, HY–IG repricing, CPFF funding stress, STLFSI4 and NFCIRISK. "
        "Adds a small kicker when HY spreads widen rapidly."
    )
    if warnings:
        tooltip += " Warnings: " + " | ".join(warnings)

    return score, tooltip, warnings


# ----------------------------
# Main dial construction
# ----------------------------

def make_cards() -> Dict:
    as_of = utc_now_iso()
    fred_key = os.environ.get("FRED_API_KEY", "").strip() or None
    prev_payload = load_previous_payload()

    cards = []

    # 1) VIX (FRED: VIXCLS)  ✅ replaces Stooq because Stooq often returns "No data"
    vix = fred_latest("VIXCLS", fred_key)
    if vix:
        _, vix_val = vix
        cards.append({
            "id": "vix",
            "type": "gauge",
            "title": "VOLATILITY (VIX)",
            "status": status_from_band(vix_val, good_max=18, warn_max=28, higher_is_worse=True),
            "value": round(vix_val, 1),
            "unit": "",
            "min": 10,
            "max": 40,
            "minLabel": "10",
            "midLabel": "20",
            "maxLabel": "40",
            "tooltip": "CBOE VIX close from FRED (VIXCLS). Higher = riskier.",
            "updatedAt": as_of
        })
    else:
        cards.append({
            "id": "vix",
            "type": "gauge",
            "title": "VOLATILITY (VIX)",
            "status": "DELAYED",
            "valueText": "FRED key?",
            "pct": 50,
            "minLabel": "10",
            "midLabel": "20",
            "maxLabel": "40",
            "tooltip": "Could not fetch FRED series VIXCLS. Check env var FRED_API_KEY.",
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
        dd1m = float(dd1m)
        status = "GOOD"
        if dd1m <= -6:
            status = "WARN"
        if dd1m <= -10:
            status = "DELAYED"
        cards.append({
            "id": "spy_dd_1m",
            "type": "gauge",
            "title": "EQUITY DRAWDOWN (SPY, 1M)",
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

    # 7) RECESSION RISK (Composite 0–100)
    try:
        rec_score, rec_tooltip, _ = build_recession_dial(fred_key)
        if rec_score is None:
            raise RuntimeError("missing components")
        prev = prev_card_value(prev_payload, "recession_risk")
        rec_sm = smooth_with_previous(rec_score, prev, alpha=0.20)

        cards.append({
            "id": "recession_risk",
            "type": "gauge",
            "title": "RECESSION RISK",
            "status": "GOOD" if rec_sm < 35 else ("WARN" if rec_sm < 60 else "DELAYED"),
            "value": round(rec_sm, 0),
            "unit": "",
            "min": 0,
            "max": 100,
            "minLabel": "Low",
            "midLabel": "Elevated",
            "maxLabel": "High",
            "tooltip": rec_tooltip,
            "updatedAt": as_of
        })
    except Exception as e:
        cards.append({
            "id": "recession_risk",
            "type": "gauge",
            "title": "RECESSION RISK",
            "status": "DELAYED",
            "valueText": "—",
            "pct": 50,
            "minLabel": "Low",
            "midLabel": "Elevated",
            "maxLabel": "High",
            "tooltip": f"Recession dial build failed: {e}",
            "updatedAt": as_of
        })

    # 8) CREDIT STRESS (Composite 0–100)
    try:
        cs_score, cs_tooltip, _ = build_credit_stress_dial(fred_key)
        if cs_score is None:
            raise RuntimeError("missing components")
        prev = prev_card_value(prev_payload, "credit_stress")
        cs_sm = smooth_with_previous(cs_score, prev, alpha=0.20)

        cards.append({
            "id": "credit_stress",
            "type": "gauge",
            "title": "CREDIT STRESS",
            "status": "GOOD" if cs_sm < 40 else ("WARN" if cs_sm < 65 else "DELAYED"),
            "value": round(cs_sm, 0),
            "unit": "",
            "min": 0,
            "max": 100,
            "minLabel": "Easy",
            "midLabel": "Tightening",
            "maxLabel": "Crisis",
            "tooltip": cs_tooltip,
            "updatedAt": as_of
        })
    except Exception as e:
        cards.append({
            "id": "credit_stress",
            "type": "gauge",
            "title": "CREDIT STRESS",
            "status": "DELAYED",
            "valueText": "—",
            "pct": 50,
            "minLabel": "Easy",
            "midLabel": "Tightening",
            "maxLabel": "Crisis",
            "tooltip": f"Credit stress dial build failed: {e}",
            "updatedAt": as_of
        })

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
