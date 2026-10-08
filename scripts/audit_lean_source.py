#!/usr/bin/env python3
"""Reject active Lean admission tokens, while respecting nested comments and strings."""
from pathlib import Path
import re
import sys

FORBIDDEN = re.compile(r"(?<![A-Za-z0-9_])(sorry|admit|axiom|unsafe|implemented_by|extern|native_decide)(?![A-Za-z0-9_])")
CHAR = re.compile(r"'(?:\\(?:u\{[0-9a-fA-F]+\}|u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|[^\n])|[^'\\\n])'")


def active_code(text: str) -> str:
    out = []
    depth = 0
    string = False
    raw_end = None
    line_comment = False
    index = 0
    while index < len(text):
        pair = text[index:index + 2]
        char = text[index]
        if raw_end:
            if text.startswith(raw_end, index):
                out.extend(' ' * len(raw_end))
                index += len(raw_end) - 1
                raw_end = None
            else:
                out.append("\n" if char == "\n" else " ")
        elif line_comment:
            if char == "\n":
                line_comment = False
            out.append("\n" if char == "\n" else " ")
        elif depth:
            if pair == "/-":
                depth += 1
                out.extend("  ")
                index += 1
            elif pair == "-/":
                depth -= 1
                out.extend("  ")
                index += 1
            else:
                out.append("\n" if char == "\n" else " ")
        elif string:
            if char == "\\":
                out.extend("  ")
                index += 1
            else:
                if char == '"':
                    string = False
                out.append("\n" if char == "\n" else " ")
        elif pair == "/-":
            depth = 1
            out.extend("  ")
            index += 1
        elif pair == "--":
            line_comment = True
            out.extend("  ")
            index += 1
        elif char == "'" and (index == 0 or not (text[index - 1].isalnum() or text[index - 1] in "_'")) and (literal := CHAR.match(text, index)):
            out.extend(' ' * len(literal.group()))
            index = literal.end() - 1
        elif char == 'r' and (index == 0 or not (text[index - 1].isalnum() or text[index - 1] in "_'")) and (raw := re.match(r'r(#+)"', text[index:])):
            raw_end = '"' + raw.group(1)
            out.extend(' ' * len(raw.group()))
            index += len(raw.group()) - 1
        elif char == '"':
            string = True
            out.append(" ")
        else:
            out.append(char)
        index += 1
    if depth or string or raw_end:
        raise ValueError("unterminated comment or string")
    return "".join(out)


def audit(paths: list[Path]) -> list[str]:
    errors = []
    for path in paths:
        files = sorted(path.rglob("*.lean")) if path.is_dir() else [path]
        for file in files:
            try:
                code = active_code(file.read_text(encoding="utf-8"))
                for match in FORBIDDEN.finditer(code):
                    errors.append(f"{file}:{code.count(chr(10), 0, match.start()) + 1}: forbidden active token {match.group(1)}")
            except (ValueError, OSError) as error:
                errors.append(f"{file}: audit incomplete: {error}")
    return errors


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("supply production Lean source paths")
    findings = audit([Path(name) for name in sys.argv[1:]])
    if findings:
        print("\n".join(findings), file=sys.stderr)
        raise SystemExit(1)
    print("Production Lean source admission/escape-hatch audit passed.")
