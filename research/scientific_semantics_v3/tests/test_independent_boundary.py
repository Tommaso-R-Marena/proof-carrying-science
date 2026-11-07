"""Proposed claims and self-signed evidence cannot select their own meaning.

Forgery cases are attacker-controlled negative inputs. No mocked/affirmative
Lean result is used to validate authorization.
"""
import copy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from research.scientific_semantics_v3 import adversarial, checks, semantics


POSITIVE_SOURCE_STATUSES = {"SOURCE_DECLARATION_CHECKED", "SCOPED_EQUATION_CHECKED", "SOURCE_REPORT_CHECKED"}


def source_fixture(tmp_path):
    raw = adversarial.sbml(
        '<notes>Unrelated statement.</notes>'
        '<listOfParameters><parameter id="k" value="3" constant="false"/></listOfParameters>'
        '<listOfRules><assignmentRule variable="k">' + adversarial.mathml('<cn>2</cn>') + '</assignmentRule></listOfRules>').encode()
    (tmp_path / "source.sbml").write_bytes(raw)
    meanings = semantics.interpret_project(tmp_path)
    quantity = next(c for c in meanings["claims"] if c["quantity_role"] == "parameter")
    equation = next(c for c in meanings["claims"] if c["quantity_role"] == "assignment_rule")
    return raw, quantity, equation


def test_independent_source_check_still_accepts_unchanged_scoped_declarations(tmp_path):
    raw, quantity, equation = source_fixture(tmp_path)
    assert checks.check_claim(quantity, {"source.sbml": raw})["status"] == "SOURCE_DECLARATION_CHECKED"
    assert checks.check_claim(equation, {"source.sbml": raw})["status"] == "SCOPED_EQUATION_CHECKED"


@pytest.mark.parametrize("change", [
    {"scope": "forged/reaction/elsewhere"},
    {"quantity_role": "local_parameter"},
    {"model_id": "other_model"},
    {"scope": "authored/reaction/absent", "reaction_scope": "absent"},
])
def test_scientific_scope_is_independently_checked(tmp_path, change):
    raw, candidate, _ = source_fixture(tmp_path)
    candidate = {**candidate, **change}
    result = checks.check_claim(candidate, {"source.sbml": raw})
    assert result["status"] not in POSITIVE_SOURCE_STATUSES, result


def test_correct_value_with_unrelated_true_quote_is_not_assertion_grounding(tmp_path):
    raw, candidate, _ = source_fixture(tmp_path)
    unrelated = b"Unrelated statement."
    a = raw.index(unrelated)
    candidate = copy.deepcopy(candidate)
    candidate["source"].update(byte_start=a, byte_end=a+len(unrelated), quote=unrelated.decode())
    assert semantics.verify_grounding(candidate, tmp_path)  # Artifact/span integrity alone is insufficient.
    result = checks.check_claim(candidate, {"source.sbml": raw})
    assert result["status"] not in POSITIVE_SOURCE_STATUSES, result


def test_equation_lhs_cannot_be_replaced_by_a_new_scientific_variable(tmp_path):
    raw, _, candidate = source_fixture(tmp_path)
    candidate = {**candidate, "lhs": {"op": "symbol", "name": "WRONG"}}
    result = checks.check_claim(candidate, {"source.sbml": raw})
    assert result["status"] not in POSITIVE_SOURCE_STATUSES, result


@pytest.mark.parametrize("kind", ["quantity", "equation"])
def test_relation_polarity_cannot_be_inverted_while_reusing_correct_value(tmp_path, kind):
    raw, quantity, equation = source_fixture(tmp_path)
    candidate = {**(quantity if kind == "quantity" else equation), "relation": "not_equal"}
    result = checks.check_claim(candidate, {"source.sbml": raw})
    assert result["status"] not in POSITIVE_SOURCE_STATUSES, result


def test_mathml_foreign_child_is_not_accepted_by_local_name(tmp_path):
    raw, _, candidate = source_fixture(tmp_path)
    changed = raw.replace(b'<cn>2</cn>', b'<evil:cn xmlns:evil="urn:fake-math">2</evil:cn>')
    candidate = copy.deepcopy(candidate)
    # The attacker preserves matching digest/span of the altered source. The
    # checker must validate mathematical namespaces rather than just hashes.
    a = changed.index(b'<assignmentRule')
    b = changed.index(b'</assignmentRule>') + len(b'</assignmentRule>')
    candidate["source"].update(sha256=hashlib.sha256(changed).hexdigest(), byte_start=a, byte_end=b,
                               quote=changed[a:b].decode())
    result = checks.check_claim(candidate, {"source.sbml": changed})
    assert result["status"] not in POSITIVE_SOURCE_STATUSES, result


def test_nist_table_claim_cannot_cite_unrelated_header():
    raw = adversarial.AUTHORED_NIST
    end = raw.index(b'\n')
    candidate = {"id": "attacker-proposal", "kind": "quantity", "entity": "b1", "scope": "model",
                 "quantity_role": "certified_parameter", "value": "1.0000000000", "relation": "reported_value",
                 "source": {"path": "study.dat", "sha256": hashlib.sha256(raw).hexdigest(),
                            "byte_start": 0, "byte_end": end, "quote": raw[:end].decode()}}
    result = checks.check_claim(candidate, {"study.dat": raw})
    assert result["status"] not in POSITIVE_SOURCE_STATUSES, result


def _resign(package):
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for name in manifest["files"]:
        manifest["files"][name] = hashlib.sha256((package / name).read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")


@pytest.fixture(scope="module")
def actual_package(tmp_path_factory):
    from research.scientific_semantics_v3 import pipeline
    root = tmp_path_factory.mktemp("actual-semantic-package")
    source = root / "source"
    source.mkdir()
    (source / "experiment.dat").write_bytes(adversarial.AUTHORED_NIST)
    output = root / "evidence"
    pipeline.run(source, output, check=True)
    assert pipeline.replay(output)["status"] == "REPLAYED"
    return output


def _forged_checks(package, mutate):
    from research.scientific_semantics_v3 import pipeline
    meanings = json.loads((package / "semantics.json").read_text())
    records = json.loads((package / "checks.json").read_text())
    mutate(records)
    (package / "checks.json").write_text(json.dumps(records, sort_keys=True) + "\n")
    summary = pipeline.summary_for(meanings, records, True)
    (package / "summary.json").write_text(json.dumps(summary, sort_keys=True) + "\n")
    (package / "review.html").write_text(pipeline.review_html(meanings, records, summary))
    _resign(package)


@pytest.mark.parametrize("recheck", [False, True])
def test_fabricated_scientific_authority_rejected_even_with_resigned_display(actual_package, tmp_path, recheck):
    from research.scientific_semantics_v3 import pipeline
    package = tmp_path / "forged"
    shutil.copytree(actual_package, package)
    _forged_checks(package, lambda rows: rows[0].update(authority=True, scientific_meaning="CERTIFIED"))
    with pytest.raises(ValueError):
        pipeline.replay(package, recheck=recheck)


def test_omitted_check_rejected_after_manifest_and_display_are_resigned(actual_package, tmp_path):
    from research.scientific_semantics_v3 import pipeline
    package = tmp_path / "forged"
    shutil.copytree(actual_package, package)
    _forged_checks(package, lambda rows: rows.pop())
    with pytest.raises(ValueError):
        pipeline.replay(package)


def test_fabricated_interpretation_rejected_after_manifest_resigning(actual_package, tmp_path):
    from research.scientific_semantics_v3 import pipeline
    package = tmp_path / "forged"
    shutil.copytree(actual_package, package)
    meanings = json.loads((package / "semantics.json").read_text())
    meanings["claims"][0]["authority"] = True
    (package / "semantics.json").write_text(json.dumps(meanings, sort_keys=True) + "\n")
    _resign(package)
    with pytest.raises(ValueError):
        pipeline.replay(package)
