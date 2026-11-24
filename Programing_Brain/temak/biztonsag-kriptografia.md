# Biztonság és kriptográfia
<!-- tech: security -->
<!-- aliases: biztonság, security, appsec, kriptográfia, cryptography, owasp, titkosítás -->

Védekező szemléletű alkalmazásbiztonság: a leggyakoribb sebezhetőségek (OWASP Top 10 — pl.
hibás hozzáférés-kezelés, kriptográfiai hibák, injekció, nem biztonságos tervezés, rossz
konfiguráció, elavult komponensek, hitelesítési hibák, integritási hibák, hiányos naplózás,
SSRF) sebezhető és javított kóddal, valamint a kriptográfia helyes használata (jelszóhash,
AEAD, aszimmetrikus kulcsok, MAC és aláírás), titokkezelés, biztonsági fejlécek,
bemenet-validálás, fenyegetésmodellezés, ellátási lánc és biztonságos C-kód. Alapelv: soha ne
írj saját kriptográfiai primitívet — auditált könyvtárat használj, helyesen.

## SQL-injekció és a paraméterezett lekérdezés
<!-- q: Hogyan működik az SQL injection, és hogyan védekezzek ellene? -->
<!-- tags: sql injection, owasp, parameterized query, prepared statement, input handling, allowlist -->

SQL-injekció akkor keletkezik, ha a felhasználói bemenet a lekérdezés szövegébe kerül
(string-összefűzés, f-string), így a támadó saját SQL-logikát fűzhet be: kikerülheti a
bejelentkezést, kiolvashat vagy törölhet adatot. A védekezés a paraméterezett lekérdezés
(prepared statement): az érték külön csatornán jut el az adatbázishoz, és sosem értelmeződik
kódként. Az azonosítók (oszlopnév, rendezési irány) nem paraméterezhetők — ezekhez
engedélylista kell; LIKE-nál a `%` és `_` helyettesítő karaktereket is escape-elni kell.
Mélységi védelem: az alkalmazás adatbázis-felhasználója csak a szükséges jogokkal rendelkezzen.

```python
import sqlite3

db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT, email TEXT, is_admin INTEGER)")
db.executemany("INSERT INTO users(name, email, is_admin) VALUES (?, ?, ?)",
               [("anna", "anna@example.com", 0), ("root", "root@example.com", 1)])

# SEBEZHETŐ: a bemenet a lekérdezés SZÖVEGÉBE kerül
def find_user_vulnerable(name: str):
    return db.execute(f"SELECT id, name, email FROM users WHERE name = '{name}'").fetchall()

payload = "x' OR '1'='1"
print(find_user_vulnerable(payload))  # MINDEN felhasználót visszaad

# JAVÍTOTT: paraméterezett lekérdezés — az érték sosem értelmeződik SQL-ként
def find_user(name: str):
    return db.execute("SELECT id, name, email FROM users WHERE name = ?", (name,)).fetchall()

print(find_user(payload))  # [] — a payload egyszerű szövegként hasonlítódik

ALLOWED_SORT = {"name", "email", "id"}  # azonosítókhoz engedélylista

def list_users(sort: str = "name", desc: bool = False):
    if sort not in ALLOWED_SORT:
        raise ValueError("érvénytelen rendezési mező")
    direction = "DESC" if desc else "ASC"  # nem a felhasználó szövege kerül be
    return db.execute(f"SELECT id, name FROM users ORDER BY {sort} {direction}").fetchall()

def search(prefix: str):
    # LIKE: a helyettesítő karakterek escape-elése, különben a "%" mindent illeszt
    escaped = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return db.execute("SELECT name FROM users WHERE name LIKE ? ESCAPE '\\'", (escaped + "%",)).fetchall()

print(list_users("email", desc=True), search("an"))
```

## Cross-Site Scripting (XSS)
<!-- q: Mi az XSS, és hogyan előzzem meg a frontendben és a szerveren? -->
<!-- tags: xss, cross-site scripting, output encoding, innerhtml, textcontent, sanitization, dompurify -->

XSS-nél a támadó által szolgáltatott szöveg HTML-ként vagy szkriptként fut le az áldozat
böngészőjében, a mi oldalunk nevében: ellophatja a munkamenetet, műveleteket végezhet a
felhasználó helyett. Fajtái: tárolt (adatbázisból), visszatükrözött (URL-paraméterből) és
DOM-alapú (kliensoldali kód illeszti be). A védekezés a kontextusfüggő kimeneti kódolás: HTML
törzsben, attribútumban, URL-ben, JS-ben és CSS-ben más szabály érvényes; URL-attribútumnál a
sémát is ellenőrizni kell (`javascript:`). A keretrendszerek (React, Vue, Angular) alapból
escape-elnek, a veszély a kiskapukban van (dangerouslySetInnerHTML, v-html); mélységi védelem
a szigorú CSP és a HttpOnly cookie.

```typescript
// SEBEZHETŐ: felhasználói szöveg HTML-ként kerül a DOM-ba
function renderCommentVulnerable(container: HTMLElement, comment: string): void {
  // comment = '<img src=x onerror="...">' esetén a támadó kódja a MI oldalunkon fut le
  container.innerHTML = `<p class="comment">${comment}</p>`;
}

// JAVÍTOTT 1: szövegként kezeljük, nem jelölőként
function renderComment(container: HTMLElement, comment: string): void {
  const p = document.createElement("p");
  p.className = "comment";
  p.textContent = comment; // a böngésző nem értelmezi HTML-ként
  container.append(p);
}

// JAVÍTOTT 2: HTML-szövegkontextus kódolása (a szerveroldali sablonmotorok ezt alapból teszik)
export function escapeHtml(s: string): string {
  const map: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  return s.replace(/[&<>"']/g, (ch) => map[ch]);
}

// URL-kontextus: a "javascript:" séma escape-elés után is lefutna, ezért sémát ellenőrzünk
export function safeHref(url: string): string {
  try {
    const u = new URL(url, window.location.origin);
    return ["http:", "https:", "mailto:"].includes(u.protocol) ? u.href : "#";
  } catch {
    return "#";
  }
}

// Ha valóban HTML-t kell megjeleníteni (rich text): bevált szanitizáló könyvtár, engedélylistával
// import DOMPurify from "dompurify";
// container.innerHTML = DOMPurify.sanitize(userHtml, { ALLOWED_TAGS: ["b", "i", "a", "p"] });

const list = document.getElementById("comments")!;
renderComment(list, '<img src=x onerror="alert(1)">'); // szövegként jelenik meg, nem fut le
void renderCommentVulnerable; // csak szemléltetés, ne használd
```

## Cross-Site Request Forgery (CSRF)
<!-- q: Mi a CSRF támadás, és hogyan védjem ki tokennel és SameSite cookie-val? -->
<!-- tags: csrf, xsrf, samesite, csrf token, cookie, sec-fetch-site, origin check -->

CSRF-nél egy idegen oldal a felhasználó böngészőjével küldet kérést a mi oldalunkra (pl. egy
automatikusan elküldött rejtett űrlappal); a böngésző magától mellékeli a session cookie-t,
így a kérés hitelesnek tűnik. Védelem rétegekben: állapotot módosító műveletet soha ne végezz
GET-tel; a cookie legyen `SameSite=Lax` vagy `Strict` (így más oldalról indított POST-hoz nem
megy); minden módosító kérés hordozzon a sessionhöz kötött, kitalálhatatlan tokent (rejtett
mező vagy fejléc), amit konstans idejű összevetéssel ellenőrzünk; kiegészítésként az Origin
vagy a Sec-Fetch-Site fejléc vizsgálata. Tisztán Authorization-fejléces (Bearer token) API-t a
CSRF nem érinti, mert azt a böngésző nem küldi automatikusan.

```python
import hashlib
import hmac
import secrets

# SEBEZHETŐ minta (pszeudokód): csak a cookie-t nézi
#   def transfer(req):
#       user = session_user(req.cookies["sid"])  # a cookie-t a böngésző magától küldi
#       do_transfer(user, req.form["to"], req.form["amount"])

SERVER_KEY = secrets.token_bytes(32)  # élesben secret managerből

def issue_csrf_token(session_id: str) -> str:
    """A sessionhöz kötött token, szerveroldali állapot nélkül (HMAC)."""
    nonce = secrets.token_urlsafe(16)
    mac = hmac.new(SERVER_KEY, f"{session_id}:{nonce}".encode(), hashlib.sha256).hexdigest()
    return f"{nonce}.{mac}"  # rejtett űrlapmezőbe vagy X-CSRF-Token fejlécbe

def verify_csrf_token(session_id: str, token: str | None) -> bool:
    if not token or "." not in token:
        return False
    nonce, mac = token.split(".", 1)
    expected = hmac.new(SERVER_KEY, f"{session_id}:{nonce}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, expected)  # konstans idejű összevetés

def session_cookie_header(session_id: str) -> str:
    # SameSite=Lax: idegen oldalról indított POST-hoz nem megy; HttpOnly: JS nem olvassa;
    # Secure: csak HTTPS; __Host- előtag: pontosan ehhez a hosthoz kötött
    return f"__Host-sid={session_id}; Path=/; Secure; HttpOnly; SameSite=Lax"

def handle_transfer(session_id: str, form: dict, headers: dict) -> int:
    if headers.get("Sec-Fetch-Site") not in (None, "same-origin", "none"):
        return 403  # más oldalról indított kérés
    if not verify_csrf_token(session_id, form.get("csrf_token") or headers.get("X-CSRF-Token")):
        return 403
    return 200  # ... itt jönne az átutalás ...

if __name__ == "__main__":
    sid = secrets.token_urlsafe(32)
    tok = issue_csrf_token(sid)
    print(session_cookie_header(sid))
    print(handle_transfer(sid, {"csrf_token": tok}, {"Sec-Fetch-Site": "same-origin"}))  # 200
    print(handle_transfer(sid, {}, {"Sec-Fetch-Site": "cross-site"}))  # 403
```

## Server-Side Request Forgery (SSRF)
<!-- q: Mi az SSRF, és hogyan kérjek le biztonságosan felhasználó által megadott URL-t? -->
<!-- tags: ssrf, url fetch, cloud metadata, private ip, dns rebinding, egress proxy, webhook -->

SSRF-nél a szerver egy felhasználó által megadott URL-t kér le (kép URL-ből, webhook, előnézet),
a támadó pedig belső célra irányítja: felhős metaadat-szolgáltatásra (169.254.169.254 —
ideiglenes hozzáférési kulcsok), localhoston futó adminfelületekre, belső adatbázisokra. A
védekezés: csak engedélyezett séma és port, a host feloldott címeinek ellenőrzése (privát,
loopback, link-local tiltva), átirányítások vak követésének tiltása, méret- és időkorlát.
Buktató a DNS rebinding: az ellenőrzés és a kérés között a név más IP-re oldódhat fel — erős
védelem a kapcsolat ellenőrzött IP-hez kötése vagy egy kimenő forgalmat szűrő egress proxy,
felhőben pedig az IMDSv2 és a hálózati szabályok.

```python
import ipaddress
import socket
from urllib.parse import urlparse

import requests

def fetch_vulnerable(url: str) -> bytes:
    return requests.get(url, timeout=5).content  # bármit lekér, átirányítást is követ

ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {80, 443}

def _is_public(ip: str) -> bool:
    a = ipaddress.ip_address(ip)
    return not (a.is_private or a.is_loopback or a.is_link_local or a.is_multicast
                or a.is_reserved or a.is_unspecified)

def resolve_public(url: str) -> tuple[str, list[str], int]:
    """Séma, port és MINDEN feloldott cím ellenőrzése."""
    u = urlparse(url)
    if u.scheme not in ALLOWED_SCHEMES or not u.hostname:
        raise ValueError("nem engedélyezett séma vagy hiányzó host")
    port = u.port or (443 if u.scheme == "https" else 80)
    if port not in ALLOWED_PORTS:
        raise ValueError("nem engedélyezett port")
    ips = sorted({i[4][0] for i in socket.getaddrinfo(u.hostname, port, proto=socket.IPPROTO_TCP)})
    if not ips or not all(_is_public(ip) for ip in ips):
        raise ValueError("belső vagy fenntartott címre mutat")
    return u.hostname, ips, port

def fetch_safe(url: str, max_bytes: int = 5_000_000) -> bytes:
    resolve_public(url)
    # Egyszerűsítés: itt a requests újra felold (DNS rebinding!). Élesben az ellenőrzött IP-hez
    # kötött kapcsolat vagy egress proxy kell.
    resp = requests.get(url, timeout=5, allow_redirects=False, stream=True)
    if resp.is_redirect:
        raise ValueError("átirányítás: az új célt is ellenőrizni kell")
    data = resp.raw.read(max_bytes + 1, decode_content=True)
    if len(data) > max_bytes:
        raise ValueError("túl nagy válasz")
    return data

if __name__ == "__main__":
    for bad in ("http://169.254.169.254/latest/meta-data/", "http://localhost:6379/", "file:///etc/passwd"):
        try:
            resolve_public(bad)
        except ValueError as e:
            print(bad, "->", e)
```

## Hibás hozzáférés-kezelés és IDOR
<!-- q: Mi az IDOR, és hogyan ellenőrizzem a jogosultságot objektumszinten? -->
<!-- tags: idor, broken access control, authorization, object level authorization, bola, owasp -->

A hibás hozzáférés-kezelés az OWASP-lista első helyén áll. Az IDOR (Insecure Direct Object
Reference, API-knál BOLA) azt jelenti, hogy a végpont hitelesíti a felhasználót, de nem
ellenőrzi, hogy a kért objektum az övé-e — így az azonosító átírásával más adatai is
elérhetők. A javítás: minden hozzáférésnél objektumszintű jogosultság-ellenőrzés egy központi
függvényben, vagy még jobb, a lekérdezés eleve a tulajdonosra szűrjön. Idegen objektumra 404-et
érdemes adni (ne áruljuk el a létezését); a kitalálhatatlan azonosító (UUID) csak nehezíti a
próbálgatást, a jogosultság-ellenőrzést nem váltja ki. Alapértelmezés legyen a tiltás.

```python
from dataclasses import dataclass

from fastapi import Depends, FastAPI, Header, HTTPException

app = FastAPI()

@dataclass
class User:
    id: int
    role: str  # "customer" | "support"

@dataclass
class Invoice:
    id: int
    owner_id: int
    total: int

INVOICES = {101: Invoice(101, owner_id=1, total=12_000), 102: Invoice(102, owner_id=2, total=9_900)}

def current_user(authorization: str = Header(...)) -> User:
    # Élesben token/session ellenőrzése; itt egyszerűsített demó-leképezés
    users = {"Bearer demo-user-1": User(1, "customer"), "Bearer demo-support": User(9, "support")}
    if authorization not in users:
        raise HTTPException(401, "nincs hitelesítve")
    return users[authorization]

# SEBEZHETŐ: hitelesít, de nem ellenőrzi a tulajdonjogot (az 1-es user a 102-est is látja)
@app.get("/v1/invoices/{invoice_id}")
def get_invoice_vulnerable(invoice_id: int, user: User = Depends(current_user)) -> Invoice:
    inv = INVOICES.get(invoice_id)
    if not inv:
        raise HTTPException(404)
    return inv

# JAVÍTOTT: központi, objektumszintű jogosultság-ellenőrzés
def can_read_invoice(user: User, inv: Invoice) -> bool:
    return inv.owner_id == user.id or user.role == "support"

@app.get("/v2/invoices/{invoice_id}")
def get_invoice(invoice_id: int, user: User = Depends(current_user)) -> Invoice:
    inv = INVOICES.get(invoice_id)
    if inv is None or not can_read_invoice(user, inv):
        raise HTTPException(404, "nincs ilyen számla")  # nem áruljuk el, hogy létezik
    return inv

# Adatbázisnál még jobb: SELECT ... FROM invoices WHERE id = ? AND owner_id = ?
```

## Nem biztonságos deszerializáció
<!-- q: Miért veszélyes a pickle és a nem biztonságos deszerializáció, és mit használjak helyette? -->
<!-- tags: insecure deserialization, pickle, yaml, rce, json schema, pydantic, mass assignment -->

Számos bináris szerializációs formátum (Python pickle, Java ObjectInputStream, .NET
BinaryFormatter, PHP unserialize) visszaállításkor tetszőleges objektumot hozhat létre és kódot
futtathat — megbízhatatlan forrásból (cookie, kérés törzse, üzenetsor) érkező adattal ez
távoli kódfuttatást jelent. A javítás: csak adatot leíró formátum (JSON) és szigorú
séma-validálás (típusok, határok, ismeretlen mezők tiltása — ez a mass assignment ellen is
véd), méretkorlát a feldolgozás előtt. YAML-nál mindig `safe_load`. Ha mégis bináris objektum
kell, csak saját forrásból és aláírva (HMAC) fogadd el.

```python
import json
import pickle
from datetime import datetime

from pydantic import BaseModel, Field, ValidationError

# SEBEZHETŐ: a pickle betöltéskor kódot futtathat (__reduce__)
def load_session_vulnerable(blob: bytes) -> dict:
    return pickle.loads(blob)  # SOHA megbízhatatlan adattal

class Demo:  # ártalmatlan szemléltetés: betöltéskor függvényhívás történik
    def __reduce__(self):
        return (print, ("Ez a pickle.loads() közben futott le!",))

load_session_vulnerable(pickle.dumps(Demo()))  # egy támadó itt rendszerparancsot hívna

# JAVÍTOTT: JSON + szigorú séma
class SessionData(BaseModel):
    model_config = {"extra": "forbid"}  # ismeretlen mező => hiba (mass assignment ellen is)
    user_id: int = Field(gt=0)
    roles: list[str] = Field(max_length=10)
    issued_at: datetime

def load_session(raw: str) -> SessionData:
    if len(raw) > 4096:  # méretkorlát a feldolgozás ELŐTT
        raise ValueError("túl nagy bemenet")
    return SessionData.model_validate_json(raw)

ok = json.dumps({"user_id": 7, "roles": ["reader"], "issued_at": "2025-01-01T10:00:00Z"})
print(load_session(ok))
try:
    load_session('{"user_id": 7, "roles": [], "issued_at": "2025-01-01T10:00:00Z", "is_admin": true}')
except ValidationError as e:
    print("elutasítva:", e.errors()[0]["type"])  # extra_forbidden
```

## Jelszavak tárolása: Argon2id és bcrypt
<!-- q: Hogyan tároljam biztonságosan a jelszavakat? -->
<!-- tags: password hashing, argon2, bcrypt, scrypt, salt, rehash, timing attack, credential stuffing -->

Jelszót soha ne tárolj titkosítva vagy gyors hash-sel (SHA-256, MD5): egy kiszivárgott
adatbázison GPU-val másodpercenként milliárdnyi próbálkozás lehetséges. Lassú, memóriaigényes,
sózott jelszóhash kell: Argon2id (ajánlott), scrypt vagy bcrypt; a só automatikusan
generálódik és a hash része, így azonos jelszavakból eltérő hash lesz. A paramétereket idővel
erősíteni kell — sikeres belépéskor átmenetileg újrahash-elünk. Buktatók: a bcrypt csak az első
72 bájtot veszi figyelembe; nem létező felhasználónál is futtass hash-t (különben az időzítés
elárulja a létezést); a belépést korlátozd (rate limit), és támogasd az MFA-t.

```python
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

ph = PasswordHasher(
    time_cost=3,  # iterációk
    memory_cost=64 * 1024,  # 64 MiB hash-enként: a GPU/ASIC-gyorsítást drágítja
    parallelism=1,
)
# A kimenet tartalmazza a paramétereket és a sót: $argon2id$v=19$m=65536,t=3,p=1$<só>$<hash>
DUMMY_HASH = ph.hash("dummy-password-for-timing")  # nem létező felhasználóhoz

def register(password: str) -> str:
    if len(password) < 12:
        raise ValueError("legalább 12 karakter")  # hosszt követelj, ne bonyolult szabályokat
    if len(password) > 256:
        raise ValueError("túl hosszú")  # DoS ellen: a hash-elés szándékosan drága
    return ph.hash(password)

def login(stored_hash: str | None, password: str) -> tuple[bool, str | None]:
    """(sikeres-e, új hash, ha a paraméterek elavultak)"""
    try:
        ph.verify(stored_hash or DUMMY_HASH, password)  # nem létező usernél is fut: egyenletes időzítés
    except (VerificationError, InvalidHashError):  # a VerifyMismatchError is VerificationError
        return False, None
    if stored_hash is None:
        return False, None
    new_hash = ph.hash(password) if ph.check_needs_rehash(stored_hash) else None
    return True, new_hash

if __name__ == "__main__":
    h = register("helyes-lo-elem-tuzgolyo")
    print(h[:30], "...")
    print(login(h, "helyes-lo-elem-tuzgolyo"))  # (True, None)
    print(login(h, "rossz-jelszo-123"))  # (False, None)
    print(login(None, "barmi-jelszo-123"))  # (False, None), hasonló idő alatt
```

## Szimmetrikus titkosítás és AEAD
<!-- q: Hogyan titkosítsak adatot helyesen szimmetrikus kulccsal, és mi az AEAD? -->
<!-- tags: aes-gcm, aead, chacha20-poly1305, nonce, symmetric encryption, ecb, associated data -->

Az AEAD (Authenticated Encryption with Associated Data) egyszerre titkosít és hitelesít: a
módosított titkos szöveget a visszafejtés elutasítja. A sima titkosítás hitelesítés nélkül
(pl. AES-CBC MAC nélkül) manipulálható (bitátfordítás, padding oracle), az ECB mód pedig
láthatóvá teszi az ismétlődő mintákat — ezek kerülendők. AES-GCM-nél a 96 bites nonce
kulcsonként soha nem ismétlődhet: az ismétlés a hitelesítő kulcsot és a két üzenet XOR-ját is
kiszivárogtatja (véletlen nonce kb. 2^32 üzenetig biztonságos egy kulccsal). Az associated data
(pl. rekordazonosító) nem titkos, de hitelesített: így egy titkosított mező nem másolható át egy
másik rekordhoz. AES-hardvergyorsítás nélkül a ChaCha20-Poly1305 a gyorsabb.

```python
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305

key = AESGCM.generate_key(bit_length=256)  # élesben KMS-ből / secret managerből
aead = AESGCM(key)

def encrypt(plaintext: bytes, context: bytes) -> bytes:
    nonce = os.urandom(12)  # kulcsonként SOHA nem ismétlődhet
    return nonce + aead.encrypt(nonce, plaintext, context)  # a context hitelesített, nem titkos

def decrypt(blob: bytes, context: bytes) -> bytes:
    nonce, ct = blob[:12], blob[12:]
    try:
        return aead.decrypt(nonce, ct, context)  # a címke (tag) ellenőrzése a művelet része
    except InvalidTag:
        raise ValueError("módosított adat vagy rossz kulcs/kontextus") from None

if __name__ == "__main__":
    blob = encrypt(b"bizalmas mezo tartalma", b"user:42|field:note|v1")
    print(decrypt(blob, b"user:42|field:note|v1"))
    tampered = blob[:-1] + bytes([blob[-1] ^ 1])  # egyetlen bit módosítása
    for b, ctx in ((tampered, b"user:42|field:note|v1"), (blob, b"user:43|field:note|v1")):
        try:
            decrypt(b, ctx)
        except ValueError as e:
            print("elutasítva:", e)
    c = ChaCha20Poly1305(ChaCha20Poly1305.generate_key())  # ugyanaz az interfész
    n = os.urandom(12)
    print(c.decrypt(n, c.encrypt(n, b"adat", None), None))
```

## Aszimmetrikus kriptográfia és hibrid titkosítás
<!-- q: Hogyan működik a nyilvános kulcsú titkosítás és a kulcscsere, és miért hibrid a gyakorlatban? -->
<!-- tags: asymmetric encryption, public key, x25519, ecdh, hkdf, hybrid encryption, rsa, key exchange -->

Az aszimmetrikus kriptográfiában a nyilvános kulcs szabadon megosztható, a privát kulcs titkos.
Mivel lassú és csak kis adatra alkalmas, hibrid módon használjuk: kulcscserével (ECDH, pl.
X25519) közös titkot képzünk, abból KDF-fel (HKDF) szimmetrikus kulcsot származtatunk, és azzal
AEAD-del titkosítunk — így működik a TLS, a Signal, az age és a HPKE. Egyszeri (ephemeral)
kulcspár használata előre titkosságot ad. RSA-nál csak OAEP (titkosítás) és PSS (aláírás)
kitöltés elfogadható, legalább 3072 bites kulccsal; a kvantumszámítógépek elleni átmenethez a
hibrid (klasszikus + ML-KEM) kulcscsere a jelenlegi irány. A privát kulcsot titkosítva, ideális
esetben HSM-ben vagy KMS-ben tárold.

```python
import os

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

RAW = (serialization.Encoding.Raw, serialization.PublicFormat.Raw)

def derive_key(shared: bytes, info: bytes) -> bytes:
    # A nyers ECDH-kimenet nem egyenletes eloszlású: KDF-fel lesz belőle kulcs
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=info).derive(shared)

def seal(recipient_pub: X25519PublicKey, plaintext: bytes) -> bytes:
    """Titkosítás a címzett nyilvános kulcsára egyszeri kulcspárral (ECIES-szerű)."""
    eph = X25519PrivateKey.generate()
    eph_pub = eph.public_key().public_bytes(*RAW)
    key = derive_key(eph.exchange(recipient_pub), b"demo-seal-v1" + eph_pub)
    nonce = os.urandom(12)
    return eph_pub + nonce + AESGCM(key).encrypt(nonce, plaintext, eph_pub)

def open_sealed(recipient_priv: X25519PrivateKey, blob: bytes) -> bytes:
    eph_pub, nonce, ct = blob[:32], blob[32:44], blob[44:]
    shared = recipient_priv.exchange(X25519PublicKey.from_public_bytes(eph_pub))
    return AESGCM(derive_key(shared, b"demo-seal-v1" + eph_pub)).decrypt(nonce, ct, eph_pub)

if __name__ == "__main__":
    recipient = X25519PrivateKey.generate()  # a címzett kulcspárja
    blob = seal(recipient.public_key(), b"titkos jelentes")
    print(open_sealed(recipient, blob))
    # Privát kulcs tárolása: jelmondattal titkosított PKCS#8 (még jobb: HSM/KMS)
    pem = recipient.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(b"hosszu-demo-jelmondat"),
    )
    print(pem.splitlines()[0])  # b'-----BEGIN ENCRYPTED PRIVATE KEY-----'
```

## Hash, MAC és digitális aláírás: mikor melyik?
<!-- q: Mi a különbség a hash, a HMAC és a digitális aláírás között, és hogyan ellenőrizzek webhookot? -->
<!-- tags: hash, hmac, mac, digital signature, ed25519, webhook verification, integrity, authenticity -->

A hash (SHA-256) kulcs nélküli ujjlenyomat: integritást ellenőriz véletlen hibák ellen, de bárki
újraszámolhatja, így támadó ellen nem véd (fájl-ellenőrzőösszeg, tartalom-címzés). A MAC (HMAC)
közös titkos kulccsal hitelesít: csak a kulcs birtokosai állíthatják elő (webhookok,
API-kérések aláírása), de nem bizonyítja, hogy a két fél közül ki küldte. A digitális aláírás
(Ed25519, ECDSA, RSA-PSS) privát kulccsal készül és nyilvános kulccsal bárki ellenőrizheti:
letagadhatatlan (szoftverfrissítések, tanúsítványok, JWT RS256/EdDSA). Buktatók: a naiv
`sha256(kulcs + adat)` hossz-kiterjesztéses támadásra sebezhető (HMAC kell), az összevetés
legyen konstans idejű, webhooknál pedig időbélyeggel védj a visszajátszás ellen.

```python
import hashlib
import hmac
import secrets
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

data = b'{"event":"payment.succeeded","amount":4990}'

# 1) HASH: kulcs nélkül — támadó ellen nem véd
digest = hashlib.sha256(data).hexdigest()

# 2) HMAC: közös titok — webhook-aláírás időbélyeggel
webhook_secret = secrets.token_bytes(32)

def sign_webhook(body: bytes, ts: int) -> str:
    return hmac.new(webhook_secret, f"{ts}.".encode() + body, hashlib.sha256).hexdigest()

def verify_webhook(body: bytes, ts: int, signature: str, tolerance_s: int = 300) -> bool:
    if abs(time.time() - ts) > tolerance_s:  # régi kérés: visszajátszás ellen
        return False
    return hmac.compare_digest(sign_webhook(body, ts), signature)  # konstans idejű

# 3) ALÁÍRÁS: privát kulccsal ír alá, nyilvánossal bárki ellenőriz
signing_key = Ed25519PrivateKey.generate()
verify_key = signing_key.public_key()
signature = signing_key.sign(data)

if __name__ == "__main__":
    ts = int(time.time())
    sig = sign_webhook(data, ts)
    print("hash:", digest[:16], "...")
    print("hmac ok:", verify_webhook(data, ts, sig), "| módosítva:", verify_webhook(data + b" ", ts, sig))
    try:
        verify_key.verify(signature, data)
        print("aláírás rendben")
        verify_key.verify(signature, data.replace(b"4990", b"1"))
    except InvalidSignature:
        print("aláírás érvénytelen: az adat módosult")
```

## Kulcs- és titokkezelés, borítékos titkosítás
<!-- q: Hogyan kezeljem a titkokat és a titkosítási kulcsokat, és mi a borítékos titkosítás? -->
<!-- tags: secrets management, key management, kms, envelope encryption, key rotation, vault, dek kek -->

A titkok (API-kulcsok, adatbázis-jelszavak, aláírókulcsok) soha nem kerülhetnek forráskódba,
gitbe, Docker-image-be vagy logba; futásidőben secret managerből (Vault, felhős Secret Manager)
vagy a futtatókörnyezet által injektált változóból jönnek, legkisebb jogosultsággal és
auditnaplóval. Kiszivárgott titoknál a git-előzmény törlése nem elég — azonnal vissza kell
vonni és cserélni. Borítékos titkosításnál minden adathoz friss adatkulcs (DEK) készül, azt a
KMS-ben/HSM-ben maradó fő kulcs (KEK) csomagolja; a rekord a kulcsverzió azonosítóját is
tárolja, így a KEK rotálható, és rotációkor csak a DEK-eket kell újracsomagolni, nem az összes
adatot.

```python
import base64
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class LocalKMS:
    """KMS-szimuláció kulcsverziókkal. Élesben a KEK sosem hagyja el a KMS-t/HSM-et."""

    def __init__(self) -> None:
        self.keys = {"kek-v1": AESGCM.generate_key(256)}
        self.current = "kek-v1"

    def rotate(self) -> None:
        self.current = f"kek-v{len(self.keys) + 1}"
        self.keys[self.current] = AESGCM.generate_key(256)  # a régiek visszafejtésre megmaradnak

    def wrap(self, dek: bytes) -> tuple[str, bytes]:
        nonce = os.urandom(12)
        return self.current, nonce + AESGCM(self.keys[self.current]).encrypt(nonce, dek, b"dek")

    def unwrap(self, key_id: str, wrapped: bytes) -> bytes:
        return AESGCM(self.keys[key_id]).decrypt(wrapped[:12], wrapped[12:], b"dek")

def encrypt_record(kms: LocalKMS, plaintext: bytes) -> str:
    dek = AESGCM.generate_key(256)  # friss adatkulcs rekordonként
    nonce = os.urandom(12)
    kid, wrapped = kms.wrap(dek)
    b64 = lambda b: base64.b64encode(b).decode()
    ct = AESGCM(dek).encrypt(nonce, plaintext, kid.encode())
    return json.dumps({"kid": kid, "dek": b64(wrapped), "nonce": b64(nonce), "ct": b64(ct)})

def decrypt_record(kms: LocalKMS, blob: str) -> bytes:
    env = json.loads(blob)
    dek = kms.unwrap(env["kid"], base64.b64decode(env["dek"]))
    return AESGCM(dek).decrypt(base64.b64decode(env["nonce"]), base64.b64decode(env["ct"]), env["kid"].encode())

if __name__ == "__main__":
    if os.environ.get("DB_PASSWORD") is None:  # titok környezetből, nem a kódból
        print("figyelem: DB_PASSWORD nincs beállítva")
    kms = LocalKMS()
    old = encrypt_record(kms, b"bizalmas adat")
    kms.rotate()
    new = encrypt_record(kms, b"uj adat")
    print(decrypt_record(kms, old), json.loads(old)["kid"], json.loads(new)["kid"])  # kek-v1 kek-v2
```

## TLS tanúsítvány-rögzítés (pinning) alapjai
<!-- q: Mi a certificate pinning, mikor használjam, és mik a kockázatai? -->
<!-- tags: certificate pinning, spki pin, tls, mitm, mobile security, public key pinning -->

A pinning a normál CA- és hosztnév-ellenőrzésen felül azt is elvárja, hogy a szerver nyilvános
kulcsa (SPKI hash-e) egy előre ismert halmazba tartozzon — így egy hamisan kiállított, de
„érvényes” tanúsítvány (kompromittált CA, közbeékelődő proxy) sem fogadható el. Főleg
mobilalkalmazásokban és saját kliensekben használják; böngészőkben a HPKP megszűnt, mert
könnyű volt vele kizárni a saját felhasználókat. Szabályok: a kulcsra pinelj, ne a
tanúsítványra (megújításkor a kulcs maradhat), mindig legyen tartalék pin a következő
kulcspárra, a pinlista legyen frissíthető, és a pinning sosem helyettesíti a normál
ellenőrzést.

```python
import base64
import hashlib
import socket
import ssl

from cryptography import x509
from cryptography.hazmat.primitives import serialization

def spki_sha256(der_cert: bytes) -> str:
    """A tanúsítvány nyilvános kulcsának (SubjectPublicKeyInfo) SHA-256 hash-e base64-ben."""
    cert = x509.load_der_x509_certificate(der_cert)
    spki = cert.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return base64.b64encode(hashlib.sha256(spki).digest()).decode()

def connect_pinned(host: str, pins: set[str], port: int = 443) -> ssl.SSLSocket:
    ctx = ssl.create_default_context()  # a CA- és hosztnév-ellenőrzés MARAD
    sock = ctx.wrap_socket(socket.create_connection((host, port), timeout=5), server_hostname=host)
    der = sock.getpeercert(binary_form=True)  # a levél (leaf) tanúsítvány
    if der is None or spki_sha256(der) not in pins:
        sock.close()
        raise ssl.SSLError(f"pin-eltérés ({host}): lehetséges közbeékelődés")
    return sock

if __name__ == "__main__":
    host = "example.com"
    ctx = ssl.create_default_context()
    with ctx.wrap_socket(socket.create_connection((host, 443), timeout=5), server_hostname=host) as s:
        current = spki_sha256(s.getpeercert(binary_form=True))
    print("jelenlegi pin:", current)
    BACKUP_PIN = "tartalek-kulcs-pinje-base64="  # a következő kulcspár előre kiszámolt pinje
    with connect_pinned(host, {current, BACKUP_PIN}) as conn:
        print("rögzített kapcsolat rendben:", conn.version())
```

## Biztonsági HTTP-fejlécek és Content Security Policy
<!-- q: Milyen biztonsági HTTP fejléceket állítsak be, és hogyan írjak szigorú CSP-t? -->
<!-- tags: csp, content security policy, hsts, security headers, nonce, clickjacking, x-content-type-options -->

A biztonsági fejlécek megmondják a böngészőnek, mit ne engedjen: mélységi védelem XSS,
clickjacking, MIME-találgatás és protokoll-visszaminősítés ellen. A szigorú CSP nonce-alapú: csak
az a szkript fut, amelyik a kérésenként új, kitalálhatatlan nonce-t hordozza, így az injektált
szkript nem; az `object-src 'none'`, `base-uri 'none'` és `frame-ancestors 'none'` további
támadási felületeket zár le. A HSTS a böngészőt csak HTTPS használatára kötelezi (SSL-stripping
ellen) — bevezetéskor rövid max-age-dzsel kezdj. Új CSP-t először Report-Only módban vezess be,
és figyeld a jelentéseket; az `unsafe-inline` és az `unsafe-eval` gyakorlatilag hatástalanítja.

```typescript
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { randomBytes } from "node:crypto";

function securityHeaders(res: ServerResponse): string {
  const nonce = randomBytes(16).toString("base64"); // kérésenként új érték
  res.setHeader("Content-Security-Policy", [
    "default-src 'self'", // alapból csak a saját origin
    `script-src 'nonce-${nonce}' 'strict-dynamic'`, // csak nonce-os (és általa betöltött) szkript fut
    "object-src 'none'", // plugin-alapú támadások tiltása
    "base-uri 'none'", // <base> injektálás ellen
    "frame-ancestors 'none'", // clickjacking ellen
    "img-src 'self' data: https:",
    "connect-src 'self' https://api.example.com", // fetch/XHR/WebSocket célpontok
    "form-action 'self'",
    "report-to csp", // megsértések jelentése
  ].join("; "));
  res.setHeader("Reporting-Endpoints", 'csp="/csp-report"');
  res.setHeader("Strict-Transport-Security", "max-age=63072000; includeSubDomains"); // 2 év, csak HTTPS
  res.setHeader("X-Content-Type-Options", "nosniff"); // ne találgassa a MIME-típust
  res.setHeader("Referrer-Policy", "strict-origin-when-cross-origin"); // ne szivárogjon a teljes URL
  res.setHeader("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  res.setHeader("Cross-Origin-Opener-Policy", "same-origin"); // ablakok közti izoláció
  return nonce;
}

createServer((req: IncomingMessage, res: ServerResponse) => {
  const nonce = securityHeaders(res);
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  // A legitim inline szkript megkapja a nonce-t; egy injektált <script> nem ismerheti
  res.end(`<!doctype html><html><head><title>Demó</title>
<script nonce="${nonce}">console.log("engedélyezett szkript");</script>
</head><body><h1>Biztonságos oldal (${req.url ?? "/"})</h1></body></html>`);
}).listen(8080);
```

## Bemenet-validálás és útvonal-bejárás elleni védelem
<!-- q: Hogyan validáljam helyesen a felhasználói bemenetet, és hogyan védekezzek a path traversal ellen? -->
<!-- tags: input validation, allowlist, path traversal, unicode normalization, pydantic, canonicalization -->

A bemenetet a rendszer határán kell ellenőrizni: típus, hossz, tartomány, formátum, és
engedélylista (mi a megengedett) a tiltólista helyett, mert a tiltólistát mindig ki lehet
játszani. Előbb normalizálj (Unicode NFKC, kisbetűsítés, szóközök), utána validálj, különben a
látszólag azonos, de eltérő kódpontú bemenetek átcsúsznak. A validálás nem helyettesíti a
kimeneti kódolást (SQL-paraméter, HTML-escape) — mindkettő kell. Fájlneveknél az útvonal-bejárás
(`../../etc/passwd`) ellen csak a fájlnevet tartsd meg, engedélylistás karakterekkel, és a
feloldott (szimbolikus linkeket is követő) útvonalról ellenőrizd, hogy a gyökérkönyvtáron belül
marad.

```python
import re
import unicodedata
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

USERNAME_RE = re.compile(r"[a-z0-9_]{3,32}")

class SignupRequest(BaseModel):
    model_config = {"extra": "forbid", "str_strip_whitespace": True}
    username: str = Field(min_length=3, max_length=32)
    display_name: str = Field(min_length=1, max_length=64)
    age: int = Field(ge=13, le=130)
    country: str = Field(pattern=r"^[A-Z]{2}$")  # ISO 3166-1 alpha-2

    @field_validator("username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        v = unicodedata.normalize("NFKC", v).lower()  # előbb normalizálás, aztán ellenőrzés
        if not USERNAME_RE.fullmatch(v):
            raise ValueError("csak kisbetű, szám és aláhúzás")
        return v

    @field_validator("display_name")
    @classmethod
    def no_control_chars(cls, v: str) -> str:
        if any(unicodedata.category(ch).startswith("C") for ch in v):  # vezérlő/láthatatlan karakter
            raise ValueError("vezérlőkarakter nem engedélyezett")
        return v

UPLOAD_ROOT = Path("/srv/app/uploads").resolve()

def safe_upload_path(user_filename: str) -> Path:
    name = Path(user_filename).name  # csak a fájlnév marad, a könyvtárrész eldobva
    if not re.fullmatch(r"[\w.-]{1,100}", name) or name.startswith("."):
        raise ValueError("érvénytelen fájlnév")
    target = (UPLOAD_ROOT / name).resolve()
    if not target.is_relative_to(UPLOAD_ROOT):  # végső ellenőrzés a feloldott úton
        raise ValueError("a gyökérkönyvtáron kívülre mutat")
    return target

if __name__ == "__main__":
    print(SignupRequest(username=" Demo_User99 ", display_name="Demo", age=30, country="HU"))
    for f in ("../../etc/passwd", ".env", "kep.png"):
        try:
            print(safe_upload_path(f))
        except ValueError as e:
            print(f, "->", e)
```

## Fenyegetésmodellezés STRIDE-dal
<!-- q: Hogyan végezzek fenyegetésmodellezést a STRIDE módszerrel? -->
<!-- tags: threat modeling, stride, data flow diagram, trust boundary, security design, risk -->

A fenyegetésmodellezés tervezési időben keresi a hibákat, amikor még olcsó javítani; négy
kérdésre épül: mit építünk (adatfolyam-diagram bizalmi határokkal), mi romolhat el, mit teszünk
ellene, és jól csináltuk-e. A STRIDE hat kategóriája: Spoofing (megszemélyesítés),
Tampering (manipuláció), Repudiation (letagadás), Information disclosure (adatszivárgás),
Denial of service, Elevation of privilege — mindegyik egy biztonsági tulajdonság megsértése.
Minden DFD-elemre végig kell menni a rá jellemző kategóriákon, és mindegyikhez döntés kell:
mérséklés, elfogadás, áthárítás vagy elkerülés. A bizalmi határt átlépő adatfolyamok a
legkockázatosabbak; a modellt minden jelentős változásnál frissíteni kell.

```python
from dataclasses import dataclass, field
from enum import Enum

class Stride(Enum):
    S = "Spoofing / megszemélyesítés (hitelesség)"
    T = "Tampering / manipuláció (integritás)"
    R = "Repudiation / letagadás (letagadhatatlanság)"
    I = "Information disclosure / adatszivárgás (bizalmasság)"
    D = "Denial of service (rendelkezésre állás)"
    E = "Elevation of privilege / jogosultság-emelés (jogosultság)"

# Mely kategóriák jellemzők az egyes DFD-elemtípusokra (STRIDE-per-element heurisztika)
APPLIES = {
    "external": {Stride.S, Stride.R},
    "process": set(Stride),
    "datastore": {Stride.T, Stride.R, Stride.I, Stride.D},
    "dataflow": {Stride.T, Stride.I, Stride.D},
}

@dataclass
class Element:
    name: str
    kind: str  # external | process | datastore | dataflow
    crosses_trust_boundary: bool = False
    mitigations: dict[Stride, str] = field(default_factory=dict)

def review(elements: list[Element]) -> list[str]:
    """Kezeletlen fenyegetések; a bizalmi határt átlépő elemek elöl."""
    findings = []
    for e in sorted(elements, key=lambda x: not x.crosses_trust_boundary):
        for threat in sorted(APPLIES[e.kind] - e.mitigations.keys(), key=lambda t: t.name):
            prio = "MAGAS" if e.crosses_trust_boundary else "közepes"
            findings.append(f"[{prio}] {e.name}: {threat.value}")
    return findings

model = [
    Element("Böngésző (felhasználó)", "external", True, {Stride.S: "OIDC + MFA", Stride.R: "auditnapló"}),
    Element("Böngésző -> API (HTTPS)", "dataflow", True,
            {Stride.T: "TLS 1.3", Stride.I: "TLS 1.3 + HSTS", Stride.D: "rate limit + WAF"}),
    Element("Orders API", "process", False,
            {Stride.S: "JWT-ellenőrzés", Stride.T: "bemenet-validálás", Stride.E: "objektumszintű jogosultság"}),
    Element("Orders DB", "datastore", False, {Stride.I: "titkosítás tároláskor", Stride.T: "külön DB-felhasználó"}),
]

if __name__ == "__main__":
    for f in review(model):
        print(f)
```

## Ellátási lánc (supply chain) biztonsága
<!-- q: Hogyan védjem a projektet a függőségeken és a CI-on keresztüli támadások ellen? -->
<!-- tags: supply chain security, dependencies, lockfile, sbom, ci/cd, pinning, typosquatting, provenance -->

Az ellátási lánc támadásai a függőségeken, a build-rendszeren és a CI-n keresztül érkeznek:
typosquatting (hasonló nevű csomag), dependency confusion (belső csomagnév a nyilvános
registryben), kompromittált karbantartói fiók, rosszindulatú telepítési szkript, átírt
CI-action címke. Védekezés: lockfile hash-ekkel és reprodukálható telepítés (`npm ci`,
`pip install --require-hashes`), telepítési szkriptek tiltása ahol lehet, külső CI-actionök
commit SHA-ra rögzítése, a CI-token legkisebb jogosultsága, privát registry helyes
hatókör-beállítása, aláírások és provenance (Sigstore, SLSA) ellenőrzése, SBOM a buildről, és a
frissítések átnézése (Dependabot/Renovate). Kevesebb függőség = kisebb támadási felület.

```yaml
# Ellátási lánc védelme CI-ban (GitHub Actions példa)
name: build
on: [push, pull_request]   # a pull_request_target titkokhoz fér: idegen kóddal veszélyes!

permissions:
  contents: read   # legkisebb jogosultság: a GITHUB_TOKEN csak olvasni tud

jobs:
  build:
    runs-on: ubuntu-24.04
    steps:
      # Külső action teljes commit SHA-ra rögzítve (a címke átírható); a megjegyzés a verzió.
      # A SHA-t mindig a hivatalos kiadási oldalon ellenőrizd.
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
        with:
          persist-credentials: false   # a token ne maradjon a git-konfigurációban

      - uses: actions/setup-node@39370e3970a6d050c480ffad4ff0ed4d3fdee5af # v4.1.0
        with:
          node-version: 22

      # Reprodukálható telepítés a lockfile-ból; a telepítési szkriptek (postinstall) tiltva
      - run: npm ci --ignore-scripts

      # Ismert sebezhetőségek és a registry-aláírások / provenance ellenőrzése
      - run: npm audit --audit-level=high
      - run: npm audit signatures

      - run: npm test

      # SBOM (szoftver-anyagjegyzék) a lockfile-ban rögzített, devDependency-ként telepített eszközzel
      - run: npx --no-install cyclonedx-npm --output-file sbom.json
```

## Biztonságos C: puffer-túlcsordulás és társai
<!-- q: Hogyan keletkezik a buffer overflow C-ben, és hogyan írjak biztonságos C kódot? -->
<!-- tags: buffer overflow, c, memory safety, strcpy, snprintf, integer overflow, use after free, hardening -->

C-ben a nyelv nem ellenőrzi a tömbhatárokat: ha egy másolás nagyobb a puffernél, a veremben
felülíródhatnak a szomszédos változók és a visszatérési cím, a halomban pedig az allokátor
metaadatai — ez a klasszikus kódfuttatási sebezhetőség. Veszélyes függvények: gets, strcpy,
strcat, sprintf, scanf("%s"); helyettük méretkorlátos változatok (snprintf) és a csonkolás
ellenőrzése. Rokon hibák: egész-túlcsordulás a méretszámításban (túl kicsi foglalás), off-by-one,
előjeles/előjel nélküli összehasonlítás, use-after-free és dupla free. A fordítói védelmek
(stack protector, FORTIFY_SOURCE, PIE, RELRO) és a sanitizerek (ASan, UBSan), valamint a fuzzing
mélységi védelmek — új kódhoz memóriabiztos nyelv (Rust, Go) a legerősebb megoldás.

```c
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* SEBEZHETŐ: nincs hosszellenőrzés; 16+ bájtos névnél túlír a veremben */
void greet_vulnerable(const char *name) {
    char buf[16];
    strcpy(buf, name);  /* hasonlóan veszélyes: gets, sprintf, strcat, scanf("%s") */
    printf("Szia, %s\n", buf);
}

/* JAVÍTOTT: méretkorlátos másolás és a csonkolás felismerése */
int greet(const char *name) {
    char buf[16];
    int n = snprintf(buf, sizeof buf, "%s", name);  /* mindig lezárja '\0'-val */
    if (n < 0 || (size_t)n >= sizeof buf) {
        fprintf(stderr, "túl hosszú név (%d bájt)\n", n);
        return -1;
    }
    printf("Szia, %s\n", buf);
    return 0;
}

/* SEBEZHETŐ: count * size túlcsordulhat => túl kicsi foglalás => halom-túlírás */
void *alloc_records_vulnerable(size_t count, size_t size) {
    return malloc(count * size);
}

/* JAVÍTOTT: túlcsordulás-ellenőrzés; a calloc ezt maga is ellenőrzi és nulláz */
void *alloc_records(size_t count, size_t size) {
    if (size != 0 && count > SIZE_MAX / size) return NULL;
    return calloc(count, size);
}

/* Külső indexnél: >= (nem >), és előjeles értéket előbb negatívra ellenőrizni */
int read_item(const int *arr, size_t len, long idx) {
    if (idx < 0 || (size_t)idx >= len) return -1;
    return arr[idx];
}

int main(void) {
    greet("Demo");
    greet("ez-egy-nagyon-hosszu-nev-ami-nem-fer-bele");
    int *recs = alloc_records(1000, sizeof(int));
    if (!recs) return 1;
    printf("%d\n", read_item(recs, 1000, 1000));  /* -1: határon kívül */
    free(recs);
    recs = NULL;  /* use-after-free és dupla free ellen */
    return 0;
}
/* Fordítás (mélységi védelem, nem helyettesíti a helyes kódot):
 *   gcc -O2 -Wall -Wextra -Wformat=2 -D_FORTIFY_SOURCE=3 -fstack-protector-strong \
 *       -fstack-clash-protection -fPIE -pie -Wl,-z,relro,-z,now prog.c
 * Fejlesztéskor: -fsanitize=address,undefined és fuzzing (libFuzzer, AFL++). */
```

## Többfaktoros hitelesítés: TOTP
<!-- q: Hogyan működik a TOTP alapú kétfaktoros hitelesítés, és hogyan ellenőrizzem biztonságosan? -->
<!-- tags: mfa, 2fa, totp, hotp, rfc 6238, hmac, brute force, replay, passkeys -->

A TOTP (RFC 6238) a közös titokból és az aktuális 30 másodperces időlépésből HMAC-kel számol
6 jegyű kódot; a második faktor („valami, ami nálad van”) a jelszó ellopása esetén is véd. A
titkot kriptográfiailag biztonságos véletlenből (secrets, nem random) kell generálni és
titkosítva tárolni. Ellenőrzéskor ±1 lépés tolerancia kell az óraeltérés miatt, konstans idejű
összevetés, a már felhasznált kód elutasítása (visszajátszás ellen), és szigorú próbálkozási
korlát — csak 10⁶ lehetséges kód van. Korlát: phishing ellen a TOTP sem véd (a kód
továbbítható); arra a WebAuthn/passkey a megoldás, ami az originhez köti a hitelesítést.

```python
import base64
import hashlib
import hmac
import secrets
import struct
import time

def new_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")  # 160 bit, CSPRNG-ből

def totp(secret_b32: str, at: float | None = None, step: int = 30, digits: int = 6) -> str:
    key = base64.b32decode(secret_b32 + "=" * (-len(secret_b32) % 8))
    counter = int((time.time() if at is None else at) // step)
    mac = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()  # az RFC szerint SHA-1
    offset = mac[-1] & 0x0F  # dinamikus csonkolás (RFC 4226)
    code = (struct.unpack(">I", mac[offset:offset + 4])[0] & 0x7FFFFFFF) % 10**digits
    return f"{code:0{digits}d}"

class TotpVerifier:
    def __init__(self) -> None:
        self.last_used_step: dict[str, int] = {}  # egy kód csak egyszer használható
        self.failures: dict[str, int] = {}

    def verify(self, user: str, secret_b32: str, code: str, now: float | None = None) -> bool:
        if self.failures.get(user, 0) >= 5:  # próbálgatás-korlát (élesben időalapú zárolás)
            return False
        current = int((time.time() if now is None else now) // 30)
        for step in (current - 1, current, current + 1):  # ±1 lépés óraeltérésre
            if hmac.compare_digest(totp(secret_b32, step * 30), code):
                if step <= self.last_used_step.get(user, -1):
                    return False  # már felhasznált (vagy régebbi) kód: visszajátszás
                self.last_used_step[user] = step
                self.failures[user] = 0
                return True
        self.failures[user] = self.failures.get(user, 0) + 1
        return False

if __name__ == "__main__":
    s = new_secret()  # QR-kódban: otpauth://totp/App:user?secret=...&issuer=App
    v = TotpVerifier()
    code = totp(s)
    print(code, v.verify("user-1", s, code), v.verify("user-1", s, code))  # True, majd False
    # RFC 6238 tesztvektor (SHA-1, T=59 s, 8 jegy): 94287082
    print(totp(base64.b32encode(b"12345678901234567890").decode(), at=59, digits=8))
```
