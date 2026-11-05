"""Strict evidence-bound experimental promotion gate, never production authority."""
import re

SHA = re.compile(r"[0-9a-f]{64}\Z")
REQUIRED_BINDINGS = ("source_sha256", "dataset_sha256", "checkpoint_sha256", "optimizer_sha256",
                     "protocol_sha256", "architecture_sha256", "hyperparameters_sha256")


def evaluate_promotion(candidate, incumbent, protocol):
    """Pure fail-closed review decision; does not edit registry/deployment.

    Pair exact held-out IDs, independently verified outcomes, frozen budget and
    checker identity. Holdout cannot overlap training, validation or selection.
    A candidate must improve at least one solve at equal budget and not exceed
    the predeclared physical-call limit. It still requires human release approval.
    """
    reasons = []
    if protocol.get("format") != "pcs-promotion-protocol-v1" or protocol.get("frozen") is not True:
        reasons.append("unfrozen_or_invalid_protocol")
    if type(protocol.get("budget")) is not int or not 1 <= protocol["budget"] <= 4096:
        reasons.append("invalid_frozen_budget")
    if type(protocol.get("minimum_additional_solves", 1)) is not int or protocol.get("minimum_additional_solves", 1) < 1:
        reasons.append("invalid_improvement_threshold")
    if type(protocol.get("max_calls_per_task")) is not int or protocol["max_calls_per_task"] < 1:
        reasons.append("invalid_physical_cost_limit")
    for binding in REQUIRED_BINDINGS:
        if not SHA.fullmatch(str(candidate.get(binding, ""))):
            reasons.append("missing_or_invalid_" + binding)
    if candidate.get("protocol_sha256") != protocol.get("protocol_sha256"):
        reasons.append("protocol_binding_mismatch")
    if candidate.get("dataset_sha256") != protocol.get("dataset_sha256"):
        reasons.append("dataset_binding_mismatch")
    holdout = protocol.get("heldout_ids", [])
    if not holdout or len(set(holdout)) != len(holdout):
        reasons.append("empty_or_duplicate_holdout")
    for split in ("training_ids", "validation_ids", "selection_ids"):
        if set(holdout) & set(candidate.get(split, [])):
            reasons.append("holdout_leakage_" + split)
    counts = {}
    for label, result in (("candidate", candidate), ("incumbent", incumbent)):
        rows = result.get("outcomes", [])
        if [row.get("id") for row in rows] != holdout:
            reasons.append(label + "_holdout_membership_mismatch")
        count = 0
        for row in rows:
            if row.get("budget") != protocol.get("budget") or row.get("checker_sha256") != protocol.get("checker_sha256"):
                reasons.append(label + "_resource_or_checker_mismatch")
            if row.get("status") == "verified":
                if row.get("independent_kernel_replay") is not True or not SHA.fullmatch(str(row.get("receipt_sha256", ""))):
                    reasons.append(label + "_unverified_success")
                else:
                    count += 1
            calls = row.get("physical_lean_calls")
            if type(calls) is not int or calls < 0:
                reasons.append(label + "_missing_physical_cost")
            elif label == "candidate" and calls > protocol.get("max_calls_per_task", -1):
                reasons.append("candidate_cost_limit")
        counts[label] = count
    if counts["candidate"] < counts["incumbent"] + protocol.get("minimum_additional_solves", 1):
        reasons.append("no_predeclared_heldout_improvement")
    return {"format": "pcs-model-promotion-decision-v1", "eligible_for_review": not reasons,
            "candidate_verified": counts["candidate"], "incumbent_verified": counts["incumbent"],
            "reasons": sorted(set(reasons)), "automatic_deployment": False,
            "required_release_authority": "human-controlled protected release",
            "pcs_scientific_authority": False}
