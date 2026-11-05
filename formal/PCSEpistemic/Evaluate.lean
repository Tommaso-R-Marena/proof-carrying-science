import PCSEpistemic.Core

/-!
# Receiving evaluation of finite epistemic packages

The receiver recomputes status bottom-up. Producer-declared statuses are ignored.
-/
set_option autoImplicit false

namespace PCSEpistemic

/-- Evidence that can discharge a claim under exact class match. -/
def evidenceFor (evs : List Evidence) (claimId : Nat) (klass : EvidenceClass) : Option Bool :=
  match evs.find? (fun e => e.claimId == claimId && classCompatible klass e.klass) with
  | some e => some e.pass
  | none => none

/-- Duplicate detection by structural recursion. -/
def hasDup : List Nat → Bool
  | [] => false
  | x :: xs => xs.contains x || hasDup xs

/-- Unique claim ids. -/
def Package.idsUnique (p : Package) : Bool :=
  !(hasDup (p.claims.map (·.id)))

def Package.depsResolved (p : Package) : Bool :=
  let ids := p.claims.map (·.id)
  p.claims.all (fun c => c.dependencies.all (fun d => ids.contains d))

def Package.structurallySound (p : Package) : Bool :=
  p.idsUnique && p.depsResolved && p.claims.all (·.wellFormed)

/-- Dependency statuses force a conservative join for composition. -/
def depJoin (statuses : List Status) : Status :=
  if statuses.any (· == .unsound) then .unsound
  else if statuses.any (· == .refuted) then .refuted
  else if statuses.any (· == .open_) then .open_
  else if statuses.isEmpty || statuses.all (· == .supported) then .supported
  else .open_

/-- Evaluate one claim given already-evaluated dependency statuses. -/
def evalClaim (c : Claim) (depStatuses : List Status) (evs : List Evidence) (o : Observations)
    : Status :=
  if !c.wellFormed then .unsound
  else
    let dj := depJoin depStatuses
    if dj == .unsound then .unsound
    else if anyFalsifier c.falsifiers o then .refuted
    else if dj == .refuted then .open_
    else if dj == .open_ then .open_
    else
      match evidenceFor evs c.id c.klass with
      | some true =>
          if allSupport c.supportRequires o then .supported else .open_
      | some false => .open_
      | none => .open_

def lookupStatus (table : List (Nat × Status)) (id : Nat) : Status :=
  match table.find? (fun p => p.1 == id) with
  | some p => p.2
  | none => .open_

/-- Fuel-bounded topological evaluation; exhaustion marks remainder unsound. -/
def evaluateLoop (remaining : List Claim) (evs : List Evidence) (o : Observations)
    (done : List (Nat × Status)) : Nat → List (Nat × Status)
  | 0 => done ++ remaining.map (fun c => (c.id, Status.unsound))
  | fuel + 1 =>
    let ready := remaining.filter (fun c =>
      c.dependencies.all (fun d => (done.map (·.1)).contains d))
    if ready.isEmpty then
      if remaining.isEmpty then done
      else done ++ remaining.map (fun c => (c.id, Status.unsound))
    else
      let step := ready.map (fun c =>
        let deps := c.dependencies.map (lookupStatus done)
        (c.id, evalClaim c deps evs o))
      let rest := remaining.filter (fun c => !(ready.map (·.id)).contains c.id)
      evaluateLoop rest evs o (done ++ step) fuel

/-- Independent receiving evaluation. -/
def evaluate (p : Package) : List (Nat × Status) :=
  if !p.structurallySound then
    p.claims.map (fun c => (c.id, Status.unsound))
  else
    evaluateLoop p.claims p.evidence p.observations [] (p.claims.length + 1)

def packageSupported (table : List (Nat × Status)) : Bool :=
  !table.isEmpty && table.all (fun p => p.2 == .supported)

def packageRefuted (table : List (Nat × Status)) : Bool :=
  table.any (fun p => p.2 == .refuted)

def packageUnsound (table : List (Nat × Status)) : Bool :=
  table.any (fun p => p.2 == .unsound)

end PCSEpistemic
