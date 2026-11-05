"""Format-only finite token language; never filters actions by policy/state."""
from research.real_model_execution_v2.oracle import Oracle,EOS

PAYLOADS=tuple(b'{"action":'+str(a).encode()+b'}' for a in range(7))


def decode(raw):
    if type(raw) is not bytes:raise ValueError("Exact canonical bytes required")
    return PAYLOADS.index(raw) if raw in PAYLOADS else None


class Trie:
    def __init__(self,paths):
        if type(paths) is not tuple or len(paths)!=7 or any(type(p) is not tuple or not p or len(p)>=32 or any(type(t) is not int or t<0 or t>=151936 or t==EOS for t in p) for p in paths):
            raise ValueError("Seven bounded noncontrol token paths required")
        if len(set(paths))!=7 or any(a!=b and len(a)<=len(b) and b[:len(a)]==a for a in paths for b in paths):
            raise ValueError("Unique prefix-free payload paths required")
        self.paths=paths

    def allowed(self,prefix):
        if type(prefix) not in (list,tuple) or any(type(t) is not int for t in prefix):raise ValueError("Exact token prefix required")
        prefix=tuple(prefix)
        result=sorted({(p+(EOS,))[len(prefix)] for p in self.paths if len(prefix)<=len(p) and (p+(EOS,))[:len(prefix)]==prefix})
        if not result:raise ValueError("Prefix outside the declared language")
        return result

    def action(self,ids):
        if type(ids) not in (list,tuple) or any(type(t) is not int for t in ids):raise ValueError("Exact token sequence required")
        try:return tuple(p+(EOS,) for p in self.paths).index(tuple(ids))
        except ValueError:raise ValueError("Not a complete canonical action plus EOS") from None


class ActionOracle(Oracle):
    def __init__(self,root,profile="tokenizer",*,mode):
        if mode not in ("raw","trie"):raise ValueError("Unknown output profile")
        super().__init__(root,profile);self.mode=mode
        paths=tuple(tuple(self.tokenizer.encode(p.decode(),add_special_tokens=False).ids) for p in PAYLOADS)
        self.trie=Trie(paths)
        for action,ids in enumerate(paths):
            if self.tokenizer.decode(list(ids),skip_special_tokens=True).encode()!=PAYLOADS[action]:
                raise ValueError("Canonical action token/byte disagreement")

    def validate(self,messages,value):
        raw=super().validate(messages,value)
        if self.mode=="trie":
            action=self.trie.action(value["generated_ids"])
            if raw!=PAYLOADS[action] or decode(raw)!=action:raise ValueError("Token language/byte codec disagreement")
        return raw
