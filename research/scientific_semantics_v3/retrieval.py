"""Bounded scientific source retrieval. Relevance is never verification.

The default is deterministic.  The old scientific neural checkpoint remains an
explicit diagnostic baseline, not an authority or a routing decision.  All modes
rank the same candidate pool; chunk generation never reads questions or labels.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from fractions import Fraction
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import tempfile
import time
import unicodedata
import zipfile

from research.scientific_understanding_v2 import retrieval as baseline
from research.scientific_understanding_v2.rational_equivalence import compare
from pcs.jsonio import strict_json_loads

MAX_CANDIDATES = 4096
MAX_TEXT = 10000
MAX_SOURCE = 2 * 1024 * 1024
MAX_CORPUS = 8 * 1024 * 1024
MODES = ("bm25", "tfidf", "normalized_bm25", "hybrid", "neural")
PINNED_CHECKPOINT = baseline.DEFAULT_CHECKPOINT
PINNED_CHECKPOINT_SHA256 = "e537cce039675369d63c254b6a51da989c35d773cb23a72995c3527dbc345d95"
MAX_CHECKPOINT_BYTES = 1024 * 1024
_NUMBER = re.compile(r"(?<![\w.])[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?(?![\w.])")
_WORD = re.compile(r"[A-Za-z_][A-Za-z_0-9]*|[α-ωΑ-Ω]+|[=+*/^()-]")
_GREEK = {"α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "μ": "micro", "σ": "sigma", "τ": "tau", "λ": "lambda", "ω": "omega"}
_SYNONYMS = {
    "initializes": "initial", "initialized": "initial", "initialization": "initial",
    "concentrations": "concentration", "parameters": "parameter",
    "iterations": "iteration", "evaluations": "evaluation", "estimated": "estimate",
    "derivatives": "derivative", "species": "species", "equations": "equation",
    "minimizer": "minimum", "minimizers": "minimum", "minimized": "minimum",
    "reported": "report", "reports": "report", "uncertainties": "uncertainty",
}
_XML_TAGS = frozenset("sbml listofparameters listofspecies listofreactions annotation rdf description math ci cn apply plus minus times divide power xmlns metaid sboTerm".lower().split())


def normalized_tokens(text):
    """Retrieval-only spelling normalization, not scientific equivalence.

    Split camel/snake identifiers while retaining the complete spelling; exact
    case-sensitive identifiers are separately used by the hybrid ranker.  Unit
    aliases and biological synonyms are intentionally not identified as meaning.
    """
    text = unicodedata.normalize("NFKC", str(text)).replace("−", "-")
    text = re.sub(r"</?[A-Za-z_:][A-Za-z_0-9:.-]*", " ", text)
    tokens = []
    for match in _WORD.finditer(text):
        word = match.group()
        for greek, name in _GREEK.items():
            word = word.replace(greek, name)
        if word.lower() in _XML_TAGS:
            continue
        split = re.sub(r"([a-z])([A-Z])", r"\1 \2", word).replace("_", " ")
        full = word.lower()
        tokens.append(_SYNONYMS.get(full, full))
        parts = split.lower().split()
        if len(parts) > 1:
            tokens.extend(_SYNONYMS.get(p, p) for p in parts)
    for literal in _NUMBER.findall(text):
        if len(literal) > 64:
            continue
        try:
            if "e" in literal.lower() and abs(int(literal.lower().split("e")[1])) > 100:
                continue
            tokens.append("number:" + str(Fraction(literal)))
        except (ValueError, OverflowError):
            continue
    return tokens


def _identifiers(text):
    # Mixed alphanumeric names and explicit XML/quoted identifiers only. Ordinary
    # prose words are not inferred to be formal variables.
    values = re.findall(r"\b(?:id|name|symbol)\s*=\s*['\"]([^'\"]{1,128})['\"]", text)
    values += re.findall(r"<(?:\w+:)?ci\b[^>]*>\s*([A-Za-z_][A-Za-z_0-9]*)\s*</", text)
    values += re.findall(r"`([A-Za-z_][A-Za-z_0-9]*)`", text)
    values += re.findall(r"\b(?:[A-Za-z_]*[A-Za-z][0-9][A-Za-z_0-9]*|[A-Za-z]+_[A-Za-z_0-9]+|[A-Z])\b", text)
    return set(values)


def _bm25(query, documents):
    n = len(documents)
    df = Counter(t for d in documents for t in d)
    average = sum(sum(d.values()) for d in documents) / max(1, n)
    result = []
    for d in documents:
        length = sum(d.values())
        score = 0.0
        for term, count in query.items():
            frequency = d[term]
            idf = math.log(1 + (n-df[term]+0.5)/(df[term]+0.5))
            denominator = frequency + 1.5*(0.25+0.75*length/max(average, 1))
            if denominator:
                score += count*idf*frequency*2.5/denominator
        result.append(score)
    return result


def load_pinned_checkpoint(checkpoint=None):
    """Read the historical baseline by pinned content, never a sibling digest.

    Alternate model admission is intentionally unsupported by this research
    wrapper. This is integrity validation, not immutable storage or a claim
    that ordinary host permissions protect a compromised Python process.
    """
    path = Path(PINNED_CHECKPOINT)
    if checkpoint is not None and Path(checkpoint).absolute() != path.absolute():
        raise ValueError("alternate checkpoints require separate reviewed admission")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or not 0 < metadata.st_size <= MAX_CHECKPOINT_BYTES:
            raise ValueError("checkpoint regular-file/size bound")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(MAX_CHECKPOINT_BYTES+1)
        if len(raw) > MAX_CHECKPOINT_BYTES or hashlib.sha256(raw).hexdigest() != PINNED_CHECKPOINT_SHA256:
            raise ValueError("pinned checkpoint SHA256 mismatch")
        return baseline._validate_checkpoint(strict_json_loads(raw.decode("utf-8")))
    finally:
        os.close(descriptor)


def _safe_ir(expression):
    if not isinstance(expression, str) or len(expression) > 1024:
        raise ValueError("bounded scalar expression required")
    tree = ast.parse(expression.replace("^", "**"), mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 128:
        raise ValueError("expression node bound")
    def walk(node, depth=0):
        if depth > 16:
            raise ValueError("expression depth bound")
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return {"op": "number", "value": ast.get_source_segment(expression.replace("^", "**"), node)}
        if isinstance(node, ast.Name):
            return {"op": "symbol", "name": node.id}
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = walk(node.operand, depth+1)
            return value if isinstance(node.op, ast.UAdd) else {"op": "neg", "arg": value}
        operations = {ast.Add: "add", ast.Sub: "sub", ast.Mult: "mul", ast.Div: "div", ast.Pow: "pow"}
        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            return {"op": operations[type(node.op)], "args": [walk(node.left, depth+1), walk(node.right, depth+1)]}
        raise ValueError("outside explicit scalar arithmetic")
    return walk(tree.body)


def symbolic_match(query, candidate):
    """Check an explicit equation against an equation in candidate source text.

    This is a ranking feature only. Equal rational functions on a common defined
    domain do not establish equal scientific meanings or resolve denominators.
    Candidate expression metadata is ignored; both expressions are parsed
    through a closed arithmetic AST and independently normalized again. This
    does not authenticate a candidate's claimed file provenance.
    """
    match = re.fullmatch(r"\s*([A-Za-z_][A-Za-z_0-9]*)\s*=\s*([^=\n]+)\s*", query)
    text = candidate.get("text")
    if not match or not isinstance(text, str) or len(text) > MAX_TEXT:
        return None
    for source_equation in re.finditer(r"(?m)^\s*([A-Za-z_][A-Za-z_0-9]*)\s*=\s*([^=\n]{1,1024})\s*$", text):
        if match[1] != source_equation[1]:
            continue
        try:
            result = compare(_safe_ir(match[2]), _safe_ir(source_equation[2]))
        except (ValueError, SyntaxError, TypeError, KeyError, RecursionError, OverflowError):
            continue
        return {**result, "scientific_context_equivalence": "UNRESOLVED", "feature_only": True}
    return None


def rank(query, candidates, mode="hybrid", checkpoint=None):
    """Aligned finite scores; no labels, source truth, or verification authority."""
    if not isinstance(query, str) or len(query) > MAX_TEXT:
        raise ValueError("bounded query string required")
    if not isinstance(candidates, (list, tuple)) or len(candidates) > MAX_CANDIDATES:
        raise ValueError("candidate count bound")
    texts = []
    for candidate in candidates:
        if not isinstance(candidate, dict) or not isinstance(candidate.get("text"), str) or len(candidate["text"]) > MAX_TEXT:
            raise ValueError("bounded candidate text required")
        texts.append(candidate["text"])
    if sum(map(len, texts)) > MAX_CORPUS:
        raise ValueError("candidate corpus bound")
    if mode not in MODES:
        raise ValueError("unknown retrieval mode")
    if mode in {"bm25", "tfidf"}:
        return baseline.rank(query, candidates, mode=mode, checkpoint=checkpoint)
    if mode == "neural":
        model = load_pinned_checkpoint(checkpoint)
        query_vector = baseline._encode(query, model)
        return [sum(a*b for a, b in zip(query_vector, baseline._encode(text, model))) for text in texts]
    if not texts:
        return []
    documents = [Counter(normalized_tokens(text)) for text in texts]
    lexical = _bm25(Counter(normalized_tokens(query)), documents)
    if mode == "normalized_bm25":
        return lexical
    # Reciprocal-rank fusion prevents score scales from silently weighting a
    # method differently on each corpus. All constituents see the same pool.
    scores = [0.0] * len(texts)
    for values in [lexical, baseline.rank(query, candidates, "bm25"), baseline.rank(query, candidates, "tfidf")]:
        for position, index in enumerate(sorted(range(len(values)), key=lambda i: (-values[i], i)), 1):
            # A completely nonmatching method contributes no arbitrary tie bias.
            if values[index] > 0:
                scores[index] += 1/(20+position)
    query_ids = _identifiers(query)
    for index, text in enumerate(texts):
        if query_ids:
            scores[index] += 0.03 * len(query_ids & _identifiers(text))/len(query_ids)
        symbolic = symbolic_match(query, candidates[index])
        if symbolic and symbolic["status"] == "EQUAL_ON_COMMON_DEFINED_DOMAIN":
            scores[index] += 0.05
    return scores


def structural_candidates(inventory, *, chunk_chars=1000, overlap=200):
    """Query-independent overlapping source chunks, bound to original bytes.

    Accept the existing PCS portable inventory. No parser is executed and no
    imported content becomes training data. XML attributes/paragraphs remain
    verbatim; windows prefer line boundaries and retain deterministic overlap.
    """
    if type(chunk_chars) is not int or not 128 <= chunk_chars <= 4000:
        raise ValueError("chunk size bound")
    if type(overlap) is not int or not 0 <= overlap < chunk_chars//2:
        raise ValueError("overlap bound")
    artifacts = inventory.get("artifacts", []) if isinstance(inventory, dict) else inventory
    if not isinstance(artifacts, list) or len(artifacts) > 512:
        raise ValueError("artifact count bound")
    result, total = [], 0
    for artifact in artifacts:
        path = Path(artifact["snapshot_path"])
        if path.is_symlink() or not path.is_file():
            raise ValueError("source snapshot must be a regular file")
        if path.stat().st_size > MAX_SOURCE:
            raise ValueError("source byte bound")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != artifact["sha256"]:
            raise ValueError("source digest mismatch")
        total += len(raw)
        if total > MAX_CORPUS:
            raise ValueError("source corpus bound")
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeError:
            continue
        start = 0
        while start < len(text):
            end = min(start+chunk_chars, len(text))
            if end < len(text):
                boundary = text.rfind("\n", start+chunk_chars//2, end)
                if boundary > start:
                    end = boundary+1
            quote = text[start:end]
            if quote.strip():
                source = {"artifact_id": artifact.get("id"), "path": artifact["path"], "sha256": artifact["sha256"],
                          "quote": quote, "locator": {"char_start": start, "char_end": end,
                          "line_start": text.count("\n", 0, start)+1}}
                identifier = hashlib.sha256((artifact["sha256"]+":"+str(start)+":"+str(end)).encode()).hexdigest()
                result.append({"id": "source-window-"+identifier, "text": quote, "source": source, "kind": "source_window"})
                if len(result) > MAX_CANDIDATES:
                    raise ValueError("candidate count bound")
            if end == len(text):
                break
            start = max(start+1, end-overlap)
    return result


def candidate_pool(inventory, *, pool="structural", interpretation=None):
    """Build a question-independent pool; combined retains narrow parsed spans."""
    from research.scientific_understanding_v2.evaluation import retrieval_candidates
    if pool not in {"v2", "structural", "combined"}:
        raise ValueError("unknown candidate pool")
    if pool in {"v2", "combined"} and interpretation is None:
        raise ValueError("v2/combined pools require a v2 interpretation")
    candidates = retrieval_candidates(interpretation, inventory) if pool in {"v2", "combined"} else []
    if pool in {"structural", "combined"}:
        candidates += structural_candidates(inventory)
    result, seen = [], set()
    for candidate in candidates:
        source = candidate["source"]
        key = (source["path"], source["sha256"], source["locator"]["char_start"], source["locator"]["char_end"])
        if key not in seen:
            result.append(candidate)
            seen.add(key)
    if len(result) > MAX_CANDIDATES:
        raise ValueError("candidate count bound")
    return result


def _evaluate(annotations, candidates, inventory, modes):
    from research.scientific_understanding_v2.evaluation import _Sources, _grounded
    sources = _Sources(inventory)
    output = {"candidate_count": len(candidates), "modes": {}}
    for mode in modes:
        outcomes, elapsed = [], 0.0
        for annotation in annotations:
            relevant = {i for i, candidate in enumerate(candidates) if _grounded(candidate["source"], annotation["source"], sources, relevance=True)}
            start = time.perf_counter()
            scores = rank(annotation["statement"], candidates, mode=mode)
            elapsed += time.perf_counter()-start
            order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
            position = next((i+1 for i, candidate in enumerate(order) if candidate in relevant), None)
            outcomes.append({"annotation_id": annotation["id"], "relevant_candidates": len(relevant), "rank": position,
                             "top_candidate_id": candidates[order[0]]["id"] if order else None})
        count = len(outcomes)
        output["modes"][mode] = {"n": count, "top1_count": sum(o["rank"] == 1 for o in outcomes),
            "top1": sum(o["rank"] == 1 for o in outcomes)/count if count else None,
            "mrr": sum(1/o["rank"] if o["rank"] else 0 for o in outcomes)/count if count else None,
            "candidate_coverage": sum(bool(o["relevant_candidates"]) for o in outcomes),
            "ranking_wall_seconds": elapsed, "outcomes": outcomes}
    return output


def evaluate_references(refs, inventory, mode="normalized_bm25", pool="structural", interpretation=None):
    """Evaluation-only exact source-span relevance, never supplied to ``rank``.

    References are internal annotations, not checker authority. Relevance means
    a valid source chunk overlaps the exact referenced quote in the same original
    byte-hashed file; it is not a judgment that the chunk entails the question.
    No lexical overlap or equation equivalence can substitute for provenance.
    """
    from research.scientific_understanding_v2.evaluation import _Sources
    if isinstance(refs, dict):
        refs = refs.get("annotations", [])
    if not isinstance(refs, list) or len(refs) > 1024:
        raise ValueError("reference count bound")
    candidates = candidate_pool(inventory, pool=pool, interpretation=interpretation)
    sources = _Sources(inventory)
    outcomes, latency = [], 0.0
    for ref in refs:
        source = ref.get("source")
        if not isinstance(source, dict) or not isinstance(source.get("quote"), str) or not source["quote"] or len(source["quote"]) > 100000:
            raise ValueError("reference source quote required")
        # References can have repository fixture prefixes. A matching relative
        # path suffix is required, not a shared basename across two subprojects.
        def path_match(candidate_path):
            candidate_parts, reference_parts = Path(candidate_path).parts, Path(source.get("path", "")).parts
            return bool(candidate_parts) and tuple(reference_parts[-len(candidate_parts):]) == tuple(candidate_parts)
        relevant, reference_spans = [], []
        reference_valid = False
        for artifact in sources.artifacts:
            if artifact.get("sha256") != source.get("sha256") or not path_match(artifact.get("path", "")):
                continue
            bound = {"path": artifact["path"], "sha256": artifact["sha256"], "artifact_id": artifact.get("id")}
            text = sources.text(bound)
            if text is None:
                continue
            cursor, occurrences = 0, []
            while True:
                position = text.find(source["quote"], cursor)
                if position < 0:
                    break
                occurrences.append((position, position+len(source["quote"])))
                cursor = position+1
                if len(occurrences) > 4096:
                    raise ValueError("ambiguous reference occurrence bound")
            locator = source.get("locator")
            if isinstance(locator, dict) and "char_start" in locator:
                span = (locator.get("char_start"), locator.get("char_end"))
                if type(span[0]) is not int or type(span[1]) is not int or span not in occurrences:
                    raise ValueError("reference locator does not bind its quote")
                occurrences = [span]
            if "byte_start" in source or "byte_end" in source:
                raw = Path(artifact["snapshot_path"]).read_bytes()
                if hashlib.sha256(raw).hexdigest() != artifact["sha256"]:
                    raise ValueError("source changed during evaluation")
                begin, end = source.get("byte_start"), source.get("byte_end")
                if type(begin) is not int or type(end) is not int or not 0 <= begin < end <= len(raw) or raw[begin:end] != source["quote"].encode("utf-8"):
                    raise ValueError("reference byte span does not bind its quote")
                bom = 3 if raw.startswith(b"\xef\xbb\xbf") else 0
                occurrences = [(left, right) for left, right in occurrences
                               if len(text[:left].encode("utf-8"))+bom == begin and len(text[:right].encode("utf-8"))+bom == end]
            if occurrences:
                reference_valid = True
                reference_spans.append((artifact["path"], occurrences))
        for index, candidate in enumerate(candidates):
            bound = candidate["source"]
            if (bound["sha256"] != source.get("sha256") or
                    not path_match(bound["path"]) or not sources.valid(bound)):
                continue
            begin, end = (bound["locator"][key] for key in ("char_start", "char_end"))
            if any(path == bound["path"] and begin < right and end > left
                   for path, occurrences in reference_spans for left, right in occurrences):
                relevant.append(index)
        start = time.perf_counter()
        scores = rank(ref["statement"], candidates, mode=mode)
        seconds = time.perf_counter()-start
        latency += seconds
        order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
        position = next((i+1 for i, index in enumerate(order) if index in relevant), None)
        outcomes.append({"annotation_id": ref["id"], "reference_source_valid": reference_valid,
            "relevant_candidate_ids": [candidates[i]["id"] for i in relevant], "rank": position,
            "top_candidate_id": candidates[order[0]]["id"] if order else None, "ranking_wall_seconds": seconds})
    count = len(outcomes)
    return {"schema": "pcs-exact-source-span-retrieval-v1", "mode": mode, "pool": pool,
        "scope": "source relevance only; exact source hash and literal quote overlap, not scientific entailment",
        "candidate_count": len(candidates), "candidate_ids": [c["id"] for c in candidates],
        "n": count, "top1_count": sum(o["rank"] == 1 for o in outcomes),
        "top1": sum(o["rank"] == 1 for o in outcomes)/count if count else None,
        "mrr": sum(1/o["rank"] if o["rank"] else 0 for o in outcomes)/count if count else None,
        "candidate_coverage": sum(bool(o["relevant_candidate_ids"]) for o in outcomes),
        "invalid_reference_sources": sum(not o["reference_source_valid"] for o in outcomes),
        "ranking_wall_seconds": latency, "authority": False, "outcomes": outcomes}


def _neural_diagnostics(annotations, candidates):
    """Measure transfer symptoms; these numbers do not prove a causal failure."""
    model = load_pinned_checkpoint()
    queries, texts = [a["statement"] for a in annotations], [c["text"] for c in candidates]
    def oov(items):
        tokens = [token for item in items for token in baseline.tokenize(item)]
        return sum(token not in model["vocabulary"] for token in tokens)/max(1, len(tokens))
    vectors = [baseline._encode(text, model) for text in queries]
    document_vectors = [baseline._encode(text, model) for text in texts]
    cosine = lambda a, b: sum(x*y for x, y in zip(a, b))
    pairs = [cosine(vectors[i], vectors[j]) for i in range(len(vectors)) for j in range(i)]
    rankings = [[cosine(q, d) for d in document_vectors] for q in vectors]
    counts = Counter(max(range(len(values)), key=lambda i: values[i]) for values in rankings if values)
    return {"query_word_OOV_fraction": oov(queries), "source_word_OOV_fraction": oov(texts),
        "query_pair_cosine_mean": sum(pairs)/max(1, len(pairs)),
        "query_pair_cosine_min": min(pairs) if pairs else None,
        "query_pair_cosine_max": max(pairs) if pairs else None,
        "most_repeated_top_candidates": [{"candidate_id": candidates[i]["id"], "query_count": count} for i, count in counts.most_common(5)],
        "interpretation": "OOV words retain hashed character features. High OOV and XML/prose shift are transfer symptoms; neither proves representation collapse or a causal diagnosis."}


def diagnostic(output):
    """Re-evaluate EXPOSED PR202 sources; not a prospective generalization test."""
    from research.scientific_understanding_v2.pipeline import portable_inventory
    from research.scientific_understanding_v2.evaluation import retrieval_candidates
    old = Path(__file__).parents[1]/"scientific_understanding_v2"
    records = []
    for split in ("development", "final"):
        reference = json.loads((old/"reference"/(split+".json")).read_text())["annotations"]
        primary = json.loads(gzip.decompress((old/"evidence"/(split+"-primary.json.gz")).read_bytes()))
        with tempfile.TemporaryDirectory(prefix="pcs-retrieval-diagnostic-", dir="/dev/shm") as temporary:
            folder = Path(temporary)
            with zipfile.ZipFile(old/"evidence"/(split+"-primary-packages.zip")) as archive:
                for name in archive.namelist():
                    destination = (folder/name).resolve()
                    if not destination.is_relative_to(folder) or len(name) > 512:
                        raise ValueError("unsafe archived package path")
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(archive.read(name))
            for case in primary["cases"]:
                root = folder/case["id"]
                inventory = portable_inventory(root/"intake")
                interpretation = json.loads((root/"interpretations.json").read_text())
                annotations = [a for a in reference if a["project_id"] == case["id"]]
                candidates = retrieval_candidates(interpretation, inventory)
                frozen = _evaluate(annotations, candidates, inventory, MODES)
                for mode in ("bm25", "tfidf", "neural"):
                    old_outcomes = case["retrieval"]["modes"][mode]["outcomes"]
                    if [o["rank"] for o in frozen["modes"][mode]["outcomes"]] != [o["rank"] for o in old_outcomes]:
                        raise AssertionError("frozen retrieval result was not reproduced")
                structural = _evaluate(annotations, structural_candidates(inventory), inventory, MODES[:-1])
                records.append({"id": case["id"], "historical_split": split, "frozen_candidates": frozen,
                                "structural_candidates": structural, "neural_transfer_diagnostics": _neural_diagnostics(annotations, candidates)})
    result = {"schema": "pcs-scientific-retrieval-diagnostic-v1", "scope": "exposed PR202 diagnostic; no fresh heldout claim",
              "modes": list(MODES), "relevance_protocol": "unchanged PR202 exact source hash, valid quote and frozen lexical relevance predicate",
              "pool_comparison": "modes matched within each pool; structural coverage is a separate intervention with a different pool",
              "training_on_projects": False, "authority": False, "cases": records}
    Path(output).write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    return result


def development_diagnostic(output):
    """Measure the prospective development cases, never read the final split."""
    from .corpus import materialize
    from research.scientific_understanding_v2.interpretation import interpret
    here = Path(__file__).parent
    references = json.loads((here/"reference/development.json").read_text())["annotations"]
    results = []
    with tempfile.TemporaryDirectory(prefix="pcs-retrieval-development-", dir="/dev/shm") as temporary:
        records = materialize(Path(temporary)/"projects", split="development")
        for record in records:
            root = Path(record["path"])
            inventory = {"artifacts": [{"id": "a-"+hashlib.sha256(p.relative_to(root).as_posix().encode()).hexdigest(),
                "path": p.relative_to(root).as_posix(), "snapshot_path": str(p), "size": p.stat().st_size,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(root.rglob("*")) if p.is_file()]}
            annotations = [a for a in references if a["project_id"] == record["id"]]
            interpretation = interpret(inventory)
            results.append({"id": record["id"], "pools": {
                pool: {mode: evaluate_references(annotations, inventory, mode, pool=pool, interpretation=interpretation)
                       for mode in MODES} for pool in ("v2", "structural", "combined")}})
    result = {"schema": "pcs-development-source-retrieval-v3", "scope": "new development only; not generalization evidence",
              "reference_sha256": hashlib.sha256((here/"reference/development.json").read_bytes()).hexdigest(),
              "runtime_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "training_on_sources": False, "authority": False, "cases": results}
    Path(output).write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--diagnostic", type=Path)
    group.add_argument("--development", type=Path)
    arguments = parser.parse_args()
    if arguments.development:
        result = development_diagnostic(arguments.development)
        print(json.dumps([{ "id": case["id"], "pools": {pool: {mode: {key: data[key] for key in ("n", "top1_count", "candidate_coverage", "mrr")}
            for mode, data in values.items()} for pool, values in case["pools"].items()}} for case in result["cases"]], indent=2))
    else:
        result = diagnostic(arguments.diagnostic)
        print(json.dumps([{k: v for k, v in case.items() if k in {"id", "historical_split"}} | {
            pool: {mode: {metric: data[metric] for metric in ("n", "top1_count", "candidate_coverage", "mrr")}
                   for mode, data in case[pool]["modes"].items()}
            for pool in ("frozen_candidates", "structural_candidates")} for case in result["cases"]], indent=2))
