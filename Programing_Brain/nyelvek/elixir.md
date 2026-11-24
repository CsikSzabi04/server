# Elixir
<!-- tech: elixir -->
<!-- aliases: phoenix, ex, exs, mix, liveview, ecto -->

Az Elixir dinamikusan típusos, funkcionális nyelv, amely az Erlang virtuális gépén (BEAM) fut, így örökli az OTP évtizedes tapasztalatát: millió könnyűsúlyú folyamat, üzenetküldés megosztott memória nélkül, felügyeleti fák és „let it crash” hibatűrés. Az adatok immutábilisak, a kód mintaillesztésre, pipe-okra (`|>`) és makrókra épül; a `mix` a build- és csomagkezelő, a Hex a csomagtár. Fő terepe a valós idejű, sok párhuzamos kapcsolatot kezelő backend (Phoenix, LiveView, chat, IoT, üzenetsorok), adatfeldolgozó pipeline-ok (Broadway) és újabban az ML (Nx). Kevésbé alkalmas CPU-intenzív számításokhoz (ott NIF vagy Rust kell), és ahol erős statikus típusosság a fő szempont (bár a 1.17+ fokozatosan bevezeti a set-theoretic típusellenőrzést).

## Mintaillesztés, guardok és a pipe operátor
<!-- q: Hogyan használjam a mintaillesztést, guardokat és a pipe operátort Elixirben? -->
<!-- tags: pattern matching, guards, pipe operator, pin operator, binary matching, multi-clause -->

Elixirben az `=` nem értékadás, hanem *illesztés*: a bal oldali minta szétbontja a jobb oldali értéket, és ha nem illeszkedik, `MatchError` keletkezik. A függvényeknek több klóza lehet; a futtatókörnyezet felülről lefelé az első illeszkedőt választja (mintával és `when` guarddal), így az elágazások deklaratívak lesznek `if`-láncok helyett. A pin operátor (`^id`) egy meglévő változó értékére illeszt újrakötés helyett, a bináris minták (`<<cat::binary-size(3), ...>>`) protokollok és fix formátumok bontására valók. A pipe (`|>`) az előző eredményt a következő függvény *első* argumentumaként adja át — ezért az Elixir API-k az „alany” paramétert teszik előre. Buktató: guardban csak korlátozott, mellékhatás-mentes függvények hívhatók.

```elixir
defmodule Orders do
  # Több klóz guarddal: az első illeszkedő nyer, a sorrend számít
  def shipping_cost(%{country: "HU", total: total}) when total >= 20_000, do: 0
  def shipping_cost(%{country: "HU"}), do: 1_490
  def shipping_cost(%{country: c}) when c in ["AT", "SK", "RO"], do: 4_990
  def shipping_cost(_order), do: 9_990

  # Bináris minta: "ABC-0042" formátumú cikkszám bontása
  def parse_sku(<<cat::binary-size(3), "-", num::binary-size(4)>>) do
    case Integer.parse(num) do
      {n, ""} -> {:ok, cat, n}
      _ -> {:error, :invalid_sku}
    end
  end

  def parse_sku(_), do: {:error, :invalid_sku}

  # Pin operátor: a meglévő id értékére illesztünk, nem kötjük újra
  def find(orders, id) do
    Enum.find(orders, fn
      %{id: ^id} -> true
      _ -> false
    end)
  end

  # Pipe-lánc: fizetett rendelések országonkénti bevétele szállítással együtt
  def revenue_by_country(orders) do
    orders
    |> Enum.filter(&(&1.status == :paid))
    |> Enum.map(&Map.put(&1, :shipping, shipping_cost(&1)))
    |> Enum.group_by(& &1.country, &(&1.total + &1.shipping))
    |> Map.new(fn {country, amounts} -> {country, Enum.sum(amounts)} end)
  end
end

orders = [
  %{id: 1, country: "HU", total: 25_000, status: :paid},
  %{id: 2, country: "HU", total: 5_000, status: :paid},
  %{id: 3, country: "AT", total: 12_000, status: :pending},
  %{id: 4, country: "DE", total: 30_000, status: :paid}
]

IO.inspect(Orders.revenue_by_country(orders))   # %{"DE" => 39990, "HU" => 31490}
IO.inspect(Orders.parse_sku("KAB-0042"))         # {:ok, "KAB", 42}
IO.inspect(Orders.find(orders, 3).country)       # "AT"

# Destrukturálás: beágyazott minta egy lépésben
%{id: id, country: country} = hd(orders)
IO.puts("#{id} -> #{country}")
```

## Hibakezelés: tagged tuple-ök, with és kivételek
<!-- q: Hogyan kezeljem a hibákat Elixirben with-del, ok/error tuple-ökkel és kivételekkel? -->
<!-- tags: error handling, with, ok error tuples, exceptions, defexception, let it crash -->

Az idiomatikus Elixir a várható hibákat értékként adja vissza: `{:ok, érték}` vagy `{:error, ok}`. A `with` több ilyen lépést fűz össze: amíg a minták illeszkednek, folytatja, az első nem illeszkedő értéknél kilép, és azt az `else` ágban lehet átalakítani — ez kiváltja a mélyen egymásba ágyazott `case`-eket. A felkiáltójeles függvényváltozatok (`File.read!`) kivételt dobnak; ezek ott jók, ahol a hiba programhibát jelent. Az Erlang-filozófia szerint a váratlan hibát nem kell mindenáron elkapni („let it crash”): a folyamat összeomlik, a supervisor tiszta állapotból újraindítja. Buktató: a túl általános `else` (`_ -> ...`) elnyeli a valódi hibákat, a `try/rescue`-t pedig ne használd vezérlésre.

```elixir
defmodule Signup do
  # Saját kivétel: programozói hibákra / érvénytelen állapotra
  defmodule InvalidConfig do
    defexception [:key, message: "érvénytelen konfiguráció"]
  end

  @min_age 16

  def register(params, existing_emails) do
    with {:ok, email} <- fetch(params, "email"),
         :ok <- validate_email(email),
         :ok <- ensure_unique(email, existing_emails),
         {:ok, raw_age} <- fetch(params, "age"),
         {age, ""} <- Integer.parse(raw_age),
         true <- age >= @min_age || {:error, {:too_young, age}} do
      {:ok, %{email: String.downcase(email), age: age}}
    else
      # Az első nem illeszkedő érték ide érkezik: egységes hibaformára hozzuk
      {:error, reason} -> {:error, reason}
      :error -> {:error, :age_not_a_number}
      {_age, _rest} -> {:error, :age_not_a_number}
    end
  end

  defp fetch(params, key) do
    case Map.fetch(params, key) do
      {:ok, v} when v != "" -> {:ok, v}
      _ -> {:error, {:missing, key}}
    end
  end

  defp validate_email(email) do
    if String.match?(email, ~r/^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i),
      do: :ok,
      else: {:error, :invalid_email}
  end

  defp ensure_unique(email, existing) do
    if String.downcase(email) in existing, do: {:error, :taken}, else: :ok
  end

  # Kivétel dobása és elkapása: csak ahol valóban kivételes a helyzet
  def port!(config) do
    case Map.get(config, :port) do
      p when is_integer(p) and p in 1..65_535 -> p
      _ -> raise InvalidConfig, key: :port, message: "a port 1..65535 közötti egész legyen"
    end
  end
end

taken = ["foo@example.com"]
IO.inspect(Signup.register(%{"email" => "Uj@Example.com", "age" => "21"}, taken))
IO.inspect(Signup.register(%{"email" => "foo@example.com", "age" => "21"}, taken))
IO.inspect(Signup.register(%{"email" => "x@y.hu", "age" => "tizenöt"}, taken))
IO.inspect(Signup.register(%{"email" => "x@y.hu", "age" => "12"}, taken))

try do
  Signup.port!(%{port: 70_000})
rescue
  e in Signup.InvalidConfig -> IO.puts("hiba (#{e.key}): #{Exception.message(e)}")
after
  IO.puts("after ág: mindig lefut")
end
```

## Enum vs Stream: mohó és lusta feldolgozás
<!-- q: Mi a különbség az Enum és a Stream között Elixirben, és mikor melyiket használjam? -->
<!-- tags: enum, stream, lazy evaluation, file.stream, stream.resource, pagination, memory -->

Az `Enum` mohó: minden lépés azonnal lefut és teljes köztes listát épít, ami kis és közepes adatnál a leggyorsabb és legolvashatóbb. A `Stream` lusta: a lépések csak recepteket építenek, és az elemek egyenként, a lánc végén egy `Enum` hívás (vagy `Stream.run`) hatására haladnak végig — így óriási fájlok, végtelen sorozatok vagy lapozott API-k konstans memóriával dolgozhatók fel. A `Stream.resource` erőforrás nyitását, lépésenkénti olvasását és garantált lezárását írja le. Buktató: kis listán a `Stream` overheadje miatt lassabb, a stream minden bejáráskor újra lefut (mellékhatásokkal együtt), és a `Enum.to_list` egy végtelen streamen soha nem tér vissza.

```elixir
defmodule LogStats do
  # Nagy naplófájl: soronként, konstans memóriával
  def top_paths(path, n) do
    path
    |> File.stream!()                              # lusta, soronként olvas
    |> Stream.map(&String.trim/1)
    |> Stream.reject(&(&1 == ""))
    |> Stream.map(&String.split(&1, " "))
    |> Stream.filter(&match?([_method, _path, "200" | _], &1))
    |> Enum.frequencies_by(fn [_m, p | _] -> p end) # itt fut ténylegesen a lánc
    |> Enum.sort_by(fn {_p, count} -> count end, :desc)
    |> Enum.take(n)
  end

  # Lapozott API lustán: csak annyi oldalt kér le, amennyi elem kell
  def all_items(fetch_page) do
    Stream.resource(
      fn -> 1 end,                                 # kezdőállapot: oldalszám
      fn
        :done -> {:halt, :done}
        page ->
          case fetch_page.(page) do
            {items, :last} -> {items, :done}
            {items, :more} -> {items, page + 1}
          end
      end,
      fn _ -> :ok end                              # lezárás (pl. kapcsolat bontása)
    )
  end
end

# Szimulált API: 3 oldal, oldalanként 4 elem; kiírja, melyik oldalt kéri
fake_api = fn page ->
  IO.puts("lekérés: #{page}. oldal")
  items = Enum.map(1..4, &((page - 1) * 4 + &1))
  {items, if(page == 3, do: :last, else: :more)}
end

# Csak az első 6 elem kell: a 3. oldalt le sem kéri
LogStats.all_items(fake_api) |> Enum.take(6) |> IO.inspect()

# Végtelen stream: az első 5 olyan négyzetszám, amely 6-ra végződik
Stream.iterate(1, &(&1 + 1))
|> Stream.map(&(&1 * &1))
|> Stream.filter(&(rem(&1, 10) == 6))
|> Enum.take(5)
|> IO.inspect()                                    # [16, 36, 196, 256, 576]

# Ideiglenes naplófájl a top_paths kipróbálásához
tmp = Path.join(System.tmp_dir!(), "access_demo.log")
File.write!(tmp, "GET /a 200\nGET /b 404\nGET /a 200\nPOST /c 200\n\nGET /c 200\n")
IO.inspect(LogStats.top_paths(tmp, 2))             # [{"/a", 2}, {"/c", 2}]
```

## Folyamatok és üzenetküldés
<!-- q: Hogyan működnek a folyamatok és az üzenetküldés Elixirben (spawn, send, receive)? -->
<!-- tags: processes, spawn, send, receive, mailbox, monitor, actor model, concurrency -->

A BEAM folyamatai rendkívül könnyűek (néhány KB, mikroszekundumos indítás), saját heappel és GC-vel rendelkeznek, és kizárólag aszinkron üzenetekkel kommunikálnak — nincs megosztott memória, így nincs adatverseny sem. A `send` a cél folyamat postafiókjába tesz egy üzenetet, a `receive` mintaillesztéssel *szelektíven* veszi ki az első illeszkedőt, `after` ággal időkorláttal. A `make_ref()` egyedi azonosító a válaszok párosítására, a `Process.monitor` pedig `:DOWN` üzenetet küld, ha a megfigyelt folyamat leáll. Buktató: a nem illeszkedő üzenetek a postafiókban maradnak és lassítják a szelektív receive-et (memóriaszivárgás) — éles kódban GenServer-t és Task-ot használj nyers `spawn` helyett.

```elixir
defmodule Counter do
  # Állapottartó folyamat: a ciklus paramétere az állapot (rekurzió = hurok)
  def start(initial), do: spawn(fn -> loop(initial) end)

  defp loop(count) do
    receive do
      {:inc, n} ->
        loop(count + n)

      {:get, caller, ref} ->
        send(caller, {ref, count})                  # válasz a kérdezőnek
        loop(count)

      :stop ->
        :ok                                         # nincs rekurzív hívás: a folyamat kilép
    end
  end

  # Szinkron lekérdezés ref-fel és időkorláttal
  def get(pid, timeout \\ 1_000) do
    ref = make_ref()
    send(pid, {:get, self(), ref})

    receive do
      {^ref, value} -> {:ok, value}                 # csak a MI válaszunkra illeszkedik
    after
      timeout -> {:error, :timeout}
    end
  end
end

defmodule PMap do
  # Párhuzamos map: elemenként egy folyamat, az eredmények sorrendje megmarad
  def pmap(items, fun) do
    parent = self()

    items
    |> Enum.map(fn item ->
      ref = make_ref()
      spawn(fn -> send(parent, {ref, fun.(item)}) end)
      ref
    end)
    |> Enum.map(fn ref ->
      receive do
        {^ref, result} -> result
      after
        5_000 -> exit(:pmap_timeout)
      end
    end)
  end
end

pid = Counter.start(0)
Enum.each(1..1_000, fn _ -> send(pid, {:inc, 1}) end)
IO.inspect(Counter.get(pid))                        # {:ok, 1000}

# Monitor: értesítést kapunk a folyamat leállásáról
ref = Process.monitor(pid)
send(pid, :stop)

receive do
  {:DOWN, ^ref, :process, ^pid, reason} -> IO.puts("a számláló leállt: #{inspect(reason)}")
end

IO.inspect(PMap.pmap(1..5, fn x -> Process.sleep(100); x * x end))   # ~100 ms, nem 500
```

## GenServer: állapottartó szerverfolyamat
<!-- q: Hogyan írjak GenServer-t Elixirben call, cast és handle_info kezeléssel? -->
<!-- tags: genserver, otp, handle_call, handle_cast, handle_info, state, ttl cache -->

A `GenServer` az OTP általános szerver-behaviourje: a receive-ciklust, a szinkron hívást (`call`, időkorláttal, válasszal), az aszinkron üzenetet (`cast`) és a rendszerüzeneteket (supervisor, hot code upgrade, tracing) a könyvtár kezeli, nekünk csak a callbackeket kell megírni. Bevett szerkezet: a modul tetején a *kliens API* (sima függvények, amelyek `GenServer.call/cast`-ot hívnak), alul a *szerver callbackek* (`init`, `handle_call`, `handle_cast`, `handle_info`). Időzített munkához a `Process.send_after` saját magának küld üzenetet, amit a `handle_info` kezel. Buktató: a GenServer sorosít — egy lassú `handle_call` minden hívót blokkol (szűk keresztmetszet), az `init`-ben végzett lassú munka pedig a supervisor indulását is (erre a `handle_continue` való).

```elixir
defmodule TTLCache do
  use GenServer

  # ---- Kliens API: ezt hívják a többi modulból ----
  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts, name: Keyword.get(opts, :name, __MODULE__))
  end

  def put(server, key, value, ttl_ms), do: GenServer.cast(server, {:put, key, value, ttl_ms})
  def get(server, key), do: GenServer.call(server, {:get, key})
  def size(server), do: GenServer.call(server, :size)

  # ---- Szerver callbackek: a GenServer folyamatban futnak ----
  @impl true
  def init(opts) do
    sweep_ms = Keyword.get(opts, :sweep_ms, 1_000)
    schedule_sweep(sweep_ms)
    {:ok, %{data: %{}, sweep_ms: sweep_ms}}
  end

  @impl true
  def handle_cast({:put, key, value, ttl_ms}, state) do
    expires_at = now() + ttl_ms
    {:noreply, %{state | data: Map.put(state.data, key, {value, expires_at})}}
  end

  @impl true
  def handle_call({:get, key}, _from, state) do
    reply =
      case Map.fetch(state.data, key) do
        {:ok, {value, exp}} -> if exp > now(), do: {:ok, value}, else: :error
        :error -> :error
      end

    {:reply, reply, state}
  end

  def handle_call(:size, _from, state), do: {:reply, map_size(state.data), state}

  # Időzített takarítás: a lejárt kulcsok törlése, majd újraütemezés
  @impl true
  def handle_info(:sweep, state) do
    t = now()
    data = Map.reject(state.data, fn {_k, {_v, exp}} -> exp <= t end)
    schedule_sweep(state.sweep_ms)
    {:noreply, %{state | data: data}}
  end

  defp schedule_sweep(ms), do: Process.send_after(self(), :sweep, ms)
  defp now, do: System.monotonic_time(:millisecond)
end

{:ok, _pid} = TTLCache.start_link(name: :cache, sweep_ms: 50)
TTLCache.put(:cache, "session:1", %{user: 7}, 100)
TTLCache.put(:cache, "session:2", %{user: 9}, 10_000)
IO.inspect(TTLCache.get(:cache, "session:1"))       # {:ok, %{user: 7}}
Process.sleep(200)
IO.inspect(TTLCache.get(:cache, "session:1"))       # :error (lejárt)
IO.inspect(TTLCache.size(:cache))                   # 1 — a takarítás törölte
```

## Supervisorok és felügyeleti fák
<!-- q: Hogyan építsek supervision tree-t Elixirben és melyik újraindítási stratégiát válasszam? -->
<!-- tags: supervisor, supervision tree, one_for_one, rest_for_one, restart strategy, application, fault tolerance -->

A supervisor egy folyamat, amelynek egyetlen dolga a gyermekei felügyelete: ha egy gyermek összeomlik, a stratégia szerint újraindítja — `:one_for_one` csak a hibásat, `:one_for_all` mindet, `:rest_for_one` a hibásat és az utána indítottakat (függőségi láncnál). A `max_restarts`/`max_seconds` korlát fölött a supervisor maga is leáll, és a hibát feljebb adja a fában; így a hiba fokozatosan, egyre nagyobb tiszta újraindítással kezelődik. A gyermekeket `child_spec` írja le (a `use GenServer` generálja), ahol a `restart` lehet `:permanent`, `:transient` (csak hibás kilépésnél) vagy `:temporary`. Buktató: az indítási sorrend számít (függőség előbb), és az `init`-ben dobott hiba az egész alkalmazás indulását megakaszthatja.

```elixir
defmodule MyApp.Metrics do
  # transient: csak hibás leállás után indul újra, normál kilépés után nem
  use GenServer, restart: :transient

  def start_link(_), do: GenServer.start_link(__MODULE__, %{}, name: __MODULE__)
  def record(event), do: GenServer.cast(__MODULE__, {:record, event})
  def crash!, do: GenServer.cast(__MODULE__, :crash)
  def counts, do: GenServer.call(__MODULE__, :counts)

  @impl true
  def init(state), do: {:ok, state}

  @impl true
  def handle_cast({:record, e}, s), do: {:noreply, Map.update(s, e, 1, &(&1 + 1))}
  def handle_cast(:crash, _s), do: raise("szándékos hiba")

  @impl true
  def handle_call(:counts, _from, s), do: {:reply, s, s}
end

defmodule MyApp.Application do
  use Application

  @impl true
  def start(_type, _args) do
    children = [
      # Sorrend = indítási sorrend; a függőségek kerülnek előre
      {Registry, keys: :unique, name: MyApp.Registry},
      {Task.Supervisor, name: MyApp.TaskSup},
      {DynamicSupervisor, name: MyApp.WorkerSup, strategy: :one_for_one},
      MyApp.Metrics
    ]

    # Ha 5 mp alatt 3-nál több újraindítás kell, a supervisor is leáll
    Supervisor.start_link(children,
      strategy: :one_for_one,
      max_restarts: 3,
      max_seconds: 5,
      name: MyApp.Supervisor
    )
  end
end

# Kipróbálás (mix projektben az Application automatikusan indul)
{:ok, _sup} = MyApp.Application.start(:normal, [])
MyApp.Metrics.record(:login)
old_pid = Process.whereis(MyApp.Metrics)
MyApp.Metrics.crash!()
Process.sleep(50)
new_pid = Process.whereis(MyApp.Metrics)
IO.puts("újraindítva: #{old_pid != new_pid}")     # true, tiszta (üres) állapottal
IO.inspect(MyApp.Metrics.counts())                # %{} — az állapot elveszett
IO.inspect(Supervisor.count_children(MyApp.Supervisor))
```

## Task és Task.async_stream
<!-- q: Hogyan futtassak párhuzamos feladatokat Elixirben Task-kal és async_stream-mel? -->
<!-- tags: task, async, await, async_stream, max_concurrency, task.supervisor, parallelism -->

A `Task` egyszeri, eredményt visszaadó háttérmunka: a `Task.async` elindítja (a hívóhoz *linkelve*), a `Task.await`/`await_many` időkorláttal bevárja. Sok elem korlátozott párhuzamosságú feldolgozására a `Task.async_stream` való: `max_concurrency`-vel szabályozza a terhelést (pl. külső API rate limit), sorrendtartó, és elemenkénti `timeout`-ot ad, `on_timeout: :kill_task` mellett a lassú elemek `{:exit, :timeout}` eredményt adnak az egész lánc leállítása helyett. Ha a feladat hibája nem döntheti be a hívót (pl. webkérés-kezelő), `Task.Supervisor.async_nolink` kell. Buktató: a `Task.async` linkelt, tehát a task összeomlása a hívót is megöli, és az `await` alapértelmezett 5 mp-es időkorlátja után a hívó kilép.

```elixir
defmodule PriceFetcher do
  # Szimulált külső hívás változó késleltetéssel és alkalmi hibával
  def fetch(symbol) do
    delay = :erlang.phash2(symbol, 300)
    Process.sleep(delay)
    if symbol == "BAD", do: raise("ismeretlen szimbólum"), else: {symbol, delay}
  end

  # Két független lekérés párhuzamosan
  def fetch_pair(a, b) do
    t1 = Task.async(fn -> fetch(a) end)
    t2 = Task.async(fn -> fetch(b) end)
    Task.await_many([t1, t2], 2_000)
  end

  # Sok elem, korlátozott párhuzamosság, elemenkénti időkorlát
  def fetch_all(symbols) do
    symbols
    |> Task.async_stream(&fetch/1,
      max_concurrency: 4,
      timeout: 250,
      on_timeout: :kill_task           # a lassú elem {:exit, :timeout} lesz
    )
    |> Enum.zip(symbols)
    |> Enum.map(fn
      {{:ok, {sym, ms}}, _} -> {sym, {:ok, ms}}
      {{:exit, reason}, sym} -> {sym, {:error, reason}}
    end)
  end

  # Hibatűrő változat: a task összeomlása nem dönti be a hívót
  def fetch_isolated(sup, symbol) do
    task = Task.Supervisor.async_nolink(sup, fn -> fetch(symbol) end)

    case Task.yield(task, 1_000) || Task.shutdown(task) do
      {:ok, result} -> {:ok, result}
      {:exit, reason} -> {:error, {:crashed, Exception.format_exit(reason)}}
      nil -> {:error, :timeout}
    end
  end
end

IO.inspect(PriceFetcher.fetch_pair("AAPL", "MSFT"))
IO.inspect(PriceFetcher.fetch_all(~w(AAPL MSFT GOOG AMZN NVDA TSLA)))

{:ok, sup} = Task.Supervisor.start_link()
IO.inspect(PriceFetcher.fetch_isolated(sup, "AAPL"))
IO.inspect(PriceFetcher.fetch_isolated(sup, "BAD"))   # {:error, {:crashed, ...}}, a hívó él
```

## Agent: egyszerű megosztott állapot
<!-- q: Mikor használjak Agent-et Elixirben és mire figyeljek vele? -->
<!-- tags: agent, state, get_and_update, shared state, genserver alternative -->

Az `Agent` egy minimális GenServer-burok, amely csak egy állapotot tárol, és függvényekkel lehet olvasni (`get`), módosítani (`update`) vagy egy lépésben mindkettőt (`get_and_update`) — kis, egyszerű megosztott állapotra (konfiguráció, számláló, cache) kényelmes. Az átadott függvény az Agent *folyamatában* fut, ezért a módosítás atomikus, nincs versenyhelyzet a „kiolvas, majd visszaír” mintánál. Buktató: ha a függvényben drága számítás fut, az minden más hívót blokkol — a nehéz munkát a kliens oldalon végezd, és csak az eredményt add át; ha az állapothoz logika, időzítés vagy üzenetkezelés kell, válts GenServer-re.

```elixir
defmodule FeatureFlags do
  use Agent

  # A start_link child_spec-ként is használható egy supervisor alatt
  def start_link(initial) do
    Agent.start_link(fn -> Map.new(initial) end, name: __MODULE__)
  end

  def enabled?(flag), do: Agent.get(__MODULE__, &Map.get(&1, flag, false))

  def toggle(flag) do
    # get_and_update: atomikus olvasás + írás; a régi értéket adja vissza
    Agent.get_and_update(__MODULE__, fn flags ->
      old = Map.get(flags, flag, false)
      {old, Map.put(flags, flag, not old)}
    end)
  end

  # ROSSZ: a drága számítás az Agent folyamatában futna, mindenkit blokkolva
  # def rollout(users), do: Agent.update(__MODULE__, fn f -> heavy(users, f) end)

  # JÓ: a nehéz munka a hívónál fut, az Agent csak a kész eredményt kapja
  def enable_for_percentage(flag, users, percent) do
    selected =
      users
      |> Enum.filter(fn u -> :erlang.phash2({flag, u}, 100) < percent end)
      |> MapSet.new()

    Agent.update(__MODULE__, &Map.put(&1, {flag, :users}, selected))
    MapSet.size(selected)
  end

  def enabled_for?(flag, user) do
    Agent.get(__MODULE__, fn flags ->
      flags |> Map.get({flag, :users}, MapSet.new()) |> MapSet.member?(user)
    end)
  end
end

{:ok, _} = FeatureFlags.start_link(dark_mode: true, new_checkout: false)
IO.inspect(FeatureFlags.enabled?(:dark_mode))        # true
IO.inspect(FeatureFlags.toggle(:new_checkout))       # false (a régi érték)
IO.inspect(FeatureFlags.enabled?(:new_checkout))     # true

# Párhuzamos toggle-ök: az atomikusság miatt nincs elveszett frissítés
1..100 |> Enum.map(fn _ -> Task.async(fn -> FeatureFlags.toggle(:beta) end) end) |> Task.await_many()
IO.inspect(FeatureFlags.enabled?(:beta))             # false (páros számú váltás)

n = FeatureFlags.enable_for_percentage(:beta_ui, Enum.to_list(1..1_000), 10)
IO.puts("kiválasztott felhasználók: #{n} (~100)")
```

## DynamicSupervisor és Registry: folyamat entitásonként
<!-- q: Hogyan indítsak dinamikusan folyamatot entitásonként (pl. chatszobánként) DynamicSupervisor-ral és Registry-vel? -->
<!-- tags: dynamicsupervisor, registry, via tuple, process per entity, idle timeout -->

Gyakori BEAM-minta, hogy minden entitás (felhasználói session, chatszoba, játszma, eszköz) saját folyamatot kap: az állapota izolált, a hibája csak azt az egy entitást érinti. A `DynamicSupervisor` futás közben indít és felügyel ilyen gyermekeket, a `Registry` pedig név → pid leképezést ad, így a folyamatot `{:via, Registry, {Reg, kulcs}}` tuple-lel lehet címezni, pid tárolása nélkül (a regisztráció a folyamat halálakor automatikusan törlődik). Az `{:error, {:already_started, pid}}` eredmény teszi az indítást idempotenssé. Buktató: tétlen folyamatokat le kell állítani (pl. GenServer timeout-tal), különben a memória nő; a `Registry` csak egy node-on belül működik — klaszterben `:global`, `Horde` vagy `:pg` kell.

```elixir
defmodule Chat.Room do
  # transient: normál leállás (tétlenség) után nem indul újra
  use GenServer, restart: :transient

  @idle_ms 30_000

  def start_link(name), do: GenServer.start_link(__MODULE__, name, name: via(name))
  defp via(name), do: {:via, Registry, {Chat.Registry, name}}

  def post(name, user, text), do: GenServer.call(via(name), {:post, user, text})
  def history(name), do: GenServer.call(via(name), :history)

  @impl true
  def init(name), do: {:ok, %{name: name, messages: []}, @idle_ms}

  @impl true
  def handle_call({:post, user, text}, _from, state) do
    msg = %{user: user, text: text, at: DateTime.utc_now()}
    # A visszatérési érték végén a timeout: ennyi tétlenség után :timeout üzenet jön
    {:reply, :ok, %{state | messages: [msg | state.messages]}, @idle_ms}
  end

  def handle_call(:history, _from, state) do
    {:reply, Enum.reverse(state.messages), state, @idle_ms}
  end

  @impl true
  def handle_info(:timeout, state), do: {:stop, :normal, state}   # tétlen: leáll
end

defmodule Chat.Rooms do
  # Idempotens indítás: ha már fut, a meglévő pid-et adja
  def ensure_started(name) do
    case DynamicSupervisor.start_child(Chat.RoomSup, {Chat.Room, name}) do
      {:ok, pid} -> {:ok, pid}
      {:error, {:already_started, pid}} -> {:ok, pid}
    end
  end

  def list, do: Registry.select(Chat.Registry, [{{:"$1", :_, :_}, [], [:"$1"]}])
end

# Supervisor-fa: előbb a Registry, aztán a dinamikus supervisor
{:ok, _} =
  Supervisor.start_link(
    [
      {Registry, keys: :unique, name: Chat.Registry},
      {DynamicSupervisor, name: Chat.RoomSup, strategy: :one_for_one}
    ],
    strategy: :one_for_one
  )

{:ok, pid1} = Chat.Rooms.ensure_started("elixir")
{:ok, pid2} = Chat.Rooms.ensure_started("elixir")
IO.puts("ugyanaz a folyamat: #{pid1 == pid2}")
{:ok, _} = Chat.Rooms.ensure_started("haskell")
Chat.Room.post("elixir", "anna", "Sziasztok!")
Chat.Room.post("elixir", "bence", "Hali!")
IO.inspect(Enum.map(Chat.Room.history("elixir"), & &1.text))
IO.inspect(Enum.sort(Chat.Rooms.list()))          # ["elixir", "haskell"]
```

## Protokollok: polimorfizmus adattípus szerint
<!-- q: Hogyan használjam a protokollokat Elixirben típusonkénti polimorfizmusra? -->
<!-- tags: protocols, defprotocol, defimpl, polymorphism, string.chars, fallback_to_any, derive -->

A protokoll az Elixir típus szerinti (adat-alapú) polimorfizmusa: a `defprotocol` deklarálja a függvényeket, a `defimpl ... for:` pedig típusonként (struct, `Map`, `List`, `Integer`, `Any`) megvalósítja őket — akár utólag, a típus forráskódjának módosítása nélkül. Így működik az `Enumerable` (minden `Enum`-függvény), a `String.Chars` (`"#{x}"` interpoláció) és az `Inspect`. A `@fallback_to_any true` és a `@derive` alapértelmezett implementációt ad. Buktató: a protokoll-hívás a dispatch miatt kicsit lassabb (release-ben konszolidálva gyors), és ha egy típushoz nincs implementáció, futásidejű `Protocol.UndefinedError` jön.

```elixir
defprotocol Exportable do
  @doc "Az értéket CSV-sor mezőinek listájává alakítja."
  @fallback_to_any true
  def to_row(value)
end

defmodule User do
  defstruct [:id, :name, :email, password_hash: nil]
end

defmodule Invoice do
  defstruct [:number, :total, :currency, lines: []]
end

# Implementáció struct-onként: a jelszó-hash szándékosan kimarad
defimpl Exportable, for: User do
  def to_row(%User{id: id, name: name, email: email}), do: [id, name, email]
end

defimpl Exportable, for: Invoice do
  def to_row(%Invoice{} = inv), do: [inv.number, inv.total, inv.currency, length(inv.lines)]
end

# Beépített típusra is implementálható
defimpl Exportable, for: Map do
  def to_row(map), do: map |> Enum.sort() |> Enum.map(fn {k, v} -> "#{k}=#{v}" end)
end

# Alapértelmezés minden másra
defimpl Exportable, for: Any do
  def to_row(other), do: [inspect(other)]
end

# String.Chars: így használható a struct "#{...}" interpolációban
defimpl String.Chars, for: Invoice do
  def to_string(inv), do: "Számla #{inv.number} (#{inv.total} #{inv.currency})"
end

defmodule CsvExport do
  # Egyszerűsített CSV: idézőjelek duplázása, mezők idézőjelben
  def export(items) do
    items
    |> Enum.map(&Exportable.to_row/1)
    |> Enum.map(fn row ->
      Enum.map_join(row, ";", fn field ->
        "\"" <> String.replace(to_string(field), "\"", "\"\"") <> "\""
      end)
    end)
    |> Enum.join("\n")
  end
end

items = [
  %User{id: 1, name: "Kiss Anna", email: "anna@example.com", password_hash: "titok"},
  %Invoice{number: "2026/001", total: 12_700, currency: "HUF", lines: [:a, :b]},
  %{sku: "X-1", qty: 3},
  {:unknown, 42}
]

IO.puts(CsvExport.export(items))
IO.puts("#{Enum.at(items, 1)}")                 # Számla 2026/001 (12700 HUF)
```

## Behaviourök: cserélhető implementációk
<!-- q: Hogyan definiáljak behaviour-t Elixirben cserélhető adapterekhez (pl. értesítő, fizetés)? -->
<!-- tags: behaviour, callback, impl, adapter pattern, dependency injection, mox, testing -->

A behaviour egy modul-szintű interfész: a `@callback` deklarációk leírják, milyen függvényeket kell egy implementáló modulnak exportálnia, az `@behaviour` + `@impl true` pedig fordítási időben figyelmeztet a hiányzó vagy elírt callbackre. Míg a protokoll *adattípus* szerint választ implementációt, a behaviour *modult* cserél — tipikusan adapterekhez (e-mail/SMS küldő, fizetési szolgáltató, tárhely), ahol a konkrét modult konfigurációból olvassuk. Tesztben így egy fake vagy Mox-mock modul köthető be valódi hálózati hívás nélkül. Buktató: a modul a konfigurációból futásidőben jön, ezért elírt modulnév csak futáskor derül ki — az `Application.compile_env` vagy induláskori ellenőrzés segít.

```elixir
defmodule Notifier do
  @moduledoc "Értesítő-adapterek közös szerződése."
  @type recipient :: String.t()
  @callback deliver(recipient, subject :: String.t(), body :: String.t()) ::
              {:ok, id :: String.t()} | {:error, term()}
  @callback max_length() :: pos_integer()

  # A felhasználói kód csak ezt hívja; az adapter konfigurációból jön
  def notify(recipient, subject, body, adapter \\ adapter()) do
    if String.length(body) > adapter.max_length() do
      {:error, :too_long}
    else
      adapter.deliver(recipient, subject, body)
    end
  end

  defp adapter, do: Application.get_env(:my_app, :notifier, Notifier.Log)
end

defmodule Notifier.Sms do
  @behaviour Notifier

  @impl true
  def max_length, do: 160

  @impl true
  def deliver(phone, _subject, body) do
    # Valódi rendszerben itt HTTP-hívás menne az SMS-szolgáltató felé
    if String.starts_with?(phone, "+"),
      do: {:ok, "sms-" <> Integer.to_string(:erlang.phash2({phone, body}))},
      else: {:error, :invalid_phone}
  end
end

defmodule Notifier.Log do
  @behaviour Notifier

  @impl true
  def max_length, do: 10_000

  @impl true
  def deliver(to, subject, body) do
    IO.puts("[értesítés] #{to} | #{subject} | #{body}")
    {:ok, "log-#{System.unique_integer([:positive])}"}
  end
end

# Teszt-adapter: üzenetet küld a tesztfolyamatnak, így ellenőrizhető
defmodule Notifier.Test do
  @behaviour Notifier
  @impl true
  def max_length, do: 50
  @impl true
  def deliver(to, subject, body) do
    send(self(), {:notified, to, subject, body})
    {:ok, "test"}
  end
end

IO.inspect(Notifier.notify("ops@example.com", "Riasztás", "CPU 95%"))
IO.inspect(Notifier.notify("+36301234567", "Kód", "Belépési kód: 4821", Notifier.Sms))
IO.inspect(Notifier.notify("06301234567", "Kód", "x", Notifier.Sms))   # {:error, :invalid_phone}
IO.inspect(Notifier.notify("a@b.hu", "Teszt", String.duplicate("x", 60), Notifier.Test))
Notifier.notify("a@b.hu", "Teszt", "rövid", Notifier.Test)
receive do
  {:notified, to, _, _} -> IO.puts("a teszt-adapter megkapta: #{to}")
end
```

## Makrók és metaprogramozás
<!-- q: Hogyan írjak makrókat Elixirben quote és unquote segítségével? -->
<!-- tags: macros, quote, unquote, defmacro, __using__, before_compile, metaprogramming, ast -->

Az Elixir kódja fordításkor AST-vé (háromelemű tuple-ök fája) alakul, a makró pedig olyan függvény, amely fordítási időben AST-t kap és AST-t ad vissza. A `quote` kódot AST-vé alakít, az `unquote` beilleszt egy értéket vagy kifejezést, a makró-higiénia pedig garantálja, hogy a makróban létrehozott változók ne ütközzenek a hívó változóival. A `use Modul` a `__using__/1` makrót hívja (így injektál kódot pl. a `use GenServer`), a modul-attribútumok gyűjtése és a `@before_compile` DSL-ek építésére jó (Ecto séma, Phoenix router). Buktató: a makró nehezebben olvasható és debugolható — „ne írj makrót, ha függvény is megoldja”; az argumentum többszöri `unquote`-ja többszöri kiértékelést okoz (használd `bind_quoted`-ot vagy köss változóhoz).

```elixir
defmodule Timing do
  # A blokk köré mérést tesz; a start/result változók higiénikusak (nem szivárognak ki)
  defmacro measure(label, do: block) do
    quote do
      start = System.monotonic_time(:microsecond)
      result = unquote(block)
      IO.puts("#{unquote(label)}: #{System.monotonic_time(:microsecond) - start} µs")
      result
    end
  end
end

defmodule Validator do
  # use Validator: importálja a DSL-t és gyűjtő attribútumot regisztrál
  defmacro __using__(_opts) do
    quote do
      import Validator, only: [validate: 2]
      Module.register_attribute(__MODULE__, :rules, accumulate: true)
      @before_compile Validator
    end
  end

  # Minden validate hívás egy szabályt tesz az attribútumba (fordítási időben)
  defmacro validate(field, rule) do
    quote do: @rules({unquote(field), unquote(rule)})
  end

  # A modul fordításának végén függvényeket generálunk a szabályokból
  defmacro __before_compile__(env) do
    rules = env.module |> Module.get_attribute(:rules) |> Enum.reverse()

    quote do
      def rules, do: unquote(Macro.escape(rules))
      def errors(params), do: Validator.run(unquote(Macro.escape(rules)), params)
    end
  end

  # Futásidejű rész: sima függvény (amit lehet, ne makróban csinálj)
  def run(rules, params) do
    Enum.flat_map(rules, fn
      {field, :required} ->
        if params[field] in [nil, ""], do: [{field, "kötelező"}], else: []

      {field, {:min_length, n}} ->
        if String.length(params[field] || "") < n, do: [{field, "min. #{n} karakter"}], else: []
    end)
  end
end

defmodule UserForm do
  use Validator
  validate :name, :required
  validate :password, :required
  validate :password, {:min_length, 8}
end

require Timing

Timing.measure "validálás" do
  IO.inspect(UserForm.errors(%{name: "", password: "rovid"}))
end

IO.inspect(UserForm.rules())
IO.inspect(quote(do: 1 + x * 2))   # az AST: {:+, _, [1, {:*, _, [{:x, _, _}, 2]}]}
```

## ETS: gyors, megosztott memóriatáblák
<!-- q: Hogyan használjam az ETS táblákat Elixirben gyors, párhuzamosan olvasható cache-hez? -->
<!-- tags: ets, erlang term storage, cache, read_concurrency, update_counter, match spec, rate limiter -->

Az ETS (Erlang Term Storage) a BEAM beépített, memóriában lévő kulcs-érték táblája: a folyamatok kívül tárolja az adatot, így sok folyamat egyszerre, üzenetküldés és sorosítás nélkül olvashatja — ezért gyorsabb a GenServer-alapú cache-nél, ha az olvasás dominál. Típusai: `:set`, `:ordered_set`, `:bag`, `:duplicate_bag`; a `read_concurrency`/`write_concurrency` opciók a párhuzamos hozzáférést optimalizálják, az `:ets.update_counter` atomikus számlálót ad (rate limiter, statisztika). Buktatók: a tábla a létrehozó (tulajdonos) folyamattal együtt megszűnik, ezért egy hosszú életű, felügyelt folyamat hozza létre; az olvasás *másolja* az adatot a hívó heapjébe (nagy értékeknél költséges); és nincs tranzakció több kulcsra.

```elixir
defmodule RateLimiter do
  @moduledoc "Fix ablakos rate limiter ETS-sel: kulcsonként max N kérés ablakonként."
  use GenServer

  @table :rate_limits

  def start_link(opts), do: GenServer.start_link(__MODULE__, opts, name: __MODULE__)

  # A tábla tulajdonosa ez a GenServer; ha leáll, a supervisor újraindítja
  @impl true
  def init(opts) do
    :ets.new(@table, [:named_table, :public, :set, read_concurrency: true, write_concurrency: true])
    window = Keyword.get(opts, :window_ms, 1_000)
    Process.send_after(self(), :cleanup, window)
    {:ok, %{window: window}}
  end

  # Ez a hívó folyamatban fut, GenServer-üzenet NÉLKÜL: nincs szűk keresztmetszet
  def allow?(key, limit, window_ms \\ 1_000) do
    bucket = div(System.system_time(:millisecond), window_ms)
    # Atomikus növelés; ha nincs még sor, a default tuple-lel jön létre
    count = :ets.update_counter(@table, {key, bucket}, {2, 1}, {{key, bucket}, 0})
    count <= limit
  end

  # Régi ablakok törlése match spec-kel: {{kulcs, ablak}, darab}, ahol ablak < aktuális
  @impl true
  def handle_info(:cleanup, %{window: w} = state) do
    current = div(System.system_time(:millisecond), w)
    spec = [{{{:_, :"$1"}, :_}, [{:<, :"$1", current}], [true]}]
    deleted = :ets.select_delete(@table, spec)
    if deleted > 0, do: IO.puts("törölt régi bejegyzések: #{deleted}")
    Process.send_after(self(), :cleanup, w)
    {:noreply, state}
  end
end

{:ok, _} = RateLimiter.start_link(window_ms: 1_000)

# 20 párhuzamos kérés ugyanattól a klienstől, limit 5/ablak
results =
  1..20
  |> Task.async_stream(fn _ -> RateLimiter.allow?("client-42", 5) end)
  |> Enum.map(fn {:ok, allowed} -> allowed end)

IO.puts("engedélyezett: #{Enum.count(results, & &1)}")   # 5 (vagy ablakhatáron kicsit több)
IO.inspect(:ets.info(:rate_limits, :size))
```

## Ecto: séma és changeset
<!-- q: Hogyan definiáljak Ecto sémát és validáljak adatot changesettel? -->
<!-- tags: ecto, schema, changeset, validation, cast, constraints, database -->

Az Ecto az Elixir adatbázis-könyvtára, de nem klasszikus ORM: a séma (`schema`) csak az adatszerkezetet írja le, az adatbázis-műveletek a `Repo`-n keresztül, explicit módon történnek. A változtatásokat *changeset* írja le: a `cast` szűri és típuskonvertálja a külső paramétereket (csak az engedélyezett mezők jutnak át — tömeges hozzárendelés elleni védelem), a `validate_*` függvények ellenőriznek, a `*_constraint` függvények pedig az adatbázis-megszorítások (unique index, foreign key) hibáit alakítják changeset-hibává kivétel helyett. Buktató: a `unique_constraint` csak akkor működik, ha az adatbázisban valóban van unique index (migrációban), és a virtuális mezők (`virtual: true`, pl. jelszó) nem kerülnek mentésre.

```elixir
defmodule Shop.Accounts.User do
  use Ecto.Schema
  import Ecto.Changeset

  schema "users" do
    field :email, :string
    field :name, :string
    field :age, :integer
    field :role, Ecto.Enum, values: [:customer, :admin], default: :customer
    field :password, :string, virtual: true, redact: true   # nem kerül az adatbázisba
    field :password_hash, :string, redact: true
    has_many :orders, Shop.Orders.Order
    timestamps(type: :utc_datetime)
  end

  # Regisztráció: a role-t szándékosan NEM castoljuk (külső input ne állíthassa)
  def registration_changeset(user, attrs) do
    user
    |> cast(attrs, [:email, :name, :age, :password])
    |> validate_required([:email, :name, :password])
    |> update_change(:email, &String.downcase/1)
    |> validate_format(:email, ~r/^[^@\s]+@[^@\s]+$/, message: "érvénytelen e-mail")
    |> validate_number(:age, greater_than_or_equal_to: 16)
    |> validate_length(:password, min: 10, max: 72)
    |> unique_constraint(:email)           # DB unique index hibája -> changeset hiba
    |> put_password_hash()
  end

  defp put_password_hash(%Ecto.Changeset{valid?: true, changes: %{password: pw}} = cs) do
    # Éles kódban: Bcrypt.hash_pwd_salt(pw) / Argon2; itt csak szemléltetés
    cs
    |> put_change(:password_hash, :crypto.hash(:sha256, pw) |> Base.encode16())
    |> delete_change(:password)
  end

  defp put_password_hash(cs), do: cs
end

# Repo nélkül is kipróbálható: a changeset tiszta adatszerkezet
alias Shop.Accounts.User

cs = User.registration_changeset(%User{}, %{"email" => "Anna@Example.COM", "name" => "Anna",
                                            "age" => "21", "password" => "nagyonhosszu1", "role" => "admin"})
IO.inspect({cs.valid?, cs.changes.email, Map.has_key?(cs.changes, :role)})  # {true, "anna@example.com", false}

bad = User.registration_changeset(%User{}, %{"email" => "rossz", "age" => "12", "password" => "rövid"})
errors =
  Ecto.Changeset.traverse_errors(bad, fn {msg, opts} ->
    Enum.reduce(opts, msg, fn {k, v}, acc -> String.replace(acc, "%{#{k}}", to_string(v)) end)
  end)

IO.inspect(errors)   # %{age: [...], email: [...], name: ["can't be blank"], password: [...]}
# Mentés valós Repo-val: Repo.insert(cs) -> {:ok, %User{}} | {:error, %Ecto.Changeset{}}
```

## Ecto lekérdezések, preload és Ecto.Multi
<!-- q: Hogyan írjak Ecto lekérdezéseket, kerüljem el az N+1 problémát, és kezeljek tranzakciót Ecto.Multi-val? -->
<!-- tags: ecto query, preload, n+1, joins, aggregates, ecto.multi, transaction, repo -->

Az Ecto lekérdezései (`from`, illetve pipe-olható `where`/`join`/`select`) fordítási időben ellenőrzött, összetehető adatszerkezetek, amelyekből a `Repo` paraméterezett SQL-t generál (SQL injection ellen védett, a külső értéket mindig `^` pinnel kell beilleszteni). Az asszociációk nem töltődnek be automatikusan: a `preload` explicit kéri őket, egy lekérdezéssel asszociációnként, így elkerülhető az N+1 probléma. Több, összetartozó írást az `Ecto.Multi` fűz egy tranzakcióba: a lépések neveket kapnak, a későbbi lépések elérik a korábbiak eredményét, és bármelyik hibájánál minden visszagörgetődik. Buktató: a `Repo.all` nagy táblán mindent memóriába tölt (`Repo.stream` tranzakcióban), és a lekérdezésen kívüli `Enum.filter` az adatbázis helyett az alkalmazásban szűr.

```elixir
defmodule Shop.Orders do
  import Ecto.Query
  alias Ecto.Multi
  alias Shop.Repo
  alias Shop.Orders.{Order, LineItem}
  alias Shop.Inventory.Product

  # Összetehető lekérdezés-építők: mindegyik query-t kap és query-t ad
  def base, do: from(o in Order, as: :order)
  def paid(query), do: where(query, [order: o], o.status == :paid)
  def since(query, %DateTime{} = dt), do: where(query, [order: o], o.inserted_at >= ^dt)

  # N+1 elkerülése: a vevő és a tételek a termékkel együtt, kevés lekérdezéssel
  def recent_paid_with_items(dt) do
    base()
    |> paid()
    |> since(dt)
    |> order_by([order: o], desc: o.inserted_at)
    |> limit(50)
    |> preload([:user, line_items: :product])
    |> Repo.all()
  end

  # Aggregálás az adatbázisban: vevőnkénti bevétel, csak 10 000 Ft felett
  def revenue_by_user do
    from(o in Order,
      join: u in assoc(o, :user),
      where: o.status == :paid,
      group_by: [u.id, u.email],
      having: sum(o.total) > 10_000,
      select: %{user_id: u.id, email: u.email, revenue: sum(o.total), orders: count(o.id)},
      order_by: [desc: sum(o.total)]
    )
    |> Repo.all()
  end

  # Tranzakció: rendelés + tételek + készletcsökkentés; bármely hiba -> teljes rollback
  def place_order(user, items) do
    Multi.new()
    |> Multi.insert(:order, Order.changeset(%Order{user_id: user.id}, %{status: :pending}))
    |> Multi.run(:line_items, fn repo, %{order: order} ->
      Enum.reduce_while(items, {:ok, []}, fn %{product_id: pid, qty: qty}, {:ok, acc} ->
        # Atomikus feltételes csökkentés: csak ha van elég készlet
        {count, _} =
          from(p in Product, where: p.id == ^pid and p.stock >= ^qty)
          |> repo.update_all(inc: [stock: -qty])

        if count == 1 do
          li = repo.insert!(%LineItem{order_id: order.id, product_id: pid, qty: qty})
          {:cont, {:ok, [li | acc]}}
        else
          {:halt, {:error, {:out_of_stock, pid}}}
        end
      end)
    end)
    |> Multi.update(:confirm, fn %{order: order} -> Order.changeset(order, %{status: :paid}) end)
    |> Repo.transaction()
    |> case do
      {:ok, %{confirm: order}} -> {:ok, order}
      {:error, step, reason, _done_so_far} -> {:error, step, reason}
    end
  end
end
```

## Phoenix LiveView: valós idejű UI szerveroldalon
<!-- q: Hogyan építsek interaktív, valós idejű felületet Phoenix LiveView-val? -->
<!-- tags: phoenix, liveview, heex, handle_event, assigns, pubsub, real-time, websocket -->

A Phoenix LiveView-ban a felület állapota a szerveren, egy folyamatban él (`socket.assigns`); a böngésző egy WebSocketen küldi az eseményeket (`phx-click`, `phx-change`, `phx-submit`), a szerver `handle_event`-ben frissíti az állapotot, és a LiveView csak a megváltozott HTML-részeket (diffet) küldi vissza. Így SPA-szerű interaktivitás érhető el saját JavaScript és külön API nélkül; a `Phoenix.PubSub` segítségével más felhasználók változásai is valós időben megjelennek (`handle_info`). A `mount` kétszer fut (először statikus HTTP render, aztán a WebSocket csatlakozáskor), ezért feliratkozást csak `connected?(socket)` esetén végezz. Buktató: nagy listákat `stream`-mel kezelj (különben minden elem a szerver memóriájában marad), és minden eseményben ellenőrizd a jogosultságot — a kliens bármilyen eseményt küldhet.

```elixir
defmodule ShopWeb.ProductSearchLive do
  use ShopWeb, :live_view
  alias Shop.Catalog

  @impl true
  def mount(_params, _session, socket) do
    # Csak élő (WebSocket) kapcsolatnál iratkozunk fel a készletváltozásokra
    if connected?(socket), do: Phoenix.PubSub.subscribe(Shop.PubSub, "stock")

    {:ok,
     socket
     |> assign(query: "", loading: false, page_title: "Termékkereső")
     |> stream(:products, Catalog.search(""))}
  end

  # Gépelés közben (phx-change + phx-debounce) frissül a találati lista
  @impl true
  def handle_event("search", %{"q" => q}, socket) do
    {:noreply,
     socket
     |> assign(query: q)
     |> stream(:products, Catalog.search(q), reset: true)}
  end

  def handle_event("add_to_cart", %{"id" => id}, socket) do
    # A kliens bármit küldhet: azonosítás és jogosultság a szerveren
    case Catalog.add_to_cart(socket.assigns.current_user, String.to_integer(id)) do
      :ok -> {:noreply, put_flash(socket, :info, "Kosárba téve")}
      {:error, :out_of_stock} -> {:noreply, put_flash(socket, :error, "Elfogyott")}
    end
  end

  # Más folyamatból (PubSub) érkező valós idejű frissítés: egy elem cseréje
  @impl true
  def handle_info({:stock_changed, product}, socket) do
    {:noreply, stream_insert(socket, :products, product)}
  end

  @impl true
  def render(assigns) do
    ~H"""
    <form phx-change="search" phx-submit="search">
      <input type="text" name="q" value={@query} phx-debounce="300" placeholder="Keresés…" />
    </form>

    <ul id="products" phx-update="stream">
      <li :for={{dom_id, p} <- @streams.products} id={dom_id}>
        <span>{p.name}</span>
        <span class={if p.stock == 0, do: "text-red-600", else: "text-green-700"}>
          {p.stock} db
        </span>
        <button phx-click="add_to_cart" phx-value-id={p.id} disabled={p.stock == 0}>
          Kosárba
        </button>
      </li>
    </ul>
    """
  end
end

# Bárhonnan (pl. a raktár-kezelő kódból) szólva minden nyitott oldal frissül:
# Phoenix.PubSub.broadcast(Shop.PubSub, "stock", {:stock_changed, product})
```
