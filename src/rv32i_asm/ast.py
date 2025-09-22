'''
dataclases de AST (Instruction, Label, Directive, Operand)
'''

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Union, Optional, Literal

# ---- Nodos a nivel de fuente (AST/IR) ----

@dataclass(frozen=True)
class Label:
    """Etiqueta en el código fuente (p.ej., 'loop:')."""
    name: str
    line: int
    col: int
    section: Optional[str] = None    # '.text' o '.data'

@dataclass(frozen=True)
class Directive:
    """Directiva del ensamblador (p.ej., .text, .data, .equ)."""
    name: str
    args: List[Union[int, str, bytes]]
    line: int
    col: int
    section: Optional[str] = None

@dataclass(frozen=True)
class Instruction:
    """Instrucción con mnemónico y operandos tipados."""
    mnemonic: str
    operands: List['Operand']
    line: int
    col: int
    section: Optional[str] = None

# ---- Operandos ----

@dataclass(frozen=True)
class Reg:
    """Registro canónico 'xN' con su índice 0..31."""
    name: str   # 'xN'
    num: int    # 0..31

@dataclass(frozen=True)
class Imm:
    """Inmediato con origen: numérico (relativo en ramas) o simbólico (absoluto)."""
    value: int
    origin: Literal["numeric", "symbolic"] = "numeric"

@dataclass(frozen=True)
class Sym:
    """Símbolo (etiqueta) referenciado por una instrucción o directiva."""
    name: str

@dataclass(frozen=True)
class Mem:
    """Dirección base+desplazamiento: offset(rs1)."""
    base: Reg
    offset: Imm

Operand = Union[Reg, Imm, Sym, Mem]
