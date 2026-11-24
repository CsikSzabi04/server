# Kotlin
<!-- tech: kotlin -->
<!-- aliases: kt, kts, kotlin jvm, kotlinx, kotlin multiplatform, kmp -->

A Kotlin a JetBrains statikusan típusos, tömör nyelve, amely elsősorban a JVM-re fordul (de van Kotlin/JS, Kotlin/Native és Multiplatform is), és 100%-ban együttműködik a Java kóddal és könyvtárakkal. Típusrendszerébe épített null safety, típuskövetkeztetés, data és sealed osztályok, extension függvények, magasabb rendű függvények és a coroutine-alapú aszinkron programozás jellemzi; a memóriát a JVM GC-je kezeli. Az Android hivatalos elsődleges nyelve (Jetpack Compose), backendre Ktorral vagy Spring Boottal használják, a Gradle build-szkriptek (`.kts`) nyelve is. Erős a Java-kódbázisok fokozatos modernizálására; gyengébb oldala a lassabb fordítás és az, hogy a túl "okos" DSL-ek és extensionök nehezíthetik az olvashatóságot.

## Null safety: nullable típusok, safe call, Elvis
<!-- q: Hogyan működik a null safety Kotlinban? -->
<!-- tags: null safety, nullable, safe call, elvis, smart cast, lateinit, platform types -->

Kotlinban a `String` soha nem lehet null, a `String?` igen – a fordító csak ellenőrzés után engedi a nullable érték használatát, így a NullPointerException nagy része fordítási hibává válik. Eszközök: safe call (`?.`), Elvis (`?:`) alapértékhez vagy korai kilépéshez, `let` a nem-null ághoz, `as?` biztonságos casthoz, smart cast az ellenőrzés után. A `!!` NPE-t dob, ha mégis null – kerüljük; a `lateinit var` későbbi inicializáláshoz (DI, Android) való. Buktató: a Java API-kból jövő platform típusoknál (`String!`) a fordító nem véd, ott magunknak kell eldönteni a nullabilitást.

```kotlin
data class Address(val city: String?, val zip: String?)
data class Customer(val name: String, val email: String?, val address: Address?)

fun shippingLabel(c: Customer): String {
    // Safe call láncolás + Elvis alapérték
    val city = c.address?.city?.trim()?.takeIf { it.isNotEmpty() } ?: "ismeretlen város"
    return "${c.name} – $city"
}

fun requireEmail(c: Customer): String {
    // Elvis + throw: utána a fordító tudja, hogy az email nem null (smart cast)
    val email = c.email ?: throw IllegalArgumentException("Hiányzó email: ${c.name}")
    return email.lowercase()
}

fun normalizeZip(raw: Any?): String? {
    val s = raw as? String ?: return null      // as?: null hiba helyett
    return s.filter(Char::isDigit).takeIf { it.length == 4 }
}

class LazyHolder {
    lateinit var config: Map<String, String>    // korai olvasás -> UninitializedPropertyAccessException
    fun isReady() = ::config.isInitialized
}

fun main() {
    val customers = listOf(
        Customer("Anna", "ANNA@EXAMPLE.COM", Address("Kecskemét", "6000")),
        Customer("Bence", null, Address(null, "60x0")),
        Customer("Csaba", "csaba@example.com", null),
    )
    customers.forEach { println(shippingLabel(it)) }

    // let csak nem-null értékre fut le
    customers.forEach { c -> c.email?.let { println("Levél megy ide: $it") } }

    // mapNotNull: a null eredmények kiszűrése
    println(customers.mapNotNull { it.address?.zip }.mapNotNull(::normalizeZip))

    println(runCatching { requireEmail(customers[1]) }.exceptionOrNull()?.message)

    // !! – "biztosan nem null"; ha mégis, NPE. Csak ott, ahol tényleg garantált.
    val first: String = customers.first().email!!

    // Platform típus: a Java metódus String!-et ad, mi döntjük el, hogy nullable-ként kezeljük
    val home: String? = System.getenv("SOME_UNSET_VARIABLE")
    println("$first, ${home ?: "nincs beállítva"}")
    println(LazyHolder().isReady())
}
```

## Data class, value class, object és companion
<!-- q: Mire valók a data classok, value classok, object és companion object Kotlinban? -->
<!-- tags: data class, value class, inline class, object, companion object, operator overloading, copy -->

A `data class` a primary konstruktor property-jeiből generál `equals`/`hashCode`/`toString`/`copy`/`componentN` metódusokat – ideális immutábilis modellekhez (`val` property-kkel). A `@JvmInline value class` egyetlen értéket burkol típusbiztosan (pl. `OrderId` a nyers `Long` helyett), és a JVM-en többnyire allokáció nélkül, a mögöttes értékként jelenik meg. Az `object` szálbiztos, lustán inicializált singleton, a `companion object` az osztályhoz kötött "statikus" tagok helye (factory, konstansok). Buktató: a data class törzsében deklarált property nem része az `equals`-nak, és mutable (`var`) property-vel a `HashMap` kulcsként használt objektum "elveszhet".

```kotlin
import java.math.BigDecimal

data class Money(val amount: BigDecimal, val currency: String) {
    init { require(currency.length == 3) { "ISO 4217 kód kell: $currency" } }

    // Operátor-túlterhelés: a + b, a * n
    operator fun plus(other: Money): Money {
        check(currency == other.currency) { "Eltérő pénznem: $currency vs ${other.currency}" }
        return copy(amount = amount + other.amount)
    }
    operator fun times(n: Int) = copy(amount = amount * n.toBigDecimal())
    override fun toString() = "${amount.toPlainString()} $currency"
}

// Típusbiztos azonosító futásidejű wrapper-objektum nélkül
@JvmInline
value class OrderId(val raw: Long) {
    init { require(raw > 0) { "Az azonosító pozitív" } }
}

data class OrderLine(val sku: String, val unitPrice: Money, val qty: Int)

data class Order(val id: OrderId, val lines: List<OrderLine>, val note: String? = null) {
    // Számított property: nincs a konstruktorban, ezért nem része az equals-nak
    val total: Money
        get() = lines.map { it.unitPrice * it.qty }.reduce(Money::plus)
}

object Currencies {                     // singleton
    const val HUF = "HUF"               // fordítási idejű konstans
    fun huf(v: Long) = Money(BigDecimal.valueOf(v), HUF)
}

class Invoice private constructor(val number: String) {
    companion object {                  // "statikus" factory; @JvmStatic a Java-hívóknak
        private var seq = 0
        @JvmStatic fun next(): Invoice = Invoice("INV-%05d".format(++seq))
    }
}

fun main() {
    val order = Order(
        OrderId(42),
        listOf(OrderLine("KAVE", Currencies.huf(1890), 2), OrderLine("BOGRE", Currencies.huf(3490), 1)),
    )
    println(order.total)                                // 7270 HUF

    // copy: immutábilis módosítás; destrukturálás componentN-nel
    val updated = order.copy(note = "ajándékcsomagolás")
    val (id, lines, note) = updated
    println("$id ${lines.size} $note")
    println(order == updated.copy(note = null))         // true: strukturális egyenlőség
    println(Invoice.next().number)
}
```

## Sealed osztályok és a when kifejezés
<!-- q: Hogyan modellezzek zárt állapotokat sealed osztályokkal és when kifejezéssel? -->
<!-- tags: sealed class, sealed interface, when, exhaustive, adt, ui state, data object -->

A `sealed` osztály/interfész összes közvetlen altípusa fordításkor ismert (ugyanabban a modulban és csomagban), ezért a `when` kifejezés `else` ág nélkül is kimerítő, és új altípus hozzáadásakor a fordító minden kezeletlen helyet jelez. Tipikus felhasználás: műveleti eredmények (siker/hiba/folyamatban), UI-állapotok, parancsok és események modellezése. Az állapot nélküli esetekre `data object` (Kotlin 1.9+) való, a kovariáns `out T` paraméterrel a `Nothing`-ot használó esetek bármely `T`-hez illeszkednek. A `when` ágakban smart cast történik, így az altípus mezői közvetlenül elérhetők.

```kotlin
sealed interface PaymentResult {
    data class Success(val transactionId: String, val amount: Long) : PaymentResult
    data class Declined(val reason: Reason) : PaymentResult
    data class Failed(val error: Throwable, val retryable: Boolean) : PaymentResult
    data object Pending : PaymentResult

    enum class Reason { INSUFFICIENT_FUNDS, FRAUD_SUSPECTED, CARD_EXPIRED }
}

// UI-állapot (tipikus Android/Compose minta); out T: UiState<Nothing> bármely UiState<T> helyére jó
sealed class UiState<out T> {
    data object Loading : UiState<Nothing>()
    data class Content<T>(val data: T) : UiState<T>()
    data class Error(val message: String) : UiState<Nothing>()
}

fun describe(r: PaymentResult): String = when (r) {        // kimerítő, nincs else
    is PaymentResult.Success -> "Sikeres: ${r.transactionId} (${r.amount} Ft)" // smart cast
    is PaymentResult.Declined -> when (r.reason) {
        PaymentResult.Reason.INSUFFICIENT_FUNDS -> "Nincs fedezet"
        PaymentResult.Reason.FRAUD_SUSPECTED -> "Biztonsági ellenőrzés szükséges"
        PaymentResult.Reason.CARD_EXPIRED -> "Lejárt kártya"
    }
    is PaymentResult.Failed -> if (r.retryable) "Átmeneti hiba, újrapróbálható" else "Végleges hiba: ${r.error.message}"
    PaymentResult.Pending -> "Feldolgozás alatt"
}

fun <T> render(state: UiState<T>, show: (T) -> String): String = when (state) {
    UiState.Loading -> "töltés…"
    is UiState.Content -> show(state.data)
    is UiState.Error -> "Hiba: ${state.message}"
}

// Argumentum nélküli when: if-else lánc helyett
fun riskLevel(amount: Long, foreignCard: Boolean) = when {
    amount > 1_000_000 && foreignCard -> "magas"
    amount > 1_000_000 || foreignCard -> "közepes"
    else -> "alacsony"
}

fun main() {
    listOf(
        PaymentResult.Success("TX-1", 12_990),
        PaymentResult.Declined(PaymentResult.Reason.CARD_EXPIRED),
        PaymentResult.Failed(java.io.IOException("timeout"), retryable = true),
        PaymentResult.Pending,
    ).map(::describe).forEach(::println)

    val states: List<UiState<List<String>>> =
        listOf(UiState.Loading, UiState.Content(listOf("a", "b")), UiState.Error("offline"))
    states.forEach { println(render(it) { list -> "${list.size} elem" }) }
    println(riskLevel(2_000_000, foreignCard = false))
}
```

## Extension függvények és scope függvények
<!-- q: Hogyan írjak extension függvényeket, és mikor melyik scope függvényt (let, apply, also, run, with) használjam? -->
<!-- tags: extension function, extension property, scope functions, let, apply, also, run, with -->

Az extension függvény új "metódust" ad egy meglévő típushoz öröklés és forráskód-módosítás nélkül; valójában statikus függvény, amelynek első paramétere a receiver, ezért statikusan kötődik (nincs polimorf felülírás), és nem fér hozzá a privát tagokhoz. Lehet nullable receiverre is (`String?.orDash()`), és létezik extension property is (backing field nélkül). A scope függvények: `apply` (konfigurálás, a receivert adja vissza), `also` (mellékhatás, pl. log), `let` (transzformáció, gyakran `?.let`), `run` (blokk a receiverrel, az eredményt adja), `with` (nem-extension `run`). Ne ágyazzuk őket túl mélyre, mert az `it`/`this` gyorsan olvashatatlanná válik.

```kotlin
import java.time.LocalDate
import java.time.format.DateTimeFormatter

// URL-barát slug magyar ékezetekkel
fun String.toSlug(): String =
    lowercase()
        .replace(Regex("[áà]"), "a").replace(Regex("[éè]"), "e").replace(Regex("[íì]"), "i")
        .replace(Regex("[óöő]"), "o").replace(Regex("[úüű]"), "u")
        .replace(Regex("[^a-z0-9]+"), "-").trim('-')

fun String?.orDash(): String = if (this.isNullOrBlank()) "-" else this   // nullable receiver

val LocalDate.isWeekend: Boolean get() = dayOfWeek.value >= 6            // extension property

fun <T, K> Iterable<T>.countBy(key: (T) -> K): Map<K, Int> = groupingBy(key).eachCount()

data class Report(var title: String = "", val lines: MutableList<String> = mutableListOf(), var date: LocalDate? = null)

fun main() {
    println("Árvíztűrő Tükörfúrógép 2025!".toSlug())   // arvizturo-tukorfurogep-2025
    val missing: String? = null
    println(missing.orDash())
    println(LocalDate.of(2025, 3, 8).isWeekend)
    println(listOf("java", "kotlin", "kotlin", "scala").countBy { it })

    // apply: konfigurálás, a receiver (this) a visszatérési érték
    val report = Report().apply {
        title = "Havi riport"
        date = LocalDate.of(2025, 1, 31)
        lines += "Bevétel: 1,2M"
    }

    // also: mellékhatás, az eredeti objektumot adja tovább
    val saved = report.also { println("Mentés: ${it.title}") }

    // let: transzformáció null-ellenőrzéssel
    val formatted = saved.date?.let { DateTimeFormatter.ISO_DATE.format(it) } ?: "nincs dátum"

    // run: blokk a receiverrel, az utolsó kifejezés az eredmény
    val summary = report.run { "$title ($formatted): ${lines.size} sor" }

    // with: ha már megvan az objektum
    val csv = with(StringBuilder()) {
        append("title;date\n")
        append("${report.title};$formatted")
        toString()
    }
    println(summary)
    println(csv)
}
```

## Magasabb rendű függvények, inline és reified
<!-- q: Mit csinál az inline, a reified, a noinline és a crossinline Kotlinban? -->
<!-- tags: higher-order functions, inline, reified, noinline, crossinline, lambda with receiver, non-local return -->

A magasabb rendű függvény függvényt kap vagy ad vissza; normál esetben minden lambda egy objektum (allokáció, virtuális hívás). Az `inline` függvény törzse és a kapott lambdák a hívás helyére másolódnak: nincs allokáció, a lambdából `return`-nel a külső függvényből is ki lehet lépni (non-local return), és a `reified` típusparaméter futásidőben is elérhető (`is T`, `T::class`) a type erasure ellenére. A `noinline` lambdát objektumként eltárolhatjuk, a `crossinline` lambda pedig másik végrehajtási kontextusban (pl. `Runnable`-ben) fut, ezért tilos benne a non-local return. Csak kis, lambdát kapó függvényeket inline-oljunk, különben nő a bájtkód mérete.

```kotlin
import kotlin.system.measureTimeMillis

// Újrapróbálás exponenciális backoff-fal; az inline miatt a block nem allokálódik
inline fun <T> retry(times: Int, delayMs: Long = 100, block: (attempt: Int) -> T): T {
    var last: Throwable? = null
    repeat(times) { attempt ->
        try {
            return block(attempt + 1)                   // non-local return: a retry-ból tér vissza
        } catch (e: Exception) {
            last = e
            Thread.sleep(delayMs * (1L shl attempt))
        }
    }
    throw IllegalStateException("$times próbálkozás után is hiba", last)
}

// reified: a T futásidőben is ismert, nem kell Class<T> paraméter
inline fun <reified T> Iterable<*>.firstOfType(): T? = firstOrNull { it is T } as T?

inline fun <reified T : Enum<T>> enumOrNull(name: String): T? =
    enumValues<T>().firstOrNull { it.name.equals(name, ignoreCase = true) }

// crossinline: az action egy másik (nem inline) lambdában fut; noinline: objektumként adjuk tovább
inline fun runInBackground(noinline onDone: (Long) -> Unit, crossinline action: () -> Unit): Thread =
    Thread {
        val t = measureTimeMillis { action() }
        onDone(t)
    }.apply { start() }

fun multiplier(factor: Int): (Int) -> Int = { it * factor }   // függvényt visszaadó függvény

// Receiveres függvénytípus – a DSL-ek alapja
fun buildCsvRow(block: MutableList<String>.() -> Unit): String =
    mutableListOf<String>().apply(block).joinToString(";")

enum class Level { DEBUG, INFO, WARN }

fun main() {
    var calls = 0
    val result = retry(times = 3, delayMs = 10) { attempt ->
        calls++
        if (attempt < 3) throw RuntimeException("átmeneti hiba #$attempt")
        "siker a(z) $attempt. próbára"
    }
    println("$result, hívások: $calls")

    val mixed: List<Any> = listOf(1, "kettő", 3.0, "négy")
    println(mixed.firstOfType<Double>())
    println(enumOrNull<Level>("warn"))

    runInBackground({ ms -> println("kész $ms ms alatt") }) { Thread.sleep(20) }.join()

    val triple = multiplier(3)
    println(listOf(1, 2, 3).map(triple))
    println(buildCsvRow { add("név"); add("kor"); add("város") })
}
```

## Generikusok és variancia (in, out, star projection)
<!-- q: Hogyan működik a variancia Kotlinban, mit jelent az in, az out és a star projection? -->
<!-- tags: generics, variance, covariance, contravariance, in, out, star projection, where -->

Kotlinban a varianciát a deklaráció helyén adjuk meg: `out T` (kovariáns, T csak kimenet – `Source<Cat>` használható `Source<Animal>`-ként), `in T` (kontravariáns, T csak bemenet – `Sink<Any>` jó `Sink<Animal>` helyére). Ez a Java wildcardjainak (`? extends`/`? super`) tisztább megfelelője; invariáns típusoknál (pl. `MutableList`) a használat helyén is írhatunk projekciót (`MutableList<out Animal>`). A star projection (`List<*>`) ismeretlen típusparamétert jelent, csak biztonságos olvasást enged. Több felső korlátot `where` záradékkal adunk meg; a type erasure itt is érvényes, kivéve az inline `reified` függvényeket.

```kotlin
interface Source<out T> { fun next(): T? }      // csak kimenet
interface Sink<in T> { fun put(item: T) }       // csak bemenet

open class Animal(val name: String) { override fun toString() = "${this::class.simpleName}($name)" }
class Cat(name: String) : Animal(name)
class Dog(name: String) : Animal(name)

class ListSource<out T>(private val items: List<T>) : Source<T> {
    private var i = 0
    override fun next(): T? = items.getOrNull(i++)
}

class PrintingSink : Sink<Any> {
    override fun put(item: Any) = println("-> $item")
}

// Source<Cat> -> Source<Animal> (out), Sink<Any> -> Sink<Animal> (in)
fun pipe(from: Source<Animal>, to: Sink<Animal>) {
    while (true) to.put(from.next() ?: return)
}

// Használat-oldali projekció invariáns MutableList-en
fun copyInto(src: MutableList<out Animal>, dst: MutableList<in Animal>) {
    src.forEach { dst.add(it) }
}

// Felső korlát és több korlát (where)
fun <T> longestName(items: List<T>): T? where T : Animal = items.maxByOrNull { it.name.length }

fun <T> sortedNames(items: Collection<T>): List<String> where T : Animal, T : Comparable<T> =
    items.sorted().map { it.name }

class Ranked(name: String, val score: Int) : Animal(name), Comparable<Ranked> {
    override fun compareTo(other: Ranked) = score.compareTo(other.score)
}

// Star projection: ismeretlen elemtípus, csak Any?-ként olvasható
fun describeAll(list: List<*>) = list.joinToString { it?.javaClass?.simpleName ?: "null" }

fun main() {
    val cats: Source<Cat> = ListSource(listOf(Cat("Cirmi"), Cat("Mici")))
    pipe(cats, PrintingSink())

    val zoo = mutableListOf<Any>()
    copyInto(mutableListOf(Dog("Bodri")), zoo)
    println(zoo)

    println(longestName(listOf(Cat("Ab"), Cat("Abcd"))))
    println(sortedNames(listOf(Ranked("b", 2), Ranked("a", 1))))
    println(describeAll(listOf(1, "x", null, 2.5)))
}
```

## Kollekciók és lusta Sequence-ek
<!-- q: Hogyan dolgozzak fel kollekciókat Kotlinban, és mikor használjak Sequence-et? -->
<!-- tags: collections, list, map, groupby, fold, partition, sequence, lazy evaluation, buildlist -->

A Kotlin megkülönbözteti a csak olvasható (`List`, `Map`, `Set`) és a módosítható (`MutableList` stb.) kollekció-interfészeket; a csak olvasható nem feltétlenül immutábilis, csak a mi nézetünkből nem módosítható. A standard könyvtár gazdag műveleteket ad (`groupBy`, `associateBy`, `partition`, `fold`, `windowed`, `zip`, `buildList`/`buildMap`), ezek mohók: minden lépés új listát hoz létre. A `Sequence` lusta, elemenkénti feldolgozás köztes kollekciók nélkül – nagy vagy végtelen adatnál és hosszú láncoknál nyerő, kis listáknál viszont a többletköltség miatt lassabb lehet. Buktató: a `Sequence` minden terminális műveletnél újra lefut.

```kotlin
data class Employee(val name: String, val dept: String, val salary: Int, val skills: Set<String>)

fun main() {
    val staff = listOf(
        Employee("Anna", "IT", 950_000, setOf("kotlin", "sql")),
        Employee("Bence", "IT", 780_000, setOf("java", "kotlin")),
        Employee("Csilla", "HR", 620_000, setOf("excel")),
        Employee("Dávid", "Sales", 700_000, setOf("excel", "sql")),
    )

    // groupBy + mapValues destrukturálással
    val avgSalary = staff.groupBy { it.dept }.mapValues { (_, list) -> list.map { it.salary }.average().toInt() }
    println(avgSalary)

    println(staff.associateBy { it.name }["Anna"]?.dept)          // Map építése kulcs szerint

    // flatMap + groupingBy.eachCount: skill-gyakoriság
    println(staff.flatMap { it.skills }.groupingBy { it }.eachCount().toList().sortedByDescending { it.second })

    // partition, fold, windowed, zip
    val (seniors, juniors) = staff.partition { it.salary >= 750_000 }
    println("${seniors.map { it.name }} / ${juniors.map { it.name }}")
    println("Bérköltség: ${staff.fold(0L) { acc, e -> acc + e.salary }}")
    println((1..10).windowed(size = 3, step = 3, partialWindows = true))
    println(staff.map { it.name }.zip(staff.map { it.salary }).take(2))

    // buildMap: mutable építés, read-only eredmény
    val report = buildMap {
        staff.forEach { put(it.name, it.skills.size) }
        put("összesen", staff.sumOf { it.skills.size })
    }
    println(report)

    // Sequence: végtelen generátor + lusta lánc
    val squaresDivBy7 = generateSequence(1) { it + 1 }.map { it * it }.filter { it % 7 == 0 }.take(5).toList()
    println(squaresDivBy7)

    // Lusta vs mohó: a sequence csak annyi elemet érint, amennyi a take(1)-hez kell
    var touched = 0
    staff.asSequence().onEach { touched++ }.filter { it.dept == "IT" }.take(1).toList()
    println("Sequence által érintett elemek: $touched")           // 1 (List-tel 4 lenne)
}
```

## Delegálás: osztály- és property-delegálás
<!-- q: Hogyan használjam a delegálást (by, by lazy, observable, saját delegate) Kotlinban? -->
<!-- tags: delegation, by, lazy, observable, vetoable, readwriteproperty, decorator, map delegation -->

Az osztály-delegálás (`class X(inner: I) : I by inner`) a Decorator mintát adja boilerplate nélkül: minden interfész-metódus a belső példányhoz megy, csak a módosítandókat írjuk felül – az öröklés helyett kompozíció. A property-delegálás a getter/setter logikát egy újrahasznosítható objektumba szervezi: `by lazy` (első hozzáféréskor számol, alapból szálbiztos), `Delegates.observable`/`vetoable` (változásfigyelés, elutasítás), `by map` (property-k Map-ből), vagy saját `ReadWriteProperty`. Buktató: a `lazy` alapértelmezett `SYNCHRONIZED` módja zárat használ – egyszálú környezetben a `LazyThreadSafetyMode.NONE` gyorsabb.

```kotlin
import kotlin.properties.Delegates
import kotlin.properties.ReadWriteProperty
import kotlin.reflect.KProperty

interface Repository<K, V> {
    fun get(key: K): V?
    fun put(key: K, value: V)
}
class InMemoryRepo<K, V> : Repository<K, V> {
    private val data = HashMap<K, V>()
    override fun get(key: K) = data[key]
    override fun put(key: K, value: V) { data[key] = value }
}

// Decorator delegálással: csak a get-et írjuk felül, a put automatikusan az inner-é
class CountingRepo<K, V>(private val inner: Repository<K, V>) : Repository<K, V> by inner {
    var reads = 0
        private set
    override fun get(key: K): V? { reads++; return inner.get(key) }
}

// Saját property-delegate: minden íráskor tartományba szorít
class Clamped(private var value: Int, private val range: IntRange) : ReadWriteProperty<Any?, Int> {
    override fun getValue(thisRef: Any?, property: KProperty<*>) = value
    override fun setValue(thisRef: Any?, property: KProperty<*>, value: Int) { this.value = value.coerceIn(range) }
}

class Settings(map: Map<String, Any?>) {
    val expensive: String by lazy { println("számolás…"); "kész" }          // egyszer számol
    var theme: String by Delegates.observable("light") { prop, old, new -> println("${prop.name}: $old -> $new") }
    var port: Int by Delegates.vetoable(8080) { _, _, new -> new in 1024..65535 } // elutasíthat
    var volume: Int by Clamped(50, 0..100)
    val host: String by map            // a property neve a kulcs
    val debug: Boolean by map
}

fun main() {
    val repo = CountingRepo(InMemoryRepo<String, Int>())
    repo.put("a", 1)
    repo.get("a"); repo.get("b")
    println("olvasások: ${repo.reads}")

    val s = Settings(mapOf("host" to "localhost", "debug" to true))
    println(s.expensive); println(s.expensive)   // a "számolás…" csak egyszer jelenik meg
    s.theme = "dark"
    s.port = 80; println(s.port)                 // 8080 marad: a vetoable elutasította
    s.volume = 150; println(s.volume)            // 100-ra vágva
    println("${s.host} debug=${s.debug}")
}
```

## Coroutine-ok alapjai: suspend, async, dispatcherek
<!-- q: Hogyan működnek a Kotlin coroutine-ok és a strukturált konkurencia? -->
<!-- tags: coroutines, suspend, async, launch, structured concurrency, dispatchers, withcontext, kotlinx.coroutines -->

A coroutine felfüggeszthető számítás: a `suspend` függvényt a fordító állapotgéppé alakítja (continuation-passing style), így várakozáskor nem blokkol szálat, és tízezres nagyságrendű coroutine is olcsó. A strukturált konkurencia szerint minden coroutine egy `CoroutineScope`-ban fut: a `coroutineScope { }` megvárja a gyerekeit, és ha egy elbukik, a testvéreit lemondja – nincs "elszökött" háttérmunka. A `launch` eredmény nélküli Job-ot, az `async` `Deferred`-et ad (`await`), a `withContext` dispatchert vált: `Dispatchers.Default` CPU-munkára, `Dispatchers.IO` blokkoló I/O-ra, `Main` UI-ra. A `runBlocking` csak `main`-ben és tesztben használható, a `GlobalScope` kerülendő.

```kotlin
import kotlinx.coroutines.*
import kotlin.system.measureTimeMillis

data class User(val id: Int, val name: String)
data class Dashboard(val user: User, val notifications: Int, val weather: String)

// Hálózati hívások szimulációja: a delay felfüggeszt, nem blokkol
suspend fun fetchUser(id: Int): User { delay(300); return User(id, "user$id") }
suspend fun fetchNotifications(id: Int): Int { delay(200); return 3 }
suspend fun fetchWeather(): String { delay(250); return "napos, 21°C" }

// Strukturált konkurencia: ha bármelyik async elbukik, a többi lemondódik, és a hiba továbbterjed
suspend fun loadDashboard(id: Int): Dashboard = coroutineScope {
    val user = async { fetchUser(id) }
    val notifications = async { fetchNotifications(id) }
    val weather = async { fetchWeather() }
    Dashboard(user.await(), notifications.await(), weather.await())
}

// CPU-munka a Default dispatcheren
suspend fun checksum(data: String): String = withContext(Dispatchers.Default) {
    (1..100_000).fold(data.hashCode()) { acc, i -> acc * 31 + i }.toString(16)
}

// Blokkoló I/O (fájl, JDBC) az IO dispatcheren
suspend fun readConfig(): String = withContext(Dispatchers.IO) {
    "port=8080" // itt lenne a blokkoló olvasás
}

fun main() = runBlocking {
    val time = measureTimeMillis { println(loadDashboard(7)) }
    println("Idő: $time ms (párhuzamos: ~300 ms, nem 750)")

    // launch: "fire and forget" Job, join-nal várható
    val job = launch {
        repeat(3) { i -> println("háttérmunka $i"); delay(100) }
    }
    println(checksum("adat") + " / " + readConfig())
    job.join()

    // 10 000 coroutine is olcsó: nem szálak, hanem felfüggeszthető objektumok
    val total = (1..10_000).map { async { delay(10); it } }.awaitAll().sum()
    println("Összeg: $total")
}
```

## Coroutine-ok: lemondás, hibakezelés, supervisor, Mutex
<!-- q: Hogyan kezeljem a hibákat és a lemondást Kotlin coroutine-okban? -->
<!-- tags: cancellation, supervisorjob, supervisorscope, coroutineexceptionhandler, withtimeout, mutex, noncancellable -->

A lemondás kooperatív: a felfüggesztési pontok (`delay`, `await`, `yield`) ellenőrzik, a hosszú CPU-ciklusnak magának kell `ensureActive()`-ot vagy `isActive`-ot hívnia. Normál Job-ban egy gyerek hibája lemondja a szülőt és a testvéreket; a `SupervisorJob`/`supervisorScope` ezt megakadályozza, így független feladatok (pl. képfeldolgozás) egymástól függetlenül bukhatnak el. A `launch` kezeletlen kivételét `CoroutineExceptionHandler` kapja el, az `async` kivétele az `await()`-nél jelenik meg. Buktatók: a `CancellationException`-t soha ne nyeljük le általános `catch (e: Exception)`-nel, a `finally`-ben felfüggesztő takarításhoz `withContext(NonCancellable)` kell, a közös állapotot pedig `Mutex`-szel (nem blokkoló zár) védjük.

```kotlin
import kotlinx.coroutines.*
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

class ImageService {
    private val handler = CoroutineExceptionHandler { _, e -> println("kezeletlen hiba: ${e.message}") }
    // SupervisorJob: egy gyerek hibája NEM lövi le a testvéreit és a scope-ot
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default + handler)
    private val mutex = Mutex()
    private var processed = 0

    fun processAll(ids: List<Int>): List<Job> = ids.map { id ->
        scope.launch(CoroutineName("img-$id")) {
            if (id == 3) error("sérült kép: $id")        // csak ez a gyerek bukik el
            delay(100)
            mutex.withLock { processed++ }               // nem blokkoló kölcsönös kizárás
        }
    }
    suspend fun processedCount() = mutex.withLock { processed }
    fun shutdown() = scope.cancel()                      // minden futó munka lemondása
}

// Kooperatív lemondás CPU-ciklusban
suspend fun crunch(): Long = withContext(Dispatchers.Default) {
    var acc = 0L
    for (i in 0 until 2_000_000_000) {
        if (i % 1_000_000 == 0) ensureActive()           // lemondáskor CancellationException
        acc += i
    }
    acc
}

fun main() = runBlocking {
    val svc = ImageService()
    svc.processAll(listOf(1, 2, 3, 4)).joinAll()
    println("feldolgozva: ${svc.processedCount()}")      // 3 – a hibás nem rontotta el a többit

    println("időkorláttal: ${withTimeoutOrNull(200) { crunch() }}")   // null

    // supervisorScope: az async hibája nem lövi le a szülőt, az await()-nél kapjuk el
    supervisorScope {
        val deferred = async { throw IllegalStateException("upstream 503") }
        try { deferred.await() } catch (e: IllegalStateException) { println("elkapva: ${e.message}") }
    }

    // finally + NonCancellable: felfüggesztő takarítás lemondott coroutine-ban is
    val job = launch {
        try { awaitCancellation() }
        finally { withContext(NonCancellable) { delay(50); println("erőforrás lezárva") } }
    }
    delay(50)
    job.cancelAndJoin()
    svc.shutdown()
}
```

## Flow, StateFlow és SharedFlow
<!-- q: Hogyan használjam a Kotlin Flow-t, StateFlow-t és SharedFlow-t reaktív adatfolyamokhoz? -->
<!-- tags: flow, stateflow, sharedflow, cold flow, hot flow, debounce, flatmaplatest, statein, operators -->

A `Flow` hideg (cold) aszinkron adatfolyam: a `flow { emit(...) }` blokk csak `collect`-kor indul, és minden gyűjtő saját futást kap; az operátorok (`map`, `filter`, `debounce`, `flatMapLatest`, `catch`) lusták és felfüggeszthetők. A `StateFlow` forró, mindig van aktuális értéke és csak a változást adja tovább – UI-állapotra való; a `SharedFlow` egyszeri eseményekhez (navigáció, toast) használható. A `stateIn`/`shareIn` egy hideg flow-t oszt meg több gyűjtő között, a `flowOn` a felette lévő lépések dispatcherét váltja. Buktatók: a `flow { }` belsejében tilos `withContext`-tel kontextust váltani (helyette `flowOn`), és a forró flow-k gyűjtését életciklushoz kell kötni.

```kotlin
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*

data class Tick(val symbol: String, val price: Double)

// Hideg, végtelen flow: minden collect újraindítja
fun priceTicks(symbol: String): Flow<Tick> = flow {
    var price = 100.0
    while (true) {
        price += (-2..2).random()
        emit(Tick(symbol, price))
        delay(50)
    }
}

class SearchViewModel(scope: CoroutineScope) {
    private val _query = MutableStateFlow("")             // UI-állapot
    val query: StateFlow<String> = _query.asStateFlow()

    private val _events = MutableSharedFlow<String>(extraBufferCapacity = 8) // egyszeri események
    val events: SharedFlow<String> = _events

    @OptIn(FlowPreview::class, ExperimentalCoroutinesApi::class)
    val results: StateFlow<List<String>> = _query
        .debounce(300)                                     // gépelés közben ne keressen
        .map { it.trim() }
        .distinctUntilChanged()
        .flatMapLatest { q -> if (q.length < 2) flowOf(emptyList()) else search(q) } // régi keresés lemondva
        .catch { e -> _events.emit("hiba: ${e.message}"); emit(emptyList()) }
        .stateIn(scope, SharingStarted.WhileSubscribed(5_000), emptyList())

    fun onQueryChanged(q: String) { _query.value = q }

    private fun search(q: String): Flow<List<String>> = flow {
        delay(100)                                         // hálózati hívás helye
        emit(listOf("kotlin", "ktor", "koin", "compose").filter { it.startsWith(q) })
    }
}

fun main() = runBlocking {
    priceTicks("AURI")
        .map { it.price }
        .runningReduce { acc, p -> (acc + p) / 2 }         // simítás
        .take(5)                                           // a végtelen flow lezárása
        .flowOn(Dispatchers.Default)                       // a felette lévő rész más dispatcheren fut
        .collect { println("simított ár: %.2f".format(it)) }

    val vm = SearchViewModel(this)
    launch { vm.results.collect { println("találatok: $it") } }
    listOf("k", "ko", "kot").forEach { vm.onQueryChanged(it); delay(100) }
    delay(600)
    coroutineContext.cancelChildren()                     // a gyűjtő és a stateIn leállítása
}
```

## Típusbiztos DSL builderek
<!-- q: Hogyan írjak típusbiztos DSL-t Kotlinban receiveres lambdákkal és @DslMarker-rel? -->
<!-- tags: dsl, type-safe builder, lambda with receiver, dslmarker, operator overloading, builder pattern -->

A Kotlin DSL-ek alapja a receiveres lambda (`T.() -> Unit`): a blokkon belül a `this` az épülő objektum, így a metódusai minősítés nélkül hívhatók, és normál vezérlési szerkezetek (`for`, `if`) is használhatók benne. Így épül fel a Gradle Kotlin DSL, a kotlinx.html, a Ktor routing és a Compose is. A `@DslMarker` annotáció megakadályozza, hogy egy belső blokkban véletlenül a külső receiver metódusait hívjuk (pl. `li`-n belül `h1`-et). Az `operator fun String.unaryPlus()` adja a `+"szöveg"` szintaxist; a DSL legyen kicsi és jól dokumentált, mert a túl sok implicit receiver rontja az olvashatóságot.

```kotlin
@DslMarker
annotation class HtmlDsl

@HtmlDsl
abstract class Tag(private val name: String) {
    private val children = mutableListOf<Tag>()
    private val attributes = linkedMapOf<String, String>()

    // A block-on belül a `this` az új tag
    protected fun <T : Tag> initTag(tag: T, block: T.() -> Unit): T {
        tag.block()
        children += tag
        return tag
    }
    operator fun String.unaryPlus() { children += Text(this) }   // +"szöveg"
    fun attr(key: String, value: String) { attributes[key] = value }

    open fun render(sb: StringBuilder, indent: String) {
        val attrs = attributes.entries.joinToString("") { (k, v) -> " $k=\"$v\"" }
        sb.append("$indent<$name$attrs>\n")
        children.forEach { it.render(sb, "$indent  ") }
        sb.append("$indent</$name>\n")
    }
    override fun toString() = StringBuilder().also { render(it, "") }.toString()
}

class Text(private val text: String) : Tag("#text") {
    override fun render(sb: StringBuilder, indent: String) { sb.append("$indent$text\n") }
}
class Html : Tag("html") {
    fun body(block: Body.() -> Unit) = initTag(Body(), block)
}
class Body : Tag("body") {
    fun h1(block: H1.() -> Unit) = initTag(H1(), block)
    fun ul(block: Ul.() -> Unit) = initTag(Ul(), block)
    fun a(href: String, block: A.() -> Unit) = initTag(A(), block).also { it.attr("href", href) }
}
class H1 : Tag("h1")
class A : Tag("a")
class Li : Tag("li")
class Ul : Tag("ul") {
    fun li(block: Li.() -> Unit) = initTag(Li(), block)
}

fun html(block: Html.() -> Unit): Html = Html().apply(block)   // belépési pont

fun main() {
    val langs = listOf("Kotlin", "Scala", "Groovy")
    val page = html {
        body {
            h1 { +"JVM nyelvek" }
            ul {
                for (lang in langs) li { +lang }   // normál vezérlési szerkezet a DSL-ben
                // h1 { }  <- a @DslMarker miatt fordítási hiba: a Body itt nem implicit receiver
            }
            a(href = "https://kotlinlang.org") { +"Dokumentáció" }
        }
    }
    print(page)
}
```

## Hibakezelés: kivételek, Result és típusos hibák
<!-- q: Hogyan kezeljem a hibákat idiomatikusan Kotlinban kivételekkel, Result-tal és sealed hibatípusokkal? -->
<!-- tags: error handling, exceptions, result, runcatching, either, sealed errors, require, check -->

Kotlinban nincsenek checked kivételek: a fordító nem kényszerít `catch`-re, ezért a várható, üzleti hibákat érdemes a típusban jelezni (sealed hibahierarchia, Either-szerű típus vagy az Arrow könyvtár), a kivételt pedig a valóban váratlan helyzetekre tartani. A beépített `Result` és `runCatching` gyors csomagolást ad (`map`, `recover`, `getOrElse`), de elkapja a `CancellationException`-t is, ezért coroutine-okban óvatosan használjuk. A `require` paraméterhibára (`IllegalArgumentException`), a `check` állapothibára (`IllegalStateException`), az `error()` általános hibára dob. Az infrastruktúra-kivételeket a határon érdemes domain-hibává alakítani.

```kotlin
import java.io.IOException

sealed interface DomainError {
    data class NotFound(val id: String) : DomainError
    data class Validation(val field: String, val msg: String) : DomainError
    data class Infra(val cause: Throwable) : DomainError
}

// Minimális Either-szerű típus (az Arrow ezt teljes értékűen adja)
sealed interface Outcome<out E, out A> {
    data class Ok<A>(val value: A) : Outcome<Nothing, A>
    data class Fail<E>(val error: E) : Outcome<E, Nothing>
}
inline fun <E, A, B> Outcome<E, A>.flatMap(f: (A) -> Outcome<E, B>): Outcome<E, B> = when (this) {
    is Outcome.Ok -> f(value)
    is Outcome.Fail -> this
}

data class Product(val id: String, val price: Int)

fun parseQuantity(raw: String): Outcome<DomainError, Int> =
    raw.toIntOrNull()?.takeIf { it > 0 }?.let { Outcome.Ok(it) }
        ?: Outcome.Fail(DomainError.Validation("qty", "pozitív egész kell: '$raw'"))

fun findProduct(id: String): Outcome<DomainError, Product> = try {
    if (id == "net-err") throw IOException("connection reset")
    if (id.startsWith("P")) Outcome.Ok(Product(id, 2490)) else Outcome.Fail(DomainError.NotFound(id))
} catch (e: IOException) {
    Outcome.Fail(DomainError.Infra(e))              // infrastruktúra-hiba -> domain-hiba
}

fun quote(id: String, qty: String): String {
    val result = findProduct(id).flatMap { p -> parseQuantity(qty).flatMap { q -> Outcome.Ok(p.price * q) } }
    return when (result) {
        is Outcome.Ok -> "Ár: ${result.value} Ft"
        is Outcome.Fail -> when (val e = result.error) {   // kimerítő a sealed miatt
            is DomainError.NotFound -> "Nincs ilyen termék: ${e.id}"
            is DomainError.Validation -> "Hibás ${e.field}: ${e.msg}"
            is DomainError.Infra -> "Szolgáltatás nem elérhető (${e.cause.message})"
        }
    }
}

fun main() {
    listOf("P-1" to "3", "X-9" to "1", "P-1" to "nulla", "net-err" to "1")
        .forEach { (id, qty) -> println(quote(id, qty)) }

    // Beépített Result: gyors csomagolás és helyreállítás
    val port = runCatching { "80a".toInt() }.recover { 8080 }.getOrThrow()
    println(port)

    // require -> IllegalArgumentException, check -> IllegalStateException
    runCatching { require(port in 1..65535) { "érvénytelen port" } }.onSuccess { println("port ok") }
}
```

## Java interoperabilitás
<!-- q: Hogyan működik együtt a Kotlin és a Java kód, mire valók a @JvmStatic, @JvmOverloads és társai? -->
<!-- tags: java interop, jvmstatic, jvmoverloads, jvmfield, jvmname, throws, platform types, sam conversion -->

A Kotlin ugyanarra a JVM-bájtkódra fordul, ezért a két nyelv osztályai kölcsönösen hívhatják egymást egy projekten belül is. Java felől a Kotlin-sajátosságokat annotációk teszik kényelmessé: `@JvmOverloads` (alapértelmezett paraméterekből overloadok), `@JvmStatic` (valódi statikus metódus `object`/`companion`-ban), `@JvmField` (getter nélküli mező), `@file:JvmName` (a top-level függvényeket tartalmazó osztály neve), `@Throws` (a `throws` záradék a Java hívónak). Kotlin felől a Java típusok platform típusok (`String!`), ezért a nullabilitást nekünk kell eldönteni; a Java funkcionális interfészek lambdával hívhatók (SAM-konverzió).

```kotlin
@file:JvmName("TextUtils") // a top-level függvények Java-ból: TextUtils.capitalizeWords(...)

package com.example.interop

import java.util.Optional

// @JvmOverloads: Java-ból is használhatók az alapértelmezett paraméterek
class HttpConfig @JvmOverloads constructor(
    val host: String,
    val port: Int = 443,
    val tls: Boolean = true,
)

object Registry {
    @JvmStatic fun lookup(name: String): HttpConfig? = if (name == "api") HttpConfig("api.local") else null
    @JvmField val DEFAULT_TIMEOUT_MS = 5_000L      // publikus mező getter nélkül
    const val VERSION = "1.4.2"                    // fordítási idejű konstans
}

// @Throws: a Java hívó számára checked kivételként jelenik meg
@Throws(java.io.IOException::class)
fun readFirstLine(path: String): String = java.io.File(path).bufferedReader().use { it.readLine() ?: "" }

// Extension Java-ból statikus metódusként látszik, első paraméter a receiver
fun String.capitalizeWords(): String = split(" ").joinToString(" ") { w -> w.replaceFirstChar { it.uppercase() } }

fun <T : Any> Optional<T>.orNullKt(): T? = orElse(null)   // Optional -> nullable

fun startWorker(): Thread = Thread { println("Fut: ${Thread.currentThread().name}") }.apply { start() } // SAM

fun main() {
    val home: String? = System.getProperty("user.home")      // platform típus -> mi döntünk
    println(home?.length)
    println(Registry.lookup("api")?.port)
    println("kotlin java interop".capitalizeWords())
    println(Optional.empty<String>().orNullKt() ?: "üres")
    startWorker().join()
}
```

```java
// Java oldali hívások a fenti Kotlin kódra (a com.example.interop csomagban)
HttpConfig a = new HttpConfig("example.com");          // @JvmOverloads miatt létezik
HttpConfig b = new HttpConfig("example.com", 8443);
HttpConfig c = Registry.lookup("api");                 // @JvmStatic: nincs INSTANCE
long timeout = Registry.DEFAULT_TIMEOUT_MS;            // @JvmField
String title = TextUtils.capitalizeWords("hello world"); // @file:JvmName
```

## Android és Jetpack Compose alapok
<!-- q: Hogyan épül fel egy egyszerű Android képernyő Jetpack Compose-zal és ViewModellel? -->
<!-- tags: android, jetpack compose, viewmodel, stateflow, recomposition, state hoisting, lazycolumn -->

A Jetpack Compose deklaratív UI-keretrendszer: a `@Composable` függvények az állapotból írják le a felületet, és állapotváltozáskor a futtatókörnyezet csak az érintett részeket futtatja újra (recomposition). Az ajánlott architektúra egyirányú adatfolyam: a `ViewModel` (túléli a képernyőforgatást) `StateFlow`-ban tartja az immutábilis UI-állapotot, a UI eseményeket küld vissza, a composable pedig `collectAsStateWithLifecycle()`-lel életciklus-tudatosan gyűjt. A state hoisting miatt az állapotmentes composable könnyen tesztelhető és előnézhető. Buktatók: composable-ben ne végezzünk mellékhatást közvetlenül (arra `LaunchedEffect` való), és listáknál adjunk stabil `key`-t.

```kotlin
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

data class Todo(val id: Int, val title: String, val done: Boolean = false)
data class TodoUiState(val items: List<Todo> = emptyList(), val input: String = "")

class TodoViewModel : ViewModel() {
    private val _state = MutableStateFlow(TodoUiState())
    val state: StateFlow<TodoUiState> = _state.asStateFlow()

    fun onInputChange(text: String) = _state.update { it.copy(input = text) }

    fun add() {
        val title = _state.value.input.trim()
        if (title.isEmpty()) return
        viewModelScope.launch {                     // a ViewModel törlésekor automatikusan lemondódik
            delay(50)                               // pl. Room adatbázis-írás helye
            _state.update { s -> s.copy(items = s.items + Todo(s.items.size + 1, title), input = "") }
        }
    }

    fun toggle(id: Int) = _state.update { s ->
        s.copy(items = s.items.map { if (it.id == id) it.copy(done = !it.done) else it })
    }
}

@Composable
fun TodoScreen(vm: TodoViewModel = viewModel()) {
    val state by vm.state.collectAsStateWithLifecycle()   // életciklus-tudatos gyűjtés
    TodoContent(state, vm::onInputChange, vm::add, vm::toggle)
}

// Állapotmentes composable (state hoisting): minden adat paraméterként jön
@Composable
fun TodoContent(state: TodoUiState, onInput: (String) -> Unit, onAdd: () -> Unit, onToggle: (Int) -> Unit) {
    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(value = state.input, onValueChange = onInput,
                label = { Text("Új feladat") }, modifier = Modifier.weight(1f))
            Spacer(Modifier.width(8.dp))
            Button(onClick = onAdd, enabled = state.input.isNotBlank()) { Text("Hozzáad") }
        }
        LazyColumn {                                       // csak a látható elemeket rajzolja
            items(state.items, key = { it.id }) { todo ->
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(checked = todo.done, onCheckedChange = { onToggle(todo.id) })
                    Text(todo.title, style = MaterialTheme.typography.bodyLarge)
                }
            }
        }
    }
}
```

## Ktor szerver: REST API coroutine-okkal
<!-- q: Hogyan írjak REST API-t Ktorral Kotlinban? -->
<!-- tags: ktor, rest api, routing, content negotiation, kotlinx.serialization, status pages, netty -->

A Ktor a JetBrains coroutine-alapú, könnyűsúlyú webes keretrendszere: minden kéréskezelő egy coroutine, így a `call.receive`/`call.respond` és a felfüggesztő I/O nem blokkol szálat. A funkciókat pluginként telepítjük (`ContentNegotiation` JSON-hoz `kotlinx.serialization`-nel, `StatusPages` kivétel → HTTP-válasz leképezéshez, `Authentication`, `CallLogging`), az útvonalakat a `routing { }` DSL-lel írjuk. Az alkalmazást `Application.module()` extension függvényekbe szervezzük, így tesztben a `testApplication { }` ugyanazt a modult indítja HTTP-szerver nélkül. Buktató: kéréskezelőben ne hívjunk blokkoló kódot (JDBC) `Dispatchers.IO` nélkül.

```kotlin
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import io.ktor.server.application.*
import io.ktor.server.engine.*
import io.ktor.server.netty.*
import io.ktor.server.plugins.contentnegotiation.*
import io.ktor.server.plugins.statuspages.*
import io.ktor.server.request.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import kotlinx.serialization.Serializable
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicInteger

@Serializable data class Book(val id: Int, val title: String, val author: String)
@Serializable data class NewBook(val title: String, val author: String)
@Serializable data class ApiError(val error: String)

class BookRepository {
    private val books = ConcurrentHashMap<Int, Book>()
    private val seq = AtomicInteger()
    fun all() = books.values.sortedBy { it.id }
    fun get(id: Int) = books[id]
    fun add(b: NewBook) = Book(seq.incrementAndGet(), b.title, b.author).also { books[it.id] = it }
    fun delete(id: Int) = books.remove(id) != null
}

fun Application.module(repo: BookRepository = BookRepository()) {
    install(ContentNegotiation) { json() }                       // JSON <-> data class
    install(StatusPages) {
        exception<IllegalArgumentException> { call, e ->
            call.respond(HttpStatusCode.BadRequest, ApiError(e.message ?: "hibás kérés"))
        }
    }
    routing {
        route("/api/books") {
            get { call.respond(repo.all()) }
            get("/{id}") {
                val id = call.parameters["id"]?.toIntOrNull() ?: throw IllegalArgumentException("érvénytelen id")
                val book = repo.get(id)
                if (book == null) call.respond(HttpStatusCode.NotFound, ApiError("nincs ilyen könyv: $id"))
                else call.respond(book)
            }
            post {
                val body = call.receive<NewBook>()                // deszerializálás
                require(body.title.isNotBlank()) { "a cím kötelező" } // -> 400 a StatusPages-en át
                call.respond(HttpStatusCode.Created, repo.add(body))
            }
            delete("/{id}") {
                val id = call.parameters["id"]?.toIntOrNull() ?: throw IllegalArgumentException("érvénytelen id")
                call.respond(if (repo.delete(id)) HttpStatusCode.NoContent else HttpStatusCode.NotFound)
            }
        }
    }
}

fun main() {
    embeddedServer(Netty, port = 8080) { module() }.start(wait = true)
}
```
