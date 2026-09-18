from sas_parser import parse_program


SAMPLE = '''
data work.temp;
    x = a + b;
    if a > 0 then do;
        y = x * 2;
    end;
    else do;
        y = 0;
    end;
run;

proc sql;
    create table out as
    select a, b, sum(c) as total
    from src
    where a > 1
    group by a, b;
quit;
'''


def test_parse_program_extracts_statement_order_and_sql_clause_types():
    program = parse_program(SAMPLE)

    assert len(program.sections) >= 2
    assert any(section.kind == "data_step" for section in program.sections)
    assert any(section.kind == "proc_sql" for section in program.sections)

    data_section = next(section for section in program.sections if section.kind == "data_step")
    assert len(data_section.statements) >= 2
    assert any(stmt.kind == "assignment" for stmt in data_section.statements)
    assert any(stmt.kind == "if" for stmt in data_section.statements)
    assert "x = a + b" in data_section.body
    assert "if a > 0 then do" in data_section.body.lower()

    sql_section = next(section for section in program.sections if section.kind == "proc_sql")
    assert sql_section.statements
    assert sql_section.statements[0].kind == "sql_query"
    assert sql_section.statements[0].select_columns
    assert "src" in sql_section.statements[0].from_tables
    assert "a > 1" in sql_section.statements[0].where_condition
    assert any(col in sql_section.statements[0].group_by for col in ["a", "b", "a, b"])
    assert "select a, b, sum(c) as total" in sql_section.body.lower()
    assert "from src" in sql_section.body.lower()
    assert "group by a, b" in sql_section.body.lower()
