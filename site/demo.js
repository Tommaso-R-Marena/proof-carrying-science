const $=id=>document.getElementById(id);
const dose=100, V=20, CL=2;
const expected=t=>(dose/V)*Math.exp(-(CL/V)*t);
let baseObserved=expected(4);

function shaLike(input){
  let h=2166136261;
  for(const ch of input){h^=ch.charCodeAt(0);h=Math.imul(h,16777619)}
  return (h>>>0).toString(16).padStart(8,"0").repeat(8).slice(0,64);
}
function setStatus(card,status,value){
  card.classList.remove("pass","fail","warn");
  if(status) card.classList.add(status);
  card.querySelector(".value").textContent=value;
}
function sync(){
  const t=+$("time").value;
  $("timeLabel").textContent=t+" h";
  baseObserved=expected(t);
  $("concentration").min=Math.max(0,baseObserved-2).toFixed(2);
  $("concentration").max=(baseObserved+2).toFixed(2);
  $("concentration").value=baseObserved.toFixed(4);
  $("concLabel").textContent=baseObserved.toFixed(4)+" mg/L";
}
function run(){
  const t=+$("time").value;
  const exp=expected(t);
  const tampered=$("tamper").checked;
  const observed= tampered ? exp+0.75 : exp;
  $("concentration").value=observed.toFixed(4);
  $("concLabel").textContent=observed.toFixed(4)+" mg/L";
  const replay=Math.abs(observed-exp) <= 1e-6;
  const integrity=!tampered;
  const authenticity=!tampered;
  const strict=$("strictPolicy").checked;
  const policy=replay && !strict;

  setStatus($("replayCard"),replay?"pass":"fail",replay?"PASS":"FAIL");
  setStatus($("integrityCard"),integrity?"pass":"fail",integrity?"PASS":"FAIL");
  setStatus($("authCard"),authenticity?"pass":"fail",authenticity?"VERIFIED":"INVALID");
  setStatus($("policyCard"),policy?"pass":"fail",policy?"PASS":"FAIL");
  $("contractDot").className="dot pass";
  $("replayDot").className="dot "+(replay?"pass":"fail");

  const cert={
    spec_version:"pcs-demo-v1",
    subject:"synthetic-pkpd-browser-demo",
    assumptions:["restricted one-compartment IV-bolus PK + direct Emax PD is the declared computational model"],
    claims:{
      C_PKPD_CONTRACT:"COMPUTATIONALLY_SUPPORTED",
      C_PKPD_REPLAY:replay?"COMPUTATIONALLY_SUPPORTED":"FALSIFIED_OR_CHECK_FAILED"
    },
    replay:{time_h:t,expected_mg_L:+exp.toFixed(8),observed_mg_L:+observed.toFixed(8),abs_error:+Math.abs(observed-exp).toFixed(8)},
    package_integrity:integrity?"PASS":"FAIL",
    signer_authenticity:authenticity?"VERIFIED":"INVALID",
    reviewer_policy:strict?"requires FORMALLY_VERIFIED_UNDER_ASSUMPTIONS":"accepts COMPUTATIONALLY_SUPPORTED",
    semantic_hash:shaLike(JSON.stringify([t,exp,replay,strict]))
  };
  $("certificate").textContent=JSON.stringify(cert,null,2);
}
$("verify").addEventListener("click",run);
$("reset").addEventListener("click",()=>{$("tamper").checked=false;$("strictPolicy").checked=false;$("time").value=4;sync();["replayCard","integrityCard","authCard","policyCard"].forEach(id=>setStatus($(id),"","NOT RUN"));$("contractDot").className="dot";$("replayDot").className="dot";$("certificate").textContent='{ "status": "not run" }';});
$("time").addEventListener("input",sync);
$("tamper").addEventListener("change",run);
$("strictPolicy").addEventListener("change",run);
sync();
