from __future__ import annotations

import re

from .models import Statement


def parse_sql_block(body: str):
    lowered = body.lower()
    query = Statement(text=body, kind="sql_query")
    query.raw = body

    select_match = re.search(r"select\s+(.*?)\s+from\b", lowered, flags=re.I | re.S)
    if select_match:
        select_fragment = select_match.group(1).strip()
        query.select_columns = [part.strip() for part in select_fragment.split(",") if part.strip()]

    from_match = re.search(r"from\s+([a-z0-9_\.%]+)", lowered, flags=re.I)
    if from_match:
        query.from_tables = [from_match.group(1).strip()]

    where_match = re.search(r"where\s+(.*?)(?:group\s+by|order\s+by|limit|;|$)", lowered, flags=re.I | re.S)
    if where_match:
        query.where_condition = where_match.group(1).strip()

    group_match = re.search(r"group\s+by\s+(.*?)(?:order\s+by|having|;|$)", lowered, flags=re.I | re.S)
    if group_match:
        group_value = group_match.group(1).strip()
        query.group_by = [group_value]
        query.group_by.extend([part.strip() for part in group_value.split(",") if part.strip()])

    return [query]
