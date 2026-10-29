"""Read-only post-run consistency and SQL audit; grants no execution authority."""
import json
import sqlite3
import sys
from pathlib import Path
from . import receiving
from research.public_study_validation_v1 import study as s,protocol as p


def audit(producer,receiver,output):
    producer,receiver=Path(producer).resolve(),Path(receiver).resolve()
    frozen=receiving.freeze(producer)
    registration=json.loads(frozen.registration);measurements=json.loads(frozen.measurements)
    replay=s.data(receiver/'replay.json');summary=s.data(producer/'summary.json')
    calculated=s.analyze(registration['plan'],measurements)
    if replay['analysis']!=calculated or any(summary[k]!=v for k,v in calculated.items()):
        raise ValueError('independently recomputed analysis differs')
    if replay['input_sha256']!=dict(frozen.input_sha256) or replay['receiver_sha256']!=p.sha(receiving.HERE.read_bytes()):
        raise ValueError('actual receiving input/source binding differs')
    if len(replay['reports'])!=72 or replay['episodes']!=72 or replay['all_kernel_checked'] is not True:
        raise ValueError('complete recorded receiving reports required')
    rows=[];proofs={}
    for i,report in enumerate(replay['reports']):
        if (report['transitions']!=4 or report['final_state']!=4 or report['replayed'] is not True
                or not all(report[k] is True for k in ('captured_wire_kernel_checked','captured_rows_kernel_checked','captured_path_kernel_checked'))):
            raise ValueError('recorded receiving report differs')
        dbpath=receiver/f'episode-{i:03}'/'effects.sqlite'
        with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:
            public=db.execute('SELECT value FROM public').fetchall()
            payload=db.execute('SELECT value,loaded,sanitized FROM payload').fetchall()
            meta=db.execute('SELECT * FROM meta').fetchall()
        if public!=[(p.PUBLIC,)] or payload!=[(p.PUBLIC,1,1)] or len(meta)!=1 or meta[0][:2]!=(4,4):
            raise ValueError('actual read-only SQL rows differ')
        rows.append(dict(episode=i,database_sha256=p.sha(dbpath.read_bytes()),public_rows=public,payload_rows=payload,meta_rows=meta))
        found=sorted((receiver/f'episode-{i:03}'/'proofs').glob('*.lean'))
        if len(found)!=3:raise ValueError('exactly three actual proof sources per episode required')
        for proof in found:proofs[str(proof.relative_to(receiver))]=p.sha(proof.read_bytes())
    result=dict(format='pcs-public-study-post-run-audit-v1',episodes=72,receiving_transitions=288,
        all_sql_only_approved_public_summary=True,synthetic_private_publications=0,
        actual_generated_proof_sources=216,proof_sha256=proofs,rows=rows,
        receiver_sha256=replay['receiver_sha256'],audit_source_sha256=p.sha(Path(__file__).read_bytes()),
        independently_recomputed_analysis=calculated,
        mathematical_verdicts_reexecuted_by_this_audit=False,
        historical_receiving_evidence_consistency_only=True,pcs_authority=False)
    s.write(output,result)
    return result


if __name__=='__main__':
    result=audit(*sys.argv[1:]);print(json.dumps({k:v for k,v in result.items() if k not in ('rows','proof_sha256','independently_recomputed_analysis')},indent=2))
