"""Post-hoc replay of the prior nonvacuous guard AND pointwise dominance."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from dominance import certificate
from receive import Kernel, RESEARCH, ROOT, audit, canonical, digest, rows
from guard import guard_expression
from affine_certificates import certificate as prior_certificate
from proof_gate import parse_model
from universal_relu import Net, Term, single_neuron

TARGET = Net((Term(1, 2, 1),))


def run(output, decisions):
    k = Kernel(output)
    source = HERE / "PreservedGuard.lean"
    prior = RESEARCH / "kernel/results/v1/MODEL_CLASSIFICATION.json"
    sources = {
        str(p.relative_to(ROOT)): digest(p) for p in (source, prior, Path(__file__))
    }
    expected_sha = digest(decisions)
    data = json.loads(Path(decisions).read_text())
    classifications = json.loads(prior.read_text())
    models = [parse_model(m) for m in data["models"]]
    assert len(models) == 128 and len(data["transitions"]) == 16384
    witnesses = {parse_model(c["model"]): c["correct_witness"] for c in classifications}
    p = subprocess.run(
        [
            k.base.lean,
            "-M4096",
            "--root=" + str(HERE),
            "-o",
            str(k.output / "PreservedGuard.olean"),
            str(source),
        ],
        env=k.env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    (k.output / "PreservedGuard.log").write_text(p.stdout + p.stderr)
    if p.returncode or p.stderr:
        raise RuntimeError("Preserved guard failed to compile")
    audit(
        p.stdout,
        {
            "PCS.Research.PreservedPointwiseGuard.accepts_sound",
            "PCS.Research.PreservedPointwiseGuard.first_update",
            "PCS.Research.PreservedPointwiseGuard.second_update",
        },
    )
    k.pins[k.output / "PreservedGuard.olean"] = digest(
        k.output / "PreservedGuard.olean"
    )
    pending, records, accepted = [], [], []

    def flush():
        if not pending:
            return
        name = "PreservedBatch" + str(len(records)).zfill(3)
        raw = (
            "import PreservedGuard\nset_option maxRecDepth 10000\nset_option maxHeartbeats 20000000\n"
            "open PCS.Research.IntegerAffine PCS.Research.PGSI1Bridge PCS.Research.Pointwise PCS.Research.PreservedPointwiseGuard\n"
            "namespace PCS.Research.PreservedPointwiseReplay\n"
            "def cases : List Case := [\n" + ",\n".join(pending) + "]\n"
            "theorem checked : cases.all accepts = true := by decide\n"
            "theorem cases_sound : ∀ c ∈ cases, GuardMeaning c.prior ∧ Dominates (embed c.prior.old) (embed c.prior.new) targetNet := by\n"
            "  intro c hc\n  exact accepts_sound c (List.all_eq_true.mp checked c hc)\n"
            "#print axioms cases_sound\nend PCS.Research.PreservedPointwiseReplay\n"
        ).encode()
        path = k.output / (name + ".lean")
        with path.open("xb") as f:
            f.write(raw)
        sha = hashlib.sha256(raw).hexdigest()
        if digest(path) != sha:
            raise RuntimeError("Proof changed before replay")
        start = time.perf_counter()
        ax = audit(k.run(path), {"PCS.Research.PreservedPointwiseReplay.cases_sound"})
        if digest(path) != sha:
            raise RuntimeError("Proof changed during replay")
        records.append(
            {
                "file": path.name,
                "sha256": sha,
                "claims": len(pending),
                "axioms": ax,
                "elapsed_seconds": time.perf_counter() - start,
            }
        )
        pending.clear()
        print(
            json.dumps(
                {"batches": len(records), "claims": sum(r["claims"] for r in records)}
            ),
            flush=True,
        )

    for i, d in enumerate(data["transitions"]):
        assert d["old"] == i // 128 and d["new"] == i % 128
        if not (d["finite"] and d["pointwise"]):
            continue
        old, new = models[d["old"]], models[d["new"]]
        witness = witnesses[old]
        if witness is None:
            continue
        a, b = (single_neuron(m.relu, m.weight, m.bias) for m in (old, new))
        cert = certificate(a, b, TARGET)
        assert cert["result"]["passes"]
        pc = prior_certificate("preserves", (a, b, TARGET))
        oc, nc = (
            prior_certificate("max_error", (n, TARGET), (-20, 20)) for n in (a, b)
        )
        guard = guard_expression(old, new, pc, oc, nc, -20, 20, witness)
        pending.append("⟨" + guard + "," + rows(cert, 3) + "⟩")
        accepted.append([d["old"], d["new"]])
        if len(pending) == 64:
            flush()
    flush()
    assert len(accepted) == 673
    assert (
        sources == {name: digest(ROOT / name) for name in sources}
        and digest(decisions) == expected_sha
    )
    (k.output / source.name).write_bytes(source.read_bytes())
    semantic = {
        "accepted_compositions": len(accepted),
        "pairs_sha256": hashlib.sha256(canonical(accepted)).hexdigest(),
    }
    result = {
        "format": "pgsi-preserved-pointwise-campaign-v1",
        "post_hoc": True,
        **semantic,
        "semantic_results_sha256": hashlib.sha256(canonical(semantic)).hexdigest(),
        "sources": sources,
        "core_sources": k.sources,
        "decisions_sha256": expected_sha,
        "proofs": records,
        "pairs": accepted,
        "production_authority": False,
        "native_execution_refinement_proved": False,
        "external_scientific_validation": False,
    }
    (k.output / "RESULT.json").write_bytes(canonical(result) + b"\n")
    with (k.output / "PROOFS.tar.gz").open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(mode="w", fileobj=gz) as archive:
                for record in records:
                    path = k.output / record["file"]
                    info = archive.gettarinfo(str(path), arcname=path.name)
                    info.uid = info.gid = info.mtime = 0
                    info.uname = info.gname = ""
                    info.mode = 0o600
                    with path.open("rb") as f:
                        archive.addfile(info, f)
    index = {
        p.name: digest(p)
        for p in k.output.iterdir()
        if p.is_file()
        and p.suffix in {".json", ".log", ".gz", ".lean"}
        and not p.name.startswith("PreservedBatch")
        or p.is_file()
        and p.name.endswith("-lean.log")
    }
    # Proof source bytes are archived and hash-bound per record; keep logs too.
    (k.output / "SHA256.json").write_bytes(canonical(index) + b"\n")
    print(
        json.dumps(
            {
                "accepted_compositions": len(accepted),
                "semantic_results_sha256": result["semantic_results_sha256"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--decisions", type=Path, required=True)
    a = p.parse_args()
    run(a.output, a.decisions)
