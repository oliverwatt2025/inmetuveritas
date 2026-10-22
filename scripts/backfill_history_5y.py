#!/usr/bin/env python3
"""Five-year, dated market observations. Does not alter dashboard snapshot histories.

Sources: FRED published observations and Yahoo daily ETF closing prices.
Missing provider responses leave the previous five-year file intact for that series.
"""
from __future__ import annotations
import json, os, sys, urllib.request
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from update_indicators import fred_series

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "public" / "history_5y.ndjson"
FRED = {"vix":"VIXCLS","hy_oas":"BAMLH0A0HYM2",
        "ig_oas":"BAMLC0A0CM","curve_10y2y":"T10Y2Y"}
LIMIT_DAYS = 5 * 366

def yahoo(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5y&interval=1d"
    req=urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 inmetuveritas-research/1.0"})
    with urllib.request.urlopen(req,timeout=30) as response:
        data=json.load(response)
    result=(data.get("chart",{}).get("result") or [None])[0]
    if not result: raise ValueError(f"No Yahoo result for {symbol}")
    times=result.get("timestamp") or []
    quotes=(result.get("indicators",{}).get("quote") or [{}])[0].get("close") or []
    return {datetime.fromtimestamp(ts,timezone.utc).date().isoformat():float(close)
            for ts,close in zip(times,quotes) if isinstance(close,(float,int)) and close>0}

def derived(prices,lookback,method):
    days=sorted(prices)
    out={}
    for i in range(lookback-1,len(days)):
        dates=days[i-lookback+1:i+1]
        vals=[prices[k] for k in dates]
        if method=="drawdown":
            out[days[i]]=round((vals[-1]/max(vals)-1)*100,2)
        elif method=="return":
            out[days[i]]=round((vals[-1]/vals[0]-1)*100,3)
    return out

def backfill(today=None, load_fred=None, load_yahoo=None):
    today=today or datetime.now(timezone.utc).date()
    cutoff=today-timedelta(days=LIMIT_DAYS)
    old={}
    if PATH.exists():
        for line in PATH.read_text(encoding="utf-8").splitlines():
            try:
                row=json.loads(line)
                if isinstance(row.get("date"),str): old[row["date"]]=row
            except (ValueError,TypeError):
                continue
    merged={day:{"date":day,**row} for day,row in old.items()
            if cutoff.isoformat()<=day<=today.isoformat()}
    updates=0
    api_key=os.environ.get("FRED_API_KEY")
    load_fred=load_fred or (lambda sid:fred_series(sid,api_key,limit=2300,sort_order="desc"))
    load_yahoo=load_yahoo or yahoo
    for key,series in FRED.items():
        try:
            data={d:round(float(v)*(100 if key in ("hy_oas","ig_oas","curve_10y2y") else 1),2)
                  for d,v in load_fred(series)}
            if len(data)<200: raise ValueError(f"Only {len(data)} FRED observations")
            for day,val in data.items():
                if cutoff.isoformat()<=day<=today.isoformat():
                    merged.setdefault(day,{"date":day})[key]=val
            updates+=1
            print(f"{key}: {len(data)} FRED observations")
        except Exception as exc:
            print(f"WARNING: {key}: {exc}; previous observations preserved",file=sys.stderr)
    prices={}
    for symbol in ("SPY","RSP","KRE"):
        try:
            prices[symbol]=load_yahoo(symbol)
            if len(prices[symbol])<200: raise ValueError("Insufficient observations")
            updates+=1
            print(f"{symbol}: {len(prices[symbol])} ETF closes")
        except Exception as exc:
            prices.pop(symbol,None)
            print(f"WARNING: {symbol}: {exc}; previous observations preserved",file=sys.stderr)
    if "SPY" in prices:
        for d,v in derived(prices["SPY"],21,"drawdown").items():
            merged.setdefault(d,{"date":d})["spy_dd_1m"]=v
    if "KRE" in prices:
        for d,v in derived(prices["KRE"],63,"drawdown").items():
            merged.setdefault(d,{"date":d})["kre_dd_3m"]=v
    if "SPY" in prices and "RSP" in prices:
        a,b=derived(prices["SPY"],21,"return"),derived(prices["RSP"],21,"return")
        for d in set(a)&set(b):
            merged.setdefault(d,{"date":d})["breadth"]=round(b[d]-a[d],2)
    if updates==0: raise RuntimeError("Every historical provider failed; file left unchanged")
    ordered=[]
    for day,row in sorted(merged.items()):
        if day < cutoff.isoformat() or day > today.isoformat():continue
        # Dated source observations, not artificial weekend carrying-forward.
        if len(row)>1:ordered.append(row)
    if not ordered: raise RuntimeError("No historical observations; file left unchanged")
    PATH.write_text("".join(json.dumps(row,separators=(",",":"))+"\n" for row in ordered),encoding="utf-8")
    print(f"Saved {len(ordered)} actual observation dates to {PATH.name}")

if __name__=="__main__":
    backfill()
