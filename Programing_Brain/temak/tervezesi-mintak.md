# Tervezési minták és architektúra
<!-- tech: design-patterns -->
<!-- aliases: tervezési minták, design patterns, gof, solid, architektúra, clean architecture, ddd -->

A tervezési minták visszatérő tervezési problémák bevált, megnevezett megoldásai: közös
szókincset adnak, és megmutatják, hol érdemes a változékony részt elválasztani a stabiltól.
Ez a fájl a GoF létrehozási, szerkezeti és viselkedési mintáit modern (funkcionális, típusos)
változatokkal, a SOLID elveket, a dependency injectiont és az alkalmazás-architektúrákat
(repository, CQRS, event sourcing, hexagonális, MVVM) fedi le. Fontos: a minta eszköz, nem cél —
ha a variáció még nem jelent meg, a legegyszerűbb kód a jó kód.

## SOLID: egyetlen felelősség és nyitott/zárt elv
<!-- q: Mit jelent a Single Responsibility és az Open/Closed elv a gyakorlatban? -->
<!-- tags: solid, srp, single responsibility, ocp, open closed, refactoring -->

Az SRP szerint egy modulnak egyetlen oka (egyetlen „szereplő”) legyen a változásra: ha a
számítás, a formázás és a küldés egy osztályban van, egy új exportformátum a számítást is
veszélyezteti. Az OCP szerint a kód legyen bővíthető módosítás nélkül: új viselkedés új
osztály/függvény formájában jöjjön, ne egy egyre hosszabb if/elif láncban. Ezt absztrakcióval
(interfész, Protocol) és injektálással érjük el. Buktató: a túlzott előre-absztrahálás —
a „rule of three” szerint csak a második-harmadik variációnál vezess be absztrakciót.

```python
import json
from dataclasses import dataclass
from typing import Iterable, Protocol

@dataclass(frozen=True)
class Sale:
    product: str
    qty: int
    unit_price: int  # fillérben: pénzhez egész szám

# SRP: csak számol, nem tud formázásról vagy küldésről
class SalesSummary:
    def __init__(self, sales: Iterable[Sale]) -> None:
        self.sales = list(sales)

    def totals(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for s in self.sales:
            out[s.product] = out.get(s.product, 0) + s.qty * s.unit_price
        return out

# OCP: új formátumhoz új osztály, a meglévő kód érintetlen
class Exporter(Protocol):
    def export(self, totals: dict[str, int]) -> str: ...

class CsvExporter:
    def export(self, totals: dict[str, int]) -> str:
        return "\n".join(["product,total"] + [f"{p},{t}" for p, t in sorted(totals.items())])

class JsonExporter:
    def export(self, totals: dict[str, int]) -> str:
        return json.dumps(totals, ensure_ascii=False, sort_keys=True)

class ReportService:
    """Összeköti a részeket; a kimenet módja injektált, nem if/elif lánc."""

    def __init__(self, exporter: Exporter) -> None:
        self.exporter = exporter

    def build(self, sales: Iterable[Sale]) -> str:
        return self.exporter.export(SalesSummary(sales).totals())

if __name__ == "__main__":
    data = [Sale("alma", 3, 12000), Sale("körte", 2, 20000), Sale("alma", 1, 12000)]
    for exp in (CsvExporter(), JsonExporter()):
        print(ReportService(exp).build(data))
```

## SOLID: Liskov-helyettesítés, interfész-szétválasztás, függőségmegfordítás
<!-- q: Mit jelent az LSP, az ISP és a DIP, és hogyan néz ki kódban? -->
<!-- tags: solid, lsp, liskov, isp, interface segregation, dip, dependency inversion -->

Az LSP szerint az altípus mindenhol használható kell legyen, ahol az őse: nem szigoríthatja az
előfeltételeket és nem gyengítheti az ígéreteket (a klasszikus hiba: a Négyzet extends Téglalap,
ahol a setWidth a magasságot is átírja). Az ISP kicsi, szerepkör-alapú interfészeket kér, hogy
egy kliens ne függjön olyan metódustól, amit nem használ. A DIP szerint a magas szintű szabályok
absztrakciótól függjenek, a konkrét tároló/hálózat pedig ezt az absztrakciót valósítsa meg —
így a részlet cserélhető és tesztben helyettesíthető. Változtathatatlan objektumok sok
LSP-problémát eleve megszüntetnek.

```typescript
// --- LSP: változtathatatlan alakzatok közös interfésszel, nincs "meglepő" setter ---
interface Shape {
  area(): number;
}
class Rect implements Shape {
  constructor(readonly w: number, readonly h: number) {}
  area(): number { return this.w * this.h; }
  withWidth(w: number): Rect { return new Rect(w, this.h); } // új példány, nincs rejtett mellékhatás
}
class Square implements Shape {
  constructor(readonly side: number) {}
  area(): number { return this.side ** 2; }
}

// --- ISP: kicsi szerepkör-interfészek egy "mindent tudó" helyett ---
interface Reader { read(key: string): Promise<string | undefined>; }
interface Writer { write(key: string, value: string): Promise<void>; }

// --- DIP: a szabály absztrakciótól függ, nem konkrét tárolótól ---
class FeatureFlags {
  constructor(private readonly store: Reader) {} // csak olvas: csak Reader-t kér
  async isEnabled(flag: string): Promise<boolean> {
    return (await this.store.read(`flag:${flag}`)) === "on";
  }
}
class AdminConsole {
  constructor(private readonly store: Reader & Writer) {} // itt mindkettő kell
  async toggle(flag: string): Promise<void> {
    const cur = await this.store.read(`flag:${flag}`);
    await this.store.write(`flag:${flag}`, cur === "on" ? "off" : "on");
  }
}

// Alacsony szintű részlet: cserélhető Redisre, fájlra; tesztben memória
class MemoryStore implements Reader, Writer {
  private data = new Map<string, string>();
  async read(key: string) { return this.data.get(key); }
  async write(key: string, value: string) { this.data.set(key, value); }
}

async function main(): Promise<void> {
  const store = new MemoryStore();
  await new AdminConsole(store).toggle("dark-mode");
  console.log(await new FeatureFlags(store).isEnabled("dark-mode")); // true
  const shapes: Shape[] = [new Rect(2, 3).withWidth(4), new Square(3)];
  console.log(shapes.map((s) => s.area())); // [ 12, 9 ]
}
main();
```

## Dependency injection és a composition root
<!-- q: Mi a dependency injection, és hogyan használjam konténer nélkül? -->
<!-- tags: dependency injection, di, ioc, composition root, constructor injection, testing -->

DI esetén egy objektum nem maga hozza létre a függőségeit (adatbázis, óra, e-mail küldő), hanem
kívülről kapja meg, jellemzően a konstruktorban. Ettől lesz tesztelhető (hamis óra, memóriás
repository) és cserélhető a konfiguráció. A konkrét típusokat egyetlen helyen, a composition
rootban (main) drótozzuk össze; a DI-konténerek (Spring, .NET, NestJS) ezt automatizálják, de
elrejtik a függőségi gráfot. Buktatók: a Service Locator (globális „add ide a X-et”) rejtett
függőség — anti-minta; a 6+ konstruktorparaméter SRP-sértésre utal.

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"time"
)

// Go-idióma: az interfészt a FOGYASZTÓ oldalon, minimálisra szabva definiáljuk
type UserRepo interface {
	FindEmail(ctx context.Context, id int) (string, error)
}
type Mailer interface {
	Send(ctx context.Context, to, subject, body string) error
}
type Clock interface{ Now() time.Time }

// Minden függőség a konstruktorban érkezik: nincs globális állapot
type ReminderService struct {
	users  UserRepo
	mailer Mailer
	clock  Clock
}

func NewReminderService(u UserRepo, m Mailer, c Clock) *ReminderService {
	return &ReminderService{users: u, mailer: m, clock: c}
}

func (s *ReminderService) Remind(ctx context.Context, userID int) error {
	email, err := s.users.FindEmail(ctx, userID)
	if err != nil {
		return fmt.Errorf("remind %d: %w", userID, err)
	}
	day := s.clock.Now().Format("2006-01-02") // injektált óra => determinisztikus teszt
	return s.mailer.Send(ctx, email, "Emlékeztető", "Mai dátum: "+day)
}

// --- Egyszerű implementációk (élesben adatbázis és SMTP) ---
type memRepo map[int]string

func (m memRepo) FindEmail(_ context.Context, id int) (string, error) {
	if e, ok := m[id]; ok {
		return e, nil
	}
	return "", errors.New("nincs ilyen felhasználó")
}

type consoleMailer struct{}

func (consoleMailer) Send(_ context.Context, to, subject, body string) error {
	fmt.Printf("to=%s subject=%s body=%s\n", to, subject, body)
	return nil
}

type fixedClock struct{ t time.Time }

func (c fixedClock) Now() time.Time { return c.t }

// Composition root: az egyetlen hely, ahol konkrét típusokat választunk
func main() {
	svc := NewReminderService(
		memRepo{1: "user@example.com"},
		consoleMailer{},
		fixedClock{time.Date(2025, 1, 2, 0, 0, 0, 0, time.UTC)},
	)
	if err := svc.Remind(context.Background(), 1); err != nil {
		fmt.Println("hiba:", err)
	}
}
```

## Factory Method és regisztrációs gyár
<!-- q: Mikor használjak factory mintát, és hogyan bővíthető módosítás nélkül? -->
<!-- tags: factory method, simple factory, registry, creational pattern, plugin -->

A gyár elrejti, melyik konkrét osztály példányosul: a hívó csak az absztrakciót ismeri, a típus
pedig futásidőben (konfigurációból, felhasználói választásból) dől el. A GoF Factory Method
alosztályra bízza a termék kiválasztását; modern kódban gyakoribb a regisztrációs gyár, ahol az
új implementáció saját magát regisztrálja, így a gyár kódja sosem változik (plugin-rendszerek).
Pythonban gyakran egy egyszerű dict-of-callables is elég; ne vezess be gyárat, ha csak egyetlen
implementáció van.

```python
from abc import ABC, abstractmethod
from typing import Callable, ClassVar

class Notifier(ABC):
    @abstractmethod
    def send(self, to: str, msg: str) -> None: ...

class NotifierFactory:
    """Regisztrációs gyár: új típushoz nem kell a gyárat módosítani (OCP)."""

    _registry: ClassVar[dict[str, Callable[..., Notifier]]] = {}

    @classmethod
    def register(cls, kind: str) -> Callable[[type[Notifier]], type[Notifier]]:
        def deco(klass: type[Notifier]) -> type[Notifier]:
            if kind in cls._registry:
                raise ValueError(f"már regisztrált típus: {kind}")
            cls._registry[kind] = klass
            return klass

        return deco

    @classmethod
    def create(cls, kind: str, **config: object) -> Notifier:
        try:
            ctor = cls._registry[kind]
        except KeyError:
            raise ValueError(f"ismeretlen típus: {kind}; elérhető: {sorted(cls._registry)}") from None
        return ctor(**config)

@NotifierFactory.register("email")
class EmailNotifier(Notifier):
    def __init__(self, sender: str = "noreply@example.com") -> None:
        self.sender = sender

    def send(self, to: str, msg: str) -> None:
        print(f"[email {self.sender} -> {to}] {msg}")

@NotifierFactory.register("sms")
class SmsNotifier(Notifier):
    def __init__(self, max_len: int = 160) -> None:
        self.max_len = max_len

    def send(self, to: str, msg: str) -> None:
        print(f"[sms -> {to}] {msg[: self.max_len]}")

if __name__ == "__main__":
    # A típus konfigurációból jön; a hívó csak a Notifier absztrakciót látja
    for kind, cfg in (("email", {}), ("sms", {"max_len": 10})):
        NotifierFactory.create(kind, **cfg).send("felhasznalo", "A rendelésed elkészült")
```

## Abstract Factory: összetartozó objektumcsaládok
<!-- q: Mi a különbség a Factory Method és az Abstract Factory között? -->
<!-- tags: abstract factory, creational pattern, product family, infrastructure, environment -->

Az Abstract Factory egy egész családnyi, együtt használandó objektumot hoz létre (pl. helyi vs.
felhős tároló + üzenetsor, vagy egy UI-téma összes komponense), így kizárja, hogy összeférhetetlen
darabok keveredjenek. A Factory Method egyetlen terméket gyárt, az Abstract Factory több,
egymáshoz illő terméket egy interfész mögött. Tipikus haszna a környezetfüggő infrastruktúra
(dev/test/prod). Buktató: új terméktípus felvétele minden konkrét gyárat érinti — ha a család
gyakran bővül, ez a minta merev.

```typescript
// Abstract Factory: EGYÜTT használandó objektumok családja egy interfész mögött
interface BlobStore {
  put(key: string, data: Uint8Array): Promise<string>; // visszaadja az elérési URL-t
}
interface JobQueue {
  enqueue(job: { type: string; payload: unknown }): Promise<void>;
}
interface InfraFactory {
  blobStore(): BlobStore;
  jobQueue(): JobQueue;
}

// --- Helyi fejlesztői család ---
class LocalBlobStore implements BlobStore {
  private files = new Map<string, Uint8Array>();
  async put(key: string, data: Uint8Array) {
    this.files.set(key, data);
    return `file:///tmp/blobs/${key}`;
  }
}
class InMemoryQueue implements JobQueue {
  readonly jobs: unknown[] = [];
  async enqueue(job: { type: string; payload: unknown }) { this.jobs.push(job); }
}
class LocalInfra implements InfraFactory {
  blobStore() { return new LocalBlobStore(); }
  jobQueue() { return new InMemoryQueue(); }
}

// --- Felhős család (itt csak naplóz; élesben SDK-hívások) ---
class CloudBlobStore implements BlobStore {
  constructor(private bucket: string) {}
  async put(key: string, _data: Uint8Array) {
    return `https://${this.bucket}.storage.example.com/${key}`;
  }
}
class CloudQueue implements JobQueue {
  constructor(private queueName: string) {}
  async enqueue(job: { type: string; payload: unknown }) {
    console.log(`[${this.queueName}] küldve:`, job.type);
  }
}
class CloudInfra implements InfraFactory {
  constructor(private env: { bucket: string; queue: string }) {}
  blobStore() { return new CloudBlobStore(this.env.bucket); }
  jobQueue() { return new CloudQueue(this.env.queue); }
}

// A kliens kód csak az absztrakt gyárat ismeri
async function uploadAvatar(infra: InfraFactory, userId: string, img: Uint8Array) {
  const url = await infra.blobStore().put(`avatars/${userId}.png`, img);
  await infra.jobQueue().enqueue({ type: "thumbnail", payload: { url } });
  return url;
}

// A család kiválasztása egyetlen helyen, a környezet alapján
const infra: InfraFactory =
  process.env.NODE_ENV === "production"
    ? new CloudInfra({ bucket: "app-media", queue: "media-jobs" })
    : new LocalInfra();
uploadAvatar(infra, "u42", new Uint8Array([1, 2, 3])).then(console.log);
```

## Builder: sok opcionális paraméter, érvényes objektum
<!-- q: Mikor érdemes builder mintát használni? -->
<!-- tags: builder, fluent interface, creational pattern, validation, rust, typestate -->

A Builder lépésenként, olvasható láncolással állít össze egy összetett objektumot, és a
`build()` egyetlen helyen ellenőrzi az invariánsokat — így a kész objektum mindig érvényes, és
nem kell 8 paraméteres konstruktor („telescoping constructor”). Rustban a builder az idiomatikus
megoldás a hiányzó nevesített/alapértelmezett paraméterekre; a typestate változat (a builder
típusa kódolja, mi van már beállítva) fordítási időben tiltja a hiányos buildet. Pythonban és
Kotlinban a nevesített argumentumok és a dataclass sokszor feleslegessé teszik.

```rust
use std::time::Duration;

#[derive(Debug)]
pub struct HttpRequest {
    method: String,
    url: String,
    headers: Vec<(String, String)>,
    body: Option<Vec<u8>>,
    timeout: Duration,
    retries: u8,
}

/// Builder: opcionális mezők, láncolható beállítók, validálás a build()-ben
#[derive(Default)]
pub struct HttpRequestBuilder {
    method: Option<String>,
    url: Option<String>,
    headers: Vec<(String, String)>,
    body: Option<Vec<u8>>,
    timeout: Option<Duration>,
    retries: u8,
}

impl HttpRequestBuilder {
    pub fn new(url: impl Into<String>) -> Self {
        Self { url: Some(url.into()), ..Default::default() }
    }
    // self-et érték szerint kapjuk és adjuk vissza: láncolható, nincs klónozás
    pub fn method(mut self, m: &str) -> Self { self.method = Some(m.to_uppercase()); self }
    pub fn header(mut self, k: &str, v: &str) -> Self { self.headers.push((k.into(), v.into())); self }
    pub fn json_body(mut self, json: &str) -> Self {
        self.body = Some(json.as_bytes().to_vec());
        self.header("Content-Type", "application/json")
    }
    pub fn timeout(mut self, t: Duration) -> Self { self.timeout = Some(t); self }
    pub fn retries(mut self, n: u8) -> Self { self.retries = n; self }

    /// Az invariánsok egy helyen: a kész objektum mindig érvényes
    pub fn build(self) -> Result<HttpRequest, String> {
        let url = self.url.ok_or("hiányzó URL")?;
        if !url.starts_with("http://") && !url.starts_with("https://") {
            return Err(format!("érvénytelen séma: {url}"));
        }
        let method = self.method.unwrap_or_else(|| "GET".to_string());
        if method == "GET" && self.body.is_some() {
            return Err("GET kérésnek nem lehet törzse".into());
        }
        Ok(HttpRequest {
            method,
            url,
            headers: self.headers,
            body: self.body,
            timeout: self.timeout.unwrap_or(Duration::from_secs(30)),
            retries: self.retries.min(5), // ésszerű felső korlát
        })
    }
}

fn main() {
    let req = HttpRequestBuilder::new("https://api.example.com/orders")
        .method("post")
        .header("Accept", "application/json")
        .json_body(r#"{"item":"book","qty":2}"#)
        .timeout(Duration::from_secs(5))
        .retries(3)
        .build();
    println!("{req:?}");
    println!("{:?}", HttpRequestBuilder::new("ftp://x").build().unwrap_err());
}
```

## Singleton és jobb alternatívái
<!-- q: Hogyan írjak szálbiztos singletont, és miért kerüljem inkább? -->
<!-- tags: singleton, lazy initialization, thread safety, holder idiom, global state, di -->

A Singleton garantálja, hogy egy osztályból egyetlen példány létezzen, globális hozzáféréssel.
Ha mégis kell, Javában az enum vagy a lusta „holder” idióma a szálbiztos megoldás (a JVM
osztálybetöltése szinkronizál), nem a hibásan írt double-checked locking. A gond a globális
állapot: rejtett függőség, tesztek között szivárgó állapot, nehéz mockolás. Jobb megoldás:
egyetlen példányt a composition rootban létrehozni és injektálni — az „egy legyen belőle” a
konfiguráció döntése, ne az osztályé.

```java
import java.util.concurrent.atomic.AtomicLong;

// 1) Enum singleton: szálbiztos, szerializáció- és reflexióbiztos
enum IdGenerator {
    INSTANCE;
    private final AtomicLong next = new AtomicLong(1);
    public long nextId() { return next.getAndIncrement(); }
}

// 2) Lusta inicializálás holder idiómával: az osztálybetöltés garantálja a szálbiztosságot
final class AppConfig {
    private final String dbUrl;
    private AppConfig() {
        this.dbUrl = System.getenv().getOrDefault("DB_URL", "jdbc:h2:mem:dev");
    }
    private static final class Holder {
        static final AppConfig INSTANCE = new AppConfig(); // első get() hívásakor jön létre
    }
    static AppConfig get() { return Holder.INSTANCE; }
    String dbUrl() { return dbUrl; }
}

// 3) Ajánlott: egy példány, de injektálva — tesztben cserélhető
interface Clock { long millis(); }
final class SystemClock implements Clock {
    public long millis() { return System.currentTimeMillis(); }
}

final class SessionService {
    private final Clock clock;
    SessionService(Clock clock) { this.clock = clock; }
    boolean expired(long createdAt, long ttlMs) { return clock.millis() - createdAt > ttlMs; }
}

public class SingletonDemo {
    public static void main(String[] args) {
        System.out.println(IdGenerator.INSTANCE.nextId() + ", " + IdGenerator.INSTANCE.nextId());
        System.out.println(AppConfig.get().dbUrl());
        Clock fixed = () -> 10_000L; // tesztben rögzített idő lambdával
        System.out.println(new SessionService(fixed).expired(0, 5_000)); // true
        SessionService real = new SessionService(new SystemClock()); // élesben egy példány a mainben
        System.out.println(real.expired(System.currentTimeMillis(), 5_000)); // false
    }
}
```

## Adapter: idegen API a saját interfészünk mögött
<!-- q: Hogyan illesszek be egy külső könyvtárat úgy, hogy ne szivárogjon szét a kódban? -->
<!-- tags: adapter, wrapper, anti-corruption layer, structural pattern, legacy integration -->

Az Adapter egy meglévő, nem módosítható API-t (külső SDK, régi rendszer) a saját, általunk
tervezett interfészre fordít: neveket, típusokat, mértékegységeket és a hibamodellt. Így a
külső függőség egyetlen osztályba zárul („anti-corruption layer”), cseréje vagy verzióváltása
nem érinti az üzleti kódot, és tesztben a saját interfész könnyen mockolható. Buktató: ne
szivárogjanak át a külső típusok (pl. SDK-specifikus kivételek, DTO-k) az adapter felületén.

```typescript
// Az alkalmazás saját interfésze (port)
export interface PaymentGateway {
  charge(input: { amountCents: number; currency: "HUF" | "EUR"; token: string }): Promise<{ id: string }>;
}

// Külső, nem módosítható SDK: callbackes, más nevek, más mértékegység
type LegacyCallback = (err: { code: number; msg: string } | null, res?: { txn_ref: string }) => void;
class LegacyPayClient {
  makePayment(amountMajor: number, curr: string, cardToken: string, cb: LegacyCallback): void {
    setTimeout(() => {
      if (cardToken.startsWith("bad")) cb({ code: 402, msg: "card declined" });
      else cb(null, { txn_ref: `T-${Date.now()}-${curr}-${amountMajor}` });
    }, 10);
  }
}

export class PaymentDeclinedError extends Error {}

// Adapter: callback -> Promise, cent -> egész egység, külső hibakód -> domain-hiba
export class LegacyPayAdapter implements PaymentGateway {
  constructor(private readonly client: LegacyPayClient) {}

  charge(input: { amountCents: number; currency: "HUF" | "EUR"; token: string }): Promise<{ id: string }> {
    return new Promise((resolve, reject) => {
      this.client.makePayment(input.amountCents / 100, input.currency, input.token, (err, res) => {
        if (err) {
          reject(err.code === 402 ? new PaymentDeclinedError(err.msg) : new Error(`gateway ${err.code}: ${err.msg}`));
        } else if (!res) {
          reject(new Error("üres válasz a fizetési szolgáltatótól"));
        } else {
          resolve({ id: res.txn_ref }); // a külső mezőnév nem szivárog ki
        }
      });
    });
  }
}

async function checkout(gw: PaymentGateway): Promise<void> {
  try {
    const { id } = await gw.charge({ amountCents: 129900, currency: "HUF", token: "tok_ok" });
    console.log("sikeres fizetés:", id);
    await gw.charge({ amountCents: 500, currency: "EUR", token: "bad_tok" });
  } catch (e) {
    console.log(e instanceof PaymentDeclinedError ? "elutasítva:" : "egyéb hiba:", (e as Error).message);
  }
}
checkout(new LegacyPayAdapter(new LegacyPayClient()));
```

## Decorator és middleware-lánc
<!-- q: Hogyan adjak viselkedést egy komponenshez a módosítása nélkül? -->
<!-- tags: decorator, middleware, http handler, structural pattern, cross-cutting concerns -->

A Decorator ugyanazt az interfészt valósítja meg, mint a becsomagolt objektum, és előtte/utána
extra viselkedést futtat; tetszőleges sorrendben egymásba ágyazható. Modern formája a HTTP
middleware: naplózás, hitelesítés, pánikkezelés, rate limit — keresztmetszeti feladatok, amik
így nem szennyezik az üzleti handlert. A sorrend számít (pl. a recover legyen kívül, hogy a
többi réteg pánikját is elkapja). Buktató: a túl mély lánc nehezen debugolható, és a
becsomagolt ResponseWriter elrejtheti az opcionális interfészeket (Flusher, Hijacker).

```go
package main

import (
	"crypto/subtle"
	"log"
	"net/http"
	"time"
)

// Middleware = dekorátor: http.Handler-t kap és http.Handler-t ad vissza
type Middleware func(http.Handler) http.Handler

type statusRecorder struct { // elkapja a státuszkódot a naplózáshoz
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(code int) {
	r.status = code
	r.ResponseWriter.WriteHeader(code)
}

func Logging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)
		log.Printf("%s %s %d %v", r.Method, r.URL.Path, rec.status, time.Since(start))
	})
}

func Recover(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if err := recover(); err != nil { // egy pánik ne döntse le a szervert
				log.Printf("panic: %v", err)
				http.Error(w, "belső hiba", http.StatusInternalServerError)
			}
		}()
		next.ServeHTTP(w, r)
	})
}

func RequireAPIKey(valid string) Middleware { // paraméterezett dekorátor
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			got := r.Header.Get("X-API-Key")
			if subtle.ConstantTimeCompare([]byte(got), []byte(valid)) != 1 { // időzítéses támadás ellen
				http.Error(w, "unauthorized", http.StatusUnauthorized)
				return // rövidzár: a belső handler nem fut
			}
			next.ServeHTTP(w, r)
		})
	}
}

// Chain: az első middleware lesz a legkülső réteg
func Chain(h http.Handler, mws ...Middleware) http.Handler {
	for i := len(mws) - 1; i >= 0; i-- {
		h = mws[i](h)
	}
	return h
}

func main() {
	hello := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("szia\n"))
	})
	// A kulcs élesben környezeti változóból/secret store-ból jön; ez csak helykitöltő
	http.Handle("/hello", Chain(hello, Recover, Logging, RequireAPIKey("dev-placeholder-key")))
	log.Fatal(http.ListenAndServe(":8080", nil))
}
```

## Proxy és Facade
<!-- q: Mi a különbség a Proxy, a Decorator és a Facade között? -->
<!-- tags: proxy, facade, caching proxy, lazy loading, structural pattern, subsystem -->

A Proxy ugyanazt az interfészt adja, mint a valódi objektum, de a hozzáférést szabályozza:
gyorsítótáraz, lustán tölt be, jogosultságot ellenőriz vagy távoli hívást rejt el (RPC stub,
ORM lazy loading). Szerkezetileg azonos a Decoratorral, a szándék más: a proxy a hozzáférést
kezeli, a decorator funkciót ad hozzá. A Facade ezzel szemben új, egyszerűbb interfészt ad egy
bonyolult alrendszer fölé, hogy a kliensnek ne kelljen ismernie a részleteit. Buktató: a
cache-proxynál gondold végig az érvénytelenítést és a többszálú hozzáférést.

```python
import time
from typing import Protocol

class WeatherService(Protocol):
    def forecast(self, city: str) -> dict: ...

class RemoteWeather:
    """Valódi szolgáltatás: lassú hálózati hívás (itt szimulálva)."""

    def forecast(self, city: str) -> dict:
        time.sleep(0.2)
        return {"city": city, "temp_c": 21}

class CachingWeatherProxy:
    """Proxy: ugyanaz az interfész, de TTL-es cache-sel szabályozza a hozzáférést."""

    def __init__(self, real: WeatherService, ttl_s: float = 60.0) -> None:
        self._real = real
        self._ttl = ttl_s
        self._cache: dict[str, tuple[float, dict]] = {}

    def forecast(self, city: str) -> dict:
        now = time.monotonic()  # monoton óra: a rendszeridő átállítása nem zavarja
        hit = self._cache.get(city)
        if hit and now - hit[0] < self._ttl:
            return hit[1]
        result = self._real.forecast(city)
        self._cache[city] = (now, result)
        return result

class TripPlannerFacade:
    """Facade: egyszerű belépési pont több alrendszer fölé."""

    def __init__(self, weather: WeatherService) -> None:
        self.weather = weather

    def plan(self, city: str) -> str:
        fc = self.weather.forecast(city)
        # élesben itt jönne a szállásfoglalás, útvonaltervezés, fizetés is
        advice = "rövid ujjú" if fc["temp_c"] > 18 else "kabát"
        return f"{city}: {fc['temp_c']} °C, javaslat: {advice}"

if __name__ == "__main__":
    planner = TripPlannerFacade(CachingWeatherProxy(RemoteWeather(), ttl_s=30))
    t0 = time.perf_counter()
    planner.plan("Budapest")
    print(planner.plan("Budapest"))  # a második hívás már a cache-ből jön
    print(f"{time.perf_counter() - t0:.2f} s")  # ~0.20 s, nem 0.40 s
```

## Composite: fa-szerkezetek egységes kezelése
<!-- q: Hogyan kezeljem egységesen az egyedi elemeket és a csoportjaikat? -->
<!-- tags: composite, tree structure, recursion, structural pattern, file system, ui tree -->

A Composite-ban a levél és az összetett csomópont ugyanazt az interfészt valósítja meg, így a
kliens rekurzív szerkezeteket (fájlrendszer, UI-komponensfa, szervezeti ábra, árazott csomagok)
anélkül kezel, hogy tudná, egy elemmel vagy egy csoporttal van dolga. A műveletek a csoportban
rekurzívan delegálódnak a gyerekekre. Buktatók: a gyerekkezelő metódusok (add/remove) ne
kerüljenek a levél interfészébe; mély fáknál a rekurzív aggregálás (pl. méret) drága lehet —
ilyenkor gyorsítótárazás és érvénytelenítés kell.

```typescript
// Composite: levél és csoport ugyanazt az interfészt valósítja meg
interface FsNode {
  readonly name: string;
  size(): number;
  render(indent?: string): string;
}

class FileNode implements FsNode {
  constructor(readonly name: string, private readonly bytes: number) {}
  size(): number { return this.bytes; }
  render(indent = ""): string { return `${indent}${this.name} (${this.bytes} B)`; }
}

class DirNode implements FsNode {
  private readonly children: FsNode[] = [];
  constructor(readonly name: string) {}

  add(...nodes: FsNode[]): this { // láncolható
    this.children.push(...nodes);
    return this;
  }
  // Rekurzív delegálás: a hívó nem tudja, levél-e vagy mappa
  size(): number {
    return this.children.reduce((sum, c) => sum + c.size(), 0);
  }
  render(indent = ""): string {
    const lines = [`${indent}${this.name}/ (${this.size()} B)`];
    for (const c of this.children) lines.push(c.render(indent + "  "));
    return lines.join("\n");
  }
  // Generátoros bejárás: útvonal + csomópont párok
  *walk(path = ""): Generator<[string, FsNode]> {
    for (const c of this.children) {
      const p = `${path}/${c.name}`;
      yield [p, c];
      if (c instanceof DirNode) yield* c.walk(p);
    }
  }
}

const root = new DirNode("projekt").add(
  new FileNode("README.md", 1200),
  new DirNode("src").add(new FileNode("main.ts", 5400), new FileNode("util.ts", 800)),
  new DirNode("assets").add(new FileNode("logo.png", 20480)),
);
console.log(root.render());
const big = [...root.walk()]
  .filter(([, n]) => n instanceof FileNode && n.size() > 1000)
  .map(([p]) => p);
console.log(big); // [ '/README.md', '/src/main.ts', '/assets/logo.png' ]
```

## Strategy vs. State
<!-- q: Mi a különbség a Strategy és a State minta között? -->
<!-- tags: strategy, state, state machine, behavioral pattern, polymorphism, first-class functions -->

Mindkettő egy cserélhető objektumra delegál, a különbség a szándékban van: a Strategy-t a hívó
választja ki (pl. árazási szabály), a stratégiák nem tudnak egymásról; a State-nél az objektum
maga váltja az állapotát, és minden állapot tudja, milyen átmenetek engedélyezettek. Funkcionális
nyelvekben a stratégia egyszerűen egy függvény. A State kiváltja az állapotokra írt if/elif
láncokat, és az érvénytelen átmeneteket egy helyen tiltja; Rustban/TypeScriptben gyakran
enum + exhaustív match vagy typestate a tisztább megoldás.

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

# --- STRATEGY: a hívó választja; Pythonban egy függvény is elég ---
PricingStrategy = Callable[[int], int]

def regular(total: int) -> int:
    return total

def black_friday(total: int) -> int:
    return total * 70 // 100

def loyalty(points: int) -> PricingStrategy:
    return lambda total: max(0, total - points * 50)  # paraméterezett stratégia closure-rel

# --- STATE: az állapot maga dönti el, mi következhet ---
class OrderState:
    name = "abstract"

    def pay(self, o: Order) -> None:
        raise RuntimeError(f"'{self.name}' állapotban nem lehet fizetni")

    def ship(self, o: Order) -> None:
        raise RuntimeError(f"'{self.name}' állapotban nem lehet szállítani")

    def cancel(self, o: Order) -> None:
        raise RuntimeError(f"'{self.name}' állapotban nem lehet lemondani")

class New(OrderState):
    name = "new"
    def pay(self, o: Order) -> None: o.state = Paid()
    def cancel(self, o: Order) -> None: o.state = Cancelled()

class Paid(OrderState):
    name = "paid"
    def ship(self, o: Order) -> None: o.state = Shipped()

    def cancel(self, o: Order) -> None:
        o.refund_due = True  # állapotfüggő mellékhatás
        o.state = Cancelled()

class Shipped(OrderState):
    name = "shipped"

class Cancelled(OrderState):
    name = "cancelled"

@dataclass
class Order:
    items_total: int
    pricing: PricingStrategy = regular
    state: OrderState = field(default_factory=New)
    refund_due: bool = False

    def price(self) -> int:
        return self.pricing(self.items_total)

    # A kontextus delegál; nincs if/elif lánc az állapotokra
    def pay(self) -> None: self.state.pay(self)
    def ship(self) -> None: self.state.ship(self)
    def cancel(self) -> None: self.state.cancel(self)

if __name__ == "__main__":
    o = Order(10_000, pricing=black_friday)
    print(o.price(), o.state.name)  # 7000 new
    o.pay()
    o.cancel()
    print(o.state.name, o.refund_due)  # cancelled True
    try:
        o.ship()
    except RuntimeError as e:
        print(e)
```

## Observer vs. Publish/Subscribe
<!-- q: Mi a különbség az observer minta és a pub/sub között? -->
<!-- tags: observer, pub/sub, event emitter, message broker, decoupling, reactive -->

Az Observernél a subject közvetlenül ismeri a feliratkozóit, és általában szinkron, ugyanabban a
folyamatban értesíti őket (UI-állapot, reaktív változók). A Pub/Sub-nál egy közvetítő (broker,
event bus, Kafka) választja szét a feleket: a kiadó csak egy témára publikál, nem tudja, ki és
hányan kapják meg, a kézbesítés jellemzően aszinkron, akár folyamatok között. Buktatók: el nem
távolított feliratkozók memóriaszivárgást okoznak (mindig adj vissza leiratkozó függvényt), egy
hibás feliratkozó ne állítsa meg a többit, és aszinkron kézbesítésnél a sorrend és a
kézbesítési garancia külön tervezést igényel.

```typescript
// --- OBSERVER: a subject ismeri a feliratkozóit, szinkron értesít ---
type Listener<T> = (value: T) => void;

class Observable<T> {
  private listeners = new Set<Listener<T>>();
  constructor(private value: T) {}
  subscribe(fn: Listener<T>): () => void {
    this.listeners.add(fn);
    return () => { this.listeners.delete(fn); }; // leiratkozás: szivárgás ellen
  }
  set(v: T): void {
    if (Object.is(v, this.value)) return; // nincs változás, nincs értesítés
    this.value = v;
    for (const fn of [...this.listeners]) fn(v); // másolaton iterálunk: közbeni leiratkozás biztonságos
  }
  get(): T { return this.value; }
}

// --- PUB/SUB: a broker választja szét a feleket; témák, aszinkron kézbesítés ---
type Handler = (payload: unknown) => void | Promise<void>;

class Broker {
  private topics = new Map<string, Set<Handler>>();
  subscribe(topic: string, h: Handler): () => void {
    if (!this.topics.has(topic)) this.topics.set(topic, new Set());
    this.topics.get(topic)!.add(h);
    return () => { this.topics.get(topic)?.delete(h); };
  }
  // A kiadó nem tudja, kik kapják meg; egy hibás feliratkozó nem állítja meg a többit
  publish(topic: string, payload: unknown): void {
    for (const h of this.topics.get(topic) ?? []) {
      queueMicrotask(async () => {
        try {
          await h(payload);
        } catch (e) {
          console.error(`[${topic}] feliratkozói hiba:`, (e as Error).message);
        }
      });
    }
  }
}

const cartCount = new Observable(0);
const unsubscribe = cartCount.subscribe((n) => console.log("kosár ikon:", n));
cartCount.set(2);
unsubscribe();
cartCount.set(3); // már nem ír ki semmit

const bus = new Broker();
bus.subscribe("order.created", (p) => console.log("e-mail küldése:", p));
bus.subscribe("order.created", () => { throw new Error("analitika leállt"); });
bus.publish("order.created", { orderId: 17 });
console.log("a publish nem blokkol"); // ez íródik ki előbb
```

## Command: visszavonás és újrajátszás
<!-- q: Hogyan implementáljak undo/redo funkciót? -->
<!-- tags: command pattern, undo, redo, history, behavioral pattern, macro -->

A Command egy műveletet objektumként csomagol be (mit, min, milyen paraméterekkel), így a
művelet tárolható, sorba állítható, naplózható, később futtatható és visszavonható. Az undo/redo
két veremmel működik: végrehajtáskor az undo-verembe kerül, visszavonáskor a redo-verembe; új
művelet után a redo-ág érvénytelen. A visszavonáshoz a parancsnak el kell mentenie, amit
felülír (pl. a törölt szöveget). Alternatíva a memento (állapot-pillanatkép), ami egyszerűbb, de
nagy állapotnál memóriaigényes.

```python
from collections import deque
from dataclasses import dataclass
from typing import Protocol

class Command(Protocol):
    def execute(self) -> None: ...
    def undo(self) -> None: ...

class Document:
    def __init__(self) -> None:
        self.text = ""

@dataclass
class InsertText:
    doc: Document
    pos: int
    s: str

    def execute(self) -> None:
        self.doc.text = self.doc.text[: self.pos] + self.s + self.doc.text[self.pos :]

    def undo(self) -> None:
        self.doc.text = self.doc.text[: self.pos] + self.doc.text[self.pos + len(self.s) :]

@dataclass
class DeleteText:
    doc: Document
    pos: int
    length: int
    removed: str = ""  # a visszavonáshoz elmentjük, mit töröltünk

    def execute(self) -> None:
        self.removed = self.doc.text[self.pos : self.pos + self.length]
        self.doc.text = self.doc.text[: self.pos] + self.doc.text[self.pos + self.length :]

    def undo(self) -> None:
        self.doc.text = self.doc.text[: self.pos] + self.removed + self.doc.text[self.pos :]

class History:
    def __init__(self, limit: int = 100) -> None:
        self.undo_stack: deque[Command] = deque(maxlen=limit)  # a legrégebbi automatikusan kiesik
        self.redo_stack: list[Command] = []

    def run(self, cmd: Command) -> None:
        cmd.execute()
        self.undo_stack.append(cmd)
        self.redo_stack.clear()  # új művelet után a redo-ág érvénytelen

    def undo(self) -> None:
        if self.undo_stack:
            cmd = self.undo_stack.pop()
            cmd.undo()
            self.redo_stack.append(cmd)

    def redo(self) -> None:
        if self.redo_stack:
            cmd = self.redo_stack.pop()
            cmd.execute()
            self.undo_stack.append(cmd)

if __name__ == "__main__":
    doc, h = Document(), History()
    h.run(InsertText(doc, 0, "Helló világ"))
    h.run(DeleteText(doc, 5, 6))
    print(repr(doc.text))  # 'Helló'
    h.undo()
    print(repr(doc.text))  # 'Helló világ'
    h.redo()
    print(repr(doc.text))  # 'Helló'
```

## Visitor és a modern alternatíva: exhaustív mintaillesztés
<!-- q: Mire jó a Visitor minta, és mi váltja ki modern nyelvekben? -->
<!-- tags: visitor, double dispatch, discriminated union, pattern matching, ast, exhaustiveness -->

A Visitor új műveletet ad egy osztályhierarchiához a hierarchia módosítása nélkül, „double
dispatch”-csel (accept → visitX). Tipikus terep a fordítók AST-je: kiértékelés, kiírás,
típusellenőrzés mind külön visitor. Modern nyelvekben (TypeScript, Rust, Kotlin, Java 21
sealed + switch) a diszkriminált unió és az exhaustív mintaillesztés ugyanezt kevesebb
szertartással adja, és fordítási hibát jelez, ha egy új eset kezeletlen marad. Kompromisszum
(„expression problem”): unióval új művelet olcsó, új típus drága; OOP-vel fordítva.

```typescript
// Kifejezésfa diszkriminált unióval — a modern "visitor"
type Expr =
  | { kind: "num"; value: number }
  | { kind: "var"; name: string }
  | { kind: "add"; left: Expr; right: Expr }
  | { kind: "mul"; left: Expr; right: Expr };

// Új MŰVELET = új függvény; a típusokat nem kell módosítani
function evaluate(e: Expr, env: Record<string, number>): number {
  switch (e.kind) {
    case "num": return e.value;
    case "var": {
      const v = env[e.name];
      if (v === undefined) throw new Error(`ismeretlen változó: ${e.name}`);
      return v;
    }
    case "add": return evaluate(e.left, env) + evaluate(e.right, env);
    case "mul": return evaluate(e.left, env) * evaluate(e.right, env);
    default: {
      const never: never = e; // új kind esetén itt FORDÍTÁSI hiba keletkezik
      throw new Error(`kezeletlen: ${JSON.stringify(never)}`);
    }
  }
}

function show(e: Expr): string {
  switch (e.kind) {
    case "num": return String(e.value);
    case "var": return e.name;
    case "add": return `(${show(e.left)} + ${show(e.right)})`;
    case "mul": return `${show(e.left)} * ${show(e.right)}`;
  }
}

// Klasszikus GoF visitor (double dispatch) osztályhierarchiára
interface Visitor<R> { visitNum(n: NumNode): R; visitAdd(a: AddNode): R; }
abstract class AstNode { abstract accept<R>(v: Visitor<R>): R; }
class NumNode extends AstNode {
  constructor(readonly value: number) { super(); }
  accept<R>(v: Visitor<R>): R { return v.visitNum(this); }
}
class AddNode extends AstNode {
  constructor(readonly l: AstNode, readonly r: AstNode) { super(); }
  accept<R>(v: Visitor<R>): R { return v.visitAdd(this); }
}
const depth: Visitor<number> = {
  visitNum: () => 1,
  visitAdd: (a) => 1 + Math.max(a.l.accept(depth), a.r.accept(depth)),
};

const ast: Expr = {
  kind: "add",
  left: { kind: "num", value: 2 },
  right: { kind: "mul", left: { kind: "var", name: "x" }, right: { kind: "num", value: 3 } },
};
console.log(show(ast), "=", evaluate(ast, { x: 4 })); // (2 + x * 3) = 14
console.log(new AddNode(new NumNode(1), new AddNode(new NumNode(2), new NumNode(3))).accept(depth)); // 3
```

## Chain of Responsibility
<!-- q: Hogyan adjak át egy kérést kezelők láncán, amíg valaki el nem bírálja? -->
<!-- tags: chain of responsibility, handler chain, pipeline, approval workflow, behavioral pattern -->

A Chain of Responsibility a kérést kezelők láncán vezeti végig; mindegyik eldönti, hogy
feldolgozza-e, vagy továbbadja a következőnek. A küldő nem tudja, melyik kezelő fog dönteni,
és a lánc konfigurálható (sorrend, elemek). Ide tartoznak a servlet-filterek, a jóváhagyási
munkafolyamatok és a validációs pipeline-ok. Buktatók: a sorrend üzleti szabály, ezt
dokumentálni/tesztelni kell; kell egy alapértelmezett kimenet arra az esetre, ha senki sem
kezeli a kérést.

```java
import java.math.BigDecimal;
import java.util.Optional;

record Expense(String employee, BigDecimal amount, String category) {}

abstract class Approver {
    private Approver next;

    Approver then(Approver next) { // fluent láncépítés
        this.next = next;
        return next;
    }

    final Optional<String> handle(Expense e) {
        Optional<String> decision = tryHandle(e);
        if (decision.isPresent()) return decision;
        return next != null ? next.handle(e) : Optional.empty(); // továbbadás
    }

    protected abstract Optional<String> tryHandle(Expense e);
}

class PolicyCheck extends Approver {
    protected Optional<String> tryHandle(Expense e) {
        if (e.amount().signum() <= 0) return Optional.of("ELUTASÍTVA: érvénytelen összeg");
        if (e.category().equals("alkohol")) return Optional.of("ELUTASÍTVA: nem elszámolható");
        return Optional.empty(); // nem dönt, továbbmegy
    }
}

class TeamLead extends Approver {
    protected Optional<String> tryHandle(Expense e) {
        return e.amount().compareTo(new BigDecimal("50000")) <= 0
                ? Optional.of("JÓVÁHAGYTA: csapatvezető") : Optional.empty();
    }
}

class Director extends Approver {
    protected Optional<String> tryHandle(Expense e) {
        return e.amount().compareTo(new BigDecimal("500000")) <= 0
                ? Optional.of("JÓVÁHAGYTA: igazgató") : Optional.empty();
    }
}

public class ChainDemo {
    public static void main(String[] args) {
        Approver chain = new PolicyCheck();
        chain.then(new TeamLead()).then(new Director()); // a sorrend maga is üzleti szabály
        Expense[] expenses = {
            new Expense("A", new BigDecimal("12000"), "utazás"),
            new Expense("B", new BigDecimal("320000"), "eszköz"),
            new Expense("C", new BigDecimal("2000000"), "eszköz"),
            new Expense("D", new BigDecimal("8000"), "alkohol"),
        };
        for (Expense e : expenses) {
            // alapértelmezett kimenet, ha senki sem döntött
            System.out.println(e.employee() + ": " + chain.handle(e).orElse("NINCS DÖNTÉS: bizottság elé"));
        }
    }
}
```

## Repository és Unit of Work
<!-- q: Mire jó a repository minta és a unit of work? -->
<!-- tags: repository, unit of work, transaction, data access, persistence, ddd -->

A Repository gyűjteményszerű interfészt ad a domainnek (get, save, find), és elzárja mögé a
perzisztencia részleteit (SQL, ORM, cache), így az üzleti logika tárolófüggetlen és memóriás
implementációval tesztelhető. A Unit of Work egy üzleti művelet összes változását egyetlen
tranzakcióba fogja: vagy minden commitolódik, vagy semmi (nincs „félig átutalt” pénz). Buktatók:
ne legyen generikus „IRepository<T>” minden táblára (az csak az ORM-et ismétli), és a
repository ne commitoljon magától — a tranzakcióhatár a use case-é.

```python
import sqlite3
from dataclasses import dataclass
from typing import Optional

@dataclass
class Account:
    id: int
    owner: str
    balance: int  # fillérben: pénzhez soha ne float

class SqliteAccountRepository:
    """Repository: gyűjteményszerű interfész; az SQL itt marad elzárva."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get(self, account_id: int) -> Optional[Account]:
        row = self.conn.execute(
            "SELECT id, owner, balance FROM accounts WHERE id = ?", (account_id,)  # paraméterezett
        ).fetchone()
        return Account(*row) if row else None

    def save(self, acc: Account) -> None:
        self.conn.execute(
            "INSERT INTO accounts(id, owner, balance) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET owner = excluded.owner, balance = excluded.balance",
            (acc.id, acc.owner, acc.balance),
        )

class UnitOfWork:
    """Egy üzleti művelet összes változása egyetlen tranzakcióban."""

    def __init__(self, path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(path, isolation_level=None)  # kézi tranzakciókezelés
        self.conn.execute("CREATE TABLE IF NOT EXISTS accounts(id INTEGER PRIMARY KEY, owner TEXT, balance INTEGER)")
        self.accounts = SqliteAccountRepository(self.conn)

    def __enter__(self) -> "UnitOfWork":
        self.conn.execute("BEGIN")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.conn.execute("ROLLBACK" if exc_type else "COMMIT")  # hiba esetén minden visszagörgetődik

def transfer(uow: UnitOfWork, src: int, dst: int, amount: int) -> None:
    with uow:
        a, b = uow.accounts.get(src), uow.accounts.get(dst)
        if a is None or b is None:
            raise LookupError("ismeretlen számla")
        if a.balance < amount:
            raise ValueError("nincs elég fedezet")
        a.balance -= amount
        b.balance += amount
        uow.accounts.save(a)
        uow.accounts.save(b)

if __name__ == "__main__":
    uow = UnitOfWork()
    with uow:
        uow.accounts.save(Account(1, "A", 10_000))
        uow.accounts.save(Account(2, "B", 0))
    transfer(uow, 1, 2, 2_500)
    try:
        transfer(uow, 1, 2, 999_999)
    except ValueError as e:
        print("hiba:", e)
    print(uow.accounts.get(1), uow.accounts.get(2))  # 7500 és 2500
```

## CQRS: írási és olvasási modell szétválasztása
<!-- q: Mi a CQRS, és mikor éri meg használni? -->
<!-- tags: cqrs, command query separation, read model, projection, eventual consistency -->

A CQRS (Command Query Responsibility Segregation) külön modellt használ az íráshoz (parancsok:
üzleti szabályok, validálás, konzisztencia) és az olvasáshoz (lekérdezésre optimalizált,
denormalizált nézetek/projekciók). Az írási oldal eseményeket bocsát ki, amikből a read modell
frissül — akár külön adatbázisban, külön skálázva. Ára: az olvasási oldal jellemzően késik
(eventual consistency), és több mozgó alkatrész van; egyszerű CRUD-alkalmazásnál felesleges
bonyolítás. Akkor éri meg, ha az olvasási és írási terhelés vagy forma nagyon eltér.

```python
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class PlaceOrder:  # parancs: szándék, felszólító mód
    order_id: str
    customer: str
    lines: tuple[tuple[str, int, int], ...]  # (termék, db, egységár)

@dataclass(frozen=True)
class OrderPlaced:  # esemény: megtörtént tény, múlt idő
    order_id: str
    customer: str
    total: int

class WriteModel:
    """Írási oldal: szabályok és konzisztencia; nem ad vissza lekérdezési adatot."""

    def __init__(self, publish: Callable[[OrderPlaced], None]) -> None:
        self.orders: dict[str, PlaceOrder] = {}
        self.publish = publish

    def handle(self, cmd: PlaceOrder) -> None:
        if cmd.order_id in self.orders:
            raise ValueError("duplikált rendelés")  # idempotencia
        if not cmd.lines or any(q <= 0 for _, q, _ in cmd.lines):
            raise ValueError("érvénytelen tételek")
        self.orders[cmd.order_id] = cmd
        self.publish(OrderPlaced(cmd.order_id, cmd.customer, sum(q * p for _, q, p in cmd.lines)))

@dataclass
class CustomerStats:
    orders: int = 0
    revenue: int = 0

class ReadModel:
    """Olvasási oldal: denormalizált projekció, join és üzleti logika nélkül."""

    def __init__(self) -> None:
        self.by_customer: dict[str, CustomerStats] = defaultdict(CustomerStats)

    def on_event(self, ev: OrderPlaced) -> None:
        s = self.by_customer[ev.customer]
        s.orders += 1
        s.revenue += ev.total

    def top_customers(self, n: int) -> list[tuple[str, int]]:
        ranked = sorted(self.by_customer.items(), key=lambda kv: -kv[1].revenue)
        return [(c, s.revenue) for c, s in ranked[:n]]

if __name__ == "__main__":
    read = ReadModel()
    # Élesben üzenetsor kötné össze őket, és a read model késhet (eventual consistency)
    write = WriteModel(publish=read.on_event)
    write.handle(PlaceOrder("o1", "acme", (("könyv", 2, 3000),)))
    write.handle(PlaceOrder("o2", "globex", (("toll", 10, 200), ("füzet", 3, 500))))
    write.handle(PlaceOrder("o3", "acme", (("lámpa", 1, 9000),)))
    print(read.top_customers(2))  # [('acme', 15000), ('globex', 3500)]
```

## Event sourcing: az állapot mint eseménynapló
<!-- q: Mi az event sourcing, és hogyan épül fel belőle az állapot? -->
<!-- tags: event sourcing, event store, append-only log, optimistic concurrency, aggregate, replay -->

Event sourcingnál nem az aktuális állapotot tároljuk, hanem az összes változást
változtathatatlan eseményként egy csak hozzáfűzhető naplóban; az állapotot az események
visszajátszásával kapjuk. Előnyei: teljes audit trail, időutazás (állapot bármely múltbeli
pillanatban), új projekciók utólag is építhetők. Párhuzamos írásokat optimista
konkurenciakezeléssel (várt verziószám) zárunk ki. Buktatók: az eseménysémák verziózása
(upcasting), hosszú streamek lassú betöltése (snapshotok kellenek), a GDPR-törlés nehézsége
(crypto-shredding), és a tanulási görbe — csak ott használd, ahol a történet maga is érték.

```python
from dataclasses import dataclass
from typing import Union

@dataclass(frozen=True)
class Deposited:
    amount: int

@dataclass(frozen=True)
class Withdrawn:
    amount: int

Event = Union[Deposited, Withdrawn]

class ConcurrencyError(Exception):
    pass

class EventStore:
    """Csak hozzáfűzhető napló streamenként: az esemény az igazság forrása."""

    def __init__(self) -> None:
        self.streams: dict[str, list[Event]] = {}

    def load(self, stream: str) -> list[Event]:
        return list(self.streams.get(stream, []))

    def append(self, stream: str, expected_version: int, events: list[Event]) -> None:
        current = self.streams.setdefault(stream, [])
        if len(current) != expected_version:  # optimista konkurencia: közben más írt
            raise ConcurrencyError(f"várt verzió {expected_version}, tényleges {len(current)}")
        current.extend(events)

class Account:
    def __init__(self, events: list[Event]) -> None:
        self.balance, self.version, self.pending = 0, 0, []
        for e in events:  # állapot újraépítése visszajátszással
            self._apply(e)
            self.version += 1

    def _apply(self, e: Event) -> None:  # tiszta állapotátmenet, nincs validálás
        if isinstance(e, Deposited):
            self.balance += e.amount
        elif isinstance(e, Withdrawn):
            self.balance -= e.amount

    def deposit(self, amount: int) -> None:  # parancs: validál, majd eseményt rögzít
        if amount <= 0:
            raise ValueError("pozitív összeg kell")
        self._record(Deposited(amount))

    def withdraw(self, amount: int) -> None:
        if amount > self.balance:
            raise ValueError("nincs fedezet")
        self._record(Withdrawn(amount))

    def _record(self, e: Event) -> None:
        self._apply(e)
        self.pending.append(e)

def save(store: EventStore, stream: str, acc: Account) -> None:
    store.append(stream, acc.version, acc.pending)
    acc.version += len(acc.pending)
    acc.pending = []

if __name__ == "__main__":
    store = EventStore()
    acc = Account(store.load("acc-1"))
    acc.deposit(10_000)
    acc.withdraw(3_000)
    save(store, "acc-1", acc)
    a1, a2 = Account(store.load("acc-1")), Account(store.load("acc-1"))  # két párhuzamos kérés
    a1.withdraw(5_000)
    save(store, "acc-1", a1)
    a2.withdraw(5_000)
    try:
        save(store, "acc-1", a2)  # elavult verzió: elutasítva, újra kell tölteni és próbálni
    except ConcurrencyError as e:
        print("ütközés:", e)
    print(Account(store.load("acc-1")).balance)  # 2000
```

## Hexagonális és Clean Architecture
<!-- q: Mi a hexagonális (ports and adapters) és a clean architecture lényege? -->
<!-- tags: hexagonal architecture, ports and adapters, clean architecture, onion, dependency rule -->

Mindkettő ugyanazt a szabályt követi: a függőségek mindig befelé, az üzleti mag felé mutatnak.
A belső körben a domain (entitások, szabályok) és a use case-ek vannak, keretrendszer-import
nélkül; a mag portokat (interfészeket) definiál, a külső körben lévő adapterek (HTTP-handler,
adatbázis, üzenetsor) ezeket valósítják meg vagy hívják. Így a mag adatbázis és web nélkül
tesztelhető, és egy adapter cseréje (pl. Postgres helyett DynamoDB) nem érinti az üzleti
kódot. Buktató: kis CRUD-szolgáltatásnál a sok réteg és leképezés több kárt okoz, mint hasznot.

```go
// Egy fájlban szemléltetve; valós projektben: domain/, app/, adapters/http, adapters/postgres
package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"sync"
)

// ---- DOMAIN: tiszta üzleti szabályok, keretrendszer-import nélkül ----
type Todo struct {
	ID    int    `json:"id"`
	Title string `json:"title"`
}

var ErrEmptyTitle = errors.New("a cím nem lehet üres")

func NewTodo(title string) (Todo, error) {
	if title == "" {
		return Todo{}, ErrEmptyTitle
	}
	return Todo{Title: title}, nil
}

// ---- PORT + USE CASE: a mag definiálja, mire van szüksége ----
type TodoStore interface{ Save(t Todo) (Todo, error) }

type TodoService struct{ store TodoStore }

func (s TodoService) Create(title string) (Todo, error) {
	t, err := NewTodo(title)
	if err != nil {
		return Todo{}, err
	}
	return s.store.Save(t)
}

// ---- ADAPTEREK: kívül vannak, a függőség befelé mutat ----
type memStore struct {
	mu     sync.Mutex
	nextID int
	items  map[int]Todo
}

func (m *memStore) Save(t Todo) (Todo, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.nextID++
	t.ID = m.nextID
	m.items[t.ID] = t
	return t, nil
}

func httpCreate(svc TodoService) http.HandlerFunc { // bejövő (driving) adapter
	return func(w http.ResponseWriter, r *http.Request) {
		var in struct{ Title string `json:"title"` }
		if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
			http.Error(w, "hibás JSON", http.StatusBadRequest)
			return
		}
		t, err := svc.Create(in.Title)
		switch { // domain-hiba -> HTTP-státusz leképezése az adapter dolga
		case errors.Is(err, ErrEmptyTitle):
			http.Error(w, err.Error(), http.StatusUnprocessableEntity)
		case err != nil:
			http.Error(w, "belső hiba", http.StatusInternalServerError)
		default:
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusCreated)
			json.NewEncoder(w).Encode(t)
		}
	}
}

func main() {
	svc := TodoService{store: &memStore{items: map[int]Todo{}}} // itt cserélhető DB-adapterre
	http.HandleFunc("POST /todos", httpCreate(svc))           // Go 1.22+ metódusos útvonalminta
	http.ListenAndServe(":8080", nil)
}
```

## MVC és MVVM
<!-- q: Mi a különbség az MVC és az MVVM között? -->
<!-- tags: mvc, mvvm, mvp, viewmodel, data binding, ui architecture -->

Mindkettő a megjelenítést választja el a domainlogikától. MVC-ben a Controller fogadja a
bemenetet, frissíti a Modellt és kiválasztja a View-t (klasszikusan szerveroldali keretrendszerek:
Rails, Spring MVC, ASP.NET MVC). MVVM-ben a ViewModel a nézet állapotát és parancsait teszi
közzé megjelenítésre kész formában, a View pedig adatkötéssel (data binding) automatikusan
követi — WPF, Angular, Vue, SwiftUI/Jetpack ViewModel. A ViewModel DOM-/UI-független, ezért
egységtesztelhető. Buktató: a „kövér” controller/viewmodel, amibe az üzleti szabályok
szivárognak — azok a Modellben a helyük.

```typescript
// MODEL: domain-adat és szabályok, semmit sem tud a UI-ról
interface Todo { id: number; title: string; done: boolean; }

class TodoModel {
  private items: Todo[] = [];
  private nextId = 1;
  add(title: string): Todo {
    const t = { id: this.nextId, title: title.trim(), done: false };
    if (!t.title) throw new Error("üres cím"); // üzleti szabály a modellben
    this.nextId++;
    this.items.push(t);
    return t;
  }
  toggle(id: number): void {
    const t = this.items.find((x) => x.id === id);
    if (t) t.done = !t.done;
  }
  all(): readonly Todo[] { return this.items; }
}

// VIEWMODEL: a nézet állapota és parancsai; DOM-független => böngésző nélkül tesztelhető
class TodoViewModel {
  draft = "";
  error: string | null = null;
  private listeners: Array<() => void> = [];
  constructor(private readonly model: TodoModel) {}

  get rows() { // megjelenítésre kész, származtatott adat
    return this.model.all().map((t) => ({ id: t.id, label: (t.done ? "[x] " : "[ ] ") + t.title }));
  }
  get remaining(): string {
    return `${this.model.all().filter((t) => !t.done).length} hátra`;
  }
  addCommand(): void {
    try {
      this.model.add(this.draft);
      this.draft = "";
      this.error = null;
    } catch (e) {
      this.error = (e as Error).message;
    }
    this.notify();
  }
  toggleCommand(id: number): void {
    this.model.toggle(id);
    this.notify();
  }
  onChange(fn: () => void): void { this.listeners.push(fn); } // az adatkötés alapja
  private notify(): void { this.listeners.forEach((fn) => fn()); }
}

// VIEW: vékony réteg — csak kirajzol és eseményt továbbít (itt konzolos nézet)
function renderConsole(vm: TodoViewModel): void {
  console.log(vm.rows.map((r) => r.label).join(" | "), "—", vm.remaining, vm.error ?? "");
}

const vm = new TodoViewModel(new TodoModel());
vm.onChange(() => renderConsole(vm));
vm.draft = "Bevásárlás";
vm.addCommand();
vm.draft = "   ";
vm.addCommand(); // hibát jelez, a modell nem változik
vm.toggleCommand(1);
```

## Anti-minták és javításuk
<!-- q: Melyek a leggyakoribb tervezési anti-minták, és hogyan javítsam őket? -->
<!-- tags: anti-patterns, god object, primitive obsession, service locator, value object, code smell -->

Gyakori anti-minták: God Object (mindent tudó osztály), Big Ball of Mud (struktúra nélküli kód),
Service Locator és Singleton-túlhasználat (rejtett globális függőségek), Golden Hammer (mindenre
ugyanaz az eszköz), spekulatív általánosítás (absztrakció egy soha meg nem érkező igényre),
primitív-megszállottság (pénz float-ként, e-mail stringként) és a bool flag paraméterek. A
javítás iránya általában: kisebb, egyfelelősségű egységek, explicit függőségek, és
értékobjektumok, amelyek a validálást egy helyre gyűjtik, így az érvénytelen állapot ki sem
fejezhető.

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

# ANTI-MINTA: primitív-megszállottság + bool flagek + "isten-függvény"
def send_invoice_bad(email: str, amount: float, currency: str, urgent: bool, pdf: bool, test: bool):
    # send_invoice_bad("x", 10.1, "huf", True, False, True) — mit jelent? Senki sem tudja.
    # A float pénznél kerekítési hibát okoz, a valuta szabad szöveg, az e-mail nincs ellenőrizve.
    ...

# JAVÍTÁS: értékobjektumok — a validálás egy helyen, érvénytelen állapot nem létezhet
class Currency(Enum):
    HUF = "HUF"
    EUR = "EUR"

@dataclass(frozen=True)
class Money:
    minor_units: int  # fillér/cent egészként: nincs lebegőpontos hiba
    currency: Currency

    def __add__(self, other: Money) -> Money:
        if other.currency is not self.currency:
            raise ValueError("eltérő valuták nem adhatók össze")
        return Money(self.minor_units + other.minor_units, self.currency)

    def __str__(self) -> str:
        return f"{self.minor_units / 100:.2f} {self.currency.value}"

@dataclass(frozen=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", self.value):
            raise ValueError(f"érvénytelen e-mail: {self.value!r}")

class Priority(Enum):  # bool flag helyett beszédes enum
    NORMAL = 1
    URGENT = 2

@dataclass(frozen=True)
class InvoiceRequest:
    to: Email
    amount: Money
    priority: Priority = Priority.NORMAL
    attach_pdf: bool = True

def send_invoice(req: InvoiceRequest) -> str:
    # A "test" mód nem flag, hanem egy másik (injektált) Mailer implementáció lenne
    return f"Számla {req.amount} -> {req.to.value} ({req.priority.name})"

if __name__ == "__main__":
    total = Money(129_900, Currency.HUF) + Money(10_000, Currency.HUF)
    print(send_invoice(InvoiceRequest(Email("ugyfel@example.com"), total, Priority.URGENT)))
    try:
        Email("nem-email")
    except ValueError as e:
        print(e)
```
