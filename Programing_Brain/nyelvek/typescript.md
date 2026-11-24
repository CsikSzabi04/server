# TypeScript
<!-- tech: typescript -->
<!-- aliases: ts, tsx, tsc, typed javascript -->

A TypeScript a JavaScript statikusan típusos szuperhalmaza: a `tsc` (vagy esbuild/swc/Node type-stripping) a típusokat fordításkor ellenőrzi, majd eltávolítja, így a futó kód sima JavaScript (type erasure), futásidejű többletköltség nélkül. A típusrendszer strukturális (a forma számít, nem a név), erős típus-következtetéssel, generikusokkal, unió/metszet típusokkal és típusszintű programozással (mapped, conditional, template literal típusok). Nagy kódbázisoknál, csapatmunkában és refaktorálásnál ad sokat: az IDE-támogatás, az automatikus kiegészítés és a fordítási hibák rengeteg futásidejű hibát megfognak. Korlátja, hogy a típusok futásidőben nem léteznek — külső adatot (API, JSON, űrlap) futásidejű validációval kell ellenőrizni —, és a túl bonyolult típusok lassítják a fordítást és nehezen olvashatók.

## Strukturális típusrendszer, inferencia, any, unknown és never
<!-- q: Hogyan működik a TypeScript típusrendszere, és mi a különbség az any, unknown és never között? -->
<!-- tags: structural typing, type inference, any, unknown, never, type erasure, excess property check -->

A TypeScript strukturálisan típusos: egy érték akkor felel meg egy típusnak, ha megvannak a szükséges mezői, függetlenül az osztály vagy interfész nevétől. Friss objektumliterálnál viszont extra "excess property check" fut, ami az elírt mezőneveket fogja meg. A legtöbb típust a fordító kikövetkezteti (`const` literál típust, `let` szélesített típust kap). Az `any` kikapcsolja az ellenőrzést és "fertőz", az `unknown` a biztonságos megfelelője: bármi lehet, de használat előtt szűkíteni kell; a `never` a lehetetlen érték típusa (soha vissza nem térő függvény, kimerített unió).

```ts
interface Pont2D { x: number; y: number }
class Vektor { constructor(public x: number, public y: number, public z = 0) {} }

function hossz(p: Pont2D): number {
  return Math.hypot(p.x, p.y);
}
console.log(hossz(new Vektor(3, 4)));        // OK: a forma megfelel, a név nem számít
const literal = { x: 1, y: 2, szin: 'piros' };
console.log(hossz(literal));                  // OK: változón keresztül az extra mező megengedett
// hossz({ x: 1, y: 2, szin: 'piros' });      // HIBA: excess property check friss literálnál

const szamok = [1, 2, 3];                     // number[]
const parok = szamok.map((n) => [n, String(n)] as const); // (readonly [number, string])[]
let allapot = 'betolt';                       // string (let -> szélesítés)
const rogzitett = 'betolt';                   // "betolt" (const -> literál típus)

// unknown: használat előtt szűkíteni kell
function leir(adat: unknown): string {
  if (typeof adat === 'string') return adat.toUpperCase();
  if (Array.isArray(adat)) return `tömb (${adat.length})`;
  if (adat instanceof Date) return adat.toISOString();
  if (typeof adat === 'object' && adat !== null && 'nev' in adat) return String(adat.nev);
  return 'ismeretlen';
}
// any: minden "átmegy" – a hiba csak futáskor derül ki
const veszelyes: any = { nev: 'x' };
// veszelyes.nincs.ilyen();                   // fordul, de futáskor TypeError

function hiba(uzenet: string): never {         // never: soha nem tér vissza
  throw new Error(uzenet);
}

type Azon = string | number;
function formaz(id: Azon): string {
  return typeof id === 'number' ? id.toString().padStart(6, '0') : id;
}
const ertek: number = Math.random() > 2 ? hiba('lehetetlen') : 1; // a never bármivé értékadható
console.log(leir('abc'), leir([1, 2]), leir({ nev: 'x' }), formaz(42), allapot, rogzitett, parok[0], ertek, veszelyes.nev);
// Futásidőben nincs interface/type: a `Pont2D` a lefordított JS-ben nem létezik.
```

## Unió típusok, szűkítés és diszkriminált unió
<!-- q: Hogyan használjam a union típusokat és a diszkriminált uniót TypeScriptben kimerítő ellenőrzéssel? -->
<!-- tags: union, intersection, narrowing, discriminated union, exhaustiveness, never, control flow analysis -->

Az unió (`A | B`) "vagy ez, vagy az" típus; a fordító vezérlésfolyam-elemzéssel (control flow analysis) szűkíti `typeof`, `instanceof`, `in`, egyenlőség és truthiness ellenőrzések után. A diszkriminált unió minden tagjának van egy közös literál mezője (pl. `allapot`), amely alapján `switch`-ben pontosan szűkít, és csak az adott ágban létező mezők érhetők el. A `default` ágban `never`-re szűkült értéket egy `kimerito()` függvénynek átadva fordítási hibát kapsz, ha új esetet adsz az unióhoz, de elfelejted kezelni. A metszet (`A & B`) mindkét típus mezőit egyesíti.

```ts
type Betoltes<T> =
  | { allapot: 'tetlen' }
  | { allapot: 'tolt'; kezdve: number }
  | { allapot: 'siker'; adat: T; ms: number }
  | { allapot: 'hiba'; hiba: Error; ujraprobalhato: boolean };

function kimerito(x: never): never {
  throw new Error(`kezeletlen eset: ${JSON.stringify(x)}`);
}

function megjelenit<T>(b: Betoltes<T>, formaz: (adat: T) => string): string {
  switch (b.allapot) {
    case 'tetlen':
      return 'Kattints a betöltéshez';
    case 'tolt':
      return `Töltés… (${Date.now() - b.kezdve} ms)`;   // csak itt létezik a kezdve
    case 'siker':
      return `${formaz(b.adat)} – ${b.ms} ms`;           // b.adat: T
    case 'hiba':
      return b.ujraprobalhato ? `Hiba: ${b.hiba.message} (újra?)` : 'Végzetes hiba';
    default:
      return kimerito(b); // új állapot hozzáadásakor ITT lesz fordítási hiba
  }
}

type Bemenet = string | number | Date | null | { nyers: string };
function normalizal(b: Bemenet): string {
  if (b === null) return '';                    // egyenlőség
  if (typeof b === 'string') return b.trim();   // typeof
  if (typeof b === 'number') return b.toFixed(2);
  if (b instanceof Date) return b.toISOString(); // instanceof
  return b.nyers;                                // ami maradt: { nyers: string }
}

type Idobelyeg = { letrehozva: Date; modositva?: Date };
type Felhasznalo = { id: string; nev: string } & Idobelyeg; // metszet
type Szerep = 'admin' | 'szerkeszto' | 'olvaso';            // literál unió enum helyett

const jogok: Record<Szerep, readonly string[]> = {           // minden szerepet le kell fedni
  admin: ['olvas', 'ir', 'torol'],
  szerkeszto: ['olvas', 'ir'],
  olvaso: ['olvas'],
};

const f: Felhasznalo = { id: 'u1', nev: 'teszt', letrehozva: new Date(0) };
console.log(
  megjelenit<number[]>({ allapot: 'siker', adat: [1, 2, 3], ms: 42 }, (a) => `${a.length} elem`),
  normalizal({ nyers: 'x' }),
  jogok.szerkeszto.includes('ir'),
  f.modositva?.getTime() ?? 'soha',
);
```

## Type guardok, assertion függvények, satisfies és as const
<!-- q: Hogyan írjak saját type guardot és assertion függvényt TypeScriptben, és mire való a satisfies? -->
<!-- tags: type guard, type predicate, asserts, satisfies, as const, narrowing, unknown -->

A felhasználói type guard visszatérési típusa `x is T`: ha `true`-t ad, a hívó helyen a fordító `T`-re szűkíti az értéket (az `Array.filter` is ismeri). Az assertion függvény (`asserts x is T` vagy `asserts feltetel`) dob, ha a feltétel hamis, és utána a szűkítés érvényben marad — ideális bemeneti ellenőrzésre. Az `as const` a legszűkebb literál- és readonly típust adja, a `satisfies` pedig ellenőrzi, hogy egy érték megfelel-e egy típusnak, de nem szélesíti a következtetett típust (a konkrét kulcsok és literálok megmaradnak). Buktató: a type guard törzsét a fordító nem ellenőrzi — ha hazudik, a típusbiztonság elvész.

```ts
interface Termek { tipus: 'termek'; cikkszam: string; ar: number }
interface Szolgaltatas { tipus: 'szolgaltatas'; oradij: number; orak: number }
type Tetel = Termek | Szolgaltatas;

function isTermek(t: Tetel): t is Termek {
  return t.tipus === 'termek';
}

function isTetel(x: unknown): x is Tetel {   // külső adat ellenőrzése
  if (typeof x !== 'object' || x === null) return false;
  const o = x as Record<string, unknown>;
  return (o.tipus === 'termek' && typeof o.cikkszam === 'string' && typeof o.ar === 'number')
    || (o.tipus === 'szolgaltatas' && typeof o.oradij === 'number' && typeof o.orak === 'number');
}

function assert(feltetel: unknown, uzenet: string): asserts feltetel {
  if (!feltetel) throw new Error(uzenet);
}
function assertDefined<T>(x: T, nev: string): asserts x is NonNullable<T> {
  if (x === null || x === undefined) throw new Error(`${nev} hiányzik`);
}

const nyers: unknown = JSON.parse(
  '[{"tipus":"termek","cikkszam":"A1","ar":990},{"tipus":"szolgaltatas","oradij":8000,"orak":2}]');
assert(Array.isArray(nyers) && nyers.every(isTetel), 'érvénytelen tétellista');
const tetelek: Tetel[] = nyers;                    // az assert után már Tetel[]
const termekek = tetelek.filter(isTermek);        // Termek[] – a guard a filternél is szűkít
const osszeg = tetelek.reduce((s, t) => s + (isTermek(t) ? t.ar : t.oradij * t.orak), 0);

const talalat = termekek.find((t) => t.cikkszam === 'A1'); // Termek | undefined
assertDefined(talalat, 'A1 termék');
console.log(talalat.ar);                           // innentől Termek

// as const + satisfies: ellenőrzött, de literál típusú konfiguráció
const UTVONALAK = {
  fooldal: '/',
  termek: '/termek/:id',
  kosar: '/kosar',
} as const satisfies Record<string, `/${string}`>;
type UtvonalNev = keyof typeof UTVONALAK;          // 'fooldal' | 'termek' | 'kosar'
const cel: (typeof UTVONALAK)[UtvonalNev] = UTVONALAK.termek;

// Annotációval (`: Record<...>`) a konkrét kulcsok és az értékek pontos típusa elveszne
const szinek = { elsodleges: '#0af', hiba: [255, 0, 0] } satisfies Record<string, string | number[]>;
console.log(osszeg, cel, szinek.elsodleges.toUpperCase(), szinek.hiba.map((c) => c / 255));
```

## Generikusok: megkötések, alapértelmezések és const típusparaméter
<!-- q: Hogyan írjak generikus függvényeket és osztályokat TypeScriptben megkötésekkel? -->
<!-- tags: generics, constraints, extends, keyof, default type parameters, const type parameters, inference -->

A generikus típusparaméter (`<T>`) egy "típusváltozó", amelyet a fordító általában a hívásból következtet ki, így a függvény típusbiztos marad tetszőleges bemenetre. Az `extends` megkötés szűkíti, mi lehet a T (pl. `K extends keyof T` csak T kulcsa), az alapértelmezett típusparaméter (`<T, S = Partial<T>>`) kényelmet ad. A TS 5.0 `const` típusparamétere literál típusokat következtet ki `as const` nélkül. Ökölszabály: ha egy típusparaméter csak egyszer szerepel a szignatúrában, valószínűleg nem kell generikusnak lennie.

```ts
function elso<T>(xs: readonly T[]): T | undefined {
  return xs[0];
}

// K csak T kulcsa lehet -> típusbiztos property-kiválasztás
function kiszed<T, K extends keyof T>(obj: T, ...kulcsok: K[]): Pick<T, K> {
  const ki = {} as Pick<T, K>;
  for (const k of kulcsok) ki[k] = obj[k];
  return ki;
}

interface Entitas { id: string }
class Tarolo<T extends Entitas, Szuro = Partial<T>> {    // megkötés + alapértelmezett paraméter
  #adat = new Map<string, T>();
  ment(e: T): T { this.#adat.set(e.id, e); return e; }
  keres(szuro: Szuro): T[] {
    return [...this.#adat.values()].filter((e) =>
      Object.entries(szuro as object).every(([k, v]) => (e as Record<string, unknown>)[k] === v));
  }
}

// const típusparaméter (TS 5.0): ['piros', 'zold'] literál tuple-ként következtetődik
function enumbol<const T extends readonly string[]>(ertekek: T) {
  return {
    ertekek,
    ervenyes: (x: string): x is T[number] => (ertekek as readonly string[]).includes(x),
  };
}
const Szin = enumbol(['piros', 'zold', 'kek']);

type Osszehasonlito<T> = (a: T, b: T) => number;
const szerint = <T, K extends keyof T>(kulcs: K, irany: 1 | -1 = 1): Osszehasonlito<T> =>
  (a, b) => (a[kulcs] < b[kulcs] ? -irany : a[kulcs] > b[kulcs] ? irany : 0);

interface Felhasznalo extends Entitas { nev: string; kor: number; aktiv: boolean }
const tarolo = new Tarolo<Felhasznalo>();
tarolo.ment({ id: 'u1', nev: 'Teszt A', kor: 31, aktiv: true });
tarolo.ment({ id: 'u2', nev: 'Teszt B', kor: 25, aktiv: true });

const rendezett = tarolo.keres({ aktiv: true }).sort(szerint<Felhasznalo, 'kor'>('kor'));
const legfiatalabb = elso(rendezett);
if (legfiatalabb) console.log(kiszed(legfiatalabb, 'nev', 'kor')); // { nev: string; kor: number }

const bemenet: string = 'zold';
if (Szin.ervenyes(bemenet)) {
  const sz: 'piros' | 'zold' | 'kek' = bemenet;   // szűkítve a literál unióra
  console.log('érvényes szín:', sz);
}
```

## keyof, typeof, indexed access és a beépített utility típusok
<!-- q: Hogyan származtassak típusokat meglévő típusokból és értékekből TypeScriptben (keyof, typeof, Pick, Omit, ReturnType)? -->
<!-- tags: keyof, typeof, indexed access, utility types, pick, omit, partial, record, returntype, awaited -->

A `typeof ertek` egy értékből (pl. konfigurációs objektumból) típust készít, a `keyof T` a kulcsok unióját adja, a `T[K]` (indexed access) egy mező típusát, a `T[number]` egy tömb elemtípusát. Ezekből és a beépített utility típusokból (`Partial`, `Required`, `Readonly`, `Pick`, `Omit`, `Record`, `Exclude`, `Extract`, `NonNullable`, `Parameters`, `ReturnType`, `Awaited`) a típusok egyetlen forrásból származtathatók, így nincs kézzel duplikált, elcsúszó definíció. Tipikus példa egy CRUD API: a létrehozási, módosítási és listázási típus mind a fő entitásból készül.

```ts
const alapKonfig = {
  szerver: { host: 'localhost', port: 8080 },
  naplo: { szint: 'info' as 'debug' | 'info' | 'warn' | 'error', fajl: null as string | null },
  funkciok: ['kereses', 'export'],
};

type Konfig = typeof alapKonfig;                         // értékből típus
type Szakasz = keyof Konfig;                             // 'szerver' | 'naplo' | 'funkciok'
type NaploSzint = Konfig['naplo']['szint'];              // 'debug' | 'info' | 'warn' | 'error'
type Funkcio = Konfig['funkciok'][number];               // string (tömb elemtípusa)

function szakasz<K extends Szakasz>(k: K): Konfig[K] {   // a visszatérés a kulcstól függ
  return alapKonfig[k];
}

interface Termek {
  id: string;
  nev: string;
  ar: number;
  leiras?: string;
  letrehozva: Date;
}
type UjTermek = Omit<Termek, 'id' | 'letrehozva'>;       // ezeket a szerver adja
type TermekModositas = Partial<UjTermek>;                 // PATCH: minden opcionális
type TermekListaElem = Pick<Termek, 'id' | 'nev' | 'ar'>;
type ArIndex = Record<Termek['id'], Termek['ar']>;

function frissit(t: Readonly<Termek>, m: TermekModositas): Termek {
  // t.ar = 0;                                            // HIBA: readonly
  return { ...t, ...m };
}

async function termekBetolt(id: string, opciok?: { cache: boolean }) {
  return { id, nev: opciok?.cache ? 'cache-elt' : 'friss', ar: 990, letrehozva: new Date() } satisfies Termek;
}
type BetoltParameterek = Parameters<typeof termekBetolt>;       // [id: string, opciok?: {...}]
type BetoltEredmeny = Awaited<ReturnType<typeof termekBetolt>>;  // a Promise kicsomagolva
type Statusz = 'uj' | 'fizetve' | 'torolve' | null;
type AktivStatusz = Exclude<NonNullable<Statusz>, 'torolve'>;    // 'uj' | 'fizetve'

const uj: UjTermek = { nev: 'kávé', ar: 1290 };
const lista: TermekListaElem[] = [{ id: 'p1', ...uj }];
const arak: ArIndex = { p1: 1290 };
const statusz: AktivStatusz = 'fizetve';
const szint: NaploSzint = 'warn';
const funkcio: Funkcio = 'kereses';
const param: BetoltParameterek = ['p1', { cache: true }];
void termekBetolt(...param).then((t: BetoltEredmeny) => {
  console.log(szakasz('szerver').port, lista, arak, statusz, szint, funkcio, frissit(t, { ar: 1100 }).ar);
});
```

## Mapped típusok és key remapping
<!-- q: Hogyan alakítsam át egy típus összes mezőjét mapped típusokkal TypeScriptben? -->
<!-- tags: mapped types, key remapping, as clause, modifiers, readonly, optional, capitalize -->

A mapped típus (`{ [K in keyof T]: ... }`) egy típus kulcsain iterálva új típust épít; a `Partial`, `Readonly`, `Record` is így készül. A `?` és `readonly` módosítók `+`/`-` előtaggal hozzáadhatók vagy eltávolíthatók. Az `as` záradékkal (key remapping) a kulcsok átnevezhetők (pl. `get${Capitalize<K>}`) vagy `never`-re képezve kiszűrhetők — így például csak a metódusok vagy csak az adatmezők választhatók ki. Gyakorlati haszna: generált getterek, eseménynevek, típusbiztos store-ok és űrlapállapotok.

```ts
type Opcionalis<T> = { [K in keyof T]?: T[K] };            // = Partial<T>
type Modosithato<T> = { -readonly [K in keyof T]: T[K] };   // readonly eltávolítása
type Nullazhato<T> = { [K in keyof T]: T[K] | null };

type Getterek<T> = { [K in keyof T & string as `get${Capitalize<K>}`]: () => T[K] };
type CsakAdat<T> = { [K in keyof T as T[K] extends (...a: never[]) => unknown ? never : K]: T[K] };
type Esemenyek<T> = { [K in keyof T & string as `${K}Valtozott`]: (uj: T[K], regi: T[K]) => void };

interface Beallitasok {
  readonly tema: 'sotet' | 'vilagos';
  nyelv: string;
  betumeret: number;
  ment(): Promise<void>;
}
type Adatok = Modosithato<CsakAdat<Beallitasok>>;           // { tema; nyelv; betumeret } – metódus nélkül
type BeallitasGetterek = Getterek<Adatok>;                  // { getTema(); getNyelv(); getBetumeret() }

// Típusbiztos store: a figyelők nevei és paraméterei a mezőkből generálódnak
function store<T extends object>(kezdo: T, figyelok: Partial<Esemenyek<T>>) {
  const allapot = { ...kezdo };
  return {
    get: <K extends keyof T>(k: K): T[K] => allapot[k],
    set<K extends keyof T & string>(k: K, ertek: T[K]): void {
      const regi = allapot[k];
      allapot[k] = ertek;
      // generikus kulcs-átnevezést a fordító nem tud követni, ezért itt egy tudatos cast kell
      const figyelo = (figyelok as unknown as Record<string, ((u: T[K], r: T[K]) => void) | undefined>)[`${k}Valtozott`];
      figyelo?.(ertek, regi);
    },
  };
}

const s = store<Adatok>(
  { tema: 'sotet', nyelv: 'hu', betumeret: 14 },
  { temaValtozott: (uj, regi) => console.log(`téma: ${regi} -> ${uj}`) }, // uj, regi típusa kikövetkeztetve
);
s.set('tema', 'vilagos');
// s.set('tema', 'kek');           // HIBA: '"kek"' nem 'sotet' | 'vilagos'
// s.set('ment', async () => {});  // HIBA: a metódust a CsakAdat kiszűrte

const getterek: BeallitasGetterek = {
  getTema: () => s.get('tema'),
  getNyelv: () => s.get('nyelv'),
  getBetumeret: () => s.get('betumeret'),
};
const urlap: Nullazhato<Pick<Adatok, 'nyelv'>> = { nyelv: null };
const reszleges: Opcionalis<Adatok> = { betumeret: 16 };
console.log(getterek.getTema(), urlap, reszleges);
```

## Feltételes típusok és infer
<!-- q: Hogyan működnek a conditional type-ok és az infer kulcsszó TypeScriptben? -->
<!-- tags: conditional types, infer, distributive, extract, type-level programming -->

A feltételes típus (`T extends U ? X : Y`) típusszintű elágazás; ha a `T` "csupasz" típusparaméter és uniót kap, a feltétel elemenként (disztributívan) értékelődik ki — ezt `[T] extends [U]` formával lehet kikapcsolni. Az `infer` egy mintából "kiolvas" egy típust (pl. Promise értéktípusát, függvény paraméterét, tömb elemtípusát), és rekurzív kicsomagolásra is használható. A gyakorlatban ezzel készülnek a `ReturnType`, `Awaited`, `Extract` típusok, és ezzel lehet egy API-válasz-unióból automatikusan típusos kezelőtérképet levezetni.

```ts
type IsString<T> = T extends string ? true : false;
type TombbeCsomagol<T> = T extends unknown ? T[] : never;          // disztributív
type B1 = TombbeCsomagol<string | number>;                         // string[] | number[]
type NemDisztributiv<T> = [T] extends [unknown] ? T[] : never;
type B2 = NemDisztributiv<string | number>;                        // (string | number)[]

type ElemTipus<T> = T extends readonly (infer E)[] ? E : T;
type Kicsomagol<T> = T extends PromiseLike<infer V> ? Kicsomagol<V> : T; // rekurzív "Awaited"
type ElsoParam<F> = F extends (elso: infer P, ...tobbi: never[]) => unknown ? P : never;
type Peldany<C> = C extends abstract new (...a: never[]) => infer I ? I : never;
type ElsoSzam<T> = T extends [infer N extends number, ...unknown[]] ? N : never; // infer megkötéssel

type ApiValasz =
  | { tipus: 'felhasznalo'; adat: { id: string; nev: string } }
  | { tipus: 'rendeles'; adat: { id: string; osszeg: number } }
  | { tipus: 'hiba'; adat: { kod: number; uzenet: string } };

type AdatTipus<T extends ApiValasz['tipus']> = Extract<ApiValasz, { tipus: T }>['adat'];
type Kezelok = { [T in ApiValasz['tipus']]: (adat: AdatTipus<T>) => string };

const kezelok: Kezelok = {
  felhasznalo: (a) => `felhasználó: ${a.nev}`,          // a: { id; nev } – automatikusan
  rendeles: (a) => `rendelés ${a.id}: ${a.osszeg} Ft`,
  hiba: (a) => `hiba ${a.kod}: ${a.uzenet}`,
};

function feldolgoz(v: ApiValasz): string {
  // "korrelált unió": a fordító nem látja, hogy v.tipus és v.adat összetartozik -> egy cast
  const kezelo = kezelok[v.tipus] as (adat: ApiValasz['adat']) => string;
  return kezelo(v.adat);
}

async function lekeres() { return [1, 2, 3] as const; }
type Lekert = Kicsomagol<ReturnType<typeof lekeres>>;   // readonly [1, 2, 3]
const elem: ElemTipus<Lekert> = 2;                      // 1 | 2 | 3
const ellenorzes: [IsString<'x'>, B1, B2, ElsoSzam<[42, 'x']>] = [true, ['a'], ['a', 1], 42];
class Kapcsolat { constructor(public url: string) {} }
const k: Peldany<typeof Kapcsolat> = new Kapcsolat('db://helyi');
const p: ElsoParam<typeof feldolgoz> = { tipus: 'hiba', adat: { kod: 500, uzenet: 'belső hiba' } };
console.log(elem, ellenorzes, k.url, feldolgoz(p), feldolgoz({ tipus: 'rendeles', adat: { id: 'r1', osszeg: 5000 } }));
```

## Template literal típusok: típusos útvonalak és stringminták
<!-- q: Mire jók a template literal típusok TypeScriptben, például route paraméterek kinyerésére? -->
<!-- tags: template literal types, string manipulation, capitalize, uppercase, route params, infer -->

A template literal típus (`` `margin-${Irany}` ``) string-mintákat ír le típusszinten; uniókkal kombinálva minden kombinációt legenerál. `infer`-rel együtt egy string típus "parse-olható": például egy `'/bolt/:boltId/termek/:termekId'` útvonalból kinyerhető a `{ boltId: string; termekId: string }` paramétertípus, így egy hiányzó vagy elírt paraméter fordítási hiba lesz. A beépített `Uppercase`, `Lowercase`, `Capitalize`, `Uncapitalize` típusok a betűállást alakítják. Buktató: a túl mély rekurzió vagy hatalmas uniók lassítják a fordítót (a TS korlátozza a rekurzió mélységét).

```ts
type Irany = 'top' | 'right' | 'bottom' | 'left';
type Margo = `margin-${Irany}`;                          // 4 elemű unió
type Esemeny<T extends string> = `on${Capitalize<T>}`;   // 'click' -> 'onClick'
type Meret = `${number}${'px' | 'rem' | '%'}`;

// Útvonal-paraméterek kinyerése rekurzív infer-rel
type Parameterek<Ut extends string> =
  Ut extends `${string}:${infer P}/${infer Tobbi}`
    ? { [K in P | keyof Parameterek<`/${Tobbi}`>]: string }
    : Ut extends `${string}:${infer P}`
      ? { [K in P]: string }
      : Record<never, never>;

type T1 = Parameterek<'/bolt/:boltId/termek/:termekId'>; // { boltId: string; termekId: string }

function utvonal<const U extends string>(minta: U) {
  return {
    epit(params: Parameterek<U>): string {
      const p = params as Record<string, string>;
      return minta.replace(/:(\w+)/g, (_, nev: string) => encodeURIComponent(p[nev] ?? ''));
    },
    illeszt(ut: string): Parameterek<U> | null {
      const nevek: string[] = [];
      const forras = minta.replace(/:(\w+)/g, (_, n: string) => { nevek.push(n); return '([^/]+)'; });
      const m = new RegExp(`^${forras}$`).exec(ut);
      if (!m) return null;
      return Object.fromEntries(nevek.map((n, i) => [n, decodeURIComponent(m[i + 1] ?? '')])) as Parameterek<U>;
    },
  };
}

const termekUt = utvonal('/bolt/:boltId/termek/:termekId');
console.log(termekUt.epit({ boltId: 'b1', termekId: 'kávé 250g' }));
// termekUt.epit({ boltId: 'b1' });                     // HIBA: hiányzik a termekId
const illesztes = termekUt.illeszt('/bolt/b7/termek/p42');
if (illesztes) console.log(illesztes.termekId);         // típusosan elérhető

type KornyezetiValtozo<T extends string> = `APP_${Uppercase<T>}`;
const env: Record<KornyezetiValtozo<'port' | 'db_url'>, string> = {
  APP_PORT: '8080',
  APP_DB_URL: 'postgres://localhost/app',
};
const margok: Partial<Record<Margo, Meret>> = { 'margin-top': '8px', 'margin-left': '1.5rem' };
// const rossz: Meret = '12pt';                         // HIBA
const kezelo: Esemeny<'click'> = 'onClick';
const t1: T1 = { boltId: '1', termekId: '2' };
console.log(env.APP_PORT, margok, kezelo, t1);
```

## Rekurzív típusok és variadic tuple-ök
<!-- q: Hogyan írjak rekurzív típusokat (DeepPartial, pontozott útvonalak) és variadic tuple típusokat TypeScriptben? -->
<!-- tags: recursive types, deep partial, deep readonly, paths, variadic tuples, json type -->

A típusok hivatkozhatnak önmagukra, így leírható a tetszőleges mélységű JSON, és készíthető `DeepPartial`/`DeepReadonly`, amely a beágyazott objektumokra is érvényes (a beépített `Partial` csak sekély). Pontozott útvonal-típussal (`'adatbazis.kapcsolat.port'`) egy konfiguráció-lekérdező függvény a pontos értéktípust adja vissza, és elírt útvonalra fordítási hibát jelez. A variadic tuple típusok (`[...A, ...B]`) argumentumlistákat fűznek össze, ami például típusos részleges alkalmazást (partial application) tesz lehetővé.

```ts
type JsonErtek = string | number | boolean | null | JsonErtek[] | { [kulcs: string]: JsonErtek };

type DeepPartial<T> = T extends (...a: never[]) => unknown ? T
  : T extends readonly (infer E)[] ? readonly DeepPartial<E>[]
  : T extends object ? { [K in keyof T]?: DeepPartial<T[K]> }
  : T;
type DeepReadonly<T> = T extends object ? { readonly [K in keyof T]: DeepReadonly<T[K]> } : T;

// Pontozott útvonalak és a hozzájuk tartozó értéktípus
type Utak<T> = T extends object
  ? { [K in keyof T & string]: T[K] extends object ? K | `${K}.${Utak<T[K]>}` : K }[keyof T & string]
  : never;
type ErtekAz<T, U extends string> = U extends `${infer F}.${infer R}`
  ? F extends keyof T ? ErtekAz<T[F], R> : never
  : U extends keyof T ? T[U] : never;

interface Konfig {
  adatbazis: { kapcsolat: { host: string; port: number }; pool: number };
  naplo: { szint: 'info' | 'debug' };
}

function lekerdez<U extends Utak<Konfig>>(k: Konfig, ut: U): ErtekAz<Konfig, U> {
  return ut.split('.').reduce<unknown>((o, kulcs) => (o as Record<string, unknown>)[kulcs], k) as ErtekAz<Konfig, U>;
}

function osszefesul<T>(alap: T, felulir: DeepPartial<T>): T {
  const ki: Record<string, unknown> = { ...(alap as Record<string, unknown>) };
  for (const [k, v] of Object.entries(felulir as Record<string, unknown>)) {
    const a = ki[k];
    ki[k] = v && typeof v === 'object' && !Array.isArray(v) && a && typeof a === 'object'
      ? osszefesul(a, v as DeepPartial<typeof a>) : v;
  }
  return ki as T;
}

type Osszefuz<A extends unknown[], B extends unknown[]> = [...A, ...B];
function reszleges<E extends unknown[], M extends unknown[], R>(fn: (...a: [...E, ...M]) => R, ...elso: E) {
  return (...maradek: M): R => fn(...elso, ...maradek);
}

const alap: Konfig = { adatbazis: { kapcsolat: { host: 'localhost', port: 5432 }, pool: 10 }, naplo: { szint: 'info' } };
const vegleges: DeepReadonly<Konfig> = osszefesul(alap, { adatbazis: { kapcsolat: { port: 6543 } } });
const port = lekerdez(alap, 'adatbazis.kapcsolat.port');   // number
const szint = lekerdez(alap, 'naplo.szint');               // 'info' | 'debug'
// lekerdez(alap, 'adatbazis.nincs');                      // HIBA: nem létező útvonal
// vegleges.adatbazis.pool = 1;                            // HIBA: mélyen readonly

const naploz = (szint: string, modul: string, uzenet: string) => `[${szint}] ${modul}: ${uzenet}`;
const dbNaplo = reszleges(naploz, 'info', 'db');           // (uzenet: string) => string
const args: Osszefuz<[string], [number, boolean]> = ['x', 1, true];
const json: JsonErtek = { lista: [1, 'kettő', { melyebb: null }] };
console.log(vegleges.adatbazis.kapcsolat.port, port, szint, dbNaplo('kapcsolódva'), args, json);
```

## Branded (nominális) típusok
<!-- q: Hogyan akadályozzam meg, hogy két azonos alaptípusú azonosítót (pl. két string ID-t) összekeverjek TypeScriptben? -->
<!-- tags: branded types, nominal typing, opaque types, smart constructor, validation, unique symbol -->

A strukturális típusrendszerben egy `FelhasznaloId` és egy `RendelesId` is csak `string`, ezért a fordító nem szól, ha felcseréled őket. A branded típus egy fantom mezőt ad az alaptípushoz (`string & { readonly [marka]: 'FelhasznaloId' }`), amely futásidőben nem létezik, de típusszinten megkülönbözteti az értékeket. A brandet csak egy validáló "smart constructor" függvény adhatja ki, így a függvényszignatúra garantálja, hogy például az e-mail cím már ellenőrzött. Buktató: aritmetika után (`a + b`) az eredmény újra sima `number`, ezért vissza kell brandelni.

```ts
declare const marka: unique symbol;
type Brand<T, B extends string> = T & { readonly [marka]: B };

type FelhasznaloId = Brand<string, 'FelhasznaloId'>;
type RendelesId = Brand<string, 'RendelesId'>;
type Email = Brand<string, 'Email'>;
type PozitivEgesz = Brand<number, 'PozitivEgesz'>;
type Filler = Brand<number, 'Filler'>;           // pénz egész fillérben

// Smart constructorok: a brand CSAK validáció után szerezhető meg
function email(nyers: string): Email {
  const e = nyers.trim().toLowerCase();
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(e)) throw new TypeError(`érvénytelen e-mail: ${nyers}`);
  return e as Email;
}
function pozitivEgesz(n: number): PozitivEgesz {
  if (!Number.isInteger(n) || n <= 0) throw new RangeError(`pozitív egész kell: ${n}`);
  return n as PozitivEgesz;
}
const filler = (forint: number): Filler => Math.round(forint * 100) as Filler;
const ujId = <B extends string>(prefix: string) => `${prefix}_${crypto.randomUUID()}` as Brand<string, B>;

function rendelestLeker(felhasznalo: FelhasznaloId, rendeles: RendelesId): string {
  return `GET /felhasznalok/${felhasznalo}/rendelesek/${rendeles}`;
}
function osszead(a: Filler, b: Filler): Filler {
  return (a + b) as Filler;                      // a + b sima number -> újra brandeljük
}
function ertesit(cim: Email, darab: PozitivEgesz): string {
  return `${cim}: ${darab} új értesítés`;
}

const fId = ujId<'FelhasznaloId'>('usr');
const rId = ujId<'RendelesId'>('ord');
console.log(rendelestLeker(fId, rId));
// rendelestLeker(rId, fId);                     // HIBA: a RendelesId nem FelhasznaloId
// rendelestLeker('usr_123', rId);               // HIBA: sima string nem elég

const vegosszeg = osszead(filler(1290.5), filler(450));
console.log(vegosszeg, (vegosszeg / 100).toFixed(2)); // olvasáskor sima numberként is működik
console.log(ertesit(email(' Valaki@Example.COM '), pozitivEgesz(3)));
// ertesit('valaki@example.com', 3);             // HIBA: validálatlan bemenet
```

## Függvény-overloadok, this paraméter és variancia
<!-- q: Hogyan írjak overloadolt függvényt TypeScriptben, és mit jelent a variancia (in/out)? -->
<!-- tags: overloads, function types, this parameter, variance, covariance, contravariance, strictfunctiontypes -->

Az overload több hívási szignatúrát ad egyetlen implementációhoz, így a hívó a bemenettől függő pontos visszatérési típust kapja; sokszor egyszerűbb alternatíva a generikus + lookup típus (`Tipusok[K]`). A `this` paraméter (az első, fordításkor törlődő paraméter) rögzíti, milyen kontextusban hívható a függvény. A variancia azt írja le, hogyan öröklődik a típusok közötti viszony: a visszatérési érték kovariáns, a függvényparaméter (strictFunctionTypes mellett) kontravariáns — egy állatkezelő használható kutyakezelőként, fordítva nem. Az `in`/`out` jelölés ezt generikus interfészen explicitté teszi; buktató, hogy a metódus-szintaxisú tagok történeti okból bivariánsak maradnak.

```ts
function parse(ertek: string, tipus: 'szam'): number;
function parse(ertek: string, tipus: 'datum'): Date;
function parse(ertek: string, tipus: 'logikai'): boolean;
function parse(ertek: string, tipus: 'szam' | 'datum' | 'logikai'): number | Date | boolean {
  switch (tipus) {
    case 'szam': {
      const n = Number(ertek);
      if (Number.isNaN(n)) throw new TypeError(`nem szám: ${ertek}`);
      return n;
    }
    case 'datum':
      return new Date(ertek);
    case 'logikai':
      return ['1', 'true', 'igen'].includes(ertek.toLowerCase());
  }
}
const n = parse('42', 'szam');           // number
const d = parse('2024-03-01', 'datum');  // Date

// Overload helyett gyakran elég: generikus + lookup típus
type Tipusok = { szam: number; datum: Date; logikai: boolean };
type ParseFv = <K extends keyof Tipusok>(ertek: string, tipus: K) => Tipusok[K];
const parse2: ParseFv = (ertek, tipus) => parse(ertek, tipus as never);

interface Gomb { felirat: string; letiltva: boolean }
function kattintas(this: Gomb, e: { x: number }): void {  // a this típusa rögzítve
  if (!this.letiltva) console.log(`${this.felirat} @${e.x}`);
}
const gomb = { felirat: 'Mentés', letiltva: false, onClick: kattintas };
gomb.onClick({ x: 10 });
// kattintas({ x: 1 });                  // HIBA: a 'this' kontextus void

class Allat { nev = 'állat'; }
class Kutya extends Allat { ugat() { return 'vau'; } }
type Kezelo<T> = (x: T) => void;
const allatKezelo: Kezelo<Allat> = (a) => console.log(a.nev);
const kutyaKezelo: Kezelo<Kutya> = allatKezelo;            // OK: kontravariáns paraméter
// const rossz: Kezelo<Allat> = (k: Kutya) => k.ugat();    // HIBA: nem minden állat ugat

interface Forras<out T> { olvas(): T }                     // kovariáns
interface Nyelo<in T> { ir(x: T): void }                   // kontravariáns
const allatForras: Forras<Allat> = { olvas: () => new Kutya() } satisfies Forras<Kutya>;
const kutyaNyelo: Nyelo<Kutya> = { ir: (a: Allat) => console.log('írva:', a.nev) };

kutyaKezelo(new Kutya());
kutyaNyelo.ir(new Kutya());
console.log(n + 1, d.getFullYear(), parse2('true', 'logikai'), allatForras.olvas().nev);
```

## Osztályok és TC39 dekorátorok
<!-- q: Hogyan használjam az osztályokat és a modern (TC39) dekorátorokat TypeScriptben? -->
<!-- tags: classes, decorators, abstract, parameter properties, override, access modifiers, addinitializer -->

A TS osztályok a JS osztályokat egészítik ki: parameter properties (`constructor(private readonly nev: string)`), `public`/`protected`/`private` (csak fordítási idejű!) módosítók, `abstract` osztályok és metódusok, `implements` és `override`. Valódi, futásidőben is rejtett privát mezőhöz a JS `#mezo` kell. A TS 5.0 óta a szabványos (TC39) dekorátorok `experimentalDecorators` nélkül működnek: egy metódus-dekorátor az eredeti metódust és egy kontextus objektumot kap, és helyettesítő függvényt adhat vissza; a `context.addInitializer` példányosításkor fut. Több dekorátor alulról felfelé alkalmazódik; a régi "experimental" dekorátorok (pl. NestJS, TypeORM) más API-t használnak.

```ts
interface Naplozo { naploz(uzenet: string): void }

abstract class Szolgaltatas implements Naplozo {
  readonly #indulas = Date.now();                 // JS-privát: futásidőben is rejtett
  constructor(protected readonly nev: string) {}  // parameter property: deklarál + értékad
  abstract indit(): Promise<void>;
  naploz(uzenet: string): void {
    console.log(`[${this.nev} +${Date.now() - this.#indulas}ms] ${uzenet}`);
  }
}

function naplozott<This extends Naplozo, A extends unknown[], R>(
  metodus: (this: This, ...a: A) => R,
  ctx: ClassMethodDecoratorContext<This, (this: This, ...a: A) => R>,
) {
  const nev = String(ctx.name);
  return function (this: This, ...a: A): R {        // helyettesítő metódus
    this.naploz(`→ ${nev}(${a.map((x) => JSON.stringify(x)).join(', ')})`);
    return metodus.apply(this, a);
  };
}

function ujraprobal(kiserlet: number) {             // dekorátorgyár
  return <This, A extends unknown[], R>(
    metodus: (this: This, ...a: A) => Promise<R>,
    _ctx: ClassMethodDecoratorContext<This, (this: This, ...a: A) => Promise<R>>,
  ) => async function (this: This, ...a: A): Promise<R> {
    for (let n = 1; ; n++) {
      try {
        return await metodus.apply(this, a);
      } catch (e) {
        if (n >= kiserlet) throw e;
      }
    }
  };
}

function kotott<This extends object, F extends (this: This, ...a: never[]) => unknown>(
  metodus: F, ctx: ClassMethodDecoratorContext<This, F>,
) {
  ctx.addInitializer(function (this: This) {        // példányosításkor: bind a példányhoz
    Object.defineProperty(this, ctx.name, { value: metodus.bind(this), writable: true });
  });
}

class CacheSzolgaltatas extends Szolgaltatas {
  #adat = new Map<string, string>();
  #hatralevoHibak = 1;
  constructor() { super('cache'); }
  override async indit(): Promise<void> { this.naploz('elindult'); }

  @naplozott
  beallit(kulcs: string, ertek: string): void { this.#adat.set(kulcs, ertek); }

  @ujraprobal(3)                                    // alulról felfelé: előbb a @naplozott
  @naplozott
  async lekerTavolrol(kulcs: string): Promise<string> {
    if (this.#hatralevoHibak-- > 0) throw new Error('átmeneti hiba');
    return this.#adat.get(kulcs) ?? 'nincs';
  }

  @kotott
  meret(): number { return this.#adat.size; }
}

const c = new CacheSzolgaltatas();
void c.indit().then(async () => {
  c.beallit('nyelv', 'ts');
  const { meret } = c;                               // leválasztva is működik a @kotott miatt
  console.log(await c.lekerTavolrol('nyelv'), meret());
});
```

## Típusbiztos hibakezelés: Result típus és unknown catch
<!-- q: Hogyan kezeljem a hibákat típusbiztosan TypeScriptben kivételek helyett? -->
<!-- tags: error handling, result type, either, discriminated union, unknown catch, useunknownincatchvariables -->

A TypeScript nem jelöli a szignatúrában, milyen kivételt dobhat egy függvény, és a `catch (e)` változó típusa `unknown` (strict módban), ezért az elvárt, üzleti hibákat érdemes a visszatérési típusba tenni: `Result<T, E> = { ok: true; value } | { ok: false; error }`. Diszkriminált hiba-unióval a hívót a fordító kényszeríti minden hibaeset kezelésére, és a hibák nem "szöknek el" észrevétlenül. A váratlan, programozói hibákra (bug, invariáns sérülése) továbbra is a kivétel a helyes eszköz; külső, dobó kódot egy `probal()` csomagolóval lehet Resultté alakítani.

```ts
type Result<T, E = Error> = { ok: true; value: T } | { ok: false; error: E };
const Ok = <T>(value: T): Result<T, never> => ({ ok: true, value });
const Err = <E>(error: E): Result<never, E> => ({ ok: false, error });

type ParseHiba =
  | { tipus: 'ures' }
  | { tipus: 'formatum'; sor: number; reszlet: string }
  | { tipus: 'tartomany'; sor: number; min: number; max: number };

interface Meres { szenzor: string; ertek: number }

function sorParse(sor: string, sorszam: number): Result<Meres, ParseHiba> {
  const [szenzor, nyers] = sor.split(',');
  if (!szenzor || nyers === undefined) return Err({ tipus: 'formatum', sor: sorszam, reszlet: 'két mező kell' });
  const ertek = Number(nyers);
  if (Number.isNaN(ertek)) return Err({ tipus: 'formatum', sor: sorszam, reszlet: `nem szám: ${nyers}` });
  if (ertek < -50 || ertek > 150) return Err({ tipus: 'tartomany', sor: sorszam, min: -50, max: 150 });
  return Ok({ szenzor: szenzor.trim(), ertek });
}

function osszes(szoveg: string): Result<Meres[], ParseHiba> {
  if (!szoveg.trim()) return Err({ tipus: 'ures' });
  const ki: Meres[] = [];
  for (const [i, sor] of szoveg.trim().split('\n').entries()) {
    const r = sorParse(sor, i + 1);
    if (!r.ok) return r;                // a hiba "felbuborékol", típusa megmarad
    ki.push(r.value);
  }
  return Ok(ki);
}

function hibaUzenet(h: ParseHiba): string {  // kimerítő: új hibatípusnál fordítási hiba
  switch (h.tipus) {
    case 'ures': return 'üres bemenet';
    case 'formatum': return `${h.sor}. sor: ${h.reszlet}`;
    case 'tartomany': return `${h.sor}. sor: [${h.min}, ${h.max}] tartományon kívül`;
  }
}

function probal<T>(fn: () => T): Result<T> {  // dobó külső kód becsomagolása
  try {
    return Ok(fn());
  } catch (e: unknown) {
    return Err(e instanceof Error ? e : new Error(String(e)));
  }
}

for (const bemenet of ['t1,21.5\nt2,19', 't1,21.5\nt2,abc', 't3,999', '']) {
  const r = osszes(bemenet);
  console.log(r.ok ? `átlag: ${(r.value.reduce((s, m) => s + m.ertek, 0) / r.value.length).toFixed(1)}` : hibaUzenet(r.error));
}
const json = probal((): unknown => JSON.parse('{rossz json}'));
if (!json.ok) console.log('JSON hiba:', json.error.message);
```

## Deklarációs fájlok (.d.ts) és module augmentation
<!-- q: Hogyan írjak típusdeklarációt egy típus nélküli JS csomaghoz, és hogyan bővítsem a globális vagy külső típusokat? -->
<!-- tags: declaration files, d.ts, declare module, module augmentation, declare global, declaration merging, processenv -->

A `.d.ts` fájl csak típusokat tartalmaz, futó kódot nem: így írható le egy típus nélküli JS csomag (ha nincs `@types/...`), vagy a bundler által kezelt nem-JS importok (`*.svg`, `*.module.css`). Fontos különbség: script-fájlban (nincs felső szintű import/export) a `declare module 'x'` új ambient modult deklarál, modul-fájlban viszont meglévő modult bővít (augmentation). A `declare global` és az interfész-összevonás (declaration merging) a globális típusokat bővíti, például a `process.env` mezőit vagy az Express `Request`-et. Ne feledd: a deklaráció csak ígéret a fordítónak — ha nem egyezik a valósággal, futásidőben hibázik.

```ts
// types/kulso.d.ts – SCRIPT fájl (nincs felső szintű import/export): ambient deklarációk
declare module 'regi-szamlazo' {
  export interface Szamla { sorszam: string; osszeg: number; kelt: Date }
  export function kiallit(vevo: string, tetelek: Array<{ nev: string; ar: number }>): Promise<Szamla>;
  const verzio: string;
  export default verzio;
}

declare module '*.svg' {             // a bundler URL-t ad vissza
  const url: string;
  export default url;
}
```

```ts
// types/bovitesek.d.ts – MODUL fájl (van export), ezért a declare module itt AUGMENTÁCIÓ
import 'express';

declare global {
  namespace NodeJS {
    interface ProcessEnv {           // process.env.DATABASE_URL: string, nem string | undefined
      readonly NODE_ENV: 'development' | 'production' | 'test';
      readonly DATABASE_URL: string;
      readonly PORT?: string;
    }
  }
  interface Window { __APP_VERZIO__: string }
}

declare module 'express-serve-static-core' {
  interface Request {                // interfész-összevonás a csomag saját típusával
    felhasznalo?: { id: string; szerepek: readonly string[] };
    keresAzon: string;
  }
}

export {};
```

```ts
// app.ts – a deklarációk használata (a d.ts-ek a tsconfig "include"-jában legyenek)
import verzio, { kiallit } from 'regi-szamlazo';
import logo from './assets/logo.svg';
import type { Request, Response, NextFunction } from 'express';

export function azonosito(req: Request, _res: Response, next: NextFunction): void {
  req.keresAzon = crypto.randomUUID();       // a bővített mező típusosan elérhető
  next();
}

const db: string = process.env.DATABASE_URL;  // string a ProcessEnv bővítés miatt
const szamla = await kiallit('Teszt Kft.', [{ nev: 'tanácsadás', ar: 50000 }]);
console.log(verzio, logo, db.startsWith('postgres'), szamla.sorszam);
```

## tsconfig: szigorú beállítások, amelyek hibákat fognak meg
<!-- q: Milyen tsconfig beállításokat használjak egy új TypeScript projektben, és mit fognak meg a szigorú opciók? -->
<!-- tags: tsconfig, strict, nouncheckedindexedaccess, exactoptionalpropertytypes, verbatimmodulesyntax, compiler options -->

A `strict: true` egy csomag ellenőrzést kapcsol be (`strictNullChecks`, `noImplicitAny`, `strictFunctionTypes`, `useUnknownInCatchVariables` stb.) — új projektben mindig legyen bekapcsolva. Érdemes mellé tenni a `noUncheckedIndexedAccess`-t (az indexelés eredménye `T | undefined`), az `exactOptionalPropertyTypes`-t (a hiányzó mező és az `undefined` értékű mező nem ugyanaz), a `noImplicitOverride`-ot és a `verbatimModuleSyntax`-ot (a csak típusként használt importot `import type`-pal kell jelölni). Node-hoz `module`/`moduleResolution: NodeNext`, bundlerhez `moduleResolution: Bundler` való; a `skipLibCheck` gyorsítja a fordítást.

```jsonc
// tsconfig.json – Node.js szolgáltatás / könyvtár szigorú alapbeállítása
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",              // a package.json "type" mezője dönti el: ESM vagy CJS
    "moduleResolution": "NodeNext",
    "lib": ["ES2023"],
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "verbatimModuleSyntax": true,      // import type kötelező a csak típus-importokra
    "isolatedModules": true,           // esbuild/swc fájlonként is helyesen fordíthat
    "skipLibCheck": true,
    "declaration": true,               // .d.ts generálás könyvtárhoz
    "sourceMap": true,
    "outDir": "dist",
    "rootDir": "src"
  },
  "include": ["src"]
}
```

```ts
// Mit fognak meg a szigorú opciók? (a "HIBA" sorok nem fordulnának le)
interface Felhasznalo { nev: string; becenev?: string }

function koszont(f: Felhasznalo | undefined): string {
  // return `Szia ${f.nev}`;                    // HIBA (strictNullChecks): f lehet undefined
  return `Szia ${f?.becenev ?? f?.nev ?? 'vendég'}`;
}

const pontszamok: Record<string, number> = { a1: 10 };
const tomb = [1, 2, 3];
// const dupla = pontszamok['b2'] * 2;          // HIBA (noUncheckedIndexedAccess): lehet undefined
const dupla = (pontszamok['b2'] ?? 0) * 2;
const elso = tomb[0];                           // number | undefined
if (elso !== undefined) console.log(elso.toFixed(1));
for (const x of tomb) console.log(x.toFixed(1)); // for...of nem érintett: x: number

const f1: Felhasznalo = { nev: 'teszt' };
// const f2: Felhasznalo = { nev: 'teszt', becenev: undefined }; // HIBA (exactOptionalPropertyTypes)

class Alap { indit(): void {} }
class Szarmaztatott extends Alap {
  override indit(): void { super.indit(); }     // override nélkül HIBA (noImplicitOverride)
}

try {
  JSON.parse('{');
} catch (e) {
  // console.log(e.message);                    // HIBA (useUnknownInCatchVariables): e unknown
  console.log(e instanceof Error ? e.message : String(e));
}
console.log(koszont(undefined), koszont(f1), dupla, new Szarmaztatott());
```

## Futásidejű validáció és típus-levezetés sémából
<!-- q: Hogyan validáljam a külső (API, JSON) adatokat TypeScriptben úgy, hogy a típus is a sémából jöjjön? -->
<!-- tags: runtime validation, schema, zod, type inference, infer, fetch, api, unknown -->

A típusok futásidőben nem léteznek, ezért egy `fetch().json()` vagy `JSON.parse` eredményét (ami `any`/`unknown`) csak validálás után szabad típusosként kezelni — egy `as Felhasznalo` cast semmit nem ellenőriz. A zod/valibot-féle könyvtárak ötlete, hogy a séma egyszerre végzi a futásidejű ellenőrzést és vezeti le a statikus típust (`Infer<typeof Sema>`), így nincs két, egymástól elcsúszó definíció. Az alábbi mini implementáció ugyanezt mutatja: a hibaüzenet a pontos mezőútvonalat adja, az ismeretlen mezők eldobódnak. Éles projektben használj kiforrott könyvtárat (zod, valibot, arktype).

```ts
type Sema<T> = { parse(x: unknown, ut?: string): T; opcionalis(): Sema<T | undefined> };
type Infer<S> = S extends Sema<infer T> ? T : never;

class ValidaciosHiba extends Error {
  constructor(public readonly ut: string, uzenet: string) { super(`${ut || '<gyökér>'}: ${uzenet}`); }
}

function sema<T>(parse: (x: unknown, ut: string) => T): Sema<T> {
  return {
    parse: (x, ut = '') => parse(x, ut),
    opcionalis: () => sema((x, ut) => (x === undefined ? undefined : parse(x, ut))),
  };
}

const z = {
  string: (opc: { min?: number; minta?: RegExp } = {}) => sema((x, ut) => {
    if (typeof x !== 'string') throw new ValidaciosHiba(ut, 'string kell');
    if (opc.min !== undefined && x.length < opc.min) throw new ValidaciosHiba(ut, `min. ${opc.min} karakter`);
    if (opc.minta && !opc.minta.test(x)) throw new ValidaciosHiba(ut, 'formátumhiba');
    return x;
  }),
  number: () => sema((x, ut) => {
    if (typeof x !== 'number' || !Number.isFinite(x)) throw new ValidaciosHiba(ut, 'véges szám kell');
    return x;
  }),
  literal: <const L extends readonly (string | number)[]>(...ertekek: L) => sema((x, ut) => {
    if (!ertekek.includes(x as L[number])) throw new ValidaciosHiba(ut, `${ertekek.join(' | ')} egyike kell`);
    return x as L[number];
  }),
  array: <T>(elem: Sema<T>) => sema((x, ut) => {
    if (!Array.isArray(x)) throw new ValidaciosHiba(ut, 'tömb kell');
    return x.map((e, i) => elem.parse(e, `${ut}[${i}]`));
  }),
  object: <S extends Record<string, Sema<unknown>>>(alak: S) => sema((x, ut) => {
    if (typeof x !== 'object' || x === null) throw new ValidaciosHiba(ut, 'objektum kell');
    const ki: Record<string, unknown> = {};
    for (const [k, s] of Object.entries(alak)) ki[k] = s.parse((x as Record<string, unknown>)[k], ut ? `${ut}.${k}` : k);
    return ki as { [K in keyof S]: Infer<S[K]> };   // az ismeretlen mezők eldobva
  }),
};

const FelhasznaloSema = z.object({
  id: z.number(),
  email: z.string({ minta: /^[^@\s]+@[^@\s]+$/ }),
  szerep: z.literal('admin', 'user'),
  cimkek: z.array(z.string({ min: 1 })),
  becenev: z.string().opcionalis(),
});
type Felhasznalo = Infer<typeof FelhasznaloSema>;    // a típus a sémából jön

async function lekerJson<T>(url: string, s: Sema<T>, signal?: AbortSignal): Promise<T> {
  const valasz = await fetch(url, { signal: signal ?? AbortSignal.timeout(5000) });
  if (!valasz.ok) throw new Error(`HTTP ${valasz.status}`);
  return s.parse(await valasz.json());               // validálatlan adat nem lép be a programba
}

const nyers: unknown = JSON.parse('{"id":7,"email":"x@example.com","szerep":"user","cimkek":["a"],"extra":1}');
const f: Felhasznalo = FelhasznaloSema.parse(nyers);
console.log(f.szerep, f.becenev ?? '-', typeof lekerJson);
try {
  FelhasznaloSema.parse({ id: 1, email: 'rossz', szerep: 'root', cimkek: [] });
} catch (e) {
  if (e instanceof ValidaciosHiba) console.log(e.message);  // "email: formátumhiba"
}
```
