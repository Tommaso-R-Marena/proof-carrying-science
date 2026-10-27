"""Fixed local-weight inference worker. No SQL, verifier or effect API."""
import argparse
import importlib.metadata
from pathlib import Path
import sys
import time
import uuid

from .artifacts import verify
from .channel import Channel
from .oracle import Oracle
from .protocol import VERSIONS,ready,check_request,output,closed,sources


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("snapshot",type=Path)
    args=parser.parse_args()
    verify(args.snapshot)
    for name,version in VERSIONS.items():
        if importlib.metadata.version(name)!=version:
            raise ValueError("reviewed inference library version required")
    import torch
    from transformers import AutoTokenizer,AutoModelForCausalLM
    torch.set_num_threads(2);torch.set_num_interop_threads(1)
    torch.manual_seed(0);torch.use_deterministic_algorithms(True)
    tokenizer=AutoTokenizer.from_pretrained(args.snapshot,local_files_only=True,trust_remote_code=False)
    model=AutoModelForCausalLM.from_pretrained(args.snapshot,local_files_only=True,trust_remote_code=False,
                                             use_safetensors=True,dtype=torch.float32,attn_implementation="eager")
    model.eval()
    oracle=Oracle(args.snapshot,profile="full")
    original_sources=sources();sid=uuid.uuid4().hex
    incoming=Channel(sys.stdin.fileno(),limit=16384)
    outgoing=Channel(sys.stdout.fileno())
    outgoing.write(ready(sid))
    for seq in range(65):
        req=check_request(incoming.read(),sid,seq)
        if sources()!=original_sources:raise ValueError("inference sources changed")
        if req["kind"]=="close":
            verify(args.snapshot)
            outgoing.write(closed(req));return
        inputs=tokenizer.apply_chat_template(req["messages"],tokenize=True,add_generation_prompt=True,
                                            enable_thinking=False,return_tensors="pt",return_dict=True)
        if inputs["input_ids"][0].tolist()!=oracle.inputs(req["messages"]):
            raise ValueError("Transformers/Rust prompt token disagreement")
        start=time.monotonic()
        with torch.inference_mode():
            generated=model.generate(**inputs,max_new_tokens=32,do_sample=False,pad_token_id=tokenizer.eos_token_id)
        ids=generated[0,inputs["input_ids"].shape[1]:].tolist()
        value=dict(status="OUTPUT",text=tokenizer.decode(ids,skip_special_tokens=True),generated_ids=ids,
                   input_ids=inputs["input_ids"][0].tolist(),seconds=time.monotonic()-start,
                   ended_with_eos=bool(ids and ids[-1]==tokenizer.eos_token_id))
        oracle.validate(req["messages"],value)
        outgoing.write(output(req,value))
    raise ValueError("explicit close within budget required")


if __name__=="__main__":main()
