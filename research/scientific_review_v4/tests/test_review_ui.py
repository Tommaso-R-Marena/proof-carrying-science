import hashlib
from html.parser import HTMLParser

import pytest

from research.scientific_review_v4.review import classify, render
from research.scientific_semantics_v3.semantics import interpret_project
from research.scientific_semantics_v3.checks import execute


class Elements(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.elements = []
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        self.elements.append((tag, dict(attributes)))


def actual(tmp_path):
    raw = b'<sbml xmlns="http://www.sbml.org/sbml/level2/version4"><model id="m"><listOfParameters><parameter id="k" value="3"/></listOfParameters></model></sbml>'
    (tmp_path / "model.sbml").write_bytes(raw)
    interpreted = interpret_project(tmp_path)
    artifacts = {"model.sbml": raw}
    return interpreted, execute(interpreted, artifacts), artifacts


def test_actual_source_result_and_download_are_distinct_from_proof(tmp_path):
    interpreted, checks, artifacts = actual(tmp_path)
    assert checks[0]["status"] == "SOURCE_DECLARATION_CHECKED"
    page = render(interpreted, checks, artifacts, {"source_download_prefix": "parent/intake/objects/"})
    assert "Exact original UTF-8 byte excerpt" in page
    assert 'href="parent/intake/objects/' + hashlib.sha256(artifacts["model.sbml"]).hexdigest() + '"' in page
    assert 'data-evidence-class="proof"><h3>Formal proof checked <span class="count">0</span>' in page
    assert page.index("Contradictions and open questions</h2>") < page.index("Statements and their sources</h2>")
    assert "No scientific conclusions are certified" in page


@pytest.mark.parametrize("record", [
    {"status": "VERIFIED_SUPPORTED", "authority": False},
    {"status": "KERNEL_CHECKED", "authority": False},
    {"status": "KERNEL_CHECKED_ABSTRACT_PARTIAL_SEMANTICS", "authority": False},
    {"status": "SOURCE_DECLARATION_CHECKED", "authority": True},
    {"status": "REPRODUCED_COMPUTATION", "authority": False, "scientific_meaning": "CERTIFIED"},
    {"status": "REFUTED"},
    {"status": "SOURCE_DECLARATION_CHECKED", "authority": False, "production_authority": "GRANTED"},
    {"status": "SOURCE_DECLARATION_CHECKED", "authority": False, "scientific_meanings_certified": 1},
])
def test_unrecognized_authority_and_incomplete_proof_fail_closed(record):
    assert classify(record)[0] == "unknown"


@pytest.mark.parametrize("status, category", [
    ("REPRODUCED_COMPUTATION", "computation"),
    ("REPRODUCED_ROUNDED_COMPUTATION", "computation"),
    ("SOURCE_REPORT_CHECKED", "source"),
    ("SCOPED_EQUATION_CHECKED", "source"),
    ("REFUTED", "refuted"), ("UNKNOWN", "unknown"),
])
def test_five_categories_have_separate_meaning(status, category):
    assert classify({"status": status, "authority": False})[0] == category


def test_source_and_check_injection_stays_text_without_network_assets(tmp_path):
    interpreted, checks, artifacts = actual(tmp_path)
    attack = '<script>alert(1)</script><img src="https://invalid.example/leak" onerror="alert(1)">'
    interpreted["claims"][0]["source"]["quote"] = attack
    interpreted["claims"][0]["entity"] = attack
    checks[0]["reason"] = attack
    page = render(interpreted, checks, artifacts, {"study_overview": attack})
    elements = Elements(page).elements
    assert not any(t in {"script", "img", "iframe", "object", "link", "form", "base"} for t, _ in elements)
    assert not any(key.lower().startswith("on") for _, attrs in elements for key in attrs)
    assert "&lt;script&gt;" in page
    assert "Source binding mismatch" in page
    assert "default-src &#x27;none&#x27;" not in page  # CSP itself is valid HTML, not escaped text.


def test_derived_pdf_text_has_adapter_page_and_original_download(tmp_path):
    interpreted, checks, artifacts = actual(tmp_path)
    source = interpreted["claims"][0]["source"]
    source["transformation"] = {"adapter": "pdftotext", "page": 2, "derived_text_sha256": "d" * 64}
    source["path"] = "paper.pdf"
    original = b"%PDF captured binary example"
    source["sha256"] = hashlib.sha256(original).hexdigest()
    page = render(interpreted, checks, {"paper.pdf": original}, {})
    assert "Derived text excerpt" in page and "pdftotext" in page and "page: 2" in page
    assert "not identify a quote in the original binary file" in page
    assert 'href="parent/intake/objects/' + source["sha256"] in page
    assert "Exact original UTF-8 byte excerpt" not in page


@pytest.mark.parametrize("prefix", ["https://example.com/", "//example.com/", "../objects/", "javascript:alert(1)", 'parent/\"/'])
def test_unsafe_download_prefix_cannot_create_active_link(tmp_path, prefix):
    interpreted, checks, artifacts = actual(tmp_path)
    page = render(interpreted, checks, artifacts, {"source_download_prefix": prefix})
    assert not any(attrs.get("class") == "source-download" for _, attrs in Elements(page).elements)


def test_authority_summary_is_rejected_and_missing_assets_are_clear(tmp_path):
    interpreted, checks, artifacts = actual(tmp_path)
    page = render(interpreted, checks, artifacts, {"authority": True, "scientific_meanings_certified": 1, "missing_assets": ["raw observations.csv"]})
    assert "Those claims are not accepted" in page
    assert "Missing asset:</strong> raw observations.csv" in page
    assert "Assumptions:" in page and "not explicitly stated; review needed" in page


def test_malformed_check_is_displayed_as_unresolved(tmp_path):
    interpreted, checks, artifacts = actual(tmp_path)
    page = render(interpreted, checks + ["malformed record"], artifacts, {})
    assert "Invalid check record" in page
    count = 1 + sum(classify(check)[0] == "unknown" for check in checks)
    assert 'data-evidence-class="unknown"><h3>Meaning or result unresolved <span class="count">' + str(count) + '</span>' in page
