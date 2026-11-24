# Zig
<!-- tech: zig -->
<!-- aliases: ziglang, zig cc -->

A Zig egy modern, natívra fordított rendszerprogramozási nyelv, amelyet a C utódjának szánnak: nincs rejtett vezérlés (nincs operator overloading, kivétel, rejtett konstruktor), és nincs rejtett allokáció – aminek memória kell, az explicit `Allocator` paramétert kap. Makrók és külön generikus szintaxis helyett a `comptime` (fordítási idejű kódfuttatás) adja a metaprogramozást, a hibákat pedig error unionök (`!T`) és `try`/`catch` kezelik. Kiváló C-interop (`@cImport`, a `zig cc` teljes értékű keresztfordító C/C++ fordító), Debug/ReleaseSafe módban futásidejű ellenőrzésekkel (túlcsordulás, túlindexelés). A nyelv még 1.0 előtti, a standard library API-ja verzióról verzióra változik – a példák a 0.14/0.15-ös sorozatot követik.

## Alapok: változók, egészek, optional és slice
<!-- q: Mik a Zig alapjai: változók, egész típusok, optional és slice? -->
<!-- tags: zig basics, const, var, integers, overflow, optional, slices, arrays, casting -->

A `const` nem módosítható, a `var` módosítható kötés; a fordító hibát ad a nem használt lokális változóra és a soha nem módosított `var`-ra. Az egészek explicit szélességűek (`u8`, `i32`, `u64`, `usize`), implicit szűkítés nincs: `@intCast`, `@truncate` vagy `std.math.cast` kell. A túlcsordulás Debug/ReleaseSafe módban panic, nem csendes UB; szándékos körbefordulásra a `+%`, telítésre a `+|` operátor való. A null csak optional típusban (`?T`) létezhet, és kezelni kötelező (`if (x) |v|`, `orelse`); a slice (`[]T`) pointer + hossz, határellenőrzéssel.

```zig
const std = @import("std");

fn parseTimeout(s: []const u8) ?u32 {
    return std.fmt.parseInt(u32, s, 10) catch null;   // hiba -> null
}

pub fn main() void {
    const max_users: u32 = 1000;
    var count: u32 = 0;
    count += 1;

    // Túlcsordulás: Debug módban panic. Explicit körbefordulás / telítés:
    const base: u8 = 250;
    const wrapped = base +% 10;          // 4
    const saturated = base +| 10;        // 255

    // Optional: a null csak ?T-ben létezik
    const maybe_port: ?u16 = 8080;
    if (maybe_port) |port| {             // kicsomagolás capture-rel
        std.debug.print("port: {d}\n", .{port});
    }
    const timeout: u32 = parseTimeout("abc") orelse 30;   // alapérték null esetén

    // Tömb (fix méret, érték típus) és slice (ptr + len)
    const primes = [_]u32{ 2, 3, 5, 7, 11 };
    const tail: []const u32 = primes[2..];
    var sum: u32 = 0;
    for (tail, 0..) |p, i| {             // elem + index párhuzamos bejárása
        sum += p * @as(u32, @intCast(i + 1));
    }

    // Explicit konverziók
    const big: u64 = 300;
    const small: u8 = @truncate(big);                     // 44: levágja a felső biteket
    const checked: u8 = std.math.cast(u8, big) orelse 255; // biztonságos szűkítés

    // Blokk mint kifejezés, címkével
    const category = blk: {
        if (count > max_users) break :blk "tele";
        break :blk "van hely";
    };

    std.debug.print("{d} {d} {d} {d} {d} {d} {s}\n", .{
        wrapped, saturated, timeout, sum, small, checked, category,
    });
}
```

## Hibakezelés: error union, try és catch
<!-- q: Hogyan működik a hibakezelés Zigben (error union, try, catch)? -->
<!-- tags: error handling, error union, error set, try, catch, errorName, error return trace -->

A Zig hibái egyszerű értékek: a hibahalmaz (`error{ MissingKey, InvalidPort }`) nevesített kódok listája, az error union (`E!T`) pedig vagy értéket, vagy hibát hordoz – nincs kivétel, nincs allokáció, nincs rejtett vezérlés. A `try` hiba esetén azonnal továbbadja azt a hívónak, a `catch` alapértéket ad vagy kezeli a hibát, a `switch` pedig kimerítően ellenőrzi a hibahalmaz minden elemét. A hibahalmazok `||`-vel egyesíthetők, és `!T` esetén a fordító maga gyűjti össze őket. Debug módban az „error return trace” megmutatja, hol keletkezett és merre terjedt a hiba.

```zig
const std = @import("std");

const ConfigError = error{ MissingKey, InvalidPort };

// Egyesített hibahalmaz: saját hibák + a parseInt hibái
fn parsePort(text: []const u8) (ConfigError || std.fmt.ParseIntError)!u16 {
    if (text.len == 0) return error.MissingKey;
    const n = try std.fmt.parseInt(u32, text, 10);   // hiba esetén továbbdobja
    if (n == 0 or n > 65535) return error.InvalidPort;
    return @as(u16, @intCast(n));
}

// Hibák lekezelése kimerítő switch-csel: a függvény maga már nem dob
fn portOrDefault(text: []const u8) u16 {
    return parsePort(text) catch |err| switch (err) {
        error.MissingKey => 80,
        error.InvalidPort, error.Overflow => 65535,
        error.InvalidCharacter => 0,
    };
}

fn describe(text: []const u8) void {
    if (parsePort(text)) |port| {
        std.debug.print("'{s}' -> {d}\n", .{ text, port });
    } else |err| {
        std.debug.print("'{s}' -> hiba: {s}\n", .{ text, @errorName(err) });
    }
}

// !void: kikövetkeztetett hibahalmaz; a main hibája kiírva, nem-nulla kilépési kóddal
pub fn main() !void {
    describe("8080");
    describe("70000");
    describe("abc");
    describe("");
    std.debug.print("{d} {d}\n", .{ portOrDefault(""), portOrDefault("x1") });

    const p = try parsePort("443");
    std.debug.print("https: {d}\n", .{p});
}
```

## defer és errdefer: erőforrás-felszabadítás
<!-- q: Mire való a defer és az errdefer Zigben? -->
<!-- tags: defer, errdefer, resource cleanup, error handling, partial initialization, raii alternative -->

A `defer` a blokk végén fut le (fordított sorrendben), az `errdefer` csak akkor, ha a függvény hibával tér vissza – ez a Zig válasza a RAII-ra és a C-s `goto cleanup`-ra. Az idiomatikus minta: az erőforrás megszerzése után KÖZVETLENÜL jön a `defer x.deinit()`, így nem felejthető el. Az `errdefer` a részleges inicializálás problémáját oldja meg: ha egy init több lépésből áll, és félúton hiba történik, a már megszerzett erőforrások felszabadulnak, sikeres visszatéréskor viszont a hívóhoz kerülnek. Buktató: a defer a blokk (nem a függvény) végén fut, ciklusban tehát minden iterációban.

```zig
const std = @import("std");

const Connection = struct {
    id: u32,
    fn open(id: u32) !Connection {
        if (id == 13) return error.ConnectionRefused;
        std.debug.print("open {d}\n", .{id});
        return .{ .id = id };
    }
    fn close(self: Connection) void {
        std.debug.print("close {d}\n", .{self.id});
    }
};

const Pool = struct {
    conns: []Connection,
    allocator: std.mem.Allocator,

    fn init(allocator: std.mem.Allocator, ids: []const u32) !Pool {
        const conns = try allocator.alloc(Connection, ids.len);
        errdefer allocator.free(conns);                   // hiba esetén a tömb is felszabadul

        var opened: usize = 0;
        errdefer for (conns[0..opened]) |c| c.close();    // csak a már megnyitottakat zárja

        for (ids, 0..) |id, i| {
            conns[i] = try Connection.open(id);
            opened += 1;
        }
        return .{ .conns = conns, .allocator = allocator };   // siker: az errdefer-ek nem futnak
    }

    fn deinit(self: *Pool) void {
        for (self.conns) |c| c.close();
        self.allocator.free(self.conns);
    }
};

pub fn main() !void {
    var gpa: std.heap.DebugAllocator(.{}) = .init;
    defer _ = gpa.deinit();                 // a defer-ek fordított sorrendben futnak
    const allocator = gpa.allocator();

    var pool = try Pool.init(allocator, &.{ 1, 2, 3 });
    defer pool.deinit();                    // közvetlenül a megszerzés után

    if (Pool.init(allocator, &.{ 10, 11, 13 })) |p| {
        var p2 = p;
        p2.deinit();
    } else |err| {
        std.debug.print("pool hiba: {s} (a 10 es 11 mar lezarva)\n", .{@errorName(err)});
    }
}
```

## Allokátorok: DebugAllocator, Arena, FixedBuffer
<!-- q: Hogyan működnek az allokátorok Zigben és melyiket mikor használjam? -->
<!-- tags: allocators, DebugAllocator, GeneralPurposeAllocator, ArenaAllocator, FixedBufferAllocator, memory leaks, ArrayList -->

Zigben nincs globális `malloc`: minden allokáló függvény `std.mem.Allocator` paramétert kap, így a HÍVÓ dönti el a stratégiát, és a kód könnyen tesztelhető. A `DebugAllocator` (korábban `GeneralPurposeAllocator`) leaket, double free-t és use-after-free-t detektál; az `ArenaAllocator` sok apró foglalást egyetlen `deinit`-tel szabadít fel; a `FixedBufferAllocator` stack-pufferből dolgozik heap nélkül. Elfogyott memóriánál `error.OutOfMemory` jön, ami kezelhető hiba, nem összeomlás. Az újabb verziókban a konténerek „unmanaged” formájúak: az allokátort hívásonként kell átadni (`list.append(gpa, x)`).

```zig
const std = @import("std");

// Aminek memória kell, az Allocator paramétert kap; a hívó szabadít fel
fn joinWords(allocator: std.mem.Allocator, words: []const []const u8, sep: []const u8) ![]u8 {
    var total: usize = 0;
    for (words) |w| total += w.len;
    if (words.len > 0) total += sep.len * (words.len - 1);

    const out = try allocator.alloc(u8, total);
    var pos: usize = 0;
    for (words, 0..) |w, i| {
        if (i > 0) {
            @memcpy(out[pos..][0..sep.len], sep);
            pos += sep.len;
        }
        @memcpy(out[pos..][0..w.len], w);
        pos += w.len;
    }
    return out;
}

pub fn main() !void {
    // 1) DebugAllocator: hibakereső allokátor fejlesztéshez
    var debug: std.heap.DebugAllocator(.{}) = .init;
    defer if (debug.deinit() == .leak) std.debug.print("MEMORIASZIVARGAS!\n", .{});
    const gpa = debug.allocator();

    const s = try joinWords(gpa, &.{ "zig", "allokator", "minta" }, "-");
    defer gpa.free(s);

    // 2) Arena: sok apró foglalás, egyetlen felszabadítás
    var arena = std.heap.ArenaAllocator.init(gpa);
    defer arena.deinit();
    const a = arena.allocator();
    var list: std.ArrayListUnmanaged(u32) = .empty;
    for (0..100) |i| try list.append(a, @intCast(i * i));
    // nincs list.deinit: az arena.deinit mindent visz

    // 3) FixedBufferAllocator: stack-puffer, heap nélkül
    var buf: [256]u8 = undefined;
    var fba = std.heap.FixedBufferAllocator.init(&buf);
    const tmp = try joinWords(fba.allocator(), &.{ "csak", "stack" }, " ");

    // 4) Egyetlen objektum: create/destroy
    const Item = struct { value: i32, tag: u8 };
    const node = try gpa.create(Item);
    defer gpa.destroy(node);
    node.* = .{ .value = 42, .tag = 'x' };

    std.debug.print("{s} | {d} elem | {s} | {d}\n", .{ s, list.items.len, tmp, node.value });
}
```

## comptime: fordítási idejű kódfuttatás
<!-- q: Mi a comptime Zigben és mire használható? -->
<!-- tags: comptime, compile time, metaprogramming, reflection, inline for, compileError, lookup tables -->

A `comptime` kód fordítási időben fut: ugyanaz a Zig nyelv, nincs külön makró- vagy sablonnyelv. Használható táblák előszámolására (a binárisba égetve), generikus függvényekhez (`comptime T: type`), reflexióhoz (`@typeInfo`, `std.meta.fields`, `@field`) és fordítási idejű validációhoz (`@compileError` érthető üzenettel). Az `inline for` fordításkor kibontja a ciklust, így heterogén mezőkön is végigmehet. Buktató: a comptime kiértékelésnek van ághatára (`@setEvalBranchQuota`), és minden eltérő comptime argumentum külön példányt generál, ami növeli a bináris méretét.

```zig
const std = @import("std");

// Fordítási idejű tábla: a négyzetszámok a binárisba égetve
const squares = blk: {
    var t: [16]u32 = undefined;
    for (&t, 0..) |*v, i| v.* = @intCast(i * i);
    break :blk t;
};

// comptime típusparaméter: minden T-re külön példány
fn maxOf(comptime T: type, items: []const T) T {
    var m: T = std.math.minInt(T);
    for (items) |x| m = @max(m, x);
    return m;
}

// Reflexió: struct mezőinek bejárása fordítási időben
fn printStruct(value: anytype) void {
    const T = @TypeOf(value);
    std.debug.print("{s} {{\n", .{@typeName(T)});
    inline for (std.meta.fields(T)) |f| {
        std.debug.print("  {s}: {any}\n", .{ f.name, @field(value, f.name) });
    }
    std.debug.print("}}\n", .{});
}

// Fordítási idejű validáció
fn checkedDivisor(comptime d: u32) u32 {
    if (d == 0) @compileError("a nevezo nem lehet 0");
    return d;
}

// comptime string-feldolgozás: "main.User" -> "User"
fn shortName(comptime T: type) []const u8 {
    return comptime blk: {
        const full = @typeName(T);
        const dot = std.mem.lastIndexOfScalar(u8, full, '.') orelse break :blk full;
        break :blk full[dot + 1 ..];
    };
}

const User = struct { id: u32, score: i16, active: bool };

pub fn main() void {
    std.debug.print("{d} {d}\n", .{ squares[7], maxOf(i16, &.{ -5, 12, 3 }) });
    printStruct(User{ .id = 1, .score = -3, .active = true });
    const half = 100 / checkedDivisor(2);
    // const bad = 1 / checkedDivisor(0);   // FORDÍTÁSI hiba: "a nevezo nem lehet 0"
    std.debug.print("{d} {s}\n", .{ half, shortName(User) });
}
```

## Generikus típusok és anytype
<!-- q: Hogyan írjak generikus adatszerkezetet és függvényt Zigben? -->
<!-- tags: generics, comptime type, anytype, @This, duck typing, hasDecl, generic data structures -->

Zigben a generikus típus egyszerűen egy függvény, ami `comptime` paraméterekből típust ad vissza (`fn RingBuffer(comptime T: type, comptime cap: usize) type`), a `@This()` pedig az épp példányosított structra hivatkozik. Az `anytype` paraméter statikus „duck typing”: bármi megfelel, aminek megvannak a használt metódusai, és a hiba fordításkor derül ki. A szerződés `@hasDecl`-lel és `@compileError`-ral tehető explicitté és olvashatóvá. Comptime függvényparaméter (pl. összehasonlító) inline-olható, így nincs függvénypointer-költség.

```zig
const std = @import("std");

fn RingBuffer(comptime T: type, comptime capacity: usize) type {
    if (capacity == 0 or (capacity & (capacity - 1)) != 0)
        @compileError("a kapacitas ketto hatvanya legyen");
    return struct {
        const Self = @This();
        items: [capacity]T = undefined,
        head: usize = 0,
        len: usize = 0,

        pub fn push(self: *Self, v: T) error{Full}!void {
            if (self.len == capacity) return error.Full;
            self.items[(self.head + self.len) & (capacity - 1)] = v;   // maszk = olcsó modulo
            self.len += 1;
        }
        pub fn pop(self: *Self) ?T {
            if (self.len == 0) return null;
            const v = self.items[self.head];
            self.head = (self.head + 1) & (capacity - 1);
            self.len -= 1;
            return v;
        }
    };
}

// anytype + inline for: heterogén tuple bejárása
fn totalArea(shapes: anytype) f64 {
    var sum: f64 = 0;
    inline for (shapes) |s| sum += s.area();
    return sum;
}
const Circle = struct {
    r: f64,
    pub fn area(self: Circle) f64 { return std.math.pi * self.r * self.r; }
};
const Square = struct {
    a: f64,
    pub fn area(self: Square) f64 { return self.a * self.a; }
};

fn requireArea(comptime T: type) void {
    if (!@hasDecl(T, "area")) @compileError(@typeName(T) ++ " nem implementalja az area()-t");
}

// Generikus algoritmus comptime összehasonlítóval
fn insertionSort(comptime T: type, items: []T, comptime lessThan: fn (T, T) bool) void {
    var i: usize = 1;
    while (i < items.len) : (i += 1) {
        const x = items[i];
        var j = i;
        while (j > 0 and lessThan(x, items[j - 1])) : (j -= 1) items[j] = items[j - 1];
        items[j] = x;
    }
}
fn desc(a: i32, b: i32) bool { return a > b; }

pub fn main() void {
    var rb: RingBuffer(u8, 4) = .{};
    for ("abcde") |c| rb.push(c) catch std.debug.print("tele: {c}\n", .{c});
    while (rb.pop()) |c| std.debug.print("{c}", .{c});
    std.debug.print("\n", .{});

    comptime requireArea(Circle);
    std.debug.print("{d:.2}\n", .{totalArea(.{ Circle{ .r = 1 }, Square{ .a = 2 } })});

    var nums = [_]i32{ 5, 2, 9, 1 };
    insertionSort(i32, &nums, desc);
    std.debug.print("{any}\n", .{nums});
}
```

## Struct, enum, tagged union és switch
<!-- q: Hogyan használjam a structokat, enumokat és tagged unionokat Zigben? -->
<!-- tags: struct, enum, tagged union, switch, packed struct, extern struct, bitCast, sum types -->

A Zig `enum` metódusokat kaphat, és explicit tag típussal (`enum(u8)`) bináris formátumhoz is illeszthető. A tagged union (`union(enum)`) összegtípus: a `switch` kimerítő, és a payload capture-rel (`|r|`) érhető el; az aktív tagtól eltérő mező olvasása Debug módban panic. A `packed struct` bitpontos elrendezést ad (regiszterek, protokollfejlécek), és `@bitCast`-tal egésszé alakítható; az `extern struct` C ABI-kompatibilis. A sima `struct` mezősorrendjét a fordító szabadon optimalizálhatja, ezért FFI-hez és fájlformátumhoz nem szabad rá építeni.

```zig
const std = @import("std");

const Method = enum(u8) {
    get,
    post,
    delete,
    pub fn isSafe(self: Method) bool { return self == .get; }
};

const Message = union(enum) {
    request: struct { method: Method, path: []const u8 },
    response: u16,
    ping,
    @"error": []const u8,                 // kulcsszó-ütközés: @"..." név
};

fn handle(msg: Message) void {
    switch (msg) {
        .request => |r| std.debug.print("{s} {s} safe={}\n", .{ @tagName(r.method), r.path, r.method.isSafe() }),
        .response => |code| switch (code) {
            200...299 => std.debug.print("siker {d}\n", .{code}),      // tartomány-ág
            400, 404 => std.debug.print("kliens hiba {d}\n", .{code}),
            else => std.debug.print("egyeb {d}\n", .{code}),
        },
        .ping => std.debug.print("pong\n", .{}),
        .@"error" => |e| std.debug.print("hiba: {s}\n", .{e}),
    }
}

// Packed struct: pontosan 8 bit
const Flags = packed struct(u8) {
    readable: bool,
    writable: bool,
    executable: bool,
    _reserved: u5 = 0,
};

// extern struct: C ABI elrendezés
const Vec3 = extern struct { x: f32, y: f32, z: f32 };

pub fn main() void {
    const msgs = [_]Message{
        .{ .request = .{ .method = .post, .path = "/api/users" } },
        .{ .response = 404 },
        .ping,
        .{ .@"error" = "timeout" },
    };
    for (msgs) |m| handle(m);

    const f = Flags{ .readable = true, .writable = false, .executable = true };
    const raw: u8 = @bitCast(f);
    std.debug.print("flags=0b{b:0>8} meret={d} vec3={d}\n", .{ raw, @sizeOf(Flags), @sizeOf(Vec3) });
    std.debug.print("aktiv tag: {s}\n", .{@tagName(std.meta.activeTag(msgs[1]))});
}
```

## Pointerek, slice-ok és sentinel-terminált típusok
<!-- q: Milyen pointertípusok vannak Zigben, mi a különbség a *T, [*]T, []T és [*:0]u8 között? -->
<!-- tags: pointers, slices, many-item pointer, sentinel terminated, optional pointer, ptrCast, alignment -->

Zig a pointer fajtáját a típusban rögzíti: `*T` egyetlen elemre mutat, `[*]T` sok elemre hossz nélkül (C-szerű), `[]T` slice (pointer + hossz, határellenőrzéssel), `[*:0]const u8` pedig nullával lezárt C string, ahol a lezáró érték típusszinten garantált. A null pointer csak optionalban létezhet (`?*T`), így véletlen NULL-deref nem fordulhat elő. Az `undefined` inicializálatlan értéket jelent (Debug módban `0xaa` mintával töltve a hibák könnyebb észleléséhez). A `@ptrCast`/`@alignCast` alacsony szintű reinterpretáció: az igazításért és az aliasingért a programozó felel.

```zig
const std = @import("std");

fn fill(buf: []u8, value: u8) void {
    for (buf) |*b| b.* = value;            // pointer-capture: az elem módosítható
}

fn swap(a: *i32, b: *i32) void {
    const t = a.*;
    a.* = b.*;
    b.* = t;
}

// A lezáró 0 típusszinten garantált
fn cStrLen(s: [*:0]const u8) usize {
    var n: usize = 0;
    while (s[n] != 0) n += 1;
    return n;
}

const Node = struct {
    value: i32,
    next: ?*Node = null,                   // null csak optionalban
};

pub fn main() void {
    var x: i32 = 1;
    var y: i32 = 2;
    swap(&x, &y);

    var buf: [8]u8 = undefined;
    fill(buf[0..4], 'z');
    fill(buf[4..], '-');

    const many: [*]u8 = &buf;              // tömbpointer -> sok-elemes pointer
    const part: []u8 = many[2..5];         // vissza slice-ra (itt nincs határellenőrzés!)

    const lit = "hello";                   // típusa: *const [5:0]u8
    const as_slice: []const u8 = lit;
    const as_c: [*:0]const u8 = lit;

    var c = Node{ .value = 3 };
    var b = Node{ .value = 2, .next = &c };
    const a = Node{ .value = 1, .next = &b };
    var it: ?*const Node = &a;
    var sum: i32 = 0;
    while (it) |n| : (it = n.next) sum += n.value;

    // Reinterpretáció: 2 db u32 bájtjai
    const words = [_]u32{ 0x11223344, 0x55667788 };
    const bytes: *const [8]u8 = @ptrCast(&words);

    std.debug.print("{d} {d} {s} {s} {d} {d} {d} 0x{x}\n", .{
        x, y, &buf, part, as_slice.len, cStrLen(as_c), sum, bytes[0],
    });
}
```

## C interop: @cImport, export és extern
<!-- q: Hogyan használjak C könyvtárat Zigből, és hogyan hívható Zig kód C-ből? -->
<!-- tags: c interop, cImport, cInclude, export, extern, callconv, libc, zig cc, ffi -->

A Zig beépített Clang-gal közvetlenül importál C headereket (`@cImport` + `@cInclude`), így C könyvtárak kötés-generátor nélkül használhatók; a build-ben `link_libc = true` kell. Az `export fn` C ABI-val exportál függvényt, a `callconv(.c)` C-ből hívható callbacket (pl. `qsort` komparátort) ad, az `extern "c" fn` pedig kézzel deklarál C-függvényt. A C stringek `[*:0]const u8`, a nullable C pointerek `?*T` / `?*anyopaque` típusként jelennek meg. Szabály: a C által foglalt memóriát C-vel kell felszabadítani. A `zig cc` drop-in C/C++ fordító és keresztfordító (`zig cc -target aarch64-linux-musl main.c`).

```zig
const std = @import("std");

// C headerek importja (a build-ben: link_libc = true)
const c = @cImport({
    @cInclude("stdio.h");
    @cInclude("stdlib.h");
});

// Kézi deklaráció (a string.h-t nem importáltuk)
extern "c" fn strlen(s: [*:0]const u8) usize;

// C-ből hívható: int32_t zig_add(int32_t, int32_t);
export fn zig_add(a: i32, b: i32) i32 {
    return a +% b;
}

// C callback: callconv(.c) kell
fn cmpInt(a: ?*const anyopaque, b: ?*const anyopaque) callconv(.c) c_int {
    const x: *const c_int = @ptrCast(@alignCast(a.?));
    const y: *const c_int = @ptrCast(@alignCast(b.?));
    return @as(c_int, @intFromBool(x.* > y.*)) - @intFromBool(x.* < y.*);
}

pub fn main() void {
    const msg: [*:0]const u8 = "C printf Zigbol";   // variadikus C-hívásnál explicit C-típus
    _ = c.printf("%s\n", msg);

    var nums = [_]c_int{ 42, 7, 19, 3 };
    c.qsort(&nums, nums.len, @sizeOf(c_int), &cmpInt);

    // C által foglalt memória: C free-vel szabadítjuk fel
    const raw: ?[*]u8 = @ptrCast(c.malloc(16));
    if (raw) |buf| {
        defer c.free(buf);
        const text = "zig+c";
        @memcpy(buf[0..text.len], text);
        buf[text.len] = 0;                          // C string lezárása
        const cs: [*:0]u8 = @ptrCast(buf);
        std.debug.print("{s} len={d}\n", .{ std.mem.span(cs), strlen(cs) });
    }
    std.debug.print("{any} {d}\n", .{ nums, zig_add(2, 3) });
}
```

## Build rendszer: build.zig
<!-- q: Hogyan működik a Zig build rendszer (build.zig), hogyan adjak hozzá modult, C forrást és tesztet? -->
<!-- tags: build.zig, zig build, modules, cross compilation, build options, linkLibC, tests -->

A Zig build-leírása maga is Zig kód (`build.zig`): nincs külön Make/CMake nyelv, a build-gráf lépésekből (`Step`) áll, a `zig build <lépés>` pedig a szükséges lépéseket futtatja, gyorsítótárazással. A `standardTargetOptions` és `standardOptimizeOption` miatt egy kapcsolóval lehet keresztfordítani (`-Dtarget=aarch64-linux-musl`) és optimalizálási módot választani (`-Doptimize=ReleaseFast`). Modulok, C forrásfájlok, futtatási és tesztlépések, valamint fordítási idejű build-opciók adhatók hozzá; a függőségeket a `build.zig.zon` írja le hash-sel rögzítve (`zig fetch --save <url>`). A build API verzióról verzióra változik, a példa a `root_module` alapú (0.14+) formát követi.

```zig
// build.zig
const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});        // -Dtarget=...
    const optimize = b.standardOptimizeOption(.{});     // -Doptimize=ReleaseFast

    // Újrahasznosítható modul
    const core = b.addModule("core", .{
        .root_source_file = b.path("src/core.zig"),
        .target = target,
        .optimize = optimize,
    });

    const exe_mod = b.createModule(.{
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
        .link_libc = true,                               // @cImport-hoz
        .imports = &.{.{ .name = "core", .module = core }},   // @import("core")
    });
    exe_mod.addCSourceFile(.{ .file = b.path("vendor/fast.c"), .flags = &.{ "-O3", "-std=c11" } });
    exe_mod.addIncludePath(b.path("vendor"));

    // Build-opció: -Dtracing=true -> @import("build_options").tracing
    const options = b.addOptions();
    options.addOption(bool, "tracing", b.option(bool, "tracing", "Nyomkovetes") orelse false);
    exe_mod.addOptions("build_options", options);

    const exe = b.addExecutable(.{ .name = "app", .root_module = exe_mod });
    b.installArtifact(exe);                              // zig-out/bin/app

    // zig build run -- arg1 arg2
    const run = b.addRunArtifact(exe);
    run.step.dependOn(b.getInstallStep());
    if (b.args) |args| run.addArgs(args);
    b.step("run", "Az alkalmazas futtatasa").dependOn(&run.step);

    // zig build test
    const tests = b.addTest(.{ .root_module = core });
    b.step("test", "Unit tesztek").dependOn(&b.addRunArtifact(tests).step);
}
```

## Tesztelés: test blokkok és szivárgásdetektálás
<!-- q: Hogyan írjak teszteket Zigben, és hogyan ellenőrizzem a memóriaszivárgást? -->
<!-- tags: testing, test blocks, std.testing, testing.allocator, FailingAllocator, memory leaks, zig test -->

A tesztek `test "név" { ... }` blokkok közvetlenül a forrásfájlban; a `zig test file.zig` vagy `zig build test` futtatja őket, release buildbe nem kerülnek. A `std.testing.allocator` a teszt végén szivárgást jelez, így az elfelejtett `free` bukott tesztet jelent. A `FailingAllocator` az N-edik foglalásnál `OutOfMemory`-t ad, a `checkAllAllocationFailures` pedig minden foglalási pontot egyszer elbuktat – így az `errdefer` ágak is tesztelve vannak, ami más nyelvekben ritkán elérhető. Az `expectEqual(expected, actual)` sorrendje számít a hibaüzenet miatt.

```zig
const std = @import("std");
const testing = std.testing;

/// Szóközökkel tagolt szavak; a hívó szabadítja fel a visszaadott slice-ot.
pub fn splitWords(allocator: std.mem.Allocator, text: []const u8) ![][]const u8 {
    var list: std.ArrayListUnmanaged([]const u8) = .empty;
    errdefer list.deinit(allocator);
    var it = std.mem.tokenizeScalar(u8, text, ' ');
    while (it.next()) |w| try list.append(allocator, w);
    return list.toOwnedSlice(allocator);
}

pub fn clampPercent(x: i32) u8 {
    return @intCast(std.math.clamp(x, 0, 100));
}

test "splitWords alapeset" {
    const words = try splitWords(testing.allocator, "  zig   teszt  ok ");
    defer testing.allocator.free(words);          // nélküle a teszt szivárgás miatt elbukna
    try testing.expectEqual(@as(usize, 3), words.len);
    try testing.expectEqualStrings("teszt", words[1]);
}

test "ures bemenet" {
    const words = try splitWords(testing.allocator, "");
    defer testing.allocator.free(words);
    try testing.expect(words.len == 0);
}

test "allokacios hiba kezelese" {
    var failing = testing.FailingAllocator.init(testing.allocator, .{ .fail_index = 0 });
    try testing.expectError(error.OutOfMemory, splitWords(failing.allocator(), "a b c"));
}

test "tablazatos clamp" {
    const cases = [_]struct { in: i32, want: u8 }{
        .{ .in = -5, .want = 0 },
        .{ .in = 42, .want = 42 },
        .{ .in = 300, .want = 100 },
    };
    for (cases) |case| try testing.expectEqual(case.want, clampPercent(case.in));
}

test "minden foglalasi hiba vegigprobalva" {
    try testing.checkAllAllocationFailures(testing.allocator, struct {
        fn run(a: std.mem.Allocator) !void {
            const w = try splitWords(a, "x y z");
            a.free(w);
        }
    }.run, .{});
}
```

## Szálak és atomikus műveletek
<!-- q: Hogyan használjak szálakat, mutexet és atomikus változókat Zigben? -->
<!-- tags: threads, std.Thread, mutex, atomics, std.atomic.Value, memory ordering, concurrency, data race -->

A `std.Thread.spawn` natív szálat indít egy függvénnyel és egy argumentum-tuple-lel; minden szálat `join`-olni (vagy `detach`-olni) kell, különben az erőforrásai szivárognak. Megosztott, nem atomikus adatot csak `std.Thread.Mutex` alatt szabad írni, különben data race (UB) keletkezik – a `defer mutex.unlock()` minden kilépési úton felold. Az `std.atomic.Value(T)` atomikus műveleteket ad explicit rendezéssel: `.monotonic` (relaxed) számlálóhoz elég, adat publikálásához `.release` tárolás + `.acquire` olvasás kell. Teljesítményhez gyűjts szálanként lokálisan, és csak a végén zárolj.

```zig
const std = @import("std");

const Shared = struct {
    hits: std.atomic.Value(u64) = std.atomic.Value(u64).init(0),
    mutex: std.Thread.Mutex = .{},
    total: u64 = 0,                        // CSAK mutex alatt írható
};

fn worker(shared: *Shared, id: usize, items: []const u32) void {
    var local: u64 = 0;                    // szálanként lokális gyűjtés
    for (items) |x| {
        local += x;
        _ = shared.hits.fetchAdd(1, .monotonic);   // számláló: monotonic elég
    }
    shared.mutex.lock();
    defer shared.mutex.unlock();
    shared.total += local;
    std.debug.print("szal {d}: {d}\n", .{ id, local });
}

fn publish(p: *u32, r: *std.atomic.Value(bool)) void {
    p.* = 42;                              // (1) sima írás
    r.store(true, .release);               // (2) kiadja az (1)-et
}

pub fn main() !void {
    var debug: std.heap.DebugAllocator(.{}) = .init;
    defer _ = debug.deinit();
    const gpa = debug.allocator();

    const data = try gpa.alloc(u32, 10_000);
    defer gpa.free(data);
    for (data, 0..) |*d, i| d.* = @intCast(i % 100);

    var shared: Shared = .{};
    const n_threads = 4;
    var threads: [n_threads]std.Thread = undefined;
    const chunk = data.len / n_threads;

    for (&threads, 0..) |*t, i| {
        const end = if (i == n_threads - 1) data.len else (i + 1) * chunk;
        t.* = try std.Thread.spawn(.{}, worker, .{ &shared, i, data[i * chunk .. end] });
    }
    for (threads) |t| t.join();
    std.debug.print("osszeg={d} hits={d}\n", .{ shared.total, shared.hits.load(.acquire) });

    // Release/acquire publikálás
    var ready = std.atomic.Value(bool).init(false);
    var payload: u32 = 0;
    const producer = try std.Thread.spawn(.{}, publish, .{ &payload, &ready });
    while (!ready.load(.acquire)) std.Thread.yield() catch {};   // (3) szinkronizál (2)-vel
    std.debug.print("payload={d}\n", .{payload});
    producer.join();
}
```
