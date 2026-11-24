# Önkérdezés — részkérdések, „mit nem tudok?”, pontosítás, kíváncsiság

> **Miről szól:** hogyan bontja Auri a kérdést kisebb, megválaszolható részkérdésekre (self-ask),
> hogyan vizsgálja a saját állításait (szókratészi lánc), hogyan veszi észre, mit **nem** tud, mikor
> kérdez vissza a felhasználótól, és hogyan gyűjt kíváncsiság-kérdéseket a későbbi tanuláshoz.
> Ez a Kérdező szerep munkája ([01-szerepek.md](01-szerepek.md)).

## 1. Self-ask: a nagy kérdés kis kérdésekre bontva

A kis modell egy összetett kérdésre egyben gyakran rosszul felel, de egy-egy szűk részkérdésre — ha
közben megkapja a választ is — jobban. A Kérdező ezért **részkérdéseket** ír, és mindegyikhez
megmondja a **legolcsóbb forrást**. A forrássorrend (olcsótól a drágáig):

`store` (tudástár, ms) → `sandbox` (futtatás, s) → `web` (keresés + olvasás, 5–15 s, becslés) →
`model` (generálás, tíz másodpercek) → `user` (a felhasználó ideje — a legdrágább).

```ts
interface SubQuestion { q: string; why: string; source: 'store'|'sandbox'|'web'|'model'|'user'; answer?: Evidence }

async function selfAsk(task: Task, depth = 0): Promise<SubQuestion[]> {
  const subs = await kerdezo(task);                    // max. 5 részkérdés, JSON
  for (const s of subs) {
    s.answer = await answerFromCheapest(s);            // a megadott forrásból, ha ott nincs: a következőből
    if (!s.answer && depth < 1 && s.source !== 'user') // egyszer még bonthat tovább (max. mélység 2)
      s.answer = await summarize(await selfAsk({ goal: s.q }, depth + 1));
  }
  return subs;
}
```

**Példa** — „Írj FastAPI végpontot, ami fájlt fogad és 2 MB fölött elutasítja”:

| Részkérdés | Forrás | Miért |
|---|---|---|
| Melyik FastAPI-verzióra írunk? | `store` (a projekt függőségei) | API-különbségek |
| Hogyan fogad fájlt egy végpont (`UploadFile`)? | `store` → `web` (hivatalos doku) | pontos szignatúra |
| Kell-e hozzá külön csomag (`python-multipart`)? | `web` | telepítési feltétel |
| Hol ellenőrizhető a méret, mielőtt az egész fájl beolvasódik? | `web` → `model` | tervezési döntés |
| Hogyan tesztelhető (`TestClient`)? | `store` → `sandbox` | ellenőrzési pont |

Költség: a Kérdező egy lépés (~80 token, ~13 s gemma4:e2b-n, becslés). **Interaktív módban kihagyjuk**,
ha a feladat rövid, ismert mintájú, vagy a tudástár már ellenőrzött választ ad
([02-vita-protokoll.md](02-vita-protokoll.md), 5. pont).

## 2. Szókratészi lánc: a saját állítás vizsgálata

Egy állítás (a Gondolkodó javaslatában, egy weboldalon, a Tanár magyarázatában) négy kérdésen megy át:

1. **Mit állítok pontosan?** — egy mondat, alany + állítmány (pl. „`str.removeprefix` Python 3.9 óta van”).
2. **Miből tudom?** — forrás-azonosító (kártya, URL, tesztkimenet) vagy „a modell szerint” (= gyenge).
3. **Mi cáfolná?** — egy konkrét megfigyelés (pl. 3.8-on `AttributeError`).
4. **Hogyan ellenőrizhető olcsón?** — sandbox-futtatás, második forrás, vagy „nem ellenőrizhető” → `hipotézis`.

A 4. kérdés válasza **művelet**, nem szöveg: a lánc kimenete egy ellenőrzési lépés a ciklusban.
Így lesz az önkérdezésből ellenőrzés, nem csak „még több modell-szöveg”.

## 3. „Mit nem tudok?” — hiányfelismerés külső jelekből

A kis modellek saját magabiztossága rosszul kalibrált, ezért a hiányt elsősorban **mérhető jelekből**
ismerjük fel:

| Jel | Honnan | Mit jelent |
|---|---|---|
| A kérdés kulcsfogalmaihoz nincs kártya | tudástár-lefedettség | ismeretlen téma |
| Ismeretlen API-/csomagnév | tudástár + doku-index | nem ismert eszköz → web |
| A projekt verziója ≠ a kártya `appliesTo` tartománya | függőséglista | elavulhat |
| A teszt ismeretlen típusú hibával bukik | sandbox | hibakeresési hiány ([../06-programozas/06-hibakereses.md](../06-programozas/06-hibakereses.md)) |
| A források ellentmondanak | bizalmi réteg | `vitatott` |
| A k = 3 minta nem egyezik | szavazás | a modell bizonytalan |
| A modell maga írja: „nem tudom” / „nem vagyok biztos” | kimenet | gyenge, de figyelembe vesszük |

```ts
interface KnowledgeGap {
  topic: string;                 // pl. "fastapi: UploadFile méretkorlát"
  signal: 'no_card'|'unknown_api'|'version_mismatch'|'unknown_error'|'sources_disagree'|'self_inconsistent'|'model_unsure';
  severity: 1 | 2 | 3;           // 3 = a feladat enélkül nem oldható meg
  seenIn: string;                // munkamenet-azonosító (nem a felhasználó szövege)
}
```

Severity 3 → most kell pótolni (web/sandbox), ha a keret engedi. Severity 1–2 → a kíváncsiság-sorba (5. pont).

## 4. Pontosító kérdés a felhasználónak

| Helyzet | Döntés |
|---|---|
| A kétértelműség **lényegesen** más eredményt adna (pl. Python vagy TypeScript?) és olcsón nem dönthető el | **kérdez** — egy kérdés |
| Van ésszerű alapértelmezés (pl. legújabb stabil verzió, a projekt nyelve) | **feltételez**, és a válaszban kimondja („Feltételeztem: …”) |
| A feladat veszélyes vagy visszafordíthatatlan műveletet érint | **kérdez** (megerősítés) |
| A kérdés személyes adatra vonatkozna | **nem kérdez** ilyet — az agyba úgysem kerülhet |

Formai szabályok: **egy** kérdés, legfeljebb 3 opció, az egyik az ajánlott alapértelmezés.
Hangmódban egy rövid mondat (a Jarvis persona: „Ha a kérés zavaros… egy rövid kérdéssel
visszakérdezel, nem találgatsz.”). Példa: *„TypeScriptben vagy Pythonban kéred? Ha mindegy,
TypeScriptben írom, mert a projekted az.”*

## 5. Kíváncsiság-kérdések későbbre

Ami most nem fér a keretbe, az nem vész el: a Kérdező **kíváncsiság-kérdésként** sorba teszi, és az
éjszakai önálló tanulás (P4) ebből dolgozik.

```ts
interface CuriosityItem {
  question: string;          // általános, személytelen: "Hogyan korlátozható a feltöltés mérete FastAPI-ban streaming közben?"
  topic: string;             // normalizált téma-kulcs a deduplikáláshoz
  origin: 'gap'|'failed_task'|'disputed'|'teach_back';
  priority: number;          // lent
  createdAt: string; attempts: number; status: 'open'|'studied'|'dropped';
}
// priority = előfordulás (hányszor jött elő) × programozási hasznosság (0..1) × súlyosság (1..3)
```

Szabályok: (1) mentés előtt **személyesadat-szűrés** (`isPersonal` mintájára) — a kérdés legyen
általános, projektnév, fájlútvonal, név nélkül; (2) deduplikálás téma-kulcs + `textSimilar ≥ 0,82`
alapján — ismétlődés esetén csak a `priority` nő; (3) a sor korlátos (pl. 200 nyitott elem, kiinduló
érték) — a legalacsonyabb prioritású esik ki; (4) 3 sikertelen tanulási kísérlet után `dropped`.
Részletek: [../05-tanulas/02-ejszakai-onallo-tanulas.md](../05-tanulas/02-ejszakai-onallo-tanulas.md).

## 6. Kész, ha

1. A Kérdező a P3-feladatkészlet kétértelmű feladatainál ≥ 80%-ban a lényeges kétértelműséget kérdezi
   meg, egyértelmű feladatoknál pedig ≤ 10%-ban kérdez feleslegesen (célértékek, mérni kell).
2. Minden `KnowledgeGap` külső jelhez kötött, és a severity-3 hiányok a munkamenetben pótlódnak vagy
   `ask_help`-pel zárulnak.
3. A kíváncsiság-sorban nincs személyes adat (automatikus teszt fiktív adatokkal, pl. „Teszt Elek”),
   és nincs duplikált téma.

## Kapcsolódó

- [01-szerepek.md](01-szerepek.md) · [02-vita-protokoll.md](02-vita-protokoll.md) · [04-prompt-sablonok.md](04-prompt-sablonok.md) (T1 Kérdező)
- [../07-komplex-feladatok/01-feladatbontas.md](../07-komplex-feladatok/01-feladatbontas.md) — a self-ask nagy testvére
- [../03-web-szorfozes/01-kereses.md](../03-web-szorfozes/01-kereses.md) — amikor a részkérdés forrása `web`
- [../05-tanulas/04-tudas-ellenorzese.md](../05-tanulas/04-tudas-ellenorzese.md) · [../05-tanulas/05-mit-nem-szabad-megtanulni.md](../05-tanulas/05-mit-nem-szabad-megtanulni.md)
- [../09-biztonsag-es-adatvedelem/01-alapszabalyok.md](../09-biztonsag-es-adatvedelem/01-alapszabalyok.md)
