"""Development code that hands oracle-predicted receipts to the policy must say so explicitly.

Since the outward-verdict guard (`policy.established_status`, 2026-11-17), a receipt whose variants
the kernel did not accept decides nothing unless the caller passes `oracle_receipts=True`, a switch
for development analysis only.  Forgetting the switch fails silently: the oracle-scored documents
become UNKNOWN and committed development results stop reproducing.  That happened to
`dev/evaluate.py` (its five oracle-scored development documents; fixed 2026-11-18).

This test reads the source.  In every function that calls `oracle_receipts` or
`oracle_receipts_raw`, every call of `assess_document` must pass `oracle_receipts=True` literally
(not through `**kwargs`).  The verification pipeline and the site export build no oracle receipts
and must pass neither development switch.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTORIES = {"oracle_receipts", "oracle_receipts_raw"}
PIPELINE = ("verify.py", "export_site_v11.py")


def _name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _calls(node: ast.AST) -> list[ast.Call]:
    return [n for n in ast.walk(node) if isinstance(n, ast.Call)]


def _opted_in(call: ast.Call) -> bool:
    return any(k.arg == "oracle_receipts" and isinstance(k.value, ast.Constant) and k.value.value is True for k in call.keywords)


class OracleOptIn(unittest.TestCase):
    def test_every_function_that_builds_oracle_receipts_opts_in_explicitly(self):
        checked, missing = set(), set()
        for path in sorted(ROOT.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for fn in ast.walk(tree):
                if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                calls = _calls(fn)
                if not any(_name(c.func) in FACTORIES for c in calls):
                    continue
                for c in calls:
                    if _name(c.func) == "assess_document":
                        where = f"{path.relative_to(ROOT).as_posix()}:{c.lineno}"
                        checked.add(where)
                        if not _opted_in(c):
                            missing.add(where)
        self.assertEqual(sorted(missing), [], "these calls hand oracle receipts to the policy without oracle_receipts=True")
        # tests/test_v11_offline.py (run), dev/evaluate.py (run), dev/adversary.py (two calls)
        self.assertGreaterEqual(len(checked), 4, sorted(checked))

    def test_the_pipeline_and_the_site_export_pass_no_development_switch(self):
        for rel in PIPELINE:
            tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
            calls = [c for c in _calls(tree) if _name(c.func) == "assess_document"]
            self.assertTrue(calls, rel)
            for c in calls:
                names = {k.arg for k in c.keywords}
                self.assertFalse(names & {"oracle_receipts", "oracle_siblings", None}, f"{rel}:{c.lineno}")


if __name__ == "__main__":
    unittest.main()
