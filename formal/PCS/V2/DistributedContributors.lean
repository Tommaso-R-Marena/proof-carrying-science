import PCS.V2.DomainAdapter
import PCS.V2.ClaimGraphMemo

/-!
# Distributed, untrusted contributors cannot forge PCS assurance

A finite population of contributors (humans, AI systems, adversaries, stochastic or
adaptive strategies, colluding coalitions) submits obligation-graph nodes — claims,
decompositions, repairs, leaf evidence, checker inputs, adversarial cases — in an
arbitrary interleaving.  **No contributor is assumed honest or competent.**

## Protocol

The shared store is a list of committed entries `(author, node)`.  A submission becomes
authoritative (is committed) only if the deterministic admission check `admitSubmission` passes:

* the node id is not already committed (**no overwrite**: an accepted commitment can never
  be replaced, by its author or anyone else);
* a **leaf** is admitted only if the trusted validator accepts its obligation for the
  leaf's *own* claim (`V.leaf ob claim`); unverified material can never discharge a leaf;
* a **derivation** is admitted only if every child id is already committed and the trusted
  rule check accepts the parent claim from the committed children's claims (so the
  committed graph is built bottom-up and is acyclic by construction);
* an **unsupported** node is never admitted.

The root id and the root claim `goal` are protocol parameters fixed by the deterministic
claim binding (for PCS: the compiled, signed certificate claim); contributors cannot choose
them.  `protocolAccepts` holds iff the committed node with the root id carries exactly
`goal`.

## Results

* `run_invariant` — under `CheckerSound V Sem`, **every committed node's claim holds**, for
  every submission list (hence for every population, strategy and interleaving).
* `accepted_contributions_cannot_forge_assurance` — for every contributor population,
  every (adaptive, stochastic, colluding) strategy profile and every schedule, protocol
  acceptance implies `Sem goal`.  No honesty assumption appears.
* Protocol facts: `unverified_leaf_rejected`, `no_overwrite`, `committed_persistent`,
  `committed_provenance` (nothing is invented and authorship is preserved),
  `committed_ids_nodup`, `committed_children_earlier` (acyclic by construction),
  `accepted_root_claim_fixed`, `accepted_conclusion_order_independent`,
  `coalition_is_submission_list` (collusion = an arbitrary joint submission list, already
  covered).
* Honest limitation (proved, not hidden): an adversary *can* block acceptance by squatting
  an id first (`squatting_blocks_liveness`) — ordering can change **whether** the root is
  accepted, never **what** an accepted root means.
* `pcs_distributed_domain_sound` — the PCS instance: contributions checked against an
  accepted PCS package with the adapter's induced checker yield the domain proposition.
-/

set_option autoImplicit false

namespace PCS.V2.DistributedContributors

open PCS.V2.ClaimGraph

variable {Cid L C : Type}

/-- A submission: who proposes which node. -/
structure Submission (Cid L C : Type) where
  author : Cid
  node : Node L C

/-- The committed store. -/
abbrev Store (Cid L C : Type) := List (Submission Cid L C)

/-- Claims of committed children; `none` if one is not committed. -/
def childClaims (st : Store Cid L C) : List String → Option (List C)
  | [] => some []
  | i :: is =>
    match st.find? (fun e => e.node.id == i), childClaims st is with
    | some e, some cs => some (e.node.claim :: cs)
    | _, _ => none

/-- Local admission validation of a node against the current store. -/
def admissible (V : Checker L C) (st : Store Cid L C) (n : Node L C) : Bool :=
  match n.kind with
  | .leaf ob => V.leaf ob n.claim
  | .derive r chs =>
    match childClaims st chs with
    | some cs => V.rule r n.claim cs
    | none => false
  | .unsupported _ => false

/-- **The admission step**: commit iff the id is fresh and the node is admissible. -/
def admitSubmission (V : Checker L C) (st : Store Cid L C) (s : Submission Cid L C) : Store Cid L C :=
  if st.any (fun e => e.node.id == s.node.id) then st
  else if admissible V st s.node then st ++ [s] else st

/-- Process a list of submissions in order. -/
def run (V : Checker L C) (subs : List (Submission Cid L C)) : Store Cid L C :=
  subs.foldl (admitSubmission V) []

/-- Final acceptance: the committed root node carries exactly the bound goal claim. -/
def protocolAccepts [DecidableEq C] (V : Checker L C) (goal : C) (root : String)
    (subs : List (Submission Cid L C)) : Bool :=
  match (run V subs).find? (fun e => e.node.id == root) with
  | some e => decide (e.node.claim = goal)
  | none => false

/-! ## Store invariants -/

theorem childClaims_spec {st : Store Cid L C} :
    ∀ {chs : List String} {cs : List C}, childClaims st chs = some cs →
      ∀ c ∈ cs, ∃ e ∈ st, e.node.claim = c
  | [], cs, h, c, hc => by
    simp only [childClaims, Option.some.injEq] at h; subst h; cases hc
  | i :: is, cs, h, c, hc => by
    simp only [childClaims] at h
    split at h
    · rename_i e cs' he hcs
      cases h
      simp only [List.mem_cons] at hc
      rcases hc with rfl | hc
      · exact ⟨e, List.mem_of_find?_eq_some he, rfl⟩
      · exact childClaims_spec hcs c hc
    · cases h

theorem childClaims_ids {st : Store Cid L C} :
    ∀ {chs : List String} {cs : List C}, childClaims st chs = some cs →
      ∀ i ∈ chs, ∃ e ∈ st, e.node.id = i
  | [], _, _, i, hi => by cases hi
  | j :: js, cs, h, i, hi => by
    simp only [childClaims] at h
    split at h
    · rename_i e cs' he hcs
      simp only [List.mem_cons] at hi
      rcases hi with rfl | hi
      · exact ⟨e, List.mem_of_find?_eq_some he, by simpa using List.find?_some he⟩
      · exact childClaims_ids hcs i hi
    · cases h

/-- The semantic store invariant. -/
def StoreSound (Sem : C → Prop) (st : Store Cid L C) : Prop := ∀ e ∈ st, Sem e.node.claim

theorem admit_sound {V : Checker L C} {Sem : C → Prop} (hV : CheckerSound V Sem)
    {st : Store Cid L C} (hst : StoreSound Sem st) (s : Submission Cid L C) :
    StoreSound Sem (admitSubmission V st s) := by
  unfold admitSubmission
  split
  · exact hst
  · split
    · rename_i hadm
      intro e he
      rcases List.mem_append.mp he with he | he
      · exact hst e he
      · simp only [List.mem_singleton] at he
        subst he
        unfold admissible at hadm
        split at hadm
        · rename_i ob _
          exact hV.leaf ob _ hadm
        · rename_i r chs _
          split at hadm
          · rename_i cs hcs
            refine hV.rule r _ cs hadm ?_
            intro c hc
            obtain ⟨e', he', rfl⟩ := childClaims_spec hcs c hc
            exact hst e' he'
          · cases hadm
        · cases hadm
    · exact hst

theorem foldl_admit_sound {V : Checker L C} {Sem : C → Prop} (hV : CheckerSound V Sem) :
    ∀ (subs : List (Submission Cid L C)) (st : Store Cid L C), StoreSound Sem st →
      StoreSound Sem (subs.foldl (admitSubmission V) st)
  | [], _, h => h
  | s :: ss, _, h => foldl_admit_sound hV ss _ (admit_sound hV h s)

/-- **Every committed node is true**, whoever submitted it, in whatever order. -/
theorem run_invariant {V : Checker L C} {Sem : C → Prop} (hV : CheckerSound V Sem)
    (subs : List (Submission Cid L C)) : StoreSound Sem (run V subs) :=
  foldl_admit_sound hV subs [] (fun _ h => by cases h)

/-! ## Protocol facts -/

/-- An unverified leaf (validator rejects its obligation for its own claim) is never
    committed. -/
theorem unverified_leaf_rejected (V : Checker L C) (st : Store Cid L C) (a : Cid) (i : String)
    (c : C) (ob : L) (h : V.leaf ob c = false) :
    admitSubmission V st ⟨a, ⟨i, c, .leaf ob⟩⟩ = st := by
  unfold admitSubmission
  split
  · rfl
  · simp [admissible, h]

/-- **No overwrite**: a submission reusing a committed id leaves the store unchanged. -/
theorem no_overwrite (V : Checker L C) {st : Store Cid L C} {e : Submission Cid L C}
    (he : e ∈ st) (s : Submission Cid L C) (hid : s.node.id = e.node.id) : admitSubmission V st s = st := by
  unfold admitSubmission
  have : st.any (fun e => e.node.id == s.node.id) = true :=
    List.any_eq_true.mpr ⟨e, he, by simp [hid]⟩
  simp [this]

theorem admit_prefix (V : Checker L C) (st : Store Cid L C) (s : Submission Cid L C) :
    ∃ t, admitSubmission V st s = st ++ t := by
  unfold admitSubmission
  split
  · exact ⟨[], by simp⟩
  · split
    · exact ⟨[s], rfl⟩
    · exact ⟨[], by simp⟩

theorem foldl_admit_prefix (V : Checker L C) :
    ∀ (subs : List (Submission Cid L C)) (st : Store Cid L C),
      ∃ t, subs.foldl (admitSubmission V) st = st ++ t
  | [], st => ⟨[], by simp⟩
  | s :: ss, st => by
    obtain ⟨t₁, h₁⟩ := admit_prefix V st s
    obtain ⟨t₂, h₂⟩ := foldl_admit_prefix V ss (admitSubmission V st s)
    exact ⟨t₁ ++ t₂, by rw [List.foldl_cons, h₂, h₁, List.append_assoc]⟩

/-- **Commitments are permanent**: later submissions (by anyone) never remove or alter a
    committed entry. -/
theorem committed_persistent (V : Checker L C) (subs more : List (Submission Cid L C))
    {e : Submission Cid L C} (he : e ∈ run V subs) : e ∈ run V (subs ++ more) := by
  unfold run at *
  rw [List.foldl_append]
  obtain ⟨t, ht⟩ := foldl_admit_prefix V more (subs.foldl (admitSubmission V) [])
  rw [ht]; exact List.mem_append_left _ he

theorem foldl_admit_provenance (V : Checker L C) :
    ∀ (subs : List (Submission Cid L C)) (st : Store Cid L C) (e : Submission Cid L C),
      e ∈ subs.foldl (admitSubmission V) st → e ∈ st ∨ e ∈ subs
  | [], st, e, h => Or.inl h
  | s :: ss, st, e, h => by
    rcases foldl_admit_provenance V ss _ e h with h | h
    · unfold admitSubmission at h
      split at h
      · exact Or.inl h
      · split at h
        · rcases List.mem_append.mp h with h | h
          · exact Or.inl h
          · simp only [List.mem_singleton] at h; subst h; exact Or.inr List.mem_cons_self
        · exact Or.inl h
    · exact Or.inr (List.mem_cons_of_mem _ h)

/-- **Provenance**: every committed entry is literally one of the submissions, with its
    true author; the protocol invents nothing and misattributes nothing. -/
theorem committed_provenance (V : Checker L C) (subs : List (Submission Cid L C))
    {e : Submission Cid L C} (he : e ∈ run V subs) : e ∈ subs := by
  rcases foldl_admit_provenance V subs [] e he with h | h
  · cases h
  · exact h

theorem admit_nodup (V : Checker L C) {st : Store Cid L C}
    (h : (st.map (·.node.id)).Nodup) (s : Submission Cid L C) :
    ((admitSubmission V st s).map (·.node.id)).Nodup := by
  unfold admitSubmission
  split
  · exact h
  · rename_i hn
    split
    · rw [List.map_append, List.nodup_append]
      refine ⟨h, by simp, ?_⟩
      intro a ha b hb hab
      simp only [List.map_cons, List.map_nil, List.mem_singleton] at hb
      subst hb; subst hab
      obtain ⟨e, he, hid⟩ := List.mem_map.mp ha
      exact hn (List.any_eq_true.mpr ⟨e, he, by simp [hid]⟩)
    · exact h

/-- Committed ids are pairwise distinct. -/
theorem committed_ids_nodup (V : Checker L C) (subs : List (Submission Cid L C)) :
    ((run V subs).map (·.node.id)).Nodup := by
  unfold run
  suffices ∀ (ss : List (Submission Cid L C)) (st : Store Cid L C),
      (st.map (·.node.id)).Nodup → ((ss.foldl (admitSubmission V) st).map (·.node.id)).Nodup from
    this subs [] List.nodup_nil
  intro ss
  induction ss with
  | nil => intro st h; exact h
  | cons s ss ih => intro st h; exact ih _ (admit_nodup V h s)

/-- Acyclic by construction: every child of a committed derivation was committed
    strictly **before** it. -/
theorem committed_children_earlier (V : Checker L C) :
    ∀ (subs : List (Submission Cid L C)) (pre post : Store Cid L C) (e : Submission Cid L C)
      (r : String) (chs : List String),
      run V subs = pre ++ e :: post → e.node.kind = .derive r chs →
      ∀ i ∈ chs, ∃ e' ∈ pre, e'.node.id = i := by
  intro subs
  unfold run
  suffices ∀ (ss : List (Submission Cid L C)) (st : Store Cid L C),
      (∀ pre post (e : Submission Cid L C) r chs, st = pre ++ e :: post →
        e.node.kind = .derive r chs → ∀ i ∈ chs, ∃ e' ∈ pre, e'.node.id = i) →
      (∀ pre post (e : Submission Cid L C) r chs, ss.foldl (admitSubmission V) st = pre ++ e :: post →
        e.node.kind = .derive r chs → ∀ i ∈ chs, ∃ e' ∈ pre, e'.node.id = i) from
    this subs [] (fun pre post e _ _ h => by
      exact absurd h (by simp))
  intro ss
  induction ss with
  | nil => intro st h; exact h
  | cons s ss ih =>
    intro st hst
    apply ih
    intro pre post e r chs heq hk
    unfold admitSubmission at heq
    split at heq
    · exact hst pre post e r chs heq hk
    · split at heq
      · rename_i hadm
        rcases post.eq_nil_or_concat with hp | ⟨post', x, hp⟩
        · subst hp
          obtain ⟨hpre, hs⟩ := List.append_inj' heq rfl
          simp only [List.cons.injEq, and_true] at hs
          subst hpre; subst hs
          unfold admissible at hadm
          rw [hk] at hadm
          simp only at hadm
          split at hadm
          · rename_i cs hcs
            exact childClaims_ids hcs
          · cases hadm
        · subst hp
          rw [List.concat_eq_append,
            show pre ++ e :: (post' ++ [x]) = (pre ++ e :: post') ++ [x] by simp] at heq
          exact hst pre post' e r chs (List.append_inj' heq rfl).1 hk
      · exact hst pre post e r chs heq hk

/-! ## Main theorem -/

/-- Soundness for an arbitrary submission list (any population, any joint behaviour). -/
theorem run_accepts_sound [DecidableEq C] {V : Checker L C} {Sem : C → Prop}
    (hV : CheckerSound V Sem) {goal : C} {root : String} {subs : List (Submission Cid L C)}
    (h : protocolAccepts V goal root subs = true) : Sem goal := by
  unfold protocolAccepts at h
  split at h
  · rename_i e he
    simp only [decide_eq_true_eq] at h
    rw [← h]
    exact run_invariant hV subs e (List.mem_of_find?_eq_some he)
  · cases h

/-- The committed root node of an accepted run carries exactly the bound goal claim. -/
theorem accepted_root_claim_fixed [DecidableEq C] {V : Checker L C} {goal : C} {root : String}
    {subs : List (Submission Cid L C)} (h : protocolAccepts V goal root subs = true) :
    ∃ e ∈ run V subs, e.node.id = root ∧ e.node.claim = goal ∧ e ∈ subs := by
  unfold protocolAccepts at h
  split at h
  · rename_i e he
    simp only [decide_eq_true_eq] at h
    have hm := List.mem_of_find?_eq_some he
    exact ⟨e, hm, by simpa using List.find?_some he, h, committed_provenance V subs hm⟩
  · cases h

/-! ### Contributors, strategies, schedules -/

/-- Public history visible to every contributor: all previous submissions with the
    admission verdict. -/
abbrev History (Cid L C : Type) := List (Submission Cid L C × Bool)

/-- An arbitrary contributor strategy: adaptive (sees the full public history), stochastic
    (receives a per-turn random seed), possibly adversarial; returns a proposed node or
    abstains. -/
abbrev Strategy (Cid L C : Type) := History Cid L C → Nat → Option (Node L C)

/-- Execute a schedule (an arbitrary interleaving of turns, each with a random seed)
    against a strategy profile; returns the submissions and the final store. -/
def execute (V : Checker L C) (strat : Cid → Strategy Cid L C) :
    List (Cid × Nat) → History Cid L C → Store Cid L C → List (Submission Cid L C) × Store Cid L C
  | [], _, st => ([], st)
  | (a, seed) :: rest, hist, st =>
    match strat a hist seed with
    | none => execute V strat rest hist st
    | some n =>
      let s : Submission Cid L C := ⟨a, n⟩
      let st' := admitSubmission V st s
      let r := execute V strat rest (hist ++ [(s, decide (st'.length > st.length))]) st'
      (s :: r.1, r.2)

theorem execute_store (V : Checker L C) (strat : Cid → Strategy Cid L C) :
    ∀ (sched : List (Cid × Nat)) (hist : History Cid L C) (st : Store Cid L C),
      (execute V strat sched hist st).2 = (execute V strat sched hist st).1.foldl (admitSubmission V) st
  | [], _, _ => rfl
  | (a, seed) :: rest, hist, st => by
    simp only [execute]
    split
    · exact execute_store V strat rest hist st
    · simp only [List.foldl_cons]
      exact execute_store V strat rest _ _

/-- Final store of an execution started from the empty store. -/
def finalStore (V : Checker L C) (strat : Cid → Strategy Cid L C) (sched : List (Cid × Nat)) :
    Store Cid L C := (execute V strat sched [] []).2

theorem finalStore_eq_run (V : Checker L C) (strat : Cid → Strategy Cid L C)
    (sched : List (Cid × Nat)) :
    finalStore V strat sched = run V (execute V strat sched [] []).1 :=
  execute_store V strat sched [] []

/-- Protocol acceptance of an execution. -/
def executionAccepts [DecidableEq C] (V : Checker L C) (goal : C) (root : String)
    (strat : Cid → Strategy Cid L C) (sched : List (Cid × Nat)) : Bool :=
  protocolAccepts V goal root (execute V strat sched [] []).1

/-- **Distributed-contributor non-authority.**
    For every finite contributor population (`Cid` arbitrary; the schedule is a finite list
    of turns), every strategy profile (adaptive, stochastic, adversarial, colluding — the
    strategies are arbitrary functions of the public history, the contributor id and the
    seed), and every interleaving, if the protocol accepts the bound root claim `goal`, then
    `Sem goal` holds.  The only hypothesis is the local soundness of the trusted checker;
    there is **no assumption about any contributor**. -/
theorem accepted_contributions_cannot_forge_assurance [DecidableEq C] {V : Checker L C}
    {Sem : C → Prop} (hV : CheckerSound V Sem) (goal : C) (root : String)
    (strat : Cid → Strategy Cid L C) (sched : List (Cid × Nat))
    (h : executionAccepts V goal root strat sched = true) : Sem goal :=
  run_accepts_sound hV h

/-- Ordering cannot change the semantic conclusion of an accepted root: any two accepted
    executions (different strategies, different interleavings) certify the same bound
    claim, and it is true. -/
theorem accepted_conclusion_order_independent [DecidableEq C] {V : Checker L C}
    {Sem : C → Prop} (hV : CheckerSound V Sem) {goal : C} {root : String}
    {strat₁ strat₂ : Cid → Strategy Cid L C} {sched₁ sched₂ : List (Cid × Nat)}
    (h₁ : executionAccepts V goal root strat₁ sched₁ = true)
    (h₂ : executionAccepts V goal root strat₂ sched₂ = true) :
    (∃ e₁ ∈ finalStore V strat₁ sched₁, ∃ e₂ ∈ finalStore V strat₂ sched₂,
      e₁.node.id = root ∧ e₂.node.id = root ∧ e₁.node.claim = e₂.node.claim) ∧ Sem goal := by
  obtain ⟨e₁, he₁, hi₁, hc₁, _⟩ := accepted_root_claim_fixed h₁
  obtain ⟨e₂, he₂, hi₂, hc₂, _⟩ := accepted_root_claim_fixed h₂
  rw [finalStore_eq_run, finalStore_eq_run]
  exact ⟨⟨e₁, he₁, e₂, he₂, hi₁, hi₂, hc₁.trans hc₂.symm⟩, run_accepts_sound hV h₁⟩

/-- **Collusion does not help**: a coalition's joint behaviour is just some submission
    list, and every execution's submissions are such a list, so the list-level theorem
    `run_accepts_sound` already covers every coalition (including all contributors
    colluding, with private coordination). -/
theorem coalition_is_submission_list (V : Checker L C) (strat : Cid → Strategy Cid L C)
    (sched : List (Cid × Nat)) :
    ∃ subs : List (Submission Cid L C), finalStore V strat sched = run V subs :=
  ⟨_, finalStore_eq_run V strat sched⟩

/-- Every committed entry of an execution was submitted by the contributor recorded as its
    author during that execution (no contributor can commit in another's name). -/
theorem execution_provenance (V : Checker L C) (strat : Cid → Strategy Cid L C)
    (sched : List (Cid × Nat)) {e : Submission Cid L C} (he : e ∈ finalStore V strat sched) :
    e ∈ (execute V strat sched [] []).1 := by
  rw [finalStore_eq_run] at he
  exact committed_provenance V _ he

/-! ## Honest limitation: liveness, not soundness -/

/-- **An adversary can block acceptance** by squatting the root id with a true but
    different claim first: with the honest submission alone the root is accepted; with the
    adversary's submission scheduled first, it is not.  (Soundness is unaffected:
    `run_accepts_sound` holds for both orders.) -/
theorem squatting_blocks_liveness :
    let V : Checker Bool Nat := { leaf := fun ob _ => ob, rule := fun _ _ _ => false }
    let honest : Submission String Bool Nat := ⟨"honest", ⟨"root", 1, .leaf true⟩⟩
    let adv : Submission String Bool Nat := ⟨"adversary", ⟨"root", 2, .leaf true⟩⟩
    protocolAccepts V 1 "root" [honest] = true ∧ protocolAccepts V 1 "root" [adv, honest] = false ∧
      protocolAccepts V 1 "root" [honest, adv] = true := by
  decide

/-! ## PCS instance -/

open PCS PCS.V2.Json PCS.V2.Replay PCS.V2.CertificateModel PCS.V2.EndToEnd PCS.V2.Flagship
open PCS.V2.DomainAdapter

variable {D : Domain}

/-- **Distributed contributions against an accepted PCS package.**  Contributors build the
    obligation graph for the signed certificate claim `cl` (decoded to `c`, compiled to
    `ir`) through the admission protocol, with leaves discharged only by certificate
    evidence that is required by `cl`, replayed with outcome PASS and accepted by the
    adapter's leaf check.  Acceptance of the root `ir` yields the domain proposition in the
    world of the committed artifacts — for every population, strategy profile and schedule. -/
theorem pcs_distributed_domain_sound {O : Oracles} {T : TrustAnchor} {inp : PCS.V2.Package.PackageInput}
    {r : AcceptedResult} {Valid : ReplayRequest → Prop} (hacc : acceptPCS O T inp = some r)
    (hV : ReplayFaithful O.exec Valid) (A : DomainAdapter D) (hA : AdapterSound A Valid)
    (cl : CertClaim) {c : D.Claim} {ir : A.IR} (hcomp : A.compile c = some ir)
    (root : String) (strat : Cid → Strategy Cid String A.IR) (sched : List (Cid × Nat))
    (h : executionAccepts (pcsChecker A r cl) ir root strat sched = true) :
    D.Holds (A.world r.table) c :=
  hA.compile_sound _ c ir hcomp
    (accepted_contributions_cannot_forge_assurance (pcsChecker_sound hacc hV hA cl) ir root
      strat sched h)

end PCS.V2.DistributedContributors

/-! ## The committed store is a graph accepted by the existing checker -/

namespace PCS.V2.DistributedContributors

open PCS.V2.ClaimGraph

variable {Cid L C : Type}

/-- The obligation graph formed by the committed store. -/
def storeGraph (st : Store Cid L C) (root : String) : Graph L C := ⟨st.map (·.node), root⟩

/-- Every committed entry was admissible with respect to the store **at its admission
    time** and its id was fresh then. -/
theorem admitted_at_time (V : Checker L C) (subs : List (Submission Cid L C)) :
    ∀ (pre post : Store Cid L C) (e : Submission Cid L C), run V subs = pre ++ e :: post →
      admissible V pre e.node = true ∧ ¬ pre.any (fun x => x.node.id == e.node.id) = true := by
  unfold run
  suffices ∀ (ss : List (Submission Cid L C)) (st : Store Cid L C),
      (∀ pre post (e : Submission Cid L C), st = pre ++ e :: post →
        admissible V pre e.node = true ∧ ¬ pre.any (fun x => x.node.id == e.node.id) = true) →
      (∀ pre post (e : Submission Cid L C), ss.foldl (admitSubmission V) st = pre ++ e :: post →
        admissible V pre e.node = true ∧ ¬ pre.any (fun x => x.node.id == e.node.id) = true) from
    this subs [] (fun pre post e h => absurd h (by simp))
  intro ss
  induction ss with
  | nil => intro st h; exact h
  | cons s ss ih =>
    intro st hst
    apply ih
    intro pre post e heq
    unfold admitSubmission at heq
    split at heq
    · exact hst pre post e heq
    · rename_i hfresh
      split at heq
      · rename_i hadm
        rcases post.eq_nil_or_concat with hp | ⟨post', x, hp⟩
        · subst hp
          obtain ⟨hpre, hs⟩ := List.append_inj' heq rfl
          simp only [List.cons.injEq, and_true] at hs
          subst hpre; subst hs
          exact ⟨hadm, hfresh⟩
        · subst hp
          rw [List.concat_eq_append,
            show pre ++ e :: (post' ++ [x]) = (pre ++ e :: post') ++ [x] by simp] at heq
          exact hst pre post' e (List.append_inj' heq rfl).1
      · exact hst pre post e heq

theorem storeGraph_find_prefix {pre rest : Store Cid L C} {i : String} {e : Submission Cid L C}
    (h : pre.find? (fun x => x.node.id == i) = some e) (root : String) :
    (storeGraph (pre ++ rest) root).find i = some e.node := by
  simp only [Graph.find, storeGraph, List.find?_map, List.map_append, List.find?_append]
  have : (pre.find? ((fun n : Node L C => n.id == i) ∘ (·.node))) = some e := h
  simp [this]

theorem childClaims_findAll {pre rest : Store Cid L C} (root : String) :
    ∀ {chs : List String} {cs : List C}, childClaims pre chs = some cs →
      (storeGraph (pre ++ rest) root).findAll chs = some cs
  | [], cs, h => by simp only [childClaims, Option.some.injEq] at h; subst h; rfl
  | i :: is, cs, h => by
    simp only [childClaims] at h
    split at h
    · rename_i e cs' he hcs
      cases h
      simp only [Graph.findAll, storeGraph_find_prefix he root, childClaims_findAll root hcs]
    · cases h

theorem store_eq_of_id {F : Store Cid L C} (hnd : (F.map (·.node.id)).Nodup) :
    ∀ {x y : Submission Cid L C}, x ∈ F → y ∈ F → x.node.id = y.node.id → x = y := by
  induction F with
  | nil => intro x y hx; cases hx
  | cons a F ih =>
    intro x y hx hy hxy
    simp only [List.map_cons, List.nodup_cons, List.mem_map, not_exists, not_and] at hnd
    rcases List.mem_cons.mp hx with h1 | h1 <;> rcases List.mem_cons.mp hy with h2 | h2
    · rw [h1, h2]
    · subst h1; exact absurd hxy.symm (hnd.1 y h2)
    · subst h2; exact absurd hxy (hnd.1 x h1)
    · exact ih hnd.2 h1 h2 hxy

theorem storeGraph_find_mem {F : Store Cid L C} (hnd : (F.map (·.node.id)).Nodup)
    {e : Submission Cid L C} (he : e ∈ F) (root : String) :
    (storeGraph F root).find e.node.id = some e.node := by
  have hex : ∃ x ∈ F, (x.node.id == e.node.id) = true := ⟨e, he, by simp⟩
  obtain ⟨x, hx⟩ := Option.isSome_iff_exists.mp
    (List.find?_isSome.mpr hex)
  have hxm := List.mem_of_find?_eq_some hx
  have hxid : x.node.id = e.node.id := by simpa using List.find?_some hx
  have := store_eq_of_id hnd hxm he hxid
  subst this
  simp only [Graph.find, storeGraph, List.find?_map]
  have : F.find? ((fun n : Node L C => n.id == x.node.id) ∘ (·.node)) = some x := hx
  simp [this]

/-- The committed store, newest first, is a topologically ordered closed list of locally
    valid nodes of the store graph. -/
theorem store_topo (V : Checker L C) (subs : List (Submission Cid L C)) (root : String) :
    ∀ (q post : Store Cid L C), run V subs = q.reverse ++ post →
      TopoList V (storeGraph (run V subs) root) (q.map (·.node.id)) := by
  intro q
  induction q with
  | nil => intro _ _; exact TopoList.nil
  | cons e q ih =>
    intro post hF
    have hF' : run V subs = q.reverse ++ e :: post := by simpa using hF
    have hq := ih (e :: post) hF'
    obtain ⟨hadm, hfresh⟩ := admitted_at_time V subs q.reverse post e hF'
    have hnd := committed_ids_nodup V subs
    have hemem : e ∈ run V subs := by rw [hF']; simp
    refine TopoList.cons hq ?_ (storeGraph_find_mem hnd hemem root) ?_ ?_
    · intro hm
      obtain ⟨x, hx, hxid⟩ := List.mem_map.mp hm
      exact hfresh (List.any_eq_true.mpr ⟨x, List.mem_reverse.mpr hx, by simp [hxid]⟩)
    · unfold LocalOK
      unfold admissible at hadm
      split at hadm
      · rename_i ob hk; rw [hk]; exact hadm
      · rename_i r chs hk
        rw [hk]
        split at hadm
        · rename_i cs hcs
          refine ⟨cs, ?_, hadm⟩
          rw [hF']
          exact childClaims_findAll root hcs
        · cases hadm
      · cases hadm
    · intro r chs hk ch hch
      unfold admissible at hadm
      rw [hk] at hadm
      simp only at hadm
      split at hadm
      · rename_i cs hcs
        obtain ⟨x, hx, hxid⟩ := childClaims_ids hcs ch hch
        exact List.mem_map.mpr ⟨x, List.mem_reverse.mp hx, hxid⟩
      · cases hadm

/-- **Refinement into the existing obligation-graph checker.**  If the admission protocol
    accepts the bound root claim, the committed store, read as an obligation graph, is
    accepted by `checkGraph` (hence also by `checkGraphMemo`), so it can be fed unchanged to
    `domainAccepts` and every existing graph theorem applies. -/
theorem protocol_graph_accepted [DecidableEq C] {V : Checker L C} {goal : C} {root : String}
    {subs : List (Submission Cid L C)} (h : protocolAccepts V goal root subs = true) :
    checkGraph V (storeGraph (run V subs) root) goal = true := by
  obtain ⟨e, he, hid, hclaim, _⟩ := accepted_root_claim_fixed h
  have hnd := committed_ids_nodup V subs
  have ht := store_topo V subs root (run V subs).reverse [] (by simp)
  have hroot : root ∈ (run V subs).reverse.map (·.node.id) :=
    List.mem_map.mpr ⟨e, List.mem_reverse.mpr he, hid⟩
  have hfind : (storeGraph (run V subs) root).find root = some e.node := by
    rw [← hid]; exact storeGraph_find_mem hnd he root
  apply checkGraph_complete
  refine ⟨by simpa [storeGraph] using hnd, ⟨e.node, hfind, hclaim⟩, ?_, ?_⟩
  · intro x hx
    obtain ⟨nd, hf, hl, _⟩ := topo_mem ht (topo_closed ht hx hroot)
    exact ⟨nd, hf, hl⟩
  · intro x hx
    exact topo_acyclic ht x (topo_closed ht hx hroot)

end PCS.V2.DistributedContributors
