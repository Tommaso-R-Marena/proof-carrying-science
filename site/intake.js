const $=id=>document.getElementById(id);
let claimN=0, assumptionN=0;

function esc(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[c]))}
function claimCard(v={}){
  claimN++; const id="claim-"+claimN;
  const div=document.createElement("div");div.className="rowcard";div.dataset.kind="claim";
  div.innerHTML=`
    <header><h3>Claim</h3><button class="smallbutton remove" type="button">Remove</button></header>
    <div class="formgrid">
      <div class="field"><label>Claim ID</label><input class="textinput cid" value="${esc(v.id||("C"+claimN))}"></div>
      <div class="field"><label>Desired assurance</label><select class="selectinput assurance">
        ${["computational","formal","empirical","mixed"].map(x=>`<option ${x===(v.desired_assurance||"computational")?"selected":""}>${x}</option>`).join("")}
      </select></div>
    </div>
    <div class="field"><label>Claim statement</label><textarea class="statement">${esc(v.statement||"")}</textarea></div>
    <div class="field"><label>Rationale</label><textarea class="rationale">${esc(v.rationale||"")}</textarea></div>`;
  div.querySelector(".remove").onclick=()=>{div.remove();refresh()};
  div.querySelectorAll("input,textarea,select").forEach(x=>x.addEventListener("input",refresh));
  $("claims").appendChild(div);
}
function assumptionCard(v={}){
  assumptionN++; const div=document.createElement("div");div.className="rowcard";div.dataset.kind="assumption";
  div.innerHTML=`
    <header><h3>Assumption</h3><button class="smallbutton remove" type="button">Remove</button></header>
    <div class="field"><label>Assumption ID</label><input class="textinput aid" value="${esc(v.id||("A"+assumptionN))}"></div>
    <div class="field"><label>Statement</label><textarea class="astatement">${esc(v.statement||"")}</textarea></div>`;
  div.querySelector(".remove").onclick=()=>{div.remove();refresh()};
  div.querySelectorAll("input,textarea").forEach(x=>x.addEventListener("input",refresh));
  $("assumptions").appendChild(div);
}
function build(){
  const claims=[...$("claims").querySelectorAll('[data-kind="claim"]')].map(x=>({
    id:x.querySelector(".cid").value.trim(),
    statement:x.querySelector(".statement").value.trim(),
    desired_assurance:x.querySelector(".assurance").value,
    rationale:x.querySelector(".rationale").value.trim()
  }));
  const assumptions=[...$("assumptions").querySelectorAll('[data-kind="assumption"]')].map(x=>({
    id:x.querySelector(".aid").value.trim(),
    statement:x.querySelector(".astatement").value.trim()
  }));
  return {
    intake_format:"pcs-pilot-intake-v1",
    pilot_id:$("pilotId").value.trim(),
    workflow_summary:$("workflow").value.trim(),
    claims, assumptions,
    data_classification:$("classification").value,
    notes:$("notes").value.trim()
  };
}
function refresh(){$("preview").textContent=JSON.stringify(build(),null,2)}
function download(){
  const data=JSON.stringify(build(),null,2)+"\n";
  const blob=new Blob([data],{type:"application/json"});
  const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="pilot_intake.json";a.click();URL.revokeObjectURL(a.href);
}
function loadPkpd(){
  $("claims").innerHTML="";$("assumptions").innerHTML="";claimN=assumptionN=0;
  $("pilotId").value="PCS-DEMO-PKPD-001";
  $("workflow").value="Synthetic one-compartment IV-bolus PK with direct Emax PD; verify restricted model contract and analytic replay only.";
  $("classification").value="synthetic";
  $("notes").value="No biological, clinical, regulatory, or model-adequacy claim is requested.";
  claimCard({id:"C_PK_CONTRACT",statement:"The PK model artifact satisfies the restricted positivity and dimensional contract.",desired_assurance:"computational",rationale:"Representation/unit/positivity contract."});
  claimCard({id:"C_PK_REPLAY",statement:"The prediction artifact matches the declared analytic one-compartment IV-bolus PK and direct Emax PD model within the stated numeric tolerance.",desired_assurance:"computational",rationale:"Independent replay against delivered output."});
  assumptionCard({id:"A_PK_MODEL",statement:"The restricted one-compartment IV-bolus equation is the declared computational model; no claim of biological adequacy is made."});
  refresh();
}
$("addClaim").onclick=()=>{claimCard();refresh()};
$("addAssumption").onclick=()=>{assumptionCard();refresh()};
$("download").onclick=download;$("loadPkpd").onclick=loadPkpd;
["pilotId","workflow","classification","notes"].forEach(id=>$(id).addEventListener("input",refresh));
claimCard({id:"C1",statement:"",desired_assurance:"computational",rationale:""});
assumptionCard({id:"A1",statement:""});
refresh();
