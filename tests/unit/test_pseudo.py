from src.rv32i_asm.parser import parse
from src.rv32i_asm.pseudo import expand
from src.rv32i_asm.ast import Instruction, Reg, Imm, Sym, Mem

def _mnems(nodes):
    return [n.mnemonic for n in nodes if isinstance(n, Instruction)]

def test_nop_and_mv_and_neg_not():
    src = ".text\n  nop\n  mv a0, a1\n  neg a2, a3\n  not a4, a5\n"
    nodes, _ = parse(src)
    out = expand(nodes)
    m = _mnems(out)
    assert m == ["addi", "addi", "sub", "xori"]
    i = [n for n in out if isinstance(n, Instruction)][1]
    assert isinstance(i.operands[0], Reg) and i.operands[0].name == "x10"
    assert isinstance(i.operands[1], Reg) and i.operands[1].name == "x11"
    assert isinstance(i.operands[2], Imm) and i.operands[2].value == 0

def test_seqz_snez_sltz_sgtz():
    src = ".text\n  seqz t0, t1\n  snez t2, t3\n  sltz s0, s1\n  sgtz s2, s3\n"
    nodes, _ = parse(src)
    out = expand(nodes)
    assert _mnems(out) == ["sltiu","sltu","slt","slt"]

def test_branch_zero_and_relations():
    src = ".text\n  beqz s0, loop\n  bnez s1, 12\n  bgt t0, t1, loop\n  bleu t2, t3, 8\n"
    nodes, _ = parse(src)
    out = expand(nodes)
    m = _mnems(out)
    assert m == ["beq","bne","blt","bgeu"]
    beq = [n for n in out if isinstance(n, Instruction)][0]
    assert beq.operands[1].name == "x0" and isinstance(beq.operands[2], Sym) and beq.operands[2].name=="loop"

def test_j_jal_jr_jalr_ret():
    src = ".text\n  j loop\n  jal 16\n  jr ra\n  jalr s0\n  ret\n"
    nodes, _ = parse(src)
    out = expand(nodes)
    m = _mnems(out)
    assert m == ["jal","jal","jalr","jalr","jalr"]
    j = [n for n in out if isinstance(n, Instruction)][0]
    assert j.operands[0].name == "x0"
    j2 = [n for n in out if isinstance(n, Instruction)][1]
    assert j2.operands[0].name == "x1"
    ret = [n for n in out if isinstance(n, Instruction)][4]
    assert ret.operands[0].name == "x0" and ret.operands[1].name=="x1"

def test_li_small_and_large():
    src = ".text\n  li a0, 5\n  li a1, 0x12345678\n"
    nodes, _ = parse(src)
    out = expand(nodes)
    m = _mnems(out)
    assert m == ["addi","lui","addi"]
    addi_small = [n for n in out if isinstance(n, Instruction)][0]
    assert addi_small.operands[0].name == "x10" and addi_small.operands[2].value == 5

def test_la_and_call_tail_with_symbols():
    src = ".text\n  la a0, glob\n  call glob\n  tail glob\n"
    nodes, _ = parse(src)
    out = expand(nodes)
    m = _mnems(out)
    assert m == ["auipc","addi","auipc","jalr","auipc","jalr"]
    auipc_la = [n for n in out if isinstance(n, Instruction)][0]
    assert isinstance(auipc_la.operands[1], Sym) and auipc_la.operands[1].name.endswith("@pcrel_hi")
    addi_la = [n for n in out if isinstance(n, Instruction)][1]
    assert isinstance(addi_la.operands[2], Sym) and addi_la.operands[2].name.endswith("@pcrel_lo")
    call_jalr = [n for n in out if isinstance(n, Instruction)][3]
    assert call_jalr.operands[0].name == "x1"

def test_load_store_with_symbol():
    src = ".text\n  lw a0, glob\n  sw a1, glob\n"
    nodes, _ = parse(src)
    out = expand(nodes)
    m = _mnems(out)
    assert m == ["auipc","addi","lw","auipc","addi","sw"]
    lw2 = [n for n in out if isinstance(n, Instruction)][2]
    assert isinstance(lw2.operands[1], Mem) and lw2.operands[1].base.name == "x10"
