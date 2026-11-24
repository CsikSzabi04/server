# Gépi tanulás alapjai
<!-- tech: machine-learning -->
<!-- aliases: ml, machine learning, gépi tanulás, deep learning, neurális háló, pytorch, scikit-learn, llm, transformer -->

A gépi tanulás (ML) adatokból tanul meg egy függvényt ahelyett, hogy szabályokat kódolnánk: felügyelt tanulásnál címkézett példákból (regresszió, osztályozás), felügyelet nélkülinél szerkezetet keres (klaszterezés, dimenziócsökkentés). A munkafolyamat: adatgyűjtés és -tisztítás, train/validációs/teszt felosztás, modell és veszteségfüggvény választása, optimalizálás (gradiens-módszer), kiértékelés a feladathoz illő metrikával, majd üzemeltetés és monitorozás. Táblázatos adatra a gradient boosting (scikit-learn, XGBoost, LightGBM) a legerősebb kiindulás, képre, szövegre, hangra a mély neurális hálók (PyTorch), nyelvi feladatokra az előtanított LLM-ek RAG-gal vagy finomhangolással. A leggyakoribb hiba nem a modell, hanem az adat: szivárgás (leakage), rossz felosztás, félrevezető metrika.

## Lineáris regresszió nulláról NumPy-jal
<!-- q: Hogyan implementáljam a lineáris regressziót nulláról NumPy-ban? -->
<!-- tags: linear regression, numpy, least squares, normal equation, gradient descent, mse, r2 -->

A lineáris regresszió a célváltozót a feature-ök súlyozott összegeként modellezi (`ŷ = Xw + b`), és a négyzetes hiba (MSE) átlagát minimalizálja. Két megoldási út van: a zárt alak (normál egyenlet / legkisebb négyzetek, `np.linalg.lstsq`), ami kis feature-számnál pontos és gyors, illetve a gradiens-módszer, ami nagy adatra és más modellekre is általánosít. Gradiens-módszernél a feature-öket standardizálni kell, különben az eltérő skálák miatt lassú vagy instabil a konvergencia. Az `inv(XᵀX)` helyett `lstsq`/`solve` kell, mert numerikusan stabilabb; az R² azt mutatja, a variancia mekkora részét magyarázza a modell.

```python
import numpy as np

rng = np.random.default_rng(42)
n = 200
X = rng.uniform(0, 10, size=(n, 2))                 # két feature
true_w, true_b = np.array([3.0, -1.5]), 4.0
y = X @ true_w + true_b + rng.normal(0, 1.0, n)     # zajos lineáris kapcsolat

# 1) Zárt alak: legkisebb négyzetek; a bias-hoz egy csupa-1 oszlop
Xb = np.c_[np.ones(n), X]
w_closed, *_ = np.linalg.lstsq(Xb, y, rcond=None)   # stabilabb, mint inv(XᵀX) @ Xᵀy
print("zárt alak [b, w1, w2]:", w_closed.round(2))   # ~[4.0, 3.0, -1.5]

# 2) Gradiens-módszer az MSE-re
def fit_gd(X, y, lr=0.05, epochs=1000):
    mu, sigma = X.mean(0), X.std(0)
    Xs = (X - mu) / sigma                            # standardizálás: gyors, stabil konvergencia
    w, b = np.zeros(X.shape[1]), 0.0
    for _ in range(epochs):
        err = Xs @ w + b - y                         # előrejelzési hiba
        w -= lr * 2 * Xs.T @ err / len(y)            # dMSE/dw
        b -= lr * 2 * err.mean()                     # dMSE/db
    w_orig = w / sigma                               # vissza az eredeti skálára
    return w_orig, b - (mu * w_orig).sum()

w, b = fit_gd(X, y)
pred = X @ w + b
mse = np.mean((pred - y) ** 2)
r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
print(f"GD: w={w.round(2)} b={b:.2f} MSE={mse:.3f} R²={r2:.3f}")
```

## Gradiens-módszer: batch, SGD, mini-batch, momentum
<!-- q: Mi a különbség a batch, a sztochasztikus és a mini-batch gradiens-módszer között, és mit csinál a momentum? -->
<!-- tags: gradient descent, sgd, mini batch, momentum, learning rate, learning rate schedule, optimization -->

A gradiens-módszer a veszteség gradiensével ellentétes irányba lép, a lépésköz a *tanulási ráta*. A batch GD minden lépésben a teljes adaton számol (pontos, de drága), az SGD egyetlen mintán (olcsó, de zajos), a *mini-batch* (32–512 minta) a kettő közti kompromisszum, és jól kihasználja a vektorizált hardvert (GPU). A *momentum* az előző lépések „lendületét” is felhasználja, így kisimítja a zajos irányokat és gyorsít a hosszú völgyekben; az Adam/AdamW ezt adaptív, paraméterenkénti lépésközzel egészíti ki. Túl nagy tanulási ráta divergál, túl kicsi nagyon lassú — ezért kell ütemezés (warmup, decay) és minden epochban újrakeverés.

```python
import numpy as np

rng = np.random.default_rng(0)
X = rng.normal(size=(5000, 3))
y = X @ np.array([2.0, -1.0, 0.5]) + 0.3 + rng.normal(0, 0.1, 5000)
Xb = np.c_[X, np.ones(len(X))]                       # bias az utolsó oszlopban

def mse_grad(w, Xbatch, ybatch):
    return 2 * Xbatch.T @ (Xbatch @ w - ybatch) / len(ybatch)

def train(batch_size, lr=0.05, momentum=0.0, epochs=10, decay=0.0):
    w, velocity, history = np.zeros(Xb.shape[1]), np.zeros(Xb.shape[1]), []
    for epoch in range(epochs):
        idx = rng.permutation(len(Xb))               # minden epochban újrakeverés
        step_lr = lr / (1 + decay * epoch)           # egyszerű tanulásiráta-ütemezés
        for start in range(0, len(Xb), batch_size):
            batch = idx[start:start + batch_size]
            g = mse_grad(w, Xb[batch], y[batch])
            velocity = momentum * velocity - step_lr * g   # lendület: a korábbi irányok összegzése
            w = w + velocity
        history.append(float(np.mean((Xb @ w - y) ** 2)))
    return w, history

configs = {
    "batch GD (teljes adat)": dict(batch_size=len(Xb), epochs=200),
    "SGD (1 minta)": dict(batch_size=1, lr=0.005, epochs=2),
    "mini-batch 64": dict(batch_size=64),
    "mini-batch 64 + momentum": dict(batch_size=64, lr=0.01, momentum=0.9),
}
for name, kwargs in configs.items():
    w, hist = train(**kwargs)
    print(f"{name:26} veszteség: {hist[0]:.4f} -> {hist[-1]:.4f}  w={w.round(2)}")

_, hist = train(batch_size=64, lr=1.5, epochs=3)     # túl nagy tanulási ráta: divergál
print("lr=1.5 veszteség:", hist)
```

## Logisztikus regresszió nulláról
<!-- q: Hogyan működik a logisztikus regresszió és hogyan implementáljam nulláról? -->
<!-- tags: logistic regression, sigmoid, cross entropy, log loss, binary classification, odds ratio, numpy -->

A logisztikus regresszió bináris osztályozó: a lineáris kombinációt a szigmoid függvény (0, 1) közötti valószínűséggé alakítja, és a *log-loss*-t (bináris keresztentrópia) minimalizálja, aminek gradiense meglepően egyszerű: `Xᵀ(p − y)/n`. A kimenet kalibrált valószínűség, így a döntési küszöb (alapból 0,5) az üzleti költségek szerint állítható. A súlyok értelmezhetők: `exp(w_j)` az esélyhányados szorzója a j. feature egységnyi növelésére. Numerikusan figyelni kell a `exp` túlcsordulására és a `log(0)`-ra (vágás, `clip`); lineárisan nem szeparálható adatnál feature-transzformáció vagy nemlineáris modell kell.

```python
import numpy as np

def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))    # vágás: nincs overflow

def log_loss(y, p, eps=1e-12):
    p = np.clip(p, eps, 1 - eps)                             # log(0) elkerülése
    return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))

class LogisticRegression:
    def __init__(self, lr=0.1, epochs=1000, l2=0.0):
        self.lr, self.epochs, self.l2 = lr, epochs, l2

    def fit(self, X, y):
        n, d = X.shape
        self.w, self.b = np.zeros(d), 0.0
        for _ in range(self.epochs):
            p = sigmoid(X @ self.w + self.b)                 # P(y=1 | x)
            self.w -= self.lr * (X.T @ (p - y) / n + self.l2 * self.w)   # log-loss gradiense + L2
            self.b -= self.lr * np.mean(p - y)
        return self

    def predict_proba(self, X):
        return sigmoid(X @ self.w + self.b)

    def predict(self, X, threshold=0.5):
        return (self.predict_proba(X) >= threshold).astype(int)

rng = np.random.default_rng(1)
n = 400
X = np.vstack([rng.normal([-1, -1], 1.0, (n // 2, 2)), rng.normal([1.5, 1.0], 1.0, (n // 2, 2))])
y = np.r_[np.zeros(n // 2), np.ones(n // 2)]

model = LogisticRegression(lr=0.5, epochs=500).fit(X, y)
p = model.predict_proba(X)
print("w:", model.w.round(2), "b:", round(model.b, 2))
print(f"log-loss: {log_loss(y, p):.3f}  pontosság: {(model.predict(X) == y).mean():.3f}")
print("esélyhányados-szorzók:", np.exp(model.w).round(2))
```

## Túltanulás és regularizáció
<!-- q: Mi a túltanulás (overfitting) és hogyan védekezzek ellene regularizációval? -->
<!-- tags: overfitting, underfitting, regularization, ridge, lasso, l1, l2, bias variance tradeoff -->

Túltanulás (overfitting) esetén a modell a tanító adat zaját is megtanulja: a tanító hiba kicsi, a validációs nagy; alultanulásnál (underfitting) mindkettő nagy, mert a modell túl egyszerű. Ez a bias–variancia kompromisszum: a bonyolultabb modell kisebb torzítású, de nagyobb varianciájú. A *regularizáció* bünteti a nagy súlyokat: az L2 (Ridge) simább modellt ad, az L1 (Lasso) sok súlyt pontosan nullára állít (feature-szelekció); neurális hálóknál a weight decay, a dropout, az early stopping és az adatbővítés (augmentation) a megfelelője. A regularizáció erősségét (alpha, C) mindig validációs adaton válaszd meg, és a feature-ök legyenek standardizáltak, mert a büntetés skálafüggő.

```python
import numpy as np

rng = np.random.default_rng(3)

def make_data(n):
    x = rng.uniform(-1, 1, n)
    return x, np.sin(3 * x) + rng.normal(0, 0.2, n)

x_train, y_train = make_data(20)                     # kevés adat -> könnyű túltanulni
x_val, y_val = make_data(200)

def poly_features(x, degree):
    return np.vander(x, degree + 1, increasing=True)  # [1, x, x², ..., x^d]

def fit_ridge(X, y, alpha):
    # Ridge (L2): w = (XᵀX + αI)⁻¹ Xᵀy; a bias-t nem büntetjük
    penalty = alpha * np.eye(X.shape[1])
    penalty[0, 0] = 0.0
    return np.linalg.solve(X.T @ X + penalty, X.T @ y)

def mse(X, y, w):
    return float(np.mean((X @ w - y) ** 2))

print(f"{'fok':>4} {'alpha':>7} {'train MSE':>10} {'val MSE':>12}")
for degree in (1, 3, 15):
    for alpha in (0.0, 1e-3, 1e-1):
        Xtr, Xva = poly_features(x_train, degree), poly_features(x_val, degree)
        w = fit_ridge(Xtr, y_train, alpha)
        print(f"{degree:>4} {alpha:>7} {mse(Xtr, y_train, w):>10.4f} {mse(Xva, y_val, w):>12.4f}")
# Tipikus kép: fok=1 -> alultanul (mindkét hiba nagy);
# fok=15, alpha=0 -> túltanul (train ~0, val nagyon nagy);
# fok=15 + regularizáció -> a validációs hiba újra alacsony.
```

## Train/validáció/teszt felosztás és keresztvalidáció
<!-- q: Hogyan osszam fel az adatot train, validációs és teszt halmazra, és hogyan használjam a keresztvalidációt? -->
<!-- tags: train test split, cross validation, stratified kfold, data leakage, pipeline, grid search, hyperparameter tuning -->

A teszthalmazt legelőször kell félretenni, és csak a legvégén, egyszer szabad használni — ha a döntéseidet (modell, hiperparaméter) a teszt alapján hozod, az eredmény optimistán torzított lesz. A modellválasztást validációs adaton vagy *k-szoros keresztvalidációval* végezd, ami kis adatnál stabilabb becslést ad (átlag ± szórás); osztályozásnál rétegzett (stratified) felosztás kell, idősornál `TimeSeriesSplit` (sosem tanulhatsz a jövőből). A leggyakoribb hiba az *adatszivárgás* (leakage): a skálázót, imputálót vagy feature-szelekciót a teljes adaton illesztik a felosztás előtt. Ezt a scikit-learn `Pipeline` megelőzi, mert minden lépést csak a tanító foldon illeszt.

```python
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

X, y = make_classification(n_samples=2000, n_features=20, n_informative=6,
                           weights=[0.8, 0.2], random_state=0)

# 1) A teszthalmaz LEGELŐSZÖR leválasztva, rétegzetten (az osztályarány megmarad)
X_dev, X_test, y_dev, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=0)

# 2) Pipeline: a skálázó minden foldban CSAK a tanító részen illesztődik -> nincs leakage
pipe = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
scores = cross_val_score(pipe, X_dev, y_dev, cv=cv, scoring="roc_auc")
print(f"CV ROC-AUC: {scores.mean():.3f} ± {scores.std():.3f}")

# 3) Hiperparaméter-keresés is keresztvalidációval
grid = GridSearchCV(pipe, {"logisticregression__C": [0.01, 0.1, 1, 10]}, cv=cv, scoring="roc_auc")
grid.fit(X_dev, y_dev)
print("legjobb C:", grid.best_params_, f"CV AUC: {grid.best_score_:.3f}")

# 4) Egyetlen, végső mérés a félretett teszthalmazon
print(f"teszt ROC-AUC: {grid.score(X_test, y_test):.3f}")

# HIBÁS (leakage): skálázás a felosztás ELŐTT, a teljes adaton
#   X_scaled = StandardScaler().fit_transform(X)   # a teszt statisztikája "átszivárog"
```

## Döntési fák
<!-- q: Hogyan épül fel egy döntési fa és hogyan választja a vágásokat? -->
<!-- tags: decision tree, gini impurity, entropy, information gain, split, overfitting, scikit-learn -->

A döntési fa a feature-teret tengelyekkel párhuzamos vágásokkal osztja fel: minden csomópontban azt a (feature, küszöb) párt választja, amely a legjobban csökkenti a szennyezettséget (Gini vagy entrópia), a levelek pedig a többségi osztályt (vagy regressziónál az átlagot) adják. Előnye az értelmezhetőség, hogy nem kell skálázni, és kezeli a nemlinearitást; hátránya, hogy egyetlen mély fa erősen túltanul és instabil (kis adatváltozás más fát ad). Ezért korlátozni kell (`max_depth`, `min_samples_leaf`), vagy sok fát kell együttesbe (ensemble) szervezni — erre épül a random forest és a gradient boosting.

```python
import numpy as np
from sklearn.datasets import load_iris
from sklearn.tree import DecisionTreeClassifier, export_text

def gini(y):
    _, counts = np.unique(y, return_counts=True)       # 1 - Σ p_k²  (0 = tiszta csomópont)
    p = counts / counts.sum()
    return 1.0 - np.sum(p ** 2)

def best_split(X, y):
    best, parent = (None, None, 0.0), gini(y)          # (feature, küszöb, nyereség)
    for j in range(X.shape[1]):
        values = np.unique(X[:, j])
        for t in (values[:-1] + values[1:]) / 2:       # szomszédos értékek felezőpontjai
            left = X[:, j] <= t
            child = (left.sum() * gini(y[left]) + (~left).sum() * gini(y[~left])) / len(y)
            if parent - child > best[2]:
                best = (j, t, parent - child)
    return best

def build(X, y, depth=0, max_depth=3, min_samples=5):
    j, t, _ = best_split(X, y) if depth < max_depth and len(y) >= min_samples else (None, None, 0)
    if j is None:
        return {"leaf": int(np.bincount(y).argmax())}  # levél: többségi osztály
    mask = X[:, j] <= t
    return {"feature": j, "threshold": float(t),
            "left": build(X[mask], y[mask], depth + 1, max_depth, min_samples),
            "right": build(X[~mask], y[~mask], depth + 1, max_depth, min_samples)}

def predict_one(node, x):
    while "leaf" not in node:
        node = node["left"] if x[node["feature"]] <= node["threshold"] else node["right"]
    return node["leaf"]

X, y = load_iris(return_X_y=True)                     # a scikit-learn-nel együtt települ
tree = build(X, y)
print("saját fa pontossága:", np.mean([predict_one(tree, x) == t for x, t in zip(X, y)]).round(3))

clf = DecisionTreeClassifier(max_depth=3, min_samples_leaf=5, random_state=0).fit(X, y)
print(export_text(clf, feature_names=["sepal_len", "sepal_wid", "petal_len", "petal_wid"]))
```

## Random forest és gradient boosting
<!-- q: Mi a különbség a random forest és a gradient boosting között, és mikor melyiket használjam? -->
<!-- tags: random forest, gradient boosting, bagging, boosting, ensemble, xgboost, lightgbm, feature importance -->

A *random forest* sok mély fát tanít bootstrap-mintákon, csomópontonként véletlen feature-részhalmazzal, majd átlagol (bagging): a fák hibái függetlenebbek, így az együttes varianciája kicsi; kevés hangolást igényel, és az out-of-bag (OOB) becslés ingyen validációt ad. A *gradient boosting* sekély fákat tanít egymás után, mindegyik az eddigi együttes hibáját (a veszteség gradiensét) javítja kis lépéssel (learning rate) — táblázatos adaton általában ez a legpontosabb (XGBoost, LightGBM, CatBoost, sklearn `HistGradientBoosting`), de érzékenyebb a hangolásra és early stopping kell neki. A beépített impurity-alapú feature-fontosság torzít a sok értékű feature-ök felé; a permutációs fontosság megbízhatóbb.

```python
from sklearn.datasets import make_classification
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

X, y = make_classification(n_samples=5000, n_features=25, n_informative=8, random_state=0)
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, stratify=y, random_state=0)

# RANDOM FOREST: párhuzamos, független mély fák átlaga (bagging)
rf = RandomForestClassifier(n_estimators=300, max_features="sqrt", min_samples_leaf=2,
                            oob_score=True, n_jobs=-1, random_state=0)
rf.fit(X_tr, y_tr)
rf_auc = roc_auc_score(y_te, rf.predict_proba(X_te)[:, 1])
print(f"RF  OOB pontosság: {rf.oob_score_:.3f}  teszt AUC: {rf_auc:.3f}")

# GRADIENT BOOSTING: egymásra épülő sekély fák, early stoppinggal
gb = HistGradientBoostingClassifier(learning_rate=0.05, max_iter=1000, max_leaf_nodes=31,
                                    early_stopping=True, validation_fraction=0.1,
                                    n_iter_no_change=30, random_state=0)
gb.fit(X_tr, y_tr)
gb_auc = roc_auc_score(y_te, gb.predict_proba(X_te)[:, 1])
print(f"GB  iterációk: {gb.n_iter_}  teszt AUC: {gb_auc:.3f}")

# Permutációs fontosság: mennyit romlik a modell, ha egy feature értékeit összekeverjük
imp = permutation_importance(gb, X_te, y_te, n_repeats=5, scoring="roc_auc", random_state=0)
top = imp.importances_mean.argsort()[::-1][:5]
print("top feature-ök:", [(int(i), round(float(imp.importances_mean[i]), 4)) for i in top])
```

## k-means klaszterezés
<!-- q: Hogyan működik a k-means klaszterezés és hogyan válasszam meg a k értékét? -->
<!-- tags: k-means, clustering, unsupervised learning, kmeans++, elbow method, inertia, numpy -->

A k-means k középpontot keres úgy, hogy a pontok a legközelebbi középponthoz tartozzanak, és a klasztereken belüli négyzetes távolságösszeg (inertia) minimális legyen: felváltva hozzárendel (legközelebbi középpont) és frissít (a klaszter átlaga), amíg a középpontok nem mozdulnak. Az eredmény függ a kezdőpontoktól, ezért k-means++ inicializálás és több újraindítás kell; a k értékét a „könyök-módszer” (inertia k függvényében) vagy a silhouette-pontszám segít eldönteni. Gömbszerű, hasonló méretű klasztereket feltételez, és a skálára érzékeny (standardizálj!); tetszőleges alakú klaszterekhez a DBSCAN/HDBSCAN jobb.

```python
import numpy as np

def kmeans_pp_init(X, k, rng):
    # k-means++: az új középpont esélye ∝ a legközelebbi meglévőtől vett távolság négyzete
    centers = [X[rng.integers(len(X))]]
    for _ in range(k - 1):
        d2 = np.min(((X[:, None, :] - np.array(centers)[None]) ** 2).sum(-1), axis=1)
        centers.append(X[rng.choice(len(X), p=d2 / d2.sum())])
    return np.array(centers)

def kmeans(X, k, iters=100, tol=1e-6, seed=0):
    rng = np.random.default_rng(seed)
    C = kmeans_pp_init(X, k, rng)
    for _ in range(iters):
        labels = ((X[:, None, :] - C[None]) ** 2).sum(-1).argmin(1)   # 1) hozzárendelés
        new_C = np.array([X[labels == j].mean(0) if np.any(labels == j) else C[j]
                          for j in range(k)])                          # 2) frissítés (üres: marad)
        if np.linalg.norm(new_C - C) < tol:
            break
        C = new_C
    labels = ((X[:, None, :] - C[None]) ** 2).sum(-1).argmin(1)
    inertia = float(((X - C[labels]) ** 2).sum())                       # klaszteren belüli négyzetösszeg
    return C, labels, inertia

rng = np.random.default_rng(7)
X = np.vstack([rng.normal(c, 0.5, size=(100, 2)) for c in ([0, 0], [4, 4], [0, 5])])

for k in range(1, 7):                                  # könyök-módszer: hol törik meg a csökkenés?
    print(k, round(kmeans(X, k)[2], 1))
centers, labels, _ = kmeans(X, 3)
print("középpontok:\n", centers.round(2))
```

## Főkomponens-analízis (PCA)
<!-- q: Hogyan működik a PCA dimenziócsökkentés és hogyan implementáljam? -->
<!-- tags: pca, principal component analysis, dimensionality reduction, svd, explained variance, compression -->

A PCA az adatot olyan új, egymásra merőleges tengelyekre (főkomponensekre) vetíti, amelyek mentén a variancia a legnagyobb; az első néhány komponens gyakran az információ nagy részét megőrzi, így csökkenthető a dimenzió (vizualizáció, zajszűrés, gyorsabb tanítás). Számítása az adat centrálása után szingulárisérték-felbontással (SVD) történik: `Vᵀ` sorai a komponensirányok, a szinguláris értékek négyzete arányos a magyarázott varianciával. Eltérő skálájú feature-öknél előbb standardizálni kell, különben a nagy skálájú feature dominál. A PCA lineáris; nemlineáris szerkezet vizualizálására a t-SNE vagy az UMAP alkalmasabb.

```python
import numpy as np
from sklearn.datasets import load_digits

def pca(X, n_components):
    mean = X.mean(axis=0)
    Xc = X - mean                                       # centrálás kötelező
    _, S, Vt = np.linalg.svd(Xc, full_matrices=False)   # Xc = U·S·Vᵀ
    components = Vt[:n_components]                      # főkomponens-irányok
    explained = S ** 2 / (S ** 2).sum()                 # magyarázott variancia-arány
    return Xc @ components.T, components, mean, explained

X, y = load_digits(return_X_y=True)                     # 8x8 képek -> 64 dimenzió (beépített adat)
Z, comps, mean, ratio = pca(X, 2)
cum = np.cumsum(ratio)
print("2 komponens magyarázott varianciája:", cum[1].round(3))
print("95%-hoz szükséges komponensek:", int(np.searchsorted(cum, 0.95) + 1))

# Rekonstrukció k komponensből: tömörítés / zajszűrés
k = 20
Zk, comps_k, mean_k, _ = pca(X, k)
X_rec = Zk @ comps_k + mean_k
print(f"rekonstrukciós MSE (k={k}): {np.mean((X - X_rec) ** 2):.3f}")
print("2D beágyazás alakja:", Z.shape)                  # (1797, 2) -> szórásdiagramon ábrázolható
```

## Neurális háló nulláról
<!-- q: Hogyan írjak egy egyszerű neurális hálót (MLP) nulláról NumPy-ban? -->
<!-- tags: neural network, mlp, relu, softmax, cross entropy, he initialization, numpy, deep learning -->

A többrétegű perceptron (MLP) lineáris rétegek és nemlineáris aktivációk (ReLU) váltakozása; nemlinearitás nélkül a sok réteg egyetlen lineáris függvénnyé esne össze, így nem tudna például körkörös döntési határt tanulni. Az utolsó réteg logitokat ad, amiket a softmax valószínűségekké alakít, a veszteség pedig a keresztentrópia. A súlyok inicializálása fontos: ReLU-hoz a He-inicializálás (szórás √(2/bemenetek)) tartja stabilan a jelek nagyságát; a softmaxnál a maximum kivonása numerikus stabilitást ad. A tanítás a gradiensek visszaterjesztésével (backprop, következő szakasz) és gradiens-lépéssel történik.

```python
import numpy as np

rng = np.random.default_rng(0)
n = 600                                                # két koncentrikus kör: lineárisan nem szeparálható
r = np.r_[rng.uniform(0, 1, n // 2), rng.uniform(1.5, 2.5, n // 2)]
theta = rng.uniform(0, 2 * np.pi, n)
X = np.c_[r * np.cos(theta), r * np.sin(theta)]
y = np.r_[np.zeros(n // 2, dtype=int), np.ones(n // 2, dtype=int)]

def init(sizes):
    # He-inicializálás ReLU-hoz
    return [(rng.normal(0, np.sqrt(2 / a), (a, b)), np.zeros(b)) for a, b in zip(sizes, sizes[1:])]

def forward(params, X):
    acts = [X]
    for i, (W, b) in enumerate(params):
        z = acts[-1] @ W + b
        acts.append(np.maximum(z, 0) if i < len(params) - 1 else z)   # rejtett: ReLU, utolsó: logit
    return acts

def softmax(z):
    e = np.exp(z - z.max(1, keepdims=True))             # numerikus stabilitás
    return e / e.sum(1, keepdims=True)

params, lr = init([2, 16, 16, 2]), 0.1
for epoch in range(500):
    acts = forward(params, X)
    probs = softmax(acts[-1])
    loss = -np.log(probs[np.arange(n), y] + 1e-12).mean()              # keresztentrópia
    delta = probs.copy()
    delta[np.arange(n), y] -= 1                                         # dL/dlogit = softmax − onehot
    delta /= n
    for i in reversed(range(len(params))):                              # visszaterjesztés
        W, b = params[i]
        gW, gb = acts[i].T @ delta, delta.sum(0)
        if i > 0:
            delta = (delta @ W.T) * (acts[i] > 0)                       # ReLU deriváltja (a RÉGI W-vel)
        params[i] = (W - lr * gW, b - lr * gb)
    if epoch % 100 == 0:
        print(f"epoch {epoch:3}: loss={loss:.3f} pontosság={(probs.argmax(1) == y).mean():.3f}")
```

## Visszaterjesztés (backpropagation) érthetően
<!-- q: Hogyan működik a backpropagation, és hogyan ellenőrizzem, hogy helyes a gradiens? -->
<!-- tags: backpropagation, chain rule, gradient, gradient check, autograd, computational graph -->

A backpropagation a láncszabály hatékony alkalmazása a számítási gráfon: az előre lépés (forward) minden köztes értéket eltárol, a visszafelé lépés pedig a kimenettől a bemenet felé haladva minden réteg helyi deriváltjával szorozza a beérkező gradienst. Egy lineáris rétegnél `dL/dW = xᵀ · dL/dz` és `dL/dx = dL/dz · Wᵀ` (a hiba a súlyokon keresztül „visszafolyik”), az aktivációknál elemenként a derivált szorzódik (tanh' = 1 − tanh²). Így egyetlen visszafelé lépés költsége nagyjából egy előre lépésé — ezt automatizálja a PyTorch autograd. Saját implementációt mindig ellenőrizz numerikus gradienssel (középponti differencia): a relatív eltérés ~1e-7 alatt legyen.

```python
import numpy as np

rng = np.random.default_rng(1)
X, y = rng.normal(size=(8, 3)), rng.normal(size=(8, 1))
W1, b1 = rng.normal(size=(3, 4)) * 0.5, np.zeros(4)
W2, b2 = rng.normal(size=(4, 1)) * 0.5, np.zeros(1)

def loss_fn():
    h = np.tanh(X @ W1 + b1)
    return 0.5 * np.mean((h @ W2 + b2 - y) ** 2)

def backprop():
    # ELŐRE: a köztes értékeket eltároljuk, mert a visszafelé lépéshez kellenek
    h = np.tanh(X @ W1 + b1)
    out = h @ W2 + b2
    # VISSZA: láncszabály rétegenként, a kimenettől a bemenet felé
    d_out = (out - y) / len(X)            # dL/dout
    dW2, db2 = h.T @ d_out, d_out.sum(0)  # dL/dW2 = hᵀ · dL/dout
    d_h = d_out @ W2.T                    # a hiba visszafolyik a súlyokon át
    d_z1 = d_h * (1 - h ** 2)             # tanh'(z) = 1 − tanh²(z), elemenként
    dW1, db1 = X.T @ d_z1, d_z1.sum(0)
    return dW1, db1, dW2, db2

def numerical_grad(f, param, eps=1e-6):
    # Középponti differencia minden elemre: lassú, de megbízható ellenőrzés
    g = np.zeros_like(param)
    for idx in np.ndindex(param.shape):
        old = param[idx]
        param[idx] = old + eps; plus = f()
        param[idx] = old - eps; minus = f()
        param[idx] = old
        g[idx] = (plus - minus) / (2 * eps)
    return g

for name, p, g in zip(["W1", "b1", "W2", "b2"], [W1, b1, W2, b2], backprop()):
    num = numerical_grad(loss_fn, p)
    rel = np.linalg.norm(g - num) / (np.linalg.norm(g) + np.linalg.norm(num) + 1e-12)
    print(f"{name}: relatív eltérés {rel:.2e}")      # ~1e-9 körül: a gradiens helyes
```

## PyTorch tanítóciklus
<!-- q: Hogyan néz ki egy helyes PyTorch tanítóciklus validációval és early stoppinggal? -->
<!-- tags: pytorch, training loop, dataloader, optimizer, adamw, early stopping, model.eval, no_grad -->

A PyTorch tanítóciklus négy lépése batch-enként: gradiensek nullázása, előre lépés és veszteség, `loss.backward()` (autograd), `optimizer.step()`. Tipikus hibák: a `model.train()`/`model.eval()` váltás elmaradása (a dropout és a batchnorm másként viselkedik), a validáció `torch.no_grad()` nélkül (felesleges memória), softmax a `CrossEntropyLoss` előtt (az logitot vár), és a `.item()` hiánya a veszteség gyűjtésénél (a gráf életben marad). Az AdamW + tanulásiráta-ütemező jó alapértelmezés, a gradiens-vágás véd a robbanó gradiens ellen, az early stopping pedig a validációs veszteség alapján menti a legjobb modellt.

```python
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset, random_split

torch.manual_seed(0)
device = "cuda" if torch.cuda.is_available() else "cpu"

X = torch.randn(6000, 10)                                     # szintetikus adat, 3 osztály
y = (X[:, :3].sum(1) > 0).long() + (X[:, 3] > 1).long()
train_ds, val_ds = random_split(TensorDataset(X, y), [5000, 1000])
train_dl = DataLoader(train_ds, batch_size=128, shuffle=True)
val_dl = DataLoader(val_ds, batch_size=512)

model = nn.Sequential(nn.Linear(10, 64), nn.ReLU(), nn.Dropout(0.1), nn.Linear(64, 3)).to(device)
loss_fn = nn.CrossEntropyLoss()                               # logitot vár, NEM softmaxot
opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-2)
sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=20)

best_val, patience, bad_epochs = float("inf"), 3, 0
for epoch in range(20):
    model.train()                                             # dropout bekapcsolva
    for xb, yb in train_dl:
        xb, yb = xb.to(device), yb.to(device)
        opt.zero_grad(set_to_none=True)                       # 1) régi gradiensek törlése
        loss = loss_fn(model(xb), yb)                         # 2) előre + veszteség
        loss.backward()                                       # 3) visszaterjesztés
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)     # robbanó gradiens ellen
        opt.step()                                            # 4) súlyfrissítés
    sched.step()

    model.eval()                                              # kiértékelő mód: dropout ki
    total, correct, val_loss = 0, 0, 0.0
    with torch.no_grad():                                     # nincs gradiens-számítás
        for xb, yb in val_dl:
            xb, yb = xb.to(device), yb.to(device)
            logits = model(xb)
            val_loss += loss_fn(logits, yb).item() * len(yb)  # .item(): a gráf nem marad életben
            correct += (logits.argmax(1) == yb).sum().item()
            total += len(yb)
    val_loss /= total
    print(f"epoch {epoch:2}: val_loss={val_loss:.4f} acc={correct / total:.3f}")
    if val_loss < best_val:                                   # early stopping + legjobb modell mentése
        best_val, bad_epochs = val_loss, 0
        torch.save(model.state_dict(), "best.pt")
    else:
        bad_epochs += 1
        if bad_epochs >= patience:
            break
```

## Konvolúciós neurális háló (CNN)
<!-- q: Hogyan működik a konvolúciós neurális háló és hogyan építsek egyet PyTorch-ban? -->
<!-- tags: cnn, convolution, pooling, batchnorm, image classification, pytorch, transfer learning -->

A konvolúciós réteg egy kis szűrőt (kernelt) csúsztat végig a képen, és ugyanazokat a súlyokat használja minden pozícióban (súlymegosztás): így kevés paraméterrel ismer fel lokális mintákat (élek, textúrák), helytől függetlenül. Az egymásra rakott rétegek egyre összetettebb mintákat tanulnak (él → forma → objektum), a pooling csökkenti a felbontást és növeli a látómezőt, a batchnorm stabilizálja a tanítást. A gyakorlatban ritkán tanítunk nulláról: egy ImageNeten előtanított hálót (ResNet, EfficientNet, ConvNeXt) finomhangolunk *transfer learning*-gel, ami kevés adattal is jó eredményt ad. Mindig kövesd a tenzorméreteket rétegről rétegre — a legtöbb hiba itt keletkezik.

```python
import torch
from torch import nn
import torch.nn.functional as F

class SmallCNN(nn.Module):
    """28x28-as szürkeárnyalatos képekre; a méreteket kommentben követjük."""
    def __init__(self, n_classes=10):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)   # (B,1,28,28) -> (B,32,28,28)
        self.bn1 = nn.BatchNorm2d(32)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)  # (B,32,14,14) -> (B,64,14,14)
        self.bn2 = nn.BatchNorm2d(64)
        self.dropout = nn.Dropout(0.25)
        self.fc = nn.Linear(64 * 7 * 7, n_classes)

    def forward(self, x):
        x = F.max_pool2d(F.relu(self.bn1(self.conv1(x))), 2)     # -> (B,32,14,14)
        x = F.max_pool2d(F.relu(self.bn2(self.conv2(x))), 2)     # -> (B,64,7,7)
        x = self.dropout(torch.flatten(x, 1))                     # -> (B,3136)
        return self.fc(x)                                          # logitok

model = SmallCNN()
print(model(torch.randn(8, 1, 28, 28)).shape)                     # torch.Size([8, 10])
print("paraméterek száma:", sum(p.numel() for p in model.parameters()))

# Egy konvolúció közelről: Sobel-szűrő függőleges élre
sobel = torch.tensor([[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]]).view(1, 1, 3, 3)
img = torch.zeros(1, 1, 5, 5)
img[..., 2:] = 1.0                                                # függőleges él a kép közepén
print(F.conv2d(img, sobel, padding=1)[0, 0])                      # az él mentén nagy a válasz

# Transfer learning (a súlyok letöltése hálózatot igényel):
#   from torchvision.models import resnet18, ResNet18_Weights
#   net = resnet18(weights=ResNet18_Weights.DEFAULT)
#   for p in net.parameters(): p.requires_grad = False   # a törzs fagyasztva
#   net.fc = nn.Linear(net.fc.in_features, 5)            # csak az új fej tanul
```

## Rekurrens hálók: RNN és LSTM
<!-- q: Hogyan működik az RNN és az LSTM, és mikor használjam őket? -->
<!-- tags: rnn, lstm, gru, sequence modeling, embedding, packed sequence, vanishing gradient, pytorch -->

A rekurrens háló (RNN) a sorozatot elemenként dolgozza fel, és egy rejtett állapotot visz tovább, ugyanazokkal a súlyokkal minden lépésben: `h_t = tanh(W_x·x_t + W_h·h_{t−1} + b)`. Hosszú sorozatoknál a gradiens elhal vagy felrobban, ezért az LSTM és a GRU *kapukkal* (felejtő, bemeneti, kimeneti) szabályozza, mi maradjon meg az állapotban. Változó hosszúságú sorozatoknál paddinget és `pack_padded_sequence`-et használj, hogy a kitöltő pozíciók ne torzítsanak. Szövegre ma a Transformer jobb (párhuzamosítható, hosszú kontextus), de idősorokra, beágyazott és streaming feladatokra az RNN/GRU kis mérete és lépésenkénti működése miatt még mindig hasznos.

```python
import torch
from torch import nn

class SeqClassifier(nn.Module):
    """Token-azonosítók -> embedding -> kétirányú LSTM -> osztály."""
    def __init__(self, vocab_size, emb_dim=64, hidden=128, n_classes=2, pad_idx=0):
        super().__init__()
        self.emb = nn.Embedding(vocab_size, emb_dim, padding_idx=pad_idx)
        self.lstm = nn.LSTM(emb_dim, hidden, batch_first=True, bidirectional=True)
        self.head = nn.Linear(2 * hidden, n_classes)

    def forward(self, tokens, lengths):
        x = self.emb(tokens)                                       # (B, T, E)
        packed = nn.utils.rnn.pack_padded_sequence(                # a padding kimarad
            x, lengths.cpu(), batch_first=True, enforce_sorted=False)
        _, (h_n, _) = self.lstm(packed)                            # h_n: (irányok, B, H)
        h = torch.cat([h_n[-2], h_n[-1]], dim=1)                   # előre + hátra utolsó állapota
        return self.head(h)

def rnn_step(x_t, h_prev, W_xh, W_hh, b):
    # Egyetlen RNN-lépés: az állapot hordozza a múltat, a súlyok minden lépésben ugyanazok
    return torch.tanh(x_t @ W_xh + h_prev @ W_hh + b)

B, T, vocab = 4, 12, 1000
tokens = torch.randint(1, vocab, (B, T))
lengths = torch.tensor([12, 9, 5, 3])
for i, L in enumerate(lengths.tolist()):
    tokens[i, L:] = 0                                              # padding a rövidebb sorozatokra
print(SeqClassifier(vocab)(tokens, lengths).shape)                 # torch.Size([4, 2])

W_xh, W_hh, b = torch.randn(8, 16) * 0.1, torch.randn(16, 16) * 0.1, torch.zeros(16)
h = torch.zeros(1, 16)
for t in range(5):
    h = rnn_step(torch.randn(1, 8), h, W_xh, W_hh, b)
print("rejtett állapot:", h.shape)
```

## Attention és a Transformer blokk
<!-- q: Hogyan működik az attention mechanizmus és a Transformer felépítése? -->
<!-- tags: attention, self attention, transformer, multi head attention, causal mask, layernorm, residual, pytorch -->

A self-attention minden tokenhez egy *query*, *key* és *value* vektort számol; a token a többi tokenre a `softmax(QKᵀ/√d)` súlyokkal figyel, és a value-k súlyozott átlagát kapja — így bármely két pozíció közvetlenül, egyetlen lépésben összeköthető. A `√d` skálázás megakadályozza a softmax telítődését, a *causal mask* a dekóderben (GPT-típusú modellek) elrejti a jövőbeli tokeneket. A multi-head attention több „szempont” szerint figyel párhuzamosan; a Transformer blokk attention + pozíciónkénti MLP, reziduális kapcsolatokkal és LayerNormmal, a sorrendet pozíció-kódolás (pl. RoPE) adja. A költség a sorozathosszal négyzetesen nő — ezért fontos a FlashAttention (`F.scaled_dot_product_attention`) és a KV-cache generáláskor.

```python
import math
import torch
from torch import nn
import torch.nn.functional as F

def attention(q, k, v, causal=False):
    # q, k, v: (B, fejek, T, d)
    scores = q @ k.transpose(-2, -1) / math.sqrt(q.size(-1))     # (B, h, T, T) hasonlóságok
    if causal:                                                    # a jövő tokenjei nem láthatók
        T = q.size(-2)
        mask = torch.triu(torch.ones(T, T, dtype=torch.bool), diagonal=1)
        scores = scores.masked_fill(mask, float("-inf"))
    weights = F.softmax(scores, dim=-1)                           # soronként 1-re összegződik
    return weights @ v, weights

class MultiHeadSelfAttention(nn.Module):
    def __init__(self, d_model=64, n_heads=4):
        super().__init__()
        assert d_model % n_heads == 0
        self.h, self.d = n_heads, d_model // n_heads
        self.qkv = nn.Linear(d_model, 3 * d_model)                # Q, K, V egyetlen vetítésben
        self.out = nn.Linear(d_model, d_model)

    def forward(self, x, causal=True):
        B, T, C = x.shape
        q, k, v = self.qkv(x).split(C, dim=-1)
        q, k, v = (t.view(B, T, self.h, self.d).transpose(1, 2) for t in (q, k, v))  # -> (B,h,T,d)
        y, _ = attention(q, k, v, causal)
        return self.out(y.transpose(1, 2).reshape(B, T, C))       # fejek összefűzése

class TransformerBlock(nn.Module):
    def __init__(self, d_model=64, n_heads=4):
        super().__init__()
        self.ln1, self.ln2 = nn.LayerNorm(d_model), nn.LayerNorm(d_model)
        self.attn = MultiHeadSelfAttention(d_model, n_heads)
        self.mlp = nn.Sequential(nn.Linear(d_model, 4 * d_model), nn.GELU(), nn.Linear(4 * d_model, d_model))

    def forward(self, x):
        x = x + self.attn(self.ln1(x))         # pre-LN + reziduális kapcsolat
        return x + self.mlp(self.ln2(x))       # pozíciónkénti MLP

x = torch.randn(2, 10, 64)                     # (batch, tokenek, d_model)
print(TransformerBlock()(x).shape)             # torch.Size([2, 10, 64])
_, w = attention(*(torch.randn(1, 1, 4, 8) for _ in range(3)), causal=True)
print(w[0, 0].round(decimals=2))               # alsó háromszög-mátrix: a jövő maszkolva
```

## Embeddingek és vektoros keresés
<!-- q: Mik az embeddingek és hogyan működik a vektoros (szemantikus) keresés? -->
<!-- tags: embeddings, vector search, cosine similarity, semantic search, ann, hnsw, pgvector, faiss -->

Az embedding egy objektum (szó, mondat, kép, termék) sűrű vektor-reprezentációja, amelyben a hasonló jelentésű elemek közel esnek egymáshoz; tanított modell (pl. sentence-transformers, embedding API) állítja elő. A szemantikus keresés a lekérdezés vektorához legközelebbi dokumentumvektorokat keresi koszinusz-hasonlósággal — normalizált vektoroknál ez egyszerű skalárszorzat. Kis adatnál (≤ ~100 ezer vektor) a brute-force mátrixszorzás gyors és pontos; nagyobbnál közelítő legközelebbi-szomszéd (ANN) index kell: HNSW, IVF (FAISS, pgvector, Qdrant, Milvus). Ugyanazzal a modellel kell beágyazni a lekérdezést és a dokumentumokat, és a modell cseréjekor mindent újra kell indexelni.

```python
import hashlib
import numpy as np

def normalize(v):
    return v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-12)

def toy_embed(text: str, dim: int = 256) -> np.ndarray:
    # Játék-embedding: karakter-trigramok hash-elve egy fix vektorba (csak a demóhoz!).
    # Élesben tanított modell adja a valódi szemantikus vektort.
    v = np.zeros(dim, dtype=np.float32)
    t = f"  {text.lower()}  "
    for i in range(len(t) - 2):
        h = int.from_bytes(hashlib.md5(t[i:i + 3].encode()).digest()[:4], "little")
        v[h % dim] += 1.0
    return v

class VectorIndex:
    """Brute-force koszinusz-keresés: normalizált vektoroknál skalárszorzat = koszinusz."""
    def __init__(self, dim: int):
        self.vecs = np.empty((0, dim), dtype=np.float32)
        self.ids: list[str] = []

    def add(self, ids, vecs):
        self.vecs = np.vstack([self.vecs, normalize(np.asarray(vecs, dtype=np.float32))])
        self.ids.extend(ids)

    def search(self, query, k=3):
        scores = self.vecs @ normalize(np.asarray(query, dtype=np.float32))
        k = min(k, len(scores))
        top = np.argpartition(-scores, k - 1)[:k]             # O(n) top-k teljes rendezés helyett
        top = top[np.argsort(-scores[top])]
        return [(self.ids[i], round(float(scores[i]), 3)) for i in top]

docs = {
    "d1": "A Postgres MVCC-vel kezeli a párhuzamos tranzakciókat",
    "d2": "A Kubernetes podokat ütemez a node-okra",
    "d3": "A B+fa index gyors tartomány-lekérdezést ad",
    "d4": "Docker image rétegei és a build cache",
}
index = VectorIndex(256)
index.add(list(docs), [toy_embed(t) for t in docs.values()])
print(index.search(toy_embed("postgres tranzakciók"), k=2))
```

## LLM alapok: tokenizálás (BPE)
<!-- q: Hogyan bontják tokenekre a szöveget a nagy nyelvi modellek (BPE)? -->
<!-- tags: tokenization, bpe, byte pair encoding, subword, llm, vocabulary, context window -->

Az LLM-ek nem karaktereket vagy szavakat, hanem *részszó-tokeneket* látnak: a BPE (byte pair encoding) a tanító korpuszon a leggyakoribb szomszédos szimbólumpárokat ismételten egyesíti, így a gyakori szavak egy tokenek, a ritkák ismert darabokból állnak össze — nincs „ismeretlen szó”. A modern modellek bájtszintű BPE-t használnak (bármely Unicode-szöveg kódolható). A tokenszám határozza meg a költséget és a kontextusablak kihasználását; az angolra optimalizált szótárral a magyar (ragozó nyelv, ékezetek) jellemzően több tokenre esik szét. A tokenizálás magyarázza az LLM-ek furcsaságait is (betűszámolás, számjegyek kezelése).

```python
from collections import Counter

def merge_pair(symbols, pair):
    out, i = [], 0
    while i < len(symbols):
        if i + 1 < len(symbols) and (symbols[i], symbols[i + 1]) == pair:
            out.append(symbols[i] + symbols[i + 1]); i += 2
        else:
            out.append(symbols[i]); i += 1
    return tuple(out)

def train_bpe(corpus: list[str], num_merges: int):
    # Kezdetben minden szó karakterek sorozata + szóvég-jel
    words = Counter(tuple(w) + ("</w>",) for line in corpus for w in line.lower().split())
    merges = []
    for _ in range(num_merges):
        pairs = Counter()
        for word, freq in words.items():
            for a, b in zip(word, word[1:]):
                pairs[(a, b)] += freq
        if not pairs:
            break
        best = max(pairs, key=pairs.get)                    # a leggyakoribb szomszédos pár
        merges.append(best)
        words = Counter({merge_pair(w, best): f for w, f in words.items()})
    return merges

def tokenize(word: str, merges):
    symbols = tuple(word.lower()) + ("</w>",)
    for pair in merges:                                     # a tanult sorrendben alkalmazva
        symbols = merge_pair(symbols, pair)
    return list(symbols)

corpus = ["a programozás programozó programok", "a program fut", "programozni jó", "programot írok"]
merges = train_bpe(corpus, 20)
print(merges[:6])
print(tokenize("programozás", merges))     # néhány hosszú, gyakori részszó
print(tokenize("programkód", merges))      # ismeretlen szó: ismert darabokból áll össze
```

## Szöveggenerálás: temperature, top-k, top-p
<!-- q: Hogyan választja ki az LLM a következő tokent, mit csinál a temperature, top-k és top-p? -->
<!-- tags: sampling, temperature, top-k, top-p, nucleus sampling, greedy decoding, llm generation -->

A nyelvi modell minden lépésben logitokat ad a teljes szótárra, amiből a softmax valószínűségi eloszlást csinál, és ebből választjuk a következő tokent. A *temperature* osztja a logitokat: T < 1 élesebb, determinisztikusabb, T > 1 laposabb, kreatívabb (és több hibát ejtő) eloszlást ad; T = 0 a greedy dekódolás. A *top-k* csak a k legvalószínűbb tokent tartja meg, a *top-p* (nucleus) a legkisebb olyan halmazt, amelynek össz-valószínűsége eléri p-t — ez alkalmazkodik az eloszlás alakjához. Kódgeneráláshoz és tényszerű válaszokhoz alacsony temperature, kreatív szöveghez magasabb ajánlott; a reprodukálhatósághoz rögzíts seedet.

```python
import numpy as np

rng = np.random.default_rng(0)
vocab = ["a", "macska", "kutya", "alszik", "fut", "repül", "<eos>"]
logits = np.array([2.0, 3.5, 3.2, 1.0, 0.8, -1.0, 0.5])

def softmax(z):
    e = np.exp(z - z.max())
    return e / e.sum()

def sample(logits, temperature=1.0, top_k=None, top_p=None):
    if temperature == 0:                                  # greedy
        return int(np.argmax(logits))
    z = logits / temperature                              # T<1 élesít, T>1 laposít
    if top_k is not None:                                 # csak a k legvalószínűbb marad
        kth = np.sort(z)[-top_k]
        z = np.where(z < kth, -np.inf, z)
    p = softmax(z)
    if top_p is not None:                                 # nucleus: kumulált valószínűség ≥ p
        order = np.argsort(-p)
        keep = order[: np.searchsorted(np.cumsum(p[order]), top_p) + 1]
        mask = np.zeros_like(p)
        mask[keep] = 1.0
        p = p * mask / (p * mask).sum()                   # újranormálás
    return int(rng.choice(len(p), p=p))

for T in (0.2, 1.0, 1.8):
    print(f"T={T}:", np.round(softmax(logits / T), 3))
for cfg in [dict(temperature=0), dict(temperature=0.7, top_k=3), dict(temperature=1.0, top_p=0.9)]:
    print(cfg, [vocab[sample(logits, **cfg)] for _ in range(8)])
```

## Finomhangolás vagy RAG?
<!-- q: Mikor finomhangoljak egy LLM-et, és mikor használjak RAG-ot (retrieval-augmented generation)? -->
<!-- tags: rag, retrieval augmented generation, fine-tuning, lora, peft, chunking, grounding, hallucination -->

A *RAG* a kérdéshez releváns dokumentumrészleteket keres (embedding + vektoros keresés), és a promptba illeszti őket forrásként: friss, gyakran változó vagy privát tudáshoz ez a jó választás, mert a tudás frissítése csak újraindexelés, a válasz hivatkozhat forrásra, és kevésbé hallucinál. A *finomhangolás* (fine-tuning, olcsón LoRA/QLoRA-val, ahol csak kis adapter-mátrixok tanulnak) a modell *viselkedését* változtatja: stílus, formátum, szaknyelv, egy szűk feladat megbízható végrehajtása — tényeket tanítani vele drága és nehezen frissíthető. Gyakran a kettő együtt a legjobb. A RAG minősége főleg a darabolásán (chunking, átfedés), a visszakeresésen és az értékelésen múlik, nem a modellen.

```python
import re
import numpy as np

def chunk(text: str, max_words=60, overlap=15):
    # Átfedő darabolás: a határon kettévágott gondolat se vesszen el
    words, step = text.split(), max_words - overlap
    return [" ".join(words[i:i + max_words]) for i in range(0, max(len(words) - overlap, 1), step)]

def embed(texts, dim=512):
    # Helyőrző bag-of-words hashing (egy processzen belül konzisztens); élesben embedding-modell kell
    out = np.zeros((len(texts), dim), dtype=np.float32)
    for row, t in enumerate(texts):
        for w in re.findall(r"\w+", t.lower()):
            out[row, hash(w) % dim] += 1.0
    return out / (np.linalg.norm(out, axis=1, keepdims=True) + 1e-9)

def build_prompt(question, hits):
    sources = "\n\n".join(f"[{i + 1}] ({src}) {txt}" for i, (src, txt, _) in enumerate(hits))
    return ("Válaszolj KIZÁRÓLAG az alábbi források alapján, [n] hivatkozással. "
            "Ha a források nem tartalmazzák a választ, mondd, hogy nem tudod.\n\n"
            f"Források:\n{sources}\n\nKérdés: {question}\nVálasz:")

class RAG:
    def __init__(self, documents: dict[str, str]):
        self.chunks = [(src, c) for src, text in documents.items() for c in chunk(text)]
        self.matrix = embed([c for _, c in self.chunks])

    def retrieve(self, question, k=3, min_score=0.1):
        scores = self.matrix @ embed([question])[0]
        best = np.argsort(-scores)[:k]
        return [(*self.chunks[i], float(scores[i])) for i in best if scores[i] >= min_score]

    def answer(self, question, llm):
        hits = self.retrieve(question)
        return llm(build_prompt(question, hits)) if hits else "Nem találtam releváns forrást."

docs = {
    "szabalyzat.md": "A szabadságkérelmet legalább öt munkanappal előre jelezni kell a vezetőnek.",
    "it.md": "A VPN-hez kétlépcsős azonosítás szükséges, a jelszót kilencven naponta cserélni kell.",
}
rag = RAG(docs)
print(rag.retrieve("Hány munkanappal előre kell jelezni a szabadságot?"))
print(rag.answer("Kell-e kétlépcsős azonosítás a VPN-hez?", llm=lambda prompt: prompt[:200]))  # helyőrző LLM
```

```python
# Finomhangolás LoRA-val (peft): az alapmodell fagyasztva, csak kis adapterek tanulnak
from peft import LoraConfig, get_peft_model

lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                  target_modules=["q_proj", "v_proj"], task_type="CAUSAL_LM")
# model = get_peft_model(base_model, lora)
# model.print_trainable_parameters()   # tipikusan a paraméterek 0,1–1%-a tanul
```

## Értékelési metrikák
<!-- q: Milyen metrikával értékeljem a modellemet: accuracy, precision, recall, F1, ROC-AUC? -->
<!-- tags: evaluation metrics, accuracy, precision, recall, f1, roc auc, pr auc, confusion matrix, threshold, rmse -->

Kiegyensúlyozatlan adatnál az accuracy félrevezető: 5% pozitív esetén a „mindig negatív” modell is 95%-os. A *precision* azt mutatja, a riasztásokból mennyi valódi, a *recall*, hogy a valódi pozitívokból mennyit találtunk meg, az F1 a kettő harmonikus átlaga; a ROC-AUC és a PR-AUC küszöbfüggetlen rangsor-minőséget mér, ritka pozitív osztálynál a PR-AUC informatívabb. A döntési küszöböt az üzleti költségek alapján válaszd (egy kihagyott csalás drágább lehet, mint egy téves riasztás), ne hagyd automatikusan 0,5-ön. Regressziónál a MAE robusztusabb a kiugró értékekre, az RMSE jobban bünteti a nagy hibákat; mindig hasonlítsd egy egyszerű alapmodellhez (baseline) is.

```python
import numpy as np
from sklearn.metrics import (accuracy_score, average_precision_score, classification_report,
                             confusion_matrix, f1_score, mean_absolute_error, mean_squared_error,
                             precision_score, r2_score, recall_score, roc_auc_score)

rng = np.random.default_rng(0)
y_true = (rng.random(2000) < 0.05).astype(int)                         # 5% pozitív (pl. csalás)
scores = np.clip(y_true * 0.35 + rng.normal(0.3, 0.15, 2000), 0, 1)   # modell-pontszámok
y_pred = (scores >= 0.5).astype(int)

print("accuracy :", round(accuracy_score(y_true, y_pred), 3))          # a "mindig 0" is ~0.95!
print("precision:", round(precision_score(y_true, y_pred, zero_division=0), 3))
print("recall   :", round(recall_score(y_true, y_pred), 3))
print("F1       :", round(f1_score(y_true, y_pred), 3))
print("ROC-AUC  :", round(roc_auc_score(y_true, scores), 3))           # küszöbfüggetlen
print("PR-AUC   :", round(average_precision_score(y_true, scores), 3)) # ritka pozitívnál informatívabb
tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
print(f"TP={tp} FP={fp} FN={fn} TN={tn}")

# Küszöb üzleti költség alapján: egy kihagyott pozitív 20x drágább egy téves riasztásnál
thresholds = np.linspace(0.05, 0.95, 91)
cost = [20 * ((scores < t) & (y_true == 1)).sum() + ((scores >= t) & (y_true == 0)).sum()
        for t in thresholds]
print("költség-optimális küszöb:", round(float(thresholds[int(np.argmin(cost))]), 2))
print(classification_report(y_true, y_pred, digits=3, zero_division=0))

# Regresszió: MAE (robusztus) és RMSE (a nagy hibákat bünteti), R²
y_r = rng.normal(100, 20, 500)
pred_r = y_r + rng.normal(0, 8, 500)
rmse = np.sqrt(mean_squared_error(y_r, pred_r))
print(f"MAE={mean_absolute_error(y_r, pred_r):.2f} RMSE={rmse:.2f} R²={r2_score(y_r, pred_r):.3f}")
```
