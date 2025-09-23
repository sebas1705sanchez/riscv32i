from __future__ import annotations
import re
from typing import List, Tuple, Dict, Optional, Union
from .lexer import strip_comment, split_label, is_directive, split_mnemonic_operands, split_operands
from .ast import Label, Directive, Instruction, Reg, Imm, Sym, Mem, Operand
from .regs import normalize_reg, reg_num
from .diagnostics import error, Diagnostic

HEX_IMM_RE = re.compile(r"^[+-]?0x[0-9a-fA-F]+$")
DEC_IMM_RE = re.compile(r"^[+-]?\d+$")
SYMBOL_RE  = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MEM_RE     = re.compile(r"^(?P<off>[^(]+)?\(\s*(?P<base>[^)]+)\s*\)$")

def _parse_imm(token: str) -> Imm | Sym:
    t = token.strip()
    if HEX_IMM_RE.match(t) or DEC_IMM_RE.match(t):
        return Imm(int(t, 0), origin="numeric")
    if SYMBOL_RE.match(t):
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
    # offset puede ser número o símbolo
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
    nodes: List[Union[Label, Directive, Instruction]] = []
    diags: List[Diagnostic] = []
    section: Optional[str] = None  # '.text' o '.data'

    lines = text.splitlines()
    for lineno, raw in enumerate(lines, start=1):
        core = strip_comment(raw)
        if not core:
            continue

        # .directivas primero
        if core.startswith('.'):
            parts = core.split()
            dname = parts[0].lower()
            args = parts[1:]
            if dname in ('.text', '.data'):
                section = dname
                nodes.append(Directive(name=dname, args=[], line=lineno, col=1, section=section))
                continue
            if dname == '.equ':
                # .equ name, value   o   .equ name value
                if len(args) == 0:
                    diags.append(error(".equ requiere nombre y valor", line=lineno, file=filename))
                    continue
                name = args[0].rstrip(',')
                if not name or not SYMBOL_RE.match(name):
                    diags.append(error("Nombre de .equ inválido", line=lineno, file=filename))
                    continue
                val_tok = args[1] if len(args) > 1 else None
                if val_tok is None and len(args) >= 2:
                    val_tok = args[1]
                elif val_tok is None and len(args) == 1:
                    diags.append(error("Falta valor en .equ", line=lineno, file=filename))
                    continue
                try:
                    val = int(val_tok.rstrip(','), 0)
                except Exception:
                    diags.append(error("Valor de .equ inválido", line=lineno, file=filename))
                    continue
                nodes.append(Directive(name='.equ', args=[name, val], line=lineno, col=1, section=section))
                continue
            # otras directivas: ignorar pero registrar
            nodes.append(Directive(name=dname, args=args, line=lineno, col=1, section=section))
            continue

        # Soporta 'label:' y 'label: instr ...'
        label, rest = split_label(core)
        if label:
            nodes.append(Label(name=label, line=lineno, col=1, section=section))
            if not rest:
                continue  # solo etiqueta en la línea
            core = rest

        # instrucción
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
                    except Exception as ex:
                        diags.append(error(str(ex), line=lineno, file=filename))
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
                    if isinstance(val, (Imm, Sym)):
                        operands.append(val)
                        continue
                except Exception:
                    pass
                diags.append(error(f"Operando inválido: '{tok_s}'", line=lineno, file=filename))
        nodes.append(Instruction(mnemonic=mnemonic, operands=operands, line=lineno, col=1, section=section))

    return nodes, diags
