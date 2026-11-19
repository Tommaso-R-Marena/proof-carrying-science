"""Local Kimina-Autoformalizer-7B (GGUF) wrapper — research only.

Default model path: /tmp/sota_models/kimina/Kimina-Autoformalizer-7B.Q3_K_M.gguf
Prompt follows Project Numina Kimina-Autoformalizer quickstart.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

DEFAULT_GGUF = Path(
    os.environ.get(
        "KIMINA_GGUF",
        "/tmp/sota_models/kimina/Kimina-Autoformalizer-7B.Q3_K_M.gguf",
    )
)

_LLM = None


def _get_llm(model_path: Path | None = None):
    global _LLM
    path = Path(model_path or DEFAULT_GGUF)
    if _LLM is not None and getattr(_LLM, "_pcs_path", None) == str(path):
        return _LLM
    from llama_cpp import Llama

    if not path.is_file():
        raise FileNotFoundError(f"Kimina GGUF missing: {path}")
    _LLM = Llama(
        model_path=str(path),
        n_ctx=int(os.environ.get("KIMINA_N_CTX", "4096")),
        n_threads=int(os.environ.get("KIMINA_THREADS", "4")),
        verbose=False,
    )
    _LLM._pcs_path = str(path)  # type: ignore[attr-defined]
    return _LLM


def autoformalize(
    problem: str,
    *,
    theorem_name: str = "my_favorite_theorem",
    temperature: float = 0.2,
    max_tokens: int = 1024,
    model_path: Path | None = None,
) -> dict[str, Any]:
    """Return Lean 4 theorem ending with `by sorry`."""
    prompt = (
        "Please autoformalize the following problem in Lean 4 with a header. "
        f"Use the following theorem names: {theorem_name}.\n\n{problem}"
    )
    messages = [
        {"role": "system", "content": "You are an expert in mathematics and Lean 4."},
        {"role": "user", "content": prompt},
    ]
    llm = _get_llm(model_path)
    out = llm.create_chat_completion(
        messages=messages, temperature=temperature, max_tokens=max_tokens
    )
    text = out["choices"][0]["message"]["content"]
    return {
        "ok": True,
        "text": text,
        "model": "Kimina-Autoformalizer-7B-GGUF",
        "theorem_name": theorem_name,
        "pcs_scientific_authority": False,
    }


__all__ = ["autoformalize", "DEFAULT_GGUF"]
