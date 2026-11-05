# Real finite-data scientific workflow

`penguins.csv` contains real field measurements from Palmer Station LTER, collected by Dr. Kristen Gorman. The exact upstream revision, retained attribution, source URLs and digests are in `provenance.json`; `UPSTREAM_LICENSE.md` is the upstream CC0 dedication. This dataset is neither synthetic nor a new PCS collection.

`run_workflow.py` and `contract.json` are newly authored CC0 artifacts. The workflow fits a descriptive line to flipper length and body mass, explicitly converts millimetres to metres and grams to kilograms, and records exclusions. It does not prove biological causation or applicability to unobserved animals.

From this directory, run `python run_workflow.py`. From the repository root, run `python scripts/run_scientific_workflow_v2.py --output /tmp/pcs-workflow-new`. The second command uses ephemeral signing keys, builds the existing signed PCS package, and executes a separate receiving process that independently calculates the statistics. Submitted source files are retained as evidence and are not executed by the receiver.
