# Julia
<!-- tech: julia -->

A Julia nagy teljesítményű, dinamikusan típusos, JIT-fordított (LLVM) nyelv tudományos és numerikus számításokra, amely a "két nyelv problémáját" célozza: Python/MATLAB-szerű kényelem C-közeli sebességgel. Központi paradigmája a multiple dispatch (a metódus kiválasztása minden argumentum típusa alapján), gazdag parametrikus típusrendszerrel, első osztályú makrókkal és metaprogramozással; a memóriát garbage collector kezeli, a párhuzamosságot szálak, taskok és elosztott folyamatok adják. A sebesség feltétele a típusstabil kód – a fordító minden konkrét argumentumtípus-kombinációra specializált gépi kódot generál. Kiváló szimulációhoz, optimalizáláshoz, differenciálegyenletekhez és adatelemzéshez; rövid szkripteknél a fordítási késleltetés ("time to first plot") zavaró lehet, és az ökoszisztéma kisebb, mint a Pythoné.

## Multiple dispatch
<!-- q: Mi a multiple dispatch Juliában és miért fontos? -->
<!-- tags: multiple dispatch, methods, polymorphism, generic functions, ambiguity -->

Juliában egy függvénynek (generic function) sok metódusa lehet, és a futtatandó metódust *minden* argumentum konkrét típusa együtt határozza meg, nem csak az elsőé, mint az OO nyelvekben. Ez természetesen kezeli a kettős dispatch-et (pl. ütközésvizsgálat típuspáronként) visitor minta nélkül, és lehetővé teszi, hogy idegen típusokra is új metódust írj, vagy saját típusra kiterjeszd a `Base` függvényeit (`show`, `+`, `isless`). A fordító minden argumentumtípus-kombinációra külön specializált kódot generál, így a dispatch általában futásidőben ingyenes. Buktató: ha két metódus egyformán specifikus egy hívásra, `MethodError: ambiguous` keletkezik – ezt egy még specifikusabb metódussal kell feloldani.

```julia
using InteractiveUtils   # @which, methods – REPL-ben alapból elérhető

abstract type Shape end
struct Circle <: Shape
    r::Float64
end
struct Rect <: Shape
    w::Float64
    h::Float64
end

area(c::Circle) = π * c.r^2
area(r::Rect)   = r.w * r.h

# Kettős dispatch: viselkedés típuspáronként, visitor minta nélkül
intersects(a::Circle, b::Circle) = "kör–kör: középpont-távolság vs. sugarak összege"
intersects(a::Rect, b::Rect)     = "téglalap–téglalap: AABB átfedés"
intersects(a::Circle, b::Rect)   = "kör–téglalap: legközelebbi pont vizsgálata"
intersects(a::Rect, b::Circle)   = intersects(b, a)          # szimmetria egy sorban
intersects(a::Shape, b::Shape)   = error("nincs implementáció: $(typeof(a)) × $(typeof(b))")

shapes = Shape[Circle(1.0), Rect(2.0, 3.0)]
for a in shapes, b in shapes
    println(nameof(typeof(a)), " × ", nameof(typeof(b)), " → ", intersects(a, b))
end

# Base függvények kiterjesztése saját típusra
Base.show(io::IO, c::Circle) = print(io, "Circle(r=", c.r, ")")
Base.isless(a::Shape, b::Shape) = area(a) < area(b)
println(sort(shapes))               # az isless miatt rendezhető
println(maximum(shapes))

# Kétértelműség és feloldása
f(x::Int, y) = 1
f(x, y::Int) = 2
# f(1, 2) itt MethodError: ambiguous lenne -> specifikusabb metódus:
f(x::Int, y::Int) = 3
println(f(1, 2), f(1, "a"), f("a", 1))   # 312

println(length(methods(intersects)), " metódus")
println(@which intersects(Rect(1, 1), Circle(1)))   # melyik metódus fut?
```

## Típusrendszer: absztrakt és konkrét típusok
<!-- q: Hogyan működik a Julia típusrendszere, mi a különbség a struct és a mutable struct között? -->
<!-- tags: type system, abstract type, struct, mutable struct, constructors, union, nothing -->

A Julia típushierarchiájában az absztrakt típusok a csomópontok (nem példányosíthatók), a konkrét típusok a levelek – konkrét típusból nem lehet örökölni, így a viselkedés megosztása dispatch-csel és kompozícióval történik. A `struct` alapból immutable, ezért a fordító inline/stack tárolással optimalizálhatja és szálbiztos; a `mutable struct` heap-en él és referenciaként adódik át (1.8+-tól `const` mezővel részben rögzíthető). A belső konstruktor (`new`) invariánsokat kényszerít ki, a külső konstruktor kényelmi alapértékeket ad; a hiányzó értéket `Union{T,Nothing}` jelzi. Buktató: absztrakt típusú mező (`x::Real`) "dobozolt", lassú kódot ad – használj konkrét vagy parametrikus mezőtípust.

```julia
using InteractiveUtils   # subtypes

abstract type Animal end
abstract type Pet <: Animal end

# Immutable struct belső konstruktorral (invariáns ellenőrzés)
struct Dog <: Pet
    name::String
    age::Int
    function Dog(name::AbstractString, age::Integer)
        age >= 0 || throw(ArgumentError("az életkor nem lehet negatív"))
        new(String(name), Int(age))
    end
end
Dog(name::AbstractString) = Dog(name, 0)      # külső konstruktor: alapértelmezés

# mutable struct: heap-en, referenciaként adódik át
mutable struct Account
    const id::Int                 # Julia 1.8+: nem módosítható mező mutable structban
    balance::Float64
end

# Union{Dog,Nothing}: opcionális visszatérési érték
function find_dog(dogs::Vector{Dog}, name)::Union{Dog,Nothing}
    idx = findfirst(d -> d.name == name, dogs)
    return idx === nothing ? nothing : dogs[idx]
end

dogs = [Dog("Bodri", 3), Dog("Morzsa")]
d = find_dog(dogs, "Bodri")
d === nothing || println(d.name, " ", d.age)
something(find_dog(dogs, "Nincs"), Dog("alapértelmezett")) |> println

acc = Account(1, 100.0)
acc.balance += 50                 # rendben
try
    acc.id = 2                    # hiba: const mező
catch e
    println("Hiba: ", typeof(e))
end

# Típus-lekérdezések
println(Dog <: Pet <: Animal)                     # true
println(isconcretetype(Dog), " ", isabstracttype(Pet))
println(supertypes(Dog))                          # (Dog, Pet, Animal, Any)
println(subtypes(Animal))                         # [Pet]
println(fieldnames(Dog), " ", fieldtypes(Dog))

# Absztrakt mezőtípus = dobozolás, lassú; konkrét = gyors
struct SlowBox; x::Real; end
struct FastBox; x::Float64; end
println(isbitstype(SlowBox), " ", isbitstype(FastBox))   # false true
```

## Parametrikus típusok
<!-- q: Hogyan használjak parametrikus típusokat és where záradékot Juliában? -->
<!-- tags: parametric types, generics, where, invariance, ntuple, type parameters -->

A parametrikus típus (`Point{T}`) a generikusok Julia-megfelelője: minden konkrét `T`-re a fordító külön, specializált kódot generál, így a generikus kód sem lassabb a kézzel írt változatnál. A metódusokban a `where {T}` záradék köti meg a típusparamétert, felső korláttal is (`T<:Real`). A típusparaméterek invariánsak: `Vector{Int}` nem altípusa `Vector{Real}`-nek, ezért szignatúrában `Vector{<:Real}`-t kell írni. Érték is lehet típusparaméter (`FixedVec{N,T}`), így a méret fordítási időben ismert. Buktató: vegyes típusú argumentumokhoz (`Point(1, 2.5)`) külső, `promote`-ot használó konstruktor kell.

```julia
struct Point{T<:Real}
    x::T
    y::T
end
Point(x::Real, y::Real) = Point(promote(x, y)...)   # vegyes típusok -> közös típus

p1 = Point(1, 2)            # Point{Int64}
p2 = Point(1, 2.5)          # Point{Float64} a promote miatt
println(typeof(p1), " ", typeof(p2))

Base.:+(a::Point, b::Point) = Point(a.x + b.x, a.y + b.y)
norm2(p::Point{T}) where {T<:AbstractFloat} = sqrt(p.x^2 + p.y^2)   # csak lebegőpontosra
println(p1 + p2, " ", norm2(p2))

# Invariancia
println(Vector{Int} <: Vector{Real})        # false
println(Vector{Int} <: Vector{<:Real})      # true – szignatúrában így írd
mean_x(ps::AbstractVector{<:Point}) = sum(p -> p.x, ps) / length(ps)
println(mean_x([p1, Point(3, 4)]))

# Parametrikus konténer típusparaméteres konstruktorral
struct RingBuffer{T}
    data::Vector{T}
    capacity::Int
end
RingBuffer{T}(cap::Int) where {T} = RingBuffer{T}(T[], cap)

function Base.push!(rb::RingBuffer{T}, x) where {T}
    push!(rb.data, convert(T, x))           # konverzió a tárolt típusra
    length(rb.data) > rb.capacity && popfirst!(rb.data)
    return rb
end
Base.eltype(::Type{RingBuffer{T}}) where {T} = T

rb = RingBuffer{Float64}(3)
foreach(x -> push!(rb, x), 1:5)             # Int-ek Float64-gyé alakítva
println(rb.data, " ", eltype(typeof(rb)))   # [3.0, 4.0, 5.0] Float64

# Érték mint típusparaméter: a hossz fordítási időben ismert
struct FixedVec{N,T}
    data::NTuple{N,T}
end
Base.length(::FixedVec{N}) where {N} = N
println(length(FixedVec((1.0, 2.0, 3.0))))  # 3

const Point2D = Point{Float64}              # típusalias
println(Point2D(1, 2))
```

## Típusstabilitás és @code_warntype
<!-- q: Mi a típusstabilitás Juliában és hogyan ellenőrizzem @code_warntype-pal? -->
<!-- tags: type stability, code_warntype, inferred, performance, function barrier, globals -->

Egy függvény típusstabil, ha a visszatérési típusa csak az argumentumok *típusától* függ, nem az értékétől – ekkor a fordító végig konkrét típusokkal dolgozhat, és C-közeli kódot generál. Ha egy változó típusa menet közben változik (pl. `s = 0` majd `s += 1.5`), `Union` vagy `Any` keletkezik, ami dobozolást és dinamikus dispatch-et okoz – gyakran 10–100× lassulással. A `@code_warntype` pirossal/sárgával jelöli az ilyen helyeket, a `Test.@inferred` tesztben kényszeríti ki a stabilitást. Buktató: a nem `const` globális változók típusa ismeretlen a fordító számára – add át argumentumként, vagy izoláld a bizonytalan részt egy "function barrier" függvényhívással.

```julia
using InteractiveUtils, Test

# INSTABIL: Float64 vagy Int a visszatérés, az értéktől függően
unstable_relu(x) = x > 0 ? x : 0
# STABIL: zero(x) mindig x típusával egyezik
stable_relu(x) = x > 0 ? x : zero(x)

@code_warntype unstable_relu(1.5)   # Body::Union{Float64, Int64} – kiemelve
@code_warntype stable_relu(1.5)     # Body::Float64

# Gyakori hiba: a gyűjtőváltozó típusa a ciklusban változik
function sum_unstable(v::Vector{Float64})
    s = 0                    # Int-tel indul, majd Float64 -> Union
    for x in v
        s += x
    end
    return s
end
function sum_stable(v::AbstractVector{T}) where {T}
    s = zero(T)              # a kezdőérték típusa az elemtípus
    for x in v
        s += x
    end
    return s
end

# Globális változók: a nem-const globál típusa ismeretlen
data = rand(10^6)
const DATA = rand(10^6)
f_global() = sum(x -> x^2, data)    # lassú: data típusa bármikor változhat
f_const()  = sum(x -> x^2, DATA)    # gyors: a típus rögzített
f_arg(v)   = sum(x -> x^2, v)       # a legjobb: argumentumként

# Function barrier: a bizonytalan típusú bemenetet egy hívással izoláljuk
kernel(v::Vector{Float64}) = sum(abs2, v) / length(v)   # specializáltan fordul
function process(raw::Vector{Any})
    v = Float64[x for x in raw]     # innentől konkrét típus
    return kernel(v)
end
println(process(Any[1, 2.5, 3]))

# Tesztben kikényszerítve
@inferred stable_relu(2.0)
@test_throws ErrorException @inferred unstable_relu(2.0)
println(sum_stable([1.0, 2.0]) == sum_unstable([1.0, 2.0]))
```

## Teljesítmény-optimalizálás
<!-- q: Hogyan írjak gyors, allokációmentes kódot Juliában? -->
<!-- tags: performance, allocations, views, inbounds, preallocation, benchmarktools, column major -->

A gyors Julia kód három pillére: típusstabilitás, kevés allokáció és memóriabarát hozzáférés. A tömbök oszlopfolytonosak (column-major), ezért a belső ciklus a sorindexen fusson; a szeletelés (`A[:, j]`) alapból másolatot készít, a `@view`/`@views` viszont allokáció nélküli nézetet ad. A forró ciklusban előre foglalt puffereket és in-place (`!` végű) függvényeket használj, a fused broadcast (`@.`) pedig köztes tömbök nélkül számol. Mérésre a BenchmarkTools `@btime`-ja való (a `$` interpolációval), mert a `@time` első hívása a fordítást is méri. Buktató: az `@inbounds` kikapcsolja a határellenőrzést – hibás indexnél csendes memóriasérülés lehet, ezért csak bizonyítottan helyes ciklusra tedd.

```julia
using BenchmarkTools, LinearAlgebra

# 1) Oszlopfolytonos bejárás: a belső ciklus a sorindex (i)
function colsum_fast(A::Matrix{Float64})
    s = 0.0
    @inbounds for j in axes(A, 2), i in axes(A, 1)   # j külső, i belső ciklus
        s += A[i, j]
    end
    return s
end

# 2) In-place lépés: kimenet előre foglalt pufferbe, fused broadcast
function step!(out::Vector{Float64}, x::Vector{Float64}, dt)
    @. out = x + dt * sin(x)        # egyetlen ciklus, nincs köztes tömb
    return out
end

# 3) @view: a szelet nem másolódik
col_norms(A) = [norm(@view A[:, j]) for j in axes(A, 2)]

# 4) Puffercsere iterációk között: nulla allokáció a ciklusban
function simulate(x0::Vector{Float64}, steps::Int, dt::Float64)
    x, buf = copy(x0), similar(x0)
    for _ in 1:steps
        step!(buf, x, dt)
        x, buf = buf, x
    end
    return x
end

A  = rand(1000, 1000)
x0 = rand(10_000)
@btime colsum_fast($A)              # $: a globális változó ne torzítsa a mérést
@btime col_norms($A)
@btime simulate($x0, 100, 0.01)     # figyeld az allokációk számát is!
println(@allocated simulate(x0, 100, 0.01), " bájt")

# Profilozás:
# using Profile; @profile simulate(x0, 10_000, 0.01); Profile.print(maxdepth = 12)
```

## Broadcasting
<!-- q: Hogyan működik a broadcasting és a pont-szintaxis Juliában? -->
<!-- tags: broadcasting, dot syntax, vectorization, fusion, ref, broadcastable -->

A pont-szintaxis (`f.(x)`, `.+`, `.*`) bármely függvényt elemenként alkalmaz, automatikus méretkiterjesztéssel (oszlop- és sorvektorból mátrix lesz, mint a NumPy-ban). A láncolt pontos műveletek egyetlen ciklussá olvadnak (fusion), köztes tömbök nélkül, a `.=` pedig helyben ír egy meglévő tömbbe; a `@.` makró egy kifejezés minden műveletét pontossá teszi. Ha egy argumentum ne iterálódjon (halmaz, objektum), `Ref()`-be csomagold, saját típusnál pedig a `Base.broadcastable` határozza meg a viselkedést. Buktató: pont nélkül a `*` és a `^` mátrixműveletet jelent – `M * M` mátrixszorzás, `M .* M` elemenkénti szorzás.

```julia
using Statistics

x = [1.0, 2.0, 3.0]
y = x .^ 2 .+ 1                  # [2.0, 5.0, 10.0]
println(sin.(x))                 # saját függvényre is: f.(x)

# Fúzió: egyetlen ciklus, köztes tömb nélkül; .= helyben ír
z = similar(x)
z .= 2 .* x .+ sin.(x)
@. z = 2x + sin(x)               # ugyanaz a @. makróval

# Méretkiterjesztés: oszlop × sor -> mátrix
col = [1, 2, 3]                  # 3 elemű vektor (oszlop)
row = [10 20 30 40]              # 1×4 mátrix
table = col .* row               # 3×4 szorzótábla
println(size(table))

# Oszloponkénti standardizálás ciklus nélkül
X  = rand(100, 5) .* [1 10 100 1000 10000]
μ  = mean(X, dims = 1)           # 1×5
σ  = std(X, dims = 1)
Xn = (X .- μ) ./ σ
println(round.(mean(Xn, dims = 1), digits = 10))

# Páronkénti távolságmátrix broadcasttal
pts = rand(50, 2)
D = sqrt.((pts[:, 1] .- pts[:, 1]') .^ 2 .+ (pts[:, 2] .- pts[:, 2]') .^ 2)
println(size(D))

# Ne iterálódjon: Ref() – a string eleve skalárként viselkedik
words = ["alma", "körte", "szilva"]
println(occursin.("a", words))
println(in.(words, Ref(Set(["alma", "szilva"]))))

# Saját típus skalárként broadcastolva
struct Money
    cents::Int
end
Base.broadcastable(m::Money) = Ref(m)
add(m::Money, c::Int) = Money(m.cents + c)
println(add.(Money(100), [1, 2, 3]))

# Mátrix- vs elemenkénti művelet
M = [1 2; 3 4]
println(M * M)                   # mátrixszorzás
println(M .* M)                  # elemenkénti
println(M^2 == M * M, " ", M .^ 2)
```

## Makrók
<!-- q: Hogyan írjak saját makrót Juliában és mi a makrohigiénia? -->
<!-- tags: macros, metaprogramming, esc, hygiene, quote, code generation, macroexpand -->

A makró a forráskódot (AST-t, `Expr`) kapja meg fordítás *előtt*, és új kódot ad vissza – így lehet a kódot átírni, időmérést, assertet vagy ismétlődő definíciókat generálni (`@time`, `@test`, `@inbounds` is makró). A makrohigiénia miatt a makró saját lokális változói automatikusan egyedi nevet kapnak (gensym), így nem ütköznek a hívó változóival; a felhasználótól kapott kifejezést `esc()`-pel kell "kiengedni", hogy a hívó környezetében értékelődjön ki. A `@macroexpand` megmutatja a generált kódot. Buktató: makrót csak akkor írj, ha függvénnyel nem oldható meg – például ha a kifejezés szövegére vagy késleltetett kiértékelésére van szükség.

```julia
# Időmérő makró: a kifejezést körbeveszi méréssel
macro timeit(label, expr)
    quote
        local t0 = time_ns()
        local val = $(esc(expr))             # a hívó környezetében értékelődik ki
        local dt = (time_ns() - t0) / 1e6
        println($(esc(label)), ": ", round(dt, digits = 3), " ms")
        val
    end
end

result = @timeit "összegzés" sum(abs2, rand(10^6))

# Assert-szerű makró, ami a feltétel forrásszövegét is kiírja
macro check(cond, msg = "")
    text = string(cond)                      # a kifejezés szövege fordításkor
    :($(esc(cond)) || throw(AssertionError(string($text, " nem teljesül. ", $(esc(msg))))))
end

x = 5
@check x > 0 "x legyen pozitív"
try
    @check x > 10 "túl kicsi"
catch e
    println(e.msg)                           # x > 10 nem teljesül. túl kicsi
end

# Kódgenerálás: getter-függvények egy mezőlistából
macro getters(T, fields...)
    defs = map(fields) do f
        fname = Symbol(:get_, f)
        :($fname(obj::$T) = getfield(obj, $(QuoteNode(f))))
    end
    esc(Expr(:block, defs...))               # a hívó modulban definiáljuk
end

struct Config
    host::String
    port::Int
end
@getters Config host port
println(get_port(Config("localhost", 5432)))   # 5432

# A generált kód megtekintése
println(@macroexpand @check x > 0)
```

## Metaprogramozás: Expr, @eval és generált függvények
<!-- q: Hogyan generáljak kódot programból Juliában (Expr, @eval, @generated)? -->
<!-- tags: metaprogramming, expr, eval, generated functions, code generation, symbols, ast -->

A Julia kód maga is adat: a `Meta.parse` vagy a `:( ... )` idézés `Expr` fát ad (`head` + `args`), ami rekurzívan bejárható és átírható. A `@eval` ciklusban sok hasonló metódust definiálhat (pl. operátorok egy típusra, mértékegység-konverziók táblázatból), interpolációval (`$op`). A `@generated` függvény törzsét a fordító az argumentumok *típusaiból* állítja elő, így például ciklus nélküli, kibontott kód generálható ismert hosszú tuple-re. Buktató: az `eval` mindig globális (modul) szinten fut, nem látja a lokális változókat, és futásidejű használata a forró kódban lassú – ott makró vagy closure kell.

```julia
# Kód mint adat
ex = Meta.parse("a * (b + 2)")
println(ex.head, " ", ex.args)          # call Any[:*, :a, :(b + 2)]
dump(:(b + 2))                          # a részfa szerkezete

# Rekurzív AST-átírás: minden számliterál duplázása
double_literals(x::Number) = 2x
double_literals(x) = x
double_literals(ex::Expr) = Expr(ex.head, map(double_literals, ex.args)...)
println(eval(double_literals(:(1 + 2 * 3))))   # 2 + 4 * 6 = 26

# @eval ciklusban: operátorok egy saját típusra
struct Vec3
    x::Float64
    y::Float64
    z::Float64
end
for op in (:+, :-, :*)
    @eval Base.$op(a::Vec3, b::Vec3) = Vec3($op(a.x, b.x), $op(a.y, b.y), $op(a.z, b.z))
end
println(Vec3(1, 2, 3) + Vec3(1, 1, 1))

# Függvények generálása táblázatból
for (name, factor) in ((:km_to_m, 1000), (:h_to_s, 3600), (:kg_to_g, 1000))
    @eval $name(x) = x * $factor
end
println(km_to_m(2.5), " ", h_to_s(0.5))

# @generated: a törzs a TÍPUSOKBÓL készül fordításkor (itt t típus, nem érték!)
@generated function unrolled_sum(t::NTuple{N,T}) where {N,T}
    N == 0 && return :(zero(T))
    terms = [:(t[$i]) for i in 1:N]
    return :(+($(terms...)))            # t[1] + t[2] + ... ciklus nélkül
end
println(unrolled_sum((1, 2, 3, 4)))     # 10

# Szimbólumok és interpoláció
field = :y
println(getproperty(Vec3(1, 2, 3), field))   # 2.0
println(:(f($field, $(1 + 2))))              # f(y, 3)
```

## Többszálú párhuzamosság
<!-- q: Hogyan írjak többszálú, párhuzamos kódot Juliában? -->
<!-- tags: multithreading, threads, spawn, atomic, lock, race condition, parallelism -->

A Julia szálakat a `julia --threads=auto` (vagy a `JULIA_NUM_THREADS` környezeti változó) kapcsolja be; a `Threads.@threads` egy ciklus iterációit osztja szét, a `Threads.@spawn` dinamikus, work-stealing ütemezésű taskot indít, amelynek eredménye `fetch`-csel kérhető le. Közös változót atomi művelettel (`Atomic`, `atomic_add!`) vagy zárral (`ReentrantLock`) kell védeni, de a legjobb, ha minden task saját részeredményt számol, és a végén összegzünk. Buktató: a `threadid()`-vel indexelt közös puffer nem biztonságos, mert egy task futás közben szálat válthat – használj chunkonkénti lokális akkumulátort.

```julia
using Base.Threads

println("Szálak: ", nthreads())

# @threads: független iterációk, előre foglalt kimenetbe írva (nincs verseny)
function mandel_rows(h, w; maxit = 200)
    img = Matrix{Int}(undef, h, w)
    @threads for i in 1:h
        for j in 1:w
            c = complex(-2.0 + 3.0 * (j - 1) / w, -1.2 + 2.4 * (i - 1) / h)
            z = 0.0im
            n = 0
            while abs2(z) <= 4 && n < maxit
                z = z * z + c
                n += 1
            end
            img[i, j] = n
        end
    end
    return img
end

# @spawn: chunkonkénti részösszeg, majd összegzés (lokális akkumulátor minta)
function psum(v::AbstractVector; chunks = nthreads())
    parts = Iterators.partition(eachindex(v), cld(length(v), chunks))
    tasks = [@spawn sum(@view v[r]) for r in parts]
    return sum(fetch, tasks)
end

# Versenyhelyzet és megoldásai
function count_bad(n)
    c = 0
    @threads for _ in 1:n
        c += 1                         # HIBÁS: nem atomi, elvesznek frissítések
    end
    return c
end
function count_atomic(n)
    c = Atomic{Int}(0)
    @threads for _ in 1:n
        atomic_add!(c, 1)
    end
    return c[]
end
function count_lock(n)
    lk = ReentrantLock()
    c = Ref(0)
    @threads for _ in 1:n
        lock(lk) do                    # kritikus szakasz
            c[] += 1
        end
    end
    return c[]
end

v = rand(10^7)
println(psum(v) ≈ sum(v))
println(count_bad(10^5), " vs ", count_atomic(10^5), " vs ", count_lock(10^5))
println(sum(mandel_rows(200, 300)))
```

## Taskok és Channelek
<!-- q: Hogyan építsek producer–consumer pipeline-t taskokkal és Channelekkel Juliában? -->
<!-- tags: tasks, channels, async, producer consumer, concurrency, timeout, sync -->

A Task kooperatív korutin, amely I/O-nál, `sleep`-nél vagy `wait`-nél átadja a vezérlést; az `@async` az aktuális szálon, a `Threads.@spawn` bármely szálon futtatja. A Channel szálbiztos, opcionálisan korlátos sor taskok között: a `put!` blokkol, ha tele van (természetes backpressure), a `close` jelzi a fogyasztóknak a végét, és a Channel `for` ciklussal bejárható a lezárásig. A `@sync` blokk megvárja az összes benne indított taskot, a `timedwait` időkorláttal vár. Buktató: a taskban dobott kivétel csak a `fetch`/`wait` híváskor jelenik meg (`TaskFailedException`-be csomagolva) – ha senki nem várja meg, a hiba csendben elveszhet.

```julia
# Termelő: számokat tesz a csatornába, majd lezárja
function producer(ch::Channel{Int}, n)
    for i in 1:n
        put!(ch, i)                    # blokkol, ha a puffer tele
    end
    close(ch)                          # jelzés a fogyasztóknak
end

function run_pipeline(n; workers = 4)
    jobs    = Channel{Int}(32)         # korlátos puffer -> backpressure
    results = Channel{Tuple{Int,Float64}}(Inf)

    @async producer(jobs, n)
    consumers = map(1:workers) do _
        Threads.@spawn for job in jobs # a Channel a lezárásig iterálható
            sleep(0.001)               # szimulált I/O
            put!(results, (job, sqrt(job)))
        end
    end
    foreach(wait, consumers)           # a kivételek itt jelennek meg
    close(results)
    return sort!(collect(results))
end

res = run_pipeline(100)
println(length(res), " eredmény, utolsó: ", res[end])

# Időkorlátos várakozás egy task eredményére
function with_timeout(f, seconds)
    t = @async f()
    status = timedwait(() -> istaskdone(t), seconds; pollint = 0.01)
    status === :ok || error("Időtúllépés ($seconds s)")
    return fetch(t)                    # hibás task esetén TaskFailedException
end

println(with_timeout(() -> (sleep(0.05); :kész), 1.0))
try
    with_timeout(() -> (sleep(2); :késő), 0.2)
catch e
    println("Hiba: ", e.msg)
end

# @sync: megvárja a blokkban indított összes taskot
@sync for name in ["a", "b", "c"]
    @async begin
        sleep(rand() * 0.05)
        println("kész: ", name)
    end
end
```

## Csomagok, környezetek és modulok
<!-- q: Hogyan kezeljem a csomagokat és környezeteket Pkg-vel, és hogyan írjak saját modult Juliában? -->
<!-- tags: pkg, packages, environments, project.toml, manifest, modules, testing -->

A Julia csomagkezelője (Pkg) projektenkénti környezetekkel dolgozik: a `Project.toml` a közvetlen függőségeket és a `[compat]` verziókorlátokat, a `Manifest.toml` a teljes, pontosan rögzített függőségi fát tartalmazza – alkalmazásnál mindkettőt commitold a reprodukálhatóságért. A `Pkg.activate(".")` + `Pkg.instantiate()` egy klónozott projektet pontosan visszaállít. A kód modulokba szerveződik: az `export` határozza meg a `using` után minősítés nélkül elérhető neveket, az `__init__` betöltéskor fut, a tesztek a `test/runtests.jl`-ben a `Test` csomaggal készülnek. Buktató: a globális (alapértelmezett) környezetbe telepített csomagok verzióütközést okozhatnak – projektenként külön környezetet használj.

```julia
# Környezetkezelés (REPL-ben a ] billentyűvel csomagmódba is léphetsz)
using Pkg
Pkg.activate(".")                          # a mappa saját környezete
Pkg.add(["DataFrames", "CSV"])             # Project.toml-ba kerül
Pkg.add(name = "Plots", version = "1.40")  # konkrét verzió
Pkg.instantiate()                          # klónozott projekt: pontosan a Manifest verziói
Pkg.status()
# Pkg.develop(path = "../GeoTools")        # helyi csomag fejlesztése
# Pkg.generate("GeoTools")                 # új csomag váza
```

```julia
# src/GeoTools.jl – saját csomag fő modulja
module GeoTools

using LinearAlgebra: norm          # csak a szükséges név importálása
export Point, distance, centroid   # `using GeoTools` után minősítés nélkül elérhetők

# include("io.jl")                 # nagyobb csomagnál több fájlra bontva

struct Point
    x::Float64
    y::Float64
end

"""
    distance(a::Point, b::Point) -> Float64

Két pont euklideszi távolsága.
"""
distance(a::Point, b::Point) = norm([a.x - b.x, a.y - b.y])

centroid(ps::AbstractVector{Point}) =
    Point(sum(p -> p.x, ps) / length(ps), sum(p -> p.y, ps) / length(ps))

# Betöltéskor fut (nem előfordításkor) – pl. környezeti változók, C könyvtárak
function __init__()
    @debug "GeoTools betöltve"
end

end # module
```

```julia
# test/runtests.jl – futtatás: ] test GeoTools  vagy  Pkg.test("GeoTools")
using Test, GeoTools

@testset "GeoTools" begin
    @test distance(Point(0, 0), Point(3, 4)) ≈ 5
    @test centroid([Point(0, 0), Point(2, 2)]) == Point(1, 1)
    @test_throws MethodError distance(Point(0, 0), (3, 4))
end
```

## Interfészek: iteráció és AbstractArray
<!-- q: Hogyan tegyem a saját típusomat iterálhatóvá vagy tömbként használhatóvá Juliában? -->
<!-- tags: interfaces, iteration, abstractarray, iterate, getindex, duck typing, generic programming -->

A Julia interfészei informálisak: ha egy típus megvalósítja a szükséges metódusokat, az egész ökoszisztéma működik rajta. Az iterációs interfészhez a `Base.iterate(x)` és `Base.iterate(x, state)` kell (opcionálisan `length` és `eltype`), és utána a `for`, `collect`, `sum`, generátorok mind használhatók. Az `AbstractMatrix` altípusához elég a `size` és a `getindex`: a kiírás, a mátrix–vektor szorzás, a broadcast és a transzponálás generikus fallbackkel azonnal működik, a szűk keresztmetszetekre pedig specializált metódus írható. Buktató: a generikus fallback helyes, de lehet lassú (pl. O(n²) elemenkénti elérés) – a forró műveleteket specializáld.

```julia
using LinearAlgebra

# 1) Iterációs interfész: Fibonacci-sorozat első n eleme
struct Fibonacci
    n::Int
end
# Az állapot: (aktuális, következő, darabszám)
Base.iterate(f::Fibonacci, state = (0, 1, 0)) =
    state[3] >= f.n ? nothing : (state[1], (state[2], state[1] + state[2], state[3] + 1))
Base.length(f::Fibonacci) = f.n
Base.eltype(::Type{Fibonacci}) = Int

println(collect(Fibonacci(10)))          # [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
println(sum(Fibonacci(10)), " ", maximum(Fibonacci(10)))
println([x^2 for x in Fibonacci(8) if isodd(x)])

# 2) AbstractArray interfész: cirkuláns mátrix O(n) memóriával
struct Circulant{T} <: AbstractMatrix{T}
    c::Vector{T}                         # csak az első oszlopot tároljuk
end
Base.size(A::Circulant) = (length(A.c), length(A.c))
Base.getindex(A::Circulant, i::Int, j::Int) = A.c[mod1(i - j + 1, length(A.c))]

C = Circulant([1, 2, 3, 4])
display(C)                               # mátrixként íródik ki
println(C * ones(4))                     # generikus mátrix–vektor szorzás
println(C' == transpose(C))              # lusta Adjoint
println(sum(C, dims = 1))
println(typeof(C .+ 1))                  # broadcast eredménye sima Matrix

# Specializált, gyorsabb metódus a generikus fallback helyett
LinearAlgebra.tr(A::Circulant) = length(A.c) * A.c[1]   # O(1) az O(n) helyett
println(tr(C))                           # 4
```

## Hibakezelés és saját kivételek
<!-- q: Hogyan kezeljem a hibákat és írjak saját kivételtípust Juliában? -->
<!-- tags: exceptions, error handling, try catch, finally, showerror, tryparse, logging -->

Juliában a kivétel az `Exception` altípusa; saját típussal strukturált adat (melyik mező, miért) adható át, a `Base.showerror` pedig szép üzenetet ad. A `try/catch` blokkban a `rethrow()` továbbdobja a nem várt hibát, a `finally` garantált takarítást ad (fájlnál a `do`-blokkos `open` ugyanezt teszi automatikusan). Várható hiányra (pl. érvénytelen szám egy CSV-ben) olcsóbb a `tryparse` + `nothing` ellenőrzés, mint a kivétel, mert a kivétel kezelése drága. Buktató: a túl tág `catch` elnyelheti a programozási hibákat (`MethodError`, `UndefVarError`) – mindig szűrj típusra.

```julia
struct ValidationError <: Exception
    field::Symbol
    msg::String
end
Base.showerror(io::IO, e::ValidationError) = print(io, "ValidationError(", e.field, "): ", e.msg)

struct Order
    id::Int
    qty::Int
    price::Float64
end

function parse_order(row::AbstractString)
    parts = split(row, ',')
    length(parts) == 3 || throw(ValidationError(:row, "3 mező kell, kaptam $(length(parts))"))
    id    = tryparse(Int, parts[1])        # nothing kivétel helyett -> olcsó
    qty   = tryparse(Int, parts[2])
    price = tryparse(Float64, parts[3])
    id === nothing && throw(ValidationError(:id, "nem egész: $(parts[1])"))
    (qty === nothing || qty <= 0) && throw(ValidationError(:qty, "pozitív egész kell"))
    price === nothing && throw(ValidationError(:price, "nem szám: $(parts[3])"))
    return Order(id, qty, price)
end

rows = ["1,2,9.99", "2,0,5", "x,1,1", "4,1,2.5,extra"]
orders = Order[]
errors = Tuple{Int,Exception}[]
for (i, r) in enumerate(rows)
    try
        push!(orders, parse_order(r))
    catch e
        e isa ValidationError || rethrow()  # csak a várt hibát nyeljük el
        push!(errors, (i, e))
    end
end
println(length(orders), " érvényes rendelés")
for (i, e) in errors
    println("Sor $i: ", sprint(showerror, e))
end

# finally: garantált takarítás
function first_line(path)
    io = open(path)
    try
        return readline(io)
    finally
        close(io)
    end
end
# Ugyanez idiomatikusan: open(readline, path)  vagy  open(path) do io ... end

# Naplózás kivétellel és stacktrace-szel
try
    sqrt(-1.0)
catch e
    @error "Számítási hiba" exception = (e, catch_backtrace())
end
```

## Lineáris algebra és numerika
<!-- q: Hogyan oldjak meg lineáris egyenletrendszert és legkisebb négyzetes feladatot Juliában? -->
<!-- tags: linear algebra, factorization, cholesky, least squares, svd, eigen, structured matrices -->

A `LinearAlgebra` standard könyvtár BLAS/LAPACK-ra épül, és a dispatch itt is kulcsszerepet játszik: a `\` operátor a mátrix típusa és szerkezete alapján választ algoritmust (LU, Cholesky, QR, tridiagonális Thomas-algoritmus). Ha ugyanazzal a mátrixszal több jobboldalt kell megoldani, faktorizálj egyszer (`cholesky`, `lu`, `qr`), és a faktorizációs objektummal oldj meg. A struktúrált típusok (`Diagonal`, `Tridiagonal`, `Symmetric`) O(n) tárolást és gyorsabb algoritmusokat adnak, túlhatározott rendszernél a `\` legkisebb négyzetes megoldást számol. Buktató: soha ne számolj `inv(A) * b`-t – lassabb és numerikusan pontatlanabb, mint az `A \ b`.

```julia
using LinearAlgebra, Statistics

# Egyenletrendszer: a \ a szerkezet alapján választ algoritmust
A = [4.0 1 2; 1 5 3; 2 3 6]               # szimmetrikus, pozitív definit
b = [1.0, 2, 3]
x = A \ b                                  # NE inv(A) * b
println(norm(A * x - b) < 1e-12)

# Faktorizáció egyszer, megoldás sokszor
F = cholesky(Symmetric(A))                 # SPD mátrixra a leggyorsabb
B = rand(3, 5)
X = F \ B                                  # 5 jobboldal egyszerre
println(size(X))

# Struktúrált mátrixok: speciális algoritmusok
T = Tridiagonal(fill(-1.0, 99), fill(2.0, 100), fill(-1.0, 99))
y = T \ ones(100)                          # O(n), nem O(n³)
D = Diagonal([1.0, 2, 3])
println(D * A)                             # sorskálázás teljes szorzás nélkül

# Sajátértékek és SVD
vals, vecs = eigen(Symmetric(A))
println(round.(vals, digits = 4))
U, S, V = svd(rand(6, 4))
println(rank(A), " ", round(cond(A), digits = 2), " ", round(det(A), digits = 2))

# Legkisebb négyzetek: egyenes illesztése zajos adatra
t    = collect(0:0.1:5)
yobs = 2.0 .+ 0.7 .* t .+ 0.1 .* randn(length(t))
Xd   = [ones(length(t)) t]                 # tervezőmátrix [1 t]
β    = Xd \ yobs                           # QR-alapú LS megoldás, ≈ [2.0, 0.7]
resid = yobs - Xd * β
println("β = ", round.(β, digits = 3), ", RMSE = ", round(sqrt(mean(abs2, resid)), digits = 3))

# Allokációmentes BLAS hívás forró ciklusba
Cm = zeros(3, 3)
mul!(Cm, A, A')                            # Cm = A * A' helyben
println(Cm ≈ A * A')
```
