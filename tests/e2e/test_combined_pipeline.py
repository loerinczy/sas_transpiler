from sas_generator import generate_job
from sas_parser import lower_program, parse_program


SAS_JOB = """
data work.prepared;
    set source.transactions;
    where amount > 0;
    net_amount = amount - fee;
run;

proc sql;
    create table work.final as
    select p.account_id, sum(r.net_amount) as total_net
    from work.prepared as p
    inner join source.risk as r on p.account_id = r.account_id
    group by p.account_id;
quit;
"""


def test_data_step_and_sql_sections_flow_through_one_generated_job():
    job = lower_program(parse_program(SAS_JOB))

    module = generate_job(job)

    assert [ref.dataset for ref in job.inputs] == ["source.transactions", "work.prepared", "source.risk"]
    assert job.transforms[0].target == "net_amount"
    assert job.joins[0].type == "inner join"
    assert job.outputs[0].dataset == "work.final"
    assert 'df_source_transactions = sources["source.transactions"]' in module.source
    assert 'df_work_prepared = sources["work.prepared"]' in module.source
    assert 'df_source_risk = sources["source.risk"]' in module.source
    assert 'df_working = df_working.withColumn("net_amount", F.col("amount") - F.col("fee"))' in module.source
    assert 'outputs["work.final"] = df_work_final' in module.source
    compile(module.source, "generated_combined_job.py", "exec")