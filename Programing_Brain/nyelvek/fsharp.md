# F#
<!-- tech: fsharp -->
<!-- aliases: f# -->

Az F# a .NET funkcionális-első nyelve: erős, statikus típusrendszerrel és Hindley–Milner-szerű típuskikövetkeztetéssel, alapértelmezett immutabilitással, algebrai adattípusokkal (rekordok, discriminated unionok) és mintaillesztéssel. Ugyanarra a CLR-re fordul, mint a C#, így a teljes .NET ökoszisztéma (NuGet, ASP.NET Core, EF) elérhető, és jól keverhető C# projektekkel. Kiváló üzleti logika- és domain-modellezésre („make illegal states unrepresentable”), adatfeldolgozásra, pénzügyi és tudományos számításokra, parserekre és fordítókra; az `fsi` REPL és a `.fsx` szkriptek gyors kísérletezést adnak. Hátránya a kisebb közösség és tooling, a fájlsorrend-függő fordítás, valamint hogy erősen OOP-centrikus (UI-) keretrendszerekben kevésbé természetes.

## Immutabilitás, let kötések és rekordok
<!-- q: Hogyan működik az immutabilitás és a rekordok F#-ban? -->
<!-- tags: immutability, let, records, copy and update, structural equality, map, set -->

F#-ban a `let` kötések alapból nem módosíthatók, a rekordok és a gyűjtemények (list, Map, Set) is immutábilisak; „módosításkor” új érték jön létre, ami strukturális megosztás miatt olcsó. A rekordok strukturális egyenlőséget és összehasonlítást kapnak, a `{ r with ... }` kifejezés másolatot készít a megadott mezők cseréjével. Ha teljesítmény miatt mutáció kell, használd a `mutable` kulcsszót lokálisan, szűk hatókörrel. Buktató: a .NET osztályok (pl. `Dictionary`, tömb) ettől még mutábilisak maradnak.

```fsharp
type Address = { City: string; Zip: string }
type Person = { Name: string; Age: int; Address: Address }

let p1 = { Name = "Teszt Elek"; Age = 30; Address = { City = "Kecskemét"; Zip = "6000" } }

// Copy-and-update: p1 érintetlen marad, a beágyazott rekordot is másoljuk
let p2 = { p1 with Age = 31; Address = { p1.Address with Zip = "6001" } }

// Strukturális egyenlőség: mezőnként hasonlít
printfn "%b" (p1 = { p2 with Age = 30; Address = p1.Address })   // true

// Lokális, kívülről láthatatlan mutáció teljesítménykritikus ciklushoz
let sumSquares (xs: int list) =
    let mutable acc = 0
    for x in xs do acc <- acc + x * x
    acc

// Immutábilis Map: minden művelet új Map-et ad
let inventory = Map.ofList [ "alma", 10; "körte", 4 ]
let restocked =
    inventory
    |> Map.change "körte" (Option.map ((+) 6))   // meglévő kulcs frissítése
    |> Map.add "szilva" 3

printfn "%A -> %A" inventory restocked
printfn "%d" (sumSquares [ 1; 2; 3 ])   // 14
```

## Discriminated unionok
<!-- q: Mik a discriminated unionok F#-ban és hogyan modellezzek velük domaint? -->
<!-- tags: discriminated union, algebraic data types, sum types, domain modeling, single case union -->

A discriminated union (DU) egy „vagy-vagy” típus: az érték pontosan egy esetet vesz fel, és minden esethez saját adat tartozhat. Ezzel az érvénytelen állapotok egyszerűen nem ábrázolhatók (például a kifizetett rendelésnek mindig van fizetési módja), és ha új esetet adsz hozzá, a fordító minden hiányos mintaillesztésre figyelmeztet. A rekurzív DU fákat és kifejezéseket ír le, a single-case union privát konstruktorral pedig validált „wrapper” típust ad primitívek köré (Email, OrderId).

```fsharp
type PaymentMethod =
    | Cash
    | Card of last4: string * expiry: (int * int)
    | Transfer of iban: string

type OrderState =
    | Draft
    | Placed of placedAt: System.DateTime
    | Paid of PaymentMethod * amount: decimal
    | Shipped of trackingId: string
    | Cancelled of reason: string

// Rekurzív DU: aritmetikai kifejezésfa
type Expr =
    | Num of float
    | Var of string
    | Add of Expr * Expr
    | Mul of Expr * Expr

let rec eval (env: Map<string, float>) expr =
    match expr with
    | Num n -> n
    | Var v -> env |> Map.tryFind v |> Option.defaultWith (fun () -> failwithf "Ismeretlen változó: %s" v)
    | Add (a, b) -> eval env a + eval env b
    | Mul (a, b) -> eval env a * eval env b

// Single-case union privát konstruktorral: csak validáltan hozható létre
type Email = private Email of string

module Email =
    let create (s: string) =
        if s.Contains "@" then Ok (Email s) else Error $"Érvénytelen email: {s}"
    let value (Email s) = s

let describe state =
    match state with
    | Draft -> "piszkozat"
    | Placed at -> "leadva: " + at.ToString("yyyy-MM-dd")
    | Paid (Card (last4, _), amt) -> $"kártyával fizetve (**{last4}), {amt} Ft"
    | Paid (_, amt) -> $"fizetve: {amt} Ft"
    | Shipped id -> $"úton: {id}"
    | Cancelled r -> $"törölve: {r}"

printfn "%f" (eval (Map.ofList [ "x", 2.0 ]) (Add (Num 1.0, Mul (Var "x", Num 3.0))))   // 7.0
printfn "%s" (describe (Paid (Card ("4242", (12, 2027)), 15000m)))
printfn "%A" (Email.create "nem-email")
```

## Mintaillesztés
<!-- q: Hogyan használjam a pattern matchinget F#-ban? -->
<!-- tags: pattern matching, match, guards, list patterns, type test, function keyword -->

A `match` kifejezés DU-esetekre, tuple-ökre, listákra (`[]`, `x :: rest`, `[a; b]`), rekordmezőkre, konstansokra és típusokra (`:? string as s`) illeszt, `when` guarddal kiegészítve. Kifejezés, tehát értéket ad, és a fordító ellenőrzi a teljességet — a hiányzó esetre figyelmeztet, ami a refaktorálás egyik legjobb védőhálója. A `function` kulcsszó egyargumentumú illesztő lambdát ad. Buktató: a `_` wildcard túl korai használata elnyeli a később hozzáadott eseteket, és a sorrend számít.

```fsharp
type Shape =
    | Circle of r: float
    | Rect of w: float * h: float
    | Triangle of a: float * b: float * c: float

let area shape =
    match shape with
    | Circle r when r <= 0.0 -> 0.0                // guard
    | Circle r -> System.Math.PI * r * r
    | Rect (w, h) -> w * h
    | Triangle (a, b, c) ->
        let s = (a + b + c) / 2.0                     // Hérón-képlet
        sqrt (s * (s - a) * (s - b) * (s - c))

// Lista minták
let summarize (xs: int list) =
    match xs with
    | [] -> "üres"
    | [ x ] -> $"egy elem: {x}"
    | [ x; y ] -> $"kettő: {x}, {y}"
    | x :: rest -> $"{x}, majd még {List.length rest}"

// Tuple-minta döntési táblaként
let classify n =
    match n % 3, n % 5 with
    | 0, 0 -> "FizzBuzz"
    | 0, _ -> "Fizz"
    | _, 0 -> "Buzz"
    | _ -> string n

// Típustesztelő minta .NET objektumokra
let describeObj (o: obj) =
    match o with
    | :? string as s when s.Length > 10 -> "hosszú szöveg"
    | :? string as s -> $"szöveg: {s}"
    | :? int | :? int64 -> "egész szám"
    | :? System.Collections.IEnumerable -> "gyűjtemény"
    | null -> "null"
    | _ -> o.GetType().Name

// Rekordminta 'function'-nel: csak a lényeges mezők
type Http = { Status: int; Body: string }
let handle = function
    | { Status = 200; Body = b } -> Ok b
    | { Status = s } when s >= 500 -> Error "szerverhiba — újrapróbálható"
    | { Status = s } -> Error $"kliens hiba: {s}"

[ Circle 1.0; Rect (2.0, 3.0); Triangle (3.0, 4.0, 5.0) ] |> List.iter (area >> printfn "%.2f")
printfn "%s | %s" (summarize [ 1; 2; 3 ]) (classify 15)
printfn "%s | %A" (describeObj [ 1; 2 ]) (handle { Status = 503; Body = "" })
```

## Pipeline, kompozíció és currying
<!-- q: Hogyan működik a |> pipe operátor és a függvénykompozíció F#-ban? -->
<!-- tags: pipeline, pipe operator, composition, currying, partial application, point-free -->

A `|>` operátor az előző kifejezés értékét a következő függvény utolsó argumentumaként adja át, így az adatfeldolgozás balról jobbra, lépésenként olvasható, és a típuskikövetkeztetés is jobban működik. A `>>` két függvényből újat komponál, ami pont-mentes (point-free) stílust enged. Mivel minden függvény curried, a részleges alkalmazással „konfigurált” függvényeket készíthetsz; ezért az API-kban az adatot (amin dolgozunk) érdemes utolsó paraméternek tenni. Buktató: a túl hosszú pont-mentes láncok nehezen debugolhatók — nevesíts köztes lépéseket.

```fsharp
open System

type LogLine = { Level: string; Source: string; Message: string }

let parse (line: string) =
    match line.Split('|') with
    | [| lvl; src; msg |] -> Some { Level = lvl.Trim(); Source = src.Trim(); Message = msg.Trim() }
    | _ -> None

let lines =
    [ "ERROR | db  | timeout after 30s"
      "INFO  | web | GET /api 200"
      "ERROR | web | null reference"
      "ERROR | db  | deadlock"
      "hibás sor" ]

// Balról jobbra olvasható adatfolyam
let errorsBySource =
    lines
    |> List.choose parse                    // parse + None-ok eldobása egy lépésben
    |> List.filter (fun l -> l.Level = "ERROR")
    |> List.countBy (fun l -> l.Source)
    |> List.sortByDescending snd            // [("db", 2); ("web", 1)]

// >> : kompozíció
let normalize: string -> string = (fun s -> s.Trim()) >> (fun s -> s.ToLowerInvariant())
let isBlank = String.IsNullOrWhiteSpace
let cleanWords = List.map normalize >> List.filter (isBlank >> not) >> List.distinct

// Részleges alkalmazás
let between lo hi x = x >= lo && x <= hi
let isPercent = between 0 100

printfn "%A" errorsBySource
printfn "%A" (cleanWords [ " Alma"; "alma "; ""; "Körte" ])   // ["alma"; "körte"]
printfn "%b %b" (isPercent 42) (isPercent 120)
```

## Option, Result és railway-oriented hibakezelés
<!-- q: Hogyan kezeljem a hibákat kivételek helyett Result és Option típussal F#-ban? -->
<!-- tags: option, result, railway oriented programming, error handling, validation, bind -->

Az `Option<'T>` a hiányzó értéket fejezi ki null helyett, a `Result<'T,'E>` pedig a várható hibát kivétel helyett, így a hiba a típusszignatúrában is látszik. A `Result.bind`/`Option.map` láncolása a „railway-oriented” stílus: amíg minden `Ok`, a feldolgozás halad, az első `Error` „kisiklatja” és a többi lépés kimarad. Ha nem az első, hanem az összes hibát akarod (űrlapvalidáció), több eredményt egyszerre illeszts, és gyűjtsd listába a hibákat. Kivételt csak valóban kivételes, nem kezelhető helyzetre (programhiba, erőforrás-hiány) használj.

```fsharp
type ValidationError =
    | Missing of field: string
    | TooShort of field: string * min: int
    | InvalidAge of int

type Registration = { UserName: string; Age: int }

let required field (value: string) =
    if System.String.IsNullOrWhiteSpace value then Error (Missing field) else Ok value

let minLength field n (value: string) =
    if value.Length < n then Error (TooShort (field, n)) else Ok value

let parseAge (s: string) =
    match System.Int32.TryParse s with
    | true, a when a >= 18 && a < 130 -> Ok a
    | true, a -> Error (InvalidAge a)
    | false, _ -> Error (Missing "age")

// Az első hibánál megáll (bind), a két mező hibáit viszont összegyűjtjük
let validate (name: string) (age: string) =
    let nameResult = name |> required "userName" |> Result.bind (minLength "userName" 3)
    match nameResult, parseAge age with
    | Ok n, Ok a -> Ok { UserName = n; Age = a }
    | Error e, Ok _
    | Ok _, Error e -> Error [ e ]
    | Error e1, Error e2 -> Error [ e1; e2 ]

// Option: kedvezménykód keresése
let tryFindDiscount (code: string) =
    [ "TAVASZ10", 0.10m; "VIP25", 0.25m ]
    |> List.tryFind (fst >> (=) code)
    |> Option.map snd

let finalPrice price code =
    tryFindDiscount code
    |> Option.map (fun d -> price * (1m - d))
    |> Option.defaultValue price

printfn "%A" (validate "al" "15")      // Error [TooShort ("userName", 3); InvalidAge 15]
printfn "%A" (validate "alex" "25")    // Ok { UserName = "alex"; Age = 25 }
printfn "%M" (finalPrice 1000m "VIP25") // 750
```

## List, Array, Seq: mohó és lusta gyűjtemények
<!-- q: Mi a különbség a List, Array és Seq között F#-ban és mikor melyiket használjam? -->
<!-- tags: list, array, seq, lazy evaluation, seq expression, collections, performance -->

A `list` immutábilis láncolt lista (O(1) elejére fűzés, O(n) indexelés), az `array` mutábilis, folytonos memória (gyors indexelés, numerikus munka, `Array.Parallel`), a `seq` pedig lusta `IEnumerable`, ami csak bejáráskor számol és végtelen is lehet. A `seq { ... }` kifejezéssel `yield`-del generálhatsz, például fájlt soronként olvashatsz anélkül, hogy az egészet memóriába töltenéd. Buktató: a seq minden bejárásnál újra lefut (mellékhatásokkal együtt), ilyenkor `Seq.cache` vagy materializálás (`List.ofSeq`) kell; a lusta seq-ben megnyitott erőforrás csak a bejárás végén zárul.

```fsharp
// Végtelen, lusta prímsorozat
let primes =
    let isPrime n = n > 1 && Seq.forall (fun d -> n % d <> 0) (seq { 2 .. int (sqrt (float n)) })
    Seq.initInfinite id |> Seq.filter isPrime

let first10 = primes |> Seq.take 10 |> List.ofSeq

// Lusta fájlolvasás: a 'use' a bejárás végén zárja a readert
let readLines (path: string) =
    seq {
        use reader = new System.IO.StreamReader(path)
        while not reader.EndOfStream do
            yield reader.ReadLine()
    }

// Seq.cache nélkül a "számolok" minden bejárásnál újra kiíródna
let expensive =
    seq {
        for i in 1 .. 3 do
            printfn "számolok %d" i
            yield i * i
    }
    |> Seq.cache

// Array: párhuzamos map nagy adaton
let data = Array.init 1_000_000 float
let total = data |> Array.Parallel.map (fun x -> x * 0.5) |> Array.sum

// Gyakori műveletek: windowed, fold
let movingAvg = [ 1.0; 2.0; 6.0; 3.0; 8.0 ] |> List.windowed 3 |> List.map List.average
let wordFreq =
    "a b a c b a".Split ' '
    |> Array.fold (fun (m: Map<string, int>) w -> m |> Map.change w (Option.defaultValue 0 >> (+) 1 >> Some)) Map.empty

printfn "%A" first10
printfn "%d %d" (Seq.sum expensive) (Seq.sum expensive)
printfn "%.0f %A %A" total movingAvg wordFreq

// Ideiglenes fájl a readLines demóhoz (utána töröljük a saját temp fájlunkat)
let tmp = System.IO.Path.GetTempFileName()
System.IO.File.WriteAllLines(tmp, [| "egy"; "kettő" |])
readLines tmp |> Seq.iter (printfn "> %s")
System.IO.File.Delete tmp
```

## Computation expressionök
<!-- q: Mik a computation expressionök F#-ban és hogyan írjak sajátot? -->
<!-- tags: computation expressions, builder, monad, let!, result builder, seq, query -->

A computation expression (CE) egy builder osztály metódusaira (`Bind`, `Return`, `Zero`, `Delay`, `Combine`...) fordított szintaxis: a `let!` „kibontja” az értéket a kontextusból, a `return` visszacsomagolja. Így imperatívnak látszó, mégis tiszta kód írható Result-, Option-, aszinkron vagy lekérdezési kontextusban, egymásba ágyazott `match`-ek nélkül. A beépített CE-k: `seq`, `async`, `task`, `query`; sajátot néhány metódussal írsz. Buktató: a `Delay`/`Run` pár határozza meg, mikor fut a kód — hiányukban a mellékhatások túl korán futhatnak le.

```fsharp
// Saját "result" builder: let! a Result-ból bont ki, Error esetén rövidzár
type ResultBuilder() =
    member _.Bind(r, f) = Result.bind f r
    member _.Return x = Ok x
    member _.ReturnFrom(r: Result<_, _>) = r
    member _.Zero() = Ok()
    member _.Delay(f: unit -> Result<_, _>) = f
    member _.Run(f: unit -> Result<_, _>) = f ()
    member _.Combine(r, f) = Result.bind f r

let result = ResultBuilder()

let parseInt (s: string) =
    match System.Int32.TryParse s with
    | true, v -> Ok v
    | _ -> Error $"nem szám: '{s}'"

let safeDiv a b = if b = 0 then Error "nullával osztás" else Ok(a / b)

// Nincs egymásba ágyazott match — minden let! egy bind
let compute (x: string) (y: string) =
    result {
        let! a = parseInt x
        let! b = parseInt y
        let! q = safeDiv a b
        if q > 1000 then
            return! Error "túl nagy eredmény"
        return q * 2
    }

// Beépített CE-k: seq és query
let evens = seq { for i in 1 .. 10 do if i % 2 = 0 then yield i }

let query1 =
    query {
        for x in [ 5; 3; 9; 1 ] do
        where (x > 2)
        sortBy x
        select (x * 10)
    }
    |> List.ofSeq

printfn "%A | %A | %A" (compute "10" "2") (compute "10" "0") (compute "x" "1")
printfn "%A %A" (List.ofSeq evens) query1   // [2; 4; 6; 8; 10] [30; 50; 90]
```

## async és task
<!-- q: Mi a különbség az async és a task computation expression között F#-ban? -->
<!-- tags: async, task, concurrency, async.parallel, cancellation, retry, httpclient -->

Az `async { }` „hideg”: csak futtatáskor indul, újrafuttatható, és a `CancellationToken` automatikusan öröklődik a belső hívásokra — kompozícióra (retry, párhuzamosítás) ideális. A `task { }` (F# 6+) „forró” .NET `Task`-ot ad, gyorsabb és közvetlenül illeszkedik a C# könyvtárakhoz és az ASP.NET Core-hoz, de a tokent kézzel kell továbbadni. Átjárás: `Async.AwaitTask` és `Async.StartAsTask`. A `RunSynchronously` csak a program legszélén (main, teszt) blokkoljon, könyvtári kódban soha.

```fsharp
open System
open System.Net.Http
open System.Threading
open System.Threading.Tasks

// task: .NET interop, a tokent explicit adjuk tovább
let fetchLength (http: HttpClient) (url: string) (ct: CancellationToken) =
    task {
        try
            let! body = http.GetStringAsync(url, ct)
            return Ok body.Length
        with
        | :? HttpRequestException as e -> return Error $"{url}: {e.Message}"
        | :? TaskCanceledException -> return Error $"{url}: időtúllépés"
    }

// async: hideg, újrafuttatható → kényelmes retry exponenciális várakozással
let rec retry (attempts: int) (delayMs: int) (work: Async<Result<'a, string>>) =
    async {
        let! r = work
        match r with
        | Ok _ -> return r
        | Error _ when attempts > 1 ->
            do! Async.Sleep delayMs
            return! retry (attempts - 1) (delayMs * 2) work
        | Error _ -> return r
    }

// Párhuzamos HTTP lekérések közös timeouttal
let crawl (urls: string list) =
    task {
        use http = new HttpClient(Timeout = TimeSpan.FromSeconds 10.0)
        use cts = new CancellationTokenSource(TimeSpan.FromSeconds 30.0)
        let tasks = urls |> List.map (fun u -> fetchLength http u cts.Token)
        let! results = Task.WhenAll<Result<int, string>>(tasks)
        return Array.zip (Array.ofList urls) results
    }

// Async.Parallel korlátozott párhuzamossággal
let simulated i =
    async {
        do! Async.Sleep 50
        return Ok(i * i)
    }

let batch =
    [ 1 .. 10 ]
    |> List.map (fun i -> retry 3 100 (simulated i))
    |> fun jobs -> Async.Parallel(jobs, maxDegreeOfParallelism = 4)
    |> Async.RunSynchronously          // csak a program szélén blokkolj!

printfn "%A" batch
// crawl [ "https://example.com" ] |> Async.AwaitTask |> Async.RunSynchronously |> printfn "%A"
```

## Type providerek
<!-- q: Mik a type providerek F#-ban és hogyan dolgozzak velük CSV vagy JSON adattal? -->
<!-- tags: type providers, fsharp.data, csv, json, schema inference, data access -->

A type provider fordításkor, egy minta (fájl, inline szöveg, URL, adatbázis-séma) alapján generál típusokat, így a CSV oszlopai, a JSON mezői vagy az SQL táblák IntelliSense-szel, típusosan érhetők el, kézi DTO-írás nélkül. A legismertebb csomag a `FSharp.Data` (CsvProvider, JsonProvider, XmlProvider, HtmlProvider); adatbázisra a `SqlProvider` vagy a `FSharp.Data.SqlClient` való. Buktatók: ha a valós adat eltér a mintától (hiányzó mező, más típus), futásidejű hiba lehet, ezért reprezentatív mintát adj; a fordításkori hálózati/adatbázis-elérés a CI-ben gondot okozhat.

```fsharp
// Szkriptben (.fsx); projektben NuGet csomagként: FSharp.Data
#r "nuget: FSharp.Data"
open FSharp.Data

// A típus a mintából jön: Date: DateTime, Region: string, Amount: decimal
type Sales = CsvProvider<"Date,Region,Amount\n2026-01-01,North,120.5\n2026-01-02,South,80">

let csvText = "Date,Region,Amount\n2026-03-01,North,200.0\n2026-03-01,South,150.5\n2026-03-02,North,99.9"

let byRegion =
    (Sales.Parse csvText).Rows
    |> Seq.groupBy (fun r -> r.Region)                                    // típusos mező
    |> Seq.map (fun (region, rows) -> region, rows |> Seq.sumBy (fun r -> r.Amount))
    |> List.ofSeq

// JSON provider: beágyazott objektumok és tömbök is típusosak
type Weather = JsonProvider<"""{ "city": "Szeged", "current": { "tempC": 21.5, "wind": 3 }, "alerts": ["hőség"] }""">

let w = Weather.Parse """{ "city": "Pécs", "current": { "tempC": 18.0, "wind": 5 }, "alerts": [] }"""

printfn "%s: %M °C, szél: %d, riasztások: %d" w.City w.Current.TempC w.Current.Wind w.Alerts.Length
printfn "%A" byRegion   // [("North", 299.9M); ("South", 150.5M)]

// Hálózatról: Weather.AsyncLoad url — éles kódban kezeld a hibát és a timeoutot
```

## Mértékegységek (units of measure)
<!-- q: Hogyan használjam a mértékegységeket F#-ban a fizikai számítások hibáinak elkerülésére? -->
<!-- tags: units of measure, measure, type safety, physics, dimensional analysis -->

Az F# mértékegységei (`[<Measure>]`) a numerikus típusokhoz dimenziót kötnek, és a fordító ellenőrzi a dimenzióanalízist: méter és másodperc nem adható össze, a szorzás/osztás pedig helyes származtatott egységet ad. Futásidőben a mértékegységek teljesen törlődnek, így nincs teljesítményköltség. Generikus egységgel (`float<'u>`) bármilyen dimenzióra működő függvény írható. Külső, egység nélküli adatot a `LanguagePrimitives.FloatWithMeasure` emel be, kifelé pedig a `float` konverzió veszi le az egységet.

```fsharp
[<Measure>] type m
[<Measure>] type s
[<Measure>] type kg
[<Measure>] type N = kg m / s^2     // származtatott egység
[<Measure>] type km
[<Measure>] type h

let metersPerKm = 1000.0<m/km>
let secondsPerHour = 3600.0<s/h>

// A visszatérési típus egységét a fordító ellenőrzi
let toMetersPerSecond (v: float<km/h>) : float<m/s> = v * metersPerKm / secondsPerHour

let force (mass: float<kg>) (accel: float<m/s^2>) : float<N> = mass * accel

// Generikus mértékegység
let average (xs: float<'u> list) : float<'u> = List.sum xs / float (List.length xs)

let speed = toMetersPerSecond 90.0<km/h>    // 25.0<m/s>
let f = force 80.0<kg> 9.81<m/s^2>
// let hiba = speed + f                     // FORDÍTÁSI HIBA: m/s és N nem adható össze

let lapTimes = [ 61.2<s>; 59.8<s>; 60.4<s> ]
printfn "%.1f m/s, %.1f N, átlagos kör: %.2f s" (float speed) (float f) (float (average lapTimes))

// Egység nélküli szenzoradat beemelése
let fromSensor (raw: float) : float<m> = LanguagePrimitives.FloatWithMeasure raw
printfn "%.1f m" (float (fromSensor 12.5 + 2.0<m>))
```

## Active patternök
<!-- q: Mik az active patternök F#-ban és hogyan tegyem velük olvashatóbbá a mintaillesztést? -->
<!-- tags: active patterns, partial active patterns, parameterized patterns, regex, parsing -->

Az active pattern egy függvény, amit mintaként használhatsz a `match`-ben: a teljes változat (`(|Even|Odd|)`) az inputot kategóriákra bontja, a részleges (`(|Int|_|)`) `Option`-t ad és illeszkedhet vagy nem, a paraméterezett (`(|Regex|_|) pattern`) pedig argumentumot is kap. Ezzel a parse-olás, validáció és osztályozás logikája elnevezett, újrahasznosítható mintákba kerül, a `match` pedig deklaratív döntési táblává válik. Buktató: a részleges minták nem adnak teljességi garanciát, ezért mindig legyen záró ág, és a drága mintákat ne futtasd feleslegesen sokszor.

```fsharp
open System
open System.Globalization
open System.Text.RegularExpressions

// Teljes active pattern
let (|Even|Odd|) n = if n % 2 = 0 then Even else Odd

// Részleges active patternök
let (|Int|_|) (s: string) =
    match Int32.TryParse s with
    | true, v -> Some v
    | _ -> None

let (|IsoDate|_|) (s: string) =
    match DateTime.TryParseExact(s, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None) with
    | true, d -> Some d
    | _ -> None

// Paraméterezett: regex csoportok listaként
let (|Regex|_|) (pattern: string) (input: string) =
    let m = Regex.Match(input, pattern)
    if m.Success then Some [ for i in 1 .. m.Groups.Count - 1 -> m.Groups.[i].Value ] else None

let interpret (cmd: string) =
    match cmd.Trim() with
    | Int (Even as n) -> $"páros szám: {n}"          // minták egymásba ágyazva
    | Int n -> $"páratlan szám: {n}"
    | IsoDate d -> $"dátum, a hét napja: {d.DayOfWeek}"
    | Regex @"^move (\w+) to (\d+),(\d+)$" [ name; x; y ] -> $"{name} mozgatása ({x}, {y})"
    | Regex @"^[\w.]+@([\w-]+\.\w+)$" [ domain ] -> $"email, domain: {domain}"
    | "" -> "üres parancs"
    | other -> $"ismeretlen: {other}"

[ "42"; "7"; "2026-11-21"; "move player to 10,20"; "info@example.com"; "???" ]
|> List.iter (interpret >> printfn "%s")
```

## Rekurzió és farokhívás
<!-- q: Hogyan írjak verembiztos rekurziót F#-ban? -->
<!-- tags: recursion, tail call, tail recursion, accumulator, continuation passing style, stack overflow -->

F#-ban a ciklusok helyett gyakran rekurziót írunk, de a nem farokrekurzív függvény minden hívással vermet foglal, és nagy inputnál `StackOverflowException`-t dob (ez nem kapható el). Akkumulátor paraméterrel a rekurzív hívás lesz az utolsó művelet, ezt a fordító ciklussá alakítja; a `[<TailCall>]` attribútum (F# 8) figyelmeztet, ha mégsem farokhívás. Fákra a continuation-passing style (CPS) ad verembiztos megoldást. Fontos: a valódi .NET tail call utasításokat Release módban (`--tailcalls+`) generálja a fordító, Debugban alapból nem.

```fsharp
// NEM farokrekurzív: az összeadás a rekurzív hívás UTÁN történik
let rec sumNaive (xs: int list) =
    match xs with
    | [] -> 0L
    | x :: rest -> int64 x + sumNaive rest

// Farokrekurzív akkumulátorral → ciklussá fordul
let sumTail (xs: int list) =
    let rec go acc xs =
        match xs with
        | [] -> acc
        | x :: rest -> go (acc + int64 x) rest
    go 0L xs

[<TailCall>]
let rec gcd a b = if b = 0 then a else gcd b (a % b)

// CPS: fa bejárása — a "mi a következő lépés" egy closure-ben utazik
type Tree =
    | Leaf
    | Node of Tree * int * Tree

let sumTree tree =
    let rec go t (k: int64 -> int64) =
        match t with
        | Leaf -> k 0L
        | Node (l, v, r) -> go l (fun ls -> go r (fun rs -> k (ls + int64 v + rs)))
    go tree id

// Mély, degenerált fa építése iteratívan (fold)
let deepTree = Seq.fold (fun acc i -> Node (acc, i, Leaf)) Leaf (seq { 1 .. 100_000 })

let big = List.init 1_000_000 id
printfn "%d" (sumTail big)        // biztonságos
// printfn "%d" (sumNaive big)    // StackOverflow veszély!
printfn "%d %d" (gcd 1071 462) (sumTree deepTree)   // Release módban verembiztos
```

## MailboxProcessor (agentek)
<!-- q: Hogyan kezeljek megosztott állapotot lock nélkül F# MailboxProcessorral? -->
<!-- tags: mailboxprocessor, agent, actor model, concurrency, message passing, state -->

A `MailboxProcessor` egy aszinkron üzenetsor egyetlen feldolgozó ciklussal (actor/agent modell): az állapot a rekurzív ciklus paramétere, amit csak ez az egy ciklus lát, így nincs szükség lockra, és versenyhelyzet sem alakulhat ki. A `Post` nem blokkol, a `PostAndReply`/`PostAndAsyncReply` válaszcsatornával (`AsyncReplyChannel`) kérés-választ valósít meg, timeouttal. Buktatók: a sor alapból korlátlan (túlterheléskor nő a memória), a ciklusban dobott kivétel leállítja az agentet (az `Error` eseményen jelenik meg), és egy lassú üzenet az összes többit is várakoztatja.

```fsharp
type CounterMsg =
    | Increment of key: string
    | Get of key: string * reply: AsyncReplyChannel<int>
    | Snapshot of AsyncReplyChannel<Map<string, int>>

let counterAgent =
    MailboxProcessor<CounterMsg>.Start(fun inbox ->
        // Az állapot a ciklus paramétere: soha nem osztott, nem kell zárolni
        let rec loop (state: Map<string, int>) =
            async {
                let! msg = inbox.Receive()
                match msg with
                | Increment key ->
                    return! loop (state |> Map.change key (Option.defaultValue 0 >> (+) 1 >> Some))
                | Get (key, reply) ->
                    reply.Reply(state |> Map.tryFind key |> Option.defaultValue 0)
                    return! loop state
                | Snapshot reply ->
                    reply.Reply state
                    return! loop state
            }
        loop Map.empty)

// Az agenten belüli kivétel itt jelenik meg
counterAgent.Error.Add(fun ex -> eprintfn "Agent hiba: %s" ex.Message)

// Sok párhuzamos küldő — a Post nem blokkol
[ for i in 1 .. 1000 -> async { counterAgent.Post(Increment(if i % 3 = 0 then "fizz" else "egyéb")) } ]
|> Async.Parallel
|> Async.Ignore
|> Async.RunSynchronously

// Kérés-válasz timeouttal (ms)
let fizz = counterAgent.PostAndReply((fun ch -> Get("fizz", ch)), timeout = 5000)
let all = counterAgent.PostAndAsyncReply Snapshot |> Async.RunSynchronously
printfn "fizz=%d, állapot: %A" fizz all   // fizz=333
```

## OOP és .NET interop: interfészek, osztályok, object expression
<!-- q: Hogyan írjak osztályokat, interfészeket és eseményeket F#-ban C#-kompatibilis módon? -->
<!-- tags: oop, interfaces, classes, object expressions, events, interop, csharp interop -->

Az F# teljes értékű .NET OOP-t támogat: osztályok primary konstruktorral, interfészek explicit implementációval, öröklés, property-k és `[<CLIEvent>]` események, amelyeket a C# kód természetesen használ. Az object expression (`{ new IFoo with ... }`) osztálydeklaráció nélkül, helyben implementál interfészt — teszt-dublőrökhöz, comparerekhez ideális. Buktató: F#-ban az interfésztagok explicitek, ezért a hívás előtt upcast kell (`:>`); a C# felé nyitott API-ban kerüld a curried metódusokat és az F#-specifikus típusokat (list, option), helyettük `IEnumerable` és null/`Nullable` jobb.

```fsharp
open System
open System.Collections.Generic

type IRepository<'T> =
    abstract Get: id: int -> 'T option
    abstract Save: id: int * item: 'T -> unit

type InMemoryRepo<'T>() =
    let store = Dictionary<int, 'T>()
    member _.Count = store.Count
    interface IRepository<'T> with
        member _.Get id =
            match store.TryGetValue id with
            | true, v -> Some v
            | _ -> None
        member _.Save(id, item) = store[id] <- item

// Primary konstruktor validációval, mutábilis belső állapottal és eseménnyel
type BankAccount(owner: string, initial: decimal) =
    do if initial < 0m then invalidArg (nameof initial) "Negatív nyitóegyenleg"
    let mutable balance = initial
    let changed = Event<decimal>()
    member _.Owner = owner
    member _.Balance = balance
    [<CLIEvent>]
    member _.BalanceChanged = changed.Publish      // C#-ból normál eventként látszik
    member _.Deposit(amount: decimal) =
        if amount <= 0m then invalidArg (nameof amount) "Pozitív összeg kell"
        balance <- balance + amount
        changed.Trigger balance
    override _.ToString() = $"{owner}: {balance} Ft"

// Object expression: helyben implementált interfész (pl. teszt-dublőr)
let fakeRepo =
    { new IRepository<string> with
        member _.Get id = if id = 1 then Some "teszt" else None
        member _.Save(_, _) = () }

let byLength =
    { new IComparer<string> with
        member _.Compare(a, b) = compare a.Length b.Length }

let acc = BankAccount("Demo Bt.", 1000m)
acc.BalanceChanged.Add(printfn "Új egyenleg: %M")
acc.Deposit 500m

let repo = InMemoryRepo<string>() :> IRepository<string>   // upcast az interfészre
repo.Save(42, "válasz")
printfn "%A %A %O" (repo.Get 42) (fakeRepo.Get 1) acc
printfn "%A" (List.sortWith (fun a b -> byLength.Compare(a, b)) [ "ccc"; "a"; "bb" ])
```
