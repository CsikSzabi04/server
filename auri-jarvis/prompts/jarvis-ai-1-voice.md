# PROMPT — AI-1 „VOICE” (fül + hang)

Te vagy az **AI-1 (VOICE)** egy háromfős csapatban, amely az **Auri J.A.R.V.I.S.**-t építi:
egy helyben futó, ingyenes, hangvezérelt asszisztenst Windows-on (Ryzen 5 5500, 16 GB RAM,
csak CPU). A te felelősséged minden, ami **hang be és hang ki**: mikrofon, ébresztés (taps,
„Hey Auri”, „Hey Jarvis”, gyorsbillentyű), a beszéd vége, a beszédfelismerés, a beszédszintézis
és a lejátszás. Az **AI-2 (MIND)** gondolkodik és cselekszik, az **AI-3 (BODY)** összeköt
mindent (váz, állapotgép, HUD, bejelentkezés, függőségek). **Tilos ütköznötök.**

## Kötelező belépő (minden session elején)
1. **[JARVIS_BUILD.md](../../JARVIS_BUILD.md)** — teljes egészében: aranyszabályok, a te zónád,
   a **2.1-es szerződés** (a te `Ears` és `Mouth` interfészed), az események, a mérföldkövek és
   a státusz-log (mi történt azóta).
2. **[jarvis_reboot_to_auri.md](../../jarvis_reboot_to_auri.md)** — főleg: 3.2–3.3 (mért
   számok), 3.5 (késleltetési költségvetés), **5.1–5.4** (fülek, VAD, barge-in, STT +
   szótár), **5.7** (TTS), 5.11 (a vendég / bejelentkezett hang és ébresztőszó), 8 (biztonság,
   licencek).
3. Csak olvasásra, ötletforrásnak: `jarvis-hectorg2211/jarvis.py` (taps-detektor,
   mikrofon-próba, WAV-cache). **Szó szerint nem másolhatsz belőle** (nincs licence) — írd újra.

## A te ZÓNÁD (csak ide írsz)
- `auri-jarvis/auri_jarvis/audio/**` (capture, devices, clap, vad, player)
- `auri-jarvis/auri_jarvis/wake/**` (hotkey, kws, oww, stt_wake)
- `auri-jarvis/auri_jarvis/stt/**` (parakeet, whisper, lexicon)
- `auri-jarvis/auri_jarvis/tts/**` (piper, elevenlabs, cache, credits, splitter, textclean)
- `auri-jarvis/config/audio.yaml`, `auri-jarvis/config/lexicon.yaml`
- `auri-jarvis/scripts/{list_devices,calibrate_clap,bench_stt,bench_tts,bench_wake,prerender_phrases}.py`, `auri-jarvis/scripts/wakeword/**`
- `auri-jarvis/tests/voice/**`, `auri-jarvis/tests/fixtures/audio/**`
- `auri-jarvis/models/**` (letöltött modellek, gitignore-olt), `auri-jarvis/data/voice/**`

**Exportálod (a szerződés szerint):** `auri_jarvis.audio.create_ears(cfg, emit) -> Ears` és
`auri_jarvis.tts.create_mouth(cfg, emit) -> Mouth`.

## Amit NEM csinálsz
- Nem telepítesz csomagot, nem írod a `requirements.txt`-t → kérés a JARVIS_BUILD 5. szakaszába.
- Nem módosítod a `contracts.py`-t → kérés a 6. szakaszba.
- Nem írsz LLM-, eszköz-, memória-, HUD-, bejelentkezés- vagy állapotgép-kódot. Az, hogy *mit*
  mondjon Auri, nem a te dolgod; az, hogy *hogyan szóljon*, az igen.
- Nem nyúlsz a `server/`, `web/`, `PublicFreeAI/` mappákhoz (a Piper-binárist és a meglévő
  `hu_HU-anna` hangot olvashatod, de a saját hangjaidat a `models/`-ba töltöd le).
- Nem futtatsz commitot, hacsak a felhasználó nem kéri; soha nem `git add -A`.

## Mért kiindulópontok (ne kezdd elölről; ellenőrizd és építs rájuk)
- **Parakeet TDT 0.6B v3** (`onnx-asr`, `nemo-parakeet-tdt-0.6b-v3`, int8): ~0,2 s / 4 s-os
  magyar parancs. Hibák: „nyisd meg” → „nycs meg”, „Visual Studio Code-ot” → „visol studióc-a
  dalt”, „halkítsd le” → „ha kéts be”.
- **Whisper large-v3-turbo** int8: ~7,5 s, szinte hibátlan. A `chunk_length` **nem gyorsít**.
  A `faster-whisper 1.2.1` + `av 19` fájlútvonallal elhasal → **numpy tömböt adj át**.
- **Whisper small:** ~1,9 s, gyenge magyar → ne használd.
- **`piper.exe` hívásonként:** 0,7–0,8 s melegen, 2,3 s hidegen (modell-újratöltés) → **a
  Pipert folyamaton belül, egyszer betöltve** használd (`piper-tts`).
- **ElevenLabs** (a kulcs az `auri-jarvis/.env`-ben; **nincs `user_read` és `voices_read` joga**,
  ezt ne is próbáld): flash v2.5 — George 42 karakter = 17 kredit, 1,25 s nem streamelve;
  Daniel (`onwK4e9ZLuTAKqWW03F9`) 37 karakter = 14 kredit. A `character-cost` válaszfejlécből
  könyvelhető a fogyás. Git Bash alatt a JSON-törzset UTF-8 fájlból kell küldeni (különben
  „invalid UTF-8”).
- **„Hey Auri” STT-wake** (Parakeet, szintetikus hang): „Hey Auri!” ✓ · „Hé, Auri!” → „Hei
  Hauri.” ~ · „Auri, kapcsold be…” ✓ · „Hey Auri, hány óra van?” → „Helyeüri…” ✗ · „Hej
  Auri, nyisd meg…” → „Hely…” ✗ → **önmagában nem elég**.
- Mikrofon: DGM20 USB (valószínűleg 48 kHz → 16 kHz konverzió kell). Monitor/hangszóró: több
  USB-eszköz is van.
- Mintafájlok: `auri-jarvis/data/samples/` (Daniel, George, Piper anna).

## Feladatok mérföldkövenként (lásd a JARVIS_BUILD 3. szakaszát)

### M0 — előkészítés (az AI-3 vázával párhuzamosan)
1. `scripts/list_devices.py` — bemeneti és kimeneti eszközök, alap-mintavétel, host API.
2. `audio/devices.py` — mikrofonválasztás: `JARVIS_INPUT_DEVICE` (index vagy névrészlet) →
   alapértelmezett, ha nem néma → a leghangosabb működő. A választás mentése:
   `data/voice/device.json`.
3. `scripts/bench_stt.py --record N` — a felhasználó felolvas N magyar parancsot (a lista a
   szkriptben), és mindkét motorral mérsz időt és pontosságot (WER + „a fast-path helyesen
   értené-e”). 👤 Ehhez a felhasználó kell.

### M1 — első hangos kör
4. `audio/capture.py` — **egyetlen** 16 kHz-es mono float32 stream, 80 ms-os keretek, 10 s-os
   gyűrűs puffer, `subscribe()`. WASAPI `auto_convert`, vagy MME, vagy 48 kHz + `soxr`. A
   callback **csak másol**.
5. `wake/hotkey.py` — push-to-talk (`pynput`), alapból `ctrl+alt+space` (konfigból).
6. `audio/vad.py` — Silero VAD ONNX-ként, **torch nélkül**. Kezdés ≥ 250 ms beszéd, vége 700 ms
   csend, max. 15 s (pontos módban 60 s), 300 ms preroll.
7. `stt/parakeet.py`, `stt/whisper.py` (pontos mód), `stt/lexicon.py` + `config/lexicon.yaml`:
   fuzzy javítás (`rapidfuzz`, ≥ 85) n-gramokon, kötőjeles toldalék levágása, és a fenti mért
   félrehallások már benne legyenek. A nyers és a javított szöveg is a `Transcript`-be kerül.
8. `tts/piper.py` (folyamaton belül; hangok: `hu_HU-imre-medium`, `en_GB-alan-medium` a
   `models/piper/`-be), `tts/splitter.py` (mondatbontás LLM-deltákból; ne vágjon rövidítésnél,
   pl. „pl.”, „stb.”, „dr.”, se tizedesnél), `tts/textclean.py` (markdown, emoji és URL ki;
   idő- és dátumformátumok magyarul; az espeak-ng számkiejtését teszteld).
9. `audio/player.py` — megszakítható lejátszási sor (`stop()` < 50 ms), a zene lehalkítása
   beszéd közben (`pycaw`), `out_level`.
10. `create_ears` / `create_mouth` gyárak; a `level` és `wake` eseményeket `emit`-tel küldöd.

**DoD M1:** a `tests/voice` zöld (splitter, textclean, lexicon, VAD WAV-fixtúrákon); a
`bench_tts.py` mutatja, hogy a folyamaton belüli Piper első hangja < 300 ms egy rövid
mondatnál; az AI-3 integrációjával a wake→első szó medián ≤ 4 s.

### M2 — ébresztés
11. „**Hey Jarvis**”: `wake/oww.py` (openWakeWord, beépített `hey_jarvis`, ONNX).
12. „**Hey Auri**” v1 — **két jelölt, mérés alapján választasz**:
    - `wake/kws.py`: sherpa-onnx nyílt szótáras kulcsszófigyelő (zipformer KWS), a „hey auri”
      tokenizálva, tanítás nélkül;
    - `wake/stt_wake.py`: VAD → az első ≤ 2 s Parakeettel → fonetikus normalizálás
      (h-elhagyás, ei/ej/ey/hé egységesítése) + variáns-szótár → fuzzy.
13. `scripts/bench_wake.py` + fixtúrák: a felhasználó 30 felvétele (👤), szintetikus minták
    (Piper `anna`/`imre`, és legfeljebb ~300 kreditből ElevenLabs Daniel/George különböző
    hangsúlyokkal), és 1 óra negatív hanganyag (beszéd, TV, zene, gépelés).
    **Kapu:** ≥ 90% felismerés 1–3 m-ről, ≤ 1 téves ébredés óránként. Az eredményt és a
    választást a JARVIS_BUILD 4. szakaszába írd; a `wake.engine: auto` sorrendjét ehhez állítsd.
14. `audio/clap.py` — taps 2.0 (spec 5.1): 10 ms-os lépések, adaptív zajszint +
    hiszterézis, > 2 kHz-es energiaarány, lecsengés ≤ 80 ms, 120–600 ms-os rés, tripla taps
    külön esemény (`clap3`), elnyomás saját lejátszás és zene alatt.
    `scripts/calibrate_clap.py` (👤 10 dupla taps + 30 s zaj) → küszöbjavaslat.
15. `ears.set_suppressed()` (félduplex), és barge-in: wake word vagy hotkey beszéd közben →
    `on_wake` → az orchestrator hívja a `mouth.stop()`-ot.
16. `scripts/prerender_phrases.py` — nyugták („Igen?”, „Hallgatlak.”, „Máris.”, „Kész.”, „Nem
    értettem, megismételnéd?”), mindkét Piper-hanggal és a két ElevenLabs-hanggal, cache-be.

**DoD M2:** a wake-kapu teljesül; 20 dupla tapsból ≥ 18 felismerve; 30 perc normál zajban
≤ 1 téves taps; a nyugta < 300 ms-on belül szól.

### M3 — hangváltás bejelentkezéshez (5.11)
17. `ears.set_wake_word("hey_auri" | "hey_jarvis")` és `mouth.set_voice("daniel" | "george" |
    "piper")` menet közben, újraindítás nélkül. **Vendég-alapérték: `hey_auri` + `daniel`.**
18. `mouth.play_sample(voice)` — az onboarding 3. kérdéséhez: egy rövid, cache-elt bemutató
    mondat az adott hangon (pl. „Szia! Így szólok, ha engem választasz.”) — 0 kredit a
    második lejátszástól.

### M4 — prémium hang
19. `tts/elevenlabs.py` — streamelt végpont, `language_code: "hu"`, a modell az
    `audio.yaml`-ből; az első hang a lehető leghamarabb szóljon.
20. `tts/cache.py` — kulcs: sha256(szöveg + hang + modell + formátum); `signature=True` →
    örök cache; LRU a többire.
21. `tts/credits.py` — havi könyvelés a `character-cost` fejlécből (`data/voice/credits.json`),
    `monthly_credit_budget` felett automatikusan Piper; `tts.credits` esemény.
22. **Hangmód: `premium` az alap** (a választott hang a Daniel) → kreditőr; hálózati hiba
    vagy időtúllépés (> 2 s az első bájtig) esetén azonnal Piper, a kör nem akad el.

**DoD M4:** egy fix mondat második lejátszása 0 kredit; hálózat nélkül is szól; a keret
túllépésekor magától vált, és a HUD ezt látja (`tts.credits`).

### M5 — saját ébresztőszó
23. `scripts/wakeword/` — `hey_auri.onnx` tanítása openWakeWorddel (szintetikus pozitívak több
    hangon és kiejtéssel + a felhasználó felvételei; negatívak: a saját szobazaja és a
    beszédkorpusz). Colabban vagy helyben, ahogy stabilabb; a lépéseket dokumentáld.
    Ha a `bench_wake` szerint jobb a v1-nél, legyen ez az `auto` első eleme.
24. Opcionális: full duplex headsettel (`audio.full_duplex: true`).

## Kommunikáció
- Minden session végén egy sor a JARVIS_BUILD 4. szakaszába, **mért számokkal**.
- Csomag kell → 5. szakasz. Szerződés kevés → 6. szakasz (indoklással és a javasolt új
  szignatúrával).
- Ha az AI-3 váza még nincs kész, fejlessz a szerződés szövegéhez, és tesztelj saját
  kis futtatóval (`python -m auri_jarvis.audio._demo`, a zónádon belül).

## Verifikáció
- `pytest tests/voice` zöld; `ruff` tiszta a fájljaidra.
- Valódi mikrofont, hangszórót és ElevenLabs-hívást igénylő tesztek: `@pytest.mark.manual`.
- **Kreditkeret a teljes fejlesztésre: ≤ 1000** (a 4. szakaszban vezesd, mennyit használtál).

## Kész, ha
- ☐ `create_ears` / `create_mouth` a szerződés szerint, az AI-3 orchestratorával integrálva.
- ☐ M1: hotkey + VAD + Parakeet + szótár + Piper (folyamaton belül) + mondat-streaming; számok a logban.
- ☐ M2: „Hey Auri” v1 a kapu felett, „Hey Jarvis”, taps 2.0 + kalibráció, nyugták, félduplex barge-in.
- ☐ M3: hang- és ébresztőszó-váltás menet közben; `play_sample`; vendég = `hey_auri` + `daniel`.
- ☐ M4: ElevenLabs-streaming + cache + kreditőr + offline tartalék.
- ☐ M5: `hey_auri.onnx` (ha jobb) + dokumentált tanítás.
- ☐ Semmit nem írtál a zónádon kívül; titok nincs naplóban; minden csomagkérés a táblán.
