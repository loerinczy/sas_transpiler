from sas_parser import parse_program


SAMPLE = '''
proc sql;
    create table out as
    select a.id, b.value, sum(c.amount) as total_amount
    from input_a as a
    left join input_b as b on a.id = b.id
    where a.id > 0
    group by a.id, b.value;
quit;
'''


def test_parse_program_extracts_sql_query_blocks_with_joins_and_aggregates():
    program = parse_program(SAMPLE)
    sql_section = next(section for section in program.sections if section.kind == "proc_sql")

    stmt = sql_section.statements[0]
    assert stmt.kind == "sql_query"
    assert "a.id" in stmt.select_columns
    assert "b.value" in stmt.select_columns
    assert "total_amount" in " ".join(stmt.select_columns)
    assert "input_a" in stmt.from_tables
    assert "input_b" in stmt.from_tables
    assert "a.id > 0" in stmt.where_condition
    assert "a.id" in " ".join(stmt.group_by)
    assert "left join" in stmt.join_type.lower()
