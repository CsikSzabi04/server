# Reguláris kifejezések és szövegfeldolgozás
<!-- tech: regex -->
<!-- aliases: regex, regexp, reguláris kifejezés, regular expression, pcre, re modul, szövegfeldolgozás, text processing, unicode -->

A reguláris kifejezés (regex) egy kis mintanyelv szövegek keresésére, ellenőrzésére, kinyerésére és cseréjére; a legtöbb nyelv beépítve támogatja (Python `re`, JavaScript `RegExp`, .NET `Regex`, Java `Pattern`, PCRE), és a parancssori eszközök (grep, sed, awk) is erre épülnek. A legtöbb motor *visszalépéses* (backtracking), ami rugalmas (visszahivatkozás, lookaround), de rossz mintánál exponenciális lassulást (ReDoS) okozhat; az automata-alapú motorok (RE2, Rust `regex`, .NET NonBacktracking) lineáris időt garantálnak, cserébe szűkebb funkciókészlettel. A regex kiváló tokenizálásra, logsorok és egyszerű formátumok feldolgozására, de beágyazott vagy szabványos formátumokhoz (HTML, JSON, CSV, e-mail RFC) dedikált parser kell.

## Alapszintaxis: karakterosztályok, horgonyok, flagek
<!-- q: Mik a regex alapelemei: karakterosztályok, horgonyok és flagek? -->
<!-- tags: regex syntax, character classes, anchors, word boundary, flags, multiline, dotall, verbose, re.escape -->

A karakterosztályok egy pozícióra illeszkedő karakterhalmazt adnak meg (`\d` számjegy, `\w` szókarakter, `\s` whitespace, `[A-Z]` tartomány, `[^...]` tagadás), a horgonyok pedig pozíciót, nem karaktert illesztenek (`^`, `$`, `\b` szóhatár). Alapból a `^`/`$` a teljes szöveg elejére/végére illeszkedik — soronként a `re.M` (multiline) flaggel; a `.` a sortörésre csak `re.S` (dotall) mellett; `re.I` a kis-nagybetű-függetlenség, `re.X` (verbose) pedig szóközöket és kommenteket enged a mintában, ami összetett regexnél sokat segít. Pythonban mindig raw stringet (`r"..."`) használj, különben a `\b` backspace lesz. Felhasználói bemenetből mintát csak `re.escape`-pel szabad építeni.

```python
import re

text = """Rendelés #A-1042 2025-03-14 összeg: 12 990 Ft
rendelés #b-77 2025-3-1 összeg: 990 Ft
Megjegyzés: sürgős!"""

# Karakterosztályok
print(re.findall(r"#[A-Za-z]-\d+", text))                 # ['#A-1042', '#b-77']

# Horgonyok: alapból a teljes szövegre, re.M-mel soronként
print(re.findall(r"^\w+", text))                          # ['Rendelés']
print(re.findall(r"^\w+", text, flags=re.M))              # mindhárom sor első szava

# \b szóhatár + kis-nagybetű-függetlenség
print(len(re.findall(r"\brendelés\b", text, flags=re.I)))  # 2

# re.X (verbose): olvasható, kommentezett minta
AMOUNT = re.compile(r"""
    összeg:\s*
    (?P<value>\d{1,3}(?:[  ]\d{3})*)   # ezres tagolás szóközzel vagy nem törhető szóközzel
    \s*Ft
""", re.X)
for m in AMOUNT.finditer(text):
    print(int(re.sub(r"\D", "", m["value"])))              # 12990, 990

# re.S: a . a sortörésre is illeszkedik
print(re.search(r"#A.*sürgős", text) is None, re.search(r"#A.*sürgős", text, re.S) is not None)

# match / search / fullmatch: elejéről / bárhol / teljes egyezés
print(bool(re.match(r"\d+", "abc123")), bool(re.search(r"\d+", "abc123")),
      bool(re.fullmatch(r"\d+", "123")))

# Felhasználói bemenet mintaként: mindig re.escape
user_input = "1+1=2?"
print(re.search(re.escape(user_input), "Igaz, hogy 1+1=2? Igen.") is not None)
```

## Kvantorok: mohó, lusta és possessive
<!-- q: Mi a különbség a mohó (greedy), a lusta (lazy) és a possessive kvantorok között? -->
<!-- tags: quantifiers, greedy, lazy, non greedy, possessive, atomic group, backtracking, regex -->

A kvantorok az ismétlést adják meg (`*` 0+, `+` 1+, `?` 0–1, `{n,m}`); alapból *mohók*: a lehető legtöbbet nyelik el, majd szükség esetén visszalépnek, ezért a `<a.*>` az első `<a`-tól az utolsó `>`-ig mindent elnyel. A *lusta* változat (`*?`, `+?`) a lehető legkevesebbet nyeli, a *possessive* (`*+`, `++`) és az *atomi csoport* (`(?>...)`) pedig elnyel, és soha nem ad vissza — Pythonban 3.11-től támogatott. A legjobb megoldás gyakran a negált karakterosztály (`"[^"]*"`): egyértelmű, gyors és nincs visszalépés. A possessive forma a ReDoS elleni egyik védekezés, mert a nem illeszkedő mintánál azonnal feladja.

```python
import re

html = '<a href="/x">egy</a> és <a href="/y">kettő</a>'

print(re.findall(r"<a.*>", html))           # MOHÓ: egyetlen találat a teljes stringre!
print(re.findall(r"<a.*?>", html))          # LUSTA: ['<a href="/x">', '<a href="/y">']
print(re.findall(r'href="([^"]*)"', html))  # NEGÁLT OSZTÁLY: ['/x', '/y'] — egyértelmű és gyors

# Pontos ismétlésszám
print(re.fullmatch(r"\d{4}-\d{2}-\d{2}", "2025-03-14") is not None)

# POSSESSIVE és ATOMI csoport (Python 3.11+): elnyel és nem ad vissza
print(re.fullmatch(r'"[^"]*+"', '"idézet"') is not None)    # True
print(re.fullmatch(r'".*+"', '"idézet"'))                   # None: a .*+ a záró "-t is elnyelte
print(re.fullmatch(r"(?>a+)b", "aaab") is not None)         # True

# A különbség a nem illeszkedő bemenetnél látszik: a possessive azonnal feladja
s = "a" * 30 + "!"
print(re.fullmatch(r"(?:a++)+$", s))                        # None, gyorsan
# print(re.fullmatch(r"(?:a+)+$", s))                       # ugyanez visszalépéssel: másodpercek!
```

## Csoportok, nevesített csoportok és visszahivatkozások
<!-- q: Hogyan használjam a befogó, nevesített és nem befogó csoportokat, valamint a visszahivatkozásokat? -->
<!-- tags: capturing groups, named groups, non capturing groups, backreferences, re.sub, findall, regex -->

A zárójeles csoport befogja (capture) az illeszkedő részt, amit sorszámmal vagy névvel (`(?P<név>...)`, más dialektusban `(?<név>...)`) érhetsz el; a `(?:...)` csak csoportosít (alternáció, ismétlés) befogás nélkül, ami gyorsabb és nem zavarja a sorszámozást. A visszahivatkozás (`\1`, `(?P=név)`) ugyanazt a szöveget követeli meg újra (duplikált szavak, egyező nyitó/záró tag). Buktatók: a `findall` több csoport esetén tuple-öket ad; az ismételt csoport csak az *utolsó* ismétlést őrzi meg; cserénél `\g<név>` vagy függvény is használható.

```python
import re

log = "2025-03-14 10:22:01 user=anna action=login ip=10.0.0.7"

m = re.search(r"(?P<date>\d{4}-\d{2}-\d{2}) (?P<time>[\d:]{8})", log)
print(m.group(1), m["time"], m.groupdict())

# Nem befogó csoport: csoportosít, de nem kerül a találatba
print(re.findall(r"(?:user|ip)=(\S+)", log))            # ['anna', '10.0.0.7']
print(dict(re.findall(r"(\w+)=(\S+)", log)))           # több csoport -> tuple-ök -> dict

# Visszahivatkozás: ugyanaz a szöveg még egyszer
print(re.findall(r"\b(\w+)\s+\1\b", "ez ez egy hiba hiba itt"))      # ['ez', 'hiba']
print(re.sub(r"<(?P<tag>\w+)>(.*?)</(?P=tag)>", r"[\g<tag>:\2]", "<b>vastag</b> <i>dőlt</i>"))

# Csere függvénnyel: dinamikus helyettesítés (IP-cím maszkolása)
def mask_ip(m: re.Match) -> str:
    a, b, _, _ = m.group(0).split(".")
    return f"{a}.{b}.x.x"
print(re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", mask_ip, log))

# Buktató: az ismételt csoport csak az UTOLSÓ ismétlést tartja meg
print(re.fullmatch(r"(\d+,)+", "1,22,333,").group(1))   # '333,' — nem az összes
print(re.findall(r"\d+", "1,22,333,"))                  # helyette: findall a részmintára
```

## Lookahead és lookbehind
<!-- q: Hogyan működik a lookahead és a lookbehind, és mire használjam őket? -->
<!-- tags: lookahead, lookbehind, lookaround, zero width assertion, password validation, regex -->

A lookaround nulla szélességű feltétel: ellenőrzi, mi áll a pozíció után (`(?=...)`, negatív: `(?!...)`) vagy előtt (`(?<=...)`, `(?<!...)`), de nem fogyaszt karaktert, így nem kerül a találatba. Tipikus használat: több független feltétel egyetlen mintában (jelszó-szabály, minden feltétel egy lookahead), kontextusfüggő kinyerés (szám, ami előtt `$` áll), pozíció beszúrása (ezres tagolás). A Python `re` lookbehindja csak fix hosszúságú lehet (a .NET, a JavaScript és a `regex` csomag engedi a változót), és a lookaround nem támogatott a lineáris idejű motorokban (RE2, Rust `regex`). Bonyolult feltételeknél egy-két külön ellenőrzés olvashatóbb, mint egy hosszú lookahead-lánc.

```python
import re

# Több feltétel egyszerre, mindegyik egy lookahead
STRONG = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?!.*\s).{12,}$")
for pw in ["Gyenge1", "ErosJelszo2025", "Van Szokoz 2025"]:
    print(pw, bool(STRONG.match(pw)))               # False, True, False

# Lookbehind: a $ nem része a találatnak
prices = "Ár: $120, €95, $7.50, 300 Ft"
print(re.findall(r"(?<=\$)\d+(?:\.\d+)?", prices))  # ['120', '7.50']

# Ezres tagolás: szóköz oda, ahol utána 3-mal osztható számú számjegy van
def group_thousands(n: int) -> str:
    return re.sub(r"(?<=\d)(?=(?:\d{3})+$)", " ", str(n))
print(group_thousands(1234567), group_thousands(999))   # '1 234 567' '999'

# Negatív lookahead: "teszt" kezdetű szó, de nem "tesztel..."
print(re.findall(r"\bteszt(?!el)\w*", "teszt tesztelés tesztek"))   # ['teszt', 'tesztek']

# Negatív lookbehind: szám, ami előtt nincs mínuszjel
print(re.findall(r"(?<![-\d])\d+", "5 -3 12 -40"))  # ['5', '12']

# Python re: a lookbehind csak fix hosszú lehet
try:
    re.compile(r"(?<=\d+)px")
except re.error as e:
    print("hiba:", e)                               # look-behind requires fixed-width pattern
```

## Katasztrofális visszalépés és ReDoS
<!-- q: Mi a katasztrofális backtracking (ReDoS), és hogyan írjak biztonságos regexet? -->
<!-- tags: catastrophic backtracking, redos, regex performance, nested quantifiers, security, timeout, re2 -->

Visszalépéses motorban az egymásba ágyazott, ugyanazt a szöveget illesztő kvantorok (`(a+)+`, `(\w+\s?)+`, `(.*,)*`) nem illeszkedő bemenetnél az összes lehetséges felosztást kipróbálják — ez exponenciális idő, és egyetlen rosszindulatú, néhány tucat karakteres bemenet percekre lefoglalhat egy CPU-magot (ReDoS, valós incidensek: Cloudflare 2019, Stack Overflow 2016). A javítás: a minta legyen egyértelmű (minden karakter csak egyféleképpen illeszkedhessen), negált osztály `.*` helyett, possessive/atomi csoport. Védekezés még: a bemenet hosszának korlátozása, időkorlát (a Python `re`-ben nincs — külön processz vagy a `regex` csomag `timeout` paramétere), illetve lineáris idejű motor (RE2, Rust `regex`, .NET NonBacktracking) felhasználói mintákhoz.

```python
import re
import time

EVIL = re.compile(r"^(a+)+$")         # egymásba ágyazott kvantorok ugyanarra a karakterre
SAFE = re.compile(r"^a+$")

for n in (16, 18, 20, 22):
    s = "a" * n + "!"                 # a végén NEM illeszkedik -> minden felosztást kipróbál
    t0 = time.perf_counter()
    EVIL.match(s)
    print(f"n={n}: {time.perf_counter() - t0:.3f} s")    # kb. duplázódik karakterenként: O(2^n)

t0 = time.perf_counter()
SAFE.match("a" * 100_000 + "!")
print(f"biztonságos változat 100 000 karakteren: {time.perf_counter() - t0:.4f} s")

# Rejtett változat a gyakorlatban és javításai:
EMAIL_BAD = re.compile(r"^([a-zA-Z0-9]+\.?)+@")              # a pont opcionális -> kétértelmű
EMAIL_OK = re.compile(r"^[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*@")  # minden karakter egyértelmű helyen
EMAIL_ATOMIC = re.compile(r"^(?>[a-zA-Z0-9]+\.?)++@")        # possessive: nincs visszalépés

attack = "a" * 28 + "!"
for name, rx in [("OK", EMAIL_OK), ("ATOMIC", EMAIL_ATOMIC)]:
    t0 = time.perf_counter()
    rx.match(attack)
    print(name, f"{time.perf_counter() - t0:.5f} s")
# EMAIL_BAD.match(attack) itt másodpercekig/percekig futna — ezért nem futtatjuk.

MAX_INPUT = 1_000
def safe_match(rx: re.Pattern, s: str):
    if len(s) > MAX_INPUT:            # hosszkorlát: az egyszerű, de hatékony védelem
        raise ValueError("túl hosszú bemenet")
    return rx.match(s)
```

## Regex-dialektusok: PCRE, JavaScript, Python, .NET, POSIX
<!-- q: Miben különböznek a regex dialektusok (PCRE, JavaScript, Python, .NET, POSIX)? -->
<!-- tags: regex flavors, pcre, javascript regexp, dotnet regex, posix ere, grep, sed, named groups, unicode property -->

A dialektusok alapjai közösek, de a részletek eltérnek: nevesített csoport Pythonban `(?P<n>...)` (3.11 óta `(?<n>...)` is), JS-ben és .NET-ben `(?<n>...)`; a lookbehind Pythonban fix hosszú, JS-ben és .NET-ben tetszőleges; a `\p{L}` Unicode-tulajdonság JS-ben csak `u`/`v` flaggel, a Python `re`-ben egyáltalán nincs (a `regex` csomagban van). A POSIX ERE (`grep -E`, `sed -E`, awk) nem ismeri a `\d`-t (helyette `[0-9]` vagy `[[:digit:]]`), a lusta kvantort és a lookaroundot; a `grep -P` PCRE-t ad. A .NET különlegességei a timeout, a forráskód-generált regex és a NonBacktracking mód; JavaScriptben a `g`/`y` flagű regex állapotot (`lastIndex`) tart, ami újrahasználva csendes hibát okoz.

```javascript
// JavaScript (ECMAScript)
const re = /(?<year>\d{4})-(?<month>\d{2})/gu;            // g: összes találat, u: Unicode-mód
for (const m of "2025-03 és 2024-12".matchAll(re)) {
  console.log(m.groups.year, m.groups.month, m.index);
}
// lastIndex csapda: a g flagű regex ÁLLAPOTOT tart
const g = /a/g;
console.log(g.test("a"), g.test("a"));                     // true false (!)
console.log("Árvíz ÉS tűrő".match(/\p{Lu}/gu));            // ['Á', 'É', 'S'] — csak u flaggel
console.log(/a.b/s.test("a\nb"));                          // s flag: dotAll
console.log(/(?<=\$)\d+/.exec("ár: $42")[0]);              // lookbehind (JS-ben változó hossz is ok)
console.log("2025-03-14".replace(/(?<y>\d+)-(?<m>\d+)-(?<d>\d+)/, "$<d>.$<m>.$<y>"));  // 14.03.2025
```

```csharp
using System;
using System.Text.RegularExpressions;

public static partial class Patterns
{
    // .NET 7+: fordítási időben generált regex, beépített időkorláttal
    [GeneratedRegex(@"^(?<user>[\w.+-]+)@(?<domain>[\w-]+(?:\.[\w-]+)+)$", RegexOptions.IgnoreCase, matchTimeoutMilliseconds: 100)]
    public static partial Regex Email();

    // NonBacktracking: lineáris idő (nincs ReDoS), de nincs visszahivatkozás és lookaround
    public static readonly Regex Words = new(@"\w+", RegexOptions.NonBacktracking);

    public static void Main()
    {
        var m = Email().Match("valaki@example.com");
        Console.WriteLine(m.Success ? m.Groups["domain"].Value : "nincs találat");
        try
        {
            Regex.Match(new string('a', 30) + "!", @"^(a+)+$", RegexOptions.None, TimeSpan.FromMilliseconds(50));
        }
        catch (RegexMatchTimeoutException)
        {
            Console.WriteLine("időtúllépés: a ReDoS megfogva");
        }
        // .NET-specifikus: balancing groups — kiegyensúlyozott zárójelezés ellenőrzése
        var balanced = new Regex(@"^\((?>[^()]+|\((?<d>)|\)(?<-d>))*(?(d)(?!))\)$");
        Console.WriteLine($"{balanced.IsMatch("(a(b)c)")} {balanced.IsMatch("(a(b c)")}");   // True False
    }
}
```

```bash
grep -E '^[0-9]{4}-[0-9]{2}' app.log          # POSIX ERE: nincs \d, lusta kvantor, lookaround
grep -oP '(?<=user=)\w+' app.log              # PCRE (GNU grep -P): lookbehind, \d, \w
sed -E 's/([0-9]{4})-([0-9]{2})-([0-9]{2})/\3.\2.\1/' dates.txt   # dátumformátum-csere
```

## Logfájlok feldolgozása regexszel
<!-- q: Hogyan dolgozzak fel logfájlokat (pl. nginx access log) regexszel Pythonban? -->
<!-- tags: log parsing, nginx, access log, regex, named groups, generators, counter, python -->

Logsorok feldolgozására a regex ideális: a formátum fix, soronként független, és a nevesített csoportok közvetlenül dict-té alakíthatók. A mintát egyszer fordítsd le, a fájlt soronként, lustán (generátorral) olvasd, a mezőket rögtön alakítsd típusosra (idő, szám), és a nem illeszkedő sorokat soha ne dobd el csendben — számold vagy naplózd őket, mert formátumváltozást jeleznek. A lekérdezési paramétereket (`?page=2`) vágd le az útvonalról, különben a csoportosítás szétesik. Ha teheted, a logot eleve strukturáltan (JSON) írd, akkor nem kell regex.

```python
import re
from collections import Counter
from datetime import datetime

# Nginx "combined" formátum
LINE = re.compile(
    r'(?P<ip>\S+) \S+ (?P<user>\S+) \[(?P<ts>[^\]]+)\] '
    r'"(?P<method>[A-Z]+) (?P<path>\S+) (?P<proto>[^"]+)" '
    r'(?P<status>\d{3}) (?P<size>\d+|-) "(?P<referer>[^"]*)" "(?P<agent>[^"]*)"'
)

def parse(lines):
    for lineno, line in enumerate(lines, 1):
        m = LINE.match(line)
        if not m:
            yield {"error": f"nem illeszkedő sor: {lineno}"}       # nem dobjuk el csendben
            continue
        rec = m.groupdict()
        rec["ts"] = datetime.strptime(rec["ts"], "%d/%b/%Y:%H:%M:%S %z")
        rec["status"] = int(rec["status"])
        rec["size"] = 0 if rec["size"] == "-" else int(rec["size"])
        rec["path"] = rec["path"].split("?", 1)[0]                  # query string nélkül
        yield rec

sample = [
    '10.0.0.7 - - [14/Mar/2025:10:22:01 +0100] "GET /api/products?page=2 HTTP/1.1" 200 5120 "-" "Mozilla/5.0"',
    '10.0.0.9 - - [14/Mar/2025:10:22:03 +0100] "POST /api/checkout HTTP/1.1" 502 0 "-" "curl/8.5"',
    "sérült sor",
]
records = list(parse(sample))
ok = [r for r in records if "error" not in r]
print(Counter(r["status"] for r in ok))
print(Counter(r["path"] for r in ok if r["status"] >= 500))
print([r["error"] for r in records if "error" in r])
```

## CSV feldolgozása: miért nem regexszel
<!-- q: Miért ne parszoljak CSV-t regexszel vagy split-tel, és hogyan csináljam helyesen? -->
<!-- tags: csv, csv module, rfc 4180, quoting, escaping, parsing, python, excel -->

A CSV egyszerűnek látszik, de az RFC 4180 szerint a mező tartalmazhat vesszőt és sortörést (idézőjelek között), az idézőjelet pedig duplázással escape-eljük (`""`) — a `split(",")` és a naiv regex ezeket elrontja. Pythonban a `csv` modul (fájlnál `newline=""`-vel) helyesen kezeli az idézést, a többsoros mezőt és az írásnál az automatikus idézőjelezést; nagy adatnál a pandas/polars is. A gyakorlati buktatók: a magyar Excel `;` elválasztót és gyakran BOM-ot használ (`encoding="utf-8-sig"`), a kódolás lehet cp1250, és a számok tizedesvesszővel érkezhetnek. Regex csak egyetlen, ismert formátumú sor gyors darabolására jöhet szóba.

```python
import csv
import io
import re

data = 'id,név,megjegyzés\n1,"Kovács, Anna","azt mondta: ""jó"""\n2,Béla,"több\nsoros"\n'

# NAIV: az idézett vessző, a "" escape és a többsoros mező is elromlik
print([line.split(",") for line in data.splitlines()][:2])

# HELYES: csv modul
rows = list(csv.DictReader(io.StringIO(data, newline="")))
print(rows[0]["név"], "|", rows[0]["megjegyzés"], "|", repr(rows[1]["megjegyzés"]))

# Fájlból (magyar Excel-export: ; elválasztó, BOM):
#   with open("export.csv", newline="", encoding="utf-8-sig") as f:
#       for row in csv.DictReader(f, delimiter=";"):
#           amount = float(row["összeg"].replace(" ", "").replace(",", "."))

# Írás: az idézőjelezést a modul végzi
out = io.StringIO()
csv.writer(out).writerow(["2", 'Mondta: "szia", majd elment', "x"])
print(out.getvalue())                     # 2,"Mondta: ""szia"", majd elment",x

# Ha mégis regex kell egyetlen sorra: idézett mező VAGY vessző nélküli mező
FIELD = re.compile(r'(?:^|,)("(?:[^"]|"")*"|[^,]*)')
def split_csv_line(line: str) -> list[str]:
    fields = [m.group(1) for m in FIELD.finditer(line)]
    return [f[1:-1].replace('""', '"') if f.startswith('"') else f for f in fields]
print(split_csv_line('1,"Kovács, Anna","azt mondta: ""jó"""'))
```

## Validálás és kinyerés: e-mail, URL, dátum
<!-- q: Hogyan validáljak vagy nyerjek ki e-mail címet, URL-t és dátumot regexszel, és mik a buktatók? -->
<!-- tags: email validation, url parsing, date extraction, urllib, validation pitfalls, regex, python -->

Az e-mail cím teljes RFC 5322 szerinti regexe gyakorlatilag használhatatlan; a pragmatikus út egy laza ellenőrzés (`valami@valami.tld`, hosszkorlát), a valódi validáció pedig a megerősítő levél — a túl szigorú minta a `+` jeles és a nemzetközi (IDN) címeket is elutasítja. URL-t ne regexszel validálj, hanem szabványos parserrel (`urllib.parse.urlsplit`), és explicit szabályokkal (csak `http`/`https`, van host, nincs beágyazott felhasználónév) — ez a `javascript:` és a `user@evil` típusú trükköket is megfogja. Szövegből *kinyerni* viszont jó a regex, de a záró írásjeleket le kell vágni. Dátumnál a regex csak a formátumot ellenőrzi, a létezést (február 30.) a dátumkonstruktor dönti el.

```python
import re
from datetime import date
from urllib.parse import urlsplit

# E-MAIL: pragmatikus ellenőrzés (+ a valódi validálás a megerősítő levél)
EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
def plausible_email(s: str) -> bool:
    return len(s) <= 254 and EMAIL.fullmatch(s) is not None
print([plausible_email(e) for e in ["anna+hirlevel@example.com", "a@b", "x y@z.hu", "név@példa.hu"]])

# URL VALIDÁLÁS: parser + explicit szabályok
def safe_http_url(s: str) -> bool:
    try:
        parts = urlsplit(s)
    except ValueError:
        return False
    return parts.scheme in ("http", "https") and bool(parts.hostname) and parts.username is None
print([safe_http_url(u) for u in ["https://example.com/a?b=1", "javascript:alert(1)",
                                  "https://user@evil.example/"]])            # True False False

# URL KINYERÉS szövegből: a záró írásjeleket levágjuk
URL_IN_TEXT = re.compile(r"https?://[^\s<>\"']+")
text = "Lásd: https://example.com/doc/1. Vagy (https://example.org/x)!"
print([u.rstrip(".,;:!?)") for u in URL_IN_TEXT.findall(text)])

# DÁTUM: a regex a formát, a date() az érvényességet ellenőrzi
DATE = re.compile(r"\b(?P<y>\d{4})[-./](?P<m>\d{1,2})[-./](?P<d>\d{1,2})\.?")
def extract_dates(s: str) -> list[date]:
    found = []
    for m in DATE.finditer(s):
        try:
            found.append(date(int(m["y"]), int(m["m"]), int(m["d"])))
        except ValueError:
            pass                                    # formailag jó, de nem létező nap
    return found
print(extract_dates("Határidő: 2025.03.14., csúszás: 2025-02-30, új: 2025/4/1"))
```

## Unicode és normalizálás
<!-- q: Mire figyeljek Unicode szövegek regexes feldolgozásánál és összehasonlításánál? -->
<!-- tags: unicode, normalization, nfc, nfd, nfkc, casefold, accents, graphemes, unicodedata -->

Python 3-ban a `\w`, `\d` és `\s` Unicode-tudatos: a `\w` illeszkedik az ékezetes betűkre, de a `\d` más írásrendszerek számjegyeire is (arab-indiai, dévanágari) — ASCII számhoz `[0-9]` vagy `re.ASCII` kell. Ugyanaz a látható szöveg többféle kódpont-sorozat lehet (`é` egy kódpontként vagy `e` + kombináló ékezetként), ezért összehasonlítás, keresés és egyediség-ellenőrzés előtt normalizálni kell (NFC általános célra, NFKC azonosítókhoz, felhasználónevekhez). Kis-nagybetű-független összehasonlításhoz a `casefold()` a helyes (`ß` → `ss`). A felhasználó által látott „karakter” (graféma: emoji, zászló) több kódpontból állhat, így a `len()` és a szeletelés félrevezető lehet.

```python
import re
import unicodedata

print(re.findall(r"\w+", "Árvíztűrő tükörfúrógép"))      # ékezetes szavak egyben
print(re.fullmatch(r"\d+", "١٢٣") is not None)            # True: arab-indiai számjegyek!
print(re.fullmatch(r"[0-9]+", "١٢٣") is not None)         # False: csak ASCII számjegy

# Normalizálás: ugyanaz a látható szöveg, más kódpontok
composed, decomposed = "é", "é"                 # é (NFC) vs e + kombináló ékezet (NFD)
print(composed == decomposed, len(composed), len(decomposed))   # False 1 2
def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)
print(nfc(composed) == nfc(decomposed))                    # True: összehasonlítás előtt normalizálj

# casefold: erősebb a lower()-nél
print("STRASSE".lower() == "straße".lower(), "STRASSE".casefold() == "straße".casefold())  # False True

# Ékezetmentesítés (kereséshez, slughoz): NFD-bontás, a kombináló jelek eldobása
def strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if not unicodedata.combining(ch))
print(strip_accents("Árvíztűrő tükörfúrógép"))             # Arvizturo tukorfurogep

# NFKC: kompatibilitási alakok egységesítése (teljes szélességű betűk, körbe írt számok)
print(unicodedata.normalize("NFKC", "ｆｉｌｅ①"))            # file1

# Grafémák: egy látható jel több kódpont is lehet
flag = "\U0001F1ED\U0001F1FA"                              # magyar zászló emoji
print(len(flag))                                            # 2 kódpont, 1 látható jel
# Graféma-alapú darabolás: a 'regex' csomag \X mintája -> regex.findall(r"\X", s)
```

## Tokenizálás regexszel
<!-- q: Hogyan írjak tokenizálót (lexert) egyetlen regexszel nevesített csoportokkal? -->
<!-- tags: tokenizer, lexer, regex scanner, named groups, alternation, lastgroup, finditer -->

Egy egyszerű nyelv vagy formátum tokenizálója megírható egyetlen nagy alternációval, ahol minden tokentípus egy nevesített csoport; a `finditer` balról jobbra halad, a `m.lastgroup` megadja az illeszkedett típust. Az alternáció *balról az első illeszkedőt* választja (nem a leghosszabbat), ezért a hosszabb, specifikusabb mintáknak kell elöl állniuk (`==` a `=` előtt, szám az azonosító előtt). Kötelező egy utolsó `MISMATCH` ág, különben a `finditer` csendben átugorja az ismeretlen karaktereket. A kulcsszavakat érdemes azonosítóként illeszteni, és utána halmazból besorolni.

```python
import re
from typing import Iterator, NamedTuple

class Token(NamedTuple):
    kind: str
    value: str
    line: int
    col: int

TOKEN_SPEC = [                                  # a SORREND számít: specifikusabb előre
    ("NUMBER",   r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"),
    ("STRING",   r'"(?:[^"\\\n]|\\.)*"'),
    ("IDENT",    r"[A-Za-z_]\w*"),
    ("OP",       r"==|!=|<=|>=|&&|\|\||[-+*/%=<>!(){}\[\],;.]"),
    ("NEWLINE",  r"\n"),
    ("SKIP",     r"[ \t]+|//[^\n]*"),           # szóköz és sorvégi komment
    ("MISMATCH", r"."),                         # minden más: hiba, nem csendes átugrás
]
MASTER = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC))
KEYWORDS = {"if", "else", "while", "return", "let"}

def tokenize(code: str) -> Iterator[Token]:
    line, line_start = 1, 0
    for m in MASTER.finditer(code):
        kind, value = m.lastgroup, m.group()
        col = m.start() - line_start + 1
        if kind == "NEWLINE":
            line, line_start = line + 1, m.end()
        elif kind == "SKIP":
            continue
        elif kind == "MISMATCH":
            raise SyntaxError(f"{line}:{col}: váratlan karakter {value!r}")
        else:
            if kind == "IDENT" and value in KEYWORDS:
                kind = value.upper()            # kulcsszó besorolása halmazból
            yield Token(kind, value, line, col)

code = 'let total = price * 1.27; // ÁFA\nif (total >= 1e3) { print("drága\\n"); }'
for tok in tokenize(code):
    print(tok)
```

## Szöveg feldolgozása regex nélkül: állapotgépek
<!-- q: Mikor és hogyan dolgozzak fel szöveget állapotgéppel regex helyett? -->
<!-- tags: state machine, finite automaton, parsing, shlex, escaping, quoting, tokenizer, without regex -->

Ha a szabályok kontextusfüggők (idézés, escape, beágyazás), a regex gyorsan olvashatatlanná és törékennyé válik; ilyenkor egy explicit *állapotgép* a jobb: karakterenként halad, az aktuális állapot (szóközben, szóban, idézőjelben, escape után) dönti el, mit jelent a következő karakter. Az eredmény lineáris idejű, minden eset külön tesztelhető, és pontos hibaüzenet adható (pl. lezáratlan idézőjel). Beágyazott szerkezetekhez (zárójelek, JSON, HTML) verem vagy rekurzív leszálló parser kell — a klasszikus regex elméletileg sem képes tetszőleges mélységű egyezést kezelni. Mielőtt sajátot írsz, nézd meg, van-e kész parser (`shlex`, `json`, `html.parser`, `tomllib`).

```python
import shlex
from enum import Enum, auto

class S(Enum):
    BETWEEN = auto()        # argumentumok között
    WORD = auto()           # idézőjel nélküli szóban
    SINGLE = auto()         # '...' belül: minden szó szerint
    DOUBLE = auto()         # "..." belül: \" és \\ escape
    DOUBLE_ESCAPE = auto()  # \ után idézőjelen belül
    ESCAPE = auto()         # \ után idézőjelen kívül

def split_args(s: str) -> list[str]:
    """Shell-szerű argumentum-darabolás állapotgéppel (egyszerűsített shlex.split)."""
    args, buf, state = [], [], S.BETWEEN
    for ch in s:
        if state in (S.BETWEEN, S.WORD):
            if ch.isspace():
                if state is S.WORD:
                    args.append("".join(buf))
                    buf = []
                state = S.BETWEEN
            elif ch == "'":
                state = S.SINGLE
            elif ch == '"':
                state = S.DOUBLE
            elif ch == "\\":
                state = S.ESCAPE
            else:
                buf.append(ch)
                state = S.WORD
        elif state is S.SINGLE:
            if ch == "'": state = S.WORD          # záró idézőjel után a szó folytatódhat
            else: buf.append(ch)
        elif state is S.DOUBLE:
            if ch == '"': state = S.WORD
            elif ch == "\\": state = S.DOUBLE_ESCAPE
            else: buf.append(ch)
        elif state is S.DOUBLE_ESCAPE:
            buf.append(ch if ch in '"\\' else "\\" + ch)   # csak \" és \\ speciális
            state = S.DOUBLE
        elif state is S.ESCAPE:
            buf.append(ch)
            state = S.WORD
    if state not in (S.BETWEEN, S.WORD):
        raise ValueError(f"befejezetlen idézés vagy escape a bemenet végén ({state.name})")
    if state is S.WORD:
        args.append("".join(buf))
    return args

for case in ['cp "my file.txt" /tmp/', "echo 'it''s' a\\ b", 'grep -e "a\\"b" ""']:
    print(split_args(case), split_args(case) == shlex.split(case))
```

## String-algoritmusok és teljesítmény
<!-- q: Hogyan keressek gyorsan szövegben, és mikor gyorsabbak a string metódusok a regexnél? -->
<!-- tags: string search, performance, kmp, aho corasick, boyer moore, str methods, compile, join -->

Egyszerű részszöveg-keresésre a beépített string-metódusok (`in`, `find`, `startswith`, `replace`, `split`) a leggyorsabbak, mert C-ben, optimalizált algoritmussal (Boyer–Moore–Horspool-jellegű, „two-way”) futnak — regex csak valódi mintához kell. A regexet fordítsd le egyszer (`re.compile`) modulszinten; sok kulcsszó keresésekor egyetlen alternáció (vagy nagy kulcsszólistánál Aho–Corasick automata, pl. `pyahocorasick`) egy menetben dolgozik N külön keresés helyett. A KMP O(n + m) időt garantál, mert a szövegben sosem lép vissza — ez az alapja a streaming keresésnek is. Gyakori lassúság a `+=` stringépítés ciklusban: helyette `"".join(...)`.

```python
import re
import timeit

text = ("lorem ipsum dolor sit amet " * 20_000) + "TALÁLAT"

# 1) Egyszerű keresésre a str metódus a leggyorsabb
print("in:       ", timeit.timeit(lambda: "TALÁLAT" in text, number=200))
print("re.search:", timeit.timeit(lambda: re.search("TALÁLAT", text), number=200))

# 2) Sok kulcsszó: egyetlen alternáció, a hosszabbak előre (balról az első nyer)
keywords = ["dolor", "amet", "TALÁLAT"]
ANY = re.compile("|".join(map(re.escape, sorted(keywords, key=len, reverse=True))))
print(len(ANY.findall(text)))

# 3) KMP: O(n + m), a szövegben sosem lép vissza
def kmp_search(text: str, pattern: str) -> list[int]:
    fail, k = [0] * len(pattern), 0       # fail[i]: pattern[:i+1] leghosszabb valódi prefix=szuffix
    for i in range(1, len(pattern)):
        while k and pattern[i] != pattern[k]:
            k = fail[k - 1]
        if pattern[i] == pattern[k]:
            k += 1
        fail[i] = k
    hits, k = [], 0
    for i, ch in enumerate(text):
        while k and ch != pattern[k]:
            k = fail[k - 1]               # csak a mintában ugrunk vissza
        if ch == pattern[k]:
            k += 1
        if k == len(pattern):
            hits.append(i - k + 1)
            k = fail[k - 1]               # átfedő találatok is
    return hits

print(kmp_search("abababcabababab", "ababab"))   # [0, 7, 9]

# 4) Stringépítés: join, nem += ciklusban
parts = [str(i) for i in range(100_000)]
print(timeit.timeit(lambda: "".join(parts), number=20))
```

## Szövegfeldolgozó pipeline-ok: grep, sed, awk és Python
<!-- q: Hogyan dolgozzak fel nagy szövegfájlokat parancssorban (grep, sed, awk) vagy Python generátorokkal? -->
<!-- tags: text processing pipeline, grep, sed, awk, sort, uniq, python generators, gzip, streaming -->

Nagy szövegfájlokat soronként, streamelve érdemes feldolgozni: a Unix-pipeline (`grep | awk | sort | uniq -c | sort -rn`) minden lépése párhuzamosan fut, és a memóriahasználat állandó. A `grep -F` fix stringre a leggyorsabb, az `LC_ALL=C` a bájtszintű összehasonlítással tovább gyorsít (de kikapcsolja a Unicode-tudatosságot), az awk oszlopokra bont és aggregál, a `sed -i.bak` mentéssel cserél helyben. Pythonban ugyanez generátorokkal: minden lépés egy lusta generátor, így gigabájtos (akár gzip-elt) fájl is állandó memóriával feldolgozható, és a lépések külön tesztelhetők. Ha a logika bonyolultabb egy egysoros awk-nál, válts Pythonra.

```bash
# Top 10 IP-cím az 5xx válaszok között (nginx combined log: $9 = státusz)
awk '$9 ~ /^5/ { print $1 }' access.log | sort | uniq -c | sort -rn | head -10

# Leggyakoribb útvonalak query string nélkül
grep -oE '"(GET|POST) [^ ?"]+' access.log | cut -d' ' -f2 | sort | uniq -c | sort -rn | head

# Jelszó-paraméter maszkolása helyben, biztonsági mentéssel
sed -E -i.bak 's/(password=)[^&[:space:]]+/\1***/g' app.log

# Oszlopösszeg és átlag egyszerű, idézőjel nélküli ;-s CSV-ből
awk -F';' 'NR > 1 { sum += $3; n++ } END { if (n) printf "összeg=%d átlag=%.2f\n", sum, sum / n }' sales.csv

# Tömörített log kicsomagolás nélkül; fix string + C locale = gyors
zcat access.log.gz | LC_ALL=C grep -F ' 502 ' | wc -l
```

```python
import gzip
import re
from collections import Counter
from pathlib import Path

LINE = re.compile(r'^(?P<ip>\S+) .*?"(?P<method>[A-Z]+) (?P<path>[^ ?"]+)[^"]*" (?P<status>\d{3}) ')

def read_lines(paths):
    for p in paths:                       # lusta: a fájl sosem kerül egészben memóriába
        opener = gzip.open if p.suffix == ".gz" else open
        with opener(p, "rt", encoding="utf-8", errors="replace") as f:
            yield from f

def parse(lines):
    for line in lines:
        if m := LINE.match(line):
            yield m.groupdict()

def only_server_errors(records):
    return (r for r in records if r["status"].startswith("5"))

paths = sorted(Path("logs").glob("access.log*"))
top = Counter(r["path"] for r in only_server_errors(parse(read_lines(paths)))).most_common(10)
for path, count in top:
    print(f"{count:6}  {path}")
```
