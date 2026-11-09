"""Fresh bounded correspondence and source-link regression examples."""
from copy import deepcopy
import hashlib
import json

import pytest

from research.scientific_review_v4 import correspondence as c
from research.scientific_semantics_v3 import semantics
from research.scientific_understanding_v2.interpretation import parse_expression


def config(**changes):
    value = {"format_version": 1, "parameter_file": "parameters.tsv", "problems": [{
        "sbml_files": ["model.xml"], "observable_files": ["observables.tsv"],
        "measurement_files": ["measurements.tsv"], "condition_files": ["conditions.tsv"]}]}
    value.update(changes)
    return value


def artifacts(value=None, directory=""):
    prefix = directory + "/" if directory else ""
    result = {prefix+name: b"data" for name in
              ["parameters.tsv", "model.xml", "observables.tsv", "measurements.tsv", "conditions.tsv"]}
    result[prefix+"problem.json"] = json.dumps(config() if value is None else value).encode()
    return result


def source(path, files):
    raw = files[path]
    return {"path":path, "sha256":hashlib.sha256(raw).hexdigest(), "byte_start":0,
            "byte_end":len(raw), "quote":raw.decode()}


def claim(files, path, entity, *, kind="quantity", scope="model", **extra):
    return {"id":path+"::"+entity+"::"+scope, "entity":entity, "kind":kind,
            "scope":scope, "source":source(path, files), **extra}


def test_json_links_exact_pointer_sources():
    files = artifacts()
    link, = c.parse_project_links(files)
    assert set(link) == {"config_path", "sbml_files", "measurement_files", "observable_files",
                         "condition_files", "parameter_file", "source", "pointer_sources"}
    assert link["sbml_files"] == ["model.xml"]
    assert link["parameter_file"] == "parameters.tsv"
    assert all(c.verify_source(s, files) for s in [link["source"], *link["pointer_sources"].values()])
    assert link["pointer_sources"]["/problems/0/sbml_files/0"]["quote"] == '"model.xml"'


def test_yaml_block_flow_quotes_and_comments():
    files = artifacts(); del files["problem.json"]
    files["problem.yaml"] = b'''# literal input only
format_version: 1
parameter_file: 'parameters.tsv'
problems:
  - sbml_files:
      - model.xml # explicit source
    observable_files: ["observables.tsv"]
    measurement_files: [measurements.tsv]
    condition_files: [conditions.tsv]
'''
    link, = c.parse_project_links(files)
    assert link["sbml_files"] == ["model.xml"]
    assert all(c.verify_source(s, files) for s in link["pointer_sources"].values())


def test_config_paths_are_relative_to_config_directory():
    link, = c.parse_project_links(artifacts(directory="nested"))
    assert link["sbml_files"] == ["nested/model.xml"]
    assert link["parameter_file"] == "nested/parameters.tsv"


def test_standard_indentless_yaml_and_optional_visualizations():
    files = artifacts(); del files["problem.json"]
    files["visualizations.tsv"] = b"plotId\np0\n"
    files["problem.yaml"] = b'''format_version: 1
parameter_file: parameters.tsv
problems:
- condition_files:
  - conditions.tsv
  measurement_files:
  - measurements.tsv
  observable_files:
  - observables.tsv
  sbml_files:
  - model.xml
  visualization_files:
  - visualizations.tsv
'''
    link, = c.parse_project_links(files)
    assert link["sbml_files"] == ["model.xml"]
    assert "/problems/0/visualization_files/0" in link["pointer_sources"]
    assert all(c.verify_source(s,files) for s in link["pointer_sources"].values())
    del files["visualizations.tsv"]
    with pytest.raises(ValueError,match="missing"): c.parse_project_links(files)


@pytest.mark.parametrize("version", [0, 2, 1.0, "1", True, None])
def test_only_exact_integer_format_version_one(version):
    with pytest.raises(ValueError): c.parse_project_links(artifacts(config(format_version=version)))


@pytest.mark.parametrize("target", ["../model.xml", "/model.xml", "https://example.org/model.xml",
                                    "a/../model.xml", "a//model.xml", "./model.xml", "a\\model.xml",
                                    "%2e%2e/model.xml", "model.xml?x=1"])
def test_unsafe_targets_rejected(target):
    value = config(); value["problems"][0]["sbml_files"] = [target]
    with pytest.raises(ValueError): c.parse_project_links(artifacts(value))


def test_missing_targets_and_duplicate_roles_fail_closed():
    files = artifacts(); del files["model.xml"]
    with pytest.raises(ValueError, match="missing"): c.parse_project_links(files)
    value = config(); value["problems"][0]["sbml_files"] *= 2
    with pytest.raises(ValueError, match="duplicate"): c.parse_project_links(artifacts(value))
    value = config(); value["problems"][0]["measurement_files"] = ["model.xml"]
    with pytest.raises(ValueError, match="roles"): c.parse_project_links(artifacts(value))


@pytest.mark.parametrize("prefix", ["format_version: 1\nformat_version: 1\n", "format_version: &v 1\n",
                                     "format_version: *v\n", "format_version: !include 1\n",
                                     "%YAML 1.2\nformat_version: 1\n", "---\nformat_version: 1\n"])
def test_yaml_nonliteral_features_rejected(prefix):
    files = artifacts(); del files["problem.json"]
    files["problem.yaml"] = (prefix + "parameter_file: parameters.tsv\nproblems:\n"
                             "  - sbml_files: [model.xml]\n    observable_files: [observables.tsv]\n"
                             "    measurement_files: [measurements.tsv]\n").encode()
    with pytest.raises(ValueError): c.parse_project_links(files)


def test_duplicate_json_keys_rejected():
    files = artifacts()
    files["problem.json"] = files["problem.json"].replace(b'"format_version": 1', b'"format_version": 1, "format_version": 1')
    with pytest.raises(ValueError, match="duplicate"): c.parse_project_links(files)


def test_unrelated_json_is_not_a_project_configuration():
    assert c.parse_project_links({"notes.json":b'{"arbitrary":"metadata"}'}) == []


def test_artifact_resource_and_path_bounds():
    with pytest.raises(ValueError): c.parse_project_links({"../unsafe":b"x"})
    with pytest.raises(ValueError): c.parse_project_links({"x.txt":"not bytes"})
    with pytest.raises(ValueError): c.parse_project_links({"x.txt":b"x"*(c.MAX_FILE+1)})


def test_repeated_identifiers_and_equal_equations_do_not_map():
    files = {"a.txt":b"x = 1", "b.txt":b"x = 1"}
    interpretation = {"claims":[claim(files, p, "x", kind="equation", rhs=parse_expression("1")) for p in files]}
    result = c.analyze(interpretation, files)
    assert result["mappings"] == result["correspondences"] == result["conflicts"] == []
    assert result["authority"] is False


def test_explicit_mapping_is_grounded_and_never_scientific_authority():
    files = {"a.txt":b"x = 1", "b.txt":b"y = 1", "links.md":b"Mapping: a.txt::x = b.txt::y\n"}
    result = c.analyze({"claims":[claim(files,"a.txt","x"),claim(files,"b.txt","y")]}, files)
    assert len(result["mappings"]) == len(result["correspondences"]) == 1
    assert c.verify_source(result["mappings"][0]["source"], files)
    assert result["correspondences"][0]["scientific_equivalence"] == "NOT_ESTABLISHED"
    assert all(r["authority"] is False for k in ["mappings","correspondences","conflicts","obligations"] for r in result[k])


def test_natural_mapping_sentence_needs_both_file_pointers():
    files = {"a.txt":b"x", "b.txt":b"y", "links.md":b"x in a.txt corresponds to y in b.txt.\n"}
    result = c.analyze({"claims":[claim(files,"a.txt","x"),claim(files,"b.txt","y")]}, files)
    assert len(result["correspondences"]) == 1


def test_ambiguous_same_name_abstains_and_explicit_scope_resolves():
    files = {"a.txt":b"x", "b.txt":b"y", "links.md":b"Mapping: a.txt::x = b.txt::y\n"}
    claims = [claim(files,"a.txt","x",scope="m1"),claim(files,"a.txt","x",scope="m2"),claim(files,"b.txt","y")]
    result = c.analyze({"claims":claims}, files)
    assert not result["correspondences"]
    assert any(o["kind"] == "explicit_mapping_resolution" for o in result["obligations"])
    files["links.md"] = b"Mapping: a.txt::x[scope=m1] = b.txt::y\n"
    assert len(c.analyze({"claims":claims}, files)["correspondences"]) == 1


def test_changed_source_and_forged_span_do_not_bind():
    files = {"a.txt":b"x", "b.txt":b"y", "links.md":b"Mapping: a.txt::x = b.txt::y\n"}
    claims = [claim(files,"a.txt","x"),claim(files,"b.txt","y")]
    claims[0]["source"]["byte_end"] = 0
    result = c.analyze({"claims":claims}, files)
    assert not result["correspondences"]
    assert any(o["kind"] == "source_grounding" for o in result["obligations"])


def equations(symbol_mapping=True, rhs="z/z"):
    files = {"a.txt":b"f = x/x", "b.txt":b"g = z/z",
             "links.md":b"Mapping: a.txt::f = b.txt::g\n" + (b"Mapping: a.txt::x = b.txt::z\n" if symbol_mapping else b"")}
    claims = [claim(files,"a.txt","f",kind="equation",rhs=parse_expression("x/x")),
              claim(files,"b.txt","g",kind="equation",rhs=parse_expression(rhs))]
    return files, {"claims":claims}


def test_equation_comparison_requires_every_symbol_mapping():
    files, interpretation = equations(False)
    result = c.analyze(interpretation, files)
    assert not any(r["kind"] == "equation_comparison" for r in result["correspondences"])


def test_same_spelling_symbols_still_require_explicit_mapping():
    files, interpretation = equations(False, "x/x")
    result = c.analyze(interpretation, files)
    assert not any(r["kind"] == "equation_comparison" for r in result["correspondences"])


def test_exact_rational_comparison_retains_original_domains():
    files, interpretation = equations()
    result = c.analyze(interpretation, files)
    compared, = [r for r in result["correspondences"] if r["kind"] == "equation_comparison"]
    assert compared["status"] == "EQUAL_ON_COMMON_DEFINED_DOMAIN"
    assert compared["scientific_equivalence"] == "NOT_ESTABLISHED"
    assert compared["comparison"]["original_domain_conditions"]["right"][0]["expression"]["name"] == "z"
    assert c.verify_source(compared["symbol_mappings"][0]["source"], files)
    assert compared["symbol_mappings"][0]["source"] in compared["sources"]
    assert any(o["kind"] == "common_defined_domain" and o["status"] == "OPEN" for o in result["obligations"])


def test_mapped_equation_difference_is_a_declaration_conflict():
    files, interpretation = equations(True, "z+1")
    result = c.analyze(interpretation, files)
    assert any(r["kind"] == "mapped_equation_difference" for r in result["conflicts"])


def test_mapped_unit_scale_difference_requires_explicit_mapping():
    files = {"a.txt":b"x = 1 mol", "b.txt":b"y = 1 mmol", "links.md":b"Mapping: a.txt::x = b.txt::y\n"}
    claims = [claim(files,p,e,unit=u,unit_resolution=semantics._unit_record(u,{}))
              for p,e,u in [("a.txt","x","mol"),("b.txt","y","mmol")]]
    result = c.analyze({"claims":claims}, files)
    assert any(r["kind"] == "mapped_unit_difference" for r in result["conflicts"])
    del files["links.md"]
    assert not c.analyze({"claims":claims},files)["conflicts"]


def petab(tmp_path, formula="x+observableParameter1"):
    files = artifacts()
    files["model.xml"] = b'''<sbml xmlns="http://www.sbml.org/sbml/level2/version4" level="2" version="4"><model id="EXACT_model"><listOfParameters><parameter id="x" value="1"/></listOfParameters></model></sbml>'''
    files["observables.tsv"] = ("observableId\tobservableFormula\nobs\t"+formula+"\n").encode()
    files["measurements.tsv"] = b"observableId\tmeasurement\ttime\nobs\t1\t0\n"
    files["conditions.tsv"] = b"conditionId\nc0\n"
    files["parameters.tsv"] = b"parameterId\testimate\nx\t0\n"
    for path, raw in files.items(): (tmp_path/path).write_bytes(raw)
    return files, semantics.interpret_project(tmp_path)


def test_petab_bindings_use_exact_configured_model_scope_and_quotes(tmp_path):
    files, interpretation = petab(tmp_path)
    result = c.analyze(interpretation,files)
    observable, = [r for r in result["correspondences"] if r["kind"] == "petab_observable_formula"]
    assert observable["model_id"] == observable["scope"] == "EXACT_model"
    assert observable["symbol_bindings"][0]["symbol"] == "x"
    assert all(c.verify_source(s,files) for s in observable["sources"])
    assert observable["placeholders"] == ["observableParameter1"]
    assert any(o["kind"] == "petab_observable_parameter" and o["status"] == "OPEN" for o in result["obligations"])
    assert any(r["kind"] == "petab_measurement_observable" for r in result["correspondences"])


def test_unknown_and_wrong_case_model_ids_are_open(tmp_path):
    files, interpretation = petab(tmp_path,"X+unknown")
    result = c.analyze(interpretation,files)
    observable, = [r for r in result["correspondences"] if r["kind"] == "petab_observable_formula"]
    assert observable["symbol_bindings"] == []
    assert observable["unresolved_symbols"] == ["X","unknown"]


def test_foreign_model_same_identifier_never_authorizes_binding(tmp_path):
    files, interpretation = petab(tmp_path,"x")
    interpretation["symbols"][0]["source"]["path"] = "unconfigured.xml"
    files["unconfigured.xml"] = files["model.xml"]
    result = c.analyze(interpretation,files)
    assert not any(r["kind"] == "petab_observable_formula" for r in result["correspondences"])


def test_multiple_configured_models_abstain(tmp_path):
    files, interpretation = petab(tmp_path)
    value = config(); value["problems"][0]["sbml_files"].append("second.xml")
    files["second.xml"] = files["model.xml"]
    files["problem.json"] = json.dumps(value).encode()
    result = c.analyze(interpretation,files)
    assert not any(r["kind"] == "petab_observable_formula" for r in result["correspondences"])
    assert any(o["kind"] == "petab_model_scope" for o in result["obligations"])


def test_invalid_config_becomes_open_obligation_in_analyze():
    result = c.analyze({}, artifacts(config(format_version="1")))
    assert not result["mappings"]
    assert any(o["kind"] == "petab_configuration" and o["status"] == "OPEN" for o in result["obligations"])


def test_utf8_exact_spans_survive_unicode_comments():
    files = artifacts(); del files["problem.json"]
    files["problem.yaml"] = ("# α source\nformat_version: 1\nparameter_file: parameters.tsv\nproblems:\n"
                             "  - sbml_files: [model.xml]\n    observable_files: [observables.tsv]\n"
                             "    measurement_files: [measurements.tsv]\n").encode()
    link, = c.parse_project_links(files)
    assert all(c.verify_source(s,files) for s in [link["source"],*link["pointer_sources"].values()])


def test_no_uploaded_python_executes(tmp_path):
    sentinel = tmp_path/"ran"
    files = {"unsafe.py":("from pathlib import Path\nPath("+repr(str(sentinel))+").write_text('bad')\n").encode()}
    assert not c.analyze({},files)["mappings"]
    assert not sentinel.exists()
