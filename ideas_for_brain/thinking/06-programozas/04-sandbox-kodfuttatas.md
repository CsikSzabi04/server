# Sandbox — az ellenőrző: kód futtatása biztonságosan, Windowson

> **Miről szól:** a gondolkodó ciklus „Ellenőrzés” lépésének motorja: TS/JS, Python és SQL kód futtatása
> időkorláttal, memóriakorláttal, ideiglenes mappában, hálózat nélkül. Őszinte összevetés a Windows-os
> izolációs lehetőségekről, lépcsőzetes javaslat, Job Object-limitek, engedélyek, eredményformátum, szökési próbák.

## 1. Kitől védünk (fenyegetési modell)

| Veszély | Példa | Valószínűség |
|---|---|---|
| **Baleset** a modell kódjában | végtelen ciklus, memóriazabálás, `rm` rossz útvonallal, rekurzió | **gyakori** — kis modell, sok próbálkozás |
| **Mellékhatás** | fájlírás a projektbe, hálózati hívás, vágólap, folyamatindítás | időnként |
| **Ártó kód** | webről vagy idegen repóból átvett kód, prompt-injekcióval „rávett” modell | ritka, de a legsúlyosabb |

Következmény: a **saját feladatra generált** kódnak elég egy balesetek elleni gyors korlát (S0); minden
**idegen eredetű** kódhoz valódi izoláció kell (S1). Részletek: [../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md](../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md).

## 2. Kiinduló állapot ezen a gépen (ellenőrizve 2026-11-21)

Windows 10 Pro 19045 · Node v24.14.0 · Python 3.12.6 · TypeScript 5.9.3 (`web/node_modules`) · **nincs** Docker
a PATH-on · **nincs** telepített WSL-disztribúció. Minden más ebben a fájlban terv vagy becslés.

## 3. Lehetőségek összevetése

| Szint | Megoldás | Izoláció | Indulás / futás | RAM-többlet | Telepítés |
|---|---|---|---|---|---|
| **S0** | korlátozott alfolyamat: Job Object + futási mappa + tiszta env + tűzfalszabály + futtatókörnyezeti korlátok | balesetek ellen jó; **nem** biztonsági határ ártó kód ellen | ~azonnali (becslés: < 1 s) | ~0 | egyszeri admin a tűzfalszabályhoz |
| S0+ | S0 külön, alacsony jogú Windows-felhasználóval (NTFS-tiltás a `D:\Projectss`-re és a profilra) | fájlrendszer-határ is | ~azonnali | ~0 | felhasználó + ACL, jelszókezelés (mérni/kipróbálni) |
| **S1** | WSL2 + saját disztró + `bubblewrap` (`--unshare-all`: nincs hálózat) + `prlimit`/cgroup | Linux-névterek: erős | WSL-hidegindítás másodpercek (becslés), utána futásonként kicsi | `.wslconfig`-gal korlátozható (pl. 3 GB) | `wsl --install` (admin, újraindítás), lemez: GB-ok |
| S1' | Docker Desktop: `--network none --memory --pids-limit --read-only --cap-drop ALL` | konténer: erős | konténerenként ~1–2 s (becslés) | jelentős (becslés: 1–2 GB, WSL2-n fut) — versenyez az Ollamával | Docker Desktop telepítés |
| S2 | Windows Sandbox (`.wsb`: `<Networking>Disable</Networking>`, csak olvasható mappák) | eldobható VM: legerősebb | indulás tíz másodpercek (becslés), egyszerre egy példány | GB-ok | `Enable-WindowsOptionalFeature -Online -FeatureName Containers-DisposableClientVM` |

## 4. Javasolt lépcsőzés

| Fázis | Mit vezetünk be | Mire szabad használni |
|---|---|---|
| **P0** | **S0** | csak Auri **saját** generálású kódja, saját/kurált feladatokra |
| P1–P2 | **S1** (WSL2 + bubblewrap; Docker csak ha a mérés szerint belefér a 16 GB-ba) | minden idegen eredetű kód, `npm`/`pip` csomagot igénylő kód, saját repók tesztjei |
| bármikor | S2, kézzel | teljes idegen projekt kipróbálása, ritkán |

| A kód eredete | Minimum szint | Kockázat (a Jarvis-regiszter mintájára) |
|---|---|---|
| Auri generálta saját feladatra | S0 | `safe` |
| a felhasználó beillesztett kódja | S0 megerősítéssel; S1, ha van | `confirm` |
| webről / idegen repóból, telepítést igényel | **S1** (S0-ban tilos) | `confirm` |
| a felhasználó saját repójának tesztjei ([07](07-sajat-projektekbol-tanulas.md)) | S1, allowlistes fájlmásolattal | `confirm`, `min_tier='user'` |

## 5. S0 részletesen — rétegek

**a) Job Object** (a futtató a gyerekfolyamatot `CREATE_SUSPENDED`-del indítja, a jobhoz rendeli, majd folytatja —
így nincs rés az indulás és a korlátozás között). Kiinduló értékek, **mérni kell**:

| Korlát | Érték (L0–L2) | Mire jó |
|---|---|---|
| `JOB_OBJECT_LIMIT_PROCESS_MEMORY` / `JOB_MEMORY` | 512 MB / 1 GB | memóriabomba → `oom` |
| `JOB_OBJECT_LIMIT_ACTIVE_PROCESS` | 8 | folyamatbomba ellen |
| `JOB_OBJECT_LIMIT_PROCESS_TIME` (CPU-idő) | 30 s | pörgő ciklus |
| falióra-időkorlát (a futtatóban) + `TerminateJobObject` | L0–L1: 20 s · L2: 60 s · L3: 180 s | elakadás → `timeout` |
| `JOB_OBJECT_LIMIT_PRIORITY_CLASS` + CPU-ráta-korlát | BELOW_NORMAL, ≤ 50 % | a gép használható marad |
| `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, `DIE_ON_UNHANDLED_EXCEPTION` | be | nincs árva folyamat, nincs hibaablak |
| UI-korlátok (`JOB_OBJECT_UILIMIT_*`: vágólap olvasás/írás, asztal, kijelentkezés, rendszerbeállítás) | mind be | vágólap és UI érintetlen |

A Job Object **nem** korlátozza a fájlrendszert, a registryt és a hálózatot — ezért kellenek a további rétegek.

- **b) Futási mappa:** `%LOCALAPPDATA%\Auri\sandbox\runs\<runId>\` — a projektmappán **kívül**; futás után törlés.
- **c) Tiszta környezet:** üres env-ből csak `SystemRoot`, `PATH` (csak a sandbox-futtatókörnyezet), `TEMP`/`TMP`/
  `USERPROFILE`/`HOME` = futási mappa, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONHASHSEED=0`. Semmilyen kulcs
  (Groq, Gemini, Supabase, ElevenLabs), semmilyen `OLLAMA_*` nem jut át.
- **d) Külön futtatókörnyezet:** `C:\AuriSandbox\runtime\` — saját `node.exe` másolat + vendorolt csomagok
  (`typescript`, `fast-check`), és **beágyazható (embeddable) Python**, benne `pytest`, `hypothesis`. Nem venv: a
  Windows-os venv `python.exe` csak indító, a valódi folyamat az alap-értelmező lenne, és arra nem vonatkozna a
  tűzfalszabály (**ellenőrizni kell**). Futásidőben nincs `npm install` / `pip install`.
- **e) Hálózat:** egyszeri, adminos tűzfalszabály a sandbox-értelmezőkre:
  `New-NetFirewallRule -DisplayName "Auri sandbox python" -Direction Outbound -Action Block -Program "C:\AuriSandbox\runtime\py\python.exe"`
  (ugyanígy a `node.exe`-re). A loopback-forgalmat a Windows-tűzfal jellemzően nem szűri — az L3 API-tesztekhez ez jól
  jön, de **ellenőrizni kell**.
- **f) Futtatókörnyezeti korlátok:** Node: `--permission --allow-fs-read=<RUN>,<RT> --allow-fs-write=<RUN>` (tiltja a
  gyerekfolyamatot és a futási mappán kívüli fájlelérést; a hálózatot a v24 permission modellje nem korlátozza —
  ellenőrizni). Python: `boot.py` `sys.addaudithook`-kal blokkolja az `open`-t a futási mappán és a runtime-on kívül,
  a `socket.connect`, `subprocess.Popen`, `os.system`, `ctypes.dlopen`, `winreg.*` eseményeket. **Mindkettő
  „biztonsági öv”, nem határ** (a dokumentációjuk is így mondja).
- **g) Statikus előszűrés:** tiltólista (`child_process`, `node:net`, `worker_threads`, `eval`, `new Function`,
  abszolút út / `..`; Pythonban `subprocess`, `socket`, `ctypes`, `winreg`, `shutil.rmtree`, `multiprocessing`) →
  `blocked` státusz **okkal**, amit a modell visszajelzésként kap („ne használj hálózatot, mockold”).

```python
# sandbox/runner.py — S0 vázlat (pywin32; a mezőneveket implementáláskor ellenőrizni)
def run(cmd: list[str], run_dir: str, env: dict, lim: Limits) -> dict:
    job = make_job(lim)                                   # 5a táblázat
    p = subprocess.Popen(cmd, cwd=run_dir, env=env, stdout=PIPE, stderr=PIPE,
                         creationflags=win32process.CREATE_SUSPENDED | subprocess.CREATE_NO_WINDOW)
    win32job.AssignProcessToJobObject(job, p._handle)
    resume(p)                                             # NtResumeProcess (ctypes)
    t0, status = time.perf_counter(), "done"
    try:
        out, err = p.communicate(timeout=lim.wall_s)
    except subprocess.TimeoutExpired:
        win32job.TerminateJobObject(job, 1); out, err = p.communicate(); status = "timeout"
    acct = win32job.QueryInformationJobObject(job, win32job.JobObjectExtendedLimitInformation)
    return {"status": status, "exit": p.returncode, "stdout": out, "stderr": err,
            "ms": int((time.perf_counter() - t0) * 1000), "peak": acct["PeakJobMemoryUsed"]}
```

A futtató **külön folyamat**, JSON-t ír a stdoutra — így független attól, milyen nyelven készül az Auri Core
([../01-architektura/03-hol-fut-auri-core.md](../01-architektura/03-hol-fut-auri-core.md)).

## 6. Nyelvenkénti futtatás

| Nyelv | Statikus lépés | Futtatás | Riport |
|---|---|---|---|
| TS | `tsc --noEmit` (`strict`, `allowImportingTsExtensions`, `module: nodenext`, `erasableSyntaxOnly` — TS 5.8+, az 5.9.3 tudja) | `node --permission … --test-reporter=junit --test-reporter-destination=report.xml solution.test.ts` — a Node 24 típuslecsupaszítása csak „törölhető” TS-szintaxist futtat (enum, namespace nem) | JUnit XML |
| JS | `node --check` | ugyanígy | JUnit XML |
| Python | `ruff check` | `python -I -X utf8 boot.py -m pytest -q -p no:cacheprovider --junitxml=report.xml`; `py.io` témáknál egy második futás `-X utf8` **nélkül** is (a Windows-kódlap hibái csak így jönnek elő, [06](06-hibakereses.md)) | JUnit XML |
| SQL | — | Python `sqlite3` `:memory:`: séma + fixture + lekérdezés, eredményhalmaz-összevetés (ORDER BY nélkül sorrendfüggetlenül) | saját JSON |

A `--test-reporter` közvetlen fájlfuttatásnál és a `--permission` melletti viselkedését v24.14.0-n **ellenőrizni kell**
(a `node --test` alapból fájlonként gyerekfolyamatot indít, amit a permission modell tilt).

## 7. Eredményformátum

```ts
interface RunResult {
  runId: string;
  status: 'pass' | 'fail' | 'error' | 'timeout' | 'oom' | 'blocked';
  phase: 'static' | 'typecheck' | 'test';           // hol állt meg
  tests: { name: string; ok: boolean; message?: string; expected?: string; actual?: string }[];
  passed: number; failed: number;
  stdout: string; stderr: string;                   // ANSI nélkül, futási út → '<RUN>', max 8 KB a modellnek
  blockedReason?: string;                           // statikus szűrő / audit hook / permission
  durationMs: number; peakMemMb?: number; exitCode: number | null;
  sandbox: 'S0' | 'S0+' | 'S1' | 'S2'; env: { node?: string; python?: string; typescript?: string };
  testsHash: string;                                // a befagyasztott tesztek hash-e (05)
}
```

## 8. Szökési próbák (a sandbox saját tesztkészlete)

| Próba | Elvárt S0-ban | Elvárt S1-ben |
|---|---|---|
| végtelen ciklus | `timeout`, nincs árva folyamat | `timeout` |
| 4 GB lefoglalása | `oom` | `oom` |
| 100 gyerekfolyamat | `blocked`/limit | pids-limit |
| `fetch('https://example.com')` / `socket.connect` | hiba (tűzfal + audit) | nincs hálózat |
| írás `D:\Projectss\...` alá | Node: permission tiltja; Python: audit hook tiltja | nem látszik a fájl |
| `.env` olvasása abszolút úttal | tiltva, de **ismert rés**: ártó kód megkerülheti → S0+ zárja | nem látszik |
| vágólap olvasása | UI-korlát tiltja | nincs vágólap |
| `cmd.exe` indítása | `blocked` | a konténeren belül maradhat |

## 9. Kész, ha

- a 8. pont próbái automatikusan futnak, és mindegyik az elvárt státuszt adja (az ismert rés dokumentálva);
- 100 egymás utáni futás után nincs árva folyamat és nincs maradék futási mappa;
- egy L1-es TS- és Python-tesztfuttatás sandbox-overheadje mérve van (célérték: < 1,5 s a teszteken felül);
- a `RunResult` minden mezője kitöltődik, a stdout/stderr normalizált, és nem tartalmaz felhasználói útvonalat.

## Kapcsolódó

- [05-tesztvezerelt-gondolkodas.md](05-tesztvezerelt-gondolkodas.md) · [06-hibakereses.md](06-hibakereses.md) · [07-sajat-projektekbol-tanulas.md](07-sajat-projektekbol-tanulas.md)
- [../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md](../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md) · [../09-biztonsag-es-adatvedelem/01-alapszabalyok.md](../09-biztonsag-es-adatvedelem/01-alapszabalyok.md)
- [../01-architektura/03-hol-fut-auri-core.md](../01-architektura/03-hol-fut-auri-core.md) · [../11-utemterv/03-nyitott-kerdesek.md](../11-utemterv/03-nyitott-kerdesek.md)
