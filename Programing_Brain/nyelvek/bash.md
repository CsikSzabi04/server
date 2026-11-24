# Bash
<!-- tech: bash -->
<!-- aliases: shell, sh, zsh -->

A Bash (Bourne Again SHell) a Linux és sok Unix-szerű rendszer alapértelmezett parancsértelmezője és szkriptnyelve: a programokat folyamatokként indítja, szöveges adatfolyamokat köt össze pipe-okkal, és változókkal, ciklusokkal, függvényekkel automatizál. A POSIX `sh` szabvány bővített változata (tömbök, `[[ ]]`, process substitution), a zsh pedig nagyrészt kompatibilis vele interaktív extrákkal. Kiváló rendszeradminisztrációra, build- és deploy-szkriptekre, CI-lépésekre, cron-jobokra és a Unix-eszközök (grep, sed, awk, find, xargs) összefűzésére. Nem ideális összetett adatszerkezetekhez, nagy programokhoz, lebegőpontos számításhoz vagy hordozható hibakezeléshez — 100–200 sor fölött érdemes Pythonra vagy Go-ra váltani.

## Szigorú mód: set -euo pipefail
<!-- q: Mit csinál a set -euo pipefail és miért kezdjem vele a bash szkriptjeimet? -->
<!-- tags: set -e, set -u, pipefail, strict mode, error handling, shebang, ifs -->

A `set -e` hibás (nem nulla) exit kód esetén leállítja a szkriptet, a `set -u` hibát jelez nem definiált változóra (elgépelés!), a `set -o pipefail` pedig azt eredményezi, hogy a pipeline exit kódja az első hibázó elemé legyen, ne csak az utolsóé. Együtt a „strict mode” megakadályozza, hogy a szkript egy hiba után csendben, rossz állapotban fusson tovább. Buktatók: a `set -e` nem hat `if` feltételben, `||`/`&&` láncban és a függvényhívásokon belül sem mindig, ezért a kritikus parancsokat kifejezetten ellenőrizd; a várhatóan hibázó parancsot `|| true`-val jelöld. Az `IFS=$'\n\t'` a szóközt kiveszi a szóelválasztók közül.

```bash
#!/usr/bin/env bash
# Hordozható shebang: a PATH-ban lévő bash-t használja
set -Eeuo pipefail           # -E: az ERR trap a függvényekben is öröklődik
IFS=$'\n\t'                  # szóközzel tagolt fájlnevek ne essenek szét

# Nem definiált változó alapértékkel — set -u mellett így biztonságos
LOG_LEVEL="${LOG_LEVEL:-info}"
TARGET_DIR="${1:-$(mktemp -d)}"

# A grep 1-gyel tér vissza, ha nincs találat → set -e leállítana, ezért || true
count=$(grep -c 'ERROR' /etc/hostname 2>/dev/null || true)
# pipefail nélkül egy 'cmd | wc -l' lánc hibája elveszne (csak a wc exit kódja számítana)
echo "ERROR sorok: ${count:-0}, log szint: $LOG_LEVEL, cél: $TARGET_DIR"

# A set -e NEM állít meg if-ben — itt kell explicit kezelni
if ! mkdir -p "$TARGET_DIR/out"; then
  echo "Nem sikerült létrehozni: $TARGET_DIR/out" >&2
  exit 1
fi

# Buktató: a 'local var=$(cmd)' elnyeli a cmd hibakódját → külön sorba
read_version() {
  local version
  version=$(uname -r)        # itt a set -e már működik
  printf '%s\n' "$version"
}
read_version

# Hibás parancs tudatos tűrése és az exit kód megőrzése
status=0
false || status=$?
echo "A 'false' exit kódja: $status"
```

## Változók, idézés és paraméter-kifejtés
<!-- q: Hogyan idézzek helyesen és mit tud a paraméter-kifejtés bashben? -->
<!-- tags: quoting, variables, parameter expansion, word splitting, globbing, string manipulation -->

Idézőjel nélkül a változó értéke szófelbontáson (word splitting) és glob-kiterjesztésen megy át, ezért a szóközt vagy `*`-ot tartalmazó fájlnév szétesik — szabály: mindig `"$var"` és `"$@"`. A `'...'` semmit nem helyettesít, a `"..."` a változókat és a `$(...)` parancshelyettesítést igen. A paraméter-kifejtés külső programok (sed, cut, basename) nélkül végez gyakori műveleteket: alapérték (`${v:-x}`), kötelező érték (`${v:?hiba}`), előtag/utótag levágása (`#`, `##`, `%`, `%%`), csere (`${v//a/b}`), hossz (`${#v}`), részstring és kis/nagybetűsítés. A backtick helyett mindig `$(...)`-t használj, mert egymásba ágyazható.

```bash
#!/usr/bin/env bash
set -euo pipefail

path="/var/log/my app/access.log.2026-11-21.gz"

# Előtag/utótag levágása (# rövid, ## leghosszabb előtag; % rövid, %% leghosszabb utótag)
echo "${path##*/}"        # access.log.2026-11-21.gz   (basename)
echo "${path%/*}"         # /var/log/my app            (dirname)
echo "${path%%.*}"        # /var/log/my app/access     (első pont előtt)
echo "${path##*.}"        # gz                         (kiterjesztés)

# Csere, hossz, részstring
file="${path##*/}"
echo "${file//./_}"       # minden pont → aláhúzás
echo "${#file}"           # karakterszám
echo "${file:0:10}"       # első 10 karakter
date_part="${file#access.log.}"; date_part="${date_part%.gz}"
echo "Dátum: $date_part"

# Kis-/nagybetű (bash 4+)
env_name="Production"
echo "${env_name,,} ${env_name^^}"   # production PRODUCTION

# Alapértékek és kötelező változók
port="${PORT:-8080}"                  # ha üres/nincs: 8080
: "${HOME:?A HOME változó kötelező}"  # ha hiányzik: hibaüzenet és kilépés
echo "Port: $port"

# Idézés: a szóközös útvonal EGY argumentum marad
dir="$(mktemp -d)/my folder"
mkdir -p "$dir"                        # idézőjel nélkül két mappa jönne létre!
touch "$dir/a b.txt"
for f in "$dir"/*; do                  # a glob ne legyen idézőjelben, a változó igen
  printf 'Fájl: [%s]\n' "$f"
done

# "$@" vs "$*": az előbbi megőrzi az argumentumhatárokat
show_args() { printf '<%s> ' "$@"; echo; }
set -- "egy kettő" három
show_args "$@"        # <egy kettő> <három>
show_args "$*"        # <egy kettő három>

rm -r -- "${dir%/*}"   # csak a saját temp mappánkat töröljük
```

## Tömbök és asszociatív tömbök
<!-- q: Hogyan használjam a tömböket és az asszociatív tömböket bashben? -->
<!-- tags: arrays, associative arrays, declare -A, mapfile, readarray, iteration -->

A bash indexelt tömbje (`arr=(a b c)`) a szóközös elemeket is biztonságosan tárolja, ezért parancsok argumentumlistájának felépítésére is ez a helyes eszköz (stringbe fűzés helyett). Az asszociatív tömb (`declare -A`, bash 4+) kulcs-érték tár, például számlálásra vagy konfigurációra. Bejáráskor mindig `"${arr[@]}"` formát használj (idézőjellel), a kulcsokat `"${!map[@]}"` adja, az elemszámot `${#arr[@]}`. A `mapfile`/`readarray` fájlt vagy parancskimenetet olvas soronként tömbbe. Buktató: a macOS alapértelmezett bash 3.2-je nem ismeri az asszociatív tömböket.

```bash
#!/usr/bin/env bash
set -euo pipefail

# Indexelt tömb: parancs argumentumainak biztonságos felépítése
rsync_opts=(--archive --compress --human-readable)
dry_run=true
[[ $dry_run == true ]] && rsync_opts+=(--dry-run)          # feltételes bővítés
exclude_list=("node_modules" "*.tmp" "build output")      # szóközös elem is jó
for e in "${exclude_list[@]}"; do rsync_opts+=(--exclude "$e"); done
echo "rsync ${rsync_opts[*]} src/ dst/"                    # csak kiírjuk, nem futtatjuk

echo "Elemszám: ${#rsync_opts[@]}, utolsó: ${rsync_opts[-1]}"
echo "Szelet: ${rsync_opts[*]:0:2}"

# Asszociatív tömb: HTTP státuszkódok számlálása
declare -A status_count=()
log_lines=(
  '10.0.0.1 GET /index 200'
  '10.0.0.2 GET /api 500'
  '10.0.0.1 POST /api 200'
  '10.0.0.3 GET /missing 404'
)
for line in "${log_lines[@]}"; do
  code="${line##* }"                                       # utolsó mező
  status_count[$code]=$(( ${status_count[$code]:-0} + 1 ))
done

# Kulcsok rendezett bejárása
for code in $(printf '%s\n' "${!status_count[@]}" | sort); do
  printf '%s: %d\n' "$code" "${status_count[$code]}"
done

# Kulcs létezésének ellenőrzése
if [[ -v status_count[500] ]]; then echo "Volt szerverhiba!"; fi

# mapfile: parancs kimenete soronként tömbbe (-t: a sorvégjel nélkül)
mapfile -t users < <(cut -d: -f1 /etc/passwd | head -n 5)
echo "Első ${#users[@]} felhasználó: ${users[*]}"

# Elem törlése és "lyukas" indexek
unset 'users[1]'
echo "Indexek törlés után: ${!users[*]}"
```

## Feltételek: [[ ]], (( )) és case
<!-- q: Mi a különbség a [ ] és a [[ ]] között bashben, és hogyan írjak feltételeket? -->
<!-- tags: conditionals, test, double brackets, arithmetic, case, regex, file tests -->

A `[[ ]]` a bash beépített feltételkifejezése: benne nincs szófelbontás és glob-kiterjesztés, támogatja a `&&`/`||` operátorokat, a mintaillesztést (`==` glob mintával) és a reguláris kifejezést (`=~`, a csoportok a `BASH_REMATCH` tömbben). A régi `[ ]` (= `test`) POSIX-kompatibilis, de ott kötelező az idézés. Számokhoz a `(( ))` aritmetikai kontextus való (`<`, `>=`, `++`), mert a `[[ ]]`-ben a `<` szöveges összehasonlítás! A `case` több mintára ágazik el olvashatóan. Fájltesztek: `-f` (fájl), `-d` (mappa), `-r`/`-w`/`-x` (jogok), `-s` (nem üres), `-nt` (újabb, mint).

```bash
#!/usr/bin/env bash
set -euo pipefail

version="v2.14.3"
# Regex illesztés: a mintát változóban tartsd (idézés nélkül a =~ jobb oldalán)
re='^v([0-9]+)\.([0-9]+)\.([0-9]+)$'
if [[ $version =~ $re ]]; then
  major=${BASH_REMATCH[1]} minor=${BASH_REMATCH[2]} patch=${BASH_REMATCH[3]}
  echo "Fő: $major, al: $minor, javítás: $patch"
fi

# Aritmetika: (( )) — a [[ 10 < 9 ]] szövegesen IGAZ lenne!
if (( minor >= 10 && major > 1 )); then echo "Elég új verzió"; fi
(( patch++ )) || true            # a (( 0 )) exit kódja 1 → set -e miatt || true
echo "Következő javítás: $major.$minor.$patch"

# Glob mintaillesztés [[ ]]-ben (jobb oldal idézőjel nélkül = minta)
file="report-2026.csv"
[[ $file == report-*.csv ]] && echo "Riportfájl"

# Fájltesztek
tmp=$(mktemp)
echo "adat" > "$tmp"
if [[ -f $tmp && -s $tmp && -r $tmp ]]; then echo "Létező, nem üres, olvasható fájl"; fi
[[ -d /etc ]] && echo "/etc mappa"
[[ -z ${UNSET_VAR:-} ]] && echo "Üres vagy nincs beállítva"

# case: több minta ágakkal
classify() {
  case "${1,,}" in                       # kisbetűsítve
    *.tar.gz|*.tgz)  echo "tar+gzip archívum" ;;
    *.zip)           echo "zip archívum" ;;
    *.jp?g|*.png)    echo "kép" ;;
    "")              echo "üres név" ;;
    *)               echo "ismeretlen típus" ;;
  esac
}
for f in backup.TGZ photo.jpeg notes.txt; do
  printf '%-12s → %s\n' "$f" "$(classify "$f")"
done

rm -f -- "$tmp"
```

## Függvények, local és visszatérési értékek
<!-- q: Hogyan írjak függvényeket bashben és hogyan adjak vissza értéket? -->
<!-- tags: functions, local, return, exit code, nameref, stdout, error handling -->

Bash-függvény nem ad vissza „értéket” a megszokott értelemben: a `return` csak 0–255 közötti exit kódot (siker/hiba) jelez, az adatot a stdout-ra írja, amit a hívó `$(...)`-vel kap meg. A függvényen belüli változókat mindig `local`-lal deklaráld, különben globálisak lesznek és felülírnak dolgokat. A hibaüzenetek a stderr-re (`>&2`) menjenek, hogy ne keveredjenek az adattal. Több érték vagy tömb visszaadására a nameref (`local -n`, bash 4.3+) való. Buktató: a `$(...)` subshellben fut, így ott a globális változók módosítása elvész.

```bash
#!/usr/bin/env bash
set -euo pipefail

log()  { printf '[%(%H:%M:%S)T] %s\n' -1 "$*" >&2; }   # stderr-re, időbélyeggel
die()  { log "HIBA: $*"; exit 1; }

# Adat a stdout-on, állapot az exit kódban
parse_kv() {
  local line=$1 key value
  [[ $line == *=* ]] || return 1                    # nem kulcs=érték sor → hiba
  key=${line%%=*}
  value=${line#*=}
  printf '%s\t%s\n' "${key//[[:space:]]/}" "$value"
}

# Nameref: a hívó tömbjét tölti fel (nincs subshell, nincs szövegparse-olás)
load_config() {
  local file=$1
  local -n _cfg=$2                                   # referencia a hívó asszociatív tömbjére
  local line k v kv
  while IFS= read -r line || [[ -n $line ]]; do
    [[ -z $line || $line == \#* ]] && continue      # üres sor és komment kihagyása
    if kv=$(parse_kv "$line"); then
      IFS=$'\t' read -r k v <<< "$kv"
      _cfg[$k]=$v
    else
      log "Kihagyott sor: $line"
    fi
  done < "$file"
}

# Visszatérési kód felhasználása feltételben
is_port_valid() {
  local p=$1
  [[ $p =~ ^[0-9]+$ ]] && (( p > 0 && p < 65536 ))
}

cfg_file=$(mktemp)
trap 'rm -f -- "$cfg_file"' EXIT
cat > "$cfg_file" <<'EOF'
# demó konfiguráció
host = localhost
port=8080
hibás sor
name=Teszt Szerver
EOF

declare -A config=()
load_config "$cfg_file" config
is_port_valid "${config[port]:-}" || die "Érvénytelen port: ${config[port]:-nincs}"
for k in "${!config[@]}"; do printf '%s => %s\n' "$k" "${config[$k]}"; done
```

## trap, ideiglenes fájlok és takarítás
<!-- q: Hogyan takarítsak el automatikusan ideiglenes fájlokat és kezeljem a jeleket bash szkriptben? -->
<!-- tags: trap, mktemp, cleanup, signals, exit, err, sigint, sigterm -->

A `trap` parancs jelekre és pszeudo-eseményekre köt kezelőt: az `EXIT` mindig lefut kilépéskor (normál vége, `exit`, `set -e` miatti leállás), így ide való a takarítás; az `ERR` hibás parancsnál fut (a sorszámmal hasznos hibaüzenetet adhatsz), az `INT`/`TERM` pedig Ctrl+C-re és leállítási kérésre. Ideiglenes fájlt és mappát mindig `mktemp`-pel hozz létre (egyedi név, biztonságos jogok), soha ne fix `/tmp/valami` névvel (versenyhelyzet, symlink-támadás). Buktató: a `trap` felülírja az ugyanarra a jelre korábban beállított kezelőt, és a `SIGKILL` nem kapható el.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

# Egyedi ideiglenes munkamappa
WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/pbdemo.XXXXXX")
LOCK_HELD=false

cleanup() {
  local rc=$?                                  # az eredeti exit kód megőrzése
  trap - EXIT INT TERM                         # ne fusson kétszer
  [[ $LOCK_HELD == true ]] && echo "Zár feloldva" >&2
  rm -rf -- "$WORKDIR"                         # csak a saját mappánk
  echo "Takarítás kész (exit kód: $rc)" >&2
  exit "$rc"
}

on_error() {
  local rc=$? line=$1 cmd=$2
  echo "HIBA a(z) $line. sorban: '$cmd' (exit $rc)" >&2
}

on_interrupt() {
  echo "Megszakítva (jel érkezett)" >&2
  exit 130                                     # konvenció: 128 + SIGINT(2)
}

trap cleanup EXIT
trap 'on_error "$LINENO" "$BASH_COMMAND"' ERR
trap on_interrupt INT TERM

# --- Munka ---
LOCK_HELD=true
for i in 1 2 3; do
  printf 'adat %d\n' "$i" > "$WORKDIR/part_$i.txt"
done
cat "$WORKDIR"/part_*.txt > "$WORKDIR/merged.txt"
echo "Összefűzve: $(wc -l < "$WORKDIR/merged.txt") sor"

# Szimulált hiba: az ERR trap kiírja a sort, majd az EXIT trap takarít
if [[ ${SIMULATE_ERROR:-0} == 1 ]]; then
  ls /nem/letezo/utvonal
fi

echo "Sikeres befejezés"
```

## Argumentumok feldolgozása getopts-szal
<!-- q: Hogyan dolgozzam fel a parancssori kapcsolókat bash szkriptben getopts-szal? -->
<!-- tags: getopts, command line arguments, options, usage, flags, cli -->

A beépített `getopts` a POSIX-stílusú rövid kapcsolókat (`-v`, `-o fájl`, összevonva `-vn`) dolgozza fel: az opciós string betűi a kapcsolók, a `:` utáni betű argumentumot vár, a vezető `:` csendes módot ad, ahol a hibákat (`?` ismeretlen kapcsoló, `:` hiányzó argumentum) magad kezeled. A feldolgozás után a `shift $((OPTIND - 1))` eltávolítja a kapcsolókat, és a maradék a pozicionális argumentum. Hosszú kapcsolókat (`--output`) a getopts nem ismer — ehhez kézi `while/case` ciklus vagy a GNU `getopt` kell. Mindig legyen `usage` függvény és `-h` kapcsoló, és a módosító szkriptek kapjanak `-n` (dry-run) opciót.

```bash
#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Használat: ${0##*/} [-n] [-v] [-d NAPOK] [-o KIMENET] MAPPA...
  -n         dry-run: csak kiírja, mit tenne (alapértelmezett!)
  -x         valódi végrehajtás (tömörítés)
  -v         részletes kimenet (többször is: -vv)
  -d NAPOK   ennél régebbi fájlok (alap: 7)
  -o FÁJL    eredménylista fájlba
  -h         súgó
EOF
}

dry_run=true verbose=0 days=7 output=""

while getopts ':nxvd:o:h' opt; do
  case $opt in
    n) dry_run=true ;;
    x) dry_run=false ;;
    v) (( ++verbose )) ;;
    d) [[ $OPTARG =~ ^[0-9]+$ ]] || { echo "A -d szám legyen: $OPTARG" >&2; exit 2; }
       days=$OPTARG ;;
    o) output=$OPTARG ;;
    h) usage; exit 0 ;;
    :) echo "A -$OPTARG kapcsolónak argumentum kell" >&2; usage >&2; exit 2 ;;
    \?) echo "Ismeretlen kapcsoló: -$OPTARG" >&2; usage >&2; exit 2 ;;
  esac
done
shift $((OPTIND - 1))                     # a maradék: pozicionális argumentumok

(( $# > 0 )) || { echo "Legalább egy MAPPA kell" >&2; usage >&2; exit 2; }
(( verbose > 0 )) && echo "dry_run=$dry_run days=$days output=${output:-stdout} mappák: $*" >&2

for dir in "$@"; do
  [[ -d $dir ]] || { echo "Nem mappa, kihagyom: $dir" >&2; continue; }
  while IFS= read -r -d '' f; do
    if [[ $dry_run == true ]]; then
      echo "[DRY-RUN] gzip -- $f"
    else
      gzip -- "$f"
    fi
  done < <(find "$dir" -type f -name '*.log' -mtime +"$days" -print0)
done | if [[ -n $output ]]; then tee -- "$output"; else cat; fi
```

## Szövegfeldolgozás: grep, sed, awk pipeline-ok
<!-- q: Hogyan elemezzek logfájlokat grep, sed és awk kombinálásával? -->
<!-- tags: grep, sed, awk, pipeline, text processing, log analysis, sort, uniq -->

A Unix-filozófia szerint kis eszközöket fűzünk össze: a `grep` sorokat szűr (mintával, `-E` bővített regex, `-v` tagadás, `-o` csak a találat), a `sed` soronként átalakít (csere, törlés, kivágás), az `awk` mezőkre bont és számol (összegzés, csoportosítás asszociatív tömbbel), a `sort | uniq -c | sort -rn` pedig gyakorisági toplistát ad. Az `awk` önmagában gyakran kiváltja a `grep | cut | sort` láncot, és egyetlen folyamat, ezért gyorsabb. Buktatók: a `sed -i` GNU és BSD (macOS) alatt eltérő szintaxisú, a locale lassíthatja a grepet (`LC_ALL=C`), és a `cat fájl | grep` felesleges folyamat.

```bash
#!/usr/bin/env bash
set -euo pipefail

# Demó access log (Combined Log Format-szerű) egy temp fájlba
log=$(mktemp)
trap 'rm -f -- "$log"' EXIT
cat > "$log" <<'EOF'
10.0.0.1 - - [21/Nov/2026:10:00:01 +0100] "GET /index.html HTTP/1.1" 200 5120 0.012
10.0.0.2 - - [21/Nov/2026:10:00:02 +0100] "GET /api/users HTTP/1.1" 500 312 1.204
10.0.0.1 - - [21/Nov/2026:10:01:13 +0100] "POST /api/login HTTP/1.1" 200 89 0.340
10.0.0.3 - - [21/Nov/2026:10:02:44 +0100] "GET /api/users HTTP/1.1" 200 2048 0.090
10.0.0.2 - - [21/Nov/2026:11:15:09 +0100] "GET /missing HTTP/1.1" 404 0 0.003
10.0.0.4 - - [21/Nov/2026:11:20:31 +0100] "GET /api/users HTTP/1.1" 502 120 2.511
EOF

echo "== Top IP-k (grep + sort + uniq) =="
grep -oE '^[0-9.]+' "$log" | sort | uniq -c | sort -rn | head -n 3

echo "== 5xx hibák endpointonként (awk mezőkkel) =="
# $9 = státusz, $7 = útvonal (a szóközök szerinti mezőbontás alapján)
awk '$9 >= 500 { errors[$7]++ } END { for (p in errors) printf "%-12s %d\n", p, errors[p] }' "$log"

echo "== Átlagos és maximális válaszidő útvonalanként =="
awk '{
  t = $NF; sum[$7] += t; cnt[$7]++
  if (t > max[$7]) max[$7] = t
} END {
  for (p in sum) printf "%-12s átlag=%.3fs max=%.3fs n=%d\n", p, sum[p]/cnt[p], max[p], cnt[p]
}' "$log" | sort -k2 -t= -rn

echo "== Óránkénti kérésszám (sed kivágás + uniq) =="
# A [21/Nov/2026:10:00:01 ...] részből az órát vágjuk ki
sed -E 's/.*\[[^:]+:([0-9]{2}):.*/\1/' "$log" | sort | uniq -c

echo "== Anonimizált log (utolsó IP-oktett maszkolása) =="
sed -E 's/^([0-9]+\.[0-9]+\.[0-9]+)\.[0-9]+/\1.xxx/' "$log" | head -n 2

echo "== Lassú (>1s) kérések, csak a szükséges mezők =="
awk '$NF > 1 { gsub(/"/, "", $6); print $4, $6, $7, $9, $NF "s" }' "$log" | sed 's/\[//'
```

## Fájlok biztonságos bejárása: read -r, find -print0
<!-- q: Hogyan olvassak fájlt soronként és járjak be fájlneveket biztonságosan bashben? -->
<!-- tags: while read, ifs, read -r, find, print0, null delimiter, filenames, globbing -->

Fájl soronkénti olvasására a `while IFS= read -r line` a helyes forma: az `IFS=` megtartja a sor eleji/végi szóközöket, a `-r` nem értelmezi a backslasht, a `|| [[ -n $line ]]` pedig az újsor nélküli utolsó sort is beolvassa. A `for f in $(ls)` és a `for line in $(cat f)` hibás, mert szóközöknél szétesik. Fájlneveket a `find ... -print0` és a `read -d ''` NUL-elválasztóval kezelj, mert a fájlnévben szóköz, sőt újsor is lehet. Ha a ciklus `cmd | while` formájú, az subshellben fut, és a benne módosított változók elvesznek — ilyenkor `while ...; done < <(cmd)` kell.

```bash
#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob                 # nem illeszkedő glob → üres lista, nem a minta szövege

demo=$(mktemp -d)
trap 'rm -rf -- "$demo"' EXIT

# "Gonosz" fájlnevek: szóköz, kötőjeles kezdés, újsor
touch "$demo/normal.txt" "$demo/szóközös név.txt" "$demo/-kotojel.txt" "$demo/uj"$'\n'"sor.txt"
printf 'első sor\n  behúzott sor\nutolsó sor újsor nélkül' > "$demo/normal.txt"

echo "== Soronkénti olvasás, szóközök megtartásával =="
n=0
while IFS= read -r line || [[ -n $line ]]; do
  (( ++n ))
  printf '%2d: [%s]\n' "$n" "$line"
done < "$demo/normal.txt"
echo "Sorok: $n"                  # a változó megmaradt (nincs subshell)

echo "== Glob bejárás: biztonságos =="
for f in "$demo"/*.txt; do
  printf '[%s]\n' "${f##*/}"
done

echo "== find -print0 + read -d '': újsoros névre is jó =="
count=0
while IFS= read -r -d '' f; do
  (( ++count ))
  # a '--' megvédi a kötőjellel kezdődő nevet attól, hogy kapcsolónak tűnjön
  size=$(wc -c < "$f")
  printf '%q (%d bájt)\n' "${f##*/}" "$size"     # %q: látható escape-elés
done < <(find "$demo" -type f -name '*.txt' -print0)
echo "Talált: $count"

echo "== HIBÁS minta (ne használd): for f in \$(ls) =="
# for f in $(ls "$demo"); do ...  → a "szóközös név.txt" két elemre esne szét

echo "== CSV mezők olvasása =="
printf 'név;kor;város\nAnna;34;Pécs\nBéla;29;Győr\n' > "$demo/people.csv"
{
  read -r _header                                 # fejléc átugrása
  while IFS=';' read -r name age city; do
    (( age > 30 )) && echo "$name ($age) — $city"
  done
} < "$demo/people.csv"
```

## Process substitution, here-doc és here-string
<!-- q: Mire jó a process substitution, a here-doc és a here-string bashben? -->
<!-- tags: process substitution, here document, here string, diff, tee, subshell, redirection -->

A process substitution (`<(cmd)` és `>(cmd)`) egy parancs kimenetét vagy bemenetét fájlként (`/dev/fd/N`) adja át, így két parancs kimenete közvetlenül összehasonlítható (`diff <(...) <(...)`), egy kimenet több feldolgozóhoz ágaztatható (`tee >(...)`), és a `while` ciklus subshell nélkül olvashat parancskimenetet. A here-doc (`<<EOF`) többsoros bemenetet ad (az `<<'EOF'` nem helyettesít változót, a `<<-EOF` levágja a vezető tabokat), a here-string (`<<<`) egyetlen stringet ad a parancs stdin-jére. Buktató: ezek bash-specifikusak, POSIX `sh`-ban nem működnek, és a `>(...)` folyamat aszinkron fut, ezért a kimenete később érkezhet.

```bash
#!/usr/bin/env bash
set -euo pipefail

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

# Két "környezet" konfigurációja
printf 'DB_HOST=db1\nDB_PORT=5432\nCACHE=on\nLOG=info\n' > "$work/staging.env"
printf 'DB_PORT=5432\nDB_HOST=db-prod\nLOG=warn\nCACHE=on\n' > "$work/prod.env"

echo "== Rendezett összehasonlítás ideiglenes fájlok nélkül =="
diff <(sort "$work/staging.env") <(sort "$work/prod.env") || true   # diff exit 1 = eltérés

echo "== Csak az egyikben lévő kulcsok (comm) =="
comm -3 <(cut -d= -f1 "$work/staging.env" | sort) <(cut -d= -f1 "$work/prod.env" | sort)

echo "== Kimenet elágaztatása: tee + >(...) =="
seq 1 10 | tee >(awk '{ s += $1 } END { print "összeg:", s }' > "$work/sum.txt") \
              >(grep -c . > "$work/count.txt") > /dev/null
wait                                  # bash 5.1+: megvárja a >(...) folyamatokat is
echo "$(cat "$work/sum.txt"), darab: $(cat "$work/count.txt")"

echo "== Here-doc változó-helyettesítéssel =="
app="pbdemo" port=8080
cat > "$work/nginx.conf" <<EOF
server {
    listen ${port};
    server_name ${app}.local;
    location / { proxy_pass http://127.0.0.1:$((port + 1)); }
}
EOF
cat "$work/nginx.conf"

echo "== Here-doc helyettesítés NÉLKÜL (szó szerinti szkript) =="
cat > "$work/remote.sh" <<'EOF'
#!/bin/sh
echo "Ez a $HOME a célgépen értékelődik ki"
EOF
head -n 2 "$work/remote.sh"

echo "== Here-string: string a stdin-re =="
read -r major minor patch <<< "$(tr '.' ' ' <<< "3.12.1")"
echo "major=$major minor=$minor patch=$patch"
bc_result=$(bc <<< "scale=2; 10 / 3" 2>/dev/null || echo "bc nincs telepítve")
echo "10/3 = $bc_result"
```

## Párhuzamos feldolgozás: xargs és GNU parallel
<!-- q: Hogyan futtassak parancsokat párhuzamosan xargs-szal vagy GNU parallel-lel? -->
<!-- tags: xargs, parallel, gnu parallel, concurrency, batch processing, -P, null delimiter -->

Az `xargs` a stdin elemeiből parancssort épít: `-0` NUL-elválasztót vár (`find -print0` párja), `-n` elemszámot ad hívásonként, `-P N` pedig N párhuzamos folyamatot futtat, így a CPU- vagy I/O-igényes kötegelt munka egyszerűen gyorsítható. A GNU `parallel` ennél kényelmesebb: rendezett kimenet (`--keep-order`), haladásjelzés, joblog, újrapróbálás, távoli gépek. Buktatók: a párhuzamos folyamatok kimenete összekeveredhet, közös fájlba írni versenyhelyzetes, és `-P 0` korlátlan párhuzamosságot jelent, ami túlterhelheti a gépet. Bash függvényt `export -f`-fel tehetsz elérhetővé a gyerekfolyamatoknak.

```bash
#!/usr/bin/env bash
set -euo pipefail

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

# Demó adat: 20 fájl, némelyik szóközös névvel
for i in $(seq 1 20); do
  head -c $(( RANDOM % 5000 + 100 )) /dev/urandom > "$work/file $i.bin"
done

jobs_n=$(nproc 2>/dev/null || echo 4)

echo "== xargs: párhuzamos checksum, NUL-elválasztással =="
find "$work" -name '*.bin' -print0 \
  | xargs -0 -n 4 -P "$jobs_n" sha256sum \
  | sort -k2 | head -n 3

echo "== Bash függvény xargs-szal (export -f) =="
process_file() {
  local f=$1
  local size
  size=$(wc -c < "$f")
  # Szimulált munka; az eredményt a stdoutra írjuk (nem közös fájlba!)
  printf '%s\t%d\n' "${f##*/}" "$size"
}
export -f process_file
find "$work" -name '*.bin' -print0 \
  | xargs -0 -I{} -P "$jobs_n" bash -c 'process_file "$1"' _ {} \
  | sort -t$'\t' -k2 -n | tail -n 3

echo "== Dry-run minta: a parancsot csak kiírjuk =="
find "$work" -name 'file 1*.bin' -print0 | xargs -0 -n 1 echo "gzip --"

echo "== GNU parallel (ha telepítve van) =="
if command -v parallel > /dev/null; then
  # --keep-order: a kimenet a bemenet sorrendjében; --joblog: futási napló
  find "$work" -name '*.bin' -print0 \
    | parallel -0 --keep-order --jobs "$jobs_n" --joblog "$work/jobs.log" \
        'printf "%s %s\n" {/} $(wc -c < {})' | head -n 3
  echo "Sikertelen jobok: $(awk 'NR > 1 && $7 != 0' "$work/jobs.log" | wc -l)"
else
  echo "A GNU parallel nincs telepítve (apt install parallel)"
fi
```

## Háttérfolyamatok, wait és timeout
<!-- q: Hogyan futtassak és várjak meg háttérfolyamatokat bashben, időkorláttal? -->
<!-- tags: background jobs, wait, pid, timeout, job control, concurrency, semaphore -->

A `cmd &` háttérbe indítja a parancsot, a `$!` a PID-jét adja, a `wait PID` megvárja és visszaadja az exit kódját — így több független feladat párhuzamosan futtatható, majd egyenként ellenőrizhető. A `wait -n` (bash 4.3+) az első befejeződőre vár, amivel egyszerű „szemafor” (legfeljebb N egyszerre) építhető. A `timeout` parancs időkorlátot ad (124-es exit kód lejáratkor), a `kill` jelet küld. Buktatók: a háttérfolyamat hibája a `set -e`-t nem váltja ki (csak a `wait` exit kódjában látszik), a szkript kilépésekor az árva gyerekeket érdemes `trap`-pel leállítani, és a kimenetük összekeveredhet.

```bash
#!/usr/bin/env bash
set -euo pipefail

# Kilépéskor a még futó gyerekfolyamatok leállítása
trap 'jobs -pr | xargs -r kill 2>/dev/null || true' EXIT

fake_task() {                     # szimulált munka véletlen időtartammal és eredménnyel
  local name=$1 secs=$2 rc=$3
  sleep "$secs"
  echo "  $name kész (${secs}s)"
  return "$rc"
}

echo "== Párhuzamos indítás, egyenkénti ellenőrzés =="
declare -A pids=()
fake_task "backup" 1 0 & pids[backup]=$!
fake_task "report" 2 0 & pids[report]=$!
fake_task "sync"   1 3 & pids[sync]=$!    # ez hibával tér vissza

failed=0
for name in "${!pids[@]}"; do
  if wait "${pids[$name]}"; then
    echo "OK: $name"
  else
    rc=$?
    echo "HIBA: $name (exit $rc)" >&2
    (( ++failed ))
  fi
done
echo "Hibás feladatok: $failed"

echo "== Korlátozott párhuzamosság wait -n-nel (max 3 egyszerre) =="
max_jobs=3
for i in $(seq 1 7); do
  while (( $(jobs -pr | wc -l) >= max_jobs )); do
    wait -n || true               # bármelyik befejeződésére vár
  done
  fake_task "job$i" "$(( RANDOM % 2 + 1 ))" 0 &
done
wait                              # a maradék megvárása
echo "Minden job kész"

echo "== Időkorlát timeout-tal =="
if timeout 2 sleep 5; then
  echo "Időben végzett"
else
  rc=$?
  (( rc == 124 )) && echo "Időtúllépés (exit 124)" || echo "Más hiba: $rc"
fi

# Kíméletes leállítás: előbb TERM, türelmi idő után KILL
timeout --kill-after=3 10 sleep 1 && echo "Rendben lefutott"
```

## Átirányítás, fájlleírók és naplózás
<!-- q: Hogyan irányítsam át a kimenetet és naplózzak egy bash szkriptből fájlba és képernyőre egyszerre? -->
<!-- tags: redirection, file descriptors, exec, tee, stderr, logging, /dev/null -->

Minden folyamatnak három alap fájlleírója van: 0 (stdin), 1 (stdout), 2 (stderr); a `>` felülír, a `>>` hozzáfűz, a `2>&1` a stderr-t a stdout aktuális céljába irányítja (a sorrend számít: `> f 2>&1` jó, `2>&1 > f` nem azt teszi). Az `exec` parancs átirányítással a szkript hátralévő részére állít be kimenetet, így egyszerre fájlba és képernyőre naplózhatsz (`exec > >(tee -a log) 2>&1`), vagy saját fájlleírót nyithatsz (`exec 3>file`). Az adat a stdoutra, a diagnosztika a stderr-re menjen, hogy a szkript pipeline-ban is használható legyen. A `&>` (bash) mindkét kimenetet irányítja, POSIX-ban `> f 2>&1` kell.

```bash
#!/usr/bin/env bash
set -euo pipefail

LOG_DIR=$(mktemp -d)
LOG_FILE="$LOG_DIR/run_$(date +%Y%m%d_%H%M%S).log"
trap 'echo "Napló: $LOG_FILE (a mappa a demó után törölhető)" >&3' EXIT

# Az eredeti stdout mentése a 3-as leíróra (a képernyőre íráshoz később)
exec 3>&1
# Innentől MINDEN kimenet (stdout + stderr) a képernyőre ÉS a naplófájlba megy
exec > >(tee -a "$LOG_FILE") 2>&1

log() {
  local level=$1; shift
  printf '%s [%-5s] %s\n' "$(date '+%F %T')" "$level" "$*" >&2   # diagnosztika: stderr
}

log INFO "Szkript indult, PID: $$"

# Adat a stdoutra, diagnosztika a stderr-re — külön szűrhetők
generate_data() {
  log DEBUG "Adatgenerálás..."
  printf '%s\n' alma körte szilva
}
generate_data | sort

# Egy parancs zajos kimenetének eldobása, csak az exit kód számít
if grep -q root /etc/passwd 2>/dev/null; then log INFO "root felhasználó létezik"; fi

# Saját fájlleíró: CSV eredményfájl nyitva tartása a ciklus alatt (gyorsabb, mint >> minden sorban)
exec 4> "$LOG_DIR/results.csv"
echo "id,négyzet" >&4
for i in 1 2 3; do echo "$i,$(( i * i ))" >&4; done
exec 4>&-                         # leíró lezárása
log INFO "Eredmény: $(wc -l < "$LOG_DIR/results.csv") sor"

# Csak a stderr-t irányítjuk át egy parancsnál (stdout marad)
ls /etc/hostname /nem/letezik 2> "$LOG_DIR/errors.txt" || log WARN "ls hiba: $(cat "$LOG_DIR/errors.txt")"

# Közvetlenül a képernyőre (a naplót megkerülve) a mentett 3-as leírón át
echo "Ez csak a képernyőn jelenik meg" >&3

log INFO "Kész"
```

## POSIX sh és a bash különbségei
<!-- q: Mi a különbség a POSIX sh és a bash között, és hogyan írjak hordozható shell szkriptet? -->
<!-- tags: posix, sh, dash, bashisms, portability, shellcheck, busybox, alpine -->

Sok rendszeren a `/bin/sh` nem bash: Debian/Ubuntun `dash`, Alpine/BusyBox konténerekben `ash`, ezért egy `#!/bin/sh` shebanges szkriptben a bash-specifikus elemek („bashism”) hibát okoznak. POSIX-ban nincs `[[ ]]` (helyette `[ ]` és kötelező idézés), nincsenek tömbök (helyette `set --` és `"$@"`), nincs `local` (bár a legtöbb sh ismeri), `function` kulcsszó, `$'...'`, `<<<`, `<(...)`, `{1..10}`, `==` a `test`-ben, `pipefail` (csak újabb dash/POSIX 2024), `&>` és `${var,,}`. Ha bash-funkció kell, írj `#!/usr/bin/env bash`-t; ha hordozhatóság kell (konténer, init szkript), tesztelj `dash`-sel, és futtasd a `shellcheck -s sh` ellenőrzést.

```bash
#!/bin/sh
# POSIX-kompatibilis szkript: dash, ash (BusyBox) és bash alatt is fut.
# A bash megfelelőket a kommentek mutatják.
set -eu                                   # pipefail POSIX-ban nem mindenhol érhető el

# [[ $a == b* ]]  →  case mintaillesztés
is_backup() {
  case $1 in
    *.bak|*.backup) return 0 ;;
    *) return 1 ;;
  esac
}

# Tömb helyett a pozicionális paraméterek: set -- és "$@"
set -- "első elem" "második elem" "harmadik"
echo "Elemszám: $#"
for item in "$@"; do printf '  [%s]\n' "$item"; done

# {1..5}  →  while ciklus aritmetikával ($(( )) POSIX!)
i=1
while [ "$i" -le 5 ]; do
  printf '%s ' "$i"
  i=$((i + 1))
done
echo

# ${var,,}  →  tr
name="ProDuction"
lower=$(printf '%s' "$name" | tr '[:upper:]' '[:lower:]')
echo "Kisbetűs: $lower"

# [ ] idézéssel: üres változónál is helyes; == helyett =
mode=""
if [ -z "$mode" ] || [ "$mode" = "auto" ]; then echo "Automatikus mód"; fi

# <<< here-string  →  here-doc vagy printf | ...
read -r major minor <<EOF
$(echo "3.12" | tr '.' ' ')
EOF
echo "major=$major minor=$minor"

# <(...) process substitution  →  ideiglenes fájl (mktemp nem POSIX, de szinte mindenhol van)
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT INT TERM
printf 'b\na\nc\n' > "$tmp"
sort "$tmp" | head -n 1

# echo -e helyett printf (az echo viselkedése shellenként eltér)
printf 'Tab:\t|  Újsor után:\n  vége\n'

# Parancs létezésének ellenőrzése: command -v (a 'which' nem szabványos)
if command -v is_backup >/dev/null 2>&1 && is_backup "adat.bak"; then
  echo "adat.bak egy mentés"
fi
```

## systemd unit szkripthez
<!-- q: Hogyan futtassak egy bash szkriptet szolgáltatásként vagy időzítve systemd-vel? -->
<!-- tags: systemd, service unit, timer, journalctl, daemon, linux, hardening -->

A systemd a modern Linux init rendszere: egy `.service` unit leírja, hogyan induljon, ki nevében fusson, mikor induljon újra a folyamat, a `.timer` unit pedig cron helyett ütemez (pontosabb naplózással, kihagyott futás pótlásával — `Persistent=true`). A szkript kimenete automatikusan a journalba kerül (`journalctl -u név`), ezért nem kell saját logfájl. Biztonsági okból ne rootként fusson: `DynamicUser`, `ProtectSystem=strict`, `PrivateTmp`, `NoNewPrivileges` korlátozza, mit érhet el. A `Type=oneshot` egyszer lefutó feladatokra, a `Type=simple`/`exec` hosszan futó démonokra való; módosítás után `systemctl daemon-reload` kell.

```ini
# /etc/systemd/system/pb-backup.service
[Unit]
Description=Napi adatmentés (demó)
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/pb-backup.sh --dry-run
# Ne rootként: ideiglenes, dinamikus felhasználó
DynamicUser=yes
StateDirectory=pb-backup
# Hardening: csak olvasható rendszer, saját /tmp, nincs jogosultság-emelés
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=yes
NoNewPrivileges=yes
# Erőforráskorlátok
Nice=10
IOSchedulingClass=idle
TimeoutStartSec=30min

# /etc/systemd/system/pb-backup.timer
[Unit]
Description=pb-backup naponta 02:30-kor

[Timer]
OnCalendar=*-*-* 02:30:00
RandomizedDelaySec=15min
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
#!/usr/bin/env bash
# Telepítő segéd — alapból CSAK kiírja a parancsokat; valódi futtatás: APPLY=1 sudo ./install.sh
set -euo pipefail

run() {
  if [[ ${APPLY:-0} == 1 ]]; then "$@"; else printf '[DRY-RUN] %q ' "$@"; echo; fi
}

unit=pb-backup
run install -m 0755 ./pb-backup.sh /usr/local/bin/pb-backup.sh
run install -m 0644 "./$unit.service" "./$unit.timer" /etc/systemd/system/
run systemctl daemon-reload                       # unit fájlok újraolvasása
run systemd-analyze verify "/etc/systemd/system/$unit.service"
run systemctl enable --now "$unit.timer"          # a TIMER-t engedélyezzük, nem a service-t

# Ellenőrzés és naplók (csak olvasás):
echo "systemctl list-timers $unit.timer"
echo "systemctl status $unit.service"
echo "journalctl -u $unit.service --since today --no-pager"
echo "systemctl start $unit.service   # kézi, azonnali futtatás teszteléshez"
```

## Cron-jobok és flock
<!-- q: Hogyan ütemezzek bash szkriptet cronnal úgy, hogy ne fusson két példány egyszerre? -->
<!-- tags: cron, crontab, flock, scheduling, locking, environment, logging -->

A cron a klasszikus ütemező: a `crontab -e` sorai „perc óra nap hónap hét-napja parancs” formájúak, az aktuális lista a `crontab -l`. A cron minimális környezettel fut (szűk `PATH`, nincs `.bashrc`, más munkakönyvtár), ezért a szkriptben abszolút útvonalakat használj, és állítsd be a `PATH`-t; a kimenetet irányítsd naplófájlba, különben e-mailben vész el. Ha a futás tovább tarthat az ütemezési intervallumnál, a `flock` zárolással akadályozd meg az átfedést. Buktató: a crontabban a `%` speciális karakter (újsort jelent), ezért `\%`-ként kell írni, a hét napja 0 és 7 is vasárnap.

```bash
#!/usr/bin/env bash
# /usr/local/bin/pb-report.sh — cronból futtatható, átfedés elleni védelemmel
#
# Crontab bejegyzések (crontab -e):
#   PATH=/usr/local/bin:/usr/bin:/bin
#   MAILTO=""
#   # Hétköznap 15 percenként, 8 és 18 óra között:
#   */15 8-18 * * 1-5  /usr/local/bin/pb-report.sh >> "$HOME/pb-report.log" 2>&1
#   # Minden hónap 1-jén 03:00-kor (a % jelet escape-elni kell):
#   0 3 1 * *  /usr/local/bin/pb-report.sh --monthly >> "$HOME/pb-$(date +\%Y\%m).log" 2>&1
set -euo pipefail
export PATH=/usr/local/bin:/usr/bin:/bin       # cron alatt szűk a PATH
export LC_ALL=C.UTF-8

readonly LOCK_FILE="${XDG_RUNTIME_DIR:-/tmp}/pb-report.lock"
readonly OUT_DIR="${HOME}/pb-reports"
mode="${1:---daily}"

# flock: a 9-es leírón zárolunk; ha más példány fut, azonnal kilépünk (-n)
exec 9> "$LOCK_FILE"
if ! flock -n 9; then
  echo "$(date '+%F %T') Már fut egy példány, kihagyom." >&2
  exit 0
fi
# A zár a folyamat végén automatikusan felszabadul (a leíró bezárul)

log() { printf '%s [%s] %s\n' "$(date '+%F %T')" "$mode" "$*"; }

log "Indul (PID $$)"
mkdir -p "$OUT_DIR"

report="$OUT_DIR/report_$(date +%Y%m%d_%H%M).txt"
tmp=$(mktemp "$OUT_DIR/.report.XXXXXX")
trap 'rm -f -- "$tmp"' EXIT

{
  echo "Gép: $(uname -n), idő: $(date -Is)"
  echo "== Lemezhasználat =="
  df -h --output=target,pcent 2>/dev/null | sort -k2 -rn | head -n 5 || df -h
  echo "== Terhelés =="
  cut -d' ' -f1-3 /proc/loadavg 2>/dev/null || uptime
} > "$tmp"

mv -- "$tmp" "$report"                          # atomikus csere: félkész fájl soha nem látszik
log "Riport kész: $report"

# Régi riportok listázása (csak kiírja; törléshez cseréld -print-et -delete-re, ha biztos vagy benne)
find "$OUT_DIR" -name 'report_*.txt' -mtime +30 -print
```
