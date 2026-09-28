from __future__ import annotations
import json
from pathlib import Path


def _map(items: list[dict]) -> dict[str, dict]:
    return {x.get('id'): x for x in items if isinstance(x, dict) and x.get('id')}


def diff_certificates(left_path: str | Path, right_path: str | Path) -> dict:
    left = json.loads(Path(left_path).read_text(encoding='utf-8'))
    right = json.loads(Path(right_path).read_text(encoding='utf-8'))
    la, ra = _map(left.get('artifacts', [])), _map(right.get('artifacts', []))
    lc, rc = _map(left.get('claims', [])), _map(right.get('claims', []))
    le, re = _map(left.get('evidence', [])), _map(right.get('evidence', []))

    artifact_changes = {}
    for aid in sorted(set(la) | set(ra)):
        if aid not in la:
            artifact_changes[aid] = {"change": "added", "right_sha256": ra[aid].get('sha256')}
        elif aid not in ra:
            artifact_changes[aid] = {"change": "removed", "left_sha256": la[aid].get('sha256')}
        elif la[aid].get('sha256') != ra[aid].get('sha256'):
            artifact_changes[aid] = {"change": "modified", "left_sha256": la[aid].get('sha256'), "right_sha256": ra[aid].get('sha256')}

    claim_changes = {}
    for cid in sorted(set(lc) | set(rc)):
        if cid not in lc:
            claim_changes[cid] = {"change": "added", "status": rc[cid].get('assessment', {}).get('status')}
        elif cid not in rc:
            claim_changes[cid] = {"change": "removed", "status": lc[cid].get('assessment', {}).get('status')}
        else:
            old_status = lc[cid].get('assessment', {}).get('status')
            new_status = rc[cid].get('assessment', {}).get('status')
            fields = {}
            if old_status != new_status:
                fields['status'] = {"left": old_status, "right": new_status}
            if lc[cid].get('predicate') != rc[cid].get('predicate'):
                fields['predicate'] = {"left": lc[cid].get('predicate'), "right": rc[cid].get('predicate')}
            if lc[cid].get('assumptions') != rc[cid].get('assumptions'):
                fields['assumptions'] = {"left": lc[cid].get('assumptions'), "right": rc[cid].get('assumptions')}
            if fields:
                claim_changes[cid] = {"change": "modified", "fields": fields}

    evidence_changes = {}
    for eid in sorted(set(le) | set(re)):
        if eid not in le:
            evidence_changes[eid] = {"change": "added", "outcome": re[eid].get('outcome')}
        elif eid not in re:
            evidence_changes[eid] = {"change": "removed", "outcome": le[eid].get('outcome')}
        else:
            fields = {}
            if le[eid].get('outcome') != re[eid].get('outcome'):
                fields['outcome'] = {"left": le[eid].get('outcome'), "right": re[eid].get('outcome')}
            if le[eid].get('check_spec') != re[eid].get('check_spec'):
                fields['check_spec'] = {"left": le[eid].get('check_spec'), "right": re[eid].get('check_spec')}
            if fields:
                evidence_changes[eid] = {"change": "modified", "fields": fields}

    return {
        "same_semantic_hash": left.get('semantic_hash') == right.get('semantic_hash'),
        "left_semantic_hash": left.get('semantic_hash'),
        "right_semantic_hash": right.get('semantic_hash'),
        "artifact_changes": artifact_changes,
        "claim_changes": claim_changes,
        "evidence_changes": evidence_changes,
    }
