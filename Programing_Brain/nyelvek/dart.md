# Dart
<!-- tech: dart -->
<!-- aliases: flutter -->

A Dart a Google kliensoldalra optimalizált, objektumorientált nyelve hangos (sound) null safety-vel és erős statikus típusrendszerrel (típuskövetkeztetéssel). Fejlesztés közben JIT-tel fut (Flutter hot reload), kiadáskor AOT-tal natív gépi kódra fordul, de JavaScriptre és WebAssemblyre is fordítható. Minden isolate egyszálú eseményhurokkal és saját heappel dolgozik (async/await, Stream), a valódi párhuzamosság isolate-okkal érhető el; a memóriát generációs GC kezeli. Legfőbb felhasználása a Flutter keretrendszer (iOS, Android, web, desktop egy kódbázisból), emellett CLI-eszközökhöz és szerverhez is jó; alacsony szintű rendszerprogramozásra nem ideális.

## Null safety
<!-- q: Hogyan működik a null safety Dartban (?, !, late, required, ??)? -->
<!-- tags: null safety, nullable, late, required, null-aware operators, type promotion -->

Dartban a típusok alapból nem lehetnek null-ok; a nullable változatot `?` jelöli (`String?`), és a fordító kikényszeríti a null-ellenőrzést. A null-ellenőrzés után a lokális változó automatikusan nem-nullable típusra „lép elő” (type promotion), a `?.`, `??` és `??=` operátorok tömörítik a kezelést. A `late` kulcsszó későbbi, de olvasás előtt garantált inicializálást ígér (megszegése futásidejű `LateInitializationError`), a `!` pedig „biztosan nem null” állítás, ami ha mégis null, kivételt dob. Buktató: publikus mezőkre nincs automatikus promotion (getter felülírható), ezért lokális változóba kell másolni.

```dart
class Felhasznalo {
  final String nev;
  final String? becenev; // nullable: lehet null
  late final String _profilUrl; // később kap értéket, de olvasás előtt garantáltan

  Felhasznalo({required this.nev, this.becenev});

  String get megjelenitettNev => becenev ?? nev; // ?? : alapérték null esetén
  String get profilUrl => _profilUrl; // ha még nincs értéke -> LateInitializationError

  void profilBeallit(String id) => _profilUrl = 'https://cdn.example.com/u/$id.png';
}

int? hosszVagyNull(String? s) => s?.length; // ?. : null-biztos hívás

void main() {
  final f = Felhasznalo(nev: 'Teszt Elek');
  print(f.megjelenitettNev);

  String? bemenet = DateTime.now().second.isEven ? 'abc' : null;
  // Type promotion: a null-ellenőrzés után a fordító String-ként kezeli.
  if (bemenet != null) {
    print(bemenet.toUpperCase());
  }

  bemenet ??= 'alapérték'; // csak akkor ad értéket, ha null
  print(hosszVagyNull(bemenet));

  // A Map [] operátora mindig nullable típust ad; a ! állítja, hogy van érték.
  final keszlet = <String, int>{'alma': 3};
  final darab = keszlet['alma']!; // ha mégsem lenne -> futásidejű kivétel
  print(darab);

  // Publikus mezőre nincs promotion -> lokális változóba másolás.
  final b = f.becenev;
  if (b != null) print(b.length);

  f.profilBeallit('42');
  print(f.profilUrl);
}
```

## Osztályok és konstruktorok
<!-- q: Milyen konstruktorok vannak Dartban (nevesített, factory, const, inicializáló lista)? -->
<!-- tags: class, constructor, named constructor, factory, const constructor, initializer list, operator overloading -->

Dartban a konstruktor lehet generatív (`this.mezo` paraméterekkel), nevesített (`Penz.forint(...)`), átirányító (`: this(...)`), `factory` (nem feltétlenül hoz létre új példányt: cache, validálás, alosztály) és `const` (fordítási idejű, kanonikus példányok — Flutterben ez spórol újraépítést). Az inicializáló lista (`: assert(...), mezo = ...`) a konstruktortörzs előtt fut, így `final` mezők is számíthatók. Értékobjektumoknál az `==` mellett a `hashCode`-ot is felül kell írni (`Object.hash`), különben a Map/Set hibásan működik. A `super.` paraméterek (Dart 2.17+) tömörítik az ősosztálynak továbbított argumentumokat.

```dart
class Penz {
  final int fillerek; // egész ábrázolás: nincs lebegőpontos kerekítési hiba
  final String deviza;

  // const konstruktor: kanonikus, fordítási idejű példányok.
  const Penz(this.fillerek, this.deviza);

  // Nevesített konstruktor + inicializáló lista + assert.
  Penz.forint(double osszeg)
      : assert(osszeg >= 0, 'negatív összeg'),
        fillerek = (osszeg * 100).round(),
        deviza = 'HUF';

  // Átirányító konstruktor.
  const Penz.nulla(String deviza) : this(0, deviza);

  // factory: validál és parse-ol, mielőtt példányt adna.
  factory Penz.parse(String s) {
    final m = RegExp(r'^(\d+(?:\.\d{1,2})?)\s*([A-Z]{3})$').firstMatch(s.trim());
    if (m == null) throw FormatException('Érvénytelen összeg', s);
    return Penz((double.parse(m[1]!) * 100).round(), m[2]!);
  }

  Penz operator +(Penz o) {
    if (o.deviza != deviza) throw ArgumentError('Eltérő deviza: $deviza vs ${o.deviza}');
    return Penz(fillerek + o.fillerek, deviza);
  }

  @override
  bool operator ==(Object other) =>
      other is Penz && other.fillerek == fillerek && other.deviza == deviza;

  @override
  int get hashCode => Object.hash(fillerek, deviza); // == mellé KÖTELEZŐ

  @override
  String toString() => '${(fillerek / 100).toStringAsFixed(2)} $deviza';
}

// Öröklés + super paraméterek.
class Kedvezmenyes extends Penz {
  final double szazalek;
  const Kedvezmenyes(super.fillerek, super.deviza, {this.szazalek = 0});

  Penz alkalmaz() => Penz((fillerek * (1 - szazalek / 100)).round(), deviza);
}

void main() {
  const a = Penz(1500, 'HUF');
  const b = Penz(1500, 'HUF');
  print(identical(a, b)); // true — a const példányok kanonikusak
  print(Penz.forint(12.5) + Penz.parse('7.25 HUF')); // 19.75 HUF
  print(const Kedvezmenyes(10000, 'EUR', szazalek: 15).alkalmaz()); // 85.00 EUR
  print({a, b, const Penz.nulla('HUF')}.length); // 2 — a hashCode miatt helyes
}
```

## Mixinek, extension metódusok és extension type-ok
<!-- q: Hogyan használjam a mixineket, extension metódusokat és extension type-okat Dartban? -->
<!-- tags: mixin, extension methods, extension type, on clause, code reuse, zero-cost wrapper -->

A mixin (`mixin Naplozo`) újrahasznosítható viselkedést (metódusokat és mezőket) kever egy osztályba öröklési lánc nélkül (`with`), az `on` megkötés pedig előírja, milyen ősosztályra keverhető, így annak tagjai is hívhatók. Az extension metódus meglévő — akár SDK — típust bővít forráskód-módosítás nélkül, de statikusan oldódik fel (nem működik `dynamic`-on). Az extension type (Dart 3.3+) nulla futásidejű költségű, típusbiztos burkoló: futáskor csak az alaptípus létezik, fordításkor viszont külön típus, így pl. egy `FelhasznaloId` nem keverhető össze egy sima `int`-tel.

```dart
// Mixin: újrahasznosítható viselkedés.
mixin Naplozo {
  final List<String> _naplo = [];
  void naploz(String uzenet) => _naplo.add('[${DateTime.now().toIso8601String()}] $uzenet');
  List<String> get naplo => List.unmodifiable(_naplo);
}

abstract class Szolgaltatas {
  String get nev;
}

// 'on': csak Szolgaltatas leszármazottjaira keverhető, és használhatja a 'nev'-et.
mixin Ujraprobalo on Szolgaltatas {
  Future<T> ujra<T>(Future<T> Function() muvelet, {int max = 3}) async {
    for (var i = 1;; i++) {
      try {
        return await muvelet();
      } catch (e) {
        if (i >= max) rethrow;
        print('$nev: $i. próbálkozás sikertelen ($e)');
        await Future<void>.delayed(Duration(milliseconds: 100 * i)); // lineáris backoff
      }
    }
  }
}

class FizetesiSzolgaltatas extends Szolgaltatas with Naplozo, Ujraprobalo {
  @override
  String get nev => 'fizetés';
}

// Extension metódusok meglévő típusokra.
extension SzovegExt on String {
  String get nagyKezdobetu => isEmpty ? this : this[0].toUpperCase() + substring(1);
  bool get emailFormatum => RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(this);
}

extension Osszegzes<T extends num> on Iterable<T> {
  num get osszeg => fold<num>(0, (a, b) => a + b);
}

// Extension type: futáskor csak egy int, fordításkor külön típus.
extension type FelhasznaloId(int ertek) {
  FelhasznaloId.parse(String s) : this(int.parse(s));
  bool get ervenyes => ertek > 0;
}

void torol(FelhasznaloId id) => print('törlés: ${id.ertek}');

Future<void> main() async {
  final sz = FizetesiSzolgaltatas();
  var hivas = 0;
  final eredmeny = await sz.ujra(() async {
    if (++hivas < 2) throw StateError('timeout');
    return 'OK';
  });
  sz.naploz('fizetés: $eredmeny');
  print(sz.naplo.length);

  print('${'dart'.nagyKezdobetu} ${'a@b.hu'.emailFormatum} ${[1, 2, 3.5].osszeg}');
  torol(FelhasznaloId.parse('42'));
  // torol(42); // fordítási HIBA: int nem FelhasznaloId
}
```

## Generikusok
<!-- q: Hogyan működnek a generikusok Dartban (megkötések, generikus metódusok, reified típusok)? -->
<!-- tags: generics, type parameters, bounded types, reified generics, covariance, whereType -->

Dartban a generikusok reifikáltak: a típusargumentum futásidőben is ismert, így a `whereType<S>()` és az `is List<String>` ellenőrzés valóban működik. A típusparaméter `extends`-szel korlátozható, és a metódusoknak is lehet saját típusparaméterük. Buktatók: az `int` csak `Comparable<num>`-ot valósít meg, ezért egy `T extends Comparable<T>` megkötésnek nem felel meg; a Dart generikusai kovariánsak, így egy `List<Object>` típusú változón át egy `List<int>`-be írt string csak futásidőben bukik el.

```dart
abstract interface class Azonosithato {
  String get id;
}

class Repo<T extends Azonosithato> {
  final Map<String, T> _adat = {};

  void ment(T elem) => _adat[elem.id] = elem;
  T? keres(String id) => _adat[id];

  // Generikus metódus saját típusparaméterrel.
  List<R> lekepez<R>(R Function(T) f) => _adat.values.map(f).toList();

  // Futásidejű típusszűrés — a reified generikusok miatt működik.
  Iterable<S> tipusSzerint<S extends T>() => _adat.values.whereType<S>();
}

class Termek implements Azonosithato {
  @override
  final String id;
  final String nev;
  final int ar;
  Termek(this.id, this.nev, this.ar);
}

class DigitalisTermek extends Termek {
  final String letoltesUrl;
  DigitalisTermek(super.id, super.nev, super.ar, this.letoltesUrl);
}

// Megkötés: T összehasonlítható önmagával.
T legnagyobb<T extends Comparable<T>>(List<T> lista) {
  if (lista.isEmpty) throw StateError('üres lista');
  return lista.reduce((a, b) => a.compareTo(b) >= 0 ? a : b);
}

void main() {
  final repo = Repo<Termek>()
    ..ment(Termek('t1', 'Egér', 4990))
    ..ment(DigitalisTermek('d1', 'E-könyv', 2990, 'https://example.com/d1'));

  print(repo.lekepez((t) => t.nev)); // [Egér, E-könyv]
  print(repo.tipusSzerint<DigitalisTermek>().length); // 1
  print(legnagyobb(['körte', 'alma', 'szilva'])); // szilva
  // legnagyobb([3, 1]); // HIBA: int csak Comparable<num>, nem Comparable<int>

  print(<int>[] is List<String>); // false — a típusargumentum futásidőben is ismert

  // Kovariancia-buktató: fordul, de futásidőben TypeError.
  List<Object> objektumok = <int>[1, 2];
  try {
    objektumok.add('szöveg');
  } on TypeError catch (e) {
    print('futásidejű hiba: $e');
  }
}
```

## Recordok és mintaillesztés (patterns)
<!-- q: Hogyan használjam a recordokat és a pattern matchinget Dart 3-ban? -->
<!-- tags: records, patterns, destructuring, switch expression, pattern matching, dart 3 -->

A record (Dart 3) névtelen, immutable, értékszemantikájú összetett típus — pozicionális (`(double, double)`) vagy nevesített (`({String nev, int kor})`) mezőkkel —, ideális több visszatérési értékhez osztály definiálása nélkül; az egyenlősége szerkezeti. A minták (patterns) destrukturálnak változódeklarációban, `switch`-ben és `if-case`-ben: illeszthetők listára (`[a, b, ...]`), map-re, recordra, objektumra, típusra, és `when` őrfeltétellel szűrhetők. A `switch` kifejezés értéket ad vissza, és a fordító ellenőrzi a kimerítő lefedést. Buktató: a deklarációban lévő lista-minta futásidejű hibát dob, ha a hossz nem egyezik.

```dart
import 'dart:math' as math;

// Pozicionális record több visszatérési értékhez.
(double atlag, double szoras) statisztika(List<double> xs) {
  final n = xs.length;
  final atlag = xs.reduce((a, b) => a + b) / n;
  final variancia = xs.map((x) => (x - atlag) * (x - atlag)).reduce((a, b) => a + b) / n;
  return (atlag, math.sqrt(variancia));
}

// Nevesített mezős record.
({String nev, int kor}) parseSor(String sor) {
  final [nev, kor] = sor.split(';'); // lista-minta: eltérő hossz -> futásidejű hiba
  return (nev: nev.trim(), kor: int.parse(kor.trim()));
}

// JSON-szerű adatok szerkezeti illesztése switch kifejezéssel.
String leir(Object? json) => switch (json) {
      {'tipus': 'kor', 'r': num r} => 'kör, terület: ${(math.pi * r * r).toStringAsFixed(1)}',
      {'tipus': 'teglalap', 'a': num a, 'b': num b} when a == b => 'négyzet ($a)',
      {'tipus': 'teglalap', 'a': num a, 'b': num b} => 'téglalap ${a}x$b',
      [int elso, ...] => 'lista, első: $elso',
      String s when s.isEmpty => 'üres szöveg',
      null => 'semmi',
      _ => 'ismeretlen: $json',
    };

void main() {
  final (atlag, szoras) = statisztika([2, 4, 4, 4, 5, 5, 7, 9]);
  print('átlag=$atlag szórás=$szoras'); // 5.0 2.0

  final (:nev, :kor) = parseSor('Teszt Elek; 31'); // :nev = "nev: var nev" rövidítése
  print('$nev $kor');

  var a = 1, b = 2;
  (a, b) = (b, a); // csere segédváltozó nélkül
  print('$a $b');

  final mintak = <Object?>[
    {'tipus': 'kor', 'r': 2},
    {'tipus': 'teglalap', 'a': 3, 'b': 3},
    [7, 8],
    '',
    null,
  ];
  for (final j in mintak) {
    print(leir(j));
  }

  if (parseSor('Minta Anna;17') case (nev: final n, kor: < 18)) {
    print('$n kiskorú'); // if-case: illesztés + kötés egy lépésben
  }
  print((1, 'a') == (1, 'a')); // true — szerkezeti egyenlőség
}
```

## Sealed osztályok és osztálymódosítók
<!-- q: Hogyan használjam a sealed osztályokat és a kimerítő switch-et Dartban? -->
<!-- tags: sealed class, exhaustive switch, class modifiers, final class, interface class, base class -->

A `sealed` osztály leszármazottjai csak ugyanabban a könyvtárban (fájlban) definiálhatók, ezért a fordító ismeri a teljes listát, és a `switch` kimerítőségét `default` ág nélkül is ellenőrzi — ha új állapotot adsz hozzá, minden kezeletlen hely fordítási hibát ad. Ez ideális állapotgépekhez, UI-állapotokhoz (betöltés/adat/hiba) és eredménytípusokhoz. A Dart 3 további módosítói: `final` (könyvtáron kívül nem örökölhető és nem implementálható), `base` (csak örökölhető), `interface` (csak implementálható), `mixin class`. Objektum-mintákkal (`Bejelentkezve(:final felhasznalo)`) a mezők közvetlenül kiköthetők.

```dart
sealed class AuthAllapot {
  const AuthAllapot();
}

final class Kijelentkezve extends AuthAllapot {
  const Kijelentkezve();
}

final class Betoltes extends AuthAllapot {
  const Betoltes();
}

final class Bejelentkezve extends AuthAllapot {
  final String felhasznalo;
  final DateTime lejarat;
  const Bejelentkezve(this.felhasznalo, this.lejarat);
}

final class AuthHiba extends AuthAllapot {
  final String uzenet;
  final bool ujraprobalhato;
  const AuthHiba(this.uzenet, {this.ujraprobalhato = true});
}

// Kimerítő switch: nincs default; új alosztály -> fordítási hiba itt.
String allapotSzoveg(AuthAllapot a) => switch (a) {
      Kijelentkezve() => 'Kérlek, jelentkezz be',
      Betoltes() => 'Bejelentkezés...',
      Bejelentkezve(:final felhasznalo, :final lejarat) when lejarat.isBefore(DateTime.now()) =>
        'Lejárt munkamenet: $felhasznalo',
      Bejelentkezve(:final felhasznalo) => 'Üdv, $felhasznalo!',
      AuthHiba(uzenet: final u, ujraprobalhato: true) => '$u — próbáld újra',
      AuthHiba(:final uzenet) => 'Végzetes hiba: $uzenet',
    };

// "Tiszta interfész": csak implementálható, nem örökölhető.
abstract interface class AuthRepo {
  Future<AuthAllapot> bejelentkezes(String email, String jelszo);
}

class MemoriaAuthRepo implements AuthRepo {
  @override
  Future<AuthAllapot> bejelentkezes(String email, String jelszo) async {
    await Future<void>.delayed(const Duration(milliseconds: 50));
    if (!email.contains('@')) return const AuthHiba('Hibás email', ujraprobalhato: false);
    return Bejelentkezve(email, DateTime.now().add(const Duration(hours: 1)));
  }
}

Future<void> main() async {
  final repo = MemoriaAuthRepo();
  for (final email in ['teszt@example.com', 'rossz']) {
    print(allapotSzoveg(const Betoltes()));
    print(allapotSzoveg(await repo.bejelentkezes(email, 'pelda-jelszo')));
  }
}
```

## Future, async/await és hibakezelés
<!-- q: Hogyan használjam a Future-t és az async/await-et Dartban, párhuzamos várakozással és timeouttal? -->
<!-- tags: future, async, await, Future.wait, timeout, completer, error handling, event loop -->

A `Future<T>` egy később elkészülő érték; az `async` függvény mindig Future-t ad vissza, az `await` pedig felfüggeszti a függvényt az eseményhurok blokkolása nélkül. Egymás utáni `await`-ek szekvenciálisan futnak — független műveleteket párhuzamosan kell indítani (`Future.wait`, vagy Dart 3-ban recordon `.wait`, ami típusos eredményt ad). A hibák `try`/`on Tipus catch`/`finally` szerkezettel kezelhetők; a `.timeout()` csak az eredményt dobja el, a háttérben futó művelet nem áll le. Buktató: az `await` nélkül hagyott Future hibája kezeletlen marad — szándékos esetben jelöld `unawaited()`-del.

```dart
import 'dart:async';

class HalozatiHiba implements Exception {
  final int statusz;
  HalozatiHiba(this.statusz);
  @override
  String toString() => 'HalozatiHiba($statusz)';
}

// Szimulált API-hívás: késleltetés + esetenkénti hiba.
Future<Map<String, Object>> lekerdez(String eroforras, {int kesleltetesMs = 100}) async {
  await Future<void>.delayed(Duration(milliseconds: kesleltetesMs));
  if (eroforras == 'hibas') throw HalozatiHiba(503);
  return {'eroforras': eroforras, 'ido': kesleltetesMs};
}

Future<void> main() async {
  // 1) Szekvenciális: összesen ~200 ms.
  final a = await lekerdez('profil');
  final b = await lekerdez('beallitasok');
  print('szekvenciális: ${a['eroforras']}, ${b['eroforras']}');

  // 2) Párhuzamos: ~100 ms; recordon .wait -> típusos eredmény (Dart 3).
  final (profil, kosar) = await (lekerdez('profil'), lekerdez('kosar')).wait;
  print('párhuzamos: ${profil['eroforras']}, ${kosar['eroforras']}');

  // 3) Hibakezelés típus szerint; finally mindig lefut.
  try {
    await lekerdez('hibas');
  } on HalozatiHiba catch (e) {
    print('elkapva: $e (státusz=${e.statusz})');
  } catch (e, st) {
    print('váratlan: $e\n$st');
  } finally {
    print('takarítás');
  }

  // 4) Időkorlát: az eredményt eldobjuk, de a művelet a háttérben lefut!
  try {
    await lekerdez('lassu', kesleltetesMs: 2000).timeout(const Duration(milliseconds: 300));
  } on TimeoutException {
    print('timeout');
  }

  // 5) Future.wait eagerError-ral: az első hibánál azonnal visszatér.
  try {
    await Future.wait([lekerdez('a'), lekerdez('hibas'), lekerdez('c')], eagerError: true);
  } on HalozatiHiba catch (e) {
    print('Future.wait hiba: $e');
  }

  // 6) Completer: callback-alapú API-ból Future.
  final c = Completer<String>();
  Timer(const Duration(milliseconds: 50), () => c.complete('kész'));
  print(await c.future);
}
```

## Streamek: async*, StreamController, transzformációk
<!-- q: Hogyan használjam a Streameket Dartban (async*, StreamController, broadcast, transform)? -->
<!-- tags: stream, async*, yield, StreamController, broadcast, StreamTransformer, StreamSubscription -->

A `Stream<T>` időben érkező értékek aszinkron sorozata: `async*` generátorral (`yield`), `StreamController`-rel (kézi `add`) vagy beépített forrásokból (fájl, socket) jön létre, és `await for`-ral vagy `listen`-nel fogyasztható. Az operátorok (`where`, `map`, `take`, `transform`) új streamet adnak, saját lépés `StreamTransformer.fromBind`-dal írható. A single-subscription streamre csak egy hallgató iratkozhat fel; több hallgatóhoz `broadcast` kell. Buktatók: a `StreamSubscription`-t le kell mondani (`cancel`, Flutterben a `dispose`-ban), a controllert pedig le kell zárni, különben memóriaszivárgás lesz.

```dart
import 'dart:async';

// async* generátor: lusta, aszinkron értéksorozat.
Stream<int> szenzor(int db) async* {
  const meresek = [21, 22, 35, 23, 24, 50, 22];
  for (var i = 0; i < db; i++) {
    await Future<void>.delayed(const Duration(milliseconds: 20));
    yield meresek[i % meresek.length];
  }
}

// Saját transzformer: csúszó átlag.
StreamTransformer<int, double> csuszoAtlag(int ablak) =>
    StreamTransformer.fromBind((forras) async* {
      final buf = <int>[];
      await for (final v in forras) {
        buf.add(v);
        if (buf.length > ablak) buf.removeAt(0);
        yield buf.reduce((a, b) => a + b) / buf.length;
      }
    });

// StreamController: események kézi kibocsátása (pl. repositoryból).
class Ertesitesek {
  final _ctrl = StreamController<String>.broadcast(); // több hallgató is lehet
  Stream<String> get stream => _ctrl.stream;
  void kuld(String uzenet) => _ctrl.add(uzenet);
  Future<void> bezar() => _ctrl.close(); // mindig zárd le
}

Future<void> main() async {
  // Operátorok láncolása: kiugró értékek szűrése + csúszó átlag.
  await for (final atlag in szenzor(7).where((t) => t < 45).transform(csuszoAtlag(3))) {
    print('átlag: ${atlag.toStringAsFixed(1)}');
  }

  final e = Ertesitesek();
  final sub1 = e.stream.listen((u) => print('UI: $u'));
  final sub2 = e.stream
      .where((u) => u.startsWith('!'))
      .listen((u) => print('Riasztás: $u'), onDone: () => print('lezárva'));

  e
    ..kuld('új üzenet')
    ..kuld('!szerver lassú');
  await Future<void>.delayed(Duration.zero); // a kézbesítés aszinkron

  await sub1.cancel(); // a feliratkozást le KELL mondani
  await e.bezar(); // a sub2 onDone-ja lefut
  await sub2.cancel();
}
```

## Isolate-ok: párhuzamos végrehajtás
<!-- q: Hogyan futtassak CPU-igényes munkát háttérben isolate-tal Dartban/Flutterben? -->
<!-- tags: isolate, Isolate.run, compute, SendPort, ReceivePort, concurrency, parallelism -->

Az isolate saját heappel és eseményhurokkal rendelkező végrehajtási egység; az isolate-ok nem osztanak meg memóriát, csak üzenetekkel kommunikálnak, ezért nincs adatverseny — de az üzenetek másolódnak. Egyszeri, CPU-igényes feladatra (nagy JSON parse, képfeldolgozás, kriptográfia) az `Isolate.run` (Dart 2.19+, Flutterben `compute`) a legegyszerűbb, így a UI-isolate nem akad meg. Hosszú életű workerhez `Isolate.spawn` + `SendPort`/`ReceivePort` páros kell, kérés–válasz mintával. Buktató: a háttérbe küldött closure nem foghat be nem küldhető objektumot (nyitott socket, ReceivePort), és a nyitva hagyott port életben tartja a programot.

```dart
import 'dart:convert';
import 'dart:isolate';

// CPU-igényes, tiszta függvény: prímszámok száma (Eratoszthenész szitája).
int primekSzama(int n) {
  final szita = List<bool>.filled(n + 1, true);
  var db = 0;
  for (var i = 2; i <= n; i++) {
    if (!szita[i]) continue;
    db++;
    for (var j = i * i; j <= n; j += i) {
      szita[j] = false;
    }
  }
  return db;
}

// Hosszú életű worker: az első üzenet a worker saját SendPort-ja.
Future<(SendPort, Isolate)> workerIndit() async {
  final valaszPort = ReceivePort();
  final iso = await Isolate.spawn(_worker, valaszPort.sendPort);
  final port = await valaszPort.first as SendPort; // a first után a port lezárul
  return (port, iso);
}

void _worker(SendPort fo) {
  final bejovo = ReceivePort();
  fo.send(bejovo.sendPort);
  bejovo.listen((uzenet) {
    // Kérés-válasz minta: minden kéréshez saját válaszport jön.
    final (String json, SendPort valasz) = uzenet as (String, SendPort);
    final adat = jsonDecode(json) as List<dynamic>;
    valasz.send(adat.length);
  });
}

Future<int> kerdez(SendPort worker, String json) async {
  final rp = ReceivePort();
  worker.send((json, rp.sendPort));
  return await rp.first as int;
}

Future<void> main() async {
  // 1) Egyszeri feladat: Isolate.run (Flutterben: compute).
  final db = await Isolate.run(() => primekSzama(5000000));
  print('prímek: $db'); // a fő isolate közben szabad

  // 2) Nagy JSON feldolgozása hosszú életű workerben.
  final nagyJson = jsonEncode(List.generate(100000, (i) => {'id': i, 'nev': 'elem$i'}));
  final (worker, iso) = await workerIndit();
  print('elemek: ${await kerdez(worker, nagyJson)}');
  iso.kill(); // különben a worker ReceivePort-ja életben tartja a programot
}
```

## Flutter widgetek: Stateless, Stateful és életciklus
<!-- q: Mi a különbség a StatelessWidget és a StatefulWidget között Flutterben, és milyen az életciklusa? -->
<!-- tags: flutter, widget, StatelessWidget, StatefulWidget, setState, initState, dispose, lifecycle -->

Flutterben minden widget immutable konfiguráció; a `StatelessWidget` csak a konstruktor-paramétereiből (és az örökölt widgetekből, pl. `Theme`) épít. A `StatefulWidget` maga is immutable, a változó állapot a hosszú életű `State` objektumban él: `initState` egyszer fut, `didUpdateWidget` akkor, ha a szülő új konfigurációval építi újra (a State megmarad!), `dispose` a fából való végleges eltávolításkor. A `setState` jelzi, hogy a `build`-et újra kell futtatni. Buktatók: a `dispose`-ban minden Timert, Controllert és StreamSubscriptiont fel kell szabadítani, aszinkron callbackben pedig `mounted` ellenőrzés kell `setState` előtt.

```dart
import 'dart:async';
import 'package:flutter/material.dart';

class IdoKijelzo extends StatelessWidget {
  const IdoKijelzo({super.key, required this.masodperc});
  final int masodperc;

  @override
  Widget build(BuildContext context) {
    final p = masodperc ~/ 60, m = masodperc % 60;
    return Text(
      '${p.toString().padLeft(2, '0')}:${m.toString().padLeft(2, '0')}',
      style: Theme.of(context).textTheme.displayMedium, // örökölt (Inherited) függőség
    );
  }
}

class Stopperora extends StatefulWidget {
  const Stopperora({super.key, this.lepes = const Duration(seconds: 1)});
  final Duration lepes;

  @override
  State<Stopperora> createState() => _StopperoraState();
}

class _StopperoraState extends State<Stopperora> {
  Timer? _timer;
  int _eltelt = 0;

  @override
  void initState() {
    super.initState();
    _indit(); // egyszer, a State létrejöttekor
  }

  @override
  void didUpdateWidget(covariant Stopperora regi) {
    super.didUpdateWidget(regi);
    if (regi.lepes != widget.lepes) _indit(); // új konfiguráció, ugyanaz a State
  }

  void _indit() {
    _timer?.cancel();
    _timer = Timer.periodic(widget.lepes, (_) {
      if (!mounted) return; // a State már nincs a fában
      setState(() => _eltelt++); // a build újrafut
    });
  }

  @override
  void dispose() {
    _timer?.cancel(); // erőforrások felszabadítása
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        IdoKijelzo(masodperc: _eltelt),
        const SizedBox(height: 16), // const: nem épül újra feleslegesen
        FilledButton.icon(
          onPressed: () => setState(() => _eltelt = 0),
          icon: const Icon(Icons.restart_alt),
          label: const Text('Nullázás'),
        ),
      ],
    );
  }
}

void main() => runApp(const MaterialApp(home: Scaffold(body: Center(child: Stopperora()))));
```

## Flutter layout, listák és teljesítmény
<!-- q: Hogyan működik a layout Flutterben, és hogyan építsek gyors, hosszú listát? -->
<!-- tags: flutter, layout, constraints, Row, Column, Expanded, ListView.builder, keys, performance -->

A Flutter layout aranyszabálya: a korlátok (constraints) lefelé mennek, a méretek felfelé, a pozíciót a szülő állítja be. A `Row`/`Column` a fő tengelyen nem korlátozza a gyerekeket, ezért a maradék hely kitöltéséhez `Expanded`/`Flexible` kell — a Column-ba tett `ListView` `Expanded` nélkül „unbounded height” hibát ad. Hosszú listához a `ListView.builder` kell, mert csak a látható elemeket építi fel; a fix `itemExtent` tovább gyorsít. Teljesítmény: használj `const` widgeteket, stabil `Key`-t (pl. `ValueKey(id)`) átrendezhető listában, és a `LayoutBuilder`-rel a kapott korlátok alapján építs reszponzív elrendezést.

```dart
import 'package:flutter/material.dart';

class Termek {
  const Termek(this.id, this.nev, this.ar);
  final int id;
  final String nev;
  final int ar;
}

class TermekOldal extends StatelessWidget {
  const TermekOldal({super.key, required this.termekek});
  final List<Termek> termekek;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Termékek')),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                // Expanded: kitölti a Row maradék helyét.
                const Expanded(child: TextField(decoration: InputDecoration(hintText: 'Keresés'))),
                const SizedBox(width: 8),
                IconButton(onPressed: () {}, icon: const Icon(Icons.filter_list)),
              ],
            ),
          ),
          // Column-ban a ListView-nak Expanded kell, különben végtelen magasságot kapna.
          Expanded(
            child: ListView.builder(
              itemCount: termekek.length,
              itemExtent: 72, // fix sormagasság: gyorsabb görgetés
              itemBuilder: (context, i) {
                final t = termekek[i];
                return ListTile(
                  key: ValueKey(t.id), // stabil kulcs: az állapot az elemmel együtt mozog
                  leading: CircleAvatar(child: Text(t.nev[0])),
                  title: Text(t.nev, maxLines: 1, overflow: TextOverflow.ellipsis),
                  trailing: Text('${t.ar} Ft'),
                );
              },
            ),
          ),
          // Reszponzív döntés a kapott korlátok alapján.
          LayoutBuilder(
            builder: (context, korlat) => korlat.maxWidth > 600
                ? const Text('Széles nézet', textAlign: TextAlign.center)
                : const Text('Keskeny nézet'),
          ),
        ],
      ),
    );
  }
}

void main() => runApp(MaterialApp(
      home: TermekOldal(
        termekek: List.generate(5000, (i) => Termek(i, 'Termék $i', 990 + i)),
      ),
    ));
```

## Állapotkezelés: ChangeNotifier és InheritedNotifier
<!-- q: Hogyan osszam meg az állapotot widgetek között Flutterben külső csomag nélkül? -->
<!-- tags: flutter, state management, ChangeNotifier, InheritedWidget, InheritedNotifier, ListenableBuilder -->

A `setState` csak egy widget helyi állapotára jó; több képernyő által használt állapothoz (kosár, bejelentkezés) az állapotot egy `ChangeNotifier`-be emeljük, amely `notifyListeners()`-szel jelez. A fában lefelé egy `InheritedNotifier` (InheritedWidget + Listenable) teszi elérhetővé: a `dependOnInheritedWidgetOfExactType` feliratkoztatja a hívó widgetet, így változáskor csak a függő widgetek épülnek újra. Eseménykezelőben a feliratkozás nélküli `getInheritedWidgetOfExactType` a helyes (ezt csinálja a Provider `read`-je is). Helyi, célzott újraépítéshez a `ListenableBuilder` használható; a modellt birtokló State `dispose`-ában a notifiert is fel kell szabadítani.

```dart
import 'package:flutter/material.dart';

class KosarModell extends ChangeNotifier {
  final Map<String, int> _tetelek = {};
  Map<String, int> get tetelek => Map.unmodifiable(_tetelek);
  int get darab => _tetelek.values.fold(0, (a, b) => a + b);

  void hozzaad(String termek) {
    _tetelek.update(termek, (n) => n + 1, ifAbsent: () => 1);
    notifyListeners(); // a feliratkozott widgetek újraépülnek
  }
}

class KosarScope extends InheritedNotifier<KosarModell> {
  const KosarScope({super.key, required KosarModell modell, required super.child})
      : super(notifier: modell);

  // build-ben: feliratkozik -> változáskor újraépül.
  static KosarModell watch(BuildContext c) =>
      c.dependOnInheritedWidgetOfExactType<KosarScope>()!.notifier!;

  // eseménykezelőben: feliratkozás nélkül olvas.
  static KosarModell read(BuildContext c) => c.getInheritedWidgetOfExactType<KosarScope>()!.notifier!;
}

class KosarIkon extends StatelessWidget {
  const KosarIkon({super.key});
  @override
  Widget build(BuildContext context) =>
      Badge(label: Text('${KosarScope.watch(context).darab}'), child: const Icon(Icons.shopping_cart));
}

class TermekGomb extends StatelessWidget {
  const TermekGomb(this.nev, {super.key});
  final String nev;
  @override
  Widget build(BuildContext context) =>
      ElevatedButton(onPressed: () => KosarScope.read(context).hozzaad(nev), child: Text(nev));
}

class KosarApp extends StatefulWidget {
  const KosarApp({super.key});
  @override
  State<KosarApp> createState() => _KosarAppState();
}

class _KosarAppState extends State<KosarApp> {
  final _modell = KosarModell(); // a State birtokolja -> túléli az újraépítéseket

  @override
  void dispose() {
    _modell.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => KosarScope(
        modell: _modell,
        child: MaterialApp(
          home: Scaffold(
            appBar: AppBar(actions: const [KosarIkon()]),
            body: Column(children: [
              const TermekGomb('Alma'),
              const TermekGomb('Körte'),
              ListenableBuilder(
                listenable: _modell, // csak ez a rész épül újra
                builder: (context, _) => Text('Tételek: ${_modell.tetelek}'),
              ),
            ]),
          ),
        ),
      );
}

void main() => runApp(const KosarApp());
```

## Állapotkezelés Riverpoddal
<!-- q: Hogyan kezeljem az állapotot Riverpoddal Flutterben (Notifier, FutureProvider, ref.watch)? -->
<!-- tags: flutter, riverpod, provider, notifier, FutureProvider, AsyncValue, ConsumerWidget, state management -->

A Riverpod (`flutter_riverpod` csomag) a providereket globális, de immutable deklarációként kezeli, a `BuildContext`-től függetlenül, így fordítási időben biztonságos és tesztben könnyen felülírható (`overrides`). A `ref.watch` feliratkozik és függőséget épít (a származtatott provider automatikusan újraszámolódik), a `ref.read` eseménykezelőben egyszeri olvasásra való. A `Notifier` szinkron, a `FutureProvider`/`AsyncNotifier` aszinkron állapotot ad `AsyncValue` formában (data/loading/error), az `autoDispose` pedig felszabadítja a már nem figyelt állapotot. Alternatívák: Provider (egyszerűbb), BLoC (eseményvezérelt, stream-alapú).

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class TermekApi {
  Future<List<String>> lista(String szuro) async {
    await Future<void>.delayed(const Duration(milliseconds: 300)); // hálózati késés szimulálása
    return ['Egér', 'Billentyűzet', 'Monitor']
        .where((t) => t.toLowerCase().contains(szuro))
        .toList();
  }
}

// Függőség-provider: tesztben felülírható (overrideWithValue).
final apiProvider = Provider<TermekApi>((ref) => TermekApi());

// Szinkron állapot Notifierrel.
class SzuroNotifier extends Notifier<String> {
  @override
  String build() => ''; // kezdőállapot
  void beallit(String s) => state = s.toLowerCase();
}

final szuroProvider = NotifierProvider<SzuroNotifier, String>(SzuroNotifier.new);

// Származtatott, aszinkron állapot: a szűrő változásakor automatikusan újratölt.
final termekekProvider = FutureProvider.autoDispose<List<String>>((ref) async {
  final szuro = ref.watch(szuroProvider);
  return ref.watch(apiProvider).lista(szuro);
});

class TermekLista extends ConsumerWidget {
  const TermekLista({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final allapot = ref.watch(termekekProvider); // AsyncValue<List<String>>
    return Column(children: [
      // eseménykezelőben read, nem watch
      TextField(onChanged: (s) => ref.read(szuroProvider.notifier).beallit(s)),
      Expanded(
        child: allapot.when(
          data: (lista) => ListView(children: [for (final t in lista) ListTile(title: Text(t))]),
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => Center(child: Text('Hiba: $e')),
        ),
      ),
    ]);
  }
}

// A ProviderScope tárolja az összes provider állapotát.
void main() => runApp(const ProviderScope(
      child: MaterialApp(home: Scaffold(body: TermekLista())),
    ));
```

## Aszinkron UI: FutureBuilder és StreamBuilder
<!-- q: Hogyan jelenítsek meg aszinkron adatot FutureBuilderrel és StreamBuilderrel Flutterben? -->
<!-- tags: flutter, FutureBuilder, StreamBuilder, AsyncSnapshot, RefreshIndicator, loading state -->

A `FutureBuilder` és a `StreamBuilder` egy Future/Stream aktuális állapotát (`AsyncSnapshot`: connectionState, data, error) képezi le widgetre, így a betöltés–adat–hiba állapotok deklaratívan kezelhetők. A legfontosabb szabály: a Future-t vagy Streamet NE a `build`-ben hozd létre, mert a build bármikor újrafuthat, és minden alkalommal új kérés indulna — tárold a `State`-ben, és újratöltéskor `setState`-ben cseréld. A `setState` callbackje nem adhat vissza Future-t, ezért blokk-törzsű függvényt használj benne. A StreamBuilder a widget eltávolításakor magától lemondja a feliratkozást.

```dart
import 'package:flutter/material.dart';

class Profil {
  const Profil(this.nev, this.pont);
  final String nev;
  final int pont;
}

Future<Profil> profilBetolt() async {
  await Future<void>.delayed(const Duration(seconds: 1));
  return const Profil('Teszt Elek', 1200);
}

Stream<int> onlineSzam() => Stream.periodic(const Duration(seconds: 2), (i) => 10 + i % 5);

class ProfilOldal extends StatefulWidget {
  const ProfilOldal({super.key});
  @override
  State<ProfilOldal> createState() => _ProfilOldalState();
}

class _ProfilOldalState extends State<ProfilOldal> {
  // A Future/Stream a State-ben él, NEM a build-ben jön létre.
  late Future<Profil> _profil = profilBetolt();
  late final Stream<int> _online = onlineSzam();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: RefreshIndicator(
        onRefresh: () async {
          setState(() {
            _profil = profilBetolt(); // blokk-törzs: a setState nem kaphat Future-t
          });
          await _profil;
        },
        child: ListView(children: [
          FutureBuilder<Profil>(
            future: _profil,
            builder: (context, snap) {
              if (snap.connectionState == ConnectionState.waiting) {
                return const LinearProgressIndicator();
              }
              if (snap.hasError) return Text('Hiba: ${snap.error}');
              final p = snap.requireData;
              return ListTile(title: Text(p.nev), subtitle: Text('${p.pont} pont'));
            },
          ),
          StreamBuilder<int>(
            stream: _online,
            initialData: 0,
            builder: (context, snap) => Text('Online felhasználók: ${snap.data}'),
          ),
        ]),
      ),
    );
  }
}

void main() => runApp(const MaterialApp(home: ProfilOldal()));
```

## JSON szerializálás
<!-- q: Hogyan alakítsak JSON-t Dart objektummá és vissza (fromJson, toJson)? -->
<!-- tags: json, serialization, fromJson, toJson, jsonDecode, json_serializable, patterns -->

A `dart:convert` `jsonDecode`-ja `Map<String, dynamic>`/`List<dynamic>` szerkezetet ad, amit típusos modellé kell alakítani; az idiomatikus forma egy `fromJson` factory és egy `toJson` metódus. Dart 3-ban a map-minta (`{'id': int id, ...}`) egyszerre validál és köt, így hibás bemenetnél egyértelmű `FormatException` dobható a homályos `TypeError` helyett. A `JsonEncoder` a nem kódolható objektumokon automatikusan meghívja a `toJson()`-t. Nagyobb projektben a `json_serializable` vagy `freezed` kódgenerátor (build_runner) állítja elő ugyanezt; buktató, hogy a JSON-szám lehet `int` vagy `double`, ezért `num`-ként olvasd.

```dart
import 'dart:convert';

class Rendeles {
  const Rendeles({required this.id, required this.tetelek, required this.letrehozva, this.megjegyzes});

  final int id;
  final List<Tetel> tetelek;
  final DateTime letrehozva;
  final String? megjegyzes;

  int get vegosszeg => tetelek.fold(0, (s, t) => s + t.ar * t.darab);

  // Mintaillesztéssel validált dekódolás.
  factory Rendeles.fromJson(Map<String, dynamic> json) => switch (json) {
        {'id': int id, 'tetelek': List<dynamic> tetelek, 'letrehozva': String datum} => Rendeles(
            id: id,
            tetelek: [for (final t in tetelek) Tetel.fromJson(t as Map<String, dynamic>)],
            letrehozva: DateTime.parse(datum),
            megjegyzes: json['megjegyzes'] as String?, // opcionális mező
          ),
        _ => throw FormatException('Érvénytelen rendelés JSON: $json'),
      };

  Map<String, dynamic> toJson() => {
        'id': id,
        'tetelek': [for (final t in tetelek) t.toJson()],
        'letrehozva': letrehozva.toUtc().toIso8601String(),
        if (megjegyzes != null) 'megjegyzes': megjegyzes, // collection-if
      };
}

class Tetel {
  const Tetel(this.sku, this.darab, this.ar);
  final String sku;
  final int darab;
  final int ar;

  factory Tetel.fromJson(Map<String, dynamic> j) => Tetel(
        j['sku'] as String,
        (j['darab'] as num).toInt(), // a JSON-szám lehet 2 vagy 2.0
        (j['ar'] as num).toInt(),
      );

  Map<String, dynamic> toJson() => {'sku': sku, 'darab': darab, 'ar': ar};
}

void main() {
  const bemenet = '''
  {"id": 42, "letrehozva": "2026-02-10T09:15:00Z",
   "tetelek": [{"sku": "KB-1", "darab": 2, "ar": 12990}, {"sku": "M-7", "darab": 1, "ar": 4990}]}
  ''';
  final r = Rendeles.fromJson(jsonDecode(bemenet) as Map<String, dynamic>);
  print('végösszeg: ${r.vegosszeg}'); // 30970
  print(const JsonEncoder.withIndent('  ').convert(r)); // a toJson() automatikusan hívódik

  try {
    Rendeles.fromJson({'id': 'nem-szam'});
  } on FormatException catch (e) {
    print(e.message);
  }
}
```

## Tesztelés: unit és widget tesztek
<!-- q: Hogyan írjak unit és widget teszteket Dartban/Flutterben? -->
<!-- tags: testing, unit test, widget test, flutter_test, testWidgets, expect, group, setUp -->

A Dart tesztek a `test` csomaggal (Flutterben a `flutter_test`-tel) készülnek: `group` csoportosít, `setUp` minden teszt előtt friss állapotot ad, az `expect` pedig matcherekkel (`throwsArgumentError`, `findsOneWidget`) ellenőriz. A widget teszt (`testWidgets`) valódi eszköz nélkül, gyorsan építi fel a widgetfát: a `tester.pumpWidget` felépíti, a `tap` eseményt szimulál, a `pump` egy frame-et léptet (animációknál `pumpAndSettle`), a `find` pedig szöveg, kulcs vagy típus alapján keres. Futtatás: `dart test` vagy `flutter test`; függőségek mockolásához a `mocktail` csomag ajánlott.

```dart
// test/kosar_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

// --- tesztelt kód (rendesen a lib/ mappában) ---
class Kosar {
  final _t = <String, int>{};
  int get darab => _t.values.fold(0, (a, b) => a + b);
  void hozzaad(String sku, {int db = 1}) {
    if (db <= 0) throw ArgumentError.value(db, 'db', 'pozitív kell legyen');
    _t.update(sku, (n) => n + db, ifAbsent: () => db);
  }
}

class Szamlalo extends StatefulWidget {
  const Szamlalo({super.key});
  @override
  State<Szamlalo> createState() => _SzamlaloState();
}

class _SzamlaloState extends State<Szamlalo> {
  int _n = 0;
  @override
  Widget build(BuildContext context) => MaterialApp(
        home: Scaffold(
          body: Text('Érték: $_n'),
          floatingActionButton: FloatingActionButton(
            key: const Key('novel'),
            onPressed: () => setState(() => _n++),
            child: const Icon(Icons.add),
          ),
        ),
      );
}

// --- tesztek ---
void main() {
  group('Kosar', () {
    late Kosar kosar;
    setUp(() => kosar = Kosar()); // minden teszt előtt friss példány

    test('összeadja az azonos tételeket', () {
      kosar
        ..hozzaad('A')
        ..hozzaad('A', db: 2);
      expect(kosar.darab, 3);
    });

    test('nem pozitív darabszámra hibát dob', () {
      expect(() => kosar.hozzaad('B', db: 0), throwsArgumentError);
    });
  });

  testWidgets('a gomb növeli a számlálót', (tester) async {
    await tester.pumpWidget(const Szamlalo()); // widgetfa felépítése
    expect(find.text('Érték: 0'), findsOneWidget);

    await tester.tap(find.byKey(const Key('novel')));
    await tester.pump(); // egy frame: a setState hatása megjelenik

    expect(find.text('Érték: 1'), findsOneWidget);
    expect(find.text('Érték: 0'), findsNothing);
  });
}
```
