"""Independent scientific-falsification evaluation harness (Workstream B).

Treats PCS as a black-box system under test. Prefer subprocess CLI entrypoints
(`pcs`, `python -m pcs.cli`) over importing PCS internals in test assertions.
Fixture *generation* may use PCS adapters once to freeze byte-identical tables.
"""

from .paths import ROOT, REPO_ROOT, FIXTURES, CASEBOOK, RESULTS

__all__ = ["ROOT", "REPO_ROOT", "FIXTURES", "CASEBOOK", "RESULTS"]
