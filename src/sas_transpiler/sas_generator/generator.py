from __future__ import annotations

import ast
import json
import keyword
import re
from typing import Iterable, List, Tuple

from sas_parser.models import Aggregate, Assignment, ColumnRef, Filter, FunctionCall, Job, Join, Literal, SourceRef, TargetRef

from .models import GeneratedModule, GenerationConfig, GenerationError
from .validation import validate_job


PYSPARK_IMPORTS = [
    "from pyspark.sql import DataFrame, SparkSession",
    "from pyspark.sql import functions as F",
]

_RESERVED_NAMES = {
    "spark",
    "sources",
    "runtime",
    "outputs",
    "DataFrame",
    "SparkSession",
    "F",
    "df",
    "pd",
    "list",
    "dict",
    "str",
    "int",
    "float",
    "bool",
    "set",
    "tuple",
}


def generate_job(job: Job, config: GenerationConfig | None = None) -> GeneratedModule:
    config = config or GenerationConfig()
    diagnostics = validate_job(job)
    if config.strict and any(diagnostic.level == "error" for diagnostic in diagnostics):
        raise GenerationError(diagnostics)

    source = _render_module(job, config)
    return GeneratedModule(source=source, imports=PYSPARK_IMPORTS, diagnostics=diagnostics)


def _render_module(job: Job, config: GenerationConfig) -> str:
    lines = [
        "\n".join(PYSPARK_IMPORTS),
        "",
        f"def {config.function_name}(spark: SparkSession, sources: dict[str, DataFrame], runtime=None) -> dict[str, DataFrame]:",
        f'    """Run the generated PySpark job: {job.name or "unnamed_job"}."""',
        "    outputs: dict[str, DataFrame] = {}",
    ]

    source_bindings = _resolve_reference_bindings(job.inputs)
    used_names = {variable for _, variable in source_bindings}
    output_bindings = _resolve_reference_bindings(job.outputs, used_names)

    if source_bindings:
        for dataset, variable in source_bindings:
            source_key = json.dumps(dataset)
            lines.append(f"    if {source_key} not in sources:")
            lines.append(f'        raise KeyError("Missing dependency: {dataset}")')
            lines.append(f"    {variable} = sources[{source_key}]")
        working_name = source_bindings[0][1]
    else:
        working_name = "spark.createDataFrame([], schema='*')"

    lines.append(f"    df_working = {working_name}")
    working_name = "df_working"

    source_binding_map = {dataset: variable for dataset, variable in source_bindings}

    for join_step in job.joins:
        left_var = source_binding_map.get(join_step.left.strip(), _safe_identifier(join_step.left.strip()))
        right_var = source_binding_map.get(join_step.right.strip(), _safe_identifier(join_step.right.strip()))
        left_alias = _default_alias(join_step.left.strip())
        right_alias = _default_alias(join_step.right.strip())
        left_alias_var = f"{left_var}_alias"
        right_alias_var = f"{right_var}_alias"
        lines.append(f"    {left_alias_var} = {left_var}.alias({json.dumps(left_alias)})")
        lines.append(f"    {right_alias_var} = {right_var}.alias({json.dumps(right_alias)})")
        join_type = _spark_join_type(join_step.type)
        condition = _translate_expression(join_step.condition) if join_step.condition is not None else "F.lit(True)"
        lines.append(f"    {working_name} = {left_alias_var}.join({right_alias_var}, ({condition}), how={json.dumps(join_type)})")

    for filter_step in job.filters:
        condition = _translate_expression(getattr(filter_step, "condition", None))
        lines.append(f"    {working_name} = {working_name}.filter({condition})")

    for aggregate in job.aggregates:
        group_by = [col for col in (aggregate.group_by or []) if col and col.strip()]
        measures = [measure for measure in (aggregate.measures or []) if measure and measure.strip()]
        if group_by:
            group_exprs = ", ".join(f"F.col({json.dumps(col)})" for col in group_by)
            lines.append(f"    {working_name} = {working_name}.groupBy({group_exprs}).agg({', '.join(_translate_aggregate_measure(measure) for measure in measures)})")
        elif measures:
            lines.append(f"    {working_name} = {working_name}.agg({', '.join(_translate_aggregate_measure(measure) for measure in measures)})")

    for transform in job.transforms:
        target = transform.target
        expr = _translate_expression(transform.expression)
        lines.append(f'    {working_name} = {working_name}.withColumn({json.dumps(target)}, {expr})')

    if not job.transforms and not job.filters and not job.joins and not job.aggregates and source_bindings:
        working_name = "df_working" if source_bindings else "spark.createDataFrame([], schema='*')"
        if source_bindings:
            lines.append(f"    {working_name} = {source_bindings[0][1]}")

    if output_bindings:
        for dataset, variable in output_bindings:
            lines.append(f"    {variable} = {working_name}")
            lines.append(f"    outputs[{json.dumps(dataset)}] = {variable}")
    else:
        lines.append(f"    outputs['output'] = {working_name}")

    lines.append("    return outputs")
    lines.append("")
    return "\n".join(lines)


def _safe_identifier(raw_name: str) -> str:
    token = re.sub(r"[^0-9A-Za-z_]+", "_", (raw_name or "").strip())
    token = token.strip("_")
    if not token:
        token = "dataset"
    if token[0].isdigit():
        token = f"df_{token}"
    if not token.startswith("df_"):
        token = f"df_{token}"
    if keyword.iskeyword(token) or token in _RESERVED_NAMES:
        token = f"{token}_"
    return token


def _resolve_reference_bindings(
    references: Iterable[SourceRef | TargetRef],
    used_names: set[str] | None = None,
) -> List[Tuple[str, str]]:
    resolved: List[Tuple[str, str]] = []
    used = set(used_names or [])
    for reference in references:
        dataset = (reference.dataset or "").strip()
        if not dataset:
            continue
        base_name = _safe_identifier(dataset)
        candidate = base_name
        counter = 2
        while candidate in used or keyword.iskeyword(candidate) or candidate in _RESERVED_NAMES:
            candidate = f"{base_name}_{counter}"
            counter += 1
        used.add(candidate)
        resolved.append((dataset, candidate))
    return resolved


def _translate_expression(expression: object) -> str:
    if isinstance(expression, ColumnRef):
        return f'F.col({json.dumps(expression.name)})'
    if isinstance(expression, FunctionCall):
        return _translate_function_call(expression)
    if isinstance(expression, Literal):
        return _translate_literal_value(expression.value)
    if isinstance(expression, str):
        return _translate_raw_expression(expression)
    if expression is None:
        return "F.lit(None)"
    return _translate_raw_expression(str(expression))


def _spark_string_literal(value: str) -> str:
    return f"F.lit({json.dumps(value)})"


def _translate_literal_value(value: object) -> str:
    if value is None:
        return "F.lit(None)"
    if isinstance(value, bool):
        return f"F.lit({str(value)})"
    if isinstance(value, (int, float)):
        return f"F.lit({value!r})"
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return _spark_string_literal("")
        if stripped.lower() in {"true", "false", "null", "missing"}:
            return f"F.lit({stripped.lower() == 'true'})" if stripped.lower() in {"true", "false"} else "F.lit(None)"
        if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", stripped):
            return f"F.lit({float(stripped) if '.' in stripped else int(stripped)})"
        if (stripped.startswith("'") and stripped.endswith("'")) or (stripped.startswith('"') and stripped.endswith('"')):
            return _spark_string_literal(ast.literal_eval(stripped))
        if re.search(r"[\+\-\*/<>=!&|()]|\b(?:and|or|not)\b", stripped, flags=re.I):
            return _translate_raw_expression(stripped)
        return f'F.col({json.dumps(stripped)})'
    return f"F.lit({value!r})"


def _translate_function_call(call: FunctionCall) -> str:
    name = call.name.strip()
    args = [_translate_expression(arg) for arg in call.args]
    mapped = {
        "abs": "F.abs",
        "ceil": "F.ceil",
        "floor": "F.floor",
        "round": "F.round",
        "lower": "F.lower",
        "upper": "F.upper",
        "length": "F.length",
        "trim": "F.trim",
        "ltrim": "F.ltrim",
        "rtrim": "F.rtrim",
        "coalesce": "F.coalesce",
        "concat": "F.concat",
        "substr": "F.substring",
        "substring": "F.substring",
        "sum": "F.sum",
        "avg": "F.avg",
        "count": "F.count",
        "min": "F.min",
        "max": "F.max",
        "mean": "F.avg",
    }
    fn = mapped.get(name.lower(), None)
    if fn is None:
        return f"F.col({json.dumps(name)})"
    if name.lower() == "concat":
        return f"F.concat({', '.join(args)})"
    return f"{fn}({', '.join(args)})"


def _translate_aggregate_measure(measure: str) -> str:
    cleaned = (measure or "").strip()
    if not cleaned:
        return "F.lit(None)"
    match = re.match(r"^(?P<func>[A-Za-z_][A-Za-z0-9_]*)\s*\(\s*(?P<arg>[^)]*?)\s*\)\s*(?:as\s+(?P<alias>[A-Za-z_][A-Za-z0-9_]*))?\s*$", cleaned, flags=re.I)
    if not match:
        return f"F.lit({cleaned!r})"
    func = match.group("func").lower()
    arg = match.group("arg").strip()
    alias = match.group("alias")
    mapping = {"sum": "F.sum", "avg": "F.avg", "count": "F.count", "min": "F.min", "max": "F.max"}
    spark_func = mapping.get(func, None)
    if spark_func is None:
        return f"F.lit({cleaned!r})"
    if arg == "*":
        expression = f"{spark_func}(F.lit(1))"
    else:
        expression = f"{spark_func}(F.col({json.dumps(arg)}))"
    if alias:
        expression = f"{expression}.alias({json.dumps(alias)})"
    return expression


def _default_alias(dataset: str) -> str:
    token = re.split(r"[./\\]+", (dataset or "").strip())[-1]
    parts = re.findall(r"[A-Za-z0-9]+", token)
    if not parts:
        return "t"
    alias = parts[-1].lower()
    if not alias:
        alias = "t"
    return alias


def _spark_join_type(join_type: str) -> str:
    value = (join_type or "inner").strip().lower()
    if value.startswith("left"):
        return "left"
    if value.startswith("right"):
        return "right"
    if value.startswith("full"):
        return "full"
    if value.startswith("cross"):
        return "cross"
    return "inner"


def _translate_raw_expression(expression: str) -> str:
    if not expression or not expression.strip():
        return "F.lit(None)"

    text = expression.strip().rstrip(";")
    if text.startswith("(") and text.endswith(")") and _balanced(text):
        inner = text[1:-1].strip()
        if inner:
            return _translate_raw_expression(inner)

    if re.search(r"\|\|", text):
        parts = _split_top_level(text, "||")
        if len(parts) > 1:
            return "F.concat(" + ", ".join(_translate_concat_arg(part) for part in parts) + ")"

    for op in ("and", "or"):
        match = re.search(rf"\b{op}\b", text, flags=re.I)
        if match and _at_top_level(text, match.start()):
            parts = _split_top_level_keyword(text, op)
            if len(parts) == 2:
                left = _translate_raw_expression(parts[0])
                right = _translate_raw_expression(parts[1])
                return f"({left}) & ({right})" if op.lower() == "and" else f"({left}) | ({right})"

    for op in (">=", "<=", "==", "=", "!=", "<>", ">", "<"):
        match = re.search(re.escape(op), text)
        if match and _at_top_level(text, match.start()):
            parts = _split_top_level_operator(text, op)
            if len(parts) == 2:
                left = _translate_raw_expression(parts[0])
                right = _translate_raw_expression(parts[1])
                translated = op.replace("<>", "!=").replace("=", "==")
                return f"{left} {translated} {right}"

    for op in ("+", "-", "*", "/"):
        match = re.search(re.escape(op), text)
        if match and _at_top_level(text, match.start()):
            parts = _split_top_level_operator(text, op)
            if len(parts) == 2:
                left = _translate_raw_expression(parts[0])
                right = _translate_raw_expression(parts[1])
                return f"{left} {op} {right}"

    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_\.]*", text):
        return f'F.col({json.dumps(text)})'

    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", text):
        return text

    if re.fullmatch(r"(?:True|False)", text, flags=re.I):
        return str(text).lower() == "true"

    if re.fullmatch(r"(?:NULL|MISSING)", text, flags=re.I):
        return "F.lit(None)"

    if _is_quoted_literal(text):
        return _spark_string_literal(ast.literal_eval(text))

    match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)", text, flags=re.S)
    if match:
        name, args = match.groups()
        arg_parts = _split_arguments(args)
        mapped_args = [_translate_concat_arg(part) for part in arg_parts]
        lowered = name.lower()
        fn = {
            "abs": "F.abs",
            "ceil": "F.ceil",
            "floor": "F.floor",
            "lower": "F.lower",
            "upper": "F.upper",
            "trim": "F.trim",
            "length": "F.length",
            "concat": "F.concat",
        }.get(lowered)
        if fn:
            return f"{fn}({', '.join(mapped_args)})"
        return f"F.{lowered}({', '.join(mapped_args)})"

    return f"F.lit({text!r})"


def _translate_concat_arg(part: str) -> str:
    value = part.strip()
    if _is_quoted_literal(value):
        return _spark_string_literal(ast.literal_eval(value))
    return _translate_raw_expression(value)


def _split_top_level(expr: str, token: str) -> list[str]:
    pieces: list[str] = []
    current: list[str] = []
    depth = 0
    quote = None
    i = 0
    while i < len(expr):
        ch = expr[i]
        if quote is not None:
            current.append(ch)
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "'\"":
            quote = ch
            current.append(ch)
            i += 1
            continue
        if ch in "([":
            depth += 1
            current.append(ch)
            i += 1
            continue
        if ch in ")]":
            depth = max(0, depth - 1)
            current.append(ch)
            i += 1
            continue
        if depth == 0 and expr.startswith(token, i):
            pieces.append("".join(current).strip())
            current = []
            i += len(token)
            continue
        current.append(ch)
        i += 1
    pieces.append("".join(current).strip())
    return [piece for piece in pieces if piece]


def _split_top_level_keyword(expr: str, keyword: str) -> list[str]:
    regex = re.compile(rf"\b{re.escape(keyword)}\b", re.I)
    matches = list(regex.finditer(expr))
    if not matches:
        return [expr.strip()]
    parts: list[str] = []
    last = 0
    for match in matches:
        if _at_top_level(expr, match.start()):
            parts.append(expr[last:match.start()].strip())
            last = match.end()
    parts.append(expr[last:].strip())
    return [part for part in parts if part]


def _split_top_level_operator(expr: str, op: str) -> list[str]:
    pieces: list[str] = []
    current: list[str] = []
    depth = 0
    quote = None
    i = 0
    while i < len(expr):
        ch = expr[i]
        if quote is not None:
            current.append(ch)
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "'\"":
            quote = ch
            current.append(ch)
            i += 1
            continue
        if ch in "([":
            depth += 1
            current.append(ch)
            i += 1
            continue
        if ch in ")]":
            depth = max(0, depth - 1)
            current.append(ch)
            i += 1
            continue
        if depth == 0 and expr.startswith(op, i):
            pieces.append("".join(current).strip())
            current = []
            i += len(op)
            continue
        current.append(ch)
        i += 1
    pieces.append("".join(current).strip())
    return [piece for piece in pieces if piece]


def _split_arguments(expr: str) -> list[str]:
    if not expr.strip():
        return []
    args: list[str] = []
    current: list[str] = []
    depth = 0
    quote = None
    i = 0
    while i < len(expr):
        ch = expr[i]
        if quote is not None:
            current.append(ch)
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "'\"":
            quote = ch
            current.append(ch)
            i += 1
            continue
        if ch in "([":
            depth += 1
            current.append(ch)
            i += 1
            continue
        if ch in ")]":
            depth = max(0, depth - 1)
            current.append(ch)
            i += 1
            continue
        if depth == 0 and ch == ",":
            args.append("".join(current).strip())
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1
    args.append("".join(current).strip())
    return [part for part in args if part]


def _balanced(expr: str) -> bool:
    depth = 0
    quote = None
    for ch in expr:
        if quote is not None:
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _at_top_level(expr: str, index: int) -> bool:
    depth = 0
    quote = None
    for pos, ch in enumerate(expr):
        if quote is not None:
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if pos == index:
            return depth == 0
    return True


def _is_quoted_literal(value: str) -> bool:
    stripped = value.strip()
    return (stripped.startswith("'") and stripped.endswith("'")) or (stripped.startswith('"') and stripped.endswith('"'))
