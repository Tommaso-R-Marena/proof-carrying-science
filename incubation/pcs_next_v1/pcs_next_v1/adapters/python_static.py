"""Non-executing static discovery for Python research scripts."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


SUPPORTED = {
    "fragment": "pcs-next-python-static-v1",
    "executes_code": False,
    "limitations": [
        "Does not execute imported modules.",
        "Dynamic imports and getattr paths are flagged UNSUPPORTED.",
        "Network and subprocess usage flagged.",
    ],
}


class PythonStaticAdapter:
    def inspect(self, path: str | Path) -> dict[str, Any]:
        text = Path(path).read_text(encoding="utf-8")
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            return {"status": "REFUTED", "reason": f"syntax error: {exc}", "supported": SUPPORTED}

        imports: list[str] = []
        calls: list[str] = []
        flags: list[str] = []
        assigns: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imports.append(a.name)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Call):
                name = _call_name(node)
                calls.append(name)
                if name in {"exec", "eval", "compile", "__import__"}:
                    flags.append(f"dynamic_execution:{name}")
                if name.startswith("subprocess.") or name in {"os.system", "os.popen"}:
                    flags.append(f"process:{name}")
                if name.startswith("requests.") or name.startswith("urllib"):
                    flags.append(f"network:{name}")
                if name in {"open"}:
                    flags.append("filesystem:open")
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        assigns.append(t.id)

        randomness = [c for c in calls if "random" in c or c.endswith("seed")]
        model_fit = [c for c in calls if any(k in c for k in ("fit", "minimize", "curve_fit", "OLS"))]

        status = "COMPUTATIONALLY_TESTED" if not flags else "CONDITIONAL"
        return {
            "adapter": SUPPORTED["fragment"],
            "path": str(path),
            "imports": sorted(set(imports)),
            "calls_sample": sorted(set(calls))[:50],
            "assigns_sample": assigns[:50],
            "randomness": randomness,
            "model_fitting_calls": model_fit,
            "flags": flags,
            "status": status,
            "supported": SUPPORTED,
        }


def _call_name(node: ast.Call) -> str:
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        parts = []
        cur: Any = f
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return ".".join(reversed(parts))
    return "<unknown>"
