from __future__ import annotations
from typing import Iterable, List
from .utils import to_hex32, to_bin32
from .encoding import Encoded

def to_hex_lines(words: Iterable[Encoded]) -> List[str]:
    return [to_hex32(w.word) for w in words]

def to_bin_lines(words: Iterable[Encoded]) -> List[str]:
    return [to_bin32(w.word) for w in words]

def write_hex(words: Iterable[Encoded], path: str) -> None:
    lines = to_hex_lines(words)
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

def write_bin(words: Iterable[Encoded], path: str) -> None:
    lines = to_bin_lines(words)
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
