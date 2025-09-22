1) por que esta estructura? 
separacion nitida por responsabilidades
    parser 
    encoder 
    linker
dos pasadas reales:
    linker: simbolod + layout sin emitir codigo
    encododing: codificacion con PC correcto
pseudo_ antes del encoding para entender sin tocar bits
writers: garantiza que el formato de salida (hex/bin) este desacoplado de la codificacion
diagnostics: centraliza errores.

2) Flujo de vida.
lexer -> parser
pseudo AST -> AST pero con pseudos expandidas a base RV21i
Pasada 1 (linker): recorre el AST expandido
Pasada 2 (encoding): recorre el AST expandido, codifica R/I/S/B/U/J/SYS
writers: recibe la lista de palabras u32 y escribe:
    program.hex: una palabra por línea (ej. 0x00000013).
    program.bin: 32 bits ASCII por línea.
