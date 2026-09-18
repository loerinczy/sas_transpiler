from __future__ import annotations

from typing import List

from sas_parser.models import Assignment, Filter, Job, SourceRef, TargetRef

from .models import GenerationDiagnostic


def _looks_dynamic_dataset_name(value: str) -> bool:
    normalized = (value or "").strip()
    return any(token in normalized for token in ("%", "&", "${", "}", ".."))


def validate_job(job: Job) -> List[GenerationDiagnostic]:
    diagnostics: List[GenerationDiagnostic] = []

    if not isinstance(job, Job):
        return [
            GenerationDiagnostic(
                level="error",
                message="Generator input must be a Job.",
                code="InvalidIR",
            )
        ]

    source_names = [source.dataset.strip() for source in job.inputs if isinstance(source, SourceRef)]

    for source in job.inputs:
        if not isinstance(source, SourceRef) or not source.dataset.strip():
            diagnostics.append(
                GenerationDiagnostic(
                    level="error",
                    message="Each input must be a SourceRef with a dataset name.",
                    code="InvalidIR",
                    dataset=getattr(source, "dataset", None),
                )
            )
            continue

        if _looks_dynamic_dataset_name(source.dataset):
            diagnostics.append(
                GenerationDiagnostic(
                    level="warning",
                    message=f"Input dataset reference '{source.dataset}' appears macro-generated or unresolved.",
                    code="NameResolutionError",
                    dataset=source.dataset,
                )
            )

    for target in job.outputs:
        if not isinstance(target, TargetRef) or not target.dataset.strip():
            diagnostics.append(
                GenerationDiagnostic(
                    level="error",
                    message="Each output must be a TargetRef with a dataset name.",
                    code="InvalidIR",
                    dataset=getattr(target, "dataset", None),
                )
            )
            continue

        if _looks_dynamic_dataset_name(target.dataset):
            diagnostics.append(
                GenerationDiagnostic(
                    level="warning",
                    message=f"Output dataset reference '{target.dataset}' appears macro-generated or unresolved.",
                    code="NameResolutionError",
                    dataset=target.dataset,
                )
            )

        if target.dataset.strip() not in source_names and source_names:
            diagnostics.append(
                GenerationDiagnostic(
                    level="warning",
                    message=f"Output dataset '{target.dataset}' is not backed by a matching source dependency.",
                    code="MissingDependency",
                    dataset=target.dataset,
                )
            )

    for filter_step in job.filters:
        if not isinstance(filter_step, Filter) or filter_step.condition is None:
            diagnostics.append(
                GenerationDiagnostic(
                    level="error",
                    message="Each filter must be a Filter with a condition.",
                    code="InvalidIR",
                    dataset=getattr(filter_step, "condition", None),
                )
            )

    for transform in job.transforms:
        if not isinstance(transform, Assignment) or not transform.target.strip() or transform.expression is None:
            diagnostics.append(
                GenerationDiagnostic(
                    level="error",
                    message="Each transform must be an Assignment with a target and expression.",
                    code="InvalidIR",
                    dataset=getattr(transform, "target", None),
                )
            )

    return diagnostics