from src.rv32i_asm.parser import parse
from src.rv32i_asm.pseudo import expand
from src.rv32i_asm.linker import first_pass
from src.rv32i_asm.encoding import encode
from src.rv32i_asm.utils import to_hex32

def _pipe(src: str):
    nodes, diags = parse(src, filename="<mem>")
    assert not diags
    nodes = expand(nodes)
    link = first_pass(nodes, base_text=0x0, base_data=0x10000000)
    enc  = encode(nodes, link.symtab, text_base=link.text_base)
    assert not enc.diagnostics
    return enc

def test_addi_and_jal_and_beq_zero():
    src = """
    .text
      addi x0, x0, 0
      beq  x0, x0, 0
      jal  x0, 0
      ecall
    """
    enc = _pipe(src)
    words_hex = [to_hex32(w.word) for w in enc.words]
    # addi x0,x0,0  -> 0x00000013
    # beq  x0,x0,0  -> 0x00000063
    # jal  x0,0     -> 0x0000006f
    # ecall         -> 0x00000073
    assert words_hex[:4] == ["0x00000013", "0x00000063", "0x0000006f", "0x00000073"]

def test_load_store_and_shifts():
    src = """
    .text
      lw   a0, 0(sp)
      sw   ra, -8(s0)
      slli t0, t0, 5
      srai t1, t1, 1
    """
    enc = _pipe(src)
    # No diagnostic y se generaron 4 palabras
    assert len(enc.words) == 4

def test_la_pcrel_and_li_large():
    src = """
    .data
    glob: .word 0
    .text
      la   a0, glob
      li   a1, 0x12345678
    """
    enc = _pipe(src)
    # la -> auipc+addi ; li grande -> lui+addi
    assert len(enc.words) == 4
