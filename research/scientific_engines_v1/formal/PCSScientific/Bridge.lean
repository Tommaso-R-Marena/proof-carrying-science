import PRISM.Certificates.Checker
import RequestProject.AION.Checker

/-! Research composition: model-conditioned risk certificates and identified
    experimental policies. No claim about real-world model membership is inferred. -/
set_option autoImplicit false
namespace PCSScientific

open PRISM PRISM.Problem AION AION.MACRN

/-- An accepted pair of AION certificates bounds the same event only when the
lower/upper target coordinates and levels agree. The premise is explicit. -/
theorem checked_model_interval {d n : Nat} (net : MACRN d n)
    (u : UpperCert d) (l : LowerCert d)
    (hj : l.jB = u.jB) (hlvl : l.lvl = u.lvl)
    (hu : net.checkUpper u = true) (hl : net.checkLower (tabooA u.zero) l = true)
    (x : Fin d → Nat) (lo hi : ℚ)
    (hlo : lo ≤ l.f (tabooA u.zero) x) (hhi : u.g x ≤ hi) :
    (lo : ℝ) ≤ net.toJump.hitProb {y | tabooA u.zero y = true} {y | u.lvl ≤ y u.jB} x ∧
    net.toJump.hitProb {y | tabooA u.zero y = true} {y | u.lvl ≤ y u.jB} x ≤ (hi : ℝ) := by
  have hU := net.checkUpper_sound hu x
  have hL := net.checkLower_sound hl x
  rw [hj,hlvl] at hL
  exact ⟨le_trans (by exact_mod_cast hlo) hL,le_trans hU (by exact_mod_cast hhi)⟩

/-- An envelope transfers to an actual model only under actual membership. -/
theorem model_envelope {M : Type} [DecidableEq M] (K : Finset M)
    (risk : M → ℝ) (lo hi : M → ℚ) (m : M) (hm : m ∈ K)
    (hb : ∀ a ∈ K, (lo a : ℝ) ≤ risk a ∧ risk a ≤ (hi a : ℝ)) :
    ((K.inf' ⟨m,hm⟩ lo : ℚ) : ℝ) ≤ risk m ∧
      risk m ≤ ((K.sup' ⟨m,hm⟩ hi : ℚ) : ℝ) := by
  exact ⟨le_trans (by exact_mod_cast Finset.inf'_le lo hm) (hb m hm).1,
    le_trans (hb m hm).2 (by exact_mod_cast Finset.le_sup' hi hm)⟩

/-- Experimental success at zero tolerance identifies a query exactly within
its terminal version space. This does not assert that the query models truth. -/
theorem terminal_query_identified {M E O : Type} [DecidableEq O]
    (P : PRISM.Problem M E O) (p : PRISM.Policy E O) (K : Finset M)
    (hs : P.Succeeds 0 p K) (m : M) (hm : m ∈ K)
    (a : M) (ha : a ∈ P.terminal p m K) : P.q a = P.q m := by
  have hself := P.mem_terminal_self p hm
  have hwidth := hs m hm
  have h1 := P.sub_le_width ha hself
  have h2 := P.sub_le_width hself ha
  linarith

/-- A model-indexed risk classification transfers after an identifying policy,
provided both the classifier correspondence and model membership are supplied. -/
theorem identified_risk_classification {M E O : Type} [DecidableEq O]
    (P : PRISM.Problem M E O) (p : PRISM.Policy E O) (K : Finset M)
    (risk : M → ℝ) (threshold : ℝ)
    (hc : ∀ a ∈ K, P.q a = 0 ↔ risk a ≤ threshold)
    (hs : P.Succeeds 0 p K) (m : M) (hm : m ∈ K)
    (a : M) (ha : a ∈ P.terminal p m K) :
    P.q a = 0 ↔ risk m ≤ threshold := by
  rw [terminal_query_identified P p K hs m hm a ha]
  exact hc m hm

/-- Checking an optimal PRISM certificate gives both global minimax optimality
and the identified risk conclusion, under the separate risk correspondence. -/
theorem optimal_identified_risk {M E O : Type} [DecidableEq M] [DecidableEq O] [Fintype E]
    (P : PRISM.Problem M E O) (K : Finset M) (c : PRISM.Problem.OptCert M E O)
    (risk : M → ℝ) (threshold : ℝ)
    (hc : ∀ a ∈ K, P.q a = 0 ↔ risk a ≤ threshold)
    (h : P.checkOptimal 0 K c = true) (m : M) (hm : m ∈ K) :
    (∀ a ∈ P.terminal c.policy m K, P.q a = 0 ↔ risk m ≤ threshold) ∧
    (∀ p : PRISM.Policy E O, P.Succeeds 0 p K → c.bound ≤ P.worstCost p K) := by
  have ho := P.checkOptimal_sound (by norm_num) h
  exact ⟨fun a ha => identified_risk_classification P c.policy K risk threshold hc ho.1 m hm a ha,
    ho.2.2.1⟩

/-- The identifying policy preserves an actual model's previously checked risk
interval; successful experiment selection cannot create empirical membership. -/
theorem posterior_risk_interval {M E O : Type} [DecidableEq O]
    (P : PRISM.Problem M E O) (p : PRISM.Policy E O) (K : Finset M)
    (risk : M → ℝ) (lo hi : ℝ)
    (hb : ∀ a ∈ K, lo ≤ risk a ∧ risk a ≤ hi) (m : M) (hm : m ∈ K) :
    m ∈ P.terminal p m K ∧ lo ≤ risk m ∧ risk m ≤ hi :=
  ⟨P.mem_terminal_self p hm,hb m hm⟩
end PCSScientific
