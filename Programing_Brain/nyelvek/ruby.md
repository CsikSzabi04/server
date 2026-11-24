# Ruby
<!-- tech: ruby -->
<!-- aliases: rails -->

A Ruby dinamikusan és erősen típusos, interpretált, tisztán objektumorientált nyelv (minden érték objektum), erős funkcionális elemekkel (blokkok, lambdák, Enumerable) és rendkívül rugalmas metaprogramozással. A referencia-implementáció (CRuby/MRI) bytecode VM-en fut, opcionális YJIT fordítóval, a memóriát generációs, tömörítő garbage collector kezeli; a GVL miatt a szálak I/O-ban párhuzamosak, CPU-munkában nem (erre valók a Ractorok vagy több processz). Fő terepe a webfejlesztés Ruby on Rails-szel, valamint szkriptek, DSL-ek és devops eszközök. Kiváló gyors termékfejlesztéshez és olvasható üzleti logikához; kevésbé ideális nyers számításigényes vagy alacsony késleltetésű rendszerekhez.

## Minden objektum: az objektummodell
<!-- q: Mit jelent, hogy Rubyban minden objektum, és hogyan működnek a nyitott osztályok? -->
<!-- tags: object model, open classes, singleton class, duck typing, comparable, coerce -->

Rubyban az egész számok, a `nil`, sőt maguk az osztályok is objektumok, az operátorok pedig közönséges metódushívások (`5 + 3` = `5.+(3)`). Az osztályok nyitottak – bármikor bővíthetők –, és minden objektumnak van egy saját singleton osztálya, ahová csak rá vonatkozó metódus tehető; az "osztálymetódus" valójában az osztály-objektum singleton metódusa. A típus helyett a viselkedés számít (duck typing): ha egy objektum válaszol a `<=>`-re, a `Comparable` mixinnel minden összehasonlítást megkap. Buktató: a beépített osztályok globális módosítása (monkey patching) könnyen ütközik gemekkel – erre a refinements a biztonságos megoldás.

```ruby
5.class                  # => Integer
nil.class                # => NilClass
Integer.class            # => Class – az osztály is objektum
5.respond_to?(:+)        # => true – az operátor is metódus
5.public_send(:+, 3)     # => 8   – dinamikus metódushívás
3.times.map { _1 * 2 }   # => [0, 2, 4] (számozott blokkparaméter, Ruby 2.7+)

# Singleton metódus: csak ezen az EGY objektumon létezik
config = Object.new
def config.env
  "production"
end
config.singleton_methods # => [:env]

class Temperature
  include Comparable           # a <=> alapján: <, >, ==, between?, clamp
  attr_reader :celsius

  # Osztálymetódus = a Temperature objektum singleton metódusa
  def self.from_fahrenheit(f) = new((f - 32) * 5.0 / 9)

  def initialize(celsius)
    @celsius = Float(celsius)  # Float() kivételt dob érvénytelen inputra, a to_f csendben 0.0-t adna
    freeze                     # érték-objektum: módosíthatatlan
  end

  def <=>(other)
    celsius <=> other.celsius
  end

  def +(other)
    Temperature.new(celsius + (other.is_a?(Temperature) ? other.celsius : other))
  end

  # coerce: így az `5 + homerseklet` is működik (Integer#+ meghívja)
  def coerce(num)
    [Temperature.new(num), self]
  end

  def to_s = format("%.1f °C", celsius)
end

temps = [Temperature.new(21), Temperature.from_fahrenheit(212), Temperature.new(-4)]
puts temps.sort.map(&:to_s).join(", ")    # -4.0 °C, 21.0 °C, 100.0 °C
puts temps.max                             # 100.0 °C
puts 5 + Temperature.new(10)               # 15.0 °C (coerce miatt)
puts Temperature.new(30).between?(temps[0], temps[1]) # true
```

## Blokkok és yield
<!-- q: Hogyan működnek a blokkok és a yield Rubyban, és hogyan adjak vissza Enumeratort? -->
<!-- tags: block, yield, block_given, enumerator, ensure, retry -->

A blokk a metódushívásnak átadott névtelen kódrész (`do ... end` vagy `{ ... }`), amit a metódus `yield`-del hív meg; a blokk visszatérési értéke a `yield` értéke lesz. Ez a Ruby legfontosabb absztrakciója: erőforrás-kezelés (a takarítás `ensure`-ben garantált), újrapróbálás, tranzakciók, iteráció. Idiomatikus, ha egy iteráló metódus blokk nélkül `Enumerator`-t ad vissza (`enum_for`), így láncolható (`with_index`, `lazy`, `each_slice`). Buktató: a `{}` erősebben köt, mint a `do...end`, ezért zárójel nélküli hívásnál (`puts list.map do ... end`) a `do` blokk a `puts`-hoz kerül.

```ruby
class TransientError < StandardError; end

# Újrapróbálás exponenciális várakozással – a blokkot ismételten meghívjuk
def with_retry(attempts: 3, on: [TransientError], base_delay: 0.05)
  tries = 0
  begin
    tries += 1
    yield tries                         # a blokk értéke lesz a metódus értéke
  rescue *on => e                       # splat: kivételosztály-lista
    raise if tries >= attempts
    warn "#{e.class}: #{e.message} – újra (#{tries}/#{attempts})"
    sleep(base_delay * 2**(tries - 1))
    retry                               # a begin blokk újrafuttatása
  end
end

result = with_retry(attempts: 4) do |n|
  raise TransientError, "hálózati hiba" if n < 3
  "siker a(z) #{n}. próbára"
end
puts result

# Erőforrás-kezelés blokkal: a visszaadás garantált (mint File.open { ... })
def with_connection(pool)
  conn = pool.checkout
  yield conn
ensure
  pool.checkin(conn) if conn
end

# Blokk nélkül Enumerator-t adunk vissza (méret-blokkal, iteráció nélküli .size-hoz)
def each_page(total, per_page)
  return enum_for(__method__, total, per_page) { (total.to_f / per_page).ceil } unless block_given?

  (0...total).step(per_page).with_index(1) do |offset, page|
    yield page, offset, [per_page, total - offset].min
  end
end

each_page(95, 20) { |page, offset, size| puts "#{page}. oldal: #{offset}+#{size}" }
p each_page(95, 20).size          # => 5 (iteráció nélkül)
p each_page(95, 20).to_a.last     # => [5, 80, 15]

# Explicit blokkparaméter: továbbadható más metódusnak
def log_each(items, &block)
  items.each { |i| puts "-> #{i}" }.each(&block)
end
log_each([1, 2]) { |i| puts i * 10 }
```

## Proc, lambda és closure-ök
<!-- q: Mi a különbség a Proc és a lambda között Rubyban? -->
<!-- tags: proc, lambda, closure, curry, composition, to_proc, method object -->

A blokk objektummá alakítva `Proc`; ennek két fajtája van. A lambda (`->(x) { }`) szigorú aritású, és a `return` csak magából a lambdából tér vissza – úgy viselkedik, mint egy metódus. A sima proc laza aritású (hiányzó argumentum `nil`, felesleges eldobva), és a `return` a *környező metódusból* lép ki, ami metóduson kívül `LocalJumpError`-t okoz. Mindkettő closure: a környező változókat (nem az értéküket!) fogja be. A `curry`, a `>>`/`<<` kompozíció, a `&:symbol` és a `method(:name)` funkcionális stílust tesz lehetővé.

```ruby
# Lambda: szigorú aritás, a return csak a lambdából tér vissza
add = ->(a, b) { a + b }
add.(1, 2)              # => 3  (.call, .() és [] ugyanaz)
begin
  add.(1)
rescue ArgumentError => e
  puts "lambda: #{e.message}"
end

# Proc: laza aritás
loose = proc { |a, b| [a, b] }
p loose.call(1)         # => [1, nil]
p loose.call(1, 2, 3)   # => [1, 2]

# Blokkban a return a METÓDUSBÓL lép ki – korai kilépéshez hasznos
def find_first_negative(nums)
  nums.each { |n| return n if n.negative? }
  nil
end
p find_first_negative([3, -2, -7])   # => -2

def proc_return_demo
  pr = Proc.new { return :from_proc }
  pr.call
  :never_reached                     # ide nem jutunk el
end
p proc_return_demo                   # => :from_proc

# Closure: a változót fogja be, nem az értékét -> közös, privát állapot
def make_counter
  count = 0
  [-> { count += 1 }, -> { count }]
end
inc, get = make_counter
3.times { inc.() }
p get.()                             # => 3

# Curry és kompozíció
tax      = ->(rate, amount) { (amount * (1 + rate)).round(2) }
with_vat = tax.curry[0.27]           # részleges alkalmazás
discount = ->(x) { x * 0.9 }
pipeline = discount >> with_vat      # előbb discount, aztán with_vat
p pipeline.(1000)                    # => 1143.0

# Symbol#to_proc és Method objektum blokként
p %w[alma korte].map(&:upcase)       # => ["ALMA", "KORTE"]
p %w[1 2 3].map(&method(:Integer))   # => [1, 2, 3]
```

## Modulok és mixinek
<!-- q: Hogyan használjam a modulokat mixinként Rubyban (include, extend, prepend)? -->
<!-- tags: module, mixin, include, extend, prepend, ancestors, concern -->

A modul névtér és mixin egyben: nem példányosítható, de metódusait "bekeverhetjük" osztályokba. Az `include` a modult az osztály *mögé* teszi a metóduskeresési láncban (példánymetódusok), az `extend` az objektum/osztály singleton osztályába (osztálymetódusok), a `prepend` pedig az osztály *elé*, így a modul metódusa `super`-rel körbeveheti az eredetit (naplózás, időmérés, cache). Az `included` hook-kal egy modul egyszerre adhat példány- és osztálymetódusokat – ez az ActiveSupport::Concern alapötlete. A `Klass.ancestors` mindig megmutatja a tényleges keresési sorrendet.

```ruby
module Auditable
  # Hook: amikor egy osztály include-olja, osztálymetódusokat is kap
  def self.included(base)
    base.extend(ClassMethods)
  end

  module ClassMethods
    def audited_fields(*fields)
      @audited_fields = fields
    end

    def audited
      @audited_fields || []
    end
  end

  def audit_log
    @audit_log ||= []
  end

  # Mely auditált mezők változtak egy korábbi állapothoz képest
  def changes_since(old)
    self.class.audited.filter_map do |f|
      [f, old[f], public_send(f)] if old[f] != public_send(f)
    end
  end
end

# prepend: a lánc elejére kerül -> "around" viselkedés super-rel
module Timing
  def save
    started = Process.clock_gettime(Process::CLOCK_MONOTONIC)
    result = super                                     # az eredeti Product#save
    elapsed = Process.clock_gettime(Process::CLOCK_MONOTONIC) - started
    audit_log << format("save %.3f ms", elapsed * 1000)
    result
  end
end

class Product
  include Auditable
  prepend Timing
  audited_fields :name, :price

  attr_accessor :name, :price

  def initialize(name, price)
    @name = name
    @price = price
  end

  def save
    true # ... perzisztálás
  end
end

p Product.ancestors.first(3)                     # => [Timing, Product, Auditable]
item = Product.new("Toll", 490)
item.save
p item.audit_log                                 # => ["save 0.002 ms"]
p item.changes_since({ name: "Toll", price: 390 }) # => [[:price, 390, 490]]

# module_function: modul mint függvénygyűjtemény (Math-szerű)
module Units
  module_function

  def km_to_mi(km) = km * 0.621371
end
p Units.km_to_mi(10).round(2)                     # => 6.21
```

## Metaprogramozás: method_missing
<!-- q: Hogyan használjam a method_missing-et és a respond_to_missing?-et Rubyban? -->
<!-- tags: metaprogramming, method_missing, respond_to_missing, dynamic finder, proxy, ghost methods -->

A `method_missing` akkor fut, ha a metóduskeresés sikertelen – így "szellem-metódusok" (pl. `find_by_email`) és átlátszó proxyk készíthetők. Mindig párosítsd `respond_to_missing?`-gel, különben a `respond_to?` és a `method(:x)` hazudni fog, és minden nem kezelt esetben hívd meg a `super`-t, hogy a `NoMethodError` megmaradjon. Teljesítmény: a `method_missing` lassú (végigjárja a teljes láncot), ezért bevett trükk, hogy az első híváskor valódi metódust definiálunk. Buktató: a túlzott használat nehezen debugolható kódot ad – ha a nevek előre ismertek, a `define_method` jobb választás.

```ruby
class Repository
  FINDER = /\A(find_by|find_all_by)_(\w+?)(!)?\z/

  def initialize(records)
    @records = records
  end

  def method_missing(name, *args, &block)
    match = FINDER.match(name.to_s)
    return super unless match && args.size == 1   # minden mást az ősre bízunk -> NoMethodError

    kind, field, bang = match.captures
    results = @records.select { |r| r[field.to_sym] == args.first }
    return results if kind == "find_all_by"

    results.first || (bang ? raise(KeyError, "nincs #{field}=#{args.first}") : nil)
  end

  # KÖTELEZŐ pár: respond_to? és method() is helyesen működjön
  def respond_to_missing?(name, include_private = false)
    FINDER.match?(name.to_s) || super
  end
end

repo = Repository.new([
  { email: "a@example.com", role: "admin" },
  { email: "b@example.com", role: "user" }
])
p repo.find_by_email("b@example.com")      # => {email: "b@example.com", role: "user"}
p repo.find_all_by_role("admin").size      # => 1
p repo.respond_to?(:find_by_role)          # => true
begin
  repo.find_by_role!("guest")
rescue KeyError => e
  puts e.message
end

# Teljesítmény-trükk: az első hívás után valódi (singleton) metódust definiálunk
class LazyConfig
  def initialize(hash)
    @data = hash.transform_keys(&:to_s)
  end

  def method_missing(name, *args)
    key = name.to_s
    return super unless args.empty? && @data.key?(key)

    singleton_class.define_method(name) { @data[key] } # csak ERRE a példányra
    public_send(name)
  end

  def respond_to_missing?(name, include_private = false)
    @data.key?(name.to_s) || super
  end
end

cfg = LazyConfig.new(host: "localhost", port: 5432)
p cfg.port                          # method_missing -> definiál
p cfg.singleton_methods             # => [:port]
```

## Metaprogramozás: define_method és osztálymakrók
<!-- q: Hogyan generáljak metódusokat define_method-dal és írjak osztálymakrót Rubyban? -->
<!-- tags: define_method, class macro, dsl, instance_variable_get, inherited, metaprogramming -->

Az osztálytörzs is futó kód, ezért a `has_many`, `validates`, `attr_accessor` stílusú "osztálymakrók" egyszerű osztálymetódusok, amelyek `define_method`-dal futásidőben generálnak metódusokat. A `define_method` blokkja closure, így a generált metódus látja a makró paramétereit (mezőnév, típus, alapérték), és benne a `return` a metódusból tér vissza. Az `inherited` hook-kal a leszármazott saját másolatot kaphat a metaadatokból, így a gyerekosztály bővítése nem szennyezi az őst. Buktató: a generált metódusok nem látszanak a forrásban – dokumentáld a DSL-t, és ellenőrizd a nevek ütközését.

```ruby
module Attributes
  def self.extended(base)
    base.instance_variable_set(:@attribute_defs, {})
  end

  # Osztálymakró: attribute :age, :integer, default: 0
  def attribute(name, type, default: nil)
    @attribute_defs[name] = { type:, default: }     # Ruby 3.1 hash shorthand
    ivar = :"@#{name}"

    # Getter: lusta alapértelmezés (a lambda-default minden példánynak friss értéket ad)
    define_method(name) do
      return instance_variable_get(ivar) if instance_variable_defined?(ivar)

      default.respond_to?(:call) ? default.call : default
    end

    # Setter típuskonverzióval
    define_method(:"#{name}=") do |value|
      cast = case type
             when :integer then Integer(value)
             when :string  then String(value)
             when :boolean then [true, "true", "1", 1].include?(value)
             else raise ArgumentError, "ismeretlen típus: #{type}"
             end
      instance_variable_set(ivar, cast)
    end

    define_method(:"#{name}?") { !!public_send(name) } if type == :boolean
  end

  def attribute_names = @attribute_defs.keys

  # Öröklésnél a leszármazott saját másolatot kap
  def inherited(sub)
    super
    sub.instance_variable_set(:@attribute_defs, @attribute_defs.dup)
  end
end

class User
  extend Attributes
  attribute :name, :string
  attribute :age, :integer, default: 0
  attribute :active, :boolean, default: -> { true }

  def initialize(**attrs)
    attrs.each { |k, v| public_send(:"#{k}=", v) }
  end
end

class Admin < User
  attribute :level, :integer, default: 1
end

u = User.new(name: "Teszt", age: "42")
p u.age                         # => 42 (Integer-ré konvertálva)
p u.active?                     # => true
p User.attribute_names          # => [:name, :age, :active]
p Admin.attribute_names         # => [:name, :age, :active, :level]
p User.instance_methods(false).sort.first(4)
```

## Refinements: biztonságos monkey patching
<!-- q: Hogyan bővítsem a beépített osztályokat globális mellékhatás nélkül Rubyban? -->
<!-- tags: refinements, monkey patching, using, lexical scope, core extensions -->

A refinement lokális monkey patch: a `refine String do ... end` blokkban definiált metódusok csak ott élnek, ahol a modult `using`-gal aktiváltuk, és csak a fájl vagy osztály/modul törzsének végéig (lexikális hatókör). Így egy könyvtár kényelmes core-bővítéseket használhat anélkül, hogy más gemek vagy az alkalmazás viselkedését megváltoztatná. A `refine` blokkon belül maga a refinement is aktív, így a bővítések egymást hívhatják. Buktató: a `respond_to?` nem látja a refinementet, metóduson belül `using` nem hívható, és dinamikus hívásoknál (`method`, `instance_method`) a régebbi Ruby-verziók eltérően viselkednek.

```ruby
module StringCase
  refine String do
    def snake_case
      gsub(/([a-z\d])([A-Z])/, '\1_\2').tr("-", "_").downcase
    end

    def camel_case
      split("_").each_with_index.map { |w, i| i.zero? ? w : w.capitalize }.join
    end
  end

  refine Hash do
    # Rekurzív kulcs-transzformáció JSON API-khoz
    def deep_transform_keys(&blk)
      each_with_object({}) do |(k, v), acc|
        acc[blk.call(k)] = v.is_a?(Hash) ? v.deep_transform_keys(&blk) : v
      end
    end
  end
end

module ApiSerializer
  using StringCase # innentől a modultörzs végéig aktív

  def self.to_api(hash)
    hash.deep_transform_keys { |k| k.to_s.camel_case }
  end

  def self.from_api(hash)
    hash.deep_transform_keys { |k| k.to_s.snake_case.to_sym }
  end
end

payload = ApiSerializer.to_api({ user_id: 1, billing_address: { zip_code: "1011" } })
p payload                                  # => {"userId"=>1, "billingAddress"=>{"zipCode"=>"1011"}}
p ApiSerializer.from_api(payload)          # => {user_id: 1, billing_address: {zip_code: "1011"}}

# A refinementen kívül nincs hatása:
p "UserId".respond_to?(:snake_case)        # => false
begin
  "UserId".snake_case
rescue NoMethodError
  puts "itt nem elérhető – nincs globális mellékhatás"
end
```

## Enumerable, Enumerator és lazy kiértékelés
<!-- q: Hogyan használjam az Enumerable modult és a lazy enumerátorokat Rubyban? -->
<!-- tags: enumerable, enumerator, lazy, tally, group_by, each_slice, infinite sequence -->

Ha egy osztály megvalósítja az `each`-et és include-olja az `Enumerable`-t, ingyen kap több mint 50 metódust (`map`, `select`, `group_by`, `tally`, `each_slice`, `chunk_while`, `min_by`, `sum`…). A `lazy` láncot épít, amely elemenként halad és csak annyit számol, amennyi kell – végtelen sorozatokhoz (`(2..)`) és nagy fájlokhoz konstans memóriával. Az `Enumerator.new` generátor-szerű külső iterációt ad (`next`, `peek`). Buktató: nem lazy láncban minden lépés teljes köztes tömböt hoz létre, a lazy viszont kis kollekcióknál a többletköltség miatt lassabb is lehet.

```ruby
require "stringio"

class LogFile
  include Enumerable
  Entry = Data.define(:time, :level, :message) # Ruby 3.2 immutable value object

  def initialize(io)
    @io = io
  end

  # Az each az egyetlen kötelező metódus; blokk nélkül Enumerator
  def each
    return enum_for(:each) unless block_given?

    @io.each_line do |line|
      time, level, message = line.chomp.split(" ", 3)
      next unless message                      # hibás sor kihagyása
      yield Entry.new(time:, level: level.to_sym, message:)
    end
  end
end

log = LogFile.new(StringIO.new(<<~LOG))
  10:00:01 INFO indul a szerver
  10:00:02 WARN lassú lekérdezés 1200ms
  10:00:03 ERROR adatbázis timeout
  10:00:04 ERROR adatbázis timeout
LOG

p log.map(&:level).tally                             # => {INFO: 1, WARN: 1, ERROR: 2}
p log.group_by(&:level).transform_values(&:count)    # ugyanaz másképp
p log.select { _1.level == :ERROR }.map(&:message).uniq
p log.each_slice(2).map { |pair| pair.map(&:level) } # kötegelés
p log.chunk_while { |a, b| a.level == b.level }.map(&:size) # => [1, 1, 2]

# Lazy: végtelen sorozat, csak a szükséges elemek számolódnak ki
primes = (2..).lazy.select { |n| (2..Integer.sqrt(n)).none? { |d| (n % d).zero? } }
p primes.first(10)                     # => [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]

# Nagy fájl konstans memóriával, korai leállással:
# File.foreach("access.log").lazy.grep(/ 500 /).map { _1.split.first }.uniq.first(20)

# Külső iteráció: Enumerator mint generátor
fib = Enumerator.new do |y|
  a, b = 0, 1
  loop do
    y << a
    a, b = b, a + b
  end
end
p fib.take(10)                         # => [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
p [fib.next, fib.next, fib.peek]       # => [0, 1, 1]
```

## Szálak, Mutex és Queue
<!-- q: Hogyan írjak szálbiztos, párhuzamos kódot Ruby szálakkal? -->
<!-- tags: thread, mutex, queue, gvl, concurrency, worker pool, race condition -->

A CRuby szálai valódi OS-szálak, de a GVL (Global VM Lock) miatt egyszerre csak egy futtat Ruby kódot – I/O (hálózat, fájl, adatbázis) alatt viszont elengedik a zárat, ezért I/O-kötött munkára a szálak jól skáláznak. A `Queue` szálbiztos FIFO, `close` után a `pop` `nil`-t ad, ami elegáns leállítást tesz lehetővé; a közös, módosítható állapotot `Mutex#synchronize` védi. Buktató: a `+=` nem atomi, így GVL mellett is lehet versenyhelyzet; a szálban elkapatlan kivétel alapból csak a `join`-nál jelenik meg (`Thread.report_on_exception` figyelmeztet).

```ruby
# Thread pool Queue-val: I/O-kötött feladatokra
class WorkerPool
  def initialize(size)
    @jobs    = Queue.new
    @results = Queue.new
    @errors  = []
    @mutex   = Mutex.new
    @workers = Array.new(size) do |i|
      Thread.new do
        Thread.current.name = "worker-#{i}"
        # pop blokkol; lezárt és üres queue esetén nil -> kilépés
        while (job = @jobs.pop)
          begin
            @results << [job[:id], job[:work].call]
          rescue StandardError => e
            @mutex.synchronize { @errors << [job[:id], e.message] } # közös tömb védelme
          end
        end
      end
    end
  end

  def submit(id, &work)
    @jobs << { id:, work: }
  end

  def shutdown
    @jobs.close              # nincs több feladat
    @workers.each(&:join)    # megvárjuk az összes szálat
    results = []
    results << @results.pop until @results.empty?
    [results.to_h, @errors]
  end
end

pool = WorkerPool.new(4)
10.times do |i|
  pool.submit(i) do
    sleep(rand * 0.05)       # szimulált I/O (pl. HTTP hívás)
    raise "hiba a(z) #{i}. feladatban" if i == 7
    i * i
  end
end
results, errors = pool.shutdown
p results.size               # => 9
p errors                     # => [[7, "hiba a(z) 7. feladatban"]]

# Versenyhelyzet: a += nem atomi -> Mutex kell
counter = 0
lock = Mutex.new
threads = Array.new(8) do
  Thread.new { 10_000.times { lock.synchronize { counter += 1 } } }
end
threads.each(&:join)
p counter                    # => 80000
```

## Fiberek és a Fiber Scheduler
<!-- q: Mik azok a Fiberek Rubyban és hogyan segít a Fiber Scheduler az aszinkron I/O-ban? -->
<!-- tags: fiber, fiber scheduler, async, coroutine, non-blocking io, concurrency -->

A Fiber könnyűsúlyú, kooperatív korutin: csak explicit `Fiber.yield`/`resume` vált közöttük, a `resume` argumentuma pedig a `Fiber.yield` visszatérési értéke lesz, így kétirányú kommunikáció is lehetséges. A Ruby 3 Fiber Scheduler interfészével a blokkoló műveletek (`sleep`, socket, `Net::HTTP`) automatikusan átadják a vezérlést egy másik fibernek, így egyetlen szálon több ezer egyidejű kapcsolat kezelhető, változatlan, szinkron kinézetű kóddal. A gyakorlatban ezt az `async` gem adja (a Falcon webszerver is erre épül). Buktató: C-kiterjesztések, amelyek nem támogatják a schedulert, továbbra is blokkolnak.

```ruby
# Alap Fiber: kooperatív váltás
producer = Fiber.new do
  %w[a b c].each { |x| Fiber.yield x }   # felfüggeszt és értéket ad vissza
  :done
end
p producer.resume   # => "a"
p producer.resume   # => "b"

# Kétirányú: a resume argumentuma lesz a Fiber.yield értéke
line_counter = Fiber.new do |first|
  buffer = +first                      # +"" -> nem fagyasztott string
  loop do
    chunk = Fiber.yield(buffer.count("\n"))
    buffer << chunk
  end
end
p line_counter.resume("a\nb")          # => 1
p line_counter.resume("\nc\n")         # => 3

# Fiber Scheduler az async gemmel: a sleep/I/O nem blokkolja a többi taskot
require "async"

Async do |task|
  started = Process.clock_gettime(Process::CLOCK_MONOTONIC)
  jobs = 3.times.map do |i|
    task.async do
      sleep 0.5                        # a scheduler közben a többit futtatja
      "kész #{i}"
    end
  end
  p jobs.map(&:wait)                   # => ["kész 0", "kész 1", "kész 2"]
  elapsed = Process.clock_gettime(Process::CLOCK_MONOTONIC) - started
  puts format("%.2f s", elapsed)       # ~0.5 s, nem 1.5 s
end
```

## Ractorok: valódi párhuzamosság
<!-- q: Hogyan futtassak CPU-igényes kódot párhuzamosan Ractorokkal Rubyban? -->
<!-- tags: ractor, parallelism, gvl, shareable, message passing, actor model -->

A Ractor (Ruby 3.0+, még kísérleti státuszú) az aktor-modellt valósítja meg: minden Ractornak saját GVL-je van, ezért CPU-igényes munkát valóban több magon futtat. Az ár az izoláció: a Ractorok nem osztanak meg módosítható objektumot, csak üzenetekkel kommunikálnak (`send`/`Ractor.receive`), az argumentumok másolódnak vagy mozgatódnak, a blokk nem látja a külső lokális változókat. Megosztani csak "shareable" (mélyen fagyasztott) objektumot lehet, amit `Ractor.make_shareable` állít elő. Buktató: sok gem nem Ractor-biztos; az eredmény lekérése Ruby 3.0–3.4-ben `take`, újabb verziókban `value`.

```ruby
NUMBERS = [2_000_000, 2_000_000, 2_000_000, 2_000_000].freeze # frozen -> shareable

ractors = NUMBERS.each_with_index.map do |n, i|
  # Az argumentumok átmásolódnak; külső lokális változó NEM érhető el a blokkból
  Ractor.new(n, i, name: "calc-#{i}") do |count, idx|
    [idx, (1..count).sum { |k| Math.sqrt(k) * Math.sin(k) }]
  end
end

# Eredmény: Ruby 3.5+/4.0 -> value; Ruby 3.0–3.4 -> take
fetch = ->(r) { r.respond_to?(:value) ? r.value : r.take }
results = ractors.map(&fetch)
results.sort_by(&:first).each { |idx, v| puts format("%d: %.3f", idx, v) }

# Üzenetküldés: send a Ractor bejövő sorába, Ractor.receive olvassa
worker = Ractor.new do
  total = 0
  while (msg = Ractor.receive) != :stop
    total += msg
  end
  total                          # a blokk értéke az eredmény
end
[10, 20, 30].each { |x| worker.send(x) }
worker.send(:stop)
p fetch.(worker)                 # => 60

# Mély fagyasztás: megosztható konfiguráció
CONFIG = Ractor.make_shareable({ precision: 3, mode: "fast" })
p Ractor.shareable?(CONFIG)      # => true
p Ractor.shareable?([1, "a"])    # => false (a string nem fagyasztott)
```

## Rails: ActiveRecord asszociációk
<!-- q: Hogyan definiáljak kapcsolatokat ActiveRecord modellek között Railsben? -->
<!-- tags: rails, activerecord, associations, has_many, belongs_to, polymorphic, validations -->

Az ActiveRecord asszociációk deklaratívan írják le a táblák közötti kapcsolatokat: `belongs_to` (az idegen kulcs ennél a táblánál van), `has_many`/`has_one`, `has_many :through` (köztes modellen át, extra oszlopokkal), valamint polimorf kapcsolat (`commentable_type` + `commentable_id`). A `dependent:` szabályozza a törlés továbbterjedését, a `counter_cache` számláló oszlopot tart karban, a scope-pal ellátott asszociáció pedig szűrt kapcsolatot ad. Buktató: a `dependent: :destroy` minden gyereket egyenként tölt be és callbackeket futtat (lassú), a `:delete_all` egy SQL, de kihagyja a callbackeket.

```ruby
# app/models/author.rb
class Author < ApplicationRecord
  has_many :books, dependent: :destroy                   # szülő törlésekor a gyerekek is
  has_many :reviews, through: :books                     # köztes modellen át
  has_one  :profile, dependent: :destroy
  has_many :published_books, -> { published.order(published_at: :desc) },
           class_name: "Book", inverse_of: :author

  validates :name, presence: true, uniqueness: { case_sensitive: false }
end

# app/models/book.rb
class Book < ApplicationRecord
  belongs_to :author, counter_cache: true                # authors.books_count karbantartása
  has_many :reviews, dependent: :delete_all              # gyors törlés callback nélkül
  has_many :taggings, dependent: :destroy
  has_many :tags, through: :taggings                     # N:M extra oszlopokkal a taggings-ben
  has_many :comments, as: :commentable                   # polimorf kapcsolat

  enum :status, { draft: 0, review: 1, published: 2 }, default: :draft
  scope :recent, -> { where(published_at: 1.month.ago..) }

  validates :title, presence: true, length: { maximum: 200 }
  validates :isbn, uniqueness: true, allow_nil: true
end

# app/models/comment.rb
class Comment < ApplicationRecord
  belongs_to :commentable, polymorphic: true             # Book, Author, ... is lehet
end

# Használat (pl. rails console)
author = Author.create!(name: "Példa Szerző")
book = author.books.create!(title: "Ruby mélyvíz")       # author_id automatikusan beáll
book.published!                                          # enum bang metódus: status = published
book.comments.create!(body: "Remek könyv")
book.reviews.where("rating >= ?", 4).average(:rating)
Author.joins(:books).merge(Book.recent).distinct          # scope újrahasznosítása joinon át
author.books.find_or_create_by!(title: "Második kötet")
```

## Rails: az N+1 probléma és az eager loading
<!-- q: Hogyan kerüljem el az N+1 lekérdezés problémát Railsben includes-szal? -->
<!-- tags: rails, n+1, includes, preload, eager_load, strict_loading, performance -->

N+1 probléma: egy listát egy lekérdezéssel töltünk be, majd ciklusban minden elem kapcsolatához külön lekérdezés fut – 50 könyvnél 51 SQL. Az `includes` előre betölti a kapcsolatot: alapból külön `IN (...)` lekérdezéssel (`preload`), de ha a feltétel a kapcsolt táblára hivatkozik, egyetlen LEFT JOIN-nal (`eager_load`). A `strict_loading` kivételt dob lusta betöltésnél, így a hibát már fejlesztés közben észreveszed. Buktató: betöltött kollekción a `.size` nem futtat SQL-t, a `.count` viszont mindig `COUNT` lekérdezést indít.

```ruby
# N+1: 1 lekérdezés a könyvekre + 50 külön a szerzőkre
Book.limit(50).each { |b| puts b.author.name }              # 51 SQL!

# includes: 2 SQL (books + authors WHERE id IN (...))
Book.includes(:author).limit(50).each { |b| puts b.author.name }

# preload: mindig külön lekérdezés; eager_load: mindig egy JOIN
Book.preload(:author, :tags).limit(50)
Book.eager_load(:author).where(authors: { country: "HU" })  # szűrés a kapcsolt táblán

# Beágyazott eager loading + kötegelt bejárás nagy táblán
Author.includes(books: %i[reviews tags]).find_each(batch_size: 500) do |author|
  total = author.books.sum { |b| b.reviews.size }           # .size: nincs SQL (betöltött)
  puts "#{author.name}: #{total} értékelés"
end

# Ha csak szám vagy létezés kell, ne tölts be objektumokat
Author.where.associated(:books)                             # van legalább egy könyve (Rails 7+)
Author.left_joins(:books)
      .group(:id)
      .select("authors.*, COUNT(books.id) AS books_total")
Book.where(status: :published).pluck(:id, :title)           # csak tömbök, nincs modell-példány

# Szigorú mód: lusta betöltéskor kivétel
class Book < ApplicationRecord
  self.strict_loading_by_default = true
end
begin
  Book.first.author
rescue ActiveRecord::StrictLoadingViolationError => e
  Rails.logger.warn(e.message)
end

# config/environments/development.rb – globális naplózás kivétel helyett:
# config.active_record.action_on_strict_loading_violation = :log
```

## Rails: migrációk
<!-- q: Hogyan írjak biztonságos adatbázis-migrációt Railsben? -->
<!-- tags: rails, migration, schema, index, foreign key, zero downtime, data migration -->

A migráció verziózott, időbélyeggel elnevezett Ruby-osztály, amely a sémát lépésenként változtatja; a `change` metódus automatikusan visszafordítható, a nem visszafordítható műveletekhez `up`/`down` kell. Idegen kulcsot, indexet és check constraintet az adatbázis szintjén is érdemes megadni – a modellvalidáció önmagában nem véd versenyhelyzet ellen. Nagy táblán PostgreSQL-ben `algorithm: :concurrently`-vel építs indexet zárolás nélkül (ehhez tranzakción kívül kell futni). Buktató: adatmigrációban ne használd az alkalmazás modelljeit, mert azok később megváltozhatnak – definiálj lokális, minimális modellt.

```ruby
# db/migrate/20260501120000_create_orders.rb
class CreateOrders < ActiveRecord::Migration[8.0]
  def change # automatikusan visszafordítható (rollback)
    create_table :orders do |t|
      t.references :user, null: false, foreign_key: true, index: true
      t.string  :status, null: false, default: "pending"
      t.integer :total_cents, null: false, default: 0
      t.jsonb   :metadata, null: false, default: {}         # PostgreSQL
      t.timestamps
    end
    add_index :orders, %i[user_id status]
    add_check_constraint :orders, "total_cents >= 0", name: "orders_total_non_negative"
  end
end

# Index építése nagy táblán zárolás nélkül (PostgreSQL)
class AddIndexOnOrdersCreatedAt < ActiveRecord::Migration[8.0]
  disable_ddl_transaction!          # CONCURRENTLY nem futhat tranzakcióban

  def change
    add_index :orders, :created_at, algorithm: :concurrently
  end
end

# Adatmigráció: lokális modell + kötegelt frissítés
class BackfillOrderCurrency < ActiveRecord::Migration[8.0]
  class MigrationOrder < ActiveRecord::Base
    self.table_name = "orders"
  end

  def up
    add_column :orders, :currency, :string, limit: 3
    MigrationOrder.in_batches(of: 1_000) { |batch| batch.update_all(currency: "HUF") }
    change_column_null :orders, :currency, false
  end

  def down
    remove_column :orders, :currency
  end
end

# bin/rails db:migrate | bin/rails db:rollback STEP=1 | bin/rails db:migrate:status
```

## Rails: controllerek és strong parameters
<!-- q: Hogyan írjak REST API controllert Railsben strong parameterekkel? -->
<!-- tags: rails, controller, rest, strong parameters, before_action, rescue_from, api -->

A Rails controller a route-okhoz rendelt action-metódusokból áll; a `before_action` közös előkészítést (hitelesítés, rekord betöltése) futtat, a `rescue_from` egységes hibaválaszt ad. A strong parameters (`params.require(...).permit(...)`, Rails 8-ban `params.expect`) csak az engedélyezett mezőket engedi át a modellbe, ami a mass assignment támadás elleni védelem. A rekordokat mindig a bejelentkezett felhasználó hatókörén keresztül kérd le (`current_user.orders.find`), így más felhasználó adata nem érhető el ID-találgatással (IDOR). Buktató: a lassú munkát (e-mail, PDF) ne a kérésben végezd, hanem háttérjobként.

```ruby
# config/routes.rb: namespace(:api) { namespace(:v1) { resources :orders } }
module Api
  module V1
    class OrdersController < ApplicationController
      before_action :authenticate_user!                  # pl. Devise vagy saját auth
      before_action :set_order, only: %i[show update destroy]
      rescue_from ActiveRecord::RecordNotFound, with: :not_found

      # GET /api/v1/orders?status=paid&page=2
      def index
        page   = params.fetch(:page, 1).to_i.clamp(1, 1_000)
        orders = current_user.orders.includes(:items).order(created_at: :desc)
        orders = orders.where(status: params[:status]) if params[:status].present?
        render json: orders.limit(20).offset((page - 1) * 20)
      end

      def show
        render json: @order, include: :items
      end

      def create
        order = current_user.orders.build(order_params)
        if order.save
          GenerateInvoiceJob.perform_later(order)        # lassú munka a háttérbe
          render json: order, status: :created, location: api_v1_order_url(order)
        else
          render json: { errors: order.errors.full_messages }, status: :unprocessable_entity
        end
      end

      def update
        if @order.update(order_params)
          render json: @order
        else
          render json: { errors: @order.errors.full_messages }, status: :unprocessable_entity
        end
      end

      def destroy
        @order.destroy!
        head :no_content
      end

      private

      # Hatókörös keresés: csak a saját rendelés (IDOR ellen)
      def set_order
        @order = current_user.orders.find(params[:id])
      end

      # Strong parameters: csak engedélyezett mezők
      def order_params
        params.require(:order).permit(:note, :shipping_method, items_attributes: %i[product_id quantity])
      end

      def not_found
        render json: { error: "Nem található" }, status: :not_found
      end
    end
  end
end
```

## Rails: háttérfeladatok ActiveJobbal
<!-- q: Hogyan futtassak háttérfeladatot ActiveJobbal Railsben újrapróbálással? -->
<!-- tags: rails, activejob, background job, solid queue, sidekiq, retry_on, idempotency -->

Az ActiveJob egységes API a háttérfeladatokhoz, a tényleges sort egy adapter adja (Rails 8 alapértelmezése a DB-alapú Solid Queue, népszerű alternatíva a Redis-alapú Sidekiq). A modell-argumentumokat GlobalID-ként szerializálja, így a worker friss rekordot tölt be; a `retry_on` átmeneti hibáknál növekvő várakozással újrapróbál, a `discard_on` értelmetlen újrapróbálásnál eldobja a jobot. A jobnak idempotensnek kell lennie, mert hálózati hiba vagy újraindítás miatt többször is lefuthat. Buktató: ha tranzakcióban indítod, a worker hamarabb futhat, mint a COMMIT – indítsd `after_commit` callbackből.

```ruby
# app/jobs/generate_invoice_job.rb
class GenerateInvoiceJob < ApplicationJob
  queue_as :invoices

  # Átmeneti hibáknál újrapróbálás, egyre hosszabb várakozással
  retry_on Timeout::Error, Errno::ECONNRESET, wait: :polynomially_longer, attempts: 5
  # Ha a rekord közben törlődött, nincs értelme újrapróbálni
  discard_on ActiveJob::DeserializationError

  # Az order GlobalID-ként utazik (gid://app/Order/42), a worker újratölti
  def perform(order, send_email: true)
    return if order.invoice_number.present?            # idempotencia: kétszeri futás se duplikáljon

    order.with_lock do                                 # sorzár párhuzamos futás ellen
      next if order.invoice_number.present?

      order.update!(invoice_number: InvoiceNumber.next_for(order))
    end
    InvoiceMailer.with(order:).ready.deliver_later if send_email
  end
end

# app/models/order.rb – indítás a COMMIT után
class Order < ApplicationRecord
  after_commit :enqueue_invoice, on: :create

  private

  def enqueue_invoice
    GenerateInvoiceJob.perform_later(self)
  end
end

# További indítási módok
# GenerateInvoiceJob.set(wait: 10.minutes, queue: :low).perform_later(order, send_email: false)
# GenerateInvoiceJob.perform_now(order)                # szinkron (konzol, teszt)

# config/application.rb – backend kiválasztása
# config.active_job.queue_adapter = :solid_queue       # vagy :sidekiq
```

## Tesztelés RSpec-kel
<!-- q: Hogyan írjak jól szervezett RSpec teszteket mockokkal? -->
<!-- tags: rspec, testing, tdd, let, subject, instance_double, mocks, context -->

Az RSpec viselkedés-leíró (BDD) tesztkeret: a `describe`/`context` csoportosít, az `it` egy elvárás, a `let` lusta, tesztenként újra kiértékelt segédérték, a `subject` a tesztelt objektum. Az `instance_double` ellenőrzött teszt-dublőr: hibát ad, ha a valódi osztályon nem létezik a stubolt metódus, így a mock nem "rohad el" refaktorálásnál. A `allow ... to receive` stubol, a `have_received` utólag ellenőrzi a hívást (arrange–act–assert sorrend). Buktató: a `let!` és a `before` mindig lefut, ami lassíthatja a tesztcsomagot – csak ott használd, ahol tényleg kell.

```ruby
# spec/services/discount_calculator_spec.rb
require "rails_helper"

RSpec.describe DiscountCalculator do
  subject(:calculator) { described_class.new(coupon_repo:) }

  let(:coupon_repo) { instance_double(CouponRepository) } # ellenőrzi a valódi interfészt

  describe "#tiered" do
    # Táblázatos tesztek: minden sorból külön példa lesz
    {
      9_999 => 0,
      10_000 => 500,
      100_000 => 10_000
    }.each do |total, expected|
      it "#{total} Ft-ra #{expected} Ft kedvezményt ad" do
        expect(calculator.tiered(total)).to eq(expected)
      end
    end

    it "negatív összegre hibát dob" do
      expect { calculator.tiered(-1) }.to raise_error(ArgumentError, /negatív/)
    end
  end

  describe "#with_coupon" do
    context "érvényes kuponnal" do
      before { allow(coupon_repo).to receive(:percent_for).with("NYAR10").and_return(10) }

      it "levonja a százalékot" do
        expect(calculator.with_coupon(10_000, "NYAR10")).to eq(9_000)
      end

      it "pontosan egyszer kérdezi le a kupont" do
        calculator.with_coupon(10_000, "NYAR10")
        expect(coupon_repo).to have_received(:percent_for).once
      end
    end

    context "lejárt kuponnal" do
      before { allow(coupon_repo).to receive(:percent_for).and_raise(CouponRepository::Expired) }

      it "az eredeti árat adja és nem dob" do
        expect(calculator.with_coupon(5_000, "REGI")).to eq(5_000)
      end
    end
  end
end

# Request spec (HTTP szint):
RSpec.describe "Orders API", type: :request do
  it "érvénytelen adatra 422-t ad" do
    post "/api/v1/orders", params: { order: { note: "" } }, as: :json
    expect(response).to have_http_status(:unprocessable_entity)
  end
end
```

## Gemek és Bundler
<!-- q: Hogyan kezeljem a függőségeket Bundlerrel és hogyan készítsek saját gemet? -->
<!-- tags: gems, bundler, gemfile, gemfile.lock, gemspec, dependencies, versioning -->

A gem a Ruby csomagformátuma, a Bundler pedig a projekt függőségeit kezeli: a `Gemfile` írja le a kívánt verziókat, a `Gemfile.lock` rögzíti a ténylegesen feloldott fát – alkalmazásnál ezt mindig commitold, így mindenhol ugyanaz fut. A pesszimista operátor (`~> 8.0` = `>= 8.0, < 9.0`) biztonságos frissítési sávot ad, a csoportok (`:development, :test`) pedig élesben kihagyhatók. A parancsokat `bundle exec`-kel futtasd, hogy a lockolt verziók töltődjenek be. Saját gemnél a `.gemspec` írja le a metaadatokat és függőségeket; könyvtárnál ne commitold a lockfile-t, és a függőségeknél tágabb sávot adj meg.

```ruby
# Gemfile
source "https://rubygems.org"
ruby "~> 3.3"

gem "rails", "~> 8.0"           # pesszimista: >= 8.0, < 9.0
gem "pg", ">= 1.5"
gem "puma"
gem "solid_queue"
gem "bootsnap", require: false  # require: false -> nem töltődik be automatikusan

group :development, :test do
  gem "rspec-rails", "~> 7.0"
  gem "debug", platforms: %i[mri windows], require: false
end

group :test do
  gem "webmock"
end

# Git vagy helyi forrás (fejlesztés közben)
gem "internal_lib", git: "https://github.com/example/internal_lib.git", tag: "v1.2.0"
# gem "local_gem", path: "../local_gem"

# Parancsok:
#   bundle install                       – telepítés a lock alapján
#   bundle update --conservative rails   – csak a rails (és ami muszáj) frissül
#   bundle outdated                      – elavult gemek listája
#   bundle exec rspec                    – a lockolt verziókkal futtat
#   bundle config set --local without development:test   (éles szerveren)
```

```ruby
# my_toolkit.gemspec – saját gem leírója
require_relative "lib/my_toolkit/version"

Gem::Specification.new do |spec|
  spec.name                  = "my_toolkit"
  spec.version               = MyToolkit::VERSION
  spec.summary               = "Kis segédkönyvtár szövegfeldolgozáshoz"
  spec.authors               = ["Example Dev"]
  spec.license               = "MIT"
  spec.files                 = Dir["lib/**/*.rb", "README.md", "LICENSE"]
  spec.required_ruby_version = ">= 3.2"

  spec.add_dependency "zeitwerk", "~> 2.6"            # futásidejű függőség (tág sáv)
  spec.add_development_dependency "rspec", "~> 3.13"
end

# Építés és kiadás: gem build my_toolkit.gemspec && gem push my_toolkit-0.1.0.gem
```
