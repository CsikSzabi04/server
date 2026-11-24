# C
<!-- tech: c -->
<!-- aliases: c99, c11, c17, c23, ansi c -->

A C egy alacsony szintű, statikusan (de gyengén) típusos, natív kódra fordított rendszerprogramozási nyelv. Nincs szemétgyűjtő és nincs futásidejű ellenőrzés: a memória élettartamáért, a tömbhatárokért és a szálbiztonságért a programozó felel, cserébe teljes kontrollt, kis binárist és kiszámítható teljesítményt kapsz. Operációs rendszerek, beágyazott rendszerek, adatbázisok, interpreterek és nagy teljesítményű könyvtárak nyelve; a stabil ABI miatt szinte minden más nyelv FFI-je C-n keresztül kommunikál. Jó választás, ha hardverközeli kontroll vagy maximális hordozhatóság kell; rossz választás, ha a gyors fejlesztés és a memóriabiztonság fontosabb (ott Rust, Go, C#).

## Memória-elrendezés: stack, heap, data, bss
<!-- q: Hogyan néz ki egy C program memóriája, mi a stack és a heap? -->
<!-- tags: memory layout, stack, heap, data segment, bss, rodata, storage duration -->

Egy futó C program címtere szegmensekből áll: `.text` (kód), `.rodata` (csak olvasható konstansok, string literálok), `.data` (inicializált globálisok), `.bss` (nullázott globálisok), a heap (malloc) és a stack (lokális változók, hívási keretek). A tárolási idő (storage duration) dönti el, hol él egy objektum: automatikus (stack, a blokk végéig), statikus (a program teljes futása), dinamikus (malloc-tól free-ig). A leggyakoribb hiba a stack-objektumra mutató pointer visszaadása: a keret a return után megszűnik, a pointer lógó (dangling) lesz.

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int g_init = 42;                 // .data: inicializált globális, a binárisban tárolódik
int g_zero;                      // .bss: nullázott globális, csak a mérete kerül a fájlba
const char g_text[] = "const";   // .rodata: csak olvasható adat

static int next_id(void) {
    static int id = 0;           // statikus élettartam (.bss), de csak itt látható
    return ++id;
}

/* HIBÁS minta (ne írd így):
static int *bad(void) {
    int local = 5;
    return &local;               // a keret a return után megszűnik -> lógó pointer, UB
}
*/

int main(void) {
    int local = 7;                          // stack: automatikus élettartam
    char *heap = malloc(64);                // heap: az élettartamot mi kezeljük
    if (heap == NULL) return EXIT_FAILURE;
    strcpy(heap, "heap adat");

    printf("data  : %p\n", (void *)&g_init);
    printf("bss   : %p\n", (void *)&g_zero);
    printf("rodata: %p\n", (void *)g_text);
    printf("heap  : %p (%s)\n", (void *)heap, heap);
    printf("stack : %p (%d)\n", (void *)&local, local);  // tipikusan magas cím, lefelé nő

    int a = next_id();                      // külön utasítások: a függvényargumentumok
    int b = next_id();                      // kiértékelési sorrendje NEM specifikált
    printf("id: %d %d\n", a, b);

    free(heap);                             // minden malloc-hoz pontosan egy free
    return 0;
}
```

## Pointerek és pointer-aritmetika
<!-- q: Hogyan működnek a pointerek és a pointer-aritmetika C-ben? -->
<!-- tags: pointers, pointer arithmetic, ptrdiff_t, const, dereference, one past the end -->

A pointer egy memóriacím típusinformációval; a `p + 1` nem egy bájtot, hanem `sizeof(*p)` bájtot lép. Két pointer különbsége csak ugyanazon tömbön belül értelmezett, és elemszámot ad (`ptrdiff_t`). A tömb utáni „one past the end” pointer képezhető (ciklusvégnek), de nem dereferálható; ennél tovább lépni már UB. A `const` helye számít: `const int *p` az értéket védi, `int *const p` magát a pointert.

```c
#include <stddef.h>
#include <stdio.h>

// Az első negatív elem címe, vagy NULL. [begin, end) félig nyílt tartomány.
static const int *find_negative(const int *begin, const int *end) {
    for (const int *p = begin; p != end; ++p)   // ++p sizeof(int) bájtot lép
        if (*p < 0) return p;
    return NULL;
}

// Pointer a pointerre: a hívó változóját módosítjuk (kimeneti paraméter).
static void advance(const char **cursor, size_t n) {
    *cursor += n;
}

int main(void) {
    int data[] = {4, 8, 15, -16, 23, 42};
    size_t n = sizeof data / sizeof data[0];
    const int *end = data + n;           // "one past the end": képezhető, NEM dereferálható

    const int *hit = find_negative(data, end);
    if (hit) {
        ptrdiff_t idx = hit - data;      // különbség elemszámban
        printf("negativ: %d a(z) %td. indexen\n", *hit, idx);
    }

    // data[i] pontosan *(data + i)
    printf("%d == %d\n", data[2], *(data + 2));

    // Bájtszintű bejárás: unsigned char*-on át BÁRMELY objektum bájtjai olvashatók
    const unsigned char *bytes = (const unsigned char *)&data[0];
    for (size_t i = 0; i < sizeof data[0]; ++i)
        printf("%02x ", bytes[i]);       // little-endian gépen: 04 00 00 00
    printf("\n");

    const char *s = "kulcs=ertek";
    advance(&s, 6);
    printf("%s\n", s);                   // "ertek"

    int x = 1, y = 2;
    const int *pc = &x;                  // *pc nem írható, pc átállítható
    int *const cp = &x;                  // cp nem állítható át, *cp írható
    pc = &y;
    *cp = 10;
    printf("%d %d\n", *pc, x);           // 2 10
    return 0;
}
```

## Tömbök és a pointer decay
<!-- q: Mi a különbség a tömb és a pointer között C-ben, miért rossz a sizeof a függvényben? -->
<!-- tags: arrays, array decay, sizeof, multidimensional arrays, pointer to array -->

A legtöbb kifejezésben a tömb automatikusan az első elemére mutató pointerré „bomlik” (decay), ezért függvényparaméterként az `int arr[]` valójában `int *arr`, és a `sizeof` ott a pointer méretét adja. A tömb hosszát ezért mindig külön paraméterként kell átadni. A többdimenziós tömb egyetlen folytonos blokk, a belső dimenziókat a fordítónak ismernie kell a címszámításhoz; az `int (*row)[COLS]` egy teljes sorra mutat, a `row + 1` egy egész sort lép.

```c
#include <stddef.h>
#include <stdio.h>

#define ROWS 3
#define COLS 4

// A paraméterben "int arr[]" == "int *arr": a méret elveszik!
static size_t wrong_count(int arr[]) {
    return sizeof arr / sizeof arr[0];   // sizeof(int*)/sizeof(int) -> 2 x86-64-en: HIBÁS
}

// Helyes: a hossz külön paraméter
static long sum(const int *arr, size_t n) {
    long s = 0;
    for (size_t i = 0; i < n; ++i) s += arr[i];
    return s;
}

// 2D tömb: a belső dimenzió (COLS) kell a grid[i][j] címének kiszámításához
static int trace(int m[][COLS], size_t rows) {
    int t = 0;
    for (size_t i = 0; i < rows && i < COLS; ++i) t += m[i][i];
    return t;
}

int main(void) {
    int v[] = {1, 2, 3, 4, 5};
    size_t n = sizeof v / sizeof v[0];   // itt működik: v valódi tömb ebben a scope-ban
    printf("valodi: %zu, fuggvenyben: %zu, osszeg: %ld\n", n, wrong_count(v), sum(v, n));

    int grid[ROWS][COLS] = {{1, 2, 3, 4}, {5, 6, 7, 8}, {9, 10, 11, 12}};
    int (*row)[COLS] = grid;             // pointer egy 4 elemű int tömbre
    printf("grid[1][2] = %d\n", (*(row + 1))[2]);            // 7
    printf("folytonos: %td\n", &grid[1][0] - &grid[0][0]);   // 4
    printf("trace = %d\n", trace(grid, ROWS));               // 1 + 6 + 11

    // &v és v ugyanarra a címre mutat, de más a típusuk: int (*)[5] vs int *
    printf("%p %p, sizeof(&v)=%zu\n", (void *)&v, (void *)v, sizeof(&v));
    return 0;
}
```

## Stringek és biztonságos pufferkezelés
<!-- q: Hogyan kezeljem biztonságosan a stringeket és puffereket C-ben? -->
<!-- tags: strings, null terminator, snprintf, strncpy, buffer overflow, strtok -->

A C string egy `'\0'`-ra végződő `char` tömb: a hossz nincs tárolva, a `strlen` O(n), és a lezáró nulla hiánya puffertúlolvasáshoz vezet. A `strcpy`/`sprintf`/`gets` nem ismerik a célpuffer méretét, ezért buffer overflow-forrásai; használj `snprintf`-et (a visszatérési értéke a szükséges hossz, így a csonkolás detektálható). A `strncpy` csapda: ha a forrás nem fér el, NEM teszi ki a lezáró nullát. A string literál a `.rodata`-ban van, írása UB, ezért mindig `const char *`-ként kezeld.

```c
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

// Biztonságos másolás: mindig lezárja a célt és jelzi a csonkolást.
static bool str_copy(char *dst, size_t cap, const char *src) {
    if (cap == 0) return false;
    size_t len = strlen(src);
    if (len >= cap) {                 // a '\0'-val együtt nem fér el
        memcpy(dst, src, cap - 1);
        dst[cap - 1] = '\0';
        return false;                 // csonkolva
    }
    memcpy(dst, src, len + 1);        // +1: a lezáró nulla is
    return true;
}

// Tokenizálás strtok nélkül (a strtok globális állapotot tart, nem reentráns).
static void split_csv(const char *line) {
    const char *start = line;
    for (;;) {
        const char *comma = strchr(start, ',');
        size_t len = comma ? (size_t)(comma - start) : strlen(start);
        printf("mezo: '%.*s'\n", (int)len, start);   // %.*s: hosszkorlátos kiírás
        if (!comma) break;
        start = comma + 1;
    }
}

int main(void) {
    char name[8];
    if (!str_copy(name, sizeof name, "nagyon_hosszu_nev"))
        printf("csonkolva: %s\n", name);

    // snprintf: a visszatérési érték a SZÜKSÉGES hossz -> csonkolás detektálható
    char buf[16];
    int need = snprintf(buf, sizeof buf, "user=%s id=%d", "anna", 12345);
    if (need < 0 || (size_t)need >= sizeof buf)
        printf("snprintf csonkolt (%d bajt kellett)\n", need);

    // strncpy CSAPDA: ha nem fér el, nem zárja le -> kézzel kell
    char small[4];
    strncpy(small, "abcdef", sizeof small);
    small[sizeof small - 1] = '\0';

    const char *lit = "fix";          // literál: csak olvasható
    char arr[] = "fix";               // másolat a stacken: írható
    arr[0] = 'm';

    split_csv("alma,korte,,szilva");
    printf("%s %s %s\n", small, lit, arr);
    return 0;
}
```

## Dinamikus memória: malloc, realloc, free
<!-- q: Hogyan használjam helyesen a malloc, realloc és free függvényeket? -->
<!-- tags: malloc, realloc, calloc, free, dynamic array, memory leak, double free, use after free -->

A heap-memóriát `malloc`/`calloc` foglalja és `free` szabadítja fel; minden foglaláshoz pontosan egy felszabadítás tartozik. A `realloc` csapdája: ha `NULL`-t ad vissza, az eredeti blokk érintetlen marad, ezért ideiglenes pointerbe kell fogadni, különben leak keletkezik. Mindig ellenőrizd a visszatérési értéket és a méretszorzás túlcsordulását. Tipikus hibák: use-after-free, double free, leak; ezeket AddressSanitizer (`-fsanitize=address`) vagy Valgrind fogja meg.

```c
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct {
    int    *items;
    size_t  len;
    size_t  cap;
} IntVec;

// Geometrikus növekedés (x2): a push amortizáltan O(1).
static int vec_push(IntVec *v, int value) {
    if (v->len == v->cap) {
        size_t new_cap = v->cap ? v->cap * 2 : 8;
        if (new_cap > SIZE_MAX / sizeof *v->items) return -1;   // szorzás-túlcsordulás
        // realloc NULL esetén az eredeti blokk megmarad -> NE írd felül azonnal v->items-et!
        int *tmp = realloc(v->items, new_cap * sizeof *tmp);
        if (!tmp) return -1;
        v->items = tmp;
        v->cap = new_cap;
    }
    v->items[v->len++] = value;
    return 0;
}

static void vec_free(IntVec *v) {
    free(v->items);          // free(NULL) megengedett, no-op
    v->items = NULL;         // lógó pointer és double free ellen
    v->len = v->cap = 0;
}

int main(void) {
    IntVec v = {0};
    for (int i = 0; i < 100; ++i) {
        if (vec_push(&v, i * i) != 0) { vec_free(&v); return 1; }
    }

    // calloc: nullázott memória és beépített n*size túlcsordulás-ellenőrzés
    double *zeros = calloc(v.len, sizeof *zeros);
    if (!zeros) { vec_free(&v); return 1; }

    printf("len=%zu cap=%zu utolso=%d\n", v.len, v.cap, v.items[v.len - 1]);

    // Tipikus hibák (NE):
    //  free(p); p[0] = 1;     -> use-after-free
    //  free(p); free(p);      -> double free, heap-korrupció
    //  p = realloc(p, n);     -> hiba esetén az eredeti blokk elveszik (leak)
    free(zeros);
    vec_free(&v);
    return 0;
}
```

## Undefined behaviour (UB)
<!-- q: Mi az undefined behaviour C-ben és hogyan védekezzek ellene? -->
<!-- tags: undefined behavior, ub, signed overflow, sanitizers, optimization, null check -->

Az undefined behaviour olyan művelet, amire a szabvány semmilyen viselkedést nem ír elő: a fordító feltételezheti, hogy SOHA nem történik meg, és erre építve optimalizál. Ezért az UB nem „véletlen érték”, hanem eltűnő ellenőrzések, végtelen ciklusok, -O2-n másként viselkedő program. Klasszikusok: előjeles túlcsordulás, túlindexelés, inicializálatlan olvasás, NULL-deref, a bitszélességnél nagyobb shift, strict aliasing megsértése. Védekezés: ellenőrizz a művelet ELŐTT, fordíts `-Wall -Wextra`-val, tesztelj `-fsanitize=address,undefined`-dal.

```c
#include <limits.h>
#include <stdbool.h>
#include <stdio.h>

// A túlcsordulást a művelet ELŐTT kell ellenőrizni; utána már UB történt.
static bool add_checked(int a, int b, int *out) {
    if ((b > 0 && a > INT_MAX - b) || (b < 0 && a < INT_MIN - b)) return false;
    *out = a + b;
    return true;
}
// GCC/Clang: __builtin_add_overflow(a, b, &res); C23: ckd_add(&res, a, b) <stdckdint.h>

// Shift >= bitszélesség UB -> ellenőrizni kell
static unsigned shift_left(unsigned x, unsigned n) {
    return n < sizeof x * CHAR_BIT ? x << n : 0;
}

// A fordító törölheti a NULL-ellenőrzést: a deref után "p biztosan nem NULL".
static int fragile(const int *p) {
    int first = *p;              // ha p == NULL: UB
    if (p == NULL) return -1;    // -O2-n ez a sor kioptimalizálható!
    return first;
}

// Előjeles túlcsordulás miatt a fordító ezt "mindig igaz"-ra egyszerűsítheti
static bool will_not_overflow(int x) {
    return x + 1 > x;            // UB, ha x == INT_MAX -> gyakran konstans true lesz
}

int main(void) {
    int r = 0;
    printf("add: %d\n", add_checked(INT_MAX, 1, &r));   // 0: elutasítva

    unsigned u = UINT_MAX;
    u += 1;                       // előjel nélküli: modulo 2^N, DEFINIÁLT -> 0
    printf("%u %u\n", u, shift_left(1u, 40));

    int v = 5;
    printf("%d %d\n", fragile(&v), will_not_overflow(10));

    // Gyakori UB-k (ne):
    // int a[4]; a[4] = 1;       túlindexelés
    // int x; printf("%d", x);   inicializálatlan olvasás
    // i = i++ + 1;              kétszeri módosítás szekvenciapont nélkül
    // INT_MIN / -1;  x % 0;     túlcsordulás, nullával osztás
    // Fordítás: gcc -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer
    return 0;
}
```

## Strict aliasing, restrict és type punning
<!-- q: Mi a strict aliasing szabály és mire jó a restrict kulcsszó? -->
<!-- tags: strict aliasing, restrict, type punning, memcpy, vectorization, optimization -->

A strict aliasing szabály szerint egy objektumot csak a saját (kompatibilis) típusán, előjeles/előjel nélküli változatán vagy `char`/`unsigned char` pointeren át szabad elérni; egy `float`-ot `uint32_t *`-on át olvasni UB. A fordító erre építve feltételezi, hogy különböző típusú pointerek nem fedik egymást. A helyes bitszintű reinterpretáció a `memcpy` (a fordító egyetlen mov-ra optimalizálja), C-ben az union is megengedett. A `restrict` ígéret, hogy a pointerek nem fedik át egymást: ez vektorizálást tesz lehetővé, de ha megszeged, UB.

```c
#include <stdint.h>
#include <stdio.h>
#include <string.h>

// HIBÁS (UB): float objektum elérése uint32_t*-on át
// static uint32_t bits_bad(float f) { return *(uint32_t *)&f; }

// HELYES: memcpy -- -O2-n nincs valódi függvényhívás
static uint32_t float_bits(float f) {
    uint32_t u;
    _Static_assert(sizeof u == sizeof f, "meretelteres");
    memcpy(&u, &f, sizeof u);
    return u;
}

// restrict: x és y NEM fedik át -> a fordító szabadon vektorizálhat (SIMD)
static void saxpy(size_t n, float a, const float *restrict x, float *restrict y) {
    for (size_t i = 0; i < n; ++i)
        y[i] = a * x[i] + y[i];
}

// restrict nélkül a fordító pesszimista: ha a == b, a második sor már
// a módosított értéket olvassa, ezért nem vonhatja össze "*a += 2 * *b"-re.
static void add_twice(int *a, const int *b) {
    *a += *b;
    *a += *b;
}

// Bájtsorrend-független olvasás bájtpufferből (hálózati protokollokhoz)
static uint32_t read_be32(const unsigned char *p) {
    return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 | (uint32_t)p[2] << 8 | p[3];
}

int main(void) {
    printf("1.0f bitjei: 0x%08lx\n", (unsigned long)float_bits(1.0f));   // 0x3f800000

    float x[4] = {1, 2, 3, 4}, y[4] = {10, 20, 30, 40};
    saxpy(4, 2.0f, x, y);
    printf("%.1f %.1f\n", y[0], y[3]);    // 12.0 48.0

    int v = 3;
    add_twice(&v, &v);                     // alias! 3 -> 6 -> 12
    printf("%d\n", v);

    const unsigned char pkt[] = {0x00, 0x00, 0x1F, 0x90};
    printf("port: %lu\n", (unsigned long)read_be32(pkt));   // 8080
    return 0;
}
```

## Struktúrák, padding és igazítás
<!-- q: Miért nagyobb a struct mérete, mint a mezők összege, mi a padding? -->
<!-- tags: struct, padding, alignment, offsetof, alignof, flexible array member, designated initializers -->

A fordító minden mezőt a saját igazítási követelményére helyez (pl. `double` 8-cal osztható címre), és a hézagokat padding bájtokkal tölti ki; a struct végére is kerülhet padding, hogy tömbben is igazított maradjon. A mezők csökkenő méret szerinti rendezésével gyakran 25–40% memória spórolható, ami cache-szempontból is számít. A padding tartalma meghatározatlan, ezért structokat `memcmp`-pel összehasonlítani hibás. A flexible array member (C99) egyetlen allokációban tárol változó hosszú rekordot.

```c
#include <stdalign.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct Bad {          // x86-64: 24 bájt
    char   tag;       // 1 + 7 padding
    double value;     // 8
    int    id;        // 4 + 4 tail padding
};

struct Good {         // 16 bájt: csökkenő méret szerinti sorrend
    double value;
    int    id;
    char   tag;       // + 3 tail padding
};

// Flexible array member: a fejléc és az adat egy blokkban
typedef struct {
    size_t len;
    char   data[];    // méret nélküli utolsó tag, a sizeof nem számolja bele
} Blob;

static Blob *blob_new(const char *src) {
    size_t n = strlen(src);
    Blob *b = malloc(sizeof *b + n + 1);
    if (!b) return NULL;
    b->len = n;
    memcpy(b->data, src, n + 1);
    return b;
}

int main(void) {
    printf("Bad=%zu Good=%zu\n", sizeof(struct Bad), sizeof(struct Good));
    printf("offsetof(Bad, value)=%zu, id=%zu\n",
           offsetof(struct Bad, value), offsetof(struct Bad, id));
    printf("alignof(double)=%zu\n", alignof(double));

    // Struct másolás (=) működik; összehasonlítás mezőnként, NEM memcmp-pel
    struct Good a = {1.5, 7, 'x'};
    struct Good b = a;
    int equal = a.value == b.value && a.id == b.id && a.tag == b.tag;

    // Kijelölt inicializálók (C99): a nem említett mezők nullák
    struct Good c = {.id = 3, .tag = 'c'};

    Blob *blob = blob_new("payload");
    if (blob) printf("%d %d %zu %s\n", equal, c.id, blob->len, blob->data);
    free(blob);
    return 0;
}
```

## Union és tagged union
<!-- q: Mire való a union C-ben, és hogyan készítsek típusbiztos tagged uniont? -->
<!-- tags: union, tagged union, variant, anonymous union, enum, type punning -->

A union minden tagja ugyanazon a címen kezdődik, a mérete a legnagyobb tagé: egyszerre csak egy tag „él”. Önmagában nem tudja, melyik tag érvényes, ezért egy enum „tag” mezővel párosítjuk (tagged union / discriminated union) – így épülnek interpreterek értéktípusai, AST-k, üzenetformátumok. A `switch` az enumon `-Wswitch` mellett figyelmeztet a kimaradt esetre. C-ben a union-alapú type punning megengedett, C++-ban viszont UB.

```c
#include <stdio.h>
#include <string.h>

typedef enum { VAL_NUM, VAL_BOOL, VAL_STR } ValKind;

typedef struct {
    ValKind kind;                  // melyik union-tag érvényes
    union {                        // névtelen union (C11): v.num közvetlenül elérhető
        double num;
        int    boolean;
        struct { const char *ptr; size_t len; } str;
    };
} Value;                           // méret: tag + legnagyobb tag (igazítva)

static Value val_num(double d)      { return (Value){.kind = VAL_NUM, .num = d}; }
static Value val_bool(int b)        { return (Value){.kind = VAL_BOOL, .boolean = b}; }
static Value val_str(const char *s) { return (Value){.kind = VAL_STR, .str = {s, strlen(s)}}; }

static void val_print(const Value *v) {
    switch (v->kind) {             // -Wswitch: figyelmeztet, ha egy enum-ág hiányzik
    case VAL_NUM:  printf("%g\n", v->num); break;
    case VAL_BOOL: printf("%s\n", v->boolean ? "true" : "false"); break;
    case VAL_STR:  printf("\"%.*s\"\n", (int)v->str.len, v->str.ptr); break;
    }
}

static int val_truthy(const Value *v) {
    switch (v->kind) {
    case VAL_NUM:  return v->num != 0.0;
    case VAL_BOOL: return v->boolean;
    case VAL_STR:  return v->str.len > 0;
    }
    return 0;
}

// Union-alapú type punning: C-ben megengedett (C++-ban UB!)
typedef union { float f; unsigned int u; } FloatBits;

int main(void) {
    Value vals[] = {val_num(3.14), val_bool(1), val_str("hello"), val_str("")};
    for (size_t i = 0; i < sizeof vals / sizeof vals[0]; ++i) {
        val_print(&vals[i]);
        printf("  truthy=%d\n", val_truthy(&vals[i]));
    }
    FloatBits fb = {.f = -2.0f};
    printf("0x%08x sizeof(Value)=%zu\n", fb.u, sizeof(Value));
    return 0;
}
```

## Bitműveletek, maszkok és bitfield-ek
<!-- q: Hogyan használjak bitműveleteket, flag-maszkokat és bitfield-eket C-ben? -->
<!-- tags: bitwise, bit flags, bitmask, bitfields, popcount, power of two, endianness -->

A bitmaszkos flagek (`1u << n`) hordozhatóak és pontosan kontrolláltak: beállítás `|=`, törlés `&= ~`, váltás `^=`, tesztelés `&`. A bitfield-ek kényelmesek, de a bitek sorrendje, az igazítás és az előjel implementációfüggő, ezért fájlformátumhoz és hálózati protokollhoz maszk + shift a helyes. Bitműveleteket mindig előjel nélküli típuson végezz: előjeles értéken a balra shift túlcsordulása UB. Klasszikus trükkök: `x & (x - 1)` törli a legalsó 1-es bitet, `x & -x` izolálja.

```c
#include <stdint.h>
#include <stdio.h>

enum {
    PERM_READ  = 1u << 0,
    PERM_WRITE = 1u << 1,
    PERM_EXEC  = 1u << 2,
};

#define BIT_SET(x, m)    ((x) |= (m))
#define BIT_CLEAR(x, m)  ((x) &= ~(m))
#define BIT_TOGGLE(x, m) ((x) ^= (m))
#define BIT_TEST(x, m)   (((x) & (m)) != 0)

// Bitfield: kényelmes, de az elrendezés implementációfüggő
struct RgbPixel {
    unsigned r : 5;
    unsigned g : 6;
    unsigned b : 5;   // 16 bit hasznos adat, de a sizeof lehet 4
};

// Hordozható RGB565 csomagolás maszk + shift segítségével
static uint16_t pack565(unsigned r, unsigned g, unsigned b) {
    return (uint16_t)(((r & 0x1Fu) << 11) | ((g & 0x3Fu) << 5) | (b & 0x1Fu));
}

static int popcount32(uint32_t x) {      // Kernighan: minden kör a legalsó 1-est törli
    int n = 0;
    while (x) { x &= x - 1; ++n; }
    return n;
}
static int is_pow2(uint64_t x)          { return x && !(x & (x - 1)); }
static uint32_t lowest_bit(uint32_t x)  { return x & (~x + 1u); }   // x & -x
static uint32_t round_up_pow2(uint32_t x) {                          // x > 0
    --x;
    x |= x >> 1; x |= x >> 2; x |= x >> 4; x |= x >> 8; x |= x >> 16;
    return x + 1;
}

int main(void) {
    unsigned perms = PERM_READ;
    BIT_SET(perms, PERM_WRITE);
    BIT_TOGGLE(perms, PERM_EXEC);
    BIT_CLEAR(perms, PERM_READ);
    printf("r=%d w=%d x=%d\n", BIT_TEST(perms, PERM_READ),
           BIT_TEST(perms, PERM_WRITE), BIT_TEST(perms, PERM_EXEC));

    struct RgbPixel px = {31, 63, 0};
    printf("bitfield sizeof=%zu g=%u packed=0x%04x\n",
           sizeof px, (unsigned)px.g, (unsigned)pack565(31, 63, 0));
    printf("pop=%d pow2=%d low=%u up=%u\n", popcount32(0xF0F0u), is_pow2(1024),
           (unsigned)lowest_bit(40u), (unsigned)round_up_pow2(100u));
    // Beépítettek: __builtin_popcount, __builtin_ctz; C23: <stdbit.h> stdc_count_ones
    return 0;
}
```

## Függvénypointerek és callbackek
<!-- q: Hogyan használjak függvénypointereket és callbacket C-ben? -->
<!-- tags: function pointers, callbacks, qsort, dispatch table, void pointer, user data -->

A függvénypointer egy függvény címét tárolja, így viselkedés adható át paraméterként (stratégia, callback, eseménykezelő); a `typedef` olvashatóvá teszi a szintaxist. Mivel C-ben nincs closure, a callbackek mellé egy `void *user` paramétert szokás adni, amin keresztül állapot érhető el. A `qsort` komparátornál a klasszikus `return a - b` túlcsordulhat, használd a `(a > b) - (a < b)` formát. A diszpécstábla (név → függvény) egyszerű „vtable”, így épül a polimorfizmus C-ben.

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { const char *name; int age; } Person;

static int by_age(const void *a, const void *b) {
    const Person *pa = a, *pb = b;
    return (pa->age > pb->age) - (pa->age < pb->age);   // NE "a - b": túlcsordulhat
}
static int by_name(const void *a, const void *b) {
    return strcmp(((const Person *)a)->name, ((const Person *)b)->name);
}

typedef void (*visit_fn)(const Person *p, void *user);

// Callback + "user data": állapot átadása closure nélkül
static void for_each(const Person *arr, size_t n, visit_fn fn, void *user) {
    for (size_t i = 0; i < n; ++i) fn(&arr[i], user);
}
static void sum_age(const Person *p, void *user) { *(int *)user += p->age; }
static void print_person(const Person *p, void *user) {
    (void)user;
    printf("  %s (%d)\n", p->name, p->age);
}

// Diszpécstábla: parancsnév -> handler
typedef int (*cmd_fn)(int, int);
static int add(int a, int b) { return a + b; }
static int mul(int a, int b) { return a * b; }
static const struct { const char *name; cmd_fn fn; } COMMANDS[] = {
    {"add", add},
    {"mul", mul},
};

static cmd_fn find_cmd(const char *name) {
    for (size_t i = 0; i < sizeof COMMANDS / sizeof COMMANDS[0]; ++i)
        if (strcmp(COMMANDS[i].name, name) == 0) return COMMANDS[i].fn;
    return NULL;
}

int main(void) {
    Person people[] = {{"Bela", 41}, {"Anna", 29}, {"Cecil", 35}};
    size_t n = sizeof people / sizeof people[0];

    qsort(people, n, sizeof people[0], by_age);
    for_each(people, n, print_person, NULL);
    qsort(people, n, sizeof people[0], by_name);
    for_each(people, n, print_person, NULL);

    int total = 0;
    for_each(people, n, sum_age, &total);
    printf("osszeg: %d\n", total);

    cmd_fn f = find_cmd("mul");
    if (f) printf("mul(6, 7) = %d\n", f(6, 7));
    return 0;
}
```

## Preprocesszor és makrók
<!-- q: Hogyan írjak biztonságos makrókat, mi az X-macro és a _Generic? -->
<!-- tags: preprocessor, macros, x-macro, stringify, token pasting, _Generic, conditional compilation -->

A preprocesszor fordítás előtt, szövegszinten dolgozik: nem ismeri a típusokat és a scope-ot, ezért a makrókban minden paramétert és a teljes kifejezést zárójelezni kell. A többutasításos makrót `do { ... } while (0)` védi, hogy if/else-ben is helyes legyen; a mellékhatásos argumentum (`MAX(i++, j)`) többször kiértékelődhet. Hasznos minták: X-macro (egy listából enum + névtábla), `#` stringify, `##` token-összefűzés, `_Generic` típus szerinti kiválasztás (C11). Ahol lehet, makró helyett `static inline` függvényt vagy `enum`-ot használj.

```c
#include <stdio.h>

// 1) Többutasításos makró: do { } while (0)
#define SWAP(T, a, b) do { T tmp_ = (a); (a) = (b); (b) = tmp_; } while (0)

// 2) Minden zárójelezve; mellékhatásos argumentum: MAX(i++, j) kétszer növelhet!
#define MAX(a, b) ((a) > (b) ? (a) : (b))

// 3) Stringify és token-összefűzés
#define STR(x)       #x
#define XSTR(x)      STR(x)          // kétlépcsős: előbb kibontja x-et
#define CONCAT(a, b) a##b

// 4) X-macro: egyetlen lista -> enum + névtábla + értéktábla, nem csúszhatnak szét
#define COLOR_LIST(X)   \
    X(RED,   0xFF0000)  \
    X(GREEN, 0x00FF00)  \
    X(BLUE,  0x0000FF)

#define AS_ENUM(name, rgb) COLOR_##name,
#define AS_NAME(name, rgb) #name,
#define AS_RGB(name, rgb)  rgb,
enum Color { COLOR_LIST(AS_ENUM) COLOR_COUNT };
static const char *const COLOR_NAMES[] = { COLOR_LIST(AS_NAME) };
static const unsigned COLOR_RGB[] = { COLOR_LIST(AS_RGB) };

// 5) _Generic (C11): típus szerinti "overload"
#define type_name(x) _Generic((x), int: "int", double: "double", char *: "char*", default: "egyeb")

// 6) Feltételes fordítás és fordítási idejű hiba
#ifndef NDEBUG
#  define LOG(fmt, ...) fprintf(stderr, "[%s:%d] " fmt "\n", __FILE__, __LINE__, __VA_ARGS__)
#else
#  define LOG(fmt, ...) ((void)0)
#endif

#define VERSION 3
#if VERSION < 2
#  error "Legalabb 2-es verzio kell"
#endif

int main(void) {
    int x = 1, y = 2;
    if (x < y) SWAP(int, x, y); else puts("nincs csere");   // do-while(0) nélkül nem fordulna
    int CONCAT(my, Var) = MAX(x, y);                        // -> int myVar = ...
    printf("%d %d %d\n", x, y, myVar);
    printf("%s vs %s\n", XSTR(VERSION), STR(VERSION));      // "3" vs "VERSION"
    for (int c = 0; c < COLOR_COUNT; ++c)
        printf("%s = #%06X\n", COLOR_NAMES[c], COLOR_RGB[c]);
    printf("%s %s\n", type_name(42), type_name(3.0));
    LOG("x=%d", x);
    return 0;
}
```

## Egyedi allokátor: arena (bump) allocator
<!-- q: Hogyan írjak arena allokátort C-ben, és mikor érdemes? -->
<!-- tags: arena allocator, bump allocator, custom allocator, alignment, memory pool, region -->

Az arena allokátor egy nagy blokkból egyszerűen „továbbtolja” a pointert: a foglalás O(1), nincs objektumonkénti `free`, és a teljes arena egyetlen lépésben szabadul fel – így leak és fragmentáció sem keletkezik. Ideális kérésenkénti (HTTP request), képkockánkénti (játék) vagy fordítási fázisonkénti memóriához. Belül az igazítás a kritikus rész: a címet a típus `alignof` értékére kell felfelé kerekíteni, különben misaligned elérés (UB, egyes architektúrákon crash) lesz. A mark/rewind ideiglenes (scratch) foglalásokra jó, de a visszatekerés utáni pointerek érvénytelenek.

```c
#include <stdalign.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    unsigned char *base;
    size_t cap;
    size_t off;
} Arena;

static int arena_init(Arena *a, size_t cap) {
    a->base = malloc(cap);
    a->cap = cap;
    a->off = 0;
    return a->base ? 0 : -1;
}

// align kettő hatványa; (x + a-1) & ~(a-1) felfelé kerekít
static void *arena_alloc(Arena *a, size_t size, size_t align) {
    uintptr_t cur = (uintptr_t)(a->base + a->off);
    uintptr_t aligned = (cur + (align - 1)) & ~(uintptr_t)(align - 1);
    size_t pad = (size_t)(aligned - cur);
    if (pad > a->cap - a->off || size > a->cap - a->off - pad) return NULL;  // túlcsordulás-biztos
    a->off += pad + size;
    return a->base + (a->off - size);
}

#define ARENA_NEW(a, T, n) ((T *)arena_alloc((a), sizeof(T) * (n), alignof(T)))

typedef struct { size_t off; } ArenaMark;
static ArenaMark arena_mark(const Arena *a)     { return (ArenaMark){a->off}; }
static void arena_rewind(Arena *a, ArenaMark m) { a->off = m.off; }
static void arena_destroy(Arena *a)             { free(a->base); a->base = NULL; }

static char *arena_strdup(Arena *a, const char *s) {
    size_t n = strlen(s) + 1;
    char *p = arena_alloc(a, n, 1);
    if (p) memcpy(p, s, n);
    return p;
}

typedef struct Node { int value; struct Node *next; } Node;

int main(void) {
    Arena arena;
    if (arena_init(&arena, 1 << 16) != 0) return 1;

    Node *head = NULL;
    for (int i = 0; i < 5; ++i) {                 // láncolt lista csomópontonkénti free nélkül
        Node *n = ARENA_NEW(&arena, Node, 1);
        if (!n) break;
        n->value = i;
        n->next = head;
        head = n;
    }
    ArenaMark m = arena_mark(&arena);
    char *tmp = arena_strdup(&arena, "ideiglenes puffer");
    if (tmp) printf("%s, hasznalt: %zu bajt\n", tmp, arena.off);
    arena_rewind(&arena, m);                      // tmp innentől ÉRVÉNYTELEN

    for (Node *n = head; n; n = n->next) printf("%d ", n->value);
    printf("\n");
    arena_destroy(&arena);                        // minden objektum egyszerre szabadul fel
    return 0;
}
```

## Hibakezelés és fájl I/O: errno és goto cleanup
<!-- q: Hogyan kezeljem a hibákat C-ben, mi a goto cleanup minta? -->
<!-- tags: error handling, errno, goto cleanup, fopen, fread, strtol, resource management -->

C-ben nincs kivétel: a hibát visszatérési kód (vagy `NULL`) jelzi, a részleteket gyakran az `errno` hordozza, amit közvetlenül a hiba után kell kiolvasni, mert a következő hívás felülírhatja. Több erőforrás esetén a `goto cleanup` minta adja az egyetlen kilépési pontot, ahol minden pontosan egyszer szabadul fel (a Linux kernel is így dolgozik). Számparse-hoz `strtol` + `errno` + végpointer-ellenőrzés kell, az `atoi` semmilyen hibát nem jelez. Bináris fájlnál a `"rb"` mód kötelező, különben Windows-on a `\r\n` átalakul.

```c
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef enum { OK = 0, ERR_OPEN, ERR_READ, ERR_NOMEM, ERR_FORMAT } Status;

static const char *status_str(Status s) {
    static const char *const names[] = {"ok", "megnyitas", "olvasas", "memoria", "formatum"};
    return names[s];
}

// Egész fájl beolvasása; egyetlen kilépési pont a cleanup címkénél.
static Status read_file(const char *path, char **out, size_t *out_len) {
    Status st = OK;
    char *buf = NULL;
    FILE *f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "%s: %s\n", path, strerror(errno));   // errno-t AZONNAL olvasd
        return ERR_OPEN;
    }
    if (fseek(f, 0, SEEK_END) != 0) { st = ERR_READ; goto cleanup; }
    long size = ftell(f);                  // long: 32 bites Windows-on 2 GB korlát
    if (size < 0) { st = ERR_READ; goto cleanup; }
    rewind(f);

    buf = malloc((size_t)size + 1);
    if (!buf) { st = ERR_NOMEM; goto cleanup; }

    size_t got = fread(buf, 1, (size_t)size, f);
    if (got != (size_t)size || ferror(f)) { st = ERR_READ; goto cleanup; }
    buf[got] = '\0';

    *out = buf;                            // tulajdonjog átadása a hívónak
    *out_len = got;
    buf = NULL;                            // hogy a cleanup ne szabadítsa fel

cleanup:
    free(buf);
    fclose(f);
    return st;
}

// Szigorú számparse: strtol + errno + végpointer
static Status parse_long(const char *s, long *out) {
    char *end;
    errno = 0;
    long v = strtol(s, &end, 10);
    if (errno == ERANGE || end == s || *end != '\0') return ERR_FORMAT;
    *out = v;
    return OK;
}

int main(int argc, char **argv) {
    long n = 0;
    if (parse_long("12345", &n) == OK) printf("szam: %ld\n", n);
    if (parse_long("12abc", &n) != OK) printf("hibas szam\n");

    if (argc < 2) { fprintf(stderr, "hasznalat: %s FAJL\n", argv[0]); return 2; }
    char *data = NULL;
    size_t len = 0;
    Status st = read_file(argv[1], &data, &len);
    if (st != OK) { fprintf(stderr, "hiba: %s\n", status_str(st)); return 1; }
    printf("%zu bajt beolvasva\n", len);
    free(data);
    return 0;
}
```

## Intruzív láncolt lista és container_of
<!-- q: Mi az intruzív lista és hogyan működik a container_of makró? -->
<!-- tags: intrusive list, container_of, offsetof, linked list, linux kernel, data structures -->

Az intruzív adatszerkezetben a láncszem (`ListNode`) az objektumba van ágyazva, nem az objektum a csomópontba: nincs külön allokáció csomópontonként, a törlés O(1), és egy objektum több listában is szerepelhet egyszerre. A `container_of` a láncszem címéből az `offsetof` levonásával visszaszámolja a tartalmazó struct címét – így működik a Linux kernel `list_head`-je. A körkörös, sentinel fejjel rendelkező lista kiküszöböli a NULL-speciális eseteket. Buktató: az objektum nem szabadulhat fel, amíg bármely listában benne van.

```c
#include <stddef.h>
#include <stdio.h>

typedef struct ListNode { struct ListNode *prev, *next; } ListNode;

#define container_of(ptr, type, member) \
    ((type *)((char *)(ptr) - offsetof(type, member)))

static void list_init(ListNode *head) { head->prev = head->next = head; }  // üres: önmagára mutat
static void list_insert_after(ListNode *pos, ListNode *n) {
    n->next = pos->next;
    n->prev = pos;
    pos->next->prev = n;
    pos->next = n;
}
static void list_push_back(ListNode *head, ListNode *n) { list_insert_after(head->prev, n); }
static void list_remove(ListNode *n) {
    n->prev->next = n->next;
    n->next->prev = n->prev;
    n->prev = n->next = n;          // önmagára mutat: az ismételt remove ártalmatlan
}

#define list_for_each(it, head) \
    for (ListNode *it = (head)->next; it != (head); it = it->next)

typedef struct {
    int id;
    int priority;
    ListNode all_link;              // tagja a "minden task" listának
    ListNode run_link;              // és a "futásra kész" listának is
} Task;

int main(void) {
    ListNode all, ready;
    list_init(&all);
    list_init(&ready);

    Task tasks[4];
    for (int i = 0; i < 4; ++i) {
        tasks[i] = (Task){.id = i, .priority = i * 10};
        list_push_back(&all, &tasks[i].all_link);
        if (i % 2 == 0) list_push_back(&ready, &tasks[i].run_link);
    }
    list_remove(&tasks[2].run_link);           // O(1), keresés nélkül

    list_for_each(it, &all) {
        Task *t = container_of(it, Task, all_link);   // láncszemből vissza az objektumra
        printf("task %d (prio %d)\n", t->id, t->priority);
    }
    list_for_each(it, &ready)
        printf("ready: %d\n", container_of(it, Task, run_link)->id);
    return 0;
}
```

## Többszálúság és atomikus műveletek (C11)
<!-- q: Hogyan írjak többszálú programot C-ben szálakkal, mutexszel és atomikus változókkal? -->
<!-- tags: threads, pthreads, c11 threads, mutex, stdatomic, memory_order, data race -->

A C11 `<threads.h>` és `<stdatomic.h>` szabványos szálkezelést ad (POSIX rendszereken a `pthread_create`/`pthread_mutex_lock` a gyakoribb, a logika azonos). Két szál egyidejű, legalább egy írással járó, szinkronizálatlan hozzáférése ugyanahhoz a nem-atomikus változóhoz data race, ami UB. Számlálóhoz elég a `memory_order_relaxed`, adat publikálásához viszont release-store + acquire-load pár kell, ami garantálja, hogy a flag előtti írások láthatók. A szálanként lokális gyűjtés és a ritka zárolás sokkal gyorsabb, mint minden lépésnél lockolni.

```c
#include <stdatomic.h>
#include <stdbool.h>
#include <stdio.h>
#include <threads.h>

#define THREADS 4
#define ITERS   100000

static atomic_long hits;          // atomikus számláló: nincs data race
static long total_sum = 0;        // nem atomikus -> csak mutex alatt írható
static mtx_t lock;

typedef struct { int id; long local_sum; } WorkerArg;

static int worker(void *p) {
    WorkerArg *arg = p;
    for (int i = 0; i < ITERS; ++i) {
        atomic_fetch_add_explicit(&hits, 1, memory_order_relaxed);  // csak számolás: relaxed
        arg->local_sum += i % 7;                // szálanként saját adat
    }
    mtx_lock(&lock);
    total_sum += arg->local_sum;                // kritikus szakasz
    mtx_unlock(&lock);
    return 0;
}

// Release/acquire publikálás
static int payload;
static atomic_bool ready;

static int producer(void *p) {
    (void)p;
    payload = 42;                                               // (1) sima írás
    atomic_store_explicit(&ready, true, memory_order_release);  // (2) "kiadja" az (1)-et
    return 0;
}

int main(void) {
    if (mtx_init(&lock, mtx_plain) != thrd_success) return 1;

    thrd_t th[THREADS];
    WorkerArg args[THREADS];
    for (int i = 0; i < THREADS; ++i) {
        args[i] = (WorkerArg){.id = i};
        if (thrd_create(&th[i], worker, &args[i]) != thrd_success) return 1;
    }
    for (int i = 0; i < THREADS; ++i) thrd_join(th[i], NULL);
    printf("hits=%ld sum=%ld\n", atomic_load(&hits), total_sum);

    thrd_t prod;
    thrd_create(&prod, producer, NULL);
    while (!atomic_load_explicit(&ready, memory_order_acquire))  // (3) szinkronizál (2)-vel
        thrd_yield();                           // élesben: condition variable (cnd_wait)
    printf("payload=%d\n", payload);            // garantáltan 42
    thrd_join(prod, NULL);
    mtx_destroy(&lock);
    return 0;
}
```

## Build rendszerek: Make és CMake
<!-- q: Hogyan buildeljek egy C projektet Makefile-lal vagy CMake-kel? -->
<!-- tags: make, makefile, cmake, build system, dependencies, compiler flags, sanitizers -->

A Make célokat (target), függőségeket és recepteket ír le, és csak azt fordítja újra, aminek a forrása vagy headere változott; a `-MMD -MP` kapcsolók automatikusan generálják a header-függőségeket. A receptsorok TAB karakterrel kezdődnek, szóközzel a Make hibát ad. A CMake egy generátor (Makefile, Ninja, Visual Studio projekt), target-alapú: a `PUBLIC`/`PRIVATE` include-ok és flagek a függőségi gráfban terjednek. Nagyobb, többplatformos projekthez CMake (vagy Meson), kicsihez a Make is elég.

```makefile
# Makefile: inkrementális build automatikus header-függőségekkel
CC       ?= cc
CFLAGS   ?= -std=c17 -Wall -Wextra -Wpedantic -O2 -g
CPPFLAGS += -Iinclude -MMD -MP
LDLIBS   += -lm

SRC := $(wildcard src/*.c)
OBJ := $(SRC:src/%.c=build/%.o)
DEP := $(OBJ:.o=.d)
BIN := build/app

.PHONY: all clean asan
all: $(BIN)

# $^ = összes előfeltétel, $@ = a cél, $< = az első előfeltétel
$(BIN): $(OBJ)
	$(CC) $(LDFLAGS) $^ $(LDLIBS) -o $@

# "| build": order-only előfeltétel (a mappa léte kell, az időbélyege nem)
build/%.o: src/%.c | build
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

build:
	mkdir -p $@

asan: CFLAGS := -std=c17 -Wall -Wextra -O1 -g -fsanitize=address,undefined
asan: LDFLAGS += -fsanitize=address,undefined
asan: all

clean:
	rm -rf build

-include $(DEP)
```

```cmake
cmake_minimum_required(VERSION 3.20)
project(textstats VERSION 1.2 LANGUAGES C)

set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)   # compile_commands.json clangd-nek / IDE-nek

# Könyvtár target: a PUBLIC include út a felhasználóira is átöröklődik
add_library(stats STATIC src/stats.c src/parse.c)
target_include_directories(stats PUBLIC include)
target_compile_options(stats PRIVATE
    $<$<C_COMPILER_ID:GNU,Clang>:-Wall -Wextra -Wpedantic>
    $<$<C_COMPILER_ID:MSVC>:/W4>)

add_executable(app src/main.c)
target_link_libraries(app PRIVATE stats)
if(UNIX)
    target_link_libraries(app PRIVATE m)   # libm csak Unix-on külön könyvtár
endif()

enable_testing()
add_executable(stats_test tests/stats_test.c)
target_link_libraries(stats_test PRIVATE stats)
add_test(NAME stats COMMAND stats_test)
# cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j && ctest --test-dir build
```

## Linkelés: statikus és dinamikus könyvtárak
<!-- q: Mi a különbség a statikus és a dinamikus könyvtár között, hogyan működik a linkelés C-ben? -->
<!-- tags: linking, static library, shared library, dll, extern, static, visibility, fpic, abi -->

A fordítás fordítási egységenként (.c → .o) történik, a linker köti össze a szimbólumokat: az `extern` deklaráció ígéret, hogy a definíció máshol van, a `static` pedig belső linkage-et ad (a szimbólum nem látszik a fájlon kívül). Statikus könyvtár (`.a`/`.lib`) esetén a kód bemásolódik a binárisba; dinamikus (`.so`/`.dll`/`.dylib`) esetén futáskor töltődik be, több program osztozik rajta, és frissíthető újrafordítás nélkül – cserébe ABI-stabilitásra kell figyelni. Linux-on a shared library-hez `-fPIC` kell, és a `-fvisibility=hidden` + explicit export kisebb, gyorsabb könyvtárat ad; a `-l` kapcsolók sorrendje számít.

```c
/* ---- mathx.h: publikus interfész ---- */
#ifndef MATHX_H
#define MATHX_H
#include <stddef.h>

#if defined(_WIN32) && defined(MATHX_BUILD_DLL)
#  define MATHX_API __declspec(dllexport)
#elif defined(_WIN32) && defined(MATHX_USE_DLL)
#  define MATHX_API __declspec(dllimport)
#elif defined(__GNUC__)
#  define MATHX_API __attribute__((visibility("default")))
#else
#  define MATHX_API
#endif

#ifdef __cplusplus
extern "C" {                    /* C++-ból is hívható, név-mangling nélkül */
#endif

MATHX_API extern int mathx_calls;                 /* deklaráció: a definíció a .c-ben */
MATHX_API double mathx_mean(const double *xs, size_t n);

#ifdef __cplusplus
}
#endif
#endif /* MATHX_H */

/* ---- mathx.c: implementáció ---- */
/* #include "mathx.h" */
int mathx_calls = 0;                              /* definíció, külső linkage */

static double sum(const double *xs, size_t n) {   /* static: belső linkage, nem exportált */
    double s = 0.0;
    for (size_t i = 0; i < n; ++i) s += xs[i];
    return s;
}

MATHX_API double mathx_mean(const double *xs, size_t n) {
    ++mathx_calls;
    return n ? sum(xs, n) / (double)n : 0.0;
}
```

```bash
# Statikus könyvtár: .o fájlok archívuma, linkeléskor bemásolódik
gcc -c -O2 mathx.c -o mathx.o
ar rcs libmathx.a mathx.o
gcc main.c -L. -lmathx -o app_static     # a -l a forrás UTÁN álljon (sorrend számít)

# Dinamikus könyvtár: pozíciófüggetlen kód, soname a verziózáshoz
gcc -c -O2 -fPIC -fvisibility=hidden mathx.c -o mathx.pic.o
gcc -shared -Wl,-soname,libmathx.so.1 mathx.pic.o -o libmathx.so.1.0
ln -sf libmathx.so.1.0 libmathx.so.1 && ln -sf libmathx.so.1 libmathx.so
gcc main.c -L. -lmathx -Wl,-rpath,'$ORIGIN' -o app_dyn
ldd app_dyn                # betöltendő könyvtárak
nm -D --defined-only libmathx.so   # exportált szimbólumok (sum nem látszik)
# Futásidejű betöltés: dlopen("libmathx.so", RTLD_NOW) + dlsym(h, "mathx_mean")
```
