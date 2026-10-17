# Journal-backed demos report

## Datasets (public / redistributed)

See `fixtures/journal_demos/PROVENANCE.md` and `MANIFEST.json` (SHA-256 pinned).

| Demo | Dataset | Result (this environment) |
|---|---|---|
| Theophylline oral Bateman + IV misspecification | R `datasets::Theoph` / Boeckmann–Sheiner–Beal; Pinheiro & Bates | 12/12 oral grid threshold met; IV structural **REFUTED**; external lab **OPEN** |
| Indomethacin biexponential + mono negative control | R `datasets::Indometh` | Monoexponential refuted; biexponential computational support; external **OPEN** |
| e-Drug3D t½↔VD/Cl consistency | Zenodo 10.5281/zenodo.17063565 (CC BY 4.0) | 1072 complete rows checked; 820 within 50% 1-cmt diagnostic |
| OSP DDI literature table | OSP Database for observed data v1.9 | 635 rows; 0 missing references; 0 non-positive AUCR |
| Paper blurb claim extraction | Fixture paraphrasing public Theoph modeling context | Obligations extracted; no scientific authority conferred |

## Non-claims

- Journal authors did not run PCS.
- These demos are not clinical validation.
- Digitized secondary tables may contain transcription error relative to primary figures.

## Reproduce

```bash
python incubation/pcs_next_v1/scripts/run_journal_demos.py
```
