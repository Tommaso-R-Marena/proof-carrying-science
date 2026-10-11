"""Independent Lean intake for explicit adult CC0 Bridge Builder exports.

Consent/authentication are application provenance assumptions, never inferred
from gameplay. This command rechecks mathematical labels, not consent validity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .bridge_catalog import VERSION
from .environment import LeanEnvironment
from .ir import digest
from .data import intake_feedback, structural_fingerprint


def replay_session(env, catalog, session):
    keys = {"format", "version", "catalog_sha256", "mission_id", "events"}
    if type(session) is not dict or set(session)!=keys or session["format"]!="pcs-bridge-session-v1" or session["version"]!=VERSION or session["catalog_sha256"]!=catalog["content_sha256"]:
        raise ValueError("invalid session/catalog binding")
    mission = next((m for m in catalog["missions"] if m["id"] == session["mission_id"]),None)
    if mission is None: raise ValueError("unknown mission")
    if type(session["events"]) is not list or len(session["events"])>120: raise ValueError("event limit")
    current, stack, last, hints, transitions = mission["start"], [mission["start"]], -1, 0, []
    for event_index,event in enumerate(session["events"]):
        if type(event) is not dict or set(event)!={"kind", "node", "edge", "sequence"} or event["node"]!=current or type(event["sequence"]) is not int or event["sequence"]!=event_index:
            raise ValueError("invalid or reordered event")
        last=event["sequence"]; kind=event["kind"]
        if kind=="undo":
            if event["edge"] is not None or len(stack)<2: raise ValueError("invalid undo")
            stack.pop();current=stack[-1];continue
        if kind=="hint":
            if event["edge"] is not None or not mission["nodes"][current]["state"]["goals"]: raise ValueError("invalid hint")
            hints+=1;continue
        edges=mission["nodes"][current]["edges"]
        if kind!="choose" or type(event["edge"]) is not int or not 0<=event["edge"]<len(edges): raise ValueError("invalid choice")
        edge=edges[event["edge"]];path=mission["nodes"][current]["path"]
        before=env.observe(mission["goal"],path)["states"][-1]
        after=env.observe(mission["goal"],path+[edge["action"]])
        if after["status"]!=edge["status"]: raise ValueError("catalog transition failed fresh Lean replay")
        transitions.append({"state":before,"action":edge["action"],"checker_status":after["status"],"hint_exposed":hints>0})
        if edge["status"]!="invalid":
            if not edge["next"] or mission["nodes"][edge["next"]]["path"]!=path+[edge["action"]]: raise ValueError("changed path")
            current=edge["next"];stack.append(current)
    path=mission["nodes"][current]["path"]
    observed=env.observe(mission["goal"],path)
    receipt=env.verify(mission["goal"],path) if observed["status"]=="closed" else None
    return mission,transitions,receipt,hints


def intake(catalog, export, *, heldout=(), cache=None):
    if digest({k:v for k,v in catalog.items() if k!="content_sha256"})!=catalog["content_sha256"]: raise ValueError("changed catalog")
    if export.get("format")!="pcs-bridge-consented-export-v1" or export.get("version")!=VERSION or type(export.get("entries")) is not list or len(export["entries"])>25:
        raise ValueError("authorized export envelope required")
    env=LeanEnvironment(cache=cache,timeout=30);entries=[];negatives=[]
    try:
        for record in export["entries"]:
            if record.get("license")!="CC0-1.0" or record.get("adult_consented") is not True or record.get("training_consented") is not True:
                raise ValueError("explicit adult CC0 research provenance required")
            mission,transitions,receipt,hints=replay_session(env,catalog,record["session"])
            if structural_fingerprint(mission["goal"]) in {structural_fingerprint(t["goal"]) for t in heldout}:
                raise ValueError("evaluation contamination")
            negatives.extend({"source_session_sha256":digest(record["session"]),**t} for t in transitions if t["checker_status"]=="invalid")
            if receipt:
                entry=intake_feedback(env,{"goal":mission["goal"],"receipt":receipt,"original_statement":mission["statement"],"hint_exposure":hints>0},
                    heldout,license="CC0-1.0",source_revision=catalog["core_revision"])
                entry.update(source="consented Bridge Builder export",source_session_sha256=digest(record["session"]),
                    human_transitions=transitions,automatic_setup_actions=mission["automatic_setup_actions"],
                    consent_boundary="Application-authenticated adult CC0 opt-in; not mathematically proved consent")
                entries.append(entry)
        return {"format":"pcs-bridge-kernel-intake-v1","verified_training_examples":entries,
                "independently_checked_invalid_transitions":negatives,"automatic_training_authorization":False,"pcs_authority":False,
                "source_catalog_sha256":catalog["content_sha256"],"source_export_sha256":digest(export)}
    finally:env.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--catalog",required=True);p.add_argument("--export",required=True);p.add_argument("--heldout",required=True);p.add_argument("--output",required=True);a=p.parse_args()
    paths=[Path(a.catalog),Path(a.export),Path(a.heldout)]
    if any(x.stat().st_size>2_000_000 for x in paths): raise ValueError("dataset bound")
    c,e,h=[json.loads(x.read_text()) for x in paths]
    result=intake(c,e,heldout=[t for t in h if t["split"]!="train"])
    Path(a.output).write_text(json.dumps(result,indent=2)+"\n")


if __name__=="__main__":main()
