"""Read-only loopback server over a captured asset snapshot; no verification API."""
from __future__ import annotations
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[2]
ASSET_ROOT=ROOT/'research/flux_detective_v1'
ASSETS=('index.html','style.css','app.mjs','engine.mjs','forge.mjs','inspector.mjs','inspector-ui.mjs','inspector-worker.mjs','README.md')
CSP="default-src 'self'; script-src 'self'; style-src 'self'; worker-src 'self'; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"


def create_server(port=8080, *, asset_root=ASSET_ROOT):
    if type(port) is not int or not 0<=port<=65535:raise ValueError('Port must be an integer in 0..65535')
    captured={name:(Path(asset_root)/name).read_bytes() for name in ASSETS}
    try:commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,timeout=5).strip()
    except (OSError,subprocess.SubprocessError):commit=None
    manifest=dict(format='pcs-local-lab-assets-v1',commit_hint=commit,
      files={n:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in captured.items()},
      kernel_checked=False,pcs_authority=False)
    captured['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):self.respond(False)
        def do_HEAD(self):self.respond(True)
        def respond(self,head):
            allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
            if self.headers.get('Host','').lower() not in allowed:self.send_error(403,'Loopback Host required');return
            if not self.path.startswith('/') or self.path.startswith('//'):self.send_error(404);return
            path=urlsplit(self.path).path;name='index.html' if path=='/' else path[1:]
            if name not in captured:self.send_error(404);return
            raw=captured[name];mime='text/javascript' if name.endswith('.mjs') else 'text/css' if name.endswith('.css') else 'text/html' if name.endswith('.html') else 'application/json' if name.endswith('.json') else 'text/plain'
            self.send_response(200);self.send_header('Content-Type',mime+'; charset=utf-8');self.send_header('Content-Length',str(len(raw)))
            for key,value in {'Content-Security-Policy':CSP,'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Cache-Control':'no-store','Cross-Origin-Resource-Policy':'same-origin'}.items():self.send_header(key,value)
            self.end_headers()
            if not head:self.wfile.write(raw)
        def do_POST(self):self.send_error(405,'Read-only static server')
        do_PUT=do_POST
        do_DELETE=do_POST
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)
