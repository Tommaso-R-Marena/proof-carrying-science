"""Real loopback HTTP integration; no final corpus sources or fake verdicts."""
from __future__ import annotations

import hashlib
import http.client
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
import zipfile

from . import web


def archive(parts):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as zipped:
        for name, raw in parts.items():
            zipped.writestr(name, raw)
    return stream.getvalue()


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(dir='/dev/shm')
        cls.directory = Path(cls.temporary.name)
        cls.server = web.make_server(cls.directory / 'private-review')
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.temporary.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=15)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def upload_headers(self, **updates):
        return {'Origin': self.server.url, 'X-PCS-Token': self.server.token,
                'Content-Type': 'application/zip', **updates}

    def test_loopback_page_explains_authorization_and_limits(self):
        self.assertEqual(self.server.server_address[0], '127.0.0.1')
        self.assertEqual(self.server.output_root.stat().st_mode & 0o077, 0)
        status, headers, body = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn(b'Review project', body)
        self.assertIn(b'not establish scientific truth', body)
        self.assertIn(b'Uploaded code is never executed', body)
        self.assertIn(b'type="checkbox"', body)
        self.assertNotIn(b'type="checkbox" checked', body)
        self.assertIn(self.server.token.encode(), body)
        self.assertIn("default-src 'none'", headers['Content-Security-Policy'])
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        self.assertNotIn('Access-Control-Allow-Origin', headers)

    def test_auth_host_and_origin_fail_closed(self):
        body = archive({'notes.txt': 'A source to review.'})
        cases = [
            self.upload_headers(**{'X-PCS-Token': 'wrong'}),
            self.upload_headers(**{'X-PCS-Token': '\u00ff'}),
            {'Origin': self.server.url, 'Content-Type': 'application/zip'},
            self.upload_headers(Origin='https://other.example'),
            self.upload_headers(Host='other.example'),
            {'X-PCS-Token': self.server.token, 'Content-Type': 'application/zip'},
        ]
        for headers in cases:
            with self.subTest(headers=list(headers)):
                self.assertEqual(self.request('POST', '/upload?check=0', body, headers)[0], 403)
        self.assertEqual(self.request('GET', '/', headers={'Host': 'other.example'})[0], 403)

    def test_metadata_limits_and_routes_before_body_read(self):
        for length in (str(web.MAX_UPLOAD + 1), '9' * 10000):
            status, _, _ = self.request('POST', '/upload?check=0', headers=self.upload_headers(**{'Content-Length': length}))
            self.assertEqual(status, 413)
        for length in ('-1', 'not-a-number', '\u00b2'):
            status, _, _ = self.request('POST', '/upload?check=0', headers=self.upload_headers(**{'Content-Length': length}))
            self.assertEqual(status, 400)
        self.assertEqual(self.request('POST', '/upload?check=0', b'123', self.upload_headers(**{'Transfer-Encoding': 'chunked'}))[0], 400)
        self.assertEqual(self.request('POST', '/upload?check=0', b'123', self.upload_headers(**{'Content-Type': 'text/plain'}))[0], 415)
        self.assertEqual(self.request('POST', '/upload?check=true', b'123', self.upload_headers())[0], 404)

    def test_one_review_at_a_time(self):
        self.server.job_lock.acquire()
        try:
            result = self.request('POST', '/upload?check=0', b'zip', self.upload_headers())
            self.assertEqual(result[0], 409)
        finally:
            self.server.job_lock.release()

    def test_real_upload_review_manifest_sources_and_no_code_execution(self):
        sentinel = self.directory / 'uploaded-code-executed'
        raw_source = b'<script>window.PCS_UPLOAD_EXECUTED=true</script>'
        uploaded_code = ('from pathlib import Path\nPath(' + repr(str(sentinel)) + ').write_text("executed")\n').encode()
        filename = '<script>alert(1)</script>.txt'
        body = archive({'notes.txt': 'Scientific meaning requires review.', 'analysis.py': uploaded_code,
                        'source.html': raw_source, filename: 'An attributed observation.'})
        headers = self.upload_headers(**{'Content-Disposition': 'attachment; filename="../../caller-output.zip"'})
        status, _, raw = self.request('POST', '/upload?check=0', body, headers)
        self.assertEqual(status, 200, raw)
        result = json.loads(raw)
        self.assertFalse(result['summary']['authorized_checks'])
        self.assertFalse(result['summary']['authority'])
        self.assertEqual(sum(result['summary']['checks'].values()), 0)
        self.assertFalse(sentinel.exists())
        self.assertEqual(list((self.server.output_root / 'uploads').iterdir()), [])
        self.assertFalse((self.directory / 'caller-output.zip').exists())
        review_url = result['review_url']
        status, headers, page = self.request('GET', review_url)
        self.assertEqual(status, 200)
        self.assertIn('text/html', headers['Content-Type'])
        self.assertIn(b'No checks have run yet', page)
        prefix = review_url.removesuffix('review.html')
        status, _, manifest_raw = self.request('GET', prefix + 'manifest.json')
        self.assertEqual(status, 200)
        manifest = json.loads(manifest_raw)
        self.assertIn('review.html', manifest['files'])
        source_path = 'intake/objects/' + hashlib.sha256(raw_source).hexdigest()
        status, headers, served_source = self.request('GET', prefix + source_path)
        self.assertEqual(status, 200)
        self.assertEqual(served_source, raw_source)
        self.assertEqual(headers['Content-Type'], 'application/octet-stream')
        self.assertIn('attachment', headers['Content-Disposition'])
        status, _, base_review = self.request('GET', prefix + 'intake/review.html')
        self.assertEqual(status, 200)
        self.assertIn(b'&lt;script&gt;alert(1)&lt;/script&gt;.txt', base_review)
        self.assertNotIn(filename.encode(), base_review)
        for suffix in ('../cache/host-key', '%2e%2e/cache/host-key', 'unknown.txt', 'review.html?x=1'):
            self.assertEqual(self.request('GET', prefix + suffix)[0], 404)
        folder = self.server.output_root / 'runs' / review_url.split('/')[2]
        private_extra = folder / 'unlisted.txt'
        private_extra.write_text('not in generated manifest')
        self.assertEqual(self.request('GET', prefix + 'unlisted.txt')[0], 404)
        source = folder / source_path
        source.unlink()
        source.symlink_to(self.directory / 'elsewhere.txt')
        self.assertEqual(self.request('GET', prefix + source_path)[0], 404)
        page_path = folder / 'review.html'
        page_path.write_text('<script>changed</script>')
        self.assertEqual(self.request('GET', review_url)[0], 404)

    def test_bad_zip_and_traversal_delegate_to_real_intake(self):
        for body in (b'not a zip', archive({'../escape.py': 'raise RuntimeError("never run")'})):
            status, _, raw = self.request('POST', '/upload?check=0', body, self.upload_headers())
            self.assertEqual(status, 400, raw)
        self.assertFalse((self.directory / 'escape.py').exists())
        self.assertEqual(list((self.server.output_root / 'uploads').iterdir()), [])

    def test_existing_or_symlink_review_root_rejected(self):
        with self.assertRaises(FileExistsError):
            web.make_server(self.server.output_root)
        link = self.directory / 'linked-parent'
        link.symlink_to(self.server.output_root, target_is_directory=True)
        with self.assertRaises(ValueError):
            web.make_server(link / 'new-root')


if __name__ == '__main__':
    unittest.main()
