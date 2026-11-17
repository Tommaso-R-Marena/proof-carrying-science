"""Binding between data bytes, receipts, proof obligations and the independent replay (no Lean).

The kernel is replaced by a stand-in that writes the real obligation file and reports acceptance (as
in claimcheck_v1/tests); a stand-in `lean` for the stand-alone runner imitates an accepting kernel.
Neither checks anything: these tests exercise the binding checks that need no kernel.  check_live_v11
runs its own resealed tampering cases with the real Lean 4.28.0 kernel.

Every forgery is resealed (receipt digests, record digests, both bundle indexes made consistent
again), so what refuses it is a check of meaning, not a stale digest.

Three tests named `test_claim_binding_*` cover a gap found on 2026-11-17
(research/claimcheck_assurance_v1/conformance/CORRESPONDENCE.md on the research branch): the
replayers checked that each obligation is the one derived from the receipt's claim, but not that the
claim is the sentence's -- the claim's reported value against the printed number, and the checked
variants against the claim's statistic (a refuting standard-deviation convention could be dropped).
The kernel cannot catch these: the theorem that remains is true, about another statement.  The v1.1
replayer now refuses all three.  The frozen v1 replayer (FREEZE.json; not changed) still accepts
them on its own; the tests record that as a known limit, so use the v1.1 replayer for v1.1 bundles.
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

from research.claimcheck_v1 import lean as lean_mod
from research.claimcheck_v1 import pipeline
from research.claimcheck_v1 import replay_independent as replay_v1
from research.claimcheck_v1.oracle import evaluate
from research.claimcheck_v1.pipeline import _outcome_json
from research.claimcheck_v1.spec import ClaimSpec, canonical, sha256_hex
from research.claimcheck_v1_1 import claimcheck_kernel_runner as runner
from research.claimcheck_v1_1.tests.test_v11_offline import DATA, MANIFEST
from research.claimcheck_v1_1.verify import verify, write_bundle_v11

HERE = Path(__file__).resolve().parent
REPLAY = HERE.parent / "replay_independent_v1_1.py"
RUNNER = HERE.parent / "claimcheck_kernel_runner.py"
OTHER_DATA = DATA.replace(b"12.31", b"12.51")
SENTENCES = ["Mean body mass was 14.76 g (range 11.95–18.09 g) across the 12 individuals.",
             "In a second report the mean body length was 111.2 mm (range 99.7–121.6 mm).",
             "The standard deviation of body mass was 2.20 g across the 11 individuals.",
             "The median age was 4 in this sample.",
             "Mean body mass was 14.26 g in a pilot."]
TEXT = "\n\n".join(SENTENCES)
SPECS = [{"stat": "mean", "reported": "14.76", "column": "mass"},      # c001 match
         {"stat": "mean", "reported": "111.2", "column": "length"},    # c002 mismatch (the file's mean is 109.5)
         {"stat": "sd", "reported": "2.20", "column": "mass"},         # c003 n - 1 matches, n does not: conditional
         {"stat": "median", "reported": "4", "column": "age"},         # c004 match
         {"stat": "mean", "reported": "14.26", "column": "mass"}]      # c005 mismatch (14.26 is the median)
PROPOSALS = [(f"c{i + 1:03d}", {"quote": s, "spec": spec}, "binding test") for i, (s, spec) in enumerate(zip(SENTENCES, SPECS))]


def accept_all(data, items, *, timeout=900, keep_dir=None, name="batch"):
    """Stand-in for the kernel: writes the real obligation file and reports acceptance (checks nothing)."""
    text = lean_mod.batch_source(data, items)
    out = []
    for i in range(len(items)):
        rec = {"kernel_accepted": True, "axioms": ["propext"], "batch_seconds": 0.0, "batch_size": len(items), "index": i,
               "theorem": f"pcs_claim_{i}", "toolchain": "stand-in, not a kernel", "detail": "stand-in acceptance",
               "obligation_sha256": sha256_hex(text.encode("utf-8")), "checker_sha256": lean_mod.checker_sha256()}
        if keep_dir is not None:
            keep_dir.mkdir(parents=True, exist_ok=True)
            (keep_dir / f"{name}.lean").write_text(text, encoding="utf-8")
            rec["obligation_file"] = f"{name}.lean"
        out.append(rec)
    return out


def make_bundle(out: Path, proposals=PROPOSALS, data: bytes = DATA) -> None:
    manifest = dict(MANIFEST, sha256=sha256_hex(data))
    with mock.patch.object(pipeline, "check_items", side_effect=accept_all):
        result = verify(proposals, source_text=TEXT, source_meta={"name": "binding"}, data=data, manifest=manifest,
                        keep_dir=out / "v1" / "obligations", find_siblings=False)
    write_bundle_v11(out, result, source_text=TEXT, data=data, manifest=manifest, source_name="binding.txt", data_name="binding.csv")


def replay(bundle: Path) -> tuple[int, dict | None]:
    proc = subprocess.run([sys.executable, str(REPLAY), str(bundle), "--checker-sha256", lean_mod.checker_sha256(), "--skip-lean"],
                          capture_output=True, text=True)
    try:
        return proc.returncode, json.loads(proc.stdout)
    except ValueError:
        return proc.returncode, None


def problems(summary: dict | None) -> list[str]:
    if summary is None:
        return ["(no report: the replayer stopped)"]
    v1 = summary.get("v1_replay") or {}
    return summary["bundle_problems"] + list(v1.get("bundle_problems") or []) + [i for r in summary["records"] for i in r["issues"]]


def v1_problems(bundle: Path) -> list[str]:
    """The v1 replayer's own findings (the v1.1 report says only whether the v1 replay succeeded)."""
    try:
        results, _ok = replay_v1.replay(bundle / "v1", lean_mod.checker_sha256(), 60, True)
    except Exception as exc:  # noqa: BLE001 - a malformed bundle may stop the replayer
        return [f"(the v1 replayer stopped: {type(exc).__name__})"]
    return list(results[0]["bundle_problems"]) + [i for r in results[1:] for i in r["issues"]]


# ---- what a careful forger does after an edit -----------------------------------------------------
def reseal_v1(b: Path) -> None:
    index = json.loads((b / "v1" / "bundle.json").read_text(encoding="utf-8"))
    for name in index["files"]:
        if (b / "v1" / name).is_file():
            raw = (b / "v1" / name).read_bytes()
            index["files"][name] = {"sha256": sha256_hex(raw), "bytes": len(raw)}
    (b / "v1" / "bundle.json").write_text(json.dumps(index, indent=1, sort_keys=True), encoding="utf-8")


def reseal(b: Path) -> None:
    index = json.loads((b / "claimcheck_v1_1.json").read_text(encoding="utf-8"))
    for name in index["files"]:
        if (b / name).is_file():
            index["files"][name] = sha256_hex((b / name).read_bytes())
    (b / "claimcheck_v1_1.json").write_text(json.dumps(index, indent=1, sort_keys=True), encoding="utf-8")


def load(b: Path) -> tuple[list, list]:
    return (json.loads((b / "v1" / "receipts.json").read_text(encoding="utf-8")),
            json.loads((b / "records.json").read_text(encoding="utf-8")))


def rederive(b: Path, receipts: list) -> None:
    """Re-render every obligation file from the (edited) receipts, renumbering what is left."""
    data = (b / "v1" / "data.csv").read_bytes()
    manifest = json.loads((b / "v1" / "manifest.json").read_text(encoding="utf-8"))
    checker = (b / "v1" / "ClaimCheck.lean").read_text(encoding="utf-8")
    files: dict = {}
    for rc in receipts:
        for v in (rc.get("q1_mathematics") or {}).get("variants", []):
            if (v.get("lean") or {}).get("kernel_accepted"):
                files.setdefault(v["lean"]["obligation_file"], []).append((v["lean"]["index"], rc, v))
    for name, entries in files.items():
        entries.sort(key=lambda e: e[0])
        text = checker + replay_v1.render_tail(data, [(rc["claim"]["spec"], v["stat"], v["predicted_outcome"]) for _, rc, v in entries], manifest)
        (b / "v1" / "obligations" / name).write_text(text, encoding="utf-8")
        for k, (_, _rc, v) in enumerate(entries):
            v["lean"].update(index=k, batch_size=len(entries), obligation_sha256=sha256_hex(text.encode("utf-8")))


def save(b: Path, receipts: list, records: list) -> None:
    """Recompute receipt digests, carry them into the records, recompute record digests, reseal."""
    moved = {}
    for rc in receipts:
        old = rc.get("receipt_sha256")
        rc["receipt_sha256"] = sha256_hex(canonical({k: v for k, v in rc.items() if k != "receipt_sha256"}))
        moved[old] = rc
    for rec in records:
        rc = moved.get(rec.get("v1_receipt_sha256"))
        if rc is not None:
            rec["v1_receipt_sha256"], rec["v1_result"] = rc["receipt_sha256"], rc.get("result")
            rec["mathematical"]["data_sha256"] = (rc.get("data") or {}).get("sha256")
        for c in rec["source_reading"]["corroborated_by"]:
            if c.get("receipt_sha256") in moved:
                c["receipt_sha256"] = moved[c["receipt_sha256"]]["receipt_sha256"]
        rec["record_sha256"] = sha256_hex(canonical({k: v for k, v in rec.items() if k != "record_sha256"}))
    (b / "v1" / "receipts.json").write_text(json.dumps(receipts, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    (b / "records.json").write_text(json.dumps(records, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    reseal_v1(b)
    reseal(b)


def by_id(items: list, claim_id: str) -> dict:
    return next(x for x in items if x["claim_id"] == claim_id)


def relabel(record: dict, status: str, verdict: str = "REQUIRE_HUMAN_REVIEW") -> None:
    record["mathematical"]["status"], record["outward"]["verdict"] = status, verdict


class Binding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="claimcheck-binding-")
        cls.work = Path(cls._tmp.name)
        make_bundle(cls.work / "good")
        make_bundle(cls.work / "other-data", data=OTHER_DATA)
        make_bundle(cls.work / "other-claims", proposals=PROPOSALS[3:])

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def forged(self, name: str, edit) -> tuple[int, dict | None, list[str]]:
        target = self.work / name
        shutil.copytree(self.work / "good", target)
        edit(target)
        return replay(target) + (v1_problems(target),)

    def assertClaimBindingRefused(self, outcome, expected: str):
        """Refused by the v1.1 replayer; the frozen v1 replayer alone still accepts it (known limit)."""
        code, summary, v1 = outcome
        self.assertNotEqual(code, 0)
        self.assertFalse(summary and summary.get("all_replayed"))
        self.assertTrue(any(expected in p for p in problems(summary)), (expected, problems(summary)))
        self.assertEqual(v1, [], "the frozen v1 replayer is expected to accept this forgery on its own (known limit)")

    def assertRefused(self, outcome, *expected: str):
        code, summary, v1 = outcome
        self.assertNotEqual(code, 0)
        self.assertFalse(summary and summary.get("all_replayed"))
        found = problems(summary) + v1
        for text in expected:
            self.assertTrue(any(text in p for p in found), (text, found))

    # ---- the genuine bundle ---------------------------------------------------------------------
    def test_the_genuine_bundle_replays(self):
        code, summary = replay(self.work / "good")
        self.assertEqual(code, 0, problems(summary))
        self.assertTrue(summary["all_replayed"])
        got = {r["claim_id"]: r["mathematical"] for r in summary["records"]}
        self.assertEqual(got, {"c001": "MATCH_PROVED", "c002": "MISMATCH_PROVED", "c003": "CONDITIONAL_ON_CONVENTION",
                               "c004": "MATCH_PROVED", "c005": "MISMATCH_PROVED"})
        self.assertFalse(summary["proofs_rechecked_by_the_lean_kernel"])  # offline: integrity and recomputation only

    # ---- (a) receipts for one file presented with another ----------------------------------------
    def test_receipts_about_other_data_presented_with_this_data_file_are_refused(self):
        def edit(b):
            shutil.rmtree(b)
            shutil.copytree(self.work / "other-data", b)
            (b / "v1" / "data.csv").write_bytes(DATA)  # the bundle about OTHER_DATA, handed over with this file
            reseal_v1(b)
            reseal(b)
        self.assertRefused(self.forged("a-other-data", edit), "receipt names different data bytes",
                           "bundled obligation differs from the one derived from the receipts")

    # ---- (b) receipts edited after the run --------------------------------------------------------
    def test_a_receipt_whose_data_digest_was_edited_is_refused(self):
        def edit(b):
            receipts, records = load(b)
            for rc in receipts:
                rc["data"]["sha256"] = sha256_hex(OTHER_DATA)
            (b / "v1" / "data.csv").write_bytes(OTHER_DATA)  # data digest and data file agree again; the obligations do not
            save(b, receipts, records)
        self.assertRefused(self.forged("b-data-digest", edit), "bundled obligation differs from the one derived from the receipts")

    def test_substituted_data_with_rederived_obligations_is_refused_by_the_second_calculation(self):
        """Offline only the second calculation refuses this.  With Lean 4.28.0 the kernel also rejects the
        re-derived obligations, which are false for the substituted file (run by hand, 2026-11-17)."""
        def edit(b):
            receipts, records = load(b)
            for rc in receipts:
                rc["data"]["sha256"] = sha256_hex(OTHER_DATA)
            (b / "v1" / "data.csv").write_bytes(OTHER_DATA)
            rederive(b, receipts)
            save(b, receipts, records)
        self.assertRefused(self.forged("b-data-rederived", edit), "second calculation disagrees with the kernel-checked value")

    def test_an_edited_outcome_with_a_rederived_obligation_is_refused_by_the_second_calculation(self):
        """Offline only the second calculation refuses this.  With Lean 4.28.0 the kernel also rejects the
        re-derived obligation (run by hand, 2026-11-17).  check_live_v11's kernel_outcome_forged does not
        re-derive the obligation, so there the comparison with the re-derived file refuses it before Lean."""
        def edit(b):
            receipts, records = load(b)
            rc = by_id(receipts, "c002")
            for v in rc["q1_mathematics"]["variants"]:
                v["predicted_outcome"]["verdict"], v["status"] = "consistent", "PROVED"
            rc["q1_mathematics"]["status"] = rc["result"] = "PROVED"
            rederive(b, receipts)
            relabel(by_id(records, "c002"), "MATCH_PROVED")
            save(b, receipts, records)
        self.assertRefused(self.forged("b-outcome", edit), "second calculation reaches a different verdict")

    def test_a_decided_result_must_have_the_polarity_of_the_kernels_status(self):
        """The input condition of conformance part E, enforced at replay: result REFUTED over a proved match."""
        def edit(b):
            receipts, records = load(b)
            by_id(receipts, "c001")["result"] = "REFUTED"
            save(b, receipts, records)
        self.assertRefused(self.forged("b-polarity", edit), "result REFUTED is not what Q1 and Q2 support (PROVED)")

    # ---- (c) two genuine files about the same data ------------------------------------------------
    def test_records_of_another_bundle_about_the_same_data_are_refused(self):
        def edit(b):
            shutil.copy(self.work / "other-claims" / "records.json", b / "records.json")
            reseal(b)
        self.assertRefused(self.forged("c-other-claims", edit), "the record points to a v1 receipt that is not in the bundle",
                           "the number of v1.1 records differs from the number of v1 receipts")

    def test_runner_receipts_for_two_genuine_files_about_the_same_data_differ_in_the_proof_file_digest(self):
        """Same data, different claims (printed 14.26 and 14.3, both the median 14.26), identical outcomes.

        A kernel-run receipt does not restate the claims: it is bound to them only through
        proof_file_sha256, the digest of the exact bytes run, so a consumer must compare that digest
        with the file it generated.  The stand-in `lean` imitates an accepting kernel and checks nothing.
        """
        items = [[(ClaimSpec("median", rep, column="mass"), ("", "NA"), Fraction(1),
                   evaluate(DATA, ClaimSpec("median", rep, column="mass"), ("", "NA"), Fraction(1)))] for rep in ("14.26", "14.3")]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            lean = tmp / "lean"
            lean.write_text(f"#!{sys.executable}\nimport sys\n"
                            "if sys.argv[1:] == ['--version']:\n    print('Lean (version 4.28.0, stand-in, not a kernel)'); sys.exit(0)\n"
                            "text = open(sys.argv[1], encoding='utf-8').read()\n"
                            "for i in range(text.count('#print axioms pcs_claim_')):\n    print(f\"'pcs_claim_{i}' depends on axioms: [propext]\")\n")
            lean.chmod(0o755)
            receipts, files = [], []
            for k, its in enumerate(items):
                path = tmp / f"proof-{k}.lean"
                path.write_text(lean_mod.batch_source(DATA, its), encoding="utf-8")
                files.append(path.read_bytes())
                proc = subprocess.run([sys.executable, str(RUNNER), str(path), "--lean", str(lean)], capture_output=True, text=True)
                receipts.append(json.loads(proc.stdout))
        a, b = receipts
        self.assertTrue(a["accepted"] and b["accepted"] and a["generated_part_canonical"] and b["generated_part_canonical"])
        self.assertEqual(a["data_sha256"], sha256_hex(DATA))
        self.assertEqual(a["data_sha256"], b["data_sha256"])
        self.assertEqual([t["proved_outcome"] for t in a["theorems"]], [t["proved_outcome"] for t in b["theorems"]])
        self.assertEqual([a["proof_file_sha256"], b["proof_file_sha256"]], [hashlib.sha256(f).hexdigest() for f in files])
        self.assertNotEqual(a["proof_file_sha256"], b["proof_file_sha256"])
        tails = [f.decode("utf-8").split(runner.MARKER)[1] for f in files]
        self.assertNotEqual(tails[0], tails[1])                                      # the files differ: in the claims
        self.assertEqual(runner.parse_tail(tails[0]), runner.parse_tail(tails[1]))  # what the runner extracts does not

    # ---- (d) a proof file about other data --------------------------------------------------------
    def test_an_obligation_embedding_other_data_is_refused(self):
        def edit(b):
            receipts, records = load(b)
            name = sorted((b / "v1" / "obligations").glob("*.lean"))[0]
            text = name.read_text(encoding="utf-8")
            text = text.replace(f"⟨0x{DATA.hex()}, {len(DATA)}⟩", f"⟨0x{OTHER_DATA.hex()}, {len(OTHER_DATA)}⟩")
            data, _ = runner.parse_tail(text.split(runner.MARKER)[1])  # still a canonical proof file, about OTHER_DATA
            self.assertEqual(data, OTHER_DATA)
            name.write_text(text, encoding="utf-8")
            for rc in receipts:
                for v in rc["q1_mathematics"]["variants"]:
                    if v["lean"].get("obligation_file") == name.name:
                        v["lean"]["obligation_sha256"] = sha256_hex(text.encode("utf-8"))
            save(b, receipts, records)
        self.assertRefused(self.forged("d-embedded-data", edit), "bundled obligation differs from the one derived from the receipts",
                           "obligation digest in a receipt differs from the re-derived obligation")

    # ---- (e) malformed input fails closed ---------------------------------------------------------
    def test_malformed_bundles_fail_closed(self):
        """The replayer may stop with an error or list problems, but never reports a replay."""
        def receipts_edit(fn):
            def edit(b):
                receipts, records = load(b)
                fn(receipts)
                save(b, receipts, records)
            return edit

        def records_edit(fn):
            def edit(b):
                receipts, records = load(b)
                fn(records)
                (b / "records.json").write_text(json.dumps(records), encoding="utf-8")
                reseal(b)
            return edit

        def write(rel, content, v1_index=True, index=True):
            def edit(b):
                path = b / rel
                if content is None:
                    path.unlink()
                else:
                    path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
                if v1_index:
                    reseal_v1(b)
                if index:
                    reseal(b)
            return edit

        def first_variant(receipts):
            return next(rc for rc in receipts if (rc.get("q1_mathematics") or {}).get("variants"))["q1_mathematics"]["variants"][0]

        receipts_text = (self.work / "good" / "v1" / "receipts.json").read_text(encoding="utf-8")
        cases = {
            "receipts_not_a_list": write("v1/receipts.json", "{}"),
            "receipts_empty": write("v1/receipts.json", "[]"),
            "receipts_truncated": write("v1/receipts.json", receipts_text[:len(receipts_text) // 2]),
            "receipts_not_utf8": write("v1/receipts.json", b"\xff\xfe[]"),
            "receipt_without_data": receipts_edit(lambda rs: rs[0].pop("data")),
            "receipt_without_claim": receipts_edit(lambda rs: rs[0].pop("claim")),
            "receipt_q1_is_text": receipts_edit(lambda rs: rs[0].__setitem__("q1_mathematics", "PROVED")),
            "receipt_result_null": receipts_edit(lambda rs: rs[0].__setitem__("result", None)),
            "variant_lean_null": receipts_edit(lambda rs: first_variant(rs).__setitem__("lean", None)),
            "variant_without_exact_value": receipts_edit(lambda rs: first_variant(rs)["predicted_outcome"].pop("exact")),
            "variant_index_out_of_range": receipts_edit(lambda rs: first_variant(rs)["lean"].__setitem__("index", 99)),
            "receipt_digest_removed": write("v1/receipts.json", json.dumps([{k: v for k, v in r.items() if k != "receipt_sha256"}
                                                                           for r in json.loads(receipts_text)])),
            "records_not_a_list": write("records.json", "{}", v1_index=False),
            "records_empty": write("records.json", "[]", v1_index=False),
            "record_without_outward": records_edit(lambda rs: rs[0].pop("outward")),
            "record_with_an_unknown_verdict": records_edit(lambda rs: rs[0]["outward"].__setitem__("verdict", "PROVED")),
            "record_mathematical_null": records_edit(lambda rs: rs[0].__setitem__("mathematical", None)),
            "record_findings_null": records_edit(lambda rs: rs[0]["source_reading"].__setitem__("findings", None)),
            "record_corroborator_null": records_edit(lambda rs: rs[0]["source_reading"].__setitem__("corroborated_by", [{"receipt_sha256": None}])),
            "record_duplicated": records_edit(lambda rs: rs.append(copy.deepcopy(rs[0]))),
            "index_truncated": write("claimcheck_v1_1.json", "{\"files\": {", v1_index=False, index=False),
            "index_names_another_checker": lambda b: (b / "claimcheck_v1_1.json").write_text(json.dumps(
                dict(json.loads((b / "claimcheck_v1_1.json").read_text()), checker_sha256="0" * 64))),
            "v1_index_truncated": write("v1/bundle.json", "{\"files\"", v1_index=False),
            "v1_index_omits_the_receipts": lambda b: ((b / "v1" / "bundle.json").write_text(json.dumps(
                {**json.loads((b / "v1" / "bundle.json").read_text()), "files": {k: v for k, v in json.loads(
                    (b / "v1" / "bundle.json").read_text())["files"].items() if k != "receipts.json"}})), reseal(b)),
            "v1_unlisted_file": lambda b: ((b / "v1" / "extra.txt").write_text("x"), reseal(b)),
            "manifest_not_json": write("v1/manifest.json", "{"),
            "manifest_a_list": write("v1/manifest.json", "[]"),
            "source_not_utf8": write("v1/source.txt", b"\xff\xfe\x00"),
            "data_missing": write("v1/data.csv", None),
            "obligation_missing": lambda b: (sorted((b / "v1" / "obligations").glob("*.lean"))[0].unlink(), reseal_v1(b), reseal(b)),
            "obligation_not_utf8": lambda b: (sorted((b / "v1" / "obligations").glob("*.lean"))[0].write_bytes(b"\xff\xfe"), reseal_v1(b), reseal(b)),
        }
        for name, edit in cases.items():
            with self.subTest(name):
                code, summary, _v1 = self.forged("e-" + name, edit)
                self.assertNotEqual(code, 0, name)
                self.assertFalse(summary and summary.get("all_replayed"), name)

    # ---- (f) a conditional result presented as a match --------------------------------------------
    def test_a_conditional_record_relabelled_as_a_match_is_refused(self):
        def edit(b):
            receipts, records = load(b)
            relabel(by_id(records, "c003"), "MATCH_PROVED")
            save(b, receipts, records)
        self.assertRefused(self.forged("f-record", edit), "is not what the kernel-checked theorems support (CONDITIONAL_ON_CONVENTION)")

    def test_a_conditional_receipt_relabelled_as_proved_is_refused(self):
        def edit(b):
            receipts, records = load(b)
            rc = by_id(receipts, "c003")
            rc["q1_mathematics"].pop("conditional")
            rc["q1_mathematics"]["status"] = rc["result"] = "PROVED"
            relabel(by_id(records, "c003"), "MATCH_PROVED")
            save(b, receipts, records)
        self.assertRefused(self.forged("f-receipt", edit), "Q1 status PROVED is not what the variants support (UNKNOWN)")

    def test_claim_binding_a_dropped_convention_is_refused(self):
        """Was a gap (refused by the v1.1 replayer since 2026-11-17): CONDITIONAL_ON_CONVENTION becomes MATCH_PROVED when the n variant is removed.

        The replayers recompute the status from the variants present; they do not check that the
        variants are the ones the reading requires (both conventions unless the manifest declares
        one).  The remaining theorem (n - 1) is true, so the kernel re-check passes too.  With findings
        fabricated (they are taken as recorded) the verdict becomes CONFIRMATION.
        """
        def edit(b):
            receipts, records = load(b)
            rc = by_id(receipts, "c003")
            rc["q1_mathematics"]["variants"] = [v for v in rc["q1_mathematics"]["variants"] if v["status"] == "PROVED"]
            rc["q1_mathematics"].pop("conditional")
            rc["q1_mathematics"]["status"] = rc["result"] = "PROVED"
            rc["reason"] = "checked"
            rederive(b, receipts)
            relabel(by_id(records, "c003"), "MATCH_PROVED")
            save(b, receipts, records)
        outcome = self.forged("f-dropped-convention", edit)
        receipt = by_id(load(self.work / "f-dropped-convention")[0], "c003")
        self.assertEqual([v["stat"] for v in receipt["q1_mathematics"]["variants"]], ["sd_sample"])  # the forgery is in place
        self.assertClaimBindingRefused(outcome, "the checked variants are not the ones the claim's statistic requires")

    def test_claim_binding_another_statistic_is_refused(self):
        """Was a gap (refused by the v1.1 replayer since 2026-11-17): a mean that does not match becomes MATCH_PROVED when the variant checks the median.

        The obligation is rendered from the claim and the variant's own `stat` field, which is not
        compared with the claim's statistic; the receipt still reads "The arithmetic mean of mass".
        """
        def edit(b):
            receipts, records = load(b)
            manifest = json.loads((b / "v1" / "manifest.json").read_text(encoding="utf-8"))
            rc = by_id(receipts, "c005")
            v = rc["q1_mathematics"]["variants"][0]
            scale = replay_v1.scale_for(rc["claim"]["spec"], "median", manifest)
            v["stat"], v["status"] = "median", "PROVED"
            v["predicted_outcome"] = _outcome_json(evaluate(DATA, ClaimSpec("median", "14.26", column="mass"), ("", "NA"), scale), scale)
            rc["q1_mathematics"]["status"] = rc["result"] = "PROVED"
            rederive(b, receipts)
            relabel(by_id(records, "c005"), "MATCH_PROVED")
            save(b, receipts, records)
        outcome = self.forged("f-other-statistic", edit)
        receipt = by_id(load(self.work / "f-other-statistic")[0], "c005")
        self.assertEqual((receipt["claim"]["spec"]["stat"], receipt["q1_mathematics"]["variants"][0]["stat"]), ("mean", "median"))
        self.assertIn("arithmetic mean", receipt["claim"]["reading"])
        self.assertClaimBindingRefused(outcome, "the checked variants are not the ones the claim's statistic requires")

    def test_claim_binding_another_reported_value_is_refused(self):
        """Was a gap (refused by the v1.1 replayer since 2026-11-17): the claim's reported value is not compared with the printed number.

        The sentence prints 111.2 (q2 still records 111.2 at its offsets); the claim is edited to
        109.5, the file's mean, and the re-derived theorem is true.
        """
        def edit(b):
            receipts, records = load(b)
            manifest = json.loads((b / "v1" / "manifest.json").read_text(encoding="utf-8"))
            rc = by_id(receipts, "c002")
            rc["claim"]["spec"]["reported"] = "109.5"
            v = rc["q1_mathematics"]["variants"][0]
            scale = replay_v1.scale_for(rc["claim"]["spec"], "mean", manifest)
            v["predicted_outcome"] = _outcome_json(evaluate(DATA, ClaimSpec("mean", "109.5", column="length"), ("", "NA"), scale), scale)
            v["status"] = "PROVED"
            rc["q1_mathematics"]["status"] = rc["result"] = "PROVED"
            rederive(b, receipts)
            rec = by_id(records, "c002")
            relabel(rec, "MATCH_PROVED")
            rec["source_reading"]["findings"] = []
            save(b, receipts, records)
        outcome = self.forged("f-reported-value", edit)
        receipt = by_id(load(self.work / "f-reported-value")[0], "c002")
        self.assertEqual((receipt["claim"]["spec"]["reported"], receipt["q2_correspondence"]["reported_value"]["literal_checked"]), ("109.5", "111.2"))
        self.assertClaimBindingRefused(outcome, "the claim's reported value is not the number printed in the sentence")


if __name__ == "__main__":
    unittest.main()
