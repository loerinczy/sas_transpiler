from src.sas_transpiler.sas_generator import generate_job
from src.sas_transpiler.sas_parser.models import Aggregate, Filter, Job, Join, Literal, SourceRef, TargetRef


def test_generate_job_emits_sql_join_filter_and_aggregate_pipeline():
    job = Job(
        name="sql_job",
        inputs=[SourceRef(dataset="input_a"), SourceRef(dataset="input_b")],
        outputs=[TargetRef(dataset="out")],
        filters=[Filter(condition=Literal("a.id > 0"))],
        joins=[Join(left="input_a", right="input_b", type="left join", condition=Literal("a.id = b.id"))],
        aggregates=[Aggregate(group_by=["a.id", "b.value"], measures=["sum(c.amount) as total_amount"])],
    )

    module = generate_job(job)

    assert 'df_input_a.alias("a")' in module.source
    assert 'df_input_b.alias("b")' in module.source
    assert 'join(df_input_b_alias, (F.col("a.id") == F.col("b.id")), how="left")' in module.source
    assert 'filter(F.col("a.id") > 0)' in module.source
    assert 'groupBy(F.col("a.id"), F.col("b.value"))' in module.source
    assert 'agg(F.sum(F.col("c.amount")).alias("total_amount"))' in module.source
    compile(module.source, "generated_sql_job.py", "exec")
