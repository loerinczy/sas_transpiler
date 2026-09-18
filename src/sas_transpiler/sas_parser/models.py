from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class SourceSpan:
    start: int = 0
    end: int = 0
    line: int = 1
    column: int = 1


class Node:
    source_text: Optional[str] = None
    span: Optional[SourceSpan] = None


@dataclass
class Section(Node):
    kind: str
    header: str = ""
    body: str = ""
    name: Optional[str] = None
    statements: List["Statement"] = field(default_factory=list)


@dataclass
class Program(Node):
    sections: List[Section] = field(default_factory=list)
    raw_text: str = ""


@dataclass
class Statement(Node):
    text: str = ""
    kind: str = "statement"
    condition: Optional[str] = None
    select_columns: List[str] = field(default_factory=list)
    from_tables: List[str] = field(default_factory=list)
    where_condition: str = ""
    group_by: List[str] = field(default_factory=list)
    join_type: str = ""
    join_condition: str = ""
    raw: str = ""


@dataclass
class DataStep(Statement):
    dataset_name: Optional[str] = None
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)


@dataclass
class ProcSql(Statement):
    query_text: str = ""


@dataclass
class MacroBlock(Statement):
    name: Optional[str] = None
    parameters: List[str] = field(default_factory=list)


@dataclass
class UnsupportedNode(Statement):
    reason: str = "unsupported"
    raw_text: str = ""


@dataclass
class Expression(Node):
    pass


@dataclass
class ColumnRef(Expression):
    name: str


@dataclass
class Literal(Expression):
    value: Any


@dataclass
class FunctionCall(Expression):
    name: str
    args: List[Expression] = field(default_factory=list)


@dataclass
class Assignment(Node):
    target: str
    expression: Expression


@dataclass
class Filter(Node):
    condition: Expression


@dataclass
class Join(Node):
    left: str
    right: str
    type: str = "inner"
    condition: Optional[Expression] = None


@dataclass
class Aggregate(Node):
    group_by: List[str] = field(default_factory=list)
    measures: List[str] = field(default_factory=list)


@dataclass
class Column(Node):
    name: str
    source: Optional[str] = None
    expr: Optional[Expression] = None


@dataclass
class Dataset(Node):
    name: str
    columns: List[Column] = field(default_factory=list)


@dataclass
class SourceRef(Node):
    dataset: str


@dataclass
class TargetRef(Node):
    dataset: str


@dataclass
class Job(Node):
    name: str = ""
    inputs: List[SourceRef] = field(default_factory=list)
    outputs: List[TargetRef] = field(default_factory=list)
    transforms: List[Assignment] = field(default_factory=list)
    filters: List[Filter] = field(default_factory=list)
    joins: List[Join] = field(default_factory=list)
    aggregates: List[Aggregate] = field(default_factory=list)

