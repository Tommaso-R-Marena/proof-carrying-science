"""Smallest reproducer: `formalize` lets a RecursionError escape for a statement inside the
3000-character language bound (CPython 3.11, default recursion limit 1000).

Run from the archive root:  python3 counterexamples/language_recursion/reproduce.py [patched]
"""
import os, sys, types

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "source_reference/proof-carrying-science/pcs/experimental/prover")
PATCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "language_depth_guard.patch")

def load(patched):
    pkg = types.ModuleType("prover"); pkg.__path__ = []; sys.modules["prover"] = pkg
    for name in ["ir", "language"]:
        code = open(os.path.join(SRC, name + ".py.txt"), encoding="utf-8").read()
        if patched and name == "language":
            code = code.replace(
                "    def parse(self, minimum=0):\n        tok = self.take()\n",
                "    def parse(self, minimum=0, depth=0):\n        if depth > 256:\n            raise ValueError(\"statement nesting exceeds language bound\")\n        tok = self.take()\n")
            for old, new in [("left = self.parse()\n            self.take(\")\")", "left = self.parse(0, depth + 1)\n            self.take(\")\")"),
                             ("self.take(\",\")\n            left = self.parse()", "self.take(\",\")\n            left = self.parse(0, depth + 1)"),
                             ("{\"op\": \"not\", \"arg\": self.parse(8)}", "{\"op\": \"not\", \"arg\": self.parse(8, depth + 1)}"),
                             ("\"arg\": self.parse(8)}\n        else:", "\"arg\": self.parse(8, depth + 1)}\n        else:"),
                             ("right = self.parse(p if symbol == \"→\" else p + 1)", "right = self.parse(p if symbol == \"→\" else p + 1, depth + 1)")]:
                assert old in code, old
                code = code.replace(old, new)
        mod = types.ModuleType("prover." + name); mod.__package__ = "prover"
        sys.modules["prover." + name] = mod
        exec(compile(code, name + ".py", "exec"), mod.__dict__)
    return sys.modules["prover.language"]

if __name__ == "__main__":
    patched = len(sys.argv) > 1 and sys.argv[1] == "patched"
    L = load(patched)
    k = 995
    source = "For all propositions p, " + "(" * k + "p" + ")" * k
    print("python", sys.version.split()[0], "recursion limit", sys.getrecursionlimit())
    print("source length", len(source), "(language bound 3000)")
    try:
        r = L.formalize(source)
        print("status:", r["status"], "|", r.get("reason", ""))
    except RecursionError:
        print("UNCAUGHT RecursionError escaped formalize")
