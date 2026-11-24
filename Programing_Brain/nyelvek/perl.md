# Perl
<!-- tech: perl -->

A Perl dinamikusan típusos, interpretált nyelv, amelyet a szövegfeldolgozás, a rendszeradminisztráció és a "ragasztó" szkriptek tettek híressé; a reguláris kifejezések nyelvi szinten, első osztályú elemként vannak beépítve. A változók típusát a szigil (`$` skalár, `@` tömb, `%` hash) jelzi, a kifejezések jelentése pedig a kontextustól (skalár vagy lista) függ. A memóriát referenciaszámlálás kezeli (körkörös referenciáknál `weaken` kell), az objektumorientáltság a `bless`-re épül, a modern OO-t a Moose/Moo vagy az 5.38+ natív `class` szintaxisa adja. A CPAN hatalmas modulgyűjtemény. Kiváló log- és szövegfeldolgozásra, egysoros parancsokra és régi rendszerek karbantartására; új, nagy csapatos alkalmazásokhoz ma ritkábban választják.

## Szigilek és kontextus
<!-- q: Mit jelentenek a szigilek és a skalár/lista kontextus Perlben? -->
<!-- tags: sigils, context, scalar, list, wantarray, slices -->

A szigil azt jelzi, *mit kérsz ki*, nem a változó típusát: `$langs[0]` egy elem (skalár), `@langs[0,1]` tömbszelet, `@ver{qw(a b)}` hash-szelet. Minden kifejezés kontextusban értékelődik ki: egy tömb skalár kontextusban az elemszámát adja, lista kontextusban az elemeit – ez ugyanannak a kódnak más-más jelentést ad. A `wantarray` segítségével egy függvény a hívó kontextusához igazíthatja a visszatérési értékét. Buktató: a `my ($x) = @list` (lista, első elem) és a `my $x = @list` (skalár, darabszám) egyetlen zárójelben különbözik.

```perl
use v5.36;    # strict, warnings, say és szignatúrák bekapcsolva

my @langs = ('Perl', 'Ruby', 'PHP');           # @ – tömb
my %ver   = (Perl => '5.40', Ruby => '3.3');   # % – hash

# A szigil azt jelzi, MIT kérsz ki:
my $first  = $langs[0];                 # egy elem -> $
my @two    = @langs[0, 1];              # tömbszelet -> @
my @vers   = @ver{qw(Perl Ruby)};       # hash-szelet -> @
my %subset = %ver{'Perl'};              # kulcs/érték szelet (5.20+)

# Kontextus: ugyanaz a kifejezés mást ad
my $count  = @langs;                    # skalár kontextus -> 3
my ($head) = @langs;                    # lista kontextus -> 'Perl'
say 'Elemek száma: ' . @langs;          # konkatenáció skalár kontextust ad -> 3
say "Elemek: @langs";                   # interpoláció: szóközzel összefűzve

# Függvény, ami a hívó kontextusához igazodik
sub matches ($re, @items) {
    my @hits = grep { /$re/ } @items;
    return wantarray ? @hits : scalar @hits;   # lista vagy darabszám
}
my @found = matches(qr/^P/, @langs);    # ('Perl', 'PHP')
my $n     = matches(qr/^P/, @langs);    # 2
say "$n találat: @found";

# Klasszikus csapda: a localtime is kontextusfüggő
my $stamp = localtime;                  # "Sat Nov 21 10:00:00 2026"
my @parts = localtime;                  # (sec, min, hour, mday, mon, year, ...)
printf "%s | év: %d\n", $stamp, $parts[5] + 1900;

# scalar() kikényszeríti a skalár kontextust egy lista belsejében
my %info = (count => scalar(@langs), names => "@langs", head => $head, first => $first);
say "$_ => $info{$_}" for sort keys %info;
say "Szeletek: @two | @vers | ", join(',', %subset), " | $count";
```

## Referenciák
<!-- q: Hogyan működnek a referenciák és a dereferálás Perlben? -->
<!-- tags: references, dereference, arrayref, hashref, coderef, postfix deref, weaken -->

A referencia egy skalár, amely tömbre, hashre, függvényre vagy más skalárra mutat; `\@tomb`-bel vagy anonim konstruktorokkal (`[...]`, `{...}`, `sub {...}`) jön létre. Enélkül nem lehetne beágyazott adatszerkezetet építeni, és függvénynek tömböt "kilapítás" nélkül átadni. A dereferálásnak klasszikus (`@$ref`, `$ref->[0]`) és postfix (`$ref->@*`, 5.24+) formája van; az utóbbi balról jobbra olvasható. Buktató: a tömb másolása (`my @b = @a`) csak sekély másolat – a belső referenciák közösek maradnak –, a körkörös referenciák pedig memóriaszivárgást okoznak, amit `Scalar::Util::weaken` old meg.

```perl
use v5.36;
use Scalar::Util qw(weaken reftype);

my @matrix = ([1, 2, 3], [4, 5, 6]);           # tömb-referenciák tömbje
my $config = {                                  # anonim hash-ref
    db       => { host => 'localhost', port => 5432 },
    roles    => [qw(admin editor)],
    on_error => sub ($msg) { warn "HIBA: $msg\n" },   # kódreferencia
};

# Létrehozás a \ operátorral
my @list = (3, 1, 2);
my $aref = \@list;

# Dereferálás: klasszikus és postfix (5.24+)
say $aref->[0];                       # egy elem
say scalar @$aref;                    # teljes tömb, klasszikusan
say scalar $aref->@*;                 # ugyanaz postfix formában
say join ',', $config->{roles}->@*;
say $config->{db}{port};              # a második szinttől a nyíl elhagyható
$config->{on_error}->('kapcsolat bontva');

say ref($config), ' / ', ref($config->{on_error}), ' / ', reftype($aref);  # HASH / CODE / ARRAY

# Átadás referenciaként: a függvény helyben módosíthat, és nem lapul ki a lista
sub normalize ($rows) {
    $_->{name} = lc $_->{name} for @$rows;
    return scalar @$rows;
}
my @users = ({ name => 'ADMIN' }, { name => 'Guest' });
normalize(\@users);
say join ',', map { $_->{name} } @users;   # admin,guest

# Sekély másolat csapdája: a belső tömbök közösek!
my @shallow = @matrix;
$shallow[0][0] = 99;
say $matrix[0][0];                    # 99 – az eredeti is változott
my @deep = map { [@$_] } @matrix;     # egyszintű mély másolat

# Körkörös referencia: refcount sosem nullázódik -> weaken
my $parent = { name => 'root' };
my $child  = { name => 'leaf', parent => $parent };
$parent->{child} = $child;
weaken($child->{parent});             # gyenge ref: nem növeli a refcountot
say scalar @deep;
```

## Összetett adatszerkezetek és autovivification
<!-- q: Hogyan építsek hash of hashes és hash of arrays struktúrát Perlben? -->
<!-- tags: data structures, hash of arrays, hash of hashes, autovivification, data dumper, json -->

Referenciák egymásba ágyazásával tetszőleges mélységű struktúra építhető: hash of arrays (`$h{kulcs}[i]`), hash of hashes (`$h{a}{b}`), tömb hash-ekből (rekordlista). Az autovivification a hiányzó köztes szinteket automatikusan létrehozza írásnál (`$stats{$user}{count}++`), ami számlálásnál és csoportosításnál rendkívül tömör kódot ad. A struktúra a `Data::Dumper`-rel vagy a core `JSON::PP`-vel vizsgálható és szerializálható. Buktató: az autovivification *olvasásnál* is létrehozhat szinteket (`exists $h{x}{y}` létrehozza a `$h{x}`-et), ezért lépcsőzetesen ellenőrizz, vagy használd a `no autovivification` CPAN pragmát.

```perl
use v5.36;
use Data::Dumper;
use JSON::PP;
$Data::Dumper::Sortkeys = 1;
$Data::Dumper::Indent   = 1;

my @log = (
    'user1 GET /index 200',
    'user2 POST /login 401',
    'user1 GET /cart 200',
    'user2 POST /login 200',
    'user1 GET /index 304',
);

# { user => { count => N, paths => { path => db }, codes => [...], errors => [...] } }
my %stats;
for my $line (@log) {
    my ($user, $method, $path, $code) = split ' ', $line;
    $stats{$user}{count}++;                    # autovivification: a hash magától létrejön
    $stats{$user}{paths}{$path}++;
    push $stats{$user}{codes}->@*, $code;      # a tömb-ref is magától létrejön
    push @{ $stats{$user}{errors} }, $line if $code >= 400;
}

# Bejárás: kérésszám szerint csökkenő, egyezésnél név szerint
for my $user (sort { $stats{$b}{count} <=> $stats{$a}{count} or $a cmp $b } keys %stats) {
    my $s = $stats{$user};
    my ($top) = sort { $s->{paths}{$b} <=> $s->{paths}{$a} or $a cmp $b } keys $s->{paths}->%*;
    printf "%-6s %d kérés, leggyakoribb: %-7s hibák: %d\n",
        $user, $s->{count}, $top, scalar @{ $s->{errors} // [] };
}

# Hash of arrays: sorok státuszkód szerint csoportosítva
my %by_code;
push @{ $by_code{ (split ' ')[3] } }, $_ for @log;
say "$_: ", scalar @{ $by_code{$_} } for sort keys %by_code;

# Létezés-ellenőrzés autovivification nélkül: lépcsőzetesen
my $has = exists $stats{user3} && exists $stats{user3}{paths};
say exists $stats{user3} ? 'user3 létrejött!' : 'user3 nem jött létre';

print Dumper(\%stats);
say JSON::PP->new->canonical->pretty->encode($stats{user1});
```

## Reguláris kifejezések: nevesített csoportok és /x
<!-- q: Hogyan írjak olvasható, összetett regexet Perlben nevesített csoportokkal? -->
<!-- tags: regex, named captures, qr, x modifier, global match, non-greedy, parsing -->

A `qr//` előfordított regexet ad, ami változóban tárolható és más mintákba ágyazható. Az `/x` módosító engedi a szóközöket és kommenteket a mintában, így a bonyolult minta is olvasható; a nevesített csoportok (`(?<nev>...)`) eredménye a `%+` hashben érhető el. Lista kontextusban a `//g` az összes találatot visszaadja, párokból akár közvetlenül hash is építhető. Buktató: a `.*` mohó, és a lehető leghosszabb illeszkedést adja – HTML-szerű szövegnél `.*?` (nem mohó) vagy negált karakterosztály (`[^<]*`) kell; ékezetes szöveghez `use utf8` és megfelelő I/O réteg szükséges.

```perl
use v5.36;
use utf8;                                   # a forrásban lévő stringek UTF-8 karakterek
binmode STDOUT, ':encoding(UTF-8)';

# /x: szóközök és kommentek a mintában; (?<név>...) nevesített csoport
my $log_re = qr{
    ^ (?<ip> \d{1,3} (?: \.\d{1,3} ){3} ) \s+       # IPv4 cím
    \[ (?<ts> [^\]]+ ) \] \s+                       # időbélyeg szögletes zárójelben
    " (?<method> GET|POST|PUT|DELETE ) \s+
      (?<path> \S+ ) [^"]* " \s+                    # kérés sora
    (?<status> \d{3} ) \s+
    (?<bytes> \d+ | - )                             # méret vagy kötőjel
}x;

my @lines = (
    '10.0.0.1 [21/Nov/2026:10:00:01 +0100] "GET /api/items?page=2 HTTP/1.1" 200 5120',
    '10.0.0.2 [21/Nov/2026:10:00:02 +0100] "POST /login HTTP/1.1" 401 -',
    'hibás sor',
);

for (@lines) {
    unless (/$log_re/) { warn "Nem illeszkedik: $_\n"; next }
    my %rec = %+;                           # a nevesített találatok másolata
    $rec{bytes} = 0 if $rec{bytes} eq '-';
    printf "%-9s %-6s %-20s %s %6d\n", @rec{qw(ip method path status bytes)};
}

# Lista kontextusban a //g minden találatot visszaad
my $text = 'Ár: 1200 Ft, szállítás: 990 Ft, kedvezmény: -300 Ft';
my @amounts = $text =~ /(-?\d+)\s*Ft/g;    # (1200, 990, -300)
my $sum = 0;
$sum += $_ for @amounts;
say "Összesen: $sum Ft";

# Párokból közvetlenül hash
my %kv = 'host=db1;port=5432;user=app' =~ /(\w+)=([^;]+)/g;
say join ', ', map { "$_=$kv{$_}" } sort keys %kv;

# Nem mohó kvantor: a legrövidebb illeszkedés
my $html = '<b>egy</b> és <b>kettő</b>';
my @bold = $html =~ m{<b>(.*?)</b>}g;      # ('egy', 'kettő'); .* esetén egy hosszú találat
say "@bold";

# Unicode tulajdonság: \p{L} bármely betű, ékezetesek is
my @words = 'Árvíztűrő tükörfúrógép 2026' =~ /(\p{L}+)/g;
say scalar(@words), ' szó';
```

## Reguláris kifejezések: haladó technikák
<!-- q: Hogyan használjak lookaroundot, s///e-t, tr-t és \G alapú lexert Perlben? -->
<!-- tags: regex, lookahead, lookbehind, substitution, tr, lexer, pos -->

A lookahead/lookbehind (`(?=...)`, `(?<=...)`) feltételt vizsgál karakterek "elfogyasztása" nélkül – így egyetlen regexben ellenőrizhető több jelszószabály, vagy beszúrható ezres elválasztó. Az `s///e` a cserét Perl-kódként értékeli ki (sablonmotor, számítás), az `s///r` pedig új stringet ad vissza az eredeti módosítása nélkül. A `tr///` nem regex, hanem karakterenkénti fordítótábla, nagyon gyors, és visszaadja a darabszámot. A `\G` + `/gc` párossal lexert írhatsz, amely ott folytatja, ahol az előző illeszkedés véget ért (`pos`). Buktató: katasztrofális visszalépés (`(a+)+$`) exponenciális futásidőt okozhat – használj atomi csoportot (`(?>...)`) vagy possessive kvantort (`a++`).

```perl
use v5.36;
use utf8;
binmode STDOUT, ':encoding(UTF-8)';

# Lookahead: több jelszószabály egyetlen regexben
my $strong = qr/^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[^\w\s]).{12,}$/;
say 'Abcdef123456!' =~ $strong ? 'erős' : 'gyenge';

# Lookbehind + lookahead: ezres elválasztó beszúrása
(my $num = '1234567890') =~ s/(?<=\d)(?=(?:\d{3})+$)/ /g;
say $num;                                    # 1 234 567 890

# s///e + s///r: sablon kitöltése, ismeretlen kulcs érintetlen marad
my $tpl  = 'Kedves {name}, egyenleged: {balance} Ft.';
my %vars = (name => 'Felhasználó', balance => 15000);
my $out  = $tpl =~ s{\{(\w+)\}}{ $vars{$1} // "{$1}" }ger;
say $out;

# Árak bruttósítása helyben, számítással
my $prices = 'alma 100, körte 250, szilva 80';
$prices =~ s/(\d+)/sprintf('%.0f', $1 * 1.27)/ge;
say $prices;

# tr///: karakterenkénti csere és számlálás
(my $ascii = 'árvíztűrő tükörfúrógép') =~ tr/áéíóöőúüű/aeiooouuu/;
my $vowels = ($ascii =~ tr/aeiou//);         # csak számol
say "$ascii ($vowels magánhangzó)";

# \G + /gc lexer: ott folytatja, ahol az előző illeszkedés véget ért
sub tokenize ($src) {
    my @tok;
    for ($src) {                              # $_ aliasolása a forrásra
        while (1) {
            if    (/\G\s+/gc)                { next }
            elsif (/\G(\d+(?:\.\d+)?)/gc)    { push @tok, [NUM => $1] }
            elsif (/\G([A-Za-z_]\w*)/gc)     { push @tok, [ID  => $1] }
            elsif (/\G([-+*\/()=])/gc)       { push @tok, [OP  => $1] }
            elsif (/\G\z/gc)                 { last }
            else  { die 'Váratlan karakter a(z) ' . pos() . ". pozíción\n" }
        }
    }
    return @tok;
}
say join ' ', map { "$_->[0]:$_->[1]" } tokenize('x = 3.14 * (r + 2)');

# Atomi csoport: nincs visszalépés -> gyors kudarc patológikus inputon
my $evil = ('a' x 30) . 'b';
say $evil =~ /^(?>a+)+$/ ? 'illeszkedik' : 'gyorsan elutasítva';
```

## Szubrutinok, szignatúrák és closure-ök
<!-- q: Hogyan írjak szubrutinokat szignatúrákkal és closure-ökkel Perlben? -->
<!-- tags: subroutines, signatures, closures, state, local, higher-order functions, memoization -->

A Perl 5.36-tól stabil szignatúrák (`sub f ($x, $y = 10, %opt)`) a régi `my ($x) = @_;` mintát váltják ki, és ellenőrzik az argumentumszámot. A névtelen `sub` closure: befogja a lexikális változókat, így privát állapotú függvénygyárak (rate limiter, számláló) készíthetők, a `state` pedig hívások között megőrzött, egyszer inicializált változót ad (memoizálás). A `local` dinamikus hatókörrel ideiglenesen felülír egy csomagváltozót, ami a hívott függvényekben is látszik. Buktató: a `@_` elemei aliasok – módosításuk a hívó változóját is módosítja –, és a `return` nélküli sub az utolsó kifejezés értékét adja vissza.

```perl
use v5.36;

# Szignatúra: kötelező, alapértelmezett és "slurpy" hash paraméter
sub fetch_page ($url, $timeout = 10, %opt) {
    my $retries = $opt{retries} // 3;          # // = defined-or
    return "GET $url (timeout=$timeout, retries=$retries)";
}
say fetch_page('/api', 5, retries => 1);

# Closure: privát állapot a névtelen sub-ban
sub make_rate_limiter ($max_per_sec) {
    my @stamps;
    return sub {
        my $now = time;
        @stamps = grep { $now - $_ < 1 } @stamps;   # 1 mp-nél régebbiek ki
        return 0 if @stamps >= $max_per_sec;
        push @stamps, $now;
        return 1;
    };
}
my $limiter = make_rate_limiter(3);
say join ',', map { $limiter->() } 1 .. 5;      # 1,1,1,0,0

# state: egyszer inicializálódik, hívások között megmarad -> memoizálás
sub fib ($n) {
    state %cache;
    return $n if $n < 2;
    return $cache{$n} //= fib($n - 1) + fib($n - 2);
}
say fib(80);                                    # 23416728348467685

# Magasabb rendű függvény: kompozíció (jobbról balra)
sub compose (@fns) {
    return sub (@args) {
        @args = $_->(@args) for reverse @fns;
        return wantarray ? @args : $args[0];
    };
}
my $slugify = compose(
    sub ($s) { $s =~ s/^-+|-+$//gr },
    sub ($s) { $s =~ s/[^a-z0-9]+/-/gr },
    sub ($s) { lc $s },
);
say $slugify->('  Hello Perl World! ');        # hello-perl-world

# local: dinamikus hatókör – a hívott függvények is az új értéket látják
our $DEBUG = 0;
sub log_debug ($msg) { say "[debug] $msg" if $DEBUG }
sub risky_operation { local $DEBUG = 1; log_debug('csak itt látszik') }
risky_operation();
log_debug('ez már nem jelenik meg');
```

## Fájlkezelés és hibakezelés
<!-- q: Hogyan kezeljem biztonságosan a fájlokat és a kivételeket Perlben? -->
<!-- tags: file io, open, autodie, eval, die, try catch, exceptions -->

Fájlt mindig háromargumentumos `open`-nel és lexikális fájlkezelővel nyiss (`open my $fh, '<:encoding(UTF-8)', $path`), a kódolási réteg megadásával; az `autodie` pragma minden I/O hibánál automatikusan kivételt dob, így nem maradhat ellenőrizetlen `open`. A kivétel a `die` (akár objektummal), az elkapás klasszikusan `eval { }` + `$@`, Perl 5.40-től stabil `try/catch` szintaxissal. Strukturált hibához saját kivételosztály ajánlott, amit `isa`-val lehet szétválogatni. Buktató: a `$@`-t azonnal mentsd el, mert egy közbeeső destruktor vagy `eval` felülírhatja.

```perl
use v5.36;
use utf8;
use autodie;                      # open/close/... hibánál automatikus die
use File::Temp qw(tempfile);
binmode $_, ':encoding(UTF-8)' for \*STDOUT, \*STDERR;

# Egyszerű kivételosztály: strukturált hiba string helyett
package App::Error {
    sub new ($class, %args) { return bless {%args}, $class }
    sub message ($self)     { return $self->{message} }
    sub throw ($class, %args) { die $class->new(%args) }
}

package main;

sub parse_config ($path) {
    open my $fh, '<:encoding(UTF-8)', $path;        # 3 argumentum, lexikális fh, réteg
    my %cfg;
    while (my $line = <$fh>) {
        chomp $line;
        next if $line =~ /^\s*(?:#|$)/;              # komment vagy üres sor
        my ($k, $v) = $line =~ /^\s*(\w+)\s*=\s*(.*?)\s*$/
            or App::Error->throw(message => "Hibás sor ($.): $line", line => $.);
        $cfg{$k} = $v;                               # $. = aktuális sorszám
    }
    close $fh;
    return \%cfg;
}

# Tesztfájl készítése
my ($tmp, $file) = tempfile(UNLINK => 1);
binmode $tmp, ':encoding(UTF-8)';
print {$tmp} "# beállítások\nhost = localhost\nport=5432\nrossz sor\n";
close $tmp;

# eval-blokk: a $@-t AZONNAL mentsd el
my $cfg = eval { parse_config($file) };
if (my $err = $@) {
    if (ref $err && $err->isa('App::Error')) {
        warn 'Konfig hiba: ', $err->message, "\n";
    } else {
        die $err;                                    # ismeretlen hiba továbbdobása
    }
}

# Perl 5.40+: stabil, beépített try/catch/finally
use feature 'try';
no warnings 'experimental::try';                     # 5.34–5.38-on még kísérleti volt
try {
    parse_config('/nem/letezo/fajl.conf');
}
catch ($e) {
    say 'autodie hiba: ', (split /\n/, "$e")[0];
}
```

## Objektumorientált Perl bless-szel
<!-- q: Hogyan írjak osztályokat és öröklést bless-szel Perlben? -->
<!-- tags: oop, bless, package, inheritance, SUPER, can, isa, classes -->

Perlben az osztály egy csomag (`package`), az objektum egy "megáldott" referencia (`bless {...}, $class`), a metódus pedig olyan szubrutin, amely első paraméterként az objektumot (vagy az osztálynevet) kapja. Az öröklést az `@ISA` tömb adja, amit a `use parent` állít be; az ős metódusa `SUPER::`-rel hívható, a `can` és `isa` futásidejű vizsgálatot tesz lehetővé. A konstruktorban érdemes hook metódust (`_init`) hívni, hogy a leszármazottak csak a saját mezőiket kezeljék. Buktató: a hash-alapú objektum mezőnevének elgépelése csendben új kulcsot hoz létre – ezért nagyobb kódban Moo/Moose vagy az 5.38+ natív `class`/`field`/`method` szintaxis ajánlott.

```perl
use v5.36;
use utf8;
binmode STDOUT, ':encoding(UTF-8)';

package Shape {
    use Carp qw(croak);
    my $count = 0;                                 # osztályszintű privát állapot

    sub new ($class, %args) {
        my $self = bless { name => $args{name} // 'névtelen' }, $class;
        $self->_init(%args);                       # leszármazott hook
        $count++;
        return $self;
    }
    sub _init { }                                  # alapból üres
    sub area ($self) { croak ref($self) . ' nem implementálja az area()-t' }
    sub describe ($self) { sprintf '%s (%s): %.2f', $self->{name}, ref $self, $self->area }
    sub count ($class) { $count }
}

package Circle {
    use parent -norequire, 'Shape';               # öröklés (@ISA beállítása)
    use Carp qw(croak);
    use constant PI => 4 * atan2(1, 1);

    sub _init ($self, %args) {
        croak 'r kötelező és pozitív' unless ($args{r} // 0) > 0;
        $self->{r} = $args{r};
    }
    sub area ($self) { PI * $self->{r}**2 }
}

package Rect {
    use parent -norequire, 'Shape';

    sub _init ($self, %args) { @$self{qw(w h)} = @args{qw(w h)} }
    sub area ($self) { $self->{w} * $self->{h} }
    sub describe ($self) {
        my $base = $self->SUPER::describe();      # ős metódusának hívása
        return "$base [$self->{w}x$self->{h}]";
    }
}

package main;

my @shapes = (
    Circle->new(name => 'kör', r => 2),
    Rect->new(name => 'téglalap', w => 3, h => 4),
);
say $_->describe for sort { $a->area <=> $b->area } @shapes;
say 'Létrehozva: ', Shape->count;
say Circle->can('describe') ? 'Circle tud describe-ot' : 'nem tud';
say $shapes[0]->isa('Shape') ? 'Shape leszármazott' : 'idegen';

# Accessor-generálás typeglobbal (ezt automatizálja a Moose/Moo)
for my $field (qw(name)) {
    no strict 'refs';
    *{"Shape::$field"} = sub ($self) { $self->{$field} };
}
say $shapes[1]->name;

# Dinamikus metódushívás névvel
my $method = 'area';
printf "%.2f\n", $shapes[0]->$method;
```

## Modern OO Moose-zal
<!-- q: Hogyan használjam a Moose-t attribútumokkal, típusokkal és role-okkal Perlben? -->
<!-- tags: moose, moo, roles, attributes, type constraints, method modifiers, oop -->

A Moose deklaratív OO-réteg: a `has` attribútumot definiál (accessor, kötelezőség, alapérték, típusellenőrzés, lusta builder), a `extends` örököltet, a `with` role-t komponál, a `before`/`after`/`around` metódus-módosítók pedig keresztmetszeti logikát (audit, validálás) adnak az eredeti kód érintése nélkül. A role (`Moose::Role`) újrahasznosítható viselkedés `requires`-zel deklarált elvárásokkal – a többszörös öröklés biztonságos alternatívája. A Moo könnyebb, gyorsabban induló, nagyrészt kompatibilis változat. Buktató: referencia-alapértéket (`[]`, `{}`) mindig `sub { [] }` formában adj meg, különben minden példány ugyanazt a tömböt kapja, és az osztály végén hívd meg a `make_immutable`-t a gyors konstruktorért.

```perl
package Role::Auditable;
use Moose::Role;

requires 'owner';                                 # a fogyasztó osztálynak kell owner metódus

# Metódus-módosító: a withdraw ELŐTT fut, az eredeti kód érintése nélkül
before withdraw => sub {
    my ($self, $amount) = @_;
    printf "[audit] %s: kivét %.2f\n", $self->owner, $amount;
};

package BankAccount;
use Moose;
use Moose::Util::TypeConstraints;
use namespace::autoclean;                         # importok ne legyenek metódusok

subtype 'PositiveNum', as 'Num', where { $_ > 0 }, message { "Pozitív szám kell, kaptam: $_" };

has owner   => (is => 'ro', isa => 'Str', required => 1);
has balance => (is => 'ro', isa => 'Num', default => 0, writer => '_set_balance');
has history => (
    is      => 'ro',
    isa     => 'ArrayRef[HashRef]',
    default => sub { [] },                        # referencia-default MINDIG sub-ban!
    traits  => ['Array'],
    handles => { _log => 'push', entries => 'elements', entry_count => 'count' },
);
has fee => (is => 'ro', isa => 'CodeRef', lazy => 1, builder => '_build_fee');

sub _build_fee { return sub { 0 } }               # lusta builder: első használatkor fut

sub deposit {
    my ($self, $amount) = @_;
    find_type_constraint('PositiveNum')->assert_valid($amount);
    $self->_set_balance($self->balance + $amount);
    $self->_log({ type => 'deposit', amount => $amount });
    return $self;                                 # láncolható
}

sub withdraw {
    my ($self, $amount) = @_;
    find_type_constraint('PositiveNum')->assert_valid($amount);
    my $total = $amount + $self->fee->($amount);
    die "Nincs elég fedezet\n" if $total > $self->balance;
    $self->_set_balance($self->balance - $total);
    $self->_log({ type => 'withdraw', amount => $total });
    return $self;
}

with 'Role::Auditable';                           # a metódusok definiálása UTÁN komponáljuk
__PACKAGE__->meta->make_immutable;

package SavingsAccount;
use Moose;
extends 'BankAccount';

has '+fee' => (default => sub { sub { $_[0] * 0.01 } });   # örökölt attribútum felülírása

around withdraw => sub {
    my ($orig, $self, $amount) = @_;
    die "Havonta legfeljebb 3 tranzakció\n" if $self->entry_count >= 3;
    return $self->$orig($amount);                 # az eredeti metódus hívása
};
__PACKAGE__->meta->make_immutable;

package main;
my $acc = SavingsAccount->new(owner => 'Teszt Ügyfél');
$acc->deposit(1000)->withdraw(200);
printf "Egyenleg: %.2f, tételek: %d\n", $acc->balance, $acc->entry_count;
```

## Listaműveletek: sort, map, grep és Schwartzian transform
<!-- q: Hogyan rendezzek és alakítsak át listákat hatékonyan Perlben? -->
<!-- tags: sort, map, grep, schwartzian transform, list util, functional, sorting -->

A `map`, `grep` és `sort` láncolása (jobbról balra olvasva) a Perl funkcionális gerince; a `sort` blokkja a `$a`/`$b` csomagváltozókkal dolgozik, és az `or`/`||` láncolással többkulcsos rendezés adható meg. Ha a rendezési kulcs kiszámítása drága (regex, fájlrendszer-hívás), a Schwartzian transform egyszer számolja ki minden elemre: map → sort → map. A core `List::Util` modul `sum0`, `max`, `first`, `reduce`, `any`, `uniq` függvényei rövidzárral és C-sebességgel dolgoznak. Buktató: a `map { {...} }` kétértelmű (blokk vagy hash?) – anonim hash visszaadásához írj `+{ ... }`-t.

```perl
use v5.36;
use utf8;
binmode STDOUT, ':encoding(UTF-8)';
use List::Util qw(sum0 max first reduce any uniq);

# +{ }: egyértelműen anonim hash (nem blokk)
my @files = map { +{ name => "file$_." . ($_ % 2 ? 'log' : 'txt'), size => ($_ * 1337) % 10_000 } } 1 .. 8;

# map/grep lánc: jobbról balra olvasd
my @big_names = map { $_->{name} } grep { $_->{size} > 5_000 } @files;
say "Nagy fájlok: @big_names";

# Többkulcsos rendezés: méret szerint csökkenő, egyezésnél név szerint
my @sorted = sort { $b->{size} <=> $a->{size} or $a->{name} cmp $b->{name} } @files;
say join ', ', map { "$_->{name}($_->{size})" } @sorted[0 .. 2];

# Schwartzian transform: a drága kulcs (regex) elemenként egyszer számolódik
my @versions = qw(v1.10.0 v1.2.3 v1.2.10 v2.0.0 v1.9.9);
my @by_semver =
    map  { $_->[0] }                                           # 3. vissza az eredetire
    sort { $a->[1] <=> $b->[1] || $a->[2] <=> $b->[2] || $a->[3] <=> $b->[3] }  # 2. rendezés
    map  { [ $_, /^v(\d+)\.(\d+)\.(\d+)$/ ] }                  # 1. [eredeti, kulcsok...]
    @versions;
say "@by_semver";                       # v1.2.3 v1.2.10 v1.9.9 v1.10.0 v2.0.0

# List::Util (core)
say 'Össz méret: ', sum0 map { $_->{size} } @files;
my $largest   = reduce { $a->{size} > $b->{size} ? $a : $b } @files;
my $first_big = first { $_->{size} > 9_000 } @files;           # megáll az első találatnál
say "Legnagyobb: $largest->{name}; első 9000 feletti: ", $first_big ? $first_big->{name} : 'nincs';
say 'Van üres fájl' if any { $_->{size} == 0 } @files;
my @ext = uniq map { $_->{name} =~ /\.(\w+)$/ ? $1 : () } @files;
say "Kiterjesztések: @ext";

# Szógyakoriság, top 3 érték szerint
my %wc;
$wc{ lc $_ }++ for 'A perl a regex Perl a lista' =~ /\w+/g;
my @top = (sort { $wc{$b} <=> $wc{$a} || $a cmp $b } keys %wc)[0 .. 2];
say join ', ', map { "$_=$wc{$_}" } @top;
say 'Leghosszabb szó: ', max map { length } keys %wc;
```

## Modulok, CPAN és tesztelés
<!-- q: Hogyan írjak saját Perl modult, kezeljem a CPAN függőségeket és teszteljek? -->
<!-- tags: modules, cpan, exporter, cpanfile, carton, test more, pod -->

Egy modul egy `.pm` fájl, amelynek csomagneve a fájlútvonalat követi (`My::Text::Util` → `lib/My/Text/Util.pm`); az `Exporter` `@EXPORT_OK` listája szabályozza, mit importálhat a hívó (az `@EXPORT` automatikus exportja kerülendő, mert szennyezi a névteret). A dokumentáció POD formátumban a kódba ágyazva él (`perldoc`). A függőségeket `cpanfile` írja le, a `cpanm --installdeps .` vagy a reprodukálható `carton install` telepíti őket; teszteléshez a core `Test::More` és a `prove` futtató szolgál. Buktató: a modulnak régebbi Perl-en igaz értékkel (`1;`) kell végződnie – 5.38+ alatt a `use v5.38` ezt feleslegessé teszi.

```perl
# lib/My/Text/Util.pm – saját modul
package My::Text::Util;
use v5.36;
use Exporter 'import';                  # import() átvétele öröklés nélkül

our $VERSION     = '0.03';
our @EXPORT_OK   = qw(slugify truncate_words);
our %EXPORT_TAGS = (all => \@EXPORT_OK); # use My::Text::Util ':all'

sub slugify ($s) {
    $s = lc $s;
    $s =~ s/[^a-z0-9]+/-/g;
    $s =~ s/^-|-$//g;
    return $s;
}

sub truncate_words ($text, $max = 10) {
    my @w = split ' ', $text;
    return @w <= $max ? $text : join(' ', @w[0 .. $max - 1]) . '...';
}

1;   # igaz visszatérési érték (5.38+ "use v5.38" mellett nem kötelező)

__END__

=head1 NAME

My::Text::Util - egyszerű szövegsegédek

=head1 SYNOPSIS

  use My::Text::Util qw(slugify);
  say slugify('Hello World');   # hello-world

=cut
```

```perl
# t/util.t – futtatás: prove -lv t/
use v5.36;
use Test::More;
use My::Text::Util qw(:all);

is slugify('  Hello, Perl World! '), 'hello-perl-world', 'slugify alapeset';
is truncate_words('a b c d', 2), 'a b...', 'levágás szóhatáron';
is truncate_words('rövid', 5), 'rövid', 'rövid szöveg változatlan';
is_deeply [map { slugify($_) } 'A B', 'C'], ['a-b', 'c'], 'listán is működik';
ok !defined eval { My::Text::Util::slugify(); 1 }, 'hiányzó argumentum hibát dob';

done_testing;
```

```perl
# cpanfile – telepítés: cpanm --installdeps .   vagy reprodukálhatóan: carton install
requires 'perl', '5.036';
requires 'Moose', '>= 2.2200';
requires 'Mojolicious', '>= 9.0, < 10.0';

on 'test' => sub {
    requires 'Test::More', '>= 1.302';
};
```

## Egysoros parancsok (one-liners)
<!-- q: Hogyan használjam a Perlt egysoros parancsokként szövegfeldolgozásra? -->
<!-- tags: one-liner, command line, perl -ne, perl -pi, autosplit, text processing, sed awk -->

A Perl parancssori kapcsolói a `sed` és `awk` erősebb helyettesítőjévé teszik: `-n` soronkénti ciklust ír a kód köré, `-p` ugyanezt a sor kiírásával, `-l` kezeli a sorvégeket, `-a` szóközök (vagy `-F` szerinti elválasztó) mentén a `@F` tömbbe bont, `-i` helyben szerkeszt (opcionális backup kiterjesztéssel). Az `END { }` blokk a feldolgozás után fut – összesítésre ideális, a flip-flop operátor (`/A/ .. /B/`) pedig két minta közötti tartományt választ ki. Buktató: Windows `cmd`-ben a parancsot dupla idézőjelbe kell tenni, és a `-i` backup nélkül visszavonhatatlanul felülírja a fájlt.

```bash
# Oszlop összegzése: -a autosplit a @F-be, END a végén fut
perl -lane '$sum += $F[2]; END { print $sum }' sales.txt

# Helyben szerkesztés biztonsági mentéssel (.bak)
perl -i.bak -pe 's{http://}{https://}g' config/*.conf

# CSV 3. oszlopának gyakorisága csökkenő sorrendben
perl -F, -lane '$c{$F[2]}++; END { print "$c{$_}\t$_" for sort { $c{$b} <=> $c{$a} } keys %c }' data.csv

# Bekezdés mód (-00): üres sorral elválasztott blokkok, amelyekben ERROR van
perl -00 -ne 'print if /ERROR/' app.log

# Tartomány két minta között (flip-flop operátor)
perl -ne 'print if /^BEGIN/ .. /^END/' report.txt

# Teljes fájl egyben (-0777) és JSON szépítés core modullal
perl -MJSON::PP -0777 -ne 'print JSON::PP->new->pretty->encode(decode_json($_))' data.json
```

```perl
# Amit a `perl -lane 'KÓD'` valójában futtat (megnézhető: perl -MO=Deparse -lane 'KÓD'):
BEGIN { $/ = "\n"; $\ = "\n"; }                  # -l: bemeneti sorvég + kimeneti sorvég
LINE: while (defined($_ = readline ARGV)) {      # -n: ciklus a fájlokon / STDIN-en
    chomp $_;                                    # -l: sorvég levágása
    our @F = split(' ', $_, 0);                  # -a: autosplit (-F, esetén vessző mentén)
    # ... KÓD ...
}
# -p esetén a ciklus végén még: print $_;  -i esetén a kimenet a fájlba íródik vissza

# Ugyanez szkriptként, ha a one-liner túl hosszúra nőne: státuszkódok aránya egy access logban
use strict;
use warnings;
my (%codes, $total);
while (my $line = <>) {                          # <> = minden argumentum-fájl vagy STDIN
    next unless $line =~ /" (\d{3}) /;
    $codes{$1}++;
    $total++;
}
printf "%s: %5.1f%%\n", $_, 100 * $codes{$_} / $total for sort keys %codes;
```
