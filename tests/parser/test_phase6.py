from src.sas_transpiler.sas_parser import lower_program, parse_program


SAMPLE = '''
data work.stage;
    set src_data;
    where a > 0;
    x = a + b;
run;

proc sql;
    create table out as
    select a.id, b.value, sum(c.amount) as total_amount
    from input_a as a
    left join input_b as b on a.id = b.id
    where a.id > 0
    group by a.id, b.value;
quit;
'''


def test_lower_program_creates_etl_ir_for_data_step_and_sql():
    program = parse_program(SAMPLE)
    job = lower_program(program)

    assert job.name.startswith("job") or job.name == "stage"
    assert any(ref.dataset == "src_data" for ref in job.inputs)
    assert any(ref.dataset == "input_a" for ref in job.inputs)
    assert any(ref.dataset == "input_b" for ref in job.inputs)
    assert any(filter.condition.value == "a > 0" for filter in job.filters)
    assert any(join.type == "left join" for join in job.joins)
    assert any(transform.target == "x" for transform in job.transforms)
    assert any(agg.group_by for agg in job.aggregates)
