import os, io
from src.rv32i_asm.assembler import assemble_text
from src.rv32i_asm.writers import to_hex_lines

def test_e2e_hello(tmp_path):
    src = """
    .text
    start:
      addi a0, x0, 1
      addi a1, a0, 41
      add  a0, a0, a1
      beq  a0, x0, start
      jal  x0, 0
    """
    nodes, diags, link, enc = assemble_text(src, filename="hello.s")
    assert not diags
    hex_lines = to_hex_lines(enc.words)
    assert hex_lines[0] == "0x00100513"  # addi a0,x0,1
    assert hex_lines[-1] == "0x0000006f"  # jal x0,0
