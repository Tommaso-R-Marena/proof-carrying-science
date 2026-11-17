import Lake
open Lake DSL

package «pcs-scientific-reasoning» where
  moreLeanArgs := #["-DautoImplicit=false"]

@[default_target]
lean_lib ScientificReasoning where
  roots := #[`ScientificReasoning]
