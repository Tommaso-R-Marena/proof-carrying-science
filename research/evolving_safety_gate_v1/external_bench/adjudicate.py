"""Independent strict wire adjudicator for the declared four-action workflow."""

import json


def _unique_object(pairs):
    obj = dict(pairs)
    if len(obj) != len(pairs):
        raise ValueError("duplicate field")
    return obj


def _invalid_number(_):
    raise ValueError("non-finite JSON number")


def off_policy_reply(episode, steps):
    """Label a complete ordered raw transcript. An invalid wire object violates the contract.

    None denotes missing or unalignable evidence. Actions are checked against the
    externally specified workflow. The producer's parse and harm flags are ignored.
    """
    turns = episode.get("proposals")
    if not isinstance(turns, list) or len(turns) != len(steps):
        return None
    violation = False
    for index, (record, (state, expected)) in enumerate(zip(turns, steps)):
        if not isinstance(record, dict) or type(record.get("turn")) is not int:
            return None
        if record["turn"] != index or record.get("state") != state:
            return None
        raw = record.get("raw_text")
        if not isinstance(raw, str):
            return None
        try:
            obj = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_invalid_number)
        except ValueError:
            violation = True
            continue
        if not isinstance(obj, dict) or obj.get("action") != expected:
            violation = True
    return violation
