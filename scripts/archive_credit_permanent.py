#!/usr/bin/env python3
"""Maintain a durable encrypted HY/IG research archive, independently of public histories.

Requires CREDIT_ARCHIVE_KEY (a Fernet key) from GitHub Actions secrets.
Only the encrypted .fernet bytes are committed. Existing dated observations never
expire, and existing readings are preserved rather than overwritten by revisions.
"""
from __future__ import annotations
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

sys.path.insert(0,str(Path(__file__).resolve().parent))
from update_indicators import fred_series

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"research"/"private_data"/"credit_archive.fernet"
SOURCE={"hy_oas":"BAMLH0A0HYM2","ig_oas":"BAMLC0A0CM"}

def merge_rows(existing, fresh):
    """Add previously unseen dates only, never delete or revise historical dates."""
    merged={str(row["date"]):dict(row) for row in existing if isinstance(row,dict) and "date" in row}
    added=0
    for key, series in fresh.items():
        for d, value in series:
            if not isinstance(d,str) or len(d)!=10:continue
            try:
                datetime.strptime(d,"%Y-%m-%d")
                value=round(float(value)*100,2)
            except (TypeError,ValueError):continue
            record=merged.setdefault(d,{"date":d})
            if key not in record:
                record[key]=value
                added+=1
    return [merged[d] for d in sorted(merged)],added

def update(path=PATH,loader=None,key=None):
    token=key or os.environ.get("CREDIT_ARCHIVE_KEY")
    if not token:raise RuntimeError("Missing CREDIT_ARCHIVE_KEY; archive untouched")
    cipher=Fernet(token.encode() if isinstance(token,str) else token)
    old=[]
    if path.exists():
        try:
            data=json.loads(cipher.decrypt(path.read_bytes()))
            if not isinstance(data,list):raise ValueError("Archive is not a list")
            old=data
        except (InvalidToken,ValueError) as exc:
            raise RuntimeError("Unable to authenticate existing archive; refusing overwrite") from exc
    if loader is None:
        fred_key=os.environ.get("FRED_API_KEY")
        if not fred_key:raise RuntimeError("Missing FRED_API_KEY")
        loader=lambda sid:fred_series(sid,fred_key,limit=1100,sort_order="desc")
    fresh={}
    for indicator,sid in SOURCE.items():
        try:
            result=loader(sid)
            if len(result)<100:raise ValueError(f"Too few observations: {len(result)}")
            fresh[indicator]=result
        except Exception as exc:
            print(f"WARNING: {indicator} request failed: {exc}",file=sys.stderr)
    if not fresh:raise RuntimeError("All FRED requests failed; archive preserved")
    merged,added=merge_rows(old,fresh)
    if not merged:raise RuntimeError("No valid observations; archive preserved")
    if added==0 and path.exists():
        print(f"No new observations; preserved {len(old)} dated rows")
        return
    path.parent.mkdir(parents=True,exist_ok=True)
    import tempfile
    encrypted=cipher.encrypt(json.dumps(merged,separators=(",",":")).encode())
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as temp:
        temp.write(encrypted)
        name=temp.name
    os.replace(name,path)
    counts={k:sum(k in row for row in merged) for k in SOURCE}
    print(f"Encrypted archive updated: added {added} observations; {len(merged)} dates")
    print("Counts:",counts,"from",merged[0]["date"],"through",merged[-1]["date"])

if __name__=="__main__":
    update()
