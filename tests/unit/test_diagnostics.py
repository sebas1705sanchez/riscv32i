from src.rv32i_asm.diagnostics import error

def test_error_str():
    d = error("inmediato fuera de rango", line=12, col=8, file="prog.asm", hint="use 12 bits con signo")
    s = str(d)
    assert "prog.asm:12:8:" in s
    assert "ERROR: inmediato fuera de rango" in s
    assert "(pista: use 12 bits con signo)" in s
