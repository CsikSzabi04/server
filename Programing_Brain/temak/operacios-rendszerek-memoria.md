# Operációs rendszerek és memóriakezelés
<!-- tech: operating-systems -->
<!-- aliases: operációs rendszerek, operating systems, os, kernel, memóriakezelés, linux, unix, garbage collection -->

Az operációs rendszer a hardver és a programok közötti réteg: folyamatokat és szálakat ütemez,
virtuális memóriát biztosít, fájlrendszert és I/O-t kezel, és elszigeteli egymástól a
programokat. Ez a fájl a folyamatkezelést, az ütemezést, a virtuális memóriát (lapozás, TLB,
lapcsere), a verem és halom működését, az allokátorokat és a szemétgyűjtést, a
rendszerhívásokat, a fájlrendszert és a page cache-t, az I/O-modelleket (epoll, io_uring), a
jeleket, az IPC-t és a konténerek alapjait (namespace, cgroup) mutatja be — főleg Linux/POSIX
példákkal C, Python és Go nyelven.

## Folyamatok és szálak: fork, exec, wait
<!-- q: Hogyan jön létre egy folyamat Unix alatt, és mi a különbség folyamat és szál között az OS szemszögéből? -->
<!-- tags: process, thread, fork, exec, waitpid, zombie, pcb, copy-on-write -->

A folyamat a futó program példánya saját virtuális címtérrel, erőforrásokkal (fájlleírók,
jogosultságok) és legalább egy szállal; a szál a végrehajtási kontextus (regiszterek, verem),
ami a folyamat címterén osztozik. Linuxon mindkettő „task”, a különbség a `clone()` flagjeiben
van. Unixon a `fork()` lemásolja a hívót — copy-on-write lapokkal, így olcsó —, a gyerekben az
`exec*()` lecseréli a programképet, a szülő `waitpid()`-del gyűjti be a kilépési kódot. Buktatók:
a be nem gyűjtött gyerek zombi marad, fork előtt üríteni kell a stdio-puffereket, a gyerek exec
hiba után `_exit()`-tel lépjen ki; Windowson nincs fork (CreateProcess), és a `posix_spawn` is
gyakran jobb választás.

```c
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

int run(char *const argv[]) {
    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        return -1;
    }
    if (pid == 0) {
        /* GYEREK: ugyanaz a kód, de saját (copy-on-write) címtér */
        execvp(argv[0], argv);  /* siker esetén ide NEM tér vissza */
        fprintf(stderr, "exec %s: %s\n", argv[0], strerror(errno));
        _exit(127);  /* _exit: ne fussanak a szülőtől örökölt atexit-kezelők és stdio-ürítések */
    }
    /* SZÜLŐ: begyűjtés nélkül a gyerek zombi maradna */
    int status;
    while (waitpid(pid, &status, 0) < 0) {
        if (errno != EINTR) {  /* jel megszakíthatja: újrapróbáljuk */
            perror("waitpid");
            return -1;
        }
    }
    if (WIFEXITED(status)) return WEXITSTATUS(status);
    if (WIFSIGNALED(status)) fprintf(stderr, "jel ölte meg: %d\n", WTERMSIG(status));
    return -1;
}

int main(void) {
    printf("szülő pid=%d\n", getpid());
    fflush(stdout);  /* fork előtt: különben a puffer tartalma kétszer íródna ki */
    char *ls[] = {"ls", "-l", "/tmp", NULL};
    printf("kilépési kód: %d\n", run(ls));
    char *bad[] = {"nincs-ilyen-parancs", NULL};
    printf("kilépési kód: %d\n", run(bad));  /* 127 */
    return 0;
}
```

## CPU-ütemezés: FCFS, SJF, Round Robin és a modern ütemezők
<!-- q: Hogyan dönti el az operációs rendszer, melyik folyamat fusson, és milyen ütemezési algoritmusok vannak? -->
<!-- tags: scheduling, round robin, sjf, fcfs, cfs, eevdf, context switch, preemption -->

Az ütemező dönti el, melyik kész állapotú szál kapja a CPU-t. Az FCFS egyszerű, de egy hosszú
feladat mögött mindenki vár (konvojhatás); az SJF minimalizálja az átlagos várakozást, de
ismernie kell a futásidőt, és kiéheztetheti a hosszú feladatokat; a Round Robin időszeletekkel
preemptív, jó válaszidőt ad — a túl kicsi kvantum sok kontextusváltást okoz, a túl nagy
FCFS-sé fajul. A Linux CFS-e a „virtuális futásidő” szerint igazságos (piros-fekete fában), a
6.6-os kerneltől az EEVDF váltotta; vannak valós idejű házirendek is (SCHED_FIFO, SCHED_RR).
Többmagos gépen magonkénti futási sorok és terheléskiegyenlítés működik; egy kontextusváltás
közvetlen költsége mikroszekundum nagyságrendű, de a cache- és TLB-hatás ennél drágább lehet.

```python
from collections import deque
from dataclasses import dataclass

@dataclass
class Proc:
    name: str
    arrival: int
    burst: int  # szükséges CPU-idő

def fcfs(procs: list[Proc]) -> dict[str, int]:
    t, finish = 0, {}
    for p in sorted(procs, key=lambda p: p.arrival):
        t = max(t, p.arrival) + p.burst
        finish[p.name] = t
    return finish

def sjf(procs: list[Proc]) -> dict[str, int]:
    """Nem preemptív SJF: a kész feladatok közül a legrövidebb fut."""
    pending, t, finish = sorted(procs, key=lambda p: p.arrival), 0, {}
    while pending:
        ready = [p for p in pending if p.arrival <= t] or [pending[0]]
        p = min(ready, key=lambda p: p.burst)
        t = max(t, p.arrival) + p.burst
        finish[p.name] = t
        pending.remove(p)
    return finish

def round_robin(procs: list[Proc], quantum: int) -> dict[str, int]:
    pending = deque(sorted(procs, key=lambda p: p.arrival))
    remaining = {p.name: p.burst for p in procs}
    queue: deque[Proc] = deque()
    t, finish = 0, {}
    while pending or queue:
        while pending and pending[0].arrival <= t:
            queue.append(pending.popleft())
        if not queue:
            t = pending[0].arrival  # üresjárat a következő érkezésig
            continue
        p = queue.popleft()
        run = min(quantum, remaining[p.name])
        t += run
        remaining[p.name] -= run
        while pending and pending[0].arrival <= t:  # a közben érkezők előbb kerülnek sorra
            queue.append(pending.popleft())
        if remaining[p.name] == 0:
            finish[p.name] = t
        else:
            queue.append(p)  # preempció: vissza a sor végére
    return finish

def report(name: str, procs: list[Proc], finish: dict[str, int]) -> None:
    waits = [finish[p.name] - p.arrival - p.burst for p in procs]
    print(f"{name:<10} átlagos várakozás: {sum(waits) / len(waits):5.2f}")

if __name__ == "__main__":
    ps = [Proc("hosszú", 0, 20), Proc("A", 1, 2), Proc("B", 2, 3), Proc("C", 3, 1)]
    report("FCFS", ps, fcfs(ps))  # konvojhatás: mindenki a hosszú mögött vár
    report("SJF", ps, sjf(ps))
    report("RR (q=2)", ps, round_robin(ps, 2))
```

## Virtuális memória, laptáblák és a TLB
<!-- q: Hogyan működik a virtuális memória, a laptábla és a TLB? -->
<!-- tags: virtual memory, paging, page table, tlb, mmu, page fault, huge pages, address translation -->

Minden folyamat saját virtuális címteret lát; az MMU a laptáblák alapján fordítja a virtuális
lapot (tipikusan 4 KiB) fizikai keretre. Ez adja az elszigetelést, a copy-on-write-ot, a lusta
(igény szerinti) foglalást, a memórialeképezett fájlokat és a swapot. A címfordítás többszintű
tábla bejárása (x86-64-en 4–5 memóriaolvasás), ezért a TLB gyorsítótárazza a friss
fordításokat; TLB-hiánynál „page walk” jön, nem leképezett lapnál laphiba, amit a kernel kezel
(lap betöltése, CoW-másolás vagy SIGSEGV). Buktatók: a véletlenszerű memória-hozzáférés sok
TLB-hiányt okoz (nagy lapok — 2 MiB/1 GiB — segítenek), és a leképezés változásakor a többi mag
TLB-jét is érvényteleníteni kell (TLB shootdown).

```python
from collections import OrderedDict

PAGE_SIZE = 4096  # 4 KiB lap: az alsó 12 bit a lapon belüli eltolás
OFFSET_BITS = 12
LEVEL_BITS = 10  # 32 bites cím = 10 (könyvtár) + 10 (tábla) + 12 (eltolás)

class PageFault(Exception):
    pass

class MMU:
    """Kétszintű laptábla + TLB szimuláció (a valódi MMU hardver, az OS tölti a táblákat)."""

    def __init__(self, tlb_size: int = 4) -> None:
        self.page_dir: dict[int, dict[int, tuple[int, bool]]] = {}  # könyvtár -> {index: (keret, írható)}
        self.tlb: OrderedDict[int, tuple[int, bool]] = OrderedDict()  # VPN -> (keret, írható)
        self.tlb_size = tlb_size
        self.hits = self.misses = 0

    def map(self, vaddr: int, frame: int, writable: bool = True) -> None:
        vpn = vaddr >> OFFSET_BITS
        self.page_dir.setdefault(vpn >> LEVEL_BITS, {})[vpn & ((1 << LEVEL_BITS) - 1)] = (frame, writable)
        self.tlb.pop(vpn, None)  # leképezés-változás: a TLB-bejegyzés érvénytelen

    def translate(self, vaddr: int, write: bool = False) -> int:
        vpn, offset = vaddr >> OFFSET_BITS, vaddr & (PAGE_SIZE - 1)
        if vpn in self.tlb:  # TLB-találat: nincs laptábla-olvasás
            self.hits += 1
            self.tlb.move_to_end(vpn)
            frame, writable = self.tlb[vpn]
        else:  # TLB-hiány: page walk, szintenként egy memóriaolvasás
            self.misses += 1
            entry = self.page_dir.get(vpn >> LEVEL_BITS, {}).get(vpn & ((1 << LEVEL_BITS) - 1))
            if entry is None:
                raise PageFault(f"nincs leképezve: {vaddr:#010x}")  # OS: lusta foglalás / swap / SIGSEGV
            frame, writable = entry
            self.tlb[vpn] = entry
            if len(self.tlb) > self.tlb_size:
                self.tlb.popitem(last=False)  # LRU-kiszorítás
        if write and not writable:
            raise PageFault(f"írásvédett lap: {vaddr:#010x}")  # pl. itt indul a copy-on-write
        return (frame << OFFSET_BITS) | offset

if __name__ == "__main__":
    mmu = MMU()
    for i in range(8):
        mmu.map(0x0040_0000 + i * PAGE_SIZE, frame=100 + i, writable=(i != 0))
    for addr in range(0x0040_0000, 0x0040_0000 + 8 * PAGE_SIZE, 64):  # szekvenciális bejárás
        mmu.translate(addr)
    print(f"TLB találat: {mmu.hits}, hiány: {mmu.misses}")  # 504 / 8 — a lokalitás miatt
    print(hex(mmu.translate(0x0040_1ABC)))  # 0x65abc
    for bad in ((0x0800_0000, False), (0x0040_0010, True)):
        try:
            mmu.translate(*bad)
        except PageFault as e:
            print("laphiba:", e)
```

## Lapcserélési algoritmusok és a thrashing
<!-- q: Hogyan dönti el az OS, melyik lapot írja ki a memóriából, és mi az a thrashing? -->
<!-- tags: page replacement, lru, clock algorithm, fifo, belady anomaly, working set, thrashing, swap -->

Ha a fizikai memória megtelt, laphibánál egy lapot ki kell szorítani (piszkos lapot előbb
lemezre írva). Az optimális (Bélády-féle MIN) algoritmus a legkésőbb újra használt lapot dobná
el, de ehhez a jövőt kellene ismerni; az LRU jó közelítés, de pontos megvalósítása minden
hozzáférésnél drága. Ezért a kernelek a hardveres „accessed” bitre építő Clock (második esély)
algoritmust vagy annak változatait (Linux: aktív/inaktív listák, multi-gen LRU) használják; a
FIFO-nál pedig a Bélády-anomália miatt több keret több laphibát is okozhat. Ha a folyamatok
munkahalmaza (working set) nem fér el a RAM-ban, a rendszer szinte csak lapoz (thrashing) — a
megoldás kevesebb memóriahasználat, több RAM vagy a terhelés csökkentése; Linuxon végső
esetben az OOM-killer lép közbe.

```python
from collections import OrderedDict, deque

def fifo(refs: list[int], frames: int) -> int:
    mem: deque[int] = deque()
    faults = 0
    for p in refs:
        if p not in mem:
            faults += 1
            if len(mem) == frames:
                mem.popleft()  # a legrégebben BETÖLTÖTT lap megy, bármilyen gyakori is
            mem.append(p)
    return faults

def lru(refs: list[int], frames: int) -> int:
    mem: OrderedDict[int, None] = OrderedDict()
    faults = 0
    for p in refs:
        if p in mem:
            mem.move_to_end(p)  # használat => legfrissebb
        else:
            faults += 1
            if len(mem) == frames:
                mem.popitem(last=False)  # a legrégebben HASZNÁLT lap megy
            mem[p] = None
    return faults

def clock(refs: list[int], frames: int) -> int:
    """Második esély: a mutató körbejár; 1-es bitű lapot megkímél (bitet töröl), 0-st kiszorít."""
    slots: list[int | None] = [None] * frames
    ref_bit = [False] * frames
    hand, faults = 0, 0
    for p in refs:
        if p in slots:
            ref_bit[slots.index(p)] = True  # valójában a hardver állítja hozzáféréskor
            continue
        faults += 1
        while ref_bit[hand]:
            ref_bit[hand] = False
            hand = (hand + 1) % frames
        slots[hand], ref_bit[hand] = p, True
        hand = (hand + 1) % frames
    return faults

if __name__ == "__main__":
    refs = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
    for f in (3, 4):
        print(f"{f} keret: FIFO={fifo(refs, f)} LRU={lru(refs, f)} Clock={clock(refs, f)}")
    # Bélády-anomália: FIFO-val 3 kereten 9, 4 kereten 10 laphiba
```

## Verem és halom
<!-- q: Mi a különbség a verem (stack) és a halom (heap) között, és mikor melyikbe kerül az adat? -->
<!-- tags: stack, heap, stack frame, stack overflow, dangling pointer, malloc, escape analysis -->

A verem függvényhívásonként egy keretet tárol (lokális változók, visszatérési cím, mentett
regiszterek): a foglalás csak a veremmutató eltolása, a felszabadítás automatikus, és a
lokalitás miatt cache-barát — de mérete korlátos (Linuxon a fő szálnak tipikusan 8 MiB, a
többinek kevesebb), és az adat csak a függvény végéig él. A halom tetszőleges méretű és
élettartamú adatot tárol, de drágább (allokátorhívás, töredezettség), és a felszabadítás a
programozó (C), a tulajdonos (Rust, C++ RAII) vagy a GC (Java, Go) dolga. Tipikus hibák: lokális
változó címének visszaadása (lógó mutató), túl mély rekurzió vagy óriási lokális tömb
(veremtúlcsordulás). Go és Java fordítója escape-analízissel dönti el, mehet-e a verembe egy
objektum.

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int sum_stack(void) {
    int arr[256];  /* veremben: gyors, de csak a függvény végéig él */
    for (int i = 0; i < 256; i++) arr[i] = i;
    int s = 0;
    for (int i = 0; i < 256; i++) s += arr[i];
    return s;
}

/* HIBA: lokális változó címének visszaadása — a keret visszatéréskor megszűnik.
 * A fordító figyelmeztet rá (-Wreturn-local-addr). */
char *dangling(void) {
    char buf[32];
    strcpy(buf, "már nem létezik");
    return buf;  /* NE TEDD: lógó mutató, definiálatlan viselkedés */
}

/* Halom: az eredmény túléli a függvényt; a tulajdonjog a hívóé, ő szabadítja fel */
char *make_greeting(const char *name) {
    size_t n = strlen(name) + 7;
    char *s = malloc(n);
    if (!s) return NULL;
    snprintf(s, n, "Szia, %s", name);
    return s;
}

/* Rekurzió: keretenként ~1 KiB verem — túl mély hívásnál veremtúlcsordulás (SIGSEGV) */
unsigned long depth(unsigned long n) {
    volatile char pad[1024];
    pad[0] = (char)n;
    return n == 0 ? 0 : 1 + depth(n - 1) + (unsigned long)(pad[0] & 0);
}

int main(void) {
    printf("%d\n", sum_stack());
    char *g = make_greeting("világ");
    if (g) {
        puts(g);
        free(g);  /* minden malloc-hoz pontosan egy free */
    }
    printf("%lu\n", depth(1000));  /* ~1 MiB: rendben; depth(100000000) összeomlana */
    (void)dangling;
    return 0;
}
```

## A malloc belülről: szabadlista, darabolás, összevonás
<!-- q: Hogyan működik belül a malloc és a free? -->
<!-- tags: malloc, free, allocator, free list, fragmentation, coalescing, ptmalloc, jemalloc -->

A malloc a kernelt ritkán hívja (brk/sbrk vagy mmap nagy darabokért), a kapott memóriát maga
osztja ki: minden blokk előtt egy fejléc tárolja a méretet és az állapotot, a szabad blokkok
listában vannak. Foglaláskor megkeres egy elég nagy szabad blokkot (first-fit, best-fit,
méretosztályok), a fölösleget levágja; felszabadításkor a szomszédos szabad blokkokat
összevonja a külső töredezettség ellen. A valódi allokátorok (glibc ptmalloc, jemalloc,
mimalloc, tcmalloc) méretosztályokat, szálankénti gyorsítótárakat és arénákat használnak a
zárversengés ellen, nagy kéréseket pedig közvetlenül mmap-pel szolgálnak ki. Mivel a fejléc a
kiadott mutató előtt van, egy puffer-túlírás vagy dupla free az allokátor adatait rongálja meg.

```c
#include <stddef.h>
#include <stdio.h>

#define HEAP_SIZE (1 << 20)
#define ALIGN 16

typedef struct Block {
    size_t size;         /* a hasznos rész mérete */
    int free;
    struct Block *next;  /* cím szerint következő blokk */
} Block;

static _Alignas(ALIGN) unsigned char heap[HEAP_SIZE];
static Block *head = NULL;

static size_t align_up(size_t n) { return (n + ALIGN - 1) & ~(size_t)(ALIGN - 1); }
#define HDR align_up(sizeof(Block))

void *my_malloc(size_t n) {
    if (n == 0 || n > HEAP_SIZE) return NULL;
    n = align_up(n);  /* igazítás: bármely típus számára biztonságos cím */
    if (!head) {      /* első hívás: egyetlen nagy szabad blokk */
        head = (Block *)heap;
        *head = (Block){HEAP_SIZE - HDR, 1, NULL};
    }
    for (Block *b = head; b; b = b->next) {  /* first-fit keresés */
        if (!b->free || b->size < n) continue;
        if (b->size >= n + HDR + ALIGN) {    /* darabolás, ha a maradék még használható */
            Block *rest = (Block *)((unsigned char *)b + HDR + n);
            *rest = (Block){b->size - n - HDR, 1, b->next};
            b->size = n;
            b->next = rest;
        }
        b->free = 0;
        return (unsigned char *)b + HDR;  /* a fejléc UTÁNI címet adjuk ki */
    }
    return NULL;  /* nincs elég nagy összefüggő blokk: töredezettség */
}

void my_free(void *p) {
    if (!p) return;
    Block *b = (Block *)((unsigned char *)p - HDR);  /* a fejléc a mutató előtt van */
    b->free = 1;
    for (Block *c = head; c; c = c->next) {  /* szomszédos szabad blokkok összevonása */
        while (c->free && c->next && c->next->free) {
            c->size += HDR + c->next->size;
            c->next = c->next->next;
        }
    }
}

int main(void) {
    char *a = my_malloc(100), *b = my_malloc(200), *c = my_malloc(50);
    my_free(b);
    char *d = my_malloc(150);  /* first-fit: b helyére kerül */
    printf("d ugyanott, ahol b volt: %d\n", b == d);
    my_free(a);
    my_free(c);
    my_free(d);
    printf("összevonás után nagy blokk: %p\n", my_malloc(HEAP_SIZE / 2));
    return 0;
}
```

## Aréna- és slab-allokátorok
<!-- q: Mi az arena (bump) allokátor és a slab/pool allokátor, és mikor gyorsabbak a malloc-nál? -->
<!-- tags: arena allocator, bump allocator, slab allocator, memory pool, free list, fragmentation -->

Az aréna (bump) allokátor egy nagy blokkból egy mutató eltolásával foglal, egyedi
felszabadítás nincs: az egész aréna egyszerre ürül. Kérésenkénti vagy fázisonkénti adathoz
(fordító AST-je, HTTP-kérés feldolgozása, játék-képkocka) ideális — rendkívül gyors, nincs
töredezettség és szivárgás, de egyetlen hosszú életű objektum az egész arénát életben tartja.
A slab/pool allokátor azonos méretű objektumokat tárol előre foglalt blokkban, a szabad helyek
láncolt listában vannak (a szabad slot maga tárolja a következő címét), így foglalás és
felszabadítás O(1); a Linux kernel SLUB allokátora így kezeli a gyakori kernelobjektumokat.
Mindkettőnél figyelni kell az igazításra és a túlcsordulás-biztos méretellenőrzésre.

```c
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct { unsigned char *base; size_t cap, used; } Arena;

int arena_init(Arena *a, size_t cap) {
    a->base = malloc(cap);
    a->cap = cap;
    a->used = 0;
    return a->base ? 0 : -1;
}

void *arena_alloc(Arena *a, size_t n, size_t align) {  /* align: 2 hatványa */
    size_t start = (a->used + align - 1) & ~(align - 1);
    if (start > a->cap || n > a->cap - start) return NULL;  /* túlcsordulás-biztos ellenőrzés */
    a->used = start + n;
    return a->base + start;
}

void arena_reset(Arena *a) { a->used = 0; }  /* O(1) "felszabadítás" mindenre */

/* Pool: 64 bájtos slotok; a szabad slot a következő szabad címét tárolja */
typedef union Slot { union Slot *next; max_align_t align_; unsigned char data[64]; } Slot;
typedef struct { Slot *slots; Slot *free_list; } Pool;

int pool_init(Pool *p, size_t count) {
    p->slots = malloc(count * sizeof(Slot));
    if (!p->slots) return -1;
    p->free_list = NULL;
    for (size_t i = count; i-- > 0;) {  /* minden slot a szabad listára */
        p->slots[i].next = p->free_list;
        p->free_list = &p->slots[i];
    }
    return 0;
}

void *pool_alloc(Pool *p) {
    Slot *s = p->free_list;
    if (s) p->free_list = s->next;
    return s;
}

void pool_free(Pool *p, void *ptr) {
    Slot *s = ptr;
    s->next = p->free_list;  /* LIFO: a frissen felszabadított slot még "meleg" a cache-ben */
    p->free_list = s;
}

int main(void) {
    Arena a;
    if (arena_init(&a, 1 << 16)) return 1;
    for (int frame = 0; frame < 3; frame++) {
        int *tmp = arena_alloc(&a, 1000 * sizeof(int), _Alignof(int));
        double *d = arena_alloc(&a, 10 * sizeof(double), _Alignof(double));
        printf("képkocka %d: %p %p, használt %zu bájt\n", frame, (void *)tmp, (void *)d, a.used);
        arena_reset(&a);  /* a képkocka végén minden egyszerre szabadul */
    }
    free(a.base);

    Pool p;
    if (pool_init(&p, 1024)) return 1;
    void *x = pool_alloc(&p);
    pool_free(&p, x);
    printf("újrahasznosítva: %d\n", pool_alloc(&p) == x);  /* 1 */
    free(p.slots);
    return 0;
}
```

## Szemétgyűjtés referenciaszámlálással
<!-- q: Hogyan működik a referenciaszámlálás, és miért gond a körkörös hivatkozás? -->
<!-- tags: reference counting, garbage collection, weak reference, cycles, cpython, arc, rc -->

A referenciaszámlálásnál minden objektum számolja, hányan hivatkoznak rá, és nullánál azonnal
felszabadul: determinisztikus (a fájl azonnal bezárul), a szünetek kicsik és jól eloszlanak. Ezt
használja a CPython, a Swift (ARC), a Rust `Rc`/`Arc` és a C++ `shared_ptr`. Hátrányai: minden
mutatómásolás számlálófrissítéssel jár (többszálú esetben atomikussal, ami drága), egy nagy
struktúra felszabadítása láncreakciót indíthat, és a körkörös hivatkozás sosem éri el a nullát —
ezért van a CPythonban külön ciklusgyűjtő. Tervezési megoldás a gyenge hivatkozás a „visszafelé”
mutató élekre (szülő, megfigyelő, cache), ami nem növeli a számlálót.

```python
import gc
import sys
import weakref

class Node:
    def __init__(self, name: str) -> None:
        self.name = name
        self.other: "Node | None" = None

    def __del__(self) -> None:
        print(f"felszabadítva: {self.name}")

a = Node("a")
print("refcount:", sys.getrefcount(a))  # +1 a getrefcount argumentuma miatt
b = a
print("refcount:", sys.getrefcount(a))
del a, b  # a számláló 0: azonnal "felszabadítva: a"

x, y = Node("x"), Node("y")
x.other, y.other = y, x  # körkörös hivatkozás
del x, y  # a számláló nem éri el a 0-t
print("törlés után még élnek; gc fut...")
print("összegyűjtött objektumok:", gc.collect())  # a ciklusgyűjtő takarítja el

class TreeNode:
    def __init__(self, name: str, parent: "TreeNode | None" = None) -> None:
        self.name = name
        self.children: list[TreeNode] = []
        self._parent = weakref.ref(parent) if parent else None  # NEM növeli a számlálót
        if parent:
            parent.children.append(self)

    @property
    def parent(self) -> "TreeNode | None":
        return self._parent() if self._parent else None  # None, ha a szülő már megszűnt

root = TreeNode("gyökér")
leaf = TreeNode("levél", root)
print(leaf.parent.name if leaf.parent else None)  # gyökér
del root
print(leaf.parent)  # None: a gyenge hivatkozás nem tartotta életben
```

## Nyomkövető szemétgyűjtés: mark-sweep, háromszínű jelölés, generációk
<!-- q: Hogyan működik a mark-and-sweep, a háromszínű jelölés és a generációs szemétgyűjtés? -->
<!-- tags: garbage collection, mark and sweep, tri-color marking, write barrier, generational gc, g1, zgc -->

A nyomkövető GC a gyökerekből (verem, globálisok, regiszterek) bejárja az elérhető
objektumokat, és minden mást felszabadít, így a körök sem okoznak gondot. A mark-sweep
töredezettséget hagy; a mark-compact tömörít; a másoló gyűjtő az élőket átmásolja, ezután a
foglalás egyszerű mutatóeltolás. A háromszínű jelölés (fehér: nem látott, szürke: látott, de
gyerekei feldolgozatlanok, fekete: kész) teszi lehetővé az inkrementális és konkurens jelölést
— ehhez írási korlát (write barrier) őrzi az invariánst, hogy fekete objektum ne mutasson
fehérre. A generációs hipotézis szerint a legtöbb objektum fiatalon hal meg, ezért a fiatal
generációt gyakran és olcsón gyűjtjük, az öreget ritkán; az öreg→fiatal mutatókat kártyatábla
tartja nyilván. Kompromisszum: szünetidő vs. áteresztőképesség vs. memória (Java G1/ZGC, Go
konkurens mark-sweep, .NET).

```python
from dataclasses import dataclass, field

@dataclass(eq=False)
class Obj:
    name: str
    refs: list["Obj"] = field(default_factory=list)
    color: str = "white"
    age: int = 0  # túlélt gyűjtések száma (generációs GC-hez)

class Heap:
    def __init__(self) -> None:
        self.objects: list[Obj] = []
        self.roots: list[Obj] = []  # gyökerek: verem, globálisok, regiszterek

    def new(self, name: str) -> Obj:
        o = Obj(name)
        self.objects.append(o)
        return o

    def collect(self) -> list[str]:
        """Háromszínű jelölés + söprés. Invariáns: fekete objektum sosem mutat fehérre."""
        for o in self.objects:
            o.color = "white"
        gray = list(self.roots)
        for r in gray:
            r.color = "gray"
        while gray:  # ez a ciklus kis szeletekre bontható: inkrementális GC
            o = gray.pop()
            for child in o.refs:
                if child.color == "white":
                    child.color = "gray"
                    gray.append(child)
            o.color = "black"
        freed = [o.name for o in self.objects if o.color == "white"]  # söprés
        self.objects = [o for o in self.objects if o.color == "black"]
        for o in self.objects:
            o.age += 1  # a túlélők idővel az öreg generációba kerülnének
        return freed

    def write_barrier(self, src: Obj, dst: Obj) -> None:
        """Beszúrási (Dijkstra-féle) korlát konkurens jelöléshez: az új cél szürke lesz,
        így egy már fekete forrás sem rejthet el fehér, elérhető objektumot."""
        src.refs.append(dst)
        if dst.color == "white":
            dst.color = "gray"

if __name__ == "__main__":
    h = Heap()
    a, b, c, d = (h.new(n) for n in "abcd")
    a.refs.append(b)
    c.refs.append(d)
    d.refs.append(c)  # c <-> d kör, de gyökérből nem elérhető
    h.roots.append(a)
    print("felszabadítva:", h.collect())  # ['c', 'd'] — a kör nem gond
    print("túlélők kora:", [(o.name, o.age) for o in h.objects])
```

## Rendszerhívások
<!-- q: Mi az a rendszerhívás, mennyibe kerül, és hogyan kezeljem helyesen a hibáit? -->
<!-- tags: system call, syscall, kernel mode, errno, eintr, strace, vdso, partial write -->

A rendszerhívással a felhasználói módban futó program a kernelhez fordul (fájl, hálózat,
memória, folyamat): x86-64 Linuxon a paraméterek regiszterekben mennek, a `syscall` utasítás
kernel módba vált, a hibát negatív érték jelzi, amiből a libc `errno`-t állít és -1-et ad
vissza. Egy hívás nagyjából 100 ns nagyságrendű (a Spectre/Meltdown-védelmek ezt növelik), ezért
pufferelünk és kötegelünk (writev, sendmmsg, io_uring); néhány gyakori hívás (clock_gettime) a
vDSO-n át kernelváltás nélkül fut. Helyes használat: az `errno` csak hiba után értelmes, jel
megszakíthatja a hívást (EINTR), a read/write részleges eredményt adhat, a fájlleírókat
O_CLOEXEC-kel nyisd; a `strace` megmutatja az összes hívást.

```c
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>

/* A write részleges írást is végezhet (pipe, socket), és jel megszakíthatja: ciklus kell */
ssize_t write_all(int fd, const void *buf, size_t len) {
    const char *p = buf;
    size_t left = len;
    while (left > 0) {
        ssize_t n = write(fd, p, left);
        if (n < 0) {
            if (errno == EINTR) continue;  /* jel szakította meg: újra */
            return -1;
        }
        p += n;
        left -= (size_t)n;
    }
    return (ssize_t)len;
}

int main(void) {
    /* libc-csomagoló és közvetlen rendszerhívás: ugyanaz az eredmény */
    printf("getpid()=%d syscall(SYS_getpid)=%ld\n", getpid(), syscall(SYS_getpid));

    /* O_CLOEXEC: exec után ne öröklődjön a leíró (szivárgás és biztonsági hiba ellen) */
    int fd = open("/tmp/syscall-demo.txt", O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
    if (fd < 0) {
        fprintf(stderr, "open: %s\n", strerror(errno));  /* errno csak hiba után értelmes */
        return 1;
    }
    const char msg[] = "egy rendszerhívással kiírva\n";
    if (write_all(fd, msg, sizeof msg - 1) < 0) perror("write");
    if (close(fd) < 0) perror("close");  /* a close is jelezhet (késleltetett) írási hibát */

    if (open("/nincs/ilyen", O_RDONLY) < 0)
        printf("várt hiba: errno=%d (%s)\n", errno, strerror(errno));  /* ENOENT */
    return 0;  /* nyomkövetés: strace -f ./prog */
}
```

## Fájlrendszer, page cache és tartós írás
<!-- q: Hogyan kerül az adat a lemezre, mi a page cache, és hogyan írjak fájlt atomikusan és tartósan? -->
<!-- tags: file system, page cache, fsync, inode, atomic rename, durability, journaling, write-back -->

Az írás alapból a page cache-be (RAM) megy, a kernel később írja ki a „piszkos” lapokat;
olvasáskor előreolvasás (read-ahead) gyorsít. Áramszünetnél a ki nem írt adat elveszik, ezért
tartóssághoz `fsync` kell — ez lassú (milliszekundumok), ezért az adatbázisok kötegelik (group
commit). A fájl metaadata az inode-ban van (méret, jogok, blokkok helye), a név csak egy
könyvtárbejegyzés, ami az inode-ra mutat. Atomikus csere: ideiglenes fájl ugyanazon a
fájlrendszeren, írás + fsync, `rename` (atomikusan cseréli a bejegyzést), végül a könyvtár
fsync-je. A naplózó (ext4, NTFS) és copy-on-write (btrfs, ZFS, APFS) fájlrendszerek a saját
konzisztenciájukat védik, nem az alkalmazás adatait; a sikertelen fsync után a page cache
állapota nem megbízható.

```python
import os
import tempfile

def atomic_write(path: str, data: bytes) -> None:
    """Az olvasó vagy a régi, vagy a teljes új tartalmat látja — összeomlás után is."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp-")  # ugyanazon a fájlrendszeren!
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()  # Python-puffer -> kernel (page cache)
            os.fsync(f.fileno())  # page cache -> lemez
        os.replace(tmp, path)  # atomikus csere: a bejegyzés egy lépésben vált az új inode-ra
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    if hasattr(os, "O_DIRECTORY"):  # POSIX: maga az átnevezés is legyen tartós
        dfd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)

def describe(path: str) -> None:
    st = os.stat(path)
    # A név csak könyvtárbejegyzés; hard link = több név ugyanarra az inode-ra
    print(f"inode={st.st_ino} méret={st.st_size} linkek={st.st_nlink}")

if __name__ == "__main__":
    p = os.path.join(tempfile.gettempdir(), "config.json")
    atomic_write(p, b'{"version": 1}')
    describe(p)
    atomic_write(p, b'{"version": 2}')
    describe(p)  # új inode: a csere új fájlt jelent, nem helyben írást
```

## I/O-modellek: blokkoló, nem blokkoló és epoll
<!-- q: Milyen I/O modellek vannak, és hogyan kezel egy szál több ezer kapcsolatot epoll-lal? -->
<!-- tags: io models, epoll, kqueue, select, non-blocking io, event loop, c10k, readiness -->

A blokkoló I/O-nál egy szál egy kapcsolatot szolgál ki — egyszerű, de ezres nagyságrendben
elfogy a memória és sok a kontextusváltás. A nem blokkoló I/O + készenléti értesítés (select és
poll O(n), epoll Linuxon, kqueue BSD/macOS alatt O(kész leírók)) egyetlen szállal több tízezer
kapcsolatot kezel: a kernel szól, melyik leíró olvasható/írható, és csak azon hívunk read-et
vagy write-ot. A befejezés-alapú modell (Windows IOCP, Linux io_uring) ennél tovább megy: a
kernel maga végzi el az I/O-t. Buktatók: élvezérelt (EPOLLET) módban addig kell olvasni, amíg
EAGAIN nem jön; a write részleges lehet, ilyenkor kimenő puffer és EPOLLOUT kell; több worker
esetén SO_REUSEPORT vagy EPOLLEXCLUSIVE a „thundering herd” ellen.

```c
#define _GNU_SOURCE
#include <errno.h>
#include <netinet/in.h>
#include <stdio.h>
#include <sys/epoll.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_EVENTS 64

int main(void) {  /* egyszálú, nem blokkoló echo szerver epoll-lal (szintvezérelt mód) */
    int lfd = socket(AF_INET, SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);
    int one = 1;
    setsockopt(lfd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);  /* gyors újraindítás */
    struct sockaddr_in addr = {.sin_family = AF_INET, .sin_port = htons(9000),
                               .sin_addr.s_addr = htonl(INADDR_LOOPBACK)};
    if (bind(lfd, (struct sockaddr *)&addr, sizeof addr) < 0 || listen(lfd, SOMAXCONN) < 0) {
        perror("bind/listen");
        return 1;
    }
    int ep = epoll_create1(EPOLL_CLOEXEC);
    struct epoll_event ev = {.events = EPOLLIN, .data.fd = lfd};
    epoll_ctl(ep, EPOLL_CTL_ADD, lfd, &ev);

    struct epoll_event events[MAX_EVENTS];
    char buf[4096];
    for (;;) {
        int n = epoll_wait(ep, events, MAX_EVENTS, -1);  /* alszik, amíg valamelyik leíró kész */
        if (n < 0) {
            if (errno == EINTR) continue;
            perror("epoll_wait");
            break;
        }
        for (int i = 0; i < n; i++) {
            int fd = events[i].data.fd;
            if (fd == lfd) {  /* új kapcsolatok: addig fogadunk, amíg EAGAIN nem jön */
                int cfd;
                while ((cfd = accept4(lfd, NULL, NULL, SOCK_NONBLOCK | SOCK_CLOEXEC)) >= 0) {
                    struct epoll_event cev = {.events = EPOLLIN | EPOLLRDHUP, .data.fd = cfd};
                    epoll_ctl(ep, EPOLL_CTL_ADD, cfd, &cev);
                }
                continue;
            }
            ssize_t r = read(fd, buf, sizeof buf);  /* kész leíró: nem blokkol */
            if (r > 0 && write(fd, buf, (size_t)r) < 0 && errno != EAGAIN) r = 0;
            /* egyszerűsítés: élesben a részleges írás maradékát kliensenkénti pufferben
             * tartjuk, és EPOLLOUT-ra iratkozunk, amíg ki nem ürül (backpressure) */
            if (r == 0 || (r < 0 && errno != EAGAIN)) {  /* bontás vagy hiba */
                epoll_ctl(ep, EPOLL_CTL_DEL, fd, NULL);
                close(fd);
            }
        }
    }
    close(ep);
    close(lfd);
    return 0;
}
```

## Befejezés-alapú I/O: io_uring (és IOCP)
<!-- q: Mi az io_uring, és miben különbözik az epolltól? -->
<!-- tags: io_uring, iocp, completion based io, async io, submission queue, liburing, linux -->

Az io_uring (Linux 5.1+) két, a kernellel megosztott gyűrűpuffert használ: a program a
beküldési sorba (SQ) teszi a kéréseket (olvasás, írás, accept, fsync…), a kernel elvégzi őket, és
az eredményt a befejezési sorba (CQ) írja. Sok művelet egyetlen rendszerhívással (SQPOLL módban
akár hívás nélkül) küldhető be, és valódi aszinkron fájl-I/O is lehetséges — az epoll fájlokra
nem működik. A Windows IOCP ugyanezt a befejezés-alapú modellt követi. Buktatók: a befejezések
sorrendje tetszőleges (azonosító kell a kérésekhez), a puffereknek a befejezésig élniük kell, a
hibát negatív errno jelzi a `res` mezőben, és biztonsági okokból sok környezet (pl. alapértelmezett
konténer-seccomp profilok) tiltja.

```c
#include <fcntl.h>
#include <liburing.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define QD 8      /* sor mélysége */
#define BS 4096   /* blokkméret */

int main(int argc, char **argv) {  /* fordítás: gcc uring.c -luring */
    if (argc < 2) {
        fprintf(stderr, "használat: %s <fájl>\n", argv[0]);
        return 1;
    }
    int fd = open(argv[1], O_RDONLY);
    if (fd < 0) { perror("open"); return 1; }

    struct io_uring ring;
    int ret = io_uring_queue_init(QD, &ring, 0);
    if (ret < 0) { fprintf(stderr, "queue_init: %s\n", strerror(-ret)); return 1; }

    char *bufs[QD];  /* a puffereknek a befejezésig élniük kell */
    for (int i = 0; i < QD; i++) {
        bufs[i] = malloc(BS);
        struct io_uring_sqe *sqe = io_uring_get_sqe(&ring);  /* üres beküldési bejegyzés */
        io_uring_prep_read(sqe, fd, bufs[i], BS, (unsigned long long)i * BS);
        io_uring_sqe_set_data(sqe, (void *)(long)i);  /* azonosító a válasz párosításához */
    }
    printf("beküldve: %d kérés egy hívással\n", io_uring_submit(&ring));

    long total = 0;
    for (int done = 0; done < QD; done++) {
        struct io_uring_cqe *cqe;
        if ((ret = io_uring_wait_cqe(&ring, &cqe)) < 0) {
            fprintf(stderr, "wait_cqe: %s\n", strerror(-ret));
            break;
        }
        long idx = (long)io_uring_cqe_get_data(cqe);
        if (cqe->res < 0)  /* hiba: negatív errno a res mezőben */
            fprintf(stderr, "#%ld: %s\n", idx, strerror(-cqe->res));
        else
            total += cqe->res;  /* a befejezések sorrendje tetszőleges */
        io_uring_cqe_seen(&ring, cqe);  /* a CQ-bejegyzés visszaadása a kernelnek */
    }
    printf("összesen beolvasva: %ld bájt\n", total);

    for (int i = 0; i < QD; i++) free(bufs[i]);
    io_uring_queue_exit(&ring);
    close(fd);
    return 0;
}
```

## Jelek (signals) és szabályos leállás
<!-- q: Hogyan kezeljem a Unix jeleket (SIGTERM, SIGINT) biztonságosan? -->
<!-- tags: signals, sigaction, sigterm, sigint, async-signal-safe, graceful shutdown, sigpipe, signalfd -->

A jel aszinkron értesítés a folyamatnak: SIGINT (Ctrl+C), SIGTERM (leállítási kérés, pl.
Kubernetes-től), SIGHUP (gyakran: konfiguráció újratöltése), SIGCHLD (gyerek kilépett), SIGSEGV
(érvénytelen memória); a SIGKILL és SIGSTOP nem kezelhető. A kezelő bármely utasítás közepén
lefuthat, ezért benne csak aszinkron-jelbiztos függvény hívható (write igen; printf, malloc,
mutex nem) — a bevált minta: a kezelő csak egy `volatile sig_atomic_t` jelzőt állít, a fő ciklus
pedig ezt figyeli. `sigaction`-t használj a `signal` helyett, a SIGPIPE-ot hálózati
programokban hagyd figyelmen kívül (EPIPE hibát kapsz helyette); többszálú programban a jeleket
blokkold minden szálban, és egy dedikált szálban `sigwait`-tel vagy `signalfd`-vel kezeld.

```c
#define _POSIX_C_SOURCE 200809L
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static volatile sig_atomic_t stop_requested = 0;
static volatile sig_atomic_t reload_requested = 0;

static void on_signal(int sig) {
    /* Csak jelbiztos műveletek: jelző állítása és write(); printf/malloc TILOS */
    if (sig == SIGTERM || sig == SIGINT) stop_requested = 1;
    else if (sig == SIGHUP) reload_requested = 1;
    const char msg[] = "[jel érkezett]\n";
    (void)!write(STDERR_FILENO, msg, sizeof msg - 1);
}

int main(void) {
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = on_signal;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_RESTART;  /* a megszakított hívások többsége automatikusan újraindul */
    sigaction(SIGTERM, &sa, NULL);
    sigaction(SIGINT, &sa, NULL);
    sigaction(SIGHUP, &sa, NULL);
    signal(SIGPIPE, SIG_IGN);  /* zárt socketbe írás ne ölje meg a folyamatot */

    printf("pid=%d — leállítás: kill -TERM %d\n", getpid(), getpid());
    while (!stop_requested) {  /* a fő ciklusban már bármit hívhatunk */
        if (reload_requested) {
            reload_requested = 0;
            printf("konfiguráció újratöltése...\n");
        }
        sleep(1);  /* jel érkezésekor korábban visszatér */
    }
    printf("szabályos leállás: kapcsolatok lezárása, pufferek ürítése...\n");
    return 0;
}
```

## IPC: névtelen és nevesített pipe-ok
<!-- q: Hogyan működnek a pipe-ok, és hogyan valósítja meg a shell a parancsláncot? -->
<!-- tags: ipc, pipe, fifo, dup2, fork, shell pipeline, eof, sigpipe -->

A névtelen pipe egyirányú, kernelpufferelt (Linuxon alapból 64 KiB) bájtcsatorna rokon
folyamatok között: tele pufferbe írás és üresből olvasás blokkol, ami természetes backpressure.
Ha minden író vég bezárult, az olvasó EOF-ot kap; ha minden olvasó bezárult, az író SIGPIPE-ot
vagy EPIPE-et. A shell `ls | wc -l` így működik: pipe, két fork, `dup2`-vel a stdout/stdin
átirányítása, majd exec. A leggyakoribb hiba a nem használt pipe-végek lezárásának elmulasztása
— ilyenkor az olvasó sosem kap EOF-ot és beragad. A nevesített pipe (FIFO, `mkfifo`) nem rokon
folyamatok között is működik; PIPE_BUF (4096 bájt) méretig az írás atomikus, így több író
üzenetei nem keverednek.

```c
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

static void die(const char *m) { perror(m); exit(1); }

int main(void) {  /* megfelel ennek: ls -l /usr/bin | wc -l */
    int fds[2];  /* fds[0]: olvasó vég, fds[1]: író vég */
    if (pipe(fds) < 0) die("pipe");

    pid_t left = fork();
    if (left < 0) die("fork");
    if (left == 0) {  /* 1. gyerek: stdout -> pipe író vége */
        dup2(fds[1], STDOUT_FILENO);
        close(fds[0]);  /* a nem használt végeket MINDENHOL le kell zárni, */
        close(fds[1]);  /* különben az olvasó sosem kap EOF-ot */
        execlp("ls", "ls", "-l", "/usr/bin", (char *)NULL);
        _exit(127);
    }

    pid_t right = fork();
    if (right < 0) die("fork");
    if (right == 0) {  /* 2. gyerek: stdin <- pipe olvasó vége */
        dup2(fds[0], STDIN_FILENO);
        close(fds[0]);
        close(fds[1]);
        execlp("wc", "wc", "-l", (char *)NULL);
        _exit(127);
    }

    close(fds[0]);  /* a szülő egyik véget sem használja */
    close(fds[1]);
    int st_left, st_right;
    waitpid(left, &st_left, 0);
    waitpid(right, &st_right, 0);
    return WIFEXITED(st_right) ? WEXITSTATUS(st_right) : 1;
}
```

## IPC: osztott memória
<!-- q: Hogyan osszak meg memóriát folyamatok között, és mire figyeljek közben? -->
<!-- tags: shared memory, ipc, mmap, shm_open, multiprocessing, synchronization, zero-copy -->

Az osztott memória ugyanazokat a fizikai lapokat képezi le több folyamat címterébe: ez a
leggyorsabb IPC, mert nincs másolás és nincs hozzáférésenkénti rendszerhívás — nagy adatok
(képek, tenzorok, gyorsítótárak) átadására ideális. Alatta POSIX `shm_open` + `mmap` (Linuxon
/dev/shm), illetve fájl `MAP_SHARED` leképezése áll, Windowson névvel ellátott fájlleképezés. A
szinkronizáció teljesen a mi felelősségünk: folyamatok közötti zár, szemafor vagy atomikus
műveletek kellenek, és a nem egyértelmű elrendezés (struktúra-igazítás, bájtsorrend) hibákhoz
vezet. Buktatók: a szegmenst valakinek törölnie kell (unlink), különben a folyamatok után is
megmarad; a jogosultságokat szűkre kell szabni.

```python
import struct
from multiprocessing import Lock, Process, shared_memory

COUNTER = struct.Struct("q")  # 8 bájtos előjeles egész a megosztott blokk elején

def worker(shm_name: str, lock, n: int) -> None:
    shm = shared_memory.SharedMemory(name=shm_name)  # csatlakozás név alapján
    try:
        for _ in range(n):
            with lock:  # zár nélkül az olvasás-módosítás-írás versenyhelyzet lenne
                (v,) = COUNTER.unpack_from(shm.buf, 0)
                COUNTER.pack_into(shm.buf, 0, v + 1)
    finally:
        shm.close()  # csak a saját leképezést bontja

if __name__ == "__main__":
    shm = shared_memory.SharedMemory(create=True, size=COUNTER.size)
    try:
        COUNTER.pack_into(shm.buf, 0, 0)
        lock = Lock()
        procs = [Process(target=worker, args=(shm.name, lock, 10_000)) for _ in range(4)]
        for p in procs:
            p.start()
        for p in procs:
            p.join()
        print("számláló:", COUNTER.unpack_from(shm.buf, 0)[0])  # 40000
    finally:
        shm.close()
        shm.unlink()  # a létrehozó törli, különben a szegmens megmarad
```

## IPC: Unix domain socketek és fájlleíró-átadás
<!-- q: Mire jók a Unix domain socketek, és hogyan azonosítom a kapcsolódó folyamatot? -->
<!-- tags: unix domain socket, ipc, so_peercred, scm_rights, file descriptor passing, docker socket -->

A Unix domain socket a megszokott socket API-t adja fájlrendszerbeli címmel, kizárólag helyi
kommunikációra: gyorsabb a TCP loopbacknél (nincs TCP/IP-verem), a hozzáférést a socket-fájl
jogosultságai szabályozzák, és a kernel igazolja a másik fél azonosítóit (SO_PEERCRED: pid, uid,
gid). Különlegessége, hogy nyitott fájlleírót is át lehet adni rajta (SCM_RIGHTS) — így adja át
a systemd a socketeket, és így működik a jogosultság-szétválasztás. A Docker, a systemd, a
PostgreSQL és sok helyi démon ezt használja. Buktatók: a socket-fájlt induláskor el kell
távolítani, ha a régi bennmaradt, a jogosultságot szűkre kell állítani (a Docker-socket
elérése gyakorlatilag root-jog), és az SO_PEERCRED Linux-specifikus.

```python
import os
import socket
import struct
import tempfile
import threading

SOCK_PATH = os.path.join(tempfile.gettempdir(), "demo.sock")

def server(ready: threading.Event) -> None:
    if os.path.exists(SOCK_PATH):
        os.unlink(SOCK_PATH)  # bent maradt régi socket-fájl eltávolítása
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.bind(SOCK_PATH)
        os.chmod(SOCK_PATH, 0o600)  # csak a tulajdonos csatlakozhat
        s.listen()
        ready.set()
        conn, _ = s.accept()
        with conn:
            # A kernel által igazolt azonosítók (Linux): ezzel hitelesíthető a kliens
            creds = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
            pid, uid, gid = struct.unpack("3i", creds)
            print(f"kliens: pid={pid} uid={uid} gid={gid}")
            msg, fds, _, _ = socket.recv_fds(conn, 1024, maxfds=1)  # üzenet + átadott fájlleíró
            with os.fdopen(fds[0], "r") as f:  # a kliens által megnyitott fájlt olvassuk
                print("üzenet:", msg.decode(), "| első sor:", f.readline().strip())
    os.unlink(SOCK_PATH)

if __name__ == "__main__":
    ready = threading.Event()
    t = threading.Thread(target=server, args=(ready,))
    t.start()
    ready.wait()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as c, open(__file__) as f:
        c.connect(SOCK_PATH)
        socket.send_fds(c, [b"itt egy nyitott fajl"], [f.fileno()])  # SCM_RIGHTS
    t.join()
```

## Konténerek belülről: namespace-ek és cgroupok
<!-- q: Hogyan működnek a konténerek a Linux kernel szintjén (namespace-ek, cgroupok)? -->
<!-- tags: containers, namespaces, cgroups, docker, isolation, pid namespace, resource limits, linux -->

A konténer nem virtuális gép, hanem közönséges folyamat, amit a kernel elszigetel. A
namespace-ek azt szabályozzák, mit lát a folyamat: saját PID-tér (benne ő a PID 1), mount-tér
(saját gyökér-fájlrendszer pivot_root-tal), hálózat, hostnév (UTS), IPC, felhasználók (user
namespace: konténeren belüli root kívül jogtalan felhasználó) és cgroup. A cgroupok (v2) azt
szabályozzák, mennyit használhat: memória (felette OOM-kill a csoporton belül), CPU-kvóta,
I/O, folyamatszám. A teljes képhez a capabilities szűkítése, a seccomp rendszerhívás-szűrő és
az LSM (AppArmor, SELinux) is hozzátartozik. Mivel a kernel közös, egy kernelsebezhetőség
kitörést tehet lehetővé — erősebb elszigeteléshez gVisor vagy mikro-VM (Firecracker) kell.

```go
//go:build linux

package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"syscall"
)

// Futtatás rootként: go run main.go run /bin/sh
func main() {
	switch {
	case len(os.Args) > 2 && os.Args[1] == "run":
		parent()
	case len(os.Args) > 2 && os.Args[1] == "child":
		child()
	default:
		fmt.Println("használat: run <parancs> [arg...]")
	}
}

func parent() {
	// Önmagunkat indítjuk újra "child" módban, ÚJ namespace-ekben
	cmd := exec.Command("/proc/self/exe", append([]string{"child"}, os.Args[2:]...)...)
	cmd.Stdin, cmd.Stdout, cmd.Stderr = os.Stdin, os.Stdout, os.Stderr
	cmd.SysProcAttr = &syscall.SysProcAttr{
		Cloneflags: syscall.CLONE_NEWUTS | syscall.CLONE_NEWPID | syscall.CLONE_NEWNS | syscall.CLONE_NEWNET,
	}
	must(cmd.Start())
	// Egyszerűsítés: élesben a cgroupot még az indítás ELŐTT kell beállítani
	// (pl. clone3 CLONE_INTO_CGROUP), különben a gyerek korlát nélkül forkolhat.
	limit(cmd.Process.Pid)
	_ = cmd.Wait()
}

func child() {
	must(syscall.Sethostname([]byte("kontener"))) // UTS namespace: csak itt változik
	// Privát mount-propagáció, majd saját /proc: a ps csak a konténer folyamatait látja
	// (ebben a PID namespace-ben ez a "child" folyamat a PID 1)
	must(syscall.Mount("", "/", "", syscall.MS_REC|syscall.MS_PRIVATE, ""))
	must(syscall.Mount("proc", "/proc", "proc", 0, ""))
	defer syscall.Unmount("/proc", 0)
	cmd := exec.Command(os.Args[2], os.Args[3:]...)
	cmd.Stdin, cmd.Stdout, cmd.Stderr = os.Stdin, os.Stdout, os.Stderr
	must(cmd.Run())
}

// cgroup v2: a korlátok egyszerű fájlírások a /sys/fs/cgroup alatt
func limit(pid int) {
	cg := "/sys/fs/cgroup/demo-container"
	must(os.MkdirAll(cg, 0o755))
	write := func(file, val string) { must(os.WriteFile(filepath.Join(cg, file), []byte(val), 0o644)) }
	write("memory.max", "100M")              // felette OOM-kill a csoporton belül
	write("pids.max", "64")                  // fork-bomba ellen
	write("cpu.max", "50000 100000")         // 50 ms CPU / 100 ms periódus = fél mag
	write("cgroup.procs", strconv.Itoa(pid)) // a folyamat és leszármazottai a csoportba kerülnek
}

func must(err error) {
	if err != nil {
		panic(err)
	}
}
```
