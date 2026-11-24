# C#
<!-- tech: csharp -->
<!-- aliases: c#, .net, dotnet -->

A C# a Microsoft statikusan típusos, többparadigmás (objektumorientált, funkcionális elemekkel bővített) nyelve, amely a .NET futtatókörnyezeten (CLR) fut: a fordító IL kódot állít elő, amit a JIT (vagy Native AOT esetén előre) gépi kódra fordít. A memóriát generációs szemétgyűjtő kezeli, de a `Span<T>`, a `struct`-ok és az `ArrayPool` révén alacsony szintű, allokációmentes kód is írható. Erős területei a webes backend (ASP.NET Core), az asztali (WPF, WinForms, MAUI) és a játékfejlesztés (Unity), a felhő és a vállalati rendszerek; kiváló az async/await támogatása, a LINQ és a tooling. Kevésbé ideális apró, gyorsan induló szkriptekhez (bár a Native AOT ezen sokat javít) és ott, ahol a GC-szünetek teljesen elfogadhatatlanok.

## CLR, szemétgyűjtő és generációk
<!-- q: Hogyan működik a .NET szemétgyűjtő és mik a generációk? -->
<!-- tags: clr, gc, garbage collector, generations, loh, idisposable, finalizer -->

A CLR menedzselt heapen foglal, és a GC generációkban gondolkodik: az új objektumok a Gen0-ba kerülnek, a túlélők Gen1-be, majd Gen2-be lépnek elő, mert a legtöbb objektum fiatalon hal meg, így a gyakori Gen0 gyűjtés olcsó. A 85 000 bájtnál nagyobb objektumok a Large Object Heapre (LOH) kerülnek, amit csak Gen2 gyűjtéskor takarít, és alapból nem tömörít. A GC nem hívja a `Dispose`-t: a nem menedzselt erőforrásokat (fájl, socket, natív memória) `IDisposable` + `using` szabadítja fel determinisztikusan; a finalizer csak biztonsági háló, és lassítja a gyűjtést. Éles kódban kerüld a `GC.Collect()` hívást, inkább csökkentsd az allokációkat.

```csharp
using System;
using System.Runtime;
using System.Runtime.InteropServices;

// Nem menedzselt erőforrást birtokló osztály a szabványos Dispose-mintával
public sealed class NativeBuffer : IDisposable
{
    private IntPtr _ptr;          // a GC erről a memóriáról nem tud
    private bool _disposed;
    public int Size { get; }

    public NativeBuffer(int size)
    {
        _ptr = Marshal.AllocHGlobal(size);
        GC.AddMemoryPressure(size);   // jelezzük a GC-nek a valódi memórianyomást
        Size = size;
    }

    public void Dispose()
    {
        Dispose(true);
        GC.SuppressFinalize(this);    // a finalizer már nem kell → olcsóbb takarítás
    }

    private void Dispose(bool disposing)
    {
        if (_disposed) return;
        Marshal.FreeHGlobal(_ptr);
        GC.RemoveMemoryPressure(Size);
        _ptr = IntPtr.Zero;
        _disposed = true;
    }

    // Biztonsági háló, ha valaki elfelejti a Dispose-t (modern kódban inkább SafeHandle)
    ~NativeBuffer() => Dispose(false);
}

public static class GcDemo
{
    public static void Main()
    {
        var small = new object();
        Console.WriteLine($"Új objektum generációja: {GC.GetGeneration(small)}");   // 0

        GC.Collect(0);                // CSAK demóhoz — éles kódban kerüld
        Console.WriteLine($"Egy gyűjtés után: {GC.GetGeneration(small)}");         // 1

        var big = new byte[100_000];  // >= 85 000 bájt → Large Object Heap
        Console.WriteLine($"LOH objektum generációja: {GC.GetGeneration(big)}");     // 2

        Console.WriteLine($"Server GC: {GCSettings.IsServerGC}, latency: {GCSettings.LatencyMode}");

        using (var buf = new NativeBuffer(4096))
        {
            Console.WriteLine($"Puffer: {buf.Size} bájt");
        } // itt fut a Dispose, nem a GC-re várunk

        var info = GC.GetGCMemoryInfo();
        Console.WriteLine($"Heap: {info.HeapSizeBytes / 1024} KB, Gen0 gyűjtések: {GC.CollectionCount(0)}");
    }
}
```

## Érték- és referenciatípusok
<!-- q: Mi a különbség az érték- és a referenciatípusok között C#-ban? -->
<!-- tags: struct, class, value type, reference type, boxing, ref return, in parameter -->

Az értéktípusok (`struct`, `int`, `enum`, `record struct`) értékadáskor teljesen lemásolódnak, és jellemzően a stacken vagy a tartalmazó objektumba ágyazva élnek; a referenciatípusoknál (`class`, `string`, tömb) csak a hivatkozás másolódik, az objektum a heapen van. A kis, immutábilis adatokra (koordináta, pénzösszeg) a `readonly struct` ideális, mert nincs heap-allokáció. Buktatók: a boxing (struct → `object`/interfész) rejtett allokációt okoz, a nagy structok másolása drága (erre van az `in` paraméter), és a mutábilis struct a `List<T>` indexelőjén keresztül csak másolatként módosulna.

```csharp
using System;
using System.Collections.Generic;

// readonly struct: a fordító nem készít rejtett védő másolatokat
public readonly struct Point3
{
    public Point3(double x, double y, double z) => (X, Y, Z) = (x, y, z);
    public double X { get; }
    public double Y { get; }
    public double Z { get; }
    public double Length => Math.Sqrt(X * X + Y * Y + Z * Z);
    public Point3 WithX(double x) => new(x, Y, Z);   // módosítás helyett új példány
}

public class Node { public int Value; }

public static class ValueVsRef
{
    // 'in': referenciával adjuk át, de csak olvasható → nagy structnál nincs másolás
    static double Dist(in Point3 a, in Point3 b)
    {
        double dx = a.X - b.X, dy = a.Y - b.Y, dz = a.Z - b.Z;
        return Math.Sqrt(dx * dx + dy * dy + dz * dz);
    }

    // ref return: a tömb elemére ad hivatkozást, nem másolatot
    static ref int FindMax(int[] arr)
    {
        int idx = 0;
        for (int i = 1; i < arr.Length; i++) if (arr[i] > arr[idx]) idx = i;
        return ref arr[idx];
    }

    public static void Main()
    {
        var p1 = new Point3(1, 2, 2);
        var p2 = p1;                                   // teljes másolat
        Console.WriteLine(Dist(p1, p2.WithX(4)));      // 3

        var n1 = new Node { Value = 1 };
        var n2 = n1;                                   // ugyanarra az objektumra mutat
        n2.Value = 42;
        Console.WriteLine(n1.Value);                   // 42

        object boxed = 5;                              // boxing: heap-allokáció
        int unboxed = (int)boxed;                      // unboxing: típusellenőrzés + másolás
        Console.WriteLine(unboxed);

        var list = new List<Point3> { p1 };
        var copy = list[0];                            // az indexelő MÁSOLATOT ad vissza
        Console.WriteLine(copy.Length);                // 3

        int[] nums = { 3, 9, 4 };
        ref int max = ref FindMax(nums);
        max = 0;                                       // a tömbben is átíródik
        Console.WriteLine(string.Join(",", nums));     // 3,0,4
    }
}
```

## Span<T>, Memory<T> és ArrayPool
<!-- q: Hogyan írjak allokációmentes kódot Span<T>-vel és Memory<T>-vel? -->
<!-- tags: span, memory, stackalloc, arraypool, performance, zero allocation, ref struct -->

A `Span<T>` egy összefüggő memóriaterület (tömb, stack, natív memória) típusbiztos szelete; szeletelése nem másol, így parse-olás és pufferkezelés allokáció nélkül megy. Mivel `ref struct`, csak a stacken élhet: nem lehet mezője osztálynak, és nem élheti túl az `await`-et — ilyenkor a `Memory<T>` kell, amiből a `.Span`-nel kapsz szeletet. A nagy, ideiglenes pufferekre az `ArrayPool<T>.Shared` való, de a bérelt tömböt mindig vissza kell adni (`finally`), és a hossza nagyobb lehet a kértnél.

```csharp
using System;
using System.Buffers;
using System.Text;
using System.Threading.Tasks;

public static class SpanDemo
{
    // "12;7;33;5" összegzése string-allokáció nélkül
    public static int SumFields(ReadOnlySpan<char> line, char sep = ';')
    {
        int sum = 0;
        while (!line.IsEmpty)
        {
            int idx = line.IndexOf(sep);
            ReadOnlySpan<char> field = idx < 0 ? line : line[..idx];   // szelet, nem másolat
            if (int.TryParse(field, out int v)) sum += v;
            line = idx < 0 ? ReadOnlySpan<char>.Empty : line[(idx + 1)..];
        }
        return sum;
    }

    // stackalloc: kis puffer a stacken, GC nélkül; nagy méretnél heapre váltunk
    public static string ToHex(ReadOnlySpan<byte> data)
    {
        Span<char> buf = data.Length <= 128 ? stackalloc char[data.Length * 2] : new char[data.Length * 2];
        const string digits = "0123456789abcdef";
        for (int i = 0; i < data.Length; i++)
        {
            buf[i * 2] = digits[data[i] >> 4];
            buf[i * 2 + 1] = digits[data[i] & 0xF];
        }
        return new string(buf);
    }

    // Memory<T>: async metódusban kell, mert a Span nem élheti túl az await-et
    public static async Task<int> CountNewlinesAsync(ReadOnlyMemory<byte> buffer)
    {
        await Task.Yield();
        int count = 0;
        foreach (byte b in buffer.Span) if (b == (byte)'\n') count++;
        return count;
    }

    public static async Task Main()
    {
        Console.WriteLine(SumFields("12;7;33;5"));               // 57
        Console.WriteLine(ToHex(Encoding.UTF8.GetBytes("AB")));   // 4142

        byte[] rented = ArrayPool<byte>.Shared.Rent(4096);       // lehet nagyobb is!
        try
        {
            int len = Encoding.UTF8.GetBytes("a\nb\nc".AsSpan(), rented.AsSpan());
            Console.WriteLine(await CountNewlinesAsync(rented.AsMemory(0, len)));  // 2
        }
        finally
        {
            ArrayPool<byte>.Shared.Return(rented);                // mindig add vissza
        }
    }
}
```

## Generikusok és megszorítások
<!-- q: Hogyan használjam a generikusokat és a where megszorításokat C#-ban? -->
<!-- tags: generics, constraints, where, generic math, covariance, inumber -->

A generikusok típusbiztos, újrahasznosítható kódot adnak boxing nélkül: a CLR értéktípusonként külön natív kódot generál, referenciatípusokra közöset. A `where` megszorításokkal (`class`, `struct`, `notnull`, `new()`, interfész, alaposztály) mondod meg, mit tud a típusparaméter, így hívhatod a metódusait. A .NET 7 generic math (`INumber<T>`) statikus absztrakt interfésztagokkal egyetlen implementációt ad minden numerikus típusra. A variancia (`out`/`in`) csak interfészekre és delegate-ekre működik, és csak referenciatípusokkal.

```csharp
using System;
using System.Collections.Generic;
using System.Numerics;

public interface IEntity<TKey> where TKey : IEquatable<TKey>
{
    TKey Id { get; }
}

// Generikus repository több megszorítással
public sealed class InMemoryRepository<TEntity, TKey>
    where TEntity : class, IEntity<TKey>      // referenciatípus és interfész
    where TKey : notnull, IEquatable<TKey>    // kulcs nem lehet null
{
    private readonly Dictionary<TKey, TEntity> _store = new();

    public void Upsert(TEntity entity) => _store[entity.Id] = entity;
    public TEntity? Find(TKey id) => _store.TryGetValue(id, out var e) ? e : null;

    // new(): paraméter nélküli konstruktor szükséges
    public static T CreateDefault<T>() where T : new() => new T();
}

public static class MathUtil
{
    // Generic math (.NET 7+): int, double, decimal... mind ugyanazzal a kóddal
    public static T Sum<T>(ReadOnlySpan<T> values) where T : INumber<T>
    {
        T acc = T.Zero;
        foreach (var v in values) acc += v;
        return acc;
    }

    // Kovariancia: IEnumerable<out T> miatt List<string> átadható IEnumerable<object>-ként
    public static int CountAll(IEnumerable<object> items)
    {
        int n = 0;
        foreach (var _ in items) n++;
        return n;
    }
}

public record User(int Id, string Name) : IEntity<int>;

public static class GenericsDemo
{
    public static void Main()
    {
        var repo = new InMemoryRepository<User, int>();
        repo.Upsert(new User(1, "Teszt Elek"));
        Console.WriteLine(repo.Find(1)?.Name ?? "nincs");

        Console.WriteLine(MathUtil.Sum<int>(new[] { 1, 2, 3 }));            // 6
        Console.WriteLine(MathUtil.Sum<decimal>(new[] { 1.5m, 2.5m }));     // 4.0
        Console.WriteLine(MathUtil.CountAll(new List<string> { "a", "b" })); // 2
    }
}
```

## LINQ, extension methodok és expression tree-k
<!-- q: Hogyan működik a LINQ késleltetett végrehajtása és mire jók az expression tree-k? -->
<!-- tags: linq, deferred execution, extension methods, expression trees, iqueryable, yield -->

A LINQ operátorok extension methodok az `IEnumerable<T>`-n; a legtöbb (Where, Select, GroupBy) késleltetett: csak egy lekérdezés-leírót építenek, és a futás az első bejáráskor (`foreach`, `ToList`, `Count`) történik. Ezért a forrás későbbi változásai is látszanak, a többszöri bejárás viszont többször futtat mindent — ilyenkor materializálj. Az `IQueryable<T>` lambdái `Expression<Func<...>>` formában, adatszerkezetként érkeznek, ezt fordítja SQL-re például az EF Core; magad is építhetsz és fordíthatsz ilyen fát. Saját operátort `this` paraméteres statikus metódussal és `yield return`-nel írhatsz.

```csharp
using System;
using System.Collections.Generic;
using System.Linq;
using System.Linq.Expressions;

public static class LinqExtensions
{
    // Saját operátor: feltételes szűrés
    public static IEnumerable<T> WhereIf<T>(this IEnumerable<T> source, bool condition, Func<T, bool> predicate)
        => condition ? source.Where(predicate) : source;

    // yield miatt késleltetett: csak tényleges bejáráskor fut
    public static IEnumerable<T> Tap<T>(this IEnumerable<T> source, Action<T> action)
    {
        foreach (var item in source)
        {
            action(item);
            yield return item;
        }
    }
}

public record Order(int Id, string Customer, decimal Total);

public static class LinqDemo
{
    public static void Main()
    {
        var orders = new List<Order> { new(1, "A", 120m), new(2, "B", 80m), new(3, "A", 300m) };

        // Itt még SEMMI nem fut, csak a lekérdezés épül fel
        var query = orders
            .Tap(o => Console.WriteLine($"  vizsgálom: {o.Id}"))
            .WhereIf(true, o => o.Total > 100m)
            .GroupBy(o => o.Customer)
            .Select(g => new { Customer = g.Key, Sum = g.Sum(o => o.Total), Count = g.Count() });

        orders.Add(new(4, "B", 500m));          // a lekérdezés ezt is látni fogja

        foreach (var row in query)               // a végrehajtás itt indul
            Console.WriteLine($"{row.Customer}: {row.Sum} ({row.Count} db)");

        var cached = query.ToList();             // materializálás: többé nem fut újra
        Console.WriteLine(cached.Count);

        // Expression tree: a lambda adatként, nem lefordított kódként
        Expression<Func<Order, bool>> expr = o => o.Total > 100m && o.Customer == "A";
        Console.WriteLine(expr.Body);            // ((o.Total > 100) AndAlso (o.Customer == "A"))
        Func<Order, bool> compiled = expr.Compile();
        Console.WriteLine(orders.Count(compiled)); // 2

        // Dinamikus szűrő építése (pl. felhasználói filterből)
        var p = Expression.Parameter(typeof(Order), "o");
        var body = Expression.Equal(Expression.Property(p, nameof(Order.Customer)), Expression.Constant("B"));
        var lambda = Expression.Lambda<Func<Order, bool>>(body, p);
        Console.WriteLine(orders.AsQueryable().Where(lambda).Count());   // 2
    }
}
```

## async/await belülről: Task, ValueTask, SynchronizationContext
<!-- q: Hogyan működik az async/await C#-ban, és mikor használjak ValueTask-ot vagy ConfigureAwait(false)-t? -->
<!-- tags: async, await, task, valuetask, synchronizationcontext, configureawait, state machine, deadlock -->

A fordító az `async` metódusból állapotgépet generál: minden `await` egy lehetséges felfüggesztési pont, ahol a szál felszabadul, és a folytatás a művelet végén ütemeződik. Ha van `SynchronizationContext` (WPF/WinForms UI-szál), a folytatás oda tér vissza; könyvtári kódban a `ConfigureAwait(false)` ezt kikapcsolja, ami gyorsabb és megelőzi a `.Result`/`.Wait()` okozta deadlockot. A `ValueTask` akkor éri meg, ha az eredmény gyakran szinkron (cache-ből) jön, de csak egyszer szabad await-elni. Az `async void` csak eseménykezelőben elfogadható, mert a kivétele nem kapható el.

```csharp
using System;
using System.Collections.Concurrent;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;

public sealed class CachedFetcher
{
    private readonly HttpClient _http;
    private readonly ConcurrentDictionary<string, string> _cache = new();
    public CachedFetcher(HttpClient http) => _http = http;

    // ValueTask: cache-találatnál nincs Task-allokáció
    public ValueTask<string> GetAsync(string url, CancellationToken ct = default)
    {
        if (_cache.TryGetValue(url, out var hit))
            return ValueTask.FromResult(hit);               // szinkron út
        return new ValueTask<string>(FetchAndCacheAsync(url, ct));
    }

    private async Task<string> FetchAndCacheAsync(string url, CancellationToken ct)
    {
        // Könyvtári kód: nem kell visszatérni a hívó kontextusára
        var body = await _http.GetStringAsync(url, ct).ConfigureAwait(false);
        _cache[url] = body;
        return body;
    }
}

public static class AsyncDemo
{
    static async Task<int> ComputeAsync(int x)
    {
        await Task.Delay(50);                               // nem blokkol szálat
        return x * 2;
    }

    public static async Task Main()
    {
        // Párhuzamos indítás, közös várakozás
        int[] results = await Task.WhenAll(ComputeAsync(1), ComputeAsync(2), ComputeAsync(3));
        Console.WriteLine(string.Join(",", results));       // 2,4,6

        // Az await csak az ELSŐ kivételt dobja; az összes a Task.Exception-ben van
        var failing = Task.WhenAll(Task.FromException(new InvalidOperationException("x")), Task.Delay(10));
        try { await failing; }
        catch (InvalidOperationException ex)
        {
            Console.WriteLine($"Hiba: {ex.Message}, összes: {failing.Exception?.InnerExceptions.Count}");
        }

        // CPU-igényes munka UI-alkalmazásban: Task.Run a threadpoolra (ASP.NET-ben általában ne)
        long sum = await Task.Run(() => { long s = 0; for (int i = 0; i < 1_000_000; i++) s += i; return s; });
        Console.WriteLine(sum);
    }
}
```

## CancellationToken, időkorlát és összekapcsolt lemondás
<!-- q: Hogyan szakítsak meg egy hosszú async műveletet CancellationToken-nel? -->
<!-- tags: cancellationtoken, cancellationtokensource, timeout, linked token, operationcanceledexception -->

A .NET lemondása kooperatív: a `CancellationTokenSource` jelez, a token pedig minden rétegen végigadva kerül a ciklusokhoz és az I/O hívásokhoz, amelyek `OperationCanceledException`-nel lépnek ki. Időkorlátot a forrás konstruktorában vagy `CancelAfter`-rel adsz, több forrást (felhasználó + timeout) `CreateLinkedTokenSource`-szal kapcsolsz össze. Buktatók: a forrást `Dispose`-olni kell, a `Register` visszahívásai szinkron futnak a `Cancel` hívó szálán, és ha nem adod tovább a tokent, a lemondás egyszerűen nem hat.

```csharp
using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;

public static class CancellationDemo
{
    static async Task<long> HashFilesAsync(IEnumerable<string> paths, IProgress<string> progress, CancellationToken ct)
    {
        long total = 0;
        var buffer = new byte[8192];
        foreach (var path in paths)
        {
            ct.ThrowIfCancellationRequested();                   // gyors kilépés
            await using var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read, 4096, useAsync: true);
            int read;
            while ((read = await fs.ReadAsync(buffer, ct)) > 0) // a token az I/O-ig jut
                for (int i = 0; i < read; i++) total = unchecked(total * 31 + buffer[i]);
            progress.Report(path);
        }
        return total;
    }

    public static async Task Main()
    {
        // Saját ideiglenes mappa — meglévő fájlhoz nem nyúlunk
        var dir = Directory.CreateTempSubdirectory("ctdemo");
        var files = new List<string>();
        for (int i = 0; i < 3; i++)
        {
            var p = Path.Combine(dir.FullName, $"f{i}.bin");
            await File.WriteAllBytesAsync(p, new byte[1024 * (i + 1)]);
            files.Add(p);
        }

        using var userCts = new CancellationTokenSource();                       // pl. "Mégse" gomb
        using var timeoutCts = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        using var linked = CancellationTokenSource.CreateLinkedTokenSource(userCts.Token, timeoutCts.Token);
        using var reg = linked.Token.Register(() => Console.WriteLine("Lemondva!"));

        try
        {
            var progress = new Progress<string>(p => Console.WriteLine($"kész: {Path.GetFileName(p)}"));
            Console.WriteLine($"Hash: {await HashFilesAsync(files, progress, linked.Token)}");
        }
        catch (OperationCanceledException) when (timeoutCts.IsCancellationRequested)
        {
            Console.WriteLine("Időtúllépés");
        }
        catch (OperationCanceledException)
        {
            Console.WriteLine("A felhasználó megszakította");
        }
        finally
        {
            dir.Delete(recursive: true);   // csak a saját temp mappánkat töröljük
        }
    }
}
```

## Producer–consumer System.Threading.Channels-szel
<!-- q: Hogyan valósítsak meg producer-consumer mintát Channel-lel C#-ban? -->
<!-- tags: channels, producer consumer, backpressure, bounded channel, async streams -->

A `Channel<T>` egy aszinkron, szálbiztos sor, ami a `BlockingCollection` modern, `await`-barát utódja. A korlátos (`CreateBounded`) csatorna backpressure-t ad: ha tele van, a producer vár, így a memória nem nő korlátlanul. A fogyasztók `ReadAllAsync`-kal `await foreach`-ben olvasnak, ami akkor ér véget, ha a writer `Complete()`-et hívott — ennek elmaradása a leggyakoribb hiba (örökre váró fogyasztók). A `SingleWriter`/`SingleReader` opciók gyorsabb implementációt engednek.

```csharp
using System;
using System.Linq;
using System.Threading;
using System.Threading.Channels;
using System.Threading.Tasks;

public record Job(int Id, string Payload);

public static class ChannelDemo
{
    public static async Task Main()
    {
        var channel = Channel.CreateBounded<Job>(new BoundedChannelOptions(capacity: 10)
        {
            FullMode = BoundedChannelFullMode.Wait,   // tele → a WriteAsync vár
            SingleWriter = true,
            SingleReader = false
        });

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));

        var producer = Task.Run(async () =>
        {
            try
            {
                for (int i = 0; i < 50; i++)
                    await channel.Writer.WriteAsync(new Job(i, $"adat-{i}"), cts.Token);
            }
            finally
            {
                channel.Writer.Complete();   // jelzés: több elem nem jön
            }
        });

        // 3 párhuzamos fogyasztó
        var consumers = Enumerable.Range(1, 3).Select(workerId => Task.Run(async () =>
        {
            int processed = 0;
            await foreach (var job in channel.Reader.ReadAllAsync(cts.Token))
            {
                await Task.Delay(10, cts.Token);       // szimulált munka
                processed++;
            }
            Console.WriteLine($"Worker {workerId}: {processed} feladat");
            return processed;
        })).ToArray();

        await producer;
        int[] counts = await Task.WhenAll(consumers);
        Console.WriteLine($"Összesen: {counts.Sum()}");   // 50
    }
}
```

## Párhuzamosság: Parallel és PLINQ
<!-- q: Mikor használjak Parallel.For-t, Parallel.ForEachAsync-et vagy PLINQ-t? -->
<!-- tags: parallel, plinq, asparallel, parallel.foreachasync, threadpool, interlocked, concurrency -->

A `Parallel.For`/`ForEach` és a PLINQ (`AsParallel`) CPU-kötött, egymástól független munkára való: a threadpool szálai között osztják szét az elemeket. I/O-kötött, aszinkron munkára a `Parallel.ForEachAsync` jó, korlátozott párhuzamossággal (`MaxDegreeOfParallelism`). A közös állapotot kerüld: szálankénti lokális akkumulátor + egyetlen `Interlocked` összegzés sokkal gyorsabb, mint a lock minden iterációban. Kis munkánál a párhuzamosítás overheadje nagyobb lehet a nyereségnél, és a PLINQ nem tart sorrendet (`AsOrdered`, ha kell).

```csharp
using System;
using System.Collections.Concurrent;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

public static class ParallelDemo
{
    static bool IsPrime(int n)
    {
        if (n < 2) return false;
        for (int d = 2; (long)d * d <= n; d++) if (n % d == 0) return false;
        return true;
    }

    public static async Task Main()
    {
        // PLINQ: CPU-kötött, független elemek
        int primeCount = Enumerable.Range(1, 2_000_000)
            .AsParallel()
            .WithDegreeOfParallelism(Environment.ProcessorCount)
            .Count(IsPrime);
        Console.WriteLine($"Prímek: {primeCount}");

        // Parallel.For szálankénti részösszeggel — nincs lock iterációnként
        long total = 0;
        Parallel.For(0, 1_000_000,
            () => 0L,                                    // szálankénti kezdőérték
            (i, state, local) => local + (i % 7),        // lokális akkumulálás
            local => Interlocked.Add(ref total, local)); // a végén egyszer szinkronizálunk
        Console.WriteLine($"Összeg: {total}");

        // Parallel.ForEachAsync: I/O-kötött munka, legfeljebb 4 egyszerre
        var results = new ConcurrentBag<(int Id, int Value)>();   // List<T> nem thread-safe
        await Parallel.ForEachAsync(Enumerable.Range(1, 20),
            new ParallelOptions { MaxDegreeOfParallelism = 4 },
            async (id, ct) =>
            {
                await Task.Delay(20, ct);                // pl. HTTP hívás helyett
                results.Add((id, id * 10));
            });
        Console.WriteLine($"Feldolgozva: {results.Count}");
    }
}
```

## Recordok, pattern matching és switch kifejezések
<!-- q: Hogyan használjam a recordokat és a pattern matchinget C#-ban? -->
<!-- tags: record, pattern matching, switch expression, list patterns, with expression, immutability -->

A `record` érték alapú egyenlőséget, `ToString`-et, dekonstrukciót és `with` kifejezést generál, ezért ideális immutábilis adatmodellekhez és DTO-khoz. A switch kifejezés típus-, property-, relációs (`<`, `>=`), logikai (`and`, `or`, `not`), pozicionális és lista mintákat (C# 11) kombinál, és figyelmeztet, ha nem teljes. Buktató: a record egyenlősége a mezőkre épül, így ha listát tartalmaz, az referencia szerint hasonlítódik; a sorrend számít a switch ágainál (a specifikusabb jöjjön előbb).

```csharp
using System;
using System.Collections.Generic;
using System.Linq;

public abstract record Shape;
public sealed record Circle(double Radius) : Shape;
public sealed record Rect(double W, double H) : Shape;
public sealed record Polygon(IReadOnlyList<(double X, double Y)> Points) : Shape;

public record Money(decimal Amount, string Currency)
{
    // Validáció a primary constructor paraméterére
    public decimal Amount { get; init; } = Amount >= 0 ? Amount : throw new ArgumentOutOfRangeException(nameof(Amount));
}

public static class PatternDemo
{
    static double Area(Shape s) => s switch
    {
        Circle { Radius: <= 0 } => 0,
        Circle(var r) => Math.PI * r * r,                       // pozicionális minta
        Rect { W: var w, H: var h } when w == h => w * w,         // guard
        Rect(var w, var h) => w * h,
        Polygon { Points.Count: < 3 } => 0,                       // kiterjesztett property minta
        Polygon p => Math.Abs(p.Points.Select((a, i) =>                // Shoelace-képlet
                         { var b = p.Points[(i + 1) % p.Points.Count]; return a.X * b.Y - b.X * a.Y; }).Sum()) / 2,
        _ => throw new ArgumentException("Ismeretlen alakzat", nameof(s))
    };

    // Lista minták (C# 11)
    static string Describe(int[] xs) => xs switch
    {
        [] => "üres",
        [var only] => $"egy elem: {only}",
        [var first, .., var last] when first == last => "azonos végek",
        [_, _, ..] => $"{xs.Length} elem"
    };

    // Tuple + relációs és logikai minták
    static string Shipping(decimal total, bool premium) => (total, premium) switch
    {
        (_, true) => "ingyenes",
        ( >= 50m, _) => "ingyenes",
        ( > 0m and < 50m, _) => "1500 Ft",
        _ => "érvénytelen"
    };

    public static void Main()
    {
        Shape[] shapes = { new Circle(1), new Rect(2, 2), new Polygon(new[] { (0.0, 0.0), (4.0, 0.0), (0.0, 3.0) }) };
        foreach (var s in shapes) Console.WriteLine($"{s.GetType().Name}: {Area(s):F2}");

        var price = new Money(10m, "EUR");
        var discounted = price with { Amount = 8m };            // másolat, az eredeti nem változik
        Console.WriteLine(price == new Money(10m, "EUR"));      // True — érték alapú egyenlőség
        Console.WriteLine(discounted);
        Console.WriteLine(Describe(new[] { 1, 2, 1 }));          // azonos végek
        Console.WriteLine(Shipping(30m, false));
    }
}
```

## Nullable reference types
<!-- q: Hogyan kerüljem el a NullReferenceException-t a nullable reference types funkcióval? -->
<!-- tags: nullable, nrt, null safety, notnullwhen, required, null-forgiving -->

A `<Nullable>enable</Nullable>` bekapcsolásával a `string` jelentése „nem null”, a `string?` pedig „lehet null”, és a fordító statikus folyamatelemzéssel figyelmeztet a lehetséges null-dereferenciára (CS8602) és a null hozzárendelésre. A `[NotNullWhen]`, `[NotNullIfNotNull]`, `[MemberNotNull]` attribútumokkal az API-k szemantikáját írod le a fordítónak, a `required` taggal kötelezővé teszed az inicializálást. Fontos: ez csak fordítási idejű ellenőrzés — futásidőben a null ugyanúgy bejöhet (reflexió, JSON, régi könyvtár), a `!` operátor pedig csak elnémítja a figyelmeztetést.

```csharp
#nullable enable
using System;
using System.Collections.Generic;
using System.Diagnostics.CodeAnalysis;

public sealed class Customer
{
    public required string Name { get; init; }   // kötelező beállítani létrehozáskor
    public string? Email { get; init; }          // lehet null — ellenőrizni kell
    public Address? Address { get; init; }
}

public sealed record Address(string City, string? Zip);

public static class CustomerService
{
    private static readonly Dictionary<string, Customer> Db = new()
    {
        ["c1"] = new Customer { Name = "Példa Kft.", Email = "info@example.com", Address = new("Szeged", null) }
    };

    // true visszatérésnél a fordító tudja, hogy a customer nem null
    public static bool TryGet(string id, [NotNullWhen(true)] out Customer? customer)
        => Db.TryGetValue(id, out customer);

    // csak akkor ad nullt, ha a bemenet is null
    [return: NotNullIfNotNull(nameof(input))]
    public static string? Normalize(string? input) => input?.Trim().ToLowerInvariant();

    public static string ZipOrDefault(Customer c) => c.Address?.Zip ?? "ismeretlen";

    public static void Main()
    {
        if (TryGet("c1", out var c))
        {
            Console.WriteLine(c.Name.Length);         // nincs figyelmeztetés
            // Console.WriteLine(c.Email.Length);     // CS8602: lehetséges null dereferencia
            if (c.Email is { Length: > 0 } email)     // mintával szűkítjük a típust
                Console.WriteLine(Normalize(email));
            Console.WriteLine(ZipOrDefault(c));
        }

        string? maybe = Environment.GetEnvironmentVariable("PELDA_NEM_LETEZO_VALTOZO");
        string value = maybe ?? "alapértelmezett";   // vagy: maybe ?? throw new InvalidOperationException(...)
        Console.WriteLine(value);
    }
}
```

## Delegate-ek és események
<!-- q: Hogyan működnek a delegate-ek és az eventek C#-ban? -->
<!-- tags: delegate, event, func, action, eventhandler, multicast, memory leak -->

A delegate típusbiztos függvényreferencia; a beépített `Func<>`/`Action<>` a legtöbb esetet lefedi, és multicast: több metódust is hívhat sorban. Az `event` kulcsszó a delegate-et úgy védi, hogy kívülről csak feliratkozni (`+=`) és leiratkozni (`-=`) lehessen, meghívni csak a tulajdonos osztály tudja. Konvenció a `(object sender, TEventArgs e)` szignatúra és az `EventHandler<T>`. A klasszikus buktató a memóriaszivárgás: a hosszú életű publisher eseménye életben tartja a feliratkozót, ezért iratkozz le (lambdánál tárold el a delegate-et).

```csharp
using System;
using System.Collections.Generic;

public sealed class PriceChangedEventArgs : EventArgs
{
    public PriceChangedEventArgs(decimal oldPrice, decimal newPrice) => (OldPrice, NewPrice) = (oldPrice, newPrice);
    public decimal OldPrice { get; }
    public decimal NewPrice { get; }
}

public sealed class Product
{
    private decimal _price;
    public string Sku { get; }
    public Product(string sku, decimal price) => (Sku, _price) = (sku, price);

    // Kívülről csak += / -= ; meghívni csak ez az osztály tudja
    public event EventHandler<PriceChangedEventArgs>? PriceChanged;

    public decimal Price
    {
        get => _price;
        set
        {
            if (value == _price) return;
            var old = _price;
            _price = value;
            PriceChanged?.Invoke(this, new PriceChangedEventArgs(old, value)); // szálbiztos null-ellenőrzés
        }
    }
}

public static class DelegateDemo
{
    // Magasabb rendű függvény: lépések láncolása egyetlen Func-ká
    static Func<decimal, decimal> Compose(params Func<decimal, decimal>[] steps) => x =>
    {
        foreach (var step in steps) x = step(x);
        return x;
    };

    public static void Main()
    {
        var p = new Product("SKU-1", 100m);

        // Leiratkozáshoz el kell tárolni a delegate-et
        EventHandler<PriceChangedEventArgs> logger = (s, e) =>
            Console.WriteLine($"{((Product)s!).Sku}: {e.OldPrice} -> {e.NewPrice}");
        p.PriceChanged += logger;

        var history = new List<decimal>();
        p.PriceChanged += (_, e) => history.Add(e.NewPrice);   // multicast: második feliratkozó

        var pricing = Compose(x => x * 1.27m, x => Math.Round(x, 0), x => x - 1m); // ÁFA, kerekítés, „…99” ár
        p.Price = pricing(p.Price);
        p.PriceChanged -= logger;
        p.Price = 50m;                                          // a logger már nem fut

        Console.WriteLine(string.Join(", ", history));          // 126, 50
    }
}
```

## Reflexió és source generatorok
<!-- q: Mikor használjak reflexiót, és mikor source generatort C#-ban? -->
<!-- tags: reflection, attributes, source generators, roslyn, iincrementalgenerator, aot, trimming -->

A reflexió futásidőben vizsgálja a típusokat, attribútumokat és tagokat (`GetProperties`, `GetCustomAttribute`), ami rugalmas (szerializálók, DI, ORM), de lassú, és nem barátja a trimmingnek és a Native AOT-nak. A source generator (Roslyn `IIncrementalGenerator`) fordításkor elemzi a kódot és új C# forrást ad hozzá, így ugyanaz a funkció reflexió nélkül, gyorsan és AOT-kompatibilisen működik — ezt teszi a `System.Text.Json` és a `LoggerMessage` generátora is. A generátor `netstandard2.0` projektben él, analyzerként hivatkozod, és a generált kódnak `partial` osztályra van szüksége.

```csharp
using System;
using System.Linq;
using System.Reflection;

[AttributeUsage(AttributeTargets.Property)]
public sealed class MaskAttribute : Attribute { }

public sealed class LoginRequest
{
    public string User { get; set; } = "";
    [Mask] public string Password { get; set; } = "";
}

public static class ReflectionDemo
{
    // Futásidejű bejárás — ismételt hívásnál cache-eld a PropertyInfo tömböt!
    public static string Dump(object obj)
    {
        var props = obj.GetType().GetProperties(BindingFlags.Public | BindingFlags.Instance);
        return string.Join(", ", props.Select(p =>
            $"{p.Name}={(p.GetCustomAttribute<MaskAttribute>() is null ? p.GetValue(obj) : "***")}"));
    }

    public static void Main() =>
        Console.WriteLine(Dump(new LoginRequest { User = "demo", Password = "nem-valodi" }));
}
```

```csharp
// Külön netstandard2.0 projekt, NuGet: Microsoft.CodeAnalysis.CSharp
// Fogyasztó: <ProjectReference Include="..." OutputItemType="Analyzer" ReferenceOutputAssembly="false" />
using System.Linq;
using System.Text;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Text;

[Generator]
public sealed class DumpGenerator : IIncrementalGenerator
{
    public void Initialize(IncrementalGeneratorInitializationContext context)
    {
        // Csak a [GenerateDump] attribútumú osztályok — inkrementálisan, cache-elve
        var classes = context.SyntaxProvider.ForAttributeWithMetadataName(
            "Demo.GenerateDumpAttribute",
            predicate: static (node, _) => node is ClassDeclarationSyntax,
            transform: static (ctx, _) => (INamedTypeSymbol)ctx.TargetSymbol);

        context.RegisterSourceOutput(classes, static (spc, type) =>
        {
            var props = type.GetMembers().OfType<IPropertySymbol>()
                .Where(p => p.DeclaredAccessibility == Accessibility.Public && !p.IsStatic);

            var sb = new StringBuilder();
            sb.AppendLine($"namespace {type.ContainingNamespace.ToDisplayString()};");
            sb.AppendLine($"partial class {type.Name}");
            sb.AppendLine("{");
            sb.AppendLine("    public string Dump() => string.Join(\", \", new string[] {");
            foreach (var p in props)
            {
                bool masked = p.GetAttributes().Any(a => a.AttributeClass?.Name == "MaskAttribute");
                // Generált sor: "Password=***"  vagy  $"User={User}"
                sb.AppendLine(masked ? $"        \"{p.Name}=***\"," : $"        $\"{p.Name}={{{p.Name}}}\",");
            }
            sb.AppendLine("    });");
            sb.AppendLine("}");
            spc.AddSource($"{type.Name}.Dump.g.cs", SourceText.From(sb.ToString(), Encoding.UTF8));
        });
    }
}
```

## Dependency injection és élettartamok
<!-- q: Hogyan működik a dependency injection .NET-ben, és mi a különbség a Singleton, Scoped és Transient között? -->
<!-- tags: dependency injection, di, ioc, servicecollection, singleton, scoped, transient, options -->

A `Microsoft.Extensions.DependencyInjection` konténerben interfész → implementáció párokat regisztrálsz, és a konstruktor-injektálás miatt az osztályok lazán csatoltak és tesztelhetők. Az élettartamok: Singleton (egy példány az alkalmazásnak, legyen szálbiztos), Scoped (egy scope-on, például egy HTTP-kérésen belül egy), Transient (minden feloldáskor új). A legfontosabb buktató a „captive dependency”: a singleton ne függjön scoped szolgáltatástól (pl. `DbContext`), mert az így örökké élne — a `ValidateScopes` ezt elkapja. Konfigurációra az Options minta (`IOptions<T>`) való.

```csharp
// NuGet: Microsoft.Extensions.DependencyInjection, Microsoft.Extensions.Options
using System;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;

public sealed class SmtpOptions
{
    public string Host { get; set; } = "localhost";
    public int Port { get; set; } = 25;
}

public interface IClock { DateTimeOffset Now { get; } }
public sealed class SystemClock : IClock { public DateTimeOffset Now => DateTimeOffset.UtcNow; }

public interface IEmailSender { void Send(string to, string subject); }

// Nem küld valódi levelet, csak kiírja — biztonságos demó
public sealed class ConsoleEmailSender : IEmailSender
{
    private readonly SmtpOptions _opt;
    private readonly IClock _clock;
    public ConsoleEmailSender(IOptions<SmtpOptions> opt, IClock clock) => (_opt, _clock) = (opt.Value, clock);
    public void Send(string to, string subject) =>
        Console.WriteLine($"[{_clock.Now:HH:mm:ss}] {_opt.Host}:{_opt.Port} → {to}: {subject}");
}

public sealed class OrderService
{
    private readonly IEmailSender _email;
    public Guid InstanceId { get; } = Guid.NewGuid();
    public OrderService(IEmailSender email) => _email = email;
    public void Place(string customerEmail) => _email.Send(customerEmail, "Rendelés visszaigazolva");
}

public static class DiDemo
{
    public static void Main()
    {
        var services = new ServiceCollection();
        services.AddSingleton<IClock, SystemClock>();              // egy példány az app életére
        services.AddScoped<OrderService>();                        // scope-onként egy
        services.AddTransient<IEmailSender, ConsoleEmailSender>(); // minden feloldáskor új
        services.Configure<SmtpOptions>(o => { o.Host = "smtp.example.test"; o.Port = 2525; });

        // ValidateScopes + ValidateOnBuild: a hibás regisztrációk már induláskor kiderülnek
        using var provider = services.BuildServiceProvider(new ServiceProviderOptions { ValidateScopes = true, ValidateOnBuild = true });

        using (var scope = provider.CreateScope())
        {
            var a = scope.ServiceProvider.GetRequiredService<OrderService>();
            var b = scope.ServiceProvider.GetRequiredService<OrderService>();
            Console.WriteLine(a.InstanceId == b.InstanceId);       // True — ugyanaz a scope
            a.Place("vevo@example.com");
        }

        using var scope2 = provider.CreateScope();
        Console.WriteLine(scope2.ServiceProvider.GetRequiredService<OrderService>().InstanceId); // új példány
    }
}
```

## ASP.NET Core minimal API és middleware
<!-- q: Hogyan írjak REST API-t ASP.NET Core minimal API-val és saját middleware-rel? -->
<!-- tags: asp.net core, minimal api, middleware, pipeline, endpoint filter, problemdetails, rest -->

A minimal API-ban a végpontokat közvetlenül a `WebApplication`-ön képezed le (`MapGet`, `MapPost`), a paraméterek a route-ból, query-ből, body-ból és a DI-ből automatikusan kötődnek. A kérés egy middleware-láncon (pipeline) halad át, ahol a sorrend számít: a kivételkezelő legyen elöl, az autentikáció az autorizáció előtt; egy middleware az `await next()` előtt és után is dolgozhat. A `MapGroup` közös prefixet és filtereket ad, a `ProblemDetails` szabványos hibaválaszokat. Singleton szolgáltatás több kérésből párhuzamosan érhető el, ezért legyen szálbiztos.

```csharp
// dotnet new web → Program.cs (ImplicitUsings bekapcsolva)
using System.Collections.Concurrent;
using System.Diagnostics;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<TodoStore>();
builder.Services.AddProblemDetails();                 // RFC 7807 hibaválaszok

var app = builder.Build();
app.UseExceptionHandler();                            // kivétel → ProblemDetails JSON

// Saját inline middleware: időmérés és kérésazonosító
app.Use(async (ctx, next) =>
{
    var sw = Stopwatch.StartNew();
    ctx.Response.Headers["X-Request-Id"] = ctx.TraceIdentifier;
    await next(ctx);                                  // a pipeline többi része
    app.Logger.LogInformation("{Method} {Path} → {Status} ({Ms} ms)",
        ctx.Request.Method, ctx.Request.Path, ctx.Response.StatusCode, sw.ElapsedMilliseconds);
});

var todos = app.MapGroup("/api/todos");

todos.MapGet("/", (TodoStore store) => store.All());
todos.MapGet("/{id:int}", (int id, TodoStore store) =>
    store.Get(id) is { } t ? Results.Ok(t) : Results.NotFound());

todos.MapPost("/", (CreateTodo dto, TodoStore store) =>
{
    if (string.IsNullOrWhiteSpace(dto.Title))
        return Results.ValidationProblem(new Dictionary<string, string[]> { ["title"] = new[] { "Kötelező mező" } });
    var created = store.Add(dto.Title);
    return Results.Created($"/api/todos/{created.Id}", created);
});

todos.MapDelete("/{id:int}", (int id, TodoStore store) =>
    store.Remove(id) ? Results.NoContent() : Results.NotFound());

app.Run();

public record CreateTodo(string Title);
public record Todo(int Id, string Title, bool Done);

// Szálbiztos memóriabeli tároló
public sealed class TodoStore
{
    private readonly ConcurrentDictionary<int, Todo> _items = new();
    private int _nextId;
    public IEnumerable<Todo> All() => _items.Values.OrderBy(t => t.Id);
    public Todo? Get(int id) => _items.GetValueOrDefault(id);
    public Todo Add(string title)
    {
        var t = new Todo(Interlocked.Increment(ref _nextId), title, false);
        _items[t.Id] = t;
        return t;
    }
    public bool Remove(int id) => _items.TryRemove(id, out _);
}
```

## Entity Framework Core: tracking, migrációk, N+1
<!-- q: Hogyan kerüljem el az N+1 problémát és mikor kapcsoljam ki a change trackinget EF Core-ban? -->
<!-- tags: ef core, entity framework, orm, migrations, n+1, include, asnotracking, change tracking -->

Az EF Core a LINQ lekérdezéseket SQL-re fordítja, a betöltött entitásokat pedig alapból követi (change tracking), így a `SaveChanges` csak a módosított oszlopokat írja vissza. Csak olvasó lekérdezésnél az `AsNoTracking()` vagy egy `Select` projekció jelentősen gyorsabb. Az N+1 probléma akkor jelentkezik, ha egy listán végigmenve elemenként tölt be kapcsolt adatot (lazy loading): ezt `Include`-dal (nagy gráfnál `AsSplitQuery`-vel) vagy projekcióval kerülöd el. A séma változásait migrációk kezelik (`dotnet ef migrations add`, `database update`); mindig nézd meg a generált SQL-t (`LogTo`).

```csharp
// NuGet: Microsoft.EntityFrameworkCore.Sqlite, Microsoft.EntityFrameworkCore.Design
// Migráció: dotnet ef migrations add Init   →   dotnet ef database update
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;

public class Blog
{
    public int Id { get; set; }
    public string Title { get; set; } = "";
    public List<Post> Posts { get; set; } = new();
}

public class Post
{
    public int Id { get; set; }
    public string Content { get; set; } = "";
    public int BlogId { get; set; }
}

public class AppDb : DbContext
{
    public DbSet<Blog> Blogs => Set<Blog>();
    public DbSet<Post> Posts => Set<Post>();

    protected override void OnConfiguring(DbContextOptionsBuilder o) =>
        o.UseSqlite("Data Source=demo.db")
         .LogTo(Console.WriteLine, LogLevel.Information);     // lásd a generált SQL-t
}

public static class EfDemo
{
    public static async Task RunAsync()
    {
        await using var db = new AppDb();
        // N+1 HIBA (lazy loadinggal): 1 lekérdezés a blogokra + blogonként 1 a posztokra
        // foreach (var b in db.Blogs) Console.WriteLine(b.Posts.Count);

        // Helyes 1: eager loading, tracking nélkül
        var blogs = await db.Blogs
            .Include(b => b.Posts)
            .AsSplitQuery()          // nagy Include-nál elkerüli a "cartesian explosion"-t
            .AsNoTracking()          // csak olvasunk
            .ToListAsync();

        // Helyes 2: projekció — csak a szükséges oszlopok, egyetlen SQL
        var stats = await db.Blogs
            .Select(b => new { b.Title, PostCount = b.Posts.Count })
            .ToListAsync();
        stats.ForEach(s => Console.WriteLine($"{s.Title}: {s.PostCount}"));

        // Tracking: a módosítást a SaveChanges menti
        var first = await db.Blogs.FirstOrDefaultAsync(b => b.Title.StartsWith("Demo"));
        if (first is not null)
        {
            first.Title += " (frissítve)";
            await db.SaveChangesAsync();   // UPDATE csak a Title oszlopra
        }

        // Tömeges frissítés betöltés nélkül (EF Core 7+)
        await db.Posts.Where(p => p.Content == "")
            .ExecuteUpdateAsync(s => s.SetProperty(p => p.Content, "(üres)"));
    }
}
```

## WPF és az MVVM minta
<!-- q: Hogyan építsek WPF alkalmazást MVVM mintával? -->
<!-- tags: wpf, mvvm, data binding, inotifypropertychanged, icommand, xaml, observablecollection -->

Az MVVM-ben a View (XAML) csak data bindinggal kapcsolódik a ViewModelhez, amely nem ismeri a UI-t, így a logika unit-tesztelhető. A ViewModel az `INotifyPropertyChanged`-del jelzi a változást, a gyűjtemények `ObservableCollection<T>`-ként frissítik a listákat, a gombok pedig `ICommand`-hoz kötődnek, amelynek `CanExecute`-ja automatikusan engedélyez/tilt. Éles projektben a `CommunityToolkit.Mvvm` (`[ObservableProperty]`, `[RelayCommand]`) legenerálja ezt a boilerplate-et. Buktató: a UI elemeket csak a UI-szálról szabad módosítani (async után a `Dispatcher` vagy a SynchronizationContext gondoskodik erről).

```csharp
using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows.Input;

public abstract class ObservableObject : INotifyPropertyChanged
{
    public event PropertyChangedEventHandler? PropertyChanged;

    // CallerMemberName: a property neve automatikusan kerül ide → nincs elgépelt string
    protected bool SetProperty<T>(ref T field, T value, [CallerMemberName] string? name = null)
    {
        if (Equals(field, value)) return false;
        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
        return true;
    }
}

public sealed class RelayCommand : ICommand
{
    private readonly Action _execute;
    private readonly Func<bool> _canExecute;
    public RelayCommand(Action execute, Func<bool>? canExecute = null)
        => (_execute, _canExecute) = (execute, canExecute ?? (() => true));
    public event EventHandler? CanExecuteChanged;
    public bool CanExecute(object? parameter) => _canExecute();
    public void Execute(object? parameter) => _execute();
    public void RaiseCanExecuteChanged() => CanExecuteChanged?.Invoke(this, EventArgs.Empty);
}

public sealed class TodoViewModel : ObservableObject
{
    private string _newTitle = "";
    public ObservableCollection<string> Items { get; } = new();   // a ListBox magától frissül
    public RelayCommand AddCommand { get; }

    public TodoViewModel() => AddCommand = new RelayCommand(Add, () => !string.IsNullOrWhiteSpace(NewTitle));

    public string NewTitle
    {
        get => _newTitle;
        set { if (SetProperty(ref _newTitle, value)) AddCommand.RaiseCanExecuteChanged(); }
    }

    private void Add()
    {
        Items.Add(NewTitle.Trim());
        NewTitle = "";
    }
}
```

```xml
<!-- MainWindow.xaml — a code-behind konstruktorában: DataContext = new TodoViewModel(); -->
<Window x:Class="TodoApp.MainWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="Teendők" Width="360" Height="420">
  <DockPanel Margin="12">
    <StackPanel DockPanel.Dock="Top" Orientation="Horizontal">
      <!-- UpdateSourceTrigger=PropertyChanged: minden leütésnél frissül a ViewModel -->
      <TextBox Width="240" Text="{Binding NewTitle, UpdateSourceTrigger=PropertyChanged}" />
      <Button Content="Hozzáad" Margin="8,0,0,0" Command="{Binding AddCommand}" />
    </StackPanel>
    <ListBox ItemsSource="{Binding Items}" Margin="0,12,0,0" />
  </DockPanel>
</Window>
```

## .NET MAUI alapok
<!-- q: Hogyan kezdjek el egy keresztplatformos mobil/asztali alkalmazást .NET MAUI-val? -->
<!-- tags: maui, cross-platform, mobile, android, ios, dependency injection, xamarin -->

A .NET MAUI a Xamarin.Forms utódja: egyetlen projektből Android, iOS, macOS (Catalyst) és Windows alkalmazás készül, natív vezérlőkre leképezett közös UI-val. Belépési pontja a `MauiProgram.CreateMauiApp`, ahol ugyanaz a DI és logging rendszer van, mint ASP.NET Core-ban; az oldalakat és ViewModeleket regisztrálva a konstruktor-injektálás oldalakra is működik. A platformfüggő kód a `Platforms/<platform>` mappákba vagy `#if ANDROID` blokkokba kerül, az eszköz-API-k (hálózat, szenzorok, fájlok) közös absztrakciókon érhetők el. Buktató: a UI-t csak a fő szálon módosítsd (`MainThread.BeginInvokeOnMainThread`), és a platformok jogosultságait (manifest, Info.plist) külön kell beállítani.

```csharp
// MauiProgram.cs — dotnet new maui sablon alapján
using Microsoft.Extensions.Logging;
using Microsoft.Maui;
using Microsoft.Maui.Controls;
using Microsoft.Maui.Hosting;
using Microsoft.Maui.Networking;

public static class MauiProgram
{
    public static MauiApp CreateMauiApp()
    {
        var builder = MauiApp.CreateBuilder();
        builder.UseMauiApp<App>();

        // Ugyanaz a DI, mint ASP.NET Core-ban
        builder.Services.AddSingleton<IConnectivity>(Connectivity.Current);
        builder.Services.AddTransient<StatusViewModel>();
        builder.Services.AddTransient<StatusPage>();
#if DEBUG
        builder.Logging.AddDebug();
#endif
        return builder.Build();
    }
}

public sealed class App : Application
{
    private readonly StatusPage _page;
    public App(StatusPage page) => _page = page;   // a DI adja az első oldalt
    protected override Window CreateWindow(IActivationState? state) => new Window(new NavigationPage(_page));
}

public sealed class StatusViewModel
{
    private readonly IConnectivity _net;
    public StatusViewModel(IConnectivity net) => _net = net;   // tesztben mockolható
    public string Status => _net.NetworkAccess == NetworkAccess.Internet ? "Online" : "Offline mód — cache-elt adatok";
}

// Oldal kódból (XAML is lehetne); a BindingContext a ViewModel
public sealed class StatusPage : ContentPage
{
    public StatusPage(StatusViewModel vm)
    {
        BindingContext = vm;
        var label = new Label { FontSize = 20, HorizontalOptions = LayoutOptions.Center };
        label.SetBinding(Label.TextProperty, nameof(StatusViewModel.Status));
        Content = new VerticalStackLayout { Padding = 24, Spacing = 12, Children = { label } };
#if ANDROID
        Title = "Állapot (Android)";               // platformspecifikus kód
#else
        Title = "Állapot";
#endif
    }
}
```

## Unit tesztelés xUnit-tal
<!-- q: Hogyan írjak unit teszteket xUnit-tal és mockokkal C#-ban? -->
<!-- tags: xunit, unit testing, theory, fact, mocking, nsubstitute, arrange act assert -->

Az xUnit minden teszthez új tesztosztály-példányt hoz létre, így a konstruktor a setup, az `IDisposable` a teardown, a megosztott drága erőforrásokra pedig `IClassFixture<T>` való. A `[Fact]` paraméter nélküli teszt, a `[Theory]` + `[InlineData]`/`[MemberData]` adatvezérelt. A függőségeket interfészen keresztül kapja a tesztelt kód, ezeket mock könyvtárral (NSubstitute, Moq) helyettesíted, és az interakciót is ellenőrizheted. Buktatók: async tesztnél `async Task` legyen (ne `async void`), és ne függjön a teszt a valós időtől, hálózattól vagy a futtatási sorrendtől.

```csharp
// NuGet: xunit, xunit.runner.visualstudio, Microsoft.NET.Test.Sdk, NSubstitute
using System;
using System.Threading.Tasks;
using NSubstitute;
using Xunit;

public interface IRateProvider { Task<decimal> GetRateAsync(string from, string to); }

public sealed class CurrencyConverter
{
    private readonly IRateProvider _rates;
    public CurrencyConverter(IRateProvider rates) => _rates = rates;

    public async Task<decimal> ConvertAsync(decimal amount, string from, string to)
    {
        if (amount < 0) throw new ArgumentOutOfRangeException(nameof(amount));
        if (from == to) return amount;
        return Math.Round(amount * await _rates.GetRateAsync(from, to), 2);
    }
}

public class CurrencyConverterTests
{
    private readonly IRateProvider _rates = Substitute.For<IRateProvider>();
    private readonly CurrencyConverter _sut;

    // Minden teszt új példányt kap → a konstruktor a setup
    public CurrencyConverterTests() => _sut = new CurrencyConverter(_rates);

    [Theory]
    [InlineData(100, 400, 40000)]
    [InlineData(0.5, 400, 200)]
    [InlineData(1.005, 1, 1)]        // Math.Round alapból banker's rounding (ToEven)
    public async Task Convert_UsesRate(decimal amount, decimal rate, decimal expected)
    {
        _rates.GetRateAsync("EUR", "HUF").Returns(rate);              // Arrange
        var result = await _sut.ConvertAsync(amount, "EUR", "HUF");   // Act
        Assert.Equal(expected, result);                               // Assert
    }

    [Fact]
    public async Task SameCurrency_DoesNotCallProvider()
    {
        var result = await _sut.ConvertAsync(10m, "EUR", "EUR");
        Assert.Equal(10m, result);
        await _rates.DidNotReceiveWithAnyArgs().GetRateAsync(default!, default!);
    }

    [Fact]
    public Task NegativeAmount_Throws() =>
        Assert.ThrowsAsync<ArgumentOutOfRangeException>(() => _sut.ConvertAsync(-1m, "EUR", "HUF"));
}
```

## Teljesítménymérés BenchmarkDotNet-tel
<!-- q: Hogyan mérjem pontosan egy C# kód teljesítményét és allokációit? -->
<!-- tags: benchmarkdotnet, performance, profiling, memorydiagnoser, allocations, stringbuilder -->

A `Stopwatch`-alapú mérés félrevezető (JIT-bemelegedés, tiered compilation, GC-zaj), ezért mikrobenchmarkra a BenchmarkDotNet a szabvány: külön folyamatban, bemelegítéssel, több iterációval és statisztikával mér. A `[MemoryDiagnoser]` az allokációt és a GC-ket is mutatja, ami .NET-ben gyakran fontosabb a nyers időnél. Mindig Release módban, debugger nélkül futtasd, és az eredményt add vissza a metódusból, különben a JIT kioptimalizálhatja. Éles rendszer vizsgálatára a `dotnet-counters`, `dotnet-trace` és `dotnet-gcdump` eszközök valók.

```csharp
// NuGet: BenchmarkDotNet — futtatás: dotnet run -c Release
using System;
using System.Linq;
using System.Text;
using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Running;

[MemoryDiagnoser]                // allokációk és GC-k mérése
[RankColumn]
public class StringJoinBenchmarks
{
    private string[] _parts = Array.Empty<string>();

    [Params(10, 1000)]           // minden értékre külön mérés
    public int N;

    [GlobalSetup]
    public void Setup() => _parts = Enumerable.Range(0, N).Select(i => i.ToString()).ToArray();

    [Benchmark(Baseline = true)]
    public string Concat()
    {
        var s = "";
        foreach (var p in _parts) s += p + ",";     // O(n²) másolás
        return s;
    }

    [Benchmark]
    public string Builder()
    {
        var sb = new StringBuilder(_parts.Length * 4);   // előre méretezve
        foreach (var p in _parts) sb.Append(p).Append(',');
        return sb.ToString();
    }

    [Benchmark]
    public string Join() => string.Join(',', _parts);
}

public static class Program
{
    // A BenchmarkSwitcher parancssori szűrést is ad: --filter *Join*
    public static void Main(string[] args) =>
        BenchmarkSwitcher.FromAssembly(typeof(Program).Assembly).Run(args);
}
```
