# Final combined-suite namespace integration repair

The first final combined pytest invocation exposed two failing witness transport
controls. Both earlier passed under the canonical `python -m unittest
research.scientific_witness_v1...` import path. Investigation reproduced the
failure in a fresh focused pytest process: pytest named the namespace package
`scientific_witness_v1`, while the existing fault patch targeted
`research.scientific_witness_v1.server.ACQUISITION_SECONDS`. This loaded two module
identities, so the0.3s test deadline did not replace the actual5s default; both
2s client probes timed out. The production5s deadline was not removed or bypassed.

`--import-mode=importlib` alone reproduced both failures. Enabling pytest's
`consider_namespace_packages=true` makes collection preserve the canonical
`research.*` identity. The same two controls then passed in1.01s with identical
assertions, deadline values, server source and fault patches. The new research
workflow now explicitly sets that collection option. No application, Lean,
cryptographic, production or predecessor source file changes are needed.

The original failed log and final corrected combined JUnit/log are retained in
the external final handoff. The exact revised GitHub proposed-merge tree must
repeat all required inherited and new workflow qualification. Earlier parent
results and the superseded workflow run are not final-tree qualification.
