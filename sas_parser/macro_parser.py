from __future__ import annotations

import re

from .models import Statement


def parse_macro_block(body: str):
    statements = []
    macro_match = re.search(r"%macro\s+([A-Za-z0-9_]+)", body, flags=re.I)
    name = macro_match.group(1) if macro_match else None

    if macro_match:
        statements.append(Statement(text=macro_match.group(0).strip(), kind="macro_declaration"))

    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("%macro") or stripped.startswith("%mend"):
            continue
        if stripped.startswith("%let "):
            statements.append(Statement(text=stripped, kind="macro_assignment"))
            continue
        if stripped.startswith("%include "):
            statements.append(Statement(text=stripped, kind="macro_include"))
            continue
        if stripped.startswith("proc ") or stripped.startswith("data "):
            statements.append(Statement(text=stripped, kind="macro_inner_logic"))
            continue

    return name, statements
