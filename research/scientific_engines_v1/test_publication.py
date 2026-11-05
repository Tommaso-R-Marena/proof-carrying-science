"""Storage tests only. These do not simulate or claim scientific authorization."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from .verifier import _publish


def test_concurrent_publication_has_one_winner_and_complete_bytes(tmp_path):
    target = tmp_path / "evidence.json"
    barrier = Barrier(8)

    def writer(i):
        barrier.wait()
        try:
            _publish(target, dict(writer=i, payload="x" * 10000))
            return i
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(writer, range(8)))
    winners = [r for r in results if r is not None]
    assert len(winners) == 1
    import json

    assert json.loads(target.read_bytes()) == dict(
        writer=winners[0], payload="x" * 10000
    )
    assert not list(tmp_path.glob(".pcs-scientific-*"))


def test_dangling_symlink_is_not_overwritten(tmp_path):
    import pytest

    target = tmp_path / "evidence.json"
    target.symlink_to(tmp_path / "missing")
    with pytest.raises(ValueError, match="overwrite"):
        _publish(target, dict(accepted=False))
    assert target.is_symlink() and not (tmp_path / "missing").exists()
