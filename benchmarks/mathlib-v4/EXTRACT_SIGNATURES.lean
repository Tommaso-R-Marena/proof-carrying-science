import Mathlib.Data.Set.Function
import Mathlib.Algebra.Group.Basic
import Mathlib.Data.Nat.Factorial.Basic
import Mathlib.Data.List.Basic
import Mathlib.Data.Finset.Card
import Mathlib.Data.Real.Basic

set_option maxHeartbeats 400000
open Lean Elab Command Meta
namespace PCSStatementExtractionV4
partial def expr (e : Expr) : Json :=
  let node (kind : String) (children : Array Json := #[]) (value : String := "") (binder : String := "") :=
    Json.mkObj [("kind", toJson kind), ("value", toJson value), ("children", toJson children), ("binder_info", toJson binder)]
  let bi (b : BinderInfo) : String := match b with
    | .default => "explicit" | .implicit => "implicit" | .strictImplicit => "strict_implicit" | .instImplicit => "instance"
  match e with
  | .bvar n => node "bound" #[] (toString n)
  | .fvar n => node "local" #[] (toString n.name)
  | .mvar n => node "metavariable" #[] (toString n.name)
  | .sort u => node "sort" #[] (toString u)
  | .const n us => node "constant" #[] s!"{n}:{us}"
  | .app f a => node "application" #[expr f, expr a]
  | .lam n t b i => node "lambda" #[expr t, expr b] (toString n) (bi i)
  | .forallE n t b i => node "forall" #[expr t, expr b] (toString n) (bi i)
  | .letE n t v b _ => node "let" #[expr t, expr v, expr b] (toString n)
  | .lit (.natVal n) => node "natural" #[] (toString n)
  | .lit (.strVal s) => node "string" #[] s
  | .mdata _ b => expr b
  | .proj n i b => node "projection" #[expr b] s!"{n}:{i}"
end PCSStatementExtractionV4
syntax "#pcs_statement_signatures" : command
elab_rules : command
  | `(#pcs_statement_signatures) => do
    liftTermElabM do
      let mut rows := #[]
      let names := [``List.mem_pair, ``List.mem_map_of_injective, ``List.length_eq_two, ``List.insert_neg, ``List.foldl_fixed, ``Finset.card_le_card, ``Finset.card_insert_of_notMem, ``Finset.card_erase_add_one, ``Finset.card_image_of_injective, ``Finset.card_union_add_card_inter, ``Nat.factorial_dvd_factorial, ``Nat.dvd_factorial, ``Nat.factorial_eq_one, ``Nat.factorial_inj, ``inv_unique, ``mul_eq_left, ``inv_eq_iff_eq_inv, ``mul_div_assoc', ``eq_of_inv_mul_eq_one, ``Real.ratCast_lt, ``Real.mul_add_one_le_add_one_pow, ``Real.mk_le_of_forall_le]
      for name in names do
        let info ← getConstInfo name
        let .thmInfo _ := info | throwError "selected declaration is not a theorem: {name}"
        rows := rows.push <| Json.mkObj [
          ("name", toJson (toString name)),
          ("universe_parameters", toJson (info.levelParams.map toString)),
          ("statement", toJson (toString (← ppExpr info.type))),
          ("expression", PCSStatementExtractionV4.expr info.type)]
      IO.println s!"PCS_STATEMENT_SIGNATURES:{(toJson rows).compress}"
#pcs_statement_signatures
