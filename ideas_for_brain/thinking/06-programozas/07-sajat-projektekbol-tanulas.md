# Tanulás a saját projektekből — a felhasználó kódja mint tananyag

> **Miről szól:** hogyan tanul Auri a felhasználó saját repóiból (`web/`, `server/`, `auri-jarvis/`):
> indexelés, konvenciók és stílus, architektúra-jegyzetek — **szigorú titok- és személyesadat-szűréssel**,
> helyben tartva, és frissen, ahogy a kód változik. A cél: L4-en a *meglévő* kódbázist is jól módosítsa.

## 1. Mit akarunk megtanulni

| Mit | Példa a mostani kódból | Mire jó |
|---|---|---|
| **Konvenciók** | fájlfejléc-komment a fájl céljáról (`// recipes.ts — …`); „pure, never throws” segédfüggvények | az új kód úgy néz ki, mintha a felhasználó írta volna |
| **Eszközök és verziók** | `requires-python = ">=3.12,<3.13"`, `ruff.toml` (`line-length = 130`), TS `strict`, Node `engines >=20` (`server/`) | a megoldás átmegy a projekt saját ellenőrzésein |
| **Tesztszerkezet** | `auri-jarvis/tests/{body,mind,voice}`, pytest `manual` marker, YAML-fixture-ök, fiktív adat („Minta Máté”) | a teszt a megszokott helyre és formában kerül |
| **Architektúra** | Jarvis: `mind/` (Ollama-kliens, agent-kör), `tools/registry.py` (`risk`, `min_tier`); web: `brain/`, `autolearn/`, `api/` | L4-ben tudja, *hova* kell nyúlni |
| **Minták** | dekorátoros eszközregisztráció, `ToolResult` frozen dataclass, magyar felhasználói üzenet + angol kódkomment | újrahasznosítható snippetek ([03](03-kod-tudasbazis.md), `source.kind='own-repo'`) |
| **Hiányok** | a `web/`-ben nincs tesztfuttató (csak `tsc --noEmit`) | javaslatnál jelzi, hogy ehhez előbb teszt-infrastruktúra kell |

## 2. Mely részek — és melyek soha

| Elérési minta | Döntés | Ok |
|---|---|---|
| `**/*.{ts,tsx,js,mjs,py,sql,css,html,md,toml,yaml,json}` | indexelhető, **szűrés után** | forráskód és konfiguráció |
| amit a `.gitignore` kizár | **kizárva** | ott vannak a titkok és a privát adatok |
| `**/.env*` — beleértve `web/.env.local`, `web/.env.vercel-*.local`, `server/.env`, `auri-jarvis/.env` | **soha** | kulcsok (`.env.example` csak szűrés után) |
| `auri-jarvis/data/**` | **soha** | a `.gitignore` szerint privát memória/adat |
| `auri-jarvis/config/me.md` (a `me.example.md` mehet) | **soha** | a felhasználó profilja = személyes adat |
| `auri-jarvis/config/persona.md` | csak kézi jóváhagyással | megszólítást, személyes utalást tartalmazhat |
| `**/node_modules`, `dist`, `.venv`, `__pycache__`, `models`, `PublicFreeAI/**`, `*.wav`, `*.onnx` | **soha** | idegen kód / bináris / modell |
| `**/*.{pem,key,pfx,p12}`, `id_*`, `.claude/**` | **soha** | kulcsok, eszközbeállítások |
| `deploy/**` | szűrés után, IP/hosztnév maszkolva | szerverelérhetőség |
| git-előzmények | csak commitüzenet (szűrve) és diff; **szerző neve/e-mailje soha** | személyes adat |

## 3. A folyamat

```
felderítés ─▶ útvonalszűrés (2.) ─▶ titokszűrés (4.) ─▶ személyesadat-szűrés (4.) ─▶ darabolás szimbólumonként (5.)
     ─▶ rövid magyar összefoglaló (helyi modell) ─▶ beágyazás (embeddinggemma) ─▶ tárolás commit-hash-sel
     ─▶ ellenőrzés: a repó tesztjei S1-ben (7.) ─▶ konvenciókártyák frissítése (6.)
```

Nehéz lépés (összefoglalás, beágyazás) **csak tétlenségben/éjjel** fut (egy Ollama-sáv,
[../05-tanulas/02-ejszakai-onallo-tanulas.md](../05-tanulas/02-ejszakai-onallo-tanulas.md)).

## 4. Titok- és személyesadat-szűrés

**Fájlszintű szabály:** ha egy fájlban **bármilyen** titoktalálat van, az egész fájl kimarad, és a helyi jelentésbe
csak az **útvonal** és a minta *neve* kerül (az érték soha). A felhasználó dönt, mit kezd vele.

| Mintacsalád (példák, nem teljes lista) | Mit fog meg |
|---|---|
| `-----BEGIN [A-Z ]*PRIVATE KEY-----` | privát kulcs |
| `eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{10,}` | JWT (pl. Supabase anon/service kulcs) |
| ismert előtagok: `sk-`, `gsk_`, `AIza`, `xox[bp]-`, `ghp_` + hosszú token | OpenAI-/Groq-/Google-/Slack-/GitHub-kulcs |
| `(api[_-]?key\|secret\|token\|passw(or)?d)\s*[:=]\s*['"][^'"]{8,}['"]` | hozzárendelt titok |
| ≥ 24 karakteres, magas entrópiájú (Shannon > 4,0) token hozzárendelésben | ismeretlen formátumú kulcs |
| `[a-z]{20}\.supabase\.co`, IPv4-cím, `C:\Users\<név>\` | projekt-/gépazonosító → **maszkolás** (`<PROJECT>`, `<IP>`, `<HOME>`) |

**Soronkénti szűrés** a megmaradt fájlokon: `isPersonal` (`web/src/brain/privacy.ts`) minden kommentre és
string-literálra; a bejelentkezett felhasználó neveit a szűrő **futásidőben** kapja a fiókjából, de ezek a nevek
maguk sem kerülnek az agyba. Találat → a sor kimarad (a kód szerkezete megmarad, a literál `<REDACTED>` lesz).
A szűrő hibája felé tévedünk: egy hamis pozitív csak annyi, hogy egy sorral kevesebbet tanul.

## 5. Darabolás és kártyák

```ts
interface RepoChunk {
  repo: 'web' | 'server' | 'auri-jarvis'; path: string; symbol: string;   // 'tools/registry.py#ToolRegistry'
  kind: 'function' | 'class' | 'module' | 'config' | 'test';
  code: string; summary_hu: string; commit: string; dirty: boolean;      // dirty = nem commitolt munkapéldány
  imports: string[]; usedBy: string[];                                    // egyszerű hívási gráf
}
interface ConventionCard { repo: string; rule_hu: string; evidence: string[]; confidence: number }
interface ArchNote { repo: string; area: string; summary_hu: string; entryPoints: string[]; commit: string }
```

Darabolás szimbólumonként: Pythonnál `ast`, TS-nél a TypeScript compiler API (a gépen 5.9.3 van). A `dirty`
darabok alacsonyabb súlyt kapnak, mert a munkakönyvtár most sok nem commitolt változást tartalmaz.

## 6. Konvenciók kinyerése

Determinisztikusan, ahol lehet (konfigurációból), és csak a többi a modellből:
- **konfigurációból:** `pyproject.toml`, `ruff.toml`, `tsconfig.json`, `package.json` (`scripts`, `engines`) → pontos kártyák, `confidence = 1`;
- **statisztikából:** névadás (camelCase / snake_case aránya), fájlfejléc-komment aránya, tesztek helye → `confidence` = arány;
- **modellből:** „milyen mintát követ ez a modul?” → `confidence ≤ 0,6`, amíg legalább 3 helyen meg nem erősítjük.

Használat: a Gondolkodó promptjába az érintett repó 3–5 legerősebb kártyája kerül (≤ 600 karakter); a Kritikus a
kész kódot ezekhez méri ([../02-belso-parbeszed/01-szerepek.md](../02-belso-parbeszed/01-szerepek.md)).

## 7. Ellenőrzés: a repó saját tesztjei

- **S1** sandboxban (WSL2/konténer, [04](04-sandbox-kodfuttatas.md)), egy **allowlistes másolaton** — a 2. pont
  tiltott fájljai a másolatba sem kerülnek.
- Ami a saját tesztekkel fedett és zöld, abból a kinyert snippet T2-t kaphat; a tesztek nélküli rész legfeljebb T1.
- Csak `safe` tesztek: a Jarvis `manual` markeres tesztjei (valódi mellékhatás: alkalmazásnyitás, hang, ElevenLabs) **soha**.

## 8. Frissítés

| Esemény | Teendő |
|---|---|
| a `HEAD` commit megváltozott | `git diff --name-only <régi>..<új>` → csak az érintett fájlok újraindexelése |
| munkakönyvtár-változás (mtime) | `dirty` darabok frissítése éjjel |
| fájl törölve / átnevezve | a darabok és a belőlük nyert snippetek törlése / áthelyezése |
| konfiguráció változott | konvenciókártyák újragenerálása |
| hetente | teljes újraépítés és összevetés (eltérés = hiba a növekményes frissítésben) |

## 9. Hatókör és adatvédelem

- A repóból tanult tudás `scope='own-repo'`: **helyben** marad (Auri Core SQLite), nem szinkronizálódik a felhős
  `brain_state`-be, és nem megy felhős modellhez a felhasználó kifejezett, kérésenkénti engedélye nélkül
  ([../08-modellek-es-utvonalvalasztas/03-felhos-segitseg-opcionalis.md](../08-modellek-es-utvonalvalasztas/03-felhos-segitseg-opcionalis.md)).
- Egy paranccsal törölhető repónként („felejtsd el a `server/`-t”).
- Licenc: `own` — de ha a repóba idegen kód került (vendorolt fájl), annak a licence öröklődik, vagy kimarad.

## 10. Kész, ha

- a teljes index egy **telepített kulcsokat tartalmazó** munkakönyvtáron fut le, és az indexben (szöveg, összefoglaló,
  beágyazás forrásszövege) **egyetlen** titok vagy `.env`-érték sincs — ellenőrző szkript keres rá;
- egy szándékosan elhelyezett hamis kulcs (tesztfájlban, fiktív értékkel) a fájl kizárását váltja ki, és a jelentés
  csak az útvonalat mutatja;
- a konvenciókártyák között ott van a Python-verzió, a `ruff`-sorhossz, a TS `strict` és a tesztmappák szerkezete;
- egy commit után a növekményes frissítés csak a változott fájlokat dolgozza fel, és a heti teljes újraépítéssel egyezik.

## Kapcsolódó

- [03-kod-tudasbazis.md](03-kod-tudasbazis.md) · [04-sandbox-kodfuttatas.md](04-sandbox-kodfuttatas.md) · [02-tananyag.md](02-tananyag.md)
- [../09-biztonsag-es-adatvedelem/01-alapszabalyok.md](../09-biztonsag-es-adatvedelem/01-alapszabalyok.md) · [../05-tanulas/05-mit-nem-szabad-megtanulni.md](../05-tanulas/05-mit-nem-szabad-megtanulni.md)
- [../07-komplex-feladatok/03-tobbfajlos-projektek.md](../07-komplex-feladatok/03-tobbfajlos-projektek.md) · [../01-architektura/04-tarolas-es-adatfolyam.md](../01-architektura/04-tarolas-es-adatfolyam.md)
