"""Coverage gates for test assignment, independent of native authorization."""
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from .ci import PREFIX, SHARDS, aggregate, census, run


def test_current_census_assigns_all_test_modules_and_baselines_once():
    result = census()
    assert result["research_test_modules"] == len(list(Path(__file__).parent.glob("test_*.py")))
    assert result["assigned_test_modules"] == result["research_test_modules"] + 2


def test_new_unassigned_module_fails_census(tmp_path):
    for path in Path(__file__).parent.glob("test_*.py"):
        (tmp_path / path.name).touch()
    (tmp_path / "test_future_capability.py").touch()
    with pytest.raises(ValueError, match="unassigned"):
        census(tmp_path)


@pytest.mark.parametrize("attack", ["duplicate", "empty", "baseline", "missing"])
def test_invalid_assignments_never_form_successful_matrix(attack):
    groups = dict(SHARDS)
    if attack == "duplicate":groups["duplicate"] = groups["worker"]
    elif attack == "empty":groups["empty"] = ()
    elif attack == "baseline":groups["authority"] = (PREFIX + "test_progress.py",)
    else:groups["extra"] = (PREFIX + "test_does_not_exist.py",)
    with pytest.raises(ValueError):census(assignments=groups)


def test_unknown_shard_creates_no_output(tmp_path):
    target = tmp_path / "unknown"
    with pytest.raises(ValueError, match="unknown"):
        run("not-a-shard", target)
    assert not target.exists()


def report_fixtures(directory):
    """Artificial report structure only; this never represents authorization."""
    for shard, modules in SHARDS.items():
        parent = directory / ("progress-supervisor-tests-" + shard)
        parent.mkdir(parents=True)
        root = ET.Element("testsuites")
        suite = ET.SubElement(root, "testsuite", tests=str(len(modules)), failures="0", errors="0", skipped="0")
        for module in modules:
            ET.SubElement(suite, "testcase", classname=module[:-3].replace("/", "."), name="structural-fixture")
        ET.ElementTree(root).write(parent / "tests.xml")


def test_report_aggregation_requires_all_assigned_modules(tmp_path):
    report_fixtures(tmp_path / "reports")
    result = aggregate(tmp_path / "reports", tmp_path / "combined")
    assert result["tests"] == sum(map(len, SHARDS.values()))
    assert result["ci_observations_not_authority"] and result["pcs_authority"] is False


@pytest.mark.parametrize("attack", ["missing", "extra", "count", "failure", "skip", "duplicate", "module", "dtd"])
def test_bad_shard_reports_cannot_produce_aggregate_success(tmp_path, attack):
    reports = tmp_path / "reports";report_fixtures(reports)
    path = reports / "progress-supervisor-tests-authority/tests.xml"
    root = ET.parse(path).getroot();suite = root.find("testsuite")
    if attack == "missing":path.unlink()
    elif attack == "extra":(reports / "unexpected").mkdir()
    elif attack == "count":suite.set("tests", "999")
    elif attack == "failure":suite.set("failures", "1")
    elif attack == "skip":ET.SubElement(suite.find("testcase"), "skipped")
    elif attack == "duplicate":suite[1].set("classname", suite[0].get("classname"))
    elif attack == "module":suite.remove(suite[-1]);suite.set("tests", str(len(suite)))
    else:path.write_bytes(b'<!DOCTYPE test [<!ENTITY x "boom">]><testsuites/>')
    if attack not in ["missing", "extra", "dtd"]:ET.ElementTree(root).write(path)
    with pytest.raises((ValueError, FileNotFoundError)):
        aggregate(reports, tmp_path / "combined")
    assert not (tmp_path / "combined").exists()
