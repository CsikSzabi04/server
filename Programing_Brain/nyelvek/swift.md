# Swift
<!-- tech: swift -->
<!-- aliases: swiftui, ios -->

A Swift az Apple által fejlesztett, LLVM-re épülő, natívan forduló, statikusan és erősen típusos nyelv típuskövetkeztetéssel. Memóriakezelése ARC (automatikus referenciaszámlálás, nincs tracing GC), erősen épít az értékszemantikára (struct, enum) és a protokoll-orientált programozásra; a Swift 6 nyelvi mód fordítási időben zárja ki az adatversenyeket (actorok, Sendable). Elsősorban iOS/macOS/watchOS/visionOS appokhoz használják (SwiftUI, UIKit), de fut Linuxon és Windowson is (szerveroldalon pl. Vapor). Kevésbé ideális, ha Apple-ökoszisztémán kívüli, többplatformos UI kell, vagy ha nagyon gyors fordítási idő a fő szempont.

## Értéktípusok és referenciatípusok (struct vs class)
<!-- q: Mi a különbség a struct és a class között Swiftben, és mi az a copy-on-write? -->
<!-- tags: value types, reference types, struct, class, copy-on-write, mutating, identity -->

A `struct` és `enum` értéktípus: értékadáskor és paraméterátadáskor logikailag másolat készül, így nincs rejtett megosztott állapot. A `class` referenciatípus: több változó ugyanarra az objektumra mutat, van identitása (`===`), öröklődése és `deinit`-je. A standard gyűjtemények (Array, Dictionary, String) copy-on-write-ot használnak, tehát a másolás olcsó, a tényleges duplikálás csak módosításkor történik; saját típusban ez az `isKnownUniquelyReferenced`-del valósítható meg. Alapértelmezésként válassz struct-ot, class-t akkor, ha identitás vagy megosztott, módosítható állapot kell.

```swift
// Értéktípus: másoláskor független példány jön létre.
struct Pont {
    var x: Double
    var y: Double

    // mutating: az értéktípus saját magát módosító metódusa
    mutating func eltol(dx: Double, dy: Double) {
        x += dx
        y += dy
    }
}

// Referenciatípus: a változók ugyanarra az objektumra mutatnak.
final class Szamla {
    var egyenleg: Int
    init(egyenleg: Int) { self.egyenleg = egyenleg }
}

var a = Pont(x: 0, y: 0)
var b = a              // másolat
b.eltol(dx: 5, dy: 5)
print(a.x, b.x)        // 0.0 5.0

let s1 = Szamla(egyenleg: 100)
let s2 = s1            // ugyanaz az objektum (a let csak a referenciát fagyasztja)
s2.egyenleg -= 30
print(s1.egyenleg)     // 70
print(s1 === s2)       // true — identitás-összehasonlítás

// Copy-on-write saját típusban: a másolás csak módosításkor és csak
// megosztott tárolónál történik meg.
struct NagyPuffer {
    private final class Tarolo {
        var bajtok: [UInt8]
        init(_ b: [UInt8]) { bajtok = b }
    }
    private var tarolo: Tarolo

    init(meret: Int) { tarolo = Tarolo(Array(repeating: 0, count: meret)) }

    subscript(i: Int) -> UInt8 {
        get { tarolo.bajtok[i] }
        set {
            // Ha más is hivatkozik a tárolóra, előbb lemásoljuk.
            if !isKnownUniquelyReferenced(&tarolo) {
                tarolo = Tarolo(tarolo.bajtok)
            }
            tarolo.bajtok[i] = newValue
        }
    }
}

var p1 = NagyPuffer(meret: 1_000_000)
var p2 = p1            // még nincs másolás: közös tároló
p2[0] = 42             // itt történik a másolás
print(p1[0], p2[0])    // 0 42
```

## Optionalök biztonságos kezelése
<!-- q: Hogyan kezeljem az optional értékeket Swiftben (if let, guard let, ??, optional chaining)? -->
<!-- tags: optionals, if let, guard let, nil coalescing, optional chaining, force unwrap -->

Az `Optional<T>` (`T?`) egy enum: vagy `.some(érték)`, vagy `.none` (nil), így a fordító kikényszeríti a hiányzó érték kezelését. A `guard let` korai kilépést ad, utána a változó nem-opcionális; az `if let x` rövidítés Swift 5.7 óta használható. Az optional chaining (`a?.b?.c`) bármelyik nil láncszemnél nil-t ad, a `??` alapértéket, a `map`/`flatMap` pedig csak meglévő értéken fut. A `!` (force unwrap) nil esetén azonnal összeomlik — csak ott használd, ahol a nil logikai hiba lenne.

```swift
struct Cim { let varos: String; let iranyitoszam: String? }
struct Felhasznalo { let nev: String; let cim: Cim? }

let adatbazis: [Int: Felhasznalo] = [
    1: Felhasznalo(nev: "Teszt Elek", cim: Cim(varos: "Kecskemét", iranyitoszam: "6000")),
    2: Felhasznalo(nev: "Minta Anna", cim: nil),
]

// guard let: korai kilépés; utána a változó nem-opcionális.
func szallitasiCimke(id: Int) -> String {
    guard let f = adatbazis[id] else { return "ismeretlen felhasználó" }
    guard let cim = f.cim else { return "\(f.nev): nincs cím" }
    return "\(f.nev), \(cim.iranyitoszam ?? "????") \(cim.varos)"   // ?? alapérték
}

print(szallitasiCimke(id: 1))
print(szallitasiCimke(id: 2))
print(szallitasiCimke(id: 9))

// Optional chaining: bármelyik láncszem nil -> az egész nil.
let irsz: String? = adatbazis[1]?.cim?.iranyitoszam
if let irsz {                       // Swift 5.7+ rövidítés
    print("irányítószám:", irsz)
}

// map / flatMap: csak akkor fut, ha van érték.
let irszSzam: Int? = irsz.flatMap { Int($0) }   // Int(String) maga is opcionálist ad
print(irszSzam.map { $0 * 2 } as Any)

// switch mintaillesztés opcionálisra
switch adatbazis[2]?.cim {
case .some(let c): print("van cím:", c.varos)
case .none: print("nincs cím")
}
```

## Hibakezelés: throws, typed throws, Result
<!-- q: Hogyan kezeljem a hibákat Swiftben (throws, do-catch, typed throws, Result)? -->
<!-- tags: error handling, throws, typed throws, do catch, Result, try?, rethrows, defer -->

Swiftben a hibát dobó függvényt `throws` jelöli, hívása `try`-jal történik, és `do`/`catch` kapja el; a hibák az `Error` protokollnak megfelelő típusok, jellemzően asszociált értékes enumok. Swift 6 óta létezik typed throws (`throws(FizetesHiba)`), így a hívó pontosan tudja, milyen hiba jöhet. A `try?` a hibát nil-lé alakítja, a `Result` a hibát értékként tárolja (callback API-knál hasznos), a `defer` pedig a scope elhagyásakor mindig lefut. Buktató: a `try!` hibánál összeomlik, éles kódban kerülendő.

```swift
import Foundation

enum FizetesHiba: Error, LocalizedError {
    case nincsFedezet(hiany: Decimal)
    case kartyaLejart

    var errorDescription: String? {
        switch self {
        case .nincsFedezet(let h): return "Nincs elég fedezet, hiányzik: \(h)"
        case .kartyaLejart: return "A kártya lejárt"
        }
    }
}

struct Penztarca {
    private(set) var egyenleg: Decimal
    init(egyenleg: Decimal) { self.egyenleg = egyenleg }

    // Swift 6 typed throws: csak FizetesHiba dobható.
    mutating func fizet(_ osszeg: Decimal) throws(FizetesHiba) {
        guard osszeg <= egyenleg else {
            throw .nincsFedezet(hiany: osszeg - egyenleg)
        }
        egyenleg -= osszeg
    }
}

var t = Penztarca(egyenleg: 5000)
do {
    try t.fizet(3000)
    try t.fizet(4000)
} catch FizetesHiba.nincsFedezet(let hiany) {   // eset szerinti elkapás
    print("Hiány:", hiany)
} catch {
    print("Egyéb:", error)
}

// try?: hiba -> nil, ha az ok nem érdekes.
let siker = (try? t.fizet(100)) != nil
print("sikerült?", siker)

// Result: hiba értékként (pl. callbackekben).
func betolt(_ id: Int) -> Result<String, FizetesHiba> {
    id > 0 ? .success("tranzakció-\(id)") : .failure(.kartyaLejart)
}
switch betolt(-1) {
case .success(let v): print(v)
case .failure(let e): print(e.localizedDescription)
}

// rethrows: csak akkor dob, ha a kapott closure dob.
func ujraprobal<T>(_ n: Int, _ muvelet: () throws -> T) rethrows -> T {
    for _ in 1..<n {
        if let v = try? muvelet() { return v }
    }
    return try muvelet()   // az utolsó próbálkozás hibája továbbmegy
}

// defer: a scope elhagyásakor mindig lefut (takarítás).
func feldolgoz() {
    print("zár megszerezve")
    defer { print("zár elengedve") }
    print("munka...")
}
feldolgoz()
print(ujraprobal(3) { 42 })
```

## Protokollok és protokoll-orientált programozás
<!-- q: Mi a protokoll-orientált programozás Swiftben, és hogyan működnek a protokoll-kiterjesztések? -->
<!-- tags: protocols, protocol extensions, protocol-oriented programming, default implementation, static dispatch -->

A protokoll követelményeket (metódusok, property-k) ír le, amelyeknek struct, enum és class egyaránt megfelelhet; a protokoll-kiterjesztés (`extension`) alapértelmezett implementációt ad, így öröklési hierarchia nélkül osztható meg viselkedés. Feltételes kiterjesztéssel (`extension Array where Element: Alakzat`) csak bizonyos típusokra adható funkció, a protokoll-kompozíció (`A & B`) pedig több megfelelést követel egyszerre. Fontos buktató: a csak kiterjesztésben definiált, a protokollban nem deklarált metódus statikusan diszpécselődik, így egy `any P` értéken a kiterjesztés változata fut, nem a típus saját felülírása.

```swift
import Foundation

protocol Alakzat {
    var nev: String { get }
    func terulet() -> Double
}

// Alapértelmezett implementáció minden megfelelő típusnak.
extension Alakzat {
    var nev: String { String(describing: Self.self) }
    func leiras() -> String { "\(nev): \(String(format: "%.2f", terulet()))" }
}

protocol Rajzolhato {
    func rajzol(skala: Double) -> String
}

// Feltételes kiterjesztés: csak Alakzat-elemű tömbökön.
extension Array where Element: Alakzat {
    var osszTerulet: Double { reduce(0) { $0 + $1.terulet() } }
}

struct Kor: Alakzat, Rajzolhato {
    let r: Double
    func terulet() -> Double { .pi * r * r }
    func rajzol(skala: Double) -> String { "○ r=\(r * skala)" }
}

struct Teglalap: Alakzat {
    let a, b: Double
    var nev: String { "Téglalap \(a)x\(b)" }   // felülírja az alapértelmezettet
    func terulet() -> Double { a * b }
}

// Protokoll-kompozíció: mindkettőnek meg kell felelnie.
func megjelenit(_ x: some Alakzat & Rajzolhato) {
    print(x.leiras(), x.rajzol(skala: 2))
}

let korok = [Kor(r: 1.5), Kor(r: 2)]
print(korok.osszTerulet)
megjelenit(korok[0])
print(Teglalap(a: 2, b: 3).leiras())

// Buktató: a protokollban NEM deklarált kiterjesztés-metódus statikus diszpécsű.
protocol Udvozlo { func szia() -> String }
extension Udvozlo {
    func szia() -> String { "alap szia" }
    func viszlat() -> String { "alap viszlát" }   // nem követelmény!
}
struct Magyar: Udvozlo {
    func szia() -> String { "Szia!" }
    func viszlat() -> String { "Viszlát!" }
}
let u: any Udvozlo = Magyar()
print(u.szia(), u.viszlat())   // "Szia!" "alap viszlát"
```

## Generikusok és asszociált típusok
<!-- q: Hogyan használjam a generikusokat és az associatedtype-ot Swift protokollokban? -->
<!-- tags: generics, associatedtype, primary associated type, where clause, conditional conformance -->

A generikus függvények és típusok típusparaméterekkel dolgoznak, amelyeket protokoll-megkötések és `where` záradékok korlátoznak; a fordító specializálja őket, így nincs futásidejű költség. Protokollban az `associatedtype` egy a megfelelő típus által meghatározott helyőrző típus (pl. a tároló eleme); Swift 5.7 óta a primary associated type (`protocol Tarolo<Elem>`) lehetővé teszi a `some Tarolo<Int>` írásmódot. A feltételes megfelelés (`extension Par: Equatable where A: Equatable`) csak akkor ad képességet, ha a típusargumentumok is tudják.

```swift
// Protokoll asszociált típusokkal; <Elem> = primary associated type.
protocol Tarolo<Elem> {
    associatedtype Elem
    associatedtype Kulcs: Hashable
    mutating func ment(_ e: Elem) -> Kulcs
    func betolt(_ k: Kulcs) -> Elem?
}

// Generikus implementáció: az asszociált típusokat a fordító kikövetkezteti (Elem = T, Kulcs = Int).
struct MemoriaTarolo<T>: Tarolo {
    private var adat: [Int: T] = [:]
    private var kovetkezo = 0

    mutating func ment(_ e: T) -> Int {
        defer { kovetkezo += 1 }
        adat[kovetkezo] = e
        return kovetkezo
    }
    func betolt(_ k: Int) -> T? { adat[k] }
}

// Generikus függvény where-záradékkal.
func legnagyobb<S: Sequence>(_ s: S) -> S.Element? where S.Element: Comparable {
    s.reduce(nil) { acc, x in
        guard let acc else { return x }
        return max(acc, x)
    }
}

// Feltételes megfelelés.
struct Par<A, B> {
    let elso: A
    let masodik: B
}
extension Par: Equatable where A: Equatable, B: Equatable {}
extension Par: CustomStringConvertible {
    var description: String { "(\(elso), \(masodik))" }
}

// Tetszőleges Tarolo-val működő függvény.
func mindetMent<T: Tarolo>(_ t: inout T, _ elemek: [T.Elem]) -> [T.Kulcs] {
    var kulcsok: [T.Kulcs] = []
    for e in elemek { kulcsok.append(t.ment(e)) }
    return kulcsok
}

var tar = MemoriaTarolo<String>()
let kulcsok = mindetMent(&tar, ["alma", "körte"])
print(kulcsok, tar.betolt(1) ?? "-")
print(legnagyobb([3, 9, 2]) ?? 0, legnagyobb("swift") ?? " ")
print(Par(elso: 1, masodik: "a") == Par(elso: 1, masodik: "a"), Par(elso: 2, masodik: true))
```

## Opaque és existential típusok: some vs any
<!-- q: Mi a különbség a some és az any kulcsszó között Swiftben? -->
<!-- tags: opaque types, existential, some, any, type erasure, implicit opening -->

A `some P` (opaque típus) egyetlen, a hívó elől elrejtett, de a fordító által ismert konkrét típust jelent: statikus diszpécs, nincs doboz, és megmarad a típusidentitás (pl. `==` működik). Az `any P` (existential) egy doboz, amely bármilyen megfelelő típust tárolhat — ez kell heterogén kollekcióhoz, de dinamikus diszpécset, esetleges heap-allokációt és típusinformáció-vesztést jelent. Paraméterben a `some P` a rövidített generikus szintaxis, és Swift 5.7 óta egy `any P` érték implicit módon átadható `some P` paraméternek (existential opening). Ökölszabály: alapból `some`, `any` csak ha tényleg heterogén értékek kellenek.

```swift
protocol Szuro<Bemenet> {
    associatedtype Bemenet
    func alkalmaz(_ x: Bemenet) -> Bool
}

struct MinHossz: Szuro {
    let n: Int
    func alkalmaz(_ x: String) -> Bool { x.count >= n }
}
struct Tartalmaz: Szuro {
    let resz: String
    func alkalmaz(_ x: String) -> Bool { x.contains(resz) }
}

// OPAQUE visszatérés: a hívó nem látja a konkrét típust, a fordító igen.
// Minden return ágnak UGYANAZT a konkrét típust kell adnia!
func jelszoSzabaly() -> some Szuro<String> {
    MinHossz(n: 12)
}

// EXISTENTIAL: heterogén kollekció, dinamikus diszpécs.
let szabalyok: [any Szuro<String>] = [MinHossz(n: 8), Tartalmaz(resz: "@")]

func ellenoriz(_ s: String, _ szabalyok: [any Szuro<String>]) -> Bool {
    szabalyok.allSatisfy { $0.alkalmaz(s) }
}

// "some" paraméterben = func naplo<T: Szuro<String>>(_ sz: T, ...)
func naplo(_ sz: some Szuro<String>, _ minta: String) {
    print(type(of: sz), sz.alkalmaz(minta))
}

print(ellenoriz("user@example.com", szabalyok))
naplo(jelszoSzabaly(), "rovid")

// Implicit existential-nyitás: any -> some paraméterbe átadható.
for sz in szabalyok {
    naplo(sz, "teszt@teszt")
}

// Típusidentitás: két "some" ugyanabból a függvényből azonos típusú.
func azonosito() -> some Equatable { 42 }
print(azonosito() == azonosito())   // true
// let x: any Equatable = 1; x == x  // HIBA: any Equatable-ön nincs ==
```

## ARC, retain ciklusok, weak és unowned
<!-- q: Hogyan működik az ARC Swiftben, és hogyan kerüljem el a retain ciklusokat? -->
<!-- tags: arc, memory management, retain cycle, weak, unowned, deinit, delegate -->

Az ARC fordítási időben beszúrt retain/release hívásokkal számolja az erős referenciákat, és amikor a számláló nullára esik, az objektum azonnal felszabadul (`deinit` fut). Ha két objektum kölcsönösen erősen hivatkozik egymásra, retain ciklus keletkezik és egyik sem szabadul fel — ezt `weak` (opcionális, felszabaduláskor nil-re áll) vagy `unowned` (nem opcionális, csak ha a hivatkozott garantáltan tovább él, különben crash) referenciával kell megtörni. Tipikus helyek: szülő–gyerek kapcsolat visszamutató oldala és a delegate minta (`weak var delegate`, class-bound protokollal). Szivárgást az Xcode Memory Graph Debugger és az Instruments Leaks mutat.

```swift
final class Szulo {
    let nev: String
    var gyerekek: [Gyerek] = []          // erős referencia lefelé
    init(nev: String) { self.nev = nev }
    deinit { print("\(nev) felszabadítva") }
}

final class Gyerek {
    let nev: String
    weak var szulo: Szulo?               // gyenge referencia felfelé -> nincs ciklus
    init(nev: String) { self.nev = nev }
    deinit { print("\(nev) felszabadítva") }
}

// unowned: a kártya nem élhet tovább a tulajdonosánál.
final class Ugyfel {
    var kartya: Bankkartya?
    deinit { print("Ügyfél felszabadítva") }
}
final class Bankkartya {
    unowned let tulajdonos: Ugyfel
    init(tulajdonos: Ugyfel) { self.tulajdonos = tulajdonos }
    deinit { print("Kártya felszabadítva") }
}

// Delegate: mindig weak, ezért class-bound (AnyObject) protokoll kell.
protocol LetoltoDelegate: AnyObject {
    func kesz(_ adat: String)
}
final class Letolto {
    weak var delegate: LetoltoDelegate?
    func indit() { delegate?.kesz("payload") }
}
final class Kepernyo: LetoltoDelegate {
    let letolto = Letolto()
    init() { letolto.delegate = self }   // Kepernyo -> Letolto erős, vissza gyenge
    func kesz(_ adat: String) { print("megjött:", adat) }
    deinit { print("Képernyő felszabadítva") }
}

do {
    let apa = Szulo(nev: "Szülő")
    let fiu = Gyerek(nev: "Gyerek")
    apa.gyerekek.append(fiu)
    fiu.szulo = apa
}   // mindkét deinit lefut; weak nélkül egyik sem -> memóriaszivárgás

do {
    let u = Ugyfel()
    u.kartya = Bankkartya(tulajdonos: u)
}

do {
    let k = Kepernyo()
    k.letolto.indit()
}
```

## Closure-ök és capture listák
<!-- q: Hogyan működnek a closure-ök és a capture listák ([weak self]) Swiftben? -->
<!-- tags: closures, capture list, weak self, escaping, autoclosure, retain cycle -->

A closure a környezetéből befogott változókat referenciaként tartja életben; az `@escaping` closure túléli a függvényhívást (eltároljuk), ezért ha `self`-et erősen fogja be, és `self` is tartja a closure-t, retain ciklus keletkezik. A capture lista (`[weak self]`, `[unowned self]`, `[x]`) szabályozza a befogás módját: a `[x]` a létrehozáskori értéket rögzíti. A nem-escaping (alapértelmezett) closure-ökben, pl. `map`, a `self` nyugodtan használható erősen. Az `@autoclosure` lusta kiértékelést ad: a kifejezés csak akkor fut le, ha tényleg szükség van rá.

```swift
// Eseménybusz: eltárolja (escaping) a feliratkozók closure-jeit.
final class EsemenyBusz {
    private var figyelok: [(String) -> Void] = []
    func feliratkozik(_ f: @escaping (String) -> Void) { figyelok.append(f) }
    func kuld(_ e: String) { figyelok.forEach { $0(e) } }
}

final class ProfilNezet {
    let busz: EsemenyBusz
    private(set) var cim = ""

    init(busz: EsemenyBusz) {
        self.busz = busz
        // nézet -> busz -> closure -> nézet: erős self-fel RETAIN CIKLUS lenne.
        busz.feliratkozik { [weak self] uzenet in
            guard let self else { return }   // ha a nézet már felszabadult
            self.cim = uzenet
        }
    }
    deinit { print("ProfilNezet felszabadítva") }
}

do {
    let busz = EsemenyBusz()
    let nezet = ProfilNezet(busz: busz)
    busz.kuld("Új cím")
    print(nezet.cim)
}   // a [weak self] miatt a deinit lefut

// Capture lista értékrögzítésre: a LÉTREHOZÁSKORI értéket látja.
var szamlalo = 0
let rogzitett = { [szamlalo] in print("rögzített:", szamlalo) }
let elo = { print("élő:", szamlalo) }
szamlalo = 10
rogzitett()   // 0
elo()         // 10

// A befogott belső állapot (osszeg) a closure-ben él tovább.
func akkumulator(kezdo: Int) -> (Int) -> Int {
    var osszeg = kezdo
    return { osszeg += $0; return osszeg }
}
let acc = akkumulator(kezdo: 100)
_ = acc(5)
print(acc(10))   // 115

// @autoclosure: lusta kiértékelés.
func naplo(_ uzenet: @autoclosure () -> String, szint: Int) {
    if szint >= 2 { print(uzenet()) }
}
naplo("drága formázás: \(Array(1...5).map { $0 * $0 })", szint: 1)   // nem értékelődik ki
```

## async/await és callback API-k áthidalása
<!-- q: Hogyan használjam az async/await-et Swiftben, és hogyan alakítsak át callbacket async-ra? -->
<!-- tags: async await, concurrency, async let, URLSession, continuation, Task -->

Az `async` függvény felfüggesztheti magát `await` pontokon a szál blokkolása nélkül; a futtatókörnyezet közben más feladatokat futtat ugyanazon a szálkészleten. Az `async let` független műveleteket indít párhuzamosan, amelyeket később együtt várunk be. A régi completion-handleres API-k a `withCheckedThrowingContinuation`-nel alakíthatók async-ra; a continuationt pontosan egyszer kell folytatni, különben a feladat örökre függ (vagy debugban hibát kapsz). Szinkron kódból `Task { }`-kel indítható async munka, belépési pontként pedig `@main` + `static func main() async` használható.

```swift
import Foundation

struct Termek: Decodable { let id: Int; let nev: String; let ar: Double }

enum ApiHiba: Error { case rosszStatusz(Int) }

// async throws: felfüggeszthető és hibát dobhat.
func termekLetolt(id: Int) async throws -> Termek {
    let url = URL(string: "https://api.example.com/termekek/\(id)")!
    let (data, valasz) = try await URLSession.shared.data(from: url)
    guard let http = valasz as? HTTPURLResponse, http.statusCode == 200 else {
        throw ApiHiba.rosszStatusz((valasz as? HTTPURLResponse)?.statusCode ?? -1)
    }
    return try JSONDecoder().decode(Termek.self, from: data)
}

// async let: két független kérés PÁRHUZAMOSAN fut.
func olcsobb(_ a: Int, _ b: Int) async throws -> String {
    async let elso = termekLetolt(id: a)
    async let masodik = termekLetolt(id: b)
    let (t1, t2) = try await (elso, masodik)
    return t1.ar < t2.ar ? t1.nev : t2.nev
}

// Régi, callback-alapú API...
func regiApi(_ id: Int, kesz: @escaping @Sendable (Result<String, Error>) -> Void) {
    DispatchQueue.global().async { kesz(.success("régi-\(id)")) }
}

// ...áthidalása async-ra continuationnel.
func modernApi(_ id: Int) async throws -> String {
    try await withCheckedThrowingContinuation { cont in
        regiApi(id) { eredmeny in
            cont.resume(with: eredmeny)   // PONTOSAN egyszer!
        }
    }
}

@main
struct App {
    static func main() async {
        do {
            print(try await modernApi(7))
            print("olcsóbb:", try await olcsobb(1, 2))
        } catch {
            print("hiba:", error)
        }
    }
}
```

## Actorok, Sendable és @MainActor
<!-- q: Mik az actorok és a Sendable Swiftben, és hogyan kerülöm el az adatversenyt? -->
<!-- tags: actor, sendable, mainactor, data race, isolation, reentrancy, swift 6 -->

Az `actor` referenciatípus, amelynek módosítható állapotához egyszerre csak egy feladat fér hozzá; kívülről a metódusai `await`-tel hívhatók, így a fordító garantálja az adatverseny-mentességet. A `Sendable` jelzi, hogy egy típus biztonságosan átadható concurrency-határokon (értéktípusok Sendable mezőkkel automatikusan azok, osztálynál `final` + immutable mezők, vagy `@unchecked Sendable` saját zárral). A `@MainActor` a UI-állapotot a fő szálhoz köti. A legnagyobb buktató az actor reentrancy: minden `await` pontnál más hívások is beléphetnek, ezért az `await` után az állapotot újra ellenőrizni kell.

```swift
import Foundation

actor KepCache {
    private var cache: [String: Data] = [:]
    private var folyamatban: [String: Task<Data, Error>] = [:]

    func kep(_ url: String) async throws -> Data {
        if let d = cache[url] { return d }
        // REENTRANCY: az await alatt más hívás is beléphet -> a futó Task-ot is
        // eltároljuk, hogy ugyanazt ne töltsük le kétszer.
        if let futo = folyamatban[url] { return try await futo.value }

        let task = Task { try await Self.letolt(url) }
        folyamatban[url] = task
        defer { folyamatban[url] = nil }
        let d = try await task.value
        cache[url] = d
        return d
    }

    private static func letolt(_ url: String) async throws -> Data {
        try await Task.sleep(for: .milliseconds(50))
        return Data(url.utf8)
    }

    nonisolated var nev: String { "KepCache" }   // nem érinti az állapotot -> await nélkül hívható
}

struct Beallitas: Sendable {   // értéktípus Sendable mezőkkel
    let tema: String
    let meret: Int
}

final class Naplo: @unchecked Sendable {   // @unchecked: a szálbiztonságot MI garantáljuk
    private let zar = NSLock()
    private var sorok: [String] = []
    func ir(_ s: String) {
        zar.lock(); defer { zar.unlock() }
        sorok.append(s)
    }
}

@MainActor
final class GaleriaModell {
    private(set) var kepek: [Data] = []
    private let cache = KepCache()
    let naplo = Naplo()

    func betolt(_ urlek: [String]) async {
        for u in urlek {
            if let d = try? await cache.kep(u) {   // izolációs határ: await kell
                kepek.append(d)                     // a folytatás újra a MainActoron fut
                naplo.ir("betöltve: \(u)")
            }
        }
    }
}

let modell = GaleriaModell()
await modell.betolt(["a.png", "b.png", "a.png"])
print(modell.kepek.count, Beallitas(tema: "sötét", meret: 14).tema)
```

## Strukturált konkurencia: TaskGroup és megszakítás
<!-- q: Hogyan futtassak párhuzamos feladatokat TaskGroup-pal és korlátozott párhuzamossággal Swiftben? -->
<!-- tags: structured concurrency, TaskGroup, withThrowingTaskGroup, cancellation, timeout, async let -->

A strukturált konkurenciában a gyerek-feladatok élettartama a szülő scope-hoz kötött: a `withThrowingTaskGroup` nem tér vissza, amíg minden gyerek be nem fejeződött, és hiba esetén automatikusan megszakítja a többit. A megszakítás kooperatív: a feladatnak magának kell ellenőriznie (`Task.checkCancellation()`, `Task.isCancelled`), a `Task.sleep` pedig megszakításkor hibát dob. Korlátozott párhuzamossághoz „csúszó ablakot” használunk: csak N gyereket indítunk, és minden befejezett helyére újat. Kerüld a strukturálatlan `Task { }` és `Task.detached` felesleges használatát, mert azok megszakítása és hibái nem terjednek automatikusan.

```swift
import Foundation

struct Oldal: Sendable { let url: String; let meret: Int }

func letolt(_ url: String) async throws -> Oldal {
    try Task.checkCancellation()   // kooperatív megszakítás
    try await Task.sleep(for: .milliseconds(Int.random(in: 10...80)))
    if url.hasSuffix("hibas") { throw URLError(.badServerResponse) }
    return Oldal(url: url, meret: url.count * 1024)
}

// Legfeljebb `maxPar` letöltés fut egyszerre; az első hiba mindent megszakít.
func mindLetolt(_ urlek: [String], maxPar: Int = 3) async throws -> [Oldal] {
    try await withThrowingTaskGroup(of: Oldal.self) { group in
        var eredmeny: [Oldal] = []
        var iter = urlek.makeIterator()

        for _ in 0..<maxPar {              // első hullám
            guard let u = iter.next() else { break }
            group.addTask { try await letolt(u) }
        }
        while let oldal = try await group.next() {   // csúszó ablak
            eredmeny.append(oldal)
            if let u = iter.next() {
                group.addTask { try await letolt(u) }
            }
        }
        return eredmeny
        // Ha a next() hibát dob, a csoport kilépéskor megszakítja és bevárja a többit.
    }
}

// Időkorlát: verseny a munka és egy időzítő között.
func idokorlattal<T: Sendable>(
    _ mp: Double,
    _ munka: @escaping @Sendable () async throws -> T
) async throws -> T {
    try await withThrowingTaskGroup(of: T.self) { group in
        group.addTask { try await munka() }
        group.addTask {
            try await Task.sleep(for: .seconds(mp))
            throw CancellationError()
        }
        let elso = try await group.next()!   // amelyik előbb végez
        group.cancelAll()                     // a másikat leállítjuk
        return elso
    }
}

let urlek = (1...8).map { "https://example.com/oldal/\($0)" }
let oldalak = try await mindLetolt(urlek)
print("letöltve:", oldalak.count)
let gyors = try await idokorlattal(0.5) { try await letolt("https://example.com/gyors") }
print(gyors.meret)
```

## Combine alapok
<!-- q: Hogyan működik a Combine keretrendszer (Publisher, operátorok, AnyCancellable)? -->
<!-- tags: combine, publisher, subscriber, published, debounce, sink, anycancellable, reactive -->

A Combine az Apple reaktív keretrendszere: a `Publisher` időben érkező értékeket és egy befejezést (vagy hibát) bocsát ki, az operátorok (`map`, `debounce`, `removeDuplicates`, `flatMap`, `combineLatest`) láncot építenek, a `sink`/`assign` pedig feliratkozik. A feliratkozás `AnyCancellable`-t ad vissza; ha ez felszabadul, a lánc leáll, ezért `store(in: &cancellables)`-szel tároljuk. Hiba után a publisher befejeződik, ezért a belső láncban `catch`-csel kell kezelni, hogy a külső folyam életben maradjon. Új kódban sok esetben az async/await, az `AsyncSequence` és az `@Observable` egyszerűbb alternatíva.

```swift
import Combine
import Foundation

final class KeresoViewModel: ObservableObject {
    @Published var keresoSzoveg = ""                    // Publisher: $keresoSzoveg
    @Published private(set) var talalatok: [String] = []
    @Published private(set) var hiba: String?

    private var cancellables = Set<AnyCancellable>()    // ha felszabadul, leiratkozik
    private let adatbazis = ["swift", "swiftui", "combine", "concurrency", "actor"]

    init() {
        $keresoSzoveg
            .debounce(for: .milliseconds(300), scheduler: RunLoop.main)   // gépelés közben vár
            .map { $0.trimmingCharacters(in: .whitespaces).lowercased() }
            .removeDuplicates()                                            // ugyanarra ne keressen újra
            .filter { $0.count >= 2 }
            .flatMap { [unowned self] q in
                self.keres(q)
                    .catch { err -> Just<[String]> in   // hiba -> üres lista; a külső lánc él tovább
                        self.hiba = err.localizedDescription
                        return Just([])
                    }
            }
            .receive(on: DispatchQueue.main)
            .sink { [weak self] in self?.talalatok = $0 }                  // [weak self]: nincs ciklus
            .store(in: &cancellables)
    }

    // Aszinkron "API-hívás" szimulálása; a hívó csak AnyPublisher-t lát (típus-elrejtés).
    private func keres(_ q: String) -> AnyPublisher<[String], Error> {
        Just(adatbazis.filter { $0.contains(q) })
            .delay(for: .milliseconds(100), scheduler: DispatchQueue.global())
            .setFailureType(to: Error.self)
            .eraseToAnyPublisher()
    }
}

// Két forrás kombinálása: az űrlap akkor érvényes, ha mindkét mező az.
let email = CurrentValueSubject<String, Never>("")
let jelszo = CurrentValueSubject<String, Never>("")
let feliratkozas = email.combineLatest(jelszo)
    .map { e, j in e.contains("@") && j.count >= 8 }
    .removeDuplicates()
    .sink { print("űrlap érvényes:", $0) }
email.send("teszt@example.com")
jelszo.send("hosszujelszo123")
feliratkozas.cancel()
```

## SwiftUI állapot: @State és @Binding
<!-- q: Hogyan működik a @State és a @Binding SwiftUI-ban? -->
<!-- tags: swiftui, state, binding, view, declarative ui, foreach, source of truth -->

SwiftUI-ban a nézet az állapot függvénye: a `body` minden állapotváltozáskor újraértékelődik, és a keretrendszer csak a ténylegesen változott részeket rajzolja újra. A `@State` a nézet saját, a SwiftUI által tárolt állapota (a struct újralétrehozásakor is megmarad), mindig `private`, és ez az „igazság forrása” (source of truth). A `@Binding` kétirányú hivatkozás egy máshol tárolt állapotra; a `$` előtaggal képezhető (`$teendo.cim`), így a gyerek nézet módosíthatja a szülő adatát anélkül, hogy birtokolná. Buktató: `@State`-et kívülről inicializálni csak a kezdőértékre hat, utána a SwiftUI a saját tárolt értékét használja.

```swift
import SwiftUI

struct Teendo: Identifiable {
    let id = UUID()
    var cim: String
    var kesz = false
}

struct TeendoLista: View {
    // @State: a nézet SAJÁT állapota (source of truth).
    @State private var teendok = [Teendo(cim: "Bevásárlás"), Teendo(cim: "Edzés")]
    @State private var ujCim = ""
    @State private var csakNyitott = false

    var body: some View {
        NavigationStack {
            List {
                Toggle("Csak a nyitottak", isOn: $csakNyitott)   // $ = Binding az állapotra
                // ForEach($tomb): minden elemhez Binding jön -> a sor közvetlenül módosíthat.
                ForEach($teendok) { $teendo in
                    if !csakNyitott || !teendo.kesz {
                        TeendoSor(teendo: $teendo)
                    }
                }
                .onDelete { teendok.remove(atOffsets: $0) }
            }
            .navigationTitle("Teendők (\(teendok.filter({ !$0.kesz }).count))")
            .toolbar {
                TextField("Új teendő", text: $ujCim)
                    .onSubmit(hozzaad)
            }
        }
    }

    private func hozzaad() {
        let cim = ujCim.trimmingCharacters(in: .whitespaces)
        guard !cim.isEmpty else { return }
        teendok.append(Teendo(cim: cim))
        ujCim = ""
    }
}

// Gyerek nézet: nem birtokolja az adatot, csak kétirányú hivatkozást kap.
struct TeendoSor: View {
    @Binding var teendo: Teendo

    var body: some View {
        HStack {
            Image(systemName: teendo.kesz ? "checkmark.circle.fill" : "circle")
                .foregroundStyle(teendo.kesz ? Color.green : Color.secondary)
                .onTapGesture { teendo.kesz.toggle() }   // a szülő @State-je változik
            TextField("Cím", text: $teendo.cim)          // Binding egy mezőre
                .strikethrough(teendo.kesz)
        }
    }
}

#Preview {
    TeendoLista()
}
```

## @Observable modellek (Observation keretrendszer)
<!-- q: Hogyan használjam az @Observable makrót és a @Bindable-t SwiftUI-ban? -->
<!-- tags: observable, observation, bindable, environment, swiftui, state management, ios 17 -->

Az iOS 17/macOS 14 óta elérhető `@Observable` makró egy osztály minden tárolt property-jét megfigyelhetővé teszi, és a nézet csak azokra iratkozik fel, amelyeket a `body` ténylegesen olvas — finomabb és gyorsabb, mint az `ObservableObject` + `@Published`, ahol bármely változás újrarajzol. A modell tulajdonosa `@State`-ben tartja, a környezetbe `.environment(modell)`-lel injektálható és `@Environment(Tipus.self)`-fel olvasható. Kétirányú kötéshez (`$modell.mezo`) a `@Bindable` kell. A nem megfigyelendő mezőket `@ObservationIgnored` jelöli.

```swift
import SwiftUI
import Observation

@Observable
final class KosarModell {
    var tetelek: [Tetel] = []
    var kuponKod = ""
    @ObservationIgnored var muveletSzam = 0   // nem okoz újrarajzolást

    var vegosszeg: Double {                   // számított: a függőségein át követett
        let alap = tetelek.reduce(0) { $0 + $1.ar * Double($1.darab) }
        return kuponKod == "TAVASZ10" ? alap * 0.9 : alap
    }

    func hozzaad(_ nev: String, ar: Double) {
        if let i = tetelek.firstIndex(where: { $0.nev == nev }) {
            tetelek[i].darab += 1
        } else {
            tetelek.append(Tetel(nev: nev, ar: ar))
        }
        muveletSzam += 1
    }
}

struct Tetel: Identifiable {
    var id: String { nev }
    let nev: String
    let ar: Double
    var darab = 1
}

@main
struct BoltApp: App {
    @State private var kosar = KosarModell()   // a modell tulajdonosa
    var body: some Scene {
        WindowGroup {
            KosarNezet()
                .environment(kosar)              // típus szerinti injektálás
        }
    }
}

struct KosarNezet: View {
    @Environment(KosarModell.self) private var kosar

    var body: some View {
        VStack {
            List(kosar.tetelek) { t in
                Text("\(t.nev) × \(t.darab)")
            }
            KuponMezo(kosar: kosar)
            Text("Végösszeg: \(kosar.vegosszeg, format: .currency(code: "HUF"))")
            Button("Billentyűzet") { kosar.hozzaad("Billentyűzet", ar: 12990) }
        }
    }
}

// @Bindable: Binding ($) egy @Observable objektum property-jeire.
struct KuponMezo: View {
    @Bindable var kosar: KosarModell
    var body: some View {
        TextField("Kuponkód", text: $kosar.kuponKod)
    }
}
```

## Codable: JSON kódolás és dekódolás
<!-- q: Hogyan használjam a Codable-t JSON feldolgozásra Swiftben (CodingKeys, saját init(from:))? -->
<!-- tags: codable, decodable, encodable, json, codingkeys, JSONDecoder, date decoding -->

A `Codable` (= `Encodable & Decodable`) megfelelést a fordító automatikusan szintetizálja, ha minden property Codable; a `CodingKeys` enum a JSON-kulcsneveket képezi le, az opcionális mezők hiánya nil-t ad. Eltérő szerkezetnél (beágyazott objektum kilapítása, alapértékek, hibatűrés) saját `init(from:)` írható konténerekkel (`container`, `nestedContainer`, `decodeIfPresent`). Buktató: a `JSONDecoder` alapból a `Date`-et 2001 óta eltelt másodpercként várja, ezért ISO-8601 dátumhoz `dateDecodingStrategy = .iso8601` kell. A `DecodingError` esetei (keyNotFound, typeMismatch) pontos hibahelyet adnak a `codingPath`-ban.

```swift
import Foundation

struct Felhasznalo: Codable, Equatable {
    let id: Int
    let teljesNev: String
    let email: String?
    let regisztralt: Date
    let szerepkor: Szerepkor

    enum Szerepkor: String, Codable { case admin, szerkeszto, olvaso }

    // A JSON-kulcsok eltérnek a property-nevektől.
    enum CodingKeys: String, CodingKey {
        case id, email
        case teljesNev = "full_name"
        case regisztralt = "created_at"
        case szerepkor = "role"
    }
}

// Saját dekódolás: beágyazott objektum kilapítása, alapértékek, hibatűrés.
struct Termek: Decodable {
    let sku: String
    let ar: Decimal
    let raktaron: Bool
    let cimkek: [String]

    enum Kulcsok: String, CodingKey { case sku, arazas, raktaron, cimkek }
    enum ArKulcsok: String, CodingKey { case brutto }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: Kulcsok.self)
        sku = try c.decode(String.self, forKey: .sku)
        let arazas = try c.nestedContainer(keyedBy: ArKulcsok.self, forKey: .arazas)
        ar = try arazas.decode(Decimal.self, forKey: .brutto)              // {"arazas":{"brutto":1990}}
        raktaron = try c.decodeIfPresent(Bool.self, forKey: .raktaron) ?? false
        cimkek = (try? c.decode([String].self, forKey: .cimkek)) ?? []    // hibás típus -> üres
    }
}

let json = Data("""
{"id": 7, "full_name": "Teszt Elek", "created_at": "2026-03-01T08:30:00Z", "role": "szerkeszto"}
""".utf8)

let dekoder = JSONDecoder()
dekoder.dateDecodingStrategy = .iso8601   // alapból: másodpercek 2001 óta!
do {
    let f = try dekoder.decode(Felhasznalo.self, from: json)
    print(f.teljesNev, f.szerepkor, f.email ?? "nincs email")

    let enkoder = JSONEncoder()
    enkoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    enkoder.dateEncodingStrategy = .iso8601
    let vissza = try dekoder.decode(Felhasznalo.self, from: try enkoder.encode(f))
    print("round-trip egyezik:", vissza == f)

    let t = try JSONDecoder().decode(Termek.self, from: Data(#"{"sku":"KB-1","arazas":{"brutto":1990}}"#.utf8))
    print(t.ar, t.raktaron, t.cimkek)
} catch let DecodingError.keyNotFound(kulcs, ctx) {
    print("hiányzó kulcs:", kulcs.stringValue, ctx.codingPath)
} catch {
    print("dekódolási hiba:", error)
}
```

## Result builderek (saját DSL)
<!-- q: Hogyan írjak saját result buildert (DSL-t) Swiftben, mint a SwiftUI ViewBuilder? -->
<!-- tags: result builder, resultBuilder, dsl, buildBlock, buildEither, viewbuilder -->

A `@resultBuilder` lehetővé teszi, hogy egy closure egymás utáni kifejezéseit a fordító statikus `build...` metódusok hívásaivá alakítsa — ez működteti a SwiftUI `@ViewBuilder`-t is. A `buildExpression` az egyes sorokat alakítja át, a `buildBlock` fűzi össze őket, a `buildOptional` az else nélküli `if`-et, a `buildEither` az `if/else`-t és `switch`-et, a `buildArray` a `for` ciklust kezeli. Ha egy szerkezethez nincs megfelelő `build` metódus, fordítási hibát kapsz („closure containing control flow statement cannot be used with result builder”). Deklaratív konfigurációkhoz, HTML/SQL-építéshez és tesztadat-DSL-ekhez hasznos.

```swift
// Mini HTML DSL — ugyanaz a mechanizmus, mint a SwiftUI @ViewBuilder mögött.
protocol HTMLElem {
    func render(_ behuzas: Int) -> String
}
typealias Elemek = [any HTMLElem]

struct Szoveg: HTMLElem {
    let s: String
    func render(_ b: Int) -> String { String(repeating: "  ", count: b) + s }
}

struct Tag: HTMLElem {
    let nev: String
    let gyerekek: Elemek

    init(_ nev: String, @HTMLBuilder _ tartalom: () -> Elemek) {
        self.nev = nev
        self.gyerekek = tartalom()
    }

    func render(_ b: Int) -> String {
        let pad = String(repeating: "  ", count: b)
        let belso = gyerekek.map { $0.render(b + 1) }.joined(separator: "\n")
        return "\(pad)<\(nev)>\n\(belso)\n\(pad)</\(nev)>"
    }
}

@resultBuilder
enum HTMLBuilder {
    // Minden sort tömbbé alakítunk, így egységesen fűzhetők össze.
    static func buildExpression(_ e: any HTMLElem) -> Elemek { [e] }
    static func buildExpression(_ s: String) -> Elemek { [Szoveg(s: s)] }   // nyers string is mehet
    static func buildBlock(_ reszek: Elemek...) -> Elemek { reszek.flatMap { $0 } }
    static func buildOptional(_ r: Elemek?) -> Elemek { r ?? [] }            // if else nélkül
    static func buildEither(first r: Elemek) -> Elemek { r }                 // if ág
    static func buildEither(second r: Elemek) -> Elemek { r }                // else ág
    static func buildArray(_ r: [Elemek]) -> Elemek { r.flatMap { $0 } }     // for-in
}

let bejelentkezve = true
let nyelvek = ["Go", "Swift", "Dart"]

let oldal = Tag("div") {
    Tag("h1") { "Nyelvek" }
    if bejelentkezve {
        Tag("p") { "Üdv újra!" }
    } else {
        Tag("a") { "Bejelentkezés" }
    }
    Tag("ul") {
        for nyelv in nyelvek {
            Tag("li") { nyelv }
        }
    }
}
print(oldal.render(0))
```

## Property wrapperek
<!-- q: Hogyan írjak saját property wrappert Swiftben (wrappedValue, projectedValue)? -->
<!-- tags: property wrapper, propertyWrapper, wrappedValue, projectedValue, userdefaults, validation -->

A `@propertyWrapper` típus egy property tárolási és hozzáférési logikáját csomagolja be újrahasznosíthatóan: a `wrappedValue` get/set-je fut minden olvasáskor és íráskor. Az `init(wrappedValue:)` teszi lehetővé a `@Wrapper var x = érték` szintaxist, további paraméterek az attribútumban adhatók át (`@Korlatozott(0...100)`). A `projectedValue` a `$x` szintaxissal érhető el (SwiftUI-ban így lesz a `@State`-ből Binding). Buktató: a wrapper struct, ezért a setter mutating — `let` példányon a wrapped property nem írható, és a wrapperek nem ingyenesek, ha drága logikát rejtenek egy egyszerűnek látszó értékadás mögé.

```swift
import Foundation

// Érték korlátozása tartományra; minden írásnál lefut.
@propertyWrapper
struct Korlatozott<Ertek: Comparable> {
    private var ertek: Ertek
    private let tartomany: ClosedRange<Ertek>

    init(wrappedValue: Ertek, _ tartomany: ClosedRange<Ertek>) {
        self.tartomany = tartomany
        self.ertek = min(max(wrappedValue, tartomany.lowerBound), tartomany.upperBound)
    }

    var wrappedValue: Ertek {
        get { ertek }
        set { ertek = min(max(newValue, tartomany.lowerBound), tartomany.upperBound) }
    }

    var projectedValue: ClosedRange<Ertek> { tartomany }   // $nev
}

// UserDefaults-hoz kötött, típusos beállítás alapértékkel.
@propertyWrapper
struct Beallitas<T> {
    let kulcs: String
    let alap: T
    var tarolo: UserDefaults = .standard

    var wrappedValue: T {
        get { tarolo.object(forKey: kulcs) as? T ?? alap }
        set { tarolo.set(newValue, forKey: kulcs) }
    }
}

// Szöveg automatikus normalizálása.
@propertyWrapper
struct Normalizalt {
    private var s = ""
    var wrappedValue: String {
        get { s }
        set { s = newValue.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() }
    }
    init(wrappedValue: String) { self.wrappedValue = wrappedValue }
}

struct Lejatszo {
    @Korlatozott(0...100) var hangero: Int = 50
    @Normalizalt var email: String = "  Teszt@Example.COM "
}

struct AppBeallitasok {
    @Beallitas(kulcs: "sotet_mod", alap: false) var sotetMod: Bool
}

var l = Lejatszo()
l.hangero = 150
print(l.hangero, l.$hangero, l.email)   // 100 0...100 teszt@example.com

var app = AppBeallitasok()
app.sotetMod = true
print(app.sotetMod)
```

## Enumok asszociált értékekkel és mintaillesztés
<!-- q: Hogyan használjam az asszociált értékes enumokat és a mintaillesztést Swiftben? -->
<!-- tags: enum, associated values, pattern matching, switch, if case, indirect enum, state machine -->

A Swift enum esetei asszociált értékeket hordozhatnak, így egy állapot pontosan azokat az adatokat tartalmazza, amelyek abban az állapotban értelmesek — ideális állapotgépekhez és hibatípusokhoz. A `switch` kimerítő: új eset hozzáadásakor a fordító minden kezeletlen helyet jelez, ezért kerüld a felesleges `default`-ot. A minták kötnek (`let`), szűrnek (`where`), tuple-ökre is illeszthetők, egyetlen eset kiemelésére pedig az `if case` való. Az `indirect enum` rekurzív adatszerkezetet (pl. kifejezésfát) tesz lehetővé.

```swift
// Állapotgép egy letöltéshez.
enum LetoltesAllapot: Equatable {
    case tetlen
    case folyamatban(szazalek: Double)
    case kesz(fajl: String, meret: Int)
    case hiba(kod: Int, uzenet: String)
}

func leiras(_ a: LetoltesAllapot) -> String {
    switch a {   // kimerítő: új eset -> fordítási hiba
    case .tetlen:
        return "Várakozik"
    case .folyamatban(let p) where p >= 0.99:
        return "Majdnem kész"
    case .folyamatban(let p):
        return "Letöltés: \(Int(p * 100))%"
    case let .kesz(fajl, meret) where meret > 1_000_000:
        return "\(fajl) (\(meret / 1_000_000) MB)"
    case let .kesz(fajl, _):
        return fajl
    case .hiba(let kod, _) where (500...599).contains(kod):
        return "Szerverhiba, újrapróbálkozás..."
    case .hiba(_, let uzenet):
        return "Hiba: \(uzenet)"
    }
}

// Állapotátmenetek tuple-mintával: (jelenlegi, esemény).
enum Esemeny { case indit, halad(Double), vege(String, Int), elbukik(Int) }

func atmenet(_ a: LetoltesAllapot, _ e: Esemeny) -> LetoltesAllapot {
    switch (a, e) {
    case (.tetlen, .indit), (.hiba, .indit):
        return .folyamatban(szazalek: 0)
    case (.folyamatban, .halad(let p)):
        return .folyamatban(szazalek: min(p, 1))
    case (.folyamatban, .vege(let f, let m)):
        return .kesz(fajl: f, meret: m)
    case (.folyamatban, .elbukik(let kod)):
        return .hiba(kod: kod, uzenet: "HTTP \(kod)")
    default:
        return a   // érvénytelen átmenet: marad az állapot
    }
}

// indirect enum: rekurzív kifejezésfa.
indirect enum Kif {
    case szam(Double)
    case osszeg(Kif, Kif)
    case szorzat(Kif, Kif)

    var ertek: Double {
        switch self {   // Swift 5.9+: switch kifejezésként
        case .szam(let x): x
        case let .osszeg(a, b): a.ertek + b.ertek
        case let .szorzat(a, b): a.ertek * b.ertek
        }
    }
}

var allapot = LetoltesAllapot.tetlen
for e: Esemeny in [.indit, .halad(0.5), .vege("adat.zip", 4_200_000)] {
    allapot = atmenet(allapot, e)
    print(leiras(allapot))
}
if case .kesz(let fajl, _) = allapot { print("Megnyitás:", fajl) }   // egy eset kiemelése
print(Kif.osszeg(.szam(2), .szorzat(.szam(3), .szam(4))).ertek)     // 14.0
```
