'''
 bit-twiddling (u32, sign_extend, split fields, etc.)
'''

from __future__ import annotations
from typing import Tuple

# Máscara para 32 bits sin signo
U32_MASK = 0xFFFFFFFF

def u32(x: int) -> int:
    """Fuerza el valor al rango de 32 bits sin signo."""
    return x & U32_MASK

def sign_extend(x: int, bits: int) -> int:
    """Extiende el signo de x, asumiendo que cabe en 'bits' bits (complemento a dos)."""
    if bits <= 0:
        raise ValueError("bits debe ser positivo")
    mask = (1 << bits) - 1
    x &= mask
    sign_bit = 1 << (bits - 1)
    return (x ^ sign_bit) - sign_bit

def is_unsigned_nbit(x: int, n: int) -> bool:
    """Devuelve True si x está en [0, 2^n) (sin signo de n bits)."""
    if n <= 0:
        raise ValueError("n debe ser positivo")
    return 0 <= x < (1 << n)

def is_signed_nbit(x: int, n: int) -> bool:
    """Devuelve True si x está en [-(2^(n-1)), 2^(n-1)-1] (con signo de n bits)."""
    if n <= 0:
        raise ValueError("n debe ser positivo")
    lo = -(1 << (n - 1))
    hi = (1 << (n - 1)) - 1
    return lo <= x <= hi

def to_bin32(x: int) -> str:
    """Representación binaria de 32 bits (cadena)."""
    return format(u32(x), "032b")

def to_hex32(x: int, *, prefix: bool = True) -> str:
    """Representación hexadecimal de 32 bits (cadena), con o sin prefijo 0x."""
    s = format(u32(x), "08x")
    return ("0x" + s) if prefix else s

def split_bits(value: int, positions: Tuple[Tuple[int, int], ...]) -> tuple[int, ...]:
    """Extrae campos de bits dados como rangos (hi, lo) inclusivos (base 0)."""
    out = []
    for hi, lo in positions:
        if hi < lo or hi < 0 or lo < 0:
            raise ValueError("rango de bits inválido")
        width = hi - lo + 1
        field = (value >> lo) & ((1 << width) - 1)
        out.append(field)
    return tuple(out)
