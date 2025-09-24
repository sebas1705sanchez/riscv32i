# src/rv32i_asm/encoding.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

from .ast import Instruction, Directive, Label, Reg, Imm, Sym, Mem, Operand
from .isa import spec as isa_spec
from .utils import u32, is_signed_nbit, is_unsigned_nbit
from .diagnostics import Diagnostic, error, warning

# ---------------- Resultados de codificación ----------------

@dataclass(frozen=True)
class Encoded:
    word: int     # u32
    pc: int       # dirección de esta instrucción
    line: int
    col: int
    mnemonic: str

@dataclass(frozen=True)
class EncodeResult:
    words: List[Encoded]
    diagnostics: List[Diagnostic]

# ---------------- Helpers de empaquetado de bits ----------------

def _pack_R(f7: int, rs2: int, rs1: int, f3: int, rd: int, opc: int) -> int:
    return u32((f7 & 0x7F) << 25 |
               (rs2 & 0x1F) << 20 |
               (rs1 & 0x1F) << 15 |
               (f3 & 0x7)  << 12 |
               (rd & 0x1F) << 7  |
               (opc & 0x7F))

def _pack_I(imm12: int, rs1: int, f3: int, rd: int, opc: int) -> int:
    return u32((imm12 & 0xFFF) << 20 |
               (rs1  & 0x1F)  << 15 |
               (f3   & 0x7)   << 12 |
               (rd   & 0x1F)  << 7  |
               (opc  & 0x7F))

def _pack_S(imm12: int, rs2: int, rs1: int, f3: int, opc: int) -> int:
    return u32(((imm12 >> 5) & 0x7F) << 25 |
               (rs2 & 0x1F) << 20 |
               (rs1 & 0x1F) << 15 |
               (f3  & 0x7)  << 12 |
               (imm12 & 0x1F) << 7 |
               (opc & 0x7F))

def _pack_B(offset_bytes: int, rs1: int, rs2: int, f3: int, opc: int, *, line:int, col:int, diags:List[Diagnostic]) -> int:
    if offset_bytes % 2 != 0:
        diags.append(error("Offset de branch debe ser múltiplo de 2 bytes", line=line, col=col))
    s = int(offset_bytes // 2)
    if not is_signed_nbit(s, 12):
        diags.append(error("Offset de branch fuera de rango (±4096 bytes, paso 2)", line=line, col=col))
    b12   = (offset_bytes >> 12) & 0x1
    b10_5 = (offset_bytes >> 5)  & 0x3F
    b4_1  = (offset_bytes >> 1)  & 0xF
    b11   = (offset_bytes >> 11) & 0x1
    return u32((b12 << 31) | (b10_5 << 25) |
               ((rs2 & 0x1F) << 20) |
               ((rs1 & 0x1F) << 15) |
               ((f3 & 0x7) << 12) |
               (b4_1 << 8) | (b11 << 7) | (opc & 0x7F))

def _pack_U(imm20: int, rd: int, opc: int) -> int:
    return u32(((imm20 & 0xFFFFF) << 12) |
               ((rd & 0x1F) << 7) |
               (opc & 0x7F))

def _pack_J(offset_bytes: int, rd: int, opc: int, *, line:int, col:int, diags:List[Diagnostic]) -> int:
    if offset_bytes % 2 != 0:
        diags.append(error("Offset de JAL debe ser múltiplo de 2 bytes", line=line, col=col))
    s = int(offset_bytes // 2)
    if not is_signed_nbit(s, 20):
        diags.append(error("Offset de JAL fuera de rango (±1 MiB, paso 2)", line=line, col=col))
    i20   = (offset_bytes >> 20) & 0x1
    i10_1 = (offset_bytes >> 1)  & 0x3FF
    i11   = (offset_bytes >> 11) & 0x1
    i19_12= (offset_bytes >> 12) & 0xFF
    return u32((i20 << 31) | (i19_12 << 12) | (i11 << 20) | (i10_1 << 21) |
               ((rd & 0x1F) << 7) | (opc & 0x7F))

# ---------------- Helpers semánticos ----------------

def _is_sym(obj: Operand) -> bool:
    return isinstance(obj, Sym)

def _is_imm(obj: Operand) -> bool:
    return isinstance(obj, Imm)

def _base_sym(name: str) -> Tuple[str, Optional[str]]:
    if name.endswith("@pcrel_hi"):
        return (name[:-10], "hi")
    if name.endswith("@pcrel_lo"):
        return (name[:-10], "lo")
    return (name, None)

# ---------------- Codificador principal ----------------

def encode(
    nodes: List[Union[Label, Directive, Instruction]],
    symtab: Dict[str, int],
    *,
    text_base: int = 0x0000_0000,
) -> EncodeResult:
    diags: List[Diagnostic] = []
    words: List[Encoded] = []

    section: Optional[str] = None
    pc = text_base    # LC de .text en bytes

    # Contexto para emparejar auipc(sym@pcrel_hi) ... addi rd,rd,sym@pcrel_lo
    last_auipc: Dict[Tuple[int, str], Tuple[int, int]] = {}  # (rd, sym) -> (pc_auipc, hi20)

    def _imm12(num: int, *, line:int, col:int) -> int:
        if not is_signed_nbit(num, 12):
            diags.append(error("Inmediato de 12 bits con signo fuera de rango (−2048..2047)", line=line, col=col))
        return num & 0xFFF

    def _imm20_signed(num: int, *, line:int, col:int) -> int:
        # U-type permite bit 31 como signo; aceptamos 20 bits con signo
        if not is_signed_nbit(num, 20):
            diags.append(error("Inmediato de 20 bits (U-type) fuera de rango (±2^19)", line=line, col=col))
        return num & 0xFFFFF

    def _resolve_branch_offset(op: Operand, cur_pc: int, *, line:int, col:int) -> int:
        if isinstance(op, Sym):
            name, suf = _base_sym(op.name)
            addr = symtab.get(name)
            if addr is None:
                diags.append(error(f"Etiqueta no definida: {name}", line=line, col=col))
                return 0
            return addr - cur_pc
        elif isinstance(op, Imm):
            # Numérico: se interpreta como relativo ya dado (bytes)
            return op.value
        else:
            diags.append(error("Operando de branch inválido (se esperaba símbolo o inmediato)", line=line, col=col))
            return 0

    def _resolve_j_offset(op: Operand, cur_pc: int, *, line:int, col:int) -> int:
        # mismas reglas que branch
        return _resolve_branch_offset(op, cur_pc, line=line, col=col)

    def _resolve_pcrel_hi(imm: Operand, cur_pc: int, *, line:int, col:int) -> Tuple[str, int]:
        assert isinstance(imm, Sym)
        name, suf = _base_sym(imm.name)
        if suf != "hi":
            diags.append(error("Se esperaba símbolo @pcrel_hi", line=line, col=col))
        addr = symtab.get(name)
        if addr is None:
            diags.append(error(f"Etiqueta no definida: {name}", line=line, col=col))
            addr = 0
        rel = addr - cur_pc
        hi20 = (rel + 0x800) >> 12  # redondeo para que el low12 quede en rango
        return name, hi20

    def _resolve_pcrel_lo(imm: Operand, rd: Reg, *, line:int, col:int) -> int:
        assert isinstance(imm, Sym)
        name, suf = _base_sym(imm.name)
        if suf != "lo":
            diags.append(error("Se esperaba símbolo @pcrel_lo", line=line, col=col))
        ctx = last_auipc.get((rd.num, name))
        if ctx is None:
            # Fallback: usar PC actual (menos preciso); avisar
            diags.append(warning(f"No se encontró AUIPC previo para {name}@pcrel_lo; usando PC actual", line=line, col=col))
            addr = symtab.get(name, 0)
            rel = addr - pc
            hi20 = (rel + 0x800) >> 12
            lo12 = rel - (hi20 << 12)
            if not is_signed_nbit(lo12, 12):
                diags.append(error("pcrel_lo fuera de rango tras fallback", line=line, col=col))
            return lo12 & 0xFFF
        pc_hi, hi20 = ctx
        addr = symtab.get(name, 0)
        rel = addr - pc_hi
        lo12 = rel - (hi20 << 12)
        if not is_signed_nbit(lo12, 12):
            diags.append(error("pcrel_lo fuera de rango", line=line, col=col))
        return lo12 & 0xFFF

    def _get_reg(op: Operand, *, line:int, col:int) -> Optional[Reg]:
        if isinstance(op, Reg):
            return op
        diags.append(error("Se esperaba registro", line=line, col=col))
        return None

    def _i_load(ins: Instruction, f3: int, opc: int) -> Optional[int]:
        rd = _get_reg(ins.operands[0], line=ins.line, col=ins.col)
        mem = ins.operands[1]
        rs1: Optional[Reg]
        imm_val: int
        if isinstance(mem, Mem):
            rs1 = mem.base
            if isinstance(mem.offset, Imm) and mem.offset.origin == "numeric":
                imm_val = mem.offset.value
            else:
                diags.append(error("Desplazamiento de memoria debe ser inmediato numérico (12 bits)", line=ins.line, col=ins.col))
                return None
        else:
            diags.append(error("Operando de memoria inválido", line=ins.line, col=ins.col))
            return None
        if rd is None:
            return None
        return _pack_I(_imm12(imm_val, line=ins.line, col=ins.col), rd=rd.num, rs1=rs1.num, f3=f3, opc=opc)

    def _s_store(ins: Instruction, f3: int, opc: int) -> Optional[int]:
        rs2 = _get_reg(ins.operands[0], line=ins.line, col=ins.col)
        mem = ins.operands[1]
        if not isinstance(mem, Mem):
            diags.append(error("Operando de memoria inválido", line=ins.line, col=ins.col))
            return None
        if not isinstance(mem.offset, Imm) or mem.offset.origin != "numeric":
            diags.append(error("Desplazamiento de memoria debe ser inmediato numérico (12 bits)", line=ins.line, col=ins.col))
            return None
        if rs2 is None:
            return None
        rs1 = mem.base
        imm12 = _imm12(mem.offset.value, line=ins.line, col=ins.col)
        return _pack_S(imm12, rs2=rs2.num, rs1=rs1.num, f3=f3, opc=opc)

    # --- recorrido principal ---
    for n in nodes:
        if isinstance(n, Directive):
            if n.name in (".text", ".data"):
                section = n.name
                # NO reseteamos PC al reencontrar .text: es un LC acumulado en .text
            # otras directivas no afectan
            continue
        if isinstance(n, Label):
            # no cambia pc; ya fue registrado en first_pass
            continue
        if not isinstance(n, Instruction):
            continue

        if section != ".text":
            diags.append(error("Instrucción fuera de .text", line=n.line, col=n.col))
            continue

        mnem = n.mnemonic.lower()
        try:
            sp = isa_spec(mnem)
        except KeyError:
            diags.append(error(f"Instrucción no válida (¿falta expandir pseudo?): {mnem}", line=n.line, col=n.col))
            continue

        word: Optional[int] = None

        # ---- Tipos por mnemónico / categoría ----
        if sp.itype == "R":
            if len(n.operands) != 3:
                diags.append(error(f"{mnem} espera 3 registros", line=n.line, col=n.col))
            rd = _get_reg(n.operands[0], line=n.line, col=n.col)
            rs1 = _get_reg(n.operands[1], line=n.line, col=n.col)
            rs2 = _get_reg(n.operands[2], line=n.line, col=n.col)
            if rd and rs1 and rs2:
                word = _pack_R(sp.funct7 or 0, rs2.num, rs1.num, sp.funct3 or 0, rd.num, sp.opcode)

        elif sp.itype == "I":
            # Distinción: LOADS, ALU-imm, SHIFTS, JALR
            if mnem in ("lb","lh","lw","lbu","lhu"):
                word = _i_load(n, f3=sp.funct3 or 0, opc=sp.opcode)

            elif mnem in ("jalr",):
                # Formas aceptadas: jalr rd, rs1, imm  |  jalr rd, imm(rs1)  |  (pseudo ya expandida)
                if len(n.operands) == 3 and isinstance(n.operands[0], Reg) and isinstance(n.operands[1], Reg) and isinstance(n.operands[2], (Imm, Sym)):
                    rd: Reg = n.operands[0]         # type: ignore[assignment]
                    rs1: Reg = n.operands[1]        # type: ignore[assignment]
                    immop: Union[Imm, Sym] = n.operands[2]  # type: ignore[assignment]
                    if isinstance(immop, Imm):
                        imm12 = _imm12(immop.value, line=n.line, col=n.col)
                    else:
                        # sym@pcrel_lo
                        imm12 = _resolve_pcrel_lo(immop, rd, line=n.line, col=n.col)
                    word = _pack_I(imm12, rs1=rs1.num, f3=sp.funct3 or 0, rd=rd.num, opc=sp.opcode)
                elif len(n.operands) == 2 and isinstance(n.operands[1], Mem):
                    rd = _get_reg(n.operands[0], line=n.line, col=n.col)
                    mem: Mem = n.operands[1]        # type: ignore[assignment]
                    if not isinstance(mem.offset, Imm):
                        diags.append(error("jalr requiere offset inmediato en operando de memoria", line=n.line, col=n.col))
                    else:
                        if rd:
                            word = _pack_I(_imm12(mem.offset.value, line=n.line, col=n.col),
                                            rs1=mem.base.num, f3=sp.funct3 or 0, rd=rd.num, opc=sp.opcode)
                else:
                    diags.append(error("Forma de jalr inválida", line=n.line, col=n.col))

            elif mnem in ("slli","srli","srai"):
                if len(n.operands) != 3:
                    diags.append(error(f"{mnem} espera rd, rs1, shamt", line=n.line, col=n.col))
                rd = _get_reg(n.operands[0], line=n.line, col=n.col)
                rs1 = _get_reg(n.operands[1], line=n.line, col=n.col)
                if not isinstance(n.operands[2], Imm):
                    diags.append(error("shamt debe ser inmediato numérico (0..31)", line=n.line, col=n.col))
                    imm12 = 0
                else:
                    sh = n.operands[2].value
                    if not is_unsigned_nbit(sh, 5):
                        diags.append(error("shamt fuera de rango (0..31 para RV32I)", line=n.line, col=n.col))
                    imm12 = ((sp.funct7 or 0) << 5) | (sh & 0x1F)
                if rd and rs1:
                    word = _pack_I(imm12, rs1=rs1.num, f3=sp.funct3 or 0, rd=rd.num, opc=sp.opcode)

            else:
                # ALU immediates: addi/slti/sltiu/xori/ori/andi
                if len(n.operands) != 3:
                    diags.append(error(f"{mnem} espera rd, rs1, imm", line=n.line, col=n.col))
                rd = _get_reg(n.operands[0], line=n.line, col=n.col)
                rs1 = _get_reg(n.operands[1], line=n.line, col=n.col)
                if not isinstance(n.operands[2], Imm):
                    diags.append(error("Inmediato debe ser numérico (12 bits con signo)", line=n.line, col=n.col))
                    imm12 = 0
                else:
                    imm12 = _imm12(n.operands[2].value, line=n.line, col=n.col)
                if rd and rs1:
                    word = _pack_I(imm12, rs1=rs1.num, f3=sp.funct3 or 0, rd=rd.num, opc=sp.opcode)

        elif sp.itype == "S":
            if len(n.operands) != 2 or not isinstance(n.operands[1], Mem):
                diags.append(error(f"{mnem} espera rs2, imm(rs1)", line=n.line, col=n.col))
            else:
                word = _s_store(n, f3=sp.funct3 or 0, opc=sp.opcode)

        elif sp.itype == "B":
            if len(n.operands) != 3:
                diags.append(error(f"{mnem} espera rs1, rs2, offset", line=n.line, col=n.col))
            rs1 = _get_reg(n.operands[0], line=n.line, col=n.col)
            rs2 = _get_reg(n.operands[1], line=n.line, col=n.col)
            off = _resolve_branch_offset(n.operands[2], pc, line=n.line, col=n.col)
            if rs1 and rs2:
                word = _pack_B(off, rs1=rs1.num, rs2=rs2.num, f3=sp.funct3 or 0, opc=sp.opcode,
                               line=n.line, col=n.col, diags=diags)

        elif sp.itype == "U":
            if len(n.operands) != 2 or not isinstance(n.operands[0], Reg):
                diags.append(error(f"{mnem} espera rd, imm20", line=n.line, col=n.col))
            else:
                rd: Reg = n.operands[0]  # type: ignore[assignment]
                immop = n.operands[1]
                if isinstance(immop, Imm):
                    word = _pack_U(_imm20_signed(immop.value, line=n.line, col=n.col), rd=rd.num, opc=sp.opcode)
                elif isinstance(immop, Sym):
                    # auipc rd, sym@pcrel_hi
                    name, tag = _base_sym(immop.name)
                    if tag == "hi" and mnem == "auipc":
                        base, hi20 = _resolve_pcrel_hi(immop, pc, line=n.line, col=n.col)
                        last_auipc[(rd.num, base)] = (pc, hi20)
                        word = _pack_U(hi20, rd=rd.num, opc=sp.opcode)
                    else:
                        diags.append(error("U-type con símbolo: sólo se admite auipc con @pcrel_hi", line=n.line, col=n.col))
                else:
                    diags.append(error("Inmediato inválido en U-type", line=n.line, col=n.col))

        elif sp.itype == "J":
            # jal rd, offset
            if len(n.operands) != 2 or not isinstance(n.operands[0], Reg):
                diags.append(error("jal espera rd, offset", line=n.line, col=n.col))
            else:
                rd: Reg = n.operands[0]  # type: ignore[assignment]
                off = _resolve_j_offset(n.operands[1], pc, line=n.line, col=n.col)
                word = _pack_J(off, rd=rd.num, opc=sp.opcode, line=n.line, col=n.col, diags=diags)

        elif sp.itype == "SYS":
            # ecall/ebreak son formas sin operandos
            if mnem == "ecall":
                word = _pack_I(0, rs1=0, f3=0, rd=0, opc=sp.opcode)
            elif mnem == "ebreak":
                word = _pack_I(1, rs1=0, f3=0, rd=0, opc=sp.opcode)
            else:
                diags.append(error("Instrucción SYSTEM no soportada", line=n.line, col=n.col))

        elif sp.itype == "FENCE":
            # fence: I-type con rd=rs1=0, funct3 según spec (000 para fence, 001 para fence.i)
            # Por defecto en 'fence' usamos pred=succ=0xF (IORW,IORW) si no hay operando.
            if mnem == "fence":
                imm = 0x0F | (0x0F << 4)  # succ=0xF, pred=0xF, fm=0
                if len(n.operands) == 1 and isinstance(n.operands[0], Imm):
                    imm = n.operands[0].value & 0xFFF
                word = _pack_I(imm, rs1=0, f3=sp.funct3 or 0, rd=0, opc=sp.opcode)
            elif mnem == "fence.i":
                word = _pack_I(0, rs1=0, f3=sp.funct3 or 0, rd=0, opc=sp.opcode)
            else:
                diags.append(error("Forma de FENCE no soportada", line=n.line, col=n.col))

        else:
            diags.append(error(f"Tipo de instrucción no soportado: {sp.itype}", line=n.line, col=n.col))

        # Registrar palabra y avanzar PC
        if word is not None:
            words.append(Encoded(word=word, pc=pc, line=n.line, col=n.col, mnemonic=mnem))
            pc += 4

    return EncodeResult(words=words, diagnostics=diags)
