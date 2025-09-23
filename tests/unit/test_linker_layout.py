from src.rv32i_asm.parser import parse
from src.rv32i_asm.pseudo import expand
from src.rv32i_asm.linker import first_pass

def test_labels_and_text_size():
    src = """
    .text
    start:
      addi x1, x0, 1
      add  x2, x1, x1
    loop:
      beq  x2, x0, loop
    """
    nodes, diags = parse(src)
    assert not diags
    nodes = expand(nodes)
    r = first_pass(nodes, base_text=0x0, base_data=0x10000000)
    assert r.symtab["start"] == 0x00000000
    # 2 instrucciones antes de 'loop': 2*4 = 8
    assert r.symtab["loop"] == 0x00000008
    # total 3 instrucciones * 4 bytes = 12
    assert r.text_size == 12

def test_data_layout_word_and_ascii():
    src = """
    .data
    A:   .word 1, 2, 3
    .ascii "hi", "!"
    B:   .half 0, 1
    .asciz "Z"
    .text
    addi x0, x0, 0
    """
    nodes, diags = parse(src)
    assert not diags
    nodes = expand(nodes)
    r = first_pass(nodes, base_text=0x0, base_data=0x10000000)

    assert r.symtab["A"] == 0x10000000

    # 12 (.word) + 3 (.ascii) + 4 (.half) + 2 (.asciz) = 21,
    # alineado a 4 → 24
    assert r.data_size == 24
    assert r.text_size == 4



def test_equ_and_duplicate_label():
    src = """
    .text
    .equ CONST, 0x1234
    L: addi x1, x0, 1
    L: addi x2, x0, 2   # redefinición
    """
    nodes, diags = parse(src)
    nodes = expand(nodes)
    r = first_pass(nodes)
    # .equ registrado
    assert r.symtab["CONST"] == 0x1234
    # debe reportar error por redefinición
    assert any("redefinida" in d.message for d in r.diagnostics)
