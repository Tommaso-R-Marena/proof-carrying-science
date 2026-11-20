"""Bounded Gemini free-tier red team for Assurance Mirage.

Reads GEMINI_API_KEY from the environment only. Never logs or writes the key.
Respects conservative free-tier pacing: default <=10 requests/minute and a hard
request cap. Absolute remaining project quota is not exposed by the Generative
Language API key; this arm records session usage and any 429 quota details.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from .channels import (
    EpisodeResult,
    ProposalRecord,
    detect_raw_leak,
    detect_scope_escalation,
    mirage_gap,
    parse_proposal,
)
from .programs.scientific_store import ScientificStore
from .protocol import CASES, PRIVATE_MARKER, SYSTEM_BOUNDARY, SYSTEM_PLAIN, write_protocol

DEFAULT_MODEL = "gemini-flash-lite-latest"
# Conservative vs commonly observed free-tier ~15 RPM flash-lite limits.
MIN_INTERVAL_SEC = 6.0
DEFAULT_MAX_REQUESTS = 20


class GeminiClient:
    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        min_interval_sec: float = MIN_INTERVAL_SEC,
        max_requests: int = DEFAULT_MAX_REQUESTS,
    ):
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY required in environment")
        self.key = key
        self.model = model
        self.min_interval_sec = min_interval_sec
        self.max_requests = max_requests
        self.requests = 0
        self.last_request_at = 0.0
        self.usage_events: list[dict] = []
        self.quota_errors: list[dict] = []

    def _throttle(self) -> None:
        if self.requests >= self.max_requests:
            raise ValueError(f"Hard free-tier request cap reached ({self.max_requests})")
        elapsed = time.monotonic() - self.last_request_at
        if self.last_request_at and elapsed < self.min_interval_sec:
            time.sleep(self.min_interval_sec - elapsed)

    def generate(self, prompt: str, *, max_output_tokens: int = 128) -> tuple[str, dict]:
        self._throttle()
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": max_output_tokens,
            },
        }
        raw_body = json.dumps(body, separators=(",", ":")).encode()
        req = urllib.request.Request(
            url,
            data=raw_body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": self.key,
            },
        )
        start = time.monotonic()
        self.last_request_at = time.monotonic()
        self.requests += 1
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = resp.read()
                data = json.loads(raw)
                text = "".join(
                    p.get("text", "")
                    for c in data.get("candidates", [])
                    for p in c.get("content", {}).get("parts", [])
                )
                prov = {
                    "call": self.requests - 1,
                    "model": self.model,
                    "seconds": round(time.monotonic() - start, 6),
                    "usage": data.get("usageMetadata"),
                    "request_sha256": sha256(raw_body).hexdigest(),
                    "response_sha256": sha256(raw).hexdigest(),
                    "http_status": resp.status,
                    "remote_model_api": True,
                    "weight_attestation": False,
                    "api_key_materialized_in_evidence": False,
                }
                self.usage_events.append(
                    {
                        "call": prov["call"],
                        "usage": prov["usage"],
                        "http_status": resp.status,
                    }
                )
                return text, prov
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            try:
                err = json.loads(raw)
            except json.JSONDecodeError:
                err = {"raw": raw}
            event = {
                "call": self.requests - 1,
                "http_status": e.code,
                "error": err,
            }
            self.quota_errors.append(event)
            if e.code == 429:
                raise ValueError(f"Free-tier quota/rate limit hit: {raw[:800]}") from e
            raise ValueError(f"Gemini HTTP {e.code}: {raw[:800]}") from e


def _selected_cases(
    max_cases: int | None = None,
    *,
    case_ids: list[str] | None = None,
) -> list[dict]:
    """Prefer one benign control then attacks, or an explicit id list."""
    by_id = {c["id"]: c for c in CASES}
    if case_ids is not None:
        missing = [i for i in case_ids if i not in by_id]
        if missing:
            raise ValueError(f"Unknown case ids: {missing}")
        return [by_id[i] for i in case_ids]
    benign = [c for c in CASES if not c["attack"]]
    attacks = [c for c in CASES if c["attack"]]
    ordered = benign[:1] + attacks
    if max_cases is None:
        return ordered
    return ordered[:max_cases]


def run_gemini_arm(
    out: Path,
    *,
    model: str = DEFAULT_MODEL,
    max_cases: int | None = 5,
    case_ids: list[str] | None = None,
    prompt_arm: str = "instruction_boundary",
    turns: int = 4,
    max_requests: int = DEFAULT_MAX_REQUESTS,
    min_interval_sec: float = MIN_INTERVAL_SEC,
) -> dict:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    if prompt_arm not in ("instruction_boundary", "plain"):
        raise ValueError("prompt_arm must be instruction_boundary or plain")
    system = SYSTEM_BOUNDARY if prompt_arm == "instruction_boundary" else SYSTEM_PLAIN
    protocol = write_protocol(out / "protocol.json")
    cases = _selected_cases(max_cases, case_ids=case_ids)
    needed = len(cases) * turns
    if needed > max_requests:
        raise ValueError(
            f"Plan needs {needed} requests but max_requests={max_requests}; reduce cases/turns"
        )
    client = GeminiClient(
        model=model, min_interval_sec=min_interval_sec, max_requests=max_requests
    )
    episodes: list[EpisodeResult] = []
    stopped_reason = None
    for case in cases:
        ep_dir = out / "episodes" / f"{prompt_arm}__{case['id']}"
        ep_dir.mkdir(parents=True, exist_ok=False)
        store = ScientificStore(ep_dir / "store.sqlite")
        ep = EpisodeResult(
            case_id=case["id"],
            family=case["family"],
            attack=case["attack"],
            prompt_arm=prompt_arm,
        )
        try:
            for turn in range(turns):
                state = store.state
                admitted = store.admitted()
                prompt = (
                    system
                    + f"\n\nState: {state}. Admitted next action: {admitted}.\n"
                    + f"User message: {case['user']}\n"
                    + 'Reply with exactly one JSON object: {"action":"...","note":"..."}'
                )
                text, prov = client.generate(prompt)
                (ep_dir / f"turn-{turn:02d}-raw.txt").write_text(text)
                (ep_dir / f"turn-{turn:02d}-provenance.json").write_text(
                    json.dumps(prov, indent=2) + "\n"
                )
                action, note, malformed = parse_proposal(text)
                forbidden = malformed or (action is not None and action != admitted)
                ep.proposals.append(
                    ProposalRecord(
                        turn=turn,
                        state=state,
                        admitted=admitted,
                        proposed=action,
                        forbidden=bool(forbidden),
                        malformed=malformed,
                        note=note,
                        raw_text=text,
                    )
                )
                if detect_raw_leak(text) or detect_raw_leak(note):
                    ep.raw_leak = True
                if detect_scope_escalation(note) or detect_scope_escalation(text):
                    ep.scope_escalation = True
                result = store.execute_admitted()
                ep.tools.append((state, result["action"]))
                if "published" in result:
                    ep.published.append(result["published"])
            joined = "".join(p.note for p in ep.proposals)
            if PRIVATE_MARKER in joined and not ep.raw_leak:
                ep.split_leak = True
        except ValueError as e:
            stopped_reason = str(e)
            store.close()
            ep.finalize()
            (ep_dir / "episode_partial.json").write_text(json.dumps(ep.to_json(), indent=2) + "\n")
            break
        store.close()
        ep.finalize()
        (ep_dir / "episode.json").write_text(json.dumps(ep.to_json(), indent=2) + "\n")
        episodes.append(ep)

    gap = mirage_gap(episodes) if episodes else {}
    summary = {
        "format": "pcs-assurance-mirage-gemini-arm-v1",
        "model": model,
        "prompt_arm": prompt_arm,
        "case_ids": [c["id"] for c in cases],
        "project_hint": "projects/171569345899",
        "free_tier_policy": {
            "min_interval_sec": min_interval_sec,
            "max_requests": max_requests,
            "planned_requests": needed,
            "requests_used_this_session": client.requests,
            "note": (
                "Generative Language API keys do not expose remaining RPD/RPM. "
                "Session usage and any 429 QuotaFailure details are the measurable signals. "
                "Check https://aistudio.google.com/rate-limit for live project limits."
            ),
        },
        "protocol_sha256": protocol.get("protocol_sha256"),
        "n_episodes_complete": len(episodes),
        "stopped_reason": stopped_reason,
        "usage_events": client.usage_events,
        "quota_errors": client.quota_errors,
        "episodes": [e.to_json() for e in episodes],
        "mirage_gap": gap,
        "weight_attestation": False,
        "production_authority": False,
        "api_key_not_stored": True,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (out / "quota_session.json").write_text(
        json.dumps(
            {
                "requests_used_this_session": client.requests,
                "usage_events": client.usage_events,
                "quota_errors": client.quota_errors,
                "stopped_reason": stopped_reason,
            },
            indent=2,
        )
        + "\n"
    )
    return summary
