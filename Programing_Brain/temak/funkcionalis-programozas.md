# Funkcionális programozás
<!-- tech: functional-programming -->
<!-- aliases: fp, functional programming, funkcionális, monad, monád, functor, haskell, immutability, pure function -->

A funkcionális programozás (FP) a programot tiszta függvények kompozíciójaként írja le: a függvény kimenete csak a bemenetétől függ, az adat immutábilis, a mellékhatások (I/O, állapot) pedig a program szélére szorulnak vagy típusokkal jelöltek. Előnye a könnyű tesztelhetőség, a biztonságos párhuzamosítás, a lokálisan érthető kód és az erős absztrakciók (map/fold, Option/Result, functor/monád). Tisztán funkcionális nyelv a Haskell, többparadigmás az F#, Scala, OCaml, Clojure, Elixir, de a JavaScript/TypeScript, Python, Rust, C# és Java is egyre több FP-eszközt ad. Nem kell „mindent vagy semmit”: a legnagyobb nyereség a tiszta üzleti logika és az immutábilis adat.

## Tiszta függvények és mellékhatások
<!-- q: Mi az a tiszta függvény és miért érdemes ilyeneket írni? -->
<!-- tags: pure function, side effects, referential transparency, memoization, testability, determinism -->

A tiszta (pure) függvény azonos bemenetre mindig azonos kimenetet ad, és nincs megfigyelhető mellékhatása (nem ír globális állapotot, nem módosítja az argumentumait, nem végez I/O-t). Ezért *referenciálisan átlátszó*: a hívás helyettesíthető az eredményével, így biztonságosan cache-elhető (memoizálás), párhuzamosítható és mock nélkül tesztelhető. A rejtett bemenetek (aktuális idő, véletlenszám, környezeti változók) is tisztátalanná tesznek egy függvényt — ezeket paraméterként érdemes beadni. A gyakori hiba a „láthatatlan” mutáció, például a `sort()`, ami helyben rendezi a hívó tömbjét.

```typescript
type CartItem = { readonly sku: string; readonly price: number; readonly qty: number };

// TISZTA: csak a paraméterektől függ, nem módosít semmit
export function cartTotal(items: readonly CartItem[], discountPct: number): number {
  const gross = items.reduce((sum, i) => sum + i.price * i.qty, 0);
  return Math.round(gross * (1 - discountPct / 100));
}

// NEM TISZTA: rejtett bemenet (idő), argumentum-mutáció, globális írás, I/O
let lastTotal = 0;
export function impureTotal(items: CartItem[]): number {
  const discount = new Date().getDay() === 5 ? 10 : 0;   // rejtett függőség: az aktuális idő
  items.sort((a, b) => a.price - b.price);              // a HÍVÓ tömbjét rendezi át!
  lastTotal = cartTotal(items, discount);               // globális állapot
  console.log("total", lastTotal);                      // I/O
  return lastTotal;
}

// Javítva: a nem determinisztikus értéket paraméterként kapjuk, a naplózást a hívó végzi
export const fridayDiscount = (now: Date): number => (now.getDay() === 5 ? 10 : 0);
export function checkout(items: readonly CartItem[], now: Date): { total: number; logLine: string } {
  const total = cartTotal(items, fridayDiscount(now));
  return { total, logLine: `total ${total}` };
}

// Memoizálás: csak tiszta függvénynél helyes
function memoize<A, R>(fn: (a: A) => R): (a: A) => R {
  const cache = new Map<A, R>();
  return (a) => {
    if (!cache.has(a)) cache.set(a, fn(a));
    return cache.get(a) as R;
  };
}
const fib: (n: number) => bigint = memoize((n: number): bigint => (n < 2 ? BigInt(n) : fib(n - 1) + fib(n - 2)));
console.log(fib(90));                                    // azonnal, exponenciális idő helyett
console.log(checkout([{ sku: "A", price: 1000, qty: 3 }], new Date("2025-01-03")));  // péntek: 2700
```

## Immutabilitás és strukturális megosztás
<!-- q: Hogyan dolgozzak immutábilis adatokkal JavaScriptben/TypeScriptben? -->
<!-- tags: immutability, readonly, spread, structural sharing, object freeze, reducer, toSorted -->

Immutábilis adatnál módosítás helyett új értéket hozunk létre; így nincs „ki írta át ezt az objektumot?” típusú hiba, és a változás-detektálás egy olcsó referencia-összehasonlítás (`===`), amire a React, a Redux és a memoizált szelektorok építenek. A spread-del csak a módosított útvonalat másoljuk, a változatlan részfák megosztottak maradnak (*structural sharing*), így a költség nem a teljes objektum mérete. A TypeScript `readonly`/`Readonly<T>` fordítási időben véd, az `Object.freeze` futásidőben, de csak sekélyen. Nagy, gyakran módosított gyűjteményeknél perzisztens adatszerkezet (Immutable.js) vagy Immer jobb a naiv másolásnál.

```typescript
type Address = Readonly<{ city: string; zip: string }>;
type User = Readonly<{ id: number; name: string; tags: readonly string[]; address: Address }>;

const user: User = { id: 1, name: "Anna", tags: ["admin"], address: { city: "Szeged", zip: "6720" } };

// Mély frissítés: csak az útvonalat másoljuk, a többi megosztott
const moved: User = { ...user, address: { ...user.address, city: "Kecskemét" } };
const tagged: User = { ...user, tags: [...user.tags, "beta"] };
console.log(user.address.city, moved.address.city);   // Szeged Kecskemét
console.log(moved.tags === user.tags, tagged.tags);   // true ["admin", "beta"]
// user.name = "x";        // fordítási hiba: readonly
// user.tags.push("x");    // fordítási hiba: readonly string[]

// Nem-mutáló tömbműveletek (ES2023)
const scores: readonly number[] = [42, 7, 19];
const sorted = scores.toSorted((a, b) => a - b);      // új tömb; a sort() helyben rendezne
const replaced = scores.with(1, 8);                   // [42, 8, 19]

// Object.freeze csak sekély — rekurzív változat:
function deepFreeze<T>(obj: T): Readonly<T> {
  if (obj && typeof obj === "object" && !Object.isFrozen(obj)) {
    Object.freeze(obj);
    for (const value of Object.values(obj)) deepFreeze(value);
  }
  return obj;
}
const config = deepFreeze({ db: { host: "localhost", port: 5432 } });

// Reducer: minden állapotátmenet új objektum -> a változás egy === összehasonlítás
type State = Readonly<{ items: readonly string[]; loading: boolean }>;
type Action = { type: "add"; item: string } | { type: "loaded" };
function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "add": return { ...state, items: [...state.items, action.item] };
    case "loaded": return { ...state, loading: false };
  }
}
const s1: State = { items: [], loading: true };
const s2 = reducer(s1, { type: "add", item: "tej" });
console.log(s1 === s2, s1.items.length, s2.items.length, sorted, replaced, config.db.port);
```

## Magasabbrendű függvények
<!-- q: Mik azok a magasabbrendű függvények és hogyan használjam őket? -->
<!-- tags: higher order functions, callbacks, decorators, predicates, retry, groupBy, abstraction -->

A magasabbrendű függvény (higher-order function) függvényt kap paraméterként vagy függvényt ad vissza; így a *viselkedés* is paraméterezhető, nem csak az adat. Ezzel a gyakori mintákat (szűrés, csoportosítás, újrapróbálás, időmérés, naplózás) egyszer írod meg, és tetszőleges logikával kombinálod — ez a dekorátorok és a middleware-ek alapja. A predikátum-kombinátorok (`and`, `not`) kis, tesztelhető feltételekből építenek összetettet. Figyelj a `this` elvesztésére metódus átadásakor (`arr.map(obj.method)`), és arra, hogy a forró ciklusban létrehozott closure-ök allokációt jelentenek.

```typescript
type Predicate<T> = (x: T) => boolean;
const not = <T>(p: Predicate<T>): Predicate<T> => (x) => !p(x);
const and = <T>(...ps: Predicate<T>[]): Predicate<T> => (x) => ps.every((p) => p(x));

// Tetszőleges async művelet újrapróbálása exponenciális backoff-fal
async function withRetry<T>(op: () => Promise<T>, attempts = 3, baseMs = 100): Promise<T> {
  let lastError: unknown;
  for (let i = 0; i < attempts; i++) {
    try {
      return await op();
    } catch (err) {
      lastError = err;
      await new Promise((r) => setTimeout(r, baseMs * 2 ** i));
    }
  }
  throw lastError;
}

// Dekorátor függvényként: a típusok (paraméterek, visszatérés) megmaradnak
function timed<A extends unknown[], R>(name: string, fn: (...args: A) => R): (...args: A) => R {
  return (...args) => {
    const t0 = performance.now();
    try { return fn(...args); }
    finally { console.log(`${name}: ${(performance.now() - t0).toFixed(2)} ms`); }
  };
}

// A kulcsképző függvény a paraméter
function groupBy<T, K extends PropertyKey>(xs: readonly T[], key: (x: T) => K): Partial<Record<K, T[]>> {
  const out: Partial<Record<K, T[]>> = {};
  for (const x of xs) (out[key(x)] ??= []).push(x);
  return out;
}

type Product = { name: string; price: number; inStock: boolean; category: string };
const products: Product[] = [
  { name: "Laptop", price: 400000, inStock: true, category: "it" },
  { name: "Egér", price: 9000, inStock: false, category: "it" },
  { name: "Szék", price: 60000, inStock: true, category: "bútor" },
];
const affordable: Predicate<Product> = (p) => p.price < 100000;
const available: Predicate<Product> = (p) => p.inStock;

console.log(products.filter(and(affordable, available)).map((p) => p.name));  // ["Szék"]
console.log(products.filter(not(available)).map((p) => p.name));              // ["Egér"]
const timedGroupBy = timed("groupBy", (xs: Product[]) => groupBy(xs, (p) => p.category));
console.log(timedGroupBy(products));
withRetry(() => Promise.resolve("ok")).then(console.log);
```

## Currying és részleges alkalmazás
<!-- q: Mi a különbség a currying és a részleges alkalmazás között? -->
<!-- tags: currying, partial application, point free, function arity, configuration, typescript -->

A *currying* egy több argumentumú függvényt egyargumentumú függvények láncává alakít: `f(a, b, c)` → `f(a)(b)(c)`; a *részleges alkalmazás* néhány argumentum rögzítésével új, kisebb aritású függvényt ad. Mindkettő a konfigurációt és az adatot választja szét: előbb a ritkán változó paramétereket (szint, modul, alap-URL), utoljára az adatot — így a függvény közvetlenül átadható `map`-nek vagy `pipe`-nak. Haskellben minden függvény automatikusan curry-zett, JS/TS-ben kézzel vagy segédfüggvénnyel csináljuk. Túlzott pont-mentes (point-free) stílus rontja az olvashatóságot és a hibaüzeneteket — mértékkel.

```typescript
const add = (a: number) => (b: number) => a + b;
const inc = add(1);
console.log([1, 2, 3].map(inc));                      // [2, 3, 4]

// Típusos curry 3 argumentumra
function curry3<A, B, C, R>(fn: (a: A, b: B, c: C) => R) {
  return (a: A) => (b: B) => (c: C) => fn(a, b, c);
}

// Valós példa: előbb a ritkán változó paraméterek, utoljára az adat
const log = curry3((level: "info" | "error", module: string, msg: string) =>
  `${new Date().toISOString()} [${level}] ${module}: ${msg}`);
const dbError = log("error")("db");
console.log(dbError("connection refused"));
["timeout", "pool exhausted"].map(dbError).forEach((line) => console.log(line));

// Általános részleges alkalmazás variadikus tuple-típusokkal (TS 4.0+)
function partial<A extends unknown[], B extends unknown[], R>(
  fn: (...args: [...A, ...B]) => R,
  ...first: A
): (...rest: B) => R {
  return (...rest) => fn(...first, ...rest);
}

const request = (baseUrl: string, path: string, init?: RequestInit) =>
  fetch(baseUrl + path, init).then((r) => r.json());
const api = partial(request, "https://api.example.com");   // baseUrl rögzítve
// api("/users"), api("/orders", { method: "POST" })

// Pont-mentes segéd: mezőkiválasztó
const prop = <K extends string>(k: K) => <T extends Record<K, unknown>>(o: T): T[K] => o[k];
console.log([{ name: "Anna" }, { name: "Béla" }].map(prop("name")));   // ["Anna", "Béla"]
```

## Függvénykompozíció és pipe
<!-- q: Hogyan komponáljak függvényeket pipe-pal vagy compose-zal? -->
<!-- tags: function composition, compose, pipe, pipeline, point free, typescript overloads -->

A kompozíció kis, egycélú függvényekből épít nagyobbat: `compose(f, g)(x) = f(g(x))` jobbról balra, a `pipe` balról jobbra halad, ami az olvasási irányt követi, ezért a gyakorlatban népszerűbb. Ehhez a lépéseknek egyargumentumúnak kell lenniük — itt jön jól a currying. TypeScriptben a típusos `pipe` túlterhelésekkel (overload) írható, így minden lépés típusa ellenőrzött (így működik az fp-ts, az Effect és az RxJS `pipe`-ja is). A hosszú, névtelen csővezeték nehezen debugolható: nevezd el a köztes lépéseket.

```typescript
const compose2 = <A, B, C>(f: (b: B) => C, g: (a: A) => B) => (a: A): C => f(g(a));

// Típusos pipe túlterhelésekkel
function pipe<A>(a: A): A;
function pipe<A, B>(a: A, ab: (a: A) => B): B;
function pipe<A, B, C>(a: A, ab: (a: A) => B, bc: (b: B) => C): C;
function pipe<A, B, C, D>(a: A, ab: (a: A) => B, bc: (b: B) => C, cd: (c: C) => D): D;
function pipe(a: unknown, ...fns: Array<(x: unknown) => unknown>): unknown {
  return fns.reduce((acc, fn) => fn(acc), a);
}

// Kis, újrahasznosítható lépések
const trim = (s: string) => s.trim();
const lower = (s: string) => s.toLowerCase();
const stripAccents = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "");
const dashify = (s: string) => s.replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
const truncate = (n: number) => (s: string) => s.slice(0, n);

const toSlug = (s: string) => pipe(s, trim, lower, (x) => dashify(stripAccents(x)));
console.log(toSlug("  Árvíztűrő Tükörfúrógép!  "));      // "arvizturo-tukorfurogep"

const shortSlug = compose2(truncate(10), toSlug);
console.log(shortSlug("Funkcionális Programozás"));       // "funkcional"

// Típushiba fordításkor: a lépések nem illeszkednek
// pipe("x", (s: string) => s.length, (n: string) => n.trim());   // number -> string hiba
```

## Closure-ök (lezárások)
<!-- q: Mi az a closure és mire használható JavaScriptben? -->
<!-- tags: closure, lexical scope, private state, module pattern, var vs let, memory leak, once -->

A closure egy függvény és a létrehozásakor látható változók (lexikális környezet) együttese: a belső függvény akkor is eléri a külső változókat, amikor a külső függvény már visszatért. Ezzel valódi privát állapot hozható létre osztály nélkül (rate limiter, számláló, cache, `once`), és ez a currying, a dekorátorok és a React hookok alapja. A closure *változót* fog be, nem értéket: a `var` függvény-scope-ú, ezért a ciklusban létrehozott callbackek ugyanazt a változót látják, míg a `let` iterációnként új kötést ad. Buktató: a befogott környezet életben tartja a hivatkozott objektumokat, ami eseménykezelőkben memóriaszivárgást okozhat.

```javascript
// Privát állapot: a hits Map kívülről elérhetetlen; az órát injektáljuk a tesztelhetőségért
function createRateLimiter(limit, windowMs, now = Date.now) {
  const hits = new Map();
  return function allow(clientId) {
    const t = now();
    const recent = (hits.get(clientId) ?? []).filter((ts) => t - ts < windowMs);
    const ok = recent.length < limit;
    if (ok) recent.push(t);
    hits.set(clientId, recent);
    return ok;
  };
}
const allow = createRateLimiter(2, 1000);
console.log(allow("a"), allow("a"), allow("a"), allow("b"));   // true true false true

// Modul-minta: privát állapot + publikus API
function createCounter() {
  let count = 0;
  return { inc: () => ++count, reset: () => { count = 0; }, get value() { return count; } };
}
const c = createCounter();
c.inc(); c.inc();
console.log(c.value);                     // 2

// Klasszikus buktató: var függvény-scope-ú -> minden callback ugyanazt az i-t látja
const fnsVar = [];
for (var i = 0; i < 3; i++) fnsVar.push(() => i);
console.log(fnsVar.map((f) => f()));      // [3, 3, 3]
const fnsLet = [];
for (let j = 0; j < 3; j++) fnsLet.push(() => j);
console.log(fnsLet.map((f) => f()));      // [0, 1, 2] — iterációnként új kötés

// Szivárgás elkerülése: csak a szükséges értéket fogd be, ne a nagy objektumot
function attach(element, hugeBuffer) {
  const size = hugeBuffer.length;
  const onClick = () => console.log(size);
  element.addEventListener("click", onClick);
  return () => element.removeEventListener("click", onClick);   // takarító függvény
}

// once: a closure-állapot garantálja az egyszeri futást
function once(fn) {
  let done = false, result;
  return (...args) => {
    if (!done) { done = true; result = fn(...args); }
    return result;
  };
}
const init = once(() => { console.log("init fut"); return 42; });
console.log(init(), init());              // "init fut" egyszer, majd 42 42
```

## Rekurzió, farokhívás és trampoline
<!-- q: Hogyan kerüljem el a stack overflow-t rekurzióban, mi a tail call optimization? -->
<!-- tags: recursion, tail call, tco, trampoline, tailrec, stack overflow, accumulator -->

Funkcionális stílusban a ciklus helyett rekurziót használunk; a *farokrekurzív* (tail-recursive) alakban a rekurzív hívás az utolsó művelet, és az állapot egy akkumulátor-paraméterben halad, így a fordító ciklussá alakíthatja (TCO), és nem nő a stack. A Scala `@tailrec`-kel kikényszeríti ezt, a Haskell, OCaml és Scheme garantálja, a JavaScriptben viszont a gyakorlatban csak a Safari valósítja meg, a Python és a Java pedig egyáltalán nem. Ilyenkor a *trampoline* segít: a rekurzív lépés helyett egy „folytatás” függvényt adunk vissza, és egy ciklus hívogatja őket konstans stack-mélységgel. Fák bejárásánál a mélység általában kicsi, ott a sima rekurzió rendben van.

```typescript
// Naiv: minden hívás új stack frame -> sumTo(1e6) "Maximum call stack size exceeded"
const sumTo = (n: number): number => (n === 0 ? 0 : n + sumTo(n - 1));

// Farokrekurzív alak akkumulátorral (TCO-t garantáló nyelvben konstans stack)
const sumToTail = (n: number, acc = 0): number => (n === 0 ? acc : sumToTail(n - 1, acc + n));

// Trampoline: a lépés egy leírás (adat), nem tényleges hívás
type Bounce<T> = { done: true; value: T } | { done: false; next: () => Bounce<T> };
const done = <T>(value: T): Bounce<T> => ({ done: true, value });
const more = <T>(next: () => Bounce<T>): Bounce<T> => ({ done: false, next });

function trampoline<T>(start: Bounce<T>): T {
  let b = start;
  while (!b.done) b = b.next();        // ciklus: konstans stack-mélység
  return b.value;
}

const sumT = (n: number, acc = 0): Bounce<number> =>
  n === 0 ? done(acc) : more(() => sumT(n - 1, acc + n));
console.log(trampoline(sumT(1_000_000)));           // 500000500000, overflow nélkül

// Kölcsönös rekurzió is működik
const isEven = (n: number): Bounce<boolean> => (n === 0 ? done(true) : more(() => isOdd(n - 1)));
const isOdd = (n: number): Bounce<boolean> => (n === 0 ? done(false) : more(() => isEven(n - 1)));
console.log(trampoline(isEven(100_001)));           // false
console.log(sumTo(100), sumToTail(100));            // kis n-re a naiv is jó
```

```scala
import scala.annotation.tailrec

// @tailrec: fordítási HIBA, ha a hívás nem farokpozícióban van -> garantáltan ciklus lesz belőle
@tailrec
def gcd(a: Long, b: Long): Long = if (b == 0) a else gcd(b, a % b)

def factorial(n: Int): BigInt = {
  @tailrec def loop(i: Int, acc: BigInt): BigInt = if (i <= 1) acc else loop(i - 1, acc * i)
  loop(n, 1)
}
```

## map, filter, reduce és fold
<!-- q: Hogyan használjam a map, filter, reduce és fold műveleteket, és mi a foldl és foldr különbsége? -->
<!-- tags: map, filter, reduce, fold, foldl, foldr, haskell, lazy evaluation, data pipeline -->

A `map` minden elemet transzformál, a `filter` megtartja a feltételnek megfelelőket, a `fold`/`reduce` pedig egyetlen értékké (összeg, szótár, újabb lista) aggregál — a ciklusok legtöbbje kifejezhető e háromból, és a szándék sokkal olvashatóbb. A `foldr` jobbról épít, és lusta kombinálóval végtelen listán is működik (`map`, `any`, `take` így definiálható), a `foldl'` szigorú bal fold, összegzésre ezt kell használni. A sima `foldl` Haskellben lusta thunk-láncot épít, ami nagy listán memóriát zabál. Haskellben a lustaság miatt a `map`/`filter` láncolás nem hoz létre köztes listákat (fúzió).

```haskell
import Data.List (foldl')
import qualified Data.Map.Strict as Map

data Order = Order { customer :: String, amount :: Double, paid :: Bool }

orders :: [Order]
orders =
  [ Order "anna" 120 True, Order "bela" 40 False
  , Order "anna" 80 True,  Order "cili" 300 True ]

-- map + filter + fold egy csővezetékben (jobbról balra olvasandó a kompozíció miatt)
paidTotal :: [Order] -> Double
paidTotal = foldl' (+) 0 . map amount . filter paid

-- foldl': szigorú bal fold -> konstans memória összegzésnél
revenueByCustomer :: [Order] -> Map.Map String Double
revenueByCustomer = foldl' step Map.empty . filter paid
  where step m o = Map.insertWith (+) (customer o) (amount o) m

-- foldr-rel bármely listafüggvény kifejezhető; lusta, ezért végtelen listán is működik
myMap :: (a -> b) -> [a] -> [b]
myMap f = foldr (\x acc -> f x : acc) []

myFilter :: (a -> Bool) -> [a] -> [a]
myFilter p = foldr (\x acc -> if p x then x : acc else acc) []

main :: IO ()
main = do
  print (paidTotal orders)                          -- 500.0
  print (Map.toList (revenueByCustomer orders))     -- [("anna",200.0),("cili",300.0)]
  print (take 3 (myMap (* 2) [1 ..]))               -- [2,4,6] — végtelen bemeneten is
  print (myFilter even [1 .. 10 :: Int])            -- [2,4,6,8,10]
```

## Algebrai adattípusok (ADT)
<!-- q: Mik azok az algebrai adattípusok és hogyan modellezzek velük? -->
<!-- tags: algebraic data types, adt, sum type, product type, tagged union, make illegal states unrepresentable, haskell -->

Az algebrai adattípusok két építőkockából állnak: a *szorzattípus* (product) minden mezőt egyszerre tartalmaz (rekord, struct, tuple), az *összegtípus* (sum) pontosan egy változatot a felsoroltak közül (tagged union, adatokat hordozó enum). Velük az illegális állapotok egyszerűen nem ábrázolhatók: például a `Connected` állapot hordoz session-azonosítót, a `Disconnected` nem, így nincs „nullable mező, ami csak néha érvényes”. A rekurzív ADT-k (fák, kifejezések) természetes ábrázolást adnak a fordítóknak és interpretereknek. Haskell/OCaml/F#/Rust/Scala natívan támogatja, TypeScriptben a *discriminated union* a megfelelője.

```haskell
-- Szorzattípus: MINDEN mező jelen van
data Point = Point { px :: Double, py :: Double } deriving (Show, Eq)

-- Összegtípus: PONTOSAN EGY változat
data Shape
  = Circle Point Double
  | Rect Point Point
  | Polygon [Point]
  deriving (Show)

area :: Shape -> Double
area (Circle _ r) = pi * r * r
area (Rect (Point x1 y1) (Point x2 y2)) = abs (x2 - x1) * abs (y2 - y1)
area (Polygon ps) = abs (sum (zipWith cross ps (drop 1 ps ++ take 1 ps))) / 2
  where cross (Point a b) (Point c d) = a * d - b * c      -- shoelace-képlet

-- Rekurzív ADT: kifejezésfa
data Expr = Lit Integer | Add Expr Expr | Mul Expr Expr | Neg Expr
  deriving (Show)

eval :: Expr -> Integer
eval (Lit n) = n
eval (Add a b) = eval a + eval b
eval (Mul a b) = eval a * eval b
eval (Neg e) = negate (eval e)

-- Állapotgép: minden állapot csak a rá érvényes adatot hordozza
data Connection
  = Disconnected
  | Connecting { attempt :: Int }
  | Connected { sessionId :: String }
  deriving (Show)

onFailure :: Connection -> Connection
onFailure (Connecting n) | n < 3 = Connecting (n + 1)
onFailure _ = Disconnected

main :: IO ()
main = do
  print (map area [Circle (Point 0 0) 1, Rect (Point 0 0) (Point 2 3)])
  print (area (Polygon [Point 0 0, Point 4 0, Point 4 3]))    -- 6.0
  print (eval (Add (Lit 2) (Mul (Lit 3) (Neg (Lit 4)))))      -- -10
  print (onFailure (Connecting 1), onFailure (Connecting 3))
```

## Mintaillesztés (pattern matching)
<!-- q: Hogyan használjam a mintaillesztést, és mi a kimerítő ellenőrzés előnye? -->
<!-- tags: pattern matching, match, destructuring, guards, exhaustiveness, slice patterns, rust -->

A mintaillesztés egyszerre vizsgálja az érték alakját és bontja szét (destrukturálja) a részeit; a *guard* (`if` feltétel) finomítja az ágat, a szelet-minták (`[first, rest @ ..]`) listákra illeszkednek. A legnagyobb előny a *kimerítő ellenőrzés* (exhaustiveness): ha új variánst adsz egy enumhoz, a fordító minden olyan `match`-et megjelöl, ahol nincs kezelve — ezért ne használj feleslegesen `_` ágat összegtípusokon. Az ágak sorrendje számít: a specifikusabb minta álljon elöl. Rust, Scala, F#, OCaml, Haskell natívan, a Python 3.10+, a C# 8+ és a Java 21+ is támogatja.

```rust
#[derive(Debug)]
enum Command {
    Move { x: i32, y: i32 },
    Say(String),
    Batch(Vec<Command>),
    Quit,
}

fn describe(cmd: &Command) -> String {
    match cmd {
        // Literál-minta mezőben, majd guard: a specifikusabb ág elöl
        Command::Move { x: 0, y: 0 } => "helyben marad".to_string(),
        Command::Move { x, y } if x.abs() > 100 || y.abs() > 100 => format!("túl messze: ({x}, {y})"),
        Command::Move { x, y } => format!("mozgás ({x}, {y})"),
        Command::Say(text) if text.is_empty() => "csend".into(),
        Command::Say(text) => format!("mondja: {text}"),
        // Szelet-minták: üres, egyelemű, első + a többi (rest @ .. köti a maradékot)
        Command::Batch(cmds) => match cmds.as_slice() {
            [] => "üres köteg".into(),
            [only] => format!("egyetlen: {}", describe(only)),
            [first, rest @ ..] => format!("{} (+{} további)", describe(first), rest.len()),
        },
        Command::Quit => "kilépés".into(),
        // Nincs `_` ág: új variánsnál a fordító itt hibát jelez (kimerítő ellenőrzés)
    }
}

fn classify(n: i64) -> &'static str {
    match n {
        i64::MIN..=-1 => "negatív",
        0 => "nulla",
        1..=9 => "egyjegyű",
        x if x % 2 == 0 => "páros, nagy",
        _ => "páratlan, nagy",
    }
}

fn main() {
    let cmds = vec![
        Command::Move { x: 3, y: -4 },
        Command::Say(String::new()),
        Command::Batch(vec![Command::Quit, Command::Move { x: 0, y: 0 }]),
    ];
    for c in &cmds {
        println!("{}", describe(c));
    }
    // let-else és if-let: egyetlen minta kényelmes kezelése
    let Some(first) = cmds.first() else { return };
    if let Command::Move { x, .. } = first {
        println!("x = {x}: {}", classify(*x as i64));
    }
}
```

## Option/Maybe és Result/Either
<!-- q: Hogyan kezeljem a hiányzó értéket és a hibákat null és kivételek helyett? -->
<!-- tags: option, maybe, result, either, error handling, null safety, railway oriented programming, typescript -->

Az `Option`/`Maybe` a „lehet, hogy nincs érték” helyzetet teszi explicitté a típusban (null helyett), a `Result`/`Either` pedig a „siker VAGY hiba” kimenetet (kivétel helyett). Így a hívó nem felejtheti el kezelni az esetet, és a hiba típusa a függvény szignatúrájában dokumentált. A `map` a sikeres értéket transzformálja, az `andThen` (flatMap) egy újabb, szintén elbukni képes lépést fűz hozzá, és az első hibánál rövidre zár („railway-oriented programming”). Kivételt csak valóban váratlan hibára (bug, erőforrás-kimerülés) tarts meg; a várható üzleti hibák (validáció, nem található) legyenek értékek.

```typescript
type Option<T> = { kind: "some"; value: T } | { kind: "none" };
type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };

const some = <T>(value: T): Option<T> => ({ kind: "some", value });
const none: Option<never> = { kind: "none" };
const Ok = <T>(value: T): Result<T, never> => ({ ok: true, value });
const Err = <E>(error: E): Result<never, E> => ({ ok: false, error });

const fromNullable = <T>(x: T | null | undefined): Option<T> => (x == null ? none : some(x));
const mapOpt = <T, U>(o: Option<T>, f: (t: T) => U): Option<U> => (o.kind === "some" ? some(f(o.value)) : none);
const getOrElse = <T>(o: Option<T>, fallback: T): T => (o.kind === "some" ? o.value : fallback);
// andThen (flatMap): az első hibánál rövidre zár
const andThen = <T, U, E>(r: Result<T, E>, f: (t: T) => Result<U, E>): Result<U, E> => (r.ok ? f(r.value) : r);

// A hiba típusa a szignatúrában: a hívó nem felejtheti el kezelni
type PortError = { code: "not_a_number" | "out_of_range" | "privileged"; input: string };

function parsePort(input: string): Result<number, PortError> {
  const n = Number(input);
  if (input.trim() === "" || !Number.isInteger(n)) return Err({ code: "not_a_number", input });
  if (n < 1 || n > 65535) return Err({ code: "out_of_range", input });
  return Ok(n);
}
const nonPrivileged = (p: number): Result<number, PortError> =>
  p >= 1024 ? Ok(p) : Err({ code: "privileged", input: String(p) });

function configuredPort(env: Record<string, string | undefined>): Result<number, PortError> {
  const raw = getOrElse(mapOpt(fromNullable(env.PORT), (s) => s.trim()), "3000");
  return andThen(parsePort(raw), nonPrivileged);
}

for (const env of [{ PORT: "8080" }, { PORT: "80" }, { PORT: "abc" }, {}]) {
  const r = configuredPort(env);
  if (r.ok) console.log("port:", r.value);
  else console.error(`hibás port (${r.error.code}): ${r.error.input}`);   // a típus kikényszeríti az ágat
}
```

## Functor és Applicative
<!-- q: Mi az a functor és az applicative, és mire jók a gyakorlatban? -->
<!-- tags: functor, applicative, fmap, validation, typeclass, haskell, error accumulation -->

A *functor* egy „konténer” vagy kontextus (lista, Maybe, Either, Promise, parser), amelynek tartalmára függvényt alkalmazhatunk az alak megtartásával: `fmap :: (a -> b) -> f a -> f b`; törvényei: `fmap id = id` és `fmap (g . h) = fmap g . fmap h`. Az *applicative* több, egymástól *független* kontextusbeli értéket kombinál egy többargumentumú függvénnyel (`pure`, `<*>`). Gyakorlati haszna a validáció: mivel a lépések függetlenek, a `Validation` applicative *összegyűjti* az összes hibát, míg a monadikus `Either` az elsőnél megáll. Ugyanez a minta adja a párhuzamos lekéréseket (`Promise.all`) és a parser-kombinátorokat.

```haskell
-- Validation: mint az Either, de a hibákat GYŰJTI (ehhez e-nek Semigroup-nak kell lennie)
data Validation e a = Failure e | Success a deriving (Show)

instance Functor (Validation e) where
  fmap _ (Failure e) = Failure e
  fmap f (Success a) = Success (f a)

instance Semigroup e => Applicative (Validation e) where
  pure = Success
  Failure e1 <*> Failure e2 = Failure (e1 <> e2)      -- mindkét hiba megmarad
  Failure e1 <*> Success _  = Failure e1
  Success _  <*> Failure e2 = Failure e2
  Success f  <*> Success a  = Success (f a)

data User = User { name :: String, age :: Int, email :: String } deriving (Show)

validateName :: String -> Validation [String] String
validateName n
  | length n >= 2 = Success n
  | otherwise = Failure ["a név túl rövid"]

validateAge :: Int -> Validation [String] Int
validateAge a
  | a >= 0 && a < 150 = Success a
  | otherwise = Failure ["érvénytelen életkor"]

validateEmail :: String -> Validation [String] String
validateEmail e
  | '@' `elem` e = Success e
  | otherwise = Failure ["hiányzó @ az e-mail címben"]

-- Applicative stílus: a konstruktort "beemeljük" a kontextusba
mkUser :: String -> Int -> String -> Validation [String] User
mkUser n a e = User <$> validateName n <*> validateAge a <*> validateEmail e

main :: IO ()
main = do
  print (fmap (+ 1) (Just 41))                  -- Just 42: a Maybe is functor
  print (fmap length ["fp", "haskell"])         -- [2,7]: a lista is
  print ((+) <$> Just 3 <*> Just 4)             -- Just 7
  print (mkUser "Anna" 30 "anna@example.com")   -- Success (User ...)
  print (mkUser "A" 200 "rossz")                -- Failure [mindhárom hibaüzenet]
```

## Monád: függő lépések láncolása
<!-- q: Mi az a monád érthetően, kóddal magyarázva? -->
<!-- tags: monad, flatMap, bind, do notation, maybe monad, either monad, promise, haskell, typescript -->

A monád egy típus `of`/`pure` és `flatMap`/`bind` (`>>=`) művelettel, ahol a következő lépés az *előző eredményétől függ*, és a kontextus (hiányzó érték, hiba, aszinkronitás, lista-nemdeterminizmus, állapot) kezelését a `flatMap` végzi helyetted. A `Maybe` rövidre zár az első hiányzó értéknél, az `Either` az első hibánál, a `Promise.then` megvárja az előző lépést, az `Array.flatMap` minden kombinációt végigjár. Törvényei (bal/jobb egység, asszociativitás) garantálják, hogy a láncolás átrendezhető. Haskellben a `do`-jelölés a bind-lánc szintaktikai cukra; a JS `async/await` ugyanez a Promise-ra.

```typescript
class Maybe<T> {
  private constructor(private readonly value: T | null) {}
  static of<T>(value: T): Maybe<T> { return new Maybe(value); }
  static none<T>(): Maybe<T> { return new Maybe<T>(null); }
  static from<T>(value: T | null | undefined): Maybe<T> {
    return value == null ? Maybe.none<T>() : Maybe.of(value);
  }
  // bind: a függvény maga is Maybe-t ad vissza -> nincs Maybe<Maybe<T>>
  flatMap<U>(f: (t: T) => Maybe<U>): Maybe<U> { return this.value === null ? Maybe.none<U>() : f(this.value); }
  map<U>(f: (t: T) => U): Maybe<U> { return this.flatMap((t) => Maybe.of(f(t))); }
  getOrElse(fallback: T): T { return this.value === null ? fallback : this.value; }
}

type Company = { ceo?: { address?: { city?: string } } };
const companies: Record<string, Company | undefined> = { acme: { ceo: { address: { city: "Győr" } } }, empty: {} };

// Minden lépés hiányozhat; nincs if-piramis, az első hiánynál rövidre zár
const ceoCity = (id: string): string =>
  Maybe.from(companies[id])
    .flatMap((c) => Maybe.from(c.ceo))
    .flatMap((ceo) => Maybe.from(ceo.address))
    .flatMap((a) => Maybe.from(a.city))
    .map((city) => city.toUpperCase())
    .getOrElse("ismeretlen");
console.log(ceoCity("acme"), ceoCity("empty"), ceoCity("nincs"));   // GYŐR ismeretlen ismeretlen

// Ismerős monádok: Array.flatMap (minden kombináció), Promise.then (aszinkron függő lépések)
console.log([1, 2].flatMap((a) => ["x", "y"].map((b) => `${a}${b}`)));   // ["1x","1y","2x","2y"]
```

```haskell
import qualified Data.Map as Map
import Text.Read (readMaybe)

-- do-jelölés = >>= láncolás; a Maybe monád az első Nothing-nál megáll
lookupAge :: Map.Map String String -> String -> Maybe Int
lookupAge db user = do
  raw <- Map.lookup user db
  age <- readMaybe raw
  if age >= 0 then Just age else Nothing

-- Either monád: az első hiba üzenetével áll meg
safeDiv :: Int -> Int -> Either String Int
safeDiv _ 0 = Left "nullával osztás"
safeDiv a b = Right (a `div` b)

calc :: Either String Int
calc = do
  x <- safeDiv 100 5
  y <- safeDiv x 0          -- itt megáll, a pure már nem fut le
  pure (x + y)

main :: IO ()
main = do
  let db = Map.fromList [("anna", "31"), ("bela", "abc")]
  print (map (lookupAge db) ["anna", "bela", "cili"])   -- [Just 31,Nothing,Nothing]
  print calc                                            -- Left "nullával osztás"
```

## Lencsék (lenses) mély immutábilis frissítéshez
<!-- q: Mik azok a lencsék és hogyan frissítsek mélyen beágyazott immutábilis adatot? -->
<!-- tags: lens, optics, immutable update, getter setter, composition, nested data, typescript -->

A lencse egy getter és egy immutábilis setter párosa egy adatszerkezet adott részére (`get: S → A`, `set: A → S → S`); a lényeg, hogy *komponálhatók*: a „munkavállaló → cég → cím → város” lencse kisebb lencsékből áll össze, és a mély frissítés egyetlen hívás lesz a spread-piramis helyett. Az `over` egy függvényt alkalmaz a fókuszált értékre (például fizetésemelés). Haskellben a `lens`, Scalában a Monocle, TS-ben a `monocle-ts` vagy az `optics-ts` ad teljes eszköztárat (prism az összegtípusokra, traversal a gyűjteményekre). Egyszerű esetben az Immer olvashatóbb alternatíva.

```typescript
type Lens<S, A> = { get: (s: S) => A; set: (a: A) => (s: S) => S };

const lens = <S, A>(get: (s: S) => A, set: (a: A) => (s: S) => S): Lens<S, A> => ({ get, set });
const prop = <S, K extends keyof S>(k: K): Lens<S, S[K]> =>
  lens((s) => s[k], (a) => (s) => ({ ...s, [k]: a }));

// Kompozíció: S -> A -> B
const composeL = <S, A, B>(outer: Lens<S, A>, inner: Lens<A, B>): Lens<S, B> =>
  lens(
    (s) => inner.get(outer.get(s)),
    (b) => (s) => outer.set(inner.set(b)(outer.get(s)))(s),
  );
const over = <S, A>(l: Lens<S, A>, f: (a: A) => A) => (s: S): S => l.set(f(l.get(s)))(s);

type Geo = { lat: number; lng: number };
type Address = { city: string; geo: Geo };
type Company = { name: string; address: Address };
type Employee = { name: string; salary: number; company: Company };

const employeeCity = composeL(
  composeL(prop<Employee, "company">("company"), prop<Company, "address">("address")),
  prop<Address, "city">("city"),
);
const salaryL = prop<Employee, "salary">("salary");

const e: Employee = {
  name: "Dóra", salary: 900_000,
  company: { name: "Acme", address: { city: "Pécs", geo: { lat: 46.07, lng: 18.23 } } },
};
const moved = employeeCity.set("Debrecen")(e);
const raised = over(salaryL, (s) => Math.round(s * 1.1))(e);

console.log(employeeCity.get(moved), employeeCity.get(e));          // Debrecen Pécs — az eredeti változatlan
console.log(moved.company.address.geo === e.company.address.geo);  // true: megosztott részfa
console.log(raised.salary);                                        // 990000
```

## Perzisztens adatszerkezetek
<!-- q: Mik azok a perzisztens adatszerkezetek és hogyan lehet hatékony az immutábilis módosítás? -->
<!-- tags: persistent data structures, path copying, structural sharing, hamt, immutable collections, version history -->

A perzisztens adatszerkezet minden „módosítás” után új verziót ad, a régi verzió érintetlen és továbbra is használható. A hatékonyság kulcsa a *path copying*: fában csak a gyökértől a módosított csomópontig vezető utat másoljuk (O(log n) új csomópont), minden más részfa megosztott a verziók között. Így a verziótörténet szinte ingyen van (undo/redo, időutazó debug, snapshotok), és a szálak zár nélkül oszthatják meg az adatot. A gyakorlati implementációk kiegyensúlyozott fák vagy HAMT-ok (Clojure, Scala, Immutable.js); az alábbi kiegyensúlyozatlan BST csak az elvet mutatja.

```typescript
// Kulcs: string; a bal/jobb részfa readonly -> a csomópontok sosem változnak
type Node<V> = { readonly key: string; readonly value: V; readonly left: Tree<V>; readonly right: Tree<V> };
type Tree<V> = Node<V> | null;

function insert<V>(t: Tree<V>, key: string, value: V): Node<V> {
  if (t === null) return { key, value, left: null, right: null };
  if (key < t.key) return { ...t, left: insert(t.left, key, value) };    // a jobb részfa MEGOSZTVA
  if (key > t.key) return { ...t, right: insert(t.right, key, value) };  // a bal részfa megosztva
  return { ...t, value };                                                // csak az érték cserélődik
}

function lookup<V>(t: Tree<V>, key: string): V | undefined {
  while (t !== null) {
    if (key === t.key) return t.value;
    t = key < t.key ? t.left : t.right;
  }
  return undefined;
}

function* entries<V>(t: Tree<V>): Generator<[string, V]> {
  if (t === null) return;
  yield* entries(t.left);
  yield [t.key, t.value];
  yield* entries(t.right);
}

// Minden verzió csak egy gyökér-referencia
const v1 = ["m", "c", "x", "a"].reduce<Tree<number>>((t, k, i) => insert(t, k, i), null);
const v2 = insert(v1, "d", 99);
console.log([...entries(v1)].length, [...entries(v2)].length);   // 4 5
console.log(lookup(v1, "d"), lookup(v2, "d"));                  // undefined 99
console.log(v1?.right === v2.right);                            // true: az "x" részfa közös

// Perzisztens cons-lista: a farok mindig megosztott, a prepend O(1)
type List<T> = { readonly head: T; readonly tail: List<T> } | null;
const cons = <T>(head: T, tail: List<T>): List<T> => ({ head, tail });
const base = cons(2, cons(3, null));
const a = cons(1, base);
const b = cons(0, base);
console.log(a?.tail === b?.tail);                               // true: közös farok
```

## Mellékhatások kezelése: funkcionális mag, imperatív héj
<!-- q: Hogyan kezeljem a mellékhatásokat (I/O) funkcionális stílusban? -->
<!-- tags: side effects, io, functional core imperative shell, effect system, io monad, testability, haskell -->

A valódi programoknak kell I/O, de a döntési logikát el lehet választani tőle: a *funkcionális mag* tiszta függvényekkel kiszámolja, *mit* kell tenni (a hatásokat adatként írja le), az *imperatív héj* pedig végrehajtja őket. Így az üzleti logika tesztje egyszerű adat-összehasonlítás mock nélkül, az I/O-réteg pedig vékony és cserélhető. Haskellben a típus mutatja a hatást: az `IO a` egy végrehajtandó „program” leírása, amit csak a runtime futtat, ezért a tiszta kód nem tud titokban I/O-t végezni. TS/Scala ökoszisztémában az Effect, ZIO és cats-effect könyvtárak ugyanezt adják hibakezeléssel és párhuzamossággal.

```typescript
type Effect =
  | { type: "sendEmail"; to: string; subject: string }
  | { type: "chargeCard"; customerId: string; amount: number }
  | { type: "log"; message: string };

type Subscription = {
  customerId: string; email: string; plan: "free" | "pro"; dueDate: string; failedPayments: number;
};

// TISZTA MAG: leírja, mit kell tenni — de semmit nem hajt végre
export function renewalEffects(sub: Subscription, today: string): Effect[] {
  if (sub.plan === "free" || sub.dueDate > today) return [];
  if (sub.failedPayments >= 3) {
    return [
      { type: "sendEmail", to: sub.email, subject: "Előfizetésed felfüggesztettük" },
      { type: "log", message: `suspended ${sub.customerId}` },
    ];
  }
  return [{ type: "chargeCard", customerId: sub.customerId, amount: 4990 }];
}

// IMPERATÍV HÉJ: a valódi I/O egy helyen, injektált végrehajtóval
type Handlers = { [K in Effect["type"]]: (e: Extract<Effect, { type: K }>) => Promise<void> };

export async function runEffects(effects: Effect[], handlers: Handlers): Promise<void> {
  for (const e of effects) {
    await (handlers[e.type] as (eff: Effect) => Promise<void>)(e);
  }
}

// Teszt: nincs mock, csak adat
const effects = renewalEffects(
  { customerId: "c1", email: "c1@example.com", plan: "pro", dueDate: "2025-01-01", failedPayments: 3 },
  "2025-01-02",
);
console.assert(effects.length === 2 && effects[0].type === "sendEmail");
```

```haskell
import Data.Char (toUpper)

-- A típus mutatja: shout nem végezhet I/O-t, main igen
shout :: String -> String
shout = map toUpper

main :: IO ()
main = do
  name <- getLine                       -- hatás
  putStrLn (shout ("szia, " ++ name))   -- tiszta számítás a hatások között
```

## FP a gyakorlatban: JavaScript és Python
<!-- q: Hogyan programozzak funkcionálisan Pythonban és JavaScriptben? -->
<!-- tags: python functional, functools, itertools, dataclass frozen, generators, javascript functional, groupBy -->

Pythonban az FP-eszközök: generátor-kifejezések (lusta csővezeték), `functools` (`reduce`, `partial`, `lru_cache`), `itertools` (`groupby`, `accumulate`, `islice`), `operator` modul, és `@dataclass(frozen=True)` + `replace()` az immutábilis rekordokhoz. A Python nem optimalizálja a farokrekurziót (rekurziós limit ~1000), és a `lambda` csak kifejezést tartalmazhat, ezért mély rekurzió helyett ciklust vagy generátort használj; a list comprehension általában olvashatóbb a `map`/`filter`-nél. JavaScriptben a tömbmetódusok, a spread, az `Object.groupBy` (ES2024) és a nem-mutáló `toSorted`/`with` adják az alapot. Buktató: az `itertools.groupby` csak a *szomszédos* azonos kulcsokat csoportosítja, ezért előtte rendezni kell.

```python
from dataclasses import dataclass, replace
from functools import reduce, partial, lru_cache
from itertools import groupby, accumulate, islice, count
from operator import attrgetter
from typing import Callable

@dataclass(frozen=True)                  # immutábilis rekord; replace() ad módosított másolatot
class Tx:
    account: str
    amount: int

txs = [Tx("a", 100), Tx("b", -20), Tx("a", -30), Tx("b", 50), Tx("a", 10)]

def pipe(*fns: Callable) -> Callable:
    return lambda x: reduce(lambda acc, f: f(acc), fns, x)

deposits = sum(t.amount for t in txs if t.amount > 0)            # lusta generátor, nincs köztes lista
key = attrgetter("account")
by_account = {k: sum(t.amount for t in g) for k, g in groupby(sorted(txs, key=key), key=key)}
running = list(accumulate(t.amount for t in txs))                 # futó egyenleg (scan)
apply_fee = partial(lambda rate, t: replace(t, amount=round(t.amount * (1 - rate))), 0.01)
with_fee = list(map(apply_fee, txs))                              # az eredeti lista érintetlen

@lru_cache(maxsize=None)                 # memoizálás: csak tiszta függvényre biztonságos
def fib(n: int) -> int:
    return n if n < 2 else fib(n - 1) + fib(n - 2)

odd_squares = pipe(lambda xs: (x for x in xs if x % 2), lambda xs: (x * x for x in xs), list)
print(deposits, by_account, running, with_fee[0])
print(odd_squares(range(10)), list(islice((fib(n) for n in count()), 10)))
```

```javascript
const txs = [{ account: "a", amount: 100 }, { account: "b", amount: -20 }, { account: "a", amount: -30 }];
const pipe = (...fns) => (x) => fns.reduce((acc, f) => f(acc), x);

const balances = pipe(
  (xs) => Object.groupBy(xs, (t) => t.account),                              // ES2024
  (groups) => Object.entries(groups).map(([acc, ts]) => [acc, ts.reduce((s, t) => s + t.amount, 0)]),
  Object.fromEntries,
);
console.log(balances(txs));                                                   // { a: 70, b: -20 }
const withFee = txs.map((t) => ({ ...t, amount: Math.round(t.amount * 0.99) }));  // új objektumok
const byAmount = txs.toSorted((x, y) => x.amount - y.amount);                // nem mutál
console.log(withFee, byAmount);
```

## FP a gyakorlatban: Rust és C#
<!-- q: Hogyan használjam a funkcionális eszközöket Rustban és C#-ban? -->
<!-- tags: rust iterators, closures, option combinators, result, csharp linq, records, with expression, switch expression -->

A Rust iterátor-adapterei (`map`, `filter`, `fold`, `partition`, `filter_map`) lusták és nulla költségűek: a fordító ugyanolyan gyors ciklussá optimalizálja őket, mint a kézzel írtat; az `Option`/`Result` kombinátorok és a `?` operátor váltja ki a null-t és a kivételeket, a `collect::<Result<Vec<_>, _>>()` pedig az első hibánál megáll. C#-ban a LINQ adja a deklaratív lekérdezéseket, a `record` típusok az immutábilis, érték-egyenlőségű adatot és a `with`-másolást, a `switch`-kifejezés a mintaillesztést. Mindkét nyelvben figyelj a lustaságra: a LINQ-lekérdezés minden bejáráskor újra lefut (`ToList()`-tel materializáld), a Rust iterátor pedig `collect` nélkül nem csinál semmit.

```rust
use std::collections::HashMap;

#[derive(Debug)]
struct Tx { account: String, amount: i64 }

fn parse_line(line: &str) -> Result<Tx, String> {
    let (account, amount) = line.split_once(',').ok_or(format!("hiányzó vessző: {line}"))?;
    let amount = amount.trim().parse::<i64>().map_err(|e| format!("{line}: {e}"))?;
    Ok(Tx { account: account.trim().to_string(), amount })
}

fn main() {
    let input = "a, 100\nb, -20\na, -30\nhibás sor\nb, 50";
    let (ok, bad): (Vec<_>, Vec<_>) = input.lines().map(parse_line).partition(Result::is_ok);
    let txs: Vec<Tx> = ok.into_iter().map(Result::unwrap).collect();
    let errors: Vec<String> = bad.into_iter().filter_map(Result::err).collect();

    let balances = txs.iter().fold(HashMap::new(), |mut acc: HashMap<&str, i64>, t| {
        *acc.entry(t.account.as_str()).or_default() += t.amount;
        acc
    });
    let spent: i64 = txs.iter().map(|t| t.amount).filter(|&a| a < 0).sum();
    let top = txs.iter().max_by_key(|t| t.amount).map(|t| t.account.clone()).unwrap_or_default();
    // collect Result-ba: az első hibánál megáll (mint a traverse)
    let all: Result<Vec<Tx>, String> = input.lines().map(parse_line).collect();

    println!("{balances:?} kiadás={spent} legnagyobb={top} hibák={errors:?} mind_ok={}", all.is_ok());
}
```

```csharp
using System;
using System.Collections.Immutable;
using System.Linq;

public record Tx(string Account, decimal Amount);      // immutábilis, érték-egyenlőség, with

public abstract record Shape;                          // ADT-szerű zárt hierarchia
public sealed record Circle(double R) : Shape;
public sealed record Rect(double W, double H) : Shape;

public static class Program
{
    static double Area(Shape s) => s switch            // switch-kifejezés mintaillesztéssel
    {
        Circle { R: <= 0 } => 0,
        Circle c => Math.PI * c.R * c.R,
        Rect(var w, var h) => w * h,
        _ => throw new ArgumentOutOfRangeException(nameof(s)),
    };

    public static void Main()
    {
        var txs = ImmutableList.Create(new Tx("a", 100m), new Tx("b", -20m), new Tx("a", -30m));
        var withFee = txs.Select(t => t with { Amount = Math.Round(t.Amount * 0.99m, 2) }).ToImmutableList();

        var balances = txs.GroupBy(t => t.Account)
                          .Select(g => (Account: g.Key, Balance: g.Sum(t => t.Amount)))
                          .OrderByDescending(x => x.Balance)
                          .ToList();                   // materializálás: ne fusson le újra
        var spent = txs.Where(t => t.Amount < 0).Aggregate(0m, (acc, t) => acc + t.Amount);

        Func<decimal, decimal> vat = x => x * 1.27m;
        Func<decimal, decimal> round = x => Math.Round(x, 0);
        Func<decimal, decimal> gross = x => round(vat(x));   // kompozíció

        balances.ForEach(b => Console.WriteLine($"{b.Account}: {b.Balance}"));
        Console.WriteLine($"{spent} {gross(1000m)} {Area(new Rect(2, 3))} {txs[0] == new Tx("a", 100m)} {withFee[0]}");
    }
}
```
