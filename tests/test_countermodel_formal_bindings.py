"""The unproved JSON-to-Lean generator must reject malformed or misbound input."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('countermodel_bindings',
    Path(__file__).resolve().parents[1] / 'scripts/generate_countermodel_missions.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize('node', [
    {'op': 'pred', 'p': 'P', 'x': 'x'},
    {'op': 'forall', 'x': 'x', 'f': {'op': 'pred', 'p': 'X', 'x': 'x'}},
    {'op': 'forall', 'x': 'x', 'f': {'op': 'pred', 'p': 'P', 'x': 'x', 'proof': 'trusted'}},
    {'op': 'exec', 'source': 'anything'},
    {'op': 'forall', 'x': 'x"\n', 'f': {'op': 'pred', 'p': 'P', 'x': 'x"\n'}},
    {'op': 'and', 'a': {'op': 'forall', 'x': 'x', 'f': {'op': 'pred', 'p': 'P', 'x': 'x'}},
     'b': {'op': 'pred', 'p': 'Q', 'x': 'x'}},
])
def test_rejects_unbound_unknown_extra_fields_and_source_injection(node):
    with pytest.raises(ValueError):
        module.formula(node)


def test_shadowing_resolves_innermost_binder():
    node = {'op': 'forall', 'x': 'x', 'f': {'op': 'exists', 'x': 'x',
            'f': {'op': 'rel', 'x': 'x', 'y': 'x'}}}
    assert module.formula(node)[1] == '(.all (.ex (.rel 0 0)))'
