import PCS.V2.DomainAuthority

/-!
# The external-world boundary as a theorem-level object

PCS establishes domain propositions about the **committed computational world**
`A.world r.table` â€” the world determined by the delivered, digest-bound, signed artifact
bytes.  It cannot, by itself, establish anything about an external / deployed / physical
world: acceptance is a function of the archive bytes, so two external worlds that agree on
the committed bytes receive the same verdict (see `false_external_world_not_corresponding` and the
AI-safety counter-model in `PCS.V2.Witnesses.AISafetyDeployment`).

`ExternalWorldBridge D` makes the boundary explicit:

* `ExternalWorld`  â€” the external semantic domain (deployed executions, physical samples, â€¦);
* `ExternalHolds`  â€” the external reading of a domain claim;
* `Corresponds w ew` â€” the domain-specific **data-adequacy relation** between a committed
  world and an external world (e.g. "the committed trace is a faithful log of the deployed
  run").  PCS never proves it; it is an explicit premise of every transfer theorem;
* `transport` â€” the domain lemma: correspondence plus committed truth gives external truth.
  This is an obligation of the bridge's author, proved once per domain.

`external_world_transfer_sound`:
PCS acceptance + `AdapterSound` + an explicit `Corresponds (A.world r.table) ew` premise
â‡’ `ExternalHolds ew c`.
-/

set_option autoImplicdÑPÐ€L@ú÷Ýœ…ªì