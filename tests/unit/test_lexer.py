import pytest
from src.rv32i_asm.lexer import (
    strip_comment, split_label, is_directive,
    split_mnemonic_operands, split_operands
)

# --- strip_comment ---
@pytest.mark.parametrize("src, expected", [
    ("add x1,x2,x3 # cmt", "add x1,x2,x3"),
    ("mv a0,a1 // trailing", "mv a0,a1"),
    ("# full comment", ""),
    ("// full comment", ""),
    ("   add x1,x2,x3   ", "add x1,x2,x3"),
    ("", ""),
])
def test_strip_comment(src, expected):
    assert strip_comment(src) == expected

# --- split_label ---
@pytest.mark.parametrize("src, label, rest", [
    ("loop: add x1,x2,x3", "loop", "add x1,x2,x3"),
    ("_start:   ", "_start", ""),
    ("  nope: add x1,x2,x3", None, "  nope: add x1,x2,x3"),
    ("notlabel :", None, "notlabel :"),
])
def test_split_label(src, label, rest):
    got_label, got_rest = split_label(src)
    assert got_label == label
    assert got_rest == rest

# --- is_directive ---
@pytest.mark.parametrize("src, expected", [
    (".text", True),
    ("  .data", True),
    ("add x1,x2,x3", False),
    ("", False),
])
def test_is_directive(src, expected):
    assert is_directive(src) == expected

# --- split_mnemonic_operands ---
@pytest.mark.parametrize("src, mn, tail", [
    ("ADD x1, x2, x3", "add", "x1, x2, x3"),
    ("ret", "ret", ""),
    ("   ", "", ""),
])
def test_split_mnemonic_operands(src, mn, tail):
    got_mn, got_tail = split_mnemonic_operands(src)
    assert got_mn == mn
    assert got_tail == tail

# --- split_operands ---
@pytest.mark.parametrize("src, expected", [
    ("x1,x2,x3", ["x1","x2","x3"]),
    (" x1 , x2 , x3 ", ["x1","x2","x3"]),
    ("4(x2), t0", ["4(x2)","t0"]),
    ("%pcrel_hi(foo), %lo(bar)(x1)", ["%pcrel_hi(foo)", "%lo(bar)(x1)"]),
    ("", []),
])
def test_split_operands(src, expected):
    assert split_operands(src) == expected
