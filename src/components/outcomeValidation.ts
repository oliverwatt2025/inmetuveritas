import { relationshipStability } from "./relationshipStability";
import type { HistoricalRow } from "./historicalCorrelation";

export type OutcomeCheck={date:string;signal:"watch"|"ordinary";eligible:boolean;outcome:"stress"|"no_stress"|"unknown";futureLow:number|null;};
export type OutcomeValidation={
 checks:number; eligible:number;watchCount:number; ordinaryCount:number; insufficient:number;
 stressAfterWatch:number;noStressAfterWatch:number;
 stressAfterOrdinary:number;noStressAfterOrdinary:number;
 unknownOutcome:number;rows:OutcomeCheck[];
};
const isNumber=(x:unknown):x is number=>typeof x==="number"&&Number.isFinite(x);

/**
 * Exploratory post-signal outcome, independently specified before reading results:
 * a subsequently observed <= -8% 1-month SPY drawdown proxy over the NEXT
 * 20 dated observations. Exclude checkpoints already at/below -8%.
 * Treat missing coverage as UNKNOWN rather than "no stress".
 *
 * Note: SPY rolling drawdown proxy is not a point-in-time SPY daily-return
 * backtest and may be related to equity-derived signals. This is NOT
 * independent out-of-sample validation of warning effectiveness.
 */
export function validateOutcomes(history:HistoricalRow[],a:string,b:string):OutcomeValidation{
 const sorted=[...history].sort((x,y)=>x.date.localeCompare(y.date));
 const result:OutcomeValidation={checks:0,eligible:0,watchCount:0,ordinaryCount:0,
  insufficient:0,stressAfterWatch:0,noStressAfterWatch:0,stressAfterOrdinary:0,
  noStressAfterOrdinary:0,unknownOutcome:0,rows:[]};
 const start=Math.max(341,sorted.length-756);
 for(let end=start;end<=sorted.length-21;end+=20){
  const snapshot=sorted.slice(0,end);
  const check=relationshipStability(snapshot,a,b);
  result.checks++;
  if(check.status==="insufficient"){result.insufficient++;continue}
  const atDate=sorted[end-1];
  const present=atDate.spy_dd_1m;
  // At least one independent observable outcome series must be available
  // at the checkpoint, and it must not already meet the stress threshold.
  if(!isNumber(present)||present<=-8){result.unknownOutcome++;continue}
  const future=sorted.slice(end,end+20);
  const values=future.map(x=>x.spy_dd_1m).filter(isNumber);
  // Require >= 16/20 dated points to avoid incorrectly calling gaps safe.
  const outcome=values.length<16?"unknown":Math.min(...values)<=-8?"stress":"no_stress";
  const signal=check.status==="watch"?"watch":"ordinary";
  result.eligible++;
  if(signal==="watch")result.watchCount++;else result.ordinaryCount++;
  if(outcome==="unknown")result.unknownOutcome++;
  else if(signal==="watch"&&outcome==="stress")result.stressAfterWatch++;
  else if(signal==="watch")result.noStressAfterWatch++;
  else if(outcome==="stress")result.stressAfterOrdinary++;
  else result.noStressAfterOrdinary++;
  result.rows.push({date:atDate.date,signal,eligible:true,outcome,
   futureLow:values.length?Math.min(...values):null});
 }
 return result;
}
