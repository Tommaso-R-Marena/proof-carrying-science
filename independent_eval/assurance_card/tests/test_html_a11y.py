from __future__ import annotations

from pathlib import Path

from python_harness.card import build_and_write, main as card_main
from python_harness.html_render import LIMITATIONS_BANNER


def test_html_contains_disclaimer_skip_link_and_banner(fixture_bundle: Path, tmp_path: Path):
    card, written = build_and_write(
        fixture_bundle,
        tmp_path / "assurance",
        fmt="both",
        skip_verify=True,
    )
    html_path = written["html"]
    text = html_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in text
    assert 'lang="en"' in text
    assert 'class="skip-link"' in text
    assert 'href="#main"' in text
    assert 'id="main"' in text
    assert "focus-visible" in text
    assert "card_issues_accept" in text
    assert "inspection_is_not_authority" in text
    assert "never certifies science" in text.lower() or "never certifies" in LIMITATIONS_BANNER.lower()
    assert "LIMITATIONS" in text or "limitations-banner" in text
    assert "Authority lane" in text
    assert "Inspection lane" in text
    assert "Card integrity seal" in text
    assert "Program context digests" in text
    assert "computationally_supported" in text
    assert "scientific_adequacy_open" in text
    assert 'th scope="col"' in text
    assert written["json"].is_file()
    assert card["card_issues_accept"] is False
    assert card["card_integrity"]["digest_sha256"]
    assert card["card_integrity"]["digest_sha256"] in text


def test_cli_main_writes_both(fixture_bundle: Path, tmp_path: Path):
    out = tmp_path / "cli-card"
    rc = card_main(
        [
            "--evidence",
            str(fixture_bundle),
            "--out",
            str(out),
            "--format",
            "both",
            "--skip-verify",
            "--generated-at",
            "2026-10-17T21:00:00Z",
        ]
    )
    assert rc == 0
    assert Path(str(out) + ".html").is_file()
    assert Path(str(out) + ".json").is_file()
    loaded = Path(str(out) + ".json").read_text(encoding="utf-8")
    assert "card_integrity" in loaded
    assert "digest_sha256" in loaded
