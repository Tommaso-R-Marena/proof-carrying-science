from __future__ import annotations

import csv
import io
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any, Mapping

from ..jsonio import StrictJSONError, strict_json_loads


PKPD_RMSE_POLICY_FORMAT_V06 = "pcs-pkpd-rmse-policy-v1"
PKPD_RMSE_VALIDATOR_ID_V06 = "pcs-reference-pkpd-rmse-validator/0.1"


class V06PkpdRmseValidatorError(ValueError):
    pass


def _positive_decimal(value: Any, *, label: str) -> Decimal:
    if not isinstance(value, str) or not value:
        raise V06PkpdRmseValidatorError(
            f"{label} must be a non-empty decimal string"
        )
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise V06PkpdRmseValidatorError(
            f"{label} is not a valid decimal"
        ) from exc
    if not result.is_finite() or result <= 0:
        raise V06PkpdRmseValidatorError(
            f"{label} must be finite and positive"
        )
    return result


def _load_policy(raw: bytes) -> dict[str, Any]:
    try:
        value = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, StrictJSONError) as exc:
        raise V06PkpdRmseValidatorError(
            f"RMSE policy is not strict UTF-8 JSON: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise V06PkpdRmseValidatorError("RMSE policy root must be an object")

    expected = {
        "format",
        "time_column",
        "concentration_column",
        "effect_column",
        "concentration_rmse_max",
        "effect_rmse_max",
        "require_exact_time_alignment",
    }
    if set(value) != expected:
        raise V06PkpdRmseValidatorError(
            "RMSE policy has unexpected or missing fields"
        )
    if value.get("format") != PKPD_RMSE_POLICY_FORMAT_V06:
        raise V06PkpdRmseValidatorError("unsupported RMSE policy format")
    for key in ("time_column", "concentration_column", "effect_column"):
        if not isinstance(value.get(key), str) or not value[key]:
            raise V06PkpdRmseValidatorError(
                f"RMSE policy {key} must be a non-empty string"
            )
    if value.get("require_exact_time_alignment") is not True:
        raise V06PkpdRmseValidatorError(
            "reference RMSE validator requires exact time alignment"
        )
    _positive_decimal(
        value["concentration_rmse_max"],
        label="concentration_rmse_max",
    )
    _positive_decimal(
        value["effect_rmse_max"],
        label="effect_rmse_max",
    )
    return value


def _csv_rows(
    raw: bytes,
    *,
    columns: tuple[str, str, str],
    label: str,
) -> list[dict[str, Decimal]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise V06PkpdRmseValidatorError(
            f"{label} is not UTF-8"
        ) from exc
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""))
        if reader.fieldnames is None:
            raise V06PkpdRmseValidatorError(
                f"{label} has no CSV header"
            )
        if not set(columns).issubset(set(reader.fieldnames)):
            raise V06PkpdRmseValidatorError(
                f"{label} is missing required RMSE columns"
            )
        rows: list[dict[str, Decimal]] = []
        for index, row in enumerate(reader, start=2):
            parsed: dict[str, Decimal] = {}
            for column in columns:
                raw_value = row.get(column)
                if raw_value is None or raw_value == "":
                    raise V06PkpdRmseValidatorError(
                        f"{label} row {index} has empty {column!r}"
                    )
                try:
                    value = Decimal(raw_value)
                except InvalidOperation as exc:
                    raise V06PkpdRmseValidatorError(
                        f"{label} row {index} has invalid decimal in {column!r}"
                    ) from exc
                if not value.is_finite():
                    raise V06PkpdRmseValidatorError(
                        f"{label} row {index} has non-finite {column!r}"
                    )
                parsed[column] = value
            rows.append(parsed)
    except csv.Error as exc:
        raise V06PkpdRmseValidatorError(
            f"{label} is invalid CSV: {exc}"
        ) from exc
    if not rows:
        raise V06PkpdRmseValidatorError(f"{label} contains no data rows")
    return rows


def _decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def evaluate_pkpd_rmse_policy_v06(
    *,
    predictions_bytes: bytes,
    observations_bytes: bytes,
    policy_bytes: bytes,
) -> dict[str, Any]:
    policy = _load_policy(policy_bytes)
    time_column = policy["time_column"]
    concentration_column = policy["concentration_column"]
    effect_column = policy["effect_column"]
    columns = (time_column, concentration_column, effect_column)

    predicted = _csv_rows(
        predictions_bytes,
        columns=columns,
        label="predictions",
    )
    observed = _csv_rows(
        observations_bytes,
        columns=columns,
        label="observations",
    )
    if len(predicted) != len(observed):
        raise V06PkpdRmseValidatorError(
            "predictions and observations have different row counts"
        )

    with localcontext() as context:
        context.prec = 50
        concentration_sq = Decimal(0)
        effect_sq = Decimal(0)
        for index, (pred, obs) in enumerate(
            zip(predicted, observed, strict=True),
            start=1,
        ):
            if pred[time_column] != obs[time_column]:
                raise V06PkpdRmseValidatorError(
                    f"time mismatch at aligned row {index}"
                )
            concentration_sq += (
                pred[concentration_column] - obs[concentration_column]
            ) ** 2
            effect_sq += (
                pred[effect_column] - obs[effect_column]
            ) ** 2

        n = Decimal(len(predicted))
        concentration_rmse = (concentration_sq / n).sqrt()
        effect_rmse = (effect_sq / n).sqrt()
        concentration_max = _positive_decimal(
            policy["concentration_rmse_max"],
            label="concentration_rmse_max",
        )
        effect_max = _positive_decimal(
            policy["effect_rmse_max"],
            label="effect_rmse_max",
        )
        passed = (
            concentration_rmse <= concentration_max
            and effect_rmse <= effect_max
        )

    return {
        "format": "pcs-pkpd-rmse-validation-result-v1",
        "validator": PKPD_RMSE_VALIDATOR_ID_V06,
        "outcome": "PASS" if passed else "FAIL",
        "row_count": len(predicted),
        "metrics": {
            "concentration_rmse": _decimal_text(concentration_rmse),
            "effect_rmse": _decimal_text(effect_rmse),
        },
        "thresholds": {
            "concentration_rmse_max": policy["concentration_rmse_max"],
            "effect_rmse_max": policy["effect_rmse_max"],
        },
        "scope": (
            "This result establishes only that the supplied prediction and "
            "observation tables satisfy the prespecified synthetic RMSE policy. "
            "It does not establish biological or clinical validity."
        ),
    }
