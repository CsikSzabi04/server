# Groovy
<!-- tech: groovy -->
<!-- aliases: apache groovy, gdk, groovy script, gradle groovy dsl, spock -->

A Groovy (Apache Groovy) dinamikus, opcionálisan statikusan típusos JVM-nyelv, amely szintaxisában szinte a Java szuperhalmaza, így a Java kód többnyire változtatás nélkül is érvényes Groovy. Erőssége a tömörség (closure-ök, lista/map literálok, GString, a Groovy Development Kit kiegészítő metódusai), a futásidejű és fordítási idejű metaprogramozás (MetaClass, AST-transzformációk) és a DSL-építés, a memóriát a JVM GC-je kezeli. Leggyakrabban a Gradle build-szkriptek (Groovy DSL), a Jenkins pipeline-ok, a Spock tesztkeretrendszer, a Grails webes keretrendszer és az ad-hoc JVM-szkriptelés nyelve. Dinamikus módban lassabb és kevesebb hibát fog meg fordításkor, ezért teljesítmény- vagy biztonságkritikus kódban a `@CompileStatic` ajánlott, nagy alkalmazásokra pedig ma inkább Javát vagy Kotlint választanak.

## Dinamikus és statikus típusosság
<!-- q: Hogyan működik a dinamikus típusosság Groovyban, és mikor használjam a @CompileStatic-ot? -->
<!-- tags: dynamic typing, def, duck typing, compilestatic, typechecked, multimethods, optional typing -->

Groovyban a `def` dinamikus típust jelent: a metódushívás futásidőben, a MetaClass-on keresztül oldódik fel, ezért működik a duck typing (bármi, aminek van `quack()` metódusa), és a túlterhelt metódusok közül a FUTÁSIDEJŰ argumentumtípus alapján választ (multimethods) – Javában ez fordítási időben dől el. A `@TypeChecked` Java-szerű típusellenőrzést ad fordításkor, a `@CompileStatic` emellett statikus dispatch-et is, így a kód közel Java-sebességű, de a futásidejű metaprogramozás nem érvényesül rá. Sok elem opcionális: pontosvessző, zárójel a hívásnál, `return`, `public`. Buktató: dinamikus kódban az elírt metódusnév csak futáskor derül ki (`MissingMethodException`).

```groovy
import groovy.transform.CompileStatic
import groovy.transform.TypeChecked

// Multimethod: a futásidejű típus dönt a túlterhelések között
String greet(String s) { "szöveg: $s" }
String greet(Object o) { "objektum: $o" }

def describe(x) { x.getClass().simpleName }

// @TypeChecked: fordítási idejű típusellenőrzés
@TypeChecked
int sumLengths(List<String> words) {
    int total = 0
    for (String w : words) total += w.length()
    // total += words.foo()   <- fordítási hiba lenne
    return total
}

// @CompileStatic: statikus dispatch, Java-közeli sebesség
@CompileStatic
long fib(int n) {
    long a = 0, b = 1
    for (int i = 0; i < n; i++) {
        long t = a + b
        a = b
        b = t
    }
    return a
}

// Duck typing: nincs közös interfész, csak azonos metódusnév
class Duck { String quack() { 'Háp!' } }
class Robot { String quack() { 'BEEP-háp' } }
def makeNoise(thing) { thing.quack() }

Object o = 'Groovy'
println greet(o)                         // "szöveg: Groovy" – Javában "objektum: ..." lenne
println "${describe(42)} ${describe([1, 2])} ${describe([a: 1])}"  // Integer ArrayList LinkedHashMap
println sumLengths(['jvm', 'groovy'])
println fib(90)
println([new Duck(), new Robot()].collect { makeNoise(it) })

def numbers = [3, 1, 2]
println numbers.sort(false)              // false: nem módosítja az eredeti listát
assert numbers == [3, 1, 2]

def value = 10                           // a def változó típusa futás közben változhat
value = 'most már String'
println value.toUpperCase()
```

## Closure-ök: delegate, currying, memoizálás
<!-- q: Hogyan működnek a closure-ök Groovyban, és mi a különbség a this, owner és delegate között? -->
<!-- tags: closure, delegate, owner, resolve strategy, currying, memoize, composition, method pointer -->

A closure (`{ a, b -> ... }`, egy paraméternél implicit `it`) első osztályú kódblokk, amely lezárja a környezetét, így állapotot is hordozhat. Három hivatkozása van: `this` (a befoglaló osztály), `owner` (a befoglaló objektum vagy closure) és `delegate` (alapból az owner, de átállítható) – a `resolveStrategy` (`DELEGATE_FIRST`, `OWNER_FIRST`) dönti el, hol keresi a nem minősített neveket, és erre épül minden Groovy DSL (Gradle, builderek). Funkcionális eszközök: `curry`/`rcurry`, kompozíció (`>>`, `<<`), `memoize()` a tiszta függvények gyorsítótárazására, metóduspointer (`.&`). Az utolsó closure-paraméter a zárójelen kívülre írható.

```groovy
// Állapotot lezáró closure
def counter() {
    int count = 0
    return { -> ++count }
}
def next = counter()
3.times { next() }
println "számláló: ${next()}"                     // 4

// Currying és kompozíció
def priceWithVat = { BigDecimal net, BigDecimal rate -> net * (1 + rate) }
def huPrice = priceWithVat.rcurry(0.27)            // a jobb oldali paraméter rögzítése
def round2 = { BigDecimal v -> v.setScale(2, java.math.RoundingMode.HALF_UP) }
def finalPrice = huPrice >> round2                 // előbb huPrice, aztán round2
println finalPrice(1000.0)                         // 1270.00

// Memoizálás tiszta, drága függvényre
def slowSquare = { int n -> Thread.sleep(50); n * n }.memoize()
println((1..3).collect(slowSquare) + (1..3).collect(slowSquare))   // a második kör cache-ből

// delegate + DELEGATE_FIRST: mini-DSL
class EmailSpec {
    String to, subject, body
    void to(String v) { to = v }
    void subject(String v) { subject = v }
    void body(String v) { body = v }
    String toString() { "To: $to | $subject | $body" }
}
def email(@DelegatesTo(value = EmailSpec, strategy = Closure.DELEGATE_FIRST) Closure spec) {
    def e = new EmailSpec()
    def c = spec.rehydrate(e, this, this)           // delegate = e
    c.resolveStrategy = Closure.DELEGATE_FIRST      // először a delegate-en keres
    c()
    e
}
def mail = email {
    to 'csapat@example.com'
    subject 'Kiadás kész'
    body "Verzió: ${'1.2.0'}"
}
println mail

// Az utolsó closure a zárójelen kívül
def withTiming(String label, Closure work) {
    long t0 = System.nanoTime()
    def result = work()
    println "$label: ${(System.nanoTime() - t0).intdiv(1_000_000)} ms"
    result
}
println withTiming('összegzés') { (1..100_000).sum() }

// Metóduspointer (.&): metódus closure-ként átadva
boolean isLongWord(String w) { w.size() > 5 }
def isLong = this.&isLongWord
println(['kotlin', 'jvm', 'groovy'].findAll(isLong))
```

## Kollekciók és a GDK metódusai
<!-- q: Hogyan dolgozzak fel listákat és map-eket Groovyban? -->
<!-- tags: collections, list, map, range, gdk, collect, findall, inject, groupby, spread operator -->

Groovyban a `[1, 2]` `ArrayList`, a `[a: 1]` `LinkedHashMap` (a kulcsok alapból String-ek), a `1..10` pedig `Range`. A GDK (Groovy Development Kit) minden Java kollekcióhoz closure-alapú metódusokat ad: `collect` (map), `findAll` (filter), `find`, `inject` (fold), `groupBy`, `countBy`, `collectEntries`, `sum`, `max`, `any`/`every`, `collate`, `transpose`. A spread operátor (`*.`) minden elemen kiolvassa a property-t vagy meghívja a metódust. Buktatók: a `sort()` és `unique()` alapból HELYBEN módosít (`sort(false)` másolatot ad), és a map-literálban a kulcs változóként csak zárójelben (`[(key): v]`) értékelődik ki.

```groovy
def staff = [
    [name: 'Anna',   dept: 'IT',    salary: 950_000, skills: ['groovy', 'sql']],
    [name: 'Bence',  dept: 'IT',    salary: 780_000, skills: ['java']],
    [name: 'Csilla', dept: 'HR',    salary: 620_000, skills: ['excel']],
    [name: 'Dávid',  dept: 'Sales', salary: 700_000, skills: ['excel', 'sql']],
]

println staff*.name                                   // spread: [Anna, Bence, Csilla, Dávid]

def itStaff = staff.findAll { it.dept == 'IT' }       // filter
println itStaff.collect { "${it.name} (${it.salary})" }  // map
println "Bérköltség: ${staff.sum { it.salary }}"
println "Legjobban fizetett: ${staff.max { it.salary }.name}"
println "Skill-ek összesen: ${staff.inject(0) { acc, e -> acc + e.skills.size() }}"   // fold

// groupBy + collectEntries: részlegenkénti átlag
def avgByDept = staff.groupBy { it.dept }
                     .collectEntries { dept, list -> [dept, list.sum { it.salary }.intdiv(list.size())] }
println avgByDept

def allSkills = staff*.skills.flatten()
println allSkills.countBy { it }                      // gyakoriság
println allSkills.unique(false).toSorted()            // unique(false): nem módosít helyben

assert staff.any { it.salary > 900_000 }
assert !staff.every { 'sql' in it.skills }
println staff.find { it.name.startsWith('C') }?.dept

// Range-ek
println((1..10).step(3))                              // [1, 4, 7, 10]
println(('a'..'e').join(''))

// Map alapértékkel
def stock = [laptop: 5, 'egér': 40].withDefault { 0 }
stock.monitor += 3                                    // hiányzó kulcs -> 0 + 3
stock.each { k, v -> println "$k: $v" }

// Darabolás, indexelés, zip
println((1..7).collate(3))                            // [[1, 2, 3], [4, 5, 6], [7]]
println(['a', 'b'].withIndex().collect { v, i -> "$i=$v" })
println([[1, 2, 3], ['x', 'y', 'z']].transpose())     // [[1, x], [2, y], [3, z]]

// Rendezés több kulcs szerint: a <=> 0 eredménye "hamis", így az Elvis a második kulcsra lép
println staff.sort(false) { a, b -> a.dept <=> b.dept ?: b.salary <=> a.salary }*.name
```

## Stringek, GString és reguláris kifejezések
<!-- q: Hogyan kezeljem a stringeket, a GString interpolációt és a regexeket Groovyban? -->
<!-- tags: string, gstring, interpolation, multiline string, regex, slashy string, matcher -->

Az egyszeres idézőjeles literál `java.lang.String`, a dupla idézőjeles `GString`, amely `$x` és `${kifejezés}` interpolációt támogat; a `${-> x}` closure-forma lustán, minden `toString`-kor újraértékelődik. A háromszoros idézőjel többsoros stringet ad (`stripIndent()`-tel), a slashy (`/.../`) és dollar-slashy (`$/.../$`) string nem igényel backslash-escape-et, ezért regexekhez ideális. Regex operátorok: `~/minta/` (Pattern), `=~` (Matcher, részleges keresés, Groovy truth szerint igaz, ha van találat), `==~` (teljes egyezés). Buktató: a GString hashCode-ja eltér az azonos tartalmú String-étől, ezért Map-kulcsként mindig `toString()`-et használjunk; SQL-be soha ne fűzzünk felhasználói adatot (a `groovy.sql.Sql` a GString-et paraméterezett lekérdezéssé alakítja).

```groovy
def user = 'Anna'
def items = 3
println "Szia $user, ${items} tétel van a kosaradban (${items > 1 ? 'több' : 'egy'})"

// Lusta GString: a closure-forma minden kiíráskor újraértékelődik
def counter = 0
def lazyMsg = "érték: ${-> counter}"
counter = 5
println lazyMsg                                     // érték: 5

// GString vs String Map-kulcsként
def key = "id-${1}"
def m = [(key.toString()): 'ok']                    // kulcsnak mindig String
assert m['id-1'] == 'ok'

// Többsoros string
def sql = """
    SELECT name, salary
    FROM employee
    WHERE dept = ?
""".stripIndent().trim()
println sql

// Regex: ~/.../ Pattern, =~ Matcher, ==~ teljes egyezés
def logLine = '2025-01-10 12:00:03 ERROR [db] connection refused (attempt 3)'
def pattern = ~/(\d{4}-\d{2}-\d{2}) (\S+) (\w+) \[(\w+)\] (.+)/
def matcher = logLine =~ pattern
if (matcher) {                                      // Groovy truth: van-e találat
    def (all, date, time, level, module, text) = matcher[0]   // többszörös értékadás
    println "$level @ $module ($date $time): $text"
}
assert '2025-01-10' ==~ /\d{4}-\d{2}-\d{2}/
println logLine.findAll(/\d+/)*.toInteger().sum()   // a szövegben lévő számok összege

// Slashy és dollar-slashy string: nincs szükség backslash-escape-re
def winPath = /C:\temp\logs/
def jsonTemplate = $/{"path": "C:\data", "regex": "\d+"}/$
println "$winPath | $jsonTemplate"

// Hasznos GDK String-metódusok
println 'groovy-nyelv'.tokenize('-')*.capitalize().join(' ')
println 'abc'.padLeft(6, '.') + '|' + 'ünnep'.center(9, '*')
println('42'.isNumber() ? '42'.toInteger() * 2 : 'nem szám')
```

## Operátorok: Groovy truth, Elvis, safe navigation, túlterhelés
<!-- q: Milyen speciális operátorai vannak a Groovynak, és hogyan terheljek túl operátorokat? -->
<!-- tags: operators, groovy truth, elvis, safe navigation, spread, operator overloading, spaceship -->

A Groovy truth szerint hamis a `null`, a `0`, az üres string, lista, map és a találat nélküli Matcher; saját osztálynál az `asBoolean()` metódus dönt. Null-biztos eszközök: safe navigation (`?.`), Elvis (`?:`) és Elvis-értékadás (`?=`). Operátor-túlterheléshez elég a megfelelő nevű metódus: `plus` (+), `minus`, `multiply` (*), `negative` (unáris -), `getAt` ([]), `compareTo` (<, >, <=>), `call` (()), `isCase` (`in`, `switch`). Buktató: Groovyban az `==` az `equals()`-t (Comparable-nél a `compareTo`-t) hívja, a referencia-egyenlőség `is()` vagy `===`.

```groovy
class Vector2 implements Comparable<Vector2> {
    final double x, y
    Vector2(double x, double y) { this.x = x; this.y = y }
    Vector2 plus(Vector2 o)    { new Vector2(x + o.x, y + o.y) }   // a + b
    Vector2 multiply(double k) { new Vector2(x * k, y * k) }       // a * 2
    Vector2 negative()         { new Vector2(-x, -y) }             // -a
    double getAt(int i)        { i == 0 ? x : y }                  // a[0]
    double length()            { Math.sqrt(x * x + y * y) }
    int compareTo(Vector2 o)   { length() <=> o.length() }          // <, >, <=>, min(), sort()
    boolean asBoolean()        { x != 0 || y != 0 }                // Groovy truth testreszabása
    String toString()          { "($x, $y)" }
}

def a = new Vector2(1, 2), b = new Vector2(3, 4)
println a + b * 2                                    // (7.0, 10.0)
println(-a)
println "${a[0]} ${b > a} ${[b, a].min()}"
println(new Vector2(0, 0) ? 'nem nulla' : 'nullvektor')

assert !null && !0 && !'' && ![] && ![:]             // Groovy truth

// Safe navigation és Elvis
def config = [db: [host: 'localhost', port: null]]
def port = config.db?.port ?: 5432
def user = config.auth?.user ?: 'anonymous'
println "$port $user"

def timeout = null
timeout ?= 30                                        // csak ha jelenleg null/hamis
println timeout

// Spread argumentumként és listában
def add3(x, y, z) { x + y + z }
def nums = [1, 2, 3]
println add3(*nums)
println([0, *nums, 4])

// == vs referencia-egyenlőség
def s1 = new String('x'), s2 = new String('x')
println "${s1 == s2} ${s1.is(s2)}"                   // true false

// in (isCase) és call operátor
println(3 in nums)
class Multiplier { int k; def call(int v) { v * k } }
def triple = new Multiplier(k: 3)
println triple(7)                                    // 21
```

## Osztályok, property-k és traitek
<!-- q: Hogyan működnek az osztályok, property-k és traitek Groovyban? -->
<!-- tags: class, property, getter, setter, trait, named arguments, withtraits, oop -->

Groovyban a hozzáférés-módosító nélküli mező property: privát mező + automatikusan generált getter/setter, és a pont-szintaxis (`acc.balance = x`) a settert hívja, így a validáció utólag, a hívók módosítása nélkül beépíthető. Alapértelmezett konstruktorral rendelkező osztálynál named-argument (map) konstruktor is használható (`new Address(city: '...')`). A `trait` állapotot és implementációt is hordozhat, több is bekeverhető (ütközésnél az utoljára felsorolt nyer), absztrakt metódussal a befogadó osztálytól várhat el képességet, és futásidőben is hozzáadható egy objektumhoz (`withTraits`). Buktató: a `final` property csak gettert kap, a class-on belül pedig a saját property elérése közvetlen mezőhozzáférés.

```groovy
import java.time.LocalTime

class Account {
    String owner
    BigDecimal balance = 0
    final String iban                                  // csak getter
    private List<String> history = []

    Account(String owner, String iban) { this.owner = owner; this.iban = iban }

    // Saját setter: az acc.balance = x is ezen megy át
    void setBalance(BigDecimal value) {
        if (value < 0) throw new IllegalArgumentException('negatív egyenleg')
        history << "egyenleg: $balance -> $value"
        this.balance = value                           // osztályon belül: közvetlen mezőírás
    }
    List<String> getHistory() { history.asUnmodifiable() }
}

// Trait állapottal és implementációval
trait Auditable {
    List<String> auditLog = []
    void audit(String event) { auditLog << "${LocalTime.now().withNano(0)} $event" }
}
trait Notifying {
    abstract String getOwner()                         // a befogadó osztálynak kell biztosítania
    String notifyOwner(String msg) { "Értesítés ${owner} részére: $msg" }
}

class SavingsAccount extends Account implements Auditable, Notifying {
    BigDecimal rate
    SavingsAccount(String owner, String iban, BigDecimal rate) { super(owner, iban); this.rate = rate }

    void applyInterest() {
        balance = balance * (1 + rate)                 // alosztályból: a setBalance hívódik
        audit("kamat jóváírva ($rate)")
    }
}

def acc = new SavingsAccount('Teszt Elek', 'HU00 0000 0000', 0.05)
acc.balance = 1000.00
acc.applyInterest()
println "${acc.owner}: ${acc.balance}"
println acc.history
println acc.auditLog
println acc.notifyOwner('kamat érkezett')
try { acc.balance = -1 } catch (IllegalArgumentException e) { println "elutasítva: ${e.message}" }

// Named-argument konstruktor
class Address { String city; String zip }
def addr = new Address(city: 'Kecskemét', zip: '6000')
println "${addr.city} ${addr.zip}"

// Trait futásidejű hozzárendelése
trait Shouting { String shout(String s) { s.toUpperCase() + '!' } }
println new Object().withTraits(Shouting).shout('groovy')
```

## AST-transzformációk: @Immutable, @Canonical, @Builder és társai
<!-- q: Milyen AST-transzformációk vannak Groovyban, és hogyan csökkentik a boilerplate kódot? -->
<!-- tags: ast transformation, immutable, canonical, builder, memoized, delegate, sortable, log, compile-time metaprogramming -->

Az AST-transzformációk fordítási időben, a szintaxisfán generálnak kódot, így nincs futásidejű költségük, és Javából is látszanak a generált metódusok. Gyakoriak: `@Immutable` (final osztály és mezők, védekező másolatok, tuple-konstruktor, `equals`/`hashCode`/`toString`), `@Canonical` (ugyanez módosítható osztályra), `@Builder` (fluent builder), `@Memoized` (metódus-szintű cache), `@Delegate` (kompozíció öröklés helyett), `@Sortable` (`compareTo` a megadott mezőkre), `@Log`/`@Slf4j` (logger mező). Saját globális vagy lokális transzformáció is írható `ASTTransformation` implementálásával. Buktató: az `@Immutable` csak ismert immutábilis típusú mezőket fogad el (különben `@ImmutableOptions`-szel kell jelezni), a `@Memoized` cache-e pedig korlátlan, ha nem adunk meg `maxCacheSize`-t.

```groovy
import groovy.transform.*
import groovy.util.logging.Log

@Immutable
class Money {
    BigDecimal amount
    String currency
    Money plus(Money o) {
        assert currency == o.currency : 'eltérő pénznem'
        new Money(amount + o.amount, currency)
    }
}

@Canonical                       // @ToString + @EqualsAndHashCode + @TupleConstructor
class Product { String sku; String name; BigDecimal price }

@Builder
@ToString(includeNames = true)
class RequestSpec { String url; String method; Integer timeoutMs }

@Log                             // java.util.logging Logger a `log` mezőben
class PricingService {
    @Memoized(maxCacheSize = 100)
    BigDecimal exchangeRate(String from, String to) {
        log.info("árfolyam lekérés: $from -> $to")   // ugyanarra a párra csak egyszer fut le
        from == to ? 1.0 : 400.0
    }
}

@Sortable(includes = ['priority', 'title'])
@TupleConstructor
@ToString
class Task { int priority; String title }

class History {
    @Delegate(includes = ['size', 'get', 'iterator', 'isEmpty'])   // csak ezek a List-metódusok
    private final List<String> events = []
    void record(String e) { events << e }
}

def total = new Money(1200.50, 'HUF') + new Money(799.50, 'HUF')
println total                                        // Money(2000.00, HUF)
println new Product('A-1', 'Bögre', 3490.0) == new Product('A-1', 'Bögre', 3490.0)  // true

println RequestSpec.builder().url('https://api.example.com').method('POST').timeoutMs(2000).build()

def svc = new PricingService()
2.times { svc.exchangeRate('EUR', 'HUF') }

println([new Task(2, 'deploy'), new Task(1, 'teszt'), new Task(1, 'build')].sort()*.title) // [build, teszt, deploy]

def h = new History()
h.record('login'); h.record('logout')
println "${h.size()} esemény, első: ${h.get(0)}"

try { total.amount = 5 } catch (ReadOnlyPropertyException e) { println 'immutábilis!' }
```

## Builderek: JSON, XML és HTML generálás és feldolgozás
<!-- q: Hogyan generáljak és dolgozzak fel JSON-t és XML-t Groovy builderekkel és slurperekkel? -->
<!-- tags: builder, jsonbuilder, jsonslurper, markupbuilder, xmlslurper, gpath, json, xml -->

A Groovy builderek a dinamikus metódushívást (`methodMissing`/`invokeMethod`) használják: a closure-ben hívott, nem létező "metódusokból" elemek vagy kulcsok lesznek, így a kód szerkezete tükrözi a kimenetét. A `JsonBuilder`/`JsonOutput` JSON-t, a `MarkupBuilder` XML-t/HTML-t generál; a `JsonSlurper` és az `XmlSlurper` beolvasáskor Map/List vagy lusta GPath-struktúrát ad, amelyben pont-szintaxissal és GDK-metódusokkal navigálhatunk (`xml.invoice.line`, `@attr`). Buktatók: a builder closure-ben egy azonos nevű lokális változó vagy metódus "elnyeli" az elemnevet, és nagy XML-nél a `XmlSlurper` az egész dokumentumot a memóriába tölti (streameléshez StAX kell).

```groovy
import groovy.json.JsonBuilder
import groovy.json.JsonOutput
import groovy.json.JsonSlurper
import groovy.xml.MarkupBuilder
import groovy.xml.XmlSlurper

def orders = [
    [id: 1, customer: 'Anna', items: [[sku: 'A-1', qty: 2, price: 1890], [sku: 'B-7', qty: 1, price: 3490]]],
    [id: 2, customer: 'Bence', items: [[sku: 'C-3', qty: 5, price: 590]]],
]

// JsonBuilder: a closure-struktúrából JSON-fa lesz
def json = new JsonBuilder()
json {
    generatedAt '2025-01-10T12:00:00Z'
    count orders.size()
    data(orders.collect { o -> [id: o.id, customer: o.customer, total: o.items.sum { it.qty * it.price }] })
}
println json.toPrettyString()

// JsonSlurper: JSON -> Map/List, dinamikus navigáció
def parsed = new JsonSlurper().parseText(json.toString())
println "Legnagyobb rendelés: ${parsed.data.max { it.total }.customer}"
println JsonOutput.toJson([ok: true, ids: parsed.data*.id])

// MarkupBuilder: XML generálás; line(attribútumok, szöveges tartalom)
def writer = new StringWriter()
new MarkupBuilder(writer).invoices(version: '1.0') {
    orders.each { o ->
        invoice(id: o.id) {
            customer(o.customer)
            o.items.each { i -> line(sku: i.sku, qty: i.qty, i.price * i.qty) }
        }
    }
}
println writer

// XmlSlurper: GPath navigáció
def xml = new XmlSlurper().parseText(writer.toString())
def sum = xml.invoice.line.collect { it.text() as int }.sum()
println "XML-ből számolt végösszeg: $sum"
println xml.invoice.find { it.@id.text() == '2' }.customer.text()   // Bence
```

## Futásidejű metaprogramozás: MetaClass, methodMissing, kategóriák
<!-- q: Hogyan bővítsek osztályokat futásidőben Groovyban metaClass-szal és methodMissing-gel? -->
<!-- tags: metaprogramming, metaclass, expandometaclass, methodmissing, propertymissing, groovyinterceptable, category, expando -->

Dinamikus Groovyban minden hívás a MetaClass-on megy át, ezért futásidőben bármely osztályhoz (a JDK-osztályokhoz is) adhatunk metódust vagy property-t (`String.metaClass.toSlug = { ... }`, a closure-ben a `delegate` a fogadó objektum). A `methodMissing`/`propertyMissing` a nem létező tagok hívását kapja el – így működnek a GORM-stílusú dinamikus finderek (`findAllByCity`); a `GroovyInterceptable` + `invokeMethod` minden hívást elfog (naplózás, időmérés). A kategóriák (`use(Category) { }`) hatókörre korlátozott bővítést adnak, ami biztonságosabb a globális metaClass-módosításnál. Buktatók: a globális metaClass-módosítás az egész JVM-re hat (tesztek közt is), és `@CompileStatic` kód nem látja ezeket a bővítéseket.

```groovy
// Metódus és property hozzáadása meglévő osztályhoz
String.metaClass.toSlug = { ->
    delegate.toLowerCase().replaceAll(/[^a-z0-9]+/, '-').replaceAll(/^-|-$/, '')
}
Integer.metaClass.getKb = { -> delegate * 1024 }      // 5.kb
println 'Groovy Metaprogramozás 101'.toSlug()
println 5.kb

// methodMissing: dinamikus finder API
class Repo {
    List<Map> rows = [[name: 'Anna', city: 'Szeged'], [name: 'Bence', city: 'Pécs'], [name: 'Csaba', city: 'Szeged']]

    def methodMissing(String name, args) {
        def m = name =~ /^findAllBy([A-Z]\w*)$/
        if (!m) throw new MissingMethodException(name, Repo, args as Object[])
        String field = m[0][1].uncapitalize()
        // Gyorsítás: a következő hívásra valódi metódus lesz (a delegate a hívott példány)
        Repo.metaClass."$name" = { Object v -> delegate.rows.findAll { it[field] == v } }
        rows.findAll { it[field] == args[0] }
    }
    def propertyMissing(String name) { "nincs ilyen property: $name" }
}
def repo = new Repo()
println repo.findAllByCity('Szeged')*.name
println repo.findAllByName('Bence')
println repo.valami

// GroovyInterceptable: minden metódushívás elfogása
class Service implements GroovyInterceptable {
    def compute(int n) { (1..n).sum() }
    def invokeMethod(String name, args) {
        def mm = metaClass.getMetaMethod(name, args)
        long t = System.nanoTime()
        def result = mm.invoke(this, args)
        // System.out kell: a sima println is elfogott hívás lenne -> végtelen rekurzió
        System.out.println("$name${args.toList()} -> $result (${(System.nanoTime() - t).intdiv(1000)} µs)")
        result
    }
}
new Service().compute(1000)

// Kategória: csak a use blokkon belül érvényes
class DurationCategory {
    static Integer getMinutes(Integer self) { self * 60 }
}
use(DurationCategory) { println "15 perc = ${15.minutes} mp" }

// Expando: teljesen dinamikus objektum
def bot = new Expando(name: 'auri')
bot.greet = { "Szia, ${name} vagyok" }
println bot.greet()

println "${'x'.respondsTo('toSlug') ? 'van toSlug' : 'nincs'} ${repo.hasProperty('rows') != null}"
```

## Szkriptelés: fájlok, folyamatok, @Grab, CliBuilder
<!-- q: Hogyan írjak parancssori szkriptet Groovyban fájlkezeléssel, külső folyamatokkal és függőségekkel? -->
<!-- tags: scripting, file io, process, execute, grab, grape, clibuilder, automation -->

A Groovy szkript osztály és `main` nélkül futtatható (`groovy backup.groovy -d ./data`), a `@Grab` (Grape) a szkript indulásakor letölti a Maven-függőségeket, a `CliBuilder` (picocli-alapú) pedig parancssori kapcsolókat értelmez. A GDK tömör fájlkezelést ad (`eachFileRecurse`, `text`, `withWriter`, `withInputStream` – ezek automatikusan lezárják az erőforrást), a `String`/`List.execute()` külső folyamatot indít. Buktatók: a folyamat kimenetét olvasni kell (`consumeProcessOutput`), különben a puffer megtelik és a folyamat beragad; a felhasználói inputot ne fűzzük shell-parancsba, hanem listaként adjuk át az argumentumokat.

```groovy
#!/usr/bin/env groovy
@Grab('org.apache.commons:commons-compress:1.26.1')    // függőség letöltése indításkor
import org.apache.commons.compress.archivers.tar.TarArchiveOutputStream
import groovy.cli.picocli.CliBuilder

def cli = new CliBuilder(usage: 'backup.groovy -d <könyvtár> [-o kimenet.tar] [--dry-run]')
cli.d(longOpt: 'dir', args: 1, required: true, 'forráskönyvtár')
cli.o(longOpt: 'out', args: 1, 'kimeneti tar fájl')
cli._(longOpt: 'dry-run', 'csak kiírja, mit csinálna')
def opts = cli.parse(args)
if (!opts) System.exit(1)

def src = new File(opts.d)
def out = new File(opts.o ?: "backup-${System.currentTimeMillis()}.tar")

// Rekurzív bejárás szűréssel
def files = []
src.eachFileRecurse(groovy.io.FileType.FILES) { f ->
    if (!f.name.endsWith('.tmp') && f.length() < 50 * 1024 * 1024) files << f
}
println "${files.size()} fájl, ${files.sum(0L) { it.length() }.intdiv(1024)} KB"

if (opts.'dry-run') {
    files.each { println " + ${src.toPath().relativize(it.toPath())}" }
    return
}

// withCloseable / withInputStream: automatikus lezárás
new TarArchiveOutputStream(out.newOutputStream()).withCloseable { tar ->
    tar.longFileMode = TarArchiveOutputStream.LONGFILE_POSIX
    files.each { f ->
        tar.putArchiveEntry(tar.createArchiveEntry(f, src.toPath().relativize(f.toPath()).toString()))
        f.withInputStream { tar << it }                // << : stream másolása
        tar.closeArchiveEntry()
    }
}

// Külső folyamat: argumentumlista (nincs shell-injection), kimenet olvasása, időkorlát
def proc = ['tar', '-tf', out.absolutePath].execute()
def stdout = new StringBuilder(), stderr = new StringBuilder()
proc.consumeProcessOutput(stdout, stderr)
proc.waitForOrKill(30_000)
println(proc.exitValue() == 0 ? "Archívum rendben: ${stdout.readLines().size()} bejegyzés" : "Hiba: $stderr")

// Riport írása UTF-8-ban
new File(out.absoluteFile.parentFile, 'backup-report.txt').withWriter('UTF-8') { w ->
    files.each { w << "${it.name}\t${it.length()}\n" }
}
```

## Gradle build Groovy DSL-lel
<!-- q: Hogyan írjak Gradle build-szkriptet Groovy DSL-ben, és hogyan definiáljak saját taskot? -->
<!-- tags: gradle, build.gradle, groovy dsl, dependencies, tasks, plugins, toolchain, incremental build -->

A `build.gradle` valójában Groovy szkript: a blokkok (`plugins`, `dependencies`, `tasks`) closure-ök, amelyek delegate-je egy Gradle-objektum (`Project`, `DependencyHandler`, `Task`), ezért működik a zárójel nélküli `implementation '...'` hívás. A függőségi konfigurációk számítanak: `implementation` (nem szivárog a fogyasztók fordítási classpath-jára), `api` (igen, `java-library` pluginnal), `compileOnly`, `runtimeOnly`, `testImplementation`, `annotationProcessor`. A saját taskot `tasks.register`-rel (lusta konfiguráció) hozzuk létre, és deklaráljuk az `inputs`/`outputs`-ot, így inkrementális és cache-elhető lesz. Buktatók: a `doLast`-on kívüli kód konfigurációs fázisban fut (minden buildnél!), a GString csak dupla idézőjelben interpolál, új projektben pedig a típusbiztosabb Kotlin DSL (`build.gradle.kts`) az alapértelmezett.

```groovy
// build.gradle
plugins {
    id 'java'
    id 'application'
    id 'org.springframework.boot' version '3.3.5'
    id 'io.spring.dependency-management' version '1.1.6'
}

group = 'com.example'
version = '1.0.0'

java {
    toolchain { languageVersion = JavaLanguageVersion.of(21) }   // reprodukálható JDK
}

repositories { mavenCentral() }

ext { testcontainersVersion = '1.20.3' }   // saját property (modernebb: gradle/libs.versions.toml)

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web'
    runtimeOnly 'org.postgresql:postgresql'
    compileOnly 'org.projectlombok:lombok'
    annotationProcessor 'org.projectlombok:lombok'
    testImplementation 'org.springframework.boot:spring-boot-starter-test'
    testImplementation "org.testcontainers:postgresql:${testcontainersVersion}"   // dupla idézőjel: GString
    testImplementation 'org.spockframework:spock-spring:2.3-groovy-4.0'
}

application { mainClass = 'com.example.App' }

tasks.withType(JavaCompile).configureEach {       // lusta: csak ha a task ténylegesen kell
    options.encoding = 'UTF-8'
    options.compilerArgs += ['-Xlint:all', '-parameters']
}

tasks.named('test') {
    useJUnitPlatform()                            // JUnit 5 és Spock 2 is ezen fut
    maxParallelForks = Math.max(1, Runtime.runtime.availableProcessors().intdiv(2))
    testLogging { events 'failed', 'skipped' }
}

// Saját task deklarált be- és kimenettel -> inkrementális, cache-elhető
def generateBuildInfo = tasks.register('generateBuildInfo') {
    def outFile = layout.buildDirectory.file('generated/build-info.properties')
    inputs.property('version', project.version)
    outputs.file(outFile)
    doLast {                                      // végrehajtási fázis
        def f = outFile.get().asFile
        f.parentFile.mkdirs()
        f.text = "version=${project.version}\nbuiltBy=gradle\n"
        logger.lifecycle("build-info kész: $f")
    }
}

tasks.named('processResources') {
    from(generateBuildInfo)                       // a task kimenete bekötve -> automatikus függőség
}
```

## Tesztelés Spockkal
<!-- q: Hogyan írjak teszteket Spock keretrendszerrel Groovyban? -->
<!-- tags: spock, testing, specification, mock, stub, data-driven testing, where block, given when then -->

A Spock Groovy-alapú teszt- és specifikációs keretrendszer (JUnit Platformon fut), amely Java- és Groovy-kódot egyaránt tesztel. A tesztek blokkokra tagolódnak (`given`/`when`/`then`, `expect`, `where`), a `then` és `expect` blokkban minden logikai kifejezés automatikus assert, hibánál pedig részletes, kifejezésenkénti diagnosztikát ad. Beépített mockolás: `Stub()` csak válaszol, `Mock()` az interakciókat is ellenőrzi (`1 * audit.log(_)`, `0 * _`), a `where` táblázat adatvezérelt teszteket ad, a `thrown()` a kivételt ellenőrzi. Buktatók: a `then` blokkbeli interakciók élveznek elsőbbséget a stubbingnál, és interfész-mockból dobott, nem deklarált checked kivételt a JDK-proxy becsomagolja – ezért ilyenkor unchecked kivételt dobjunk.

```groovy
import spock.lang.*
import java.math.RoundingMode

// A tesztelt kód
interface RateProvider { BigDecimal rate(String from, String to) }
interface Audit { void log(String msg) }

class Converter {
    RateProvider rates
    Audit audit
    BigDecimal convert(BigDecimal amount, String from, String to) {
        if (amount < 0) throw new IllegalArgumentException('negatív összeg')
        def result = (amount * rates.rate(from, to)).setScale(2, RoundingMode.HALF_UP)
        audit.log("$amount $from -> $result $to")
        result
    }
}

class ConverterSpec extends Specification {
    def rates = Stub(RateProvider)               // Stub: csak válaszokat ad
    def audit = Mock(Audit)                      // Mock: interakció-ellenőrzés
    @Subject def converter = new Converter(rates: rates, audit: audit)

    def "átváltás árfolyammal és naplózással"() {
        given:
        rates.rate('EUR', 'HUF') >> 400.0

        when:
        def result = converter.convert(12.5, 'EUR', 'HUF')

        then:
        result == 5000.00
        1 * audit.log({ it.contains('EUR') })   // pontosan egyszer, a feltételnek megfelelő argumentummal
        0 * audit._                              // más hívás nem történt az auditon
    }

    @Unroll
    def "#amount #from -> #to = #expected"() {   // adatvezérelt: soronként külön teszteset
        given:
        rates.rate(_, _) >> { String f, String t -> f == t ? 1.0 : 0.0025 }

        expect:
        converter.convert(amount, from, to) == expected

        where:
        amount | from  | to    || expected
        1000.0 | 'HUF' | 'EUR' || 2.50
        99.99  | 'EUR' | 'EUR' || 99.99
        0.0    | 'HUF' | 'EUR' || 0.00
    }

    def "negatív összeg kivételt dob, és nem naplóz"() {
        when:
        converter.convert(-1.0, 'EUR', 'HUF')

        then:
        def e = thrown(IllegalArgumentException)
        e.message == 'negatív összeg'
        0 * audit.log(_)
    }

    def "a sikertelen árfolyam-lekérés továbbterjed"() {
        given:
        rates.rate(*_) >> { throw new UncheckedIOException(new IOException('timeout')) }

        when:
        converter.convert(10.0, 'EUR', 'HUF')

        then:
        thrown(UncheckedIOException)
    }
}
```
