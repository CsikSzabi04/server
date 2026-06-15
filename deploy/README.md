# Auri backend — 0–24 üzemeltetés Oracle Cloud Always Free VPS-en

Cél: az **Ollama + a `server/` + Piper** egy mindig-bekapcsolt, **ingyenes** felhős
gépen fusson, hogy a Vercelen lévő AuriGPT **akkor is működjön, ha a saját géped ki van kapcsolva**.

```
[Vercel: web + proxy]  ──HTTPS──▶  [Oracle VPS 0–24]
                                     ├ server/  (:8787, kulcsvédett)
                                     ├ Ollama   (:11434, csak lokál)
                                     └ Piper TTS
```

---

## 1. fázis — Oracle Cloud (böngésző, ezt csak te tudod)

1. **Regisztráció:** <https://www.oracle.com/cloud/free/> → „Start for free”. Bankkártya kell
   **verifikációhoz** (nem terheli; az „Always Free” erőforrások ingyenesek maradnak).
   Válassz egy **Home Region**-t, ahol van szabad ARM kapacitás (pl. Frankfurt, Amsterdam).
2. **Instance létrehozása:** Console → **Compute → Instances → Create instance**.
   - **Image:** Canonical **Ubuntu 22.04** (vagy 24.04).
   - **Shape:** „Change shape” → **Ampere (ARM)** → **VM.Standard.A1.Flex** →
     állítsd **4 OCPU / 24 GB RAM**-ra (ez belefér az Always Free keretbe).
     *(Ha „out of capacity” jön: próbálj kevesebb magot, másik AD-t, vagy másik régiót.)*
   - **SSH keys:** „Generate a key pair for me” → **töltsd le a private key-t** (kelleni fog).
   - **Create.** Pár perc múlva lesz egy **Public IP** — jegyezd fel.
3. **Portok megnyitása (KÉT helyen kell!):**
   - **OCI Security List:** Networking → a VCN → Subnet → Security List → **Add Ingress Rules**:
     - TLS-sel (domainnel): nyisd a **80** és **443** TCP-t `0.0.0.0/0`-ra.
     - Domain nélkül (egyszerű HTTP): nyisd a **8787** TCP-t `0.0.0.0/0`-ra.
   - A 22 (SSH) alapból nyitva van.
   - ⚠️ Az Ubuntu image-en **belül is** van tűzfal — a setup script `ufw`-vel megnyitja ugyanezeket.
   - **A 11434-et SOHA ne nyisd meg** (az Ollama maradjon csak lokál a VPS-en).

> **Domain vagy sem?** A böngésző sosem hívja közvetlenül a backendet — csak a Vercel
> szerveroldali proxy (api/chat.ts) hívja. Ezért **TLS nem kötelező**: mehet sima
> `http://<IP>:8787` is, a kulcs véd. Biztonságosabb viszont a HTTPS: ahhoz egy domain kell
> (akár ingyenes, pl. **DuckDNS** → `auri.duckdns.org`, ami a VPS IP-jére mutat), és a script
> a `DOMAIN=...` megadásakor automatikusan tesz rá Caddy + Let's Encrypt TLS-t.

---

## 2. fázis — a VPS beállítása (SSH, szinte csak másolás)

SSH-zz be (a letöltött kulccsal):

```bash
ssh -i /eleresi/ut/private.key ubuntu@<ORACLE_PUBLIC_IP>
```

Töltsd fel a `server/` kódot a gépre `/opt/auri/server` alá. Két mód:

```bash
# A) ha a kód fent van GitHubon:
sudo mkdir -p /opt/auri && sudo chown $USER /opt/auri
git clone https://github.com/CsikSzabi04/server.git /opt/auri/server
#  (ha a repo a 3 mappás monorepo, akkor a server almappa kell: lásd lentebb)

# B) vagy a saját gépedről scp-vel (a server/ mappát):
#   scp -i private.key -r D:\Server\server ubuntu@<IP>:/opt/auri/server
```

Másold fel ezt a `deploy/setup-vps.sh`-t is, majd futtasd:

```bash
# HTTPS-sel (ajánlott), ha van domained a VPS IP-re mutatva:
sudo DOMAIN=auri.pelda.hu bash /opt/auri/server/deploy/setup-vps.sh

# vagy egyszerű HTTP (domain nélkül):
sudo bash /opt/auri/server/deploy/setup-vps.sh
```

A script: Node 20 + Ollama (keep-alive/flash-attention + modellek) + Piper (magyar hang)
+ buildeli a szervert + **systemd szolgáltatásként** indítja (auto-start, crash-restart),
megnyitja a tűzfalat, és kiírja a **végén az API-kulcsot** + a Vercel-be másolandó értékeket.

Ellenőrzés:
```bash
curl http://127.0.0.1:8787/health       # {"status":"ok","model":...,"ollama":"up","tts":"up"}
systemctl status auri-server ollama     # mindkettő "active (running)"
```

---

## 3. fázis — Vercel összekötése

A Vercel projekt (web) **Settings → Environment Variables**:

```
AURI_SERVER_URL      = https://auri.pelda.hu        # vagy http://<ORACLE_IP>:8787
AURI_SERVER_API_KEY  = <a script által kiírt kulcs>
VITE_API_URL         = /api/chat                     # hogy a frontend a proxyt használja
```

Redeploy a Vercelen. Ezután az AuriGPT **0–24 megy**, a géped állapotától függetlenül.

---

## Üzemeltetési parancsok a VPS-en

```bash
sudo systemctl restart auri-server      # szerver újraindítás (pl. kód frissítés után)
journalctl -u auri-server -f            # élő logok
ollama list                             # telepített modellek
ollama pull qwen2.5:3b-instruct         # új modell
#   majd a server/.env-ben OLLAMA_MODEL=... és: sudo systemctl restart auri-server
```

Kód frissítés: `git pull` (vagy scp), majd `cd /opt/auri/server && npm install && npm run build && sudo systemctl restart auri-server`.

---

## Teljesítmény Oracle ARM-on

A 4 mag / 24 GB RAM **bőven elég** egy 3B modellhez CPU-n, sőt egy 7–8B is elfut (lassabban).
A `keep_alive` + warmup miatt a modell bent marad a memóriában, így a válaszok gyorsak.
Több modell is hot lehet egyszerre (`OLLAMA_MAX_LOADED_MODELS=2`).
