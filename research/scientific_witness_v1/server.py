"""Minimal bounded witness service. Loopback HTTP is local Profile A only.

Remote binds require operator TLS certificates. TLS authenticates transport;
receiver-pinned Ed25519 witness identity and nonce still authenticate statements.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import ssl
import stat
import socket
import sqlite3
from threading import Timer

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from research.scientific_receiver_v1.host import OperatorConfig
from .store import WitnessStore
from .protocol import (PROTOCOL, Rejected, MAX_REQUEST, MAX_RESPONSE, canonical,
                       parse, unhex, sign, root_from_json)

ACQUISITION_SECONDS = 5


def _shutdown(connection):
    try: connection.shutdown(socket.SHUT_RDWR)
    except OSError: pass


def dispatch(store, request):
    if type(request) is not dict or request.get("protocol") != PROTOCOL:
        raise Rejected("Wrong witness protocol")
    action = request.get("action")
    fields = {"checkpoint": set(), "export": set(), "prepare": {"intent"}, "finalize": {"intent_sha256"}}
    if type(action) is not str or action not in fields or set(request) != {"protocol", "action", "nonce"} | fields[action]:
        raise Rejected("Unknown action/fields")
    nonce = unhex(request["nonce"], length=32)
    if action == "checkpoint":
        payload = store.checkpoint(nonce)["statement"]["payload"]
    elif action == "export":
        payload = store.export(nonce)["statement"]["payload"]
    elif action == "prepare":
        payload = {"receipt": store.prepare(unhex(request["intent"]))}
    else:
        payload = {"receipt": store.finalize(request["intent_sha256"])}
    return sign(store.key, store.root, "response:" + action, payload, nonce)


def make_server(store, bind="127.0.0.1", port=0, *, cert=None, tls_key=None):
    if bind not in {"127.0.0.1", "localhost", "::1"} and not (cert and tls_key):
        raise Rejected("Nonloopback service requires authenticated TLS transport")
    if bool(cert) != bool(tls_key):
        raise Rejected("Both TLS certificate and private key required")
    context = None
    if cert:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(cert, tls_key)
    class BoundedHTTPServer(HTTPServer):
        def get_request(self):
            connection, address = super().get_request()
            if context is None: return connection, address
            # Do not wrap the listening socket: its accept() would perform an
            # unbounded handshake before Handler.setup can install a deadline.
            wrapped = context.wrap_socket(connection, server_side=True, do_handshake_on_connect=False)
            wrapped.settimeout(ACQUISITION_SECONDS)
            timer = Timer(ACQUISITION_SECONDS, _shutdown, (wrapped,));timer.daemon = True;timer.start()
            try:
                wrapped.do_handshake()
                return wrapped, address
            except BaseException:
                wrapped.close()
                raise
            finally: timer.cancel()
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"
        def setup(self):
            super().setup()
            self.connection.settimeout(ACQUISITION_SECONDS)
            # Absolute header+body deadline, not a resettable per-read timeout.
            self._acquisition = Timer(ACQUISITION_SECONDS, _shutdown, (self.connection,))
            self._acquisition.daemon = True;self._acquisition.start()
        def finish(self):
            self._acquisition.cancel()
            super().finish()
        def log_message(self, *_): pass
        def handle(self):
            try: super().handle()
            except (BrokenPipeError, ConnectionResetError, TimeoutError): pass
        def do_POST(self):
            try:
                lengths = self.headers.get_all("Content-Length", [])
                if (self.path != "/rpc" or self.headers.get("Transfer-Encoding") is not None
                        or len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit()
                        or int(lengths[0]) > MAX_REQUEST or self.headers.get("Content-Type") != "application/json"):
                    raise Rejected("Unsupported bounded request framing")
                count = int(lengths[0]);raw = self.rfile.read(count)
                if len(raw) != count: raise Rejected("Truncated request")
                self._acquisition.cancel()
                self.connection.settimeout(5)  # Bounded response send, science has its own host deadline.
                result = canonical(dispatch(store, parse(raw, MAX_REQUEST)))
                if len(result) > MAX_RESPONSE: raise Rejected("Witness response exceeds budget")
                self.send_response(200);self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(result)));self.end_headers();self.wfile.write(result)
            except (Rejected, ValueError, TypeError, KeyError, OSError, sqlite3.Error) as exc:
                raw = canonical({"error": type(exc).__name__, "accepted": False})
                try:
                    self.send_response(400);self.send_header("Content-Length", str(len(raw)))
                    self.end_headers();self.wfile.write(raw)
                except OSError: pass
    server = BoundedHTTPServer((bind, port), Handler)  # Serial bounded service, no unbounded request threads.
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("init", "serve"))
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--ready-file", type=Path)
    parser.add_argument("--cert");parser.add_argument("--tls-key")
    args = parser.parse_args()
    info = args.key.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_size != 32:
        raise Rejected("Witness key must be a regular operator-only 32-byte file")
    key = Ed25519PrivateKey.from_private_bytes(args.key.read_bytes())
    root = root_from_json(parse(args.root.read_bytes(), MAX_REQUEST))
    config = OperatorConfig.load(args.config)
    store = (WitnessStore.create if args.operation == "init" else WitnessStore)(args.db, root, config, key)
    if args.operation == "init": return
    server = make_server(store, args.bind, args.port, cert=args.cert, tls_key=args.tls_key)
    if args.ready_file:
        # Operator launch path only; never accepted from an RPC.
        with args.ready_file.open("x") as stream:
            stream.write(canonical({"port": server.server_port, "witness_key": store.public_key.hex(),
                                    "profile": "A:local-process"}).decode())
    try: server.serve_forever(poll_interval=.1)
    finally: server.server_close()


if __name__ == "__main__": main()
