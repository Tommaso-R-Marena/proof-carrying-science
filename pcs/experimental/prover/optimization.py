"""Learned CertIR proposal ranking using the existing independent Rust checker.

The receiver pins the checker executable. Complete u8 replay is bounded Rust
evidence, never a Lean certificate, universal large-domain proof or runtime gain.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time

import torch
from torch import nn

OPS = ["add", "and", "or", "xor"]


def features(original, candidate):
    return [original.count(op + "(") / 4 for op in OPS] + [candidate.count(op + "(") / 4 for op in OPS] + [
        float("x, x" in original), float("y, y" in original), float(candidate == "x"),
        float(candidate == "y"), float(candidate == "u8(0)"), len(candidate) / 100]


def checker(binary, expected_sha, original, candidate, folder):
    if hashlib.sha256(binary.read_bytes()).hexdigest() != expected_sha:
        raise ValueError("CertiForge checker integrity failure")
    original_path, candidate_path = folder / "original.certir", folder / "candidate.certir"
    original_path.write_text(f"fn original(x: u8, y: u8) -> u8 {{ {original} }}\n")
    candidate_path.write_text(f"fn candidate(x: u8, y: u8) -> u8 {{ {candidate} }}\n")
    package = folder / "package"
    built = subprocess.run([str(binary), "package", "build", str(original_path), "--optimized", str(candidate_path),
        "--out", str(package)], capture_output=True, text=True, timeout=30)
    if built.returncode:
        return {"accepted": False, "error": (built.stdout + built.stderr)[-2000:]}
    verified = subprocess.run([str(binary), "package", "verify", str(package), "--json"], capture_output=True, text=True, timeout=30)
    result = json.loads(verified.stdout)
    accepted = verified.returncode == 0 and result["result"]["result"] == "accept"
    return {"accepted": accepted, "evidence": result}


def reproduce(binary, output):
    binary, output = Path(binary).resolve(), Path(output)
    if not binary.is_file(): raise ValueError("separately built CertiForge binary required")
    output.mkdir(parents=True, exist_ok=False)
    sha = hashlib.sha256(binary.read_bytes()).hexdigest()
    original_tasks = [("train", "or(x, x)"), ("train", "and(x, x)"), ("train", "xor(x, x)"),
                      ("train", "add(x, u8(0))"), ("final", "add(and(x, y), xor(x, y))"),
                      ("final", "or(and(x, x), y)")]
    alternatives = ["x", "y", "u8(0)", "or(x, y)", "xor(x, y)", "and(x, y)", "add(x, y)"]
    protocol = {"checker_sha256": sha, "tasks": original_tasks, "candidates": alternatives,
                "budget": 4, "selection": "first independently accepted strict AST-cost reduction",
                "domain": "all 65536 u8 input pairs", "runtime_gain_measured": False}
    (output / "protocol.json").write_text(json.dumps(protocol, indent=2))
    data = []
    start = time.monotonic()
    for split, original in original_tasks:
        records = []
        for i, candidate in enumerate(alternatives):
            folder = output / f"task{len(data)}-candidate{i}"
            folder.mkdir()
            evidence = checker(binary, sha, original, candidate, folder)
            improvement = evidence["accepted"] and evidence["evidence"]["cost"]["optimized"] < evidence["evidence"]["cost"]["original"]
            records.append({"candidate": candidate, "improvement": bool(improvement), "check": evidence})
        data.append({"split": split, "original": original, "records": records})
    torch.manual_seed(23)
    model = nn.Sequential(nn.Linear(14, 24), nn.Tanh(), nn.Linear(24, 1))
    before = {k: v.detach().clone() for k, v in model.state_dict().items()}
    optimizer = torch.optim.Adam(model.parameters(), lr=.015)
    for _ in range(120):
        for task in data:
            if task["split"] != "train": continue
            x = torch.tensor([features(task["original"], r["candidate"]) for r in task["records"]])
            y = torch.tensor([float(r["improvement"]) for r in task["records"]])
            logits = model(x).squeeze(1)
            loss = nn.functional.binary_cross_entropy_with_logits(logits, y)
            optimizer.zero_grad(); loss.backward(); optimizer.step()
    evaluations = []
    for task in data:
        if task["split"] != "final": continue
        with torch.no_grad():
            scores = model(torch.tensor([features(task["original"], r["candidate"]) for r in task["records"]])).squeeze(1).tolist()
        order = sorted(range(len(scores)), key=lambda i: -scores[i])
        # Check selected actions AGAIN; training/evaluation labels cannot authorize.
        checked = []
        for i in order[:4]:
            folder = output / f"recheck-{len(evaluations)}-{i}"
            folder.mkdir()
            checked.append({"candidate": alternatives[i], "check": checker(binary, sha, task["original"], alternatives[i], folder)})
            if checked[-1]["check"]["accepted"] and checked[-1]["check"]["evidence"]["cost"]["optimized"] < checked[-1]["check"]["evidence"]["cost"]["original"]: break
        original_file = output / f"baseline-{len(evaluations)}.certir"
        original_file.write_text(f"fn baseline(x: u8, y: u8) -> u8 {{ {task['original']} }}")
        baselines = []
        for seed in [1, 2, 3]:
            result = subprocess.run([str(binary), "optimize", str(original_file), "--max-candidates", "4", "--seed", str(seed)],
                                    capture_output=True, text=True, timeout=30)
            baselines.append({"seed": seed, "exit": result.returncode, "output": result.stdout, "error": result.stderr})
        evaluations.append({"original": task["original"], "ranked_candidates": [alternatives[i] for i in order],
                            "model_checks": checked, "forgeopt_baselines": baselines})
    weights = {k: v.detach().tolist() for k, v in model.state_dict().items()}
    (output / "checkpoint.json").write_text(json.dumps({"architecture": "14-24-1-tanh", "weights": weights}, separators=(",", ":")))
    report = {"format": "pcs-learned-certiforge-v1", "parameters": sum(p.numel() for p in model.parameters()),
              "training_pairs": 28, "epochs": 120, "checker_sha256": sha, "dataset": data,
              "weights_changed": any(not torch.equal(before[k], v) for k, v in model.state_dict().items()),
              "evaluations": evaluations, "wall_seconds": time.monotonic() - start, "pcs_authority": False,
              "limitations": "Four training expression families and two held-out families; full u8 Rust replay only. No optimization RL, large-domain proof, Rust/Lean refinement or empirical runtime result."}
    (output / "report.json").write_text(json.dumps(report, indent=2))
    return report
