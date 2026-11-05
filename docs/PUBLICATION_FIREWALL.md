# Publication Firewall

Status: **private pre-publication architecture**.

The synthesis project is intentionally downstream of the constituent research projects. Its purpose is to generalize reusable assurance principles, not to scoop, absorb, or prematurely disclose the scientific contributions of those projects.

## Rules before constituent papers are public

1. Do not copy unpublished algorithms, theorem statements, benchmark results, figures, datasets, or experimental conclusions from another research project into this repository.
2. Use synthetic fixtures, public standards, or independently specified toy models for the assurance kernel and domain adapters.
3. Treat CertiForge, CASMI/QFD, proof-carrying agency, protein work, and other projects as **future case studies**, not dependencies, until their publication/IP status is cleared.
4. Keep this repository private until a deliberate publication decision is made.
5. For each future import, record the source repository, commit, authorship, license/IP owner, public disclosure date, and paper/preprint citation.
6. Publish constituent scientific papers first when the synthesis would reveal their novel mechanism or result. The synthesis paper should cite them rather than silently subsume them.
7. Patent-sensitive work must be cleared with the relevant owner/technology-transfer counsel before public disclosure.

## Current independence statement

The v0.4 kernel and PK adapter use only generic assurance abstractions and a synthetic one-compartment IV-bolus pharmacokinetic example. They do not incorporate CASMI/QFD algorithms, CertiForge optimizer internals, unpublished biological discoveries, or AI-safety implementation code.

## Preferred publication sequence

1. Freeze and submit the strongest constituent papers independently.
2. Establish citable versions (preprint, proceedings, journal DOI, or accepted manuscript as appropriate).
3. Add post-publication adapters/case studies with explicit provenance.
4. Publish the general Proof-Carrying Scientific Workflows synthesis only after it can properly cite the constituent work.
