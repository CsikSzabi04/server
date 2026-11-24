# Java
<!-- tech: java -->
<!-- aliases: java se, jdk, openjdk, jvm, j2ee, jakarta ee -->

A Java statikusan és erősen típusos, osztályalapú, objektumorientált nyelv, amely bájtkódra fordul és a JVM-en fut (HotSpot JIT, adaptív optimalizálás); a memóriát szemétgyűjtő (GC) kezeli. A Java 8 óta lambdák és streamek, a 17/21/25 LTS-ek óta recordok, sealed típusok, pattern matching és virtuális szálak teszik modernné. Fő terepe a nagyvállalati backend (Spring Boot, Jakarta EE), a big data (Kafka, Spark), a pénzügyi rendszerek és részben az Android. Erőssége a hatalmas ökoszisztéma, a kiforrott eszközök, a hosszú távon kiváló teljesítmény és a visszafelé kompatibilitás; gyengébb a bőbeszédűség, a lassabb indulás és a nagyobb memóriaigény (ezen GraalVM native image és CDS segít), ezért apró CLI-eszközökhöz vagy rövid életű serverless függvényekhez nem mindig ideális.

## JVM memóriamodell és szemétgyűjtés
<!-- q: Hogyan kezeli a JVM a memóriát és hogyan működik a garbage collector? -->
<!-- tags: jvm, heap, stack, metaspace, gc, g1, zgc, weakreference, cleaner, memory leak -->

A JVM memóriája szálanként külön stackből (lokális változók, hívási keretek), közös heapből (objektumok, generációkra bontva: young/Eden+survivor és old) és metaspace-ből (osztálymetaadatok, natív memóriában) áll. A GC az elérhetetlen objektumokat gyűjti be a GC-gyökerektől (stack, statikus mezők) indulva; az alapértelmezett G1 régiókra bontott, szünetidő-célos gyűjtő, a ZGC (generációs a 21+ verziókban) milliszekundum alatti szüneteket ad nagy heapen is. Memóriaszivárgás Javában is van: statikus kollekciókban, le nem iratkozott listenerekben vagy ThreadLocal-ban felejtett referenciák. A `System.gc()` csak javaslat, a `finalize()` elavult – helyette try-with-resources és `Cleaner` kell.

```java
import java.lang.management.ManagementFactory;
import java.lang.ref.Cleaner;
import java.lang.ref.WeakReference;
import java.util.Map;
import java.util.WeakHashMap;

// Futtatás pl.: java -Xms256m -Xmx512m -XX:+UseZGC -Xlog:gc MemoryDemo.java
public class MemoryDemo {
    // Cleaner: a finalize() biztonságos utódja natív erőforrások felszabadítására
    private static final Cleaner CLEANER = Cleaner.create();

    static final class NativeBuffer implements AutoCloseable {
        // A State NEM hivatkozhat vissza a NativeBuffer-re, különben sosem válna elérhetetlenné
        private record State(long address) implements Runnable {
            @Override public void run() { System.out.println("Natív memória felszabadítva: " + address); }
        }
        private final Cleaner.Cleanable cleanable;
        NativeBuffer(long address) { this.cleanable = CLEANER.register(this, new State(address)); }
        @Override public void close() { cleanable.clean(); } // determinisztikus takarítás
    }

    public static void main(String[] args) throws InterruptedException {
        var mem = ManagementFactory.getMemoryMXBean();
        System.out.println("Heap: " + mem.getHeapMemoryUsage());
        System.out.println("Non-heap (metaspace, code cache): " + mem.getNonHeapMemoryUsage());

        // WeakReference: a GC begyűjtheti, ha nincs rá erős hivatkozás
        Object payload = new byte[10 * 1024 * 1024];
        WeakReference<Object> weak = new WeakReference<>(payload);
        payload = null;          // az egyetlen erős hivatkozás eldobása
        System.gc();             // csak javaslat, nem garancia!
        Thread.sleep(100);
        System.out.println("Weak referencia él még? " + (weak.get() != null));

        // WeakHashMap: gyengén hivatkozott kulcsok -> metaadat-cache szivárgás nélkül
        Map<Object, String> metadata = new WeakHashMap<>();
        Object key = new Object();
        metadata.put(key, "csatolt adat");
        key = null;
        System.gc();
        Thread.sleep(100);
        System.out.println("WeakHashMap mérete GC után: " + metadata.size());

        try (var buf = new NativeBuffer(0xCAFEL)) {
            System.out.println("Puffer használatban: " + buf);
        } // a close() itt lefuttatja a takarítást

        // Gyűjtőnkénti statisztika (pl. "G1 Young Generation", "ZGC Cycles")
        ManagementFactory.getGarbageCollectorMXBeans().forEach(gc ->
            System.out.printf("%s: %d gyűjtés, %d ms%n", gc.getName(), gc.getCollectionCount(), gc.getCollectionTime()));
    }
}
```

## Generikusok, wildcardok és variancia
<!-- q: Hogyan működnek a generikusok Javában, mi a PECS szabály és a type erasure? -->
<!-- tags: generics, wildcard, variance, pecs, type erasure, bounded types -->

A generikusok fordítási idejű típusbiztonságot adnak, de futásidőben a típusparaméterek törlődnek (type erasure): `List<String>` és `List<Integer>` ugyanaz az osztály, ezért nem lehet `new T()` vagy `instanceof List<String>`. A generikus típusok invariánsak (`List<Integer>` nem `List<Number>`), a varianciát a használat helyén wildcardokkal adjuk meg. A PECS szabály: Producer Extends (`? extends T`, amiből olvasunk), Consumer Super (`? super T`, amibe írunk). Ha futásidőben kell a típus, `Class<T>` tokent adunk át (típusbiztos heterogén konténer).

```java
import java.util.*;
import java.util.function.Function;

public class GenericsDemo {
    // Korlátos típusparaméter: T összehasonlítható önmagával vagy egy ősével
    static <T extends Comparable<? super T>> T max(Collection<? extends T> items) {
        Iterator<? extends T> it = items.iterator();
        T best = it.next();
        while (it.hasNext()) {
            T next = it.next();
            if (next.compareTo(best) > 0) best = next;
        }
        return best;
    }

    // PECS: a forrásból olvasunk (extends), a célba írunk (super)
    static <T> void copy(List<? extends T> src, List<? super T> dst) {
        for (T item : src) dst.add(item);
    }

    // Típusbiztos heterogén konténer: a Class<T> token túléli a type erasure-t
    static final class TypedRegistry {
        private final Map<Class<?>, Object> values = new HashMap<>();
        <T> void put(Class<T> type, T value) { values.put(type, type.cast(value)); }
        <T> Optional<T> get(Class<T> type) { return Optional.ofNullable(type.cast(values.get(type))); }
    }

    // Generikus Result típus map-pel; a sealed miatt a switch kimerítő
    sealed interface Result<T> permits Ok, Err {
        default <R> Result<R> map(Function<? super T, ? extends R> f) {
            return switch (this) {
                case Ok<T> ok -> new Ok<>(f.apply(ok.value()));
                case Err<T> err -> new Err<>(err.message());
            };
        }
    }
    record Ok<T>(T value) implements Result<T> {}
    record Err<T>(String message) implements Result<T> {}

    public static void main(String[] args) {
        List<Integer> ints = List.of(3, 9, 4);
        List<Number> numbers = new ArrayList<>();
        copy(ints, numbers);                 // Integer -> Number
        System.out.println(max(ints) + " " + numbers);
        // List<Number> bad = ints;          // fordítási hiba: a generikusok invariánsak

        TypedRegistry reg = new TypedRegistry();
        reg.put(String.class, "konfig");
        reg.put(Integer.class, 42);
        System.out.println(reg.get(Integer.class).orElse(0) + 1);

        Result<String> r = new Ok<>(21).map(x -> x * 2).map(String::valueOf);
        System.out.println(r);               // Ok[value=42]
    }
}
```

## Recordok, sealed osztályok és pattern matching
<!-- q: Hogyan használjam a recordokat, sealed interfészeket és a pattern matching switch-et? -->
<!-- tags: record, sealed, pattern matching, switch, record pattern, java 21, algebraic data types -->

A `record` immutábilis adathordozó: a fordító generálja a konstruktort, az accessorokat, az `equals`/`hashCode`/`toString`-et; validációt a kompakt konstruktorba írunk. A `sealed` interfész/osztály felsorolja a megengedett altípusait, így a fordító ismeri a teljes hierarchiát, és a `switch` default ág nélkül is kimerítő – új altípusnál fordítási hiba jelzi a kezeletlen helyeket. A Java 21 record patternjei egy lépésben ellenőrzik a típust és bontják szét a mezőket, a `when` guarddal feltételt adhatunk. Buktató: a record mezői csak sekélyen immutábilisak, ezért a kollekciókat `List.copyOf`-fal érdemes védeni.

```java
import java.util.List;

public class ShapesDemo {
    // Zárt hierarchia: algebrai adattípus Javában
    sealed interface Shape permits Circle, Rect, Group {}
    record Point(double x, double y) {}

    record Circle(Point center, double r) implements Shape {
        Circle { // kompakt konstruktor: validáció a mezők beállítása előtt
            if (r <= 0) throw new IllegalArgumentException("A sugár pozitív kell legyen: " + r);
        }
    }
    record Rect(Point topLeft, double w, double h) implements Shape {}
    record Group(List<Shape> children) implements Shape {
        Group { children = List.copyOf(children); } // védekező másolat -> valódi immutabilitás
    }

    // Pattern matching switch + record pattern: dekonstrukció és guard egyben
    static double area(Shape s) {
        return switch (s) {
            case Circle(Point c, double r) -> Math.PI * r * r;
            case Rect(Point p, double w, double h) when w == h -> w * w; // négyzet ág előbb
            case Rect(var p, var w, var h) -> w * h;
            case Group(var children) -> children.stream().mapToDouble(ShapesDemo::area).sum();
        }; // nincs default: a sealed miatt kimerítő
    }

    // Beágyazott record pattern instanceof-ban, majd switch null-kezeléssel
    static String describe(Object o) {
        if (o instanceof Circle(Point(double x, double y), double r) && x == 0 && y == 0) {
            return "origó középpontú kör, r=" + r;
        }
        return switch (o) {
            case null -> "null érték";
            case Shape s -> "alakzat: " + s.getClass().getSimpleName();
            case String str when str.isBlank() -> "üres szöveg";
            case String str -> "szöveg: " + str;
            default -> "ismeretlen: " + o;
        };
    }

    public static void main(String[] args) {
        Shape scene = new Group(List.of(
            new Circle(new Point(0, 0), 1),
            new Rect(new Point(1, 1), 2, 2),
            new Rect(new Point(5, 5), 2, 3)));
        System.out.printf("Össz terület: %.2f%n", area(scene));
        System.out.println(describe(new Circle(new Point(0, 0), 2)));
        System.out.println(describe(null));
        System.out.println(describe("  "));
    }
}
```

## Lambdák és funkcionális interfészek
<!-- q: Hogyan működnek a lambdák és a funkcionális interfészek Javában? -->
<!-- tags: lambda, functional interface, method reference, function composition, closure -->

A lambda egy funkcionális interfész (pontosan egy absztrakt metódus, SAM) példánya; a fordító `invokedynamic`-kal hozza létre, így nem keletkezik külön osztályfájl. A `java.util.function` csomag kész típusokat ad (`Function`, `Supplier`, `Predicate`, `UnaryOperator`, primitív változatok a boxing elkerülésére), a metódusreferencia (`String::trim`, `ArrayList::new`) a lambda tömör formája. A lambda csak effektíven final lokális változót zárhat le, és a beépített interfészek nem dobhatnak checked kivételt – ezt saját interfésszel és burkolással oldjuk meg. Saját interfészre tegyünk `@FunctionalInterface`-t, a kompozíciót default metódusok adják.

```java
import java.util.*;
import java.util.function.*;

public class FunctionalDemo {
    @FunctionalInterface
    interface Validator<T> {
        Optional<String> validate(T value); // hibaüzenet, ha érvénytelen

        // default metódus: kompozíció, nem rontja el a SAM jelleget
        default Validator<T> and(Validator<? super T> other) {
            return v -> validate(v).or(() -> other.validate(v));
        }
        static <T> Validator<T> of(Predicate<T> ok, String msg) {
            return v -> ok.test(v) ? Optional.empty() : Optional.of(msg);
        }
    }

    // Checked kivételt dobó függvény burkolása (a Function nem engedi a checked kivételt)
    @FunctionalInterface
    interface ThrowingFunction<T, R> { R apply(T t) throws Exception; }

    static <T, R> Function<T, R> unchecked(ThrowingFunction<T, R> f) {
        return t -> {
            try { return f.apply(t); }
            catch (Exception e) { throw new RuntimeException(e); }
        };
    }

    public static void main(String[] args) {
        Validator<String> username = Validator.<String>of(s -> !s.isBlank(), "üres név")
            .and(Validator.of(s -> s.length() <= 16, "túl hosszú"))
            .and(Validator.of(s -> s.matches("[a-z0-9_]+"), "tiltott karakter"));
        System.out.println(username.validate("auri_dev"));   // Optional.empty
        System.out.println(username.validate("Rossz Név!")); // Optional[tiltott karakter]

        // Kompozíció és metódusreferenciák
        Function<String, String> trim = String::trim;
        Function<String, Integer> length = trim.andThen(String::length);
        System.out.println(length.apply("  hello  "));      // 5

        Supplier<List<String>> factory = ArrayList::new;     // konstruktor-referencia
        UnaryOperator<String> upper = String::toUpperCase;
        BinaryOperator<Integer> add = Integer::sum;
        List<String> list = factory.get();
        list.add(upper.apply("lambda"));
        System.out.println(list + " " + add.apply(2, 3));

        // Closure: a base effektíven final; base++ fordítási hibát okozna
        int base = 10;
        IntUnaryOperator addBase = x -> x + base;            // primitív: nincs boxing
        System.out.println(addBase.applyAsInt(5));

        Function<String, Integer> parse = unchecked(Integer::parseInt);
        System.out.println(parse.apply("123"));
    }
}
```

## Stream API és Collectors
<!-- q: Hogyan dolgozzak fel kollekciókat Stream API-val és Collectors-szal? -->
<!-- tags: stream, collectors, groupingby, partitioningby, tomap, teeing, flatmap, parallel stream -->

A Stream deklaratív, lusta adatfeldolgozó lánc: a köztes műveletek (`filter`, `map`, `flatMap`) csak a terminális műveletnél (`collect`, `count`, `toList`) futnak le, elemenként, köztes kollekció nélkül. A `Collectors` adja az aggregációkat: `groupingBy` downstream collectorral, `partitioningBy`, `toMap` merge-függvénnyel (nélküle duplikált kulcsnál `IllegalStateException`!), `teeing` két collector kombinálására. A primitív streamek (`IntStream`, `DoubleStream`) elkerülik a boxingot. Buktatók: a stream egyszer használható, a lambdák ne módosítsanak közös állapotot, a `parallel()` csak nagy, CPU-igényes, állapotmentes feladatnál gyorsít.

```java
import java.util.*;
import java.util.stream.*;

public class StreamsDemo {
    record Order(String customer, String category, double amount, boolean paid) {}

    public static void main(String[] args) {
        List<Order> orders = List.of(
            new Order("anna", "könyv", 4200, true),
            new Order("bence", "játék", 15900, false),
            new Order("anna", "játék", 8900, true),
            new Order("csaba", "könyv", 3100, true),
            new Order("bence", "könyv", 6100, true));

        // groupingBy + downstream collector, rendezett (TreeMap) kimenettel
        Map<String, Double> revenueByCategory = orders.stream()
            .filter(Order::paid)
            .collect(Collectors.groupingBy(Order::category, TreeMap::new,
                     Collectors.summingDouble(Order::amount)));
        System.out.println(revenueByCategory);

        // partitioningBy: mindig két kulcs (true/false)
        Map<Boolean, Long> paidCount = orders.stream()
            .collect(Collectors.partitioningBy(Order::paid, Collectors.counting()));
        System.out.println(paidCount);

        // toMap merge-függvénnyel és beszúrási sorrendet tartó Map-pel
        Map<String, Double> perCustomer = orders.stream()
            .collect(Collectors.toMap(Order::customer, Order::amount, Double::sum, LinkedHashMap::new));
        System.out.println(perCustomer);

        // teeing: két collector egy menetben, majd az eredmények összefésülése
        String stats = orders.stream().collect(Collectors.teeing(
            Collectors.averagingDouble(Order::amount),
            Collectors.maxBy(Comparator.comparingDouble(Order::amount)),
            (avg, max) -> "átlag=%.0f, legnagyobb=%s".formatted(avg, max.map(Order::customer).orElse("-"))));
        System.out.println(stats);

        // flatMap + distinct + sorted + joining
        String letters = orders.stream()
            .map(Order::customer)
            .flatMap(name -> name.chars().mapToObj(c -> String.valueOf((char) c)))
            .distinct().sorted()
            .collect(Collectors.joining(",", "[", "]"));
        System.out.println(letters);

        // Primitív stream statisztikával (boxing nélkül)
        DoubleSummaryStatistics s = orders.stream().mapToDouble(Order::amount).summaryStatistics();
        System.out.printf("min=%.0f max=%.0f sum=%.0f%n", s.getMin(), s.getMax(), s.getSum());

        // Párhuzamos stream: CPU-igényes, állapotmentes munkára
        long primes = LongStream.rangeClosed(2, 200_000).parallel().filter(StreamsDemo::isPrime).count();
        System.out.println("Prímek száma: " + primes);
    }

    static boolean isPrime(long n) {
        return LongStream.rangeClosed(2, (long) Math.sqrt(n)).noneMatch(d -> n % d == 0);
    }
}
```

## ExecutorService és CompletableFuture
<!-- q: Hogyan futtassak párhuzamos és aszinkron feladatokat ExecutorService-szel és CompletableFuture-rel? -->
<!-- tags: concurrency, executorservice, completablefuture, thread pool, async, future -->

Az `ExecutorService` szálkészletet kezel: a feladatokat (`Runnable`/`Callable`) sorba állítja és újrahasznosított szálakon futtatja, így elkerüljük a szálanként drága létrehozást. A `CompletableFuture` nem blokkoló láncolást ad: `thenApply` (map), `thenCompose` (függő aszinkron lépés, flatMap), `thenCombine`/`allOf` (független eredmények), `exceptionally`/`handle` (hibakezelés), `completeOnTimeout` (alapérték időtúllépéskor). Mindig adjunk meg saját executort a `*Async` metódusoknak, különben a közös ForkJoinPool-t terheljük blokkoló I/O-val. A poolt kötelező leállítani (`shutdown` + `awaitTermination`), Java 19+ óta try-with-resources-szal is.

```java
import java.util.List;
import java.util.concurrent.*;

public class AsyncDemo {
    record User(long id, String name) {}
    record Profile(User user, List<String> orders, int score) {}

    // Lassú távoli hívásokat szimuláló szolgáltatások
    static User loadUser(long id) { sleep(200); return new User(id, "user-" + id); }
    static List<String> loadOrders(long id) { sleep(300); return List.of("A-1", "A-2"); }
    static int loadScore(long id) {
        sleep(150);
        if (id < 0) throw new IllegalStateException("ismeretlen user");
        return 87;
    }

    public static void main(String[] args) throws Exception {
        ExecutorService io = Executors.newFixedThreadPool(8); // I/O-ra több szál, CPU-ra ~magszám
        try {
            long id = 7;
            var user = CompletableFuture.supplyAsync(() -> loadUser(id), io);
            var orders = CompletableFuture.supplyAsync(() -> loadOrders(id), io);
            var score = CompletableFuture.supplyAsync(() -> loadScore(id), io)
                .completeOnTimeout(0, 1, TimeUnit.SECONDS)   // lassú függőség -> alapérték
                .exceptionally(ex -> -1);                    // hiba -> alapérték

            // allOf: a három hívás párhuzamosan fut, a join() itt már nem blokkol
            CompletableFuture<Profile> profile = CompletableFuture.allOf(user, orders, score)
                .thenApply(v -> new Profile(user.join(), orders.join(), score.join()));
            System.out.println(profile.get(2, TimeUnit.SECONDS)); // ~300 ms, nem 650

            // thenCompose: függő lépés; thenCombine: független eredmény; handle: hiba vagy érték
            String chained = CompletableFuture.supplyAsync(() -> loadUser(1), io)
                .thenCompose(u -> CompletableFuture.supplyAsync(() -> loadScore(u.id()), io))
                .thenCombine(CompletableFuture.supplyAsync(() -> loadOrders(1), io),
                             (s, o) -> "score=" + s + ", rendelések=" + o.size())
                .handle((res, ex) -> ex == null ? res : "hiba: " + ex.getMessage())
                .join();
            System.out.println(chained);

            // invokeAll: Callable-ök listája -> Future-ök; a hiba ExecutionException-be csomagolva jön
            List<Callable<Integer>> tasks = List.of(() -> loadScore(1), () -> loadScore(-1));
            for (Future<Integer> f : io.invokeAll(tasks)) {
                try { System.out.println("eredmény: " + f.get()); }
                catch (ExecutionException e) { System.out.println("feladat hibázott: " + e.getCause()); }
            }
        } finally {
            io.shutdown();                                   // új feladatot már nem fogad
            if (!io.awaitTermination(5, TimeUnit.SECONDS)) io.shutdownNow();
        }
    }

    static void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }
}
```

## Virtuális szálak (Project Loom)
<!-- q: Mik a virtuális szálak és mikor használjam őket? -->
<!-- tags: virtual threads, loom, java 21, concurrency, pinning, semaphore, thread-per-request -->

A virtuális szálak (Java 21+) a JVM által ütemezett, néhány KB-os szálak, amelyek kevés platform- (carrier) szálon futnak egy ForkJoinPool-on. Blokkoló hívásnál (I/O, `sleep`, `BlockingQueue.take`) a virtuális szál lecsatol a carrierről, így százezres párhuzamosság is olcsó, és a megszokott blokkoló, szinkron stílus megmarad (thread-per-request). CPU-kötött munkát nem gyorsítanak; poolozni őket felesleges, a szűkös erőforrást (DB-kapcsolat) `Semaphore`-ral korlátozzuk. Buktató: Java 21–23-ban a `synchronized` blokkon belüli blokkolás "pinning"-et okoz (a carrier lefoglalva marad), ezt a JDK 24 megszüntette; a sok virtuális szál mellett a nagy `ThreadLocal` értékek memóriát pazarolnak.

```java
import java.time.Duration;
import java.util.List;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.IntStream;

public class VirtualThreadsDemo {
    // A párhuzamosságot nem a pool mérete, hanem egy Semaphore korlátozza (pl. max 500 DB-kapcsolat)
    private static final Semaphore DB_PERMITS = new Semaphore(500);
    private static final AtomicInteger DONE = new AtomicInteger();

    static String handleRequest(int i) throws InterruptedException {
        DB_PERMITS.acquire();
        try {
            Thread.sleep(Duration.ofMillis(100)); // blokkoló hívás: a virtuális szál lecsatol a carrierről
        } finally {
            DB_PERMITS.release();
        }
        DONE.incrementAndGet();
        return "kérés-" + i + " @ " + Thread.currentThread();
    }

    public static void main(String[] args) throws Exception {
        long start = System.nanoTime();
        // Feladatonként egy új virtuális szál; a close() megvárja mindet
        try (ExecutorService exec = Executors.newVirtualThreadPerTaskExecutor()) {
            List<Future<String>> results = IntStream.range(0, 5_000)
                .mapToObj(i -> exec.submit(() -> handleRequest(i)))
                .toList();
            System.out.println(results.getFirst().get());
        }
        System.out.printf("%d kérés kész %d ms alatt%n", DONE.get(), (System.nanoTime() - start) / 1_000_000);

        // Közvetlen létrehozás builderrel
        Thread t = Thread.ofVirtual().name("worker-", 0).start(() ->
            System.out.println("virtuális? " + Thread.currentThread().isVirtual()));
        t.join();

        // ThreadFactory meglévő API-khoz (pl. HTTP szerver executorja)
        ThreadFactory factory = Thread.ofVirtual().name("vt-", 0).factory();
        try (var exec = Executors.newThreadPerTaskExecutor(factory)) {
            exec.submit(() -> System.out.println("fut: " + Thread.currentThread().getName()));
        }
    }
}
```

## Szálbiztonság: Java Memory Model, synchronized, lockok, atomikus típusok
<!-- q: Hogyan tegyem szálbiztossá a kódot synchronized-dal, lockokkal és atomikus változókkal? -->
<!-- tags: synchronized, volatile, happens-before, reentrantlock, readwritelock, atomic, longadder, cas -->

A Java Memory Model szerint egy szál írása csak happens-before kapcsolat esetén garantáltan látható a másiknak: ilyet ad a monitor elengedése/megszerzése, a `volatile` írás/olvasás, a `Thread.start`/`join`. A `synchronized` kölcsönös kizárást és láthatóságot ad, a `ReentrantLock` ezen felül `tryLock`-ot időkorláttal, megszakíthatóságot és fair módot, a `ReadWriteLock` párhuzamos olvasókat. Az atomikus osztályok (`AtomicLong`, `AtomicReference`) zár nélküli CAS-műveletek, nagy versengésnél a `LongAdder` skálázódik jobban. A `volatile` NEM teszi atomivá a `count++`-t; a lockot mindig `finally`-ben engedjük el, és a lockokat mindig azonos sorrendben szerezzük meg a deadlock elkerülésére.

```java
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.*;
import java.util.concurrent.locks.*;

public class SyncDemo {
    // volatile: láthatóság + rendezés, de nem atomicitás
    private static volatile boolean running = true;

    static final class Counter {               // synchronized: belső monitor, reentráns
        private long value;
        synchronized void inc() { value++; }
        synchronized long get() { return value; }
    }

    static final class Cache<K, V> {           // ReadWriteLock: sok olvasó, egy író
        private final Map<K, V> map = new HashMap<>();
        private final ReadWriteLock rw = new ReentrantReadWriteLock();
        V get(K k) { rw.readLock().lock(); try { return map.get(k); } finally { rw.readLock().unlock(); } }
        void put(K k, V v) { rw.writeLock().lock(); try { map.put(k, v); } finally { rw.writeLock().unlock(); } }
    }

    static final AtomicLong atomic = new AtomicLong();
    static final LongAdder adder = new LongAdder();          // cellákra bontott számláló
    static final AtomicReference<String> leader = new AtomicReference<>("nincs");

    public static void main(String[] args) throws InterruptedException {
        Counter counter = new Counter();
        Runnable work = () -> {
            for (int i = 0; i < 100_000; i++) { counter.inc(); atomic.incrementAndGet(); adder.increment(); }
        };
        Thread a = new Thread(work), b = new Thread(work);
        a.start(); b.start();
        a.join(); b.join();    // join() happens-before: utána látjuk a szálak írásait
        System.out.println(counter.get() + " " + atomic.get() + " " + adder.sum()); // mind 200000

        // compareAndSet: csak akkor ír, ha közben senki nem módosította
        boolean won = leader.compareAndSet("nincs", "node-1");
        leader.compareAndSet("nincs", "node-2");             // ez már elbukik
        System.out.println("vezető: " + leader.get() + " (első nyert: " + won + ")");

        // tryLock időkorláttal: nem akadunk be örökre
        Lock lock = new ReentrantLock(true);                 // fair: FIFO, de lassabb
        if (lock.tryLock(50, TimeUnit.MILLISECONDS)) {
            try { System.out.println("zár megszerezve"); } finally { lock.unlock(); }
        }

        // volatile leállítási jelző: nélküle a JIT kiemelhetné a ciklusból az olvasást
        Thread poller = new Thread(() -> { while (running) Thread.onSpinWait(); System.out.println("poller leállt"); });
        poller.start();
        Thread.sleep(50);
        running = false;
        poller.join();

        Cache<String, Integer> cache = new Cache<>();
        cache.put("x", 1);
        System.out.println(cache.get("x"));
    }
}
```

## java.util.concurrent: konkurens kollekciók és szinkronizálók
<!-- q: Hogyan építsek producer-consumer feldolgozást BlockingQueue-val és ConcurrentHashMap-pel? -->
<!-- tags: blockingqueue, concurrenthashmap, countdownlatch, producer consumer, copyonwritearraylist, backpressure -->

A `java.util.concurrent` kész, alaposan tesztelt építőelemeket ad, amelyek többnyire jobbak a kézzel írt `wait/notify`-nál. A korlátos `BlockingQueue` (`ArrayBlockingQueue`) producer-consumer mintához való: tele sornál a `put` blokkol, ez természetes backpressure. A `ConcurrentHashMap` szegmensenként/bucketenként zárol, a `merge`/`compute` atomikus – a `get` majd `put` páros viszont versenyhelyzet. A `CountDownLatch` egyszeri bevárásra, a `Semaphore` erőforrás-korlátozásra, a `CopyOnWriteArrayList` ritkán írt, sokszor bejárt listákra (pl. listenerek) való.

```java
import java.util.*;
import java.util.concurrent.*;

public class PipelineDemo {
    record Job(int id, String payload) {}
    private static final Job POISON = new Job(-1, ""); // "méregpirula": leállítási jel a fogyasztóknak

    public static void main(String[] args) throws Exception {
        BlockingQueue<Job> queue = new ArrayBlockingQueue<>(100); // korlátos -> backpressure
        ConcurrentHashMap<String, Integer> wordCounts = new ConcurrentHashMap<>();
        int consumers = 4;
        CountDownLatch done = new CountDownLatch(consumers);
        ExecutorService pool = Executors.newFixedThreadPool(consumers + 1);

        // Termelő: Callable, hogy a put() InterruptedException-jét ne kelljen helyben elkapni
        pool.submit(() -> {
            String[] texts = {"alma körte alma", "szilva alma", "körte körte barack"};
            for (int i = 0; i < 300; i++) queue.put(new Job(i, texts[i % texts.length]));
            for (int i = 0; i < consumers; i++) queue.put(POISON);
            return null;
        });

        // Fogyasztók
        for (int c = 0; c < consumers; c++) {
            pool.submit(() -> {
                try {
                    while (true) {
                        Job job = queue.take();             // üres sornál blokkol
                        if (job == POISON) break;
                        for (String w : job.payload().split(" ")) {
                            wordCounts.merge(w, 1, Integer::sum); // atomikus frissítés
                        }
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();     // megszakítási jelzés visszaállítása
                } finally {
                    done.countDown();
                }
            });
        }

        if (!done.await(5, TimeUnit.SECONDS)) System.err.println("időtúllépés!");
        pool.shutdown();
        System.out.println(new TreeMap<>(wordCounts));

        // Tömeges CHM-művelet párhuzamossági küszöbbel
        String top = wordCounts.reduceEntries(1, (e1, e2) -> e1.getValue() >= e2.getValue() ? e1 : e2).getKey();
        System.out.println("leggyakoribb: " + top);

        // CopyOnWriteArrayList: iteráció közbeni módosítás sem dob ConcurrentModificationException-t
        List<Runnable> listeners = new CopyOnWriteArrayList<>();
        listeners.add(() -> System.out.println("esemény kezelve"));
        listeners.forEach(Runnable::run);
    }
}
```

## Reflection, annotációk és annotation processing
<!-- q: Hogyan használjak saját annotációkat reflectionnel és fordítási idejű annotation processorral? -->
<!-- tags: reflection, annotations, retention, dynamic proxy, annotation processor, code generation -->

Az annotáció metaadat; a `@Retention` dönti el, meddig él: `SOURCE` (csak fordító), `CLASS` (bájtkód), `RUNTIME` (reflectionnel olvasható). Futásidőben a reflection (`getDeclaredFields`, `getAnnotation`, `Proxy`) általános keretrendszereket tesz lehetővé (validáció, DI, ORM, mock), de lassabb, megkerüli a fordítási ellenőrzést, és modulhatáron csak `opens` esetén ér el privát tagokat. A fordítási idejű annotation processor (`AbstractProcessor`) a `javac` futása közben generál forráskódot (így működik a Lombok, MapStruct, Dagger), nincs futásidejű költsége. A processort `META-INF/services/javax.annotation.processing.Processor` fájlban vagy `-processor` kapcsolóval regisztráljuk.

```java
import java.lang.annotation.*;
import java.lang.reflect.*;
import java.util.*;

public class ValidationDemo {
    @Retention(RetentionPolicy.RUNTIME) @Target(ElementType.FIELD)
    @interface NotBlank { String message() default "nem lehet üres"; }

    @Retention(RetentionPolicy.RUNTIME) @Target(ElementType.FIELD)
    @interface Range { int min(); int max(); }

    static class SignupForm {
        @NotBlank String username;
        @NotBlank(message = "email kötelező") String email;
        @Range(min = 13, max = 120) int age;
        SignupForm(String u, String e, int a) { username = u; email = e; age = a; }
    }

    // Általános validátor: bármely objektum mezőit bejárja
    static List<String> validate(Object target) throws IllegalAccessException {
        List<String> errors = new ArrayList<>();
        for (Field f : target.getClass().getDeclaredFields()) {
            f.setAccessible(true);
            Object value = f.get(target);
            NotBlank nb = f.getAnnotation(NotBlank.class);
            if (nb != null && (value == null || value.toString().isBlank())) errors.add(f.getName() + ": " + nb.message());
            Range r = f.getAnnotation(Range.class);
            if (r != null && value instanceof Integer i && (i < r.min() || i > r.max()))
                errors.add(f.getName() + ": " + r.min() + "–" + r.max() + " között kell legyen");
        }
        return errors;
    }

    public static void main(String[] args) throws Exception {
        System.out.println(validate(new SignupForm("auri", "", 9)));

        // Dinamikus proxy: futásidejű interfész-implementáció (így működik sok AOP és mock eszköz)
        Runnable real = () -> System.out.println("valódi munka");
        Runnable timed = (Runnable) Proxy.newProxyInstance(
            Runnable.class.getClassLoader(), new Class<?>[]{Runnable.class},
            (proxy, method, a) -> {
                long t = System.nanoTime();
                Object res = method.invoke(real, a);       // továbbhívás a valódi objektumra
                System.out.printf("%s: %d µs%n", method.getName(), (System.nanoTime() - t) / 1000);
                return res;
            });
        timed.run();

        Method m = String.class.getMethod("repeat", int.class); // hívás név alapján
        System.out.println(m.invoke("ab", 3));
    }
}
```

```java
import java.io.Writer;
import java.util.Set;
import javax.annotation.processing.*;
import javax.lang.model.SourceVersion;
import javax.lang.model.element.*;
import javax.tools.Diagnostic;

// Fordítási idejű processzor: minden @AutoToString osztályhoz XxxPrinter osztályt generál.
// Használat: javac -processorpath out -processor ToStringProcessor Model.java
@SupportedAnnotationTypes("AutoToString")
@SupportedSourceVersion(SourceVersion.RELEASE_21)
public class ToStringProcessor extends AbstractProcessor {
    @Override
    public boolean process(Set<? extends TypeElement> annotations, RoundEnvironment env) {
        for (TypeElement ann : annotations) {
            for (Element el : env.getElementsAnnotatedWith(ann)) {
                if (el.getKind() != ElementKind.CLASS) {
                    // Fordítási hiba a felhasználó kódjában, pontos helymegjelöléssel
                    processingEnv.getMessager().printMessage(Diagnostic.Kind.ERROR, "csak osztályon használható", el);
                    continue;
                }
                generate((TypeElement) el);
            }
        }
        return true; // az annotációt "elfogyasztottuk"
    }

    private void generate(TypeElement type) {
        String name = type.getSimpleName() + "Printer";
        StringBuilder body = new StringBuilder("\"" + type.getSimpleName() + "{\"");
        for (Element member : type.getEnclosedElements()) {
            // csak a nem statikus (és nem privát) mezők kerülnek bele
            if (member.getKind() == ElementKind.FIELD && !member.getModifiers().contains(Modifier.STATIC)
                    && !member.getModifiers().contains(Modifier.PRIVATE)) {
                String f = member.getSimpleName().toString();
                body.append(" + \" ").append(f).append("=\" + o.").append(f);
            }
        }
        body.append(" + \" }\"");
        try (Writer w = processingEnv.getFiler().createSourceFile(name, type).openWriter()) {
            w.write("public final class " + name + " {\n"
                  + "  public static String print(" + type.getQualifiedName() + " o) {\n"
                  + "    return " + body + ";\n  }\n}\n");
        } catch (Exception e) {
            processingEnv.getMessager().printMessage(Diagnostic.Kind.ERROR, e.toString(), type);
        }
    }
}
```

## Modulrendszer (JPMS)
<!-- q: Hogyan működik a Java modulrendszer és a module-info.java? -->
<!-- tags: jpms, modules, module-info, exports, opens, requires, serviceloader, jlink -->

A Java 9-ben bevezetett modulrendszer erős egységbezárást ad: egy modul csak az `exports`-szal megnevezett csomagjait teszi elérhetővé, a többi akkor sem látható, ha `public`. A `requires` explicit függőségeket ír le (a `transitive` továbbadja őket, a `static` csak fordításkor kell), az `opens` mély reflectiont enged (Jackson, Hibernate, Spring), a `uses`/`provides` pedig a `ServiceLoader`-alapú plugin-architektúrát. A `jlink` csak a ténylegesen használt modulokból épít minimális futtatókörnyezetet (kisebb Docker image). Buktató: sok könyvtár még classpath-on él (unnamed/automatic module), és a reflection-alapú keretrendszerek hiányzó `opens` esetén `InaccessibleObjectException`-t dobnak.

```java
// src/com.example.billing/module-info.java
module com.example.billing {
    requires java.net.http;                       // platformmodul
    requires transitive com.example.core;         // a felhasználóink is látják a core-t
    requires static com.github.spotbugs.annotations; // csak fordításkor kell

    exports com.example.billing.api;              // csak ez a csomag publikus API
    exports com.example.billing.spi to com.example.plugins; // minősített export

    opens com.example.billing.model to com.fasterxml.jackson.databind; // reflection a JSON-hoz

    uses com.example.billing.spi.TaxProvider;     // ServiceLoader-fogyasztó
    provides com.example.billing.spi.TaxProvider
        with com.example.billing.internal.HuTaxProvider; // szolgáltatás-implementáció
}
```

```java
package com.example.billing.api;

import com.example.billing.spi.TaxProvider;
import java.math.BigDecimal;
import java.util.ServiceLoader;

public final class TaxCalculator {
    public BigDecimal gross(BigDecimal net, String country) {
        // ServiceLoader: a module-path összes "provides" implementációját felfedezi
        return ServiceLoader.load(TaxProvider.class).stream()
            .map(ServiceLoader.Provider::get)
            .filter(p -> p.supports(country))
            .findFirst()
            .map(p -> net.multiply(BigDecimal.ONE.add(p.rate())))
            .orElseThrow(() -> new IllegalArgumentException("Nincs adószabály: " + country));
    }
}
```

```bash
# Fordítás modulonként, futtatás module-path-ról, majd minimális runtime építése
javac -d out --module-source-path src $(find src -name '*.java')
java --module-path out -m com.example.app/com.example.app.Main
jlink --module-path out --add-modules com.example.app --strip-debug --no-header-files --output build/runtime
```

## Fájlkezelés NIO.2-vel és a beépített HTTP kliens
<!-- q: Hogyan kezeljek fájlokat NIO.2-vel és hogyan küldjek HTTP kéréseket a java.net.http klienssel? -->
<!-- tags: nio, files, path, io, httpclient, java.net.http, atomic move, streaming -->

A `java.nio.file` (`Path`, `Files`) a régi `java.io.File` utódja: jobb hibaüzenetek, szimbolikus linkek, attribútumok, `WatchService`, és streamelt feldolgozás (`Files.lines`, `Files.walk`) – ezeket a streameket le kell zárni, különben fájlleíró szivárog. Atomikus íráshoz ideiglenes fájlba írunk és `ATOMIC_MOVE`-val nevezzük át, így az olvasó sosem lát félkész fájlt. A Java 11 óta beépített `HttpClient` támogatja a HTTP/2-t, a szinkron (`send`) és aszinkron (`sendAsync`, `CompletableFuture`) hívást; szálbiztos, és újra kell hasznosítani (connection pool). Mindig állítsunk be connect- és kérés-timeoutot.

```java
import java.io.IOException;
import java.net.URI;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.stream.*;

public class IoHttpDemo {
    // Nagy log fájl lusta, soronkénti feldolgozása – nem tölti be az egészet a memóriába
    static Map<String, Long> countLevels(Path log) throws IOException {
        try (Stream<String> lines = Files.lines(log, StandardCharsets.UTF_8)) { // le KELL zárni
            return lines.map(l -> l.split(" ", 2)[0])
                        .collect(Collectors.groupingBy(s -> s, TreeMap::new, Collectors.counting()));
        }
    }

    // Atomikus írás: temp fájl + átnevezés
    static void writeAtomically(Path target, List<String> lines) throws IOException {
        Path tmp = Files.createTempFile(target.toAbsolutePath().getParent(), "tmp-", ".part");
        Files.write(tmp, lines, StandardCharsets.UTF_8);
        Files.move(tmp, target, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
    }

    // Egy kliens az egész alkalmazásnak: connection pool, HTTP/2, szálbiztos
    private static final HttpClient HTTP = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(5))
        .followRedirects(HttpClient.Redirect.NORMAL)
        .build();

    static String postJson(URI uri, String json) throws IOException, InterruptedException {
        HttpRequest req = HttpRequest.newBuilder(uri)
            .timeout(Duration.ofSeconds(10))                       // kérésenkénti időkorlát
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(json))
            .build();
        HttpResponse<String> res = HTTP.send(req, HttpResponse.BodyHandlers.ofString());
        if (res.statusCode() >= 400) throw new IOException("HTTP " + res.statusCode() + ": " + res.body());
        return res.body();
    }

    // Aszinkron változat: nem blokkol, CompletableFuture-t ad
    static CompletableFuture<Integer> statusAsync(URI uri) {
        return HTTP.sendAsync(HttpRequest.newBuilder(uri).GET().build(), HttpResponse.BodyHandlers.discarding())
                   .thenApply(HttpResponse::statusCode);
    }

    public static void main(String[] args) throws IOException {
        Path dir = Files.createTempDirectory("nio-demo");
        Path log = dir.resolve("app.log");
        writeAtomically(log, List.of("INFO indul", "WARN lassú", "INFO kész", "ERROR hiba"));
        System.out.println(countLevels(log));                     // {ERROR=1, INFO=2, WARN=1}
        // postJson(URI.create("https://api.example.com/items"), "{\"name\":\"teszt\"}");
    }
}
```

## JDBC: lekérdezések, tranzakciók, batch
<!-- q: Hogyan használjam a JDBC-t biztonságosan PreparedStatement-tel és tranzakciókkal? -->
<!-- tags: jdbc, sql, preparedstatement, transaction, batch, datasource, connection pool, sql injection -->

A JDBC a Java szabványos, alacsony szintű adatbázis-API-ja; a JPA/Hibernate, jOOQ és a Spring `JdbcTemplate` is erre épül. Mindig `PreparedStatement`-et használjunk paraméterkötéssel (SQL injection ellen, és a lekérdezési terv is újrahasznosítható), a `Connection`/`Statement`/`ResultSet` erőforrásokat pedig try-with-resources zárja le. Éles környezetben `DataSource` connection poollal (HikariCP) adja a kapcsolatokat, a `close()` ilyenkor visszaadja a kapcsolatot a poolnak. Tranzakciónál kikapcsoljuk az auto-commitot, hibánál `rollback`, a végén visszaállítjuk az auto-commitot; sok sor beszúrásához batch-et használunk.

```java
import java.math.BigDecimal;
import java.sql.*;
import java.util.*;
import javax.sql.DataSource;

public class AccountRepository {
    public record Account(long id, String owner, BigDecimal balance) {}

    private final DataSource ds; // pl. HikariDataSource
    public AccountRepository(DataSource ds) { this.ds = ds; }

    public Optional<Account> findById(long id) throws SQLException {
        String sql = "SELECT id, owner, balance FROM account WHERE id = ?";
        try (Connection c = ds.getConnection();
             PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setLong(1, id);                        // paraméterkötés, sosem string-összefűzés
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next()
                    ? Optional.of(new Account(rs.getLong("id"), rs.getString("owner"), rs.getBigDecimal("balance")))
                    : Optional.empty();
            }
        }
    }

    // Tranzakció: mindkét UPDATE sikerül, vagy egyik sem
    public void transfer(long from, long to, BigDecimal amount) throws SQLException {
        String debit = "UPDATE account SET balance = balance - ? WHERE id = ? AND balance >= ?";
        String credit = "UPDATE account SET balance = balance + ? WHERE id = ?";
        try (Connection c = ds.getConnection()) {
            c.setAutoCommit(false);
            c.setTransactionIsolation(Connection.TRANSACTION_READ_COMMITTED);
            try (PreparedStatement d = c.prepareStatement(debit);
                 PreparedStatement cr = c.prepareStatement(credit)) {
                d.setBigDecimal(1, amount); d.setLong(2, from); d.setBigDecimal(3, amount);
                if (d.executeUpdate() != 1) throw new SQLException("Nincs fedezet vagy nincs ilyen számla: " + from);
                cr.setBigDecimal(1, amount); cr.setLong(2, to);
                if (cr.executeUpdate() != 1) throw new SQLException("Nincs ilyen célszámla: " + to);
                c.commit();
            } catch (SQLException e) {
                c.rollback();                         // hiba esetén visszagörgetés
                throw e;
            } finally {
                c.setAutoCommit(true);                // a pool tiszta állapotban kapja vissza
            }
        }
    }

    // Batch insert: sok sor egy hálózati körben
    public int[] insertAll(List<Account> accounts) throws SQLException {
        try (Connection c = ds.getConnection();
             PreparedStatement ps = c.prepareStatement("INSERT INTO account(owner, balance) VALUES (?, ?)")) {
            for (Account a : accounts) {
                ps.setString(1, a.owner());
                ps.setBigDecimal(2, a.balance());
                ps.addBatch();
            }
            return ps.executeBatch();
        }
    }
}
```

## Spring Boot REST API és dependency injection
<!-- q: Hogyan építsek REST API-t Spring Boottal és hogyan működik a dependency injection? -->
<!-- tags: spring boot, rest, dependency injection, controller, service, validation, problemdetail -->

A Spring Boot az IoC konténerre épül: a `@Component`/`@Service`/`@RestController` osztályokból bean lesz (alapból singleton), a függőségeket a konténer konstruktoron keresztül injektálja, az auto-configuration pedig a classpath alapján állítja be a webszervert, JSON-t, adatbázist. A konstruktor-injektálás a javasolt (final mezők, tesztben kézzel is példányosítható), a mező-injektálás (`@Autowired` mezőn) kerülendő. A `@Valid` a Bean Validation annotációkat ellenőrzi, a `@ExceptionHandler`/`@RestControllerAdvice` a kivételeket HTTP-válaszra képezi (RFC 7807 `ProblemDetail`). Buktató: a `@Transactional` és más proxy-alapú annotációk nem hatnak, ha az osztályon belülről hívjuk a metódust (self-invocation).

```java
package com.example.notes;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.net.URI;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.*;

@SpringBootApplication // = @Configuration + @EnableAutoConfiguration + @ComponentScan
public class NotesApplication {
    public static void main(String[] args) { SpringApplication.run(NotesApplication.class, args); }
}

// DTO-k recordként; a validációs annotációk a @Valid hatására futnak
record CreateNoteRequest(@NotBlank @Size(max = 200) String title, String body) {}
record Note(long id, String title, String body) {}

class NoteNotFoundException extends RuntimeException {
    NoteNotFoundException(long id) { super("Nincs ilyen jegyzet: " + id); }
}

@Service // singleton bean; éles kódban itt lenne egy Spring Data repository
class NoteService {
    private final Map<Long, Note> store = new ConcurrentHashMap<>();
    private final AtomicLong ids = new AtomicLong();

    Note create(CreateNoteRequest req) {
        Note n = new Note(ids.incrementAndGet(), req.title(), req.body());
        store.put(n.id(), n);
        return n;
    }
    Note get(long id) { return Optional.ofNullable(store.get(id)).orElseThrow(() -> new NoteNotFoundException(id)); }
    List<Note> all() { return List.copyOf(store.values()); }
}

@RestController
@RequestMapping("/api/notes")
class NoteController {
    private final NoteService service;

    // Konstruktor-injektálás: egyetlen konstruktornál @Autowired sem kell
    NoteController(NoteService service) { this.service = service; }

    @GetMapping
    List<Note> list() { return service.all(); }

    @GetMapping("/{id}")
    Note one(@PathVariable long id) { return service.get(id); }

    @PostMapping
    ResponseEntity<Note> create(@Valid @RequestBody CreateNoteRequest req) {
        Note n = service.create(req);
        return ResponseEntity.created(URI.create("/api/notes/" + n.id())).body(n); // 201 + Location
    }

    @ExceptionHandler(NoteNotFoundException.class)
    ProblemDetail notFound(NoteNotFoundException e) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, e.getMessage()); // RFC 7807
    }
}
```

## Tesztelés JUnit 5-tel és Mockitóval
<!-- q: Hogyan írjak unit teszteket JUnit 5-tel és Mockitóval? -->
<!-- tags: testing, junit5, mockito, mock, parameterized test, assertions, argumentcaptor -->

A JUnit 5 (Jupiter) a Java tesztelés alapja: `@Test`, `@ParameterizedTest` adatvezérelt esetekhez, `@Nested` csoportosításhoz, `assertThrows`/`assertAll` és bővítmények (`@ExtendWith`). A Mockito a függőségeket helyettesíti: `when(...).thenReturn(...)` a viselkedést adja (stub), a `verify` az interakciókat ellenőrzi, az `ArgumentCaptor` az átadott argumentumot fogja meg. A `MockitoExtension` szigorú stubbingot használ: a felesleges `when()` hibát okoz, ami tisztán tartja a teszteket. Buktatók: ne mockoljunk értékobjektumot és olyat, ami nem a miénk; `BigDecimal`-nál az `equals` a skálát is nézi (`compareTo` biztonságosabb).

```java
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.math.BigDecimal;
import java.util.Optional;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;

// A tesztelt kód (normál esetben src/main/java alatt)
interface PriceRepository { Optional<BigDecimal> priceOf(String sku); }
interface AuditLog { void record(String event); }

class CheckoutService {
    private final PriceRepository prices; private final AuditLog audit;
    CheckoutService(PriceRepository prices, AuditLog audit) { this.prices = prices; this.audit = audit; }

    BigDecimal total(String sku, int qty) {
        if (qty <= 0) throw new IllegalArgumentException("qty > 0 kell");
        BigDecimal unit = prices.priceOf(sku).orElseThrow(() -> new IllegalStateException("ismeretlen: " + sku));
        BigDecimal total = unit.multiply(BigDecimal.valueOf(qty));
        audit.record("checkout:" + sku + ":" + total);
        return total;
    }
}

@ExtendWith(MockitoExtension.class)
class CheckoutServiceTest {
    @Mock PriceRepository prices;
    @Mock AuditLog audit;
    @InjectMocks CheckoutService service;            // konstruktoron át kapja a mockokat
    @Captor ArgumentCaptor<String> eventCaptor;

    @Test
    @DisplayName("Összeg = egységár × mennyiség, és naplózódik")
    void computesTotalAndAudits() {
        when(prices.priceOf("SKU-1")).thenReturn(Optional.of(new BigDecimal("199.90")));

        BigDecimal total = service.total("SKU-1", 3);

        assertEquals(0, new BigDecimal("599.70").compareTo(total));
        verify(audit).record(eventCaptor.capture());
        assertTrue(eventCaptor.getValue().startsWith("checkout:SKU-1"));
    }

    @Test
    void unknownSkuThrowsAndDoesNotAudit() {
        when(prices.priceOf(anyString())).thenReturn(Optional.empty());
        var ex = assertThrows(IllegalStateException.class, () -> service.total("X", 1));
        assertTrue(ex.getMessage().contains("X"));
        verifyNoInteractions(audit);
    }

    @ParameterizedTest(name = "qty={0} érvénytelen")
    @ValueSource(ints = {0, -1, -100})
    void rejectsInvalidQuantity(int qty) {
        assertThrows(IllegalArgumentException.class, () -> service.total("SKU-1", qty));
        verifyNoInteractions(prices);                // validáció a repository hívása előtt
    }
}
```

## Idiomatikus tervezési minták Javában
<!-- q: Hogyan valósítsam meg idiomatikusan a Builder, Strategy, Singleton, Observer és Factory mintákat Javában? -->
<!-- tags: design patterns, builder, strategy, singleton, observer, factory, enum -->

A modern Java sok klasszikus mintát tömörebben ad: a Builder sok opcionális paraméterű, immutábilis objektumhoz való (a teleszkópos konstruktorok helyett), a Strategy enummal vagy lambdával cserélhető viselkedés `switch`-láncok helyett. A Singleton legbiztonságosabb formája az egyelemű `enum` (szálbiztos, szerializáció- és reflection-álló), bár DI-konténer mellett inkább a konténer kezelje az élettartamot. Az Observer típusos eseménybusszal, a Factory sealed interfész + statikus metódus kombinációval tiszta. Ne vigyük túlzásba: egy egyszerű lambda vagy record sokszor elég a "minta" helyett.

```java
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.*;

public class PatternsDemo {
    // Builder: kötelező paraméter a builder() metódusban, a többi opcionális
    record RequestSpec(String url, String method, Map<String, String> headers, int timeoutMs) {
        static Builder builder(String url) { return new Builder(url); }
        static final class Builder {
            private final String url; private String method = "GET"; private int timeoutMs = 5000;
            private final Map<String, String> headers = new LinkedHashMap<>();
            private Builder(String url) { this.url = Objects.requireNonNull(url); }
            Builder method(String m) { method = m; return this; }
            Builder header(String k, String v) { headers.put(k, v); return this; }
            Builder timeoutMs(int t) { if (t <= 0) throw new IllegalArgumentException("timeout > 0"); timeoutMs = t; return this; }
            RequestSpec build() { return new RequestSpec(url, method, Map.copyOf(headers), timeoutMs); }
        }
    }

    // Strategy enummal: a viselkedés adatként cserélhető
    enum Discount implements UnaryOperator<Double> {
        NONE { public Double apply(Double p) { return p; } },
        STUDENT { public Double apply(Double p) { return p * 0.8; } },
        BLACK_FRIDAY { public Double apply(Double p) { return Math.max(0, p - 5000); } }
    }

    // Singleton enummal
    enum Metrics {
        INSTANCE;
        private final Map<String, Integer> counters = new ConcurrentHashMap<>();
        void inc(String name) { counters.merge(name, 1, Integer::sum); }
        Map<String, Integer> snapshot() { return Map.copyOf(counters); }
    }

    // Observer: típusos eseménybusz
    static final class EventBus {
        private final Map<Class<?>, List<Consumer<Object>>> handlers = new ConcurrentHashMap<>();
        <E> void subscribe(Class<E> type, Consumer<? super E> h) {
            handlers.computeIfAbsent(type, k -> new ArrayList<>()).add(o -> h.accept(type.cast(o)));
        }
        void publish(Object event) { handlers.getOrDefault(event.getClass(), List.of()).forEach(h -> h.accept(event)); }
    }
    record UserRegistered(String name) {}

    // Factory sealed interfésszel: a lehetséges termékek zárt halmaza
    sealed interface Notifier permits Email, Sms {
        void send(String msg);
        static Notifier of(String channel) {
            return switch (channel) {
                case "email" -> new Email();
                case "sms" -> new Sms();
                default -> throw new IllegalArgumentException("ismeretlen csatorna: " + channel);
            };
        }
    }
    record Email() implements Notifier { public void send(String m) { System.out.println("email: " + m); } }
    record Sms() implements Notifier { public void send(String m) { System.out.println("sms: " + m); } }

    public static void main(String[] args) {
        System.out.println(RequestSpec.builder("https://api.example.com/x").method("POST").header("Accept", "application/json").build());
        System.out.println(Discount.STUDENT.apply(10_000.0));
        EventBus bus = new EventBus();
        bus.subscribe(UserRegistered.class, e -> { Metrics.INSTANCE.inc("signup"); Notifier.of("email").send("Üdv, " + e.name()); });
        bus.publish(new UserRegistered("teszt"));
        System.out.println(Metrics.INSTANCE.snapshot());
    }
}
```
