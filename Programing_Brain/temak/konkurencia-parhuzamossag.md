# Konkurencia és párhuzamosság
<!-- tech: concurrency -->
<!-- aliases: konkurencia, párhuzamosság, concurrency, parallelism, multithreading, szálkezelés, async -->

A konkurencia több feladat egymást átfedő kezelése (nem feltétlenül egy időben), a
párhuzamosság több feladat tényleges egyidejű futtatása több magon. Ez a fájl a szálak,
folyamatok és aszinkron modellek különbségeit, a szinkronizációs primitíveket (mutex, szemafor,
condition variable, atomikus műveletek), a tipikus hibákat (versenyhelyzet, holtpont, livelock,
kiéheztetés), a memóriamodelleket, valamint a magasabb szintű modelleket (actor, CSP, szálkészlet,
fork-join, map-reduce, eseményhurok, SIMD/GPU) mutatja be.

## Szálak, folyamatok és async: mikor melyiket?
<!-- q: Mi a különbség a szálak, a folyamatok és az aszinkron programozás között, és mikor melyiket használjam? -->
<!-- tags: threads, processes, async, gil, cpu-bound, io-bound, multiprocessing -->

A folyamat saját címtérrel fut, elszigetelt (egy összeomlás nem rántja magával a többit), de
létrehozása drágább és a kommunikáció IPC-t igényel. A szálak egy folyamaton belül osztoznak a
memórián: olcsóbbak, de minden közös adat szinkronizációt kíván. Az async (kooperatív
multitasking) egyetlen szálon sok I/O-várakozást kezel nagyon olcsón, de csak nem blokkoló
hívásokkal működik. Ökölszabály: CPU-kötött munkára folyamatok (vagy GIL nélküli nyelvben
szálak), I/O-kötött munkára async vagy szálak. CPythonban a GIL miatt a szálak nem gyorsítják a
tiszta Python-számítást (a 3.13+ free-threaded build ezt opcionálisan feloldja).

```python
import asyncio
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

def cpu_heavy(n: int) -> int:
    """CPU-kötött: a GIL miatt szálakkal nem gyorsul, folyamatokkal igen."""
    return sum(i * i for i in range(n))

def io_blocking(_: int) -> None:
    """Blokkoló I/O (itt sleep): várakozás közben a GIL elenged, szálakkal jól skálázódik."""
    time.sleep(0.1)

async def io_async(i: int) -> int:
    """Async: egy szál, sok egyidejű várakozás — csak nem blokkoló hívásokkal."""
    await asyncio.sleep(0.1)  # közben más korutin fut
    return i

def timed(label: str, fn) -> None:
    t0 = time.perf_counter()
    fn()
    print(f"{label:<24} {time.perf_counter() - t0:.2f} s")

async def many_async() -> None:
    await asyncio.gather(*(io_async(i) for i in range(1000)))

if __name__ == "__main__":  # Windows/macOS 'spawn' indítás miatt kötelező a folyamatokhoz
    jobs = [3_000_000] * 4
    timed("CPU, soros", lambda: [cpu_heavy(n) for n in jobs])
    with ThreadPoolExecutor(4) as tp:
        timed("CPU, 4 szál (GIL!)", lambda: list(tp.map(cpu_heavy, jobs)))
        timed("I/O, 4 szál, 20 hívás", lambda: list(tp.map(io_blocking, range(20))))  # ~0.5 s
    with ProcessPoolExecutor(4) as pp:
        timed("CPU, 4 folyamat", lambda: list(pp.map(cpu_heavy, jobs)))
    timed("1000 async várakozás", lambda: asyncio.run(many_async()))  # ~0.1 s, nem 100 s
```

## Versenyhelyzet (race condition) és adatverseny
<!-- q: Mi az a race condition, és hogyan előzzem meg? -->
<!-- tags: race condition, data race, mutex, atomic, check-then-act, go race detector -->

Versenyhelyzetről akkor beszélünk, ha az eredmény a szálak ütemezésének sorrendjétől függ. A
klasszikus eset a `counter++`, ami valójában olvasás–módosítás–írás: két szál lépései
összefésülődhetnek, és frissítések vesznek el. Ugyanilyen a „check-then-act” (ha van készlet,
akkor foglalj), ahol a feltétel és a cselekvés között más is közbeléphet — ezért a teljes
műveletnek egy zár alatt kell lennie. Az adatverseny (két nem szinkronizált hozzáférés, ebből
legalább egy írás) C/C++/Go-ban definiálatlan viselkedés; Go-ban a `-race`, C/C++-ban a
ThreadSanitizer találja meg.

```go
package main

import (
	"fmt"
	"sync"
	"sync/atomic"
)

// HIBÁS: a counter++ három lépés, a goroutine-ok frissítései elveszhetnek
func racy(n int) int {
	counter := 0
	var wg sync.WaitGroup
	for i := 0; i < n; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			counter++ // ADATVERSENY: `go run -race` jelzi
		}()
	}
	wg.Wait()
	return counter
}

func withMutex(n int) int {
	var mu sync.Mutex
	var wg sync.WaitGroup
	counter := 0
	for i := 0; i < n; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			mu.Lock()
			counter++ // kritikus szakasz: egyszerre egy goroutine
			mu.Unlock()
		}()
	}
	wg.Wait()
	return counter
}

func withAtomic(n int) int64 {
	var counter atomic.Int64 // Go 1.19+: típusos atomikus érték
	var wg sync.WaitGroup
	for i := 0; i < n; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			counter.Add(1) // oszthatatlan CPU-utasítás (pl. LOCK XADD)
		}()
	}
	wg.Wait()
	return counter.Load()
}

// Check-then-act: az ellenőrzés és a módosítás EGY zár alatt
type Inventory struct {
	mu    sync.Mutex
	stock int
}

func (inv *Inventory) Reserve(q int) bool {
	inv.mu.Lock()
	defer inv.mu.Unlock()
	if inv.stock < q {
		return false
	}
	inv.stock -= q
	return true
}

func main() {
	fmt.Println(racy(10000), withMutex(10000), withAtomic(10000)) // pl. 9731 10000 10000
	inv := &Inventory{stock: 1}
	fmt.Println(inv.Reserve(1), inv.Reserve(1)) // true false
}
```

## Mutex és olvasó-író zár
<!-- q: Hogyan használjam a mutexet és az RwLockot helyesen? -->
<!-- tags: mutex, rwlock, lock guard, raii, poisoning, rust, critical section -->

A mutex kölcsönös kizárást biztosít: egyszerre egy szál lehet a kritikus szakaszban. Az
olvasó-író zár (RwLock) sok egyidejű olvasót vagy egyetlen írót enged — olvasás-domináns
adatnál előnyös, de írás-intenzív terhelésnél a nagyobb overhead miatt lassabb lehet egy sima
mutexnél. Rustban a zár birtokolja az adatot, így zár nélkül hozzá sem lehet férni, a guard
pedig hatókör végén (RAII) automatikusan felenged. Szabályok: a kritikus szakasz legyen rövid,
zár alatt ne végezz I/O-t, és ne próbáld ugyanabban a szálban újra megszerezni ugyanazt a
(nem rekurzív) zárat.

```rust
use std::collections::HashMap;
use std::sync::{Arc, Mutex, RwLock};
use std::thread;

// A zár BIRTOKOLJA az adatot: az adatverseny fordítási hibává válik
struct Stats {
    hits: Mutex<u64>,
    config: RwLock<HashMap<String, String>>, // sok olvasó VAGY egy író
}

fn main() {
    let stats = Arc::new(Stats {
        hits: Mutex::new(0),
        config: RwLock::new(HashMap::from([("mode".to_string(), "fast".to_string())])),
    });

    let mut handles = Vec::new();
    for i in 0..8 {
        let s = Arc::clone(&stats); // Arc: megosztott tulajdon atomikus referenciaszámlálással
        handles.push(thread::spawn(move || {
            for _ in 0..1000 {
                *s.hits.lock().unwrap() += 1; // a guard az utasítás végén felenged
            }
            // Az ideiglenes read guard az utasítás végén eldobódik, mielőtt írnánk
            let mode = s.config.read().unwrap().get("mode").cloned();
            if i == 0 {
                s.config.write().unwrap().insert("mode".into(), "safe".into());
            }
            mode
        }));
    }
    for h in handles {
        let _ = h.join().unwrap();
    }
    println!("hits = {}", *stats.hits.lock().unwrap()); // 8000
    println!("mode = {:?}", stats.config.read().unwrap().get("mode"));

    // Mérgezett (poisoned) mutex: ha egy szál a zár tartása közben pánikol,
    // a lock() Err-t ad; eldönthetjük, hogy az adat használható-e még.
    let m = Arc::new(Mutex::new(vec![1, 2, 3]));
    let m2 = Arc::clone(&m);
    let _ = thread::spawn(move || {
        let _g = m2.lock().unwrap();
        panic!("hiba a kritikus szakaszban");
    })
    .join();
    let data = m.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
    println!("helyreállítva: {:?}", *data);
}
```

## Szemafor: párhuzamossági korlát
<!-- q: Mire jó a szemafor, és miben különbözik a mutextől? -->
<!-- tags: semaphore, concurrency limit, rate limiting, asyncio, connection pool -->

A számláló szemafor N engedélyt kezel: az acquire csökkenti, a release növeli a számlálót, nulla
esetén a kérő vár. Tipikus használat a párhuzamosság korlátozása (legfeljebb N egyidejű
letöltés, adatbázis-kapcsolat, GPU-feladat). A mutextől abban különbözik, hogy nincs
„tulajdonosa”: bármely szál elengedheti, és N > 1 is lehet; a BoundedSemaphore hibát dob, ha
többször engedik el, mint ahányszor megszerezték. Buktató: sok ezer feladatnál ne hozz létre
mindegyikhez korutint előre — egy fix méretű worker-készlet olcsóbb.

```python
import asyncio
import random
import time

async def fetch(i: int, sem: asyncio.Semaphore, stats: dict[str, int]) -> str:
    async with sem:  # legfeljebb N korutin lehet egyszerre ebben a blokkban
        stats["active"] += 1
        stats["peak"] = max(stats["peak"], stats["active"])
        try:
            await asyncio.sleep(random.uniform(0.05, 0.15))  # hálózati hívás helyett
            return f"oldal-{i}"
        finally:
            stats["active"] -= 1  # kivételnél is lefut

async def main() -> None:
    sem = asyncio.Semaphore(5)  # pl. a cél API legfeljebb 5 párhuzamos kapcsolatot enged
    stats = {"active": 0, "peak": 0}
    t0 = time.perf_counter()
    results = await asyncio.gather(*(fetch(i, sem, stats) for i in range(50)))
    print(len(results), "letöltve, csúcs:", stats["peak"], f"{time.perf_counter() - t0:.2f} s")

if __name__ == "__main__":
    asyncio.run(main())  # csúcs: 5, idő kb. 50/5 * 0.1 s = ~1 s
```

## Condition variable és blokkoló sor
<!-- q: Hogyan használjam a condition variable-t, és mi az a spurious wakeup? -->
<!-- tags: condition variable, blocking queue, producer consumer, spurious wakeup, notify -->

A condition variable lehetővé teszi, hogy egy szál zár alatt egy feltétel teljesülésére várjon
(pl. „a sor nem üres”) anélkül, hogy pörögne: a `wait` atomikusan elengedi a zárat és alszik,
ébredéskor újra megszerzi. A feltételt mindig ciklusban (vagy predikátumos wait-tel) kell
ellenőrizni, mert hamis ébredés (spurious wakeup) előfordulhat, és egy másik szál közben
elviheti az elemet. A klasszikus alkalmazás a korlátos termelő–fogyasztó sor; lezáráskor
`notify_all` kell, hogy minden várakozó kilépjen.

```cpp
#include <condition_variable>
#include <deque>
#include <iostream>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <thread>
#include <vector>

// Korlátos blokkoló sor: tele => a termelő vár, üres => a fogyasztó vár
template <typename T>
class BoundedQueue {
public:
    explicit BoundedQueue(size_t cap) : cap_(cap) {}

    void push(T v) {
        std::unique_lock lk(mu_);
        // predikátumos wait: belül ciklus, így véd a hamis ébredés ellen
        not_full_.wait(lk, [&] { return q_.size() < cap_ || closed_; });
        if (closed_) throw std::runtime_error("a sor lezárva");
        q_.push_back(std::move(v));
        lk.unlock();  // a zár elengedése után értesítünk: a felébredő nem blokkol rögtön
        not_empty_.notify_one();
    }

    std::optional<T> pop() {  // nullopt, ha lezárt és üres
        std::unique_lock lk(mu_);
        not_empty_.wait(lk, [&] { return !q_.empty() || closed_; });
        if (q_.empty()) return std::nullopt;
        T v = std::move(q_.front());
        q_.pop_front();
        lk.unlock();
        not_full_.notify_one();
        return v;
    }

    void close() {
        { std::lock_guard lk(mu_); closed_ = true; }
        not_empty_.notify_all();  // MINDEN várakozót fel kell ébreszteni
        not_full_.notify_all();
    }

private:
    std::mutex mu_;
    std::condition_variable not_full_, not_empty_;
    std::deque<T> q_;
    size_t cap_;
    bool closed_ = false;
};

int main() {
    BoundedQueue<int> q(4);
    std::mutex out_mu;
    std::vector<std::thread> consumers;
    for (int c = 0; c < 3; ++c) {
        consumers.emplace_back([&, c] {
            long sum = 0;
            while (auto v = q.pop()) sum += *v;
            std::lock_guard lk(out_mu);
            std::cout << "fogyasztó " << c << " összeg: " << sum << '\n';
        });
    }
    for (int i = 1; i <= 100; ++i) q.push(i);  // a termelő blokkol, ha a sor tele van
    q.close();
    for (auto& t : consumers) t.join();
}
```

## Holtpont (deadlock) és elkerülése
<!-- q: Hogyan alakul ki holtpont, és hogyan kerülhetem el? -->
<!-- tags: deadlock, lock ordering, coffman conditions, timeout, trylock, circular wait -->

Holtpont akkor van, ha szálak körben egymásra várnak, és egyik sem tud haladni. A négy Coffman-
feltétel (kölcsönös kizárás, tartás és várakozás, nincs elvétel, körkörös várakozás) együttes
teljesülése kell hozzá — bármelyik megszüntetése megelőzi. A leggyakoribb gyakorlati megoldás a
globális zársorrend (pl. azonosító szerint), ami kizárja a körkörös várakozást; alternatíva az
időkorlátos zárszerzés visszalépéssel, vagy egyetlen durvább zár. Az adatbázisok várakozási
gráffal felismerik a holtpontot, és az egyik tranzakciót megszakítják — ezért az
alkalmazásnak újra kell tudnia próbálni.

```python
import threading
from dataclasses import dataclass, field

@dataclass
class Account:
    id: int
    balance: int
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

def transfer_deadlock_prone(a: Account, b: Account, amount: int) -> None:
    # VESZÉLYES: T1: transfer(x, y) zárja x-et, vár y-ra;
    # T2: transfer(y, x) zárja y-t, vár x-re => mindketten örökké várnak.
    with a.lock:
        with b.lock:
            a.balance -= amount
            b.balance += amount

def transfer(a: Account, b: Account, amount: int) -> None:
    # Globális zársorrend (azonosító szerint): nincs körkörös várakozás
    first, second = (a, b) if a.id < b.id else (b, a)
    with first.lock, second.lock:
        if a.balance < amount:
            raise ValueError("nincs fedezet")
        a.balance -= amount
        b.balance += amount

def transfer_with_timeout(a: Account, b: Account, amount: int, timeout: float = 0.5) -> bool:
    # Alternatíva: időkorlát + visszalépés; a hívó véletlen várakozás után újrapróbál
    if not a.lock.acquire(timeout=timeout):
        return False
    try:
        if not b.lock.acquire(timeout=timeout):
            return False  # a finally elengedi a.lock-ot is
        try:
            a.balance -= amount
            b.balance += amount
            return True
        finally:
            b.lock.release()
    finally:
        a.lock.release()

def worker(src: Account, dst: Account) -> None:
    for _ in range(10_000):
        transfer(src, dst, 1)

if __name__ == "__main__":
    x, y = Account(1, 1_000_000), Account(2, 1_000_000)
    threads = [threading.Thread(target=worker, args=(x, y)), threading.Thread(target=worker, args=(y, x))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(x.balance + y.balance)  # 2000000: nincs holtpont, nincs elveszett pénz
```

## Livelock és kiéheztetés (starvation)
<!-- q: Mi a livelock és a starvation, és hogyan védekezzek ellenük? -->
<!-- tags: livelock, starvation, fairness, backoff, jitter, priority inversion, trylock -->

Livelocknál a szálak nem blokkolnak, hanem folyamatosan reagálnak egymásra (pl. mindkettő
udvariasan elengedi a zárat és azonnal újrapróbál), így dolgoznak, de nem haladnak; a megoldás a
véletlenített, exponenciálisan növekvő várakozás (backoff + jitter). Kiéheztetésnél egy szál
sosem jut erőforráshoz, mert mások mindig megelőzik — tipikusan nem fair zárak vagy
prioritásos ütemezés miatt. Fair (FIFO) zár megoldja, cserébe kisebb az áteresztőképesség.
Rokon jelenség a prioritásinverzió (alacsony prioritású szál tartja a zárat, amire a magas
vár), amit prioritásöröklés old meg.

```java
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.ReentrantLock;

public class LivelockDemo {
    // fair = true: a legrégebben váró kapja meg a zárat => nincs kiéheztetés
    static final ReentrantLock a = new ReentrantLock(true);
    static final ReentrantLock b = new ReentrantLock(true);

    // Mindkét zár megszerzése; sikertelenség esetén minden elengedése és véletlen várakozás.
    // Jitter nélkül a két szál ugyanabban az ütemben ütközhetne a végtelenségig (livelock).
    static void doWork(ReentrantLock first, ReentrantLock second, String name) throws InterruptedException {
        long backoffMs = 1;
        int attempts = 0;
        while (true) {
            attempts++;
            if (first.tryLock(10, TimeUnit.MILLISECONDS)) {
                try {
                    if (second.tryLock(10, TimeUnit.MILLISECONDS)) {
                        try {
                            System.out.println(name + " kész a(z) " + attempts + ". próbálkozásra");
                            return;
                        } finally {
                            second.unlock();
                        }
                    }
                } finally {
                    first.unlock(); // nem sikerült mindkettő: visszalépés
                }
            }
            Thread.sleep(ThreadLocalRandom.current().nextLong(backoffMs + 1)); // jitter
            backoffMs = Math.min(backoffMs * 2, 64); // exponenciális, felső korláttal
        }
    }

    static void run(ReentrantLock x, ReentrantLock y, String name) {
        try {
            for (int i = 0; i < 3; i++) doWork(x, y, name);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt(); // a megszakítási jelzést nem nyeljük el
        }
    }

    public static void main(String[] args) throws InterruptedException {
        Thread t1 = new Thread(() -> run(a, b, "T1"));
        Thread t2 = new Thread(() -> run(b, a, "T2")); // ellentétes zársorrend
        t1.start();
        t2.start();
        t1.join();
        t2.join();
    }
}
```

## Atomikus műveletek és compare-and-swap
<!-- q: Hogyan működnek az atomikus műveletek és a CAS, és mikor elég a Relaxed rendezés? -->
<!-- tags: atomics, compare-and-swap, cas, fetch_add, memory ordering, false sharing, rust -->

Az atomikus műveletek oszthatatlanok: a CPU egyetlen utasítással (x86-on LOCK előtag, ARM-on
LL/SC vagy LSE) végzi el az olvasás–módosítás–írást. A compare-and-swap (CAS) csak akkor ír, ha
az érték még a várt; ha nem, újraolvasunk és újrapróbálunk — erre épül szinte minden lock-free
algoritmus. Csak számlálóhoz elég a Relaxed rendezés, de ha az atomikus változó más adat
közzétételét jelzi, Release/Acquire kell. Buktatók: nagy versengésnél a cache-vonal
„pattogása” lassít; a független, gyakran írt atomikus változókat külön cache-vonalra (64 bájt)
kell tenni a false sharing ellen.

```rust
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::sync::Arc;
use std::thread;

/// Atomikus maximum CAS-ciklussal (az std-ben fetch_max is van; itt a minta a lényeg)
fn cas_max(a: &AtomicU64, v: u64) -> u64 {
    let mut cur = a.load(Ordering::Relaxed);
    while v > cur {
        // a _weak változat hamisan is hibázhat, ezért mindig ciklusban használjuk
        match a.compare_exchange_weak(cur, v, Ordering::AcqRel, Ordering::Relaxed) {
            Ok(prev) => return prev,
            Err(actual) => cur = actual, // valaki megelőzött: friss értékkel újra
        }
    }
    cur
}

/// Csak egyetlen szál nyerhet: 0 -> saját azonosító
fn try_claim(flag: &AtomicUsize, me: usize) -> bool {
    flag.compare_exchange(0, me, Ordering::AcqRel, Ordering::Acquire).is_ok()
}

fn main() {
    let max = Arc::new(AtomicU64::new(0));
    let hits = Arc::new(AtomicU64::new(0));
    let owner = Arc::new(AtomicUsize::new(0));
    let handles: Vec<_> = (1..=8usize)
        .map(|id| {
            let (max, hits, owner) = (Arc::clone(&max), Arc::clone(&hits), Arc::clone(&owner));
            thread::spawn(move || {
                for i in 0..10_000u64 {
                    hits.fetch_add(1, Ordering::Relaxed); // számláló: Relaxed elég
                    cas_max(&max, (i * 7919 + id as u64 * 31) % 100_003);
                }
                if try_claim(&owner, id) {
                    println!("a(z) {id}. szál lett a vezető");
                }
            })
        })
        .collect();
    for h in handles {
        h.join().unwrap();
    }
    println!("hits={} max={}", hits.load(Ordering::Relaxed), max.load(Ordering::Relaxed));
}
```

## Lock-free adatszerkezetek és az ABA-probléma
<!-- q: Mi az ABA-probléma a lock-free algoritmusokban, és hogyan védekezzek ellene? -->
<!-- tags: lock-free, aba problem, treiber stack, tagged pointer, hazard pointers, epoch reclamation -->

A lock-free algoritmus garantálja, hogy valamelyik szál mindig halad (egy felfüggesztett szál
sem blokkolja a többit); a wait-free ennél is erősebb. Az ABA-probléma: egy szál kiolvassa az
A értéket, közben mások A→B→A-ra változtatják (pl. a csúcsot kiveszik, felszabadítják, és
ugyanazon a címen újra betesznek egy csúcsot), így a CAS tévesen sikerül. Védekezés: verziózott
(„tagged”) pointer, ami minden módosításnál nő, illetve biztonságos memória-visszanyerés
(hazard pointer, epoch-alapú felszabadítás, GC). Fontos: a lock-free kód nehezen helyes és
nem feltétlenül gyorsabb egy jó mutexnél — mérj, mielőtt választasz.

```cpp
#include <atomic>
#include <cstdint>
#include <iostream>
#include <optional>
#include <thread>
#include <vector>

// Treiber-féle lock-free verem verziózott fejjel (ABA ellen)
template <typename T>
class LockFreeStack {
    struct Node {
        T value;
        Node* next;
    };
    struct Head {
        Node* ptr;
        std::uintptr_t tag;  // minden sikeres CAS-nál nő (16 bájtos CAS: x86-64 cmpxchg16b)
    };
    std::atomic<Head> head_{Head{nullptr, 0}};

public:
    void push(T v) {
        Node* n = new Node{std::move(v), nullptr};
        Head old = head_.load(std::memory_order_relaxed);
        Head desired;
        do {
            n->next = old.ptr;
            desired = Head{n, old.tag + 1};
            // release: a csúcs tartalma látható lesz annak, aki acquire-rel olvassa a fejet
        } while (!head_.compare_exchange_weak(old, desired, std::memory_order_release,
                                              std::memory_order_relaxed));
    }

    std::optional<T> pop() {
        Head old = head_.load(std::memory_order_acquire);
        while (old.ptr) {
            // VIGYÁZAT: old.ptr->next olvasásakor egy másik szál már felszabadíthatta a csúcsot.
            // Éles kódban hazard pointer / epoch kell; itt ezért nem szabadítunk fel (szivárgás).
            Head desired{old.ptr->next, old.tag + 1};
            if (head_.compare_exchange_weak(old, desired, std::memory_order_acquire,
                                            std::memory_order_acquire)) {
                return std::move(old.ptr->value);
            }
            // sikertelen CAS: az old automatikusan friss értéket kapott, újrapróbáljuk
        }
        return std::nullopt;
    }
};

int main() {
    LockFreeStack<int> s;
    std::vector<std::thread> ts;
    for (int t = 0; t < 4; ++t)
        ts.emplace_back([&s, t] { for (int i = 0; i < 1000; ++i) s.push(t * 1000 + i); });
    for (auto& t : ts) t.join();
    long count = 0;
    while (s.pop()) ++count;
    std::cout << "kivett elemek: " << count << '\n';  // 4000
}
```

## Memóriamodell és happens-before
<!-- q: Mi az a memóriamodell és a happens-before reláció, és miért kell a release/acquire? -->
<!-- tags: memory model, happens-before, release acquire, reordering, volatile, seq_cst -->

A fordító és a CPU átrendezheti a memóriaműveleteket, amíg egyetlen szál szemszögéből az
eredmény azonos — más szálak viszont ezt láthatják. A memóriamodell rögzíti, mikor garantált a
láthatóság: ha A happens-before B, akkor B látja A hatását. C++-ban egy release-írás és az azt
kiolvasó acquire-olvasás szinkronizál; Javában a volatile írás/olvasás, a synchronized blokk és
a Thread.start/join; Go-ban a csatornaküldés megelőzi a fogadást. Az x86 (TSO) erős, az ARM
gyenge modellű, ezért a hibás kód gyakran csak ARM-on (pl. Apple Silicon, mobil) jön elő.

```cpp
#include <atomic>
#include <cassert>
#include <string>
#include <thread>

std::string payload;              // NEM atomikus adat
std::atomic<bool> ready{false};   // ez szinkronizál

void producer() {
    payload = "kész adat";                         // (1) sima írás
    ready.store(true, std::memory_order_release);  // (2) release: (1) nem csúszhat (2) mögé
}

void consumer() {
    while (!ready.load(std::memory_order_acquire)) {  // (3) acquire: (4) nem csúszhat (3) elé
        // pörgés; éles kódban condition variable vagy std::atomic::wait (C++20)
    }
    assert(payload == "kész adat");  // (4) garantáltan látja (1)-et: (1) happens-before (4)
}

// HIBÁS minta: relaxed rendezéssel nincs happens-before, a fogyasztó láthatja a jelzőt,
// de még a régi adatot (ARM-on ténylegesen előfordul).
std::atomic<bool> ready_relaxed{false};
int data_relaxed = 0;
void bad_producer() {
    data_relaxed = 42;
    ready_relaxed.store(true, std::memory_order_relaxed);  // nincs rendezési garancia!
}

int main() {
    std::thread c(consumer), p(producer);
    p.join();
    c.join();
    // seq_cst (alapértelmezés): egyetlen globális sorrend; a legkönnyebb helyesen használni
    std::atomic<int> x{0};
    x.fetch_add(1);
    return 0;
}
```

## Actor modell
<!-- q: Hogyan működik az actor modell, és mikor jobb a zároknál? -->
<!-- tags: actor model, mailbox, message passing, erlang, akka, supervision, asyncio -->

Az actor egy elszigetelt egység saját privát állapottal és postafiókkal: más actorok csak
üzenetet küldhetnek neki, ő pedig egyesével dolgozza fel őket, így az állapothoz nem kell zár.
Az Erlang/Elixir, az Akka és a Microsoft Orleans erre épül; az actorok helyfüggetlenek (helyi
vagy távoli címzett ugyanúgy kezelhető), a hibákat pedig felügyelő (supervisor) hierarchia
kezeli („let it crash”). Buktatók: korlátlan postafiók túlterhelésnél elfogyasztja a memóriát;
két actor egymásra váró kérés–válasza holtpontot okozhat (időkorlát kell); üzenetsorrend csak
egy küldő–fogadó páron belül garantált.

```python
import asyncio
from dataclasses import dataclass
from typing import Any

@dataclass
class Deposit:
    amount: int

@dataclass
class GetBalance:
    reply: asyncio.Future  # válaszcsatorna a kérdezőnek

class Actor:
    """Privát állapot + postafiók; egyszerre egy üzenet => nincs szükség zárra."""

    def __init__(self) -> None:
        self.mailbox: asyncio.Queue[Any] = asyncio.Queue(maxsize=1000)  # korlátos: backpressure
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def send(self, msg: Any) -> None:  # "tell": küldd el és ne várj válaszra
        await self.mailbox.put(msg)

    async def _run(self) -> None:
        while (msg := await self.mailbox.get()) is not None:  # None = leállító üzenet
            try:
                await self.receive(msg)
            except Exception as e:  # egy rossz üzenet ne ölje meg az actort (élesben: supervisor)
                print(f"{type(self).__name__} hiba: {e!r}")

    async def stop(self) -> None:
        await self.mailbox.put(None)
        if self._task:
            await self._task

    async def receive(self, msg: Any) -> None:
        raise NotImplementedError

class AccountActor(Actor):
    def __init__(self) -> None:
        super().__init__()
        self.balance = 0  # csak ez az actor fér hozzá

    async def receive(self, msg: Any) -> None:
        match msg:
            case Deposit(amount=a) if a > 0:
                self.balance += a
            case GetBalance(reply=fut):
                fut.set_result(self.balance)
            case _:
                raise ValueError(f"érvénytelen üzenet: {msg}")

async def ask(actor: Actor, make_msg) -> Any:
    """Kérés-válasz minta Future-rel, időkorláttal."""
    fut = asyncio.get_running_loop().create_future()
    await actor.send(make_msg(fut))
    return await asyncio.wait_for(fut, timeout=1.0)

async def main() -> None:
    acc = AccountActor()
    acc.start()
    await asyncio.gather(*(acc.send(Deposit(10)) for _ in range(100)))  # sok egyidejű küldő
    await acc.send(Deposit(-5))  # érvénytelen: naplóz, de az actor tovább él
    print("egyenleg:", await ask(acc, GetBalance))  # 1000
    await acc.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## CSP és csatornák: pipeline, fan-out, fan-in
<!-- q: Hogyan építsek párhuzamos feldolgozó pipeline-t csatornákkal? -->
<!-- tags: csp, channels, goroutines, pipeline, fan-out, fan-in, context cancellation -->

A CSP (Communicating Sequential Processes) modellben független folyamatok csatornákon
kommunikálnak — Go jelmondata: „ne memória megosztásával kommunikálj, hanem kommunikációval ossz
meg memóriát”. Egy pipeline szakaszai csatornákkal kapcsolódnak; fan-out-tal több worker olvas
ugyanarról a csatornáról, fan-in-nel egy csatornába fésüljük vissza az eredményeket. Szabályok:
mindig a küldő zárja a csatornát; minden goroutine-nak legyen kilépési útja (context
lemondás), különben goroutine-szivárgás lesz; a puffer nélküli csatorna egyben szinkronizációs
pont is.

```go
package main

import (
	"context"
	"fmt"
	"sync"
	"time"
)

func generate(ctx context.Context, nums ...int) <-chan int {
	out := make(chan int)
	go func() {
		defer close(out) // a küldő zárja a csatornát, soha a fogadó
		for _, n := range nums {
			select {
			case out <- n:
			case <-ctx.Done(): // lemondás: a goroutine nem szivárog
				return
			}
		}
	}()
	return out
}

func square(ctx context.Context, in <-chan int) <-chan int {
	out := make(chan int)
	go func() {
		defer close(out)
		for n := range in {
			time.Sleep(10 * time.Millisecond) // drága munka szimulálása
			select {
			case out <- n * n:
			case <-ctx.Done():
				return
			}
		}
	}()
	return out
}

func merge(ctx context.Context, chans ...<-chan int) <-chan int { // fan-in
	out := make(chan int)
	var wg sync.WaitGroup
	wg.Add(len(chans))
	for _, c := range chans {
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
	go func() { wg.Wait(); close(out) }() // csak ha minden forrás kiürült
	return out
}

func main() {
	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()
	src := generate(ctx, 1, 2, 3, 4, 5, 6, 7, 8)
	workers := make([]<-chan int, 4) // fan-out: 4 worker ugyanarról a csatornáról olvas
	for i := range workers {
		workers[i] = square(ctx, src)
	}
	sum := 0
	for v := range merge(ctx, workers...) { // érkezési sorrend nem determinisztikus
		sum += v
	}
	fmt.Println("négyzetösszeg:", sum) // 204
}
```

## Szálkészletek (thread pool) és méretezésük
<!-- q: Hogyan méretezzem és konfiguráljam a thread poolt? -->
<!-- tags: thread pool, executor, bounded queue, rejection policy, virtual threads, java -->

A szálkészlet előre létrehozott szálakon futtat feladatokat, így elkerüli a szálanként
indítás költségét és korlátozza az egyidejűséget. Méretezés: CPU-kötött munkára nagyjából a
magok száma, I/O-kötöttre magok × (1 + várakozási idő / számítási idő). A sor legyen korlátos —
a végtelen sor elrejti a túlterhelést, amíg el nem fogy a memória —, és legyen elutasítási
stratégia (pl. CallerRunsPolicy: a beküldő maga futtatja, ami természetes lassítás). Java 21+
virtuális szálaival blokkoló I/O-ra már nem kell pool: szálanként csak néhány száz bájt a
költség.

```java
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

public class PoolDemo {
    public static void main(String[] args) throws Exception {
        int cores = Runtime.getRuntime().availableProcessors();
        ThreadPoolExecutor pool = new ThreadPoolExecutor(
                cores, cores, 30, TimeUnit.SECONDS,
                new ArrayBlockingQueue<>(100),               // KORLÁTOS sor
                namedThreads("worker"),
                new ThreadPoolExecutor.CallerRunsPolicy());  // tele: a beküldő szál futtatja

        List<Future<Integer>> results = new ArrayList<>();
        for (int i = 0; i < 1_000; i++) {
            final int n = i;
            results.add(pool.submit(() -> {
                if (n == 500) throw new IllegalStateException("hibás feladat: " + n);
                return n * n;
            }));
        }
        long sum = 0;
        int failed = 0;
        for (Future<Integer> f : results) {
            try {
                sum += f.get(5, TimeUnit.SECONDS);  // mindig időkorláttal várjunk
            } catch (ExecutionException e) {
                failed++;  // a feladat kivétele itt jön elő; get() nélkül "elnyelődne"
            }
        }
        pool.shutdown();  // új feladatot nem fogad, a meglévőket befejezi
        if (!pool.awaitTermination(10, TimeUnit.SECONDS)) pool.shutdownNow();
        System.out.println("összeg=" + sum + " hibás=" + failed);

        // Java 21+: virtuális szál feladatonként, blokkoló I/O-hoz
        try (ExecutorService vexec = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 10_000; i++) {
                vexec.submit(() -> { Thread.sleep(100); return null; });
            }
        }  // a close() megvárja az összes feladatot
    }

    static ThreadFactory namedThreads(String prefix) {
        AtomicInteger seq = new AtomicInteger();
        // beszédes szálnév: thread dumpban és logban azonnal látszik, honnan jön
        return r -> new Thread(r, prefix + "-" + seq.incrementAndGet());
    }
}
```

## Eseményhurok (event loop) és aszinkron futtatókörnyezetek
<!-- q: Hogyan működik belül az event loop, és miért nem szabad benne blokkolni? -->
<!-- tags: event loop, async runtime, coroutine, asyncio, node.js, non-blocking io, scheduler -->

Az eseményhurok egyetlen szálon futtat sok korutint: mindegyik addig fut, amíg nem kell várnia
(I/O, időzítő), ekkor visszaadja a vezérlést, a hurok pedig a készen állók közül futtatja a
következőt; ha nincs kész feladat, az OS-től (epoll/kqueue/IOCP) vár eseményre a legközelebbi
időzítő lejártáig. Így működik az asyncio, a Node.js (libuv) és a Rust tokio (ez több szálon,
munkalopással). A legfontosabb szabály: a hurokban nem szabad blokkolni vagy hosszan számolni,
mert minden más feladat is áll — az ilyen munkát szálkészletbe kell kiszervezni
(`run_in_executor`, `spawn_blocking`, worker threads).

```python
import heapq
import time
from collections import deque
from typing import Generator

# Mini eseményhurok generátorokkal — az asyncio belső elve, egyszerűsítve.
# A feladat yield-del adja vissza a vezérlést, és megmondja, mennyit akar aludni.
Task = Generator[float, None, None]

class EventLoop:
    def __init__(self) -> None:
        self.ready: deque[Task] = deque()  # futásra kész feladatok
        self.sleeping: list[tuple[float, int, Task]] = []  # időzítők kupacban
        self._seq = 0  # holtverseny-bontó a kupachoz

    def spawn(self, task: Task) -> None:
        self.ready.append(task)

    def run(self) -> None:
        while self.ready or self.sleeping:
            if not self.ready:
                # Valódi hurokban itt epoll/kqueue/IOCP vár I/O-ra, ezzel a timeouttal
                time.sleep(max(0.0, self.sleeping[0][0] - time.monotonic()))
            now = time.monotonic()
            while self.sleeping and self.sleeping[0][0] <= now:
                self.ready.append(heapq.heappop(self.sleeping)[2])
            for _ in range(len(self.ready)):  # egy "tick": minden kész feladat egyet lép
                task = self.ready.popleft()
                try:
                    delay = next(task)  # fut a következő yield-ig
                except StopIteration:
                    continue  # a feladat befejeződött
                self._seq += 1
                heapq.heappush(self.sleeping, (time.monotonic() + delay, self._seq, task))

def worker(name: str, n: int, delay: float) -> Task:
    for i in range(n):
        print(f"{time.monotonic() % 100:6.2f} {name} lépés {i}")
        yield delay  # ~ "await asyncio.sleep(delay)"

def blocking_bad() -> Task:
    time.sleep(0.5)  # HIBA: blokkoló hívás a hurokban — minden más feladat is áll!
    yield 0

if __name__ == "__main__":
    loop = EventLoop()
    loop.spawn(worker("A", 3, 0.2))
    loop.spawn(worker("B", 3, 0.3))
    loop.run()  # A és B egymásba fésülve fut, egyetlen szálon
```

## Backpressure: amikor a termelő gyorsabb a fogyasztónál
<!-- q: Mi az a backpressure, és hogyan kezeljem, ha a termelő gyorsabb a fogyasztónál? -->
<!-- tags: backpressure, bounded queue, load shedding, flow control, producer consumer, streams -->

Ha a termelő tartósan gyorsabb a fogyasztónál, a köztük lévő puffer korlátlanul nő: nő a
késleltetés, végül elfogy a memória. A backpressure a terhelést visszafelé jelzi: korlátos sor
esetén a termelő blokkol/vár, amíg hely nem lesz (TCP flow control ablak, Reactive Streams
`request(n)`, Node streams `highWaterMark`). Ha a várakozás nem elfogadható (telemetria,
élő adat), terhelés-eldobás (load shedding), mintavételezés vagy összevonás jön; HTTP-szinten a
429/503 + Retry-After válasz a backpressure jele. Az alapértelmezetten végtelen sorok
(asyncio.Queue(), LinkedBlockingQueue()) a leggyakoribb rejtett hibaforrás.

```python
import asyncio
import random

async def blocking_producer(q: asyncio.Queue[int], n: int, stats: dict[str, int]) -> None:
    for i in range(n):
        await q.put(i)  # tele sor esetén VÁR: a lassú fogyasztó lassítja a termelőt
        stats["produced"] += 1

async def lossy_producer(q: asyncio.Queue[int], n: int, stats: dict[str, int]) -> None:
    for i in range(n):
        try:
            q.put_nowait(i)  # load shedding: inkább eldobjuk, mint hogy várjunk
            stats["produced"] += 1
        except asyncio.QueueFull:
            stats["dropped"] += 1
        await asyncio.sleep(0)  # vezérlés átadása a fogyasztóknak

async def consumer(q: asyncio.Queue[int], stats: dict[str, int]) -> None:
    while True:
        await q.get()
        await asyncio.sleep(random.uniform(0.001, 0.003))  # lassú feldolgozás
        stats["consumed"] += 1
        q.task_done()

async def run(kind: str) -> None:
    q: asyncio.Queue[int] = asyncio.Queue(maxsize=50)  # a korlát a lényeg; maxsize=0 végtelen!
    stats = {"produced": 0, "consumed": 0, "dropped": 0}
    consumers = [asyncio.create_task(consumer(q, stats)) for _ in range(4)]
    producer = blocking_producer if kind == "blokkoló" else lossy_producer
    await producer(q, 2_000, stats)
    await q.join()  # megvárjuk a betett elemek feldolgozását
    for c in consumers:
        c.cancel()
    await asyncio.gather(*consumers, return_exceptions=True)
    print(kind, stats)

if __name__ == "__main__":
    asyncio.run(run("blokkoló"))  # semmi sem vész el, a termelő lelassul
    asyncio.run(run("eldobó"))  # a termelő nem lassul, de elemek vesznek el
```

## Fork-join és munkalopás (work stealing)
<!-- q: Hogyan működik a fork-join párhuzamosítás és a work stealing ütemezés? -->
<!-- tags: fork-join, work stealing, forkjoinpool, divide and conquer, parallel streams, java -->

A fork-join az oszd-meg-és-uralkodj párhuzamos változata: a feladatot rekurzívan kisebbekre
bontjuk (fork), egy küszöb alatt sorosan számolunk, majd összevonjuk az eredményeket (join). A
munkalopásos ütemezőben minden szálnak saját deque-je van: a saját végéről LIFO-ban dolgozik
(cache-barát), a tétlen szál pedig egy másik szál deque-jének másik végéről lop (a nagyobb, még
fel nem bontott darabokat), így kevés szinkronizációval egyenletes a terhelés. Így működik a
Java ForkJoinPool, a Rust rayon, a Go ütemező és a .NET TPL. Buktatók: túl kicsi küszöbnél a
fork overheadje elviszi a nyereséget, és a közös poolban nem szabad blokkoló I/O-t végezni.

```java
import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.RecursiveTask;
import java.util.stream.LongStream;

class SumTask extends RecursiveTask<Long> {
    private static final int THRESHOLD = 10_000;  // ez alatt sorosan: a fork drágább lenne
    private final long[] data;
    private final int lo, hi;

    SumTask(long[] data, int lo, int hi) {
        this.data = data;
        this.lo = lo;
        this.hi = hi;
    }

    @Override
    protected Long compute() {
        if (hi - lo <= THRESHOLD) {
            long s = 0;
            for (int i = lo; i < hi; i++) s += data[i];
            return s;
        }
        int mid = (lo + hi) >>> 1;  // előjel nélküli eltolás: nincs túlcsordulás
        SumTask left = new SumTask(data, lo, mid);
        SumTask right = new SumTask(data, mid, hi);
        left.fork();                // a bal fél a saját deque-be kerül: más ellophatja
        long r = right.compute();   // a jobb felet mi számoljuk (nem forkolunk mindkettőt)
        return left.join() + r;     // join közben a szál más munkát is végezhet
    }
}

public class ForkJoinDemo {
    public static void main(String[] args) {
        long[] data = LongStream.rangeClosed(1, 10_000_000).toArray();
        long t0 = System.nanoTime();
        long sum = ForkJoinPool.commonPool().invoke(new SumTask(data, 0, data.length));
        System.out.printf("fork-join: %d (%d ms)%n", sum, (System.nanoTime() - t0) / 1_000_000);
        // A párhuzamos stream belül ugyanezt a common ForkJoinPoolt használja
        System.out.println("stream:    " + LongStream.of(data).parallel().sum());
    }
}
```

## Map-reduce párhuzamos adatfeldolgozás
<!-- q: Hogyan működik a map-reduce, és hogyan párhuzamosítsak vele adatfeldolgozást? -->
<!-- tags: map-reduce, parallel processing, multiprocessing, combiner, aggregation, amdahl -->

A map-reduce két lépésre bontja a feldolgozást: a map független darabokon, mellékhatás nélkül
állít elő részeredményeket (párhuzamosítható), a reduce asszociatív (és lehetőleg kommutatív)
művelettel vonja össze őket — ezért mindegy, milyen sorrendben érkeznek a részek. Elosztott
rendszerekben (Hadoop, Spark) közöttük egy „shuffle” csoportosít kulcs szerint; a helyi
előaggregálás (combiner) drasztikusan csökkenti a mozgatott adatot. Buktatók: túl apró
feladatoknál az IPC/szerializáció drágább a munkánál, az egyenetlen kulcseloszlás (data skew)
egyetlen reducert terhel túl, és Amdahl törvénye szerint a soros rész korlátozza a gyorsulást.

```python
import re
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from functools import reduce
from itertools import islice
from typing import Iterable, Iterator

WORD = re.compile(r"\w+", re.UNICODE)

def chunks(lines: Iterable[str], size: int) -> Iterator[list[str]]:
    """Nagyobb darabok: soronkénti feladatnál az IPC-költség dominálna."""
    it = iter(lines)
    while batch := list(islice(it, size)):
        yield batch

def map_phase(batch: list[str]) -> Counter[str]:
    """MAP: független, mellékhatásmentes, helyben előaggregál (combiner)."""
    c: Counter[str] = Counter()
    for line in batch:
        c.update(w.lower() for w in WORD.findall(line))
    return c

def reduce_phase(a: Counter[str], b: Counter[str]) -> Counter[str]:
    """REDUCE: asszociatív összevonás — a részek sorrendje mindegy."""
    a.update(b)
    return a

def word_count(lines: Iterable[str], workers: int = 4) -> Counter[str]:
    with ProcessPoolExecutor(workers) as pool:
        partials = pool.map(map_phase, chunks(lines, 5_000))
        return reduce(reduce_phase, partials, Counter())

if __name__ == "__main__":
    text = ["Az alma piros, a körte sárga.", "Az alma édes és az alma finom."] * 50_000
    print(word_count(text).most_common(3))
    # [('az', 150000), ('alma', 150000), (...50000)] — holtversenynél a sorrend változhat
```

## SIMD és GPU: adatpárhuzamosság
<!-- q: Mi a SIMD és a GPU-programozás lényege, és mikor éri meg? -->
<!-- tags: simd, avx, vectorization, gpu, cuda, simt, data parallelism, intrinsics -->

A SIMD (Single Instruction, Multiple Data) egy utasítással több adatelemen dolgozik egy magon
belül: AVX2-vel 8 float, AVX-512-vel 16, ARM NEON-nal 4 egyszerre. A fordító -O2/-O3 mellett
egyszerű ciklusokat gyakran magától vektorizál, kézi intrinsicekre csak mérés után van szükség.
A GPU ezer egyszerű magot futtat SIMT modellben (32-es warpok ugyanazt az utasítást hajtják
végre), így szabályos, nagy adatpárhuzamos feladatokon (mátrixműveletek, gépi tanulás,
képfeldolgozás) nagyságrendekkel gyorsabb. Buktatók: a CPU–GPU adatmozgatás (PCIe) gyakran
drágább a számításnál, az elágazások szétválasztják a warpot (divergencia), és a lebegőpontos
összeadás nem asszociatív, így a párhuzamos eredmény az utolsó jegyekben eltérhet.

```cpp
#include <immintrin.h>  // x86 SIMD intrinsicek (AVX2 + FMA)
#include <cstddef>
#include <iostream>
#include <vector>

// Skalár változat: -O3 mellett a fordító gyakran magától vektorizálja
float dot_scalar(const float* a, const float* b, std::size_t n) {
    float s = 0.0f;
    for (std::size_t i = 0; i < n; ++i) s += a[i] * b[i];
    return s;
}

// Kézi AVX2/FMA: egy utasítás 8 szorzás-összeadás. Fordítás: -O2 -mavx2 -mfma;
// élesben futásidőben ellenőrizni kell a CPU támogatását (pl. __builtin_cpu_supports).
float dot_avx2(const float* a, const float* b, std::size_t n) {
    __m256 acc = _mm256_setzero_ps();
    std::size_t i = 0;
    for (; i + 8 <= n; i += 8) {
        __m256 va = _mm256_loadu_ps(a + i);  // 8 float betöltése (igazítás nélkül)
        __m256 vb = _mm256_loadu_ps(b + i);
        acc = _mm256_fmadd_ps(va, vb, acc);  // acc += va * vb, sávonként
    }
    // Horizontális összegzés: 8 sáv -> 1 szám
    __m128 sum4 = _mm_add_ps(_mm256_castps256_ps128(acc), _mm256_extractf128_ps(acc, 1));
    __m128 shuf = _mm_movehdup_ps(sum4);
    __m128 sums = _mm_add_ps(sum4, shuf);
    shuf = _mm_movehl_ps(shuf, sums);
    sums = _mm_add_ss(sums, shuf);
    float s = _mm_cvtss_f32(sums);
    for (; i < n; ++i) s += a[i] * b[i];  // maradék elemek, ha n nem osztható 8-cal
    return s;
}

int main() {
    std::vector<float> a(1003, 0.5f), b(1003, 2.0f);
    std::cout << dot_scalar(a.data(), b.data(), a.size()) << ' '
              << dot_avx2(a.data(), b.data(), a.size()) << '\n';  // 1003 1003
}
```
