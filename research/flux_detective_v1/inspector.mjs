// Bounded offline diagnostic. This module never runs Lean or grants authority.
import {Q} from './engine.mjs';
export const MAX_INPUT_BYTES=256*1024;
const zero=new Q(0n), one=new Q(1n);
function fail(message){throw new Error(message);}
function bound(x){if(x.n.toString(2).replace('-','').length>4096 || x.d.toString(2).length>4096) fail('Browser arithmetic limit exceeded; use the independent CLI.');return x;}
const add=(a,b)=>bound(a.add(b)), sub=(a,b)=>bound(a.sub(b)), mul=(a,b)=>bound(a.mul(b)), div=(a,b)=>bound(a.div(b));
const sum=xs=>xs.reduce(add,zero);
const min=xs=>xs.reduce((a,b)=>a.cmp(b)<0?a:b), max=xs=>xs.reduce((a,b)=>a.cmp(b)>0?a:b);

// Preserve the legacy PCS decimal/fraction grammar, without binary floats.
// Imported aliases are normalized for display; original input bytes are retained.
export function wireRat(s){
  if(typeof s!=='string' || s.length>128 || !/^-?(?:[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]{1,3})?|[0-9]+\/[1-9][0-9]*)$/.test(s)) fail('Unsupported bounded rational.');
  if(s.includes('/')){const [n,d]=s.split('/');return bound(new Q(BigInt(n),BigInt(d)));}
  const [m,e='0']=s.toLowerCase().split('e'), places=(m.split('.')[1]??'').length;
  let n=BigInt(m.replace('.','')),d=10n**BigInt(places),exponent=Number(e);
  if(exponent>=0)n*=10n**BigInt(exponent);else d*=10n**BigInt(-exponent);
  return bound(new Q(n,d));
}

// JSON.parse alone silently accepts duplicate keys. The bounded structural
// parser detects duplicates at every depth, and never evaluates submitted code.
export function strictJSON(raw){
  if(typeof raw!=='string' || new TextEncoder().encode(raw).length>MAX_INPUT_BYTES) fail('Input exceeds the 256 KiB limit.');
  let at=0,nodes=0;
  function ws(){while(/[\x20\t\r\n]/.test(raw[at]??'!'))at++;}
  function string(){
    const start=at++;
    while(at<raw.length){const ch=raw[at++];if(ch==='\\'){at++;continue;}if(ch==='"'){
      const s=JSON.parse(raw.slice(start,at));
      for(const c of s){const point=c.codePointAt(0);if(point>=0xd800&&point<=0xdfff)fail('Unpaired Unicode surrogate.');}
      return s;
    }}
    fail('Unterminated JSON string.');
  }
  function value(depth){
    if(depth>16 || ++nodes>30000)fail('JSON structural budget exceeded.');ws();const ch=raw[at];
    if(ch==='"')return string();
    if(ch==='{' || ch==='['){
      const object=ch==='{', out=object?Object.create(null):[], keys=new Set(),end=object?'}':']';at++;ws();
      if(raw[at]===end){at++;return out;}
      while(true){
        ws();let key;
        if(object){if(raw[at]!=='"')fail('JSON object key required.');key=string();if(keys.has(key))fail('Duplicate JSON key.');keys.add(key);ws();if(raw[at++]!==':')fail('JSON colon required.');}
        const child=value(depth+1);if(object)out[key]=child;else out.push(child);ws();
        const sep=raw[at++];if(sep===end)return out;if(sep!==',')fail('JSON separator required.');
      }
    }
    for(const [word,result] of [['true',true],['false',false],['null',null]])if(raw.startsWith(word,at)){at+=word.length;return result;}
    const token=/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/.exec(raw.slice(at))?.[0];
    if(!token || /[.eE]/.test(token))fail('Integral JSON numeric syntax required.');
    at+=token.length;const number=Number(token);if(!Number.isSafeInteger(number))fail('JSON integer exceeds the exact range.');return number;
  }
  const result=value(0);ws();if(at!==raw.length)fail('Trailing JSON bytes.');return result;
}
function object(x,keys,label){
  if(x===null || typeof x!=='object' || Array.isArray(x))fail(`Exact ${label} fields required.`);
  const actual=Object.keys(x).sort(),expected=[...keys].sort();
  if(actual.length!==expected.length||actual.some((k,i)=>k!==expected[i]))fail(`Exact ${label} fields required.`);
}
function integer(x,low,high){if(!Number.isInteger(x)||x<low||x>high)fail('Integer metadata or dimensions out of range.');}
function text(x,limit){if(typeof x!=='string'||x.length<1||[...x].length>limit)fail('Bounded nonempty text required.');}
function identifier(x){text(x,64);if(!/^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(x))fail('ASCII identifier required.');}

export function inspectCase(raw){
  const b=strictJSON(raw);
  object(b,['format','seed','level','choice','contract','trajectory'],'export');
  if(b.format!=='pcs-flux-detective-export-v1')fail('Unknown export version.');
  integer(b.seed,0,4294967295);integer(b.level,0,5);integer(b.choice,0,2);
  const c=b.contract;
  object(c,['format','question','cells','edges','time_step','steps','units','data_path','data_origin','license','assumptions'],'contract');
  if(c.format!=='pcs-finite-volume-transport-contract-v3'||c.license!=='CC0-1.0'||c.data_origin!=='synthetic_numerical_computation_not_empirical')fail('Unsupported model format or origin.');
  text(c.question,4096);text(c.data_path,256);
  if(c.data_path.includes('\\') || c.data_path.split('/').some(s=>s===''||s==='.'||s==='..') || c.data_path==='contract.json' || c.data_path.split('/')[0]==='pcs-transport-v3')fail('Canonical project-relative data path required.');
  const units={volume:'m^3',concentration:'mol/m^3',conductance:'m^3/s',time:'s'};
  object(c.units,Object.keys(units),'units');if(Object.keys(units).some(k=>c.units[k]!==units[k]))fail('Unsupported units.');
  integer(c.steps,1,64);const dt=wireRat(c.time_step);if(dt.cmp(zero)<=0)fail('Positive time step required.');
  if(!Array.isArray(c.cells)||c.cells.length<2||c.cells.length>16)fail('Supported cell count is 2..16.');
  const ids=[],volumes=[],initial=[];
  for(const cell of c.cells){object(cell,['id','volume','initial_concentration'],'cell');identifier(cell.id);if(ids.includes(cell.id)||cell.id==='time_s')fail('Duplicate or reserved cell identifier.');ids.push(cell.id);const v=wireRat(cell.volume),x=wireRat(cell.initial_concentration);if(v.cmp(zero)<=0||x.cmp(zero)<0)fail('Positive volumes and nonnegative initial concentrations required.');volumes.push(v);initial.push(x);}
  if(!Array.isArray(c.edges)||c.edges.length<1||c.edges.length>64)fail('Supported edge count is 1..64.');
  const matrix=ids.map((_,i)=>ids.map((_,j)=>i===j?one:zero)),seen=new Set();
  for(const e of c.edges){
    object(e,['left','right','conductance'],'edge');const i=ids.indexOf(e.left),j=ids.indexOf(e.right),key=[i,j].sort((a,b)=>a-b).join(':');
    if(i<0||j<0||i===j||seen.has(key))fail('Distinct declared cells and unique edges required.');seen.add(key);
    const g=wireRat(e.conductance);if(g.cmp(zero)<=0)fail('Positive conductance required.');
    for(const [a,d] of [[i,j],[j,i]]){const coefficient=div(mul(dt,g),volumes[a]);matrix[a][d]=add(matrix[a][d],coefficient);matrix[a][a]=sub(matrix[a][a],coefficient);}
  }
  if(matrix.some((row,i)=>row[i].cmp(zero)<0))fail('CFL violation: the declared update is unstable.');
  if(!Array.isArray(c.assumptions)||c.assumptions.length<1||c.assumptions.length>32)fail('Explicit bounded assumptions required.');
  const assumptions=new Set();for(const a of c.assumptions){object(a,['id','statement'],'assumption');identifier(a.id);text(a.statement,4096);if(assumptions.has(a.id))fail('Duplicate assumption.');assumptions.add(a.id);}
  if(typeof b.trajectory!=='string')fail('CSV text required.');
  if(b.trajectory.includes('"'))fail('Quoted CSV is outside the browser subset; use the independent CLI.');
  const lines=b.trajectory.split(/\r\n|\n|\r/);if(lines.at(-1)==='')lines.pop();
  if(lines.shift()!==['time_s',...ids].join(','))fail('Exact trajectory header required.');
  if(lines.length!==c.steps+1)fail('Complete bounded trajectory required.');
  const rows=lines.map(line=>{const parts=line.split(',');if(parts.length!==ids.length+1)fail('Complete CSV row required.');return parts.map(wireRat);});
  const times=rows.map(r=>r[0]),states=rows.map(r=>r.slice(1));let fault=null;
  const note=(kind,k,i,observed,expected)=>{if(!fault&&observed.cmp(expected)!==0)fault={kind,step:k,cell:i,observed:String(observed),expected:String(expected),residual:String(sub(observed,expected))};};
  initial.forEach((x,i)=>note('initial',0,i,states[0][i],x));
  for(let k=0;k<c.steps;k++)matrix.forEach((row,i)=>note('recurrence',k,i,states[k+1][i],sum(row.map((p,j)=>mul(p,states[k][j])))));
  times.forEach((t,k)=>note('time',k,null,t,mul(new Q(BigInt(k)),dt)));
  const amount=row=>sum(row.map((x,i)=>mul(x,volumes[i]))),energy=row=>sum(row.map((x,i)=>mul(mul(x,x),volumes[i])));
  const amounts=states.map(amount),energies=states.map(energy),declaredAmount=amount(initial),lo=min(initial),hi=max(initial);
  const mass=amounts.every(x=>x.cmp(declaredAmount)===0),bounds=states.every(row=>row.every(x=>x.cmp(lo)>=0&&x.cmp(hi)<=0)),historicalEnergy=energies.slice(1).every((e,k)=>e.cmp(energies[k])<=0);
  const span=sub(hi,lo),bars=states.at(-1).map(x=>{if(span.n===0n)return 0;const r=div(sub(x,lo),span),t=r.n*1000n/r.d;return Number(t<0n?0n:t>1000n?1000n:t);});
  return {format:'pcs-browser-trace-diagnostic-v1',status:fault?'BROWSER_MODEL_MISMATCH':'BROWSER_MODEL_MATCH',
    kernel_checked:false,pcs_authority:false,empirical_validation:false,ids,volumes:volumes.map(String),steps:c.steps,
    states:states.map(r=>r.map(String)),times:times.map(String),bars,fault,
    summaries:{mass,bounds,historical_energy:historicalEnergy,declared_amount:String(declaredAmount),final_amount:String(amounts.at(-1)),final_energy:String(energies.at(-1))}};
}
