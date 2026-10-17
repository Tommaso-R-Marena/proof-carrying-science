"""Conservative finite-volume transport, composed with existing PCS authority.

Source trajectories are computations, not empirical observations. Only the
dimensional predicates have existing compiled PCS authority. Finite numerical
replay, continuum applicability and empirical claims retain explicit boundaries.
"""
from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path, PurePosixPath
from fractions import Fraction

from .attest_v06 import build_attestation_directory_v06
from .bundle_v06 import create_verified_bundle_v06
from .canonical_json import canonicalize_jcs_bytes
from .check_registry_v06 import predicate_from_manifest_check_v06
from .discover_v06 import discover_project_v06, confirm_manifest_draft_v06
from .jsonio import strict_json_loads
from .scientific_assurance_v1 import _relative_file, _claim
from .scientific_contracts_v1 import rational, rational_text, digest, _bounded
from .scientific_obligations_v1 import FORMAT as GRAPH_FORMAT, resolve_plan, topological_order
from .checks.units import units_compatible
from .verifier_zip_v06 import load_package_zip_v06, verify_package_zip_end_to_end_v06

FORMAT = "pcs-conservative-transport-workflow-v3"
CONTRACT = "pcs-finite-volume-transport-contract-v3"
RESERVED = "pcs-transport-v3"
MAX_CELLS, MAX_EDGES, MAX_STEPS, MAX_BYTES = 16, 64, 64, 2 * 1024 * 1024
FILES = {name: f"{RESERVED}/{name}.json" for name in ("binding", "report", "plan", "resolved")}
UNITS = {"volume": "m^3", "concentration": "mol/m^3", "conductance": "m^3/s", "time": "s"}
OPEN_CLAIMS = {
    "C_NUMERICAL": "The supplied finite trajectory matches the declared conservative transport discretization and its bounded invariants.",
    "C_CONTINUUM": "This discretization approximates a continuous physical diffusion process with adequate accuracy.",
    "C_EMPIRICAL": "The model describes a real material system and its empirical behavior adequately.",
}


class TransportWorkflowError(ValueError):
    pass


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise TransportWorkflowError("artifact byte limit exceeded")
    value = strict_json_loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise TransportWorkflowError("object required")
    return value


def _sum(values):
    total = Fraction()
    for value in values:
        total = _bounded(total + value)
    return total


def _object(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise TransportWorkflowError(f"{label}: exact supported fields required")


def _text(value, label, limit=4096):
    if not isinstance(value, str) or not 1 <= len(value) <= limit:
        raise TransportWorkflowError(f"{label}: bounded nonempty text required")


def _identifier(value):
    _text(value, "identifier", 64)
    if not value.isascii() or not value.replace("_", "").isalnum() or not value[0].isalpha():
        raise TransportWorkflowError("ASCII identifiers required")


def load_contract(raw):
    value = _json(raw)
    _object(value, {"format", "question", "cells", "edges", "time_step", "steps", "units", "data_path", "assumptions", "data_origin", "license"}, "contract")
    if value["format"] != CONTRACT or value["units"] != UNITS:
        raise TransportWorkflowError("unsupported contract version or dimensional units")
    _text(value["question"], "question")
    if value["license"] != "CC0-1.0" or value["data_origin"] != "synthetic_numerical_computation_not_empirical":
        raise TransportWorkflowError("explicit CC0 synthetic-computation origin required")
    path = value["data_path"]
    _text(path, "data_path", 256)
    parts = PurePosixPath(path)
    if (not parts.parts or "\\" in path or parts.is_absolute() or parts.as_posix() != path
            or any(x in {".", ".."} for x in parts.parts) or parts.parts[0] == RESERVED or path == "contract.json"):
        raise TransportWorkflowError("canonical project-relative trajectory path required")
    if type(value["steps"]) is not int or not 1 <= value["steps"] <= MAX_STEPS:
        raise TransportWorkflowError("step count outside [1,64]")
    if rational(value["time_step"], "time_step") <= 0:
        raise TransportWorkflowError("positive time step required")
    cells = value["cells"]
    if not isinstance(cells, list) or not 2 <= len(cells) <= MAX_CELLS:
        raise TransportWorkflowError("cell count outside [2,16]")
    names = []
    for cell in cells:
        _object(cell, {"id", "volume", "initial_concentration"}, "cell")
        _identifier(cell["id"])
        if cell["id"] in names or cell["id"] == "time_s":
            raise TransportWorkflowError("duplicate or reserved cell identifier")
        names.append(cell["id"])
        if rational(cell["volume"], "volume") <= 0 or rational(cell["initial_concentration"], "initial_concentration") < 0:
            raise TransportWorkflowError("positive volumes and nonnegative concentrations required")
    edges = value["edges"]
    if not isinstance(edges, list) or not 1 <= len(edges) <= MAX_EDGES:
        raise TransportWorkflowError("edge count outside [1,64]")
    seen = set()
    for edge in edges:
        _object(edge, {"left", "right", "conductance"}, "edge")
        if not isinstance(edge["left"], str) or not isinstance(edge["right"], str) or edge["left"] not in names or edge["right"] not in names or edge["left"] == edge["right"]:
            raise TransportWorkflowError("edge must join two declared distinct cells")
        pair = tuple(sorted((edge["left"], edge["right"])))
        if pair in seen:
            raise TransportWorkflowError("duplicate undirected edge")
        seen.add(pair)
        if rational(edge["conductance"], "conductance") <= 0:
            raise TransportWorkflowError("positive symmetric conductance required")
    assumptions = value["assumptions"]
    if not isinstance(assumptions, list) or not 1 <= len(assumptions) <= 32:
        raise TransportWorkflowError("explicit assumptions required")
    ids = set()
    for item in assumptions:
        _object(item, {"id", "statement"}, "assumption")
        _identifier(item["id"])
        _text(item["statement"], "assumption statement")
        if item["id"] in ids:
            raise TransportWorkflowError("duplicate assumption identifier")
        ids.add(item["id"])
    # Stability is part of the supported semantics, not a warning that can be
    # ignored while certifying an unstable numerical trajectory.
    transition_matrix(value)
    return value


def transition_matrix(contract):
    cells = contract["cells"]
    names = [x["id"] for x in cells]
    matrix = [[Fraction(int(i == j)) for j in range(len(cells))] for i in range(len(cells))]
    dt = rational(contract["time_step"], "time_step")
    for edge in contract["edges"]:
        a, b = names.index(edge["left"]), names.index(edge["right"])
        g = rational(edge["conductance"], "conductance")
        for i, j in ((a, b), (b, a)):
            coefficient = _bounded(dt * g / rational(cells[i]["volume"], "volume"))
            matrix[i][j] = _bounded(matrix[i][j] + coefficient)
            matrix[i][i] = _bounded(matrix[i][i] - coefficient)
    if any(matrix[i][i] < 0 for i in range(len(cells))):
        raise TransportWorkflowError("CFL violation: time_step * total conductance / cell volume exceeds one")
    return matrix


def reference(contract):
    """Matrix-row evolution, independently implemented from edge-flux producer."""
    matrix = transition_matrix(contract)
    state = [rational(cell["initial_concentration"], "initial_concentration") for cell in contract["cells"]]
    trajectory = [state]
    for _ in range(contract["steps"]):
        state = [_sum(_bounded(weight * value) for weight, value in zip(row, state)) for row in matrix]
        trajectory.append(state)
    return trajectory


def _observations(contract, raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise TransportWorkflowError("trajectory artifact byte limit exceeded")
    reader = csv.reader(io.StringIO(raw.decode("utf-8"), newline=""))
    expected_header = ["time_s", *(x["id"] for x in contract["cells"])]
    if next(reader, None) != expected_header:
        raise TransportWorkflowError("trajectory header must match declared cells in exact order")
    rows = []
    for row in reader:
        if len(rows) > contract["steps"] or len(row) != len(expected_header):
            raise TransportWorkflowError("unexpected trajectory row count or width")
        rows.append([rational(x, "trajectory value") for x in row])
    if len(rows) != contract["steps"] + 1:
        raise TransportWorkflowError("trajectory must contain exactly steps+1 states")
    return rows


def dimension_checks():
    # Divide by complete products under the existing PCS unit grammar. Put
    # multiplied factors in the numerator; kg/m*m-style ambiguity is avoided.
    return [
        {"id": "inventory_dimensions", "type": "unit_compatible", "left_unit": "mol*m^3/m^3", "right_unit": "mol"},
        {"id": "flux_dimensions", "type": "unit_compatible", "left_unit": "m^3*mol/s/m^3", "right_unit": "mol/s"},
        {"id": "step_dimensions", "type": "unit_compatible", "left_unit": "s*m^3/s/m^3", "right_unit": "1"},
    ]


def evaluate(contract_raw, trajectory_raw):
    contract = load_contract(contract_raw)
    observed = _observations(contract, trajectory_raw)
    expected = reference(contract)
    volumes = [rational(x["volume"], "volume") for x in contract["cells"]]
    dt = rational(contract["time_step"], "time_step")
    initial = expected[0]
    initial_amount = _sum(_bounded(v * c) for v, c in zip(volumes, initial))
    minimum, maximum = min(initial), max(initial)
    matrix = transition_matrix(contract)
    matrix_good = (all(all(w >= 0 for w in row) and _sum(row) == 1 for row in matrix)
        and all(_sum(_bounded(volumes[i] * matrix[i][j]) for i in range(len(volumes))) == volumes[j] for j in range(len(volumes))))
    witnesses = {x: None for x in ("time_grid", "nonnegative", "step_replay", "amount_conservation", "maximum_principle", "quadratic_dissipation")}
    energies, amountes = [], []
    for index, row in enumerate(observed):
        time, state = row[0], row[1:]
        amount = _sum(_bounded(v * c) for v, c in zip(volumes, state))
        energy = _sum(_bounded(v * _bounded(c * c)) for v, c in zip(volumes, state))
        amountes.append(amount)
        energies.append(energy)
        conditions = {
            "time_grid": time == dt * index,
            "nonnegative": all(c >= 0 for c in state),
            "step_replay": state == expected[index],
            "amount_conservation": amount == initial_amount,
            "maximum_principle": all(minimum <= c <= maximum for c in state),
            "quadratic_dissipation": index == 0 or energy <= energies[index-1],
        }
        for ident, passed in conditions.items():
            if not passed and witnesses[ident] is None:
                witnesses[ident] = {"row": index, "time_s": rational_text(time), "concentrations_mol_per_m3": [rational_text(c) for c in state]}
    checks = [{"id": x["id"], "outcome": "PASS" if units_compatible(x["left_unit"], x["right_unit"])[0] else "FAIL", "witness": None}
              for x in dimension_checks()]
    checks.extend({"id": key, "outcome": "PASS" if witness is None else "FAIL", "witness": witness} for key, witness in witnesses.items())
    checks.append({"id": "transition_invariants", "outcome": "PASS" if matrix_good else "FAIL", "witness": None})
    return {"format": FORMAT, "contract_sha256": sha(contract_raw), "data_sha256": sha(trajectory_raw),
        "outcome": "PASS" if all(x["outcome"] == "PASS" for x in checks) else "FAIL", "checks": checks,
        "statistics": {"cells": len(volumes), "steps": contract["steps"], "states": len(observed),
            "initial_amount_mol": rational_text(initial_amount), "final_amount_mol": rational_text(amountes[-1]),
            "initial_quadratic_functional_mol2_per_m3": rational_text(energies[0]),
            "final_quadratic_functional_mol2_per_m3": rational_text(energies[-1])},
        "trajectory": [{"time_s": rational_text(row[0]), "concentrations": [rational_text(c) for c in row[1:]],
                        "total_amount_mol": rational_text(amountes[i]), "quadratic_functional_mol2_per_m3": rational_text(energies[i])}
                       for i, row in enumerate(observed)],
        "transition_matrix_sha256": digest([[rational_text(x) for x in row] for row in matrix]),
        "resources": {"cells": len(volumes), "edges": len(contract["edges"]), "steps": contract["steps"],
            "matrix_products": contract["steps"] * len(volumes)**2, "max_fraction_bits": 4096, "input_bytes": len(contract_raw)+len(trajectory_raw)},
        "quadratic_functional_is_thermodynamic_energy": False, "pcs_authority": False,
        "scientific_acceptance": False, "data_origin": contract["data_origin"]}


def make_plan(contract, contract_sha256, data_sha256):
    for value in (contract_sha256, data_sha256):
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise TransportWorkflowError("exact source identities required")
    nodes = [{"id": "assumption_" + a["id"], "kind": "assumption", "statement": a["statement"],
        "dependencies": [], "required_evidence": [], "authority": "EXPLICIT_UNVERIFIED_PREMISE"} for a in contract["assumptions"]]
    aids = [x["id"] for x in nodes]
    nodes.append({"id": "data_binding", "kind": "domain_predicate", "statement": "Trajectory source SHA-256 " + data_sha256,
        "dependencies": [], "required_evidence": [], "authority": "SIGNED_SOURCE_BYTES_AND_INDEPENDENT_HASH_CHECK"})
    definitions = [(x["id"], [], "Declared transport expression has the stated dimensions.") for x in dimension_checks()]
    definitions.extend([
        ("transition_invariants", [], "The finite transition matrix is nonnegative and row-stochastic, with volume-weighted column sums."),
        ("time_grid", ["data_binding"], "Every state occurs at the exact declared time."),
        ("step_replay", ["time_grid", "transition_invariants"], "Every state matches independently reconstructed transition-matrix evolution."),
        ("nonnegative", ["step_replay"], "Every recorded concentration is nonnegative."),
        ("amount_conservation", ["step_replay", "inventory_dimensions"], "Total recorded amount is exactly conserved at every step."),
        ("maximum_principle", ["step_replay"], "Every concentration remains between the initial minimum and maximum."),
        ("quadratic_dissipation", ["step_replay"], "The volume-weighted squared-concentration functional never increases; this is not thermodynamic energy."),
    ])
    for ident, dependencies, statement in definitions:
        nodes.append({"id": ident, "kind": "domain_predicate", "statement": statement, "dependencies": [*aids, *dependencies],
            "required_evidence": [], "authority": "EXISTING_PCS_BUILTIN_CERTIFICATE_REQUIRED" if ident.endswith("dimensions") else "INDEPENDENT_BOUNDED_NUMERICAL_REPLAY"})
    nodes.extend([
        {"id": "workflow", "kind": "aggregate", "statement": "All explicit finite transport obligations pass under the declared premises.",
         "dependencies": [x[0] for x in definitions], "required_evidence": [], "authority": "CONDITIONAL_PLANNING_SUMMARY_ONLY"},
        {"id": "continuum_and_empirical_adequacy", "kind": "unsupported", "statement": "The discretization and model faithfully describe continuous real-world physics.",
         "dependencies": ["workflow"], "required_evidence": [], "authority": "NONE"}])
    plan = {"format": GRAPH_FORMAT, "source_contract_sha256": contract_sha256, "source_data_sha256": data_sha256,
        "original_claim": contract["question"], "domain": "bounded conservative finite-volume network transport",
        "original_language_grounding": "NOT_CERTIFIED: only the typed contract determines the checked finite meaning",
        "nodes": nodes, "pcs_authority": False, "planner": "existing deterministic_dependency_topological_v1"}
    topological_order(plan)
    return plan


def resolve(plan, report, previous=None):
    # The v1 graph engine tracks contract and node revisions. Explicitly compare
    # data as well, so callers cannot combine a valid report with another table.
    if report.get("data_sha256") != plan.get("source_data_sha256"):
        raise TransportWorkflowError("obligation plan and replay refer to different trajectory bytes")
    augmented = {**report, "checks": [*report["checks"], {"id": "data_binding", "outcome": "PASS"}]}
    return resolve_plan(plan, augmented, previous=previous)


def _implementation():
    from . import scientific_assurance_v1, scientific_contracts_v1, scientific_obligations_v1
    from .checks import units
    return {f"{RESERVED}/adapter.py.txt": Path(__file__).read_bytes(),
        **{f"{RESERVED}/{name}.py.txt": Path(module.__file__).read_bytes() for name, module in (
        ("assurance-v1", scientific_assurance_v1), ("contracts-v1", scientific_contracts_v1),
        ("obligations-v1", scientific_obligations_v1), ("units", units))}}


def build_bundle(project_root, work_directory, output_bundle, private_key_path, public_key_path, *,
                 expected_fingerprint, confirm_reviewed_draft=False, lean_authority_path=None):
    if not confirm_reviewed_draft:
        raise TransportWorkflowError("explicit bounded draft confirmation required; not independent human review")
    root, work, bundle = Path(project_root).resolve(), Path(work_directory).resolve(), Path(output_bundle).resolve()
    if (not root.is_dir() or work.exists() or bundle.exists() or root == work or root in work.parents
            or root == bundle or root in bundle.parents or (root / RESERVED).exists()):
        raise TransportWorkflowError("new work and output paths outside input project required")
    discovered = discover_project_v06(root, subject="Explicit finite-volume conservative transport")
    sources = {x["path"]: _relative_file(root, x["path"]).read_bytes() for x in discovered["inventory"]}
    if any(sha(sources[x["path"]]) != x["sha256"] for x in discovered["inventory"]):
        raise TransportWorkflowError("source changed after discovery")
    if "contract.json" not in sources:
        raise TransportWorkflowError("regular contract.json source required")
    contract_raw = sources["contract.json"]
    contract = load_contract(contract_raw)
    if contract["data_path"] not in sources:
        raise TransportWorkflowError("regular trajectory source required")
    report = evaluate(contract_raw, sources[contract["data_path"]])
    plan = make_plan(contract, sha(contract_raw), sha(sources[contract["data_path"]]))
    implementation = _implementation()
    binding = {"format": FORMAT, "source_inventory": {k: sha(v) for k, v in sorted(sources.items())},
        "implementation_sha256": {k: sha(v) for k, v in sorted(implementation.items())},
        "data_origin": contract["data_origin"], "independent_human_review": False}
    additions = {**implementation, FILES["binding"]: canonicalize_jcs_bytes(binding), FILES["report"]: canonicalize_jcs_bytes(report),
        FILES["plan"]: canonicalize_jcs_bytes(plan), FILES["resolved"]: canonicalize_jcs_bytes(resolve(plan, report))}
    stage = work / "project"
    stage.mkdir(parents=True)
    for path, raw in {**sources, **additions}.items():
        target = stage / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    found = discover_project_v06(stage, subject=contract["question"])
    manifest = found["manifest_draft"]
    manifest["assumptions"], manifest["checks"], manifest["claims"] = contract["assumptions"], [], []
    aids = [x["id"] for x in contract["assumptions"]]
    for check in dimension_checks():
        eid, cid = "E_" + check["id"], "C_" + check["id"]
        manifest["checks"].append({**check, "id": eid, "claim_ids": [cid]})
        manifest["claims"].append(_claim(cid, "The declared transport expression has its specified dimensions.",
            predicate_from_manifest_check_v06(check), eid, aids))
    for cid, statement in OPEN_CLAIMS.items():
        claim = _claim(cid, statement, {"type": "external", "namespace": "pcs-conservative-transport/v3", "proposition": statement}, "", aids)
        claim["required_evidence"] = []
        manifest["claims"].append(claim)
    manifest["artifacts"] = [{"id": x["artifact_id"], "path": x["path"], "role": x["role"], "media_type": x["media_type"],
        "metadata": {"pcs_discovery_sha256": x["sha256"], "pcs_discovery_size": x["size"]}} for x in found["inventory"]]
    draft, confirmed = stage / "pcs-manifest.draft.json", stage / "manifest.confirmed.json"
    draft.write_bytes(canonicalize_jcs_bytes(manifest))
    confirm_manifest_draft_v06(draft, confirmed, project_root=stage)
    package = work / "package"
    build_attestation_directory_v06(confirmed, package, private_key_path, public_key_path, expected_fingerprint=expected_fingerprint,
        generated_at="2026-10-13T00:00:00+00:00", lean_authority_path=lean_authority_path)
    create_verified_bundle_v06(package, bundle, public_key_path, expected_fingerprint=expected_fingerprint, lean_authority_path=lean_authority_path)
    receipt = verify_bundle(bundle, public_key_path, expected_fingerprint=expected_fingerprint, lean_authority_path=lean_authority_path)
    if not receipt["independent_replay_consistent"]:
        raise TransportWorkflowError("new package failed independent transport replay")
    return {"format": FORMAT, "bundle_sha256": sha(bundle.read_bytes()), "pcs_package_valid": receipt["pcs_package_valid"],
        "bounded_contract_satisfied": receipt["bounded_contract_satisfied"], "scientific_acceptance": False,
        "open_claims": sorted(OPEN_CLAIMS), "user_code_executed": False, "data_origin": contract["data_origin"]}


def verify_bundle(bundle, public_key_path, *, expected_fingerprint, lean_authority_path=None):
    try:
        verification = verify_package_zip_end_to_end_v06(bundle, public_key_path, expected_fingerprint=expected_fingerprint, lean_authority_path=lean_authority_path)
    except ValueError as exc:
        verification = {"valid": False, "accepted": False, "error": str(exc)}
    base = {"format": FORMAT, "pcs_package_valid": verification["valid"], "pcs_verification": verification,
        "independent_replay_consistent": False, "bounded_contract_satisfied": False,
        "scientific_acceptance": False, "independent_human_review": False, "user_code_executed": False, "errors": []}
    if not verification["valid"]:
        return {**base, "errors": ["existing PCS package authority rejected"]}
    try:
        loaded = load_package_zip_v06(bundle)
        certificate = _json(loaded["certificate_bytes"])
        sources = {}
        for item in certificate["artifacts"]:
            source = item.get("source_path")
            if not isinstance(source, str) or source in sources:
                raise TransportWorkflowError("missing or duplicate signed source path")
            sources[source] = loaded["package_files"][item["path"]]
        binding = _json(sources[FILES["binding"]])
        _object(binding, {"format", "source_inventory", "implementation_sha256", "data_origin", "independent_human_review"}, "binding")
        if binding["format"] != FORMAT or binding["independent_human_review"] is not False:
            raise TransportWorkflowError("unsupported authority binding")
        implementation = _implementation()
        if binding["implementation_sha256"] != {k: sha(v) for k, v in sorted(implementation.items())} or any(sources[k] != raw for k, raw in implementation.items()):
            raise TransportWorkflowError("receiving pinned implementation source mismatch")
        inventory = binding["source_inventory"]
        if not isinstance(inventory, dict) or set(sources) != set(inventory) | set(FILES.values()) | set(implementation):
            raise TransportWorkflowError("signed source inventory incomplete")
        if any(sha(sources[path]) != expected for path, expected in inventory.items()):
            raise TransportWorkflowError("source artifact digest mismatch")
        contract_raw = sources["contract.json"]
        contract = load_contract(contract_raw)
        if binding["data_origin"] != contract["data_origin"]:
            raise TransportWorkflowError("synthetic numerical computation must not be relabeled empirical")
        if [{"id": x["id"], "statement": x["statement"]} for x in certificate["assumptions"]] != contract["assumptions"]:
            raise TransportWorkflowError("certificate premises differ from typed contract")
        claims = {x["id"]: x for x in certificate["claims"]}
        evidence = {x["id"]: x for x in certificate["evidence"]}
        if set(claims) != set(OPEN_CLAIMS) | {"C_" + x["id"] for x in dimension_checks()} or set(evidence) != {"E_" + x["id"] for x in dimension_checks()}:
            raise TransportWorkflowError("unexpected or missing claims/evidence")
        aids = [x["id"] for x in contract["assumptions"]]
        for check in dimension_checks():
            eid, cid = "E_" + check["id"], "C_" + check["id"]
            predicate = predicate_from_manifest_check_v06(check)
            if (evidence[eid]["predicate"] != predicate or claims[cid]["predicate"] != predicate or claims[cid]["required_evidence"] != [eid] or claims[cid]["assumptions"] != aids
                    or claims[cid]["kind"] != "computational" or claims[cid]["statement"] != "The declared transport expression has its specified dimensions."):
                raise TransportWorkflowError("dimension evidence differs from declared transport predicate")
        for cid, statement in OPEN_CLAIMS.items():
            expected = {"type": "external", "namespace": "pcs-conservative-transport/v3", "proposition": statement}
            if (claims[cid]["predicate"] != expected or claims[cid]["statement"] != statement or claims[cid]["required_evidence"] != [] or claims[cid]["assumptions"] != aids
                    or claims[cid]["kind"] != "computational"):
                raise TransportWorkflowError("unsupported scientific claim must remain OPEN")
        report = evaluate(contract_raw, sources[contract["data_path"]])
        if sources[FILES["report"]] != canonicalize_jcs_bytes(report):
            raise TransportWorkflowError("signed numerical report differs from independent replay")
        plan = make_plan(contract, sha(contract_raw), sha(sources[contract["data_path"]]))
        resolved = resolve(plan, report)
        if sources[FILES["plan"]] != canonicalize_jcs_bytes(plan) or sources[FILES["resolved"]] != canonicalize_jcs_bytes(resolved):
            raise TransportWorkflowError("signed obligation graph or results differ from source replay")
        decisions = {x["claim_id"]: x["decision"] for x in verification["claims"]}
        if any(decisions.get(cid) != "OPEN" for cid in OPEN_CLAIMS):
            raise TransportWorkflowError("unsupported transport claim acquired authority")
        return {**base, "independent_replay_consistent": True,
            "bounded_contract_satisfied": report["outcome"] == "PASS" and verification.get("accepted") is True and all(decisions.get("C_" + x["id"]) == "COMPUTATIONALLY_SUPPORTED" for x in dimension_checks()),
            "domain_replay": report, "obligation_results": resolved, "bundle_sha256": sha(Path(bundle).read_bytes()),
            "kernel_refinement_of_numerical_adapter": False, "data_origin": contract["data_origin"]}
    except (ValueError, KeyError, TypeError, UnicodeDecodeError) as exc:
        return {**base, "errors": [f"transport receiver rejected: {type(exc).__name__}: {exc}"]}
