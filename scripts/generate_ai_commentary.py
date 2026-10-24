#!/usr/bin/env python3
"""Evidence-gated daily commentary. AI may select/order verified findings only.

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

def choose_with_ai(report, bank, api_key):
    instructions=("You are ranking market intelligence evidence for an educational daily summary. "
                  "Use ONLY supplied evidence IDs. Do not generate any new facts, numbers, "
                  "claims, rationale, or market predictions. Return JSON only: "
                  '{"selected_ids":["finding:..."]}. Select 1-3 distinct IDs. '
                  "Prefer conflicting evidence and significance, then representative findings.")
    payload={"model":os.environ.get("OPENAI_COMMENTARY_MODEL","gpt-5-mini"),
             "instructions":instructions,
             "input":json.dumps({"regime":report.get("regime"),
                                  "summary":report.get("summary"),"evidence":bank}),
             "text":{"format":{"type":"json_schema","name":"market_evidence_selection","strict":True,"schema":{"type":"object","properties":{"selected_ids":{"type":"array","items":{"type":"string"}}},"required":["selected_ids"],"additionalProperties":False}}},
             "max_output_tokens":600}
    req=urllib.request.Request("https://api.openai.com/v1/responses",
          data=json.dumps(payload).encode(),method="POST",
          headers={"Authorization":"Bearer "+api_key,"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=35) as resp:
        obj=json.load(resp)
    content=[]
    for output in obj.get("output",[]):
        for part in output.get("content",[]):
            if part.get("type")=="output_text":
                content.append(part.get("text",""))
    if not content: raise ValueError("No usable model response")
    return validate_selection(json.loads("".join(content)), bank)

def add_commentary(report, ai_key=None):
    bank=evidence_bank(report)
    if report.get("dataQuality")!="CURRENT" or not bank:
        report["editorialCommentary"]={"mode":"UNAVAILABLE","sourceAsOf":report.get("sourceAsOf"),
                                       "evidenceIds":[],"paragraphs":[],
                                       "disclaimer":"No current verified evidence for a commentary."}
        return report
    selected=list(bank)[:3]
    mode="RULE_BASED"
    if ai_key:
        try:
            selected=choose_with_ai(report,bank,ai_key)
            mode="AI_CURATED"
        except Exception as exc:
            print("AI selection unavailable; retaining verified fallback (error type):",type(exc).__name__)
    report["editorialCommentary"]=render_commentary(report,selected,bank,mode)
    return report

def main():
    report=json.loads(PATH.read_text(encoding="utf-8"))
    report=add_commentary(report,os.environ.get("OPENAI_API_KEY"))
    PATH.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Daily evidence commentary:",report["editorialCommentary"]["mode"])

if __name__=="__main__":main()
