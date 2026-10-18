from pcca import CERT_FORMAT

SUPPORTED_KINDS = frozenset(
    {
        "conservation_law",
        "trajectory_conservation",
        "conservation_refutation",
    }
)

__all__ = ["CERT_FORMAT", "SUPPORTED_KINDS"]
