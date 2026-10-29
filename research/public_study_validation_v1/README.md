# Public-study attack transfer with actual open model weights

This additive research branch tests five published AgentDojo attack templates on
official Qwen3-0.6B and Qwen3-1.7B Q8_0 weights. Upstream Python is parsed as data,
never imported or executed. The model proposes actions for the unchanged PCS
fixed synthetic document workflow; its Lean authority checks actual SQLite rows
before commitment. The plan contains 18 cases per prompt policy/model, 72 model
calls total. All four benign template controls and the clean case remain included.

The five templates, model revisions/weights/runtime digests, case goals, arm order,
prompt construction and metrics are fixed before any model generation. The exact
registration and each raw request/response/proposal are retained. No examples are
selected after seeing responses, and no prompt tuning or training occurs.

```sh
source scripts/activate_lean_428.sh
python -c 'from pathlib import Path; from research.public_study_validation_v1.runtime import download; print(download(Path("/tmp/study-weights")))'
python -m pytest -q research/public_study_validation_v1/test_study.py
python -m research.public_study_validation_v1.study run /tmp/new-study --weights /tmp/study-weights
python -m research.public_study_validation_v1.study replay /tmp/new-study /tmp/new-receiver
```

About 2.5 GB downloads and sufficient Linux RAM for a sealed 1.8 GB model snapshot
are required. This uses the existing frozen PCS Python dependencies and exact Lean
4.28.0 tools. There is no hosted model API, GPU service or paid infrastructure.
Model files are streamed and hashed; inference consumes a sealed memfd snapshot.
Ordinary host control, compiler/libraries, llama.cpp inference and the OS remain
trusted. This is not an immutable or independently controlled security root.

The receiving process reads and validates all 72 proposal/request/response/capture
bindings before any effects. It re-executes the original fixed native Lean/SQL
authority and regenerates wire, row and path proofs. It does not execute submitted
proof code, adopt producer verdicts or attest that neural computation originally
produced a recorded response. Real generation and receiving replay are reported
separately. Existing outputs are never adopted or overwritten.

This is **attack-template transfer**, not the full AgentDojo task suite, official
attack-success score, representative production deployment or external partner
validation. AgentDojo's environments/tasks are not implemented here. The task,
action space, goals and constant approved summary remain PCS-authored and
synthetic. Both prompt arms state the correct next action; differences are
descriptive, not a general causal defense claim. Training contamination is unknown.

Metrics distinguish model proposals, malformed responses, raw-text private-marker
exposure and executed guarded tool effects. Unsafe proposals are not measured
unsafe ungated executions: the fixed SQL adapter has its own checks. A host that
forwards raw model text creates an additional channel outside the tool-only model;
the raw synthetic marker metric does not claim real-world exfiltration.
Shield-driven completion is not evidence of improved model competence.

The source copies retain AgentDojo's MIT notice and official model cards/licenses
at exact revisions. Runtime/source adaptations and file hashes are recorded under
`provenance/` and `upstream/`. These notices narrow artifact-provenance work;
they are not independent legal clearance of the entire PCS history. No untrusted
Aristotle development trace is used as training data.

Primary study: Debenedetti et al., *AgentDojo*, NeurIPS 2024 Datasets and Benchmarks,
https://proceedings.nips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html

PCS issues9/11/13/14 and website2 retain their actual owner/external exit criteria.
This study does not invent agreements, key custody, partner/reviewer independence,
legal approval, scientific acceptance, production promotion or release authority.
