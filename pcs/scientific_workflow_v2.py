"""Exact finite-data calibration, composed with PCS v0.6 package authority.

The source data may be empirical; this adapter establishes only properties of
the supplied bytes and an explicit least-squares computation. It neither runs
submitted code nor certifies a population, causal, or biological conclusion.
"""
from __future__ import annotations

import csv
import hashlib
import io
from fractions import Fraction
from pathlib import Path, PurePosixPath

from .attest_v06 import build_attestation_directory_v06
from .bundle_v06 import create_verified_bundle_v06
from .canonical_json import canonicalize_jcs_bytes
from .check_registry_v06 import predicate_from_manifest_check_v06
from .discover_v06 import discover_project_v06, confirm_manifest_draft_v06
from .jsonio import strict_json_loads
from .scientific_assurance_v1 import _relative_file, _claim
from .scientific_contracts_v1 import rational, rational_text, digest, _bounded
from .scientific_obligations_v1 import FORMAT as GRAPH_FORMAT, topological_order, resolve_plan
from .checks.units import units_compatible
from .verifier_zip_v06 import load_package_zip_v06, verify_package_zip_end_to_end_v06

FORMAT = "pcs-scientific-workflow-v2"
CONTRACT_FORMAT = "pcs-linear-calibration-contract-v2"
MAX_ROWS = 4096
MAX_BYTES = 2 * 1024 * 1024
RESERVED = "pcs-workflow-v2"
# These exact rational conversions, rather than diagnostic floating-point unit
# scales, determine the calculation. Other units require a new version.
CONVERSIONS = {("mm", "m"): Fraction(1, 1000), ("m", "m"): Fraction(1),
               ("g", "kg"): Fraction(1, 1000), ("kg", "kg"): Fraction(1)}
SIDECARS = {name: f"{RESERVED}/{name}.json" for name in ("binding", "report", "plan", "resolved")}
ADAPTER = f"{RESERVED}/adapter.py.txt"


class ScientificWorkflowError(ValueError):
    pass


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise ScientificWorkflowError("artifact byte limit exceeded")
    value = strict_json_loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ScientificWorkflowError("object required")
    return value


def _text(value, label, maximum=4096):
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise ScientificWorkflowError(f"invalid bounded {label}")
    return value


def _sum(values) -> Fraction:
    total = Fraction()
    for value in values:
        total = _bounded(total + value)
    return total


def load_contract(raw: bytes) -> dict:
    value = _json(raw)
    fields = {"format", "question", "data_path", "provenance_path", "result_path", "x", "y",
              "missing_value", "missing_policy", "minimum_complete_rows", "assumptions", "license"}
    if set(value) != fields or value["format"] != CONTRACT_FORMAT:
        raise ScientificWorkflowError("unsupported exact contract schema")
    _text(value["question"], "question")
    for path in ("data_path", "provenance_path", "result_path"):
        _text(value[path], path, 256)
        literal = value[path]
        parts = PurePosixPath(literal)
        if ("\\" in literal or not parts.parts or parts.is_absolute() or parts.as_posix() != literal
                or any(x in {".", ".."} for x in parts.parts) or parts.parts[0] == RESERVED
                or literal == "contract.json"):
            raise ScientificWorkflowError("contract paths must be canonical project-relative source paths")
    if len({value[x] for x in ("data_path", "provenance_path", "result_path")}) != 3:
        raise ScientificWorkflowError("source artifacts must be distinct")
    if value["license"] != "CC0-1.0":
        raise ScientificWorkflowError("v2 supports explicitly CC0-cleared sources")
    if value["missing_value"] != "NA" or value["missing_policy"] != "exclude_pair_if_either_missing":
        raise ScientificWorkflowError("unsupported or implicit missing-data policy")
    if type(value["minimum_complete_rows"]) is not int or not 2 <= value["minimum_complete_rows"] <= MAX_ROWS:
        raise ScientificWorkflowError("invalid minimum complete row count")
    for name, target in (("x", "m"), ("y", "kg")):
        column = value[name]
        if not isinstance(column, dict) or set(column) != {"column", "source_unit", "target_unit", "scale"}:
            raise ScientificWorkflowError("invalid typed measurement column")
        _text(column["column"], "column", 128)
        if column["target_unit"] != target:
            raise ScientificWorkflowError("calibration input types must be length and mass")
        pair = (column["source_unit"], column["target_unit"])
        if pair not in CONVERSIONS or rational(column["scale"], name) != CONVERSIONS[pair]:
            raise ScientificWorkflowError("unit scale must match the exact versioned conversion")
    if value["x"]["column"] == value["y"]["column"]:
        raise ScientificWorkflowError("predictor and response columns must differ")
    assumptions = value["assumptions"]
    if not isinstance(assumptions, list) or not 1 <= len(assumptions) <= 32:
        raise ScientificWorkflowError("explicit applicability assumptions required")
    identifiers = set()
    for item in assumptions:
        if not isinstance(item, dict) or set(item) != {"id", "statement"}:
            raise ScientificWorkflowError("invalid assumption")
        ident = _text(item["id"], "assumption id", 64)
        if not ident.isascii() or not ident.replace("_", "").isalnum() or not ident[0].isalpha() or ident in identifiers:
            raise ScientificWorkflowError("invalid or duplicate assumption identifier")
        identifiers.add(ident)
        _text(item["statement"], "assumption statement")
    return value


def numerical_reference(contract: dict, data_raw: bytes) -> dict:
    """Centered sufficient statistics, independent of the producer's normal equations."""
    if len(data_raw) > MAX_BYTES:
        raise ScientificWorkflowError("CSV exceeds artifact byte limit")
    reader = csv.reader(io.StringIO(data_raw.decode("utf-8"), newline=""))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise ScientificWorkflowError("empty CSV") from exc
    if not 1 <= len(header) <= 64 or len(set(header)) != len(header) or any(len(x) > 128 for x in header):
        raise ScientificWorkflowError("invalid or duplicate CSV columns")
    try:
        xi, yi = (header.index(contract[x]["column"]) for x in ("x", "y"))
    except ValueError as exc:
        raise ScientificWorkflowError("measurement column absent") from exc
    points = []
    excluded = []
    total = 0
    for total, row in enumerate(reader, 1):
        if total > MAX_ROWS:
            raise ScientificWorkflowError("CSV row limit exceeded")
        if len(row) != len(header):
            raise ScientificWorkflowError("ragged CSV row")
        # Validate a present measurement even if its partner is missing. Invalid
        # input must not hide behind the missing-data exclusion rule.
        numbers = []
        for field, name in ((row[xi], "x"), (row[yi], "y")):
            numbers.append(None if field == contract["missing_value"] else rational(field, name))
        if any(number is not None and number <= 0 for number in numbers):
            raise ScientificWorkflowError("length and mass measurements must be positive")
        if any(x is None for x in numbers):
            excluded.append(total)
            continue
        x, y = (_bounded(numbers[i] * rational(contract[name]["scale"], name)) for i, name in enumerate(("x", "y")))
        if x <= 0 or y <= 0:
            raise ScientificWorkflowError("length and mass measurements must be positive")
        points.append((x, y))
    n = len(points)
    if n < contract["minimum_complete_rows"]:
        raise ScientificWorkflowError("insufficient complete measurements")
    xbar = _bounded(_sum(x for x, _ in points) / n)
    ybar = _bounded(_sum(y for _, y in points) / n)
    sxx = _sum(_bounded((x - xbar) ** 2) for x, _ in points)
    sxy = _sum(_bounded((x - xbar) * (y - ybar)) for x, y in points)
    if sxx == 0:
        raise ScientificWorkflowError("singular calibration: all predictor measurements equal")
    slope = _bounded(sxy / sxx)
    intercept = _bounded(ybar - slope * xbar)
    residuals = [_bounded(y - (intercept + slope * x)) for x, y in points]
    sse = _sum(_bounded(r * r) for r in residuals)
    # These are executable mathematical checks; no Python-to-Lean refinement is
    # inferred from their success.
    zero_sum = _sum(residuals) == 0
    orthogonal = _sum(_bounded(x * r) for (x, _), r in zip(points, residuals)) == 0
    if not (zero_sum and orthogonal):
        raise ScientificWorkflowError("internal normal-equation inconsistency")
    return {"format": "pcs-linear-calibration-result-v2", "total_rows": total,
        "complete_rows": n, "excluded_rows": excluded,
        "intercept_kg": rational_text(intercept), "slope_kg_per_m": rational_text(slope),
        "residual_sum_squares_kg2": rational_text(sse),
        "residual_sum_zero": zero_sum, "residual_predictor_inner_product_zero": orthogonal}


def dimension_checks() -> list[dict]:
    # PCS's unit grammar divides by the complete following product. Render the
    # algebraically equivalent kg*m/m, never the ambiguous kg/m*m spelling.
    return [{"id": "slope_dimensions", "type": "unit_compatible", "left_unit": "kg*m/m", "right_unit": "kg"},
            {"id": "intercept_dimensions", "type": "unit_compatible", "left_unit": "kg", "right_unit": "kg"}]


def evaluate(contract_raw: bytes, data_raw: bytes, result_raw: bytes) -> dict:
    contract = load_contract(contract_raw)
    reference = numerical_reference(contract, data_raw)
    observed = _json(result_raw)
    if set(observed) != set(reference):
        raise ScientificWorkflowError("reported calibration result has missing or extra fields")
    for name in ("total_rows", "complete_rows"):
        if type(observed[name]) is not int or not 0 <= observed[name] <= MAX_ROWS:
            raise ScientificWorkflowError("reported row counts must be bounded integers")
    if (not isinstance(observed["excluded_rows"], list) or len(observed["excluded_rows"]) > MAX_ROWS
            or any(type(x) is not int or not 1 <= x <= MAX_ROWS for x in observed["excluded_rows"])
            or observed["excluded_rows"] != sorted(set(observed["excluded_rows"]))):
        raise ScientificWorkflowError("reported exclusion indices must be sorted distinct bounded integers")
    for name in ("residual_sum_zero", "residual_predictor_inner_product_zero"):
        if type(observed[name]) is not bool:
            raise ScientificWorkflowError("reported predicates must be actual booleans")
    for name in ("intercept_kg", "slope_kg_per_m", "residual_sum_squares_kg2"):
        rational(observed[name], name)
    checks = [{"id": x["id"], "outcome": "PASS" if units_compatible(x["left_unit"], x["right_unit"])[0] else "FAIL"}
              for x in dimension_checks()]
    checks.extend([{"id": "data_binding", "outcome": "PASS"}, {"id": "complete_case_policy", "outcome": "PASS"},
                   {"id": "exact_unit_conversion", "outcome": "PASS"},
                   {"id": "least_squares_replay", "outcome": "PASS" if observed == reference else "FAIL"}])
    return {"format": FORMAT, "contract_sha256": sha(contract_raw), "data_sha256": sha(data_raw),
        "result_sha256": sha(result_raw), "outcome": "PASS" if all(x["outcome"] == "PASS" for x in checks) else "FAIL",
        "checks": checks, "reference": reference, "observed": observed,
        "resources": {"csv_rows": reference["total_rows"], "complete_rows": reference["complete_rows"],
                      "max_rows": MAX_ROWS, "max_artifact_bytes": MAX_BYTES, "fraction_bits": 4096},
        "pcs_authority": False, "scientific_acceptance": False}


def make_plan(contract: dict, contract_sha256: str, data_sha256: str) -> dict:
    for value in (contract_sha256, data_sha256):
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ScientificWorkflowError("plan requires exact contract and dataset SHA-256 identities")
    assumptions = [{"id": "assumption_" + x["id"], "kind": "assumption", "statement": x["statement"],
        "dependencies": [], "required_evidence": [], "assumption_sha256": digest(x),
        "authority": "EXPLICIT_UNVERIFIED_PREMISE"} for x in contract["assumptions"]]
    aids = [x["id"] for x in assumptions]
    predicates = [{"id": "data_binding", "kind": "domain_predicate", "statement": "The supplied dataset has SHA-256 " + data_sha256 + ".",
        "dependencies": [], "required_evidence": [], "typed_interpretation": {"data_sha256": data_sha256},
        "authority": "SIGNED_SOURCE_BYTES_AND_INDEPENDENT_HASH_CHECK"}]
    for ident, deps, statement in (
            ("complete_case_policy", ["data_binding"], "Every supplied row is accounted for; exclude only missing predictor/response pairs."),
            ("exact_unit_conversion", ["complete_case_policy"], "Apply the exact declared mm-to-m and g-to-kg scales, or supported identity conversions."),
            ("slope_dimensions", [], "Slope times predictor has mass dimensions."),
            ("intercept_dimensions", [], "The intercept has mass dimensions."),
            ("least_squares_replay", ["complete_case_policy", "exact_unit_conversion", "slope_dimensions", "intercept_dimensions"],
             "Every reported rational coefficient and residual statistic equals a fresh centered least-squares calculation.")):
        predicates.append({"id": ident, "kind": "domain_predicate", "statement": statement,
            "dependencies": [*aids, *deps], "required_evidence": [],
            "authority": "EXISTING_PCS_BUILTIN_CERTIFICATE_REQUIRED" if ident.endswith("dimensions") else "INDEPENDENT_BOUNDED_REPLAY"})
    plan = {"format": GRAPH_FORMAT, "source_contract_sha256": contract_sha256, "source_data_sha256": data_sha256,
        "original_claim": contract["question"],
        "domain": "finite empirical measurement table and descriptive linear calibration",
        "original_language_grounding": "NOT_CERTIFIED: only the explicit typed contract determines checked meaning",
        "nodes": [*assumptions, *predicates,
            {"id": "workflow", "kind": "aggregate", "statement": "The finite computation is reproducible under the explicit premises.",
             "dependencies": [x["id"] for x in predicates], "required_evidence": [], "authority": "CONDITIONAL_PLANNING_SUMMARY_ONLY"},
            {"id": "population_or_causal_validity", "kind": "unsupported", "statement": "The fitted association generalizes or establishes a causal biological relationship.",
             "dependencies": ["workflow"], "required_evidence": [], "authority": "NONE"}],
        "pcs_authority": False, "planner": "existing deterministic_dependency_topological_v1"}
    topological_order(plan)
    return plan


def _adapter() -> bytes:
    return Path(__file__).read_bytes()


def _implementation_sources() -> dict[str, bytes]:
    # Bind helper semantics as well as this adapter. Hashing one top-level module
    # would leave conversion, rational parsing, and propagation helpers unbound.
    from . import scientific_assurance_v1, scientific_contracts_v1, scientific_obligations_v1
    from .checks import units
    return {ADAPTER: _adapter(), f"{RESERVED}/contracts-v1.py.txt": Path(scientific_contracts_v1.__file__).read_bytes(),
            f"{RESERVED}/obligations-v1.py.txt": Path(scientific_obligations_v1.__file__).read_bytes(),
            f"{RESERVED}/assurance-v1.py.txt": Path(scientific_assurance_v1.__file__).read_bytes(),
            f"{RESERVED}/units.py.txt": Path(units.__file__).read_bytes()}


def _provenance(raw: bytes, source_files: dict[str, bytes], data_path: str) -> dict:
    value = _json(raw)
    if value.get("format") != "pcs-scientific-source-provenance-v2" or value.get("license") != "CC0-1.0":
        raise ScientificWorkflowError("source provenance and explicit CC0 dedication required")
    revision = value.get("source_revision")
    if not isinstance(revision, str) or len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise ScientificWorkflowError("immutable source revision required")
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, dict) or data_path not in artifacts or value.get("license_path") not in artifacts:
        raise ScientificWorkflowError("provenance must bind data and license")
    for path, item in artifacts.items():
        if not isinstance(item, dict) or path not in source_files or sha(source_files[path]) != item.get("sha256"):
            raise ScientificWorkflowError("source provenance digest mismatch")
        if not isinstance(item.get("url"), str) or revision not in item["url"]:
            raise ScientificWorkflowError("provenance URL must contain the pinned revision")
    # Provenance is retained and byte checked, not fetched or authenticated here.
    return value


def build_bundle(project_root, work_directory, output_bundle, private_key_path, public_key_path, *,
                 expected_fingerprint, confirm_reviewed_draft=False, lean_authority_path=None) -> dict:
    if not confirm_reviewed_draft:
        raise ScientificWorkflowError("explicit bounded draft confirmation required; this is not independent human review")
    root, work, bundle = Path(project_root).resolve(), Path(work_directory).resolve(), Path(output_bundle).resolve()
    if (not root.is_dir() or work.exists() or bundle.exists() or work == root or root in work.parents
            or bundle == root or root in bundle.parents or (root / RESERVED).exists()):
        raise ScientificWorkflowError("new output paths outside the input project are required")
    discovery = discover_project_v06(root, subject="Explicit finite-data calibration")
    sources = {x["path"]: _relative_file(root, x["path"]).read_bytes() for x in discovery["inventory"]}
    if any(sha(sources[x["path"]]) != x["sha256"] for x in discovery["inventory"]):
        raise ScientificWorkflowError("source changed after discovery")
    if "contract.json" not in sources:
        raise ScientificWorkflowError("regular source contract.json required")
    contract_raw = sources["contract.json"]
    contract = load_contract(contract_raw)
    if any(contract[k] not in sources for k in ("data_path", "provenance_path", "result_path")):
        raise ScientificWorkflowError("contract references a missing or unsupported source artifact")
    provenance = _provenance(sources[contract["provenance_path"]], sources, contract["data_path"])
    replay = evaluate(contract_raw, sources[contract["data_path"]], sources[contract["result_path"]])
    plan = make_plan(contract, sha(contract_raw), sha(sources[contract["data_path"]]))
    stage = work / "project"
    stage.mkdir(parents=True)
    for path, raw in sources.items():
        target = stage / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    binding = {"format": FORMAT, "source_inventory": {k: sha(v) for k, v in sorted(sources.items())},
        "implementation_sha256": {k: sha(v) for k, v in sorted(_implementation_sources().items())},
        "contract_path": "contract.json", "independent_human_review": False,
        "source_authentication": "producer signature plus retained upstream provenance; no online origin attestation"}
    additions = {**_implementation_sources(), SIDECARS["binding"]: canonicalize_jcs_bytes(binding),
        SIDECARS["report"]: canonicalize_jcs_bytes(replay), SIDECARS["plan"]: canonicalize_jcs_bytes(plan),
        SIDECARS["resolved"]: canonicalize_jcs_bytes(resolve_plan(plan, replay))}
    for path, raw in additions.items():
        target = stage / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    discovered = discover_project_v06(stage, subject=contract["question"])
    manifest = discovered["manifest_draft"]
    manifest["assumptions"] = contract["assumptions"]
    manifest["checks"], manifest["claims"] = [], []
    aids = [x["id"] for x in contract["assumptions"]]
    for check in dimension_checks():
        eid, cid = "E_" + check["id"], "C_" + check["id"]
        manifest["checks"].append({**check, "id": eid, "claim_ids": [cid]})
        manifest["claims"].append(_claim(cid, "The typed calibration expression has mass dimensions.",
            predicate_from_manifest_check_v06(check), eid, aids))
    for cid, statement in (("C_NUMERICAL", "The exact least-squares report faithfully describes the bound finite measurement table."),
                           ("C_EMPIRICAL", "The fitted relationship is biologically causal or generalizes to an unobserved population.")):
        claim = _claim(cid, statement, {"type": "external", "namespace": "pcs-finite-calibration/v2", "proposition": statement}, "", aids)
        claim["required_evidence"] = []
        manifest["claims"].append(claim)
    manifest["artifacts"] = [{"id": x["artifact_id"], "path": x["path"], "role": x["role"], "media_type": x["media_type"],
        "metadata": {"pcs_discovery_sha256": x["sha256"], "pcs_discovery_size": x["size"]}} for x in discovered["inventory"]]
    draft = stage / "pcs-manifest.draft.json"
    draft.write_bytes(canonicalize_jcs_bytes(manifest))
    confirmed = stage / "manifest.confirmed.json"
    confirm_manifest_draft_v06(draft, confirmed, project_root=stage)
    package = work / "package"
    build_attestation_directory_v06(confirmed, package, private_key_path, public_key_path,
        expected_fingerprint=expected_fingerprint, generated_at="2026-10-13T00:00:00+00:00", lean_authority_path=lean_authority_path)
    create_verified_bundle_v06(package, bundle, public_key_path, expected_fingerprint=expected_fingerprint, lean_authority_path=lean_authority_path)
    receipt = verify_bundle(bundle, public_key_path, expected_fingerprint=expected_fingerprint, lean_authority_path=lean_authority_path)
    if not receipt["independent_replay_consistent"]:
        raise ScientificWorkflowError("new package failed independent workflow replay")
    return {"format": FORMAT, "bundle_sha256": sha(bundle.read_bytes()),
        "source_revision": provenance["source_revision"], "pcs_package_valid": receipt["pcs_package_valid"],
        "bounded_contract_satisfied": receipt["bounded_contract_satisfied"], "scientific_acceptance": False,
        "pcs_numerical_claim": "OPEN", "pcs_empirical_claim": "OPEN", "user_code_executed": False}


def verify_bundle(bundle, public_key_path, *, expected_fingerprint, lean_authority_path=None) -> dict:
    try:
        verification = verify_package_zip_end_to_end_v06(bundle, public_key_path, expected_fingerprint=expected_fingerprint,
                                                        lean_authority_path=lean_authority_path)
    except ValueError as exc:
        verification = {"valid": False, "accepted": False, "error": str(exc)}
    base = {"format": FORMAT, "pcs_package_valid": verification["valid"], "pcs_verification": verification,
        "independent_replay_consistent": False, "bounded_contract_satisfied": False,
        "scientific_acceptance": False, "independent_human_review": False, "errors": []}
    if not verification["valid"]:
        return {**base, "errors": ["existing PCS package authority rejected"]}
    try:
        loaded = load_package_zip_v06(bundle)
        certificate = _json(loaded["certificate_bytes"])
        sources = {}
        for item in certificate["artifacts"]:
            path = item.get("source_path")
            if not isinstance(path, str) or path in sources:
                raise ScientificWorkflowError("duplicate or missing signed source path")
            sources[path] = loaded["package_files"][item["path"]]
        binding = _json(sources[SIDECARS["binding"]])
        if set(binding) != {"format", "source_inventory", "implementation_sha256", "contract_path", "independent_human_review", "source_authentication"}:
            raise ScientificWorkflowError("invalid binding schema")
        if binding["format"] != FORMAT or binding["contract_path"] != "contract.json" or binding["independent_human_review"] is not False:
            raise ScientificWorkflowError("unsupported authority binding")
        pinned = _implementation_sources()
        if binding["implementation_sha256"] != {k: sha(v) for k, v in sorted(pinned.items())} or any(sources[k] != v for k, v in pinned.items()):
            raise ScientificWorkflowError("receiving implementation source mismatch")
        inventory = binding["source_inventory"]
        if not isinstance(inventory, dict) or set(sources) != set(inventory) | set(SIDECARS.values()) | set(pinned):
            raise ScientificWorkflowError("source inventory must account for every signed artifact")
        for path, expected in inventory.items():
            if sha(sources[path]) != expected:
                raise ScientificWorkflowError("original source digest mismatch")
        contract_raw = sources["contract.json"]
        contract = load_contract(contract_raw)
        provenance = _provenance(sources[contract["provenance_path"]], sources, contract["data_path"])
        if [{"id": x["id"], "statement": x["statement"]} for x in certificate["assumptions"]] != contract["assumptions"]:
            raise ScientificWorkflowError("certificate premises differ from contract")
        claims = {x["id"]: x for x in certificate["claims"]}
        evidence = {x["id"]: x for x in certificate["evidence"]}
        expected_claims = {"C_NUMERICAL", "C_EMPIRICAL", *("C_" + x["id"] for x in dimension_checks())}
        if set(claims) != expected_claims or set(evidence) != {"E_" + x["id"] for x in dimension_checks()}:
            raise ScientificWorkflowError("unexpected or missing workflow claims/evidence")
        aids = [x["id"] for x in contract["assumptions"]]
        for check in dimension_checks():
            eid, cid = "E_" + check["id"], "C_" + check["id"]
            predicate = predicate_from_manifest_check_v06(check)
            if evidence[eid]["predicate"] != predicate or claims[cid]["predicate"] != predicate or claims[cid]["required_evidence"] != [eid] or claims[cid]["assumptions"] != aids:
                raise ScientificWorkflowError("dimension evidence is not the contract's exact builtin predicate")
        for cid, statement in (("C_NUMERICAL", "The exact least-squares report faithfully describes the bound finite measurement table."),
                               ("C_EMPIRICAL", "The fitted relationship is biologically causal or generalizes to an unobserved population.")):
            if (claims[cid]["required_evidence"] != [] or claims[cid]["assumptions"] != aids
                    or claims[cid]["predicate"] != {"type": "external", "namespace": "pcs-finite-calibration/v2", "proposition": statement}
                    or claims[cid]["statement"] != statement or claims[cid]["kind"] != "computational"):
                raise ScientificWorkflowError("unsupported claim must remain OPEN")
        replay = evaluate(contract_raw, sources[contract["data_path"]], sources[contract["result_path"]])
        if replay != _json(sources[SIDECARS["report"]]):
            raise ScientificWorkflowError("signed report differs from fresh independent replay")
        plan = make_plan(contract, sha(contract_raw), sha(sources[contract["data_path"]]))
        resolved = resolve_plan(plan, replay)
        if plan != _json(sources[SIDECARS["plan"]]) or resolved != _json(sources[SIDECARS["resolved"]]):
            raise ScientificWorkflowError("signed obligation graph or results differ from fresh replay")
        decisions = {x["claim_id"]: x["decision"] for x in verification["claims"]}
        if decisions.get("C_NUMERICAL") != "OPEN" or decisions.get("C_EMPIRICAL") != "OPEN":
            raise ScientificWorkflowError("unsupported workflow claim acquired certificate authority")
        return {**base, "independent_replay_consistent": True,
            "bounded_contract_satisfied": (replay["outcome"] == "PASS" and verification.get("accepted") is True
                and all(decisions.get("C_" + x["id"]) == "COMPUTATIONALLY_SUPPORTED" for x in dimension_checks())),
            "domain_replay": replay, "obligation_results": resolved, "source_provenance": provenance,
            "bundle_sha256": sha(Path(bundle).read_bytes()), "user_code_executed": False,
            "kernel_refinement_of_numerical_adapter": False}
    except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
        return {**base, "errors": [f"workflow receiver rejected: {type(exc).__name__}: {exc}"]}
