import { useEffect, useState } from "react";
import "./CreditEvidence.css";

type ComponentReading = {latest:number|null;score:number|null};
type CreditDetails = {
  raw?:number;smoothed?:number;
  components?:Record<string,ComponentReading>;
  momentum?:{chg_1m?:number;pct_rank?:number;kicker_applied?:boolean};
};
type Card = {id:string;value?:number;status?:string;details?:CreditDetails};
type Payload = {asOf?:string;cards?:Card[]};

const formatted = (v:number|undefined|null, digits=0) => typeof v==="number"&&Number.isFinite(v)?v.toFixed(digits):"—";
export function CreditEvidence(){
 const [payload,setPayload]=useState<Payload|null>(null);
 const [error,setError]=useState(false);
 useEffect(()=>{
  let active=true;
  const load=()=>fetch("/indicators.json",{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("No indicator snapshot");return r.json()}).then((data:Payload)=>{
   if(active){setPayload(data);setError(false)}
  }).catch(()=>{if(active)setError(true)});
  load();const timer=setInterval(load,5*60*1000);
  return ()=>{active=false;clearInterval(timer)};
 },[]);
 const cards=payload?.cards??[];
 const find=(id:string)=>cards.find(c=>c.id===id);
 const credit=find("credit_stress");
 const hy=find("hy_oas");const ig=find("ig_oas");
 const c=credit?.details?.components;
 const m=credit?.details?.momentum;
 const hyContained=hy?.status==="GOOD";
 const igContained=ig?.status==="GOOD";
 const contained=hyContained&&igContained;
 const funding=[["CPFF",c?.cpff],["St. Louis FSI",c?.stlfsi4],["Chicago Fed risk",c?.nfcirisk]] as const;
 const validFunding=funding.filter(([,v])=>typeof v?.score==="number");
 // A descriptive cross-check, not an independently calibrated alarm.
 const highFunding=validFunding.filter(([,v])=>(v?.score??0)>=80);
 const fundingLabel=validFunding.length===0?"No usable funding readings":highFunding.length>=2?"Multiple relatively elevated measures":highFunding.length===1?"One relatively elevated measure":"No broad relative funding elevation";
 const kicked=m?.kicker_applied===true;
 return <section className="creditEvidence" aria-label="Credit stress evidence explained">
  <div className="creditEvidenceHeader">
   <div><span className="creditEvidenceEyebrow">IN METU VERITAS · CREDIT EVIDENCE</span>
    <h2>Inside the Credit Stress Signal</h2>
    <p>Separate spread levels, rate of change and corroborating indicators — without changing the composite calculation.</p>
   </div>
   {credit&&<div className="creditEvidenceScore"><strong>{formatted(credit.value)}</strong><span>/ 100 relative pressure score</span></div>}
  </div>
  {!credit||!c?<p className="creditEvidenceUnavailable">Detailed credit evidence is not yet available from the most recent indicator snapshot.{error?" The data request was unsuccessful.":""}</p>:
   <>
    <div className="creditEvidenceGrid">
     <article><div className="creditEvidenceCategory">01 · ABSOLUTE LEVEL</div>
      <h3>Corporate spreads</h3><div className={"creditEvidenceState "+(contained?"positive":"caution")}>{contained?"Contained levels":"Check individual spread readings"}</div>
      <p>HY <strong>{formatted(hy?.value)} bp</strong> · IG <strong>{formatted(ig?.value)} bp</strong></p>
      <small>{contained?"Both underlying cards are GOOD under their absolute thresholds.":"At least one spread card is not GOOD, or a valid reading is unavailable."} This is separate from historical relative rankings.</small>
     </article>
     <article><div className="creditEvidenceCategory">02 · DIRECTION OF TRAVEL</div>
      <h3>High-yield momentum</h3><div className={"creditEvidenceState "+(kicked?"caution":"positive")}>{kicked?"Top-decile acceleration":"No momentum kicker"}</div>
      <p>Recent change <strong>{typeof m?.chg_1m==="number"?(m.chg_1m>=0?"+":"")+formatted(m.chg_1m*100,0)+" bp":"—"}</strong></p>
      <p>Change percentile <strong>{formatted(m?.pct_rank,1)}th</strong> · Contribution <strong>{kicked?"+5 points":"0 points"}</strong></p>
      <small>The +5 adjustment is part of the existing model and is preserved without recalibration.</small>
     </article>
     <article><div className="creditEvidenceCategory">03 · CROSS-CHECK</div>
      <h3>Other financial measures</h3><div className="creditEvidenceState neutral">{fundingLabel}</div>
      {funding.map(([name,value])=><p className="creditEvidenceMini" key={name}><span>{name}</span><strong>{formatted(value?.score,1)}th percentile</strong></p>)}
      <small>These are historical relative readings, not independent proof of systemic distress. Two readings at or above the 80th percentile are labelled multiple elevation for descriptive context only.</small>
     </article>
    </div>
    <div className="creditEvidenceConclusion">
      <strong>HOW TO READ THIS</strong>
      <p>{contained&&kicked
       ?"Absolute HY and IG spread readings remain contained, but relatively rapid HY widening has activated the five-point sensitivity adjustment. This merits monitoring without, on its own, confirming systemic credit stress."
       :contained?"Absolute HY and IG spreads are contained. Relative pressure in the other components still warrants monitoring.":"At least one absolute spread reading needs attention alongside the relative-pressure composite."}
       {" "}{highFunding.length>=2?"Multiple other financial measures are also relatively elevated.":highFunding.length===1?"One other financial measure is relatively elevated.":"The other financial measures do not show widespread relative elevation under this descriptive screen."}</p>
    </div>
    <footer>Method: the published 0–100 composite remains unchanged (including smoothing and momentum). HY/BBB/HY–IG components share underlying credit-market information and should not be treated as three independent confirmations. Status labels are interpretive, not forecasts. Snapshot: {payload?.asOf?new Date(payload.asOf).toLocaleString("en-GB",{dateStyle:"medium",timeStyle:"short",timeZone:"UTC"})+" UTC":"date unavailable"}.</footer>
   </>}
 </section>;
}
