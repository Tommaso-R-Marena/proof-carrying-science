import pytest
from pcs.experimental.prover.evidence_journal_v4 import EvidenceJournal

def test_failed_next_publication_preserves_checked_row(tmp_path,monkeypatch):
    journal=EvidenceJournal(tmp_path);original={'goal':'original','status':'unknown'}
    receipt=journal.append(0,original)
    def interrupted(*args):raise OSError('actual publication interrupted')
    monkeypatch.setattr('pcs.experimental.prover.evidence_journal_v4.os.link',interrupted)
    with pytest.raises(OSError):journal.append(1,{'goal':'next','status':'unknown'})
    assert journal.read(0,receipt['sha256'])==original
    assert not (tmp_path/'row-00001.json.gz').exists()

def test_duplicate_and_corrupted_record_fail_closed(tmp_path):
    j=EvidenceJournal(tmp_path);r=j.append(0,{'status':'verified','authority':False})
    with pytest.raises(ValueError):j.append(0,{'status':'forged'})
    p=tmp_path/r['row'];p.write_bytes(p.read_bytes()+b'changed')
    with pytest.raises(ValueError):j.read(0,r['sha256'])

@pytest.mark.parametrize('index',[True,-1,100000,'../outside'])
def test_index_cannot_escape_output(tmp_path,index):
    with pytest.raises(ValueError):EvidenceJournal(tmp_path).append(index,{})
