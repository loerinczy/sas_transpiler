from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class GenerationDiagnostic:
    level: str
    message: str
    code: Optional[str] = None
    dataset: Optional[str] = None
    node: Optional[object] = None
    source_text: Optional[str] = None


@dataclass
class GenerationConfig:
    function_name: str = "run_job"
    strict: bool = True


@dataclass
class GeneratedModule:
    source: str
    imports: List[str] = field(default_factory=list)
    diagnostics: List[GenerationDiagnostic] = field(default_factory=list)


class GenerationError(ValueError):
    def __init__(self, diagnostics: List[GenerationDiagnostic]) -> None:
        super().__init__("Cannot generate PySpark module from invalid ETL IR.")
        self.diagnostics = diagnostics
