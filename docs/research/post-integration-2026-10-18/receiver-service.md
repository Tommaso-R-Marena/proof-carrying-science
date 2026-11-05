# Separately launched scientific receiving process

Research branch: `research/pcs-receiver-host-v1-20261018`, based on integration
head `b916eec1b9d0d5c02c9cc19b070f7a47df5e5d87` with the parent's scientific
receiver commits applied for dependency setup. No production authority change.

`research/scientific_receiver_v1/host.py` provides a bounded process wrapper for
`PCS-SCI-BOUND-V1`. The operator constructs `OperatorConfig` once; a request
supplies only immutable raw bytes or a regular-file path. Requests cannot choose
a verifier, command, environment, policy, pin inventory or executable expression.
The separate child runs the operator's fixed command, without a shell or inherited
environment overrides.

For each request the wrapper checks configured executable/source/dependency
SHA-256 pins before and after the process, frames exactly the input snapshot,
limits elapsed child execution and both output pipes, and requires a successful
exit with exactly one strict JSON response. Duplicate keys, nonfinite JSON,
extra fields, wrong protocol/policy, boolean-as-integer policy, wrong raw byte
echo, wrong scope flags and mismatched exact rational results reject.

The actual Lean result is conjunctively checked against the independent Python
transition replay. Python cannot supply a positive Lean verdict when the child
fails. The returned `accepted` means only that this scoped mathematical receiver
accepted under its explicit assumptions. `scientific_acceptance` and
`production_authority` are always false. The actual child result and per-stage
status remain in the receipt, including on a normal mathematical rejection.

A path request is opened once with no symlink following; regular-file and byte
bounds reject FIFOs, devices and oversize files before child launch. All child
input and result checks use the captured bytes. Replacing the original path
while verification runs does not change those bytes. The wrapper never reopens
that input path during verification or receipt construction.

## Operator API and portable invocation

```python
from research.scientific_receiver_v1.host import (
    operator_config_for_lean, ReceiverService, replay_signed_receipt,
)
config = operator_config_for_lean(
    executable=lean_path, main=main_path, cwd=formal_directory,
    lean_path=reviewed_lean_search_path,
    source_files=reviewed_source_paths,
    dependency_files=reviewed_dependency_paths,
    toolchain="Lean 4.28.0; operator-reviewed toolchain identity",
)
service = ReceiverService(config)
envelope = service.verify_bytes(received_bytes)
```

The helper pins exactly the operator-supplied inventory plus Main, this host,
and the independent reference source. It does not infer or prove closure
completeness. In particular, `lean --deps Main.lean` alone returns direct imports,
not a full transitive module inventory. The parent qualification's full declared
module/artifact inventory can be supplied separately. Its correspondence to OS
loaded libraries/compiler execution remains a separate assumption.

The CLI is operator launch code:

```
python -m research.scientific_receiver_v1.host \
  --operator-config /operator/reviewed-config.json \
  --request /received/contract.wire --receipt /fresh/output.json
```

A caller who launches another service with another configuration or key has not
replaced this service's externally pinned identity. Config JSON uses exact fields
`command`, `executable_sha256`, `pins`, `cwd`, `environment`, `toolchain`,
`timeout_seconds`, `stdout_limit`, and `stderr_limit`. Each pin has `kind`
(`source` or `dependency`), absolute `path`, and lowercase `sha256`.
The CLI creates its receipt exclusively and exits zero only on accepted input.

Each service instance generates an ephemeral Ed25519 key. Its signature binds
canonical receipt bytes, raw SHA-256/hex, fixed policy, operator configuration
identity, executable/source/dependency hashes, declared toolchain and result.
`replay_signed_receipt(envelope, expected_public_key_hex)` requires an explicitly
supplied public key and detects modification. This is signature replay, not a
new Lean execution or a proof of historical occurrence. Independent execution
replay calls the fixed receiver again with the same raw bytes.

## Security boundary and open obligations

This implements separately launched verification, not an independently
administered verifier or immutable execution root. Ordinary Python objects,
source files, hashes, process groups, filesystem permissions and ephemeral keys
are not unconditional security boundaries. The trusted computing base includes
operator configuration, host Python/reference, Lean/compiler and dependencies,
OS/loader, source/dependency inventory completeness, storage and key handling.

Pre/post hashes do not exclude transient substitution followed by restoration,
in-place modification during a load, or a malicious same-UID/root actor. The
fixed executable and source paths remain OS execution inputs. No executable
memory measurement, protected independent credentials, protected storage,
loaded-library attestation or compiler refinement has been established.
A child process is terminated on timeout/output failure; process-group cleanup
is best effort, not a sandbox against a hostile child escaping its group.

An ephemeral signature provides no independent operator identity until its key
is pinned over a separate trusted channel. It does not establish authenticated
external chronology or empirical validity. Receipt toolchain metadata are
operator-declared and tied to executable hashes, not independently certified.

## Test evidence

Tests use the actual Lean 4.28.0 executable with the parent's exact Main and
compiled scientific receiver modules. Local setup reads `/tmp/pcs-receiver-lean-env.json`;
CI instead uses `PCS_SCIENTIFIC_LEAN`, `PCS_SCIENTIFIC_MAIN`,
`PCS_SCIENTIFIC_CWD`, and `LEAN_PATH`. `PCS_SCI_HOST_OPERATOR_CONFIG` can select
an operator-provided integration configuration at test bootstrap. Missing real
infrastructure fails these integration tests; there is no mocked success fallback.

The local test inventory pins scientific source/module files and host/reference
source. It is explicitly a partial dependency inventory: success under it does
not claim the complete compiler/runtime closure was independently measured.
A full closure profile is a separate operator qualification artifact.

Synthetic child programs occur only in rejection tests: malformed/duplicate or
multiple responses, NaN, invalid UTF-8, fake positive flags/results, excessive
stdout/stderr, nonzero exit, timeout and source modification. They are never
reported as successful Lean authorization.

Final owned host suite: **32 passed, zero skips**, 39.64 s. This includes ten
actual Lean fixture cases, a live input-path substitution test, the actual CLI
path and rejection-only synthetic subprocess controls. JUnit evidence:
`/workspace/.onboarding/pcs-receiver-host-final-tests.xml`.

The actual executable SHA-256 was
`3e0d0d3d801675359f2d4cf9815bfdb417b20b92fdd9d48b3b14c95bbae28bbf`.
It reported Lean 4.28.0, commit
`7e01a1bf5c70fc6167d49c345d3bf80596e9a79b`.
Main source SHA-256 was
`427f046da8101b3e1b29c28caaf40c72ddb3da49c2ba5d5012dacb02c579ca99`.
This session's partial local integration profile had ten source pins and six
dependency pins. These are source/execution observations, not compiler or loaded
runtime attestation. Independent source review and hosted CI remain separate.
