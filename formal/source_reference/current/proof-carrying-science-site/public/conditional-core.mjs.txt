// Independent reduced ordered BDD engine. Partial work cannot establish a result.
import {canonical,digest,exact,integer} from './omega-core.mjs';
export const TASK='pcs-conditional-boolean-task-v1',RECEIPT='pcs-conditional-boolean-receipt-v1';
const OPS=['atom','true','false','not','and','or','implies'],RESERVED=['AND','OR','NOT','IMPLIES','TRUE','FALSE'];
export const DEFAULT_LIMITS=Object.freeze({nodes:4096,operations:100000});
export function validateConditional(t){
 exact(t,['format','variables','source','candidate','assumptions']);const names=t.variables;
 if(t.format!==TASK||!Array.isArray(names)||names.length>24||names.some(n=>typeof n!=='string'||!/^[A-Z][A-Z0-9_]{0,15}$/.test(n)||RESERVED.includes(n))||new Set(names).size!==names.length||canonical(names)!==canonical([...names].sort()))throw Error('Declare at most 24 distinct sorted uppercase Boolean variables; logical keywords are reserved');
 if(!Array.isArray(t.assumptions)||t.assumptions.length>8)throw Error('Declare at most eight assumptions');
 for(const f of [t.source,t.candidate,...t.assumptions]){let count=0;
  function visit(n,depth){if(++count>128||depth>12)throw Error('Formula complexity bound exceeded');if(!n||!OPS.includes(n.op))throw Error('Unsupported Boolean formula');const op=n.op;
   exact(n,op==='atom'?['op','symbol','args']:op==='not'?['op','body']:['and','or','implies'].includes(op)?['op','left','right']:['op']);
   if(op==='atom'&&(!names.includes(n.symbol)||!Array.isArray(n.args)||n.args.length))throw Error('Unknown variable or nonzero arity');
   if(op==='not')visit(n.body,depth+1);else if(['and','or','implies'].includes(op)){visit(n.left,depth+1);visit(n.right,depth+1);}
  }visit(f,0);
 }return t;
}
export function evaluateConditional(f,a){switch(f.op){case 'atom':return a[f.symbol];case 'true':return true;case 'false':return false;case 'not':return !evaluateConditional(f.body,a);case 'and':return evaluateConditional(f.left,a)&&evaluateConditional(f.right,a);case 'or':return evaluateConditional(f.left,a)||evaluateConditional(f.right,a);case 'implies':return !evaluateConditional(f.left,a)||evaluateConditional(f.right,a);default:throw Error('Unsupported Boolean operator');}}
class ResourceLimit extends Error{}
class Diagram{
 constructor(names,limits){this.names=names;this.limits=limits;this.nodes=[];this.unique=new Map();this.memo=new Map();this.operations=0;this.visits=0;this.witnessSteps=0;}
 node(v,lo,hi){if(lo===hi)return lo;const key=[v,lo,hi].join(',');if(this.unique.has(key))return this.unique.get(key);if(this.nodes.length>=this.limits.nodes)throw new ResourceLimit('nodes');const id=this.nodes.length+2;this.nodes.push([v,lo,hi]);this.unique.set(key,id);return id;}
 apply(op,a,b){if(this.operations>=this.limits.operations)throw new ResourceLimit('operations');this.operations++;if(a>b)[a,b]=[b,a];const key=[op,a,b].join(',');if(this.memo.has(key))return this.memo.get(key);let result;
  if(a<2&&b<2)result=op==='and'?Number(Boolean(a&&b)):op==='or'?Number(Boolean(a||b)):Number(a!==b);
  else{const av=a>=2?this.nodes[a-2][0]:this.names.length,bv=b>=2?this.nodes[b-2][0]:this.names.length,v=Math.min(av,bv);
   const [al,ah]=av===v?this.nodes[a-2].slice(1):[a,a],[bl,bh]=bv===v?this.nodes[b-2].slice(1):[b,b];
   const lo=this.apply(op,al,bl),hi=this.apply(op,ah,bh);result=this.node(v,lo,hi);
  }this.memo.set(key,result);return result;
 }
 compile(f){this.visits++;switch(f.op){case 'atom':return this.node(this.names.indexOf(f.symbol),0,1);case 'true':return 1;case 'false':return 0;case 'not':return this.apply('xor',this.compile(f.body),1);default:{const a=this.compile(f.left),b=this.compile(f.right);return f.op==='implies'?this.apply('or',this.apply('xor',a,1),b):this.apply(f.op,a,b);}}}
 conjunction(roots){let r=1;for(const n of roots)r=this.apply('and',r,n);return r;}
 world(root){if(root===0)return null;const values=Object.fromEntries(this.names.map(n=>[n,false]));while(root>=2){this.witnessSteps++;const [v,lo,hi]=this.nodes[root-2];values[this.names[v]]=lo===0;root=lo===0?hi:lo;}if(root!==1)throw Error('Invalid diagram terminal');return values;}
 work(){return {bdd_nodes:this.nodes.length,apply_calls:this.operations,ast_visits:this.visits,witness_steps:this.witnessSteps};}
}
export async function checkConditional(input,{limits=DEFAULT_LIMITS}={}){
 const t=validateConditional(structuredClone(input));limits=structuredClone(limits);exact(limits,['nodes','operations']);for(const k of Object.keys(limits))integer(limits[k],1,DEFAULT_LIMITS[k]);const m=new Diagram(t.variables,limits);
 const r={format:RECEIPT,checker:'pcs-conditional-bdd/1',original_task:t,task_sha256:await digest(t),limits,decision:null,context_example:null,counterexample:null,unsat_core:null,core_necessity_witnesses:null,diagram:null,limit_reached:null,scope:'Declared Boolean interpretations and explicit assumptions only',pcs_authority:false,lean_kernel_checked:false};
 try{
  const premises=[];let context=1,source=null,candidate=null,difference=null;for(const f of t.assumptions){premises.push(m.compile(f));context=m.apply('and',context,premises.at(-1));if(context===0)break;}
  if(context===0){let core=premises.map((_,i)=>i);for(const i of [...core]){const remaining=core.filter(j=>j!==i);if(m.conjunction(remaining.map(j=>premises[j]))===0)core=remaining;}
   const necessities=core.map(i=>{const assignment=m.world(m.conjunction(core.filter(j=>j!==i).map(j=>premises[j])));if(assignment===null)throw Error('Invalid minimal conflict');return {removed_assumption:i,assignment};});Object.assign(r,{decision:'inconsistent_assumptions',unsat_core:core,core_necessity_witnesses:necessities});
  }else{source=m.compile(t.source);candidate=m.compile(t.candidate);difference=m.apply('and',context,m.apply('xor',source,candidate));r.context_example=m.world(context);const world=m.world(difference);if(world===null)r.decision='equivalent_under_assumptions';else{const truths=t.assumptions.map(f=>evaluateConditional(f,world)),a=evaluateConditional(t.source,world),b=evaluateConditional(t.candidate,world);if(!truths.every(Boolean)||a===b)throw Error('Invalid counterexample');Object.assign(r,{decision:'counterexample',counterexample:{assignment:world,source_true:a,candidate_true:b,assumptions_true:truths}});}}
  r.diagram={nodes:m.nodes,source,candidate,context,difference};
 }catch(e){if(!(e instanceof ResourceLimit))throw e;for(const k of ['context_example','counterexample','unsat_core','core_necessity_witnesses','diagram'])r[k]=null;Object.assign(r,{decision:'resource_limit',limit_reached:e.message});}
 r.work=m.work();r.receipt_sha256=await digest(r);return r;
}
export async function verifyConditional(input){const r=structuredClone(input);if(!r||!r.original_task||!r.limits)throw Error('Invalid conditional receipt');if(canonical(r)!==canonical(await checkConditional(r.original_task,{limits:r.limits})))throw Error('Forged, stale or mismatched conditional receipt');return r.decision;}
export function parseFormula(text){
 if(typeof text!=='string'||new TextEncoder().encode(text).length>4096)throw Error('Formula exceeds text budget');const tokens=[];let pos=0;
 while(pos<text.length){if(/[\t\n\r\f\v \u001c-\u001f\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]/.test(text[pos])){pos++;continue;}const match=/^(->|&&|\|\||[()!&|]|[A-Za-z][A-Za-z0-9_]*)/.exec(text.slice(pos));if(!match)throw Error('Invalid formula token at character '+(pos+1));let token=match[0];pos+=token.length;token=({'&&':'AND','&':'AND','||':'OR','|':'OR','!':'NOT','->':'IMPLIES'})[token]||token;if(RESERVED.includes(token.toUpperCase()))token=token.toUpperCase();tokens.push(token);if(tokens.length>512)throw Error('Formula token budget exceeded');}
 let index=0;const peek=()=>tokens[index],take=()=>tokens[index++];
 function balanced(op,items){if(items.length===1)return items[0];const middle=Math.floor(items.length/2);return {op,left:balanced(op,items.slice(0,middle)),right:balanced(op,items.slice(middle))};}
 function unary(depth){if(depth>32)throw Error('Formula nesting budget exceeded');const token=take();if(token==='NOT')return {op:'not',body:unary(depth+1)};if(token==='('){const node=implication(depth+1);if(take()!==')')throw Error('Expected a closing parenthesis');return node;}if(token==='TRUE'||token==='FALSE')return {op:token.toLowerCase()};if(!token||!/^[A-Z][A-Z0-9_]{0,15}$/.test(token)||RESERVED.includes(token))throw Error('Expected an uppercase variable, TRUE, FALSE or parenthesis');return {op:'atom',symbol:token,args:[]};}
 function conjunction(depth){const items=[unary(depth)];while(peek()==='AND'){take();items.push(unary(depth));}return balanced('and',items);}
 function disjunction(depth){const items=[conjunction(depth)];while(peek()==='OR'){take();items.push(conjunction(depth));}return balanced('or',items);}
 function implication(depth){if(depth>32)throw Error('Formula nesting budget exceeded');let node=disjunction(depth);if(peek()==='IMPLIES'){take();node={op:'implies',left:node,right:implication(depth+1)};}return node;}
 const result=implication(0);if(index!==tokens.length)throw Error('Unexpected trailing formula token');return result;
}
export function conditionalFromText(source,candidate,assumptions=''){
 if(typeof assumptions!=='string'||new TextEncoder().encode(assumptions).length>32768)throw Error('Assumption text exceeds byte budget');const lines=assumptions.split(/\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]/).map(x=>x.replace(/^[\t\n\r\f\v \u001c-\u001f\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\t\n\r\f\v \u001c-\u001f\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/g,'')).filter(Boolean);if(lines.length>8)throw Error('Declare at most eight assumptions, one per line');
 const s=parseFormula(source),c=parseFormula(candidate),premises=lines.map(parseFormula),names=new Set();
 function collect(n){if(n.op==='atom')names.add(n.symbol);else if(n.op==='not')collect(n.body);else if(['and','or','implies'].includes(n.op)){collect(n.left);collect(n.right);}}
 for(const f of [s,c,...premises])collect(f);return validateConditional({format:TASK,variables:[...names].sort(),source:s,candidate:c,assumptions:premises});
}
export const formulaText=f=>f.op==='atom'?f.symbol:f.op==='true'||f.op==='false'?f.op.toUpperCase():f.op==='not'?`NOT (${formulaText(f.body)})`:`(${formulaText(f.left)} ${f.op==='implies'?'->':f.op.toUpperCase()} ${formulaText(f.right)})`;
