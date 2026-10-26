#!/usr/bin/env python3
"""Publish non-sensitive archive-health metadata, never raw credit observations."""
from __future__ import annotations
import json,os
from datetime import datetime,timezone
from pathlib import Path
from cryptography.fernet import Fernet
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"research"/"private_data"/"credit_archive.fernet"

OUT=Path(__file__).resolve().parents[1]/"public"/"archive_health.json"
KEYS=("hy_oas","ig_oas")

def summary(rows,as_of):
    result={}
    for key in KEYS:
        dates=sorted(r["date"] for r in rows if isinstance(r,dict) and isinstance(r.get("date"),str) and key in r)
        result[key]={"count":len(dates),"earliest":dates[0] if dates else None,"latest":dates[-1] if dates else None}
    return {"asOf":as_of,"status":"collected","series":result,
            "note":"Counts and observation dates only; underlying observations are encrypted and are not published."}

def publish(archive=PATH,output=OUT,key=None,now=None):
    token=key or os.environ.get("CREDIT_ARCHIVE_KEY")
    if not token:raise RuntimeError("CREDIT_ARCHIVE_KEY unavailable")
    cipher=Fernet(token.encode() if isinstance(token,str) else token)
    rows=json.loads(cipher.decrypt(archive.read_bytes()))
    if not isinstance(rows,list):raise ValueError("Invalid archive contents")
    stamp=now or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    result=summary(rows,stamp)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("Published archive health counts and dates only")
    return result

if __name__=="__main__":publish()
