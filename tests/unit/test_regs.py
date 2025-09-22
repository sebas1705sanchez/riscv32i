import pytest
from src.rv32i_asm.regs import normalize_reg, reg_num, is_reg

def test_abi_and_xnames():
    assert normalize_reg("a0") == "x10"
    assert normalize_reg("X5") == "x5"
    assert reg_num("t6") == 31
    assert is_reg("s11")

def test_invalid():
    with pytest.raises(ValueError):
        normalize_reg("x32")
    with pytest.raises(ValueError):
        normalize_reg("foo")
