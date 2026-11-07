"""Source-bound correspondence proposals with no scientific authority.

Only explicit source pointers and bounded PEtab v1 configuration links authorize
cross-file candidates. Bare repeated identifiers never establish identity.
"""
from __future__ import annotations

import csv
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import io
import json
from pathlib import PurePosixPath
import re

from research.scientific_semantics_v3 import semantics
from research.scientific_understanding_v2.interpretation import parse_expression, Unsupported

VERSION = "scientific-correspondence/v4.0"
MAX_FILES = 256
MAX_FILE = 1_000_000
MAX_TOTAL = 16_000_000
MAX_NODES = 8192
MAX_DEPTH = 16
MAX_RECORDS = 6000
_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _path(value):
    if (not isinstance(value, str) or not value or len(value.encode()) > 4096
            or any(ord(c) < 32 for c in value) or any(c in value for c in "\\:?#%")
            or value.startswith("/") or any(p in {"", ".", ".."} for p in value.split("/"))):
        raise ValueError("noncanonical, unsafe or nonrelative source path")
    return value


def _artifacts(artifacts):
    if not isinstance(artifacts, dict) or len(artifacts) > MAX_FILES:
        raise ValueError("artifact mapping/file-count bound")
    total = 0
    for path, raw in artifacts.items():
        _path(path)
        if type(raw) is not bytes or len(raw) > MAX_FILE:
            raise ValueError("artifact bytes/file-size bound")
        total += len(raw)
    if total > MAX_TOTAL:
        raise ValueError("artifact total-byte bound")
    return artifacts


def _source(path, raw, start=0, end=None):
    end = len(raw) if end is None else end
    quote = raw[start:end].decode("utf-8", errors="strict")
    sha = hashlib.sha256(raw).hexdigest()
    return {"path": path, "sha256": sha,
            "artifact_id": "artifact-" + semantics.digest([path, sha])[:24],
            "byte_start": start, "byte_end": end, "quote": quote,
            "locator": {"line_start": raw[:start].count(b"\n") + 1,
                        "line_end": raw[:end].count(b"\n") + 1}}


def _text_source(path, raw, text, start, end):
    return _source(path, raw, len(text[:start].encode()), len(text[:end].encode()))


def verify_source(source, artifacts):
    """Verify a nonempty exact UTF-8 interval against the supplied bytes."""
    try:
        raw = artifacts[source["path"]]
        a, b = source["byte_start"], source["byte_end"]
        return (type(a) is int and type(b) is int and 0 <= a < b <= len(raw)
                and hashlib.sha256(raw).hexdigest() == source["sha256"]
                and raw[a:b].decode("utf-8") == source["quote"])
    except (KeyError, TypeError, UnicodeError):
        return False


@dataclass
class _Node:
    value: object
    start: int
    end: int
    children: object = field(default_factory=dict)


class _Literals:
    """Small literal reader; no general YAML loader or object construction."""
    def __init__(self, text):
        self.text = text
        self.count = 0

    def node(self, value, start, end, children=None):
        self.count += 1
        if self.count > MAX_NODES:
            raise ValueError("configuration node bound")
        return _Node(value, start, end, {} if children is None else children)

    def scalar(self, token, start, *, json_only=False):
        token = token.strip()
        if not token or len(token) > 4096:
            raise ValueError("empty/excessive configuration literal")
        if token.startswith('"'):
            try:
                value = json.loads(token)
            except (ValueError, RecursionError) as exc:
                raise ValueError("invalid quoted literal") from exc
            if not isinstance(value, str):
                raise ValueError("string literal required")
        elif token.startswith("'") and not json_only:
            if len(token) < 2 or not token.endswith("'") or "'" in token[1:-1].replace("''", ""):
                raise ValueError("invalid single-quoted literal")
            value = token[1:-1].replace("''", "'")
        elif re.fullmatch(r"-?(?:0|[1-9][0-9]*)", token):
            if len(token) > 16:
                raise ValueError("integer literal bound")
            value = int(token)
        elif not json_only and re.fullmatch(r"[A-Za-z0-9_./-]+", token):
            if token.lower() in {"true", "false", "null", "yes", "no", "on", "off", "nan", "inf"}:
                raise ValueError("ambiguous YAML literal")
            value = token
        else:
            raise ValueError("unsupported configuration literal")
        return self.node(value, start, start + len(token))

    def flow(self, token, start, depth=0, *, json_only=False):
        if depth > MAX_DEPTH:
            raise ValueError("configuration depth bound")
        if not token.startswith("["):
            return self.scalar(token, start, json_only=json_only)
        if not token.endswith("]"):
            raise ValueError("unterminated flow list")
        body = token[1:-1]
        pieces, begin, quote = [], 0, None
        for i, c in enumerate(body):
            if quote:
                if c == quote and (i == 0 or body[i-1] != "\\"):
                    quote = None
            elif c in "\"'":
                quote = c
            elif c in "[]{}":
                raise ValueError("nested YAML flow collections unsupported")
            elif c == ",":
                pieces.append((begin, body[begin:i])); begin = i + 1
        if quote:
            raise ValueError("unterminated flow quote")
        pieces.append((begin, body[begin:]))
        children = []
        if body.strip():
            for offset, part in pieces:
                if not part.strip():
                    raise ValueError("empty flow list item")
                leading = len(part) - len(part.lstrip())
                children.append(self.scalar(part.strip(), start + 1 + offset + leading,
                                            json_only=json_only))
        return self.node([c.value for c in children], start, start+len(token), children)

    def yaml(self):
        lines, offset = [], 0
        for original in self.text.splitlines(keepends=True):
            line = original.rstrip("\r\n")
            if "\t" in line or "\x00" in line:
                raise ValueError("tabs/NUL forbidden in configuration")
            indent = len(line)-len(line.lstrip(" "))
            content = line[indent:]
            # Comments are accepted only outside quoted scalars/flow strings.
            quote = None
            for i, c in enumerate(content):
                if quote:
                    if c == quote and (i == 0 or content[i-1] != "\\"):
                        quote = None
                elif c in "\"'":
                    quote = c
                elif c == "#" and (i == 0 or content[i-1].isspace()):
                    content = content[:i].rstrip(); break
            if content:
                if indent % 2 or content.startswith(("---", "...", "%", "!", "&", "*")):
                    raise ValueError("unsupported YAML directive/tag/anchor/indentation")
                if content.startswith("- ") and ":" in content[2:]:
                    lines.append((indent, "-", offset+indent))
                    lines.append((indent+2, content[2:], offset+indent+2))
                else:
                    lines.append((indent, content, offset+indent))
            offset += len(original)
        if not lines or lines[0][0] != 0:
            raise ValueError("configuration requires a root mapping")

        def block(index, indent, depth):
            if depth > MAX_DEPTH:
                raise ValueError("configuration depth bound")
            sequence = lines[index][1] == "-" or lines[index][1].startswith("- ")
            children = [] if sequence else {}
            first = lines[index][2]
            while index < len(lines) and lines[index][0] == indent:
                _, content, start = lines[index]
                if sequence:
                    if not (content == "-" or content.startswith("- ")):
                        break  # End of a standard YAML indentless sequence.
                    token = content[1:].strip()
                    value_start = start + len(content)-len(token)
                    key = None
                else:
                    if ":" not in content:
                        raise ValueError("mapping key required")
                    key, token = content.split(":", 1)
                    if not _KEY.fullmatch(key) or key in children:
                        raise ValueError("invalid or duplicate configuration key")
                    token = token.strip()
                    value_start = start + len(content)-len(token)
                index += 1
                if token:
                    child = self.flow(token, value_start, depth+1)
                else:
                    indentless = (not sequence and index < len(lines) and lines[index][0] == indent
                                  and (lines[index][1] == "-" or lines[index][1].startswith("- ")))
                    if index >= len(lines) or (lines[index][0] <= indent and not indentless):
                        raise ValueError("missing configuration value")
                    child, index = block(index, lines[index][0], depth+1)
                if sequence:
                    children.append(child)
                else:
                    children[key] = child
                if index < len(lines) and lines[index][0] > indent:
                    raise ValueError("ambiguous configuration indentation")
            values = [c.value for c in children] if sequence else {k:c.value for k,c in children.items()}
            last = (children[-1] if sequence else list(children.values())[-1]).end
            return self.node(values, first, last, children), index

        root, index = block(0, 0, 0)
        if index != len(lines):
            raise ValueError("unconsumed configuration block")
        return root

    def json(self):
        # Recursive JSON reader preserves scalar intervals and duplicate keys.
        text = self.text
        def whitespace(i):
            while i < len(text) and text[i] in " \r\n\t": i += 1
            return i
        def read(i, depth):
            if depth > MAX_DEPTH:
                raise ValueError("configuration depth bound")
            i = whitespace(i); start = i
            if i >= len(text): raise ValueError("missing JSON value")
            if text[i] in "[{":
                mapping = text[i] == "{"; close = "}" if mapping else "]"
                children = {} if mapping else []; i = whitespace(i+1)
                if i < len(text) and text[i] == close:
                    return self.node({} if mapping else [], start, i+1, children), i+1
                while True:
                    if mapping:
                        keynode, i = read(i, depth+1)
                        key = keynode.value
                        if not isinstance(key, str) or not _KEY.fullmatch(key) or key in children:
                            raise ValueError("invalid or duplicate JSON key")
                        i = whitespace(i)
                        if i >= len(text) or text[i] != ":": raise ValueError("JSON colon required")
                        i += 1
                    child, i = read(i, depth+1)
                    if mapping: children[key] = child
                    else: children.append(child)
                    i = whitespace(i)
                    if i >= len(text): raise ValueError("unterminated JSON collection")
                    if text[i] == close: break
                    if text[i] != ",": raise ValueError("JSON comma required")
                    i = whitespace(i+1)
                value = {k:c.value for k,c in children.items()} if mapping else [c.value for c in children]
                return self.node(value, start, i+1, children), i+1
            if text[i] == '"':
                match = re.match(r'"(?:[^"\\\x00-\x1f]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*"', text[i:])
                if not match: raise ValueError("invalid JSON string")
                token = match[0]
            else:
                match = re.match(r"-?(?:0|[1-9][0-9]*)", text[i:])
                if not match: raise ValueError("unsupported JSON scalar")
                token = match[0]
            return self.scalar(token, i, json_only=True), i+len(token)
        root, end = read(0, 0)
        if whitespace(end) != len(text): raise ValueError("trailing JSON configuration content")
        return root


def _config_candidates(artifacts):
    for path, raw in sorted(artifacts.items()):
        if PurePosixPath(path).suffix.lower() in {".yaml", ".yml", ".json"} and re.search(
                rb"(?:format_version|sbml_files|measurement_files|observable_files)\s*[\"']?\s*:", raw):
            yield path, raw


def _parse_config(path, raw, artifacts):
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ValueError("configuration must be strict UTF-8") from exc
    if "\x00" in text:
        raise ValueError("configuration NUL forbidden")
    parser = _Literals(text)
    root = parser.json() if PurePosixPath(path).suffix.lower() == ".json" else parser.yaml()
    value = root.value
    if not isinstance(value, dict) or set(value) != {"format_version", "parameter_file", "problems"}:
        raise ValueError("bounded PEtab configuration keys required")
    if type(value["format_version"]) is not int or value["format_version"] != 1:
        raise ValueError("only exact integer PEtab format_version 1 is supported")
    problems = value["problems"]
    if not isinstance(problems, list) or not 1 <= len(problems) <= 64:
        raise ValueError("bounded nonempty PEtab problems list required")
    base = str(PurePosixPath(path).parent)
    def resolve(target):
        _path(target)
        resolved = target if base == "." else base + "/" + target
        if resolved not in artifacts:
            raise ValueError("PEtab target is missing: " + resolved)
        return resolved
    parameter = resolve(value["parameter_file"])
    output = []
    required = {"sbml_files", "measurement_files", "observable_files"}
    allowed = required | {"condition_files", "visualization_files"}
    for index, problem in enumerate(problems):
        if not isinstance(problem, dict) or not required <= set(problem) or set(problem) - allowed:
            raise ValueError("bounded PEtab problem fields required")
        node = root.children["problems"].children[index]
        pointers = {"/format_version": root.children["format_version"],
                    "/parameter_file": root.children["parameter_file"]}
        record = {"config_path": path, "parameter_file": parameter,
                  "source": _text_source(path, raw, text, root.start, root.end)}
        all_targets = []
        for key in sorted(allowed):
            entries = problem.get(key, [])
            if not isinstance(entries, list) or (key in required and not entries) or len(entries) > 64:
                raise ValueError("bounded PEtab file list required: " + key)
            resolved = [resolve(entry) for entry in entries]
            if len(set(resolved)) != len(resolved):
                raise ValueError("duplicate PEtab target")
            all_targets.extend(resolved)
            if key != "visualization_files": record[key] = resolved
            for position, child in enumerate(node.children[key].children if key in node.children else []):
                pointers[f"/problems/{index}/{key}/{position}"] = child
        if len(set(all_targets + [parameter])) != len(all_targets) + 1:
            raise ValueError("ambiguous PEtab file roles")
        record["pointer_sources"] = {pointer: _text_source(path, raw, text, n.start, n.end)
                                     for pointer, n in sorted(pointers.items())}
        output.append(record)
    return output


def parse_project_links(artifacts):
    """Return explicit bounded PEtab v1 links, raising ValueError on ambiguity.

    File references are relative to the configuration's directory and must be
    present in ``artifacts``. No filesystem or network reads occur. Unsupported
    candidate configurations fail closed; unrelated JSON/YAML files are ignored.
    ``pointer_sources`` maps JSON-pointer strings to exact original intervals.
    """
    _artifacts(artifacts)
    result = []
    for path, raw in _config_candidates(artifacts):
        result.extend(_parse_config(path, raw, artifacts))
    return result


class _Result:
    def __init__(self):
        self.value = {"schema_version": VERSION, "schema": VERSION, "mappings": [],
                      "correspondences": [], "conflicts": [], "obligations": [],
                      "authority": False}

    def add(self, category, **record):
        if len(self.value[category]) >= MAX_RECORDS:
            raise ValueError("correspondence record bound")
        record.update(authority=False, scientific_equivalence="NOT_ESTABLISHED")
        record["id"] = category.rstrip("s") + "-" + _digest([category, record])[:24]
        if not any(r["id"] == record["id"] for r in self.value[category]):
            self.value[category].append(record)
        return record

    def obligation(self, kind, reason, **extra):
        return self.add("obligations", kind=kind, status="OPEN", reason=reason, **extra)


def _claims(interpretation, artifacts, result):
    output = []
    for claim in interpretation.get("claims", []):
        if not isinstance(claim, dict) or not verify_source(claim.get("source", {}), artifacts):
            result.obligation("source_grounding", "Input claim lacks an exact current source interval",
                              claim_id=claim.get("id") if isinstance(claim, dict) else None)
        else:
            output.append(claim)
    return output


def _endpoint(path, entity, scope=None):
    return {"path": path, "entity": entity, "scope": scope}


def _explicit_mappings(artifacts, result):
    # Pointers must name both files. A case-sensitive symbol alone never binds.
    pointer = r"(?P<{p}>[A-Za-z0-9_./-]+)::(?P<{e}>" + _IDENTIFIER + r")(?:\[scope=(?P<{s}>[A-Za-z0-9_./-]+)\])?"
    pattern = re.compile(r"(?m)^\s*(?:Variable |Equation |Unit )?Mapping:\s*" +
                         pointer.format(p="lp", e="le", s="ls") + r"\s*=\s*" +
                         pointer.format(p="rp", e="re", s="rs") + r"\s*\.?\s*$")
    natural = re.compile(r"(?m)^\s*(?P<le>" + _IDENTIFIER +
                         r") in (?P<lp>[A-Za-z0-9_./-]+) corresponds to (?P<re>" +
                         _IDENTIFIER + r") in (?P<rp>[A-Za-z0-9_./-]+)\.\s*$")
    for path, raw in sorted(artifacts.items()):
        if PurePosixPath(path).suffix.lower() not in {".md", ".txt", ".rst"}:
            continue
        try: text = raw.decode("utf-8")
        except UnicodeError: continue
        for regex in (pattern, natural):
            for match in regex.finditer(text):
                groups = match.groupdict()
                source = _text_source(path, raw, text, match.start(), match.end())
                try:
                    lp, rp = _path(groups["lp"]), _path(groups["rp"])
                    if lp not in artifacts or rp not in artifacts or lp == rp:
                        raise ValueError("mapping must point to two present distinct files")
                except ValueError as exc:
                    result.obligation("mapping_pointer", str(exc), source=source); continue
                result.add("mappings", kind="explicit_source_mapping", status="SOURCE_DECLARED",
                           left=_endpoint(lp, groups["le"], groups.get("ls")),
                           right=_endpoint(rp, groups["re"], groups.get("rs")), source=source)


def _resolve(endpoint, claims):
    matches = [c for c in claims if c["source"]["path"] == endpoint["path"]
               and c.get("entity", c.get("subject")) == endpoint["entity"]
               and (endpoint["scope"] is None or c.get("scope") == endpoint["scope"])]
    # Distinct declarations or roles under the same name remain ambiguous.
    return matches[0] if len(matches) == 1 else None


def _mapped_rhs(left, right, mappings):
    """Rename only symbols with explicit, unambiguous cross-file pointers."""
    left_names, right_names = set(semantics._symbols(left["rhs"])), set(semantics._symbols(right["rhs"]))
    pairs = []
    for mapping in mappings:
        if mapping.get("kind") != "explicit_source_mapping": continue
        a, b = mapping["left"], mapping["right"]
        if a["path"] == right["source"]["path"] and b["path"] == left["source"]["path"]:
            a, b = b, a
        if (a["path"] != left["source"]["path"] or b["path"] != right["source"]["path"]
                or a["entity"] not in left_names or b["entity"] not in right_names):
            continue
        for endpoint, claim in ((a, left), (b, right)):
            binding_scopes = {s.get("scope") for s in claim.get("symbol_bindings", [])
                              if s.get("symbol") == endpoint["entity"]}
            actual_scopes = binding_scopes or {claim.get("scope")}
            if endpoint["scope"] is not None and actual_scopes != {endpoint["scope"]}:
                break
        else: pairs.append((a["entity"], b["entity"], mapping))
    if (any(len({b for a, b, _ in pairs if a == name}) != 1 for name in left_names)
            or any(len({a for a, b, _ in pairs if b == name}) != 1 for name in right_names)):
        raise ValueError("Every equation symbol needs one explicit cross-file mapping")
    rename = {b:a for a,b,_ in pairs}
    def replace(value, depth=0):
        if depth > 64: raise ValueError("equation IR depth bound")
        if isinstance(value, dict):
            if value.get("op") == "symbol": return {"op":"symbol", "name":rename[value["name"]]}
            return {k:replace(v, depth+1) for k,v in value.items()}
        if isinstance(value, list): return [replace(v, depth+1) for v in value]
        return deepcopy(value)
    return replace(right["rhs"]), [{"left":a, "right":b, "mapping_id":m["id"], "source":m["source"]}
                                   for a,b,m in sorted(pairs, key=lambda item:(item[0],item[1],item[2]["id"]))]


def _compare(mapping, left, right, result, mappings):
    source = mapping["source"]
    base = {"mapping_id": mapping["id"], "left_claim_id": left.get("id"),
            "right_claim_id": right.get("id"), "source": source,
            "sources": [source, left["source"], right["source"]]}
    result.add("correspondences", kind="explicit_entity_correspondence", status="SOURCE_DECLARED", **base)
    if left.get("kind") == right.get("kind") == "equation":
        try:
            renamed, symbol_mappings = _mapped_rhs(left, right, mappings)
            comparison = semantics.compare_expressions(left["rhs"], renamed)
            comparison["original_domain_conditions"] = {"left":semantics._denominators(left["rhs"]),
                                                        "right":semantics._denominators(right["rhs"])}
        except (ValueError, KeyError, TypeError, RecursionError):
            result.obligation("equation_comparison", "Mapped equations exceed the closed rational fragment", **base)
        else:
            equation_base = {**base, "sources":base["sources"]+[m["source"] for m in symbol_mappings]}
            result.add("correspondences", kind="equation_comparison", status=comparison["algebra"]["status"],
                       comparison=comparison, symbol_mappings=symbol_mappings, **equation_base)
            if comparison["algebra"]["status"] == "DISTINCT_RATIONAL_FUNCTIONS":
                result.add("conflicts", kind="mapped_equation_difference", status="DECLARATION_CONFLICT", **base)
            if any(comparison["original_domain_conditions"].values()):
                result.obligation("common_defined_domain", "Original denominator conditions remain open",
                                  domain_conditions=comparison["original_domain_conditions"], **equation_base)
    lu, ru = left.get("unit_resolution", {}), right.get("unit_resolution", {})
    if left.get("unit") is not None and right.get("unit") is not None:
        if lu.get("dimension") is None or ru.get("dimension") is None:
            result.obligation("mapped_unit_resolution", "At least one mapped unit lacks an explicit supported resolution", **base)
        elif lu["dimension"] != ru["dimension"] or lu.get("factor") != ru.get("factor"):
            result.add("conflicts", kind="mapped_unit_difference", status="DECLARATION_CONFLICT",
                       left_unit=left.get("unit"), right_unit=right.get("unit"), **base)
    result.obligation("scientific_meaning", "Explicit mapping and algebra do not establish scientific identity", **base)


def _table(path, raw):
    text = raw.decode("utf-8", errors="strict")
    if "\x00" in text: raise ValueError("table NUL forbidden")
    lines = text.splitlines(keepends=True)
    if not lines: raise ValueError("empty PEtab table")
    header = next(csv.reader([lines[0].rstrip("\r\n")], delimiter="\t", strict=True))
    if len(set(header)) != len(header) or not header or len(header) > 128:
        raise ValueError("ambiguous PEtab table columns")
    rows, offset = [], len(lines[0])
    for line in lines[1:]:
        if not line.strip():
            offset += len(line); continue
        values = next(csv.reader([line.rstrip("\r\n")], delimiter="\t", strict=True))
        if len(values) != len(header) or len(rows) >= MAX_RECORDS:
            raise ValueError("PEtab table row shape/bound")
        rows.append((dict(zip(header, values)), _text_source(path, raw, text, offset, offset+len(line))))
        offset += len(line)
    return header, rows


def _petab(link, claims, interpretation, artifacts, result):
    mapping = result.add("mappings", kind="petab_project_links", status="SOURCE_DECLARED", **link)
    if len(link["sbml_files"]) != 1:
        result.obligation("petab_model_scope", "Multiple configured SBML models require an explicit disambiguating scope",
                          mapping_id=mapping["id"], source=link["source"]); return
    model_path = link["sbml_files"][0]
    symbols = [s for s in interpretation.get("symbols", []) if isinstance(s, dict)
               and s.get("source", {}).get("path") == model_path
               and verify_source(s.get("source", {}), artifacts)]
    scopes = {s.get("scope") for s in symbols if "/reaction/" not in str(s.get("scope", ""))}
    # An empty/unsupported model cannot authorize observable symbol bindings.
    if len(scopes) != 1:
        result.obligation("petab_model_scope", "Configured model does not have one grounded exact model scope",
                          mapping_id=mapping["id"], source=link["source"]); return
    scope = next(iter(scopes))
    model_symbols = {}
    for symbol in symbols:
        if symbol.get("scope") == scope:
            model_symbols.setdefault(symbol.get("symbol"), []).append(symbol)
    observable_ids = {}
    for path in link["observable_files"]:
        try:
            header, rows = _table(path, artifacts[path])
            if not {"observableId", "observableFormula"} <= set(header):
                raise ValueError("observableId and observableFormula columns required")
        except (ValueError, UnicodeError, csv.Error) as exc:
            result.obligation("petab_observable_table", str(exc), source=link["source"], path=path); continue
        for row, source in rows:
            observable = row["observableId"]
            if not re.fullmatch(_IDENTIFIER, observable):
                result.obligation("petab_observable_id", "Invalid exact observable identifier", source=source); continue
            observable_ids.setdefault(observable, []).append(source)
            try: rhs = parse_expression(row["observableFormula"])
            except (Unsupported, ValueError):
                result.obligation("petab_observable_formula", "Observable formula is outside the bounded arithmetic fragment", source=source); continue
            bindings, unknown, placeholders = [], [], []
            for name in semantics._symbols(rhs):
                if re.fullmatch(r"observableParameter[1-9][0-9]*(?:_" + re.escape(observable) + r")?", name):
                    placeholders.append(name)
                elif len(model_symbols.get(name, [])) == 1:
                    target = model_symbols[name][0]
                    bindings.append({"symbol": name, "symbol_id": target.get("id"), "model_id": scope,
                                     "scope": scope, "source": target["source"]})
                else: unknown.append(name)
            result.add("correspondences", kind="petab_observable_formula", status="SOURCE_DECLARED",
                       mapping_id=mapping["id"], config_path=link["config_path"], observable_id=observable,
                       model_path=model_path, model_id=scope, scope=scope, rhs=rhs,
                       symbol_bindings=bindings, unresolved_symbols=unknown, placeholders=placeholders,
                       source=source, sources=[link["source"], source]+[b["source"] for b in bindings])
            for name in placeholders:
                result.obligation("petab_observable_parameter", "Observable placeholder requires measurement-table resolution",
                                  symbol=name, observable_id=observable, source=source,
                                  mapping_id=mapping["id"])
            for name in unknown:
                result.obligation("petab_unbound_symbol", "Formula identifier has no unique declaration in the configured model scope",
                                  symbol=name, observable_id=observable, source=source)
    for observable, sources in observable_ids.items():
        if len(sources) > 1:
            result.add("conflicts", kind="petab_duplicate_observable", status="AMBIGUOUS", observable_id=observable,
                       sources=sources, source=sources[0])
    for path in link["measurement_files"]:
        try:
            header, rows = _table(path, artifacts[path])
            if "observableId" not in header: raise ValueError("measurement observableId column required")
        except (ValueError, UnicodeError, csv.Error) as exc:
            result.obligation("petab_measurement_table", str(exc), source=link["source"], path=path); continue
        for row, source in rows:
            matches = observable_ids.get(row["observableId"], [])
            if len(matches) != 1:
                result.obligation("petab_measurement_observable", "Measurement observableId has no unique configured observable row",
                                  observable_id=row["observableId"], source=source); continue
            result.add("correspondences", kind="petab_measurement_observable", status="SOURCE_DECLARED",
                       mapping_id=mapping["id"], observable_id=row["observableId"], source=source,
                       sources=[link["source"], source, matches[0]])
    result.obligation("scientific_meaning", "PEtab project linkage does not establish empirical adequacy or scientific identity",
                      mapping_id=mapping["id"], source=link["source"])


def analyze(interpretation, artifacts):
    """Analyze grounded v3 interpretation claims and exact project bytes.

    This sidecar is a bounded proposal. All records retain ``authority=False``;
    scientific equivalence is never established by this module.
    """
    _artifacts(artifacts)
    if not isinstance(interpretation, dict): raise ValueError("interpretation mapping required")
    if any(not isinstance(interpretation.get(k, []), list) or len(interpretation.get(k, [])) > MAX_RECORDS
           for k in ("claims", "symbols")):
        raise ValueError("interpretation list/bound")
    result = _Result()
    claims = _claims(interpretation, artifacts, result)
    _explicit_mappings(artifacts, result)
    for mapping in list(result.value["mappings"]):
        left, right = _resolve(mapping["left"], claims), _resolve(mapping["right"], claims)
        if left is None or right is None:
            result.obligation("explicit_mapping_resolution", "Mapping endpoint lacks one uniquely grounded scoped claim",
                              mapping_id=mapping["id"], source=mapping["source"])
        else: _compare(mapping, left, right, result, result.value["mappings"])
    for path, raw in _config_candidates(artifacts):
        try: links = _parse_config(path, raw, artifacts)
        except (ValueError, RecursionError, UnicodeError) as exc:
            # Invalid UTF-8 cannot be quoted as an exact UTF-8 interval.
            source = {"path": path, "sha256": hashlib.sha256(raw).hexdigest()}
            try: source = _source(path, raw)
            except UnicodeError: pass
            result.obligation("petab_configuration", str(exc), source=source)
        else:
            for link in links: _petab(link, claims, interpretation, artifacts, result)
    return result.value
