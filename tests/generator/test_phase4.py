from sas_generator import generate_job
from sas_parser.models import Assignment, Filter, Job, Literal, SourceRef, TargetRef


def test_generate_job_applies_filters_before_transformations():
    job = Job(
        name="filtered_stage_job",
        inputs=[SourceRef(dataset="source_data")],
        outputs=[TargetRef(dataset="work.result")],
        filters=[Filter(condition=Literal("amount > 0"))],
        transforms=[Assignment(target="total", expression=Literal("amount + tax"))],
    )

    module = generate_job(job)

    assert 'df_working = df_source_data' in module.source
    assert 'df_working = df_working.filter(F.col("amount") > 0)' in module.source
    assert 'df_working = df_working.withColumn("total", F.col("amount") + F.col("tax"))' in module.source
    assert 'outputs["work.result"] = df_work_result' in module.source
