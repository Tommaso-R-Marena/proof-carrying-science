"""ClaimCheck v1.1: a semantic-reliability layer over the frozen ClaimCheck v1 pipeline.

Research sidecar.  No PCS v0.6 production authority.  v1.1 changes no v1 file and does not change
the Lean checker: every mathematical result still comes from the v1 kernel path.  The layer added
here can only make the outward verdict about a paper MORE conservative than v1's result.
"""
VERSION = "pcs-claimcheck-v1.1"
POLICY_ID = "pcs-claimcheck-semantic-policy-v1.1"
AUTHORITY = "RESEARCH_ONLY_NOT_PCS_V06_AUTHORITY"
