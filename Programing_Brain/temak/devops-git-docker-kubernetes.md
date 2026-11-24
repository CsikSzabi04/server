# DevOps: Git, Docker, Kubernetes, CI/CD
<!-- tech: devops -->
<!-- aliases: devops, git, docker, kubernetes, k8s, helm, terraform, ci/cd, github actions, prometheus, sre -->

A DevOps a fejlesztés és az üzemeltetés összekapcsolása automatizálással: verziókezelés (Git), reprodukálható csomagolás (Docker image), deklaratív futtatás és skálázás (Kubernetes, Helm), infrastruktúra kódként (Terraform), automatikus build-teszt-deploy láncok (CI/CD), valamint megfigyelhetőség (metrikák, strukturált naplók, riasztások). A cél a gyakori, kicsi, visszafordítható kiadás: minden változás verziózott, review-zott és automatikusan tesztelt, a kiadás pedig fokozatos (canary, blue-green), mért és gyorsan visszagörgethető. A titkok soha nem kerülnek a repóba vagy az image-be.

## Git belülről: objektumok (blob, tree, commit)
<!-- q: Hogyan tárolja a Git az adatokat belül, mik a blob, tree és commit objektumok? -->
<!-- tags: git internals, blob, tree, commit, sha1, content addressable, packfile, cat-file -->

A Git egy tartalom-címzett (content-addressable) objektumtár: minden objektum azonosítója a tartalmának hash-e (SHA-1, újabban opcionálisan SHA-256). A *blob* egy fájl tartalma (név nélkül), a *tree* egy könyvtár (név → blob/tree hash), a *commit* egy gyökér-tree-re, a szülő commit(ok)ra, a szerzőre és az üzenetre mutat, az annotált *tag* pedig egy commitra. Mivel a hash a tartalomból számolódik, az azonos fájlok egyszer tárolódnak, és bármely bájt megváltozása az összes felette lévő hash-t megváltoztatja — ez adja az integritást. A laza objektumokat a `git gc` delta-tömörített packfile-okba rendezi.

```bash
git init demo && cd demo
echo "hello" > a.txt && git add a.txt
find .git/objects -type f                 # .git/objects/ce/013625030ba8dba906f756967f9e9ca394464a
git cat-file -t ce01362                   # blob
git commit -qm "első commit"
git cat-file -p HEAD                      # tree <hash>, author, committer, üzenet
git cat-file -p 'HEAD^{tree}'             # 100644 blob ce0136...    a.txt
git rev-parse HEAD:a.txt                  # a fájl blob-hash-e
git gc -q && git count-objects -vH        # packfile-ba tömörítve
```

```python
import hashlib
import pathlib
import zlib

def git_blob_hash(data: bytes) -> str:
    # objektum = "<típus> <méret>\0" fejléc + tartalom; az azonosító ennek SHA-1-e
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()

def read_loose_object(repo: str, sha: str) -> tuple[str, bytes]:
    # Laza objektum: zlib-tömörített fájl .git/objects/<2 karakter>/<38 karakter> alatt
    raw = zlib.decompress(pathlib.Path(repo, ".git", "objects", sha[:2], sha[2:]).read_bytes())
    header, _, body = raw.partition(b"\x00")
    kind, size = header.decode().split()
    assert int(size) == len(body), "sérült objektum"
    return kind, body

print(git_blob_hash(b"hello\n"))   # ce013625030ba8dba906f756967f9e9ca394464a (mint a git)
```

## Git refek, HEAD és reflog: elveszett munka visszaszerzése
<!-- q: Mik a Git refek és a HEAD, és hogyan szerezzek vissza elveszettnek hitt commitokat? -->
<!-- tags: git refs, head, branch, reflog, detached head, reset, recovery, fsck -->

A branch csupán egy fájl (`.git/refs/heads/<név>`), amely egy commit hash-ét tartalmazza; a `HEAD` egy szimbolikus ref, ami az aktuális branchre (vagy detached állapotban közvetlenül egy commitra) mutat. Commitoláskor a branch egyszerűen az új commitra lép. A *reflog* minden ref-mozgást naplóz helyben (~90 napig), ezért egy elhibázott `reset --hard`, rebase vagy törölt branch szinte mindig visszaszerezhető: megkeresed a régi állapotot, és branchet teszel rá. A reflog nem kerül push-ra, ezért egy másik gépen nem segít; a ref nélküli commitokat a `gc` idővel véglegesen törli.

```bash
cat .git/HEAD                       # ref: refs/heads/main  (szimbolikus ref)
cat .git/refs/heads/main            # egyetlen commit hash: a branch csak egy mutató
git show-ref                        # minden ref: branchek, tagek, remote-ok

# Baleset: "eltűnt" 3 commit
git reset --hard HEAD~3
git reflog                          # ... HEAD@{1}: commit: fontos munka
git branch mentes HEAD@{1}          # visszaszerzés: branch a régi állapotra
git reset --hard HEAD@{1}           # vagy egyszerűen vissza oda

# Félresikerült rebase visszacsinálása: ORIG_HEAD a művelet előtti állapot
git reset --hard ORIG_HEAD

# Törölt branch: a reflogban a branch utolsó commitja is megvan
git reflog --date=relative | grep "feature/kereso"

# Semmilyen refből el nem érhető commitok keresése
git fsck --lost-found

# Detached HEAD: commitolhatsz, de branch nélkül a munka "lebeg"
git switch --detach v1.2.0
git switch -c hotfix/1.2.1          # mentsd branchbe, mielőtt továbblépsz
```

## Rebase vs. merge
<!-- q: Mi a különbség a git rebase és a merge között, és mikor melyiket használjam? -->
<!-- tags: git rebase, git merge, linear history, force with lease, autosquash, fixup, squash merge -->

A `merge` összefésüli a két ágat egy merge committal: a történet a valóságot tükrözi, de elágazó, és a sok merge commit zajos lehet. A `rebase` a branch commitjait újrajátssza a cél tetején: lineáris, könnyen olvasható történetet ad, de *új hash-ű* commitokat hoz létre, ezért csak olyan branchen használd, amire más nem épít — közös branchen tilos. Push-olt saját branch rebase-e után `--force-with-lease` kell (nem sima `--force`), ami nem írja felül mások közben érkezett munkáját. Bevált gyakorlat: a saját feature branch rebase-elése a main-re, a PR-ek squash- vagy merge committal való beolvasztása.

```bash
# MERGE: a feature egy egységként látszik a történetben
git switch main
git merge --no-ff feature/login

# REBASE: a saját branch frissítése a main-re, lineáris történet
git switch feature/login
git fetch origin
git rebase origin/main              # konfliktus: javítás -> git add <fájl> -> git rebase --continue
git rebase --abort                  # ... vagy minden vissza a rebase előtti állapotra
git push --force-with-lease         # csak ha a remote azóta nem változott

# Takarítás PR előtt: javító commit a megfelelő korábbihoz, automatikus összevonás
git commit --fixup=abc1234          # "fixup! <eredeti üzenet>"
git rebase -i --autosquash origin/main

# Kényelmi beállítások
git config --global pull.rebase true        # pull = fetch + rebase (nincs felesleges merge commit)
git config --global rerere.enabled true     # a már egyszer feloldott konfliktusokra emlékszik

# Egyetlen commit átvétele másik branchről
git cherry-pick -x 4f2c9e1          # -x: hivatkozás az eredeti commitra az üzenetben
```

## Hibás commit keresése git bisecttel
<!-- q: Hogyan találjam meg git bisecttel, melyik commit vezette be a hibát? -->
<!-- tags: git bisect, regression, binary search, debugging, bisect run, automation -->

A `git bisect` bináris kereséssel találja meg a regressziót okozó commitot: megadsz egy „jó” és egy „rossz” pontot, a Git a középső commitot veszi elő, te pedig megmondod, jó-e — így 1000 commit között kb. 10 lépés elég. A `git bisect run` teljesen automatizálja egy szkripttel, amelynek kilépési kódja dönt: 0 = jó, 1–124 és 126–127 = rossz, 125 = „nem tesztelhető, ugord át” (pl. nem fordul). Ehhez fontos, hogy minden commit buildelhető legyen — ezért éri meg a kicsi, önálló commit. A végén a `bisect reset` visszaállít.

```bash
git bisect start
git bisect bad                      # a jelenlegi HEAD hibás
git bisect good v2.3.0              # ez a kiadás még jó volt
# Kézi mód: a Git kiveszi a középső commitot; tesztelés után:
#   git bisect good   vagy   git bisect bad

# Automatikus mód: a szkript kilépési kódja dönt
cat > /tmp/bisect-check.sh <<'EOF'
#!/usr/bin/env bash
set -uo pipefail
npm ci --silent || exit 125                     # nem buildelhető -> commit átugrása
npx vitest run tests/regression/price.test.ts   # 0 = jó, nem nulla = rossz
EOF
chmod +x /tmp/bisect-check.sh
git bisect run /tmp/bisect-check.sh             # a végén kiírja: "<hash> is the first bad commit"

git bisect log > bisect.log         # a keresés naplója (megosztható, visszajátszható)
git bisect reset                    # vissza az eredeti HEAD-re
```

## Git hookok: pre-commit és commit-msg
<!-- q: Hogyan használjak git hookokat ellenőrzésekre commit előtt, csapatszinten? -->
<!-- tags: git hooks, pre-commit, commit-msg, core.hooksPath, linting, conventional commits, secret scanning -->

A git hookok szkriptek, amelyeket a Git bizonyos eseményeknél futtat: a `pre-commit` a commit előtt (lint, formázás, titokkeresés), a `commit-msg` az üzenet ellenőrzésére, a `pre-push` push előtt (gyors tesztek). A `.git/hooks` mappa nem verziókezelt, ezért csapatban a `core.hooksPath`-szal egy verziózott mappára mutass (vagy használd a pre-commit / husky / lefthook eszközt). A hook csak a stage-elt fájlokat nézze, és legyen gyors, különben a fejlesztők `--no-verify`-jal megkerülik. Mivel a hook megkerülhető, ugyanezeket az ellenőrzéseket a CI-ban is futtatni kell.

```bash
git config core.hooksPath .githooks          # verziózott hook-mappa
mkdir -p .githooks

cat > .githooks/pre-commit <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
# Csak a stage-elt (hozzáadott/módosított) Python fájlok
mapfile -t files < <(git diff --cached --name-only --diff-filter=ACM -- '*.py')
if [ ${#files[@]} -gt 0 ]; then
  ruff check "${files[@]}"
  ruff format --check "${files[@]}"
fi
# Titoknak tűnő tartalom (privát kulcs, felhő-hozzáférési kulcs mintája) a staged diffben
if git diff --cached -U0 | grep -Eq '^\+.*(-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16})'; then
  echo "Titoknak tűnő tartalom a commitban — megszakítva." >&2
  exit 1
fi
EOF

cat > .githooks/commit-msg <<'EOF'
#!/usr/bin/env bash
# Conventional Commits: típus(scope): leírás
pattern='^(feat|fix|docs|refactor|test|chore|perf|ci|build)(\([a-z0-9-]+\))?!?: .{3,}'
if ! head -n1 "$1" | grep -Eq "$pattern"; then
  echo "Hibás commit üzenet. Példa: feat(auth): jelszó-visszaállítás" >&2
  exit 1
fi
EOF

chmod +x .githooks/pre-commit .githooks/commit-msg
```

## Branching stratégiák: trunk-based, GitHub flow, Git flow
<!-- q: Milyen branching stratégiát válasszak: trunk-based, GitHub flow vagy Git flow? -->
<!-- tags: branching strategy, trunk based development, github flow, git flow, feature flags, release branch, hotfix -->

A *trunk-based* fejlesztésben mindenki rövid életű (órák–1-2 nap) branchekről gyakran olvaszt a main-be, a félkész funkciókat *feature flag* rejti; ez a folyamatos szállítás (CD) alapja, mert kevés a merge-konfliktus és a main mindig kiadható. A *GitHub flow* ennek egyszerű formája: branch → PR → review + CI → merge → deploy. A *Git flow* (develop, release és hotfix branchek) ritka, ütemezett kiadásokhoz és több támogatott verzióhoz illik (dobozos szoftver, mobilapp), folyamatos deploynál túl nehézkes. Bármelyiknél kulcs a main védelme: kötelező PR, zöld CI és review.

```bash
# TRUNK-BASED / GITHUB FLOW
git switch -c feat/search-filters
# ... kis commitok; a félkész funkció flag mögött:  if (flags.searchFilters) { ... }
git push -u origin feat/search-filters
gh pr create --fill                          # PR -> review -> zöld CI -> squash merge
gh pr merge --squash --delete-branch

# Kiadás tag-gel a main-ről (a main mindig kiadható állapotban van)
git switch main && git pull
git tag -a v1.8.0 -m "v1.8.0" && git push origin v1.8.0

# Hotfix egy régebbi kiadásra: release branch a tagről, a javítás a main-en készül
git switch -c release/1.8 v1.8.0
git cherry-pick -x 4f2c9e1                   # a main-en már beolvasztott javítás
git tag -a v1.8.1 -m "v1.8.1"
git push origin release/1.8 v1.8.1

# GIT FLOW vázlat (ütemezett kiadásokhoz):
#   main     <- csak kiadott verziók (tagek)
#   develop  <- integrációs ág
#   feature/* -> develop,  release/* -> main + develop,  hotfix/* -> main + develop
```

## Dockerfile: multi-stage build, réteg-cache, nem root felhasználó
<!-- q: Hogyan írjak jó Dockerfile-t multi-stage builddel, cache-eléssel és nem root felhasználóval? -->
<!-- tags: dockerfile, multi stage build, layer caching, non root, docker image size, security, healthcheck -->

A Docker image rétegekből áll, és egy utasítás rétegét csak akkor kell újraépíteni, ha az utasítás vagy az előző réteg változott — ezért a ritkán változó lépések (függőségek telepítése a lockfile alapján) kerüljenek előre, a forráskód másolása a végére. A *multi-stage* build a fordító-eszközöket és dev-függőségeket a build-fázisban hagyja, a végső image csak a futtatáshoz szükséges fájlokat tartalmazza (kisebb, kevesebb sérülékenység). Futtass nem root felhasználóként, rögzítsd az alap-image verzióját, használj `.dockerignore`-t (`.git`, `node_modules`, `.env` kizárása), és exec formájú `CMD`-t, hogy a processz megkapja a SIGTERM-et. Titkot soha ne tegyél `ENV`-be vagy `COPY`-val az image-be — build-időben `--mount=type=secret` kell.

```dockerfile
# syntax=docker/dockerfile:1.7

# ---- 1. fázis: függőségek (cache-elődik, amíg a lockfile nem változik)
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

# ---- 2. fázis: build, majd a dev-függőségek eldobása
FROM deps AS build
COPY . .
RUN npm run build && npm prune --omit=dev

# ---- 3. fázis: minimális futtató image
FROM node:22-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/dist ./dist
COPY --chown=node:node package.json ./
# Nem root felhasználó (a node image beépített "node" felhasználója).
# Figyelem: Dockerfile-ban a # csak sor elején komment, utasítás végén nem!
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:3000/healthz || exit 1
# exec forma: a node a PID 1, megkapja a SIGTERM-et -> graceful shutdown
CMD ["node", "dist/server.js"]
```

```bash
# Build-idejű titok (pl. privát registry token) úgy, hogy NEM kerül rétegbe:
#   RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci
docker build --secret id=npmrc,src="$HOME/.npmrc" -t shop/api:1.8.0 .
docker image ls shop/api                    # méret ellenőrzése
docker history shop/api:1.8.0               # melyik réteg mekkora
```

## Docker Compose helyi fejlesztéshez
<!-- q: Hogyan használjam a docker compose-t több szolgáltatás helyi futtatására? -->
<!-- tags: docker compose, local development, healthcheck, depends_on, volumes, environment, compose watch -->

A Docker Compose egy YAML-fájlban írja le a szolgáltatásokat (API, adatbázis, cache), a hálózatot és a köteteket; a szolgáltatások a nevükön érik el egymást (`db:5432`). A `depends_on` önmagában csak az indulási sorrendet adja meg, a függőség *készenlétét* a `condition: service_healthy` + `healthcheck` garantálja. Az adatbázis adatai nevesített kötetben maradjanak meg, a titkok `.env` fájlból jöjjenek (amely a `.gitignore`-ban van), a `${VAR:?üzenet}` szintaxis pedig hiányzó érték esetén azonnal hibát ad. A `docker compose watch` kódváltozáskor szinkronizál vagy újraépít; élesbe a Compose helyett általában Kubernetes vagy menedzselt szolgáltatás való.

```yaml
# compose.yaml — titkok a .env fájlból (ami NINCS verziókezelve)
services:
  api:
    build:
      context: .
      target: runtime
    ports: ["3000:3000"]
    environment:
      DATABASE_URL: postgres://app:${DB_PASSWORD:?a DB_PASSWORD hiányzik a .env-ből}@db:5432/app
      REDIS_URL: redis://cache:6379
    depends_on:
      db:
        condition: service_healthy       # megvárja, amíg a DB valóban fogad kapcsolatot
      cache:
        condition: service_started
    restart: unless-stopped
    develop:
      watch:                             # docker compose watch
        - action: sync
          path: ./src
          target: /app/src
        - action: rebuild
          path: package-lock.json

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: app
    volumes:
      - pgdata:/var/lib/postgresql/data  # nevesített kötet: újraindítás után is megmarad
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app"]
      interval: 5s
      retries: 10

  cache:
    image: redis:7-alpine
    command: ["redis-server", "--appendonly", "yes"]

volumes:
  pgdata:
```

## Kubernetes: Pod és Deployment
<!-- q: Mi a Pod és a Deployment Kubernetesben, és hogyan írjak biztonságos Deployment manifestet? -->
<!-- tags: kubernetes, pod, deployment, rolling update, replicas, security context, rollout -->

A *Pod* a Kubernetes legkisebb egysége: egy vagy több, közös hálózati névteret és köteteket használó konténer; a podok halandók és cserélhetők, közvetlenül ritkán hozunk létre őket. A *Deployment* deklaratívan leírja a kívánt állapotot (image, replikaszám), és ReplicaSet-eken keresztül gondoskodik róla: összeomlott podot pótol, frissítéskor *rolling update*-et végez, és visszagörgethető (`kubectl rollout undo`). A `maxUnavailable: 0` + `maxSurge: 1` frissítés közben sem csökkenti a kapacitást; a `preStop` szünet kivárja, hogy a pod kikerüljön a Service végpontjai közül, így nincs eldobott kérés. Mindig rögzített image-taget (vagy digestet) használj, `latest`-et soha.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  labels: { app: api }
spec:
  replicas: 3
  revisionHistoryLimit: 5
  selector:
    matchLabels: { app: api }            # létrehozás után nem módosítható
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0                  # frissítés közben sem csökken a kapacitás
      maxSurge: 1
  template:
    metadata:
      labels: { app: api }
    spec:
      terminationGracePeriodSeconds: 30
      securityContext:
        runAsNonRoot: true
        seccompProfile: { type: RuntimeDefault }
      containers:
        - name: api
          image: registry.example.com/shop/api:1.8.0     # rögzített tag, soha :latest
          ports:
            - name: http
              containerPort: 3000
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: { drop: ["ALL"] }
          lifecycle:
            preStop:
              exec: { command: ["sleep", "5"] }   # kivárja az endpoint-frissítést
      topologySpreadConstraints:                  # podok szétszórása zónák között
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels: { app: api }
# kubectl apply -f deploy.yaml && kubectl rollout status deploy/api
# kubectl rollout history deploy/api;  kubectl rollout undo deploy/api
```

## Kubernetes Service és Ingress
<!-- q: Hogyan tegyem elérhetővé az alkalmazást Kubernetesben Service-szel és Ingress-szel? -->
<!-- tags: kubernetes service, clusterip, ingress, tls, cert-manager, load balancing, dns -->

A *Service* stabil virtuális IP-t és DNS-nevet ad a változó podoknak (`api.<namespace>.svc.cluster.local`), és a label-selectornak megfelelő, *ready* állapotú podok között osztja el a forgalmat; típusai: `ClusterIP` (csak klaszteren belül), `NodePort`, `LoadBalancer` (felhős terheléselosztó). Az *Ingress* HTTP(S) szintű útválasztást ad host és útvonal alapján egyetlen belépési ponton keresztül, a TLS-t pedig a cert-manager automatikusan kezelheti (Let's Encrypt). Ingress controller (ingress-nginx, Traefik) nélkül az Ingress objektum semmit nem csinál; az újabb Gateway API rugalmasabb utódja. A nevesített `targetPort` miatt a konténerport átszámozása nem töri el a Service-t.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api
spec:
  type: ClusterIP
  selector: { app: api }               # label-egyezésű, READY podok kapnak forgalmat
  ports:
    - name: http
      port: 80                         # a Service portja
      targetPort: http                 # a konténer nevesített portja
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: shop
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod      # automatikus TLS-tanúsítvány
    nginx.ingress.kubernetes.io/proxy-body-size: 10m
spec:
  ingressClassName: nginx
  tls:
    - hosts: [shop.example.com]
      secretName: shop-tls
  rules:
    - host: shop.example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api
                port: { name: http }
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web
                port: { number: 80 }
```

## Kubernetes ConfigMap és Secret
<!-- q: Hogyan adjak át konfigurációt és titkokat Kubernetesben ConfigMappal és Secrettel? -->
<!-- tags: configmap, secret, environment variables, volume mount, sealed secrets, external secrets, kubernetes -->

A *ConfigMap* nem titkos konfigurációt, a *Secret* érzékeny adatot (jelszó, token, tanúsítvány) tárol; mindkettő env-változóként vagy fájlként csatolható a podba. A Secret alapból csak base64-kódolt, *nem titkosított*: kapcsold be az etcd-titkosítást, korlátozd RBAC-kal, és a repóba soha ne commitold nyersen — helyette Sealed Secrets, SOPS vagy External Secrets Operator (felhős titoktárból szinkronizál). Az env-változók csak a pod indulásakor olvasódnak be, a kötetként csatolt fájlok viszont frissülnek; konfig-változáskor ezért rollout kell (`kubectl rollout restart` vagy checksum-annotáció Helmben).

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
data:
  LOG_LEVEL: info
  FEATURE_SEARCH_FILTERS: "true"         # minden érték string!
  app.yaml: |
    cache:
      ttlSeconds: 300
---
apiVersion: v1
kind: Secret
metadata:
  name: api-secrets
type: Opaque
stringData:                              # base64-be kerül, de ez NEM titkosítás
  DATABASE_URL: postgres://app:CHANGE_ME@db:5432/app   # helyőrző; valódit soha ne commitolj
---
apiVersion: v1
kind: Pod
metadata:
  name: api-config-demo
spec:
  containers:
    - name: api
      image: registry.example.com/shop/api:1.8.0
      envFrom:
        - configMapRef: { name: api-config }         # minden kulcs env-változó lesz
      env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef: { name: api-secrets, key: DATABASE_URL }
      volumeMounts:
        - name: config
          mountPath: /etc/app                        # fájlként: újraindítás nélkül is frissül
          readOnly: true
  volumes:
    - name: config
      configMap:
        name: api-config
        items: [{ key: app.yaml, path: app.yaml }]
```

## Health probe-ok és erőforrás-korlátok
<!-- q: Hogyan állítsam be a liveness, readiness és startup probe-okat és az erőforrás-korlátokat? -->
<!-- tags: liveness probe, readiness probe, startup probe, resources, requests, limits, oomkilled, kubernetes -->

A *readiness* probe dönti el, kaphat-e a pod forgalmat (a sikertelen pod kikerül a Service mögül, de nem indul újra), a *liveness* probe azt, hogy beragadt-e (sikertelenség esetén a kubelet újraindítja a konténert), a *startup* probe pedig lassú indulásnál védi a podot, amíg fel nem áll. A liveness ne ellenőrizze a külső függőségeket (DB): egy adatbázis-kiesés így az összes pod újraindítási hullámát okozná. A `requests` az ütemezés alapja (ennyit garantál a node), a memória-`limit` túllépése OOMKill; a CPU-limit throttlingot okoz, ezért sokan csak requestet adnak meg CPU-ra. Request nélkül a HPA sem tud százalékos kihasználtságot számolni.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: api-probes-demo
spec:
  containers:
    - name: api
      image: registry.example.com/shop/api:1.8.0
      ports: [{ name: http, containerPort: 3000 }]
      resources:
        requests: { cpu: 250m, memory: 256Mi }   # ütemezés: ennyit garantál a node
        limits: { memory: 512Mi }                # felette OOMKill; CPU-limit szándékosan nincs
      startupProbe:                              # amíg nem sikeres, a többi probe nem fut
        httpGet: { path: /healthz, port: http }
        periodSeconds: 5
        failureThreshold: 30                     # legfeljebb 150 s indulási idő
      readinessProbe:                            # kaphat-e forgalmat? (DB elérhető, cache meleg)
        httpGet: { path: /readyz, port: http }
        periodSeconds: 5
        failureThreshold: 3
      livenessProbe:                             # beragadt-e? CSAK a processz saját állapota
        httpGet: { path: /healthz, port: http }
        periodSeconds: 10
        timeoutSeconds: 2
        failureThreshold: 3
# Diagnózis: kubectl describe pod <név>   (Events: Readiness probe failed, OOMKilled)
#            kubectl top pod               (tényleges CPU/memória fogyasztás)
```

## Automatikus skálázás: HPA és PodDisruptionBudget
<!-- q: Hogyan skálázzam automatikusan a podokat terhelés alapján Kubernetesben? -->
<!-- tags: hpa, horizontal pod autoscaler, autoscaling, custom metrics, pod disruption budget, scaling behavior -->

A HorizontalPodAutoscaler a megfigyelt metrika (CPU-kihasználtság a `requests`-hez képest, memória, vagy egyedi/külső metrika, pl. kérés/s, sorhossz) alapján állítja a replikák számát `minReplicas` és `maxReplicas` között. A `behavior` szakasz szabályozza a skálázás sebességét: felfelé gyorsan, lefelé óvatosan (stabilizációs ablakkal), hogy ne „lengjen” (flapping). A sorhossz alapú skálázáshoz (Kafka, SQS) a KEDA a kényelmes megoldás. A *PodDisruptionBudget* garantálja, hogy node-karbantartás vagy klaszterfrissítés közben is maradjon elég futó pod.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 3
  maxReplicas: 30
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 65                 # a requests.cpu 65%-a a cél
    - type: Pods                                 # egyedi metrika (Prometheus Adapterrel)
      pods:
        metric: { name: http_requests_per_second }
        target: { type: AverageValue, averageValue: "50" }
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies: [{ type: Percent, value: 100, periodSeconds: 30 }]   # max duplázás 30 s alatt
    scaleDown:
      stabilizationWindowSeconds: 300            # 5 perc nyugalom leskálázás előtt
      policies: [{ type: Pods, value: 2, periodSeconds: 60 }]
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api
spec:
  minAvailable: 2                                # karbantartáskor is legalább 2 pod fut
  selector:
    matchLabels: { app: api }
```

## Helm chartok
<!-- q: Hogyan csomagoljam és telepítsem Kubernetes alkalmazásomat Helm charttal? -->
<!-- tags: helm, chart, values, templates, release, rollback, kubernetes packaging -->

A Helm a Kubernetes csomagkezelője: a *chart* Go-sablonokból (`templates/`) és alapértékekből (`values.yaml`) áll, telepítéskor a környezetenkénti értékfájlokkal (`values-prod.yaml`) és `--set` kapcsolókkal kitöltve *release* lesz belőle, verziótörténettel és visszagörgetéssel. Az `--atomic` sikertelen telepítésnél automatikusan visszaáll, a `checksum/config` annotáció pedig konfig-változáskor kikényszeríti a podok újraindítását. Telepítés előtt a `helm template | kubectl diff` megmutatja, mi változna. Sok sablonlogika helyett tartsd egyszerűen a chartot; GitOps-szal (Argo CD, Flux) a release-eket a repó állapota vezérli.

```yaml
# charts/api/values.yaml — környezetenként felülírható alapértékek
replicaCount: 2
image:
  repository: registry.example.com/shop/api
  tag: ""                       # üres -> .Chart.AppVersion
resources:
  requests: { cpu: 250m, memory: 256Mi }
env:
  LOG_LEVEL: info
---
# charts/api/templates/deployment.yaml (Go-sablon)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "api.fullname" . }}
  labels: {{- include "api.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels: {{- include "api.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels: {{- include "api.selectorLabels" . | nindent 8 }}
      annotations:
        # a ConfigMap hash-e: konfig-változáskor automatikus rollout
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
    spec:
      containers:
        - name: api
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          resources: {{- toYaml .Values.resources | nindent 12 }}
          env:
            {{- range $key, $value := .Values.env }}
            - name: {{ $key }}
              value: {{ $value | quote }}
            {{- end }}
```

```bash
helm lint charts/api
helm template api charts/api -f values-prod.yaml | kubectl diff -f -   # mi változna?
helm upgrade --install api charts/api -n shop --create-namespace \
  -f values-prod.yaml --set image.tag=1.8.1 --atomic --timeout 5m      # hiba -> automatikus rollback
helm history api -n shop
helm rollback api 3 -n shop
```

## CI/CD pipeline GitHub Actionsszel
<!-- q: Hogyan építsek CI/CD pipeline-t GitHub Actionsszel image builddel és deployjal? -->
<!-- tags: ci/cd, github actions, docker build, container registry, deployment, environments, oidc, pipeline -->

A CI/CD pipeline minden main-re érkező változásból automatikusan image-et épít, registrybe tolja, majd fokozatosan kiadja (staging → production). Az image-taget a commit SHA-ja adja (megváltoztathatatlan, visszakövethető), a Docker rétegcache (`type=gha`) a futások között megmarad. A GitHub *environments* jóváhagyást, védett titkokat és deploy-történetet ad; felhőhöz OIDC-vel (`id-token: write`) érdemes hitelesíteni, rövid életű tokennel hosszú életű kulcsok helyett. A `permissions` legyen minimális, a harmadik féltől származó actionöket pedig rögzített verzióval (ideálisan commit SHA-val) hivatkozd.

```yaml
name: build-and-deploy
on:
  push:
    branches: [main]

permissions:
  contents: read
  packages: write
  id-token: write                      # OIDC: felhő-hitelesítés hosszú életű kulcs nélkül

env:
  IMAGE: ghcr.io/acme/shop-api

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          push: true
          tags: ${{ env.IMAGE }}:${{ github.sha }}   # megváltoztathatatlan, visszakövethető tag
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - uses: azure/setup-helm@v4
      # (itt jön a klaszter-hitelesítés, pl. felhős OIDC login + kubeconfig)
      - run: |
          helm upgrade --install api charts/api -n shop \
            --set image.repository=${{ env.IMAGE }} \
            --set image.tag=${{ github.sha }} --atomic --timeout 5m

  deploy-prod:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production            # kötelező jóváhagyás a környezet védelmi szabályaiból
    steps:
      - uses: actions/checkout@v4
      - uses: azure/setup-helm@v4
      - run: |
          helm upgrade --install api charts/api -n shop -f charts/api/values-prod.yaml \
            --set image.repository=${{ env.IMAGE }} \
            --set image.tag=${{ github.sha }} --atomic --timeout 5m
```

## Infrastruktúra kódként: Terraform
<!-- q: Hogyan kezeljem az infrastruktúrát kódként Terraformmal? -->
<!-- tags: terraform, infrastructure as code, iac, hcl, state, plan, apply, modules, aws -->

A Terraform deklaratívan írja le az infrastruktúrát (HCL nyelven): a `plan` összeveti a kívánt állapotot a *state*-ben nyilvántartott valós állapottal, és megmutatja a változásokat, az `apply` pedig végrehajtja őket a függőségi gráf sorrendjében. A state érzékeny és kritikus: csapatban távoli backendben (S3 + zárolás, Terraform Cloud) tárold, titkosítva, és soha ne commitold. Az ismétlődő mintákat modulokba szervezd, a változókat validáld, a PR-ban a `plan` kimenetét review-zd, és pontosan azt a mentett tervet alkalmazd. A konzolon végzett kézi módosítás *drift*-et okoz — mindent kódból kezelj.

```hcl
terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" {                                  # távoli, titkosított state zárolással
    bucket         = "acme-terraform-state"
    key            = "shop/prod/terraform.tfstate"
    region         = "eu-central-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}

variable "region" {
  type    = string
  default = "eu-central-1"
}

variable "env" {
  type = string
  validation {
    condition     = contains(["staging", "prod"], var.env)
    error_message = "Az env értéke csak staging vagy prod lehet."
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { project = "shop", env = var.env, managed_by = "terraform" }
  }
}

resource "aws_s3_bucket" "uploads" {
  bucket = "acme-shop-uploads-${var.env}"
}

resource "aws_s3_bucket_versioning" "uploads" {
  bucket = aws_s3_bucket.uploads.id               # implicit függőség -> helyes sorrend
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket                  = aws_s3_bucket.uploads.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

module "db" {                                     # újrahasznosítható modul
  source         = "./modules/postgres"
  name           = "shop-${var.env}"
  instance_class = var.env == "prod" ? "db.r6g.large" : "db.t4g.micro"
}

output "uploads_bucket" {
  value = aws_s3_bucket.uploads.bucket
}
```

```bash
terraform fmt -check && terraform validate
terraform plan -var env=prod -out=tfplan    # a PR-ban review-zandó változáslista
terraform apply tfplan                      # pontosan a jóváhagyott terv fut le
```

## Monitorozás: Prometheus metrikák és Grafana
<!-- q: Hogyan monitorozzam az alkalmazást Prometheusszal és Grafanával, és hogyan riasszak? -->
<!-- tags: prometheus, grafana, metrics, counter, histogram, gauge, promql, alerting, slo, red method -->

A Prometheus időközönként lekéri (scrape) az alkalmazások `/metrics` végpontját, és idősorokként tárolja a metrikákat; típusok: *Counter* (csak nő: kérések, hibák), *Gauge* (fel-le: folyamatban lévő kérések, sorhossz), *Histogram* (eloszlás: késleltetés-percentilisekhez). Szolgáltatásokra a RED-módszer (Rate, Errors, Duration), erőforrásokra a USE (Utilization, Saturation, Errors) ad jó kiindulást; a Grafana PromQL-lekérdezésekből épít dashboardot. A címkékbe soha ne tegyél nagy kardinalitású értéket (user-id, teljes URL), mert minden címkekombináció külön idősor, ami felrobbantja a memóriát. Tünetre riassz (hibaarány, késleltetés az SLO felett, tartósan — `for:`), ne minden okra.

```python
import random
import time
from prometheus_client import Counter, Gauge, Histogram, start_http_server

REQUESTS = Counter("http_requests_total", "HTTP kérések száma", ["method", "route", "status"])
LATENCY = Histogram("http_request_duration_seconds", "Kérés-feldolgozási idő", ["route"],
                    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5))
IN_FLIGHT = Gauge("http_requests_in_flight", "Folyamatban lévő kérések")

def handle(route: str) -> int:
    with IN_FLIGHT.track_inprogress(), LATENCY.labels(route).time():
        time.sleep(random.uniform(0.005, 0.2))           # "munka"
        status = 500 if random.random() < 0.02 else 200
    # címke: route-SABLON (/api/orders/{id}), nem a konkrét URL -> alacsony kardinalitás
    REQUESTS.labels("GET", route, str(status)).inc()
    return status

if __name__ == "__main__":
    start_http_server(9100)                               # /metrics a Prometheus számára
    while True:
        handle(random.choice(["/api/products", "/api/orders/{id}"]))
```

```yaml
# Prometheus szabályfájl: recording rule + riasztások
groups:
  - name: api-slo
    rules:
      - record: route:http_error_ratio:rate5m
        expr: |
          sum by (route) (rate(http_requests_total{status=~"5.."}[5m]))
          / sum by (route) (rate(http_requests_total[5m]))
      - alert: HighErrorRate
        expr: route:http_error_ratio:rate5m > 0.05
        for: 10m                                     # csak tartós probléma riaszt
        labels: { severity: page }
        annotations:
          summary: "{{ $labels.route }}: {{ $value | humanizePercentage }} 5xx arány"
      - alert: SlowP95
        expr: histogram_quantile(0.95, sum by (le, route) (rate(http_request_duration_seconds_bucket[5m]))) > 0.5
        for: 15m
        labels: { severity: ticket }
```

## Strukturált naplózás
<!-- q: Hogyan naplózzak strukturáltan (JSON) és korreláljam egy kérés naplósorait? -->
<!-- tags: logging, structured logging, json logs, correlation id, request id, loki, elk, python logging -->

A strukturált napló soronként egy JSON-objektum fix mezőkkel (időbélyeg, szint, üzenet, kontextus), így a naplógyűjtő (Loki, Elasticsearch, CloudWatch) mezők szerint kereshet és aggregálhat, regex-elés helyett. Minden kéréshez rendelj *request/correlation ID*-t, amit a naplósorok és a downstream hívások (HTTP header) is továbbvisznek — így egy kérés útja több szolgáltatáson át is követhető; a teljes elosztott nyomkövetést az OpenTelemetry adja. Konténerben a napló a stdout-ra menjen, a gyűjtést a platform végzi. Soha ne naplózz jelszót, tokent, teljes kártyaszámot vagy személyes adatot, és a szinteket következetesen használd (az `error` legyen ritka és cselekvésre ösztönző).

```python
import contextvars
import json
import logging
import sys
import time
import uuid

request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

class JsonFormatter(logging.Formatter):
    """Soronként egy JSON-objektum: gépileg kereshető (Loki, ELK)."""
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)) + f".{int(record.msecs):03d}Z",
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id.get(),          # egy kérés összes sora összeköthető
        }
        entry.update(getattr(record, "fields", {}))   # extra={"fields": {...}}
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)

def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)       # stdout: a platform gyűjti
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)

log = logging.getLogger("shop.checkout")

def handle_checkout(order_id: str, amount: int) -> None:
    request_id.set(uuid.uuid4().hex[:12])             # valóságban a bejövő headerből, ha van
    log.info("checkout indult", extra={"fields": {"order_id": order_id, "amount": amount}})
    try:
        if amount <= 0:
            raise ValueError("érvénytelen összeg")
    except ValueError:
        log.exception("checkout sikertelen", extra={"fields": {"order_id": order_id}})

setup_logging()
handle_checkout("o-1001", 4990)
handle_checkout("o-1002", 0)
```

## Kiadási stratégiák: blue-green és canary
<!-- q: Mi a blue-green és a canary deployment, és hogyan valósítsam meg Kubernetesben? -->
<!-- tags: blue green deployment, canary release, progressive delivery, argo rollouts, rollback, traffic shifting -->

A *blue-green* kiadásnál két teljes környezet fut: az új verzió (green) mellett a régi (blue) szolgálja ki a forgalmat, a váltás egyetlen lépés (Service-selector vagy terheléselosztó átállítása), és a visszaállás ugyanilyen azonnali — cserébe dupla kapacitás kell, és az adatbázis-sémának mindkét verzióval kompatibilisnek kell lennie (expand–contract migráció). A *canary* fokozatosan tereli a forgalmat az új verzióra (5% → 25% → 50% → 100%), közben metrikák alapján automatikusan elemez, és hiba esetén visszagörget; így egy rossz kiadás csak a felhasználók kis részét érinti. Kubernetesben az Argo Rollouts vagy a Flagger végzi a forgalom-eltolást és az elemzést.

```yaml
# CANARY Argo Rollouts-szal: lépcsőzetes forgalom + Prometheus-alapú automatikus elemzés
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: api
spec:
  replicas: 10
  selector:
    matchLabels: { app: api }
  template:
    metadata:
      labels: { app: api }
    spec:
      containers:
        - name: api
          image: registry.example.com/shop/api:1.9.0
  strategy:
    canary:
      steps:
        - setWeight: 5                    # a forgalom 5%-a az új verzióra
        - pause: { duration: 10m }
        - analysis:                       # rossz metrika -> automatikus visszagörgetés
            templates: [{ templateName: error-rate }]
        - setWeight: 25
        - pause: { duration: 10m }
        - setWeight: 50
        - pause: { duration: 10m }        # utána 100%
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: error-rate
spec:
  metrics:
    - name: error-rate
      interval: 1m
      failureLimit: 2
      successCondition: result[0] < 0.01
      provider:
        prometheus:
          address: http://prometheus.monitoring:9090
          query: |
            sum(rate(http_requests_total{app="api",status=~"5.."}[2m]))
            / sum(rate(http_requests_total{app="api"}[2m]))
```

```bash
# BLUE-GREEN: két Deployment (slot=blue / slot=green), a Service selectora vált
kubectl apply -f deploy-green.yaml
kubectl rollout status deploy/api-green
./scripts/smoke-test.sh https://green.internal.example.com || exit 1   # teszt éles forgalom előtt
kubectl patch service api -p '{"spec":{"selector":{"app":"api","slot":"green"}}}'
# Hiba esetén azonnali visszaállás:
kubectl patch service api -p '{"spec":{"selector":{"app":"api","slot":"blue"}}}'
```

## A 12-faktoros alkalmazás elvei
<!-- q: Mik a 12-faktoros alkalmazás elvei és hogyan alkalmazzam őket? -->
<!-- tags: twelve factor app, 12 factor, configuration, environment variables, stateless, disposability, backing services -->

A 12-faktoros módszertan a felhőben jól üzemeltethető alkalmazások irányelvei: egy kódbázis sok deployhoz, explicit függőségek, a konfiguráció környezeti változókban (nem a kódban), a háttérszolgáltatások (DB, cache, üzenetsor) URL-lel csatolt, cserélhető erőforrások, szigorúan elválasztott build–release–run fázisok, állapotmentes processzek (az állapot a DB-ben/cache-ben él), port-kötés, skálázás processzekkel, gyors indulás és kecses leállítás, a fejlesztői és éles környezet hasonlósága, naplók stdout-ra eseményfolyamként, és az adminfeladatok egyszeri processzként. A gyakorlatban a legfontosabb: induláskor validált env-konfiguráció (fail fast), SIGTERM-kezelés és állapotmentesség — ezek nélkül a Kubernetes rolling update és az autoscaling sem működik megbízhatóan.

```python
"""12-faktoros konfiguráció: minden környezetfüggő érték env-ből, induláskor validálva."""
import os
import signal
import sys
from dataclasses import dataclass

class ConfigError(Exception):
    pass

def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise ConfigError(f"hiányzó környezeti változó: {name}")
    return value

@dataclass(frozen=True)
class Settings:
    database_url: str          # III. Config: env-ben, nem a repóban
    redis_url: str             # IV. Backing services: URL-lel csatolt, cserélhető erőforrás
    port: int                  # VII. Port binding: az app maga köt portra
    log_level: str
    workers: int               # VIII. Concurrency: skálázás processzekkel

    @classmethod
    def from_env(cls) -> "Settings":
        try:
            return cls(
                database_url=_env("DATABASE_URL"),
                redis_url=_env("REDIS_URL", "redis://localhost:6379/0"),
                port=int(_env("PORT", "8000")),
                log_level=_env("LOG_LEVEL", "INFO").upper(),
                workers=int(_env("WEB_CONCURRENCY", "2")),
            )
        except ValueError as e:
            raise ConfigError(f"hibás szám a konfigurációban: {e}") from e

def install_graceful_shutdown(on_stop) -> None:
    # IX. Disposability: SIGTERM-re a folyamatban lévő munka befejezése, majd kilépés
    def handler(signum, frame):
        on_stop()
        sys.exit(0)
    signal.signal(signal.SIGTERM, handler)

if __name__ == "__main__":
    try:
        settings = Settings.from_env()                  # fail fast: hibás konfiggal el sem indul
    except ConfigError as e:
        print(f"konfigurációs hiba: {e}", file=sys.stderr)
        sys.exit(2)
    install_graceful_shutdown(lambda: print("leállás: kapcsolatok lezárása"))
    print(f"indulás a {settings.port} porton, {settings.workers} workerrel")   # XI. Logs: stdout
```
