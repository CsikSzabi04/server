# SQL
<!-- tech: sql -->
<!-- aliases: postgresql, mysql, sqlite, t-sql, pl/pgsql -->

Az SQL deklaratív, halmazalapú lekérdezőnyelv relációs adatbázisokhoz: azt írod le, MIT akarsz
megkapni, a lekérdezéstervező (query planner) dönti el, HOGYAN (melyik index, milyen join-algoritmus).
A fő dialektusok: PostgreSQL (gazdag típusrendszer, JSONB, PL/pgSQL, MVCC), MySQL/MariaDB (InnoDB,
elterjedt webes stack), SQLite (beágyazott, egyfájlos, egy író egyszerre) és T-SQL (SQL Server).
A szabványos mag (SELECT, JOIN, GROUP BY, ablakfüggvények, CTE) mindenhol hasonló, de az upsert, a
dátumkezelés, az automatikus azonosító és a zárolás dialektusonként eltér. Erős konzisztenciát,
tranzakciókat és ad-hoc lekérdezést igénylő adatokra ideális; óriási, séma nélküli eseményfolyamokra
vagy gráfszerű mély bejárásokra más eszköz (oszloptár, gráfadatbázis) lehet jobb.

## JOIN típusok és az ON vs WHERE buktató
<!-- q: Mi a különbség az INNER, LEFT és self JOIN között, és miért tűnnek el sorok a LEFT JOIN-ból? -->
<!-- tags: join, inner join, left join, self join, outer join -->

Az INNER JOIN csak a mindkét oldalon illeszkedő sorokat adja vissza, a LEFT JOIN a bal tábla minden
sorát megtartja, és a hiányzó jobb oldalt NULL-lal tölti ki; a FULL JOIN mindkét oldalt megtartja
(PostgreSQL, SQLite 3.39+). A leggyakoribb hiba, hogy a jobb oldali táblára vonatkozó szűrés a
WHERE-be kerül: a NULL-os sorokat ez kiszűri, így a LEFT JOIN észrevétlenül INNER JOIN-ná válik.
A self join ugyanazt a táblát két aliasszal kapcsolja össze, például hierarchiához vagy ajánlási lánchoz.

```sql
-- Dialektus: SQLite / PostgreSQL / MySQL
-- Mintaséma: ügyfelek (önhivatkozó ajánlóval) és rendelések
CREATE TABLE customers (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,
  city        TEXT,
  referrer_id INTEGER REFERENCES customers(id)   -- ki ajánlotta (self join-hoz)
);
CREATE TABLE orders (
  id          INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES customers(id),
  status      TEXT NOT NULL,                     -- 'paid' | 'cancelled' | 'new'
  total       INTEGER NOT NULL,
  created_at  TEXT NOT NULL
);
INSERT INTO customers VALUES (1,'Anna','Budapest',NULL),(2,'Bence','Szeged',1),(3,'Csilla','Pécs',1);
INSERT INTO orders VALUES (10,1,'paid',12000,'2026-01-05'),(11,1,'cancelled',5000,'2026-01-07'),
                          (12,2,'paid',8000,'2026-02-01');

-- INNER JOIN: csak a rendeléssel rendelkező ügyfelek
SELECT c.name, o.id AS order_id, o.total
FROM customers c
JOIN orders o ON o.customer_id = c.id;

-- LEFT JOIN, a szűrés az ON-ban: minden ügyfél megmarad (Csilla 0-val)
SELECT c.name, COALESCE(SUM(o.total), 0) AS paid_total
FROM customers c
LEFT JOIN orders o
       ON o.customer_id = c.id
      AND o.status = 'paid'          -- ITT kell szűrni, nem a WHERE-ben!
GROUP BY c.id, c.name
ORDER BY paid_total DESC;

-- BUKTATÓ: a WHERE kiszűri a NULL-os (rendelés nélküli) sorokat -> Csilla eltűnik
SELECT c.name, o.total
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
WHERE o.status = 'paid';

-- SELF JOIN: ki kit ajánlott
SELECT c.name AS customer, r.name AS referred_by
FROM customers c
LEFT JOIN customers r ON r.id = c.referrer_id;
```

## Semi-join, anti-join és LATERAL join
<!-- q: Hogyan kérdezzem le, ami létezik vagy hiányzik egy másik táblában, és mire jó a LATERAL? -->
<!-- tags: semi join, anti join, exists, not exists, not in, lateral, cross apply, top-n -->

A semi-join (EXISTS) azt adja vissza, aminek VAN párja, duplikálás nélkül és az első találatnál
megállva; az anti-join (NOT EXISTS vagy LEFT JOIN ... IS NULL) azt, aminek NINCS. A NOT IN veszélyes:
ha a részlekérdezés akár egy NULL-t is visszaad, a feltétel UNKNOWN lesz, és az eredmény üres. A
LATERAL részlekérdezés soronként fut, és hivatkozhat a bal oldali tábla oszlopaira, ezért ideális
csoportonkénti top-N lekérdezéshez (T-SQL-ben CROSS APPLY / OUTER APPLY).

```sql
-- Dialektus: SQLite / PostgreSQL / MySQL
CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL);
CREATE TABLE order_items (order_id INTEGER NOT NULL, product_id INTEGER, qty INTEGER NOT NULL);
INSERT INTO products VALUES (1,'Billentyűzet','periféria'),(2,'Egér','periféria'),(3,'Monitor','kijelző');
INSERT INTO order_items VALUES (100,1,2),(100,2,1),(101,1,1),(102,NULL,5);  -- NULL: törölt termék

-- SEMI-JOIN: termékek, amelyekből valaha rendeltek (nincs duplikátum, nem kell DISTINCT)
SELECT p.name FROM products p
WHERE EXISTS (SELECT 1 FROM order_items oi WHERE oi.product_id = p.id);

-- ANTI-JOIN: soha nem rendelt termékek -> 'Monitor'
SELECT p.name FROM products p
WHERE NOT EXISTS (SELECT 1 FROM order_items oi WHERE oi.product_id = p.id);

-- BUKTATÓ: NOT IN + NULL -> "3 NOT IN (1, 2, NULL)" = UNKNOWN -> 0 sor!
SELECT p.name FROM products p
WHERE p.id NOT IN (SELECT oi.product_id FROM order_items oi);

-- Anti-join LEFT JOIN ... IS NULL formában (régi MySQL-ben gyakran gyorsabb)
SELECT p.name
FROM products p
LEFT JOIN order_items oi ON oi.product_id = p.id
WHERE oi.order_id IS NULL;
```

```sql
-- Dialektus: PostgreSQL (MySQL 8.0.14+ is; T-SQL: CROSS APPLY / OUTER APPLY)
-- Kategóriánként a 2 legutóbbi rendeléstétel: a részlekérdezés soronként fut
SELECT c.category, last2.order_id, last2.qty
FROM (SELECT DISTINCT category FROM products) AS c
CROSS JOIN LATERAL (
    SELECT oi.order_id, oi.qty
    FROM order_items oi
    JOIN products p ON p.id = oi.product_id
    WHERE p.category = c.category      -- korrelált hivatkozás a bal oldalra
    ORDER BY oi.order_id DESC
    LIMIT 2                            -- csoportonkénti top-N, indexszel nagyon gyors
) AS last2;

-- LEFT JOIN LATERAL ... ON true: megtartja a bal sort üres részlekérdezésnél is
SELECT c.category, last1.order_id
FROM (SELECT DISTINCT category FROM products) AS c
LEFT JOIN LATERAL (
    SELECT oi.order_id
    FROM order_items oi JOIN products p ON p.id = oi.product_id
    WHERE p.category = c.category
    ORDER BY oi.order_id DESC
    LIMIT 1
) AS last1 ON true;
```

## Rangsoroló ablakfüggvények: ROW_NUMBER, RANK, DENSE_RANK
<!-- q: Hogyan rangsoroljak csoportonként, és hogyan kérjem le csoportonként a legjobb sort? -->
<!-- tags: window function, row_number, rank, dense_rank, ntile, partition by, top-n per group, deduplication -->

Az ablakfüggvény (OVER) a GROUP BY-jal ellentétben nem vonja össze a sorokat: minden sor megmarad, és
mellé kerül egy, a "partíció" soraiból számolt érték. A ROW_NUMBER holtversenyben is egyedi sorszámot
ad, a RANK a holtverseny után ugrik (1,1,3), a DENSE_RANK nem (1,1,2). Ablakfüggvény nem állhat a
WHERE-ben (az előbb értékelődik ki), ezért szűréshez részlekérdezés vagy CTE kell. Determinisztikus
eredményhez mindig adj holtverseny-törő oszlopot az ORDER BY-hoz.

```sql
-- Dialektus: SQLite 3.28+ / PostgreSQL / MySQL 8+
CREATE TABLE sales (
  id INTEGER PRIMARY KEY, region TEXT NOT NULL, seller TEXT NOT NULL, amount INTEGER NOT NULL
);
INSERT INTO sales (region, seller, amount) VALUES
 ('Észak','Ádám',500),('Észak','Béla',700),('Észak','Cili',700),
 ('Dél','Dóra',300),('Dél','Ede',900),('Dél','Feri',100);

SELECT region, seller, amount,
       ROW_NUMBER() OVER w AS rn,      -- 1,2,3: holtversenyben is egyedi
       RANK()       OVER w AS rnk,     -- 1,1,3
       DENSE_RANK() OVER w AS drnk,    -- 1,1,2
       NTILE(2)     OVER w AS half,    -- felső / alsó fél
       ROUND(100.0 * amount / SUM(amount) OVER (PARTITION BY region), 1) AS pct_of_region
FROM sales
WINDOW w AS (PARTITION BY region ORDER BY amount DESC)   -- elnevezett ablak
ORDER BY region, rn;

-- Csoportonkénti TOP-1: régiónként a legjobb eladó (holtversenyt a név dönti el)
SELECT region, seller, amount
FROM (
  SELECT s.*, ROW_NUMBER() OVER (PARTITION BY region ORDER BY amount DESC, seller) AS rn
  FROM sales s
) ranked
WHERE rn = 1;

-- Duplikátumok törlése: (region, seller) párosonként csak a legkisebb id marad
DELETE FROM sales
WHERE id IN (
  SELECT id FROM (
    SELECT id, ROW_NUMBER() OVER (PARTITION BY region, seller ORDER BY id) AS rn
    FROM sales
  ) t
  WHERE rn > 1
);
```

## LAG/LEAD, futó összeg és ablakkeretek (frame)
<!-- q: Hogyan számoljak futó összeget, mozgóátlagot és előző sorhoz képesti változást SQL-ben? -->
<!-- tags: lag, lead, running total, moving average, window frame, rows between, range, first_value, last_value -->

A LAG és LEAD az előző/következő sor értékét adja a partíción belül, így önillesztés nélkül számolható
napi változás. Az aggregátum ablakfüggvényként (SUM ... OVER (ORDER BY ...)) futó összeget ad, a frame
(ROWS BETWEEN ...) pedig megmondja, pontosan mely sorok számítanak bele. Ha van ORDER BY, az
alapértelmezett keret RANGE UNBOUNDED PRECEDING, ami holtversenyben az összes egyenrangú sort egyszerre
beveszi; ezért futó összeghez ROWS-t írj ki explicit. A LAST_VALUE alapból csak az aktuális sorig lát,
ezért teljes partícióhoz UNBOUNDED FOLLOWING kell.

```sql
-- Dialektus: SQLite 3.28+ / PostgreSQL / MySQL 8+
CREATE TABLE daily_revenue (day TEXT PRIMARY KEY, revenue INTEGER NOT NULL);
INSERT INTO daily_revenue VALUES
 ('2026-03-01',100),('2026-03-02',120),('2026-03-03',90),
 ('2026-03-04',150),('2026-03-05',150),('2026-03-06',80);

SELECT day, revenue,
  LAG(revenue, 1, 0) OVER (ORDER BY day)       AS prev_rev,   -- 3. param: alapérték
  LEAD(revenue)      OVER (ORDER BY day)       AS next_rev,
  revenue - LAG(revenue) OVER (ORDER BY day)   AS delta,
  -- futó összeg explicit ROWS kerettel
  SUM(revenue) OVER (ORDER BY day ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total,
  -- 3 napos mozgóátlag: az aktuális + 2 előző sor
  ROUND(AVG(revenue) OVER (ORDER BY day ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 1) AS ma3,
  MAX(revenue)         OVER (ORDER BY day)     AS max_so_far,
  FIRST_VALUE(revenue) OVER (ORDER BY day)     AS first_rev
FROM daily_revenue
ORDER BY day;

-- ROWS vs RANGE: a 150-es holtversenynél a RANGE mindkét sorban ugyanazt adja
SELECT revenue,
  SUM(revenue) OVER (ORDER BY revenue)                          AS range_sum,
  SUM(revenue) OVER (ORDER BY revenue ROWS UNBOUNDED PRECEDING) AS rows_sum
FROM daily_revenue;

-- LAST_VALUE buktató: teljes partícióhoz explicit keret kell
SELECT day,
  LAST_VALUE(revenue) OVER (ORDER BY day
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS last_rev
FROM daily_revenue;
```

## CTE és rekurzív CTE fa bejárására
<!-- q: Hogyan járjak be egy fa szerkezetű (szülő-gyerek) táblát rekurzív CTE-vel? -->
<!-- tags: cte, with, recursive cte, hierarchy, tree, adjacency list, breadcrumb -->

A CTE (WITH) elnevezett részlekérdezés: a többlépéses logikát olvasható blokkokra bontja. A rekurzív
CTE egy horgony (anchor) lekérdezésből és egy rekurzív tagból áll, amelyet UNION ALL köt össze; a
rekurzív tag mindig az előző kör eredményéhez illeszt, amíg új sor keletkezik. Szülő-gyerek
(adjacency list) táblán így lekérhető a teljes részfa mélységgel és útvonallal, vagy egy elem összes
őse. Hibás, ciklikus adat végtelen ciklust okoz, ezért tegyél bele mélységkorlátot; MySQL-ben az
útvonal-oszlop szélességét a horgony határozza meg, ott CAST(name AS CHAR(1000)) kell.

```sql
-- Dialektus: SQLite / PostgreSQL / MySQL 8+ (MySQL-ben || helyett CONCAT)
CREATE TABLE categories (
  id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES categories(id), name TEXT NOT NULL
);
INSERT INTO categories VALUES
 (1,NULL,'Elektronika'),(2,1,'Számítógép'),(3,2,'Laptop'),
 (4,2,'Asztali gép'),(5,1,'Telefon'),(6,3,'Gamer laptop');

-- Sima CTE: közvetlen gyerekek száma kategóriánként
WITH child_counts AS (
  SELECT parent_id, COUNT(*) AS n
  FROM categories WHERE parent_id IS NOT NULL
  GROUP BY parent_id
)
SELECT c.name, COALESCE(cc.n, 0) AS direct_children
FROM categories c
LEFT JOIN child_counts cc ON cc.parent_id = c.id;

-- Rekurzív CTE: teljes fa a gyökértől, mélységgel és útvonallal
WITH RECURSIVE tree(id, name, depth, path) AS (
  SELECT id, name, 0, name                   -- 1) horgony: gyökérelemek
  FROM categories WHERE parent_id IS NULL
  UNION ALL
  SELECT c.id, c.name, t.depth + 1, t.path || ' > ' || c.name   -- 2) rekurzív tag
  FROM categories c
  JOIN tree t ON c.parent_id = t.id
  WHERE t.depth < 20                         -- vészfék ciklikus adatra
)
SELECT substr('                    ', 1, depth * 2) || name AS indented, path
FROM tree
ORDER BY path;

-- Visszafelé: a 6-os kategória összes őse (breadcrumb)
WITH RECURSIVE ancestors(id, parent_id, name, lvl) AS (
  SELECT id, parent_id, name, 0 FROM categories WHERE id = 6
  UNION ALL
  SELECT c.id, c.parent_id, c.name, a.lvl + 1
  FROM categories c
  JOIN ancestors a ON c.id = a.parent_id
)
SELECT name FROM ancestors ORDER BY lvl DESC;
```

## Rekurzív CTE gráfbejárásra ciklusvédelemmel
<!-- q: Hogyan keressek utakat egy gráfban SQL-ben úgy, hogy a ciklusok ne okozzanak végtelen ciklust? -->
<!-- tags: recursive cte, graph, path finding, cycle detection, cycle clause, shortest path -->

Gráfnál (élek táblája) ugyanaz a rekurzív minta működik, de a ciklusok miatt minden útvonalnak
tárolnia kell a már érintett csúcsokat, és a rekurzív tag nem léphet vissza ezekre. PostgreSQL-ben
erre tömb (route || csúcs) és 14-es verziótól a beépített CYCLE záradék való, SQLite-ban szöveges
útvonallal oldható meg. Az összes út felsorolása exponenciálisan nőhet, ezért mindig legyen
mélységkorlát; sűrű gráfon legrövidebb úthoz inkább alkalmazásoldali Dijkstra vagy pgRouting kell.

```sql
-- Dialektus: SQLite (PostgreSQL-ben instr helyett strpos, vagy lásd a tömbös változatot)
CREATE TABLE edges (src TEXT NOT NULL, dst TEXT NOT NULL, km INTEGER NOT NULL,
                    PRIMARY KEY (src, dst));
INSERT INTO edges VALUES
 ('Budapest','Kecskemét',86),('Kecskemét','Szeged',88),('Budapest','Szolnok',100),
 ('Szolnok','Szeged',120),('Kecskemét','Szolnok',62),
 ('Szeged','Budapest',170);                         -- ez az él ciklust okoz

-- Összes út Budapestről Szegedre; a 'visited' ',Város,' formában tárolja az érintett csúcsokat
WITH RECURSIVE paths(node, visited, total_km, hops) AS (
  SELECT 'Budapest', ',Budapest,', 0, 0
  UNION ALL
  SELECT e.dst, p.visited || e.dst || ',', p.total_km + e.km, p.hops + 1
  FROM paths p
  JOIN edges e ON e.src = p.node
  WHERE instr(p.visited, ',' || e.dst || ',') = 0   -- ciklusvédelem
    AND p.node <> 'Szeged'                          -- a célban nem megyünk tovább
    AND p.hops < 10                                 -- mélységkorlát
)
SELECT visited AS route, total_km, hops
FROM paths
WHERE node = 'Szeged'
ORDER BY total_km
LIMIT 3;
```

```sql
-- Dialektus: PostgreSQL 14+ (tömbös útvonal + beépített CYCLE detektálás)
WITH RECURSIVE paths(node, route, total_km) AS (
  SELECT 'Budapest'::text, ARRAY['Budapest'], 0
  UNION ALL
  SELECT e.dst, p.route || e.dst, p.total_km + e.km
  FROM paths p
  JOIN edges e ON e.src = p.node
  WHERE p.node <> 'Szeged'
) CYCLE node SET is_cycle USING cycle_path      -- ismétlődő csúcsnál megáll és jelöl
SELECT route, total_km
FROM paths
WHERE node = 'Szeged' AND NOT is_cycle
ORDER BY total_km;
```

## Részösszegek: GROUPING SETS, ROLLUP, CUBE
<!-- q: Hogyan kapjak részösszegeket és végösszeget egyetlen SQL lekérdezésben? -->
<!-- tags: grouping sets, rollup, cube, grouping, subtotal, olap, report -->

A GROUPING SETS több GROUP BY eredményét adja vissza egyetlen táblaolvasással; a ROLLUP (a, b) a
hierarchikus részösszegeket ((a,b), (a), ()) jelenti, a CUBE pedig minden kombinációt (2^n halmaz,
sok oszlopnál robban). A részösszeg-sorokban az összevont oszlop NULL, ami összetéveszthető a valódi
NULL-lal, ezt a GROUPING() függvény különbözteti meg. PostgreSQL és T-SQL mindhármat ismeri, MySQL
csak a WITH ROLLUP-ot, SQLite egyiket sem, ott UNION ALL-lal emulálható.

```sql
-- Dialektus: SQLite / MySQL — ROLLUP emulálása UNION ALL-lal
-- (MySQL-ben natívan: GROUP BY year, region WITH ROLLUP)
CREATE TABLE sales_fact (year INT, region TEXT, product TEXT, amount NUMERIC(12,2));
INSERT INTO sales_fact VALUES
 (2025,'Észak','Laptop',1200),(2025,'Dél','Laptop',800),(2025,'Dél','Egér',50),
 (2026,'Észak','Egér',70),(2026,'Észak','Laptop',1500),(2026,'Dél','Laptop',900);

SELECT * FROM (
  SELECT year, region, SUM(amount) AS total FROM sales_fact GROUP BY year, region
  UNION ALL
  SELECT year, NULL, SUM(amount) FROM sales_fact GROUP BY year      -- évenkénti részösszeg
  UNION ALL
  SELECT NULL, NULL, SUM(amount) FROM sales_fact                    -- végösszeg
) t
ORDER BY year IS NULL, year, region IS NULL, region;
```

```sql
-- Dialektus: PostgreSQL (T-SQL is)
SELECT year, region, SUM(amount) AS total,
       GROUPING(year, region) AS lvl          -- bitmaszk: 0 = részletsor, 1 = év, 3 = végösszeg
FROM sales_fact
GROUP BY ROLLUP (year, region)
ORDER BY year NULLS LAST, region NULLS LAST;

-- Tetszőleges kombinációk egy menetben
SELECT year, region, product, SUM(amount)
FROM sales_fact
GROUP BY GROUPING SETS ((year, region), (product), ());

-- Minden kombináció (4 halmaz két oszlopra)
SELECT region, product, SUM(amount)
FROM sales_fact
GROUP BY CUBE (region, product);

-- Részösszeg-sor címkézése a GROUPING() alapján
SELECT CASE WHEN GROUPING(region) = 1 THEN '(összes)' ELSE region END AS region,
       SUM(amount) AS total
FROM sales_fact
GROUP BY ROLLUP (region);
```

## Indextípusok és az összetett index oszlopsorrendje
<!-- q: Milyen indexet hozzak létre, és számít-e az oszlopok sorrendje egy összetett indexben? -->
<!-- tags: index, b-tree, composite index, partial index, covering index, gin, gist, hash index, expression index -->

A B-tree az alapértelmezett index: egyenlőségre, tartományra, rendezésre és prefix LIKE-ra jó. Az
összetett indexnél a sorrend döntő: csak a bal oldali prefix használható, ezért elöl legyenek az
egyenlőséggel szűrt, hátul a tartománnyal szűrt vagy rendezett oszlopok. A részleges index (WHERE)
csak a releváns sorokat tartalmazza, a covering index (PostgreSQL INCLUDE) heap-olvasás nélküli
Index Only Scant tesz lehetővé, a GIN jsonb/tömb/teljes szöveg, a GiST tartomány- és geometriai
típusokhoz való. Minden index lassítja az írást és helyet foglal, ezért csak mért lekérdezésekhez adj.

```sql
-- Dialektus: SQLite / PostgreSQL (részleges index MySQL-ben nincs)
CREATE TABLE events (
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, kind TEXT NOT NULL,
  created_at TEXT NOT NULL, processed INTEGER NOT NULL DEFAULT 0, payload TEXT
);
-- ÖSSZETETT index: egyenlőség elöl, tartomány/rendezés hátul.
-- Kiszolgálja:  WHERE tenant_id = ?
--               WHERE tenant_id = ? AND created_at >= ?
--               WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 20
-- NEM szolgálja ki jól: WHERE created_at >= ?   (hiányzik a bal oldali prefix)
CREATE INDEX idx_events_tenant_time ON events (tenant_id, created_at);

-- RÉSZLEGES index: csak a feldolgozatlan sorok -> kicsi, gyors (job queue minta)
CREATE INDEX idx_events_pending ON events (created_at) WHERE processed = 0;

-- KIFEJEZÉS-index: kis-nagybetű független kereséshez
CREATE INDEX idx_events_kind_lower ON events (lower(kind));

-- Ellenőrzés: használja-e a terv az indexeket
EXPLAIN QUERY PLAN
SELECT id FROM events WHERE tenant_id = 7 AND created_at >= '2026-01-01'
ORDER BY created_at DESC LIMIT 20;
EXPLAIN QUERY PLAN
SELECT id FROM events WHERE processed = 0 ORDER BY created_at LIMIT 100;
```

```sql
-- Dialektus: PostgreSQL
-- COVERING: az INCLUDE oszlopok csak a levelekben vannak -> Index Only Scan
CREATE INDEX idx_orders_cust_cover ON orders (customer_id, created_at DESC) INCLUDE (total, status);

-- HASH: csak egyenlőség (=), rendezni / tartományt nem tud
CREATE INDEX idx_sessions_token ON sessions USING hash (token);

-- GIN: "sok érték egy mezőben": jsonb, tömb, tsvector, trigram
CREATE INDEX idx_docs_tags ON docs USING gin (tags);                    -- tags text[]
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_users_name_trgm ON users USING gin (name gin_trgm_ops); -- ILIKE '%szó%'

-- GiST: tartomány-átfedés (&&), geometria, legközelebbi szomszéd (<->)
CREATE INDEX idx_bookings_during ON bookings USING gist (during);       -- during tstzrange

-- Éles táblán írási zár nélkül (tranzakción kívül kell futtatni)
CREATE INDEX CONCURRENTLY idx_events_kind ON events (kind);
```

## EXPLAIN ANALYZE olvasása
<!-- q: Hogyan olvassam az EXPLAIN ANALYZE kimenetét, és miből látom, miért lassú egy lekérdezés? -->
<!-- tags: explain, explain analyze, query plan, seq scan, index scan, buffers, statistics, performance -->

Az EXPLAIN a tervezett végrehajtási fát mutatja becsült költséggel és sorszámmal, az ANALYZE ténylegesen
le is futtatja a lekérdezést, és mellé teszi a valós időket és sorszámokat. A fát belülről kifelé,
alulról felfelé olvasd: a legmélyebb csomópontok futnak először. A legfontosabb jel a becsült és a
tényleges sorszám nagy eltérése (elavult statisztika, korrelált oszlopok), a sok "Rows Removed by
Filter" (hiányzó index), és a loops érték, amellyel a csomópont ideje szorzódik. Mivel az ANALYZE
végrehajt, módosító utasítást csak visszagörgetett tranzakcióban vizsgálj.

```sql
-- Dialektus: PostgreSQL
EXPLAIN (ANALYZE, BUFFERS)
SELECT c.name, SUM(o.total)
FROM customers c
JOIN orders o ON o.customer_id = c.id
WHERE o.created_at >= now() - interval '30 days'
GROUP BY c.name;

-- Példa kimenet (rövidítve):
-- HashAggregate (cost=1520..1530 rows=1000) (actual time=18.2..18.9 rows=850 loops=1)
--   -> Hash Join (cost=35..1495 rows=5000) (actual time=0.6..15.1 rows=48210 loops=1)
--        Hash Cond: (o.customer_id = c.id)
--        -> Seq Scan on orders o (cost=0..1380 rows=5000) (actual rows=48210 loops=1)
--             Filter: (created_at >= (now() - '30 days'::interval))
--             Rows Removed by Filter: 51790
--             Buffers: shared hit=640 read=95
--        -> Hash (actual rows=1000 loops=1)
--             -> Seq Scan on customers c ...
-- Execution Time: 19.4 ms
--
-- Olvasat:
-- 1) rows=5000 becslés vs 48210 valós: ~10x eltérés -> ANALYZE orders;
--    korrelált oszlopokra: CREATE STATISTICS ... (dependencies) ON a, b FROM t;
-- 2) Seq Scan + sok "Rows Removed by Filter" -> index kell a created_at-re.
-- 3) loops=N: a Nested Loop belső ágának ideje N-szer számít.
-- 4) Buffers read (lemez) vs hit (cache): sok read = hideg cache vagy túl sok olvasás.
-- 5) "Sort Method: external merge Disk" -> kevés a work_mem ehhez a rendezéshez.

-- Módosító utasítás biztonságos vizsgálata
BEGIN;
EXPLAIN ANALYZE DELETE FROM orders WHERE status = 'cancelled';
ROLLBACK;
```

## Tranzakciók, izolációs szintek és anomáliák
<!-- q: Melyik tranzakciós izolációs szintet válasszam, és milyen anomáliák fordulhatnak elő? -->
<!-- tags: transaction, acid, isolation level, read committed, repeatable read, serializable, write skew, savepoint -->

A tranzakció az utasításokat atomi egységgé fogja: vagy mind véglegesül (COMMIT), vagy egyik sem
(ROLLBACK). Az izolációs szint határozza meg, mit látsz a párhuzamos tranzakciók munkájából: READ
COMMITTED-nél minden utasítás friss pillanatképet lát, REPEATABLE READ-nél az egész tranzakció egyet,
SERIALIZABLE-nél az eredmény egyenértékű valamilyen soros végrehajtással. A write skew (két tranzakció
ugyanazt az invariánst olvassa, majd különböző sorokat ír) csak SERIALIZABLE alatt bukik el. Magasabb
szinten az adatbázis 40001-es hibával megszakíthat, ezért az alkalmazásnak újrapróbálkozó ciklus kell.

```sql
-- Dialektus: PostgreSQL
-- Átutalás: a két UPDATE együtt véglegesül vagy együtt vész el
BEGIN ISOLATION LEVEL READ COMMITTED;
UPDATE accounts SET balance = balance - 5000 WHERE id = 1 AND balance >= 5000;
-- az alkalmazás ellenőrzi az érintett sorok számát; ha 0 -> ROLLBACK
UPDATE accounts SET balance = balance + 5000 WHERE id = 2;
COMMIT;

-- Anomáliák PostgreSQL-ben:
--                    dirty read | nonrepeatable read | phantom | serialization anomaly
-- READ COMMITTED         -      |       lehet        |  lehet  |  lehet
-- REPEATABLE READ        -      |         -          |    -    |  lehet (write skew)
-- SERIALIZABLE           -      |         -          |    -    |    -
-- (PG-ben a READ UNCOMMITTED = READ COMMITTED; MySQL InnoDB alapja REPEATABLE READ.)

-- WRITE SKEW: "legalább egy orvos legyen ügyeletben". Két párhuzamos tranzakció
-- mindkettő 2 ügyeletest lát, és mindkettő kivesz egyet -> 0 marad.
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT count(*) FROM doctors WHERE on_call AND shift_id = 42;   -- 2
UPDATE doctors SET on_call = false WHERE id = 7 AND shift_id = 42;
COMMIT;   -- a később véglegesülő ág: ERROR: could not serialize access (SQLSTATE 40001)

-- SAVEPOINT: részleges visszagörgetés egy tranzakción belül
BEGIN;
INSERT INTO import_log (msg) VALUES ('import indul');
SAVEPOINT before_batch;
INSERT INTO items (id, name) VALUES (1, 'lehet, hogy duplikált');
ROLLBACK TO SAVEPOINT before_batch;   -- csak a köteg vész el, a log sor megmarad
COMMIT;
```

## MVCC, sorzárolás és deadlock
<!-- q: Hogyan működik az MVCC, hogyan zároljak sorokat, és hogyan kerüljem el a deadlockot? -->
<!-- tags: mvcc, vacuum, bloat, select for update, skip locked, deadlock, lock ordering, job queue -->

Az MVCC (multi-version concurrency control) miatt az UPDATE nem felülír, hanem új sorverziót hoz létre,
így az olvasók nem blokkolják az írókat és fordítva; a halott verziókat PostgreSQL-ben a VACUUM
takarítja, amit egy órákig nyitva hagyott tranzakció megakaszt (bloat). Írás-írás ütközésnél sorzár
kell: a SELECT ... FOR UPDATE megakadályozza az elveszett frissítést, a SKIP LOCKED pedig párhuzamos
feladatsor-feldolgozást tesz lehetővé várakozás nélkül. Deadlock akkor jön létre, ha két tranzakció
fordított sorrendben zárol; a megoldás a mindig azonos (például id szerinti) zárolási sorrend és rövid
tranzakciók.

```sql
-- Dialektus: PostgreSQL
-- MVCC belülről: xmin = létrehozó tranzakció, xmax = törlő/felülíró tranzakció
SELECT xmin, xmax, ctid, id, balance FROM accounts WHERE id = 1;
SELECT relname, n_live_tup, n_dead_tup, last_autovacuum
FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 5;

-- Pesszimista zárolás: az olvasott sort más író nem módosíthatja a COMMIT-ig
BEGIN;
SELECT stock FROM products WHERE id = 3 FOR UPDATE;
UPDATE products SET stock = stock - 1 WHERE id = 3;
COMMIT;

-- Feladatsor több workerrel: a zárolt sorokat átugorja, nincs várakozás és dupla feldolgozás
WITH next_job AS (
  SELECT id FROM jobs
  WHERE status = 'queued'
  ORDER BY priority DESC, id
  FOR UPDATE SKIP LOCKED
  LIMIT 1
)
UPDATE jobs j
SET status = 'running', started_at = now()
FROM next_job
WHERE j.id = next_job.id
RETURNING j.id, j.payload;

-- DEADLOCK megelőzése: mindkét sort előre, azonos (id szerinti) sorrendben zároljuk
BEGIN;
SELECT id FROM accounts WHERE id IN (1, 2) ORDER BY id FOR UPDATE;
UPDATE accounts SET balance = balance - 100 WHERE id = 2;
UPDATE accounts SET balance = balance + 100 WHERE id = 1;
COMMIT;

-- Ki kire vár? (diagnosztika)
SELECT pid, pg_blocking_pids(pid) AS blocked_by, state, left(query, 60) AS query
FROM pg_stat_activity
WHERE cardinality(pg_blocking_pids(pid)) > 0;

-- Védőhálók munkamenet szinten
SET lock_timeout = '3s';
SET idle_in_transaction_session_timeout = '30s';
```

## Normalizálás vs denormalizálás
<!-- q: Mennyire normalizáljam az adatbázist, és mikor éri meg denormalizálni? -->
<!-- tags: normalization, 1nf, 2nf, 3nf, denormalization, schema design, redundancy -->

A normalizálás (1NF: atomi értékek, 2NF/3NF: minden nem-kulcs oszlop a teljes kulcstól és csak attól
függ) megszünteti a redundanciát, így egy tény egyetlen helyen él, és nem jönnek létre ellentmondó
másolatok. A denormalizálás tudatos redundancia olvasási teljesítményért (előre számolt összeg,
másolt név), ennek ára, hogy minden írásnál karban kell tartani. Fontos különbség: a rendeléskori
egységár nem redundancia, hanem történeti tény, mert a termék ára később változhat. Pénzt egész
számként (fillérben) vagy NUMERIC-ként tárolj, soha ne lebegőpontosan.

```sql
-- Dialektus: SQLite / PostgreSQL / MySQL
-- ROSSZ: orders_flat(order_id, customer_name, customer_email, product_ids = '1,4,9')
--        -> ismétlődő vevőadat és több érték egy mezőben (1NF sértés)

-- 3NF séma
CREATE TABLE customer (
  id    INTEGER PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  name  TEXT NOT NULL
);
CREATE TABLE product (
  id    INTEGER PRIMARY KEY,
  sku   TEXT NOT NULL UNIQUE,
  name  TEXT NOT NULL,
  price INTEGER NOT NULL CHECK (price >= 0)              -- fillérben
);
CREATE TABLE purchase (
  id          INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES customer(id),
  created_at  TEXT NOT NULL
);
CREATE TABLE purchase_line (
  purchase_id INTEGER NOT NULL REFERENCES purchase(id) ON DELETE CASCADE,
  product_id  INTEGER NOT NULL REFERENCES product(id),
  qty         INTEGER NOT NULL CHECK (qty > 0),
  unit_price  INTEGER NOT NULL,          -- rendeléskori ár: történeti tény, nem redundancia
  PRIMARY KEY (purchase_id, product_id)
);

-- Tudatos denormalizálás: előre számolt végösszeg a gyors listázáshoz
ALTER TABLE purchase ADD COLUMN total_cache INTEGER NOT NULL DEFAULT 0;

INSERT INTO customer VALUES (1, 'vevo@example.com', 'Teszt Vevő');
INSERT INTO product VALUES (1, 'KB-01', 'Billentyűzet', 1599000), (2, 'MS-01', 'Egér', 499000);
INSERT INTO purchase (id, customer_id, created_at) VALUES (1, 1, '2026-05-01');
INSERT INTO purchase_line VALUES (1, 1, 1, 1599000), (1, 2, 2, 499000);

-- A cache frissítése (élesben trigger vagy az író kódút végzi, egy tranzakcióban)
UPDATE purchase
SET total_cache = (SELECT SUM(qty * unit_price) FROM purchase_line
                   WHERE purchase_line.purchase_id = purchase.id);
SELECT id, total_cache FROM purchase;    -- 2597000
```

## Kényszerek és triggerek
<!-- q: Hogyan biztosítsam az adatintegritást kényszerekkel és triggerekkel? -->
<!-- tags: constraint, check, foreign key, unique, not null, trigger, audit log, integrity -->

A kényszerek (NOT NULL, UNIQUE, CHECK, FOREIGN KEY) az adatbázis szintjén garantálják az invariánsokat,
így egyetlen kliens vagy hibás migráció sem tud érvénytelen adatot írni; ez erősebb, mint az
alkalmazásoldali ellenőrzés. A trigger egy eseményre (INSERT/UPDATE/DELETE) automatikusan lefutó kód,
például audit naplóhoz vagy származtatott értékek karbantartásához. A triggerek rejtett mellékhatások,
nehezen debugolhatók és tömeges írásnál lassítanak, ezért csak valóban adatbázis-szintű szabályokra
használd őket. SQLite-ban az idegen kulcsokat kapcsolatonként PRAGMA foreign_keys = ON-nal kell
bekapcsolni.

```sql
-- Dialektus: SQLite (PostgreSQL trigger-függvény: lásd a PL/pgSQL szakaszt)
PRAGMA foreign_keys = ON;
CREATE TABLE account (
  id       INTEGER PRIMARY KEY,
  owner    TEXT NOT NULL,
  currency TEXT NOT NULL CHECK (currency IN ('HUF', 'EUR')),
  balance  INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),   -- nem mehet mínuszba
  UNIQUE (owner, currency)                                    -- devizánként egy számla
);
CREATE TABLE transfer (
  id      INTEGER PRIMARY KEY,
  from_id INTEGER NOT NULL REFERENCES account(id) ON DELETE RESTRICT,
  to_id   INTEGER NOT NULL REFERENCES account(id) ON DELETE RESTRICT,
  amount  INTEGER NOT NULL CHECK (amount > 0),
  CHECK (from_id <> to_id)                                    -- tábla szintű CHECK
);
CREATE TABLE balance_audit (
  account_id INTEGER, old_balance INTEGER, new_balance INTEGER,
  changed_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Minden átutalás automatikusan könyvel; ha a CHECK sérül, az egész INSERT visszagördül
CREATE TRIGGER trg_transfer_apply AFTER INSERT ON transfer
FOR EACH ROW
BEGIN
  UPDATE account SET balance = balance - NEW.amount WHERE id = NEW.from_id;
  UPDATE account SET balance = balance + NEW.amount WHERE id = NEW.to_id;
END;

-- Audit: csak akkor naplóz, ha az egyenleg ténylegesen változott
CREATE TRIGGER trg_balance_audit AFTER UPDATE OF balance ON account
FOR EACH ROW WHEN OLD.balance <> NEW.balance
BEGIN
  INSERT INTO balance_audit (account_id, old_balance, new_balance)
  VALUES (NEW.id, OLD.balance, NEW.balance);
END;

INSERT INTO account (id, owner, currency, balance) VALUES (1, 'A', 'HUF', 10000), (2, 'B', 'HUF', 0);
INSERT INTO transfer (from_id, to_id, amount) VALUES (1, 2, 2500);
SELECT account_id, old_balance, new_balance FROM balance_audit;   -- 2 sor
-- INSERT INTO transfer (from_id, to_id, amount) VALUES (2, 1, 999999);  -> CHECK hiba
```

## PL/pgSQL függvények, trigger-függvények és eljárások
<!-- q: Hogyan írjak tárolt függvényt és eljárást PostgreSQL-ben PL/pgSQL-lel? -->
<!-- tags: pl/pgsql, stored procedure, function, trigger function, plpgsql, exception, call -->

PostgreSQL-ben a FUNCTION értéket ad vissza és SELECT-ből hívható, de nem kezelhet tranzakciót; a
PROCEDURE (11+) CALL-lal hívható, és belül COMMIT-olhat, ami kötegelt karbantartáshoz hasznos. Az
egyszerű lekérdezést érdemes LANGUAGE sql-ként írni (a tervező beágyazhatja), a vezérlési szerkezetet
igénylőt plpgsql-ként. A volatilitás (IMMUTABLE / STABLE / VOLATILE) megjelölése befolyásolja az
optimalizálást és az indexelhetőséget, hibás megjelölés rossz eredményt adhat. Az EXCEPTION blokk
belül implicit savepointot nyit, ezért szoros ciklusban drága.

```sql
-- Dialektus: PostgreSQL
-- FÜGGVÉNY (LANGUAGE sql, STABLE: egy snapshoton belül azonos eredmény)
CREATE OR REPLACE FUNCTION purchase_total(p_purchase_id bigint)
RETURNS numeric
LANGUAGE sql STABLE
AS $$
  SELECT COALESCE(SUM(qty * unit_price), 0)
  FROM purchase_line WHERE purchase_id = p_purchase_id;
$$;

-- TRIGGER-FÜGGVÉNY: updated_at automatikus frissítése
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;                     -- BEFORE triggerben a módosított sort adjuk vissza
END;
$$;
CREATE TRIGGER trg_products_updated
BEFORE UPDATE ON products
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ELJÁRÁS: régi események archiválása kötegenként, köztes COMMIT-tal
CREATE OR REPLACE PROCEDURE archive_old_events(p_before timestamptz, p_batch int DEFAULT 5000)
LANGUAGE plpgsql AS $$
DECLARE
  v_moved int;
BEGIN
  LOOP
    WITH moved AS (
      DELETE FROM events
      WHERE id IN (SELECT id FROM events WHERE created_at < p_before LIMIT p_batch)
      RETURNING *
    )
    INSERT INTO events_archive SELECT * FROM moved;

    GET DIAGNOSTICS v_moved = ROW_COUNT;
    RAISE NOTICE 'Áthelyezve: % sor', v_moved;
    EXIT WHEN v_moved = 0;
    COMMIT;                       -- rövid zárak, kisebb WAL-csúcsok
  END LOOP;
END;
$$;
CALL archive_old_events(now() - interval '90 days');

-- Hibakezelés EXCEPTION blokkal
CREATE OR REPLACE FUNCTION safe_div(a numeric, b numeric) RETURNS numeric
LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
  RETURN a / b;
EXCEPTION WHEN division_by_zero THEN
  RETURN NULL;
END;
$$;
```

## JSONB a PostgreSQL-ben
<!-- q: Hogyan tároljak és kérdezzek le JSON adatot hatékonyan PostgreSQL-ben? -->
<!-- tags: jsonb, json, gin index, jsonpath, jsonb_set, generated column, semi-structured -->

A jsonb bináris, előre feldolgozott JSON-típus: a kulcsok sorrendje és a duplikátumok nem maradnak
meg, cserébe gyorsan kérdezhető és GIN-nel indexelhető (a sima json csak szövegként tárol). A -> jsonb-t,
a ->> szöveget ad vissza, a @> tartalmazás-operátor és a jsonpath (@?, @@) indexet tud használni. A
gyakran szűrt mezőt érdemes generált oszlopba kiemelni, mert így típusos és B-tree-vel indexelhető. Ne
tegyél mindent JSON-ba: a kulcsokra nincs kényszer, idegen kulcs vagy statisztika, és a jsonb_set
minden módosításnál a teljes dokumentumot újraírja.

```sql
-- Dialektus: PostgreSQL 12+
CREATE TABLE product_doc (
  id    bigserial PRIMARY KEY,
  data  jsonb NOT NULL,
  price numeric GENERATED ALWAYS AS ((data->>'price')::numeric) STORED  -- kiemelt mező
);
INSERT INTO product_doc (data) VALUES
 ('{"name":"Laptop","price":349990,"tags":["it","sale"],"specs":{"ram":16,"cpu":"x86"}}'),
 ('{"name":"Egér","price":4990,"tags":["it"],"specs":{"dpi":1600}}');

-- GIN index: a jsonb_path_ops kisebb és gyorsabb, de csak a @> / @? / @@ operátorokat tudja
CREATE INDEX idx_product_doc_data ON product_doc USING gin (data jsonb_path_ops);

-- -> jsonb, ->> szöveg, #>> útvonal szövegként; @> tartalmazás (indexelhető)
SELECT data->>'name' AS name, (data #>> '{specs,ram}')::int AS ram_gb
FROM product_doc
WHERE data @> '{"tags":["sale"]}';

-- Kulcs létezése és SQL/JSON path szűrés
SELECT id FROM product_doc WHERE data ? 'specs';
SELECT id FROM product_doc WHERE data @? '$.specs.ram ? (@ >= 16)';

-- Tömb kibontása sorokká
SELECT p.id, t.tag
FROM product_doc p
CROSS JOIN LATERAL jsonb_array_elements_text(p.data->'tags') AS t(tag);

-- Részleges módosítás, kulcs törlése és összefésülés
UPDATE product_doc SET data = jsonb_set(data, '{specs,ram}', '32'::jsonb)
WHERE data->>'name' = 'Laptop';
UPDATE product_doc SET data = (data - 'tags') || '{"archived": true}'::jsonb
WHERE id = 2;

-- JSON összeállítása API válaszhoz
SELECT jsonb_agg(jsonb_build_object('id', id, 'name', data->>'name', 'price', price) ORDER BY id)
FROM product_doc;
```

## Teljes szöveges keresés (full-text search)
<!-- q: Hogyan valósítsak meg szöveges keresést rangsorolással SQL adatbázisban LIKE helyett? -->
<!-- tags: full-text search, tsvector, tsquery, gin, ts_rank, fts5, bm25, search -->

A LIKE '%szó%' nem használ B-tree indexet, nem ismeri a szótöveket és nem rangsorol; a teljes szöveges
keresés tokenekre bontja és normalizálja a szöveget, majd invertált indexet épít. PostgreSQL-ben a
tsvector (dokumentum) és tsquery (keresőkifejezés) típusokat GIN index gyorsítja, a setweight-tel a
cím többet érhet a törzsnél, a websearch_to_tsquery pedig Google-szerű szintaxist ért. SQLite-ban az
FTS5 virtuális tábla és a bm25 rangsor ad hasonlót. Magyar szövegnél a 'hungarian' konfiguráció
szótövez, ékezetfüggetlenséghez az unaccent kiterjesztés vagy remove_diacritics kell.

```sql
-- Dialektus: PostgreSQL 12+
CREATE TABLE articles (
  id    bigserial PRIMARY KEY,
  title text NOT NULL,
  body  text NOT NULL,
  -- súlyozott keresővektor generált oszlopban: a cím (A) többet ér a törzsnél (B)
  tsv tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('hungarian', title), 'A') ||
    setweight(to_tsvector('hungarian', body),  'B')
  ) STORED
);
CREATE INDEX idx_articles_tsv ON articles USING gin (tsv);

-- "pontos kifejezés", -kizárás, OR támogatott
SELECT id, title,
       ts_rank_cd(tsv, q) AS rank,
       ts_headline('hungarian', body, q, 'MaxWords=20, MinWords=5') AS snippet
FROM articles, websearch_to_tsquery('hungarian', 'adatbázis indexek -mysql') AS q
WHERE tsv @@ q
ORDER BY rank DESC
LIMIT 10;
```

```sql
-- Dialektus: SQLite (FTS5)
CREATE VIRTUAL TABLE notes_fts USING fts5(
  title, body, tokenize = 'unicode61 remove_diacritics 2'   -- ékezetfüggetlen tokenizálás
);
INSERT INTO notes_fts (title, body) VALUES
 ('Indexelés alapjai', 'A B-tree index rendezett, tartományos keresésre jó.'),
 ('Tranzakciók', 'Az izolációs szint határozza meg, mit lát a többi tranzakció.'),
 ('Keresés', 'A teljes szöveges keresés invertált indexet használ.');

-- prefix keresés (*); bm25: KISEBB érték = jobb találat; a cím 10x súllyal
SELECT title,
       snippet(notes_fts, 1, '[', ']', '...', 8) AS snip,
       bm25(notes_fts, 10.0, 1.0) AS score
FROM notes_fts
WHERE notes_fts MATCH 'index*'
ORDER BY score
LIMIT 5;
```

## Táblaparticionálás
<!-- q: Mikor és hogyan particionáljak egy nagy táblát PostgreSQL-ben? -->
<!-- tags: partitioning, range partition, list partition, hash partition, partition pruning, time series, retention -->

A particionálás egy logikai táblát több fizikai táblára bont egy kulcs (tipikusan idő) szerint. Fő
haszna a partition pruning (a lekérdezés csak az érintett partíciókat olvassa) és az olcsó adatmegőrzés:
egy régi hónap DROP-ja azonnali, míg egy hatalmas DELETE bloatot és VACUUM-terhelést okoz. Buktatók: az
elsődleges kulcsnak és a UNIQUE kényszereknek tartalmazniuk kell a partíciókulcsot, a partíciókulcsot
nem használó lekérdezés minden partíciót végigolvas, és a túl sok (ezres nagyságrendű) partíció lassítja
a tervezést. Néhány millió soros tábla alatt ritkán éri meg.

```sql
-- Dialektus: PostgreSQL 11+
CREATE TABLE measurements (
  device_id int              NOT NULL,
  ts        timestamptz      NOT NULL,
  value     double precision,
  PRIMARY KEY (device_id, ts)            -- a partíciókulcsot (ts) tartalmaznia kell
) PARTITION BY RANGE (ts);

CREATE TABLE measurements_2026_01 PARTITION OF measurements
  FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');   -- alsó határ zárt, felső nyitott
CREATE TABLE measurements_2026_02 PARTITION OF measurements
  FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE measurements_default PARTITION OF measurements DEFAULT;  -- kilógó sorok

-- A szülőn létrehozott index minden (jövőbeli) partícióra öröklődik
CREATE INDEX ON measurements (ts);

-- Partition pruning: a terv csak a januári partíciót tartalmazza
EXPLAIN SELECT avg(value) FROM measurements
WHERE ts >= '2026-01-10' AND ts < '2026-01-20';

-- Adatmegőrzés: lecsatolás és eldobás, DELETE nélkül
ALTER TABLE measurements DETACH PARTITION measurements_2026_01;
DROP TABLE measurements_2026_01;

-- LIST particionálás (régió szerint)
CREATE TABLE tenant_data (tenant_id int NOT NULL, region text NOT NULL, payload jsonb)
  PARTITION BY LIST (region);
CREATE TABLE tenant_data_eu PARTITION OF tenant_data FOR VALUES IN ('eu', 'uk');
CREATE TABLE tenant_data_us PARTITION OF tenant_data FOR VALUES IN ('us');

-- HASH particionálás (egyenletes elosztás)
CREATE TABLE sessions_p (id uuid NOT NULL, data jsonb) PARTITION BY HASH (id);
CREATE TABLE sessions_p0 PARTITION OF sessions_p FOR VALUES WITH (MODULUS 2, REMAINDER 0);
CREATE TABLE sessions_p1 PARTITION OF sessions_p FOR VALUES WITH (MODULUS 2, REMAINDER 1);
```

## Upsert: ON CONFLICT és ON DUPLICATE KEY UPDATE
<!-- q: Hogyan szúrjak be egy sort, vagy frissítsem, ha már létezik (upsert)? -->
<!-- tags: upsert, on conflict, on duplicate key update, insert or update, merge, idempotent -->

Az upsert atomian beszúr vagy frissít, így elkerülhető a "SELECT, aztán INSERT vagy UPDATE" versenyhelyzet.
PostgreSQL-ben és SQLite-ban az INSERT ... ON CONFLICT (oszlopok) DO UPDATE a megadott UNIQUE kényszerre
figyel, az excluded pszeudotábla a beszúrni próbált sort jelenti, és WHERE-rel feltételessé tehető.
MySQL-ben az ON DUPLICATE KEY UPDATE BÁRMELY egyedi index ütközésére aktiválódik, ami meglepetést okozhat,
és az AUTO_INCREMENT értéket ilyenkor is elhasználja. A REPLACE INTO kerülendő, mert DELETE + INSERT, így
elvesznek a nem megadott oszlopok, és FK-kaszkádok indulhatnak.

```sql
-- Dialektus: SQLite 3.24+ / PostgreSQL 9.5+
CREATE TABLE page_views (
  page          TEXT NOT NULL,
  day           TEXT NOT NULL,
  views         INTEGER NOT NULL DEFAULT 0,
  last_referrer TEXT,
  PRIMARY KEY (page, day)                    -- az ütközést ez a kényszer jelzi
);

-- Atomi számláló: első alkalommal beszúr, utána növel
INSERT INTO page_views (page, day, views, last_referrer)
VALUES ('/docs', '2026-06-01', 1, 'google')
ON CONFLICT (page, day) DO UPDATE
SET views         = page_views.views + excluded.views,
    last_referrer = COALESCE(excluded.last_referrer, page_views.last_referrer);

INSERT INTO page_views (page, day, views, last_referrer)
VALUES ('/docs', '2026-06-01', 1, NULL)
ON CONFLICT (page, day) DO UPDATE
SET views         = page_views.views + excluded.views,
    last_referrer = COALESCE(excluded.last_referrer, page_views.last_referrer);

-- Feltételes upsert: régebbi adat nem írhatja felül az újabbat
CREATE TABLE prices (sku TEXT PRIMARY KEY, price INTEGER NOT NULL, updated_at TEXT NOT NULL);
INSERT INTO prices VALUES ('A1', 1000, '2026-06-02');
INSERT INTO prices VALUES ('A1', 900, '2026-06-01')
ON CONFLICT (sku) DO UPDATE
SET price = excluded.price, updated_at = excluded.updated_at
WHERE excluded.updated_at > prices.updated_at;

-- Idempotens beszúrás: ütközésnél csendben kihagy
INSERT INTO prices VALUES ('A1', 1, '2000-01-01') ON CONFLICT DO NOTHING;

SELECT page, views, last_referrer FROM page_views;   -- 2, 'google'
SELECT sku, price FROM prices;                       -- 1000 marad
```

```sql
-- Dialektus: MySQL 8.0.19+ (sor-alias; régebben VALUES(oszlop) függvény)
INSERT INTO page_views (page, day, views, last_referrer)
VALUES ('/docs', '2026-06-01', 1, 'google') AS new
ON DUPLICATE KEY UPDATE
  views         = page_views.views + new.views,
  last_referrer = COALESCE(new.last_referrer, page_views.last_referrer);
```

## Lapozás: OFFSET vs keyset (seek)
<!-- q: Miért lassú az OFFSET-es lapozás nagy tábláknál, és hogyan működik a keyset pagination? -->
<!-- tags: pagination, keyset pagination, seek method, offset, limit, cursor, infinite scroll -->

Az OFFSET n LIMIT k lapozásnál az adatbázis az első n sort is beolvassa és eldobja, így a mély oldalak
egyre lassabbak, és ha közben új sor érkezik, elemek duplikálódnak vagy kimaradnak. A keyset (seek)
lapozás az előző oldal utolsó sorának rendezési kulcsából folytatja (WHERE (created_at, id) < (...)),
és indexszel bármilyen mélységben közvetlenül a helyére ugrik. Feltétele a determinisztikus, egyedi
rendezés (holtverseny-törő id) és egy pontosan ehhez illeszkedő összetett index. Hátránya, hogy
tetszőleges oldalszámra nem lehet ugrani, ezért végtelen görgetéshez és API kurzorokhoz ideális.

```sql
-- Dialektus: SQLite / PostgreSQL / MySQL 8 (a tesztadat-generálás SQLite szintaxis)
CREATE TABLE posts (
  id         INTEGER PRIMARY KEY,
  created_at TEXT NOT NULL,
  title      TEXT NOT NULL
);
-- Az index iránya és oszlopai egyezzenek a rendezéssel (holtverseny-törő id-vel)
CREATE INDEX idx_posts_created_id ON posts (created_at DESC, id DESC);

-- 1000 tesztsor, naponta 3 poszt (PostgreSQL-ben: generate_series)
WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 1000)
INSERT INTO posts (id, created_at, title)
SELECT i, date('2026-01-01', '+' || (i / 3) || ' days'), 'Poszt ' || i FROM n;

-- OFFSET: egyszerű, de a kihagyott 980 sort is beolvassa
SELECT id, created_at, title
FROM posts
ORDER BY created_at DESC, id DESC
LIMIT 20 OFFSET 980;

-- KEYSET: az előző oldal utolsó eleme ('2026-04-10', 298) a kurzor
-- (a kliens pl. base64-kódolt "2026-04-10|298" formában kapja vissza)
SELECT id, created_at, title
FROM posts
WHERE (created_at, id) < ('2026-04-10', 298)     -- sorérték-összehasonlítás
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- Ugyanez kifejtve, ha a dialektus nem ismeri a sorértékeket
SELECT id, created_at, title
FROM posts
WHERE created_at < '2026-04-10'
   OR (created_at = '2026-04-10' AND id < 298)
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

## SQL injection és paraméterezett lekérdezések
<!-- q: Hogyan védekezzek az SQL injection ellen? -->
<!-- tags: sql injection, security, prepared statement, parameterized query, bind parameter, dynamic sql, format -->

SQL injection akkor történik, ha felhasználói bemenet szövegösszefűzéssel kerül a lekérdezésbe, így a
támadó idézőjelekkel kiléphet az adatból és saját SQL-t futtathat. Az egyetlen megbízható védelem a
paraméterezett lekérdezés (prepared statement, bind paraméter): az érték külön csatornán utazik, és soha
nem értelmeződik SQL-ként; a kézi escape-elés és a feketelista nem elég. Azonosítót (tábla, oszlop,
rendezési irány) nem lehet paraméterezni, ezeket fehérlistával vagy PL/pgSQL-ben format('%I')-vel kell
kezelni. Kiegészítő védelem a legkisebb jogosultság elve: az alkalmazás felhasználója ne legyen
tulajdonos vagy superuser.

```sql
-- Dialektus: PostgreSQL
-- ROSSZ (kliensoldali összefűzés):
--   "SELECT * FROM users WHERE email = '" + email + "'"
--   email = x' OR '1'='1   ->   WHERE email = 'x' OR '1'='1'   -> minden sor!
-- JÓ: szerveroldali prepared statement, a $1 mindig adat
PREPARE find_user(text) AS
  SELECT id, email FROM users WHERE email = $1;
EXECUTE find_user('x'' OR ''1''=''1');   -- egyszerűen nem talál ilyen e-mailt
DEALLOCATE find_user;

-- Dinamikus SQL PL/pgSQL-ben: azonosító %I-vel idézve, érték USING paraméterrel
CREATE OR REPLACE FUNCTION count_by_status(p_table text, p_status text)
RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE
  n bigint;
BEGIN
  EXECUTE format('SELECT count(*) FROM %I WHERE status = $1', p_table)
    INTO n
    USING p_status;
  RETURN n;
END;
$$;
```

```javascript
// node-postgres: $1, $2 helyőrzők; a driver az értékeket külön küldi el
import pg from 'pg';
const pool = new pg.Pool();

// A rendezési oszlop NEM paraméterezhető -> fehérlista
const SORTABLE = new Set(['created_at', 'title', 'id']);

export async function searchPosts(term, sort = 'created_at', limit = 20) {
  const col = SORTABLE.has(sort) ? sort : 'created_at';
  const safeLimit = Math.min(Math.max(Number(limit) || 20, 1), 100);
  // A LIKE speciális karaktereit (% _ \) escape-eljük, hogy szó szerint keressen
  const pattern = '%' + String(term).replace(/[\\%_]/g, (m) => '\\' + m) + '%';
  const { rows } = await pool.query(
    `SELECT id, title FROM posts
      WHERE title ILIKE $1
      ORDER BY ${col} DESC
      LIMIT $2`,
    [pattern, safeLimit],
  );
  return rows;
}
```

## Lekérdezés-optimalizálási minták
<!-- q: Milyen gyakori mintákkal gyorsíthatom a lassú SQL lekérdezéseket? -->
<!-- tags: query optimization, sargable, exists, n+1, union, batching, analyze, performance -->

A legtöbb lassú lekérdezés néhány visszatérő okra vezethető vissza: függvénybe csomagolt indexelt
oszlop (nem "sargable" feltétel), felesleges SELECT *, COUNT(*) létezés-ellenőrzésre, N+1 lekérdezés a
kódból, különböző oszlopokon OR, és implicit típuskonverzió. Javításkor mindig mérj (EXPLAIN /
EXPLAIN QUERY PLAN) előtte és utána, mert a tervező döntése az adatok eloszlásától függ. Tömeges
módosítást kötegelj, hogy a zárak és a tranzakciós napló kicsik maradjanak, és frissítsd a
statisztikákat (ANALYZE) nagy adatbetöltés után.

```sql
-- Dialektus: SQLite (a minták PostgreSQL-ben és MySQL-ben is érvényesek)
CREATE TABLE logs (id INTEGER PRIMARY KEY, user_id INTEGER, level TEXT, created_at TEXT);
CREATE INDEX idx_logs_created ON logs (created_at);
CREATE INDEX idx_logs_user ON logs (user_id);

-- 1) SARGABLE: ROSSZ, a függvény miatt nem használható az index -> full scan
EXPLAIN QUERY PLAN SELECT count(*) FROM logs WHERE substr(created_at, 1, 7) = '2026-05';
--    JÓ: tartomány az eredeti oszlopon -> index range scan
EXPLAIN QUERY PLAN SELECT count(*) FROM logs
WHERE created_at >= '2026-05-01' AND created_at < '2026-06-01';

-- 2) Létezés: az EXISTS az első találatnál megáll, a COUNT(*) végigszámol
SELECT EXISTS (SELECT 1 FROM logs WHERE user_id = 42 AND level = 'error') AS has_error;

-- 3) N+1 helyett egy halmazalapú lekérdezés (a kód egyszerre kéri le az összes felhasználót)
SELECT user_id, count(*) AS errors
FROM logs
WHERE level = 'error' AND user_id IN (1, 2, 3)
GROUP BY user_id;

-- 4) OR különböző oszlopokon -> UNION, így mindkét ág a saját indexét használja
SELECT id FROM logs WHERE user_id = 42
UNION
SELECT id FROM logs WHERE created_at >= '2026-06-01';

-- 5) Tömeges törlés kötegekben (ismételd, amíg 0 sort érint)
DELETE FROM logs
WHERE id IN (SELECT id FROM logs WHERE created_at < '2025-01-01' LIMIT 1000);

-- 6) Statisztika frissítése a tervező számára
ANALYZE;
-- 7) Implicit konverzió: MySQL-ben VARCHAR oszlop = szám literál -> az index nem használható;
--    mindig az oszlop típusának megfelelő paramétert küldj.
```

## MySQL, PostgreSQL, SQLite és T-SQL különbségek
<!-- q: Miben különbözik a MySQL, a PostgreSQL és az SQLite, és melyiket válasszam? -->
<!-- tags: mysql, postgresql, sqlite, t-sql, dialect, comparison, auto increment, returning, collation -->

A dialektusok legtöbbször az automatikus azonosítóban, a beszúrt sor visszaadásában, a szövegösszefűzésben,
a dátumkezelésben, az upsert szintaxisában és az alapértelmezett collation-ben térnek el. Az SQLite
"type affinity" rendszere alapból bármilyen értéket beenged egy oszlopba (a STRICT tábla szigorít), és
egyszerre csak egy író lehet; a MySQL alapértelmezett utf8mb4_0900_ai_ci collation-je kis-nagybetű ÉS
ékezet-érzéketlen. Választás: SQLite beágyazott, edge, mobil és tesztkörnyezetre; PostgreSQL általános
OLTP-re fejlett típusokkal (JSONB, tömb, tartomány); MySQL ott, ahol a meglévő ökoszisztéma vagy
replikációs tudás azt indokolja; T-SQL a Microsoft-környezetben.

```sql
-- Dialektus: összehasonlítás (a futtatható sorok SQLite-ra vonatkoznak)
-- Automatikus azonosító:
--   PostgreSQL: id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY
--   MySQL:      id BIGINT AUTO_INCREMENT PRIMARY KEY
--   SQLite:     id INTEGER PRIMARY KEY          (rowid alias)
--   T-SQL:      id BIGINT IDENTITY(1,1) PRIMARY KEY
-- Beszúrt sor visszaadása:
--   PG / SQLite 3.35+: INSERT ... RETURNING id;  MySQL: LAST_INSERT_ID();  T-SQL: OUTPUT inserted.id
-- Összefűzés: PG / SQLite: a || b;  MySQL: CONCAT(a, b);  T-SQL: a + b vagy CONCAT
-- Első N sor: LIMIT n (PG, MySQL, SQLite);  T-SQL: SELECT TOP (n) ... / OFFSET ... FETCH
-- Idézés: PG / SQLite: "order";  MySQL: `order`;  T-SQL: [order]
-- Logikai típus: PG: boolean;  MySQL: TINYINT(1);  SQLite: 0/1;  T-SQL: BIT

-- SQLite típusossága: STRICT nélkül a 'sok' szöveg is bekerülne az INTEGER oszlopba
CREATE TABLE strict_demo (id INTEGER PRIMARY KEY, qty INTEGER NOT NULL) STRICT;
INSERT INTO strict_demo VALUES (1, '42');        -- veszteség nélkül konvertálható -> 42
-- INSERT INTO strict_demo VALUES (2, 'sok');    -> hiba: cannot store TEXT value in INTEGER column
SELECT typeof(qty) FROM strict_demo;             -- integer

-- Dátum/idő: SQLite-ban nincs dátumtípus, ISO-8601 szöveg + függvények
--   PG: now() - interval '7 days';  MySQL: NOW() - INTERVAL 7 DAY;  T-SQL: DATEADD(day, -7, SYSDATETIME())
SELECT datetime('now', '-7 days') AS week_ago, strftime('%Y-%m', 'now') AS year_month;

-- Kis-nagybetű: SQLite-ban az = érzékeny, a LIKE ASCII-re érzéketlen
SELECT 'alma' = 'ALMA' AS eq, 'alma' LIKE 'ALMA' AS like_eq;   -- 0, 1
-- MySQL (utf8mb4_0900_ai_ci): 'alma' = 'ÁLMA' -> 1 !   PG: érzékeny (ILIKE / citext)

-- Konkurencia: PG és MySQL InnoDB sorszintű zárolás + MVCC;
-- SQLite: egy író egyszerre, WAL módban az olvasók nem blokkolják az írót
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;   -- zárolt adatbázisnál ennyi ms-ig vár, mielőtt SQLITE_BUSY-t ad
```
