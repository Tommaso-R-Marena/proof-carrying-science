"""Model-provider transport: Gemini and OpenRouter.

Security and data-handling rules enforced here:

* Credentials are read only from the environment (GEMINI_API_KEY / OPENROUTER_API_KEY) at call
  time.  They are sent only as a header to the one fixed host of that provider, never placed in a
  URL, a prompt, a cache key, a log line, an exception message or a returned object.
* Redirects are refused (a redirect would forward the credential header).
* Nothing is sent unless the caller passes ``allow_network=True``.  Free provider tiers may retain
  or train on inputs, so callers must only send text they are entitled to disclose (the benchmark
  sends only openly licensed, already-public article text and column names — never data rows).
* Every call is bounded (bytes in, bytes out, seconds) and counted in a ledger with a hard cap.
* Responses are cached on disk by a digest of (provider, model, prompt) so that re-runs and
  independent audits never need a second call.  Cached records contain no credential.

A model's output is untrusted data.  Nothing in this module can mark a claim as verified.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

MAX_PROMPT_BYTES = 400_000
MAX_RESPONSE_BYTES = 2_000_000
HOSTS = {"gemini": "generativelanguage.googleapis.com", "openrouter": "openrouter.ai"}
ENV = {"gemini": "GEMINI_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
MODEL_RE = {
    "gemini": re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}\Z"),
    "openrouter": re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}/[A-Za-z0-9][A-Za-z0-9._:-]{0,79}\Z"),
}


class ProviderError(RuntimeError):
    """Deliberately carries no response body and no header content."""


class BudgetExceeded(ProviderError):
    pass


@dataclass
class Ledger:
    """Counts real network calls and reported token usage; refuses calls beyond the cap."""

    max_calls: dict = field(default_factory=lambda: {"gemini": 60, "openrouter": 40})
    calls: dict = field(default_factory=lambda: {"gemini": 0, "openrouter": 0})
    cache_hits: dict = field(default_factory=lambda: {"gemini": 0, "openrouter": 0})
    prompt_tokens: dict = field(default_factory=lambda: {"gemini": 0, "openrouter": 0})
    output_tokens: dict = field(default_factory=lambda: {"gemini": 0, "openrouter": 0})
    seconds: dict = field(default_factory=lambda: {"gemini": 0.0, "openrouter": 0.0})
    failures: dict = field(default_factory=lambda: {"gemini": 0, "openrouter": 0})

    def to_json(self) -> dict:
        return {"max_calls": self.max_calls, "network_calls": self.calls, "cache_hits": self.cache_hits,
                "prompt_tokens": self.prompt_tokens, "output_tokens": self.output_tokens,
                "seconds": {k: round(v, 2) for k, v in self.seconds.items()}, "failures": self.failures}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401, ANN001
        return None


def _post(url: str, headers: dict, payload: dict, timeout: int) -> tuple[int, dict | None]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read(MAX_RESPONSE_BYTES + 1)
            status = resp.status
    except urllib.error.HTTPError as exc:
        return exc.code, None          # body intentionally discarded
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, None
    if len(raw) > MAX_RESPONSE_BYTES:
        return status, None
    try:
        data = json.loads(raw)
    except ValueError:
        return status, None
    return status, data if isinstance(data, dict) else None


def cache_key(provider: str, model: str, prompt: str, system: str) -> str:
    h = hashlib.sha256()
    for part in (provider, model, system, prompt):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def complete(provider: str, model: str, prompt: str, *, system: str = "", ledger: Ledger, cache_dir: Path | None,
             allow_network: bool, timeout: int = 180, max_output_tokens: int = 8192, retries: int = 3,
             transport=_post) -> dict:
    """One bounded text completion.  Returns ``{"text", "cached", "usage", "model", "provider", "key"}``."""
    if provider not in HOSTS:
        raise ProviderError("unsupported provider")
    if not model or not MODEL_RE[provider].match(model):
        raise ProviderError("model identifier rejected")
    if len(prompt.encode("utf-8")) + len(system.encode("utf-8")) > MAX_PROMPT_BYTES:
        raise ProviderError("prompt exceeds the configured size bound")
    key = cache_key(provider, model, prompt, system)
    cache_file = None if cache_dir is None else cache_dir / f"{provider}-{key[:32]}.json"
    if cache_file is not None and cache_file.exists():
        rec = json.loads(cache_file.read_text(encoding="utf-8"))
        if rec.get("key") == key:
            ledger.cache_hits[provider] += 1
            rec["cached"] = True
            return rec
    if not allow_network:
        raise ProviderError("network use was not authorised and no cached response exists")
    secret = os.environ.get(ENV[provider], "").strip()
    if not secret:
        raise ProviderError(f"{ENV[provider]} is not set")
    if provider == "gemini":
        url = f"https://{HOSTS[provider]}/v1beta/models/{model}:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": secret}
        payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                   "generationConfig": {"temperature": 0, "maxOutputTokens": max_output_tokens,
                                        "responseMimeType": "application/json"}}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
    else:
        url = f"https://{HOSTS[provider]}/api/v1/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + secret}
        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        payload = {"model": model, "temperature": 0, "max_tokens": max_output_tokens, "messages": messages}
    last = "no attempt"
    for attempt in range(retries + 1):
        if ledger.calls[provider] >= ledger.max_calls[provider]:
            raise BudgetExceeded(f"{provider} call budget exhausted")
        ledger.calls[provider] += 1
        start = time.monotonic()
        status, data = transport(url, headers, payload, timeout)
        ledger.seconds[provider] += time.monotonic() - start
        text, usage, finish = None, {}, None
        if status == 200 and data is not None:
            try:
                if provider == "gemini":
                    cand = data["candidates"][0]
                    finish = cand.get("finishReason")
                    text = "".join(p.get("text", "") for p in cand["content"]["parts"] if not p.get("thought"))
                    um = data.get("usageMetadata", {})
                    usage = {"prompt_tokens": um.get("promptTokenCount", 0),
                             "output_tokens": um.get("candidatesTokenCount", 0) + um.get("thoughtsTokenCount", 0)}
                else:
                    choice = data["choices"][0]
                    finish = choice.get("finish_reason")
                    text = choice["message"]["content"]
                    um = data.get("usage", {})
                    usage = {"prompt_tokens": um.get("prompt_tokens", 0), "output_tokens": um.get("completion_tokens", 0)}
            except (KeyError, IndexError, TypeError):
                text = None
        if isinstance(text, str) and text.strip():
            ledger.prompt_tokens[provider] += int(usage.get("prompt_tokens") or 0)
            ledger.output_tokens[provider] += int(usage.get("output_tokens") or 0)
            rec = {"provider": provider, "model": model, "key": key, "text": text, "usage": usage,
                   "finish": finish, "cached": False, "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest()}
            if cache_file is not None:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(json.dumps({**rec, "cached": False}, ensure_ascii=False, indent=1), encoding="utf-8")
            return rec
        ledger.failures[provider] += 1
        last = f"HTTP {status}" if status else "transport failure"
        if status in (400, 401, 403, 404):
            break
        time.sleep(min(60, 8 * (attempt + 1)))
    raise ProviderError(f"{provider} did not return a usable completion ({last})")


def extract_json(text: str) -> dict | None:
    """Best-effort extraction of one JSON object from model text (models add fences and prose)."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[A-Za-z]*\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except ValueError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        obj = json.loads(text[start:end + 1])
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None
