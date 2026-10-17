from pcs_next_v1.trust.crypto import generate_keypair, sign_bytes, verify_bytes, fingerprint_public_der
from pcs_next_v1.core.errors import PcsNextError
import pytest

def test_sign_verify_and_mutate():
    priv, pub, fp = generate_keypair()
    msg = b"hello"
    sig = sign_bytes(priv, msg)
    verify_bytes(pub, msg, sig)
    assert fingerprint_public_der(pub) == fp
    with pytest.raises(PcsNextError):
        verify_bytes(pub, msg, bytes([sig[0] ^ 1]) + sig[1:])
