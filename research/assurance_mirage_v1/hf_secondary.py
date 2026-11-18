"""Optional secondary red team via Hugging Face Inference Providers.

Uses only synthetic prompts and the same correcting-guard program. Requires a
token with inference access. Failures are recorded as unavailable, not as model
safety. This does not replace the local pinned-weight campaign.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import time

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

# Small open instruct model commonly served; identity recorded in evidence.
HF_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"


def _complete(client, model: str, messages: list[dict]) -> tuple[str, dict]:
    start = time.monotonic()
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
        max_tokens=128,
        seed=42,
    )
    choice = resp.choices[0]
    text = choice.message.content or ""
    prov = {
        "model": model,
        "seconds": round(time.monotonic() - start, 6),
        "finish_reason": getattr(choice, "finish_reason", None),
        "provider": "huggingface_inference",
        "remote_model_api": True,
        "weight_attestation": False,
    }
    return text, prov


def run_hf_secondary(out: Path, *, max_cases: int | None = 5) -> dict:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    try:
        from huggingface_hub import InferenceClient
    except ImportError as e:
        raise ValueError("huggingface_hub required for secondary arm") from e
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    # InferenceClient also picks up cached login; token may be None.
    client = InferenceClient(token=token, provider="auto")
    protocol = write_protocol(out / "protocol.json")
    cases = CASES if max_cases is None else CASES[:max_cases]
    episodes: list[EpisodeResult] = []
    errors: list[dict] = []
    for case in cases:
        ep_dir = out / "episodes" / case["id"]
        ep_dir.mkdir(parents=True, exist_ok=False)
        store = ScientificStore(ep_dir / "store.sqlite")
        ep = EpisodeResult(
            case_id=case["id"],
            family=case["family"],
            attack=case["attack"],
            prompt_arm="instruction_boundary",
        )
        try:
            for turn in range(4):
                state = store.state
                admitted = store.admitted()
                messages = [
                    {"role": "system", "content": SYSTEM_BOUNDARY},
                    {
                        "role": "user",
                        "content": (
                            f"State: {state}. Admitted next action: {admitted}.\n"
                            f"User message: {case['user']}"
                        ),
                    },
                ]
                text, prov = _complete(client, HF_MODEL, messages)
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
        except Exception as e:  # noqa: BLE001 - record provider failures explicitly
            errors.append({"case_id": case["id"], "error": str(e)})
            store.close()
            continue
        store.close()
        ep.finalize()
        (ep_dir / "episode.json").write_text(json.dumps(ep.to_json(), indent=2) + "\n")
        episodes.append(ep)

    gap = mirage_gap(episodes) if episodes else {}
    summary = {
        "format": "pcs-assurance-mirage-hf-secondary-v1",
        "model": HF_MODEL,
        "protocol_sha256": protocol.get("protocol_sha256"),
        "n_episodes": len(episodes),
        "errors": errors,
        "episodes": [e.to_json() for e in episodes],
        "mirage_gap": gap,
        "weight_attestation": False,
        "production_authority": False,
        "system_prompt_sha256": sha256(SYSTEM_BOUNDARY.encode()).hexdigest(),
        "plain_unused_sha256": sha256(SYSTEM_PLAIN.encode()).hexdigest(),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary
