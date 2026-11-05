import json
from pathlib import Path
import pytest
from pcs_next_v1.demos.provenance import verify_manifest, FIX
from pcs_next_v1.core.errors import PcsNextError

def test_manifest_tamper(tmp_path):
    # copy manifest and break hash
    import shutil
    root = tmp_path / "jd"
    shutil.copytree(FIX, root)
    man = json.loads((root / "MANIFEST.json").read_text())
    man["datasets"][0]["sha256"] = "0" * 64
    (root / "MANIFEST.json").write_text(json.dumps(man))
    with pytest.raises(PcsNextError):
        verify_manifest(root)
