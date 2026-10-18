from pcs_next_v1.adapters.python_static import PythonStaticAdapter
from pathlib import Path

def test_flags_exec(tmp_path):
    p = tmp_path / "x.py"
    p.write_text("import os\nexec('1')\n")
    r = PythonStaticAdapter().inspect(p)
    assert any("dynamic_execution" in f for f in r["flags"])
