import PCSConditionalRuntime.PyMain
import PCSConditionalRuntime.JsMain
import PCSConditionalShieldBridge

/-!
Source-extracted conditional checkers and all-history shield safety, under their
explicit callee contracts. The reference equivalence decision and the state/action
encoding are checked obligations; an arbitrary producer receipt is insufficient.
Nothing here proves native interpreter/OS behavior or deployed-model completeness.
-/
set_option autoImplicit false

namespace PCSConditionalShield

open PCSCR PCSCR.Py PCSDD PCSActionShield

def PythonCorresponds (ext : Ext) (dg : T → String) (names : List String)
    (tj : T) (t : CTask names.length) (lim : Limits) : Prop :=
  ∃ v heap, Eventually (fun k => pyRunCheck ext k tj (limT lim)) (.ok v heap) ∧
    (∀ k, pyRunCheck ext k tj (limT lim) = .fuel ∨ pyRunCheck ext k tj (limT lim) = .ok v heap) ∧
    ∃ fuel, readback fuel heap v = some (receiptT names tj dg (PCSDD.check t lim))

def JavaScriptCorresponds (ext : Ext) (dg : T → String) (names : List String)
    (tj : T) (t : CTask names.length) (lim : Limits) : Prop :=
  ∃ v heap, Eventually (fun k => PCSCR.Js.jsRunCheck ext k tj (limT lim)) (.ok v heap) ∧
    (∀ k, PCSCR.Js.jsRunCheck ext k tj (limT lim) = .fuel ∨ PCSCR.Js.jsRunCheck ext k tj (limT lim) = .ok v heap) ∧
    ∃ fuel, readback fuel heap v = some (receiptT names tj dg (PCSDD.check t lim))

theorem python_runtime_and_guard_histories_safe (ext : Ext) (dg : T → String)
    {names : List String} (hnd : names.Nodup) (tj : T) (t : CTask names.length)
    (htask : TaskDen names tj t) (lim : Limits) (hlv : lim.valid = true)
    (hval : ValidateAccepts ext tj) (hdg : DigestOK ext dg)
    (hdecision : (PCSDD.check t lim).decision = .equivalentUnderAssumptions)
    (m : Model) (hcertificate : PCSActionShield.check m = true)
    (encoding : Nat → Nat → Nat → Bool)
    (hcontext : ∀ s a, allEval t.assumptions (encoding s a) = true)
    (hsource : ∀ s a, t.source.eval (encoding s a) = true ↔ (s, a) ∈ m.allowed)
    {history : List Edge} {state : Nat}
    (h : GuardHistory m (fun s a => t.candidate.eval (encoding s a)) history state) :
    PythonCorresponds ext dg names tj t lim ∧
    state ∈ m.safe ∧ ∀ e ∈ history, e.action ∉ m.forbidden := by
  exact ⟨python_conditional_refines_reference ext dg hnd tj t htask lim hlv hval hdg,
         conditional_guard_histories_safe t lim hdecision m hcertificate encoding hcontext hsource h⟩

theorem javascript_runtime_and_guard_histories_safe (ext : Ext) (dg : T → String)
    {names : List String} (hnd : names.Nodup) (tj : T) (t : CTask names.length)
    (htask : TaskDen names tj t) (hb : PCSCR.Js.JsTaskBounds t) (lim : Limits) (hlv : lim.valid = true)
    (hval : PCSCR.Js.JValidateAccepts ext tj) (hexact : PCSCR.Js.JExactOK ext)
    (hint : PCSCR.Js.JIntegerOK ext) (hdg : DigestOK ext dg)
    (hdecision : (PCSDD.check t lim).decision = .equivalentUnderAssumptions)
    (m : Model) (hcertificate : PCSActionShield.check m = true)
    (encoding : Nat → Nat → Nat → Bool)
    (hcontext : ∀ s a, allEval t.assumptions (encoding s a) = true)
    (hsource : ∀ s a, t.source.eval (encoding s a) = true ↔ (s, a) ∈ m.allowed)
    {history : List Edge} {state : Nat}
    (h : GuardHistory m (fun s a => t.candidate.eval (encoding s a)) history state) :
    JavaScriptCorresponds ext dg names tj t lim ∧
    state ∈ m.safe ∧ ∀ e ∈ history, e.action ∉ m.forbidden := by
  exact ⟨PCSCR.Js.javascript_conditional_refines_reference ext dg hnd tj t htask hb lim hlv hval hexact hint hdg,
         conditional_guard_histories_safe t lim hdecision m hcertificate encoding hcontext hsource h⟩

#print axioms python_runtime_and_guard_histories_safe
#print axioms javascript_runtime_and_guard_histories_safe

end PCSConditionalShield
