from sas_generator import generate_job
from sas_parser.models import Assignment, ColumnRef, FunctionCall, Job, Literal, SourceRef, TargetRef


def test_generate_job_translates_simple_expressions_into_spark_columns():
    job = Job(
        name="expression_job",
        inputs=[SourceRef(dataset="source_data")],
        outputs=[TargetRef(dataset="work.result")],
        transforms=[
            Assignment(target="total", expression=Literal("amount + tax")),
            Assignment(target="flag", expression=Literal("amount > 100 and tax > 0")),
        ],
    )

    module = generate_job(job)

    assert 'withColumn("total", F.col("amount") + F.col("tax"))' in module.source
    assert 'withColumn("flag", (F.col("amount") > 100) & (F.col("tax") > 0))' in module.source
    compile(module.source, "generated_expression_job.py", "exec")


def test_generate_job_supports_column_and_function_expressions():
    job = Job(
        name="function_job",
        inputs=[SourceRef(dataset="input_data")],
        outputs=[TargetRef(dataset="work.output")],
        transforms=[
            Assignment(target="amount_clean", expression=FunctionCall("abs", [ColumnRef("amount")])),
            Assignment(target="label", expression=Literal("region || '-' || city")),
        ],
    )

    module = generate_job(job)

    assert 'F.abs(F.col("amount"))' in module.source
    assert 'F.concat(F.col("region"), F.lit("-"), F.col("city"))' in module.source
