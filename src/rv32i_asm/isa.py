'''
tabla formal RV32I (opcodes, funct3/7, formas)
'''

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass(frozen=True)
class ISpec:
    """Especificación de una instrucción RV32I.

    - itype: 'R','I','S','B','U','J','SYS','FENCE'
    - opcode: campo de 7 bits
    - funct3/funct7: cuando aplica
    - forms: formas aceptadas de operandos a nivel mnemónico (solo forma, no rango)
    """
    itype: str
    opcode: int
    funct3: Optional[int] = None
    funct7: Optional[int] = None
    forms: Optional[List[str]] = None

# Constantes de opcode
OP_R     = 0b0110011  # 0x33
OP_I_ALU = 0b0010011  # 0x13
OP_I_JALR= 0b1100111  # 0x67
OP_LOAD  = 0b0000011  # 0x03
OP_STORE = 0b0100011  # 0x23
OP_BRANCH= 0b1100011  # 0x63
OP_LUI   = 0b0110111  # 0x37
OP_AUIPC = 0b0010111  # 0x17
OP_JAL   = 0b1101111  # 0x6F
OP_SYSTEM= 0b1110011  # 0x73
OP_MISC_MEM = 0b0001111  # 0x0F (FENCE/FENCE.I)

# Conjunto base RV32I
SPEC: Dict[str, ISpec] = {}

def _add(name: str, spec: ISpec, forms: List[str]):
    SPEC[name] = ISpec(**{**spec.__dict__, "forms": forms})

# Tipo R
_add("add",  ISpec("R", OP_R, funct3=0b000, funct7=0b0000000), ["rd,rs1,rs2"])
_add("sub",  ISpec("R", OP_R, funct3=0b000, funct7=0b0100000), ["rd,rs1,rs2"])
_add("sll",  ISpec("R", OP_R, funct3=0b001, funct7=0b0000000), ["rd,rs1,rs2"])
_add("slt",  ISpec("R", OP_R, funct3=0b010, funct7=0b0000000), ["rd,rs1,rs2"])
_add("sltu", ISpec("R", OP_R, funct3=0b011, funct7=0b0000000), ["rd,rs1,rs2"])
_add("xor",  ISpec("R", OP_R, funct3=0b100, funct7=0b0000000), ["rd,rs1,rs2"])
_add("srl",  ISpec("R", OP_R, funct3=0b101, funct7=0b0000000), ["rd,rs1,rs2"])
_add("sra",  ISpec("R", OP_R, funct3=0b101, funct7=0b0100000), ["rd,rs1,rs2"])
_add("or",   ISpec("R", OP_R, funct3=0b110, funct7=0b0000000), ["rd,rs1,rs2"])
_add("and",  ISpec("R", OP_R, funct3=0b111, funct7=0b0000000), ["rd,rs1,rs2"])

# Tipo I (ALU inmediatos)
_add("addi",  ISpec("I", OP_I_ALU, funct3=0b000), ["rd,rs1,imm"])
_add("slti",  ISpec("I", OP_I_ALU, funct3=0b010), ["rd,rs1,imm"])
_add("sltiu", ISpec("I", OP_I_ALU, funct3=0b011), ["rd,rs1,imm"])
_add("xori",  ISpec("I", OP_I_ALU, funct3=0b100), ["rd,rs1,imm"])
_add("ori",   ISpec("I", OP_I_ALU, funct3=0b110), ["rd,rs1,imm"])
_add("andi",  ISpec("I", OP_I_ALU, funct3=0b111), ["rd,rs1,imm"])
# Desplazamientos (I con shamt en imm[4:0], funct7 distingue SRLI/SRAI)
_add("slli",  ISpec("I", OP_I_ALU, funct3=0b001, funct7=0b0000000), ["rd,rs1,shamt"])
_add("srli",  ISpec("I", OP_I_ALU, funct3=0b101, funct7=0b0000000), ["rd,rs1,shamt"])
_add("srai",  ISpec("I", OP_I_ALU, funct3=0b101, funct7=0b0100000), ["rd,rs1,shamt"])

# Cargas
_add("lb",  ISpec("I", OP_LOAD, funct3=0b000), ["rd,mem"])
_add("lh",  ISpec("I", OP_LOAD, funct3=0b001), ["rd,mem"])
_add("lw",  ISpec("I", OP_LOAD, funct3=0b010), ["rd,mem"])
_add("lbu", ISpec("I", OP_LOAD, funct3=0b100), ["rd,mem"])
_add("lhu", ISpec("I", OP_LOAD, funct3=0b101), ["rd,mem"])

# JALR
_add("jalr", ISpec("I", OP_I_JALR, funct3=0b000), ["rd,mem0"])  # mem0 = rs1, imm(12)

# Almacenes (tipo S)
_add("sb", ISpec("S", OP_STORE, funct3=0b000), ["rs2,mem"])
_add("sh", ISpec("S", OP_STORE, funct3=0b001), ["rs2,mem"])
_add("sw", ISpec("S", OP_STORE, funct3=0b010), ["rs2,mem"])

# Saltos condicionales (tipo B)
_add("beq",  ISpec("B", OP_BRANCH, funct3=0b000), ["rs1,rs2,offset"])
_add("bne",  ISpec("B", OP_BRANCH, funct3=0b001), ["rs1,rs2,offset"])
_add("blt",  ISpec("B", OP_BRANCH, funct3=0b100), ["rs1,rs2,offset"])
_add("bge",  ISpec("B", OP_BRANCH, funct3=0b101), ["rs1,rs2,offset"])
_add("bltu", ISpec("B", OP_BRANCH, funct3=0b110), ["rs1,rs2,offset"])
_add("bgeu", ISpec("B", OP_BRANCH, funct3=0b111), ["rs1,rs2,offset"])

# Tipo U
_add("lui",   ISpec("U", OP_LUI),   ["rd,imm20"])
_add("auipc", ISpec("U", OP_AUIPC), ["rd,imm20"])

# Tipo J
_add("jal", ISpec("J", OP_JAL), ["rd,offset"])

# Sistema
_add("ecall",  ISpec("SYS", OP_SYSTEM, funct3=0b000), ["sys"])   # imm=0
_add("ebreak", ISpec("SYS", OP_SYSTEM, funct3=0b000), ["sys"])   # imm=1

# FENCE
_add("fence",   ISpec("FENCE", OP_MISC_MEM, funct3=0b000), ["predsucc"])  # fm/pred/succ en imm
_add("fence.i", ISpec("FENCE", OP_MISC_MEM, funct3=0b001), ["none"])

def spec(mnemonic: str) -> ISpec:
    """Devuelve la especificación de una instrucción por mnemónico."""
    m = mnemonic.lower()
    if m not in SPEC:
        raise KeyError(f"Instrucción desconocida: {mnemonic}")
    return SPEC[m]
