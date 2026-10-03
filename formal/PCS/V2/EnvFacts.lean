import PCS.V2.Replay
import PCS.V2.TextSplit

/-!
# Verified environment facts (`capture_environment_v06`, strict high-assurance subset)

The environment stage proves *declared = captured*; what the capture *means* was the named
contract `CaptureSound`.  This module removes that contract for the highest-value,
deterministic part of the capture.  For every capture that the Lean authority accepts,
`envFactsB_sound` proves `EnvFacts`:

* **sources** — every `sources` record (`artifact_id`, `path`, `sha256`, `size`) is a
  committed, digest-checked inventory item with exactly that path, digest and size;
* **exact `==` pins** — every Python dependency record from a `requirements*` file with
  `exact_pin = true` has a strict exact version (no wildcard, range or comma), and the
  committed file contains a line that *begins a logical requirement line* (the previous
  line is not a `\` continuation) and spells `name == version`;
* **SHA-256 hash pins** — if such a record also has `hash_pinned = true`, the logical
  requirement line (with its `\` continuations) contains `--hash=sha256:` followed by 64
  lower-case hex digits;
* **interpreter versions** — every interpreter constraint read from `.python-version` or
  `runtime.txt` is a version token `N.N` / `N.N.N` occurring in that committed file;
* **digest-pinned container bases** — every container stage with `digest_pinned = true`
  has a reference `name@sha256:<64 lower-case hex>` without `$`, and the committed
  Dockerfile/Containerfile has a `FROM [--platform=…] <reference>` line.

Text is decoded as UTF-8 and split at LF (one trailing CR per line allowed).  Files that
contain any other Python line-break or non-ASCII whitespace character are rejected when a
fact must be read from them (fail-closed), so the line structure is unambiguous.

Everything else in the capture (hermeticity summary, replay plan, other ecosystems,
`unresolved`) remains covered only by the explicit `CaptureSound` assumption.
-/

namespace PCS.V2.EnvFacts

open PCS.V2.Json PCS.V2.Hex PCS.V2.Package PCS.V2.Replay PCS.V2.CertificateModel PCS.V2.TextSplit

/-! ## Text and lines -/

/-- Python `str.isspace`/`splitlines` characters other than `\t`, `\n`, `\r` and space. -/
def badWs (c : Char) : Bool :=
  c = '\x0b' || c = '\x0c' || c = '\x1c' || c = '\x1d' || c = '\x1e' || c = '\x1f' ||
  c = '\x85' || c = '\xa0' || c = '\u1680' || c = '\u2028' || c = '\u2029' || c = '\u202f' ||
  c = '\u205f' || c = '\u3000' || ('\u2000' ≤ c && c ≤ '\u200a')

def dropCR (l : List Char) : List Char := if l.getLast? = some '\r' then l.dropLast else l

/-- The committed bytes `b` are safe UTF-8 text with lines `ls`. -/
def TextLines (b : ByteArray) (ls : List (List Char)) : Prop :=
  ∃ s raw, String.fromUTF8? b = some s ∧ (∀ c ∈ s.toList, badWs c = false) ∧
    SplitBy '\n' s.toList raw ∧ (∀ l ∈ raw, '\r' ∉ l.dropLast) ∧ ls = raw.map dropCR

def textLines (b : ByteArray) : Option (List (List Char)) :=
  match String.fromUTF8? b with
  | some s =>
    if s.toList.all (fun c => badWs c == false) &&
        (splitAt '\n' s.toList).all (fun l => !(l.dropLast.contains '\r'))
    then some ((splitAt '\n' s.toList).map dropCR) else none
  | none => none

/-- The committed inventory item at source path `sp` is safe text with lines `ls`. -/
def FileLines (inv : List InventoryItem) (sp : String) (ls : List (List Char)) : Prop :=
  ∃ it ∈ inv, it.path = sp ∧ TextLines it.bytes ls

def fileLines (inv : List InventoryItem) (sp : String) : Option (List (List Char)) :=
  (inv.find? (·.path == sp)).bind (fun it => textLines it.bytes)

/-! ## Lexical predicates -/

def wsB (c : Char) : Bool := c = ' ' || c = '\t'
def AllWs (w : List Char) : Prop := ∀ c ∈ w, wsB c = true

def isLowerHex (c : Char) : Bool := ('0' ≤ c && c ≤ '9') || ('a' ≤ c && c ≤ 'f')
def isDigitC (c : Char) : Bool := '0' ≤ c && c ≤ '9'
def isAlnumC (c : Char) : Bool := isDigitC c || ('a' ≤ c && c ≤ 'z') || ('A' ≤ c && c ≤ 'Z')

/-- A strict exact version: non-empty, only `[A-Za-z0-9._+!-]` (no `*`, `,`, `<`, `=`, …). -/
def versionChar (c : Char) : Bool := isAlnumC c || c = '.' || c = '_' || c = '+' || c = '!' || c = '-'
def StrictVersion (v : List Char) : Prop := v ≠ [] ∧ ∀ c ∈ v, versionChar c = true

/-- The line ends a `\` continuation: after removing trailing blanks it ends with `\`. -/
def continuesB (l : List Char) : Bool :=
  match l.reverse.dropWhile wsB with
  | '\\' :: _ => true
  | _ => false

/-- A requirement line `ws* name ws* == ws* version` followed by end, blank, `;` or `\`. -/
def PinLine (nm v l : List Char) : Prop :=
  ∃ w1 w2 w3 rest, AllWs w1 ∧ AllWs w2 ∧ AllWs w3 ∧
    l = w1 ++ nm ++ w2 ++ ['=', '='] ++ w3 ++ v ++ rest ∧
    (rest = [] ∨ ∃ c r, rest = c :: r ∧ (c = ' ' ∨ c = '\t' ∨ c = ';' ∨ c = '\\'))

def hashPrefix : List Char := "--hash=sha256:".toList

/-- The line contains `--hash=sha256:` followed by 64 lower-case hex digits. -/
def HasHash (y : List Char) : Prop :=
  ∃ a b, y = a ++ hashPrefix ++ b ∧ 64 ≤ b.length ∧ ∀ c ∈ b.take 64, isLowerHex c = true

/-- `name == version` begins a logical requirement line of `ls`; if `hashed`, that logical
    line (the line and its `\` continuations) carries a SHA-256 hash pin. -/
def PinnedIn (ls : List (List Char)) (nm v : List Char) (hashed : Bool) : Prop :=
  ∃ pre l post, ls = pre ++ l :: post ∧ (∀ p, pre.getLast? = some p → continuesB p = false) ∧
    PinLine nm v l ∧
    (hashed = true → ∃ blk rest, post = blk ++ rest ∧
      (∀ x ∈ (l :: blk).dropLast, continuesB x = true) ∧ ∃ y ∈ l :: blk, HasHash y)

/-- `N.N` or `N.N.N` (ASCII digits). -/
def VersionToken (v : List Char) : Prop :=
  ∃ parts, SplitBy '.' v parts ∧ (parts.length = 2 ∨ parts.length = 3) ∧
    ∀ p ∈ parts, p ≠ [] ∧ ∀ c ∈ p, isDigitC c = true

def lastSeg (sp : String) : List Char := ((splitAt '/' sp.toList).getLast?).getD []

def isVersionFile (sp : String) : Bool :=
  lastSeg sp == ".python-version".toList || lastSeg sp == "runtime.txt".toList

def digestPrefix : List Char := "@sha256:".toList

/-- `name@sha256:<64 lower-case hex>` with no `$` (no build-arg substitution). -/
def DigestRef (ref : List Char) : Prop :=
  ∃ name hex, ref = name ++ digestPrefix ++ hex ∧ hex.length = 64 ∧
    (∀ c ∈ hex, isLowerHex c = true) ∧ '$' ∉ ref

def tokens (l : List Char) : List (List Char) :=
  (splitAt ' ' (l.map fun c => if c = '\t' then ' ' else c)).filter (fun t => !t.isEmpty)

/-- `FROM <ref> …` or `FROM --platform=… <ref> …` (keyword case-insensitive). -/
def FromLine (ref l : List Char) : Prop :=
  ∃ t0 rest, tokens l = t0 :: rest ∧ t0.map Char.toLower = "from".toList ∧
    ((∃ r, rest = ref :: r) ∨ (∃ p r, rest = p :: ref :: r ∧ "--platform=".toList.isPrefixOf p = true))

/-! ## The `EnvFacts` relation -/

def SourceBacked (inv : List InventoryItem) (s : JVal) : Prop :=
  ∃ sm a p h n, s = .obj sm ∧ strField sm "artifact_id" = some a ∧ strField sm "path" = some p ∧
    strField sm "sha256" = some h ∧ field sm "size" = some (.num n) ∧
    ∃ it ∈ inv, it.artifactId = a ∧ it.path = p ∧ hexChars it.sha256 = h.toList ∧
      (it.bytes.size : Int) = n

def isReqKind (dm : List (String × JVal)) : Bool :=
  strField dm "source_kind" == some "requirements" || strField dm "source_kind" == some "requirements_lock"

def DepBacked (inv : List InventoryItem) (dm : List (String × JVal)) : Prop :=
  isReqKind dm = true → boolField dm "exact_pin" = some true →
  ∃ nm v sp ls, strField dm "name" = some nm ∧ strField dm "version" = some v ∧
    strField dm "source_path" = some sp ∧ StrictVersion v.toList ∧ FileLines inv sp ls ∧
    PinnedIn ls nm.toList v.toList (boolField dm "hash_pinned" == some true)

def IcBacked (inv : List InventoryItem) (im : List (String × JVal)) : Prop :=
  ∀ sp, strField im "source_path" = some sp → isVersionFile sp = true →
    ∃ val ls, strField im "value" = some val ∧ VersionToken val.toList ∧ FileLines inv sp ls ∧
      ∃ l ∈ ls, ∃ a b, l = a ++ val.toList ++ b

def ContainerBacked (inv : List InventoryItem) (c : JVal) : Prop :=
  ∃ cm sp stages, c = .obj cm ∧ strField cm "source_path" = some sp ∧
    field cm "stages" = some (.arr stages) ∧
    ∀ st ∈ stages, ∃ sm, st = .obj sm ∧ (boolField sm "digest_pinned" = some true →
      ∃ ref ls, strField sm "reference" = some ref ∧ DigestRef ref.toList ∧ FileLines inv sp ls ∧
        ∃ l ∈ ls, FromLine ref.toList l)

/-- **`EnvFacts`**: the verified meaning of an accepted environment capture `v` over the
    committed, digest-checked inventory `inv`. -/
def EnvFacts (inv : List InventoryItem) (v : JVal) : Prop :=
  ∃ ms ss py ds ics cs, v = .obj ms ∧ field ms "sources" = some (.arr ss) ∧
    field ms "python" = some (.obj py) ∧ field py "dependencies" = some (.arr ds) ∧
    field py "interpreter_constraints" = some (.arr ics) ∧ field ms "containers" = some (.arr cs) ∧
    (∀ s ∈ ss, SourceBacked inv s) ∧ (∀ d ∈ ds, ∃ dm, d = .obj dm ∧ DepBacked inv dm) ∧
    (∀ i ∈ ics, ∃ im, i = .obj im ∧ IcBacked inv im) ∧ (∀ c ∈ cs, ContainerBacked inv c)

/-! ## Executable checker -/

def dropPrefix (p l : List Char) : Option (List Char) :=
  if p.isPrefixOf l then some (l.drop p.length) else none

def endOK : List Char → Bool
  | [] => true
  | c :: _ => c = ' ' || c = '\t' || c = ';' || c = '\\'

def pinLineB (nm v l : List Char) : Bool :=
  match dropPrefix nm (l.dropWhile wsB) with
  | some r2 =>
    match dropPrefix ['=', '='] (r2.dropWhile wsB) with
    | some r3 =>
      match dropPrefix v (r3.dropWhile wsB) with
      | some rest => endOK rest
      | none => false
    | none => false
  | none => false

/-- Some occurrence of `pat` in `l` is followed by a suffix satisfying `P`. -/
def infixWith (pat : List Char) (P : List Char → Bool) : List Char → Bool
  | [] => match dropPrefix pat [] with
    | some b => P b
    | none => false
  | c :: r => (match dropPrefix pat (c :: r) with
      | some b => P b
      | none => false) || infixWith pat P r

def hashTail (b : List Char) : Bool := decide (64 ≤ b.length) && (b.take 64).all isLowerHex

def hasHashB (y : List Char) : Bool := infixWith hashPrefix hashTail y

def hashBlockB : List (List Char) → Bool
  | [] => false
  | y :: ys => hasHashB y || (continuesB y && hashBlockB ys)

def findPin (nm v : List Char) (hashed : Bool) : Option (List Char) → List (List Char) → Bool
  | _, [] => false
  | prev, l :: post =>
    ((match prev with
      | some p => !continuesB p
      | none => true) && pinLineB nm v l && (!hashed || hashBlockB (l :: post))) ||
    findPin nm v hashed (some l) post

def strictVersionB (v : List Char) : Bool := !v.isEmpty && v.all versionChar

def versionTokenB (v : List Char) : Bool :=
  let parts := splitAt '.' v
  (parts.length == 2 || parts.length == 3) && parts.all (fun p => !p.isEmpty && p.all isDigitC)

def digestRefB (ref : List Char) : Bool :=
  let k := ref.length - 72
  decide (72 ≤ ref.length) && (ref.drop k).take 8 == digestPrefix &&
    (ref.drop (k + 8)).all isLowerHex && !ref.contains '$'

def fromLineB (ref l : List Char) : Bool :=
  match tokens l with
  | t0 :: rest =>
    t0.map Char.toLower == "from".toList &&
    (match rest with
     | r :: rs => r == ref || ("--platform=".toList.isPrefixOf r && rs.head? == some ref)
     | [] => false)
  | [] => false

def sourceB (inv : List InventoryItem) : JVal → Bool
  | .obj sm =>
    match strField sm "artifact_id", strField sm "path", strField sm "sha256", field sm "size" with
    | some a, some p, some h, some (.num n) =>
      inv.any fun it => it.artifactId == a && it.path == p && hexChars it.sha256 == h.toList &&
        (it.bytes.size : Int) == n
    | _, _, _, _ => false
  | _ => false

def depB (inv : List InventoryItem) : JVal → Bool
  | .obj dm =>
    if isReqKind dm && boolField dm "exact_pin" == some true then
      match strField dm "name", strField dm "version", strField dm "source_path" with
      | some nm, some v, some sp =>
        strictVersionB v.toList &&
        (match fileLines inv sp with
         | some ls => findPin nm.toList v.toList (boolField dm "hash_pinned" == some true) none ls
         | none => false)
      | _, _, _ => false
    else true
  | _ => false

def icB (inv : List InventoryItem) : JVal → Bool
  | .obj im =>
    match strField im "source_path" with
    | some sp =>
      if isVersionFile sp then
        match strField im "value" with
        | some val =>
          versionTokenB val.toList &&
          (match fileLines inv sp with
           | some ls => ls.any (infixWith val.toList (fun _ => true))
           | none => false)
        | none => false
      else true
    | none => true
  | _ => false

def stageB (inv : List InventoryItem) (sp : String) : JVal → Bool
  | .obj sm =>
    if boolField sm "digest_pinned" == some true then
      match strField sm "reference" with
      | some ref =>
        digestRefB ref.toList &&
        (match fileLines inv sp with
         | some ls => ls.any (fromLineB ref.toList)
         | none => false)
      | none => false
    else true
  | _ => false

def containerB (inv : List InventoryItem) : JVal → Bool
  | .obj cm =>
    match strField cm "source_path", field cm "stages" with
    | some sp, some (.arr stages) => stages.all (stageB inv sp)
    | _, _ => false
  | _ => false

/-- The Lean environment-facts decision. -/
def envFactsB (inv : List InventoryItem) : JVal → Bool
  | .obj ms =>
    match field ms "sources", field ms "python", field ms "containers" with
    | some (.arr ss), some (.obj py), some (.arr cs) =>
      match field py "dependencies", field py "interpreter_constraints" with
      | some (.arr ds), some (.arr ics) =>
        ss.all (sourceB inv) && ds.all (depB inv) && ics.all (icB inv) && cs.all (containerB inv)
      | _, _ => false
    | _, _, _ => false
  | _ => false

/-! ## Soundness -/

theorem textLines_sound {b : ByteArray} {ls : List (List Char)} (h : textLines b = some ls) :
    TextLines b ls := by
  unfold textLines at h
  split at h
  · rename_i s hs
    split at h
    · rename_i hc
      cases h
      simp only [Bool.and_eq_true, List.all_eq_true, beq_iff_eq, Bool.not_eq_true'] at hc
      refine ⟨s, splitAt '\n' s.toList, hs, hc.1, splitAt_sound _ _, ?_, rfl⟩
      intro l hl
      have := hc.2 l hl
      simpa using this
    · cases h
  · cases h

theorem fileLines_sound {inv : List InventoryItem} {sp : String} {ls : List (List Char)}
    (h : fileLines inv sp = some ls) : FileLines inv sp ls := by
  unfold fileLines at h
  cases hf : inv.find? (·.path == sp) with
  | none => rw [hf] at h; cases h
  | some it =>
    rw [hf] at h
    have hm := List.mem_of_find?_eq_some hf
    have hp := List.find?_some hf
    simp only [beq_iff_eq] at hp
    exact ⟨it, hm, hp, textLines_sound h⟩

theorem dropPrefix_sound {p l r : List Char} (h : dropPrefix p l = some r) : l = p ++ r := by
  unfold dropPrefix at h
  split at h
  · rename_i hp
    cases h
    obtain ⟨t, ht⟩ := List.isPrefixOf_iff_prefix.1 hp
    subst ht
    simp
  · cases h

theorem takeWhile_allWs : ∀ (l : List Char), AllWs (l.takeWhile wsB)
  | [] => by simp [AllWs]
  | c :: r => by
    cases hc : wsB c with
    | false => simp [hc, AllWs]
    | true =>
      simp only [List.takeWhile_cons, hc, if_true]
      intro x hx
      rcases List.mem_cons.1 hx with hx | hx
      · rw [hx]; exact hc
      · exact takeWhile_allWs r x hx

theorem dropWhile_split (l : List Char) :
    l = l.takeWhile wsB ++ l.dropWhile wsB ∧ AllWs (l.takeWhile wsB) :=
  ⟨(List.takeWhile_append_dropWhile).symm, takeWhile_allWs l⟩

theorem pinLineB_sound {nm v l : List Char} (h : pinLineB nm v l = true) : PinLine nm v l := by
  unfold pinLineB at h
  split at h
  · rename_i r2 h2
    split at h
    · rename_i r3 h3
      split at h
      · rename_i rest h4
        obtain ⟨e1, w1⟩ := dropWhile_split l
        obtain ⟨e2, w2⟩ := dropWhile_split r2
        obtain ⟨e3, w3⟩ := dropWhile_split r3
        have d2 := dropPrefix_sound h2
        have d3 := dropPrefix_sound h3
        have d4 := dropPrefix_sound h4
        refine ⟨_, _, _, rest, w1, w2, w3, ?_, ?_⟩
        · rw [d2] at e1; rw [e2] at e1; rw [d3] at e1; rw [e3] at e1; rw [d4] at e1
          exact e1.trans (by simp)
        · cases rest with
          | nil => exact Or.inl rfl
          | cons c r =>
            simp only [endOK, Bool.or_eq_true, decide_eq_true_eq] at h
            refine Or.inr ⟨c, r, rfl, ?_⟩
            rcases h with ((h | h) | h) | h
            · exact Or.inl h
            · exact Or.inr (Or.inl h)
            · exact Or.inr (Or.inr (Or.inl h))
            · exact Or.inr (Or.inr (Or.inr h))
      · cases h
    · cases h
  · cases h

theorem infixWith_sound {pat : List Char} {P : List Char → Bool} :
    ∀ {l : List Char}, infixWith pat P l = true → ∃ a b, l = a ++ pat ++ b ∧ P b = true
  | [], h => by
    simp only [infixWith] at h
    split at h
    · rename_i b hb
      exact ⟨[], b, by simpa using dropPrefix_sound hb, h⟩
    · cases h
  | c :: r, h => by
    simp only [infixWith, Bool.or_eq_true] at h
    rcases h with h | h
    · split at h
      · rename_i b hb
        exact ⟨[], b, by simpa using dropPrefix_sound hb, h⟩
      · cases h
    · obtain ⟨a, b, hab, hb⟩ := infixWith_sound h
      exact ⟨c :: a, b, by rw [hab]; simp, hb⟩

theorem hasHashB_sound {y : List Char} (h : hasHashB y = true) : HasHash y := by
  obtain ⟨a, b, hab, hb⟩ := infixWith_sound h
  simp only [hashTail, Bool.and_eq_true, decide_eq_true_eq, List.all_eq_true] at hb
  exact ⟨a, b, hab, hb.1, hb.2⟩

theorem hashBlockB_sound :
    ∀ {l : List Char} {post : List (List Char)}, hashBlockB (l :: post) = true →
      ∃ blk rest, post = blk ++ rest ∧ (∀ x ∈ (l :: blk).dropLast, continuesB x = true) ∧
        ∃ y ∈ l :: blk, HasHash y
  | l, post, h => by
    simp only [hashBlockB, Bool.or_eq_true, Bool.and_eq_true] at h
    rcases h with h | ⟨hc, h⟩
    · exact ⟨[], post, rfl, by simp, l, by simp, hasHashB_sound h⟩
    · cases post with
      | nil => simp [hashBlockB] at h
      | cons m post' =>
        obtain ⟨blk, rest, hp, hcont, y, hy, hh⟩ := hashBlockB_sound h
        refine ⟨m :: blk, rest, by rw [hp]; rfl, ?_, y, ?_, hh⟩
        · intro x hx
          rw [List.dropLast_cons_of_ne_nil (by simp)] at hx
          rcases List.mem_cons.1 hx with hx | hx
          · rw [hx]; exact hc
          · exact hcont x hx
        · exact List.mem_cons_of_mem _ hy

theorem findPin_sound {nm v : List Char} {hashed : Bool} :
    ∀ (pre ls : List (List Char)), findPin nm v hashed pre.getLast? ls = true →
      PinnedIn (pre ++ ls) nm v hashed
  | _, [], h => by simp [findPin] at h
  | pre, l :: post, h => by
    simp only [findPin, Bool.or_eq_true, Bool.and_eq_true] at h
    rcases h with ⟨⟨hprev, hpin⟩, hhash⟩ | h
    · refine ⟨pre, l, post, rfl, ?_, pinLineB_sound hpin, ?_⟩
      · intro p hp
        rw [hp] at hprev
        simpa using hprev
      · intro hh
        rw [hh] at hhash
        exact hashBlockB_sound (by simpa using hhash)
    · have hlast : (pre ++ [l]).getLast? = some l := by simp
      rw [← hlast] at h
      have := findPin_sound (pre ++ [l]) post h
      simpa using this

theorem strictVersionB_sound {v : List Char} (h : strictVersionB v = true) : StrictVersion v := by
  simp only [strictVersionB, Bool.and_eq_true, Bool.not_eq_true', List.isEmpty_eq_false_iff,
    List.all_eq_true] at h
  exact ⟨h.1, h.2⟩

theorem versionTokenB_sound {v : List Char} (h : versionTokenB v = true) : VersionToken v := by
  simp only [versionTokenB, Bool.and_eq_true, Bool.or_eq_true, beq_iff_eq, List.all_eq_true,
    Bool.not_eq_true', List.isEmpty_eq_false_iff] at h
  exact ⟨_, splitAt_sound _ _, h.1, fun p hp => h.2 p hp⟩

theorem digestRefB_sound {ref : List Char} (h : digestRefB ref = true) : DigestRef ref := by
  simp only [digestRefB, Bool.and_eq_true, decide_eq_true_eq, beq_iff_eq, List.all_eq_true,
    Bool.not_eq_true'] at h
  obtain ⟨⟨⟨hlen, hpre⟩, hhex⟩, hdollar⟩ := h
  refine ⟨ref.take (ref.length - 72), ref.drop (ref.length - 72 + 8), ?_, ?_, hhex, ?_⟩
  · have e : ref.drop (ref.length - 72) = digestPrefix ++ ref.drop (ref.length - 72 + 8) := by
      rw [← hpre, ← List.drop_drop, List.take_append_drop]
    calc ref = ref.take (ref.length - 72) ++ ref.drop (ref.length - 72) :=
          (List.take_append_drop _ _).symm
      _ = _ := by rw [e, List.append_assoc]
  · simp only [List.length_drop]; omega
  · intro hm
    have : ref.contains '$' = true := by simpa using hm
    rw [this] at hdollar; cases hdollar

theorem fromLineB_sound {ref l : List Char} (h : fromLineB ref l = true) : FromLine ref l := by
  unfold fromLineB at h
  split at h
  · rename_i t0 rest ht
    simp only [Bool.and_eq_true, beq_iff_eq] at h
    refine ⟨t0, rest, ht, h.1, ?_⟩
    obtain ⟨_, h2⟩ := h
    split at h2
    · rename_i r rs
      simp only [Bool.or_eq_true, beq_iff_eq, Bool.and_eq_true] at h2
      rcases h2 with h2 | ⟨hp, hh⟩
      · exact Or.inl ⟨rs, by rw [h2]⟩
      · cases rs with
        | nil => simp at hh
        | cons r' rs' =>
          simp only [List.head?_cons, Option.some.injEq] at hh
          exact Or.inr ⟨r, rs', by rw [hh], hp⟩
    · cases h2
  · cases h

theorem sourceB_sound {inv : List InventoryItem} {s : JVal} (h : sourceB inv s = true) :
    SourceBacked inv s := by
  cases s with
  | obj sm =>
    simp only [sourceB] at h
    split at h
    · rename_i a p hh n ha hp hsh hn
      obtain ⟨it, hit, hok⟩ := List.any_eq_true.1 h
      simp only [Bool.and_eq_true, beq_iff_eq] at hok
      exact ⟨sm, a, p, hh, n, rfl, ha, hp, hsh, hn, it, hit, hok.1.1.1, hok.1.1.2, hok.1.2, hok.2⟩
    · cases h
  | _ => simp [sourceB] at h

theorem depB_sound {inv : List InventoryItem} {d : JVal} (h : depB inv d = true) :
    ∃ dm, d = .obj dm ∧ DepBacked inv dm := by
  cases d with
  | obj dm =>
    refine ⟨dm, rfl, fun hk he => ?_⟩
    simp only [depB, hk, he, beq_self_eq_true, Bool.and_self, if_true] at h
    split at h
    · rename_i nm v sp hn hv hs
      simp only [Bool.and_eq_true] at h
      obtain ⟨hsv, hf⟩ := h
      split at hf
      · rename_i ls hls
        have := findPin_sound [] ls hf
        exact ⟨nm, v, sp, ls, hn, hv, hs, strictVersionB_sound hsv, fileLines_sound hls,
          by simpa using this⟩
      · cases hf
    · cases h
  | _ => simp [depB] at h

theorem icB_sound {inv : List InventoryItem} {i : JVal} (h : icB inv i = true) :
    ∃ im, i = .obj im ∧ IcBacked inv im := by
  cases i with
  | obj im =>
    refine ⟨im, rfl, fun sp hsp hvf => ?_⟩
    simp only [icB, hsp, hvf, if_true] at h
    split at h
    · rename_i val hval
      simp only [Bool.and_eq_true] at h
      obtain ⟨hvt, hf⟩ := h
      split at hf
      · rename_i ls hls
        obtain ⟨l, hl, hinf⟩ := List.any_eq_true.1 hf
        obtain ⟨a, b, hab, _⟩ := infixWith_sound hinf
        exact ⟨val, ls, hval, versionTokenB_sound hvt, fileLines_sound hls, l, hl, a, b, hab⟩
      · cases hf
    · cases h
  | _ => simp [icB] at h

theorem containerB_sound {inv : List InventoryItem} {c : JVal} (h : containerB inv c = true) :
    ContainerBacked inv c := by
  cases c with
  | obj cm =>
    simp only [containerB] at h
    split at h
    · rename_i sp stages hsp hst
      refine ⟨cm, sp, stages, rfl, hsp, hst, fun st hmem => ?_⟩
      have hs := List.all_eq_true.1 h st hmem
      cases st with
      | obj sm =>
        refine ⟨sm, rfl, fun hd => ?_⟩
        simp only [stageB, hd, beq_self_eq_true, if_true] at hs
        split at hs
        · rename_i ref href
          simp only [Bool.and_eq_true] at hs
          obtain ⟨hdr, hf⟩ := hs
          split at hf
          · rename_i ls hls
            obtain ⟨l, hl, hfl⟩ := List.any_eq_true.1 hf
            exact ⟨ref, ls, href, digestRefB_sound hdr, fileLines_sound hls, l, hl,
              fromLineB_sound hfl⟩
          · cases hf
        · cases hs
      | _ => simp [stageB] at hs
    · cases h
  | _ => simp [containerB] at h

/-- **Soundness of the Lean environment-facts check.** -/
theorem envFactsB_sound {inv : List InventoryItem} {v : JVal} (h : envFactsB inv v = true) :
    EnvFacts inv v := by
  cases v with
  | obj ms =>
    simp only [envFactsB] at h
    split at h
    · rename_i ss py cs hss hpy hcs
      split at h
      · rename_i ds ics hds hics
        simp only [Bool.and_eq_true, List.all_eq_true] at h
        obtain ⟨⟨⟨h1, h2⟩, h3⟩, h4⟩ := h
        exact ⟨ms, ss, py, ds, ics, cs, rfl, hss, hpy, hds, hics, hcs,
          fun s hs => sourceB_sound (h1 s hs), fun d hd => depB_sound (h2 d hd),
          fun i hi => icB_sound (h3 i hi), fun c hc => containerB_sound (h4 c hc)⟩
      · cases h
    · cases h
  | _ => simp [envFactsB] at h

end PCS.V2.EnvFacts
