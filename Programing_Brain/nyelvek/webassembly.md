# WebAssembly
<!-- tech: webassembly -->
<!-- aliases: wasm, wat, wasi -->

A WebAssembly (Wasm) hordozható, verem-alapú bináris utasításformátum: C, C++, Rust, Go, Zig és más
nyelvek fordíthatók rá, és közel natív sebességgel fut a böngészőben, Node.js-ben vagy önálló
futtatókörnyezetben (wasmtime, wasmer, WasmEdge). Szigorúan típusos (i32, i64, f32, f64, v128 és
referenciatípusok), a memóriája egyetlen, határellenőrzött lineáris bájttömb, és sandboxban fut: csak
azt érheti el, amit importként kap. A szöveges formája a WAT, a böngészőn kívüli rendszerinterfésze a
WASI. Számításigényes, kiszámítható munkához (kép- és hangfeldolgozás, tömörítés, kriptográfia,
szimuláció, meglévő natív könyvtárak webre hozása) ideális; DOM-manipulációhoz és apró, gyakori
JS-hívásokhoz nem, mert a határátlépés és az adatmásolás elviheti a nyereséget.

## Modulszerkezet és a WAT szöveges formátum
<!-- q: Hogyan néz ki egy WebAssembly modul szöveges (WAT) formában, és hogyan működik a verem? -->
<!-- tags: wat, text format, module, stack machine, func, export, i32, s-expression -->

Egy Wasm modul típusokból, importokból, függvényekből, táblákból, memóriából, globálokból és exportokból
áll; a WAT ezek S-kifejezéses szöveges leírása, amely a binárissal kölcsönösen átalakítható
(wat2wasm / wasm-tools). A végrehajtás verem-alapú: minden utasítás a veremről vesz le operandusokat,
és oda teszi az eredményt; a "folded" írásmód ugyanezt beágyazott kifejezésekként mutatja. Az egész
típusok nem tárolnak előjelet, az utasítás dönti el az értelmezést (div_s vagy div_u). Nullával osztás,
túlcsorduló konverzió vagy határon kívüli memóriaelérés trapet (futásidejű kivételt) okoz.

```wat
(module
  ;; Lineáris (verem) forma: minden utasítás a veremmel dolgozik
  (func $add (export "add") (param $a i32) (param $b i32) (result i32)
    local.get $a        ;; verem: [a]
    local.get $b        ;; verem: [a, b]
    i32.add)            ;; verem: [a+b] -> ez a visszatérési érték

  ;; Ugyanez "folded" formában: lineáris interpoláció f64-en
  (func $lerp (export "lerp") (param $a f64) (param $b f64) (param $t f64) (result f64)
    (f64.add
      (local.get $a)
      (f64.mul
        (f64.sub (local.get $b) (local.get $a))
        (local.get $t))))

  ;; Az előjelet az utasítás dönti el, nem a típus
  (func (export "divs") (param i32 i32) (result i32)
    (i32.div_s (local.get 0) (local.get 1)))      ;; -7 / 2 = -3
  (func (export "divu") (param i32 i32) (result i32)
    (i32.div_u (local.get 0) (local.get 1)))      ;; 0xFFFFFFF9 / 2 = 2147483644

  ;; Biztonságos osztás: a nullával osztás trap lenne, ezért előbb ellenőrzünk
  (func (export "safe_div") (param $a i32) (param $b i32) (result i32)
    (if (result i32) (i32.eqz (local.get $b))
      (then (i32.const 0))
      (else (i32.div_s (local.get $a) (local.get $b)))))
)
```

```bash
wat2wasm math.wat -o math.wasm
wasm-tools validate math.wasm
wasm-tools print math.wasm
```

## Vezérlési szerkezetek: block, loop, br_if, br_table
<!-- q: Hogyan írjak ciklust és elágazást WebAssembly szöveges formátumban? -->
<!-- tags: wat, control flow, block, loop, br, br_if, br_table, if, select -->

A Wasm strukturált vezérlést használ, nincs tetszőleges goto: a block címkéjére ugrás (br) a blokk
VÉGÉRE visz (break), a loop címkéjére ugrás a ciklus ELEJÉRE (continue). A br_if feltételes ugrás, a
br_table ugrótábla (switch), az if/else pedig értéket is visszaadhat, ha mindkét ág azonos típust hagy
a veremen. A select elágazás nélküli feltételes választás, ami rövid, kiszámítható kódnál gyorsabb lehet.
A validátor fordításkor ellenőrzi a verem típusait minden ágon, ezért a hibás vezérlési kód be sem töltődik.

```wat
(module
  ;; n! iteratívan, i64 eredménnyel
  (func (export "fact") (param $n i32) (result i64)
    (local $acc i64)
    (local.set $acc (i64.const 1))
    (block $done                               ;; br $done -> a block végére (break)
      (loop $next                              ;; br $next -> a loop elejére (continue)
        (br_if $done (i32.le_s (local.get $n) (i32.const 1)))
        (local.set $acc
          (i64.mul (local.get $acc) (i64.extend_i32_s (local.get $n))))
        (local.set $n (i32.sub (local.get $n) (i32.const 1)))
        (br $next)))
    (local.get $acc))

  ;; if/else értékkel + select (ternáris operátor elágazás nélkül)
  (func (export "clamp") (param $x i32) (param $lo i32) (param $hi i32) (result i32)
    (if (result i32) (i32.lt_s (local.get $x) (local.get $lo))
      (then (local.get $lo))
      (else
        (select
          (local.get $hi)                      ;; ha a feltétel igaz
          (local.get $x)                       ;; ha hamis
          (i32.gt_s (local.get $x) (local.get $hi))))))

  ;; br_table: 0-4 -> hétköznap (0), 5 -> szombat (1), egyéb -> vasárnap (2)
  (func (export "day_type") (param $d i32) (result i32)
    (block $weekend
      (block $sat
        (block $weekday
          ;; az utolsó címke az alapértelmezett (default) ág
          (br_table $weekday $weekday $weekday $weekday $weekday $sat $weekend
                    (local.get $d)))
        (return (i32.const 0)))
      (return (i32.const 1)))
    (i32.const 2))
)
```

## Lineáris memória
<!-- q: Hogyan működik a WebAssembly lineáris memóriája, és hogyan olvasok-írok benne? -->
<!-- tags: linear memory, memory, load, store, data segment, memory.grow, bulk memory, pages -->

A Wasm memória egyetlen összefüggő, bájtcímzett tömb 64 KiB-os lapokban; a load/store utasítások
little-endian módon olvasnak és írnak, és minden elérés határellenőrzött, így a hibás cím trapet okoz,
nem pedig a gazdagép memóriájának sérülését. A data szegmens példányosításkor tölti fel a memóriát
(konstans adatok, stringek), a memory.grow lapokkal bővít, és a régi lapszámot (hiba esetén -1-et) adja
vissza. A bulk memory utasítások (memory.copy, memory.fill) gyors memcpy/memset megfelelők. A memória
nem zsugorítható, és a modulon belül nincs szemétgyűjtés: az allokátort a forrásnyelv futtatókörnyezete adja.

```wat
(module
  ;; 1 lap = 64 KiB; kezdetben 1 lap, legfeljebb 16 lap
  (memory (export "memory") 1 16)

  ;; Adatszegmens: példányosításkor a 16-os címre másolódik (null-terminált string)
  (data (i32.const 16) "config:v1\00")

  ;; i32 tömb összege: ptr = kezdőcím bájtban, len = elemszám
  (func (export "sum_i32") (param $ptr i32) (param $len i32) (result i32)
    (local $sum i32)
    (local $end i32)
    ;; end = ptr + len * 4 (shl 2 = szorzás 4-gyel)
    (local.set $end (i32.add (local.get $ptr) (i32.shl (local.get $len) (i32.const 2))))
    (block $done
      (loop $next
        (br_if $done (i32.ge_u (local.get $ptr) (local.get $end)))
        (local.set $sum (i32.add (local.get $sum) (i32.load (local.get $ptr))))
        (local.set $ptr (i32.add (local.get $ptr) (i32.const 4)))
        (br $next)))
    (local.get $sum))

  ;; Struktúra mezőinek elérése fix eltolással: { u8 flags; u32 id @4; f64 score @8 }
  (func (export "score_of") (param $rec i32) (result f64)
    (f64.load offset=8 align=8 (local.get $rec)))
  (func (export "set_id") (param $rec i32) (param $id i32)
    (i32.store offset=4 (local.get $rec) (local.get $id)))

  ;; Bővítés: a régi lapszámot adja vissza, sikertelenségnél -1-et
  (func (export "grow") (param $pages i32) (result i32)
    (memory.grow (local.get $pages)))

  ;; Bulk memory: memcpy és memset megfelelők
  (func (export "copy") (param $dst i32) (param $src i32) (param $n i32)
    (memory.copy (local.get $dst) (local.get $src) (local.get $n)))
  (func (export "zero") (param $dst i32) (param $n i32)
    (memory.fill (local.get $dst) (i32.const 0) (local.get $n)))
)
```

## Importok, exportok, táblák és globálok
<!-- q: Hogyan hívjon a WebAssembly modul JavaScript függvényt, és hogyan működik az indirekt hívás? -->
<!-- tags: import, export, table, call_indirect, funcref, global, start function, host functions -->

A modul csak azt érheti el, amit a gazdakörnyezet importként átad (függvény, memória, tábla, globál),
ezért a képességek pontosan szabályozhatók; az exportok a kifelé látható felületet adják. A tábla
függvényreferenciákat tárol, a call_indirect index alapján hív belőle, és futásidőben ellenőrzi a
típusegyezést; erre épülnek a függvénypointerek, a virtuális metódusok és a callbackek. A mutable
globál exportálható és importálható, a start függvény pedig példányosításkor automatikusan lefut. A
WAT-ban az importoknak meg kell előzniük a modul saját függvény-, tábla-, memória- és globáldefinícióit.

```wat
(module
  ;; IMPORTOK: a gazda (JS vagy WASI runtime) adja őket
  (import "env" "log_i32" (func $log (param i32)))
  (import "env" "memory" (memory 1))               ;; JS-ben létrehozott, közös memória
  (import "env" "base" (global $base i32))         ;; nem módosítható importált globál

  ;; Módosítható, exportált globál: hívásszámláló
  (global $calls (export "calls") (mut i32) (i32.const 0))

  ;; Függvénytábla az indirekt hívásokhoz
  (type $binop (func (param i32 i32) (result i32)))
  (table (export "ops") 2 funcref)
  (elem (i32.const 0) $add $mul)                   ;; 0 -> $add, 1 -> $mul
  (func $add (type $binop) (i32.add (local.get 0) (local.get 1)))
  (func $mul (type $binop) (i32.mul (local.get 0) (local.get 1)))

  ;; op = táblaindex; rossz index vagy típus -> trap
  (func (export "apply") (param $op i32) (param $a i32) (param $b i32) (result i32)
    (local $r i32)
    (global.set $calls (i32.add (global.get $calls) (i32.const 1)))
    (local.set $r
      (call_indirect (type $binop) (local.get $a) (local.get $b) (local.get $op)))
    (call $log (i32.add (local.get $r) (global.get $base)))   ;; JS függvény hívása
    (local.get $r))

  ;; Start függvény: példányosításkor egyszer lefut
  (func $init (call $log (i32.const -1)))
  (start $init)
)
```

## JavaScript API: betöltés, példányosítás, memória-nézetek
<!-- q: Hogyan töltsek be és hívjak meg egy WebAssembly modult JavaScriptből? -->
<!-- tags: javascript api, instantiateStreaming, WebAssembly.Memory, typed array, LinkError, RuntimeError, detached buffer -->

A WebAssembly.instantiateStreaming a letöltéssel párhuzamosan fordít, és egy lépésben ad Module-t és
Instance-t; ehhez a szervernek application/wasm Content-Type-pal kell küldenie a fájlt. Az import
objektum kulcsai pontosan a modul import-neveivel egyeznek, hiányzó import esetén LinkError keletkezik,
trap esetén RuntimeError. A memóriát TypedArray nézeteken keresztül olvasod és írod; a memory.grow után
a régi ArrayBuffer leválik (detached), ezért a nézeteket mindig frissen kell létrehozni. A lefordított
Module újrahasznosítható több példányhoz vagy workerekhez.

```javascript
// A memóriát a JS hozza létre, és a modul importálja (lásd az "Importok" szakaszt)
const memory = new WebAssembly.Memory({ initial: 1, maximum: 16 });

const imports = {
  env: {
    memory,
    base: new WebAssembly.Global({ value: 'i32', mutable: false }, 100),
    log_i32: (x) => console.log('wasm:', x),
  },
};

// Streaming fordítás + példányosítás (Content-Type: application/wasm kell)
const { instance, module } = await WebAssembly.instantiateStreaming(fetch('/ops.wasm'), imports);

const { apply, calls } = instance.exports;
console.log(apply(1, 6, 7));        // 42 (az 1-es táblaelem a $mul)
console.log(calls.value);           // exportált globál értéke: 1

// Memória-nézet: közvetlenül a lineáris memóriára mutat
const bytes = new TextEncoder().encode('alma');
new Uint8Array(memory.buffer).set(bytes, 1024);

// BUKTATÓ: grow után a régi buffer leválik, a régi nézetek 0 hosszúak lesznek
const before = new Uint8Array(memory.buffer);
memory.grow(1);
console.log(before.length);                         // 0 (detached)
const fresh = new Uint8Array(memory.buffer);         // mindig frissen kérd le
console.log(fresh.length);                          // 131072

// Ugyanaz a lefordított Module újra példányosítható (cache, worker)
const second = await WebAssembly.instantiate(module, imports);

// Hibatípusok: CompileError (rossz bináris), LinkError (import), RuntimeError (trap)
try {
  second.exports.apply(5, 1, 1);                    // nincs 5-ös táblaelem -> trap
} catch (e) {
  if (e instanceof WebAssembly.RuntimeError) console.warn('Trap:', e.message);
  else throw e;
}
```

## Stringek és tömbök átadása JS és Wasm között
<!-- q: Hogyan adjak át stringet vagy tömböt JavaScript és WebAssembly között? -->
<!-- tags: strings, utf-8, TextEncoder, TextDecoder, pointer, alloc, dealloc, abi, data exchange -->

A Wasm függvények csak számokat fogadnak és adnak vissza, ezért a stringek és tömbök a lineáris
memórián át, (mutató, hossz) párként utaznak: a JS a modul exportált allokátorával foglal helyet,
bemásolja a bájtokat, majd a hívás után felszabadítja. A stringet UTF-8-ra kell kódolni (TextEncoder),
és a hossz a bájtszám, nem a str.length. A memórianézetet minden hívás után újra kell létrehozni, mert a
hívás közben a memória nőhetett. A wasm-bindgen (Rust) és az Emscripten ezt a "ragasztókódot"
automatikusan generálja, kézzel csak alacsony szintű vagy nyelvfüggetlen ABI-nál kell megírni.

```javascript
// A modul (pl. Rust/C fordításból) exportálja: memory, alloc, dealloc, count_words, normalize
const { memory, alloc, dealloc, count_words, normalize } = instance.exports;
const enc = new TextEncoder();
const dec = new TextDecoder('utf-8');

// String átadása: kódolás -> foglalás -> másolás -> hívás -> felszabadítás
function withString(str, fn) {
  const bytes = enc.encode(str);                 // UTF-8: a hossz bájtban, nem str.length!
  const ptr = alloc(bytes.length);
  try {
    new Uint8Array(memory.buffer, ptr, bytes.length).set(bytes);
    return fn(ptr, bytes.length);
  } finally {
    dealloc(ptr, bytes.length);                  // különben memóriaszivárgás
  }
}
const words = withString('árvíztűrő tükörfúrógép és társai', (p, l) => count_words(p, l));

// Visszaadott string olvasása (ptr, len) alapján; a nézet a hívás UTÁN készül
function readString(ptr, len) {
  return dec.decode(new Uint8Array(memory.buffer, ptr, len));
}

// Float32 tömb: egy másolás be, helyben feldolgozás, egy másolás ki
function processSamples(samples /* Float32Array */) {
  const byteLen = samples.length * Float32Array.BYTES_PER_ELEMENT;
  const ptr = alloc(byteLen);                    // az allokátor 4 bájtra igazított címet ad
  try {
    new Float32Array(memory.buffer, ptr, samples.length).set(samples);
    normalize(ptr, samples.length);
    return new Float32Array(memory.buffer, ptr, samples.length).slice();   // másolat kifelé
  } finally {
    dealloc(ptr, byteLen);
  }
}
```

## Rust → WebAssembly wasm-bindgen-nel
<!-- q: Hogyan fordítsak Rust kódot WebAssemblyre, és hogyan hívjam meg JavaScriptből wasm-bindgen-nel? -->
<!-- tags: rust, wasm-bindgen, wasm-pack, cdylib, JsError, struct export, typed arrays -->

A wasm-bindgen a #[wasm_bindgen] attribútummal jelölt Rust függvényekhez és struktúrákhoz JS/TypeScript
ragasztókódot generál: a szeleteket TypedArray-ből másolja, a Stringet UTF-8-ként adja át, a struktúrákat
JS osztályként teszi elérhetővé, a Result<_, JsError> pedig JS kivétellé válik. A wasm-pack egy
paranccsal fordít, futtatja a wasm-bindgen-t és npm csomagot készít (--target web, bundler vagy nodejs).
Buktató: a Rust oldalon élő objektumot a JS szemétgyűjtő nem látja, ezért a .free() hívást nem szabad
elfelejteni (vagy a using / FinalizationRegistry megoldásra kell bízni).

```toml
[package]
name = "img-filters"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib", "rlib"]   # cdylib: .wasm kimenet; rlib: natív tesztekhez

[dependencies]
wasm-bindgen = "0.2"
```

```rust
use wasm_bindgen::prelude::*;

/// Szürkeárnyalatos szűrő RGBA pixelekre, helyben.
/// A &mut [u8] a JS Uint8Array tartalmát kapja, és a hívás végén vissza is másolódik.
#[wasm_bindgen]
pub fn grayscale(pixels: &mut [u8]) {
    for px in pixels.chunks_exact_mut(4) {
        // ITU-R BT.601 luma, egész aritmetikával
        let y = ((px[0] as u32 * 299 + px[1] as u32 * 587 + px[2] as u32 * 114) / 1000) as u8;
        px[0] = y;
        px[1] = y;
        px[2] = y;
    }
}

/// Állapotot tartó típus: JS-ben osztály lesz (new Histogram()).
#[wasm_bindgen]
pub struct Histogram {
    bins: [u32; 256],
}

#[wasm_bindgen]
impl Histogram {
    #[wasm_bindgen(constructor)]
    pub fn new() -> Histogram {
        Histogram { bins: [0; 256] }
    }

    /// RGBA pixelek első csatornájának hisztogramja (szürkeárnyalatos képen ez a luma)
    pub fn add_pixels(&mut self, pixels: &[u8]) {
        for px in pixels.chunks_exact(4) {
            self.bins[px[0] as usize] += 1;
        }
    }

    /// Vec<u32> -> JS oldalon Uint32Array (másolat)
    pub fn bins(&self) -> Vec<u32> {
        self.bins.to_vec()
    }

    /// Result<_, JsError> -> JS oldalon kivétel
    pub fn percentile(&self, p: f64) -> Result<u8, JsError> {
        if !(0.0..=100.0).contains(&p) {
            return Err(JsError::new("p értéke 0 és 100 közé kell essen"));
        }
        let total: u64 = self.bins.iter().map(|&b| b as u64).sum();
        let target = (total as f64 * p / 100.0).ceil() as u64;
        let mut acc = 0u64;
        for (i, &b) in self.bins.iter().enumerate() {
            acc += b as u64;
            if acc >= target {
                return Ok(i as u8);
            }
        }
        Ok(255)
    }
}
```

```javascript
// wasm-pack build --target web --release  ->  ./pkg/img_filters.js + .wasm + .d.ts
import init, { grayscale, Histogram } from './pkg/img_filters.js';

await init();                                          // betölti és példányosítja a .wasm-ot
const ctx = canvas.getContext('2d');
const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
const view = new Uint8Array(img.data.buffer);          // ugyanarra a pufferre mutat
grayscale(view);                                       // a visszamásolás a képet módosítja
ctx.putImageData(img, 0, 0);

const h = new Histogram();
try {
  h.add_pixels(view);
  console.log('medián fényesség:', h.percentile(50));
} finally {
  h.free();                                            // Rust oldali memória felszabadítása
}
```

## wasm-bindgen haladó: web-sys, async és closure-ök
<!-- q: Hogyan érjem el a böngésző API-kat és a Promise-okat Rustból WebAssemblyben? -->
<!-- tags: web-sys, js-sys, wasm-bindgen-futures, async, promise, closure, event listener, extern -->

A web-sys a böngésző API-k (DOM, fetch, Canvas, WebSocket) típusos Rust kötése, de minden használt típust
feature-ként engedélyezni kell a Cargo.toml-ban, különben nem fordul. A wasm-bindgen-futures a JS
Promise-t Rust Future-ré alakítja (JsFuture), az async exportált függvény pedig JS oldalon Promise-t ad
vissza. JS függvényt az extern "C" blokkban lehet importálni, Rust closure-t pedig a Closure típussal
lehet eseménykezelőként átadni. A Closure-t életben kell tartani, amíg a JS hívhatja: vagy eltárolod,
vagy a forget() szándékosan kiszivárogtatja, ami csak egyszer telepített kezelőknél elfogadható.

```toml
[dependencies]
wasm-bindgen = "0.2"
wasm-bindgen-futures = "0.4"
web-sys = { version = "0.3", features = ["Window", "Document", "Element", "EventTarget", "Request", "RequestInit", "Response"] }
```

```rust
use wasm_bindgen::prelude::*;
use wasm_bindgen_futures::JsFuture;
use web_sys::{Request, RequestInit, Response};

// JS függvény importálása Rustba
#[wasm_bindgen]
extern "C" {
    #[wasm_bindgen(js_namespace = console)]
    fn log(s: &str);
}

/// async fn -> JS Promise; a ? operátor a JsValue hibát Promise-elutasítássá alakítja
#[wasm_bindgen]
pub async fn fetch_json(url: String) -> Result<JsValue, JsValue> {
    let opts = RequestInit::new();
    opts.set_method("GET");
    let req = Request::new_with_str_and_init(&url, &opts)?;
    let window = web_sys::window().ok_or("nincs window objektum")?;
    let resp: Response = JsFuture::from(window.fetch_with_request(&req)).await?.dyn_into()?;
    if !resp.ok() {
        return Err(JsValue::from_str(&format!("HTTP {}", resp.status())));
    }
    let json = JsFuture::from(resp.json()?).await?;
    log(&format!("letöltve: {url}"));
    Ok(json)
}

/// Rust closure eseménykezelőként; az állapot (count) a closure-ben él
#[wasm_bindgen]
pub fn install_click_counter(id: &str) -> Result<(), JsValue> {
    let doc = web_sys::window().and_then(|w| w.document()).ok_or("nincs document")?;
    let el = doc.get_element_by_id(id).ok_or("nincs ilyen elem")?;
    let mut count = 0u32;
    let cb = Closure::<dyn FnMut()>::new(move || {
        count += 1;
        log(&format!("kattintás #{count}"));
    });
    el.add_event_listener_with_callback("click", cb.as_ref().unchecked_ref())?;
    cb.forget();   // életben tartás: egyszer telepített kezelőnél elfogadható
    Ok(())
}
```

## WASI: WebAssembly böngészőn kívül
<!-- q: Hogyan futtassak WebAssembly programot szerveren vagy parancssorban WASI-val? -->
<!-- tags: wasi, wasmtime, wasm32-wasip1, wasip2, component model, sandbox, capabilities, preopened dirs -->

A WASI szabványos rendszerinterfész (fájlok, órák, véletlenszám, környezeti változók, stdout), amellyel
ugyanaz a std-t használó program böngészőn kívül, sandboxban fut wasmtime-mal vagy más runtime-mal. A
biztonsági modell képesség-alapú: a program csak az indításkor kifejezetten megnyitott (preopened)
könyvtárakat éri el, hálózatot és más erőforrást csak engedéllyel. A wasm32-wasip1 a stabil, széles
körben támogatott cél, a wasip2 a Component Modelre épül (típusos interfészek WIT nyelven). Szálkezelés
és általános socket-elérés runtime-onként eltérő érettségű, ezt célplatformonként ellenőrizni kell.

```rust
// Közönséges std-s Rust program, amely wasm32-wasip1 célra is fordul
use std::env;
use std::fs;
use std::io::{self, BufRead, BufReader, Write};

fn main() -> io::Result<()> {
    // Csak a --dir kapcsolóval megnyitott könyvtárak érhetők el (sandbox)
    let path = env::args().nth(1).unwrap_or_else(|| "/data/input.csv".to_string());
    let file = fs::File::open(&path)?;

    let mut total = 0f64;
    let mut rows = 0usize;
    for line in BufReader::new(file).lines() {
        let line = line?;
        // második oszlop számként; a hibás sorokat kihagyjuk
        if let Some(v) = line.split(',').nth(1).and_then(|s| s.trim().parse::<f64>().ok()) {
            total += v;
            rows += 1;
        }
    }

    let out = format!("sorok: {rows}, összeg: {total:.2}\n");
    fs::write("/data/summary.txt", &out)?;      // csak a megnyitott könyvtárba írhat
    io::stdout().write_all(out.as_bytes())?;
    Ok(())
}
```

```bash
rustup target add wasm32-wasip1
cargo build --release --target wasm32-wasip1
wasmtime run --dir ./data::/data target/wasm32-wasip1/release/csv-sum.wasm /data/input.csv
```

## Teljesítmény: határátlépés, kötegelés, SIMD
<!-- q: Mitől lesz gyors vagy lassú a WebAssembly kód a JavaScripthez képest? -->
<!-- tags: performance, simd, simd128, boundary crossing, batching, allocation, vectorization, benchmark -->

A Wasm ott nyer, ahol hosszú, számításigényes ciklusok futnak kiszámítható típusokkal; egy jól JIT-elt JS
kód sokszor csak 1,5-2-szer lassabb, ezért mindig mérni kell. A legnagyobb hiba a sok apró hívás: minden
JS-Wasm határátlépésnek és főleg a string- vagy tömbmásolásnak ára van, ezért egy hívással egy egész
puffert dolgozz fel, ne elemenként. A 128 bites SIMD (simd128 feature) 4 f32 vagy 16 u8 értéket
dolgoz fel egyszerre, a forró ciklusban kerüld az allokációt, és használj újrahasznosított puffert,
amelyet a JS közvetlenül Float32Array nézettel tölt fel.

```rust
use wasm_bindgen::prelude::*;

// 1) Egy hívás az egész pufferre (nem pixelenként); a fordító ezt magától is vektorizálhatja
#[wasm_bindgen]
pub fn brighten(pixels: &mut [u8], delta: u8) {
    for v in pixels.iter_mut() {
        *v = v.saturating_add(delta);
    }
}

// 2) Kézi SIMD: RUSTFLAGS="-C target-feature=+simd128" fordítással érhető el
#[cfg(all(target_arch = "wasm32", target_feature = "simd128"))]
pub fn sum_f32_simd(data: &[f32]) -> f32 {
    use core::arch::wasm32::*;
    let mut acc = f32x4_splat(0.0);
    let chunks = data.chunks_exact(4);
    let rest = chunks.remainder();
    for c in chunks {
        // SAFETY: a szelet pontosan 4 f32 (16 bájt); a v128_load nem igényel igazítást
        let v = unsafe { v128_load(c.as_ptr() as *const v128) };
        acc = f32x4_add(acc, v);
    }
    f32x4_extract_lane::<0>(acc) + f32x4_extract_lane::<1>(acc)
        + f32x4_extract_lane::<2>(acc) + f32x4_extract_lane::<3>(acc)
        + rest.iter().sum::<f32>()
}

// 3) Újrahasznosított puffer: a JS közvetlenül ide ír, nincs másolás és allokáció hívásonként
#[wasm_bindgen]
pub struct Processor {
    scratch: Vec<f32>,
}

#[wasm_bindgen]
impl Processor {
    #[wasm_bindgen(constructor)]
    pub fn new(capacity: usize) -> Processor {
        Processor { scratch: Vec::with_capacity(capacity) }
    }

    /// Mutató a belső pufferre; JS: new Float32Array(memory.buffer, ptr, len)
    pub fn buffer_ptr(&mut self, len: usize) -> *mut f32 {
        self.scratch.resize(len, 0.0);
        self.scratch.as_mut_ptr()
    }

    pub fn mean(&self) -> f32 {
        if self.scratch.is_empty() {
            return 0.0;
        }
        self.scratch.iter().sum::<f32>() / self.scratch.len() as f32
    }
}
```

## Szálak: shared memory, Web Workerek és Atomics
<!-- q: Hogyan futtassak párhuzamos WebAssembly kódot több szálon a böngészőben? -->
<!-- tags: threads, shared memory, sharedarraybuffer, web workers, atomics, coop, coep, cross-origin isolation -->

A Wasm szálak Web Workerekből, közös (shared) lineáris memóriából és atomi utasításokból állnak: minden
worker ugyanazt a lefordított modult példányosítja ugyanazzal a shared memóriával. A SharedArrayBuffer
csak cross-origin isolated oldalon érhető el, ehhez a szervernek COOP: same-origin és COEP: require-corp
fejlécet kell küldenie. A shared memória a grow után sem válik le, de a fő szálon az Atomics.wait tilos
(blokkolná a felületet), ott Atomics.waitAsync vagy üzenetküldés használható. Rustban a
wasm-bindgen-rayon, C/C++-ban az Emscripten -pthread kapcsolója rejti el a részleteket.

```javascript
// main.js — a modulnak shared memóriát kell importálnia:
//   (import "env" "memory" (memory 32 256 shared))
if (!crossOriginIsolated) {
  throw new Error('COOP/COEP fejlécek hiányoznak, nincs SharedArrayBuffer');
}
const memory = new WebAssembly.Memory({ initial: 32, maximum: 256, shared: true });
const module = await WebAssembly.compileStreaming(fetch('/kernel.wasm'));

const threads = navigator.hardwareConcurrency || 4;
const done = new Int32Array(memory.buffer, 0, 1);       // közös "kész" számláló a 0-s címen

const workers = Array.from({ length: threads }, (_, id) => {
  const w = new Worker('/kernel-worker.js', { type: 'module' });
  w.postMessage({ module, memory, id, threads });        // a Module és a shared memória nem másolódik
  return w;
});

// A fő szálon nem blokkolunk: waitAsync addig vár, amíg mindenki végez
let finished;
while ((finished = Atomics.load(done, 0)) < threads) {
  await Atomics.waitAsync(done, 0, finished).value;
}
console.log('Minden szál végzett');
workers.forEach((w) => w.terminate());

// kernel-worker.js
self.onmessage = async ({ data: { module, memory, id, threads } }) => {
  const instance = await WebAssembly.instantiate(module, { env: { memory } });
  instance.exports.run_slice(id, threads);                // mindenki a saját szeletén dolgozik
  const done = new Int32Array(memory.buffer, 0, 1);
  Atomics.add(done, 0, 1);                                // atomi növelés
  Atomics.notify(done, 0);                                // a várakozók felébresztése
};
```

## Méretcsökkentés és hibakeresés
<!-- q: Hogyan csökkentsem a .wasm fájl méretét, és hogyan debugoljak WebAssembly kódot? -->
<!-- tags: wasm-opt, binary size, lto, opt-level, twiggy, debugging, dwarf, panic hook, wasm-tools -->

A .wasm mérete közvetlenül a betöltési időt befolyásolja: a release profilban az opt-level = "z" vagy "s",
az lto, a codegen-units = 1 és a panic = "abort" együtt gyakran a felére csökkenti, a Binaryen wasm-opt
-Oz pedig további 10-20%-ot vesz le. A twiggy megmutatja, mely függvények foglalják a legtöbb helyet
(tipikusan a formázó gépezet és a generikus monomorfizáció), a szervernek pedig Brotli/gzip tömörítéssel
kell kiszolgálnia a fájlt. Hibakereséshez a console_error_panic_hook a Rust pánik üzenetét a konzolba
írja az "unreachable" trap helyett, a DWARF debug információval pedig a Chrome DevTools forrásszinten lép.

```toml
[profile.release]
opt-level = "z"      # méretre optimalizál ("s" hasonló, "3" sebességre)
lto = true           # link-time optimization: halott kód eltávolítása crate-ek között
codegen-units = 1    # jobb optimalizálás, lassabb fordítás
panic = "abort"      # nincs unwinding kód
strip = true         # szimbólumok elhagyása

[dependencies]
wasm-bindgen = "0.2"
console_error_panic_hook = "0.1"
```

```rust
use wasm_bindgen::prelude::*;

/// A modul betöltésekor automatikusan lefut
#[wasm_bindgen(start)]
pub fn start() {
    // Fejlesztői buildben a pánik üzenete és helye a konzolba kerül
    #[cfg(debug_assertions)]
    console_error_panic_hook::set_once();
}
```

```bash
wasm-pack build --target web --release
wasm-opt -Oz --enable-bulk-memory --enable-sign-ext --enable-nontrapping-float-to-int -o pkg/app_bg.min.wasm pkg/app_bg.wasm
twiggy top -n 15 pkg/app_bg.wasm
wasm-tools validate pkg/app_bg.min.wasm
```
