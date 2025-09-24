from src.rv32i_asm.utils import u32, sign_extend, is_unsigned_nbit, is_signed_nbit, to_bin32, to_hex32, split_bits

def test_split_bits():
    x = 0b1101_0010
    # fields: [7:5]=110, [3:1]=010
    assert split_bits(x, ((7,5),(3,1))) == (6, 1)


def test_u32_and_formats():
    assert u32(-1) == 0xFFFFFFFF
    assert to_bin32(1) == "0"*31 + "1"
    assert to_hex32(0x1234, prefix=True) == "0x00001234"
    assert to_hex32(0xFFFFFFFF) == "0xffffffff"

def test_sign_extend():
    # 8-bit: 0x80 => -128
    assert sign_extend(0x80, 8) == -128
    # 8-bit: 0x7F => 127
    assert sign_extend(0x7F, 8) == 127

def test_nbit_checks():
    assert is_unsigned_nbit(4095, 12)
    assert not is_unsigned_nbit(4096, 12)
    assert is_signed_nbit(2047, 12)
    assert is_signed_nbit(-2048, 12)
    assert not is_signed_nbit(2048, 12)
    assert not is_signed_nbit(-2049, 12)


