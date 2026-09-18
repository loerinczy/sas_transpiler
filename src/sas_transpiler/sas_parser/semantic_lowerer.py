from __future__ import annotations

import re
from typing import List

from .models import Aggregate, Assignment, Filter, Join, Job, Literal, SourceRef, TargetRef


def _parse_assignment(statement_text: str):
    match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*;?\s*$", statement_text.strip(), flags=re.I)
    if not match:
        return None
    target = match.group(1)
    expression = match.group(2).strip()
    return target, expression


def _lower_data_step(section) -> List[SourceRef]:
    refs: List[SourceRef] = []
    statements = section.statements or []
    for stmt in statements:
        if stmt.kind == "set":
            dataset = re.search(r"^\s*set\s+([A-Za-z0-9_\.\%]+)\s*;?\s*$", stmt.text, flags=re.I)
            if dataset:
                refs.append(SourceRef(dataset=dataset.group(1)))
        elif stmt.kind == "where":
            if stmt.condition:
                pass
    return refs


def _lower_sql_query(statement) -> tuple[List[SourceRef], List[Filter], List[Join], List[Aggregate], List[TargetRef]]:
    inputs: List[SourceRef] = []
    filters: List[Filter] = []
    joins: List[Join] = []
    aggregates: List[Aggregate] = []
    outputs: List[TargetRef] = []

    for table in getattr(statement, "from_tables", []) or []:
        if table:
            inputs.append(SourceRef(dataset=table))

    if getattr(statement, "where_condition", ""):
        filters.append(Filter(condition=Literal(statement.where_condition.strip())))

    join_type = getattr(statement, "join_type", "").strip()
    join_condition = getattr(statement, "join_condition", "").strip()
    if join_type and join_condition:
        left = (getattr(statement, "from_tables", []) or [""])[0]
        right = (getattr(statement, "from_tables", []) or [""])[-1]
        joins.append(Join(left=left, right=right, type=join_type, condition=Literal(join_condition)))

    if getattr(statement, "group_by", None):
        agg = Aggregate(group_by=[item.strip() for item in statement.group_by if item and item.strip()], measures=[])
        if getattr(statement, "select_columns", None):
            agg.measures = [item.strip() for item in statement.select_columns if item and item.strip() and ("sum(" in item.lower() or "count(" in item.lower() or "avg(" in item.lower())]
        aggregates.append(agg)

    target_match = re.search(r"create\s+table\s+([A-Za-z0-9_\.\%]+)\s+as", statement.text, flags=re.I)
    if target_match:
        outputs.append(TargetRef(dataset=target_match.group(1)))

    return inputs, filters, joins, aggregates, outputs


def lower_program(program):
    job = Job(name="job_1")

    for section in program.sections:
        if section.kind == "data_step":
            for stmt in section.statements:
                if stmt.kind == "set":
                    dataset = re.search(r"^\s*set\s+([A-Za-z0-9_\.\%]+)\s*;?\s*$", stmt.text, flags=re.I)
                    if dataset:
                        job.inputs.append(SourceRef(dataset=dataset.group(1)))
                elif stmt.kind == "where":
                    if stmt.condition:
                        job.filters.append(Filter(condition=Literal(stmt.condition.strip())))
                elif stmt.kind == "assignment":
                    assignment = _parse_assignment(stmt.text)
                    if assignment:
                        target, expr = assignment
                        job.transforms.append(Assignment(target=target, expression=Literal(expr)))
        elif section.kind == "proc_sql":
            for stmt in section.statements:
                if stmt.kind == "sql_query":
                    inputs, filters, joins, aggregates, outputs = _lower_sql_query(stmt)
                    job.inputs.extend(inputs)
                    job.filters.extend(filters)
                    job.joins.extend(joins)
                    job.aggregates.extend(aggregates)
                    job.outputs.extend(outputs)

    deduped_inputs = []
    seen = set()
    for ref in job.inputs:
        if ref.dataset not in seen:
            seen.add(ref.dataset)
            deduped_inputs.append(ref)
    job.inputs = deduped_inputs

    if not job.outputs:
        for section in program.sections:
            if section.kind == "data_step":
                for stmt in section.statements:
                    if stmt.kind == "where":
                        continue

    return job
