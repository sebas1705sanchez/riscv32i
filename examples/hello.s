# examples/hello.s
# Imprime "Hello, RV32I!\n" por stdout y termina (ABI Linux RISC-V)

    .data
msg: .asciz "Hello, RV32I!\n"   # 14 bytes útiles (sin contar el NUL)

    .text
    .globl _start
_start:
    # write(fd=1, buf=&msg, len=14)
    li  a0, 1            # fd = 1 (stdout)
    la  a1, msg          # buf = &msg
    li  a2, 14           # len = 14
    li  a7, 64           # syscall write
    ecall

    # exit(code=0)
    li  a0, 0
    li  a7, 93           # syscall exit
    ecall
