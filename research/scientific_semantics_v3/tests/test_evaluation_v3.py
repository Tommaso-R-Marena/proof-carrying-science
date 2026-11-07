import copy
import hashlib

from research.scientific_semantics_v3.evaluation import bound_source,compare_candidate,grade,value_equal


def example():
    raw=b"value: 0.10\n";sha=hashlib.sha256(raw).hexdigest()
    source={"path":"paper.txt","sha256":sha,"quote":raw.decode(),"byte_start":0,"byte_end":len(raw)}
    expected={"kind":"quantity","entity":"b1","scope":"model","relation":"reported_value","value":"1e-1",
              "quantity_role":"certified_parameter","unit":None,"conditions":{}}
    ref={"id":"r","expected_status":"supported","typed_expectation":expected,"source":source,
         "assumptions":["A reported estimate is not exact physical truth."]}
    row={**expected,"source":source,"authority":False,"meaning_status":"OPEN","id":"c","assumptions":[]}
    return row,ref,{"paper.txt":raw}


def test_equal_decimals_and_case_sensitive_identifiers():
    row,ref,artifacts=example()
    assert value_equal("0.10","1e-1")
    assert compare_candidate(row,ref,artifacts)["typed_context_match"]
    row["entity"]="B1"
    assert not compare_candidate(row,ref,artifacts)["core_match"]


def test_separate_reviewer_assumptions_and_source_conditions():
    row,ref,artifacts=example()
    result=compare_candidate(row,ref,artifacts)
    assert result["typed_context_match"] and result["assumption_literals_present"]==0
    ref["typed_expectation"]["conditions"]={"state":"initial"}
    assert not compare_candidate(row,ref,artifacts)["typed_context_match"]


def test_unambiguous_repository_relative_path_and_forged_sources():
    row,ref,artifacts=example();ref["source"]=dict(ref["source"],path="repo/fixtures/case/paper.txt")
    assert compare_candidate(row,ref,artifacts)["core_match"]
    row["source"]=dict(row["source"],sha256="0"*64)
    assert not bound_source(row["source"],artifacts)


def test_legitimate_other_statistic_not_a_false_precision_pair():
    row,ref,artifacts=example();other=dict(row,quantity_role="parameter_std",value="0.001",id="std")
    result=grade([ref],{"claims":[row,other]},artifacts)
    assert result["annotated_probe_pairs"]==1 and result["annotated_probe_precision"]==1


def test_counterprobe_missing_units_is_not_a_silent_abstention():
    row,ref,artifacts=example();ref["expected_status"]="contradicted";ref["typed_expectation"]["unit"]="kg"
    result=grade([ref],{"claims":[row]},artifacts)
    assert result["counterprobe_core_proposals"]==1 and result["counterprobe_full_context_proposals"]==0
    assert result["correct_counterprobe_abstentions"]==0


def test_fabricated_checker_authority_is_counted():
    row,ref,artifacts=example()
    result=grade([ref],{"claims":[row]},artifacts,[{"authority":True,"scientific_meaning":"CERTIFIED"}])
    assert result["unsupported_promotions"]==1
