import CertNum.Certificate.Checker
import PCCA.Stoich

/-!
Conditional cross-library composition for a declared rational A → B network.
The expression/state link is an explicit premise, not a runtime refinement claim.
No physical nonnegativity, continuum accuracy, authentication or science follows.
-/
namespace PCSIntegration

open CertNum CertNum.Expr CertNum.Certificate

def transfer : PCCA.Stoich.Matrix (Fin 2) (Fin 1) ℚ :=
  fun s _ => if s = 0 then -1 else 1

theorem transfer_conserves : PCCA.Stoich.ConservationLaw (fun _ => (1 : ℚ)) transfer := by
  intro r
  simp [transfer, Fin.sum_univ_two]

/-- Arbitrarily many exact firings conserve A+B; a checked enclosure for A
transfers to B, conditional on the explicitly supplied expression/state link. -/
theorem conserved_complement_enclosure
    (initial : Fin 2 → ℚ) (firings : Nat → Fin 1 → ℚ) (n : Nat)
    (certificate : IntervalEnclosureCert)
    (accepted : checkIntervalEnclosure certificate = true)
    (environment : Env)
    (inBox : EnvInBox environment (toBox certificate.box))
    (semanticLink : certificate.expr.eval environment =
      some (PCCA.Stoich.evolve transfer firings initial n 0)) :
    let state := PCCA.Stoich.evolve transfer firings initial n
    let total := initial 0 + initial 1
    state 0 + state 1 = total ∧
    state 0 ∈ᵢ certificate.claimed ∧
    state 1 ∈ᵢ Interval.sub (Interval.singleton total) certificate.claimed := by
  dsimp only
  have conserved := PCCA.Stoich.conserved_all_times (fun _ => (1 : ℚ))
    transfer transfer_conserves firings initial n
  have sumEq : PCCA.Stoich.evolve transfer firings initial n 0 +
      PCCA.Stoich.evolve transfer firings initial n 1 = initial 0 + initial 1 := by
    simpa [PCCA.Stoich.pool, Fin.sum_univ_two] using conserved
  have enclosed := checkIntervalEnclosure_sound certificate accepted environment inBox semanticLink
  refine ⟨sumEq, enclosed, ?_⟩
  have complement : PCCA.Stoich.evolve transfer firings initial n 1 =
      (initial 0 + initial 1) - PCCA.Stoich.evolve transfer firings initial n 0 := by
    linarith
  rw [complement]
  exact Interval.mem_sub (Interval.mem_singleton _) enclosed

def sampleCertificate : IntervalEnclosureCert where
  expr := .const (2 / 3)
  arith := .const _
  box := []
  claimed := .nonempty (3 / 5) (7 / 10) (by norm_num)

theorem sample_certificate_accepts : checkIntervalEnclosure sampleCertificate = true := by
  norm_num [checkIntervalEnclosure, sampleCertificate, Expr.evalInterval,
            Enclosure.ok, Interval.singleton]

/-- Independently checkable concrete instance: one firing of 1/3 from (1,0). -/
theorem sample_complement_enclosed :
    PCCA.Stoich.evolve transfer (fun _ _ => (1 / 3 : ℚ))
      (fun s => if s = 0 then 1 else 0) 1 1 ∈ᵢ
      Interval.sub (Interval.singleton 1) sampleCertificate.claimed := by
  have result := conserved_complement_enclosure
    (fun s => if s = 0 then 1 else 0) (fun _ _ => (1 / 3 : ℚ)) 1
    sampleCertificate sample_certificate_accepts (fun _ => none)
    (by intro v x h; cases h)
    (by norm_num [sampleCertificate, Expr.eval, PCCA.Stoich.evolve,
                  PCCA.Stoich.fire, transfer, Fin.sum_univ_one])
  simpa using result.2.2

def unrelatedCertificate : IntervalEnclosureCert where
  expr := .const 0
  arith := .const _
  box := []
  claimed := .singleton 0

/-- Checking a numerical statement about another quantity cannot bound this
network's B coordinate. This concrete countermodel explains the semantic link. -/
theorem acceptance_without_semantic_link_is_insufficient :
    checkIntervalEnclosure unrelatedCertificate = true ∧
    ¬ (PCCA.Stoich.evolve transfer (fun _ _ => (1 / 3 : ℚ))
        (fun s => if s = 0 then 1 else 0) 1 1 ∈ᵢ
        Interval.sub (Interval.singleton 1) unrelatedCertificate.claimed) := by
  constructor
  · norm_num [checkIntervalEnclosure, unrelatedCertificate, Expr.evalInterval,
              Enclosure.ok, Interval.singleton]
  · norm_num [PCCA.Stoich.evolve, PCCA.Stoich.fire, transfer, Fin.sum_univ_one,
              unrelatedCertificate, Interval.sub, Interval.add, Interval.neg,
              Interval.singleton, Interval.mk', Interval.Mem]

#print axioms transfer_conserves
#print axioms conserved_complement_enclosure
#print axioms sample_certificate_accepts
#print axioms sample_complement_enclosed
#print axioms acceptance_without_semantic_link_is_insufficient

end PCSIntegration
