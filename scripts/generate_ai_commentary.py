#!/usr/bin/env python3
"""Evidence-gated daily commentary. Cloudflare AI may select/order verified findings only.

Market statements are rendered from previously validated analytic findings,
never from unrestricted model-generated financial prose. If model unavailable,
fallback is deterministic. No API credentials are written to files.
"""
import json
import os
import urllib.request
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "public" / "market_intelligence.json"

def evidence_bank(report):
    bank={}
    for finding in report.get("keyFindings", []):
        key=finding.get("id")
        if key and finding.get("headline") and finding.get("explanation"):
            bank["finding:"+key] = str(finding["headline"])+". "+str(finding["explanation"])
    for finding in report.get("historicalFindings", []):
        key=finding.get("indicator")
        if key and finding.get("explanation"):
            bank["historical:"+key]=str(finding["explanation"])
    for i, explanation in enumerate(report.get("divergences", [])):
        if isinstance(explanation,str):
            bank["divergence:"+str(i)]=explanation
    return bank

def validate_selection(selection, bank):
    if not isinstance(selection,dict) or set(selection)!={"selected_ids"}:
        raise ValueError("Unexpected AI response structure")
    selected=selection["selected_ids"]
    if not isinstance(selected,list) or not 1<=len(selected)<=3:
        raise ValueError("Selection length out of range")
    if any(not isinstance(x,str) or x not in bank for x in selected):
        raise ValueError("Unrecognised evidence ID")
    if len(set(selected))!=len(selected):
        raise ValueError("Repeated evidence ID")
    return selected

def render_commentary(report, selected, bank, mode):
    # Exact statements come from verified deterministic calculations.
    return {"mode":mode, "sourceAsOf":report["sourceAsOf"],
            "evidenceIds":selected,
            "paragraphs":[bank[x] for x in selected],
            "disclaimer":"An evidence selection, not a prediction. Interpretations use provisional thresholds."}

def choose_with_ai(report, bank, token, account_id):
    """Cloudflare Workers AI ranks allowlisted evidence IDs, never composes claims."""
    instructions=("Select 1 to 3 distinct evidence IDs for an educational daily market brief. "
                  "Prioritise significant historical deviations and conflicting evidence. "
                  "Do not create new figures, predictions, or IDs. "
                  "Reply ONLY as a JSON object with exactly one key, selected_ids, "
                  "whose value is an array of supplied IDs.")
    prompt=instructions+"\\n"+json.dumps({"regime":report.get("regime"),
             "summary":report.get("summary"),"evidence":bank},ensure_ascii=False)
    model="@cf/meta/llama-3.1-8b-instruct"
    url=f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    req=urllib.request.Request(url,method="POST",
         data=json.dumps({"messages":[{"role":"system","content":instructions},
                                      {"role":"user","content":prompt}],
                          "max_tokens":300,"temperature":0}).encode("utf-8"),
         headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=35) as resp:
        obj=json.load(resp)
    if not obj.get("success") or not isinstance(obj.get("result"),dict):
        raise ValueError("Cloudflare AI returned unsuccessful response")
    raw=obj["result"].get("response")
    if not isinstance(raw,str):
        raise ValueError("Cloudflare AI returned no text")
    # Reject any surrounding prose: only JSON containing the approved IDs passes.
    return validate_selection(json.loads(raw.strip()),bank)

def add_commentary(report, ai_key=None, account_id=None):
    bank=evidence_bank(report)
    if report.get("dataQuality")!="CURRENT" or not bank:
        report["editorialCommentary"]={"mode":"UNAVAILABLE","sourceAsOf":report.get("sourceAsOf"),
                                       "evidenceIds":[],"paragraphs":[],
                                       "disclaimer":"No current verified evidence for a commentary."}
        return report
    selected=list(bank)[:3]
    mode="RULE_BASED"
    if ai_key and account_id:
        try:
            selected=choose_with_ai(report,bank,ai_key,account_id)
            mode="AI_CURATED"
        except Exception as exc:
            print("AI selection unavailable; retaining verified fallback (error type):",type(exc).__name__)
    report["editorialCommentary"]=render_commentary(report,selected,bank,mode)
    return report

def main():
    report=json.loads(PATH.read_text(encoding="utf-8"))
    report=add_commentary(report,os.environ.get("CLOUDFLARE_AI_TOKEN"),os.environ.get("CLOUDFLARE_ACCOUNT_ID"))
    PATH.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Daily evidence commentary:",report["editorialCommentary"]["mode"])

if __name__=="__main__":main()
