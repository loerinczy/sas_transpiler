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
        elif lower.startswith("proc"):
            kind = "proc_sql"
            header = block.splitlines()[0].strip() if block.splitlines() else "proc sql"
        elif lower.startswith("data"):
            kind = "data_step"
            header = block.splitlines()[0].strip() if block.splitlines() else "data"
        else:
            kind = "metadata"
            header = "metadata"

        section = Section(
            kind=kind,
            header=header,
            body=block,
        )
        section.source_text = text
        sections.append(section)

    return sections
