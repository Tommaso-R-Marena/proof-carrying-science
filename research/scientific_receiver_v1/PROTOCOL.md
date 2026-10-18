# Scientific bound receiver protocol v1

Status: protocol and implementation work in progress; no receiving theorem or authority is asserted by this specification alone. Research-only, stacked on PR153 at b916eec1b9d0d5c02c9cc19b070f7a47df5e5d87. Existing protocols and production authority remain unchanged.

The exact canonical ASCII tag is `PCS-SCI-BOUND-V1`. Every remaining field is an integer, separated by a single `|`. No final separator, newline, whitespace, BOM, Unicode, extra field, producer proof flag, executable expression or version fallback is supported. Canonical integers are `0`, a nonzero decimal digit followed by zero or more decimal digits, or `-` followed by the positive form. `-0`, `+1`, `00` and all equivalent alternate encodings reject. Each rational is a numerator/denominator pair, with strictly positive denominator and gcd(abs(numerator),denominator)=1; zero is exactly `0|1`. Numerators and denominators are bounded in magnitude by 10^18. Fields have at most20 ASCII characters. Total input is at most8192 bytes. There are at most64 firings.

The integer sequence after the tag is exactly:

1. policy version `1`;
2. model family `1` (exact discrete A→B);
3. species A code `0`;
4. species B code `1`;
5. stoichiometric A coefficient `-1`;
6. stoichiometric B coefficient `1`;
7. conserved A weight `1`;
8. conserved B weight `1`;
9. expression code `0` (the final A coordinate, never an unrelated expression);
10. `referenceStep` (a natural number≤64, required at receiving to equal the firing count);
11. `unitCode` (`0`: common uninterpreted amount; `1`: declared mol; no conversion or empirical dimensional validation);
12. `physical` (`0`: algebraic scope; `1`: additionally check nonnegative initial/intermediate states and firings);
13. assumption declaration code `1` (exact discrete declared model, common units; empirical/kinetic validity unestablished);
14. limitations declaration code `1` (no continuum/measurement/empirical/cryptographic/host-security conclusion);
15–30. eight reduced rational pairs in this order: `initialA`, `initialB`, `envValue`, `boxLo`, `boxHi`, `lower`, `upper`, `declaredTotal`;
31. firing count `n` (natural≤64);
32 onward. exactly `n` reduced rational pairs for the firing schedule.

Typed contract fields and names are fixed in `formal/PCSScientificReceiver/Types.lean`. The receiver computes every state from the initial state and schedule using S=(-1,1). It checks the declared total equals initialA+initialB, the reference step equals n, and envValue equals the computed final A coordinate. Its only numerical expression is the variable `A_final`, with environment mapped to envValue, declared interval box [boxLo,boxHi], and claimed enclosure [lower,upper]. It rejects reversed endpoints, requires the actual value inside the box, and executes the existing CertNum variable-enclosure checker. The state/expression link must be proved from these checks, never assumed from a producer assertion. It derives final B bounds [total-upper,total-lower]. Unit and assumption declarations grant no empirical authority.

A changed initial value or schedule is not intrinsically invalid: it must reject when inconsistent with the submitted evidence, or produce an appropriately changed correctly scoped result. Positive fixtures must include zero, one and multiple steps, nonsingleton intervals, signed algebraic schedules, and separately checked nonnegative schedules.

Independent Python reference code must parse this grammar and replay rational transitions without importing the producer's encoder or validation/decision logic. The producer may use direct sum formulas; the independent reference should replay each transition. JSON is an untrusted convenience adapter only; duplicate keys, unknown fields and noncanonical rationals reject. Neither Python JSON nor its PASS fields define Lean acceptance.

The planned pure Lean API is `decode : List UInt8 → Option Contract` and `receive : List UInt8 → Option Result`, with executable byte input forwarded unchanged to the same pure function. Result rendering, hashes, signatures, compiler/IO/OS correspondence and independently protected execution roots retain their own explicit obligations.
