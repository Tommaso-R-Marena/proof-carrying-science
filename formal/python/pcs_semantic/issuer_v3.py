"""Reference elaboration / kernel-check receipt issuers for PCS v3 (operational, NOT verified).

An issuer holds an Ed25519 key registered in the authority configuration for one role.  These
reference issuers sign a receipt **only after** running the real Lean 4 frontend/kernel through
``tools/CheckElaborationV3.lean`` on the exact request:

* ``issue_elaboration_receipt`` — signs the elaboration statement only if ``check`` prints
  ``ELABORATION_MATCHES`` (environment fingerprint equal to the bound one, every registry entry
  grounded, proved anti-capture gate, canonical rendering, and Lean's elaborated expression is
  structurally the expression of the proved syntax tree ``readClaim``);
* ``issue_proof_receipt`` — signs the kernel-check record only if ``prove`` prints
  ``KERNEL_CHECK_PASSED`` (additionally: ``decl_name`` is a theorem of exactly that expression,
  every declaration of the proof file was re-checked by the Lean kernel in the clean base
  environment, and its axioms are claimed and allowed).

What a signature from these issuers means: *the holder of this key ran this tool and it
succeeded*.  It is evidence that a kernel check happened only if the key holder is honest and
uncompromised and actually runs this code (the threat model of ``ReceiptThreatModelV3`` bounds
the number of dishonest keys instead of excluding them).  Signing with a PUBLIC test key, as the
tests do, is evidence of nothing.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, Optional, Tuple

from . import receipts_v3 as R

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join("tools", "CheckElaborationV3.lean")


class IssuerRefused(Exception):
    """The issuer refused to sign; ``code`` is the checker's fail-closed code."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code} {detail}")
        self.code = code
        self.detail = detail


def run_tool(*args: str, env_path: Optional[str] = None, timeout: int = 900) -> Tuple[int, str]:
    cmd = ["lake", "env", "lean", "--run", TOOL, *args]
    if env_path is not None:
        cmd += ["--env", env_path]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    lines = [l for l in p.stdout.splitlines() if l.strip()]
    return p.returncode, (lines[-1] if lines else "TOOL_FAILED " + p.stderr[-500:])


def _require(rc: int, line: str, ok_code: str) -> None:
    code = line.split(" ")[0]
    if rc != 0 or code != ok_code:
        raise IssuerRefused(code, line)


def issue_elaboration_receipt(key: R.TestKey, authority: Dict[str, Any], authority_path: str,
                              request_v3: Dict[str, Any], request_path: str, nonce: str,
                              issued_at: int, expires_at: int,
                              env_path: Optional[str] = None) -> Dict[str, Any]:
    rc, line = run_tool("check", authority_path, request_path, env_path=env_path)
    _require(rc, line, "ELABORATION_MATCHES")
    st = R.expected_statement(authority, request_v3, "elaboration")
    return R.sign_envelope(key, "elaboration", st, nonce, issued_at, expires_at)


def issue_proof_receipt(key: R.TestKey, authority: Dict[str, Any], authority_path: str,
                        request_v3: Dict[str, Any], request_path: str, proof_path: str,
                        nonce: str, issued_at: int, expires_at: int,
                        env_path: Optional[str] = None) -> Dict[str, Any]:
    rc, line = run_tool("prove", authority_path, request_path, proof_path, env_path=env_path)
    _require(rc, line, "KERNEL_CHECK_PASSED")
    st = R.expected_statement(authority, request_v3, "proof")
    return R.sign_envelope(key, "proof", st, nonce, issued_at, expires_at)
