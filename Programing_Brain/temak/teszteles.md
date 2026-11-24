# Tesztelés
<!-- tech: testing -->
<!-- aliases: tesztelés, unit test, pytest, jest, vitest, junit, xunit, tdd, e2e, playwright, mocking -->

A szoftvertesztelés célja, hogy a változtatások gyorsan és magabiztosan kiadhatók legyenek: a jó tesztkészlet gyors, determinisztikus, a viselkedést ellenőrzi (nem az implementációt), és hiba esetén pontosan megmutatja, mi romlott el. A rétegek: unit tesztek (tiszta logika, ms-os futás), integrációs tesztek (valódi adatbázis, üzenetsor, HTTP), szerződés-tesztek (szolgáltatások közti API), E2E tesztek (teljes felhasználói út böngészőben), valamint teljesítmény- és terheléses tesztek. A tesztelhetőség tervezési kérdés: a függőségek injektálása, a tiszta mag és a vékony I/O-réteg sokkal többet ad, mint bármilyen mock-könyvtár.

## Tesztpiramis és a tesztkészlet szerkezete
<!-- q: Mi a tesztpiramis és hogyan osszam el a unit, integrációs és E2E teszteket? -->
<!-- tags: test pyramid, unit tests, integration tests, e2e, test strategy, markers, pytest -->

A tesztpiramis szerint sok gyors unit teszt, kevesebb integrációs teszt és kevés, a kritikus utakat lefedő E2E teszt adja a legjobb arányt: lefelé haladva a tesztek gyorsabbak, stabilabbak és pontosabban lokalizálják a hibát, felfelé haladva valósághűbbek, de lassúbbak és törékenyebbek. A „fagylalttölcsér” (főleg kézi és E2E teszt) lassú visszajelzést és flaky CI-t okoz. Modern backendnél gyakran a „tesztelési trófea” a jobb modell: az integrációs tesztek valódi DB-vel (konténerben) olcsók lettek, és többet érnek, mint a mockokkal teli unit tesztek. A rétegeket markerekkel válaszd szét, hogy a gyors kör minden mentéskor, a lassabb a CI-ban fusson.

```toml
# pyproject.toml — rétegek markerekkel, külön futtathatóan
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"          # elgépelt marker = hiba, nem csendes kihagyás
markers = [
    "integration: valódi DB/üzenetsor kell (konténerben, lassabb)",
    "e2e: a teljes rendszer böngészőn/API-n át (leglassabb)",
    "slow: 1 másodpercnél tovább fut",
]
# Könyvtárszerkezet:
#   tests/unit/          ~70%: tiszta logika, ms-os futás, minden mentésnél
#   tests/integration/   ~20%: DB, HTTP kliens, fájlrendszer valódi függőséggel
#   tests/e2e/           ~10%: kritikus felhasználói utak (belépés, fizetés)
# Futtatás:
#   pytest -m "not integration and not e2e"     -> gyors kör fejlesztés közben
#   pytest -m integration                       -> CI, konténerekkel
```

## Unit tesztek pytesttel, paraméterezéssel
<!-- q: Hogyan írjak jó unit teszteket pytesttel és paraméterezett tesztekkel? -->
<!-- tags: pytest, unit test, parametrize, assert, raises, edge cases, python -->

A pytest sima `assert`-tel dolgozik, és hiba esetén részletesen kiírja a kifejezés értékeit; a `pytest.raises` a kivételt és az üzenetét is ellenőrzi. A `@pytest.mark.parametrize` egy tesztfüggvényt több bemenettel futtat, mindegyik külön tesztként jelenik meg, olvasható `ids`-szel — ez a határértékek (0, üres, maximum, kerekítési pont) szisztematikus lefedésének eszköze. Egy teszt egy viselkedést ellenőrizzen, a neve mondja meg, mit vár (`test_rejects_unknown_vat`). Pénzhez `Decimal`-t és explicit kerekítési módot használj: a Python `round()` banker's rounding-ot alkalmaz.

```python
from decimal import Decimal, ROUND_HALF_UP
import pytest

# --- src/pricing.py ---
class PricingError(ValueError):
    pass

def net_to_gross(net: Decimal, vat_pct: int) -> Decimal:
    if net < 0:
        raise PricingError("negatív nettó ár")
    if vat_pct not in (0, 5, 18, 27):
        raise PricingError(f"ismeretlen ÁFA-kulcs: {vat_pct}")
    gross = net * (100 + vat_pct) / 100
    return gross.quantize(Decimal("1"), rounding=ROUND_HALF_UP)   # forintra kerekítve

# --- tests/unit/test_pricing.py ---
@pytest.mark.parametrize(
    ("net", "vat", "expected"),
    [
        (Decimal("1000"), 27, Decimal("1270")),
        (Decimal("999"), 27, Decimal("1269")),      # 1268.73 -> 1269
        (Decimal("0"), 27, Decimal("0")),           # határeset
        (Decimal("100"), 0, Decimal("100")),
        (Decimal("0.5"), 0, Decimal("1")),          # HALF_UP; a banker's rounding 0-t adna
    ],
    ids=["alap", "kerekítés", "nulla", "áfamentes", "fél-felfelé"],
)
def test_net_to_gross(net, vat, expected):
    assert net_to_gross(net, vat) == expected

@pytest.mark.parametrize("vat", [-1, 26, 100])
def test_rejects_unknown_vat(vat):
    with pytest.raises(PricingError, match="ismeretlen ÁFA"):
        net_to_gross(Decimal("100"), vat)

def test_rejects_negative_net():
    with pytest.raises(PricingError, match="negatív"):
        net_to_gross(Decimal("-1"), 27)
```

## Unit tesztek Vitesttel és Jesttel
<!-- q: Hogyan írjak unit teszteket JavaScript/TypeScript kódhoz Vitesttel vagy Jesttel? -->
<!-- tags: vitest, jest, typescript, describe, it.each, fake timers, vi.fn, mock functions -->

A Vitest és a Jest API-ja szinte azonos (`describe`, `it`, `expect`, `beforeEach`); a Vitest a Vite-ra épül, natívan kezeli az ESM-et és a TypeScriptet, ezért új projektben gyorsabb és egyszerűbb, Jestben a `vi` helyett `jest` a segédobjektum. Az `it.each` táblázatos teszteket ad, a *fake timers* (`vi.useFakeTimers`, `vi.setSystemTime`) determinisztikussá teszi az időfüggő kódot, a `vi.fn()` pedig rögzíti a hívásokat. A fake timereket mindig állítsd vissza (`afterEach`), különben a következő tesztek furcsán viselkednek. Az időt lehetőleg paraméterként add át — akkor fake timer sem kell.

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// --- cart.ts ---
export type Item = { sku: string; price: number; qty: number };

export function subtotal(items: readonly Item[]): number {
  return items.reduce((sum, i) => {
    if (i.qty <= 0) throw new RangeError(`hibás mennyiség: ${i.sku}`);
    return sum + i.price * i.qty;
  }, 0);
}

export function couponDiscount(code: string, amount: number, now: Date): number {
  return code === "BF25" && now.getMonth() === 10 ? Math.round(amount * 0.25) : 0;  // csak novemberben
}

// --- cart.test.ts ---
describe("subtotal", () => {
  it("összeadja a tételeket", () => {
    expect(subtotal([{ sku: "a", price: 100, qty: 2 }, { sku: "b", price: 50, qty: 1 }])).toBe(250);
  });
  it("üres kosárra 0", () => expect(subtotal([])).toBe(0));
  it("hibás mennyiségre dob", () => {
    expect(() => subtotal([{ sku: "x", price: 1, qty: 0 }])).toThrowError(/hibás mennyiség: x/);
  });
  it.each([
    [1, 100],
    [3, 300],
    [10, 1000],
  ])("qty=%i -> %i", (qty, expected) => {
    expect(subtotal([{ sku: "a", price: 100, qty }])).toBe(expected);
  });
});

describe("couponDiscount", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());          // mindig visszaállítjuk

  it("novemberben 25% kedvezmény", () => {
    vi.setSystemTime(new Date("2025-11-28T10:00:00Z"));
    expect(couponDiscount("BF25", 1000, new Date())).toBe(250);
  });
  it("máskor nincs kedvezmény", () => {
    expect(couponDiscount("BF25", 1000, new Date("2025-06-01T00:00:00Z"))).toBe(0);
  });
});

describe("mock függvény", () => {
  it("rögzíti a hívásokat", async () => {
    const notify = vi.fn().mockResolvedValue(undefined);
    await Promise.all([1, 2].map((n) => notify(`order-${n}`)));
    expect(notify).toHaveBeenCalledTimes(2);
    expect(notify).toHaveBeenLastCalledWith("order-2");
  });
});
```

## Unit tesztek JUnit 5-tel és xUnittal
<!-- q: Hogyan írjak paraméterezett unit teszteket Javában (JUnit 5) és C#-ban (xUnit)? -->
<!-- tags: junit5, java, parameterized test, csvsource, xunit, csharp, theory, inlinedata, assertall -->

JUnit 5-ben a `@ParameterizedTest` + `@CsvSource`/`@MethodSource` adja a táblázatos teszteket, az `assertAll` pedig minden állítást lefuttat, és az összes hibát egyszerre jelenti (nem áll meg az elsőnél). xUnitban a `[Fact]` paraméter nélküli, a `[Theory]` + `[InlineData]`/`[MemberData]` paraméterezett teszt; minden tesztmetódus új osztálypéldányt kap, így a konstruktor a setup, az `IDisposable.Dispose` a teardown. Véletlen adatokkal futó tesztnél mindig rögzített seedet használj, hogy a hiba reprodukálható legyen. Mindkét keretrendszer párhuzamosan futtat, ezért a tesztek ne osszanak meg módosítható statikus állapotot.

```java
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import java.util.ArrayList;
import static org.junit.jupiter.api.Assertions.*;

class PasswordPolicy {
    static boolean isStrong(String pw) {
        return pw != null && pw.length() >= 12
            && pw.chars().anyMatch(Character::isDigit)
            && pw.chars().anyMatch(Character::isUpperCase);
    }
}

@DisplayName("Jelszó-szabály")
class PasswordPolicyTest {
    @ParameterizedTest(name = "[{index}] \"{0}\" -> {1}")
    @CsvSource({
        "Abcdefghijk1, true",
        "abcdefghijk1, false",   // nincs nagybetű
        "Abcdefghijkl, false",   // nincs számjegy
        "Ab1, false",            // túl rövid
    })
    void strength(String pw, boolean expected) {
        assertEquals(expected, PasswordPolicy.isStrong(pw));
    }

    @Test
    void nullIsWeak() {
        assertFalse(PasswordPolicy.isStrong(null));
    }

    @Test
    void groupedAssertions() {
        var errors = new ArrayList<String>();
        assertAll("üres lista",                    // minden állítás lefut, az összes hiba jelentve
            () -> assertTrue(errors.isEmpty()),
            () -> assertThrows(IndexOutOfBoundsException.class, () -> errors.get(0)));
    }
}
```

```csharp
using System;
using System.Linq;
using Xunit;

public static class Money
{
    // Összeg szétosztása n részre úgy, hogy egy fillér se vesszen el
    public static long[] Split(long totalCents, int parts)
    {
        if (parts <= 0) throw new ArgumentOutOfRangeException(nameof(parts));
        var share = totalCents / parts;
        var remainder = totalCents % parts;
        return Enumerable.Range(0, parts).Select(i => share + (i < remainder ? 1 : 0)).ToArray();
    }
}

public class MoneyTests
{
    [Theory]
    [InlineData(100L, 3, new long[] { 34, 33, 33 })]
    [InlineData(10L, 2, new long[] { 5, 5 })]
    [InlineData(0L, 4, new long[] { 0, 0, 0, 0 })]
    public void Split_distributes_remainder(long total, int parts, long[] expected)
        => Assert.Equal(expected, Money.Split(total, parts));

    [Fact]
    public void Split_never_loses_money()
    {
        var rnd = new Random(42);                 // rögzített seed: reprodukálható hiba
        for (var i = 0; i < 1000; i++)
        {
            long total = rnd.Next(0, 1_000_000);
            int parts = rnd.Next(1, 50);
            Assert.Equal(total, Money.Split(total, parts).Sum());
        }
    }

    [Fact]
    public void Split_rejects_zero_parts()
        => Assert.Throws<ArgumentOutOfRangeException>(() => Money.Split(100, 0));
}
```

## Tesztelés Go-ban: táblázatos tesztek, benchmark, fuzz
<!-- q: Hogyan írjak táblázatos teszteket, benchmarkot és fuzz tesztet Go-ban? -->
<!-- tags: go testing, table driven tests, t.Run, subtests, benchmark, fuzzing, t.Parallel -->

A Go beépített `testing` csomagja külön keretrendszer nélkül ad unit tesztet, benchmarkot és fuzzolást; az idiomatikus forma a *táblázatos teszt*: egy esetlista, és `t.Run`-nal mindegyik külön, névvel szűrhető részteszt (`go test -run 'TestMake/üres'`). A `t.Parallel()` párhuzamosít; Go 1.22 előtt a ciklusváltozót le kellett másolni (`tt := tt`), mert a closure-ök ugyanazt a változót látták. A `Benchmark*` függvényt a `go test -bench . -benchmem` futtatja, a `Fuzz*` pedig véletlen bemenetekkel invariánsokat ellenőriz, és a hibát okozó bemenetet elmenti a `testdata` mappába.

```go
// --- slug.go ---
package slug

import (
	"strings"
	"unicode"
)

func Make(s string) string {
	var b strings.Builder
	dash := false
	for _, r := range strings.ToLower(s) {
		switch {
		case r >= 'a' && r <= 'z' || unicode.IsDigit(r):
			b.WriteRune(r)
			dash = false
		case !dash && b.Len() > 0:
			b.WriteByte('-') // több elválasztóból egyetlen kötőjel
			dash = true
		}
	}
	return strings.TrimSuffix(b.String(), "-")
}
```

```go
// --- slug_test.go ---
package slug

import (
	"strings"
	"testing"
)

func TestMake(t *testing.T) {
	tests := []struct {
		name, in, want string
	}{
		{"egyszerű", "Hello World", "hello-world"},
		{"többszörös elválasztó", "a  --  b", "a-b"},
		{"szélek", "  ---x---  ", "x"},
		{"üres", "", ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel() // Go 1.22+: a ciklusváltozó iterációnként új
			if got := Make(tt.in); got != tt.want {
				t.Errorf("Make(%q) = %q, want %q", tt.in, got, tt.want)
			}
		})
	}
}

func BenchmarkMake(b *testing.B) {
	for i := 0; i < b.N; i++ {
		Make("Funkcionális Programozás Alapjai 2025")
	}
}

func FuzzMake(f *testing.F) {
	f.Add("Hello World")
	f.Fuzz(func(t *testing.T, s string) {
		out := Make(s)
		// Invariánsok: nincs kötőjel a széleken, és nincs dupla kötőjel
		if strings.HasPrefix(out, "-") || strings.HasSuffix(out, "-") || strings.Contains(out, "--") {
			t.Fatalf("Make(%q) = %q sérti az invariánst", s, out)
		}
	})
}
```

## Test double-ok: mock, stub, fake — és mikor ne mockolj
<!-- q: Mi a különbség a mock, stub és fake között, és mikor ne használjak mockot? -->
<!-- tags: mocking, mock, stub, fake, spy, test doubles, unittest.mock, autospec, over-mocking -->

A *stub* előre megadott választ ad (pl. a fizetési gateway „sikeres” választ), a *mock* azt is ellenőrzi, hogyan hívták, a *fake* pedig működő, egyszerűsített implementáció (memóriabeli repository), a *spy* a valódi objektum hívásait rögzíti. Mockolj a rendszer határán (külső HTTP API, fizetés, e-mail, idő), de ne a saját belső osztályaidat: a túlmockolt teszt az implementációt rögzíti, refaktoráláskor eltörik, miközben valódi hibát nem fog meg. Belső függőségre fake vagy a valódi objektum a jobb, az eredményt pedig állapot alapján ellenőrizd. Python `Mock`-nál mindig használj `spec`/`autospec`-et, különben az elgépelt metódusnév is „sikeresen” lefut.

```python
from unittest.mock import Mock, create_autospec
import pytest

class PaymentGateway:                       # külső rendszer (HTTP) — ezt érdemes helyettesíteni
    def charge(self, customer_id: str, amount: int) -> str: ...

class OrderRepo:
    def save(self, order: dict) -> None: ...
    def get(self, order_id: str) -> dict | None: ...

class FakeOrderRepo(OrderRepo):             # FAKE: működő, memóriabeli implementáció
    def __init__(self): self.rows = {}
    def save(self, order): self.rows[order["id"]] = dict(order)
    def get(self, order_id): return self.rows.get(order_id)

class CheckoutService:
    def __init__(self, gateway: PaymentGateway, repo: OrderRepo):
        self.gateway, self.repo = gateway, repo
    def checkout(self, order_id: str, customer_id: str, amount: int) -> dict:
        if amount <= 0:
            raise ValueError("az összeg pozitív kell legyen")
        payment_id = self.gateway.charge(customer_id, amount)
        order = {"id": order_id, "status": "paid", "payment_id": payment_id}
        self.repo.save(order)
        return order

def test_checkout_charges_and_persists():
    gateway = create_autospec(PaymentGateway, instance=True)   # STUB + szignatúra-ellenőrzés
    gateway.charge.return_value = "pay_123"
    repo = FakeOrderRepo()
    CheckoutService(gateway, repo).checkout("o1", "c1", 4990)
    gateway.charge.assert_called_once_with("c1", 4990)         # MOCK-ellenőrzés a határon
    assert repo.get("o1") == {"id": "o1", "status": "paid", "payment_id": "pay_123"}  # állapot

def test_gateway_failure_does_not_persist():
    gateway = create_autospec(PaymentGateway, instance=True)
    gateway.charge.side_effect = TimeoutError("gateway timeout")   # hiba szimulálása
    repo = FakeOrderRepo()
    with pytest.raises(TimeoutError):
        CheckoutService(gateway, repo).checkout("o1", "c1", 4990)
    assert repo.get("o1") is None

def test_invalid_amount_never_calls_gateway():
    gateway = Mock(spec=PaymentGateway)
    with pytest.raises(ValueError):
        CheckoutService(gateway, FakeOrderRepo()).checkout("o1", "c1", 0)
    gateway.charge.assert_not_called()
```

## Fixture-ök: setup, teardown és factory-k
<!-- q: Hogyan használjam a pytest fixture-öket setupra, teardownra és tesztadatokra? -->
<!-- tags: pytest fixtures, setup, teardown, scope, factory fixture, tmp_path, monkeypatch, conftest -->

A pytest fixture egy függvény, amelynek eredményét a teszt paraméterként kapja; a `yield` előtti rész a setup, utána a teardown, ami hiba esetén is lefut. A `scope` határozza meg az élettartamot: `function` (alapértelmezett, minden teszt friss példányt kap), `module`, `session` (drága, de nem módosítható erőforráshoz). A *factory fixture* függvényt ad vissza, így a teszt maga dönti el, milyen és mennyi adat kell — ez kiváltja a sok közös, „mindenre jó” tesztadatot. A közös fixture-ök a `conftest.py`-ba valók; a beépített `tmp_path` és `monkeypatch` automatikusan takarít.

```python
import json
import os
import sqlite3
import pytest

@pytest.fixture(scope="session")
def schema_sql() -> str:
    # session scope: egyszer jön létre a teljes futásra
    return "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, active INTEGER)"

@pytest.fixture
def db(schema_sql):
    # function scope: minden teszt friss adatbázist kap -> nincs teszt-közti függés
    conn = sqlite3.connect(":memory:")
    conn.execute(schema_sql)
    yield conn                       # setup | teardown a yield két oldalán
    conn.close()

@pytest.fixture
def make_user(db):
    # factory fixture: a teszt dönti el, milyen user kell
    counter = iter(range(1, 10_000))
    def _make(email=None, active=True):
        email = email or f"user{next(counter)}@example.test"
        db.execute("INSERT INTO users (email, active) VALUES (?, ?)", (email, int(active)))
        return email
    return _make

@pytest.fixture
def config_file(tmp_path, monkeypatch):
    # tmp_path: izolált könyvtár; monkeypatch: env-változó, a teszt végén visszaáll
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"feature_x": True}), encoding="utf-8")
    monkeypatch.setenv("APP_CONFIG", str(path))
    return path

def count_active(conn) -> int:
    return conn.execute("SELECT count(*) FROM users WHERE active = 1").fetchone()[0]

def test_counts_only_active(db, make_user):
    make_user(); make_user(); make_user(active=False)
    assert count_active(db) == 2

def test_email_unique(make_user):
    make_user(email="a@example.test")
    with pytest.raises(sqlite3.IntegrityError):
        make_user(email="a@example.test")

def test_config_from_env(config_file):
    with open(os.environ["APP_CONFIG"], encoding="utf-8") as f:
        assert json.load(f)["feature_x"] is True
```

## Property-based tesztelés: Hypothesis és fast-check
<!-- q: Mi az a property-based testing és hogyan használjam Hypothesis-szel vagy fast-checkkel? -->
<!-- tags: property based testing, hypothesis, fast-check, invariants, shrinking, round trip, generators -->

A property-based teszt nem konkrét példákat ellenőriz, hanem *tulajdonságokat*, amelyeknek minden bemenetre teljesülniük kell; a könyvtár száz/ezer véletlen bemenetet generál, és hiba esetén a legkisebb ellenpéldára zsugorítja (*shrinking*). Tipikus tulajdonságok: oda-vissza alakítás (encode → decode = eredeti), invariánsok (a rendezett lista rendezett és ugyanannyi elemű), idempotencia, egy egyszerű referencia-implementációval való egyezés. Kiválóan megtalálja a határeseteket (üres string, Unicode, nagy számok), amikre nem gondoltál. A Hypothesis a megtalált hibás eseteket adatbázisban megjegyzi és újrafuttatja; a `@example` a fontos esetet mindig lefuttatja.

```python
from hypothesis import example, given, settings, strategies as st

def rle_encode(s: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for ch in s:
        if out and out[-1][0] == ch:
            out[-1] = (ch, out[-1][1] + 1)
        else:
            out.append((ch, 1))
    return out

def rle_decode(pairs: list[tuple[str, int]]) -> str:
    return "".join(ch * n for ch, n in pairs)

@given(st.text())
@example("")                                    # a határeset mindig lefut
def test_roundtrip(s):
    assert rle_decode(rle_encode(s)) == s       # oda-vissza tulajdonság

@given(st.text(min_size=1))
def test_no_adjacent_duplicates(s):
    pairs = rle_encode(s)                       # invariáns: szomszédos párok különböznek
    assert all(a[0] != b[0] for a, b in zip(pairs, pairs[1:]))
    assert all(n >= 1 for _, n in pairs)

@settings(max_examples=500)
@given(st.lists(st.integers()))
def test_sort_properties(xs):
    ys = sorted(xs)
    assert len(ys) == len(xs)                   # semmi nem vész el
    assert all(a <= b for a, b in zip(ys, ys[1:]))
    assert sorted(ys) == ys                     # idempotens
```

```typescript
import fc from "fast-check";
import { describe, it, expect } from "vitest";

const encodeQuery = (params: Record<string, string>) => new URLSearchParams(params).toString();
const decodeQuery = (q: string) => Object.fromEntries(new URLSearchParams(q));

describe("query string", () => {
  it("oda-vissza alakítás tetszőleges kulcsokra és értékekre", () => {
    fc.assert(
      fc.property(fc.dictionary(fc.string({ minLength: 1 }), fc.string()), (params) => {
        expect(decodeQuery(encodeQuery(params))).toEqual(params);
      }),
      { numRuns: 1000 },   // hiba esetén a legkisebb ellenpéldát kapod vissza
    );
  });
});
```

## Integrációs tesztek valódi függőségekkel (Testcontainers)
<!-- q: Hogyan írjak integrációs teszteket valódi adatbázissal Docker konténerben? -->
<!-- tags: integration tests, testcontainers, docker, postgres, database testing, transactions -->

Az integrációs teszt a kódot valódi függőséggel futtatja: a Testcontainers a teszt elején Dockerben elindít egy eldobható Postgrest (Redis-t, Kafkát), és a végén leállítja, így pontosan az éles verzió viselkedését teszteled — constrainteket, tranzakciókat, SQL-dialektust, amit SQLite vagy mock sosem fogna meg. A konténert session scope-ban indítsd (másodpercekig tart), a tesztek közti izolációt pedig `TRUNCATE`-tel vagy tranzakció-visszagörgetéssel oldd meg. Markerrel válaszd le a unit tesztektől, hogy a gyors kör ne igényeljen Dockert. CI-ban a Docker elérhetősége (vagy GitHub Actions `services`) előfeltétel.

```python
import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def pg_url():
    # Valódi Postgres, ugyanaz a főverzió, mint élesben; a végén automatikusan leáll
    with PostgresContainer("postgres:16-alpine", driver=None) as pg:
        yield pg.get_connection_url()

@pytest.fixture
def conn(pg_url):
    with psycopg.connect(pg_url) as c:
        c.execute("CREATE TABLE IF NOT EXISTS accounts "
                  "(id int PRIMARY KEY, balance int NOT NULL CHECK (balance >= 0))")
        c.execute("TRUNCATE accounts")                 # izoláció: tiszta állapot tesztenként
        c.execute("INSERT INTO accounts VALUES (1, 100), (2, 0)")
        c.commit()
        yield c

def transfer(c, src: int, dst: int, amount: int) -> None:
    with c.transaction():                              # hiba esetén mindkét UPDATE visszagörgetődik
        c.execute("UPDATE accounts SET balance = balance - %s WHERE id = %s", (amount, src))
        c.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s", (amount, dst))

def balances(c) -> dict[int, int]:
    return dict(c.execute("SELECT id, balance FROM accounts ORDER BY id").fetchall())

@pytest.mark.integration
def test_transfer_moves_money(conn):
    transfer(conn, 1, 2, 30)
    assert balances(conn) == {1: 70, 2: 30}

@pytest.mark.integration
def test_overdraft_rolls_back_whole_transaction(conn):
    # A CHECK constraint a valódi adatbázisban fut le — egy mock ezt nem fogná meg
    with pytest.raises(psycopg.errors.CheckViolation):
        transfer(conn, 2, 1, 50)
    assert balances(conn) == {1: 100, 2: 0}
```

## E2E tesztek Playwrighttal
<!-- q: Hogyan írjak stabil end-to-end teszteket Playwrighttal? -->
<!-- tags: e2e, playwright, browser testing, locators, auto waiting, network mocking, end to end -->

Az E2E teszt valódi böngészőben, a felhasználó szemszögéből járja végig a kritikus utakat (belépés, kosár, fizetés). A Playwright stabilitásának kulcsa az *auto-wait*: a műveletek és a web-first állítások (`toHaveText`, `toBeVisible`) automatikusan várnak, ezért soha ne használj fix `sleep`-et. Szerep- és label-alapú lokátorokat (`getByRole`, `getByLabel`) használj CSS-szelektorok helyett — ezek a felhasználó és az akadálymentesség szemszögét követik, és ellenállnak a markup-változásoknak. A bejelentkezést egyszer végezd el és mentsd (`storageState`), a lassú vagy külső API-kat `page.route`-tal helyettesítsd; az E2E-t tartsd kevésnek, mert lassú és drága karbantartani.

```typescript
import { test, expect } from "@playwright/test";

test.describe("belépés és kosár", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");                         // baseURL a playwright.config.ts-ben
  });

  test("belépés után termék tehető a kosárba", async ({ page }) => {
    await page.getByLabel("E-mail").fill("teszt.user@example.test");
    await page.getByLabel("Jelszó").fill(process.env.E2E_PASSWORD ?? "");   // titok env-ből
    await page.getByRole("button", { name: "Belépés" }).click();

    await expect(page).toHaveURL(/\/dashboard/);       // auto-wait, nincs sleep
    await page.getByRole("link", { name: "Termékek" }).click();
    await page
      .getByRole("article")
      .filter({ hasText: "Billentyűzet" })
      .getByRole("button", { name: "Kosárba" })
      .click();
    await expect(page.getByTestId("cart-count")).toHaveText("1");
  });

  test("hibás jelszóra hibaüzenet", async ({ page }) => {
    await page.getByLabel("E-mail").fill("teszt.user@example.test");
    await page.getByLabel("Jelszó").fill("rossz-jelszo");
    await page.getByRole("button", { name: "Belépés" }).click();
    await expect(page.getByRole("alert")).toContainText("Hibás e-mail vagy jelszó");
  });

  test("lassú API alatt töltésjelző (hálózat helyettesítve)", async ({ page }) => {
    await page.route("**/api/products", async (route) => {
      await new Promise((r) => setTimeout(r, 1500));   // késleltetett válasz szimulálása
      await route.fulfill({ json: [] });
    });
    await page.goto("/products");
    await expect(page.getByText("Betöltés…")).toBeVisible();
    await expect(page.getByText("Nincs termék")).toBeVisible();
  });
});
```

## Szerződés-tesztek (contract testing) Pacttal
<!-- q: Mi az a contract testing és hogyan előzi meg a mikroszolgáltatások közti törő változásokat? -->
<!-- tags: contract testing, pact, consumer driven contracts, microservices, api compatibility, provider verification -->

Mikroszolgáltatásoknál az E2E teszt minden szolgáltatással lassú és törékeny; a *fogyasztó-vezérelt szerződésteszt* (Pact) ehelyett a fogyasztó oldalán rögzíti, milyen kérést küld és milyen *alakú* választ vár, egy mock szerver ellen. A keletkező szerződés-fájl egy brokerbe kerül, és a szolgáltató CI-ja visszajátssza a saját valódi API-ja ellen (*provider verification*); ha a szolgáltató törne egy olyan mezőt, amit valaki használ, a deploy előtt kiderül. Matchereket (`like`, `eachLike`, `integer`) használj pontos értékek helyett, hogy a szerződés csak azt rögzítse, amire tényleg építesz. A `can-i-deploy` ellenőrzés a broker alapján dönti el, kiadható-e egy verzió.

```typescript
import { PactV3, MatchersV3 } from "@pact-foundation/pact";
import { describe, it, expect } from "vitest";

const { like, eachLike, integer } = MatchersV3;

// A fogyasztó (web-shop) leírja, mit vár a szolgáltatótól (user-service)
const provider = new PactV3({ consumer: "web-shop", provider: "user-service", dir: "./pacts" });

async function fetchUser(baseUrl: string, id: number) {
  const res = await fetch(`${baseUrl}/users/${id}`, { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as { id: number; name: string; roles: string[] };
}

describe("user-service szerződés", () => {
  it("visszaadja a felhasználót", async () => {
    provider
      .given("létezik a 42-es felhasználó")          // provider state: a szolgáltató állítja elő
      .uponReceiving("kérés a 42-es felhasználóra")
      .withRequest({ method: "GET", path: "/users/42", headers: { Accept: "application/json" } })
      .willRespondWith({
        status: 200,
        headers: { "Content-Type": "application/json" },
        // alakot rögzítünk, nem pontos értéket
        body: { id: integer(42), name: like("Teszt Elek"), roles: eachLike("customer") },
      });

    await provider.executeTest(async (mockServer) => {
      const user = await fetchUser(mockServer.url, 42);
      expect(user.id).toBe(42);
      expect(user.roles.length).toBeGreaterThan(0);
    });
  });
});
// A ./pacts/web-shop-user-service.json a brokerbe kerül; a user-service CI-ja ellenőrzi a
// saját API-ja ellen, deploy előtt pedig: pact-broker can-i-deploy --pacticipant user-service ...
```

## TDD munkafolyamat lépésről lépésre
<!-- q: Hogyan néz ki a TDD (tesztvezérelt fejlesztés) a gyakorlatban? -->
<!-- tags: tdd, test driven development, red green refactor, triangulation, design, unit tests -->

A TDD ciklusa: *piros* (írj egy tesztet a következő kis viselkedésre, és nézd meg, hogy elbukik), *zöld* (írd meg a legegyszerűbb kódot, ami átmegy), *refaktor* (a zöld tesztek védelmében tisztítsd a kódot). Az újabb tesztek *trianguláció*val kényszerítik ki az általánosítást, így csak annyi kód születik, amennyit tesztek igényelnek. A legnagyobb haszna a tervezésre gyakorolt hatás: tesztelhető, kis interfészű, függőségeit kívülről kapó kód jön létre, és a hibás bemenetek kezelése is már az elején eszedbe jut. Nem kötelező mindenre — felfedező prototípusnál vagy UI-finomhangolásnál a teszt jöhet később.

```python
import re
import pytest

# 1) PIROS: a teszt leírja a kívánt viselkedést (parse_duration még nem létezik -> elbukik)
def test_parses_minutes():
    assert parse_duration("15m") == 900

# 2) ZÖLD: a legegyszerűbb, ami átmegy — akár "csalás" is:
#    def parse_duration(text): return int(text[:-1]) * 60

# 3) Újabb tesztek kényszerítik az általánosítást (trianguláció)
@pytest.mark.parametrize(("text", "seconds"), [
    ("15m", 900), ("2h", 7200), ("1h30m", 5400), ("45s", 45), ("1h0m5s", 3605),
])
def test_parses_combinations(text, seconds):
    assert parse_duration(text) == seconds

# 4) A hibás bemenetek is specifikáció részei
@pytest.mark.parametrize("bad", ["", "10", "5x", "m", "1h1h", "-5m", "30m1h"])
def test_rejects_invalid(bad):
    with pytest.raises(ValueError):
        parse_duration(bad)

# 5) REFAKTOR: zöld tesztek mellett tisztított végleges megoldás
_PATTERN = re.compile(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?")
_UNITS = (3600, 60, 1)

def parse_duration(text: str) -> int:
    m = _PATTERN.fullmatch(text)
    if not text or m is None:
        raise ValueError(f"érvénytelen időtartam: {text!r}")
    return sum(int(v) * unit for v, unit in zip(m.groups(), _UNITS) if v is not None)
```

## Snapshot tesztek
<!-- q: Mikor hasznosak a snapshot tesztek és mire figyeljek használatuknál? -->
<!-- tags: snapshot testing, inline snapshot, vitest, jest, golden files, property matchers -->

A snapshot teszt egy kimenetet (renderelt szöveg, komponens-markup, API-válasz) elment, és a következő futásokban az eltérést jelzi; hasznos nagy, strukturált kimenetnél, ahol kézzel írt assertek sokasága kellene. A veszély, hogy a fejlesztők gondolkodás nélkül frissítik (`-u`), így a teszt bármit „elfogad” — ezért legyenek kicsik, és lehetőleg *inline* snapshotok, amelyek a review-ban is láthatók. Az instabil mezőket (időbélyeg, UUID) rögzítsd vagy property matcherrel (`expect.any(String)`) helyettesítsd. Üzleti szabályt ne snapshottal, hanem célzott assertekkel ellenőrizz.

```typescript
import { describe, it, expect } from "vitest";

type Line = { name: string; qty: number; unit: number };
type Invoice = { id: string; lines: Line[]; issuedAt: Date };

function renderInvoice(inv: Invoice): string {
  const rows = inv.lines.map((l) => `${l.name.padEnd(12)} ${String(l.qty).padStart(3)} x ${l.unit} Ft`);
  const total = inv.lines.reduce((s, l) => s + l.qty * l.unit, 0);
  const date = inv.issuedAt.toISOString().slice(0, 10);
  return [`Számla #${inv.id} (${date})`, ...rows, `Összesen: ${total} Ft`].join("\n");
}

describe("renderInvoice", () => {
  const invoice: Invoice = {
    id: "2025-0042",
    issuedAt: new Date("2025-03-01T00:00:00Z"),        // fix dátum: a now() instabil snapshotot adna
    lines: [
      { name: "Billentyűzet", qty: 1, unit: 24990 },
      { name: "Egér", qty: 2, unit: 8990 },
    ],
  };

  it("inline snapshot: a várt kimenet a tesztfájlban, review-ban látható", () => {
    expect(renderInvoice(invoice)).toMatchInlineSnapshot(`
      "Számla #2025-0042 (2025-03-01)
      Billentyűzet   1 x 24990 Ft
      Egér           2 x 8990 Ft
      Összesen: 42970 Ft"
    `);
  });

  it("objektum-snapshot az instabil mezők helyettesítésével", () => {
    const response = { id: crypto.randomUUID(), createdAt: new Date().toISOString(), status: "created" };
    expect(response).toMatchSnapshot({ id: expect.any(String), createdAt: expect.any(String) });
  });
});
```

## Kódlefedettség és mutációs tesztelés
<!-- q: Mit mér a code coverage, és hogyan mutatja meg a mutációs tesztelés a gyenge teszteket? -->
<!-- tags: code coverage, branch coverage, mutation testing, mutmut, stryker, test quality, ci gate -->

A lefedettség (coverage) azt méri, mely sorok/ágak futottak le a tesztek alatt — azt nem, hogy a tesztek *ellenőrzik-e* az eredményt; 100% lefedettség mellett is lehet minden assert gyenge. Az ág-lefedettség (`branch = true`) szigorúbb a sorlefedettségnél, mert az `if` mindkét irányát megköveteli. A *mutációs tesztelés* (mutmut, Stryker, PIT) apró hibákat visz a kódba (`>=` → `>`, `+` → `-`), és megnézi, elbukik-e valamelyik teszt; az életben maradt mutáns hiányzó vagy gyenge tesztet jelez. Coverage-ből CI-kaput érdemes csinálni (ne csökkenjen), a mutációs tesztet pedig a kritikus modulokra futtasd, mert lassú.

```toml
# pyproject.toml
[tool.coverage.run]
branch = true                      # ág-lefedettség: az if mindkét iránya kell
source = ["src"]
omit = ["src/*/migrations/*"]

[tool.coverage.report]
fail_under = 85                    # CI-kapu
show_missing = true
skip_covered = true
exclude_also = ["if TYPE_CHECKING:", "raise NotImplementedError", "@overload"]

[tool.mutmut]
paths_to_mutate = ["src/pricing.py"]
```

```python
def is_adult(age: int) -> bool:
    return age >= 18

def test_is_adult_weak():          # 100% sorlefedettség, mégis gyenge
    assert is_adult(30)
    assert not is_adult(5)
# Az "age > 18" mutáns ÉLETBEN marad: egyik assert sem bukik el rajta.

def test_is_adult_boundary():      # a határérték-teszt megöli a mutánst
    assert is_adult(18)
    assert not is_adult(17)
```

```bash
pytest --cov --cov-report=term-missing --cov-report=xml   # lefedettség + hiányzó sorok
mutmut run && mutmut results                              # életben maradt mutánsok listája
npx stryker run                                           # ugyanez JS/TS projektben
```

## Flaky tesztek okai és javítása
<!-- q: Miért flaky egy teszt és hogyan tegyem determinisztikussá? -->
<!-- tags: flaky tests, nondeterminism, time, randomness, test isolation, waiting, retries, quarantine -->

A flaky teszt ugyanarra a kódra hol átmegy, hol elbukik, és lassan aláássa a bizalmat a CI-ban („biztos csak flaky, futtasd újra”). Leggyakoribb okai: valódi idő és `sleep` használata, nem rögzített véletlen, tesztek közti megosztott állapot és sorrend-függés, rendezetlen gyűjtemények összehasonlítása, aszinkron műveletre való fix idejű várakozás, külső szolgáltatás. A javítás: injektált óra és véletlengenerátor, minden teszt saját adattal, feltételre várás határidővel, véletlen tesztsorrend (pytest-randomly) a rejtett függések felderítésére. Az automatikus újrafuttatás csak átmeneti karantén, nem megoldás.

```python
import random
import time
import pytest

# 1) Idő: injektált óra a valódi helyett
class Token:
    def __init__(self, ttl_s: float, clock=time.monotonic):
        self.clock, self.expires = clock, clock() + ttl_s
    def valid(self) -> bool:
        return self.clock() < self.expires

def test_token_expiry_without_sleep():
    now = [1000.0]
    token = Token(ttl_s=30, clock=lambda: now[0])
    assert token.valid()
    now[0] += 31                         # "időutazás" sleep helyett: gyors és determinisztikus
    assert not token.valid()

# 2) Véletlen: injektált, seedelt generátor
def shuffle_deck(rng: random.Random) -> list[int]:
    deck = list(range(52))
    rng.shuffle(deck)
    return deck

def test_shuffle_is_reproducible():
    assert shuffle_deck(random.Random(7)) == shuffle_deck(random.Random(7))

# 3) Aszinkron eredmény: feltételre várás határidővel, nem fix sleep
def wait_until(predicate, timeout=5.0, interval=0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(interval)
    raise AssertionError(f"a feltétel {timeout} s alatt sem teljesült")

# 4) Rendezetlen gyűjtemény: halmazként vagy rendezve hasonlíts
def test_order_independent_comparison():
    tags = {"b", "a"}
    assert sorted(tags) == ["a", "b"]

# 5) Karantén ismert flaky tesztre (pytest-rerunfailures) — határidővel javítandó!
@pytest.mark.flaky(reruns=2)
def test_external_sandbox_api():
    pytest.skip("külső sandbox nélkül kihagyva")
```

## Aszinkron és konkurens kód tesztelése
<!-- q: Hogyan teszteljek aszinkron és párhuzamos kódot, versenyhelyzeteket? -->
<!-- tags: async testing, pytest-asyncio, concurrency, race condition, semaphore, timeout, asyncio -->

Aszinkron kódhoz a tesztkeretnek is futtatnia kell az eseményhurkot (pytest-asyncio, Vitest/Jest natívan kezeli a Promise-t); a teszt mindig `await`-elje az eredményt, különben az állítások a művelet vége előtt futnak. A konkurenciakorlátot úgy ellenőrizheted, hogy egy fake függvény méri az egyidejűleg futó hívások csúcsát. Versenyhelyzetet úgy tehetsz reprodukálhatóvá, hogy ütemezési pontot (`await asyncio.sleep(0)`) iktatsz a kritikus szakaszba; a sikeres futás nem bizonyítja a szálbiztonságot, ezért a kritikus logikánál a stressz-teszt és a race detektor (Go: `-race`) is kell. Minden várakozásnak legyen időkorlátja, hogy egy beragadt teszt ne fagyassza le a CI-t.

```python
import asyncio
import pytest

class LimitedClient:
    def __init__(self, fetch, max_concurrency: int):
        self.fetch, self.sem = fetch, asyncio.Semaphore(max_concurrency)
    async def get_all(self, urls):
        async def one(url):
            async with self.sem:
                return await self.fetch(url)
        return await asyncio.gather(*(one(u) for u in urls))

@pytest.mark.asyncio                                   # pytest-asyncio plugin
async def test_respects_concurrency_limit():
    in_flight = peak = 0
    async def fake_fetch(url):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)                    # egyidejű hívások csúcsa
        await asyncio.sleep(0.01)
        in_flight -= 1
        return url.upper()
    result = await LimitedClient(fake_fetch, 3).get_all([f"u{i}" for i in range(10)])
    assert result == [f"U{i}" for i in range(10)]      # a gather megőrzi a sorrendet
    assert peak == 3

@pytest.mark.asyncio
async def test_hanging_call_times_out():
    async def hang(_):
        await asyncio.Event().wait()                   # sosem tér vissza
    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.1):               # Python 3.11+
            await LimitedClient(hang, 1).get_all(["x"])

class Counter:
    def __init__(self):
        self.value, self.lock = 0, asyncio.Lock()
    async def unsafe_inc(self):
        v = self.value
        await asyncio.sleep(0)                         # ütemezési pont olvasás és írás között
        self.value = v + 1
    async def safe_inc(self):
        async with self.lock:
            await self.unsafe_inc()

@pytest.mark.asyncio
async def test_lock_prevents_lost_updates():
    c = Counter()
    await asyncio.gather(*(c.unsafe_inc() for _ in range(100)))
    assert c.value < 100                               # a race reprodukálva: elveszett írások
    c.value = 0
    await asyncio.gather(*(c.safe_inc() for _ in range(100)))
    assert c.value == 100
```

## Teljesítmény- és terheléses tesztek k6-tal
<!-- q: Hogyan írjak terheléses tesztet k6-tal és hogyan állítsak be SLO küszöböket? -->
<!-- tags: load testing, performance testing, k6, thresholds, slo, latency percentiles, arrival rate, spike test -->

A terheléses teszt azt méri, hogyan viselkedik a rendszer adott forgalom alatt: késleltetés-percentilisek (p95, p99 — az átlag elfedi a lassú kéréseket), hibaarány és áteresztőképesség. A k6 JavaScriptben írt forgatókönyveket futtat; a `ramping-arrival-rate` executor *nyílt modellt* ad (kérés/másodperc a cél), ami a valós forgalomhoz jobban hasonlít, mint a fix felhasználószám, mert a lassuló szerver nem csökkenti a terhelést. A `thresholds` SLO-kat rögzít: ha sérülnek, a k6 hibakóddal lép ki, így CI-kapu lehet belőle. Éles-szerű környezetben és adatmennyiséggel mérj, és soha ne idegen rendszer ellen engedély nélkül.

```javascript
import http from "k6/http";
import { check, sleep } from "k6";
import { Trend } from "k6/metrics";

const checkoutLatency = new Trend("checkout_latency", true);

export const options = {
  scenarios: {
    ramp: {
      executor: "ramping-arrival-rate",       // nyílt modell: kérés/s a cél
      startRate: 10,
      timeUnit: "1s",
      preAllocatedVUs: 50,
      maxVUs: 300,
      stages: [
        { target: 50, duration: "2m" },       // felfutás
        { target: 50, duration: "5m" },       // tartós terhelés
        { target: 150, duration: "1m" },      // tüske (spike)
        { target: 0, duration: "1m" },        // lecsengés
      ],
    },
  },
  thresholds: {                               // SLO-k: sérülés esetén nem nulla kilépési kód
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<400", "p(99)<1000"],
    checkout_latency: ["p(95)<800"],
  },
};

const BASE = __ENV.BASE_URL || "http://localhost:8080";

export default function () {
  const list = http.get(`${BASE}/api/products?limit=20`, { tags: { name: "products" } });
  check(list, { "200 a terméklistára": (r) => r.status === 200 });

  const res = http.post(`${BASE}/api/checkout`, JSON.stringify({ sku: "KB-01", qty: 1 }), {
    headers: { "Content-Type": "application/json" },
    tags: { name: "checkout" },
  });
  checkoutLatency.add(res.timings.duration);
  check(res, { "checkout 201": (r) => r.status === 201 });
  sleep(Math.random() * 2);                   // felhasználói "gondolkodási idő"
}
```

## Tesztek a CI-ban
<!-- q: Hogyan futtassam a teszteket CI-ban gyorsan és megbízhatóan (GitHub Actions)? -->
<!-- tags: ci, github actions, test automation, matrix, service containers, artifacts, parallel tests -->

A CI minden pull requestnél lefuttatja a teszteket, és a merge feltétele a zöld eredmény; a gyors visszajelzéshez a gyors unit kör fusson először, a lassabb integrációs és E2E jobok csak utána (`needs`) és párhuzamosan. A függőség-cache (`cache: pip`/`npm`), a tesztek párhuzamosítása (`pytest -n auto`, Playwright shardok) és a `concurrency` (az elavult futások leállítása) jelentősen csökkenti a futási időt. A szolgáltatás-konténerek (`services`) valódi adatbázist adnak, a JUnit XML és a Playwright-riport artefaktként megmarad a hibakereséshez. A titkokat (`secrets`) csak azok a jobok kapják meg, amelyeknek kell.

```yaml
name: tests
on:
  pull_request:
  push:
    branches: [main]

concurrency:                              # ugyanarra a branchre az előző futás leáll
  group: tests-${{ github.ref }}
  cancel-in-progress: true

jobs:
  unit:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
          cache: pip
      - run: pip install -e ".[test]"
      - run: pytest -m "not integration and not e2e" -n auto --cov --cov-report=xml --junitxml=junit.xml
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: unit-results-${{ matrix.python }}
          path: junit.xml

  integration:
    needs: unit                           # csak zöld unit kör után
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_PASSWORD: ci-only      # eldobható CI-konténer, nem valódi titok
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s --health-retries 10
    env:
      DATABASE_URL: postgresql://postgres:ci-only@localhost:5432/postgres
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -e ".[test]"
      - run: pytest -m integration

  e2e:
    needs: unit
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - run: npx playwright install --with-deps chromium
      - run: npx playwright test
        env:
          E2E_PASSWORD: ${{ secrets.E2E_PASSWORD }}
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
```
