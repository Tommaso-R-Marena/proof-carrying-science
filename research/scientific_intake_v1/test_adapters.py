"""Real-format adapter checks, including hostile inputs and no-execution tests."""
from __future__ import annotations

import io
import json
from pathlib import Path
import struct
import zipfile

import pytest

from . import adapters


def _zip(files: dict[str, str | bytes], **kwargs) -> bytes:
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, **kwargs) as archive:
        for name, value in files.items():
            archive.writestr(name, value)
    return target.getvalue()


def _docx(extra: dict[str, str | bytes] | None = None) -> bytes:
    files = {
        "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        "_rels/.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        "word/document.xml": '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Measured result</w:t><w:tab/><w:t>42</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>temperature</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>298 K</w:t></w:r></w:p></w:tc></w:tr></w:tbl><w:sectPr/></w:body></w:document>',
    }
    files.update(extra or {})
    return _zip(files)


def _xlsx(extra: dict[str, str | bytes] | None = None) -> bytes:
    files = {
        "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/></Types>',
        "_rels/.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Measurements" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/></Relationships>',
        "xl/sharedStrings.xml": '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>mass</t></si></sst>',
        "xl/worksheets/sheet1.xml": '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="inlineStr"><is><t>kg</t></is></c></row><row r="2"><c r="A2"><v>12.5</v></c><c r="B2"><f>A2*2</f><v>25</v></c><c r="C2" t="b"><v>1</v></c></row></sheetData></worksheet>',
    }
    files.update(extra or {})
    return _zip(files)


def _pdf(pages: int = 1, text: str = "Scientific measurement 42") -> bytes:
    """Build a real, cross-reference-indexed PDF without a document dependency."""
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    children = []
    for _ in range(pages):
        page_number = len(objects) + 1
        stream_number = page_number + 1
        children.append(f"{page_number} 0 R")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {stream_number} 0 R >>".encode())
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii")
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    objects[1] = f"<< /Type /Pages /Count {pages} /Kids [{' '.join(children)}] >>".encode()
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(output)


def _result(name: str, raw: bytes, status: str = "EXTRACTED") -> dict:
    result = adapters.extract(name, raw)
    assert result["status"] == status, result["warnings"]
    assert result["version"] == adapters.VERSION
    assert result["warnings"]
    assert result["capabilities"]["execution"] is False
    json.dumps(result, allow_nan=False)
    if status != "EXTRACTED":
        assert result["segments"] == []
    return result


def test_text_markdown_locators_and_strict_utf8():
    segments = _result("notes.MD", "# Result\nμ = 2.0\n".encode())["segments"]
    assert segments[1] == {"locator": {"line": 2}, "text": "μ = 2.0", "kind": "text_line", "data": {}}
    _result("bad.txt", b"\xff", "ERROR")
    _result("bad.txt", b"a\0b", "ERROR")


def test_csv_quotes_headers_multiline_and_tsv():
    result = _result("data.csv", b'name,value\n"long\nlabel",2.5\n')
    row = result["segments"][1]
    assert row["locator"] == {"row": 2, "line_start": 2, "line_end": 3}
    assert row["data"] == {"headers": ["name", "value"], "values": ["long\nlabel", "2.5"], "row": 2}
    assert _result("data.tsv", b"a\tb\n1\t2")["segments"][1]["data"]["values"] == ["1", "2"]


@pytest.mark.parametrize("raw", [b"", b"a,a\n1,2", b",b\n1,2", b"a,b\n1", b'a,b\n"unfinished,2', b"a,b\n1,2,3"])
def test_csv_malformed_fails_closed(raw):
    _result("data.csv", raw, "ERROR")


def test_json_pointers_scalars_empty_containers_and_finite_values():
    segments = _result("config.json", b'{"a/b":{"~k":[42,{},[]]},"ok":true}')["segments"]
    pointers = {s["locator"]["json_pointer"]: s["data"]["value"] for s in segments}
    assert pointers == {"/a~1b/~0k/0": 42, "/a~1b/~0k/1": {}, "/a~1b/~0k/2": [], "/ok": True}
    for raw in (b'{"x":1,"x":2}', b'{"v":NaN}', b'{"v":1e999}', b"[" * 66 + b"0" + b"]" * 66):
        _result("bad.json", raw, "ERROR")


def test_python_is_ast_data_and_never_executes(tmp_path):
    marker = tmp_path / "MUST_NOT_EXIST"
    raw = f"from os import system\nimport numpy as np\nRATE = 4.2\nsystem('touch {marker}')\ndef run():\n    return 7\n".encode()
    result = _result("experiment.py", raw)
    imports = [s for s in result["segments"] if s["kind"] == "python_import"]
    assert imports[0]["data"] == {"module": "os", "names": ["system"]}
    assert any(s["data"].get("value") == 4.2 for s in result["segments"])
    assert not marker.exists()
    _result("bad.py", b"def broken(:", "ERROR")


def test_notebook_preserves_stored_output_provenance_without_execution(tmp_path):
    marker = tmp_path / "MUST_NOT_EXIST"
    notebook = {"nbformat": 4, "nbformat_minor": 5, "cells": [{"cell_type": "code", "execution_count": 88, "source": [f"open({str(marker)!r},'w').write('bad')\n"], "outputs": [{"output_type": "execute_result", "execution_count": 88, "data": {"text/plain": ["verified: True"], "text/html": ["<script>bad()</script>"]}}]}]}
    segments = _result("analysis.ipynb", json.dumps(notebook).encode())["segments"]
    assert segments[0]["data"]["execution"] == "NEVER"
    assert segments[1]["data"]["stored_output_status"] == "UNVERIFIED"
    assert segments[1]["locator"] == {"cell": 1, "output": 1, "part": "stored_output"}
    assert "script" not in segments[1]["text"]
    assert not marker.exists()
    _result("bad.ipynb", b'{"nbformat":4,"cells":[{"cell_type":"code","source":1}]}', "ERROR")


def test_lean_text_declarations_comments_imports_and_unverified_proofs():
    raw = b'import Lean\n/- theorem fake : False := by sorry\n/- nested -/ -/\ntheorem real : True := by trivial\n#eval IO.println "UNTRUSTED"\n'
    segments = _result("theory.lean", raw)["segments"]
    assert len(segments) == 2
    assert segments[0]["data"]["modules"] == ["Lean"]
    assert segments[1]["data"]["name"] == "real"
    assert segments[1]["locator"] == {"line": 4}
    assert segments[1]["data"]["proof_status"] == "UNVERIFIED"
    _result("broken.lean", b"/- unterminated", "ERROR")


@pytest.mark.skipif(not Path(adapters.PDFTOTEXT).is_file(), reason="pdftotext unavailable")
def test_real_pdf_text_pages_and_limits():
    segments = _result("paper.pdf", _pdf(2))["segments"]
    assert len(segments) == 2
    assert segments[1]["locator"] == {"page": 2}
    assert "Scientific measurement 42" in segments[0]["text"]
    _result("too-many.pdf", _pdf(adapters.MAX_PDF_PAGES + 1), "ERROR")
    _result("empty-scan.pdf", _pdf(text=""), "UNSUPPORTED")
    _result("broken.pdf", b"%PDF-1.4\ninvalid", "ERROR")


def test_pdf_missing_dependency_reported_honestly(monkeypatch):
    monkeypatch.setattr(adapters, "PDFTOTEXT", "/nonexistent/pdftotext")
    result = _result("paper.pdf", _pdf(), "UNSUPPORTED")
    assert result["capabilities"]["formats"]["pdf"]["available"] is False


def test_real_docx_paragraph_and_table_locators():
    segments = _result("report.docx", _docx())["segments"]
    assert segments[0]["text"] == "Measured result\t42"
    assert segments[0]["locator"] == {"paragraph": 1}
    assert segments[2]["locator"] == {"table": 1, "row": 1, "column": 2}
    assert segments[2]["data"]["value"] == "298 K"


def test_real_xlsx_shared_strings_numbers_cached_formulas_and_locators():
    segments = _result("measurements.xlsx", _xlsx())["segments"]
    by_cell = {s["locator"]["cell"]: s for s in segments}
    assert by_cell["A1"]["data"]["value"] == "mass"
    assert by_cell["A2"]["data"]["value"] == 12.5
    assert by_cell["B2"]["data"] == {"value": 25, "cell_type": "n", "formula": "A2*2", "formula_status": "UNVERIFIED"}
    assert by_cell["C2"]["data"]["value"] is True
    assert by_cell["A2"]["locator"] == {"sheet": "Measurements", "cell": "A2", "row": 2, "column": "A"}


@pytest.mark.parametrize("suffix,fixture", [("docx", _docx), ("xlsx", _xlsx)])
def test_ooxml_rejects_external_relationships_paths_dtd_and_zip_bombs(suffix, fixture):
    external = '<Relationships><Relationship Id="evil" TargetMode="External" Target="https://example.invalid/tracker"/></Relationships>'
    _result("x." + suffix, fixture({"evil.rels": external}), "ERROR")
    for name in ("../escape", "/absolute", "C:/drive", "bad\\path", "x/./bad"):
        _result("x." + suffix, fixture({name: "bad"}), "ERROR")
    _result("x." + suffix, fixture({"bomb": "x" * 500_000}), "ERROR")
    _result("x." + suffix, b"PK\x03\x04broken", "ERROR")
    member = "word/document.xml" if suffix == "docx" else "xl/workbook.xml"
    _result("x." + suffix, fixture({member: '<!DOCTYPE x [<!ENTITY bomb "ha">]><x>&bomb;</x>'}), "ERROR")
    nul_archive = fixture({"badX.xml": "bad"}).replace(b"badX.xml", b"bad\x00.xml")
    _result("x." + suffix, nul_archive, "ERROR")


def test_xlsx_bad_cell_reference_nonfinite_and_relationship_escape():
    member = "xl/worksheets/sheet1.xml"
    for cell in ('<c r="XFE1"><v>2</v></c>', '<c r="A2"><v>2</v></c>', '<c r="A1"><v>NaN</v></c>', '<c r="A1" t="s"><v>999</v></c>'):
        xml = '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1">' + cell + '</row></sheetData></worksheet>'
        _result("x.xlsx", _xlsx({member: xml}), "ERROR")
    _result("x.xlsx", _xlsx({"xl/_rels/workbook.xml.rels": '<Relationships><Relationship Id="rId1" Target="../../outside.xml"/></Relationships>'}), "ERROR")


def test_ooxml_duplicate_members_and_symlinks():
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w") as archive:
        with pytest.warns(UserWarning):
            archive.writestr("word/document.xml", "first")
            archive.writestr("word/document.xml", "second")
    _result("x.docx", target.getvalue(), "ERROR")


def test_ooxml_unknown_compression_and_corrupt_deflate_fail_closed():
    # Patch both ZIP method fields without asking zipfile to emit an invalid ZIP.
    raw = _docx()
    raw = raw.replace(b"PK\x03\x04\x14\x00\x00\x00\x08\x00", b"PK\x03\x04\x14\x00\x00\x00\x63\x00")
    raw = raw.replace(b"PK\x01\x02\x14\x03\x14\x00\x00\x00\x08\x00", b"PK\x01\x02\x14\x03\x14\x00\x00\x00\x63\x00")
    _result("x.docx", raw, "ERROR")
    raw = bytearray(_docx())
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        member = archive.getinfo("word/document.xml")
        offset = member.header_offset + 30 + len(member.filename.encode()) + len(member.extra)
    raw[offset:offset + 4] = b"\xff\xff\xff\xff"
    _result("x.docx", bytes(raw), "ERROR")
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w") as archive:
        info = zipfile.ZipInfo("link")
        info.create_system = 3
        info.external_attr = 0o120777 << 16
        archive.writestr(info, "/etc/passwd")
    _result("x.docx", target.getvalue(), "ERROR")


def test_biological_formats_real_first_party_records_and_coordinates():
    fasta = _result("protein.fasta", b">chain_A example\nMAVKLE\nDELGKD\n")["segments"]
    assert fasta[0]["data"]["length"] == 12
    assert fasta[0]["locator"]["line_end"] == 3
    source = Path(__file__).parents[1] / "model_assurance_studio_v1" / "samples"
    pdb = _result("protein.pdb", (source / "demo_protein.pdb").read_bytes())["segments"]
    cif = _result("protein.cif", (source / "demo_protein.cif").read_bytes())["segments"]
    atoms = [s for s in cif if s["kind"] == "structure_atom"]
    assert len(pdb) == len(atoms) == 2
    assert pdb[1]["data"]["x"] == atoms[1]["data"]["x"] == 6.0
    assert atoms[1]["locator"]["chain"] == "A"
    assert atoms[1]["data"]["numeric_authority"] == "EXTRACTED_UNVERIFIED"


@pytest.mark.parametrize("name,raw", [("x.fa", b"NO_HEADER"), ("x.fa", b">id\nACG7\n"), ("x.fa", b">id\n"), ("x.pdb", b"ATOM      1 short\n"), ("x.cif", b"data_a\nloop_\n_atom_site.id\n_atom_site.Cartn_x\n1\n"), ("x.cif", b"data_a\n_tag.value\n;unclosed\n")])
def test_biological_malformed_inputs_fail_closed(name, raw):
    _result(name, raw, "ERROR")


def test_mmcif_quotes_semicolon_metadata_and_duplicate_fields():
    raw = b"data_demo\n_entry.id 'quoted value'\n_struct.title\n;line one\nline two\n;\nloop_\n_struct_asym.id\n_struct_asym.entity_id\nA 1\n"
    segments = _result("demo.cif", raw)["segments"]
    assert segments[0]["data"]["value"] == "quoted value"
    assert segments[1]["data"]["value"] == "line one\nline two"
    assert segments[2]["kind"] == "structure_chain"
    _result("bad.cif", raw + b"_entry.id duplicate\n", "ERROR")


def test_safetensors_header_only_and_no_pickle_loading(tmp_path):
    header = json.dumps({"__metadata__": {"producer": "first-party"}, "w": {"dtype": "F32", "shape": [2], "data_offsets": [0, 8]}}).encode()
    raw = struct.pack("<Q", len(header)) + header + struct.pack("<ff", 1.0, 2.0)
    segments = _result("weights.safetensors", raw)["segments"]
    assert segments[1]["data"]["shape"] == [2]
    assert segments[1]["data"]["weights_loaded"] is False
    _result("weights.safetensors", raw[:-1], "ERROR")
    marker = tmp_path / "NO_PICKLE_EXECUTION"
    malicious_pickle = f"cos\nsystem\n(S'touch {marker}'\ntR.".encode()
    for name in ("weights.pt", "weights.pth", "weights.pkl", "unknown.bin"):
        _result(name, malicious_pickle, "UNSUPPORTED")
    assert not marker.exists()


def test_onnx_real_protobuf_metadata_and_malformed_wire():
    # ModelProto {ir_version:8, producer_name:'PCS', graph:{name:'identity'}}.
    raw = b"\x08\x08\x12\x03PCS\x3a\x0a\x12\x08identity"
    segments = _result("model.onnx", raw)["segments"]
    values = {s["data"]["field"]: s["data"]["value"] for s in segments}
    assert values == {"ir_version": 8, "producer_name": "PCS", "graph.name": "identity"}
    assert all(s["data"]["graph_validated"] is False for s in segments)
    for bad in (b"", b"\x00", b"\x08\x80", raw[:-1], b"\x08\x08\x08\x09\x3a\x00"):
        _result("model.onnx", bad, "ERROR")


def test_input_segment_and_structure_limits_fail_closed(monkeypatch):
    _result("huge.txt", b"a" * (adapters.MAX_RAW_BYTES + 1), "ERROR")
    monkeypatch.setattr(adapters, "MAX_SEGMENTS", 2)
    _result("lines.txt", b"1\n2\n3\n", "ERROR")
    _result("array.json", b"[1,2,3]", "ERROR")
    _result("table.csv", b"a\n1\n2\n", "ERROR")


def test_invalid_api_types_and_unknown_formats_are_explicit():
    _result("x.exe", b"MZopaque", "UNSUPPORTED")
    assert adapters.extract("", b"x")["status"] == "ERROR"
    assert adapters.extract(None, b"x")["status"] == "ERROR"
    assert adapters.extract("x.txt", bytearray(b"x"))["status"] == "ERROR"
