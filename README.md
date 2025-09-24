# RV32I Assembler (dos pasadas) — Python

Ensamblador educativo para **RISC-V RV32I** con **pseudoinstrucciones**, **dos pasadas** reales y salida en **hexadecimal** y **binario**.

- **Paso 1:** `parser` + `pseudo` → AST tipado con seudoinstrucciones expandidas
- **Paso 2:** `linker` (primera pasada) → tabla de símbolos y layout `.text/.data`
- **Paso 3:** `encoding` (segunda pasada) → palabras de 32 bits (u32)
- **Paso 4:** `writers` → vuelca `.hex` y `.bin`

## Estructura

rv32i-assembler/
├─ src/rv32i_asm/
│ ├─ assembler.py # CLI: orquesta todo el pipeline
│ ├─ parser.py # texto .s → AST
│ ├─ pseudo.py # expansión de seudoinstrucciones
│ ├─ linker.py # PASADA 1: símbolos + layout .text/.data
│ ├─ encoding.py # PASADA 2: codificación R/I/S/B/U/J/SYS/FENCE
│ ├─ writers.py # salida .hex / .bin
│ ├─ isa.py # especificación RV32I (opcodes/funct3/funct7)
│ ├─ regs.py # alias ABI ↔ xN
│ ├─ ast.py # nodos y operandos tipados
│ ├─ diagnostics.py # mensajes con línea/columna
│ └─ utils.py # helpers de bits/formatos
├─ tests/ # pytest: unit + e2e
└─ examples/
└─ hello.s


## Requisitos

- Python 3.11+
- (Opcional) `pytest` si quieres correr los tests.

Instala dependencias mínimas para tests:
```bash
pip install -r requirements.txt




$env:PYTHONPATH="src"
python -m rv32i_asm.assembler examples/hello.s out.hex out.bin