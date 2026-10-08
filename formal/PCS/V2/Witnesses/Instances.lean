import PCS.V2.Witnesses.Biology
import PCS.V2.Witnesses.AISafety
import PCS.V2.Witnesses.MLEval
import PCS.V2.Proposer

/-!
# Witness instances: one authority registry, three domains, non-vacuity

* `witnessRegistry` registers the biology and AI-safety checkers together in one extended
  authority; `witnessRegistry_registered` discharges the registration conditions.
* `bio_assurance`, `ai_assurance` — the domain theorems for that concrete authority
  (sole hypothesis `NoForgery`); `ml_archive_sound` already applies to the unchanged
  production authority.
* Non-vacuity: concrete runs of each checker that PASS on good data and FAIL on bad data,
  and concrete obligation graphs accepted by the induced PCS obligation checker.  (The
  generic theorems are therefore not vacuous: the checkers and graph checker do accept
  real inputs.)
-/

set_option autoImplicit false

namespace PCS.V2.Witnesses.Instances

open PCS PCS.V2.Json PCS.V2.Replay PCS.V2.CertificateModel PCS.V2.ClaimGraph
open PCS.V2.DomainAdapter PCS.V2.DomainAuthority PCS.V2.Witnesses
open PCS.V2.Witnesses.Biology PCS.V2.Witnesses.AISafety PCS.V2.Witnesses.MLEval

def witnessRegistry : List DomainChecker := [boundsChecker, scoreChecker, traceChecker]

theorem witnessRegistry_registered : Registered witnessRegistry :=
  ⟨by decide, by decide⟩

theorem bio_assurance {t : PCS.V2.Authority.AuthorityTranscript}
    {T : PCS.V2.EndToEnd.TrustAnchor} {signed : List UInt8 → Prop}
    (hB : PCS.V2.Signature.NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {raw : ByteArray} {inp : PCS.V2.Package.PackageInput} {r : PCS.V2.EndToEnd.AcceptedResult}
    (h : acceptArchiveWithCheckers (registry witnessRegistry) t T raw = some (inp, r))
    {cid : String} {g : Graph String BioIR} {c : BioClaim}
    (hd : domainAccepts bioAdapter r cid g = some c) :
    ∃ sq st, artBytes r.table c.seqA = some sq ∧ artBytes r.table c.sitesA = some st ∧
      SitesInRange sq st ∧ c.threshold ≤ hydroScore sq st :=
  bio_archive_sound witnessRegistry_registered (by simp [witnessRegistry])
    (by simp [witnessRegistry]) hB h hd

theorem ai_assurance {t : PCS.V2.Authority.AuthorityTranscript}
    {T : PCS.V2.EndToEnd.TrustAnchor} {signed : List UInt8 → Prop}
    (hB : PCS.V2.Signature.NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {raw : ByteArray} {inp : PCS.V2.Package.PackageInput} {r : PCS.V2.EndToEnd.AcceptedResult}
    (h : acceptArchiveWithCheckers (registry witnessRegistry) t T raw = some (inp, r))
    {cid : String} {g : Graph String TraceIR} {c : TraceClaim}
    (hd : domainAccepts aiAdapter r cid g = some c) :
    ∀ a ∈ c.traces, ∃ tr, artBytes r.table a = some tr ∧ TraceSafe tr c.budget c.forbidden :=
  ai_archive_sound witnessRegistry_registered (by simp [witnessRegistry]) hB h hd

/-! ## Non-vacuity: biology -/

/-- `MAVKL` -/
def seqBytes : ByteArray := ⟨#[77, 65, 86, 75, 76]⟩
/-- sites 2, 3, 5 (A, V, L: all hydrophobic) -/
def sitesBytes : ByteArray := ⟨#[2, 3, 5]⟩
/-- site 9 is out of range -/
def badSitesBytes : ByteArray := ⟨#[2, 9]⟩
def bioTable : List (String × ByteArray) :=
  [("seq", seqBytes), ("sites", sitesBytes), ("bad_sites", badSitesBytes)]

def boundsEv (seqA sitesA : String) : JVal :=
  .obj [("check_spec", .obj [("type", .str "residue_bounds"), ("sequence_artifact", .str seqA),
    ("sites_artifact", .str sitesA)])]
def scoreEv (seqA sitesA : String) (k : Int) : JVal :=
  .obj [("check_spec", .obj [("type", .str "hydrophobic_score"),
    ("sequence_artifact", .str seqA), ("sites_artifact", .str sitesA), ("threshold", .num k)])]

def req (ev : JVal) (tbl : List (String × ByteArray)) : ReplayRequest := ⟨[], "v", ev, tbl⟩

example : (boundsChecker.run (req (boundsEv "seq" "sites") bioTable)).outcome = .pass := by decide
example : (boundsChecker.run (req (boundsEv "seq" "bad_sites") bioTable)).outcome = .fail := by decide
example : (scoreChecker.run (req (scoreEv "seq" "sites" 3) bioTable)).outcome = .pass := by decide
example : (scoreChecker.run (req (scoreEv "seq" "sites" 4) bioTable)).outcome = .fail := by decide

def bioClaim : BioClaim := ⟨"seq", "sites", 3⟩
def bioEvidence : List CertEvidence :=
  [⟨"e1", .computationalTest, .pass, .null, boundsEv "seq" "sites"⟩,
   ⟨"e2", .computationalTest, .pass, .null, scoreEv "seq" "sites" 3⟩]
def bioCertClaim : CertClaim := ⟨"c1", .computational, .null, ["e1", "e2"], [], .computational⟩
def bioGraph : Graph String BioIR :=
  ⟨[⟨"root", .sites bioClaim, .derive "bio.split" ["l1", "l2"]⟩,
    ⟨"l1", .inRange "seq" "sites", .leaf "e1"⟩,
    ⟨"l2", .score "seq" "sites" 3, .leaf "e2"⟩], "root"⟩

/-- The biology obligation graph is accepted by the induced PCS obligation checker. -/
theorem bioGraph_accepted :
    checkGraph (pcsCheckerIn bioAdapter bioEvidence bioCertClaim) bioGraph (.sites bioClaim) = true := by
  decide

/-! ## Non-vacuity: AI safety -/

def traceOk : ByteArray := ⟨#[0, 1, 2, 4]⟩     -- risks 0,1,2,0: total 3
def traceForbidden : ByteArray := ⟨#[0, 9, 1]⟩ -- contains forbidden action 9
def aiTable : List (String × ByteArray) := [("ep1", traceOk), ("ep2", traceOk), ("bad", traceForbidden)]
def traceEv (a : String) : JVal :=
  .obj [("check_spec", .obj [("type", .str "trace_invariant"), ("trace_artifact", .str a),
    ("budget", .num 3), ("forbidden", .num 9)])]

example : (traceChecker.run (req (traceEv "ep1") aiTable)).outcome = .pass := by decide
example : (traceChecker.run (req (traceEv "bad") aiTable)).outcome = .fail := by decide

def aiClaim : TraceClaim := ⟨["ep1", "ep2"], 3, 9⟩
def aiEvidence : List CertEvidence :=
  [⟨"t1", .computationalTest, .pass, .null, traceEv "ep1"⟩,
   ⟨"t2", .computationalTest, .pass, .null, traceEv "ep2"⟩]
def aiCertClaim : CertClaim := ⟨"c2", .computational, .null, ["t1", "t2"], [], .computational⟩
def aiGraph : Graph String TraceIR :=
  ⟨[⟨"root", .all aiClaim, .derive "ai.episodes" ["s1", "s2"]⟩,
    ⟨"s1", .safe "ep1" 3 9, .leaf "t1"⟩, ⟨"s2", .safe "ep2" 3 9, .leaf "t2"⟩], "root"⟩

theorem aiGraph_accepted :
    checkGraph (pcsCheckerIn aiAdapter aiEvidence aiCertClaim) aiGraph (.all aiClaim) = true := by
  decide

/-! ## Non-vacuity: ML evaluation (graph level; the leaf checker is the verified built-in) -/

def csvEv (a b : String) : JVal :=
  .obj [("check_spec", .obj [("type", .str "csv_disjoint"), ("left_artifact", .str a),
    ("right_artifact", .str b), ("key", .str "id")])]

def trainCsv : ByteArray := "id,x\n1,a\n2,b\n".toUTF8
def validCsv : ByteArray := "id,x\n3,c\n".toUTF8
def leakyCsv : ByteArray := "id,x\n2,z\n".toUTF8

/-- The production built-in `csv_disjoint` checker passes on disjoint splits ... -/
example : (PCS.V2.Csv.csvRun (req (csvEv "train" "valid")
    [("train", trainCsv), ("valid", validCsv)])).outcome = .pass := by decide
/-- ... and fails on a leaking split (key `2` occurs in both). -/
example : (PCS.V2.Csv.csvRun (req (csvEv "train" "valid")
    [("train", trainCsv), ("valid", leakyCsv)])).outcome = .fail := by decide

def mlClaim : SplitClaim := ⟨"train", "valid", "test", "id"⟩
def mlEvidence : List CertEvidence :=
  [⟨"d1", .computationalTest, .pass, .null, csvEv "train" "valid"⟩,
   ⟨"d2", .computationalTest, .pass, .null, csvEv "train" "test"⟩,
   ⟨"d3", .computationalTest, .pass, .null, csvEv "valid" "test"⟩]
def mlCertClaim : CertClaim := ⟨"c3", .computational, .null, ["d1", "d2", "d3"], [], .computational⟩
def mlGraph : Graph String SplitIR :=
  ⟨[⟨"root", .split mlClaim, .derive "ml.pairwise" ["p1", "p2", "p3"]⟩,
    ⟨"p1", .disjoint "train" "valid" "id", .leaf "d1"⟩,
    ⟨"p2", .disjoint "train" "test" "id", .leaf "d2"⟩,
    ⟨"p3", .disjoint "valid" "test" "id", .leaf "d3"⟩], "root"⟩

theorem mlGraph_accepted :
    checkGraph (pcsCheckerIn mlAdapter mlEvidence mlCertClaim) mlGraph (.split mlClaim) = true := by
  decide

end PCS.V2.Witnesses.Instances
