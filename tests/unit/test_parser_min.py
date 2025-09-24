from src.rv32i_asm.parser import parse
from src.rv32i_asm.ast import Instruction, Label, Directive, Reg, Imm, Sym, Mem

def test_errors_en_memoria_base_invalida():
    bad = ".text\nlw x1, 4(foo)\n"   # 'foo' no es un registro válido
    nodes, diags = parse(bad, filename="bad.s")
    # esperamos al menos un diagnóstico de error
    assert any(d.severity == "error" for d in diags)
    # y que el mensaje refleje el problema de registro inválido
    assert any("Registro inválido" in d.message for d in diags)

def test_parse_simple_program():
    src = """
    .text
    start:
        addi x1, x0, 1
        beq x1, x0, start
        jal x0, +8
    """
    nodes, diags = parse(src, filename="t.s")
    assert not diags
    # Expect: .text, label, 3 instructions
    kinds = [type(n).__name__ for n in nodes]
    assert kinds == ["Directive", "Label", "Instruction", "Instruction", "Instruction"]
    ins1 = nodes[2]; assert isinstance(ins1, Instruction) and ins1.mnemonic == "addi"
    assert isinstance(ins1.operands[0], Reg) and ins1.operands[0].name == "x1"
    assert isinstance(ins1.operands[1], Reg) and ins1.operands[1].name == "x0"
    assert isinstance(ins1.operands[2], Imm) and ins1.operands[2].value == 1

def test_load_store_mem_operands():
    src = ("""
    .text
        lw a0, 0(sp)
        sw ra, -8(s0)
    """)
    nodes, diags = parse(src)
    assert not diags
    lw = nodes[1]; sw = nodes[2]
    assert isinstance(lw.operands[0], (Reg,)) and lw.operands[0].name == "x10"  # a0
    assert isinstance(lw.operands[1], Mem) and lw.operands[1].base.name == "x2" # sp
    assert lw.operands[1].offset.value == 0
    assert isinstance(sw.operands[0], Reg) and sw.operands[0].name == "x1" # ra
    assert isinstance(sw.operands[1], Mem) and sw.operands[1].offset.value == -8

def test_branch_symbol_vs_numeric():
    src = """
    .text
    loop: addi x5, x5, 1
          beq x5, x0, loop
          bne x5, x0, 12
    """
    nodes, diags = parse(src)
    assert not diags
    beq = nodes[3]; bne = nodes[4]
    # beq third operand must be a Sym
    assert isinstance(beq.operands[2], Sym) and beq.operands[2].name == "loop"
    # bne third operand numeric immediate
    assert isinstance(bne.operands[2], Imm) and bne.operands[2].value == 12

def test_equ_directive():
    nodes, diags = parse(".data\n.equ CONST, 0x1000\n", filename="x.s")
    assert not diags
    d = nodes[1]
    assert isinstance(d, Directive) and d.name == ".equ"
    assert d.args[0] == "CONST" and d.args[1] == 0x1000


SRC = """
    # Programa mínimo
    .text
start:
    addi a0, x0, 5     # inmediato decimal
    add  x1, a0, x0
    lw   t0, 8(x1)     // memoria con offset
    sw   t0, (x1)      // offset 0 implícito
loop:
    beq  x0, x0, loop  # rama a símbolo
    beq  x0, x0, 8     # rama con inmediato (relativo)
    jal  x0, 0
    .data
val:
    .equ CONST, 0x10
"""

def test_parse_program_min():
    nodes, diags = parse(SRC, filename="prog.s")
    # no debería haber errores de parseo
    assert len([d for d in diags if d.severity == "error"]) == 0

    # labels presentes
    names = [n.name for n in nodes if isinstance(n, Label)]
    assert "start" in names and "loop" in names

    # secciones detectadas
    sections = [getattr(n, "section", None) for n in nodes]
    assert ".text" in sections and ".data" in sections

    # instrucción addi con operandos correctos
    insts = [n for n in nodes if isinstance(n, Instruction)]
    addi0 = next(i for i in insts if i.mnemonic == "addi")
    assert addi0.operands[0].name == "x10"  # a0 -> x10
    assert addi0.operands[2].value == 5     # inmediato decimal

    # lw con operando de memoria imm(rs1)
    lw0 = next(i for i in insts if i.mnemonic == "lw")
    mem = lw0.operands[1]
    assert isinstance(mem, Mem)
    assert mem.base.name == "x1"
    assert mem.offset.value == 8

    # beq: uno con símbolo y otro con inmediato numérico
    beqs = [i for i in insts if i.mnemonic == "beq"]
    assert any(isinstance(b.operands[2], Sym) for b in beqs)
    assert any(isinstance(b.operands[2], Imm) for b in beqs)

    # .equ parseada correctamente
    eqs = [d for d in nodes if isinstance(d, Directive) and d.name == ".equ"]
    assert len(eqs) == 1
    assert eqs[0].args[0] == "CONST"
    assert eqs[0].args[1] == 0x10



