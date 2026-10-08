import PCS.V2.Authority
import PCS.V2.SHA256Spec

/-!
# High-assurance flagship: the Lean-authoritative path with a smaller trusted base

`PCS.V2.Flagship.pcs_accept_implies_scientific_assurance` is stated for an arbitrary
oracle bundle and needs all four `ExternalContracts`:

1. `Ed25519ImplCorrect` â€” the Ed25519 primitive meets a specification;
2. `NoForgery` â€” unforgeability for the trust-anchor key;
3. `CaptureSound` â€” the environment capture means what `describes` says;
4. `ReplayFaithful` â€” every replay `PASS` means the scientific predicate holds.

For the production authority (`PCS.V2.Authority.acceptPCSWithTranscript`, the function
whose verdict the compiled `pcs-lean-authority` prints, see
`diagnose_accept_implies_accept`) this file proves strictly stronger statements:

* `pcs_verified_builtin_acceptance_sound` â€” **no hypothesis at all**: acceptance implies
  structural assurance, per-claim `Assures`, and that every passing `reaction_balance`,
  `unit_compatible`, `csv_disjoint`, `pkpd_contract`, `pkpd_reference_match`, and
  `pkpd_peak_concentration_threshold` evidence
  item denotes its declarative scientific proposition (balanced reaction / equal physical
  dimension / disjoint strict-CSV key sets / restricted PK/PD positivity-and-dimension
  contract / certified-interval agreement of every reported row with the analytic PK/PD
  model; the real-valued form is `PCSReal.PKPD.pcs_pkpd_refeq4T4 =´Û]œ…ªì