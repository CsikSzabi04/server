# Adatbázis-belsők
<!-- tech: database-internals -->
<!-- aliases: database internals, storage engine, adatbázismotor, b+tree, lsm-tree, wal, mvcc, query planner, postgres internals -->

Egy adatbázismotor rétegekből áll: tárolómotor (lapok, B+fa vagy LSM-fa), buffer pool (lap-cache), napló (WAL) a tartósságért és összeomlás utáni helyreállításért, konkurenciakezelés (zárak, MVCC), valamint a lekérdezés-feldolgozó (parser, tervező költségmodellel, végrehajtó join-algoritmusokkal). Ezek ismerete magyarázza meg a gyakorlati jelenségeket: miért lassú egy index nélküli join, miért nő a tábla UPDATE-ek után (bloat), miért kell VACUUM, mikor jobb egy LSM-alapú motor írásintenzív terhelésre, és miért ad a Postgres „could not serialize access” hibát. A példák egyszerűsített Python-modellek és valódi SQL.

## B+fa: lapok, keresés, beszúrás, lapfelosztás
<!-- q: Hogyan működik a B+fa index belül, és miért ezt használják az adatbázisok? -->
<!-- tags: b+tree, btree, page split, index, range scan, fanout, storage engine -->

A B+fa minden csomópontja egy lemezlap (Postgres: 8 KB, InnoDB: 16 KB), így a nagy elágazási tényező (fanout, több száz kulcs/lap) miatt milliárd sor is 3–4 szinttel elérhető: egy keresés ≈ 3–4 lapolvasás, a felső szintek pedig mindig a cache-ben vannak. Az értékek (vagy sor-mutatók) csak a levelekben vannak, a levelek láncolva, ezért a tartomány-lekérdezés (`BETWEEN`, `ORDER BY`) egy leszállás után szekvenciális. Beszúráskor a betelt lap kettéhasad, a szétválasztó kulcs a szülőbe kerül, és ha a gyökér hasad, a fa egy szinttel nő — ezért mindig kiegyensúlyozott. Buktató: véletlenszerű kulcs (UUIDv4) beszúrása szétszórt lapfelosztásokat és rossz cache-kihasználtságot okoz; monoton kulcs (bigserial, UUIDv7) jobb.

```python
import bisect

class Leaf:
    def __init__(self):
        self.keys, self.vals, self.next = [], [], None   # next: jobb szomszéd (range scan)

class Inner:
    def __init__(self, keys, children):
        self.keys, self.children = keys, children        # len(children) == len(keys) + 1

class BPlusTree:
    def __init__(self, order=4):
        self.order, self.root = order, Leaf()            # order: max kulcs/lap (valóságban ~több száz)

    def _find_leaf(self, key, path=None):
        node = self.root
        while isinstance(node, Inner):
            if path is not None: path.append(node)       # az útvonal kell a felosztáshoz
            node = node.children[bisect.bisect_right(node.keys, key)]
        return node

    def get(self, key):
        leaf = self._find_leaf(key)
        i = bisect.bisect_left(leaf.keys, key)
        return leaf.vals[i] if i < len(leaf.keys) and leaf.keys[i] == key else None

    def range(self, lo, hi):
        leaf = self._find_leaf(lo)
        while leaf:                                       # levéllánc: nincs újabb leszállás
            for k, v in zip(leaf.keys, leaf.vals):
                if k > hi: return
                if k >= lo: yield k, v
            leaf = leaf.next

    def insert(self, key, val):
        path = []
        leaf = self._find_leaf(key, path)
        i = bisect.bisect_left(leaf.keys, key)
        if i < len(leaf.keys) and leaf.keys[i] == key:
            leaf.vals[i] = val; return                    # upsert
        leaf.keys.insert(i, key); leaf.vals.insert(i, val)
        if len(leaf.keys) <= self.order: return
        mid = len(leaf.keys) // 2                         # levél hasad: a jobb fél első kulcsa
        right = Leaf()                                    # FELMÁSOLÓDIK a szülőbe
        right.keys, right.vals = leaf.keys[mid:], leaf.vals[mid:]
        leaf.keys, leaf.vals = leaf.keys[:mid], leaf.vals[:mid]
        right.next, leaf.next = leaf.next, right
        self._insert_into_parent(path, leaf, right.keys[0], right)

    def _insert_into_parent(self, path, left, key, right):
        if not path:                                      # a gyökér hasadt: a fa egy szinttel nő
            self.root = Inner([key], [left, right]); return
        parent = path.pop()
        i = bisect.bisect_right(parent.keys, key)
        parent.keys.insert(i, key); parent.children.insert(i + 1, right)
        if len(parent.keys) <= self.order: return
        mid = len(parent.keys) // 2                       # belső csomópont hasad: a középső
        up = parent.keys[mid]                             # kulcs FELKERÜL (nem marad lent)
        sibling = Inner(parent.keys[mid + 1:], parent.children[mid + 1:])
        parent.keys, parent.children = parent.keys[:mid], parent.children[:mid + 1]
        self._insert_into_parent(path, parent, up, sibling)

tree = BPlusTree(order=3)
for k in [15, 3, 42, 8, 23, 4, 16, 99, 1, 50]:
    tree.insert(k, f"row-{k}")
print(tree.get(23), list(tree.range(4, 23)))
```

## LSM-fa: memtable, SSTable, bloom filter, compaction
<!-- q: Hogyan működik az LSM-fa, és mikor jobb a B+fánál? -->
<!-- tags: lsm tree, memtable, sstable, compaction, bloom filter, tombstone, write amplification, rocksdb -->

Az LSM-fa (RocksDB, Cassandra, ScyllaDB, LevelDB) az írásokat egy memóriabeli rendezett táblába (*memtable*) gyűjti, ami betelve immutábilis, rendezett fájlként (*SSTable*) kerül lemezre — így minden írás szekvenciális, ezért nagyon gyors. Olvasáskor a legújabbtól a legrégebbi felé kell nézni; a felesleges fájlolvasást *bloom filter* spórolja meg („biztosan nincs benne”). A törlés *tombstone* bejegyzés, a régi verziókat a háttérben futó *compaction* fésüli össze. Összevetés: a B+fa olvasásra és kiszámítható késleltetésre jobb, az LSM írásra és tömörítésre; az LSM ára a write amplification (compaction újraírja az adatot) és a compaction okozta késleltetési tüskék.

```python
import bisect
import hashlib

class Bloom:
    """Valószínűségi halmaz: 'biztosan nincs' vagy 'talán van'."""
    def __init__(self, bits=1024, k=3):
        self.bits, self.k, self.arr = bits, k, 0
    def _hashes(self, key):
        h = hashlib.blake2b(key.encode(), digest_size=16).digest()
        a, b = int.from_bytes(h[:8], "little"), int.from_bytes(h[8:], "little")
        return [(a + i * b) % self.bits for i in range(self.k)]   # double hashing
    def add(self, key):
        for i in self._hashes(key): self.arr |= 1 << i
    def may_contain(self, key):
        return all(self.arr >> i & 1 for i in self._hashes(key))

TOMBSTONE = object()                        # törlés = különleges érték, nem tényleges törlés

class SSTable:
    """Immutábilis, rendezett „fájl”: kulcsok + értékek + bloom filter."""
    def __init__(self, items):
        self.keys = [k for k, _ in items]
        self.vals = [v for _, v in items]
        self.bloom = Bloom()
        for k in self.keys: self.bloom.add(k)
    def get(self, key):
        if not self.bloom.may_contain(key): return None   # lemezolvasás megspórolva
        i = bisect.bisect_left(self.keys, key)
        return self.vals[i] if i < len(self.keys) and self.keys[i] == key else None

class LSMTree:
    def __init__(self, memtable_limit=4, max_tables=3):
        self.mem, self.limit, self.max_tables, self.tables = {}, memtable_limit, max_tables, []
    def put(self, key, val):
        self.mem[key] = val                 # valóságban ELŐBB a WAL-ba írunk!
        if len(self.mem) >= self.limit: self.flush()
    def delete(self, key):
        self.put(key, TOMBSTONE)
    def flush(self):
        self.tables.insert(0, SSTable(sorted(self.mem.items())))  # tables[0] = legújabb
        self.mem = {}
        if len(self.tables) > self.max_tables: self.compact()
    def get(self, key):
        for source in [self.mem, *self.tables]:          # legújabbtól a legrégebbiig
            v = source.get(key)
            if v is not None:
                return None if v is TOMBSTONE else v
        return None
    def compact(self):
        merged = {}
        for table in reversed(self.tables):              # régiből az újba: az újabb felülír
            merged.update(zip(table.keys, table.vals))
        # tombstone csak akkor dobható el, ha nincs alattuk régebbi szint (itt: teljes merge)
        self.tables = [SSTable(sorted((k, v) for k, v in merged.items() if v is not TOMBSTONE))]

db = LSMTree()
for i in range(20):
    db.put(f"user:{i:03}", {"id": i})
db.delete("user:007")
print(db.get("user:005"), db.get("user:007"), len(db.tables))
```

## Write-ahead log (WAL)
<!-- q: Mi a write-ahead log és hogyan biztosítja a tartósságot? -->
<!-- tags: wal, write ahead log, durability, fsync, crc, lsn, torn write, group commit -->

A WAL szabály: minden módosítást előbb a naplóba kell írni és `fsync`-kel lemezre kényszeríteni, csak utána módosulhat az adatlap — így a commit egyetlen szekvenciális írás, a véletlen hozzáférésű lapírások ráérnek később (checkpoint). Minden rekord kap egy monoton *LSN*-t (log sequence number), hosszt és ellenőrzőösszeget, így induláskor a félig kiírt (torn) utolsó rekord felismerhető és levágható. Az `fsync` drága (ms nagyságrend), ezért a motorok *group commit*-ot használnak: több tranzakció rekordját egyetlen fsync-kel teszik tartóssá. Buktató: `flush()` önmagában csak az OS cache-be ír, és néhány lemez/vezérlő hazudik az fsync-ről (írási cache akkumulátor nélkül).

```python
import json
import os
import struct
import zlib

HEADER = struct.Struct("<QII")               # LSN (8 bájt), hossz (4), CRC32 (4)

class WAL:
    def __init__(self, path):
        self.path = path
        open(path, "ab").close()
        valid_end, last_lsn = 0, 0
        for lsn, _, end in self._scan():
            valid_end, last_lsn = end, lsn
        with open(path, "r+b") as f:
            f.truncate(valid_end)             # torn tail levágása, különben szemét után írnánk
        self.f = open(path, "ab")
        self.next_lsn = last_lsn + 1

    def append(self, record: dict, sync=True) -> int:
        payload = json.dumps(record).encode()
        lsn = self.next_lsn
        self.f.write(HEADER.pack(lsn, len(payload), zlib.crc32(payload)) + payload)
        if sync:
            self.f.flush()                    # Python buffer -> OS
            os.fsync(self.f.fileno())         # OS cache -> lemez: EZ a commit pont
        self.next_lsn += 1
        return lsn

    def _scan(self):
        with open(self.path, "rb") as f:
            while True:
                head = f.read(HEADER.size)
                if len(head) < HEADER.size: return
                lsn, length, crc = HEADER.unpack(head)
                payload = f.read(length)
                if len(payload) < length or zlib.crc32(payload) != crc:
                    return                    # összeomlás közben félbeszakadt írás
                yield lsn, json.loads(payload), f.tell()

    def replay(self):
        return [(lsn, rec) for lsn, rec, _ in self._scan()]

class KVStore:
    """A memóriabeli állapot bármikor újraépíthető a naplóból."""
    def __init__(self, wal_path):
        self.wal, self.data = WAL(wal_path), {}
        for _, rec in self.wal.replay():
            self._apply(rec)
    def _apply(self, rec):
        if rec["op"] == "set": self.data[rec["k"]] = rec["v"]
        else: self.data.pop(rec["k"], None)
    def set(self, k, v):
        rec = {"op": "set", "k": k, "v": v}
        self.wal.append(rec)                  # 1) napló + fsync
        self._apply(rec)                      # 2) csak utána az állapot

store = KVStore("demo.wal")
store.set("balance:1", 100)
print(KVStore("demo.wal").data)               # "újraindítás" után is megvan
```

## Összeomlás utáni helyreállítás (ARIES)
<!-- q: Hogyan áll helyre egy adatbázis összeomlás után a napló alapján? -->
<!-- tags: crash recovery, aries, redo, undo, checkpoint, steal no force, clr, page lsn -->

Az ARIES algoritmus (DB2, SQL Server, és elveiben a legtöbb motor) három fázisban állít helyre: *analysis* (melyik tranzakció volt aktív az összeomláskor), *redo* („repeating history”: minden naplózott változást újrajátszik, ha a lap `pageLSN`-je szerint még hiányzik), *undo* (a nem commitolt „loser” tranzakciókat visszafelé visszavonja). Ez teszi lehetővé a *steal/no-force* politikát: nem commitolt lap is kiírható (steal), és commitkor nem kell a lapot kiírni (no-force) — csak a naplót. Az undo közben *CLR* (compensation log record) készül, hogy egy újabb összeomlás esetén se kelljen semmit kétszer visszavonni. A checkpoint korlátozza, honnan kell a naplót olvasni.

```python
# Naplórekord: (lsn, txn, típus, lap, régi_érték, új_érték)
log = [
    (1, "T1", "update", "A", 10, 20),
    (2, "T2", "update", "B", 5, 7),
    (3, "T1", "commit", None, None, None),
    (4, "T2", "update", "A", 20, 30),
    (5, "T3", "update", "C", 0, 1),
    (6, "T3", "commit", None, None, None),
]   # <-- itt összeomlás: T2 nem commitolt
# Lemezállapot az összeomláskor: lap -> (érték, page_lsn). Az A lap LSN=1 állapotban íródott ki.
disk = {"A": (20, 1), "B": (5, 0), "C": (0, 0)}

def recover(log, disk):
    pages = dict(disk)
    # 1) ANALYSIS: commit nélküli tranzakciók = loser-ek
    active = set()
    for lsn, txn, kind, *_ in log:
        if kind == "commit": active.discard(txn)
        else: active.add(txn)
    losers = active
    # 2) REDO: minden update újrajátszása, ha a lap még nem tartalmazza (pageLSN < lsn)
    for lsn, txn, kind, page, old, new in log:
        if kind == "update" and pages[page][1] < lsn:
            pages[page] = (new, lsn)
    # 3) UNDO: loser-ek változásai visszafelé, minden lépésről CLR rekord
    next_lsn = log[-1][0]
    for lsn, txn, kind, page, old, new in list(reversed(log)):
        if kind == "update" and txn in losers:
            next_lsn += 1
            log.append((next_lsn, txn, "clr", page, new, old))   # a CLR-t sosem kell undo-zni
            pages[page] = (old, next_lsn)
    for txn in sorted(losers):
        next_lsn += 1
        log.append((next_lsn, txn, "abort", None, None, None))
    return pages

print(recover(log, disk))   # A=20 (T1), B=5 (T2 visszavonva), C=1 (T3 redo)
```

## Buffer pool és lapcsere (CLOCK)
<!-- q: Hogyan működik az adatbázis buffer pool és a lapcsere algoritmus? -->
<!-- tags: buffer pool, page cache, clock, lru, pin, dirty page, eviction, shared buffers -->

A buffer pool a lemezlapok memóriabeli cache-e fix méretű keretekben (frame); a motor minden lapot ezen keresztül ér el, *pin*-nel jelezve, hogy épp használja (pinelt lap nem dobható ki). Ha a lap módosult (*dirty*), kidobás előtt vissza kell írni — de csak miután a WAL már tartós az adott lap LSN-jéig. Tiszta LRU helyett a CLOCK (második esély) olcsóbb: körbejáró mutató, a „nemrég használt” bit törlése, és az első bit nélküli, nem pinelt lap a vesztes. Buktató: egy nagy szekvenciális scan kiöblítheti a forró lapokat — ezért a Postgres ilyenkor kis gyűrűpuffert használ, az InnoDB pedig „régi/új” részre osztott LRU-t.

```python
class Frame:
    __slots__ = ("page_id", "data", "dirty", "pins", "ref")
    def __init__(self, page_id, data):
        self.page_id, self.data, self.dirty, self.pins, self.ref = page_id, data, False, 0, True

class FakeDisk:
    def __init__(self): self.pages, self.reads, self.writes = {}, 0, 0
    def read(self, pid):
        self.reads += 1; return self.pages.get(pid, bytes(8192))
    def write(self, pid, data):
        self.writes += 1; self.pages[pid] = data

class BufferPool:
    def __init__(self, disk, capacity):
        self.disk, self.frames, self.table, self.hand = disk, [None] * capacity, {}, 0

    def fetch(self, page_id) -> Frame:
        if page_id in self.table:                     # cache hit
            frame = self.frames[self.table[page_id]]
        else:                                         # cache miss: hely kell
            slot = self._victim()
            frame = Frame(page_id, bytearray(self.disk.read(page_id)))
            self.frames[slot], self.table[page_id] = frame, slot
        frame.pins += 1
        frame.ref = True
        return frame

    def unpin(self, frame, dirty=False):
        frame.pins -= 1
        frame.dirty |= dirty

    def _victim(self) -> int:
        for _ in range(2 * len(self.frames)):         # CLOCK: legfeljebb két kör
            slot = self.hand
            self.hand = (self.hand + 1) % len(self.frames)
            f = self.frames[slot]
            if f is None: return slot
            if f.pins: continue                       # használatban: nem dobható
            if f.ref:
                f.ref = False; continue               # második esély
            if f.dirty:
                self.disk.write(f.page_id, bytes(f.data))  # write-back (WAL előbb tartós!)
            del self.table[f.page_id]
            return slot
        raise RuntimeError("minden keret pinelve: a buffer pool kimerült")

disk = FakeDisk()
pool = BufferPool(disk, capacity=3)
for pid in [1, 2, 3, 1, 4, 1, 5, 2]:
    page = pool.fetch(pid)
    page.data[0] = pid                                # módosítás a memóriában
    pool.unpin(page, dirty=True)
print("lemezolvasás:", disk.reads, "lemezírás:", disk.writes)
```

## MVCC: verziók és láthatóság
<!-- q: Hogyan működik az MVCC (többverziós konkurenciakezelés) belül? -->
<!-- tags: mvcc, snapshot, xmin, xmax, visibility, postgres, concurrency control, versions -->

MVCC-ben az írás nem írja felül a sort, hanem új *verziót* hoz létre; minden tranzakció egy *snapshotot* lát (mely tranzakciók voltak commitolva a kezdetekor), így az olvasók sosem blokkolják az írókat és fordítva. A Postgres minden sorverzióba beírja a létrehozó (`xmin`) és a törlő/felülíró (`xmax`) tranzakció azonosítóját; egy verzió látható, ha `xmin` commitolt a snapshot szerint, `xmax` pedig nem. Két egyidejű író esetén „first updater wins”: a második hibát kap (Repeatable Read-ben) vagy újraolvas (Read Committed-ben). Az ára a régi verziók felhalmozódása (bloat), amit a VACUUM takarít — az InnoDB ezzel szemben helyben ír, és az undo logból rakja össze a régi verziót.

```python
import itertools
from dataclasses import dataclass

@dataclass
class Version:
    value: object
    xmin: int                      # létrehozó tranzakció
    xmax: int | None = None        # törlő/felülíró tranzakció

class MVCCStore:
    def __init__(self):
        self.rows, self.txids = {}, itertools.count(1)
        self.active, self.committed = set(), set()

    def begin(self):
        xid = next(self.txids)
        snap = {"xid": xid, "active": frozenset(self.active)}   # a még futók munkája láthatatlan
        self.active.add(xid)
        return snap

    def _done_for(self, x, snap):  # x hatása látszik-e a snapshotban?
        return x == snap["xid"] or (x in self.committed and x < snap["xid"] and x not in snap["active"])

    def _visible(self, v, snap):
        return self._done_for(v.xmin, snap) and (v.xmax is None or not self._done_for(v.xmax, snap))

    def read(self, snap, key):
        return next((v.value for v in reversed(self.rows.get(key, [])) if self._visible(v, snap)), None)

    def write(self, snap, key, value):
        versions = self.rows.setdefault(key, [])
        if versions:
            last = versions[-1]
            # first-updater-wins: a legfrissebb verziót más módosította a snapshotunk óta
            if not self._visible(last, snap) or (last.xmax not in (None, snap["xid"])):
                raise RuntimeError("could not serialize access due to concurrent update")
            last.xmax = snap["xid"]                  # a régi verziót lezárjuk
        versions.append(Version(value, snap["xid"]))  # és újat hozunk létre

    def commit(self, snap):
        self.active.discard(snap["xid"]); self.committed.add(snap["xid"])

    def abort(self, snap):
        self.active.discard(snap["xid"])
        for versions in self.rows.values():          # egyszerűsítés: azonnali takarítás
            versions[:] = [v for v in versions if v.xmin != snap["xid"]]
            for v in versions:
                if v.xmax == snap["xid"]: v.xmax = None

db = MVCCStore()
t0 = db.begin(); db.write(t0, "x", 1); db.commit(t0)
t1, t2 = db.begin(), db.begin()
db.write(t2, "x", 2); db.commit(t2)
print(db.read(t1, "x"))          # 1 — t1 snapshotja még a régi verziót látja
print(db.read(db.begin(), "x"))  # 2 — új tranzakció már az újat
try:
    db.write(t1, "x", 10)        # lost update helyett hiba
except RuntimeError as e:
    db.abort(t1); print(e)
```

## Izolációs szintek megvalósítása
<!-- q: Hogyan valósítják meg az adatbázisok az izolációs szinteket, és milyen anomáliák maradnak? -->
<!-- tags: isolation levels, read committed, repeatable read, serializable, ssi, write skew, lost update, 2pl, locking -->

Postgresben a Read Committed minden *utasítás* elején új snapshotot vesz, a Repeatable Read egyet a *tranzakció* elején, a Serializable pedig Repeatable Read + SSI (Serializable Snapshot Isolation), ami a tranzakciók közti olvasás-írás függőségeket figyeli, és veszélyes mintánál az egyiket megszakítja. A MySQL InnoDB Serializable-je ezzel szemben zárakkal (2PL, gap lock) dolgozik, ami blokkolást és holtpontot okozhat. A snapshot isolation nem véd a *write skew* ellen: két tranzakció ugyanazt a feltételt olvassa, majd *különböző* sorokat ír. Gyakorlati szabály: Serializable-nél az alkalmazásnak újra kell próbálnia a `40001` hibát kapott tranzakciót, alacsonyabb szinten pedig `SELECT ... FOR UPDATE`-tel vagy atomi `UPDATE`-tel kell zárolni.

```sql
-- Write skew: legalább egy orvosnak ügyeletben kell maradnia.
CREATE TABLE oncall (doctor text PRIMARY KEY, on_duty boolean NOT NULL);
INSERT INTO oncall VALUES ('A', true), ('B', true);

-- Két párhuzamos munkamenet (S1, S2) időrendben:
/* S1 */ BEGIN ISOLATION LEVEL REPEATABLE READ;
/* S2 */ BEGIN ISOLATION LEVEL REPEATABLE READ;
/* S1 */ SELECT count(*) FROM oncall WHERE on_duty;      -- 2, tehát "mehetek"
/* S2 */ SELECT count(*) FROM oncall WHERE on_duty;      -- 2, tehát "mehetek"
/* S1 */ UPDATE oncall SET on_duty = false WHERE doctor = 'A';
/* S2 */ UPDATE oncall SET on_duty = false WHERE doctor = 'B';   -- más sor: nincs ütközés
/* S1 */ COMMIT;
/* S2 */ COMMIT;                                         -- OK => senki sincs ügyeletben!

-- Megoldás 1: SERIALIZABLE (SSI) — az egyik COMMIT ezt kapja, és újra kell próbálni:
--   ERROR: could not serialize access due to read/write dependencies among transactions (40001)
BEGIN ISOLATION LEVEL SERIALIZABLE;

-- Megoldás 2: a döntés alapjául szolgáló sorok explicit zárolása (a második vár az elsőre)
BEGIN;
SELECT doctor FROM oncall WHERE on_duty FOR UPDATE;
UPDATE oncall SET on_duty = false WHERE doctor = 'A';
COMMIT;

-- Lost update elkerülése Read Committed-ben: atomi UPDATE olvasás-módosítás-írás helyett
UPDATE accounts SET balance = balance - 100 WHERE id = 1 AND balance >= 100;
-- Rossz minta: SELECT balance ...; (alkalmazásban kivonás) UPDATE ... SET balance = <új érték>;

-- Holtpont: két tranzakció fordított sorrendben zárol; a motor észleli (wait-for gráf ciklus)
-- és az egyiket megszakítja. Ellenszer: mindig azonos sorrendben zárolj (pl. id szerint).
SELECT * FROM accounts WHERE id IN (1, 2) ORDER BY id FOR UPDATE;
```

## Lekérdezés-tervező és költségmodell
<!-- q: Hogyan dönti el a query planner, melyik végrehajtási tervet használja? -->
<!-- tags: query planner, optimizer, cost model, explain analyze, statistics, selectivity, cardinality estimation -->

A tervező a lekérdezés lehetséges végrehajtási terveit (scan-típus, join-sorrend, join-algoritmus) egy *költségmodell* alapján hasonlítja össze; a költség becsült lap-I/O és CPU-munka, ami a táblastatisztikákból (sorszám, hisztogram, leggyakoribb értékek, NULL-arány, korreláció) számolt *szelektivitáson* múlik. A legtöbb rossz terv rossz kardinalitás-becslésből fakad: elavult statisztika (`ANALYZE`), korrelált oszlopok (a tervező függetlennek tekinti őket), vagy függvénybe csomagolt oszlop. Mindig `EXPLAIN (ANALYZE, BUFFERS)`-szel nézd meg a becsült (`rows=`) és a tényleges sorszámot — a nagyságrendi eltérés a hiba helye. Kis kimenetnél az index scan nyer, nagynál a szekvenciális olvasás, mert a véletlen lapolvasás drágább.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT o.id, c.name FROM orders o JOIN customers c ON c.id = o.customer_id
WHERE o.status = 'shipped' AND o.created_at > now() - interval '7 days';
-- Hash Join  (cost=..  rows=120) (actual rows=48210)   <-- 400x alulbecslés: itt a gond!
--   -> Index Scan using orders_created_at_idx on orders o (... rows=120) (actual rows=48210)
--   -> Hash -> Seq Scan on customers c

ANALYZE orders;                                              -- friss statisztika
CREATE STATISTICS orders_status_date (dependencies, mcv)     -- korrelált oszlopok
    ON status, created_at FROM orders;
ALTER TABLE orders ALTER COLUMN status SET STATISTICS 1000;  -- részletesebb hisztogram
SELECT attname, n_distinct, most_common_vals FROM pg_stats WHERE tablename = 'orders';
```

```python
# A Postgres költségképletének egyszerűsített modellje: mikor éri meg az index?
SEQ_PAGE, RANDOM_PAGE, CPU_TUPLE, CPU_INDEX = 1.0, 4.0, 0.01, 0.005   # alapértelmezések

def seq_scan_cost(pages, rows):
    return pages * SEQ_PAGE + rows * CPU_TUPLE

def index_scan_cost(rows, selectivity, correlation=0.0):
    matched = rows * selectivity
    # korrelálatlan tábla: minden találat potenciálisan külön véletlen lapolvasás
    heap_pages = matched * (1 - correlation ** 2) + 1
    return heap_pages * RANDOM_PAGE + matched * (CPU_TUPLE + CPU_INDEX)

pages, rows = 10_000, 1_000_000
for sel in (0.0001, 0.001, 0.01, 0.05):
    seq, idx = seq_scan_cost(pages, rows), index_scan_cost(rows, sel)
    print(f"szelektivitás {sel:>7}: seq={seq:9.0f} index={idx:9.0f} -> {'INDEX' if idx < seq else 'SEQ'}")
```

## Join algoritmusok: nested loop, hash join, merge join
<!-- q: Milyen join algoritmusokat használnak az adatbázisok és mikor melyiket? -->
<!-- tags: join, nested loop join, hash join, merge join, sort merge, query execution -->

A *nested loop* join a külső tábla minden sorához végignézi (vagy indexszel kikeresi) a belső tábla illeszkedő sorait: kis külső oldalnál és indexelt belső oldalnál verhetetlen, nagy táblákon index nélkül O(n·m). A *hash join* a kisebb oldalból hash-táblát épít, majd a nagyobbon egyszer végigmegy: egyenlőségi joinra a legjobb, O(n+m), de a hash-táblának el kell férnie a memóriában (különben batch-ekre bontja és lemezre ír — `work_mem`). A *merge join* két rendezett bemenetet fésül össze: akkor jó, ha a bemenet már rendezett (index, ORDER BY), és tartomány-feltételhez is használható. A tervező a becsült méretek alapján választ, ezért rossz becslés → rossz join.

```python
from collections import defaultdict

orders = [(1, "c1", 30), (2, "c2", 15), (3, "c1", 99), (4, "c9", 5)]   # (id, customer, összeg)
customers = [("c1", "Anna"), ("c2", "Béla"), ("c3", "Cili")]           # (id, név)

def nested_loop_join(outer, inner, okey, ikey):
    # O(n*m) — belső index esetén a belső ciklus helyett indexkeresés: O(n log m)
    for o in outer:
        for i in inner:
            if okey(o) == ikey(i):
                yield o + i

def hash_join(build, probe, bkey, pkey):
    # 1) build fázis: a KISEBB oldalból hash-tábla (duplikált kulcsokat is kezel)
    table = defaultdict(list)
    for b in build:
        table[bkey(b)].append(b)
    # 2) probe fázis: a nagyobb oldal egyetlen bejárása
    for p in probe:
        for b in table.get(pkey(p), ()):
            yield p + b

def merge_join(left, right, lkey, rkey):
    # Mindkét bemenet a join-kulcs szerint rendezett (pl. indexből jön)
    left, right = sorted(left, key=lkey), sorted(right, key=rkey)
    i = j = 0
    while i < len(left) and j < len(right):
        lk, rk = lkey(left[i]), rkey(right[j])
        if lk < rk: i += 1
        elif lk > rk: j += 1
        else:
            # azonos kulcsú csoportok keresztszorzata
            j_end = j
            while j_end < len(right) and rkey(right[j_end]) == lk: j_end += 1
            while i < len(left) and lkey(left[i]) == lk:
                for r in right[j:j_end]:
                    yield left[i] + r
                i += 1
            j = j_end

ok, ck = (lambda o: o[1]), (lambda c: c[0])
print(list(nested_loop_join(orders, customers, ok, ck)))
print(list(hash_join(customers, orders, ck, ok)))   # build = customers (kisebb)
print(list(merge_join(orders, customers, ok, ck)))
```

## Indexek belső működése és típusai
<!-- q: Milyen indextípusok vannak és hogyan válasszak közülük? -->
<!-- tags: index, btree index, composite index, covering index, partial index, gin, brin, index only scan, postgres -->

A B-tree index rendezett (kulcs → sorhivatkozás) párokat tárol, ezért egyenlőségre, tartományra, rendezésre és prefix-keresésre jó; összetett indexnél a *bal szélső prefix* szabály érvényes: `(a, b)` segít `a`-ra és `a, b`-re, de `b`-re önmagában nem. A *covering* index (`INCLUDE`) minden kért oszlopot tartalmaz, így *index-only scan* lehetséges (Postgresben csak ha a visibility map szerint a lap „all-visible” — ehhez VACUUM kell). A *részleges* index csak a sorok egy részét indexeli (kisebb, gyorsabb), a GIN fordított index tömbökre, JSONB-re és teljes szöveges keresésre, a BRIN pedig blokktartományonként min/max értéket tárol — apró, és természetes sorrendű (időbélyeg) óriástáblákra ideális. Minden index lassítja az írást és helyet foglal; a nem használtakat (`pg_stat_user_indexes.idx_scan = 0`) töröld.

```sql
-- Összetett index: az egyenlőségi oszlop elöl, a tartomány/rendezés utána
CREATE INDEX orders_cust_created_idx ON orders (customer_id, created_at DESC);
-- Ezt kiszolgálja (Index Scan, külön rendezés nélkül):
SELECT * FROM orders WHERE customer_id = 42 ORDER BY created_at DESC LIMIT 20;
-- Ezt NEM (nincs bal szélső prefix): WHERE created_at > now() - interval '1 day'

-- Covering index: index-only scan, a heap érintése nélkül
CREATE INDEX orders_status_cov_idx ON orders (status) INCLUDE (total, customer_id);

-- Részleges index: csak a ritka, de sokat keresett sorok
CREATE INDEX orders_pending_idx ON orders (created_at) WHERE status = 'pending';

-- Kifejezés-index: a WHERE-nek PONTOSAN ezt a kifejezést kell használnia
CREATE INDEX users_email_lower_idx ON users (lower(email));
SELECT * FROM users WHERE lower(email) = lower('Valaki@Example.com');

-- GIN: JSONB-tartalmazás és teljes szöveges keresés
CREATE INDEX events_payload_gin ON events USING gin (payload jsonb_path_ops);
SELECT * FROM events WHERE payload @> '{"type": "login"}';

-- BRIN: pár KB egy milliárd soros, időrendben beszúrt naplótáblára
CREATE INDEX logs_ts_brin ON logs USING brin (ts) WITH (pages_per_range = 64);

-- Nagy táblán zárolás nélkül építsd (lassabb, de nem blokkolja az írást)
CREATE INDEX CONCURRENTLY orders_ref_idx ON orders (external_ref);

-- Nem használt indexek felderítése
SELECT relname, indexrelname, idx_scan, pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes WHERE idx_scan = 0 ORDER BY pg_relation_size(indexrelid) DESC;
```

## VACUUM, bloat és compaction
<!-- q: Mit csinál a VACUUM, mi a bloat, és miért kell az autovacuumot hangolni? -->
<!-- tags: vacuum, autovacuum, bloat, dead tuples, hot update, fillfactor, transaction id wraparound, compaction -->

MVCC-ben az UPDATE és DELETE „halott” sorverziókat hagy hátra; a VACUUM ezeket felszabadítja (a hely újrahasznosítható, de a fájl nem zsugorodik), frissíti a visibility mapet (index-only scanhez), és „befagyasztja” a régi tranzakció-azonosítókat a 32 bites xid *wraparound* ellen. Az autovacuum alapbeállításai (a tábla 20%-a halott) nagy, sokat írt táblákon túl ritkák, ezért ott táblaszintű hangolás kell. A hosszan nyitva tartott tranzakció (vagy elhagyott replication slot) megakadályozza a takarítást, mert a régi snapshot még láthatja a régi verziókat — ez a bloat leggyakoribb oka. Az LSM-motorok megfelelője a compaction (leveled: kisebb olvasási/tárhely-erősítés; size-tiered: kisebb írási erősítés).

```sql
-- Mely táblákban sok a halott sor, és mikor futott utoljára az autovacuum?
SELECT relname, n_live_tup, n_dead_tup,
       round(100.0 * n_dead_tup / greatest(n_live_tup, 1), 1) AS dead_pct,
       last_autovacuum, last_autoanalyze
FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 10;

-- Nagy, sokat írt tábla: gyakoribb, de lassított (I/O-kímélő) autovacuum
ALTER TABLE events SET (
    autovacuum_vacuum_scale_factor = 0.01,     -- 1% halott sor után (alap: 20%)
    autovacuum_vacuum_cost_limit   = 2000,
    autovacuum_analyze_scale_factor = 0.02
);

-- HOT update: ha nem indexelt oszlop változik és van hely a lapon, nem kell indexbejegyzés
ALTER TABLE counters SET (fillfactor = 80);   -- 20% szabad hely marad az új verzióknak

-- Mi tartja vissza a takarítást? A legrégebbi nyitott tranzakciók:
SELECT pid, state, now() - xact_start AS age, left(query, 60)
FROM pg_stat_activity WHERE xact_start IS NOT NULL ORDER BY xact_start LIMIT 5;

-- Wraparound-figyelés: 2 milliárd közelében a Postgres leállítja az írást
SELECT datname, age(datfrozenxid) FROM pg_database ORDER BY 2 DESC;

VACUUM (VERBOSE, ANALYZE) events;  -- kézi takarítás, nem zárol
-- VACUUM FULL: újraírja a táblát és visszaadja a helyet, de EXKLUZÍV zárat tart!
-- Élesben inkább: pg_repack, ami online újraépít.
```

## Replikációs naplók: fizikai és logikai replikáció
<!-- q: Hogyan működik az adatbázis replikáció a napló alapján? -->
<!-- tags: replication, streaming replication, logical replication, binlog, cdc, replication lag, leader follower -->

A replikáció lényege, hogy a leader a módosításait egy rendezett naplóba írja, a follower-ek pedig ugyanabban a sorrendben alkalmazzák. A *fizikai* replikáció (Postgres streaming, WAL shipping) bájtszinten másolja a lapváltozásokat: egyszerű és gyors, de csak azonos verziójú, teljes klasztert replikál. A *logikai* replikáció (Postgres publication/subscription, MySQL row-based binlog, Debezium CDC) sorszintű eseményeket küld: táblák szelektíven, verziók között is replikálhatók, és más rendszerekbe (Kafka, kereső) továbbíthatók. Aszinkron replikáció esetén a follower lemaradhat (*replication lag*), így „read-your-writes” garancia kell az olvasások irányításánál; szinkron módban a commit megvárja a replikát, ami késleltetést ad.

```python
class Leader:
    def __init__(self):
        self.log, self.data = [], {}            # a napló az igazság forrása
    def write(self, key, value):
        self.log.append({"lsn": len(self.log) + 1, "key": key, "value": value})
        self.data[key] = value
        return len(self.log)                    # a kliens ezt az LSN-t kapja vissza

class Follower:
    def __init__(self, leader):
        self.leader, self.applied_lsn, self.data = leader, 0, {}
    def pull(self, max_batch=100):
        # Folytatás a saját pozíciótól: újraindulás után sincs kihagyás vagy duplikáció
        batch = self.leader.log[self.applied_lsn:self.applied_lsn + max_batch]
        for entry in batch:
            if entry["lsn"] <= self.applied_lsn:
                continue                        # idempotens alkalmazás
            self.data[entry["key"]] = entry["value"]
            self.applied_lsn = entry["lsn"]
    def lag(self):
        return len(self.leader.log) - self.applied_lsn

def read_your_writes(key, min_lsn, follower, leader):
    # Ha a replika még nem érte el a kliens utolsó írását, a leaderről olvasunk
    return follower.data.get(key) if follower.applied_lsn >= min_lsn else leader.data.get(key)

leader = Leader(); replica = Follower(leader)
lsn = leader.write("profile:1", "új név")
print("lag:", replica.lag(), "->", read_your_writes("profile:1", lsn, replica, leader))
replica.pull()
print("lag:", replica.lag(), "->", read_your_writes("profile:1", lsn, replica, leader))
```

```sql
-- Postgres logikai replikáció (wal_level = logical kell a forráson)
CREATE PUBLICATION orders_pub FOR TABLE orders, order_items;          -- forrás oldalon
CREATE SUBSCRIPTION orders_sub
    CONNECTION 'host=primary dbname=shop user=replicator'             -- jelszó a .pgpass-ban
    PUBLICATION orders_pub;                                           -- cél oldalon
-- Lemaradás figyelése a primary-n:
SELECT client_addr, state, replay_lag FROM pg_stat_replication;
```

## Oszlopos tárolás és tömörítés
<!-- q: Miért gyorsabb az oszlopos tárolás analitikai lekérdezésekre? -->
<!-- tags: columnar storage, column store, olap, dictionary encoding, run length encoding, zone map, parquet, clickhouse -->

A sororientált tárolás (OLTP: Postgres, MySQL) egy sor összes oszlopát egymás mellett tárolja — egy rekord gyorsan olvasható és írható. Az oszlopos tárolás (ClickHouse, DuckDB, Parquet, Snowflake) oszloponként tárol, így egy `SUM(amount)` csak az érintett oszlopot olvassa, az azonos típusú, hasonló értékek pedig kiválóan tömöríthetők (dictionary, run-length, delta encoding). A blokkonkénti min/max statisztika (*zone map*) teljes blokkokat ugrat át, a vektorizált végrehajtás pedig egyszerre ezernyi értéket dolgoz fel SIMD-del. Hátránya: az egysoros beszúrás és frissítés drága, ezért kötegelt betöltésre és analitikára való.

```python
from itertools import groupby

rows = [("2025-01-01", "HU", 120), ("2025-01-01", "HU", 80), ("2025-01-01", "DE", 50),
        ("2025-01-02", "HU", 70), ("2025-01-02", "AT", 30), ("2025-01-02", "AT", 45)]

# Sor -> oszlop átrendezés
dates, countries, amounts = (list(col) for col in zip(*rows))

def dictionary_encode(values):
    # Alacsony kardinalitású szövegoszlop -> kis egész kódok + szótár
    dictionary = sorted(set(values))
    index = {v: i for i, v in enumerate(dictionary)}
    return dictionary, [index[v] for v in values]

def run_length_encode(values):
    # Rendezett/ismétlődő oszlop -> (érték, ismétlésszám) párok
    return [(v, len(list(g))) for v, g in groupby(values)]

def zone_maps(values, block=2):
    # Blokkonkénti min/max: a szűrő teljes blokkokat ugorhat át
    return [(min(values[i:i + block]), max(values[i:i + block]), i)
            for i in range(0, len(values), block)]

country_dict, country_codes = dictionary_encode(countries)
print(country_dict, country_codes)        # ['AT','DE','HU'] [2, 2, 1, 2, 0, 0]
print(run_length_encode(dates))           # [('2025-01-01', 3), ('2025-01-02', 3)]

# SELECT sum(amount) WHERE amount > 100 — zone map-pel csak az érintett blokkot olvassuk
total = 0
for lo, hi, start in zone_maps(amounts):
    if hi <= 100:
        continue                          # az egész blokk kiesik, nem olvassuk be
    total += sum(a for a in amounts[start:start + 2] if a > 100)
print(total)

# Szűrés a kódolt adaton: 'HU' -> 2, egész-összehasonlítás string helyett
hu = country_dict.index("HU")
print(sum(a for code, a in zip(country_codes, amounts) if code == hu))   # 270
```

## Kulcs-érték tár nulláról (Bitcask-modell)
<!-- q: Hogyan írjak egyszerű, tartós kulcs-érték adatbázist? -->
<!-- tags: key value store, bitcask, append only log, keydir, compaction, hash index, storage engine -->

A Bitcask-modellben (Riak) az adatfájl maga a napló: minden írás a fájl végére kerül, a memóriában pedig egy hash-tábla (*keydir*) tárolja, hogy melyik kulcs legfrissebb értéke melyik offseten van — így egy olvasás egyetlen lemezművelet. A törlés tombstone rekord, a régi verziókat a *merge/compaction* takarítja: új fájlba írja az élő kulcsokat, majd atomi átnevezéssel lecseréli a régit. Korlát: minden kulcsnak el kell férnie a memóriában, és tartomány-lekérdezés nincs (ehhez rendezett struktúra, pl. LSM kell). A CRC véd a félig kiírt rekordok ellen.

```python
import os
import struct
import zlib

REC = struct.Struct("<IHI")          # crc32, kulcshossz, értékhossz (0xFFFFFFFF = tombstone)
TOMB = 0xFFFFFFFF

class Bitcask:
    def __init__(self, path):
        self.path, self.keydir = path, {}            # kulcs -> (érték offset, hossz)
        open(path, "ab").close()
        self._load()
        self.f = open(path, "a+b")

    def _load(self):
        with open(self.path, "rb") as f:             # induláskor a teljes napló bejárása
            while head := f.read(REC.size):
                if len(head) < REC.size: break
                crc, klen, vlen = REC.unpack(head)
                key = f.read(klen)
                value = b"" if vlen == TOMB else f.read(vlen)
                if zlib.crc32(key + value) != crc: break   # sérült (torn) vég
                if vlen == TOMB: self.keydir.pop(key, None)
                else: self.keydir[key] = (f.tell() - vlen, vlen)

    def put(self, key: bytes, value: bytes, tomb=False):
        vlen = TOMB if tomb else len(value)
        self.f.seek(0, os.SEEK_END)
        self.f.write(REC.pack(zlib.crc32(key + value), len(key), vlen) + key + value)
        self.f.flush(); os.fsync(self.f.fileno())
        if tomb: self.keydir.pop(key, None)
        else: self.keydir[key] = (self.f.tell() - len(value), len(value))

    def get(self, key: bytes):
        if key not in self.keydir: return None
        offset, length = self.keydir[key]
        self.f.seek(offset)                          # egyetlen seek + read
        return self.f.read(length)

    def delete(self, key: bytes):
        self.put(key, b"", tomb=True)

    def compact(self):
        tmp = self.path + ".compact"
        with open(tmp, "wb") as out:                 # csak az élő, legfrissebb értékek
            for key in list(self.keydir):
                value = self.get(key)
                out.write(REC.pack(zlib.crc32(key + value), len(key), len(value)) + key + value)
            out.flush(); os.fsync(out.fileno())
        self.f.close()
        os.replace(tmp, self.path)                   # atomi csere
        self.keydir = {}; self._load(); self.f = open(self.path, "a+b")

db = Bitcask("kv.data")
for i in range(3): db.put(b"counter", str(i).encode())
db.put(b"temp", b"x"); db.delete(b"temp")
db.compact()
print(db.get(b"counter"), db.get(b"temp"), os.path.getsize("kv.data"))
```

## Redis adatszerkezetek belülről
<!-- q: Milyen adatszerkezetekkel működik a Redis belül, és mire figyeljek a használatánál? -->
<!-- tags: redis, skiplist, sorted set, listpack, intset, hash table, rehashing, single threaded -->

A Redis egyszálú eseményhurokkal szolgálja ki a parancsokat (az I/O többszálú lehet), ezért minden parancs atomi, de egy lassú O(n) parancs (`KEYS *`, nagy `SMEMBERS`, `DEL` óriás kulcson) mindenki mást blokkol — helyette `SCAN` és `UNLINK`. Az értéktípusok kis méretnél tömör kódolást használnak (listpack, intset), nagyobbnál átváltanak valódi struktúrára: a sorted set skiplist + hash tábla (O(log n) rangsor-műveletek), a hash tábla pedig *inkrementálisan* rehashel, hogy ne legyen hosszú szünet. A stringek bináris-biztos SDS-ek; a lejárat (TTL) lusta törléssel és periodikus mintavétellel működik. Az alábbi skiplist a `ZADD`/`ZRANGEBYSCORE` mögötti elv.

```python
import random

class Node:
    __slots__ = ("score", "member", "forward")
    def __init__(self, score, member, level):
        self.score, self.member, self.forward = score, member, [None] * level

class SkipList:
    """Rendezett halmaz: valószínűségi szintek, várhatóan O(log n) keresés és beszúrás."""
    MAX_LEVEL, P = 32, 0.25                  # a Redis is p=0.25-öt használ

    def __init__(self):
        self.head, self.level = Node(float("-inf"), None, self.MAX_LEVEL), 1

    def _random_level(self):
        lvl = 1
        while random.random() < self.P and lvl < self.MAX_LEVEL:
            lvl += 1
        return lvl

    def insert(self, score, member):
        update, x = [self.head] * self.MAX_LEVEL, self.head
        for i in reversed(range(self.level)):         # felülről lefelé, „expressz sávokon”
            while x.forward[i] and (x.forward[i].score, x.forward[i].member) < (score, member):
                x = x.forward[i]
            update[i] = x                             # ide kell majd befűzni ezen a szinten
        lvl = self._random_level()
        self.level = max(self.level, lvl)
        node = Node(score, member, lvl)
        for i in range(lvl):
            node.forward[i], update[i].forward[i] = update[i].forward[i], node

    def range_by_score(self, lo, hi):
        x = self.head
        for i in reversed(range(self.level)):
            while x.forward[i] and x.forward[i].score < lo:
                x = x.forward[i]
        x = x.forward[0]                              # alsó szint: rendezett láncolt lista
        while x and x.score <= hi:
            yield x.member, x.score
            x = x.forward[0]

leaderboard = SkipList()
for member, score in [("anna", 310), ("bela", 120), ("cili", 450), ("dani", 290)]:
    leaderboard.insert(score, member)
print(list(leaderboard.range_by_score(200, 400)))     # [('dani', 290), ('anna', 310)]
```

```bash
redis-cli ZADD board 310 anna 120 bela
redis-cli OBJECT ENCODING board          # "listpack" — kicsi, tömör
redis-cli CONFIG GET zset-max-listpack-entries   # e fölött skiplist-re vált
redis-cli --scan --pattern 'session:*' | head    # KEYS * helyett: nem blokkol
redis-cli UNLINK big:set                 # háttérszálon szabadít fel, nem blokkol
```

## MongoDB dokumentummodell: beágyazás vs. hivatkozás
<!-- q: Mikor ágyazzak be dokumentumokat MongoDB-ben és mikor hivatkozzak rájuk? -->
<!-- tags: mongodb, document model, embedding, referencing, schema design, multikey index, transactions, aggregation -->

A dokumentummodell előnye, hogy az együtt olvasott adat egy dokumentumban, egyetlen olvasással elérhető (nincs join), és az egy dokumentumon belüli írás atomi. Szabály: ágyazd be, ami a szülővel együtt él és korlátos méretű (címek, rendelés tételei), és hivatkozz, ami korlátlanul nő vagy önállóan is lekérdezett (kommentek, naplóesemények) — a dokumentum mérete max. 16 MB, és a folyamatosan növő tömb lassú, újraírásokat okoz. A denormalizálás gyors olvasást ad, de a duplikált adat frissítése az alkalmazás felelőssége. Többdokumentumos tranzakció van, de drágább, és a `$lookup` join kevésbé hatékony, mint egy relációs motorban — ha a modell erősen relációs, a Postgres (JSONB-vel) gyakran jobb választás.

```javascript
// mongosh — rendelés: a tételek beágyazva (együtt élnek, korlátos számú)
db.orders.insertOne({
  _id: "ord-1001",
  customerId: "cust-42",                       // hivatkozás: a vevő önálló entitás
  status: "paid",
  items: [                                      // beágyazás: egy olvasással megvan minden
    { sku: "KB-01", name: "Billentyűzet", qty: 1, price: 24990 },
    { sku: "MS-07", name: "Egér", qty: 2, price: 8990 },
  ],
  shipping: { city: "Kecskemét", zip: "6000" },
  total: 42970,
  createdAt: new Date(),
});

// Séma-validáció: a „sémamentes” nem jelenti, hogy nincs szükség sémára
db.runCommand({
  collMod: "orders",
  validator: { $jsonSchema: {
    bsonType: "object",
    required: ["customerId", "status", "items", "total"],
    properties: {
      status: { enum: ["pending", "paid", "shipped", "cancelled"] },
      items: { bsonType: "array", minItems: 1, maxItems: 500 },   // korlátos tömb!
      total: { bsonType: ["int", "long", "decimal"], minimum: 0 },
    },
  } },
});

// Összetett index (ESR szabály: Equality, Sort, Range); tömbmezőn multikey index
db.orders.createIndex({ customerId: 1, createdAt: -1 });
db.orders.createIndex({ "items.sku": 1 });

// Atomi módosítás egy dokumentumon belül — nem kell tranzakció
db.orders.updateOne(
  { _id: "ord-1001", status: "paid" },
  { $set: { status: "shipped" }, $push: { history: { at: new Date(), to: "shipped" } } },
);

// Korlátlanul növő adat: KÜLÖN kollekció, nem tömb a szülőben
db.reviews.insertOne({ productSku: "KB-01", rating: 5, text: "Jó", at: new Date() });

// Aggregáció $lookup-pal (join) — ritka lekérdezésre oké, forró útvonalon kerüld
db.orders.aggregate([
  { $match: { status: "shipped" } },
  { $lookup: { from: "customers", localField: "customerId", foreignField: "_id", as: "customer" } },
  { $unwind: "$customer" },
  { $group: { _id: "$customer.country", revenue: { $sum: "$total" } } },
  { $sort: { revenue: -1 } },
]);
```
