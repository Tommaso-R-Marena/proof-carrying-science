import Lean

/-!
# Source binding: exact source lines as kernel-visible literals

`source_lines% "relative/path"` reads the file (relative to the current Lean source file, like
Lean's `include_str`) at elaboration time and produces the literal list of its lines, obtained
by splitting the exact file contents at every `'\n'`.  `String.intercalate "\n"` of the list is
the exact file content, so a theorem comparing a rendered extraction artifact with a slice of
this list binds that artifact to the exact uploaded source bytes.  (The kernel cannot afford
to decode a 7 kB UTF-8 literal character by character; comparing per-line literals is cheap.)
-/

namespace PCSRuntimeRefinement

open Lean Elab Term in
elab "source_lines% " path:str : term => do
  let some fn := (← getFileName) |> some | throwError "no file"
  let dir := (System.FilePath.mk fn).parent.getD "."
  let txt ← IO.FS.readFile (dir / path.getString)
  return toExpr (txt.splitOn "\n")

end PCSRuntimeRefinement
