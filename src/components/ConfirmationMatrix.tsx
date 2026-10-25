import { useEffect, useState } from "react";
import "./ConfirmationMatrix.css";

type Finding = { id: string; family: string; severity: string; headline: string; explanation: string };
type Historical = {indicator: string; value?: number; percentile: number; observationCount: number; fromDate: string; toDate: string};
type Report = { sourceAsOf: string; dataQuality: string; regime: string; keyFindings: Finding[]; divergences?: string[]; historicalContext?: Historical[] };
type HistoryPoint = {date:string; [indicator:string]: string|number|undefined};
type Trend = {label:string; delta:number; fromDate:string; toDate:string; unit:string};
type Area = { id: string; title: string; description: string; evidence: Finding[]; state: "supportive"|"attention"|"mixed"|"unassessed" };

const GROUPS = [
  {id:"equities",title:"Equity participation",description:"Does performance extend beyond the largest companies?"},
  {id:"credit",title:"Corporate credit",description:"Are lenders demanding greater compensation for risk?"},
  {id:"volatility",title:"Equity volatility",description:"Are option markets pricing heightened uncertainty?"},
  {id:"banks",title:"Regional banks",description:"Is bank equity pricing showing financial-sector pressure?"},
  {id:"rates",title:"Rates & cycle",description:"Do the yield curve and cycle indicators confirm stress?"},
] as const;

function evidenceAreas(report: Report | null): Area[] {
  const verified = report?.dataQuality === "CURRENT" ? (report.keyFindings || []) : [];
  return GROUPS.map(group => {
    const evidence = verified.filter(item => item.family === group.id);
    const concern = evidence.some(item => item.severity === "attention");
    const supportive = evidence.some(item => item.severity === "supportive");
    const state: Area["state"] = concern && supportive ? "mixed" : concern ? "attention" : supportive ? "supportive" : "unassessed";
    return { ...group, evidence, state };
  });
}

const SERIES: Record<string,{field:string;unit:string;moreIsRisk:boolean}> = {
  equities:{field:"breadth",unit:"pp",moreIsRisk:false},
  credit:{field:"hy_oas",unit:"bp",moreIsRisk:true},
  volatility:{field:"vix",unit:"pts",moreIsRisk:true},
  banks:{field:"kre_dd_3m",unit:"pp",moreIsRisk:false},
  rates:{field:"curve_10y2y",unit:"bp",moreIsRisk:false},
};
function trendFor(area:string, history:HistoryPoint[], lookback:number): Trend|null {
  const cfg=SERIES[area];
  const series=history.filter(row=>typeof row[cfg.field]==="number" && Number.isFinite(row[cfg.field] as number));
  if(series.length<=lookback) return null;
  const last=series[series.length-1], prior=series[series.length-1-lookback];
  const delta=(last[cfg.field] as number)-(prior[cfg.field] as number);
  const riskMove=(cfg.moreIsRisk?1:-1)*delta;
  const label=Math.abs(delta)<(cfg.field==="vix"?0.5:cfg.field==="breadth"?0.5:cfg.field==="kre_dd_3m"?1:3)
    ?"Broadly stable":riskMove>0?"Deteriorating":"Improving";
  return {label,delta,fromDate:prior.date,toDate:last.date,unit:cfg.unit};
}
const LABELS = { supportive:"Supportive", attention:"Attention", mixed:"Mixed", unassessed:"Not assessed" };

export function ConfirmationMatrix({ report }: { report: Report | null }) {
  const areas = evidenceAreas(report);
  const [history,setHistory]=useState<HistoryPoint[]>([]);
  useEffect(()=>{
    let cancelled=false;
    fetch("/history_5y.ndjson").then(r=>{if(!r.ok) throw Error("History unavailable");return r.text()})
      .then(raw=>{
        const rows=raw.trim().split("\n").flatMap(line=>{try {return [JSON.parse(line) as HistoryPoint]} catch {return []}});
        rows.sort((a,b)=>a.date.localeCompare(b.date));
        if(!cancelled) setHistory(rows);
      }).catch(()=>{if(!cancelled)setHistory([])});
    return ()=>{cancelled=true};
  },[]);
  const [selected,setSelected] = useState("credit");
  const current = areas.find(area => area.id === selected) || areas[0];
  const assessed = areas.filter(x=>x.state!=="unassessed");
  const five = trendFor(current.id,history,5), twenty=trendFor(current.id,history,20);
  const creditHistory=report?.historicalContext?.find(x=>x.indicator==="hy_oas");
  const creditMixed=report?.dataQuality==="CURRENT" && creditHistory &&
    Number.isFinite(creditHistory.percentile) && creditHistory.percentile>=80 &&
    areas.some(a=>a.id==="credit" && a.state==="supportive");
  if(creditMixed){const a=areas.find(a=>a.id==="credit");if(a)a.state="mixed";}
  const concerns = areas.filter(x=>x.state==="attention").length;
  const mixed = areas.filter(x=>x.state==="mixed").length;
  const states=Object.fromEntries(areas.map(a=>[a.id,a.state]));
  const corroboration=states.credit==="attention" && states.volatility==="attention"
    ? "Credit and volatility independently show attention-level stress. This is corroboration, not a calibrated probability."
    : states.credit==="mixed" && states.volatility==="supportive"
      ? "Credit's relative historical position warrants attention, while current volatility does not confirm broad stress."
      : states.equities==="supportive" && states.credit==="supportive" && states.volatility==="supportive"
        ? "Participation, credit and volatility each have supportive current findings, but may still change direction."
        : "The assessed market areas do not provide a single consistent cross-market signal.";
  const stale = !report || report.dataQuality !== "CURRENT";
  return <section className="confirmMatrix" aria-label="Market stress confirmation matrix">
    <div className="confirmHeading">
      <div><span className="confirmEyebrow">V3 LAB · EVIDENCE RELATIONSHIPS</span>
        <h2>Market Stress Confirmation Matrix</h2>
        <p>Which independent market areas support or challenge today's conclusion? Select a market area to see exactly what has been assessed.</p>
      </div>
      <div className="confirmOverview" aria-label="Evidence coverage">
        <strong>{assessed.length} / {areas.length}</strong>
        <span>Market areas assessed</span>
        <small>{concerns} attention · {mixed} mixed · {areas.filter(x=>x.state==="supportive").length} supportive</small>
      </div>
    </div>
    <div className="confirmLayout">
      <div className="confirmAreas" role="group" aria-label="Market areas">
        {areas.map(area=><button key={area.id} type="button"
          onClick={()=>setSelected(area.id)}
          aria-pressed={selected===area.id}
          className={`confirmArea confirm-${area.state} ${selected===area.id?"confirmSelected":""}`}>
          <span className="confirmDot" aria-hidden="true"/>
          <span className="confirmAreaText"><strong>{area.title}</strong><small>{area.description}</small></span>
          <span className="confirmStatus"><span className="confirmLevel">Level: {LABELS[area.state]}</span>{trendFor(area.id,history,5) && <small className="confirmTrendTiny">Trend: {trendFor(area.id,history,5)!.label} · 5 sessions</small>}</span>
        </button>)}
      </div>
      <article className="confirmExplanation" aria-live="polite">
        <div className="confirmDetailTop"><span>SELECTED MARKET AREA</span><strong>Current level: {LABELS[current.state]}</strong></div>
        <h3>{current.title}</h3>
        <p>{current.description}</p>
        {current.id==="credit" && creditMixed && <p className="confirmCaveat">Mixed evidence: HY spreads remain below the absolute watch threshold, but the same report places HY OAS at the {creditHistory!.percentile.toFixed(1)}th percentile among {creditHistory!.observationCount} observations ({creditHistory!.fromDate} to {creditHistory!.toDate}). Relative position is not a crash probability.</p>}
        <div className="confirmTrends"><strong>DIRECTION OF TRAVEL · HISTORICAL OBSERVATIONS</strong><p className="confirmTrendClarifier">Current level and direction of travel are separate assessments. A supportive level can still be deteriorating; trends do not automatically override the level classification.</p>
          {[{title:"5 sessions",trend:five},{title:"20 sessions",trend:twenty}].map(x=><div key={x.title}>
            <span>{x.title}</span><b>{x.trend?x.trend.label:"Insufficient history"}</b>
            <small>{x.trend?`${x.trend.delta>0?"+":""}${x.trend.delta.toFixed(1)} ${x.trend.unit} · ${x.trend.fromDate} → ${x.trend.toDate}`:"No dated comparison"}</small>
          </div>)}
          <small>Direction uses the latest available dated observations for this area's proxy, not the report publication time. Rates curve steepening/flattening is indicative only.</small>
        </div>
        {stale && <p className="confirmUnknown">The market intelligence report is unavailable or stale; no current conclusion is presented.</p>}
        {!stale && !current.evidence.length && <p className="confirmUnknown">No independent verified finding is available for this area. This is not evidence that conditions are safe or risky.</p>}
        {!stale && current.evidence.map(item=><div className="confirmFinding" key={item.id}>
          <strong>{item.headline}</strong><p>{item.explanation}</p>
        </div>)}
        <div className="confirmContext">
          <strong>How the areas connect</strong>
          <p>{corroboration}</p>
          <p>Confirmation uses independent categories, not multiple descriptions of the same metric. Areas without verified findings remain unassessed even if historical trends can be calculated.</p>
          {(report?.divergences || []).length>0 && <p className="confirmCaveat">Latest disagreement: {report!.divergences![0]}</p>}
        </div>
      </article>
    </div>
    <footer className="confirmFooter">Research prototype · The matrix summarises existing validated findings only. Unassessed areas are deliberately not classified. No composite crash probability is inferred.</footer>
  </section>;
}
