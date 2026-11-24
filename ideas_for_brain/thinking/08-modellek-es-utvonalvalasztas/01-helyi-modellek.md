# Helyi modellek

> **Miről szól:** a telepített modellek és a szerepük a gondolkodó agyban, a kódolómodell-jelöltek
> (becslésként), a RAM-költségvetés nappal és éjjel, valamint a **mért KV-cache viselkedés** és ennek
> következményei a promptépítésre és a belső párbeszédre.

## 1. Telepített modellek → szerepek

Mért adatok: [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md) (2. pont).

| Modell | Mért (1. token független / munkamenetben · tok/s · RAM · hideg betöltés) | Szerep a gondolkodó agyban | Mire **ne** |
|---|---|---|---|
| **gemma4:e2b** | 0,44 / 0,73 s · ~6,2 · 1,9 GB · 18,5 s; eszközhívás 96,7% / 100% | **persona-modell**: a Jarvis hangja és a **Fogalmazó** (a felhasználónak szóló válasz, a persona-munkamenetben); élő `chat` a tudástárból | tények „fejből” (mért: „Ausztrália fővárosa: Sydney”); a belső szerepkönyv, ha van más modell (4. pont) |
| **gemma4:e4b** | 1,14 / 2,26 s · ~3,0 · 2,8 GB · 31,5 s | második vélemény éjjel („hideg kritika”, P3), ahol a pontosság fontosabb a sebességnél — **ha** a mérés igazolja | élő válasz (lassú) |
| **qwen3.5:4b** | 2,70 / 2,99 s · ~6,2 · nem mért · 38,3 s | **szerepkönyv-modell (javaslat)**: a belső szerepek élőben és háttérben; a tok/s az e2b-vel egyező, az első token egy percnyi generálás mellett kicsi; a P0-ban kódra mérendő | élő hangkör (lassú első token) |
| **embeddinggemma** | ~0,6 GB | beágyazás a tudástárhoz és a szemantikus cache-hez, rövid `keep_alive` | — |
| gemma2:2b, qwen2.5:1.5b, smollm2, tinyllama | nem mért | nem használjuk (régi, gyenge); lemezről törölhetők — a felhasználó döntése | — |

A `auri-jarvis/config/mind.yaml` `smart_model: qwen3.5:9b`-t említ („okos mód”), de a tények szerint
**nincs telepítve** → nem tervezünk vele, amíg nincs lehúzva és megmérve.

## 2. Kódolómodell-jelöltek (minden szám becslés, a gépen nem mérve)

| Jelölt | RAM (Q4, becslés) | Várható sebesség CPU-n | Mikor érdemes | Kockázat |
|---|---|---|---|---|
| `qwen2.5-coder:1.5b` / `:3b` | ~1–2,5 GB | gyors (az e2b-hez hasonló nagyságrend) | élő kódkiegészítés, kis javítások | gyenge tervezés |
| `qwen2.5-coder:7b` | ~4–5 GB (a ténylap szerint) | lassabb az e2b-nél (mérni kell) | **éjjeli P0/P4 kódolás** az e2b mellett | percekig tartó generálás |
| `qwen2.5-coder:14b` | ~9 GB (a ténylap szerint) | lassú | csak ha a Jarvis-modell éjjel kiürül | RAM-szűkösség, swap |
| `gpt-oss:20b` | ~14 GB | lassú | gyakorlatilag nem (16 GB-ba szűkösen fér) | a gép használhatatlanná válhat |

**Kiválasztás méréssel**, a `auri-jarvis/scripts/bench_llm.py` mintájára, plusz a kód-értékelő
készleten ([../06-programozas/09-meres-es-benchmark.md](../06-programozas/09-meres-es-benchmark.md)):
`pass@1`, siker ≤ 3 javítással, falióra-idő / feladat, RAM-csúcs, első token, tok/s. A jelöltek
**ugyanazon** a feladatkészleten futnak a telepített `qwen3.5:4b` és `gemma4:e2b` ellen is — lehet,
hogy egy általános modell javítási körökkel elég jó (ezt nem tudjuk, amíg nem mérjük).

## 3. RAM-költségvetés (16 GB)

| Tétel | Nappal (a felhasználó aktív) | Éjjel (tétlen) |
|---|---|---|
| Windows + alkalmazások (böngésző, VS Code) | ~5–7 GB (becslés) | ~3–4 GB (becslés) |
| Jarvis daemon (Python, Parakeet, Piper) | mérni kell | mérni kell |
| gemma4:e2b (Jarvis, `keep_alive: -1`) | 1,9 GB (mért) | 1,9 GB |
| embeddinggemma (csak a hívások körül) | 0,6 GB (mért) | 0,6 GB |
| Auri Core + SQLite + vektorok | ~0,3–0,5 GB (becslés) | ugyanaz |
| Sandbox-futás (pytest / node) | ~0,1–0,5 GB (becslés) | ugyanaz |
| KV-cache (`num_ctx` 8192, `q8_0`) | modellenként mérni kell | modellenként mérni kell |
| **Szerepkönyv-modell** | qwen3.5:4b csak élő `code` / `research` kéréskor (RAM: mérni kell) | qwen3.5:4b **vagy** egy ~4–5 GB-os kódolómodell (becslés) |

Következtetés (becslés): **egy** második, ~4–5 GB-os modell fér el az e2b mellett. A 14b-s méret csak akkor,
ha a Jarvis-modell éjjel kiürül — ekkor viszont a reggeli első hangkör a hideg betöltést fizeti. Ez
a felhasználó döntése ([../11-utemterv/03-nyitott-kerdesek.md](../11-utemterv/03-nyitott-kerdesek.md)).

## 4. A mért KV-cache viselkedés és következményei

**Tény (AI-2, Ollama 0.40.16):** a qwen3.5 és a gemma modelleknél a KV-cache **csak egy korábbi prompt
végétől** folytatható, tetszőleges közös előtagtól nem. Prefixváltás: gemma4:e2b ~6 s, e4b ~17 s
(egy ~1400–1700 tokenes, eszközsémás előtagon mérve).

Következmények a gondolkodó agyra:

1. **Egy szerepkönyv minden belső szerepnek.** Egy rögzített rendszerprompt (szerepkönyv); a szerep a
   *felhasználói* üzenet elején áll (`<szerep>KRITIKUS</szerep>…`) — így a szerepváltás nem okoz
   prefixváltást. Hogy a kis modell így is tartja-e a szerepet: mérni kell
   ([../02-belso-parbeszed/04-prompt-sablonok.md](../02-belso-parbeszed/04-prompt-sablonok.md)).
2. **Csak hozzáfűzés.** A belső párbeszéd egy szálban nő; token-keretnél új szál indul a rögzített
   előtagról (a Jarvis mintája: 12 kör / ~4900 token, az utolsó 2 kör átvihető).
3. **A Fogalmazó a persona-munkamenetben** fut, a belső eredmény a `<kontextus>`-ba kerül — a
   felhasználói beszélgetés előtagja sem cserélődik.
4. **Modell-elkülönítés.** Ugyanazon a modellen a szerepkönyv- és a persona-munkamenet egymás
   cache-ét írja felül: átlépésenként kb. egy prefixváltás (~6 s e2b-n), és a Jarvis meleg előtagja is
   elvész (következtetés a mért viselkedésből — mérni kell). Ezért a szerepkönyv lehetőleg másik
   modellen fut ([02-router.md](02-router.md)); ha mégis az e2b-n, utána a Jarvis `warmup()`-ját kell
   kérni. Ugyanez igaz az AuriGPT és a Jarvis eltérő persona-előtagjára (nyitott kérdés).
5. **A változó adat mindig a végére** (idő, találatok, kód, hibaüzenet) — a `prompts.py` szabálya.
6. **Rövid kontextus.** CPU-n a prefill drága: RAG-nál kevés (3–5, becslés), rövid kivonat.

```python
class PromptThread:
    """Csak hozzáfűzhető üzenetszál egy modellhez; a KV-cache a végéről folytatható."""
    def __init__(self, model: str, system: str, seed: list[dict], max_tokens: int = 4900):
        self.model, self.prefix, self.msgs = model, [{"role": "system", "content": system}, *seed], []
        self.max_tokens, self.tokens = max_tokens, 0   # tokens: a válasz LLMStats-ából frissül
    def ask(self, role: str, volatile: str, request: str) -> list[dict]:
        if self.tokens > self.max_tokens:          # új szál a rögzített előtagról
            self.msgs = self.msgs[-4:]              # utolsó 2 kör (kérés + válasz párok)
        self.msgs.append({"role": "user",
            "content": f"<szerep>{role}</szerep><kontextus>{volatile}</kontextus><kérés>{request}</kérés>"})
        return [*self.prefix, *self.msgs]           # soha nem írunk bele a közepébe
```

## 5. Paraméterek (kiinduló értékek, becslés)

| Lépés | `temperature` | `num_predict` | `format` | `think` |
|---|---|---|---|---|
| Megértés / osztályozás | 0,1 | 200 | JSON-séma | ki |
| Kódírás / javítás | 0,2 | 1200 | szöveg (kódblokk) | ki élőben; háttérben mérni |
| Fogalmazás a tudástárból | 0,6 (mint a Jarvis) | 400 | szöveg | ki |
| Tanulság | 0,3 | 120 | JSON-séma | ki |

A `think` mód tokenbe kerül: 500 gondolkodó token a mért 6,2 tok/s-mal ~80 s (levezetés) → csak
háttérben, és csak ha a mérés szerint javít a sikerarányon.

## 6. Kész, ha

- Minden modell szerepét a P0 mérése igazolja (vagy cáfolja) — a táblázat frissítve, a ténylap is.
- Az éjjeli forgatókönyv RAM-csúcsa mérve, swap nélkül.
- A szerep-a-felhasználói-üzenetben elv mellett a prefixváltások száma egy belső párbeszédben 0
  (mérve az `LLMStats.prompt_ms`-ből).

## Kapcsolódó

- [02-router.md](02-router.md) — melyik szint melyik modellt kapja
- [04-cache-es-ujrahasznositas.md](04-cache-es-ujrahasznositas.md) — kevesebb modellhívás
- [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md) — a mért számok
- [../02-belso-parbeszed/01-szerepek.md](../02-belso-parbeszed/01-szerepek.md) — szerepek és a váltás ára
- [../06-programozas/09-meres-es-benchmark.md](../06-programozas/09-meres-es-benchmark.md) — modellválasztó mérés
- [../01-architektura/03-hol-fut-auri-core.md](../01-architektura/03-hol-fut-auri-core.md) — Jarvis és Core egy Ollamán
