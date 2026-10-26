import { correlationFor } from "./historicalCorrelation";
import type { HistoricalRow } from "./historicalCorrelation";

export type StabilityResult = {
  status:"watch"|"ordinary"|"insufficient";
  title:string;
  description:string;
  current:number|null;
  historicalMedian:number|null;
  historicalPctl:number|null;
  windows:number;
  sampleCount:number;
  firstBaselineDate?:string;
  lastBaselineDate?:string;
};

function median(values:number[]):number {
 const sorted=[...values].sort((a,b)=>a-b);
 const midpoint=Math.floor(sorted.length/2);
 return sorted.length%2?sorted[midpoint]:(sorted[midpoint-1]+sorted[midpoint])/2;
}
export function relationshipStability(rows:HistoricalRow[],a:string,b:string):StabilityResult{
 const insufficient=(why:string):StabilityResult=>({
  status:"insufficient",title:"Not enough historical evidence",description:why,
  current:null,historicalMedian:null,historicalPctl:null,windows:0,sampleCount:0
 });
 if(!rows.length)return insufficient("No historical observations available.");
 const sorted=[...rows].sort((x,y)=>x.date.localeCompare(y.date));
 const latest=correlationFor(sorted,a,b,60);
 if(!latest||latest.count<60)return insufficient("Fewer than 60 valid recent paired daily changes.");
 // Historical reference windows end at least 60 rows before the latest observation;
 // step in 20-row increments. These windows overlap: the rank is descriptive only.
 const baseline:{r:number;date:string}[]=[];
 for(let end=sorted.length-61;end>=61;end-=20){
  const sample=correlationFor(sorted.slice(0,end),a,b,60);
  if(sample&&sample.count===60)baseline.push({r:sample.value,date:sample.lastDate});
 }
 if(baseline.length<12)return {
  ...insufficient("At least 12 qualifying historical windows are required, separate from the recent comparison window."),
  current:latest.value,windows:baseline.length,sampleCount:latest.count
 };
 const baselineValues=baseline.map(x=>x.r);
 const center=median(baselineValues);
 const distance=Math.abs(latest.value-center);
 const baselineDistances=baselineValues.map(x=>Math.abs(x-center));
 const percentile=100*baselineDistances.filter(x=>x<=distance).length/baseline.length;
 // Research watch only: extreme relative to history AND materially different in magnitude.
 const watch=percentile>=95&&distance>=.35;
 return {
  status:watch?"watch":"ordinary",
  title:watch?"Unusual relationship shift — research watch":"Within observed historical variation",
  description:watch
   ?"The recent correlation is far from the historical median and ranks in the outer 5% of observed deviations. This is a provisional research flag, not a statistical significance test or market-crash warning."
   :"The recent correlation does not satisfy both provisional research criteria: outer-5% historical deviation and at least 0.35 absolute difference from the median.",
  current:latest.value,historicalMedian:center,historicalPctl:percentile,
  windows:baseline.length,sampleCount:latest.count,
  firstBaselineDate:baseline[baseline.length-1].date,
  lastBaselineDate:baseline[0].date
 };
}
