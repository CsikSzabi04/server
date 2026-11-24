# Tesztvezérelt gondolkodás — specifikáció → teszt → kód → futtatás → javítás

> **Miről szól:** a programozó ciklus magja. Előbb a tesztek születnek (vagy a feladat adja őket), utána a
> megvalósítás; a sandbox ítél, a hibaüzenet tömörítve visszamegy a modellhez, legfeljebb 3 javítási körig.
> Tulajdonságalapú és differenciális tesztek, javítási költségvetés, és védelem a „tesztcsalás” ellen.

## 1. Miért pont a teszt — különösen kis modellnél

- Egy 2–4B-s helyi modell **rosszul ellenőrzi önmagát** („szerintem jó”), de egy konkrét, elbukott állításból
  (`várt: 3, kapott: 2`) sokkal jobban javít. A teszt a **külső, objektív visszajelzés**, amit a modell nem tud „lebeszélni”.
- A teszt **rögzíti a megértést**: ha a teszt rossz, a hiba már a specifikációnál kiderül, nem a kód 3. körénél.
- A zöld teszt maga a **tanulási bizonyíték**: csak ami átment, kerülhet a tudástárba ([03](03-kod-tudasbazis.md)).
- Ez a P0 minimális ciklusa ([../thinking.md](../thinking.md) 8. pont): feladat → kód → sandbox → javítás ≤ 3 → tárolás.

## 2. A ciklus

```ts
async function solve(task: CodeTask, budget: Budget): Promise<Outcome> {
  const spec = await understand(task);                       // pontosító kérdés, ha kétértelmű (02-belso-parbeszed/03)
  const hit = await reuseFromKB(spec);                       // 03 / 5. pont: T3+ találat → futtatás → kész
  if (hit?.status === 'pass') return done(hit, 'kb');

  const tests = task.visibleTests ?? (await writeTests(spec)); // Tesztelő szerep
  await validateTests(tests, spec);                          // 3. pont: piros a csonkon, Kritikus-ellenőrzés
  const frozen = freeze(tests);                              // hash → a megvalósítás nem írhatja át (8. pont)

  let impl = await implement(spec, frozen, examplesFromKB(spec));   // Gondolkodó szerep
  for (let round = 0; ; round++) {
    const res = await sandbox.run(impl, frozen);             // 04: RunResult
    if (res.status === 'pass') break;
    if (round >= budget.repairRounds || timeUp(budget)) return giveUp(task, impl, res);  // őszinte jelentés
    const fb = compress(res);                                // 5. pont
    impl = noProgress(res, history) ? await changeStrategy(spec, fb) : await repair(impl, fb); // 6. pont
  }
  const extra = await sandbox.run(impl, propertyAndLintChecks(spec));  // tulajdonság + lint + típus
  if (extra.status !== 'pass') return partial(impl, extra);
  return storeAndLearn(task, impl, frozen);                  // 03 + tanulság-jegyzet (06 / 9. pont)
}
```

Megjegyzés: a mérésnél ([09](09-meres-es-benchmark.md)) a **rejtett** teszteket a javító ciklus soha nem látja; csak a
végső ítéletnél futnak.

## 3. Honnan jönnek a tesztek, és mitől jók

**Elsőbbségi sorrend:** (1) a feladat/felhasználó adta tesztek → (2) a specifikáció példáiból (bemenet → kimenet
párok) gépiesen generált tesztek → (3) a Tesztelő szerep által írt tesztek.

**Validálás, mielőtt bármi kód születne:**

1. **Piros a csonkon:** a tesztek egy `throw new Error('not implemented')` / `raise NotImplementedError` csonk ellen
   **mind elbuknak**. Ami zöld a csonkon, az semmit nem ellenőriz → eldobjuk.
2. **Kritikus-ellenőrzés:** minden teszt visszavezethető-e a specifikáció egy mondatára? Ha nem, a teszt
   kitalált követelményt rögzít → törlés vagy pontosító kérdés ([../02-belso-parbeszed/02-vita-protokoll.md](../02-belso-parbeszed/02-vita-protokoll.md)).
3. **Szélesetek ellenőrzőlistája** (legalább azok, amelyek a feladatra értelmezhetők): üres bemenet · egy elem ·
   ismétlődés · nulla/negatív · nagyon nagy · ékezet és Unicode (`ő`, `ű`) · szóköz/whitespace ·
   `null`/`undefined`/`None` · rossz típus → hiba · rendezés stabilitása · idő (injektált óra) · lebegőpontos kerekítés.
4. **Mutáns-próba (lite):** a referencia vagy az első zöld megoldás 5–10 egyszerű mutánsa (`<` ↔ `<=`, `+1`/`-1`,
   feltétel tagadása) — a tesztek öljék meg a mutánsok ≥ 60 %-át (célérték). Ha nem, a Tesztelő pótol.

## 4. Tulajdonságalapú tesztek

Kis modellnek könnyebb **szabályt** mondani („kétszer alkalmazva ugyanaz”), mint sok helyes példát kiszámolni.

| Tulajdonság | Jelentés | Példa |
|---|---|---|
| idempotencia | `f(f(x)) = f(x)` | `slugifyHu` |
| oda-vissza | `parse(format(x)) = x` | `parse_forint` |
| invariáns | hossz, rendezettség, elemhalmaz megmarad | rendezés, szűrés |
| metamorf | `sort(xs) = sort(shuffle(xs))` | aggregálás, rendezés |
| orákulum | egyezés egy naiv referencia-megoldással (5. pont) | bármely optimalizált algoritmus |
| nem dob | érvényes tartományban nincs kivétel | parserek |

```ts
import fc from 'fast-check';                       // MIT, a sandbox runtime-ba vendorolva
test('slugifyHu idempotens', () => {
  fc.assert(fc.property(fc.string(), (s) => slugifyHu(slugifyHu(s)) === slugifyHu(s)));
});
```

```python
from hypothesis import given, strategies as st      # MPL-2.0, a sandbox runtime-ba telepítve

@given(st.integers(min_value=-10**9, max_value=10**9))
def test_oda_vissza(n):
    assert parse_forint(f"{n:,}".replace(",", " ") + " Ft") == n
```

## 5. Differenciális teszt naiv referenciával

Kis modellnél gyakran könnyebb egy **lassú, de nyilvánvalóan helyes** változatot írni (két egymásba ágyazott ciklus,
teljes bejárás). Ezt külön generáljuk, külön ellenőrizzük kis bemeneteken, majd orákulumként vetjük össze a
gyors megoldással véletlen bemeneteken. Ha a kettő eltér, a hibás bemenet automatikusan új, rögzített teszt lesz.

## 6. Visszajelzés tömörítése és stratégiaváltás

A modell nem a teljes kimenetet kapja, hanem egy rövid, szerkezett összefoglalót (≤ 1 KB, becslés arra, amit a kis
modell még jól hasznosít — **mérni kell**):

```
ELBUKOTT TESZT: slugifyHu › ékezetek
  várt:   "arvizturo-tukorfurogep"
  kapott: "-rv-zt-r-t-k-rf-r-g-p"
  hely:   solution.ts:2   return s.toLowerCase().replace(/[^a-z0-9]+/g, '-');
TOVÁBBI: 2 teszt bukott (nem részletezve) · ELŐZŐ KÖR: ugyanez a hiba
TIPP (hibatudástár, 06): az ékezetes betűt előbb bontsd szét: normalize('NFD')
```

**Nincs előrelépés**, ha két egymást követő kör „aláírása” (a bukott tesztek neve + normalizált hiba, [06](06-hibakereses.md))
azonos. Ekkor nem javítgatunk tovább, hanem stratégiát váltunk, ebben a sorrendben:
(1) újragenerálás nulláról, magasabb hőmérséklettel és a hibás teszt magyarázatával → (2) kisebb lépés: segédfüggvény
külön megírása és tesztelése → (3) tudástár/web a hibára ([06](06-hibakereses.md) 8. pont) → (4) felhő, csak opt-in
([../08-modellek-es-utvonalvalasztas/03-felhos-segitseg-opcionalis.md](../08-modellek-es-utvonalvalasztas/03-felhos-segitseg-opcionalis.md)) → (5) őszinte feladás.

## 7. Javítási költségvetés

A gemma4:e2b mért ~6,2 token/s sebességéből számolva (becslés): 400 token ≈ 65 s, 900 token ≈ 145 s generálásonként.

| Szint | Tesztírás | Max. token / generálás | Javítási kör | Teljes falióra-keret (becslés) |
|---|---|---|---|---|
| L0 | — (a feladat adja) | 200 | 2 | 3 perc |
| L1 | 1 generálás | 400 | 3 | 8 perc |
| L2 | 1 generálás + Kritikus | 900 | 3 | 20 perc |
| L3 | fájlonként | 900 / fájl | 3 / lépés, összesen ≤ 10 | 60+ perc (háttér/éjjel) |
| L4 | lépésenként, a [../07-komplex-feladatok/02-terv-vegrehajtas-ellenorzes.md](../07-komplex-feladatok/02-terv-vegrehajtas-ellenorzes.md) szerint | — | ott | órák (éjjel) |

**KV-cache-barát javítás:** a mért viselkedés szerint az Ollama 0.40 a gyorsítótárat csak a *korábbi prompt végétől*
tudja folytatni, a rendszerprompt cseréje drága (gemma4:e2b ~6 s). Ezért a javítási kör a meglévő beszélgetéshez
**hozzáfűz** (ugyanaz a rendszerprompt, új felhasználói üzenet a visszajelzéssel), nem épít új promptot. A szerepváltás
(Tesztelő → Gondolkodó) körönként legfeljebb egyszer történjen ([../02-belso-parbeszed/01-szerepek.md](../02-belso-parbeszed/01-szerepek.md)).

**Promptnyelv:** a belső, kódra vonatkozó promptok angolul valószínűleg jobban működnek a kis modelleken, a
felhasználónak szóló magyarázat magyar — ez **mérni kell** (A/B a dev készleten, [09](09-meres-es-benchmark.md)).
Sablonok: [../02-belso-parbeszed/04-prompt-sablonok.md](../02-belso-parbeszed/04-prompt-sablonok.md).

## 8. Tesztek befagyasztása és a „tesztcsalás” ellen

- A tesztfájlok hash-e a `RunResult.testsHash`-ben; a futtató eltérésnél nem fut (`blocked`).
- A modell kimenetéből **csak a megoldásfájl(ok)** kerülnek a futási mappába; ha tesztet is „javít”, azt eldobjuk és jelezzük.
- **Bedrótozás-figyelő:** ha a megoldás a látható tesztek várt kimeneteit literálként tartalmazza elágazásban → gyanú, Kritikus nézi meg.
- A rejtett tesztek másik bemeneteket használnak; ami csak a láthatókon zöld, az **nem siker**.

## 9. Kész, ha

- a `solve` a P0-ban 30 L1-feladaton végigfut, és minden kimenet `pass` / `partial` / `giveUp` + teljes napló;
- a csonk-validálás minden generált tesztkészletre lefut, és a „zöld a csonkon” tesztek nem kerülnek be;
- a nincs-előrelépés detektor egy szándékosan elrontott példán stratégiát vált (teszt fedi);
- a mérés kimutatja, hogy a tesztvisszajelzéses javítás páros összevetésben segít-e a „modell egyedül”-höz képest ([09](09-meres-es-benchmark.md) 6. pont).

## Kapcsolódó

- [04-sandbox-kodfuttatas.md](04-sandbox-kodfuttatas.md) · [06-hibakereses.md](06-hibakereses.md) · [08-gyakorlofeladatok.md](08-gyakorlofeladatok.md) · [09-meres-es-benchmark.md](09-meres-es-benchmark.md)
- [../01-architektura/02-gondolkodo-ciklus.md](../01-architektura/02-gondolkodo-ciklus.md) · [../02-belso-parbeszed/01-szerepek.md](../02-belso-parbeszed/01-szerepek.md)
- [../07-komplex-feladatok/04-onellenorzes-es-javitas.md](../07-komplex-feladatok/04-onellenorzes-es-javitas.md)
