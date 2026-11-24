# Programing_Brain — fájlformátum (minden fájl EZT követi)

Ebből a mappából a `web/scripts/ingest-programming-brain.mjs` építi fel az AuriGPT BRAIN
programozási tudását. A betöltő a fájlokat szakaszokra bontja, ezért a forma kötelező.

```markdown
# Python
<!-- tech: python -->
<!-- aliases: py, python3, cpython -->

Egy bekezdés: mi ez a nyelv, mire használják, főbb jellemzők (típusrendszer, futtatás,
memóriakezelés, paradigmák), mikor jó és mikor nem.

## Aszinkron programozás asyncio-val
<!-- q: Hogyan írjak aszinkron kódot Pythonban? -->
<!-- tags: async, concurrency, asyncio, event loop -->

2–5 mondatos magyar magyarázat: MI ez, MIÉRT kell, HOGYAN működik belül, mire figyelj
(buktatók, teljesítmény, mikor ne használd).

```python
# Részletesen kommentezett, valódi, futtatható példa.
import asyncio
...
```

(opcionálisan még 1 kódblokk vagy egy rövid „Buktatók:” bekezdés)
```

Szabályok:
- `#` = a nyelv / téma neve (egy fájlban egy). Utána `<!-- tech: x -->` (kisbetűs azonosító)
  és opcionálisan `<!-- aliases: ... -->`.
- `##` = egy önálló tudásegység. Közvetlenül alatta `<!-- q: ... -->` (egy természetes magyar
  kérdés, amire ez a szakasz a válasz) és `<!-- tags: ... -->` (angol kulcsszavak).
- A próza magyarul, a szakkifejezések maradhatnak angolul. A kódban a kommentek magyarul.
- Minden szakaszban legalább egy kódblokk a nyelv nevével jelölve (```python, ```rust …).
- Komplex, valós példák (nem „hello world”): generikusok, konkurencia, minták, algoritmusok,
  hibakezelés, teljesítmény, idiomatikus megoldások — a kód legyen szintaktikailag helyes.
- Szakaszonként legfeljebb ~120 sor kód; inkább több szakasz, mint egy óriási.
- Személyes adat, valódi kulcs, jelszó, céges titok soha.
