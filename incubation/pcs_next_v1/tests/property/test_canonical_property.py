import random
from pcs_next_v1.core.canonical import canonicalize, loads_strict

def test_roundtrip_random_objects():
    rng = random.Random(0)
    for _ in range(50):
        obj = {
            "n": rng.randint(-1000, 1000),
            "s": "".join(chr(rng.randint(32, 126)) for _ in range(rng.randint(0, 20))),
            "l": [rng.random() for _ in range(rng.randint(0, 5))],
            "b": rng.choice([True, False, None]),
        }
        raw = canonicalize(obj)
        back = loads_strict(raw)
        assert canonicalize(back) == raw
