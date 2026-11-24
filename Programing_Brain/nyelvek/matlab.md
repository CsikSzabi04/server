# MATLAB
<!-- tech: matlab -->
<!-- aliases: octave -->

A MATLAB ("MATrix LABoratory") mérnöki és tudományos számításokra készült, dinamikusan típusos, interpretált (JIT-gyorsított) nyelv és környezet, amelyben minden érték mátrix, a műveletek pedig alapból lineáris algebrai értelműek. Erőssége a vektorizált numerika, a beépített vizualizáció, az ODE-megoldók és a szakterületi toolboxok (jelfeldolgozás, szabályozástechnika, optimalizálás, Simulink); a memóriát automatikusan kezeli, a változók copy-on-write szemantikával adódnak át. A GNU Octave nyílt forrású, nagyrészt szintaxis-kompatibilis alternatíva (a toolboxok egy része `pkg` csomagként érhető el). Kiváló prototípusokhoz, mérési adatok elemzéséhez és oktatáshoz; általános célú szoftverhez, webes backendhez és licencköltség-érzékeny környezetben kevésbé ideális.

## Mátrixok létrehozása, indexelése és műveletei
<!-- q: Hogyan hozzak létre és indexeljek mátrixokat MATLAB-ban, és mi a különbség a * és .* között? -->
<!-- tags: matrix, indexing, colon operator, elementwise, backslash, reshape -->

MATLAB-ban a skalár 1×1, a vektor 1×n vagy n×1 mátrix; a `[ ]` operátorban a vessző/szóköz oszlopot, a pontosvessző új sort kezd. Az indexelés 1-alapú, az `end` az utolsó elemet, a `:` a teljes dimenziót jelenti, a lineáris index pedig oszlopfolytonos sorrendben számol. A `*`, `/` és `^` mátrixműveletek, az elemenkénti változatuk ponttal kezdődik (`.*`, `./`, `.^`) – ez a leggyakoribb hibaforrás. Lineáris egyenletrendszert mindig a `\` operátorral oldj meg, ne `inv(A)*b`-vel, mert az lassabb és pontatlanabb.

```matlab
A = [4 -2 1; 3 6 -4; 2 1 8];     % ; új sort kezd
v = (1:5)';                      % oszlopvektor (' = transzponálás)
Z = zeros(3); I = eye(3); R = rand(3, 4);

% Indexelés: 1-től, end = utolsó, : = teljes dimenzió
A(2, 3)                          % egy elem
A(:, 1)                          % első oszlop
A(end, :)                        % utolsó sor
A([1 3], [2 3])                  % részmátrix
A(5)                             % lineáris index (oszlopfolytonos) -> A(2,2) = 6

% Mátrix- vs elemenkénti műveletek
B = A * A;                       % mátrixszorzás
C = A .* A;                      % elemenkénti szorzás
D = A .^ 2;                      % elemenkénti hatvány (A^2 = A*A!)
E = A ./ 2;

% Egyenletrendszer: \ operátor (nem inv(A)*b)
b = [1; 2; 3];
x = A \ b;
residual = norm(A*x - b)         % ~1e-16

% Méret, átalakítás, összefűzés
[m, n] = size(R);
numel(R)
Rr  = reshape(R, 2, []);         % [] = automatikusan kiszámolt méret
Big = [A, b; zeros(1, 3), 1];    % blokkmátrix
T   = repmat([1 2], 2, 3);       % csempézés

% Összegző függvények dimenzió-paraméterrel
sum(A)                           % oszloponkénti összeg (sorvektor)
sum(A, 2)                        % soronkénti összeg
sum(A(:))                        % minden elem (A(:) oszlopvektorrá lapít; MATLAB-ban sum(A,'all') is)
max(A, [], 2)                    % soronkénti maximum
[sorted, idx] = sort(v, 'descend');
mean(A(:))
```

## Vektorizáció, előfoglalás és implicit expansion
<!-- q: Hogyan írjak gyors, vektorizált MATLAB kódot ciklusok helyett? -->
<!-- tags: vectorization, preallocation, implicit expansion, performance, tic toc, loops -->

A vektorizált kód egyetlen kifejezéssel dolgozza fel a teljes tömböt, a műveletek optimalizált, gyakran többszálú C/BLAS kódban futnak – ez tipikusan a leggyorsabb és legolvashatóbb megoldás. Ha ciklus kell, a kimeneti tömböt előre foglald le (`zeros`, `nan`, `cell`), mert a ciklusban növelt tömb minden lépésben újrafoglalódik. Az implicit expansion (R2016b+, Octave) automatikusan kiterjeszti a kompatibilis méreteket, így oszlop- és sorvektorból `repmat` nélkül lesz mátrix. Buktató: a modern JIT miatt az előfoglalt ciklus sokszor már elég gyors – a vektorizálás ne menjen az olvashatóság rovására, és mindig mérj (`tic/toc`, `timeit`).

```matlab
n = 1e6;
x = linspace(0, 2*pi, n);

% 1) Rossz: a tömb minden iterációban nő -> újrafoglalás
tic
y1 = [];
for k = 1:n
    y1(k) = sin(x(k)) * exp(-x(k)/5);
end
t_grow = toc;

% 2) Előfoglalás
tic
y2 = zeros(1, n);
for k = 1:n
    y2(k) = sin(x(k)) * exp(-x(k)/5);
end
t_prealloc = toc;

% 3) Vektorizált: egyetlen kifejezés
tic
y3 = sin(x) .* exp(-x/5);
t_vec = toc;
fprintf('növekvő: %.3f s | előfoglalt: %.3f s | vektorizált: %.3f s\n', t_grow, t_prealloc, t_vec);
assert(max(abs(y3 - y2)) < 1e-12)

% Implicit expansion: kompatibilis méretek automatikus kiterjesztése
X  = rand(1000, 5);
Xn = (X - mean(X)) ./ std(X);            % oszloponkénti standardizálás
pd = abs(x(1:5)' - x(1:5));              % 5×5 páronkénti távolság (oszlop - sor)

% Kumulatív és ablakos műveletek ciklus helyett
cs  = cumsum(y3);
mov = movmean(y3, 101);                  % mozgóátlag
d   = diff(y3);                          % szomszédos különbségek

% Feltételes számítás ciklus és if nélkül: logikai maszk szorzóként
penalty = (y3 < 0) .* abs(y3) * 10;      % csak a negatív elemekre büntetés
fprintf('Összes büntetés: %.2f\n', sum(penalty));
```

## Logikai indexelés
<!-- q: Hogyan szűrjek és módosítsak elemeket logikai indexeléssel MATLAB-ban? -->
<!-- tags: logical indexing, mask, find, any, all, ismember, nan -->

A logikai indexelés egy azonos méretű logikai (true/false) tömbbel választ ki elemeket – szűrésre, feltételes cserére és hiányzó értékek pótlására ez a legidiomatikusabb és leggyorsabb mód. Több feltétel elemenként `&` és `|` operátorral kombinálható (a `&&`/`||` csak skalárra, rövidzárral működik), a `find` csak akkor kell, ha tényleg az indexekre van szükség. Az `any`/`all` létezést és teljességet vizsgál, az `ismember` vektorizált halmaztagságot ad. Buktató: a `NaN` minden összehasonlításban hamis (`NaN == NaN` is), ezért hiányzó érték keresésére mindig `isnan` kell.

```matlab
temps = [12.5 NaN 18.2 25.1 -3.0 31.4 NaN 22.8];

valid = ~isnan(temps);                % logikai maszk
t = temps(valid);                     % csak az érvényes mérések
hot = temps > 25                      % NaN összehasonlítása mindig false
temps(isnan(temps)) = mean(t);        % hiányzók pótlása átlaggal

% Több feltétel: & és | elemenként
inRange = temps >= 0 & temps <= 25;
fprintf('%d mérés 0 és 25 fok között\n', nnz(inRange));

% find: ha tényleg indexek kellenek
firstHot = find(temps > 20, 1);              % első találat indexe
[r, c] = find(magic(4) > 12);                % sor- és oszlopindexek

% any / all: oszloponként vagy az egész tömbre
M = magic(5);
anyBig = any(M(:) > 24)
allPos = all(M(:) > 0)

% Feltételes csere ciklus nélkül
M(M > 20) = 20;                              % levágás (clip)
even = mod(M, 2) == 0;
M(even) = -M(even);                          % páros elemek negálása

% Adatmátrix sorainak szűrése: 1. oszlop == 2 és 3. oszlop > 0.5
data = [randi(3, 10, 1), rand(10, 2)];
rows = data(:, 1) == 2 & data(:, 3) > 0.5;
subset = data(rows, :);
fprintf('%d sor felel meg\n', size(subset, 1));

% ismember: vektorizált halmaztagság
codes = [101 205 330 101 999];
[isKnown, loc] = ismember(codes, [101 330]);
unknown = codes(~isKnown)                    % [205 999]
```

## Cell arrayek
<!-- q: Mire jók a cell arrayek MATLAB-ban és hogyan dolgozzak velük? -->
<!-- tags: cell array, cellfun, comma separated list, strings, regexp, heterogeneous data -->

A cell array heterogén elemek tárolója: minden cella tetszőleges típusú és méretű értéket tartalmazhat (különböző hosszú stringek, mátrixok, struktúrák, function handle-ök). A `()` cellát (al-cell arrayt) ad vissza, a `{}` a cella tartalmát; a `c{:}` vesszővel elválasztott listát ("comma-separated list") képez, amely függvényargumentumként vagy név–érték párként bontható ki. A `cellfun` minden cellára alkalmaz egy függvényt; nem skalár eredménynél `'UniformOutput', false` kell. Buktató: a `c(2) = []` törli a cellát, a `c{2} = []` viszont csak üres tartalmat tesz bele – a két jelölés könnyen összekeverhető.

```matlab
c = {42, 'szöveg', [1 2 3]; @sin, {true, 'beágyazott'}, magic(3)};
class(c(1, 2))        % 'cell' – () cellát ad vissza
class(c{1, 2})        % 'char' – {} a tartalmat

% Változó hosszú stringek listája
fruits = {'alma', 'körte', 'szilva', 'barack'};
lens   = cellfun(@numel, fruits);                               % skalár eredmény -> vektor
upperF = cellfun(@upper, fruits, 'UniformOutput', false);       % nem skalár -> cell
long   = fruits(lens > 4);                                      % logikai indexelés cellán

% Comma-separated list: c{:} kibontása argumentumokká
plotOpts = {'LineWidth', 2, 'Color', 'r'};
% plot(1:10, (1:10).^2, plotOpts{:});                          % név-érték párok átadása
fprintf('%s|', fruits{:}); fprintf('\n');
dateStr = strjoin({'2026', '11', '21'}, '-');

% Szövegfeldolgozás: sorok és mezők kinyerése regexp-pel
raw   = sprintf('id=1;name=alpha\nid=2;name=beta\nid=3;name=gamma');
lines = regexp(raw, '\n', 'split');
tok   = regexp(lines, 'id=(\d+);name=(\w+)', 'tokens', 'once');  % cell a cellában
ids   = cellfun(@(t) str2double(t{1}), tok);
names = cellfun(@(t) t{2}, tok, 'UniformOutput', false);

% Előfoglalás és dinamikus töltés különböző méretű elemekkel
results = cell(1, 3);
for k = 1:3
    results{k} = rand(k);
end
sizes = cellfun(@(m) size(m, 1), results)

% Törlés vs. kiürítés
tmp = fruits;
tmp(2) = [];          % a cella törlődik: 3 elem marad
tmp{1} = [];          % a cella megmarad, tartalma üres
numel(tmp)            % 3
```

## Struktúrák és struct arrayek
<!-- q: Hogyan használjak struct-ot és struct arrayt MATLAB-ban rekordok tárolására? -->
<!-- tags: struct, struct array, fieldnames, dynamic fields, arrayfun, records -->

A struct nevesített mezőkkel csoportosítja az összetartozó adatokat (konfiguráció, mérés metaadatai), a struct array pedig azonos mezőjű rekordok tömbje. A `[s.value]` egy mezőt numerikus vektorrá, a `{s.id}` cell arrayjé gyűjt minden elemből, így a rekordlistán is vektorizáltan szűrhetünk és rendezhetünk. A dinamikus mezőnév (`s.(name)`) futásidőben választott mezőt ér el, ami konfiguráció betöltésénél hasznos. Buktató: a `struct('f', {a, b})` cell argumentummal struct *arrayt* hoz létre – ha egyetlen struct mezőjébe akarsz cell arrayt tenni, dupla kapcsos zárójel kell: `struct('f', {{a, b}})`.

```matlab
sensor.id       = 'T-101';
sensor.location = struct('lat', 47.5, 'lon', 19.04);
sensor.readings = [21.3 21.8 22.4];

% Struct array cell argumentumokkal (3 elem)
s = struct('id',    {'T-101', 'T-102', 'H-201'}, ...
           'type',  {'temp', 'temp', 'humidity'}, ...
           'value', {21.3, 19.8, 55.0});
numel(s)                                   % 3

% Mezők összegyűjtése minden elemből
vals    = [s.value];                       % numerikus vektor
ids     = {s.id};                          % cell array
isTemp  = strcmp({s.type}, 'temp');
avgTemp = mean([s(isTemp).value]);

% Dinamikus mezőnevek: konfiguráció kulcs-érték listából
cfg = struct();
fieldList = {'host', 'port', 'timeout'};
defaults  = {'localhost', 5432, 30};
for k = 1:numel(fieldList)
    cfg.(fieldList{k}) = defaults{k};
end
if isfield(cfg, 'timeout') && cfg.timeout > 10
    fprintf('Hosszú timeout: %d s\n', cfg.timeout);
end
fn = fieldnames(cfg);                      % mezőnevek cellában

% arrayfun struct arrayen
labels = arrayfun(@(r) sprintf('%s=%.1f', r.id, r.value), s, 'UniformOutput', false);

% Rendezés mező szerint
[~, ord] = sort([s.value], 'descend');
s = s(ord);

% Konverziók, mező eltávolítása
c   = struct2cell(cfg);
cfg = rmfield(cfg, 'timeout');

% Egyetlen struct, cell array mezővel: dupla kapcsos zárójel!
one = struct('tags', {{'a', 'b'}});
size(one)                                  % 1×1
% MATLAB-ban táblázatos adatra a table típus kényelmesebb: T = struct2table(s)
```

## Függvények, argumentumkezelés és lokális függvények
<!-- q: Hogyan írjak függvényt több kimenettel és opcionális argumentumokkal MATLAB-ban? -->
<!-- tags: functions, nargin, nargout, varargin, inputparser, arguments block, local functions -->

Egy függvényfájl neve megegyezik a fő függvény nevével, utána lokális (csak a fájlból hívható) segédfüggvények következhetnek; a fejléc utáni komment a `help` kimenete. Több visszatérési értéket `[a, b] = f(...)` formában adunk, a `nargin`/`nargout` megmutatja, hány argumentumot adott át, illetve hány kimenetet kér a hívó – így a drága kimenet csak igény esetén számolódik. Opcionális név–érték párokhoz az `inputParser` (MATLAB és Octave), újabb MATLAB-ban az `arguments` blokk ad deklaratív validálást. Buktató: a MATLAB-ban nincs alapértelmezett paraméterérték-szintaxis a fejlécben, ezért a hiányzó argumentumokat `nargin`-nel vagy `arguments` blokkal kell kezelni.

```matlab
% fájl: movingStats.m – a fájlnév = a fő függvény neve
function [mu, sigma, info] = movingStats(x, window, varargin)
%MOVINGSTATS Mozgó átlag és szórás opcionális beállításokkal.
%   [mu, sigma] = movingStats(x, w)
%   [mu, sigma, info] = movingStats(x, w, 'Endpoints', 'discard')

    if nargin < 2 || isempty(window)
        window = 5;                               % alapértelmezett érték
    end
    validateattributes(x, {'numeric'}, {'vector', 'nonempty'});
    validateattributes(window, {'numeric'}, {'scalar', 'integer', 'positive'});

    % Név-érték párok feldolgozása
    p = inputParser;
    addParameter(p, 'Endpoints', 'shrink', @(s) any(strcmp(s, {'shrink', 'discard'})));
    parse(p, varargin{:});
    opts = p.Results;

    x = x(:);                                     % oszlopvektorrá alakítás
    n = numel(x);
    half = floor(window / 2);
    mu = nan(n, 1);
    sigma = nan(n, 1);
    for k = 1:n
        lo = max(1, k - half);
        hi = min(n, k + half);
        if strcmp(opts.Endpoints, 'discard') && (k - half < 1 || k + half > n)
            continue
        end
        [mu(k), sigma(k)] = localStats(x(lo:hi));
    end

    if nargout > 2                                % csak ha a hívó kéri
        info = struct('window', window, 'n', n, 'validCount', nnz(~isnan(mu)));
    end
end

function [m, s] = localStats(seg)
% Lokális függvény: csak ebből a fájlból hívható
    m = mean(seg);
    s = std(seg);
end
```

```matlab
% fájl: scaleSignal.m – deklaratív validálás arguments blokkal (MATLAB R2019b+)
function y = scaleSignal(x, opts)
    arguments
        x (:,1) double {mustBeFinite}
        opts.Gain (1,1) double {mustBePositive} = 1
        opts.Offset (1,1) double = 0
    end
    y = opts.Gain * x + opts.Offset;
end
% Hívás: y = scaleSignal(randn(100, 1), 'Gain', 2);   R2021a+: scaleSignal(x, Gain=2)
```

## Function handle-ök és anonim függvények
<!-- q: Hogyan használjak function handle-t és anonim függvényt MATLAB-ban? -->
<!-- tags: function handle, anonymous function, closures, fzero, integral, cellfun, higher-order -->

A function handle (`@sin`, `@(x) x.^2 - 3*x`) függvényre mutató érték, amely átadható, tárolható és később meghívható – a numerikus módszerek (`fzero`, `integral`, `fminsearch`, `ode45`) mind ilyet várnak. Az anonim függvény a *létrehozás pillanatában* lemásolja a felhasznált változók értékét, így a későbbi módosítás nem hat rá. Handle-ből handle-t visszaadó "gyárakkal" paraméterezett függvénycsaládok, cell arraybe tett handle-ökkel stratégia minta építhető. Buktató: az anonim függvény csak egyetlen kifejezés lehet – többsoros logikához írj rendes vagy lokális függvényt, és a vektoros inputhoz mindig elemenkénti operátorokat (`.^`, `.*`) használj.

```matlab
f = @sin;
g = @(x) x.^2 - 3*x + 2;              % anonim függvény, vektorizálva
h = @(x) f(g(x));                     % kompozíció

% Létrehozáskori értékmásolás
a = 2;
scale = @(x) a * x;
a = 10;
scale(3)                              % 6, nem 30

% Numerikus módszerek handle-t várnak
r1 = fzero(g, [0 1.5]);               % gyök a [0, 1.5] intervallumban -> 1
I  = integral(@(x) exp(-x.^2), -Inf, Inf);    % sqrt(pi)
rosen = @(p) (p(1) - 1)^2 + 100*(p(2) - p(1)^2)^2;
[pmin, fmin] = fminsearch(rosen, [-1 2]);      % minimum (1, 1)-nél
fprintf('gyök=%.4f, integrál=%.4f, min=(%.3f, %.3f)\n', r1, I, pmin);

% Handle-gyár: paraméterezett függvénycsalád
makeGauss = @(mu, s) @(x) exp(-(x - mu).^2 / (2*s^2)) / (s*sqrt(2*pi));
pdf1 = makeGauss(0, 1);
pdf2 = makeGauss(2, 0.5);
x = linspace(-3, 4, 200);
mix = 0.5*pdf1(x) + 0.5*pdf2(x);
fprintf('Keverék integrálja: %.4f\n', trapz(x, mix));

% Stratégia minta: handle-ök cell arrayben
ops   = {@mean, @median, @std, @(v) max(v) - min(v)};
names = {'átlag', 'medián', 'szórás', 'terjedelem'};
data  = randn(1, 1000);
for k = 1:numel(ops)
    fprintf('%-10s %8.4f\n', names{k}, ops{k}(data));
end

% Handle <-> string, arrayfun handle-lel
func2str(g)
cube = str2func('@(t) t.^3');
arrayfun(@(k) cube(k), 1:4)           % [1 8 27 64]
```

## Ábrázolás
<!-- q: Hogyan készítsek többpaneles, feliratozott ábrát MATLAB-ban és mentsem fájlba? -->
<!-- tags: plotting, plot, subplot, figure, contour, legend, print, visualization -->

A `figure` új ábraablakot, a `subplot` (vagy MATLAB-ban a modernebb `tiledlayout`/`nexttile`) paneleket hoz létre; a `hold on` mellett több görbe kerül ugyanarra a tengelyre. A feliratokat `xlabel`, `ylabel`, `title`, `legend` adja (TeX jelöléssel: `\theta`, `x^2`), a `meshgrid` + `contourf`/`surf` kétváltozós függvényeket ábrázol. Mentéshez a `print` (MATLAB és Octave), újabb MATLAB-ban az `exportgraphics` való; publikációhoz vektoros formátumot (PDF, SVG) válassz. Teljesítmény: animációnál ne rajzold újra az egész ábrát, csak a meglévő vonalobjektum `XData`/`YData` tulajdonságát frissítsd.

```matlab
t  = linspace(0, 10, 500);
y1 = exp(-0.3*t) .* sin(2*pi*0.8*t);
env = exp(-0.3*t);

fig = figure('Name', 'Csillapított rezgés', 'Position', [100 100 900 600]);

% Felső panel a teljes szélességben
subplot(2, 2, [1 2]);
plot(t, y1, 'b-', 'LineWidth', 1.5); hold on
plot(t, env, 'r--', t, -env, 'r--');        % burkoló két görbéje
hold off
grid on
xlabel('Idő [s]'); ylabel('Kitérés');
title('Csillapított rezgés és burkolója');
legend({'jel', 'burkoló'}, 'Location', 'northeast');

% Hisztogram vs. elméleti sűrűségfüggvény
subplot(2, 2, 3);
data = randn(1, 5000);
[counts, centers] = hist(data, 40);          % MATLAB-ban újabb: histogram()
binW = centers(2) - centers(1);
bar(centers, counts / (numel(data) * binW), 1);
hold on
xx = linspace(-4, 4, 200);
plot(xx, exp(-xx.^2/2) / sqrt(2*pi), 'r', 'LineWidth', 1.5);
hold off
title('Normális eloszlás');

% Kétváltozós függvény szintvonalakkal
subplot(2, 2, 4);
[X, Y] = meshgrid(linspace(-2, 2, 60));
Z = X .* exp(-X.^2 - Y.^2);
contourf(X, Y, Z, 20); colorbar
axis equal tight
title('z = x e^{-x^2-y^2}');                 % TeX jelölés a címben

% Mentés: raszteres képernyőre, vektoros publikációhoz
print(fig, 'rezges.png', '-dpng', '-r150');
% MATLAB R2020a+: exportgraphics(fig, 'rezges.pdf', 'ContentType', 'vector');

% Hatékony animáció: csak az adatot frissítjük
figure;
hLine = plot(NaN, NaN, 'b');
axis([0 10 -1 1]);
for k = 1:50
    set(hLine, 'XData', t(1:10*k), 'YData', y1(1:10*k));
    drawnow
end
```

## Differenciálegyenletek megoldása (ODE)
<!-- q: Hogyan oldjak meg differenciálegyenletet ode45-tel és merev rendszert ode15s-sel MATLAB-ban? -->
<!-- tags: ode45, ode15s, differential equations, stiff, events, odeset, simulation -->

Az ODE-megoldók elsőrendű rendszert várnak (`y' = f(t, y)`), ezért a magasabb rendű egyenletet állapotvektorra kell átírni (pl. inga: `y = [θ; θ']`). Az `ode45` adaptív lépésközű Runge–Kutta (4,5) módszer, a legtöbb nem merev feladatra ez az alapválasztás; merev (stiff) rendszerre – nagyon eltérő időskálák, pl. kémiai kinetika, Van der Pol nagy μ-vel – az implicit `ode15s` nagyságrendekkel gyorsabb. Az `odeset` a tűréseket és az eseményfüggvényt állítja (nulla-átmenet, ütközés, megállási feltétel). Buktató: az alapértelmezett tűrés (`RelTol = 1e-3`) hosszú szimulációban látható hibát halmozhat fel – energiamegmaradást vagy ismert megoldást ellenőrizve állítsd be.

```matlab
% Csillapított, gerjesztett inga: θ'' + c·θ' + (g/L)·sin θ = A·cos(ωt)
% Elsőrendű rendszerként: y = [θ; θ']
P = struct('c', 0.2, 'g', 9.81, 'L', 1.0, 'A', 0.5, 'w', 2.0);
rhs = @(t, y) [y(2);
               -P.c*y(2) - P.g/P.L*sin(y(1)) + P.A*cos(P.w*t)];

tspan = [0 30];
y0 = [pi/4; 0];                                  % kezdeti szög és szögsebesség

% Eseményfüggvény: θ felfelé haladó nulla-átmenete, nem állítja le a megoldást.
% A deal több kimenetet ad: [érték, isterminal, irány]
events = @(t, y) deal(y(1), 0, 1);
opts = odeset('RelTol', 1e-8, 'AbsTol', 1e-10, 'Events', events);
[t, Y, te, ye] = ode45(rhs, tspan, y0, opts);
fprintf('%d felfelé irányú nulla-átmenet, az első t = %.3f s-nál\n', numel(te), te(1));

% Merev rendszer: Van der Pol, mu = 1000 – ode45-tel nagyon lassú lenne
mu  = 1000;
vdp = @(t, y) [y(2); mu*(1 - y(1)^2)*y(2) - y(1)];
tic
[tv, Yv] = ode15s(vdp, [0 3000], [2; 0]);       % implicit, merev rendszerekre
fprintf('ode15s: %d lépés, %.2f s\n', numel(tv), toc);

% Megoldás tetszőleges időpontokban: interpoláció a kapott pontok között
% (MATLAB-ban: sol = ode45(...); yq = deval(sol, tq);)
tq = linspace(0, 30, 1000);
thetaQ = interp1(t, Y(:, 1), tq, 'pchip');

subplot(2, 1, 1);
plot(tq, thetaQ); ylabel('\theta [rad]'); title('Gerjesztett inga');
subplot(2, 1, 2);
plot(Y(:, 1), Y(:, 2)); xlabel('\theta'); ylabel('d\theta/dt'); title('Fázistér');
```

## Jelfeldolgozási alapok
<!-- q: Hogyan számoljak spektrumot FFT-vel és szűrjek jelet MATLAB-ban toolbox nélkül? -->
<!-- tags: signal processing, fft, spectrum, fir filter, windowing, filter, convolution -->

Az `fft` a diszkrét Fourier-transzformációt számolja; egyoldalas amplitúdóspektrumhoz a kimenet első felét vesszük, a nem-DC elemeket duplázzuk, a frekvenciatengely pedig `fs*(0:N/2)/N`. Ablakfüggvény (Hann, Hamming) csökkenti a spektrális szivárgást, a frekvenciafelbontás `fs/N`. FIR szűrő ablakos sinc módszerrel toolbox nélkül is tervezhető, a szűrést a `filter(b, a, x)` végzi (FIR-nél `a = 1`, IIR-nél rekurzív). Buktató: a `filter` kauzális, ezért fáziskésleltetést okoz (lineáris fázisú FIR-nél `(M-1)/2` minta) – offline feldolgozásnál ezt kompenzáld, vagy használj nulla fázisú `filtfilt`-et (Signal Processing Toolbox / Octave signal csomag).

```matlab
fs = 1000;                          % mintavételi frekvencia [Hz]
N  = 2048;
t  = (0:N-1) / fs;
x  = 0.7*sin(2*pi*50*t) + sin(2*pi*120*t) + 0.8*randn(size(t));

% Egyoldalas amplitúdóspektrum Hann-ablakkal (kézzel, toolbox nélkül)
w  = 0.5 - 0.5*cos(2*pi*(0:N-1)/(N-1));
X  = fft(x .* w);
P2 = abs(X) / sum(w);               % ablakerősítés korrekciója
P1 = P2(1:N/2+1);
P1(2:end-1) = 2*P1(2:end-1);        % negatív frekvenciák energiája a pozitív oldalra
f  = fs * (0:N/2) / N;

% Csúcsok: lokális maximumok közül a két legnagyobb
isPeak = [false, P1(2:end-1) > P1(1:end-2) & P1(2:end-1) > P1(3:end), false];
pk = find(isPeak);
[~, order2] = sort(P1(pk), 'descend');
fprintf('Domináns frekvenciák: %s Hz\n', mat2str(round(f(pk(order2(1:2))))));

% FIR aluláteresztő szűrő ablakos sinc módszerrel
fc = 80;  M = 101;                  % vágási frekvencia [Hz], páratlan hossz
n  = -(M-1)/2:(M-1)/2;
k  = 2*fc/fs * n;
h  = 2*fc/fs * ones(size(n));
nz = k ~= 0;
h(nz) = 2*fc/fs * sin(pi*k(nz)) ./ (pi*k(nz));     % ideális sinc impulzusválasz
h  = h .* (0.54 - 0.46*cos(2*pi*(0:M-1)/(M-1)));   % Hamming-ablak
h  = h / sum(h);                                   % egységnyi DC erősítés

y  = filter(h, 1, x);               % FIR szűrés
y  = y((M-1)/2+1:end);              % csoportkésleltetés kompenzálása

% IIR: elsőrendű exponenciális simítás, y(n) = a*x(n) + (1-a)*y(n-1)
alpha   = 0.1;
ySmooth = filter(alpha, [1, alpha - 1], x);

% Mozgóátlag konvolúcióval
ma = conv(x, ones(1, 25)/25, 'same');

% Toolboxszal: [b, a] = butter(4, fc/(fs/2)); yz = filtfilt(b, a, x); pwelch(x, [], [], [], fs)
```

## Lineáris algebra és legkisebb négyzetek
<!-- q: Hogyan illesszek polinomot, használjak mátrixfelbontásokat és ritka mátrixot MATLAB-ban? -->
<!-- tags: linear algebra, least squares, polyfit, condition number, cholesky, svd, sparse -->

Túlhatározott rendszerre (több egyenlet, mint ismeretlen) a `\` QR-alapú legkisebb négyzetes megoldást ad – ez a polinom- és regressziós illesztés alapja (a `polyfit` ugyanezt csomagolja). A kondíciószám (`cond`) megmutatja, mennyire érzékeny a megoldás az adat- és kerekítési hibákra; rosszul kondicionált mátrixnál (pl. Hilbert-mátrix) a numerikus eredmény megbízhatatlan. Ha ugyanarra a mátrixra több jobboldallal kell megoldani, faktorizálj egyszer (`chol`, `lu`), az SVD pedig alacsony rangú közelítést ad. Nagy, főleg nullás rendszerekhez (végeselem, gráfok) a `sparse` tárolás nagyságrendekkel kevesebb memóriát és időt igényel.

```matlab
% Polinom illesztése legkisebb négyzetekkel
x = linspace(0, 5, 50)';
y = 1.5 + 0.8*x - 0.12*x.^2 + 0.1*randn(size(x));
V = [ones(size(x)), x, x.^2];       % tervezőmátrix
coef = V \ y;                       % QR-alapú; NE (V'*V)\(V'*y) – rosszabb kondíció
p    = polyfit(x, y, 2);            % ugyanez beépítve (fordított együttható-sorrend)
yfit = polyval(p, x);
R2   = 1 - sum((y - yfit).^2) / sum((y - mean(y)).^2);
fprintf('együtthatók: %s, R^2 = %.4f\n', mat2str(coef', 3), R2);

% Kondíciószám: a hibák felnagyítódása
A = hilb(8);                        % hírhedten rosszul kondicionált
xtrue = ones(8, 1);
xs = A \ (A * xtrue);
fprintf('cond = %.2e, relatív hiba = %.2e\n', cond(A), norm(xs - xtrue) / norm(xtrue));

% Faktorizáció újrahasznosítása több jobboldalra
B = randn(200);
S = B' * B + 200*eye(200);          % szimmetrikus, pozitív definit
R = chol(S);                        % S = R' * R
rhs = randn(200, 5);
Xs = R \ (R' \ rhs);                % két háromszög-megoldás, olcsó
fprintf('maradék: %.2e\n', norm(S*Xs - rhs));

% SVD: legjobb rang-k közelítés
[U, Sg, W] = svd(randn(100, 40), 'econ');
k  = 5;
Ak = U(:, 1:k) * Sg(1:k, 1:k) * W(:, 1:k)';

% Ritka mátrix: 1D Poisson-egyenlet tridiagonális rendszere
n  = 1e5;
e  = ones(n, 1);
K  = spdiags([-e 2*e -e], -1:1, n, n);   % csak ~3n nemnulla elem tárolva
u  = K \ (ones(n, 1) / n^2);             % a \ felismeri a sávos szerkezetet
fprintf('nemnulla elemek: %d, max(u) = %.4f\n', nnz(K), max(u));
```

## Hibakezelés, takarítás és profilozás
<!-- q: Hogyan kezeljem a hibákat try/catch-csel és mérjem a teljesítményt MATLAB-ban? -->
<!-- tags: error handling, try catch, mexception, oncleanup, profiler, tic toc, assert -->

A hibát az `error('komponens:azonosito', 'üzenet %s', arg)` dobja; az azonosító alapján a hívó `try/catch` ágban típus szerint dönthet (`err.identifier`), az ismeretlen hibát pedig `MException` + `addCause` láncolással, az eredeti okot megőrizve dobhatja tovább. Az `onCleanup` objektum a hatókör végén – hiba esetén is – lefuttatja a takarítást (fájl bezárása, beállítás visszaállítása). Időméréshez `tic/toc`, pontosabban MATLAB-ban `timeit`, a szűk keresztmetszet megtalálásához a `profile` való; gyors önellenőrzéshez az `assert`. Buktató: a `catch` ágban ne nyeld el csendben a hibát – legalább naplózd, különben a hibás adatok észrevétlenül továbbterjednek.

```matlab
% fájl: loadMeasurements.m
function data = loadMeasurements(path)
    if ~exist(path, 'file')
        error('meas:notFound', 'A fájl nem található: %s', path);
    end
    raw = dlmread(path, ',', 1, 0);          % fejléc kihagyása (MATLAB-ban: readmatrix)
    if size(raw, 2) ~= 3
        error('meas:badFormat', 'Három oszlop kell, %d jött', size(raw, 2));
    end
    data = struct('t', raw(:, 1), 'temp', raw(:, 2), 'hum', raw(:, 3));
end
```

```matlab
% Hívó oldal: azonosító szerinti elágazás, láncolt továbbdobás
try
    d = loadMeasurements('meres.csv');
catch err
    switch err.identifier
        case 'meas:notFound'
            warning('meas:fallback', '%s – üres adatkészlettel folytatom', err.message);
            d = struct('t', [], 'temp', [], 'hum', []);
        otherwise
            wrapped = MException('app:loadFailed', 'A mérés betöltése sikertelen');
            wrapped = addCause(wrapped, err);   % az eredeti hiba megmarad
            throw(wrapped);
    end
end

% Garantált takarítás: onCleanup a hatókör végén (hibánál is) fut
fname = [tempname '.txt'];
fid = fopen(fname, 'w');
cleaner = onCleanup(@() fclose(fid));
fprintf(fid, '%f\n', rand(5, 1));
clear cleaner                                 % itt zárul a fájl

% Időmérés
A = rand(500);
tic
for k = 1:20
    B = A * A;
end
fprintf('átlagos szorzási idő: %.4f s\n', toc / 20);
% MATLAB: t = timeit(@() A * A);

% Profiler: soronkénti időeloszlás
profile on
s = 0;
for k = 1:1e5
    s = s + sqrt(k);
end
profile off
% MATLAB: profile viewer   |   Octave: profshow(profile('info'))

% Gyors önellenőrzés
assert(abs(sqrt(2)^2 - 2) < 1e-12, 'numerikus hiba túl nagy');
```
