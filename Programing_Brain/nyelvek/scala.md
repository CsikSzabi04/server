# Scala
<!-- tech: scala -->
<!-- aliases: scala3, scala 3, scala 2, dotty, sbt, scala.js -->

A Scala statikusan és erősen típusos, objektumorientált és funkcionális paradigmát ötvöző nyelv, amely elsősorban a JVM-re fordul (Scala.js és Scala Native is létezik), és teljes Java-interoperabilitást ad. Jellemzői a kifejező típusrendszer (generikusok varianciával, higher-kinded típusok, union/intersection és opaque típusok), az immutábilis kollekciók, a mintaillesztés, a case classok, a típusosztályok (`given`/`using`) és a for-comprehension; a memóriát a JVM GC-je kezeli. Erős terepe az adatfeldolgozás (Apache Spark, Kafka Streams), a nagy konkurenciájú backend (Akka/Pekko, cats-effect, ZIO) és a fordítóprogramok/DSL-ek. A Scala 3 egyszerűsítette a szintaxist (behúzás alapú blokkok, `enum`, `given`); gyengébb oldala a lassabb fordítás, a meredek tanulási görbe és a több, egymással versengő ökoszisztéma.

## Osztályok, traitek és objektumok
<!-- q: Hogyan működnek az osztályok, traitek és object-ek Scalában? -->
<!-- tags: class, trait, object, companion object, mixin, linearization, lazy val, scala 3 syntax -->

Scalában minden kifejezés (az `if` és a `match` is értéket ad), a `val` immutábilis, a `var` módosítható hivatkozás. A `trait` interfész és implementáció is lehet, több trait keverhető egy osztályba (mixin), a `super` hívások sorrendjét a linearizáció határozza meg, így "stackable" viselkedés építhető. Az `object` szálbiztos singleton, az azonos nevű companion object az osztály "statikus" részét (factory, konstansok) tartalmazza, és hozzáfér a privát tagjaihoz. A Scala 3-ban a blokkok behúzással is jelölhetők, és a `new` elhagyható (universal apply); a `lazy val` első használatkor értékelődik ki.

```scala
// Absztrakt és konkrét tagok egy traitben
trait Shape:
  def area: Double
  def describe: String = f"${getClass.getSimpleName} területe: $area%.2f"

// Stackable trait: felülírja az area-t és meghívja a lineárisan következő implementációt
trait Logged extends Shape:
  abstract override def area: Double =
    val a = super.area
    println(s"area számolva: $a")
    a

class Circle(val r: Double) extends Shape:
  require(r > 0, "a sugár pozitív")          // az osztálytörzs = konstruktor-törzs
  def area: Double = math.Pi * r * r

class Square(side: Double) extends Shape:      // side: privát mező, nem publikus property
  def area: Double = side * side

// Companion object: factory és konstans
object Circle:
  val unitCircle: Circle = Circle(1)           // universal apply: nem kell `new`
  def fromDiameter(d: Double): Circle = Circle(d / 2)

object Geometry:
  // Alapértelmezett és nevesített paraméterek
  def scaled(s: Shape, factor: Double = 2.0): Double = s.area * factor

  lazy val unitArea: Double =                  // első használatkor számolódik
    println("unitArea számolás")
    Circle.unitCircle.area

@main def runShapes(): Unit =
  val shapes: List[Shape] = List(Circle(1.5), Square(2), Circle.fromDiameter(4))
  shapes.map(_.describe).foreach(println)

  // Névtelen osztály trait-keveréssel
  val logged = new Circle(2) with Logged
  println(logged.area)

  println(Geometry.scaled(Square(3), factor = 0.5))
  println(Geometry.unitArea + Geometry.unitArea) // a println csak egyszer fut le

  val biggest = shapes.maxBy(_.area)
  val label = if biggest.area > 10 then "nagy" else "kicsi"   // if kifejezés
  println(s"Legnagyobb: ${biggest.describe} ($label)")
```

## Case classok, enumok és algebrai adattípusok
<!-- q: Hogyan modellezzek adatokat case classokkal és enumokkal Scalában? -->
<!-- tags: case class, enum, adt, sealed trait, copy, immutability, scala 3 enum -->

A `case class` immutábilis adathordozó: a fordító generálja az `equals`/`hashCode`/`toString`/`copy` metódusokat és az `unapply`-t a mintaillesztéshez, példányosításhoz nem kell `new`. Az algebrai adattípus (ADT) összeg-típusa Scala 3-ban `enum`-mal (paraméteres esetekkel is), Scala 2 stílusban `sealed trait` + case classok/objectek kombinációval írható; mindkettőnél kimerítő a mintaillesztés-ellenőrzés. A `copy` módosított másolatot ad, az eredeti változatlan marad, így az állapot biztonságosan megosztható szálak között. Buktató: a case class mezői csak akkor immutábilisak, ha a típusuk is az (pl. ne tegyünk bele `Array`-t vagy mutable kollekciót).

```scala
import java.time.LocalDate

final case class Address(city: String, zip: String)
final case class Customer(id: Long, name: String, address: Option[Address], since: LocalDate)

// Egyszerű felsorolás paraméterrel
enum Tier(val discount: Double):
  case Basic extends Tier(0.0)
  case Silver extends Tier(0.05)
  case Gold extends Tier(0.12)

// ADT enummal: minden eset egy "konstruktor", metódusokkal
enum Payment:
  case Card(number: String, holder: String)
  case Transfer(iban: String)
  case Cash

  def masked: String = this match
    case Card(n, h)  => s"Kártya **** ${n.takeRight(4)} ($h)"
    case Transfer(i) => s"Utalás ${i.take(4)}…"
    case Cash        => "Készpénz"

// Scala 2 stílusú ADT: sealed trait + case classok
sealed trait Event
final case class Registered(c: Customer) extends Event
final case class Upgraded(id: Long, to: Tier) extends Event
case object Heartbeat extends Event

@main def runAdt(): Unit =
  val anna = Customer(1, "Anna", Some(Address("Kecskemét", "6000")), LocalDate.of(2023, 5, 1))
  val moved = anna.copy(address = anna.address.map(_.copy(city = "Szeged", zip = "6720")))
  println(anna == moved.copy(address = anna.address))   // true – strukturális egyenlőség

  println(Tier.values.map(t => s"$t: ${(t.discount * 100).toInt}%").mkString(", "))
  println(Tier.valueOf("Gold").ordinal)

  List(Payment.Card("4111111111111111", "Teszt Elek"), Payment.Transfer("HU42117730161111101800000000"), Payment.Cash)
    .map(_.masked).foreach(println)

  // Mélyen beágyazott minta: szétbontás több szinten
  val events: List[Event] = List(Registered(anna), Upgraded(1, Tier.Gold), Heartbeat)
  events.foreach {
    case Registered(Customer(_, name, Some(Address(city, _)), _)) => println(s"Új ügyfél: $name ($city)")
    case Registered(c)      => println(s"Új ügyfél cím nélkül: ${c.name}")
    case Upgraded(id, tier) => println(s"#$id -> $tier")
    case Heartbeat          => ()
  }
```

## Mintaillesztés: extractorok, guardok, regex
<!-- q: Milyen lehetőségei vannak a mintaillesztésnek Scalában? -->
<!-- tags: pattern matching, match, extractor, unapply, guard, regex, typed pattern, alternatives -->

A `match` kifejezés sorban próbálja a mintákat: literál, típusminta (`n: Int`), case class-szétbontás, tuple, lista (`head :: tail`), alternatívák (`|`), változókötés (`c @ ...`) és guard (`if`). Saját extractort az `unapply` metódussal írunk (`Option`-t vagy `Boolean`-t ad vissza), így tetszőleges objektum "szétszedhető", a regexek is extractorként működnek, a csoportok változókba kötődnek. Scala 3-ban string-interpolátor minta (`case s"get $key"`) is van. Buktatók: a generikus típusparaméter futásidőben törlődik (`case xs: List[Int]` nem ellenőrzi az elemtípust), és a nem kimerítő `match` `MatchError`-t dob.

```scala
import scala.util.matching.Regex

// Saját extractor: email szétbontása
object Email:
  def unapply(s: String): Option[(String, String)] =
    s.split("@") match
      case Array(user, domain) if user.nonEmpty && domain.contains(".") => Some((user, domain))
      case _ => None

// Boolean extractor: csak illeszkedik vagy nem
object Even:
  def unapply(n: Int): Boolean = n % 2 == 0

// A regex is extractor: a csoportok változókba kötődnek
val LogLine: Regex = """(\d{4}-\d{2}-\d{2}) (INFO|WARN|ERROR) (.+)""".r

def classify(x: Any): String = x match
  case 0                           => "nulla"
  case Even()                      => s"páros: $x"
  case n: Int if n < 0             => s"negatív: $n"             // típusminta + guard
  case Email(user, "example.com")  => s"belső felhasználó: $user"
  case Email(user, domain)         => s"külső: $user @ $domain"
  case LogLine(date, "ERROR", msg) => s"[$date] HIBA: $msg"
  case LogLine(_, level, _)        => s"log ($level)"
  case s: String if s.isBlank      => "üres szöveg"
  case (a: Int, b: Int)            => s"pár, összeg=${a + b}"
  case head :: tail                => s"lista, első=$head, maradék ${tail.size} elem"
  case Some(inner)                 => s"Some -> ${classify(inner)}"
  case arr: Array[?]               => s"tömb ${arr.length} elemmel"
  case other                       => s"ismeretlen: $other"

// Alternatívák (|) és változókötés (@)
def httpCategory(code: Int): String = code match
  case 200 | 201 | 204          => "siker"
  case c @ (301 | 302)          => s"átirányítás ($c)"
  case c if c >= 400 && c < 500 => "klienshiba"
  case c if c >= 500            => "szerverhiba"
  case _                        => "egyéb"

@main def runMatch(): Unit =
  List[Any](0, 8, -3, 7, "anna@example.com", "bela@mail.hu", "2025-01-10 ERROR lemez megtelt",
            "2025-01-10 INFO indul", "  ", (2, 3), List(1, 2, 3), Some(-1), Array(1, 2))
    .map(classify).foreach(println)
  println(List(200, 302, 404, 503).map(httpCategory))
```

## Immutábilis kollekciók és műveleteik
<!-- q: Hogyan használjam a Scala kollekciókat (List, Vector, Map) és műveleteiket? -->
<!-- tags: collections, list, vector, map, groupmapreduce, foldleft, collect, view, immutable -->

A Scala alapértelmezett kollekciói immutábilisak (`List`, `Vector`, `Map`, `Set`), a módosítás új példányt ad strukturális megosztással (a régi és az új verzió közös részeket használ), így szálak között biztonságosan megoszthatók. A `List` egyirányú láncolt lista (gyors elejére fűzés `::`, lassú indexelés), a `Vector` kiegyensúlyozott fa (gyors véletlen elérés és hozzáfűzés). Gazdag műveletek: `groupMapReduce`, `foldLeft`, `collect` (filter+map részleges függvénnyel), `partition`, `sliding`, `zipWithIndex`; a `view` lusta transzformáció-láncot ad köztes kollekciók nélkül. A mutable kollekciókat (`ArrayBuffer`) csak lokálisan, teljesítménykritikus helyen használjuk.

```scala
final case class Sale(region: String, product: String, qty: Int, unitPrice: BigDecimal):
  def total: BigDecimal = unitPrice * qty

@main def runCollections(): Unit =
  val sales = List(
    Sale("Észak", "laptop", 2, BigDecimal(420000)),
    Sale("Dél", "egér", 15, BigDecimal(6500)),
    Sale("Észak", "monitor", 3, BigDecimal(89000)),
    Sale("Dél", "laptop", 1, BigDecimal(410000)),
  )

  // Csoportosítás + leképezés + redukció egy lépésben
  val revenueByRegion: Map[String, BigDecimal] = sales.groupMapReduce(_.region)(_.total)(_ + _)
  println(revenueByRegion)

  // foldLeft tuple akkumulátorral
  val (items, revenue) = sales.foldLeft((0, BigDecimal(0))) { case ((n, sum), s) => (n + s.qty, sum + s.total) }
  println(s"$items tétel, $revenue Ft")

  // Rendezés több kulccsal (régió növekvő, összeg csökkenő)
  sales.sortBy(s => (s.region, -s.total)).map(s => s"${s.region}/${s.product}").foreach(println)

  // collect: szűrés és leképezés egyben
  val bigTickets = sales.collect { case Sale(_, p, _, price) if price > 100000 => p.toUpperCase }
  println(bigTickets.distinct)

  // Immutábilis Map frissítése: updatedWith, +
  val stock = Map("laptop" -> 5, "egér" -> 40)
  val afterSales = sales.foldLeft(stock) { (st, s) => st.updatedWith(s.product)(_.map(_ - s.qty)) }
  println(afterSales + ("monitor" -> 0))

  // Vector: gyors random access és hozzáfűzés; List: gyors prepend
  val v = Vector.tabulate(5)(i => i * i) :+ 100
  val l = 0 :: List(1, 2, 3)
  println(s"$v ${l.sliding(2).map(_.sum).toList}")

  // View: lusta lánc, csak 3 találatig számol
  val firstLarge = (1 to 1_000_000).view.map(i => i.toLong * i).filter(_ % 17 == 0).take(3).toList
  println(firstLarge)

  // Mutable kollekció lokálisan
  val buf = scala.collection.mutable.ArrayBuffer.empty[String]
  sales.foreach(s => buf += s.product)
  println(buf.toSet)

  val (north, south) = sales.partition(_.region == "Észak")
  println(s"${north.map(_.product).zipWithIndex} / ${south.size}")
```

## Option, Either és Try: hibakezelés kivételek nélkül
<!-- q: Hogyan kezeljem a hiányzó értékeket és hibákat Option-nel, Either-rel és Try-jal Scalában? -->
<!-- tags: option, either, try, error handling, validation, functional error handling -->

Scalában a hiányzó értéket `Option` (`Some`/`None`) jelzi null helyett, a várható hibát `Either[E, A]` (`Left` = hiba, `Right` = siker, right-biased: a `map`/`flatMap` a `Right`-on dolgozik), a kivételt dobó (gyakran Java) kódot `Try` (`Success`/`Failure`) csomagolja. Mindhárom monád-szerű: `map`, `flatMap`, `fold`, `getOrElse` láncolható és for-comprehensionben használható, az első hiba rövidre zárja a láncot. Az `Option.get` és `Try.get` kerülendő, mert kivételt dob; a hibákat érdemes saját `enum`-mal típusosan modellezni. Ha minden hibát össze kell gyűjteni (nem csak az elsőt), a cats `Validated` típusa való.

```scala
import scala.util.{Failure, Success, Try}

final case class Config(host: String, port: Int, timeoutMs: Int)

enum ConfigError:
  case Missing(key: String)
  case Invalid(key: String, value: String, reason: String)

object ConfigLoader:
  def lookup(env: Map[String, String], key: String): Option[String] =
    env.get(key).map(_.trim).filter(_.nonEmpty)

  def required(env: Map[String, String], key: String): Either[ConfigError, String] =
    lookup(env, key).toRight(ConfigError.Missing(key))

  def intValue(key: String, raw: String, range: Range): Either[ConfigError, Int] =
    Try(raw.toInt) match                           // Try: kivételt dobó kód csomagolása
      case Success(n) if range.contains(n) => Right(n)
      case Success(_) => Left(ConfigError.Invalid(key, raw, s"${range.start}..${range.end} között kell"))
      case Failure(e) => Left(ConfigError.Invalid(key, raw, e.getMessage))

  // Either for-comprehensionben: az első Left rövidre zár
  def load(env: Map[String, String]): Either[ConfigError, Config] =
    for
      host    <- required(env, "HOST")
      portRaw <- required(env, "PORT")
      port    <- intValue("PORT", portRaw, 1 to 65535)
      timeout <- lookup(env, "TIMEOUT_MS")
                   .map(intValue("TIMEOUT_MS", _, 100 to 60000))
                   .getOrElse(Right(5000))         // opcionális kulcs alapértékkel
    yield Config(host, port, timeout)

@main def runConfig(): Unit =
  List(
    Map("HOST" -> "localhost", "PORT" -> "8080"),
    Map("HOST" -> "db.local", "PORT" -> "99999"),
    Map("PORT" -> "80"),
    Map("HOST" -> "x", "PORT" -> "80", "TIMEOUT_MS" -> "abc"),
  ).map(ConfigLoader.load).foreach {
    case Right(cfg)                           => println(s"OK: $cfg")
    case Left(ConfigError.Missing(k))         => println(s"Hiányzik: $k")
    case Left(ConfigError.Invalid(k, v, why)) => println(s"Hibás $k='$v': $why")
  }

  // Option API: flatMap / fold – a .get kerülendő
  val maybePort: Option[Int] = Some("8443").flatMap(_.toIntOption)
  println(maybePort.fold("nincs port")(p => s"port: $p"))

  // Try helyreállítás
  val divisor = "0".toInt
  val ratio = Try(10 / divisor).recover { case _: ArithmeticException => 0 }.getOrElse(-1)
  println(ratio)
```

## For-comprehension
<!-- q: Hogyan működik a for-comprehension Scalában és mire fordul le? -->
<!-- tags: for comprehension, flatmap, map, withfilter, yield, monad, desugaring -->

A for-comprehension szintaktikai cukor: a generátorok (`<-`) `flatMap`/`map` hívásokká, a guardok (`if`) `withFilter`-ré fordulnak, a köztes `=` értékadás pedig `map`-be kerül. Ezért bármely típuson működik, amelynek vannak ilyen metódusai: `List` (beágyazott ciklus), `Option`/`Either` (az első hiány/hiba rövidre zár), `Future`, `IO`, vagy saját típus (pl. egy parser). A `yield` nélküli változat `foreach`-re fordul, mellékhatásokhoz. Buktató: `Future`-nél a for-on belül létrehozott future-ök szekvenciálisan futnak – párhuzamossághoz előbb kell őket elindítani.

```scala
final case class Course(code: String, credits: Int, prerequisites: List[String])
final case class Student(name: String, passed: Set[String])

val courses = List(
  Course("PROG1", 6, Nil),
  Course("PROG2", 6, List("PROG1")),
  Course("ALGO", 5, List("PROG1", "MATH1")),
  Course("MATH1", 5, Nil),
)
val students = List(Student("Anna", Set("PROG1", "MATH1")), Student("Bence", Set("PROG1")))

// Saját típus for-ban: elég a map és a flatMap – minimális parser-kombinátor
final case class Parser[A](run: String => Option[(A, String)]):
  def map[B](f: A => B): Parser[B] = Parser(s => run(s).map((a, rest) => (f(a), rest)))
  def flatMap[B](f: A => Parser[B]): Parser[B] = Parser(s => run(s).flatMap((a, rest) => f(a).run(rest)))

object Parser:
  def char(c: Char): Parser[Char] = Parser(s => s.headOption.filter(_ == c).map(_ => (c, s.tail)))
  val digits: Parser[Int] = Parser { s =>
    val (d, rest) = s.span(_.isDigit)
    d.toIntOption.map(n => (n, rest))
  }

@main def runFor(): Unit =
  // Generátorok + guard + köztes értékadás: ki melyik kurzust veheti fel?
  val eligible = for
    s <- students
    c <- courses
    if !s.passed.contains(c.code)
    missing = c.prerequisites.filterNot(s.passed)
    if missing.isEmpty
  yield s"${s.name} felveheti: ${c.code} (${c.credits} kr.)"
  eligible.foreach(println)

  // Option-ön: az első None rövidre zár
  val lookup = Map("a" -> 1, "b" -> 2)
  val sum = for { x <- lookup.get("a"); y <- lookup.get("b") } yield x + y
  println(sum)                       // Some(3)

  // Saját Parser for-ban: "12:30" -> (12, 30)
  import Parser.*
  val time = for
    h <- digits
    _ <- char(':')
    m <- digits
  yield (h, m)
  println(time.run("12:30"))         // Some(((12,30),""))
  println(time.run("12-30"))         // None

  // yield nélkül: foreach mellékhatásra
  for (c, i) <- courses.zipWithIndex if c.credits > 5 do println(s"$i: ${c.code}")
```

## Magasabb rendű függvények, currying, részleges függvények
<!-- q: Hogyan használjam a magasabb rendű függvényeket, a curryinget és a részleges függvényeket Scalában? -->
<!-- tags: higher-order functions, currying, partial function, by-name parameter, closure, polymorphic function -->

A függvények first-class értékek: paraméterként átadhatók, visszaadhatók, `andThen`/`compose`-zal komponálhatók, a metódusok pedig automatikusan függvénnyé alakulnak (eta-expansion). A több paraméterlista (currying) részleges alkalmazást és blokk-szintaxist (`retry(3) { ... }`) tesz lehetővé, a by-name paraméter (`op: => T`) minden hivatkozáskor újraértékelődik, ami saját vezérlési szerkezetekhez kell. A `PartialFunction` csak a bemenetek egy részére definiált (`isDefinedAt`), `orElse`-szel láncolható; a `collect` és a `recover` is ilyet vár. Scala 3-ban polimorf függvénytípus (`[A] => List[A] => Option[A]`) is írható.

```scala
def compose[A, B, C](f: A => B, g: B => C): A => C = a => g(f(a))

// Currying + by-name paraméter: saját vezérlési szerkezet
def retry[T](times: Int)(op: => T): T =
  try op
  catch
    case e: Exception if times > 1 =>
      println(s"újrapróbálás (${e.getMessage})")
      retry(times - 1)(op)

// Részleges alkalmazás az első paraméterlistán
def priceWithVat(rate: Double)(net: Double): Double = net * (1 + rate)
val huGross: Double => Double = priceWithVat(0.27)

// Részleges függvény string-interpolátor mintával
val parseCommand: PartialFunction[String, String] = {
  case s"get $key"        => s"GET $key"
  case s"set $key=$value" => s"SET $key -> $value"
}
val fallback: PartialFunction[String, String] = { case other => s"ismeretlen parancs: $other" }

// Closure: a számláló a lezárt környezetben él tovább
def rateLimiter(max: Int): () => Boolean =
  var used = 0
  () => { used += 1; used <= max }

// Polimorf függvényérték (Scala 3)
val safeHead: [A] => List[A] => Option[A] = [A] => (xs: List[A]) => xs.headOption

@main def runHof(): Unit =
  val normalize = compose((s: String) => s.trim, (s: String) => s.toLowerCase)
  val slug = normalize.andThen(_.replace(' ', '-'))
  println(slug("  Scala Funkcionális Programozás "))

  var calls = 0
  val n = retry(3) {
    calls += 1
    if calls < 3 then throw RuntimeException(s"#$calls") else calls
  }
  println(s"sikerült, hívások: $n")
  println(List(1000.0, 2500.0).map(huGross))

  val handler = parseCommand.orElse(fallback)
  List("get user", "set mode=dark", "del x").map(handler).foreach(println)
  println(parseCommand.isDefinedAt("del x"))   // false

  val allow = rateLimiter(2)
  println(List.fill(3)(allow()))               // List(true, true, false)
  println(safeHead(List("a", "b")))
  println(List(3, 1, 2).sortWith(_ > _).map(math.pow(2, _)).sum)
```

## Generikusok, variancia és típuskorlátok
<!-- q: Hogyan működik a variancia (+A, -A) és a típuskorlátok Scalában? -->
<!-- tags: generics, variance, covariance, contravariance, upper bound, lower bound, classtag, higher-kinded types -->

A variancia a deklarációnál adható meg: `+A` kovariáns (`List[Cat]` <: `List[Animal]`, mert csak kimenet), `-A` kontravariáns (`Printer[Animal]` <: `Printer[Cat]`, mert csak bemenet), jelölés nélkül invariáns. Kovariáns típusba elemet csak alsó korláttal (`def push[B >: A](b: B)`) lehet "betenni" – így működik az immutábilis `List.::` is; a felső korlát (`T <: Animal`) a megengedett típusokat szűkíti. A type erasure miatt a `case t: T` csak `ClassTag` context bounddal működik. A higher-kinded típusok (`F[_]`) típuskonstruktorok felett absztrahálnak – erre épül a cats és a ZIO.

```scala
import scala.reflect.ClassTag

sealed trait Animal { def name: String }
final case class Cat(name: String) extends Animal
final case class Dog(name: String) extends Animal

// Immutábilis, kovariáns verem: Stack[Cat] <: Stack[Animal]
sealed trait Stack[+A]:
  def push[B >: A](b: B): Stack[B] = NonEmpty(b, this)   // alsó korlát a kovariancia miatt
  def peek: Option[A]
case object Empty extends Stack[Nothing]:
  def peek: Option[Nothing] = None
final case class NonEmpty[+A](head: A, tail: Stack[A]) extends Stack[A]:
  def peek: Option[A] = Some(head)

// Kontravariáns fogyasztó
trait Printer[-A]:
  def print(a: A): String
val animalPrinter: Printer[Animal] = a => s"állat: ${a.name}"   // SAM-konverzió

def printAll(cats: List[Cat], p: Printer[Cat]): Unit = cats.foreach(c => println(p.print(c)))

// Felső korlát + using paraméter
def maxOf[T <: Animal](xs: List[T])(using ord: Ordering[T]): T = xs.max

// ClassTag: futásidejű típusellenőrzés a type erasure ellenére
def filterByType[T: ClassTag](xs: List[Any]): List[T] = xs.collect { case t: T => t }

// Higher-kinded type: absztrakció típuskonstruktor felett
trait Container[F[_]]:
  def wrap[A](a: A): F[A]
  def first[A](fa: F[A]): Option[A]

given Container[List] with
  def wrap[A](a: A): List[A] = List(a)
  def first[A](fa: List[A]): Option[A] = fa.headOption

def roundTrip[F[_], A](a: A)(using c: Container[F]): Option[A] = c.first(c.wrap(a))

@main def runVariance(): Unit =
  val cats: Stack[Cat] = Empty.push(Cat("Cirmi")).push(Cat("Mici"))
  val animals: Stack[Animal] = cats.push(Dog("Bodri"))   // B = Animal
  println(animals.peek)

  printAll(List(Cat("Cirmi")), animalPrinter)            // Printer[Animal] ott, ahol Printer[Cat] kell

  given Ordering[Cat] = Ordering.by((c: Cat) => c.name.length)
  println(maxOf(List(Cat("Ab"), Cat("Abcdef"), Cat("Abc"))))

  println(filterByType[String](List(1, "a", 2.0, "b")))
  println(roundTrip[List, Int](42))
```

## Implicitek Scala 3-ban: given, using, extension
<!-- q: Hogyan működnek a given és using paraméterek, valamint az extension metódusok Scala 3-ban? -->
<!-- tags: implicits, given, using, context parameters, extension methods, implicit conversion, summon -->

A Scala 3 a régi `implicit` kulcsszót szándékkal elkülönített fogalmakra bontotta: a `given` egy típus "kanonikus" példányát definiálja, a `using` paramétert a fordító automatikusan kitölti a hatókörben lévő given-nel (kontextus-paraméter, pl. konfiguráció, logger, `ExecutionContext`), a `summon[T]` explicit lekéri. Az `extension` metódusok meglévő típusokat bővítenek (Scala 2-ben `implicit class`), az implicit konverzióhoz pedig explicit `Conversion` given és nyelvi import kell – ezzel szándékosan nehezítették a visszaélést. A given-eket a fordító a lexikális hatókörben és a típus companion objectjeiben (implicit scope) keresi; más csomagból `import x.given`-nel hozzuk be őket.

```scala
import scala.concurrent.duration.*
import scala.language.implicitConversions

final case class RequestContext(requestId: String, userId: Option[String], locale: String)

trait Logger:
  def info(msg: String)(using ctx: RequestContext): Unit

// Nevesített given (Scala 2: implicit object)
given consoleLogger: Logger with
  def info(msg: String)(using ctx: RequestContext): Unit =
    println(s"[${ctx.requestId}] [${ctx.userId.getOrElse("anon")}] $msg")

final class OrderService(using log: Logger):
  def place(item: String, qty: Int)(using ctx: RequestContext): String =
    log.info(s"rendelés: $item x$qty")
    val msg = Messages.confirm(item)          // a ctx automatikusan továbbadódik
    log.info("kész")
    msg

object Messages:
  def confirm(item: String)(using ctx: RequestContext): String = ctx.locale match
    case "hu" => s"A(z) $item rendelését rögzítettük."
    case _    => s"Your order for $item is confirmed."

// Extension metódusok
extension (s: String)
  def truncate(max: Int): String = if s.length <= max then s else s.take(max - 1) + "…"
  def isValidSku: Boolean = s.matches("[A-Z]{3}-\\d{4}")

extension (n: Int)
  def percentOf(total: Int): Double = if total == 0 then 0.0 else n * 100.0 / total

// Implicit konverzió: explicit Conversion given szükséges
final case class Meters(value: Double)
given Conversion[Int, Meters] = n => Meters(n.toDouble)
def distanceLabel(m: Meters): String = f"${m.value}%.1f m"

@main def runGivens(): Unit =
  given RequestContext = RequestContext("req-7f3a", Some("u-42"), "hu")
  val service = OrderService()                // a Logger given-t a fordító keresi meg
  println(service.place("ABC-1234", 2))

  // using explicit megadása felülíráshoz
  println(Messages.confirm("XYZ-0001")(using RequestContext("req-2", None, "en")))

  println("Funkcionális programozás Scalában".truncate(15))
  println(List("ABC-1234", "abc-1", "QWE-0000").map(_.isValidSku))
  println(37.percentOf(120))
  println(distanceLabel(5))                   // Int -> Meters konverzió
  println(3.seconds + 500.millis)             // a duration DSL is extension-alapú
  println(summon[RequestContext].requestId)   // given explicit lekérése
```

## Típusosztályok (type classes)
<!-- q: Hogyan implementáljak típusosztályokat Scalában given-ekkel? -->
<!-- tags: type class, ad-hoc polymorphism, given instances, context bound, monoid, json encoder, derivation -->

A típusosztály viselkedést rendel típusokhoz öröklés nélkül (ad-hoc polimorfizmus): egy generikus trait (`JsonEncoder[A]`), típusonkénti `given` példányok, és `using`/context bound (`[A: JsonEncoder]`) a felhasználás helyén. Így olyan típusokhoz is adhatunk képességet, amelyek forrását nem módosíthatjuk (String, Int, Java-osztályok), és a példányok egymásból származtathatók (ha van `JsonEncoder[A]`, lesz `JsonEncoder[List[A]]` is). A példányokat a típusosztály vagy az adattípus companion objectjébe tesszük, ott import nélkül is megtalálja a fordító. A cats (`Monoid`, `Functor`, `Monad`) és a circe/zio-json erre épül; Scala 3-ban `derives` záradékkal automatikus származtatás is írható.

```scala
trait JsonEncoder[A]:
  def encode(a: A): String
  extension (a: A) def toJson: String = encode(a)       // x.toJson szintaxis

object JsonEncoder:
  def apply[A](using enc: JsonEncoder[A]): JsonEncoder[A] = enc   // summon-segéd

  // Alappéldányok a companionban (implicit scope)
  given JsonEncoder[String] with
    def encode(s: String): String = "\"" + s.replace("\"", "\\\"") + "\""
  given JsonEncoder[Int] with
    def encode(n: Int): String = n.toString

  // Származtatott példányok: rekurzív feloldás
  given [A](using e: JsonEncoder[A]): JsonEncoder[List[A]] with
    def encode(xs: List[A]): String = xs.map(e.encode).mkString("[", ",", "]")
  given [A](using e: JsonEncoder[A]): JsonEncoder[Option[A]] with
    def encode(o: Option[A]): String = o.fold("null")(e.encode)

final case class User(name: String, age: Int, tags: List[String], email: Option[String])
object User:
  given JsonEncoder[User] with                          // a saját típus companionjában
    def encode(u: User): String =
      List(
        "name"  -> JsonEncoder[String].encode(u.name),
        "age"   -> JsonEncoder[Int].encode(u.age),
        "tags"  -> JsonEncoder[List[String]].encode(u.tags),
        "email" -> JsonEncoder[Option[String]].encode(u.email),
      ).map((k, v) => s"\"$k\":$v").mkString("{", ",", "}")

// Context bound: [A: JsonEncoder] == (using JsonEncoder[A])
def toJsonArray[A: JsonEncoder](items: A*): String = JsonEncoder[List[A]].encode(items.toList)

// Algebrai típusosztály: Monoid (asszociatív combine + semleges elem)
trait Monoid[A]:
  def empty: A
  def combine(x: A, y: A): A

given Monoid[Int] with
  def empty: Int = 0
  def combine(x: Int, y: Int): Int = x + y

given [K, V](using m: Monoid[V]): Monoid[Map[K, V]] with
  def empty: Map[K, V] = Map.empty
  def combine(x: Map[K, V], y: Map[K, V]): Map[K, V] =
    y.foldLeft(x) { case (acc, (k, v)) => acc.updated(k, acc.get(k).fold(v)(m.combine(_, v))) }

def combineAll[A](xs: List[A])(using m: Monoid[A]): A = xs.foldLeft(m.empty)(m.combine)

@main def runTypeclasses(): Unit =
  val u = User("Teszt \"T\" Elek", 30, List("scala", "fp"), None)
  println(u.toJson)                       // az extension a User given-jéből jön (implicit scope)
  println(toJsonArray(1, 2, 3))
  println(combineAll(List(Map("a" -> 1), Map("a" -> 2, "b" -> 5))))   // Map(a -> 3, b -> 5)
```

## Opaque, union és intersection típusok
<!-- q: Mire valók az opaque type, a union és az intersection típusok Scala 3-ban? -->
<!-- tags: opaque type, union type, intersection type, smart constructor, match type, scala 3 -->

Az `opaque type` futásidőben a mögöttes típus (nincs wrapper-allokáció), fordításkor viszont önálló típus: a definiáló hatókörön kívül nem keverhető össze például egy `UserId` és egy nyers `Long`; validált létrehozásra smart constructort adunk. A union típus (`A | B`) "vagy-vagy" értéket ír le külön sealed hierarchia nélkül (pl. hibatípusok összevonására), a mintaillesztés rajta is ellenőrizhető; az intersection (`A & B`) mindkét képességet megköveteli. A match type típusszintű `match`: az eredménytípus a bemeneti típustól függ. Buktató: az opaque típusra az `==` a mögöttes értéket hasonlítja, és a generikus kollekciókban boxingolódhat.

```scala
object Ids:
  opaque type UserId = Long
  opaque type Email = String

  object UserId:
    def apply(v: Long): UserId = { require(v > 0, "pozitív azonosító kell"); v }
  extension (id: UserId) def value: Long = id

  object Email:
    // Smart constructor: csak validált érték jöhet létre
    def parse(s: String): Either[String, Email] =
      if s.matches("""[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}""") then Right(s.toLowerCase) else Left(s"hibás email: $s")
  extension (e: Email) def domain: String = e.substring(e.indexOf('@') + 1)

import Ids.*

def sendWelcome(id: UserId, to: Email): String = s"#${id.value} -> ${to.domain}"
// sendWelcome(42L, "x@y.hu")  <- fordítási hiba: a Long nem UserId, a String nem Email

// Union típus
final case class NotFound(id: Long)
final case class Forbidden(reason: String)
type LookupError = NotFound | Forbidden

def findUser(id: Long): Either[LookupError, String] =
  if id == 1 then Right("admin")
  else if id < 0 then Left(Forbidden("negatív azonosító"))
  else Left(NotFound(id))

def explain(e: LookupError): String = e match
  case NotFound(id)   => s"nincs ilyen: $id"
  case Forbidden(why) => s"tiltott: $why"

// Intersection típus: mindkét trait képességei kellenek
trait Readable { def read(): String }
trait Closeable { def close(): Unit }
def consume(r: Readable & Closeable): String =
  try r.read() finally r.close()

// Match type: típusszintű függvény
type Elem[X] = X match
  case String      => Char
  case Iterable[t] => t

@main def runTypes(): Unit =
  val mail = Email.parse("Anna@Example.com").fold(err => sys.error(err), identity)
  println(sendWelcome(UserId(7), mail))
  println(List(1L, -5L, 9L).map(findUser).map(_.left.map(explain)))
  println(consume(new Readable with Closeable {
    def read() = "adat"
    def close() = println("lezárva")
  }))
  val c: Elem[String] = 'x'                       // Elem[String] = Char
  val n: Elem[List[Int]] = 42                     // Elem[List[Int]] = Int
  println(s"$c $n")
```

## Future és ExecutionContext
<!-- q: Hogyan írjak aszinkron kódot Future-rel Scalában? -->
<!-- tags: future, executioncontext, promise, async, concurrency, traverse, recover, await -->

A `scala.concurrent.Future` egy egyszer kiértékelődő aszinkron eredmény, amely a létrehozásakor azonnal elindul egy `ExecutionContext`-en (szálkészlet); `map`/`flatMap`/`recover` láncolható és for-comprehensionben használható. A `Future.traverse`/`sequence` sok kérést futtat párhuzamosan egy `Future[List]` eredménnyel. Az `ExecutionContext`-et `using` paraméterként (given) adjuk át; blokkoló I/O-hoz külön pool kell, különben kiéheztetjük a globális (CPU-magszámnyi) poolt. Buktatók: a Future "mohó" és nem mondható le, a for-ban létrehozott future-ök szekvenciálisan futnak, az `Await.result` pedig csak a program szélén (main, teszt) megengedett – ezért komolyabb rendszerekben gyakran lusta effekt-típust (cats-effect `IO`, ZIO) használnak.

```scala
import scala.concurrent.*
import scala.concurrent.duration.*
import scala.util.{Failure, Success}
import java.util.concurrent.Executors

final case class Quote(symbol: String, price: BigDecimal)

object Market:
  // Külön pool blokkoló I/O-hoz; a global CPU-munkára való
  private val ioPool = Executors.newFixedThreadPool(8)
  given ioEc: ExecutionContext = ExecutionContext.fromExecutorService(ioPool)

  def quote(symbol: String): Future[Quote] = Future {
    Thread.sleep(200)                                   // hálózati hívás szimulációja
    if symbol == "BAD" then throw IllegalArgumentException(s"ismeretlen: $symbol")
    Quote(symbol, BigDecimal(100 + symbol.length * 7))
  }
  def shutdown(): Unit = ioPool.shutdown()

@main def runFutures(): Unit =
  import Market.ioEc

  // A két Future azonnal elindul, párhuzamosan futnak
  val fa = Market.quote("AURI")
  val fb = Market.quote("JVM")

  // for: flatMap/map lánc – a future-öket ELŐRE hoztuk létre, így párhuzamos
  val spread: Future[BigDecimal] = for
    a <- fa
    b <- fb
  yield (a.price - b.price).abs

  // traverse: sok kérés párhuzamosan
  val all: Future[List[Quote]] = Future.traverse(List("A", "BB", "CCC"))(Market.quote)

  // recover: hiba helyett alapérték
  val safe: Future[Option[Quote]] = Market.quote("BAD").map(Some(_)).recover {
    case e: IllegalArgumentException =>
      println(s"hiba: ${e.getMessage}")
      None
  }

  // Callback (nem blokkol)
  spread.onComplete {
    case Success(v) => println(s"spread: $v")
    case Failure(e) => println(s"spread hiba: $e")
  }

  // Promise: kézzel teljesített Future (pl. callback-alapú API áthidalására)
  val p = Promise[String]()
  Future { Thread.sleep(50); p.success("callback kész") }

  // Await CSAK a program szélén
  println(Await.result(all, 2.seconds).map(_.price))
  println(Await.result(safe, 2.seconds))
  println(Await.result(p.future, 2.seconds))
  Await.ready(spread, 2.seconds)
  Market.shutdown()
```

## Actor modell Akka Typeddal (Pekko)
<!-- q: Hogyan működik az actor modell Akka Typed-dal Scalában? -->
<!-- tags: akka, pekko, actor model, akka typed, behavior, message passing, concurrency -->

Az actor modellben az állapotot actorok birtokolják, és csak üzenetekkel kommunikálnak: egy actor egyszerre egy üzenetet dolgoz fel a postaládájából, így az állapota zár és szinkronizáció nélkül szálbiztos. Az Akka Typed-ban az actor egy `Behavior[Command]`, a protokollt sealed üzenethierarchia írja le, a válaszcímet (`ActorRef[Response]`) az üzenetben küldjük; az állapotváltást az új `Behavior` visszaadása jelenti. A hibakezelés felügyeleti fával (supervision) történik: a szülő dönti el, hogy a hibázó gyereket újraindítja vagy leállítja. Az Akka 2.7+ BSL licencű, a nyílt forrású, API-kompatibilis fork az Apache Pekko (`org.apache.pekko` csomagnév); buktató, hogy az actorban soha ne blokkoljunk és ne osszunk meg módosítható állapotot üzenetben.

```scala
import akka.actor.typed.{ActorRef, ActorSystem, Behavior}
import akka.actor.typed.scaladsl.Behaviors

object BankAccount:
  // A protokoll: parancsok és válaszok
  sealed trait Command
  final case class Deposit(amount: BigDecimal, replyTo: ActorRef[Response]) extends Command
  final case class Withdraw(amount: BigDecimal, replyTo: ActorRef[Response]) extends Command
  final case class GetBalance(replyTo: ActorRef[Response]) extends Command

  sealed trait Response
  final case class Balance(value: BigDecimal) extends Response
  final case class Rejected(reason: String) extends Response

  // Az állapot a Behavior paramétere: nincs mutable mező, nincs zár
  def apply(balance: BigDecimal = BigDecimal(0)): Behavior[Command] =
    Behaviors.receive { (ctx, msg) =>
      msg match
        case Deposit(amount, replyTo) =>
          replyTo ! Balance(balance + amount)
          apply(balance + amount)                       // új állapot = új Behavior
        case Withdraw(amount, replyTo) if amount > balance =>
          replyTo ! Rejected(s"nincs fedezet: $balance < $amount")
          Behaviors.same
        case Withdraw(amount, replyTo) =>
          ctx.log.info("kifizetés: {}", amount)
          replyTo ! Balance(balance - amount)
          apply(balance - amount)
        case GetBalance(replyTo) =>
          replyTo ! Balance(balance)
          Behaviors.same
    }

object Teller:
  def apply(): Behavior[BankAccount.Response] = Behaviors.setup { ctx =>
    val account = ctx.spawn(BankAccount(), "account-1")  // gyerek actor
    account ! BankAccount.Deposit(BigDecimal(10000), ctx.self)
    account ! BankAccount.Withdraw(BigDecimal(25000), ctx.self)
    account ! BankAccount.Withdraw(BigDecimal(4000), ctx.self)
    account ! BankAccount.GetBalance(ctx.self)

    var received = 0 // csak az actoron belül érjük el, ezért biztonságos
    Behaviors.receiveMessage { resp =>
      ctx.log.info("válasz: {}", resp)
      received += 1
      if received == 4 then Behaviors.stopped else Behaviors.same
    }
  }

@main def runActors(): Unit =
  // Az ActorSystem a gyökér actor; a Teller leállásával a rendszer is leáll
  ActorSystem(Teller(), "bank")
```

## Funkcionális effektek cats-effect IO-val
<!-- q: Hogyan használjam a cats-effect IO-t, Resource-t és Ref-et Scalában? -->
<!-- tags: cats-effect, io, resource, ref, fiber, partraverse, timeout, functional effects -->

A cats-effect `IO` egy mellékhatás leírása (érték), nem a végrehajtása: lusta, újrafuttatható, kompozícióval épül, és csak a program szélén (`IOApp`) fut le. A futtatókörnyezet könnyűsúlyú fibereket ütemez kevés szálon, a lemondás (`timeout`, `race`) biztonságos, a `Resource` pedig garantálja a felszabadítást hiba és lemondás esetén is (a try-with-resources funkcionális megfelelője). A `Ref` atomikus, tisztán funkcionális mutable cella konkurens állapothoz, a `parTraverse` párhuzamos futtatást ad. Buktató: az `IO`-n belül ne hívjunk blokkoló kódot `IO.blocking` nélkül, és ne futtassuk `unsafeRunSync`-kel üzleti kódban.

```scala
import cats.effect.{IO, IOApp, Ref, Resource}
import cats.syntax.all.*
import scala.concurrent.duration.*

object CatsEffectDemo extends IOApp.Simple:
  final case class Conn(id: Int)

  // Resource: megszerzés + garantált felszabadítás
  def connection(id: Int): Resource[IO, Conn] =
    Resource.make(IO.println(s"kapcsolat nyitás #$id").as(Conn(id)))(c => IO.println(s"kapcsolat zárás #${c.id}"))

  def fetch(conn: Conn, key: String): IO[String] = IO.sleep(100.millis) *> IO.pure(s"$key@conn${conn.id}")

  def worker(n: Int, counter: Ref[IO, Int]): IO[String] =
    connection(n).use { c =>
      for
        v <- fetch(c, s"kulcs-$n")
        _ <- counter.update(_ + 1)                 // atomikus frissítés
      yield v
    }

  // Újrapróbálás exponenciális visszalépéssel
  def retry[A](io: IO[A], left: Int, delay: FiniteDuration): IO[A] =
    io.handleErrorWith { e =>
      if left <= 0 then IO.raiseError(e)
      else IO.println(s"újra: ${e.getMessage}") *> IO.sleep(delay) *> retry(io, left - 1, delay * 2)
    }

  val run: IO[Unit] =
    for
      counter  <- Ref.of[IO, Int](0)
      results  <- (1 to 5).toList.parTraverse(worker(_, counter))   // párhuzamos fiberek
      _        <- IO.println(results)
      total    <- counter.get
      _        <- IO.println(s"kész: $total")
      slow     <- IO.sleep(2.seconds).as("lassú").timeout(300.millis).attempt // lemondás időtúllépéskor
      _        <- IO.println(s"timeout eredménye: ${slow.leftMap(_.getClass.getSimpleName)}")
      attempts <- Ref.of[IO, Int](0)
      flaky     = attempts.updateAndGet(_ + 1).flatMap { n =>
                    if n < 3 then IO.raiseError(RuntimeException(s"hiba #$n")) else IO.pure(n)
                  }
      ok       <- retry(flaky, 5, 50.millis)
      _        <- IO.println(s"sikerült a(z) $ok. próbára")
      winner   <- IO.race(IO.sleep(50.millis).as("gyors"), IO.sleep(1.second).as("lassú")) // a vesztes lemondódik
      _        <- IO.println(winner)
    yield ()
```

## Rekurzió, @tailrec és lusta kiértékelés
<!-- q: Hogyan írjak verembiztos rekurziót és lusta sorozatokat Scalában? -->
<!-- tags: recursion, tailrec, lazylist, lazy evaluation, trampoline, tailcalls, memoization -->

Funkcionális stílusban a ciklusokat gyakran rekurzió váltja ki; ha a rekurzív hívás az utolsó művelet (farokrekurzió), a fordító ciklussá alakítja, a `@tailrec` annotáció pedig fordítási hibát ad, ha ez nem lehetséges – így elkerüljük a `StackOverflowError`-t. Kölcsönös rekurzióhoz trampoline kell (`scala.util.control.TailCalls`), ami a hívásokat heap-objektumokká alakítja. A `LazyList` lusta és memoizált: az elemek csak igény szerint számolódnak, akár végtelen sorozat is definiálható önhivatkozással. Buktató: a végtelen `LazyList` fejére tartott hivatkozás miatt minden kiszámolt elem a memóriában marad.

```scala
import scala.annotation.tailrec
import scala.util.control.TailCalls.*

object Recursion:
  def sum(xs: List[Long]): Long =
    @tailrec def loop(rest: List[Long], acc: Long): Long = rest match
      case Nil    => acc
      case h :: t => loop(t, acc + h)          // az utolsó művelet a rekurzív hívás
    loop(xs, 0L)

  def binarySearch(arr: IndexedSeq[Int], target: Int): Option[Int] =
    @tailrec def go(lo: Int, hi: Int): Option[Int] =
      if lo > hi then None
      else
        val mid = lo + (hi - lo) / 2           // túlcsordulás-biztos közép
        if arr(mid) == target then Some(mid)
        else if arr(mid) < target then go(mid + 1, hi)
        else go(lo, mid - 1)
    go(0, arr.length - 1)

  // Végtelen, memoizált Fibonacci-sorozat (a #:: farka by-name, ezért lehet önhivatkozó)
  val fibs: LazyList[BigInt] = BigInt(0) #:: BigInt(1) #:: fibs.zip(fibs.tail).map(_ + _)

  // Lusta Eratoszthenész-szita
  def primes(from: LazyList[Int] = LazyList.from(2)): LazyList[Int] =
    from.head #:: primes(from.tail.filter(_ % from.head != 0))

  // Trampoline: kölcsönös rekurzió verembiztosan
  def isEven(n: Int): TailRec[Boolean] = if n == 0 then done(true) else tailcall(isOdd(n - 1))
  def isOdd(n: Int): TailRec[Boolean]  = if n == 0 then done(false) else tailcall(isEven(n - 1))

@main def runRecursion(): Unit =
  import Recursion.*
  println(sum(List.range(1L, 1_000_001L)))     // nincs veremtúlcsordulás
  println(binarySearch(Vector(1, 3, 5, 7, 9, 11), 9))
  println(fibs.take(15).toList)
  println(fibs(200))                           // memoizált, gyors
  println(primes().take(10).toList)
  println(isEven(100_001).result)
```

## sbt build és tesztelés (munit, ScalaCheck)
<!-- q: Hogyan állítsak be egy Scala projektet sbt-vel és hogyan írjak teszteket munit-tel és ScalaCheck-kel? -->
<!-- tags: sbt, build.sbt, testing, munit, scalacheck, property-based testing, dependencies -->

Az sbt a Scala szabványos build-eszköze: a `build.sbt` maga is Scala DSL, a `%%` operátor a függőség nevéhez a Scala bináris verzióját fűzi (pl. `_3`), a `% Test` csak a tesztekhez adja hozzá. Az sbt inkrementálisan fordít és folyamatosan futó shellt ad (`~test` minden mentéskor újrafuttat). Teszteléshez a munit (egyszerű, gyors) vagy a ScalaTest terjedt el; a ScalaCheck tulajdonság-alapú tesztelést ad: véletlen bemenetekre ellenőriz egy invariánst, és hiba esetén a legkisebb ellenpéldára szűkít (shrinking). Érdemes bekapcsolni a figyelmeztetéseket (`-Wunused:all`, `-deprecation`).

```scala
// build.sbt
ThisBuild / scalaVersion := "3.3.4"        // LTS vonal
ThisBuild / organization := "com.example"

lazy val root = (project in file("."))
  .settings(
    name := "inventory",
    libraryDependencies ++= Seq(
      "org.typelevel" %% "cats-effect"      % "3.5.4",
      "org.scalameta" %% "munit"            % "1.0.0" % Test,
      "org.scalameta" %% "munit-scalacheck" % "1.0.0" % Test,
    ),
    scalacOptions ++= Seq("-deprecation", "-feature", "-Wunused:all"),
  )
```

```scala
// src/main/scala/Inventory.scala
final case class Item(sku: String, qty: Int)

final class Inventory private (items: Map[String, Int]):
  def add(item: Item): Inventory =
    require(item.qty > 0, "pozitív mennyiség kell")
    new Inventory(items.updatedWith(item.sku)(q => Some(q.getOrElse(0) + item.qty)))

  def remove(sku: String, qty: Int): Either[String, Inventory] = items.get(sku) match
    case Some(have) if have >= qty => Right(new Inventory(items.updated(sku, have - qty).filter(_._2 > 0)))
    case Some(have)                => Left(s"csak $have db van")
    case None                      => Left(s"ismeretlen: $sku")

  def count(sku: String): Int = items.getOrElse(sku, 0)

object Inventory:
  val empty: Inventory = new Inventory(Map.empty)

// src/test/scala/InventorySuite.scala
import munit.ScalaCheckSuite
import org.scalacheck.Gen
import org.scalacheck.Prop.forAll

class InventorySuite extends ScalaCheckSuite:
  test("hozzáadás után a darabszám nő") {
    val inv = Inventory.empty.add(Item("A-1", 3)).add(Item("A-1", 2))
    assertEquals(inv.count("A-1"), 5)
  }

  test("túl sok kivétel hibát ad") {
    assertEquals(Inventory.empty.add(Item("A-1", 1)).remove("A-1", 2).map(_.count("A-1")), Left("csak 1 db van"))
  }

  test("nem pozitív mennyiség kivételt dob") {
    intercept[IllegalArgumentException](Inventory.empty.add(Item("X", 0)))
  }

  // Tulajdonság-alapú teszt: véletlen bemenetekre ellenőrzi az invariánst
  property("add, majd remove ugyanannyival nullára állítja a készletet") {
    forAll(Gen.alphaStr.suchThat(_.nonEmpty), Gen.choose(1, 1000)) { (sku: String, n: Int) =>
      Inventory.empty.add(Item(sku, n)).remove(sku, n).map(_.count(sku)) == Right(0)
    }
  }
```
