"""Freeze a label-blind text batch, issue one optional request, or replay its score."""
from pathlib import Path
import argparse
import getpass
import hashlib
import json
import os
from urllib import request, error, parse

HERE = Path(__file__).resolve().parent
MODEL = "gemini-3.5-flash-lite"
Q_SHA = "7ca1e3c0aa3d0e3ab7f0a31d469c9a7ce738526c7a78b2e5649d17670c27b699"
M_SHA = "f288ed9046a1ef5e39c0dbf6b971b8a3a485887130b7831dc5da4fe2af5d64b5"
INSTRUCTION = ("For each unrelated causal reasoning item, answer the question from the provided text. "
               "Return a JSON object with exactly the provided item IDs as keys; values must be "
               '"yes", "no" or "unknown". No reasoning or extra keys.\n')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_file(path, digest):
    raw = path.read_bytes()
    if sha(raw) != digest:
        raise ValueError("dataset digest mismatch")
    return json.loads(raw)


def sample(questions):
    return sorted(questions, key=lambda q: sha(("pcs-blind-gemini-pilot-v1/" +
        str(q["question_id"])).encode()))[:12]


def make_batch(data):
    questions = load_file(data / "cladder-v1-q-balanced.json", Q_SHA)
    models = {m["model_id"]: m for m in load_file(data / "cladder-v1-meta-models.json", M_SHA)}
    rows = []
    for i, q in enumerate(sample(questions), 1):
        rows.append({"id": f"q{i}", "background": models[q["meta"]["model_id"]]["background"],
                     "given_info": q["given_info"], "question": q["question"]})
    return json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()


def payload(batch):
    return json.dumps({"contents": [{"parts": [{"text": INSTRUCTION + batch.decode()}]}],
                       "generationConfig": {"temperature": 0, "maxOutputTokens": 768,
                                            "responseMimeType": "application/json"}}).encode()


def call(batch_path, save):
    batch = batch_path.read_bytes()
    raw = payload(batch)
    with save.open("x") as out:
        record = {"model": MODEL, "input_sha256": sha(batch), "payload_sha256": sha(raw),
                  "attempts": 1, "retries": 0}
        key = os.environ.get("GEMINI_API_KEY") or getpass.getpass("Credential: ")
        req = request.Request("https://generativelanguage.googleapis.com/v1beta/models/" + MODEL +
                              ":generateContent", data=raw,
                              headers={"Content-Type": "application/json", "X-goog-api-key": key})
        try:
            with request.urlopen(req, timeout=90) as res:
                d = json.load(res)
                record.update(status=res.status, modelVersion=d.get("modelVersion"),
                              usage=d.get("usageMetadata"), candidates=d.get("candidates", []))
        except error.HTTPError as exc:
            record.update(status=exc.code)
        finally:
            json.dump(record, out, sort_keys=True, indent=2)
            out.write("\n")
    print("HTTP status", record.get("status"))


def unique(pairs):
    if len(pairs) != len(dict(pairs)):
        raise ValueError("duplicate candidate ID")
    return dict(pairs)


def score(data, receipt):
    batch = make_batch(data)
    if receipt["input_sha256"] != sha(batch) or receipt["payload_sha256"] != sha(payload(batch)):
        raise ValueError("input differs")
    if receipt["model"] != MODEL or receipt.get("status") != 200:
        raise ValueError("wrong model or incomplete response")
    candidate, = receipt["candidates"]
    if candidate["finishReason"] != "STOP":
        raise ValueError("unfinished reply")
    response = json.loads("".join(p["text"] for p in candidate["content"]["parts"]), object_pairs_hook=unique)
    expected = sample(load_file(data / "cladder-v1-q-balanced.json", Q_SHA))
    rows = []
    for i, q in enumerate(expected, 1):
        ans = response.get(f"q{i}")
        rows.append({"id": f"q{i}", "source_id": q["question_id"], "prediction": ans,
                     "gold": q["answer"], "correct": ans == q["answer"]})
    valid = all(r["prediction"] in ("yes", "no", "unknown") for r in rows)
    return {"correct": sum(r["correct"] for r in rows), "n": len(rows),
            "protocol_valid": valid and set(response) == {r["id"] for r in rows}, "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    for action, paths in [("prepare", ("data", "batch")), ("request", ("batch", "receipt")),
                          ("score", ("data", "receipt"))]:
        p = sub.add_parser(action)
        for path in paths:
            p.add_argument(path, type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        with args.batch.open("xb") as out:
            out.write(make_batch(args.data))
    elif args.action == "request":
        call(args.batch, args.receipt)
    else:
        print(json.dumps(score(args.data, json.loads(args.receipt.read_bytes())), sort_keys=True, indent=2))
