"""Spending guard and call harness for the proposer calls of the prospective evaluation (protocol 2, 13).

Nothing here sends anything by itself, and nothing here authorises a call: that is the owner's
decision after approval.  The frozen v1 code is not changed:

* ``BudgetGuard.transport`` has the signature of the transport ``claimcheck_v1.providers.complete``
  accepts.  ``installed(guard)`` substitutes ``claimcheck_v1.propose.complete`` with
  ``functools.partial(providers.complete, transport=guard.transport)`` for the duration of a block,
  so every request made by the frozen ``propose_with_model`` passes through the guard.
* Before each request the guard checks the model identifier against the frozen configuration
  (``model_config.json``), refuses a provider without a frozen price, applies the daily request
  limit, and computes the worst case the request could cost: prompt and system bytes (an upper
  bound on prompt tokens, assuming no token is shorter than one byte) plus the request's maximum
  output tokens, at the frozen prices.  If the money committed so far plus that worst case would
  exceed the provider's sub-cap or the total cap, it raises ``SpendingRefused`` (a ``ProviderError``)
  and sends nothing.
* Every request is written to an append-only JSON-lines spend log, and synced, before it is sent;
  its result after.  A resumed guard rebuilds its totals from the log, and a request that was sent
  but has no result line (a crash) is charged its worst case.  A guard refuses to start if cached
  responses exist but the log does not.
* ``fetch_proposals`` makes one ``propose_with_model`` call per model per document and nothing
  else (no critic calls, protocol 2), applies pacing and the re-issue rule (protocol 2), and sets
  the attempt budget of the frozen ledger to four attempts per call.

Tests use a synthetic transport only (``tests/test_budget.py``).
"""
from __future__ import annotations

import contextlib
import datetime
import functools
import hashlib
import json
import os
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

from ...claimcheck_v1 import propose as _propose
from ...claimcheck_v1 import providers as _providers

CONFIG = Path(__file__).with_name("model_config.json")
PROVIDERS = ("gemini", "openrouter")
HOST_PROVIDER = {"generativelanguage.googleapis.com": "gemini", "openrouter.ai": "openrouter"}
NO_REPEAT = (200, 400, 401, 403, 404)          # as providers.complete: these statuses are never repeated
FINAL_OUTCOMES = ("ok", "no_text", "deterministic")


class SpendingRefused(_providers.BudgetExceeded):
    """Raised before a request is sent; carries no request or response content."""


def load_config(path: Path = CONFIG) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _utc(t: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc)


def _identify(url: str, payload: dict) -> tuple[str | None, str | None]:
    parts = urlsplit(url)
    provider = HOST_PROVIDER.get(parts.hostname or "")
    if provider == "gemini":
        tail = parts.path.rsplit("/models/", 1)[-1]
        return provider, tail.split(":", 1)[0] if ":generateContent" in tail else None
    if provider == "openrouter":
        return provider, payload.get("model")
    return None, None


def _prompt_bytes(provider: str, payload: dict) -> int:
    if provider == "gemini":
        texts = [p.get("text", "") for c in payload.get("contents", []) for p in c.get("parts", [])]
        texts += [p.get("text", "") for p in (payload.get("systemInstruction") or {}).get("parts", [])]
    else:
        texts = [m.get("content", "") for m in payload.get("messages", [])]
    return sum(len(t.encode("utf-8")) for t in texts if isinstance(t, str))


def _max_output(provider: str, payload: dict) -> int | None:
    v = (payload.get("generationConfig") or {}).get("maxOutputTokens") if provider == "gemini" else payload.get("max_tokens")
    return v if isinstance(v, int) and v > 0 else None


def _usage(provider: str, data) -> tuple[int, int] | None:
    if not isinstance(data, dict):
        return None
    if provider == "gemini":
        u = data.get("usageMetadata")
        if not isinstance(u, dict) or "promptTokenCount" not in u:
            return None
        return int(u.get("promptTokenCount") or 0), int(u.get("candidatesTokenCount") or 0) + int(u.get("thoughtsTokenCount") or 0)
    u = data.get("usage")
    if not isinstance(u, dict) or "prompt_tokens" not in u:
        return None
    return int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0)


def _has_text(provider: str, data) -> bool:
    try:
        if provider == "gemini":
            parts = data["candidates"][0]["content"]["parts"]
            return any(isinstance(p.get("text"), str) and p["text"].strip() and not p.get("thought") for p in parts)
        content = data["choices"][0]["message"]["content"]
        return isinstance(content, str) and bool(content.strip())
    except (KeyError, IndexError, TypeError, AttributeError):
        return False


def _served(provider: str, data) -> dict:
    """What the provider says it served (model version, route), for the record; never content."""
    if not isinstance(data, dict):
        return {}
    keys = ("modelVersion", "responseId") if provider == "gemini" else ("model", "provider", "id")
    return {k: data[k] for k in keys if isinstance(data.get(k), str)}


def _outcome(provider: str, status: int, data) -> str:
    if status == 200:
        return "ok" if _has_text(provider, data) else "no_text"
    return "deterministic" if status in NO_REPEAT else "retryable"


class BudgetGuard:
    def __init__(self, configuration: str, papers: int, log_path: Path, *, owner_authorisation: str, config: dict | None = None,
                 inner=None, clock=time.time, cache_dir: Path | None = None, session: str = "1"):
        if not (isinstance(owner_authorisation, str) and owner_authorisation.strip()):
            raise SpendingRefused("no recorded owner authorisation: no request may be sent")
        cfg = config or load_config()
        conf = cfg["configurations"][configuration]
        self.configuration, self.papers, self.session = configuration, papers, session
        self.providers = conf["providers"]
        caps = conf["caps_usd"][str(papers)]
        self.cap_total, self.sub_caps = float(caps["total"]), {p: float(caps[p]) for p in PROVIDERS}
        self.attempts_per_call = int(cfg["attempts_per_call"])
        self.log_path = Path(log_path)
        self.inner = inner if inner is not None else _providers._post
        self.clock = clock
        self.current: tuple[str, str] | None = None
        self._lock = threading.Lock()
        if cache_dir is not None and Path(cache_dir).exists() and any(Path(cache_dir).glob("*.json")) and not self.log_path.exists():
            raise SpendingRefused("cached responses exist but the spend log does not: refusing to restart the count at zero")
        self.spent = {p: 0.0 for p in PROVIDERS}
        self.requests_per_day: dict[tuple[str, str], int] = {}
        self._seq = 0
        sent: dict[int, dict] = {}
        for line in read_log(self.log_path):
            if line["event"] == "sent":
                sent[line["seq"]] = line
                key = (line["provider"], line["time"][:10])
                self.requests_per_day[key] = self.requests_per_day.get(key, 0) + 1
                self._seq = max(self._seq, line["seq"])
            elif line["event"] == "result":
                self.spent[line["provider"]] += line["charged_usd"]
                sent.pop(line["seq"], None)
        for line in sent.values():                     # sent, but no result: may have been billed
            self.spent[line["provider"]] += line["worst_usd"]
        self._append({"event": "session", "time": _utc(self.clock()).isoformat(), "session": session, "configuration": configuration,
                      "papers": papers, "owner_authorisation": owner_authorisation.strip(), "cap_total_usd": self.cap_total,
                      "sub_caps_usd": self.sub_caps, "spent_usd_at_start": dict(self.spent)})

    # -- log
    def _append(self, rec: dict) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def total(self) -> float:
        return sum(self.spent.values())

    def can_start(self, provider: str) -> bool:
        limit = self.providers[provider].get("max_requests_per_utc_day")
        return limit is None or self.requests_per_day.get((provider, _utc(self.clock()).date().isoformat()), 0) < limit

    def _refuse(self, provider, reason: str, worst: float | None = None):
        self._append({"event": "refused", "time": _utc(self.clock()).isoformat(), "session": self.session, "call": self.current,
                      "provider": provider, "reason": reason, "worst_usd": worst})
        raise SpendingRefused(f"{provider}: {reason}")

    # -- the transport
    def transport(self, url: str, headers: dict, payload: dict, timeout: int):
        with self._lock:
            provider, model = _identify(url, payload)
            if provider is None:
                self._refuse(None, "unknown provider host")
            frozen = self.providers[provider]
            if model != frozen["model"]:
                self._refuse(provider, "model identifier differs from the frozen configuration")
            p_in, p_out = frozen["usd_per_million_prompt_tokens"], frozen["usd_per_million_output_tokens"]
            if p_in is None or p_out is None:
                self._refuse(provider, "no frozen price")
            max_out = _max_output(provider, payload)
            if max_out is None:
                self._refuse(provider, "the request does not bound its output")
            prompt_bytes = _prompt_bytes(provider, payload)
            worst = (prompt_bytes * p_in + max_out * p_out) / 1e6
            if not self.can_start(provider):
                self._refuse(provider, "daily request limit reached", worst)
            if self.spent[provider] + worst > self.sub_caps[provider] + 1e-12 or self.total() + worst > self.cap_total + 1e-12:
                self._refuse(provider, "cost cap: the worst case of this request would exceed the cap", worst)
            self._seq += 1
            seq, now = self._seq, _utc(self.clock()).isoformat()
            digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
            self._append({"event": "sent", "seq": seq, "time": now, "session": self.session, "call": self.current, "provider": provider,
                          "model": model, "request_sha256": digest, "prompt_bytes": prompt_bytes, "max_output_tokens": max_out,
                          "worst_usd": worst})
            day = (provider, now[:10])
            self.requests_per_day[day] = self.requests_per_day.get(day, 0) + 1
            self.spent[provider] += worst                                 # reserved while the request is in flight
        try:
            status, data = self.inner(url, headers, payload, timeout)   # outside the lock: the request itself
        except BaseException:
            status, data = 0, None                                        # treated as a transport failure, then re-raised
            raise
        finally:
            with self._lock:
                usage = _usage(provider, data) if status == 200 else None
                if usage is not None:
                    charged = (usage[0] * p_in + usage[1] * p_out) / 1e6
                elif 400 <= status < 500:
                    charged = 0.0
                else:
                    charged = worst
                self.spent[provider] += charged - worst
                self._append({"event": "result", "seq": seq, "time": _utc(self.clock()).isoformat(), "session": self.session,
                              "call": self.current, "provider": provider, "status": status, "outcome": _outcome(provider, status, data),
                              "usage": list(usage) if usage else None, "charged_usd": charged, "served": _served(provider, data),
                              "spent_total_usd": self.total()})
        return status, data



def read_log(path: Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@contextlib.contextmanager
def installed(guard: BudgetGuard):
    """Route every request of the frozen ``propose_with_model`` through ``guard`` for this block."""
    original = _propose.complete
    _propose.complete = functools.partial(_providers.complete, transport=guard.transport)
    try:
        yield guard
    finally:
        _propose.complete = original


def call_state(log: list[dict], call: tuple[str, str], *, max_sessions: int, min_hours: float, now: float) -> str:
    """"new" (never attempted), "final" (answered, failed deterministically, or refused by a cap),
    "retry" (may be sent again now) or "wait" (retryable, but too soon or no session left)."""
    lines = [x for x in log if x.get("call") and tuple(x["call"]) == tuple(call) and x["event"] in ("sent", "result", "refused")]
    if not lines:
        return "new"
    if any(x["event"] == "result" and x["outcome"] in FINAL_OUTCOMES for x in lines):
        return "final"
    if any(x["event"] == "refused" and not x["reason"].startswith("daily request limit") for x in lines):
        return "final"
    sessions = {x["session"] for x in lines if x["event"] == "sent"}
    last = max(datetime.datetime.fromisoformat(x["time"]).timestamp() for x in lines)
    if len(sessions) >= max_sessions or now - last < min_hours * 3600:
        return "wait" if len(sessions) < max_sessions else "final"
    return "retry"


def fetch_proposals(documents: list[dict], guard: BudgetGuard, *, cache_dir: Path, config: dict | None = None) -> dict:
    """One ``propose_with_model`` call per model per document (``documents``: key, text, data,
    manifest).  Never a critic call.  Pacing: a call is not started once its provider's daily limit
    is reached ("deferred", not a failure).  Re-issue: a call whose attempts all failed with
    retryable errors may be sent again in later sessions, at least 24 h apart, in at most
    1 + max_further_rounds sessions in all."""
    cfg = config or load_config()
    rule = cfg["reissue"]
    log = read_log(guard.log_path)
    ledger = _providers.Ledger(max_calls={p: guard.attempts_per_call * len(documents) for p in PROVIDERS})
    out = {}
    with installed(guard):
        for doc in documents:
            for provider in PROVIDERS:
                call = (doc["key"], provider)
                state = call_state(log, call, max_sessions=1 + rule["max_further_rounds"], min_hours=rule["min_hours_between_rounds"],
                                   now=guard.clock())
                if state not in ("new", "retry"):
                    out[call] = {"status": state}
                    continue
                if not guard.can_start(provider):
                    out[call] = {"status": "deferred: daily request limit"}
                    continue
                guard.current = call
                try:
                    props, meta = _propose.propose_with_model(provider, guard.providers[provider]["model"], doc["text"], doc["data"],
                                                              doc["manifest"], allow_network=True, ledger=ledger, cache_dir=cache_dir)
                finally:
                    guard.current = None
                out[call] = {"status": "answered" if not meta.get("error") else "failed", "parsed": bool(meta.get("parsed")),
                             "proposals": len(props), "error": meta.get("error")}
    return {"calls": out, "ledger": ledger.to_json(), "spent_usd": dict(guard.spent)}


def primary_complete(calls: dict, papers: dict[str, tuple[str, str]]) -> dict[str, bool]:
    """Protocol 2: a paper is primary-complete when both models returned a parseable answer for both
    of its documents.  ``papers[id] = (original key, planted-copy key)``."""
    return {pid: all(calls.get((k, p), {}).get("parsed") for k in keys for p in PROVIDERS) for pid, keys in papers.items()}
