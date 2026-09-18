from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Diagnostic:
    level: str
    message: str
    detail: Optional[str] = None
    code: Optional[str] = None


class DiagnosticCollector:
    def __init__(self) -> None:
        self.diagnostics: List[Diagnostic] = []

    def warn(self, message: str, detail: Optional[str] = None, code: Optional[str] = None) -> Diagnostic:
        diag = Diagnostic(level="warning", message=message, detail=detail, code=code)
        self.diagnostics.append(diag)
        return diag

    def error(self, message: str, detail: Optional[str] = None, code: Optional[str] = None) -> Diagnostic:
        diag = Diagnostic(level="error", message=message, detail=detail, code=code)
        self.diagnostics.append(diag)
        return diag

    def info(self, message: str, detail: Optional[str] = None, code: Optional[str] = None) -> Diagnostic:
        diag = Diagnostic(level="info", message=message, detail=detail, code=code)
        self.diagnostics.append(diag)
        return diag

    def clear(self) -> None:
        self.diagnostics.clear()
