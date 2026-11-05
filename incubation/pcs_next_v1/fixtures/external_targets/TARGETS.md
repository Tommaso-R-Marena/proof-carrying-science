# External / real targets used by the mutation campaign

| Target | Origin | Notes |
|---|---|---|
| `pcs_pkpd_one_compartment` | Snapshot of repo `examples/pkpd_one_compartment` | Real PCS example; copied into owned namespace |
| `pcs_mass_action` | Snapshot of `examples/scientific_mass_action` | Real PCS example |
| `pcs_biopharma_demo` | Snapshot of `examples/biopharma_demo` | Real PCS example |
| `pcs_scientific_workflow_v3` | Snapshot of `examples/scientific_workflow_v3` | Amount conservation + static Python probes |
| `pcs_pkpd_translation_benchmark` | Snapshot of `examples/pkpd_translation_benchmark` | PK verify + Emax PD + unit-label gap probe |
| `public_nlmixr2data` | Subset of [nlmixr2/nlmixr2data](https://github.com/nlmixr2/nlmixr2data) (`data/`, LICENSE) | GPL-3+; ACOP/NONMEM teaching datasets |
| `public_osp_observed` | Subset of OSP Database-for-observed-data v1.9 | Digitized literature PK/DDI tables |
| Journal demos | `fixtures/journal_demos` | Theoph, Indometh, e-Drug3D, Puromycin |
| `pcs_notebook_demo` | Owned minimal notebook fixture | Static notebook + exec injection probe |

Production trees were **not** modified. Campaign mutations run only under `results/real_world_campaign/work/`.
