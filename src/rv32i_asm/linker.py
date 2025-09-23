# src/rv32i_asm/linker.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

from .ast import Label, Directive, Instruction
from .diagnostics import Diagnostic, error, warning

# ---------- Resultados de la pasada 1 ----------

@dataclass(frozen=True)
class LinkResult:
    symtab: Dict[str, int]
    text_base: int
    data_base: int
    text_size: int
    data_size: int
    diagnostics: List[Diagnostic]

# ---------- Helpers internos ----------

def _align_up(x: int, a: int) -> int:
    if a <= 0:
        raise ValueError("alignment must be positive")
    return (x + (a - 1)) & ~(a - 1)

def _is_pcrel_suffix(name: str) -> bool:
    return name.endswith("@pcrel_hi") or name.endswith("@pcrel_lo")

def _csv_from_tokens(tokens: List[Union[str, int, bytes]]) -> str:
    """
    Une los args crudos de Directive (que vienen tokenizados por espacios)
    en una sola cadena y los trata como CSV con comas.
    """
    if not tokens:
        return ""
    parts: List[str] = []
    for t in tokens:
        if isinstance(t, (int, bytes)):
            parts.append(str(t))
        else:
            parts.append(t)
    return " ".join(parts)

def _split_csv(s: str) -> List[str]:
    """
    Divide por comas respetando comillas dobles.
    Ej: '1, 2, "hola, mundo", 0x10' -> ["1","2","\"hola, mundo\"","0x10"]
    """
    out, cur, q = [], [], False
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == '"':
            q = not q
            cur.append(ch)
        elif ch == "," and not q:
            tok = "".join(cur).strip()
            if tok:
                out.append(tok)
            cur = []
        else:
            cur.append(ch)
        i += 1
    tok = "".join(cur).strip()
    if tok:
        out.append(tok)
    return out

def _parse_scalar(tok: str) -> Union[int, bytes]:
    """
    Convierte un token a int (dec/hex con signo) o bytes si es cadena entre comillas.
    Soporta escapes básicos: \\n, \\t, \\0, \\xNN.
    """
    tok = tok.strip()
    if len(tok) >= 2 and tok[0] == '"' and tok[-1] == '"':
        inner = tok[1:-1]
        # decodificar escapes simples
        inner = (
            inner
            .replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace("\\0", "\x00")
        )
        # \xNN
        import re
        def _hx(m):
            return chr(int(m.group(1), 16))
        inner = re.sub(r"\\x([0-9a-fA-F]{2})", _hx, inner)
        return inner.encode("utf-8")
    # entero (permite +/-, 0x..)
    return int(tok, 0)

def _items_from_args(args: List[Union[str, int, bytes]]) -> List[Union[int, bytes]]:
    if not args:
        return []
    csv = _csv_from_tokens(args)
    raw_items = _split_csv(csv)
    out: List[Union[int, bytes]] = []
    for tok in raw_items:
        # eliminar coma final/espacios accidentales
        tok = tok.strip()
        if tok.endswith(","):
            tok = tok[:-1].strip()
        if tok == "":
            continue
        out.append(_parse_scalar(tok))
    return out

# ---------- Pasada 1 (símbolos y layout de secciones) ----------

DATA_DIRS_SIZED = {
    ".byte": 1, ".2byte": 2, ".half": 2, ".short": 2,
    ".4byte": 4, ".word": 4,
    ".8byte": 8, ".dword": 8, ".quad": 8,
}
DATA_DIRS_TEXT = {".ascii", ".asciz"}
DATA_DIRS_SPACE = {".space", ".skip"}
ALIGN_DIRS = {".align", ".balign", ".p2align"}
IGNORED_DIRS = {".globl", ".global", ".type", ".size", ".section"}

def first_pass(
    nodes: List[Union[Label, Directive, Instruction]],
    *,
    base_text: int = 0x0000_0000,
    base_data: int = 0x1000_0000,
    align_text: int = 4,
    align_data: int = 4,
    auto_align_types: bool = True,  # alinear .word a 4, .half a 2, .dword a 8
) -> LinkResult:
    symtab: Dict[str, int] = {}
    diags: List[Diagnostic] = []

    section: Optional[str] = None
    lc_text = 0
    lc_data = 0

    def cur_base() -> int:
        return base_text if section == ".text" else base_data

    def cur_lc_ref() -> Tuple[int, str]:
        return (lc_text, ".text") if section == ".text" else (lc_data, ".data")

    # si no hay directiva inicial, asumimos .text al ver la primera instrucción/etiqueta
    def ensure_section_for_code():
        nonlocal section
        if section is None:
            section = ".text"

    for n in nodes:
        # Directivas que cambian sección
        if isinstance(n, Directive) and n.name in (".text", ".data"):
            section = n.name
            # Alinear contador al entrar si se configuró align_* > 1
            if section == ".text" and align_text > 1:
                lc_text = _align_up(lc_text, align_text)
            if section == ".data" and align_data > 1:
                lc_data = _align_up(lc_data, align_data)
            continue

        # Etiquetas
        if isinstance(n, Label):
            ensure_section_for_code()
            addr = (base_text + lc_text) if section == ".text" else (base_data + lc_data)
            name = n.name
            if _is_pcrel_suffix(name):
                diags.append(warning(f"No definas etiquetas con sufijo PC-relative: '{name}'", line=n.line, col=n.col))
            if name in symtab:
                diags.append(error(f"Etiqueta/constante redefinida: {name}", line=n.line, col=n.col))
            else:
                symtab[name] = addr
            continue

        # Directivas de datos/constantes
        if isinstance(n, Directive):
            d = n.name
            # .equ NAME, VALUE
            if d == ".equ":
                if len(n.args) >= 2 and isinstance(n.args[0], str):
                    name = n.args[0]
                    try:
                        value = int(n.args[1]) if isinstance(n.args[1], str) else int(n.args[1])
                    except Exception:
                        diags.append(error(".equ con valor inválido", line=n.line, col=n.col))
                        continue
                    if name in symtab:
                        diags.append(error(f"Constante/etiqueta redefinida: {name}", line=n.line, col=n.col))
                    else:
                        symtab[name] = value
                else:
                    diags.append(error(".equ requiere nombre y valor", line=n.line, col=n.col))
                continue

            # ignoradas (metadatos)
            if d in IGNORED_DIRS:
                continue

            # Alineaciones
            if d in ALIGN_DIRS:
                ensure_section_for_code()
                items = _items_from_args(n.args)
                if not items:
                    diags.append(error(f"{d} requiere un argumento", line=n.line, col=n.col)); continue
                try:
                    val = int(items[0])  # bytes o potencia según directiva
                except Exception:
                    diags.append(error(f"{d} argumento inválido", line=n.line, col=n.col)); continue

                if d == ".balign":
                    a = max(1, val)
                elif d == ".p2align":
                    a = 1 << max(0, val)
                else:  # ".align" (estilo GNU para RISC-V: potencia de 2)
                    a = 1 << max(0, val)

                if section == ".text":
                    lc_text = _align_up(lc_text, a)
                else:
                    lc_data = _align_up(lc_data, a)
                continue

            # Reservas de espacio (.space/.skip)
            if d in DATA_DIRS_SPACE:
                ensure_section_for_code()
                items = _items_from_args(n.args)
                if not items:
                    diags.append(error(f"{d} requiere tamaño en bytes", line=n.line, col=n.col)); continue
                try:
                    sz = int(items[0])
                except Exception:
                    diags.append(error(f"{d} tamaño inválido", line=n.line, col=n.col)); continue
                if section == ".text":
                    diags.append(error(f"{d} no permitido en .text", line=n.line, col=n.col))
                else:
                    lc_data += max(0, sz)
                continue

            # Datos con tamaño fijo (.byte/.half/.word/.dword/alias)
            if d in DATA_DIRS_SIZED:
                ensure_section_for_code()
                if section != ".data":
                    diags.append(error(f"{d} sólo permitido en .data", line=n.line, col=n.col))
                    continue
                size = DATA_DIRS_SIZED[d]
                items = _items_from_args(n.args)
                if auto_align_types:
                    lc_data = _align_up(lc_data, size)
                lc_data += size * len(items)
                continue

            # Texto de bytes (.ascii/.asciz)
            if d in DATA_DIRS_TEXT:
                ensure_section_for_code()
                if section != ".data":
                    diags.append(error(f"{d} sólo permitido en .data", line=n.line, col=n.col))
                    continue
                items = _items_from_args(n.args)
                if not items:
                    continue
                total = 0
                for it in items:
                    if isinstance(it, bytes):
                        total += len(it)
                    elif isinstance(it, int):
                        total += 1
                    else:
                        diags.append(error(f"{d} argumento no válido", line=n.line, col=n.col))
                if d == ".asciz":
                    total += 1  # terminador NUL
                lc_data += total
                continue

            # Otras directivas: ignorar pero mantener compatibilidad
            continue

        # Instrucciones
        if isinstance(n, Instruction):
            ensure_section_for_code()
            if section != ".text":
                # Muchos ensambladores no permiten instrucciones en .data
                diags.append(error("Instrucción fuera de la sección .text", line=n.line, col=n.col))
                # aún así no contamos para .data
                continue
            # Cada instrucción RV32I ocupa 4 bytes
            lc_text += 4
            continue

        # Si llega aquí, es un nodo desconocido (no debería)
        diags.append(warning("Nodo de AST desconocido en linker",))

    # Resultado final
    res = LinkResult(
        symtab=symtab,
        text_base=base_text, data_base=base_data,
        text_size=_align_up(lc_text, align_text) if align_text > 1 else lc_text,
        data_size=_align_up(lc_data, align_data) if align_data > 1 else lc_data,
        diagnostics=diags,
    )
    return res
