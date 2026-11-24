# R
<!-- tech: r -->
<!-- aliases: rlang, tidyverse -->

Az R statisztikai számításokra és adatelemzésre tervezett, dinamikusan típusos, interpretált nyelv; alapegysége a vektor, a legtöbb művelet vektorizált, a tipikus adatszerkezet pedig a data frame (táblázat). Funkcionális gyökerű (első osztályú függvények, lusta argumentum-kiértékelés, environmentek), több OO rendszerrel (S3, S4, R6), a memóriát garbage collector kezeli, és az objektumok módosításkor jellemzően másolódnak (copy-on-modify). Ereje az ökoszisztéma: tidyverse (dplyr, tidyr, ggplot2), statisztikai modellezés, CRAN és Bioconductor csomagok, valamint az Rcpp-vel C++-ba kiszervezhető forró pontok. Kiváló feltáró elemzéshez, vizualizációhoz és statisztikához; általános célú szoftverhez, webszerverhez vagy nagyon nagy, memórián túli adatokhoz kevésbé (ott Python, SQL vagy Spark a gyakoribb).

## Vektorok, vektorizáció és NA kezelés
<!-- q: Hogyan működnek a vektorok és a vektorizált műveletek R-ben, és hogyan kezeljem az NA-t? -->
<!-- tags: vectors, vectorization, na, recycling, coercion, factor, indexing -->

R-ben a skalár is egy 1 hosszú vektor, és a műveletek elemenként, ciklus nélkül (C-ben) futnak – ez gyors és tömör kódot ad. Az indexelés 1-alapú; negatív index kihagyást, logikai vektor szűrést, név pedig név szerinti elérést jelent. A hiányzó érték `NA`, ami minden műveleten "átterjed", ezért az összegző függvényeknek `na.rm = TRUE` kell. Buktató: a rövidebb vektor csendben ismétlődik (recycling), a `c()` közös típusra kényszerít (egy string mindent stringgé tesz), és az `1:length(x)` üres vektornál `c(1, 0)`-t ad – helyette `seq_along`/`seq_len` kell.

```r
x <- c(12.5, 7, NA, 3.2, 18)
length(x)                       # 5
x * 2                           # vektorizált: minden elem duplázva
x > 10                          # FALSE FALSE NA FALSE TRUE
sum(x > 10, na.rm = TRUE)       # TRUE = 1 -> darabszám: 2

# Az NA terjed: bármely művelet NA-val NA-t ad
mean(x)                         # NA
mean(x, na.rm = TRUE)           # 10.175
x[!is.na(x)]                    # szűrés logikai indexszel
ifelse(is.na(x), 0, x)          # vektorizált feltétel

# Recycling: a rövidebb vektor ismétlődik (figyelmeztet, ha nem többszöröse)
1:6 + c(10, 100)                # 11 102 13 104 15 106

# Indexelés: 1-alapú, negatív = kihagyás, név szerint
prices <- c(alma = 450, korte = 690, szilva = 520)
prices["korte"]
prices[-1]
prices[prices > 500]
names(which.max(prices))        # "korte"

# Típuskényszerítés: logical < integer < double < character
c(1, "a", TRUE)                 # mind character lesz!
as.numeric(c("1.5", "x"))       # 1.5 NA + figyelmeztetés

# Biztonságos szekvenciák
seq(0, 1, by = 0.25)
seq_len(0)                      # integer(0) – üres ciklus; az 1:0 viszont c(1, 0)!
for (i in seq_along(prices)) cat(names(prices)[i], prices[[i]], "\n")

# Hasznos vektor-függvények
cumsum(1:5)                     # 1 3 6 10 15
rev(sort(prices))
round(quantile(c(2, 4, 4, 5, 7, 9, 10), c(0.25, 0.5, 0.9)), 2)

# Faktor: kategorikus változó rögzített (itt rendezett) szintekkel
size <- factor(c("M", "S", "L", "M"), levels = c("S", "M", "L"), ordered = TRUE)
table(size)
size[size > "S"]                # rendezett faktor összehasonlítható
```

## Listák és data frame-ek
<!-- q: Hogyan használjam a listákat és a data frame-eket R-ben? -->
<!-- tags: list, data frame, subset, merge, aggregate, indexing, drop -->

A lista heterogén elemeket tárol tetszőleges mélységben – a JSON-szerű adatok R-beli megfelelője; a `[ ]` listát, a `[[ ]]` és `$` magát az elemet adja vissza. A data frame azonos hosszú oszlopvektorok listája, `[sor, oszlop]` indexeléssel, logikai sorszűréssel és `order()`-rel rendezve. Base R-ben az `aggregate`, `tapply` és `merge` (SQL JOIN) fedi le a tipikus átalakításokat. Buktató: egyetlen oszlop kiválasztása (`df[, "x"]`) alapból vektort ad, nem data frame-et – függvényekben `drop = FALSE` kell, különben egyoszlopos esetben eltörik a kód.

```r
# Lista: heterogén, beágyazható
user <- list(id = 1L, name = "Teszt", tags = c("admin", "dev"), meta = list(active = TRUE))
user$tags[2]                    # "dev"
user[["meta"]]$active           # TRUE
str(user["name"])               # [ ] -> lista; [[ ]] -> maga az elem

# data.frame: azonos hosszú oszlopok listája
orders <- data.frame(
  id       = 1:6,
  customer = c("A", "B", "A", "C", "B", "A"),
  amount   = c(1200, 450, 3100, 990, 1500, 270),
  date     = as.Date("2026-01-01") + c(0, 3, 5, 9, 12, 20)
)
str(orders)
summary(orders$amount)

# Indexelés [sor, oszlop]
orders[orders$amount > 1000, c("id", "amount")]
orders[order(-orders$amount), ][1:3, ]                 # top 3 összeg szerint
subset(orders, customer == "A" & amount > 500, select = c(id, amount))

# Új oszlopok és base R aggregálás
orders$vat     <- round(orders$amount * 0.27)
orders$month   <- format(orders$date, "%Y-%m")
aggregate(amount ~ customer, data = orders, FUN = sum)
tapply(orders$amount, orders$customer, mean)

# JOIN: all.x = TRUE -> LEFT JOIN, a hiányzó city NA lesz
customers <- data.frame(customer = c("A", "B", "D"), city = c("Budapest", "Szeged", "Pécs"))
merge(orders, customers, by = "customer", all.x = TRUE)

# Rekordlista (pl. API válasz) -> data frame
records <- list(list(k = "x", v = 1), list(k = "y", v = 2))
do.call(rbind, lapply(records, as.data.frame))

# Buktató: drop
class(orders[, "amount"])                  # "numeric"
class(orders[, "amount", drop = FALSE])    # "data.frame"
```

## Adatátalakítás dplyr pipeline-nal
<!-- q: Hogyan szűrjek, csoportosítsak és összesítsek adatot dplyr-rel? -->
<!-- tags: dplyr, tidyverse, pipe, filter, mutate, group_by, summarise, across, join -->

A dplyr "igékkel" (filter, mutate, select, arrange, summarise) írja le az adatátalakítást, a pipe (`|>` R 4.1+, vagy `%>%`) pedig balról jobbra olvasható láncot épít belőlük. A `group_by` + `summarise` csoportonként összesít, a `group_by` + `mutate` ablakfüggvényt ad (rang, előző érték, csoporton belüli arány), az `across` több oszlopra alkalmaz egyszerre. Saját függvényben a "curly-curly" (`{{ col }}`) adja tovább az oszlopnevet a tidy evaluationnek. Buktató: a `summarise` után maradhat csoportosítás – használd a `.groups = "drop"`-ot vagy az egyszeri `.by`-t, különben a következő lépés váratlanul csoportonként fut.

```r
library(dplyr)

sales <- tibble(
  region  = rep(c("Észak", "Dél", "Kelet"), each = 4),
  quarter = rep(paste0("Q", 1:4), times = 3),
  revenue = c(120, 135, 150, 160, 90, 95, 80, 110, 200, 210, 190, 230),
  cost    = c(80, 85, 100, 105, 70, 72, 65, 75, 120, 130, 125, 140)
)

report <- sales |>
  filter(revenue > 85) |>                        # sorok szűrése
  mutate(
    profit = revenue - cost,
    margin = profit / revenue,
    tier   = case_when(                          # vektorizált többágú feltétel
      margin >= 0.4  ~ "magas",
      margin >= 0.25 ~ "közepes",
      .default = "alacsony"
    )
  ) |>
  group_by(region) |>
  summarise(
    total_profit = sum(profit),
    avg_margin   = mean(margin),
    best_quarter = quarter[which.max(profit)],
    n            = n(),
    .groups      = "drop"                        # csoportosítás megszüntetése
  ) |>
  arrange(desc(total_profit))

# Ablakfüggvények: mutate csoportosítás után
sales |>
  group_by(region) |>
  mutate(
    growth  = revenue / lag(revenue) - 1,        # előző negyedévhez képest
    rank_in = min_rank(desc(revenue)),
    share   = revenue / sum(revenue)             # csoporton belüli arány
  ) |>
  ungroup()

# Több oszlop egyszerre: across + elnevezési sablon
sales |>
  summarise(across(c(revenue, cost), list(mean = mean, max = max), .names = "{.col}_{.fn}"), .by = region)

# Saját függvény oszlopnév-paraméterrel: {{ }}
top_by <- function(df, col, n = 3) {
  df |> arrange(desc({{ col }})) |> slice_head(n = n)
}
top_by(sales, cost, 2)

# Join
targets <- tibble(region = c("Észak", "Dél"), target = c(500, 400))
sales |>
  summarise(revenue = sum(revenue), .by = region) |>
  left_join(targets, by = join_by(region)) |>
  mutate(hit = revenue >= target)
```

## Tidy adatok tidyr-rel
<!-- q: Hogyan alakítsak széles táblát hosszúvá és vissza tidyr-rel? -->
<!-- tags: tidyr, pivot_longer, pivot_wider, tidy data, unnest, complete, nest -->

A tidy adat elve: minden változó egy oszlop, minden megfigyelés egy sor, minden érték egy cella – a tidyverse összes eszköze erre a formára van optimalizálva. A `pivot_longer` a "széles" (pl. Excelből jövő, évek oszlopokban) táblát hosszúvá alakítja, a `pivot_wider` riporthoz vissza; a `separate_wider_delim` és `unnest_longer` egy cellában tárolt több értéket bont szét. A `complete` kitölti a hiányzó kombinációkat, a `nest` pedig csoportonként beágyazott data frame-et készít, amin modellek is futtathatók. Buktató: a pivot után a "year" oszlop alapból karakter – a `names_transform`-mal alakítsd számmá.

```r
library(tidyr)
library(dplyr)

# Széles tábla: évek oszlopokban
wide <- tibble(
  country = c("HU", "AT", "SK"),
  `2022`  = c(9.7, 9.0, 5.4),
  `2023`  = c(9.6, 9.1, 5.4),
  `2024`  = c(9.6, 9.2, NA)
)

# pivot_longer: egy sor = egy megfigyelés
long <- wide |>
  pivot_longer(cols = -country, names_to = "year", values_to = "population",
               names_transform = list(year = as.integer)) |>
  drop_na(population)

# pivot_wider: vissza széles formára, előtaggal
long |> pivot_wider(names_from = year, values_from = population, names_prefix = "y")

# Egy cellában több érték: szétbontás oszlopokra és sorokra
raw <- tibble(id = 1:3, name_unit = c("hossz_cm", "tomeg_kg", "ido_s"), tags = c("a,b", "c", NA))
raw |>
  separate_wider_delim(name_unit, delim = "_", names = c("measure", "unit")) |>
  mutate(tags = strsplit(tags, ",")) |>
  unnest_longer(tags, keep_empty = TRUE)

# Hiányzó kombinációk kitöltése: minden ország × minden év
long |> complete(country, year = 2022:2024, fill = list(population = 0))

# Hiányzó értékek továbbvitele (pl. idősorban)
tibble(t = 1:5, v = c(1, NA, NA, 4, NA)) |> fill(v, .direction = "down")

# nest: csoportonként beágyazott data frame + modell csoportonként
mtcars |>
  group_by(cyl) |>
  nest() |>
  mutate(
    model = lapply(data, \(d) lm(mpg ~ wt, data = d)),
    slope = vapply(model, \(m) coef(m)[["wt"]], numeric(1))
  ) |>
  select(cyl, slope)
```

## Vizualizáció ggplot2-vel
<!-- q: Hogyan készítsek többrétegű, publikálható ábrát ggplot2-vel? -->
<!-- tags: ggplot2, visualization, grammar of graphics, facet, geom, theme, ggsave -->

A ggplot2 a "grammar of graphics" elvét követi: adat + esztétikai leképezés (`aes`: x, y, szín, méret) + geometriai rétegek (`geom_*`) + skálák + koordináták + téma, amelyek `+`-szal rétegezhetők. A facet ("small multiples") azonos skálán, csoportonként külön panelen mutatja az adatot, ami gyakran többet mond egy zsúfolt ábránál. Az összesített értékekhez `geom_col` kell (a `geom_bar` maga számol), a kategóriák sorrendjét a `reorder` állítja. Buktató: az `aes()`-en belüli konstans (`aes(colour = "blue")`) kategóriát hoz létre, nem színt – fix színt az `aes()`-en kívül adj meg.

```r
library(ggplot2)
library(dplyr)

df <- mpg |> mutate(class = reorder(class, hwy, FUN = median))

# Szórásdiagram + lineáris trend konfidenciasávval
p <- ggplot(df, aes(x = displ, y = hwy)) +
  geom_point(aes(colour = class), alpha = 0.6, size = 2) +
  geom_smooth(method = "lm", formula = y ~ x, se = TRUE, colour = "black") +
  scale_colour_brewer(palette = "Set2", name = "Kategória") +
  labs(
    title    = "Motor mérete vs. autópályás fogyasztás",
    subtitle = "Nagyobb motor, kevesebb mérföld/gallon",
    x = "Lökettérfogat (liter)", y = "Mérföld/gallon (autópálya)",
    caption = "Forrás: ggplot2::mpg"
  ) +
  theme_minimal(base_size = 12) +
  theme(legend.position = "bottom")

# Facet: csoportonként külön panel, közös skálán
p2 <- ggplot(df, aes(hwy)) +
  geom_histogram(binwidth = 2, fill = "steelblue", colour = "white") +
  facet_wrap(~ drv, ncol = 1,
             labeller = as_labeller(c(`4` = "4WD", f = "Elsőkerék", r = "Hátsókerék")))

# Boxplot + jitter: eloszlás és nyers pontok együtt
p3 <- ggplot(df, aes(class, hwy)) +
  geom_boxplot(outlier.shape = NA) +
  geom_jitter(width = 0.2, alpha = 0.3) +
  coord_flip()

# Előre összesített adat: geom_col + címkék
counts <- df |> count(manufacturer, sort = TRUE) |> slice_head(n = 8)
p4 <- ggplot(counts, aes(reorder(manufacturer, n), n)) +
  geom_col(fill = "grey40") +
  geom_text(aes(label = n), hjust = -0.2) +
  coord_flip() +
  labs(x = NULL, y = "Modellek száma")

# Mentés fix mérettel és felbontással
ggsave("hwy_vs_displ.png", p, width = 8, height = 5, dpi = 150)
```

## Az apply család és a funkcionális segédek
<!-- q: Mikor használjam a lapply, sapply, vapply és mapply függvényeket R-ben? -->
<!-- tags: apply, lapply, sapply, vapply, mapply, map, reduce, filter, functional -->

Az apply család explicit ciklus helyett egy függvényt alkalmaz egy kollekció minden elemére: a `lapply` mindig listát ad, a `sapply` megpróbál egyszerűsíteni, a `vapply` pedig deklarált kimeneti típussal típusbiztos – programkódban ezt használd. Az `apply` mátrix soraira/oszlopaira, a `mapply`/`Map` több vektoron párhuzamosan, a `tapply` csoportonként dolgozik; a `Filter`, `Reduce` és `Position` a funkcionális eszköztár többi része. Buktató: a `sapply` üres inputra `list()`-et ad vektor helyett, ami később váratlan hibát okoz; az apply-család nem automatikusan gyorsabb a jól megírt ciklusnál – az igazi gyorsulást a valódi vektorizáció (`rowSums`, `colMeans`) adja.

```r
# lapply: mindig lista
files <- c("a.csv", "b.csv")
sizes <- lapply(files, function(f) if (file.exists(f)) file.size(f) else NA_real_)

# sapply kiszámíthatatlan kimeneti típusa
sapply(1:3, function(i) i^2)               # numeric vektor
sapply(integer(0), function(i) i^2)        # list() – üres inputra LISTA!

# vapply: típusbiztos
vapply(1:3, function(i) i^2, numeric(1))
vapply(integer(0), function(i) i^2, numeric(1))   # numeric(0) – konzisztens

# Több értékes eredmény -> mátrix (oszlopok = csoportok)
stats <- vapply(split(mtcars$mpg, mtcars$cyl),
                function(v) c(mean = mean(v), sd = sd(v), n = length(v)),
                numeric(3))
t(stats)

# apply: mátrix soraira (1) vagy oszlopaira (2)
m <- matrix(rnorm(12), nrow = 3)
apply(m, 1, max)                           # soronkénti max
apply(m, 2, function(col) (col - mean(col)) / sd(col))
# Gyorsabb, vektorizált megfelelők: rowSums, colMeans, scale(m)

# Map/mapply: több vektoron párhuzamosan
Map(function(name, price) sprintf("%s: %d Ft", name, price), c("alma", "körte"), c(450L, 690L))
mapply(rep, 1:3, 3:1)                      # list(c(1,1,1), c(2,2), 3)

# Filter, Reduce, Position
Filter(function(x) x %% 2 == 0, 1:10)
Reduce(`+`, 1:5, accumulate = TRUE)        # 1 3 6 10 15
Position(function(x) x > 3, c(1, 5, 2, 7)) # 2 (első találat indexe)

# Reduce több data frame egymás utáni összefésülésére
Reduce(function(a, b) merge(a, b, by = "id"), list(
  data.frame(id = 1:3, x = 1:3),
  data.frame(id = 2:3, y = 5:6),
  data.frame(id = 3,   z = 9)
))

# Csoportonkénti számítás
tapply(mtcars$hp, mtcars$gear, median)
```

## Függvények: lusta kiértékelés, argumentumok, NSE
<!-- q: Hogyan működnek a függvények, az alapértelmezett argumentumok és a lusta kiértékelés R-ben? -->
<!-- tags: functions, lazy evaluation, arguments, match.arg, force, on.exit, nse, substitute -->

Az R függvény első osztályú objektum, és az utolsó kifejezés értéke a visszatérési érték. Az argumentumok lustán értékelődnek ki (promise): csak az első használatkor, így az alapértelmezett érték hivatkozhat más argumentumra, és a nem használt hiányzó argumentum nem hiba. A `match.arg` érvényes opciókat ellenőriz, a `stopifnot` előfeltételt, az `on.exit` garantált takarítást ad, a `...` pedig továbbadja a többi argumentumot. A nem-standard kiértékelés (`substitute`, `eval`) a kifejezést kódként éri el – erre épül a dplyr és a ggplot2. Buktató: closure-gyárban hívd a `force()`-ot, különben a lusta argumentum későn, már megváltozott értékkel értékelődik ki.

```r
summarise_vec <- function(x, stat = c("mean", "median", "trimmed"), digits = 2, ...) {
  stat <- match.arg(stat)                    # érvényes opció ellenőrzése, alapértelmezés: az első
  stopifnot(is.numeric(x), length(x) > 0)    # előfeltételek
  value <- switch(stat,
    mean    = mean(x, ...),                  # a ... továbbadja pl. a na.rm = TRUE-t
    median  = median(x, ...),
    trimmed = mean(x, trim = 0.1, ...)
  )
  round(value, digits)
}
summarise_vec(c(1, 5, NA, 9), "median", na.rm = TRUE)   # 5

# Lusta kiértékelés: b csak az első használatkor számolódik
f <- function(a, b = a * 2) {
  a <- a + 1
  b                                          # itt értékelődik ki: (a + 1) * 2
}
f(1)                                         # 4, nem 2!

g <- function(x, y) if (missing(y)) "y hiányzik" else y
g(1)

# force(): closure-gyárban kötelező
make_multiplier <- function(k) {
  force(k)
  function(x) x * k
}
mults <- lapply(1:3, make_multiplier)
mults[[2]](10)                               # 20

# on.exit: takarítás hiba esetén is (mint a finally)
read_head <- function(path, n = 5) {
  con <- file(path, "r")
  on.exit(close(con), add = TRUE)
  readLines(con, n = n)
}

# NSE: az argumentum kódként is elérhető
show_expr <- function(expr) {
  e <- substitute(expr)                      # a kifejezés, nem az értéke
  cat(deparse(e), "=", eval(e, parent.frame()), "\n")
}
show_expr(2 + 3 * 4)                         # 2 + 3 * 4 = 14

# Saját infix operátor és változó számú argumentum
`%+%` <- function(a, b) paste0(a, b)
"R" %+% "lang"
sum_all <- function(...) sum(unlist(list(...)))
sum_all(1, 2:3, c(a = 4))                    # 10
```

## Environmentek és closure-ök
<!-- q: Mik azok az environmentek R-ben és hogyan használjam őket állapot tárolására? -->
<!-- tags: environments, closures, scoping, superassignment, memoization, local, r6 -->

Minden függvényhívás új environmentet kap, amelynek szülője a függvény *definiálásának* helye (lexikális scope) – így jönnek létre a closure-ök, amelyek a `<<-` operátorral a szülő environmentben tárolt állapotot módosíthatják. Az environment az egyetlen beépített, referencia szerint átadott, módosítható objektum (a lista másolódik), ezért cache-hez, számlálóhoz, memoizáláshoz ideális; az R6 és a Reference Class osztályok is erre épülnek. A `local()` ideiglenes environmentet ad, a segédváltozók nem szivárognak ki. Buktató: a `<<-` ha nem találja a változót a szülőláncban, a globális környezetben hozza létre – ez nehezen felderíthető mellékhatás.

```r
# Closure: a count a gyár environmentjében él
counter_factory <- function() {
  count <- 0
  list(
    inc   = function(by = 1) { count <<- count + by; invisible(count) },  # <<- a szülőbe ír
    get   = function() count,
    reset = function() count <<- 0
  )
}
c1 <- counter_factory()
c1$inc(); c1$inc(5)
c1$get()                                    # 6
environment(c1$get)$count                   # belelátunk a closure környezetébe

# Environment mint módosítható cache (referencia szerint adódik át)
cache <- new.env(parent = emptyenv())
memo_fib <- function(n) {
  key <- as.character(n)
  if (!is.null(cache[[key]])) return(cache[[key]])
  res <- if (n < 2) n else memo_fib(n - 1) + memo_fib(n - 2)
  assign(key, res, envir = cache)
  res
}
memo_fib(50)                                # 12586269025, azonnal
length(ls(cache))                           # 51 tárolt érték

# Scope-lánc vizsgálata
outer_fn <- function() {
  x <- "outer"
  inner_fn <- function() {
    cat("x =", x, "| szülő env = outer_fn hívása:",
        identical(parent.env(environment()), parent.frame()), "\n")
  }
  inner_fn()
}
outer_fn()

# local: ideiglenes env, a tmp nem szivárog ki
cfg <- new.env()
local({
  tmp <- c(host = "localhost", port = "5432")
  for (k in names(tmp)) assign(k, tmp[[k]], envir = cfg)
})
exists("tmp")                               # FALSE
mget(c("host", "port"), envir = cfg)

# Függvény módosítja a hívó objektumát: környezettel igen, listával nem
bump_env  <- function(e) e$n <- e$n + 1
bump_list <- function(l) { l$n <- l$n + 1; invisible(NULL) }
e <- new.env(); e$n <- 0; bump_env(e); e$n         # 1
l <- list(n = 0);  bump_list(l); l$n               # 0 – másolaton dolgozott
```

## Lineáris regresszió lm-mel
<!-- q: Hogyan illesszek és értékeljek lineáris regressziós modellt R-ben? -->
<!-- tags: lm, linear regression, statistics, formula, predict, anova, diagnostics -->

Az `lm()` a formula-szintaxissal (`y ~ x1 + x2`) illeszt lineáris modellt; a faktorokból automatikusan dummy változók lesznek, a `*` interakciót, az `I()` szó szerinti aritmetikát jelent. A `summary` együtthatókat, standard hibát, p-értéket és R²-et ad, a `confint` konfidenciaintervallumot, a `predict` pedig előrejelzést konfidencia- vagy predikciós intervallummal. Modellek összevetésére a beágyazott modellek F-próbája (`anova`) és az AIC szolgál, a diagnosztikai ábrák a feltevések (linearitás, homoszkedaszticitás, normalitás) ellenőrzésére. Buktató: a tanító adaton mért R² túl optimista – a valódi teljesítményt külön teszthalmazon (vagy keresztvalidációval) mérd.

```r
data(mtcars)
mtcars$am <- factor(mtcars$am, levels = c(0, 1), labels = c("automata", "manualis"))

fit <- lm(mpg ~ wt + hp + am, data = mtcars)
summary(fit)                # együtthatók, std. hiba, t, p, R², F-próba
coef(fit)
confint(fit, level = 0.95)

# Interakció és négyzetes tag
fit2 <- lm(mpg ~ wt * am + I(hp^2), data = mtcars)
anova(fit, fit2)            # nem beágyazott modelleknél inkább AIC
AIC(fit, fit2)              # kisebb = jobb (bünteti a paraméterszámot)

# Diagnosztika: reziduumok, befolyásos pontok
op <- par(mfrow = c(2, 2)); plot(fit); par(op)
influential <- which(cooks.distance(fit) > 4 / nrow(mtcars))
names(influential)
shapiro.test(residuals(fit))   # reziduumok normalitása (kis mintán)

# Előrejelzés új adatra predikciós intervallummal
new_cars <- data.frame(
  wt = c(2.5, 3.5), hp = c(110, 180),
  am = factor(c("manualis", "automata"), levels = levels(mtcars$am))
)
predict(fit, newdata = new_cars, interval = "prediction", level = 0.9)

# Tanító/teszt felosztás és RMSE
set.seed(42)
idx   <- sample(nrow(mtcars), size = round(0.75 * nrow(mtcars)))
train <- mtcars[idx, ]
test  <- mtcars[-idx, ]
m     <- lm(mpg ~ wt + hp + am, data = train)
rmse  <- sqrt(mean((test$mpg - predict(m, test))^2))
cat(sprintf("Teszt RMSE: %.2f mpg\n", rmse))

# Tidy kimenet data frame-ként (broom csomag):
# broom::tidy(fit, conf.int = TRUE); broom::glance(fit); broom::augment(fit)
```

## Általánosított lineáris modellek (glm)
<!-- q: Hogyan készítsek logisztikus és Poisson regressziót glm-mel R-ben? -->
<!-- tags: glm, logistic regression, poisson, odds ratio, binomial, offset, overdispersion -->

A `glm()` a lineáris modellt nem normális eloszlású kimenetekre általánosítja egy link-függvénnyel: bináris kimenetre `binomial` (logit), darabszámra `poisson` (log). A logisztikus modell együtthatói log-odds skálán vannak – az `exp()` esélyhányadost (odds ratio) ad –, a valószínűséghez a `predict(..., type = "response")` kell. A Poisson modellben a különböző kitettséget (megfigyelési idő, populáció) `offset(log(exposure))` kezeli. Buktató: ha a reziduális deviancia/szabadságfok aránya jóval 1 fölött van (túlszórás), a Poisson modell standard hibái alulbecsültek – ilyenkor quasipoisson vagy negatív binomiális modell (`MASS::glm.nb`) kell.

```r
data(mtcars)

# Logisztikus regresszió: kézi váltó (am = 1) valószínűsége
logit <- glm(am ~ wt + hp, data = mtcars, family = binomial(link = "logit"))
summary(logit)

# Esélyhányadosok Wald-intervallummal
or <- exp(cbind(OR = coef(logit), confint.default(logit)))
round(or, 3)

# Valószínűség: type = "response" nélkül log-odds jönne!
p_hat <- predict(logit, type = "response")
pred  <- as.integer(p_hat > 0.5)
table(actual = mtcars$am, predicted = pred)      # zavarási mátrix
mean(pred == mtcars$am)                          # pontosság

# Poisson regresszió kitettséggel (szimulált biztosítási adatok)
set.seed(1)
n <- 300
claims <- data.frame(
  age_group = factor(sample(c("18-25", "26-40", "41-65"), n, replace = TRUE)),
  exposure  = runif(n, 0.2, 1)                   # évek a biztosításban
)
rate <- c("18-25" = 0.5, "26-40" = 0.2, "41-65" = 0.15)[as.character(claims$age_group)]
claims$n_claims <- rpois(n, rate * claims$exposure)

pois <- glm(n_claims ~ age_group + offset(log(exposure)), family = poisson, data = claims)
round(exp(coef(pois)), 3)                        # rátaarányok a referenciacsoporthoz képest

# Túlszórás ellenőrzése
dispersion <- deviance(pois) / df.residual(pois)
cat(sprintf("Diszperzió: %.2f %s\n", dispersion,
            if (dispersion > 1.5) "-> quasipoisson / glm.nb javasolt" else "(rendben)"))
# MASS::glm.nb(n_claims ~ age_group + offset(log(exposure)), data = claims)
```

## S3 objektumorientáltság
<!-- q: Hogyan írjak saját S3 osztályt és generikus függvényt R-ben? -->
<!-- tags: s3, oop, generics, usemethod, print method, ops, nextmethod -->

Az S3 az R legegyszerűbb és legelterjedtebb OO rendszere: az osztály csak egy `class` attribútum, a metódus egy `generikus.osztály` nevű függvény, a dispatch-et pedig a `UseMethod()` végzi. A beépített generikusok (`print`, `format`, `summary`, `Ops` csoport) kiterjesztésével a saját típus természetesen illeszkedik az R-be – az `lm` és a `data.frame` is így működik. Az öröklés egy több elemű class vektor, a `NextMethod()` a következő osztály metódusát hívja. Buktató: az S3 nem validál – mindig konstruktorfüggvényen (`new_money`) keresztül hozz létre objektumot, szigorúbb igényekre ott az S4 vagy az R6.

```r
# Konstruktor: validálás + class attribútum
new_money <- function(amount, currency = "HUF") {
  stopifnot(is.numeric(amount), is.character(currency), length(currency) == 1)
  structure(list(amount = amount, currency = currency), class = "money")
}

# Saját generikus + metódusok
convert <- function(x, ...) UseMethod("convert")
convert.money <- function(x, to, rates = c(HUF = 1, EUR = 395, USD = 365), ...) {
  new_money(x$amount * rates[[x$currency]] / rates[[to]], to)
}
convert.default <- function(x, ...) stop("Nem konvertálható: ", class(x)[1])

# Beépített generikusok kiterjesztése
format.money <- function(x, ...) {
  sprintf("%s %s", formatC(x$amount, format = "f", digits = 2, big.mark = " "), x$currency)
}
print.money <- function(x, ...) {
  cat("<money>", format(x), "\n")
  invisible(x)                     # print konvenció: a bemenetet adja vissza
}

# Ops csoport-generikus: +, -, <, >, == egy helyen
Ops.money <- function(e1, e2) {
  if (!inherits(e2, "money") || e1$currency != e2$currency) stop("Eltérő pénznem")
  switch(.Generic,
    "+"  = new_money(e1$amount + e2$amount, e1$currency),
    "-"  = new_money(e1$amount - e2$amount, e1$currency),
    ">"  = e1$amount > e2$amount,
    "<"  = e1$amount < e2$amount,
    "==" = e1$amount == e2$amount,
    stop("Nem támogatott művelet: ", .Generic)
  )
}

a <- new_money(15000)
b <- new_money(2500)
a + b                              # <money> 17 500.00 HUF
convert(a, "EUR")                  # <money> 37.97 EUR
a > b                              # TRUE

# Öröklés: class vektor + NextMethod
new_salary <- function(amount, period = "hónap") {
  obj <- new_money(amount)
  obj$period <- period
  class(obj) <- c("salary", class(obj))
  obj
}
print.salary <- function(x, ...) {
  cat("Fizetés /", x$period, ": ")
  NextMethod()                     # továbbhív a print.money-ra
}
new_salary(650000)
inherits(new_salary(1), "money")   # TRUE
```

## Hibakezelés és condition-ök
<!-- q: Hogyan kezeljem a hibákat és figyelmeztetéseket tryCatch-csel R-ben? -->
<!-- tags: error handling, trycatch, conditions, withcallinghandlers, warning, restarts, stop -->

R-ben a hibák, figyelmeztetések és üzenetek "condition" objektumok, amelyek osztályvektora szerint kezelhetők; saját condition-osztállyal (pl. `http_404`, `http_error`) a hívó finoman válogathat. A `tryCatch` a handler lefutása után *megszakítja* a hívást (mint a try/catch), míg a `withCallingHandlers` handlere után a végrehajtás folytatódik – naplózásra és figyelmeztetések elnyelésére (`invokeRestart("muffleWarning")`) ez kell. A `finally` garantált takarítást ad. Buktató: a `try(..., silent = TRUE)` csendben elnyeli a hibát; az eredményt mindig vizsgáld `inherits(res, "try-error")`-ral.

```r
# Saját condition-osztály: típus szerint kezelhető hiba
http_error <- function(status, url) {
  structure(
    list(message = sprintf("HTTP %d: %s", status, url), call = sys.call(-1), status = status),
    class = c(paste0("http_", status), "http_error", "error", "condition")
  )
}

fetch_json <- function(url) {
  # Szimulált hálózati hívás a példához
  status <- if (grepl("missing", url)) 404L else if (grepl("flaky", url)) 503L else 200L
  if (status != 200L) stop(http_error(status, url))
  if (grepl("old", url)) warning("Elavult végpont: ", url, call. = FALSE)
  list(ok = TRUE, url = url)
}

# tryCatch: a handler után a hívás MEGSZAKAD
safe_fetch <- function(url, retries = 3) {
  for (attempt in seq_len(retries)) {
    result <- tryCatch(
      fetch_json(url),
      http_404   = function(e) { message("Nem található: ", url); NULL },  # specifikusabb előbb
      http_error = function(e) {
        if (attempt == retries) stop(e)              # utolsó próbánál továbbdobjuk
        message(sprintf("Újrapróbálás (%d): %s", attempt, conditionMessage(e)))
        structure(list(), class = "retry")
      }
    )
    if (!inherits(result, "retry")) return(result)
    Sys.sleep(0.05 * 2^attempt)                      # exponenciális backoff
  }
}

safe_fetch("https://example.com/api/missing")
res <- try(safe_fetch("https://example.com/api/flaky"), silent = TRUE)
inherits(res, "try-error")                           # TRUE

# withCallingHandlers: a handler után a végrehajtás FOLYTATÓDIK
warn_log <- character()
out <- withCallingHandlers(
  fetch_json("https://example.com/api/old"),
  warning = function(w) {
    warn_log <<- c(warn_log, conditionMessage(w))
    invokeRestart("muffleWarning")                   # ne jelenjen meg a konzolon
  }
)
warn_log

# Hibák értékként egy kötegelt feldolgozásban
results <- lapply(c("a/ok", "b/missing"), \(u) tryCatch(fetch_json(u), error = \(e) e))
vapply(results, inherits, logical(1), what = "error")   # FALSE TRUE
```

## Teljesítmény: vektorizáció, profilozás, párhuzamosítás
<!-- q: Hogyan gyorsítsam az R kódot és hogyan mérjem a teljesítményt? -->
<!-- tags: performance, vectorization, preallocation, profiling, rprof, parallel, data.table -->

Az R-ben a leggyakoribb lassúság oka a ciklusban növelt vektor (minden `c()` új másolatot készít, ami O(n²)), ezért mindig foglalj előre (`numeric(n)`), vagy még jobb, ha vektorizált, C-ben futó függvényt használsz (`rowSums`, `cumsum`, logikai indexelés). Mérésre a `system.time`, pontosabban a `bench::mark`, a szűk keresztmetszet megtalálására az `Rprof`/`profvis` való. Nagy táblákhoz a `data.table` referencia szerinti módosítással és gyors csoportosítással nagyságrendeket gyorsíthat, CPU-kötött független feladatokhoz a beépített `parallel` csomag ad több magot. Buktató: Windowson nincs fork, ezért a `mclapply` ott nem párhuzamos – socket clustert (`makeCluster`) kell használni, és a szükséges objektumokat `clusterExport`-tal átadni.

```r
# 1) Ciklusban növelt vektor: O(n²) másolás
slow_grow <- function(n) { out <- c(); for (i in seq_len(n)) out <- c(out, i^2); out }
# 2) Előfoglalás: O(n)
prealloc  <- function(n) { out <- numeric(n); for (i in seq_len(n)) out[i] <- i^2; out }
# 3) Vektorizált: a ciklus C-ben fut
vectorized <- function(n) seq_len(n)^2

n <- 2e4
system.time(slow_grow(n))
system.time(prealloc(n))
system.time(vectorized(n))
stopifnot(identical(prealloc(n), vectorized(n)))
# Pontosabb mérés memóriával: bench::mark(prealloc(n), vectorized(n))

# Gyakori vektorizált helyettesítések
x  <- runif(1e6)
s1 <- sum(x[x > 0.5])                       # ciklus + if helyett logikai indexelés
m  <- matrix(runif(1e6), ncol = 100)
rs <- rowSums(m)                            # apply(m, 1, sum) helyett, sokszor gyorsabb
ids <- paste0("id_", seq_len(1e5))          # egyben, nem ciklusban fűzve

# Profilozás: hol megy el az idő?
prof_file <- tempfile()
Rprof(prof_file)
invisible(replicate(20, prealloc(5e4)))
Rprof(NULL)
head(summaryRprof(prof_file)$by.self)

# Nagy táblák data.table-lel (referencia szerinti módosítás, nincs másolás):
# library(data.table)
# dt <- as.data.table(df)
# dt[amount > 1000, vat := amount * 0.27]   # := helyben
# dt[, .(total = sum(amount)), by = customer]

# Párhuzamosítás a base parallel csomaggal (Windowson is működő socket cluster)
library(parallel)
cl <- makeCluster(max(1, detectCores() - 1))
res <- parLapply(cl, 1:8, function(i) sum(sqrt(seq_len(1e6) + i)))
stopCluster(cl)                             # függvényben: on.exit(stopCluster(cl)) garantálja
length(res)
```

## C++ gyorsítás Rcpp-vel
<!-- q: Hogyan írjak gyors C++ függvényt R-hez Rcpp-vel? -->
<!-- tags: rcpp, c++, performance, sourcecpp, cppfunction, native code, loops -->

Ha egy algoritmus nem vektorizálható (csúszó ablak, rekurzió, egymásra épülő iterációk), az R ciklus lassú marad – ilyenkor az Rcpp-vel a forró pontot C++-ban írjuk meg, és R függvényként hívjuk. A `cppFunction` egy stringből fordít, nagyobb kódhoz külön `.cpp` fájl és `sourceCpp()` kell, ahol a `// [[Rcpp::export]]` jelöli az exportált függvényt; csomagban az Rcpp ezt automatikusan beköti. Az Rcpp típusok (`NumericVector`, `NumericMatrix`) közvetlenül az R memóriáját érik el másolás nélkül, és a `stop()` R hibává alakul. Buktató: fordítóeszközlánc kell (Windowson Rtools), az NA-kat a C++ kódban külön kell kezelni, és mindig vesd össze az eredményt egy egyszerű R referencia-implementációval.

```r
library(Rcpp)

# Csúszó átlag O(n)-ben – R-ben nehezen vektorizálható, C++-ban triviális
cppFunction('
NumericVector rolling_mean(NumericVector x, int window) {
  int n = x.size();
  if (window < 1 || window > n) stop("Érvénytelen ablakméret");
  NumericVector out(n, NA_REAL);            // NA-val előtöltve
  double sum = 0.0;
  for (int i = 0; i < n; ++i) {
    sum += x[i];
    if (i >= window) sum -= x[i - window];  // ablak elejének kivonása
    if (i >= window - 1) out[i] = sum / window;
  }
  return out;
}')

x <- cumsum(rnorm(1e6))
r_version <- function(x, k) as.numeric(stats::filter(x, rep(1 / k, k), sides = 1))
stopifnot(isTRUE(all.equal(rolling_mean(x, 50), r_version(x, 50))))   # ellenőrzés referenciával
system.time(rolling_mean(x, 50))
```

```cpp
// src/pairwise.cpp – nagyobb kód külön fájlban; betöltés: Rcpp::sourceCpp("src/pairwise.cpp")
#include <Rcpp.h>
#include <cmath>
using namespace Rcpp;

// [[Rcpp::export]]
NumericMatrix pairwise_dist(NumericMatrix pts) {
  const int n = pts.nrow(), d = pts.ncol();
  NumericMatrix out(n, n);
  for (int i = 0; i < n; ++i) {
    for (int j = i + 1; j < n; ++j) {
      double s = 0.0;
      for (int k = 0; k < d; ++k) {
        const double diff = pts(i, k) - pts(j, k);
        s += diff * diff;
      }
      out(i, j) = out(j, i) = std::sqrt(s);   // szimmetrikus mátrix
    }
  }
  return out;
}
```

```r
sourceCpp("src/pairwise.cpp")
pts <- matrix(runif(2000), ncol = 2)
stopifnot(isTRUE(all.equal(pairwise_dist(pts), as.matrix(dist(pts)), check.attributes = FALSE)))
```
