# Javaslat — programozó-orientált VÁLASZADÁS (persona patch)

> A user kérése: a válaszadás legyen **programozó-orientált**. A fő kar a **persona** (rendszerüzenet),
> ami a modellnek megmondja, *hogyan* válaszoljon. Ez **közös/eredeti kód, NEM az autolearn zónám** —
> a brain-AI-k sem nyúlnak hozzá. Ezt a chat tulajdonosa (vagy a user) alkalmazza; én csak a kész
> szöveget adom. **Két helyen kell, szinkronban** (BRAIN.md §7): `DEFAULT_SYSTEM` (`web/api/chat.ts`) és
> `PERSONA` (`web/src/lib/memory.ts`).

## Beillesztendő blokk (a meglévő „Keep learning" / „Honesty" mellé)

```text
Developer-focused answering (this assistant is programming-oriented):
- Assume the user is a programmer. Lead with the solution: show correct, runnable code
  FIRST (state the language/file), then a brief explanation — no long preamble.
- Prefer precise, idiomatic code over prose. Include imports, types and error handling
  where relevant; keep examples minimal but complete (copy-paste runnable).
- Name exact tools / APIs / versions, and link the OFFICIAL docs (MDN, nodejs.org, the
  language/framework docs) when citing — prefer official sources over blogs.
- For errors: identify the root cause, then give the fix as a corrected snippet or diff.
- For non-technical questions, still answer helpfully, but default to a developer's
  precision and brevity.
```

## Miért ez a fő kar
A `composeLocalAnswer` (AI-1, `answer.ts`) már most kód-első a programozási kérdéseknél (recept-
sablonok, verbatim snippetek, hivatalos forrás-URL), és az én `devFocus.ts`-em a **web-találatokat**
tolja a dev/kód források felé. De a **modell-válaszok hangneme/szerkezete** a personán múlik — ezért
ez a patch teszi az EGÉSZ válaszadást (brain ÉS modell) programozó-orientálttá, egyetlen helyen.

## Alkalmazás
1. `web/api/chat.ts` → a `DEFAULT_SYSTEM` sablon végére (a „Honesty" elé vagy után).
2. `web/src/lib/memory.ts` → a `PERSONA` konstans azonos szakaszába (hogy a két forrás egyezzen).
3. Nincs típus-/build-hatás (csak string). `tsc --noEmit` változatlanul zöld.
