# Fresh replay import precedence correction

A fresh, isolated Python dependency-closure attempt exposed that `lake env` prepends
its cached project build directory ahead of an inherited `LEAN_PATH`. Compiling a
source certificate into a temporary overlay therefore did not establish that later
lowering/principal/audit commands imported that fresh output. In the local attempt,
six modules compiled successfully (including the Python source certificate in
73.390990 seconds and its lowering), but the seventh command failed because Lake
selected an absent cached lowering instead of the fresh overlay. That attempt is a
failure; it establishes no complete closure qualification.

The receiver now resolves Lake's `PATH` and `LEAN_PATH` once, prepends its fresh
overlay, and invokes the resolved Lean executable directly for every replay
compilation, audit and negative control. It checks the exact Lean 4.28.0 release
commit `7e01a1bf5c70fc6167d49c345d3bf80596e9a79b`. It never re-enters `lake env` after
setting fresh-import precedence. Actual direct commands and the version check are
included in receiving execution records.

A kernel-backed regression compiles conflicting modules with the same name into
cached and fresh directories. The fresh module admits a `True` proof; the cached
module would require proving `False`. Correct receiving precedence accepts the
fresh proof, while deliberately stale precedence rejects it with a type mismatch.
The existing 673-name complete inventory, six fresh replay modules, source-byte
contracts and approved-axiom gate remain mandatory.

The earlier protected full 68-module source build is independently meaningful;
its temporary-replay import isolation claim needs this correction. Its historical
478-name audit remains partial. Neither the old audit nor successful finite parity
testing substitutes for the corrected 673-name audit and complete protected CI.
