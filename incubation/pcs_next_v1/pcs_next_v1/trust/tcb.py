"""Trusted Computing Base inventory for PCS Next assurances."""

from __future__ import annotations

from typing import Any

TCB_COMPONENTS: list[dict[str, Any]] = [
    {
        "id": "lean_kernel",
        "assumption": "Lean 4 kernel correctly checks proofs",
        "false_accept_if_violated": "Invalid theorems reported as verified",
        "classification": "externally_assumed",
    },
    {
        "id": "formal_declarations",
        "assumption": "Formal definitions match intended scientific meaning",
        "false_accept_if_violated": "Correct proof of wrong statement",
        "classification": "operationally_controlled",
    },
    {
        "id": "serialization_decoding",
        "assumption": "Canonical JSON / codecs preserve intended values",
        "false_accept_if_violated": "Hash/signature covers different semantics",
        "classification": "computationally_tested",
    },
    {
        "id": "hash_sha256",
        "assumption": "SHA-256 is collision-resistant for our threat model",
        "false_accept_if_violated": "Artifact substitution with colliding digest",
        "classification": "externally_assumed",
    },
    {
        "id": "ed25519_verify",
        "assumption": "cryptography library Ed25519 verify is correct",
        "false_accept_if_violated": "Forged signatures accepted",
        "classification": "externally_assumed",
    },
    {
        "id": "trusted_pubkey_distribution",
        "assumption": "Receiver pins correct signer fingerprints out-of-band",
        "false_accept_if_violated": "Attacker-controlled signer accepted",
        "classification": "operationally_controlled",
    },
    {
        "id": "policy_selection",
        "assumption": "Receiver loads its own policy, not producer-authorized policy",
        "false_accept_if_violated": "Policy downgrade / substitution",
        "classification": "computationally_tested",
    },
    {
        "id": "filesystem",
        "assumption": "Local FS reads return authentic bytes during verification",
        "false_accept_if_violated": "Transient substitution during verify",
        "classification": "operationally_controlled",
    },
    {
        "id": "process_invocation",
        "assumption": "Subprocess launches intended executable identity",
        "false_accept_if_violated": "Authority binary substitution",
        "classification": "computationally_tested",
    },
    {
        "id": "os_compiler",
        "assumption": "OS and compiler toolchain are not adversarial",
        "false_accept_if_violated": "Compromised runtime lies about results",
        "classification": "externally_assumed",
    },
    {
        "id": "external_scientific_validators",
        "assumption": "Domain validators implement stated contracts",
        "false_accept_if_violated": "Scientifically wrong PASS",
        "classification": "computationally_tested",
    },
    {
        "id": "human_interpretation",
        "assumption": "Reviewers do not over-read scoped statuses",
        "false_accept_if_violated": "Social overclaim of scientific validity",
        "classification": "operationally_controlled",
    },
]


def tcb_report() -> dict[str, Any]:
    return {
        "format": "pcs-next-tcb-inventory-v1",
        "components": TCB_COMPONENTS,
        "notes": [
            "Git isolation does not reduce TCB size.",
            "A local hash chain is not an external trust anchor.",
        ],
    }
