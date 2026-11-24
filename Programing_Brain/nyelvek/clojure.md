# Clojure
<!-- tech: clojure -->
<!-- aliases: clj, cljs, clojurescript, edn, leiningen -->

A Clojure a JVM-en (és ClojureScriptként a JavaScript-motorokon) futó modern Lisp-dialektus: dinamikusan típusos, funkcionális, a kód adat (homoikonikus S-kifejezések), és teljes hozzáférést ad a Java-ökoszisztémához. Központi elve az immutabilitás: a beépített perzisztens adatszerkezetek (vector, map, set) strukturális megosztással olcsón „módosíthatók”, a változó állapotot pedig jól definiált referencia-típusok kezelik (atom, ref/STM, agent), ami egyszerűvé teszi a konkurens programozást. REPL-vezérelt, interaktív fejlesztésre épül. Adatfeldolgozásban, backend szolgáltatásokban, üzleti szabályrendszerekben és ott erős, ahol sok adatot kell transzformálni; gyengébb, ha gyors indulás (JVM-startup), alacsony memóriaigény vagy erős statikus típusosság kell.

## Immutábilis, perzisztens adatszerkezetek
<!-- q: Hogyan működnek a Clojure perzisztens adatszerkezetei és hogyan módosítsak beágyazott adatot? -->
<!-- tags: persistent data structures, immutability, structural sharing, assoc-in, update-in, transient -->

A Clojure vektorai, map-jei és halmazai immutábilisak: az `assoc`, `conj`, `update` új verziót ad, a régi érintetlen marad. Ez nem teljes másolással történik, hanem *strukturális megosztással* (32-ágú hash array mapped trie), így egy módosítás O(log32 n) ≈ gyakorlatilag konstans idejű, és a két verzió osztozik a változatlan részfákon. Az egyenlőség érték szerinti (`(= [1 2] '(1 2))` igaz), így az adat biztonságosan megosztható szálak között zár nélkül. Beágyazott adatra az `assoc-in`/`update-in`/`get-in` való, nagy mennyiségű lokális építéshez pedig a `transient` + `persistent!` ad mutábilis gyorsítást. Buktató: a listán (`'()`) a `conj` az elejére, vektoron a végére fűz, és a transient-et soha nem szabad kiszivárogtatni vagy a visszatérési érték helyett használni.

```clojure
(ns example.persistent
  (:require [clojure.set :as set]))

;; Beágyazott map: termékek árral, készlettel és címkékkel
(def inventory
  {:apple  {:price 120 :qty 40 :tags #{:fruit :local}}
   :banana {:price 90  :qty 0  :tags #{:fruit :import}}})

;; Minden "módosítás" új verziót ad
(def restocked  (assoc-in inventory [:banana :qty] 25))
(def discounted (update-in restocked [:apple :price] #(long (* % 0.9))))

(println (get-in inventory [:banana :qty]))            ; 0  — a régi verzió érintetlen
(println (get-in discounted [:apple :price]))          ; 108
;; Strukturális megosztás: a változatlan részfa ugyanaz az objektum
(println (identical? (:apple inventory) (:apple restocked)))   ; true

;; Vektor: indexelt elérés, conj a végére, olcsó subvec
(def v (vec (range 10)))
(println (assoc v 3 :x) (conj v 10) (subvec v 2 5))

;; Lista: conj az elejére
(println (conj '(2 3) 1))                              ; (1 2 3)

;; Halmazműveletek
(println (set/union #{1 2} #{2 3}) (set/difference #{1 2 3} #{2}))

;; Termékek, amelyekből van készlet, ár szerint rendezve
(println (->> discounted
              (filter (fn [[_ {:keys [qty]}]] (pos? qty)))
              (sort-by (comp :price val))
              (map key)))                               ; (:banana :apple)

;; Transient: lokálisan mutábilis építés, a végén perzisztenssé alakítva
(defn word-freq [words]
  (persistent!
    (reduce (fn [m w] (assoc! m w (inc (get m w 0))))
            (transient {})
            words)))

(println (word-freq ["a" "b" "a" "c" "a"]))            ; {"a" 3, "b" 1, "c" 1}
```

## Szekvenciák és lusta kiértékelés
<!-- q: Hogyan működnek a lusta szekvenciák Clojure-ben és milyen buktatóik vannak? -->
<!-- tags: lazy sequences, lazy-seq, seq abstraction, chunking, doall, line-seq, holding head -->

A seq absztrakció (`first`, `rest`, `cons`) egységes felületet ad minden gyűjteményre, a `map`, `filter`, `take` stb. pedig *lusta* szekvenciát ad vissza: az elemek csak bejáráskor, igény szerint számolódnak, és utána cache-elődnek. Így végtelen sorozatok (`iterate`, `range`, saját `lazy-seq`) és nagy fájlok (`line-seq`) is kezelhetők. Buktatók: (1) a lusta seq-ek 32-es *chunkokban* értékelődnek, ezért mellékhatás több elemre is lefuthat, mint gondolnád; (2) ha a lusta seq kiszökik egy `with-open` blokkból, a fájl már zárva lesz, mire olvasnád — `doall`/`vec` kell; (3) a seq fejének megtartása (*holding the head*) miatt az egész sorozat a memóriában marad.

```clojure
(ns example.lazy
  (:require [clojure.java.io :as io]))

;; Saját végtelen lusta sorozat: a lazy-seq törzse csak bejáráskor fut
(defn fibs
  ([] (fibs 0N 1N))
  ([a b] (lazy-seq (cons a (fibs b (+ a b))))))

(println (take 10 (fibs)))                       ; (0N 1N 1N 2N 3N 5N 8N 13N 21N 34N)

(defn prime? [n]
  (and (> n 1)
       (not-any? #(zero? (mod n %)) (range 2 (inc (long (Math/sqrt n)))))))

;; Végtelen sorozatból csak annyit veszünk, amennyi kell
(println (->> (iterate inc 2) (filter prime?) (drop 1000) first))   ; az 1001. prím: 7927

;; BUKTATÓ 1: chunking — a mellékhatás 32 elemre fut le, nem egyre
(def touched (atom 0))
(first (map (fn [x] (swap! touched inc) x) (range 100)))
(println "feldolgozott elemek:" @touched)        ; 32

;; BUKTATÓ 2: a lusta seq kiszökne a with-open-ből -> doall / into
(defn error-lines [path]
  (with-open [rdr (io/reader path)]
    (into [] (filter #(re-find #"ERROR" %)) (line-seq rdr))))   ; mohón, még nyitott fájlnál

;; Mellékhatásos bejárás: run! / doseq (nem map, mert az lusta!)
(run! println (take 3 (fibs)))

;; BUKTATÓ 3: holding the head — a 'nums' a fejet tartja, így minden elem bent marad
;; (let [nums (range 1e8)] [(last nums) (first nums)])   ; sok memória
;; JÓ: egy menetben, fej megtartása nélkül
(println (reduce + (range 1e7)))

(let [tmp (java.io.File/createTempFile "app" ".log")]
  (spit tmp "INFO indul\nERROR adatbázis\nINFO ok\nERROR időtúllépés\n")
  (println (error-lines tmp)))
```

## Transducerek
<!-- q: Mik azok a transducerek Clojure-ben és miért hatékonyabbak a sima map/filter láncnál? -->
<!-- tags: transducers, transduce, comp, into, sequence, stateful transducer, performance -->

A transducer egy forrástól és céltól független transzformáció („reducing function → reducing function”): a `(map f)`, `(filter p)` argumentum nélküli hívása transducert ad, ezek `comp`-pal összefűzhetők, majd bármilyen kontextusban alkalmazhatók — `into` (gyűjtemény), `transduce` (redukció), `sequence` (lusta seq), `eduction`, vagy core.async csatorna. Mivel nincsenek köztes lusta szekvenciák, a lánc egyetlen menetben, kevesebb allokációval fut, gyakran többszörösen gyorsabban. Állapottartó transducer `volatile!`-lal írható (lásd `dedupe`, `partition-all`). Buktató: a `comp` transducereknél balról jobbra hat (a sima függvénykompozícióval ellentétben), és az állapottartó transducer példánya nem osztható meg párhuzamos folyamatok között.

```clojure
(ns example.xf)

(def orders
  [{:id 1 :active? true  :amount 100 :country "HU"}
   {:id 2 :active? false :amount 250 :country "AT"}
   {:id 3 :active? true  :amount nil :country "HU"}
   {:id 4 :active? true  :amount 400 :country "DE"}])

;; A transzformáció egyszer definiálva, forrástól függetlenül (balról jobbra hat!)
(def gross-amounts
  (comp (filter :active?)
        (map :amount)
        (remove nil?)
        (map #(* % 1.27))))                        ; bruttósítás

(println (transduce gross-amounts + 0 orders))     ; redukció köztes seq nélkül
(println (into [] gross-amounts orders))           ; gyűjteménybe
(println (sequence gross-amounts orders))          ; lusta seq-ként

;; Saját, állapottartó transducer: egymást követő azonos kulcsú elemek kiszűrése
(defn dedupe-by [f]
  (fn [rf]
    (let [prev (volatile! ::none)]                ; példányonként saját állapot
      (fn
        ([] (rf))                                  ; init
        ([result] (rf result))                     ; completion
        ([result input]                            ; step
         (let [k (f input)
               p @prev]
           (vreset! prev k)
           (if (= k p) result (rf result input))))))))

(println (into [] (comp (filter :active?) (dedupe-by :country)) orders))   ; az aktívak közül a #3 kiesik (HU után HU)

;; Csoportosítás batch-ekbe + számítás egy menetben
(println (into [] (comp (map :id) (partition-all 2) (map #(apply + %))) orders))   ; [3 7]

;; Teljesítmény: nagy adaton a transducer nem épít köztes seq-eket
(time (reduce + (->> (range 1e6) (map inc) (filter even?))))
(time (transduce (comp (map inc) (filter even?)) + (range 1e6)))
```

## Atomok: szinkron, koordinálatlan állapot
<!-- q: Hogyan kezeljem a megosztott állapotot Clojure atomokkal (swap!, validator, watch)? -->
<!-- tags: atom, swap!, reset!, compare-and-set, validator, watch, concurrency, state -->

Az atom egyetlen, független értéket tárol, amelyet szálbiztosan, zár nélkül lehet módosítani: a `swap!` egy tiszta függvényt alkalmaz a jelenlegi értékre, és compare-and-set-tel írja vissza — ha közben más szál módosította, a függvényt *újrafuttatja*. Ezért a `swap!`-nak átadott függvény mellékhatás-mentes kell legyen. A validator (`set-validator!`) minden új értéket ellenőriz és érvénytelen állapotnál kivételt dob, a watch (`add-watch`) minden változáskor értesítést kap (audit log, UI frissítés), a `swap-vals!` pedig a régi és új értéket is visszaadja. Buktató: két *külön* atom együttes, konzisztens módosítására az atom nem alkalmas (erre ref/STM kell, vagy egyetlen atomba szervezett állapot).

```clojure
(ns example.atoms)

;; Az összes számla egy atomban: így az átutalás egyetlen atomikus swap!
(def accounts (atom {:alice 100 :bob 50 :carol 0}))

;; Validator: negatív egyenleg soha nem kerülhet be
(set-validator! accounts (fn [m] (every? (complement neg?) (vals m))))

;; Watch: minden változás naplózása (a watch fut mellékhatással, nem a swap! függvény)
(def audit (atom []))
(add-watch accounts :audit
           (fn [_key _ref old new]
             (when (not= old new)
               (swap! audit conj {:before old :after new}))))

;; Tiszta függvény: újrafuttatható, ha versenyhelyzet miatt a CAS elbukik
(defn transfer [m from to amount]
  (-> m (update from - amount) (update to + amount)))

(defn transfer! [from to amount]
  (try
    (swap! accounts transfer from to amount)
    :ok
    (catch IllegalStateException _                   ; a validator elutasította
      :insufficient-funds)))

(println (transfer! :alice :bob 30))                  ; :ok
(println (transfer! :carol :bob 10))                  ; :insufficient-funds
(println @accounts)

;; Párhuzamos terhelés: 1000 átutalás 8 szálon, az összeg megmarad
(let [futures (doall (for [_ (range 1000)]
                       (future (transfer! (rand-nth [:alice :bob]) :carol 1))))]
  (run! deref futures))
(println @accounts "összesen:" (reduce + (vals @accounts)))   ; mindig 150

;; swap-vals!: régi és új érték egyszerre (pl. "ki volt az előző?")
(def current-leader (atom :node-1))
(let [[old new] (swap-vals! current-leader (constantly :node-2))]
  (println "vezető:" old "->" new))
(println "audit bejegyzések:" (count @audit))
(shutdown-agents)                                     ; a future-ök szálkészlete
```

## Refek és STM: koordinált tranzakciók
<!-- q: Hogyan módosítsak több állapotot egyszerre konzisztensen Clojure STM-mel (ref, dosync)? -->
<!-- tags: ref, stm, dosync, alter, commute, ensure, write skew, transactions -->

A ref koordinált, szinkron állapot: több ref a `dosync` tranzakción belül atomikusan, konzisztensen módosítható (ACI, a D nélkül). A Clojure STM MVCC-alapú: minden tranzakció egy konzisztens pillanatképet lát, ütközéskor automatikusan újrapróbálkozik, ezért a tranzakció törzse ne tartalmazzon IO-t. Az `alter` sorrendfüggő módosítás, a `commute` kommutatív műveletre (számláló, `conj`) kevesebb ütközést okoz, az `ensure` pedig egy csak olvasott refet is „lezár”, így megelőzi a *write skew* anomáliát (két tranzakció egymás olvasott adatára hozott döntést). Buktató: a ref-módosítás tranzakción kívül kivételt dob, és a tranzakcióban küldött agent-üzenetek csak commit után mennek ki.

```clojure
(ns example.stm)

(def checking (ref 100))
(def savings  (ref 500))
(def tx-log   (ref []))

;; Két egyenleg + napló egy atomikus tranzakcióban
(defn transfer! [from to amount]
  (dosync
    (when (< @from amount)
      (throw (ex-info "Nincs fedezet" {:available @from :amount amount})))
    (alter from - amount)
    (alter to + amount)
    ;; commute: a log sorrendje itt nem számít, kevesebb újrapróbálás
    (commute tx-log conj {:amount amount :at (System/currentTimeMillis)})))

(transfer! savings checking 200)
(println @checking @savings (count @tx-log))         ; 300 300 1

;; Párhuzamos oda-vissza utalások: az összeg minden pillanatban 600
(let [fs (for [i (range 200)]
           (future (if (even? i) (transfer! checking savings 1) (transfer! savings checking 1))))]
  (run! deref (doall fs)))
(println "összeg:" (dosync (+ @checking @savings)))   ; konzisztens pillanatkép: 600

;; Write skew: legalább egy orvosnak ügyeletben kell maradnia
(def on-call {:anna (ref true) :bela (ref true)})

(defn leave! [who]
  (dosync
    (let [others (remove #{who} (keys on-call))]
      ;; ensure: a MÁSIK orvos ref-jét is rögzítjük, különben mindketten távozhatnának
      (if (some #(ensure (on-call %)) others)
        (do (ref-set (on-call who) false) :ok)
        :denied))))

(let [a (future (leave! :anna))
      b (future (leave! :bela))]
  (println "anna:" @a "béla:" @b))                    ; az egyik :ok, a másik :denied
(shutdown-agents)
```

## Agentek: aszinkron, sorosított állapotváltás
<!-- q: Mikor használjak agent-et Clojure-ben és hogyan kezeljem a hibáit? -->
<!-- tags: agent, send, send-off, await, error-handler, asynchronous state, io -->

Az agent független, *aszinkron* módon változó állapot: a `send`/`send-off` egy függvényt sorba állít, amelyet egy háttérszál az agent aktuális értékére alkalmaz; egy agenten az akciók sorosan, egyesével futnak, így nincs versenyhelyzet. A `send` CPU-intenzív munkára való (fix méretű szálkészlet), a `send-off` blokkoló IO-ra (bővülő szálkészlet); az `await` bevárja az eddig küldött akciókat. Tranzakcióból (`dosync`) küldött akció csak sikeres commit után indul, így az agent ideális az STM melletti mellékhatásokhoz (naplózás, fájlírás). Buktató: hibás akció után az agent alapértelmezésben *hibás állapotba* kerül és minden további `send` kivételt dob — használj `:error-mode :continue`-t és error-handlert, a program végén pedig `shutdown-agents`-et.

```clojure
(ns example.agents
  (:require [clojure.java.io :as io]))

;; Hibatűrő agent: hiba esetén naplóz és folytatja
(def stats
  (agent {:processed 0 :failed 0}
         :error-mode :continue
         :error-handler (fn [_ag ex] (println "agent hiba:" (ex-message ex)))))

(defn process-event [state event]
  (when (= (:type event) :corrupt)
    (throw (ex-info "sérült esemény" {:event event})))
  (update state :processed inc))

;; send: CPU-jellegű, rövid akciók
(doseq [e [{:type :click} {:type :view} {:type :corrupt} {:type :click}]]
  (send stats process-event e))
(await stats)
(println @stats)                                      ; {:processed 3, :failed 0}

;; send-off: blokkoló IO, az agent állapota a fájl útvonala; sorosított írás
(def log-file (java.io.File/createTempFile "events" ".log"))
(def writer (agent (.getPath log-file)))

(defn append-line! [path line]
  (with-open [w (io/writer path :append true)]
    (.write w (str line "\n")))
  path)                                                 ; az új állapot (változatlan útvonal)

(dotimes [i 5]
  (send-off writer append-line! (str "esemény #" i)))

;; STM + agent: az üzenet csak commit után megy ki, újrapróbálásnál nem duplikálódik
(def balance (ref 100))
(dosync
  (alter balance - 30)
  (send-off writer append-line! "levonás: 30"))

(await writer)
(println (slurp log-file))
(shutdown-agents)
```

## core.async: csatornák és go blokkok
<!-- q: Hogyan használjam a core.async csatornákat és go blokkokat Clojure-ben? -->
<!-- tags: core.async, channels, go, go-loop, alts!, timeout, pipeline, backpressure, csp -->

A core.async a CSP (Communicating Sequential Processes) modellt hozza Clojure-be: a folyamatok *csatornákon* (`chan`) keresztül kommunikálnak, a `go` blokk pedig egy makró, amely a kódot állapotgéppé alakítja, így a `<!`/`>!` parkoláskor nem foglal szálat — több ezer go blokk fut egy kis szálkészleten. A pufferelt csatorna (`(chan 10)`, `sliding-buffer`, `dropping-buffer`) szabályozza a visszanyomást (backpressure), az `alts!` több csatorna közül az elsőként kész műveletet választja (timeout-tal kombinálva időkorlátot ad), a `pipeline`/`pipeline-blocking` párhuzamos feldolgozó láncot épít, a csatorna transducert is kaphat. Buktatók: go blokkban tilos a blokkoló IO (az kevés szálat foglalna le — `thread` vagy `pipeline-blocking` kell), a `<!` nem működik a go blokkon belüli anonim függvényben, és a lezárt csatornából `nil` jön.

```clojure
(ns example.async
  (:require [clojure.core.async :as a :refer [go go-loop chan <! >! <!! timeout alts! close!]]))

;; Termelő: számokat ír, majd lezárja a csatornát (a fogyasztó nil-t kap)
(defn producer [out n]
  (go (doseq [i (range n)] (>! out i))
      (close! out)))

;; Szimulált lassú, blokkoló szolgáltatás
(defn slow-square [x] (Thread/sleep 50) (* x x))

;; Időkorlát alts!-szal: amelyik csatorna előbb kész, az nyer
(defn with-timeout [ms ch]
  (go (let [t (timeout ms)
            [v port] (alts! [ch t])]
        (if (= port t) :timeout v))))

(defn demo []
  ;; 1) Párhuzamos feldolgozó lánc: 4 szálon blokkoló munka, sorrendtartó
  (let [in  (chan 10)                                ; puffer = visszanyomás
        out (chan 10 (filter even?))]                ; csatorna transducerrel
    (producer in 20)
    (a/pipeline-blocking 4 out (map slow-square) in)
    (println "eredmények:" (<!! (a/into [] out))))

  ;; 2) Fan-in: több forrás egyesítése merge-dzsel, go-loop fogyasztó
  (let [sources (for [id [:a :b :c]]
                  (let [c (chan)]
                    (go (dotimes [i 3]
                          (<! (timeout (rand-int 30)))
                          (>! c [id i]))
                        (close! c))
                    c))
        merged (a/merge sources)
        done (go-loop [acc []]
               (if-let [msg (<! merged)]
                 (recur (conj acc msg))
                 acc))]                              ; nil: minden forrás lezárult
    (println "összes üzenet:" (count (<!! done))))   ; 9

  ;; 3) Időkorlát: a lassú válasz helyett :timeout
  (let [slow (go (<! (timeout 200)) :adat)
        fast (go (<! (timeout 10)) :adat)]
    (println (<!! (with-timeout 100 slow)) (<!! (with-timeout 100 fast)))))

(demo)
```

## Makrók és homoikonikusság
<!-- q: Hogyan írjak makrót Clojure-ben syntax-quote-tal és hogyan kerüljem el a buktatóit? -->
<!-- tags: macros, defmacro, syntax-quote, unquote, gensym, macroexpand, homoiconicity -->

Mivel a Clojure-kód maga is adat (listák, vektorok, szimbólumok), a makró egy olyan függvény, amely fordítási időben kódot kap és kódot ad vissza — így új vezérlési szerkezetek és DSL-ek építhetők (`when`, `->`, `defn` is makró). A syntax-quote (`` ` ``) teljesen minősíti a szimbólumokat (névtér-higiénia), a `~` beilleszt egy értéket, a `~@` egy listát „kiterít”, a `nev#` pedig automatikusan egyedi szimbólumot generál (gensym), hogy a makró változói ne ütközzenek a hívóéval. Fejlesztéskor a `macroexpand-1` mutatja meg a kifejtett kódot. Buktatók: ugyanazt az argumentumot kétszer beillesztve kétszer értékelődik ki (mellékhatás!), a makró nem first-class érték (nem adható át `map`-nek), és amit függvény is megold, azt ne írd makróként.

```clojure
(ns example.macros)

;; Időmérő makró: a start#/result# gensym-ek nem ütköznek a hívó változóival
(defmacro with-timing [label & body]
  `(let [start#  (System/nanoTime)
         result# (do ~@body)]
     (println ~label (format "%.2f ms" (/ (- (System/nanoTime) start#) 1e6)))
     result#))

(println (with-timing "összegzés" (reduce + (range 1000000))))

;; ROSSZ: az argumentum kétszer értékelődik ki
(defmacro square-bad [x] `(* ~x ~x))
;; JÓ: egyszer kiértékeljük és lokálishoz kötjük
(defmacro square [x] `(let [v# ~x] (* v# v#)))

(def counter (atom 0))
(println (square-bad (swap! counter inc)) "számláló:" @counter)   ; 2 (1*2), számláló: 2
(reset! counter 0)
(println (square (swap! counter inc)) "számláló:" @counter)       ; 1, számláló: 1

;; Új vezérlési szerkezet: újrapróbálkozás kivétel esetén
(defmacro retrying [n & body]
  `(loop [attempt# 1]
     (let [res# (try {:ok (do ~@body)}
                     (catch Exception e#
                       (if (< attempt# ~n) ::retry (throw e#))))]
       (if (= res# ::retry)
         (do (Thread/sleep (* 10 attempt#)) (recur (inc attempt#)))
         (:ok res#)))))

(def flaky (atom 0))
(println (retrying 5 (if (< (swap! flaky inc) 3) (throw (ex-info "hiba" {})) :siker)))

;; Kis DSL: handler definiálása beépített hibakezeléssel
(defmacro defhandler [name args & body]
  `(defn ~name ~args
     (try ~@body
          (catch Exception e#
            {:status 500 :error (ex-message e#)}))))

(defhandler get-user [id]
  (if (pos? id) {:status 200 :body {:id id}} (throw (ex-info "rossz id" {}))))

(println (get-user 7) (get-user -1))
(println (macroexpand-1 '(square (f x))))   ; a kifejtett kód megtekintése
```

## Java interop
<!-- q: Hogyan használjak Java osztályokat és könyvtárakat Clojure-ből? -->
<!-- tags: java interop, jvm, type hints, reflection, reify, doto, executors -->

A Clojure a JVM-en natívan hívja a Java-kódot: `(.metodus obj arg)` példánymetódus, `(Osztaly/statikus arg)` statikus tag, `(Osztaly. arg)` vagy `(new Osztaly arg)` konstruktor, a `doto` egymás utáni mutáló hívásokat, a `..`/`->` láncolást egyszerűsít. Interfészt a `reify` (névtelen implementáció) vagy a `proxy` (osztály kiterjesztése) valósít meg; a Clojure-függvények eleve implementálják a `Runnable` és `Callable` interfészt, ezért közvetlenül átadhatók egy `ExecutorService`-nek. Buktató: típus nélkül a hívás reflexióval megy, ami nagyon lassú — kapcsold be a `*warn-on-reflection*`-t, és használj típus-hintet (`^String`); a Java-gyűjtemények mutábilisak, ezért a határon alakítsd át őket (`vec`, `into {}`).

```clojure
(ns example.interop
  (:import (java.time LocalDate DayOfWeek)
           (java.time.temporal ChronoUnit)
           (java.util.concurrent Executors Future TimeUnit)
           (java.util ArrayList Comparator)))

(set! *warn-on-reflection* true)   ; figyelmeztet a lassú, reflexiós hívásokra

;; Típus-hint: a fordító közvetlen metódushívást generál reflexió helyett
(defn initials [^String full-name]
  (->> (.split full-name " ")
       (map #(.charAt ^String % 0))
       (apply str)))

(println (initials "Kiss Anna Mária"))              ; KAM

;; java.time: statikus és példánymetódusok, láncolva
(defn business-days-between [^LocalDate from ^LocalDate to]
  (->> (range (.between ChronoUnit/DAYS from to))
       (map #(.plusDays from %))
       (remove #(#{DayOfWeek/SATURDAY DayOfWeek/SUNDAY} (.getDayOfWeek ^LocalDate %)))
       count))

(println (business-days-between (LocalDate/of 2026 11 2) (LocalDate/of 2026 11 16)))   ; 10

;; doto: mutábilis Java objektum feltöltése, majd átalakítás Clojure adattá
(def names (doto (ArrayList.) (.add "Béla") (.add "anna") (.add "Csaba")))
(.sort names String/CASE_INSENSITIVE_ORDER)
(println (vec names))                                ; [anna Béla Csaba]

;; reify: interfész implementálása (Comparator hossz szerint)
(def by-length
  (reify Comparator
    (compare [_ a b] (Integer/compare (count a) (count b)))))
(println (sort by-length ["kiwi" "fig" "banana"]))

;; ExecutorService: a Clojure fn Callable-ként átadható
(let [pool    (Executors/newFixedThreadPool 4)
      tasks   (map (fn [i] (fn [] (Thread/sleep 20) (* i i))) (range 8))
      futures (.invokeAll pool ^java.util.Collection tasks)]
  (println (mapv #(.get ^Future %) futures))
  (.shutdown pool)
  (.awaitTermination pool 1 TimeUnit/SECONDS))
```

## clojure.spec: adatvalidáció és generatív tesztelés
<!-- q: Hogyan validáljak adatot és teszteljek függvényeket clojure.spec-kel? -->
<!-- tags: clojure.spec, validation, s/def, s/keys, conform, explain, fdef, generative testing -->

A `clojure.spec` deklaratív leírást ad az adatok és függvények alakjáról: a `s/def` névtérrel minősített kulcsszóhoz (`::email`) predikátumot vagy összetett specet köt, az `s/keys` map-ek kötelező és opcionális kulcsait írja le, az `s/cat`/`s/alt` szekvenciákat reguláris kifejezésszerűen. Egy spec egyszerre használható validálásra (`s/valid?`), részletes hibaleírásra (`s/explain-data`), adat-normalizálásra (`s/conform`), tesztadat-generálásra (`gen/sample`) és — `s/fdef`-fel — függvények generatív tesztelésére (`stest/check`) vagy futásidejű argumentum-ellenőrzésre fejlesztés közben (`stest/instrument`). Buktató: az `s/and` utáni egyedi predikátumokhoz a generátor nem tud értéket gyártani (sok elutasítás után hibát ad) — ilyenkor `s/with-gen` kell; a generatív teszthez a `test.check` függőség szükséges.

```clojure
(ns example.spec
  (:require [clojure.spec.alpha :as s]
            [clojure.spec.gen.alpha :as gen]
            [clojure.spec.test.alpha :as stest]))

;; Elemi specek: predikátum, halmaz, tartomány
(s/def ::email (s/and string? #(re-matches #"[^@\s]+@[^@\s]+\.[a-z]{2,}" %)))
(s/def ::age   (s/int-in 0 150))
(s/def ::role  #{:admin :customer :guest})
(s/def ::tags  (s/coll-of keyword? :kind set? :max-count 5))

;; Map-spec: kötelező és opcionális, minősítetlen kulcsok
(s/def ::user (s/keys :req-un [::email ::age] :opt-un [::role ::tags]))

(println (s/valid? ::user {:email "anna@example.com" :age 31 :role :admin}))   ; true

;; Gépileg feldolgozható hibaleírás (API hibaválaszhoz)
(defn validation-errors [spec data]
  (some->> (s/explain-data spec data)
           ::s/problems
           (map (fn [{:keys [path pred val]}] {:path path :value val :pred (s/abbrev pred)}))))

(println (validation-errors ::user {:email "rossz" :age 200 :role :root}))

;; Szekvencia-spec és conform: címkézett, szétbontott eredmény
(s/def ::range-arg (s/cat :from int? :to int? :step (s/? pos-int?)))
(println (s/conform ::range-arg [1 10 2]))          ; {:from 1, :to 10, :step 2}

;; Függvény-spec: argumentumok, visszatérés és a kettő kapcsolata
(defn apply-discount [price pct]
  (- price (quot (* price pct) 100)))

(s/fdef apply-discount
  :args (s/cat :price nat-int? :pct (s/int-in 0 101))
  :ret nat-int?
  :fn #(<= (:ret %) (-> % :args :price)))            ; a kedvezményes ár nem nagyobb

;; Generált példák és generatív teszt (test.check szükséges)
(println (gen/sample (s/gen ::role) 5))
(println (-> (stest/check `apply-discount {:clojure.spec.test.check/opts {:num-tests 200}})
             stest/summarize-results))

;; Fejlesztés közben: hibás hívás azonnal, érthető hibával szálljon el
(stest/instrument `apply-discount)
(println (try (apply-discount 100 150) (catch Exception e (ex-message e))))
```

## Protokollok, rekordok és multimethodok
<!-- q: Hogyan valósítsak meg polimorfizmust Clojure-ben protokollokkal és multimethodokkal? -->
<!-- tags: protocols, defrecord, extend-protocol, multimethods, defmulti, hierarchies, polymorphism -->

A Clojure kétféle nyitott polimorfizmust kínál. A *protokoll* (`defprotocol`) típus szerinti, gyors (JVM-interfészre fordul) dispatch: `defrecord`/`deftype` törzsében vagy utólag, `extend-protocol`-lal bármely meglévő típusra (akár `String`-re, `nil`-re) kiterjeszthető — ez oldja meg az „expression problem”-et. A *multimethod* (`defmulti`) tetszőleges dispatch-függvényt használ (pl. két argumentum típusa együtt, egy mező értéke), és a `derive`-val épített ad-hoc hierarchiákat is figyelembe veszi `isa?` szerint. A `defrecord` map-ként viselkedik (kulcsszóval olvasható, `assoc`-olható), de gyorsabb mezőeléréssel. Buktató: a multimethod lassabb a protokollnál, és ha egy értékre több módszer is illeszkedik hierarchián keresztül, `prefer-method` kell a kétértelműség feloldására.

```clojure
(ns example.poly)

;; ---- Protokoll + rekordok ----
(defprotocol Shape
  (area [this])
  (perimeter [this]))

(defrecord Circle [r]
  Shape
  (area [_] (* Math/PI r r))
  (perimeter [_] (* 2 Math/PI r)))

(defrecord Rect [w h]
  Shape
  (area [_] (* w h))
  (perimeter [_] (* 2 (+ w h))))

;; Utólagos kiterjesztés meglévő típusokra (a típus forrása nélkül)
(defprotocol Describable (describe [x]))
(extend-protocol Describable
  nil       (describe [_] "semmi")
  String    (describe [s] (str "szöveg, " (count s) " karakter"))
  Circle    (describe [c] (format "kör, r=%s, T=%.2f" (:r c) (area c)))
  Object    (describe [x] (str "ismeretlen: " (type x))))

(def shapes [(->Circle 1) (->Rect 2 3) (map->Rect {:w 4 :h 1})])
(println (map area shapes) (map describe [nil "alma" (->Circle 2) 42]))
(println (assoc (->Rect 2 3) :color :red))          ; a rekord map-ként is működik

;; ---- Multimethod: dispatch két argumentum szerepe alapján, hierarchiával ----
(derive ::admin ::editor)
(derive ::editor ::viewer)

(defmulti allowed? (fn [user action] [(:role user) action]))
(defmethod allowed? [::viewer :read]   [_ _] true)
(defmethod allowed? [::editor :write]  [_ _] true)
(defmethod allowed? [::admin :delete]  [_ _] true)
(defmethod allowed? :default           [_ _] false)

(doseq [role [::viewer ::editor ::admin]
        action [:read :write :delete]]
  (println role action (allowed? {:role role} action)))   ; az admin mindent örököl

;; Multimethod érték szerinti dispatch-csel: eseménykezelő
(defmulti handle-event :type)
(defmethod handle-event :signup [{:keys [email]}] (str "üdvözlő levél: " email))
(defmethod handle-event :purchase [{:keys [total]}] (str "számla: " total " Ft"))
(defmethod handle-event :default [e] (str "ismeretlen esemény: " (:type e)))
(println (map handle-event [{:type :signup :email "a@b.hu"} {:type :purchase :total 990} {:type :x}]))
```

## Destrukturálás és threading makrók
<!-- q: Hogyan használjam a destrukturálást és a threading makrókat (->, ->>, some->, cond->) Clojure-ben? -->
<!-- tags: destructuring, threading macros, ->, ->>, some->, cond->, as->, idiomatic clojure -->

A destrukturálás a `let`-ben és a függvényparaméterekben egy lépésben bontja szét a vektorokat (`[a b & rest]`) és map-eket (`{:keys [id name] :or {name "?"} :as all}`), akár beágyazva — így a függvény szignatúrája dokumentálja, milyen adatot vár. A threading makrók a beágyazott hívásokat olvasható lánccá alakítják: a `->` az első, a `->>` az utolsó argumentum helyére fűz (gyűjteményfüggvényekhez), a `some->` az első `nil`-nél megáll (null-biztos navigáció), a `cond->` feltételesen alkalmaz lépéseket, az `as->` pedig tetszőleges pozíciót enged. Buktató: hiányzó kulcs destrukturáláskor csendben `nil` lesz (az `:or` csak a hiányzó kulcsra hat, explicit `nil` értékre nem), és a `->`/`->>` keverése nehezen olvasható — ilyenkor bontsd `let`-re.

```clojure
(ns example.destructure
  (:require [clojure.string :as str]))

;; Map-destrukturálás alapértékkel, beágyazással és :as-szel
(defn shipping-label [{:keys [id customer items express?]
                       :or {express? false}
                       {:keys [city zip]} :address
                       :as order}]
  (format "#%d %s, %s %s (%d tétel)%s"
          id customer zip city (count items) (if express? " EXPRESSZ" "")))

;; Vektor-destrukturálás: első elemek és a maradék
(defn head-and-tail [[first-item second-item & more]]
  {:first first-item :second second-item :rest-count (count more)})

(def order {:id 42 :customer "Nagy Péter" :items [{:sku "A" :qty 2 :price 1500}
                                                  {:sku "B" :qty 1 :price 4200}]
            :address {:city "Kecskemét" :zip "6000"} :coupon "OSZ10"})

(println (shipping-label order))
(println (head-and-tail [:a :b :c :d]))

;; ->> : gyűjtemény-lánc (az érték az utolsó argumentum helyére kerül)
(defn order-total [{:keys [items]}]
  (->> items
       (map (fn [{:keys [qty price]}] (* qty price)))
       (reduce + 0)))

;; cond-> : feltételes lépések; -> : az első argumentum helyére fűz
(defn price-order [o]
  (let [subtotal (order-total o)]
    (cond-> {:subtotal subtotal :total subtotal}
      (:coupon o)       (update :total #(long (* % 0.9)))
      (> subtotal 5000) (assoc :free-shipping true)
      (:express? o)     (update :total + 1990))))

(println (price-order order))   ; {:subtotal 7200, :total 6480, :free-shipping true}

;; some-> : null-biztos navigáció, az első nil-nél megáll
(defn coupon-code [o]
  (some-> o :coupon str/trim str/upper-case not-empty))

(println (coupon-code order) (coupon-code {:id 1}))  ; OSZ10 nil

;; as-> : ha az érték pozíciója lépésenként változik
(println (as-> "  Clojure, Haskell , Elixir " s
           (str/split s #",")
           (map str/trim s)
           (sort s)
           (str/join " | " s)))
```
