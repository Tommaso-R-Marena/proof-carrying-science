"""Real filesystem attacks at the registry/public-key boundary."""
import os
from pathlib import Path

import pytest

from pcs import key_lifecycle as lifecycle
from pcs.signing import generate_keypair


def symlink(source, target):
    try:
        source.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("filesystem does not permit test symlinks")


def test_registry_symlink_rejected_without_changing_target(tmp_path):
    real = tmp_path / "real.json"
    lifecycle.write_new_registry(real, "original")
    before = real.read_bytes()
    link = tmp_path / "link.json"
    symlink(link, real)
    with pytest.raises(lifecycle.KeyLifecycleError, match="regular file"):
        lifecycle.load_registry(link)
    with pytest.raises(lifecycle.KeyLifecycleError, match="symlink"):
        lifecycle.write_new_registry(link, "replacement")
    assert real.read_bytes() == before


def test_public_key_symlink_rejected(tmp_path):
    public = tmp_path / "public.pem"
    generate_keypair(tmp_path / "private.pem", public)
    link = tmp_path / "public-link.pem"
    symlink(link, public)
    with pytest.raises(lifecycle.KeyLifecycleError, match="regular file"):
        lifecycle._public_key_metadata(link)


def test_missing_and_oversized_files_are_bounded(tmp_path):
    with pytest.raises(lifecycle.KeyLifecycleError, match="safely read"):
        lifecycle.load_registry(tmp_path / "missing")
    large = tmp_path / "large.json"
    large.write_bytes(b" " * 1_048_577)
    with pytest.raises(lifecycle.KeyLifecycleError, match="byte limit"):
        lifecycle.load_registry(large)


def test_directory_and_fifo_rejected_before_read(tmp_path):
    with pytest.raises(lifecycle.KeyLifecycleError, match="regular file"):
        lifecycle.load_registry(tmp_path)
    if hasattr(os, "mkfifo"):
        fifo = tmp_path / "fifo"
        os.mkfifo(fifo)
        with pytest.raises(lifecycle.KeyLifecycleError, match="regular file"):
            lifecycle.load_registry(fifo)


def test_read_rejects_leaf_swapped_after_inspection(tmp_path, monkeypatch):
    registry = tmp_path / "registry.json"
    lifecycle.write_new_registry(registry, "original")
    replacement = tmp_path / "replacement.json"
    lifecycle.write_new_registry(replacement, "different")
    original_open = os.open

    def swapped_open(path, flags, *args, **kwargs):
        if Path(path) == registry:
            os.replace(replacement, registry)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(lifecycle.os, "open", swapped_open)
    with pytest.raises(lifecycle.KeyLifecycleError, match="changed while opening"):
        lifecycle.load_registry(registry)


def test_no_clobber_install_rejects_racing_creator(tmp_path, monkeypatch):
    registry = tmp_path / "registry.json"
    competitor = b"another operator's file"
    original_link = os.link

    def racing_link(source, destination, *args, **kwargs):
        Path(destination).write_bytes(competitor)
        return original_link(source, destination, *args, **kwargs)

    monkeypatch.setattr(lifecycle.os, "link", racing_link)
    with pytest.raises(lifecycle.KeyLifecycleError, match="refusing to overwrite"):
        lifecycle.write_new_registry(registry, "new")
    assert registry.read_bytes() == competitor
    assert not list(tmp_path.glob(".*.tmp"))
