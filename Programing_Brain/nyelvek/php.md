# PHP
<!-- tech: php -->
<!-- aliases: laravel, symfony -->

A PHP szerveroldali, dinamikusan típusos szkriptnyelv, a web egyik legelterjedtebb backend-nyelve (WordPress, Laravel, Symfony). Minden HTTP kérés jellemzően egy rövid életű folyamatban (PHP-FPM worker) fut "share-nothing" modellben, ezért az állapot adatbázisban, sessionben vagy cache-ben él; a memóriát referenciaszámlálás + ciklusgyűjtő kezeli. A PHP 8.x komoly, opcionálisan szigorú típusrendszert (strict_types, union/intersection típusok, enum, readonly), JIT-et és Fibereket hozott. Kiváló CRUD webappokhoz, API-khoz és tartalomkezelőkhöz; kevésbé jó hosszan futó, CPU-intenzív vagy erősen párhuzamos feladatokra (ott Go, Rust vagy egy háttér-queue a jobb választás).

## Szigorú típusok és típusdeklarációk
<!-- q: Hogyan használjam a strict_types-t és a típusdeklarációkat PHP 8-ban? -->
<!-- tags: strict_types, type hints, union types, nullable, never, typeerror -->

A `declare(strict_types=1)` kikapcsolja a skalárok automatikus konverzióját a függvényhívásoknál: a `'100'` string nem lesz csendben `int`, hanem `TypeError` keletkezik. Fájlszintű és a *hívó* fájlra vonatkozik, ezért minden fájl elejére kell. A PHP 8 union (`int|float`), nullable (`?Money`), `mixed`, `never` és `static` visszatérési típusokat is ismer. Buktató: a belső függvények (pl. `strlen`) is szigorúan ellenőriznek, ezért a `null` átadása régi kódban hirtelen hibát dobhat.

```php
<?php
declare(strict_types=1); // fájlszintű: csak az ebből a fájlból indított hívásokra hat

namespace App\Billing;

final class Money
{
    public function __construct(
        public readonly int $cents,       // pénzt mindig egész centben tárolunk, nem float-ban
        public readonly string $currency,
    ) {
        if ($cents < 0) {
            throw new \InvalidArgumentException('Negatív összeg nem megengedett');
        }
    }
}

// Union típus: int vagy float jöhet, a visszatérés mindig Money
function fromDecimal(int|float $amount, string $currency = 'HUF'): Money
{
    return new Money((int) round($amount * 100), $currency);
}

// Nullable visszatérés: ?Money ugyanaz, mint Money|null
function parseMoney(string $raw): ?Money
{
    if (!preg_match('/^(\d+(?:\.\d{1,2})?)\s*([A-Z]{3})$/', trim($raw), $m)) {
        return null;
    }
    return fromDecimal((float) $m[1], $m[2]);
}

// never: a függvény soha nem tér vissza normálisan (kivételt dob vagy exit-el)
function fail(string $msg): never
{
    throw new \DomainException($msg);
}

$ok = parseMoney('1250.50 EUR') ?? fail('Hibás formátum');
echo $ok->cents, PHP_EOL; // 125050

try {
    // strict_types mellett a '100' string NEM konvertálódik int-té -> TypeError
    new Money('100', 'HUF');
} catch (\TypeError $e) {
    echo 'TypeError: ', $e->getMessage(), PHP_EOL;
}
```

## Enumok és a match kifejezés
<!-- q: Hogyan használjak enumot és match kifejezést PHP-ban? -->
<!-- tags: enum, backed enum, match, state machine, php 8.1 -->

A PHP 8.1 enumjai valódi típusok: lehetnek "backed" (string/int értékkel, így adatbázisba menthetők), implementálhatnak interfészt, és lehetnek metódusaik és konstansaik. A `match` a `switch` modern párja: kifejezés (értéket ad), szigorú `===` összehasonlítást használ, nincs "átesés", és ha egyik ág sem illeszkedik, `UnhandledMatchError`-t dob – ez enumokkal kombinálva kimerítő vizsgálatot ad. A `from()` ismeretlen értékre kivételt dob, a `tryFrom()` `null`-t ad, ezért felhasználói inputhoz az utóbbi kell.

```php
<?php
declare(strict_types=1);

interface HasLabel
{
    public function label(): string;
}

// Backed enum: minden esethez skalár érték tartozik -> DB-be menthető
enum OrderStatus: string implements HasLabel
{
    case Pending   = 'pending';
    case Paid      = 'paid';
    case Shipped   = 'shipped';
    case Cancelled = 'cancelled';

    public const DEFAULT = self::Pending; // konstans az enumon belül

    // Ha új case jön és itt kimarad, futáskor UnhandledMatchError (és a statikus elemző is szól)
    public function label(): string
    {
        return match ($this) {
            self::Pending   => 'Fizetésre vár',
            self::Paid      => 'Fizetve',
            self::Shipped   => 'Kiszállítva',
            self::Cancelled => 'Törölve',
        };
    }

    // Állapotgép: mely átmenetek engedélyezettek
    public function canTransitionTo(self $next): bool
    {
        return match ($this) {
            self::Pending   => in_array($next, [self::Paid, self::Cancelled], true),
            self::Paid      => $next === self::Shipped || $next === self::Cancelled,
            self::Shipped, self::Cancelled => false, // több eset egy ágban
        };
    }
}

// tryFrom: ismeretlen inputra null, nem kivétel
$status = OrderStatus::tryFrom($_GET['status'] ?? '') ?? OrderStatus::DEFAULT;
echo $status->label(), PHP_EOL;
var_dump($status->canTransitionTo(OrderStatus::Paid));

// match(true): feltétel-alapú elágazás; a throw is kifejezés (PHP 8.0+)
function shippingFee(int $weightGrams): int
{
    return match (true) {
        $weightGrams <= 0    => throw new ValueError('Érvénytelen súly'),
        $weightGrams < 2000  => 1490,
        $weightGrams < 10000 => 2990,
        default              => 4990,
    };
}

// Összes eset listázása, pl. <select> mezőhöz
$options = array_map(fn (OrderStatus $s) => [$s->value => $s->label()], OrderStatus::cases());
```

## Readonly property-k és constructor promotion
<!-- q: Hogyan készítsek immutable value objectet readonly property-kkel PHP-ban? -->
<!-- tags: readonly, constructor promotion, immutability, value object, wither -->

A constructor promotion a konstruktor paramétereiből egyben property-t is deklarál, ami eltünteti a boilerplate-et. A `readonly` property csak egyszer, az osztály saját scope-jából írható; a PHP 8.2 `readonly class` minden property-t readonly-vá tesz és tiltja a dinamikus property-ket. A módosítást "wither" metódusokkal oldjuk meg, amelyek új példányt adnak vissza. Buktató: a readonly csak a *referenciát* védi – egy readonly property-ben tárolt mutable objektum belseje továbbra is változhat; PHP 8.3-tól a `__clone`-ban újra lehet inicializálni readonly mezőt, 8.4-től pedig property hooks és aszimmetrikus láthatóság (`public private(set)`) is van.

```php
<?php
declare(strict_types=1);

// PHP 8.2: readonly class -> minden property readonly, dinamikus property tilos
final readonly class Address
{
    public function __construct(
        public string $city,
        public string $zip,
        public string $street,
    ) {}
}

final class Customer
{
    public function __construct(
        public readonly int $id,            // csak egyszer, az osztály scope-jából írható
        public readonly string $email,
        public readonly Address $address,   // a referencia readonly; itt az Address is az
        private array $tags = [],           // nem readonly, belsőleg módosítható
    ) {
        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            throw new InvalidArgumentException('Érvénytelen e-mail');
        }
    }

    // "Wither" minta: módosítás helyett új példány
    public function withEmail(string $email): static
    {
        return new static($this->id, $email, $this->address, $this->tags);
    }

    public function withTag(string $tag): static
    {
        $tags = array_values(array_unique([...$this->tags, $tag])); // spread tömbben
        return new static($this->id, $this->email, $this->address, $tags);
    }

    public function tags(): array
    {
        return $this->tags; // tömb érték szerint adódik vissza -> kívülről nem módosítható
    }
}

$c  = new Customer(1, 'user@example.com', new Address('Budapest', '1011', 'Fő utca 1.'));
$c2 = $c->withEmail('other@example.com')->withTag('vip');

echo $c->email, ' / ', $c2->email, ' / ', implode(',', $c2->tags()), PHP_EOL;

try {
    $c->email = 'hack@example.com'; // Error: Cannot modify readonly property
} catch (Error $e) {
    echo $e->getMessage(), PHP_EOL;
}
```

## Attribútumok és Reflection
<!-- q: Hogyan írjak saját attribútumot és olvassam ki Reflectionnel PHP-ban? -->
<!-- tags: attributes, reflection, metadata, routing, annotations -->

Az attribútumok (`#[...]`, PHP 8.0) strukturált, natív metaadatok osztályokon, metódusokon, property-ken és paramétereken – a régi docblock-annotációk utódai. Önmagukban nem csinálnak semmit: egy keretrendszer (router, ORM, validátor, DI container) olvassa ki őket Reflectionnel. A `#[Attribute]` jelzi, hol használható (`TARGET_*`) és ismételhető-e. Teljesítmény: a reflection drága, ezért éles környezetben az eredményt cache-elni kell (a Symfony és a Laravel is lefordítja/cache-eli a route-táblát).

```php
<?php
declare(strict_types=1);

namespace App\Http;

use Attribute;
use ReflectionClass;
use ReflectionMethod;

// Saját attribútum: csak metóduson használható, és többször is szerepelhet
#[Attribute(Attribute::TARGET_METHOD | Attribute::IS_REPEATABLE)]
final class Route
{
    public function __construct(
        public string $method,
        public string $path,
        public ?string $name = null,
    ) {}
}

final class ProductController
{
    #[Route('GET', '/products', name: 'products.index')]
    public function index(): array { return ['list']; }

    #[Route('GET', '/products/{id}')]
    #[Route('HEAD', '/products/{id}')]   // IS_REPEATABLE miatt kétszer is szerepelhet
    public function show(int $id): array { return ['id' => $id]; }

    public function helper(): void {}   // nincs attribútum -> nem lesz route
}

/** Reflectionnel összegyűjti a route-okat: ['GET /products' => [osztály, metódus], ...] */
function collectRoutes(string ...$controllers): array
{
    $table = [];
    foreach ($controllers as $class) {
        $ref = new ReflectionClass($class);
        foreach ($ref->getMethods(ReflectionMethod::IS_PUBLIC) as $method) {
            // getAttributes szűrhető osztálynévre; a newInstance() példányosít és validál
            foreach ($method->getAttributes(Route::class) as $attr) {
                $route = $attr->newInstance();
                $table["{$route->method} {$route->path}"] = [$class, $method->getName()];
            }
        }
    }
    return $table;
}

// Élesben: var_export-tal fájlba cache-elve, és csak deploykor újragenerálva
print_r(collectRoutes(ProductController::class));
```

## Closure-ök, binding és first-class callable szintaxis
<!-- q: Hogyan működnek a closure-ök, a Closure::bind és a strlen(...) szintaxis PHP-ban? -->
<!-- tags: closure, arrow function, bind, bindTo, first-class callable, functional -->

A `function () use ($x)` érték szerint (másolatként) fogja be a változókat, `use (&$x)`-szel referencia szerint; az arrow function (`fn`) automatikusan, de mindig érték szerint fog be, és csak egy kifejezés lehet. A `Closure::bind`/`bindTo` egy closure `$this`-ét és scope-ját cseréli – így privát állapot is elérhető (hidratáláshoz, tesztekhez). A PHP 8.1 first-class callable szintaxisa (`strlen(...)`, `$obj->method(...)`) valódi `Closure`-t ad string-callable helyett, ami refaktorálás- és IDE-barát. Buktató: `static fn` nem köthető objektumhoz, cserébe nem tart életben feleslegesen `$this`-t.

```php
<?php
declare(strict_types=1);

final class Counter
{
    private int $count = 0;
}

// 1) Closure::bind: privát állapot elérése – az objektum ÉS a scope (osztály) is kell
$peek = Closure::bind(fn () => $this->count, new Counter(), Counter::class);
echo $peek(), PHP_EOL; // 0

// bindTo: ugyanaz a closure egy konkrét objektumra kötve
$increment = function (int $by): int {
    return $this->count += $by;
};
$inc = $increment->bindTo(new Counter(), Counter::class);
$inc(5);
echo $inc(2), PHP_EOL; // 7

// 2) use: alapból érték szerint; &-tel referencia szerint
$total = 0;
$add = function (int $x) use (&$total): void { $total += $x; };
foreach ([1, 2, 3] as $n) {
    $add($n);
}
echo $total, PHP_EOL; // 6

// Arrow function: automatikus, érték szerinti befogás, egyetlen kifejezés
$rate  = 1.27;
$gross = array_map(fn (int $net): float => round($net * $rate, 2), [100, 250]);

// 3) First-class callable (PHP 8.1): strlen(...) -> Closure
$trim      = trim(...);
$normalize = static fn (string $s): string => mb_strtolower($trim($s));

// Függvénykompozíció: balról jobbra alkalmazza a lépéseket
function pipe(callable ...$fns): Closure
{
    return static fn (mixed $input): mixed =>
        array_reduce($fns, static fn (mixed $acc, callable $fn): mixed => $fn($acc), $input);
}

$slug = pipe(
    $normalize,
    fn (string $s) => preg_replace('/[^a-z0-9]+/', '-', $s),
    fn (string $s) => trim($s, '-'),
);
echo $slug('  Hello PHP World! '), PHP_EOL; // hello-php-world

// Metódusra is működik: $obj->method(...), Osztaly::statikus(...)
$format = (new DateTimeImmutable('2024-01-01'))->format(...);
echo $format('Y-m-d'), PHP_EOL;
```

## Generátorok
<!-- q: Hogyan dolgozzak fel nagy fájlt memóriatakarékosan generátorral PHP-ban? -->
<!-- tags: generator, yield, yield from, lazy, memory, iterator -->

A generátor (`yield`-et tartalmazó függvény) lusta iterátort ad: az értékek egyenként, igény szerint készülnek, így egy több GB-os CSV is állandó memóriával feldolgozható. A `yield $k => $v` kulcsot is ad, a `yield from` másik generátorra vagy tömbre delegál, a `send()` pedig értéket juttat vissza a generátorba (korutin-szerű használat). A `finally` blokk akkor is lefut, ha a hívó korán kilép a `foreach`-ből – ez garantálja a fájlzárást. Buktató: egy generátor csak egyszer járható be, és `yield from` után az `iterator_to_array()` alapból felülírja az ütköző kulcsokat (használj `false` második paramétert).

```php
<?php
declare(strict_types=1);

/** Nagy CSV soronként: a memóriaigény független a fájl méretétől. */
function readCsv(string $path): Generator
{
    $fh = fopen($path, 'rb') ?: throw new RuntimeException("Nem nyitható: $path");
    try {
        $header = fgetcsv($fh);
        $line = 1;
        while (($row = fgetcsv($fh)) !== false) {
            $line++;
            if (count($row) !== count($header)) {
                continue; // hibás sor kihagyása
            }
            yield $line => array_combine($header, $row); // kulcs = sorszám
        }
    } finally {
        fclose($fh); // korai kilépésnél (break) is lefut
    }
}

// Lusta pipeline-elemek: semmi nem fut, amíg valaki nem iterál
function filterRows(iterable $rows, callable $pred): Generator
{
    foreach ($rows as $k => $row) {
        if ($pred($row)) {
            yield $k => $row;
        }
    }
}

function take(iterable $rows, int $n): Generator
{
    if ($n <= 0) {
        return;
    }
    foreach ($rows as $k => $row) {
        yield $k => $row;
        if (--$n === 0) {
            return; // a forrás generátor finally-ja is lefut
        }
    }
}

if (is_file('orders.csv')) {
    $big = filterRows(readCsv('orders.csv'), fn (array $r) => (float) $r['total'] > 10000);
    foreach (take($big, 5) as $line => $row) {
        echo "$line. sor: {$row['id']}\n";
    }
}

// send(): kétirányú kommunikáció – futó átlag korutinként
function runningAverage(): Generator
{
    $sum = 0;
    $n = 0;
    $avg = null;
    while (true) {
        $value = yield $avg; // a yield kifejezés értéke a send()-del küldött adat
        $sum += $value;
        $n++;
        $avg = $sum / $n;
    }
}

$avg = runningAverage();
$avg->current();              // elindítja az első yield-ig
$avg->send(10);
echo $avg->send(20), PHP_EOL; // 15
```

## Trait-ek
<!-- q: Mire jók a trait-ek PHP-ban és hogyan oldjam fel a névütközést? -->
<!-- tags: trait, mixin, insteadof, code reuse, horizontal reuse -->

A trait "vízszintes" kódújrahasznosítás: metódusokat és property-ket másol be a fordító az osztályba, öröklés nélkül. Több trait is használható egyszerre; névütközésnél `insteadof`-fal választunk és `as`-szal aliasolunk (akár láthatóságot is váltva). A trait deklarálhat absztrakt metódust, amit a felhasználó osztálynak kötelező megvalósítania, és a statikus property-jéből minden használó osztály saját példányt kap. Buktató: a túl sok trait rejtett függőségeket és nehezen követhető kódot ad – ha a viselkedésnek saját állapota és szerződése van, inkább kompozíció (külön objektum) a jobb.

```php
<?php
declare(strict_types=1);

trait Timestamps
{
    private ?DateTimeImmutable $createdAt = null;
    private ?DateTimeImmutable $updatedAt = null;

    public function touch(): void
    {
        $now = new DateTimeImmutable();
        $this->createdAt ??= $now;   // csak először állítjuk
        $this->updatedAt = $now;
    }

    public function describe(): string
    {
        return 'módosítva: ' . ($this->updatedAt?->format(DATE_ATOM) ?? 'soha');
    }
}

trait SoftDeletes
{
    private ?DateTimeImmutable $deletedAt = null;

    // Statikus property: minden használó osztálynak saját példánya van
    public static int $instances = 0;

    // Absztrakt metódus a traitben: a használó osztálynak KÖTELEZŐ megvalósítani
    abstract protected function canBeDeleted(): bool;

    public function delete(): void
    {
        if (!$this->canBeDeleted()) {
            throw new LogicException(static::class . ' nem törölhető');
        }
        $this->deletedAt = new DateTimeImmutable();
    }

    public function describe(): string
    {
        return $this->deletedAt !== null ? 'törölve' : 'aktív';
    }
}

final class Article
{
    // Névütközés feloldása: insteadof választ, as aliasol (itt protected láthatósággal)
    use Timestamps, SoftDeletes {
        SoftDeletes::describe insteadof Timestamps;
        Timestamps::describe as protected timestampInfo;
    }

    public function __construct(public string $title, private bool $published = false)
    {
        self::$instances++;
        $this->touch();
    }

    protected function canBeDeleted(): bool
    {
        return !$this->published;
    }

    public function summary(): string
    {
        return "{$this->title} – {$this->describe()}, {$this->timestampInfo()}";
    }
}

$a = new Article('Trait-ek PHP-ban');
$a->delete();
echo $a->summary(), PHP_EOL;
```

## Interfészek és absztrakt osztályok
<!-- q: Mikor használjak interfészt és mikor absztrakt osztályt PHP-ban? -->
<!-- tags: interface, abstract class, template method, polymorphism, contract -->

Az interfész tiszta szerződés (MIT tud egy objektum): csak metódus-szignatúrákat és konstansokat tartalmaz, és egy osztály több interfészt is implementálhat. Az absztrakt osztály közös *implementációt* is ad, de csak egyből lehet örökölni – tipikus használata a template method minta, ahol a lépések sorrendje rögzített (`final`), a részleteket pedig a leszármazott tölti ki. Ökölszabály: a függőségeket mindig interfészre típusozd (cserélhetőség, tesztelhetőség), az absztrakt osztály legyen belső implementációs segéd. A titkok összehasonlítására mindig `hash_equals` kell, hogy időzítéses támadással ne lehessen kitalálni őket.

```php
<?php
declare(strict_types=1);

interface PaymentGateway
{
    public const TIMEOUT_SECONDS = 10;

    public function charge(int $amountCents, string $token): PaymentResult;
    public function refund(string $transactionId): bool;
}

interface SupportsWebhooks
{
    public function verifySignature(string $payload, string $signature): bool;
}

final class PaymentResult
{
    public function __construct(
        public readonly bool $ok,
        public readonly string $transactionId,
        public readonly ?string $error = null,
    ) {}
}

// Absztrakt osztály: közös logika + template method
abstract class AbstractGateway implements PaymentGateway
{
    public function __construct(protected readonly string $secret) {}

    // A lépések sorrendje rögzített, a leszármazott nem írhatja felül
    final public function charge(int $amountCents, string $token): PaymentResult
    {
        if ($amountCents <= 0) {
            return new PaymentResult(false, '', 'Az összegnek pozitívnak kell lennie');
        }
        try {
            return new PaymentResult(true, $this->doCharge($amountCents, $token));
        } catch (RuntimeException $e) {
            error_log(static::class . ': ' . $e->getMessage());
            return new PaymentResult(false, '', $e->getMessage());
        }
    }

    abstract protected function doCharge(int $amountCents, string $token): string;
}

final class FakeGateway extends AbstractGateway implements SupportsWebhooks
{
    protected function doCharge(int $amountCents, string $token): string
    {
        if ($token === 'tok_declined') {
            throw new RuntimeException('Kártya elutasítva');
        }
        return 'txn_' . bin2hex(random_bytes(6));
    }

    public function refund(string $transactionId): bool
    {
        return str_starts_with($transactionId, 'txn_');
    }

    public function verifySignature(string $payload, string $signature): bool
    {
        // hash_equals: konstans idejű összehasonlítás (timing attack ellen)
        return hash_equals(hash_hmac('sha256', $payload, $this->secret), $signature);
    }
}

$gw  = new FakeGateway('test-secret');
$res = $gw->charge(4990, 'tok_visa');
echo $res->ok ? "OK {$res->transactionId}" : "Hiba: {$res->error}", PHP_EOL;
```

## Névterek, Composer és PSR-4 autoload
<!-- q: Hogyan szervezzem a PHP projektet névterekkel és Composer autoloaddal? -->
<!-- tags: namespace, composer, psr-4, autoload, dependencies, vendor -->

A névtér (`namespace App\Order\Service;`) megelőzi a névütközést, a PSR-4 szabvány pedig a névteret mappaszerkezetre képezi le (`App\` → `src/`), így a Composer autoloadere `require` nélkül, az első használatkor tölti be az osztályokat. A függőségeket a `composer.json` írja le, a pontos verziókat a `composer.lock` rögzíti – ezt mindig commitold, és élesben `composer install --no-dev --optimize-autoloader`-rel telepíts. A `use function`/`use const` globális függvényt/konstanst importál, ami kicsit gyorsabb feloldást ad. Buktató: a mappa- és fájlnevek kis-nagybetűje Linuxon számít, Windowson nem – emiatt a "nálam működik" hibák gyakoriak.

```json
{
    "name": "acme/shop",
    "type": "project",
    "require": {
        "php": "^8.2",
        "psr/log": "^3.0"
    },
    "require-dev": {
        "phpunit/phpunit": "^11.0"
    },
    "autoload": {
        "psr-4": { "App\\": "src/" }
    },
    "autoload-dev": {
        "psr-4": { "Tests\\": "tests/" }
    },
    "config": { "optimize-autoloader": true, "sort-packages": true }
}
```

```php
<?php
// src/Order/Service/InvoiceService.php -> App\Order\Service\InvoiceService (PSR-4)
declare(strict_types=1);

namespace App\Order\Service;

use App\Order\Entity\Order;   // osztály import (src/Order/Entity/Order.php)
use Psr\Log\LoggerInterface;   // vendor csomagból
use function sprintf;          // globális függvény import: nincs névtér-fallback keresés

final class InvoiceService
{
    public function __construct(private LoggerInterface $logger) {}

    public function numberFor(Order $order): string
    {
        $no = sprintf('INV-%s-%06d', $order->createdAt->format('Y'), $order->id);
        $this->logger->info('Számla sorszám generálva', ['no' => $no]);
        return $no;
    }
}
```

```php
<?php
// public/index.php – az egyetlen belépési pont; innentől minden osztály autoloadolt
declare(strict_types=1);

require __DIR__ . '/../vendor/autoload.php';

// Parancsok: composer require psr/log | composer dump-autoload -o | composer install --no-dev
```

## PDO prepared statement és tranzakciók
<!-- q: Hogyan használjam biztonságosan a PDO-t prepared statementtel és tranzakcióval? -->
<!-- tags: pdo, prepared statement, transaction, sql injection, mysql, for update -->

A PDO egységes adatbázis-API; a prepared statement elválasztja az SQL szerkezetét az adatoktól, így az SQL injection strukturálisan kizárt. Mindig állítsd be az `ERRMODE_EXCEPTION`-t (különben a hibák csendben `false`-t adnak) és kapcsold ki az emulált prepare-t. Több összetartozó módosítást tranzakcióba kell tenni: hibánál `rollBack()`, sikernél `commit()`; a `SELECT ... FOR UPDATE` sorzárat tesz, ami párhuzamos kéréseknél megakadályozza a versenyhelyzetet. Buktató: `IN (...)` listát, tábla- és oszlopnevet nem lehet egyetlen placeholderrel paraméterezni – a listához generált placeholderek, a nevekhez whitelist kell.

```php
<?php
declare(strict_types=1);

function connect(): PDO
{
    // A kapcsolati adatok környezeti változóból jönnek, soha nem a kódból
    $dsn = getenv('DB_DSN') ?: 'mysql:host=127.0.0.1;dbname=shop;charset=utf8mb4';
    return new PDO($dsn, getenv('DB_USER') ?: 'app', getenv('DB_PASS') ?: '', [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION, // hibánál kivétel
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES   => false,                  // valódi szerveroldali prepare
    ]);
}

/** Pénzátutalás két számla között atomikusan. */
function transfer(PDO $pdo, int $fromId, int $toId, int $cents): void
{
    $pdo->beginTransaction();
    try {
        // FOR UPDATE: sorzár a tranzakció végéig -> két párhuzamos utalás nem fut össze
        $stmt = $pdo->prepare('SELECT balance FROM accounts WHERE id = :id FOR UPDATE');
        $stmt->execute(['id' => $fromId]);
        $balance = $stmt->fetchColumn();

        if ($balance === false) {
            throw new RuntimeException('Nincs ilyen számla');
        }
        if ((int) $balance < $cents) {
            throw new RuntimeException('Nincs elég fedezet');
        }

        $upd = $pdo->prepare('UPDATE accounts SET balance = balance + :delta WHERE id = :id');
        $upd->execute(['delta' => -$cents, 'id' => $fromId]); // a statement újrahasznosítható
        $upd->execute(['delta' => $cents, 'id' => $toId]);

        $pdo->prepare('INSERT INTO transfers (from_id, to_id, amount) VALUES (?, ?, ?)')
            ->execute([$fromId, $toId, $cents]);

        $pdo->commit();
    } catch (Throwable $e) {
        if ($pdo->inTransaction()) {
            $pdo->rollBack(); // minden módosítás visszavonva
        }
        throw $e; // a hívó dönti el, mit lát a felhasználó
    }
}

// IN (...) lista biztonságosan: annyi placeholder, ahány elem
function findByIds(PDO $pdo, array $ids): array
{
    if ($ids === []) {
        return [];
    }
    $placeholders = implode(',', array_fill(0, count($ids), '?'));
    $stmt = $pdo->prepare("SELECT id, name FROM products WHERE id IN ($placeholders)");
    $stmt->execute(array_map('intval', array_values($ids)));
    return $stmt->fetchAll();
}
```

## Session-kezelés és jelszó-hash
<!-- q: Hogyan kezeljem biztonságosan a bejelentkezést, sessiont és jelszavakat PHP-ban? -->
<!-- tags: session, password_hash, password_verify, login, bcrypt, session fixation -->

Jelszót soha ne tárolj nyíltan vagy gyors hash-sel (md5/sha1): a `password_hash()` lassú, sózott algoritmust (bcrypt, opcionálisan Argon2id) használ, és a sót, a költséget is a hash-be írja; ellenőrzéshez a `password_verify()` kell, a `password_needs_rehash()` pedig belépéskor észrevétlenül frissíti a régi hash-eket. A session cookie legyen `Secure`, `HttpOnly` és `SameSite`, a `session.use_strict_mode` pedig tiltsa az ismeretlen session ID-t. Bejelentkezés után kötelező a `session_regenerate_id(true)` – enélkül session fixation támadás lehetséges. Buktató: a cookie-paramétereket a `session_start()` *előtt* kell beállítani.

```php
<?php
declare(strict_types=1);

// Biztonságos session cookie – a session_start() ELŐTT
session_set_cookie_params([
    'lifetime' => 0,         // böngésző bezárásáig
    'path'     => '/',
    'secure'   => true,      // csak HTTPS-en
    'httponly' => true,      // JavaScript nem éri el -> XSS-sel nem lopható
    'samesite' => 'Lax',     // alap CSRF-védelem
]);
ini_set('session.use_strict_mode', '1'); // ismeretlen session ID elutasítása
session_start();

function register(PDO $pdo, string $email, string $password): void
{
    if (mb_strlen($password) < 12) {
        throw new InvalidArgumentException('A jelszó legyen legalább 12 karakter');
    }
    // PASSWORD_DEFAULT jelenleg bcrypt; a só és a költség a hash része
    $hash = password_hash($password, PASSWORD_DEFAULT);
    $pdo->prepare('INSERT INTO users (email, password_hash) VALUES (?, ?)')
        ->execute([mb_strtolower($email), $hash]);
}

function login(PDO $pdo, string $email, string $password): bool
{
    $stmt = $pdo->prepare('SELECT id, password_hash FROM users WHERE email = ?');
    $stmt->execute([mb_strtolower($email)]);
    $user = $stmt->fetch(PDO::FETCH_ASSOC);

    // Nem létező usernél is számolunk hash-t, hogy a válaszidő ne árulja el a fiók létezését
    $hash = $user['password_hash'] ?? '$2y$12$' . str_repeat('a', 53);
    if (!password_verify($password, $hash) || $user === false) {
        return false;
    }

    // Algoritmus- vagy költségváltásnál újrahash-elés belépéskor
    if (password_needs_rehash($user['password_hash'], PASSWORD_DEFAULT)) {
        $pdo->prepare('UPDATE users SET password_hash = ? WHERE id = ?')
            ->execute([password_hash($password, PASSWORD_DEFAULT), $user['id']]);
    }

    session_regenerate_id(true); // új session ID (fixation ellen), a régi törlődik
    $_SESSION['user_id']  = (int) $user['id'];
    $_SESSION['login_at'] = time();
    return true;
}

function logout(): void
{
    $_SESSION = [];
    if (ini_get('session.use_cookies')) {
        $p = session_get_cookie_params();
        setcookie(session_name(), '', time() - 42000, $p['path'], $p['domain'], $p['secure'], $p['httponly']);
    }
    session_destroy();
}
```

## CSRF, XSS és SQL injection elleni védekezés
<!-- q: Hogyan védekezzek CSRF, XSS és SQL injection ellen PHP-ban? -->
<!-- tags: security, csrf, xss, sql injection, htmlspecialchars, owasp, csp -->

XSS ellen a kimenetet a *kontextusnak megfelelően* kell escape-elni: HTML-be `htmlspecialchars(..., ENT_QUOTES)`, JavaScriptbe `json_encode` a HEX flagekkel, URL-be `rawurlencode`; kiegészítésként egy szigorú Content-Security-Policy fejléc korlátozza a futtatható szkripteket. CSRF ellen minden állapotmódosító kéréshez (POST/PUT/DELETE) sessionhöz kötött, véletlen tokent kell kérni és `hash_equals`-szal ellenőrizni. SQL injection ellen kizárólag prepared statement, és amit nem lehet paraméterezni (ORDER BY, oszlopnév), azt whitelistből kell választani. Buktató: a bemenet "szűrése" (strip_tags) nem helyettesíti a kimeneti escape-elést.

```php
<?php
declare(strict_types=1);

session_start();
header("Content-Security-Policy: default-src 'self'; object-src 'none'; base-uri 'self'");

// XSS: HTML-kontextus escape (attribútumban is biztonságos az ENT_QUOTES miatt)
function e(?string $value): string
{
    return htmlspecialchars($value ?? '', ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

// JS-kontextus: json_encode a megfelelő flagekkel, NEM htmlspecialchars
function jsValue(mixed $v): string
{
    return json_encode($v, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_THROW_ON_ERROR);
}

// CSRF: szinkronizált token minta
function csrfToken(): string
{
    return $_SESSION['csrf'] ??= bin2hex(random_bytes(32));
}

function verifyCsrf(): void
{
    $sent = $_POST['_csrf'] ?? $_SERVER['HTTP_X_CSRF_TOKEN'] ?? '';
    if (!is_string($sent) || !hash_equals($_SESSION['csrf'] ?? '', $sent)) {
        http_response_code(419);
        exit('Érvénytelen CSRF token');
    }
}

// SQL injection: értékek paraméterként, azonosítók whitelistből
function listProducts(PDO $pdo, string $search, string $sort): array
{
    $allowedSort = ['name' => 'name', 'price' => 'price', 'newest' => 'created_at DESC'];
    $orderBy = $allowedSort[$sort] ?? 'name'; // ORDER BY nem paraméterezhető

    $stmt = $pdo->prepare("SELECT id, name, price FROM products WHERE name LIKE :q ORDER BY $orderBy LIMIT 50");
    // A LIKE wildcardjait (% és _) escape-eljük, hogy szó szerint értődjenek
    $stmt->execute(['q' => '%' . addcslashes($search, '%_\\') . '%']);
    return $stmt->fetchAll(PDO::FETCH_ASSOC);
}

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
    verifyCsrf();
    // ... állapotmódosító művelet
}
$name = (string) ($_GET['name'] ?? '');
?>
<form method="post">
    <input type="hidden" name="_csrf" value="<?= e(csrfToken()) ?>">
    <input name="comment" value="<?= e($name) ?>">
    <button>Küldés</button>
</form>
<script>
    const initialName = <?= jsValue($name) ?>; // biztonságos JS literál
</script>
```

## Laravel: Eloquent modellek és migrációk
<!-- q: Hogyan írjak Laravel migrációt és Eloquent modellt kapcsolatokkal? -->
<!-- tags: laravel, eloquent, orm, migration, relationships, eager loading, casts -->

A migráció verziókezelt sémaváltozás (`up`/`down`), amit `php artisan migrate` futtat; csapatban így mindenki ugyanazt az adatbázis-szerkezetet kapja. Az Eloquent Active Record ORM: a modell egy táblát, a példány egy sort képvisel, a kapcsolatokat metódusok írják le (`belongsTo`, `hasMany`, `belongsToMany`). A `$fillable` véd a mass assignment ellen, a `casts()` típusokat (enum, dátum, JSON) konvertál, a lokális scope-ok újrahasznosítható lekérdezésrészek. Buktató: a kapcsolatok lusta betöltése ciklusban N+1 lekérdezést okoz – mindig `with()`-szel töltsd előre, fejlesztésben pedig a `Model::preventLazyLoading()` azonnal jelzi a hibát.

```php
<?php
// database/migrations/2024_05_01_000000_create_orders_table.php
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('orders', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete(); // FK + index
            $table->string('status', 20)->default('pending')->index();
            $table->unsignedInteger('total_cents');
            $table->timestamps();
            $table->softDeletes();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('orders');
    }
};
```

```php
<?php
namespace App\Models;

use App\Enums\OrderStatus;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\SoftDeletes;

class Order extends Model
{
    use SoftDeletes;

    // Mass assignment védelem: csak ezek tölthetők create()/fill()-lel
    protected $fillable = ['user_id', 'status', 'total_cents'];

    // Cast: a status automatikusan enum, a total_cents int
    protected function casts(): array
    {
        return ['status' => OrderStatus::class, 'total_cents' => 'integer'];
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function items(): HasMany
    {
        return $this->hasMany(OrderItem::class);
    }

    // Lokális scope: Order::paid()->get()
    public function scopePaid(Builder $query): void
    {
        $query->where('status', OrderStatus::Paid);
    }
}

// Használat controllerben – eager loading: 3 lekérdezés 1+N helyett
// $orders = Order::paid()->with(['user', 'items'])->withSum('items', 'price_cents')->latest()->paginate(20);
```

## Laravel: queue-k és middleware
<!-- q: Hogyan futtassak háttérfeladatot queue-val és írjak middleware-t Laravelben? -->
<!-- tags: laravel, queue, job, middleware, retry, backoff, http -->

A queue-ba tett job (`ShouldQueue`) a HTTP kéréstől függetlenül, egy `queue:work` workerben fut – lassú műveletekre (e-mail, PDF, külső API) ez tartja gyorsan a válaszidőt. A `$tries`, `backoff()` és `failed()` az újrapróbálást és a végső hibakezelést szabályozza, a `SerializesModels` pedig csak a modell ID-ját teszi a sorba. A middleware a kérés–válasz lánc egy rétege: a `$next($request)` előtti kód előfeldolgoz, az utána következő utófeldolgoz. Buktató: a jobnak idempotensnek kell lennie (többször is lefuthat), és tranzakcióban indítva használd az `afterCommit()`-ot, különben a worker még nem látja az új sort.

```php
<?php
namespace App\Jobs;

use App\Models\Order;
use App\Services\InvoiceGenerator;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\Middleware\WithoutOverlapping;
use Illuminate\Queue\SerializesModels;
use Throwable;

class GenerateInvoice implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public int $tries = 5;     // max próbálkozás
    public int $timeout = 120; // másodperc

    public function __construct(public Order $order) {}

    public function backoff(): array
    {
        return [10, 60, 300]; // növekvő várakozás az újrapróbálások között
    }

    public function middleware(): array
    {
        // Ugyanarra a rendelésre egyszerre csak egy job fusson
        return [(new WithoutOverlapping($this->order->id))->expireAfter(180)];
    }

    // A handle() paramétereit a service container injektálja
    public function handle(InvoiceGenerator $generator): void
    {
        $generator->generate($this->order); // idempotens legyen: újrafutáskor ne duplikáljon
    }

    public function failed(Throwable $e): void
    {
        logger()->error('Számlagenerálás végleg sikertelen', ['order' => $this->order->id, 'err' => $e->getMessage()]);
    }
}

// Indítás: GenerateInvoice::dispatch($order)->onQueue('invoices')->afterCommit();
// Worker:  php artisan queue:work --queue=invoices,default
```

```php
<?php
namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class EnsureApiVersion
{
    // Paraméteres middleware a route-on: ->middleware(EnsureApiVersion::class . ':2')
    public function handle(Request $request, Closure $next, string $min = '1'): Response
    {
        $version = (int) $request->header('X-Api-Version', '1');
        if ($version < (int) $min) {
            return response()->json(['error' => "Minimum API verzió: $min"], 426);
        }
        $response = $next($request);                                   // a lánc többi része
        $response->headers->set('X-Api-Version', (string) $version);   // utófeldolgozás
        return $response;
    }
}
```

## Symfony Dependency Injection
<!-- q: Hogyan működik a Symfony service container és az autowiring? -->
<!-- tags: symfony, dependency injection, autowiring, service container, tagged services -->

A Symfony DI container a szolgáltatásokat (osztálypéldányokat) központilag hozza létre és köti össze: autowiringnál a konstruktor típusai alapján injektál, autoconfigure-nál az interfészek/attribútumok alapján taggel. Skalár paramétereket (`%kernel.project_dir%`, környezeti változó) az `#[Autowire]` attribútummal adunk, egy tag összes szolgáltatását pedig `#[AutowireIterator]`-ral kapjuk lusta iterátorként – ez a stratégia minta tiszta megvalósítása. A container fordításkor PHP kóddá generálódik, így futásidőben gyors. Buktató: a szolgáltatások alapból privátok és megosztottak (singleton) – állapotot tároló szolgáltatásnál ez kérések közötti szivárgást okozhat hosszan futó workerekben.

```php
<?php
namespace App\Report;

use App\Repository\OrderRepository;
use Psr\Log\LoggerInterface;
use Symfony\Component\DependencyInjection\Attribute\AutoconfigureTag;
use Symfony\Component\DependencyInjection\Attribute\Autowire;
use Symfony\Component\DependencyInjection\Attribute\AutowireIterator;

// Minden implementáció automatikusan megkapja az 'app.report_formatter' taget
#[AutoconfigureTag('app.report_formatter')]
interface ReportFormatter
{
    public function supports(string $format): bool;
    public function format(array $rows): string;
}

final class JsonFormatter implements ReportFormatter
{
    public function supports(string $format): bool { return $format === 'json'; }
    public function format(array $rows): string { return json_encode($rows, JSON_THROW_ON_ERROR); }
}

final class CsvFormatter implements ReportFormatter
{
    public function supports(string $format): bool { return $format === 'csv'; }

    public function format(array $rows): string
    {
        $fh = fopen('php://temp', 'r+');
        foreach ($rows as $row) {
            fputcsv($fh, $row);
        }
        rewind($fh);
        return stream_get_contents($fh);
    }
}

final class ReportService
{
    /** @param iterable<ReportFormatter> $formatters */
    public function __construct(
        private readonly OrderRepository $orders,   // autowiring típus alapján
        private readonly LoggerInterface $logger,
        #[AutowireIterator('app.report_formatter')] private readonly iterable $formatters,
        #[Autowire('%kernel.project_dir%/var/reports')] private readonly string $outputDir,
        #[Autowire(env: 'int:REPORT_MAX_ROWS')] private readonly int $maxRows,
    ) {}

    public function export(string $format): string
    {
        foreach ($this->formatters as $formatter) { // lusta: csak a bejárt szolgáltatás példányosodik
            if ($formatter->supports($format)) {
                $rows = array_slice($this->orders->findForReport(), 0, $this->maxRows);
                $path = sprintf('%s/report_%s.%s', $this->outputDir, date('Ymd_His'), $format);
                file_put_contents($path, $formatter->format($rows));
                $this->logger->info('Riport elkészült', ['path' => $path]);
                return $path;
            }
        }
        throw new \InvalidArgumentException("Nem támogatott formátum: $format");
    }
}
```

```yaml
# config/services.yaml – alapértelmezett, attribútum-alapú konfiguráció
services:
    _defaults:
        autowire: true        # konstruktor-típusok alapján injektál
        autoconfigure: true   # interfészek/attribútumok alapján taggel
    App\:
        resource: '../src/'
        exclude: '../src/{Entity,Kernel.php}'
```

## Unit tesztelés PHPUnit-tal
<!-- q: Hogyan írjak unit tesztet PHPUnit-tal data providerrel és mockkal? -->
<!-- tags: phpunit, testing, unit test, mock, data provider, tdd -->

A PHPUnit a PHP szabványos tesztkerete; a tesztosztály a `TestCase`-ből örököl, a `setUp()` minden teszt előtt friss állapotot épít, így a tesztek függetlenek. A PHPUnit 10+ attribútumokat használ (`#[Test]`, `#[DataProvider]`, `#[CoversClass]`) a régi docblock-annotációk helyett; a data provider nevesített esetei hibánál olvasható üzenetet adnak. Mockkal a külső függőséget (adatbázis, API) helyettesítjük és a hívásokat is ellenőrizzük. Buktató: ne mockolj túl – az érték-objektumokat és a saját egyszerű osztályokat valódi példánnyal teszteld, különben a teszt az implementációt rögzíti, nem a viselkedést.

```php
<?php
declare(strict_types=1);

namespace Tests\Unit;

use App\Billing\CouponRepository;
use App\Billing\DiscountCalculator;
use InvalidArgumentException;
use PHPUnit\Framework\Attributes\CoversClass;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\Attributes\Test;
use PHPUnit\Framework\MockObject\MockObject;
use PHPUnit\Framework\TestCase;

#[CoversClass(DiscountCalculator::class)]
final class DiscountCalculatorTest extends TestCase
{
    private CouponRepository&MockObject $coupons; // intersection típus
    private DiscountCalculator $calc;

    protected function setUp(): void
    {
        // Minden teszt előtt friss példány -> nincs közös állapot
        $this->coupons = $this->createMock(CouponRepository::class);
        $this->calc = new DiscountCalculator($this->coupons);
    }

    public static function totals(): iterable
    {
        // Nevesített esetek: hibánál a név jelenik meg
        yield 'nincs kedvezmény 10 000 alatt' => [9_999, 0];
        yield 'pont a határértéken'           => [10_000, 500];
        yield 'nagy kosár'                    => [100_000, 10_000];
    }

    #[Test]
    #[DataProvider('totals')]
    public function itAppliesTieredDiscount(int $total, int $expected): void
    {
        self::assertSame($expected, $this->calc->tiered($total));
    }

    #[Test]
    public function itUsesCouponFromRepository(): void
    {
        $this->coupons->expects(self::once()) // pontosan egyszer kell hívni
            ->method('percentFor')
            ->with('NYAR10')
            ->willReturn(10);

        self::assertSame(1_000, $this->calc->withCoupon(10_000, 'NYAR10'));
    }

    #[Test]
    public function itRejectsNegativeTotals(): void
    {
        $this->expectException(InvalidArgumentException::class);
        $this->expectExceptionMessage('negatív');
        $this->calc->tiered(-1);
    }
}

// Futtatás: vendor/bin/phpunit --testdox   |   lefedettség: XDEBUG_MODE=coverage vendor/bin/phpunit --coverage-html cov
```

## OPcache, preloading és JIT
<!-- q: Hogyan gyorsítsam a PHP-t OPcache-sel, preloadinggal és JIT-tel? -->
<!-- tags: opcache, jit, preload, performance, php.ini, production -->

Az OPcache a lefordított bytecode-ot osztott memóriában tartja, így a fájlokat nem kell minden kérésnél újra parse-olni – élesben kötelező, és gyakran 2–3× gyorsulást ad. `validate_timestamps=0` mellett a fájlváltozást nem figyeli, ezért deploy után FPM reload vagy `opcache_reset()` kell. A preloading (PHP 7.4+) a szerver indulásakor egyszer betölti a keretrendszer osztályait; a JIT (PHP 8+) gépi kódra fordít, ami CPU-intenzív kódnál (számítás, képfeldolgozás) sokat hoz, tipikus I/O-kötött webappnál keveset. Buktató: túl kicsi `memory_consumption` vagy `max_accelerated_files` esetén a cache betelik, és csendben lassul a rendszer – figyeld a hit rate-et.

```ini
; php.ini – éles beállítások
opcache.enable=1
opcache.memory_consumption=256
opcache.interned_strings_buffer=32
opcache.max_accelerated_files=50000
; fájlváltozás figyelése kikapcsolva: deploy után FPM reload kell
opcache.validate_timestamps=0
opcache.preload=/var/www/app/preload.php
opcache.preload_user=www-data
; JIT: CPU-intenzív kódnál segít
opcache.jit=tracing
opcache.jit_buffer_size=64M
```

```php
<?php
// preload.php – a szerver indulásakor EGYSZER fut; az osztályok a shared memoryban maradnak
declare(strict_types=1);

$it = new RecursiveIteratorIterator(
    new RecursiveDirectoryIterator(__DIR__ . '/src', FilesystemIterator::SKIP_DOTS)
);

foreach ($it as $file) {
    if ($file->getExtension() === 'php') {
        // Lefordítja, de nem futtatja -> nincs mellékhatás
        opcache_compile_file($file->getPathname());
    }
}

// Diagnosztika (pl. védett admin endpointon): találati arány, memória, JIT állapot
function opcacheReport(): array
{
    $status = opcache_get_status(false);
    if ($status === false) {
        return ['enabled' => false];
    }
    $stats = $status['opcache_statistics'];
    return [
        'enabled'   => true,
        'hit_rate'  => round($stats['opcache_hit_rate'], 2),
        'scripts'   => $stats['num_cached_scripts'],
        'free_mem'  => $status['memory_usage']['free_memory'],
        'jit_on'    => (bool) ($status['jit']['on'] ?? false),
        'restarts'  => $stats['oom_restarts'], // ha nő: kevés a memória
    ];
}
```

## Fiberek és kooperatív konkurencia
<!-- q: Mik azok a Fiberek PHP 8.1-ben és hogyan írjak velük ütemezőt? -->
<!-- tags: fiber, concurrency, coroutine, async, scheduler, php 8.1 -->

A Fiber (PHP 8.1) saját veremmel futó, megszakítható végrehajtási egység: a `Fiber::suspend()` bárhonnan – akár mélyen beágyazott hívásból is – felfüggeszti, a `resume()` folytatja, és értékeket adhatnak át egymásnak. Ez kooperatív konkurencia egyetlen szálon: nincs valódi párhuzamosság, de az I/O-várakozások átfedhetők. A Fiberekre épülnek az aszinkron könyvtárak (Revolt event loop, AMPHP v3, ReactPHP), amelyekkel a kód szinkron kinézetű marad (nincs "callback hell" vagy `yield`-láncolás). Buktató: egy blokkoló hívás (pl. sima `sleep()` vagy PDO lekérdezés) az egész ütemezőt megállítja – csak nem blokkoló I/O-val van értelme.

```php
<?php
declare(strict_types=1);

/** Minimális kooperatív ütemező: a taskok Fiber::suspend()-del "alszanak". */
final class Scheduler
{
    private SplQueue $ready;
    /** @var list<array{Fiber, float}> alvó fiberek ébredési idővel */
    private array $sleeping = [];

    public function __construct()
    {
        $this->ready = new SplQueue();
    }

    public function spawn(callable $task): void
    {
        $this->ready->enqueue(new Fiber($task));
    }

    // A taskokból hívható: alvás a folyamat blokkolása nélkül
    public static function sleep(float $seconds): void
    {
        Fiber::suspend(['sleep', $seconds]);
    }

    public function run(): void
    {
        while (!$this->ready->isEmpty() || $this->sleeping !== []) {
            $now = microtime(true);
            foreach ($this->sleeping as $i => [$fiber, $wakeAt]) {
                if ($wakeAt <= $now) {
                    $this->ready->enqueue($fiber);
                    unset($this->sleeping[$i]);
                }
            }
            if ($this->ready->isEmpty()) {
                usleep(1000); // nincs futtatható task
                continue;
            }
            $fiber = $this->ready->dequeue();
            // Első indítás start(), utána resume(); a visszakapott érték a suspend() argumentuma
            $signal = $fiber->isStarted() ? $fiber->resume() : $fiber->start();
            if ($fiber->isTerminated()) {
                continue;
            }
            if (is_array($signal) && $signal[0] === 'sleep') {
                $this->sleeping[] = [$fiber, microtime(true) + $signal[1]];
            } else {
                $this->ready->enqueue($fiber);
            }
        }
    }
}

$s = new Scheduler();
foreach (['A' => 0.03, 'B' => 0.01] as $name => $delay) {
    $s->spawn(function () use ($name, $delay): void {
        for ($i = 1; $i <= 3; $i++) {
            Scheduler::sleep($delay);
            echo "$name lépés $i\n";
        }
    });
}
$s->run(); // B gyorsabban lép, a kimenet összefésülődik – egyetlen szálon
```
