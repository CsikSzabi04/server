# HTML és CSS
<!-- tech: html-css -->
<!-- aliases: html, css, html5, css3 -->

A HTML a weboldal szerkezetét és jelentését (szemantikáját) írja le, a CSS a megjelenését: elrendezést,
tipográfiát, színeket, animációt. A böngésző a HTML-ből DOM-ot, a CSS-ből CSSOM-ot épít, ezekből jön
létre a renderelési fa, majd a layout, a festés és a kompozitálás. A modern CSS (flexbox, grid, subgrid,
container queries, cascade layers, :has(), nesting, custom properties) ma már sok korábban JS-t vagy
preprocesszort igénylő feladatot natívan megold. A jó HTML egyben akadálymentesség és SEO is: a
szemantikus elemek a képernyőolvasóknak és a keresőknek is jelentést adnak. Buktatói a kaszkád és a
specificitás, a stacking context, a layout shift és az, hogy a böngészőtámogatást mindig ellenőrizni kell.

## Szemantikus HTML és landmark elemek
<!-- q: Hogyan építsek fel egy oldalt szemantikus HTML elemekkel div-ek helyett? -->
<!-- tags: semantic html, landmarks, header, main, nav, article, section, accessibility, headings -->

A szemantikus elemek (header, nav, main, article, section, aside, footer) jelentést hordoznak: a
képernyőolvasók landmarkként ugrálhatnak köztük, a keresők jobban értik a tartalmat, és a kód is
olvashatóbb. A címsorok (h1–h6) a dokumentum vázlatát adják, ezért ne ugorj szintet stílus miatt;
a méretet CSS-sel állítsd. Az article önállóan is értelmes tartalom, a section egy címmel ellátott
tematikus rész, a div pedig csak stílusozási konténer. A lang attribútum a helyes kiejtéshez és
elválasztáshoz kell, a skip link a billentyűzetes navigációt gyorsítja.

```html
<!doctype html>
<html lang="hu">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Termékek – Példa Bolt</title>
</head>
<body>
  <!-- Ugrólink: a billentyűzetes felhasználó átugorhatja a navigációt -->
  <a class="skip-link" href="#main">Ugrás a tartalomra</a>

  <header>
    <nav aria-label="Fő navigáció">
      <ul>
        <li><a href="/">Főoldal</a></li>
        <li><a href="/termekek" aria-current="page">Termékek</a></li>
        <li><a href="/kapcsolat">Kapcsolat</a></li>
      </ul>
    </nav>
  </header>

  <main id="main">
    <h1>Termékek</h1>  <!-- oldalanként egy h1, a szintek ne ugorjanak -->
    <article>
      <h2>Mechanikus billentyűzet</h2>
      <p>Frissítve: <time datetime="2026-03-14">2026. március 14.</time></p>
      <figure>
        <img src="/img/kb.jpg" alt="Fekete mechanikus billentyűzet RGB világítással"
             width="800" height="450">
        <figcaption>A 2026-os modell</figcaption>
      </figure>
      <section aria-labelledby="specs-title">
        <h3 id="specs-title">Specifikáció</h3>
        <dl>
          <dt>Kapcsoló</dt><dd>Lineáris</dd>
          <dt>Csatlakozás</dt><dd>USB-C, Bluetooth</dd>
        </dl>
      </section>
    </article>
    <aside aria-label="Kapcsolódó termékek">
      <h2>Ezek is érdekelhetnek</h2>
    </aside>
  </main>

  <footer>
    <address>Kapcsolat: <a href="mailto:info@example.com">info@example.com</a></address>
  </footer>
</body>
</html>
```

## Akadálymentesség és ARIA
<!-- q: Hogyan tegyem akadálymentessé az interaktív elemeket, és mikor használjak ARIA attribútumokat? -->
<!-- tags: accessibility, a11y, aria, aria-expanded, aria-live, focus-visible, screen reader, wcag -->

Az ARIA első szabálya: ha van natív elem (button, details, dialog, input), azt használd, mert
billentyűzetkezelést, fókuszt és szerepet ingyen ad; egy kattintható div-hez mindezt kézzel kellene
pótolni. Az ARIA csak a segédtechnológiának szóló információt módosítja (szerep, állapot, név), a
viselkedést nem, ezért az aria-expanded értékét a JS-nek kell frissítenie. Minden interaktív elemnek
legyen hozzáférhető neve (látható szöveg vagy aria-label), a dinamikus változásokat élő régió
(role="status" / aria-live) jelentse be. A fókuszjelzést soha ne vedd el pótlás nélkül; a
:focus-visible csak billentyűzetes navigációnál mutatja.

```html
<!-- Kinyitható szakasz (disclosure): natív gomb + állapot ARIA-val -->
<button type="button" class="disclosure" aria-expanded="false" aria-controls="faq-1">
  Mennyi a szállítási idő?
</button>
<div id="faq-1" hidden>
  <p>Raktári termékeknél 1–2 munkanap.</p>
</div>

<!-- Élő régió: a képernyőolvasó fókuszváltás nélkül felolvassa a változást -->
<div id="cart-status" role="status" aria-live="polite"></div>

<!-- Csak ikonos gomb: kötelező a hozzáférhető név; az ikon rejtett -->
<button type="button" id="add-to-cart" aria-label="Kosárba teszem">
  <svg aria-hidden="true" focusable="false" width="20" height="20"><use href="#icon-cart"></use></svg>
</button>

<style>
  /* Fókuszjelzés billentyűzetes navigációnál; outline: none csak pótlással */
  :focus-visible { outline: 3px solid #1a73e8; outline-offset: 2px; }

  /* Vizuálisan rejtett, de képernyőolvasónak elérhető szöveg */
  .visually-hidden {
    position: absolute; width: 1px; height: 1px; overflow: hidden;
    clip-path: inset(50%); white-space: nowrap;
  }
</style>

<script>
  document.querySelectorAll('.disclosure').forEach((btn) => {
    btn.addEventListener('click', () => {
      const open = btn.getAttribute('aria-expanded') === 'true';
      btn.setAttribute('aria-expanded', String(!open));   // állapot a segédtechnológiának
      document.getElementById(btn.getAttribute('aria-controls')).hidden = open;
    });
  });
  document.getElementById('add-to-cart').addEventListener('click', () => {
    // A role="status" tartalma változik -> felolvassa: "1 termék a kosárban"
    document.getElementById('cart-status').textContent = '1 termék a kosárban';
  });
</script>
```

## Űrlapok és natív validáció
<!-- q: Hogyan validáljak egy HTML űrlapot natívan, akadálymentes hibaüzenetekkel? -->
<!-- tags: forms, validation, constraint validation api, required, pattern, user-invalid, autocomplete, label -->

A HTML beépített validációja (required, type="email", pattern, minlength) és a Constraint Validation
API (input.validity) a legtöbb kliensoldali ellenőrzést JS-könyvtár nélkül megoldja. Minden mezőhöz
tartozzon label (for/id párossal), a súgó- és hibaszöveget aria-describedby kösse a mezőhöz, és az
autocomplete, inputmode attribútumok gyorsítják a mobilos kitöltést. A :user-invalid csak a felhasználó
interakciója után jelez, így betöltéskor nem piros az üres űrlap. A kliensoldali validáció csak
kényelmi funkció: a szervernek mindig újra kell ellenőriznie az adatot.

```html
<!-- novalidate: a natív buborékok helyett saját, akadálymentes hibaüzenetek -->
<form id="signup" novalidate>
  <div class="field">
    <label for="email">E-mail</label>
    <input id="email" name="email" type="email" required autocomplete="email"
           aria-describedby="email-err">
    <p id="email-err" class="error" aria-live="polite"></p>
  </div>
  <div class="field">
    <label for="zip">Irányítószám</label>
    <input id="zip" name="zip" inputmode="numeric" pattern="[1-9][0-9]{3}" required
           aria-describedby="zip-hint zip-err">
    <p id="zip-hint" class="hint">4 számjegy, pl. 6000</p>
    <p id="zip-err" class="error" aria-live="polite"></p>
  </div>
  <div class="field">
    <label for="pw">Jelszó (min. 12 karakter)</label>
    <input id="pw" name="pw" type="password" minlength="12" required
           autocomplete="new-password" aria-describedby="pw-err">
    <p id="pw-err" class="error" aria-live="polite"></p>
  </div>
  <fieldset>
    <legend>Hírlevél</legend>
    <label><input type="radio" name="news" value="weekly" checked> Heti</label>
    <label><input type="radio" name="news" value="none"> Nem kérek</label>
  </fieldset>
  <button type="submit">Regisztrálok</button>
</form>

<style>
  input:user-invalid { border-color: #c62828; }   /* csak interakció után */
  .error { color: #c62828; min-height: 1.2em; }
</style>

<script>
  const form = document.getElementById('signup');
  const messages = {
    valueMissing: 'Kötelező mező.',
    typeMismatch: 'Érvénytelen formátum.',
    patternMismatch: 'Nem megfelelő formátum.',
    tooShort: 'Túl rövid.',
  };
  function check(input) {
    // validity: ValidityState objektum, minden hibaokhoz külön logikai mezővel
    const key = Object.keys(messages).find((k) => input.validity[k]);
    input.setAttribute('aria-invalid', key ? 'true' : 'false');
    document.getElementById(input.id + '-err').textContent = key ? messages[key] : '';
    return !key;
  }
  form.addEventListener('submit', (e) => {
    const results = [...form.querySelectorAll('input[required]:not([type="radio"])')].map(check);
    if (results.includes(false)) {
      e.preventDefault();
      form.querySelector('[aria-invalid="true"]').focus();   // fókusz az első hibás mezőre
    }
  });
</script>
```

## Reszponzív képek: srcset, sizes, picture
<!-- q: Hogyan szolgáljak ki képernyőmérethez illő képeket layout shift nélkül? -->
<!-- tags: responsive images, srcset, sizes, picture, avif, webp, lazy loading, cls, lcp, fetchpriority -->

A srcset w-leírókkal több méretet kínál, a sizes megmondja, mekkora helyet foglal a kép a layoutban, és
ebből a böngésző a kijelző pixelsűrűségét is figyelembe véve választ; a picture elem formátumváltásra
(AVIF, WebP, JPEG) és eltérő kivágásra (art direction) való. A width és height attribútum az arányt adja
meg, így a böngésző letöltés előtt helyet foglal, és nincs layout shift (CLS). A loading="lazy" a
hajtás alatti képekhez jó, de a fő (LCP) képet soha ne tedd lazy-vé, inkább fetchpriority="high"-t
kapjon. A dekoratív kép alt="" értéket kap, a tartalmi kép tömör, informatív leírást.

```html
<!-- LCP (fő) kép: nem lazy, magas prioritás; width/height -> nincs layout shift -->
<img
  src="/img/hero-800.jpg"
  srcset="/img/hero-400.jpg 400w, /img/hero-800.jpg 800w, /img/hero-1600.jpg 1600w"
  sizes="(min-width: 1024px) 50vw, 100vw"
  width="1600" height="900"
  alt="Csapat a műhelyben egy prototípus körül"
  fetchpriority="high">

<!-- picture: art direction mobilra + modern formátumok tartalékkal -->
<picture>
  <source media="(max-width: 600px)" srcset="/img/banner-mobile.avif" type="image/avif">
  <source srcset="/img/banner.avif" type="image/avif">
  <source srcset="/img/banner.webp" type="image/webp">
  <img src="/img/banner.jpg" alt="Nyári akció: 20% kedvezmény" width="1200" height="400"
       loading="lazy" decoding="async">
</picture>

<!-- Fix megjelenítési méret: x-leírók a pixelsűrűséghez; alt="" = dekoratív -->
<img src="/img/avatar-64.png" srcset="/img/avatar-64.png 1x, /img/avatar-128.png 2x"
     width="64" height="64" alt="" loading="lazy">

<style>
  img { max-width: 100%; height: auto; }                      /* arányt tartva zsugorodik */
  .card img { aspect-ratio: 4 / 3; object-fit: cover; }       /* egységes kártyaképek */
</style>
```

## Flexbox elrendezés
<!-- q: Hogyan használjam a flexboxot egydimenziós elrendezésekhez, és miért lóg ki a tartalom? -->
<!-- tags: flexbox, flex, justify-content, align-items, gap, flex-grow, flex-basis, min-width -->

A flexbox egydimenziós elrendezés: az elemeket egy főtengely mentén (sor vagy oszlop) osztja el, a
justify-content a főtengelyen, az align-items a kereszttengelyen igazít, a gap pedig margók nélküli
térközt ad. A flex: grow shrink basis rövidítéssel szabályozható, hogyan osztoznak az elemek a helyen;
a margin-top: auto egy elemet a konténer végére tol. A leggyakoribb buktató, hogy a flex elem
alapértelmezett min-width: auto értéke miatt nem zsugorodik a tartalma alá, így a hosszú szöveg vagy
kódblokk kilóg; ilyenkor min-width: 0 kell. Az order csak vizuálisan rendez át, a fókusz- és
olvasási sorrendet nem.

```css
/* Navigációs sáv: logó balra, menü jobbra, függőlegesen középen */
.navbar {
  display: flex;
  align-items: center;              /* kereszttengely */
  justify-content: space-between;   /* főtengely */
  gap: 1rem;
  flex-wrap: wrap;
}

/* Kártyasor: min. 220px széles elemek, egyenlően nőnek, utána tördelnek */
.cards {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
}
.cards > .card {
  flex: 1 1 220px;                  /* grow shrink basis */
  display: flex;
  flex-direction: column;
}
.card .card-body { flex: 1; }               /* kitölti a maradék helyet */
.card .card-actions { margin-top: auto; }   /* a gomb mindig a kártya alján */

/* Chat sor: fix avatar + rugalmas üzenet. min-width: 0 nélkül a hosszú URL kilógna! */
.chat-row { display: flex; gap: .5rem; align-items: flex-start; }
.chat-row .avatar { flex: 0 0 40px; }       /* nem nő, nem zsugorodik */
.chat-row .message { flex: 1; min-width: 0; overflow-wrap: anywhere; }

/* Keresőmező + gomb egy sorban */
.search { display: flex; }
.search input { flex: 1; min-width: 0; }
.search button { flex: none; }

/* Az order csak vizuális: a Tab-sorrend a DOM-sorrend marad (akadálymentesség!) */
.layout.sidebar-first .sidebar { order: -1; }
```

## CSS Grid elrendezés
<!-- q: Hogyan készítsek kétdimenziós, reszponzív oldalelrendezést CSS Griddel? -->
<!-- tags: css grid, grid-template-areas, auto-fit, minmax, fr, place-items, layout -->

A grid kétdimenziós elrendezés: sorokat és oszlopokat egyszerre kezel, ezért oldalvázhoz és rácsos
listákhoz ideális, míg a flexbox egy sor elemeinek elosztására. A grid-template-areas névvel ellátott
területekkel olvashatóvá teszi az elrendezést, a repeat(auto-fit, minmax(...)) pedig media query nélkül
reszponzív kártyarácsot ad. Az fr egység a maradék helyet osztja fel; a minmax(0, 1fr) megakadályozza,
hogy egy széles tartalom szétfeszítse az oszlopot. A grid-auto-flow: dense betömi a lyukakat, de a
vizuális sorrend eltérhet a DOM-sorrendtől, ami a billentyűzetes navigációt zavarja.

```css
/* Oldalváz: mobilon egy oszlop, széles képernyőn oldalsáv + tartalom */
.page {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: auto 1fr auto auto;
  grid-template-areas:
    "header"
    "main"
    "aside"
    "footer";
  gap: 1rem;
  min-height: 100dvh;               /* dinamikus viewport: mobil címsorral is pontos */
}
@media (min-width: 900px) {
  .page {
    grid-template-columns: 240px minmax(0, 1fr);
    grid-template-rows: auto 1fr auto;
    grid-template-areas:
      "header header"
      "aside  main"
      "footer footer";
  }
}
.page > header { grid-area: header; }
.page > main   { grid-area: main; }
.page > aside  { grid-area: aside; }
.page > footer { grid-area: footer; }

/* Reszponzív kártyarács media query nélkül; a min() miatt keskeny kijelzőn sem lóg ki */
.gallery {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr));
  gap: 1rem;
}
.gallery .featured { grid-column: span 2; grid-row: span 2; }   /* kiemelt elem */
.gallery.dense { grid-auto-flow: dense; }                       /* lyukak betömése */

/* Középre igazítás egy sorban */
.center { display: grid; place-items: center; }

/* Rétegezés: kép és felirat ugyanabban a cellában */
.hero { display: grid; }
.hero > * { grid-area: 1 / 1; }
.hero .caption {
  align-self: end;
  padding: 1rem;
  background: rgb(0 0 0 / .55);
  color: #fff;
}
```

## Subgrid: igazítás egymásba ágyazott rácsok között
<!-- q: Hogyan igazítsam egy vonalba a kártyák belső részeit (cím, szöveg, gomb) különböző tartalomhosszaknál? -->
<!-- tags: subgrid, css grid, alignment, card layout, nested grid, form layout -->

Egymás melletti kártyáknál gyakori gond, hogy a különböző hosszú címek miatt a szövegek és gombok nem
esnek egy vonalba, mert minden kártya saját, független rácsot használ. A subgrid-del a gyerek rács a
szülő sorait vagy oszlopait örökli, így a sorok magasságát az összes kártya legnagyobb tartalma határozza
meg. Ehhez a kártyának annyi szülősort kell foglalnia (grid-row: span N), ahány részből áll. Ma minden
modern böngésző támogatja, régiekhez az @supports adhat flexboxos tartalékot.

```css
/* Minden kártya 3 szülősort foglal (cím, szöveg, akciók), és ezeket örökli */
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr));
  gap: 1rem 1.5rem;
}
.card {
  display: grid;
  grid-row: span 3;                 /* 3 sor a szülő rácsból */
  grid-template-rows: subgrid;      /* a gyerekek ezekbe a sorokba kerülnek */
  gap: .5rem;                       /* a subgrid saját gap-et adhat */
  padding: 1rem;
  border: 1px solid var(--border, #ddd);
  border-radius: .5rem;
}
.card h3       { margin: 0; align-self: end; }
.card p        { margin: 0; }
.card .actions { align-self: end; }

/* Űrlap: a címkék és a mezők minden sorban ugyanabba az oszlopba esnek */
.form-grid {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: .75rem 1rem;
}
.form-grid .row {
  display: grid;
  grid-column: 1 / -1;              /* teljes szélesség */
  grid-template-columns: subgrid;   /* a szülő két oszlopát örökli */
}

/* Tartalék subgrid nélküli böngészőkre */
@supports not (grid-template-rows: subgrid) {
  .card { display: flex; flex-direction: column; }
  .card .actions { margin-top: auto; }
}
```

## Container queries
<!-- q: Hogyan reagáljon egy komponens a saját konténere méretére a viewport helyett? -->
<!-- tags: container queries, container-type, cqi, responsive components, style queries -->

A media query a teljes viewporthoz igazodik, ezért ugyanaz a kártya rosszul nézhet ki egy keskeny
oldalsávban egy széles képernyőn. A container query (@container) a legközelebbi, container-type-pal
megjelölt ős méretét kérdezi le, így a komponens bárhová tehető és mindenhol jól rendeződik. A cqi/cqw
egységek a konténer méretéhez viszonyítanak, ami folyékony tipográfiához hasznos. Buktató: a
container-type: inline-size elem szélessége nem függhet a tartalmától (size containment), ezért
zsugorodó flex elemként vagy inline-block-ként 0 szélesre eshet össze.

```css
/* A konténer: a szélessége lekérdezhető, a magassága nem */
.card-wrapper {
  container-type: inline-size;
  container-name: card;
}

.product-card {
  display: grid;
  gap: .75rem;
}
.product-card img { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; }

/* Ha a KONTÉNER legalább 480px széles: kép balra, szöveg jobbra */
@container card (min-width: 480px) {
  .product-card {
    grid-template-columns: 200px 1fr;
    align-items: start;
  }
}
/* Még szélesebb konténerben az ár is külön oszlopba kerül */
@container card (min-width: 760px) {
  .product-card { grid-template-columns: 240px 1fr auto; }
}

/* cqi: a konténer inline méretének 1%-a -> a cím a kártyával együtt skálázódik */
.product-card h3 {
  font-size: clamp(1rem, 4cqi, 1.75rem);
}

/* Style query: egy custom property értékére reagál (minden elem stíluskonténer) */
.sidebar { --density: compact; }
@container style(--density: compact) {
  .product-card { gap: .25rem; font-size: .9rem; }
}
```

## Custom properties, témázás és sötét mód
<!-- q: Hogyan készítsek témázható felületet CSS változókkal és sötét móddal? -->
<!-- tags: custom properties, css variables, theming, dark mode, prefers-color-scheme, color-scheme, color-mix, property -->

A custom property (--név) futás közben változtatható, öröklődő érték, ezért design tokenekre (szín,
térköz, lekerekítés) és komponensváltozatokra ideális: egy változót felülírva az egész alfa frissül. A
sötét mód alapja a prefers-color-scheme média-lekérdezés, a kézi választást pedig egy data-theme
attribútum írja felül; a color-scheme tulajdonság az űrlapelemeket és a görgetősávot is átszínezi. A
var() második argumentuma tartalék érték, a color-mix() pedig származtatott színeket ad. Az @property
típust ad a változónak, így az animálható lesz; típus nélkül a böngésző csak szövegként cseréli.

```css
:root {
  color-scheme: light dark;              /* natív vezérlők is igazodnak */
  --bg: #ffffff;
  --fg: #1d1d1f;
  --muted: #6e6e73;
  --accent: #0a66c2;
  --radius: .5rem;
  --space: clamp(.75rem, 2vw, 1.25rem);  /* folyékony térköz */
}
/* Rendszer szerinti sötét mód, ha a felhasználó nem választott világosat */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #111214; --fg: #ececf1; --muted: #a1a1aa; --accent: #6cb4ff;
  }
}
/* Kézi választás (a JS állítja a data-theme attribútumot) */
:root[data-theme="dark"] {
  --bg: #111214; --fg: #ececf1; --muted: #a1a1aa; --accent: #6cb4ff;
}

body { background: var(--bg); color: var(--fg); }

.button {
  background: var(--accent);
  color: var(--btn-fg, #fff);            /* második argumentum: tartalék érték */
  border-radius: var(--radius);
  padding: calc(var(--space) / 2) var(--space);
}
.button.danger { --accent: #c62828; }    /* változat: csak a tokent írjuk felül */
.button:hover  { background: color-mix(in oklab, var(--accent) 85%, black); }

/* Típusos custom property: így animálható (pl. forgó színátmenet) */
@property --angle {
  syntax: '<angle>';
  initial-value: 0deg;
  inherits: false;
}
.ring {
  background: conic-gradient(from var(--angle), var(--accent), transparent);
  animation: spin 1.2s linear infinite;
}
@keyframes spin { to { --angle: 360deg; } }
```

```javascript
// Témaváltó; a villanás elkerüléséhez a beállítást inline <script>-ben, a <head>-ben alkalmazd
const root = document.documentElement;
try {
  const saved = localStorage.getItem('theme');          // 'light' | 'dark' | null
  if (saved) root.dataset.theme = saved;
} catch { /* privát mód: tárhely nélkül a rendszerbeállítás érvényes */ }

export function toggleTheme() {
  const systemDark = matchMedia('(prefers-color-scheme: dark)').matches;
  const isDark = root.dataset.theme ? root.dataset.theme === 'dark' : systemDark;
  root.dataset.theme = isDark ? 'light' : 'dark';
  try { localStorage.setItem('theme', root.dataset.theme); } catch { /* nem kritikus */ }
}
```

## Cascade layers (@layer) és specificitás
<!-- q: Hogyan kezeljem a CSS specificitási háborúkat cascade layerekkel? -->
<!-- tags: cascade layers, layer, specificity, cascade, where, important, css architecture -->

A kaszkád eddig a specificitáson és a forrássorrenden múlt, ezért egy külső könyvtár erős szelektorai
ellen gyakran !important-tel kellett harcolni. A @layer rétegekbe sorolja a stílusokat, és a később
deklarált réteg nyer, függetlenül a szelektorok specificitásától; a réteg nélküli stílus pedig minden
réteges normál stílust felülír. A rétegsorrendet egyszer, a fájl elején érdemes deklarálni, a külső CSS
pedig @import ... layer()-rel tehető alacsony rétegbe. Buktató: !important esetén a sorrend megfordul,
ott a korábbi réteg nyer.

```css
/* Sorrend egyszer, elöl: a későbbi réteg nyer */
@layer reset, base, vendor, components, utilities;

/* Külső könyvtár a vendor rétegbe (az @import-nak minden szabály előtt kell állnia) */
@import url("vendor/datepicker.css") layer(vendor);

@layer reset {
  *, *::before, *::after { box-sizing: border-box; }
  body { margin: 0; }
}

@layer base {
  a { color: var(--accent, #0a66c2); }
  /* magas specificitás, de alacsony réteg -> a components réteg felülírja */
  main article p a:not(.button) { text-decoration: underline; }
  /* :where() = 0 specificitás: könnyen felülírható alapértelmezés */
  :where(ul, ol)[role="list"] { list-style: none; padding: 0; }
}

@layer components {
  /* egyetlen osztály, mégis nyer a base fenti, sokkal specifikusabb szabálya ellen */
  .button { color: white; text-decoration: none; }
  .card { padding: 1rem; border-radius: .5rem; }
}

@layer utilities {
  .hidden { display: none; }
  .mt-0   { margin-top: 0; }
}

/* Réteg nélküli stílus: minden réteges NORMÁL stílust felülír.
   Buktató: ha egy elem .legacy-banner és .hidden is, akkor LÁTSZIK, mert ez nyer. */
.legacy-banner { display: block; }

/* Beágyazott réteg: components.forms a components-en belül rendeződik */
@layer components.forms {
  input { font: inherit; }
}
```

## :has() és modern szelektorok
<!-- q: Hogyan stílusozzak egy elemet a gyerekei vagy testvérei állapota alapján CSS-ben? -->
<!-- tags: has selector, parent selector, is, where, css nesting, relational selector -->

A :has() relációs pszeudo-osztály ("szülőszelektor") lehetővé teszi, hogy egy elem stílusa a
leszármazottaitól vagy a következő testvéreitől függjön, amihez korábban JS kellett. Használható
űrlapállapot jelzésére, elrendezés váltására a tartalom alapján, mennyiségi lekérdezésekre vagy
"előző testvér" kijelölésére. Az :is() csoportosít és a legspecifikusabb argumentum specificitását
veszi át, a :where() ugyanígy működik, de nulla specificitással. A body:has(...) típusú, nagy DOM-ot
érintő szabályok minden változásnál újraértékelést okozhatnak, ezért szűk hatókörrel használd.

```css
/* Kártya, amelynek közvetlen gyereke kép -> két oszlopos elrendezés */
.card:has(> img) { display: grid; grid-template-columns: 120px 1fr; gap: 1rem; }

/* Mező címkéje piros, ha a benne lévő input érvénytelen (felhasználói interakció után) */
.field:has(input:user-invalid) label { color: #c62828; }
.field:has(input:focus-visible) { outline: 2px solid var(--accent, #0a66c2); }

/* Kijelölt jelölőnégyzetű táblázatsor kiemelése JS nélkül */
tr:has(input[type="checkbox"]:checked) {
  background: color-mix(in srgb, var(--accent, #0a66c2) 12%, transparent);
}

/* Görgetés tiltása, amíg nyitott modális dialógus van */
html:has(dialog[open]:modal) { overflow: hidden; }

/* Mennyiségi lekérdezés: legalább 5 elemű lista két oszlopba tördel */
ul:has(> li:nth-child(5)) { columns: 2; }

/* "Előző testvér": a hover-elt csillag ELŐTTI csillagok is kiemelődnek */
.rating span:has(~ span:hover) { color: gold; }

/* :is() — rövidebb szelektorlista */
:is(h1, h2, h3):hover > a.anchor { visibility: visible; }

/* :where() — 0 specificitás, könnyen felülírható tipográfiai alap */
:where(.prose) :where(h2, h3) { margin-block: 1.5em .5em; }

/* Natív CSS nesting */
.menu {
  display: flex;
  gap: .5rem;
  & a { padding: .5rem; }
  & a:hover { text-decoration: underline; }
  &:has(a[aria-current="page"]) { border-bottom: 2px solid var(--accent, #0a66c2); }
}
```

## Animációk és átmenetek
<!-- q: Hogyan készítsek teljesítménybarát CSS animációkat és átmeneteket? -->
<!-- tags: transition, animation, keyframes, starting-style, scroll-driven animation, prefers-reduced-motion, performance -->

A transition két állapot (például hover) közötti váltást animál, a @keyframes animáció többlépéses és
ismételhető. Csak a transform és az opacity animálása olcsó, mert ezeket a kompozitor a GPU-n végzi; a
width, top vagy margin animálása minden képkockán layoutot és újrafestést okoz. A @starting-style és az
allow-discrete átmenet lehetővé teszi a display: none állapotból való beúsztatást, a scroll-driven
animáció (animation-timeline) pedig JS nélkül köti az animációt a görgetéshez. A prefers-reduced-motion
beállítást mindig tartsd tiszteletben, mert a mozgás egyeseknél rosszullétet okoz.

```css
/* Átmenet: csak transform és háttérszín, rövid időtartammal */
.button { transition: transform 150ms ease-out, background-color 150ms ease-out; }
.button:hover  { transform: translateY(-2px); }
.button:active { transform: translateY(0) scale(.98); }

/* Keyframe animáció: értesítés beúszik */
@keyframes toast-in {
  from { opacity: 0; transform: translateY(1rem); }
  to   { opacity: 1; transform: none; }
}
.toast { animation: toast-in 250ms cubic-bezier(.2, .8, .2, 1) both; }

/* Skeleton betöltésjelző */
@keyframes shimmer { to { background-position: -200% 0; } }
.skeleton {
  background: linear-gradient(90deg, #eee 25%, #f5f5f5 50%, #eee 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s linear infinite;
}

/* Popover be- és kiúsztatása display: none-ból */
.menu-panel {
  transition: opacity 200ms, transform 200ms,
              display 200ms allow-discrete, overlay 200ms allow-discrete;
}
.menu-panel:not(:popover-open) { opacity: 0; transform: scale(.96); }
@starting-style {
  .menu-panel:popover-open { opacity: 0; transform: scale(.96); }
}

/* Görgetéshez kötött olvasási folyamatjelző JS nélkül */
.progress {
  position: fixed; inset: 0 0 auto 0; height: 4px;
  background: var(--accent, #0a66c2);
  transform-origin: left;
  animation: grow linear both;
  animation-timeline: scroll(root);
}
@keyframes grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }

/* Csökkentett mozgás: gyakorlatilag kikapcsoljuk az animációkat */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
    scroll-behavior: auto !important;
  }
}
```

## Renderelési teljesítmény: critical CSS, preload, content-visibility
<!-- q: Hogyan gyorsítsam fel az oldal első megjelenését CSS és HTML szinten? -->
<!-- tags: performance, critical css, preload, preconnect, content-visibility, font-display, render blocking, core web vitals -->

A külső CSS render-blokkoló: amíg le nem töltődik, a böngésző nem fest, ezért a hajtás feletti
(above-the-fold) kritikus stílusokat érdemes inline beágyazni, a teljes CSS-t pedig nem blokkolóan
betölteni. A preload a később felfedezett, de kritikus erőforrásokat (font, LCP kép) korán kéri le, a
preconnect a külső domain kapcsolatát készíti elő. A content-visibility: auto a képernyőn kívüli
szekciók layoutját és festését kihagyja, a contain-intrinsic-size pedig becsült méretet ad, hogy a
görgetősáv ne ugráljon. A font-display: swap megakadályozza a láthatatlan szöveget fontbetöltés közben.

```html
<head>
  <!-- 1) Kritikus CSS inline: az első festéshez nem kell külön kérés -->
  <style>
    body { margin: 0; font-family: system-ui, sans-serif; }
    .hero { min-height: 60vh; display: grid; place-items: center; }
  </style>

  <!-- 2) A teljes CSS nem blokkoló betöltése, JS nélküli tartalékkal -->
  <link rel="preload" href="/css/main.css" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="stylesheet" href="/css/main.css"></noscript>

  <!-- 3) Kritikus erőforrások korai kérése (fontnál a crossorigin kötelező!) -->
  <link rel="preload" href="/fonts/inter-var.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="preconnect" href="https://cdn.example.com">

  <!-- 4) A szkript ne blokkolja a HTML elemzését -->
  <script src="/js/app.js" defer></script>
</head>
```

```css
@font-face {
  font-family: "Inter";
  src: url("/fonts/inter-var.woff2") format("woff2");
  font-weight: 100 900;
  font-display: swap;                  /* tartalék fonttal azonnal látszik a szöveg */
}

/* Hosszú lista: a képernyőn kívüli elemek renderelése elhalasztva */
.comment-list > article {
  content-visibility: auto;
  contain-intrinsic-size: auto 300px;  /* becsült magasság, a böngésző megjegyzi a valósat */
}

/* A widget belső változása nem okoz teljes oldalas layoutot */
.widget { contain: layout paint; }

/* will-change csak célzottan és ideiglenesen: mindenre téve memóriát pazarol */
.drawer.is-animating { will-change: transform; }
```

## SEO meta adatok és strukturált adat
<!-- q: Milyen meta tageket és strukturált adatot tegyek egy oldalra a keresőoptimalizáláshoz? -->
<!-- tags: seo, meta description, canonical, open graph, json-ld, schema.org, hreflang, robots -->

A title és a meta description jelenik meg a találati listában, ezért legyen egyedi és tömör minden
oldalon (kb. 50–60, illetve 150–160 karakter). A canonical link összevonja a duplikált URL-eket
(szűrőparaméterek, UTM kódok), a hreflang a nyelvi változatokat köti össze, a robots meta pedig az
indexelést szabályozza. Az Open Graph tagek a közösségi megosztás előnézetét adják, a JSON-LD
strukturált adat (schema.org) pedig rich resultot (ár, értékelés, készlet) tehet lehetővé. A meta
tagek mellett a gyors betöltés, a szemantikus címsorok és a beszédes alt szövegek is számítanak.

```html
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mechanikus billentyűzetek – Példa Bolt</title>
  <meta name="description"
        content="Mechanikus billentyűzetek lineáris és taktilis kapcsolókkal, gyors szállítással.">

  <!-- Kanonikus URL és nyelvi változatok -->
  <link rel="canonical" href="https://www.example.com/billentyuzetek">
  <link rel="alternate" hreflang="hu" href="https://www.example.com/billentyuzetek">
  <link rel="alternate" hreflang="en" href="https://www.example.com/en/keyboards">
  <link rel="alternate" hreflang="x-default" href="https://www.example.com/en/keyboards">

  <!-- Indexelés: belső keresési találatoldalon pl. "noindex, follow" -->
  <meta name="robots" content="index, follow, max-image-preview:large">

  <!-- Open Graph: megosztási előnézet -->
  <meta property="og:type" content="website">
  <meta property="og:title" content="Mechanikus billentyűzetek">
  <meta property="og:description" content="Lineáris és taktilis kapcsolók, gyors szállítás.">
  <meta property="og:image" content="https://www.example.com/og/billentyuzetek.jpg">
  <meta property="og:url" content="https://www.example.com/billentyuzetek">
  <meta name="twitter:card" content="summary_large_image">

  <!-- Strukturált adat (JSON-LD) termékoldalhoz -->
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "Mechanikus billentyűzet K-01",
    "image": "https://www.example.com/img/k01.jpg",
    "offers": {
      "@type": "Offer",
      "priceCurrency": "HUF",
      "price": "34990",
      "availability": "https://schema.org/InStock"
    }
  }
  </script>
</head>
```

## Web components: custom elements
<!-- q: Hogyan készítsek keretrendszer-független, újrafelhasználható HTML komponenst custom elementtel? -->
<!-- tags: web components, custom elements, customElements.define, lifecycle callbacks, observedAttributes, custom event -->

A custom element saját HTML címke (kötelezően kötőjellel a nevében), amelynek viselkedését egy
HTMLElement-ből származó osztály adja, így bármilyen keretrendszerben vagy anélkül használható. Az
életciklus-metódusok: connectedCallback (DOM-ba kerüléskor), disconnectedCallback (eltávolításkor,
itt kell takarítani időzítőt és figyelőt), attributeChangedCallback (az observedAttributes-ben felsorolt
attribútumok változásakor). A komponens kifelé CustomEvent-ekkel kommunikál; a composed: true kell
ahhoz, hogy az esemény a shadow DOM határán is átjusson. A regisztráció előtti állapot a :not(:defined)
szelektorral stílusozható.

```javascript
// <countdown-timer seconds="90"></countdown-timer>
class CountdownTimer extends HTMLElement {
  static observedAttributes = ['seconds'];   // ezek változásakor fut az attributeChangedCallback
  #remaining = 0;
  #timer = null;

  connectedCallback() {                      // DOM-ba kerüléskor
    this.setAttribute('role', 'timer');
    this.#remaining = Number(this.getAttribute('seconds') ?? 60);
    this.#render();
    this.#timer = setInterval(() => this.#tick(), 1000);
  }

  disconnectedCallback() {                   // eltávolításkor: takarítás, különben szivárog
    clearInterval(this.#timer);
  }

  attributeChangedCallback(name, oldVal, newVal) {
    if (name === 'seconds' && oldVal !== newVal) {
      this.#remaining = Number(newVal);
      this.#render();
    }
  }

  #tick() {
    this.#remaining = Math.max(0, this.#remaining - 1);
    this.#render();
    if (this.#remaining === 0) {
      clearInterval(this.#timer);
      // bubbles + composed: a dokumentumig felbuborékol, shadow DOM-on át is
      this.dispatchEvent(new CustomEvent('countdown-end', { bubbles: true, composed: true }));
    }
  }

  #render() {
    const m = String(Math.floor(this.#remaining / 60)).padStart(2, '0');
    const s = String(this.#remaining % 60).padStart(2, '0');
    this.textContent = `${m}:${s}`;
  }
}

customElements.define('countdown-timer', CountdownTimer);
document.addEventListener('countdown-end', (e) => console.log('Lejárt:', e.target));
```

```html
<!-- A tartalék szöveg JS nélkül vagy regisztráció előtt is látszik -->
<countdown-timer seconds="90">01:30</countdown-timer>
<style>
  countdown-timer:not(:defined) { opacity: .6; }
  countdown-timer { font-variant-numeric: tabular-nums; }   /* nem ugrálnak a számjegyek */
</style>
```

## Shadow DOM, slotok és ::part
<!-- q: Hogyan szigeteljem el egy web component belső DOM-ját és stílusát shadow DOM-mal? -->
<!-- tags: shadow dom, slot, part, host, slotted, adoptedStyleSheets, encapsulation, declarative shadow dom -->

A shadow DOM a komponens belső szerkezetét és CSS-ét elszigeteli: a külső stílusok nem szivárognak be,
a belsők nem szivárognak ki, így nincs osztálynév-ütközés. A felhasználó által átadott tartalom (light
DOM) slotokon keresztül jelenik meg, a belső részek kívülről csak custom property-kkel és a part
attribútummal exportált ::part() szelektorral stílusozhatók. Az adoptedStyleSheets egy közös
CSSStyleSheet-et oszt meg minden példány között, ami memóriát takarít meg. Buktató: a külső oldal
szabályai erősebbek a :host szabályoknál; szerveroldali rendereléshez a deklaratív shadow DOM
(template shadowrootmode="open") való.

```javascript
// Egy közös, konstruált stíluslap minden példánynak
const sheet = new CSSStyleSheet();
sheet.replaceSync(`
  :host { display: block; border: 1px solid var(--card-border, #ddd); border-radius: 8px; }
  :host([variant="warning"]) { border-color: #f9a825; }      /* attribútum a hoston */
  header { display: flex; justify-content: space-between; padding: .75rem 1rem; font-weight: 600; }
  .body { padding: 0 1rem 1rem; }
  ::slotted(img) { max-width: 100%; border-radius: 4px; }   /* csak a slot közvetlen gyereke */
  button { all: unset; cursor: pointer; }
  button:focus-visible { outline: 2px solid currentColor; }
`);

class InfoCard extends HTMLElement {
  constructor() {
    super();
    const root = this.attachShadow({ mode: 'open' });
    root.adoptedStyleSheets = [sheet];
    root.innerHTML = `
      <header part="header">
        <slot name="title">Cím nélkül</slot>
        <button part="close" aria-label="Bezárás">✕</button>
      </header>
      <div class="body"><slot></slot></div>`;
    root.querySelector('button').addEventListener('click', () => this.remove());
    root.querySelector('slot:not([name])').addEventListener('slotchange', (e) => {
      // a kiosztott light DOM elemek változásáról értesít
      console.log('Tartalomelemek:', e.target.assignedElements().length);
    });
  }
}
customElements.define('info-card', InfoCard);
```

```html
<info-card variant="warning">
  <span slot="title">Karbantartás</span>
  <p>Szombaton 2:00 és 4:00 között a szolgáltatás nem elérhető.</p>
</info-card>
<style>
  /* Kívülről csak custom property-k és exportált part-ok érhetők el */
  info-card { --card-border: #90caf9; }
  info-card::part(header) { background: #f5f9ff; }
</style>
```

## Stacking context, z-index és pozicionálás
<!-- q: Miért nem működik a z-index, és hogyan kezeljem a rétegeket és a sticky pozicionálást? -->
<!-- tags: z-index, stacking context, position, sticky, absolute, isolation, top layer -->

A z-index csak pozicionált (relative, absolute, fixed, sticky) elemre, illetve flex- és grid-gyerekre
hat, és csak a saját stacking contexten belül versenyez. Új stacking contextet hoz létre többek között a
transform, a 1-nél kisebb opacity, a filter, a will-change és az isolation: isolate, így egy belső elem
z-index: 9999 értéke sem emeli ki a szülője rétegéből. A tudatos rétegskála (változókkal), az isolation
a komponensek elszigetelésére és a natív top layer (dialog, popover) megszünteti a z-index háborút. A
position: sticky nem működik, ha egy ős overflow értéke hidden vagy auto, és nincs megadva top/bottom.

```css
.header { position: sticky; top: 0; z-index: 10; }

/* BUKTATÓ: a transform új stacking contextet hoz létre, ezért a .dropdown
   z-index: 9999-e is a .card rétegén belül marad, és a .header alá kerülhet. */
.card { transform: translateZ(0); }
.card .dropdown { position: absolute; z-index: 9999; }

/* 1) Tudatos rétegskála egy helyen */
:root {
  --z-dropdown: 100;
  --z-sticky: 200;
  --z-modal: 1000;
  --z-toast: 1100;
}
.toast { position: fixed; z-index: var(--z-toast); }

/* 2) Komponens elszigetelése: a belső z-index-ek nem versenyeznek kívül */
.widget { isolation: isolate; }

/* 3) A dialog.showModal() és a popover a top layerbe kerül: mindig felül van */

/* Sticky fejléc görgethető táblázatban: a legközelebbi görgető őshöz tapad */
.table-wrap { overflow: auto; max-height: 400px; }
.table-wrap th { position: sticky; top: 0; background: var(--bg, #fff); }

/* absolute: a legközelebbi pozicionált őshöz viszonyít */
.avatar { position: relative; }
.avatar .badge { position: absolute; right: -4px; bottom: -4px; }

/* inset: 0 = top, right, bottom, left: 0 -> teljes lefedés */
.overlay { position: fixed; inset: 0; background: rgb(0 0 0 / .4); }
```

## Natív dialog és Popover API
<!-- q: Hogyan készítsek modális ablakot és lenyíló menüt JavaScript könyvtár nélkül? -->
<!-- tags: dialog, showModal, popover, popovertarget, backdrop, anchor positioning, top layer, focus trap -->

A dialog elem showModal() hívással modális: a top layerbe kerül, a háttér inert lesz (fókuszcsapda),
Esc-re bezárul, és a ::backdrop pszeudo-elemmel stílusozható háttere van. A form method="dialog"
gombjai JS nélkül zárják be, a megnyomott gomb value értéke a returnValue-ba kerül. A popover
attribútum nem modális lebegő elemet (menü, tooltip) ad: a popovertarget gomb nyitja, kívülre
kattintva vagy Esc-re bezárul. Az anchor positioning a popovert a nyitó gombhoz igazítja; régebbi
böngészőkben ehhez JS-alapú pozicionálás kell.

```html
<button type="button" id="open-delete">Fiók törlése</button>

<dialog id="confirm" aria-labelledby="confirm-title">
  <!-- method="dialog": a gomb bezárja a dialógust, a value a returnValue-ba kerül -->
  <form method="dialog">
    <h2 id="confirm-title">Biztosan törlöd a fiókot?</h2>
    <p>A művelet nem vonható vissza.</p>
    <button value="cancel" autofocus>Mégse</button>
    <button value="confirm">Törlés</button>
  </form>
</dialog>

<!-- Popover: nem modális menü, kívülre kattintva bezárul -->
<button type="button" class="menu-btn" popovertarget="user-menu">Fiók ▾</button>
<div id="user-menu" popover>
  <a href="/profil">Profil</a>
  <a href="/kilepes">Kilépés</a>
</div>

<style>
  dialog { border: none; border-radius: 12px; padding: 1.5rem; max-width: min(90vw, 420px); }
  dialog::backdrop { background: rgb(0 0 0 / .5); backdrop-filter: blur(2px); }

  /* Anchor positioning: a menü a gomb alá igazodik */
  .menu-btn { anchor-name: --menu-btn; }
  #user-menu {
    position-anchor: --menu-btn;
    inset: auto;
    top: anchor(bottom);
    left: anchor(left);
    margin: 4px 0 0;
  }
</style>

<script>
  const dlg = document.getElementById('confirm');
  document.getElementById('open-delete').addEventListener('click', () => dlg.showModal());
  dlg.addEventListener('close', () => {
    if (dlg.returnValue === 'confirm') {
      // itt jöhet az API-hívás; a show() nem modális, a showModal() modális
      console.log('Törlés megerősítve');
    }
  });
</script>
```
