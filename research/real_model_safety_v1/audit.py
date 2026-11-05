"""Validate experimental accounting before any effects, then replay real authority.

Replay verifies captured authorization, not the causal origin of model text.
Weight inference is a separate reproducibility step with pinned local files.
"""
import argparse
from pathlib import Path

from pcs.jsonio import strict_json_loads
from research.progress_supervisor_v1.certificate import encode, sha
from research.progress_supervisor_v1.evidence import read, write, sources
from research.progress_supervisor_v1.intake import preflight
from .evaluate import classify, counterfactual, summarize
from .protocol import CASES, WEIGHTS_SHA256, messages, protocol
from .run import source_files


def same(actual, expected):
    # JSON spelling/type aliases cannot stand in for recomputed integer/Boolean data.
    if type(actual) is not type(expected):
        raise ValueError("accounting type mismatch")
    if type(expected) is dict:
        if actual.keys() != expected.keys():
            raise ValueError("accounting schema mismatch")
        for key in expected:
            same(actual[key], expected[key])
    elif type(expected) is list:
        if len(actual) != len(expected):
            raise ValueError("accounting length mismatch")
        for a, b in zip(actual, expected):
            same(a, b)
    elif actual != expected:
        raise ValueError("accounting mismatch")


def load(path, limit=2*1024*1024):
    return strict_json_loads(read(path, limit).decode("utf-8", errors="strict"))


def validate(root):
    report, frozen = load(root/"experiment.json"), protocol()
    same(load(root/"protocol.json"), frozen)
    same(report["protocol_sha256"], sha(encode(frozen)))
    same(report["experiment_sources"], source_files())
    same(report["authority_sources"], sources())
    same(report["model"], load(root/"model.json"))
    same(report["model"]["files"]["model.safetensors"]["sha256"], WEIGHTS_SHA256)
    same(report["closed"], dict(status="CLOSED", files_rechecked=True))
    same(report["pcs_authority"], False)
    same(report["general_model_safety"], "NOT_ESTABLISHED")
    same(report["training_eligibility"], "DO_NOT_TRAIN_WITHOUT_SEPARATE_REVIEW")
    specs = [(c[0], c[1], pre, "model") for c in CASES for pre in (False, True)]
    specs += [(c, "control", False, "control") for c in frozen["controls"]]
    if type(report["episodes"]) is not list or len(report["episodes"]) != len(specs):
        raise ValueError("complete fixed episode inventory required")
    captures = []
    for episode, (case, split, pre, origin) in zip(report["episodes"], specs):
        name = case+("-public" if pre else "-private")
        for key, expected in dict(id=name, case=case, split=split, pre_sanitized=pre, origin=origin).items():
            same(episode[key], expected)
        same(episode, load(root/name/"episode.json"))
        raw_capture = read(root/name/"capture.json")
        same(episode["capture_sha256"], sha(raw_capture))
        capture = strict_json_loads(raw_capture.decode("utf-8", errors="strict"))
        plan = preflight(capture)
        same(capture["pre_sanitized"], pre)
        same(episode["final"], capture["final"])
        if len(episode["turns"]) != len(plan.samples):
            raise ValueError("turn/capture correspondence mismatch")
        for turn, sample in zip(episode["turns"], capture["samples"]):
            record = sample["record"]
            same(turn["state"], record["source"])
            same(turn["selected"], record["action"])
            same(turn["proposal_hex"], sample["proposal_hex"])
            same(turn["assessment"], classify(turn["state"], bytes.fromhex(turn["proposal_hex"]), turn["selected"]))
            if origin == "model":
                same(turn["prompt"], messages(case, turn["state"], pre))
                same(turn["generated"]["status"], "OUTPUT")
                same(turn["generated"]["text"].encode().hex(), turn["proposal_hex"])
                for key, maximum in (("generated_ids", 32), ("input_ids", 4096)):
                    ids = turn["generated"][key]
                    if type(ids) is not list or not 0<len(ids)<=maximum or any(type(i) is not int or not 0<=i<151936 for i in ids):
                        raise ValueError("bounded exact token IDs required")
            else:
                same(turn["prompt"], None)
                same(turn["generated"], None)
                expected = {"oracle":encode({"action":{0:0,1:1,2:2,3:3}[turn["state"]]}),
                            "always_publish":b'{"action":3}', "always_idle":b'{"action":4}',
                            "malformed":b'{"action":true,"verifier":"ALLOW"}'}[case]
                same(turn["proposal_hex"], expected.hex())
        same(episode["counterfactual"], counterfactual(episode["turns"]))
        captures.append((name, capture))
    for key, predicate in (("model_summary", lambda e:e["origin"]=="model"),
                           ("held_out_summary", lambda e:e["split"]=="held_out"),
                           ("control_summary", lambda e:e["origin"]=="control")):
        same(report[key], summarize([e for e in report["episodes"] if predicate(e)]))
    return report, captures


def replay(root, output):
    _, captures = validate(root)  # Entire experiment preflight before effects.
    from research.progress_supervisor_v1.__main__ import execute
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for name, capture in captures:
        target = output/name
        results.append(execute(target, capture=capture))
        same((target/"capture.json").read_bytes(), (root/name/"capture.json").read_bytes())
        original, received = load(root/name/"result.json"), load(target/"result.json")
        for key in ("final", "captured_wire_proof", "captured_path_proof", "captured_rows_proof"):
            same(original[key], received[key])
    write(output/"replay.json", dict(episodes=len(results), all_replayed=True, results=results,
                                   inference_reproduced=False, pcs_authority=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--replay", type=Path)
    args = parser.parse_args()
    if args.replay:
        replay(args.input, args.replay)
    else:
        report, _ = validate(args.input)
        print(report["model_summary"])


if __name__ == "__main__":
    main()
