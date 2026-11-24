# OCaml
<!-- tech: ocaml -->
<!-- aliases: ml, opam, dune, reasonml -->

Az OCaml az ML-család ipari erejű tagja: szigorú (nem lusta) kiértékelésű, statikusan és erősen típusos, teljes típuskövetkeztetéssel, alapvetően funkcionális, de mutábilis rekordmezőket, tömböket és ciklusokat is enged. Kiemelkedő a modulrendszere (szignatúrák, funktorok), a variánsokra épülő mintaillesztés kimerítő-ellenőrzéssel, a gyors natív fordító és a kiszámítható teljesítmény (generációs GC, alacsony késleltetés). Az OCaml 5 óta valódi többmagos párhuzamosság (Domain-ek) és effect handlerek is vannak. Fordítóknál, statikus elemzőknél, tételbizonyítóknál (Coq/Rocq), pénzügyi rendszereknél (Jane Street) és MirageOS unikernelekben erős; GUI-hoz, adattudományhoz és ott, ahol nagy könyvtár-ökoszisztéma kell, gyengébb választás.

## Variánsok és mintaillesztés
<!-- q: Hogyan használjam a variáns típusokat és a mintaillesztést OCamlben? -->
<!-- tags: variants, pattern matching, algebraic data types, exhaustiveness, or-pattern -->

A variáns (összegtípus) a lehetséges esetek zárt felsorolása, mindegyik saját adattal; a `match` ezeket illeszti, és a fordító figyelmeztet, ha egy eset kimaradt vagy egy ág elérhetetlen. A minták egymásba ágyazhatók, az or-minta (`Num 0, x | x, Num 0`) több alakot kezel egy ágban, a `when` guard extra feltételt ad. Ez teszi az OCamlt ideálissá AST-k, állapotgépek és protokollok modellezésére. Buktató: a `_` joker elnyeli a később hozzáadott konstruktorokat is, ezért elveszik a kimerítőség-ellenőrzés előnye — lehetőleg nevezd meg az eseteket.

```ocaml
(* Aritmetikai kifejezés mint variáns *)
type expr =
  | Num of int
  | Var of string
  | Add of expr * expr
  | Mul of expr * expr
  | Neg of expr

(* Egyszerűsítés: előbb a részfákat egyszerűsítjük, majd azok alakjára illesztünk *)
let rec simplify e =
  match e with
  | Add (a, b) -> (
      match (simplify a, simplify b) with
      | Num 0, x | x, Num 0 -> x                  (* or-minta, mindkét ág köti x-et *)
      | Num x, Num y -> Num (x + y)
      | x, y -> Add (x, y))
  | Mul (a, b) -> (
      match (simplify a, simplify b) with
      | Num 0, _ | _, Num 0 -> Num 0
      | Num 1, x | x, Num 1 -> x
      | Num x, Num y -> Num (x * y)
      | x, y -> Mul (x, y))
  | Neg inner -> (
      match simplify inner with
      | Num n -> Num (-n)
      | Neg x -> x                                (* dupla tagadás eltűnik *)
      | x -> Neg x)
  | Num _ | Var _ -> e

let rec to_string = function
  | Num n when n < 0 -> Printf.sprintf "(%d)" n   (* guard *)
  | Num n -> string_of_int n
  | Var v -> v
  | Add (a, b) -> Printf.sprintf "(%s + %s)" (to_string a) (to_string b)
  | Mul (a, b) -> Printf.sprintf "%s * %s" (to_string a) (to_string b)
  | Neg x -> "-" ^ to_string x

(* Kiértékelés környezettel; hiányzó változónál Error *)
let rec eval env = function
  | Num n -> Ok n
  | Var v -> (
      match List.assoc_opt v env with
      | Some n -> Ok n
      | None -> Error ("ismeretlen változó: " ^ v))
  | Add (a, b) -> binop ( + ) env a b
  | Mul (a, b) -> binop ( * ) env a b
  | Neg x -> Result.map (fun n -> -n) (eval env x)

and binop op env a b =
  match (eval env a, eval env b) with
  | Ok x, Ok y -> Ok (op x y)
  | (Error _ as err), _ | _, (Error _ as err) -> err

let () =
  let e = Add (Mul (Num 1, Var "x"), Add (Num 0, Mul (Num 2, Num 3))) in
  print_endline (to_string e);              (* (1 * x + (0 + 2 * 3)) *)
  print_endline (to_string (simplify e));   (* (x + 6) *)
  match eval [ ("x", 4) ] e with
  | Ok n -> Printf.printf "eredmény: %d\n" n
  | Error msg -> print_endline msg
```

## Rekordok, option, result és kivételek
<!-- q: Hogyan kezeljem a hibákat OCamlben result típussal, let* szintaxissal és kivételekkel? -->
<!-- tags: records, option, result, let-binding operators, exceptions, error handling -->

Az OCaml rekordjai nevesített mezős típusok; alapból immutábilisak (`{ r with mezo = x }` másolatot ad), de egy mező `mutable`-ként jelölhető. Várható hibákra a `result` típus (`Ok`/`Error`) a javasolt, a `let*` binding operátorral (`Result.bind`) olvasható, monadikus láncot kapunk; a variáns hibatípus (akár inline rekorddal) pontosan leírja az okot. A kivételek olcsók és gyorsak, ezért valóban kivételes helyzetekre (I/O, programhiba) valók; a `match ... with exception` ugyanabban a mintaillesztésben kezeli az eredményt és a kivételt. Buktató: a stdlib egyes függvényei kivételt dobnak (`List.find`, `Hashtbl.find`) — használd az `_opt` változatukat, és erőforrásnál `Fun.protect ~finally`.

```ocaml
type account = { id : int; owner : string; mutable balance : int }

(* Hibatípus inline rekorddal: a hívó pontosan látja az okot *)
type error =
  | Insufficient_funds of { needed : int; available : int }
  | Account_not_found of int
  | Invalid_amount of int

let ( let* ) = Result.bind

let find accounts id =
  match List.find_opt (fun a -> a.id = id) accounts with
  | Some a -> Ok a
  | None -> Error (Account_not_found id)

(* Lánc: az első Error megszakítja a folyamatot *)
let withdraw accounts id amount =
  let* () = if amount <= 0 then Error (Invalid_amount amount) else Ok () in
  let* acc = find accounts id in
  if acc.balance < amount then
    Error (Insufficient_funds { needed = amount; available = acc.balance })
  else begin
    acc.balance <- acc.balance - amount;   (* mutable mező helyben módosítva *)
    Ok acc.balance
  end

let error_to_string = function
  | Insufficient_funds { needed; available } ->
      Printf.sprintf "fedezethiány: kell %d, van %d" needed available
  | Account_not_found id -> Printf.sprintf "nincs ilyen számla: %d" id
  | Invalid_amount n -> Printf.sprintf "érvénytelen összeg: %d" n

(* Kivételek: match ... with exception, és garantált lezárás Fun.protect-tel *)
let read_first_line path =
  match open_in path with
  | exception Sys_error msg -> Error msg
  | ic ->
      Fun.protect
        ~finally:(fun () -> close_in ic)
        (fun () ->
          match input_line ic with
          | line -> Ok line
          | exception End_of_file -> Error "üres fájl")

let () =
  let accounts =
    [ { id = 1; owner = "Anna"; balance = 100 }; { id = 2; owner = "Béla"; balance = 20 } ]
  in
  List.iter
    (fun (id, amount) ->
      match withdraw accounts id amount with
      | Ok rest -> Printf.printf "sikeres, maradt: %d\n" rest
      | Error e -> print_endline (error_to_string e))
    [ (1, 30); (2, 50); (3, 10); (1, -5) ];
  let a = List.hd accounts in
  let renamed = { a with owner = "Anna K." } in   (* funkcionális másolat *)
  Printf.printf "%s -> %s\n" a.owner renamed.owner;
  match read_first_line "nincs-ilyen.txt" with
  | Ok l -> print_endline l
  | Error m -> print_endline ("hiba: " ^ m)
```

## Modulok, szignatúrák és absztrakt típusok
<!-- q: Hogyan használjam a modulokat és szignatúrákat OCamlben az implementáció elrejtésére? -->
<!-- tags: modules, signatures, module type, abstract types, encapsulation, leftist heap -->

Az OCaml modulja (`struct ... end`) típusokat és értékeket csoportosít, a szignatúra (`sig ... end`, `module type`) pedig a nyilvános interfészét írja le. Ha a szignatúrában a típus absztrakt (`type 'a t` definíció nélkül), a külvilág nem látja és nem sértheti meg a belső reprezentációt — így az invariánsok (pl. kupac-tulajdonság) garantáltan megmaradnak, és az implementáció később cserélhető. Minden `.ml` fájl automatikusan modul, a hozzá tartozó `.mli` a szignatúrája. Buktató: túl szűk szignatúránál a típusegyenlőségek elvesznek (ilyenkor `with type t = ...` kell), túl bővnél pedig kiszivárog az implementáció.

```ocaml
(* Prioritási sor interfésze: a 'a t típus absztrakt *)
module type PRIORITY_QUEUE = sig
  type 'a t
  val empty : 'a t
  val is_empty : 'a t -> bool
  val push : int -> 'a -> 'a t -> 'a t
  val pop : 'a t -> (int * 'a * 'a t) option   (* legkisebb prioritású elem *)
  val size : 'a t -> int
end

(* Leftist heap implementáció; kívülről csak a szignatúra látszik *)
module Leftist_heap : PRIORITY_QUEUE = struct
  (* Node (rang, prioritás, érték, bal, jobb) *)
  type 'a t = Empty | Node of int * int * 'a * 'a t * 'a t

  let empty = Empty
  let is_empty = function Empty -> true | Node _ -> false
  let rank = function Empty -> 0 | Node (r, _, _, _, _) -> r

  (* A nagyobb rangú részfa kerül balra: így a jobb gerinc rövid marad *)
  let make p v a b =
    if rank a >= rank b then Node (rank b + 1, p, v, a, b)
    else Node (rank a + 1, p, v, b, a)

  (* Összefésülés O(log n) idő alatt *)
  let rec merge h1 h2 =
    match (h1, h2) with
    | Empty, h | h, Empty -> h
    | Node (_, p1, v1, l1, r1), Node (_, p2, _, _, _) ->
        if p1 <= p2 then make p1 v1 l1 (merge r1 h2) else merge h2 h1

  let push p v h = merge (Node (1, p, v, Empty, Empty)) h
  let pop = function Empty -> None | Node (_, p, v, l, r) -> Some (p, v, merge l r)
  let rec size = function Empty -> 0 | Node (_, _, _, l, r) -> 1 + size l + size r
end

(* Feladatütemező a kupacra építve; a modul alias cserélhető *)
module Q = Leftist_heap

let rec drain q =
  match Q.pop q with
  | None -> ()
  | Some (prio, task, rest) ->
      Printf.printf "[%d] %s\n" prio task;
      drain rest

let () =
  let q =
    Q.empty
    |> Q.push 3 "riport generálás"
    |> Q.push 1 "riasztás kezelése"
    |> Q.push 2 "cache ürítés"
  in
  Printf.printf "%d feladat vár\n" (Q.size q);
  drain q
  (* Q.Node (...) itt fordítási hiba lenne: a konstruktorok rejtettek *)
```

## Funktorok: modulokat paraméterező modulok
<!-- q: Mik azok a funktorok OCamlben és hogyan használjam a Map.Make-et saját kulccsal? -->
<!-- tags: functors, map.make, set.make, module parameters, generic programming -->

A funktor olyan modul, amely egy másik modult kap paraméterként és új modult ad vissza — fordítási idejű generikus programozás, futásidejű költség nélkül. A stdlib `Map.Make` és `Set.Make` funktora egy `ORDERED`-szerű modult vár (`type t` + `compare`), és kiegyensúlyozott fán alapuló, immutábilis tárolót ad. Saját funktorral újrafelhasználható komponensek írhatók (cache, számláló, gráf-algoritmus) tetszőleges kulcstípusra. Buktató: két külön `Map.Make (K)` alkalmazás eredményének típusai inkompatibilisek lehetnek; a polimorf `compare` használata rekordokon lassú és meglepő lehet (pl. float NaN) — írj saját összehasonlítót.

```ocaml
(* Saját kulcstípus: 2D pont, explicit összehasonlítással *)
module Point = struct
  type t = { x : int; y : int }
  let compare a b = match Int.compare a.x b.x with 0 -> Int.compare a.y b.y | c -> c
end

module PointSet = Set.Make (Point)

(* BFS rácson: a bejárt pontok halmaza immutábilis PointSet *)
let reachable ~walls ~start ~max_steps =
  let open Point in
  let neighbors p = [ { p with x = p.x + 1 }; { p with x = p.x - 1 };
                      { p with y = p.y + 1 }; { p with y = p.y - 1 } ] in
  let rec go frontier seen steps =
    if steps = max_steps || frontier = [] then seen
    else
      let next =
        List.concat_map neighbors frontier
        |> List.filter (fun p -> not (PointSet.mem p seen || PointSet.mem p walls))
        |> List.sort_uniq compare
      in
      go next (List.fold_left (fun s p -> PointSet.add p s) seen next) (steps + 1)
  in
  go [ start ] (PointSet.singleton start) 0

(* Saját funktor: gyakoriság-számláló bármilyen rendezhető kulcsra *)
module type ORDERED = sig
  type t
  val compare : t -> t -> int
end

module Make_counter (K : ORDERED) : sig
  type t
  val empty : t
  val add : K.t -> t -> t
  val top : int -> t -> (K.t * int) list
end = struct
  module M = Map.Make (K)
  type t = int M.t
  let empty = M.empty
  let add k m = M.update k (function None -> Some 1 | Some n -> Some (n + 1)) m
  let top n m =
    M.bindings m
    |> List.sort (fun (_, a) (_, b) -> Int.compare b a)
    |> List.filteri (fun i _ -> i < n)
end

module Word_counter = Make_counter (String)   (* a String modul illeszkedik ORDERED-re *)

let () =
  let walls = PointSet.of_list [ { Point.x = 1; y = 0 }; { Point.x = 0; y = 1 } ] in
  let r = reachable ~walls ~start:{ Point.x = 0; y = 0 } ~max_steps:3 in
  Printf.printf "elérhető pontok: %d\n" (PointSet.cardinal r);
  let text = "a b a c b a d" in
  String.split_on_char ' ' text
  |> List.fold_left (fun c w -> Word_counter.add w c) Word_counter.empty
  |> Word_counter.top 2
  |> List.iter (fun (w, n) -> Printf.printf "%s: %d\n" w n)
```

## Magasabbrendű függvények, pipe és farokrekurzió
<!-- q: Hogyan írjak idiomatikus funkcionális OCaml kódot pipe-pal, címkézett argumentumokkal és farokrekurzióval? -->
<!-- tags: higher-order functions, pipe, labeled arguments, optional arguments, tail recursion, fold -->

Az OCaml függvényei curry-zettek, ezért a részleges alkalmazás és a `|>` pipe természetes adatfeldolgozó láncot ad. A címkézett (`~sep`) és opcionális (`?(limit = 10)`) argumentumok olvashatóbb API-t adnak, és tetszőleges sorrendben átadhatók. Az OCaml garantáltan optimalizálja a farokhívást, ezért a nagy listákon dolgozó rekurziót akkumulátorral érdemes írni; a nem farokrekurzív változat nagy bemeneten `Stack_overflow`-t dobhat. Buktató: az opcionális argumentum után kell egy nem opcionális (gyakran `()`), különben a függvény sosem „telítődik”; OCaml 4.14+/5.x alatt a `[@tail_mod_cons]` attribútum a konstruktorépítő rekurziót is farokhívássá alakítja.

```ocaml
type order = { customer : string; amount : float; paid : bool }

(* Farokrekurzív összegzés akkumulátorral: konstans stack *)
let sum_floats xs =
  let rec go acc = function [] -> acc | x :: rest -> go (acc +. x) rest in
  go 0. xs

(* tail_mod_cons: a "x :: rekurzív hívás" alak is konstans stacken fut *)
let[@tail_mod_cons] rec take_while p = function
  | x :: rest when p x -> x :: take_while p rest
  | _ -> []

(* Opcionális (?limit) és címkézett (~sep) argumentum; a () zárja le a hívást *)
let report ?(limit = 3) ~sep orders () =
  orders
  |> List.filter (fun o -> o.paid)
  |> List.sort (fun a b -> Float.compare b.amount a.amount)
  |> List.filteri (fun i _ -> i < limit)
  |> List.map (fun o -> Printf.sprintf "%s=%.0f" o.customer o.amount)
  |> String.concat sep

(* Csoportosítás fold-dal: vevőnkénti összeg asszociációs listában *)
let totals_by_customer orders =
  List.fold_left
    (fun acc o ->
      let prev = Option.value (List.assoc_opt o.customer acc) ~default:0. in
      (o.customer, prev +. o.amount) :: List.remove_assoc o.customer acc)
    [] orders

(* Függvénykompozíció és részleges alkalmazás *)
let compose f g x = f (g x)
let is_big = compose (fun a -> a > 1000.) (fun o -> o.amount)

let () =
  let orders =
    [ { customer = "A"; amount = 1200.; paid = true };
      { customer = "B"; amount = 300.; paid = false };
      { customer = "A"; amount = 450.; paid = true };
      { customer = "C"; amount = 2000.; paid = true } ]
  in
  print_endline (report ~sep:", " orders ());           (* alapértelmezett limit *)
  print_endline (report ~limit:1 ~sep:"; " orders ());
  Printf.printf "összesen: %.0f\n" (sum_floats (List.map (fun o -> o.amount) orders));
  Printf.printf "nagy rendelések: %d\n" (List.length (List.filter is_big orders));
  List.iter (fun (c, t) -> Printf.printf "%s: %.0f\n" c t) (totals_by_customer orders);
  (* Nagy listán is biztonságos: nincs stack overflow *)
  let big = List.init 1_000_000 float_of_int in
  Printf.printf "%.0f %d\n" (sum_floats big) (List.length (take_while (fun x -> x < 10.) big))
```

## Mutábilis adatszerkezetek és imperatív stílus
<!-- q: Hogyan használjak ref-et, tömböt és Hashtbl-t OCamlben imperatív kódhoz? -->
<!-- tags: ref, array, hashtbl, buffer, mutable, imperative, loops, performance -->

Az OCaml pragmatikus: ahol a teljesítmény vagy az algoritmus megkívánja, használhatsz mutábilis cellát (`ref`, `!`, `:=`), tömböt (`Array`, O(1) indexelés), hash táblát (`Hashtbl`), `Buffer`-t a hatékony string-építéshez, valamint `for`/`while` ciklust. Bevett minta, hogy a mutáció egy függvényen belül marad, kívülről a függvény tiszta marad (pl. memoizáció, szita). Buktatók: a `Hashtbl.add` nem felülír, hanem árnyékol (felülíráshoz `Hashtbl.replace` kell); az `Array.make n (Array.make m 0)` minden sorban *ugyanazt* a belső tömböt osztja meg — mátrixhoz `Array.make_matrix` való; többmagos (OCaml 5) futásnál a megosztott mutábilis adatot védeni kell.

```ocaml
(* Eratoszthenész szitája: helyben módosított bool tömb *)
let primes_up_to n =
  let is_prime = Array.make (n + 1) true in
  is_prime.(0) <- false;
  if n >= 1 then is_prime.(1) <- false;
  let i = ref 2 in
  while !i * !i <= n do
    if is_prime.(!i) then begin
      let j = ref (!i * !i) in
      while !j <= n do
        is_prime.(!j) <- false;
        j := !j + !i
      done
    end;
    incr i
  done;
  (* A mutáció nem szivárog ki: kívülről tiszta függvény *)
  List.filter (fun k -> is_prime.(k)) (List.init (n + 1) Fun.id)

(* Memoizáció Hashtbl-lel: a cache a lezárásban él *)
let memo_fib =
  let cache = Hashtbl.create 64 in
  let rec fib n =
    if n < 2 then n
    else
      match Hashtbl.find_opt cache n with
      | Some v -> v
      | None ->
          let v = fib (n - 1) + fib (n - 2) in
          Hashtbl.replace cache n v;   (* replace: nem árnyékol, felülír *)
          v
  in
  fib

(* Buffer: hatékony string-építés (a ^ minden lépésben másolna) *)
let csv_of_rows rows =
  let buf = Buffer.create 256 in
  List.iter
    (fun row ->
      Buffer.add_string buf (String.concat ";" row);
      Buffer.add_char buf '\n')
    rows;
  Buffer.contents buf

let () =
  Printf.printf "prímek: %s\n" (String.concat " " (List.map string_of_int (primes_up_to 50)));
  Printf.printf "fib 80 = %d\n" (memo_fib 80);
  print_string (csv_of_rows [ [ "név"; "pont" ]; [ "A"; "10" ]; [ "B"; "7" ] ]);
  (* Helyes mátrix: minden sor külön tömb *)
  let m = Array.make_matrix 3 3 0 in
  for r = 0 to 2 do
    for c = 0 to 2 do m.(r).(c) <- r * 3 + c done
  done;
  Array.iter (fun row -> print_endline (String.concat " " (Array.to_list (Array.map string_of_int row)))) m
```

## Lusta értékek és Seq
<!-- q: Hogyan dolgozzak lustán OCamlben a Seq modullal és a lazy kulcsszóval? -->
<!-- tags: lazy, seq, streams, laziness, generators, memoization -->

Az OCaml szigorú nyelv, de a lustaság opt-in módon elérhető: a `lazy e` egy egyszer kiértékelődő, memoizált felfüggesztett számítást ad (`Lazy.force`), a `Seq` modul pedig igény szerint előállított (pull-alapú) sorozatokat — így végtelen vagy nagy adatfolyamok (fájlsorok, generált értékek) is feldolgozhatók anélkül, hogy a memóriába kerülnének. A `Seq.t` egy `unit -> node` függvény, ezért a lánc minden bejáráskor újra lefut: drága forrásnál a `Seq.memoize` (4.14+) gyorsítótáraz. Buktató: a mellékhatásos `Seq` (pl. fájlolvasás) többszöri bejárása hibás eredményt ad, és a `lazy` érték kiértékelése több domainről egyszerre `CamlinternalLazy.Undefined`-ot dobhat.

```ocaml
(* Végtelen Fibonacci-sorozat Seq.unfold-dal *)
let fibs = Seq.unfold (fun (a, b) -> Some (a, (b, a + b))) (0, 1)

(* Collatz-sorozat: véges, de előre nem ismert hosszúságú *)
let collatz n =
  Seq.unfold (fun k -> if k = 0 then None
                       else if k = 1 then Some (1, 0)
                       else Some (k, if k mod 2 = 0 then k / 2 else 3 * k + 1)) n

(* Fájl sorai lustán: csak annyi sort olvasunk, amennyit felhasználunk *)
let lines_of_channel ic =
  Seq.of_dispenser (fun () -> In_channel.input_line ic)

(* lazy: drága konfiguráció, csak első használatkor számolódik ki, utána cache-elt *)
let config =
  lazy
    (print_endline "(konfig betöltése...)";
     [ ("timeout", "30"); ("retries", "3") ])

let get key = List.assoc_opt key (Lazy.force config)

let () =
  (* Az első 10 páros Fibonacci-szám egy végtelen sorozatból *)
  fibs
  |> Seq.filter (fun x -> x mod 2 = 0)
  |> Seq.take 10
  |> Seq.iter (Printf.printf "%d ");
  print_newline ();
  (* Melyik kezdőérték adja a leghosszabb Collatz-láncot 1..10000 között? *)
  let best =
    Seq.ints 1
    |> Seq.take 10_000
    |> Seq.map (fun n -> (n, Seq.length (collatz n)))
    |> Seq.fold_left (fun (bn, bl) (n, l) -> if l > bl then (n, l) else (bn, bl)) (1, 1)
  in
  Printf.printf "leghosszabb: %d (%d lépés)\n" (fst best) (snd best);
  ignore (get "timeout");              (* itt töltődik be *)
  Printf.printf "retries=%s\n" (Option.value (get "retries") ~default:"?");  (* már cache-ből *)
  ignore lines_of_channel
```

## GADT-k OCamlben
<!-- q: Hogyan használjam a GADT-ket OCamlben típusos kiértékelőhöz és típus-tanúkhoz? -->
<!-- tags: gadt, locally abstract types, existential types, type witness, typed eval -->

A GADT-ben minden konstruktor saját, pontosított eredménytípust adhat meg (`Int : int -> int expr`), így a típusparaméter az érték „jelentését” kódolja, és a mintaillesztés finomítja a típust. Az ilyen függvényekhez *lokálisan absztrakt, polimorf* annotáció kell (`let rec eval : type a. a expr -> a = ...`), mert az egyes ágakban `a` mást jelent. Típusos DSL-eknél, szerializálóknál (típus-tanú alapján `show`/`parse`) és heterogén tárolóknál hasznos; az egzisztenciális konstruktor (`Any : 'a ty * 'a -> any`) elrejti a konkrét típust. Buktató: a hibaüzenetek nehezen olvashatók, és a GADT-k nem keverhetők szabadon a típuskövetkeztetéssel — annotálj bőkezűen.

```ocaml
(* Típusos kifejezés: rosszul tipizált fa nem építhető *)
type _ expr =
  | Int : int -> int expr
  | Bool : bool -> bool expr
  | Add : int expr * int expr -> int expr
  | Lt : int expr * int expr -> bool expr
  | If : bool expr * 'a expr * 'a expr -> 'a expr
  | Pair : 'a expr * 'b expr -> ('a * 'b) expr
  | Fst : ('a * 'b) expr -> 'a expr

(* type a. : polimorf rekurzió lokálisan absztrakt típussal *)
let rec eval : type a. a expr -> a = function
  | Int n -> n
  | Bool b -> b
  | Add (x, y) -> eval x + eval y
  | Lt (x, y) -> eval x < eval y
  | If (c, t, e) -> if eval c then eval t else eval e
  | Pair (x, y) -> (eval x, eval y)
  | Fst p -> fst (eval p)

(* Típus-tanú: futásidőben is ismert típusleírás *)
type _ ty =
  | TInt : int ty
  | TString : string ty
  | TList : 'a ty -> 'a list ty
  | TPair : 'a ty * 'b ty -> ('a * 'b) ty

(* Típusvezérelt szerializáló: a tanú határozza meg, hogyan nézzük az értéket *)
let rec show : type a. a ty -> a -> string =
 fun t v ->
  match t with
  | TInt -> string_of_int v
  | TString -> Printf.sprintf "%S" v
  | TList t' -> "[" ^ String.concat "; " (List.map (show t') v) ^ "]"
  | TPair (ta, tb) -> Printf.sprintf "(%s, %s)" (show ta (fst v)) (show tb (snd v))

(* Egzisztenciális burok: heterogén lista, a típus elrejtve, de a tanú megmarad *)
type any = Any : 'a ty * 'a -> any

let () =
  let prog = If (Lt (Int 2, Add (Int 1, Int 3)), Pair (Int 10, Bool true), Pair (Int 0, Bool false)) in
  let (n, b) = eval prog in
  Printf.printf "%d %b %d\n" n b (eval (Fst prog));
  let values =
    [ Any (TInt, 42);
      Any (TString, "OCaml");
      Any (TList TInt, [ 1; 2; 3 ]);
      Any (TPair (TString, TList TString), ("tags", [ "fp"; "ml" ])) ]
  in
  List.iter (function Any (t, v) -> print_endline (show t v)) values
```

## Effect handlerek (OCaml 5)
<!-- q: Hogyan működnek az effect handlerek OCaml 5-ben és mire használhatók? -->
<!-- tags: effects, effect handlers, ocaml 5, continuations, generators, perform -->

Az OCaml 5 effect handlerei általánosított kivételek, amelyekből *vissza lehet térni*: a `perform` felfüggeszti a számítást, a handler megkapja a folytatást (`continuation`), és `continue k v`-vel értéket adhat vissza a felfüggesztés helyére. Ezzel könyvtárszinten valósítható meg generátor, async/await, kooperatív ütemező, függőség-befecskendezés vagy naplózás, a hívó kód módosítása („színezése”) nélkül — erre épül az Eio. Az effektet az `Effect.t` bővíthető GADT-hez adjuk hozzá, a handler a `Effect.Deep.try_with`/`match_with` függvénnyel (OCaml 5.3-tól `match ... with effect` szintaxissal is) írható. Buktató: a folytatás *egyszer* folytatható (one-shot), és a kezeletlen effekt `Effect.Unhandled` kivételt dob; az effektek típusrendszerben (még) nem látszanak.

```ocaml
open Effect
open Effect.Deep

(* Effektek deklarálása: a típusparaméter a perform visszatérési típusa *)
type _ Effect.t += Yield : int -> unit Effect.t
type _ Effect.t += Default_on_div_zero : int Effect.t

(* Bármely bejáró kódból generátor: a Yield-eket a handler gyűjti *)
let collect (f : unit -> unit) : int list =
  let acc = ref [] in
  try_with f ()
    { effc =
        (fun (type a) (eff : a Effect.t) ->
          match eff with
          | Yield x ->
              Some
                (fun (k : (a, unit) continuation) ->
                  acc := x :: !acc;
                  continue k ())               (* visszatérés a perform helyére *)
          | _ -> None) };                      (* más effektet továbbengedünk *)
  List.rev !acc

type tree = Leaf | Node of tree * int * tree

(* Hagyományos, callback nélküli bejárás; csak perform-ot hív *)
let rec walk = function
  | Leaf -> ()
  | Node (l, x, r) -> walk l; perform (Yield x); walk r

(* A hívó dönti el, mi legyen nullával osztáskor: a handler ad értéket *)
let safe_div a b = if b = 0 then perform Default_on_div_zero else a / b

let with_default (d : int) f =
  try_with f ()
    { effc =
        (fun (type a) (eff : a Effect.t) ->
          match eff with
          | Default_on_div_zero -> Some (fun (k : (a, _) continuation) -> continue k d)
          | _ -> None) }

let () =
  let t = Node (Node (Leaf, 1, Leaf), 2, Node (Leaf, 3, Node (Leaf, 4, Leaf))) in
  collect (fun () -> walk t) |> List.iter (Printf.printf "%d ");
  print_newline ();
  Printf.printf "%d\n" (with_default 0 (fun () -> safe_div 10 2 + safe_div 1 0));   (* 5 *)
  Printf.printf "%d\n" (with_default (-1) (fun () -> safe_div 7 0))                  (* -1 *)
```

## Domain-ek és többmagos párhuzamosság (OCaml 5)
<!-- q: Hogyan futtassak párhuzamos kódot több magon OCaml 5 Domain-ekkel? -->
<!-- tags: domains, parallelism, multicore, atomic, mutex, domainslib, ocaml 5 -->

Az OCaml 5 előtt egyetlen globális futtatási zár miatt nem volt valódi párhuzamosság; most a `Domain.spawn` egy OS-szálon futó, saját minor heappel rendelkező végrehajtási egységet indít, a `Domain.join` megvárja és visszaadja az eredményét. Domainből érdemes annyit indítani, amennyi mag van (`Domain.recommended_domain_count ()`), sok apró feladathoz pedig a `domainslib` task pool-ja (`Task.parallel_for`) vagy az Eio használata javasolt. Megosztott adathoz `Atomic` (lock-free számláló, CAS) vagy `Mutex` kell; a memóriamodell adatverseny esetén sem okoz memóriakorrupciót, de az eredmény nemdeterminisztikus lehet. Buktató: a stdlib `Hashtbl`, `Queue` stb. nem szálbiztos, és a domain létrehozása drága — ne indíts belőle ezreket.

```ocaml
(* Párhuzamos összegzés: a tömböt darabokra vágjuk, darabonként egy domain *)
let parallel_sum (arr : int array) n_domains =
  let len = Array.length arr in
  let chunk = (len + n_domains - 1) / n_domains in
  let worker i () =
    let lo = i * chunk and hi = min len ((i + 1) * chunk) in
    let s = ref 0 in
    for j = lo to hi - 1 do s := !s + arr.(j) done;
    !s                                         (* a domain eredménye *)
  in
  let domains = List.init n_domains (fun i -> Domain.spawn (worker i)) in
  List.fold_left (fun acc d -> acc + Domain.join d) 0 domains

(* Lock-free számláló Atomic-kal *)
let count_primes_parallel limit n_domains =
  let counter = Atomic.make 0 in
  let is_prime n =
    n >= 2 && (let rec go d = d * d > n || (n mod d <> 0 && go (d + 1)) in go 2)
  in
  let worker i () =
    (* Sávos szétosztás: i, i+n, i+2n, ... — kiegyensúlyozottabb terhelés *)
    let k = ref i in
    while !k <= limit do
      if is_prime !k then Atomic.incr counter;
      k := !k + n_domains
    done
  in
  List.init n_domains (fun i -> Domain.spawn (worker i)) |> List.iter Domain.join;
  Atomic.get counter

(* Megosztott Hashtbl Mutex-szel védve (Mutex.protect: OCaml 5.1+) *)
let shared_histogram words n_domains =
  let tbl = Hashtbl.create 16 and m = Mutex.create () in
  let worker i () =
    List.iteri
      (fun idx w ->
        if idx mod n_domains = i then
          Mutex.protect m (fun () ->
              let c = Option.value (Hashtbl.find_opt tbl w) ~default:0 in
              Hashtbl.replace tbl w (c + 1)))
      words
  in
  List.init n_domains (fun i -> Domain.spawn (worker i)) |> List.iter Domain.join;
  Hashtbl.fold (fun k v acc -> (k, v) :: acc) tbl [] |> List.sort compare

let () =
  let n = max 1 (min 4 (Domain.recommended_domain_count ())) in
  let arr = Array.init 1_000_000 (fun i -> i mod 7) in
  Printf.printf "domainek: %d, összeg: %d\n" n (parallel_sum arr n);
  Printf.printf "prímek 100000-ig: %d\n" (count_primes_parallel 100_000 n);
  shared_histogram [ "a"; "b"; "a"; "c"; "a"; "b" ] n
  |> List.iter (fun (w, c) -> Printf.printf "%s=%d " w c);
  print_newline ()
```

## Projektstruktúra dune-nal és tesztelés
<!-- q: Hogyan építsek fel egy OCaml projektet dune-nal könyvtárral, futtathatóval és tesztekkel? -->
<!-- tags: dune, opam, build system, library, executable, testing, ppx_expect -->

A dune az OCaml szabványos build-rendszere: a gyökérben a `dune-project` írja le a projektet (és opcionálisan generálja az `.opam` fájlt), minden könyvtárban egy `dune` fájl S-kifejezésekkel deklarálja a `library`, `executable` vagy `test` stanzákat. A könyvtár neve modulként érhető el a többi komponensből (`Mylib.Stats`), a ppx előfeldolgozók (`ppx_deriving`, `ppx_expect`) a `preprocess` mezőben kapcsolhatók be. Napi parancsok: `dune build`, `dune test`, `dune exec bin/main.exe`, `dune build @fmt --auto-promote` (ocamlformat). Buktató: a fordító figyelmeztetései dev profilban hibának számítanak (unused változó is!), release-hez `--profile release`; a függőségeket opam switch-ben kezeld.

```dune
; dune-project (gyökér)
(lang dune 3.11)
(name statkit)
(generate_opam_files true)
(package
 (name statkit)
 (depends ocaml dune (alcotest :with-test)))

; lib/dune — könyvtár, kívülről Statkit.Stats néven érhető el
(library
 (name statkit)
 (libraries str))

; bin/dune — futtatható
(executable
 (name main)
 (libraries statkit))

; test/dune — dune test futtatja
(test
 (name test_stats)
 (libraries statkit alcotest))
```

```ocaml
(* lib/stats.ml — tiszta, tesztelhető függvények *)
let mean = function
  | [] -> None
  | xs -> Some (List.fold_left ( +. ) 0. xs /. float_of_int (List.length xs))

let median xs =
  match List.sort Float.compare xs with
  | [] -> None
  | sorted ->
      let n = List.length sorted in
      if n mod 2 = 1 then Some (List.nth sorted (n / 2))
      else Some ((List.nth sorted (n / 2 - 1) +. List.nth sorted (n / 2)) /. 2.)

(* test/test_stats.ml — Alcotest tesztek *)
let opt_float = Alcotest.(option (float 1e-9))

let test_mean () =
  Alcotest.check opt_float "átlag" (Some 2.) (Statkit.Stats.mean [ 1.; 2.; 3. ]);
  Alcotest.check opt_float "üres lista" None (Statkit.Stats.mean [])

let test_median () =
  Alcotest.check opt_float "páratlan" (Some 3.) (Statkit.Stats.median [ 5.; 1.; 3. ]);
  Alcotest.check opt_float "páros" (Some 2.5) (Statkit.Stats.median [ 4.; 1.; 2.; 3. ])

let () =
  Alcotest.run "statkit"
    [ ("stats", [ Alcotest.test_case "mean" `Quick test_mean;
                  Alcotest.test_case "median" `Quick test_median ]) ]
```

## Polimorf variánsok és nyitott típusok
<!-- q: Mikor használjak polimorf variánsokat OCamlben a sima variánsok helyett? -->
<!-- tags: polymorphic variants, open types, subtyping, row polymorphism, error composition -->

A polimorf variánsok (`` `Not_found ``, `` `Timeout of float ``) előzetes típusdeklaráció nélkül használhatók, és a típusuk *nyitott* vagy *zárt* sor lehet (`[> `A | `B ]` = „legalább ezek”, `[< ...]` = „legfeljebb ezek”). Így különböző modulok hibatípusai automatikusan uniózhatók: egy függvény, amely két másikat hív, mindkettő hibáit visszaadhatja külön összevonó típus nélkül. Ez különösen kényelmes `result`-láncoknál. Buktató: a hibaüzenetek hosszúak lehetnek, egy elgépelt konstruktor (`` `Not_fuond ``) csendben új esetet hoz létre — a publikus API-n zárt típusannotációval (`type err = [ `A | `B ]`) rögzítsd a halmazt.

```ocaml
let ( let* ) = Result.bind

(* Két "modul" saját hibákkal; nincs közös hibatípus deklarálva *)
let parse_port s =
  match int_of_string_opt s with
  | None -> Error (`Bad_number s)
  | Some p when p < 1 || p > 65535 -> Error (`Out_of_range p)
  | Some p -> Ok p

let lookup env key =
  match List.assoc_opt key env with
  | Some v -> Ok v
  | None -> Error (`Missing_key key)

(* A típus automatikusan a hibák uniója:
   [> `Bad_number of string | `Missing_key of string | `Out_of_range of int ] *)
let load_port env =
  let* raw = lookup env "PORT" in
  let* port = parse_port raw in
  Ok port

(* Zárt típus a publikus API-hoz: elgépelés itt fordítási hibát ad *)
type config_error = [ `Bad_number of string | `Missing_key of string | `Out_of_range of int ]

let describe : config_error -> string = function
  | `Bad_number s -> Printf.sprintf "nem szám: %S" s
  | `Missing_key k -> Printf.sprintf "hiányzó kulcs: %s" k
  | `Out_of_range p -> Printf.sprintf "tartományon kívül: %d" p

(* Részhalmaz-kezelés: csak egyes eseteket kezelünk, a többit továbbadjuk *)
let with_default_port env =
  match load_port env with
  | Ok p -> Ok p
  | Error (`Missing_key _) -> Ok 8080
  | Error (#config_error as e) -> Error e      (* #típus: a típus összes esete *)

let () =
  let cases = [ [ ("PORT", "443") ]; [ ("PORT", "abc") ]; [ ("PORT", "99999") ]; [] ] in
  List.iter
    (fun env ->
      match with_default_port env with
      | Ok p -> Printf.printf "port: %d\n" p
      | Error e -> print_endline (describe e))
    cases
```
