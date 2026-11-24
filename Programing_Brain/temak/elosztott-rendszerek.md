# Elosztott rendszerek
<!-- tech: distributed-systems -->
<!-- aliases: elosztott rendszerek, distributed systems, mikroszolgáltatások, microservices, replikáció, konszenzus -->

Elosztott rendszerben több, hálózaton kommunikáló gép dolgozik együtt, és mindegyik
függetlenül hibázhat: üzenetek elvesznek, késnek, duplikálódnak, az órák eltérnek, a hálózat
partíciókra szakadhat. Ez a fájl a fő kompromisszumokat (CAP, PACELC, konzisztencia-modellek),
a replikációt és konszenzust (Raft), a particionálást, az elosztott tranzakciókat (2PC, saga),
az üzenetkezelési szemantikákat és a rugalmassági mintákat (rate limit, circuit breaker,
újrapróbálás jitterrel, service discovery, megfigyelhetőség) tárgyalja.

## CAP-tétel és PACELC
<!-- q: Mit mond ki a CAP-tétel és a PACELC, és mit jelent ez a gyakorlatban? -->
<!-- tags: cap theorem, pacelc, partition tolerance, consistency, availability, latency -->

A CAP szerint hálózati partíció (P) esetén választani kell a konzisztencia (C: minden olvasás a
legfrissebb írást látja, vagy hibát ad) és a rendelkezésre állás (A: minden működő csomópont
válaszol) között; a P nem opcionális, mert a hálózat hibázik. A PACELC kiegészíti: ha nincs
partíció (Else), akkor is választani kell a késleltetés (L) és a konzisztencia (C) között, mert
az erős konzisztencia koordinációt (körutakat) igényel. Példák: etcd, ZooKeeper, Spanner — PC/EC;
Cassandra, DynamoDB alapbeállítással — PA/EL, de hangolható. A választás valójában
műveletenként is történhet (pl. fizetés CP, ajánlások AP).

```python
from dataclasses import dataclass, field
from enum import Enum

class Mode(Enum):
    CP = "CP"  # partíció alatt inkább hibát ad, mint elavult/ütköző adatot
    AP = "AP"  # partíció alatt is válaszol, de a replikák eltérhetnek

class Unavailable(Exception):
    pass

@dataclass
class Replica:
    name: str
    data: dict[str, tuple[int, str]] = field(default_factory=dict)  # kulcs -> (verzió, érték)

@dataclass
class Cluster:
    replicas: list[Replica]
    mode: Mode
    reachable: set[str] = field(default_factory=set)  # a kliens oldaláról elérhető replikák

    def _live(self) -> list[Replica]:
        live = [r for r in self.replicas if r.name in self.reachable]
        if self.mode is Mode.CP and len(live) < len(self.replicas) // 2 + 1:
            raise Unavailable("nincs többség: a kérés elutasítva")  # kisebbségi oldal nem szolgál ki
        return live

    def write(self, key: str, value: str) -> None:
        live = self._live()
        version = max((r.data.get(key, (0, ""))[0] for r in live), default=0) + 1
        for r in live:  # AP-ben a kisebbségi oldal is ír => később ütközésfeloldás kell
            r.data[key] = (version, value)

    def read(self, key: str) -> str | None:
        best = max((r.data[key] for r in self._live() if key in r.data), default=None)
        return best[1] if best else None

if __name__ == "__main__":
    for mode in Mode:
        c = Cluster([Replica("a"), Replica("b"), Replica("c")], mode, {"a", "b", "c"})
        c.write("ár", "100")
        c.reachable = {"c"}  # hálózati partíció: a kliens csak 'c'-t éri el
        try:
            c.write("ár", "120")
            print(mode.value, "írt a partíció alatt:", c.read("ár"), "(a és b még a régit tárolja)")
        except Unavailable as e:
            print(mode.value, "partíció alatt:", e)
```

## Konzisztencia-modellek és munkamenet-garanciák
<!-- q: Milyen konzisztencia-modellek vannak, és mi az a read-your-writes? -->
<!-- tags: consistency models, linearizability, causal consistency, eventual consistency, read your writes, session guarantees -->

A legerősebb a linearizálhatóság: a rendszer úgy viselkedik, mintha egyetlen példány lenne, és
egy befejezett írás után minden olvasás látja azt. Gyengébb fokozatok: szekvenciális, kauzális
(az ok-okozati sorrend mindenkinél azonos), végül az eventual consistency (írások nélkül előbb-
utóbb minden replika egyezik). A gyakorlatban sokszor a munkamenet-garanciák elegendők:
read-your-writes (látod a saját írásodat), monoton olvasás (nem „ugrasz vissza az időben”),
monoton írás. Aszinkron replikációnál a követőről olvasás ezeket megsérti — a megoldás a kliens
utolsó írásának verzióját (LSN) figyelembe vevő útválasztás.

```python
import random
from dataclasses import dataclass, field

@dataclass
class Node:
    name: str
    applied_lsn: int = 0  # meddig alkalmazta a replikációs naplót
    data: dict[str, str] = field(default_factory=dict)

class ReplicatedStore:
    """Leader + aszinkron követők; a követők késve zárkóznak fel."""

    def __init__(self, followers: int = 2) -> None:
        self.leader = Node("leader")
        self.followers = [Node(f"f{i}") for i in range(followers)]
        self.log: list[tuple[int, str, str]] = []

    def write(self, key: str, value: str) -> int:
        lsn = len(self.log) + 1
        self.log.append((lsn, key, value))
        self.leader.data[key] = value
        self.leader.applied_lsn = lsn
        return lsn  # a kliens ezt munkamenet-tokenként megőrzi

    def replicate_some(self) -> None:
        for f in self.followers:  # véletlen mértékű felzárkózás = replikációs késés
            target = random.randint(f.applied_lsn, len(self.log))
            for lsn, k, v in self.log[f.applied_lsn:target]:
                f.data[k] = v
                f.applied_lsn = lsn

    def read(self, key: str, min_lsn: int = 0) -> tuple[str | None, str]:
        # Csak olyan követőről olvasunk, amelyik már elérte a kliens által látott LSN-t
        ok = [f for f in self.followers if f.applied_lsn >= min_lsn]
        node = random.choice(ok) if ok else self.leader  # végső esetben a leader
        return node.data.get(key), node.name

class Session:
    def __init__(self, store: ReplicatedStore) -> None:
        self.store, self.last_lsn = store, 0

    def write(self, k: str, v: str) -> None:
        self.last_lsn = max(self.last_lsn, self.store.write(k, v))

    def read(self, k: str) -> tuple[str | None, str]:
        return self.store.read(k, self.last_lsn)  # read-your-writes garancia

if __name__ == "__main__":
    store = ReplicatedStore()
    s = Session(store)
    s.write("profil:név", "Új név")
    print("naiv olvasás:", store.read("profil:név"))  # lehet None egy lemaradt követőről
    print("RYW olvasás:", s.read("profil:név"))  # mindig 'Új név'
    store.replicate_some()
    print("felzárkózás után:", s.read("profil:név"))
```

## Leader–follower replikáció: szinkron, aszinkron, félszinkron
<!-- q: Mi a különbség a szinkron és az aszinkron replikáció között, és mi a kockázata a failovernek? -->
<!-- tags: replication, leader follower, synchronous, asynchronous, semi-sync, failover, split brain, fencing -->

Leader–follower replikációban minden írás a leaderhez megy, ő továbbítja a naplót a követőknek.
Szinkron replikációnál a kliens csak akkor kap OK-t, ha a követő(k) is tárolták az írást
(tartós, de lassabb, és egy lassú követő megállítja az írásokat); aszinkronnál azonnal (gyors,
de a leader összeomlásakor a már nyugtázott írások elveszhetnek); a félszinkron egy követőt vár
meg, időtúllépésnél aszinkronra esik vissza. Failovernél a fő veszélyek: elveszett írások, és a
„split brain”, amikor két csomópont is leadernek hiszi magát — ez ellen fencing token / epoch
szám és kvórum-alapú választás véd.

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"math/rand"
	"sync"
	"time"
)

type Entry struct {
	Index      int
	Key, Value string
}

type Follower struct {
	mu  sync.Mutex
	log []Entry
}

func (f *Follower) Append(ctx context.Context, e Entry) error { // szimulált hálózati késés
	select {
	case <-time.After(time.Duration(rand.Intn(80)) * time.Millisecond):
		f.mu.Lock()
		f.log = append(f.log, e)
		f.mu.Unlock()
		return nil
	case <-ctx.Done():
		return ctx.Err()
	}
}

type Leader struct {
	mu        sync.Mutex
	log       []Entry
	followers []*Follower
	syncAcks  int // hány követő nyugtája kell az OK előtt (0 = aszinkron)
}

func (l *Leader) Write(ctx context.Context, key, value string) error {
	l.mu.Lock()
	e := Entry{Index: len(l.log) + 1, Key: key, Value: value}
	l.log = append(l.log, e) // helyben naplózás (élesben fsync)
	l.mu.Unlock()

	acks := make(chan error, len(l.followers)) // pufferelt: a késő válasz sem blokkol
	for _, f := range l.followers {
		go func(f *Follower) { acks <- f.Append(context.Background(), e) }(f) // a többi a háttérben zárkózik fel
	}
	ctx, cancel := context.WithTimeout(ctx, 50*time.Millisecond)
	defer cancel()
	for got := 0; got < l.syncAcks; {
		select {
		case err := <-acks:
			if err == nil {
				got++
			}
		case <-ctx.Done():
			// Félszinkron rendszer itt aszinkronra esne vissza; mi jelezzük a tartósság hiányát
			return errors.New("replikációs nyugta időtúllépés")
		}
	}
	return nil
}

func main() {
	fs := []*Follower{{}, {}}
	for _, mode := range []int{0, 1, 2} {
		l := &Leader{followers: fs, syncAcks: mode}
		start := time.Now()
		err := l.Write(context.Background(), "k", "v")
		fmt.Printf("syncAcks=%d err=%v késleltetés=%v\n", mode, err, time.Since(start).Round(time.Millisecond))
	}
}
```

## Multi-leader replikáció és CRDT-k
<!-- q: Hogyan kezeljem az ütközéseket multi-leader replikációnál, és mik azok a CRDT-k? -->
<!-- tags: multi-leader, conflict resolution, crdt, last writer wins, pn-counter, convergence -->

Multi-leader (és leaderless) rendszerben több replika fogad egyszerre írást — több adatközpont,
offline-képes kliensek, közös szerkesztés —, így az ütközések elkerülhetetlenek. A „last writer
wins” egyszerű, de az egyidejű írások közül az egyik csendben elvész, és órák eltérésére
érzékeny. A CRDT-k (Conflict-free Replicated Data Types) olyan adattípusok, amelyek
összevonása kommutatív, asszociatív és idempotens, így a replikák bármilyen sorrendben, akár
többszöri állapotcserével is ugyanarra az eredményre konvergálnak (Riak, Redis Enterprise,
Automerge, Yjs). Korlát: nem minden invariáns fejezhető ki CRDT-vel (pl. „egyenleg ≥ 0”).

```python
from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class PNCounter:
    """Növelhető-csökkenthető számláló CRDT: replikánként külön P és N számláló.
    Összevonás = elemenkénti maximum => kommutatív, asszociatív, idempotens."""

    replica: str
    p: dict[str, int] = field(default_factory=dict)
    n: dict[str, int] = field(default_factory=dict)

    def incr(self, k: int = 1) -> None:
        self.p[self.replica] = self.p.get(self.replica, 0) + k

    def decr(self, k: int = 1) -> None:
        self.n[self.replica] = self.n.get(self.replica, 0) + k

    def value(self) -> int:
        return sum(self.p.values()) - sum(self.n.values())

    def merge(self, other: PNCounter) -> None:
        for mine, theirs in ((self.p, other.p), (self.n, other.n)):
            for r, v in theirs.items():
                mine[r] = max(mine.get(r, 0), v)

@dataclass
class LWWRegister:
    """Last-Writer-Wins: a nagyobb (időbélyeg, replika) pár nyer; a másik írás elvész."""

    value: str | None = None
    stamp: tuple[float, str] = (0.0, "")

    def set(self, value: str, ts: float, replica: str) -> None:
        if (ts, replica) > self.stamp:  # a replikanév determinisztikusan bontja a holtversenyt
            self.value, self.stamp = value, (ts, replica)

    def merge(self, other: LWWRegister) -> None:
        if other.value is not None:
            self.set(other.value, *other.stamp)

if __name__ == "__main__":
    eu, us = PNCounter("eu"), PNCounter("us")  # két adatközpont partíció alatt
    eu.incr(5)
    us.incr(3)
    us.decr(1)
    eu.merge(us)
    us.merge(eu)
    eu.merge(us)  # ismételt összevonás sem ront el semmit (idempotencia)
    print(eu.value(), us.value())  # 7 7 — konvergencia

    a, b = LWWRegister(), LWWRegister()
    a.set("kék", 1000.0, "eu")
    b.set("piros", 1000.0, "us")
    a.merge(b)
    b.merge(a)
    print(a.value, b.value)  # piros piros — a "kék" írás elveszett
```

## Kvórumok (N, W, R) és read repair
<!-- q: Hogyan működnek a kvórum-alapú olvasások és írások leaderless adatbázisokban? -->
<!-- tags: quorum, leaderless replication, dynamo, read repair, sloppy quorum, hinted handoff -->

Leaderless (Dynamo-stílusú: Cassandra, Riak, ScyllaDB) rendszerben a kliens N replikának küld
írást, és W nyugta után sikeresnek tekinti; olvasáskor R replikát kérdez, és a legnagyobb
verziót veszi. Ha W + R > N, minden olvasási halmaz metszi az utolsó sikeres írás halmazát,
így legalább egy friss választ kapunk; W és R hangolásával az írási vagy olvasási késleltetést
optimalizálhatjuk. Az elavult replikákat a read repair (olvasás közbeni javítás) és a háttérben
futó anti-entropy (Merkle-fás összehasonlítás) hozza helyre. Buktató: a kvórum még nem
linearizálható (pl. részben sikerült írás, sloppy quorum hinted handoff-fal).

```python
import random
from dataclasses import dataclass, field

@dataclass
class Replica:
    name: str
    up: bool = True
    store: dict[str, tuple[int, str]] = field(default_factory=dict)  # kulcs -> (verzió, érték)

class QuorumKV:
    """Ha W + R > N, az olvasási és írási kvórum mindig metszi egymást."""

    def __init__(self, n: int = 3, w: int = 2, r: int = 2) -> None:
        assert w + r > n, "W + R > N nélkül elavult olvasás lehetséges"
        self.replicas = [Replica(f"r{i}") for i in range(n)]
        self.w, self.r = w, r

    def put(self, key: str, value: str, version: int) -> None:
        acks = 0
        for rep in self.replicas:  # élesben párhuzamosan, időkorláttal
            if rep.up:
                if version > rep.store.get(key, (0, ""))[0]:
                    rep.store[key] = (version, value)
                acks += 1
        if acks < self.w:
            # Az írás RÉSZBEN megtörténhetett — nincs rollback, a kliens újrapróbál
            raise RuntimeError(f"írási kvórum nem teljesült ({acks}/{self.w})")

    def get(self, key: str) -> str | None:
        live = [rep for rep in self.replicas if rep.up]
        if len(live) < self.r:
            raise RuntimeError("olvasási kvórum nem teljesült")
        replies = [(rep, rep.store.get(key, (0, None))) for rep in random.sample(live, self.r)]
        newest = max((v for _, v in replies), key=lambda v: v[0])
        for rep, v in replies:  # read repair: az elavult replikát menet közben frissítjük
            if v[0] < newest[0]:
                rep.store[key] = newest
        return newest[1]

if __name__ == "__main__":
    kv = QuorumKV()
    kv.put("kosár:42", "[alma]", version=1)
    kv.replicas[0].up = False  # egy csomópont kiesik
    kv.put("kosár:42", "[alma, körte]", version=2)  # W=2 még teljesül
    kv.replicas[0].up = True  # visszajön, elavult adattal
    print(kv.get("kosár:42"))  # mindig '[alma, körte]' a metszés miatt
```

## Raft konszenzus: vezetőválasztás
<!-- q: Hogyan működik a Raft konszenzus algoritmus vezetőválasztása? -->
<!-- tags: raft, consensus, leader election, term, request vote, etcd, distributed log -->

A Raft (etcd, Consul, CockroachDB, TiKV) egy replikált naplóban egyezteti a csomópontokat;
2f+1 csomóponttal f kiesését bírja. Az idő ciklusokra (term) oszlik, ciklusonként legfeljebb egy
leader lehet. Ha egy követő a véletlenített választási időkorlátig (pl. 150–300 ms) nem kap
heartbeatet, jelöltté válik, növeli a ciklust, magára szavaz és szavazatot kér; a többséget
elérő jelölt lesz a leader. Szavazni csak ciklusonként egyszer és csak legalább annyira friss
naplójú jelöltre lehet — ez garantálja, hogy az új leader minden véglegesített bejegyzést
tartalmaz. A currentTerm és votedFor értékét válaszadás előtt tartósan (fsync) menteni kell.

```go
package raft

import (
	"math/rand"
	"sync"
	"time"
)

type Role int

const (
	Follower Role = iota
	Candidate
	Leader
)

type LogEntry struct {
	Term    int
	Command []byte
}

type Node struct {
	mu          sync.Mutex
	id          int
	peers       []int
	role        Role
	currentTerm int        // tartósan mentendő
	votedFor    int        // -1 = ebben a ciklusban még nem szavazott; tartósan mentendő
	log         []LogEntry // log[0] egy üres őrszem bejegyzés (Term 0)
	commitIndex int
	lastHeard   time.Time
}

type VoteArgs struct{ Term, CandidateID, LastLogIndex, LastLogTerm int }
type VoteReply struct {
	Term        int
	VoteGranted bool
}

// Véletlenített időkorlát: ritkán indul egyszerre két jelölt (kevesebb osztott szavazás)
func electionTimeout() time.Duration { return time.Duration(150+rand.Intn(150)) * time.Millisecond }

func (n *Node) HandleRequestVote(a VoteArgs) VoteReply {
	n.mu.Lock()
	defer n.mu.Unlock()
	if a.Term > n.currentTerm { // újabb ciklus: követővé válunk, új szavazat lehetséges
		n.currentTerm, n.votedFor, n.role = a.Term, -1, Follower
	}
	if a.Term < n.currentTerm {
		return VoteReply{Term: n.currentTerm} // elavult jelölt
	}
	lastIdx := len(n.log) - 1
	lastTerm := n.log[lastIdx].Term
	upToDate := a.LastLogTerm > lastTerm || (a.LastLogTerm == lastTerm && a.LastLogIndex >= lastIdx)
	if (n.votedFor == -1 || n.votedFor == a.CandidateID) && upToDate {
		n.votedFor = a.CandidateID
		n.lastHeard = time.Now() // szavazás után ne induljunk rögtön mi is
		return VoteReply{Term: n.currentTerm, VoteGranted: true}
	}
	return VoteReply{Term: n.currentTerm}
}

// startElection: heartbeat hiányában új ciklus jelöltként (élesben párhuzamos RPC-kkel)
func (n *Node) startElection(send func(peer int, a VoteArgs) (VoteReply, bool)) {
	n.mu.Lock()
	n.role, n.currentTerm, n.votedFor = Candidate, n.currentTerm+1, n.id
	args := VoteArgs{n.currentTerm, n.id, len(n.log) - 1, n.log[len(n.log)-1].Term}
	n.mu.Unlock()
	votes := 1 // saját szavazat
	for _, p := range n.peers {
		reply, ok := send(p, args)
		n.mu.Lock()
		if ok && reply.Term > n.currentTerm {
			n.currentTerm, n.votedFor, n.role = reply.Term, -1, Follower // van újabb ciklus
		} else if ok && reply.VoteGranted && n.role == Candidate && n.currentTerm == args.Term {
			if votes++; votes > (len(n.peers)+1)/2 {
				n.role = Leader // azonnal heartbeatet (üres AppendEntries) küld
			}
		}
		n.mu.Unlock()
	}
}
```

## Raft konszenzus: naplóreplikáció és véglegesítés
<!-- q: Hogyan replikálja a Raft a naplót, és mikor véglegesített egy bejegyzés? -->
<!-- tags: raft, log replication, append entries, commit index, log matching, state machine replication -->

A leader az új parancsot a naplójához fűzi, majd AppendEntries RPC-vel küldi a követőknek,
mellékelve az előző bejegyzés indexét és ciklusát. A követő csak akkor fogadja el, ha ezen a
ponton a naplója egyezik a leaderével (Log Matching: azonos index és ciklus esetén a teljes
előzmény is azonos); eltérésnél a leader egyre korábbról küld, a követő pedig levágja ütköző,
nem véglegesített végét. Egy bejegyzés akkor véglegesített (commit), ha a többség tárolja és a
leader jelenlegi ciklusából való; ekkor alkalmazható az állapotgépre. Az olvasások
linearizálhatóságához a leadernek is meg kell győződnie, hogy még ő a leader (ReadIndex vagy
lease).

```go
package raft

import "time"

type AppendArgs struct {
	Term         int
	LeaderID     int
	PrevLogIndex int        // az új bejegyzések előtti index...
	PrevLogTerm  int        // ...és ciklusa: erre épül a konzisztencia-ellenőrzés
	Entries      []LogEntry // üres = heartbeat
	LeaderCommit int
}

type AppendReply struct {
	Term    int
	Success bool
}

// Követő oldal
func (n *Node) HandleAppendEntries(a AppendArgs) AppendReply {
	n.mu.Lock()
	defer n.mu.Unlock()
	if a.Term < n.currentTerm {
		return AppendReply{Term: n.currentTerm} // elavult leader
	}
	n.currentTerm, n.role = a.Term, Follower
	n.lastHeard = time.Now() // érvényes leader: a választási időzítő újraindul
	if a.PrevLogIndex >= len(n.log) || n.log[a.PrevLogIndex].Term != a.PrevLogTerm {
		return AppendReply{Term: n.currentTerm} // hiányzó/ütköző előzmény: a leader visszalép
	}
	for i, e := range a.Entries {
		idx := a.PrevLogIndex + 1 + i
		if idx < len(n.log) && n.log[idx].Term != e.Term {
			n.log = n.log[:idx] // ütközés: a saját, nem véglegesített vég eldobása
		}
		if idx >= len(n.log) {
			n.log = append(n.log, e)
		}
	}
	if a.LeaderCommit > n.commitIndex {
		// commitIndex-ig a bejegyzések az állapotgépre alkalmazhatók
		n.commitIndex = min(a.LeaderCommit, a.PrevLogIndex+len(a.Entries))
	}
	return AppendReply{Term: n.currentTerm, Success: true}
}

// Leader oldal: többség tárolja ÉS a jelenlegi ciklusból való => véglegesíthető.
// (Korábbi ciklus bejegyzései csak közvetve, egy új bejegyzéssel együtt véglegesülnek.)
func (n *Node) advanceCommit(matchIndex map[int]int) {
	for idx := len(n.log) - 1; idx > n.commitIndex; idx-- {
		if n.log[idx].Term != n.currentTerm {
			break // a ciklusok monoton nőnek: lejjebb is csak régebbi ciklus van
		}
		count := 1 // a leader maga
		for _, m := range matchIndex {
			if m >= idx {
				count++
			}
		}
		if count > (len(n.peers)+1)/2 {
			n.commitIndex = idx
			return
		}
	}
}
```

## Particionálás (sharding) és konzisztens hash-elés
<!-- q: Hogyan osszam szét az adatokat több szerver között, és mi a konzisztens hash-elés? -->
<!-- tags: partitioning, sharding, consistent hashing, virtual nodes, rebalancing, hot keys -->

A particionálás szétosztja az adatot csomópontok között, hogy a tárolás és a terhelés
skálázódjon. Kulcstartomány szerinti felosztásnál hatékonyak a tartomány-lekérdezések, de
monoton kulcsoknál (időbélyeg) forró pont keletkezik; hash szerinti felosztás egyenletes, de a
tartomány-lekérdezés minden partíciót érint. A naiv `hash % N` szerver hozzáadásakor szinte
minden kulcsot áthelyez; a konzisztens hash-elés gyűrűjén csak kb. 1/N rész költözik, a
virtuális csomópontok pedig egyenletesebbé teszik az eloszlást. Buktatók: a forró kulcsok
(„celebrity problem”) kulcs-sózást igényelnek, a másodlagos indexek pedig vagy helyiek (scatter-
gather olvasás), vagy globálisak (drágább írás).

```python
import bisect
import hashlib
from collections import Counter

def h(s: str) -> int:
    # Stabil hash: a Python beépített hash()-e folyamatonként véletlenített!
    return int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(), "big")

class ConsistentHashRing:
    """Gyűrű virtuális csomópontokkal: egy szerver sok ponton szerepel,
    így kieséskor a terhe sok másik szerver között oszlik szét."""

    def __init__(self, nodes: list[str], vnodes: int = 100) -> None:
        self.vnodes = vnodes
        self._ring: list[tuple[int, str]] = []
        for n in nodes:
            self.add(n)

    def add(self, node: str) -> None:
        for i in range(self.vnodes):
            bisect.insort(self._ring, (h(f"{node}#{i}"), node))

    def remove(self, node: str) -> None:
        self._ring = [(p, n) for p, n in self._ring if n != node]

    def lookup(self, key: str, replicas: int = 1) -> list[str]:
        """Óramutató szerint az első `replicas` KÜLÖNBÖZŐ fizikai csomópont."""
        if not self._ring:
            raise LookupError("üres gyűrű")
        i = bisect.bisect(self._ring, (h(key), ""))
        out: list[str] = []
        for j in range(len(self._ring)):
            node = self._ring[(i + j) % len(self._ring)][1]
            if node not in out:
                out.append(node)
                if len(out) == replicas:
                    break
        return out

if __name__ == "__main__":
    keys = [f"user:{i}" for i in range(20_000)]
    ring = ConsistentHashRing(["db1", "db2", "db3", "db4"])
    before = {k: ring.lookup(k)[0] for k in keys}
    print("eloszlás:", Counter(before.values()))
    ring.add("db5")
    moved = sum(before[k] != ring.lookup(k)[0] for k in keys)
    print(f"konzisztens hash: {moved / len(keys):.1%} költözött")  # ~20%
    naive = sum(h(k) % 4 != h(k) % 5 for k in keys)
    print(f"naiv modulo: {naive / len(keys):.1%} költözött")  # ~80%
```

## Elosztott tranzakciók: kétfázisú commit (2PC)
<!-- q: Hogyan működik a kétfázisú commit, és mi a gyengéje? -->
<!-- tags: two-phase commit, 2pc, distributed transaction, xa, coordinator, atomic commit -->

A 2PC több erőforrás (adatbázis, üzenetsor) között biztosít atomikus commitot. Az első
fázisban a koordinátor mindenkitől megkérdezi, készen áll-e (prepare): az „igen” szavazat
ígéret, hogy a résztvevő bármi történjék képes lesz commitolni, ezért zárakat tart és tartósan
naplóz. Ha mindenki igent mond, a koordinátor tartósan naplózza a döntést, és a második
fázisban mindenkinek commitot küld; bármely „nem” vagy időtúllépés esetén abortot. A fő
gyengeség: ha a koordinátor a két fázis között kiesik, a „prepared” résztvevők blokkolnak és
zárakat tartanak — ezért mikroszolgáltatások között inkább sagát, adatbázison belül pedig
konszenzus-alapú commitot (Spanner, CockroachDB) használnak.

```python
from enum import Enum

class Vote(Enum):
    YES = "yes"
    NO = "no"

class Participant:
    """Erőforrás-kezelő; a prepare után a döntésig zárakat tart és várakozik."""

    def __init__(self, name: str, will_fail: bool = False) -> None:
        self.name, self.will_fail = name, will_fail
        self.state = "init"

    def prepare(self, tx: str) -> Vote:
        if self.will_fail:
            self.state = "aborted"
            return Vote.NO
        self.state = "prepared"  # innentől bizonytalan: csak a koordinátor dönthet
        return Vote.YES

    def commit(self, tx: str) -> None:
        self.state = "committed"

    def abort(self, tx: str) -> None:
        self.state = "aborted"

class Coordinator:
    def __init__(self, participants: list[Participant]) -> None:
        self.participants = participants
        self.decision_log: dict[str, str] = {}  # élesben tartós (fsync-elt) napló

    def run(self, tx: str) -> str:
        votes = []
        for p in self.participants:  # 1. fázis: szavazás
            try:
                votes.append(p.prepare(tx))
            except TimeoutError:
                votes.append(Vote.NO)  # időtúllépés = nem
        decision = "commit" if all(v is Vote.YES for v in votes) else "abort"
        self.decision_log[tx] = decision  # a döntést a kiküldés ELŐTT kell tartósan rögzíteni
        for p in self.participants:  # 2. fázis: kihirdetés (élesben nyugtáig újrapróbálva)
            if decision == "commit":
                p.commit(tx)
            elif p.state == "prepared":
                p.abort(tx)
        return decision

if __name__ == "__main__":
    ok = Coordinator([Participant("orders-db"), Participant("payments-db")])
    print(ok.run("tx-1"), [p.state for p in ok.participants])
    bad = Coordinator([Participant("orders-db"), Participant("payments-db", will_fail=True)])
    print(bad.run("tx-2"), [p.state for p in bad.participants])
```

## Saga minta: hosszú üzleti tranzakciók kompenzációval
<!-- q: Hogyan kezeljek tranzakciót több mikroszolgáltatás között 2PC nélkül? -->
<!-- tags: saga, compensating transaction, orchestration, choreography, microservices, eventual consistency -->

A saga egy üzleti folyamatot helyi tranzakciók sorozatára bont (minden szolgáltatás a saját
adatbázisában commitol), és hiba esetén a már lefutott lépéseket kompenzáló műveletekkel
(visszatérítés, foglalás feloldása) vonja vissza fordított sorrendben. Orkesztrált változatban
egy központi koordinátor vezérel (átlátható, jól monitorozható), koreografáltban a
szolgáltatások egymás eseményeire reagálnak (laza csatolás, de nehezen követhető). Buktatók:
nincs izoláció — a köztes állapot látható (ezért kellenek „függőben” állapotok); a
kompenzációknak idempotensnek és újrapróbálhatónak kell lenniük; a saga állapotát tartósan kell
tárolni (pl. Temporal, AWS Step Functions).

```python
from dataclasses import dataclass
from typing import Callable

@dataclass
class Step:
    name: str
    action: Callable[[dict], None]
    compensate: Callable[[dict], None]  # szemantikus visszavonás, nem adatbázis-rollback

class SagaFailed(Exception):
    pass

def run_saga(steps: list[Step], ctx: dict) -> None:
    """Orkesztrált saga: hiba esetén a kész lépések kompenzálása fordított sorrendben."""
    done: list[Step] = []
    log = ctx.setdefault("log", [])
    for step in steps:
        try:
            step.action(ctx)
            done.append(step)
            log.append(f"OK {step.name}")
        except Exception as e:
            log.append(f"HIBA {step.name}: {e}")
            for prev in reversed(done):
                try:
                    prev.compensate(ctx)  # idempotens kell legyen: újrapróbálható
                    log.append(f"KOMPENZÁLVA {prev.name}")
                except Exception as ce:  # élesben újrapróbálási sor / kézi beavatkozás
                    log.append(f"KOMPENZÁCIÓ SIKERTELEN {prev.name}: {ce}")
            raise SagaFailed(step.name) from e

# Élesben mindegyik lépés egy-egy külön szolgáltatás hívása
def reserve_stock(c: dict) -> None: c["stock_reserved"] = True
def release_stock(c: dict) -> None: c["stock_reserved"] = False
def refund_card(c: dict) -> None: c["charged"] = False
def schedule_delivery(c: dict) -> None: c["delivery"] = "ütemezve"
def cancel_delivery(c: dict) -> None: c["delivery"] = None

def charge_card(c: dict) -> None:
    if c["amount"] > c["card_limit"]:
        raise RuntimeError("kártya elutasítva")
    c["charged"] = True

ORDER_SAGA = [
    Step("készletfoglalás", reserve_stock, release_stock),
    Step("terhelés", charge_card, refund_card),
    Step("szállítás", schedule_delivery, cancel_delivery),
]

if __name__ == "__main__":
    for limit in (50_000, 1_000):
        ctx: dict = {"amount": 12_000, "card_limit": limit}
        try:
            run_saga(ORDER_SAGA, ctx)
        except SagaFailed as e:
            print("sikertelen lépés:", e)
        print(ctx["log"], "készlet foglalva:", ctx.get("stock_reserved"))
```

## Idempotencia és az „exactly-once” mítosza
<!-- q: Lehetséges-e a pontosan egyszeri kézbesítés, és hogyan tegyem idempotenssé az API-t? -->
<!-- tags: idempotency, idempotency key, exactly-once, at-least-once, deduplication, retries -->

Megbízhatatlan hálózaton a pontosan egyszeri kézbesítés nem garantálható: ha nem jön válasz,
a küldő nem tudhatja, hogy az üzenet vagy a nyugta veszett-e el (két hadvezér problémája). Ami
elérhető: legalább egyszeri kézbesítés + idempotens feldolgozás = „ténylegesen egyszeri”
hatás. Idempotens a művelet, ha többszöri végrehajtása ugyanazt eredményezi, mint az egyszeri
(SET igen, INCREMENT nem). API-knál a kliens egyedi idempotencia-kulcsot küld, a szerver
atomikusan lefoglalja, és ismétléskor a tárolt választ adja vissza; a Kafka „exactly-once”
garanciája is csak a Kafkán belüli olvasás–feldolgozás–írás láncra vonatkozik.

```typescript
type Stored =
  | { state: "in_progress"; fingerprint: string }
  | { state: "done"; fingerprint: string; status: number; body: unknown };

interface KeyStore {
  // Atomikus "beállít, ha nincs": Redis SET NX EX, SQL INSERT ... ON CONFLICT DO NOTHING
  putIfAbsent(key: string, value: Stored, ttlSec: number): Promise<boolean>;
  get(key: string): Promise<Stored | undefined>;
  set(key: string, value: Stored, ttlSec: number): Promise<void>;
  delete(key: string): Promise<void>;
}

class MemoryKeyStore implements KeyStore {
  private m = new Map<string, Stored>();
  async putIfAbsent(k: string, v: Stored) { if (this.m.has(k)) return false; this.m.set(k, v); return true; }
  async get(k: string) { return this.m.get(k); }
  async set(k: string, v: Stored) { this.m.set(k, v); }
  async delete(k: string) { this.m.delete(k); }
}

export async function idempotent(
  store: KeyStore,
  key: string | undefined,
  requestBody: unknown,
  handler: () => Promise<{ status: number; body: unknown }>,
): Promise<{ status: number; body: unknown }> {
  if (!key) return { status: 400, body: { error: "Idempotency-Key fejléc kötelező" } };
  const fingerprint = JSON.stringify(requestBody); // élesben a törzs hash-e
  const TTL = 24 * 3600;
  if (!(await store.putIfAbsent(key, { state: "in_progress", fingerprint }, TTL))) {
    const prev = (await store.get(key))!;
    if (prev.fingerprint !== fingerprint) {
      return { status: 422, body: { error: "ugyanaz a kulcs eltérő kéréssel" } };
    }
    if (prev.state === "in_progress") {
      return { status: 409, body: { error: "a kérés még feldolgozás alatt" } }; // párhuzamos ismétlés
    }
    return { status: prev.status, body: prev.body }; // a tárolt válasz visszajátszása
  }
  try {
    const res = await handler();
    await store.set(key, { state: "done", fingerprint, ...res }, TTL);
    return res;
  } catch (e) {
    await store.delete(key); // nem tudni, mi történt: engedjük az újrapróbálást
    throw e;
  }
}

// A kliens hálózati hiba után UGYANAZZAL a kulccsal próbálkozik újra => egyetlen terhelés
const store = new MemoryKeyStore();
let charges = 0;
const pay = () =>
  idempotent(store, "c0ffee-0001", { amount: 4990 }, async () => {
    charges++;
    return { status: 201, body: { paymentId: "p_1" } };
  });
(async () => {
  console.log(await pay(), await pay(), "terhelések száma:", charges); // ... 1
})();
```

## Üzenetsorok: Kafka és RabbitMQ szemantikája
<!-- q: Mi a különbség a Kafka és a RabbitMQ között, és hogyan érjek el legalább egyszeri feldolgozást? -->
<!-- tags: kafka, rabbitmq, message queue, consumer group, offset commit, at-least-once, dead letter -->

A Kafka particionált, csak hozzáfűzhető napló: az üzenetek a megőrzési ideig megmaradnak, a
fogyasztói csoportok a saját offsetjüket követik (visszajátszás lehetséges), a sorrend csak
partíción belül garantált, ezért az összetartozó eseményeket azonos kulccsal kell küldeni. A
RabbitMQ klasszikus broker: exchange-ek irányítják az üzeneteket sorokba, a nyugtázott üzenet
törlődik, üzenetenkénti ack, prefetch és dead-letter sor van. Szemantika: ha a feldolgozás
ELŐTT nyugtázunk/commitolunk, legfeljebb egyszeri (vesztés lehet), ha UTÁNA, legalább egyszeri
(duplikátum lehet) — ezért a fogyasztó legyen idempotens. Az adatbázis-írás és az üzenetküldés
atomicitására a transactional outbox minta való.

```python
# Kafka fogyasztó legalább egyszeri szemantikával és idempotens feldolgozással
# (confluent-kafka kliens; a broker címe és a téma neve példa).
import json
import sqlite3

from confluent_kafka import Consumer, KafkaException

db = sqlite3.connect("orders.db", isolation_level=None)
db.execute("CREATE TABLE IF NOT EXISTS processed(event_id TEXT PRIMARY KEY)")
db.execute("CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY, total INTEGER)")

consumer = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": "order-projector",  # azonos csoport: a partíciók megoszlanak a példányok között
    "enable.auto.commit": False,  # KÉZI commit, csak sikeres feldolgozás után
    "auto.offset.reset": "earliest",
    "max.poll.interval.ms": 300_000,  # ennél lassabb feldolgozás => rebalance
})
consumer.subscribe(["orders.v1"])

def handle(event: dict) -> None:
    """Deduplikáció és hatás EGY tranzakcióban: az ismételt esemény nem fut le kétszer."""
    db.execute("BEGIN")
    try:
        cur = db.execute("INSERT OR IGNORE INTO processed(event_id) VALUES (?)", (event["event_id"],))
        if cur.rowcount == 1:  # először látjuk
            db.execute("INSERT OR REPLACE INTO orders(id, total) VALUES (?, ?)",
                       (event["order_id"], event["total"]))
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise

try:
    while True:
        msg = consumer.poll(timeout=1.0)
        if msg is None:
            continue
        if msg.error():
            raise KafkaException(msg.error())
        try:
            handle(json.loads(msg.value()))
        except (ValueError, KeyError) as e:
            # "Méregüzenet": ne akassza meg a partíciót — élesben dead-letter témába küldjük
            print(f"hibás üzenet offset={msg.offset()}: {e}")
        # Commit a feldolgozás UTÁN => at-least-once; előtte => at-most-once
        consumer.commit(message=msg, asynchronous=False)
finally:
    consumer.close()  # tiszta kilépés: gyors rebalance
```

## Logikai órák: Lamport- és vektoróra
<!-- q: Miért nem bízhatok a fizikai órákban, és hogyan működik a Lamport- és a vektoróra? -->
<!-- tags: lamport clock, vector clock, logical time, causality, happens-before, concurrency detection -->

A fizikai órák csúsznak, az NTP-szinkron pontatlan és ugrálhat, ezért időbélyegből nem
dönthető el megbízhatóan két esemény sorrendje különböző gépeken. A Lamport-óra egy számláló,
amit minden eseménynél növelünk, üzenetfogadáskor pedig a nagyobb értékre ugrunk: ha a okozza
b-t, L(a) < L(b), de fordítva nem igaz, így az egyidejűséget nem ismeri fel. A vektoróra
csomópontonként egy számlálót tart, és pontosan megmondja, hogy két esemény okozati viszonyban
áll vagy egyidejű (ütközés) — a Dynamo-stílusú adatbázisok ezt használják. Hátrány: mérete a
résztvevők számával nő; modern alternatíva a hibrid logikai óra (HLC, CockroachDB) és a
Spanner TrueTime.

```python
from dataclasses import dataclass, field

class LamportClock:
    """Ha a -> b (okozatiság), akkor L(a) < L(b). Fordítva NEM igaz."""

    def __init__(self) -> None:
        self.t = 0

    def tick(self) -> int:  # helyi esemény vagy küldés
        self.t += 1
        return self.t

    def receive(self, remote: int) -> int:  # fogadáskor a nagyobbat követjük
        self.t = max(self.t, remote) + 1
        return self.t

@dataclass
class VectorClock:
    node: str
    v: dict[str, int] = field(default_factory=dict)

    def tick(self) -> dict[str, int]:
        self.v[self.node] = self.v.get(self.node, 0) + 1
        return dict(self.v)  # másolat megy az üzenetbe

    def receive(self, remote: dict[str, int]) -> None:
        for n, t in remote.items():
            self.v[n] = max(self.v.get(n, 0), t)  # elemenkénti maximum
        self.tick()

def compare(a: dict[str, int], b: dict[str, int]) -> str:
    keys = a.keys() | b.keys()
    le = all(a.get(k, 0) <= b.get(k, 0) for k in keys)
    ge = all(a.get(k, 0) >= b.get(k, 0) for k in keys)
    if le and ge:
        return "egyenlő"
    if le:
        return "a megelőzi b-t"
    if ge:
        return "b megelőzi a-t"
    return "egyidejű (ütközés!)"  # Lamport-órával ez nem lenne felismerhető

if __name__ == "__main__":
    A, B, C = VectorClock("A"), VectorClock("B"), VectorClock("C")
    m1 = A.tick()  # A ír, és elküldi B-nek
    B.receive(m1)
    b_write = B.tick()  # B az A írását látva módosít
    c_write = C.tick()  # C tőlük függetlenül, egyidejűleg módosít
    print(compare(m1, b_write))  # a megelőzi b-t
    print(compare(b_write, c_write))  # egyidejű (ütközés!)
    la, lb = LamportClock(), LamportClock()
    print(la.tick(), lb.receive(la.t), lb.tick())  # 1 2 3
```

## Elosztott rate limiting token buckettel
<!-- q: Hogyan korlátozzam a kérések számát több szerverpéldány között? -->
<!-- tags: rate limiting, token bucket, redis, lua, distributed, throttling, 429 -->

A token bucket kapacitásnyi tokent tárol, amit állandó ütemben tölt újra; minden kérés elvesz
egyet, üres vödörnél a kérés elutasítást kap (HTTP 429 + Retry-After). Megengedi a kapacitásnyi
löketet, de hosszú távon az utántöltési ütemet tartja; a leaky bucket ezzel szemben egyenletes
kimenetet ad, a fix ablak pedig az ablakhatáron dupla löketet enged át. Több alkalmazáspéldány
esetén az állapotnak közös tárolóban kell lennie, és a „kiolvas–számol–visszaír” lépésnek
atomikusnak — Redisben ezt egy Lua-szkript biztosítja. Döntsd el előre, mi legyen, ha a Redis
nem elérhető (fail-open vagy fail-closed), és az órákat egy forrásból (pl. Redis TIME) vedd.

```python
import time

import redis

# A Lua-szkript ATOMIKUSAN fut a Redis szerveren: nincs versenyhelyzet a példányok között
TOKEN_BUCKET_LUA = """
local key      = KEYS[1]
local capacity = tonumber(ARGV[1])   -- vödörméret (megengedett löket)
local rate     = tonumber(ARGV[2])   -- utántöltés: token / másodperc
local now      = tonumber(ARGV[3])   -- idő ms-ban
local cost     = tonumber(ARGV[4])

local state  = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(state[1]) or capacity
local ts     = tonumber(state[2]) or now

-- lusta utántöltés az eltelt idő arányában, a kapacitásig
tokens = math.min(capacity, tokens + math.max(0, now - ts) / 1000 * rate)
local allowed = 0
if tokens >= cost then
  tokens = tokens - cost
  allowed = 1
end
redis.call('HSET', key, 'tokens', tokens, 'ts', now)
redis.call('PEXPIRE', key, math.ceil(capacity / rate * 1000) + 1000)  -- inaktív kulcs lejár
local wait_ms = 0
if allowed == 0 then wait_ms = math.ceil((cost - tokens) / rate * 1000) end
return {allowed, wait_ms}
"""

class DistributedRateLimiter:
    def __init__(self, r: redis.Redis, capacity: int, rate_per_s: float) -> None:
        self.script = r.register_script(TOKEN_BUCKET_LUA)  # EVALSHA, szükség esetén újratölt
        self.capacity, self.rate = capacity, rate_per_s

    def allow(self, client_id: str, cost: int = 1) -> tuple[bool, int]:
        now_ms = int(time.time() * 1000)
        allowed, wait_ms = self.script(keys=[f"rl:{client_id}"], args=[self.capacity, self.rate, now_ms, cost])
        return bool(allowed), int(wait_ms)

if __name__ == "__main__":
    limiter = DistributedRateLimiter(redis.Redis(host="localhost", port=6379), capacity=10, rate_per_s=5)
    for i in range(15):
        ok, wait = limiter.allow("client-123")
        print(i, "OK" if ok else f"429, próbáld újra {wait} ms múlva")
```

## Circuit breaker (áramkör-megszakító)
<!-- q: Mi az a circuit breaker, és hogyan védi meg a rendszert a kaszkádhibáktól? -->
<!-- tags: circuit breaker, resilience, fault tolerance, fallback, cascading failure, half-open -->

Ha egy függőség tartósan hibázik vagy lassú, a hívók szálai és kapcsolatai rá várva elfogynak,
és a hiba továbbterjed (kaszkád). Az áramkör-megszakító CLOSED állapotban átengedi a hívásokat
és számolja a hibákat; küszöb felett OPEN állapotba vált, ilyenkor azonnal hibát vagy
tartalék (fallback) választ ad, így a beteg szolgáltatás tehermentesül. A türelmi idő után
HALF_OPEN állapotban néhány próbahívást enged: siker esetén visszazár, hiba esetén újranyit.
Mindig időkorláttal együtt használd, függőségenként külön példánnyal; éles könyvtárak
(resilience4j, Polly) csúszóablakos hibaarányt figyelnek.

```typescript
type State = "CLOSED" | "OPEN" | "HALF_OPEN";
export class CircuitOpenError extends Error {}

interface BreakerOptions { failureThreshold: number; resetTimeoutMs: number; halfOpenMax: number; callTimeoutMs: number; }

export class CircuitBreaker {
  private state: State = "CLOSED";
  private failures = 0;
  private openedAt = 0;
  private probes = 0; // folyamatban lévő próbahívások HALF_OPEN állapotban

  constructor(private readonly opts: BreakerOptions) {}

  async call<T>(fn: () => Promise<T>, fallback?: () => T): Promise<T> {
    if (this.state === "OPEN") {
      if (Date.now() - this.openedAt < this.opts.resetTimeoutMs) {
        if (fallback) return fallback(); // gyors hiba helyett degradált válasz
        throw new CircuitOpenError("áramkör nyitva");
      }
      this.state = "HALF_OPEN"; // lejárt a türelmi idő: próbálkozhatunk
    }
    const probe = this.state === "HALF_OPEN";
    if (probe && this.probes >= this.opts.halfOpenMax) {
      if (fallback) return fallback();
      throw new CircuitOpenError("félig nyitva: próbahívás folyamatban");
    }
    if (probe) this.probes++;
    try {
      const result = await this.withTimeout(fn()); // időkorlát nélkül a lassú hívás "beragad"
      this.failures = 0;
      this.state = "CLOSED";
      return result;
    } catch (e) {
      this.failures++;
      if (probe || this.failures >= this.opts.failureThreshold) {
        this.state = "OPEN"; // nyitás vagy újranyitás
        this.openedAt = Date.now();
      }
      if (fallback) return fallback();
      throw e;
    } finally {
      if (probe) this.probes--;
    }
  }

  private withTimeout<T>(p: Promise<T>): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      const t = setTimeout(() => reject(new Error("időtúllépés")), this.opts.callTimeoutMs);
      p.then((v) => { clearTimeout(t); resolve(v); }, (e) => { clearTimeout(t); reject(e); });
    });
  }

  get status(): State { return this.state; }
}

// Függőségenként egy példány
const breaker = new CircuitBreaker({ failureThreshold: 3, resetTimeoutMs: 5_000, halfOpenMax: 1, callTimeoutMs: 1_000 });
async function getRecommendations(userId: string): Promise<string[]> {
  return breaker.call(
    async () => { throw new Error(`ajánló szolgáltatás nem elérhető (${userId})`); },
    () => ["népszerű-1", "népszerű-2"], // tartalék: általános ajánlat
  );
}
(async () => {
  for (let i = 0; i < 4; i++) console.log(await getRecommendations("u1"), breaker.status);
})();
```

## Újrapróbálás exponenciális visszalépéssel és jitterrel
<!-- q: Hogyan próbáljak újra helyesen egy sikertelen hálózati hívást? -->
<!-- tags: retry, exponential backoff, jitter, thundering herd, transient errors, deadline -->

Csak átmeneti hibát érdemes újrapróbálni (időtúllépés, kapcsolati hiba, 429, 503), végleges
hibát (400, 404, validáció) soha. A várakozás exponenciálisan nő felső korláttal, és véletlen
szórást (jitter) kap — enélkül a sok kliens egyszerre próbálkozna újra („thundering herd”), és
újra ledöntené az épp magához térő szolgáltatást; a „full jitter” (0 és a határ közötti
egyenletes véletlen) a legjobb terheléselosztást adja. Szabályok: csak idempotens műveletet
próbálj újra automatikusan; a teljes határidőt (deadline) a hívó szabja meg és adja tovább;
csak egy rétegben próbálkozz újra, mert rétegenkénti 3 próba 3 rétegen 27-szeres terhelést okoz;
vedd figyelembe a Retry-After fejlécet.

```go
package retry

import (
	"context"
	"errors"
	"math/rand"
	"net/http"
	"time"
)

// RetryableError jelöli az átmeneti hibákat; minden más végleges
type RetryableError struct{ Err error }

func (e RetryableError) Error() string { return e.Err.Error() }
func (e RetryableError) Unwrap() error { return e.Err }

type Policy struct {
	MaxAttempts int
	Base, Cap   time.Duration // első várakozás alapja és felső korlátja
}

// Do: sleep = random(0, min(Cap, Base * 2^attempt)) — "full jitter"
func Do(ctx context.Context, p Policy, op func(ctx context.Context) error) error {
	var err error
	for attempt := 0; attempt < p.MaxAttempts; attempt++ {
		if err = op(ctx); err == nil {
			return nil
		}
		var re RetryableError
		if !errors.As(err, &re) || attempt == p.MaxAttempts-1 {
			return err // végleges hiba, vagy elfogytak a próbák
		}
		backoff := p.Base << attempt
		if backoff > p.Cap || backoff <= 0 { // <= 0: túlcsordulás elleni védelem
			backoff = p.Cap
		}
		select {
		case <-time.After(time.Duration(rand.Int63n(int64(backoff) + 1))):
		case <-ctx.Done(): // a teljes határidőt a hívó szabja meg
			return errors.Join(ctx.Err(), err)
		}
	}
	return err
}

// FetchStatus: CSAK idempotens kérés (GET) automatikus újrapróbálása
func FetchStatus(ctx context.Context, c *http.Client, url string) error {
	policy := Policy{MaxAttempts: 5, Base: 100 * time.Millisecond, Cap: 5 * time.Second}
	return Do(ctx, policy, func(ctx context.Context) error {
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
		if err != nil {
			return err
		}
		resp, err := c.Do(req)
		if err != nil {
			return RetryableError{err} // hálózati hiba: valószínűleg átmeneti
		}
		defer resp.Body.Close()
		switch {
		case resp.StatusCode == 408 || resp.StatusCode == 429 || resp.StatusCode >= 500:
			return RetryableError{errors.New(resp.Status)}
		case resp.StatusCode >= 400:
			return errors.New(resp.Status) // kliens hiba: újrapróbálni értelmetlen
		}
		return nil
	})
}
```

## Service discovery és egészség-ellenőrzés
<!-- q: Hogyan találják meg egymást a szolgáltatások, és hogyan kerülnek ki a hibás példányok? -->
<!-- tags: service discovery, service registry, health check, heartbeat, ttl, load balancing, consul -->

Dinamikus környezetben (konténerek, autoskálázás) a példányok címe folyamatosan változik, ezért
egy szolgáltatásjegyzék (Consul, etcd, Kubernetes Service/Endpoints, Eureka) tartja nyilván az
élő példányokat. A példány induláskor regisztrál, rendszeresen heartbeatet küld (vagy a
jegyzék ellenőrzi), a TTL lejártával kikerül; leálláskor kijelentkezik. A kliensoldali
felderítésnél a kliens kérdezi le a jegyzéket (gyorsítótárazva) és maga osztja el a terhelést;
szerveroldalinál egy load balancer, DNS vagy service mesh (Envoy sidecar) végzi. Buktató: a
liveness (él-e) és a readiness (fogadhat-e forgalmat) ellenőrzés nem ugyanaz.

```python
import itertools
import random
import threading
import time
from dataclasses import dataclass, field

@dataclass
class Instance:
    service: str
    instance_id: str
    address: str
    last_heartbeat: float = field(default_factory=time.monotonic)

class Registry:
    """Jegyzék TTL-alapú egészség-ellenőrzéssel (mint a Consul TTL check / etcd lease)."""

    def __init__(self, ttl_s: float = 3.0) -> None:
        self.ttl = ttl_s
        self._lock = threading.Lock()
        self._items: dict[str, Instance] = {}

    def register(self, inst: Instance) -> None:
        with self._lock:
            self._items[inst.instance_id] = inst

    def heartbeat(self, instance_id: str) -> None:
        with self._lock:
            if instance_id in self._items:
                self._items[instance_id].last_heartbeat = time.monotonic()

    def deregister(self, instance_id: str) -> None:  # tiszta leállításkor
        with self._lock:
            self._items.pop(instance_id, None)

    def healthy(self, service: str) -> list[Instance]:
        now = time.monotonic()
        with self._lock:
            return [i for i in self._items.values() if i.service == service and now - i.last_heartbeat < self.ttl]

class ClientSideBalancer:
    """Kliensoldali felderítés + round-robin, gyorsítótárazott jegyzéklistával."""

    def __init__(self, registry: Registry, service: str, refresh_s: float = 1.0) -> None:
        self.registry, self.service, self.refresh_s = registry, service, refresh_s
        self._cache: list[Instance] = []
        self._fetched = 0.0
        self._rr = itertools.count()

    def pick(self) -> Instance:
        if time.monotonic() - self._fetched > self.refresh_s:  # nem kérdezzük minden hívásnál
            self._cache = self.registry.healthy(self.service)
            random.shuffle(self._cache)  # ne minden kliens ugyanazzal a példánnyal kezdjen
            self._fetched = time.monotonic()
        if not self._cache:
            raise LookupError(f"nincs egészséges '{self.service}' példány")
        return self._cache[next(self._rr) % len(self._cache)]

if __name__ == "__main__":
    reg = Registry(ttl_s=0.5)
    for n in range(3):
        reg.register(Instance("payments", f"pay-{n}", f"10.0.0.{10 + n}:8080"))
    lb = ClientSideBalancer(reg, "payments", refresh_s=0.1)
    print([lb.pick().address for _ in range(4)])
    time.sleep(0.6)  # senki sem küld heartbeatet...
    reg.heartbeat("pay-1")  # ...csak a pay-1
    time.sleep(0.15)
    print([lb.pick().address for _ in range(3)])  # csak 10.0.0.11
```

## Megfigyelhetőség: logok, metrikák, trace-ek
<!-- q: Hogyan tegyem megfigyelhetővé az elosztott rendszert logokkal, metrikákkal és trace-ekkel? -->
<!-- tags: observability, logging, metrics, tracing, opentelemetry, prometheus, structured logging -->

A három pillér más-más kérdésre felel: a metrikák olcsó, aggregált idősorok riasztáshoz és
trendekhez (RED: rate, errors, duration; USE: utilization, saturation, errors); a logok
részletes, diszkrét események a „mi történt pontosan” kérdésre; a trace-ek egy kérés útját
mutatják szolgáltatásokon át, span-fában, a késleltetés lebontásával. A trace-kontextust a
W3C `traceparent` fejléc viszi tovább, a logokba írt trace_id köti össze a pilléreket. Buktatók:
metrikacímkébe soha ne kerüljön nagy kardinalitású érték (user_id, teljes URL), a logokba ne
kerüljön személyes adat vagy titok, a trace-eket pedig nagy forgalomnál mintavételezni kell.

```python
import json
import logging
import time

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from prometheus_client import Counter, Histogram, start_http_server

# TRACE: span-fa közös trace_id-vel (élesben OTLP exporter a collector felé)
provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("checkout-service")

# METRIKÁK: alacsony kardinalitású címkék!
REQUESTS = Counter("checkout_requests_total", "Checkout kérések", ["outcome"])
LATENCY = Histogram("checkout_duration_seconds", "Checkout időtartam", buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5))

class JsonFormatter(logging.Formatter):
    """Strukturált JSON log, trace_id-vel a pillérek összekötéséhez."""

    def format(self, record: logging.LogRecord) -> str:
        ctx = trace.get_current_span().get_span_context()
        return json.dumps({
            "ts": round(record.created, 3),
            "level": record.levelname,
            "msg": record.getMessage(),
            "trace_id": format(ctx.trace_id, "032x") if ctx.is_valid else None,
            **getattr(record, "fields", {}),
        }, ensure_ascii=False)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
log = logging.getLogger("checkout")
log.addHandler(handler)
log.setLevel(logging.INFO)

def charge(amount: int) -> None:
    with tracer.start_as_current_span("payment.charge") as span:  # gyerek span
        span.set_attribute("payment.amount", amount)
        time.sleep(0.05)  # külső hívás helyett

def checkout(order_id: str, amount: int) -> None:
    start = time.perf_counter()
    with tracer.start_as_current_span("checkout") as span:  # gyökér span
        span.set_attribute("order.id", order_id)  # span-attribútumban lehet nagy kardinalitás
        try:
            charge(amount)
            log.info("rendelés fizetve", extra={"fields": {"order_id": order_id}})  # kártyaadat SOHA
            REQUESTS.labels(outcome="ok").inc()
        except Exception as e:
            span.record_exception(e)
            REQUESTS.labels(outcome="error").inc()
            log.error("fizetés sikertelen", extra={"fields": {"order_id": order_id}})
            raise
        finally:
            LATENCY.observe(time.perf_counter() - start)

if __name__ == "__main__":
    start_http_server(9100)  # /metrics végpont a Prometheusnak
    checkout("ord-1001", 4990)
    provider.shutdown()  # a pufferelt spanek kiírása kilépés előtt
```
