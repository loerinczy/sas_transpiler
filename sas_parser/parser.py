from __future__ import annotations

from .blocks import split_sections
from .data_step_parser import parse_data_step_block
from .macro_parser import parse_macro_block
from .models import Program
from .sql_parser import parse_sql_block


def parse_program(text: str) -> Program:
    sections = split_sections(text)
    for section in sections:
        if section.kind == "macro":
            section.name, section.statements = parse_macro_block(section.body)
        elif section.kind == "data_step":
            section.statements = parse_data_step_block(section.body)
        elif section.kind == "proc_sql":
            section.statements = parse_sql_block(section.body)
    return Program(sections=sections, raw_text=text)
