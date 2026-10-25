import { useState } from "react";
import "./RelationshipMap.css";

type Finding={id:string;family:string;severity:string;headline:string;explanation:string};
type History={indicator:string;percentile:number;observationCount:number;fromDate:string;toDate:string};
type Report={dataQuality:string;regime:string;sourceAsOf:string;keyFindings:Finding[];historicalContext?:History[]};
type Status="supportive"|"attention"|"mixed"|"unknown";
type Node={id:string;name:string;x:number;y:number;detail:string};
type Edge={a:string;b:string;why:string};
const NODES:Node[]=[
 {id:"equities",name:"EQUITIES",x:170,y:105,detail:"Participation across equal-weight and cap-weighted stocks"},
 {id:"credit",name:"CREDIT",x:465,y:85,detail:"High-yield and investment-grade risk compensation"},
 {id:"volatility",name:"VOLATILITY",x:765,y:170,detail:"Equity options pricing of expected volatility"},
 {id:"banks",name:"BANKS",x:295,y:350,detail:"Regional banking sector as a potential stress channel"},
 {id:"rates",name:"RATES",x:660,y:365,detail:"Yield-curve conditions and economic-cycle signals"}
];
const EDGES:Edge[]=[
 {a:"equities",b:"credit",why:"Equity participation and corporate spreads reflect different investors' appetites for risk."},
 {a:"credit",b:"volatility",why:"Credit compensation and implied volatility can provide independent confirmation of risk aversion."},
 {a:"equities",b:"volatility",why:"Weak equity participation accompanied by rising volatility can strengthen a risk-off interpretation."},
 {a:"credit",b:"banks",why:"Bank weakness matters more when credit conditions are also tightening."},
 {a:"banks",b:"rates",why:"Interest rates and funding conditions can influence banking-sector resilience."},
 {a:"rates",b:"credit",why:"Rate moves and credit spreads are distinct drivers of borrowing costs."},
];
const LABEL:{[key in Status]:string}={supportive:"Supportive",attention:"Attention",mixed:"Mixed",unknown:"Not assessed"};
function stateFor(id:string,report:Report|null):Status{
 if(!report||report.dataQuality!=="CURRENT")return "unknown";
 const f=(report.keyFindings||[]).filter(x=>x.family===id);
 let pos=f.some(x=>x.severity==="supportive"),neg=f.some(x=>x.severity==="attention");
 if(id==="credit"&&pos){
  const hy=report.historicalContext?.find(x=>x.indicator==="hy_oas");
  if(hy&&hy.observationCount>=60&&hy.percentile>=80)neg=true;
 }
 return pos&&neg?"mixed":neg?"attention":pos?"supportive":"unknown";
}
function relationship(a:Status,b:Status):"agree"|"diverge"|"insufficient"{
 if(a==="unknown"||b==="unknown")return "insufficient";
 if(a==="mixed"||b==="mixed")return "diverge";
 return a===b?"agree":"diverge";
}
export function RelationshipMap({report}:{report:Report|null}){
 const [focus,setFocus]=useState("credit");
 const chosen=NODES.find(n=>n.id===focus)||NODES[1];
 const nodeState=Object.fromEntries(NODES.map(n=>[n.id,stateFor(n.id,report)])) as Record<string,Status>;
 const links=EDGES.filter(e=>e.a===chosen.id||e.b===chosen.id);
 const finding=(report?.dataQuality==="CURRENT"?report.keyFindings:[])?.filter(f=>f.family===chosen.id)||[];
 const hy=chosen.id==="credit"?report?.historicalContext?.find(x=>x.indicator==="hy_oas"):undefined;
 return <section className="relationshipMap" aria-label="Financial system relationship map">
  <div className="relationshipMapHeader">
   <div><span className="relationshipEyebrow">IN METU VERITAS · V4 RESEARCH LAB</span>
   <h2>Financial System Relationship Map</h2>
   <p>Explore how independent market signals relate. Select a node to reveal its evidence and connections. Lines show research relationships, not proven causation or live fund flows.</p></div>
   <div className="relationshipLegend"><span><i className="legendDot positive"/> Supportive</span><span><i className="legendDot warning"/> Attention</span><span><i className="legendDot mixed"/> Mixed</span><span><i className="legendDot neutral"/> Not assessed</span></div>
  </div>
  <div className="relationshipLayout">
   <div className="relationshipCanvas">
    <svg viewBox="0 0 930 480" role="img" aria-label="Five market areas connected by six explanatory links" preserveAspectRatio="xMidYMid meet">
      <defs><radialGradient id="map-glow"><stop stopColor="#e1c589" stopOpacity=".08"/><stop offset="1" stopColor="#e1c589" stopOpacity="0"/></radialGradient></defs>
      <circle cx="465" cy="245" r="260" fill="url(#map-glow)"/>
      {EDGES.map(e=>{
       const a=NODES.find(n=>n.id===e.a)!,b=NODES.find(n=>n.id===e.b)!;
       const result=relationship(nodeState[e.a],nodeState[e.b]);
       const highlighted=focus===e.a||focus===e.b;
       return <line key={e.a+e.b} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
        stroke={result==="agree"?"#5fbf97":result==="diverge"?"#ddb576":"#667385"}
        strokeWidth={highlighted?3:1.7} strokeOpacity={highlighted?0.95:0.38}
        strokeDasharray={result==="insufficient"?"6 7":undefined}/>;
      })}
      {NODES.map(n=>{
       const active=focus===n.id,state=nodeState[n.id];
       const color=state==="supportive"?"#69cda5":state==="attention"?"#f0ac73":state==="mixed"?"#e2c07d":"#94a0b3";
       return <g key={n.id} aria-hidden="true">
        <circle cx={n.x} cy={n.y} r={active?73:65} fill="#091521" stroke={active?"#e6d2a2":"#526071"} strokeWidth={active?3:1.5}/>
        <circle cx={n.x} cy={n.y-14} r="7" fill={color}/>
        <text x={n.x} y={n.y+12} fill="#f3e7cf" textAnchor="middle" fontSize="16" fontWeight="600" letterSpacing="1.1">{n.name}</text>
        <text x={n.x} y={n.y+34} fill={color} textAnchor="middle" fontSize="12">{LABEL[state]}</text>
       </g>;
      })}
    </svg>
    <div className="relationshipNodeControls" aria-label="Choose a market node">
      {NODES.map(n=><button key={n.id} className={focus===n.id?"relationshipNodeActive":""} type="button" onClick={()=>setFocus(n.id)} aria-pressed={focus===n.id}>{n.name.toLowerCase()}</button>)}
    </div>
    <p className="relationshipCanvasNote">Dashed links lack confirmed evidence · Solid links indicate comparable assessments, not statistical correlations.</p>
   </div>
   <aside className="relationshipDetails" aria-live="polite">
    <span className="relationshipEyebrow">SELECTED NODE</span>
    <h3>{chosen.name}</h3>
    <span className={"relationshipState state-"+nodeState[chosen.id]}>{LABEL[nodeState[chosen.id]]}</span>
    <p>{chosen.detail}</p>
    <h4>Supporting evidence</h4>
    {finding.length?finding.map(f=><div key={f.id} className="relationshipEvidence"><strong>{f.headline}</strong><p>{f.explanation}</p></div>):<p className="relationshipCaution">No current independently assessed finding. Historical data alone does not imply a safe or dangerous condition.</p>}
    {hy&&<p className="relationshipCaution">HY OAS: {hy.percentile.toFixed(1)}th percentile over {hy.observationCount} dated observations ({hy.fromDate}–{hy.toDate}). Historical ranking is not a probability of loss.</p>}
    <h4>Connections to other markets</h4>
    {links.map(e=>{
     const other=NODES.find(n=>n.id===(e.a===focus?e.b:e.a))!;
     const state=relationship(nodeState[e.a],nodeState[e.b]);
     return <button className="relationshipConnection" type="button" key={other.id} onClick={()=>setFocus(other.id)}>
      <span><strong>{other.name}</strong><small>{state==="agree"?"Assessments aligned":state==="diverge"?"Mixed or differing signals":"Insufficient confirmation"}</small></span><span aria-hidden="true">↗</span>
      <em>{e.why}</em>
     </button>;
    })}
   </aside>
  </div>
  <footer className="relationshipFooter">Research prototype · Only validated market findings determine node classifications. Links are explanatory hypotheses from the research catalogue, not measured causal dependencies. No composite forecast or probability is calculated.</footer>
 </section>;
}
