from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from .models import Section


_SECTION_PATTERN = re.compile(
    r"(?is)(%macro\s+[^;\n]+.*?%mend;?|proc\s+sql\b.*?(?:quit\s*;|run\s*;)|data\s+[^;\n]+;.*?(?:run\s*;|quit\s*;))"
)


@dataclass
class BlockMatch:
    kind: str
    header: str
    body: str


def split_sections(text: str) -> List[Section]:
    sections: List[Section] = []
    matches = list(_SECTION_PATTERN.finditer(text))

    if not matches:
        normalized = text.strip()
        if normalized:
            sections.append(Section(kind="metadata", header="raw", body=normalized))
        return sections

    for match in matches:
        block = match.group(1).strip()
        lower = block.lower()

        if lower.startswith("%macro"):
            kind = "macro"
            header = block.splitlines()[0].strip() if block.splitlines() else "macro"
            name_match = re.search(r"%macro\s+([A-Za-z0-9_]+)", block)
            name = name_match.group(1) if name_match else None
        elif lower.startswith("proc"):
            kind = "proc_sql"
            header = block.splitlines()[0].strip() if block.splitlines() else "proc sql"
            name = None
        elif lower.startswith("data"):
            kind = "data_step"
            header = block.splitlines()[0].strip() if block.splitlines() else "data"
            name = None
        else:
            kind = "metadata"
            header = "metadata"
            name = None

        section = Section(
            kind=kind,
            header=header,
            body=block,
            name=name,
        )
        section.source_text = text
        sections.append(section)

    return sections
