# PCS Trace Lab: create, inspect and independently replay exact cases

The lab joins the existing puzzle and counterexample workshop to a complete-trace
inspector, a standard-library launcher, and nine new finite-vector/trace theorems.
It is an isolated research extension to frozen PR168
`a84b485a4b7b84a6eb69e05a3ee7bcc26d5bf71b`. Production authority, canonical
receivers, receipt schemas, the old exact engine/export parser, previous Lean
statements, and Aristotle modules remain unchanged. No merge or deployment occurs.

## Start in one command

From the reviewed research checkout:

```sh
python -m research.trace_lab_v1 serve --open
```

Python3.11+ and a modern browser are sufficient to play, build and inspect; no
Lean download, pip install, npm build, account or API is required. The optional
`--open` opens the fixed local URL. Without it, the launcher prints the URL.
`--port 0` chooses a free port; the default is8080. Stop with Ctrl-C.

Use the Play, Build and Inspect buttons without losing the seeded challenge URL.
Build a workshop trace, click **Inspect this case**, or select an existing JSON
export. The inspector shows every recorded row, the first proposed exact fault,
invariant summaries and normalized concentration bars with exact rational labels.
It never supplies a Lean verdict. Files stay in the browser; there is no upload or
verification service. Match and mismatch are browser calculations, not certificates.

Download the **captured original bytes**, save as `inspected-case.json`, and copy:

```sh
python -m research.flux_detective_v1.check inspected-case.json ./new-evidence
python -m research.portable_transport_v2.replay verify ./new-evidence
```

Choose an unused evidence directory each time. Exit0 means kernel support for the
finite trace, exit10 kernel refutation, exit20 refusal/unavailability. The pinned
Lean4.28.0/Mathlib and Python package setup in the existing README is required for
these independent commands. `python -m research.trace_lab_v1 doctor` reports tool
availability without issuing a proof verdict or downloading tools.

## Nine new mathematical results

`Vector.lean` imports unchanged transport/trace semantics and PR168's pair results.
For an arbitrary finite index type with decidable equality, `shift` subtracts t/v_a
at a and adds t/v_b at distinct b; every other coordinate stays unchanged.

| `PCSTraceLab` theorem | Exact guarantee |
| --- | --- |
| `at_left`, `at_right`, `elsewhere` | Exact coordinate semantics; distinct indices are required for the right-coordinate result. |
| `amount_shift` | Whole-vector weighted amount is preserved for distinct coordinates with nonzero selected volumes. |
| `quadratic_shift` | Whole-vector quadratic-energy change is exactly the pair's energy change. |
| `energy_iff` | For positive selected volumes, global energy does not increase iff t lies between0 and the exact pair root. |
| `bounds_shift` | Old global bounds and the two updated coordinate bounds imply new global bounds. |
| `feasible_shift` | PR168's complete rational interval implies whole-vector amount, bounds and energy preservation. |
| `trace_reject` | Given any baseline accepted by the unchanged trace checker, changing its final row by any nonzero transfer causes that same checker to reject. |

`trace_reject` holds for any finite dimension and horizon N, including N=0, when
the selected first volume and transfer are nonzero. It uses uniqueness from the
existing checker. Distinctness is not needed for rejection: if indices coincide,
the definition's first branch still changes the coordinate. Distinctness remains
mandatory for the amount and energy preservation claims. No stochasticity or
physical validity is inferred merely from baseline trace acceptance.

These theorems close the mathematical bridge from pair formulas to finite vectors
and the existing trace predicate. They do **not** prove the JavaScript, Python,
JSON/CSV decoder, compiler, OS or scientific model correct.

## Engineering and input semantics

- The local HTTP server binds only127.0.0.1, captures nine reviewed asset files
  once, and serves that snapshot. A manifest identifies their exact bytes.
  Traversal, arbitrary repository files, non-loopback Host headers and writes are
  refused. There is no subprocess/verification endpoint. Captured assets improve
  consistency under accidental path changes; Python memory and hashes do not
  establish an immutable security root. The manifest's commit is only a hint.
- Imported UTF-8 bytes are captured before analysis. Download and optional SHA256
  use those same bytes, not reserialized JSON. Hashes identify bytes, not authors.
- A dedicated module worker runs exact bounded rational arithmetic. A new import
  terminates the previous worker; epoch checks suppress stale responses. Refusals
  clear prior results and disable downloads. A five-second deadline terminates
  unavailable or expensive browser analysis. This is availability handling, not
  an independently administered verification boundary.
- JSON parsing rejects duplicate keys at every depth, unpaired surrogates,
  nonintegral numeric metadata syntax, unsafe integers and structural-budget
  violations. Input is capped at256KiB, JSON depth16/nodes30000, arithmetic4096bits,
  models2..16cells/1..64steps and the existing bounded positive/CFL contract.
- The inspector preserves the existing receiver's exact decimal/scientific/fraction
  grammar, including accepted rational aliases and negative zero, without binary
  floating-point predictions. It normalizes values only for display. No canonical
  encoder or authority parser is weakened or changed.
- Quoted CSV is an explicit browser-subset refusal even where the Python receiver
  accepts it. Such cases can go directly to the unchanged CLI. Resource refusal is
  distinct from an arithmetic mismatch. Browser output always keeps kernel, PCS
  authority and empirical-validation flags false.
- All displayed content uses DOM text, including untrusted inputs. Download names
  and replay commands are fixed; submitted filenames never enter shell commands.
  Clipboard convenience has a bounded fallback, and the visible command remains
  usable without clipboard permissions.

## Reproduction and evidence

```sh
source scripts/activate_lean_428.sh
python -m research.trace_lab_v1.audit --out /new/combined-formal-audit
node --test research/flux_detective_v1/test_engine.mjs research/flux_detective_v1/test_forge.mjs research/flux_detective_v1/test_inspector.mjs research/flux_detective_v1/test_browser.mjs
python -m pytest -q research/flux_detective_v1/test_correspondence.py research/flux_forge_v1/test_forge.py research/trace_lab_v1/test_lab.py research/portable_transport_v2/test_replay.py
python -m research.trace_lab_v1.preservation
```

The combined formal audit captures and freshly compiles Transport, TransportTrace,
Transfer and Vector, checks all36 exact theorem inventories, then runs the official
`leanchecker --fresh Vector`. Only propext/Classical.choice/Quot.sound are permitted.
It pins the reviewed **Linux x86_64** compiler and checker binary digests before
and after execution, as well as source and object bytes. Other platforms may serve
the lab, but require a separate reviewed toolchain qualification for this audit.
The object checker is the same Lean kernel; imported cache objects/compiler/OS and
same-host administration remain trusted. No source rebuild of all Mathlib occurs.

The final focused pipeline contains **85 Python tests and32 Node/browser tests**,
plus the combined formal audit. The new inspector is compared with the independent
Python receiver on all **2,520 existing exports** (the1,224 puzzle and1,296 workshop
cases, not additional independent scientific samples). Two inspected cases receive
real Lean support/refutation, alongside the26 retained prior cases. Stale-worker
and timeout tests simulate browser failures only; no affirmative Lean verdict is
mocked. Real-browser tests also launch the server with Python `-S`, demonstrating
that play/inspection does not require installed Python packages.

The existing pair-grid and policy experiments remain unchanged: tighter energy
still accepts276 invalid unique cases in the constructed protocol. This lab adds
no new population experiment, measured educational benefit, engagement result,
physical/continuum validation or recursive-self-improvement claim.

Next: formally refine byte decoding and executable vector updates, broaden browser
CSV support through explicit compatibility work, and evaluate whether people can
diagnose unseen-model counterexamples. Production and future Aristotle codec
integration remain separate reviewable work.
