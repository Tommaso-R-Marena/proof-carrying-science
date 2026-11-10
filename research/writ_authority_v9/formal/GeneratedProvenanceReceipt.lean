import Provenance
/-! Writ/12 host-owned provenance classification certificate.
Policy SHA-256: 3a6204398f2892ebd12b9d3177453797041873b3fb213ec4ec35677f0ee8cdfd
Root classification and data construction verified by the Python gateway.
Lean does NOT authenticate the underlying bytes, root pins, or implicit flows. -/
namespace WritProvenanceCertificate
-- 0 abstract level=0 sha256=e4ea681766da7c8bfe76231a7ea40284674d8e442a4023f38ad919e966a9abaa
-- 1 patient_record level=2 sha256=5224582a1b908903a912b149c4c23ca1a6c6a4467263a27ff74ca969fe40f3bb
-- 2 replication_report level=1 sha256=b5ede979df04a9785b516b765d2e76eb9e07d04ac74aaae64e6d166b24ceca78
-- 3 tainted_summary level=2 sha256=04e3b064e9a9d5c2ea12d43b01774977137c368c71e025264a9b2ee4b46f2490
def parents : Fin 4 → List (Fin 4) :=
  fun i : Fin 4 =>
    if i.val == 0 then [] else
    if i.val == 1 then [] else
    if i.val == 2 then [] else
    [(0 : Fin 4), (1 : Fin 4)]
def level : Fin 4 → Nat :=
  fun i : Fin 4 =>
    if i.val == 0 then 0 else
    if i.val == 1 then 2 else
    if i.val == 2 then 1 else
    2
example : Writ12.CheckFlow parents level = true := by decide
end WritProvenanceCertificate
