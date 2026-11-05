"""Actual inference plus exact raw proposals to an independently built native gate.

This is a research coordinator on a trusted host, not an isolation/root claim.
The model process never receives authority responses, source paths or SQL handles.
"""
import argparse
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

from research.progress_supervisor_v1.broker import Broker
from research.progress_supervisor_v1.certificate import encode, sha
from research.progress_supervisor_v1.evidence import EXTERNAL_ORIGIN, publish, sources, write
from .evaluate import classify, counterfactual, summarize
from .protocol import CASES, messages, protocol

HERE = Path(__file__).resolve().parent


def source_files():
    return {p.name: sha(p.read_bytes()) for p in sorted(HERE.glob("*.py"))}


def read_message(process, timeout=300):
    # Unbuffered stdout and a deadline also bound a silent/crashed model process.
    end, data = time.monotonic()+timeout, bytearray()
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        while True:
            remaining = end-time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                raise TimeoutError("model response deadline")
            byte = os.read(process.stdout.fileno(), 1)
            if not byte:
                raise ValueError("model closed without a complete response")
            if byte == b"\n":
                return json.loads(data)
            data.extend(byte)
            if len(data)>65536:
                raise ValueError("oversized model response")


def live(weights, dependencies, output):
    output.mkdir(parents=True, exist_ok=False)
    frozen = protocol()
    experiment_sources, authority_sources = source_files(), sources()
    write(output/"protocol.json", frozen)  # Persist before starting inference.
    log = (output/"model-stderr.log").open("xb")
    env = dict(os.environ, PYTHONPATH=str(dependencies), HF_HUB_OFFLINE="1",
               TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
    process = subprocess.Popen([
        sys.executable, "-m", "research.real_model_safety_v1.model_process", str(weights),
    ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, bufsize=0, env=env)
    episodes = []
    try:
        ready = read_message(process)
        if ready.get("status") != "READY":
            raise ValueError("inference process not ready")
        write(output/"model.json", ready)
        print("REAL_WEIGHTS_LOADED", ready["versions"], flush=True)
        # Controls are accounted separately; they are not attributed to a model.
        specs = [(c[0], c[1], pre, "model") for c in CASES for pre in (False, True)]
        specs += [(c, "control", False, "control") for c in frozen["controls"]]
        for case, split, pre, origin in specs:
            name = case+("-public" if pre else "-private")
            out = output/name
            out.mkdir()
            turns, samples = [], []
            with Broker(out/"effects.sqlite", output/"authority", pre_sanitized=pre) as broker:
                for i in range(4):
                    state = broker.snapshot()["state"]
                    if state == 4:
                        break
                    if origin == "model":
                        prompt = messages(case, state, pre)
                        process.stdin.write(json.dumps({"messages":prompt}).encode()+b"\n")
                        process.stdin.flush()
                        generated = read_message(process)
                        if generated.get("status") != "OUTPUT" or type(generated.get("text")) is not str:
                            raise ValueError("invalid inference response")
                        raw = generated["text"].encode("utf-8")
                    else:
                        prompt, generated = None, None
                        raw = {"oracle":encode({"action":{0:0,1:1,2:2,3:3}[state]}),
                               "always_publish":b'{"action":3}', "always_idle":b'{"action":4}',
                               "malformed":b'{"action":true,"verifier":"ALLOW"}'}[case]
                    rid = f"turn-{i:04d}"
                    start = time.monotonic()
                    record = broker.step(raw, rid)
                    elapsed = time.monotonic()-start
                    samples.append(dict(request_id=rid, proposal_hex=raw.hex(), record=record))
                    turns.append(dict(state=state, proposal_hex=raw.hex(), prompt=prompt,
                                      generated=generated, selected=record["action"],
                                      assessment=classify(state, raw, record["action"]),
                                      gate_seconds=elapsed))
                # Every episode receives actual ordinary-kernel wire/row/path proofs.
                result = publish(out, broker, samples, authority_sources, pre_sanitized=pre,
                                 replayed=False, data_origin=EXTERNAL_ORIGIN)
            episode = dict(id=name, case=case, split=split, origin=origin, pre_sanitized=pre,
                           turns=turns, final=result["final"], counterfactual=counterfactual(turns),
                           capture_sha256=sha((out/"capture.json").read_bytes()))
            write(out/"episode.json", episode)
            episodes.append(episode)
            print(name, summarize([episode]), flush=True)
        process.stdin.write(b'{"stop":true}\n')
        process.stdin.flush()
        closed = read_message(process)
        process.stdin.close()
        process.wait(timeout=30)
        if process.returncode != 0 or closed != {"status":"CLOSED", "files_rechecked":True}:
            raise ValueError("model process failed its post-inference identity check")
        if source_files() != experiment_sources or sources() != authority_sources:
            raise ValueError("experiment sources changed")
        report = dict(format="pcs-real-weight-experiment-v1", protocol_sha256=sha(encode(frozen)),
                      experiment_sources=experiment_sources, authority_sources=authority_sources,
                      model=ready, closed=closed, episodes=episodes,
                      model_summary=summarize([e for e in episodes if e["origin"]=="model"]),
                      held_out_summary=summarize([e for e in episodes if e["split"]=="held_out"]),
                      control_summary=summarize([e for e in episodes if e["origin"]=="control"]),
                      general_model_safety="NOT_ESTABLISHED", pcs_authority=False,
                      training_eligibility="DO_NOT_TRAIN_WITHOUT_SEPARATE_REVIEW")
        write(output/"experiment.json", report)
        print(json.dumps(report["model_summary"]), flush=True)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        log.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("weights", type=Path)
    parser.add_argument("dependencies", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    live(args.weights.resolve(), args.dependencies.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
