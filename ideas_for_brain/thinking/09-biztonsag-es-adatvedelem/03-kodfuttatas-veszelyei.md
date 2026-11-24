# A kódfuttatás veszélyei — mi romolhat el, mi véd, mit nem futtatunk soha magától

> **Miről szól:** a generált vagy letöltött kód futtatásának kockázatai **ezen a gépen** (Windows,
> 16 GB RAM, egy Ollama-sáv, kulcsok `.env`-fájlokban), a védelmi rétegek, egy kártékony próbakészlet,
> és a lista arról, mi nem futhat automatikusan. A sandbox megvalósítása:
> [../06-programozas/04-sandbox-kodfuttatas.md](../06-programozas/04-sandbox-kodfuttatas.md).

## 1. Miért kell komolyan venni

- A kód forrása egy kis helyi modell (téved, csomagneveket hallucinál), a web és a dokumentáció
  (injekció lehet benne, ld. [02-prompt-injekcio.md](02-prompt-injekcio.md)), vagy a felhasználó projektje.
- Ugyanezen a gépen van a teljes forráskód (`d:\Projectss\Server`), API-kulcsok (`auri-jarvis/.env`,
  `web/.env*`), a böngészőprofil, és fut a Jarvis meg az Ollama.
- Egyetlen hiba: adatvesztés, kiszivárgott kulcs, vagy lefagyott gép, miközben a felhasználó dolgozik.

## 2. Kockázatok

| Kockázat | Példa generált kódban | Kár |
|---|---|---|
| Fájlírás/törlés | `shutil.rmtree(path)` rossz útvonallal; írás a `../../.env`-be; symlink vagy junction a munkamappából kifelé | adatvesztés, felülírt projekt |
| Fájlolvasás | `~/.ssh/…`, `.env`, böngészőprofil beolvasása | titok kiszivárgása |
| Hálózat | `requests.post(url, data=dict(os.environ))`; második lépcsős letöltés; LAN-pásztázás | adatkiküldés, fertőzés |
| Örökölt környezet | a gyerekfolyamat megkapja a szülő változóit (`GROQ_API_KEY`…) | kulcs egy `print(os.environ)`-nel kint van |
| Folyamatrobbanás | `subprocess.Popen` ciklusban, Node `child_process` láncban | a gép megáll |
| Végtelen ciklus | `while x != 0.3: x += 0.1` | 100% CPU, az Ollama-sáv éhezik |
| Memória | `[0] * 10**10`, mély rekurzió | 16 GB elfogy, lapozás, a Jarvis is lelassul |
| Lemez | ciklusban írt nagy fájl | megtelt lemez |
| Tartós beépülés | Startup mappa, `HKCU\…\Run`, ütemezett feladat, PowerShell-profil | minden indításkor lefut |
| Telepítési szkript | npm `postinstall`, `setup.py` | tetszőleges kód már a telepítéskor |
| Ellátási lánc | hallucinált vagy elírt csomagnév (typosquat) | rosszindulatú csomag |
| Rendszerparancs | `shutdown /s`, `taskkill /im ollama.exe`, `reg add`, `bcdedit` | szolgáltatások, gép leáll |
| Interaktív elem | `input()` örökké vár; felugró ablak; vágólap olvasása | lógás, adatszivárgás |

## 3. Védelmi rétegek

```
L0 előszűrés ─▶ L1 izolált folyamat ─▶ L2 erőforrás-korlátok ─▶ L3 tiszta környezet ─▶ L4 eredmény-kezelés
(heurisztika)    (a valódi határ)        (idő, CPU, RAM, PID)      (env, munkamappa)       (kimenet = adat)
```

**L0 — előszűrés.** AST/regex keresi: `subprocess`, `os.system`, `ctypes`, `winreg`, `socket`,
`child_process`, `Remove-Item -Recurse`, `rm -rf`, munkamappán kívüli abszolút útvonal. **Nem
biztonsági határ** — csak korai figyelmeztetés és érthetőbb hibaüzenet a modellnek.

**L1 — izoláció.** A döntés a 06-os sandbox-fájlé; a lehetőségek ezen a gépen:

| Megoldás | Erősség | Ár | Megjegyzés |
|---|---|---|---|
| WSL2 + konténer (`--network none --read-only --memory --pids-limit --cpus`) | erős | WSL2/Docker kell, RAM | **nyitott kérdés:** telepítve van-e |
| Windows Sandbox | erős | lassú indulás, sok RAM | Pro kiadáson elérhető; minden futás új VM |
| Külön, korlátozott Windows-felhasználó + Job Object + tűzfalszabály | közepes | olcsó | P0-hoz elég lehet (becslés), ha L2–L3 szigorú |

**L2 — korlátok** (kiinduló értékek, **becslés**):

| Korlát | Érték |
|---|---|
| Falióra-idő | 10 s tesztfutásonként (P0); 60 s projekt-tesztkészletre (P5) |
| CPU | 2 mag |
| Memória | 1 GB |
| Folyamatok | legfeljebb 32 |
| Kimenet | stdout + stderr legfeljebb 1 MB, a többi levágva |
| Lemez | legfeljebb 100 MB a munkamappában |
| Hálózat | nincs |
| stdin | lezárva (azonnali EOF) |

Időtúllépéskor a **teljes folyamatfa** leáll (Job Object `KILL_ON_JOB_CLOSE`, illetve konténer-leállítás),
nem csak a szülő.

**L3 — tiszta környezet.** Üres környezeti változók; csak az értelmező `PATH`-ja; `HOME` és `TEMP` a
munkamappa. A munkamappa minden futásnál új ideiglenes mappa; a projektfájlok **másolatként** kerülnek
be, írható csatolás nincs. Tiltott másolni: `.env*`, `*.pem`, `*.key`, `id_*`, `secrets*`, `*.sqlite`.

**L4 — eredmény.** A stdout/stderr `taint: tool` adat — injekció lehet benne. Csak a munkamappából
jöhet ki fájl, utána a mappa törlődik.

## 4. Amit soha nem futtatunk automatikusan (akkor sem, ha a tesztek zöldek)

1. Bármit a valódi projektmappában vagy a felhasználó fájljain — csak diffként, jóváhagyással.
2. Csomagtelepítést a sandboxon kívül (`npm install`, `pip install`) — a valódi projektben csak
   jóváhagyás után, a lock-fájl változását megmutatva.
3. Letöltött szkriptet: `curl … | sh`, `iwr … | iex`, webes `.bat`, `.ps1`, `.exe`.
4. Webről, dokumentációból, kommentből vagy hibaüzenetből javasolt parancsot.
5. Git-műveletet valódi repón: `commit`, `push`, `reset --hard`, `clean -fd`.
6. Rendszergazdai jogot, registry-, szolgáltatás-, ütemezőfeladat-, tűzfal- vagy Defender-módosítást.
7. Leállítást, újraindítást, `format`, `diskpart`, `bcdedit`, folyamatok leállítását.
8. Migrációt vagy lekérdezést valódi adatbázison (Supabase); felhős API-hívást valódi kulccsal.
9. Üzenetküldést, e-mailt, közzétételt (`npm publish`, deploy).
10. Konténert host-csatolással, `--privileged` módban vagy hálózattal.

A valódi gépen futtatás csak a Jarvis `confirm` szintű eszközein át vagy a felhasználó saját kezével történhet.

## 5. Kártékony próbakészlet — a sandbox saját tesztje

| Próba | Elvárt eredmény |
|---|---|
| folyamatrobbanás | `killed` (PID-korlát), a gép reagál |
| végtelen ciklus | `timeout`, a folyamatfa eltűnik |
| 10 GB lefoglalása | `oom` |
| `~/.ssh` vagy `d:\Projectss\Server\web\.env` olvasása | `denied` / nem létezik |
| írás a `..\..\` útvonalra, symlinkes kitörés | `denied`, a munkamappán kívül semmi nem változik |
| HTTP-kérés az `example.com`-ra | hálózati hiba |
| `print(os.environ)` | a kimeneten a `containsSecret` hamis |
| háttérfolyamat, ami túlélné a szülőt | a futás végén nincs maradék folyamat |
| `taskkill /im ollama.exe` | sikertelen; az Ollama és a Jarvis fut tovább |
| `input()` | azonnali EOF, nem lóg |

## Kész, ha

- a próbakészlet 100%-ban zöld, része a biztonsági kiértékelésnek
  ([../10-meres-es-fejlodes/02-ertekelo-keszletek.md](../10-meres-es-fejlodes/02-ertekelo-keszletek.md)), és minden sandbox-változtatás előtt lefut;
- minden futás után törlődik a munkamappa, és nem marad folyamat;
- a 4. pont tiltásait a K4/K5 kapu kódja érvényesíti, kategóriánként legalább egy teszttel
  ([01-alapszabalyok.md](01-alapszabalyok.md));
- sandbox-futás közben a felhasználó első kérésének késése mérve van, és nem nő érdemben (mérni kell).

## Kapcsolódó

- [../06-programozas/04-sandbox-kodfuttatas.md](../06-programozas/04-sandbox-kodfuttatas.md) · [../06-programozas/06-hibakereses.md](../06-programozas/06-hibakereses.md)
- [01-alapszabalyok.md](01-alapszabalyok.md) · [02-prompt-injekcio.md](02-prompt-injekcio.md)
- [../07-komplex-feladatok/03-tobbfajlos-projektek.md](../07-komplex-feladatok/03-tobbfajlos-projektek.md) · [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md)
