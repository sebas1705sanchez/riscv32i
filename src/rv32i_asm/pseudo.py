from __future__ import annotations
from typing import List, Union
from .ast import Instruction, Label, Directive, Reg, Imm, Sym, Mem, Operand

def _rx(n: int) -> Reg: return Reg(name=f"x{n}", num=n)
X0=_rx(0); RA=_rx(1); T0=_rx(5); T1=_rx(6)

LOADS={"lb","lh","lw","lbu","lhu"}
STORES={"sb","sh","sw"}

def _copy(ins: Instruction, mnemonic: str, ops: list[Operand]) -> Instruction:
    return Instruction(mnemonic=mnemonic, operands=ops, line=ins.line, col=ins.col, section=ins.section)

def _sym_suffix(sym: Sym, suffix: str) -> Sym: return Sym(name=f"{sym.name}@{suffix}")

def _as_reg(op: Operand) -> Reg:
    assert isinstance(op, Reg), f"Se esperaba registro, obtuve {op!r}"
    return op
def _as_imm_or_sym(op: Operand): 
    assert isinstance(op, (Imm, Sym)), f"Se esperaba inmediato o símbolo, obtuve {op!r}"
    return op

def _fits_i12(v: int) -> bool: return -2048 <= v <= 2047

def _li_expand(ins: Instruction) -> list[Instruction]:
    rd = _as_reg(ins.operands[0])
    op1 = ins.operands[1]
    if isinstance(op1, Sym):
        return [_copy(ins,"auipc",[rd,_sym_suffix(op1,"pcrel_hi")]), _copy(ins,"addi",[rd,rd,_sym_suffix(op1,"pcrel_lo")])]
    assert isinstance(op1, Imm)
    v = op1.value
    if _fits_i12(v): return [_copy(ins,"addi",[rd,X0,Imm(v)])]
    upper = (v + 0x800) >> 12
    low   = v - (upper << 12)
    return [_copy(ins,"lui",[rd,Imm(upper)]), _copy(ins,"addi",[rd,rd,Imm(low)])]

def _la_expand(ins: Instruction) -> list[Instruction]:
    rd = _as_reg(ins.operands[0]); sym = ins.operands[1]
    assert isinstance(sym, Sym), "la requiere símbolo"
    return [_copy(ins,"auipc",[rd,_sym_suffix(sym,"pcrel_hi")]), _copy(ins,"addi",[rd,rd,_sym_suffix(sym,"pcrel_lo")])]

def _call_expand(ins: Instruction) -> list[Instruction]:
    op = ins.operands[0]
    if isinstance(op, Sym):
        return [_copy(ins,"auipc",[RA,_sym_suffix(op,"pcrel_hi")]), _copy(ins,"jalr",[RA,RA,_sym_suffix(op,"pcrel_lo")])]
    assert isinstance(op, Imm)
    return [_copy(ins,"jal",[RA,op])]

def _tail_expand(ins: Instruction) -> list[Instruction]:
    op = ins.operands[0]
    if isinstance(op, Sym):
        return [_copy(ins,"auipc",[T1,_sym_suffix(op,"pcrel_hi")]), _copy(ins,"jalr",[X0,T1,_sym_suffix(op,"pcrel_lo")])]
    assert isinstance(op, Imm)
    return [_copy(ins,"jal",[X0,op])]

def expand(nodes: list[Union[Label,Directive,Instruction]]) -> list[Union[Label,Directive,Instruction]]:
    out: list[Union[Label,Directive,Instruction]] = []
    for n in nodes:
        if not isinstance(n, Instruction): out.append(n); continue
        m = n.mnemonic.lower(); ops = n.operands

        if m == "nop" and len(ops) == 0: out.append(_copy(n,"addi",[X0,X0,Imm(0)])); continue
        if m == "mv"  and len(ops) == 2: rd,rs=_as_reg(ops[0]),_as_reg(ops[1]); out.append(_copy(n,"addi",[rd,rs,Imm(0)])); continue
        if m == "not" and len(ops) == 2: rd,rs=_as_reg(ops[0]),_as_reg(ops[1]); out.append(_copy(n,"xori",[rd,rs,Imm(-1)])); continue
        if m == "neg" and len(ops) == 2: rd,rs=_as_reg(ops[0]),_as_reg(ops[1]); out.append(_copy(n,"sub",[rd,X0,rs])); continue
        if m == "seqz" and len(ops)==2: rd,rs=_as_reg(ops[0]),_as_reg(ops[1]); out.append(_copy(n,"sltiu",[rd,rs,Imm(1)])); continue
        if m == "snez" and len(ops)==2: rd,rs=_as_reg(ops[0]),_as_reg(ops[1]); out.append(_copy(n,"sltu",[rd,X0,rs])); continue
        if m == "sltz" and len(ops)==2: rd,rs=_as_reg(ops[0]),_as_reg(ops[1]); out.append(_copy(n,"slt",[rd,rs,X0])); continue
        if m == "sgtz" and len(ops)==2: rd,rs=_as_reg(ops[0]),_as_reg(ops[1]); out.append(_copy(n,"slt",[rd,X0,rs])); continue

        if m == "beqz" and len(ops)==2: rs,off=_as_reg(ops[0]),_as_imm_or_sym(ops[1]); out.append(_copy(n,"beq",[rs,X0,off])); continue
        if m == "bnez" and len(ops)==2: rs,off=_as_reg(ops[0]),_as_imm_or_sym(ops[1]); out.append(_copy(n,"bne",[rs,X0,off])); continue
        if m == "blez" and len(ops)==2: rs,off=_as_reg(ops[0]),_as_imm_or_sym(ops[1]); out.append(_copy(n,"bge",[X0,rs,off])); continue
        if m == "bgez" and len(ops)==2: rs,off=_as_reg(ops[0]),_as_imm_or_sym(ops[1]); out.append(_copy(n,"bge",[rs,X0,off])); continue
        if m == "bltz" and len(ops)==2: rs,off=_as_reg(ops[0]),_as_imm_or_sym(ops[1]); out.append(_copy(n,"blt",[rs,X0,off])); continue
        if m == "bgtz" and len(ops)==2: rs,off=_as_reg(ops[0]),_as_imm_or_sym(ops[1]); out.append(_copy(n,"blt",[X0,rs,off])); continue

        if m == "bgt"  and len(ops)==3: rs,rt,off=_as_reg(ops[0]),_as_reg(ops[1]),_as_imm_or_sym(ops[2]); out.append(_copy(n,"blt",[rt,rs,off])); continue
        if m == "ble"  and len(ops)==3: rs,rt,off=_as_reg(ops[0]),_as_reg(ops[1]),_as_imm_or_sym(ops[2]); out.append(_copy(n,"bge",[rt,rs,off])); continue
        if m == "bgtu" and len(ops)==3: rs,rt,off=_as_reg(ops[0]),_as_reg(ops[1]),_as_imm_or_sym(ops[2]); out.append(_copy(n,"bltu",[rt,rs,off])); continue
        if m == "bleu" and len(ops)==3: rs,rt,off=_as_reg(ops[0]),_as_reg(ops[1]),_as_imm_or_sym(ops[2]); out.append(_copy(n,"bgeu",[rt,rs,off])); continue

        if m == "j"   and len(ops)==1: out.append(_copy(n,"jal",[X0,_as_imm_or_sym(ops[0]) ])); continue
        if m == "jal" and len(ops)==1: out.append(_copy(n,"jal",[RA,_as_imm_or_sym(ops[0]) ])); continue
        if m == "jr"  and len(ops)==1: rs=_as_reg(ops[0]); out.append(_copy(n,"jalr",[X0,rs,Imm(0)])); continue
        if m == "jalr" and len(ops)==1: rs=_as_reg(ops[0]); out.append(_copy(n,"jalr",[RA,rs,Imm(0)])); continue
        if m == "ret" and len(ops)==0: out.append(_copy(n,"jalr",[X0,RA,Imm(0)])); continue

        if m == "li"  and len(ops)==2: out.extend(_li_expand(n)); continue
        if m == "la"  and len(ops)==2: out.extend(_la_expand(n)); continue
        if m == "call" and len(ops)==1: out.extend(_call_expand(n)); continue
        if m == "tail" and len(ops)==1: out.extend(_tail_expand(n)); continue

        if m in LOADS and len(ops)==2 and isinstance(ops[1], Sym):
            sym=ops[1]; rd=_as_reg(ops[0])
            out.extend(_la_expand(_copy(n,"la",[rd,sym])))
            out.append(_copy(n,m,[rd,Mem(base=rd, offset=Imm(0))])); continue

        if m in STORES and len(ops)==2 and isinstance(ops[1], Sym):
            sym=ops[1]; rs2=_as_reg(ops[0])
            out.extend(_la_expand(_copy(n,"la",[T0,sym])))
            out.append(_copy(n,m,[rs2,Mem(base=T0, offset=Imm(0))])); continue

        out.append(n)
    return out
