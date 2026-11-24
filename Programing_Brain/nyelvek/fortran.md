# Fortran
<!-- tech: fortran -->

A Fortran a legrégebbi, ma is aktívan fejlesztett magas szintű nyelv (FORTRAN 77 után a modern
szabványok: 90, 95, 2003, 2008, 2018, 2023), a tudományos és mérnöki számítások, az időjárás- és
klímamodellek, a numerikus lineáris algebra (BLAS, LAPACK) és a szuperszámítógépes kódok nyelve. Statikusan
típusos, fordított, a tömbök első osztályú elemek (teljes tömbös műveletek, szeletek, oszlopfolytonos
tárolás), és a nyelvbe épített párhuzamosságot (coarray, do concurrent) az OpenMP és az MPI egészíti ki.
A modern Fortran modulokat, generikus interfészeket, objektumorientált típusokat és C-interoperabilitást
ad, a fordítók (gfortran, Intel ifx, NVIDIA nvfortran, LLVM flang) kiválóan vektorizálnak. Numerikus,
tömbközpontú munkára ideális, általános alkalmazás-, web- vagy szövegfeldolgozó fejlesztésre nem.

## Programszerkezet, implicit none és kind-ok
<!-- q: Hogyan néz ki egy modern Fortran program, és hogyan adjam meg hordozhatóan a számok pontosságát? -->
<!-- tags: program, implicit none, kind, real64, iso_fortran_env, literals, integer division -->

A modern Fortran szabad formátumú (.f90), és minden programegység elejére implicit none kell, különben az
i–n betűkkel kezdődő nem deklarált nevek egészek, a többiek valósak lesznek, így egy elgépelés csendes
hibát okoz. A pontosságot az iso_fortran_env kind-konstansaival (real64, int64) add meg, ne a nem
hordozható real*8 vagy kind=8 írásmóddal, és a literálokat is lásd el kind-dal (1.0_dp), mert a sima 1.0
egyszeres pontosságú. A tömbindexelés alapból 1-től indul, az egész osztás csonkol. Fejlesztéskor
fordíts -std=f2018 -Wall -fcheck=all kapcsolókkal, élesben -O3 -march=native beállítással.

```fortran
program heat_stats
  use, intrinsic :: iso_fortran_env, only: dp => real64, i8 => int64, output_unit
  implicit none                          ! minden változót deklarálni kell

  integer, parameter :: n = 1000         ! fordítási idejű konstans
  real(dp) :: temps(n)                   ! 64 bites valós tömb, indexek: 1..n
  real(dp) :: mean, stdev
  integer(i8) :: big_counter
  integer :: i

  ! 20.0_dp: dupla pontosságú literál; a sima 20.0 egyszeres pontosságú lenne
  do i = 1, n
     temps(i) = 20.0_dp + 5.0_dp * sin(real(i, dp) * 0.01_dp)
  end do

  mean  = sum(temps) / n
  stdev = sqrt(sum((temps - mean)**2) / (n - 1))
  big_counter = huge(0_i8)               ! az int64 legnagyobb értéke

  write(output_unit, '(a, f10.4)') 'Átlag:  ', mean
  write(output_unit, '(a, f10.4)') 'Szórás: ', stdev
  write(output_unit, '(a, i0)')    'Max int64: ', big_counter

  ! Egész osztás csonkol: 7/2 = 3; valós eredményhez valós operandus kell
  print '(a, i0, a, f4.1)', '7/2 = ', 7/2, ',  7.0/2 = ', 7.0_dp/2
end program heat_stats
```

## Tömbök: teljes tömbös műveletek, szeletek, where
<!-- q: Hogyan dolgozzak tömbökkel Fortranban ciklusok nélkül, szeletekkel és maszkokkal? -->
<!-- tags: arrays, allocatable, array slicing, where, reshape, matmul, sum, intrinsic functions -->

A Fortran tömbjein az aritmetika elemenként, ciklus nélkül működik (b = 2*a + 1), a szeletek (a(:, 2),
a(1:m:2, :)) nézetek egy részre, a where konstrukció pedig maszk szerinti feltételes értékadás. Az
allocatable tömb futás közben kap méretet, értékadáskor automatikusan újraallokálódik, és a hatókör
végén magától felszabadul, ezért a pointernél biztonságosabb. A beépített függvények (sum, maxloc,
count, matmul, dot_product, transpose) dimenzió szerint is működnek, és jól optimalizáltak. A tárolás
oszlopfolytonos (column-major), és a határon kívüli indexelés csak -fcheck=bounds mellett derül ki.

```fortran
program array_ops
  use, intrinsic :: iso_fortran_env, only: dp => real64
  implicit none
  real(dp), allocatable :: a(:,:), b(:,:), col_mean(:)
  integer :: m, n, i, ierr

  m = 4; n = 3
  allocate(a(m, n), stat=ierr)                       ! foglalás hibakezeléssel
  if (ierr /= 0) error stop 'Memóriafoglalási hiba'

  ! reshape: 1D adatból 2D tömb, OSZLOPFOLYTONOS sorrendben
  a = reshape([(real(i, dp), i = 1, m*n)], [m, n])

  ! Teljes tömbös művelet: b automatikusan (re)allokálódik
  b = 2.0_dp * a + 1.0_dp

  ! Szelet: a 2. oszlop nullázása
  a(:, 2) = 0.0_dp
  print '(3f6.1)', transpose(a)                       ! soronkénti kiírás

  ! Redukció dimenzió mentén: oszlopátlagok
  col_mean = sum(a, dim=1) / m
  print '(a, 3f8.3)', 'Oszlopátlagok: ', col_mean

  ! Maszkolt értékadás
  where (b > 20.0_dp)
     b = 20.0_dp                                      ! vágás felülről
  elsewhere (b < 5.0_dp)
     b = 0.0_dp
  end where
  print '(a, i0)', 'Pozitív elemek: ', count(b > 0.0_dp)
  print '(a, 2i3)', 'Maximum helye (sor, oszlop): ', maxloc(b)

  ! Beépített lineáris algebra
  print '(a, f8.2)', 'dot(1. oszlop, 3. oszlop) = ', dot_product(a(:, 1), a(:, 3))
  b = matmul(transpose(a), a)                         ! n x n Gram-mátrix, b 3x3-ra újraallokálódik
  print '(3f8.1)', b
end program array_ops
```

## Modulok, generikus interfészek és láthatóság
<!-- q: Hogyan szervezzem a Fortran kódot modulokba, és hogyan készítsek generikus (túlterhelt) eljárást? -->
<!-- tags: module, interface, generic, private, public, overloading, assumed-shape arrays -->

A modul típusokat, konstansokat és eljárásokat zár egységbe; a use utasítással importálva a fordító
ellenőrzi az argumentumok számát és típusát, ezért a modul nélküli, külső eljárások hibáit (rossz típusú
argumentum) kiszűri. A private alapértelmezéssel és explicit public listával tiszta API adható, a
generikus interface blokkal egy név alá több, eltérő típusú specifikus eljárás tehető (ugyanígy
saját operátor is definiálható interface operator(...) blokkal). A feltételezett alakú tömbargumentum (x(:)) a méretet a hívótól kapja,
ami modulban lévő eljárásnál biztonságos. A modulokat a használatuk előtt kell lefordítani (.mod fájl),
ezért a build-sorrend számít.

```fortran
module stats_mod
  use, intrinsic :: iso_fortran_env, only: dp => real64
  implicit none
  private                                   ! alapból minden rejtett...
  public :: dp, mean, variance, normalize   ! ...csak ez a publikus API

  interface mean                            ! generikus név, típus szerinti túlterhelés
     module procedure mean_r, mean_i
  end interface mean

contains

  pure function mean_r(x) result(m)
    real(dp), intent(in) :: x(:)            ! feltételezett alakú tömb
    real(dp) :: m
    m = sum(x) / max(size(x), 1)
  end function mean_r

  pure function mean_i(x) result(m)
    integer, intent(in) :: x(:)
    real(dp) :: m
    m = real(sum(x), dp) / max(size(x), 1)
  end function mean_i

  pure function variance(x) result(v)
    real(dp), intent(in) :: x(:)
    real(dp) :: v
    v = sum((x - mean_r(x))**2) / max(size(x) - 1, 1)
  end function variance

  subroutine normalize(x)                   ! helyben módosít: intent(inout)
    real(dp), intent(inout) :: x(:)
    real(dp) :: s
    s = sqrt(variance(x))
    if (s > 0.0_dp) x = (x - mean_r(x)) / s
  end subroutine normalize

end module stats_mod

program use_stats
  use stats_mod                             ! csak a public elemek látszanak
  implicit none
  real(dp) :: v(5) = [2.0_dp, 4.0_dp, 4.0_dp, 5.0_dp, 9.0_dp]
  print *, 'mean(real) =', mean(v), '  mean(int) =', mean([1, 2, 3, 4])
  print *, 'variance   =', variance(v)
  call normalize(v)
  print '(5f8.3)', v
end program use_stats
```

## Eljárások: intent, pure, elemental, optional argumentumok
<!-- q: Hogyan írjak jól definiált függvényeket és szubrutinokat Fortranban intenttel, optional és elemental eljárásokkal? -->
<!-- tags: subroutine, function, intent, pure, elemental, optional, present, keyword arguments, recursive -->

A function értéket ad vissza, a subroutine-t call-lal hívod, és az argumentumain keresztül ad eredményt;
az intent(in/out/inout) dokumentálja és a fordítóval ellenőrizteti az adatáramlást, az intent(out)
argumentum pedig belépéskor definiálatlan. A pure eljárásnak nincs mellékhatása (párhuzamosítható, do
concurrent-ben hívható), az elemental skalárra írt eljárás, ami tömbre elemenként alkalmazódik. Az
optional argumentum jelenlétét a present() ellenőrzi, a kulcsszavas hívás (x1=r1) olvashatóbbá teszi a
sok paraméteres hívást. Rekurzióhoz a recursive kulcsszó kell (Fortran 2018-tól alapértelmezett).

```fortran
module geometry
  use, intrinsic :: iso_fortran_env, only: dp => real64
  implicit none
  real(dp), parameter :: pi = acos(-1.0_dp)
contains

  elemental function deg2rad(deg) result(rad)      ! skalárra írva, tömbre is működik
    real(dp), intent(in) :: deg
    real(dp) :: rad
    rad = deg * pi / 180.0_dp
  end function deg2rad

  pure function haversine(lat1, lon1, lat2, lon2, radius) result(d)
    real(dp), intent(in) :: lat1, lon1, lat2, lon2
    real(dp), intent(in), optional :: radius
    real(dp) :: d, r, a, dlat, dlon
    r = 6371.0_dp                                  ! alapértelmezés: Föld sugara km-ben
    if (present(radius)) r = radius
    dlat = deg2rad(lat2 - lat1)
    dlon = deg2rad(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(deg2rad(lat1)) * cos(deg2rad(lat2)) * sin(dlon/2)**2
    d = 2.0_dp * r * asin(min(1.0_dp, sqrt(a)))
  end function haversine

  subroutine solve_quadratic(a, b, c, x1, x2, status)
    real(dp), intent(in)  :: a, b, c
    real(dp), intent(out) :: x1, x2
    integer,  intent(out) :: status               ! 0 = ok, 1 = nincs valós gyök, 2 = nem másodfokú
    real(dp) :: disc, q
    x1 = 0.0_dp; x2 = 0.0_dp
    status = 2; if (a == 0.0_dp) return
    disc = b*b - 4.0_dp*a*c
    status = 1; if (disc < 0.0_dp) return
    q = -0.5_dp * (b + sign(sqrt(disc), b))       ! stabil képlet, nincs kivonásos kiejtés
    x1 = q / a
    if (q /= 0.0_dp) then
       x2 = c / q
    else
       x2 = x1
    end if
    status = 0
  end subroutine solve_quadratic
end module geometry

program demo
  use geometry
  implicit none
  real(dp) :: r1, r2
  integer :: st
  print '(a, f8.2, a)', 'Budapest-Szeged: ', &
        haversine(47.4979_dp, 19.0402_dp, 46.2530_dp, 20.1414_dp), ' km'
  print '(3f8.4)', deg2rad([0.0_dp, 90.0_dp, 180.0_dp])          ! elemental tömbre
  call solve_quadratic(1.0_dp, -3.0_dp, 2.0_dp, x1=r1, x2=r2, status=st)
  print '(a, 2f6.2, a, i0)', 'Gyökök: ', r1, r2, '  status=', st
end program demo
```

## Származtatott típusok és objektumorientált Fortran
<!-- q: Hogyan használjak osztályokat, öröklődést és polimorfizmust modern Fortranban? -->
<!-- tags: derived types, oop, type-bound procedures, extends, abstract, deferred, class, select type, polymorphism -->

A Fortran 2003 óta a származtatott típus (type) metódusokat (type-bound procedure) kaphat, az extends
öröklést, az abstract típus deferred metódussal interfészt ad. A class(t) deklaráció polimorf: bármely
leszármazottat elfogad, a metódushívás dinamikusan kötődik, a select type pedig típusfüggő ágat nyit.
Heterogén gyűjteményhez wrapper típus kell, amelynek polimorf, allocatable komponense van, mert
polimorf elemekből álló tömb közvetlenül nem képezhető. A polimorf kód fordítói támogatása ma már jó,
de a forró numerikus ciklusokban a dinamikus kötés gátolhatja a vektorizálást.

```fortran
module shapes_mod
  use, intrinsic :: iso_fortran_env, only: dp => real64
  implicit none
  private
  public :: shape_t, circle_t, rect_t
  type, abstract :: shape_t                       ! absztrakt alaptípus
     character(len=:), allocatable :: name
  contains
     procedure(area_iface), deferred :: area      ! a leszármazott köteles megvalósítani
     procedure :: describe                        ! közös, öröklődő metódus
  end type shape_t
  abstract interface
     pure function area_iface(self) result(a)
       import :: shape_t, dp
       class(shape_t), intent(in) :: self
       real(dp) :: a
     end function area_iface
  end interface
  type, extends(shape_t) :: circle_t
     real(dp) :: r = 0.0_dp
  contains
     procedure :: area => circle_area
  end type circle_t
  type, extends(shape_t) :: rect_t
     real(dp) :: w = 0.0_dp, h = 0.0_dp
  contains
     procedure :: area => rect_area
  end type rect_t
contains
  subroutine describe(self)
    class(shape_t), intent(in) :: self            ! polimorf: bármely leszármazott
    print '(a, a, f10.3)', self%name, ' területe: ', self%area()   ! dinamikus kötés
  end subroutine describe
  pure function circle_area(self) result(a)
    class(circle_t), intent(in) :: self
    real(dp) :: a
    a = acos(-1.0_dp) * self%r**2
  end function circle_area
  pure function rect_area(self) result(a)
    class(rect_t), intent(in) :: self
    real(dp) :: a
    a = self%w * self%h
  end function rect_area
end module shapes_mod
program oop_demo
  use shapes_mod
  implicit none
  type :: shape_box                               ! wrapper a heterogén gyűjteményhez
     class(shape_t), allocatable :: s
  end type shape_box
  type(shape_box) :: items(2)
  integer :: i
  items(1)%s = circle_t(name='kör', r=2.0_dp)    ! polimorf értékadás (F2008)
  items(2)%s = rect_t(name='téglalap', w=3.0_dp, h=4.0_dp)
  do i = 1, size(items)
     call items(i)%s%describe()
     select type (sh => items(i)%s)
     type is (circle_t)
        print '(a, f6.2)', '  sugár: ', sh%r
     end select
  end do
end program oop_demo
```

## Fájlkezelés: szöveges és bináris I/O
<!-- q: Hogyan olvassak és írjak szöveges és bináris fájlokat Fortranban hibakezeléssel? -->
<!-- tags: file io, open, read, write, newunit, iostat, iomsg, unformatted, stream access, csv -->

Az open utasítás newunit argumentuma automatikusan szabad egységszámot ad, így elkerülhetők a fix
egységszám-ütközések; az iostat és iomsg argumentumokkal a hibák programból kezelhetők, a fájl végét az
iostat_end konstans jelzi. A formázott (szöveges) I/O formátumleíróval (f, es, i0, a) vagy listavezérelten
(*) működik, CSV-hez a listavezérelt olvasás a vesszőt elválasztóként kezeli. A bináris, unformatted
stream elérés gyors és bitpontos, de a bájtsorrend és a kind-ok miatt gépek között nem feltétlenül
hordozható; hosszú távú, hordozható tároláshoz HDF5 vagy NetCDF javasolt.

```fortran
program file_io
  use, intrinsic :: iso_fortran_env, only: dp => real64, iostat_end, error_unit
  implicit none
  integer :: u, ios, n, i
  real(dp) :: t, v
  real(dp), allocatable :: data(:,:)
  character(len=256) :: msg, line

  ! 1) Szöveges írás: newunit szabad egységszámot ad
  open(newunit=u, file='samples.csv', status='replace', action='write', iostat=ios, iomsg=msg)
  if (ios /= 0) error stop trim(msg)
  write(u, '(a)') 'time,value'
  do i = 1, 5
     write(u, '(f0.2, a, es12.5)') i * 0.1_dp, ',', exp(-real(i, dp))
  end do
  close(u)

  ! 2) Olvasás a fájl végéig, hibás sorok kihagyásával
  open(newunit=u, file='samples.csv', status='old', action='read')
  read(u, '(a)') line                             ! fejléc
  n = 0
  do
     read(u, *, iostat=ios) t, v                  ! listavezérelt: a vessző elválasztó
     if (ios == iostat_end) exit
     if (ios /= 0) then
        write(error_unit, '(a)') 'Hibás sor, kihagyva'
        cycle
     end if
     n = n + 1
  end do
  close(u)
  print '(a, i0)', 'Beolvasott sorok: ', n

  ! 3) Bináris stream: előbb a méret, utána az adat
  allocate(data(1000, 3))
  call random_number(data)
  open(newunit=u, file='matrix.bin', access='stream', form='unformatted', status='replace')
  write(u) shape(data), data
  close(u)

  open(newunit=u, file='matrix.bin', access='stream', form='unformatted', status='old')
  block
     integer :: dims(2)
     real(dp), allocatable :: back(:,:)
     read(u) dims
     allocate(back(dims(1), dims(2)))
     read(u) back
     print '(a, l1)', 'Bináris visszaolvasás egyezik: ', all(back == data)
  end block
  close(u)
end program file_io
```

## Párhuzamosítás OpenMP-vel
<!-- q: Hogyan párhuzamosítsak egy Fortran ciklust OpenMP-vel versenyhelyzet nélkül? -->
<!-- tags: openmp, parallel do, reduction, private, schedule, race condition, shared memory -->

Az OpenMP megosztott memóriás szálpárhuzamosítás fordítói direktívákkal (!$omp ...), amelyek -fopenmp
nélkül egyszerű megjegyzések maradnak, így a kód soros módban is fordul. A parallel do a ciklus
iterációit osztja szét a szálak között; a ciklusváltozó automatikusan privát, a többi belső
segédváltozót private-ként kell megadni. Ha több szál ugyanabba a változóba gyűjt, reduction kell, mert
különben versenyhelyzet (race condition) miatt hibás, futásonként eltérő eredmény jön ki. Oszlopfolytonos
tárolás miatt a legbelső ciklus az első index legyen, valós mátrixszorzáshoz pedig a matmul vagy egy
optimalizált BLAS (dgemm) jobb a kézi ciklusnál.

```fortran
! Fordítás: gfortran -O3 -fopenmp omp_demo.f90 ; futtatás: OMP_NUM_THREADS=8 ./a.out
program omp_demo
  use, intrinsic :: iso_fortran_env, only: dp => real64
  use omp_lib
  implicit none
  integer, parameter :: n = 1500
  real(dp), allocatable :: a(:,:), b(:,:), c(:,:)
  real(dp) :: total, t0
  integer :: i, j, k

  allocate(a(n, n), b(n, n), c(n, n))
  call random_number(a)
  call random_number(b)
  t0 = omp_get_wtime()

  ! Az oszlopokat (j) osztjuk szét; a legbelső ciklus az i -> folytonos memóriaelérés
  !$omp parallel do private(i, k) schedule(static)
  do j = 1, n
     c(:, j) = 0.0_dp
     do k = 1, n
        do i = 1, n
           c(i, j) = c(i, j) + a(i, k) * b(k, j)
        end do
     end do
  end do
  !$omp end parallel do
  print '(a, f8.3, a, i0, a)', 'Szorzás: ', omp_get_wtime() - t0, ' s (', &
        omp_get_max_threads(), ' szál)'

  ! Redukció: szálankénti részösszeg, a végén összeadva (nélküle race condition!)
  total = 0.0_dp
  !$omp parallel do reduction(+:total) collapse(2)
  do j = 1, n
     do i = 1, n
        total = total + c(i, j)
     end do
  end do
  !$omp end parallel do
  print '(a, es14.6)', 'Elemösszeg: ', total

  ! Kritikus szakasz: egyszerre egy szál írhat a kimenetre
  !$omp parallel
  !$omp critical
  print '(a, i0)', 'Szál kész: ', omp_get_thread_num()
  !$omp end critical
  !$omp end parallel
end program omp_demo
```

## Coarray-ek: beépített elosztott párhuzamosság
<!-- q: Hogyan írjak párhuzamos Fortran programot coarray-ekkel több folyamaton? -->
<!-- tags: coarray, image, this_image, num_images, sync all, co_sum, spmd, pgas, opencoarrays -->

A coarray Fortran SPMD modellt használ: ugyanaz a program több példányban (image) fut, mindegyik saját
memóriával, és a szögletes zárójeles coarray-szintaxis (x[img]) egy másik image változóját éri el
(PGAS modell). A this_image() és num_images() adja az azonosítót és a példányszámot, a sync all
szinkronizál, a Fortran 2018 kollektív műveletei (co_sum, co_max, co_broadcast) pedig hatékony
redukciót adnak. A távoli elérés kommunikáció, ezért drága: a számítást lokálisan végezd, és ritkán
cserélj adatot. gfortran-nal az OpenCoarrays könyvtár (caf, cafrun) kell, az Intel ifx natívan támogatja.

```fortran
! Fordítás: caf -O2 pi.f90 -o pi ; futtatás: cafrun -n 4 ./pi   (vagy: ifx -coarray)
program coarray_pi
  use, intrinsic :: iso_fortran_env, only: dp => real64, i8 => int64
  implicit none
  integer(i8), parameter :: samples = 10000000_i8     ! mintaszám image-enként
  integer(i8) :: hits[*]                              ! coarray: minden image-nek saját példány
  integer(i8) :: i, total
  real(dp) :: x, y
  integer :: me, np, img

  me = this_image()                                   ! 1..num_images()
  np = num_images()
  call random_init(repeatable=.false., image_distinct=.true.)   ! image-enként eltérő sorozat

  hits = 0
  do i = 1, samples                                   ! Monte Carlo pi-becslés lokálisan
     call random_number(x)
     call random_number(y)
     if (x*x + y*y <= 1.0_dp) hits = hits + 1
  end do

  ! 1) Kézi gyűjtés: mindenki végzett, majd az 1. image kiolvassa a többieket
  sync all
  if (me == 1) then
     total = hits
     do img = 2, np
        total = total + hits[img]                     ! távoli olvasás = kommunikáció
     end do
     print '(a, i0, a, f12.8)', 'Image-ek: ', np, '  pi ~ ', 4.0_dp * total / (samples * np)
  end if
  sync all                                            ! az olvasás befejeződjön a módosítás előtt

  ! 2) Kollektív redukció (F2018): fa-alapú, hatékonyabb
  call co_sum(hits, result_image=1)
  if (me == 1) print '(a, i0)', 'co_sum találatok: ', hits
end program coarray_pi
```

## Teljesítmény: memória-elrendezés, contiguous, do concurrent
<!-- q: Hogyan írjak gyors Fortran kódot, és miért számít a ciklusok sorrendje? -->
<!-- tags: performance, column-major, cache, contiguous, do concurrent, vectorization, array temporaries -->

A Fortran tömbjei oszlopfolytonosak: az első (bal oldali) index szomszédos elemei vannak egymás mellett a
memóriában, ezért beágyazott ciklusnál a legbelső ciklus az első indexen fusson, különben nagy
lépésközű, cache-ellenes elérés lesz belőle, ami többszörös lassulást okozhat. A contiguous attribútum
megengedi a fordítónak, hogy folytonos memóriát feltételezzen (jobb vektorizálás), de nem folytonos
szelettel hívva rejtett ideiglenes másolat készül. A do concurrent kijelenti, hogy az iterációk
függetlenek, így a fordító vektorizálhat vagy párhuzamosíthat. A -fcheck=all fejlesztéskor hasznos, de
lassít; méréshez -O3 -march=native kapcsolókkal fordíts.

```fortran
module perf_mod
  use, intrinsic :: iso_fortran_env, only: dp => real64
  implicit none
contains
  subroutine scale_good(a, s)               ! JÓ: a belső ciklus az első indexen fut
    real(dp), intent(inout) :: a(:,:)
    real(dp), intent(in) :: s
    integer :: i, j
    do j = 1, size(a, 2)
       do i = 1, size(a, 1)                 ! folytonos memória, SIMD-barát
          a(i, j) = a(i, j) * s
       end do
    end do
  end subroutine scale_good

  subroutine scale_bad(a, s)                ! ROSSZ: a belső ciklus oszlopokat ugrál
    real(dp), intent(inout) :: a(:,:)
    real(dp), intent(in) :: s
    integer :: i, j
    do i = 1, size(a, 1)
       do j = 1, size(a, 2)
          a(i, j) = a(i, j) * s
       end do
    end do
  end subroutine scale_bad

  pure subroutine axpy(y, alpha, x)         ! y = y + alpha * x
    real(dp), intent(inout), contiguous :: y(:)
    real(dp), intent(in) :: alpha
    real(dp), intent(in), contiguous :: x(:)
    integer :: i
    do concurrent (i = 1:size(y))           ! független iterációk
       y(i) = y(i) + alpha * x(i)
    end do
  end subroutine axpy
end module perf_mod

program perf_demo
  use, intrinsic :: iso_fortran_env, only: int64
  use perf_mod
  implicit none
  real(dp), allocatable :: m(:,:), x(:), y(:)
  integer(int64) :: c0, c1, rate

  allocate(m(4000, 4000), x(10**7), y(10**7))
  call random_number(m)
  call random_number(x)
  y = 0.0_dp

  call system_clock(c0, rate)
  call scale_good(m, 1.0001_dp)
  call system_clock(c1)
  print '(a, f8.4, a)', 'oszlopfolytonos: ', real(c1 - c0) / real(rate), ' s'

  call system_clock(c0)
  call scale_bad(m, 1.0001_dp)
  call system_clock(c1)
  print '(a, f8.4, a)', 'soronkénti:      ', real(c1 - c0) / real(rate), ' s'

  call axpy(y, 2.0_dp, x)
  ! BUKTATÓ: m(1, :) egy SOR, ami nem folytonos -> contiguous argumentumnál másolat készülne
  print '(a, f14.4)', 'sum(y) = ', sum(y)
end program perf_demo
```

## C-interoperabilitás iso_c_binding-gel
<!-- q: Hogyan hívjak C függvényt Fortranból, és hogyan tegyek Fortran rutint C-ből hívhatóvá? -->
<!-- tags: iso_c_binding, bind(c), interoperability, c_double, c_int, value, c strings, name mangling -->

Az iso_c_binding modul a C típusokkal kompatibilis kind-okat (c_int, c_double, c_char) ad, a bind(c,
name='...') pedig név-dekoráció (name mangling) nélküli, C hívási konvencióval elérhető szimbólumot
készít. A C érték szerinti paraméteréhez a Fortran oldalon value attribútum kell, a tömbök C pointerként
utaznak, a stringeket pedig null-karakterrel (c_null_char) kell lezárni. Fontos különbség, hogy a
Fortran oszlopfolytonos, a C sorfolytonos, ezért egy m×n Fortran mátrix (i, j) eleme C-ben a[j*m + i]
(0-tól indexelve). Így a nagy numerikus Fortran könyvtárak Pythonból (ctypes, f2py) vagy C/C++-ból is
használhatók.

```fortran
module cinterop
  use, intrinsic :: iso_c_binding, only: c_double, c_int, c_char, c_null_char, c_size_t
  implicit none

  ! C függvény hívása Fortranból: size_t strlen(const char *s);
  interface
     function c_strlen(s) bind(c, name='strlen') result(n)
       import :: c_char, c_size_t
       character(kind=c_char), intent(in) :: s(*)
       integer(c_size_t) :: n
     end function c_strlen
  end interface

contains

  ! C-ből hívható: double f_dot(const double *x, const double *y, int n);
  function dot(x, y, n) bind(c, name='f_dot') result(d)
    integer(c_int), value, intent(in) :: n          ! value: érték szerinti átadás
    real(c_double), intent(in) :: x(n), y(n)        ! explicit méretű tömb = C pointer
    real(c_double) :: d
    d = dot_product(x, y)
  end function dot

  ! C-ből hívható: void f_fill_matrix(double *a, int m, int n);
  subroutine fill_matrix(a, m, n) bind(c, name='f_fill_matrix')
    integer(c_int), value, intent(in) :: m, n
    real(c_double), intent(out) :: a(m, n)
    integer :: i, j
    do j = 1, n
       do i = 1, m
          a(i, j) = real(10*i + j, c_double)          ! pl. a(2,3) = 23
       end do
    end do
  end subroutine fill_matrix

  ! Fortran string átadása C-nek: null-terminátor kell
  function fstrlen(s) result(n)
    character(len=*), intent(in) :: s
    integer :: n
    n = int(c_strlen(s // c_null_char))
  end function fstrlen
end module cinterop
```

```c
/* Fordítás: gfortran -c cinterop.f90 && gcc main.c cinterop.o -lgfortran -o demo */
#include <stdio.h>

/* A bind(c, name=...) szimbólumok, név-dekoráció nélkül */
double f_dot(const double *x, const double *y, int n);
void f_fill_matrix(double *a, int m, int n);

int main(void) {
    double x[3] = {1, 2, 3}, y[3] = {4, 5, 6};
    printf("dot = %.1f\n", f_dot(x, y, 3));        /* 32.0 */

    int m = 2, n = 3;
    double a[2 * 3];
    f_fill_matrix(a, m, n);
    /* column-major: a Fortran (i, j) eleme (0-tól) a[j*m + i] */
    printf("a(2,3) = %.0f\n", a[2 * m + 1]);       /* 23 */
    return 0;
}
```
