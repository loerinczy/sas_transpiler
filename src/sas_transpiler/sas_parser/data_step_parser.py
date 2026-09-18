from __future__ import annotations

import re

from .models import Statement


def _split_statements(body: str):
    statements = []
    buffer = []
    depth = 0
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        buffer.append(line)
        if stripped.lower().endswith("do;"):
            depth += 1
        if stripped.lower().endswith("end;"):
            depth = max(0, depth - 1)
        if ";" in stripped and depth == 0:
            statements.append("\n".join(buffer).strip())
            buffer = []
    if buffer:
        statements.append("\n".join(buffer).strip())
    return [s for s in statements if s]


def parse_data_step_block(body: str):
    statements = []
    for text in _split_statements(body):
        lowered = text.lower().strip()

        if lowered.startswith("if "):
            stmt = Statement(text=text, kind="if")
            stmt.raw = text
            stmt.condition = text[3:].split("then", 1)[0].strip() if "then" in text.lower() else ""
            statements.append(stmt)
            continue

        if lowered.startswith("set "):
            stmt = Statement(text=text, kind="set")
            stmt.raw = text
            statements.append(stmt)
            continue

        if lowered.startswith("where "):
            stmt = Statement(text=text, kind="where")
            stmt.raw = text
            stmt.condition = text[len("where ") :].rstrip(";").strip()
            statements.append(stmt)
            continue

        if lowered.startswith("keep ") or lowered.startswith("drop "):
            stmt = Statement(text=text, kind="keep_drop")
            stmt.raw = text
            statements.append(stmt)
            continue

        if lowered.startswith("rename "):
            stmt = Statement(text=text, kind="rename")
            stmt.raw = text
            statements.append(stmt)
            continue

        if "=" in text and "if " not in lowered and not lowered.startswith(("data ", "run", "quit")):
            stmt = Statement(text=text, kind="assignment")
            stmt.raw = text
            statements.append(stmt)
            continue

        statements.append(Statement(text=text, kind="unknown", raw=text))
    return statements
