"""Receiver-owned public CI proof request; no submitted source/code execution."""
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import time

from .cli import run
from .induction_ir import digest
from .environment import LeanEnvironment, render_action
from .induction_language import formalize, explain


def check_actions(statement, actions, interpretation=None):
    """Compile the user's exact typed path against an immutable interpretation."""
    if type(actions) is not list or not 1 <= len(actions) <= 24:
        raise ValueError("bounded typed proof actions required")
    for action in actions: render_action(action)
    formal = formalize(statement)
    result = {"formalization": formal, "pcs_authority": False}
    if formal["status"] == "unsupported": return {**result, "status": "unsupported_formalization"}
    if interpretation is None and formal["status"] == "ambiguous": return {**result, "status": "ambiguous_interpretation"}
    index = interpretation if interpretation is not None else 0
    if type(index) is not int or not 0 <= index < len(formal["candidates"]):
        raise ValueError("invalid interpretation")
    goal = formal["candidates"][index]["ir"]
    env = LeanEnvironment(timeout=30)
    try:
        observation = env.observe(goal, actions)
        if observation["status"] != "closed":
            return {**result, "status": "unknown", "reason": observation.get("error") or "Proof still has open goals",
                    "observation": observation, "search": {"receipt": None}}
        receipt = env.verify(goal, actions)
        return {**result, "status": "verified", "explanation": explain(goal),
                "search": {"receipt": receipt, "states": observation["states"],
                           "expansions": len(actions), "lean_invocations": env.invocations},
                "mode": "exact human proof actions; fresh kernel compilation"}
    except RuntimeError as ex:
        return {**result, "status": "resource_exhaustion", "reason": str(ex)[-2000:]}
    finally: env.close()


def run_stage(name, statement, registry, interpretation, domain=None):
    # Operational diagnostics only: no user text, credentials or proof authority.
    print("PCS_LEAN_PROGRESS_V1:" + json.dumps({"stage": name, "status": "started"}), flush=True)
    started = time.monotonic()
    result = run(statement, registry, budget=96, interpretation=interpretation,domain=domain)
    print("PCS_LEAN_PROGRESS_V1:" + json.dumps({"stage": name, "status": result["status"],
                                               "wall_seconds": time.monotonic() - started}), flush=True)
    return result


def main():
    request_id = os.environ.get("PCS_PUBLIC_REQUEST_ID", "")
    statement = os.environ.get("PCS_PUBLIC_STATEMENT", "")
    choice = os.environ.get("PCS_PUBLIC_INTERPRETATION", "")
    if not re.fullmatch(r"[0-9a-f]{32}", request_id) or not 1 <= len(statement) <= 3000:
        raise ValueError("invalid public request")
    if choice and not re.fullmatch(r"[0-9]{1,2}", choice): raise ValueError("invalid interpretation")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    interpretation = int(choice) if choice else None
    raw_actions = os.environ.get("PCS_PUBLIC_PROOF_ACTIONS", "")
    if len(raw_actions) > 6000: raise ValueError("action payload exceeds bound")
    actions = json.loads(raw_actions) if raw_actions else None
    family=os.environ.get("PCS_PUBLIC_MODEL_FAMILY","")
    if family not in {"","induction-abstraction-v2"} or (family and actions is not None):raise ValueError("invalid model-family request")
    if actions is not None:
        result = check_actions(statement, actions, interpretation)
        previous = baseline = None
    elif family:
        result=run_stage("grounded_induction",statement,"research/induction-abstraction-v2",interpretation,"induction")
        previous=run_stage("previous_policy_extended_actions",statement,"research/lean-learning-v2",interpretation,"induction")
        baseline=run_stage("symbolic_induction",statement,None,interpretation,"induction")
    else:
        result = run_stage("checked_reuse", statement, "research/checked-reuse-v2", interpretation)
        previous = run_stage("previous_policy", statement, "research/lean-learning-v2", interpretation)
        baseline = run_stage("symbolic", statement, None, interpretation)
    for observation in [result, previous, baseline]:
        if observation is None: continue
        if observation.get("search") and "attempts" in observation["search"]:
            observation["search"]["attempts"] = [{k: v for k, v in a.items() if k != "state"} for a in observation["search"]["attempts"]]
    response = {"format": "pcs-public-lean-result-v1", "request_id": request_id,
                "source_sha256": digest(statement), "core_sha": revision, "result": result, "previous": previous, "baseline": baseline,
                "source_license": "CC0-1.0", "automatic_training_authorization": False}
    if actions is not None: response["actions_sha256"] = digest(actions)
    if family:response["model_family"]=family
    raw = json.dumps(response, separators=(",", ":"), ensure_ascii=False).encode()
    if len(raw) > 1_000_000:
        response["result"] = {"status": "resource_exhaustion", "reason": "public result exceeds 1 MB", "pcs_authority": False}
        response.pop("baseline", None)
        response.pop("previous", None)
        raw = json.dumps(response, separators=(",", ":"), ensure_ascii=False).encode()
    # One mandatory marker. A fabricated marker in submitted text would produce
    # duplicates and is rejected by the receiver; failed jobs cannot authorize.
    print("PCS_LEAN_RESULT_V1:" + base64.b64encode(raw).decode(), flush=True)


if __name__ == "__main__": main()
