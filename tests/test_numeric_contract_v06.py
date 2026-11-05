from __future__ import annotations

import math

import pytest

from pcs.numeric_contract_v06 import (
    V06NumericContractError,
    canonical_nonnegative_number_text_v06,
    normalize_certificate_metadata_scalar_v06,
)


def test_nonintegral_contract_numbers_have_unique_string_wire_form():
    assert canonical_nonnegative_number_text_v06(1e-9, label="rel_tol") == "1e-9"
    assert canonical_nonnegative_number_text_v06(1e-12, label="abs_tol") == "1e-12"
    assert canonical_nonnegative_number_text_v06(0.5, label="rel_tol") == "0.5"
    assert canonical_nonnegative_number_text_v06(0, label="abs_tol") == "0"
    assert canonical_nonnegative_number_text_v06("1e-9", label="rel_tol") == "1e-9"


@pytest.mark.parametrize(
    "value",
    ["1.0e-09", "01", "-0", -1, -0.5, math.inf, -math.inf, math.nan, True, None],
)
def test_noncanonical_or_invalid_contract_numbers_fail_closed(value):
    with pytest.raises(V06NumericContractError):
        canonical_nonnegative_number_text_v06(value, label="tolerance")


def test_certificate_metadata_rejects_nonintegral_json_numbers():
    assert normalize_certificate_metadata_scalar_v06(4, label="m") == 4
    assert normalize_certificate_metadata_scalar_v06(4.0, label="m") == 4
    assert normalize_certificate_metadata_scalar_v06("0.98", label="m") == "0.98"
    with pytest.raises(V06NumericContractError, match="non-integral"):
        normalize_certificate_metadata_scalar_v06(0.98, label="m")
    with pytest.raises(V06NumericContractError, match="safe-integer"):
        normalize_certificate_metadata_scalar_v06(2**53 + 1, label="m")
