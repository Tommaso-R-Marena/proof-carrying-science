# Journal-demo dataset provenance

All datasets below are **publicly redistributed** research/literature artifacts.
PCS Next uses them for assurance-method demonstration only.

| Dataset | Path | Origin / citation | License | Notes |
|---|---|---|---|---|
| Theophylline (`Theoph`) | `theophylline/raw/Theoph.csv` | Boeckmann, Sheiner & Beal (1994) NONMEM Users Guide Part V; Upton theophylline study; redistributed via R `datasets::Theoph` / Rdatasets | Public redistribution (Rdatasets); classic published PK teaching dataset | Oral dosing — **not** IV bolus |
| Indomethacin (`Indometh`) | `indomethacin/raw/Indometh.csv` | Kwan et al. pharmacokinetics of indomethacin; R `datasets::Indometh` / Rdatasets | Public redistribution (Rdatasets) | IV kinetics teaching set |
| e-Drug3D PK | `edrug3d/raw/e-Drug3D_2118_PK.csv` | Douguet (2024), Zenodo 10.5281/zenodo.17063565 | CC BY 4.0 | FDA-approved drug PK property table |
| OSP DDI literature DB | `osp_ddi/raw/DDI.csv` | Open Systems Pharmacology “Database for observed data” v1.9; values digitized from cited peer-reviewed papers | Upstream OSP project terms; retain paper `Reference` column | Not a clinical claim by PCS |

## Explicit non-claims

- Presence here does **not** mean an outside laboratory validated PCS.
- Fitting a model to published data does **not** rediscover biological mechanisms.
- Digitized secondary tables may contain transcription error; fail closed on inconsistency.

| Paper blurb fixture | `paper_abstracts/pinheiro_bates_theoph_blurb.txt` | Paraphrased public teaching-context sentences about Theoph modeling (not a verbatim copyrighted abstract) | Fixture / fair-use paraphrase | For claim-extraction plumbing only |
