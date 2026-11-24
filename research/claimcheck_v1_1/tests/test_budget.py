"""The pre-request spending guard and the call harness (prospective/budget.py), with a SYNTHETIC
transport only: nothing is sent anywhere, and the dummy credential exists only inside the test."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from research.claimcheck_v1 import propose
from research.claimcheck_v1_1.prospective import budget as B

DAY = 86400.0
T0 = 1_800_000_000.0                       # a fixed synthetic clock


class Clock:
    def __init__(self, t=T0):
        self.t = t

    def __call__(self):
        return self.t


class Synthetic:
    """Answers like each provider would, counts requests, can be told to fail."""

    def __init__(self, statuses=None, prompt_tokens=1000, output_tokens=200):
        self.requests, self.statuses = [], list(statuses or [])
        self.prompt_tokens, self.output_tokens = prompt_tokens, output_tokens

    def __call__(self, url, headers, payload, timeout):
        self.requests.append((url, payload))
        status = self.statuses.pop(0) if self.statuses else 200
        if status != 200:
            return status, None
        body = json.dumps({"claims": []})
        if "openrouter" in url:
            return 200, {"choices": [{"message": {"content": body}, "finish_reason": "stop"}], "model": payload["model"],
                         "provider": "synthetic", "usage": {"prompt_tokens": self.prompt_tokens, "completion_tokens": self.output_tokens}}
        return 200, {"candidates": [{"content": {"parts": [{"text": body}]}, "finishReason": "STOP"}], "modelVersion": "synthetic",
                     "usageMetadata": {"promptTokenCount": self.prompt_tokens, "candidatesTokenCount": self.output_tokens, "thoughtsTokenCount": 0}}


def config(gemini_price=(1.0, 4.0), caps=None, daily=None):
    cfg = B.load_config()
    conf = cfg["configurations"]["P"]
    conf["providers"]["gemini"]["usd_per_million_prompt_tokens"], conf["providers"]["gemini"]["usd_per_million_output_tokens"] = gemini_price
    if caps:
        conf["caps_usd"]["60"] = caps
    if daily is not None:
        conf["providers"]["gemini"]["max_requests_per_utc_day"] = daily
    return cfg


def gemini_payload(text="x" * 1000, max_out=16384):
    return ("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent",
            {"contents": [{"role": "user", "parts": [{"text": text}]}], "generationConfig": {"maxOutputTokens": max_out}})


DOC = {"text": "The mean length was 4.2 mm (n = 12).\n", "data": b"length\n4.1\n4.3\n", "manifest": {"columns": {}}}
KEYS = {"GEMINI_API_KEY": "synthetic-not-a-key", "OPENROUTER_API_KEY": "synthetic-not-a-key"}


class Guard(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.log = self.tmp / "spend.jsonl"

    def guard(self, cfg=None, inner=None, clock=None, **kw):
        return B.BudgetGuard("P", 60, self.log, owner_authorisation="synthetic test", config=cfg or config(),
                             inner=inner or Synthetic(), clock=clock or Clock(), **kw)

    def test_no_request_without_a_recorded_owner_authorisation(self):
        with self.assertRaises(B.SpendingRefused):
            B.BudgetGuard("P", 60, self.log, owner_authorisation=" ", config=config(), inner=Synthetic())

    def test_a_request_that_could_exceed_the_cap_is_refused_before_it_is_sent(self):
        inner = Synthetic()
        g = self.guard(cfg=config(caps={"total": 15, "gemini": 0.05, "openrouter": 5}), inner=inner)
        url, payload = gemini_payload()                     # worst case (1000 B + structure) x 1 + 16384 x 4 per million, about 0.0666 USD
        with self.assertRaises(B.SpendingRefused):
            g.transport(url, {}, payload, 30)
        self.assertEqual(inner.requests, [])
        self.assertEqual(B.read_log(self.log)[-1]["event"], "refused")

    def test_charges_follow_reported_usage_and_survive_a_restart(self):
        g = self.guard()
        url, payload = gemini_payload()
        self.assertEqual(g.transport(url, {}, payload, 30)[0], 200)
        self.assertAlmostEqual(g.spent["gemini"], (1000 * 1.0 + 200 * 4.0) / 1e6)
        again = self.guard()
        self.assertAlmostEqual(again.spent["gemini"], g.spent["gemini"])

    def test_a_request_sent_without_a_result_is_charged_its_worst_case(self):
        self.guard()
        with open(self.log, "a", encoding="utf-8") as fh:            # a crash between sending and the answer
            fh.write(json.dumps({"event": "sent", "seq": 99, "time": "2027-01-15T08:00:00+00:00", "session": "1", "call": None,
                                 "provider": "gemini", "model": "gemini-3.6-flash", "worst_usd": 0.5}) + "\n")
        self.assertAlmostEqual(self.guard().spent["gemini"], 0.5)

    def test_unpriced_provider_and_unfrozen_model_are_refused(self):
        inner = Synthetic()
        g = self.guard(cfg=config(gemini_price=(None, None)), inner=inner)
        url, payload = gemini_payload()
        with self.assertRaises(B.SpendingRefused):
            g.transport(url, {}, payload, 30)
        g = self.guard(inner=inner)
        with self.assertRaises(B.SpendingRefused):
            g.transport(url.replace("gemini-3.6-flash", "gemini-3.8-flash"), {}, payload, 30)
        self.assertEqual(inner.requests, [])

    def test_unbounded_output_is_refused(self):
        g = self.guard()
        url, payload = gemini_payload()
        del payload["generationConfig"]
        with self.assertRaises(B.SpendingRefused):
            g.transport(url, {}, payload, 30)

    def test_cached_answers_without_a_spend_log_refuse_to_start(self):
        cache = self.tmp / "cache"
        cache.mkdir()
        (cache / "gemini-0123.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(B.SpendingRefused):
            self.guard(cache_dir=cache)

    def test_daily_request_limit(self):
        clock = Clock()
        g = self.guard(cfg=config(daily=2), clock=clock)
        url, payload = gemini_payload()
        g.transport(url, {}, payload, 30)
        g.transport(url, {}, payload, 30)
        self.assertFalse(g.can_start("gemini"))
        with self.assertRaises(B.SpendingRefused):
            g.transport(url, {}, payload, 30)
        clock.t += DAY
        self.assertTrue(g.can_start("gemini"))

    def test_failed_attempts_without_usage_are_charged_conservatively(self):
        inner = Synthetic(statuses=[0, 503, 429, 408])
        g = self.guard(inner=inner)
        url, payload = gemini_payload()
        worst = (B._prompt_bytes(payload) * 1.0 + 16384 * 4.0) / 1e6
        for _ in range(4):
            g.transport(url, {}, payload, 30)
        self.assertAlmostEqual(g.spent["gemini"], 3 * worst)        # transport failure, 5xx and timeout: worst case; 429: nothing

    def test_the_prompt_bound_counts_every_byte_of_the_request_body(self):
        url, payload = gemini_payload()
        self.assertGreater(B._prompt_bytes(payload), 1000)          # the text and the structure around it
        payload["tools"] = [{"note": "y" * 5000}]                   # input the provider could bill that is not a text part
        worst = (B._prompt_bytes(payload) * 1.0 + 16384 * 4.0) / 1e6
        text_only = (1000 * 1.0 + 16384 * 4.0) / 1e6
        inner = Synthetic()
        g = self.guard(cfg=config(caps={"total": 15, "gemini": (text_only + worst) / 2, "openrouter": 5}), inner=inner)
        with self.assertRaises(B.SpendingRefused):
            g.transport(url, {}, payload, 30)
        self.assertEqual(inner.requests, [])

    def test_a_response_that_costs_more_than_its_worst_case_stops_the_guard(self):
        inner = Synthetic(prompt_tokens=10 ** 6)                    # usage the worst-case model says is impossible
        g = self.guard(inner=inner)
        url, payload = gemini_payload()
        g.transport(url, {}, payload, 30)
        self.assertTrue(B.read_log(self.log)[-1]["exceeded_worst_case"])
        with self.assertRaises(B.SpendingRefused):
            g.transport(url, {}, payload, 30)
        self.assertEqual(len(inner.requests), 1)                    # nothing further was sent
        with self.assertRaises(B.SpendingRefused):                  # and a resumed guard refuses to start
            self.guard(inner=inner)


class Harness(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def run_fetch(self, inner, clock, session="1", docs=None):
        g = B.BudgetGuard("P", 60, self.tmp / "spend.jsonl", owner_authorisation="synthetic test", config=config(),
                          inner=inner, clock=clock, cache_dir=self.tmp / "cache", session=session)
        docs = docs or [dict(DOC, key="p1/original"), dict(DOC, key="p1/planted", text=DOC["text"].replace("4.2", "4.5"))]
        with mock.patch.dict(os.environ, KEYS):
            return B.fetch_proposals(docs, g, cache_dir=self.tmp / "cache"), g

    def test_one_call_per_model_per_document_and_no_critic_call(self):
        inner = Synthetic()
        res, _g = self.run_fetch(inner, Clock())
        self.assertEqual(len(inner.requests), 4)                      # 2 documents x 2 models
        prompts = [json.dumps(p) for _u, p in inner.requests]
        self.assertTrue(all(propose.PROMPT_VERSION in s and propose.CRITIC_VERSION not in s for s in prompts))
        self.assertEqual(res["ledger"]["max_calls"], {"gemini": 8, "openrouter": 8})       # four attempts per call
        self.assertEqual(B.primary_complete(res["calls"], {"p1": ("p1/original", "p1/planted")}), {"p1": True})
        self.assertIs(propose.complete, B._providers.complete)        # the substitution is undone

    def test_a_cached_answer_is_never_requested_again(self):
        inner = Synthetic()
        clock = Clock()
        self.run_fetch(inner, clock)
        clock.t += 2 * DAY
        self.run_fetch(inner, clock, session="2")
        self.assertEqual(len(inner.requests), 4)

    def test_reissue_only_retryable_failures_at_least_a_day_later_and_in_at_most_three_sessions(self):
        # gemini fails four times with 429 for the original; everything else answers
        inner = Synthetic(statuses=[429, 429, 429, 429])
        clock = Clock()
        with mock.patch("time.sleep"):
            res, _g = self.run_fetch(inner, clock)
            self.assertEqual(res["calls"][("p1/original", "gemini")]["status"], "failed")
            n = len(inner.requests)
            res, _g = self.run_fetch(inner, clock, session="2")        # too soon: not re-sent
            self.assertEqual(res["calls"][("p1/original", "gemini")]["status"], "wait")
            self.assertEqual(len(inner.requests), n)
            clock.t += DAY
            res, _g = self.run_fetch(inner, clock, session="3")
            self.assertEqual(res["calls"][("p1/original", "gemini")]["status"], "answered")
            self.assertEqual(len(inner.requests), n + 1)

    def test_a_deterministic_failure_is_final(self):
        inner = Synthetic(statuses=[400])
        clock = Clock()
        res, _g = self.run_fetch(inner, clock)
        clock.t += 2 * DAY
        res, _g = self.run_fetch(inner, clock, session="2")
        self.assertEqual(res["calls"][("p1/original", "gemini")]["status"], "final")
        self.assertEqual(B.primary_complete(res["calls"], {"p1": ("p1/original", "p1/planted")}), {"p1": False})


if __name__ == "__main__":
    unittest.main()
