# Algoritmusok és adatszerkezetek
<!-- tech: algorithms -->
<!-- aliases: algoritmusok, adatszerkezetek, dsa, data structures, algorithms, algo -->

Nyelvfüggetlen alapok: hogyan mérjük egy algoritmus költségét, melyik adatszerkezet milyen
műveletet tesz olcsóvá, és a klasszikus rendező-, kereső-, gráf-, dinamikus programozási és
szövegkereső algoritmusok belső működése. A példák a legérthetőbb nyelven készültek (főleg
Python, mellette Go, C++, Rust, Java, TypeScript); a lényeg az invariánsokon és a komplexitáson van.

## Időkomplexitás és amortizált elemzés
<!-- q: Mit jelent az O(n), és mi az amortizált költség? -->
<!-- tags: big-o, complexity, amortized analysis, dynamic array, potential method -->

A Big-O a futási idő felső korlátja a bemenet méretének függvényében (Θ: pontos nagyságrend,
Ω: alsó korlát); a konstansokat és a kisebb tagokat elhagyjuk, ezért egy O(n) algoritmus kis
n-re lehet lassabb egy O(n log n)-esnél. Az amortizált elemzés egy műveletsorozat teljes
költségét osztja szét: a dinamikus tömb néha O(n)-es másolást végez, de kétszerezéssel a teljes
költség n beszúrásra < 3n, így az append amortizáltan O(1). Buktató: fix lépésközű növelés (+k)
O(n²)-et ad, és ha zsugorításnál ugyanazon a küszöbön (1/2) nő és csökken a tömb, „thrashing” lép
fel — zsugorítani 1/4-es telítettségnél érdemes.

```python
# Dinamikus tömb kétszerezéssel: az append amortizáltan O(1)
class DynArray:
    def __init__(self) -> None:
        self._cap = 1
        self._n = 0
        self._data: list[object | None] = [None] * self._cap
        self.copies = 0  # összesen hány elemet másoltunk (költségmérés)

    def append(self, x: object) -> None:
        if self._n == self._cap:
            self._grow(self._cap * 2)  # geometriai növekedés: ez adja az O(1)-et
        self._data[self._n] = x
        self._n += 1

    def _grow(self, new_cap: int) -> None:
        new: list[object | None] = [None] * new_cap
        for i in range(self._n):  # O(n) másolás, de egyre ritkábban történik
            new[i] = self._data[i]
            self.copies += 1
        self._data, self._cap = new, new_cap

    def __len__(self) -> int:
        return self._n

if __name__ == "__main__":
    for n in (1_000, 100_000):
        a = DynArray()
        for i in range(n):
            a.append(i)
        # 1 + 2 + 4 + ... < 2n másolás => elemenként átlagosan konstans
        print(n, a.copies, round(a.copies / n, 3))
```

## Quicksort: pivotválasztás és háromutas particionálás
<!-- q: Hogyan működik a quicksort, és mikor lesz O(n^2)? -->
<!-- tags: quicksort, partition, pivot, sorting, divide and conquer, introsort -->

A quicksort egy pivot körül két (vagy három) részre osztja a tömböt, majd rekurzívan rendezi a
részeket; átlagosan O(n log n), helyben dolgozik és cache-barát, ezért a gyakorlatban nagyon
gyors. Rossz pivotnál (pl. mindig az első elem rendezett bemeneten) O(n²) lesz, sok egyenlő
kulcsnál pedig a kétutas particionálás is elfajul — ezért véletlen pivot és háromutas (<, =, >)
particionálás kell. Ha a kisebbik részre rekurzálunk, a nagyobbikat ciklusban dolgozzuk fel, a
verem mélysége O(log n) marad; az introsort (std::sort) ráadásul heapsortra vált túl mély
rekurziónál. Nem stabil rendezés.

```python
import random

def quicksort(a: list[int], lo: int = 0, hi: int | None = None) -> None:
    """Helyben rendez; véletlen pivot + háromutas (Dijkstra-féle) particionálás."""
    if hi is None:
        hi = len(a) - 1
    while lo < hi:
        if hi - lo < 16:  # kis tartományon a beszúró rendezés gyorsabb
            insertion_sort(a, lo, hi)
            return
        pivot = a[random.randint(lo, hi)]  # véletlen pivot: nincs rossz bemenet
        lt, i, gt = lo, lo, hi
        # Invariáns: a[lo:lt] < pivot, a[lt:i] == pivot, a[gt+1:hi+1] > pivot
        while i <= gt:
            if a[i] < pivot:
                a[lt], a[i] = a[i], a[lt]
                lt += 1
                i += 1
            elif a[i] > pivot:
                a[i], a[gt] = a[gt], a[i]
                gt -= 1
            else:
                i += 1
        # Kisebbik oldal rekurzívan, nagyobbik ciklusban: verem mélység O(log n)
        if lt - lo < hi - gt:
            quicksort(a, lo, lt - 1)
            lo = gt + 1
        else:
            quicksort(a, gt + 1, hi)
            hi = lt - 1

def insertion_sort(a: list[int], lo: int, hi: int) -> None:
    for i in range(lo + 1, hi + 1):
        x, j = a[i], i - 1
        while j >= lo and a[j] > x:
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = x

if __name__ == "__main__":
    data = [random.randint(0, 50) for _ in range(1000)]  # sok ismétlődő kulcs
    expected = sorted(data)
    quicksort(data)
    assert data == expected
```

## Merge sort és a Timsort ötletei
<!-- q: Miért stabil a merge sort, és mit csinál másképp a Timsort? -->
<!-- tags: merge sort, timsort, stable sort, runs, galloping, sorting -->

A merge sort felezi a tömböt, rekurzívan rendezi a feleket, majd lineáris időben összefésüli
őket: garantáltan O(n log n), stabil (egyenlő kulcsok sorrendje megmarad), de O(n) segédmemóriát
igényel. A Timsort (Python, Java objektumrendezés) erre épít: megkeresi a bemenetben a már
rendezett „futamokat” (run), a rövideket beszúró rendezéssel minrun (32–64) hosszúra bővíti,
egy veremben tartott futamokat kiegyensúlyozottan fésül össze, és „galloping” módban
exponenciális kereséssel ugorja át a hosszú egyoldalú szakaszokat. Ezért részben rendezett
valós adatokon közel O(n). Buktató: rekurziónként újra allokált puffer lassú — egyetlen
segédtömböt használj.

```go
package main

import "fmt"

// MergeSort stabil, O(n log n) idejű, O(n) extra memóriát használ.
func MergeSort(a []int) {
	buf := make([]int, len(a)) // egyetlen segédpuffer, nem allokálunk rekurziónként
	sortRange(a, buf, 0, len(a))
}

func sortRange(a, buf []int, lo, hi int) {
	if hi-lo <= 32 { // Timsort-ötlet: rövid szakaszra beszúró rendezés
		insertion(a, lo, hi)
		return
	}
	mid := lo + (hi-lo)/2
	sortRange(a, buf, lo, mid)
	sortRange(a, buf, mid, hi)
	if a[mid-1] <= a[mid] { // a két fél már sorban van: nincs mit fésülni
		return
	}
	merge(a, buf, lo, mid, hi)
}

func merge(a, buf []int, lo, mid, hi int) {
	copy(buf[lo:hi], a[lo:hi])
	i, j := lo, mid
	for k := lo; k < hi; k++ {
		switch {
		case i >= mid:
			a[k] = buf[j]
			j++
		case j >= hi:
			a[k] = buf[i]
			i++
		case buf[j] < buf[i]: // szigorú <: egyenlőnél a bal elem jön => stabil
			a[k] = buf[j]
			j++
		default:
			a[k] = buf[i]
			i++
		}
	}
}

func insertion(a []int, lo, hi int) {
	for i := lo + 1; i < hi; i++ {
		x, j := a[i], i-1
		for j >= lo && a[j] > x {
			a[j+1] = a[j]
			j--
		}
		a[j+1] = x
	}
}

func main() {
	xs := []int{9, 3, 7, 1, 8, 2, 6, 4, 5, 0}
	MergeSort(xs)
	fmt.Println(xs)
}
```

## Bináris kupac, heapsort és prioritási sor
<!-- q: Hogyan működik a kupac és a prioritási sor, mire jó a heapsort? -->
<!-- tags: heap, binary heap, heapsort, priority queue, top-k, sift down -->

A bináris kupac egy tömbben tárolt teljes bináris fa (i gyerekei 2i+1 és 2i+2), ahol minden
szülő ≥ gyerekei (max-kupac); a csúcs olvasása O(1), beszúrás és kivétel O(log n), a kupacépítés
alulról felfelé O(n). Erre épül a prioritási sor (ütemezők, Dijkstra, top-k) és a heapsort, ami
helyben, garantált O(n log n)-ben rendez, de nem stabil és cache-kezelése rosszabb a
quicksortnál. Top-k elemhez k méretű MIN-kupac kell: O(n log k) idő, O(k) memória, streamre is
működik.

```cpp
#include <functional>
#include <iostream>
#include <queue>
#include <vector>

// Lesüllyesztés max-kupacban az [0, n) tartományon
void siftDown(std::vector<int>& a, size_t i, size_t n) {
    while (true) {
        size_t largest = i, l = 2 * i + 1, r = 2 * i + 2;
        if (l < n && a[l] > a[largest]) largest = l;
        if (r < n && a[r] > a[largest]) largest = r;
        if (largest == i) return;  // a kupactulajdonság helyreállt
        std::swap(a[i], a[largest]);
        i = largest;
    }
}

// Heapsort: O(n) építés + n darab O(log n) kivétel, helyben, NEM stabil
void heapSort(std::vector<int>& a) {
    size_t n = a.size();
    for (size_t i = n / 2; i-- > 0;) siftDown(a, i, n);
    for (size_t end = n; end > 1; --end) {
        std::swap(a[0], a[end - 1]);  // a maximum a rendezett végre kerül
        siftDown(a, 0, end - 1);
    }
}

// Top-k legnagyobb elem k méretű min-kupaccal
std::vector<int> topK(const std::vector<int>& xs, size_t k) {
    if (k == 0) return {};
    std::priority_queue<int, std::vector<int>, std::greater<int>> pq;
    for (int x : xs) {
        if (pq.size() < k) {
            pq.push(x);
        } else if (x > pq.top()) {  // csak a kupac minimumánál nagyobb érdekes
            pq.pop();
            pq.push(x);
        }
    }
    std::vector<int> out;
    while (!pq.empty()) {
        out.push_back(pq.top());
        pq.pop();
    }
    return out;  // növekvő sorrendben
}

int main() {
    std::vector<int> v{5, 1, 9, 3, 7, 2, 8};
    heapSort(v);
    for (int x : v) std::cout << x << ' ';
    std::cout << '\n';
    for (int x : topK({4, 10, 2, 15, 7, 1}, 3)) std::cout << x << ' ';  // 7 10 15
    std::cout << '\n';
}
```

## Nem összehasonlító rendezések: counting és radix sort
<!-- q: Hogyan lehet O(n log n)-nél gyorsabban rendezni? -->
<!-- tags: radix sort, counting sort, lsd, bucket sort, linear time sorting -->

Összehasonlítás alapú rendezés nem lehet gyorsabb Ω(n log n)-nél, de ha a kulcsok korlátos
egészek, a counting sort O(n + k)-ban rendez úgy, hogy megszámolja az értékeket és prefix
összeggel kiszámolja a helyüket. Az LSD radix sort a legkisebb helyiértékű „számjegytől” (itt
bájttól) haladva stabil counting sorttal rendez, így d számjegyre O(d·(n + b)). A stabilitás
kulcsfontosságú: enélkül az előző menetek sorrendje elveszne. Buktató: negatív számokhoz
eltolás vagy előjelbit-kezelés kell, és kis n-nél a 256 elemű számlálótömbök overheadje miatt a
sima sort() gyorsabb.

```python
def counting_sort_by_byte(a: list[int], shift: int) -> list[int]:
    """Stabil számláló rendezés egy bájt (256 vödör) szerint."""
    count = [0] * 257
    for x in a:
        count[((x >> shift) & 0xFF) + 1] += 1
    for i in range(256):  # prefix összeg: minden vödör kezdőindexe
        count[i + 1] += count[i]
    out = [0] * len(a)
    for x in a:  # balról jobbra haladunk => stabil, ez kell az LSD-hez
        b = (x >> shift) & 0xFF
        out[count[b]] = x
        count[b] += 1
    return out

def radix_sort(a: list[int]) -> list[int]:
    """LSD radix rendezés nemnegatív egészekre: O(d * (n + 256))."""
    if not a:
        return a
    if min(a) < 0:
        raise ValueError("csak nemnegatív egészekre; negatívaknál told el az értékeket")
    shift, biggest = 0, max(a)
    while (biggest >> shift) > 0:  # annyi menet, ahány bájtos a legnagyobb elem
        a = counting_sort_by_byte(a, shift)
        shift += 8
    return a

if __name__ == "__main__":
    import random

    xs = [random.randrange(1 << 32) for _ in range(10_000)]
    assert radix_sort(xs) == sorted(xs)
```

## Bináris keresés változatai
<!-- q: Hogyan írjak hibátlan bináris keresést (lower bound, upper bound, válaszra keresés)? -->
<!-- tags: binary search, lower bound, upper bound, bisect, search on answer, monotonic predicate -->

A bináris keresés egy monoton feltétel (F…F T…T) határát keresi O(log n) lépésben; a hibák
szinte mindig az intervallumhatárokból jönnek, ezért érdemes egyetlen sémát használni: félig
nyílt [lo, hi) intervallum, `while lo < hi`, és a ciklus végén lo a válasz. A lower_bound az
első ≥ x, az upper_bound az első > x elem indexe; különbségük az x előfordulásainak száma.
A „válaszra keresés” akkor működik, ha a megvalósíthatóság monoton a paraméterben (pl. nagyobb
kapacitással biztosan belefér). C++/Java-ban `(lo + hi) / 2` túlcsordulhat, ott `lo + (hi - lo) / 2`.

```python
from typing import Callable, Sequence

def lower_bound(a: Sequence[int], x: int) -> int:
    """Az első index, ahol a[i] >= x (len(a), ha nincs ilyen)."""
    lo, hi = 0, len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] < x:
            lo = mid + 1  # mid biztosan nem válasz
        else:
            hi = mid      # mid lehet a válasz, megtartjuk
    return lo

def upper_bound(a: Sequence[int], x: int) -> int:
    """Az első index, ahol a[i] > x."""
    lo, hi = 0, len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] <= x:
            lo = mid + 1
        else:
            hi = mid
    return lo

def first_true(lo: int, hi: int, pred: Callable[[int], bool]) -> int:
    """Monoton predikátum első igaz helye [lo, hi]-ban; hi, ha addig mind hamis."""
    while lo < hi:
        mid = (lo + hi) // 2
        if pred(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo

def min_ship_capacity(weights: list[int], days: int) -> int:
    """Válaszra keresés: legkisebb kapacitás, amivel `days` nap alatt minden elszállítható."""
    def feasible(cap: int) -> bool:
        used, load = 1, 0
        for w in weights:
            if load + w > cap:  # új nap kezdődik
                used, load = used + 1, 0
            load += w
        return used <= days

    return first_true(max(weights), sum(weights), feasible)

if __name__ == "__main__":
    a = [1, 2, 2, 2, 5, 8]
    assert lower_bound(a, 2) == 1 and upper_bound(a, 2) == 4
    assert min_ship_capacity([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5) == 15
```

## Hash tábla: nyílt címzés vs. láncolás
<!-- q: Hogyan működik belül a hash tábla, és mi a különbség a nyílt címzés és a láncolás között? -->
<!-- tags: hash table, hashmap, open addressing, chaining, linear probing, load factor, tombstone -->

A hash tábla a kulcs hash-éből számolt indexre teszi az elemet, így a keresés átlagosan O(1),
legrosszabb esetben O(n). Láncolásnál minden vödör egy lista (a Java HashMap 8 elem felett
kiegyensúlyozott fává alakítja); nyílt címzésnél ütközéskor a tömbben keresünk új helyet
(lineáris próbálgatás: cache-barát, de klaszteresedik), és törléskor „sírkövet” kell hagyni,
különben megszakadnak a keresési láncok. A telítettséget (load factor) ~0,7 alatt kell tartani,
efölött kétszerezés és újrahash-elés jön (amortizáltan O(1)). Buktató: kiszámítható hash
függvénnyel a támadó ütközéseket gyárthat (HashDoS) — ezért használ a Python/Rust véletlen
seedes SipHash-t.

```python
_EMPTY = object()
_TOMB = object()  # sírkő: törölt hely, a keresés továbblép rajta

class OpenAddressingMap:
    """Lineáris próbálgatás; (élő + sírkő) / kapacitás > 0.7 esetén kétszerezés."""

    def __init__(self, cap: int = 8) -> None:
        self._keys: list = [_EMPTY] * cap  # a kapacitás mindig 2 hatványa
        self._vals: list = [None] * cap
        self._size = 0  # élő elemek
        self._used = 0  # élő + sírkő: ez határozza meg a próbaláncok hosszát

    def _slot(self, key) -> int:
        """A kulcs helye, vagy beszúráshoz az első sírkő / üres hely."""
        mask = len(self._keys) - 1
        i = hash(key) & mask
        first_tomb = -1
        while True:  # a load factor miatt mindig van üres hely, a ciklus véget ér
            k = self._keys[i]
            if k is _EMPTY:
                return first_tomb if first_tomb >= 0 else i
            if k is _TOMB:
                if first_tomb < 0:
                    first_tomb = i
            elif k == key:
                return i
            i = (i + 1) & mask  # következő rekesz: egymás melletti memória

    def put(self, key, val) -> None:
        if (self._used + 1) / len(self._keys) > 0.7:
            self._resize(len(self._keys) * 2)
        i = self._slot(key)
        k = self._keys[i]
        if k is _EMPTY or k is _TOMB:
            self._size += 1
            if k is _EMPTY:
                self._used += 1
        self._keys[i], self._vals[i] = key, val

    def get(self, key, default=None):
        i = self._slot(key)
        k = self._keys[i]
        return default if k is _EMPTY or k is _TOMB else self._vals[i]

    def delete(self, key) -> None:
        i = self._slot(key)
        k = self._keys[i]
        if k is not _EMPTY and k is not _TOMB:
            self._keys[i], self._vals[i] = _TOMB, None
            self._size -= 1

    def _resize(self, cap: int) -> None:
        live = [(k, v) for k, v in zip(self._keys, self._vals) if k is not _EMPTY and k is not _TOMB]
        self._keys, self._vals = [_EMPTY] * cap, [None] * cap
        self._size = self._used = 0
        for k, v in live:  # újrahash-elés: a sírkövek eltűnnek
            self.put(k, v)
```

## Kiegyensúlyozott keresőfák: AVL, piros-fekete fa, B-fa
<!-- q: Miért kellenek kiegyensúlyozott fák, és miben különbözik az AVL, a piros-fekete fa és a B-fa? -->
<!-- tags: avl tree, red-black tree, b-tree, b+ tree, rotation, balanced bst, database index -->

Egy sima bináris keresőfa rendezett beszúrásnál listává fajul (O(n) keresés); a kiegyensúlyozott
fák forgatásokkal O(log n) magasságot garantálnak. Az AVL minden csúcsban legfeljebb 1
magasságkülönbséget enged (gyorsabb keresés), a piros-fekete fa lazább (magasság ≤ 2·log n), így
kevesebb forgatással jár beszúráskor/törléskor — ezért ez van a std::map és a Java TreeMap
mögött. A B-fa csúcsai sok kulcsot tárolnak (fan-out 100+), egy csúcs egy lemezlapnak felel meg,
így pár lapolvasással megtalálható bármely kulcs; a B+ fa csak a levelekben tárol adatot és a
leveleket láncolja a gyors tartomány-lekérdezéshez (SQL indexek). A rendezett fák előnye a
hash táblával szemben: rendezett bejárás, min/max, tartomány-lekérdezés.

```java
// AVL fa: minden csúcsban |h(bal) - h(jobb)| <= 1, így a magasság O(log n)
public final class AvlTree<K extends Comparable<K>> {
    private static final class Node<K> {
        K key;
        int height = 1;
        Node<K> left, right;
        Node(K key) { this.key = key; }
    }

    private Node<K> root;

    private static <K> int h(Node<K> n) { return n == null ? 0 : n.height; }
    private static <K> void update(Node<K> n) { n.height = 1 + Math.max(h(n.left), h(n.right)); }
    private static <K> int balance(Node<K> n) { return h(n.left) - h(n.right); }

    // Jobbra forgatás: a bal gyerek lesz az új részfa-gyökér, O(1)
    private static <K> Node<K> rotateRight(Node<K> y) {
        Node<K> x = y.left;
        y.left = x.right;
        x.right = y;
        update(y);  // előbb az alsó csúcs magasságát frissítjük
        update(x);
        return x;
    }

    private static <K> Node<K> rotateLeft(Node<K> x) {
        Node<K> y = x.right;
        x.right = y.left;
        y.left = x;
        update(x);
        update(y);
        return y;
    }

    public void insert(K key) { root = insert(root, key); }

    private Node<K> insert(Node<K> n, K key) {
        if (n == null) return new Node<>(key);
        int c = key.compareTo(n.key);
        if (c < 0) n.left = insert(n.left, key);
        else if (c > 0) n.right = insert(n.right, key);
        else return n;  // duplikátumot nem tárolunk
        update(n);
        int b = balance(n);
        // Négy eset: bal-bal, bal-jobb, jobb-jobb, jobb-bal
        if (b > 1 && key.compareTo(n.left.key) < 0) return rotateRight(n);
        if (b > 1) { n.left = rotateLeft(n.left); return rotateRight(n); }
        if (b < -1 && key.compareTo(n.right.key) > 0) return rotateLeft(n);
        if (b < -1) { n.right = rotateRight(n.right); return rotateLeft(n); }
        return n;
    }

    public boolean contains(K key) {
        Node<K> n = root;
        while (n != null) {
            int c = key.compareTo(n.key);
            if (c == 0) return true;
            n = c < 0 ? n.left : n.right;
        }
        return false;
    }
}
```

## Trie (prefixfa) automatikus kiegészítéshez
<!-- q: Hogyan működik a trie, és mire jó? -->
<!-- tags: trie, prefix tree, autocomplete, radix tree, string search -->

A trie karakterenként ágazó fa: a gyökértől egy út egy prefixnek felel meg, így beszúrás és
keresés O(L) a szó hosszában, függetlenül a tárolt szavak számától. Kiválóan alkalmas
automatikus kiegészítésre, prefix-számlálásra, IP-útválasztásra (bináris trie, longest prefix
match) és szótárellenőrzésre. Buktató: csúcsonként egy Map sok memóriát eszik — nagy
szótárnál tömörített radix-fa (egyágú láncok összevonása), DAWG vagy double-array trie a jobb.

```typescript
// Prefixfa: beszúrás és keresés O(L), ahol L a szó hossza
class TrieNode {
  children = new Map<string, TrieNode>();
  isWord = false;
  count = 0; // hány beszúrt szó halad át ezen a csúcson (prefix-számláláshoz)
}

export class Trie {
  private root = new TrieNode();

  insert(word: string): void {
    let node = this.root;
    for (const ch of word) {
      let next = node.children.get(ch);
      if (!next) {
        next = new TrieNode();
        node.children.set(ch, next);
      }
      next.count++;
      node = next;
    }
    node.isWord = true;
  }

  private find(prefix: string): TrieNode | undefined {
    let node: TrieNode | undefined = this.root;
    for (const ch of prefix) {
      node = node.children.get(ch);
      if (!node) return undefined;
    }
    return node;
  }

  countPrefix(prefix: string): number {
    return this.find(prefix)?.count ?? 0;
  }

  // Kiegészítés: legfeljebb `limit` találat ábécérendben, DFS-sel
  complete(prefix: string, limit = 10): string[] {
    const start = this.find(prefix);
    const out: string[] = [];
    if (!start) return out;
    const dfs = (node: TrieNode, acc: string): void => {
      if (out.length >= limit) return; // korai leállás: nem járjuk be az egész részfát
      if (node.isWord) out.push(acc);
      for (const k of [...node.children.keys()].sort()) {
        dfs(node.children.get(k)!, acc + k);
      }
    };
    dfs(start, prefix);
    return out;
  }
}

const t = new Trie();
["alma", "almafa", "alfa", "beta"].forEach((w) => t.insert(w));
console.log(t.complete("al"), t.countPrefix("alm")); // [ 'alfa', 'alma', 'almafa' ] 2
```

## Szegmensfa és Fenwick-fa
<!-- q: Hogyan kérdezzek le gyorsan intervallum-összeget vagy -minimumot változó tömbön? -->
<!-- tags: segment tree, fenwick tree, binary indexed tree, range query, point update -->

Ha egy tömb elemei változnak és közben intervallum-lekérdezéseket kell kiszolgálni, a naiv
megoldás O(n) lekérdezésenként; a szegmensfa és a Fenwick-fa mindkét műveletet O(log n)-re
viszi. A szegmensfa bármilyen asszociatív műveletre (min, max, összeg, gcd) működik, lusta
propagálással intervallum-frissítést is tud; az iteratív változat 2n méretű tömbben tárolja a
fát. A Fenwick-fa (BIT) egyszerűbb és kisebb, de csak invertálható műveletre (összeg, xor) ad
intervallum-választ, mert prefixek különbségéből számol.

```cpp
#include <algorithm>
#include <limits>
#include <vector>

// Iteratív szegmensfa: pont-frissítés és intervallum-minimum O(log n)
class SegTree {
    int n;
    std::vector<long long> t;  // t[n..2n) a levelek, t[1..n) a belső csúcsok
public:
    explicit SegTree(const std::vector<long long>& a) : n((int)a.size()), t(2 * a.size()) {
        std::copy(a.begin(), a.end(), t.begin() + n);
        for (int i = n - 1; i > 0; --i) t[i] = std::min(t[2 * i], t[2 * i + 1]);
    }
    void update(int pos, long long value) {
        for (t[pos += n] = value; pos > 1; pos >>= 1)
            t[pos >> 1] = std::min(t[pos], t[pos ^ 1]);  // pos ^ 1 a testvércsúcs
    }
    // Minimum a [l, r) félig nyílt intervallumon
    long long query(int l, int r) const {
        long long res = std::numeric_limits<long long>::max();
        for (l += n, r += n; l < r; l >>= 1, r >>= 1) {
            if (l & 1) res = std::min(res, t[l++]);  // bal szél jobb gyerek: bevesszük
            if (r & 1) res = std::min(res, t[--r]);
        }
        return res;
    }
};
```

```python
class Fenwick:
    """Binárisan indexelt fa: prefix összeg és pont-hozzáadás O(log n), 1-től indexelve."""

    def __init__(self, n: int) -> None:
        self.n = n
        self.tree = [0] * (n + 1)

    def add(self, i: int, delta: int) -> None:
        while i <= self.n:
            self.tree[i] += delta
            i += i & -i  # legalsó 1-es bit hozzáadása: a következő felelős csúcs

    def prefix(self, i: int) -> int:
        s = 0
        while i > 0:
            s += self.tree[i]
            i -= i & -i  # legalsó 1-es bit levágása
        return s

    def range_sum(self, l: int, r: int) -> int:
        return self.prefix(r) - self.prefix(l - 1)
```

## Union-Find (diszjunkt halmazok)
<!-- q: Hogyan tartsam nyilván gyorsan, hogy két elem egy komponensben van-e? -->
<!-- tags: union find, disjoint set, dsu, path compression, union by size, connectivity -->

A DSU elemek halmazokra bontását tartja nyilván: Find megadja a halmaz reprezentánsát, Union
összevon két halmazt. Útvonal-tömörítéssel és méret (vagy rang) szerinti egyesítéssel a
műveletek amortizált költsége O(α(n)), ahol α az inverz Ackermann-függvény — gyakorlatilag
konstans. Felhasználás: Kruskal MST, összefüggő komponensek dinamikus gráfban, képszegmentálás,
ekvivalencia-osztályok. Korlát: törlést (halmaz szétvágását) nem támogat; mély rekurzív Find
helyett iteratív kell a veremtúlcsordulás elkerülésére.

```go
package dsu

// DSU útvonal-tömörítéssel és méret szerinti egyesítéssel:
// műveletenként amortizáltan O(α(n)), gyakorlatilag konstans.
type DSU struct {
	parent []int
	size   []int
	Sets   int // komponensek száma
}

func New(n int) *DSU {
	d := &DSU{parent: make([]int, n), size: make([]int, n), Sets: n}
	for i := range d.parent {
		d.parent[i] = i // kezdetben mindenki a saját halmazának gyökere
		d.size[i] = 1
	}
	return d
}

// Find iteratív, kétmenetes útvonal-tömörítéssel (nincs mély rekurzió)
func (d *DSU) Find(x int) int {
	root := x
	for d.parent[root] != root {
		root = d.parent[root]
	}
	for d.parent[x] != root { // második menet: mindenkit közvetlenül a gyökérre kötünk
		next := d.parent[x]
		d.parent[x] = root
		x = next
	}
	return root
}

// Union igazat ad, ha két különböző halmazt vont össze
func (d *DSU) Union(a, b int) bool {
	ra, rb := d.Find(a), d.Find(b)
	if ra == rb {
		return false
	}
	if d.size[ra] < d.size[rb] { // a kisebb fát kötjük a nagyobb alá: sekély fák
		ra, rb = rb, ra
	}
	d.parent[rb] = ra
	d.size[ra] += d.size[rb]
	d.Sets--
	return true
}

func (d *DSU) Connected(a, b int) bool { return d.Find(a) == d.Find(b) }
```

## Gráfbejárás: BFS és DFS
<!-- q: Mikor használjak szélességi és mikor mélységi keresést? -->
<!-- tags: bfs, dfs, graph traversal, shortest path, cycle detection, grid -->

A BFS sorral, rétegenként halad, ezért súlyozatlan gráfban a legrövidebb utat adja; a DFS
veremmel (vagy rekurzióval) a lehető legmélyebbre megy, ami kör-, komponens-, híd- és
topologikus sorrend-kereséshez jó. Mindkettő O(V + E). Buktatók: BFS-nél a csúcsot a sorba
tételkor kell látogatottnak jelölni (különben többször bekerül), a rekurzív DFS nagy gráfon
veremtúlcsordulást okoz (Pythonban ~1000 mélység) — használj explicit vermet. Irányított
gráfban a kört a „szürke” (éppen az úton lévő) csúcsra mutató él jelzi.

```python
from collections import deque

def bfs_grid(grid: list[str], start: tuple[int, int], goal: tuple[int, int]) -> int:
    """Legrövidebb lépésszám rácson ('#' = fal); -1, ha nem elérhető."""
    rows, cols = len(grid), len(grid[0])
    dist = {start: 0}
    q = deque([start])
    while q:
        r, c = q.popleft()
        if (r, c) == goal:
            return dist[(r, c)]
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            # Sorba tételkor jelölünk: így egy csúcs csak egyszer kerül be
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] != "#" and (nr, nc) not in dist:
                dist[(nr, nc)] = dist[(r, c)] + 1
                q.append((nr, nc))
    return -1

def has_cycle(graph: dict[str, list[str]]) -> bool:
    """Irányított kör keresése iteratív DFS-sel, háromszínű jelöléssel."""
    WHITE, GRAY, BLACK = 0, 1, 2  # GRAY = éppen a DFS-úton van
    color = {v: WHITE for v in graph}
    for s in graph:
        if color[s] != WHITE:
            continue
        color[s] = GRAY
        stack = [(s, iter(graph[s]))]  # (csúcs, a még nem vizsgált szomszédok iterátora)
        while stack:
            v, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                color[v] = BLACK  # minden leszármazott kész
                stack.pop()
            elif color.get(nxt, WHITE) == GRAY:
                return True  # visszaél egy úton lévő csúcsra => kör
            elif color.get(nxt, WHITE) == WHITE:
                color[nxt] = GRAY
                stack.append((nxt, iter(graph.get(nxt, []))))
    return False

if __name__ == "__main__":
    maze = ["..#.", "..#.", "....", "#.#."]
    print(bfs_grid(maze, (0, 0), (0, 3)))  # 7
    print(has_cycle({"a": ["b"], "b": ["c"], "c": ["a"]}))  # True
```

## Dijkstra-algoritmus
<!-- q: Hogyan találom meg a legrövidebb utat súlyozott gráfban? -->
<!-- tags: dijkstra, shortest path, priority queue, heapq, weighted graph, routing -->

A Dijkstra mindig a legkisebb ideiglenes távolságú csúcsot véglegesíti, és onnan lazítja a
kimenő éleket; bináris kupaccal O((V + E) log V). Csak nemnegatív élsúlyokkal helyes: egy
negatív él utólag „olcsóbbá” tehetne egy már véglegesített csúcsot. A gyakorlatban a
decrease-key helyett „lusta törlést” használunk: új bejegyzést teszünk a kupacba, és kivételkor
eldobjuk az elavultat. Az útvonalat a `prev` mutatókból fejtjük vissza; egy célhoz elég a cél
kivételekor megállni.

```python
import heapq
from math import inf

def dijkstra(graph: dict[str, list[tuple[str, float]]], src: str):
    """Legrövidebb utak nemnegatív élsúlyokkal. O((V + E) log V)."""
    dist = {src: 0.0}
    prev: dict[str, str] = {}
    pq = [(0.0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, inf):
            continue  # elavult bejegyzés (lusta törlés a decrease-key helyett)
        for v, w in graph.get(u, []):
            if w < 0:
                raise ValueError("negatív él: Bellman-Ford kell")
            nd = d + w
            if nd < dist.get(v, inf):  # lazítás
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    return dist, prev

def path_to(prev: dict[str, str], src: str, dst: str) -> list[str]:
    """Útvonal visszafejtése a prev mutatókból; [] ha nem elérhető."""
    path = [dst]
    while path[-1] != src:
        if path[-1] not in prev:
            return []
        path.append(prev[path[-1]])
    return path[::-1]

if __name__ == "__main__":
    g = {
        "A": [("B", 4), ("C", 1)],
        "C": [("B", 2), ("D", 7)],
        "B": [("D", 1)],
    }
    dist, prev = dijkstra(g, "A")
    print(dist["D"], path_to(prev, "A", "D"))  # 4.0 ['A', 'C', 'B', 'D']
```

## Bellman-Ford és a negatív körök
<!-- q: Hogyan számoljak legrövidebb utat negatív élsúlyokkal, és hogyan ismerem fel a negatív kört? -->
<!-- tags: bellman-ford, negative weights, negative cycle, shortest path, arbitrage -->

A Bellman-Ford V−1 körben az összes élt lazítja; mivel egy egyszerű út legfeljebb V−1 élű, ennyi
kör után minden távolság végleges — O(V·E), lassabb a Dijkstránál, de negatív élekkel is helyes.
Ha a V-edik körben még mindig javítható egy távolság, a forrásból elérhető negatív kör van (ekkor
a „legrövidebb út” nem értelmezett). Alkalmazás: távolságvektor-alapú útválasztás (RIP),
devizaarbitrázs keresése −log(árfolyam) súlyokkal, a Johnson-algoritmus előfeldolgozása.

```python
from math import inf

def bellman_ford(n: int, edges: list[tuple[int, int, float]], src: int) -> list[float]:
    """Legrövidebb utak negatív élekkel is; O(V * E). Negatív körnél kivétel."""
    dist = [inf] * n
    dist[src] = 0.0
    for _ in range(n - 1):  # egy egyszerű út legfeljebb V-1 élű
        changed = False
        for u, v, w in edges:
            if dist[u] != inf and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                changed = True
        if not changed:  # korai kilépés: már stabil
            break
    # Még egy kör: ha még lehet lazítani, elérhető negatív kör van
    for u, v, w in edges:
        if dist[u] != inf and dist[u] + w < dist[v]:
            raise ValueError(f"negatív kör érhető el (él: {u}->{v})")
    return dist

if __name__ == "__main__":
    edges = [(0, 1, 4), (0, 2, 5), (1, 2, -3), (2, 3, 2)]
    print(bellman_ford(4, edges, 0))  # [0.0, 4.0, 1.0, 3.0]
```

## A* keresés heurisztikával
<!-- q: Miben jobb az A* a Dijkstránál útkeresésnél? -->
<!-- tags: a-star, heuristic, pathfinding, admissible, consistent, game ai -->

Az A* a Dijkstra kiterjesztése: a kupacban f = g + h szerint rendez, ahol g az eddigi költség, h
pedig a célig hátralévő becslés, így a keresés a cél felé „húz” és jóval kevesebb csúcsot bont ki.
Ha h elfogadható (sosem becsül túl), az eredmény optimális; ha konzisztens is (h(u) ≤ w(u,v) + h(v)),
minden csúcsot elég egyszer kibontani. Rácson 4 iránynál Manhattan-, 8 iránynál Chebyshev-/oktil
távolság a jó heurisztika; h = 0 esetén visszakapjuk a Dijkstrát. Holtversenynél a nagyobb g-jű
(mélyebb) csúcs előnyben részesítése tovább csökkenti a kibontásokat.

```python
import heapq

def astar(grid: list[str], start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]]:
    """A* 4-irányú rácson, Manhattan-heurisztikával. Üres lista, ha nincs út."""
    def h(p: tuple[int, int]) -> int:
        return abs(p[0] - goal[0]) + abs(p[1] - goal[1])

    rows, cols = len(grid), len(grid[0])
    g = {start: 0}
    came: dict[tuple[int, int], tuple[int, int]] = {}
    open_heap = [(h(start), 0, start)]  # (f, -g, csúcs): holtversenynél a mélyebb nyer
    closed: set[tuple[int, int]] = set()
    while open_heap:
        _, neg_g, cur = heapq.heappop(open_heap)
        if cur == goal:  # útvonal visszafejtése
            path = [cur]
            while cur in came:
                cur = came[cur]
                path.append(cur)
            return path[::-1]
        if cur in closed:
            continue
        closed.add(cur)  # konzisztens h mellett végleges
        r, c = cur
        for nxt in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            nr, nc = nxt
            if not (0 <= nr < rows and 0 <= nc < cols) or grid[nr][nc] == "#":
                continue
            ng = -neg_g + 1
            if ng < g.get(nxt, 1 << 60):
                g[nxt] = ng
                came[nxt] = cur
                heapq.heappush(open_heap, (ng + h(nxt), -ng, nxt))
    return []

if __name__ == "__main__":
    maze = ["....", ".##.", "...."]
    print(astar(maze, (0, 0), (2, 3)))
```

## Topologikus rendezés (Kahn-algoritmus)
<!-- q: Hogyan állítsak fel függőségi sorrendet, és hogyan vegyem észre a körkörös függőséget? -->
<!-- tags: topological sort, kahn algorithm, dag, dependency resolution, build order, cycle -->

Irányított körmentes gráf (DAG) csúcsainak olyan sorrendje, ahol minden él előre mutat — így
számolják a build-rendszerek, csomagkezelők és táblázatkalkulátorok a végrehajtási sorrendet.
A Kahn-algoritmus a 0 befokú csúcsokat veszi ki sorban, és csökkenti a szomszédaik befokát;
O(V + E). Ha a végén maradt fel nem dolgozott csúcs, kör van a gráfban — ezek a hibaüzenetben
megnevezhetők. A DFS-alapú változat a befejezési sorrend megfordítása; a Kahn előnye, hogy
természetesen párhuzamosítható (egy „réteg” 0 befokú csúcsai egyszerre futhatnak).

```typescript
// Kahn-algoritmus: O(V + E). Ha nem kerül minden csúcs a sorrendbe, kör van.
export function topoSort(deps: Record<string, string[]>): string[] {
  // deps[x] = azok a feladatok, amelyeknek x előtt kell lefutniuk
  const indeg = new Map<string, number>();
  const out = new Map<string, string[]>();
  const touch = (n: string): void => {
    if (!indeg.has(n)) indeg.set(n, 0);
    if (!out.has(n)) out.set(n, []);
  };
  for (const [node, reqs] of Object.entries(deps)) {
    touch(node);
    for (const r of reqs) {
      touch(r);
      out.get(r)!.push(node); // él: r -> node
      indeg.set(node, indeg.get(node)! + 1);
    }
  }
  // Determinisztikus kimenet: a kész csúcsokat névsorban vesszük
  const ready = [...indeg].filter(([, d]) => d === 0).map(([n]) => n).sort();
  const order: string[] = [];
  while (ready.length > 0) {
    const n = ready.shift()!; // nagy gráfnál index-mutató vagy kupac kell, a shift O(n)
    order.push(n);
    for (const m of out.get(n)!) {
      const d = indeg.get(m)! - 1;
      indeg.set(m, d);
      if (d === 0) {
        ready.push(m);
        ready.sort();
      }
    }
  }
  if (order.length !== indeg.size) {
    const stuck = [...indeg].filter(([, d]) => d > 0).map(([n]) => n);
    throw new Error(`Körkörös függőség: ${stuck.join(", ")}`);
  }
  return order;
}

console.log(topoSort({ app: ["lib", "utils"], lib: ["utils"], test: ["app"] }));
// [ 'utils', 'lib', 'app', 'test' ]
```

## Minimális feszítőfa: Kruskal és Prim
<!-- q: Hogyan kössem össze az összes csúcsot a lehető legkisebb összköltséggel? -->
<!-- tags: minimum spanning tree, mst, kruskal, prim, cut property, union find -->

A minimális feszítőfa az összes csúcsot körmentesen, minimális élsúly-összeggel köti össze
(hálózattervezés, klaszterezés). Mindkét klasszikus algoritmus a vágás-tulajdonságon alapul: egy
vágáson átmenő legolcsóbb él biztosan benne lehet egy MST-ben. A Kruskal az éleket súly szerint
rendezi és DSU-val dobja el a kört képzőket (O(E log E), ritka gráfra jó); a Prim egy fát
növeszt mindig a legolcsóbb kilépő éllel, kupaccal O(E log V) (sűrű gráfra jobb). Nem
összefüggő gráfnál csak feszítő erdő létezik — ezt ellenőrizni kell.

```python
import heapq

def kruskal(n: int, edges: list[tuple[float, int, int]]) -> tuple[float, list[tuple[int, int]]]:
    """Kruskal: élek súly szerint, DSU-val kerüljük a köröket. O(E log E)."""
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # útvonal-felezés
            x = parent[x]
        return x

    total, used = 0.0, []
    for w, u, v in sorted(edges):
        ru, rv = find(u), find(v)
        if ru != rv:  # két komponenst köt össze: biztonságos él
            parent[ru] = rv
            total += w
            used.append((u, v))
            if len(used) == n - 1:
                break
    return total, used

def prim(adj: list[list[tuple[int, float]]]) -> float:
    """Prim: a fát mindig a legolcsóbb kilépő éllel bővítjük. O(E log V)."""
    seen = [False] * len(adj)
    pq = [(0.0, 0)]
    total = 0.0
    while pq:
        w, u = heapq.heappop(pq)
        if seen[u]:
            continue  # már a fában van: elavult bejegyzés
        seen[u] = True
        total += w
        for v, wv in adj[u]:
            if not seen[v]:
                heapq.heappush(pq, (wv, v))
    if not all(seen):
        raise ValueError("a gráf nem összefüggő")
    return total

if __name__ == "__main__":
    edges = [(1, 0, 1), (4, 0, 2), (2, 1, 2), (6, 1, 3), (3, 2, 3)]
    adj: list[list[tuple[int, float]]] = [[] for _ in range(4)]
    for w, u, v in edges:
        adj[u].append((v, w))
        adj[v].append((u, w))
    print(kruskal(4, edges)[0], prim(adj))  # 6.0 6.0
```

## Maximális folyam (Ford–Fulkerson, Edmonds–Karp)
<!-- q: Hogyan számoljam ki a maximális folyamot egy hálózatban? -->
<!-- tags: max flow, ford-fulkerson, edmonds-karp, min cut, residual graph, bipartite matching -->

A maximális folyam azt adja meg, mennyi „anyag” juthat el a forrásból a nyelőbe az élkapacitások
mellett. A Ford–Fulkerson módszer javítóutakat keres a maradékgráfban, és mindegyiken átküldi a
szűk keresztmetszetnyi folyamot; a visszaélek teszik lehetővé a korábbi döntések
„visszavonását”. Az Edmonds–Karp BFS-sel a legrövidebb javítóutat választja, így O(V·E²); a
Dinic-algoritmus gyorsabb (O(V²·E)). A max-flow min-cut tétel szerint a maximum egyenlő a
legkisebb vágás kapacitásával; alkalmazás: páros gráf párosítás, szegmentálás, ütemezés.

```python
from collections import deque

def max_flow(cap: list[list[int]], s: int, t: int) -> int:
    """Edmonds–Karp szomszédsági mátrixon. O(V * E^2)."""
    n = len(cap)
    residual = [row[:] for row in cap]  # maradékgráf; visszaélek kezdetben 0
    flow = 0
    while True:
        parent = [-1] * n
        parent[s] = s
        q = deque([s])
        while q and parent[t] == -1:  # BFS: legrövidebb javítóút
            u = q.popleft()
            for v in range(n):
                if parent[v] == -1 and residual[u][v] > 0:
                    parent[v] = u
                    q.append(v)
        if parent[t] == -1:
            return flow  # nincs több javítóút: a folyam maximális
        bottleneck, v = float("inf"), t
        while v != s:  # szűk keresztmetszet az út mentén
            bottleneck = min(bottleneck, residual[parent[v]][v])
            v = parent[v]
        v = t
        while v != s:  # előre csökken, visszafelé nő a maradék kapacitás
            u = parent[v]
            residual[u][v] -= bottleneck
            residual[v][u] += bottleneck
            v = u
        flow += int(bottleneck)

if __name__ == "__main__":
    cap = [
        [0, 16, 13, 0, 0, 0],
        [0, 0, 10, 12, 0, 0],
        [0, 4, 0, 0, 14, 0],
        [0, 0, 9, 0, 0, 20],
        [0, 0, 0, 7, 0, 4],
        [0, 0, 0, 0, 0, 0],
    ]
    print(max_flow(cap, 0, 5))  # 23
```

## Dinamikus programozás: 0/1 hátizsák
<!-- q: Hogyan oldjam meg a hátizsák-problémát dinamikus programozással? -->
<!-- tags: dynamic programming, knapsack, memoization, tabulation, pseudo-polynomial -->

A dinamikus programozás akkor működik, ha a feladat átfedő részproblémákra bomlik és az optimális
megoldás részmegoldásokból áll össze (optimális részstruktúra). A 0/1 hátizsáknál dp[i][w] az
első i tárggyal, w kapacitással elérhető legnagyobb érték: vagy kihagyjuk az i-edik tárgyat,
vagy betesszük. O(n·W) idő — ez pszeudo-polinomiális, mert W értékétől és nem a bitszámától függ
(a probléma NP-nehéz). Egy sorra tömörítve a kapacitást visszafelé kell bejárni, különben egy
tárgy többször is bekerülhet (az a korlátlan hátizsák).

```python
def knapsack_01(weights: list[int], values: list[int], cap: int) -> tuple[int, list[int]]:
    """0/1 hátizsák O(n * W)-ben; visszaadja a maximumot és a választott indexeket."""
    n = len(weights)
    # dp[i][w] = legjobb érték az első i tárggyal, w kapacitással
    dp = [[0] * (cap + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        wi, vi = weights[i - 1], values[i - 1]
        for w in range(cap + 1):
            dp[i][w] = dp[i - 1][w]  # i-edik tárgy kihagyása
            if wi <= w and dp[i - 1][w - wi] + vi > dp[i][w]:
                dp[i][w] = dp[i - 1][w - wi] + vi  # i-edik tárgy berakása
    chosen, w = [], cap
    for i in range(n, 0, -1):  # visszafejtés: ahol változott az érték, ott betettük
        if dp[i][w] != dp[i - 1][w]:
            chosen.append(i - 1)
            w -= weights[i - 1]
    return dp[n][cap], chosen[::-1]

def knapsack_01_compact(weights: list[int], values: list[int], cap: int) -> int:
    """Ugyanez O(W) memóriával: a kapacitást VISSZAFELÉ járjuk be."""
    dp = [0] * (cap + 1)
    for wi, vi in zip(weights, values):
        for w in range(cap, wi - 1, -1):  # előrefelé korlátlan hátizsák lenne belőle
            dp[w] = max(dp[w], dp[w - wi] + vi)
    return dp[cap]

if __name__ == "__main__":
    print(knapsack_01([1, 3, 4, 5], [1, 4, 5, 7], 7))  # (9, [1, 2])
    print(knapsack_01_compact([1, 3, 4, 5], [1, 4, 5, 7], 7))  # 9
```

## Dinamikus programozás: LCS és szerkesztési távolság
<!-- q: Hogyan számoljam ki két szöveg leghosszabb közös részsorozatát és Levenshtein-távolságát? -->
<!-- tags: lcs, edit distance, levenshtein, dynamic programming, diff, string similarity -->

Mindkettő kétdimenziós DP a két szöveg prefixein: az LCS-nél egyező karakter esetén átlósan
lépünk +1-gyel, különben a jobb szomszédos részprobléma nyer; a Levenshtein-távolság a törlés,
beszúrás és csere minimumát veszi. Az idő O(n·m); a távolsághoz elég két sor (O(min(n, m))
memória), de a tényleges illesztés visszafejtéséhez a teljes tábla vagy a Hirschberg-féle
oszd-meg-és-uralkodj kell. A diff eszközök (git) a Myers-algoritmust használják, ami O(N·D),
ahol D a különbségek száma — hasonló fájlokon sokkal gyorsabb.

```python
def lcs(a: str, b: str) -> str:
    """Leghosszabb közös részsorozat O(n*m) idővel és memóriával, visszafejtéssel."""
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):  # hátulról töltjük, így elölről fejthető vissza
        for j in range(m - 1, -1, -1):
            if a[i] == b[j]:
                dp[i][j] = dp[i + 1][j + 1] + 1
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j + 1])
    out, i, j = [], 0, 0
    while i < n and j < m:
        if a[i] == b[j]:
            out.append(a[i])
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return "".join(out)

def edit_distance(a: str, b: str) -> int:
    """Levenshtein-távolság két sorral: O(n*m) idő, O(min(n, m)) memória."""
    if len(a) < len(b):
        a, b = b, a  # a rövidebb szöveg adja a sor hosszát
    prev = list(range(len(b) + 1))  # üres prefixből j beszúrással
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(
                prev[j] + 1,  # törlés
                cur[j - 1] + 1,  # beszúrás
                prev[j - 1] + (ca != cb),  # csere (egyezésnél 0 költség)
            )
        prev = cur
    return prev[-1]

if __name__ == "__main__":
    print(lcs("ABCBDAB", "BDCABA"))  # egy 4 hosszú LCS
    print(edit_distance("kitten", "sitting"))  # 3
```

## Mohó algoritmusok és bizonyításuk
<!-- q: Mikor ad optimális eredményt a mohó algoritmus? -->
<!-- tags: greedy, interval scheduling, exchange argument, coin change, matroid -->

A mohó algoritmus minden lépésben a lokálisan legjobbat választja, és sosem vonja vissza —
gyors és egyszerű, de csak akkor optimális, ha a feladatnak mohó-választási tulajdonsága van,
amit általában cserebizonyítással (exchange argument) igazolunk. Klasszikus helyes példák:
intervallum-ütemezés legkorábbi befejezés szerint, Huffman-kódolás, Kruskal/Prim, Dijkstra.
Tipikus csapda a pénzváltás: kanonikus érmerendszerben (1, 2, 5, 10…) a mohó optimális, de
{1, 3, 4} érmékkel 6-ra 4+1+1-et ad 3+3 helyett — ilyenkor DP kell.

```python
def max_non_overlapping(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Intervallum-ütemezés: mindig a legkorábban VÉGZŐT választjuk. O(n log n), optimális."""
    chosen: list[tuple[int, int]] = []
    last_end = float("-inf")
    for start, end in sorted(intervals, key=lambda iv: iv[1]):
        if start >= last_end:  # félig nyílt [start, end): érintkezés megengedett
            chosen.append((start, end))
            last_end = end
    return chosen

def greedy_coins(amount: int, coins: list[int]) -> list[int]:
    """Mohó pénzváltás: csak kanonikus érmerendszerben optimális."""
    out = []
    for c in sorted(coins, reverse=True):
        while amount >= c:
            amount -= c
            out.append(c)
    if amount:
        raise ValueError("nem váltható fel")
    return out

def min_coins_dp(amount: int, coins: list[int]) -> int:
    """Ellenőrzés DP-vel: mindig optimális, O(amount * len(coins))."""
    inf = amount + 1
    dp = [0] + [inf] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a and dp[a - c] + 1 < dp[a]:
                dp[a] = dp[a - c] + 1
    return dp[amount] if dp[amount] != inf else -1

if __name__ == "__main__":
    print(max_non_overlapping([(1, 4), (3, 5), (0, 6), (5, 7), (8, 9), (5, 9)]))
    # [(1, 4), (5, 7), (8, 9)]
    print(greedy_coins(6, [1, 3, 4]), min_coins_dp(6, [1, 3, 4]))  # [4, 1, 1] 2
```

## Visszalépéses keresés (backtracking)
<!-- q: Hogyan írjak visszalépéses keresést, és hogyan gyorsítsam metszéssel? -->
<!-- tags: backtracking, n-queens, combination sum, pruning, recursion, search -->

A backtracking a megoldásteret mélységi kereséssel járja be: választ, rekurzívan továbblép,
majd pontosan visszavonja a választást. Exponenciális, ezért a hatékonyság a metszésen (pruning)
múlik: minél korábban felismerjük, hogy egy ág nem vezethet megoldásra, annál kisebb a fa
(rendezett jelöltek, O(1)-es ütközésvizsgálat halmazokkal, korlátok). Buktató: a közös,
változó állapotot (pl. az aktuális listát) a találatnál másolni kell, különben a későbbi
visszavonások „kiürítik” az eredményt.

```python
def solve_n_queens(n: int) -> list[list[str]]:
    """Soronként egy királynő; halmazokkal O(1) ütközésvizsgálat."""
    cols: set[int] = set()
    diag1: set[int] = set()  # r - c állandó a "\" átlón
    diag2: set[int] = set()  # r + c állandó a "/" átlón
    placement: list[int] = []
    solutions: list[list[str]] = []

    def place(r: int) -> None:
        if r == n:
            solutions.append(["." * c + "Q" + "." * (n - c - 1) for c in placement])
            return
        for c in range(n):
            if c in cols or (r - c) in diag1 or (r + c) in diag2:
                continue  # metszés: ez az ág biztosan zsákutca
            cols.add(c); diag1.add(r - c); diag2.add(r + c); placement.append(c)  # választás
            place(r + 1)
            cols.remove(c); diag1.remove(r - c); diag2.remove(r + c); placement.pop()  # visszavonás

    place(0)
    return solutions

def combination_sum(cands: list[int], target: int) -> list[list[int]]:
    """Az összes (ismétléses) kombináció, aminek összege target."""
    cands = sorted(cands)  # rendezés => korai leállás
    out: list[list[int]] = []
    cur: list[int] = []

    def go(start: int, remaining: int) -> None:
        if remaining == 0:
            out.append(cur.copy())  # másolat! a cur tovább változik
            return
        for i in range(start, len(cands)):
            if cands[i] > remaining:
                break  # rendezett: a többi jelölt is túl nagy
            cur.append(cands[i])
            go(i, remaining - cands[i])  # i, nem i+1: ugyanaz az elem újra választható
            cur.pop()

    go(0, target)
    return out

if __name__ == "__main__":
    print(len(solve_n_queens(8)))  # 92
    print(combination_sum([2, 3, 6, 7], 7))  # [[2, 2, 3], [7]]
```

## Szövegkeresés: KMP és Rabin–Karp
<!-- q: Hogyan keressek mintát szövegben lineáris időben? -->
<!-- tags: string search, kmp, knuth-morris-pratt, rabin-karp, rolling hash, prefix function -->

A naiv keresés O(n·m), mert eltéréskor visszaugrik a szövegben. A KMP előre kiszámolja a minta
prefixfüggvényét (a leghosszabb valódi prefix, ami egyben szuffix is), így eltéréskor a mintában
ugrik vissza, a szövegben soha — garantált O(n + m). A Rabin–Karp gördülő hash-sel O(1)-ben
lépteti az ablakot, átlagosan O(n + m), és könnyen kiterjeszthető több minta egyidejű keresésére;
hash-egyezés után valódi összehasonlítás kell az ütközések miatt. Sok mintára az Aho–Corasick,
gyakorlati egymintás keresésre a Boyer–Moore(–Horspool) a tipikus választás.

```python
def prefix_function(p: str) -> list[int]:
    """pi[i] = p[:i+1] leghosszabb valódi prefixe, ami egyben szuffixe is."""
    pi = [0] * len(p)
    k = 0
    for i in range(1, len(p)):
        while k > 0 and p[i] != p[k]:
            k = pi[k - 1]  # visszaesés a következő jelölt határra
        if p[i] == p[k]:
            k += 1
        pi[i] = k
    return pi

def kmp_search(text: str, p: str) -> list[int]:
    """Az összes (átfedő) előfordulás O(n + m) időben."""
    if not p:
        return list(range(len(text) + 1))
    pi, k, hits = prefix_function(p), 0, []
    for i, ch in enumerate(text):
        while k > 0 and ch != p[k]:
            k = pi[k - 1]
        if ch == p[k]:
            k += 1
        if k == len(p):
            hits.append(i - k + 1)
            k = pi[k - 1]  # folytatás az átfedő találatokért
    return hits

def rabin_karp(text: str, p: str, base: int = 257, mod: int = (1 << 61) - 1) -> list[int]:
    """Gördülő hash: átlagosan O(n + m); ütközésnél karakteres ellenőrzés."""
    n, m = len(text), len(p)
    if m == 0 or m > n:
        return []
    high = pow(base, m - 1, mod)  # a kilépő karakter súlya
    hp = ht = 0
    for i in range(m):
        hp = (hp * base + ord(p[i])) % mod
        ht = (ht * base + ord(text[i])) % mod
    hits = []
    for i in range(n - m + 1):
        if hp == ht and text[i:i + m] == p:  # hash-egyezés után valódi összevetés
            hits.append(i)
        if i + m < n:  # ablak csúsztatása O(1)-ben (Pythonban a % mindig nemnegatív)
            ht = ((ht - ord(text[i]) * high) * base + ord(text[i + m])) % mod
    return hits

if __name__ == "__main__":
    t = "abababcabab"
    assert kmp_search(t, "abab") == rabin_karp(t, "abab") == [0, 2, 7]
```

## Bitmanipulációs trükkök
<!-- q: Milyen hasznos bitműveleti trükkök vannak, és mire jó a bitmaszk-DP? -->
<!-- tags: bit manipulation, bitmask, popcount, power of two, submask, bitmask dp, tsp -->

A bitműveletek egyetlen CPU-utasítással oldanak meg dolgokat, amik egyébként ciklust
igényelnének: `x & (x - 1)` törli a legalsó 1-es bitet (kettő-hatvány teszt), `x & -x`
kiemeli azt (Fenwick-fa), a popcount és a trailing zeros hardveres utasítás. Kis (≤ ~20 elemű)
halmazok bitmaszkként ábrázolhatók, így a részhalmazokon futó DP (pl. utazó ügynök
O(2ⁿ·n²)-ben) tömbindexeléssé válik. Buktatók: C/C++-ban előjeles számon a jobbra léptetés és a
túlcsordulás implementációfüggő/UB — használj előjel nélküli típust; az XOR-csere olvashatatlan
és nem gyorsabb.

```rust
// Gyakori bittrükkök; a beépített metódusok egy-egy CPU-utasításra fordulnak
fn is_power_of_two(x: u64) -> bool {
    x != 0 && (x & (x - 1)) == 0 // x & (x-1) törli a legalsó 1-es bitet
}

fn lowest_set_bit(x: u64) -> u64 {
    x & x.wrapping_neg() // kettes komplemens: -x = !x + 1
}

/// Egy maszk összes nemüres részmaszkja csökkenő sorrendben
fn submasks(mask: u32) -> Vec<u32> {
    let mut out = Vec::new();
    let mut s = mask;
    while s != 0 {
        out.push(s);
        s = (s - 1) & mask; // a következő kisebb részmaszk
    }
    out
}

/// Bitmaszk-DP: utazó ügynök n <= ~20 városra, O(2^n * n^2)
fn tsp(dist: &[Vec<u32>]) -> u32 {
    let n = dist.len();
    let full = 1usize << n;
    let mut dp = vec![vec![u32::MAX; n]; full]; // dp[S][v]: S bejárva, v-ben állunk
    dp[1][0] = 0;
    for s in 1..full {
        if s & 1 == 0 {
            continue; // mindig a 0. városból indulunk
        }
        for v in 0..n {
            if dp[s][v] == u32::MAX || s & (1 << v) == 0 {
                continue;
            }
            for u in 0..n {
                if s & (1 << u) != 0 {
                    continue; // u már szerepel az úton
                }
                let ns = s | (1 << u);
                let cand = dp[s][v] + dist[v][u];
                if cand < dp[ns][u] {
                    dp[ns][u] = cand;
                }
            }
        }
    }
    (1..n).map(|v| dp[full - 1][v].saturating_add(dist[v][0])).min().unwrap_or(0)
}

fn main() {
    assert!(is_power_of_two(64) && !is_power_of_two(96));
    assert_eq!(lowest_set_bit(0b1011_0000), 0b1_0000);
    assert_eq!(0b1011u32.count_ones(), 3); // popcount
    assert_eq!(40u32.trailing_zeros(), 3); // 40 = 0b101000
    println!("{:?}", submasks(0b101)); // [5, 4, 1]
    let d = vec![vec![0, 10, 15, 20], vec![10, 0, 35, 25], vec![15, 35, 0, 30], vec![20, 25, 30, 0]];
    println!("{}", tsp(&d)); // 80
}
```

## LRU gyorsítótár O(1) műveletekkel
<!-- q: Hogyan implementáljak LRU cache-t O(1) get és put művelettel? -->
<!-- tags: lru cache, hash map, doubly linked list, eviction, caching, sentinel -->

Az LRU (least recently used) cache telítettségnél a legrégebben használt elemet dobja ki. O(1)
műveletekhez két szerkezet kell együtt: hash map a kulcs → csúcs kereséshez, és kétirányú
láncolt lista a használati sorrendhez (elején a legfrissebb, végén a kidobandó). Egy őrszem
(sentinel) csúcs körkörös listában megszünteti a None-ellenőrzéseket a széleken. A gyakorlatban
kész eszköz van rá (Python `functools.lru_cache`, `OrderedDict.move_to_end`, Java
`LinkedHashMap` access-order móddal); többszálú használathoz zár vagy szegmentált cache kell, a
Redis pedig mintavételezéssel közelíti az LRU-t.

```python
from typing import Generic, Hashable, Optional, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")

class _Node(Generic[K, V]):
    __slots__ = ("key", "val", "prev", "next")

    def __init__(self, key: Optional[K] = None, val: Optional[V] = None) -> None:
        self.key, self.val = key, val
        self.prev: "_Node[K, V]" = self  # körkörös lista: önmagára mutat
        self.next: "_Node[K, V]" = self

class LRUCache(Generic[K, V]):
    """Hash map + körkörös kétirányú lista: get és put O(1)."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("a kapacitásnak pozitívnak kell lennie")
        self.cap = capacity
        self.map: dict[K, _Node[K, V]] = {}
        self.head: _Node[K, V] = _Node()  # őrszem: head.next a legfrissebb, head.prev a legrégebbi

    def _unlink(self, n: _Node[K, V]) -> None:
        n.prev.next, n.next.prev = n.next, n.prev

    def _push_front(self, n: _Node[K, V]) -> None:
        n.prev, n.next = self.head, self.head.next
        self.head.next.prev = n
        self.head.next = n

    def get(self, key: K) -> Optional[V]:
        n = self.map.get(key)
        if n is None:
            return None
        self._unlink(n)  # használat => a lista elejére kerül
        self._push_front(n)
        return n.val

    def put(self, key: K, val: V) -> None:
        n = self.map.get(key)
        if n is not None:
            n.val = val
            self._unlink(n)
            self._push_front(n)
            return
        if len(self.map) >= self.cap:
            lru = self.head.prev  # a legrégebben használt elem
            self._unlink(lru)
            del self.map[lru.key]
        n = _Node(key, val)
        self.map[key] = n
        self._push_front(n)

if __name__ == "__main__":
    c: LRUCache[str, int] = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")
    c.put("c", 3)  # "b" a legrégebbi, ő esik ki
    assert c.get("b") is None and c.get("a") == 1
```
