from src.sas_transpiler.sas_parser import parse_program


SAMPLE = '''
data work.stage;
    set src_data;
    where a > 0;
    keep col_a col_b;
    rename col_a = a_new;
    x = a + b;
run;
'''


def test_parse_program_tracks_data_step_keywords_and_assignments():
    program = parse_program(SAMPLE)
    data_section = next(section for section in program.sections if section.kind == "data_step")

    kinds = {stmt.kind for stmt in data_section.statements}
    assert "set" in kinds
    assert "where" in kinds
    assert "keep_drop" in kinds
    assert "rename" in kinds
    assert "assignment" in kinds

    set_stmt = next(stmt for stmt in data_section.statements if stmt.kind == "set")
    assert "src_data" in set_stmt.text.lower()

    where_stmt = next(stmt for stmt in data_section.statements if stmt.kind == "where")
    assert "a > 0" in where_stmt.condition

    keep_stmt = next(stmt for stmt in data_section.statements if stmt.kind == "keep_drop")
    assert "keep" in keep_stmt.text.lower()

    rename_stmt = next(stmt for stmt in data_section.statements if stmt.kind == "rename")
    assert "col_a" in rename_stmt.text.lower()
    assert "a_new" in rename_stmt.text.lower()
