import {Q,puzzle} from '../flux_detective_v1/engine.mjs';
import {pairRegion,regionFor,forgeCase,sliderAmount} from '../flux_detective_v1/forge.mjs';
const q=Q.parse;
if(process.argv[2]==='pairs') {
  const rows=[];
  for(let v=1;v<=4;v++) for(let w=1;w<=4;w++) for(let a=0;a<=4;a++) for(let b=0;b<=4;b++) {
    const x=new Q(BigInt(a),4n),y=new Q(BigInt(b),4n),r=pairRegion(q(String(v)),q(String(w)),x,y,q('0'),q('1'));
    rows.push({v:String(v),w:String(w),x:String(x),y:String(y),low:String(r.low),high:String(r.high),root:String(r.root)});
  }
  process.stdout.write(JSON.stringify(rows)+'\n');
} else {
  const seeds=process.argv.length>2?process.argv.slice(2).map(Number):[0,20261021,4294967295];
  const rows=[];
  for(const seed of seeds) for(let level=0;level<6;level++) {
    const p=puzzle(seed,level);
    for(let i=0;i<p.contract.cells.length;i++) for(let j=0;j<p.contract.cells.length;j++) if(i!==j) {
      const r=regionFor(p,i,j);
      const amounts=[String(r.low.sub(q('1/8'))),String(r.low.sub(q('1/1024'))),sliderAmount(r,0),sliderAmount(r,25),sliderAmount(r,50),sliderAmount(r,75),sliderAmount(r,100),String(r.high.add(q('1/1024'))),String(r.high.add(q('1/8')))];
      for(const amount of amounts) {
        const f=forgeCase(p,i,j,amount);rows.push({seed,level,left:i,right:j,summary:f.summary,analysis:f.analysis,bundle:f.bundle});
      }
    }
  }
  process.stdout.write(JSON.stringify(rows)+'\n');
}
