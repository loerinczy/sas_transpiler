from src.sas_transpiler.sas_generator import generate_job
from src.sas_transpiler.sas_parser import lower_program, parse_program


SAS_JOB = """
proc sql;
    create table work.customer_totals as
    select a.customer_id, sum(b.amount) as total_amount
    from source.customers as a
    left join source.orders as b on a.customer_id = b.customer_id
    where a.active = 1
    group by a.customer_id;
quit;
"""


def test_sql_join_filter_and_aggregate_are_generated_end_to_end():
    job = lower_program(parse_program(SAS_JOB))

    module = generate_job(job)

    assert [ref.dataset for ref in job.inputs] == ["source.customers", "source.orders"]
    assert job.outputs[0].dataset == "work.customer_totals"
    assert job.joins[0].type == "left join"
    assert job.aggregates[0].measures == ["sum(b.amount) as total_amount"]
    assert 'df_source_customers_alias = df_source_customers.alias("customers")' in module.source
    assert 'df_source_orders_alias = df_source_orders.alias("orders")' in module.source
    assert 'join(df_source_orders_alias, (F.col("a.customer_id") == F.col("b.customer_id")), how="left")' in module.source
    assert 'df_working = df_working.filter(F.col("a.active") == 1)' in module.source
    assert 'F.sum(F.col("b.amount")).alias("total_amount")' in module.source
    assert 'outputs["work.customer_totals"] = df_work_customer_totals' in module.source
    compile(module.source, "generated_sql_job.py", "exec")