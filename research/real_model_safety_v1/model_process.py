"""CPU inference only. No broker, effects, proofs or verdicts in this process.

Uses local safetensors and library architecture code, never remote model code.
The parent process supplies observations and treats every output as untrusted.
This interface separation does not sandbox a hostile same-user process.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time

from .protocol import WEIGHTS_SHA256


def inventory(root):
    result = {}
    for p in sorted(root.iterdir()):
        if p.is_file():
            with p.open("rb") as stream:
                result[p.name] = dict(bytes=p.stat().st_size,
                                      sha256=hashlib.file_digest(stream, "sha256").hexdigest())
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("weights", type=Path)
    args = parser.parse_args()
    before = inventory(args.weights)
    if before["model.safetensors"]["sha256"] != WEIGHTS_SHA256:
        raise ValueError("pinned weight digest mismatch")
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)
    start = time.monotonic()
    tokenizer = AutoTokenizer.from_pretrained(args.weights, local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(
        args.weights, local_files_only=True, trust_remote_code=False,
        use_safetensors=True, dtype=torch.float32, attn_implementation="eager")
    model.eval()
    if inventory(args.weights) != before:
        raise ValueError("model files changed while loading")
    ready = dict(status="READY", files=before, load_seconds=time.monotonic()-start,
                 versions={p: importlib.metadata.version(p) for p in
                           ("torch", "transformers", "tokenizers", "safetensors")},
                 dtype="float32", device="cpu", threads=2)
    print(json.dumps(ready), flush=True)
    for _ in range(64):
        line = sys.stdin.buffer.readline(16385)
        if not line:
            break
        if len(line)>16384 or not line.endswith(b"\n"):
            raise ValueError("bounded JSONL request required")
        request = json.loads(line)
        if request == {"stop": True}:
            if inventory(args.weights) != before:
                raise ValueError("model files changed during inference")
            print(json.dumps(dict(status="CLOSED", files_rechecked=True)), flush=True)
            return
        if set(request) != {"messages"}:
            raise ValueError("messages-only inference request")
        inputs = tokenizer.apply_chat_template(
            request["messages"], tokenize=True, add_generation_prompt=True,
            enable_thinking=False, return_tensors="pt", return_dict=True)
        start = time.monotonic()
        with torch.inference_mode():
            outputs = model.generate(**inputs, max_new_tokens=32, do_sample=False,
                                     pad_token_id=tokenizer.eos_token_id)
        ids = outputs[0, inputs["input_ids"].shape[1]:].tolist()
        text = tokenizer.decode(ids, skip_special_tokens=True)
        print(json.dumps(dict(status="OUTPUT", text=text, generated_ids=ids,
                              input_ids=inputs["input_ids"][0].tolist(),
                              seconds=time.monotonic()-start,
                              ended_with_eos=bool(ids and ids[-1] == tokenizer.eos_token_id))), flush=True)
    raise ValueError("explicit close required within request budget")


if __name__ == "__main__":
    main()
