import { relationshipStability } from "./relationshipStability";
import type { HistoricalRow } from "./historicalCorrelation";

export type BacktestSummary={
  checked:number; watches:number; ordinary:number; insufficient:number;
  firstDate:string|null;lastDate:string|null;
  events:{date:string;label:string;rank:number|null;median:number|null;current:number|null}[];
};
// Observational replay only. No outcome labelled "true positive" without an
// independent dated event definition and point-in-time data validation.
export function backtestRelationship(rows:HistoricalRow[],a:string,b:string):BacktestSummary{
 const ordered=[...rows].sort((x,y)=>x.date.localeCompare(y.date));
 const result:BacktestSummary={checked:0,watches:0,ordinary:0,insufficient:0,firstDate:null,lastDate:null,events:[]};
 // Sample non-overlapping checkpoints in time (20 raw observation rows apart).
 // Each evaluation sees *only* data available through that checkpoint.
 // Limit evaluations to the most recent 3 years of available history.
 const start=Math.max(0,ordered.length-756);
 for(let end=Math.max(start+1,341);end<=ordered.length;end+=20){
  const slice=ordered.slice(0,end);
  const r=relationshipStability(slice,a,b);
  const date=slice[slice.length-1].date;
  result.checked++;
  result.firstDate??=date;result.lastDate=date;
  if(r.status==="watch"){
   result.watches++;
   result.events.push({date,label:r.title,rank:r.historicalPctl,median:r.historicalMedian,current:r.current});
  }else if(r.status==="ordinary")result.ordinary++;
  else result.insufficient++;
 }
 return result;
}
