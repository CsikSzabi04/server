# Go
<!-- tech: go -->
<!-- aliases: golang -->

A Go (golang) a Google által tervezett, statikusan típusos, natív gépi kódra forduló nyelv szemétgyűjtővel (GC) és beépített konkurenciával (goroutine-ok, channelek). Szándékosan kicsi nyelv: nincs öröklődés, kivételek helyett hibaértékek vannak, a generikusok az 1.18 óta érhetők el. Gyors fordítás, egyetlen statikus bináris és erős standard könyvtár (net/http, encoding/json, database/sql) jellemzi, ezért felhőszolgáltatásokhoz, hálózati szerverekhez, CLI-eszközökhöz és DevOps-toolinghoz (Docker, Kubernetes) ideális. Kevésbé jó választás GUI-hoz, kemény valós idejű rendszerekhez (GC-szünetek) vagy ahol nagyon kifejező típusrendszer kell.

## Goroutine-ok és a GMP ütemező
<!-- q: Hogyan működnek a goroutine-ok és a Go ütemező (GMP modell)? -->
<!-- tags: goroutine, scheduler, gmp, gomaxprocs, concurrency, preemption -->

A goroutine egy pehelysúlyú, a Go runtime által kezelt végrehajtási egység (néhány KB-os, dinamikusan növő veremmel), így százezres nagyságrendben is indítható. Az ütemező M:N modellt használ: G (goroutine) fut M-en (OS-szál), de csak akkor, ha az M birtokol egy P-t (logikai processzor, számuk = GOMAXPROCS). Minden P-nek saját futási sora van, az üresjáratú P-k munkát lopnak (work stealing), blokkoló syscallnál a P átkerül másik M-re, 1.14 óta pedig aszinkron preempció is van. Fő buktató a goroutine-szivárgás: az örökre blokkolt goroutine-t a GC nem takarítja el.

```go
package main

import (
	"fmt"
	"runtime"
	"sync"
	"time"
)

// cpuMunka egy CPU-igényes feladatot szimulál.
func cpuMunka(n int) int {
	osszeg := 0
	for i := 0; i < n; i++ {
		osszeg += i % 7
	}
	return osszeg
}

func main() {
	// GOMAXPROCS(0) csak lekérdez: a P-k száma, alapból a CPU-magok száma.
	fmt.Println("P-k száma:", runtime.GOMAXPROCS(0))

	var wg sync.WaitGroup
	eredmenyek := make([]int, 8)

	start := time.Now()
	for i := range 8 { // Go 1.22+: range egész számon, iterációnként ÚJ i változó
		wg.Add(1)
		go func() {
			defer wg.Done()
			// Minden goroutine a saját indexére ír -> nincs adatverseny.
			eredmenyek[i] = cpuMunka(5_000_000)
		}()
	}
	wg.Wait() // Go 1.25+: wg.Go(func(){...}) egyben végzi az Add/Done párost
	fmt.Println("kész:", time.Since(start), "goroutine-ok:", runtime.NumGoroutine())

	// Szivárgás: ez a goroutine örökre blokkol, mert senki nem ír a channelbe.
	ch := make(chan int)
	go func() { <-ch }()
	time.Sleep(10 * time.Millisecond)
	fmt.Println("szivárgó goroutine-ok:", runtime.NumGoroutine()-1)
}
```

## Channelek: pufferelt, puffer nélküli, irányított
<!-- q: Hogyan használjam a channeleket Go-ban, és mi a különbség a pufferelt és a puffer nélküli között? -->
<!-- tags: channel, buffered, unbuffered, close, range, directional channel -->

A channel típusos csővezeték goroutine-ok között: a puffer nélküli channelen a küldő és a fogadó „találkozik” (szinkronizációs pont), a pufferelt channel egy korlátos sor. A channelt mindig a küldő zárja le, a fogadó `range`-dzsel vagy a „comma ok” idiómával érzékeli a lezárást. Az irányított típusok (`chan<-`, `<-chan`) fordítási időben akadályozzák meg a rossz irányú használatot. Buktatók: lezárt channelre küldés és kétszeres close panic-ot okoz, nil channelen minden művelet örökre blokkol.

```go
package main

import "fmt"

// termelo csak küldeni tud (chan<-), és ő zárja le a channelt.
func termelo(n int, ki chan<- int) {
	defer close(ki) // a lezárás jelzi a fogyasztónak: nincs több adat
	for i := 1; i <= n; i++ {
		ki <- i * i
	}
}

// osszegzo csak fogadni tud (<-chan) a bemenetről.
func osszegzo(be <-chan int, eredmeny chan<- int) {
	sum := 0
	for v := range be { // a range a lezárásig olvas
		sum += v
	}
	eredmeny <- sum
}

func main() {
	adat := make(chan int, 4)  // pufferelt: max 4 elem várakozhat blokkolás nélkül
	eredmeny := make(chan int) // puffer nélküli: küldő és fogadó találkozik

	go termelo(10, adat)
	go osszegzo(adat, eredmeny)
	fmt.Println("négyzetösszeg:", <-eredmeny) // 385

	// "comma ok" idióma: lezárt channelből a nulla érték + false jön.
	c := make(chan string, 1)
	c <- "utolsó"
	close(c)
	v, ok := <-c
	fmt.Println(v, ok) // utolsó true — a pufferben maradt elem még kiolvasható
	v, ok = <-c
	fmt.Printf("%q %v\n", v, ok) // "" false

	// Buktatók:
	// - lezárt channelre küldés -> panic
	// - kétszeres close -> panic
	// - nil channelen küldés/fogadás örökre blokkol
}
```

## select minták: timeout, nem blokkoló művelet, nil channel
<!-- q: Hogyan használjam a select utasítást timeouttal és nem blokkoló küldéssel Go-ban? -->
<!-- tags: select, timeout, time.After, default, nil channel, non-blocking -->

A `select` több channel-műveletre vár egyszerre, és azt hajtja végre, amelyik előbb kész (ha több is kész, véletlenszerűen választ). A `default` ág nem blokkoló küldést/fogadást tesz lehetővé, a `time.After` időtúllépést ad, a nil-re állított channel pedig kikapcsolja az adott ágat. Figyelj arra, hogy timeout után a lassú küldő goroutine beragadhat, ha puffer nélküli channelre próbál írni — ilyenkor 1 elemű puffer kell.

```go
package main

import (
	"fmt"
	"time"
)

// osszefesul két forrást olvas, amíg mindkettő le nem zárul.
// A lezárt channelt nil-re állítjuk: a nil channel ága soha nem fut le.
func osszefesul(a, b <-chan int) []int {
	var out []int
	for a != nil || b != nil {
		select {
		case v, ok := <-a:
			if !ok {
				a = nil // ág kikapcsolása
				continue
			}
			out = append(out, v)
		case v, ok := <-b:
			if !ok {
				b = nil
				continue
			}
			out = append(out, v)
		}
	}
	return out
}

func gyart(vals ...int) <-chan int {
	ch := make(chan int)
	go func() {
		defer close(ch)
		for _, v := range vals {
			ch <- v
		}
	}()
	return ch
}

func main() {
	fmt.Println(osszefesul(gyart(1, 3, 5), gyart(2, 4)))

	// Időtúllépés: amelyik előbb kész, az nyer.
	lassu := make(chan string, 1) // 1-es puffer: timeout után sem ragad be a küldő
	go func() {
		time.Sleep(200 * time.Millisecond)
		lassu <- "válasz"
	}()
	select {
	case r := <-lassu:
		fmt.Println(r)
	case <-time.After(50 * time.Millisecond):
		fmt.Println("timeout")
	}

	// Nem blokkoló küldés: ha tele a puffer, eldobjuk az eseményt.
	esemenyek := make(chan string, 1)
	for _, e := range []string{"a", "b", "c"} {
		select {
		case esemenyek <- e:
		default:
			fmt.Println("eldobva:", e)
		}
	}
}
```

## Pipeline, fan-out és fan-in
<!-- q: Hogyan építsek pipeline-t és fan-out/fan-in mintát channelekkel Go-ban? -->
<!-- tags: pipeline, fan-out, fan-in, merge, channels, cancellation -->

A pipeline egymás után kapcsolt lépcsőkből áll, ahol minden lépcső egy bemeneti channelt olvas és egy kimenetit ír. Fan-out: ugyanabból a channelből több worker olvas (párhuzamosítás); fan-in: több channel egyesítése egyetlen kimenetbe. Minden küldésnél figyelni kell a `ctx.Done()`-ra, különben ha a fogyasztó korán kilép, a termelő goroutine-ok örökre beragadnak. A fan-in után az eredmények sorrendje nem garantált.

```go
package main

import (
	"context"
	"fmt"
	"sync"
)

// generator: az első lépcső, számokat bocsát ki, amíg a ctx él.
func generator(ctx context.Context, nums ...int) <-chan int {
	out := make(chan int)
	go func() {
		defer close(out)
		for _, n := range nums {
			select {
			case out <- n:
			case <-ctx.Done(): // leállításkor nem ragadunk be a küldésnél
				return
			}
		}
	}()
	return out
}

// negyzet: feldolgozó lépcső; több példányban futtatva ez a fan-out.
func negyzet(ctx context.Context, in <-chan int) <-chan int {
	out := make(chan int)
	go func() {
		defer close(out)
		for n := range in {
			select {
			case out <- n * n:
			case <-ctx.Done():
				return
			}
		}
	}()
	return out
}

// merge: fan-in — több channelt egyetlen kimenetbe gyűjt.
func merge(ctx context.Context, ins ...<-chan int) <-chan int {
	out := make(chan int)
	var wg sync.WaitGroup
	wg.Add(len(ins))
	for _, c := range ins {
		go func(c <-chan int) {
			defer wg.Done()
			for v := range c {
				select {
				case out <- v:
				case <-ctx.Done():
					return
				}
			}
		}(c)
	}
	// Külön goroutine zárja a kimenetet, ha minden bemenet elfogyott.
	go func() {
		wg.Wait()
		close(out)
	}()
	return out
}

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel() // kilépéskor minden lépcső leáll -> nincs goroutine-szivárgás

	src := generator(ctx, 1, 2, 3, 4, 5, 6, 7, 8)
	// Fan-out: három worker olvas ugyanabból a channelből.
	w1, w2, w3 := negyzet(ctx, src), negyzet(ctx, src), negyzet(ctx, src)

	sum := 0
	for v := range merge(ctx, w1, w2, w3) { // a sorrend NEM garantált
		sum += v
	}
	fmt.Println("összeg:", sum) // 204
}
```

## Worker pool korlátozott párhuzamossággal
<!-- q: Hogyan írjak worker poolt Go-ban, ami korlátozza a párhuzamos feladatok számát? -->
<!-- tags: worker pool, waitgroup, bounded concurrency, jobs, results, errgroup -->

A worker pool fix számú goroutine-t indít, amelyek egy közös `jobs` channelből veszik a feladatokat — így a párhuzamosság korlátos marad (pl. adatbázis-kapcsolatok vagy API rate limit miatt). Az eredményeket és hibákat egy `results` channelen gyűjtjük, a hibát az eredmény részeként adjuk vissza. A lezárási sorrend kritikus: előbb a `jobs` zárása, majd `wg.Wait()`, végül a `results` zárása. Ha az első hibánál mindent le kell állítani, a `golang.org/x/sync/errgroup` `SetLimit`-tel kényelmesebb.

```go
package main

import (
	"errors"
	"fmt"
	"sync"
)

type Feladat struct {
	ID   int
	Fajl string
}

type Eredmeny struct {
	ID    int
	Meret int
	Err   error
}

// feldolgoz valós munkát szimulál (pl. fájl tömörítése).
func feldolgoz(f Feladat) (int, error) {
	if f.Fajl == "" {
		return 0, errors.New("üres fájlnév")
	}
	return len(f.Fajl) * 100, nil
}

// workerPool fix számú goroutine-nal dolgozza fel a feladatokat.
func workerPool(feladatok []Feladat, workers int) []Eredmeny {
	jobs := make(chan Feladat)
	results := make(chan Eredmeny, len(feladatok)) // pufferelt: a workerek itt nem blokkolnak

	var wg sync.WaitGroup
	for range workers {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for f := range jobs { // addig fut, amíg a jobs le nem zárul
				m, err := feldolgoz(f)
				results <- Eredmeny{ID: f.ID, Meret: m, Err: err}
			}
		}()
	}

	for _, f := range feladatok {
		jobs <- f
	}
	close(jobs) // jelzés a workereknek: nincs több munka
	wg.Wait()
	close(results)

	out := make([]Eredmeny, 0, len(feladatok))
	for r := range results {
		out = append(out, r)
	}
	return out
}

func main() {
	fs := []Feladat{{1, "a.log"}, {2, ""}, {3, "nagy.csv"}, {4, "x.json"}}
	for _, r := range workerPool(fs, 2) {
		if r.Err != nil {
			fmt.Printf("#%d hiba: %v\n", r.ID, r.Err)
			continue
		}
		fmt.Printf("#%d kész, %d bájt\n", r.ID, r.Meret)
	}
}
```

## context: megszakítás, időkorlát, kérés-szintű értékek
<!-- q: Hogyan használjam a context csomagot megszakításra és timeoutra Go-ban? -->
<!-- tags: context, cancellation, timeout, deadline, WithCancelCause, AfterFunc -->

A `context.Context` a megszakítási jelet, határidőt és kérés-szintű értékeket viszi végig a hívási láncon; konvenció szerint mindig az első paraméter. A `WithTimeout`/`WithCancel` által visszaadott `cancel`-t mindig meg kell hívni (defer), különben a belső erőforrások csak lejáratkor szabadulnak. A `ctx.Done()` channel lezárul megszakításkor, a `context.Cause` (1.20+) a konkrét okot adja vissza. A `WithValue` csak kérés-szintű metaadatra (trace ID, auth) való, nem opcionális paraméterek átadására.

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"time"
)

var ErrKvotaElfogyott = errors.New("kvóta elfogyott")

// lekerdez lassú műveletet szimulál, ami tiszteletben tartja a ctx-et.
func lekerdez(ctx context.Context, id int) (string, error) {
	select {
	case <-time.After(time.Duration(id) * 40 * time.Millisecond):
		return fmt.Sprintf("rekord-%d", id), nil
	case <-ctx.Done():
		// context.Cause: a megadott ok, vagy ctx.Err() (Canceled / DeadlineExceeded).
		return "", fmt.Errorf("lekérdezés %d: %w", id, context.Cause(ctx))
	}
}

type traceKulcs struct{} // saját, nem exportált kulcstípus -> nincs ütközés más csomagokkal

func main() {
	// 1) Időkorlát: a teljes művelet max. 100 ms.
	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()
	for _, id := range []int{1, 5} {
		r, err := lekerdez(ctx, id)
		fmt.Println(r, err, errors.Is(err, context.DeadlineExceeded))
	}

	// 2) Megszakítás konkrét okkal (Go 1.20+).
	ctx2, cancel2 := context.WithCancelCause(context.Background())
	go func() {
		time.Sleep(20 * time.Millisecond)
		cancel2(ErrKvotaElfogyott)
	}()
	_, err := lekerdez(ctx2, 3)
	fmt.Println(err, errors.Is(err, ErrKvotaElfogyott)) // ... true

	// 3) Kérés-szintű érték (trace ID).
	ctx3 := context.WithValue(context.Background(), traceKulcs{}, "trace-abc123")
	if v, ok := ctx3.Value(traceKulcs{}).(string); ok {
		fmt.Println("trace:", v)
	}

	// 4) AfterFunc (Go 1.21+): visszahívás a ctx lezárásakor (pl. kapcsolat bezárása).
	ctx4, cancel4 := context.WithCancel(context.Background())
	stop := context.AfterFunc(ctx4, func() { fmt.Println("takarítás lefutott") })
	defer stop()
	cancel4()
	time.Sleep(10 * time.Millisecond)
}
```

## sync csomag: Mutex, RWMutex, OnceValue, Pool
<!-- q: Mikor használjak Mutexet, RWMutexet, sync.Once-t és sync.Pool-t Go-ban? -->
<!-- tags: sync, mutex, rwmutex, once, oncevalue, pool, waitgroup -->

Megosztott, módosítható állapotnál a `sync.Mutex` kizárólagos hozzáférést ad; ha sok az olvasó és ritka az író, az `RWMutex` párhuzamos olvasást enged. A `sync.OnceValue` (1.21+) lusta, szálbiztos, egyszeri inicializálást ad, a `sync.Pool` pedig gyakran allokált ideiglenes objektumokat hasznosít újra a GC-terhelés csökkentésére. Buktató: a Mutexet tartalmazó structot soha ne másold érték szerint (a `go vet` copylocks ellenőrzése jelzi), és a Poolba visszatett objektumot előbb ürítsd ki.

```go
package main

import (
	"bytes"
	"fmt"
	"sync"
)

// Cache: sok olvasó, ritka író -> RWMutex.
type Cache struct {
	mu   sync.RWMutex
	data map[string]string
}

func NewCache() *Cache { return &Cache{data: make(map[string]string)} }

func (c *Cache) Get(k string) (string, bool) {
	c.mu.RLock() // több olvasó egyszerre tarthatja
	defer c.mu.RUnlock()
	v, ok := c.data[k]
	return v, ok
}

func (c *Cache) Set(k, v string) {
	c.mu.Lock() // kizárólagos zár
	defer c.mu.Unlock()
	c.data[k] = v
}

// Lusta, szálbiztos inicializálás: a függvény pontosan egyszer fut le.
var konfig = sync.OnceValue(func() map[string]int {
	fmt.Println("konfig betöltése...")
	return map[string]int{"maxConn": 32}
})

// sync.Pool: ideiglenes pufferek újrahasznosítása.
var bufPool = sync.Pool{New: func() any { return new(bytes.Buffer) }}

func formaz(nev string, n int) string {
	buf := bufPool.Get().(*bytes.Buffer)
	defer func() {
		buf.Reset() // visszaadás előtt KÖTELEZŐ kiüríteni
		bufPool.Put(buf)
	}()
	fmt.Fprintf(buf, "%s=%d", nev, n)
	return buf.String()
}

func main() {
	c := NewCache()
	var wg sync.WaitGroup
	for i := range 50 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			c.Set(fmt.Sprint("k", i%5), fmt.Sprint(i))
			c.Get("k0")
		}()
	}
	wg.Wait()

	fmt.Println(konfig()["maxConn"], konfig()["maxConn"]) // a betöltés csak egyszer íródik ki
	fmt.Println(formaz("worker", 4))
}
```

## sync/atomic: zár nélküli számlálók és konfig-csere
<!-- q: Hogyan használjam a sync/atomic csomagot zár nélküli műveletekhez Go-ban? -->
<!-- tags: atomic, atomic.Int64, atomic.Pointer, compare-and-swap, lock-free, hot reload -->

A `sync/atomic` típusos atomikus értékei (`atomic.Int64`, `atomic.Bool`, `atomic.Pointer[T]`, 1.19+) zár nélkül, hardveres utasításokkal módosítanak egyetlen változót. Tipikus felhasználás: kérésszámlálók, leállítási jelzők és a teljes konfiguráció atomikus cseréje (copy-on-write: új objektumot tárolunk, a régit nem módosítjuk). Összetett feltételes frissítéshez CAS-ciklus (compare-and-swap) kell. Buktató: atomikkal csak egy változó konzisztens; több mező közös invariánsához Mutex kell.

```go
package main

import (
	"fmt"
	"sync"
	"sync/atomic"
)

type Config struct {
	RateLimit int
	Verzio    string
}

type Szerver struct {
	keresek atomic.Int64           // zár nélküli számláló
	leall   atomic.Bool            // leállítási jelző
	cfg     atomic.Pointer[Config] // a teljes konfig atomikus cseréje
}

func (s *Szerver) Kezel() bool {
	if s.leall.Load() {
		return false
	}
	s.keresek.Add(1)
	_ = s.cfg.Load().RateLimit // olvasás zár nélkül, mindig konzisztens snapshot
	return true
}

// maxFrissit CAS-ciklussal frissít egy maximumot.
func maxFrissit(max *atomic.Int64, uj int64) {
	for {
		regi := max.Load()
		if uj <= regi || max.CompareAndSwap(regi, uj) {
			return // nem nagyobb, vagy sikerült a csere
		}
		// valaki közben módosította -> újrapróbálkozás
	}
}

func main() {
	s := &Szerver{}
	s.cfg.Store(&Config{RateLimit: 100, Verzio: "v1"})

	var wg sync.WaitGroup
	var maxLatencia atomic.Int64
	for i := range 1000 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			s.Kezel()
			maxFrissit(&maxLatencia, int64(i%97))
		}()
	}
	// Hot-swap futás közben: új objektum, a régit NEM módosítjuk.
	s.cfg.Store(&Config{RateLimit: 200, Verzio: "v2"})
	wg.Wait()
	s.leall.Store(true)

	fmt.Println("kérések:", s.keresek.Load(), "max:", maxLatencia.Load(), "cfg:", s.cfg.Load().Verzio)
}
```

## A Go memóriamodell és a race detector
<!-- q: Mi az a data race Go-ban, és hogyan találom meg a race detectorral? -->
<!-- tags: memory model, data race, happens-before, race detector, -race, synchronization -->

A Go memóriamodell szerint egy goroutine írása csak akkor garantáltan látható egy másikban, ha „happens-before” kapcsolat van köztük (channel-művelet, Mutex, WaitGroup, atomic). Két goroutine szinkronizáció nélküli hozzáférése ugyanahhoz a változóhoz, amelyből legalább az egyik írás, adatverseny (data race), és az eredmény nem definiált. A `-race` kapcsoló (ThreadSanitizer alapú) futásidőben észleli ezeket; kb. 5–10× lassít, ezért tesztekben és CI-ban kötelező, éles buildben nem szokás. Csak a ténylegesen lefutó kódutakat ellenőrzi, tehát jó tesztlefedettség kell hozzá.

```go
package main

import (
	"fmt"
	"sync"
)

// HIBÁS: adatverseny. Az n++ olvasás + írás, nem atomikus.
func versenyes() int {
	n := 0
	var wg sync.WaitGroup
	for range 1000 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			n++ // DATA RACE
		}()
	}
	wg.Wait()
	return n // gyakran < 1000
}

// HIBÁS minta (busy wait sima bool-ra) — nincs happens-before kapcsolat,
// a fordító kiemelheti az olvasást a ciklusból, így örökre pöröghet:
//
//	var kesz bool
//	go func() { adat = 42; kesz = true }()
//	for !kesz {}
//
// HELYES: a channel lezárása happens-before a fogadás befejezése előtt.
func helyes() int {
	var adat int
	kesz := make(chan struct{})
	go func() {
		adat = 42
		close(kesz) // a close "publikálja" az adat írását
	}()
	<-kesz
	return adat // garantáltan 42
}

func javitott() int {
	var mu sync.Mutex
	n := 0
	var wg sync.WaitGroup
	for range 1000 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			mu.Lock()
			n++
			mu.Unlock()
		}()
	}
	wg.Wait()
	return n // mindig 1000
}

func main() {
	fmt.Println(versenyes(), helyes(), javitott())
}

// Futtatás race detectorral:
//   go run -race .
//   go test -race ./...
// Kimenet részlet:
//   WARNING: DATA RACE
//   Read at 0x00c000012345 by goroutine 8: main.versenyes.func1() main.go:16
```

## Interfészek és beágyazás (embedding)
<!-- q: Hogyan működnek az interfészek és a struct-beágyazás Go-ban? -->
<!-- tags: interface, embedding, composition, implicit implementation, nil interface, decorator -->

Go-ban az interfész-megfelelés implicit: egy típus akkor teljesít egy interfészt, ha megvannak a metódusai, nincs `implements` kulcsszó — ezért érdemes kicsi interfészeket (io.Reader-stílus) a felhasználó oldalon definiálni. A struct-beágyazás kompozíció: a beágyazott mező metódusai „feljönnek” a külső típusra (promotion), így öröklődés nélkül írható dekorátor. A `var _ I = (*T)(nil)` sor fordítási időben ellenőrzi a megfelelést. Klasszikus buktató: egy nil `*T` pointer interfészbe csomagolva NEM nil interfész, mert van dinamikus típusa.

```go
package main

import (
	"errors"
	"fmt"
	"io"
)

// Kicsi interfészek, kompozícióval (interfész-beágyazás).
type Tarolo interface {
	Get(kulcs string) (string, error)
	Set(kulcs, ertek string) error
}

type TaroloLezarhato interface {
	Tarolo
	io.Closer // a standard könyvtár interfésze is beágyazható
}

// memTarolo implicit módon teljesíti az interfészt.
type memTarolo struct{ m map[string]string }

func (t *memTarolo) Get(k string) (string, error) {
	v, ok := t.m[k]
	if !ok {
		return "", errors.New("nincs ilyen kulcs: " + k)
	}
	return v, nil
}

func (t *memTarolo) Set(k, v string) error {
	t.m[k] = v
	return nil
}

func (t *memTarolo) Close() error { return nil }

// Fordítási idejű ellenőrzés: ha a típus nem teljesíti, nem fordul le.
var _ TaroloLezarhato = (*memTarolo)(nil)

// Struct-beágyazás: a beágyazott metódusai feljönnek; csak a Get-et írjuk felül.
type metrikasTarolo struct {
	TaroloLezarhato
	talalat, hiany int
}

func (m *metrikasTarolo) Get(k string) (string, error) {
	v, err := m.TaroloLezarhato.Get(k) // explicit hívás a beágyazottra
	if err != nil {
		m.hiany++
	} else {
		m.talalat++
	}
	return v, err
}

// Buktató: nil *T interfészben NEM nil interfész.
type sajatHiba struct{}

func (*sajatHiba) Error() string { return "hiba" }

func rosszHiba() error {
	var e *sajatHiba // nil pointer
	return e         // a visszaadott error != nil, mert van dinamikus típusa!
}

func main() {
	mt := &metrikasTarolo{TaroloLezarhato: &memTarolo{m: map[string]string{}}}
	var t TaroloLezarhato = mt
	defer t.Close()

	_ = t.Set("nyelv", "go") // a Set a beágyazott memTarolo-tól jön
	t.Get("nyelv")
	t.Get("hianyzik")
	fmt.Println(mt.talalat, mt.hiany, rosszHiba() != nil) // 1 1 true
}
```

## Generikusok: típusparaméterek és megkötések
<!-- q: Hogyan használjam a generikusokat (type parameters, constraints) Go-ban? -->
<!-- tags: generics, type parameters, constraints, comparable, cmp.Ordered, tilde -->

Az 1.18 óta a függvényeknek és típusoknak lehetnek típusparamétereik, amelyeket interfész-alapú megkötések (constraints) korlátoznak: `any`, `comparable`, `cmp.Ordered` vagy saját unió (`~int | ~float64`). A `~` azt jelenti, hogy az alaptípus számít, így a `type Forint int` is megfelel `~int`-nek. A típusargumentumok általában kikövetkeztethetők a hívásból. Korlát: metódusnak nem lehet saját típusparamétere, ilyenkor szabad függvényt kell írni; ahol egy egyszerű interfész elég, ne használj generikust.

```go
package main

import (
	"cmp"
	"fmt"
	"slices"
)

// Saját megkötés: a ~ miatt a származtatott típusok (type Forint int) is jók.
type Szam interface {
	~int | ~int64 | ~float64
}

func Osszeg[T Szam](xs []T) T {
	var s T
	for _, x := range xs {
		s += x
	}
	return s
}

// Map két típusparaméterrel; a hívásnál kikövetkeztetődnek.
func Map[T, U any](xs []T, f func(T) U) []U {
	out := make([]U, 0, len(xs))
	for _, x := range xs {
		out = append(out, f(x))
	}
	return out
}

// cmp.Ordered: minden rendezhető beépített típus (<, > használható).
func MaxKulcs[K cmp.Ordered, V any](m map[K]V) (K, bool) {
	var best K
	first := true
	for k := range m {
		if first || k > best {
			best, first = k, false
		}
	}
	return best, !first
}

// Generikus típus: halmaz comparable elemekkel (map-kulcs lehet).
type Set[T comparable] struct{ m map[T]struct{} }

func NewSet[T comparable](xs ...T) *Set[T] {
	s := &Set[T]{m: make(map[T]struct{})}
	for _, x := range xs {
		s.m[x] = struct{}{}
	}
	return s
}

func (s *Set[T]) Has(x T) bool {
	_, ok := s.m[x]
	return ok
}

type Forint int

func main() {
	fmt.Println(Osszeg([]Forint{1200, 800})) // 2000 — a ~int miatt működik
	hosszak := Map([]string{"go", "rust", "zig"}, func(s string) int { return len(s) })
	fmt.Println(hosszak, slices.Max(hosszak))
	k, _ := MaxKulcs(map[string]int{"alma": 1, "körte": 2})
	fmt.Println(k, NewSet(1, 2, 3).Has(2))
}
```

## Hibakezelés: wrapping, errors.Is és errors.As
<!-- q: Hogyan csomagoljam és vizsgáljam a hibákat Go-ban (errors.Is, errors.As, %w)? -->
<!-- tags: error handling, wrapping, errors.Is, errors.As, sentinel error, errors.Join -->

Go-ban a hiba érték: a függvény utolsó visszatérési értéke, amit a hívó azonnal ellenőriz. A `fmt.Errorf("...: %w", err)` becsomagolja a hibát, így rétegenként kontextus adható hozzá, miközben az eredeti megmarad a láncban. Az `errors.Is` sentinel értékre (pl. `fs.ErrNotExist`), az `errors.As` konkrét hibatípusra keres a teljes láncban; az `errors.Join` (1.20+) több hibát fűz össze. Buktató: `==` összehasonlítás becsomagolt hibánál hamisat ad, ezért mindig `errors.Is` kell; a `panic` csak helyrehozhatatlan programozói hibára való.

```go
package main

import (
	"errors"
	"fmt"
	"io/fs"
	"os"
)

// Sentinel hiba: összehasonlítható érték (errors.Is-szel).
var ErrNemTalalhato = errors.New("nem található")

// Saját hibatípus extra mezőkkel (errors.As-szel nyerhető ki).
type ValidaciosHiba struct {
	Mezo, Ok string
}

func (e *ValidaciosHiba) Error() string { return e.Mezo + ": " + e.Ok }

func felhasznaloKeres(id int) error {
	if id <= 0 {
		return &ValidaciosHiba{Mezo: "id", Ok: "pozitív kell legyen"}
	}
	if id > 100 {
		// %w becsomagolja: a lánc megmarad, a kontextus hozzáadódik.
		return fmt.Errorf("felhasználó %d: %w", id, ErrNemTalalhato)
	}
	return nil
}

func szolgaltatas(id int) error {
	if err := felhasznaloKeres(id); err != nil {
		return fmt.Errorf("profil betöltése: %w", err) // rétegenként +kontextus
	}
	return nil
}

func main() {
	for _, id := range []int{-1, 500, 7} {
		err := szolgaltatas(id)
		var vh *ValidaciosHiba
		switch {
		case err == nil:
			fmt.Println(id, "OK")
		case errors.Is(err, ErrNemTalalhato): // a teljes láncot bejárja (Unwrap)
			fmt.Println("404:", err)
		case errors.As(err, &vh): // típus szerinti keresés a láncban
			fmt.Println("400, mező:", vh.Mezo, "->", err)
		}
	}

	// A standard könyvtár hibái is így vizsgálhatók.
	_, err := os.Open("/nem/letezo/fajl")
	fmt.Println(errors.Is(err, fs.ErrNotExist)) // true

	// Több hiba összefűzése (pl. több Close egyszerre).
	osszes := errors.Join(errors.New("cache close"), ErrNemTalalhato)
	fmt.Println(errors.Is(osszes, ErrNemTalalhato)) // true
}
```

## net/http szerver middleware-rel és graceful shutdownnal
<!-- q: Hogyan írjak HTTP szervert middleware-rel és graceful shutdownnal Go-ban? -->
<!-- tags: net/http, servemux, middleware, routing, graceful shutdown, timeouts, slog -->

A `net/http` éles használatra kész szervert ad; az 1.22 óta a `ServeMux` metódust és útvonal-wildcardot is ismer (`"GET /termekek/{id}"`, `r.PathValue("id")`), így sok esetben nem kell külső router. A middleware egyszerűen `func(http.Handler) http.Handler`, egymásba ágyazva láncolható (naplózás, panic-védelem, auth). Éles szervernél mindig állíts be timeoutokat (`ReadHeaderTimeout` a Slowloris ellen), mert az alapértelmezett `http.ListenAndServe` ezek nélkül fut. A graceful shutdown (`srv.Shutdown`) megvárja a futó kéréseket.

```go
package main

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"time"
)

// Middleware: func(http.Handler) http.Handler — láncolható.
func naplozo(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		next.ServeHTTP(w, r)
		slog.Info("kérés", "method", r.Method, "path", r.URL.Path, "dur", time.Since(start))
	})
}

func panicVedo(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if rec := recover(); rec != nil {
				slog.Error("panic", "err", rec)
				http.Error(w, "belső hiba", http.StatusInternalServerError)
			}
		}()
		next.ServeHTTP(w, r)
	})
}

func termekHandler(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id") // Go 1.22+: útvonal-wildcard
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"id": id, "nev": "Billentyűzet"})
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /termekek/{id}", termekHandler) // metódus + minta
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	})

	srv := &http.Server{
		Addr:              ":8080",
		Handler:           panicVedo(naplozo(mux)), // kívülről befelé fut
		ReadHeaderTimeout: 5 * time.Second,         // Slowloris elleni védelem
		WriteTimeout:      10 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	// Graceful shutdown: Ctrl+C esetén a futó kérések befejeződhetnek.
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()
	go func() {
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			slog.Error("szerver hiba", "err", err)
			os.Exit(1)
		}
	}()
	<-ctx.Done()
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	_ = srv.Shutdown(shutdownCtx)
}
```

## encoding/json: struct tagek, saját (un)marshal, streamelés
<!-- q: Hogyan kezeljem a JSON-t Go-ban struct tagekkel és saját MarshalJSON-nal? -->
<!-- tags: encoding/json, struct tags, omitempty, MarshalJSON, UnmarshalJSON, RawMessage, Decoder -->

Az `encoding/json` reflexióval képezi le a structokat: csak az exportált (nagybetűs) mezők szerializálódnak, a tagek (`json:"nev,omitempty"`) szabályozzák a kulcsnevet és az üres értékek kihagyását. Saját formátumhoz a típus megvalósíthatja a `MarshalJSON`/`UnmarshalJSON` metódusokat (pl. enum szövegként), a `json.RawMessage` pedig későbbre halasztja egy rész dekódolását. HTTP-kérés törzsénél a streamelő `json.NewDecoder` és a `DisallowUnknownFields` ajánlott. Buktató: `interface{}`-be dekódolva minden szám `float64` lesz, ami nagy azonosítóknál pontatlan.

```go
package main

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"
)

type Rendeles struct {
	ID         int64           `json:"id"`
	Vevo       string          `json:"vevo"`
	Tetelek    []Tetel         `json:"tetelek"`
	Megjegyzes string          `json:"megjegyzes,omitempty"` // üres string esetén kimarad
	Letrehozva time.Time       `json:"letrehozva"`           // RFC 3339 formátum
	Statusz    Statusz         `json:"statusz"`
	Extra      json.RawMessage `json:"extra,omitempty"` // nyers JSON, később dekódolható
}

type Tetel struct {
	SKU   string  `json:"sku"`
	Darab int     `json:"darab"`
	Ar    float64 `json:"ar,string"` // stringként utazik: "1990.5"
}

// Saját (un)marshal: az enum szövegként jelenik meg a JSON-ben.
type Statusz int

const (
	Fuggo Statusz = iota
	Kiszallitva
)

var statuszNevek = []string{"fuggo", "kiszallitva"}

func (s Statusz) MarshalJSON() ([]byte, error) { return json.Marshal(statuszNevek[s]) }

func (s *Statusz) UnmarshalJSON(b []byte) error {
	var str string
	if err := json.Unmarshal(b, &str); err != nil {
		return err
	}
	for i, n := range statuszNevek {
		if n == str {
			*s = Statusz(i)
			return nil
		}
	}
	return fmt.Errorf("ismeretlen státusz: %q", str)
}

func main() {
	be := `{"id":42,"vevo":"Teszt Kft.","tetelek":[{"sku":"KB-1","darab":2,"ar":"1990.5"}],
	"letrehozva":"2026-01-15T10:00:00Z","statusz":"kiszallitva","extra":{"kupon":"X"}}`

	dec := json.NewDecoder(strings.NewReader(be)) // streamelő dekóder (pl. r.Body-hoz)
	dec.DisallowUnknownFields()                   // elgépelt mezőnév -> hiba
	var r Rendeles
	if err := dec.Decode(&r); err != nil {
		fmt.Println("dekódolási hiba:", err)
		return
	}
	fmt.Println(r.Statusz == Kiszallitva, r.Tetelek[0].Ar, string(r.Extra))

	ki, _ := json.MarshalIndent(r, "", "  ")
	fmt.Println(string(ki))
}
```

## database/sql: kapcsolatkészlet, lekérdezések, tranzakciók
<!-- q: Hogyan használjam a database/sql csomagot helyesen Go-ban (pool, lekérdezés, tranzakció)? -->
<!-- tags: database/sql, connection pool, QueryContext, transaction, sql.ErrNoRows, rows.Close -->

Az `*sql.DB` nem egyetlen kapcsolat, hanem szálbiztos kapcsolatkészlet: egyszer kell létrehozni és megosztani, a méretét a `SetMaxOpenConns` és társai hangolják. Mindig paraméterezett lekérdezést használj (Postgres: `$1`, MySQL/SQLite: `?`), és `Context` változatokat, hogy a kérés megszakítása az SQL-t is leállítsa. A `rows.Close()` nélkül a kapcsolat nem kerül vissza a poolba, és a `rows.Err()`-t az iteráció után is ellenőrizni kell. Tranzakciónál a `defer tx.Rollback()` biztonságos, mert sikeres `Commit` után no-op.

```go
package tarolo

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib" // driver regisztráció "pgx" néven
)

type Felhasznalo struct {
	ID    int64
	Email string
	Nev   sql.NullString // NULL-képes oszlop
}

var (
	ErrNincs        = errors.New("felhasználó nem található")
	ErrNincsFedezet = errors.New("nincs elég fedezet")
)

func Megnyit(dsn string) (*sql.DB, error) {
	db, err := sql.Open("pgx", dsn) // még nem kapcsolódik!
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(20)
	db.SetMaxIdleConns(10)
	db.SetConnMaxLifetime(30 * time.Minute)
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	return db, db.PingContext(ctx) // itt derül ki, elérhető-e
}

func Keres(ctx context.Context, db *sql.DB, id int64) (*Felhasznalo, error) {
	var f Felhasznalo
	err := db.QueryRowContext(ctx, `SELECT id, email, nev FROM felhasznalok WHERE id = $1`, id).
		Scan(&f.ID, &f.Email, &f.Nev)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, ErrNincs
	}
	return &f, err
}

func Lista(ctx context.Context, db *sql.DB, limit int) ([]Felhasznalo, error) {
	rows, err := db.QueryContext(ctx, `SELECT id, email, nev FROM felhasznalok ORDER BY id LIMIT $1`, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close() // e nélkül a kapcsolat nem kerül vissza a poolba!
	var out []Felhasznalo
	for rows.Next() {
		var f Felhasznalo
		if err := rows.Scan(&f.ID, &f.Email, &f.Nev); err != nil {
			return nil, err
		}
		out = append(out, f)
	}
	return out, rows.Err() // az iteráció közbeni hiba
}

// Atutal tranzakcióban: vagy minden lefut, vagy semmi.
func Atutal(ctx context.Context, db *sql.DB, honnan, hova int64, osszeg int) error {
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer tx.Rollback() // Commit után no-op; korai return esetén visszagörget

	res, err := tx.ExecContext(ctx,
		`UPDATE szamlak SET egyenleg = egyenleg - $1 WHERE id = $2 AND egyenleg >= $1`, osszeg, honnan)
	if err != nil {
		return fmt.Errorf("terhelés: %w", err)
	}
	if n, _ := res.RowsAffected(); n != 1 {
		return ErrNincsFedezet
	}
	if _, err := tx.ExecContext(ctx,
		`UPDATE szamlak SET egyenleg = egyenleg + $1 WHERE id = $2`, osszeg, hova); err != nil {
		return fmt.Errorf("jóváírás: %w", err)
	}
	return tx.Commit()
}
```

## Tesztelés: táblázatos tesztek, benchmark, fuzzing
<!-- q: Hogyan írjak táblázatvezérelt teszteket, benchmarkot és fuzz tesztet Go-ban? -->
<!-- tags: testing, table-driven tests, t.Run, benchmark, b.Loop, fuzzing, go test -->

A Go beépített `testing` csomaggal és `go test` paranccsal tesztel; a `_test.go` fájlok csak teszteléskor fordulnak le. Az idiomatikus forma a táblázatvezérelt teszt: esetek slice-a, mindegyik `t.Run` alesetként, akár `t.Parallel()`-lel. A `BenchmarkXxx` függvények teljesítményt mérnek (`-bench=. -benchmem`; Go 1.24+: `b.Loop()`), a `FuzzXxx` függvények pedig véletlen bemenetekkel keresnek invariáns-sértést. A fuzzer által talált hibás bemenet a `testdata/fuzz` mappába kerül, és onnan regressziós tesztként fut tovább.

```go
package szoveg

import (
	"strings"
	"testing"
	"unicode/utf8"
)

// A tesztelt függvény (rendesen a szoveg.go-ban lenne).
func Megfordit(s string) string {
	r := []rune(s) // rune-onként, hogy az ékezetes betűk ne törjenek el
	for i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {
		r[i], r[j] = r[j], r[i]
	}
	return string(r)
}

// Táblázatvezérelt teszt: új eset = új sor.
func TestMegfordit(t *testing.T) {
	esetek := []struct {
		nev, be, vart string
	}{
		{"ures", "", ""},
		{"ascii", "golang", "gnalog"},
		{"ekezet", "árvíz", "zívrá"},
	}
	for _, tc := range esetek {
		t.Run(tc.nev, func(t *testing.T) {
			t.Parallel() // az alesetek párhuzamosan futnak
			if got := Megfordit(tc.be); got != tc.vart {
				t.Errorf("Megfordit(%q) = %q, várt %q", tc.be, got, tc.vart)
			}
		})
	}
}

// Benchmark: go test -bench=. -benchmem
func BenchmarkMegfordit(b *testing.B) {
	s := strings.Repeat("árvíztűrő", 100)
	for b.Loop() { // Go 1.24+: időmérés és optimalizáció-védelem automatikus
		Megfordit(s)
	}
}

// Fuzz teszt: go test -fuzz=FuzzMegfordit -fuzztime=30s
func FuzzMegfordit(f *testing.F) {
	f.Add("golang") // seed korpusz
	f.Add("ő ű á")
	f.Fuzz(func(t *testing.T, s string) {
		if !utf8.ValidString(s) {
			t.Skip() // érvénytelen UTF-8-ra a rune-konverzió nem visszafordítható
		}
		if ketszer := Megfordit(Megfordit(s)); ketszer != s {
			t.Fatalf("kétszeres fordítás eltér: %q -> %q", s, ketszer)
		}
		if utf8.RuneCountInString(s) != utf8.RuneCountInString(Megfordit(s)) {
			t.Fatal("rune-szám változott")
		}
	})
}
```

## Profilozás pprof-fal
<!-- q: Hogyan profilozzam a Go programom CPU- és memóriahasználatát pprof-fal? -->
<!-- tags: pprof, profiling, cpu profile, heap profile, flame graph, pgo, performance -->

A Go beépített profilozója mintavételezéssel méri a CPU-időt, a heap-allokációkat, a goroutine-okat, valamint a mutex- és blokkolási versengést. Futó szerverhez a `net/http/pprof` import regisztrálja a `/debug/pprof/` végpontokat (csak belső címen tedd elérhetővé!), egyszeri futáshoz a `runtime/pprof` fájlba ír. Az elemzés a `go tool pprof -http=:8081 cpu.prof` paranccsal flame graph-ként is megnézhető. A profil `default.pgo` néven a main csomag mellé téve PGO-t (profile-guided optimization) kapcsol be, ami jellemzően néhány százalék gyorsulást ad.

```go
package main

import (
	"flag"
	"log"
	"net/http"
	_ "net/http/pprof" // /debug/pprof/ végpontok a DefaultServeMux-on
	"os"
	"runtime"
	"runtime/pprof"
	"strings"
)

func dragaMunka() string {
	var sb strings.Builder
	for i := 0; i < 200_000; i++ {
		sb.WriteString("x")
	}
	return sb.String()
}

func main() {
	cpuFajl := flag.String("cpuprofile", "", "CPU profil kimeneti fájl")
	memFajl := flag.String("memprofile", "", "heap profil kimeneti fájl")
	flag.Parse()

	// 1) Élő profilozás: CSAK localhoston!
	go func() { log.Println(http.ListenAndServe("localhost:6060", nil)) }()
	runtime.SetMutexProfileFraction(5) // mutex-versengés mintavételezése
	runtime.SetBlockProfileRate(1000)  // blokkolási események (ns küszöb)

	// 2) Egyszeri futás profilozása fájlba.
	if *cpuFajl != "" {
		f, err := os.Create(*cpuFajl)
		if err != nil {
			log.Fatal(err)
		}
		defer f.Close()
		if err := pprof.StartCPUProfile(f); err != nil {
			log.Fatal(err)
		}
		defer pprof.StopCPUProfile() // a defer-ek fordított sorrendben: előbb Stop, aztán Close
	}

	for range 50 {
		_ = dragaMunka()
	}

	if *memFajl != "" {
		f, err := os.Create(*memFajl)
		if err != nil {
			log.Fatal(err)
		}
		defer f.Close()
		runtime.GC() // friss heap-statisztika
		if err := pprof.WriteHeapProfile(f); err != nil {
			log.Fatal(err)
		}
	}
}

// Elemzés:
//   go tool pprof -http=:8081 cpu.prof                    # flame graph böngészőben
//   go tool pprof http://localhost:6060/debug/pprof/heap   # élő heap
//   curl "localhost:6060/debug/pprof/goroutine?debug=2"    # goroutine-dump (szivárgás)
//   go test -bench=. -cpuprofile=cpu.prof -memprofile=mem.prof
```

## Modulok és függőségkezelés
<!-- q: Hogyan működnek a Go modulok (go.mod, go.sum, verziózás, workspace)? -->
<!-- tags: go modules, go.mod, go.sum, semantic import versioning, go work, internal, GOPRIVATE -->

A Go modul egy verziózott csomaggyűjtemény, amelyet a gyökérben lévő `go.mod` ír le (modul-útvonal, Go-verzió, függőségek); a `go.sum` a letöltött függőségek kriptográfiai hash-eit rögzíti. A verzióválasztás minimális verziójú (MVS), és v2-től a főverzió az import útvonal része (`example.com/lib/v2`). Az `internal/` könyvtár csomagjai csak a modulon belülről importálhatók, a `go work` workspace pedig több helyi modul együttes fejlesztését teszi lehetővé `replace` nélkül. Privát repókhoz a `GOPRIVATE` kapcsolja ki a nyilvános proxyt és checksum-adatbázist.

```go
// Fájl: cmd/szamlazo/main.go — a modul gyökerében: go.mod (module example.com/szamlazo)
package main

import (
	"fmt"
	"log/slog"

	matek "example.com/matek/v2"              // v2+ főverzió: a /v2 az import útvonal része!
	"example.com/szamlazo/internal/ado"       // internal/: csak ezen a modulon belülről
	"github.com/google/uuid"                  // külső függőség; verzió a go.mod-ban, hash a go.sum-ban
)

func main() {
	id := uuid.NewString()
	brutto := ado.Brutto(10000, 27) // 27% ÁFA
	slog.Info("számla", "id", id, "brutto", brutto, "kerekitett", matek.Kerekit(brutto, 0))
	fmt.Println("kész")
}
```

```text
// go.mod
module example.com/szamlazo

go 1.24                       // minimális nyelvi verzió
toolchain go1.25.3            // ajánlott toolchain (szükség esetén automatikusan letöltődik)

require (
	example.com/matek/v2 v2.3.1
	github.com/google/uuid v1.6.0
)

replace example.com/matek/v2 => ../matek   // helyi fejlesztés alatt álló függőség

tool golang.org/x/tools/cmd/stringer       // Go 1.24+: verziókövetett eszköz (go tool stringer)
```

```bash
go mod init example.com/szamlazo         # új modul
go get github.com/google/uuid@v1.6.0     # függőség hozzáadása/frissítése
go mod tidy                              # hiányzók hozzáadása, feleslegesek törlése
go list -m -u all                        # elérhető frissítések
go work init ./szamlazo ./matek          # workspace több helyi modulhoz
GOPRIVATE=git.example.com/* go get git.example.com/belso/lib
govulncheck ./...                        # ismert sérülékenységek a használt kódutakon
```
