# Lisp (Common Lisp, Scheme, Racket)
<!-- tech: lisp -->
<!-- aliases: common lisp, scheme, racket, cl, sbcl, guile, chicken, s-expression -->

A Lisp a második legrégebbi magas szintű nyelvcsalád (1958): a programkód maga is adat, zárójelezett listák, ún. S-kifejezések formájában (homoikonikusság), ezért a makrók a teljes nyelvet használhatják kódgenerálásra, és új nyelvi szerkezetek építhetők. A három fő dialektus: a **Common Lisp** (ANSI szabvány, ipari erejű, natív fordítók mint az SBCL, CLOS objektumrendszer, egyedülálló condition/restart hibakezelés), a **Scheme** (minimalista, garantált farokhívás-optimalizálás, first-class continuation-ök, higiénikus makrók — oktatás, nyelvkutatás) és a **Racket** (Scheme-ből nőtt „nyelvépítő nyelv” modulokkal, contractokkal, `#lang` DSL-ekkel). Dinamikusan típusosak, GC-vel, REPL-központú interaktív fejlesztéssel. Kiválóak DSL-ekhez, szimbolikus számításhoz, prototípushoz, fordítóépítéshez és oktatáshoz; kisebb az ökoszisztémájuk és a munkaerőpiacuk, mint a mainstream nyelveké.

## S-kifejezések: a kód mint adat
<!-- q: Mik azok az S-kifejezések Lispben és hogyan dolgozhatok a kóddal adatként? -->
<!-- tags: s-expressions, cons cells, lists, quote, symbolic computation, homoiconicity, common lisp -->

Lispben minden kifejezés egy S-kifejezés: atom (szám, szimbólum, string) vagy lista, ahol a lista `cons` cellákból épül (`car` = első elem, `cdr` = maradék, a vége `nil`). A függvényhívás is lista: `(+ 1 2)` — az első elem az operátor, ez a prefix jelölés teszi egységessé és könnyen elemezhetővé a szintaxist. A `quote` (`'`) megakadályozza a kiértékelést, így `'(+ x 1)` egy háromelemű lista, amelyet programmal lehet bejárni, átalakítani, majd akár `eval`-lal futtatni — ez a szimbolikus számítás (deriválás, egyszerűsítés, fordítók) alapja. Buktató: a quote-olt literál listák konstansok, módosításuk (`setf`, `nreverse`) nem definiált viselkedés; az `eq` szimbólumokra, az `eql` számokra/karakterekre, az `equal` szerkezeti egyezésre való.

```lisp
;; Cons cellák és listák
(cons 1 (cons 2 nil))          ; => (1 2)
(cons 1 2)                     ; => (1 . 2)  pontozott pár
(car '(a b c))                 ; => A
(cdr '(a b c))                 ; => (B C)
(list '+ 1 2)                  ; => (+ 1 2) — adat, nem hívás
(eval (list '+ 1 2))           ; => 3      — ugyanez kódként

;; Szimbolikus deriválás: a bemenet és a kimenet is S-kifejezés
(defun simplify (expr)
  "Aritmetikai kifejezés egyszerűsítése rekurzívan."
  (if (atom expr)
      expr
      (let ((op (first expr))
            (a (simplify (second expr)))
            (b (simplify (third expr))))
        (cond ((and (numberp a) (numberp b)) (funcall op a b))   ; konstans összevonás
              ((and (eq op '+) (eql a 0)) b)
              ((and (eq op '+) (eql b 0)) a)
              ((and (eq op '*) (or (eql a 0) (eql b 0))) 0)
              ((and (eq op '*) (eql a 1)) b)
              ((and (eq op '*) (eql b 1)) a)
              (t (list op a b))))))

(defun deriv (expr var)
  "d(expr)/d(var), + és * műveletekre."
  (cond ((numberp expr) 0)
        ((symbolp expr) (if (eq expr var) 1 0))
        (t (destructuring-bind (op a b) expr
             (ecase op
               (+ `(+ ,(deriv a var) ,(deriv b var)))
               ;; szorzat szabály: (ab)' = a b' + a' b
               (* `(+ (* ,a ,(deriv b var)) (* ,(deriv a var) ,b))))))))

(defun evaluate (expr env)
  "Kiértékelés változó-környezettel (asszociációs lista)."
  (cond ((numberp expr) expr)
        ((symbolp expr)
         (let ((binding (assoc expr env)))
           (if binding (cdr binding) (error "Ismeretlen változó: ~a" expr))))
        (t (apply (first expr) (mapcar (lambda (e) (evaluate e env)) (rest expr))))))

(let* ((f '(+ (* x x) (* 3 x)))               ; f(x) = x^2 + 3x
       (df (simplify (deriv f 'x))))            ; f'(x)
  (format t "f'(x) = ~s~%" df)                  ; (+ (+ X X) 3)
  (format t "f'(2) = ~a~%" (evaluate df '((x . 2)))))   ; 7
```

## Makrók és homoikonikusság (Common Lisp)
<!-- q: Hogyan írjak makrót Common Lispben backquote-tal és gensym-mel? -->
<!-- tags: macros, defmacro, backquote, gensym, macroexpand, dsl, homoiconicity, common lisp -->

Mivel a Lisp-kód lista, a makró egyszerűen egy fordítási időben futó függvény, amely a kiértékeletlen argumentum-formákat kapja meg, és új kódot (listát) ad vissza; ezt a fordító a hívás helyére illeszti. A backquote (`` ` ``) sablont ad, a `,` beilleszt egy értéket, a `,@` kiterít egy listát. A Common Lisp makrói nem higiénikusak, ezért a makró saját segédváltozóit `gensym`-mel kell generálni, különben „elkaphatják” a hívó azonos nevű változóit. A makrókkal új vezérlési szerkezetek és teljes DSL-ek építhetők (a `loop`, `defclass`, `with-open-file` is makró). Buktatók: az argumentum többszöri beillesztése többszöri kiértékelést okoz; a makró nem first-class függvény; fejlesztéskor mindig nézd meg a `macroexpand-1` kimenetét.

```lisp
;; Időmérő makró: a START gensym, így nem ütközik a hívó változóival
(defmacro with-timing ((label) &body body)
  (let ((start (gensym "START")))
    `(let ((,start (get-internal-real-time)))
       (multiple-value-prog1 (progn ,@body)        ; a törzs értékeit adja vissza
         (format t "~a: ~,2f ms~%" ,label
                 (/ (* 1000.0 (- (get-internal-real-time) ,start))
                    internal-time-units-per-second))))))

;; ROSSZ: az argumentum kétszer értékelődik ki
(defmacro square-bad (x) `(* ,x ,x))
;; JÓ: egyszer kiértékelve, gensym változóba kötve
(defmacro square (x)
  (let ((v (gensym)))
    `(let ((,v ,x)) (* ,v ,v))))

(let ((i 0)) (print (list (square-bad (incf i)) i)))   ; (2 2) — 1*2, i kétszer nőtt
(let ((i 0)) (print (list (square (incf i)) i)))       ; (1 1)

;; Új vezérlési szerkezet: while
(defmacro while (test &body body)
  `(loop while ,test do (progn ,@body)))

;; DSL: deklaratív validátor-függvény generálása fordítási időben
(defmacro define-validator (name &body rules)
  `(defun ,name (plist)
     (let ((errors '()))
       ,@(loop for (field pred message) in rules
               collect `(unless (funcall ,pred (getf plist ,field))
                          (push (cons ,field ,message) errors)))
       (nreverse errors))))

(define-validator validate-user
  (:name #'stringp "a név kötelező szöveg")
  (:age (lambda (a) (and (integerp a) (<= 0 a 150))) "az életkor 0 és 150 közötti egész")
  (:email (lambda (e) (and (stringp e) (find #\@ e))) "érvénytelen e-mail"))

(print (validate-user '(:name "Anna" :age 31 :email "anna@example.com")))  ; NIL
(print (validate-user '(:age 200 :email "rossz")))                         ; három hiba

(let ((n 3))
  (with-timing ("visszaszámlálás")
    (while (> n 0) (format t "~a " n) (decf n))))

(print (macroexpand-1 '(square (incf i))))   ; a generált kód megtekintése
```

## Higiénikus makrók Schemeben (syntax-rules)
<!-- q: Hogyan írjak higiénikus makrót Schemeben syntax-rules-szal? -->
<!-- tags: hygienic macros, syntax-rules, define-syntax, scheme, racket, pattern-based macros -->

A Scheme makrórendszere *higiénikus*: a `syntax-rules` mintaillesztéses átírási szabályokat ad (`minta → sablon`), és a rendszer automatikusan átnevezi a makró által bevezetett azonosítókat, így azok soha nem ütköznek a hívó változóival, a makróban használt globális nevek (`let`, `if`) pedig a definíció helyén érvényes jelentésüket tartják meg — nincs szükség `gensym`-re. Az `...` (ellipszis) ismétlődő mintát jelöl, a literál lista (`(in from to)`) kulcsszavakat engedélyez. Rekurzív makrók is írhatók. Buktató: a `syntax-rules` csak mintaalapú átírásra képes (számolni, tetszőleges kódot futtatni nem tud) — ehhez a `syntax-case` (R6RS) vagy a Racket `syntax-parse` kell, és szándékos névelkapás (anaforikus makró) csak ezekkel oldható meg.

```scheme
;; swap!: a tmp a makró saját azonosítója — a hívó tmp nevű változója sem zavarja
(define-syntax swap!
  (syntax-rules ()
    ((_ a b)
     (let ((tmp a))
       (set! a b)
       (set! b tmp)))))

(define tmp 1)
(define y 2)
(swap! tmp y)                 ; higiénia: helyesen cserél
(display (list tmp y))        ; (2 1)
(newline)

;; Rekurzív makró ellipszissel: rövidzáras or, minden kifejezés legfeljebb egyszer fut
(define-syntax my-or
  (syntax-rules ()
    ((_) #f)
    ((_ e) e)
    ((_ e rest ...)
     (let ((t e))             ; a t nem ütközik a hívó t-jével
       (if t t (my-or rest ...))))))

(define t 5)
(display (my-or #f t))        ; 5 — a hívó t változója, nem a makróé
(newline)

;; Kulcsszavas ciklus-DSL: a literálok (in from to) a minta részei
(define-syntax for
  (syntax-rules (in from to)
    ((_ x in lst body ...)
     (for-each (lambda (x) body ...) lst))
    ((_ x from a to b body ...)
     (let loop ((x a))
       (when (<= x b)
         body ...
         (loop (+ x 1)))))))

(for fruit in '(alma körte szilva)
  (display fruit) (display " "))
(newline)

(define loop 'felhasználói-érték)  ; a makró belső "loop"-ja ettől nem sérül
(for i from 1 to 5
  (display (* i i)) (display " "))
(newline)

;; while ciklus makróként (R7RS-ben nincs beépítve)
(define-syntax while
  (syntax-rules ()
    ((_ cond body ...)
     (let lp () (when cond body ... (lp))))))

(define n 3)
(while (> n 0) (display n) (set! n (- n 1)))
(newline)
```

## CLOS: osztályok, generikus függvények, multiple dispatch
<!-- q: Hogyan működik a CLOS objektumrendszer Common Lispben (defclass, defgeneric, defmethod)? -->
<!-- tags: clos, defclass, defgeneric, defmethod, multiple dispatch, call-next-method, print-object -->

A CLOS (Common Lisp Object System) a metódusokat nem az osztályokhoz, hanem *generikus függvényekhez* köti: a `defgeneric` deklarálja a műveletet, a `defmethod`-ok pedig az argumentumok osztályai szerint specializálnak — *az összes* argumentum szerint (multiple dispatch), nem csak az első (`this`) szerint. Így pl. egy `combine` művelet külön implementációt kaphat (szám, szám), (string, string) és (string, szám) párokra. Az osztályok (`defclass`) slotjai `:initarg`, `:initform`, `:accessor` opciókat kapnak, többszörös öröklés támogatott (C3-szerű linearizációval), a `call-next-method` a következő, kevésbé specifikus metódust hívja. Buktató: a slotok alapból nem típusellenőrzöttek, és az osztály futás közbeni újradefiniálása a meglévő példányokat is frissíti — REPL-ben hasznos, élesben figyelni kell rá.

```lisp
(defclass account ()
  ((id      :initarg :id      :reader account-id)
   (owner   :initarg :owner   :accessor owner)
   (balance :initarg :balance :initform 0 :accessor balance)))

(defclass savings-account (account)
  ((max-withdrawal :initarg :max-withdrawal :initform 1000 :reader max-withdrawal)))

(defgeneric withdraw (account amount)
  (:documentation "Pénz felvétele; hibát jelez, ha nem engedélyezett."))

(defmethod withdraw ((acc account) amount)
  (when (> amount (balance acc))
    (error "Nincs fedezet: ~a < ~a" (balance acc) amount))
  (decf (balance acc) amount))

;; Specializált metódus: saját ellenőrzés, majd az általános viselkedés
(defmethod withdraw ((acc savings-account) amount)
  (when (> amount (max-withdrawal acc))
    (error "Megtakarítási számláról egyszerre max ~a vehető fel" (max-withdrawal acc)))
  (call-next-method))

;; Saját nyomtatási forma a REPL-hez és a format ~a-hoz
(defmethod print-object ((acc account) stream)
  (print-unreadable-object (acc stream :type t)
    (format stream "~a ~a: ~a Ft" (account-id acc) (owner acc) (balance acc))))

;; Multiple dispatch: MINDKÉT argumentum osztálya számít
(defgeneric combine (a b))
(defmethod combine ((a number) (b number)) (+ a b))
(defmethod combine ((a string) (b string)) (concatenate 'string a b))
(defmethod combine ((a string) (b number)) (format nil "~a×~a" a b))
(defmethod combine ((a list) (b list)) (append a b))
(defmethod combine (a b) (list :nem-kombinálható a b))   ; alapeset (T, T)

(let ((s (make-instance 'savings-account :id 1 :owner "Anna" :balance 5000)))
  (withdraw s 800)
  (print s)                                       ; #<SAVINGS-ACCOUNT 1 Anna: 4200 Ft>
  (handler-case (withdraw s 2000)
    (error (e) (format t "~%hiba: ~a~%" e))))

(print (list (combine 1 2) (combine "foo" "bar") (combine "kód" 3)
             (combine '(1) '(2 3)) (combine 1 "x")))
```

## CLOS metódus-kombináció: :before, :after, :around
<!-- q: Hogyan használjam a :before, :after és :around metódusokat CLOS-ban? -->
<!-- tags: clos, method combination, before, after, around, mixins, aspect oriented, initialize-instance -->

A CLOS standard metódus-kombinációja egy generikus függvény hívásakor nem egyetlen metódust futtat, hanem egy összeállított láncot: először az `:around` metódusokat (legspecifikusabbtól), amelyek `call-next-method`-dal engedik tovább a vezérlést; aztán az összes alkalmazható `:before` metódust (legspecifikusabbtól), a legspecifikusabb elsődleges metódust, végül az `:after`-öket (fordított sorrendben). Ezzel naplózás, gyorsítótárazás, jogosultság-ellenőrzés vagy validálás *mixin* osztályokkal, az eredeti kód módosítása nélkül adható hozzá (beépített aspektus-orientáltság). Az `initialize-instance :after` a konstruktor utáni validálás bevett helye, és alternatív kombinációk is vannak (pl. `+`, `list`, `progn`). Buktató: az `:around` metódus, amely nem hívja a `call-next-method`-ot, az egész láncot elnyeli.

```lisp
(defclass service ()
  ((name  :initarg :name :reader name)
   (calls :initform 0 :accessor calls)))

;; Validálás a példányosítás után
(defmethod initialize-instance :after ((svc service) &key)
  (unless (slot-boundp svc 'name)
    (error "A szolgáltatás neve kötelező")))

(defgeneric handle (svc request))

(defmethod handle ((svc service) request)               ; elsődleges metódus
  (format nil "~a feldolgozta: ~a" (name svc) request))

(defmethod handle :before ((svc service) request)        ; előtte: számlálás, napló
  (incf (calls svc))
  (format t "[log] ~a <- ~a~%" (name svc) request))

(defmethod handle :after ((svc service) request)         ; utána
  (declare (ignore request))
  (format t "[log] ~a kész (~a hívás)~%" (name svc) (calls svc)))

(defmethod handle :around ((svc service) request)        ; körülötte: őrfeltétel
  (if (null request)
      "üres kérés elutasítva"                            ; nincs call-next-method: a lánc nem fut
      (call-next-method)))

;; Mixin-szerű bővítés: cache réteg egy alosztály :around metódusában
(defclass cached-service (service)
  ((cache :initform (make-hash-table :test #'equal) :reader cache)))

(defmethod handle :around ((svc cached-service) request)
  (multiple-value-bind (hit found) (gethash request (cache svc))
    (if found
        (format nil "~a (cache-ből)" hit)
        (setf (gethash request (cache svc)) (call-next-method)))))

(let ((svc (make-instance 'cached-service :name "árazó")))
  (print (handle svc "termék-42"))    ; teljes lánc: before, primary, after
  (print (handle svc "termék-42"))    ; cache találat: before/after nem fut
  (print (handle svc nil)))

;; Alternatív kombináció: az összes alkalmazható metódus eredménye összeadódik
(defgeneric price (item) (:method-combination +))
(defclass product () ())
(defclass taxed () ())
(defclass shipped () ())
(defclass book (taxed shipped product) ())
(defmethod price + ((x product)) 4000)   ; alapár
(defmethod price + ((x taxed)) 200)      ; adó
(defmethod price + ((x shipped)) 990)    ; szállítás
(print (price (make-instance 'book)))    ; 5190
```

## Condition system: hibák jelzése és kezelése
<!-- q: Hogyan működik a Common Lisp condition rendszere (define-condition, handler-case, unwind-protect)? -->
<!-- tags: conditions, error handling, define-condition, handler-case, unwind-protect, signal, warn, common lisp -->

A Common Lisp hibakezelése általánosabb a kivételeknél: a *condition* bármilyen jelzés lehet (hiba, figyelmeztetés, információ), amelyet a `signal`/`warn`/`error` küld, és a hívási láncban feljebb lévő handlerek kezelnek. A `define-condition` saját condition-osztályt definiál slotokkal és olvasható `:report` szöveggel, a `handler-case` a megszokott kivételkezeléshez hasonlóan *visszatekeri* a stacket a kezelőig, az `unwind-protect` pedig garantálja a takarító kód lefutását (mint a `finally`). Fontos különbség: a `warn` és a `signal` kezeletlenül is továbbengedi a futást, az `error` viszont a debuggerbe visz. Buktató: a `handler-case` a stack visszatekerésével elveszíti a hiba helyének kontextusát — ha ott akarsz dönteni, restartokat és `handler-bind`-ot használj (lásd a következő szakaszt).

```lisp
;; Saját condition-hierarchia olvasható hibaüzenettel
(define-condition config-error (error)
  ((key :initarg :key :reader config-key))
  (:report (lambda (c stream)
             (format stream "Konfigurációs hiba a(z) ~a kulcsnál" (config-key c)))))

(define-condition missing-key (config-error) ()
  (:report (lambda (c stream) (format stream "Hiányzó kulcs: ~a" (config-key c)))))

(define-condition invalid-value (config-error)
  ((value :initarg :value :reader bad-value))
  (:report (lambda (c stream)
             (format stream "Érvénytelen érték a(z) ~a kulcsnál: ~s" (config-key c) (bad-value c)))))

(defun get-port (config)
  (let ((raw (getf config :port)))
    (cond ((null raw) (error 'missing-key :key :port))
          ((not (and (integerp raw) (< 0 raw 65536)))
           (error 'invalid-value :key :port :value raw))
          ((< raw 1024)
           (warn "A(z) ~a privilegizált port, root jog kellhet" raw)   ; nem állítja meg a futást
           raw)
          (t raw))))

;; handler-case: típus szerinti kezelés, a specifikusabb előre
(defun safe-port (config)
  (handler-case (get-port config)
    (missing-key () 8080)                                  ; alapértelmezés
    (config-error (e) (format t "~a~%" e) nil)))           ; minden más konfig-hiba

;; unwind-protect: a takarítás hiba esetén is lefut
(defun process-with-resource ()
  (let ((resource (list :open)))
    (unwind-protect
         (progn (format t "erőforrás használatban~%")
                (error "váratlan hiba feldolgozás közben"))
      (setf (first resource) :closed)
      (format t "erőforrás lezárva: ~a~%" resource))))

(print (safe-port '(:port 443)))        ; 443 + figyelmeztetés
(print (safe-port '()))                 ; 8080
(print (safe-port '(:port "abc")))      ; hibaüzenet, NIL
(print (handler-case (process-with-resource)
         (error (e) (format nil "elkapva: ~a" e))))
;; ignore-errors: gyors megoldás, (values nil condition)-t ad hiba esetén
(print (multiple-value-list (ignore-errors (parse-integer "12x"))))
```

## Restartok: helyreállítás a hiba helyén
<!-- q: Mik azok a restartok Common Lispben és miben jobbak a kivételeknél? -->
<!-- tags: restarts, restart-case, handler-bind, invoke-restart, use-value, error recovery, condition system -->

A restart a Common Lisp condition rendszerének különlegessége: az alacsony szintű kód (ahol a hiba keletkezik) `restart-case`-szel *felkínál* helyreállítási lehetőségeket (kihagyás, helyettesítő érték, újrapróbálás), a magas szintű kód pedig `handler-bind`-dal *eldönti*, melyiket használja — a stack visszatekerése nélkül, így a feldolgozás a hiba helyén folytatódhat. Ez szétválasztja a „hogyan lehet helyreállni” (alsó réteg tudja) és a „melyik helyreállítás a helyes” (felső réteg tudja) kérdését, amit kivételekkel nem lehet szépen megoldani. Interaktív használatban a debugger listázza a restartokat, és a fejlesztő választhat közülük. Buktató: a `handler-bind` kezelője visszatérés esetén *továbbengedi* a condition-t (nem kezeli le), ezért ott `invoke-restart` vagy nem lokális kilépés kell.

```lisp
(define-condition bad-record (error)
  ((line :initarg :line :reader record-line)
   (text :initarg :text :reader record-text))
  (:report (lambda (c s)
             (format s "Hibás rekord a(z) ~a. sorban: ~s" (record-line c) (record-text c)))))

;; Alsó réteg: CSV-szerű "név,mennyiség" sor bontása, restartok felkínálásával
(defun parse-record (line-no text)
  (restart-case
      (let* ((pos (position #\, text))
             (qty (and pos (parse-integer text :start (1+ pos) :junk-allowed t))))
        (unless qty
          (error 'bad-record :line line-no :text text))
        (cons (subseq text 0 pos) qty))
    (skip-record ()
      :report "A sor kihagyása"
      nil)
    (use-value (value)
      :report "Helyettesítő érték megadása"
      value)
    (retry-with (new-text)
      :report "Újrapróbálás javított szöveggel"
      (parse-record line-no new-text))))

;; Középső réteg: semmit nem tud a hibakezelési szabályról
(defun parse-all (lines)
  (loop for text in lines
        for i from 1
        for rec = (parse-record i text)
        when rec collect rec))

(defparameter *input* '("alma,3" "hibás sor" "körte,x" "szilva,5"))

;; Felső réteg, 1. szabály: hibás sorok kihagyása
(print (handler-bind ((bad-record (lambda (c) (declare (ignore c))
                                    (invoke-restart 'skip-record))))
         (parse-all *input*)))       ; (("alma" . 3) ("szilva" . 5))

;; 2. szabály: helyettesítés 0 mennyiséggel, a szöveg megtartásával
(print (handler-bind ((bad-record (lambda (c)
                                    (invoke-restart 'use-value (cons (record-text c) 0)))))
         (parse-all *input*)))

;; 3. szabály: javítási kísérlet, ha van vessző, egyébként kihagyás
(print (handler-bind ((bad-record
                        (lambda (c)
                          (let ((txt (record-text c)))
                            (if (find #\, txt)
                                (invoke-restart 'retry-with
                                                (concatenate 'string (subseq txt 0 (position #\, txt)) ",1"))
                                (invoke-restart 'skip-record))))))
         (parse-all *input*)))       ; a "körte,x" -> ("körte" . 1)
```

## Farokhívás és iteráció Schemeben
<!-- q: Mit jelent a garantált farokhívás-optimalizálás Schemeben és hogyan írjak vele ciklusokat? -->
<!-- tags: tail calls, tail call optimization, named let, recursion, iteration, state machine, scheme -->

A Scheme szabvány *megköveteli* a megfelelő farokhívás-kezelést (proper tail calls): ha egy függvényhívás az utolsó művelet (farokpozícióban van), a hívó stack-kerete újrahasznosul, így a rekurzió konstans memóriában fut és a ciklus egyszerűen egy önmagát farokpozícióban hívó függvény. Ezért Schemeben nincs szükség külön ciklus-utasításra: a named `let` a szokásos ciklusforma, a kölcsönösen rekurzív függvények pedig állapotgépet alkotnak, ahol minden állapot egy függvény. Common Lispben ez nem garantált (az SBCL optimalizál, de debug beállításoktól függ), ezért ott a `loop`/`do` az idiomatikus. Buktató: a `(+ 1 (f x))` alakú hívás *nem* farokhívás (az összeadás még hátravan) — nagy bemeneten akkumulátoros átírás kell.

```scheme
;; NEM farokrekurzív: minden hívás után még hátravan egy összeadás -> stack nő
(define (sum-naive lst)
  (if (null? lst) 0 (+ (car lst) (sum-naive (cdr lst)))))

;; Farokrekurzív named let-tel: konstans stack, valójában egy ciklus
(define (sum-list lst)
  (let loop ((xs lst) (acc 0))
    (if (null? xs)
        acc
        (loop (cdr xs) (+ acc (car xs))))))

;; Kölcsönös farokrekurzió: egymillió mélység sem tölti meg a stacket
(define (my-even? n) (if (= n 0) #t (my-odd? (- n 1))))
(define (my-odd? n)  (if (= n 0) #f (my-even? (- n 1))))

;; Állapotgép függvényekkel: szószámláló, két állapot (szóközben / szóban)
(define (count-words str)
  (let ((n (string-length str)))
    (define (in-space i count)
      (cond ((= i n) count)
            ((char-whitespace? (string-ref str i)) (in-space (+ i 1) count))
            (else (in-word (+ i 1) (+ count 1)))))     ; állapotváltás = farokhívás
    (define (in-word i count)
      (cond ((= i n) count)
            ((char-whitespace? (string-ref str i)) (in-space (+ i 1) count))
            (else (in-word (+ i 1) count))))
    (in-space 0 0)))

;; Gyorshatványozás akkumulátorral, farokrekurzívan
(define (fast-expt base e)
  (let loop ((b base) (e e) (acc 1))
    (cond ((= e 0) acc)
          ((even? e) (loop (* b b) (quotient e 2) acc))
          (else (loop b (- e 1) (* acc b))))))

(display (sum-list (iota 1000000)))          (newline)   ; iota: SRFI-1 / a legtöbb Schemeben
(display (my-even? 1000001))                 (newline)   ; #f, stack overflow nélkül
(display (count-words "  a Scheme   farokhívás  garantált ")) (newline)   ; 4
(display (fast-expt 2 100))                  (newline)
```

## Continuation-ök: call/cc
<!-- q: Mi az a call/cc Schemeben és mire használhatók a continuation-ök? -->
<!-- tags: continuations, call/cc, call-with-current-continuation, early exit, generators, control flow, scheme -->

A continuation „a számítás hátralevő része” egy adott ponton; a `call-with-current-continuation` (`call/cc`) ezt first-class értékként (egyargumentumú függvényként) adja át, és amikor később meghívjuk, a program *oda tér vissza*, ahol a continuation-t elkaptuk, a megadott értékkel. Ezzel a nyelvben magában implementálható a korai kilépés (return/break), a kivételkezelés, a generátorok, a korutinok és a visszalépéses keresés. Elméletileg ez a legáltalánosabb vezérlési primitív, a gyakorlatban azonban nehezen követhető kódot ad; a modern ajánlás a *delimitált* continuation-ök (Racket `call/prompt`, `shift`/`reset`) használata, mert azok csak egy körülhatárolt részt fognak meg. Buktató: a teljes continuation drága lehet, és erőforrás-kezelésnél a `dynamic-wind` kell, mert a continuation-nel ki- és be lehet ugrani egy blokkba.

```scheme
;; 1) Korai kilépés: a for-each-ből "return"-nel ugrunk ki
(define (find-first pred lst)
  (call/cc
    (lambda (return)
      (for-each (lambda (x) (when (pred x) (return x))) lst)
      #f)))

(display (find-first negative? '(3 1 -4 1 -5)))   ; -4
(newline)

;; 2) Generátor: fa leveleinek lusta bejárása, két continuation váltogatásával
(define done (list 'done))                          ; egyedi végjel (eq?-val összevethető)

(define (make-leaf-generator tree)
  (define return #f)                                ; ahová a következő levelet adjuk
  (define resume-walk #f)                           ; ahol a bejárás folytatódik
  (define (walk t)
    (cond ((null? t) 'ok)
          ((pair? t) (walk (car t)) (walk (cdr t)))
          (else (call/cc
                  (lambda (k)
                    (set! resume-walk k)            ; megjegyezzük, hol tartunk
                    (return t))))))                 ; és kiugrunk a levéllel
  (lambda ()
    (call/cc
      (lambda (r)
        (set! return r)
        (if resume-walk
            (resume-walk 'tovább)                   ; folytatás az előző levél után
            (begin (walk tree) (return done)))))))

;; Same-fringe: két különböző alakú fa leveleinek sorrendje egyezik-e?
;; A generátorok miatt nem kell a teljes levéllistát felépíteni.
(define (same-fringe? t1 t2)
  (let ((g1 (make-leaf-generator t1))
        (g2 (make-leaf-generator t2)))
    (let loop ()
      (let ((a (g1)) (b (g2)))
        (cond ((and (eq? a done) (eq? b done)) #t)
              ((or (eq? a done) (eq? b done)) #f)
              ((equal? a b) (loop))
              (else #f))))))

(display (same-fringe? '(1 (2 3) ((4))) '((1 2) (3 4))))   ; #t
(newline)
(display (same-fringe? '(1 (2 3)) '(1 (3 2))))             ; #f
(newline)

;; 3) dynamic-wind: be- és kilépéskor lefutó kód continuation-ugrásoknál is
(call/cc
  (lambda (escape)
    (dynamic-wind
      (lambda () (display "[belépés]"))
      (lambda () (escape 'kiugrás) (display "ez nem fut le"))
      (lambda () (display "[kilépés]") (newline)))))
```

## Lezárások és magasabbrendű függvények
<!-- q: Hogyan használjam a lezárásokat (closure) és a magasabbrendű függvényeket Common Lispben? -->
<!-- tags: closures, higher-order functions, lambda, funcall, lisp-2, labels, flet, memoization -->

A Lisp függvényei first-class értékek, és a `lambda` *lexikális lezárást* (closure) hoz létre: a függvény magával viszi a definíciója helyén látható változókat, és ezek a függvény élettartamáig megmaradnak — így privát állapot (számláló, cache) objektumok nélkül is kialakítható. A Common Lisp *Lisp-2*: a függvényeknek és a változóknak külön névtere van, ezért egy függvény-értéket `#'nev`-vel kell elkérni és `funcall`/`apply`-jal hívni (Schemeben, ami Lisp-1, közvetlenül hívható). Lokális függvényekhez a `flet` (nem rekurzív) és a `labels` (rekurzív) való. Buktató: memoizálásnál a rekurzív hívások csak akkor mennek a cache-en át, ha a globális függvénydefiníciót is lecseréled; a `loop` ciklusváltozóját elkapó closure-ök implementációtól függően ugyanazt a kötést oszthatják meg.

```lisp
;; Privát állapot lezárással: két függvény ugyanazon az n-en osztozik
(defun make-counter (&optional (start 0))
  (let ((n start))
    (values (lambda () (incf n))           ; növelő
            (lambda () (setf n start)))))  ; visszaállító

(multiple-value-bind (next reset) (make-counter 10)
  (print (list (funcall next) (funcall next) (funcall next)))   ; (11 12 13)
  (funcall reset)
  (print (funcall next)))                                       ; 11

;; Függvénykompozíció: jobbról balra alkalmaz
(defun compose (&rest fns)
  (lambda (x) (reduce #'funcall fns :from-end t :initial-value x)))

(print (funcall (compose #'1+ (lambda (x) (* x x)) #'abs) -3))  ; (1+ (sq (abs -3))) = 10

;; Általános memoizáló burok: argumentumlista a kulcs
(defun memoize (fn)
  (let ((cache (make-hash-table :test #'equal)))
    (lambda (&rest args)
      (multiple-value-bind (value found) (gethash args cache)
        (if found
            value
            (setf (gethash args cache) (apply fn args)))))))

(declaim (notinline slow-fib))   ; a rekurzív hívás a globális definíción menjen át
(defun slow-fib (n) (if (< n 2) n (+ (slow-fib (- n 1)) (slow-fib (- n 2)))))
;; A rekurzív hívások is a cache-t használják: a globális definíciót cseréljük
(setf (symbol-function 'slow-fib) (memoize #'slow-fib))
(print (slow-fib 80))                       ; azonnal: 23416728348467685

;; labels: lokális, egymást hívó függvények (pl. mélységi bejárás)
(defun tree-depth-and-leaves (tree)
  (let ((leaves 0))
    (labels ((walk (node depth)
               (if (atom node)
                   (progn (incf leaves) depth)
                   (reduce #'max (mapcar (lambda (child) (walk child (1+ depth))) node)
                           :initial-value depth))))
      (values (walk tree 0) leaves))))

(print (multiple-value-list (tree-depth-and-leaves '(a (b c) ((d)) e))))   ; (3 5)

;; Magasabbrendű függvények: rendezés kulccsal, szűrés, redukció
(let ((people '(("Anna" . 31) ("Béla" . 25) ("Cecil" . 42))))
  (print (sort (copy-list people) #'> :key #'cdr))          ; copy-list: a sort destruktív!
  (print (remove-if-not (lambda (p) (> (cdr p) 30)) people))
  (print (reduce #'+ people :key #'cdr)))                   ; 98
```

## Hash táblák, struktúrák és a loop makró
<!-- q: Hogyan dolgozzak hash táblákkal, defstruct-tal és a loop makróval Common Lispben? -->
<!-- tags: hash tables, defstruct, loop macro, format, common lisp, data processing -->

A gyakorlati Common Lisp-kód alapkövei: a `defstruct` gyors, rekord-jellegű típust generál konstruktorral, típus-predikátummal és accessorokkal; a `make-hash-table` (a `:test` kulcs-összehasonlítóval — stringekhez `#'equal`!) O(1) keresést ad; a `loop` makró pedig egy beágyazott mini-nyelv iterációra, gyűjtésre (`collect`, `sum`, `maximize`), feltételekre és párhuzamos léptetésre. A `format` direktívái (`~a`, `~d`, `~,2f`, `~{...~}` iteráció, `~^` elválasztó) tömör riportkészítést tesznek lehetővé. Buktatók: az alapértelmezett `eql` teszt string kulcsokkal nem talál semmit; a `sort` destruktív (másolatot rendezz); a `loop` szintaxisa nem lispes, ezért összetett esetben az `iterate` könyvtár vagy explicit rekurzió olvashatóbb lehet.

```lisp
(defstruct (sale (:constructor make-sale (product region qty unit-price)))
  product region qty unit-price)

(defparameter *sales*
  (list (make-sale "toll" "Észak" 120 250)
        (make-sale "füzet" "Dél" 40 890)
        (make-sale "toll" "Dél" 75 250)
        (make-sale "táska" "Észak" 5 12900)
        (make-sale "füzet" "Észak" 60 890)))

(defun sale-total (s) (* (sale-qty s) (sale-unit-price s)))

;; Csoportosítás hash táblába; string kulcshoz :test #'equal kell
(defun revenue-by (key-fn sales)
  (let ((table (make-hash-table :test #'equal)))
    (dolist (s sales table)
      (incf (gethash (funcall key-fn s) table 0) (sale-total s)))))

;; Hash tábla -> érték szerint csökkenően rendezett (kulcs . érték) lista
(defun sorted-entries (table)
  (sort (loop for k being the hash-keys of table using (hash-value v)
              collect (cons k v))
        #'> :key #'cdr))

;; A loop több gyűjtést is végezhet egyetlen menetben
(defun summary (sales)
  (loop for s in sales
        for total = (sale-total s)
        sum total into revenue
        maximize total into biggest
        count (> (sale-qty s) 50) into bulk-orders
        finally (return (list :revenue revenue :biggest biggest :bulk bulk-orders))))

(format t "Termékenként:~%~:{  ~10a ~8d Ft~%~}"
        (mapcar (lambda (e) (list (car e) (cdr e)))
                (sorted-entries (revenue-by #'sale-product *sales*))))
(format t "Régiók: ~{~a~^, ~}~%"
        (mapcar #'car (sorted-entries (revenue-by #'sale-region *sales*))))
(format t "Összesítés: ~s~%" (summary *sales*))
(format t "Átlagos tétel: ~,2f Ft~%"
        (/ (reduce #'+ *sales* :key #'sale-total) (length *sales*)))
```

## Racket: modulok, mintaillesztés és contractok
<!-- q: Hogyan használjam a Racket moduljait, a match mintaillesztést és a contractokat? -->
<!-- tags: racket, contracts, match, struct, modules, for loops, define/contract -->

A Racket a Scheme-ből fejlődött ki, de saját, „elemekkel együtt” érkező ökoszisztémát ad: minden fájl egy modul (`#lang racket`), az exportot a `provide` szabályozza, a `struct` átlátszó rekordtípust generál, a `match` gazdag mintaillesztést ad (listák, struktúrák, ellipszis, predikátumok), a `for/list`, `for/fold`, `for/hash` család pedig olvasható iterációt. A *contractok* (`->`, `listof`, `integer-in`, `contract-out`) futásidejű, a modulhatáron ellenőrzött szerződések, és hiba esetén pontosan megnevezik a felelőst (*blame*: a hívó vagy a hívott fél szegte meg). Buktató: a `contract-out` csak a modulhatáron ellenőriz (modulon belüli hívásra nem) — belső teszthez `define/contract` kell; a contractoknak futásidejű költsége van, forró ciklusokban mérd.

```racket
#lang racket
;; Export contracttal: a modulon kívüli hívók ellen ellenőrzött
(provide (contract-out
          [order-total (-> order? exact-nonnegative-integer?)]
          [struct order ([id exact-positive-integer?]
                         [lines (listof (cons/c string? exact-positive-integer?))]
                         [status (or/c 'new 'paid 'shipped)])]))

(struct order (id lines status) #:transparent)

(define prices (hash "toll" 250 "füzet" 890 "táska" 12900))

(define (order-total o)
  (for/sum ([line (in-list (order-lines o))])
    (* (cdr line) (hash-ref prices (car line) 0))))

;; match: struktúra + lista ellipszissel + feltétel
(define (describe o)
  (match o
    [(order id '() _) (format "#~a: üres rendelés" id)]
    [(order id (list (cons skus qtys) ...) 'paid)
     #:when (> (apply + qtys) 10)
     (format "#~a: nagy, fizetett rendelés (~a db): ~a" id (apply + qtys) skus)]
    [(order id lines status)
     (format "#~a: ~a tétel, állapot: ~a" id (length lines) status)]))

;; define/contract: modulon BELÜL is ellenőrzött függvény
(define/contract (apply-discount price pct)
  (-> exact-nonnegative-integer? (integer-in 0 100) exact-nonnegative-integer?)
  (- price (quotient (* price pct) 100)))

;; for/fold: több akkumulátor egy menetben
(define (stats orders)
  (for/fold ([count 0] [revenue 0] #:result (list count revenue))
            ([o (in-list orders)] #:when (eq? (order-status o) 'paid))
    (values (add1 count) (+ revenue (order-total o)))))

(define orders
  (list (order 1 '(("toll" . 12) ("füzet" . 2)) 'paid)
        (order 2 '() 'new)
        (order 3 '(("táska" . 1)) 'shipped)))

(for-each (compose displayln describe) orders)
(displayln (stats orders))                          ; (1 4780)
(displayln (apply-discount 10000 15))               ; 8500
;; Contract-sértés: a hiba megnevezi a felelőst (blame)
(with-handlers ([exn:fail:contract? (λ (e) (displayln "contract-hiba: rossz százalék"))])
  (apply-discount 10000 150))
```
