# Rust
<!-- tech: rust -->
<!-- aliases: rustlang, cargo, rs -->

A Rust egy natívra fordított, statikusan és erősen típusos rendszerprogramozási nyelv, amely szemétgyűjtő nélkül garantál memóriabiztonságot: az ownership (tulajdonjog) és a borrow checker fordítási időben zárja ki a lógó pointert, a double free-t és a data race-t. A „zero-cost abstraction” elv miatt az iterátorok, generikusok és traitek C/C++-szintű teljesítményre fordulnak, a `cargo` pedig egységes build-, függőség- és tesztkezelést ad. CLI-eszközök, hálózati szolgáltatások, böngészőmotor-részek, beágyazott rendszerek, WebAssembly és OS-komponensek nyelve. Hátránya a meredek tanulási görbe (élettartamok, borrow-szabályok) és a viszonylag lassú fordítás; gyors prototípushoz egy GC-s nyelv kényelmesebb lehet.

## Ownership és move szemantika
<!-- q: Hogyan működik az ownership (tulajdonjog) és a move Rustban? -->
<!-- tags: ownership, move, drop, copy, clone, raii, mem::take -->

Rustban minden értéknek pontosan egy tulajdonosa van; amikor a tulajdonos kikerül a scope-ból, az érték determinisztikusan felszabadul (`Drop`). Az értékadás és a paraméterátadás alapértelmezésben MOZGAT: a régi változó többé nem használható, és ezt a fordító ellenőrzi, így double free nem fordulhat elő. A kis, csak stacken élő típusok (`i32`, `f64`, `Copy` derive-val ellátott structok) bitenként másolódnak; a drága mélymásolat mindig explicit (`.clone()`). A `std::mem::take`/`replace` egy `&mut` mögül mozgat ki értéket úgy, hogy alapértéket hagy a helyén.

```rust
#[derive(Debug)]
struct Document {
    title: String,
    body: Vec<u8>,
}

impl Drop for Document {
    fn drop(&mut self) {
        println!("drop: {}", self.title);   // determinisztikus, RAII-szerű felszabadítás
    }
}

fn consume(doc: Document) -> usize {
    doc.body.len()                           // doc a függvény végén droppolódik
}

fn make(title: &str) -> Document {
    Document { title: title.to_string(), body: vec![0; 1024] }   // tulajdon a hívónak
}

#[derive(Debug, Clone, Copy, PartialEq)]
struct Point { x: f64, y: f64 }              // Copy: bitenkénti másolás

fn main() {
    let a = make("jelentes");
    let b = a;                               // MOVE: a innentől használhatatlan
    // println!("{:?}", a);                  // fordítási hiba: borrow of moved value `a`
    let size = consume(b);
    println!("meret: {size}");

    let p1 = Point { x: 1.0, y: 2.0 };
    let p2 = p1;                             // Copy: p1 továbbra is érvényes
    println!("{:?} {:?}", p1, p2);

    let s1 = String::from("megosztott");
    let s2 = s1.clone();                     // explicit mélymásolat
    println!("{s1} {s2}");

    let doc = make("reszleges");
    let Document { title, .. } = &doc;       // referencia-minta: nem mozgat
    println!("cim: {title}");

    let mut buf = vec![1, 2, 3];
    let taken = std::mem::take(&mut buf);    // kimozgatás, a helyén üres Vec marad
    println!("{:?} {:?}", taken, buf);
}   // itt droppolódik a "reszleges" dokumentum
```

## Borrowing: megosztott és kizárólagos referenciák
<!-- q: Mik a kölcsönzési (borrowing) szabályok Rustban, mi a különbség a & és a &mut között? -->
<!-- tags: borrowing, references, mutable reference, borrow checker, nll, split_at_mut, aliasing -->

A kölcsönzés tulajdonátadás nélküli hozzáférés: egyszerre VAGY tetszőleges számú `&T` (megosztott, csak olvasható), VAGY pontosan egy `&mut T` (kizárólagos) létezhet. Ez a „aliasing XOR mutability” szabály fordítási időben zárja ki a data race-t és az iterátor-invalidációt (pl. egy vektorba nem lehet push-olni, amíg egy elemére referencia él, mert az újraallokálás lógóvá tenné). A non-lexical lifetimes (NLL) miatt a kölcsönzés az utolsó használatig tart, nem a blokk végéig. Diszjunkt részek egyszerre is kölcsönözhetők kizárólagosan: külön struct-mezők vagy `split_at_mut`.

```rust
use std::collections::HashMap;

fn longest_word(text: &str) -> &str {
    text.split_whitespace().max_by_key(|w| w.len()).unwrap_or("")
}

fn add_bonus(scores: &mut HashMap<String, u32>, name: &str, bonus: u32) {
    // entry API: egyetlen keresés, nincs kettős kölcsönzés
    *scores.entry(name.to_string()).or_insert(0) += bonus;
}

struct Pair { a: Vec<i32>, b: Vec<i32> }

fn main() {
    let text = String::from("a rust kolcsonzesi szabalyai");
    println!("leghosszabb: {}", longest_word(&text));

    let mut scores: HashMap<String, u32> = HashMap::new();
    add_bonus(&mut scores, "anna", 10);
    add_bonus(&mut scores, "anna", 5);

    let mut v = vec![1, 2, 3];
    let first = &v[0];                 // megosztott kölcsönzés
    // v.push(4);                      // HIBA: &mut kellene, miközben first él
    println!("elso: {first}");         // first utolsó használata -> a kölcsönzés itt véget ér
    v.push(4);                         // most már rendben

    // Diszjunkt kizárólagos kölcsönzés
    let (left, right) = v.split_at_mut(2);
    left[0] += right[0];
    println!("{v:?}");

    // Két különböző mező egyszerre &mut-olható
    let mut p = Pair { a: vec![1], b: vec![2] };
    let (ra, rb) = (&mut p.a, &mut p.b);
    ra.extend(rb.iter());
    println!("{:?} {:?} {:?}", p.a, p.b, scores.get("anna"));
}
```

## Élettartamok (lifetimes)
<!-- q: Mik az élettartam-paraméterek Rustban és mikor kell kiírni őket? -->
<!-- tags: lifetimes, lifetime elision, 'static, borrow checker, dangling reference, struct with references -->

Az élettartam-paraméter (`'a`) nem változtatja meg, meddig él egy érték: csak leírja a fordítónak a referenciák közötti kapcsolatot, hogy lógó referencia ne jöhessen létre. Az elision-szabályok miatt a legtöbb esetben nem kell kiírni (egy bemeneti referencia, vagy `&self` metódus); több bemenet esetén viszont meg kell mondani, melyikhez kötődik a kimenet. Referenciát tároló struct nem élheti túl a forrását; ha a visszaadott slice a forráshoz és nem a `&mut self`-hez kötött, több token is tartható egyszerre. A `'static` a program teljes futására szól (string literálok, szivárogtatott adatok).

```rust
use std::fmt::Debug;

// A kimenet legfeljebb a RÖVIDEBB életű bemenetig érvényes
fn longer<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() >= b.len() { a } else { b }
}

// Referenciát tároló parser: nem élheti túl a forrás-stringet
struct Parser<'src> {
    input: &'src str,
    pos: usize,
}

impl<'src> Parser<'src> {
    fn new(input: &'src str) -> Self { Parser { input, pos: 0 } }

    // A token a forráshoz ('src) kötött, nem a &mut self-hez
    fn next_token(&mut self) -> Option<&'src str> {
        let rest = &self.input[self.pos..];
        let trimmed = rest.trim_start();
        if trimmed.is_empty() { return None; }
        let start = self.pos + (rest.len() - trimmed.len());
        let len = trimmed.find(char::is_whitespace).unwrap_or(trimmed.len());
        self.pos = start + len;
        Some(&self.input[start..start + len])
    }
}

fn first_line(s: &str) -> &str { s.lines().next().unwrap_or("") }   // elision

fn error_text(code: u16) -> &'static str {
    match code { 404 => "nem talalhato", 500 => "szerverhiba", _ => "ismeretlen" }
}

// Élettartam-korlát generikuson: T legalább 'a ideig érvényes
fn store<'a, T: Debug + 'a>(items: &mut Vec<Box<dyn Debug + 'a>>, x: T) {
    items.push(Box::new(x));
}

fn main() {
    let source = String::from("let x = 42 ;");
    let mut p = Parser::new(&source);
    let t1 = p.next_token();
    let t2 = p.next_token();
    println!("{:?} {:?}", t1, t2);           // mindkettő egyszerre érvényes

    let outer = String::from("hosszabb szoveg");
    {
        let inner = String::from("rovid");
        let result = longer(&outer, &inner);
        println!("{result}");                 // OK: inner még él
    }   // a result-ot itt már nem lehetne használni: inner megszűnt

    let mut boxed: Vec<Box<dyn Debug>> = Vec::new();
    store(&mut boxed, 5);
    println!("{} {} {:?}", first_line("a\nb"), error_text(404), boxed);
}
```

## Struct, impl, newtype és builder minta
<!-- q: Hogyan definiáljak structot metódusokkal, newtype-ot és builder mintát Rustban? -->
<!-- tags: struct, impl, methods, newtype, builder pattern, encapsulation, Display, Into -->

A struct adatot, az `impl` blokk viselkedést ad hozzá; a metódus első paramétere dönti el a hozzáférést: `&self` olvas, `&mut self` módosít, `self` elfogyasztja az objektumot. A newtype (`struct Port(u16)`) nulla költségű, típusbiztos burok, amivel validált értékek és invariánsok fejezhetők ki, és megkerülhető az orphan rule. A builder minta sok opcionális paramétert tesz olvashatóvá; a privát mezők garantálják, hogy érvénytelen objektum ne jöhessen létre. Az `impl Into<String>` paraméter kényelmes API-t ad `&str`-re és `String`-re is.

```rust
use std::fmt;
use std::time::Duration;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct Port(u16);

impl Port {
    pub fn new(p: u16) -> Option<Self> { (p != 0).then_some(Port(p)) }   // validáló konstruktor
    pub fn get(self) -> u16 { self.0 }
}

#[derive(Debug, Clone)]
pub struct ServerConfig {
    host: String,               // privát mezők: csak a builderen át állíthatók
    port: Port,
    timeout: Duration,
    max_conn: usize,
}

#[derive(Default)]
pub struct ServerConfigBuilder {
    host: Option<String>,
    port: Option<Port>,
    timeout: Option<Duration>,
    max_conn: Option<usize>,
}

impl ServerConfigBuilder {
    pub fn host(mut self, h: impl Into<String>) -> Self { self.host = Some(h.into()); self }
    pub fn port(mut self, p: Port) -> Self { self.port = Some(p); self }
    pub fn timeout(mut self, t: Duration) -> Self { self.timeout = Some(t); self }
    pub fn max_conn(mut self, n: usize) -> Self { self.max_conn = Some(n); self }

    pub fn build(self) -> Result<ServerConfig, String> {
        Ok(ServerConfig {
            host: self.host.unwrap_or_else(|| "127.0.0.1".into()),
            port: self.port.ok_or("a port kotelezo")?,
            timeout: self.timeout.unwrap_or(Duration::from_secs(30)),
            max_conn: self.max_conn.unwrap_or(1024),
        })
    }
}

impl ServerConfig {
    pub fn builder() -> ServerConfigBuilder { ServerConfigBuilder::default() }  // asszociált fv
    pub fn addr(&self) -> String { format!("{}:{}", self.host, self.port.get()) }
    pub fn scale(&mut self, factor: usize) { self.max_conn *= factor; }
    pub fn into_host(self) -> String { self.host }                             // elfogyaszt
}

impl fmt::Display for ServerConfig {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{} (timeout {:?}, max {})", self.addr(), self.timeout, self.max_conn)
    }
}

fn main() -> Result<(), String> {
    let mut cfg = ServerConfig::builder()
        .host("0.0.0.0")
        .port(Port::new(8080).ok_or("rossz port")?)
        .max_conn(256)
        .build()?;
    cfg.scale(2);
    println!("{cfg}");
    println!("{}", cfg.into_host());   // cfg ezután nem használható
    Ok(())
}
```

## Enumok és mintaillesztés
<!-- q: Hogyan használjam az enumokat és a match mintaillesztést Rustban? -->
<!-- tags: enum, pattern matching, match, if let, let else, matches!, guards, algebraic data types -->

A Rust `enum` algebrai adattípus: minden variáns saját adatot hordozhat, így egy típusban fejezhető ki például egy AST csomópont vagy egy protokollüzenet. A `match` kimerítő – ha egy variáns kimarad, fordítási hiba jön, ezért egy új variáns hozzáadásakor a fordító megmutatja az összes javítandó helyet. A minták lehetnek beágyazottak, or-minták (`'+' | '-'`), tartományok, szeletminták és guard-ok (`if`); a `@` köti a teljes illesztett értéket. Az `if let`, a `let ... else` és a `matches!` a rövid esetekre való. Rekurzív enumhoz `Box` indirekció kell, mert a méretnek fordításkor ismertnek kell lennie.

```rust
#[derive(Debug, Clone, PartialEq)]
enum Token { Num(f64), Op(char), LParen, RParen }

#[derive(Debug)]
enum Expr {
    Num(f64),
    Bin { op: char, lhs: Box<Expr>, rhs: Box<Expr> },   // Box: rekurzív típushoz
    Neg(Box<Expr>),
}

fn eval(e: &Expr) -> Result<f64, String> {
    Ok(match e {
        Expr::Num(n) => *n,
        Expr::Neg(inner) => -eval(inner)?,
        Expr::Bin { op, lhs, rhs } => {
            let (a, b) = (eval(lhs)?, eval(rhs)?);
            match *op {
                '+' => a + b,
                '-' => a - b,
                '*' => a * b,
                '/' if b == 0.0 => return Err("nullaval osztas".into()),   // guard
                '/' => a / b,
                other => return Err(format!("ismeretlen operator: {other}")),
            }
        }
    })
}

fn classify(t: &Token) -> &'static str {
    match t {
        Token::Num(n) if n.fract() == 0.0 => "egesz",
        Token::Num(_) => "tort",
        Token::Op('+' | '-') => "additiv",            // or-minta
        Token::Op(_) => "multiplikativ",
        Token::LParen | Token::RParen => "zarojel",
    }
}

fn main() {
    // (2 + 3) * -4
    let e = Expr::Bin {
        op: '*',
        lhs: Box::new(Expr::Bin { op: '+', lhs: Box::new(Expr::Num(2.0)), rhs: Box::new(Expr::Num(3.0)) }),
        rhs: Box::new(Expr::Neg(Box::new(Expr::Num(4.0)))),
    };
    println!("{:?}", eval(&e));                        // Ok(-20.0)

    let tokens = [Token::Num(2.0), Token::Op('+'), Token::Num(0.5), Token::LParen];
    for t in &tokens { println!("{t:?} -> {}", classify(t)); }

    if let Some(Token::Num(n)) = tokens.first() { println!("elso szam: {n}"); }
    let Some(Token::Op(op)) = tokens.get(1) else { panic!("operator kellett") };
    let parens = tokens.iter().filter(|t| matches!(t, Token::LParen | Token::RParen)).count();

    let nums = [1, 5, 9, 12];
    let [first, .., last] = nums;                      // tömbminta: fix méretnél cáfolhatatlan
    println!("elso {first}, utolso {last}");

    let age: u32 = 17;
    let group = match age {
        n @ 0..=17 => format!("kiskoru ({n})"),        // @ kötés tartománnyal
        _ => "felnott".to_string(),
    };
    println!("{op} {parens} {group}");
}
```

## Traitek és generikusok
<!-- q: Hogyan működnek a traitek és a generikus függvények Rustban? -->
<!-- tags: traits, generics, trait bounds, where clause, associated types, blanket impl, impl Trait, monomorphization -->

A trait viselkedés-szerződés (más nyelvekben interface/typeclass), alapértelmezett metódusokkal is. A generikus függvény trait-korláttal (`T: Summary`) monomorfizálódik: minden konkrét típusra külön, inline-olható kód készül, így nincs futásidejű költség. Az asszociált típus (`type Output`) a traithez tartozó kimeneti típust rögzíti, a blanket implementáció (`impl<T: Display> Shout for T`) egyszerre minden megfelelő típusnak ad képességet. Az `impl Trait` visszatérési pozícióban rejtett, de konkrét típust ad (pl. iterátorláncot vagy closure-t). Az orphan rule miatt idegen traitet idegen típusra nem implementálhatsz – erre newtype a megoldás.

```rust
use std::collections::HashMap;
use std::fmt::Display;
use std::hash::Hash;
use std::ops::Add;

trait Summary {
    fn author(&self) -> String;
    fn summarize(&self) -> String { format!("(Bovebben: {}...)", self.author()) }  // alapértelmezett
}

struct Tweet { user: String, text: String }
struct Article { by: String }

impl Summary for Tweet {
    fn author(&self) -> String { format!("@{}", self.user) }
    fn summarize(&self) -> String { format!("{}: {}", self.author(), self.text) }
}
impl Summary for Article {
    fn author(&self) -> String { self.by.clone() }
}

// Statikus diszpécs: monomorfizáció
fn notify<T: Summary>(item: &T) -> String { format!("Uj: {}", item.summarize()) }

// where-záradék és asszociált típus (Add::Output)
fn sum_all<T>(items: &[T]) -> T
where
    T: Add<Output = T> + Copy + Default,
{
    items.iter().fold(T::default(), |acc, &x| acc + x)
}

fn frequencies<K: Eq + Hash + Clone>(items: &[K]) -> HashMap<K, usize> {
    let mut m = HashMap::new();
    for k in items { *m.entry(k.clone()).or_insert(0) += 1; }
    m
}

// Blanket implementáció: minden Display típus megkapja
trait Shout { fn shout(&self) -> String; }
impl<T: Display + ?Sized> Shout for T {
    fn shout(&self) -> String { self.to_string().to_uppercase() + "!" }
}

#[derive(Debug, Clone, Copy, Default, PartialEq)]
struct Vec2 { x: f32, y: f32 }
impl Add for Vec2 {                                  // operátor-túlterhelés traittel
    type Output = Vec2;
    fn add(self, o: Vec2) -> Vec2 { Vec2 { x: self.x + o.x, y: self.y + o.y } }
}

fn evens(limit: u32) -> impl Iterator<Item = u32> { (0..limit).filter(|n| n % 2 == 0) }

fn main() {
    let t = Tweet { user: "rustlang".into(), text: "uj kiadas".into() };
    let a = Article { by: "Szerzo".into() };
    println!("{}\n{}", notify(&t), notify(&a));
    println!("{:?}", sum_all(&[Vec2 { x: 1.0, y: 2.0 }, Vec2 { x: 3.0, y: 4.0 }]));
    println!("{} {}", sum_all(&[1, 2, 3]), "hello".shout());
    println!("{:?}", frequencies(&["a", "b", "a"]));
    println!("{:?}", evens(10).collect::<Vec<_>>());
}
```

## Trait objektumok és dinamikus diszpécs (dyn Trait)
<!-- q: Mikor használjak dyn Trait trait objektumot generikus helyett Rustban? -->
<!-- tags: trait objects, dyn, dynamic dispatch, vtable, fat pointer, Box dyn, object safety, plugin -->

A `dyn Trait` dinamikus diszpécset ad: a `&dyn Trait` / `Box<dyn Trait>` egy „fat pointer” (adatpointer + vtable-pointer, 16 bájt), a hívás indirekt. Akkor kell, ha a konkrét típus csak futásidőben dől el (pluginek, konfigurációból választott stratégia), vagy heterogén gyűjteményt tárolsz. A generikus (statikus) változat gyorsabb és inline-olható, a `dyn` viszont kisebb binárist és rugalmasabb architektúrát ad. Csak dyn-kompatibilis (object safe) trait használható így: nem lehet generikus metódusa, és nem adhat vissza `Self`-et (`where Self: Sized` nélkül).

```rust
use std::collections::HashMap;
use std::fmt::Debug;

trait Plugin: Debug {                           // supertrait: minden plugin Debug is
    fn name(&self) -> &str;
    fn handle(&mut self, input: &str) -> Option<String>;
}

#[derive(Debug, Default)]
struct Counter { seen: usize }
impl Plugin for Counter {
    fn name(&self) -> &str { "counter" }
    fn handle(&mut self, _input: &str) -> Option<String> {
        self.seen += 1;
        Some(format!("{} uzenet", self.seen))
    }
}

#[derive(Debug)]
struct Filter { banned: Vec<String> }
impl Plugin for Filter {
    fn name(&self) -> &str { "filter" }
    fn handle(&mut self, input: &str) -> Option<String> {
        self.banned
            .iter()
            .any(|b| input.contains(b.as_str()))
            .then(|| "tiltott tartalom".to_string())
    }
}

// Gyártábla: futásidejű név -> konkrét típus
type Factory = fn() -> Box<dyn Plugin>;

fn registry() -> HashMap<&'static str, Factory> {
    let mut m: HashMap<&'static str, Factory> = HashMap::new();
    m.insert("counter", || Box::new(Counter::default()));
    m.insert("filter", || Box::new(Filter { banned: vec!["spam".into()] }));
    m
}

// &dyn paraméter: bármely Plugin, egyetlen lefordított példány
fn describe(p: &dyn Plugin) -> String { format!("plugin<{}>", p.name()) }

fn main() {
    let reg = registry();
    let mut plugins: Vec<Box<dyn Plugin>> = ["counter", "filter"]
        .iter()
        .filter_map(|n| reg.get(n).map(|make| make()))
        .collect();

    for msg in ["szia", "olcso spam itt"] {
        for p in plugins.iter_mut() {
            if let Some(out) = p.handle(msg) { println!("[{}] {}", p.name(), out); }
        }
    }
    println!("{}", describe(plugins[0].as_ref()));
    println!("{:?}", plugins);
    println!("&dyn meret: {} bajt", std::mem::size_of::<&dyn Plugin>());   // 16
}
```

## Hibakezelés: Result, ? operátor és saját hibatípus
<!-- q: Hogyan kezeljem a hibákat Rustban Result-tal, a ? operátorral és saját hibatípussal? -->
<!-- tags: error handling, Result, question mark operator, custom error, thiserror, anyhow, Box dyn Error, source -->

A Rust nem használ kivételt: a helyreállítható hiba `Result<T, E>`, a „nincs érték” `Option<T>`, a programhiba pedig `panic!`. A `?` operátor `Err` esetén korán visszatér, és közben `From::from`-mal konvertálja a hibát a függvény hibatípusára. Könyvtárban saját, strukturált hibatípus (enum) a helyes, `Display` + `std::error::Error` implementációval és `source()` hibalánccal – a `thiserror` crate ezt `#[derive(Error)]`-ral generálja. Alkalmazásszinten a `Box<dyn Error>` vagy az `anyhow::Result` a kényelmes. Az `unwrap`/`expect` csak tesztben vagy bizonyítottan lehetetlen hibára való.

```rust
use std::fmt;
use std::fs;
use std::num::ParseIntError;
use std::path::Path;

#[derive(Debug)]
pub enum ConfigError {
    Io { path: String, source: std::io::Error },
    Parse { line: usize, source: ParseIntError },
    Missing(&'static str),
}

impl fmt::Display for ConfigError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ConfigError::Io { path, .. } => write!(f, "nem olvashato: {path}"),
            ConfigError::Parse { line, .. } => write!(f, "hibas szam a(z) {line}. sorban"),
            ConfigError::Missing(k) => write!(f, "hianyzo kulcs: {k}"),
        }
    }
}

impl std::error::Error for ConfigError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {   // hibalánc
        match self {
            ConfigError::Io { source, .. } => Some(source),
            ConfigError::Parse { source, .. } => Some(source),
            ConfigError::Missing(_) => None,
        }
    }
}

#[derive(Debug)]
pub struct Config { pub port: u16, pub workers: u32 }

pub fn parse_config(text: &str) -> Result<Config, ConfigError> {
    let (mut port, mut workers) = (None, None);
    for (i, line) in text.lines().enumerate() {
        let Some((key, val)) = line.split_once('=') else { continue };
        let err = |e| ConfigError::Parse { line: i + 1, source: e };
        match key.trim() {
            "port" => port = Some(val.trim().parse::<u16>().map_err(err)?),
            "workers" => workers = Some(val.trim().parse::<u32>().map_err(err)?),
            _ => {}
        }
    }
    Ok(Config {
        port: port.ok_or(ConfigError::Missing("port"))?,
        workers: workers.unwrap_or(4),
    })
}

pub fn load(path: &Path) -> Result<Config, ConfigError> {
    let text = fs::read_to_string(path)
        .map_err(|e| ConfigError::Io { path: path.display().to_string(), source: e })?;
    parse_config(&text)
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cfg = parse_config("port = 8080\nworkers = 8\n")?;
    println!("{cfg:?}");
    if let Err(e) = parse_config("port = sok") {
        eprintln!("hiba: {e}");
        if let Some(src) = std::error::Error::source(&e) { eprintln!("  oka: {src}"); }
    }
    if let Err(e) = load(Path::new("nincs_ilyen.conf")) { eprintln!("{e}"); }
    Ok(())
}
```

## Iterátorok és closure-ök
<!-- q: Hogyan használjam az iterátorokat és a closure-öket Rustban, mi az Fn, FnMut és FnOnce? -->
<!-- tags: iterators, closures, Fn, FnMut, FnOnce, map, filter, fold, collect, lazy evaluation, zero-cost -->

Az iterátor-adapterek (`map`, `filter`, `zip`, `windows`…) lusták: csak a fogyasztó (`collect`, `sum`, `for`) hajtja végre őket, egyetlen bejárásban, köztes gyűjtemény nélkül, és a fordító kézi ciklussal egyenértékű kódra optimalizálja. Saját iterátorhoz elég a `next()` metódust megírni, a többi adapter ingyen jár. A closure a környezetét befogja: az `Fn` csak olvas, az `FnMut` módosít, az `FnOnce` elfogyaszt; a `move` kulcsszó tulajdonba veszi a befogott értékeket (szálaknál és visszaadott closure-nél kötelező). Hasznos trükk: `Result`-ok iterátorát `Result<Vec<_>, _>`-ba gyűjtve az első hibánál megáll.

```rust
use std::collections::HashMap;

struct LogEntry { level: &'static str, service: &'static str, ms: u32 }

// Saját iterátor: csak a next() kell
struct Fib { a: u64, b: u64 }
impl Iterator for Fib {
    type Item = u64;
    fn next(&mut self) -> Option<u64> {
        let r = self.a;
        self.a = self.b;
        self.b = r.checked_add(self.b)?;     // túlcsordulásnál a sorozat véget ér
        Some(r)
    }
}

// Closure-t visszaadó függvény: move befogja a küszöböt
fn slower_than(limit: u32) -> impl Fn(&&LogEntry) -> bool {
    move |e: &&LogEntry| e.ms > limit
}

fn apply_n<F: FnMut()>(n: usize, mut f: F) { for _ in 0..n { f(); } }

fn main() {
    let logs = vec![
        LogEntry { level: "INFO", service: "api", ms: 12 },
        LogEntry { level: "WARN", service: "db", ms: 340 },
        LogEntry { level: "ERROR", service: "api", ms: 1200 },
        LogEntry { level: "INFO", service: "db", ms: 45 },
    ];

    let slow: Vec<&str> = logs.iter().filter(slower_than(100)).map(|e| e.service).collect();

    let per_service = logs.iter().fold(HashMap::new(), |mut m: HashMap<&str, u32>, e| {
        *m.entry(e.service).or_default() += e.ms;
        m
    });

    let avg = logs.iter().map(|e| e.ms as f64).sum::<f64>() / logs.len() as f64;
    let first_error = logs.iter().position(|e| e.level == "ERROR");
    let (errors, rest): (Vec<_>, Vec<_>) = logs.iter().partition(|e| e.level == "ERROR");
    let deltas: Vec<i64> = logs.windows(2).map(|w| w[1].ms as i64 - w[0].ms as i64).collect();
    let fibs: Vec<u64> = Fib { a: 0, b: 1 }.skip(5).step_by(2).take(5).collect();

    let mut calls = 0;
    apply_n(3, || calls += 1);               // FnMut: módosítja a befogott változót

    // Az első hibánál megálló gyűjtés
    let parsed: Result<Vec<u32>, _> = ["1", "2", "x"].iter().map(|s| s.parse::<u32>()).collect();

    println!("{slow:?}\n{per_service:?}\navg={avg:.1} first_err={first_error:?}");
    println!("{} hiba, {} egyeb, {deltas:?} {fibs:?} {calls} {}", errors.len(), rest.len(), parsed.is_err());
}
```

## Smart pointerek: Box, Rc, Weak, RefCell, Cell
<!-- q: Mikor használjak Box, Rc, RefCell és Weak smart pointert Rustban? -->
<!-- tags: smart pointers, Box, Rc, Weak, RefCell, Cell, interior mutability, reference counting, cycles -->

A `Box<T>` egyedi tulajdon a heapen (rekurzív típusok, nagy értékek, trait objektumok). Az `Rc<T>` egyszálú referenciaszámlált megosztott tulajdon, de csak olvasható hozzáférést ad; a módosításhoz belső mutabilitás kell: a `RefCell<T>` a kölcsönzési szabályokat FUTÁSIDŐBEN ellenőrzi (megsértése panic), a `Cell<T>` `Copy` típusokat cserél kölcsönzés nélkül. Két `Rc` egymásra mutatva soha nem szabadul fel, ezért a visszafelé mutató éleket (`parent`) `Weak`-kel kell tárolni. Többszálú megfelelőjük az `Arc<Mutex<T>>`/`Arc<RwLock<T>>`.

```rust
use std::cell::{Cell, RefCell};
use std::collections::HashMap;
use std::rc::{Rc, Weak};

#[derive(Debug)]
enum List { Cons(i32, Box<List>), Nil }       // Box: rekurzív típus

#[derive(Debug)]
struct TreeNode {
    name: String,
    children: RefCell<Vec<Rc<TreeNode>>>,
    parent: RefCell<Weak<TreeNode>>,          // Weak: nincs Rc-ciklus, nincs leak
}

impl TreeNode {
    fn new(name: &str) -> Rc<TreeNode> {
        Rc::new(TreeNode {
            name: name.into(),
            children: RefCell::new(vec![]),
            parent: RefCell::new(Weak::new()),
        })
    }
    fn add_child(parent: &Rc<TreeNode>, child: Rc<TreeNode>) {
        *child.parent.borrow_mut() = Rc::downgrade(parent);
        parent.children.borrow_mut().push(child);
    }
}

// Memoizáló cache &self mögött: kívülről immutábilis API, belül módosuló állapot
struct Fib { cache: RefCell<HashMap<u64, u64>>, misses: Cell<u32> }
impl Fib {
    fn get(&self, n: u64) -> u64 {
        if n < 2 { return n; }
        let cached = self.cache.borrow().get(&n).copied();   // a borrow itt véget ér
        if let Some(v) = cached { return v; }
        self.misses.set(self.misses.get() + 1);
        let v = self.get(n - 1) + self.get(n - 2);
        self.cache.borrow_mut().insert(n, v);   // ha itt még élne egy borrow(): panic
        v
    }
}

fn main() {
    let list = List::Cons(1, Box::new(List::Cons(2, Box::new(List::Nil))));
    println!("{list:?}");

    let root = TreeNode::new("root");
    let leaf = TreeNode::new("leaf");
    TreeNode::add_child(&root, Rc::clone(&leaf));   // Rc::clone: csak számlálónövelés
    println!("leaf strong={} weak={}", Rc::strong_count(&leaf), Rc::weak_count(&leaf));
    if let Some(p) = leaf.parent.borrow().upgrade() { println!("szulo: {}", p.name); }
    println!("root gyerekei: {}", root.children.borrow().len());

    let fib = Fib { cache: RefCell::new(HashMap::new()), misses: Cell::new(0) };
    println!("fib(80)={} misses={}", fib.get(80), fib.misses.get());

    let shared = Rc::new(RefCell::new(Vec::<String>::new()));
    let writer = Rc::clone(&shared);
    writer.borrow_mut().push("bejegyzes".into());
    println!("{:?}", shared.borrow());
}
```

## Szálak: Arc, Mutex, csatornák és scoped threads
<!-- q: Hogyan írjak többszálú kódot Rustban Arc, Mutex és csatornák segítségével? -->
<!-- tags: threads, Arc, Mutex, RwLock, mpsc, channels, scoped threads, atomics, fearless concurrency -->

A Rust „fearless concurrency” ígérete a típusrendszerből jön: megosztott, módosítható állapot csak szinkronizációs primitíven (`Mutex`, `RwLock`, atomikus típus) át érhető el, így a data race fordítási hiba. A `thread::scope` szálai kölcsönözhetik a stack-adatot, mert garantáltan véget érnek a scope előtt; a `thread::spawn` `'static` closure-t vár, ezért ott `Arc` kell. A `MutexGuard` drop-ja oldja fel a zárat – a kritikus szakasz legyen rövid. A csatorna (`mpsc`) üzenetküldéssel kerüli el a megosztott állapotot; a vevő ciklusa csak akkor ér véget, ha minden küldő eldobódott. Ha egy szál zár tartása közben panikol, a mutex „mérgezett” lesz.

```rust
use std::collections::HashMap;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{mpsc, Arc, Mutex, RwLock};
use std::thread;

fn main() {
    // 1) Scoped threads: a stack-adat kölcsönözhető
    let data: Vec<u64> = (1..=1_000_000).collect();
    let total: u64 = thread::scope(|s| {
        let handles: Vec<_> = data
            .chunks(data.len() / 4)
            .map(|part| s.spawn(move || part.iter().sum::<u64>()))
            .collect();
        handles.into_iter().map(|h| h.join().unwrap()).sum()
    });
    println!("osszeg: {total}");

    // 2) Arc<Mutex<T>>: megosztott, módosítható állapot 'static szálak között
    let stats = Arc::new(Mutex::new(HashMap::<String, u32>::new()));
    let processed = Arc::new(AtomicUsize::new(0));
    let mut handles = Vec::new();
    for id in 0..4 {
        let stats = Arc::clone(&stats);
        let processed = Arc::clone(&processed);
        handles.push(thread::spawn(move || {
            for i in 0..100 {
                let key = format!("bucket{}", (id + i) % 3);
                *stats.lock().unwrap().entry(key).or_insert(0) += 1;   // a guard a sor végén eldobódik
                processed.fetch_add(1, Ordering::Relaxed);
            }
        }));
    }
    for h in handles { h.join().expect("a szal panikolt"); }
    println!("{:?} feldolgozva: {}", stats.lock().unwrap(), processed.load(Ordering::Relaxed));

    // 3) Csatorna: üzenetküldés megosztott állapot helyett
    let (tx, rx) = mpsc::channel::<(usize, String)>();
    for w in 0..3 {
        let tx = tx.clone();
        thread::spawn(move || {
            for job in 0..2 { tx.send((w, format!("eredmeny {job}"))).unwrap(); }
        });
    }
    drop(tx);                      // különben az rx ciklus sosem ér véget
    for (w, msg) in rx { println!("worker {w}: {msg}"); }

    // 4) RwLock: sok olvasó VAGY egy író
    let cfg = RwLock::new(String::from("v1"));
    {
        let r1 = cfg.read().unwrap();
        let r2 = cfg.read().unwrap();
        println!("{r1} {r2}");
    }
    *cfg.write().unwrap() = "v2".into();
    println!("{}", cfg.read().unwrap());
}
```

## Send és Sync marker traitek
<!-- q: Mit jelent a Send és a Sync trait Rustban, miért nem küldhető át az Rc szálak között? -->
<!-- tags: Send, Sync, auto traits, thread safety, unsafe impl, PhantomData, Rc, Arc -->

A `Send` azt jelenti, hogy a típus TULAJDONA átadható egy másik szálnak; a `Sync` azt, hogy `&T` megosztható szálak között (`T: Sync` pontosan akkor, ha `&T: Send`). Ezek auto traitek: a fordító a mezőkből vezeti le őket, ezért az `Rc` (nem atomikus számláló) nem `Send`, a `RefCell` (nem szálbiztos borrow-flag) nem `Sync`, a nyers pointer pedig egyik sem. Ha egy nyers pointert tartalmazó típus bizonyítottan szálbiztos, `unsafe impl Send` jelentheti ki – a helyességért ekkor a programozó felel. A `PhantomData<*const ()>` mezővel egy típus szándékosan szálhoz köthető.

```rust
use std::cell::RefCell;
use std::marker::PhantomData;
use std::rc::Rc;
use std::sync::{Arc, Mutex};
use std::thread;

fn assert_send<T: Send>() {}
fn assert_sync<T: Sync>() {}

// A nyers pointer miatt se nem Send, se nem Sync...
struct RawBuffer { ptr: *mut u8, len: usize }

// ...de mivel kizárólagosan birtokolja a memóriát, átadható másik szálnak.
// SAFETY: a puffert csak a tulajdonos éri el, megosztott mutáció nincs.
unsafe impl Send for RawBuffer {}

impl RawBuffer {
    fn new(len: usize) -> Self {
        let boxed: Box<[u8]> = vec![0u8; len].into_boxed_slice();
        let ptr = Box::into_raw(boxed) as *mut u8;   // a tulajdon a RawBuffer-é
        RawBuffer { ptr, len }
    }
}
impl Drop for RawBuffer {
    fn drop(&mut self) {
        // SAFETY: ptr/len egy Box<[u8]>-ból származik, és pontosan egyszer szabadítjuk fel
        unsafe { drop(Box::from_raw(std::ptr::slice_from_raw_parts_mut(self.ptr, self.len))); }
    }
}

// Szándékosan nem Send típus (pl. szálhoz kötött handle)
struct ThreadBound { _not_send: PhantomData<*const ()> }

fn main() {
    assert_send::<Arc<Mutex<Vec<i32>>>>();   // Arc<T>: Send + Sync, ha T: Send + Sync
    assert_sync::<Mutex<RefCell<i32>>>();    // a Mutex Sync-ké teszi a csak Send tartalmat
    assert_send::<RawBuffer>();
    // assert_send::<Rc<i32>>();             // HIBA: Rc nem Send
    // assert_sync::<RefCell<i32>>();        // HIBA: RefCell nem Sync
    // assert_send::<ThreadBound>();         // HIBA: *const () nem Send

    let buf = RawBuffer::new(1024);
    let h = thread::spawn(move || {
        let b = buf;                         // az egész puffer átkerül a szálba
        b.len
    });
    println!("{}", h.join().unwrap());

    let local = Rc::new(5);
    // thread::spawn(move || println!("{local}"));   // `Rc<i32>` cannot be sent between threads
    println!("{local}");
    let _bound = ThreadBound { _not_send: PhantomData };
}
```

## Async/await tokio-val
<!-- q: Hogyan írjak aszinkron kódot Rustban async/await-tel és tokio-val? -->
<!-- tags: async, await, tokio, futures, spawn, join, select, semaphore, channels, cancellation -->

Az `async fn` egy `Future`-t ad vissza, ami magától nem fut: egy executor (pl. tokio) pollozza, és minden `.await` pontnál más taskra válthat – így kevés OS-szálon sok ezer egyidejű I/O-művelet futhat. A `tokio::join!` egyszerre futtat több future-t, a `tokio::spawn` önálló taskot indít (`Send + 'static` future kell), a `select!` az elsőként kész ágat választja, a többit eldobja (ez a cancellation). Async kódban tilos blokkolni (`std::thread::sleep`, szinkron fájl-I/O, hosszú CPU-munka), mert kiéhezteti az executor szálait – erre `spawn_blocking` való. A `.await`-en át tartott zárhoz `tokio::sync::Mutex` kell, rövid kritikus szakaszra a `std::sync::Mutex` is jó.

```rust
// Cargo.toml: tokio = { version = "1", features = ["full"] }
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{mpsc, Mutex, Semaphore};
use tokio::time::{sleep, timeout};

async fn fetch(id: u32) -> Result<String, String> {
    sleep(Duration::from_millis(50 * id as u64)).await;     // nem blokkoló várakozás
    if id == 3 { Err(format!("{id}: hiba")) } else { Ok(format!("adat-{id}")) }
}

#[tokio::main]
async fn main() {
    // 1) Párhuzamos várakozás join!-nal
    let (a, b) = tokio::join!(fetch(1), fetch(2));
    println!("{a:?} {b:?}");

    // 2) spawn + Semaphore: legfeljebb 2 egyidejű "kérés"
    let limit = Arc::new(Semaphore::new(2));
    let results = Arc::new(Mutex::new(Vec::new()));
    let mut handles = Vec::new();
    for id in 1..=5 {
        let limit = Arc::clone(&limit);
        let results = Arc::clone(&results);
        handles.push(tokio::spawn(async move {
            let _permit = limit.acquire().await.unwrap();   // droppoláskor felszabadul
            let r = fetch(id).await;
            results.lock().await.push((id, r));
        }));
    }
    for h in handles { h.await.unwrap(); }
    println!("{:?}", results.lock().await);

    // 3) Időkorlát: lejáratkor a belső future eldobódik
    match timeout(Duration::from_millis(100), fetch(4)).await {
        Ok(r) => println!("idoben: {r:?}"),
        Err(_) => println!("timeout"),
    }

    // 4) Korlátos csatorna (backpressure) + leállítás select!-tel
    let (tx, mut rx) = mpsc::channel::<u32>(16);
    let producer = tokio::spawn(async move {
        for i in 0..5 {
            tx.send(i).await.unwrap();
            sleep(Duration::from_millis(10)).await;
        }
    });
    let shutdown = sleep(Duration::from_millis(200));
    tokio::pin!(shutdown);
    loop {
        tokio::select! {
            Some(v) = rx.recv() => println!("kapott: {v}"),
            _ = &mut shutdown => { println!("leallas"); break; }
        }
    }
    producer.await.unwrap();
}
```

## Unsafe Rust
<!-- q: Mire való az unsafe Rust, és hogyan írjak biztonságos absztrakciót unsafe kód köré? -->
<!-- tags: unsafe, raw pointers, undefined behavior, safety invariants, MaybeUninit, get_unchecked, miri -->

Az `unsafe` öt pluszképességet ad: nyers pointer dereferálása, `unsafe fn` hívása, mutable static elérése, unsafe trait implementálása és union-mező olvasása – a borrow checker és a típusellenőrzés közben is működik. Az unsafe blokk szerződés: a programozó garantálja, hogy nincs UB (érvényes, igazított pointer, nincs aliasing-sértés, inicializált memória). A helyes minta egy kicsi unsafe mag biztonságos API mögött, amely az előfeltételeket (pl. `assert!`) ellenőrzi, és minden unsafe blokk fölött `// SAFETY:` komment indokol. Az unsafe kódot a Miri (`cargo +nightly miri test`) futásidőben ellenőrzi UB-re.

```rust
use std::mem::MaybeUninit;

// Két diszjunkt &mut szelet egy szeletből (a std split_at_mut is így működik)
fn split_at_mut<T>(s: &mut [T], mid: usize) -> (&mut [T], &mut [T]) {
    let len = s.len();
    assert!(mid <= len);                       // a biztonságos burok ellenőrzi az előfeltételt
    let p = s.as_mut_ptr();
    // SAFETY: mid <= len, a két tartomány nem fedi egymást, mindkettő a szeleten belül van,
    // és az élettartamuk az eredeti &mut-hoz kötött.
    unsafe {
        (
            std::slice::from_raw_parts_mut(p, mid),
            std::slice::from_raw_parts_mut(p.add(mid), len - mid),
        )
    }
}

/// Ellenőrzés nélküli indexelés.
/// # Safety
/// `i < v.len()` kell legyen.
unsafe fn get_fast(v: &[u32], i: usize) -> u32 {
    // SAFETY: a hívó garantálja, hogy i < v.len()
    unsafe { *v.get_unchecked(i) }
}

fn sum_every_other(v: &[u32]) -> u64 {
    let mut s = 0u64;
    let mut i = 0;
    while i < v.len() {
        // SAFETY: a ciklusfeltétel miatt i < v.len()
        s += unsafe { get_fast(v, i) } as u64;
        i += 2;
    }
    s
}

// MaybeUninit: inicializálatlan memória korrekt kezelése
fn make_array() -> [String; 3] {
    let mut arr: [MaybeUninit<String>; 3] = [const { MaybeUninit::uninit() }; 3];
    for (i, slot) in arr.iter_mut().enumerate() {
        slot.write(format!("elem{i}"));
    }
    // SAFETY: mindhárom elemet inicializáltuk fent
    arr.map(|x| unsafe { x.assume_init() })
}

static mut COUNTER: u32 = 0;   // mutable static: minden elérés unsafe, data race veszély

fn bump() -> u32 {
    // SAFETY: csak a fő szál hívja (élesben inkább AtomicU32-t használj)
    unsafe {
        COUNTER += 1;
        COUNTER
    }
}

fn main() {
    let mut data = [1, 2, 3, 4, 5, 6];
    let (a, b) = split_at_mut(&mut data, 3);
    a[0] += b[0];
    println!("{data:?} {} {:?}", sum_every_other(&[1, 2, 3, 4, 5]), make_array());
    println!("{:#x} {}", 1.0f32.to_bits(), bump());   // to_bits a transmute biztonságos helyettese
}
```

## FFI: C és Rust együttműködése
<!-- q: Hogyan hívjak C függvényt Rustból, és hogyan exportáljak Rust függvényt C-nek (FFI)? -->
<!-- tags: ffi, extern c, repr c, no_mangle, CString, CStr, cdylib, catch_unwind, interop -->

Az FFI a C ABI-n keresztül köti össze a Rustot más nyelvekkel: az `extern "C"` blokk C függvényeket deklarál (a hívásuk unsafe, mert a fordító nem látja a túloldalt), a `#[no_mangle] extern "C" fn` pedig C-ből hívható szimbólumot exportál (`crate-type = ["cdylib"]` vagy `"staticlib"`). Az átadott structok legyenek `#[repr(C)]`, a stringek `CString`/`CStr` (nullával lezárt, belső `\0` nélkül). Aki allokálta a memóriát, az szabadítsa fel: Rust-allokációt Rust-függvénnyel kell visszaadni. Panic nem léphet át FFI-határon, ezért a határon `catch_unwind` kell; a 2024-es editionben a szintaxis `unsafe extern "C"` és `#[unsafe(no_mangle)]`.

```rust
use std::ffi::{c_char, c_int, CStr, CString};

// --- Rust hív C-t (libc) ---
unsafe extern "C" {
    fn strlen(s: *const c_char) -> usize;
    fn abs(x: c_int) -> c_int;
}

// --- C hív Rustot ---
#[repr(C)]                                  // C-kompatibilis mezőelrendezés
pub struct Stats { pub count: u64, pub mean: f64 }

/// # Safety
/// `data` `len` darab érvényes f64-re mutat (vagy `len == 0`).
#[unsafe(no_mangle)]
pub unsafe extern "C" fn stats_compute(data: *const f64, len: usize) -> Stats {
    if data.is_null() || len == 0 { return Stats { count: 0, mean: 0.0 }; }
    let xs = unsafe { std::slice::from_raw_parts(data, len) };
    Stats { count: len as u64, mean: xs.iter().sum::<f64>() / len as f64 }
}

/// A visszaadott stringet a `greeting_free`-vel kell felszabadítani.
/// # Safety
/// `name` NULL vagy érvényes, nullával lezárt C string.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn greeting(name: *const c_char) -> *mut c_char {
    let name = if name.is_null() {
        "ismeretlen".into()
    } else {
        unsafe { CStr::from_ptr(name) }.to_string_lossy()
    };
    CString::new(format!("Szia, {name}!")).unwrap().into_raw()   // tulajdon a C oldalé
}

/// # Safety
/// `s` a `greeting` által visszaadott pointer (vagy NULL), és csak egyszer adható át.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn greeting_free(s: *mut c_char) {
    if !s.is_null() { unsafe { drop(CString::from_raw(s)); } }   // visszaveszi és felszabadítja
}

// Panic nem léphet át a határon
#[unsafe(no_mangle)]
pub extern "C" fn safe_double(x: c_int) -> c_int {
    std::panic::catch_unwind(|| if x < 0 { panic!("negativ") } else { x * 2 }).unwrap_or(-1)
}

fn main() {
    let s = CString::new("hello ffi").unwrap();   // s-nek élnie kell a hívás alatt!
    let n = unsafe { strlen(s.as_ptr()) };
    let a = unsafe { abs(-42) };
    let st = unsafe { stats_compute([1.0, 2.0, 6.0].as_ptr(), 3) };
    let g = unsafe { greeting(c"Anna".as_ptr()) };
    println!("{n} {a} {} {} {:?}", st.count, st.mean, unsafe { CStr::from_ptr(g) });
    unsafe { greeting_free(g) };
    println!("{}", safe_double(-1));
}
```

## Deklaratív makrók: macro_rules!
<!-- q: Hogyan írjak saját makrót Rustban macro_rules! segítségével? -->
<!-- tags: macros, macro_rules, declarative macros, repetition, hygiene, metaprogramming, proc macro -->

A `macro_rules!` deklaratív makró tokenfán végez mintaillesztést, és fordításkor bontódik ki; fragmentum-specifikátorokkal (`expr`, `ident`, `ty`, `tt`) és ismétlésekkel (`$(...),*`) dolgozik. Higiénikus: a makróban bevezetett lokális változók nem ütköznek a hívó változóival. Boilerplate (getterek, trait-implementációk), DSL-ek, variadikus „függvények” és korai visszatérés (`ensure!`) írására jó; a szabályok sorrendje számít, ezért a belső `@`-szabályok kerüljenek előre. A kibontott kódot a `cargo expand` mutatja; bonyolultabb esetekre (derive, attribútum) procedurális makró való (`syn` + `quote`).

```rust
use std::collections::HashMap;

// hashmap!{ "a" => 1, "b" => 2 } -- kapacitás fordítási időben megszámolva
macro_rules! hashmap {
    (@unit $x:expr) => { () };
    (@count $($x:expr),*) => { <[()]>::len(&[$(hashmap!(@unit $x)),*]) };
    () => { HashMap::new() };
    ($($k:expr => $v:expr),+ $(,)?) => {{          // $(,)?: opcionális záró vessző
        let mut m = HashMap::with_capacity(hashmap!(@count $($k),+));
        $( m.insert($k, $v); )+
        m
    }};
}

// Getter-generálás: ismétlődő boilerplate kiváltása
macro_rules! getters {
    ($t:ty { $($field:ident : $fty:ty),* $(,)? }) => {
        impl $t {
            $( pub fn $field(&self) -> &$fty { &self.$field } )*
        }
    };
}

struct User { name: String, age: u32 }
getters!(User { name: String, age: u32 });

// Korai visszatérés formázott hibával
macro_rules! ensure {
    ($cond:expr, $($fmt:tt)+) => {
        if !$cond { return Err(format!($($fmt)+)); }
    };
}

fn validate(age: u32) -> Result<u32, String> {
    ensure!(age >= 18, "tul fiatal: {}", age);
    ensure!(age < 130, "irrealis kor: {age}");
    Ok(age)
}

// Rekurzív makró: variadikus max
macro_rules! max {
    ($x:expr) => { $x };
    ($x:expr, $($rest:expr),+) => {{
        let a = $x;
        let b = max!($($rest),+);
        if a > b { a } else { b }
    }};
}

fn main() {
    let m: HashMap<&str, i32> = hashmap! { "alma" => 3, "korte" => 5, };
    let u = User { name: "Bela".into(), age: 40 };
    println!("{:?} {} {} {}", m.get("korte"), u.name(), u.age(), max!(3, 9, 4));
    println!("{:?} {:?}", validate(16), validate(30));
}
```

## Cargo: workspace, feature-ök és profilok
<!-- q: Hogyan szervezzek egy Rust projektet cargo workspace-szel, feature flagekkel és release profillal? -->
<!-- tags: cargo, workspace, features, profiles, dependencies, lto, Cargo.toml, build -->

A cargo workspace több crate-et kezel közös `Cargo.lock`-kal és `target/` mappával, így a függőségek egyszer fordulnak, és a verziók a `[workspace.dependencies]`-ben egy helyen rögzíthetők. A feature-ök fordítási idejű kapcsolók: opcionális függőségeket és kódrészeket (`#[cfg(feature = "...")]`) kapcsolnak be; additívnak kell lenniük, mert a cargo a gráfban egyesíti őket. A release profilban az `lto`, a `codegen-units = 1` és a `panic = "abort"` gyorsabb és kisebb binárist ad lassabb fordítás árán. Hasznos parancsok: `cargo clippy` (lint), `cargo fmt`, `cargo tree -d` (duplikált függőségek), `cargo audit`.

```toml
# Gyökér Cargo.toml: workspace
[workspace]
resolver = "2"
members = ["crates/core-lib", "crates/cli"]

[workspace.package]
edition = "2021"
version = "0.3.0"
license = "MIT"

[workspace.dependencies]          # a tagok `serde.workspace = true`-val öröklik
serde = { version = "1", features = ["derive"] }
tokio = { version = "1", features = ["rt-multi-thread", "macros", "fs"] }
thiserror = "2"

[profile.release]
lto = "thin"                      # link-time optimalizálás crate-eken át
codegen-units = 1                 # lassabb build, gyorsabb kód
panic = "abort"                   # kisebb bináris, nincs unwinding
strip = true

[profile.dev.package."*"]
opt-level = 2                     # a függőségek debugban is optimalizáltak

# --- crates/core-lib/Cargo.toml ---
# [package]
# name = "core-lib"
# version.workspace = true
# edition.workspace = true
#
# [dependencies]
# serde.workspace = true
# tokio = { workspace = true, optional = true }
#
# [features]
# default = []
# async = ["dep:tokio"]           # cargo build -p core-lib --features async
```

```rust
// crates/core-lib/src/lib.rs: feature-függő fordítás
pub fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")                 // fordításkor beégetett verzió
}

#[cfg(feature = "async")]
pub async fn load_async(path: &str) -> std::io::Result<String> {
    tokio::fs::read_to_string(path).await     // csak az "async" feature-rel fordul
}

#[cfg(not(feature = "async"))]
pub fn load(path: &str) -> std::io::Result<String> {
    std::fs::read_to_string(path)
}
```

## Tesztelés: unit, integrációs és doc tesztek
<!-- q: Hogyan írjak teszteket Rustban (unit teszt, integrációs teszt, doc teszt)? -->
<!-- tags: testing, cargo test, unit tests, integration tests, doc tests, should_panic, cfg test, table driven -->

A unit tesztek ugyanabban a fájlban, egy `#[cfg(test)]` modulban élnek, így a privát függvények is tesztelhetők, és release buildbe nem kerülnek. Az integrációs tesztek a `tests/` mappában külön crate-ként fordulnak, és csak a publikus API-t látják. A dokumentációs kommentek példái doc testként futnak (`cargo test --doc`), így a dokumentáció nem avulhat el. A teszt visszaadhat `Result`-ot (akkor használhatja a `?`-t), a `#[should_panic(expected = ...)]` a várt panicot ellenőrzi; a `cargo test -- --nocapture` megmutatja a kimenetet. Tulajdonság-alapú teszteléshez `proptest`, benchmarkhoz `criterion` ajánlott.

```rust
// src/lib.rs  (crate neve: mylib)

/// Szöveg URL-barát "slug"-gá alakítása.
///
/// A példa doc testként fut:
/// ~~~
/// assert_eq!(mylib::slugify("Hello, World!"), "hello-world");
/// ~~~
pub fn slugify(s: &str) -> String {
    let mut out = String::new();
    for c in s.chars() {
        if c.is_ascii_alphanumeric() {
            out.push(c.to_ascii_lowercase());
        } else if !out.is_empty() && !out.ends_with('-') {
            out.push('-');
        }
    }
    out.trim_end_matches('-').to_string()
}

pub fn parse_ratio(s: &str) -> Result<f64, String> {
    let (a, b) = s.split_once('/').ok_or("hianyzo '/'")?;
    let a: f64 = a.trim().parse().map_err(|_| "rossz szamlalo")?;
    let b: f64 = b.trim().parse().map_err(|_| "rossz nevezo")?;
    if b == 0.0 { return Err("nulla nevezo".into()); }
    Ok(a / b)
}

#[cfg(test)]
mod tests {
    use super::*;                        // a privát elemek is elérhetők

    #[test]
    fn slug_basic() {
        assert_eq!(slugify("  Rust  Is Fun "), "rust-is-fun");
    }

    #[test]
    fn ratio_ok() -> Result<(), String> {   // Result-os teszt: használhat ?-t
        let r = parse_ratio("10/4")?;
        assert!((r - 2.5).abs() < f64::EPSILON);
        Ok(())
    }

    #[test]
    fn ratio_errors() {
        assert!(parse_ratio("1/0").is_err());
        assert_eq!(parse_ratio("x"), Err("hianyzo '/'".to_string()));
    }

    #[test]
    #[should_panic(expected = "index out of bounds")]
    fn panics_on_oob() {
        let v: Vec<i32> = Vec::new();
        let _x = v[0];
    }

    #[test]
    fn slug_table() {                    // táblázatos teszt
        let cases = [("A B", "a-b"), ("--x--", "x"), ("", "")];
        for (input, want) in cases {
            assert_eq!(slugify(input), want, "bemenet: {input:?}");
        }
    }
}
```

```rust
// tests/api.rs: integrációs teszt, csak a publikus API-t látja
use mylib::{parse_ratio, slugify};

#[test]
fn public_api_works() {
    assert_eq!(slugify("Integracios Teszt"), "integracios-teszt");
    assert_eq!(parse_ratio("3/4"), Ok(0.75));
}
```
