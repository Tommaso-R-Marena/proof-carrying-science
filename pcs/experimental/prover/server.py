"""Credential-free loopback backend for the public Lean learning laboratory."""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import time
import uuid

from pcs.jsonio import strict_json_loads
from .cli import run
from .environment import LeanEnvironment, candidates, render_action
from .language import formalize, parse_lean, explain
from .ir import digest

PUBLIC_ORIGIN = "https://proof-carrying-science-site.marenatommaso.workers.dev"


def serve(models, public, port=8766):
    models = Path(models).resolve()
    public = Path(public).resolve()
    lock = threading.BoundedSemaphore(1)
    sessions = {}
    env = LeanEnvironment(timeout=30)

    class Handler(BaseHTTPRequestHandler):
        def allowed(self):
            host = self.headers.get("Host", "")
            if host not in {f"127.0.0.1:{port}", f"localhost:{port}"}: return False
            origin = self.headers.get("Origin")
            return origin is None or origin == PUBLIC_ORIGIN or origin in {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}

        def reply(self, code, value):
            raw = json.dumps(value).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            if self.allowed() and self.headers.get("Origin"):
                self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
                self.send_header("Vary", "Origin")
            self.end_headers(); self.wfile.write(raw)

        def do_OPTIONS(self):
            if not self.allowed(): return self.reply(403, {"error": "origin or host rejected"})
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", PUBLIC_ORIGIN))
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.end_headers()

        def do_GET(self):
            if not self.allowed(): return self.reply(403, {"error": "origin or host rejected"})
            if self.path == "/api/health":
                return self.reply(200, {"status": "ready", "lean": env.version, "mode": "local CPU", "pcs_authority": False})
            if self.path == "/api/models":
                return self.reply(200, json.loads((models / "registry.json").read_text()))
            allowed_files = {"/": "lean-learning-lab.html", "/lean-learning-lab": "lean-learning-lab.html",
                             "/lean-learning-lab.html": "lean-learning-lab.html", "/lean-learning-lab.css": "lean-learning-lab.css",
                             "/lean-learning-lab.mjs": "lean-learning-lab.mjs",
                             "/lean-learning/summary.json": "lean-learning/summary.json"}
            if self.path not in allowed_files: return self.reply(404, {"error": "not found"})
            p = public / allowed_files[self.path]
            raw = p.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", {".html": "text/html", ".css": "text/css", ".mjs": "application/javascript", ".json": "application/json"}[p.suffix])
            self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self' http://127.0.0.1:8766 http://localhost:8766; object-src 'none'; base-uri 'none'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers(); self.wfile.write(raw)

        def do_POST(self):
            if not self.allowed(): return self.reply(403, {"error": "origin or host rejected"})
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.reply(415, {"error": "JSON required"})
            if not lock.acquire(blocking=False): return self.reply(429, {"error": "checker busy; try again after the current request"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 1 <= length <= 16384: raise ValueError("request size outside bound")
                obj = strict_json_loads(self.rfile.read(length).decode())
                if type(obj) is not dict: raise ValueError("object required")
                if self.path == "/api/formalize" and set(obj) == {"statement"}:
                    result = formalize(obj["statement"])
                elif self.path == "/api/explain" and set(obj) == {"declaration"}:
                    ir = parse_lean(obj["declaration"])
                    result = {"explanation": explain(ir), "elaboration": env.observe(ir, [])}
                elif self.path == "/api/solve" and set(obj) == {"statement", "mode", "interpretation", "budget"}:
                    if obj["mode"] not in {"model", "symbolic"} or type(obj["budget"]) is not int or not 1 <= obj["budget"] <= 96:
                        raise ValueError("invalid model mode or budget")
                    result = run(obj["statement"], models if obj["mode"] == "model" else None, obj["budget"], obj["interpretation"])
                elif self.path == "/api/session" and set(obj) == {"statement", "interpretation"}:
                    for key in list(sessions):
                        if time.monotonic() - sessions[key]["time"] > 600: del sessions[key]
                    if len(sessions) >= 16: raise ValueError("session capacity reached")
                    formal = formalize(obj["statement"])
                    index = obj["interpretation"]
                    if type(index) is not int or not 0 <= index < len(formal["candidates"]): raise ValueError("select a valid interpretation")
                    goal = formal["candidates"][index]["ir"]
                    observed = env.observe(goal, [])
                    key = uuid.uuid4().hex
                    sessions[key] = {"goal": goal, "hash": digest(goal), "actions": [], "time": time.monotonic(), "history": []}
                    result = {"id": key, "goal_sha256": digest(goal), "state": observed["states"][-1], "actions": candidates(observed["states"][-1]), "status": "open"}
                elif self.path == "/api/step" and set(obj) == {"id", "action"}:
                    session = sessions.get(obj["id"])
                    if not session or time.monotonic() - session["time"] > 600: raise ValueError("session expired")
                    if digest(session["goal"]) != session["hash"]: raise ValueError("immutable goal changed")
                    action = obj["action"]
                    observed = env.observe(session["goal"], session["actions"])
                    available = candidates(observed["states"][-1])
                    if action not in available: raise ValueError("action is not available in this proof state")
                    path = session["actions"] + [action]
                    result = env.observe(session["goal"], path)
                    if result["status"] != "invalid": session["actions"] = path
                    session["history"].append({"action": action, "status": result["status"], "error": result["error"]})
                    receipt = env.verify(session["goal"], path) if result["status"] == "closed" else None
                    state = result["states"][-1] if result["status"] != "invalid" else observed["states"][-1]
                    result = {"status": "verified" if receipt else result["status"], "state": state,
                              "actions": candidates(state), "history": session["history"], "receipt": receipt}
                else: raise ValueError("unknown route or unexpected fields")
                self.reply(200, result)
            except (ValueError, RuntimeError, KeyError, TypeError) as ex:
                self.reply(422, {"status": "unresolved", "error": str(ex)[-4000:], "pcs_authority": False})
            finally: lock.release()

        def log_message(self, *_):
            pass  # Submitted mathematical text is not logged or uploaded.

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"PCS local Lean backend ready on port {port}; no external model service or donation.", flush=True)
    try: server.serve_forever()
    finally: server.server_close(); env.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--models", required=True)
    p.add_argument("--public", required=True)
    p.add_argument("--port", type=int, default=8766)
    args = p.parse_args()
    serve(args.models, args.public, args.port)


if __name__ == "__main__": main()
