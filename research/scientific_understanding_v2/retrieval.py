"""Source relevance ranking, with no claim-checking or proof authority.

The neural model is a newly trained scientific text encoder. No weights from
native-only P1/P2 models, proof traces, or scientific project sources are used.
"""
from __future__ import annotations

from collections import Counter
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re

TOKEN = re.compile(r"[a-z]+|[0-9]+(?:\.[0-9]+)?|[=+*/^-]", re.I)
DEFAULT_CHECKPOINT = Path(__file__).parent / "learning" / "artifacts" / "scientific_encoder.json"


def tokenize(text):
    return TOKEN.findall(str(text).lower())


def _text(candidate):
    if not isinstance(candidate, dict) or not isinstance(candidate.get("text"), str):
        raise ValueError("Each candidate must contain a string text field")
    return candidate["text"]


def _lexical(query, texts, mode):
    docs = [Counter(tokenize(t)) for t in texts]
    q = Counter(tokenize(query))
    n = len(docs)
    df = Counter(t for d in docs for t in d)
    if mode == "bm25":
        avg = sum(map(lambda d: sum(d.values()), docs)) / max(n, 1)
        scores = []
        for d in docs:
            length = sum(d.values())
            score = 0.0
            for term, count in q.items():
                freq = d[term]
                idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
                denom = freq + 1.5 * (0.25 + 0.75 * length / max(avg, 1))
                score += count * idf * freq * 2.5 / denom if denom else 0
            scores.append(score)
        return scores
    idf = {t: math.log((1 + n) / (1 + f)) + 1 for t, f in df.items()}
    def vec(counter):
        v = {t: (1 + math.log(f)) * idf.get(t, math.log(1 + n) + 1)
             for t, f in counter.items()}
        norm = math.sqrt(sum(x*x for x in v.values())) or 1
        return {t: x/norm for t, x in v.items()}
    qv = vec(q)
    return [sum(qv.get(t, 0) * v for t, v in vec(d).items()) for d in docs]


def feature_ids(text, vocabulary, buckets):
    """Train-only word vocabulary plus deterministic character trigram buckets."""
    ids = []
    offset = len(vocabulary) + 1
    for word in tokenize(text):
        ids.append(vocabulary.get(word, 0))
        padded = "^" + word + "$"
        for i in range(max(0, len(padded)-2)):
            gram = padded[i:i+3].encode("utf-8")
            ids.append(offset + int.from_bytes(hashlib.sha256(gram).digest()[:4], "big") % buckets)
    return ids or [0]


def _validate_checkpoint(data):
    if not isinstance(data, dict) or data.get("schema") != "scientific-source-encoder-v1":
        raise ValueError("Unsupported scientific encoder checkpoint schema")
    vocab = data.get("vocabulary")
    if not isinstance(vocab, dict) or set(vocab.values()) != set(range(1, len(vocab)+1)):
        raise ValueError("Invalid vocabulary")
    if not all(isinstance(k, str) and type(v) is int for k, v in vocab.items()):
        raise ValueError("Invalid vocabulary entries")
    dim, buckets = data.get("width"), data.get("character_buckets")
    if type(dim) is not int or not 1 <= dim <= 256 or type(buckets) is not int or not 1 <= buckets <= 4096:
        raise ValueError("Invalid model dimensions")
    shapes = {"embedding": (len(vocab)+1+buckets, dim), "hidden_weight": (dim, dim),
              "hidden_bias": (dim,), "output_weight": (dim, dim), "output_bias": (dim,)}
    weights = data.get("weights")
    if not isinstance(weights, dict) or set(weights) != set(shapes):
        raise ValueError("Invalid model weight keys")
    def check(value, shape):
        if not shape:
            return type(value) in (int, float) and math.isfinite(value)
        return isinstance(value, list) and len(value) == shape[0] and all(check(v, shape[1:]) for v in value)
    if not all(check(weights[k], shape) for k, shape in shapes.items()):
        raise ValueError("Invalid model weight shape or non-finite weight")
    return data


@lru_cache(maxsize=8)
def _load_checkpoint(path_string, mtime_ns):
    path = Path(path_string)
    raw = path.read_bytes()
    expected = path.with_suffix(path.suffix + ".sha256").read_text().strip().split()[0]
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Checkpoint SHA256 mismatch")
    def reject_constant(value):
        raise ValueError("Non-finite JSON constant: " + value)
    return _validate_checkpoint(json.loads(raw, parse_constant=reject_constant))


def load_checkpoint(path=None):
    path = Path(path or DEFAULT_CHECKPOINT).resolve()
    # Include modification time in cache key so replaced artifacts are validated.
    return _load_checkpoint(str(path), path.stat().st_mtime_ns)


def _encode(text, model):
    """Pure Python inference, avoiding a PyTorch dependency for source ranking."""
    weights = model["weights"]
    ids = feature_ids(text, model["vocabulary"], model["character_buckets"])
    width = model["width"]
    pooled = [sum(weights["embedding"][i][d] for i in ids)/len(ids) for d in range(width)]
    hidden = [math.tanh(sum(a*b for a, b in zip(row, pooled))+bias)
              for row, bias in zip(weights["hidden_weight"], weights["hidden_bias"])]
    output = [sum(a*b for a, b in zip(row, hidden))+bias
              for row, bias in zip(weights["output_weight"], weights["output_bias"])]
    norm = math.sqrt(sum(v*v for v in output)) or 1
    return [v/norm for v in output]


def rank(query, candidates, mode="bm25", checkpoint=None):
    """Return scores aligned with candidates; larger means more source relevance.

    Candidate IDs/kinds/metadata are not model inputs. A score never establishes
    that a source is true, entails a claim, or carries checker authority.
    """
    if not isinstance(query, str):
        raise ValueError("query must be a string")
    if mode not in ("bm25", "tfidf", "neural"):
        raise ValueError("mode must be bm25, tfidf, or neural")
    texts = [_text(c) for c in candidates]
    if not texts:
        return []
    if mode != "neural":
        return _lexical(query, texts, mode)
    model = load_checkpoint(checkpoint)
    qv = _encode(query, model)
    return [sum(a*b for a, b in zip(qv, _encode(t, model))) for t in texts]
