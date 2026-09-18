from sas_generator import generate_job
from sas_parser import lower_program, parse_program


SAS_JOB = """
data work.enriched;
    set raw.orders;
    where amount > 0;
    total = amount + tax;
run;
"""


def test_data_step_is_parsed_lowered_and_generated_end_to_end():
    job = lower_program(parse_program(SAS_JOB))

    module = generate_job(job)

    assert [ref.dataset for ref in job.inputs] == ["raw.orders"]
    assert job.filters[0].condition.value == "amount > 0"
    assert job.transforms[0].target == "total"
    assert 'df_raw_orders = sources["raw.orders"]' in module.source
    assert 'df_working = df_working.filter(F.col("amount") > 0)' in module.source
    assert 'df_working = df_working.withColumn("total", F.col("amount") + F.col("tax"))' in module.source
    assert "outputs['output'] = df_working" in module.source
    compile(module.source, "generated_data_step_job.py", "exec")