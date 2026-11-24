# Mérés és benchmark — honnan tudjuk, hogy tényleg jobban programoz?

> **Miről szól:** a programozási képesség mérése: saját, magyar feladatkészlet (`aurikod-hu`) elkülönített
> (held-out) résszel, regressziós készlet, pass@1 és javítással@3, idő- és költségmérés, szintenkénti
> dashboard — és szabályok, hogy ne csapjuk be magunkat (szennyezés, canary, előre rögzítés, páros összevetés).

## 1. Mire akarunk választ kapni

1. Megoldja-e Auri a szintje feladatait **olyanokon is, amiket sosem látott**? (rejtett készlet)
2. Az agy (tudástár + sandbox-javítás + web) **többet ér-e**, mint a modell egyedül? (abláció, 6. pont)
3. Romlott-e valami, ami korábban ment? (regresszió)
4. Mennyi idő és erőforrás egy megoldás a gépen? (CPU-n ez szűk keresztmetszet)

## 2. A készletek

| Készlet | Méret (cél) | Ki látja | Mire |
|---|---|---|---|
| `dev` | 40 feladat / nyelv (L0–L2) | promptfejlesztés, hibakeresés | hangolás — eredménye **nem** hivatalos |
| `heldout` | ≥ 60 feladat / nyelv / szint | csak a mérőszkript, hetente legfeljebb egyszer | a hivatalos szint (01) |
| `regression` | növekvő: minden valaha megoldott + minden kijavított hiba | éjszakai minta (10 rotálva), hetente teljes | visszaesés-figyelés; a megoldásuk lehet a tudástárban — ez a **megtartást** méri, nem az általánosítást |
| `public-sanity` | 20 feladat HumanEval (MIT) / MBPP (CC BY 4.0) részhalmazból | mérőszkript | csak józansági ellenőrzés: ezek valószínűleg a modell tanítóadatában vannak |

A feladatformátum azonos a gyakorlással (`CodeTask`, [08](08-gyakorlofeladatok.md) 1. pont), `split` mezővel.
A rejtett készletet **ember írja** (vagy egy erős felhős modell, emberi átnézéssel), magyar leírással, a mérés előtt.

## 3. Mérőszámok

| Mérőszám | Definíció |
|---|---|
| **pass@1** | első generálás, javítás nélkül, `temperature = 0` → minden rejtett teszt zöld |
| **javítással@3** | legfeljebb 3 javítási kör után minden rejtett teszt zöld; a javító **csak a látható tesztek** visszajelzését kapja |
| pass@k (ritkán) | torzítatlan becslő: 1 − C(n−c, k) / C(n, k), ahol n minta, c zöld — CPU-n drága, csak n = 5-tel, havonta |
| körszám | a javítási körök átlaga a sikereseknél; „nincs előrelépés” arány ([05](05-tesztvezerelt-gondolkodas.md)) |
| falióra | feladatonként medián és p90 (generálás + sandbox külön is) |
| tokenek | generált és bemeneti tokenek feladatonként |
| tudástár-találat | a megoldások hány %-ában volt T2+ snippet a promptban; **modell nélküli** megoldások aránya |
| lint-tisztaság | a sikeres megoldások hány %-a `tsc --strict` / `ruff` tiszta |
| felhőhívás (P6) | hívásszám és költség feladatonként; alapértelmezés: 0 |
| **hamis „kész”** | futtatás nélküli siker-állítás a naplóban — **mindig 0-nak kell lennie** |

## 4. Futtatási protokoll

A Jarvis `scripts/eval_tools.py` mintáját követjük: YAML-fixture → `judge()` → JSON + Markdown táblázat a
stdoutra → **kész-kapu** (DoD) ellenőrzés → eredmény a `data/…/eval/` alá időbélyeggel. Rögzített feltételek:

- `temperature = 0`, rögzített `seed`, rögzített `num_ctx` és `num_predict`; a gép **tétlen** (éjjel);
- naplózzuk: modellnév + digest, Ollama-verzió (most 0.40.16), promptsablon-verzió (hash), tudástár-pillanatkép
  hash, sandbox-szint, Node/Python/TS verzió;
- a futás közben a tudástár **csak olvasható pillanatkép**; a held-out futás megoldásai **nem** kerülnek be;
- a futások 10 %-át megismételjük → a nem-determinizmus arányát is jelentjük (CPU-szálak miatt előfordulhat, mérni kell).

Időigény (becslés): 60 feladat × 3–8 perc ≈ 3–8 óra nyelvenként → a held-out heti, éjszakai futás; több nyelv
esetén éjszakákra bontva.

## 5. Eredményformátum

```json
{"run_id": "2026-12-05T01:10_ab12", "task_id": "ts-l1-0042", "split": "heldout", "mode": "brain",
 "model": "gemma4:e2b", "model_digest": "…", "prompt_ver": "tdd-v3", "kb_snapshot": "sha256:…",
 "pass1": false, "pass_repair3": true, "rounds": 2, "no_progress": false, "kb_hit": "snip_ts_slugify_hu_01",
 "wall_ms": 312000, "gen_ms": 251000, "sandbox_ms": 4100, "tokens_out": 1180, "tokens_in": 5400,
 "hidden": {"passed": 7, "total": 7}, "lint_clean": true, "sandbox": "S0", "cloud_calls": 0}
```

Tárolás: `eval_run` (környezet, verziók) és `eval_result` (soronként a fenti) tábla az Auri Core SQLite-jában;
összesítés: [../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md).

## 6. Ablációk — az agy tényleg segít?

Ugyanazon a rejtett készleten, **páros** összevetéssel:

| Mód | Mit kapcsolunk be |
|---|---|
| `model-only` | csak a modell, egy generálás (alapvonal) |
| `+repair` | + sandbox-visszajelzéses javítás ≤ 3 kör |
| `+kb` | + tudástár (few-shot és újrahasznosítás) |
| `+web` | + webes hibakeresés / API-dokumentáció |
| `+cloud` (P6) | + opcionális felhő a nehéz esetekre |

Szabály: egy komponens csak akkor marad bekapcsolva alapértelmezésként, ha a páros összevetés (7. pont)
mérhető javulást mutat — vagy ha nem ront, és más okból kell (pl. biztonság).

## 7. Statisztikai őszinteség

- **Bizonytalanság:** 60 feladatnál, 50 % körüli arányon a 95 %-os bizonytalanság nagyjából ±12–13 százalékpont
  (Wilson-intervallum; számítás, nem mérés). Ezért két külön futás 5–10 pontos különbségét **nem** hirdetjük javulásnak.
- **Páros teszt (McNemar):** `b` = A megoldja, B nem; `c` = fordítva. Ha `b + c ≥ 25`: szignifikáns 5 %-on, ha
  (|b − c| − 1)² / (b + c) > 3,84; kisebb `b + c`-nél egzakt binomiális próba.
- **Regresszió-riasztás:** az éjszakai mintán 2+ feladat esik ki az előző zöldek közül → ellenőrzés; a heti teljes
  regressziós futás dönt.

## 8. Hogyan ne csapjuk be magunkat

1. **A held-out szent:** soha nem kerül promptba, tudástárba, gyakorlásba, webes lekérdezésbe vagy felhős modellhez.
2. **Canary:** minden held-out fájlban egy egyedi `AURI-CANARY-<guid>` sor; éjszakai keresés a tudástárban, a
   gyakorlófeladatokban, a naplókban és a webes cache-ben — találat esetén a készlet **szennyezett**, rotálni kell.
3. **Előre rögzítés:** a készlet a mérés előtt fagy be (manifest: fájlonkénti sha256 + dátum); változás = új verzió
   (`aurikod-hu v2`), verziók között nem hasonlítunk.
4. **Hangolás csak a `dev`-en.** A held-out eredményét akkor is naplózzuk, ha rossz; „a legjobb a három futásból” tilos.
5. **Nyilvános készlet ≠ képesség:** a HumanEval/MBPP magas eredménye szennyezés miatt keveset jelent — csak józansági jel.
6. **Tesztjátszás ellen:** a sikeres megoldások 10 %-át ember nézi át; a bedrótozás-figyelő ([05](05-tesztvezerelt-gondolkodas.md) 8. pont) jelzéseit külön számoljuk.
7. **Tudástár vs. képesség:** a `kb_hit` mezővel szétválasztjuk, mit oldott meg „emlékezetből” és mit „gondolkodva” —
   mindkettő érték, de a kettőt nem keverjük egy számba.
8. **Tanulás utáni mérés friss készleten:** ha a gyakorlás miatt javul, azt egy új, korábban nem használt rejtett
   készleten is igazolni kell.

## 9. Dashboard

Előbb Markdown-jelentés (mint az `eval_tools.py` kimenete), P6-ban webes dashboard ([../11-utemterv/01-fazisok.md](../11-utemterv/01-fazisok.md)).

| Panel | Tartalom |
|---|---|
| Szint × nyelv | L0–L4 sorok: n, pass@1, javítással@3 (±CI), medián idő, trend az előző héthez |
| Abláció | a 6. pont módjai egymás mellett, páros különbséggel |
| Témák | `x.*`, `ts.*`, `py.*` témák sikeraránya hőtérképen → visszacsatolás a tananyag-ütemezőbe ([02](02-tananyag.md)) |
| Költség | token, falióra, sandbox-idő, felhőhívás feladatonként |
| Regresszió | a kiesett feladatok listája az első rossz futás azonosítójával |
| Egészség | hamis „kész” (= 0?), canary-ellenőrzés, nem-determinizmus aránya |

## 10. Kész, ha (P0)

- az `aurikod-hu v1` befagyasztva: TS és Python, L0–L1, nyelvenként ≥ 40 `dev` és ≥ 60 `heldout` feladat, canaryval;
- a mérőszkript `model-only` és `+repair` módban végigfut, és JSON + Markdown jelentést ad a 7. pont bizonytalanságával;
- az alapvonal (gemma4:e2b, `model-only`) mérve és a fejlődési naplóba írva ([../10-meres-es-fejlodes/03-fejlodesi-naplo-sablon.md](../10-meres-es-fejlodes/03-fejlodesi-naplo-sablon.md));
- az éjszakai regressziós minta és a canary-keresés ütemezve fut; a hamis „kész” számláló 0.

## Kapcsolódó

- [01-cel-es-szintek.md](01-cel-es-szintek.md) · [05-tesztvezerelt-gondolkodas.md](05-tesztvezerelt-gondolkodas.md) · [08-gyakorlofeladatok.md](08-gyakorlofeladatok.md)
- [../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md) · [../10-meres-es-fejlodes/02-ertekelo-keszletek.md](../10-meres-es-fejlodes/02-ertekelo-keszletek.md)
- [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md) · [../11-utemterv/02-kovetkezo-lepesek.md](../11-utemterv/02-kovetkezo-lepesek.md)
