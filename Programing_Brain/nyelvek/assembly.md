# Assembly (x86-64)
<!-- tech: assembly -->
<!-- aliases: asm, x86-64, nasm, gas, amd64 -->

Az assembly a processzor utasításkészletének (ISA) emberileg olvasható formája: minden sor közvetlenül egy (vagy néhány) gépi utasításnak felel meg, nincs típusrendszer, nincs automatikus memóriakezelés. Az x86-64 (AMD64) CISC architektúra 16 általános célú 64 bites regiszterrel, változó hosszú utasításokkal és gazdag címzési módokkal; két fő szintaxisa az Intel (NASM, MASM) és az AT&T (GNU as / GAS). Ma ritkán írunk benne teljes programot, de nélkülözhetetlen a fordítói kimenet olvasásához (`gcc -S`, Compiler Explorer), teljesítményhangoláshoz, SIMD-kernelekhez, hívási konvenciók és ABI megértéséhez, OS-kernel- és bootloader-kódhoz, valamint biztonsági elemzéshez (reverse engineering, exploitok). Hátránya: nem hordozható, nehezen karbantartható, és a modern fordítók a legtöbb esetben jobb kódot generálnak.

## Regiszterek és flagek
<!-- q: Milyen regiszterek vannak az x86-64 architektúrában és hogyan működnek a flagek? -->
<!-- tags: registers, rax, rsp, rip, rflags, zero flag, carry flag, overflow flag, partial registers -->

Az x86-64 16 általános célú 64 bites regisztert ad (`rax`, `rbx`, `rcx`, `rdx`, `rsi`, `rdi`, `rbp`, `rsp`, `r8`–`r15`), amelyek alsó 32/16/8 bites részei külön néven érhetők el (`eax`, `ax`, `al`; `r8d`, `r8w`, `r8b`). Fontos szabály: a 32 bites regiszterírás NULLÁZZA a felső 32 bitet, a 8/16 bites írás viszont nem, ami részleges regiszter-függőséget okoz. Az `rflags` a műveletek mellékhatásait tárolja: `ZF` (nulla), `SF` (előjel), `CF` (előjel nélküli átvitel), `OF` (előjeles túlcsordulás); ezekre épülnek a feltételes ugrások, a `setcc` és a `cmovcc`. Az `rip` az utasításszámláló, közvetlenül nem írható.

```nasm
; Regiszterrészek:  rax (64) -> eax (32) -> ax (16) -> ah/al (8)
; r8 (64) -> r8d (32) -> r8w (16) -> r8b (8)
section .text
global flags_demo

; uint64_t flags_demo(void) -- az OF és CF bitet adja vissza (0x0101)
flags_demo:
    mov     rax, -1             ; rax = 0xFFFFFFFFFFFFFFFF
    mov     eax, 5              ; rax = 0x0000000000000005 (felső 32 bit TÖRÖLVE)
    mov     al, 0xFF            ; rax = 0x00000000000000FF (felső bitek megmaradnak)
    xor     ecx, ecx            ; idiomatikus nullázás: rövid kódolás, függőségtörő

    mov     edx, 0x7FFFFFFF     ; INT32_MAX
    add     edx, 1              ; OF=1 (előjeles túlcsordulás), SF=1, CF=0
    seto    ch                  ; ch = OF = 1

    mov     r8d, 0xFFFFFFFF     ; UINT32_MAX
    add     r8d, 1              ; CF=1 (előjel nélküli átvitel), ZF=1, eredmény 0
    setc    cl                  ; cl = CF = 1

    movzx   eax, cx             ; zero-extend 16 -> 32 (-> 64) bit: rax = 0x0101
    ret
```

## NASM és GAS szintaxis
<!-- q: Mi a különbség az Intel (NASM) és az AT&T (GAS) assembly szintaxis között? -->
<!-- tags: nasm, gas, intel syntax, at&t syntax, gnu as, labels, operand order -->

Ugyanaz a gépi kód kétféleképpen írható le. Az Intel szintaxis (NASM, MASM, és a legtöbb dokumentáció) `cél, forrás` sorrendű, a memóriaoperandus szögletes zárójelben van, a méretet kulcsszó adja (`qword [rdi]`). Az AT&T szintaxis (GNU as, a GCC alapértelmezett kimenete) `forrás, cél` sorrendű, a regiszterek `%`, a konstansok `$` előtagot kapnak, a méret az utasítás utótagja (`q`, `l`, `w`, `b`), a címzés pedig `disp(base,index,scale)` alakú. A GAS `.intel_syntax noprefix` direktívával Intel szintaxist is elfogad, a `gcc -S -masm=intel` pedig Intel szintaxisú kimenetet ad.

```nasm
; NASM (Intel): int64_t sum_array(const int64_t *a, size_t n)   ; rdi = a, rsi = n
section .text
global sum_array
sum_array:
    xor     eax, eax                ; összeg = 0
    test    rsi, rsi
    jz      .done                   ; .label: a sum_array-hez tartozó lokális címke
.loop:
    add     rax, qword [rdi]        ; memóriaoperandus szögletes zárójelben
    add     rdi, 8
    dec     rsi
    jnz     .loop
.done:
    ret
; Fordítás: nasm -f elf64 sum.asm -o sum.o   (Windows: -f win64, macOS: -f macho64)
```

```asm
# GAS (AT&T): ugyanaz a függvény. Sorrend: forrás, cél
    .text
    .globl  sum_array
    .type   sum_array, @function
sum_array:
    xorl    %eax, %eax
    testq   %rsi, %rsi
    jz      .Ldone                  # .L előtag: nem kerül a szimbólumtáblába
.Lloop:
    addq    (%rdi), %rax            # Intel [rdi+rcx*8+16]  ==  AT&T 16(%rdi,%rcx,8)
    addq    $8, %rdi                # konstans: $ előtag
    decq    %rsi
    jnz     .Lloop
.Ldone:
    ret
    .size   sum_array, .-sum_array
# Fordítás: as sum.s -o sum.o   vagy   gcc -c sum.s
```

## Címzési módok, mov és lea
<!-- q: Hogyan működnek a címzési módok x86-64-en, és mi a különbség a mov és a lea között? -->
<!-- tags: addressing modes, mov, lea, rip-relative, sib, effective address, position independent code -->

Az x86-64 általános memóriacíme `[base + index*scale + disp]`, ahol a scale 1, 2, 4 vagy 8 – így egy utasítással érhető el például `pts[i].y` (base = tömb, index = i, scale = structméret, disp = mezőoffset). A `lea` (load effective address) kiszámolja a címet, de NEM olvas memóriát és nem állít flageket, ezért gyors aritmetikára is használják (`a + b*4 + 10` egyetlen utasítás). A RIP-relatív címzés (`[rel x]`) a pozíciófüggetlen kód (PIE, shared library) alapja. Tipikus hibák: méret nélküli memória-immediate művelet, memória→memória `mov` (nem létezik), 64 bites immediate memóriába írása.

```nasm
section .data
counter:    dq 0
table:      dd 10, 20, 30, 40

section .text
global get_y, scale_add, load_global

; struct Point { int32_t x, y; };   (8 bájt)
; int32_t get_y(const struct Point *pts, int64_t i)   ; rdi = pts, rsi = i
get_y:
    mov     eax, dword [rdi + rsi*8 + 4]    ; base + index*8 + offsetof(y)
    ret

; int64_t scale_add(int64_t a, int64_t b)   ; rdi = a, rsi = b
scale_add:
    lea     rax, [rdi + rsi*4 + 10]         ; a + 4*b + 10, memóriaolvasás nélkül
    ret

; int32_t load_global(int64_t i)   ; rdi = i
load_global:
    inc     qword [rel counter]             ; RIP-relatív: PIE-kompatibilis
    lea     rax, [rel table]                ; a tömb címe
    mov     eax, dword [rax + rdi*4]        ; table[i]
    ret

; Tipikus hibák:
;   mov [rdi], 5          -> méret nem egyértelmű; helyesen: mov dword [rdi], 5
;   mov [rax], [rbx]      -> nincs memória->memória mov; regiszteren át kell
;   mov qword [rdi], 0x1122334455667788  -> nincs 64 bites immediate memóriába
;                            (helyesen: mov rax, imm64  majd  mov [rdi], rax)
```

## Vezérlés: cmp, feltételes ugrás, ciklus és cmov
<!-- q: Hogyan írjak elágazást és ciklust assemblyben, mikor használjak cmov-ot? -->
<!-- tags: control flow, cmp, test, jcc, loops, cmov, branchless, signed unsigned comparison -->

A `cmp` (kivonás eredmény nélkül) és a `test` (AND eredmény nélkül) állítja be a flageket, a feltételes ugrások (`jcc`) ezek alapján döntenek. Az előjeles és előjel nélküli összehasonlításhoz más ugrás kell: előjeles `jl/jg/jle/jge`, előjel nélküli `jb/ja/jbe/jae` – a rossz választás klasszikus hiba. A `cmovcc` elágazásmentes (branchless) választást ad, ami kiszámíthatatlan feltételnél megelőzi a branch misprediction 15–20 ciklusos büntetését, jól megjósolható ágnál viszont nem gyorsabb. A fordítók a ciklusokat do-while formára hozzák (feltétel a végén), így iterációnként egy ugrással kevesebb fut.

```nasm
section .text
global clamp, count_char

; int64_t clamp(int64_t x, int64_t lo, int64_t hi)   ; rdi = x, rsi = lo, rdx = hi
; Elágazásmentes változat cmov-val
clamp:
    mov     rax, rdi
    cmp     rax, rsi
    cmovl   rax, rsi        ; ha x < lo (előjeles): rax = lo
    cmp     rax, rdx
    cmovg   rax, rdx        ; ha x > hi (előjeles): rax = hi
    ret

; size_t count_char(const char *s, char c)   ; rdi = s, sil = c
; C megfelelő: while (*s) { if (*s == c) n++; s++; }
count_char:
    xor     eax, eax                ; n = 0
.loop:
    movzx   ecx, byte [rdi]         ; *s betöltése zero-extenddel (nincs részleges regiszter)
    test    ecx, ecx
    jz      .end                    ; '\0' -> vége
    cmp     cl, sil
    jne     .next
    inc     rax
.next:
    inc     rdi
    jmp     .loop
.end:
    ret
```

## Linux rendszerhívások libc nélkül
<!-- q: Hogyan írjak önálló Linux assembly programot syscall-okkal, libc nélkül? -->
<!-- tags: linux, syscall, write, exit, _start, ld, itoa, div -->

Linux x86-64-en a rendszerhívás száma az `rax`-be, az argumentumok sorban az `rdi`, `rsi`, `rdx`, `r10`, `r8`, `r9` regiszterekbe kerülnek (figyelem: a 4. argumentum `r10`, nem `rcx`), a `syscall` utasítás pedig felülírja az `rcx`-et és az `r11`-et. A visszatérési érték `rax`-ben jön, hiba esetén negatív errno. libc nélküli programnál a belépési pont `_start`, és a kilépés is syscall (`exit` = 60). A `div` előtt az `rdx`-et nullázni KELL, mert az osztandó `rdx:rax` (128 bit), különben hibás eredmény vagy #DE kivétel jön; a `div` lassú, a fordítók konstanssal osztást szorzással helyettesítik.

```nasm
; Szám kiírása decimálisan, majd kilépés. Csak Linux x86-64.
; nasm -f elf64 num.asm -o num.o && ld num.o -o num && ./num
SYS_WRITE equ 1
SYS_EXIT  equ 60
STDOUT    equ 1

section .bss
buf:    resb 32

section .text
global _start
_start:
    mov     rax, 1234567890         ; kiírandó szám
    lea     rdi, [rel buf + 31]     ; a puffert hátulról töltjük
    mov     byte [rdi], 10          ; '\n'
    mov     rcx, 10
.digit:
    xor     edx, edx                ; rdx:rax az osztandó -> rdx nullázása kötelező
    div     rcx                     ; rax = hányados, rdx = maradék
    add     dl, '0'
    dec     rdi
    mov     [rdi], dl
    test    rax, rax
    jnz     .digit

    ; write(STDOUT, rdi, hossz)
    lea     rdx, [rel buf + 32]
    sub     rdx, rdi                ; hossz = vég - kezdet
    mov     rsi, rdi
    mov     edi, STDOUT
    mov     eax, SYS_WRITE
    syscall                         ; rax = kiírt bájtok száma vagy -errno

    xor     edi, edi                ; exit(0)
    mov     eax, SYS_EXIT
    syscall
```

## System V AMD64 hívási konvenció
<!-- q: Mi a System V AMD64 hívási konvenció (Linux, macOS), mely regisztereket kell megőrizni? -->
<!-- tags: calling convention, system v abi, amd64, callee-saved, caller-saved, stack alignment, red zone, plt -->

Linuxon, macOS-en és BSD-n a System V AMD64 ABI érvényes: az első 6 egész/pointer argumentum `rdi`, `rsi`, `rdx`, `rcx`, `r8`, `r9`, a lebegőpontosak `xmm0`–`xmm7`, a többi a stacken; a visszatérési érték `rax` (128 bitnél `rdx:rax`) vagy `xmm0`. A hívott függvénynek meg kell őriznie (callee-saved) az `rbx`, `rbp`, `r12`–`r15` és `rsp` értékét, a többi regisztert szabadon felülírhatja. A `call` előtt az `rsp` 16-tal osztható kell legyen (belépéskor tehát 16k+8), különben az SSE-utasítások crash-elhetnek; variadikus függvénynél az `al` a használt vektorregiszterek számát adja meg. Az `rsp` alatti 128 bájtos „red zone” leaf függvények számára foglalás nélkül használható.

```nasm
; int64_t mix(int64_t a, int64_t b, int64_t c, int64_t d,
;             int64_t e, int64_t f, int64_t g, double x);
; a..f -> rdi, rsi, rdx, rcx, r8, r9;  g -> [rsp+8] belépéskor;  x -> xmm0
section .text
global mix, print_sum
extern printf

mix:
    push    rbx                     ; callee-saved -> mentés
    mov     rbx, rdi
    add     rbx, rsi
    add     rbx, rdx
    add     rbx, rcx
    add     rbx, r8
    add     rbx, r9
    add     rbx, [rsp + 16]         ; 7. argumentum: ret cím (8) + mentett rbx (8) fölött
    cvttsd2si rax, xmm0             ; double -> int64, csonkolással
    add     rax, rbx
    pop     rbx                     ; visszaállítás
    ret

; void print_sum(int64_t v)   ; rdi = v -- C függvény hívása assemblyből
print_sum:
    sub     rsp, 8                  ; belépéskor rsp = 16k+8 -> igazítás 16-ra a call előtt
    mov     rsi, rdi                ; 2. argumentum: az érték
    lea     rdi, [rel fmt]          ; 1. argumentum: formátumstring
    xor     eax, eax                ; variadikus hívás: 0 db vektorregiszter-argumentum
    call    printf wrt ..plt        ; PIE-kompatibilis hívás a PLT-n át
    add     rsp, 8
    ret

section .rodata
fmt:    db "osszeg: %ld", 10, 0
```

## Windows x64 hívási konvenció
<!-- q: Miben különbözik a Windows x64 hívási konvenció a System V-től, mi a shadow space? -->
<!-- tags: windows x64 abi, microsoft calling convention, shadow space, home space, win64, callee-saved, unwind -->

A Microsoft x64 konvenció csak 4 regiszter-argumentumot használ: `rcx`, `rdx`, `r8`, `r9` (lebegőpontosnál `xmm0`–`xmm3`, POZÍCIÓ szerint – a 2. argumentum double-ként `xmm1`), az 5.-től a stacken. A hívó minden hívás előtt 32 bájt „shadow space”-t (home space) foglal a stacken a 4 regiszter-argumentumnak, akkor is, ha a függvénynek kevesebb van; az 5. argumentum ezért `[rsp+32]`-re kerül. Callee-saved itt az `rbx`, `rbp`, `rdi`, `rsi`, `r12`–`r15` és `xmm6`–`xmm15` – az `rdi`/`rsi` tehát NEM szabadon írható, ellentétben a System V-vel. Red zone nincs, és a nem-leaf függvényekhez unwind információ (`.pdata`/`.xdata`) kell a kivételkezeléshez.

```nasm
; Windows konzolprogram libc nélkül, közvetlen Win32 API-hívásokkal.
; nasm -f win64 win.asm -o win.obj
; link win.obj /subsystem:console /entry:main kernel32.lib
extern GetStdHandle
extern WriteFile
extern ExitProcess

section .data
msg     db "Windows x64 ABI", 13, 10
msg_len equ $ - msg

section .text
global main
main:
    sub     rsp, 56                 ; 32 shadow + 8 (5. arg) + 8 (lokális) + 8 igazítás
                                    ; belépéskor 16k+8 -> 16k+8-56 = 16(k-3): igazított
    mov     ecx, -11                ; STD_OUTPUT_HANDLE
    call    GetStdHandle            ; rax = handle

    mov     rcx, rax                ; 1. hFile
    lea     rdx, [rel msg]          ; 2. lpBuffer
    mov     r8d, msg_len            ; 3. nNumberOfBytesToWrite
    lea     r9, [rsp + 40]          ; 4. lpNumberOfBytesWritten (lokális DWORD)
    mov     qword [rsp + 32], 0     ; 5. lpOverlapped = NULL, a shadow space FÖLÖTT
    call    WriteFile

    xor     ecx, ecx                ; exit kód 0
    call    ExitProcess
```

## Stack frame, prológus és epilógus
<!-- q: Hogyan épül fel egy stack frame x86-64-en, mi a prológus és az epilógus? -->
<!-- tags: stack frame, prologue, epilogue, rbp, rsp, leave, recursion, buffer overflow, stack canary -->

A stack lefelé nő; a `call` a visszatérési címet tolja rá, a klasszikus prológus (`push rbp` / `mov rbp, rsp` / `sub rsp, N`) pedig frame pointert és helyet foglal a lokális változóknak. A frame pointer-lánc segíti a debuggereket és profilereket a hívási lánc bejárásában; `-O2` alatt a fordító gyakran elhagyja (`-fomit-frame-pointer`), és a rbp-t általános regiszterként használja. Az epilógus (`leave` = `mov rsp, rbp` + `pop rbp`, majd `ret`) visszaállítja a hívó állapotát. Biztonsági vonatkozás: egy lokális tömb túlírása a visszatérési címet írhatja felül (stack buffer overflow), ez ellen véd a stack canary (`-fstack-protector`), a nem végrehajtható stack és az ASLR.

```nasm
; Stack frame (magasabb cím felül, a stack LEFELÉ nő):
;   [rbp+16]  7. argumentum (ha volna)
;   [rbp+8]   visszatérési cím     <- a call tette ide
;   [rbp]     a hívó mentett rbp-je <- push rbp
;   [rbp-8]   lokális: mentett n
;   [rbp-16]  igazítás / további lokális
section .text
global fact

; int64_t fact(int64_t n) -- rekurzív; rdi = n
fact:
    push    rbp                     ; prológus: a régi frame mentése (rsp most 16k)
    mov     rbp, rsp                ; új frame bázis
    sub     rsp, 16                 ; hely a lokálisoknak, 16-ra igazítva
    mov     [rbp - 8], rdi          ; n mentése: a rekurzív hívás felülírja rdi-t

    cmp     rdi, 1
    jg      .recurse
    mov     eax, 1                  ; fact(0) = fact(1) = 1
    jmp     .epilogue
.recurse:
    lea     rdi, [rdi - 1]
    call    fact                    ; rax = fact(n - 1); itt rsp 16-tal osztható
    imul    rax, [rbp - 8]          ; rax *= n
.epilogue:
    leave                           ; = mov rsp, rbp ; pop rbp
    ret
```

## Assembly függvény hívása C-ből
<!-- q: Hogyan írjak assembly függvényt, amit C programból hívok, és hogyan linkeljem össze? -->
<!-- tags: c interop, extern, global, linking, object files, abi, nasm and gcc, mixed language -->

Egy assembly függvény C-ből hívható, ha `global` szimbólumként exportáljuk, betartjuk a platform hívási konvencióját (regiszterek, callee-saved regiszterek, stack-igazítás), és a C oldal a megfelelő prototípust látja. A két fájl külön fordul objektumfájllá, majd a linker köti össze a szimbólumokat név alapján – a típusokat senki nem ellenőrzi, egy hibás prototípus csendes adatkorrupcióhoz vezet. Linuxon a `.note.GNU-stack` szekció jelzi, hogy a kód nem igényel végrehajtható stacket. A legtöbb esetben a fordító intrinsicekkel ugyanolyan gyors kódot ad, ezért kézi assembly-t csak mérés után, szűk forró ciklusra érdemes írni.

```nasm
; kernels.asm -- System V ABI szerinti függvények
section .text
global my_strlen, dot_u32

; size_t my_strlen(const char *s)   ; rdi = s
my_strlen:
    mov     rax, rdi
.loop:
    cmp     byte [rax], 0
    je      .done
    inc     rax
    jmp     .loop
.done:
    sub     rax, rdi                ; hossz = vég - kezdet
    ret

; uint64_t dot_u32(const uint32_t *a, const uint32_t *b, size_t n)   ; rdi, rsi, rdx
dot_u32:
    xor     eax, eax
    xor     ecx, ecx                ; i = 0
    test    rdx, rdx
    jz      .end
.next:
    mov     r8d, [rdi + rcx*4]      ; 32 bites betöltés: a felső 32 bit nullázódik
    mov     r9d, [rsi + rcx*4]
    imul    r8, r9                  ; 64 bites szorzat: 32x32 bitnél nincs túlcsordulás
    add     rax, r8
    inc     rcx
    cmp     rcx, rdx
    jb      .next
.end:
    ret

section .note.GNU-stack noalloc noexec nowrite progbits
```

```c
// main.c -- a C oldal csak a prototípust látja, a linker köti össze a szimbólumokat.
// nasm -f elf64 kernels.asm -o kernels.o && gcc -O2 main.c kernels.o -o demo
#include <stdint.h>
#include <stdio.h>
#include <string.h>

size_t   my_strlen(const char *s);
uint64_t dot_u32(const uint32_t *a, const uint32_t *b, size_t n);

int main(void) {
    const char *t = "assembly es C egyutt";
    uint32_t a[] = {1, 2, 3, 4}, b[] = {10, 20, 30, 40};
    printf("%zu == %zu\n", my_strlen(t), strlen(t));
    printf("dot = %llu\n", (unsigned long long)dot_u32(a, b, 4));   // 300
    return 0;
}
```

## SIMD bevezető: SSE és AVX
<!-- q: Mi a SIMD, és hogyan használjam az SSE/AVX utasításokat assemblyben és intrinsicekkel? -->
<!-- tags: simd, sse, avx, avx2, intrinsics, xmm, ymm, vectorization, horizontal sum, vzeroupper -->

A SIMD (Single Instruction, Multiple Data) egy utasítással több adatelemen dolgozik: SSE-vel 128 bites `xmm` regiszterben 4 float, AVX/AVX2-vel 256 bites `ymm`-ben 8 float, AVX-512-vel 16. C-ből intrinsicekkel (`<immintrin.h>`) érhető el, így a regiszterallokációt a fordító végzi; a fordító auto-vektorizálni is tud (`-O3 -march=native`), ha nincs aliasing és a ciklus egyszerű. Tipikus minta: vektoros akkumulálás a fő ciklusban, horizontális összegzés a végén, és skaláris „maradékkezelés”. Buktatók: a lebegőpontos összeadás nem asszociatív, ezért a vektoros összeg kicsit eltérhet a skalárostól; régi SSE és AVX utasítások keverése büntetéssel jár (`vzeroupper`); és futásidőben ellenőrizni kell, hogy a CPU támogatja-e az adott utasításkészletet.

```c
// Intrinsicek: 8 float egyszerre AVX-szel. Fordítás: gcc -O2 -mavx
#include <immintrin.h>
#include <stddef.h>

float sum_avx(const float *x, size_t n) {
    __m256 acc = _mm256_setzero_ps();
    size_t i = 0;
    for (; i + 8 <= n; i += 8)
        acc = _mm256_add_ps(acc, _mm256_loadu_ps(x + i));   // loadu: nem igazított betöltés
    // Horizontális összegzés: 8 sáv -> 1 érték
    __m128 lo = _mm256_castps256_ps128(acc);
    __m128 hi = _mm256_extractf128_ps(acc, 1);
    __m128 s  = _mm_add_ps(lo, hi);                   // 4 sáv
    s = _mm_add_ps(s, _mm_movehl_ps(s, s));           // 2 sáv
    s = _mm_add_ss(s, _mm_shuffle_ps(s, s, 0x55));    // 1 sáv
    float total = _mm_cvtss_f32(s);
    for (; i < n; ++i) total += x[i];                 // skaláris maradék
    return total;
}
```

```nasm
; Ugyanez SSE-vel kézzel: float sum_sse(const float *x, size_t n)
; rdi = x, rsi = n (4 többszöröse); visszatérés: xmm0
section .text
global sum_sse
sum_sse:
    xorps   xmm0, xmm0              ; 4 sávos akkumulátor = 0
    xor     eax, eax                ; i = 0
.loop:
    cmp     rax, rsi
    jae     .reduce
    movups  xmm1, [rdi + rax*4]     ; 4 float betöltése (u = unaligned)
    addps   xmm0, xmm1              ; sávonkénti összeadás
    add     rax, 4
    jmp     .loop
.reduce:
    movhlps xmm1, xmm0              ; a felső 2 sáv az alsó helyére
    addps   xmm0, xmm1              ; 2 hasznos sáv
    movaps  xmm1, xmm0
    shufps  xmm1, xmm1, 0x55        ; az 1. sáv a 0. helyre
    addss   xmm0, xmm1              ; skaláris eredmény xmm0[0]-ban
    ret
```

## Inline assembly C-ben (GCC extended asm)
<!-- q: Hogyan írjak inline assemblyt C kódba GCC/Clang extended asm szintaxissal? -->
<!-- tags: inline assembly, extended asm, constraints, clobbers, volatile, rdtsc, cpuid, gcc, clang -->

A GCC/Clang extended asm formája `asm("sablon" : kimenetek : bemenetek : clobberek)`: a constraint-ek mondják meg a fordítónak, melyik C-változó milyen operandusba kerüljön (`"r"` regiszter, `"m"` memória, `"a"` = rax, `"="` csak írt, `"+"` olvasott és írt). A clobber-listában kell felsorolni minden mást, amit a kód módosít (`"cc"` flagek, `"memory"` – ez compiler barrierként is működik); a hiányzó clobber csendes, optimalizálási szinttől függő miscompile-t okoz. A `volatile` megakadályozza, hogy a fordító kioptimalizálja vagy áthelyezze a blokkot. Az MSVC x64 nem támogat inline asm-et (ott `__rdtsc`, `__cpuid` intrinsicek vannak), és általában is jobb a beépített függvény (`__builtin_clzll`), mert az inline asm gátolja az optimalizálást.

```c
// GCC/Clang, x86-64 (AT&T szintaxis a sablonban)
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static inline uint64_t rdtsc(void) {
    uint32_t lo, hi;
    __asm__ volatile("rdtsc" : "=a"(lo), "=d"(hi));      // eredmény edx:eax-ben
    return ((uint64_t)hi << 32) | lo;
}

static inline void cpuid(uint32_t leaf, uint32_t r[4]) {
    __asm__ volatile("cpuid"
                     : "=a"(r[0]), "=b"(r[1]), "=c"(r[2]), "=d"(r[3])
                     : "a"(leaf), "c"(0));
}

// lock prefix: atomikus read-modify-write; "memory" = compiler barrier
static inline void atomic_inc(volatile int64_t *p) {
    __asm__ volatile("lock incq %0" : "+m"(*p) : : "memory", "cc");
}

// bsr: a legmagasabb 1-es bit indexe -- x == 0 esetén az eredmény definiálatlan!
static inline unsigned highest_bit(uint64_t x) {
    uint64_t idx;
    __asm__("bsrq %1, %0" : "=r"(idx) : "rm"(x) : "cc");  // AT&T: forrás, cél
    return (unsigned)idx;
}

int main(void) {
    uint32_t r[4];
    char vendor[13];
    cpuid(0, r);
    memcpy(vendor + 0, &r[1], 4);           // a gyártó string sorrendje: ebx, edx, ecx
    memcpy(vendor + 4, &r[3], 4);
    memcpy(vendor + 8, &r[2], 4);
    vendor[12] = '\0';

    int64_t counter = 0;
    uint64_t t0 = rdtsc();
    for (int i = 0; i < 1000; ++i) atomic_inc(&counter);
    uint64_t t1 = rdtsc();
    printf("%s, %lld, ~%llu ciklus, bsr(1000)=%u\n", vendor, (long long)counter,
           (unsigned long long)(t1 - t0), highest_bit(1000));
    return 0;
}
```

## ARM64 (AArch64) összehasonlítás
<!-- q: Miben különbözik az ARM64 (AArch64) assembly az x86-64-től? -->
<!-- tags: arm64, aarch64, risc, load store, aapcs64, link register, memory model, apple silicon -->

Az AArch64 RISC architektúra: fix 32 bites utasításhossz, 31 általános regiszter (`x0`–`x30`, alsó felük `w0`–`w30`), egy nulla-regiszter (`xzr`), és load/store elv – aritmetika csak regisztereken, memória csak `ldr`/`str`(+`ldp`/`stp`) utasításokkal érhető el. A hívási konvenció (AAPCS64) 8 argumentumregisztert ad (`x0`–`x7`), a `bl` a visszatérési címet a link regiszterbe (`x30`) teszi, nem a stackre, ezért a nem-leaf függvénynek mentenie kell. A flageket csak az `s` utótagú utasítások állítják (`subs`, `adds`), és a háromoperandusú forma (`add x0, x1, x2`) kevesebb `mov`-ot igényel. Lényeges különbség a memóriamodell: az x86 erős (TSO), az ARM gyenge, ezért lock-free kódban explicit barrier vagy acquire/release utasítás (`ldar`/`stlr`) kell.

```asm
// AArch64 (GNU as). AAPCS64: argumentumok x0..x7, visszatérés x0,
// callee-saved: x19..x28, x29 (frame pointer); x30 = lr (link register)

// int64_t sum_array(const int64_t *a, size_t n)   ; x0 = a, x1 = n
    .text
    .globl  sum_array
sum_array:
    mov     x2, xzr                 // összeg = 0 (xzr mindig nulla)
    cbz     x1, 2f                  // compare-and-branch-if-zero, egy utasítás
1:  ldr     x3, [x0], #8            // post-index: x3 = *a; utána a += 8
    add     x2, x2, x3              // háromoperandusú: cél, forrás1, forrás2
    subs    x1, x1, #1              // "s" utótag: csak ez állít flaget
    b.ne    1b
2:  mov     x0, x2
    ret                             // ugrás x30-ra

// int64_t call_twice(const int64_t *a, size_t n) -- nem-leaf: lr-t menteni kell
    .globl  call_twice
call_twice:
    stp     x29, x30, [sp, #-32]!   // pre-index: sp -= 32, majd fp + lr mentése
    mov     x29, sp
    stp     x19, x20, [sp, #16]     // callee-saved regiszterek mentése
    mov     x19, x0
    mov     x20, x1
    bl      sum_array               // x30 felülíródik -> ezért mentettük
    mov     x2, x0                  // 1. eredmény
    mov     x0, x19
    mov     x1, x20
    mov     x19, x2                 // az 1. eredmény callee-saved regiszterben túléli a hívást
    bl      sum_array
    add     x0, x0, x19
    ldp     x19, x20, [sp, #16]
    ldp     x29, x30, [sp], #32     // post-index: visszatöltés, majd sp += 32
    ret
```
