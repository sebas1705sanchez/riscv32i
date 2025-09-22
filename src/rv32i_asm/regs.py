'''
mapeos ABI↔xN, validaciones, utilidades de registros
'''

from __future__ import annotations
from typing import Dict

# Mapeo de nombres ABI a nombres canónicos 'xN'
ABI_TO_X: Dict[str, str] = {
    "zero":"x0","ra":"x1","sp":"x2","gp":"x3","tp":"x4",
    "t0":"x5","t1":"x6","t2":"x7",
    "s0":"x8","fp":"x8","s1":"x9",
    "a0":"x10","a1":"x11","a2":"x12","a3":"x13","a4":"x14","a5":"x15","a6":"x16","a7":"x17",
    "s2":"x18","s3":"x19","s4":"x20","s5":"x21","s6":"x22","s7":"x23","s8":"x24","s9":"x25","s10":"x26","s11":"x27",
    "t3":"x28","t4":"x29","t5":"x30","t6":"x31",
}

def is_reg(token: str) -> bool:
    """Indica si el token representa un registro válido (ABI o 'xN')."""
    try:
        normalize_reg(token)
        return True
    except ValueError:
        return False

def normalize_reg(token: str) -> str:
    """Devuelve el nombre canónico 'xN' o lanza ValueError."""
    t = token.strip().lower()
    if t in ABI_TO_X:
        return ABI_TO_X[t]
    if t.startswith("x") and t[1:].isdigit():
        n = int(t[1:])
        if 0 <= n <= 31:
            return f"x{n}"
    raise ValueError(f"Registro inválido: {token}")

def reg_num(token: str) -> int:
    """Devuelve el índice numérico 0..31 del registro, aceptando ABI o 'xN'."""
    x = normalize_reg(token)
    return int(x[1:])
