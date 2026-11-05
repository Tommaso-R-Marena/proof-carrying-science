#!/usr/bin/env python3
"""Check frozen experiment bytes, checkpoints and reported counts; not a proof verifier.

Actual mathematical acceptance additionally requires fresh Lean replay. This
offline gate detects missing/changed artifacts and inconsistent reported metrics.
"""
import gzip
import hashlib
import json
from pathlib import Path
import tarfile

from pcs.experimental.prover.data import structural_fingerprint
from pcs.experimental.prover.ir import digest
from pcs.experimental.prover.reuse_experiment import metrics
from pcs.experimental.prover.reuse_model import ReuseNetwork

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def check():
    checkpoints = 0
    for generation in (1, 2):
        folder = ROOT / f"research/checked-reuse-v{generation}"
        seal = read(folder / "EVIDENCE_SHA256.json")
        actual = {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in folder.rglob("*") if p.is_file() and p.name != "EVIDENCE_SHA256.json"}
        assert actual == seal, "Evidence bytes or membership changed"
        registry = read(folder / "registry.json")
        assert registry["production_authority"] is False
        assert digest(read(folder / "library.json")) == registry["library_sha256"]
        for entry in registry["models"]:
            assert Path(entry["checkpoint"]).name == entry["checkpoint"]
            model = ReuseNetwork.load(folder / entry["checkpoint"], entry["sha256"])
            assert sum(p.numel() for p in model.parameters()) == entry["parameters"]
            assert entry["pcs_authority"] is False
            checkpoints += 1
        archives = [(folder / "training-source.tar.gz", folder / "source-manifest.json")] if generation == 1 else []
        archives += [(p, p.parent / "source-manifest.json") for p in folder.rglob("source-overlay.tar.gz")]
        for archive, manifest in archives:
            with tarfile.open(archive) as contents:
                members = {m.name: m for m in contents.getmembers() if m.isfile()}
                expected = read(manifest)
                assert set(members) == set(expected)
                for name, sha in expected.items():
                    assert hashlib.sha256(contents.extractfile(members[name]).read()).hexdigest() == sha
        evaluation = json.loads(gzip.decompress((folder / "evaluations.json.gz").read_bytes()))
        summary = read(folder / "summary.json")
        for split, policies in evaluation.items():
            for name, records in policies.items():
                expected = metrics(records)
                observed = summary["metrics"][split][name]
                assert all(observed[k] == v for k, v in expected.items()), (generation, split, name)
                for record in records:
                    receipt = record["result"]["receipt"]
                    if record["result"]["status"] == "verified":
                        assert receipt["goal_sha256"] == digest(record["goal"])
                        assert set(receipt["kernel"]["axioms"]) <= {"propext", "Classical.choice", "Quot.sound"}
    newer = ROOT / "research/checked-reuse-v2"
    tasks = read(newer / "tasks.json")
    assert digest(tasks) == read(newer / "protocol.json")["tasks_sha256"]
    training = read(newer / "training-trajectories.json")
    assert not ({structural_fingerprint(t["goal"]) for t in tasks} &
                {structural_fingerprint(t["goal"]) for t in training})
    assert read(newer / "registry.json")["selection_frozen_before_final"] is True
    print(json.dumps({"pass": True, "checkpoints": checkpoints,
                      "scope": "artifact integrity and metric consistency; not kernel verification"}))


if __name__ == "__main__":
    check()
