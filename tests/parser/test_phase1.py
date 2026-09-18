from sas_parser.blocks import split_sections
from sas_parser.diagnostics import DiagnosticCollector
from sas_parser.lexer import SASLexer


SAMPLE_JOB = '''
%macro build;
proc sql;
create table out as
select * from src where a > 1;
quit;
%mend;

data work.stage;
set input_data;
where x >= 3;
run;
'''


def test_lexer_tokenizes_common_sas_tokens():
    tokens = SASLexer().tokenize("data work.stage; set input_data; where x >= 3;")

    token_values = [token.value for token in tokens]
    assert "DATA" in token_values
    assert "WORK" in token_values
    assert "SET" in token_values
    assert "WHERE" in token_values
    assert ">=" in token_values
    assert ";" in token_values


def test_split_sections_identifies_job_structure():
    sections = split_sections(SAMPLE_JOB)

    kinds = [section.kind for section in sections]
    assert "macro" in kinds
    assert "data_step" in kinds

    data_section = next(section for section in sections if section.kind == "data_step")
    assert "set input_data" in data_section.body.lower()


def test_diagnostic_collector_records_warnings():
    collector = DiagnosticCollector()
    collector.warn("Unsupported construct", detail="Macro body preserved as-is")

    assert len(collector.diagnostics) == 1
    assert collector.diagnostics[0].level == "warning"
    assert "Unsupported construct" in collector.diagnostics[0].message
