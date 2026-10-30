"""Negative-only transport probes: no mathematical verifier or positive mock."""
from datetime import datetime, timedelta, timezone
import ipaddress
from pathlib import Path
import socket
import ssl
import tempfile
from threading import Thread
import time
import unittest
from unittest.mock import patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from .server import make_server


class TransportDeadlineTests(unittest.TestCase):
    def run_server(self, **kwargs):
        # object() has no authorization methods: all probes use unsupported GET
        # and cannot create even an apparent affirmative scientific response.
        server=make_server(object(),**kwargs)
        thread=Thread(target=server.serve_forever,kwargs={"poll_interval":.01},daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        return server

    def test_continuous_header_trickle_has_absolute_deadline(self):
        with patch("research.scientific_witness_v1.server.ACQUISITION_SECONDS",.3):
            server=self.run_server();first=socket.create_connection(server.server_address)
            self.addCleanup(first.close);first.sendall(b"GET / HTTP/1.0\r\n")
            def trickle():
                try:
                    for _ in range(20):first.sendall(b"X: a\r\n");time.sleep(.05)
                except OSError:pass
            Thread(target=trickle,daemon=True).start()
            second=socket.create_connection(server.server_address);self.addCleanup(second.close);second.settimeout(2)
            start=time.monotonic();second.sendall(b"GET / HTTP/1.0\r\n\r\n")
            self.assertIn(b"501",second.recv(4096));self.assertLess(time.monotonic()-start,1.5)

    def test_stalled_tls_handshake_has_deadline_and_valid_transport_recovers(self):
        with tempfile.TemporaryDirectory() as td, patch("research.scientific_witness_v1.server.ACQUISITION_SECONDS",.3):
            root=Path(td);private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
            name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,"localhost")]);now=datetime.now(timezone.utc)
            certificate=(x509.CertificateBuilder().subject_name(name).issuer_name(name)
                .public_key(private.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=1))
                .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),critical=False)
                .add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True).sign(private,hashes.SHA256()))
            cert=root/"cert.pem";key=root/"key.pem"
            cert.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
            key.write_bytes(private.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
            server=self.run_server(cert=str(cert),tls_key=str(key));stalled=socket.create_connection(server.server_address)
            self.addCleanup(stalled.close)
            context=ssl.create_default_context(cafile=str(cert));start=time.monotonic()
            with context.wrap_socket(socket.create_connection(server.server_address,timeout=2),server_hostname="127.0.0.1") as connection:
                connection.sendall(b"GET / HTTP/1.0\r\n\r\n");self.assertIn(b"501",connection.recv(4096))
            self.assertLess(time.monotonic()-start,1.5)


if __name__=="__main__":unittest.main(verbosity=2)
