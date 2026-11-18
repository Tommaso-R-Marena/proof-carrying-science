"""Pinned local GGUF inference for assurance-mirage (higher call budget than firewall lab)."""
from __future__ import annotations

import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request

from research.local_weights_v1.runtime import (
    PINS,
    check_runtime,
    extract,
    request_body,
    resource,
    sealed_snapshot,
)

F_ADD_SEALS = 1033
F_GET_SEALS = 1034
REQUIRED_SEALS = 1 | 2 | 4 | 8


def _digest(b: bytes) -> str:
    return sha256(b).hexdigest()


class MirageLocalModel:
    """Same sealed-weight localhost server as local_weights_v1, budget 160 calls."""

    def __init__(self, folder: Path, model: str, out: Path, *, max_calls: int = 160):
        self.folder = Path(folder)
        self.model = model
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=False)
        self.max_calls = max_calls
        self.calls = 0
        self.process = None
        self.fd = None
        self.log = None
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        root = check_runtime(self.folder)
        a = resource(model)
        try:
            self.fd = sealed_snapshot(self.folder / a["name"], size=a["size"], sha256=a["sha256"])
            with socket.socket() as s:
                s.bind(("127.0.0.1", 0))
                self.port = s.getsockname()[1]
            command = [
                str(root / "llama-server"),
                "-m",
                "/proc/self/fd/" + str(self.fd),
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
                "--threads",
                "2",
                "--threads-batch",
                "2",
                "--ctx-size",
                "4096",
                "--parallel",
                "1",
                "--n-gpu-layers",
                "0",
                "--offline",
                "--reasoning",
                "off",
                "--alias",
                model,
                "--no-webui",
            ]
            self.log = (self.out / "server.log").open("wb")
            self.process = subprocess.Popen(
                command,
                pass_fds=(self.fd,),
                stdout=self.log,
                stderr=subprocess.STDOUT,
                env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "OMP_NUM_THREADS": "2"},
            )
            deadline = time.monotonic() + 90
            while True:
                if self.process.poll() is not None:
                    raise ValueError("Local weight engine exited; see server.log")
                try:
                    if self.http("/health")["status"] == "ok":
                        break
                except OSError:
                    pass
                if time.monotonic() > deadline:
                    raise ValueError("Local engine failed readiness")
                time.sleep(0.1)
            check_runtime(self.folder)
            maps = Path("/proc/" + str(self.process.pid) + "/maps").read_text()
            mappings = [s for s in maps.splitlines() if "memfd:pcs-local-model-weights" in s]
            if not mappings:
                raise ValueError("Expected sealed GGUF memory mapping absent")
            self.binding = dict(
                model=model,
                weights=a,
                weight_snapshot_sha256=a["sha256"],
                snapshot_bytes=a["size"],
                seals=fcntl.fcntl(self.fd, F_GET_SEALS),
                runtime_release=PINS["runtime_release"],
                runtime_commit=PINS["runtime_commit"],
                local_cpu=True,
                gpu_layers=0,
                remote_model_api=False,
                max_calls=self.max_calls,
                production_authority=False,
                weight_mappings=mappings,
                command=command,
            )
            (self.out / "binding.json").write_text(json.dumps(self.binding, indent=2) + "\n")
        except BaseException:
            self.close()
            raise

    def http(self, path, body=None):
        raw = None if body is None else json.dumps(body, separators=(",", ":")).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:" + str(self.port) + path,
            data=raw,
            headers={"Content-Type": "application/json"},
        )
        with self.opener.open(req, timeout=180) as r:
            value = r.read(1024 * 1024 + 1)
            if len(value) > 1024 * 1024 or r.status != 200:
                raise ValueError("Bounded successful local response required")
        return json.loads(value) if body is None else value

    def complete(self, model, messages):
        if model != self.model or self.calls >= self.max_calls or self.process.poll() is not None:
            raise ValueError("Fixed live local model and request budget required")
        if fcntl.fcntl(self.fd, F_GET_SEALS) & REQUIRED_SEALS != REQUIRED_SEALS:
            raise ValueError("Sealed weights unavailable")
        body = request_body(model, messages)
        raw = json.dumps(body, separators=(",", ":")).encode()
        if len(raw) > 32768:
            raise ValueError("Prompt budget exceeded")
        i = self.calls
        self.calls += 1
        folder = self.out / f"call-{i:03d}"
        folder.mkdir()
        (folder / "request.json").write_bytes(raw)
        start = time.monotonic()
        response = self.http("/v1/chat/completions", body)
        (folder / "response.json").write_bytes(response)
        provenance = dict(
            call=i,
            model=model,
            weight_sha256=resource(model)["sha256"],
            runtime_commit=PINS["runtime_commit"],
            request_sha256=_digest(raw),
            response_sha256=_digest(response),
            seconds=round(time.monotonic() - start, 6),
            usage=json.loads(response).get("usage"),
            remote_model_api=False,
        )
        (folder / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
        return extract(response, model), provenance

    def close(self):
        try:
            if self.process is not None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=10)
        finally:
            if self.log is not None:
                self.log.close()
                self.log = None
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
