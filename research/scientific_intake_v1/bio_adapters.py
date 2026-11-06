"""Bounded biological *data* readers, with no scientific certification implied.

The public helpers return source-located segments or raise ``ValueError``.  PDB
coordinates and mmCIF tables are parsed as supplied; neither geometry nor model
quality is inferred.  These readers do not load plugins or execute input code.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
import shlex
from typing import Any

MAX_TEXT = 5 * 1024 * 1024
MAX_LINES = 50_000
MAX_TOKENS = 100_000
MAX_SEGMENTS = 10_000
MAX_ATOMS = 10_000
_AUTHORITY = "EXTRACTED_UNVERIFIED"


def _lines(text: str) -> list[str]:
    if len(text) > MAX_TEXT:
        raise ValueError("biological text exceeds size bound")
    if "\x00" in text:
        raise ValueError("NUL byte in biological text")
    lines = text.splitlines()
    if len(lines) > MAX_LINES:
        raise ValueError("biological input exceeds line bound")
    return lines


def _add(out: list[dict[str, Any]], locator: dict[str, Any], text: str,
         kind: str, data: dict[str, Any]) -> None:
    if len(out) >= MAX_SEGMENTS:
        raise ValueError("biological input exceeds segment bound")
    out.append({"locator": locator, "text": text, "kind": kind, "data": data})


def extract_fasta(text: str) -> list[dict[str, Any]]:
    """Read FASTA records with IUPAC amino-acid/nucleotide symbols and gaps.

    The symbol union cannot determine a molecule's biological type.  ``alphabet``
    denotes compatibility with the stated alphabet, not a classification proof.
    """
    lines = _lines(text)
    out: list[dict[str, Any]] = []
    header: str | None = None
    start = 0
    last_sequence_line = 0
    pieces: list[str] = []
    amino = set("ACDEFGHIKLMNPQRSTVWYBXZJUO*-.")
    nucleotide = set("ACGTRYSWKMBDHVNU-.")

    def finish() -> None:
        if header is None:
            return
        sequence = "".join(pieces).upper()
        if not sequence:
            raise ValueError(f"empty FASTA sequence starting on line {start}")
        if not set(sequence) <= amino:
            raise ValueError(f"invalid FASTA sequence symbol near line {start}")
        identifier = header.split(None, 1)[0]
        _add(out, {"sequence_index": len(out) + 1, "sequence_id": identifier,
                   "line_start": start, "line_end": last_sequence_line},
             ">" + header + "\n" + sequence, "sequence",
             {"id": identifier, "description": header, "sequence": sequence,
              "length": len(sequence),
              "alphabet": "IUPAC_NUCLEOTIDE" if set(sequence) <= nucleotide
              else "IUPAC_AMINO_ACID", "numeric_authority": _AUTHORITY})

    for number, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            finish()
            header = line[1:].strip()
            if not header:
                raise ValueError(f"empty FASTA header on line {number}")
            start = number
            pieces = []
        else:
            if header is None:
                raise ValueError(f"FASTA sequence precedes header on line {number}")
            if any(ch.isspace() for ch in line):
                raise ValueError(f"embedded whitespace in FASTA line {number}")
            pieces.append(line)
            last_sequence_line = number
    finish()
    if not out:
        raise ValueError("no FASTA records")
    return out


def _integer(value: str, field: str, *, positive: bool = False) -> int:
    if not re.fullmatch(r"[+-]?[0-9]+", value.strip()):
        raise ValueError(f"invalid integer {field}")
    if len(value.strip()) > 16:
        raise ValueError(f"integer {field} exceeds bound")
    result = int(value)
    if positive and result < 1:
        raise ValueError(f"{field} must be positive")
    return result


def _number(value: str, field: str) -> float:
    if len(value) > 64:
        raise ValueError(f"numeric {field} exceeds bound")
    try:
        number = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"invalid numeric {field}") from exc
    if not math.isfinite(number):
        raise ValueError(f"non-finite numeric {field}")
    return number


def _optional_number(value: str, field: str) -> float | None:
    return _number(value, field) if value.strip() else None


def extract_pdb(text: str) -> list[dict[str, Any]]:
    """Read fixed-column ATOM/HETATM coordinates and SEQRES declarations."""
    out: list[dict[str, Any]] = []
    atoms = 0
    model = 1
    in_model = False
    for number, line in enumerate(_lines(text), 1):
        record = line[:6].strip()
        if record == "MODEL":
            if in_model:
                raise ValueError(f"nested PDB MODEL on line {number}")
            model = _integer(line[10:14].strip(), "PDB model", positive=True)
            in_model = True
        elif record == "ENDMDL":
            if not in_model:
                raise ValueError(f"PDB ENDMDL without MODEL on line {number}")
            in_model = False
        elif record in {"ATOM", "HETATM"}:
            if len(line) < 54:
                raise ValueError(f"short PDB atom record on line {number}")
            atoms += 1
            if atoms > MAX_ATOMS:
                raise ValueError("PDB atom count exceeds bound")
            serial = _integer(line[6:11], "PDB atom serial", positive=True)
            name, residue = line[12:16].strip(), line[17:20].strip()
            if not name or not residue:
                raise ValueError(f"missing PDB atom/residue name on line {number}")
            residue_number = _integer(line[22:26], "PDB residue number")
            chain = line[21:22].strip()
            insertion = line[26:27].strip()
            data = {"record": record, "serial": serial, "name": name,
                    "alt_loc": line[16:17].strip(), "residue_name": residue,
                    "chain": chain, "residue_number": residue_number,
                    "insertion_code": insertion,
                    "x": _number(line[30:38], "PDB x"),
                    "y": _number(line[38:46], "PDB y"),
                    "z": _number(line[46:54], "PDB z"),
                    "occupancy": _optional_number(line[54:60], "PDB occupancy"),
                    "temperature_factor": _optional_number(line[60:66], "PDB B factor"),
                    "element": line[76:78].strip(), "model": model,
                    "coordinate_unit": "angstrom", "numeric_authority": _AUTHORITY}
            _add(out, {"line": number, "model": model, "chain": chain,
                       "atom_serial": serial, "residue_number": residue_number,
                       "insertion_code": insertion}, line, "structure_atom", data)
        elif record == "SEQRES":
            if len(line) < 20:
                raise ValueError(f"short PDB SEQRES on line {number}")
            serial = _integer(line[7:10], "PDB SEQRES serial", positive=True)
            declared = _integer(line[13:17], "PDB SEQRES count", positive=True)
            residues = line[19:70].split()
            if not residues or any(not re.fullmatch(r"[A-Za-z0-9]{1,3}", x)
                                   for x in residues):
                raise ValueError(f"invalid PDB SEQRES residues on line {number}")
            chain = line[11:12].strip()
            _add(out, {"line": number, "chain": chain, "sequence_row": serial},
                 line, "structure_sequence",
                 {"chain": chain, "residues": residues,
                  "declared_residue_count": declared, "serial": serial,
                  "numeric_authority": _AUTHORITY})
    if in_model:
        raise ValueError("unterminated PDB MODEL")
    if not out:
        raise ValueError("no supported PDB atom or sequence records")
    return out


@dataclass(frozen=True)
class _Token:
    value: str
    line: int
    quoted: bool = False


def _cif_tokens(text: str) -> list[_Token]:
    """Tokenize a bounded CIF 1.1 subset, including semicolon text fields."""
    lines = _lines(text)
    tokens: list[_Token] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        number = index + 1
        if line.startswith(";"):
            parts = [line[1:]]
            index += 1
            while index < len(lines) and not lines[index].startswith(";"):
                parts.append(lines[index])
                index += 1
            if index == len(lines):
                raise ValueError(f"unterminated mmCIF text field on line {number}")
            if lines[index][1:].strip():
                raise ValueError("unexpected content after mmCIF text terminator")
            tokens.append(_Token("\n".join(parts), number, True))
        else:
            lexer = shlex.shlex(line, posix=False)
            lexer.whitespace_split = True
            lexer.commenters = "#"
            try:
                for token in lexer:
                    quoted = token.startswith(("'", '"'))
                    if quoted:
                        if len(token) < 2 or token[-1] != token[0]:
                            raise ValueError(f"malformed mmCIF quote on line {number}")
                        token = token[1:-1]
                    tokens.append(_Token(token, number, quoted))
                    if len(tokens) > MAX_TOKENS:
                        raise ValueError("mmCIF token count exceeds bound")
            except ValueError as exc:
                raise ValueError(f"invalid mmCIF token on line {number}: {exc}") from exc
        if len(tokens) > MAX_TOKENS:
            raise ValueError("mmCIF token count exceeds bound")
        index += 1
    return tokens


def _control(token: _Token) -> bool:
    value = token.value.lower()
    return not token.quoted and (value.startswith(("_", "data_", "save_"))
                                 or value in {"loop_", "stop_", "global_"})


def _missing(value: str) -> str | None:
    return None if value in {".", "?"} else value


def _cif_atom(row: dict[str, str]) -> dict[str, Any]:
    def get(*keys: str, default: str | None = None) -> str | None:
        for key in keys:
            value = _missing(row.get("_atom_site." + key.lower(), "?"))
            if value is not None:
                return value
        return default

    def require(*keys: str) -> str:
        value = get(*keys)
        if value is None:
            raise ValueError(f"missing mmCIF atom field {keys[0]}")
        return value

    def optional_float(key: str) -> float | None:
        value = get(key)
        return None if value is None else _number(value, "mmCIF " + key)

    residue_number = get("auth_seq_id", "label_seq_id")
    model_text = get("pdbx_PDB_model_num", default="1")
    record = get("group_PDB", default="ATOM")
    if record not in {"ATOM", "HETATM"}:
        raise ValueError("invalid mmCIF atom group_PDB")
    return {"record": record,
            "serial": _integer(require("id"), "mmCIF atom id", positive=True),
            "name": require("auth_atom_id", "label_atom_id"),
            "alt_loc": get("label_alt_id", default=""),
            "residue_name": require("auth_comp_id", "label_comp_id"),
            "chain": require("auth_asym_id", "label_asym_id"),
            "residue_number": None if residue_number is None else
            _integer(residue_number, "mmCIF residue number"),
            "insertion_code": get("pdbx_PDB_ins_code", default=""),
            "x": _number(require("Cartn_x"), "mmCIF x"),
            "y": _number(require("Cartn_y"), "mmCIF y"),
            "z": _number(require("Cartn_z"), "mmCIF z"),
            "occupancy": optional_float("occupancy"),
            "temperature_factor": optional_float("B_iso_or_equiv"),
            "element": get("type_symbol", default=""),
            "model": _integer(str(model_text), "mmCIF model", positive=True),
            "coordinate_unit": "angstrom", "numeric_authority": _AUTHORITY}


def extract_mmcif(text: str) -> list[dict[str, Any]]:
    """Read CIF 1.1 scalar/loop tables and interpret selected structure tables.

    Uninterpreted tables remain located ``structure_metadata`` rows.  CIF 2.0
    compound values and save frames are outside this deliberately bounded reader.
    """
    tokens = _cif_tokens(text)
    out: list[dict[str, Any]] = []
    index = 0
    block: str | None = None
    seen_blocks: set[str] = set()
    tags_seen: set[str] = set()
    atoms = 0
    while index < len(tokens):
        token = tokens[index]
        value = token.value.lower()
        if not token.quoted and value.startswith("data_"):
            block = token.value[5:]
            if not block or block.lower() in seen_blocks:
                raise ValueError("empty or duplicate mmCIF data block")
            seen_blocks.add(block.lower())
            tags_seen = set()
            index += 1
            continue
        if block is None:
            raise ValueError("mmCIF data must begin with a data_ block")
        if token.quoted:
            raise ValueError(f"unexpected mmCIF value on line {token.line}")
        if value.startswith("save_") or value == "global_":
            raise ValueError("mmCIF save frames/global blocks are unsupported")
        if value == "loop_":
            index += 1
            columns: list[str] = []
            while index < len(tokens) and not tokens[index].quoted and tokens[index].value.startswith("_"):
                tag = tokens[index].value.lower()
                if tag in tags_seen or tag in columns or "." not in tag:
                    raise ValueError("duplicate or malformed mmCIF loop tag")
                columns.append(tag)
                index += 1
            if not columns:
                raise ValueError("mmCIF loop without columns")
            category = columns[0].split(".", 1)[0]
            if any(col.split(".", 1)[0] != category for col in columns):
                raise ValueError("mmCIF loop mixes categories")
            tags_seen.update(columns)
            start = index
            while index < len(tokens) and not _control(tokens[index]):
                index += 1
            count = index - start
            if count == 0 or count % len(columns):
                raise ValueError("mmCIF loop has incomplete or empty rows")
            for offset in range(0, count, len(columns)):
                row_tokens = tokens[start + offset:start + offset + len(columns)]
                row = dict(zip(columns, (x.value for x in row_tokens)))
                row_number = offset // len(columns) + 1
                locator = {"line": row_tokens[0].line,
                           "line_end": row_tokens[-1].line,
                           "block": block, "category": category, "row": row_number}
                kind = "structure_metadata"
                data: dict[str, Any] = {"category": category, "values": row}
                if category == "_atom_site":
                    atoms += 1
                    if atoms > MAX_ATOMS:
                        raise ValueError("mmCIF atom count exceeds bound")
                    data = _cif_atom(row)
                    locator.update({"model": data["model"], "chain": data["chain"],
                                    "atom_serial": data["serial"],
                                    "residue_number": data["residue_number"],
                                    "insertion_code": data["insertion_code"]})
                    kind = "structure_atom"
                elif category == "_struct_asym":
                    chain = _missing(row.get("_struct_asym.id", "?"))
                    entity = _missing(row.get("_struct_asym.entity_id", "?"))
                    if chain is None or entity is None:
                        raise ValueError("missing mmCIF chain/entity identifier")
                    data = {"chain": chain, "entity_id": entity}
                    locator["chain"] = chain
                    kind = "structure_chain"
                elif category == "_entity_poly_seq":
                    entity = _missing(row.get("_entity_poly_seq.entity_id", "?"))
                    residue = _missing(row.get("_entity_poly_seq.mon_id", "?"))
                    if entity is None or residue is None:
                        raise ValueError("missing mmCIF polymer sequence field")
                    data = {"entity_id": entity,
                            "number": _integer(row.get("_entity_poly_seq.num", ""),
                                               "mmCIF sequence number", positive=True),
                            "residue_name": residue,
                            "hetero": _missing(row.get("_entity_poly_seq.hetero", "?")),
                            "numeric_authority": _AUTHORITY}
                    kind = "structure_sequence"
                _add(out, locator, " ".join(x.value for x in row_tokens), kind, data)
            if index < len(tokens) and not tokens[index].quoted and tokens[index].value.lower() == "stop_":
                index += 1
            continue
        if value.startswith("_"):
            if "." not in value or value in tags_seen:
                raise ValueError("duplicate or malformed mmCIF scalar tag")
            if index + 1 >= len(tokens) or _control(tokens[index + 1]):
                raise ValueError("missing mmCIF scalar value")
            scalar = tokens[index + 1]
            tags_seen.add(value)
            _add(out, {"line": token.line, "line_end": scalar.line,
                       "block": block, "tag": value},
                 token.value + " " + scalar.value, "structure_metadata",
                 {"tag": value, "value": _missing(scalar.value)})
            index += 2
            continue
        raise ValueError(f"unsupported mmCIF syntax on line {token.line}")
    if not out:
        raise ValueError("no mmCIF table or metadata records")
    return out
