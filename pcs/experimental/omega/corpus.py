"""First-party synthetic corpus with fixed family splits and leakage checks."""
from __future__ import annotations

from copy import deepcopy
from collections import Counter
import random

from .logic import check, digest, exact, integer, task, walk

GENERATOR = "omega-boolean-families/1"
FAMILIES = {"connective-confusion": "train", "negation-loss": "train", "swapped-implication": "train",
            "nested-connective": "validation", "de-morgan": "test", "implication-expansion": "test",
            "distribution": "test", "absorption": "test"}


def atom(name):
    return {"op": "atom", "symbol": name, "args": []}


def unary(a):
    return {"op": "not", "body": deepcopy(a)}


def binary(op, a, b):
    return {"op": op, "left": deepcopy(a), "right": deepcopy(b)}


def alpha_source(formula):
    out, names = deepcopy(formula), {}
    for _, node in walk(out):
        if node["op"] == "atom":
            names.setdefault(node["symbol"], "V" + str(len(names)))
            node["symbol"] = names[node["symbol"]]
    return digest(out)


def semantic_signature(value):
    """Alpha-normalized truth-pair fingerprint, including the input dimension."""
    names = []
    for f in (value["source"], value["candidate"]):
        for _, n in walk(f):
            if n["op"] == "atom" and n["symbol"] not in names:
                names.append(n["symbol"])
    normalized = deepcopy(value)
    for f in (normalized["source"], normalized["candidate"]):
        for _, n in walk(f):
            if n["op"] == "atom":
                n["symbol"] = "V" + str(names.index(n["symbol"]))
    normalized["variables"] = sorted("V" + str(i) for i in range(len(names)))
    result = check(normalized)
    return digest({"variables": len(names), "truth_pairs": result["truth_pairs"]})


def generate(*, seed=20261009, per_family=24):
    integer(seed, 0, 2**32 - 1, "seed")
    integer(per_family, 2, 128, "per-family count")
    rng, records, sources, signatures = random.Random(seed), [], set(), set()

    def term(depth=0):
        if depth >= 2 or rng.random() < 0.45:
            return atom(rng.choice(["P", "Q", "R", "S"]))
        if rng.random() < 0.2:
            return unary(term(depth + 1))
        return binary(rng.choice(["and", "or", "implies"]), term(depth + 1), term(depth + 1))

    for family, partition in FAMILIES.items():
        count = 0
        for _ in range(20000):
            a, b, c = term(), term(), term()
            if family == "connective-confusion":
                source, candidate = binary("and", a, b), binary("or", a, b)
            elif family == "negation-loss":
                source, candidate = unary(a), a
            elif family == "swapped-implication":
                source, candidate = binary("implies", a, b), binary("implies", b, a)
            elif family == "nested-connective":
                source, candidate = unary(binary("or", a, b)), unary(binary("and", a, b))
            elif family == "de-morgan":
                source, candidate = unary(binary("and", a, b)), binary("or", unary(a), b)
            elif family == "implication-expansion":
                source, candidate = binary("implies", a, b), binary("or", a, b)
            elif family == "distribution":
                source = binary("and", a, binary("or", b, c))
                candidate = binary("or", binary("and", a, b), binary("or", a, c))
            else:
                source, candidate = a, binary("and", a, binary("or", unary(a), b))
            value = {"variables": ["P", "Q", "R", "S"], "source": source, "candidate": candidate}
            try:
                result = check(value)
            except ValueError:
                continue
            fingerprint, src = semantic_signature(value), alpha_source(source)
            if result["equivalent"] or fingerprint in signatures or src in sources:
                continue
            sources.add(src)
            signatures.add(fingerprint)
            core = {"id": f"{family}-{count:03d}", "family": family, "partition": partition,
                    "task": value, "task_sha256": digest(value), "source_group": src,
                    "semantic_group": fingerprint,
                    "provenance": {"origin": "first-party-synthetic", "license": "Apache-2.0",
                                   "generator": GENERATOR, "personal_data": False, "hints": False}}
            records.append(core)
            count += 1
            if count == per_family:
                break
        if count != per_family:
            raise ValueError(f"Could not generate requested distinct family {family}")
    core = {"format": "pcs-omega-corpus-v1", "generator": GENERATOR, "seed": seed,
            "per_family": per_family, "records": records}
    core["corpus_sha256"] = digest(core)
    return validate_corpus(core)


def family_matches(family, value):
    """Validate family construction; a changed label cannot import a holdout."""
    source, candidate = value["source"], value["candidate"]
    try:
        if family == "connective-confusion":
            return source["op"] == "and" and candidate == binary("or", source["left"], source["right"])
        if family == "negation-loss":
            return source["op"] == "not" and candidate == source["body"]
        if family == "swapped-implication":
            return source["op"] == "implies" and candidate == binary("implies", source["right"], source["left"])
        if family == "nested-connective":
            body = source["body"]
            return source["op"] == "not" and body["op"] == "or" and candidate == unary(binary("and", body["left"], body["right"]))
        if family == "de-morgan":
            body = source["body"]
            return source["op"] == "not" and body["op"] == "and" and candidate == binary("or", unary(body["left"]), body["right"])
        if family == "implication-expansion":
            return source["op"] == "implies" and candidate == binary("or", source["left"], source["right"])
        if family == "distribution":
            a, body = source["left"], source["right"]
            return source["op"] == "and" and body["op"] == "or" and candidate == binary("or", binary("and", a, body["left"]), binary("or", a, body["right"]))
        if family == "absorption":
            return candidate["op"] == "and" and candidate["left"] == source and candidate["right"]["op"] == "or" and candidate["right"]["left"] == unary(source)
    except (KeyError, TypeError):
        return False
    return False


def validate_corpus(corpus):
    exact(corpus, {"format", "generator", "seed", "per_family", "records", "corpus_sha256"}, "corpus")
    if corpus["format"] != "pcs-omega-corpus-v1" or corpus["generator"] != GENERATOR:
        raise ValueError("Unsupported corpus version")
    integer(corpus["seed"], 0, 2**32 - 1, "seed")
    integer(corpus["per_family"], 2, 128, "per-family count")
    records = corpus["records"]
    if type(records) is not list or not 1 <= len(records) <= 1024:
        raise ValueError("Corpus size bound exceeded")
    ids, groups, semantic = set(), set(), set()
    for r in records:
        exact(r, {"id", "family", "partition", "task", "task_sha256", "source_group", "semantic_group", "provenance"}, "corpus record")
        if (type(r["family"]) is not str or r["family"] not in FAMILIES or r["partition"] != FAMILIES[r["family"]] or
                type(r["id"]) is not str or r["id"] in ids):
            raise ValueError("Family split drift or duplicate ID")
        task(r["task"])
        if not family_matches(r["family"], r["task"]):
            raise ValueError("Task construction does not match its declared family")
        if (r["task_sha256"] != digest(r["task"]) or r["source_group"] != alpha_source(r["task"]["source"]) or
                r["semantic_group"] != semantic_signature(r["task"])):
            raise ValueError("Forged corpus binding or semantics")
        if r["source_group"] in groups or r["semantic_group"] in semantic:
            raise ValueError("Source or semantic problem leakage")
        expected = {"origin": "first-party-synthetic", "license": "Apache-2.0", "generator": GENERATOR,
                    "personal_data": False, "hints": False}
        if digest(r["provenance"]) != digest(expected):
            raise ValueError("Unsupported personal, assisted, or unlicensed corpus provenance")
        ids.add(r["id"])
        groups.add(r["source_group"])
        semantic.add(r["semantic_group"])
    if Counter(r["family"] for r in records) != {f: corpus["per_family"] for f in FAMILIES}:
        raise ValueError("Missing family records or declared sample-count drift")
    if corpus["corpus_sha256"] != digest({k: v for k, v in corpus.items() if k != "corpus_sha256"}):
        raise ValueError("Corpus digest mismatch")
    return corpus
