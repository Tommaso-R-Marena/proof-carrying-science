"""Private loopback upload/review UI. Uploaded source is data, never executed."""
from __future__ import annotations
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import threading
import zipfile
from research.scientific_intake_v1.intake import _regular, safe_name
from . import pipeline

MAX_UPLOAD = 32 * 1024 * 1024
PAGE = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Review a scientific project</title><style>body{font:18px system-ui;line-height:1.5;max-width:48rem;margin:2rem auto;padding:1rem}button,input{font:inherit}label{display:block;margin:1rem 0}button{padding:.6rem 1rem}#message{white-space:pre-wrap}</style><h1>Review a scientific project</h1><p>Upload a ZIP containing a paper, equations, data or analysis code. PCS proposes statements and links them to their sources so you can review what the files establish.</p><p>Checks support only their stated mathematical or computational scope. They do not establish scientific truth or biological validity. Uploaded code is never executed and your files are not used for training. Files stay in this local review folder.</p><form id="upload"><label>Project ZIP (up to 32 MiB)<input id="archive" type="file" accept=".zip,application/zip" required></label><label><input id="checks" type="checkbox"> I authorize the supported mathematical and computational checks.</label><p>Leave this unchecked to read and organize the project without running checks.</p><button id="review">Review project</button></form><p id="message" role="status" aria-live="polite"></p><p><a id="result" hidden>Open project review</a></p><script nonce="NONCE">document.getElementById('upload').addEventListener('submit',async e=>{e.preventDefault();const f=document.getElementById('archive').files[0],m=document.getElementById('message'),b=document.getElementById('review'),a=document.getElementById('result');a.hidden=true;if(!f||f.size>33554432){m.textContent='Choose a ZIP no larger than 32 MiB.';return}b.disabled=true;m.textContent='Reading your project. Authorized checks may take longer.';try{const r=await fetch('/upload?check='+(document.getElementById('checks').checked?'1':'0'),{method:'POST',headers:{'Content-Type':'application/zip','X-PCS-Token':'TOKEN'},body:f}),d=await r.json();if(!r.ok)throw Error(d.error||'Review failed.');a.href=d.review_url;a.hidden=false;m.textContent='Review ready. Inspect the proposed meanings, source links and stated limits.'}catch(e){m.textContent=e.message}finally{b.disabled=false}});</script></html>'''


def make_server(output_root, port=0):
    """Create an unstarted server bound to 127.0.0.1 and a new private directory."""
    root = Path(output_root).absolute()
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError('review directory cannot have symlink ancestors')
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    for name in ('uploads', 'runs', 'cache'):
        (root / name).mkdir(mode=0o700)
    token, nonce, lock, runs = secrets.token_urlsafe(32), secrets.token_urlsafe(24), threading.Lock(), {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def setup(self):
            super().setup()
            self.connection.settimeout(15)

        def reply(self, status, raw, content_type='application/json', attachment=False):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'nonce-" + nonce + "'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            if attachment:
                self.send_header('Content-Disposition', 'attachment; filename="source.bin"')
            self.end_headers()
            self.wfile.write(raw)

        def error(self, status, message):
            self.reply(status, json.dumps({'error': message}).encode())

        def local(self):
            return self.headers.get_all('Host', []) == [self.server.url.removeprefix('http://')]

        def do_GET(self):
            if not self.local():
                return self.error(403, 'Local host required.')
            if self.path == '/':
                return self.reply(200, PAGE.replace('NONCE', nonce).replace('TOKEN', token).encode(), 'text/html; charset=utf-8')
            parts = self.path.split('/', 3)
            if len(parts) != 4 or parts[1] != 'runs' or parts[2] not in runs:
                return self.error(404, 'Review file not found.')
            folder, files = runs[parts[2]]
            name = parts[3]
            if name not in files:
                return self.error(404, 'Review file not found.')
            target = folder / name
            try:
                if any(p.is_symlink() for p in (target, *target.parents) if p.is_relative_to(root)):
                    raise ValueError('symlink')
                raw = _regular(target, 64 * 1024 * 1024)
                if hashlib.sha256(raw).hexdigest() != files[name]:
                    raise ValueError('changed evidence')
            except (OSError, ValueError):
                return self.error(404, 'Review file unavailable or changed.')
            is_source = name.startswith('intake/objects/')
            kind = 'application/octet-stream' if is_source else 'text/html; charset=utf-8' if name.endswith('.html') else 'application/json'
            self.reply(200, raw, kind, attachment=is_source)

        def do_POST(self):
            if not self.local() or self.headers.get_all('Origin', []) != [self.server.url]:
                return self.error(403, 'Local page origin required.')
            supplied = self.headers.get_all('X-PCS-Token', [])
            if len(supplied) != 1 or not secrets.compare_digest(supplied[0].encode(), token.encode()):
                return self.error(403, 'Review token required.')
            if self.path not in ('/upload?check=0', '/upload?check=1'):
                return self.error(404, 'Upload route not found.')
            lengths = self.headers.get_all('Content-Length', [])
            if self.headers.get('Transfer-Encoding') or len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit():
                return self.error(400, 'A single upload length is required.')
            if len(lengths[0]) > 8:
                return self.error(413, 'ZIP exceeds the 32 MiB limit.')
            size = int(lengths[0])
            if not 0 < size <= MAX_UPLOAD:
                return self.error(413, 'ZIP must be between 1 byte and 32 MiB.')
            if self.headers.get_all('Content-Type', []) != ['application/zip']:
                return self.error(415, 'Upload a ZIP file.')
            if not lock.acquire(blocking=False):
                return self.error(409, 'A project is already being reviewed. Try again when it finishes.')
            upload = root / 'uploads' / (secrets.token_hex(16) + '.zip')
            try:
                raw = self.rfile.read(size)
                if len(raw) != size:
                    raise ValueError('incomplete upload')
                with upload.open('xb') as stream:
                    os.chmod(upload, 0o600)
                    stream.write(raw)
                identity = secrets.token_hex(16)
                folder = root / 'runs' / identity
                summary = pipeline.run(upload, folder, check=self.path.endswith('=1'), cache_dir=root / 'cache')
                manifest_raw = _regular(folder / 'manifest.json', 2 * 1024 * 1024)
                files = json.loads(manifest_raw)['files']
                if len(files) > 320:
                    raise ValueError('manifest bound')
                for name in files:
                    safe_name(name)
                files['manifest.json'] = hashlib.sha256(manifest_raw).hexdigest()
                runs[identity] = (folder, files)
                self.reply(200, json.dumps({'review_url': '/runs/' + identity + '/review.html', 'summary': summary}).encode())
            except (ValueError, OSError, zipfile.BadZipFile):
                self.error(400, 'Could not review this ZIP. Check its files and try again.')
            except Exception:
                self.error(500, 'Review could not finish. No result was published.')
            finally:
                upload.unlink(missing_ok=True)
                lock.release()

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    server.token, server.url = token, 'http://127.0.0.1:' + str(server.server_port)
    server.output_root, server.job_lock = root, lock
    return server


def serve(output_root, port=0):
    server = make_server(output_root, port)
    print(server.url, flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
