"""Receiver-owned public CI proof request; no submitted source/code execution."""
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import time

from .cli import run
from .ir import digest


def run_stage(name, statement, registry, interpretation):
    # Operational diagnostics only: no user text, credentials or proof authority.
    print("PCS_LEAN_PROGRESS_V1:" + json.dumps({"stage": name, "status": "started"}), flush=True)
    started = time.monotonic()
    result = run(statement, registry, budget=96, interpretation=interpretation)
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
    result = run_stage("checked_reuse", statement, "research/checked-reuse-v2", interpretation)
    previous = run_stage("previous_policy", statement, "research/lean-learning-v2", interpretation)
    baseline = run_stage("symbolic", statement, None, interpretation)
    for observation in [result, previous, baseline]:
        if observation.get("search"):
            observation["search"]["attempts"] = [{k: v for k, v in a.items() if k != "state"} for a in observation["search"]["attempts"]]
    response = {"format": "pcs-public-lean-result-v1", "request_id": request_id,
                "source_sha256": digest(statement), "core_sha": revision, "result": result, "previous": previous, "baseline": baseline,
                "source_license": "CC0-1.0", "automatic_training_authorization": False}
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
