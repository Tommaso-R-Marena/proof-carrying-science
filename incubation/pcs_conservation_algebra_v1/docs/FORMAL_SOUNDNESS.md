# Formal soundness notes

- `check` / `checkTrajectory` use Lean `decide` on exact rationals; no
  `native_decide`.
- `rational_certificate_real` embeds successful rational checks into ℝ via
  `exact_mod_cast`.
- Conservation is proved for **all** firing vectors, so it is strictly stronger
  than “this particular Euler trajectory conserved carbon.”
- Trajectory certificates require every step to be an exact fire of the declared
  `S`; a forged trajectory that merely keeps a pool constant by coincidence but
  is not stoichiometric is rejected.
- Axiom surface: `{propext, Classical.choice, Quot.sound}` or fewer
  (`PCCA/Audit.lean`).
