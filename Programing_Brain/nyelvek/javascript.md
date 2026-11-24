# JavaScript
<!-- tech: javascript -->
<!-- aliases: js, ecmascript, es6, es2015, esnext, vanilla js -->

A JavaScript dinamikusan és gyengén típusos, prototípus-alapú, többparadigmás nyelv (objektumorientált és funkcionális), amelyet az ECMAScript szabvány ír le; a böngészők egyetlen natív nyelve, szerveren Node.js, Deno és Bun futtatja. A motorok (V8, SpiderMonkey, JavaScriptCore) JIT-fordítással érnek el jó teljesítményt, a memóriát generációs szemétgyűjtő kezeli. A kód egy szálon fut egy event loop körül, a konkurenciát Promise-ok, async/await és callbackek adják (párhuzamossághoz Web Workerek kellenek). Erőssége az univerzális elérhetőség, a hatalmas ökoszisztéma (npm) és az aszinkron I/O; gyengéje a laza típuskonverzió és a futásidőben kiderülő hibák — nagyobb kódbázisnál ezért gyakran TypeScripttel használják.

## Típusok, egyenlőség és típuskonverzió
<!-- q: Mi a különbség a == és a === között JavaScriptben, és milyen buktatói vannak a típuskonverziónak? -->
<!-- tags: types, coercion, equality, nan, bigint, truthy, falsy, nullish -->

A JavaScriptnek hét primitív típusa van (string, number, bigint, boolean, undefined, symbol, null), minden más objektum; a primitívek érték, az objektumok referencia szerint másolódnak. Az `==` implicit típuskonverziót végez (abstract equality), ezért szinte mindig `===`-t használj — az egyetlen idiomatikus kivétel az `x == null`, ami null-ra és undefinedra is igaz. A number IEEE 754 double, ezért `0.1 + 0.2 !== 0.3`, és 2^53 felett elveszik a pontosság (ilyenkor BigInt kell). A `??` csak null/undefined esetén ad alapértéket, a `||` minden falsy értéknél (0, '' is), ami gyakori hibaforrás.

```js
// Futtatható: node tipusok.mjs
console.log(typeof null, typeof (() => {}), Array.isArray([])); // 'object' 'function' true
// typeof null === 'object' történelmi hiba: null-t így ellenőrizd: x === null

console.log(0 == '', '0' == false, null == undefined); // true true true – konverzió!
console.log(0 === '', null === undefined);             // false false

// NaN nem egyenlő önmagával; Object.is a "SameValue" összehasonlítás
console.log(NaN === NaN, Number.isNaN(NaN), Object.is(NaN, NaN)); // false true true
console.log(Object.is(0, -0), 0 === -0);                           // false true

// Lebegőpontos pontatlanság – pénzt egész fillérben vagy BigInt-ben tárolj
console.log(0.1 + 0.2 === 0.3);                                    // false
const kozel = (a, b) => Math.abs(a - b) < Number.EPSILON * Math.max(1, Math.abs(a), Math.abs(b));
console.log(kozel(0.1 + 0.2, 0.3));                                // true
console.log(Number.MAX_SAFE_INTEGER + 2, 2n ** 64n);               // 9007199254740992 (pontatlan!) 18446744073709551616n

// Implicit konverzió: a + string-összefűzést preferál, a - számmá alakít
console.log('5' + 3, '5' - 3, [] + {}, [1, 2] + [3]);              // '53' 2 '[object Object]' '1,23'
console.log(parseInt('08px', 10), Number('08px'), +'');            // 8 NaN 0

// Falsy: false, 0, -0, 0n, '', null, undefined, NaN – minden más truthy ('0' és [] is!)
console.log([0, '0', '', [], {}, null, NaN].map(Boolean));

// ?? vs ||: a 0 és '' érvényes érték lehet
const beallitas = { timeout: 0, nev: '' };
console.log(beallitas.timeout || 3000, beallitas.timeout ?? 3000); // 3000 0
beallitas.nev ||= 'névtelen';   // logikai értékadás (ES2021)
beallitas.retry ??= 3;

// Referencia vs másolat
const a = { lista: [1, 2], letrehozva: new Date(0) };
const sekely = { ...a };              // csak a felső szint új objektum
const mely = structuredClone(a);      // mély másolat (Date, Map, Set, ciklusok is)
a.lista.push(3);
console.log(sekely.lista, mely.lista, mely.letrehozva instanceof Date); // [1,2,3] [1,2] true

// Opcionális láncolás: rövidzár, ha a bal oldal null/undefined
const valasz = { adat: { felhasznalo: null } };
console.log(valasz.adat?.felhasznalo?.nev ?? 'ismeretlen', valasz.lekerdez?.());
```

## Scope, hoisting, TDZ és closure-ök
<!-- q: Hogyan működik a scope, a hoisting és a closure JavaScriptben? -->
<!-- tags: scope, hoisting, tdz, closure, var, let, const, lexical environment -->

A `var` függvény-scope-ú és `undefined` értékkel hoistolódik, a `let`/`const` blokk-scope-ú, és a deklarációig a Temporal Dead Zone-ban van (előtte elérve ReferenceError). A függvénydeklaráció teljes egészében hoistolódik, a függvénykifejezés nem. A closure azt jelenti, hogy a függvény a létrehozásakor érvényes lexikális környezetre hivatkozik (nem másolatra), így privát, állapotos függvények készíthetők. Buktató: a closure a teljes környezetet életben tarthatja (memória), és a `var` ciklusváltozót minden callback közösen látja.

```js
function hoisting() {
  console.log(v);                 // undefined: a deklaráció "felkerült", az értékadás nem
  var v = 1;
  try {
    console.log(l);               // TDZ: a let már létezik, de még nem inicializált
  } catch (e) {
    console.log(e.constructor.name); // ReferenceError
  }
  let l = 2;
  console.log(fv(), v + l);       // a függvénydeklaráció teljesen hoistolódik
  function fv() { return 'deklaráció'; }
}
hoisting();

// Closure: privát állapot osztály nélkül
function szamlaloGyar(kezdo = 0) {
  let ertek = kezdo;              // kívülről nem érhető el
  return {
    novel: () => ++ertek,
    nullaz: () => { ertek = 0; },
    get ertek() { return ertek; },
  };
}
const sz = szamlaloGyar(10);
sz.novel(); sz.novel();
console.log(sz.ertek);            // 12

// Klasszikus csapda: var -> egyetlen közös változó; let -> iterációnként új kötés
const rossz = [];
for (var i = 0; i < 3; i++) rossz.push(() => i);
const jo = [];
for (let j = 0; j < 3; j++) jo.push(() => j);
console.log(rossz.map((f) => f()), jo.map((f) => f())); // [3,3,3] [0,1,2]

// Gyakorlati closure: egyszer lefutó függvény (pl. lusta inicializálás)
function egyszer(fn) {
  let lefutott = false;
  let eredmeny;
  return function (...args) {
    if (!lefutott) {
      lefutott = true;
      eredmeny = fn.apply(this, args);
    }
    return eredmeny;
  };
}
const init = egyszer(() => { console.log('inicializálás…'); return 42; });
console.log(init(), init());      // az üzenet csak egyszer jelenik meg

// Memória: csak azt zárd be, amire tényleg szükség van
function nagyAdatKezelo() {
  const nagy = new Array(1_000_000).fill('x');
  const hossz = nagy.length;      // a visszaadott függvény csak ezt használja
  return () => hossz;             // a `nagy` tömb így felszabadulhat
}
console.log(nagyAdatKezelo()());
```

## A this kötése: metódus, bind, call/apply és nyílfüggvény
<!-- q: Miért undefined a this JavaScriptben, ha callbackként adok át egy metódust? -->
<!-- tags: this, bind, call, apply, arrow functions, method extraction, class fields -->

A `this` értékét a hívás módja határozza meg, nem a definíció helye: `obj.metodus()` esetén az `obj`, sima `fn()` hívásnál strict módban (modulok, osztályok) `undefined`, `new`-val az új objektum. Ha egy metódust leválasztasz (callbackként átadod), elveszik a kötés — ezt `bind`-dal, nyílfüggvényes class fielddel vagy csomagoló nyílfüggvénnyel lehet megoldani. A nyílfüggvénynek nincs saját `this`-e (és `arguments`-e), a környező lexikális `this`-t látja, ezért nem jó objektum-metódusnak, de kiváló callbacknek. A `call`/`apply` egyszeri hívást végez megadott `this`-szel.

```js
const szamlalo = {
  db: 0,
  novel() { this.db++; return this; },       // metódus-hívás: this = a pont előtti objektum
  kesleltetve() {
    // A nyílfüggvény a kesleltetve() this-ét látja, így a callbackben is működik
    setTimeout(() => { this.novel(); console.log('nyílfüggvényes callback:', this.db); }, 0);
  },
};
szamlalo.novel().novel();                    // láncolás: a metódus this-t ad vissza

const levalasztott = szamlalo.novel;
try {
  levalasztott();                            // sima hívás: this === undefined (strict)
} catch (e) {
  console.log('leválasztott metódus:', e.constructor.name);
}
const kotott = szamlalo.novel.bind(szamlalo); // új függvény rögzített this-szel
kotott();
console.log(szamlalo.db);                    // 3

function bemutat(udvozles, irasjel) { return `${udvozles}, ${this.nev}${irasjel}`; }
console.log(bemutat.call({ nev: 'modul' }, 'Szia', '!'));       // argumentumok egyenként
console.log(bemutat.apply({ nev: 'szerver' }, ['Helló', '?'])); // argumentumok tömbben

class Gomb {
  #kattintasok = 0;
  constructor(cimke) { this.cimke = cimke; }
  // Class field nyílfüggvénnyel: példányonként kötött, biztonságos eseménykezelő
  kezelo = () => `${this.cimke}: ${++this.#kattintasok}`;
  // Prototípus-metódus: leválasztva elveszíti a this-t
  rosszKezelo() { return this.cimke; }
}
const g = new Gomb('Mentés');
const callbackek = [g.kezelo, g.rosszKezelo];
console.log(callbackek[0](), callbackek[0]());   // 'Mentés: 1' 'Mentés: 2'
try {
  callbackek[1]();
} catch (e) {
  console.log('rosszKezelo:', e.message);
}

// new: új objektum, a this arra mutat, a [[Prototype]] a Fv.prototype lesz
function Pont(x, y) { this.x = x; this.y = y; }
Pont.prototype.hossz = function () { return Math.hypot(this.x, this.y); };
console.log(new Pont(3, 4).hossz());
const nyil = () => {};
try { new nyil(); } catch (e) { console.log('nyílfüggvény nem konstruktor:', e.constructor.name); }
szamlalo.kesleltetve();
```

## Prototípusok, osztályok és privát mezők
<!-- q: Hogyan működik a prototípus-lánc és a class szintaxis JavaScriptben? -->
<!-- tags: prototype, prototype chain, class, inheritance, private fields, static, mixin -->

Minden objektumnak van egy `[[Prototype]]` hivatkozása; ha egy property nincs az objektumon, a motor a láncon felfelé keresi egészen `Object.prototype`-ig, majd `null`-ig. A `class` szintaktikai cukor a konstruktorfüggvény + `prototype` fölött, de hoz valódi újdonságokat: `#privát` mezőket és metódusokat (kívülről elérhetetlenek, nem csak konvenció), `static` blokkot, és `#mezo in obj` brand checket. Öröklésnél a `super()` hívás előtt nem használható a `this`. Többszörös öröklés nincs, helyette mixin (osztályt visszaadó függvény) vagy kompozíció.

```js
const allat = { hang() { return `${this.nev} hangot ad`; } };
const kutya = Object.create(allat, { nev: { value: 'Bodri', enumerable: true } });
console.log(kutya.hang(), Object.getPrototypeOf(kutya) === allat, Object.hasOwn(kutya, 'hang'));

class Alakzat {
  static #peldanyok = 0;            // privát statikus mező
  #azon;                            // valódi privát példánymező
  static {                          // statikus inicializáló blokk
    Alakzat.tipusok = new Set();
  }
  constructor(nev) {
    if (new.target === Alakzat) throw new TypeError('az Alakzat absztrakt');
    this.nev = nev;
    this.#azon = ++Alakzat.#peldanyok;
    Alakzat.tipusok.add(new.target.name);
  }
  terulet() { throw new Error('nincs implementálva'); }
  get azon() { return this.#azon; }
  toString() { return `${this.nev}#${this.#azon} (${this.terulet().toFixed(2)})`; }
  static darab() { return Alakzat.#peldanyok; }
  static isAlakzat(o) { return #azon in o; } // brand check: valóban Alakzat-példány-e
}

class Kor extends Alakzat {
  constructor(r) {
    super('kör');                   // super() előtt a this nem használható
    this.r = r;
  }
  terulet() { return Math.PI * this.r ** 2; }
}

class Teglalap extends Alakzat {
  constructor(a, b) { super('téglalap'); Object.assign(this, { a, b }); }
  terulet() { return this.a * this.b; }
}

const alakzatok = [new Kor(1), new Teglalap(2, 3)];
console.log(alakzatok.map(String), Alakzat.darab(), [...Alakzat.tipusok]);
console.log(Alakzat.isAlakzat(alakzatok[0]), Alakzat.isAlakzat({ nev: 'hamis' })); // true false

// A lánc: példány -> Kor.prototype -> Alakzat.prototype -> Object.prototype -> null
console.log(Object.getPrototypeOf(Kor.prototype) === Alakzat.prototype, typeof Kor); // true 'function'

// Mixin: osztályt bővítő függvény
const Szerializalhato = (Os) => class extends Os {
  toJSON() { return { tipus: this.constructor.name, ...this }; } // privát mezők nem kerülnek bele
};
class MentettKor extends Szerializalhato(Kor) {}
console.log(JSON.stringify(new MentettKor(2)));
try { new Alakzat('x'); } catch (e) { console.log(e.message); }
```

## Iterátorok, generátorok és async iterátorok
<!-- q: Hogyan készítsek saját iterálható objektumot és lusta adatfolyamot generátorokkal JavaScriptben? -->
<!-- tags: iterators, generators, symbol.iterator, async generators, for await, lazy evaluation -->

Egy objektum iterálható, ha van `[Symbol.iterator]()` metódusa, amely `{ next() }` objektumot ad vissza `{ value, done }` eredményekkel — erre épül a `for...of`, a spread és a destructuring. A `function*` generátor a legegyszerűbb módja: lustán állítja elő az elemeket, így végtelen sorozat és memóriatakarékos pipeline is írható. A generátor kétirányú: `next(ertek)` értéket küld be, a korai `return` (pl. `break`) a forrás iterátort is lezárja. Az `async function*` és a `for await` lapozott API-k, streamek fogyasztására való.

```js
class Tartomany {
  constructor(tol, ig, lepes = 1) { Object.assign(this, { tol, ig, lepes }); }
  *[Symbol.iterator]() {                       // generátor metódus mint iterátor
    for (let i = this.tol; i < this.ig; i += this.lepes) yield i;
  }
}
console.log([...new Tartomany(0, 10, 3)]);     // [0, 3, 6, 9]

// Lusta pipeline: semmi nem fut, amíg nem kérünk elemet
function* szur(it, pred) { for (const x of it) if (pred(x)) yield x; }
function* lekepez(it, fn) { for (const x of it) yield fn(x); }
function* elso(it, n) {
  if (n <= 0) return;
  for (const x of it) { yield x; if (--n <= 0) return; } // return -> a forrás is lezárul
}
function* termeszetes() { let n = 1; while (true) yield n++; } // végtelen, de lusta
console.log([...elso(lekepez(szur(termeszetes(), (n) => n % 7 === 0), (n) => n * n), 4)]);

// Kétirányú kommunikáció next(ertek)-kel
function* azonositoGyar(prefix) {
  let n = 0;
  while (true) {
    const reset = yield `${prefix}-${++n}`;
    if (reset) n = 0;
  }
}
const ids = azonositoGyar('rendeles');
console.log(ids.next().value, ids.next().value, ids.next(true).value); // -1 -2 -1

// Async generátor: lapozott API "streamelése" (szimulált hálózat)
async function* lapozo(osszesLap) {
  for (let lap = 1; lap <= osszesLap; lap++) {
    await new Promise((r) => setTimeout(r, 10));
    yield { lap, elemek: Array.from({ length: 3 }, (_, i) => `elem-${lap}-${i}`) };
  }
}
for await (const { lap, elemek } of lapozo(3)) {  // top-level await ES modulban
  console.log(lap, elemek.join(', '));
}

// Iterator helpers (ES2025, Node 22+): lusta map/filter/take közvetlenül iterátoron
if (typeof Iterator !== 'undefined' && Iterator.prototype.take) {
  console.log(termeszetes().filter((n) => n % 2).map((n) => n * 10).take(3).toArray());
}
```

## Promise-ok és async/await: kombinátorok, időkorlát, párhuzamossági korlát
<!-- q: Hogyan futtassak párhuzamosan aszinkron műveleteket JavaScriptben időkorláttal és limittel? -->
<!-- tags: promise, async, await, promise.all, allsettled, abortcontroller, retry, concurrency limit -->

A Promise egy jövőbeli érték, amely pending állapotból egyszer és véglegesen fulfilled vagy rejected lesz; a `then` callbackjei mindig aszinkron (microtaskként) futnak. Az `async` függvény mindig Promise-t ad, az `await` felfüggeszti a függvényt az érték megérkezéséig, a hiba pedig `try/catch`-csel kapható el. Párhuzamos futtatáshoz előbb indítsd el a műveleteket, és csak utána várd meg őket (`Promise.all`, `allSettled`, `race`, `any`); sok feladatnál korlátozd az egyidejűséget. Megszakításra az `AbortController`/`AbortSignal` a szabványos eszköz. Buktató: a `forEach` nem várja meg az async callbacket, és a `try`-ban `return await` kell, különben a hiba nem itt kapódik el.

```js
const varj = (ms, ertek, hiba = false) =>
  new Promise((resolve, reject) => setTimeout(() => (hiba ? reject(new Error(ertek)) : resolve(ertek)), ms));

const [mind, telepitve, leggyorsabb, elsoSiker] = await Promise.all([
  Promise.all([varj(30, 'a'), varj(10, 'b')]),                 // bármelyik hiba -> az egész rejected
  Promise.allSettled([varj(10, 'ok'), varj(5, 'hiba', true)]), // mindig minden eredmény
  Promise.race([varj(50, 'lassú'), varj(5, 'gyors')]),         // az első befejeződő
  Promise.any([varj(5, 'x', true), varj(20, 'első siker')]),   // az első SIKERES
]);
console.log(mind, telepitve.map((r) => r.status), leggyorsabb, elsoSiker);

async function megszakithatoMunka(signal) {
  for (let lepes = 0; lepes < 10; lepes++) {
    signal.throwIfAborted();                   // kooperatív megszakítás lépésenként
    await new Promise((r) => setTimeout(r, 20));
  }
  return 'kész';
}
try {
  await megszakithatoMunka(AbortSignal.timeout(50)); // fetch(url, { signal }) ugyanígy
} catch (e) {
  console.log('megszakítva:', e.name);         // TimeoutError
}

async function ujraprobal(fn, { kiserlet = 3, alap = 20 } = {}) {
  for (let n = 1; ; n++) {
    try {
      return await fn(n);                      // return await: így a catch elkapja a hibát
    } catch (e) {
      if (n >= kiserlet) throw new Error(`${kiserlet} próbálkozás után is hiba`, { cause: e });
      await new Promise((r) => setTimeout(r, alap * 2 ** (n - 1))); // exponenciális backoff
    }
  }
}
console.log(await ujraprobal(async (n) => {
  if (n < 3) throw new Error('átmeneti');
  return `siker a ${n}. próbára`;
}));

// Párhuzamossági korlát: N "worker" húzza a közös sorból a feladatokat
async function korlatozott(feladatok, limit) {
  const eredmeny = new Array(feladatok.length);
  let kovetkezo = 0;
  async function worker() {
    while (kovetkezo < feladatok.length) {
      const i = kovetkezo++;                   // egy szál: az index-foglalás atomikus
      eredmeny[i] = await feladatok[i]();
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, feladatok.length) }, worker));
  return eredmeny;                             // az eredeti sorrendben
}
const feladatok = Array.from({ length: 8 }, (_, i) => () => varj(10 + (i % 3) * 10, i * i));
console.log(await korlatozott(feladatok, 3));
```

## Event loop: call stack, microtask és macrotask
<!-- q: Milyen sorrendben fut le a szinkron kód, a Promise.then és a setTimeout JavaScriptben? -->
<!-- tags: event loop, microtask, macrotask, queuemicrotask, settimeout, call stack, blocking -->

A JavaScript egy szálon fut: a call stack kiürülése után az event loop először a teljes microtask-sort üríti (Promise callbackek, `await` folytatások, `queueMicrotask`), és csak utána vesz ki egy macrotaskot (timer, I/O, UI esemény), majd a böngésző renderelhet. Ezért egy `setTimeout(fn, 0)` mindig az összes már sorban álló microtask után fut, és egy végtelenül újraütemezett microtask-lánc "kiéheztetheti" a timereket és a renderelést. Hosszú szinkron számítás közben semmi más nem fut (fagyott UI, válaszolni nem tudó szerver) — darabold fel, és darabok között add vissza a vezérlést, vagy tedd Workerbe.

```js
// Futtatható: node esemenyhurok.mjs – a betűk a kiírás sorrendjét mutatják
console.log('A: szinkron kód (call stack)');

setTimeout(() => console.log('H: macrotask (setTimeout 0)'), 0);

Promise.resolve()
  .then(() => console.log('D: microtask – then #1'))
  .then(() => console.log('G: microtask – then #2 (csak az #1 után kerül sorba)'));

queueMicrotask(() => console.log('E: microtask – queueMicrotask'));

(async () => {
  console.log('B: async függvény szinkron része, az első await-ig');
  await null;                       // a folytatás microtaskként kerül sorba
  console.log('F: await utáni rész');
})();

console.log('C: szinkron kód vége – most ürül a microtask-sor: D E F G, majd jön H');

// Hosszú számítás darabolása: darabonként visszaadjuk a vezérlést az event loopnak
const enged = () => new Promise((r) => setTimeout(r, 0)); // böngészőben: scheduler.yield(), ha van
async function nagyOsszeg(n, darab = 1_000_000) {
  let osszeg = 0;
  for (let i = 0; i < n; i++) {
    osszeg += i;
    if (i % darab === 0) await enged(); // macrotask-határ: más események is sorra kerülnek
  }
  return osszeg;
}

setTimeout(() => console.log('I: ez az időzítő a számítás KÖZBEN fut le'), 5);
const t0 = performance.now();
console.log('J: összeg', await nagyOsszeg(20_000_000), `${(performance.now() - t0).toFixed(0)} ms`);

// Ellenpélda (ne futtasd): a darabolás nélküli ciklus alatt az 'I' időzítő is csak a végén futna,
// a böngésző nem renderelne, és a szerver nem fogadna kéréseket.
```

## Proxy és Reflect: metaprogramozás
<!-- q: Mire jó a Proxy és a Reflect JavaScriptben, és hogyan építsek vele validációt vagy reaktív állapotot? -->
<!-- tags: proxy, reflect, metaprogramming, traps, validation, reactivity, observable -->

A `Proxy` egy célobjektum köré tett réteg, amelynek "trap"-jei elfogják az alapműveleteket (`get`, `set`, `has`, `deleteProperty`, `apply`, `construct` stb.). A `Reflect` ugyanezeket az alapműveleteket teszi elérhetővé függvényként, így a trapben `Reflect.set(...)`-tel delegálhatunk az alapértelmezett viselkedéshez (helyes `receiver`-rel, getterek és öröklés esetén is). Tipikus felhasználás: validáció, reaktivitás (a Vue 3 erre épül), naplózás, lusta betöltés, negatív indexelés. Buktatók: lassabb a natív elérésnél, a `set` trapnek `true`-t kell visszaadnia (strict módban különben TypeError), és a `#privát` mezőket nem tudja "átlátszóan" átengedni.

```js
function validalt(cel, sema) {
  return new Proxy(cel, {
    set(obj, kulcs, ertek, receiver) {
      const ellenor = sema[kulcs];
      if (!ellenor) throw new TypeError(`ismeretlen mező: ${String(kulcs)}`);
      if (!ellenor(ertek)) throw new RangeError(`érvénytelen: ${String(kulcs)}=${ertek}`);
      return Reflect.set(obj, kulcs, ertek, receiver); // alapértelmezett viselkedés, true-t ad
    },
    deleteProperty(_obj, kulcs) { throw new Error(`${String(kulcs)} nem törölhető`); },
  });
}
const felh = validalt({}, {
  nev: (v) => typeof v === 'string' && v.length > 0,
  kor: (v) => Number.isInteger(v) && v >= 0 && v < 150,
});
felh.nev = 'teszt';
felh.kor = 30;
for (const hibas of [() => { felh.kor = -1; }, () => { felh.jelszo = 'x'; }, () => delete felh.nev]) {
  try { hibas(); } catch (e) { console.log(e.constructor.name, e.message); }
}

// Reaktív állapot: beágyazott objektumokat lustán, egyszer proxyzunk (WeakMap cache)
function reaktiv(allapot, onValtozas) {
  const cache = new WeakMap();
  const keszit = (obj, ut) => {
    if (cache.has(obj)) return cache.get(obj);
    const p = new Proxy(obj, {
      get(o, k, r) {
        const ertek = Reflect.get(o, k, r);
        return ertek && typeof ertek === 'object' ? keszit(ertek, [...ut, String(k)]) : ertek;
      },
      set(o, k, v, r) {
        const regi = o[k];
        const ok = Reflect.set(o, k, v, r);
        if (ok && regi !== v) onValtozas([...ut, String(k)].join('.'), regi, v);
        return ok;
      },
    });
    cache.set(obj, p);
    return p;
  };
  return keszit(allapot, []);
}
const allapot = reaktiv({ kosar: { tetelek: [] }, tema: 'sötét' }, (ut, regi, uj) =>
  console.log(`változás ${ut}: ${JSON.stringify(regi)} -> ${JSON.stringify(uj)}`));
allapot.tema = 'világos';
allapot.kosar.tetelek.push('kávé');  // a push is set trapet vált ki ('0' index)

const negativ = (tomb) => new Proxy(tomb, {
  get: (t, k, r) => (typeof k === 'string' && /^-\d+$/.test(k) ? t[t.length + Number(k)] : Reflect.get(t, k, r)),
});
console.log(negativ([1, 2, 3])[-1]); // 3 (natívan: [1, 2, 3].at(-1))
```

## Property descriptorok, getterek, Symbol-ok és Object.freeze
<!-- q: Hogyan szabályozzam egy objektum property-jeinek viselkedését JavaScriptben, és mire jók a Symbol-ok? -->
<!-- tags: property descriptor, defineproperty, getter, setter, symbol, well-known symbols, freeze, immutability -->

Minden property-nek van leírója: adat-property esetén `value`/`writable`, accessor esetén `get`/`set`, valamint `enumerable` (megjelenik-e `Object.keys`-ben, JSON-ban) és `configurable` (törölhető/átdefiniálható-e). A `Symbol` egyedi, ütközésmentes kulcs, amely nem jelenik meg a szokásos felsorolásokban; a well-known symbolokkal (`Symbol.iterator`, `Symbol.toPrimitive`, `Symbol.hasInstance`…) a nyelvi viselkedés szabható testre. Az `Object.freeze` csak sekély, a beágyazott objektumokat rekurzívan kell fagyasztani; strict módban a fagyasztott objektum módosítása TypeError-t dob.

```js
const konfig = {};
Object.defineProperty(konfig, 'verzio', { value: '2.1.0', writable: false, enumerable: true, configurable: false });
Object.defineProperty(konfig, '_belso', { value: 'rejtett', enumerable: false });
console.log(Object.keys(konfig), JSON.stringify(konfig)); // ['verzio'] – a nem enumerable rejtve
try { konfig.verzio = '3.0'; } catch (e) { console.log('írásvédett:', e.constructor.name); }

class Homero {
  #celsius = 0;
  get celsius() { return this.#celsius; }
  set celsius(c) {
    if (c < -273.15) throw new RangeError('abszolút nulla alatt');
    this.#celsius = c;
  }
  get fahrenheit() { return this.#celsius * 9 / 5 + 32; }  // számított property
  set fahrenheit(f) { this.celsius = (f - 32) * 5 / 9; }   // a validáló setteren megy át
}
const h = new Homero();
h.fahrenheit = 212;
console.log(h.celsius); // 100

const META = Symbol('meta');                 // egyedi kulcs, nem ütközik
const rekord = { id: 1, [META]: { betoltve: Date.now() } };
console.log(Object.keys(rekord), Object.getOwnPropertySymbols(rekord).length, JSON.stringify(rekord));

class Penz {
  constructor(filler, penznem = 'HUF') { this.filler = filler; this.penznem = penznem; }
  [Symbol.toPrimitive](hint) {               // `${p}`, +p, p > q viselkedése
    return hint === 'string' ? `${(this.filler / 100).toFixed(2)} ${this.penznem}` : this.filler;
  }
  get [Symbol.toStringTag]() { return 'Penz'; }
  static [Symbol.hasInstance](o) { return typeof o?.filler === 'number'; } // instanceof testreszabás
}
const p = new Penz(123456);
console.log(`${p}`, p + 1, p > new Penz(100), Object.prototype.toString.call(p), { filler: 5 } instanceof Penz);

const deepFreeze = (o) => {
  for (const v of Object.values(o)) if (typeof v === 'object' && v !== null) deepFreeze(v);
  return Object.freeze(o);
};
const allando = deepFreeze({ szerver: { port: 8080 }, tagok: ['a'] });
try { allando.szerver.port = 1; } catch (e) { console.log('mélyen fagyasztva:', e.constructor.name); }
console.log(Object.isFrozen(allando.tagok));
// seal: nem bővíthető/törölhető, de írható; preventExtensions: csak új property tilos
```

## Map, Set, WeakMap, WeakRef és memóriaszivárgások
<!-- q: Mikor használjak Map-et, Set-et vagy WeakMap-et JavaScriptben, és hogyan kerüljem el a memóriaszivárgást? -->
<!-- tags: map, set, weakmap, weakref, finalizationregistry, garbage collection, memory leak, lru cache -->

A `Map` bármilyen kulcsot (objektumot is) elfogad, megőrzi a beszúrási sorrendet és gyakori hozzáadás/törlés mellett gyorsabb egy sima objektumnál; a `Set` egyedi értékeket tárol (ES2025-től halmazműveletekkel). A `WeakMap` kulcsa gyenge referencia: ha az objektumra máshol nincs hivatkozás, a GC a bejegyzéssel együtt felszabadítja — ideális idegen objektumokhoz vagy DOM-elemekhez csatolt metaadatra. A `WeakRef` és `FinalizationRegistry` gyenge cache-hez való, de a GC időzítése nem determinisztikus, ezért üzleti logika ne épüljön rá. A leggyakoribb szivárgások: korlát nélkül növő cache, le nem iratkozott eseménykezelők, leállítatlan `setInterval`, nagy objektumot bezáró closure.

```js
const latogatok = new Map();
const munkamenet = { id: 'm1' };
latogatok.set(munkamenet, 1).set('anonim', 5);       // objektum is lehet kulcs
console.log(latogatok.get(munkamenet), latogatok.size);

const a = new Set(['js', 'ts', 'py']);
const b = new Set(['py', 'go']);
if (a.union) console.log([...a.intersection(b)], [...a.difference(b)]); // ES2025 (Node 22+)
console.log([...new Set([3, 1, 3, 2, 1])]);           // duplikátumszűrés

// WeakMap: metaadat úgy, hogy nem tartjuk életben a kulcsobjektumot
const meta = new WeakMap();
let ideiglenes = { nagy: new Array(1e5).fill(0) };
meta.set(ideiglenes, { forras: 'import', ido: Date.now() });
ideiglenes = null;                                    // a GC felszabadíthatja a bejegyzéssel együtt

class GyengeCache {
  #map = new Map();
  #takarito = new FinalizationRegistry((kulcs) => {
    if (!this.#map.get(kulcs)?.deref()) this.#map.delete(kulcs); // csak a halott bejegyzést
  });
  set(kulcs, ertek) {
    this.#map.set(kulcs, new WeakRef(ertek));
    this.#takarito.register(ertek, kulcs);
  }
  get(kulcs) { return this.#map.get(kulcs)?.deref(); } // undefined, ha már begyűjtötték
}
const gyenge = new GyengeCache();
gyenge.set('kep:1', { pixelek: new Uint8Array(1024) });
console.log('még a cache-ben:', gyenge.get('kep:1') !== undefined);

// Korlátos LRU cache: a Map beszúrási sorrendjét használjuk ki
class LruCache {
  constructor(max = 100) { this.max = max; this.map = new Map(); }
  get(k) {
    if (!this.map.has(k)) return undefined;
    const v = this.map.get(k);
    this.map.delete(k);
    this.map.set(k, v);                               // a végére kerül = legutóbb használt
    return v;
  }
  set(k, v) {
    this.map.delete(k);
    this.map.set(k, v);
    if (this.map.size > this.max) this.map.delete(this.map.keys().next().value); // legrégebbi ki
  }
}
const lru = new LruCache(2);
lru.set('a', 1); lru.set('b', 2); lru.get('a'); lru.set('c', 3);
console.log([...lru.map.keys()]);                     // ['a', 'c']

// Szivárgás-megelőzés: AbortSignal-lal egyszerre leiratkoztatható minden listener
const vezerlo = new AbortController();
const cel = new EventTarget();
cel.addEventListener('frissites', () => console.log('frissítve'), { signal: vezerlo.signal });
cel.dispatchEvent(new Event('frissites'));
vezerlo.abort();                                      // minden ehhez kötött listener eltávolítva
cel.dispatchEvent(new Event('frissites'));            // már nem ír ki semmit
```

## Hibakezelés: saját Error osztályok, cause és AggregateError
<!-- q: Hogyan kezeljem a hibákat JavaScriptben szinkron és aszinkron kódban, saját hibaosztályokkal? -->
<!-- tags: error handling, error, cause, aggregateerror, try catch, finally, unhandled rejection -->

Mindig `Error` (vagy leszármazott) példányt dobj, mert csak az hordoz stack trace-t; saját alosztállyal (`name` beállításával, extra mezőkkel) a hívó `instanceof`-fal tud különbséget tenni. Az ES2022 `cause` opcióval az eredeti hiba láncolható, így nem vész el a kiváltó ok. Több független hiba egyszerre `AggregateError`-ként adható vissza (ezt dobja a `Promise.any` is). Aszinkron kódban a kezeletlen rejection Node-ban alapértelmezetten leállítja a folyamatot, ezért minden Promise-láncnak legyen gazdája; a `finally`-ben ne legyen `return`, mert felülírja az eredményt.

```js
class AppHiba extends Error {
  constructor(uzenet, opciok) {
    super(uzenet, opciok);              // { cause } továbbadása
    this.name = new.target.name;        // alosztályban is a helyes név
  }
}
class ValidaciosHiba extends AppHiba {
  constructor(mezo, uzenet) { super(`${mezo}: ${uzenet}`); this.mezo = mezo; }
}
class HttpHiba extends AppHiba {
  constructor(statusz, uzenet, opciok) { super(uzenet, opciok); this.statusz = statusz; }
  get ujraprobalhato() { return this.statusz >= 500 || this.statusz === 429; }
}

function konfigOlvas(nyers) {
  try {
    return JSON.parse(nyers);
  } catch (e) {
    throw new AppHiba('hibás konfiguráció', { cause: e }); // az ok megmarad
  }
}
try {
  konfigOlvas('{port: 80}');
} catch (e) {
  console.log(e.name, e.message, '<- oka:', e.cause.name);  // AppHiba ... SyntaxError
}

// Bármi dobható ('string', szám) – catch-ben normalizáld
const normalizal = (e) => (e instanceof Error ? e : new Error(String(e)));
try { throw 'string hiba'; } catch (e) { console.log(normalizal(e).message); }

function validal({ email, kor }) {
  const hibak = [];
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email ?? '')) hibak.push(new ValidaciosHiba('email', 'érvénytelen'));
  if (!Number.isInteger(kor) || kor < 0) hibak.push(new ValidaciosHiba('kor', 'nem negatív egész kell'));
  if (hibak.length) throw new AggregateError(hibak, 'érvénytelen űrlap');
}
try {
  validal({ email: 'rossz', kor: -2 });
} catch (e) {
  if (e instanceof AggregateError) console.log(e.message, e.errors.map((h) => h.mezo));
}

async function lekeres(statusz) {
  if (statusz >= 400) throw new HttpHiba(statusz, `HTTP ${statusz}`);
  return { ok: true };
}
for (const r of await Promise.allSettled([lekeres(200), lekeres(503), lekeres(404)])) {
  if (r.status === 'rejected') console.log(r.reason.message, 'újrapróbálható:', r.reason.ujraprobalhato);
}

function takaritassal() {
  const eroforras = { nyitva: true };
  try {
    throw new Error('hiba közben');
  } catch (e) {
    return `kezelve: ${e.message}`;
  } finally {
    eroforras.nyitva = false;           // a catch return-je előtt fut le
    console.log('erőforrás lezárva:', !eroforras.nyitva);
  }
}
console.log(takaritassal());
```

## ES modulok: import/export, live binding, dinamikus import
<!-- q: Hogyan működnek az ES modulok JavaScriptben, mi a live binding és mikor használjak dinamikus importot? -->
<!-- tags: esm, modules, import, export, dynamic import, top-level await, import.meta, live binding -->

Az ES modul saját scope-pal és mindig strict módban fut, és alkalmazásonként egyszer értékelődik ki (a további importok ugyanazt a példányt kapják). A statikus `import`/`export` már betöltés előtt elemezhető, ezért a bundlerek tree-shakingelni tudnak; az importált név élő kötés (live binding) — az exportáló későbbi módosítását látja, de az importáló nem írhatja. A dinamikus `import()` Promise-t ad, és futásidőben, feltételesen tölt be (kód-felosztás, lazy loading). A top-level await a modult és az összes importálóját is megvárakoztatja, ezért lassú inicializálásra óvatosan.

```js
// mat.mjs – exportáló modul
export let hivasok = 0;          // élő kötés: az importálók mindig az aktuális értéket látják

export function osszead(a, b) {
  hivasok++;
  return a + b;
}

export const KETPI = Math.PI * 2;

export default class Statisztika {
  #ertekek = [];
  hozzaad(...x) { this.#ertekek.push(...x); return this; }
  get atlag() { return this.#ertekek.reduce((s, x) => s + x, 0) / (this.#ertekek.length || 1); }
}

// Top-level await: amíg ez nem teljesül, egyetlen importáló sem fut
export const konfig = await Promise.resolve({ precizitas: 2 });
```

```js
// app.mjs – statikus importok: hoistolódnak, a modul törzse előtt betöltődnek
import Statisztika, { osszead, hivasok, KETPI as TAU } from './mat.mjs';
import * as mat from './mat.mjs';                       // névtér-objektum (csak olvasható)

console.log(hivasok);                                   // 0
osszead(1, 2);
console.log(hivasok, mat.hivasok);                      // 1 1 – élő kötés, nem másolat
// hivasok = 5;                                         // TypeError: az import csak olvasható
console.log(new Statisztika().hozzaad(1, 2, 3).atlag, TAU.toFixed(3), mat.konfig);

// Dinamikus import: futásidőben, csak ha kell (a bundler külön chunkba teszi)
const exportalok = {
  json: async () => (d) => JSON.stringify(d),
  csv: async () => (await import('./csv-export.mjs')).default,
};
async function exportal(formatum, adat) {
  const betolto = exportalok[formatum];
  if (!betolto) throw new Error(`ismeretlen formátum: ${formatum}`);
  return (await betolto())(adat);
}
console.log(await exportal('json', { a: 1 }));

// import.meta.url: a MODUL helye (nem a munkakönyvtár) – relatív erőforrásokhoz
console.log(new URL('./adatok.json', import.meta.url).href);

// Körkörös import: a még ki nem értékelt kötés TDZ-ben van (ReferenceError);
// megoldás: a közös rész kiemelése harmadik modulba, vagy lusta elérés függvényen belül.
```

## Funkcionális minták és immutábilis adatkezelés
<!-- q: Hogyan dolgozzak fel adatokat funkcionálisan JavaScriptben (map, reduce, compose, memoize, debounce)? -->
<!-- tags: functional programming, map, filter, reduce, immutability, compose, curry, memoize, debounce, throttle -->

A tömbmetódusok (`map`, `filter`, `reduce`, `flatMap`) új tömböt adnak, és az ES2023-as `toSorted`, `toReversed`, `with` is az eredeti módosítása nélkül dolgozik — a régi `sort`/`reverse` helyben módosít, ami React-állapotnál gyakori hiba. Az `Object.groupBy` (ES2024) csoportosít, a kis, tiszta függvényekből `pipe`/`compose` épít feldolgozási láncot. A memoizálás drága, tiszta függvények eredményét cache-eli; a debounce csak a "csend" után fut (keresőmező), a throttle legfeljebb adott időközönként (scroll, resize). Buktató: a `reduce` kezdőérték nélkül üres tömbön TypeError-t dob.

```js
const rendelesek = [
  { id: 1, vevo: 'v1', osszeg: 12000, statusz: 'fizetve' },
  { id: 2, vevo: 'v2', osszeg: 4500, statusz: 'uj' },
  { id: 3, vevo: 'v1', osszeg: 30000, statusz: 'fizetve' },
  { id: 4, vevo: 'v3', osszeg: 800, statusz: 'torolve' },
];
const fizetett = rendelesek.filter((r) => r.statusz === 'fizetve').reduce((s, r) => s + r.osszeg, 0);
const rendezett = rendelesek.toSorted((a, b) => b.osszeg - a.osszeg); // az eredeti változatlan
const vevonkent = Object.groupBy(rendelesek, (r) => r.vevo);         // ES2024
const frissitett = rendelesek.with(1, { ...rendelesek[1], statusz: 'fizetve' });
console.log(fizetett, rendezett[0].id, Object.keys(vevonkent), frissitett[1].statusz, rendelesek[1].statusz);

const pipe = (...fns) => (x) => fns.reduce((acc, fn) => fn(acc), x);
const curry = (fn) => function curried(...args) {
  return args.length >= fn.length ? fn.apply(this, args) : (...tobb) => curried.apply(this, [...args, ...tobb]);
};
const szoroz = curry((a, b) => a * b);
const huf = new Intl.NumberFormat('hu-HU', { style: 'currency', currency: 'HUF', maximumFractionDigits: 0 });
console.log(pipe(szoroz(1.27), Math.round, (x) => huf.format(x))(10000)); // bruttó ár formázva

function memoize(fn, kulcs = (...a) => JSON.stringify(a)) {
  const cache = new Map();
  return (...args) => {
    const k = kulcs(...args);
    if (!cache.has(k)) cache.set(k, fn(...args));
    return cache.get(k);
  };
}
const fib = memoize((n) => (n < 2 ? n : fib(n - 1) + fib(n - 2)));
console.log(fib(90));

function debounce(fn, ms) {
  let id;
  return (...args) => { clearTimeout(id); id = setTimeout(() => fn(...args), ms); };
}
function throttle(fn, ms) {
  let utolso = -Infinity;
  return (...args) => {
    const most = Date.now();
    if (most - utolso >= ms) { utolso = most; fn(...args); }
  };
}
const kereses = debounce((q) => console.log('keresés:', q), 50);
['k', 'ká', 'káv', 'kávé'].forEach((q) => kereses(q)); // csak a 'kávé' fut le
const naplo = throttle((i) => console.log('throttle:', i), 1000);
for (let i = 0; i < 5; i++) naplo(i);                  // csak a 0 fut le
```

## Teljesítmény: hidden class, inline cache és typed array
<!-- q: Hogyan írjak gyors JavaScript kódot, mit optimalizál a V8 motor? -->
<!-- tags: performance, v8, hidden classes, inline cache, monomorphic, typed arrays, jit, benchmark -->

A V8 minden objektumhoz rejtett "alakot" (hidden class/shape) rendel a mezők neve és sorrendje alapján; ha egy függvény mindig azonos alakú objektumokat kap (monomorf), az inline cache-nek köszönhetően a property-elérés szinte C-sebességű. Eltérő mezősorrend, utólagos mezőhozzáadás vagy `delete` sok alakot hoz létre, és a hívás polimorf/megamorf lesz, ami többszörösen lassabb. Numerikus munkára a typed array (`Float64Array`, `Int32Array`) összefüggő, fix típusú memóriát ad. Mérni mindig bemelegítés (JIT) után, többször ismételve kell, és az eredményt fel kell használni, különben a fordító kioptimalizálhatja a munkát.

```js
class Pont { constructor(x, y) { this.x = x; this.y = y; } } // mindig ugyanaz az alak

function osszeg(pontok) {
  let s = 0;
  for (const p of pontok) s += p.x + p.y;
  return s;
}

const N = 1_000_000;
const egyforma = Array.from({ length: N }, (_, i) => new Pont(i, i));
// Rossz minta: eltérő sorrend, utólagos bővítés -> sok shape -> megamorf elérés
const vegyes = Array.from({ length: N }, (_, i) => {
  const o = i % 4 === 0 ? { y: i, x: i } : i % 4 === 1 ? { x: i, y: i, z: 0 } : { x: i };
  if (i % 4 >= 2) o.y = i;
  if (i % 4 === 3) o.extra = true;
  return o;
});

let nyelo = 0; // az eredményt felhasználjuk, hogy a JIT ne dobja el a munkát
function mer(cimke, fn, ismetles = 5) {
  nyelo += fn(); // bemelegítés: optimalizáló fordítás (TurboFan)
  const t0 = performance.now();
  for (let i = 0; i < ismetles; i++) nyelo += fn();
  console.log(`${cimke.padEnd(24)} ${((performance.now() - t0) / ismetles).toFixed(2)} ms`);
}
mer('monomorf objektumok', () => osszeg(egyforma));
mer('megamorf objektumok', () => osszeg(vegyes));

const xs = new Float64Array(N);       // 8 MB összefüggő memória, nincs dobozolás
for (let i = 0; i < N; i++) xs[i] = i;
const sima = Array.from(xs);
mer('Float64Array for-ciklus', () => { let s = 0; for (let i = 0; i < xs.length; i++) s += xs[i]; return s; });
mer('Array reduce', () => sima.reduce((s, x) => s + x, 0));
console.log('ellenőrző összeg:', nyelo > 0);

// További szabályok:
// - forró objektumon ne használj delete-et (dictionary módba válthat) – állítsd undefined-re
// - kerüld a "lyukas" tömböket (arr[1000] = x üres tömbön) és a vegyes elemtípusokat
// - nagy szöveg építésénél tömb + join; DOM-ban kötegelt írás (layout thrashing elkerülése)
// - profilozás: Node --cpu-prof, böngészőben DevTools Performance fül
```

## Biztonság: XSS, prototype pollution, ReDoS
<!-- q: Milyen biztonsági hibákat kell elkerülni JavaScript kódban (XSS, prototype pollution, ReDoS)? -->
<!-- tags: security, xss, prototype pollution, redos, eval, csp, sanitization, randomuuid -->

XSS akkor keletkezik, ha felhasználói szöveg HTML-ként értelmeződik (`innerHTML`, `document.write`, `javascript:` URL): szöveghez `textContent`-et használj, HTML-hez sanitizert (DOMPurify) és Content-Security-Policy fejlécet. Prototype pollution: egy naiv rekurzív merge a `__proto__` kulcson keresztül az `Object.prototype`-ot módosítja, így minden objektum "megkapja" a támadó mezőit — tiltsd ezeket a kulcsokat, vagy használj `Map`-et / `Object.create(null)`-t. ReDoS: egymásba ágyazott kvantorok (`(a+)+`) exponenciális backtrackinget okozhatnak, ami blokkolja az egyszálú event loopot. Az `eval`/`new Function` felhasználói adattal tilos, és kliensoldali kódban soha nincs titok.

```js
function escapeHtml(s) {
  const csere = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  return String(s).replace(/[&<>"']/g, (c) => csere[c]);
}
const komment = '<img src=x onerror="alert(document.cookie)">';
console.log(`<p>${escapeHtml(komment)}</p>`); // böngészőben: elem.textContent = komment

function biztonsagosUrl(nyers) {              // javascript: és data: URL-ek kiszűrése href-hez
  try {
    const u = new URL(nyers, 'https://example.com');
    return ['http:', 'https:', 'mailto:'].includes(u.protocol) ? u.href : '#';
  } catch {
    return '#';
  }
}
console.log(biztonsagosUrl('javascript:alert(1)'), biztonsagosUrl('/profil'));

function naivMerge(cel, forras) {             // SEBEZHETŐ – csak szemléltetés
  for (const k in forras) {
    if (typeof forras[k] === 'object' && forras[k] !== null) {
      cel[k] ??= {};
      naivMerge(cel[k], forras[k]);           // k === '__proto__' -> Object.prototype-ba ír!
    } else cel[k] = forras[k];
  }
  return cel;
}
function biztonsagosMerge(cel, forras) {
  for (const k of Object.keys(forras)) {
    if (k === '__proto__' || k === 'constructor' || k === 'prototype') continue;
    const v = forras[k];
    cel[k] = v && typeof v === 'object' && !Array.isArray(v)
      ? biztonsagosMerge(Object.hasOwn(cel, k) ? cel[k] : Object.create(null), v)
      : v;
  }
  return cel;
}
const tamadas = JSON.parse('{"__proto__": {"admin": true}}'); // a JSON.parse saját kulcsot hoz létre
biztonsagosMerge({}, tamadas);
console.log('biztonságos merge után ({}).admin =', ({}).admin); // undefined
naivMerge({}, tamadas);
console.log('naiv merge után ({}).admin =', ({}).admin);        // true – MINDEN objektum érintett
delete Object.prototype.admin;                                 // a demó takarítása

const veszelyes = /^(a+)+$/; // 'aaa…ab' bemenetre exponenciális idő – ne futtasd ilyen bemenettel
const biztonsagos = /^a+$/;  // ugyanazt illeszti, lineáris időben
console.log(veszelyes.source, biztonsagos.test('a'.repeat(30) + 'b'));

console.log(crypto.randomUUID()); // tokenhez kriptográfiai RNG, nem Math.random
```

## Tesztelés node:test-tel és mockokkal
<!-- q: Hogyan írjak unit teszteket JavaScriptben a beépített node:test futtatóval és mockokkal? -->
<!-- tags: testing, node:test, assert, mock, unit test, dependency injection, vitest, jest -->

A Node beépített tesztfuttatója (`node --test`) külső függőség nélkül ad `describe`/`it` szerkezetet, hookokat, mockokat és coverage-et; böngészős/Vite projektekben a Vitest, régebbiekben a Jest a szokásos, de az API-juk nagyon hasonló. A tesztelhetőség kulcsa, hogy a külső függőségeket (árlista API, e-mail küldő, óra) a konstruktor kapja meg, így a tesztben hamisítványra cserélhetők, és az idő is determinisztikus lesz. Az `assert/strict` mély összehasonlítást ad, az `assert.rejects` aszinkron hibát ellenőriz. Minden teszt legyen független: a `beforeEach` mindig friss állapotot épít.

```js
// kosar.test.mjs – futtatás: node --test
import { describe, it, beforeEach, mock } from 'node:test';
import assert from 'node:assert/strict';

// ---- tesztelt kód (valós projektben külön modulban) ----
export class KosarSzolgaltatas {
  constructor({ arLista, ertesito, ora = () => new Date() }) {
    Object.assign(this, { arLista, ertesito, ora }); // függőségek kívülről -> mockolható
    this.tetelek = new Map();
  }
  hozzaad(cikk, db = 1) {
    if (!Number.isInteger(db) || db <= 0) throw new RangeError('db pozitív egész kell');
    this.tetelek.set(cikk, (this.tetelek.get(cikk) ?? 0) + db);
  }
  async vegosszeg() {
    let osszeg = 0;
    for (const [cikk, db] of this.tetelek) osszeg += (await this.arLista.ar(cikk)) * db;
    return Math.round(osszeg * (this.ora().getDay() === 0 ? 0.9 : 1)); // vasárnap -10%
  }
  async rendel(email) {
    const osszeg = await this.vegosszeg();
    await this.ertesito.kuld(email, `Rendelés: ${osszeg} Ft`);
    this.tetelek.clear();
    return osszeg;
  }
}

// ---- tesztek ----
describe('KosarSzolgaltatas', () => {
  let arLista, ertesito, kosar;
  const ujKosar = (datum) => new KosarSzolgaltatas({ arLista, ertesito, ora: () => new Date(datum) });

  beforeEach(() => {
    arLista = { ar: mock.fn(async (cikk) => ({ kave: 1000, tea: 500 })[cikk]) };
    ertesito = { kuld: mock.fn(async () => {}) };
    kosar = ujKosar('2024-01-01T12:00:00Z'); // hétfő – determinisztikus idő
  });

  it('összeadja a tételeket', async () => {
    kosar.hozzaad('kave', 2);
    kosar.hozzaad('tea');
    assert.equal(await kosar.vegosszeg(), 2500);
    assert.equal(arLista.ar.mock.callCount(), 2);
  });

  it('vasárnap 10% kedvezményt ad', async () => {
    kosar = ujKosar('2024-01-07T12:00:00Z');
    kosar.hozzaad('kave', 3);
    assert.equal(await kosar.vegosszeg(), 2700);
  });

  it('érvénytelen darabszámot elutasít', () => {
    assert.throws(() => kosar.hozzaad('kave', 0), { name: 'RangeError', message: /pozitív/ });
  });

  it('rendeléskor értesít és üríti a kosarat', async () => {
    kosar.hozzaad('tea', 4);
    assert.equal(await kosar.rendel('vevo@example.com'), 2000);
    assert.deepEqual(ertesito.kuld.mock.calls[0].arguments, ['vevo@example.com', 'Rendelés: 2000 Ft']);
    assert.equal(kosar.tetelek.size, 0);
  });

  it('az értesítő hibája továbbterjed', async () => {
    ertesito.kuld.mock.mockImplementation(async () => { throw new Error('SMTP hiba'); });
    kosar.hozzaad('kave');
    await assert.rejects(kosar.rendel('vevo@example.com'), /SMTP/);
  });
});
```
