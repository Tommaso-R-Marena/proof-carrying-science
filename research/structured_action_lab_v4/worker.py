"""Pinned local inference with a fixed format-only prefix constraint."""
import argparse
import importlib.metadata
from pathlib import Path
import sys,time,uuid
from research.real_model_execution_v2.artifacts import verify
from research.real_model_execution_v2.channel import Channel
from research.real_model_execution_v2.protocol import VERSIONS
from .codec import ActionOracle
from .protocol import ready,check_request,output,closed,sources


def main():
    p=argparse.ArgumentParser();p.add_argument("snapshot",type=Path);p.add_argument("mode",choices=("raw","trie"));args=p.parse_args()
    verify(args.snapshot)
    for name,version in VERSIONS.items():
        if importlib.metadata.version(name)!=version:raise ValueError("Reviewed inference library versions required")
    import torch
    from transformers import AutoTokenizer,AutoModelForCausalLM
    torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.manual_seed(0);torch.use_deterministic_algorithms(True)
    tokenizer=AutoTokenizer.from_pretrained(args.snapshot,local_files_only=True,trust_remote_code=False)
    model=AutoModelForCausalLM.from_pretrained(args.snapshot,local_files_only=True,trust_remote_code=False,use_safetensors=True,dtype=torch.float32,attn_implementation="eager")
    model.eval();oracle=ActionOracle(args.snapshot,profile="full",mode=args.mode)
    before=sources();sid=uuid.uuid4().hex;incoming=Channel(sys.stdin.fileno(),limit=16384);outgoing=Channel(sys.stdout.fileno())
    outgoing.write(ready(sid,args.mode))
    for seq in range(65):
        req=check_request(incoming.read(),sid,seq)
        if sources()!=before:raise ValueError("Inference sources changed")
        if req["kind"]=="close":verify(args.snapshot);outgoing.write(closed(req,args.mode));return
        inputs=tokenizer.apply_chat_template(req["messages"],tokenize=True,add_generation_prompt=True,enable_thinking=False,return_tensors="pt",return_dict=True)
        prompt=inputs["input_ids"][0].tolist()
        if prompt!=oracle.inputs(req["messages"]):raise ValueError("Transformers/Rust prompt token disagreement")
        def allowed(batch,ids):
            if batch!=0:raise ValueError("Only a single greedy sequence is supported")
            return oracle.trie.allowed(ids.tolist()[len(prompt):])
        options=dict(prefix_allowed_tokens_fn=allowed) if args.mode=="trie" else {}
        start=time.monotonic()
        with torch.inference_mode():generated=model.generate(**inputs,max_new_tokens=32,do_sample=False,pad_token_id=tokenizer.eos_token_id,**options)
        ids=generated[0,len(prompt):].tolist()
        value=dict(status="OUTPUT",text=tokenizer.decode(ids,skip_special_tokens=True),generated_ids=ids,input_ids=prompt,seconds=time.monotonic()-start,ended_with_eos=bool(ids and ids[-1]==tokenizer.eos_token_id))
        oracle.validate(req["messages"],value);outgoing.write(output(req,value,args.mode))
    raise ValueError("Explicit close within budget required")


if __name__=="__main__":main()
