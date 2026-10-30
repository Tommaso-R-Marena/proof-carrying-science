import RowWire
namespace CaptureRows
theorem actual : ([[80,67,83,82,1,0,0,1,0,1,0,1,1,0,1,0],[80,67,83,82,1,1,1,1,0,1,0,3,1,1,1,0],[80,67,83,82,1,3,3,1,1,1,0,4,1,1,1,1]] : List (List Nat)).map PCSProgressRows.batch = [[2,1],[2,1],[2,1]] := by decide
end CaptureRows
#print axioms CaptureRows.actual
