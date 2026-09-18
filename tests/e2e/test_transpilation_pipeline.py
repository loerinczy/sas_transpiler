from __future__ import annotations

import pytest

from src.sas_transpiler.sas_generator import GenerationError, GenerationConfig, generate_job
from src.sas_transpiler.sas_parser import Filter, lower_program, parse_program


MIXED_JOB = """
%let generated_by = di_studio;

data work.enriched;
    set source_data;
    where amount > 0;
    total = amount + tax;
run;

proc sql;
    create table work.summary as
    select a.customer_id, b.segment, sum(a.amount) as total_amount
    from sales as a
    left join customers as b on a.customer_id = b.customer_id
    where a.amount > 0
    group by a.customer_id, b.segment;
quit;
"""


def test_mixed_sas_job_lowers_and_generates_compilable_pyspark():
    program = parse_program(MIXED_JOB)
    job = lower_program(program)
    module = generate_job(job)

    assert [section.kind for section in program.sections] == ["data_step", "proc_sql"]
    assert {source.dataset for source in job.inputs} == {
        "source_data",
        "sales",
        "customers",
    }
    assert {target.dataset for target in job.outputs} == {"work.summary"}
    assert any(transform.target == "total" for transform in job.transforms)
    assert any(filter_step.condition.value == "amount > 0" for filter_step in job.filters)
    assert job.joins[0].type == "left join"
    assert job.aggregates[0].group_by == [
        "a.customer_id, b.segment",
        "a.customer_id",
        "b.segment",
    ]
    assert 'outputs["work.summary"]' in module.source
    assert 'join(df_customers_alias' in module.source
    assert 'groupBy(F.col("customer_id, b.segment")' in module.source
    compile(module.source, "generated_mixed_job.py", "exec")


def test_data_step_only_job_preserves_input_filter_transform_and_default_output():
    program = parse_program(
        """
        data work.cleaned;
            set raw.events;
            where status = 'active';
            normalized = amount * 100;
        run;
        """
    )

    job = lower_program(program)
    module = generate_job(job)

    assert [source.dataset for source in job.inputs] == ["raw.events"]
    assert job.outputs == []
    assert job.filters[0].condition.value == "status = 'active'"
    assert job.transforms[0].target == "normalized"
    assert "outputs['output'] = df_working" in module.source
    compile(module.source, "generated_data_step_job.py", "exec")


def test_macro_and_metadata_are_preserved_without_being_lowered_as_etl_logic():
    program = parse_program(
        """
        /* DI Studio metadata */
        %macro build(input=source, output=target);
            %let run_mode = batch;
            %include "setup.sas";
        %mend;
        """
    )

    assert len(program.sections) == 1
    assert program.sections[0].kind == "macro"
    assert program.sections[0].name == "build"
    assert {statement.kind for statement in program.sections[0].statements} == {
        "macro_declaration",
        "macro_assignment",
        "macro_include",
    }

    job = lower_program(program)
    module = generate_job(job)

    assert job.inputs == []
    assert job.outputs == []
    assert "createDataFrame" in module.source
    compile(module.source, "generated_macro_only_job.py", "exec")


def test_dynamic_sql_references_reach_generator_as_warnings():
    program = parse_program(
        """
        proc sql;
            create table output%macro as
            select * from input%macro;
        quit;
        """
    )

    job = lower_program(program)
    module = generate_job(job)

    assert [source.dataset for source in job.inputs] == ["input%macro"]
    assert [target.dataset for target in job.outputs] == ["output%macro"]
    assert [diagnostic.code for diagnostic in module.diagnostics] == [
        "NameResolutionError",
        "NameResolutionError",
        "MissingDependency",
    ]
    compile(module.source, "generated_dynamic_job.py", "exec")


def test_invalid_lowered_ir_fails_generation_in_strict_mode():
    program = parse_program(
        """
        data work.invalid;
            set source_data;
            broken = ;
        run;
        """
    )
    job = lower_program(program)
    job.filters.append(Filter(condition=None))

    with pytest.raises(GenerationError) as error:
        generate_job(job, config=GenerationConfig(strict=True))

    assert any(diagnostic.code == "InvalidIR" for diagnostic in error.value.diagnostics)