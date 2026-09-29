from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import struct
import subprocess
from pathlib import Path

from pcs.canonical_json import canonicalize_jcs


ROOT = Path(__file__).resolve().parents[1]


def _node(script: str, stdin: str) -> str:
    node = shutil.which("node")
    if node is None:
        raise SystemExit("Node.js is required for the JCS differential stress check")
    proc = subprocess.run(
        [node, "--input-type=module", "-e", script],
        cwd=ROOT,
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr or proc.stdout)
    return proc.stdout


def _finite_bit_patterns(count: int, rng: random.Random) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    while len(out) < count:
        bits = rng.getrandbits(64)
        value = struct.unpack(">d", bits.to_bytes(8, "big"))[0]
        if math.isfinite(value):
            out.append((f"{bits:016x}", value))
    return out


def _valid_char(rng: random.Random) -> str:
    while True:
        cp = rng.randrange(0x110000)
        if 0xD800 <= cp <= 0xDFFF:
            continue
        if 0xFDD0 <= cp <= 0xFDEF or (cp & 0xFFFF) in (0xFFFE, 0xFFFF):
            continue
        return chr(cp)


def _random_string(rng: random.Random, max_length: int = 6) -> str:
    return "".join(_valid_char(rng) for _ in range(rng.randrange(max_length + 1)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Differentially test PCS JCS against Node/V8")
    parser.add_argument("--numbers", type=int, default=20000)
    parser.add_argument("--objects", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20260929)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    patterns = _finite_bit_patterns(args.numbers, rng)
    node_number_script = r"""
import fs from "node:fs";
import { canonicalizeJcs } from "./site/jcs.mjs";
const hexes = fs.readFileSync(0, "utf8").trim().split(/\s+/).filter(Boolean);
for (const hex of hexes) {
  const bytes = Buffer.from(hex, "hex");
  process.stdout.write(canonicalizeJcs(bytes.readDoubleBE(0)) + "\n");
}
"""
    node_numbers = _node(node_number_script, "\n".join(bits for bits, _ in patterns)).splitlines()
    if len(node_numbers) != len(patterns):
        raise SystemExit("Node numeric result count mismatch")
    for (bits, value), node_text in zip(patterns, node_numbers, strict=True):
        python_text = canonicalize_jcs(value)
        if python_text != node_text:
            raise SystemExit(
                f"number mismatch {bits}: Python={python_text!r} Node={node_text!r}"
            )

    objects: list[dict] = []
    while len(objects) < args.objects:
        obj: dict = {}
        for _ in range(rng.randrange(1, 8)):
            obj[_random_string(rng)] = [
                _random_string(rng),
                rng.choice([True, False, None]),
                rng.uniform(-1e8, 1e8),
            ]
        objects.append(obj)

    node_object_script = r"""
import fs from "node:fs";
import { canonicalizeJcs } from "./site/jcs.mjs";
const values = JSON.parse(fs.readFileSync(0, "utf8"));
process.stdout.write(JSON.stringify(values.map(canonicalizeJcs)));
"""
    node_objects = json.loads(
        _node(node_object_script, json.dumps(objects, ensure_ascii=False, allow_nan=False))
    )
    for index, (value, node_text) in enumerate(zip(objects, node_objects, strict=True)):
        python_text = canonicalize_jcs(value)
        if python_text != node_text:
            raise SystemExit(
                f"Unicode/object mismatch {index}: Python={python_text!r} Node={node_text!r}"
            )

    print(
        f"JCS differential PASS: {len(patterns)} finite IEEE-754 numbers, "
        f"{len(objects)} randomized Unicode objects, seed={args.seed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
