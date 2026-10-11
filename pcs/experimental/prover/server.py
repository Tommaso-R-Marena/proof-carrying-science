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
from .induction_language import formalize, parse_lean, explain
from .induction_ir import digest

PUBLIC_ORIGIN = "https://proof-carrying-science-site.marenatommaso.workers.dev"


def serve(models, public, port=8766, reuse_models=None, abstraction_models=None):
    models = Path(models).resolve()
    public = Path(public).resolve()
    lock = threading.BoundedSemaphore(1)
    sessions = {}
    env = LeanEnvironment(timeout=30)
    reuse_env = None
    abstraction_env=None
    if abstraction_models is not None:
        from .abstraction_environment import AbstractionEnvironment
        abstraction_models=Path(abstraction_models).resolve()
        registry=json.loads((abstraction_models/"registry.json").read_text())
        library=json.loads((abstraction_models/"library.json").read_text())
        if registry.get("environment")!="AbstractionEnvironment" or digest(library)!=registry["library_sha256"]:raise ValueError("abstraction registry mismatch")
        abstraction_env=AbstractionEnvironment(library,timeout=30)
    if reuse_models is not None:
        from .library import LibraryEnvironment
        reuse_models = Path(reuse_models).resolve()
        registry = json.loads((reuse_models / "registry.json").read_text())
        library = json.loads((reuse_models / "library.json").read_text())
        if digest(library) != registry["library_sha256"]: raise ValueError("checked library registry mismatch")
        if registry.get("environment") == "AbstractionEnvironment":
            from .abstraction_environment import AbstractionEnvironment
            reuse_env = AbstractionEnvironment(library, timeout=30)
        else: reuse_env = LibraryEnvironment(library, timeout=30)

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
                return self.reply(200, {"status": "ready", "lean": env.version, "mode": "local CPU", "pcs_authority": False,
                    "abstraction_configured":abstraction_env is not None,
                    "checked_reuse": reuse_env is not None, "checked_lemmas": reuse_env.catalog if reuse_env else []})
            if self.path == "/api/models":
                return self.reply(200, json.loads((models / "registry.json").read_text()))
            allowed_files = {"/": "lean-learning-lab.html", "/lean-learning-lab": "lean-learning-lab.html",
                             "/lean-learning-lab.html": "lean-learning-lab.html", "/lean-learning-lab.css": "lean-learning-lab.css",
                             "/lean-learning-lab.mjs": "lean-learning-lab.mjs",
                             "/lean-learning/summary.json": "lean-learning/summary.json",
                             "/checked-reuse/summary.json": "checked-reuse/summary.json",
                             "/checked-reuse/catalog.json": "checked-reuse/catalog.json",
                             "/checked-reuse/refinement-summary.json": "checked-reuse/refinement-summary.json",
                             "/checked-reuse/library.json": "checked-reuse/library.json",
                             "/checked-reuse/REPORT.md": "checked-reuse/REPORT.md",
                             "/checked-reuse/transfer-proof.lean": "checked-reuse/transfer-proof.lean"}
            for name in ["bridge-builder.html", "bridge-builder.css", "bridge-builder.mjs", "bridge-builder-core.mjs", "bridge-builder-catalog.json", "bridge-builder-catalog.mjs"]:
                allowed_files["/"+name] = name
            for name in ["nat_three_edge_chain", "int_three_edge_chain", "nat_order_cycle", "triple_function_congruence",
                         "two_rule_function_chain", "three_part_nat_witness"]:
                allowed_files[f"/checked-reuse/{name}.lean"] = f"checked-reuse/{name}.lean"
            if self.path not in allowed_files: return self.reply(404, {"error": "not found"})
            p = public / allowed_files[self.path]
            raw = p.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", {".html": "text/html", ".css": "text/css", ".mjs": "application/javascript", ".json": "application/json", ".md": "text/plain", ".lean": "text/plain"}[p.suffix])
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
                    if obj["mode"] not in {"model", "symbolic", "reuse-model", "reuse-symbolic", "abstraction-model", "abstraction-symbolic"} or type(obj["budget"]) is not int or not 1 <= obj["budget"] <= 96:
                        raise ValueError("invalid model mode or budget")
                    if obj["mode"]=="abstraction-model":
                        if abstraction_env is None:raise ValueError("abstraction model not configured")
                        result=run(obj["statement"],abstraction_models,obj["budget"],obj["interpretation"],prepared_env=abstraction_env)
                    elif obj["mode"]=="abstraction-symbolic":
                        result=run(obj["statement"],None,obj["budget"],obj["interpretation"],domain="induction")
                    elif obj["mode"].startswith("reuse-"):
                        if reuse_env is None: raise ValueError("checked reuse backend not configured")
                        if obj["mode"] == "reuse-model":
                            result = run(obj["statement"], reuse_models, obj["budget"], obj["interpretation"], prepared_env=reuse_env)
                        else:
                            from .library import reuse_priority
                            formal = formalize(obj["statement"])
                            index = obj["interpretation"]
                            if formal["status"] != "supported" and index is None: raise ValueError("select a supported interpretation")
                            index = 0 if index is None else index
                            if type(index) is not int or not 0 <= index < len(formal["candidates"]): raise ValueError("select a valid interpretation")
                            goal = formal["candidates"][index]["ir"]
                            from .environment import search
                            solved = search(reuse_env, goal, reuse_priority, budget=obj["budget"], beam=4)
                            result = {"status": solved["status"], "search": solved, "formalization": formal,
                                      "explanation": explain(goal), "model": "symbolic-reuse", "pcs_authority": False}
                    else:
                        result = run(obj["statement"], models if obj["mode"] == "model" else None, obj["budget"], obj["interpretation"])
                elif self.path == "/api/session" and set(obj) in ({"statement", "interpretation"}, {"statement", "interpretation", "reuse"}, {"statement", "interpretation", "reuse", "abstraction"}):
                    for key in list(sessions):
                        if time.monotonic() - sessions[key]["time"] > 600: del sessions[key]
                    if len(sessions) >= 16: raise ValueError("session capacity reached")
                    formal = formalize(obj["statement"])
                    index = obj["interpretation"]
                    if type(index) is not int or not 0 <= index < len(formal["candidates"]): raise ValueError("select a valid interpretation")
                    goal = formal["candidates"][index]["ir"]
                    use_reuse = obj.get("reuse", False)
                    if type(use_reuse) is not bool or (use_reuse and reuse_env is None): raise ValueError("invalid checked reuse session")
                    use_abstraction = obj.get("abstraction", False)
                    if type(use_abstraction) is not bool or (use_abstraction and (use_reuse or abstraction_env is None)): raise ValueError("invalid abstraction session")
                    proof_env = abstraction_env if use_abstraction else reuse_env if use_reuse else env
                    observed = proof_env.observe(goal, [])
                    key = uuid.uuid4().hex
                    sessions[key] = {"goal": goal, "hash": digest(goal), "actions": [], "time": time.monotonic(), "history": [], "reuse": use_reuse, "abstraction": use_abstraction}
                    result = {"id": key, "goal_sha256": digest(goal), "state": observed["states"][-1], "actions": proof_env.candidates(observed["states"][-1]), "status": "open", "checked_lemmas": getattr(proof_env, "catalog", [])}
                elif self.path == "/api/step" and set(obj) == {"id", "action"}:
                    session = sessions.get(obj["id"])
                    if not session or time.monotonic() - session["time"] > 600: raise ValueError("session expired")
                    if digest(session["goal"]) != session["hash"]: raise ValueError("immutable goal changed")
                    action = obj["action"]
                    proof_env = abstraction_env if session["abstraction"] else reuse_env if session["reuse"] else env
                    observed = proof_env.observe(session["goal"], session["actions"])
                    available = proof_env.candidates(observed["states"][-1])
                    if action not in available: raise ValueError("action is not available in this proof state")
                    path = session["actions"] + [action]
                    result = proof_env.observe(session["goal"], path)
                    if result["status"] != "invalid": session["actions"] = path
                    session["history"].append({"action": action, "status": result["status"], "error": result["error"]})
                    receipt = proof_env.verify(session["goal"], path) if result["status"] == "closed" else None
                    state = result["states"][-1] if result["status"] != "invalid" else observed["states"][-1]
                    result = {"status": "verified" if receipt else result["status"], "state": state,
                              "actions": proof_env.candidates(state), "history": session["history"], "receipt": receipt}
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
    finally:
        server.server_close(); env.close()
        if reuse_env is not None: reuse_env.close()
        if abstraction_env is not None:abstraction_env.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--models", required=True)
    p.add_argument("--public", required=True)
    p.add_argument("--port", type=int, default=8766)
    p.add_argument("--reuse-models", help="Receiver-selected checked reuse experiment directory")
    p.add_argument("--abstraction-models", help="Receiver-selected experimental grounded induction registry")
    args = p.parse_args()
    serve(args.models, args.public, args.port, args.reuse_models,args.abstraction_models)


if __name__ == "__main__": main()
