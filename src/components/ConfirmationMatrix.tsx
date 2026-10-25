import { useState } from "react";
import "./ConfirmationMatrix.css";

type Finding = { id: string; family: string; severity: string; headline: string; explanation: string };
type Report = { sourceAsOf: string; dataQuality: string; regime: string; keyFindings: Finding[]; divergences?: string[] };
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
    return {
      ...group, evidence,
      state: concern && supportive ? "mixed" : concern ? "attention" : supportive ? "supportive" : "unassessed",
    };
  });
}

const LABELS = { supportive:"Supportive", attention:"Attention", mixed:"Mixed", unassessed:"Not assessed" };

export function ConfirmationMatrix({ report }: { report: Report | null }) {
  const areas = evidenceAreas(report);
  const [selected,setSelected] = useState("credit");
  const current = areas.find(area => area.id === selected) || areas[0];
  const assessed = areas.filter(x=>x.state!=="unassessed");
  const concerns = assessed.filter(x=>x.state==="attention").length;
  const support = assessed.filter(x=>x.state==="supportive").length;
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
        <small>{concerns} attention · {support} supportive</small>
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
          <span className="confirmStatus">{LABELS[area.state]}</span>
        </button>)}
      </div>
      <article className="confirmExplanation" aria-live="polite">
        <div className="confirmDetailTop"><span>SELECTED MARKET AREA</span><strong>{LABELS[current.state]}</strong></div>
        <h3>{current.title}</h3>
        <p>{current.description}</p>
        {stale && <p className="confirmUnknown">The market intelligence report is unavailable or stale; no current conclusion is presented.</p>}
        {!stale && !current.evidence.length && <p className="confirmUnknown">No independent verified finding is available for this area. This is not evidence that conditions are safe or risky.</p>}
        {!stale && current.evidence.map(item=><div className="confirmFinding" key={item.id}>
          <strong>{item.headline}</strong><p>{item.explanation}</p>
        </div>)}
        <div className="confirmContext">
          <strong>How the areas connect</strong>
          <p>Equities, credit and volatility can corroborate or contradict one another. Agreement across independent markets warrants more attention than repeated measures of the same underlying signal.</p>
          {(report?.divergences || []).length>0 && <p className="confirmCaveat">Latest disagreement: {report!.divergences![0]}</p>}
        </div>
      </article>
    </div>
    <footer className="confirmFooter">Research prototype · The matrix summarises existing validated findings only. Unassessed areas are deliberately not classified. No composite crash probability is inferred.</footer>
  </section>;
}
