from __future__ import annotations
import argparse, sys
from typing import Tuple

from .parser import parse
from .pseudo import expand
from .linker import first_pass
from .encoding import encode
from .writers import write_hex, write_bin

def assemble_text(text: str, *, filename: str | None = None) -> Tuple[list, list, object, object]:
    """Parsea, expande pseudos, hace PASADA 1 y PASADA 2.
    Devuelve (nodes_expandidos, diagnostics_totales, link_result, enc_result)."""
    nodes, diags_parse = parse(text, filename=filename)
    nodes_e = expand(nodes)
    link = first_pass(nodes_e)
    enc = encode(nodes_e, link.symtab, text_base=link.text_base)
    diags = list(diags_parse) + list(link.diagnostics) + list(enc.diagnostics)
    return nodes_e, diags, link, enc

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="RV32I two-pass assembler")
    ap.add_argument("source", help="archivo .asm/.s de entrada")
    ap.add_argument("out_hex", help="archivo de salida con palabras en hexadecimal")
    ap.add_argument("out_bin", help="archivo de salida con palabras en binario ASCII")
    args = ap.parse_args(argv)

    try:
        with open(args.source, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as ex:
        print(f"ERROR: no pude leer {args.source}: {ex}", file=sys.stderr)
        return 2

    nodes, diags, link, enc = assemble_text(text, filename=args.source)

    had_error = False
    for d in diags:
        # imprimimos todo; si hay error, devolvemos código 1
        print(d, file=sys.stderr)
        if d.severity == "error":
            had_error = True

    if had_error:
        return 1

    try:
        write_hex(enc.words, args.out_hex)
        write_bin(enc.words, args.out_bin)
    except Exception as ex:
        print(f"ERROR al escribir salidas: {ex}", file=sys.stderr)
        return 3

    print(f"OK: {len(enc.words)} instrucciones → {args.out_hex}, {args.out_bin}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
