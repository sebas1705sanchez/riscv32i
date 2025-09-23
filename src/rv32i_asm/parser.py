# src/rv32i_asm/parser.py
from __future__ import annotations
import re
from typing import List, Tuple, Optional, Union

from .lexer import (
    strip_comment,
    split_label,
    split_mnemonic_operands,
    split_operands,
)
from .ast import Label, Directive, Instruction, Reg, Imm, Sym, Mem, Operand
from .regs import normalize_reg, reg_num
from .diagnostics import error, Diagnostic

HEX_IMM_RE = re.compile(r"^[+-]?0x[0-9a-fA-F]+$")
DEC_IMM_RE = re.compile(r"^[+-]?\d+$")
SYMBOL_RE  = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MEM_RE     = re.compile(r"^(?P<off>[^(]+)?\(\s*(?P<base>[^)]+)\s*\)$")

def _parse_imm(token: str) -> Union[Imm, Sym]:
    t = token.strip()
    if HEX_IMM_RE.match(t) or DEC_IMM_RE.match(t):
        return Imm(int(t, 0), origin="numeric")
    if SYMBOL_RE.match(t):
        # Los operandos simbólicos se representan como Sym a nivel de instrucción
        return Sym(t)
    raise ValueError(f"Inmediato/símbolo inválido: {token}")

def _parse_reg(token: str) -> Reg:
    name = normalize_reg(token)
    return Reg(name=name, num=reg_num(name))

def _parse_mem(token: str) -> Mem:
    m = MEM_RE.match(token.strip())
    if not m:
        raise ValueError(f"Operando de memoria inválido: '{token}' (esperado imm(rs1) o (rs1))")
    off_raw = (m.group('off') or '0').strip()
    base_raw = m.group('base').strip()
    base = _parse_reg(base_raw)

    # offset puede ser numérico o simbólico; Mem.offset es Imm, por eso usamos Imm(origin="symbolic")
    if off_raw == '' or off_raw == '+':
        off = Imm(0, origin="numeric")
    else:
        if HEX_IMM_RE.match(off_raw) or DEC_IMM_RE.match(off_raw):
            off = Imm(int(off_raw, 0), origin="numeric")
        elif SYMBOL_RE.match(off_raw):
            off = Imm(0, origin="symbolic")
        else:
            raise ValueError(f"Desplazamiento inválido en operando de memoria: '{off_raw}'")
    return Mem(base=base, offset=off)

def parse(text: str, *, filename: Optional[str] = None) -> Tuple[List[Union[Label, Directive, Instruction]], List[Diagnostic]]:
    """
    Devuelve (nodes, diagnostics) donde nodes es una lista de:
      - Directive(name, args, line, col, section)
      - Label(name, line, col, section)
      - Instruction(mnemonic, operands, line, col, section)

    Reglas:
      - Comentarios: '#' o '//' hasta fin de línea.
      - Etiquetas: 'name:' al inicio de línea (permite 'name: .word ...' y 'name: instr ...').
      - Directivas: línea que empieza con '.' ('.text', '.data', '.equ', '.word', '.ascii', ...).
      - Instrucciones: resto (mnemónico + operandos).
    """
    nodes: List[Union[Label, Directive, Instruction]] = []
    diags: List[Diagnostic] = []
    section: Optional[str] = None  # '.text' o '.data'

    def _handle_directive_line(core: str, lineno: int) -> bool:
        nonlocal section
        """Procesa una línea que empieza por '.' y genera un Directive en nodes.
        Devuelve True si consumió la línea; False si no (no debería ocurrir)."""
        parts = core.split()
        if not parts:
            return True
        dname = parts[0].lower()
        args = parts[1:]
        # Cambios de sección
        if dname in ('.text', '.data'):
            nonlocal section
            section = dname
            nodes.append(Directive(name=dname, args=[], line=lineno, col=1, section=section))
            return True
        # .equ NAME, VALUE  o  .equ NAME VALUE
        if dname == '.equ':
            if len(args) < 2:
                diags.append(error(".equ requiere nombre y valor", line=lineno, file=filename))
                return True
            name = args[0].rstrip(',')
            if not SYMBOL_RE.match(name):
                diags.append(error("Nombre de .equ inválido", line=lineno, file=filename))
                return True
            val_tok = args[1].rstrip(',')
            try:
                val = int(val_tok, 0)
            except Exception:
                diags.append(error("Valor de .equ inválido", line=lineno, file=filename))
                return True
            nodes.append(Directive(name='.equ', args=[name, val], line=lineno, col=1, section=section))
            return True
        # Otras directivas (datos, alineación, etc.) -> se pasan con args crudos
        nodes.append(Directive(name=dname, args=args, line=lineno, col=1, section=section))
        return True

    lines = text.splitlines()
    for lineno, raw in enumerate(lines, start=1):
        core = strip_comment(raw)
        if not core:
            continue

        # 1) Línea que comienza con .directiva
        if core.startswith('.'):
            _handle_directive_line(core, lineno)
            continue

        # 2) 'label:' y 'label: <resto>'
        label, rest = split_label(core)
        if label:
            nodes.append(Label(name=label, line=lineno, col=1, section=section))
            if not rest:
                continue
            core = rest

            # >>> CAMBIO: si tras la etiqueta viene una directiva, manejarla como directiva
            if core.startswith('.'):
                _handle_directive_line(core, lineno)
                continue
            # <<< FIN CAMBIO

        # 3) Instrucción: mnemónico + operandos
        mnemonic, op_str = split_mnemonic_operands(core)
        if not mnemonic:
            continue

        operands: List[Operand] = []
        if op_str:
            ops = split_operands(op_str)
            for tok in ops:
                tok_s = tok.strip()
                # memoria imm(rs1) o (rs1)
                if '(' in tok_s and tok_s.endswith(')'):
                    try:
                        operands.append(_parse_mem(tok_s))
                        continue
                    except Exception:
                        diags.append(error(f"Operando inválido: '{tok_s}'", line=lineno, file=filename))
                        continue
                # registro
                try:
                    operands.append(_parse_reg(tok_s))
                    continue
                except Exception:
                    pass
                # inmediato o símbolo
                try:
                    val = _parse_imm(tok_s)
                    operands.append(val)
                    continue
                except Exception:
                    diags.append(error(f"Operando inválido: '{tok_s}'", line=lineno, file=filename))
                    continue

        nodes.append(Instruction(mnemonic=mnemonic.lower(), operands=operands, line=lineno, col=1, section=section))

    return nodes, diags
