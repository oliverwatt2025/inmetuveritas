export type HistoricalRow = {date:string; [key:string]:string|number|undefined};
export type CorrelationResult = {value:number;count:number;firstDate:string;lastDate:string;lookback:number};
export const PROXIES:Record<string,{field:string;description:string}>={
 equities:{field:"breadth",description:"daily change in 1-month equal-weight minus cap-weight performance (percentage points)"},
 credit:{field:"hy_oas",description:"daily change in high-yield option-adjusted spread (basis points)"},
 volatility:{field:"vix",description:"daily change in VIX (index points)"},
 banks:{field:"kre_dd_3m",description:"daily change in the rolling three-month KRE drawdown proxy (percentage points)"},
 rates:{field:"curve_10y2y",description:"daily change in 10-year minus 2-year Treasury spread (basis points)"},
};
function daysBetween(a:string,b:string){
 const first=Date.parse(a+"T00:00:00Z"),second=Date.parse(b+"T00:00:00Z");
 return Math.round((second-first)/86400000);
}
export function correlationFor(rows:HistoricalRow[],a:string,b:string,lookback:number):CorrelationResult|null{
 const xField=PROXIES[a]?.field,yField=PROXIES[b]?.field;
 if(!xField||!yField)return null;
 // Require paired, consecutive dated daily observations for both series.
 // Do not pair readings carried forward from unrelated dates.
 const sorted=[...rows].sort((l,r)=>l.date.localeCompare(r.date));
 const deltas:{date:string;x:number;y:number}[]=[];
 for(let i=1;i<sorted.length;i++){
  const prior=sorted[i-1],cur=sorted[i];
  if(daysBetween(prior.date,cur.date)<1||daysBetween(prior.date,cur.date)>4)continue;
  const ax=cur[xField],px=prior[xField],by=cur[yField],py=prior[yField];
  if([ax,px,by,py].some(v=>typeof v!=="number"||!Number.isFinite(v)))continue;
  deltas.push({date:cur.date,x:(ax as number)-(px as number),y:(by as number)-(py as number)});
 }
 const sample=deltas.slice(-lookback);
 if(sample.length<Math.min(40,lookback))return null;
 const n=sample.length,mx=sample.reduce((t,r)=>t+r.x,0)/n,my=sample.reduce((t,r)=>t+r.y,0)/n;
 let covariance=0,vx=0,vy=0;
 for(const r of sample){const dx=r.x-mx,dy=r.y-my;covariance+=dx*dy;vx+=dx*dx;vy+=dy*dy}
 if(vx<=1e-12||vy<=1e-12)return null;
 const corr=covariance/Math.sqrt(vx*vy);
 return {value:Math.max(-1,Math.min(1,corr)),count:n,firstDate:sample[0].date,lastDate:sample[n-1].date,lookback};
}
