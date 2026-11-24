# Erlang
<!-- tech: erlang -->
<!-- aliases: otp, beam, erl, rebar3 -->

Az Erlang a telekommunikációs iparhoz (Ericsson) készült, dinamikusan típusos, funkcionális nyelv, amelynek ereje a futtatókörnyezetben (BEAM) és az OTP keretrendszerben van: millió izolált, könnyűsúlyú folyamat, aszinkron üzenetküldés megosztott memória nélkül, folyamatonkénti GC (nincs globális „stop the world”), beépített elosztottság több gép között és futás közbeni kódcsere. A filozófia a „let it crash”: a hibát nem mindenhol védekezve kezeljük, hanem hagyjuk a folyamatot összeomlani, és a felügyelő (supervisor) tiszta állapotból újraindítja. Telekom-, üzenetküldő (WhatsApp), adatbázis- (Riak, CouchDB), üzenetsor- (RabbitMQ) és nagy rendelkezésre állású rendszerekhez kiváló; nyers számításra, GUI-ra vagy ott, ahol erős statikus típusosság kell, kevésbé (a Dialyzer és a gradual typing csak részben pótolja).

## Mintaillesztés, guardok és rekurzió
<!-- q: Hogyan működik a mintaillesztés, a guard és a rekurzió Erlangban? -->
<!-- tags: pattern matching, guards, recursion, tail recursion, list comprehension, atoms, tuples -->

Erlangban a változók egyszer köthetők (single assignment), a `=` pedig illesztés: ha a minta nem egyezik, `badmatch` hiba keletkezik. A függvények több klózból állnak (`;`-vel elválasztva, `.`-tal lezárva), és a futtatókörnyezet az első illeszkedő mintájú, igaz guardú klózt választja. Az adatok atomok (`ok`, `error`), tuple-ök (tagged tuple: `{circle, R}`), listák és map-ek; ciklus nincs, helyette rekurzió és list comprehension. A farokrekurzív függvény konstans stacket használ, ezért a hosszú életű folyamat-ciklusok is így készülnek. Buktató: a guardban csak korlátozott BIF-ek hívhatók, és a pontosvessző/vessző/pont szintaxis (klóz/kifejezés/függvény vége) kezdőknél gyakori hibaforrás.

```erlang
-module(shapes).
-export([area/1, total_area/1, classify/1, qsort/1, word_count/1]).

%% Több klóz tagged tuple-ökre; a guard kizárja a negatív sugarat
area({circle, R}) when R >= 0 -> math:pi() * R * R;
area({rect, W, H}) when W >= 0, H >= 0 -> W * H;
area({triangle, A, B, C}) ->
    S = (A + B + C) / 2,                       % Hérón-képlet
    math:sqrt(S * (S - A) * (S - B) * (S - C)).

%% List comprehension: map + filter egy kifejezésben
total_area(Shapes) -> lists:sum([area(S) || S <- Shapes]).

%% case guardokkal
classify(Shape) ->
    case area(Shape) of
        A when A > 100 -> large;
        A when A > 10 -> medium;
        _ -> small
    end.

%% Quicksort mintaillesztéssel és comprehensionnel
qsort([]) -> [];
qsort([Pivot | Rest]) ->
    qsort([X || X <- Rest, X < Pivot]) ++ [Pivot] ++ qsort([X || X <- Rest, X >= Pivot]).

%% Farokrekurzió akkumulátorral: szógyakoriság map-ben
word_count(Text) ->
    Words = string:lexemes(string:lowercase(Text), " ,.!?\n"),
    count(Words, #{}).

count([], Acc) -> Acc;
count([W | Ws], Acc) ->
    count(Ws, maps:update_with(W, fun(N) -> N + 1 end, 1, Acc)).

%% Shellben:
%% 1> c(shapes).
%% 2> shapes:total_area([{circle, 1}, {rect, 2, 3}]).   %% 9.14...
%% 3> shapes:classify({rect, 20, 10}).                  %% large
%% 4> shapes:word_count("Az alma, az alma!").            %% #{"alma" => 2,"az" => 2}
```

## Rekordok és map-ek
<!-- q: Mikor használjak rekordot és mikor map-et Erlangban? -->
<!-- tags: records, maps, data structures, map pattern, record syntax -->

A rekord fordítási idejű szintaktikai cukor egy tuple fölött (`#item{}` valójában `{item, Sku, Name, ...}`): gyors, a mezőnevek fordításkor ellenőrződnek, de a definíciót (gyakran `.hrl` fájlban) minden használó modulnak ismernie kell, és futásidőben nincsenek mezőnevek. A map (`#{kulcs => érték}`) dinamikus kulcs-érték szerkezet, mintában illeszthető (`#{Sku := Item}`), a `:=` csak létező kulcsot frissít (különben hibát dob), a `=>` beszúr vagy felülír. Ökölszabály: modulon belüli, fix szerkezetű állapothoz rekord, modulhatáron átmenő vagy dinamikus adathoz map. Buktató: a rekord-definíció megváltozása után minden használó modult újra kell fordítani, hot code upgrade-nél pedig a régi tuple-alakot át kell alakítani.

```erlang
-module(inventory).
-export([new/0, add/5, remove/3, report/1]).

%% Rekord típusannotációkkal és alapértékkel
-record(item, {sku :: binary(), name :: binary(), price :: number(), qty = 0 :: non_neg_integer()}).

new() -> #{}.

%% Map-minta kötött kulccsal: ha már van ilyen cikkszám, a mennyiséget növeljük
add(Inv, Sku, Name, Price, Qty) when Qty > 0 ->
    case Inv of
        #{Sku := #item{qty = Old} = It} ->
            Inv#{Sku := It#item{qty = Old + Qty}};           % := csak létező kulcsot frissít
        #{} ->
            Inv#{Sku => #item{sku = Sku, name = Name, price = Price, qty = Qty}}
    end.

remove(Inv, Sku, Qty) ->
    case maps:find(Sku, Inv) of
        error -> {error, {unknown_sku, Sku}};
        {ok, #item{qty = Have}} when Have < Qty -> {error, {insufficient, Have}};
        {ok, #item{qty = Qty}} -> {ok, maps:remove(Sku, Inv)};          % pont elfogyott
        {ok, #item{qty = Have} = It} -> {ok, Inv#{Sku := It#item{qty = Have - Qty}}}
    end.

%% Riport: ár szerint csökkenő sorrend, készletérték összesítve
report(Inv) ->
    Items = lists:sort(fun(A, B) -> A#item.price >= B#item.price end, maps:values(Inv)),
    Lines = [io_lib:format("~ts ~-12ts ~6.2f x ~b~n", [S, N, float(P), Q])
             || #item{sku = S, name = N, price = P, qty = Q} <- Items],
    Total = lists:sum([P * Q || #item{price = P, qty = Q} <- Items]),
    io:format("~ts összérték: ~.2f~n", [Lines, float(Total)]).

%% 1> I0 = inventory:new().
%% 2> I1 = inventory:add(I0, <<"A-1">>, <<"toll">>, 250, 10).
%% 3> I2 = inventory:add(I1, <<"B-7">>, <<"füzet">>, 890, 3).
%% 4> {ok, I3} = inventory:remove(I2, <<"A-1">>, 4).
%% 5> inventory:remove(I3, <<"B-7">>, 9).   %% {error,{insufficient,3}}
%% 6> inventory:report(I3).
```

## Hibakezelés: error, throw, exit és try
<!-- q: Hogyan kezeljem a hibákat Erlangban try/catch-csel és mit jelent a let it crash? -->
<!-- tags: error handling, try catch, throw, exit, error, stacktrace, let it crash -->

Erlangban háromféle kivételosztály van: `error` (futásidejű hiba, pl. `badarg`, `badmatch`, vagy `erlang:error/1`), `throw` (nem lokális visszatérésre, a hívó elkapja) és `exit` (a folyamat leállítása, link-eken terjed). A `try Expr of Minták catch Osztály:Ok:Stack -> ... after ... end` szerkezet a sikeres eredményt és a kivételt külön ágakban illeszti, az `after` mindig lefut. Az idiomatikus API `{ok, V}`/`{error, Ok}` tuple-t ad várható hibákra, a váratlanokat pedig hagyja összeomlani („let it crash”) — a supervisor újraindítja a folyamatot, ezért nem kell minden sort védeni. Buktató: a régi `catch Expr` forma elnyeli és összemossa a hibákat, és a mindent elkapó `_:_` ág elrejti a programhibákat.

```erlang
-module(safe).
-export([parse_port/1, run/1, find_first/2, demo/0]).

%% try ... of: a sikeres ágat is mintával illesztjük
parse_port(Bin) when is_binary(Bin) ->
    try binary_to_integer(Bin) of
        P when P > 0, P < 65536 -> {ok, P};
        P -> {error, {out_of_range, P}}
    catch
        error:badarg -> {error, not_a_number}
    end.

%% Mindhárom kivételosztály kezelése, stacktrace-szel
run(F) ->
    try F() of
        Result -> {ok, Result}
    catch
        throw:Reason -> {thrown, Reason};
        error:Reason:Stack ->
            [{M, Fn, Arity, _Loc} | _] = Stack,          % a hiba helye
            {error, Reason, {M, Fn, Arity}};
        exit:Reason -> {exited, Reason}
    after
        io:format("after: mindig lefut~n")
    end.

%% throw: mély rekurzióból korai kilépés (keresés)
find_first(Pred, Tree) ->
    try walk(Pred, Tree), not_found
    catch throw:{found, X} -> {found, X}
    end.

walk(_Pred, leaf) -> ok;
walk(Pred, {node, L, V, R}) ->
    walk(Pred, L),
    case Pred(V) of true -> throw({found, V}); false -> ok end,
    walk(Pred, R).

demo() ->
    Tree = {node, {node, leaf, 3, leaf}, 8, {node, leaf, 12, leaf}},
    [parse_port(<<"8080">>), parse_port(<<"abc">>), parse_port(<<"70000">>),
     run(fun() -> throw(not_found) end),
     run(fun() -> list_to_integer("x") end),           % error:badarg
     run(fun() -> exit(shutdown) end),
     find_first(fun(X) -> X > 5 end, Tree)].            % {found, 8}
```

## Folyamatok és üzenetküldés (aktor modell)
<!-- q: Hogyan működik az aktor modell Erlangban: spawn, üzenetküldés és receive? -->
<!-- tags: actor model, processes, spawn, message passing, receive, mailbox, selective receive -->

Az Erlang aktor modelljében minden folyamat egy izolált aktor: saját állapota csak a rekurzív ciklus paraméterében él, és kizárólag aszinkron üzenetekkel (`Pid ! Msg`) kommunikál. A `receive` a postafiókból az első illeszkedő üzenetet veszi ki (szelektív fogadás), a többit sorrendben megtartja; az `after` időkorlátot ad. Szinkron kérés-válaszhoz egyedi `make_ref()` referenciát küldünk, és csak az erre illeszkedő választ fogadjuk, így késve érkező régi válaszok nem keverednek össze. Buktató: a soha nem illeszkedő üzenetek felhalmozódnak a postafiókban (memória, lassuló receive) — ezért van egy mindent elkapó ág, éles kódban pedig gen_server.

```erlang
-module(kv).
-export([start/0, store/3, fetch/2, stop/1, demo/0]).

%% Folyamat indítása: az állapot a loop paramétere
start() -> spawn(fun() -> loop(#{}) end).

%% Aszinkron: azonnal visszatér
store(Pid, K, V) -> Pid ! {store, K, V}, ok.

%% Szinkron: egyedi ref-fel párosítjuk a választ, időkorláttal
fetch(Pid, K) ->
    Ref = make_ref(),
    Pid ! {fetch, self(), Ref, K},
    receive
        {Ref, Reply} -> Reply
    after 1000 -> {error, timeout}
    end.

stop(Pid) -> Pid ! stop, ok.

loop(State) ->
    receive
        {store, K, V} ->
            loop(State#{K => V});                       % farokhívás: konstans stack
        {fetch, From, Ref, K} ->
            From ! {Ref, maps:find(K, State)},
            loop(State);
        stop ->
            ok;                                         % nincs rekurzió: a folyamat véget ér
        Other ->
            %% Ismeretlen üzenet: naplózzuk és eldobjuk, hogy ne tömje a postafiókot
            io:format("ismeretlen üzenet: ~p~n", [Other]),
            loop(State)
    end.

demo() ->
    Pid = start(),
    [store(Pid, N, N * N) || N <- lists:seq(1, 5)],
    {ok, 16} = fetch(Pid, 4),
    error = fetch(Pid, 99),
    Pid ! {valami, furcsa},
    %% Párhuzamos kliensek: mindegyik a saját ref-jére vár
    Parent = self(),
    [spawn(fun() -> Parent ! {client, N, fetch(Pid, N)} end) || N <- lists:seq(1, 3)],
    Results = [receive {client, N, R} -> {N, R} end || N <- lists:seq(1, 3)],
    stop(Pid),
    Results.                                            % [{1,{ok,1}},{2,{ok,4}},{3,{ok,9}}]
```

## Linkek, monitorok és trap_exit
<!-- q: Mi a különbség a link és a monitor között Erlangban, és mire jó a trap_exit? -->
<!-- tags: links, monitors, trap_exit, exit signals, fault tolerance, spawn_link, spawn_monitor -->

A *link* kétirányú kapcsolat két folyamat között: ha az egyik abnormálisan leáll, a kilépési jel a másikat is megöli — így az összetartozó folyamatok együtt halnak meg, és nem marad félkész állapot. Ha egy folyamat `process_flag(trap_exit, true)`-t állít, a jelek helyett `{'EXIT', Pid, Ok}` üzenetet kap; a supervisorok pontosan így működnek. A *monitor* egyirányú és halmozható: a megfigyelő `{'DOWN', Ref, process, Pid, Ok}` üzenetet kap, de ő maga nem hal meg — kliens-szerver figyeléshez ez a jó választás. Buktató: a `spawn` + `link` két lépésben versenyhelyzetes (a folyamat közben meghalhat) — használd a `spawn_link`/`spawn_monitor` atomikus változatot, és ne kapcsold be ok nélkül a trap_exit-et.

```erlang
-module(watch).
-export([demo/0, keep_alive/2]).

demo() ->
    process_flag(trap_exit, true),                     % a jelek üzenetként érkeznek

    %% Link: a worker hibás kilépése EXIT üzenetként jön (trap_exit nélkül minket is megölne)
    W = spawn_link(fun() -> receive crash -> exit(boom) end end),
    W ! crash,
    receive {'EXIT', W, R1} -> io:format("link: ~p kilépett: ~p~n", [W, R1]) end,

    %% Monitor: egyirányú, csak értesítés; atomikusan indítva
    {P, Ref} = spawn_monitor(fun() -> timer:sleep(50), exit(done) end),
    receive {'DOWN', Ref, process, P, R2} -> io:format("monitor: ~p~n", [R2]) end,

    %% Már halott folyamat monitorozása azonnal noproc okot ad
    Dead = spawn(fun() -> ok end),
    timer:sleep(10),
    Ref2 = monitor(process, Dead),
    receive {'DOWN', Ref2, process, Dead, R3} -> io:format("halott: ~p~n", [R3]) end,
    ok.

%% Mini-supervisor: legfeljebb 3-szor újraindítja a nevesített workert
keep_alive(Name, Fun) ->
    spawn(fun() ->
                  process_flag(trap_exit, true),
                  restart_loop(Name, Fun, 0)
          end).

restart_loop(Name, Fun, N) when N < 3 ->
    Pid = spawn_link(Fun),
    register(Name, Pid),
    receive
        {'EXIT', Pid, normal} ->
            io:format("~p rendben befejeződött~n", [Name]);
        {'EXIT', Pid, Reason} ->
            io:format("~p összeomlott (~p), újraindítás #~b~n", [Name, Reason, N + 1]),
            restart_loop(Name, Fun, N + 1)
    end;
restart_loop(Name, _Fun, _N) ->
    io:format("~p: túl sok újraindítás, feladom~n", [Name]).

%% 1> watch:keep_alive(flaky, fun() -> timer:sleep(100), exit(random_failure) end).
```

## gen_server: OTP szerverfolyamat
<!-- q: Hogyan írjak gen_server-t Erlangban (handle_call, handle_cast, handle_info)? -->
<!-- tags: gen_server, otp behaviour, handle_call, handle_cast, handle_info, token bucket, rate limiting -->

A `gen_server` OTP-behaviour levezeti a szerver-folyamatok közös részét: a receive-ciklust, a szinkron hívást időkorláttal és hibafigyeléssel (`gen_server:call`), az aszinkron üzenetet (`cast`), a supervisorral való együttműködést, a hot code upgrade-et és a debug/trace támogatást. A modul a callbackeket implementálja: `init/1` (kezdőállapot), `handle_call/3` (`{reply, Válasz, Állapot}`), `handle_cast/2`, `handle_info/2` (minden más üzenet, pl. időzítő). A példa token-bucket rate limitert valósít meg: kulcsonként vödör, amely idővel újratöltődik. Buktató: a gen_server sorosít — a lassú callback minden kliens hívását blokkolja, az alapértelmezett 5 mp-es `call` timeout után a hívó összeomlik.

```erlang
-module(bucket).
-behaviour(gen_server).
-export([start_link/2, take/1]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2]).

-record(st, {capacity :: pos_integer(), rate :: number(), buckets = #{} :: map()}).

-define(CLEANUP_MS, 60000).

%% ---- Kliens API ----
start_link(Capacity, RatePerSec) ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, {Capacity, RatePerSec}, []).

%% ok | {error, rate_limited}
take(Key) -> gen_server:call(?MODULE, {take, Key}).

%% ---- Callbackek ----
init({Cap, Rate}) ->
    erlang:send_after(?CLEANUP_MS, self(), cleanup),
    {ok, #st{capacity = Cap, rate = Rate}}.

handle_call({take, Key}, _From, #st{capacity = Cap, rate = Rate, buckets = B} = St) ->
    Now = erlang:monotonic_time(millisecond),
    {Tokens0, Last} = maps:get(Key, B, {Cap, Now}),          % új kulcs: teli vödör
    Tokens = min(Cap, Tokens0 + (Now - Last) * Rate / 1000), % eltelt idő arányában tölt
    case Tokens >= 1 of
        true -> {reply, ok, St#st{buckets = B#{Key => {Tokens - 1, Now}}}};
        false -> {reply, {error, rate_limited}, St#st{buckets = B#{Key => {Tokens, Now}}}}
    end;
handle_call(_Unknown, _From, St) ->
    {reply, {error, unknown_call}, St}.

handle_cast(_Msg, St) -> {noreply, St}.

%% Időzített takarítás: a (mostanra) teli vödrök eldobhatók, újra teliként jönnének létre
handle_info(cleanup, #st{capacity = Cap, rate = Rate, buckets = B} = St) ->
    Now = erlang:monotonic_time(millisecond),
    NotFull = fun(_K, {T, L}) -> T + (Now - L) * Rate / 1000 < Cap end,
    erlang:send_after(?CLEANUP_MS, self(), cleanup),
    {noreply, St#st{buckets = maps:filter(NotFull, B)}};
handle_info(_Other, St) ->
    {noreply, St}.

%% 1> bucket:start_link(3, 1).                           %% 3 token, 1 token/mp
%% 2> [bucket:take(<<"ip:10.0.0.1">>) || _ <- lists:seq(1, 5)].
%%    [ok,ok,ok,{error,rate_limited},{error,rate_limited}]
```

## Supervisor és felügyeleti fa
<!-- q: Hogyan írjak supervisort Erlangban és hogyan épül fel egy felügyeleti fa? -->
<!-- tags: supervisor, supervision tree, child spec, one_for_one, simple_one_for_one, intensity, otp -->

A `supervisor` behaviour `init/1` callbackje adja vissza a felügyeleti szabályokat (`strategy`, `intensity`, `period`) és a gyermekek specifikációit (child spec map: `id`, `start` MFA, `restart`, `shutdown`, `type`). Stratégiák: `one_for_one` (csak a hibás indul újra), `one_for_all`, `rest_for_one`, illetve `simple_one_for_one` dinamikusan, azonos sablonból indított sok gyermekhez (pl. kapcsolatonként egy). Ha `period` másodperc alatt `intensity`-nél több újraindítás kell, a supervisor feladja és leáll, a hiba pedig a fában feljebb kerül — így eszkalálódik a helyreállítás. Buktató: a `restart => temporary` gyermeket soha nem indítja újra, a `transient` csak abnormális kilépés után, és a `shutdown` időkorlát után a gyermeket brutálisan (`kill`) leállítja.

```erlang
%% ---- shop_sup.erl: gyökér supervisor ----
-module(shop_sup).
-behaviour(supervisor).
-export([start_link/0, init/1]).

start_link() -> supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    %% 5 másodperc alatt legfeljebb 3 újraindítás, különben a supervisor is leáll
    SupFlags = #{strategy => one_for_one, intensity => 3, period => 5},
    Children = [
        #{id => bucket,
          start => {bucket, start_link, [10, 5]},     % {Modul, Függvény, Argumentumok}
          restart => permanent,                      % mindig újraindul
          shutdown => 5000,                          % ennyi idő a terminate-re
          type => worker,
          modules => [bucket]},
        #{id => job_sup,
          start => {job_sup, start_link, []},
          restart => permanent,
          type => supervisor}                        % al-supervisor: fa szerkezet
    ],
    {ok, {SupFlags, Children}}.

%% ---- job_sup.erl: dinamikus gyerekek azonos sablonból ----
-module(job_sup).
-behaviour(supervisor).
-export([start_link/0, start_job/1, init/1]).

start_link() -> supervisor:start_link({local, ?MODULE}, ?MODULE, []).

%% A [Args] lista hozzáfűződik a sablon start argumentumaihoz
start_job(Args) -> supervisor:start_child(?MODULE, [Args]).

init([]) ->
    {ok, {#{strategy => simple_one_for_one, intensity => 10, period => 1},
          [#{id => job,
             start => {job_worker, start_link, []},
             restart => transient,                    % csak hiba után indul újra
             shutdown => 2000}]}}.

%% 1> shop_sup:start_link().
%% 2> supervisor:which_children(shop_sup).
%% 3> job_sup:start_job(#{url => "https://example.com/feed"}).
%% 4> supervisor:count_children(job_sup).
```

## gen_statem: állapotgépek
<!-- q: Hogyan modellezzek állapotgépet Erlangban gen_statem-mel? -->
<!-- tags: gen_statem, state machine, state_functions, state_enter, state_timeout, otp -->

A `gen_statem` OTP-behaviour véges állapotgépekhez való (protokollok, eszközvezérlés, rendelési folyamat): az állapot neve külön van választva az állapotadattól, és `state_functions` módban minden állapot egy saját függvény, amely az eseménytípus (`cast`, `{call, From}`, `info`, `state_timeout`, `enter`) szerint illeszt. A `state_enter` belépési eseményt ad minden állapotváltáskor (pl. időzítő indítása), a `state_timeout` automatikusan törlődik állapotváltáskor, így elmarad a kézi időzítő-takarítás. Ez sokkal kevesebb hibát enged, mint egy gen_server-be kézzel kódolt állapotgép. Buktató: a nem kezelt eseménytípus kivételt okoz (a folyamat összeomlik), ezért minden állapotban gondold végig a `call`-okat; az `enter` callbackben nem lehet állapotot váltani.

```erlang
-module(door).
-behaviour(gen_statem).
-export([start_link/1, button/1, status/0]).
-export([init/1, callback_mode/0, locked/3, open/3]).

%% Kódzáras ajtó: a helyes számsor kinyitja, 3 mp múlva magától bezár
start_link(Code) -> gen_statem:start_link({local, ?MODULE}, ?MODULE, Code, []).
button(Digit) -> gen_statem:cast(?MODULE, {button, Digit}).
status() -> gen_statem:call(?MODULE, status).

callback_mode() -> [state_functions, state_enter].

init(Code) -> {ok, locked, #{code => Code, buttons => []}}.

%% ---- locked állapot ----
locked(enter, _OldState, Data) ->
    {keep_state, Data#{buttons := []}};                 % belépéskor töröljük a bevitelt
locked(cast, {button, D}, #{code := Code, buttons := Bs} = Data) ->
    New = Bs ++ [D],
    if
        New =:= Code ->
            {next_state, open, Data};
        length(New) >= length(Code) ->
            {keep_state, Data#{buttons := []}};          % rossz kód: újrakezdés
        true ->
            %% 5 mp tétlenség után a félig beírt kód törlődik
            {keep_state, Data#{buttons := New}, [{state_timeout, 5000, reset}]}
    end;
locked(state_timeout, reset, Data) ->
    {keep_state, Data#{buttons := []}};
locked({call, From}, status, _Data) ->
    {keep_state_and_data, [{reply, From, locked}]}.

%% ---- open állapot ----
open(enter, _OldState, _Data) ->
    io:format("ajtó nyitva~n"),
    {keep_state_and_data, [{state_timeout, 3000, lock}]};  % automatikus zárás
open(state_timeout, lock, Data) ->
    io:format("ajtó újra zárva~n"),
    {next_state, locked, Data};
open(cast, {button, _}, _Data) ->
    keep_state_and_data;                                  % nyitva: gombnyomás figyelmen kívül
open({call, From}, status, _Data) ->
    {keep_state_and_data, [{reply, From, open}]}.

%% 1> door:start_link([1, 2, 3]).
%% 2> door:button(1), door:button(2), door:button(3).
%% 3> door:status().                  %% open, majd 3 mp múlva locked
```

## Hot code swapping: kódcsere futás közben
<!-- q: Hogyan cserélhető le a kód futás közben Erlangban (hot code swapping)? -->
<!-- tags: hot code swapping, code upgrade, code_change, module versions, sys, release upgrade -->

A BEAM egy modulnak egyszerre két verzióját tartja a memóriában: a *jelenlegit* és a *régit*. Új verzió betöltésekor a futó folyamatok a régi kódban maradnak, amíg nem hajtanak végre *teljesen minősített* (`?MODULE:loop(State)`) hívást — ekkor átlépnek az újra; a helyi (`loop(State)`) hívás a régi verzióban marad. Egy harmadik verzió betöltésekor a régi kódot még futtató folyamatok meghalnak, ezért a `code:soft_purge` előbb ellenőrzi ezt. OTP-folyamatoknál a `sys:suspend` → kódbetöltés → `sys:change_code` (ami a `code_change/3` callbacket hívja az állapot migrálására) → `sys:resume` sorrend a biztonságos, release-szinten pedig az `.appup`/`relup` fájlok automatizálják. Buktató: az állapot szerkezetének változását mindig migrálni kell, különben az új kód régi alakú állapotot kap.

```erlang
-module(hot).
-export([start/0, loop/1]).            %% a loop-ot exportálni kell a ?MODULE:loop híváshoz
-behaviour(gen_server).
-export([init/1, handle_call/3, handle_cast/2, code_change/3]).

%% ---- 1) Nyers folyamat: a ?MODULE:loop hívás vált át az új verzióra ----
start() -> spawn(fun() -> loop(#{count => 0}) end).

loop(#{count := C} = State) ->
    receive
        {incr, N} ->
            ?MODULE:loop(State#{count := C + N});    % külső hívás: mindig a legújabb kód
        {get, From} ->
            From ! {count, C},
            ?MODULE:loop(State)
    end.

%% ---- 2) gen_server állapot-migrációval ----
%% Régi verzió állapota: {state, Count}; az új verzióé: #{count, history}
init(_) -> {ok, #{count => 0, history => []}}.

handle_call(get, _From, #{count := C} = S) -> {reply, C, S}.

handle_cast({incr, N}, #{count := C, history := H} = S) ->
    {noreply, S#{count := C + N, history := lists:sublist([N | H], 10)}}.

%% A sys:change_code hívja: a régi alakú állapotot átalakítjuk
code_change(_OldVsn, {state, Count}, _Extra) ->
    {ok, #{count => Count, history => []}};
code_change(_OldVsn, State, _Extra) ->
    {ok, State}.

%% Kódcsere a shellben (nyers folyamatnál):
%% 1> c(hot), P = hot:start(), P ! {incr, 5}.
%%    ... a forrás módosítása (pl. új üzenettípus) ...
%% 2> c(hot).                  %% új verzió betöltve; P a következő üzenetnél átvált
%% 3> code:soft_purge(hot).    %% true, ha már senki sem futtatja a régi kódot
%%
%% gen_server esetén:
%% sys:suspend(Pid), code:load_file(hot), sys:change_code(Pid, hot, "1", []), sys:resume(Pid).
```

## Elosztott Erlang: node-ok és távoli folyamatok
<!-- q: Hogyan kommunikálnak az Erlang node-ok egymással egy elosztott klaszterben? -->
<!-- tags: distribution, nodes, cluster, erpc, global, net_kernel, cookie, location transparency -->

Az Erlang node-ok (`erl -sname a`) azonos *cookie* esetén teljes hálót alkotnak, és a folyamatok helyfüggetlenek: egy távoli Pid-nek ugyanúgy `!`-lel küldünk üzenetet, link és monitor is működik node-ok között. Távoli hívásra az `erpc:call/5` (időkorláttal), folyamatindításra a `spawn(Node, Fun)` való, a `global` modul klaszterszintű neveket regisztrál, a `net_kernel:monitor_nodes/1` pedig `nodeup`/`nodedown` üzeneteket küld. Buktatók: a beépített disztribúció megbízható, zárt hálózatra készült (a cookie nem igazi hitelesítés — használj TLS-t), a hálózati partíciót (split brain) neked kell kezelned, és távoli fun-hoz mindkét node-on ugyanannak a modulverziónak kell betöltve lennie.

```erlang
-module(dist).
-export([connect/1, remote_sum/2, remote_echo/1, start_global/0, ask_global/0, watch_nodes/0]).

%% Indítás két terminálban (a cookie csak példa):
%%   erl -sname a -setcookie demo_cookie
%%   erl -sname b -setcookie demo_cookie

%% Kapcsolódás: pong = sikeres, pang = sikertelen
connect(Nodes) -> [{N, net_adm:ping(N)} || N <- Nodes].

%% Távoli függvényhívás időkorláttal; hibánál kivétel (erpc)
remote_sum(Node, List) ->
    try erpc:call(Node, lists, sum, [List], 5000)
    catch
        error:{erpc, Reason} -> {error, Reason}
    end.

%% Folyamat indítása egy másik node-on; az üzenetküldés helyfüggetlen
remote_echo(Node) ->
    Self = self(),
    Pid = spawn(Node, fun() ->
                              receive {From, Msg} -> From ! {self(), {echo, node(), Msg}} end
                      end),
    Pid ! {Self, hello},
    receive
        {Pid, Reply} -> Reply
    after 2000 -> {error, timeout}
    end.

%% Klaszterszintű név: bármely node-ról elérhető
start_global() ->
    Pid = spawn(fun global_loop/0),
    yes = global:register_name(config_server, Pid),
    Pid.

global_loop() ->
    receive
        {get, From} -> From ! {config, node(), #{env => prod}}, global_loop()
    end.

ask_global() ->
    global:send(config_server, {get, self()}),
    receive {config, Node, Cfg} -> {Node, Cfg} after 2000 -> timeout end.

%% Node-ok figyelése: nodeup/nodedown üzenetek
watch_nodes() ->
    spawn(fun() ->
                  ok = net_kernel:monitor_nodes(true),
                  Loop = fun Loop() ->
                                 receive
                                     {nodeup, N} -> io:format("csatlakozott: ~p~n", [N]), Loop();
                                     {nodedown, N} -> io:format("kiesett: ~p~n", [N]), Loop()
                                 end
                         end,
                  Loop()
          end).
```

## Bináris minták és a bit szintaxis
<!-- q: Hogyan dolgozzam fel a bináris protokollokat Erlang bit szintaxissal? -->
<!-- tags: binary, bit syntax, binary pattern matching, protocol parsing, tlv, ipv4, binary comprehension -->

Az Erlang bit szintaxisa (`<<Mező:Méret/Típus>>`) bitpontosan bont és épít bináris adatot: egy IP-fejléc vagy egy saját TLV-protokoll egyetlen mintával szétszedhető, a korábban illesztett mező (pl. hossz) pedig a későbbi mezők méreteként használható. A `binary` típusú szegmens másolás nélkül hivatkozik az eredeti adatra (sub-binary), a binary comprehension (`<< <<...>> || ... >>`) hatékonyan épít kimenetet. Ezért kiváló hálózati protokollokhoz, fájlformátumokhoz, telekom-kódolásokhoz. Buktató: egy kis sub-binary életben tartja a teljes, akár nagy eredeti binárist (memória) — hosszú távú tároláshoz `binary:copy/1`; az alapértelmezett bájtsorrend big-endian (`/little` módosító kell a little-endianhez).

```erlang
-module(packet).
-export([parse_ipv4/1, encode_tlv/1, decode_tlv/1, demo/0]).

%% IPv4 fejléc bontása egyetlen mintával; az IHL határozza meg az opciók hosszát
parse_ipv4(<<4:4, IHL:4, _DSCP:6, _ECN:2, TotalLen:16, _Id:16,
             _Flags:3, _FragOff:13, TTL:8, Proto:8, _Checksum:16,
             Src:4/binary, Dst:4/binary, Rest/binary>>) when IHL >= 5 ->
    OptsLen = (IHL - 5) * 4,
    <<_Opts:OptsLen/binary, Payload/binary>> = Rest,   % korábbi mező mint méret
    {ok, #{total_len => TotalLen, ttl => TTL, proto => proto(Proto),
           src => ip(Src), dst => ip(Dst), payload => Payload}};
parse_ipv4(_) ->
    {error, not_ipv4}.

proto(6) -> tcp;
proto(17) -> udp;
proto(N) -> {other, N}.

ip(<<A, B, C, D>>) -> {A, B, C, D}.

%% TLV (típus 8 bit, hossz 16 bit, érték): binary comprehension-nel kódolva
encode_tlv(Fields) ->
    << <<T:8, (byte_size(V)):16, V/binary>> || {T, V} <- Fields >>.

%% Dekódolás: a Len mező az érték méretét adja ugyanabban a mintában
decode_tlv(<<>>) -> [];
decode_tlv(<<T:8, Len:16, V:Len/binary, Rest/binary>>) -> [{T, V} | decode_tlv(Rest)];
decode_tlv(_Truncated) -> erlang:error(truncated_tlv).

demo() ->
    Payload = <<"hello">>,
    Header = <<4:4, 5:4, 0:6, 0:2, (20 + byte_size(Payload)):16, 1:16,
               0:3, 0:13, 64:8, 17:8, 0:16, 192, 168, 0, 1, 10, 0, 0, 7>>,
    {ok, Parsed} = parse_ipv4(<<Header/binary, Payload/binary>>),
    Tlv = encode_tlv([{1, <<"user">>}, {2, <<42:32>>}]),
    [{1, <<"user">>}, {2, <<42:32>>}] = decode_tlv(Tlv),
    {Parsed, Tlv}.
```

## OTP alkalmazás és release rebar3-mal
<!-- q: Hogyan épül fel egy OTP alkalmazás és hogyan készítsek belőle release-t rebar3-mal? -->
<!-- tags: otp application, rebar3, app.src, release, relx, application behaviour, sys.config -->

Az OTP *alkalmazás* egy önállóan indítható/leállítható komponens: az `.app.src` leírja a nevét, verzióját, függőségeit (`applications`) és a callback modult (`mod`), az `application` behaviour `start/2` függvénye pedig a gyökér supervisort indítja. A rebar3 a szabványos build-eszköz: kezeli a függőségeket (Hex), fordít, tesztel (`rebar3 eunit`, `ct`), Dialyzerrel típusellenőriz, és a relx segítségével *release*-t készít, amely tartalmazza a BEAM futtatókörnyezetet, az összes alkalmazást és az indítószkriptet — a célgépen Erlang telepítése nélkül futtatható. Buktatók: a konfigurációt (`sys.config`) induláskor olvasd `application:get_env`-vel; a függőségeknek szerepelniük kell az `applications` listában, különben release-ben nem indulnak el.

```erlang
%% ---- src/shop.app.src ----
{application, shop,
 [{description, "Webshop backend"},
  {vsn, "1.2.0"},
  {registered, [shop_sup, bucket]},
  {mod, {shop_app, []}},                          % callback modul
  {applications, [kernel, stdlib, crypto]},       % ezek induljanak el előbb
  {env, [{rate_capacity, 10}, {rate_per_sec, 5}]} % alapértelmezett konfiguráció
 ]}.

%% ---- src/shop_app.erl ----
-module(shop_app).
-behaviour(application).
-export([start/2, stop/1]).

start(_StartType, _Args) ->
    {ok, Cap} = application:get_env(shop, rate_capacity),
    logger:info("shop indul, kapacitás: ~p", [Cap]),
    shop_sup:start_link().                        % a gyökér supervisor pid-je

stop(_State) -> ok.

%% ---- rebar.config ----
{erl_opts, [debug_info, warnings_as_errors]}.
{deps, [{jsx, "3.1.0"}]}.
{relx, [{release, {shop, "1.2.0"}, [shop, sasl]},
        {sys_config, "config/sys.config"},
        {vm_args, "config/vm.args"},
        {mode, prod}]}.                           % ERTS beágyazva, önálló csomag
{dialyzer, [{warnings, [unmatched_returns, error_handling]}]}.

%% ---- config/sys.config (környezetenkénti felülírás) ----
[{shop, [{rate_capacity, 100}, {rate_per_sec, 50}]},
 {kernel, [{logger_level, info}]}].

%% Parancsok:
%%   rebar3 compile | rebar3 eunit | rebar3 dialyzer
%%   rebar3 release            -> _build/default/rel/shop
%%   _build/default/rel/shop/bin/shop foreground
```
