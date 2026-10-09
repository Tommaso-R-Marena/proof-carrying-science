/-!
# Kernel-efficient decidable equality on `ByteArray`

The core instance `ByteArray.instDecidableEq` goes through `Array`'s decidable equality,
whose index loop the kernel evaluates very slowly (a single comparison of two 1.7 KB
arrays did not finish within 150 s).  `byteArrayDecEqList` decides the same proposition by
comparing the underlying byte lists; since `Decidable` is a subsingleton the two instances
are equal (`byteArray_instDecidableEq_eq`), so rewriting with that equation changes no
statement, only the evaluation strategy.
-/

set_option autoImplicit false

namespace PCS.V2.KernelEq

theorem byteArray_eq_iff_toList (a b : ByteArray) : a.data.toList = b.data.toList ↔ a = b := by
  constructor
  · intro h; cases a; cases b; simp_all [Array.toList_inj]
  · intro h; subst h; rfl

/-- Decide `ByteArray` equality by comparing byte lists. -/
def byteArrayDecEqList : DecidableEq ByteArray := fun a b =>
  decidable_of_iff _ (byteArray_eq_iff_toList a b)

theorem byteArray_instDecidableEq_eq : ByteArray.instDecidableEq = byteArrayDecEqList := by
  funext a b; exact Subsingleton.elim _ _

end PCS.V2.KernelEq
