from __future__ import annotations
import re

COMMENT_SPLIT_RE = re.compile(r"(#|//)")

def strip_comment(line: str) -> str:
    """Remove comments starting with '#' or '//'"""
    m = COMMENT_SPLIT_RE.split(line, maxsplit=1)
    if not m:
        return line.strip()
    if m[0] is None:
        return ""
    return m[0].strip()

LABEL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")

def split_label(line: str):
    """Return (label, rest) if line has 'label:', else (None, line)."""
    m = LABEL_RE.match(line)
    if not m:
        return None, line
    return m.group(1), m.group(2).strip()

def is_directive(line: str) -> bool:
    return line.strip().startswith('.')

def split_mnemonic_operands(line: str):
    s = line.strip()
    if not s:
        return "", ""
    parts = s.split(None, 1)
    if len(parts) == 1:
        return parts[0].lower(), ""
    return parts[0].lower(), parts[1].strip()

def split_operands(op_str: str):
    if not op_str:
        return []
    # split by commas but not inside parentheses
    out = []
    cur = []
    depth = 0
    for ch in op_str:
        if ch == '(':
            depth += 1
            cur.append(ch)
        elif ch == ')':
            depth = max(0, depth-1)
            cur.append(ch)
        elif ch == ',' and depth == 0:
            s = ''.join(cur).strip()
            if s:
                out.append(s)
            cur = []
        else:
            cur.append(ch)
    s = ''.join(cur).strip()
    if s:
        out.append(s)
    return out
