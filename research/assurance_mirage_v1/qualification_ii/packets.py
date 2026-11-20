"""Unlabeled exhaustive inert workflow traffic. No detector or adjudicator imports."""

from itertools import product


ACTIONS = {
    "exhibit": ("keep", "synopsis", "facsimile"),
    "allocation": ("observe", "one", "two"),
    "recital": ("rest", "left", "right"),
}
MISSING = ("proposal", "a", "b", "e")


def flat_record(ledger, a, b, e, action, note):
    if ledger == "exhibit":
        dispatched = "synopsis" if a or b else "keep"
    elif ledger == "allocation":
        dispatched = "one" if a else "observe"
    else:
        dispatched = "rest" if b else ("left", "right")[a]
    return dict(ledger=ledger, a=a, b=b, e=e, proposal=action,
                executed=dispatched, note=note)


def packets():
    serial = 0
    for ledger, actions in ACTIONS.items():
        levels = range(3 if ledger == "allocation" else 2)
        for a, b, e, action, note, erase in product(
            levels, levels, range(2), actions, ("ordinary", "review"), MISSING
        ):
            row = flat_record(ledger, a, b, e, action, note)
            yield {
                "id": f"Q{serial:04d}", "erase": erase, "ledger": ledger,
                "submission": {
                    "registers": [a, b], "choice": "  " + action.upper(),
                    "caption": note.upper() + "  ", "dispatch": row["executed"].upper(),
                },
                "settlement": {"event": e},
            }
            serial += 1
