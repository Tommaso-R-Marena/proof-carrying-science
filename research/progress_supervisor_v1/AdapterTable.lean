import AdapterBridge
set_option autoImplicit false
/-! Bounded differential observation only; this executable grants no authority. -/
def flag (b : Bool) : Nat := if b then 1 else 0

def main : IO Unit := do
  let output ← IO.getStdout
  for s in List.range 7 do
    for a in List.range 8 do
      for b in [false,true] do
        for l in [false,true] do
          for z in [false,true] do
            for p in List.range 3 do
              let r : PCSProgressAdapter.Rows := ⟨b,l,z,p⟩
              let result := match PCSProgressAdapter.step s a r with
                | none => [0,0,0,0,0,0]
                | some (t,q) => [1,t,flag q.isPublic,flag q.loaded,flag q.sanitized,q.published]
              let values := [s,a,flag b,flag l,flag z,p,
                flag (decide (PCSProgressAdapter.Valid s r))] ++ result
              output.putStrLn (String.intercalate "," (values.map toString))
  output.flush
