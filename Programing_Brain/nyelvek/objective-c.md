# Objective-C
<!-- tech: objective-c -->
<!-- aliases: objc -->

Az Objective-C a C nyelv szigorú bővítése Smalltalk-stílusú üzenetküldéssel és erősen dinamikus futtatókörnyezettel (runtime): a metódushívás futásidőben, szelektor alapján dől el. Évtizedekig az Apple platformok (macOS, iOS) fő nyelve volt, a Foundation és UIKit/AppKit keretrendszerek ma is erre épülnek; memóriakezelése ARC (automatikus referenciaszámlálás). Ma elsősorban meglévő kódbázisok karbantartásához, C/C++ könyvtárak Swift felé történő becsomagolásához és runtime-trükkökhöz (swizzling, dinamikus proxyk) használják. Új Apple-fejlesztéshez a Swift az ajánlott, mert biztonságosabb (optionalök, értéktípusok, fordítási idejű konkurencia-ellenőrzés).

## Osztályok, property-k és inicializálók
<!-- q: Hogyan definiáljak osztályt property-kkel és inicializálóval Objective-C-ben? -->
<!-- tags: class, interface, implementation, property, designated initializer, copy, nonatomic -->

Egy osztály két részből áll: a `.h` fejlécben lévő `@interface` a publikus API, a `.m` fájlban lévő `@implementation` a megvalósítás. A property-attribútumok határozzák meg a generált getter/setter viselkedését: `nonatomic` (gyorsabb, nincs zár), `strong`/`weak`/`copy` (tulajdonviszony), `readonly`. Mutábilis párral rendelkező típusoknál (NSString, NSArray, blokkok) mindig `copy` kell, különben a hívó később módosíthatja a „mi” értékünket. Az inicializálóban és a `dealloc`-ban közvetlenül az `_ivar`-t használd a setter helyett, a kijelölt inicializálót pedig `NS_DESIGNATED_INITIALIZER` jelölje.

```objective-c
// Termek.h — publikus interfész
#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

@interface Termek : NSObject <NSCopying>

@property (nonatomic, copy, readonly) NSString *sku;     // copy: NSMutableString-et is lemásol
@property (nonatomic, copy) NSString *nev;
@property (nonatomic, assign) NSInteger arFillerben;      // primitív -> assign
@property (nonatomic, strong, nullable) NSDate *akcioVege;

// Kijelölt (designated) inicializáló: minden más init ezt hívja.
- (instancetype)initWithSku:(NSString *)sku nev:(NSString *)nev ar:(NSInteger)ar NS_DESIGNATED_INITIALIZER;
- (instancetype)init NS_UNAVAILABLE;                     // a paraméter nélküli init tiltása
+ (instancetype)termekWithSku:(NSString *)sku nev:(NSString *)nev ar:(NSInteger)ar;  // gyári metódus

- (BOOL)akciosAdottNapon:(NSDate *)nap;

@end

NS_ASSUME_NONNULL_END

// Termek.m — megvalósítás
#import "Termek.h"

// Class extension: a readonly property belül readwrite-ra bővül.
@interface Termek ()
@property (nonatomic, copy, readwrite) NSString *sku;
@end

@implementation Termek

- (instancetype)initWithSku:(NSString *)sku nev:(NSString *)nev ar:(NSInteger)ar {
    self = [super init];          // mindig a szülő inicializálója először
    if (self) {
        _sku = [sku copy];        // init-ben közvetlen ivar-hozzáférés, nem setter!
        _nev = [nev copy];
        _arFillerben = ar;
    }
    return self;
}

+ (instancetype)termekWithSku:(NSString *)sku nev:(NSString *)nev ar:(NSInteger)ar {
    return [[self alloc] initWithSku:sku nev:nev ar:ar];   // self = az aktuális (al)osztály
}

- (BOOL)akciosAdottNapon:(NSDate *)nap {
    return self.akcioVege != nil && [nap compare:self.akcioVege] == NSOrderedAscending;
}

- (id)copyWithZone:(NSZone *)zone {
    Termek *masolat = [[[self class] allocWithZone:zone] initWithSku:self.sku
                                                                 nev:self.nev
                                                                  ar:self.arFillerben];
    masolat.akcioVege = self.akcioVege;
    return masolat;
}

- (NSString *)description {     // %@ formázáskor ez jelenik meg
    return [NSString stringWithFormat:@"<Termek %@: %@, %.2f Ft>",
            self.sku, self.nev, self.arFillerben / 100.0];
}

@end
```

## Üzenetküldés, szelektorok és objc_msgSend
<!-- q: Hogyan működik az üzenetküldés (objc_msgSend) és a szelektor Objective-C-ben? -->
<!-- tags: messaging, objc_msgSend, selector, SEL, IMP, respondsToSelector, nil messaging -->

A `[obj uzenet:arg]` kifejezés fordításkor `objc_msgSend(obj, @selector(uzenet:), arg)` hívássá válik: a runtime futásidőben keresi meg a szelektorhoz tartozó implementációt (IMP) — előbb az osztály metódus-cache-ében, majd az öröklési láncon. Ez teszi lehetővé a dinamikus viselkedést (szelektor mint érték, `respondsToSelector:`, továbbítás), de minden hívás egy indirekció. A nil-nek küldött üzenet nem hiba: 0/nil/NO-t ad vissza, ami kényelmes, de elrejtheti a hibákat. Ismeretlen szelektorra „unrecognized selector sent to instance” kivétel jön.

```objective-c
#import <Foundation/Foundation.h>
#import <objc/message.h>

@interface Kalkulator : NSObject
- (NSInteger)osszead:(NSInteger)a es:(NSInteger)b;
@end

@implementation Kalkulator
- (NSInteger)osszead:(NSInteger)a es:(NSInteger)b { return a + b; }
@end

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        Kalkulator *k = [Kalkulator new];

        // 1) Normál üzenet: a fordító objc_msgSend hívássá alakítja.
        NSInteger r1 = [k osszead:2 es:3];

        // 2) Ugyanez kézzel: objc_msgSend-et a PONTOS függvénytípusra kell castolni!
        NSInteger (*kuld)(id, SEL, NSInteger, NSInteger) = (void *)objc_msgSend;
        NSInteger r2 = kuld(k, @selector(osszead:es:), 2, 3);

        // 3) Szelektor mint érték: futásidőben választott művelet.
        SEL muvelet = NSSelectorFromString(@"osszead:es:");
        if ([k respondsToSelector:muvelet]) {
            // Közvetlen IMP: a dinamikus keresés megspórolható szoros ciklusokban.
            IMP imp = [k methodForSelector:muvelet];
            NSInteger (*f)(id, SEL, NSInteger, NSInteger) = (void *)imp;
            NSLog(@"IMP hívás: %ld", (long)f(k, muvelet, 10, 20));
        }

        // 4) nil-nek küldött üzenet NEM crashel: az eredmény 0.
        Kalkulator *semmi = nil;
        NSInteger r3 = [semmi osszead:1 es:1];

        // 5) Ismeretlen szelektor ellenőrzése küldés előtt.
        id dinamikus = k;
        if (![dinamikus respondsToSelector:@selector(length)]) {
            NSLog(@"a Kalkulator nem ismeri a -length üzenetet");
        }

        NSLog(@"%ld %ld %ld", (long)r1, (long)r2, (long)r3);   // 5 5 0
    }
    return 0;
}
```

## A runtime: dinamikus metódusok, swizzling, associated objectek
<!-- q: Hogyan használjam az Objective-C runtime-ot (method swizzling, associated objects, resolveInstanceMethod)? -->
<!-- tags: runtime, method swizzling, associated objects, class_addMethod, resolveInstanceMethod, objc/runtime.h -->

Az `objc/runtime.h` API-val futásidőben módosíthatók az osztályok: a `resolveInstanceMethod:` hiányzó metódust adhat hozzá (`class_addMethod`), a `method_exchangeImplementations` két implementációt cserél fel (swizzling — naplózáshoz, analitikához, hibakereséshez), az associated objectek pedig „tárolt property-t” adnak kategóriákhoz. A swizzlinget `+load`-ban, `dispatch_once`-szal végezzük, és a csere után a „saját” metódus hívása valójában az eredetit futtatja. Buktatók: a swizzling globális és nehezen debugolható, rendszerosztályokon (főleg class clusteren, pl. NSString) könnyen nem azt a metódust cseréli, amit gondolsz; a típuskódolásnak (`"@@:"`) pontosan egyeznie kell.

```objective-c
#import <Foundation/Foundation.h>
#import <objc/runtime.h>

// --- 1) Dinamikus metódusfeloldás ---
@interface Beallitasok : NSObject
@property (nonatomic, copy, readonly) NSString *tema;   // @dynamic: nincs generált getter
@end

static NSDictionary *tarolo;

static id dinamikusGetter(id self, SEL _cmd) {
    return tarolo[NSStringFromSelector(_cmd)];          // a szelektor neve a kulcs
}

@implementation Beallitasok
@dynamic tema;

+ (BOOL)resolveInstanceMethod:(SEL)sel {
    if (sel == @selector(tema)) {
        // "@@:" = visszatérés id, paraméterek: self (id), _cmd (SEL)
        class_addMethod(self, sel, (IMP)dinamikusGetter, "@@:");
        return YES;
    }
    return [super resolveInstanceMethod:sel];
}
@end

// --- 2) Method swizzling saját osztályon ---
@interface Szolgaltatas : NSObject
- (void)indit;
@end

@implementation Szolgaltatas
- (void)indit { NSLog(@"szolgáltatás indul"); }
@end

@implementation Szolgaltatas (Meres)
+ (void)load {                                   // osztálybetöltéskor fut
    static dispatch_once_t once;
    dispatch_once(&once, ^{
        Method eredeti = class_getInstanceMethod(self, @selector(indit));
        Method uj = class_getInstanceMethod(self, @selector(meres_indit));
        method_exchangeImplementations(eredeti, uj);
    });
}

- (void)meres_indit {
    CFAbsoluteTime t0 = CFAbsoluteTimeGetCurrent();
    [self meres_indit];                          // a csere után EZ hívja az eredeti -indit-et
    NSLog(@"indit: %.3f ms", (CFAbsoluteTimeGetCurrent() - t0) * 1000);
}
@end

// --- 3) Associated object: tárolt property kategóriában ---
@interface NSObject (Cimke)
@property (nonatomic, copy) NSString *cimke;
@end

@implementation NSObject (Cimke)
static char CimkeKulcs;                          // a címe egyedi kulcs

- (NSString *)cimke { return objc_getAssociatedObject(self, &CimkeKulcs); }
- (void)setCimke:(NSString *)cimke {
    objc_setAssociatedObject(self, &CimkeKulcs, cimke, OBJC_ASSOCIATION_COPY_NONATOMIC);
}
@end

int main(void) {
    @autoreleasepool {
        tarolo = @{@"tema": @"sötét"};
        NSLog(@"téma: %@", [Beallitasok new].tema);
        [[Szolgaltatas new] indit];
        NSObject *o = [NSObject new];
        o.cimke = @"debug";
        NSLog(@"címke: %@", o.cimke);
    }
    return 0;
}
```

## ARC és memóriakezelés
<!-- q: Hogyan működik az ARC Objective-C-ben (strong, weak, autoreleasepool, bridging)? -->
<!-- tags: arc, memory management, strong, weak, unsafe_unretained, autoreleasepool, bridge_transfer -->

Az ARC fordítási időben szúrja be a retain/release hívásokat a tulajdonviszony-jelölők alapján: `strong` (birtoklás), `weak` (nem birtokol, felszabaduláskor automatikusan nil lesz), `unsafe_unretained` (nem birtokol és NEM nullázódik — lógó pointer veszély). Az autoreleased ideiglenes objektumok az aktuális `@autoreleasepool` végén szabadulnak fel, ezért nagy ciklusokban iterációnkénti pool tartja alacsonyan a memóriacsúcsot. A Core Foundation objektumokat az ARC nem kezeli: a „toll-free bridging” castoknál `__bridge` (csak cast), `__bridge_transfer` (CF → ARC tulajdon) és `__bridge_retained` (ARC → CF, utána `CFRelease` kell) dönti el a tulajdont. ARC alatt `dealloc`-ban nem hívunk `[super dealloc]`-ot.

```objective-c
#import <Foundation/Foundation.h>

@class Osztaly;

@interface Diak : NSObject
@property (nonatomic, copy) NSString *nev;
@property (nonatomic, weak) Osztaly *osztaly;     // visszamutató: weak, nil-re áll felszabaduláskor
@end

@interface Osztaly : NSObject
@property (nonatomic, strong) NSMutableArray<Diak *> *diakok;   // birtoklás
@end

@implementation Diak
- (void)dealloc { NSLog(@"Diak dealloc: %@", _nev); }   // ARC: nincs [super dealloc]
@end

@implementation Osztaly
- (instancetype)init {
    if ((self = [super init])) { _diakok = [NSMutableArray array]; }
    return self;
}
- (void)dealloc { NSLog(@"Osztaly dealloc"); }
@end

int main(void) {
    @autoreleasepool {
        Osztaly *o = [Osztaly new];
        Diak *d = [Diak new];
        d.nev = @"Teszt";
        d.osztaly = o;
        [o.diakok addObject:d];
        o = nil;                                     // az Osztaly felszabadul
        NSLog(@"diák osztálya: %@", d.osztaly);      // (null) — a weak automatikusan nil lett
    }

    // Iterációnkénti pool: a sok ideiglenes objektum azonnal felszabadul.
    for (int i = 0; i < 100000; i++) {
        @autoreleasepool {
            NSString *sor = [NSString stringWithFormat:@"sor %d", i];
            (void)[sor uppercaseString];
        }
    }

    // Core Foundation <-> Foundation bridging ARC alatt.
    CFStringRef cf = CFStringCreateWithCString(NULL, "árvíztűrő", kCFStringEncodingUTF8); // +1 (Create)
    NSString *ns = (__bridge_transfer NSString *)cf;     // tulajdon átadása ARC-nak -> nincs CFRelease
    CFStringRef kolcsonzott = (__bridge CFStringRef)ns;  // csak cast, tulajdonváltás nélkül
    NSLog(@"%@ %ld", ns, (long)CFStringGetLength(kolcsonzott));
    return 0;
}
```

## Blokkok és a weak–strong tánc
<!-- q: Hogyan használjam a blokkokat Objective-C-ben, és hogyan kerüljem el a retain ciklust (weakSelf)? -->
<!-- tags: blocks, closures, __block, weak self, retain cycle, typedef, completion handler -->

A blokk (`^{ ... }`) Objective-C closure: befogja a használt változókat — objektumokat erősen, primitíveket érték szerint (másolatként). A `__block` jelölésű változó referencia szerint kerül be, így a blokkon belül módosítható. Ha egy objektum (közvetve) tárolja a blokkot, és a blokk erősen hivatkozik `self`-re, retain ciklus keletkezik; ezt a „weak–strong tánc” oldja meg: kívül `__weak typeof(self)`, belül `__strong` másolat és nil-ellenőrzés. A blokk-property-ket mindig `copy` attribútummal deklaráld, az összetett blokk-típusokat pedig `typedef`-fel tedd olvashatóvá.

```objective-c
#import <Foundation/Foundation.h>

typedef void (^KeszBlokk)(NSData * _Nullable adat, NSError * _Nullable hiba);

@interface Letolto : NSObject
@property (nonatomic, copy) void (^haladas)(double szazalek);   // blokk property: mindig copy
- (void)letolt:(NSURL *)url kesz:(KeszBlokk)kesz;
@end

@implementation Letolto
- (void)letolt:(NSURL *)url kesz:(KeszBlokk)kesz {
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_UTILITY, 0), ^{
        for (int i = 1; i <= 4; i++) {
            if (self.haladas) self.haladas(i * 25.0);
        }
        NSData *d = [url.absoluteString dataUsingEncoding:NSUTF8StringEncoding];
        dispatch_async(dispatch_get_main_queue(), ^{ kesz(d, nil); });   // vissza a fő szálra
    });
}
@end

@interface Kepernyo : NSObject
@property (nonatomic, strong) Letolto *letolto;
@property (atomic) double allapot;
- (void)betolt;
@end

@implementation Kepernyo
- (void)betolt {
    // RETAIN CIKLUS lenne: self -> letolto -> haladas blokk -> self.
    __weak typeof(self) gyengeSelf = self;
    self.letolto.haladas = ^(double p) {
        __strong typeof(gyengeSelf) erosSelf = gyengeSelf;   // a futás idejére életben tartjuk
        if (!erosSelf) return;                               // már felszabadult
        erosSelf.allapot = p;
    };
    [self.letolto letolt:[NSURL URLWithString:@"https://example.com/adat"]
                    kesz:^(NSData *adat, NSError *hiba) {
        NSLog(@"kész: %lu bájt, hiba: %@", (unsigned long)adat.length, hiba);
    }];
}
@end

int main(void) {
    @autoreleasepool {
        // __block: a blokkon belül módosítható változó.
        __block NSInteger szamlalo = 0;
        void (^novel)(void) = ^{ szamlalo++; };
        novel();
        novel();
        NSLog(@"számláló: %ld", (long)szamlalo);   // 2

        NSArray<NSNumber *> *szamok = @[@5, @2, @9];
        NSArray *rendezett = [szamok sortedArrayUsingComparator:^NSComparisonResult(NSNumber *a, NSNumber *b) {
            return [a compare:b];
        }];
        NSLog(@"%@", rendezett);

        Kepernyo *k = [Kepernyo new];
        k.letolto = [Letolto new];
        [k betolt];
        [[NSRunLoop mainRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.5]];
    }
    return 0;
}
```

## Kategóriák és class extensionök
<!-- q: Mire jók a kategóriák és a class extensionök Objective-C-ben? -->
<!-- tags: category, class extension, extension methods, prefix, private interface, lightweight generics -->

A kategória (`@interface NSString (Valami)`) metódusokat ad egy meglévő — akár rendszer- — osztályhoz a forráskódja nélkül; tárolt property-t nem adhat (ahhoz associated object kell). Mivel névütközés esetén nem definiált, melyik implementáció nyer, a kategória-metódusokat mindig előtaggal (pl. `hu_`) nevezd el. A class extension (`@interface Osztaly ()`) „névtelen kategória” a `.m` fájlban: privát property-ket, ivarokat és protokoll-megfeleléseket rejt el a publikus fejléc elől, és readonly property-t belül readwrite-ra bővíthet. Kategóriát gyűjteményekre generikus paraméterrel (`NSArray<ObjectType>`) is lehet írni.

```objective-c
#import <Foundation/Foundation.h>

// Kategória rendszerosztályon; előtag a névütközés ellen.
@interface NSString (HUValidacio)
- (BOOL)hu_ervenyesAdoazonosito;          // 11 számjegy (kötőjelek megengedve)
- (NSString *)hu_ekezetNelkul;
@end

@implementation NSString (HUValidacio)
- (BOOL)hu_ervenyesAdoazonosito {
    NSString *tiszta = [self stringByReplacingOccurrencesOfString:@"-" withString:@""];
    NSCharacterSet *nemSzam = [[NSCharacterSet decimalDigitCharacterSet] invertedSet];
    return tiszta.length == 11 && [tiszta rangeOfCharacterFromSet:nemSzam].location == NSNotFound;
}

- (NSString *)hu_ekezetNelkul {
    // Diakritikus jelek eltávolítása (ő -> o, ű -> u).
    return [self stringByFoldingWithOptions:NSDiacriticInsensitiveSearch
                                     locale:[NSLocale localeWithLocaleIdentifier:@"hu_HU"]];
}
@end

// Kategória generikus gyűjteményen: funkcionális segédek.
@interface NSArray<ObjectType> (HUFunkcionalis)
- (NSArray *)hu_map:(id (^)(ObjectType elem))f;
- (NSArray<ObjectType> *)hu_filter:(BOOL (^)(ObjectType elem))feltetel;
@end

@implementation NSArray (HUFunkcionalis)
- (NSArray *)hu_map:(id (^)(id))f {
    NSMutableArray *out = [NSMutableArray arrayWithCapacity:self.count];
    for (id e in self) { [out addObject:f(e)]; }
    return [out copy];                    // immutable másolat kifelé
}

- (NSArray *)hu_filter:(BOOL (^)(id))feltetel {
    NSPredicate *p = [NSPredicate predicateWithBlock:^BOOL(id e, NSDictionary *bindings) {
        return feltetel(e);
    }];
    return [self filteredArrayUsingPredicate:p];
}
@end

int main(void) {
    @autoreleasepool {
        NSLog(@"%d %@", [@"8123-4567-890" hu_ervenyesAdoazonosito], [@"Árvíztűrő" hu_ekezetNelkul]);
        NSArray *duplak = [@[@1, @2, @3] hu_map:^id(NSNumber *n) { return @(n.integerValue * 2); }];
        NSLog(@"%@", [duplak hu_filter:^BOOL(NSNumber *n) { return n.integerValue > 2; }]);  // (4, 6)
    }
    return 0;
}
```

## Protokollok és a delegate minta
<!-- q: Hogyan implementáljam a delegate mintát protokollal Objective-C-ben? -->
<!-- tags: protocol, delegate, optional methods, respondsToSelector, weak delegate, conformance -->

A protokoll metódus-követelményeket deklarál, amelyek lehetnek `@required` vagy `@optional`; a delegate minta ezzel adja át egy objektum eseményeit (befejezés, haladás, döntések) egy másiknak. A delegate property mindig `weak`, különben retain ciklus keletkezik (a tulajdonos tartja a komponenst, a komponens a tulajdonost). Opcionális metódust csak `respondsToSelector:` ellenőrzés után szabad hívni, különben „unrecognized selector” crash jön; gyakran hívott delegate-nél az ellenőrzés eredményét bitmezőben cache-eljük a setterben. A protokoll-megfelelés a class extensionben is deklarálható, így kívülről nem látszik.

```objective-c
#import <Foundation/Foundation.h>

@class Letoltes;

@protocol LetoltesDelegate <NSObject>
@required
- (void)letoltes:(Letoltes *)l befejezodott:(NSData *)adat;
@optional
- (void)letoltes:(Letoltes *)l halad:(double)arany;
- (BOOL)letoltesUjraprobalhato:(Letoltes *)l hiba:(NSError *)hiba;
@end

@interface Letoltes : NSObject
@property (nonatomic, weak) id<LetoltesDelegate> delegate;   // MINDIG weak
- (void)szimulal;
@end

@implementation Letoltes {
    struct {                       // a respondsToSelector eredményének cache-e
        unsigned int halad : 1;
        unsigned int ujraprobal : 1;
    } _kepes;
}

- (void)setDelegate:(id<LetoltesDelegate>)delegate {
    _delegate = delegate;
    _kepes.halad = [delegate respondsToSelector:@selector(letoltes:halad:)];
    _kepes.ujraprobal = [delegate respondsToSelector:@selector(letoltesUjraprobalhato:hiba:)];
}

- (void)szimulal {
    for (int i = 1; i <= 3; i++) {
        if (_kepes.halad) [self.delegate letoltes:self halad:i / 3.0];   // opcionális: csak ellenőrzés után
    }
    NSError *hiba = [NSError errorWithDomain:NSURLErrorDomain code:NSURLErrorTimedOut userInfo:nil];
    if (_kepes.ujraprobal && [self.delegate letoltesUjraprobalhato:self hiba:hiba]) {
        NSLog(@"újrapróbálkozás...");
    }
    [self.delegate letoltes:self befejezodott:[@"OK" dataUsingEncoding:NSUTF8StringEncoding]];
}
@end

@interface Vezerlo : NSObject
@property (nonatomic, strong) Letoltes *letoltes;
@end

@interface Vezerlo () <LetoltesDelegate>   // megfelelés privátan deklarálva
@end

@implementation Vezerlo
- (void)letoltes:(Letoltes *)l befejezodott:(NSData *)adat {
    NSLog(@"kész: %lu bájt", (unsigned long)adat.length);
}
- (void)letoltes:(Letoltes *)l halad:(double)arany {
    NSLog(@"%.0f%%", arany * 100);
}
@end

int main(void) {
    @autoreleasepool {
        Vezerlo *v = [Vezerlo new];
        v.letoltes = [Letoltes new];
        v.letoltes.delegate = v;
        [v.letoltes szimulal];   // az ujraprobalhato nincs implementálva -> kimarad
    }
    return 0;
}
```

## KVC és KVO
<!-- q: Hogyan működik a Key-Value Coding és a Key-Value Observing Objective-C-ben? -->
<!-- tags: kvc, kvo, key-value observing, valueForKey, addObserver, keyPathsForValuesAffecting -->

A KVC (Key-Value Coding) string kulccsal ér el property-ket (`valueForKey:`, `setValue:forKey:`), automatikus NSNumber ↔ primitív konverzióval, és kollekció-operátorokat (`@sum`, `@max`, `@avg`) is ad. A KVO (Key-Value Observing) erre épül: a megfigyelt objektum osztályát a runtime futásidőben egy generált alosztályra cseréli (isa-swizzling), amelynek settere értesítést küld. Függő property-ket a `keyPathsForValuesAffecting<Kulcs>` metódus köt össze. Buktatók: egyedi `context` pointerrel azonosítsd a saját értesítéseidet, mindig iratkozz le, és csak a settert/KVC-t használó módosítás vált ki értesítést (közvetlen `_ivar` írás nem).

```objective-c
#import <Foundation/Foundation.h>

@interface Szamla : NSObject
@property (nonatomic) double egyenleg;
@property (nonatomic, copy) NSString *tulajdonos;
@property (nonatomic, readonly) NSString *osszegzes;   // származtatott property
@end

@implementation Szamla
// KVO-függőség: egyenleg vagy tulajdonos változása = osszegzes változása.
+ (NSSet<NSString *> *)keyPathsForValuesAffectingOsszegzes {
    return [NSSet setWithObjects:@"egyenleg", @"tulajdonos", nil];
}
- (NSString *)osszegzes {
    return [NSString stringWithFormat:@"%@: %.0f Ft", self.tulajdonos, self.egyenleg];
}
@end

static void *SzamlaKontextus = &SzamlaKontextus;   // egyedi kontextus

@interface Figyelo : NSObject
@property (nonatomic, strong) Szamla *szamla;
- (instancetype)initWithSzamla:(Szamla *)sz;
@end

@implementation Figyelo
- (instancetype)initWithSzamla:(Szamla *)sz {
    if ((self = [super init])) {
        _szamla = sz;
        [sz addObserver:self
             forKeyPath:@"osszegzes"
                options:NSKeyValueObservingOptionNew | NSKeyValueObservingOptionOld
                context:SzamlaKontextus];
    }
    return self;
}

- (void)observeValueForKeyPath:(NSString *)keyPath ofObject:(id)object
                        change:(NSDictionary<NSKeyValueChangeKey, id> *)change context:(void *)context {
    if (context != SzamlaKontextus) {   // nem a miénk -> tovább a szülőnek
        [super observeValueForKeyPath:keyPath ofObject:object change:change context:context];
        return;
    }
    NSLog(@"%@: %@ -> %@", keyPath, change[NSKeyValueChangeOldKey], change[NSKeyValueChangeNewKey]);
}

- (void)dealloc {
    [_szamla removeObserver:self forKeyPath:@"osszegzes" context:SzamlaKontextus];   // kötelező leiratkozás
}
@end

int main(void) {
    @autoreleasepool {
        Szamla *sz = [Szamla new];
        sz.tulajdonos = @"Teszt Kft.";
        Figyelo *f = [[Figyelo alloc] initWithSzamla:sz];
        sz.egyenleg = 25000;                          // a setter KVO-értesítést küld

        [sz setValue:@50000 forKey:@"egyenleg"];      // KVC: NSNumber -> double automatikusan
        NSLog(@"KVC olvasás: %@", [sz valueForKey:@"tulajdonos"]);

        NSArray *szamlak = @[sz, [Szamla new]];       // kollekció-operátorok
        NSLog(@"összes: %@, max: %@",
              [szamlak valueForKeyPath:@"@sum.egyenleg"], [szamlak valueForKeyPath:@"@max.egyenleg"]);
        (void)f;
    }
    return 0;
}
```

## Hibakezelés: NSError és kivételek
<!-- q: Hogyan kezeljem a hibákat Objective-C-ben (NSError **, @try/@catch)? -->
<!-- tags: error handling, NSError, error domain, NS_ERROR_ENUM, NSException, try catch -->

A Cocoa-konvenció szerint a várható hibákat (fájl, hálózat, parse) `NSError **` kimeneti paraméter jelzi, a visszatérési érték (nil/NO) pedig a sikerességet: a hibát CSAK akkor szabad vizsgálni, ha a visszatérés sikertelenséget jelez, és írás előtt ellenőrizni kell, hogy a hívó nem NULL-t adott-e át. Az `NSError` domain + kód + userInfo hármas; a `NSUnderlyingErrorKey` hibaláncot képez, az `NS_ERROR_ENUM` pedig Swiftben típusos hibává alakul. Az `@try`/`@catch` (NSException) csak programozói hibákra való (index túlcsordulás, nil beszúrás), nem normál vezérlésre: ARC alatt szivárgást okozhat, és Swift-határon át nem biztonságos.

```objective-c
#import <Foundation/Foundation.h>

// Saját hibadomain és kódok (Swiftben: KonfigHibaKod típusos hiba).
NSErrorDomain const KonfigHibaDomain = @"hu.pelda.konfig";
typedef NS_ERROR_ENUM(KonfigHibaDomain, KonfigHibaKod) {
    KonfigHibaNincsFajl = 1,
    KonfigHibaRosszFormatum = 2,
};

// Konvenció: nil visszatérés + kitöltött *hiba.
NSDictionary * _Nullable konfigBetolt(NSString *ut, NSError **hiba) {
    NSData *adat = [NSData dataWithContentsOfFile:ut options:0 error:hiba];   // a hibát továbbadjuk
    if (!adat) {
        return nil;
    }
    NSError *jsonHiba = nil;
    id json = [NSJSONSerialization JSONObjectWithData:adat options:0 error:&jsonHiba];
    if (![json isKindOfClass:[NSDictionary class]]) {
        if (hiba) {                 // a hívó adhat NULL-t, ha nem érdekli a hiba
            NSMutableDictionary *info = [@{NSLocalizedDescriptionKey: @"A konfiguráció nem JSON objektum"} mutableCopy];
            if (jsonHiba) info[NSUnderlyingErrorKey] = jsonHiba;   // hibalánc
            *hiba = [NSError errorWithDomain:KonfigHibaDomain code:KonfigHibaRosszFormatum userInfo:info];
        }
        return nil;
    }
    return json;
}

int main(void) {
    @autoreleasepool {
        NSError *hiba = nil;
        NSDictionary *konfig = konfigBetolt(@"/nem/letezo/config.json", &hiba);
        if (!konfig) {              // a visszatérési értéket nézzük, nem a hiba != nil-t
            NSLog(@"hiba: %@ (%@ %ld)", hiba.localizedDescription, hiba.domain, (long)hiba.code);
        }

        // NSException: programozói hibákra.
        @try {
            NSArray *lista = @[@1, @2];
            NSLog(@"%@", lista[5]);
        } @catch (NSException *e) {
            NSLog(@"kivétel: %@ — %@", e.name, e.reason);   // NSRangeException
        } @finally {
            NSLog(@"finally lefut");
        }
    }
    return 0;
}
```

## Grand Central Dispatch (GCD)
<!-- q: Hogyan használjam a GCD-t (dispatch queue, group, barrier, dispatch_once) Objective-C-ben? -->
<!-- tags: gcd, dispatch, queue, dispatch_group, barrier, dispatch_once, concurrency, singleton -->

A GCD blokkokat ütemez sorokra (queue): a soros sor egyszerre egy blokkot futtat (egyszerű kölcsönös kizárás), a konkurens sor többet; a fő sor (main queue) a UI-szál. A `dispatch_group` több aszinkron feladat bevárására szolgál, a `dispatch_barrier_async` konkurens soron „olvasó–író” zárat valósít meg (párhuzamos olvasás, kizárólagos írás), a `dispatch_once` pedig szálbiztos egyszeri inicializálást (singleton) ad. Buktatók: `dispatch_sync` az aktuális soros sorra deadlockot okoz, UI-t csak a main queue-n szabad frissíteni, és túl sok blokkoló feladat a globális sorokon szálrobbanáshoz vezet.

```objective-c
#import <Foundation/Foundation.h>

// Szálbiztos cache olvasó–író mintával.
@interface Cache : NSObject
+ (instancetype)megosztott;
- (nullable id)objektum:(NSString *)kulcs;
- (void)beallit:(id)obj kulcs:(NSString *)kulcs;
@end

@implementation Cache {
    dispatch_queue_t _sor;
    NSMutableDictionary *_adat;
}

+ (instancetype)megosztott {
    static Cache *peldany;
    static dispatch_once_t once;
    dispatch_once(&once, ^{ peldany = [self new]; });   // szálbiztos singleton
    return peldany;
}

- (instancetype)init {
    if ((self = [super init])) {
        _sor = dispatch_queue_create("hu.pelda.cache", DISPATCH_QUEUE_CONCURRENT);
        _adat = [NSMutableDictionary new];
    }
    return self;
}

- (id)objektum:(NSString *)kulcs {
    __block id eredmeny;
    dispatch_sync(_sor, ^{ eredmeny = self->_adat[kulcs]; });       // párhuzamos olvasók
    return eredmeny;
}

- (void)beallit:(id)obj kulcs:(NSString *)kulcs {
    dispatch_barrier_async(_sor, ^{ self->_adat[kulcs] = obj; });   // írás alatt senki más
}
@end

int main(void) {
    @autoreleasepool {
        Cache *c = [Cache megosztott];
        dispatch_group_t csoport = dispatch_group_create();
        dispatch_queue_t hatter = dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0);

        for (int i = 0; i < 10; i++) {                  // párhuzamos feladatok
            dispatch_group_async(csoport, hatter, ^{
                [c beallit:@(i * i) kulcs:[NSString stringWithFormat:@"k%d", i]];
            });
        }
        dispatch_group_wait(csoport, DISPATCH_TIME_FOREVER);   // mind kész

        // dispatch_apply: párhuzamos for-ciklus.
        __block int64_t osszeg = 0;
        dispatch_apply(1000, hatter, ^(size_t i) {
            __atomic_fetch_add(&osszeg, (int64_t)i, __ATOMIC_RELAXED);
        });

        // Késleltetett futtatás a fő soron (UI-frissítés helye).
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 100 * NSEC_PER_MSEC), dispatch_get_main_queue(), ^{
            NSLog(@"k3=%@ összeg=%lld", [c objektum:@"k3"], osszeg);   // 9, 499500
            exit(0);
        });
        dispatch_main();   // parancssori programban a fő sor feldolgozása
    }
}
```

## Nullability, lightweight generics, NS_ENUM és NS_OPTIONS
<!-- q: Hogyan használjam a nullability annotációkat, generikusokat és NS_ENUM-ot Objective-C-ben? -->
<!-- tags: nullability, nonnull, nullable, lightweight generics, NS_ENUM, NS_OPTIONS, NS_ASSUME_NONNULL -->

A modern Objective-C annotációk a fordító figyelmeztetéseit élesítik és meghatározzák, hogyan látszik az API Swiftből. Az `NS_ASSUME_NONNULL_BEGIN/END` blokkban minden pointer alapból `nonnull`, a kivételeket `nullable` jelöli (Swiftben ebből lesz `T?`). A lightweight generics (`NSArray<NSString *> *`) fordítási idejű típusellenőrzést ad és Swiftben `[String]`-ként importálódik (futásidőben nincs hatása). Az `NS_ENUM` fix alaptípusú, Swiftben natív enummá, az `NS_OPTIONS` bitmaszk `OptionSet`-té válik.

```objective-c
#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN   // minden pointer alapból nonnull

typedef NS_ENUM(NSInteger, RendelesAllapot) {    // Swiftben: RendelesAllapot.fizetve
    RendelesAllapotFuggo,
    RendelesAllapotFizetve,
    RendelesAllapotKiszallitva,
};

typedef NS_OPTIONS(NSUInteger, Ertesites) {      // Swiftben: OptionSet
    ErtesitesNincs = 0,
    ErtesitesEmail = 1 << 0,
    ErtesitesPush  = 1 << 1,
    ErtesitesSMS   = 1 << 2,
};

@interface Rendeles : NSObject
@property (nonatomic, copy) NSString *azonosito;
@property (nonatomic, copy, nullable) NSString *megjegyzes;   // Swiftben String?
@property (nonatomic) RendelesAllapot allapot;
@property (nonatomic) Ertesites ertesitesek;
@property (nonatomic, copy) NSArray<NSString *> *tetelSKUk;  // Swiftben [String]
@end

// Saját generikus osztály kovariáns típusparaméterrel.
@interface RendelesTarolo<__covariant T: Rendeles *> : NSObject
- (void)hozzaad:(T)rendeles;
- (nullable T)keres:(NSString *)azonosito;
- (NSArray<T> *)szur:(BOOL (NS_NOESCAPE ^)(T rendeles))feltetel;
@end

NS_ASSUME_NONNULL_END

@implementation Rendeles
@end

@implementation RendelesTarolo {
    NSMutableDictionary<NSString *, Rendeles *> *_adat;
}
- (instancetype)init {
    if ((self = [super init])) { _adat = [NSMutableDictionary new]; }
    return self;
}
- (void)hozzaad:(Rendeles *)r { _adat[r.azonosito] = r; }
- (Rendeles *)keres:(NSString *)azonosito { return _adat[azonosito]; }
- (NSArray *)szur:(BOOL (^)(Rendeles *))feltetel {
    NSMutableArray *out = [NSMutableArray new];
    for (Rendeles *r in _adat.allValues) {
        if (feltetel(r)) [out addObject:r];
    }
    return out;
}
@end

int main(void) {
    @autoreleasepool {
        RendelesTarolo<Rendeles *> *t = [RendelesTarolo new];
        Rendeles *r = [Rendeles new];
        r.azonosito = @"R-1";
        r.allapot = RendelesAllapotFizetve;
        r.ertesitesek = ErtesitesEmail | ErtesitesPush;   // bitenkénti VAGY
        [t hozzaad:r];
        // [t hozzaad:@"szöveg"];   // figyelmeztetés: inkompatibilis típus
        // r.azonosito = nil;       // figyelmeztetés: nil nonnull property-nek

        BOOL vanPush = (r.ertesitesek & ErtesitesPush) != 0;
        NSArray *fizetett = [t szur:^BOOL(Rendeles *x) { return x.allapot == RendelesAllapotFizetve; }];
        NSLog(@"push=%d fizetett=%lu", vanPush, (unsigned long)fizetett.count);
    }
    return 0;
}
```

## Együttműködés Swifttel (interop)
<!-- q: Hogyan használjak Objective-C kódot Swiftből és Swift kódot Objective-C-ből? -->
<!-- tags: swift interop, bridging header, NS_SWIFT_NAME, objc attribute, generated header, async import -->

Ugyanazon az app targeten belül az Objective-C fejlécek a Bridging Headeren (vagy framework esetén a modulon) keresztül válnak láthatóvá Swiftből, fordítva pedig az Xcode által generált `<ModulNév>-Swift.h` fejléc teszi elérhetővé a Swift kódot. Az `NS_SWIFT_NAME` Swiftbarát nevet ad, a nullability és generikus annotációk pontos Swift-típusokat eredményeznek, a `completion`-nevű utolsó blokk-paraméterű metódusokból pedig a Swift automatikusan `async` változatot generál. Swiftből Objective-C felé csak `NSObject`-leszármazott osztályok `@objc` tagjai látszanak; struct, generikus típus és asszociált értékes enum nem.

```objective-c
// IdojarasKliens.h — Swiftbarát Objective-C API
#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

NS_SWIFT_NAME(IdojarasKliens)                    // Swiftben előtag nélküli név
@interface HUIdojarasKliens : NSObject

- (instancetype)initWithAlapURL:(NSURL *)url NS_SWIFT_NAME(init(alapURL:));

// Completion handleres metódus -> Swiftben async throws változat is generálódik:
//   let t = try await kliens.homerseklet(varos: "Kecskemét")
- (void)homersekletVarosban:(NSString *)varos
                 completion:(void (^)(double homerseklet, NSError * _Nullable hiba))completion
    NS_SWIFT_NAME(homerseklet(varos:completion:));

@end

NS_ASSUME_NONNULL_END

// Valahol.m — Swift osztály használata Objective-C-ből
#import "SajatApp-Swift.h"                       // Xcode generálja: <ModulNév>-Swift.h

static void formazasPelda(void) {
    NSString *szoveg = [HUFormazo homerseklet:21.5];   // a Swift Formazo osztály ObjC-neve
    NSLog(@"%@", szoveg);
}
```

```swift
// Swift oldal: az ObjC fejléc a Bridging Headerben: #import "IdojarasKliens.h"
import Foundation

let kliens = IdojarasKliens(alapURL: URL(string: "https://api.example.com")!)
Task {
    do {
        let t = try await kliens.homerseklet(varos: "Kecskemét")   // generált async változat
        print("Hőmérséklet: \(t) °C")
    } catch {
        print(error.localizedDescription)
    }
}

// Swift -> ObjC: NSObject-leszármazott + @objc tagok kerülnek a generált fejlécbe.
@objc(HUFormazo)                    // ObjC-oldali név, előtaggal
public final class Formazo: NSObject {
    @objc public static func homerseklet(_ ertek: Double) -> String {
        String(format: "%.1f °C", ertek)
    }
}
```
