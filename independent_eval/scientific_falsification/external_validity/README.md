# External-validity protocols (Task 11)

Templates and scoring software only. **No invented participants or results.**

Score a filled protocol:

```bash
PYTHONPATH=independent_eval/scientific_falsification python3 -c
from pathlib import Path
from python_harness.external_validity import score_protocol_file
print(score_protocol_file(
  Path('independent_eval/scientific_falsification/external_validity/templates/external_validity_protocol_blank.json'),
  Path('independent_eval/scientific_falsification/external_validity/rubrics/completeness_rubric.json')))
```
