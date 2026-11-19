"""A withholding stub against the frozen v1 cache reader (claimcheck_v1.providers / propose), unchanged.

The stub must not be served as a cached response: the frozen reader would then read its missing text
and crash every offline tool that reads the cache (analysis, development evaluation).  It must be a
clean cache miss, which the frozen code reports as an error for that arm only.
"""
import json
import tempfile
import unittest
from pathlib import Path

from research.claimcheck_v1.propose import propose_with_model
from research.claimcheck_v1.providers import Ledger, cache_key
from research.claimcheck_v1_1.governance import withhold_model_outputs as W


class Stub(unittest.TestCase):
    def setUp(self):
        self.cache = Path(tempfile.mkdtemp())
        self.text, self.data, self.manifest = "The mean age was 41.2 years.", b"age\n40\n42\n", {"columns": {"age": {}}}

    def record(self, provider, model):
        # write a genuine-looking cached response at the exact path the frozen reader looks up, then stub it
        from research.claimcheck_v1.propose import SYSTEM, candidate_text, data_dictionary, proposer_prompt
        prompt = proposer_prompt(candidate_text(self.text), data_dictionary(self.data, self.manifest))
        key = cache_key(provider, model, prompt, SYSTEM)
        path = self.cache / f"{provider}-{key[:32]}.json"
        path.write_text(json.dumps({"provider": provider, "model": model, "key": key, "text": '{"claims": []}', "usage": {},
                                    "finish": "stop", "prompt_sha256": "0" * 64}), encoding="utf-8")
        return path, key

    def test_the_original_is_served_from_the_cache(self):
        self.record("openrouter", "nvidia/nemotron-3-ultra-550b-a55b:free")
        props, meta = propose_with_model("openrouter", "nvidia/nemotron-3-ultra-550b-a55b:free", self.text, self.data, self.manifest,
                                         allow_network=False, ledger=Ledger(max_calls={"openrouter": 0}), cache_dir=self.cache)
        self.assertTrue(meta["cached"])
        self.assertNotIn("error", meta)

    def test_a_stub_is_a_clean_cache_miss_not_a_crash(self):
        path, key = self.record("openrouter", "nvidia/nemotron-3-ultra-550b-a55b:free")
        original = json.loads(path.read_text())
        rec = {"group": "N", "provider": "openrouter", "model": original["model"], "key": key, "prompt_sha256": original["prompt_sha256"],
               "usage": {}, "finish": "stop", "original_sha256": "1" * 64, "original_bytes": 10, "text_sha256": "2" * 64,
               "text_characters": 14, "request_identifier": "not recorded by the client", "recorded_in_commit": None,
               "recorded_in_repository_utc": None, "provider_terms": "t", "status": "s"}
        s = W.stub(rec, "test")
        self.assertNotIn("key", s)
        self.assertEqual(s["cache_key"], key)                       # the provenance is kept, under another name
        self.assertNotIn("text", s)
        path.write_text(json.dumps(s), encoding="utf-8")
        props, meta = propose_with_model("openrouter", original["model"], self.text, self.data, self.manifest,
                                         allow_network=False, ledger=Ledger(max_calls={"openrouter": 0}), cache_dir=self.cache)
        self.assertEqual(props, [])
        self.assertIn("no cached response", meta["error"])


if __name__ == "__main__":
    unittest.main()
