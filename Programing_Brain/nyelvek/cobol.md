# COBOL
<!-- tech: cobol -->

A COBOL (COmmon Business-Oriented Language) 1959 óta az üzleti adatfeldolgozás nyelve: bankok, biztosítók,
közigazgatás és kereskedelem mainframe-rendszereinek (IBM z/OS, CICS, IMS, DB2) magja, ahol ma is
hatalmas mennyiségű tranzakció fut rajta. Bőbeszédű, angolszerű szintaxisa négy részre (division) tagolja
a programot, az adatokat rögzített hosszú, PIC záradékkal leírt rekordokban kezeli, és natívan ismeri a
pontos tizedes aritmetikát (packed decimal, COMP-3), ami pénzügyi számításnál a lebegőpontos kerekítési
hibákat kiküszöböli. Erőssége a nagy volumenű kötegelt (batch) fájl- és rekordfeldolgozás, a
visszafelé kompatibilitás és a stabilitás; gyenge pontja a modern eszközkészlet, az általános célú
programozás és a szakemberhiány. A példák fix formátumúak (7. oszlop: jelző, 8–11.: A terület,
12–72.: B terület), és GnuCOBOL-lal, illetve IBM Enterprise COBOL-lal is fordíthatók.

## Programszerkezet: a négy DIVISION
<!-- q: Hogyan épül fel egy COBOL program, és mit tartalmaz a négy division? -->
<!-- tags: identification division, environment division, data division, procedure division, fixed format, program structure -->

Minden COBOL program négy, kötött sorrendű részből áll: az IDENTIFICATION DIVISION a program nevét
(PROGRAM-ID) adja, az ENVIRONMENT DIVISION a környezetet (fájlhozzárendelés, tizedesjel), a DATA
DIVISION az összes adatot (fájlrekordok, munkaterület, paraméterek), a PROCEDURE DIVISION pedig a
végrehajtandó utasításokat bekezdésekbe (paragraph) szervezve. Fix formátumban a division-, section- és
bekezdésnevek, valamint a 01-es és 77-es szintek az A területen (8. oszloptól), az utasítások a B
területen (12. oszloptól) kezdődnek, a 72. oszlop utáni rész elvész. A DECIMAL-POINT IS COMMA a magyar
konvenció szerinti tizedesvesszőt kapcsolja be a literálokban és a szerkesztett mezőkben.

```cobol
       IDENTIFICATION DIVISION.
       PROGRAM-ID. INVOICE-TOTAL.
      * A sorrend kötelező: IDENTIFICATION, ENVIRONMENT,
      * DATA, PROCEDURE.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SPECIAL-NAMES.
      *    Tizedesvessző: 125000,50 és ,270 a literálokban
           DECIMAL-POINT IS COMMA.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-INVOICE.
           05  WS-NET-AMOUNT     PIC 9(7)V99   VALUE 125000,50.
           05  WS-VAT-RATE       PIC V999      VALUE ,270.
           05  WS-VAT-AMOUNT     PIC 9(7)V99   VALUE ZERO.
           05  WS-GROSS-AMOUNT   PIC 9(8)V99   VALUE ZERO.
      * Szerkesztett mező kiíráshoz: ezres pont, tizedesvessző
       01  WS-DISPLAY-AMOUNT     PIC Z.ZZZ.ZZ9,99.
       PROCEDURE DIVISION.
       MAIN-PARA.
      *    ÁFA kerekítve, majd bruttó összeg
           COMPUTE WS-VAT-AMOUNT ROUNDED =
                   WS-NET-AMOUNT * WS-VAT-RATE
           ADD WS-NET-AMOUNT WS-VAT-AMOUNT
               GIVING WS-GROSS-AMOUNT
           MOVE WS-GROSS-AMOUNT TO WS-DISPLAY-AMOUNT
      *    Kimenet: "Bruttó:   158.750,64 Ft"
           DISPLAY "Bruttó: " WS-DISPLAY-AMOUNT " Ft"
           STOP RUN.
```

## PIC záradékok, szintszámok, 88-as feltételnevek és REDEFINES
<!-- q: Hogyan írjam le az adatszerkezeteket COBOL-ban PIC záradékokkal, szintszámokkal és REDEFINES-szal? -->
<!-- tags: pic clause, picture, level numbers, 88 level, redefines, filler, edited picture, data division -->

A PIC (PICTURE) záradék a mező típusát és hosszát írja le: 9 = számjegy, X = tetszőleges karakter, A =
betű, S = előjel, V = implicit tizedesjel (nem foglal helyet), a szerkesztett képek (Z, vessző, pont,
mínusz, perjel) pedig a kiírt formát. A szintszámok hierarchiát adnak (01 a rekord, 05/10 az alárendelt
mezők, 77 önálló elemi mező), a 88-as szint feltételnevet definiál, amellyel olvasható IF és SET TO TRUE
írható. A REDEFINES ugyanazt a memóriát más szerkezettel írja le (például egy dátum egészben és részekre
bontva), a FILLER névtelen kitöltés. Buktató: a MOVE csendben csonkol, ha a cél rövidebb, ezért a
mezőhosszakat gondosan kell méretezni.

```cobol
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PIC-DEMO.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
      * 01 = rekord, 05/10 = alárendelt mező, 77 = önálló mező,
      * 88 = feltételnév (logikai érték a szülőmezőre)
       01  CUSTOMER-REC.
           05  CUST-ID            PIC 9(8).
           05  CUST-NAME          PIC X(30).
           05  CUST-BIRTH-DATE    PIC 9(8).
      *    REDEFINES: ugyanaz a 8 bájt részekre bontva
           05  CUST-BIRTH-PARTS REDEFINES CUST-BIRTH-DATE.
               10  CUST-BIRTH-YYYY PIC 9(4).
               10  CUST-BIRTH-MM   PIC 99.
               10  CUST-BIRTH-DD   PIC 99.
           05  CUST-BALANCE       PIC S9(9)V99
                                  SIGN LEADING SEPARATE.
           05  CUST-STATUS        PIC X.
               88  STATUS-ACTIVE          VALUE "A".
               88  STATUS-BLOCKED         VALUE "B".
               88  STATUS-VALID           VALUE "A" "B" "C".
           05  FILLER             PIC X(10).
       77  WS-EDITED-BAL          PIC -ZZZ,ZZZ,ZZ9.99.
       77  WS-EDITED-DATE         PIC 9999/99/99.
       77  WS-SMALL               PIC 9(3).
       77  WS-SOURCE              PIC 9(4)  VALUE 1234.
       PROCEDURE DIVISION.
       MAIN-PARA.
           MOVE 12345678 TO CUST-ID
           MOVE "Minta Kereskedelmi Bt." TO CUST-NAME
           MOVE 19850312 TO CUST-BIRTH-DATE
           MOVE -1234567.89 TO CUST-BALANCE
           SET STATUS-ACTIVE TO TRUE
           DISPLAY "Év a REDEFINES-on át: " CUST-BIRTH-YYYY
           MOVE CUST-BALANCE TO WS-EDITED-BAL
           DISPLAY "Egyenleg: " WS-EDITED-BAL
           MOVE CUST-BIRTH-DATE TO WS-EDITED-DATE
           DISPLAY "Dátum: " WS-EDITED-DATE
           IF STATUS-ACTIVE AND STATUS-VALID
               DISPLAY "Aktív ügyfél"
           END-IF
      *    BUKTATÓ: a MOVE balról csonkol: 1234 -> 234
           MOVE WS-SOURCE TO WS-SMALL
           DISPLAY "Csonkolva: " WS-SMALL
           STOP RUN.
```

## Számtípusok: DISPLAY, COMP, COMP-3 és kerekítés
<!-- q: Mi a különbség a DISPLAY, COMP és COMP-3 számmezők között, és hogyan kerekítsek pontosan COBOL-ban? -->
<!-- tags: comp-3, packed decimal, comp, binary, display, rounded, on size error, decimal arithmetic -->

A DISPLAY (zónázott) szám számjegyenként egy bájt, olvasható, de lassú; a COMP-3 (packed decimal)
bájtonként két számjegyet és egy előjel-félbájtot tárol, így egy S9(7)V99 mező 5 bájt, és az aritmetika
pontos tizedes, ami pénzügyi számításnál kötelező. A COMP/BINARY kettes komplemens egész, ciklusszámlálóhoz
és indexhez gyors, a COMP-2 duplapontos lebegőpontos, pénzhez nem való. A ROUNDED nélkül a felesleges
tizedesek csonkolódnak, az ON SIZE ERROR pedig a túlcsordulást jelzi a csendes, magasabb helyiértékű
csonkolás helyett. A COMP-3 mezőhöz páratlan számú számjegyet érdemes választani, mert az előjellel
együtt így tölti ki pontosan a bájtokat.

```cobol
       IDENTIFICATION DIVISION.
       PROGRAM-ID. NUMERIC-DEMO.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
      * DISPLAY (zónázott): 1 bájt / számjegy -> 9 bájt
       01  WS-ZONED      PIC S9(7)V99         VALUE +12345.67.
      * COMP-3: 2 számjegy / bájt + előjel -> (9 + 1) / 2 = 5 bájt
       01  WS-PACKED     PIC S9(7)V99 COMP-3  VALUE +12345.67.
      * COMP / BINARY: gyors egész számláló
       01  WS-YEAR       PIC S9(4)    COMP    VALUE 0.
       01  WS-RATE       PIC S9V9(6)  COMP-3  VALUE +0.035000.
       01  WS-INTEREST   PIC S9(7)V99 COMP-3  VALUE 0.
       01  WS-SMALL      PIC S9(3)V99 COMP-3  VALUE 0.
       01  WS-OUT        PIC -Z(6)9.99.
       PROCEDURE DIVISION.
       MAIN-PARA.
      *    ROUNDED nélkül a 3. tizedestől csonkolna
           COMPUTE WS-INTEREST ROUNDED = WS-PACKED * WS-RATE
           MOVE WS-INTEREST TO WS-OUT
           DISPLAY "Éves kamat: " WS-OUT
      *    Kamatos kamat 3 évre, pontos tizedes aritmetikával
           PERFORM VARYING WS-YEAR FROM 1 BY 1
                   UNTIL WS-YEAR > 3
               COMPUTE WS-INTEREST ROUNDED = WS-PACKED * WS-RATE
               ADD WS-INTEREST TO WS-PACKED
           END-PERFORM
           MOVE WS-PACKED TO WS-OUT
           DISPLAY "Egyenleg 3 év után: " WS-OUT
      *    ON SIZE ERROR: a túlcsordulás nem csonkol csendben
           COMPUTE WS-SMALL = WS-PACKED * 100
               ON SIZE ERROR
                   DISPLAY "Túlcsordulás: nem fér el az eredmény"
               NOT ON SIZE ERROR
                   DISPLAY "Rendben"
           END-COMPUTE
           DISPLAY "Méret (bájt): " LENGTH OF WS-ZONED
                   " / " LENGTH OF WS-PACKED
           STOP RUN.
```

## Vezérlés: PERFORM, EVALUATE és bekezdések
<!-- q: Hogyan írjak ciklust és többirányú elágazást COBOL-ban PERFORM és EVALUATE utasításokkal? -->
<!-- tags: perform, perform varying, perform until, evaluate, paragraph, 88 level, structured programming -->

A COBOL strukturált vezérlése a PERFORM-ra épül: PERFORM bekezdésnév meghív egy bekezdést (eljárás),
a PERFORM VARYING a for-ciklus, a PERFORM UNTIL a while-ciklus megfelelője, inline formában END-PERFORM-mal
lezárva. Az EVALUATE a többirányú elágazás (switch), az ALSO kulcsszóval több feltétel döntési táblaként
is leírható, a WHEN OTHER az alapértelmezett ág. A 88-as feltételnevekkel a ciklusfeltételek olvashatók
(PERFORM UNTIL WS-DONE), a GO TO használata pedig kerülendő, mert átláthatatlan vezérlést okoz. A
bekezdés végét a pont jelzi; egy elfelejtett vagy rossz helyre tett pont a régi stílusú kódban az IF
hatókörét is lezárja, ezért mindig END-IF/END-EVALUATE lezárókat használj.

```cobol
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CONTROL-DEMO.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-SCORE-TABLE.
           05  WS-SCORE          PIC 999 OCCURS 5 TIMES.
       01  WS-IDX                PIC 99   COMP.
       01  WS-GRADE              PIC 9.
       01  WS-SUM                PIC 9(4) VALUE 0.
       01  WS-AVG                PIC ZZ9.9.
       01  WS-REGION             PIC XX   VALUE "HU".
       01  WS-WEIGHT             PIC 99V9 VALUE 7.5.
       01  WS-FEE                PIC 9(5).
       01  WS-RETRY              PIC 9    VALUE 0.
       01  WS-STATUS             PIC X    VALUE "N".
           88  WS-DONE                    VALUE "Y".
       PROCEDURE DIVISION.
       MAIN-PROCEDURE.
           MOVE 92 TO WS-SCORE(1)
           MOVE 78 TO WS-SCORE(2)
           MOVE 64 TO WS-SCORE(3)
           MOVE 45 TO WS-SCORE(4)
           MOVE 88 TO WS-SCORE(5)
      *    PERFORM VARYING: a for-ciklus megfelelője
           PERFORM VARYING WS-IDX FROM 1 BY 1 UNTIL WS-IDX > 5
               PERFORM GRADE-ONE
               ADD WS-SCORE(WS-IDX) TO WS-SUM
           END-PERFORM
           COMPUTE WS-AVG = WS-SUM / 5
           DISPLAY "Átlag: " WS-AVG
      *    EVALUATE ... ALSO: döntési tábla két feltétellel
           EVALUATE WS-REGION ALSO TRUE
               WHEN "HU" ALSO WS-WEIGHT <= 5
                   MOVE 1490 TO WS-FEE
               WHEN "HU" ALSO ANY
                   MOVE 2990 TO WS-FEE
               WHEN "EU" ALSO WS-WEIGHT <= 5
                   MOVE 4990 TO WS-FEE
               WHEN OTHER
                   MOVE 9990 TO WS-FEE
           END-EVALUATE
           DISPLAY "Szállítási díj: " WS-FEE
      *    PERFORM UNTIL 88-as feltétellel: a while-ciklus
           PERFORM UNTIL WS-DONE OR WS-RETRY >= 3
               ADD 1 TO WS-RETRY
               IF WS-RETRY = 2
                   SET WS-DONE TO TRUE
               END-IF
           END-PERFORM
           DISPLAY "Próbálkozások: " WS-RETRY
           STOP RUN.

       GRADE-ONE.
           EVALUATE TRUE
               WHEN WS-SCORE(WS-IDX) >= 85  MOVE 5 TO WS-GRADE
               WHEN WS-SCORE(WS-IDX) >= 70  MOVE 4 TO WS-GRADE
               WHEN WS-SCORE(WS-IDX) >= 55  MOVE 3 TO WS-GRADE
               WHEN WS-SCORE(WS-IDX) >= 50  MOVE 2 TO WS-GRADE
               WHEN OTHER                   MOVE 1 TO WS-GRADE
           END-EVALUATE
           DISPLAY "Pont: " WS-SCORE(WS-IDX) "  Jegy: " WS-GRADE.
```

## Szekvenciális fájlkezelés és FILE STATUS
<!-- q: Hogyan olvassak végig egy szekvenciális fájlt COBOL-ban hibakezeléssel? -->
<!-- tags: sequential file, select, assign, fd, read at end, file status, open, close, batch processing -->

A fájlt az ENVIRONMENT DIVISION FILE-CONTROL részében a SELECT ... ASSIGN köti fizikai fájlhoz (mainframe-en
a JCL DD nevéhez), a DATA DIVISION FD bejegyzése pedig a rekord pontos szerkezetét írja le. A klasszikus
feldolgozási minta az előolvasás (priming read): egy READ a ciklus előtt, majd a ciklus végén mindig a
következő rekord olvasása, amíg az AT END fel nem lép. Minden fájlhoz adj FILE STATUS mezőt, és minden
művelet után ellenőrizd ("00" = rendben, "10" = fájl vége, "35" = nem létező fájl), mert e nélkül egy
hiba csendben hibás eredményt adhat. A LINE SEQUENTIAL GnuCOBOL/Micro Focus szövegfájl, mainframe-en
ennek a SEQUENTIAL szervezés, fix hosszú (FB) rekordokkal felel meg.

```cobol
       IDENTIFICATION DIVISION.
       PROGRAM-ID. SEQ-FILE.
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT TXN-FILE ASSIGN TO "transactions.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS WS-TXN-STATUS.
       DATA DIVISION.
       FILE SECTION.
      * FD: a rekord fizikai elrendezése (fix hosszú mezők)
       FD  TXN-FILE.
       01  TXN-REC.
           05  TXN-ACCOUNT       PIC X(10).
           05  TXN-TYPE          PIC X.
               88  TXN-CREDIT            VALUE "C".
               88  TXN-DEBIT             VALUE "D".
           05  TXN-AMOUNT        PIC 9(7)V99.
       WORKING-STORAGE SECTION.
       01  WS-TXN-STATUS         PIC XX.
           88  TXN-OK                    VALUE "00".
           88  TXN-EOF                   VALUE "10".
       01  WS-BALANCE            PIC S9(9)V99 VALUE 0.
       01  WS-COUNT              PIC 9(6)     VALUE 0.
       01  WS-OUT-BAL            PIC -ZZZ,ZZZ,ZZ9.99.
       PROCEDURE DIVISION.
       MAIN-PARA.
           OPEN INPUT TXN-FILE
           IF NOT TXN-OK
               DISPLAY "Megnyitási hiba, STATUS: " WS-TXN-STATUS
               STOP RUN
           END-IF
      *    Előolvasás, majd ciklus a fájl végéig
           PERFORM READ-NEXT
           PERFORM UNTIL TXN-EOF
               PERFORM PROCESS-TXN
               PERFORM READ-NEXT
           END-PERFORM
           CLOSE TXN-FILE
           MOVE WS-BALANCE TO WS-OUT-BAL
           DISPLAY "Tranzakciók: " WS-COUNT
           DISPLAY "Egyenleg:    " WS-OUT-BAL
           STOP RUN.

       READ-NEXT.
           READ TXN-FILE
               AT END CONTINUE
           END-READ
           IF NOT TXN-OK AND NOT TXN-EOF
               DISPLAY "Olvasási hiba, STATUS: " WS-TXN-STATUS
               STOP RUN
           END-IF.

       PROCESS-TXN.
           ADD 1 TO WS-COUNT
           EVALUATE TRUE
               WHEN TXN-CREDIT
                   ADD TXN-AMOUNT TO WS-BALANCE
               WHEN TXN-DEBIT
                   SUBTRACT TXN-AMOUNT FROM WS-BALANCE
               WHEN OTHER
                   DISPLAY "Ismeretlen típus: " TXN-ACCOUNT
           END-EVALUATE.
```

## Indexelt (VSAM/ISAM) fájlok: kulcs szerinti elérés
<!-- q: Hogyan olvassak, írjak és módosítsak rekordokat kulcs alapján egy indexelt COBOL fájlban? -->
<!-- tags: indexed file, vsam, ksds, record key, alternate key, read, rewrite, start, invalid key, dynamic access -->

Az ORGANIZATION IS INDEXED fájl (mainframe-en VSAM KSDS) a rekordokat elsődleges kulcs szerint tárolja,
így közvetlen (random) olvasás, beszúrás, módosítás (REWRITE) és törlés (DELETE) is lehetséges, a
másodlagos kulcs (ALTERNATE RECORD KEY) pedig további keresési utat ad, akár duplikátumokkal. Az ACCESS MODE
IS DYNAMIC egyszerre engedi a kulcs szerinti és a szekvenciális elérést: a START a megadott kulcsra
pozicionál, utána a READ NEXT halad tovább. Az INVALID KEY ág a nem talált ("23") vagy duplikált ("22")
kulcsot kezeli. REWRITE előtt a rekordot ugyanabban a futásban be kell olvasni, és az elsődleges kulcs
nem módosítható.

```cobol
       IDENTIFICATION DIVISION.
       PROGRAM-ID. ACCT-UPDATE.
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT ACCT-FILE ASSIGN TO "accounts.idx"
               ORGANIZATION IS INDEXED
               ACCESS MODE IS DYNAMIC
               RECORD KEY IS ACCT-ID
               ALTERNATE RECORD KEY IS ACCT-BRANCH WITH DUPLICATES
               FILE STATUS IS WS-STATUS.
       DATA DIVISION.
       FILE SECTION.
       FD  ACCT-FILE.
       01  ACCT-REC.
           05  ACCT-ID           PIC X(10).
           05  ACCT-BRANCH       PIC X(4).
           05  ACCT-BALANCE      PIC S9(9)V99 COMP-3.
       WORKING-STORAGE SECTION.
      * "02" = olvasás sikeres, és van még azonos másodlagos kulcs
       01  WS-STATUS             PIC XX.
           88  WS-OK                     VALUE "00" "02".
           88  WS-EOF                    VALUE "10".
       01  WS-OUT                PIC -ZZZ,ZZZ,ZZ9.99.
       PROCEDURE DIVISION.
       MAIN-PARA.
           OPEN I-O ACCT-FILE
      *    1) Közvetlen olvasás kulcs alapján, majd módosítás
           MOVE "TEST000042" TO ACCT-ID
           READ ACCT-FILE
               INVALID KEY
                   DISPLAY "Nincs ilyen számla: " ACCT-ID
               NOT INVALID KEY
                   ADD 1500.00 TO ACCT-BALANCE
                   REWRITE ACCT-REC
                       INVALID KEY DISPLAY "REWRITE hiba: " WS-STATUS
                   END-REWRITE
           END-READ
      *    2) Új rekord: létező kulcsnál INVALID KEY (STATUS 22)
           MOVE "TEST000099" TO ACCT-ID
           MOVE "0101" TO ACCT-BRANCH
           MOVE 0 TO ACCT-BALANCE
           WRITE ACCT-REC
               INVALID KEY DISPLAY "Már létezik: " ACCT-ID
           END-WRITE
      *    3) Pozicionálás másodlagos kulcsra, majd bejárás
           MOVE "0101" TO ACCT-BRANCH
           START ACCT-FILE KEY IS EQUAL TO ACCT-BRANCH
               INVALID KEY
                   DISPLAY "Nincs ilyen fiók"
               NOT INVALID KEY
                   PERFORM UNTIL NOT WS-OK
                       READ ACCT-FILE NEXT RECORD
                           AT END SET WS-EOF TO TRUE
                       END-READ
                       IF WS-OK AND ACCT-BRANCH = "0101"
                           MOVE ACCT-BALANCE TO WS-OUT
                           DISPLAY ACCT-ID " " WS-OUT
                       ELSE
                           SET WS-EOF TO TRUE
                       END-IF
                   END-PERFORM
           END-START
           CLOSE ACCT-FILE
           STOP RUN.
```

## Táblák: OCCURS, SEARCH és SEARCH ALL
<!-- q: Hogyan használjak tömböket (táblákat) COBOL-ban, és hogyan keressek bennük gyorsan? -->
<!-- tags: occurs, table, indexed by, search, search all, binary search, occurs depending on, redefines -->

A COBOL tömbje az OCCURS záradékkal ismételt mező vagy csoport, amelyet 1-től indexelünk; az INDEXED BY
indexváltozót (bájt-eltolást) ad, ami gyorsabb a sima számlálós indexelésnél, és a SEARCH utasítás ezt
használja. A SEARCH lineáris keresés, előtte az indexet SET-tel be kell állítani; a SEARCH ALL bináris
keresés, amelyhez ASCENDING/DESCENDING KEY kell, és a táblának ténylegesen rendezettnek kell lennie,
különben hibás eredményt ad. Konstans táblát a REDEFINES-os FILLER-trükkel lehet feltölteni, a változó
hosszú táblát az OCCURS DEPENDING ON írja le. A tartományon kívüli index nem feltétlenül okoz hibát
(GnuCOBOL-ban -debug, IBM-en SSRANGE kapcsoló kell az ellenőrzéshez).

```cobol
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TABLE-DEMO.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
      * Konstans árfolyamtábla, deviza szerint RENDEZVE
       01  RATE-VALUES.
           05  FILLER  PIC X(9) VALUE "CHF039850".
           05  FILLER  PIC X(9) VALUE "EUR039210".
           05  FILLER  PIC X(9) VALUE "GBP045730".
           05  FILLER  PIC X(9) VALUE "USD035480".
       01  RATE-TABLE REDEFINES RATE-VALUES.
           05  RATE-ENTRY OCCURS 4 TIMES
                   ASCENDING KEY IS RATE-CCY
                   INDEXED BY RATE-IX.
               10  RATE-CCY     PIC X(3).
               10  RATE-HUF     PIC 9(4)V99.
      * Változó hosszú tábla: a hosszt WS-LINE-COUNT adja
       01  WS-LINE-COUNT        PIC 99 VALUE 0.
       01  ORDER-LINES.
           05  ORDER-LINE OCCURS 1 TO 50 TIMES
                   DEPENDING ON WS-LINE-COUNT
                   INDEXED BY LINE-IX.
               10  LINE-SKU     PIC X(8).
               10  LINE-QTY     PIC 9(3).
       01  WS-CCY               PIC X(3) VALUE "EUR".
       01  WS-AMOUNT            PIC 9(7)V99 VALUE 250.
       01  WS-HUF               PIC 9(9)V99.
       01  WS-OUT               PIC ZZZ,ZZZ,ZZ9.99.
       PROCEDURE DIVISION.
       MAIN-PARA.
      *    SEARCH ALL: bináris keresés a rendezett kulcson
           SEARCH ALL RATE-ENTRY
               AT END
                   DISPLAY "Ismeretlen deviza: " WS-CCY
               WHEN RATE-CCY(RATE-IX) = WS-CCY
                   COMPUTE WS-HUF ROUNDED =
                           WS-AMOUNT * RATE-HUF(RATE-IX)
                   MOVE WS-HUF TO WS-OUT
                   DISPLAY "250 " WS-CCY " = " WS-OUT " HUF"
           END-SEARCH
           MOVE 3 TO WS-LINE-COUNT
           MOVE "SKU-0001" TO LINE-SKU(1)
           MOVE 2          TO LINE-QTY(1)
           MOVE "SKU-0002" TO LINE-SKU(2)
           MOVE 5          TO LINE-QTY(2)
           MOVE "SKU-0003" TO LINE-SKU(3)
           MOVE 1          TO LINE-QTY(3)
      *    Lineáris SEARCH: az indexet előbb be kell állítani!
           SET LINE-IX TO 1
           SEARCH ORDER-LINE
               AT END
                   DISPLAY "Nincs ilyen tétel"
               WHEN LINE-SKU(LINE-IX) = "SKU-0002"
                   DISPLAY "Megvan, mennyiség: " LINE-QTY(LINE-IX)
           END-SEARCH
           STOP RUN.
```

## Szövegkezelés: STRING, UNSTRING, INSPECT
<!-- q: Hogyan bontsak szét, fűzzek össze és alakítsak át szövegeket COBOL-ban? -->
<!-- tags: string, unstring, inspect, reference modification, numval, trim, upper-case, csv parsing -->

A fix hosszú mezők miatt a szövegkezelés külön utasításokkal történik: az UNSTRING elválasztó mentén
több mezőre bont (CSV), a STRING összefűz (a DELIMITED BY SPACE a záró szóközöket levágja, a POINTER a
következő írási pozíciót követi, az ON OVERFLOW a túl rövid célmezőt jelzi), az INSPECT pedig számlál és
cserél. A referencia-módosítás (mező(kezdet:hossz)) részstringet ad, az intrinsic függvények (FUNCTION
TRIM, UPPER-CASE, NUMVAL) modern kényelmet nyújtanak. Buktató: a STRING nem törli előre a célmezőt, ezért
azt előbb SPACES-szel kell feltölteni, és az ékezetes karakterek UTF-8-ban több bájtot foglalnak.

```cobol
       IDENTIFICATION DIVISION.
       PROGRAM-ID. STRING-DEMO.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-CSV-LINE     PIC X(60)
               VALUE "4711;Billentyuzet;RAKTAR-A;12500,75".
       01  WS-FIELDS.
           05  F-ID        PIC X(10).
           05  F-NAME      PIC X(20).
           05  F-LOC       PIC X(10).
           05  F-PRICE-TXT PIC X(12).
       01  WS-FIELD-COUNT  PIC 99 VALUE 0.
       01  WS-SEMI-COUNT   PIC 99 VALUE 0.
       01  WS-PRICE        PIC 9(7)V99.
       01  WS-PRICE-OUT    PIC Z(6)9.99.
       01  WS-PTR          PIC 99 VALUE 1.
       01  WS-OUT          PIC X(60) VALUE SPACES.
       PROCEDURE DIVISION.
       MAIN-PARA.
      *    UNSTRING: szétbontás pontosvessző mentén
           UNSTRING WS-CSV-LINE DELIMITED BY ";"
               INTO F-ID F-NAME F-LOC F-PRICE-TXT
               TALLYING IN WS-FIELD-COUNT
           END-UNSTRING
      *    INSPECT: számlálás és csere (tizedesvessző -> pont)
           INSPECT WS-CSV-LINE TALLYING WS-SEMI-COUNT FOR ALL ";"
           INSPECT F-PRICE-TXT REPLACING ALL "," BY "."
      *    NUMVAL: szöveg -> szám
           COMPUTE WS-PRICE = FUNCTION NUMVAL(F-PRICE-TXT)
      *    STRING: összefűzés pozíciókövetéssel
           STRING FUNCTION TRIM(F-NAME) DELIMITED BY SIZE
                  " (" DELIMITED BY SIZE
                  F-LOC DELIMITED BY SPACE
                  ")" DELIMITED BY SIZE
               INTO WS-OUT
               WITH POINTER WS-PTR
               ON OVERFLOW DISPLAY "A célmező túl rövid"
           END-STRING
      *    Referencia-módosítás: mező(kezdet:hossz)
           DISPLAY "Cikkszám eleje: " WS-CSV-LINE(1:4)
           DISPLAY "Mezők: " WS-FIELD-COUNT
                   "  Elválasztók: " WS-SEMI-COUNT
           DISPLAY "Leírás: " WS-OUT(1:WS-PTR - 1)
           MOVE WS-PRICE TO WS-PRICE-OUT
           DISPLAY "Ár: " WS-PRICE-OUT
           DISPLAY "Nagybetűs: " FUNCTION UPPER-CASE(F-NAME)
           STOP RUN.
```

## Alprogramok: CALL, LINKAGE SECTION, BY REFERENCE és BY CONTENT
<!-- q: Hogyan hívjak alprogramot COBOL-ban, és hogyan adjak át neki paramétereket? -->
<!-- tags: call, subprogram, linkage section, using, by reference, by content, return-code, goback, modularization -->

A CALL egy külön fordított (vagy azonos forrásban END PROGRAM-mal elválasztott) programot hív; a
paraméterek alapból BY REFERENCE adódnak át, vagyis a hívott a hívó memóriáján dolgozik, a BY CONTENT
másolatot ad, így az eredeti védett. A hívott program a LINKAGE SECTION-ben írja le a kapott
paramétereket, és a PROCEDURE DIVISION USING sorrendje egyezik a hívóéval; a szerkezetnek bájtra pontosan
meg kell egyeznie, különben a mezők elcsúsznak. Az alprogram GOBACK-kel tér vissza (a STOP RUN az egész
futást leállítaná), a hibakódot a RETURN-CODE speciális regiszterben adja vissza. A közös rekordleírásokat
COPY könyvtárakban (copybook) érdemes tartani, hogy a hívó és a hívott ugyanazt a szerkezetet használja.

```cobol
       IDENTIFICATION DIVISION.
       PROGRAM-ID. MAIN-CALLER.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
      * Élesben közös copybookból: COPY LOANREC.
       01  WS-LOAN.
           05  WS-PRINCIPAL      PIC 9(9)V99  VALUE 5000000.
           05  WS-ANNUAL-RATE    PIC 9V9(6)   VALUE 0.065.
           05  WS-MONTHS         PIC 9(3)     VALUE 120.
       01  WS-PAYMENT            PIC 9(9)V99  VALUE 0.
       01  WS-OUT                PIC ZZZ,ZZZ,ZZ9.99.
       PROCEDURE DIVISION.
       MAIN-PARA.
      *    BY CONTENT: másolat; BY REFERENCE: a hívott írhatja
           CALL "LOAN-CALC" USING BY CONTENT WS-LOAN
                                  BY REFERENCE WS-PAYMENT
               ON EXCEPTION
                   DISPLAY "LOAN-CALC nem található"
           END-CALL
           IF RETURN-CODE NOT = 0
               DISPLAY "Hiba, kód: " RETURN-CODE
           ELSE
               MOVE WS-PAYMENT TO WS-OUT
               DISPLAY "Havi törlesztő: " WS-OUT
           END-IF
           STOP RUN.
       END PROGRAM MAIN-CALLER.

       IDENTIFICATION DIVISION.
       PROGRAM-ID. LOAN-CALC.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-R                  COMP-2.
       01  WS-FACTOR             COMP-2.
       LINKAGE SECTION.
      * Bájtra pontosan egyeznie kell a hívó szerkezetével!
       01  LK-LOAN.
           05  LK-PRINCIPAL      PIC 9(9)V99.
           05  LK-ANNUAL-RATE    PIC 9V9(6).
           05  LK-MONTHS         PIC 9(3).
       01  LK-PAYMENT            PIC 9(9)V99.
       PROCEDURE DIVISION USING LK-LOAN LK-PAYMENT.
       CALC-PARA.
           IF LK-MONTHS = 0 OR LK-ANNUAL-RATE = 0
               MOVE 8 TO RETURN-CODE
               GOBACK
           END-IF
      *    Annuitás: P * r / (1 - (1 + r) ** -n)
           COMPUTE WS-R = LK-ANNUAL-RATE / 12
           COMPUTE WS-FACTOR = (1 + WS-R) ** (0 - LK-MONTHS)
           COMPUTE LK-PAYMENT ROUNDED =
                   LK-PRINCIPAL * WS-R / (1 - WS-FACTOR)
           MOVE 0 TO RETURN-CODE
           GOBACK.
       END PROGRAM LOAN-CALC.
```

## Kontroll-break riport: a klasszikus batch minta
<!-- q: Hogyan készítsek csoportonkénti részösszegeket egy rendezett fájlból COBOL-ban (control break)? -->
<!-- tags: control break, batch, report, subtotal, sorted input, sort, grouping, mainframe -->

A kontroll-break a kötegelt feldolgozás alapmintája: a bemenet a csoportosító kulcs (például fiók) szerint
rendezett, a program soronként halad, és amikor a kulcs megváltozik, kiírja és lenullázza az előző csoport
részösszegét, végül a végösszeget. A rendezést a futás előtt a COBOL SORT utasítása vagy egy DFSORT/
SyncSort JCL-lépés végzi; rendezetlen bemenettel ugyanaz a csoport többször jelenik meg. A leggyakoribb
hiba, hogy a ciklus után az utolsó csoportot elfelejtik lezárni, illetve az üres bemenetet nem kezelik.
Az összegzőket pontos COMP-3 típussal és a lehetséges legnagyobb összegre méretezve deklaráld.

```cobol
       IDENTIFICATION DIVISION.
       PROGRAM-ID. SALES-REPORT.
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT SALES-FILE ASSIGN TO "sales_sorted.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS WS-FS.
       DATA DIVISION.
       FILE SECTION.
       FD  SALES-FILE.
       01  SALES-REC.
           05  SR-BRANCH         PIC X(4).
           05  SR-PRODUCT        PIC X(10).
           05  SR-AMOUNT         PIC 9(7)V99.
       WORKING-STORAGE SECTION.
       01  WS-FS                 PIC XX.
           88  FS-EOF                    VALUE "10".
       01  WS-PREV-BRANCH        PIC X(4)  VALUE SPACES.
       01  WS-BRANCH-TOTAL       PIC 9(9)V99  COMP-3 VALUE 0.
       01  WS-GRAND-TOTAL        PIC 9(11)V99 COMP-3 VALUE 0.
       01  WS-SUB-LINE.
           05  FILLER            PIC X(8)  VALUE "  Fiók ".
           05  SUB-BRANCH        PIC X(4).
           05  FILLER            PIC X(12) VALUE " összesen: ".
           05  SUB-AMOUNT        PIC ZZZ,ZZZ,ZZ9.99.
       01  WS-GRAND-OUT          PIC Z,ZZZ,ZZZ,ZZ9.99.
       PROCEDURE DIVISION.
       MAIN-PARA.
           OPEN INPUT SALES-FILE
           PERFORM READ-SALES
           IF NOT FS-EOF
               MOVE SR-BRANCH TO WS-PREV-BRANCH
           END-IF
           PERFORM UNTIL FS-EOF
      *        Kulcsváltás: az előző csoport lezárása
               IF SR-BRANCH NOT = WS-PREV-BRANCH
                   PERFORM BRANCH-BREAK
                   MOVE SR-BRANCH TO WS-PREV-BRANCH
               END-IF
               ADD SR-AMOUNT TO WS-BRANCH-TOTAL
               PERFORM READ-SALES
           END-PERFORM
      *    Az utolsó csoportot is le kell zárni (gyakori hiba!)
           IF WS-PREV-BRANCH NOT = SPACES
               PERFORM BRANCH-BREAK
           END-IF
           MOVE WS-GRAND-TOTAL TO WS-GRAND-OUT
           DISPLAY "Végösszeg: " WS-GRAND-OUT
           CLOSE SALES-FILE
           STOP RUN.

       READ-SALES.
           READ SALES-FILE
               AT END SET FS-EOF TO TRUE
           END-READ.

       BRANCH-BREAK.
           MOVE WS-PREV-BRANCH TO SUB-BRANCH
           MOVE WS-BRANCH-TOTAL TO SUB-AMOUNT
           DISPLAY WS-SUB-LINE
           ADD WS-BRANCH-TOTAL TO WS-GRAND-TOTAL
           MOVE 0 TO WS-BRANCH-TOTAL.
```
