"""Case-insensitive path collision scanner.

Detects the class of bug that broke Workstream D CI when both ``CHECKLIST.json``
and ``checklist.json`` existed under the same directory on a case-insensitive
filesystem (or under repository integrity policies that forbid such pairs).
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    ".venv",
    "venv",
}


@dataclass(frozen=True)
class CollisionGroup:
    """Paths that collide when compared case-insensitively."""

    key: str
    paths: tuple[str, ...]

    @property
    def collision_count(self) -> int:
        return len(self.paths)


@dataclass(frozen=True)
class CollisionReport:
    """Result of scanning a tree for case-insensitive path collisions."""

    format: str
    root: str
    file_count: int
    collision_groups: tuple[CollisionGroup, ...]

    @property
    def has_collisions(self) -> bool:
        return bool(self.collision_groups)

    def to_dict(self) -> dict:
        return {
            "format": self.format,
            "root": self.root,
            "file_count": self.file_count,
            "collision_group_count": len(self.collision_groups),
            "has_collisions": self.has_collisions,
            "collision_groups": [
                {"key": g.key, "paths": list(g.paths), "collision_count": g.collision_count}
                for g in self.collision_groups
            ],
        }


def _iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return
    if root.is_file():
        yield root
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        yield path


def scan_path_collisions(root: Path | str) -> CollisionReport:
    """Scan ``root`` for distinct relative paths that collide case-insensitively.

    Grouping key is the lowercase POSIX relative path (including directory
    components). Two files collide when their relative paths differ only by
    letter case, e.g. ``dir/CHECKLIST.json`` vs ``dir/checklist.json``.
    """
    root_path = Path(root).resolve()
    buckets: dict[str, set[str]] = defaultdict(set)
    file_count = 0

    for file_path in _iter_files(root_path):
        file_count += 1
        try:
            rel = file_path.relative_to(root_path).as_posix()
        except ValueError:
            rel = file_path.as_posix()
        key = rel.casefold()
        buckets[key].add(rel)

    groups = tuple(
        CollisionGroup(key=key, paths=tuple(sorted(paths)))
        for key, paths in sorted(buckets.items())
        if len(paths) > 1
    )
    return CollisionReport(
        format="pcs-independent-path-collision-scan-v1",
        root=str(root_path),
        file_count=file_count,
        collision_groups=groups,
    )


def write_collision_report(report: CollisionReport, out_path: Path | str) -> Path:
    """Write a collision report as sorted JSON."""
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    import argparse

    from .paths import INDEPENDENT_EVAL, RESULTS

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=INDEPENDENT_EVAL,
        help="Tree to scan (default: independent_eval/)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=RESULTS / "path_collision_report.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--fail-on-collision",
        action="store_true",
        help="Exit non-zero when collisions are found",
    )
    args = parser.parse_args(argv)

    report = scan_path_collisions(args.root)
    write_collision_report(report, args.out)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    if args.fail_on_collision and report.has_collisions:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
