"""Nonce-fresh receiver-pinned witness client; no self-trust of response keys."""
from __future__ import annotations

import os
import ssl
import urllib.error
import urllib.parse
import urllib.request

from research.scientific_history_v1.receiver import checker_identity
from .protocol import (PROTOCOL, Rejected, canonical, parse, verify, MAX_REQUEST,
                       MAX_RESPONSE, root_id)


class WitnessClient:
    def __init__(self, url, root, config, witness_public_key: bytes, *, timeout=90, ca_file=None):
        parsed = urllib.parse.urlparse(url)
        if (parsed.scheme not in {"http", "https"} or parsed.path not in {"", "/"}
                or parsed.query or parsed.fragment or parsed.username or parsed.password
                or (parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"})
                or type(witness_public_key) is not bytes or len(witness_public_key) != 32
                or root.checker != checker_identity(config)
                or type(timeout) not in {int, float} or not 0 < timeout <= 180):
            raise Rejected("Pinned bootstrap and authenticated remote transport required")
        self._url, self._root, self._config, self._public_key = url.rstrip("/"), root, config, witness_public_key
        self._timeout = timeout
        self._context = ssl.create_default_context(cafile=ca_file) if parsed.scheme == "https" else None

    @property
    def root(self): return self._root

    @property
    def config(self): return self._config

    @property
    def witness_public_key(self): return self._public_key

    def _call(self, action, **fields):
        nonce = os.urandom(32)
        request = {"protocol": PROTOCOL, "action": action, "nonce": nonce.hex(), **fields}
        raw = canonical(request)
        if len(raw) > MAX_REQUEST:
            raise Rejected("Witness request too large")
        req = urllib.request.Request(self._url + "/rpc", data=raw, method="POST",
                                     headers={"Content-Type": "application/json"})
        # Explicit no-redirect handler prevents silently changing transport/origin.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl): return None
        handlers = [NoRedirect()]
        if self._context is None:
            handlers.append(urllib.request.ProxyHandler({}))  # Loopback only, never remote bypass.
        if self._context is not None:
            handlers.append(urllib.request.HTTPSHandler(context=self._context))
        opener = urllib.request.build_opener(*handlers)
        try:
            with opener.open(req, timeout=self._timeout) as response:
                lengths = response.headers.get_all("Content-Length", [])
                length = lengths[0] if len(lengths) == 1 else None
                if length is None or not length.isascii() or not length.isdigit() or int(length) > MAX_RESPONSE:
                    raise Rejected("Missing/bounded response length required")
                body = response.read(int(length) + 1)
                if len(body) != int(length):
                    raise Rejected("Truncated witness response")
                envelope = parse(body)
        except (OSError, urllib.error.URLError) as exc:
            raise Rejected("Witness unavailable or transport failed") from exc
        return verify(envelope, self._root, self._public_key,
                      kind="response:" + action, nonce=nonce)

    def checkpoint(self): return self._call("checkpoint")
    def export(self): return self._call("export")
    def prepare(self, intent: bytes):
        if type(intent) is not bytes: raise Rejected("Immutable intent bytes required")
        return self._call("prepare", intent=intent.hex())
    def finalize(self, intent_sha256: str): return self._call("finalize", intent_sha256=intent_sha256)


class DirectWitnessClient:
    """Same-host functional adapter; explicitly not independent administration.

    Checkpoint/export perform receiver-pinned signature/nonce verification;
    prepare/finalize return the store's signed permanent receipt directly. Useful
    for storage/crash tests, not a substitute for server/network tests.
    """
    def __init__(self, store):
        self.store, self.root, self.config, self.witness_public_key = store, store.root, store.config, store.public_key

    def checkpoint(self):
        nonce = os.urandom(32)
        return verify(self.store.checkpoint(nonce), self.root, self.witness_public_key, kind="checkpoint", nonce=nonce)

    def export(self):
        nonce = os.urandom(32)
        return verify(self.store.export(nonce), self.root, self.witness_public_key, kind="export", nonce=nonce)

    def prepare(self, intent): return {"receipt": self.store.prepare(intent)}
    def finalize(self, intent_sha256): return {"receipt": self.store.finalize(intent_sha256)}
