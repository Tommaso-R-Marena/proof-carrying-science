"""Parse the real CI download command without executing a download/verifier."""
import ast
from pathlib import Path
import shlex


def test_workflow_inline_python_is_syntactically_valid():
    root=Path(__file__).resolve().parents[2]
    text=(root/'.github/workflows/pcs-public-study-validation.yml').read_text()
    commands=[shlex.split(line.strip()) for line in text.splitlines() if line.strip().startswith('python -c ')]
    assert commands, 'download command must remain covered'
    for command in commands:
        assert len(command)==3 and command[:2]==['python','-c']
        ast.parse(command[2])
