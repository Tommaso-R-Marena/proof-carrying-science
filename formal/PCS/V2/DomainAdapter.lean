import PCS.V2.ClaimGraph
import PCS.V2.Flagship

/-!
# Generic domain adapters: from PCS acceptance to a domain-native semantic proposition

A **domain** `D` is anything with a type of native claims, a semantic world, and a truth
relation `D.Holds : D.World → D.Claim → Prop` (computational biology, chemistry, ML
evaluation, AI-safety trace audits, simulation, …).  Nothing about `D` is assumed.

A **domain adapter** `A : DomainAdapter D` connects `D` to PCS:

* `decode`   — typed decoding of a signed certificate claim predicate (JSON) into a
  domain claim (the *claim binding*);
* `compile`  — typed compilation of a domain claim into the adapter's claim IR (the root
  obligation of an obligation graph);
* `world`    — the domain world determined by the committed, digest-bound artifact bytes;
* `sem`      — the semantics of claim-IR nodes in a world;
* `leafCheck` — does a certificate evidence object (whose replay has passed) discharge an
  IR node?
* `ruleCheck` — is a decomposition step valid?

`AdapterSound A Valid` is the **local** contract a new domain must discharge.  It never
mentions a particular claim's truth:

* `compile_sound` — compilation reflects semantics: `sem w (compile c) → Holds w c`;
* `rule_sound`    — every accepted decomposition rule is semantics-preserving;
* `leaf_sound`    — an evidence object accepted by `leafCheck`, whose replay request is
  `Valid` (i.e. wi4T4 =w����