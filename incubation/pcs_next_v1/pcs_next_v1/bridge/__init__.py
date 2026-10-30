"""Read-only bridge to production PCS authority (subprocess preferred)."""

from .authority import AuthorityIdentity, resolve_authority, invoke_authority_help

__all__ = ["AuthorityIdentity", "resolve_authority", "invoke_authority_help"]
