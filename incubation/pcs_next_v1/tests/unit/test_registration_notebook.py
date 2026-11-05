import json

import pytest

from pcs_next_v1.adapters.notebook import inspect_notebook
from pcs_next_v1.core.errors import PcsNextError
from pcs_next_v1.falsification.registration import freeze_experiment_plan, record_deviation


def test_registration_tamper():
    plan = {
        "experiment_id": "e1",
        "hypotheses": ["h"],
        "outcomes": ["o"],
        "metrics": ["m"],
        "split_rules": {},
        "baselines": [],
        "stopping_criteria": [],
        "randomization": {},
        "negative_controls": [],
        "planned_comparisons": [],
        "analysis_class": "confirmatory",
    }
    frozen = freeze_experiment_plan(plan)
    frozen["plan"]["metrics"] = ["mutated"]
    with pytest.raises(PcsNextError):
        record_deviation(frozen, {"kind": "x"})


def test_notebook_exec_flag(tmp_path):
    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {},
        "cells": [
            {"cell_type": "code", "execution_count": 1, "metadata": {}, "outputs": [], "source": ["exec('1')\n"]}
        ],
    }
    p = tmp_path / "t.ipynb"
    p.write_text(json.dumps(nb))
    st = inspect_notebook(p)
    assert any("dynamic_execution" in f for f in st["flags"])
