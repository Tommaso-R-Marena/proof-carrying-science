"""Rate-limited Gemini evaluation for PCCR causal claims.

API key MUST come from the environment variable GEMINI_API_KEY.
Never write the key into results, evidence, commits, or logs.

Free-tier courtesy defaults:
  - model: gemini-2.5-flash-lite
  - min 8s between requests
  - max 12 requests per run
  - single retry on 429/503 with 20s backoff
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from research.proof_carrying_causal_reasoning_v1.experiment import (
    all_research_tasks,
    evaluate_model_responses,
)
from research.proof_carrying_causal_reasoning_v1.tasks.battery import Task

DEFAULT_MODEL = "gemini-3.5-flash-lite"
MIN_INTERVAL_SEC = 8.0
MAX_REQUESTS = 12
MAX_OUTPUT_CHARS = 4096


def _api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Export it in the shell; do not paste into files."
        )
    if key.startswith("AQ.") and len(key) < 20:
        raise RuntimeError("GEMINI_API_KEY looks truncated")
    return key


def _endpoint(model: str) -> str:
    return (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )


def generate(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
    max_output_tokens: int = 512,
) -> Dict[str, Any]:
    """One generateContent call forcing JSON (PCCR task battery)."""
    return _generate_raw(
        "You answer causal identification questions. "
        "Output a single JSON object only. No markdown.\n\n" + prompt,
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        response_mime_type="application/json",
        timeout_sec=120,
    )


def generate_text(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
    max_output_tokens: int = 2048,
    timeout_sec: int = 180,
) -> Dict[str, Any]:
    """Free-form text generateContent (CausalCoT / debate)."""
    return _generate_raw(
        prompt,
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        response_mime_type=None,
        timeout_sec=timeout_sec,
    )


def _generate_raw(
    prompt: str,
    *,
    model: str,
    temperature: float,
    max_output_tokens: int,
    response_mime_type: Optional[str],
    timeout_sec: int,
) -> Dict[str, Any]:
    """Shared generateContent helper. Returns redacted provenance + text."""
    key = _api_key()
    gen_cfg: Dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens,
    }
    if response_mime_type:
        gen_cfg["responseMimeType"] = response_mime_type
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": gen_cfg,
    }
    raw = json.dumps(body, separators=(",", ":")).encode()
    req = urllib.request.Request(
        _endpoint(model),
        data=raw,
        headers={
            "Content-Type": "application/json",
            "X-goog-api-key": key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            payload = resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:800]
        return {
            "ok": False,
            "status": e.code,
            "error": err_body,
            "text": "",
            "request_sha256": hashlib.sha256(raw).hexdigest(),
        }
    except TimeoutError as e:
        return {
            "ok": False,
            "status": 598,
            "error": f"timeout:{e}",
            "text": "",
            "request_sha256": hashlib.sha256(raw).hexdigest(),
        }
    except Exception as e:  # noqa: BLE001 — network resilience
        return {
            "ok": False,
            "status": 599,
            "error": f"{type(e).__name__}:{e}",
            "text": "",
            "request_sha256": hashlib.sha256(raw).hexdigest(),
        }
    data = json.loads(payload.decode())
    text = _extract_text(data)
    if len(text) > MAX_OUTPUT_CHARS * 4:
        text = text[: MAX_OUTPUT_CHARS * 4]
    return {
        "ok": True,
        "status": status,
        "text": text,
        "request_sha256": hashlib.sha256(raw).hexdigest(),
        "response_sha256": hashlib.sha256(payload).hexdigest(),
        "model": model,
        # Never store API key material.
        "api_key_present": True,
        "finish_reason": _finish_reason(data),
        "usage": data.get("usageMetadata"),
    }


def _extract_text(data: dict) -> str:
    cands = data.get("candidates") or []
    if not cands:
        return ""
    parts = ((cands[0].get("content") or {}).get("parts")) or []
    chunks = [p.get("text", "") for p in parts if isinstance(p.get("text"), str)]
    return "".join(chunks)


def _finish_reason(data: dict) -> Optional[str]:
    cands = data.get("candidates") or []
    if not cands:
        return None
    return cands[0].get("finishReason")


def run_gemini(
    out: Path,
    *,
    model: str = DEFAULT_MODEL,
    task_ids: Optional[Sequence[str]] = None,
    min_interval_sec: float = MIN_INTERVAL_SEC,
    max_requests: int = MAX_REQUESTS,
) -> Dict[str, Any]:
    tasks = list(all_research_tasks())
    if task_ids:
        wanted = set(task_ids)
        tasks = [t for t in tasks if t.task_id in wanted]
    if len(tasks) > max_requests:
        tasks = tasks[:max_requests]

    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    responses: Dict[str, str] = {}
    provenance: List[dict] = []
    last = 0.0

    for i, task in enumerate(tasks):
        wait = min_interval_sec - (time.monotonic() - last)
        if i > 0 and wait > 0:
            time.sleep(wait)
        attempt = 0
        result: Dict[str, Any]
        while True:
            attempt += 1
            last = time.monotonic()
            result = generate(task.prompt, model=model)
            if result.get("ok"):
                break
            status = result.get("status")
            if status in (429, 503) and attempt < 3:
                time.sleep(20.0 * attempt)
                continue
            break
        text = result.get("text") or ""
        responses[task.task_id] = text
        # Redacted provenance only
        provenance.append(
            {
                "task_id": task.task_id,
                "ok": result.get("ok"),
                "status": result.get("status"),
                "model": model,
                "request_sha256": result.get("request_sha256"),
                "response_sha256": result.get("response_sha256"),
                "finish_reason": result.get("finish_reason"),
                "usage": result.get("usage"),
                "error": result.get("error"),
                "attempt": attempt,
            }
        )
        (out / f"response_{task.task_id}.txt").write_text(text)
        (out / f"call_{task.task_id}.json").write_text(
            json.dumps(provenance[-1], indent=2) + "\n"
        )

    scored = evaluate_model_responses(tasks, responses)
    payload = {
        "provider": "google-generativelanguage",
        "model": model,
        "min_interval_sec": min_interval_sec,
        "max_requests": max_requests,
        "n_calls": len(provenance),
        "provenance": provenance,
        "evaluation": scored,
        "claims": {
            "frontier_sota": False,
            "production_authority": False,
            "empirical_causation_established": False,
            "api_key_not_stored": True,
            "rate_limited": True,
            "local_measurement_only": True,
        },
    }
    (out / "gemini_eval.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    return payload
