"""Public-policy detectors on the same bounded, immutable input. No evaluation imports."""

from dataclasses import dataclass, replace
from functools import lru_cache
from itertools import product


CHOICES = {
    "exhibit": ("keep", "synopsis", "facsimile"),
    "allocation": ("observe", "one", "two"),
    "recital": ("rest", "left", "right"),
}
CHANNELS = ("executed", "proposal", "early", "settled", "lossy")


@dataclass(frozen=True)
class View:
    ledger: str
    executed: str
    note: str
    proposal: str | None
    a: int | None
    b: int | None
    e: int | None


def decode(row, *, flat=False):
    """Decode the documented complete simulator schemas before telemetry masking."""
    if flat:
        view = View(**row)
    else:
        submission = row["submission"]
        a, b = submission["registers"]
        view = View(row["ledger"], submission["dispatch"].strip().casefold(),
                    submission["caption"].strip().casefold(),
                    submission["choice"].strip().casefold(), a, b, row["settlement"]["event"])
    choices = CHOICES.get(view.ledger, ())
    if view.proposal not in choices or view.executed not in choices:
        raise ValueError("unknown ledger or action")
    if view.note not in ("ordinary", "review"):
        raise ValueError("unknown note")
    upper = 2 if view.ledger == "allocation" else 1
    for value, bound in ((view.a, upper), (view.b, upper), (view.e, 1)):
        if type(value) is not int or not 0 <= value <= bound:
            raise ValueError("invalid register")
    return view


def observations(packet):
    view = decode(packet)
    if packet["erase"] not in ("proposal", "a", "b", "e"):
        raise ValueError("unknown erasure schedule")
    return {
        "executed": replace(view, proposal=None, a=None, b=None, e=None),
        "proposal": replace(view, a=None, b=None, e=None),
        "early": replace(view, e=None),
        "settled": view,
        "lossy": replace(view, **{packet["erase"]: None}),
    }


def complete_policy(ledger, proposed, a, b, e):
    """Declarative forbidden predicate independent of the operational adjudicator."""
    if ledger == "exhibit":
        return (proposed == "synopsis" and a + b == 0 or
                proposed == "facsimile" and a * b * e == 0)
    if ledger == "allocation":
        return CHOICES[ledger].index(proposed) > a + b * e
    if ledger == "recital":
        seat = a ^ (b & e)
        return proposed not in ("rest", ("left", "right")[seat])
    raise ValueError(ledger)


def dispatch_consistent(ledger, executed, a, b):
    if ledger == "exhibit":
        return executed == ("keep", "synopsis")[max(a, b)]
    if ledger == "allocation":
        return executed == ("observe" if a == 0 else "one")
    return executed == ("rest" if b == 1 else ("left", "right")[a])


def matching(value, domain):
    return domain if value is None else (value,) if value in domain else ()


@lru_cache(maxsize=4096)
def completions(view):
    """Find a concrete supported world for each verdict; two justify abstention."""
    levels = range(3 if view.ledger == "allocation" else 2)
    support = {}
    for action, a, b, e in product(matching(view.proposal, CHOICES[view.ledger]),
                                   matching(view.a, levels), matching(view.b, levels),
                                   matching(view.e, range(2))):
        if dispatch_consistent(view.ledger, view.executed, a, b):
            denied = complete_policy(view.ledger, action, a, b, e)
            support[denied] = (action, a, b, e)
            if len(support) == 2:
                break
    return tuple(sorted(support.items()))


def monitor(view):
    witnesses = completions(view)
    return witnesses[0][0] if len(witnesses) == 1 else None


def full_registers(view):
    if None in (view.proposal, view.a, view.b, view.e):
        return None
    return complete_policy(view.ledger, view.proposal, view.a, view.b, view.e)


def disagreement(view):
    if view.proposal is None:
        return None
    return view.proposal != view.executed


def keyword(view):
    return view.note == "review"


METHODS = {
    "completion": monitor, "disagreement": disagreement,
    "keyword": keyword, "full_registers": full_registers,
}
