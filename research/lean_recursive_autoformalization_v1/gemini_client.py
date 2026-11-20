"""Minimal Gemini client with free-tier rate limiting.

Reads API key ONLY from env `GEMINI_API_KEY` (never hardcode / never commit).
Tracks local usage; Generative Language API does not return remaining quota.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


# Conservative free-tier defaults for gemini-*-flash-lite family
# (AI Studio often shows ~15 RPM / ~500 RPD for flash-lite; we stay under).
DEFAULT_MODEL = "gemini-3.1-flash-lite"
DEFAULT_RPM = 10
DEFAULT_RPD_SOFT = 80  # soft stop for this research harness (<< typical 500 RPD)
DEFAULT_MIN_INTERVAL_S = 6.5  # ~9 RPM max


@dataclass
class UsageLedger:
    model: str
    requests: int = 0
    successes: int = 0
    failures: int = 0
    prompt_tokens: int = 0
    candidates_tokens: int = 0
    total_tokens: int = 0
    http_statuses: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def record(self, *, ok: bool, status: int, usage: dict[str, Any] | None) -> None:
        self.requests += 1
        if ok:
            self.successes += 1
        else:
            self.failures += 1
        key = str(status)
        self.http_statuses[key] = self.http_statuses.get(key, 0) + 1
        if usage:
            self.prompt_tokens += int(usage.get("promptTokenCount") or 0)
            self.candidates_tokens += int(usage.get("candidatesTokenCount") or 0)
            self.total_tokens += int(usage.get("totalTokenCount") or 0)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class GeminiClient:
    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        rpm: int = DEFAULT_RPM,
        rpd_soft: int = DEFAULT_RPD_SOFT,
        min_interval_s: float = DEFAULT_MIN_INTERVAL_S,
        ledger_path: Path | None = None,
    ) -> None:
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key:
            raise RuntimeError("GEMINI_API_KEY env var required (do not commit secrets)")
        if key.startswith("AQ.") is False and len(key) < 20:
            raise RuntimeError("GEMINI_API_KEY looks invalid")
        self.api_key = key
        self.model = model
        self.rpm = rpm
        self.rpd_soft = rpd_soft
        self.min_interval_s = max(min_interval_s, 60.0 / max(1, rpm))
        self._last_call = 0.0
        self.ledger = UsageLedger(model=model)
        self.ledger_path = ledger_path

    def _throttle(self) -> None:
        if self.ledger.requests >= self.rpd_soft:
            raise RuntimeError(
                f"soft free-tier stop: {self.ledger.requests} requests >= {self.rpd_soft} RPD soft cap"
            )
        elapsed = time.time() - self._last_call
        wait = self.min_interval_s - elapsed
        if wait > 0:
            time.sleep(wait)

    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.0,
        max_output_tokens: int = 512,
        retries: int = 3,
    ) -> dict[str, Any]:
        self._throttle()
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            },
        }
        data = json.dumps(body).encode("utf-8")
        last_err: Exception | None = None
        for attempt in range(retries):
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "X-goog-api-key": self.api_key,
                },
                method="POST",
            )
            self._last_call = time.time()
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    raw = resp.read().decode("utf-8")
                    status = getattr(resp, "status", 200) or 200
                    payload = json.loads(raw)
                    usage = payload.get("usageMetadata") or {}
                    text = ""
                    cands = payload.get("candidates") or []
                    if cands:
                        parts = ((cands[0].get("content") or {}).get("parts")) or []
                        text = "".join(str(p.get("text") or "") for p in parts)
                    self.ledger.record(ok=True, status=status, usage=usage)
                    self._persist()
                    return {
                        "ok": True,
                        "text": text.strip(),
                        "usage": usage,
                        "raw": payload,
                        "status": status,
                    }
            except urllib.error.HTTPError as ex:
                last_err = ex
                err_body = ex.read().decode("utf-8", errors="replace")
                try:
                    err_json = json.loads(err_body)
                except json.JSONDecodeError:
                    err_json = {"error": {"message": err_body[:400]}}
                self.ledger.record(ok=False, status=ex.code, usage=None)
                self.ledger.notes.append(f"HTTP {ex.code}: {(err_json.get('error') or {}).get('message','')[:160]}")
                self._persist()
                if ex.code in {429, 503, 500} and attempt + 1 < retries:
                    time.sleep(2 ** (attempt + 2))
                    continue
                return {
                    "ok": False,
                    "text": "",
                    "error": err_json,
                    "status": ex.code,
                    "usage": {},
                }
            except Exception as ex:  # noqa: BLE001
                last_err = ex
                self.ledger.record(ok=False, status=0, usage=None)
                self.ledger.notes.append(str(ex)[:160])
                self._persist()
                if attempt + 1 < retries:
                    time.sleep(2 ** (attempt + 1))
                    continue
                return {"ok": False, "text": "", "error": {"message": str(ex)}, "status": 0, "usage": {}}
        return {"ok": False, "text": "", "error": {"message": str(last_err)}, "status": 0, "usage": {}}

    def _persist(self) -> None:
        if not self.ledger_path:
            return
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger_path.write_text(json.dumps(self.ledger.as_dict(), indent=2, sort_keys=True) + "\n")


def probe_quota(*, model: str = DEFAULT_MODEL) -> dict[str, Any]:
    """Run a tiny generate + report that remaining quota is not API-visible."""
    client = GeminiClient(model=model, rpd_soft=5, min_interval_s=1.0)
    result = client.generate("Reply with exactly: pong", max_output_tokens=8)
    return {
        "format": "pcs-pgra-gemini-quota-probe-v1",
        "model": model,
        "generate_ok": result.get("ok"),
        "usage_this_request": result.get("usage"),
        "session_ledger": client.ledger.as_dict(),
        "remaining_quota_visible_in_api": False,
        "note": (
            "Google Generative Language generateContent responses expose per-request "
            "usageMetadata but not project remaining RPM/TPM/RPD. View remaining quota "
            "in Google AI Studio → Usage & Billing for project 171569345899. "
            "This harness enforces local soft caps under published free-tier flash-lite limits."
        ),
        "assumed_free_tier_flash_lite": {
            "rpm_soft": DEFAULT_RPM,
            "rpd_soft_harness": DEFAULT_RPD_SOFT,
            "typical_flash_lite_rpd": 500,
            "typical_flash_rpd": 20,
        },
        "pcs_scientific_authority": False,
    }


__all__ = ["GeminiClient", "UsageLedger", "probe_quota", "DEFAULT_MODEL"]
