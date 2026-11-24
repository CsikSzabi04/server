# C++
<!-- tech: cpp -->
<!-- aliases: c++, cxx, c++17, c++20, c++23 -->

A C++ a C-re épülő, többparadigmás (procedurális, objektumorientált, generikus, funkcionális) natív nyelv, amelynek vezérelve a „zero-cost abstraction”: amit nem használsz, az nem kerül semmibe, amit igen, azt kézzel sem tudnád jobban megírni. Szemétgyűjtő nincs; az erőforrásokat determinisztikusan, RAII-val (konstruktor szerez, destruktor felszabadít) kezeli. A modern szabványok (C++11: move, lambda, szálak; C++17: optional, variant, if constexpr; C++20: concepts, ranges, coroutines; C++23: expected, print) jelentősen biztonságosabbá tették. Játékmotorok, böngészők, adatbázisok, HFT-rendszerek, ML-futtatókörnyezetek nyelve; hátránya a nagy komplexitás, az undefined behaviour és a lassú fordítás.

## RAII: erőforráskezelés konstruktorral és destruktorral
<!-- q: Mi az a RAII C++-ban és hogyan kezeljem vele az erőforrásokat? -->
<!-- tags: raii, destructor, scope guard, lock_guard, exception safety, resource management -->

A RAII (Resource Acquisition Is Initialization) lényege, hogy minden erőforrást (memória, fájl, zár, socket) egy objektum birtokol: a konstruktor szerzi meg, a destruktor engedi el. Mivel a destruktor scope végén – return és kivétel (stack unwinding) esetén is – garantáltan lefut, nincs elfelejtett `close`/`unlock`, és a kód kivételbiztos lesz. Az erőforrás-birtokló osztály általában nem másolható, csak mozgatható. A destruktor ne dobjon kivételt: unwinding közben dobott második kivétel `std::terminate`-et okoz.

```cpp
#include <cstdio>
#include <mutex>
#include <stdexcept>
#include <string>
#include <utility>

// RAII-burok egy C FILE* köré
class File {
public:
    File(const std::string& path, const char* mode) : f_(std::fopen(path.c_str(), mode)) {
        if (!f_) throw std::runtime_error("nem nyithato: " + path);
    }
    ~File() { if (f_) std::fclose(f_); }            // kivétel esetén is lefut

    File(const File&) = delete;                     // egyedi tulajdon: nem másolható
    File& operator=(const File&) = delete;
    File(File&& o) noexcept : f_(std::exchange(o.f_, nullptr)) {}   // de mozgatható
    File& operator=(File&& o) noexcept {
        if (this != &o) {
            if (f_) std::fclose(f_);
            f_ = std::exchange(o.f_, nullptr);
        }
        return *this;
    }

    void write(const std::string& s) {
        if (std::fputs(s.c_str(), f_) < 0) throw std::runtime_error("irasi hiba");
    }
private:
    std::FILE* f_;
};

// Általános scope guard: tetszőleges takarítás a blokk végén
template <class F>
class ScopeExit {
public:
    explicit ScopeExit(F f) : f_(std::move(f)) {}
    ~ScopeExit() { if (active_) f_(); }
    void dismiss() noexcept { active_ = false; }    // pl. sikeres commit után
    ScopeExit(const ScopeExit&) = delete;
    ScopeExit& operator=(const ScopeExit&) = delete;
private:
    F f_;
    bool active_ = true;
};

std::mutex log_mutex;

void append_log(const std::string& line) {
    std::lock_guard<std::mutex> lock(log_mutex);    // RAII zár
    File f("app.log", "a");
    ScopeExit done([] { std::puts("log irasa befejezve"); });   // CTAD (C++17)
    f.write(line + "\n");
}   // destrukció fordított sorrendben: done, f (fclose), lock (unlock)

int main() {
    try {
        append_log("szerver indult");
    } catch (const std::exception& e) {
        std::fprintf(stderr, "hiba: %s\n", e.what());
        return 1;
    }
}
```

## Move szemantika és rvalue referenciák
<!-- q: Mi a move szemantika C++-ban, mire jó a std::move és a perfect forwarding? -->
<!-- tags: move semantics, rvalue reference, std::move, std::forward, noexcept, copy elision -->

A move szemantika lehetővé teszi, hogy egy ideiglenes vagy már nem használt objektum belső erőforrásait (pl. heap-puffer pointerét) O(1) időben „elloptuk” mélymásolás helyett. Az rvalue referencia (`T&&`) köti az ideiglenes értékeket; a `std::move` maga semmit nem mozgat, csak rvalue-vá castol. A move ctor legyen `noexcept`, különben a `std::vector` átméretezéskor a strong exception guarantee miatt másolni fog. A kimozgatott objektum „valid but unspecified” állapotú: csak értékadás és destrukció biztonságos rajta. A `std::forward` sablonokban megőrzi az argumentum érték-kategóriáját.

```cpp
#include <cstring>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

class Buffer {
public:
    explicit Buffer(std::size_t n) : size_(n), data_(new char[n]{}) {}
    ~Buffer() { delete[] data_; }

    Buffer(const Buffer& o) : size_(o.size_), data_(new char[o.size_]) {   // O(n) mélymásolat
        std::memcpy(data_, o.data_, size_);
        std::cout << "copy\n";
    }
    Buffer(Buffer&& o) noexcept                                            // O(1) "lopás"
        : size_(std::exchange(o.size_, 0)), data_(std::exchange(o.data_, nullptr)) {
        std::cout << "move\n";
    }
    // copy-and-swap: egyetlen operator= kezeli a copy és a move értékadást
    Buffer& operator=(Buffer o) noexcept { swap(o); return *this; }
    void swap(Buffer& o) noexcept {
        std::swap(size_, o.size_);
        std::swap(data_, o.data_);
    }
    std::size_t size() const { return size_; }
private:
    std::size_t size_;
    char* data_;
};

Buffer make_buffer() {
    Buffer b(1024);
    return b;                     // NRVO vagy implicit move: soha nem másol
}

// Perfect forwarding: lvalue-t lvalue-ként, rvalue-t rvalue-ként ad tovább
template <class T, class... Args>
T construct(Args&&... args) { return T(std::forward<Args>(args)...); }

int main() {
    Buffer a(16);
    Buffer b = a;                 // copy: a lvalue
    Buffer c = std::move(a);      // move: a innentől "valid but unspecified"

    std::vector<Buffer> v;
    v.reserve(2);
    v.push_back(make_buffer());   // ideiglenes -> move
    v.emplace_back(64);           // helyben konstruál: se copy, se move

    std::string s = "hosszu szoveg, ami mar nem fer bele az SSO pufferbe";
    std::string t = construct<std::string>(std::move(s));
    std::cout << b.size() << ' ' << c.size() << ' ' << t.size() << '\n';
}
```

## Rule of 0, 3 és 5
<!-- q: Mi a rule of zero, rule of three és rule of five C++-ban? -->
<!-- tags: rule of zero, rule of three, rule of five, special member functions, copy constructor, destructor -->

A speciális tagfüggvények (destruktor, copy ctor, copy assign, move ctor, move assign) összetartoznak: ha egyet kézzel írsz, mert az osztály nyers erőforrást kezel, valószínűleg mind az ötöt meg kell írnod (rule of 5; C++11 előtt rule of 3). A rule of 0 a preferált: ha minden tag maga kezeli az erőforrását (`std::string`, `std::vector`, `std::unique_ptr`), ne írj egyiket sem, a fordító generáltjai helyesek. A klasszikus hiba: csak destruktort írsz, a generált copy ctor sekély másolatot készít, és két objektum ugyanazt a pointert szabadítja fel (double free). Polimorf bázisosztálynál virtuális destruktor kell, és a másolás tiltása megelőzi a slicingot.

```cpp
#include <algorithm>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

// Rule of 0: a tagok kezelik az erőforrásokat -> nincs kézi speciális tag
struct Customer {
    std::string name;
    std::vector<int> orders;
    std::unique_ptr<int> cache;          // emiatt automatikusan move-only lesz
};

// Rule of 5: nyers erőforrás -> mind az 5 speciális tag kell
class IntArray {
public:
    explicit IntArray(std::size_t n) : n_(n), p_(new int[n]{}) {}
    ~IntArray() { delete[] p_; }                                   // 1
    IntArray(const IntArray& o) : n_(o.n_), p_(new int[o.n_]) {    // 2
        std::copy(o.p_, o.p_ + n_, p_);
    }
    IntArray& operator=(const IntArray& o) {                       // 3
        if (this != &o) {
            int* fresh = new int[o.n_];   // előbb foglalj: ha dob, *this érintetlen marad
            std::copy(o.p_, o.p_ + o.n_, fresh);
            delete[] p_;
            p_ = fresh;
            n_ = o.n_;
        }
        return *this;
    }
    IntArray(IntArray&& o) noexcept : n_(o.n_), p_(o.p_) {         // 4
        o.n_ = 0;
        o.p_ = nullptr;
    }
    IntArray& operator=(IntArray&& o) noexcept {                   // 5
        if (this != &o) {
            delete[] p_;
            n_ = o.n_; p_ = o.p_;
            o.n_ = 0;  o.p_ = nullptr;
        }
        return *this;
    }
    int& operator[](std::size_t i) { return p_[i]; }
    std::size_t size() const { return n_; }
private:
    std::size_t n_;
    int* p_;
};

// Polimorf bázis: virtuális destruktor + a másolás tiltása (slicing ellen)
struct Shape {
    Shape() = default;
    virtual ~Shape() = default;
    Shape(const Shape&) = delete;
    Shape& operator=(const Shape&) = delete;
    virtual double area() const = 0;
};

int main() {
    IntArray a(3);
    a[0] = 7;
    IntArray b = a;               // mélymásolat
    IntArray c = std::move(a);    // pointer-átvétel
    Customer x{"Anna", {1, 2}, std::make_unique<int>(5)};
    Customer y = std::move(x);    // generált move; a copy le sem fordulna
    std::cout << b[0] << ' ' << c.size() << ' ' << y.name << '\n';
}
```

## Smart pointerek: unique_ptr, shared_ptr, weak_ptr
<!-- q: Mikor használjak unique_ptr-t, shared_ptr-t és weak_ptr-t? -->
<!-- tags: smart pointers, unique_ptr, shared_ptr, weak_ptr, make_shared, custom deleter, ownership -->

A smart pointerek a tulajdonjogot fejezik ki a típusban: a `unique_ptr` egyedi tulajdon nulla többletköltséggel (move-only), a `shared_ptr` referenciaszámlált megosztott tulajdon (atomikus számláló, control block), a `weak_ptr` pedig nem tulajdonló megfigyelő, ami a ciklikus `shared_ptr`-hivatkozásokat töri meg. A `make_shared` egyetlen allokációban hozza létre az objektumot és a control blockot. Gyárfüggvény adjon `unique_ptr`-t, mert az olcsón `shared_ptr`-ré konvertálható; nem tulajdonló paraméterként pedig sima `T&`/`T*` a helyes, nem a smart pointer. Két `shared_ptr` egymásra mutatva soha nem szabadul fel (leak).

```cpp
#include <cstdio>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

struct Node : std::enable_shared_from_this<Node> {
    std::string name;
    std::vector<std::shared_ptr<Node>> children;   // tulajdonló élek lefelé
    std::weak_ptr<Node> parent;                    // nem tulajdonló él felfelé: nincs ciklus
    explicit Node(std::string n) : name(std::move(n)) {}
    ~Node() { std::cout << "~" << name << '\n'; }

    void add(std::shared_ptr<Node> child) {
        child->parent = weak_from_this();
        children.push_back(std::move(child));
    }
};

// unique_ptr egyedi deleterrel C erőforráshoz
struct FileCloser {
    void operator()(std::FILE* f) const noexcept { if (f) std::fclose(f); }
};
using FilePtr = std::unique_ptr<std::FILE, FileCloser>;

std::unique_ptr<Node> make_leaf(const std::string& n) { return std::make_unique<Node>(n); }

// Nem tulajdonló paraméter: sima referencia
void print_name(const Node& n) { std::cout << n.name << '\n'; }

int main() {
    auto root = std::make_shared<Node>("root");    // 1 allokáció: objektum + control block
    root->add(std::make_shared<Node>("a"));
    std::shared_ptr<Node> b = make_leaf("b");      // unique -> shared konverzió
    root->add(b);

    std::cout << "b use_count=" << b.use_count() << '\n';   // 2
    if (auto p = b->parent.lock())                          // weak -> shared, ha még él
        std::cout << "b szuloje: " << p->name << '\n';
    print_name(*b);

    FilePtr f(std::fopen("out.txt", "w"));
    if (f) std::fputs("adat\n", f.get());

    b.reset();
    std::cout << "root torlese...\n";
    root.reset();   // a teljes fa felszabadul (a weak parent miatt nincs leak)
}
```

## Sablonok (templates) és specializáció
<!-- q: Hogyan írjak függvény- és osztálysablonokat, mi a template specializáció? -->
<!-- tags: templates, generic programming, specialization, partial specialization, if constexpr, non-type template parameter -->

A sablon fordítási idejű kódgenerátor: minden használt típusra (vagy értékre) a fordító külön példányt készít (monomorfizáció), így nincs futásidejű overhead, cserébe nagyobb lehet a bináris és lassabb a fordítás. A nem-típus paraméter (`std::size_t N`) fordítási időben ismert méretet ad. A teljes és részleges specializáció egy adott típusra (vagy típuscsaládra, pl. minden pointerre) eltérő implementációt enged; az `if constexpr` (C++17) a nem választott ágat nem is példányosítja. A sablon definíciójának a headerben kell lennie, mert a példányosításhoz a fordítónak látnia kell.

```cpp
#include <array>
#include <cstddef>
#include <iostream>
#include <string>
#include <type_traits>

// Osztálysablon nem-típus paraméterrel: a kapacitás fordítási időben ismert
template <typename T, std::size_t N>
class RingBuffer {
public:
    bool push(const T& v) {
        if (count_ == N) return false;
        data_[(head_ + count_++) % N] = v;
        return true;
    }
    bool pop(T& out) {
        if (count_ == 0) return false;
        out = data_[head_];
        head_ = (head_ + 1) % N;
        --count_;
        return true;
    }
private:
    std::array<T, N> data_{};
    std::size_t head_ = 0, count_ = 0;
};

// Függvénysablon típuslevezetéssel
template <typename T>
T clamp_to(T v, T lo, T hi) { return v < lo ? lo : (hi < v ? hi : v); }

// Elsődleges sablon + teljes és részleges specializáció
template <typename T> struct TypeName { static constexpr const char* value = "ismeretlen"; };
template <> struct TypeName<int>         { static constexpr const char* value = "int"; };
template <> struct TypeName<std::string> { static constexpr const char* value = "string"; };
template <typename T> struct TypeName<T*> { static constexpr const char* value = "pointer"; };

// if constexpr: fordítási idejű elágazás
template <typename T>
std::string describe(const T& v) {
    if constexpr (std::is_arithmetic_v<T>) return "szam: " + std::to_string(v);
    else if constexpr (std::is_same_v<T, std::string>) return "szoveg: " + v;
    else return std::string("egyeb: ") + TypeName<T>::value;
}

int main() {
    RingBuffer<int, 4> rb;
    for (int i = 0; i < 6; ++i) rb.push(i);        // csak 4 fér el
    int x;
    while (rb.pop(x)) std::cout << x << ' ';
    std::cout << '\n' << clamp_to(15, 0, 10) << ' ' << clamp_to<double>(-1, 0.5, 2) << '\n';
    int* p = nullptr;
    std::cout << TypeName<int*>::value << ' ' << describe(42) << ' '
              << describe(std::string("hi")) << ' ' << describe(p) << '\n';
}
```

## Concepts (C++20)
<!-- q: Mik azok a concepts C++20-ban és hogyan korlátozzam velük a sablonokat? -->
<!-- tags: concepts, requires, constraints, c++20, templates, std::integral, overload resolution -->

A concept névvel ellátott, fordítási idejű predikátum a sablonparaméterekre: leírja, milyen műveleteket és típusokat vár el a sablon (statikus „duck typing” szerződés). Előnye a SFINAE-trükkökkel szemben az olvasható kód és a rövid, érthető hibaüzenet („constraints not satisfied”). A `requires` kifejezésben kifejezések érvényességét és visszatérési típusát lehet megkövetelni; az overload-feloldás a szűkebb (jobban korlátozott) változatot választja. A concept csak szintaktikai követelményt ellenőriz, a szemantikát (pl. hogy a `<` valóban rendezés) nem.

```cpp
#include <algorithm>
#include <concepts>
#include <functional>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>

template <typename T>
concept Shape = requires(const T& s) {
    { s.area() } -> std::convertible_to<double>;
    { s.name() } -> std::convertible_to<std::string>;
};

template <typename C>
concept SortableContainer = requires(C c) {
    typename C::value_type;
    { c.begin() } -> std::random_access_iterator;
} && std::totally_ordered<typename C::value_type>;

template <typename K>
concept Hashable = requires(K k) {
    { std::hash<K>{}(k) } -> std::convertible_to<std::size_t>;
};

struct Circle {
    double r;
    double area() const { return 3.14159 * r * r; }
    std::string name() const { return "kor"; }
};
struct Square {
    double a;
    double area() const { return a * a; }
    std::string name() const { return "negyzet"; }
};

// Rövidített szintaxis: "const Shape auto&"
void print_area(const Shape auto& s) { std::cout << s.name() << ": " << s.area() << '\n'; }

// Concept-alapú overload
template <std::integral T>
T midpoint(T a, T b) { return a + (b - a) / 2; }       // nincs túlcsordulás
template <std::floating_point T>
T midpoint(T a, T b) { return (a + b) / 2; }

template <SortableContainer C>
typename C::value_type median(C c) {                    // érték szerint: saját másolat
    std::sort(c.begin(), c.end());
    return c[c.size() / 2];
}

int main() {
    print_area(Circle{1.0});
    print_area(Square{2.0});
    // print_area(42);      // hiba: "constraints not satisfied" -- rövid, érthető üzenet
    std::cout << midpoint(1'000'000'000, 2'000'000'000) << ' ' << midpoint(1.0, 2.0) << '\n';
    std::cout << median(std::vector<int>{5, 1, 4, 2, 3}) << '\n';
    // median(std::list<int>{...});   // hiba: a list iterátora nem random access
    static_assert(Hashable<std::string> && !Hashable<std::vector<int>>);
}
```

## Variadikus sablonok és fold expression
<!-- q: Hogyan működnek a variadikus sablonok és a fold expression C++-ban? -->
<!-- tags: variadic templates, parameter pack, fold expressions, index_sequence, perfect forwarding, tuple -->

A variadikus sablon tetszőleges számú típus- vagy értékparamétert fogad egy paramétercsomagban (`Ts...`), így írható típusbiztos `printf`, `make_unique`, `emplace_back` vagy `std::tuple`. C++17 óta a fold expression (`(xs + ...)`) egy operátorral „összehajtja” a csomagot, rekurzió nélkül; korábban rekurzív kibontás kellett bázisesettel. A `std::index_sequence` fordítási idejű indexsorozatot ad tuple-ök bejárásához. Buktató: a vesszős fold sorrendje balról jobbra garantált, de a függvényargumentumok kiértékelési sorrendje nem.

```cpp
#include <iostream>
#include <sstream>
#include <string>
#include <tuple>
#include <utility>

template <typename... Ts>
auto sum(Ts... xs) { return (xs + ... + 0); }       // üres csomagra 0

template <typename... Ts>
bool all_positive(Ts... xs) { return ((xs > 0) && ...); }

// Vesszős fold: minden elemre, balról jobbra
template <typename... Args>
std::string concat(const Args&... args) {
    std::ostringstream os;
    ((os << args << ' '), ...);
    return os.str();
}

// Rekurzív kibontás (C++11 stílus)
inline void log_impl(std::ostream& os) { os << '\n'; }
template <typename T, typename... Rest>
void log_impl(std::ostream& os, const T& first, const Rest&... rest) {
    os << first;
    if constexpr (sizeof...(rest) > 0) os << ", ";
    log_impl(os, rest...);
}
template <typename... Args>
void log(const Args&... args) { log_impl(std::clog, args...); }

// Tuple bejárása index_sequence-szel
template <typename Tuple, std::size_t... I>
void print_tuple_impl(const Tuple& t, std::index_sequence<I...>) {
    ((std::cout << (I == 0 ? "" : " | ") << std::get<I>(t)), ...);
    std::cout << '\n';
}
template <typename... Ts>
void print_tuple(const std::tuple<Ts...>& t) {
    print_tuple_impl(t, std::index_sequence_for<Ts...>{});
}

// Variadikus gyár perfect forwardinggal (így működik a make_unique)
template <typename T, typename... Args>
T* create(Args&&... args) { return new T(std::forward<Args>(args)...); }

int main() {
    std::cout << sum(1, 2, 3.5) << ' ' << sum() << '\n';
    std::cout << std::boolalpha << all_positive(3, 5, -1) << '\n';
    std::cout << concat("x =", 42, "y =", 3.14) << '\n';
    log("kapcsolat", 8080, "ok", 1.5);
    print_tuple(std::make_tuple(1, "ket", 3.0));
    std::string* s = create<std::string>(5, 'z');
    std::cout << *s << '\n';
    delete s;
}
```

## constexpr, consteval és constinit
<!-- q: Mi a különbség a constexpr, consteval és constinit között C++-ban? -->
<!-- tags: constexpr, consteval, constinit, compile time, static_assert, lookup table, user-defined literal -->

A `constexpr` függvény fordítási és futási időben is hívható; ha konstans kontextusban (pl. `static_assert`, tömbméret) használod, a fordító értékeli ki, így táblák, hash-ek, parserek „beégethetők” a binárisba. A `consteval` (C++20) kötelezően fordítási idejű – például string-hash case-címkékhez. A `constinit` garantálja a statikus inicializálást, ezzel kiküszöböli a „static initialization order fiasco”-t. Fontos különbség: a constexpr kiértékelés közben az UB (túlindexelés, túlcsordulás) fordítási HIBA, futásidőben viszont csendes UB marad.

```cpp
#include <array>
#include <cstdint>
#include <iostream>
#include <string_view>

constexpr std::uint64_t fib(unsigned n) {
    std::uint64_t a = 0, b = 1;
    for (unsigned i = 0; i < n; ++i) { auto t = a + b; a = b; b = t; }
    return a;
}

// Fordítási idejű CRC32 tábla: a binárisba égetve, futásidőben nincs inicializálás
constexpr std::array<std::uint32_t, 256> make_crc_table() {
    std::array<std::uint32_t, 256> t{};
    for (std::uint32_t i = 0; i < 256; ++i) {
        std::uint32_t c = i;
        for (int k = 0; k < 8; ++k) c = (c & 1) ? 0xEDB88320u ^ (c >> 1) : c >> 1;
        t[i] = c;
    }
    return t;
}
constexpr auto CRC_TABLE = make_crc_table();

constexpr std::uint32_t crc32(std::string_view s) {
    std::uint32_t c = 0xFFFFFFFFu;
    for (unsigned char ch : s) c = CRC_TABLE[(c ^ ch) & 0xFF] ^ (c >> 8);
    return c ^ 0xFFFFFFFFu;
}

// consteval: kötelezően fordítási idejű user-defined literal
consteval std::uint32_t operator""_crc(const char* s, std::size_t n) { return crc32({s, n}); }

// constinit: statikus inicializálás garantált
constinit std::uint64_t FIB_50 = fib(50);

void handle(std::string_view cmd) {
    switch (crc32(cmd)) {             // futásidejű hash, fordítási idejű case-címkék
    case "start"_crc: std::cout << "inditas\n"; break;
    case "stop"_crc:  std::cout << "leallitas\n"; break;
    default:          std::cout << "ismeretlen: " << cmd << '\n';
    }
}

int main() {
    static_assert(fib(10) == 55);
    static_assert(crc32("123456789") == 0xCBF43926u);   // szabványos CRC32 tesztvektor
    std::cout << FIB_50 << '\n';
    handle("start");
    handle("reload");
}
```

## STL konténerek és iterátor-invalidáció
<!-- q: Melyik STL konténert válasszam, és mikor válnak érvénytelenné az iterátorok? -->
<!-- tags: stl, containers, vector, unordered_map, map, iterator invalidation, erase_if, try_emplace -->

Alapértelmezésben `std::vector`: folytonos memória, cache-barát, a legtöbb esetben a leggyorsabb, még közbeszúrásnál is kis méretig. `std::unordered_map` átlagosan O(1) keresést ad (hash), a `std::map` rendezett (piros-fekete fa, O(log n)), stabil iterátorokkal és tartomány-lekérdezéssel. A legveszélyesebb hiba az iterátor-invalidáció: a vector `push_back`/`reserve` újraallokálhat, és ekkor minden pointer, referencia és iterátor lóg; bejárás közbeni törlésnél az `erase` visszatérési értékét kell használni. Az `unordered_map::operator[]` beszúr, ha nincs kulcs – kereséshez `find` vagy `contains` kell.

```cpp
#include <algorithm>
#include <iostream>
#include <map>
#include <string>
#include <unordered_map>
#include <vector>

int main() {
    std::vector<int> v{1, 2, 3, 4, 5, 6};

    // INVALIDÁCIÓ: újraallokálás után minden referencia/iterátor lóg
    int& first = v[0];
    v.reserve(100);
    // std::cout << first;   // UB: lógó referencia
    (void)first;

    // Törlés bejárás közben: erase visszaadja a következő érvényes iterátort
    for (auto it = v.begin(); it != v.end();) {
        if (*it % 2 == 0) it = v.erase(it);
        else ++it;
    }
    std::erase_if(v, [](int x) { return x == 5; });   // C++20; régen: erase-remove idiom

    // unordered_map: operator[] BESZÚR, ha nincs kulcs
    std::unordered_map<std::string, int> freq;
    for (std::string w : {"a", "b", "a", "c", "a"}) ++freq[w];
    if (!freq.contains("z")) std::cout << "z nincs (es nem is lett beszurva)\n";
    freq.reserve(1024);   // a rehash az iterátorokat invalidálja, a referenciákat nem

    // map: rendezett, tartomány-lekérdezés lower_bound/upper_bound-dal
    std::map<int, std::string> events{{10, "start"}, {25, "tick"}, {40, "stop"}};
    for (auto it = events.lower_bound(20); it != events.upper_bound(40); ++it)
        std::cout << it->first << ": " << it->second << '\n';

    // try_emplace: nem konstruál feleslegesen, és nem írja felül a meglévőt
    auto [pos, inserted] = events.try_emplace(25, "duplikalt");
    std::cout << "beszurva? " << inserted << " -> " << pos->second << '\n';

    for (const auto& [word, count] : freq) std::cout << word << '=' << count << ' ';
    std::cout << '\n';
    for (int x : v) std::cout << x << ' ';   // 1 3
    std::cout << '\n';
}
```

## STL algoritmusok és iterátorok
<!-- q: Hogyan használjam az STL algoritmusokat (sort, transform, partition) és iterátorokat? -->
<!-- tags: stl algorithms, iterators, sort, stable_sort, transform, accumulate, partition, nth_element, back_inserter -->

Az `<algorithm>` és `<numeric>` függvényei iterátorpárokon ([begin, end)) dolgoznak, így bármely konténerrel működnek; kézi ciklus helyett kifejezik a szándékot, és gyakran gyorsabbak. Válassz a komplexitás szerint: `nth_element` O(n) átlagosan a k-adik elemhez teljes rendezés helyett, `partial_sort` top-k-hoz, rendezett tartományon `lower_bound` O(log n). A `unique` csak a szomszédos duplikátumokat vonja össze, ezért előtte rendezni kell, és az `erase`-zel kell levágni a maradékot. Buktató: a `partition`/`sort` elmozgatja az elemeket, így a korábban szerzett iterátorok már más elemre mutatnak.

```cpp
#include <algorithm>
#include <iostream>
#include <iterator>
#include <numeric>
#include <string>
#include <vector>

struct Order { std::string customer; double amount; int priority; };

int main() {
    std::vector<Order> orders{
        {"anna", 120.0, 2}, {"bela", 35.5, 1}, {"cecil", 410.0, 3},
        {"anna", 80.0, 1},  {"dora", 15.0, 2},
    };

    // Több kulcs szerinti rendezés; stable_sort megőrzi az egyenlők sorrendjét
    std::stable_sort(orders.begin(), orders.end(), [](const Order& a, const Order& b) {
        return a.priority != b.priority ? a.priority > b.priority : a.amount > b.amount;
    });

    double total = std::accumulate(orders.begin(), orders.end(), 0.0,
                                   [](double acc, const Order& o) { return acc + o.amount; });
    auto big = std::count_if(orders.begin(), orders.end(),
                             [](const Order& o) { return o.amount > 100; });

    // Az iterátor értékét a partition ELŐTT olvassuk ki (utána az elemek elmozdulnak)
    auto it = std::find_if(orders.begin(), orders.end(),
                           [](const Order& o) { return o.customer == "dora"; });
    double dora = it != orders.end() ? it->amount : -1.0;

    auto mid = std::partition(orders.begin(), orders.end(),
                              [](const Order& o) { return o.priority >= 2; });

    // transform + back_inserter: kimeneti iterátor, ami push_back-et hív
    std::vector<std::string> names;
    std::transform(orders.begin(), orders.end(), std::back_inserter(names),
                   [](const Order& o) { return o.customer; });
    std::sort(names.begin(), names.end());
    names.erase(std::unique(names.begin(), names.end()), names.end());

    // nth_element: medián O(n) átlagos időben
    std::vector<double> amounts;
    for (const auto& o : orders) amounts.push_back(o.amount);
    auto m = amounts.begin() + static_cast<std::ptrdiff_t>(amounts.size() / 2);
    std::nth_element(amounts.begin(), m, amounts.end());

    std::cout << "osszeg=" << total << " nagy=" << big << " dora=" << dora
              << " surgos=" << std::distance(orders.begin(), mid) << " median=" << *m << '\n';
    std::copy(names.begin(), names.end(), std::ostream_iterator<std::string>(std::cout, " "));
    std::cout << '\n';
}
```

## Lambdák és befogás (capture)
<!-- q: Hogyan működnek a lambdák C++-ban, mi a különbség az érték és a referencia szerinti befogás között? -->
<!-- tags: lambda, closure, capture, std::function, mutable, init capture, generic lambda, dangling reference -->

A lambda egy névtelen függvényobjektum (closure), amelynek befogott változói a closure tagjai lesznek: `[x]` másol, `[&x]` referenciát tárol, `[y = std::move(z)]` (init capture) áthelyez. A legveszélyesebb hiba a lógó referencia: ha a lambda túléli a referenciával befogott lokális változót (visszaadott lambda, eltárolt callback, másik szál), UB. Sablonparaméterként átadott lambda inline-olható, a `std::function` viszont típustörlést végez (lehetséges heap-allokáció, indirekt hívás). A `mutable` a másolatként befogott állapot módosítását engedi.

```cpp
#include <algorithm>
#include <functional>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

// std::function: bármilyen hívható tárolható (típustörlés, van költsége)
class EventBus {
public:
    using Handler = std::function<void(const std::string&)>;
    void on(Handler h) { handlers_.push_back(std::move(h)); }
    void emit(const std::string& msg) const { for (const auto& h : handlers_) h(msg); }
private:
    std::vector<Handler> handlers_;
};

// Sablonparaméterként a lambda inline-olható
template <class Pred>
long count_matching(const std::vector<int>& v, Pred pred) {
    return static_cast<long>(std::count_if(v.begin(), v.end(), pred));
}

std::function<int()> make_counter() {
    int count = 0;
    return [count]() mutable { return ++count; };   // másolat: túléli a függvényt
    // [&count] itt LÓGÓ REFERENCIA lenne!
}

int main() {
    int threshold = 10;
    std::vector<int> data{3, 14, 7, 22, 10, 41};
    auto above = [threshold](int x) { return x > threshold; };
    std::cout << count_matching(data, above) << '\n';      // 3

    // Init capture: move-only objektum átadása a lambdának
    auto owned = std::make_unique<std::string>("konfiguracio");
    auto task = [cfg = std::move(owned)] { return cfg->size(); };
    std::cout << task() << '\n';

    // Generikus lambda és C++20 template lambda
    auto print = [](const auto& x) { std::cout << x << ' '; };
    auto first_of = []<typename T>(const std::vector<T>& v) { return v.front(); };
    print(first_of(data));
    print(3.5);
    std::cout << '\n';

    // Rekurzív lambda std::function-nel (C++23: deducing this)
    std::function<long(int)> fact = [&fact](int n) -> long { return n <= 1 ? 1 : n * fact(n - 1); };
    std::cout << fact(10) << '\n';

    EventBus bus;
    int received = 0;
    bus.on([&received](const std::string&) { ++received; });   // a bus nem élheti túl received-et!
    bus.on([](const std::string& m) { std::cout << "esemeny: " << m << '\n'; });
    bus.emit("login");

    auto counter = make_counter();
    counter();
    counter();
    std::cout << received << ' ' << counter() << '\n';   // 1 3
}
```

## Ranges és views (C++20)
<!-- q: Hogyan használjam a C++20 ranges könyvtárat és a lusta view-kat? -->
<!-- tags: ranges, views, pipeline, filter, transform, projection, lazy evaluation, c++20 -->

A ranges könyvtár két dolgot ad: a `std::ranges::` algoritmusok közvetlenül konténert kapnak (nem begin/end párt) és projekciót is elfogadnak (`&Employee::salary`), a `std::views::` adaptorok pedig lusta, komponálható pipeline-t építenek a `|` operátorral. A view nem birtokolja az adatot és nem készít köztes konténert: az elemek csak iteráláskor, egyenként számolódnak. Buktatók: ideiglenes konténerre épített view lógó lesz; a `filter` view az első `begin()` eredményét cache-eli, ezért const view-ként nem mindig iterálható, és iterálás közben az alap konténert módosítani tilos.

```cpp
#include <algorithm>
#include <iostream>
#include <map>
#include <ranges>
#include <string>
#include <string_view>
#include <vector>

struct Employee { std::string name; std::string dept; int salary; bool active; };

int main() {
    std::vector<Employee> staff{
        {"Anna", "dev", 900, true},   {"Bela", "ops", 700, false},
        {"Cecil", "dev", 1100, true}, {"Dora", "hr", 650, true},
        {"Ede", "dev", 800, true},
    };

    // Lusta pipeline: semmi sem fut, amíg nem iterálunk
    auto dev_names = staff
        | std::views::filter([](const Employee& e) { return e.active && e.dept == "dev"; })
        | std::views::transform(&Employee::name)          // projekció tagpointerrel
        | std::views::take(2);
    for (const auto& n : dev_names) std::cout << n << ' ';
    std::cout << '\n';

    // Range-algoritmus projekcióval
    std::ranges::sort(staff, std::ranges::greater{}, &Employee::salary);
    auto top = std::ranges::max_element(staff, {}, &Employee::salary);
    std::cout << "legtobb: " << top->name << '\n';

    // Végtelen nézet, amit a take_while zár le
    auto squares = std::views::iota(1)
                 | std::views::transform([](int i) { return i * i; })
                 | std::views::take_while([](int x) { return x < 100; });
    for (int s : squares) std::cout << s << ' ';
    std::cout << '\n';

    // split: allokáció nélküli darabolás
    std::string csv = "alfa,beta,gamma";
    for (auto part : csv | std::views::split(','))
        std::cout << '[' << std::string_view(part.begin(), part.end()) << "] ";
    std::cout << '\n';

    // keys view asszociatív konténeren
    std::map<std::string, int> stock{{"alma", 3}, {"korte", 0}, {"szilva", 7}};
    auto in_stock = stock
        | std::views::filter([](const auto& kv) { return kv.second > 0; })
        | std::views::keys;
    for (const auto& k : in_stock) std::cout << k << ' ';
    std::cout << '\n';
}
```

## Szálak, mutex és condition_variable
<!-- q: Hogyan írjak szálbiztos producer-consumer sort std::thread, mutex és condition_variable segítségével? -->
<!-- tags: std::thread, jthread, mutex, condition_variable, producer consumer, deadlock, scoped_lock -->

A `std::thread` natív szálat indít; join vagy detach nélküli destrukciója `std::terminate`-et hív, ezért C++20-tól a `std::jthread` ajánlott, ami a destruktorában join-ol. Megosztott, nem atomikus adatot csak mutex alatt szabad elérni (különben data race, ami UB); a `lock_guard`/`unique_lock` RAII-val garantálja a feloldást. A `condition_variable::wait`-et mindig predikátummal hívd, mert spurious wakeup előfordulhat; az értesítés a zár elengedése után hatékonyabb. Több zár egyidejű megszerzésére a `std::scoped_lock(m1, m2)` holtpontmentes.

```cpp
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <optional>
#include <queue>
#include <thread>
#include <vector>

// Szálbiztos, korlátos sor (backpressure) mutex + két condition_variable párral
template <typename T>
class BlockingQueue {
public:
    explicit BlockingQueue(std::size_t cap) : cap_(cap) {}

    bool push(T v) {
        std::unique_lock lock(m_);
        not_full_.wait(lock, [&] { return q_.size() < cap_ || closed_; });  // predikátum!
        if (closed_) return false;
        q_.push(std::move(v));
        lock.unlock();                 // értesítés zár nélkül: a felébredő szál nem blokkol
        not_empty_.notify_one();
        return true;
    }
    std::optional<T> pop() {
        std::unique_lock lock(m_);
        not_empty_.wait(lock, [&] { return !q_.empty() || closed_; });
        if (q_.empty()) return std::nullopt;   // lezárva és kiürült
        T v = std::move(q_.front());
        q_.pop();
        lock.unlock();
        not_full_.notify_one();
        return v;
    }
    void close() {
        { std::lock_guard lock(m_); closed_ = true; }
        not_empty_.notify_all();
        not_full_.notify_all();
    }
private:
    std::mutex m_;
    std::condition_variable not_empty_, not_full_;
    std::queue<T> q_;
    std::size_t cap_;
    bool closed_ = false;
};

int main() {
    BlockingQueue<int> queue(8);
    std::mutex out_m;
    long total = 0;
    {
        std::vector<std::jthread> workers;      // a destruktor join-ol
        for (int w = 0; w < 3; ++w)
            workers.emplace_back([&, w] {
                long local = 0;                 // szálanként lokális gyűjtés
                while (auto job = queue.pop()) local += static_cast<long>(*job) * *job;
                std::lock_guard lock(out_m);    // megosztott adat írása csak zár alatt
                total += local;
                std::cout << "worker " << w << ": " << local << '\n';
            });
        for (int i = 1; i <= 100; ++i) queue.push(i);
        queue.close();
    }   // itt minden jthread join-olva
    std::cout << "negyzetosszeg: " << total << '\n';   // 338350
}
```

## Atomikus műveletek és memory_order
<!-- q: Hogyan működnek a std::atomic műveletek és a memory_order (relaxed, acquire, release)? -->
<!-- tags: atomics, memory_order, acquire release, compare_exchange, lock-free, aba problem, spinlock -->

A `std::atomic<T>` oszthatatlan olvasást/írást/RMW-műveletet ad, így data race nélkül érhető el több szálból. A `memory_order` a környező NEM atomikus műveletek láthatóságát szabályozza: `relaxed` csak atomicitást ad (számlálóhoz elég), a release-store + acquire-load pár garantálja, hogy a release előtti összes írás látható az acquire után, a `seq_cst` (alapértelmezett) globális sorrendet is ad. A CAS-ciklus (`compare_exchange_weak`) a lock-free adatszerkezetek alapja, de a törlésnél felmerülő ABA-probléma és a memória biztonságos visszanyerése (hazard pointer, epoch) a valódi nehézség. Gyengébb rendezést csak méréssel indokolva válassz.

```cpp
#include <atomic>
#include <cassert>
#include <iostream>
#include <thread>
#include <vector>

std::atomic<long> hits{0};

// Release/acquire publikálás
struct Config { int port; int workers; };
Config cfg;                                         // nem atomikus adat
std::atomic<bool> ready{false};

void publisher() {
    cfg = {8080, 4};                                // (1) sima írás
    ready.store(true, std::memory_order_release);   // (2) "kiadja" az (1)-et
}
void reader() {
    while (!ready.load(std::memory_order_acquire)) {}   // (3) szinkronizál (2)-vel
    assert(cfg.port == 8080);                           // garantáltan látja (1)-et
}

// Lock-free stack push CAS-ciklussal (Treiber stack)
struct Node { int value; Node* next; };
std::atomic<Node*> head{nullptr};

void push(int v) {
    Node* n = new Node{v, head.load(std::memory_order_relaxed)};
    // Ha head még n->next: csere n-re; ha nem, n->next frissül az aktuális head-re, és újra
    while (!head.compare_exchange_weak(n->next, n,
                                       std::memory_order_release,
                                       std::memory_order_relaxed)) {}
}
// A pop szándékosan hiányzik: ABA-probléma + memória-visszanyerés nélkül hibás lenne.

// Spinlock atomic_flag-gel (C++20 wait/notify: nem pörgeti a CPU-t feleslegesen)
class SpinLock {
    std::atomic_flag f_;
public:
    void lock()   { while (f_.test_and_set(std::memory_order_acquire)) f_.wait(true); }
    void unlock() { f_.clear(std::memory_order_release); f_.notify_one(); }
};

int main() {
    std::vector<std::thread> ts;
    for (int i = 0; i < 4; ++i)
        ts.emplace_back([] {
            for (int k = 0; k < 100000; ++k) hits.fetch_add(1, std::memory_order_relaxed);
        });
    std::thread p(publisher), r(reader);
    for (int i = 0; i < 4; ++i)
        ts.emplace_back([i] { for (int k = 0; k < 10; ++k) push(i * 100 + k); });
    for (auto& t : ts) t.join();
    p.join();
    r.join();

    SpinLock sl;
    sl.lock();
    int count = 0;
    for (Node* n = head.load(); n;) { Node* next = n->next; delete n; n = next; ++count; }
    sl.unlock();
    std::cout << hits.load() << ' ' << count << '\n';   // 400000 40
}
```

## Coroutine-ok (C++20): lusta generátor
<!-- q: Hogyan működnek a C++20 coroutine-ok, hogyan írjak generátort co_yield-del? -->
<!-- tags: coroutines, co_yield, co_await, promise_type, coroutine_handle, generator, c++20 -->

A coroutine olyan függvény, amely felfüggeszthető (`co_yield`, `co_await`) és később folytatható; a fordító állapotgéppé alakítja, a lokális változók pedig egy (általában heapen lévő) coroutine frame-ben élnek. A C++20 csak az alacsony szintű gépezetet adja: a visszatérési típusnak tartalmaznia kell egy `promise_type`-ot, ami szabályozza a kezdő/záró felfüggesztést, a `co_yield` értékét és a kivételeket; kész generátor a C++23 `std::generator`, aszinkron I/O-hoz pedig az Asio vagy a cppcoro ad típusokat. A handle-t RAII-val kell birtokolni, különben a frame szivárog. Buktató: a referenciaként átvett paraméter lógóvá válhat, ha a hívó ideiglenese a felfüggesztés alatt megszűnik – coroutine-ba érték szerint vegyél át.

```cpp
#include <coroutine>
#include <cstdint>
#include <exception>
#include <iostream>
#include <utility>

template <typename T>
class Generator {
public:
    struct promise_type {
        T current{};
        std::exception_ptr error;
        Generator get_return_object() { return Generator{Handle::from_promise(*this)}; }
        std::suspend_always initial_suspend() noexcept { return {}; }  // lusta: az első next()-ig áll
        std::suspend_always final_suspend() noexcept { return {}; }    // a frame-et mi szabadítjuk
        std::suspend_always yield_value(T v) noexcept { current = std::move(v); return {}; }
        void return_void() noexcept {}
        void unhandled_exception() { error = std::current_exception(); }
    };
    using Handle = std::coroutine_handle<promise_type>;

    explicit Generator(Handle h) : h_(h) {}
    Generator(Generator&& o) noexcept : h_(std::exchange(o.h_, {})) {}
    Generator(const Generator&) = delete;
    ~Generator() { if (h_) h_.destroy(); }     // RAII: a frame felszabadítása

    bool next() {                               // folytatás a következő co_yield-ig
        h_.resume();
        if (h_.promise().error) std::rethrow_exception(h_.promise().error);
        return !h_.done();
    }
    const T& value() const { return h_.promise().current; }
private:
    Handle h_;
};

// Végtelen sorozat: csak annyit számol, amennyit lekérnek
Generator<std::uint64_t> fibonacci() {
    std::uint64_t a = 0, b = 1;
    for (;;) {
        co_yield a;
        a = std::exchange(b, a + b);
    }
}

Generator<int> evens_below(int limit) {        // érték szerinti paraméter: biztonságos
    for (int i = 0; i < limit; ++i)
        if (i % 2 == 0) co_yield i;
}

int main() {
    auto fib = fibonacci();
    for (int i = 0; i < 10 && fib.next(); ++i) std::cout << fib.value() << ' ';
    std::cout << '\n';
    auto ev = evens_below(10);
    while (ev.next()) std::cout << ev.value() << ' ';
    std::cout << '\n';
}
```

## Hibakezelés: kivételek, optional és std::expected
<!-- q: Mikor használjak kivételt, std::optional-t vagy std::expected-et C++-ban? -->
<!-- tags: exceptions, noexcept, std::optional, std::expected, error handling, from_chars, c++23 -->

A kivétel a ritka, valóban kivételes hibákra való: nem lehet véletlenül figyelmen kívül hagyni, és a hibaút elválik a normál úttól, de dobáskor drága és a vezérlés nem látszik a kódban. A `std::optional<T>` a „nincs érték” esetre jó, ha a hiba okát nem kell közölni; a `std::expected<T, E>` (C++23) értéket VAGY hibaértéket hordoz kivétel nélkül, és `and_then`/`transform`-mal láncolható – forró útvonalra és hibát gyakran adó parse-olásra ideális. A `noexcept` ígéret, hogy a függvény nem dob (ha mégis: `std::terminate`), ez a move ctoroknál teljesítménykritikus. Kivételt mindig `const&`-ként kapj el, különben slicing történik.

```cpp
#include <charconv>
#include <expected>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>

class ConfigError : public std::runtime_error {
public:
    ConfigError(const std::string& key, const std::string& why)
        : std::runtime_error("config '" + key + "': " + why) {}
};

std::optional<int> find_port(std::string_view scheme) {
    if (scheme == "http") return 80;
    if (scheme == "https") return 443;
    return std::nullopt;
}

enum class ParseError { Empty, NotANumber, OutOfRange };

std::expected<int, ParseError> parse_int(std::string_view s) {
    if (s.empty()) return std::unexpected(ParseError::Empty);
    int value{};
    auto [ptr, ec] = std::from_chars(s.data(), s.data() + s.size(), value);  // nem dob, nem allokál
    if (ec == std::errc::result_out_of_range) return std::unexpected(ParseError::OutOfRange);
    if (ec != std::errc{} || ptr != s.data() + s.size()) return std::unexpected(ParseError::NotANumber);
    return value;
}

// Monadikus láncolás (C++23)
std::expected<int, ParseError> parse_percent(std::string_view s) {
    return parse_int(s).and_then([](int v) -> std::expected<int, ParseError> {
        if (v < 0 || v > 100) return std::unexpected(ParseError::OutOfRange);
        return v;
    });
}

int safe_div(int a, int b) noexcept { return b == 0 ? 0 : a / b; }

// A rendszer határán a hibaértéket kivétellé alakítjuk
int load_workers(std::string_view raw) {
    auto r = parse_int(raw);
    if (!r) throw ConfigError("workers", "ervenytelen szam");
    return *r;
}

int main() {
    std::cout << find_port("https").value_or(-1) << ' ' << find_port("ftp").value_or(-1) << '\n';
    for (std::string_view s : {"42", "abc", "150", ""}) {
        auto p = parse_percent(s);
        if (p) std::cout << s << " -> " << *p << '\n';
        else   std::cout << "'" << s << "' -> hiba #" << static_cast<int>(p.error()) << '\n';
    }
    try {
        load_workers("sok");
    } catch (const ConfigError& e) {      // const& : nincs slicing, nincs másolás
        std::cerr << e.what() << '\n';
    }
    std::cout << safe_div(10, 0) << '\n';
}
```

## std::variant, std::visit és az overloaded minta
<!-- q: Hogyan használjam a std::variant-ot és a std::visit-et típusbiztos tagged unionként? -->
<!-- tags: std::variant, std::visit, overloaded, sum type, tagged union, pattern matching, recursive variant -->

A `std::variant<A, B, C>` típusbiztos tagged union: mindig pontosan egy alternatívát tárol, heap-allokáció és virtuális hívás nélkül, és nyilvántartja, melyik az aktív. A `std::visit` az aktív alternatívára hívja a látogatót; az „overloaded” mintával több lambda egy látogatóvá áll össze, és ha egy alternatíva kimarad, fordítási hiba jön – ez kimerítő ellenőrzés. Zárt típushalmazra (AST, üzenetek, JSON) gyakran jobb, mint az öröklés; nyílt, bővíthető hierarchiára viszont a virtuális függvény a jobb. Rekurzív variánshoz indirekció kell (pl. `std::vector` vagy `unique_ptr`).

```cpp
#include <cmath>
#include <cstddef>
#include <iostream>
#include <string>
#include <variant>
#include <vector>

struct Circle   { double r; };
struct Rect     { double w, h; };
struct Triangle { double a, b, c; };
using Shape = std::variant<Circle, Rect, Triangle>;

// overloaded: több lambdából egy hívható objektum
template <class... Fs> struct overloaded : Fs... { using Fs::operator()...; };
template <class... Fs> overloaded(Fs...) -> overloaded<Fs...>;

double area(const Shape& s) {
    return std::visit(overloaded{
        [](const Circle& c) { return 3.141592653589793 * c.r * c.r; },
        [](const Rect& r)   { return r.w * r.h; },
        [](const Triangle& t) {                     // Hérón-képlet
            double p = (t.a + t.b + t.c) / 2;
            return std::sqrt(p * (p - t.a) * (p - t.b) * (p - t.c));
        },
    }, s);
}

// Rekurzív JSON-szerű érték: a vector adja az indirekciót
struct Json;
using JsonArray = std::vector<Json>;
struct Json { std::variant<std::nullptr_t, bool, double, std::string, JsonArray> v; };

void dump(const Json& j) {
    std::visit(overloaded{
        [](std::nullptr_t)       { std::cout << "null"; },
        [](bool b)               { std::cout << (b ? "true" : "false"); },
        [](double d)             { std::cout << d; },
        [](const std::string& s) { std::cout << '"' << s << '"'; },
        [](const JsonArray& a) {
            std::cout << '[';
            for (std::size_t i = 0; i < a.size(); ++i) {
                if (i) std::cout << ',';
                dump(a[i]);
            }
            std::cout << ']';
        },
    }, j.v);
}

int main() {
    std::vector<Shape> shapes{Circle{1}, Rect{2, 3}, Triangle{3, 4, 5}};
    double total = 0;
    for (const auto& s : shapes) total += area(s);
    std::cout << "osszterulet: " << total << '\n';

    if (auto* r = std::get_if<Rect>(&shapes[1])) std::cout << "rect w=" << r->w << '\n';
    // std::get<Circle>(shapes[1]) -> std::bad_variant_access kivétel

    Json doc{JsonArray{Json{1.5}, Json{std::string("hi")}, Json{true}, Json{nullptr}}};
    dump(doc);
    std::cout << '\n';
}
```

## Virtuális függvények, vtable és öröklés
<!-- q: Hogyan működnek a virtuális függvények és a vtable C++-ban, mi a slicing? -->
<!-- tags: virtual functions, vtable, polymorphism, override, final, virtual destructor, slicing, decorator -->

A virtuális függvény dinamikus diszpécset ad: minden polimorf objektum egy rejtett vptr-t tárol (64 biten 8 bájt), ami az osztály vtable-jére mutat, a hívás pedig vptr → vtable[i] → indirekt ugrás, ami gátolja az inline-olást. Az `override` fordítási hibát ad elírt szignatúránál, a `final` pedig lehetővé teszi a devirtualizálást. Polimorf bázisnak virtuális (vagy protected nem-virtuális) destruktor kell, különben a bázispointeren át történő `delete` UB. Érték szerinti átadásnál slicing történik: a származtatott rész levágódik; konstruktorban/destruktorban hívott virtuális függvény pedig nem a leszármazott változatát hívja.

```cpp
#include <iostream>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

class Logger {
public:
    virtual ~Logger() = default;                    // nélküle Base*-on át delete: UB
    virtual void log(std::string_view msg) = 0;     // tisztán virtuális
    void info(std::string_view m) { log(m); }       // nem virtuális belépési pont (NVI)
};

class ConsoleLogger : public Logger {
public:
    void log(std::string_view msg) override { std::cout << "[konzol] " << msg << '\n'; }
};

// final: nem származtatható tovább -> a fordító devirtualizálhat
class PrefixLogger final : public Logger {
public:
    PrefixLogger(std::string prefix, std::unique_ptr<Logger> inner)
        : prefix_(std::move(prefix)), inner_(std::move(inner)) {}
    void log(std::string_view msg) override {       // dekorátor minta
        inner_->log(prefix_ + std::string(msg));
    }
private:
    std::string prefix_;
    std::unique_ptr<Logger> inner_;
};

struct Plain { int x; };
struct Poly  { int x; virtual ~Poly() = default; };   // + rejtett vptr

struct Animal {
    virtual ~Animal() = default;
    virtual std::string sound() const { return "..."; }
};
struct Dog : Animal {
    std::string sound() const override { return "vau"; }
};
std::string speak_copy(Animal a) { return a.sound(); }        // slicing: mindig "..."
std::string speak_ref(const Animal& a) { return a.sound(); }  // dinamikus diszpécs: "vau"

int main() {
    std::vector<std::unique_ptr<Logger>> loggers;
    loggers.push_back(std::make_unique<ConsoleLogger>());
    loggers.push_back(std::make_unique<PrefixLogger>("[app] ", std::make_unique<ConsoleLogger>()));
    for (auto& l : loggers) l->info("indulas");

    std::cout << sizeof(Plain) << " vs " << sizeof(Poly) << '\n';   // 4 vs 16 x86-64-en
    Dog d;
    std::cout << speak_copy(d) << ' ' << speak_ref(d) << '\n';
}
```
