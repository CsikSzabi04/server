# Hálózat, HTTP és API-k
<!-- tech: networking -->
<!-- aliases: hálózat, networking, http, tcp, udp, tls, dns, rest, api, websocket, oauth -->

A hálózati programozás alapjai a szállítási rétegtől az alkalmazás-API-kig: a TCP és UDP
működése, a keretezés, a TLS-kézfogás, a DNS, a HTTP verziói és gyorsítótárazása, a REST-,
GraphQL- és gRPC-tervezés, a valós idejű csatornák (WebSocket, SSE), a böngészős biztonsági
határok (CORS), a hitelesítés (session, JWT, OAuth2/OIDC), valamint a lapozás, verziózás, rate
limiting és a helyes HTTP-kliens használat. A példák Python, TypeScript és Go nyelven készültek.

## TCP/IP modell, TCP vs. UDP
<!-- q: Mi a különbség a TCP és az UDP között, és mikor melyiket használjam? -->
<!-- tags: tcp, udp, tcp/ip, transport layer, datagram, socket, reliability -->

A TCP/IP rétegei: kapcsolati réteg (Ethernet, Wi-Fi), hálózati réteg (IP: címzés, útválasztás,
„best effort” kézbesítés), szállítási réteg (TCP/UDP: portok) és alkalmazási réteg (HTTP, DNS).
A TCP kapcsolatorientált, megbízható, sorrendtartó bájtfolyamot ad újraküldéssel, folyam- és
torlódásvezérléssel; az UDP kapcsolat nélküli datagramokat küld garancia nélkül, de nincs
kézfogás és fej-blokkolás, az üzenethatárok pedig megmaradnak. UDP-t ott érdemes választani,
ahol a késés fontosabb a tökéletességnél, vagy a megbízhatóságot az alkalmazás maga oldja meg
(DNS, VoIP, játékok, QUIC/HTTP/3) — ilyenkor az időkorlátot és az újraküldést nekünk kell
megírni.

```python
import socket
import threading
import time

def udp_server(host: str = "127.0.0.1", port: int = 9999) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((host, port))
        while True:
            data, addr = s.recvfrom(65535)  # egy recvfrom = pontosan egy datagram
            if data == b"STOP":
                break
            s.sendto(b"pong:" + data, addr)  # válasz a küldő címére

def udp_request(msg: bytes, addr=("127.0.0.1", 9999), retries: int = 3, timeout: float = 0.5) -> bytes:
    """Kérés-válasz UDP felett: az elveszett csomagot nekünk kell újraküldeni."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        for attempt in range(retries):
            s.sendto(msg, addr)
            try:
                data, _ = s.recvfrom(65535)
                return data
            except socket.timeout:
                print(f"időtúllépés, újraküldés ({attempt + 1}/{retries})")
        raise TimeoutError("nincs válasz")

if __name__ == "__main__":
    threading.Thread(target=udp_server, daemon=True).start()
    time.sleep(0.1)
    print(udp_request(b"ping-1"))
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(b"STOP", ("127.0.0.1", 9999))
```

## TCP belülről: kézfogás, vezérlés és üzenetkeretezés
<!-- q: Hogyan működik a TCP kapcsolat, és miért kell saját üzenetkeretezés? -->
<!-- tags: tcp handshake, framing, length prefix, nagle, keepalive, time_wait, flow control, congestion control -->

A TCP-kapcsolat háromutas kézfogással (SYN, SYN-ACK, ACK — 1 RTT) indul; a sorszámok és
nyugták alapján a vesztett szegmenseket újraküldi, a vevő ablaka szabja meg, mennyit küldhet a
másik fél (flow control), a torlódásvezérlés (slow start, CUBIC, BBR) pedig a hálózat
kapacitásához igazítja a sebességet. A TCP bájtfolyam: egy send() több recv()-re eshet szét, és
több send() egyetlen recv()-ben érkezhet — ezért saját keretezés kell (hossz-előtag vagy
elválasztó). Gyakori buktatók: a Nagle-algoritmus és a késleltetett ACK együtt kis üzeneteknél
40 ms-os késést okoz (TCP_NODELAY), az aktívan záró fél TIME_WAIT állapotba kerül, és időkorlát
nélkül egy recv() örökre blokkolhat.

```python
import socket
import struct

def send_msg(sock: socket.socket, payload: bytes) -> None:
    # 4 bájtos, hálózati bájtsorrendű (big-endian) hossz-előtag + adat
    sock.sendall(struct.pack("!I", len(payload)) + payload)  # sendall: mindent elküld

def recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:  # 0 bájt = a másik fél lezárta a kapcsolatot
            raise ConnectionError("a kapcsolat idő előtt lezárult")
        buf += chunk
    return bytes(buf)

def recv_msg(sock: socket.socket, max_len: int = 16 * 1024 * 1024) -> bytes:
    (length,) = struct.unpack("!I", recv_exact(sock, 4))
    if length > max_len:  # a támadó ne kérhessen 4 GB-os puffert
        raise ValueError(f"túl nagy üzenet: {length}")
    return recv_exact(sock, length)

def connect(host: str, port: int) -> socket.socket:
    # create_connection: DNS-feloldás, IPv6/IPv4 próbálgatás, kapcsolódási időkorlát
    s = socket.create_connection((host, port), timeout=5)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # kis üzenetek azonnal mennek
    s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)  # félig nyitott kapcsolatok felismerése
    s.settimeout(10)  # olvasási/írási időkorlát
    return s

if __name__ == "__main__":
    a, b = socket.socketpair()  # két összekötött végpont, szerver nélkül
    send_msg(a, "első üzenet".encode())
    send_msg(a, b"masodik")
    print(recv_msg(b).decode(), recv_msg(b))  # az üzenethatárok megmaradnak
```

## TLS-kézfogás és tanúsítvány-ellenőrzés
<!-- q: Hogyan működik a TLS kézfogás, és hogyan kapcsolódjak biztonságosan TLS-sel? -->
<!-- tags: tls, ssl, https, handshake, certificate, sni, alpn, forward secrecy -->

TLS 1.3-ban a kliens a ClientHello-ban elküldi a támogatott titkosítókat, egy ideiglenes
(ECDHE) kulcsrészt, az SNI-t (melyik hosztot kéri) és az ALPN-t (h2 vagy http/1.1); a szerver
saját kulcsrészével válaszol, onnantól minden titkosított: elküldi a tanúsítványláncát és egy
aláírást, ami bizonyítja a privát kulcs birtoklását — mindez 1 RTT. Az ideiglenes kulcscsere
előre titkosságot (forward secrecy) ad, a tanúsítvány a szervert hitelesíti, az adatot AEAD
titkosító (AES-GCM, ChaCha20-Poly1305) védi. Buktatók: a tanúsítvány- és hosztnév-ellenőrzés
kikapcsolása (CERT_NONE, verify=False) közbeékelődéses támadást tesz lehetővé, és a szervernek
a teljes láncot (leaf + intermediate) kell küldenie.

```python
import socket
import ssl

def tls_info(host: str, port: int = 443) -> dict:
    # Alapértelmezett kontextus: CA-lánc ÉS hosztnév-ellenőrzés — élesben soha ne kapcsold ki
    ctx = ssl.create_default_context()
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2  # régi, törött protokollok tiltása
    ctx.set_alpn_protocols(["h2", "http/1.1"])
    with socket.create_connection((host, port), timeout=5) as raw:
        # server_hostname: SNI + ez alapján ellenőrzi a tanúsítvány nevét
        with ctx.wrap_socket(raw, server_hostname=host) as tls:
            cert = tls.getpeercert()
            return {
                "verzió": tls.version(),  # pl. 'TLSv1.3'
                "titkosító": tls.cipher()[0],  # pl. 'TLS_AES_256_GCM_SHA384'
                "alpn": tls.selected_alpn_protocol(),  # pl. 'h2'
                "alany": dict(x[0] for x in cert["subject"]),
                "kibocsátó": dict(x[0] for x in cert["issuer"]).get("organizationName"),
                "lejár": cert["notAfter"],
            }

def server_context(cert_file: str, key_file: str) -> ssl.SSLContext:
    """Szerveroldali kontextus modern beállításokkal."""
    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(cert_file, key_file)  # a TELJES lánc kell (leaf + intermediate)
    ctx.set_alpn_protocols(["h2", "http/1.1"])
    return ctx

if __name__ == "__main__":
    for k, v in tls_info("www.python.org").items():
        print(f"{k:>10}: {v}")
```

## DNS: névfeloldás belülről
<!-- q: Hogyan működik a DNS névfeloldás, és hogyan néz ki egy DNS-üzenet? -->
<!-- tags: dns, name resolution, a record, ttl, resolver, udp 53, nxdomain, getaddrinfo -->

A DNS hierarchikus, elosztott adatbázis: a rekurzív feloldó (ISP, 1.1.1.1, 8.8.8.8) a gyökér-,
majd a TLD-, végül a mérvadó névszervert kérdezi, és a válaszokat a TTL-ig gyorsítótárazza.
Fő rekordtípusok: A/AAAA (IPv4/IPv6), CNAME (álnév), MX (levelezés), TXT (SPF, ellenőrzések),
NS, SRV. Az üzenet jellemzően UDP 53-on megy (nagy válasznál TCP-n), DNS-over-HTTPS/TLS
titkosít, a DNSSEC aláírással hitelesít. Buktatók: a módosítás a régi TTL lejártáig nem
látszik mindenhol, a negatív válaszok is gyorsítótárazódnak, és egyes futtatókörnyezetek
(pl. régi JVM-beállítások) örökre cache-elik a feloldást; alkalmazásban a `getaddrinfo` (OS
feloldó) a helyes út.

```python
import random
import socket
import struct

def build_query(name: str, qtype: int = 1) -> tuple[int, bytes]:
    """12 bájtos fejléc + kérdés. qtype 1 = A, 28 = AAAA."""
    tid = random.randint(0, 0xFFFF)  # tranzakció-azonosító: a válaszban vissza kell jönnie
    header = struct.pack("!HHHHHH", tid, 0x0100, 1, 0, 0, 0)  # RD=1: rekurziót kérünk
    qname = b"".join(bytes([len(p)]) + p.encode("ascii") for p in name.rstrip(".").split(".")) + b"\x00"
    return tid, header + qname + struct.pack("!HH", qtype, 1)  # class IN

def skip_name(msg: bytes, i: int) -> int:
    """Név átugrása; kezeli a tömörítési mutatót (felső két bit = 11)."""
    while True:
        length = msg[i]
        if length & 0xC0 == 0xC0:
            return i + 2
        if length == 0:
            return i + 1
        i += 1 + length

def resolve_a(name: str, server: str = "1.1.1.1") -> list[tuple[str, int]]:
    tid, query = build_query(name)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(2)
        s.sendto(query, (server, 53))
        msg, _ = s.recvfrom(4096)
    rid, flags, qd, an, _, _ = struct.unpack("!HHHHHH", msg[:12])
    if rid != tid:
        raise ValueError("tranzakció-azonosító eltérés (hamisított válasz?)")
    if flags & 0x000F:
        raise LookupError(f"DNS hiba, RCODE={flags & 0xF}")  # 3 = NXDOMAIN
    i = 12
    for _ in range(qd):  # kérdés szekció átugrása (név + type + class)
        i = skip_name(msg, i) + 4
    out = []
    for _ in range(an):
        i = skip_name(msg, i)
        rtype, _, ttl, rdlen = struct.unpack("!HHIH", msg[i:i + 10])
        i += 10
        if rtype == 1 and rdlen == 4:  # A rekord (a CNAME-eket itt kihagyjuk)
            out.append((socket.inet_ntoa(msg[i:i + 4]), ttl))
        i += rdlen
    return out

if __name__ == "__main__":
    print(resolve_a("example.com"))  # [(ip, ttl), ...]
    # A gyakorlatban: getaddrinfo — OS-feloldó, cache, hosts fájl, IPv6
    print({ai[4][0] for ai in socket.getaddrinfo("example.com", 443, proto=socket.IPPROTO_TCP)})
```

## HTTP/1.1, HTTP/2 és HTTP/3
<!-- q: Mi a különbség a HTTP/1.1, a HTTP/2 és a HTTP/3 között? -->
<!-- tags: http/1.1, http/2, http/3, quic, multiplexing, head-of-line blocking, keep-alive, chunked -->

A HTTP/1.1 szöveges protokoll: keep-alive-val a kapcsolat újrahasznosítható, de egyszerre egy
kérés futhat rajta (a pipelining a gyakorlatban nem működik), ezért a böngészők hosztonként ~6
kapcsolatot nyitnak; ismeretlen hosszú törzsnél chunked kódolást használ. A HTTP/2 bináris
keretekre bont, egy TCP-kapcsolaton több párhuzamos streamet multiplexel, és tömöríti a
fejléceket (HPACK) — de csomagvesztésnél a TCP minden streamet feltart (TCP-szintű fej-blokkolás).
A HTTP/3 a QUIC-re (UDP) épül: streamenkénti vesztéskezelés, beépített TLS 1.3, gyorsabb
kapcsolatfelvétel (1-RTT, 0-RTT) és kapcsolatmigráció hálózatváltáskor (Wi-Fi → mobil).

```python
import socket
import ssl

def read_response(f) -> tuple[int, dict[str, str], bytes]:
    """HTTP/1.1 válasz olvasása: státuszsor, fejlécek CRLF-ig, majd a törzs."""
    status = int(f.readline().decode("iso-8859-1").split()[1])
    headers: dict[str, str] = {}
    while (line := f.readline()) not in (b"\r\n", b""):
        k, v = line.decode("iso-8859-1").split(":", 1)
        headers[k.strip().lower()] = v.strip()
    if headers.get("transfer-encoding") == "chunked":
        body = bytearray()
        while (size := int(f.readline().split(b";")[0], 16)) > 0:  # hexadecimális darabméret
            body += f.read(size)
            f.readline()  # a darab utáni CRLF
        f.readline()  # záró CRLF (trailer nélkül)
        return status, headers, bytes(body)
    return status, headers, f.read(int(headers.get("content-length", "0")))

def get_many(host: str, paths: list[str]) -> None:
    ctx = ssl.create_default_context()
    ctx.set_alpn_protocols(["http/1.1"])  # HTTP/2 bináris keretezésű, azt ez a kód nem értené
    with socket.create_connection((host, 443), timeout=5) as raw, \
            ctx.wrap_socket(raw, server_hostname=host) as s, s.makefile("rb") as f:
        for p in paths:
            # Ugyanazon a kapcsolaton egymás után (keep-alive): nincs új TCP+TLS kézfogás,
            # de a kérések sorban állnak — egy lassú válasz feltartja a többit
            req = f"GET {p} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: demo\r\nAccept: */*\r\n\r\n"
            s.sendall(req.encode("ascii"))
            status, headers, body = read_response(f)
            print(p, status, headers.get("content-type"), len(body), "bájt")

if __name__ == "__main__":
    get_many("example.com", ["/", "/index.html"])
```

## HTTP-gyorsítótárazás: Cache-Control és ETag
<!-- q: Hogyan használjam a Cache-Control, ETag és feltételes kérés fejléceket? -->
<!-- tags: http caching, cache-control, etag, if-none-match, 304, if-match, 412, cdn, vary -->

A Cache-Control mondja meg, ki és meddig tárolhatja a választ: `max-age` (böngésző), `s-maxage`
(CDN), `private` (csak a böngésző), `no-cache` (tárolható, de minden használat előtt
újravalidálandó), `no-store` (sehol sem tárolható — személyes adatnál), `immutable` (tartalom-
hash-elt statikus fájloknál). Az ETag a reprezentáció azonosítója: a kliens If-None-Match-csel
visszaküldi, és ha nem változott, a szerver törzs nélküli 304-et ad. Ugyanez írásnál
optimista zárolás: If-Match esetén eltérő verzióra 412 a válasz, így nem írjuk felül más
módosítását. Ha a válasz fejléctől függ (Accept-Encoding, Origin), a `Vary` fejléc kötelező.

```typescript
import { createServer } from "node:http";
import { createHash } from "node:crypto";

let product = { id: 42, name: "Kávé", price: 2490, updatedAt: "2025-01-10T08:00:00Z" };
const etagOf = (body: string) => `"${createHash("sha256").update(body).digest("base64url").slice(0, 16)}"`;

const server = createServer((req, res) => {
  if (req.url === "/products/42" && req.method === "GET") {
    const body = JSON.stringify(product);
    const etag = etagOf(body);
    // 60 mp-ig kérdezés nélkül használható, utána 30 mp-ig a régi is mehet háttér-újravalidálás mellett
    res.setHeader("Cache-Control", "public, max-age=60, stale-while-revalidate=30");
    res.setHeader("ETag", etag);
    res.setHeader("Last-Modified", new Date(product.updatedAt).toUTCString());
    if (req.headers["if-none-match"] === etag) { // élesben vesszővel elválasztott listát és W/ előtagot is kezelni kell
      res.statusCode = 304; // Not Modified: nincs törzs, megtakarított sávszélesség
      return res.end();
    }
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    return res.end(body);
  }
  if (req.url === "/products/42" && req.method === "PUT") {
    // Optimista zárolás: csak a legfrissebb verzió módosítható
    if (req.headers["if-match"] !== etagOf(JSON.stringify(product))) {
      res.statusCode = 412; // Precondition Failed: közben más módosította
      return res.end();
    }
    let raw = "";
    req.on("data", (c) => (raw += c));
    req.on("end", () => {
      try {
        const { name, price } = JSON.parse(raw); // csak engedélyezett mezők
        product = { ...product, name, price, updatedAt: new Date().toISOString() };
      } catch {
        res.statusCode = 400;
        return res.end();
      }
      res.setHeader("ETag", etagOf(JSON.stringify(product)));
      res.end(JSON.stringify(product));
    });
    return;
  }
  if (req.url === "/me") {
    res.setHeader("Cache-Control", "no-store"); // személyes adat: sehol se tárolódjon
    return res.end("{}");
  }
  res.statusCode = 404;
  res.end();
});

server.listen(8080);
```

## REST API tervezés és státuszkódok
<!-- q: Hogyan tervezzek jó REST API-t, és melyik HTTP státuszkódot mikor használjam? -->
<!-- tags: rest, api design, http methods, status codes, idempotent, fastapi, resource -->

A REST erőforrásokban gondolkodik: többes számú főnevek az URL-ben (`/orders/{id}`), a műveletet
a metódus adja. A GET biztonságos és idempotens, a PUT és DELETE idempotens, a POST nem; a PATCH
részleges módosítás. Fontos státuszkódok: 200, 201 (+ Location fejléc), 202 (aszinkron
elfogadva), 204; 304; 400 (formailag hibás), 401 (nincs hitelesítve), 403 (nincs jogosultság),
404, 409 (állapotütközés), 412, 422 (szemantikailag hibás), 429; 500, 502, 503, 504. Nem CRUD
műveletet (lemondás, jóváhagyás) al-erőforrásként vagy állapotváltásként modellezz; hibát
egységes formátumban (RFC 9457 problem+json) adj, és soha ne 200-as kóddal.

```python
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, Field

app = FastAPI(title="Orders API")

class OrderIn(BaseModel):
    product_id: str
    quantity: int = Field(gt=0, le=100)  # validálás: hibás bemenet => 422

class Order(OrderIn):
    id: str
    status: str
    created_at: datetime

class OrderPatch(BaseModel):
    quantity: int | None = Field(default=None, gt=0, le=100)

ORDERS: dict[str, Order] = {}

@app.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order(body: OrderIn, response: Response) -> Order:
    order = Order(id=str(uuid4()), status="pending", created_at=datetime.now(timezone.utc), **body.model_dump())
    ORDERS[order.id] = order
    response.headers["Location"] = f"/orders/{order.id}"  # 201 + az új erőforrás címe
    return order

@app.get("/orders/{order_id}")
def get_order(order_id: str) -> Order:
    if order_id not in ORDERS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="nincs ilyen rendelés")
    return ORDERS[order_id]

@app.patch("/orders/{order_id}")  # részleges módosítás; a PUT a teljes erőforrást cserélné
def update_order(order_id: str, patch: OrderPatch) -> Order:
    order = get_order(order_id)
    if order.status != "pending":  # formailag jó kérés, de ütközik az állapottal
        raise HTTPException(status.HTTP_409_CONFLICT, detail="feladott rendelés nem módosítható")
    updated = order.model_copy(update=patch.model_dump(exclude_unset=True))
    ORDERS[order_id] = updated
    return updated

@app.post("/orders/{order_id}/cancellation", status_code=status.HTTP_202_ACCEPTED)
def cancel_order(order_id: str) -> dict:  # nem CRUD művelet: al-erőforrás
    ORDERS[order_id] = get_order(order_id).model_copy(update={"status": "cancelling"})
    return {"status": "cancelling"}  # 202: elfogadva, aszinkron feldolgozás

@app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: str) -> None:
    ORDERS.pop(order_id, None)  # idempotens: ismételt hívásra is 204

# Futtatás: uvicorn orders:app --reload
```

## API-verziózás és kurzoros lapozás
<!-- q: Hogyan lapozzak nagy listákat hatékonyan, és hogyan verziózzam az API-t? -->
<!-- tags: pagination, cursor, keyset pagination, offset, api versioning, backward compatibility -->

Az OFFSET-alapú lapozás egyszerű, de mély lapoknál lassú (az adatbázis átolvassa az átugrott
sorokat), és ha közben új sor érkezik, elemek ugranak ki vagy duplikálódnak. A kurzoros
(keyset) lapozás az utolsó elem rendezési kulcsától folytat, indexszel O(limit) költségű és
stabil; a kurzor legyen átlátszatlan (base64), hogy szabadon változtatható legyen, és a
rendezés legyen egyértelmű (pl. created_at + id). Verziózás: csak törő változásnál kell új
verzió (mező törlése/átnevezése, típusváltás); az új, opcionális mező hozzáadása kompatibilis.
Az URL-es verzió (`/v1/`) egyszerű és cache-barát, a fejléc-alapú (`Accept`) tisztább, de
nehezebben tesztelhető.

```python
import base64
import json
import sqlite3

db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE posts(id INTEGER PRIMARY KEY, created_at TEXT, title TEXT)")
db.execute("CREATE INDEX idx_posts_created ON posts(created_at, id)")  # a keyset lapozás indexe
db.executemany("INSERT INTO posts(created_at, title) VALUES (?, ?)",
               [(f"2025-01-{d:02d}T10:00:00Z", f"Bejegyzés {d}") for d in range(1, 31)])

def encode_cursor(created_at: str, id_: int) -> str:
    return base64.urlsafe_b64encode(json.dumps([created_at, id_]).encode()).decode()

def decode_cursor(cursor: str) -> tuple[str, int]:
    try:
        created_at, id_ = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return str(created_at), int(id_)
    except (ValueError, TypeError) as e:
        raise ValueError("érvénytelen kurzor") from e  # => HTTP 400

def list_posts(limit: int = 10, cursor: str | None = None) -> dict:
    limit = max(1, min(limit, 100))  # felső korlát: a kliens ne kérhessen milliót
    where, params = "", []
    if cursor:
        # A WHERE csak konstans szöveg; az értékek paraméterként mennek (nincs SQL-injekció)
        where, params = "WHERE (created_at, id) < (?, ?)", list(decode_cursor(cursor))
    rows = db.execute(
        f"SELECT id, created_at, title FROM posts {where} ORDER BY created_at DESC, id DESC LIMIT ?",
        [*params, limit + 1],  # +1 sor: így tudjuk, van-e következő lap
    ).fetchall()
    has_more = len(rows) > limit
    rows = rows[:limit]
    return {
        "data": [{"id": r[0], "created_at": r[1], "title": r[2]} for r in rows],
        "next_cursor": encode_cursor(rows[-1][1], rows[-1][0]) if has_more else None,
    }

if __name__ == "__main__":
    page = list_posts(limit=12)
    print([p["id"] for p in page["data"]])
    while page["next_cursor"]:
        page = list_posts(limit=12, cursor=page["next_cursor"])
        print([p["id"] for p in page["data"]])
```

## GraphQL és az N+1 probléma
<!-- q: Mikor jó a GraphQL, és hogyan kerüljem el az N+1 lekérdezés problémát? -->
<!-- tags: graphql, schema, resolver, dataloader, n+1, batching, query complexity -->

A GraphQL egyetlen végponton, típusos séma alapján engedi, hogy a kliens pontosan azt kérje le,
amire szüksége van (nincs over- és underfetching), és egy kérésben több összefüggő erőforrást
is lekérhet. Ára: a HTTP-szintű gyorsítótárazás nehezebb (POST, egy URL), a hibák gyakran 200-as
válaszban jönnek, és a mezőnkénti resolverek N+1 adatbázis-lekérdezést okoznak — erre a
DataLoader-minta (kötegelés egy tick alatt + kérésenkénti cache) a megoldás. Nyilvános API-nál
korlátozni kell a lekérdezések mélységét és költségét, különben egy beágyazott lekérdezés
megbéníthatja a szervert.

```typescript
import { graphql, buildSchema } from "graphql";

const schema = buildSchema(`
  type Author { id: ID!, name: String! }
  type Post { id: ID!, title: String!, author: Author! }
  type Query { posts(limit: Int = 10): [Post!]! }
`);

const AUTHORS = new Map([["a1", { id: "a1", name: "Ada" }], ["a2", { id: "a2", name: "Linus" }]]);
const POSTS = Array.from({ length: 6 }, (_, i) => ({ id: `p${i}`, title: `Poszt ${i}`, authorId: i % 2 ? "a1" : "a2" }));
let dbQueries = 0;

// DataLoader-elv: az egy tick alatt kért kulcsok EGY kötegben mennek az adatbázishoz
function createLoader<K, V>(batchFn: (keys: K[]) => Promise<V[]>) {
  let queue: { key: K; resolve: (v: V) => void; reject: (e: unknown) => void }[] = [];
  const cache = new Map<K, Promise<V>>(); // ugyanaz a kulcs kérésenként egyszer
  return (key: K): Promise<V> => {
    const hit = cache.get(key);
    if (hit) return hit;
    const p = new Promise<V>((resolve, reject) => {
      queue.push({ key, resolve, reject });
      if (queue.length === 1) {
        queueMicrotask(async () => { // a tick végén küldjük el a köteget
          const batch = queue;
          queue = [];
          try {
            const values = await batchFn(batch.map((b) => b.key));
            batch.forEach((b, i) => b.resolve(values[i]));
          } catch (e) {
            batch.forEach((b) => b.reject(e));
          }
        });
      }
    });
    cache.set(key, p);
    return p;
  };
}

async function execute(query: string) {
  // A loader KÉRÉSENKÉNT jön létre, hogy a cache ne szivárogjon felhasználók között
  const authorLoader = createLoader(async (ids: string[]) => {
    dbQueries++; // élesben: SELECT * FROM authors WHERE id IN (...)
    return ids.map((id) => AUTHORS.get(id)!);
  });
  const rootValue = {
    posts: ({ limit }: { limit: number }) =>
      POSTS.slice(0, Math.min(limit, 50)).map((p) => ({ ...p, author: () => authorLoader(p.authorId) })),
  };
  return graphql({ schema, source: query, rootValue });
}

execute(`{ posts(limit: 6) { title author { name } } }`).then((r) => {
  console.log(JSON.stringify(r.data), "DB-lekérdezések:", dbQueries); // 1, nem 6
});
```

## gRPC és Protocol Buffers
<!-- q: Mi a gRPC és a protobuf, és mikor válasszam REST helyett? -->
<!-- tags: grpc, protobuf, rpc, http/2, streaming, code generation, schema evolution -->

A gRPC HTTP/2 felett futó RPC-keretrendszer: a szolgáltatást és az üzeneteket `.proto` fájlban
írjuk le, ebből a protoc típusos kliens- és szerverkódot generál sok nyelvre. A protobuf
tömör bináris kódolás, a mezőket szám azonosítja, így a séma kompatibilisen bővíthető (új
mező új számmal; törölt mező száma `reserved`). Négy hívástípus van (unáris, szerver-, kliens- és
kétirányú stream), a határidők (deadline) és a lemondás végigterjednek a hívásláncon. Belső
szolgáltatások közötti kommunikációra kiváló; böngészőből csak gRPC-Web proxyval érhető el, és
a bináris formátum nehezebben debugolható, mint a JSON.

```protobuf
syntax = "proto3";
package inventory.v1;
option go_package = "example.com/inventory/gen/inventoryv1";

message GetStockRequest { string sku = 1; }
message Stock {
  string sku = 1;
  int32 available = 2;
  reserved 3;                // régen 'warehouse' volt: a szám nem használható újra
  optional string note = 4;  // proto3 optional: megkülönböztethető a "nincs beállítva"
}
message WatchRequest { repeated string skus = 1; }

service Inventory {
  rpc GetStock(GetStockRequest) returns (Stock);        // unáris hívás
  rpc WatchStock(WatchRequest) returns (stream Stock);  // szerveroldali stream
}
```

```go
package main

import (
	"context"
	"log"
	"net"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	pb "example.com/inventory/gen/inventoryv1" // a protoc által generált kód
)

type server struct {
	pb.UnimplementedInventoryServer // előre-kompatibilitás: új RPC esetén is fordul
	stock map[string]int32
}

func (s *server) GetStock(ctx context.Context, req *pb.GetStockRequest) (*pb.Stock, error) {
	n, ok := s.stock[req.GetSku()]
	if !ok {
		return nil, status.Errorf(codes.NotFound, "ismeretlen SKU: %s", req.GetSku())
	}
	return &pb.Stock{Sku: req.GetSku(), Available: n}, nil
}

func (s *server) WatchStock(req *pb.WatchRequest, stream pb.Inventory_WatchStockServer) error {
	t := time.NewTicker(time.Second)
	defer t.Stop()
	for {
		select {
		case <-stream.Context().Done(): // a kliens bontott vagy lejárt a határidő
			return stream.Context().Err()
		case <-t.C:
			for _, sku := range req.GetSkus() {
				if err := stream.Send(&pb.Stock{Sku: sku, Available: s.stock[sku]}); err != nil {
					return err
				}
			}
		}
	}
}

func main() {
	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatal(err)
	}
	g := grpc.NewServer() // élesben: TLS-hitelesítés és interceptorok (auth, naplózás)
	pb.RegisterInventoryServer(g, &server{stock: map[string]int32{"KAVE-1": 12}})
	log.Fatal(g.Serve(lis))
}
```

## WebSocket: kétirányú valós idejű kapcsolat
<!-- q: Hogyan működik a WebSocket, és mire figyeljek WebSocket szerver írásakor? -->
<!-- tags: websocket, real-time, upgrade, heartbeat, ping pong, broadcast, backpressure, origin -->

A WebSocket egy HTTP Upgrade kézfogás után tartós, kétirányú, üzenetkeretes kapcsolatot ad —
chat, játékok, közös szerkesztés, élő értesítések számára. Mivel a böngésző a WebSocketre nem
alkalmaz CORS-t, a szervernek magának kell ellenőriznie az Origin fejlécet, és hitelesítenie a
klienst (cookie vagy az első üzenetben küldött token; URL-paraméterben a token naplókba
kerülhet). A halott kapcsolatokat ping/pong heartbeattel kell felismerni, a lassú klienseket a
kimenő puffer mérete alapján bontani, és korlátozni kell az üzenetméretet. Több szerverpéldány
esetén az üzenetszóráshoz közös csatorna (pl. Redis pub/sub) kell.

```typescript
import { WebSocketServer, WebSocket } from "ws";

const wss = new WebSocketServer({ port: 8081, maxPayload: 64 * 1024 }); // üzenetméret-korlát
type Client = WebSocket & { isAlive?: boolean; room?: string };

wss.on("connection", (ws: Client, req) => {
  if (req.headers.origin !== "https://app.example.com") {
    ws.close(1008, "tiltott origin"); // 1008 = policy violation
    return;
  }
  ws.isAlive = true;
  ws.room = new URL(req.url ?? "/", "http://localhost").searchParams.get("room") ?? "lobby";
  ws.on("pong", () => { ws.isAlive = true; }); // válaszolt a pingre

  ws.on("message", (data, isBinary) => {
    if (isBinary) return;
    let msg: { type?: string; text?: unknown };
    try {
      msg = JSON.parse(data.toString()); // a bemenet nem megbízható
    } catch {
      ws.send(JSON.stringify({ type: "error", error: "hibás JSON" }));
      return;
    }
    if (msg.type === "chat" && typeof msg.text === "string") {
      broadcast(ws.room!, { type: "chat", text: msg.text.slice(0, 500), at: Date.now() });
    }
  });
});

function broadcast(room: string, payload: object): void {
  const frame = JSON.stringify(payload); // egyszer szerializálunk, nem kliensenként
  for (const c of wss.clients as Set<Client>) {
    if (c.readyState !== WebSocket.OPEN || c.room !== room) continue;
    if (c.bufferedAmount > 1_000_000) { // backpressure: a kliens nem olvas, bontjuk
      c.terminate();
      continue;
    }
    c.send(frame);
  }
}

// Heartbeat: a NAT által eldobott, "félig nyitott" kapcsolatot a TCP nem jelzi magától
const interval = setInterval(() => {
  for (const c of wss.clients as Set<Client>) {
    if (!c.isAlive) {
      c.terminate();
      continue;
    }
    c.isAlive = false;
    c.ping();
  }
}, 30_000);
wss.on("close", () => clearInterval(interval));
```

## Server-Sent Events (SSE)
<!-- q: Mikor használjak Server-Sent Events-et WebSocket helyett, és hogyan implementáljam? -->
<!-- tags: sse, server-sent events, eventsource, streaming, last-event-id, http streaming -->

Az SSE egyirányú (szerver → kliens) szöveges eseményfolyam sima HTTP-válaszként
(`text/event-stream`): a böngésző EventSource API-ja automatikusan újracsatlakozik, és a
Last-Event-ID fejléccel jelzi, honnan kell folytatni. Egyszerűbb a WebSocketnél: működik a
meglévő HTTP-infrastruktúrával (cookie-alapú hitelesítés, proxyk, HTTP/2 multiplexelés),
ezért értesítésekhez, élő árfolyamokhoz, LLM-válaszok tokenenkénti streameléséhez ideális.
Buktatók: HTTP/1.1-en hosztonként ~6 kapcsolat a böngészőkorlát, a proxyk pufferelhetik a
választ (ki kell kapcsolni), és időnként komment-heartbeat kell, hogy a köztes elemek ne
bontsák a tétlen kapcsolatot.

```go
package main

import (
	"fmt"
	"net/http"
	"strconv"
	"time"
)

func events(w http.ResponseWriter, r *http.Request) {
	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "streaming nem támogatott", http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("X-Accel-Buffering", "no") // nginx ne pufferelje a választ

	next := 1 // folytatás onnan, ahol a kliens lemaradt
	if last, err := strconv.Atoi(r.Header.Get("Last-Event-ID")); err == nil {
		next = last + 1
	}
	fmt.Fprint(w, "retry: 3000\n\n") // javasolt újracsatlakozási várakozás ms-ban
	flusher.Flush()

	tick := time.NewTicker(time.Second)
	heartbeat := time.NewTicker(15 * time.Second)
	defer tick.Stop()
	defer heartbeat.Stop()
	for {
		select {
		case <-r.Context().Done(): // a kliens bontott: kilépünk
			return
		case <-heartbeat.C:
			fmt.Fprint(w, ": ping\n\n") // komment sor: életben tartja a proxykat
			flusher.Flush()
		case t := <-tick.C:
			// "id:", "event:", "data:" sorok; üres sor zárja az eseményt
			fmt.Fprintf(w, "id: %d\nevent: price\ndata: {\"ts\":%d,\"price\":%d}\n\n", next, t.Unix(), 2400+next%50)
			flusher.Flush()
			next++
		}
	}
}

func main() {
	http.HandleFunc("/events", events)
	// Böngészőben:
	//   const es = new EventSource("/events");
	//   es.addEventListener("price", (e) => console.log(JSON.parse(e.data)));
	http.ListenAndServe(":8080", nil)
}
```

## CORS: a böngésző Same-Origin határa
<!-- q: Mi az a CORS, hogyan működik a preflight, és hogyan állítsam be biztonságosan? -->
<!-- tags: cors, same-origin policy, preflight, access-control-allow-origin, credentials, browser security -->

A Same-Origin Policy szerint egy szkript nem olvashatja el egy másik origin (séma + host + port)
válaszát; a CORS-fejlécekkel a szerver ezt szelektíven engedélyezheti. „Nem egyszerű” kérés
(PUT/DELETE, JSON Content-Type, egyedi fejléc) előtt a böngésző OPTIONS preflight kérést küld,
és csak engedélyező válasz után indítja az igazit. A CORS böngészős olvasási védelem, nem
hitelesítés: a szerver-szerver hívásokra és a curlre nem vonatkozik, és a kérés (pl. egy
űrlap-POST) CORS nélkül is eljuthat a szerverhez — CSRF ellen külön védekezni kell. Buktató: a
kérés Origin-jének feltétel nélküli visszatükrözése `Allow-Credentials: true` mellett bármely
oldalnak hozzáférést ad a bejelentkezett felhasználó adataihoz.

```go
package main

import "net/http"

// Pontos engedélylista; '*' hitelesítő adatokkal (cookie) amúgy sem használható
var allowedOrigins = map[string]bool{
	"https://app.example.com":   true,
	"https://admin.example.com": true,
}

func CORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		origin := r.Header.Get("Origin")
		w.Header().Add("Vary", "Origin") // a válasz originenként eltér: a cache ne keverje
		allowed := origin != "" && allowedOrigins[origin]
		if allowed {
			w.Header().Set("Access-Control-Allow-Origin", origin)
			w.Header().Set("Access-Control-Allow-Credentials", "true")
			w.Header().Set("Access-Control-Expose-Headers", "ETag, X-Request-Id") // JS-ből olvasható fejlécek
		}
		// Preflight: a böngésző OPTIONS-szel kérdez a "nem egyszerű" kérés előtt
		if r.Method == http.MethodOptions && r.Header.Get("Access-Control-Request-Method") != "" {
			if allowed {
				w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE")
				w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization, Idempotency-Key")
				w.Header().Set("Access-Control-Max-Age", "600") // preflight-cache 10 percig
			}
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func main() {
	api := http.NewServeMux()
	api.HandleFunc("/api/me", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"name":"demo"}`))
	})
	http.ListenAndServe(":8080", CORS(api))
}
```

## Hitelesítés: session cookie vs. JWT
<!-- q: Session cookie-t vagy JWT-t használjak, és hogyan működik a JWT aláírás-ellenőrzése? -->
<!-- tags: authentication, session, jwt, cookie, httponly, hmac, token revocation, stateless -->

Szerveroldali sessionnél a kliens egy véletlen azonosítót kap HttpOnly, Secure, SameSite
cookie-ban, az állapot a szerveren (Redis) van: azonnal visszavonható, de közös tároló kell. A
JWT önhordozó, aláírt token (header.payload.signature): a szerver tároló nélkül ellenőrzi,
ezért szolgáltatások közötti hívásra és rövid életű access tokenre jó, de lejárat előtt nehéz
visszavonni — ezért rövid `exp` és rotált refresh token kell. A payload nem titkosított, csak
aláírt; az algoritmust a szerver rögzítse (az „alg: none” és az HS/RS-keverés klasszikus
támadás), ellenőrizze az `exp`, `iss`, `aud` mezőket, és böngészőben ne localStorage-ban tárold
(XSS-sel ellopható). Élesben kész, auditált könyvtárat (pl. jose) használj.

```typescript
import { createHmac, timingSafeEqual, randomBytes } from "node:crypto";

const b64u = (s: string) => Buffer.from(s).toString("base64url");

export function signJwt(payload: Record<string, unknown>, secret: Buffer, ttlSec = 900): string {
  const now = Math.floor(Date.now() / 1000);
  const header = b64u(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = b64u(JSON.stringify({ ...payload, iat: now, exp: now + ttlSec, jti: randomBytes(8).toString("hex") }));
  const sig = createHmac("sha256", secret).update(`${header}.${body}`).digest("base64url");
  return `${header}.${body}.${sig}`;
}

export function verifyJwt(token: string, secret: Buffer, expected: { iss: string; aud: string }) {
  const parts = token.split(".");
  if (parts.length !== 3) throw new Error("formátumhiba");
  const [h, p, s] = parts;
  const header = JSON.parse(Buffer.from(h, "base64url").toString());
  // Az algoritmust MI rögzítjük, sosem a tokenből olvassuk
  if (header.alg !== "HS256") throw new Error("nem engedélyezett algoritmus");
  const expectedSig = createHmac("sha256", secret).update(`${h}.${p}`).digest();
  const given = Buffer.from(s, "base64url");
  if (given.length !== expectedSig.length || !timingSafeEqual(given, expectedSig)) {
    throw new Error("érvénytelen aláírás"); // konstans idejű összevetés: időzítéses támadás ellen
  }
  const claims = JSON.parse(Buffer.from(p, "base64url").toString());
  const now = Math.floor(Date.now() / 1000);
  if (typeof claims.exp !== "number" || claims.exp < now - 30) throw new Error("lejárt token"); // 30 mp óraeltérés
  if (claims.iss !== expected.iss || claims.aud !== expected.aud) throw new Error("rossz kibocsátó vagy címzett");
  return claims;
}

// A kulcs élesben secret managerből jön (legalább 32 véletlen bájt); itt a demó kedvéért generált
const secret = randomBytes(32);
const token = signJwt({ sub: "user-123", iss: "https://auth.example.com", aud: "orders-api", scope: "orders:read" }, secret);
console.log(verifyJwt(token, secret, { iss: "https://auth.example.com", aud: "orders-api" }).sub); // user-123
```

## OAuth 2.0 és OpenID Connect: Authorization Code + PKCE
<!-- q: Hogyan működik az OAuth2 authorization code flow PKCE-vel és az OpenID Connect? -->
<!-- tags: oauth2, openid connect, oidc, pkce, authorization code, id token, state, sso -->

Az OAuth 2.0 delegált jogosultságkezelés: a felhasználó engedélyezi, hogy egy kliens az ő
nevében, korlátozott hatókörrel (scope) hozzáférjen egy API-hoz, jelszó átadása nélkül. Az
OpenID Connect erre hitelesítési réteget tesz: az `openid` scope-pal ID tokent (aláírt JWT a
felhasználó azonosítójával) is kapunk. Felhasználói bejelentkezéshez ma az Authorization Code +
PKCE folyam ajánlott (az Implicit és a Password grant elavult), gépek közötti hívásokhoz a
Client Credentials, TV/CLI eszközökhöz a Device Code. Kötelező védelmek: `state` (CSRF), PKCE
(ellopott kód ellen), `nonce` (ID token visszajátszása ellen), pontosan regisztrált redirect
URI, és az ID token teljes ellenőrzése (aláírás a JWKS-kulccsal, iss, aud, exp).

```python
import base64
import hashlib
import secrets
from urllib.parse import urlencode

import requests

# Példa végpontok és azonosítók (a valós értékek a szolgáltató konfigurációjából jönnek)
AUTHORIZE_URL = "https://auth.example.com/oauth2/authorize"
TOKEN_URL = "https://auth.example.com/oauth2/token"
CLIENT_ID = "my-web-app"
REDIRECT_URI = "https://app.example.com/callback"

def start_login(session: dict) -> str:
    """1. lépés: átirányítás az authorizációs szerverre."""
    verifier = secrets.token_urlsafe(64)  # PKCE-titok: csak mi ismerjük
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    session["pkce_verifier"] = verifier
    session["oauth_state"] = state = secrets.token_urlsafe(32)  # CSRF elleni védelem
    session["oidc_nonce"] = nonce = secrets.token_urlsafe(32)  # ID token visszajátszása ellen
    return AUTHORIZE_URL + "?" + urlencode({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,  # pontosan egyeznie kell a regisztrálttal
        "scope": "openid profile email",  # 'openid' => OIDC: ID token is jön
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })

def handle_callback(session: dict, params: dict) -> dict:
    """2. lépés: az egyszer használatos kód cseréje tokenekre (szerver-szerver hívás)."""
    if "error" in params:
        raise PermissionError(params["error"])
    if not secrets.compare_digest(params.get("state", ""), session.pop("oauth_state", "")):
        raise PermissionError("state eltérés: lehetséges CSRF")
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": params["code"],
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "code_verifier": session.pop("pkce_verifier"),  # bizonyítja, hogy mi indítottuk
    }, timeout=10)
    resp.raise_for_status()
    tokens = resp.json()  # access_token, refresh_token, id_token, expires_in
    # 3. lépés (kötelező): az id_token ellenőrzése kész könyvtárral — aláírás a JWKS-kulccsal,
    # iss, aud == CLIENT_ID, exp, valamint nonce == session["oidc_nonce"].
    return tokens
```

## API rate limiting csúszóablakkal
<!-- q: Hogyan korlátozzam egy API kéréseinek számát kliensenként, és milyen fejléceket küldjek? -->
<!-- tags: rate limiting, sliding window, 429, retry-after, ratelimit headers, api gateway, throttling -->

A rate limiting védi az API-t a túlterheléstől és a visszaélésektől, és igazságos elosztást ad
a kliensek között. A fix ablak egyszerű, de az ablakhatáron dupla löketet enged; a csúszóablakos
számláló az előző ablak számát az átfedés arányában súlyozza, így kulcsonként két számlálóval
közelíti a pontos csúszó naplót. Túllépéskor 429 Too Many Requests és Retry-After a válasz, a
RateLimit-* fejlécek pedig előre jelzik a keretet. Buktatók: a kulcs hitelesített felhasználó
vagy API-kulcs legyen, IP csak végső esetben (NAT mögött sokan osztoznak rajta); az
X-Forwarded-For csak megbízható proxytól fogadható el; több példánynál közös tároló kell.

```typescript
import { createServer } from "node:http";

interface WindowState { windowStart: number; current: number; previous: number; }

export class SlidingWindowLimiter {
  private state = new Map<string, WindowState>();
  constructor(private readonly limit: number, private readonly windowMs: number) {}

  check(key: string, now = Date.now()): { allowed: boolean; remaining: number; resetMs: number } {
    const start = now - (now % this.windowMs); // a jelenlegi fix ablak kezdete
    let s = this.state.get(key);
    if (!s || start - s.windowStart >= 2 * this.windowMs) {
      s = { windowStart: start, current: 0, previous: 0 }; // régóta inaktív: tiszta lap
    } else if (start !== s.windowStart) {
      s = { windowStart: start, current: 0, previous: s.current }; // ablakváltás
    }
    const elapsed = (now - start) / this.windowMs;
    const estimated = s.previous * (1 - elapsed) + s.current; // az előző ablak súlya csökken
    const allowed = estimated < this.limit;
    if (allowed) s.current++;
    this.state.set(key, s); // élesben Redis + lejárat, különben a Map korlátlanul nő
    return {
      allowed,
      remaining: Math.max(0, Math.floor(this.limit - estimated - (allowed ? 1 : 0))),
      resetMs: start + this.windowMs - now,
    };
  }
}

const LIMIT = 100;
const limiter = new SlidingWindowLimiter(LIMIT, 60_000); // 100 kérés / perc

createServer((req, res) => {
  // Kulcs: ELLENŐRZÖTT API-kulcs vagy felhasználó, végső esetben a socket IP-címe
  const key = (req.headers["x-api-key"] as string | undefined) ?? req.socket.remoteAddress ?? "unknown";
  const r = limiter.check(key);
  res.setHeader("RateLimit-Limit", String(LIMIT));
  res.setHeader("RateLimit-Remaining", String(r.remaining));
  res.setHeader("RateLimit-Reset", String(Math.ceil(r.resetMs / 1000)));
  if (!r.allowed) {
    res.statusCode = 429;
    res.setHeader("Retry-After", String(Math.ceil(r.resetMs / 1000)));
    res.end(JSON.stringify({ error: "túl sok kérés" }));
    return;
  }
  res.end("ok");
}).listen(8080);
```

## Aszinkron TCP-szerver asyncio-val
<!-- q: Hogyan írjak sok kapcsolatot kezelő TCP szervert Pythonban? -->
<!-- tags: socket programming, asyncio, tcp server, streams, drain, backpressure, timeout -->

A szálanként egy kapcsolat modell néhány ezer kapcsolatnál elfogy (memória, kontextusváltás);
az asyncio egyetlen szálon, az OS eseményértesítőjére (epoll/kqueue/IOCP) építve kezel több
tízezer kapcsolatot. A StreamReader `readexactly` metódusa a keretezést egyszerűsíti, a
`drain()` pedig backpressure-t ad: megvárja, amíg a kimenő puffer kiürül. Kötelező elemek:
olvasási időkorlát (a tétlen kapcsolatok ne foglaljanak erőforrást), üzenetméret-korlát, a
kivételek kapcsolatonkénti elkapása és a socket lezárása `finally`-ben. Üzenetszórásnál egy lassú
kliens ne fogja meg a többit — nagy terhelésnél kliensenkénti kimenő sor kell.

```python
import asyncio
import json
import struct

MAX_MSG = 1 << 20
clients: set[asyncio.StreamWriter] = set()

async def read_msg(reader: asyncio.StreamReader) -> dict:
    (length,) = struct.unpack("!I", await reader.readexactly(4))  # 4 bájtos hossz-előtag
    if length > MAX_MSG:
        raise ValueError("túl nagy üzenet")
    return json.loads(await reader.readexactly(length))

async def write_msg(writer: asyncio.StreamWriter, msg: dict) -> None:
    data = json.dumps(msg, ensure_ascii=False).encode()
    writer.write(struct.pack("!I", len(data)) + data)
    await writer.drain()  # backpressure: vár, ha a kimenő puffer megtelt

async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    peer = str(writer.get_extra_info("peername"))
    clients.add(writer)
    try:
        while True:
            msg = await asyncio.wait_for(read_msg(reader), timeout=60)  # tétlenségi időkorlát
            if msg.get("type") == "ping":
                await write_msg(writer, {"type": "pong"})
            elif msg.get("type") == "say":
                out = {"type": "said", "from": peer, "text": str(msg.get("text", ""))[:500]}
                await asyncio.gather(*(write_msg(w, out) for w in list(clients) if w is not writer),
                                     return_exceptions=True)  # egy hibás kliens ne állítsa meg a többit
    except (asyncio.IncompleteReadError, ConnectionError, asyncio.TimeoutError, ValueError):
        pass  # bontás, időtúllépés vagy protokollhiba (a JSON-hiba is ValueError)
    finally:
        clients.discard(writer)
        writer.close()
        await writer.wait_closed()

async def main() -> None:
    server = await asyncio.start_server(handle, "127.0.0.1", 9000, limit=MAX_MSG)
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
```

## HTTP-kliens helyesen: időkorlátok, kapcsolatkészlet, streamelés
<!-- q: Hogyan használjak HTTP klienst helyesen éles kódban (timeout, connection pool, hibakezelés)? -->
<!-- tags: http client, timeouts, connection pooling, keep-alive, httpx, streaming download, error handling -->

A leggyakoribb hiba a kérésenként új kliens: így elveszik a kapcsolatkészlet, és minden
hívás új TCP- és TLS-kézfogást fizet — egyetlen, hosszú életű klienst használj. Mindig állíts
be külön kapcsolódási, olvasási és készlet-várakozási időkorlátot (sok könyvtárban az
alapértelmezés „nincs időkorlát”), és korlátozd a készlet méretét. Automatikusan csak
kapcsolódási hibát vagy idempotens kérést próbálj újra, a Retry-After fejlécet tartsd
tiszteletben, a nagy válaszokat streameld méretkorláttal, az átirányításokat pedig tudatosan
kezeld (SSRF, Authorization-fejléc szivárgása más hosztra).

```python
import httpx

# Egy hosszú életű kliens az egész alkalmazásra: keep-alive kapcsolatkészlet
client = httpx.Client(
    base_url="https://api.example.com",
    timeout=httpx.Timeout(connect=3.0, read=10.0, write=10.0, pool=2.0),  # négy külön korlát
    limits=httpx.Limits(max_connections=50, max_keepalive_connections=20, keepalive_expiry=30),
    headers={"User-Agent": "orders-service/1.4", "Accept": "application/json"},
    transport=httpx.HTTPTransport(retries=2),  # CSAK kapcsolódási hibára próbál újra
    follow_redirects=False,  # átirányítást tudatosan kezelünk
)

def get_order(order_id: str) -> dict | None:
    try:
        r = client.get(f"/orders/{order_id}")
    except httpx.TimeoutException:
        raise RuntimeError("az API nem válaszolt időben") from None
    except httpx.TransportError as e:  # DNS, elutasított kapcsolat, TLS-hiba...
        raise RuntimeError(f"hálózati hiba: {e}") from e
    if r.status_code == 404:
        return None
    r.raise_for_status()  # egyéb 4xx/5xx => httpx.HTTPStatusError
    if not r.headers.get("content-type", "").startswith("application/json"):
        raise RuntimeError("váratlan válaszformátum")
    return r.json()

def download(url: str, path: str, max_bytes: int = 100 * 1024 * 1024) -> None:
    """Nagy válasz streamelése: nem töltjük be egyszerre a memóriába, méretkorláttal."""
    with client.stream("GET", url) as r:
        r.raise_for_status()
        total = 0
        with open(path, "wb") as f:
            for chunk in r.iter_bytes(chunk_size=64 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("túl nagy letöltés")
                f.write(chunk)

if __name__ == "__main__":
    try:
        print(get_order("ord-1001"))
    finally:
        client.close()  # a készlet kapcsolatainak lezárása
```
