"""Actual native authority + SQL + replay; no model or positive-verifier mocks."""
from pathlib import Path

from .protocol import FORMAT
from .live import run,replay
from .intake import prepare,parse
from .report import write_report


def plan():
    return dict(format=FORMAT,cases=[dict(id="oracle",title="Actual control integration",task="Fixed workflow control.",
                                         pre_sanitized=False,mode="oracle")])


def test_real_control_live_bridge_proofs_and_replay(tmp_path):
    original=tmp_path/"live";received=tmp_path/"received"
    frozen=run(None,None,original,plan(),progress=lambda _:None)
    assert len(frozen.episodes)==1 and parse(frozen.episodes[0].capture_json)["final"]["transitions"]==4
    result=parse((original/"oracle/result.json").read_bytes())
    assert len(result["native_build"]["axiom_closures"])==52
    assert all(result[k]["kernel_checked"] is True for k in ("captured_wire_proof","captured_rows_proof","captured_path_proof"))
    replay(original,None,received)
    assert (original/"oracle/capture.json").read_bytes()==(received/"oracle/capture.json").read_bytes()
    assert parse((received/"replay.json").read_bytes())["inference_performed"] is False
    write_report(frozen,original/"report.html","live")
    assert "Deterministic controls" in (original/"report.html").read_text()


def test_real_replay_uses_frozen_inputs_after_source_files_are_replaced(tmp_path,monkeypatch):
    from . import live
    original=tmp_path/"original";received=tmp_path/"received"
    frozen=run(None,None,original,plan(),progress=lambda _:None)
    original_prepare=live.prepare
    def freeze_then_replace(root,oracle):
        checked=original_prepare(root,oracle)
        for path in (root/"suite.json",root/"oracle/capture.json",root/"oracle/result.json"):
            path.write_bytes(b"changed after successful full preflight")
        return checked
    monkeypatch.setattr(live,"prepare",freeze_then_replace)
    # The actual native authority/SQL/proof checker remains unchanged.
    live.replay(original,None,received)
    result=parse((received/"replay.json").read_bytes())
    assert result["suite_sha256"]==frozen.sha256
    assert (received/"oracle/capture.json").read_bytes()==frozen.episodes[0].capture_json
