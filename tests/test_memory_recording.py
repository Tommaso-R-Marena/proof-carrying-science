"""Lossless bounded-buffer artifact recording; no full-run JSON allocation."""
import gzip,json
from pcs.experimental.prover.memory_recording import write

def test_streamed_recording_preserves_complete_json_and_stable_compression(tmp_path):
    large={'states':[{'goal':'∀ n, n = n','typed':{'children':list(range(30))},'index':i} for i in range(6000)]}
    a=tmp_path/'first.json';b=tmp_path/'second.json';write(a,large);write(b,large)
    assert not a.exists()
    first=a.with_suffix('.json.gz').read_bytes();second=b.with_suffix('.json.gz').read_bytes()
    assert first==second
    assert json.loads(gzip.decompress(first))==large
    small=tmp_path/'small.json';write(small,{'verified':False,'reason':'unknown'})
    assert json.loads(small.read_text())=={'verified':False,'reason':'unknown'}
