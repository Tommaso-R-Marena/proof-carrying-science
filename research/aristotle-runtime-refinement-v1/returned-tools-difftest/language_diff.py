"""Differential test: Lean `PCSMathLanguage.Language.formalizeCore` vs the actual
`pcs/experimental/prover/language.py` (loaded from the exact uploaded source text).

Usage: python3 tools/difftest/language_diff.py gen  > /tmp/cases.json
       python3 tools/difftest/language_diff.py lean /tmp/cases.json > tools/difftest/LanguageCases.lean
       python3 tools/difftest/language_diff.py py   /tmp/cases.json > /tmp/py.out
"""
import json, random, sys, types, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "source_reference/proof-carrying-science/pcs/experimental/prover")

def load():
    pkg = types.ModuleType("prover"); pkg.__path__ = []; sys.modules["prover"] = pkg
    for name in ["ir", "language"]:
        mod = types.ModuleType("prover." + name); mod.__package__ = "prover"
        code = open(os.path.join(SRC, name + ".py.txt"), encoding="utf-8").read()
        sys.modules["prover." + name] = mod
        exec(compile(code, name + ".py", "exec"), mod.__dict__)
        setattr(pkg, name, mod)
    return sys.modules["prover.language"], sys.modules["prover.ir"]

def core(L, IR, names, domain, body):
    # Verbatim candidate loop of `formalize` (lines after the English rewriting).
    groups, current = [], [set()]
    for character in body:
        if character == "(": current.append(set())
        elif character == ")": groups.append(current.pop() if len(current) > 1 else current[0])
        elif character in {"∧", "∨"}: current[-1].add(character)
    ambiguous = any({"∧", "∨"} <= g for g in groups + current)
    candidates = []
    for precedence in ([L.PRECEDENCE, {**L.PRECEDENCE, "∧": 3, "∨": 4}] if ambiguous else [L.PRECEDENCE]):
        try:
            ir = IR.declaration(names, L.Parser(body, {n: domain for n in names}, precedence).complete(), domain)
            formal = IR.theorem(ir)
            if not any(c["lean"] == formal for c in candidates):
                candidates.append({"ir": ir, "lean": formal})
        except ValueError:
            return None
    return candidates

NAMES = {"Prop": ["p", "q", "r"], "Nat": ["x", "y"], "NatFn": ["f", "g"], "NatPred": ["P"], "Int": ["a", "b"]}
OPS = ["∧", "∨", "→", "↔", "=", "≤", "+", "*"]
WS = [" ", " ", " ", "", "\t", "\u00a0", "\u3000", "  "]
JUNK = ["é", "!", "_", "−", "\u200b"]

def gen_typed(rng, ty, env, depth):
    """Mostly well-typed token streams; `env` maps names to types."""
    of = [n for n, t in env.items() if t == ty]
    if depth <= 0 or rng.random() < 0.25:
        if ty == "Prop":
            return [rng.choice(of + ["True", "False"])] if of or rng.random() < 0.5 else ["True"]
        if ty in ("Nat", "Int"):
            if of and rng.random() < 0.6: return [rng.choice(of)]
            n = rng.choice(["0", "1", "7", "12", "1001"])
            return [n, ":", ty] if rng.random() < 0.3 else [n]
        return [rng.choice(of)] if of else ["x"]
    k = rng.random()
    if ty == "Prop":
        if k < 0.12: return ["¬"] + gen_typed(rng, "Prop", env, depth - 1)
        if k < 0.22: return ["("] + gen_typed(rng, "Prop", env, depth - 1) + [")"]
        if k < 0.34:
            q = rng.choice(["∀", "∃"]); bs = []; env2 = dict(env)
            for _ in range(rng.randint(1, 2)):
                v = rng.choice(["z", "w", "n", "m", "p"]); t = rng.choice(["Nat", "Prop", "Int", "Nat → Nat", "Nat → Prop", "NatFn"])
                key = {"Nat → Nat": "NatFn", "Nat → Prop": "NatPred"}.get(t, t)
                bs += ["(", v, ":"] + t.split() + [")"]; env2[v] = key
            return [q] + bs + [","] + gen_typed(rng, "Prop", env2, depth - 1)
        if k < 0.42:
            preds = [n for n, t in env.items() if t == "NatPred"]
            if preds: return [rng.choice(preds)] + arg(rng, env, depth)
        if k < 0.7:
            return gen_typed(rng, "Prop", env, depth - 1) + [rng.choice(["∧", "∨", "→", "↔"])] + gen_typed(rng, "Prop", env, depth - 1)
        t = rng.choice(["Nat", "Int"])
        return gen_typed(rng, t, env, depth - 1) + [rng.choice(["=", "≤"])] + gen_typed(rng, t, env, depth - 1)
    if ty in ("Nat", "Int"):
        fns = [n for n, t in env.items() if t == "NatFn"]
        if ty == "Nat" and fns and k < 0.25: return [rng.choice(fns)] + arg(rng, env, depth)
        if k < 0.4: return ["("] + gen_typed(rng, ty, env, depth - 1) + [")"]
        return gen_typed(rng, ty, env, depth - 1) + [rng.choice(["+", "*"])] + gen_typed(rng, ty, env, depth - 1)
    return [rng.choice(of)] if of else ["f"]

def arg(rng, env, depth):
    nats = [n for n, t in env.items() if t == "Nat"]
    if nats and rng.random() < 0.5: return [rng.choice(nats)]
    return ["("] + gen_typed(rng, "Nat", env, depth - 1) + [")"]

def gen(n=1500, seed=20261011):
    rng = random.Random(seed)
    cases = []
    for i in range(n):
        dom = rng.choice(list(NAMES))
        names = rng.sample(NAMES[dom], rng.randint(1, len(NAMES[dom])))
        if rng.random() < 0.05: names = names + names[:1]
        toks = gen_typed(rng, "Prop", {n: dom for n in names}, rng.randint(1, 5))
        if rng.random() < 0.08 and len(toks) > 1:
            j = rng.randrange(len(toks)); toks = toks[:j] + toks[j+1:]
        body = ""
        for t in toks:
            body += t + rng.choice(WS)
        if rng.random() < 0.05:
            pos = rng.randint(0, len(body)); body = body[:pos] + rng.choice(JUNK) + body[pos:]
        cases.append({"names": names, "domain": dom, "body": body})
    fixed = [
        (["p", "q"], "Prop", "p ∧ q ∨ p"), (["p", "q"], "Prop", "(p ∧ q) ∨ p"),
        (["p", "q"], "Prop", "p∧q∨p"), (["p", "q"], "Prop", "p ∧ (q ∨ p)"),
        (["p", "q"], "Prop", "p\u3000∧\u00a0q"), (["p", "q"], "Prop", "p ∧\u200bq"),
        (["p", "q"], "Prop", "pé ∧ q"), (["p", "p"], "Prop", "p"), (["x", "a"], "Nat", "x = 3"),
        (["x"], "Nat", "∀ (x : Nat), x = x"), (["f"], "NatFn", "∀ (n : Nat), f n = f n"),
        (["f"], "NatFn", "∀ (g : Nat → Nat), g (f 1) = 2"), (["x"], "Nat", "1001 = 1001"),
        (["x"], "Nat", "x ≤ 3 : Int"), (["p"], "Prop", "p → p → p"), (["p"], "Prop", "¬ p ∧ p"),
        (["p"], "Prop", "∀ (q : Prop) (q : Prop), q"), (["p"], "Prop", "∃ , p"),
        (["p", "q"], "Prop", "(p ∨ q ∧ p) ∧ (q ∨ p)"), (["P"], "NatPred", "P 1 ∧ P 2 ∨ P 3"),
        (["x", "y"], "Int", "x + y * 2 = y"), (["sorry"], "Prop", "sorry"), (["True"], "Prop", "True"),
    ]
    cases += [{"names": a, "domain": b, "body": c} for a, b, c in fixed]
    return cases

def lean_str(s):
    out = '"'
    for c in s:
        if c == '"': out += '\\"'
        elif c == '\\': out += '\\\\'
        elif c == '\t': out += '\\t'
        elif ord(c) > 126 or ord(c) < 32: out += '\\u%04x' % ord(c)
        else: out += c
    return out + '"'

TY = {"Prop": ".prop", "Nat": ".nat", "Int": ".int", "NatFn": ".natFn", "NatPred": ".natPred"}

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "gen":
        json.dump(gen(), sys.stdout, ensure_ascii=False)
    elif mode == "lean":
        cases = json.load(open(sys.argv[2], encoding="utf-8"))
        print("import PCSMathLanguage.Language\n\nopen PCSMathLanguage PCSMathLanguage.Language\n")
        print("def cases : List (List String × Ty × String) := [")
        print(",\n".join("  ([%s], %s, %s)" % (", ".join(lean_str(n) for n in c["names"]), TY[c["domain"]], lean_str(c["body"])) for c in cases))
        print("]\n")
        print('def render1 (c : List String × Ty × String) : String :=\n'
              '  match formalizeCore c.1 c.2.1 c.2.2 none with\n'
              '  | none => "U"\n'
              '  | some cs => " ||| ".intercalate (cs.map (·.lean))\n')
        print('#eval IO.println ("\\n".intercalate (cases.map render1))')
    elif mode == "py":
        L, IR = load()
        cases = json.load(open(sys.argv[2], encoding="utf-8"))
        for c in cases:
            r = core(L, IR, c["names"], c["domain"], c["body"])
            print("U" if r is None else " ||| ".join(x["lean"] for x in r))
