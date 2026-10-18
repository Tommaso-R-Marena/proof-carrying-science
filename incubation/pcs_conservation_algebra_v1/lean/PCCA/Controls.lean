import PCCA.Stoich
import PCCA.Elemental

/-!
# Executable controls for the conservation algebra

Small finite networks that exercise positive conservation, elemental pools,
and explicit refutation of mass leaks. These are mathematical controls, not
empirical biology.

Decision procedures use `decide +kernel` only (no `native_decide`).
-/
set_option autoImplicit false

namespace PCCA.Controls

open Finset PCCA.Stoich PCCA.Elemental

/-- Three-species, two-reaction glucose cleavage + isomerization stoichiometry. -/
def glucoseS (s : Fin 3) (r : Fin 2) : ℚ :=
  if s = 0 then (if r = 0 then -1 else 0)
  else if s = 1 then (if r = 0 then 2 else -1)
  else (if r = 0 then 0 else 1)

/-- Carbon atoms per species for C6H12O6 / C3H6O3 / C3H6O3. -/
def carbonA (s : Fin 3) : ℚ := if s = 0 then 6 else 3

/-- Hydrogen atoms per species. -/
def hydrogenA (s : Fin 3) : ℚ := if s = 0 then 12 else 6

/-- Oxygen atoms per species. -/
def oxygenA (s : Fin 3) : ℚ := if s = 0 then 6 else 3

theorem good_carbon : check carbonA glucoseS = true := by decide +kernel
theorem good_hydrogen : check hydrogenA glucoseS = true := by decide +kernel
theorem good_oxygen : check oxygenA glucoseS = true := by decide +kernel

theorem carbon_conserves :
    ConservationLaw carbonA glucoseS :=
  check_sound good_carbon

theorem carbon_all_times (ξs : Nat → Fin 2 → ℚ) (x : Fin 3 → ℚ) (n : Nat) :
    pool carbonA (evolve glucoseS ξs x n) = pool carbonA x :=
  conserved_all_times carbonA glucoseS carbon_conserves ξs x n

/-- Mass-leak stoichiometry: cleavage produces only one lactate (not balanced). -/
def leakS (s : Fin 3) (r : Fin 2) : ℚ :=
  if s = 0 then (if r = 0 then -1 else 0)
  else if s = 1 then (if r = 0 then 1 else -1)
  else (if r = 0 then 0 else 1)

theorem carbon_rejects_leak : check carbonA leakS = false := by decide +kernel

/-- Two-cell exchange transport as a stoichiometric reaction network. -/
def exchangeS (s : Fin 2) (_r : Fin 1) : ℚ := if s = 0 then -1 else 1

def totalAmount (_ : Fin 2) : ℚ := 1

theorem exchange_conserves_amount : check totalAmount exchangeS = true := by decide +kernel

theorem exchange_all_times (ξs : Nat → Fin 1 → ℚ) (x : Fin 2 → ℚ) (n : Nat) :
    pool totalAmount (evolve exchangeS ξs x n) = pool totalAmount x :=
  conserved_all_times totalAmount exchangeS (check_sound exchange_conserves_amount) ξs x n

/-- Explicit initial state and one cleavage fire. -/
def x0 (s : Fin 3) : ℚ := if s = 0 then 1 else 0

def ξ0 (r : Fin 2) : ℚ := if r = 0 then (1 : ℚ) / 10 else 0

def x1 : Fin 3 → ℚ := fire glucoseS ξ0 x0

theorem one_step_carbon :
    pool carbonA x1 = pool carbonA x0 :=
  conserved_step carbonA glucoseS carbon_conserves ξ0 x0

theorem one_step_carbon_value : pool carbonA x0 = 6 := by decide +kernel

theorem one_step_carbon_after : pool carbonA x1 = 6 := by
  simpa [one_step_carbon_value] using one_step_carbon

/-- Conservation-law vector space control: sum of C and H is still conserved. -/
theorem joint_CH_conserves :
    ConservationLaw (fun s => carbonA s + hydrogenA s) glucoseS :=
  conservation_add carbonA hydrogenA glucoseS
    (check_sound good_carbon) (check_sound good_hydrogen)

end PCCA.Controls
