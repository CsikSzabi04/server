# Auri J.A.R.V.I.S. — helyi, ingyenes, hangvezérelt asszisztens

Windows-on, a saját gépeden fut (`127.0.0.1`), CPU-n. Felébred a **„Hey Auri”** szóra
(bejelentkezve választható a „Hey Jarvis”), gyorsbillentyűre vagy dupla tapsra; meghallgat
(Parakeet), gondolkodik (Ollama), cselekszik (allowlistes eszközök), és válaszol (ElevenLabs
„Daniel” vagy helyi Piper). A HUD a meglévő AuriGPT web `/jarvis` nézete.

- Specifikáció: [../jarvis_reboot_to_auri.md](../jarvis_reboot_to_auri.md)
- A 3 AI munkamegosztása és státusza: [../JARVIS_BUILD.md](../JARVIS_BUILD.md)

> Ez a README még váz (M0–M3). A teljes kézikönyv az M5-ben készül el.

## Telepítés

```powershell
cd D:\Projectss\Server\auri-jarvis
powershell -ExecutionPolicy Bypass -File .\scripts\setup_env.ps1
```

A szkript létrehozza a `.venv`-et (Python 3.12), telepíti a pinelt csomagokat
(`requirements.txt`), létrehozza a `.env`-et a `.env.example`-ből, **kiírja** az Ollama
rendszerszintű lépéseit (és csak jóváhagyásra futtatja), végül lefuttatja az önellenőrzést.

A HUD-hoz egyszer buildelni kell a webet: `cd ..\web; npm run build` (a daemon a `web/dist`-et
szolgálja ki).

## Indítás

| Parancs | Mit csinál |
|---|---|
| `.venv\Scripts\python -m auri_jarvis` | Hangmód: mikrofon + hangszóró + HUD (Chrome app-ablak a 3. monitoron) |
| `.venv\Scripts\python -m auri_jarvis --text` | Szöveges próba: a beírt sor a „beszéd”, a válasz kiíródik |
| `… --text --echo` | Ugyanez a valódi Mind nélkül (visszhang + idő) |
| `… --selftest` | Környezet-ellenőrzés: Ollama és modellek, mikrofon, Piper-hangok, STT-modell, kulcsok *megléte*, szabad port. Kreditet nem költ. |
| `… --no-hud` / `--no-window` / `--no-tray` | HUD-szerver nélkül / szerver igen, ablak nem / tálcaikon nélkül |

Hangmódban egyszerre csak **egy** daemon futhat (a mikrofon miatt); a második üzenettel kilép.

**Tálcaikon:** a színe az állapotot mutatja (cián: kész · világoskék: figyel · narancs:
gondolkodik · lila: töltődik · szürke: némítva · piros: hiba). Menü: Hallgatás · Némítás ·
HUD megnyitása · Kilépés.

**Automatikus indítás bejelentkezéskor** (Feladatütemező, a saját felhasználóddal, 30 s
késleltetéssel, konzolablak nélkül; rákérdez, mielőtt létrehozza):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_autostart.ps1             # be
powershell -ExecutionPolicy Bypass -File .\scripts\install_autostart.ps1 -Uninstall  # ki
```

Induláskor a daemon legfeljebb `core.ollama_wait_s` (60) másodpercig vár az Ollamára; addig a
HUD „Agy töltődik…” jelzést mutat, a hotkey közben is él.

**Mérés hang és kredit nélkül:** `.venv\Scripts\python scripts\smoke.py --n 20` (a valódi
Minddal; medián/p90 a `data/body/smoke-*.json`-ba), tartósteszt: `--soak 2h`.

HUD: <http://127.0.0.1:8790/#jarvis> (a daemon szolgálja ki, a token az oldalba kerül).
Fejlesztéskor a Vite-tal (`localhost:5173/#jarvis&token=…`) — fix tokenhez állítsd be a
`hud.dev_token`-t a `config/jarvis.yaml`-ben.

## Telepítő (letölthető desktop app)

A webes AuriGPT jobb alsó sarkában lévő **⬇ AURI** gomb a GitHub Release
`…/releases/latest/download/AuriSetup.exe` fájlját tölti le. A telepítő (≈35 MB, per-user,
rendszergazdai jog nélkül, `%LOCALAPPDATA%\Programs\Auri`) kicsomagolja az appot, `uv`-vel
felrakja a Python 3.12-t és a pinelt csomagokat, letölti a Piper-hangokat (Hugging Face,
sha256-ellenőrzéssel), opcionálisan a Parakeetet, az Ollamát és a nyelvi modellt, majd Start
menü / asztali parancsikont, bejelentkezéskori indítást és eltávolító bejegyzést készít.
Frissítés = az újabb telepítő futtatása (a `.env`, a `config/me.md` és a `data/` megmarad).

Kiadás:

```powershell
.venv\Scripts\python -m pip install -r installer\requirements-build.txt   # egyszer
.venv\Scripts\python installer\build_installer.py --web                    # → installer\dist\
```

Utána a GitHub-on új Release `auri-v<verzió>` címkével („Set as the latest release”),
feltöltve: `AuriSetup.exe` + `SHA256SUMS.txt` (szöveg: `RELEASE_NOTES.md`).
A build leáll, ha a csomagba titok (a helyi `.env`-ek kulcsértékei), `.env`, `data/` vagy
`config/me.md` kerülne. A csomag csak a publikus Supabase URL-t és a publishable kulcsot
tartalmazza (ugyanazt, amit a nyilvános web is).

## Bejelentkezés és vendég mód

- **Vendég (nincs bejelentkezve):** megszólítás „you” · „Hey Auri” · Daniel · nincs
  „Üdv itthon” rutin · nincs kérdés · nincs személyes adat (memória, emlékeztetők, projektek).
- **Bejelentkezve** (a HUD-on, az AuriGPT-fiókkal): első alkalommal Auri megkérdezi a
  megszólítást, az ébresztőszót, a hangot és az „Üdv itthon” rutint — hangon és a HUD-űrlapon is
  válaszolhatsz. A válaszok a Supabase-profilodba (`profiles.prefs.jarvis`) és helyben is
  mentődnek; a HUD ⚙ gombjával vagy „Auri, állítsuk be újra” mondattal újrakezdhető.
- Ehhez az `auri-jarvis/.env`-ben kell: `SUPABASE_URL`, `SUPABASE_ANON_KEY` (a publikus anon
  kulcs, ugyanaz, mint a web `VITE_SUPABASE_*`-ja — **soha** nem a service key).
- Offline: ha 7 napon belül már igazoltad magad, a daemon a helyi másolatból indul.

## Adatvédelem és biztonság (spec 8)

- Csak `127.0.0.1`-en figyel; Host- és Origin-ellenőrzés; induláskor generált token minden
  WS/REST kérésnél. Idegen weboldal nem tud parancsot küldeni.
- A mikrofon hangja nem kerül lemezre; a leírt szöveg alapból **nem** kerül a naplóba.
- A felhőbe (ElevenLabs) csak a kimondandó szöveg megy ki.
- Titkok csak a `.env`-ben; a naplóban maszkolva. A jelszó és a refresh token soha nem jut a
  daemonhoz; a bejelentkezési tokent csak ellenőrzi, nem tárolja.
- Adatok: `data/` (gitignore-olt) — `data/body/` naplók, időzítések, identitás-cache.

## Fejlesztés

```powershell
.venv\Scripts\python -m pytest            # minden zóna (a `manual` jelölésűek nélkül)
.venv\Scripts\python -m pytest tests/body # csak a BODY (AI-3)
.venv\Scripts\ruff check .
```

Zónák (ki mit szerkeszt): [JARVIS_BUILD.md 1. szakasz](../JARVIS_BUILD.md). Új csomag csak az
AI-3-on keresztül (5. szakasz). Közös típusok: `auri_jarvis/contracts.py`.

## Hibaelhárítás

| Tünet | Teendő |
|---|---|
| `--selftest`: „Ollama nem érhető el” | Indítsd el az Ollamát; telepítés: spec 10. fejezet |
| „127.0.0.1:8790 foglalt” | Már fut egy daemon (tálca / Feladatkezelő), vagy más használja a portot |
| A HUD „NINCS TOKEN” | A daemon által kiszolgált oldalt nyisd meg: <http://127.0.0.1:8790/#jarvis> |
| Bejelentkezés: „nincs beállítva” | `SUPABASE_URL` + `SUPABASE_ANON_KEY` az `auri-jarvis/.env`-be |
