"""Validate the v3 fixtures and live decisions against schemas/semantic_authority_v3.schema.json.
(The Lean decoders remain the authority; the schema is interface documentation.)"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import unittest

import jsonschema

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FIX = os.path.join(ROOT, "fixtures", "semantic_authority_v3")
BIN = os.path.join(ROOT, ".lake", "build", "bin", "pcs-semantic-check")
SCHEMA = json.load(open(os.path.join(ROOT, "schemas", "semantic_authority_v3.schema.json")))


# adversarial fixtures that are deliberately outside the wire schema (the Lean authority must and
# does reject them independently)
OFF_SCHEMA = {"neg_unknown_version.json"}


def sub(name):
    return {"$schema": SCHEMA["$schema"], "$defs": SCHEMA["$defs"], "$ref": f"#/$defs/{name}"}


class TestSchemaV3(unittest.TestCase):

    def test_authorities(self):
        for p in glob.glob(os.path.join(FIX, "authority*.json")):
            with self.subTest(os.path.basename(p)):
                jsonschema.validate(json.load(open(p)), sub("authorityV3"))

    def test_requests_states_and_decisions(self):
        reqs = sorted(glob.glob(os.path.join(FIX, "requests", "*.json")))
        self.assertGreaterEqual(len(reqs), 37)
        for p in reqs:
            name = os.path.basename(p)
            with self.subTest(name):
                if name in OFF_SCHEMA:
                    with self.assertRaises(jsonschema.ValidationError):
                        jsonschema.validate(json.load(open(p)), sub("requestV3"))
                else:
                    jsonschema.validate(json.load(open(p)), sub("requestV3"))
                st = os.path.join(FIX, "states", name)
                jsonschema.validate(json.load(open(st)), sub("ledgerState"))
                out = subprocess.run([BIN, "--v3", os.path.join(FIX, "authority.json"), p, st],
                                     capture_output=True, text=True).stdout
                jsonschema.validate(json.loads(out), sub("decisionV3"))
                out = subprocess.run([BIN, "--v3-strengthen", os.path.join(FIX, "authority.json"), p, st],
                                     capture_output=True, text=True).stdout
                jsonschema.validate(json.loads(out), sub("strengtheningDecisionV3"))


if __name__ == "__main__":
    unittest.main()
