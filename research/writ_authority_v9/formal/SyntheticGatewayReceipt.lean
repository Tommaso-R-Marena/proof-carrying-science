import Authority
/-! Writ/11 audit-accounting certificate: verified projection only.
Policy SHA-256: ff0e3ce48a4416909f72a86c6dac07201bc9b31f4a4b0f0982fbe507cb2dec84
Audit head: f9b7c3782489165ad84f9b1288488b04509be8059b843a5e5f4180a9bdb04cf1
Admissions: 1; resources: 5
This is not a cryptographic proof of the original source record. -/
namespace WritCertifiedTrace
-- resource 0: budget:sends
-- resource 1: delegate:final_tier
-- resource 2: delegate:second_tier
-- resource 3: delegate:worker_release
-- resource 4: grant:publisher
def initial : Fin 5 → Nat :=
  fun i : Fin 5 =>
    if i.val == 0 then 5 else
    if i.val == 1 then 2 else
    if i.val == 2 then 3 else
    if i.val == 3 then 4 else
    5

def debit0 : Fin 5 → Nat :=
  fun i : Fin 5 =>
    if i.val == 0 then 1 else
    if i.val == 1 then 1 else
    if i.val == 2 then 1 else
    if i.val == 3 then 1 else
    1

def trace : List (Fin 5 → Nat) := [
debit0]
def expected : Fin 5 → Nat :=
  fun i : Fin 5 =>
    if i.val == 0 then 4 else
    if i.val == 1 then 1 else
    if i.val == 2 then 2 else
    if i.val == 3 then 3 else
    4

-- expected budget:sends = 4
example : (Writ9.CheckWeighted initial trace).map
    (fun f => f (0 : Fin 5)) = some 4 := by decide
-- expected delegate:final_tier = 1
example : (Writ9.CheckWeighted initial trace).map
    (fun f => f (1 : Fin 5)) = some 1 := by decide
-- expected delegate:second_tier = 2
example : (Writ9.CheckWeighted initial trace).map
    (fun f => f (2 : Fin 5)) = some 2 := by decide
-- expected delegate:worker_release = 3
example : (Writ9.CheckWeighted initial trace).map
    (fun f => f (3 : Fin 5)) = some 3 := by decide
-- expected grant:publisher = 4
example : (Writ9.CheckWeighted initial trace).map
    (fun f => f (4 : Fin 5)) = some 4 := by decide
end WritCertifiedTrace
