"""Complete, unique, zero-skip test aggregation for the live-lab CI boundary."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

PREFIX="research/structured_action_lab_v4/"
GROUPS={"unit":(PREFIX+"test_actions.py",),"native":(PREFIX+"test_native.py",)}


def census():
    found={PREFIX+p.name for p in Path(__file__).parent.glob("test_*.py")}
    assigned={p for paths in GROUPS.values() for p in paths if p.startswith(PREFIX)}
    if found!=assigned:raise ValueError("Unassigned or missing live-lab test module")
    return True


def combine(regressions,reports,output):
    census();expected={"structured-tests-"+name for name in GROUPS}
    if {p.name for p in reports.iterdir()}!=expected:raise ValueError("Missing/unexpected live-lab test artifacts")
    seen=set();counts={};root=ET.Element("testsuites")
    files=[("regressions",regressions/"tests.xml",None)]
    files += [(name,reports/("structured-tests-"+name)/("unit-tests.xml" if name=="unit" else "native-tests.xml"),
               {p[:-3].replace("/",".") for p in paths}) for name,paths in GROUPS.items()]
    for group,path,modules in files:
        with path.open("rb") as stream:raw=stream.read(8*1024*1024+1)
        if len(raw)>8*1024*1024 or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():raise ValueError("Bounded non-DTD JUnit required")
        document=ET.fromstring(raw);count=0;found=set();suites=list(document.iter("testsuite"))
        if not suites:raise ValueError("Empty test report")
        for suite in suites:
            cases=suite.findall("testcase")
            if not cases or suite.get("tests")!=str(len(cases)) or any(suite.get(k)!="0" for k in ("failures","errors","skipped")):
                raise ValueError("Incomplete or failed test report")
            for case in cases:
                key=(case.get("classname"),case.get("name"))
                if not all(key) or key in seen or any(case.find(k) is not None for k in ("failure","error","skipped")):
                    raise ValueError("Duplicate/failed test case")
                if modules is not None and key[0] not in modules:raise ValueError("Unexpected test module")
                seen.add(key);found.add(key[0]);count+=1
            root.append(suite)
        if modules is not None and found!=modules:raise ValueError("Missing required test module")
        counts[group]=count
    output.mkdir(parents=True,exist_ok=False)
    ET.ElementTree(root).write(output/"tests.xml",encoding="utf-8",xml_declaration=True)
    summary=dict(tests=sum(counts.values()),failures=0,errors=0,skipped=0,groups=counts)
    (output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    return summary


def main():
    p=argparse.ArgumentParser();p.add_argument("regressions",type=Path);p.add_argument("reports",type=Path);p.add_argument("output",type=Path)
    a=p.parse_args();print(json.dumps(combine(a.regressions,a.reports,a.output)))


if __name__=="__main__":main()
