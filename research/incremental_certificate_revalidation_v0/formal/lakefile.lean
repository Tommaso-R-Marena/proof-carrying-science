import Lake
open Lake DSL

package «pcs-incremental» where
  moreLeanArgs := #["-DautoImplicit=false"]

@[default_target]
lean_lib PCSIncremental where
  roots := #[`PCSIncremental]
