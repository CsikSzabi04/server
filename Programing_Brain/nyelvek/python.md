# Python
<!-- tech: python -->
<!-- aliases: py, python3, cpython, pypy -->

A Python dinamikusan, de erősen típusos, bytecode-ra fordított és interpretált általános célú nyelv; a referencia-implementáció (CPython) referenciaszámlálással és ciklikus szemétgyűjtővel kezeli a memóriát. Többparadigmás: az objektumorientált, procedurális és funkcionális stílus egyaránt idiomatikus, minden érték objektum, a változók csak nevek. Erőssége a gyors fejlesztés, az olvashatóság és a hatalmas ökoszisztéma (adatfeldolgozás, ML, web, automatizálás); gyengéje a nyers CPU-teljesítmény és a GIL miatt korlátozott szálas párhuzamosság (3.13-tól van kísérleti free-threaded build). Akkor jó választás, ha a fejlesztési idő fontosabb a futási időnél, vagy a nehéz számítást natív könyvtárak (NumPy, PyTorch) végzik; alacsony késleltetésű, mobil vagy böngészős célra kevésbé.

## Objektummodell: referenciák, mutabilitás és a mutable default csapda
<!-- q: Miért változik meg a lista, ha egy másik változón keresztül módosítom, és miért veszélyes a lista default argumentum? -->
<!-- tags: data model, mutability, identity, references, copy, default arguments -->

Pythonban az értékadás soha nem másol: a név csak egy referencia az objektumra, ezért két név ugyanarra a listára mutathat (`is` = identitás, `==` = egyenlőség). A default argumentumok egyszer, a `def` végrehajtásakor értékelődnek ki, így egy `[]` default minden hívásnál ugyanaz az objektum. A `copy.copy` csak a külső konténert másolja (a belső elemek közösek maradnak), a `deepcopy` rekurzívan mindent. Buktató a `[[0]*3]*3` is: ugyanarra a belső listára mutató referenciát ismétel.

```python
import copy


def hozzaad_rossz(elem, lista=[]):
    # HIBA: a [] egyszer jön létre (def-kor), minden hívás ugyanazt módosítja
    lista.append(elem)
    return lista


def hozzaad_jo(elem, lista=None):
    # Idiomatikus: None "sentinel" és hívásonként új lista
    if lista is None:
        lista = []
    lista.append(elem)
    return lista


def main() -> None:
    hozzaad_rossz(1)
    print(hozzaad_rossz(2), hozzaad_rossz.__defaults__)  # [1, 2] ([1, 2],)
    print(hozzaad_jo(1), hozzaad_jo(2))                   # [1] [2]

    a = [1, 2, 3]
    b = a              # nem másolat, ugyanaz az objektum
    b.append(4)
    print(a is b, a)   # True [1, 2, 3, 4]
    print([1, 2] == [1, 2], [1, 2] is [1, 2])  # True False

    racs_rossz = [[0] * 3] * 3          # 3 referencia UGYANARRA a belső listára
    racs_rossz[0][0] = 9
    racs_jo = [[0] * 3 for _ in range(3)]
    racs_jo[0][0] = 9
    print(racs_rossz[1][0], racs_jo[1][0])  # 9 0

    eredeti = {"nev": "konfig", "portok": [80, 443]}
    sekely, mely = copy.copy(eredeti), copy.deepcopy(eredeti)
    eredeti["portok"].append(8080)
    print(sekely["portok"], mely["portok"])  # [80, 443, 8080] [80, 443]

    # Az immutable tuple tartalmazhat mutable elemet -> nem hash-elhető
    t = (1, [2, 3])
    t[1].append(4)
    try:
        hash(t)
    except TypeError as exc:
        print("nem hash-elhető:", exc)

    # += mutable-n helyben módosít (__iadd__), immutable-n új objektumot köt a névhez
    lst, tup = [1], (1,)
    lst_id, tup_id = id(lst), id(tup)
    lst += [2]
    tup += (2,)
    print(id(lst) == lst_id, id(tup) == tup_id)  # True False


if __name__ == "__main__":
    main()
```

## Scope, closure-ök és a LEGB szabály
<!-- q: Hogyan működik a változók láthatósága és a closure Pythonban, mire való a nonlocal? -->
<!-- tags: scope, closure, legb, nonlocal, late binding -->

A névfeloldás sorrendje LEGB: Local → Enclosing (külső függvény) → Global (modul) → Builtins. A belső függvény "bezárja" a külső változókat cell objektumokba (`__closure__`), ezért azok a külső függvény visszatérése után is élnek — így készül állapotos függvény osztály nélkül. Ha a belső függvény értéket ad egy külső névnek, a fordító lokálisnak tekinti, ezért kell a `nonlocal` (modulszintre a `global`). Klasszikus csapda a late binding: a lambda a változó nevét zárja be, nem az aktuális értékét.

```python
from collections.abc import Callable


def szamlalo_gyar(kezdo: int = 0) -> tuple[Callable[[], int], Callable[[], None]]:
    ertek = kezdo  # Enclosing scope: a belső függvények cellában osztoznak rajta

    def novel() -> int:
        nonlocal ertek  # nélküle az `ertek += 1` UnboundLocalError-t dobna
        ertek += 1
        return ertek

    def nullaz() -> None:
        nonlocal ertek
        ertek = 0

    return novel, nullaz


def memoizal(fn: Callable[[int], int]) -> Callable[[int], int]:
    cache: dict[int, int] = {}  # privát állapot, kívülről nem érhető el

    def belso(n: int) -> int:
        if n not in cache:      # olvasás + mutálás: ehhez NEM kell nonlocal
            cache[n] = fn(n)
        return cache[n]

    return belso


def unbound_csapda() -> None:
    x = 10

    def belso() -> None:
        try:
            print(x)  # x lokális, mert lent értéket kap -> még nincs kötve
        except UnboundLocalError as e:
            print("UnboundLocalError:", e)
        x = 5  # noqa: F841

    belso()


def main() -> None:
    novel, nullaz = szamlalo_gyar(5)
    novel()
    print(novel(), novel.__code__.co_freevars, novel.__closure__[0].cell_contents)  # 7 ('ertek',) 7
    nullaz()
    print(novel())  # 1

    negyzet = memoizal(lambda n: n * n)
    print(negyzet(12), negyzet(12))

    rossz = [lambda: i for i in range(3)]       # mind ugyanazt az i-t látja
    jo = [lambda i=i: i for i in range(3)]      # default argumentum: definiáláskor köt
    print([f() for f in rossz], [f() for f in jo])  # [2, 2, 2] [0, 1, 2]
    unbound_csapda()


if __name__ == "__main__":
    main()
```

## Dekorátorok: wraps, paraméteres dekorátor, retry és cache
<!-- q: Hogyan írjak saját dekorátort Pythonban, akár paraméterekkel? -->
<!-- tags: decorators, functools, wraps, paramspec, retry, lru_cache -->

A dekorátor egy függvény, amely függvényt kap és (általában becsomagolt) függvényt ad vissza; a `@dek` szintaxis a `f = dek(f)` rövidítése, több dekorátor alulról felfelé alkalmazódik. A `functools.wraps` átmásolja a nevet, docstringet és `__wrapped__`-et, különben a naplók, a debugger és a pytest is rossz nevet lát. Paraméteres dekorátorhoz még egy réteg (dekorátorgyár) kell. A `ParamSpec` megőrzi a becsomagolt függvény szignatúráját a típusellenőrző számára.

```python
import functools
import logging
import random
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def idomeres(fn: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(fn)  # megőrzi __name__, __doc__, __wrapped__
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:  # hiba esetén is mérünk
            log.info("%s: %.2f ms", fn.__qualname__, (time.perf_counter() - start) * 1000)
    return wrapper


def ujraprobal(*, kiserlet: int = 3, alap: float = 0.05,
               kivetelek: tuple[type[Exception], ...] = (ConnectionError,)):
    # Dekorátorgyár: a paramétereket egy külső függvény zárja be
    def dekorator(fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for n in range(1, kiserlet + 1):
                try:
                    return fn(*args, **kwargs)
                except kivetelek as exc:
                    if n == kiserlet:
                        raise  # eredeti traceback-kel dobjuk tovább
                    # exponenciális backoff + jitter: a kliensek ne egyszerre próbálkozzanak
                    varj = alap * 2 ** (n - 1) * random.uniform(0.5, 1.5)
                    log.warning("%s hiba: %s, újra %.3fs múlva", fn.__name__, exc, varj)
                    time.sleep(varj)
            raise AssertionError("elérhetetlen")
        return wrapper
    return dekorator


_hibak = iter([True, True, False])  # az első két hívás "elhasal"


@ujraprobal(kiserlet=3)
@idomeres  # alulról felfelé: ujraprobal(idomeres(lekerdez))
def lekerdez(azon: int) -> dict[str, int]:
    if next(_hibak):
        raise ConnectionError("átmeneti hiba (szimulált)")
    return {"id": azon, "ertek": azon * 2}


@functools.lru_cache(maxsize=None)  # beépített memoizálás (az argumentumok legyenek hash-elhetők)
def fib(n: int) -> int:
    return n if n < 2 else fib(n - 1) + fib(n - 2)


if __name__ == "__main__":
    print(lekerdez(21), lekerdez.__name__)
    print(fib(150), fib.cache_info())
```

## Iterátorok, generátorok és comprehensionök
<!-- q: Hogyan működnek a generátorok és az iterátor protokoll, mikor használjak yield-et? -->
<!-- tags: iterators, generators, yield from, send, comprehension, lazy evaluation, walrus -->

Az iterátor protokoll két metódus: `__iter__` (iterátort ad) és `__next__` (következő elem vagy `StopIteration`). A `yield`-et tartalmazó függvény generátort ad vissza, amely lustán, egyesével állítja elő az elemeket — így több GB-os fájl is konstans memóriával dolgozható fel láncolt lépésekben. A `yield from` algenerátornak delegál, a `send()` értéket küld a generátorba (korutin-stílus). Buktató: a generátor egyszer használható, második bejárásra üres.

```python
import itertools
from collections.abc import Generator, Iterable, Iterator


def sorok(forras: Iterable[str]) -> Iterator[str]:
    for sor in forras:
        yield sor.rstrip("\n")


def hibak(sorok_: Iterable[str]) -> Iterator[dict[str, str]]:
    # Generátor-kifejezés + lusta feldolgozás: egyszerre csak egy sor van memóriában
    for s in (s for s in sorok_ if " ERROR " in s):
        datum, ido, szint, *uzenet = s.split()  # kiterjesztett kicsomagolás
        yield {"ido": f"{datum} {ido}", "uzenet": " ".join(uzenet)}


def lapit(fa: list) -> Iterator[object]:
    for elem in fa:
        if isinstance(elem, list):
            yield from lapit(elem)  # delegálás rekurzív algenerátornak
        else:
            yield elem


def futo_atlag() -> Generator[float, float | None, str]:
    osszeg, db, atlag = 0.0, 0, 0.0
    while True:
        ertek = yield atlag        # a send() értéke ide érkezik
        if ertek is None:
            return f"{db} érték"   # a return értéke StopIteration.value lesz
        osszeg += ertek
        db += 1
        atlag = osszeg / db


def main() -> None:
    naplo = ["2024-05-01 10:00:01 INFO indul\n", "2024-05-01 10:00:02 ERROR db timeout\n"]
    print(list(hibak(sorok(naplo))))
    print(list(lapit([1, [2, [3, [4]], 5]])))  # [1, 2, 3, 4, 5]

    gen = futo_atlag()
    next(gen)  # "priming": el kell jutni az első yield-ig
    print([gen.send(x) for x in (10, 20, 60)])  # [10.0, 15.0, 30.0]
    try:
        gen.send(None)
    except StopIteration as stop:
        print("vége:", stop.value)

    # Comprehension + walrus: a drága hívás egyszer fut elemenként
    nyers = ["alma:3", "korte:x", "szilva:5"]
    keszlet = {p[0]: int(p[1]) for s in nyers if (p := s.split(":"))[1].isdigit()}
    print(keszlet)  # {'alma': 3, 'szilva': 5}

    negyzetek = (n * n for n in itertools.count(1))  # végtelen, de lusta
    print(list(itertools.islice(negyzetek, 5)))
    g = (x for x in range(3))
    print(sum(g), sum(g))  # 3 0 – a generátor kimerült


if __name__ == "__main__":
    main()
```

## Context managerek: with, contextlib és ExitStack
<!-- q: Hogyan írjak saját context managert, és mire jó az ExitStack? -->
<!-- tags: context manager, with, contextlib, exitstack, resource management, atomic write -->

A `with` blokk garantálja, hogy a `__exit__` lefusson akkor is, ha kivétel vagy `return` történik — ez a fájlok, zárak, tranzakciók és kapcsolatok helyes lezárásának alapja. A `@contextlib.contextmanager` egy generátorból készít context managert: a `yield` előtti rész a belépés, utána a kilépés, és a blokkban keletkezett kivétel a `yield` sorban dobódik. Ha `__exit__` `True`-t ad, elnyeli a kivételt (ritkán jó ötlet). Az `ExitStack` dinamikus számú erőforrást kezel és fordított (LIFO) sorrendben zárja le.

```python
import contextlib
import os
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import TextIO


@contextlib.contextmanager
def atomikus_iras(cel: Path) -> Iterator[TextIO]:
    """Temp fájlba ír, és csak siker esetén cseréli le a célt (os.replace atomikus)."""
    fd, tmp = tempfile.mkstemp(dir=cel.parent, prefix=f".{cel.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yield f               # itt fut a with-blokk törzse
            f.flush()
            os.fsync(f.fileno())  # tényleg lemezre kerüljön átnevezés előtt
        os.replace(tmp, cel)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)        # félkész temp törlése, a régi cél érintetlen
        raise


class Tranzakcio:
    def __init__(self, naplo: list[str]) -> None:
        self.naplo = naplo

    def __enter__(self) -> "Tranzakcio":
        self.naplo.append("BEGIN")
        return self  # ez lesz az `as` utáni név

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.naplo.append("ROLLBACK" if exc_type else "COMMIT")
        return False  # a kivétel továbbterjed


def main() -> None:
    with tempfile.TemporaryDirectory() as mappa:  # nem nyúlunk valódi fájlokhoz
        cel = Path(mappa) / "beallitas.json"
        with atomikus_iras(cel) as f:
            f.write('{"mod": "eles"}')
        try:
            with atomikus_iras(cel) as f:
                f.write('{"mod": ')
                raise ValueError("szerializálási hiba")
        except ValueError:
            pass
        print(cel.read_text(encoding="utf-8"))  # még mindig a régi, teljes tartalom

        naplo: list[str] = []
        with contextlib.suppress(KeyError), Tranzakcio(naplo):
            {}["nincs"]
        print(naplo)  # ['BEGIN', 'ROLLBACK']

        with contextlib.ExitStack() as stack:
            fajlok = [stack.enter_context(open(Path(mappa) / f"r{i}.txt", "w")) for i in range(3)]
            stack.callback(print, "minden fájl lezárva")  # tetszőleges takarítás
            for i, fh in enumerate(fajlok):
                fh.write(str(i))


if __name__ == "__main__":
    main()
```

## dataclass, Enum és strukturális mintaillesztés (match)
<!-- q: Hogyan modellezzek adatokat dataclass-szal és Enummal, és hogyan működik a match utasítás? -->
<!-- tags: dataclass, enum, strenum, slots, match, pattern matching -->

A `@dataclass` legenerálja az `__init__`, `__repr__`, `__eq__` (opcionálisan rendezési és hash) metódusokat; `frozen=True` immutable, `slots=True` kevesebb memóriát és gyorsabb attribútum-elérést ad. Mutable defaulthoz `field(default_factory=list)` kell, validációra a `__post_init__` való. Az `Enum`/`StrEnum` véges állapothalmazt ír le varázsstringek helyett. A `match` nem switch: szerkezetet illeszt (típus, attribútumok, kulcsok, hossz), guarddal (`if`) és változókötéssel — dataclassokkal különösen jól működik, mert azok `__match_args__`-ot is generálnak.

```python
from dataclasses import dataclass, field, replace
from decimal import Decimal
from enum import StrEnum, auto


class Statusz(StrEnum):
    UJ = auto()        # 'uj' – str-ként JSON-ba közvetlenül mehet
    FIZETVE = auto()
    TOROLVE = auto()


@dataclass(frozen=True, slots=True, order=True)
class Tetel:
    cikkszam: str
    ar: Decimal        # pénzhez Decimal, nem float
    db: int = 1

    def __post_init__(self) -> None:
        if self.db <= 0:
            raise ValueError("a darabszám pozitív kell legyen")


@dataclass(slots=True)
class Rendeles:
    azon: int
    tetelek: list[Tetel] = field(default_factory=list)  # SOHA ne `= []`
    statusz: Statusz = Statusz.UJ

    @property
    def osszeg(self) -> Decimal:
        return sum((t.ar * t.db for t in self.tetelek), start=Decimal(0))


@dataclass(frozen=True)
class Fizetes:
    rendeles_azon: int
    osszeg: Decimal


@dataclass(frozen=True)
class Torles:
    rendeles_azon: int
    ok: str = ""


def kezel(esemeny: object, rendeles: Rendeles) -> str:
    match esemeny:
        case Fizetes(osszeg=o) if rendeles.statusz is Statusz.TOROLVE:
            return f"törölt rendelésre érkezett {o} Ft -> visszautalás"
        case Fizetes(osszeg=o) if o >= rendeles.osszeg:
            rendeles.statusz = Statusz.FIZETVE
            return "fizetve"
        case Fizetes(osszeg=o):
            return f"részfizetés: hiányzik {rendeles.osszeg - o} Ft"
        case Torles(ok="") | Torles(ok=None):
            return "törléshez indoklás kell"
        case Torles(ok=ok):
            rendeles.statusz = Statusz.TOROLVE
            return f"törölve: {ok}"
        case {"tipus": "megjegyzes", "szoveg": str(szoveg)}:  # dict minta
            return f"megjegyzés: {szoveg}"
        case _:
            return "ismeretlen esemény"


if __name__ == "__main__":
    r = Rendeles(1, [Tetel("B-7", Decimal("450"), 2), Tetel("A-1", Decimal("1990"))])
    print(sorted(r.tetelek)[0].cikkszam, r.osszeg)  # order=True -> rendezhető
    for e in (Fizetes(1, Decimal(1000)), Torles(1), {"tipus": "megjegyzes", "szoveg": "sürgős"},
              Fizetes(1, Decimal(2890)), 42):
        print(kezel(e, r))
    print(replace(r.tetelek[0], db=5), r.statusz == "fizetve")  # frozen: replace() új példányt ad
```

## Típusannotációk és generikusok (PEP 695, Protocol, TypedDict)
<!-- q: Hogyan írjak generikus, típusbiztos kódot Pythonban type hintekkel? -->
<!-- tags: typing, generics, typevar, protocol, typeddict, overload, mypy, pep 695 -->

A type hintek futáskor nem kényszerítenek semmit; a mypy/pyright statikusan ellenőrzi őket, és az IDE-támogatás is ebből él. A 3.12-es PEP 695 szintaxissal a generikus osztály `class Verem[T]:`, a függvény `def f[T](x: T) -> T`, a típusalias `type JSON = ...` (rekurzív is lehet, lustán értékelődik). A `Protocol` strukturális (duck) típus: bárki megfelel, akinek megvannak a metódusai, öröklés nélkül. A `TypedDict` JSON-szerű dictet, az `@overload` bemenettől függő visszatérési típust ír le.

```python
from collections.abc import Callable, Iterable, Iterator
from typing import Literal, NotRequired, Protocol, Self, TypedDict, overload

type JSON = dict[str, JSON] | list[JSON] | str | int | float | bool | None


class Verem[T]:
    def __init__(self) -> None:
        self._elemek: list[T] = []

    def push(self, elem: T) -> Self:  # Self: alosztályban is a pontos típust adja
        self._elemek.append(elem)
        return self

    def pop(self) -> T:
        if not self._elemek:
            raise IndexError("üres verem")
        return self._elemek.pop()

    def __iter__(self) -> Iterator[T]:
        return reversed(self._elemek)


class Rendezheto(Protocol):
    def __lt__(self, other: Self, /) -> bool: ...


def legkisebb[T: Rendezheto](elemek: Iterable[T]) -> T:
    # Felső korlát (bound): T csak összehasonlítható típus lehet
    it = iter(elemek)
    try:
        legjobb = next(it)
    except StopIteration:
        raise ValueError("üres bemenet") from None
    for e in it:
        if e < legjobb:
            legjobb = e
    return legjobb


def csoportosit[K, V](elemek: Iterable[V], kulcs: Callable[[V], K]) -> dict[K, list[V]]:
    eredmeny: dict[K, list[V]] = {}
    for e in elemek:
        eredmeny.setdefault(kulcs(e), []).append(e)
    return eredmeny


class Felhasznalo(TypedDict):
    id: int
    szerep: Literal["admin", "user"]
    email: NotRequired[str]


@overload
def beolvas(nyers: str, *, szamkent: Literal[True]) -> int: ...
@overload
def beolvas(nyers: str, *, szamkent: Literal[False] = ...) -> str: ...
def beolvas(nyers: str, *, szamkent: bool = False) -> int | str:
    return int(nyers) if szamkent else nyers.strip()  # futáskor csak ez az egy létezik


if __name__ == "__main__":
    print(list(Verem[int]().push(1).push(2)), legkisebb(["körte", "alma"]))
    print(csoportosit(["alma", "avokádó", "banán"], kulcs=lambda s: s[0]))
    u: Felhasznalo = {"id": 1, "szerep": "admin"}
    adat: JSON = {"lista": [1, {"x": None}]}
    print(u, adat, beolvas("41", szamkent=True) + 1)
```

## Dunder metódusok és descriptorok: az adatmodell protokolljai
<!-- q: Hogyan definiáljak operátorokat, egyenlőséget és validált attribútumokat saját osztályon? -->
<!-- tags: dunder, operator overloading, hash, eq, descriptor, property, set_name, cached_property -->

A `__add__`, `__eq__`, `__len__`, `__getitem__` stb. metódusokkal az osztály beépített típusként viselkedik; ha egy operátor nem támogatja a másik operandust, `NotImplemented`-et kell visszaadni (nem kivételt), így Python megpróbálja a tükrözött `__radd__`-ot. Ha `__eq__`-t definiálsz, a `__hash__` `None` lesz, hacsak meg nem adod — és csak immutable objektum legyen hash-elhető. A descriptor (`__get__`/`__set__`/`__set_name__`) az attribútum-elérést szabja testre: a `property`, a metódusok kötése és a `cached_property` is így működik. A data descriptor (van `__set__`) elsőbbséget élvez a példány `__dict__`-jével szemben, a non-data nem.

```python
import math
from collections.abc import Callable
from functools import cached_property


class Pozitiv:
    """Újrahasznosítható validált mező (data descriptor)."""

    def __set_name__(self, owner: type, name: str) -> None:
        self.nev, self.privat = name, f"_{name}"  # osztálylétrehozáskor hívódik

    def __get__(self, obj, objtype=None):
        return self if obj is None else getattr(obj, self.privat)

    def __set__(self, obj, ertek: float) -> None:
        if not isinstance(ertek, (int, float)) or ertek <= 0:
            raise ValueError(f"{self.nev}: pozitív szám kell, kapott: {ertek!r}")
        setattr(obj, self.privat, ertek)


class Vektor:
    x = Pozitiv()
    y = Pozitiv()

    def __init__(self, x: float, y: float) -> None:
        self.x, self.y = x, y  # már a descriptor __set__-jén megy át

    def __repr__(self) -> str:
        return f"Vektor({self.x!r}, {self.y!r})"

    def __add__(self, other: object) -> "Vektor":
        if not isinstance(other, Vektor):
            return NotImplemented
        return Vektor(self.x + other.x, self.y + other.y)

    def __mul__(self, k: object) -> "Vektor":
        return Vektor(self.x * k, self.y * k) if isinstance(k, (int, float)) else NotImplemented

    __rmul__ = __mul__  # 3 * v is működjön

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Vektor) and (self.x, self.y) == (other.x, other.y)

    def __hash__(self) -> int:  # a == b  =>  hash(a) == hash(b)
        return hash((self.x, self.y))

    def __abs__(self) -> float:
        return math.hypot(self.x, self.y)

    @cached_property  # non-data descriptor: első hívás után a példány __dict__-be kerül
    def normalt(self) -> tuple[float, float]:
        print("  számolás...")
        return (self.x / abs(self), self.y / abs(self))


if __name__ == "__main__":
    v = Vektor(3, 4)
    print(v + Vektor(1, 1), 2 * v, abs(v), {v, Vektor(3, 4)})
    print(v.normalt, v.normalt)  # másodszorra már nem számol
    for hibas in (lambda: Vektor(-1, 2), lambda: v + 1):
        try:
            hibas()
        except (ValueError, TypeError) as e:
            print(type(e).__name__, e)
    kotott: Callable[[], str] = Vektor.__repr__.__get__(v, Vektor)  # a metódus is descriptor
    print(kotott(), vars(v))
```

## Metaclassok, __init_subclass__ és plugin-regiszter
<!-- q: Mire jó a metaclass és az __init_subclass__ Pythonban, és mikor melyiket használjam? -->
<!-- tags: metaclass, init_subclass, registry, plugin, class creation, type -->

Az osztály is objektum, amelyet a metaclass (alapból a `type`) hoz létre; a metaclass `__new__`-jában az osztály létrehozása, a `__call__`-jában a példányosítás szabható testre. A legtöbb "osztályszintű" igényre (alosztályok regisztrálása, kötelező attribútumok ellenőrzése) az egyszerűbb `__init_subclass__` hook elég, amely minden alosztály definiálásakor lefut és kulcsszavas argumentumot is kaphat. Metaclass akkor kell, ha a névteret (`__prepare__`) vagy a példányosítást kell módosítani (ORM-ek, singleton). Buktató: két különböző metaclassú bázis keverése metaclass-konfliktust okoz.

```python
from typing import Any, ClassVar


class Exportalo:
    regiszter: ClassVar[dict[str, type["Exportalo"]]] = {}

    def __init_subclass__(cls, /, formatum: str, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if formatum in Exportalo.regiszter:
            raise TypeError(f"már regisztrált formátum: {formatum}")
        cls.formatum = formatum
        Exportalo.regiszter[formatum] = cls  # automatikus plugin-regisztráció

    @classmethod
    def gyart(cls, formatum: str) -> "Exportalo":
        try:
            return cls.regiszter[formatum]()
        except KeyError:
            raise ValueError(f"ismeretlen formátum: {formatum}") from None

    def exportal(self, adat: dict[str, Any]) -> str:
        raise NotImplementedError


class CsvExportalo(Exportalo, formatum="csv"):
    def exportal(self, adat: dict[str, Any]) -> str:
        return ",".join(adat) + "\n" + ",".join(map(str, adat.values()))


class IniExportalo(Exportalo, formatum="ini"):
    def exportal(self, adat: dict[str, Any]) -> str:
        return "\n".join(f"{k} = {v}" for k, v in adat.items())


class InterfeszMeta(type):
    def __new__(mcs, nev: str, bazisok: tuple[type, ...], nevter: dict[str, Any]):
        cls = super().__new__(mcs, nev, bazisok, nevter)
        if bazisok:  # az absztrakt gyökeret nem ellenőrizzük
            hiany = [m for m in getattr(cls, "KOTELEZO", ()) if not callable(getattr(cls, m, None))]
            if hiany:
                raise TypeError(f"{nev} nem implementálja: {', '.join(hiany)}")
        return cls


class Tarolo(metaclass=InterfeszMeta):
    KOTELEZO = ("olvas", "ir")


if __name__ == "__main__":
    for f in ("csv", "ini"):
        print(Exportalo.gyart(f).exportal({"host": "localhost", "port": 8080}))
    try:
        class Hibas(Tarolo):  # már a class utasítás végrehajtásakor hibát kapunk
            def olvas(self, kulcs: str) -> None: ...
    except TypeError as e:
        print("TypeError:", e)
    Pont = type("Pont", (), {"__slots__": ("x", "y")})  # dinamikus osztály = class utasítás
    print(Pont, type(Tarolo).__name__)
```

## Hibakezelés: kivétel-hierarchia, láncolás és ExceptionGroup
<!-- q: Hogyan kezeljem jól a kivételeket Pythonban, mire való a raise from és az except*? -->
<!-- tags: exceptions, error handling, raise from, exceptiongroup, except star, add_note, logging -->

Érdemes modulonként saját gyökér-kivételt definiálni, így a hívó egyetlen `except`-tel elkaphatja a csomag összes hibáját, de a konkrét alosztályokra is reagálhat. A `raise ÚjHiba(...) from exc` megőrzi az eredeti okot (`__cause__`), a `from None` elrejti. A `try` blokk legyen szűk: az `else` csak hiba nélkül fut, a `finally` mindig. 3.11-től az `ExceptionGroup` több független hibát hordoz egyszerre (pl. validáció, párhuzamos taskok), amelyeket `except*` válogat szét; az `add_note()` kontextust fűz a kivételhez.

```python
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("app")


class AppHiba(Exception):
    """A modul gyökér-kivétele."""


class KonfigHiba(AppHiba):
    pass


class ValidaciosHiba(AppHiba):
    def __init__(self, mezo: str, uzenet: str) -> None:
        super().__init__(f"{mezo}: {uzenet}")
        self.mezo = mezo


def konfig_betolt(nyers: str) -> dict:
    try:
        adat = json.loads(nyers)
    except json.JSONDecodeError as exc:
        raise KonfigHiba("hibás JSON konfiguráció") from exc  # az ok megmarad
    else:
        if "port" not in adat:
            raise KonfigHiba("hiányzó kulcs: port")
        return adat
    finally:
        log.debug("konfig betöltési kísérlet vége")  # mindig lefut


def validal(adat: dict) -> None:
    hibak: list[Exception] = []  # nem az első hibánál állunk meg: mindet jelentjük
    if adat.get("email", "").count("@") != 1:
        hibak.append(ValidaciosHiba("email", "érvénytelen formátum"))
    if adat.get("mennyiseg", 0) <= 0:
        hibak.append(ValidaciosHiba("mennyiseg", "pozitív szám kell"))
    if not isinstance(adat.get("tetelek"), list):
        hibak.append(TypeError("tetelek: lista kell"))
    if hibak:
        raise ExceptionGroup("érvénytelen rendelés", hibak)


if __name__ == "__main__":
    try:
        konfig_betolt("{port: 80}")
    except AppHiba as e:
        print(f"{e!r}, oka: {e.__cause__!r}")

    try:
        validal({"email": "rossz-cim", "mennyiseg": 0})
    except* ValidaciosHiba as csoport:  # csak az illeszkedő részcsoportot kapjuk
        print("validáció:", [str(h) for h in csoport.exceptions])
    except* TypeError as csoport:
        print("típushiba:", [str(h) for h in csoport.exceptions])

    try:
        int("x12")
    except ValueError as e:
        e.add_note("a 'mennyiseg' mező feldolgozása közben")
        log.exception("feldolgozási hiba")  # traceback + note a naplóban
```

## asyncio: korutinok, TaskGroup, timeout, Queue és cancellation
<!-- q: Hogyan írjak aszinkron, párhuzamosan futó I/O kódot asyncio-val Pythonban? -->
<!-- tags: asyncio, async, await, event loop, taskgroup, semaphore, queue, cancellation, timeout -->

Az `async def` korutint ad, amely egy felfüggeszthető objektum: az event loop `send()`-del lépteti a következő `await`-ig, ahol a vezérlés visszakerül a loophoz, így egy szálon több ezer I/O-művelet futhat átlapolva. A `TaskGroup` (3.11+) strukturált konkurenciát ad: ha egy task elhasal, a többit lemondja és `ExceptionGroup`-ot dob; a `Semaphore` korlátozza az egyidejű műveleteket, az `asyncio.timeout` időkorlátot ad. A lemondás `CancelledError`-ként érkezik a task belsejébe: takarítás után mindig dobd tovább. Blokkoló kódot (`time.sleep`, szinkron HTTP, nehéz CPU) soha ne hívj korutinból — az megállítja az egész loopot; használd az `asyncio.to_thread`-et.

```python
import asyncio
import random
import time


async def letolt(url: str, korlat: asyncio.Semaphore) -> int:
    async with korlat:  # legfeljebb N egyidejű "kérés"
        await asyncio.sleep(random.uniform(0.05, 0.2))  # hálózati I/O szimulálása
        if url.endswith("/hiba"):
            raise ConnectionError(url)
        return len(url)


async def fogyaszto(nev: str, sor: asyncio.Queue[int], ki: list[int]) -> None:
    try:
        while True:
            elem = await sor.get()
            try:
                await asyncio.sleep(0.01)
                ki.append(elem * elem)
            finally:
                sor.task_done()  # a join() ebből tudja, mikor kész minden elem
    except asyncio.CancelledError:
        print(f"{nev} leállítva")
        raise  # a lemondást SOHA ne nyeld el


async def main() -> None:
    korlat = asyncio.Semaphore(3)
    t0 = time.perf_counter()
    async with asyncio.TaskGroup() as tg:
        taskok = [tg.create_task(letolt(f"https://pelda.invalid/{i}", korlat)) for i in range(9)]
    print(f"{len(taskok)} kérés {time.perf_counter() - t0:.2f}s alatt")

    eredm = await asyncio.gather(letolt("x/ok", korlat), letolt("x/hiba", korlat),
                                 return_exceptions=True)  # hiba = eredmény, nem szakít meg
    print(eredm)

    try:
        async with asyncio.timeout(0.1):
            await asyncio.sleep(5)
    except TimeoutError:
        print("időtúllépés: a belső await CancelledError-t kapott")

    sor: asyncio.Queue[int] = asyncio.Queue(maxsize=5)  # maxsize = backpressure
    ki: list[int] = []
    workerek = [asyncio.create_task(fogyaszto(f"W{i}", sor, ki)) for i in range(3)]
    for i in range(20):
        await sor.put(i)  # tele sornál vár
    await sor.join()
    for w in workerek:
        w.cancel()
    await asyncio.gather(*workerek, return_exceptions=True)
    print("összeg:", sum(ki), await asyncio.to_thread(sum, range(10**6)))  # blokkoló -> szál


if __name__ == "__main__":
    asyncio.run(main())
```

## Szálak, a GIL és többprocesszes párhuzamosítás
<!-- q: Mikor használjak szálakat és mikor folyamatokat Pythonban a GIL miatt? -->
<!-- tags: threading, gil, multiprocessing, concurrent.futures, lock, race condition, processpool -->

A CPython GIL-je egyszerre csak egy szálnak engedi Python bytecode futtatását, de I/O-várakozás (és sok C-kiterjesztés) alatt felszabadul: I/O-kötött munkára a `ThreadPoolExecutor` jó, CPU-kötöttre a `ProcessPoolExecutor`, ahol minden folyamatnak saját interpretere van. A GIL nem véd a versenyhelyzettől: az olvasás–módosítás–írás nem atomikus, ezért `Lock` kell. Folyamatoknál az argumentumok és eredmények pickle-lel utaznak (top-level függvény kell), Windows/macOS `spawn` módban pedig kötelező az `if __name__ == "__main__":` védelem. 3.13-tól a free-threaded (`python3.13t`) build GIL nélkül fut, de a könyvtárak támogatása még változó.

```python
import math
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed


def io_feladat(i: int) -> int:
    time.sleep(0.2)  # I/O-várakozás: közben a GIL szabad
    return i


class Szamla:
    def __init__(self) -> None:
        self.egyenleg = 0
        self._zar = threading.Lock()

    def befizet(self, osszeg: int, zarral: bool) -> None:
        if zarral:
            with self._zar:  # kritikus szakasz
                self._novel(osszeg)
        else:
            self._novel(osszeg)

    def _novel(self, osszeg: int) -> None:
        aktualis = self.egyenleg
        time.sleep(0)  # szálváltást provokál az olvasás és írás között
        self.egyenleg = aktualis + osszeg


def primek(intervallum: tuple[int, int]) -> int:  # top-level -> pickle-elhető
    tol, ig = intervallum
    return sum(1 for n in range(max(tol, 2), ig)
               if all(n % d for d in range(2, math.isqrt(n) + 1)))


def main() -> None:
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=10) as pool:
        jovok = [pool.submit(io_feladat, i) for i in range(10)]
        kesz = [j.result() for j in as_completed(jovok)]  # befejezési sorrendben
    print(f"{len(kesz)} I/O feladat {time.perf_counter() - t0:.2f}s alatt (nem 2s)")

    for zarral in (False, True):
        sz = Szamla()
        szalak = [threading.Thread(target=lambda: [sz.befizet(1, zarral) for _ in range(500)])
                  for _ in range(4)]
        for s in szalak:
            s.start()
        for s in szalak:
            s.join()
        print(f"zárral={zarral}: {sz.egyenleg} (elvárt 2000)")

    darabok = [(i, i + 25_000) for i in range(0, 200_000, 25_000)]
    t0 = time.perf_counter()
    with ProcessPoolExecutor() as pool:  # alapból os.cpu_count() folyamat
        print("prímek:", sum(pool.map(primek, darabok)), f"{time.perf_counter() - t0:.2f}s")


if __name__ == "__main__":  # spawn módban a gyerek újraimportálja a modult
    main()
```

## Memóriakezelés és teljesítmény: GC, weakref, __slots__, profilozás
<!-- q: Hogyan kezeli a Python a memóriát, és hogyan mérjem és gyorsítsam a kódomat? -->
<!-- tags: memory, garbage collection, refcount, weakref, slots, tracemalloc, cprofile, timeit, performance -->

A CPython elsődlegesen referenciaszámlálással szabadít fel (az objektum azonnal törlődik, amint az utolsó referencia eltűnik), a referenciaciklusokat pedig a generációs ciklikus GC takarítja. A `weakref` nem növeli a számlálót, így cache-ek nem tartják életben az objektumokat; a `__slots__` megszünteti a példányonkénti `__dict__`-et, ami sok kis objektumnál jelentős memóriát spórol. Teljesítménynél először mérj (`timeit`, `cProfile`, `tracemalloc`, élesben `py-spy`), utána válassz jobb algoritmust/adatszerkezetet: `set`/`dict` O(1) keresés, `deque` a sor két végén, `heapq` top-k-ra, `"".join` string-összefűzésre.

```python
import cProfile
import gc
import heapq
import io
import pstats
import random
import timeit
import tracemalloc
import weakref
from collections import Counter


class PontDict:
    def __init__(self, x, y): self.x, self.y = x, y


class PontSlots:
    __slots__ = ("x", "y")  # nincs __dict__: kevesebb memória

    def __init__(self, x, y): self.x, self.y = x, y


def memoria(osztaly: type, n: int = 100_000) -> int:
    tracemalloc.start()
    lista = [osztaly(i, i) for i in range(n)]
    jelenlegi, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del lista
    return jelenlegi // 1024


def dupla_lassu(xs: list[int]) -> set[int]:
    lattuk, dupla = [], set()
    for x in xs:
        (dupla.add(x) if x in lattuk else lattuk.append(x))  # `in list` O(n) -> összesen O(n²)
    return dupla


def dupla_gyors(xs: list[int]) -> set[int]:
    return {x for x, db in Counter(xs).items() if db > 1}  # hash alapú, O(n)


class Csucs:
    def __init__(self) -> None:
        self.masik: "Csucs | None" = None


if __name__ == "__main__":
    a, b = Csucs(), Csucs()
    a.masik, b.masik = b, a           # ciklus: refcount sosem lesz 0
    figyelo = weakref.ref(a)          # gyenge referencia: nem tartja életben
    del a, b
    print("él még?", figyelo() is not None, "| gc:", gc.collect(), "| él még?", figyelo() is not None)

    print("KiB dict vs slots:", memoria(PontDict), memoria(PontSlots))
    adat = [random.randrange(3000) for _ in range(3000)]
    for fn in (dupla_lassu, dupla_gyors):
        print(fn.__name__, f"{min(timeit.repeat(lambda: fn(adat), number=3, repeat=3)) * 1000:.1f} ms")
    print("top3:", heapq.nlargest(3, adat))  # O(n log k), nem rendez mindent

    prof = cProfile.Profile()
    prof.runcall(dupla_lassu, adat)
    ki = io.StringIO()
    pstats.Stats(prof, stream=ki).sort_stats("cumulative").print_stats(3)
    print(ki.getvalue()[:600])  # parancssorból: python -m cProfile -s cumtime app.py
```

## Adatfeldolgozás: csv, json, Decimal és itertools
<!-- q: Hogyan dolgozzak fel CSV és JSON adatokat Pythonban külső könyvtár nélkül? -->
<!-- tags: csv, json, decimal, itertools, groupby, defaultdict, data processing, etl -->

A `csv.DictReader` soronként olvas, így nagy fájlnál sem tölti be az egészet; a hibás sorokat érdemes gyűjteni és jelenteni ahelyett, hogy az egész feldolgozás elhasalna. Pénzhez `Decimal` kell (a float bináris, `0.1 + 0.2 != 0.3`). Az `itertools.groupby` csak egymás melletti azonos kulcsokat csoportosít, ezért előtte rendezni kell; aggregáláshoz a `defaultdict`/`Counter` a legegyszerűbb. A `json` csak alaptípusokat ismer: dátumhoz, Decimalhoz, dataclasshoz saját `JSONEncoder.default` kell.

```python
import csv
import io
import itertools
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

NYERS = """datum;varos;termek;db;ar
2024-03-01;Budapest;kávé;3;1290.50
2024-03-01;Debrecen;tea;5;890
2024-03-02;Szeged;kávé;x;1290.50
2024-03-03;Budapest;tea;2;890
"""


@dataclass(frozen=True, slots=True)
class Eladas:
    datum: date
    varos: str
    termek: str
    db: int
    ar: Decimal


def beolvas(folyam: io.TextIOBase) -> tuple[list[Eladas], list[str]]:
    jo, hibak = [], []
    for n, sor in enumerate(csv.DictReader(folyam, delimiter=";"), start=2):
        try:
            jo.append(Eladas(date.fromisoformat(sor["datum"]), sor["varos"], sor["termek"],
                             int(sor["db"]), Decimal(sor["ar"])))
        except (ValueError, InvalidOperation, KeyError) as e:
            hibak.append(f"{n}. sor: {e}")  # gyűjtjük, nem állunk le
    return jo, hibak


class Encoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)  # stringként, hogy ne vesszen el pontosság
        if isinstance(o, date):
            return o.isoformat()
        if is_dataclass(o) and not isinstance(o, type):
            return asdict(o)
        return super().default(o)


if __name__ == "__main__":
    eladasok, hibak = beolvas(io.StringIO(NYERS))
    print("hibás:", hibak)

    bevetel: defaultdict[str, Decimal] = defaultdict(Decimal)
    for e in eladasok:
        bevetel[e.varos] += e.ar * e.db
    print({k: str(v) for k, v in bevetel.items()})

    kulcs = lambda e: e.termek  # noqa: E731
    for termek, csoport in itertools.groupby(sorted(eladasok, key=kulcs), key=kulcs):
        print(termek, sum(e.db for e in csoport))  # groupby előtt KÖTELEZŐ rendezni

    for koteg in itertools.batched(eladasok, 2):  # 3.12+: kötegelt adatbázis-írás
        print("köteg:", len(koteg))
    print(json.dumps(eladasok[:1], cls=Encoder, ensure_ascii=False, indent=2))
```

## Tesztelés pytesttel: fixture, parametrize, mock
<!-- q: Hogyan írjak unit teszteket pytesttel, fixture-ökkel és mockokkal? -->
<!-- tags: testing, pytest, fixture, parametrize, mock, monkeypatch, tmp_path -->

A pytest sima `assert`-tel dolgozik és hiba esetén részletesen kiírja a két oldalt; a fixture-ök név alapján injektálódnak és egymásra épülhetnek, a `parametrize` egy tesztet több bemenettel futtat. Külső függőséget (HTTP API, óra, fájlrendszer) `Mock`-kal vagy `monkeypatch`-csel cserélj, a `tmp_path` izolált ideiglenes mappát ad. A `Mock(spec=...)` megakadályozza, hogy elírt metódusnév csendben "működjön". Jó gyakorlat a függőségeket konstruktorban átadni (dependency injection), így a teszt nem igényel patch-elést.

```python
"""Futtatás: pytest -q test_atvalto.py"""
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pytest


@dataclass
class Atvalto:  # --- tesztelt kód ---
    forras: object  # bármi, aminek van arfolyam(penznem) metódusa
    jutalek: Decimal = Decimal("0.01")

    def huf_ra(self, osszeg: Decimal, penznem: str) -> Decimal:
        if osszeg < 0:
            raise ValueError("negatív összeg")
        if penznem == "HUF":
            return osszeg
        return (osszeg * self.forras.arfolyam(penznem) * (1 - self.jutalek)).quantize(Decimal("0.01"))


@pytest.fixture
def forras() -> Mock:
    m = Mock(spec=["arfolyam"])  # elírt metódusnévre AttributeError
    m.arfolyam.return_value = Decimal("400")
    return m


@pytest.fixture
def atvalto(forras: Mock) -> Atvalto:  # fixture-re épülő fixture
    return Atvalto(forras)


@pytest.mark.parametrize(("osszeg", "penznem", "elvart"), [
    (Decimal("10"), "EUR", Decimal("3960.00")),
    (Decimal("0"), "EUR", Decimal("0.00")),
    (Decimal("1.5"), "HUF", Decimal("1.5")),
], ids=["normal", "nulla", "huf"])
def test_atvaltas(atvalto, osszeg, penznem, elvart) -> None:
    assert atvalto.huf_ra(osszeg, penznem) == elvart


def test_huf_nem_hiv_api_t(atvalto: Atvalto, forras: Mock) -> None:
    atvalto.huf_ra(Decimal("5"), "HUF")
    forras.arfolyam.assert_not_called()


def test_hibak(atvalto: Atvalto, forras: Mock) -> None:
    with pytest.raises(ValueError, match="negatív"):
        atvalto.huf_ra(Decimal("-1"), "EUR")
    forras.arfolyam.side_effect = ConnectionError("API nem elérhető")
    with pytest.raises(ConnectionError):
        atvalto.huf_ra(Decimal("1"), "USD")


def test_fajl_es_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ut = tmp_path / "konfig.json"  # izolált mappa, a teszt után törlődik
    ut.write_text('{"debug": true}', encoding="utf-8")
    monkeypatch.setenv("APP_MOD", "teszt")  # automatikusan visszaáll
    assert json.loads(ut.read_text(encoding="utf-8")) == {"debug": True}
```

## Biztonsági buktatók: SQL injection, jelszavak, eval, subprocess, path traversal
<!-- q: Milyen gyakori biztonsági hibákat kell elkerülni Python kódban? -->
<!-- tags: security, sql injection, password hashing, secrets, eval, pickle, subprocess, path traversal -->

SQL-t soha ne f-stringgel építs: paraméterezett lekérdezést használj, és az escape-elést a driver végzi. Jelszót lassú, sózott KDF-fel (scrypt, argon2) tárolj, összehasonlításhoz `hmac.compare_digest` kell (konstans idő), tokenhez a `secrets` modul (a `random` kiszámítható). Megbízhatatlan bemenetre `eval`, `pickle.loads`, `yaml.load` tilos — tetszőleges kódot futtathatnak; literálokra `ast.literal_eval`, adatcserére JSON + séma-validáció. A `subprocess`-t lista argumentummal, `shell=False`-szal hívd, felhasználói fájlnevet pedig `resolve()` után ellenőrizz a gyökérmappához képest.

```python
import ast
import hashlib
import hmac
import secrets
import sqlite3
from pathlib import Path


def keres(db: sqlite3.Connection, nev: str) -> list[tuple]:
    # Paraméterezett lekérdezés: a bemenet sosem válik SQL kóddá
    return db.execute("SELECT id, nev FROM felhasznalo WHERE nev = ?", (nev,)).fetchall()


def jelszo_hash(jelszo: str, so: bytes | None = None) -> tuple[bytes, bytes]:
    so = so or secrets.token_bytes(16)  # felhasználónként egyedi só
    return so, hashlib.scrypt(jelszo.encode(), salt=so, n=2**14, r=8, p=1, dklen=32)


def jelszo_ok(jelszo: str, so: bytes, tarolt: bytes) -> bool:
    return hmac.compare_digest(jelszo_hash(jelszo, so)[1], tarolt)  # nincs timing side-channel


def biztonsagos_ut(gyoker: Path, nev: str) -> Path:
    cel = (gyoker / nev).resolve()  # feloldja a ../ és symlink elemeket
    if not cel.is_relative_to(gyoker.resolve()):
        raise PermissionError(f"tiltott elérési út: {nev}")
    return cel


if __name__ == "__main__":
    db = sqlite3.connect(":memory:")
    db.executescript("CREATE TABLE felhasznalo (id INTEGER PRIMARY KEY, nev TEXT);"
                     "INSERT INTO felhasznalo (nev) VALUES ('teszt1'), ('teszt2');")
    tamadas = "x' OR '1'='1"
    rossz = db.execute(f"SELECT id FROM felhasznalo WHERE nev = '{tamadas}'").fetchall()
    print("f-string SQL:", rossz, "| paraméterezett:", keres(db, tamadas))  # minden sor vs []

    so, tarolt = jelszo_hash("demo-jelszo-123")
    print(jelszo_ok("demo-jelszo-123", so, tarolt), jelszo_ok("rossz", so, tarolt))
    print("token:", len(secrets.token_urlsafe(32)), "karakter")

    print(ast.literal_eval("{'a': [1, 2]}"))  # csak literál
    try:
        ast.literal_eval("__import__('os').getcwd()")
    except ValueError:
        print("literal_eval elutasította a kódot")

    try:
        biztonsagos_ut(Path("/srv/feltoltes"), "../../etc/passwd")
    except PermissionError as e:
        print(e)
    # subprocess.run(["convert", fajlnev, "ki.png"], check=True, timeout=30)  – lista, shell=False
```
