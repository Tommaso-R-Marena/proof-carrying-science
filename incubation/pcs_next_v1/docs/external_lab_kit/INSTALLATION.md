# Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install cryptography jsonschema pytest
export PYTHONPATH=incubation/pcs_next_v1:$PYTHONPATH
python incubation/pcs_next_v1/scripts/run_synthetic_pilot.py
```
