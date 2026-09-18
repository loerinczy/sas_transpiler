from sas_parser import parse_program


SAMPLE = '''
%macro build_job(input=src, output=final);
%let job_name = demo_job;
%include "pipeline/setup.sas";
proc sql;
    create table &output as
    select * from &input;
quit;
%mend;
'''


def test_parse_program_preserves_macro_wrappers_and_metadata():
    program = parse_program(SAMPLE)
    macro_section = next(section for section in program.sections if section.kind == "macro")

    assert macro_section.name == "build_job"
    assert macro_section.statements
    assert any(stmt.kind == "macro_declaration" for stmt in macro_section.statements)
    assert any(stmt.kind == "macro_assignment" for stmt in macro_section.statements)
    assert any(stmt.kind == "macro_include" for stmt in macro_section.statements)
    assert "%macro build_job" in macro_section.body
    assert "&output" in macro_section.body
