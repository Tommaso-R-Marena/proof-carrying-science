"""Modality-routed composed safety stack.

Route by input type so the stack inherits specialist precision:

* text Goals → Gemini content moderator (primary) ∪ ProtectAI (injection syntax)
* agent episodes → ensembleProbe ∪ AgentDojo-style tool-filter

Naive OR across specialists inflates FPR and loses Pareto dominance. Routing
makes the composed system uniquely undominated across content + mirage tracks.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .baselines import (
    ProtectAIInjection,
    agentdojo_tool_filter,
    build_baselines,
    gemini_moderate,
    openai_moderation_proxy,
    text_of_episode,
)


@dataclass(frozen=True)
class ComposedDecision:
    flag: bool
    reasons: tuple[str, ...]
    scores: dict[str, Any]
    route: str


class ComposedSafetyStack:
    formal_class = "composedStack"

    def __init__(
        self,
        *,
        protectai_dir: Path | None = None,
        use_gemini: bool = True,
        toxic_dir: Path | None = None,
        toxic_threshold: float = 0.35,
    ):
        self.use_gemini = use_gemini
        self.toxic_threshold = toxic_threshold
        self._baselines = build_baselines(protectai_dir)
        self.protectai: ProtectAIInjection = self._baselines["protectai"]
        self._ensemble = self._baselines["episode_detectors"]["ensemble_v1"]
        self._toxic = None
        toxic_dir = Path(toxic_dir) if toxic_dir else Path("/tmp/external-bench/toxic")
        if toxic_dir.exists() and (toxic_dir / "model.safetensors").exists():
            try:
                import torch
                from transformers import AutoModelForSequenceClassification, AutoTokenizer

                self._toxic_tok = AutoTokenizer.from_pretrained(str(toxic_dir))
                self._toxic = AutoModelForSequenceClassification.from_pretrained(
                    str(toxic_dir)
                )
                self._toxic.eval()
                self._torch = torch
            except Exception:
                self._toxic = None

    def _toxic_score(self, text: str) -> float:
        if self._toxic is None:
            return 0.0
        inputs = self._toxic_tok(
            text or "", return_tensors="pt", truncation=True, max_length=256
        )
        with self._torch.no_grad():
            logits = self._toxic(**inputs).logits.sigmoid()[0]
        return float(logits.max())

    def decide_text(
        self,
        text: str,
        *,
        allow_gemini: bool = True,
        gemini_cached: bool | None = None,
    ) -> ComposedDecision:
        reasons: list[str] = []
        scores: dict[str, Any] = {}
        pai = self.protectai.score(text)
        scores["protectai"] = pai

        gem: bool | None = gemini_cached
        if gem is None and self.use_gemini and allow_gemini:
            g = gemini_moderate(text)
            scores["gemini"] = g
            gem = bool(g.get("unsafe")) if g.get("ok") else None
        scores["gemini_cached"] = gem

        if gem is not None:
            # Gemini owns content-harm; inherit its precision.
            if gem:
                reasons.append("gemini_moderator")
            # ProtectAI only adds injection-syntax catches Gemini missed.
            elif pai >= self.protectai.threshold:
                reasons.append("protectai_injection")
        else:
            # Offline fallback when Gemini unavailable.
            if pai >= self.protectai.threshold:
                reasons.append("protectai_injection")
            proxy = openai_moderation_proxy(text)
            scores["openai_mod_proxy"] = proxy
            if proxy["flagged"]:
                reasons.append("openai_mod_proxy")
            tox = self._toxic_score(text)
            scores["toxic_bert_max"] = tox
            if tox >= self.toxic_threshold:
                reasons.append("toxic_bert")

        return ComposedDecision(
            flag=bool(reasons), reasons=tuple(dict.fromkeys(reasons)), scores=scores, route="text"
        )

    def decide_episode(self, ep: dict[str, Any], *, allow_gemini: bool = False) -> ComposedDecision:
        del allow_gemini  # episode route does not call content moderators
        reasons: list[str] = []
        scores: dict[str, Any] = {}
        ens = bool(self._ensemble(ep))
        scores["ensemble_v1"] = ens
        if ens:
            reasons.append("ensemble_v1")
        tool = agentdojo_tool_filter(ep)
        scores["agentdojo_tool_filter"] = tool
        if tool:
            reasons.append("agentdojo_tool_filter")
        scores["episode_text_len"] = len(text_of_episode(ep))
        return ComposedDecision(
            flag=bool(reasons),
            reasons=tuple(dict.fromkeys(reasons)),
            scores=scores,
            route="episode",
        )
