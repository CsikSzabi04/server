# Prolog
<!-- tech: prolog -->
<!-- aliases: swi-prolog, swipl, logic programming, clpfd, datalog -->

A Prolog (PROgramming in LOGic) deklaratív, logikai programozási nyelv: a program tények és szabályok (Horn-klózok) halmaza, a futtatás pedig egy lekérdezés bizonyítása. A motor két alapmechanizmusa az *unifikáció* (két term mintaillesztéses egyesítése változókötéssel) és a *visszalépés* (backtracking: kudarc esetén az utolsó választási pontra lép vissza, és másik lehetőséget próbál). Így ugyanaz a reláció gyakran több irányban is használható (pl. az `append/3` összefűz és szétbont), a keresési feladatok pedig nagyon tömören leírhatók. Modern implementációja az SWI-Prolog (CLP(FD) korlátkezeléssel, tablinggal, DCG-vel, webes könyvtárakkal). Szakértői rendszerekhez, szabálymotorokhoz, nyelvi elemzéshez, ütemezéshez, típusellenőrzőkhöz és rejtvényszerű kombinatorikus feladatokhoz kiváló; általános alkalmazásfejlesztésre, numerikus számításra és nagy, imperatív I/O-intenzív rendszerekre kevésbé.

## Tények, szabályok és lekérdezések
<!-- q: Hogyan írjak tényeket, szabályokat és lekérdezéseket Prologban? -->
<!-- tags: facts, rules, queries, horn clauses, recursion, relations, logic programming -->

A Prolog-program *tényekből* (`parent(anna, bela).` — feltétel nélkül igaz állítások) és *szabályokból* (`Fej :- Törzs.` — a fej igaz, ha a törzs összes célja bizonyítható; a `,` ÉS, a `;` VAGY) áll. A kisbetűs nevek atomok (konstansok), a nagybetűvel vagy `_`-sal kezdődők változók. A lekérdezés (`?- grandparent(anna, X).`) során a motor felülről lefelé, balról jobbra próbálja a klózokat, és minden megoldást visszaad (`;`-vel kérhető a következő). Mivel relációkat írunk le, nem függvényeket, ugyanaz a predikátum különböző argumentum-mintákkal (ki a nagyszülője? kinek a nagyszülője?) is használható. Buktató: balrekurzív szabály (`ancestor(A, D) :- ancestor(A, X), ...` elöl) végtelen ciklusba fut — a rekurzív hívás kerüljön a nem rekurzív cél mögé (vagy használj tablinget).

```prolog
% Tények: parent(Szülő, Gyerek)
parent(anna, bela).
parent(anna, cili).
parent(bela, dora).
parent(bela, ede).
parent(cili, feri).
parent(dora, gabi).

female(anna).  female(cili).  female(dora).  female(gabi).
male(bela).    male(ede).     male(feri).

% Szabályok: a vessző ÉS-t jelent
mother(M, C)      :- parent(M, C), female(M).
grandparent(G, C) :- parent(G, P), parent(P, C).

% Testvérek: közös szülő, de nem ugyanaz a személy (\== : nem azonos term)
sibling(A, B) :- parent(P, A), parent(P, B), A \== B.

% Rekurzív szabály: előbb a nem rekurzív cél, így nincs végtelen ciklus
ancestor(A, D) :- parent(A, D).
ancestor(A, D) :- parent(A, X), ancestor(X, D).

% Unokatestvérek: a szülők testvérek
cousin(A, B) :- parent(PA, A), parent(PB, B), sibling(PA, PB).

% Hány leszármazottja van valakinek? (aggregate_all: SWI-Prolog)
descendant_count(P, N) :- aggregate_all(count, ancestor(P, _), N).

% Lekérdezések:
% ?- grandparent(anna, X).        X = dora ; X = ede ; X = feri.
% ?- grandparent(G, feri).        G = anna.         (fordított irány)
% ?- ancestor(anna, gabi).        true.
% ?- cousin(dora, X).             X = feri.
% ?- mother(M, bela).             M = anna.
% ?- descendant_count(anna, N).   N = 6.
```

## Unifikáció és termek
<!-- q: Hogyan működik az unifikáció Prologban és mi a különbség az =, ==, is és =:= között? -->
<!-- tags: unification, terms, pattern matching, is, comparison, occurs check, univ -->

Az unifikáció (`=`) két termet próbál azonossá tenni a változók lekötésével: `point(X, 2) = point(1, Y)` sikerül `X = 1, Y = 2` kötéssel, `f(X, X) = f(a, b)` viszont kudarc. Ez kétirányú mintaillesztés — a fejek illesztése klózválasztáskor, az adatszerkezetek szétbontása és felépítése is így történik. Fontos megkülönböztetni: `=` unifikál, `==` kötés nélkül vizsgál azonosságot, `is` kiértékeli a jobb oldali aritmetikai kifejezést és az eredményt unifikálja, `=:=` két kifejezés numerikus értékét hasonlítja össze. A `=..` (univ) és a `functor/3` termeket bont és épít, így általános term-transzformációk írhatók. Buktató: a `X = f(X)` occurs check nélkül ciklikus termet hoz létre (szükség esetén `unify_with_occurs_check/2`), és a `2 + 3 = 5` hamis, mert a `+` itt csak egy term, nem művelet.

```prolog
% Strukturált adat: termek beágyazva
employee(emp(anna, address(kecskemet, '6000'), salary(820000))).
employee(emp(bela, address(szeged, '6720'), salary(690000))).
employee(emp(cili, address(kecskemet, '6000'), salary(910000))).

% Unifikáció mint mélységi mintaillesztés: egy lépésben bontjuk szét
lives_in(Name, City) :- employee(emp(Name, address(City, _), _)).

% Term "frissítése": új term építése a régi részeiből (a termek immutábilisak)
raise(emp(N, A, salary(S0)), Pct, emp(N, A, salary(S))) :-
    S is round(S0 * (1 + Pct / 100)).

% Szimbolikus egyszerűsítés tisztán unifikációval
simplify(X * 1, X) :- !.
simplify(1 * X, X) :- !.
simplify(X + 0, X) :- !.
simplify(0 + X, X) :- !.
simplify(_ * 0, 0) :- !.
simplify(X, X).

% Általános term-bejárás =.. (univ) segítségével: minden atom nagybetűssé
upcase_atoms(T, U) :- atom(T), !, upcase_atom(T, U).
upcase_atoms(T, T) :- \+ compound(T), !.
upcase_atoms(T, U) :-
    T =.. [F | Args],                 % f(a, b) =.. [f, a, b]
    maplist(upcase_atoms, Args, UArgs),
    U =.. [F | UArgs].

% ?- point(X, 2) = point(1, Y).            X = 1, Y = 2.
% ?- f(X, X) = f(a, b).                    false.
% ?- X = 2 + 3, Y is X.                    X = 2+3, Y = 5.
% ?- 2 + 3 =:= 5.                          true.     ?- 2 + 3 == 5.  false.
% ?- unify_with_occurs_check(X, f(X)).     false.
% ?- lives_in(Who, kecskemet).             Who = anna ; Who = cili.
% ?- employee(E), E = emp(bela, _, _), raise(E, 10, E2).
%    E2 = emp(bela, address(szeged, '6720'), salary(759000)).
% ?- simplify(y * 1, S).                   S = y.
% ?- upcase_atoms(order(anna, [toll, fuzet], 3), U).
%    U = order('ANNA', ['TOLL', 'FUZET'], 3).
```

## Visszalépés és a megoldások gyűjtése
<!-- q: Hogyan működik a backtracking Prologban és hogyan gyűjtsem össze az összes megoldást (findall, bagof, setof)? -->
<!-- tags: backtracking, choice points, findall, bagof, setof, aggregate_all, generate and test -->

Ha egy cél kudarcot vall, a Prolog visszalép a legutóbbi *választási pontra* (ahol még volt ki nem próbált klóz vagy alternatíva), visszavonja az azóta keletkezett kötéseket, és a következő lehetőséggel folytatja — így egy „generálj és tesztelj” szabály automatikusan bejárja a teljes keresési teret. Az összes megoldás gyűjtésére a `findall/3` (mindig listát ad, akár üreset), a `bagof/3` (szabad változók szerint csoportosít, megoldás nélkül kudarcot vall; `V^Cél` jelöli a figyelmen kívül hagyandó változót), a `setof/3` (mint a bagof, de rendezett és duplikátum-mentes) és az SWI `aggregate_all/3` (count, sum, max, bag, set) való. Buktató: a generálj-és-tesztelj exponenciális lehet — a teszteket tedd minél korábbra (a generálás közé), vagy használj CLP(FD)-t.

```prolog
% product(Név, Kategória, Ár)
product(laptop, electronics, 450000).
product(phone,  electronics, 220000).
product(tablet, electronics, 160000).
product(desk,   furniture,    89000).
product(chair,  furniture,    45000).
product(lamp,   furniture,    12000).

% Generálj és tesztelj: két különböző kategóriájú termék a kereten belül.
% A C1 @< C2 feltétel kiszűri a fordított sorrendű duplikátumokat.
bundle(Budget, P1-P2, Total) :-
    product(P1, C1, Price1),
    product(P2, C2, Price2),
    C1 @< C2,                          % korai teszt: kevesebb felesleges ág
    Total is Price1 + Price2,
    Total =< Budget.

% Legolcsóbb termék kategóriánként: a bagof csoportosít a szabad C szerint
cheapest(Category, Name-Price) :-
    bagof(P-N, product(N, Category, P), Pairs),
    keysort(Pairs, [Price-Name | _]).

% Összes megoldás különféle módokon
report :-
    findall(B-T, bundle(250000, B, T), Bundles),
    format("Csomagok 250 000 Ft alatt: ~w~n", [Bundles]),
    setof(C, N^P^product(N, C, P), Categories),          % N, P egzisztenciálisan kötve
    format("Kategóriák: ~w~n", [Categories]),
    forall(cheapest(C, Item), format("  ~w legolcsóbb: ~w~n", [C, Item])),
    aggregate_all(sum(P), product(_, furniture, P), FurnitureSum),
    aggregate_all(max(P, N), product(N, _, P), max(MaxP, MaxN)),
    format("Bútor összesen: ~d, legdrágább: ~w (~d)~n", [FurnitureSum, MaxN, MaxP]).

% ?- bundle(250000, B, T).   B = phone-lamp, T = 232000 ; B = tablet-desk, T = 249000 ; ...
% ?- bundle(150000, B, T).   false.   (nincs ilyen olcsó elektronikai termék)
% ?- report.
```

## Listák és rekurzió
<!-- q: Hogyan dolgozzak listákkal és rekurzióval Prologban (append, akkumulátor, maplist, foldl)? -->
<!-- tags: lists, recursion, accumulator, append, reverse, maplist, foldl, tail recursion -->

A Prolog-lista `[Fej | Farok]` alakú term, ezért a listafeldolgozás rekurzió: egy klóz az üres listára (`[]`), egy a nem üresre. A tiszta relációk több irányban működnek — az `append/3` összefűz, szétbont, előtagot vagy utótagot keres —, ami a Prolog egyik legnagyobb ereje. Az akkumulátoros (farokrekurzív) változat konstans stacket használ és gyorsabb (pl. `reverse` O(n) a naiv O(n²) helyett), az SWI magasabbrendű predikátumai (`maplist`, `foldl`, `include`, `exclude`) pedig kiváltják a kézi rekurzió nagy részét. Buktató: az `is` nem relációs (csak kötött jobb oldallal működik), ezért pl. a hosszt számoló predikátum fordított irányban hibát ad — ilyen esetre CLP(FD) (`#=`) kell; a `length/2` és `msort/2` beépített és gyorsabb a saját változatnál.

```prolog
% Klasszikus append: mindkét irányban használható
my_append([], L, L).
my_append([H | T], L, [H | R]) :- my_append(T, L, R).

% Akkumulátoros megfordítás: O(n), farokrekurzív
my_reverse(L, R) :- rev(L, [], R).
rev([], Acc, Acc).
rev([H | T], Acc, R) :- rev(T, [H | Acc], R).

% Összeg akkumulátorral
sum_acc([], S, S).
sum_acc([X | Xs], Acc, S) :- Acc1 is Acc + X, sum_acc(Xs, Acc1, S).

% Futáshossz-kódolás: [a,a,b,c,c,c] -> [a-2, b-1, c-3]
rle([], []).
rle([X | Xs], [X-N | Rest]) :-
    count_run(X, Xs, 1, N, Tail),
    rle(Tail, Rest).

count_run(X, [Y | Ys], N0, N, Tail) :-
    X == Y, !,
    N1 is N0 + 1,
    count_run(X, Ys, N1, N, Tail).
count_run(_, Tail, N, N, Tail).

% Lista szétválasztása predikátum szerint (partition)
split_by(_, [], [], []).
split_by(P, [X | Xs], [X | Ys], Ns) :- call(P, X), !, split_by(P, Xs, Ys, Ns).
split_by(P, [X | Xs], Ys, [X | Ns]) :- split_by(P, Xs, Ys, Ns).

positive(X) :- X > 0.

% Magasabbrendű predikátumok (SWI-Prolog library(apply), library(yall))
stats(Xs, Sum, Squares, Evens) :-
    foldl([X, A0, A] >> (A is A0 + X), Xs, 0, Sum),
    maplist([X, Y] >> (Y is X * X), Xs, Squares),
    include([X] >> (0 is X mod 2), Xs, Evens).

% ?- my_append(X, Y, [1, 2, 3]).     X = [], Y = [1,2,3] ; X = [1], Y = [2,3] ; ...
% ?- my_append(X, [3], [1, 2, 3]).   X = [1, 2].           (utótag levágása)
% ?- my_reverse([1, 2, 3], R).       R = [3, 2, 1].
% ?- rle([a, a, b, c, c, c], R).     R = [a-2, b-1, c-3].
% ?- split_by(positive, [3, -1, 0, 5], P, N).   P = [3, 5], N = [-1, 0].
% ?- stats([1, 2, 3, 4], S, Q, E).   S = 10, Q = [1,4,9,16], E = [2,4].
```

## A vágás (cut) és a negáció
<!-- q: Mit csinál a vágás (!) Prologban, és hogyan működik a negáció mint kudarc (\+)? -->
<!-- tags: cut, green cut, red cut, negation as failure, if-then-else, once, closed world -->

A vágás (`!`) elvágja a választási pontokat: miután teljesült, az adott predikátum további klózait és a vágás előtti célok alternatíváit már nem próbálja a motor. A *zöld* vágás csak hatékonyságot javít (a jelentés nem változik), a *piros* vágás viszont a program logikáját is módosítja, és gyakran helytelen eredményt ad, ha a predikátumot nem a „várt” irányban hívják. Biztonságosabb alternatívák: az if-then-else (`( Feltétel -> Akkor ; Különben )`) és a `once/1`. A `\+ Cél` (negáció mint kudarc) akkor igaz, ha a cél *nem bizonyítható* — ez a zárt világ feltevésén alapul, és nem köt változót. Buktató: kötetlen változóval hívott negáció hamis eredményt ad (pl. `\+ booked(R)` előbb, `room(R)` utána) — a negáció előtt mindig kösd le a változókat.

```prolog
% PIROS vágás — hibás: a max_bad(5, 3, 3) lekérdezés IGAZ lesz!
% (az első klóz feje nem illeszkedik, így a második "elfogadja" a rossz eredményt)
max_bad(X, Y, X) :- X >= Y, !.
max_bad(_, Y, Y).

% Helyes: az eredményt a vágás / feltétel UTÁN kötjük
max_ok(X, Y, Z) :- ( X >= Y -> Z = X ; Z = Y ).

% ZÖLD vágás: a klózok kizárják egymást, a vágás csak a felesleges választási pontot szünteti meg
classify(N, negative) :- N < 0, !.
classify(0, zero) :- !.
classify(N, positive) :- N > 0.

% Szobafoglalás: negáció mint kudarc
room(r101). room(r102). room(r201).
booked(r101, '2026-12-01').
booked(r201, '2026-12-02').

% Helyes sorrend: előbb generáljuk a szobát (R kötött), utána a negáció
free_on(Room, Day) :- room(Room), \+ booked(Room, Day).

% HIBÁS sorrend: \+ booked(R, Day) kötetlen R-rel "van-e BÁRMI foglalás"-t jelent
free_on_bad(Room, Day) :- \+ booked(Room, Day), room(Room).

% once/1: csak az első megoldás kell (pl. alapértelmezett érték kiválasztása)
first_free(Day, Room) :- once(free_on(Room, Day)).

% If-then-else lánc: determinisztikus döntési tábla
shipping(Weight, Cost) :-
    (   Weight =< 1  -> Cost = 990
    ;   Weight =< 5  -> Cost = 1490
    ;   Weight =< 20 -> Cost = 2990
    ;   Cost is 2990 + ceiling(Weight - 20) * 150
    ).

% ?- max_bad(5, 3, 3).              true.   (HIBÁS!)
% ?- max_ok(5, 3, Z).               Z = 5.
% ?- classify(-4, C).               C = negative.
% ?- free_on(R, '2026-12-01').      R = r102 ; R = r201.
% ?- free_on_bad(R, '2026-12-01').  false.  (pedig van szabad szoba)
% ?- first_free('2026-12-02', R).   R = r101.
% ?- shipping(23.5, C).             C = 3590.
```

## Gráfkeresés: útvonalak DFS-sel és BFS-sel
<!-- q: Hogyan keressek útvonalat gráfban Prologban körök elkerülésével (DFS, BFS, legrövidebb út)? -->
<!-- tags: graph search, dfs, bfs, path finding, cycles, shortest path, backtracking -->

A Prolog visszalépése természetes mélységi keresést (DFS) ad: a `path` szabály minden lehetséges utat felsorol, amelyhez csak a már bejárt csúcsok listáját kell vinni a körök elkerülésére. Az összes megoldás közül az `aggregate_all(min(...))` választja ki a legrövidebbet — kis gráfon ez egyszerű és helyes, nagy gráfon viszont exponenciális. Lépésszámban legrövidebb útra a szélességi keresés (BFS) való: sorként kezelt útlista, ahol minden lépésben az összes új szomszéd a sor végére kerül; súlyozott gráfon Dijkstra-algoritmus (prioritási sorral, pl. `library(pairs)`/`library(heaps)`). Buktató: a `visited` lista nélküli rekurzió irányítatlan vagy körös gráfon végtelen ciklusba fut, és a `memberchk` O(n) — nagy gráfnál `library(assoc)` vagy tabling kell.

```prolog
% Irányítatlan, súlyozott gráf: út(Város1, Város2, km)
road(budapest,  kecskemet,  86).
road(kecskemet, szeged,     87).
road(budapest,  szolnok,   100).
road(szolnok,   kecskemet,  60).
road(szolnok,   debrecen,  120).
road(szeged,    bekescsaba, 98).
road(debrecen,  bekescsaba, 115).

connected(X, Y, D) :- road(X, Y, D).
connected(X, Y, D) :- road(Y, X, D).

% DFS: minden körmentes út visszalépéssel; a Visited fordított sorrendben gyűlik
path(From, To, Path, Km) :-
    dfs(From, To, [From], RevPath, Km),
    reverse(RevPath, Path).

dfs(To, To, Visited, Visited, 0).
dfs(From, To, Visited, Path, Km) :-
    connected(From, Next, D),
    \+ memberchk(Next, Visited),          % körök kizárása
    dfs(Next, To, [Next | Visited], Path, Km0),
    Km is Km0 + D.

% Legrövidebb út kilométerben: minimum az összes DFS-megoldás közül
shortest(From, To, Path, Km) :-
    aggregate_all(min(K, P), path(From, To, P, K), min(Km, Path)).

% BFS: lépésszámban legrövidebb út; a sor elemei fordított útvonalak
bfs(Start, Goal, Path) :-
    bfs_queue([[Start]], Goal, [Start], RevPath),
    reverse(RevPath, Path).

bfs_queue([[Goal | Rest] | _], Goal, _, [Goal | Rest]) :- !.
bfs_queue([[Node | Rest] | Queue], Goal, Seen, Path) :-
    findall(Next, (connected(Node, Next, _), \+ memberchk(Next, Seen)), Nexts0),
    sort(Nexts0, Nexts),                    % duplikátumok kiszűrése
    findall([N, Node | Rest], member(N, Nexts), NewPaths),
    append(Seen, Nexts, Seen1),
    append(Queue, NewPaths, Queue1),        % sor végére: szélességi bejárás
    bfs_queue(Queue1, Goal, Seen1, Path).

% ?- path(budapest, szeged, P, Km).
%    P = [budapest, kecskemet, szeged], Km = 173 ; ...
% ?- shortest(budapest, bekescsaba, P, Km).
%    P = [budapest, kecskemet, szeged, bekescsaba], Km = 271.
% ?- bfs(budapest, bekescsaba, P).
%    P = [budapest, kecskemet, szeged, bekescsaba].
```

## DCG: nyelvtanok és parserek
<!-- q: Hogyan írjak parsert Prologban DCG (Definite Clause Grammar) nyelvtannal? -->
<!-- tags: dcg, grammar, parsing, phrase, definite clause grammar, tokenizer, nlp -->

A DCG (Definite Clause Grammar) a Prolog beépített nyelvtan-jelölése: a `-->` szabályokat a fordító rejtett „differencia-lista” argumentumokkal kiegészített sima predikátumokká alakítja, így a nyelvtan közvetlenül futtatható parser lesz, visszalépéssel kezelve a többértelműséget. A szabályok argumentumokat kaphatnak (pl. a felépített szintaxisfát vagy a kiszámolt értéket), a `{ ... }` kapcsos zárójelben sima Prolog-cél fut, a `phrase/2,3` pedig elindítja a feldolgozást karakterkód- vagy tokenlistán. Ugyanaz a DCG gyakran generálásra is használható (fordított irányban). Buktató: a balrekurzív szabály (`expr --> expr, "+", term`) végtelen ciklust okoz — akkumulátoros `expr_rest` mintával kell átírni, ami a balasszociativitást is helyesen kezeli; a felesleges visszalépést `!`-tal vagy determinisztikus szabályokkal érdemes korlátozni.

```prolog
:- use_module(library(dcg/basics)).     % blanks//0, number//1

% Aritmetikai kifejezés kiértékelése; balasszociatív operátorok akkumulátorral
expr(V) --> blanks, term(T), blanks, expr_rest(T, V).

expr_rest(Acc, V) --> "+", !, blanks, term(T), blanks, { Acc1 is Acc + T }, expr_rest(Acc1, V).
expr_rest(Acc, V) --> "-", !, blanks, term(T), blanks, { Acc1 is Acc - T }, expr_rest(Acc1, V).
expr_rest(V, V)   --> [].

term(V) --> factor(F), blanks, term_rest(F, V).

term_rest(Acc, V) --> "*", !, blanks, factor(F), blanks, { Acc1 is Acc * F }, term_rest(Acc1, V).
term_rest(Acc, V) --> "/", !, blanks, factor(F), blanks, { F =\= 0, Acc1 is Acc / F }, term_rest(Acc1, V).
term_rest(V, V)   --> [].

factor(V) --> "(", !, blanks, expr(V), blanks, ")".
factor(V) --> number(V).

calc(Text, Value) :-
    string_codes(Text, Codes),
    phrase(expr(Value), Codes).

% Tokenlista-alapú parancsnyelv szövegkalandhoz: a kimenet egy strukturált term
command(move(Dir, N)) --> [go], direction(Dir), steps(N).
command(take(Obj))    --> [take], article, [Obj].
command(look)         --> [look].

direction(north) --> [north].
direction(south) --> [south].
direction(east)  --> [east].
direction(west)  --> [west].

steps(N) --> [N], { integer(N), N > 0 }, [steps].
steps(1) --> [].

article --> [the].
article --> [].

% ?- calc("2 + 3 * (10 - 4) / 2", V).      V = 11.
% ?- calc("10 - 3 - 2", V).                V = 5.      (balasszociatív)
% ?- phrase(command(C), [go, north, 3, steps]).   C = move(north, 3).
% ?- phrase(command(C), [take, the, lamp]).       C = take(lamp).
% Generálás fordított irányban:
% ?- phrase(command(take(key)), Tokens).   Tokens = [take, the, key] ; Tokens = [take, key].
```

## CLP(FD): korlátkezelés egész számokon
<!-- q: Hogyan oldjak meg kombinatorikus feladatokat CLP(FD) korlátkezeléssel Prologban? -->
<!-- tags: clpfd, constraint logic programming, constraints, labeling, optimization, send more money -->

A `library(clpfd)` egész számokon értelmezett korlátokat ad: a `#=`, `#\=`, `#<` stb. a hagyományos aritmetikával (`is`) szemben *relációs*, tehát kötetlen változókkal is működnek, és tartomány-szűkítéssel (propagáció) azonnal kizárják a lehetetlen értékeket. A feladatot deklaratívan írjuk le (változók, tartományok `ins`-szel, korlátok, pl. `all_different`), majd a `label/1`/`labeling/2` a megmaradt keresési teret járja be, opcionálisan heurisztikával (`ff`: legkisebb tartomány először) vagy optimalizálási céllal (`min(Kifejezés)`). Ez nagyságrendekkel gyorsabb a generálj-és-tesztelj módszernél. Buktató: a címkézés nélküli eredmény csak a szűkített tartományokat mutatja (nem konkrét megoldást), és rosszul megfogalmazott modellnél a keresés exponenciális — a redundáns, de erős korlátok sokat gyorsíthatnak.

```prolog
:- use_module(library(clpfd)).

% Relációs faktoriális: mindkét irányban működik (az is-alapú nem!)
n_factorial(0, 1).
n_factorial(N, F) :-
    N #> 0,
    N1 #= N - 1,
    F #= N * F1,
    n_factorial(N1, F1).

% SEND + MORE = MONEY: minden betű különböző számjegy
send_more_money([S, E, N, D, M, O, R, Y]) :-
    Vars = [S, E, N, D, M, O, R, Y],
    Vars ins 0..9,
    all_different(Vars),
    S #\= 0, M #\= 0,
              1000 * S + 100 * E + 10 * N + D
            + 1000 * M + 100 * O + 10 * R + E
    #= 10000 * M + 1000 * O + 100 * N + 10 * E + Y,
    label(Vars).

% Optimalizálás: pénzváltás a lehető legkevesebb érmével/bankjeggyel
change(Amount, [N200, N100, N50, N20, N10], Count) :-
    Coins = [N200, N100, N50, N20, N10],
    Coins ins 0..Amount,
    200 * N200 + 100 * N100 + 50 * N50 + 20 * N20 + 10 * N10 #= Amount,
    Count #= N200 + N100 + N50 + N20 + N10,
    once(labeling([min(Count)], Coins)).

% Műszakbeosztás: 3 dolgozó, 7 nap, naponta pontosan 2 ember,
% senki nem dolgozik 5 napnál többet és 3 egymást követő napon
schedule(Rows) :-
    length(Rows, 3),
    maplist([Row] >> (length(Row, 7), Row ins 0..1, sum(Row, #=<, 5), no_three(Row)), Rows),
    transpose(Rows, Days),
    maplist([Day] >> sum(Day, #=, 2), Days),
    append(Rows, Vs),
    label(Vs).

no_three([A, B, C | Rest]) :- !, A + B + C #=< 2, no_three([B, C | Rest]).
no_three(_).

% ?- n_factorial(5, F).        F = 120.
% ?- n_factorial(N, 120).      N = 5.    (fordított irány!)
% ?- send_more_money(L).       L = [9, 5, 6, 7, 1, 0, 8, 2].
% ?- change(380, C, N).        C = [1, 1, 1, 1, 1], N = 5.
% ?- schedule(R), maplist(writeln, R).
```

## N-királynő probléma
<!-- q: Hogyan oldjam meg az N-királynő problémát Prologban visszalépéssel és CLP(FD)-vel? -->
<!-- tags: n-queens, backtracking, clpfd, puzzle, constraint propagation, labeling, ff heuristic -->

Az N-királynő feladat: N királynőt kell elhelyezni egy N×N-es táblán úgy, hogy egyik se üsse a másikat (nincs két királynő azonos sorban, oszlopban vagy átlón). A reprezentáció: a lista i-edik eleme az i-edik oszlopban álló királynő sorszáma — így az oszlopütközés eleve kizárt, a sorütközést a különböző értékek, az átlót pedig a `|Qi - Qj| ≠ |i - j|` feltétel kezeli. A tiszta visszalépéses megoldás (`select` + ütésellenőrzés minden lerakáskor) kis N-re jó, a CLP(FD)-s változat viszont előre propagálja a korlátokat, és `ff` (first-fail) címkézéssel N = 100 fölött is gyors. Buktató: a „minden permutáció, aztán teszt” megközelítés N! lépést igényel — az ellenőrzést mindig a generálásba építsd be.

```prolog
:- use_module(library(clpfd)).

% ---- 1) Klasszikus visszalépés: minden lerakás után azonnal ellenőrzünk ----
queens_bt(N, Qs) :-
    numlist(1, N, Rows),
    place(Rows, [], Qs).

place([], Placed, Placed).
place(Unplaced, Placed, Qs) :-
    select(Q, Unplaced, Rest),            % választási pont: melyik sor
    \+ attacks(Q, Placed, 1),             % korai teszt -> erős metszés
    place(Rest, [Q | Placed], Qs).

% Q üt-e átlósan valamit a már lerakottak közül (D = oszlopkülönbség)
attacks(Q, [Q1 | _], D) :- abs(Q - Q1) =:= D.
attacks(Q, [_ | Qs], D) :- D1 is D + 1, attacks(Q, Qs, D1).

% ---- 2) CLP(FD): korlátok előre, propagációval, majd címkézés ----
n_queens(N, Qs) :-
    length(Qs, N),
    Qs ins 1..N,
    safe_queens(Qs).

safe_queens([]).
safe_queens([Q | Qs]) :- safe_queens(Qs, Q, 1), safe_queens(Qs).

safe_queens([], _, _).
safe_queens([Q | Qs], Q0, D0) :-
    Q0 #\= Q,                             % különböző sor
    abs(Q0 - Q) #\= D0,                   % nem azonos átló
    D1 #= D0 + 1,
    safe_queens(Qs, Q0, D1).

% Tábla kirajzolása
print_board(Qs) :-
    length(Qs, N),
    forall(between(1, N, Row),
           ( forall(member(Q, Qs), (Q =:= Row -> write(' Q') ; write(' .'))), nl )).

% ?- queens_bt(8, Qs), print_board(Qs).
% ?- findall(Q, queens_bt(8, Q), All), length(All, Count).    Count = 92.
% ?- n_queens(8, Qs), labeling([ff], Qs).                     Qs = [1, 5, 8, 6, 3, 7, 2, 4].
% ?- n_queens(100, Qs), labeling([ff], Qs).                   (másodperc alatt)
```

## Sudoku megoldása CLP(FD)-vel
<!-- q: Hogyan oldjak meg Sudokut Prologban CLP(FD) korlátokkal? -->
<!-- tags: sudoku, clpfd, all_distinct, transpose, constraint propagation, puzzle -->

A Sudoku tökéletes példa a deklaratív korlátprogramozásra: nem algoritmust írunk, hanem leírjuk a szabályokat — minden cella 1..9, minden sor, oszlop és 3×3-as blokk elemei különbözők —, a megoldást pedig a CLP(FD) propagációja és címkézése találja meg. Az `all_distinct/1` erősebb propagációt végez, mint az `all_different/1` (a Hall-tétel alapú szűrés miatt sok rejtvényt címkézés nélkül, pusztán következtetéssel megold), a `transpose/2` az oszlopokat, egy rekurzív segédpredikátum a blokkokat állítja elő. A megadott számok egyszerűen előre kötött változók a mátrixban. Buktató: a legnehezebb rejtvényeknél is kell `labeling([ff], ...)`, és a gyengébb `all_different` sokkal nagyobb keresési fát eredményezhet.

```prolog
:- use_module(library(clpfd)).

sudoku(Rows) :-
    length(Rows, 9),
    maplist(same_length(Rows), Rows),     % 9x9-es mátrix
    append(Rows, Cells), Cells ins 1..9,
    maplist(all_distinct, Rows),          % sorok
    transpose(Rows, Columns),
    maplist(all_distinct, Columns),       % oszlopok
    Rows = [As, Bs, Cs, Ds, Es, Fs, Gs, Hs, Is],
    blocks(As, Bs, Cs),                   % 3x3-as blokkok, három sorcsoportban
    blocks(Ds, Es, Fs),
    blocks(Gs, Hs, Is).

% Három sor első három eleméből egy blokk, majd rekurzívan a következő három oszlop
blocks([], [], []).
blocks([N1, N2, N3 | Ns1], [N4, N5, N6 | Ns2], [N7, N8, N9 | Ns3]) :-
    all_distinct([N1, N2, N3, N4, N5, N6, N7, N8, N9]),
    blocks(Ns1, Ns2, Ns3).

% Egy nehéz rejtvény: a _ az ismeretlen cella
problem(1, [[_, _, _, _, _, _, _, _, _],
            [_, _, _, _, _, 3, _, 8, 5],
            [_, _, 1, _, 2, _, _, _, _],
            [_, _, _, 5, _, 7, _, _, _],
            [_, _, 4, _, _, _, 1, _, _],
            [_, 9, _, _, _, _, _, _, _],
            [5, _, _, _, _, _, _, 7, 3],
            [_, _, 2, _, 1, _, _, _, _],
            [_, _, _, _, 4, _, _, _, 9]]).

solve(Id) :-
    problem(Id, Rows),
    sudoku(Rows),
    maplist(labeling([ff]), Rows),        % first-fail heurisztika
    maplist(print_row, Rows).

print_row(Row) :- atomic_list_concat(Row, ' ', Line), writeln(Line).

% ?- solve(1).
% 9 8 7 6 5 4 3 2 1
% 2 4 6 1 7 3 9 8 5
% ...
```

## Hibakezelés, típusellenőrzés és erőforrások
<!-- q: Hogyan kezeljem a hibákat és kivételeket Prologban (catch, throw, must_be, setup_call_cleanup)? -->
<!-- tags: error handling, catch, throw, must_be, setup_call_cleanup, iso errors, determinism -->

A Prolog a kudarcot (`false`) és a hibát (kivétel) megkülönbözteti: a kudarc azt jelenti, hogy „nincs megoldás”, és visszalépést indít, a kivétel (`throw/1`) viszont a választási pontokon át a legközelebbi illeszkedő `catch/3`-ig fut. Az ISO szabvány hibaformátuma `error(Formális, Kontextus)` (pl. `type_error(integer, abc)`, `existence_error(...)`), az SWI `must_be/2` pedig egy sorban ellenőrzi az argumentumok típusát és szabványos hibát dob. Erőforrásokhoz (fájl, adatbázis-kapcsolat) a `setup_call_cleanup/3` garantálja a lezárást hiba, kudarc vagy vágás esetén is. Buktató: ha egy belső hiba csendes kudarccá alakul (pl. mindent elkapó `catch(_, _, fail)`), a hibakeresés nagyon nehézzé válik — csak a várt hibamintát kapd el.

```prolog
:- use_module(library(error)).      % must_be/2, domain_error/2
:- use_module(library(readutil)).   % read_line_to_string/2

% Típus- és tartományellenőrzés szabványos ISO hibákkal
safe_div(X, Y, Z) :-
    must_be(number, X),
    must_be(number, Y),
    (   Y =:= 0
    ->  throw(error(evaluation_error(zero_divisor), context(safe_div/3, _)))
    ;   Z is X / Y
    ).

% Csak a várt hibákat kapjuk el, mintaillesztéssel a hibatermen
try_div(X, Y, Result) :-
    catch(safe_div(X, Y, Z),
          error(Err, _),
          ( describe(Err, Msg), Result = error(Msg) )),
    ( var(Result) -> Result = ok(Z) ; true ).

describe(type_error(Type, Value), Msg) :-
    format(atom(Msg), "típushiba: ~w helyett ~w", [Type, Value]).
describe(evaluation_error(zero_divisor), 'nullával osztás').
describe(instantiation_error, 'kötetlen argumentum').

% Saját üzleti szabály hibája domain_error-ral
set_discount(Pct) :-
    must_be(integer, Pct),
    (   between(0, 50, Pct) -> true
    ;   domain_error(between(0, 50), Pct)
    ).

% Erőforrás garantált lezárása: a stream hiba esetén is bezárul
count_lines(File, N) :-
    setup_call_cleanup(
        open(File, read, Stream),
        count_stream_lines(Stream, 0, N),
        close(Stream)).

count_stream_lines(S, N0, N) :-
    read_line_to_string(S, Line),
    (   Line == end_of_file
    ->  N = N0
    ;   N1 is N0 + 1,
        count_stream_lines(S, N1, N)
    ).

% ?- try_div(10, 4, R).       R = ok(2.5).
% ?- try_div(10, 0, R).       R = error('nullával osztás').
% ?- try_div(10, abc, R).     R = error('típushiba: number helyett abc').
% ?- catch(set_discount(80), error(E, _), true).   E = domain_error(between(0,50), 80).
% ?- catch(count_lines('nincs.txt', N), error(E, _), true).   E = existence_error(source_sink, 'nincs.txt').
```

## Dinamikus adatbázis és tabling
<!-- q: Hogyan módosítsam futás közben a Prolog adatbázist (assert, retract), és mire jó a tabling? -->
<!-- tags: dynamic predicates, assert, retract, tabling, memoization, left recursion, datalog -->

A `:- dynamic` direktívával deklarált predikátumok futás közben bővíthetők (`assertz`, `asserta`) és törölhetők (`retract`, `retractall`), így a program tényadatbázisa állapotként (számlálók, cache, munkamenet) használható. Ez erős, de a logikai tisztaságot rontja: a sorrendfüggő mellékhatás nehezen követhető, ezért csak jól körülhatárolt helyeken (pl. egy modul belső cache-e) használd. A *tabling* (`:- table pred/N.`) automatikus memoizációt ad: a már kiszámolt részcélok eredményét táblázatban tárolja, így az exponenciális rekurzió (Fibonacci) polinomiális lesz, a balrekurzív és körös szabályok (pl. tranzitív lezárt körös gráfon) pedig véges idő alatt, teljes eredménnyel futnak — ez a Datalog-szerű lekérdezések alapja. Buktató: a tablázott predikátum memóriát fogyaszt (`abolish_all_tables/0` üríti), és a dinamikus adatbázis módosítása után a régi táblák elavulhatnak (erre van incremental tabling).

```prolog
% ---- Dinamikus tények: egyszerű kulcs-számláló ----
:- dynamic counter/2.

incr(Key) :-
    (   retract(counter(Key, N0))
    ->  N is N0 + 1
    ;   N = 1
    ),
    assertz(counter(Key, N)).

reset_counters :- retractall(counter(_, _)).

% Eseménynapló feldolgozása: a számlálók a feldolgozás után lekérdezhetők
log_events(Events) :-
    reset_counters,
    forall(member(E, Events), incr(E)).

% ---- Tabling: memoizáció ----
:- table fib/2.
fib(0, 0).
fib(1, 1).
fib(N, F) :-
    N > 1,
    N1 is N - 1, N2 is N - 2,
    fib(N1, F1), fib(N2, F2),
    F is F1 + F2.

% ---- Tabling: balrekurzív tranzitív lezárt körös gráfon ----
% Tabling nélkül ez végtelen ciklus lenne (balrekurzió + a -> b -> c -> a kör)
:- table reachable/2.
reachable(X, Y) :- reachable(X, Z), link(Z, Y).
reachable(X, Y) :- link(X, Y).

link(a, b).
link(b, c).
link(c, a).
link(c, d).
link(e, f).

% Függőségi gráf: mely csomagokat kell telepíteni egy adott csomaghoz?
:- table needs/2.
needs(P, D) :- depends(P, D).
needs(P, D) :- needs(P, X), depends(X, D).

depends(webapp, framework).
depends(framework, http).
depends(framework, json).
depends(http, sockets).
depends(json, unicode).

install_order(Pkg, Deps) :- setof(D, needs(Pkg, D), Deps).

% ?- log_events([login, view, view, logout, view]), counter(view, N).   N = 3.
% ?- fib(200, F).                 (azonnal, tabling nélkül soha nem érne véget)
% ?- findall(Y, reachable(a, Y), L), sort(L, S).   S = [a, b, c, d].
% ?- reachable(a, f).             false.   (véges idő alatt)
% ?- install_order(webapp, D).    D = [framework, http, json, sockets, unicode].
```
