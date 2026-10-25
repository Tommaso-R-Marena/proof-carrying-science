import Data
import Wire
namespace Capture
theorem actual : ([[1,0,0,0,0,0],[1,1,0,0,0,0],[1,2,0,1,3,0],[1,3,0,1,255,255]] : List (List Nat)).map (PCSProgressWire.batch PCSProgressData.spec) = [[1,1,0,0,4,0],[1,1,1,0,3,0],[1,1,2,0,2,0],[1,1,3,0,1,0]] := by decide
end Capture
#print axioms Capture.actual
