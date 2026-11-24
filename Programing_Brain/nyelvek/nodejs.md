# Node.js
<!-- tech: nodejs -->
<!-- aliases: node, node.js, nodejs runtime, npm, libuv, v8 -->

A Node.js egy szerveroldali JavaScript-futtatókörnyezet: a V8 motor futtatja a JS kódot, a libuv könyvtár adja az eseményhurkot (event loop), az aszinkron hálózati I/O-t (epoll/kqueue/IOCP) és egy szálkészletet (threadpool) a fájlrendszer-, DNS-, tömörítési és kriptográfiai műveletekhez. A JS kód egy szálon fut, ezért az I/O-intenzív, sok egyidejű kapcsolatot kezelő szolgáltatásokra (API-k, valós idejű rendszerek, proxyk, CLI-k, build eszközök) kiváló, CPU-intenzív munkára viszont worker_threads vagy külön folyamat kell. Beépített modulok (`node:fs`, `node:http`, `node:stream`, `node:crypto`, `node:test`…) és az npm ökoszisztéma adják az erejét; ES modulokat és CommonJS-t is támogat. Buktató, hogy egyetlen blokkoló hívás vagy kezeletlen hiba az egész folyamatot érinti.

## Architektúra és az event loop fázisai: nextTick, microtask, setImmediate
<!-- q: Hogyan működik a Node.js event loop, és milyen sorrendben fut a process.nextTick, a Promise és a setImmediate? -->
<!-- tags: event loop, libuv, phases, nexttick, setimmediate, microtask, timers, threadpool -->

Az event loop fázisokban halad: timers (lejárt `setTimeout`/`setInterval`) → pending callbacks → poll (I/O események várása és feldolgozása) → check (`setImmediate`) → close callbacks. Minden egyes callback után először a `process.nextTick`-sor, majd a Promise microtask-sor ürül ki teljesen, és csak utána jön a következő callback. A fő modulból a `setTimeout(0)` és a `setImmediate` sorrendje nem determinisztikus, de I/O callbackből a `setImmediate` mindig előbb fut. Buktató: ES modulban a modul kiértékelése maga is egy Promise-job, ezért ott a top-level `Promise.then` a `nextTick` előtt fut; a rekurzív `nextTick` pedig kiéhezteti az I/O-t.

```js
// fazisok.cjs – futtatás: node fazisok.cjs (CommonJS, hogy a nextTick-sorrend a klasszikus legyen)
const fs = require('node:fs');

console.log('A: szinkron kód');
setTimeout(() => console.log('E/F: timers fázis – setTimeout 0'), 0);
setImmediate(() => console.log('E/F: check fázis – setImmediate'));
// ^ a fő modulból e kettő sorrendje NEM determinisztikus (a loop indulási idejétől függ)
Promise.resolve().then(() => console.log('D: microtask – Promise.then'));
queueMicrotask(() => console.log('D2: microtask – queueMicrotask'));
process.nextTick(() => console.log('C: nextTick-sor – minden Promise előtt'));
console.log('B: szinkron kód vége');

// I/O callbackből a sorrend garantált: poll -> check (setImmediate) -> következő kör: timers
fs.readFile(__filename, () => {
  setTimeout(() => console.log('  I/O után 3: setTimeout'), 0);
  setImmediate(() => console.log('  I/O után 2: setImmediate'));
  process.nextTick(() => console.log('  I/O után 1: nextTick'));
});

// unref(): ez az időzítő nem tartja életben a folyamatot (pl. háttér-metrikák)
const hatter = setInterval(() => console.log('soha nem fut le'), 60_000);
hatter.unref();

// Darabolt munka setImmediate-tel: minden lépés között sorra kerül az I/O és a timer is.
// Rekurzív process.nextTick ugyanerre ROSSZ: a nextTick-sor előbb ürül, az I/O éhezik.
let lepes = 0;
(function darab() {
  if (++lepes < 5) setImmediate(darab);
  else console.log('darabolt munka kész:', lepes, 'lépés');
})();
```

## Az event loop blokkolása, mérése és a libuv threadpool
<!-- q: Hogyan derítsem ki és kerüljem el, hogy a Node.js event loop blokkolva legyen? -->
<!-- tags: event loop lag, blocking, monitoreventloopdelay, threadpool, uv_threadpool_size, performance -->

Minden szinkron CPU-munka (nagy JSON feldolgozás, titkosítás `*Sync` változata, regex, ciklus) a teljes folyamatot megállítja: amíg fut, egyetlen másik kérés sem kap választ. A `perf_hooks.monitorEventLoopDelay` hisztogramja megmutatja, mennyit késik a loop (p99 és max a fontos metrika); hosszú munkát darabolni kell (`setImmediate` szeletek közt), vagy worker szálra tenni. A libuv threadpool alapból 4 szálú, és ezen fut minden `fs`, `dns.lookup`, `zlib`, `crypto.scrypt/pbkdf2` hívás — ha ezek torlódnak, a `UV_THREADPOOL_SIZE` növelése segít. A szinkron API-k (`readFileSync`, `scryptSync`) induláskor elfogadhatók, kérés-útvonalon nem.

```js
// blokkolas.mjs
import { monitorEventLoopDelay, performance } from 'node:perf_hooks';
import { scrypt } from 'node:crypto';
import { promisify } from 'node:util';

const h = monitorEventLoopDelay({ resolution: 10 });
h.enable();

function blokkolo(ms) {                       // CPU-munka a fő szálon: közben semmi más nem fut
  const veg = Date.now() + ms;
  while (Date.now() < veg);
}

async function darabolt(osszesMs, szelet = 5) {
  for (let kesz = 0; kesz < osszesMs; kesz += szelet) {
    blokkolo(szelet);
    await new Promise((r) => setImmediate(r)); // szeletenként visszaadjuk a vezérlést
  }
}

const ms = (ns) => (ns / 1e6).toFixed(1);
async function meres(cimke, fn) {
  h.reset();
  const t0 = performance.now();
  let tickek = 0;
  const id = setInterval(() => tickek++, 1); // "más kérések" szimulálása
  await fn();
  clearInterval(id);
  console.log(`${cimke.padEnd(18)} ${(performance.now() - t0).toFixed(0)} ms | ` +
    `loop-késés p99=${ms(h.percentile(99))} ms, max=${ms(h.max)} ms | közben lefutott tick: ${tickek}`);
}

await meres('blokkoló 200 ms', async () => blokkolo(200));
await meres('darabolt 200 ms', () => darabolt(200));

// 8 párhuzamos scrypt a 4 szálas poolon: két "hullámban" futnak le, de a loop szabad marad
const scryptAsync = promisify(scrypt);
await meres('8× scrypt (pool)', () =>
  Promise.all(Array.from({ length: 8 }, (_, i) => scryptAsync(`jelszo-${i}`, 'so', 64, { N: 2 ** 14 }))));
// Pool méret növelése indításkor: UV_THREADPOOL_SIZE=8 node blokkolas.mjs
```

## Fájlkezelés fs/promises-szel: atomikus írás és könyvtárbejárás
<!-- q: Hogyan kezeljem a fájlokat helyesen Node.js-ben async módon, atomikus írással és hibakezeléssel? -->
<!-- tags: fs, fs/promises, filehandle, atomic write, readdir, error codes, enoent, temp directory -->

A `node:fs/promises` Promise-alapú API-ja a libuv threadpoolon fut, így nem blokkolja az event loopot; a `FileHandle`-t mindig zárd le `finally`-ben, különben fájlleíró-szivárgás lesz. Fontos konfigurációs fájlt atomikusan írj: ideiglenes fájlba írás, `fsync`, majd `rename` (ugyanazon a fájlrendszeren atomikus), így áramszünet vagy összeomlás után sincs félkész fájl. A hibákat a `code` mező alapján különböztesd meg (`ENOENT`, `EACCES`, `EEXIST`): a hiányzó fájl gyakran várt eset, a jogosultsági hiba nem. Nagy könyvtárfát async generátorral járj be, hogy ne épüljön óriási tömb a memóriában.

```js
// fajlok.mjs
import { mkdtemp, mkdir, writeFile, rename, readFile, readdir, stat, rm, open } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';

async function atomikusIras(cel, tartalom) {
  const tmp = `${cel}.${process.pid}.${Date.now()}.tmp`;
  const fh = await open(tmp, 'w');
  try {
    await fh.writeFile(tartalom, 'utf8');
    await fh.sync();                       // fsync: tényleg lemezre kerüljön az átnevezés előtt
  } finally {
    await fh.close();                      // FileHandle-t MINDIG zárd
  }
  await rename(tmp, cel);                  // atomikus csere
}

async function* bejar(mappa) {             // lusta, rekurzív bejárás
  for (const b of await readdir(mappa, { withFileTypes: true })) {
    const teljes = path.join(mappa, b.name);
    if (b.isDirectory()) yield* bejar(teljes);
    else if (b.isFile()) yield teljes;
  }
}

async function jsonOlvas(fajl, alapertek) {
  try {
    return JSON.parse(await readFile(fajl, 'utf8'));
  } catch (e) {
    if (e.code === 'ENOENT') return alapertek; // hiányzó fájl: várt eset
    throw e;                                   // jogosultság, hibás JSON: a hívó dönt
  }
}

const munka = await mkdtemp(path.join(tmpdir(), 'pb-demo-')); // izolált ideiglenes mappa
try {
  await writeFile(path.join(munka, 'a.txt'), 'alma\n');
  await atomikusIras(path.join(munka, 'konfig.json'), JSON.stringify({ port: 8080 }));
  await mkdir(path.join(munka, 'al', 'mely'), { recursive: true });
  await writeFile(path.join(munka, 'al', 'mely', 'b.log'), 'x'.repeat(1024));

  let osszMeret = 0;
  for await (const fajl of bejar(munka)) {
    const { size } = await stat(fajl);
    osszMeret += size;
    console.log(path.relative(munka, fajl), size, 'bájt');
  }
  console.log('összesen:', osszMeret, 'bájt');
  console.log(await jsonOlvas(path.join(munka, 'konfig.json')), await jsonOlvas(path.join(munka, 'nincs.json'), {}));
} finally {
  await rm(munka, { recursive: true, force: true }); // takarítás hiba esetén is
}
```

## Streamek, backpressure és pipeline
<!-- q: Hogyan dolgozzak fel nagy adatmennyiséget streamekkel Node.js-ben, és mi a backpressure? -->
<!-- tags: streams, readable, writable, backpressure, pipeline, highwatermark, zlib, async iteration -->

A stream darabokban (chunk) dolgozza fel az adatot, így egy több GB-os fájl is konstans memóriával másolható, tömöríthető vagy hash-elhető. A backpressure azt jelenti, hogy ha a cél (pl. lassú hálózat) nem győzi, a `write()` `false`-t ad, és a forrásnak a `drain` eseményig várnia kell — enélkül a puffer korlátlanul nő. A `stream/promises` `pipeline` függvénye ezt automatikusan kezeli, és hiba esetén az összes streamet lezárja (a régi `.pipe()` nem!). A streamek async iterálhatók is (`for await`), és a pipeline elemei lehetnek async generátorok.

```js
// streamek.mjs
import { Readable, Writable, PassThrough } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { createGzip, createGunzip } from 'node:zlib';
import { createHash } from 'node:crypto';

function* sorok(n) {                       // lusta forrás: csak kérésre termel
  for (let i = 0; i < n; i++) yield `${i};szenzor-${i % 7};${(Math.sin(i) * 50).toFixed(2)}\n`;
}

let irasok = 0;
const lassuCel = new Writable({
  highWaterMark: 16 * 1024,                // ennyi pufferelt bájt felett write() -> false
  write(_chunk, _enc, kesz) {
    irasok++;
    setImmediate(kesz);                    // a kesz() hívásáig nem jön a következő chunk
  },
});

const hash = createHash('sha256');
const megfigyelo = new PassThrough();
megfigyelo.on('data', (d) => hash.update(d));
// pipeline: backpressure + hibánál minden stream lezárul (nincs fd-/memóriaszivárgás)
await pipeline(Readable.from(sorok(50_000)), megfigyelo, createGzip(), lassuCel);
console.log('tömörítve kiírva', irasok, 'chunkban, sha256:', hash.digest('hex').slice(0, 16));

async function kezziIras(cel, adatok) {    // ezt csinálja a pipeline is a háttérben
  for (const d of adatok) {
    if (!cel.write(d)) await new Promise((r) => cel.once('drain', r));
  }
  cel.end();
}

// Async generátor mint pipeline-elem (itt: célként gyűjti a tömörített chunkokat)
const tomoritett = [];
await pipeline(Readable.from(sorok(1000)), createGzip(), async function* (forras) {
  for await (const chunk of forras) tomoritett.push(chunk);
});
let sorDb = 0;
for await (const chunk of Readable.from(tomoritett).pipe(createGunzip())) {
  sorDb += chunk.toString('utf8').split('\n').length - 1; // a sor chunk-határon eltörhet – lásd Transform
}
console.log('visszafejtve', sorDb, 'sor');
await kezziIras(new Writable({ write: (_c, _e, k) => k() }), ['a', 'b']);
```

## Saját Transform stream: sorokra bontás és CSV feldolgozás
<!-- q: Hogyan írjak saját Transform streamet Node.js-ben, ami chunk-határon is helyesen bontja a sorokat? -->
<!-- tags: transform stream, objectmode, string_decoder, csv, line splitting, flush, writable -->

A `Transform` egyszerre írható és olvasható stream: a `_transform(chunk, enc, kesz)` feldolgozza a bejövő darabot és `push()`-sal ad ki eredményt, a `_flush` a stream végén üríti a maradékot. A chunkok tetszőleges helyen törhetnek — sor közepén, sőt egy több bájtos UTF-8 karakter közepén is —, ezért a félkész sort meg kell tartani, a bájtokat pedig `StringDecoder`-rel dekódolni. Az `objectMode` streamek bájtok helyett JS objektumokat adnak tovább, így tiszta, lépésenként tesztelhető ETL-lánc építhető. Hibás bemeneti sornál gyakran jobb eseményt kibocsátani és továbbmenni, mint az egész feldolgozást leállítani.

```js
// transform.mjs
import { Readable, Transform, Writable } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { StringDecoder } from 'node:string_decoder';

class SorBonto extends Transform {
  #maradek = '';
  #decoder = new StringDecoder('utf8');    // a kettévágott ékezetes karakter sem sérül
  constructor() { super({ readableObjectMode: true }); } // be: bájtok, ki: string objektumok
  _transform(chunk, _enc, kesz) {
    const sorok = (this.#maradek + this.#decoder.write(chunk)).split(/\r?\n/);
    this.#maradek = sorok.pop();           // az utolsó (talán félkész) sor várakozik
    for (const s of sorok) if (s) this.push(s);
    kesz();
  }
  _flush(kesz) {                           // a stream végén a maradék kiürítése
    const utolso = this.#maradek + this.#decoder.end();
    if (utolso) this.push(utolso);
    kesz();
  }
}

const csvParse = (fejlec) => new Transform({
  objectMode: true,
  transform(sor, _enc, kesz) {
    const mezok = sor.split(';');
    if (mezok.length !== fejlec.length) {
      this.emit('hibasSor', sor);          // nem állunk le, csak jelezzük
      return kesz();
    }
    kesz(null, Object.fromEntries(fejlec.map((f, i) => [f, mezok[i]])));
  },
});

const osszesites = new Map();
const aggregalo = new Writable({
  objectMode: true,
  write({ varos, osszeg }, _enc, kesz) {
    osszesites.set(varos, (osszesites.get(varos) ?? 0) + Number(osszeg));
    kesz();
  },
});

// Szándékosan 5 bájtos chunkok: a sorok ÉS az ékezetes karakterek is chunk-határon törnek
const nyers = Buffer.from('Győr;1200\nPécs;800\nGyőr;300\nrossz sor\nPécs;50');
const chunkok = Array.from({ length: Math.ceil(nyers.length / 5) }, (_, i) => nyers.subarray(i * 5, i * 5 + 5));

const parser = csvParse(['varos', 'osszeg']);
parser.on('hibasSor', (s) => console.log('kihagyott sor:', JSON.stringify(s)));
await pipeline(Readable.from(chunkok), new SorBonto(), parser, aggregalo);
console.log(Object.fromEntries(osszesites)); // { 'Győr': 1500, 'Pécs': 850 }
```

## EventEmitter minták: once, async iteráció és hibaesemények
<!-- q: Hogyan használjam helyesen az EventEmittert Node.js-ben, és hogyan kerüljem el a listener-szivárgást? -->
<!-- tags: eventemitter, events, once, on, error event, capturerejections, memory leak, maxlisteners -->

Az `EventEmitter` a Node publish/subscribe alapja (streamek, szerverek, socketek mind ebből származnak): az `emit` szinkron hívja a feliratkozókat a regisztrálás sorrendjében. Az `'error'` esemény speciális: ha nincs rá listener, a kibocsátása kivételt dob és a folyamat összeomlik. Az `events.once()` egy eseményt Promise-ként vár meg (AbortSignal-lal megszakíthatóan), az `events.on()` eseményfolyamot ad async iterátorként. A hosszú életű emitterre kérésenként felírt, soha le nem iratkozott listener klasszikus memóriaszivárgás — erre figyelmeztet a `MaxListenersExceededWarning` (10 listener felett).

```js
// esemenyek.mjs
import { EventEmitter, once, on } from 'node:events';
import { setTimeout as varj } from 'node:timers/promises';

class Letolto extends EventEmitter {
  constructor() {
    super({ captureRejections: true });   // async listener hibája 'error' eseményként jelenik meg
  }
  async indit(fajlok) {
    for (const [i, f] of fajlok.entries()) {
      await varj(10);
      if (f.startsWith('hibas')) {
        this.emit('error', new Error(`nem tölthető le: ${f}`)); // listener nélkül összeomlana!
        continue;
      }
      this.emit('halad', { fajl: f, szazalek: Math.round(((i + 1) / fajlok.length) * 100) });
    }
    this.emit('kesz', fajlok.length);
  }
}

const l = new Letolto();
l.on('halad', ({ fajl, szazalek }) => console.log(`${szazalek}% – ${fajl}`));
l.on('error', (e) => console.error('hiba:', e.message));
l.once('kesz', (db) => console.log('kész,', db, 'fájl'));   // egyszer fut, utána leiratkozik

// events.once: egy esemény bevárása Promise-ként, időkorláttal
const keszPromise = once(l, 'kesz', { signal: AbortSignal.timeout(5000) });
l.indit(['a.zip', 'hibas.zip', 'b.zip']);
const [db] = await keszPromise;
console.log('once eredmény:', db);

// events.on: eseményfolyam async iterátorként (pl. üzenetsor-fogyasztó)
const sor = new EventEmitter();
const vezerlo = new AbortController();
setTimeout(() => { for (const u of ['u1', 'u2', 'u3']) sor.emit('uzenet', u); }, 5);
setTimeout(() => vezerlo.abort(), 30);
try {
  for await (const [uzenet] of on(sor, 'uzenet', { signal: vezerlo.signal })) console.log('kapott:', uzenet);
} catch (e) {
  if (e.name !== 'AbortError') throw e;   // a megszakítás várt kilépés
}

console.log('listenerek:', l.listenerCount('halad'), '| max:', l.getMaxListeners());
l.removeAllListeners('halad');           // hosszú életű emitteren mindig iratkozz le
```

## HTTP szerver keretrendszer nélkül
<!-- q: Hogyan írjak HTTP API-t Node.js-ben keretrendszer nélkül, a node:http modullal? -->
<!-- tags: http, createserver, routing, request body, json api, body limit, timeouts, graceful shutdown -->

A `node:http` szerver minden kérésre egy `(req, res)` párt ad: a `req` egy Readable stream (a body-t neked kell beolvasni és méretkorláttal védeni), a `res` egy Writable. Keretrendszer nélkül a routingot, a JSON-feldolgozást, a hibakezelést és a státuszkódokat magad kezeled — ez kis szolgáltatásokhoz vagy a működés megértéséhez hasznos. Biztonsági alapok: body-méretkorlát (memória-DoS), `requestTimeout`/`headersTimeout` (slowloris), belső hibarészletek elrejtése a kliens elől. Leállításkor `server.close()` nem fogad új kapcsolatot, de megvárja a futó kéréseket.

```js
// szerver.mjs
import http from 'node:http';
import { randomUUID } from 'node:crypto';

const MAX_BODY = 1024 * 1024;              // 1 MB
const jegyzetek = new Map();

class HttpHiba extends Error {
  constructor(statusz, uzenet) { super(uzenet); this.statusz = statusz; }
}

async function jsonBody(req) {
  if (!req.headers['content-type']?.startsWith('application/json')) throw new HttpHiba(415, 'JSON kell');
  let meret = 0;
  const darabok = [];
  for await (const chunk of req) {         // a req egy Readable stream
    meret += chunk.length;
    if (meret > MAX_BODY) throw new HttpHiba(413, 'túl nagy kérés');
    darabok.push(chunk);
  }
  try { return JSON.parse(Buffer.concat(darabok).toString('utf8')); } catch { throw new HttpHiba(400, 'hibás JSON'); }
}

const utvonalak = {
  'GET /jegyzetek': async () => [200, [...jegyzetek.values()]],
  'POST /jegyzetek': async (req) => {
    const { szoveg } = await jsonBody(req);
    if (typeof szoveg !== 'string' || !szoveg.trim()) throw new HttpHiba(422, 'a szoveg kötelező');
    const j = { id: randomUUID(), szoveg: szoveg.trim(), letrehozva: new Date().toISOString() };
    jegyzetek.set(j.id, j);
    return [201, j];
  },
  'DELETE /jegyzetek/:id': async (_req, { id }) => (jegyzetek.delete(id) ? [204, null] : [404, { hiba: 'nincs ilyen' }]),
};
const mintak = Object.entries(utvonalak).map(([kulcs, kezelo]) => {
  const [method, minta] = kulcs.split(' ');
  return { method, re: new RegExp(`^${minta.replace(/:(\w+)/g, '(?<$1>[^/]+)')}$`), kezelo };
});

const szerver = http.createServer(async (req, res) => {
  const { pathname } = new URL(req.url, 'http://localhost');
  try {
    const talalat = mintak.find((m) => m.method === req.method && m.re.test(pathname));
    if (!talalat) throw new HttpHiba(404, 'nem található');
    const [statusz, adat] = await talalat.kezelo(req, talalat.re.exec(pathname).groups ?? {});
    res.writeHead(statusz, adat === null ? {} : { 'content-type': 'application/json; charset=utf-8' });
    res.end(adat === null ? undefined : JSON.stringify(adat));
  } catch (e) {
    const statusz = e instanceof HttpHiba ? e.statusz : 500;
    if (statusz === 500) console.error(e);    // a részleteket csak naplózzuk
    res.writeHead(statusz, { 'content-type': 'application/json; charset=utf-8', connection: 'close' });
    res.end(JSON.stringify({ hiba: statusz === 500 ? 'belső hiba' : e.message }));
  }
});
szerver.requestTimeout = 30_000;              // lassú kliensek ellen
szerver.headersTimeout = 10_000;
szerver.listen(3000, '127.0.0.1', () => console.log('http://127.0.0.1:3000'));

process.once('SIGTERM', () => {               // graceful shutdown
  szerver.close(() => process.exit(0));
  szerver.closeIdleConnections();
  setTimeout(() => process.exit(1), 10_000).unref();
});
```

## Express middleware-lánc és hibakezelés
<!-- q: Hogyan működnek a middleware-ek Expressben, milyen a sorrendjük, és hogyan kezeljem az async hibákat? -->
<!-- tags: express, middleware, router, error handling, next, validation, authorization -->

Az Express egy middleware-lánc: minden middleware `(req, res, next)` paramétert kap, és vagy választ küld, vagy `next()`-tel továbbad; a regisztrálás sorrendje számít (body-parser és naplózás elöl, 404 és hibakezelő a végén). A hibakezelő middleware-t a négy paraméter (`err, req, res, next`) különbözteti meg; `next(err)` hívással bármely pontról oda lehet ugrani. Express 5-ben az async handlerek elutasított Promise-a automatikusan a hibakezelőbe kerül (4-ben ehhez wrapper kellett). A `Router` moduláris route-csoportokat ad, a paraméterezett middleware-gyárak (jogosultság, validáció) újrahasznosíthatók.

```js
// app.mjs – Express 5
import express from 'express';
import { randomUUID } from 'node:crypto';

const app = express();
app.disable('x-powered-by');                      // ne áruld el a keretrendszert
app.use(express.json({ limit: '100kb' }));        // body-parse méretkorláttal

app.use((req, res, next) => {                     // kérés-azonosító + naplózás
  req.keresAzon = req.get('x-request-id') ?? randomUUID();
  const t0 = process.hrtime.bigint();
  res.setHeader('x-request-id', req.keresAzon);
  res.on('finish', () => {                        // a válasz elküldése után
    const ms = Number(process.hrtime.bigint() - t0) / 1e6;
    console.log(`${req.keresAzon} ${req.method} ${req.originalUrl} ${res.statusCode} ${ms.toFixed(1)}ms`);
  });
  next();
});

const szerepKell = (...szerepek) => (req, res, next) => {  // middleware-gyár
  const szerep = req.get('x-szerep');             // valós appban: ellenőrzött JWT vagy session
  if (!szerep) return res.status(401).json({ hiba: 'bejelentkezés szükséges' });
  if (!szerepek.includes(szerep)) return res.status(403).json({ hiba: 'nincs jogosultság' });
  next();
};

const validal = (sema) => (req, _res, next) => {
  const hibasMezok = Object.entries(sema).filter(([mezo, ok]) => !ok(req.body?.[mezo])).map(([m]) => m);
  if (hibasMezok.length) return next(Object.assign(new Error('validációs hiba'), { statusz: 422, mezok: hibasMezok }));
  next();
};

const termekek = express.Router();
const db = new Map();
termekek.get('/', (_req, res) => res.json([...db.values()]));
termekek.post('/', szerepKell('admin'),
  validal({ nev: (v) => typeof v === 'string' && v.length > 0, ar: Number.isInteger }),
  async (req, res) => {
    const t = { id: randomUUID(), nev: req.body.nev, ar: req.body.ar };
    await new Promise((r) => setTimeout(r, 5)); // pl. adatbázis-írás; hibája a hibakezelőbe megy
    db.set(t.id, t);
    res.status(201).json(t);
  });
termekek.get('/:id', (req, res, next) => {
  const t = db.get(req.params.id);
  if (!t) return next(Object.assign(new Error('nem található'), { statusz: 404 }));
  res.json(t);
});
app.use('/api/termekek', termekek);

app.use((_req, res) => res.status(404).json({ hiba: 'ismeretlen útvonal' })); // 404 a lánc végén

app.use((err, req, res, _next) => {               // 4 paraméter = hibakezelő
  const statusz = err.statusz ?? err.status ?? 500;
  if (statusz >= 500) console.error(req.keresAzon, err);
  res.status(statusz).json({ hiba: statusz >= 500 ? 'belső hiba' : err.message, mezok: err.mezok });
});

app.listen(3000, '127.0.0.1');
```

## Fastify: pluginek, JSON Schema validáció és hookok
<!-- q: Hogyan építsek gyors, sémával validált API-t Fastify-jal Node.js-ben? -->
<!-- tags: fastify, plugins, encapsulation, json schema, validation, hooks, decorate, serialization -->

A Fastify a teljesítményre és a sémákra épül: a route-hoz megadott JSON Schema alapján validálja a bemenetet (Ajv), a válasz-séma alapján pedig gyorsan szerializál és kiszűri a sémában nem szereplő mezőket (pl. belső adatokat). Minden plugin saját, encapsulált kontextust kap: az abban regisztrált hookok és dekorátorok csak ott érvényesek, hacsak `fastify-plugin`-nal nem "töröd át" a határt (megosztott erőforrásokhoz, pl. adatbázis). Az életciklus-hookok (`onRequest`, `preHandler`, `onSend`, `onClose`…) a middleware-ek helyett szolgálnak; a beépített pino logger kérésenkénti azonosítóval naplóz.

```js
// fastify-app.mjs
import Fastify from 'fastify';
import fp from 'fastify-plugin';
import { timingSafeEqual } from 'node:crypto';

const app = Fastify({ logger: { level: 'info' }, bodyLimit: 100 * 1024 });

const dbPlugin = fp(async (fastify) => {           // fp: a decorate a szülő scope-ban is látszik
  const tarolo = new Map();
  fastify.decorate('db', {
    lista: async () => [...tarolo.values()],
    ment: async (r) => { tarolo.set(r.id, r); return r; },
  });
  fastify.addHook('onClose', async () => tarolo.clear()); // takarítás leállításkor
});

const rendelesSema = {
  body: {
    type: 'object',
    required: ['termek', 'db'],
    additionalProperties: false,                   // ismeretlen mező -> 400
    properties: {
      termek: { type: 'string', minLength: 1, maxLength: 100 },
      db: { type: 'integer', minimum: 1, maximum: 50 },
    },
  },
  response: {
    201: { type: 'object', properties: { id: { type: 'string' }, termek: { type: 'string' }, db: { type: 'integer' } } },
  },
};

const kulcsOk = (kapott) => {                      // API kulcs környezeti változóból, konstans idejű összevetés
  const vart = Buffer.from(process.env.API_KULCS ?? '');
  const k = Buffer.from(String(kapott ?? ''));
  return vart.length > 0 && k.length === vart.length && timingSafeEqual(k, vart);
};

async function rendelesRoutok(fastify) {           // encapsulált: a hook csak ezekre a route-okra hat
  fastify.addHook('preHandler', async (req, reply) => {
    if (!kulcsOk(req.headers['x-api-kulcs'])) return reply.code(401).send({ hiba: 'érvénytelen API kulcs' });
  });
  fastify.get('/', async () => fastify.db.lista());
  fastify.post('/', { schema: rendelesSema }, async (req, reply) => {
    const r = await fastify.db.ment({ id: crypto.randomUUID(), ...req.body, belsoMegjegyzes: 'nem megy ki' });
    return reply.code(201).send(r);                // a belsoMegjegyzes-t a válasz-séma eldobja
  });
}

app.register(dbPlugin);
app.register(rendelesRoutok, { prefix: '/api/rendelesek' });
app.get('/egeszseg', async () => ({ ok: true, uptime: process.uptime() }));

app.setErrorHandler((err, req, reply) => {
  if (err.validation) return reply.code(400).send({ hiba: 'validáció', reszletek: err.message });
  req.log.error(err);
  return reply.code(err.statusCode ?? 500).send({ hiba: 'belső hiba' });
});

await app.listen({ port: 3000, host: '127.0.0.1' });
for (const jel of ['SIGINT', 'SIGTERM']) process.once(jel, () => app.close()); // onClose hookok lefutnak
```

## worker_threads: CPU-igényes munka párhuzamosan
<!-- q: Hogyan futtassak CPU-igényes számítást Node.js-ben az event loop blokkolása nélkül worker_threads-szel? -->
<!-- tags: worker_threads, worker pool, sharedarraybuffer, atomics, postmessage, parallelism, cpu bound -->

A `worker_threads` modul valódi párhuzamos szálakat ad: minden workernek saját V8 izolátuma, heapje és event loopja van, ezért a fő szál közben szabadon kiszolgálja a kéréseket. A kommunikáció `postMessage`-dzsel történik (strukturált klónozás, nagy `ArrayBuffer` átadható másolás nélkül `transferList`-tel), közös memóriát csak `SharedArrayBuffer` + `Atomics` ad. Worker indítása drága (tíz milliszekundumok, több MB memória), ezért kérésenként ne indíts újat — használj poolt (élesben pl. Piscina). I/O-ra a worker nem segít, az már alapból aszinkron.

```js
// workerek.mjs – ugyanaz a fájl a fő szál és a worker kódja is
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { availableParallelism } from 'node:os';

function primekSzama(tol, ig) {                    // szándékosan CPU-igényes
  let db = 0;
  for (let n = Math.max(2, tol); n < ig; n++) {
    let prim = true;
    for (let d = 2; d * d <= n; d++) if (n % d === 0) { prim = false; break; }
    if (prim) db++;
  }
  return db;
}

if (!isMainThread) {
  const szamlalo = new Int32Array(workerData.megosztott); // közös memória
  parentPort.on('message', ({ id, tol, ig }) => {
    const eredmeny = primekSzama(tol, ig);
    Atomics.add(szamlalo, 0, 1);                   // atomikus növelés, nincs versenyhelyzet
    parentPort.postMessage({ id, eredmeny });
  });
} else {
  class WorkerPool {
    #szabad = [];
    #sor = [];
    #varakozok = new Map();
    #kovId = 0;
    constructor(meret, adat) {
      for (let i = 0; i < meret; i++) {
        const w = new Worker(new URL(import.meta.url), { workerData: adat });
        w.on('message', ({ id, eredmeny }) => {
          this.#varakozok.get(id).resolve(eredmeny);
          this.#varakozok.delete(id);
          this.#szabad.push(w);
          this.#kovetkezo();
        });
        w.on('error', (e) => { for (const v of this.#varakozok.values()) v.reject(e); });
        this.#szabad.push(w);
      }
    }
    futtat(feladat) {
      return new Promise((resolve, reject) => {
        const id = this.#kovId++;
        this.#varakozok.set(id, { resolve, reject });
        this.#sor.push({ id, ...feladat });
        this.#kovetkezo();
      });
    }
    #kovetkezo() {
      while (this.#szabad.length && this.#sor.length) this.#szabad.pop().postMessage(this.#sor.shift());
    }
    lezar() { return Promise.all(this.#szabad.map((w) => w.terminate())); }
  }

  const megosztott = new SharedArrayBuffer(4);
  const pool = new WorkerPool(availableParallelism(), { megosztott });
  const HATAR = 4_000_000;
  const DARAB = 16;
  const t0 = performance.now();
  const reszek = await Promise.all(Array.from({ length: DARAB }, (_, i) =>
    pool.futtat({ tol: (i * HATAR) / DARAB, ig: ((i + 1) * HATAR) / DARAB })));
  console.log(`prímek < ${HATAR}: ${reszek.reduce((a, b) => a + b)} – ${(performance.now() - t0).toFixed(0)} ms,`,
    `kész darabok (Atomics): ${Atomics.load(new Int32Array(megosztott), 0)}`);
  await pool.lezar();
}
```

## cluster és child_process: több folyamat és külső programok
<!-- q: Hogyan használjam a cluster és a child_process modult Node.js-ben, és mikor melyiket? -->
<!-- tags: cluster, child_process, spawn, execfile, fork, ipc, multi-process, zero downtime -->

A `cluster` több Node-folyamatot indít ugyanarra a portra: a primary folyamat osztja szét a kapcsolatokat a workerek között, így egy HTTP szerver minden CPU-magot kihasználhat, és egy összeomlott worker újraindítható. A `child_process` külső programokat futtat: az `execFile`/`spawn` argumentumtömbbel, shell nélkül biztonságos, az `exec` shellen át fut (injekció-veszély, és a kimenetet pufferelve `maxBuffer` felett hibázik). Nagy kimenethez `spawn` + stream kell, Node-gyerekfolyamattal pedig a `fork` IPC-csatornát is ad. Konténeres környezetben gyakran egyszerűbb több egyfolyamatos replikát futtatni cluster helyett.

```js
// folyamatok.mjs
import cluster from 'node:cluster';
import http from 'node:http';
import { availableParallelism } from 'node:os';
import { execFile, spawn } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

if (cluster.isPrimary) {
  const n = Math.min(availableParallelism(), 4);
  console.log(`primary ${process.pid}: ${n} worker indítása`);
  for (let i = 0; i < n; i++) cluster.fork();

  cluster.on('exit', (w, kod, jel) => {           // összeomlott worker pótlása
    console.log(`worker ${w.process.pid} kilépett (${jel ?? kod})`);
    if (!w.exitedAfterDisconnect) cluster.fork(); // élesben backoff-fal, hogy ne pörögjön
  });
  cluster.on('message', (w, uzenet) => console.log(`IPC ${w.process.pid}:`, uzenet));

  process.on('SIGUSR2', async () => {             // gördülő újraindítás (zero-downtime deploy)
    for (const w of Object.values(cluster.workers)) {
      const uj = cluster.fork();
      await new Promise((r) => uj.once('listening', r));
      w.disconnect();                             // a régi befejezi a futó kéréseit
    }
  });

  // execFile: argumentumtömb, shell nélkül, időkorláttal
  const { stdout } = await execFileAsync(process.execPath, ['--version'], { timeout: 5000 });
  console.log('node verzió (gyerekfolyamatból):', stdout.trim());

  // spawn: streamelt kimenet nagy adatmennyiséghez
  const gyerek = spawn(process.execPath, ['-e', 'for (let i = 0; i < 3; i++) console.log("sor", i)'],
    { stdio: ['ignore', 'pipe', 'inherit'] });
  for await (const chunk of gyerek.stdout) process.stdout.write(`[gyerek] ${chunk}`);
} else {
  http.createServer((_req, res) => {              // minden worker ugyanazon a porton figyel
    res.end(`kiszolgálta: ${process.pid}\n`);
  }).listen(3000, '127.0.0.1');
  process.send?.({ allapot: 'kész', pid: process.pid });
}
```

## ES modulok és CommonJS Node.js-ben
<!-- q: Mi a különbség az ES modulok és a CommonJS között Node.js-ben, és hogyan használjam őket együtt? -->
<!-- tags: esm, commonjs, require, import, import.meta, createrequire, __dirname, interop, dual package -->

A Node két modulrendszert támogat: a CommonJS (`require`, `module.exports`) szinkron tölt be és az exportált primitívekről másolatot ad, az ES modul (`import`/`export`) aszinkron, statikusan elemezhető, élő kötésekkel és top-level await-tel. Hogy egy `.js` fájl melyik, azt a legközelebbi `package.json` `"type"` mezője dönti el; a `.mjs` mindig ESM, a `.cjs` mindig CJS. ESM-ben nincs `__dirname`, `__filename` és `require` — helyettük `import.meta.dirname`/`import.meta.url` és `createRequire`, a relatív importhoz pedig kötelező a kiterjesztés. CJS-ből ESM-et a dinamikus `import()` mindig betölt, újabb Node-ban (22.12+, 20.19+) a `require(esm)` is működik, ha a modulban nincs top-level await.

```js
// esm-modul.mjs
import { readFile } from 'node:fs/promises';     // node: prefix – egyértelműen beépített modul
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// ESM-ben nincs __dirname/__filename – import.meta-ból állítjuk elő
const __filename = fileURLToPath(import.meta.url);
const __dirname = import.meta.dirname ?? path.dirname(__filename); // Node 20.11+: import.meta.dirname

// require ESM-ben: createRequire (pl. JSON vagy csak-CJS csomag szinkron betöltésére)
const require = createRequire(import.meta.url);
const pkg = require('./package.json');
// ESM-natív JSON import: import pkg from './package.json' with { type: 'json' };

const sajatForras = await readFile(__filename, 'utf8');  // top-level await csak ESM-ben

// CJS csomag importja ESM-ből: a module.exports a default export;
// a named import csak akkor megy, ha a Node statikusan felismeri az exportneveket.
const { default: os } = await import('node:os');       // dinamikus import
console.log(pkg.name, sajatForras.length, os.platform(), __dirname);

export const VERZIO = pkg.version;                     // relatív importnál: './esm-modul.mjs' (kiterjesztéssel!)
```

```js
// regi-modul.cjs
'use strict';
const path = require('node:path');

let hivasok = 0;
function szamol() { return ++hivasok; }

// A module.exports egy objektum; a primitív érték kiolvasáskor másolódik (nincs live binding),
// ezért az aktuális értéket getterrel tesszük elérhetővé.
module.exports = {
  szamol,
  get hivasok() { return hivasok; },
  gyoker: path.resolve(__dirname),
};

// ESM betöltése CJS-ből: dinamikus import() mindig működik
module.exports.esmVerzio = async () => (await import('./esm-modul.mjs')).VERZIO;

if (require.main === module) {                         // közvetlen futtatás vs. importálás
  console.log('közvetlenül futtatva', module.exports.szamol(), module.exports.hivasok);
}
```

## npm csomag készítése: package.json, exports, bin és semver
<!-- q: Hogyan állítsam be a package.json-t egy npm csomag publikálásához (exports, bin, files, engines)? -->
<!-- tags: npm, package.json, exports, bin, semver, files, engines, publish, cli, dual package -->

A `package.json` `exports` mezője a csomag nyilvános belépési pontjait határozza meg: ami nincs benne, azt a felhasználók nem importálhatják (belső fájlok elrejtése), és feltételes exporttal külön ESM (`import`), CJS (`require`) és típus (`types`) fájl adható. A `bin` mező futtatható parancsot telepít, a `files` szűkíti a publikált tartalmat (titkok és tesztek ne kerüljenek ki), az `engines` jelzi a támogatott Node-verziót. A semver tartományok (`^1.4.0` = 1.x, `~1.4.0` = 1.4.x) a függőségek frissítését szabályozzák, a lockfile (`package-lock.json`) pedig reprodukálható telepítést ad — alkalmazásnál mindig commitold, CI-ban `npm ci`-t használj.

```json
{
  "name": "@pelda/naplo-szuro",
  "version": "1.4.0",
  "description": "Naplófájlok szűrése naplószint alapján",
  "type": "module",
  "license": "MIT",
  "engines": { "node": ">=20.11" },
  "exports": {
    ".": {
      "types": "./dist/index.d.ts",
      "import": "./dist/index.js",
      "require": "./dist/index.cjs"
    },
    "./package.json": "./package.json"
  },
  "bin": { "naplo-szuro": "./dist/cli.js" },
  "files": ["dist", "README.md"],
  "sideEffects": false,
  "scripts": {
    "build": "tsup src/index.ts src/cli.ts --format esm,cjs --dts",
    "test": "node --test",
    "prepublishOnly": "npm run build && npm test"
  },
  "dependencies": { "picocolors": "^1.1.0" },
  "devDependencies": { "tsup": "^8.3.0", "typescript": "^5.6.0" },
  "publishConfig": { "access": "public", "provenance": true }
}
```

```js
#!/usr/bin/env node
// dist/cli.js – a "bin" belépési pontja (Unixon a shebang kell; Windowson az npm .cmd shimet generál)
import { parseArgs } from 'node:util';
import { createReadStream } from 'node:fs';
import { createInterface } from 'node:readline';

const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    szint: { type: 'string', short: 's', default: 'ERROR' },
    help: { type: 'boolean', short: 'h' },
  },
});

if (values.help || positionals.length === 0) {
  console.log('Használat: naplo-szuro [-s SZINT] <fájl...>');
  process.exit(values.help ? 0 : 2);             // 2: hibás használat
}

let talalat = 0;
for (const fajl of positionals) {
  // soronkénti olvasás streamből: nagy naplófájl sem kerül egészben a memóriába
  const sorok = createInterface({ input: createReadStream(fajl), crlfDelay: Infinity });
  for await (const sor of sorok) {
    if (sor.includes(` ${values.szint} `)) {
      talalat++;
      process.stdout.write(`${fajl}: ${sor}\n`);
    }
  }
}
process.exitCode = talalat > 0 ? 0 : 1;          // exitCode: a függő kiírás még befejeződhet
```

## Folyamat-életciklus: graceful shutdown, kezeletlen hibák, AsyncLocalStorage
<!-- q: Hogyan állítsam le szabályosan egy Node.js szervert, és hogyan kezeljem a kezeletlen hibákat? -->
<!-- tags: graceful shutdown, sigterm, sigint, uncaughtexception, unhandledrejection, asynclocalstorage, process -->

Konténerben (Docker, Kubernetes) a leállítás `SIGTERM` jellel érkezik: ilyenkor a szerver ne fogadjon új kapcsolatot, fejezze be a futó kéréseket, zárja le az adatbázis-poolt, és időkorláton belül lépjen ki — különben a kérések félbeszakadnak. Kezeletlen kivétel vagy Promise-elutasítás után a folyamat állapota ismeretlen: naplózz és lépj ki, a process manager (systemd, k8s, PM2) újraindít. Az `AsyncLocalStorage` kérésenkénti kontextust (kérés-azonosító, felhasználó, trace) visz végig az async láncon anélkül, hogy minden függvénynek paraméterként kellene átadni. A `process.exitCode` beállítása jobb a `process.exit()`-nél, mert hagyja befejeződni a függő I/O-t.

```js
// eletciklus.mjs
import http from 'node:http';
import { AsyncLocalStorage } from 'node:async_hooks';
import { randomUUID } from 'node:crypto';
import { setTimeout as varj } from 'node:timers/promises';

const kontextus = new AsyncLocalStorage();
const naplo = (...a) => console.log(`[${kontextus.getStore()?.keresAzon ?? '-'}]`, ...a);

async function adatbazisLekerdezes() {
  await varj(20);                           // akárhány await után is látszik a kontextus
  naplo('lekérdezés kész');
  return { sorok: 3 };
}

const aktivKeresek = new Set();
const szerver = http.createServer((req, res) => {
  kontextus.run({ keresAzon: randomUUID().slice(0, 8) }, async () => {
    const jelolo = Symbol('keres');
    aktivKeresek.add(jelolo);
    try {
      naplo(req.method, req.url);
      res.end(JSON.stringify(await adatbazisLekerdezes()));
    } catch (e) {
      naplo('hiba', e);
      if (!res.headersSent) res.writeHead(500).end();
    } finally {
      aktivKeresek.delete(jelolo);
    }
  });
});
szerver.listen(3000, '127.0.0.1');

let leall = false;
async function leallitas(jel) {
  if (leall) return;                        // többszöri jel ellen
  leall = true;
  console.log(`${jel}: leállás, ${aktivKeresek.size} aktív kérés`);
  setTimeout(() => { console.error('időtúllépés, kényszerített kilépés'); process.exit(1); }, 10_000).unref();
  szerver.close();                          // új kapcsolatot nem fogad
  szerver.closeIdleConnections();           // üresjárati keep-alive kapcsolatok bontása
  while (aktivKeresek.size) await varj(50); // futó kérések bevárása
  // itt zárd le: adatbázis-pool, üzenetsor-kliens, fájlok
  console.log('tiszta leállás');
  process.exitCode = 0;
}
process.once('SIGTERM', leallitas);         // Docker/Kubernetes
process.once('SIGINT', leallitas);          // Ctrl+C

process.on('unhandledRejection', (ok) => { throw ok; }); // egységesen uncaughtExceptionként kezeljük
process.on('uncaughtException', (err, eredet) => {
  console.error('VÉGZETES', eredet, err);
  process.exit(1);                          // ismeretlen állapot: kilépés, a supervisor újraindít
});
```

## Biztonság Node.js-ben: path traversal, jelszavak, parancsinjekció
<!-- q: Milyen biztonsági hibákat kell elkerülni Node.js szerveren, és hogyan tároljam a jelszavakat? -->
<!-- tags: security, path traversal, crypto, scrypt, timingsafeequal, hmac, command injection, execfile, secrets -->

Statikus fájlkiszolgálásnál a `../` (vagy URL-kódolt `%2e%2e%2f`, Windows-on `..\`) kijuthat a gyökérmappából: dekódolás és `path.resolve` után ellenőrizd, hogy a cél tényleg a gyökéren belül van. Jelszót lassú, sózott KDF-fel tárolj (`crypto.scrypt` vagy argon2), titkot/tokent `timingSafeEqual`-lal hasonlíts össze, és véletlen értékhez `randomBytes`/`randomUUID` kell. Külső programot `execFile`-lal, argumentumtömbbel indíts (nem `exec` + string), és a `-`-szal kezdődő felhasználói értéket utasítsd el (opció-injekció). A titkok környezeti változóból vagy secret managerből jöjjenek, soha ne a kódból vagy a repóból.

```js
// biztonsag.mjs
import { createServer } from 'node:http';
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { scrypt, randomBytes, timingSafeEqual, createHmac } from 'node:crypto';
import { promisify } from 'node:util';

const scryptAsync = promisify(scrypt);
const GYOKER = path.resolve('public');

async function statikusFajl(urlPath) {
  const dekodolt = decodeURIComponent(urlPath);          // %2e%2e%2f trükkök feloldása
  if (dekodolt.includes('\0')) return null;              // null byte
  const cel = path.resolve(GYOKER, '.' + path.posix.normalize('/' + dekodolt));
  if (cel !== GYOKER && !cel.startsWith(GYOKER + path.sep)) return null; // gyökéren kívül: tiltott
  const s = await stat(cel).catch(() => null);
  return s?.isFile() ? cel : null;
}

async function jelszoHash(jelszo) {
  const so = randomBytes(16);                            // felhasználónként egyedi só
  const kulcs = await scryptAsync(jelszo.normalize('NFKC'), so, 64);
  return `scrypt$${so.toString('base64')}$${kulcs.toString('base64')}`;
}
async function jelszoEllenoriz(jelszo, tarolt) {
  const [, soB64, kulcsB64] = tarolt.split('$');
  const vart = Buffer.from(kulcsB64, 'base64');
  const kapott = await scryptAsync(jelszo.normalize('NFKC'), Buffer.from(soB64, 'base64'), vart.length);
  return timingSafeEqual(vart, kapott);                  // konstans idejű összehasonlítás
}

// HMAC-aláírt token; a titok környezeti változóból jön (a véletlen tartalék csak fejlesztéshez)
const TITOK = process.env.TOKEN_TITOK ?? randomBytes(32).toString('hex');
const alair = (adat) => `${adat}.${createHmac('sha256', TITOK).update(adat).digest('base64url')}`;

function miniatur(fajl, kesz) {
  if (fajl.startsWith('-')) return kesz(new Error('érvénytelen fájlnév')); // opció-injekció ellen
  // exec(`convert ${fajl} ...`) helyett: argumentumtömb, shell nélkül, időkorláttal
  execFile('convert', [fajl, '-resize', '200x200', 'miniatur.png'], { timeout: 10_000 }, kesz);
}

createServer(async (req, res) => {
  const fajl = await statikusFajl(new URL(req.url, 'http://localhost').pathname).catch(() => null);
  if (!fajl) return res.writeHead(404).end();
  res.writeHead(200, { 'x-content-type-options': 'nosniff' });
  createReadStream(fajl).pipe(res);
}).listen(8080, '127.0.0.1');

const hash = await jelszoHash('demo-jelszo');
console.log(await jelszoEllenoriz('demo-jelszo', hash), await jelszoEllenoriz('rossz', hash), alair('felhasznalo:42'));
console.log(typeof miniatur);
// Továbbiak: npm audit + lockfile, helmet és rate limit HTTP-hez, Node permission model
// (node --permission --allow-fs-read=./public app.mjs), függőségek minimalizálása.
```

## Memória, szivárgások és profilozás
<!-- q: Hogyan találjam meg a memóriaszivárgást és a lassú kódot egy Node.js alkalmazásban? -->
<!-- tags: memory, heap, garbage collection, memory leak, heap snapshot, perf_hooks, cpu profile, inspect -->

A `process.memoryUsage()` megmutatja a teljes folyamat (`rss`), a JS heap (`heapUsed`) és a V8-on kívüli memória (`external`, pl. Bufferek) méretét; ha a `heapUsed` a GC-k után is folyamatosan nő, szivárgás van. Tipikus okok: hosszú életű emitterre kérésenként felírt listener, korlát nélküli Map-cache, nagy objektumot bezáró closure, leállítatlan időzítő. Két, időben eltérő heap snapshot (`v8.writeHeapSnapshot()` vagy `--inspect` + Chrome DevTools Memory fül) összevetése megmutatja, mely objektumok halmozódnak. CPU-oldalon a `--cpu-prof` profil és a `perf_hooks` mérései (mark/measure, `timerify`) mutatják a forró pontokat; a heap limitet a `--max-old-space-size` állítja.

```js
// memoria.mjs – futtatás: node --expose-gc memoria.mjs
import { getHeapStatistics, writeHeapSnapshot } from 'node:v8';
import { performance, PerformanceObserver } from 'node:perf_hooks';
import { EventEmitter } from 'node:events';

const mb = (b) => `${(b / 1024 / 1024).toFixed(1)} MB`;
const allapot = (cimke) => {
  const m = process.memoryUsage();
  console.log(cimke.padEnd(18), 'rss', mb(m.rss), '| heapUsed', mb(m.heapUsed), '| external', mb(m.external));
};

const busz = new EventEmitter();
busz.setMaxListeners(0);                 // a figyelmeztetés elnémítása – élesben NE tedd!
function kezeloSzivargo() {
  const nagyValasz = Buffer.alloc(100 * 1024);
  busz.on('konfigValtozott', () => nagyValasz.length); // soha nem iratkozik le -> szivárgás
}
function kezeloJo() {
  const nagyValasz = Buffer.alloc(100 * 1024);
  const kezelo = () => nagyValasz.length;
  busz.on('konfigValtozott', kezelo);
  busz.off('konfigValtozott', kezelo);   // a kérés végén takarítunk
}

allapot('kezdet');
for (let i = 0; i < 500; i++) kezeloSzivargo();
globalThis.gc?.();
allapot('500 szivárgó kérés');
for (let i = 0; i < 500; i++) kezeloJo();
globalThis.gc?.();
allapot('500 jó kérés');
console.log('listenerek:', busz.listenerCount('konfigValtozott'), '| heap limit:', mb(getHeapStatistics().heap_size_limit));

const obs = new PerformanceObserver((lista) => {
  for (const e of lista.getEntries()) console.log(`mérés: ${e.name} ${e.duration.toFixed(2)} ms`);
});
obs.observe({ entryTypes: ['measure', 'function'] });
const rendez = performance.timerify(function rendez(n) {  // minden hívás mérve
  return Array.from({ length: n }, () => Math.random()).sort((a, b) => a - b).length;
});
performance.mark('start');
rendez(200_000);
performance.mark('vege');
performance.measure('rendezés blokk', 'start', 'vege');

if (process.env.SNAPSHOT === '1') console.log('heap snapshot:', writeHeapSnapshot()); // DevTools-ban nyitható
// CPU-profil: node --cpu-prof app.mjs | élő hibakeresés: node --inspect app.mjs + chrome://inspect
setTimeout(() => obs.disconnect(), 10);
```
