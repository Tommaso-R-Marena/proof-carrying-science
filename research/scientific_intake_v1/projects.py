"""Reproducible, licensed upstream projects and explicitly derived intake cases.

Importing this module reads no fixture.  Materialization opens only the requested
split; callers must freeze components before requesting ``final`` or ``all``.
Downloaded source is copied byte for byte and is never imported or executed.
The annotations describe byte-level observations, not scientific acceptance.
"""
from __future__ import annotations

import argparse
import csv
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import re
from xml.sax.saxutils import escape
import zipfile

VERSION = "scientific-projects-v1.0"
UPSTREAM = Path(__file__).with_name("fixtures") / "upstream"
_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
_AMINO = dict(zip(
    "ALA ARG ASN ASP CYS GLN GLU GLY HIS ILE LEU LYS MET PHE PRO SER THR TRP TYR VAL".split(),
    "ARNDCQEGHILKMFPSTWYV"))
_SPECS = (
    {"id": "rcsb_1crn", "split": "development", "domain": "protein", "entry": "1CRN"},
    {"id": "nist_norris", "split": "development", "domain": "regression", "entry": "Norris", "degree": 1,
     "columns": ("y", "x", "temperature", "pressure")},
    {"id": "lean4_nat_add", "split": "development", "domain": "formal", "entry": "Nat", "theorem": "zero_add"},
    {"id": "rcsb_1ubq", "split": "final", "domain": "protein", "entry": "1UBQ"},
    {"id": "nist_pontius", "split": "final", "domain": "regression", "entry": "Pontius", "degree": 2,
     "columns": ("y", "x")},
    {"id": "lean4_list_append", "split": "final", "domain": "formal", "entry": "List", "theorem": "append_nil"},
)


def _json(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _decimal(value):
    """Render an exact terminating rational without rounding or float conversion."""
    value = Fraction(value)
    sign = "-" if value < 0 else ""
    numerator, denominator = abs(value.numerator), value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    if denominator != 1:
        raise ValueError("expected value is not a finite decimal")
    digits = max(twos, fives)
    integer = numerator * (10 ** digits) // value.denominator
    if not digits:
        return sign + str(integer)
    text = str(integer).zfill(digits + 1)
    return sign + (text[:-digits] + "." + text[-digits:]).rstrip("0").rstrip(".")


def _csv(headers, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue().encode()


def _zip(parts):
    """Fixed metadata keeps generated Office packages byte reproducible."""
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(parts.items()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return stream.getvalue()


def _docx(lines):
    paragraphs = "".join("<w:p><w:r><w:t xml:space=\"preserve\">" + escape(line) + "</w:t></w:r></w:p>" for line in lines)
    return _zip({
        "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        "_rels/.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        "word/document.xml": '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + paragraphs + '<w:sectPr/></w:body></w:document>',
    })


def _xlsx(rows):
    xml_rows = []
    for number, row in enumerate(rows, 1):
        cells = []
        for column, value in enumerate(row):
            reference = chr(65 + column) + str(number)
            # Strings preserve exact decimal source text; there are no formulas.
            cells.append(f'<c r="{reference}" t="inlineStr"><is><t xml:space="preserve">{escape(str(value))}</t></is></c>')
        xml_rows.append(f'<row r="{number}">' + "".join(cells) + "</row>")
    return _zip({
        "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        "_rels/.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Derived" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        "xl/worksheets/sheet1.xml": '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + "".join(xml_rows) + '</sheetData></worksheet>',
    })


def _pdf(lines):
    """Build a one-page, text-only PDF with byte-accurate cross references.

    This first-party derived fixture exercises text extraction. It represents no
    independently sourced paper, equation extraction, table extraction, or OCR.
    """
    escaped = [line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for line in lines]
    stream = ("BT /F1 11 Tf 72 720 Td 16 TL\n" + "\n".join("(" + line + ") Tj T*" for line in escaped) + "\nET\n").encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Count 1 /Kids [4 0 R] >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"endstream",
    ]
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


def _dataplot(raw, columns):
    lines = raw.decode("utf-8").splitlines()
    separator = next((i for i, line in enumerate(lines) if re.fullmatch(r"\s*-{5,}\s*", line)), None)
    if separator is None:
        raise ValueError("Dataplot observation separator missing")
    observations = []
    for number, line in enumerate(lines[separator + 1:], separator + 2):
        if not line.strip():
            continue
        values = line.split()
        if len(values) != len(columns) or any(not _NUMBER.fullmatch(value) for value in values):
            raise ValueError(f"unexpected Dataplot observation at line {number}")
        observations.append((number, values))
    if not observations:
        raise ValueError("no Dataplot observations")
    return observations


def ordinary_least_squares(rows, degree):
    """Independent exact normal-equation experiment, never a StRD certificate.

    Rows supply finite decimal x and y strings.  Chosen design columns are
    1,x,...,x**degree, not a claim to reproduce the source author's analysis.
    """
    if type(degree) is not int or not 0 <= degree <= 4:
        raise ValueError("degree outside bounded experiment")
    pairs = [(Fraction(row["x"]), Fraction(row["y"])) for row in rows]
    size = degree + 1
    if len(pairs) < size:
        raise ValueError("insufficient observations")
    design = [[x ** power for power in range(size)] for x, _ in pairs]
    matrix = [[sum((row[i] * row[j] for row in design), Fraction()) for j in range(size)] for i in range(size)]
    rhs = [sum((row[i] * pair[1] for row, pair in zip(design, pairs)), Fraction()) for i in range(size)]
    augmented = [row[:] + [rhs[i]] for i, row in enumerate(matrix)]
    for column in range(size):
        pivot = next((r for r in range(column, size) if augmented[r][column]), None)
        if pivot is None:
            raise ValueError("singular design")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row != column:
                factor = augmented[row][column]
                augmented[row] = [a - factor * b for a, b in zip(augmented[row], augmented[column])]
    coefficients = [row[-1] for row in augmented]
    residuals = [y - sum((b * term for b, term in zip(coefficients, row)), Fraction()) for row, (_, y) in zip(design, pairs)]
    return {"status": "DERIVED_EXACT_OLS_EXPERIMENT", "certified": False,
            "method": "exact-rational Gaussian elimination of normal equations",
            "design": ["1"] + ["x" if i == 1 else f"x^{i}" for i in range(1, size)],
            "degree": degree, "observations": len(pairs),
            "coefficients_rational": [str(value) for value in coefficients],
            "sse_rational": str(sum((r * r for r in residuals), Fraction())),
            "normal_equations_exact": all(sum((matrix[i][j] * coefficients[j] for j in range(size)), Fraction()) == rhs[i] for i in range(size)),
            "interpretation": "A deterministic fit of the declared derived design; no causal inference, source certification, or scientific acceptance."}


class _Builder:
    def __init__(self, root, spec, metadata):
        self.root, self.spec, self.metadata = root, spec, metadata
        self.files, self.sources, self.claims = [], [], []
        root.mkdir(parents=True)

    def write(self, path, raw, *, status="DERIVED", dependencies=(), locator=None):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        record = {"path": path, "sha256": _sha(raw), "byte_count": len(raw), "status": status,
                  "dependencies": list(dependencies), "transform": VERSION if status == "DERIVED" else "byte-preserving-copy"}
        descriptions = {
            "data.csv": {"protein": "Concatenate FASTA sequence lines; count all PDB ATOM/HETATM records and distinct chain-A ATOM residue keys.",
                         "regression": "Copy every whitespace-delimited numeric observation after the Dataplot separator into CSV, preserving numeric strings and order.",
                         "formal": "Copy the first exact source line declaring the specified contextual theorem into a CSV record."}.get(self.spec.get("domain")),
            "data_lineage.json": "Map each derived CSV row to its original Dataplot physical line number.",
            "ols_experiment.json": "Fit the frozen polynomial degree with exact-rational Gaussian elimination of normal equations; compute exact residual SSE.",
            "source_excerpt.txt": "Copy the contextual theorem source line with an explicit derived/data-only header.",
            "config.json": "Serialize fixed research configuration and case identifier; no model training or execution.",
            "analysis.py": "Instantiate fixed unexecuted CSV-reading example source, without importing it.",
            "claims.md": "Instantiate frozen exact-observation directives and negative scientific-meaning fixtures from source-derived counts, strings, and sums.",
            "analysis.ipynb": "Package a fixed reading notebook with unexecuted code and no stored outputs.",
            "summary.docx": "Encode a derived case identifier and table-row summary as OOXML paragraphs.",
            "summary.xlsx": "Encode a derived case identifier and table-row summary as exact inline OOXML strings; no formulas.",
            "summary.pdf": "Encode a first-party derived project summary as plain text in a valid PDF with byte-accurate cross references; no independently sourced paper, equations, tables, or OCR.",
            "context.json": "Serialize the explicitly labeled derived domain observations and exact source quotations.",
            "source_lineage.json": "Serialize source metadata and preceding artifact transformation records, excluding this file to avoid a self-referential digest.",
        }
        record["transformation"] = {"version": VERSION, "execution": "NONE",
                                    "description": "Byte-identical copy; original SHA-256 verified against download metadata." if status == "UPSTREAM" else descriptions.get(path, "Serialize explicitly derived research data.")}
        if locator:
            record["source_locator"] = locator
        self.files.append(record)
        return record

    def source(self, name, *, license=False):
        if name not in self.metadata:
            raise ValueError("source missing recorded provenance: " + name)
        raw = (UPSTREAM / name).read_bytes()
        provenance = self.metadata[name]
        if _sha(raw) != provenance["sha256"] or len(raw) != provenance["byte_count"]:
            raise ValueError("source no longer matches recorded provenance: " + name)
        path = ("licenses/" if license else "source/") + name
        self.write(path, raw, status="UPSTREAM")
        self.sources.append({**provenance, "original_path": name, "path": path, "status": "UPSTREAM", "modified": False})
        return raw, path

    def claim(self, statement, status, checker, *, truth=None, dependencies=(), rationale=""):
        self.claims.append({"statement": statement, "expected_status": status, "expected": status,
                            "expected_truth": truth, "checker": checker, "source_bindings": list(dependencies),
                            "rationale": rationale, "verification_only": True, "scientific_acceptance": False})


def _binding(builder, path, locator):
    record = next(record for record in builder.files if record["path"] == path)
    return {"path": path, "sha256": record["sha256"], "locator": locator}


def _protein(builder):
    entry = builder.spec["entry"]
    fasta, fasta_path = builder.source(entry + ".fasta")
    pdb, pdb_path = builder.source(entry + ".pdb")
    builder.source(entry + ".cif")
    builder.source("wwpdb_usage_policy.html", license=True)
    builder.source("rcsb_policy.html", license=True)
    lines = fasta.decode().splitlines()
    identifier = lines[0][1:].split()[0]
    sequence = "".join(line.strip() for line in lines[1:] if line.strip())
    atom_lines = [(i, line) for i, line in enumerate(pdb.decode().splitlines(), 1) if line[:6].strip() in {"ATOM", "HETATM"}]
    residues = {}
    for _, line in atom_lines:
        if line[:6].strip() == "ATOM" and line[21:22].strip() == "A":
            key = (int(line[22:26]), line[26:27].strip())
            name = line[17:20].strip()
            if key in residues and residues[key] != name:
                raise ValueError("conflicting source residue identities")
            residues[key] = name
    structural_sequence = "".join(_AMINO[residues[key]] for key in sorted(residues))
    dependencies = [_binding(builder, fasta_path, {"line_start": 1, "line_end": len(lines)}),
                    _binding(builder, pdb_path, {"line_start": atom_lines[0][0], "line_end": atom_lines[-1][0]})]
    rows = [[identifier, sequence, str(len(sequence)), str(len(residues)), str(len(atom_lines))]]
    builder.write("data.csv", _csv(["sequence_id", "sequence", "length", "structural_residues", "coordinates"], rows), dependencies=dependencies)
    builder.claim(f"PCS-CLAIM: sequence_length({entry}.fasta,{identifier})={len(sequence)}", "VERIFIED_SUPPORTED", "sequence_length", truth=True, dependencies=dependencies[:1])
    builder.claim(f"PCS-CLAIM: sequence_length({entry}.fasta,{identifier})={len(sequence) + 1}", "REFUTED", "sequence_length", truth=False, dependencies=dependencies[:1])
    builder.claim(f"PCS-CLAIM: coordinate_count({entry}.pdb)={len(atom_lines)}", "VERIFIED_SUPPORTED", "coordinate_count", truth=True, dependencies=dependencies[1:])
    builder.claim(f"PCS-CLAIM: sequence_matches_structure({entry}.fasta,{entry}.pdb,A)=true", "VERIFIED_SUPPORTED" if sequence == structural_sequence else "REFUTED", "sequence_matches_structure", truth=sequence == structural_sequence, dependencies=dependencies)
    builder.claim(f"PCS-CLAIM: sequence_matches_structure({entry}.fasta,{entry}.pdb,A)=false", "REFUTED" if sequence == structural_sequence else "VERIFIED_SUPPORTED", "sequence_matches_structure", truth=sequence != structural_sequence, dependencies=dependencies)
    builder.claim("The deposited crystal structure proves that this protein causes disease in humans.", "UNSUPPORTED", "unsupported", dependencies=dependencies,
                  rationale="Structure and sequence bytes do not establish disease causation.")
    metadata_lines = [(i, line) for i, line in enumerate(pdb.decode().splitlines(), 1) if line.startswith("EXPDTA") or line.startswith("REMARK   2 RESOLUTION.")]
    return {"spdx": "CC0-1.0", "scope": "PDB archive data; policy pages retain their own terms", "evidence": ["licenses/wwpdb_usage_policy.html", "licenses/rcsb_policy.html"]}, rows, {
        "sequence_length": len(sequence), "structural_residues": len(residues), "coordinate_records": len(atom_lines),
        "measurement_metadata": [{"path": pdb_path, "line": i, "quote": line} for i, line in metadata_lines],
        "derivation": "FASTA concatenation and fixed-column PDB coordinate/residue counting; no structure quality or causal judgment."}


def _regression(builder):
    raw, path = builder.source(builder.spec["entry"] + ".dat")
    builder.source("nist_LICENSE.txt", license=True)
    builder.source("nist_README.md", license=True)
    observations = _dataplot(raw, builder.spec["columns"])
    dependencies = [_binding(builder, path, {"line_start": observations[0][0], "line_end": observations[-1][0]})]
    rows = [values for _, values in observations]
    builder.write("data.csv", _csv(builder.spec["columns"], rows), dependencies=dependencies)
    builder.write("data_lineage.json", _json({"status": "DERIVED", "source": path, "rows": [{"csv_row": i + 2, "source_line": number} for i, (number, _) in enumerate(observations)]}), dependencies=dependencies)
    total = sum((Fraction(row[0]) for row in rows), Fraction())
    builder.claim(f"PCS-CLAIM: rows(data.csv)={len(rows)}", "VERIFIED_SUPPORTED", "csv_rows", truth=True, dependencies=dependencies)
    builder.claim(f"PCS-CLAIM: rows(data.csv)={len(rows) + 1}", "REFUTED", "csv_rows", truth=False, dependencies=dependencies)
    builder.claim(f"PCS-CLAIM: sum(data.csv,y)={_decimal(total)}", "VERIFIED_SUPPORTED", "csv_numeric", truth=True, dependencies=dependencies)
    builder.claim(f"PCS-CLAIM: sum(data.csv,y)={_decimal(total + 1)}", "REFUTED", "csv_numeric", truth=False, dependencies=dependencies)
    try:
        average = _decimal(total / len(rows))
    except ValueError:
        average = None
    if average is not None:
        builder.claim(f"PCS-CLAIM: mean(data.csv,y)={average}", "VERIFIED_SUPPORTED", "csv_numeric", truth=True, dependencies=dependencies)
    builder.claim("The calibration correlation proves that changing the reference device causes the guest response.", "UNSUPPORTED", "unsupported", dependencies=dependencies,
                  rationale="The supplied calibration observations and OLS fit do not identify a causal intervention.")
    experiment = ordinary_least_squares([dict(zip(builder.spec["columns"], row)) for row in rows], builder.spec["degree"])
    builder.write("ols_experiment.json", _json(experiment), dependencies=dependencies)
    fit_bindings = dependencies + [_binding(builder, "data.csv", {"row_start": 1, "row_end": len(rows) + 1}),
                                   _binding(builder, "ols_experiment.json", {"json_pointer": ""})]
    builder.claim("PCS-CLAIM: ols_optimality(data.csv,ols_experiment.json)=true", "VERIFIED_SUPPORTED", "ols_optimality", truth=True,
                  dependencies=fit_bindings, rationale="Exact independently recomputed residual normal equations and SSE for the declared polynomial model; no coefficient uniqueness, design-rank, upstream certification or causation claim.")
    builder.claim("PCS-CLAIM: ols_optimality(data.csv,ols_experiment.json)=false", "REFUTED", "ols_optimality", truth=False,
                  dependencies=fit_bindings, rationale="Deliberately false negation of the same bounded exact regression check.")
    return {"spdx": "NIST-PD", "scope": "Official usnistgov/dataplot archived data; not StRD certified results", "evidence": ["licenses/nist_LICENSE.txt"], "notice_url": "https://spdx.org/licenses/NIST-PD.html"}, rows, {
        "observations": len(rows), "columns": list(builder.spec["columns"]), "degree": builder.spec["degree"],
        "dataset_variant": "Dataplot archive pinned by preregistration amendment; no StRD certified coefficient claim.",
        "ols_experiment": experiment}


def _formal(builder):
    raw, path = builder.source("lean4_" + builder.spec["entry"] + "_Basic.lean")
    builder.source("lean4_LICENSE", license=True)
    builder.source("lean4_README.md", license=True)
    lines = raw.decode().splitlines()
    pattern = re.compile(r"\btheorem\s+" + builder.spec["theorem"] + r"\b")
    matches = [(i, line) for i, line in enumerate(lines, 1) if pattern.search(line)]
    if not matches:
        raise ValueError("preregistered source context lacks expected contextual theorem")
    number, quote = matches[0]
    dependencies = [_binding(builder, path, {"line": number, "quote": quote})]
    rows = [[builder.spec["entry"] + "." + builder.spec["theorem"], str(number), quote]]
    builder.write("data.csv", _csv(["theorem", "source_line", "exact_source_quote"], rows), dependencies=dependencies)
    builder.write("source_excerpt.txt", ("DERIVED source quotation; submitted Lean is data only.\n" + quote + "\n").encode(), dependencies=dependencies)
    positive = 'For all natural numbers n, n + 0 = n.' if builder.spec['entry']=='Nat' else 'For all lists of natural numbers xs, xs appended to the empty list = xs.'
    negative = 'For all natural numbers n, n + 0 = n + 1.' if builder.spec['entry']=='Nat' else 'For all lists of natural numbers xs, xs appended to the empty list = the empty list.'
    builder.claim(positive, "VERIFIED_SUPPORTED", "lean_closed", truth=True, dependencies=dependencies,
                  rationale="Auxiliary typed identity, independently proved; imported Lean source is not executed.")
    builder.claim(negative, "UNKNOWN", "lean_closed", truth=False, dependencies=dependencies,
                  rationale="Deliberately strengthened false identity; failed bounded proof attempts alone cannot refute a theorem.")
    builder.claim("The quoted theorem proves that every scientific model is correct.", "UNSUPPORTED", "unsupported", dependencies=dependencies,
                  rationale="A formal theorem does not establish the correctness or meaning of a scientific model.")
    context = {"theorem": builder.spec["entry"] + "." + builder.spec["theorem"], "source_quote": quote,
               "source_line": number, "imported_source_executed": False,
               "auxiliary_proposition": positive,
               "relationship": "Derived typed instance, independently reconstructed; original polymorphic source and proof are not executed or certified."}
    if builder.spec["entry"] == "Nat":
        context["preregistration_limit"] = "Frozen Nat.add_zero is referenced but not declared in this downloaded file; exact contextual quotation is Nat.zero_add. The auxiliary add_zero proposition is labeled derived."
    return {"spdx": "Apache-2.0", "scope": "Original Lean4 source and retained copyright notices", "evidence": ["licenses/lean4_LICENSE"]}, rows, context


def materialize_projects(output, split="development"):
    """Create selected cases and return their provenance/annotation records.

    ``final`` and ``all`` are explicit evaluation operations: call only after the
    caller has frozen its component choices. Existing output is never overwritten.
    No training, project code execution, network access, or source mutation occurs.
    """
    if split not in {"development", "final", "all"}:
        raise ValueError("split must be development, final, or all")
    output = Path(output).absolute()
    if output.exists():
        raise FileExistsError("refuse materialization overwrite")
    if output.resolve().is_relative_to(UPSTREAM.resolve()):
        raise ValueError("output cannot be inside original source fixtures")
    metadata = {entry["path"]: entry for entry in json.loads((UPSTREAM / "source_provenance.json").read_text())}
    registration = json.loads((UPSTREAM / "preregistration.json").read_text())
    registered = {case["id"]: case["split"] for case in registration["cases"]}
    if registered != {spec["id"]: spec["split"] for spec in _SPECS}:
        raise ValueError("frozen case IDs or split changed")
    output.mkdir(parents=True)
    records = []
    for spec in _SPECS:
        if split != "all" and spec["split"] != split:
            continue
        builder = _Builder(output / spec["id"], spec, metadata)
        license_info, rows, context = {"protein": _protein, "regression": _regression, "formal": _formal}[spec["domain"]](builder)
        config = {"status": "DERIVED", "case_id": spec["id"], "domain": spec["domain"],
                  "training_permitted": False, "source_code_execution": "NEVER", "scientific_acceptance": False}
        builder.write("config.json", _json(config), dependencies=builder.sources)
        script = ('"""DERIVED example analysis source. Intake must never execute this file."""\n'
                  'import csv\n\ndef read_rows(path):\n    with open(path, newline="") as stream:\n        return list(csv.DictReader(stream))\n')
        builder.write("analysis.py", script.encode(), dependencies=builder.sources)
        builder.claim("PCS-CLAIM: has_field(config.json,/case_id)=true", "VERIFIED_SUPPORTED", "json_field", truth=True,
                      dependencies=[_binding(builder, "config.json", {"json_pointer": "/case_id"})])
        builder.claim("PCS-CLAIM: has_field(config.json,/invented_certificate)=true", "REFUTED", "json_field", truth=False,
                      dependencies=[_binding(builder, "config.json", {"json_pointer": "/invented_certificate"})])
        builder.claim("PCS-CLAIM: imports(analysis.py,csv)=true", "VERIFIED_SUPPORTED", "python_import", truth=True,
                      dependencies=[_binding(builder, "analysis.py", {"line": 2})])
        builder.claim("PCS-CLAIM: imports(analysis.py,subprocess)=true", "REFUTED", "python_import", truth=False,
                      dependencies=[_binding(builder, "analysis.py", {"line_start": 1, "line_end": 7})])
        notes = ["# DERIVED intake claims", "All statements below are evaluator fixtures derived from preserved upstream bytes.",
                 "They are not independently sourced studies or scientific acceptance certificates."] + [claim["statement"] for claim in builder.claims]
        notes_record = builder.write("claims.md", ("\n".join(notes) + "\n").encode(), dependencies=builder.sources)
        annotations = []
        for number, claim in enumerate(builder.claims, 4):
            annotations.append({**claim, "id": spec["id"] + ":" + str(number - 3),
                                "origin": {"status": "DERIVED", "path": "claims.md", "sha256": notes_record["sha256"],
                                           "locator": {"line": number}, "quote": claim["statement"]},
                                "source_path": "claims.md", "locator": {"line": number}})
        notebook = {"nbformat": 4, "nbformat_minor": 5, "metadata": {"status": "DERIVED", "source_execution": "NEVER"}, "cells": [
            {"cell_type": "markdown", "metadata": {}, "source": "DERIVED reading notebook for " + spec["id"] + ". Source bytes and exact locators are retained."},
            {"cell_type": "code", "metadata": {}, "source": "import csv\n# Source shown as data; no execution or output is claimed.\n", "execution_count": None, "outputs": []}]}
        builder.write("analysis.ipynb", _json(notebook), dependencies=builder.sources)
        builder.write("summary.docx", _docx(["DERIVED project summary", spec["id"], "All imported code is data only; source provenance is preserved.", "Rows in the derived table: " + str(len(rows))]), dependencies=builder.sources)
        builder.write("summary.xlsx", _xlsx([["DERIVED", spec["id"]], ["derived_table_rows", len(rows)], ["source_execution", "NEVER"]]), dependencies=builder.sources)
        builder.write("summary.pdf", _pdf([
            "DERIVED project summary",
            "Case: " + spec["id"],
            "First-party generated intake fixture; not an independently sourced paper.",
            "Rows in the derived table: " + str(len(rows)),
            "Imported code is data only; no submitted source was executed.",
            "Scope: plain text extraction only; no PDF equations, tables, or OCR.",
            "Recorded observations do not establish scientific acceptance.",
        ]), dependencies=builder.sources)
        builder.write("context.json", _json({"status": "DERIVED", **context}), dependencies=builder.sources)
        lineage_sources = []
        for source in builder.sources:
            source_license = license_info
            if source["original_path"].endswith(".html"):
                source_license = {"spdx": "NOASSERTION", "scope": "Policy webpage retained as license evidence; the archive data policy is recorded separately."}
            lineage_sources.append({**source, "license": source_license})
        builder.write("source_lineage.json", _json({
            "format": "pcs-proposed-source-lineage-v1", "status": "DERIVED_PROPOSED_TRANSFORMATION_METADATA",
            "authority": False, "scientific_acceptance": False, "version": VERSION,
            "case_id": spec["id"], "split": spec["split"], "license": license_info,
            "source_provenance": lineage_sources, "files": list(builder.files),
            "self_digest_policy": "This file lists preceding artifacts only; its own digest is in the external project manifest and intake snapshot inventory.",
            "scope": "Recorded download provenance and proposed deterministic derivations; import does not authenticate the publisher or grant acceptance."
        }), dependencies=builder.sources)
        manifest = {"format": "pcs-derived-project-v1", "version": VERSION, "case_id": spec["id"], "split": spec["split"],
                    "training": [], "training_permitted": False, "source_code_executed": False,
                    "files": builder.files, "original_source_preserved": True, "scientific_acceptance": False}
        # Keep evaluator labels outside the ingested project; they are not evidence.
        metadata_path = output / "metadata" / (spec["id"] + ".json")
        metadata_path.parent.mkdir(exist_ok=True)
        record = {"id": spec["id"], "split": spec["split"], "domain": spec["domain"], "path": str(builder.root),
                  "license": license_info, "source_provenance": builder.sources, "annotations": annotations,
                  "manifest": manifest, "training_permitted": False,
                  "annotation_sha256": _sha(_json(annotations))}
        metadata_path.write_bytes(_json(record))
        records.append(record)
    (output / "projects.json").write_bytes(_json(records))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--split", choices=("development", "final", "all"), default="development")
    args = parser.parse_args()
    records = materialize_projects(args.output, args.split)
    print(json.dumps([{key: record[key] for key in ("id", "split", "path", "annotation_sha256")} for record in records], indent=2))


if __name__ == "__main__":
    main()
