from src.rv32i_asm.isa import spec

def test_core_instructions_present():
    assert spec("addi").opcode == 0x13
    assert spec("add").opcode == 0x33
    assert spec("jal").opcode == 0x6F
    assert spec("beq").opcode == 0x63
    assert spec("lw").opcode == 0x03
    assert spec("sw").opcode == 0x23
    assert spec("lui").opcode == 0x37
    assert spec("auipc").opcode == 0x17
    assert spec("jalr").opcode == 0x67
    assert spec("ecall").opcode == 0x73
    assert spec("fence").opcode == 0x0F
    assert spec("fence.i").opcode == 0x0F

def test_shift_variants_have_funct7():
    assert spec("srai").funct7 == 0b0100000
    assert spec("srli").funct7 == 0b0000000
    assert spec("slli").funct7 == 0b0000000
