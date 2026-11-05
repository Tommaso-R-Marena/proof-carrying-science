from pcs_causal.certificates.format import CausalCertificate, CertificateKind
from pcs_causal.certificates.verifier import verify_certificate
from pcs_causal.graphs.dag import CausalDAG


def test_backdoor_certificate_accept():
    g = CausalDAG.from_edges(["Z", "X", "Y"], [("Z", "X"), ("Z", "Y"), ("X", "Y")])
    cert = CausalCertificate(
        version="pcs-causal-cert-v1",
        kind=CertificateKind.BACKDOOR_IDENTIFICATION,
        claim="Z is valid backdoor set for X→Y",
        assumptions=["dag_correct", "sufficiency", "positivity"],
        graph=g.to_dict(),
        query={"treatment": "X", "outcome": "Y"},
        payload={"adjustment_set": ["Z"]},
        producer_pass=True,
    )
    # Even if producer_pass True for invalid, verifier recomputes — first valid case
    report = verify_certificate(cert)
    assert report.accepted


def test_forged_producer_pass_rejected():
    g = CausalDAG.from_edges(["Z", "X", "Y"], [("Z", "X"), ("Z", "Y"), ("X", "Y")])
    cert = CausalCertificate(
        version="pcs-causal-cert-v1",
        kind=CertificateKind.BACKDOOR_IDENTIFICATION,
        claim="empty is valid",
        assumptions=[],
        graph=g.to_dict(),
        query={"treatment": "X", "outcome": "Y"},
        payload={"adjustment_set": []},
        producer_pass=True,  # forged
    )
    report = verify_certificate(cert)
    assert not report.accepted


def test_unsupported_version_fail_closed():
    cert = CausalCertificate(
        version="nope",
        kind=CertificateKind.D_SEPARATION,
        claim="x",
        assumptions=[],
        graph={"nodes": ["A", "B"], "edges": []},
        query={"x": ["A"], "y": ["B"], "z": []},
        payload={"separated": True},
    )
    assert not verify_certificate(cert).accepted
