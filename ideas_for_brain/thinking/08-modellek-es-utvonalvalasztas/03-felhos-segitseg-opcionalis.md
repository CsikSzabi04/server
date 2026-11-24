# Felhős segítség (opcionális)

> **Miről szól:** mikor és hogyan kérhet Auri segítséget felhős modelltől (Groq, Gemini) — alapból
> **kikapcsolva**, csak a felhasználó tudtával, kitakarás után, kvótafigyeléssel és 429-kezeléssel. A
> felhő **mankó**, nem alap: minden alapfunkció nélküle is működik. (Fázis: P6.)

## 1. Alapállás

- **Alapból ki.** A Core a felhasználó kifejezett bekapcsolása nélkül egyetlen bájtot sem küld ki.
- **Helyi először.** A router csak L2/L3 kudarca után vagy kifejezett kérésre lép L4-re
  ([02-router.md](02-router.md)).
- **Látható.** Minden felhős hívásnál a felület jelzi: „ezt a Groq válaszolta”, és megnézhető, mi
  ment ki.
- **Háttérmunka soha** nem hív felhőt (éjszakai tanulás, ismétlés, konszolidáció).

## 2. Beállítás

| `cloud.mode` | Jelentés |
|---|---|
| `off` (alap) | nincs felhős hívás |
| `ask` | minden alkalommal előnézet + kérdés: „Elküldhetem a Groqnak? Ez megy ki: …” |
| `auto_general` | általános kérdés és saját-projekt-kód nélküli feladat automatikusan mehet; minden más `ask` |

Saját projekt kódja csak **projektenkénti, kifejezett** engedéllyel mehet ki, és akkor is csak a
minimális részlet (a hibás függvény + a hibaüzenet), soha az egész tároló. Vendég nevében a Core nem
hív felhőt (a hosztolt AuriGPT meglévő `web/api/chat.ts` lánca ettől független).

## 3. Mikor igen, mikor nem

| Helyzet | Felhő? |
|---|---|
| Élő kérés, az L2 (és ha van, az L3) a keretén belül bukott, `cloud.mode ≠ off` | igen, egyszer, jelezve |
| A felhasználó kifejezetten kéri („kérdezd meg a felhőt”) | igen (`off` mellett is rákérdez) |
| Háttérfeladat, önálló tanulás | **soha** |
| A kitakarás személyes adatot vagy titkot talál | **nem** — nem maszkolunk és küldünk, hanem nem küldjük |
| A kvóta elfogyott / a megszakító nyitva | nem; a helyi eredmény vagy őszinte „nem sikerült” |

## 4. Kitakarás (minden kimenő hívás előtt)

```python
def prepare_cloud_payload(msgs: list[Msg], user: UserCtx, purpose: str) -> CloudPayload | Refusal:
    text = "\n".join(m.content for m in msgs)
    if is_personal(text, names=user.names):          # web/src/brain/privacy.ts logikája
        return Refusal("személyes adat")             # hamis pozitív = csak nem megy ki, ez rendben
    if is_secret(text) or DECLARED_SECRET.search(text):  # auri-jarvis memory/redact.py
        return Refusal("titok")                      # kulcs, token, kártyaszám, IBAN, hosszú azonosító
    red = mask_paths(text)                           # C:\Users\<név>\… → <HOME>\…
    red = mask_hosts_emails_ips(red)                 # gépnév, e-mail, IP → helyőrző
    return CloudPayload(text=red, purpose=purpose, sha256=sha256(red), redactions=count_masks(red))
```

- A felhasználói profil, a T1-memória és a `me.md` tartalma **soha** nem kerül felhős promptba.
- A kimenő, már kitakart szöveg helyi naplóba kerül (`cloud_audit`: idő, szolgáltató, modell, cél,
  méret, kitakarások száma, maga a kitakart szöveg) 30 napig (becslés) — a felhasználó bármikor
  megnézheti, mi ment ki.
- A kulcsok csak az `auri-core/.env`-ben (gitignore-olva), soha nem naplózva, soha nem promptban.

## 5. Kvóták

Ingyenes keretek (külső forrás, 2026, **nem garantált**, ld. a ténylap 6. pontját):

| Szolgáltató | Keret | Megjegyzés |
|---|---|---|
| Groq | modellenként pl. `gpt-oss-120b` ~1000 kérés/nap | gyors, nagy modellek |
| Gemini | modelltől függően ~50–250 kérés/nap | az ingyenes csomagnál a Google felhasználhatja az adatokat |

⚠️ A `web/api/chat.ts` a Geminit csak `GEMINI_PAID=1` mellett használja, mert a kód megjegyzése szerint
a Google feltételei az ingyenes keretet EGT-beli felhasználóknak nem engedik. A Core ugyanezt a
szabályt követi: **Gemini csak fizetős projekttel**; a feltételeket bekapcsolás előtt ellenőrizni kell.

- Helyi számláló szolgáltatónként / modellenként / naponta; a becsült keret 80%-ánál (becslés) a
  Core leáll, hogy maradjon hely a hosztolt AuriGPT-nek, ha ugyanazt a fiókot használják.
- Felhasználói napi plafon (pl. 20 hívás/nap, becslés) — a felhő ne váljon csendben az alappá.

## 6. 429 és hibák kezelése

```python
async def call_cloud(payload: CloudPayload, interactive: bool) -> CloudAnswer | None:
    for prov in providers_in_order():                      # Groq → (Gemini, ha fizetős)
        if breaker[prov].open or quota[prov].exhausted():
            continue
        try:
            return await prov.chat(payload, timeout_s=60)
        except RateLimited as e:                           # HTTP 429
            wait = e.retry_after_s
            if interactive and wait is not None and wait <= 30:
                await asyncio.sleep(wait)                  # egyszer várunk, élő kérésnél
                with contextlib.suppress(RateLimited):
                    return await prov.chat(payload, timeout_s=60)
            quota[prov].mark_exhausted(until=e.reset_at or next_midnight_utc())
        except (Timeout, ServerError):
            breaker[prov].record_failure()                 # 3 egymás utáni hiba → 10 percig nyitva (becslés)
    return None                                            # → helyi eredmény vagy GIVE_UP
```

A megszakító mintája a webben már megvan (`web/src/autolearn/circuitBreaker.ts`); a Core ugyanezt a
viselkedést valósítja meg Pythonban.

## 7. Mit tanulhat a felhőből?

- A felhős válasz is **`hypothesis`**, eredettel: `cloud:<szolgáltató>:<modell>`. Előléptetés csak
  helyi ellenőrzéssel (zöld tesztek a sandboxban, egyező források).
- Mérjük a **felhőfüggőséget**: a sikeres epizódok hány százaléka használt L4-et. A cél, hogy ez
  idővel **csökkenjen**, mert a sikeres felhős megoldás ellenőrizve a tudástárba kerül, és legközelebb
  L0 adja vissza ([04-cache-es-ujrahasznositas.md](04-cache-es-ujrahasznositas.md)).
- Nyitott kérdés: a szolgáltatók feltételei engedik-e a kimenet tartós tárolását és újrahasznosítását
  ([../11-utemterv/03-nyitott-kerdesek.md](../11-utemterv/03-nyitott-kerdesek.md)).

## 8. Kész, ha

- `cloud.mode: off` mellett egy hálózati mock egyetlen kimenő hívást sem lát (teszt).
- Személyes adatot / titkot tartalmazó kérésnél a kimenő hívás elmarad, és a felhasználó érthető
  magyar okot kap (teszt fiktív adattal, pl. „Teszt Elek”).
- Szimulált 429-re a router továbblép, a napi számláló frissül, és az élő kérés legfeljebb egyszer vár.
- A `cloud_audit` minden kiment szöveget mutat; a kulcs sehol nem jelenik meg a naplóban.

## Kapcsolódó

- [02-router.md](02-router.md) — L4 és az eszkaláció
- [01-helyi-modellek.md](01-helyi-modellek.md) — amit helyben próbálunk előbb
- [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md) — felhős keretek, szabályok
- [../09-biztonsag-es-adatvedelem/01-alapszabalyok.md](../09-biztonsag-es-adatvedelem/01-alapszabalyok.md) — személyes adat, titkok
- [../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md](../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md) — a felhős válasz is adat
- [../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md) — felhőfüggőség
- [../11-utemterv/01-fazisok.md](../11-utemterv/01-fazisok.md) — P6
