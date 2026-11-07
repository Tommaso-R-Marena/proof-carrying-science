import hashlib
import json
from pathlib import Path
import shutil
import zipfile

import pytest

from research.scientific_intake_v1.intake import canonical
from research.scientific_semantics_v3.pipeline import run,replay,bounded_stage


def project(tmp_path):
    p=tmp_path/"project";p.mkdir()
    (p/"model.sbml").write_text('<sbml xmlns="http://www.sbml.org/sbml/level2/version4" level="2" version="4"><model id="m"><listOfParameters><parameter id="k" value="3" units="second"/></listOfParameters></model></sbml>')
    return p


def resign(folder,name):
    m=json.loads((folder/"manifest.json").read_text());m["files"][name]=hashlib.sha256((folder/name).read_bytes()).hexdigest()
    (folder/"manifest.json").write_bytes(canonical(m)+b"\n")


def test_actual_snapshot_pipeline_preserves_source_and_checks_it(tmp_path):
    source=project(tmp_path);out=tmp_path/"review"
    result=run(source,out,check=True)
    (source/"model.sbml").write_text("The original mutable file changed.")
    assert result["checks"]["SOURCE_DECLARATION_CHECKED"]==1
    assert replay(out)["status"]=="REPLAYED"
    assert result["scientific_meanings_certified"]==0


@pytest.mark.parametrize("target",["semantics.json","checks.json","dependencies.json","summary.json","review.html"])
def test_resigned_result_forgery_fails_independent_replay(tmp_path,target):
    out=tmp_path/"review";run(project(tmp_path),out,check=True)
    if target=="review.html":(out/target).write_text("PCS has certified every scientific conclusion.")
    else:
        value=json.loads((out/target).read_text())
        if target=="semantics.json":value["claims"][0]["value"]="300"
        elif target=="checks.json":value[0]["status"]="REFUTED"
        elif target=="dependencies.json":value["dependency_completeness"]="PROVED"
        elif target=="summary.json":value["scientific_meanings_certified"]=1
        (out/target).write_bytes(canonical(value))
    resign(out,target)
    with pytest.raises(ValueError):replay(out)


def test_local_zip_review_and_malicious_source_nonexecution(tmp_path):
    source=project(tmp_path);marker=tmp_path/"EXECUTED"
    (source/"attack.py").write_text("from pathlib import Path\nPath("+repr(str(marker))+").touch()\n")
    archive=tmp_path/"project.zip"
    with zipfile.ZipFile(archive,"w") as z:
        for p in source.iterdir():z.write(p,p.name)
    out=tmp_path/"result";run(archive,out,check=True)
    assert not marker.exists() and replay(out)["status"]=="REPLAYED"


def test_no_implicit_check_authorization_and_no_evidence_overwrite(tmp_path):
    out=tmp_path/"result";source=project(tmp_path)
    run(source,out)
    assert json.loads((out/"checks.json").read_text())==[]
    assert replay(out)["status"]=="INTEGRITY_ONLY"
    with pytest.raises(ValueError,match="overwrite"):run(source,out,check=True)


def test_source_context_and_pinned_manifest_are_checked(tmp_path):
    out=tmp_path/"review";run(project(tmp_path),out,check=True)
    with pytest.raises(ValueError,match="pinned manifest"):replay(out,expected_manifest_sha256="0"*64)
    value=json.loads((out/"context.json").read_text());value["authority"]=True
    (out/"context.json").write_bytes(canonical(value));resign(out,"context.json")
    with pytest.raises(ValueError,match="context changed"):replay(out)


def test_bounded_worker_cannot_accept_path_traversal_or_huge_file():
    with pytest.raises(ValueError):bounded_stage({"../escape":b"x"},False)
    with pytest.raises(ValueError):bounded_stage({"large.md":b"x"*1_000_001},False)


def test_private_parent_cache_reused_but_new_replay_ignores_it(tmp_path):
    source=project(tmp_path);cache=tmp_path/"private-cache"
    first=run(source,tmp_path/"first",check=True,cache_dir=cache)
    second=run(source,tmp_path/"second",check=True,cache_dir=cache)
    assert first["checks"]==second["checks"]
    assert replay(tmp_path/"second")["cache_used"] is False
