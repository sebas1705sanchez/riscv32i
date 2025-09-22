'''
clase Diagnostic y helpers (línea/columna, tipos de error)
'''

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Literal

# Severidad de los diagnósticos (en español)
Severity = Literal["error", "advertencia", "nota"]

_SEV_TO_LABEL = {
    "error": "ERROR",
    "advertencia": "ADVERTENCIA",
    "nota": "NOTA",
}

@dataclass(frozen=True)
class Diagnostic:
    """Estructura de un diagnóstico para reportar problemas.

    Abarca errores, advertencias y notas, con ubicación opcional (archivo, línea y columna)
    y un mensaje de ayuda (pista) para orientar la corrección.
    """
    severity: Severity
    message: str
    line: Optional[int] = None
    col: Optional[int] = None
    hint: Optional[str] = None
    file: Optional[str] = None

    def __str__(self) -> str:
        loc = ""
        if self.file is not None:
            loc += f"{self.file}:"
        if self.line is not None:
            loc += f"{self.line}"
            if self.col is not None:
                loc += f":{self.col}"
        if loc:
            loc += ": "
        sev = _SEV_TO_LABEL.get(self.severity, str(self.severity).upper())
        core = f"{sev}: {self.message}"
        if self.hint:
            core += f"  (pista: {self.hint})"
        return loc + core

def error(message: str, *, line: int | None = None, col: int | None = None,
          file: str | None = None, hint: str | None = None) -> Diagnostic:
    """Crea un diagnóstico de tipo error."""
    return Diagnostic("error", message, line, col, hint, file)

def warning(message: str, *, line: int | None = None, col: int | None = None,
            file: str | None = None, hint: str | None = None) -> Diagnostic:
    """Crea un diagnóstico de tipo advertencia."""
    return Diagnostic("advertencia", message, line, col, hint, file)

def note(message: str, *, line: int | None = None, col: int | None = None,
         file: str | None = None, hint: str | None = None) -> Diagnostic:
    """Crea un diagnóstico de tipo nota."""
    return Diagnostic("nota", message, line, col, hint, file)
