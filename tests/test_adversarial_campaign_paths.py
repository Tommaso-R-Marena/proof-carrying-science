"""Guard against stale adversarial fixtures that silently stop exercising real package artifacts."""

import json
from pathlib import Path

import pytest

from pcs.kernel import build_certificate
from scripts.adversarial_campaign import MANIFEST, PKPD_MANIFEST, packaged_artifact_path


@pytest.mark.parametrize(
    ("manifest", "artifact_id"),
    [(MANIFEST, "train"), (MANIFEST, "test"), (PKPD_MANIFEST, "pk_predictions")],
)
def test_campaign_resolves_real_packaged_artifact(tmp_path: Path, manifest: Path, artifact_id: str) -> None:
    bundle = tmp_path / "bundle"
    certificate = build_certificate(manifest, bundle)
    target = packaged_artifact_path(bundle, certificate, artifact_id)
    assert target.is_file()
    assert target == (bundle / next(a["path"] for a in certificate["artifacts"] if a["id"] == artifact_id)).resolve()


def test_campaign_rejects_missing_and_ambiguous_target(tmp_path: Path) -> None:
    cert = {"artifacts": [{"id": "train", "path": "artifacts/missing/payload"}]}
    with pytest.raises(ValueError, match="missing or escaped"):
        packaged_artifact_path(tmp_path, cert, "train")
    cert["artifacts"].append(dict(cert["artifacts"][0]))
    with pytest.raises(ValueError, match="exactly one"):
        packaged_artifact_path(tmp_path, cert, "train")


def test_campaign_rejects_artifact_path_escape(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    outside = tmp_path / "outside"
    outside.write_text("sensitive artifact", encoding="utf-8")
    cert = {"artifacts": [{"id": "train", "path": "../outside"}]}
    with pytest.raises(ValueError, match="missing or escaped"):
        packaged_artifact_path(package, cert, "train")
