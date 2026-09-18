from src.sas_transpiler.sas_generator import generate_job
from src.sas_transpiler.sas_parser.models import Assignment, Job, Literal, SourceRef, TargetRef


def test_generate_job_resolves_runtime_source_mapping_and_output_binding():
    job = Job(
        name="stage_job",
        inputs=[SourceRef(dataset="source_data"), SourceRef(dataset="work.stage")],
        outputs=[TargetRef(dataset="work.final_stage")],
        transforms=[Assignment(target="total", expression=Literal("amount"))],
    )

    module = generate_job(job)

    assert 'if "source_data" not in sources:' in module.source
    assert 'df_source_data = sources["source_data"]' in module.source
    assert 'df_work_stage = sources["work.stage"]' in module.source
    assert 'outputs["work.final_stage"] = df_work_final_stage' in module.source


def test_generate_job_sanitizes_collisions_and_reserved_names():
    job = Job(
        name="collision_job",
        inputs=[SourceRef(dataset="class"), SourceRef(dataset="class"), SourceRef(dataset="123abc")],
        outputs=[TargetRef(dataset="class")],
        transforms=[Assignment(target="total", expression=Literal("amount"))],
    )

    module = generate_job(job)

    assert 'df_class = sources["class"]' in module.source
    assert 'df_class_2 = sources["class"]' in module.source
    assert 'df_123abc = sources["123abc"]' in module.source
