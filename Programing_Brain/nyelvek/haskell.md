# Haskell
<!-- tech: haskell -->
<!-- aliases: ghc, hs, cabal, stack -->

A Haskell tisztán funkcionális, lusta kiértékelésű, statikusan és erősen típusos nyelv, Hindley–Milner alapú típuskövetkeztetéssel és típusosztályokkal. A mellékhatásokat a típusrendszer választja le (`IO`, `STM`, monádok), az adatok alapértelmezetten immutábilisak, a memóriát GC kezeli. A GHC fordító natív kódot készít, kiváló a könnyűsúlyú szálkezelése (green thread-ek, STM). Erős fordítóknál, DSL-eknél, parsereknél, pénzügyi és kritikus logikánál, ahol a „ha lefordul, jó eséllyel működik” elv sokat ér; gyengébb választás, ha kiszámítható memóriahasználat kell lusta kód mellett, ha a csapat nem ismeri a nyelvet, vagy ha az ökoszisztéma (pl. GUI, mobil) szűkös.

## Lusta kiértékelés és thunkok
<!-- q: Hogyan működik a lusta kiértékelés Haskellben és mire jó? -->
<!-- tags: laziness, thunk, whnf, infinite list, sharing, non-strict -->

Haskellben egy kifejezés csak akkor értékelődik ki, amikor az eredményére ténylegesen szükség van; addig egy *thunk* (függőben lévő számítás) áll a helyén. Kiértékeléskor a thunk felülíródik az eredménnyel (*sharing*), így ugyanaz a számítás nem fut le kétszer. Ez teszi lehetővé a végtelen adatszerkezeteket, a rövidzáras saját vezérlési szerkezeteket és a „generálj mindent, vegyél belőle annyit, amennyi kell” stílust. Az alapértelmezett kiértékelés csak WHNF-ig (weak head normal form, a legkülső konstruktorig) megy, ezért pl. `length [undefined, undefined]` gond nélkül 2. Buktató: a thunkok memóriát foglalnak, és a mellékhatás-mentes kód futási sorrendje nehezen követhető.

```haskell
import Debug.Trace (trace)

-- Végtelen Fibonacci-lista: önmagára hivatkozik, az elemek igény szerint jönnek létre
fibs :: [Integer]
fibs = 0 : 1 : zipWith (+) fibs (tail fibs)

-- Végtelen prímlista: az isPrime a már kiszámolt prímeket használja (sharing)
primes :: [Int]
primes = 2 : filter isPrime [3, 5 ..]
  where
    isPrime n = all (\p -> n `mod` p /= 0) (takeWhile (\p -> p * p <= n) primes)

-- foldr + lusta (&&): végtelen listán is megáll az első False-nál
myAnd :: [Bool] -> Bool
myAnd = foldr (&&) True

-- Saját "if" függvényként: a nem választott ág soha nem értékelődik ki
myIf :: Bool -> a -> a -> a
myIf True  t _ = t
myIf False _ e = e

-- A trace megmutatja, mikor fut ténylegesen a számítás
expensive :: Int -> Int
expensive x = trace ("számolom: " ++ show x) (x * x)

main :: IO ()
main = do
  print (take 10 fibs)                     -- [0,1,1,2,3,5,8,13,21,34]
  print (takeWhile (< 40) primes)          -- [2,3,5,7,11,13,17,19,23,29,31,37]
  print (myAnd (cycle [True, False]))      -- False, pedig a lista végtelen
  print (myIf True 1 (error "soha"))       -- 1, az error thunk nem fut le
  print (length [undefined, undefined :: Int]) -- 2: csak a lista gerince kell

  -- A párok második eleme thunk marad, amíg nem kell
  let pairs = [(n, expensive n) | n <- [1 .. 5]]
  print (map fst pairs)                    -- nincs "számolom" kiírás
  print (snd (pairs !! 2))                 -- "számolom: 3", majd 9
  print (snd (pairs !! 2))                 -- csak 9: a thunk már felülíródott
```

## Space leak, seq, BangPatterns és foldl'
<!-- q: Mi az a space leak Haskellben és hogyan kerüljem el seq-kel vagy BangPatterns-szel? -->
<!-- tags: space leak, seq, bangpatterns, foldl', deepseq, strictness, performance -->

Space leak akkor keletkezik, amikor a lusta kiértékelés miatt hatalmas thunk-lánc gyűlik fel (pl. `foldl (+) 0 [1..10^7]` tízmillió `(+)`-t halmoz fel, mielőtt bármit összeadna). A `seq a b` kikényszeríti `a` WHNF-ig való kiértékelését `b` előtt; a `foldl'` ezt teszi minden lépésben, a `BangPatterns` (`!x`) pedig mintában kényszerít. A leggyakoribb csapda, hogy a WHNF csak a legkülső konstruktort értékeli: egy `(összeg, darab)` pár akkumulátor `foldl'` mellett is szivárog, mert a mezők thunkok maradnak — ilyenkor szigorú mezős (`!Double`) adattípus vagy `deepseq`/`force` kell. Diagnózishoz: `+RTS -s` vagy heap profiling (`-hT`).

```haskell
{-# LANGUAGE BangPatterns #-}
import Control.DeepSeq (force)
import Data.List (foldl')
import qualified Data.Map.Strict as M

-- ROSSZ: a foldl' csak a párt értékeli WHNF-ig, a mezők thunk-láncok maradnak
meanLeaky :: [Double] -> Double
meanLeaky xs = s / fromIntegral n
  where
    (s, n) = foldl' step (0, 0 :: Int) xs
    step (acc, cnt) x = (acc + x, cnt + 1)

-- JÓ: szigorú mezők — a konstruktor létrehozásakor a mezők is kiértékelődnek
data Acc = Acc !Double !Int

meanStrict :: [Double] -> Double
meanStrict xs = finish (foldl' step (Acc 0 0) xs)
  where
    step (Acc s n) x = Acc (s + x) (n + 1)
    finish (Acc _ 0) = 0
    finish (Acc s n) = s / fromIntegral n

-- JÓ: BangPatterns a lokális ciklusban, az akkumulátor minden lépésben kiértékelődik
sumTo :: Int -> Int
sumTo = go 0
  where
    go !acc 0 = acc
    go !acc k = go (acc + k) (k - 1)

-- seq kézzel: ugyanaz, mint a bang, csak explicit
sumSeq :: [Int] -> Int
sumSeq = go 0
  where
    go acc []       = acc
    go acc (y : ys) = let acc' = acc + y in acc' `seq` go acc' ys

-- Szógyakoriság: a Data.Map.Strict az értékeket is kiértékeli beszúráskor,
-- a lusta Data.Map-ben (+1) thunkok gyűlnének az értékekben
wordFreq :: [String] -> M.Map String Int
wordFreq = foldl' (\m w -> M.insertWith (+) w 1 m) M.empty

main :: IO ()
main = do
  print (meanStrict [1 .. 1000000])
  print (sumTo 10000000)
  print (sumSeq [1 .. 1000000])
  print (wordFreq (words "a b a c b a"))
  -- force: teljes (normál formáig tartó) kiértékelés, pl. mielőtt egy
  -- eredményt MVar-ba tennénk, hogy ne a fogadó szál számolja ki
  let !table = force (map (\x -> x * x) [1 .. 10 :: Int])
  print (sum table)
  -- $! : szigorú függvényalkalmazás
  print $! meanLeaky [1, 2, 3]
```

## Algebrai adattípusok és mintaillesztés
<!-- q: Hogyan modellezzek adatokat algebrai adattípusokkal és mintaillesztéssel Haskellben? -->
<!-- tags: adt, sum type, product type, pattern matching, guards, as-pattern -->

Az algebrai adattípus (ADT) összeg- (`|`, „vagy”) és szorzattípusokból (mezők, „és”) épül, így a lehetséges állapotokat pontosan le lehet írni, az érvénytelenek pedig ki sem fejezhetők. A mintaillesztés felülről lefelé próbálja az egyenleteket; ha egy egyenlet összes guardja hamis, a következő egyenletre lép. A `-Wall` (benne `-Wincomplete-patterns`) figyelmeztet a lefedetlen esetekre — ezt érdemes hibának venni (`-Werror`). Buktató: a `!!`, `head`, `fromJust` parciális függvények futás közben elszállhatnak, mintaillesztéssel vagy `Maybe`-vel kezeld őket.

```haskell
import Data.List (intercalate)

-- JSON-érték mint összegtípus: minden lehetséges forma egy konstruktor
data JValue
  = JNull
  | JBool Bool
  | JNumber Double
  | JString String
  | JArray [JValue]
  | JObject [(String, JValue)]
  deriving (Show, Eq)

-- Szerializálás: minden konstruktorra egy egyenlet, guarddal finomítva
render :: JValue -> String
render JNull        = "null"
render (JBool True) = "true"
render (JBool False) = "false"
render (JNumber n)
  | n == fromIntegral r = show r        -- egész szám tizedesjegy nélkül
  | otherwise           = show n
  where
    r = round n :: Integer
render (JString s)   = show s           -- egyszerűsítés: Haskell-escape ~ JSON-escape
render (JArray xs)   = "[" ++ intercalate "," (map render xs) ++ "]"
render (JObject kvs) =
  "{" ++ intercalate "," [show k ++ ":" ++ render v | (k, v) <- kvs] ++ "}"

-- Útvonal-alapú lekérdezés: biztonságos, Maybe-t ad parciális indexelés helyett
data PathSeg = Key String | Index Int

query :: [PathSeg] -> JValue -> Maybe JValue
query [] v = Just v
query (Key k : rest) (JObject kvs) = lookup k kvs >>= query rest
query (Index i : rest) (JArray xs)
  | i >= 0, (x : _) <- drop i xs = query rest x   -- pattern guard
query _ _ = Nothing                                -- minden más eset: nincs találat

-- As-pattern (rest@...): az egész részlistára és a szétbontott fejre is hivatkozunk
dedupe :: Eq a => [a] -> [a]
dedupe (x : rest@(y : _))
  | x == y    = dedupe rest
  | otherwise = x : dedupe rest
dedupe xs = xs

main :: IO ()
main = do
  let doc = JObject
        [ ("name", JString "szenzor-7")
        , ("values", JArray [JNumber 1, JNumber 2.5, JNull])
        , ("ok", JBool True)
        ]
  putStrLn (render doc)
  print (query [Key "values", Index 1] doc)   -- Just (JNumber 2.5)
  print (query [Key "values", Index 9] doc)   -- Nothing
  print (dedupe [1, 1, 2, 3, 3, 3, 1 :: Int]) -- [1,2,3,1]
```

## Típusosztályok, Semigroup és Monoid
<!-- q: Hogyan definiáljak saját típusosztályt és példányokat Haskellben? -->
<!-- tags: type class, instance, semigroup, monoid, default method, existential -->

A típusosztály egy interfész, amelyet típusonként külön példány (`instance`) valósít meg; a fordító a típusból választja ki a megfelelő implementációt (ad-hoc polimorfizmus), futásidőben ez egy rejtett „szótár” paraméter. Lehetnek alapértelmezett metódusok és szülőosztályok (`class Eq a => Ord a`). A `Semigroup` (asszociatív `<>`) és a `Monoid` (`mempty` egységelem) azért fontos, mert asszociatív kombinálásnál a feldolgozás tetszőlegesen darabolható és párhuzamosítható, a `foldMap` pedig bármilyen `Foldable`-ön működik. Buktató: árva példányok (orphan instance — sem a típus, sem az osztály moduljában nem definiált) ütközhetnek, és a heterogén lista csak egzisztenciális típussal oldható meg.

```haskell
{-# LANGUAGE ExistentialQuantification #-}
import Data.List (maximumBy)
import Data.Ord (comparing)

-- Saját osztály alapértelmezett metódussal
class Shape a where
  area      :: a -> Double
  perimeter :: a -> Double
  describe  :: a -> String
  describe x = "terület=" ++ show (area x) ++ ", kerület=" ++ show (perimeter x)

data Circle = Circle Double
data Rect   = Rect Double Double

instance Shape Circle where
  area (Circle r)      = pi * r * r
  perimeter (Circle r) = 2 * pi * r

instance Shape Rect where
  area (Rect w h)      = w * h
  perimeter (Rect w h) = 2 * (w + h)
  describe r           = "téglalap, " ++ show (area r) ++ " m2"   -- felülírás

-- Egzisztenciális burok: különböző Shape-ek egy listában
data AnyShape = forall s. Shape s => AnyShape s

instance Shape AnyShape where
  area (AnyShape s)      = area s
  perimeter (AnyShape s) = perimeter s
  describe (AnyShape s)  = describe s

-- Megszorított polimorf függvény: bármely Shape listán működik
largest :: Shape a => [a] -> Maybe a
largest [] = Nothing
largest xs = Just (maximumBy (comparing area) xs)

-- Statisztika Monoidként: asszociatív, tehát darabokban/párhuzamosan is összevonható
data Stats = Stats
  { count :: !Int
  , total :: !Double
  , minV  :: !Double
  , maxV  :: !Double
  } deriving Show

instance Semigroup Stats where
  Stats c1 t1 lo1 hi1 <> Stats c2 t2 lo2 hi2 =
    Stats (c1 + c2) (t1 + t2) (min lo1 lo2) (max hi1 hi2)

instance Monoid Stats where
  mempty = Stats 0 0 (1 / 0) (-1 / 0)   -- +végtelen / -végtelen az egységelem

single :: Double -> Stats
single x = Stats 1 x x x

mean :: Stats -> Maybe Double
mean s
  | count s == 0 = Nothing
  | otherwise    = Just (total s / fromIntegral (count s))

main :: IO ()
main = do
  let shapes = [AnyShape (Circle 1), AnyShape (Rect 2 3), AnyShape (Circle 2)]
  mapM_ (putStrLn . describe) shapes
  print (fmap area (largest shapes))
  -- Két „darab” külön összesítve, majd <>-val egyesítve = ugyanaz, mint egyben
  let chunkA = foldMap single [3, 1, 4]
      chunkB = foldMap single [1, 5, 9, 2]
  print (chunkA <> chunkB)
  print (mean (chunkA <> chunkB))
```

## Functor, Applicative és Monad saját típusra
<!-- q: Mi a különbség a Functor, Applicative és Monad között, és hogyan írjak saját példányt? -->
<!-- tags: functor, applicative, monad, state monad, do notation, laws -->

A `Functor` egy kontextuson belüli értéket alakít át (`fmap`), az `Applicative` több, egymástól független kontextusos értéket kombinál (`<*>`, `pure`), a `Monad` pedig olyan láncolást enged, ahol a következő lépés az előző eredményétől függ (`>>=`, `do`-blokk). Minden Monad egyben Applicative és Functor, ezért mindhárom példányt meg kell írni. A legjobb módja megérteni, ha egy `State` monádot kézzel implementálunk: ez egy `s -> (a, s)` függvény, amelyet a `>>=` a háttérben továbbfűz. A törvényeket (pl. `pure a >>= f == f a`, asszociativitás) a fordító nem ellenőrzi — ha sérülnek, a `do`-blokkok refaktorálása megváltoztathatja a viselkedést.

```haskell
-- Állapotkezelő monád nulláról: egy állapotot továbbadó függvény burka
newtype State s a = State { runState :: s -> (a, s) }

instance Functor (State s) where
  -- az eredményt alakítjuk, az állapot érintetlen
  fmap f (State g) = State $ \s -> let (a, s') = g s in (f a, s')

instance Applicative (State s) where
  pure a = State $ \s -> (a, s)
  -- előbb a függvényt, majd az argumentumot futtatjuk, az állapotot fűzve
  State sf <*> State sa = State $ \s ->
    let (f, s1) = sf s
        (a, s2) = sa s1
    in (f a, s2)

instance Monad (State s) where
  -- a k folytatás az előző eredménytől függ: ezt az Applicative nem tudja
  State g >>= k = State $ \s ->
    let (a, s1) = g s
    in runState (k a) s1

get :: State s s
get = State $ \s -> (s, s)

put :: s -> State s ()
put s = State $ \_ -> ((), s)

evalState :: State s a -> s -> a
evalState m s = fst (runState m s)

-- Egyedi azonosító generátor
fresh :: State Int Int
fresh = do
  n <- get
  put (n + 1)
  pure n

data Tree a = Leaf | Node (Tree a) a (Tree a) deriving Show

-- In-order sorszámozás monadikus stílusban
label :: Tree a -> State Int (Tree (Int, a))
label Leaf = pure Leaf
label (Node l x r) = do
  l' <- label l
  n  <- fresh
  r' <- label r
  pure (Node l' (n, x) r')

-- Ugyanez applikatív stílusban: a lépések függetlenek, a sorrend balról jobbra
labelA :: Tree a -> State Int (Tree (Int, a))
labelA Leaf         = pure Leaf
labelA (Node l x r) = Node <$> labelA l <*> ((\n -> (n, x)) <$> fresh) <*> labelA r

main :: IO ()
main = do
  let t = Node (Node Leaf 'a' Leaf) 'b' (Node Leaf 'c' Leaf)
  print (evalState (label t) 100)
  print (evalState (labelA t) 0)
  -- Maybe mint Applicative: független számítások, bármelyik hiánya Nothing
  print ((+) <$> Just 3 <*> Just 4)          -- Just 7
  print ((+) <$> Just 3 <*> (Nothing :: Maybe Int))
```

## Foldable és Traversable
<!-- q: Mire való a traverse és a Traversable típusosztály Haskellben? -->
<!-- tags: foldable, traversable, traverse, sequenceA, foldMap, validation, applicative -->

A `Foldable` bármilyen „tárolót” összegezni enged (`foldr`, `foldMap`, `sum`, `length`, `elem`), a `Traversable` pedig úgy járja be a szerkezetet, hogy közben egy applikatív hatást is végrehajt, és a szerkezet alakja megmarad: `traverse :: Applicative f => (a -> f b) -> t a -> f (t b)`. Így lesz egy `[String]`-ből `Maybe [Int]` (az első hibánál `Nothing`), vagy `IO`-ban egy fa minden elemére művelet. A `DeriveTraversable` kiterjesztéssel saját típusra is automatikusan származtatható. Érdekes következmény: ha az applikatív hibát halmoz (`Validation`), a `traverse` minden hibát összegyűjt — ezt monáddal nem lehet, mert ott az első hiba megszakítja a láncot.

```haskell
{-# LANGUAGE DeriveTraversable #-}
import Data.Foldable (for_, toList)
import Text.Read (readMaybe)

-- Rózsafa: tetszőleges számú gyerek; mindhárom osztály automatikusan származtatva
data Rose a = Rose a [Rose a]
  deriving (Show, Functor, Foldable, Traversable)

-- Az első hibánál megáll
parseAll :: [String] -> Maybe [Int]
parseAll = traverse readMaybe

-- Hibaüzenettel, szintén az első hibánál áll meg (Either monád)
parseAllE :: [String] -> Either String [Int]
parseAllE = traverse (\s -> maybe (Left ("rossz szám: " ++ s)) Right (readMaybe s))

-- Hibagyűjtő applikatív: NEM monád, ezért mindkét ágat ki tudja értékelni
data Validation e a = Failure e | Success a deriving Show

instance Functor (Validation e) where
  fmap _ (Failure e) = Failure e
  fmap f (Success a) = Success (f a)

instance Semigroup e => Applicative (Validation e) where
  pure = Success
  Failure e1 <*> Failure e2 = Failure (e1 <> e2)   -- itt halmozódnak a hibák
  Failure e1 <*> Success _  = Failure e1
  Success _  <*> Failure e2 = Failure e2
  Success f  <*> Success a  = Success (f a)

validateAll :: [String] -> Validation [String] [Int]
validateAll = traverse check
  where
    check s = maybe (Failure ["rossz szám: " ++ s]) Success (readMaybe s)

main :: IO ()
main = do
  print (parseAll ["1", "2", "3"])        -- Just [1,2,3]
  print (parseAll ["1", "x", "3"])        -- Nothing
  print (parseAllE ["1", "x", "y"])       -- Left "rossz szám: x"
  print (validateAll ["1", "x", "y"])     -- Failure ["rossz szám: x","rossz szám: y"]

  let tree = Rose 1 [Rose 2 [Rose 4 []], Rose 3 []] :: Rose Int
  -- Foldable: összeg, elemszám, keresés ingyen
  print (sum tree, length tree, maximum tree, 4 `elem` tree, toList tree)
  -- Traversable: a fa alakja megmarad, az elemek Maybe-be kerülnek
  print (traverse (\x -> if x > 0 then Just (x * 10) else Nothing) tree)
  -- for_ = flip traverse_: IO hatás minden elemre
  for_ tree $ \x -> putStrLn ("csúcs: " ++ show x)
  -- sequenceA: [Maybe a] -> Maybe [a]
  print (sequenceA [Just 1, Just 2, Nothing :: Maybe Int])
```

## Hibakezelés: Maybe, Either és kivételek
<!-- q: Hogyan kezeljem a hibákat Haskellben Either-rel és kivételekkel? -->
<!-- tags: error handling, either, maybe, exception, bracket, try, throwIO -->

Tiszta kódban a hiba érték: `Maybe` ha az ok érdektelen, `Either e` ha a hívónak tudnia kell, mi romlott el — az `Either` monád az első `Left`-nél rövidre zár, így a `do`-blokk olvasható marad. `IO`-ban a futtatókörnyezet kivételeket dob (fájl, hálózat), ezeket `try`/`catch`-csel fogd el típus szerint, saját kivételhez pedig `Exception` példány kell. Erőforrásokat mindig `bracket`-tel (vagy `withFile`-lal) kezelj, mert az aszinkron kivételek (pl. `killThread`, timeout) bármikor érkezhetnek. Buktatók: a tiszta kódban dobott `error`/`div 0` csak kiértékeléskor robban (ezért `evaluate` kell), és a lusta `readFile` a fájlt csak a tartalom elfogyasztása után zárja.

```haskell
{-# LANGUAGE ScopedTypeVariables #-}
import Control.Exception
import qualified Data.Map.Strict as M
import System.IO
import Text.Read (readMaybe)

-- Tartományi hibatípus: a hívó mintaillesztéssel kezelheti
data ConfigError
  = MissingKey String
  | BadValue String String
  deriving Show

data Config = Config { port :: Int, host :: String } deriving Show

lookupKey :: M.Map String String -> String -> Either ConfigError String
lookupKey m k = maybe (Left (MissingKey k)) Right (M.lookup k m)

readInt :: String -> String -> Either ConfigError Int
readInt k v = maybe (Left (BadValue k v)) Right (readMaybe v)

-- Az Either monád az első hibánál megáll
parseConfig :: M.Map String String -> Either ConfigError Config
parseConfig m = do
  h <- lookupKey m "host"
  p <- lookupKey m "port" >>= readInt "port"
  if p > 0 && p < 65536
    then pure (Config p h)
    else Left (BadValue "port" (show p))

-- Saját IO-kivétel
newtype AppException = InvalidInput String deriving Show
instance Exception AppException

-- bracket: megnyit, használ, és BÁRMI történik, lezár
firstLine :: FilePath -> IO (Either String String)
firstLine path = do
  r <- try (bracket (openFile path ReadMode) hClose hGetLine)
  pure $ case r of
    Left (e :: IOException) -> Left ("I/O hiba: " ++ show e)
    Right line              -> Right line

checkedDiv :: Int -> Int -> IO Int
checkedDiv _ 0 = throwIO (InvalidInput "nullával osztás")
checkedDiv a b = pure (a `div` b)

main :: IO ()
main = do
  print (parseConfig (M.fromList [("host", "localhost"), ("port", "8080")]))
  print (parseConfig (M.fromList [("host", "localhost"), ("port", "abc")]))
  print (parseConfig (M.fromList [("port", "80")]))

  firstLine "nem-letezo.txt" >>= print

  -- Saját kivétel elkapása típus szerint
  r <- try (checkedDiv 10 0)
  case r of
    Left (InvalidInput msg) -> putStrLn ("elkapva: " ++ msg)
    Right v                 -> print v

  -- Tiszta kódban rejlő hiba: az evaluate kényszeríti a kiértékelést a try-on belül
  r2 <- try (evaluate (1 `div` (0 :: Int)))
  case r2 of
    Left (e :: ArithException) -> putStrLn ("aritmetikai hiba: " ++ show e)
    Right v                    -> print v
```

## Monad transzformerek
<!-- q: Hogyan kombináljak több monádot (Reader, State, Except) monad transzformerekkel? -->
<!-- tags: monad transformer, readert, statet, exceptt, mtl, lift, liftio -->

Ha egy számításnak egyszerre kell konfigurációt olvasnia (`Reader`), állapotot vinnie (`State`), hibát jeleznie (`Except`) és IO-t végeznie, a transzformerekkel rétegzett monád-stacket építünk: `ReaderT Config (StateT s (ExceptT e IO))`. Az `mtl` osztályai (`asks`, `get`, `throwError`) automatikusan a megfelelő rétegig emelnek, `liftIO` pedig a legalsó IO-ig. A futtatás kívülről befelé, rétegenként történik (`runReaderT`, majd `runStateT`, majd `runExceptT`). Fontos buktató a rétegek sorrendje: `StateT s (ExceptT e m)` esetén hiba után az állapot elvész (a `catchError` visszagörgeti), `ExceptT e (StateT s m)` esetén megmarad — tudatosan válassz.

```haskell
import Control.Monad (when)
import Control.Monad.Except (ExceptT, catchError, runExceptT, throwError)
import Control.Monad.IO.Class (liftIO)
import Control.Monad.Reader (ReaderT, asks, runReaderT)
import Control.Monad.State.Strict (StateT, get, put, runStateT)

data Config = Config
  { maxItems :: Int
  , verbose  :: Bool
  }

-- A teljes alkalmazás-monád: konfig + kosár állapot + hiba + IO
type App = ReaderT Config (StateT [String] (ExceptT String IO))

addItem :: String -> App ()
addItem item = do
  limit <- asks maxItems              -- Reader réteg
  items <- get                        -- State réteg (automatikus lift)
  when (length items >= limit) $
    throwError ("betelt a kosár (" ++ show limit ++ " tétel), elutasítva: " ++ item)
  v <- asks verbose
  when v $ liftIO (putStrLn ("hozzáadva: " ++ item))   -- IO a legalján
  put (item : items)

-- Hiba elkapása és továbblépés
safeAdd :: String -> App ()
safeAdd item = addItem item `catchError` \err ->
  liftIO (putStrLn ("figyelmeztetés: " ++ err))

-- Rétegenként „lehámozzuk” a stacket
runApp :: Config -> App a -> IO (Either String (a, [String]))
runApp cfg app = runExceptT (runStateT (runReaderT app cfg) [])

main :: IO ()
main = do
  -- Az első hiba az egész futást megszakítja: Left
  r1 <- runApp (Config 2 True) (mapM_ addItem ["alma", "körte", "szilva"])
  print r1
  -- catchError-ral a hiba lokális marad: Right ((), ["körte","alma"])
  r2 <- runApp (Config 2 False) (mapM_ safeAdd ["alma", "körte", "szilva"])
  print r2
```

## mtl-stílus és a ReaderT pattern
<!-- q: Hogyan írjak tesztelhető, képesség-alapú (mtl-stílusú) Haskell alkalmazáskódot? -->
<!-- tags: mtl, readert pattern, capability, newtype deriving, monadio, testing -->

Konkrét stack helyett az üzleti függvények csak a szükséges *képességeket* kérik típusosztály-megszorításként (`MonadReader Env m`, `MonadLogger m`), így ugyanaz a kód éles `IO`-ban és tiszta teszt-monádban is fut. A „ReaderT pattern” szerint az éles alkalmazás egy `newtype App a = App (ReaderT Env IO a)`, ahol a változó állapot `IORef`/`TVar` az `Env`-ben él — ez kivételbiztos és szálbiztos, szemben a `StateT`-vel, amelynek állapota kivételnél elvész. A példányokat `GeneralizedNewtypeDeriving` származtatja a newtype alatti típusból. Buktató: túl sok egyedi képesség-osztály nehezen követhető kódot ad, és a polimorf kód lassabb lehet, ha a GHC nem specializálja (`{-# SPECIALIZE #-}`, `-O2`).

```haskell
{-# LANGUAGE FlexibleContexts #-}
{-# LANGUAGE GeneralizedNewtypeDeriving #-}
import Control.Monad.IO.Class (MonadIO, liftIO)
import Control.Monad.Reader (MonadReader, ReaderT, asks, runReaderT)
import Control.Monad.Writer (MonadWriter, Writer, runWriter, tell)
import Data.IORef

-- Környezet: konfiguráció + változó állapot IORef-ben
data Env = Env
  { envPrefix  :: String
  , envCounter :: IORef Int
  }

-- Éles alkalmazás-monád; a példányok a ReaderT Env IO-ból jönnek
newtype App a = App { unApp :: ReaderT Env IO a }
  deriving (Functor, Applicative, Monad, MonadIO, MonadReader Env)

runApp :: Env -> App a -> IO a
runApp env app = runReaderT (unApp app) env

-- Képesség-osztály: naplózás
class Monad m => MonadLogger m where
  logMsg :: String -> m ()

instance MonadLogger App where
  logMsg msg = do
    prefix <- asks envPrefix
    liftIO (putStrLn (prefix ++ msg))

-- Teszt-monád: a naplóüzeneteket listába gyűjti, semmi IO
newtype TestM a = TestM (Writer [String] a)
  deriving (Functor, Applicative, Monad, MonadWriter [String])

instance MonadLogger TestM where
  logMsg m = tell [m]

runTestM :: TestM a -> (a, [String])
runTestM (TestM w) = runWriter w

-- Üzleti logika: csak naplózni tud, bármely MonadLogger-ben fut
greetAll :: MonadLogger m => [String] -> m Int
greetAll names = do
  mapM_ (\n -> logMsg ("Szia, " ++ n ++ "!")) names
  pure (length names)

-- Ez már a környezetet és IO-t is igényli
incrementAndLog :: (MonadReader Env m, MonadIO m, MonadLogger m) => m Int
incrementAndLog = do
  ref <- asks envCounter
  n <- liftIO (atomicModifyIORef' ref (\x -> (x + 1, x + 1)))
  logMsg ("számláló: " ++ show n)
  pure n

main :: IO ()
main = do
  ref <- newIORef 0
  let env = Env "[app] " ref
  n <- runApp env (greetAll ["Anna", "Bence"] >> incrementAndLog >> incrementAndLog)
  print n                                   -- 2
  -- Ugyanaz a greetAll tisztán tesztelve
  print (runTestM (greetAll ["Teszt"]))     -- (1,["Szia, Teszt!"])
```

## Rekordok: mezők, frissítés, pont-szintaxis
<!-- q: Hogyan használjam a rekordokat Haskellben (OverloadedRecordDot, RecordWildCards)? -->
<!-- tags: records, overloadedrecorddot, recordwildcards, namedfieldpuns, duplicaterecordfields -->

A rekord egy nevesített mezős szorzattípus; a mezőnevekből automatikusan getter függvények lesznek, a frissítés pedig új példányt ad (`r { mezo = uj }`), az eredeti változatlan marad. Régen gond volt, hogy két rekord nem használhatta ugyanazt a mezőnevet, és a beágyazott frissítés nagyon bőbeszédű. Modern GHC-n (9.2+) az `OverloadedRecordDot` adja a `c.address.city` olvasást, a `DuplicateRecordFields` engedi az azonos mezőneveket, a `RecordWildCards` (`Product{..}`) és a `NamedFieldPuns` pedig kényelmes mintaillesztést. Buktató: duplikált mezőnevű rekord frissítése (`x { name = .. }`) kétértelmű lehet, mélyen beágyazott frissítésre inkább lencséket használj.

```haskell
{-# LANGUAGE DuplicateRecordFields #-}
{-# LANGUAGE NamedFieldPuns #-}
{-# LANGUAGE OverloadedRecordDot #-}
{-# LANGUAGE RecordWildCards #-}

data Address = Address { city :: String, zipCode :: String } deriving Show

-- Mindkét rekordnak van "name" mezője: a DuplicateRecordFields engedi
data Customer = Customer
  { name    :: String
  , address :: Address
  , credit  :: Int
  } deriving Show

data Product = Product { name :: String, price :: Int } deriving Show

-- Pont-szintaxis: beágyazott olvasás, a típusból egyértelmű
label :: Customer -> String
label c = c.name ++ " (" ++ c.address.city ++ ")"

-- RecordWildCards: minden mező lokális változóként elérhető
render :: Product -> String
render Product{..} = name ++ ": " ++ show price ++ " Ft"

-- NamedFieldPuns: csak a szükséges mezőket bontjuk ki
canAfford :: Customer -> Product -> Bool
canAfford Customer{credit} Product{price} = credit >= price

-- Beágyazott frissítés: működik, de bőbeszédű (ezért léteznek a lencsék)
relocate :: String -> Customer -> Customer
relocate newCity c = c { address = (c.address) { city = newCity } }

-- Vásárlás: új Customer jön létre, a régi érték változatlan
buy :: Product -> Customer -> Either String Customer
buy p c
  | canAfford c p = Right c { credit = c.credit - p.price }
  | otherwise     = Left (c.name ++ " nem tudja megvenni: " ++ p.name)

main :: IO ()
main = do
  let cust = Customer "Kata" (Address "Kecskemét" "6000") 5000
      book = Product "Haskell könyv" 4200
  putStrLn (label cust)
  putStrLn (render book)
  print (buy book cust)
  putStrLn (label (relocate "Szeged" cust))
```

## Lencsék (lens)
<!-- q: Mik azok a lencsék Haskellben és hogyan frissítsek mélyen beágyazott adatot? -->
<!-- tags: lens, van laarhoven, getter, setter, traversal, optics, control.lens -->

A lencse egy összetehető getter+setter pár, amely egy nagyobb struktúra egy részére fókuszál; a van Laarhoven-kódolásban egyszerűen egy `(a -> f a) -> s -> f s` függvény, ezért a lencsék sima függvénykompozícióval (`.`) fűzhetők. A `Const` funktorral olvasunk (`view`), az `Identity`-vel írunk (`over`, `set`) — ugyanaz a lencse mindkettőre jó. A `lens` könyvtár ezt kiegészíti traversal-okkal (több elemre fókuszálás), prizmákkal (összegtípusok) és Template Haskell-es generálással (`makeLenses`). Buktató: a `lens` nagy függőség és bonyolult típushibákat ad; kisebb projektben a `microlens` vagy az `optics` könnyebb alternatíva.

```haskell
{-# LANGUAGE RankNTypes #-}
import Data.Functor.Const (Const (..))
import Data.Functor.Identity (Identity (..))

-- A lencse típusa: bármely Functor f-re működő függvény
type Lens s a = forall f. Functor f => (a -> f a) -> s -> f s

-- Lencse gyártása getterből és setterből
lens :: (s -> a) -> (s -> a -> s) -> Lens s a
lens getter setter f s = setter s <$> f (getter s)

-- Olvasás: a Const funktor "elnyeli" az értéket, a setter nem fut
view :: Lens s a -> s -> a
view l s = getConst (l Const s)

-- Módosítás: az Identity funktor átengedi az új értéket
over :: Lens s a -> (a -> a) -> s -> s
over l g = runIdentity . l (Identity . g)

set :: Lens s a -> a -> s -> s
set l a = over l (const a)

data Address = Address { _city :: String, _street :: String } deriving Show
data Person  = Person  { _name :: String, _address :: Address } deriving Show

city :: Lens Address String
city = lens _city (\a c -> a { _city = c })

address :: Lens Person Address
address = lens _address (\p a -> p { _address = a })

main :: IO ()
main = do
  let p = Person "Dóra" (Address "Kecskemét" "Fő utca 1.")
  -- A lencsék sima (.)-tal komponálhatók, kívülről befelé
  print (view (address . city) p)
  print (set (address . city) "Szeged" p)
  print (over (address . city) (map succ) p)
```

Ugyanez a `lens` könyvtárral, generált lencsékkel és traversal-lal:

```haskell
{-# LANGUAGE TemplateHaskell #-}
import Control.Lens

data Item  = Item  { _itemName :: String, _price :: Int } deriving Show
data Order = Order { _orderId :: Int, _items :: [Item] } deriving Show

makeLenses ''Item   -- létrehozza: itemName, price
makeLenses ''Order  -- létrehozza: orderId, items

main :: IO ()
main = do
  let o = Order 1 [Item "toll" 300, Item "füzet" 900]
  print (o ^. orderId)                          -- olvasás
  print (o ^.. items . traverse . price)        -- minden ár listában
  print (o & items . traverse . price %~ (* 2)) -- minden ár duplázása
  print (sumOf (items . traverse . price) o)    -- 1200
```

## GADT-k: típusos kifejezésfák
<!-- q: Mik azok a GADT-k Haskellben és mire használjam őket? -->
<!-- tags: gadt, generalized algebraic data types, type refinement, existential, type equality -->

A GADT (Generalized Algebraic Data Type) olyan adattípus, ahol minden konstruktor saját, pontosított visszatérési típust kaphat (`IntE :: Int -> Expr Int`). Mintaillesztéskor a fordító ebből *finomítja* a típust, így egy kiértékelő `Expr a -> a` típusú lehet, és rosszul tipizált fa (pl. `Add (BoolE True) ..`) létre sem hozható. Típusellenőrzött DSL-eknél, protokoll-állapotgépeknél, típusos AST-knél hasznos. Buktató: GADT-mintaillesztésnél gyakran kell explicit típusaláírás, és típusozatlan bemenetből (parser kimenet) futásidejű típusellenőrzéssel kell típusos fát építeni — ezt egy típus-tanú (`Ty a`) és a `:~:` egyenlőség segíti.

```haskell
{-# LANGUAGE GADTs #-}
import Data.Type.Equality ((:~:) (..))

-- Típusos kifejezés: a típusparaméter az eredmény típusa
data Expr a where
  IntE  :: Int -> Expr Int
  BoolE :: Bool -> Expr Bool
  Add   :: Expr Int -> Expr Int -> Expr Int
  Eq    :: Expr Int -> Expr Int -> Expr Bool
  If    :: Expr Bool -> Expr a -> Expr a -> Expr a

-- Nincs futásidejű típushiba: a típusrendszer garantálja a helyességet
eval :: Expr a -> a
eval (IntE n)   = n
eval (BoolE b)  = b
eval (Add x y)  = eval x + eval y
eval (Eq x y)   = eval x == eval y
eval (If c t e) = if eval c then eval t else eval e

-- Típus-tanú és egzisztenciális burok a futásidejű ellenőrzéshez
data Ty a where
  TInt  :: Ty Int
  TBool :: Ty Bool

data Typed where
  Typed :: Show a => Ty a -> Expr a -> Typed

-- Típusozatlan AST, pl. egy parser kimenete
data UExpr = UInt Int | UBool Bool | UAdd UExpr UExpr | UIf UExpr UExpr UExpr

sameTy :: Ty a -> Ty b -> Maybe (a :~: b)
sameTy TInt TInt   = Just Refl
sameTy TBool TBool = Just Refl
sameTy _ _         = Nothing

typecheck :: UExpr -> Either String Typed
typecheck (UInt n)   = Right (Typed TInt (IntE n))
typecheck (UBool b)  = Right (Typed TBool (BoolE b))
typecheck (UAdd a b) = Typed TInt <$> (Add <$> asInt a <*> asInt b)
typecheck (UIf c t e) = do
  ec <- asBool c
  rt <- typecheck t
  re <- typecheck e
  case (rt, re) of
    (Typed tt et, Typed te ee) -> case sameTy tt te of
      Just Refl -> Right (Typed tt (If ec et ee))  -- itt a két ág típusa bizonyítottan azonos
      Nothing   -> Left "az if ágai eltérő típusúak"

asInt :: UExpr -> Either String (Expr Int)
asInt u = typecheck u >>= \r -> case r of
  Typed TInt e -> Right e
  Typed _ _    -> Left "Int típust vártam"

asBool :: UExpr -> Either String (Expr Bool)
asBool u = typecheck u >>= \r -> case r of
  Typed TBool e -> Right e
  Typed _ _     -> Left "Bool típust vártam"

run :: UExpr -> String
run u = either ("típushiba: " ++) (\(Typed _ e) -> show (eval e)) (typecheck u)

main :: IO ()
main = do
  print (eval (If (Eq (IntE 2) (Add (IntE 1) (IntE 1))) (IntE 10) (IntE 20)))
  putStrLn (run (UIf (UBool True) (UAdd (UInt 2) (UInt 3)) (UInt 0)))
  putStrLn (run (UAdd (UInt 1) (UBool True)))
```

## Type families és típusszintű programozás
<!-- q: Mik azok a type family-k Haskellben és hogyan számoljak típusszinten? -->
<!-- tags: type families, associated types, datakinds, type level, vector length -->

A type family típusszintű függvény: típusokból típust számol. Az *asszociált* type family egy típusosztályhoz kötött (pl. egy tároló elemtípusa: `Elem [a] = a`), a *zárt* type family felülről lefelé illesztett egyenletekből áll. `DataKinds`-szel a saját adattípusok (pl. `Nat = Z | S Nat`) típusszintre emelődnek, így GADT-vel hossz-indexelt vektor készíthető: a `vhead` üres vektorra le sem fordul, a `vappend` eredményének hosszát a `Plus` család számolja. Buktató: a típusszintű kód nehezen debugolható és bonyolult hibaüzeneteket ad; csak ott használd, ahol a garancia valóban megéri.

```haskell
{-# LANGUAGE DataKinds, GADTs, KindSignatures, TypeFamilies #-}
import qualified Data.Set as Set

-- Asszociált típuscsalád: minden tároló megmondja, mi az eleme
class Container f where
  type Elem f
  empty  :: f
  insert :: Elem f -> f -> f
  toL    :: f -> [Elem f]

instance Container [a] where
  type Elem [a] = a
  empty  = []
  insert = (:)
  toL    = id

instance Ord a => Container (Set.Set a) where
  type Elem (Set.Set a) = a
  empty  = Set.empty
  insert = Set.insert
  toL    = Set.toList

fromL :: Container f => [Elem f] -> f
fromL = foldr insert empty

-- Típusszintű természetes számok és zárt típuscsalád az összeadásra
data Nat = Z | S Nat

type family Plus (m :: Nat) (n :: Nat) :: Nat where
  Plus 'Z n     = n
  Plus ('S m) n = 'S (Plus m n)

-- Hossz-indexelt vektor
data Vec (n :: Nat) a where
  VNil  :: Vec 'Z a
  VCons :: a -> Vec n a -> Vec ('S n) a

vhead :: Vec ('S n) a -> a          -- csak nem üres vektorra hívható
vhead (VCons x _) = x

vappend :: Vec m a -> Vec n a -> Vec (Plus m n) a
vappend VNil ys         = ys
vappend (VCons x xs) ys = VCons x (vappend xs ys)

-- Csak azonos hosszú vektorok zipelhetők: az eltérés fordítási hiba
vzip :: Vec n a -> Vec n b -> Vec n (a, b)
vzip VNil VNil                 = VNil
vzip (VCons x xs) (VCons y ys) = VCons (x, y) (vzip xs ys)

vtoList :: Vec n a -> [a]
vtoList VNil         = []
vtoList (VCons x xs) = x : vtoList xs

main :: IO ()
main = do
  print (toL (fromL [3, 1, 3, 2] :: [Int]))        -- [3,1,3,2]
  print (toL (fromL [3, 1, 3, 2] :: Set.Set Int))  -- [1,2,3]
  let v1 = VCons 1 (VCons 2 VNil) :: Vec ('S ('S 'Z)) Int
  print (vhead (vappend v1 v1))
  print (vtoList (vzip v1 (VCons 'a' (VCons 'b' VNil))))
  -- print (vhead VNil)  -- fordítási hiba: 'Z nem illeszkedik 'S n-re
```

## STM: tranzakciós memória
<!-- q: Hogyan használjam az STM-et (TVar, retry, orElse) konkurens Haskell kódban? -->
<!-- tags: stm, tvar, retry, orelse, tbqueue, concurrency, atomically -->

A Software Transactional Memory lehetővé teszi, hogy több megosztott változót (`TVar`) zárak nélkül, atomikusan módosítsunk: az `atomically` blokk vagy teljesen lefut, vagy ütközés esetén automatikusan újraindul. A `retry` (és a ráépülő `check`) blokkolja a tranzakciót, amíg az olvasott `TVar`-ok valamelyike meg nem változik — így feltételes várakozás írható busy-wait nélkül; az `orElse` alternatívát ad, ha az első ág retry-olna. A típus garantálja, hogy a tranzakcióban nincs IO, ezért az újrafuttatás biztonságos és zár-alapú deadlock nincs. Buktató: a hosszú, sok `TVar`-t érintő tranzakciók gyakran ütköznek és kiéheztethetők, ezért tartsd őket rövidnek.

```haskell
import Control.Concurrent (forkIO)
import Control.Concurrent.STM
import Control.Monad (forM_, replicateM_)

type Account = TVar Int

-- Atomikus átutalás: ha nincs fedezet, a check retry-t hív és vár
transfer :: Account -> Account -> Int -> STM ()
transfer from to amount = do
  bal <- readTVar from
  check (bal >= amount)
  modifyTVar' from (subtract amount)
  modifyTVar' to (+ amount)

-- Nem blokkoló változat: orElse-szel False, ha az első ág retry-olna
tryTransfer :: Account -> Account -> Int -> STM Bool
tryTransfer from to amount =
  (transfer from to amount >> pure True) `orElse` pure False

-- Worker: korlátos sorból olvas; Nothing = leállási jel
worker :: TBQueue (Maybe Int) -> TVar Int -> TVar Int -> IO ()
worker q total finished = loop
  where
    loop = do
      job <- atomically (readTBQueue q)
      case job of
        Nothing -> atomically (modifyTVar' finished (+ 1))
        Just n  -> atomically (modifyTVar' total (+ n)) >> loop

main :: IO ()
main = do
  a <- newTVarIO 100
  b <- newTVarIO 0
  ok1 <- atomically (tryTransfer a b 70)
  ok2 <- atomically (tryTransfer a b 70)      -- csak 30 maradt: False
  balances <- atomically ((,) <$> readTVar a <*> readTVar b)
  print (ok1, ok2, balances)                   -- (True,False,(30,70))

  q <- newTBQueueIO 16                         -- tele sornál az író blokkol
  total <- newTVarIO 0
  finished <- newTVarIO 0
  let nWorkers = 4
  replicateM_ nWorkers (forkIO (worker q total finished))
  forM_ [1 .. 1000] $ \i -> atomically (writeTBQueue q (Just i))
  replicateM_ nWorkers (atomically (writeTBQueue q Nothing))
  -- Várakozás busy-wait nélkül: csak a finished változásakor fut újra
  atomically $ readTVar finished >>= \f -> check (f == nWorkers)
  readTVarIO total >>= print                   -- 500500
```

## Parser kombinátorok (megaparsec)
<!-- q: Hogyan írjak parsert Haskellben parser kombinátorokkal (megaparsec)? -->
<!-- tags: parser combinators, megaparsec, makeexprparser, lexer, parsing, dsl -->

A parser kombinátor kis, típusos parserekből (`Parser a`) épít nagyobbakat Applicative/Monad műveletekkel (`<$>`, `<*>`, `<|>`, `many`, `sepBy`), így a nyelvtan közvetlenül Haskell-kódként olvasható, külön generátor nélkül. A megaparsec jó hibaüzeneteket ad (`errorBundlePretty`), a `Lexer` modul kezeli a whitespace-t és a kommenteket (lexeme-konvenció: minden token elnyeli a mögötte lévő szóközt), a `makeExprParser` pedig precedencia-táblából épít operátor-kifejezést. Buktató: a megaparsec nem backtrackel, ha egy ág már fogyasztott bemenetet — ilyenkor `try` kell (pl. kulcsszó vs. azonosító), és balrekurzív szabály közvetlenül nem írható.

```haskell
{-# LANGUAGE OverloadedStrings #-}
import Control.Monad.Combinators.Expr (Operator (..), makeExprParser)
import Data.Text (Text)
import Data.Void (Void)
import Text.Megaparsec
import Text.Megaparsec.Char
import qualified Text.Megaparsec.Char.Lexer as L

type Parser = Parsec Void Text

data Expr = Num Integer | Var String | Neg Expr | Bin Char Expr Expr | Let String Expr Expr
  deriving Show

-- Whitespace és kommentek elnyelése; minden token után ez fut
sc :: Parser ()
sc = L.space space1 (L.skipLineComment "--") (L.skipBlockComment "{-" "-}")

lexeme :: Parser a -> Parser a
lexeme = L.lexeme sc

symbol :: Text -> Parser Text
symbol = L.symbol sc

-- Kulcsszó: utána nem jöhet betű ("letter" nem "let"); try a visszalépéshez
keyword :: Text -> Parser Text
keyword kw = lexeme (try (string kw <* notFollowedBy alphaNumChar))

identifier :: Parser String
identifier = lexeme (try (ident >>= reject)) <?> "azonosító"
  where
    ident = (:) <$> letterChar <*> many alphaNumChar
    reject x | x `elem` ["let", "in"] = fail ("foglalt szó: " ++ x)
             | otherwise              = pure x

term :: Parser Expr
term = choice
  [ between (symbol "(") (symbol ")") expr
  , Num <$> lexeme L.decimal
  , Let <$> (keyword "let" *> identifier) <*> (symbol "=" *> expr) <*> (keyword "in" *> expr)
  , Var <$> identifier
  ]

-- Precedencia-tábla: felül a legerősebb kötés
expr :: Parser Expr
expr = makeExprParser term
  [ [Prefix (Neg <$ symbol "-")]
  , [InfixL (Bin '*' <$ symbol "*"), InfixL (Bin '/' <$ symbol "/")]
  , [InfixL (Bin '+' <$ symbol "+"), InfixL (Bin '-' <$ symbol "-")]
  ]

parseExpr :: Text -> Either String Expr
parseExpr src = either (Left . errorBundlePretty) Right (parse (sc *> expr <* eof) "<bemenet>" src)

main :: IO ()
main = mapM_ (print . parseExpr)
  ["1 + 2 * 3", "let x = 5 in x * (x - 1) -- komment", "3 + * 4"]
```

## Tulajdonság-alapú tesztelés QuickCheck-kel
<!-- q: Hogyan teszteljek QuickCheck-kel tulajdonság-alapon Haskellben? -->
<!-- tags: quickcheck, property based testing, arbitrary, shrink, generators, testing -->

A QuickCheck konkrét példák helyett *tulajdonságokat* (invariánsokat) fogalmaz meg, és véletlen bemenetekkel százszor-ezerszer ellenőrzi őket; hiba esetén *shrinkeléssel* a legkisebb ellenpéldát keresi meg. Saját típushoz `Arbitrary` példány kell: a generátor lehetőleg konstruktívan állítson elő érvényes értéket (a `suchThat`/`==>` szűrés sok bemenetet eldob), a `shrink` adjon kisebb, de még érvényes jelölteket. Jó tulajdonságok: roundtrip (`decode . encode == id`), idempotencia, invariánsok, egyezés egy egyszerű referencia-implementációval. Buktató: gyenge generátorral csak triviális esetek futnak — a `classify`/`label` megmutatja az eloszlást.

```haskell
import Data.List (sort)
import qualified Data.List.NonEmpty as NE
import qualified Data.Set as Set
import Test.QuickCheck

-- Futáshossz-kódolás: roundtrip tulajdonság
rle :: String -> [(Char, Int)]
rle = map (\g -> (NE.head g, NE.length g)) . NE.group

unrle :: [(Char, Int)] -> String
unrle = concatMap (\(c, n) -> replicate n c)

prop_roundtrip :: String -> Bool
prop_roundtrip s = unrle (rle s) == s

-- Zárt intervallum invariánssal: lo <= hi
data Interval = Interval Int Int deriving (Show, Eq, Ord)

instance Arbitrary Interval where
  -- Konstruktív generálás: mindig érvényes, semmit nem dobunk el
  arbitrary = do
    lo  <- choose (-50, 50)
    len <- choose (0, 10)
    pure (Interval lo (lo + len))
  -- Kisebb, de továbbra is érvényes jelöltek
  shrink (Interval lo hi) =
    [Interval l (l + n) | (l, n) <- shrink (lo, hi - lo), n >= 0]

-- Átfedő vagy érintkező intervallumok összevonása
mergeIntervals :: [Interval] -> [Interval]
mergeIntervals = go . sort
  where
    go (Interval a b : Interval c d : rest)
      | c <= b + 1 = go (Interval a (max b d) : rest)
      | otherwise  = Interval a b : go (Interval c d : rest)
    go xs = xs

points :: [Interval] -> Set.Set Int
points is = Set.fromList [x | Interval a b <- is, x <- [a .. b]]

-- Ugyanazokat a pontokat fedi le, mint a bemenet
prop_samePoints :: [Interval] -> Bool
prop_samePoints is = points (mergeIntervals is) == points is

-- Rendezett és diszjunkt; classify mutatja az eloszlást
prop_disjoint :: [Interval] -> Property
prop_disjoint is =
  classify (length is > 5) "hosszú lista" $
    and (zipWith (\(Interval _ b) (Interval c _) -> b + 1 < c) m (drop 1 m))
  where m = mergeIntervals is

prop_idempotent :: [Interval] -> Bool
prop_idempotent is = mergeIntervals (mergeIntervals is) == mergeIntervals is

main :: IO ()
main = do
  quickCheck prop_roundtrip
  quickCheckWith stdArgs { maxSuccess = 1000 } prop_samePoints
  quickCheck prop_disjoint
  quickCheck prop_idempotent
```
