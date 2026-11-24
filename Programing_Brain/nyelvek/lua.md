# Lua
<!-- tech: lua -->
<!-- aliases: luajit, love2d, roblox -->

A Lua kicsi, gyors, dinamikusan típusos, beágyazásra tervezett szkriptnyelv: az interpreter néhány száz KB, tiszta ANSI C-ben íródott, és egyszerű C API-n keresztül illeszthető bármilyen alkalmazásba. Egyetlen összetett adatszerkezete a tábla, a metatáblákkal pedig operátor-túlterhelés, OOP és öröklés valósítható meg; van első osztályú függvény, closure, korutin és inkrementális/generációs GC. Elterjedt játékmotorokban (LÖVE, Defold, Roblox Luau), konfigurációban és bővítményekben (Neovim, Redis, Nginx/OpenResty, Wireshark); a LuaJIT JIT-fordítója és FFI-je kiemelkedő teljesítményt ad. Nagy, sokfejlesztős alkalmazás fő nyelvének kevésbé való (gyenge statikus ellenőrzés, kicsi standard könyvtár).

## Táblák: tömb, szótár és varargs
<!-- q: Hogyan használjam a táblákat Luában tömbként és szótárként, és hogyan kezeljem a varargs-ot? -->
<!-- tags: tables, arrays, dictionary, ipairs, pairs, length operator, varargs, table.pack -->

A tábla a Lua egyetlen összetett adatszerkezete: egyszerre asszociatív tömb (hash-rész) és 1-től indexelt tömb (tömb-rész), belőle épül minden modul, objektum és halmaz. Az `ipairs` sorrendben járja be a tömb-részt az első nil-ig, a `pairs` minden kulcsot bejár, de nem definiált sorrendben. A `#` hossz-operátor csak „lyukmentes” szekvenciánál megbízható, a táblák referencia szerint adódnak át (másoláshoz saját függvény kell). Változó számú argumentumnál a `...` mellett a `table.pack` (megőrzi a nil-eket, `n` mezővel) és a `select('#', ...)` ad pontos darabszámot.

```lua
local napok = { "hétfő", "kedd", "szerda" }                     -- tömb-rész: indexelés 1-től!
local termek = { sku = "KB-1", ar = 12990, ["mennyiség"] = 3 }   -- hash-rész

for i, nap in ipairs(napok) do print(i, nap) end   -- sorrendben, az első nil-ig
for k, v in pairs(termek) do print(k, v) end       -- minden kulcs, a sorrend NEM definiált

table.insert(napok, "csütörtök")           -- a végére
table.insert(napok, 1, "vasárnap")          -- az elejére (O(n): eltolja az elemeket)
local torolt = table.remove(napok, 1)       -- "vasárnap"
print(#napok, torolt)                       -- 4  vasárnap

-- Rendezés egyéni összehasonlítóval.
local termekek = {
  { nev = "Egér", ar = 4990 },
  { nev = "Monitor", ar = 64990 },
  { nev = "Kábel", ar = 990 },
}
table.sort(termekek, function(a, b) return a.ar < b.ar end)
print(termekek[1].nev)                      -- Kábel

-- Halmaz: az elemek kulcsok -> O(1) tagság-vizsgálat.
local tiltott = { admin = true, root = true }
print(tiltott.root == true, tiltott.vendeg == nil)

-- Varargs: table.pack megőrzi a nil-eket (n mező), select("#", ...) a darabszám.
local function osszeg(...)
  local args = table.pack(...)
  local s = 0
  for i = 1, args.n do
    s = s + (args[i] or 0)                  -- nil-ek kihagyása
  end
  return s, select("#", ...)
end
print(osszeg(1, nil, 3))                    -- 4  3

-- table.unpack: tábla -> több érték (LuaJIT / Lua 5.1: unpack)
print(math.max(table.unpack({ 7, 42, 3 }))) -- 42

-- Táblák referencia szerint adódnak át: másoláshoz saját függvény kell.
local function sekelyMasolat(t)
  local m = {}
  for k, v in pairs(t) do m[k] = v end
  return m
end
local masolat = sekelyMasolat(termek)
masolat.ar = 0
print(termek.ar, masolat.ar)                -- 12990  0
```

## Metatáblák és metametódusok
<!-- q: Hogyan működnek a metatáblák és a metametódusok (__index, __newindex, __add, __call) Luában? -->
<!-- tags: metatables, metamethods, __index, __newindex, __add, __call, __tostring, operator overloading -->

A metatábla egy tábla viselkedését testreszabó „kampók” (metametódusok) gyűjteménye, amit `setmetatable`-lel kapcsolunk egy táblához. Az `__index` a hiányzó kulcsok feloldását adja (táblaként: öröklés/metódusok, függvényként: alapértékek, számított mezők), a `__newindex` az új kulcsok írását fogja el, az aritmetikai és összehasonlító metametódusok (`__add`, `__mul`, `__eq`, `__lt`) operátor-túlterhelést, a `__call` hívhatóságot, a `__tostring` szöveges formát ad. Buktatók: a `__newindex` csak még nem létező kulcsra fut; táblán a `__len` és `__pairs` csak Lua 5.2+-ban érvényes (LuaJIT/5.1-ben nem); a `rawget`/`rawset` megkerüli a metametódusokat.

```lua
local Vektor = {}
Vektor.__index = Vektor                     -- metódusok keresése a Vektor táblában

local function uj(x, y) return setmetatable({ x = x, y = y }, Vektor) end

-- Operátor-túlterhelés
Vektor.__add = function(a, b) return uj(a.x + b.x, a.y + b.y) end
Vektor.__mul = function(a, b)
  if type(a) == "number" then return uj(a * b.x, a * b.y) end   -- 2 * v
  if type(b) == "number" then return uj(a.x * b, a.y * b) end   -- v * 2
  return a.x * b.x + a.y * b.y                                  -- skaláris szorzat
end
Vektor.__eq = function(a, b) return a.x == b.x and a.y == b.y end
Vektor.__len = function(v) return math.sqrt(v.x ^ 2 + v.y ^ 2) end   -- #v (Lua 5.2+)
Vektor.__tostring = function(v) return ("(%g, %g)"):format(v.x, v.y) end

local a, b = uj(1, 2), uj(3, 4)
print(tostring(a + b), tostring(2 * a), a * b, #b, a == uj(1, 2))   -- (4, 6) (2, 4) 11 5.0 true

-- __index függvényként: alapértékek
local beallitasok = setmetatable({}, {
  __index = function(_, kulcs) return ({ tema = "sötét", nyelv = "hu" })[kulcs] end,
})
print(beallitasok.tema)                     -- sötét (a tábla maga üres)

-- __newindex: csak olvasható proxy tábla
local function csakOlvashato(t)
  return setmetatable({}, {
    __index = t,
    __newindex = function(_, k) error("csak olvasható: " .. tostring(k), 2) end,
    __len = function() return #t end,
    __pairs = function() return next, t, nil end,   -- Lua 5.2+: pairs() a valódi adatot járja
  })
end
local KONST = csakOlvashato({ PI = 3.14159, E = 2.71828 })
print(pcall(function() KONST.PI = 3 end))   -- false  ...csak olvasható: PI

-- __call: hívható tábla, memoizáló cache-sel
local fib = setmetatable({ [0] = 0, [1] = 1 }, {
  __call = function(self, n)
    if self[n] == nil then self[n] = self(n - 1) + self(n - 2) end
    return self[n]
  end,
})
print(fib(80))                              -- 23416728348467685 (Lua 5.3+ egészekkel pontos)
```

## OOP metatáblákkal: osztályok és öröklés
<!-- q: Hogyan írjak osztályokat és öröklést Luában metatáblákkal? -->
<!-- tags: oop, classes, inheritance, metatables, self, colon syntax, constructor -->

Luában nincs beépített osztály: az osztály egy tábla a metódusokkal, amelynek `__index`-e önmagára mutat, a példány pedig egy tábla, amelynek metatáblája az osztály. A kettőspont-szintaxis (`function Szamla:befizet(x)` / `obj:befizet(x)`) implicit `self` paramétert ad át. Öröklésnél a leszármazott osztály metatáblájának `__index`-e a szülő osztály, a szülő metódusa pedig explicit módon hívható (`Szamla.kivesz(self, ...)`). Buktatók: a metametódusok (`__tostring`, `__add`) NEM öröklődnek `__index`-en át, ezeket át kell másolni; a `.` és `:` összekeverése a leggyakoribb hiba (nil `self`).

```lua
local Szamla = {}
Szamla.__index = Szamla

function Szamla.new(tulajdonos, egyenleg)
  local self = setmetatable({}, Szamla)
  self.tulajdonos = tulajdonos
  self.egyenleg = egyenleg or 0
  return self
end

-- ':' = implicit self paraméter: Szamla.befizet(self, osszeg)
function Szamla:befizet(osszeg)
  assert(osszeg > 0, "pozitív összeg kell")
  self.egyenleg = self.egyenleg + osszeg
  return self                               -- láncolható hívás
end

function Szamla:kivesz(osszeg)
  if osszeg > self.egyenleg then return nil, "nincs fedezet" end   -- nil + hibaüzenet idióma
  self.egyenleg = self.egyenleg - osszeg
  return self.egyenleg
end

function Szamla:__tostring()
  return ("%s: %d Ft"):format(self.tulajdonos, self.egyenleg)
end

-- Öröklés: a leszármazott __index-e a szülő osztály.
local Megtakaritas = setmetatable({}, { __index = Szamla })
Megtakaritas.__index = Megtakaritas
Megtakaritas.__tostring = Szamla.__tostring  -- a metametódusok NEM öröklődnek!

function Megtakaritas.new(tulajdonos, egyenleg, kamat)
  local self = Szamla.new(tulajdonos, egyenleg)   -- "super" konstruktor
  self.kamat = kamat
  return setmetatable(self, Megtakaritas)
end

function Megtakaritas:kivesz(osszeg)              -- felülírás (override)
  if osszeg > 100000 then return nil, "havi limit túllépve" end
  return Szamla.kivesz(self, osszeg)              -- szülő metódus explicit hívása
end

function Megtakaritas:kamatJovairas()
  return self:befizet(math.floor(self.egyenleg * self.kamat))
end

local m = Megtakaritas.new("Teszt", 500000, 0.05)
m:kamatJovairas():befizet(1000)
print(tostring(m))                       -- Teszt: 526000 Ft
print(m:kivesz(200000))                  -- nil  havi limit túllépve
print(m:kivesz(6000))                    -- 520000

-- Valóban privát állapot closure-rel:
local function Szamlalo()
  local n = 0
  return { novel = function() n = n + 1; return n end }
end
local sz = Szamlalo()
sz.novel()
print(sz.novel())                        -- 2
```

## Closure-ök és upvalue-k
<!-- q: Hogyan működnek a closure-ök és az upvalue-k Luában? -->
<!-- tags: closures, upvalues, higher-order functions, memoization, iterators, lexical scope -->

A Lua függvények első osztályú értékek, és lexikálisan befogják a környező lokális változókat — ezeket upvalue-knak hívjuk. Az ugyanabban a scope-ban létrejött closure-ök közös upvalue-n osztoznak, így közös, rejtett állapotot tarthatnak; a numerikus `for` ciklus viszont minden iterációban új lokális változót ad, így a ciklusban létrehozott closure-ök nem keverednek. Ezzel írható memoizálás, throttle, gyártófüggvény és állapottartó iterátor (a generikus `for` addig hívja, amíg nil-t nem ad). Buktató: a closure életben tartja a befogott táblákat is, ami nem szándékos memóriatartást okozhat.

```lua
local function szamlaloGyar()
  local n = 0                               -- upvalue, mindkét closure ugyanazt látja
  local function novel(lepes) n = n + (lepes or 1); return n end
  local function lekerdez() return n end
  return novel, lekerdez
end

local novel, lekerdez = szamlaloGyar()
novel(); novel(5)
print(lekerdez())                           -- 6

-- Minden iteráció ÚJ i változót kap.
local fuggvenyek = {}
for i = 1, 3 do
  fuggvenyek[i] = function() return i * 10 end
end
print(fuggvenyek[1](), fuggvenyek[3]())     -- 10  30

-- Memoizálás magasabb rendű függvénnyel.
local function memoize(f)
  local cache = {}
  return function(x)
    local v = cache[x]
    if v == nil then
      v = f(x)
      cache[x] = v
    end
    return v
  end
end

local dragaNegyzet = memoize(function(x)
  for _ = 1, 1e6 do end                     -- drága számítás szimulálása
  return x * x
end)
print(dragaNegyzet(12), dragaNegyzet(12))   -- a második hívás a cache-ből jön

-- Throttle: az utolsó hívás ideje upvalue-ban.
local function throttle(f, intervallum)
  local utolso = -math.huge
  return function(...)
    local most = os.clock()
    if most - utolso >= intervallum then
      utolso = most
      return f(...)
    end
  end
end
local log = throttle(print, 0.5)
log("első")                                 -- kiíródik
log("második")                              -- elnyelve

-- Állapottartó iterátor a generikus for-hoz.
local function tartomany(tol, ig, lepes)
  lepes = lepes or 1
  local i = tol - lepes
  return function()
    i = i + lepes
    if i <= ig then return i end            -- nil visszaadása zárja a ciklust
  end
end
for x in tartomany(0, 10, 5) do io.write(x, " ") end   -- 0 5 10
print()
```

## Korutinok: generátorok, pipeline, ütemező
<!-- q: Hogyan használjam a korutinokat Luában (coroutine.create, resume, yield, wrap)? -->
<!-- tags: coroutines, yield, resume, generators, producer consumer, scheduler, cooperative multitasking -->

A korutin saját veremmel rendelkező, kooperatív végrehajtási egység: a `coroutine.resume` elindítja vagy folytatja, a `coroutine.yield` felfüggeszti és értéket ad vissza, a `coroutine.wrap` pedig függvényként hívható korutint készít. Nincs valódi párhuzamosság (egy OS-szál), de nincs is versenyhelyzet, ezért ideális generátorokhoz, termelő–fogyasztó csővezetékekhez és játékokban „N frame-et várakozó” szkriptekhez. A `resume` hibánál nem dob, hanem `false, hibaüzenet`-et ad (ezt ellenőrizni kell), míg a `wrap` továbbdobja a hibát. Halott (`dead`) korutin nem folytatható.

```lua
-- 1) Generátor: lusta sorozat yield-del.
local function fibonacci(max)
  return coroutine.wrap(function()
    local a, b = 0, 1
    while a <= max do
      coroutine.yield(a)
      a, b = b, a + b
    end
  end)
end
for f in fibonacci(100) do io.write(f, " ") end
print()

-- 2) Termelő–szűrő pipeline.
local function termelo(sorok)
  return coroutine.create(function()
    for _, s in ipairs(sorok) do coroutine.yield(s) end
  end)
end

local function szuro(forras, feltetel)
  return coroutine.create(function()
    while true do
      local ok, sor = coroutine.resume(forras)
      if not ok then error(sor) end
      if sor == nil then return end         -- a forrás kimerült
      if feltetel(sor) then coroutine.yield(sor) end
    end
  end)
end

local naplo = { "INFO indul", "ERROR adatbázis", "INFO kész", "ERROR timeout" }
local hibak = szuro(termelo(naplo), function(s) return s:find("^ERROR") end)
while true do
  local _, sor = coroutine.resume(hibak)
  if sor == nil then break end
  print(sor)
end
print(coroutine.status(hibak))              -- dead

-- 3) Egyszerű ütemező: várakozó feladatok (pl. játékban tick-ek).
local feladatok = {}
local function indit(f) feladatok[#feladatok + 1] = coroutine.create(f) end
local function var(tick) for _ = 1, tick do coroutine.yield() end end

indit(function() print("A: start"); var(2); print("A: 2 tick után") end)
indit(function() print("B: start"); var(1); print("B: 1 tick után") end)

for _ = 1, 3 do                             -- fő ciklus (pl. love.update)
  for i = #feladatok, 1, -1 do              -- visszafelé: biztonságos törlés
    local co = feladatok[i]
    local ok, hiba = coroutine.resume(co)
    if not ok then print("hiba:", hiba) end
    if coroutine.status(co) == "dead" then table.remove(feladatok, i) end
  end
end
```

## Modulok és require
<!-- q: Hogyan írjak és töltsek be modulokat Luában (require, package.path)? -->
<!-- tags: modules, require, package.path, package.loaded, local, encapsulation -->

A modern Lua modul egy sima fájl, amely egy táblát ad vissza; a privát részek `local` változók és függvények, amelyek kívülről nem látszanak. A `require("nev")` a `package.path` mintái alapján keresi meg a fájlt (pl. `./?.lua;./?/init.lua`), egyszer lefuttatja, és az eredményt a `package.loaded` táblában cache-eli — a további `require` hívások ugyanazt a táblát adják. Opcionális függőség `pcall(require, ...)`-szal tölthető be biztonságosan. Buktatók: a `local` nélküli változók globálisak és minden modulba „kiszivárognak”; az 5.1-es `module()` függvény elavult.

```lua
-- Fájl: penz/init.lua  — require("penz") ezt (vagy penz.lua-t) tölti be
local M = {}                                -- a modul egy sima tábla

local DEVIZAK = { HUF = 0, EUR = 2, USD = 2 }   -- privát: local, kívülről nem látszik

local function kerekit(x, tizedes)          -- privát segédfüggvény
  local szorzo = 10 ^ tizedes
  return math.floor(x * szorzo + 0.5) / szorzo
end

function M.formaz(osszeg, deviza)
  local t = DEVIZAK[deviza]
  if not t then
    error(("ismeretlen deviza: %s"):format(tostring(deviza)), 2)   -- a hívó sorát jelöli
  end
  return ("%." .. t .. "f %s"):format(kerekit(osszeg, t), deviza)
end

function M.tamogatott(deviza) return DEVIZAK[deviza] ~= nil end

M.VERZIO = "1.2.0"

return M
```

```lua
-- Fájl: main.lua
package.path = "./lib/?.lua;./lib/?/init.lua;" .. package.path   -- keresési út bővítése

local penz = require("penz")                -- első betöltés: lefut a fájl
local ujra = require("penz")                -- cache-ből (package.loaded)
print(penz == ujra)                         -- true

print(penz.formaz(1234.567, "EUR"))         -- 1234.57 EUR
print(penz.formaz(1990, "HUF"))             -- 1990 HUF

-- Opcionális függőség biztonságos betöltése:
local ok, json = pcall(require, "cjson")
if not ok then
  json = nil
  print("cjson nem elérhető, tartalék kódoló kell")
end

-- Hot reload fejlesztéskor: törlés a cache-ből, majd újratöltés.
package.loaded["penz"] = nil
penz = require("penz")
print(penz.VERZIO, json ~= nil)
```

## Hibakezelés: error, pcall, xpcall
<!-- q: Hogyan kezeljem a hibákat Luában (error, pcall, xpcall, assert)? -->
<!-- tags: error handling, pcall, xpcall, error, assert, traceback, error objects -->

Luában az `error()` bármilyen értéket „dobhat” (stringet vagy strukturált táblát), a `pcall` védett hívásban elkapja és `false, hibaérték`-et ad vissza, az `xpcall` pedig egy üzenetkezelőt futtat a hiba helyén — csak ott készíthető teljes stack trace (`debug.traceback`). Az `error` második paramétere (szint) azt szabályozza, melyik sor pozíciója kerüljön az üzenetbe (2 = a hívóé, 0 = semmi). Várható hibáknál (fájl nem létezik) az idiomatikus forma a `nil, hibaüzenet` visszatérés (így működik az `io.open` is), amit az `assert` kivétellé alakíthat. Nincs `finally`: a takarítást a `pcall` után kell elvégezni.

```lua
local ValidaciosHiba = {}
ValidaciosHiba.__index = ValidaciosHiba
ValidaciosHiba.__tostring = function(e)
  return ("ValidaciosHiba[%s]: %s"):format(e.mezo, e.uzenet)
end

local function validal(felhasznalo)
  if type(felhasznalo.email) ~= "string" or not felhasznalo.email:find("@", 1, true) then
    -- tábla-hiba: strukturált adat, amit a hívó megvizsgálhat
    error(setmetatable({ mezo = "email", uzenet = "érvénytelen formátum" }, ValidaciosHiba))
  end
  if (felhasznalo.kor or 0) < 18 then
    error("túl fiatal: " .. tostring(felhasznalo.kor), 2)   -- szint 2: a hívó sora
  end
  return true
end

local esetek = { { email = "a@b.hu", kor = 30 }, { email = "rossz" }, { email = "x@y.hu", kor = 12 } }
for _, f in ipairs(esetek) do
  local ok, hiba = pcall(validal, f)        -- (true, ...) vagy (false, hibaérték)
  if ok then
    print("OK")
  elseif getmetatable(hiba) == ValidaciosHiba then
    print("validáció:", tostring(hiba))
  else
    print("egyéb hiba:", hiba)              -- "fajl.lua:NN: túl fiatal: 12"
  end
end

-- xpcall: a traceback a hiba HELYÉN készül (pcall után már késő).
local function feldolgoz(adat)
  return adat.mezo.almezo                   -- nil indexelése -> futásidejű hiba
end
local ok, trace = xpcall(feldolgoz, function(e)
  return debug.traceback(tostring(e), 2)
end, {})                                    -- extra argumentum: Lua 5.2+ / LuaJIT
print(ok, trace)

-- "nil, hibaüzenet" konvenció várható hibákra:
local fajl, err = io.open("/nem/letezo.txt", "r")
if not fajl then print("megnyitás sikertelen:", err) end

local szam = assert(tonumber("42"), "nem szám")   -- hiba esetén dob
print(szam)

-- Takarítás "finally" nélkül: lezárás minden ágon.
local function fajlbaIr(ut, tartalom)
  local f = assert(io.open(ut, "w"))
  local okIras, e = pcall(f.write, f, tartalom)
  f:close()                                 -- hiba esetén is lezárjuk
  if not okIras then error(e, 0) end        -- szint 0: ne fűzzön hozzá pozíciót
end
```

## String minták (patterns)
<!-- q: Hogyan használjam a Lua string mintákat (match, gmatch, gsub)? -->
<!-- tags: string patterns, string.match, gmatch, gsub, captures, frontier pattern, utf8 -->

A Lua minták egyszerűbbek a reguláris kifejezéseknél: nincs alternáció (`|`), nincs `{n,m}`, a kvantorok (`*`, `+`, `-`, `?`) mindig csak egy karakterosztályra vonatkoznak, és az escape karakter a `%` (nem a `\`). Karakterosztályok: `%d` számjegy, `%a` betű, `%s` whitespace, `%w` alfanumerikus, `%p` írásjel (nagybetűs változatuk a tagadás); különlegességek a lusta `-` kvantor, a `%b()` kiegyensúlyozott zárójelpár és a `%f[...]` határminta (szóhatár). A `match` kinyer, a `gmatch` iterál, a `gsub` cserél (stringgel, táblával vagy függvénnyel) és a cserék számát is visszaadja. Buktató: a stringfüggvények és a `#` bájtokat számolnak, UTF-8 szöveghez az `utf8` könyvtár kell (Lua 5.3+).

```lua
-- 1) Kinyerés capture-ökkel
local sor = "2026-03-15 08:42:17 [ERROR] db: connection refused (code=111)"
local datum, ido, szint, uzenet = sor:match("^(%d+%-%d+%-%d+) (%d+:%d+:%d+) %[(%u+)%] (.+)$")
print(datum, ido, szint, uzenet)

-- 2) Iterálás: key=value párok
local params = {}
for k, v in ("lang=lua&page=2&sort=desc"):gmatch("([^&=]+)=([^&=]*)") do
  params[k] = v
end
print(params.lang, params.page)             -- lua  2

-- 3) Csere táblával (sablon kitöltése)
local sablon = "Kedves ${nev}! Rendelésed (${azon}) úton van."
print((sablon:gsub("%${(%w+)}", { nev = "Teszt Elek", azon = "R-1042" })))

-- A gsub második visszatérési értéke a cserék száma
local _, db = ("a,b,,c"):gsub(",", ",")
print("vesszők:", db)                       -- 3

-- 4) Trim és split
local function trim(s) return (s:gsub("^%s+", ""):gsub("%s+$", "")) end
local function split(s, sep)
  local out = {}
  local mintaSep = sep:gsub("%p", "%%%0")   -- az elválasztó escape-elése
  for resz in (s .. sep):gmatch("(.-)" .. mintaSep) do
    out[#out + 1] = resz
  end
  return out
end
print("[" .. trim("   szóköz   ") .. "]", #split("a;b;;c", ";"))   -- [szóköz]  4

-- 5) Lusta (-) vs mohó (*) kvantor, és %b() kiegyensúlyozott zárójel
print(("<b>egy</b><b>kettő</b>"):match("<b>(.-)</b>"))   -- egy
print(("f(a, g(b, c), d)"):match("%b()"))                -- (a, g(b, c), d)

-- 6) %f határminta: csak egész szavas csere
print(("cat concat cat"):gsub("%f[%w]cat%f[%W]", "kutya"))   -- kutya concat kutya  2

-- Buktató: # bájtokat számol; UTF-8-hoz utf8.len (Lua 5.3+)
print(#"árvíz", utf8 and utf8.len("árvíz"))   -- 7  5
```

## Teljesítmény, GC és gyenge táblák
<!-- q: Hogyan írjak gyors Lua kódot, és hogyan működik a szemétgyűjtés és a gyenge tábla? -->
<!-- tags: performance, garbage collection, weak tables, __mode, table.concat, locals, collectgarbage -->

A lokális változók regiszterekben élnek, a globálisok viszont táblakeresést jelentenek, ezért a gyakran használt függvényeket (`math.floor`) érdemes lokálisba menteni. A stringek immutable-ek, így a ciklusban végzett `..` összefűzés O(n²) — helyette táblába gyűjts és `table.concat`-ot használj; forró ciklusban kerüld a sok kis ideiglenes tábla létrehozását, mert az GC-terhelést okoz. A gyenge tábla (`__mode = "k"` vagy `"v"`) nem tartja életben a kulcsait/értékeit, így cache és objektumhoz rendelt metaadat szivárgás nélkül tárolható. A GC `collectgarbage`-dzsel hangolható (Lua 5.4-ben generációs mód is van).

```lua
local floor = math.floor                    -- gyakran használt függvény lokálisba mentve

-- Stringépítés: .. ciklusban O(n²), table.concat O(n)
local function lassuEpites(n)
  local s = ""
  for i = 1, n do s = s .. i .. "," end
  return s
end
local function gyorsEpites(n)
  local t = {}
  for i = 1, n do t[#t + 1] = i end         -- gyorsabb, mint a table.insert
  return table.concat(t, ",")
end

local function mer(nev, f, ...)
  local t0 = os.clock()
  f(...)
  print(("%-14s %.3f s"):format(nev, os.clock() - t0))
end
mer("konkatenálás", lassuEpites, 20000)
mer("table.concat", gyorsEpites, 20000)

-- Meglévő tábla újrahasznosítása forró ciklusban (kevesebb GC-szemét).
local eredmeny = {}
local function pontokOsszege(pontok)
  local sx, sy = 0, 0
  for i = 1, #pontok do
    local p = pontok[i]                     -- egyszeri indexelés lokálisba
    sx, sy = sx + p[1], sy + p[2]
  end
  eredmeny[1], eredmeny[2] = sx, sy
  return eredmeny
end
print(floor(pontokOsszege({ { 1, 2 }, { 3, 4 } })[1]))   -- 4

-- Gyenge kulcsú tábla: nem tartja életben az objektumot.
local metaadat = setmetatable({}, { __mode = "k" })
do
  local obj = {}
  metaadat[obj] = { letrehozva = os.time() }
end                                         -- obj elérhetetlenné vált
collectgarbage("collect")
local db = 0
for _ in pairs(metaadat) do db = db + 1 end
print("gyenge táblában maradt:", db)        -- 0

-- GC hangolása és memóriahasználat
if _VERSION == "Lua 5.4" then collectgarbage("generational") end
print(("memória: %.1f KB"):format(collectgarbage("count")))
```

## Lua beágyazása C-be (C API)
<!-- q: Hogyan ágyazzam be a Luát egy C programba, és hogyan hívjak C függvényt Luából? -->
<!-- tags: c api, embedding, lua_State, virtual stack, lua_pcall, luaL_newlib, host application -->

A Lua C API egy virtuális vermen keresztül cserél adatot a host és a szkript között: a C oldal értékeket tol a verembe (`lua_pushnumber`), olvas belőle (`luaL_checknumber`, negatív index = a verem tetejétől), és függvényt hív (`lua_pcall`). A Luából hívható C függvény szignatúrája `int f(lua_State *L)`, a visszatérési érték az eredmények száma; modulként `luaL_newlib`-bel regisztrálható. A `luaL_newstate` független interpretert hoz létre — homokozóhoz csak a szükséges könyvtárakat nyisd meg, ne a teljes `luaL_openlibs`-t. Buktatók: a vermet minden hívás után ki kell egyensúlyozni (`lua_pop`), és Lua-hiba C-ben longjmp-pel ugrik, ezért a C oldali erőforrásokat óvatosan kezeld.

```c
// host.c — Lua 5.4 beágyazása. Fordítás: cc host.c -llua -lm -o host
#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>
#include <stdio.h>

// Luából hívható C függvény: az argumentumok a vermen (1-től indexelve).
static int l_szazalek(lua_State *L) {
    lua_Number resz = luaL_checknumber(L, 1);   // típusellenőrzés + Lua-hiba, ha rossz
    lua_Number egesz = luaL_checknumber(L, 2);
    if (egesz == 0) {
        return luaL_error(L, "nullával osztás");
    }
    lua_pushnumber(L, resz / egesz * 100.0);    // eredmény a verembe
    return 1;                                    // 1 visszatérési érték
}

static const luaL_Reg app_fuggvenyek[] = {
    {"szazalek", l_szazalek},
    {NULL, NULL}
};

int main(void) {
    lua_State *L = luaL_newstate();             // független interpreter-állapot
    luaL_openlibs(L);                           // homokozóhoz: csak a szükséges könyvtárak!

    luaL_newlib(L, app_fuggvenyek);             // modul-tábla a verem tetején
    lua_setglobal(L, "app");                    // app = <tábla>

    lua_newtable(L);                            // konfiguráció átadása táblaként
    lua_pushinteger(L, 8);
    lua_setfield(L, -2, "workerek");            // konfig.workerek = 8 (-2: a tábla)
    lua_setglobal(L, "konfig");

    if (luaL_dofile(L, "script.lua") != LUA_OK) {
        fprintf(stderr, "Lua hiba: %s\n", lua_tostring(L, -1));
        lua_pop(L, 1);
    }

    // Lua függvény hívása C-ből: függvény + argumentumok a verembe, majd pcall.
    lua_getglobal(L, "ertekel");
    lua_pushstring(L, "teszt");
    if (lua_pcall(L, 1, 1, 0) == LUA_OK) {      // 1 argumentum, 1 eredmény
        printf("pontszám: %lld\n", (long long)lua_tointeger(L, -1));
    } else {
        fprintf(stderr, "hívási hiba: %s\n", lua_tostring(L, -1));
    }
    lua_pop(L, 1);                              // verem kiegyensúlyozása!

    lua_close(L);                               // minden erőforrás felszabadítása
    return 0;
}
```

```lua
-- script.lua — a host tölti be; az app és a konfig globálist a C oldal adja
print("workerek:", konfig.workerek)
print(("készültség: %.1f%%"):format(app.szazalek(37, 120)))

function ertekel(nev)                       -- globális, hogy a C oldal megtalálja
  return #nev * 10
end
```

## LuaJIT FFI
<!-- q: Hogyan hívjak C függvényeket és használjak C struktúrákat LuaJIT FFI-vel? -->
<!-- tags: luajit, ffi, cdef, cdata, metatype, c interop, performance -->

A LuaJIT `ffi` könyvtára kötéskód (binding) írása nélkül hív C függvényeket és kezel C adatszerkezeteket: a deklarációkat az `ffi.cdef`-be kell bemásolni, a hívás `ffi.C.fuggveny(...)` (vagy `ffi.load`-dal betöltött könyvtár) formájú. A JIT a C hívásokat közvetlenül gépi kódba fordítja, ezért sokkal gyorsabb a klasszikus C API-nál, a `ffi.new`-val létrehozott C tömbök pedig tömörek és GC-kezeltek. Az `ffi.metatype` metódusokat és operátorokat ad egy C struktúrához. Buktatók: nincs biztonsági háló (rossz `cdef` = crash), a C tömbök 0-tól indexelődnek, a `malloc`-olt memóriát `ffi.gc`-vel kell felszabadításhoz kötni, és a C-nek átadott cdata-t életben kell tartani, amíg a C használja.

```lua
local ffi = require("ffi")

-- C deklarációk (a fejlécek releváns része).
ffi.cdef [[
  typedef struct { double x, y; } pont_t;
  int printf(const char *fmt, ...);
  size_t strlen(const char *s);
  void *malloc(size_t size);
  void free(void *ptr);
]]

local C = ffi.C                              -- a folyamatba már betöltött C könyvtár (libc)

C.printf("%s: %d elem\n", "FFI", ffi.new("int", 42))
print(tonumber(C.strlen("árvíz")))           -- 7 (bájt)

-- C struktúra-tömb: tömör memória, nincs Lua-tábla overhead.
local N = 1000000
local pontok = ffi.new("pont_t[?]", N)       -- VLA: nullázva, a GC felszabadítja
for i = 0, N - 1 do                          -- C tömb: 0-tól indexelve!
  pontok[i].x = i
  pontok[i].y = i * 0.5
end
local sx = 0
for i = 0, N - 1 do sx = sx + pontok[i].x end
print("összeg:", sx, "méret:", ffi.sizeof("pont_t") * N, "bájt")

-- Metatípus: metódusok és operátorok C struktúrán.
local Pont
Pont = ffi.metatype("pont_t", {
  __add = function(a, b) return Pont(a.x + b.x, a.y + b.y) end,
  __tostring = function(p) return ("pont(%g, %g)"):format(p.x, p.y) end,
  __index = {
    hossz = function(p) return math.sqrt(p.x * p.x + p.y * p.y) end,
  },
})
local p = Pont(3, 4) + Pont(0, 0)
print(tostring(p), p:hossz())                -- pont(3, 4)  5

-- Kézi memória: a malloc-olt területet a GC nem ismeri -> ffi.gc finalizer.
local buf = ffi.gc(ffi.cast("uint8_t *", C.malloc(4096)), C.free)
ffi.fill(buf, 4096, 0)
buf[0] = 255
print(buf[0])                                -- 255

-- Külső könyvtár: local z = ffi.load("z")  (libz.so / z.dll)
```

## Játékfejlesztés: LÖVE és Roblox Luau
<!-- q: Hogyan épül fel egy LÖVE (love2d) játékciklus, és miben más a Roblox Luau? -->
<!-- tags: love2d, game loop, delta time, love.update, love.draw, roblox, luau, game development -->

A LÖVE (love2d) keretrendszer a `love.load` (indulás), `love.update(dt)` (logika) és `love.draw` (rajzolás) callbackeket hívja minden frame-ben, a bemenetet pedig `love.keypressed` és társai jelzik. Minden mozgást a `dt` (előző frame óta eltelt idő) értékével kell szorozni, így a játékmenet független a frame rate-től; a `draw`-ban csak rajzolj, állapotot ne módosíts. A Roblox Luau a Lua 5.1 bővített változata fokozatos típusrendszerrel (`--!strict`, típusannotációk), összetett értékadással (`+=`) és saját `task` ütemezővel; a játékos kilépésekor a hozzá kötött adatokat törölni kell, különben memóriaszivárgás lesz.

```lua
-- main.lua — LÖVE 11.x
local jatekos = { x = 400, y = 300, sebesseg = 220, meret = 24 }
local lovedekek = {}

function love.load()
  love.window.setTitle("Mini lövöldözős")
  love.graphics.setBackgroundColor(0.08, 0.09, 0.12)
end

-- dt: az előző frame óta eltelt idő (s) -> frame-rate független mozgás
function love.update(dt)
  local dx, dy = 0, 0
  if love.keyboard.isDown("a", "left") then dx = dx - 1 end
  if love.keyboard.isDown("d", "right") then dx = dx + 1 end
  if love.keyboard.isDown("w", "up") then dy = dy - 1 end
  if love.keyboard.isDown("s", "down") then dy = dy + 1 end
  if dx ~= 0 and dy ~= 0 then dx, dy = dx * 0.7071, dy * 0.7071 end   -- átló normalizálása
  jatekos.x = jatekos.x + dx * jatekos.sebesseg * dt
  jatekos.y = jatekos.y + dy * jatekos.sebesseg * dt

  for i = #lovedekek, 1, -1 do               -- visszafelé: biztonságos törlés
    local l = lovedekek[i]
    l.y = l.y - 500 * dt
    if l.y < -10 then table.remove(lovedekek, i) end
  end
end

function love.keypressed(gomb)
  if gomb == "space" then
    lovedekek[#lovedekek + 1] = { x = jatekos.x, y = jatekos.y - jatekos.meret }
  elseif gomb == "escape" then
    love.event.quit()
  end
end

-- draw: csak rajzol, állapotot nem módosít
function love.draw()
  love.graphics.setColor(0.3, 0.8, 1)
  love.graphics.circle("fill", jatekos.x, jatekos.y, jatekos.meret)
  love.graphics.setColor(1, 0.9, 0.3)
  for _, l in ipairs(lovedekek) do
    love.graphics.rectangle("fill", l.x - 2, l.y, 4, 10)
  end
  love.graphics.setColor(1, 1, 1)
  love.graphics.print(("Lövedékek: %d  FPS: %d"):format(#lovedekek, love.timer.getFPS()), 10, 10)
end
```

```luau
--!strict
-- Roblox Luau (ServerScriptService): típusannotációk, task ütemező.
local Players = game:GetService("Players")

type Statisztika = { pont: number, szint: number }
local adatok: { [Player]: Statisztika } = {}

local function pontHozzaad(jatekos: Player, mennyi: number): number
  local s = adatok[jatekos]
  if not s then return 0 end
  s.pont += mennyi                            -- Luau: összetett értékadás
  s.szint = 1 + s.pont // 1000                -- egész osztás
  local ls = jatekos:FindFirstChild("leaderstats")
  local pontErtek = ls and ls:FindFirstChild("Pont")
  if pontErtek and pontErtek:IsA("IntValue") then pontErtek.Value = s.pont end
  return s.pont
end

Players.PlayerAdded:Connect(function(jatekos: Player)
  adatok[jatekos] = { pont = 0, szint = 1 }
  local ls = Instance.new("Folder")
  ls.Name = "leaderstats"                     -- a beépített ranglista ezt mutatja
  local p = Instance.new("IntValue")
  p.Name = "Pont"
  p.Parent = ls
  ls.Parent = jatekos
  task.delay(5, pontHozzaad, jatekos, 100)    -- task könyvtár (nem az elavult wait())
end)

Players.PlayerRemoving:Connect(function(jatekos: Player)
  adatok[jatekos] = nil                       -- memóriaszivárgás elkerülése
end)
```
