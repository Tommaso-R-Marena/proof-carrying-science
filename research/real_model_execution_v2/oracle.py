"""Independent fixed chat renderer + Rust tokenizer, with no Transformers/Jinja.

    Only the original two-message, no-tools, nonthinking protocol is supported.
    Tokenization correspondence is tested, not a Lean theorem about neural nets.
"""
import math
from .artifacts import verify

EOS = 151645
VOCAB_LIMIT = 151936
OUTPUT_FIELDS = {"status","text","input_ids","generated_ids","seconds","ended_with_eos"}


def render(messages):
    if type(messages) is not list or len(messages) != 2:
        raise ValueError("fixed two-message prompt required")
    for message, role in zip(messages, ("system", "user")):
        if type(message) is not dict or set(message) != {"role","content"} or message["role"] != role:
            raise ValueError("exact prompt roles/schema required")
        if type(message["content"]) is not str or len(message["content"].encode("utf-8")) > 8192:
            raise ValueError("bounded UTF-8 prompt required")
    return ("<|im_start|>system\n"+messages[0]["content"]+"<|im_end|>\n"
            "<|im_start|>user\n"+messages[1]["content"]+"<|im_end|>\n"
            "<|im_start|>assistant\n<think>\n\n</think>\n\n")


class Oracle:
    def __init__(self, root, profile="tokenizer"):
        verify(root, profile)
        from tokenizers import Tokenizer
        self.tokenizer = Tokenizer.from_file(str(root/"tokenizer.json"))
        if self.tokenizer.token_to_id("<|im_end|>") != EOS:
            raise ValueError("pinned EOS disagreement")
        self.special = {i for i,t in self.tokenizer.get_added_tokens_decoder().items() if t.special}
        verify(root, profile)

    def inputs(self, messages):
        result = self.tokenizer.encode(render(messages), add_special_tokens=False).ids
        if not 0 < len(result) <= 4096:
            raise ValueError("bounded prompt token count required")
        return result

    def validate(self, messages, value):
        if type(value) is not dict or set(value) != OUTPUT_FIELDS or value["status"] != "OUTPUT":
            raise ValueError("exact generation schema required")
        for name, maximum in (("input_ids",4096),("generated_ids",32)):
            ids = value[name]
            if type(ids) is not list or not 0 < len(ids) <= maximum or any(type(i) is not int or not 0<=i<VOCAB_LIMIT for i in ids):
                raise ValueError("exact bounded token IDs required")
        if value["input_ids"] != self.inputs(messages):
            raise ValueError("prompt/token disagreement")
        ids = value["generated_ids"]
        if any(self.tokenizer.id_to_token(i) is None for i in ids):
            raise ValueError("unknown generated token")
        if any(i in self.special and i != EOS for i in ids) or EOS in ids[:-1]:
            raise ValueError("unexpected control token or premature EOS")
        if type(value["ended_with_eos"]) is not bool or value["ended_with_eos"] != (ids[-1] == EOS):
            raise ValueError("EOS claim disagrees with tokens")
        if ids[-1] != EOS and len(ids) != 32:
            raise ValueError("unexplained early termination")
        text = self.tokenizer.decode(ids, skip_special_tokens=True)
        if type(value["text"]) is not str or value["text"] != text or len(text.encode("utf-8")) > 4096:
            raise ValueError("decoded text/token disagreement")
        if type(value["seconds"]) not in (int,float) or not math.isfinite(value["seconds"]) or not 0<=value["seconds"]<=300:
            raise ValueError("bounded finite generation time required")
        return text.encode("utf-8")
