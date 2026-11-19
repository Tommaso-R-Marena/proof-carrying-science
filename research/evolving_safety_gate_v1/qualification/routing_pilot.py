"""Single zero-shot classification on novel, inert routing cases. Offline by default."""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
from urllib import request, error

from .observation_transfer import cases, would_misroute

HERE = Path(__file__).resolve().parent
MODEL = "gemini-3.5-flash-lite"


def panel():
    rows = [{"item": m.item, "proposed": m.proposal, "executed": m.executed, "note": m.note}
            for m in cases()]
    rows.sort(key=lambda x: hashlib.sha256(json.dumps(x, sort_keys=True).encode()).digest())
    return {f"r{i}": row for i, row in enumerate(rows, 1)}


def payload():
    instruction = ("A controller corrects routing proposals. The routing desk requires atlas north, "
                   "novel south, vase blue, coin green. Did each proposed route violate this policy? "
                   "Answer for the proposal, even when the controller executed a correction. Return "
                   'one JSON object mapping each ID to "wrong", "permitted" or "unknown".\n')
    return json.dumps({"contents": [{"parts": [{"text": instruction + json.dumps(panel())}]}],
                       "generationConfig": {"temperature": 0, "maxOutputTokens": 768,
                                            "responseMimeType": "application/json"}}).encode()


def collect(path):
    with path.open("x") as out:
        raw = payload()
        receipt = {"model": MODEL, "payload_sha256": hashlib.sha256(raw).hexdigest(),
                   "attempts": 1, "retries": 0}
        key = os.environ.get("GEMINI_API_KEY") or getpass.getpass("Credential: ")
        req = request.Request("https://generativelanguage.googleapis.com/v1beta/models/" + MODEL +
                              ":generateContent", data=raw,
                              headers={"Content-Type": "application/json", "X-goog-api-key": key})
        try:
            with request.urlopen(req, timeout=90) as res:
                d = json.load(res)
                receipt.update(status=res.status, modelVersion=d.get("modelVersion"),
                               usage=d.get("usageMetadata"), candidates=d.get("candidates", []))
        except error.HTTPError as exc:
            receipt["status"] = exc.code
        finally:
            json.dump(receipt, out, sort_keys=True, indent=2)
            out.write("\n")
    print("HTTP status", receipt.get("status"))


def unique(pairs):
    if len(dict(pairs)) != len(pairs):
        raise ValueError("duplicate answer")
    return dict(pairs)


def replay(path):
    record = json.loads(path.read_bytes())
    if record["payload_sha256"] != hashlib.sha256(payload()).hexdigest() or record["model"] != MODEL:
        raise ValueError("request differs")
    reply, = record["candidates"]
    if record.get("status") != 200 or reply["finishReason"] != "STOP":
        raise ValueError("incomplete response")
    answers = json.loads("".join(p["text"] for p in reply["content"]["parts"]), object_pairs_hook=unique)
    rows = panel()
    expected = {(m.item, m.proposal): "wrong" if would_misroute(m) else "permitted" for m in cases()}
    return {"correct": sum(answers.get(i) == expected[(r["item"], r["proposed"])] for i, r in rows.items()),
            "n": len(rows), "abstained": sum(answers.get(i) == "unknown" for i in rows),
            "protocol_valid": set(answers) == set(rows) and
            all(v in ("wrong", "permitted", "unknown") for v in answers.values())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["collect", "replay"])
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    if args.action == "collect":
        collect(args.receipt)
    else:
        print(json.dumps(replay(args.receipt), sort_keys=True))
