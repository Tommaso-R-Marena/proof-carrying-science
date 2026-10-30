"""Select an explicitly pinned combined contract or the original phase guard.

This is CI source admission only. It does not grant authority to a model,
certificate, receipt, controller update or scientific claim. The older guard
programs and their baseline predicates remain unchanged.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys

from . import reconcile

PROFILES = frozenset((
    "research.causal_firewall_v1.preservation",
    "research.compositional_disclosure_v1.preservation",
    "research.flux_detective_v1.preservation",
    "research.flux_forge_v1.preservation",
    "research.trace_lab_v1.preservation",
    "research.live_agent_lab_v3.preservation",
    "research.llm_firewall_v1.preservation",
    "research.local_weights_v1.preservation",
    "research.real_model_execution_v2.preservation",
    "research.portable_transport_v2.preservation",
    "research.progress_supervisor_v1.preservation",
    "research.real_model_safety_v1.reproduction.preservation",
    "research.relational_release_v1.preservation",
    "research.scientific_authority_v2.preservation",
    "research.scientific_engines_v1.preservation",
    "research.structured_action_lab_v4.preservation",
    "research.token_policy_gate_v5.preservation",
    "research.trace_envelope_v1.preservation",
))


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("profile", choices=sorted(PROFILES))
    args = parser.parse_args()
    path = reconcile.ROOT / reconcile.MANIFEST
    # A malformed successor refuses; it never falls back to a weaker check.
    if path.exists() or path.is_symlink():
        try:
            result = reconcile.check(require_committed=True)
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            print(json.dumps({"passed": False, "pcs_authority": False, "error": str(exc)}))
            return 1
        print(json.dumps(dict(result, passed=True, original_phase_guard=args.profile,
                              admitted_contract="EXPLICIT_COMBINED_SOURCE_V12",
                              original_additions_only_predicate_claimed=False)))
        return 0
    return subprocess.run([sys.executable, "-m", args.profile], cwd=reconcile.ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
