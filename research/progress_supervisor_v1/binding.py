"""Captured source identity, shared by native builds and untrusted replay intake.

Immutable values avoid accidental aliasing; the interpreter/filesystem/host are
still trusted. Computing this identity is not a verification verdict.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .certificate import encode, literal_source, sha

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC_FILES = ("Adapter.lean", "AdapterBridge.lean", "AdapterTable.lean")
NATIVE_FILES = ("Progress.lean", "Wire.lean", "Codec.lean", "Main.lean")
HOST_FILES = (
    "authority.py", "certificate.py", "broker.py", "example.py", "trace.py",
    "evidence.py", "worker.py", "__main__.py", "binding.py", "intake.py", "effects.py", "adapter.py",
)


def source_inventory():
    return {
        **{name: sha((HERE / name).read_bytes()) for name in (*NATIVE_FILES, *HOST_FILES, *SPEC_FILES)},
        "formal/PCSActionShield.lean": sha((ROOT / "formal/PCSActionShield.lean").read_bytes()),
    }


@dataclass(frozen=True)
class SourceBinding:
    native: tuple[tuple[str, bytes], ...]
    host: tuple[tuple[str, str], ...]
    model_sha256: str
    certificate_sha256: str

    @classmethod
    def capture(cls, model_raw: bytes, cert_raw: bytes):
        native = (
            ("PCSActionShield.lean", (ROOT / "formal/PCSActionShield.lean").read_bytes()),
            *((name, (HERE / name).read_bytes()) for name in NATIVE_FILES),
            ("Data.lean", literal_source(model_raw, cert_raw)),
        )
        return cls(native, tuple((n, sha((HERE / n).read_bytes())) for n in (*HOST_FILES, *SPEC_FILES)),
                   sha(model_raw), sha(cert_raw))

    @property
    def source_id(self):
        return sha(encode({"native": {n: sha(raw) for n, raw in self.native}, "host": dict(self.host)}))

    def seed(self, pre_sanitized: bool):
        if type(pre_sanitized) is not bool:
            raise ValueError("exact fixture mode required")
        return sha(encode(dict(model=self.model_sha256, certificate=self.certificate_sha256,
                               source=self.source_id, pre_sanitized=pre_sanitized)))
