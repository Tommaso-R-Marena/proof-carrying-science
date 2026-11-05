// Independent positive-cost Bellman planner over the independently built JS diagram.
import {canonical,digest,exact,integer} from './omega-core.mjs';
import {checkConditional,validateConditional,evaluateConditional} from './conditional-core.mjs';
export const TASK='pcs-intervention-task-v1',RECEIPT='pcs-intervention-receipt-v1';
export function validateIntervention(t){
 exact(t,['format','problem','baseline','costs','locked']);
 if(t.format!==TASK)throw Error('Invalid intervention task format');
 validateConditional(t.problem);if(canonical(t.problem.candidate)!==canonical({op:'false'}))throw Error('Intervention problem must compare its target with FALSE');
 const names=t.problem.variables;exact(t.baseline,names);exact(t.costs,names);
 for(const n of names){if(typeof t.baseline[n]!=='boolean')throw Error('Baseline values must be Boolean');integer(t.costs[n],1,1000000);}
 if(!Array.isArray(t.locked)||t.locked.some(n=>typeof n!=='string'||!names.includes(n))||canonical(t.locked)!==canonical([...new Set(t.locked)].sort()))throw Error('Locked names must be a distinct sorted subset of variables');
 return t;
}
function bellman(nodes,t){
 const cells=[null,[0,1,0,0]],choices=[null,null],names=t.problem.variables;
 for(const [v,lo,hi] of nodes){const n=names[v],bit=2**v,branches=[];
  for(const [value,child] of [[false,lo],[true,hi]]){
   if(t.locked.includes(n)&&value!==t.baseline[n])continue;
   const cell=cells[child];if(cell===null)continue;const flip=value!==t.baseline[n];
   branches.push([value,[cell[0]+(flip?t.costs[n]:0),cell[1],cell[2]|(flip?bit:0),cell[3]|(flip?bit:0)]]);
  }
  if(!branches.length){cells.push(null);choices.push(null);continue;}
  const best=Math.min(...branches.map(([,c])=>c[0])),winners=branches.filter(([,c])=>c[0]===best),cell=[...winners[0][1]];
  for(const [,other] of winners.slice(1)){cell[1]+=other[1];cell[2]&=other[2];cell[3]|=other[3];}
  cells.push(cell);choices.push(winners[0][0]);
 }return {cells,choices};
}
export async function planIntervention(input,{limits}={}){
 const t=validateIntervention(structuredClone(input));limits=limits===undefined?undefined:structuredClone(limits);
 const symbolic=await checkConditional(t.problem,limits===undefined?{}:{limits});
 const r={format:RECEIPT,checker:'pcs-intervention-bellman/1',original_task:t,task_sha256:await digest(t),symbolic_receipt:symbolic,decision:null,minimum_cost:null,optimal_count:null,assignment:null,flips:null,mandatory_flips:null,possible_flips:null,bellman_cells:null,dp_nodes:0,scope:'Minimum positive-cost changes within declared Boolean meanings only',pcs_authority:false,lean_kernel_checked:false};
 if(['resource_limit','inconsistent_assumptions'].includes(symbolic.decision))r.decision=symbolic.decision;
 else{const names=t.problem.variables,d=symbolic.diagram,{cells,choices}=bellman(d.nodes,t);let root=d.difference;
  r.bellman_cells=cells;r.dp_nodes=d.nodes.length;const cell=cells[root];
  if(cell===null)r.decision='no_feasible_plan';else{const assignment={...t.baseline};while(root>=2){const [v,lo,hi]=d.nodes[root-2],value=choices[root];assignment[names[v]]=value;root=value?hi:lo;}if(root!==1)throw Error('Invalid plan terminal');
   const valid=evaluateConditional(t.problem.source,assignment)&&t.problem.assumptions.every(f=>evaluateConditional(f,assignment))&&t.locked.every(n=>assignment[n]===t.baseline[n]),actualCost=names.reduce((s,n)=>s+(assignment[n]!==t.baseline[n]?t.costs[n]:0),0);
   if(!valid||actualCost!==cell[0])throw Error('Internal plan witness does not match the declared task or cost');
   Object.assign(r,{decision:'optimal_plan',minimum_cost:cell[0],optimal_count:cell[1],assignment,flips:names.filter(n=>assignment[n]!==t.baseline[n]),mandatory_flips:names.filter((n,i)=>Boolean(cell[2]&(2**i))),possible_flips:names.filter((n,i)=>Boolean(cell[3]&(2**i)))});
  }
 }
 r.receipt_sha256=await digest(r);return r;
}
export async function verifyIntervention(input){const r=structuredClone(input);if(!r?.original_task||!r.symbolic_receipt)throw Error('Invalid intervention receipt');if(canonical(r)!==canonical(await planIntervention(r.original_task,{limits:r.symbolic_receipt.limits})))throw Error('Forged, stale or mismatched intervention receipt');return r.decision;}
export async function auditInterventionProposal(input,values,{limits}={}){
 const t=validateIntervention(structuredClone(input)),a=structuredClone(values);limits=limits===undefined?undefined:structuredClone(limits);
 exact(a,t.problem.variables);if(t.problem.variables.some(n=>typeof a[n]!=='boolean'))throw Error('Proposal values must be Boolean');
 const r=await planIntervention(t,limits===undefined?{}:{limits}),premises=t.problem.assumptions.map(f=>evaluateConditional(f,a)),target=evaluateConditional(t.problem.source,a),violations=t.locked.filter(n=>a[n]!==t.baseline[n]),cost=t.problem.variables.reduce((s,n)=>s+(a[n]!==t.baseline[n]?t.costs[n]:0),0),feasible=premises.every(Boolean)&&target&&violations.length===0;
 return {assignment:a,assumptions_true:premises,target_true:target,lock_violations:violations,feasible,cost,optimality_gap:feasible&&r.decision==='optimal_plan'?cost-r.minimum_cost:null,planner_receipt:r,pcs_authority:false};
}
