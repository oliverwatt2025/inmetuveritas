#!/usr/bin/env python3
"""Evidence-gated daily commentary. Cloudflare AI may select/order verified findings only.

Market statements are rendered from previously validated analytic findings,
never from unrestricted model-generated financial prose. If model unavailable,
fallback is deterministic. No API credentials are written to files.
"""
import json
import os
import urllib.request
import re
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

def evidence_theme(evidence_id):
    """Related evidence should not occupy several slots in one brief."""
    if evidence_id in ("historical:hy_oas", "divergence:0", "finding:credit_contained",
                       "finding:credit_pressure", "historical:ig_oas"):
        return "credit"
    if evidence_id in ("historical:breadth", "divergence:1",
                       "finding:broad_participation", "finding:narrow_leadership"):
        return "participation"
    if evidence_id.startswith("finding:volatility") or evidence_id == "historical:vix":
        return "volatility"
    if evidence_id == "historical:curve_10y2y": return "rates"
    if evidence_id == "historical:kre_dd_3m" or evidence_id == "finding:regional_banks_weak":
        return "banks"
    return evidence_id


def select_diverse(selected, bank, limit=3):
    chosen=[]
    themes=set()
    for evidence_id in list(selected)+list(bank):
        theme=evidence_theme(evidence_id)
        if evidence_id in bank and theme not in themes:
            chosen.append(evidence_id)
            themes.add(theme)
            if len(chosen)>=limit: break
    return chosen


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
    return select_diverse(selected,bank)

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
        raise ValueError("CLOUDFLARE_RESPONSE_ERROR")
    result=obj["result"]
    raw=result.get("response")
    if not isinstance(raw,str) or not raw.strip():
        # Some Cloudflare models return OpenAI-style chat choices, or
        # structured response content in a different top-level field.
        choices=result.get("choices")
        if isinstance(choices,list) and choices:
            first=choices[0]
            if isinstance(first,dict):
                message=first.get("message")
                if isinstance(message,dict):
                    raw=message.get("content")
                if not isinstance(raw,str):
                    raw=first.get("text")
    if not isinstance(raw,str) or not raw.strip():
        # Do not print model output or secrets. Keys alone reveal the response shape.
        fields=",".join(sorted(k for k in result if isinstance(k,str) and k in (
            "response","choices","output","result","usage","prompt","text","messages")))
        raise ValueError("CLOUDFLARE_NO_TEXT_FIELDS:"+fields)
    # Some smaller models wrap JSON in markdown code fences. Unwrap only
    # fences; the decoded object still must contain ONLY allowlisted IDs.
    clean=raw.strip()
    match=re.fullmatch(r"```(?:json)?\\s*(\\{[\\s\\S]*\\})\\s*```",clean,re.IGNORECASE)
    if match: clean=match.group(1)
    try:
        selection=json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError("NON_JSON_MODEL_RESPONSE") from exc
    try:
        return validate_selection(selection,bank)
    except ValueError as exc:
        raise ValueError("INVALID_EVIDENCE_SELECTION") from exc

def add_commentary(report, ai_key=None, account_id=None):
    bank=evidence_bank(report)
    if report.get("dataQuality")!="CURRENT" or not bank:
        report["editorialCommentary"]={"mode":"UNAVAILABLE","sourceAsOf":report.get("sourceAsOf"),
                                       "evidenceIds":[],"paragraphs":[],
                                       "disclaimer":"No current verified evidence for a commentary."}
        return report
    selected=select_diverse(list(bank),bank)
    mode="RULE_BASED"
    if ai_key and account_id:
        try:
            selected=choose_with_ai(report,bank,ai_key,account_id)
            mode="AI_CURATED"
        except Exception as exc:
            print("AI selection unavailable; retaining verified fallback:",str(exc) if isinstance(exc,ValueError) else type(exc).__name__)
    report["editorialCommentary"]=render_commentary(report,selected,bank,mode)
    return report

def main():
    report=json.loads(PATH.read_text(encoding="utf-8"))
    report=add_commentary(report,os.environ.get("CLOUDFLARE_AI_TOKEN"),os.environ.get("CLOUDFLARE_ACCOUNT_ID"))
    PATH.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Daily evidence commentary:",report["editorialCommentary"]["mode"])

if __name__=="__main__":main()
