import pytest

from sas_generator import GenerationError, generate_job, validate_job
from sas_parser.models import Assignment, Job, Literal, SourceRef, TargetRef


def test_generate_job_emits_a_deterministic_compilable_module():
    job = Job(
        name="stage_job",
        inputs=[SourceRef(dataset="source_data")],
        outputs=[TargetRef(dataset="work.stage")],
        transforms=[Assignment(target="total", expression=Literal("amount + tax"))],
    )

    first_module = generate_job(job)
    second_module = generate_job(job)

    assert first_module.source == second_module.source
    assert "from pyspark.sql import DataFrame, SparkSession" in first_module.source
    assert "def run_job(spark: SparkSession, sources: dict[str, DataFrame], runtime=None)" in first_module.source
    compile(first_module.source, "generated_stage_job.py", "exec")


def test_validate_job_reports_invalid_references_and_assignments():
    job = Job(
        inputs=[SourceRef(dataset="")],
        outputs=[TargetRef(dataset="")],
        transforms=[Assignment(target="", expression=None)],
    )

    diagnostics = validate_job(job)

    assert [diagnostic.code for diagnostic in diagnostics] == ["InvalidIR", "InvalidIR", "InvalidIR"]
    with pytest.raises(GenerationError):
        generate_job(job)


def test_non_strict_generation_returns_invalid_ir_diagnostics():
    module = generate_job(Job(inputs=[SourceRef(dataset="")]), config=__import__("sas_generator").GenerationConfig(strict=False))

    assert module.diagnostics[0].code == "InvalidIR"
    compile(module.source, "generated_partial_job.py", "exec")