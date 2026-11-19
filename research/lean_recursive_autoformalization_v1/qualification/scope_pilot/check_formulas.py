"""Generate Lean obligations for individual wire formulas relative to reviewer statements."""
import json
from pathlib import Path
from replay import formula, unique

HERE = Path(__file__).resolve().parent

# Handwritten logical counterparts to the frozen set-theoretic references.
REFERENCES = {
    "a": "∀ z, T z → I z", "b": "∀ z, I z → T z",
    "c": "∃ z, T z ∧ I z", "d": "∃ z, T z ∧ ¬ I z",
    "e": "¬ ∃ z, T z ∧ I z", "f": "∃ z, I z ∧ ¬ T z",
    "g": "∀ z, T z ∨ I z", "h": "¬ ∀ z, T z",
    "i": "(∃ z, T z) → ∃ z, I z", "j": "∀ z, T z ∧ I z",
    "k": "∃ z, ¬T z ∧ ¬I z", "l": "∀ z, T z ↔ I z",
}


def render(expr):
    if expr == "T":
        return "Formula.tag"
    if expr == "I":
        return "Formula.inspected"
    names = {"not": "neg", "and": "conj", "or": "disj", "all": "all", "some": "someObj",
             "imp": "impl", "iff": "iff"}
    op, *children = expr
    return "(Formula." + names[op] + " " + " ".join(map(render, children)) + ")"


def generate():
    receipt = json.loads((HERE / "attempt.json").read_bytes())
    response, = receipt["candidates"]
    asts = json.loads("".join(p["text"] for p in response["content"]["parts"]), object_pairs_hook=unique)
    lines = ["import ProfileQuotient", "open ScopePilot", "namespace RecordedFormulas"]
    for name, ref in REFERENCES.items():
        term = render(formula(asts[name]))
        lines.extend([f"theorem item_{name} {{D : Type}} (d : D → Profile) (x : D) :",
                      "    let T := fun z => (d z).1 = true",
                      *(["    let I := fun z => (d z).2 = true"] if "I" in ref else []),
                      f"    truth d x {term} ↔ ({ref}) := by",
                      "  simp [truth]", f"#print axioms item_{name}"])
    return "\n".join([*lines, "end RecordedFormulas", ""])


if __name__ == "__main__":
    print(generate(), end="")
