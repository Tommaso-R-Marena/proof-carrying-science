"""CertNum: untrusted generators for certified scientific numerics.

Mathematical truth is defined by the Lean checker (and exact rational
semantics mirrored here for differential testing). Generators may be buggy;
invalid certificates must be rejected by the checker.
"""

__version__ = "0.1.0"
__cert_format_version__ = "certnum-cert-v1"

from certnum.interval.interval import Interval, EnclStatus, Enclosure

__all__ = ["Interval", "EnclStatus", "Enclosure", "__version__", "__cert_format_version__"]
