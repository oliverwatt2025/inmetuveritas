import { useEffect,useState } from "react";
import "./ArchiveHealth.css";
type Detail={count:number;earliest:string|null;latest:string|null};
type Health={asOf:string;status:string;series:{hy_oas:Detail;ig_oas:Detail};note?:string};
function formatDate(value:string|null){return value?new Date(value+"T12:00:00Z").toLocaleDateString("en-GB",{day:"numeric",month:"short",year:"numeric"}):"Not available";}
export function ArchiveHealth(){
 const [health,setHealth]=useState<Health|null>(null);
 const [error,setError]=useState(false);
 useEffect(()=>{
  let active=true;
  fetch("/archive_health.json",{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("Unavailable");return r.json()})
  .then((data:Health)=>{if(active){setHealth(data);setError(false)}})
  .catch(()=>{if(active)setError(true)});
  return ()=>{active=false};
 },[]);
 return <section className="archiveHealth" aria-label="Private historical credit archive health">
  <div className="archiveHealthHeader">
   <div><span className="archiveHealthEyebrow">DATA QUALITY · PRIVATE RESEARCH ARCHIVE</span><h2>Historical Archive Health</h2>
    <p>Tracking how our stored credit history grows over time. The raw readings remain encrypted and aren't displayed here.</p></div>
   <span className="archiveHealthStatus">{health?"Metadata available":error?"Awaiting first health report":"Checking…"}</span>
  </div>
  {health?<div className="archiveHealthGrid">
   {([{key:"hy_oas",name:"High-yield credit"},{key:"ig_oas",name:"Investment-grade credit"}] as const).map(item=>{
    const data=health.series?.[item.key];
    return <div className="archiveHealthTile" key={item.key}>
     <span>{item.name}</span>
     <strong>{Number.isFinite(data?.count)?data.count.toLocaleString("en-GB"):"—"}</strong><small>Dated observations</small>
     <dl><dt>Earliest</dt><dd>{formatDate(data?.earliest??null)}</dd><dt>Latest</dt><dd>{formatDate(data?.latest??null)}</dd></dl>
    </div>;
   })}
   <div className="archiveHealthTile archiveHealthTiming"><span>Last successful collection</span>
    <strong className="archiveHealthDate">{health.asOf?new Date(health.asOf).toLocaleString("en-GB",{dateStyle:"medium",timeStyle:"short",timeZone:"UTC"})+" UTC":"—"}</strong>
    <small>Collection success means the archive was read and checked, not necessarily that a new market observation was released.</small>
   </div>
  </div>:<p className="archiveHealthPending">No verified archive-health summary is available yet. This does not mean historical observations are missing. The next successful archive workflow will create the summary.</p>}
  <footer>Only observation counts, earliest/latest dates and collection time are public. Missing provider readings are never treated as fresh observations.</footer>
 </section>;
}
