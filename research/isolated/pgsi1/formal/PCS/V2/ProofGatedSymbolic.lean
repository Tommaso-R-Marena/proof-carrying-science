import Lean

/-! Symbolic companion: universal semantic equivalence and AST-cost decrease.
    These statements hold for every integer input, not just benchmark tasks.
    AST nodes measure structure, not real-world runtime or intelligence. -/
namespace PCS.V2.ProofGatedSymbolic

inductive Expr where
  | var
  | lit (n : Int)
  | add (a b : Expr)
  | mul (a b : Expr)
  deriving Repr, DecidableEq

def eval : Expr → Int → Int
  | .var, x => x
  | .lit n, _ => n
  | .add a b, x => eval a x + eval b x
  | .mul a b, x => eval a x * eval b x

def nodes : Expr → Nat
  | .var => 1
  | .lit _ => 1
  | .add a b => 1 + nodes a + nodes b
  | .mul a b => 1 + nodes a + nodes b

structure ValidRewrite (before after : Expr) : Prop where
  equivalent : ∀ x : Int, eval before x = eval after x
  smaller : nodes after < nodes before

theorem add_zero_rewrite (e : Expr) : ValidRewrite (.add e (.lit 0)) e := by
  constructor
  · intro x
    simp [eval]
  · simp [nodes]
    omega

theorem multiply_one_rewrite (e : Expr) : ValidRewrite (.mul e (.lit 1)) e := by
  constructor
  · intro x
    simp [eval]
  · simp [nodes]
    omega

theorem rewrites_compose {a b c : Expr}
    (hab : ValidRewrite a b) (hbc : ValidRewrite b c) :
    ValidRewrite a c := by
  constructor
  · intro x
    exact (hab.equivalent x).trans (hbc.equivalent x)
  · exact Nat.lt_trans hbc.smaller hab.smaller

end PCS.V2.ProofGatedSymbolic
