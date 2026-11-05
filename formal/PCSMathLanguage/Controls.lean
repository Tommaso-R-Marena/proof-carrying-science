import PCSMathLanguage.Receipt

/-!
# Executed controls for the Math IR, goals, actions and receipts
-/

namespace PCSMathLanguage.Controls

open PCSMathLanguage

/-! ### Bool versus integer, Unicode names, duplicate JSON keys -/

example : ofJson "witness" (.int 1) = some (.witness 1) := by decide
/-- Python `type(True) is int` is false: a Boolean argument is rejected. -/
example : ofJson "witness" (.bool true) = none := by decide
example : ofJson "witness" (.int 9) = none := by decide
example : validName "x1" = true := by decide
/-- Unicode letters are not in `NAME`. -/
example : validName "αx" = false := by decide
example : validName "theorem" = true ∧ RESERVED.contains "theorem" = true := by decide

/-- Python dictionaries keep the **last** duplicate key; a JSON object is decoded that way. -/
def pyGet (obj : List (String × JArg)) (k : String) : Option JArg :=
  (obj.reverse.find? (·.1 == k)).map (·.2)

def actionOfObject (obj : List (String × JArg)) : Option Act :=
  match pyGet obj "kind", pyGet obj "argument" with
  | some (.str k), some a =>
    if (obj.map (·.1)).all (fun k => k == "kind" || k == "argument") then ofJson k a else none
  | _, _ => none

example : actionOfObject [("kind", .str "intro"), ("kind", .str "simp"), ("argument", .none)] =
    some .simp := by decide
example : actionOfObject [("kind", .str "simp"), ("argument", .none), ("extra", .none)] = none := by
  decide

/-! ### Rendering cannot inject commands -/

example : renderAction "exact" (.str "h0.2") = some "exact h0.2" := by decide +kernel
example : renderAction "exact" (.str "sorry") = none := by decide +kernel
example : renderAction "exact" (.str "h0\nimport Foo") = none := by decide +kernel
example : renderAction "cases" (.str "h0 as h1") = some "rcases h0 with h1 | h1" := by decide +kernel

/-! ### Quantifier reversal and alpha renaming -/

def ae (x y : String) : Expr :=
  .quant .all x .nat (.quant .ex y .nat (.bin .le (.var x) (.var y)))
def ea (x y : String) : Expr :=
  .quant .ex y .nat (.quant .all x .nat (.bin .le (.var x) (.var y)))

example : canonDecl ⟨[], ae "x" "y"⟩ = canonDecl ⟨[], ae "a" "b"⟩ := by decide
example : canonDecl ⟨[], ae "x" "y"⟩ ≠ canonDecl ⟨[], ea "x" "y"⟩ := by decide
theorem alpha_renamed : AlphaDecl ⟨[], ae "x" "y"⟩ ⟨[], ae "a" "b"⟩ :=
  (alpha_firewall_exact _ _).1 (by decide)
theorem quantifier_reversal_not_alpha : ¬ AlphaDecl ⟨[], ae "x" "y"⟩ ⟨[], ea "x" "y"⟩ :=
  fun h => absurd ((alpha_firewall_exact _ _).2 h) (by decide)

/-- Capture: `∀ y, x ≤ y` (free `x` bound outside) is not alpha-equivalent to `∀ x, x ≤ x`. -/
example : canonDecl ⟨[("x", .nat)], .quant .all "y" .nat (.bin .le (.var "x") (.var "y"))⟩ ≠
    canonDecl ⟨[("x", .nat)], .quant .all "x" .nat (.bin .le (.var "x") (.var "x"))⟩ := by decide

/-- The firewall rejects an alpha-renamed held-out theorem even with a trivial hash. -/
example : firewallAdmit (fun _ => (0 : Nat)) [⟨[], ae "x" "y"⟩] ⟨[], ae "a" "b"⟩ = false :=
  firewall_rejects_alpha_duplicates _ _ _ _ List.mem_cons_self alpha_renamed

/-- Equal hash indices with unequal content: a constant hash rejects a non-duplicate
(conservative), while the exact firewall admits it. -/
example : firewallAdmit (fun _ => (0 : Nat)) [⟨[], ae "x" "y"⟩] ⟨[], ea "x" "y"⟩ = false := by decide
example : exactAdmit [⟨[], ae "x" "y"⟩] ⟨[], ea "x" "y"⟩ = true := by decide

/-! ### A full proof cycle: `p ∧ q → q ∧ p` -/

def swapDecl : Decl :=
  ⟨[("p", .prop), ("q", .prop)], .bin .implies (.bin .and (.var "p") (.var "q"))
    (.bin .and (.var "q") (.var "p"))⟩

def swapActs : Option (List Act) :=
  [ofJson "intro" (.str "h0"), ofJson "constructor" .none, ofJson "exact" (.str "h0.2"),
   ofJson "exact" (.str "h0.1")].mapM id

def cfg : Config := ⟨"pcs-receiver-v1", "pcs-defs-v1", ["propext", "Classical.choice", "Quot.sound"], 24⟩

def swapReceipt (acts : List Act) : Receipt :=
  ⟨swapDecl, [swapDecl], 0, acts, "pcs-defs-v1", "pcs-receiver-v1", ["propext"], "index-1"⟩

def swapActions : List Act :=
  [.intro "h0", .constructor, .exact ⟨"h0", [true]⟩, .exact ⟨"h0", [false]⟩]

example : swapActs = some swapActions := by decide +kernel

theorem swap_verified : verifyReceipt cfg (swapReceipt swapActions) = true := by decide

/-- The verified receipt yields the Lean statement of the original declaration. -/
theorem swap_holds : DeclHolds swapDecl := (final_receipt_sound cfg _ swap_verified).1

/-- Changed assumptions / changed environment / wrong axiom inventory are rejected. -/
example : verifyReceipt cfg { swapReceipt swapActions with
    decl := ⟨[("p", .prop), ("q", .prop)], .bin .implies (.var "p") (.bin .and (.var "q") (.var "p"))⟩ } =
    false := by decide
example : verifyReceipt cfg { swapReceipt swapActions with definitions := "pcs-defs-v2" } = false := by
  decide
example : verifyReceipt cfg { swapReceipt swapActions with axioms := ["sorryAx"] } = false := by decide
/-- A stale receipt whose actions prove another goal does not verify. -/
example : verifyReceipt cfg (swapReceipt [.intro "h0", .exact ⟨"h0", []⟩]) = false := by decide

/-! ### One closed branch of `A ∨ B → A` -/

def orDecl : Decl :=
  ⟨[("a", .prop), ("b", .prop)], .bin .implies (.bin .or (.var "a") (.var "b")) (.var "a")⟩

def orGoal : Goal := ⟨[], .imp (.or (.atom 1) (.atom 0)) (.atom 1)⟩

example : declGoal orDecl = some orGoal := by decide

/-- After `intro h0; rcases h0 with h1 | h1; assumption` the `b` branch remains open. -/
example : (runActs 24 (PState.init orGoal)
    [.intro "h0", .cases ⟨"h0", []⟩ (some "h1"), .assumption]).goals =
    [⟨[("h1", .atom 0), ("h0", .or (.atom 1) (.atom 0))], .atom 1⟩] := by decide

theorem orGoal_invalid : ¬ orGoal.Valid := by
  intro h
  have := h (fun i => if i = 0 then some ⟨.prop, True⟩ else some ⟨.prop, False⟩) (by simp [orGoal])
  simp [orGoal, GF.den, propAt] at this

/-- No action sequence whatsoever closes `A ∨ B → A`. -/
theorem or_never_closed (as : List Act) : (runActs 24 (PState.init orGoal) as).goals ≠ [] :=
  all_branches_required 24 orGoal orGoal_invalid as

end PCSMathLanguage.Controls
