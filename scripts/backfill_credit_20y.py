#!/usr/bin/env python3
"""Separate long-history research dataset for HY and IG OAS.

Does not modify history_5y.ndjson or dashboard indicator snapshots.
Uses FRED observation dates, without forward-filling.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from update_indicators import fred_series

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "public" / "credit_history_20y.ndjson"
SOURCES = {"hy_oas": "BAMLH0A0HYM2", "ig_oas": "BAMLC0A0CM"}
YEARS = 20
# 20 calendar years include roughly 5,200 weekday observations.
OBS_LIMIT = 7500

def build(today: date | None = None, loader=None, output: Path = OUTPUT):
    today = today or datetime.now(timezone.utc).date()
    start = date(today.year - YEARS, today.month, min(today.day, 28))
    # Old data are retained if one remote provider is temporarily unavailable.
    records = {}
    if output.exists():
        for line in output.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
                day = row.get("date", "")
                if isinstance(day, str) and start.isoformat() <= day <= today.isoformat():
                    records[day] = {k: row[k] for k in ("date", "hy_oas", "ig_oas") if k in row}
            except (ValueError, TypeError):
                continue

    if loader is None:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            raise RuntimeError("FRED_API_KEY is required for the credit archive")
        loader = lambda series: fred_series(series, api_key, limit=OBS_LIMIT, sort_order="desc")

    refreshed = 0
    for key, series_id in SOURCES.items():
        try:
            values = [(d, float(v)) for d, v in loader(series_id)]
            # Require full-length credible coverage before treating a truncated
            # response as a successful replacement.
            valid = [(d, v) for d, v in values if start.isoformat() <= d <= today.isoformat()]
            if len(valid) < 400:
                raise ValueError(f"Only {len(valid)} dated observations returned")
            for day, percent in valid:
                records.setdefault(day, {"date": day})[key] = round(percent * 100, 2)
            refreshed += 1
            print(f"{key}: {len(valid)} dated FRED observations")
        except Exception as exc:
            print(f"WARNING: {key} refresh failed: {exc}; previously archived values retained", file=sys.stderr)

    if refreshed == 0:
        raise RuntimeError("No FRED credit series refreshed; archive not rewritten")

    rows = [row for day, row in sorted(records.items()) if start.isoformat() <= day <= today.isoformat() and len(row) > 1]
    if not rows:
        raise RuntimeError("No historical observations available")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")
    print(f"Saved {len(rows)} dated observations to {output}")

if __name__ == "__main__":
    build()
