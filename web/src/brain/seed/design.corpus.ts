// design.corpus.ts — longer EN/HU text about CSS and visual design (seed v18), fed to
// the learner as `seed:prog:<tech>` so the words become neurons in the Programming lobe
// and the concepts link up (flexbox ↔ justify-content ↔ gap, contrast ↔ wcag ↔ 4.5:1 …).
// Loaded with a DYNAMIC import (seedCorpus.seedIngestedCorpora) → not in the startup bundle.
//
// Provenance (rule SZ11): every chunk is ORIGINAL text written for Auri — `license:
// 'original'` — and `source` is the reference it is based on, not copied prose.
// Generic content only: no personal data, no real people's details.

export interface DesignChunk {
  tech: 'css' | 'design';
  text: string;
  source: string;
  license: 'original';
}

const c = (tech: DesignChunk['tech'], source: string, ...texts: string[]): DesignChunk[] =>
  texts.map((text) => ({ tech, text, source, license: 'original' }));

const MDN = 'https://developer.mozilla.org/en-US/docs/Web/CSS/';
const LEARN_CSS = 'https://web.dev/learn/css/';
const LEARN_DESIGN = 'https://web.dev/learn/design/';
const WCAG = 'https://www.w3.org/WAI/WCAG22/quickref/';

export const DESIGN_CHUNKS: DesignChunk[] = [
  // ── how CSS works ────────────────────────────────────────────────────────────
  ...c('css', `${LEARN_CSS}box-model`,
    'Every element in CSS is a rectangular box with four layers: the content, the padding around it, the border, and the margin outside. Vertical margins between blocks can collapse into one, while padding never collapses. Setting box-sizing to border-box makes width and height include the padding and the border.',
    'A CSS-ben minden elem egy téglalap alakú doboz négy réteggel: tartalom, körülötte padding, aztán border, kívül margin. A blokkok közötti függőleges margók összeolvadhatnak, a padding sosem. A box-sizing: border-box mellett a szélesség és a magasság a paddinget és a bordert is tartalmazza.',
  ),
  ...c('css', `${LEARN_CSS}the-cascade`,
    'The browser combines styles from many places — its own defaults, your stylesheets, inline styles — through the cascade. Origin and importance come first, then cascade layers, then specificity, and finally the order in the source. Inheritance passes text properties such as color, font and line-height from a parent to its children.',
    'A böngésző sok helyről származó stílust fésül össze — saját alapértékek, a stíluslapjaid, inline stílusok — a kaszkáddal. Először az eredet és a fontosság számít, aztán a cascade layerek, majd a specificitás, végül a forrásbeli sorrend. Az öröklődés a szöveges tulajdonságokat, például a színt, a betűt és a sormagasságot adja tovább a szülőtől a gyerekeknek.',
  ),
  ...c('css', `${LEARN_CSS}selectors`,
    'Simple selectors target a type, a class, an id or an attribute. Combinators describe relationships: a space for any descendant, > for a direct child, + for the next sibling and ~ for any later sibling. Pseudo-classes describe state — hover, focus, checked, disabled — and position, such as first-child or nth-child.',
    'Az egyszerű szelektorok típust, osztályt, id-t vagy attribútumot céloznak. A kombinátorok kapcsolatot írnak le: szóköz bármely leszármazottra, > közvetlen gyerekre, + a következő testvérre, ~ bármely későbbi testvérre. A pszeudoosztályok állapotot írnak le — hover, focus, checked, disabled — és helyzetet, például first-child vagy nth-child.',
  ),
  ...c('css', `${LEARN_CSS}flexbox`,
    'A flex container lays its children along a main axis. flex-direction chooses row or column, justify-content distributes space along the main axis — start, center, space-between, space-evenly — and align-items positions items on the cross axis. Each item can grow with flex-grow, shrink with flex-shrink and start from a flex-basis.',
    'A flex konténer a gyerekeit egy fő tengely mentén rendezi. A flex-direction sort vagy oszlopot választ, a justify-content a fő tengelyen osztja el a helyet — start, center, space-between, space-evenly —, az align-items pedig a kereszttengelyen igazít. Minden elem nőhet a flex-grow-val, zsugorodhat a flex-shrink-kel, és egy flex-basis méretből indul.',
  ),
  ...c('css', `${LEARN_CSS}grid`,
    'A grid container defines rows and columns called tracks. The fr unit shares the remaining space, minmax sets a minimum and maximum size, and repeat with auto-fit or auto-fill creates as many columns as fit. Items can span several tracks, be placed by line numbers, or be put into named areas drawn with grid-template-areas.',
    'A grid konténer sorokat és oszlopokat, úgynevezett sávokat definiál. Az fr egység a maradék helyet osztja el, a minmax minimum és maximum méretet ad, a repeat pedig auto-fit vagy auto-fill mellett annyi oszlopot hoz létre, amennyi elfér. Az elemek több sávot átfoghatnak, vonalszámmal helyezhetők el, vagy a grid-template-areas-szel rajzolt, elnevezett területekre tehetők.',
  ),
  ...c('css', `${MDN}CSS_positioned_layout`,
    'Positioning takes an element out of the normal flow or nudges it. Absolute positioning needs a positioned ancestor as its reference, usually a parent with position relative. Sticky elements behave normally until they reach a scroll edge, then stick — perfect for headers and table headings. Stacking contexts, created by z-index, opacity, transform and filters, decide what overlaps what.',
    'A pozicionálás kiveszi az elemet a normál folyamból, vagy eltolja. Az abszolút pozicionáláshoz kell egy pozicionált ős viszonyítási pontnak, általában egy relative szülő. A sticky elem normálisan viselkedik, amíg görgetéskor el nem éri a szélt, aztán odatapad — ideális fejlécekhez és táblázatfejekhez. A rétegzési kontextusok, amelyeket a z-index, az opacity, a transform és a filter hoz létre, döntik el, mi fed mit.',
  ),
  ...c('css', `${LEARN_DESIGN}media-queries`,
    'Media queries apply styles when a condition is true: a minimum or maximum width, the orientation, the user preference for dark colours or reduced motion, or whether the device can hover. Modern range syntax reads naturally, like width greater than 600px. Write the mobile layout first and add queries as the screen grows.',
    'A media query akkor alkalmaz stílust, ha egy feltétel teljesül: minimális vagy maximális szélesség, tájolás, a felhasználó sötét színekre vagy csökkentett mozgásra vonatkozó beállítása, vagy hogy az eszköz tud-e hovert. A modern tartomány-szintaxis természetesen olvasható, például width nagyobb, mint 600px. Először a mobil elrendezést írd meg, és a képernyő növekedésével adj hozzá queryket.',
  ),
  ...c('css', `${MDN}CSS_containment/Container_queries`,
    'Container queries move responsiveness from the page to the component. A wrapper declares itself a container with container-type, and the component inside adapts to the space it actually has. The same card component can therefore sit in a narrow sidebar or a wide grid and look right in both, with no page-level breakpoints.',
    'A container query a reszponzivitást az oldalról a komponensre helyezi át. Egy burkoló a container-type-pal konténernek jelöli magát, a benne lévő komponens pedig a ténylegesen rendelkezésre álló helyhez igazodik. Ugyanaz a kártyakomponens így keskeny oldalsávban és széles rácsban is jól mutat, oldalszintű töréspontok nélkül.',
  ),
  ...c('css', `${MDN}CSS_custom_properties_for_cascading_variables`,
    'Custom properties are variables that live in the cascade. Because they inherit, a theme can change a handful of values on the root element or a section and every component updates. They can hold colours, sizes, shadows, durations or even partial values, and they can be changed at runtime with JavaScript.',
    'Az egyéni tulajdonságok a kaszkádban élő változók. Mivel öröklődnek, egy téma néhány értéket átírhat a gyökérelemen vagy egy szakaszon, és minden komponens frissül. Tárolhatnak színt, méretet, árnyékot, időtartamot vagy akár részleges értéket, és futás közben JavaScripttel is módosíthatók.',
  ),
  ...c('css', `${LEARN_CSS}animations`,
    'Transitions animate from one value to another when something changes, such as on hover or when a class is added. Keyframe animations define their own timeline with several steps, can repeat and can run on load. Animating transform and opacity is cheap for the browser; animating width, height or top causes layout work and can stutter.',
    'Az átmenet (transition) egyik értékből a másikba animál, amikor valami változik, például hoverre vagy egy osztály hozzáadásakor. A keyframe animáció saját, többlépéses idővonalat határoz meg, ismétlődhet, és betöltéskor is elindulhat. A transform és az opacity animálása olcsó a böngészőnek; a width, height vagy top animálása elrendezési munkát okoz, és akadozhat.',
  ),
  ...c('css', `${MDN}color_value`,
    'CSS can describe colour in many ways: keywords, hex codes, rgb, hsl, and the newer oklch and oklab spaces. In oklch the three numbers are lightness, chroma and hue, and equal steps in lightness look equal to the eye, which makes generating consistent shade scales and accessible pairs much easier than with hsl.',
    'A CSS sokféleképpen írhat le színt: kulcsszóval, hex kóddal, rgb-vel, hsl-lel, és az újabb oklch és oklab terekkel. Az oklch három száma a világosság, a króma és az árnyalat, és a világosság egyenlő lépései a szemnek is egyenlőnek tűnnek, így sokkal könnyebb egységes árnyalatskálát és akadálymentes színpárokat készíteni, mint hsl-lel.',
  ),
  ...c('css', `${MDN}CSS_nesting`,
    'Native nesting, cascade layers, the has selector, subgrid and container queries changed how CSS is written. Many tasks that once needed a preprocessor or JavaScript — theming, parent-aware styling, component-level responsiveness, ordering third-party styles — can now be done in plain CSS supported by every modern browser.',
    'A natív beágyazás, a cascade layerek, a has szelektor, a subgrid és a container query megváltoztatta a CSS írását. Sok feladat, amihez korábban előfeldolgozó vagy JavaScript kellett — témázás, szülőre figyelő stílusozás, komponensszintű reszponzivitás, külső stílusok sorrendezése —, ma sima CSS-sel megoldható, amit minden modern böngésző támogat.',
  ),

  // ── visual design ────────────────────────────────────────────────────────────
  ...c('design', `${LEARN_DESIGN}typography`,
    'Typography carries most of an interface. Choose a readable typeface, set a comfortable base size and line height, limit line length, and build a small scale of sizes with a consistent ratio. Use weight and colour, not only size, to separate headings, body text, captions and labels, and keep letter spacing slightly tighter on large headings.',
    'A felület nagy részét a tipográfia viszi. Válassz olvasható betűt, állíts be kényelmes alapméretet és sormagasságot, korlátozd a sorhosszt, és építs kis, következetes arányú méretskálát. A címeket, a szöveget, a képaláírásokat és a címkéket ne csak mérettel, hanem vastagsággal és színnel is válaszd el, a nagy címeknél pedig kicsit szorosabb legyen a betűköz.',
  ),
  ...c('design', `${LEARN_DESIGN}theming`,
    'A colour system starts with roles: background, surface, text, muted text, border, primary, and the states success, warning and danger. Each role gets a light and a dark value, stored as variables. Designing with roles instead of raw colours makes dark mode, brand changes and accessibility fixes a matter of changing a few tokens.',
    'Egy színrendszer szerepekkel indul: háttér, felület, szöveg, halvány szöveg, keret, elsődleges szín, valamint a siker, figyelmeztetés és veszély állapotai. Minden szerep kap egy világos és egy sötét értéket, változóként tárolva. Ha nyers színek helyett szerepekkel tervezel, a sötét mód, a márkaváltás és az akadálymentességi javítás néhány token átírása lesz.',
  ),
  ...c('design', WCAG,
    'Accessibility is part of good design, not an extra. Text needs enough contrast against its background, interactive elements need a visible focus state and a large enough target, information must not depend on colour alone, and motion should respect the reduced-motion preference. These rules help everyone, including people in bright sunlight or on a small screen.',
    'Az akadálymentesség a jó dizájn része, nem ráadás. A szövegnek elég kontraszt kell a hátteréhez, az interaktív elemeknek látható fókuszállapot és elég nagy célterület, az információ nem múlhat csak a színen, a mozgásnak pedig tiszteletben kell tartania a csökkentett mozgás beállítást. Ezek a szabályok mindenkinek segítenek, a tűző napon vagy kis képernyőn olvasóknak is.',
  ),
  ...c('design', 'https://lawsofux.com/',
    'Whitespace is an active design element. Space around a block makes it stand out, space between groups shows what belongs together, and generous margins make a page feel calm and premium. Crowded layouts force the eye to work; when a design looks messy, removing borders and adding space often fixes more than adding decoration.',
    'Az üres tér aktív dizájnelem. A blokk körüli hely kiemeli, a csoportok közötti hely megmutatja, mi tartozik össze, a bőkezű margók pedig nyugodttá és prémiummá teszik az oldalt. A zsúfolt elrendezés megdolgoztatja a szemet; ha egy dizájn rendetlennek tűnik, a keretek elhagyása és több hely gyakran többet javít, mint a díszítés.',
  ),
  ...c('design', 'https://lawsofux.com/',
    'Hierarchy guides attention. The most important element on a screen should be the largest, boldest or most colourful, the second most important a step quieter, and supporting details quiet. Squinting at a design is a quick test: if nothing stands out, or everything does, the hierarchy needs work.',
    'A hierarchia irányítja a figyelmet. A képernyő legfontosabb eleme legyen a legnagyobb, legvastagabb vagy legszínesebb, a második egy fokkal halkabb, a kiegészítő részletek pedig visszafogottak. Gyors teszt, ha hunyorogva nézed a dizájnt: ha semmi sem ugrik ki, vagy minden kiugrik, a hierarchián dolgozni kell.',
  ),
  ...c('design', 'https://lawsofux.com/',
    'Consistency makes an interface learnable. The same action should look the same everywhere, spacing should come from one scale, corners from one radius set, and shadows from one elevation system. Users transfer what they learn on one screen to the next, so every exception costs attention.',
    'A következetesség teszi tanulhatóvá a felületet. Ugyanaz a művelet mindenhol ugyanúgy nézzen ki, a térközök egy skálából, a sarkok egy ív-készletből, az árnyékok egy mélységrendszerből jöjjenek. A felhasználó az egyik képernyőn tanultakat viszi a következőre, így minden kivétel figyelembe kerül.',
  ),
  ...c('design', `${LEARN_DESIGN}ui-patterns`,
    'Familiar patterns reduce effort: a logo top left that links home, navigation along the top or bottom, a search field with a magnifier icon, cards for collections, tabs for switching views of the same thing, and a single primary button for the main action. Reinvent a pattern only when the familiar one truly fails.',
    'Az ismerős minták csökkentik az erőfeszítést: balra fent a főoldalra vivő logó, fent vagy lent a navigáció, nagyító ikonos keresőmező, kártyák a gyűjteményekhez, fülek ugyanannak a dolognak a nézetei közötti váltáshoz, és egyetlen elsődleges gomb a fő művelethez. Csak akkor találj ki új mintát, ha az ismerős tényleg nem működik.',
  ),
  ...c('design', `${LEARN_DESIGN}interaction`,
    'Every interactive element has states: default, hover, pressed, focused, disabled, loading, and for inputs also filled, invalid and valid. Designing all of them up front prevents a polished screen from feeling broken the moment someone uses it, and gives keyboard and touch users clear feedback.',
    'Minden interaktív elemnek vannak állapotai: alap, hover, lenyomott, fókuszált, letiltott, töltő, a beviteli mezőknek pedig kitöltött, érvénytelen és érvényes is. Ha mindet előre megtervezed, egy szép képernyő sem tűnik hibásnak, amint valaki használni kezdi, és a billentyűzetes meg az érintéses felhasználók is egyértelmű visszajelzést kapnak.',
  ),
  ...c('design', 'https://m3.material.io/',
    'Elevation tells which surface is on top. In light themes higher surfaces cast larger, softer shadows; in dark themes they get slightly lighter backgrounds instead, because shadows are hard to see on dark grey. Dialogs and menus float highest, cards sit just above the page, and the page itself has no elevation.',
    'A mélység (elevation) megmutatja, melyik felület van felül. Világos témában a magasabb felület nagyobb, lágyabb árnyékot vet; sötét témában inkább kicsit világosabb hátteret kap, mert a sötétszürkén alig látszik az árnyék. A dialógusok és menük lebegnek a legmagasabban, a kártyák épp az oldal fölött vannak, maga az oldal pedig nulla szinten.',
  ),
  ...c('design', 'https://m3.material.io/',
    'Motion should explain, not decorate. Elements entering the screen ease out, leaving elements ease in, things that move across the screen use both. Durations stay short — around 150 milliseconds for small changes and up to 400 for large panels — and related elements can be staggered slightly so the eye can follow the change.',
    'A mozgás magyarázzon, ne díszítsen. A belépő elemek ease-out-tal, a távozók ease-in-nel mozognak, a képernyőn átmozgók mindkettővel. Az időtartamok rövidek — kis változásnál kb. 150 ezredmásodperc, nagy paneleknél legfeljebb 400 —, az összetartozó elemek pedig enyhén lépcsőzhetők, hogy a szem követni tudja a változást.',
  ),
  ...c('design', `${LEARN_DESIGN}images`,
    'Images set the mood of a page. Use a consistent style and aspect ratio, crop with object-fit instead of stretching, add a gradient overlay when text sits on a photo, compress to modern formats and lazy-load anything below the first screen. Illustrations and icons should share one stroke width and colour palette.',
    'A képek adják meg az oldal hangulatát. Használj egységes stílust és képarányt, torzítás helyett object-fittel vágj, ha fotóra kerül szöveg, tegyél alá színátmenetes rátétet, tömöríts modern formátumba, és az első képernyő alattiakat töltsd lustán. Az illusztrációk és ikonok közös vonalvastagságot és színpalettát használjanak.',
  ),
  ...c('design', 'https://web.dev/learn/design/',
    'A good landing page reads top to bottom like a short argument: a headline that states the value, proof that it is true, the main features with a picture each, answers to the common objections, and one repeated call to action. Each section has one job, generous spacing and a clear heading.',
    'Egy jó landing oldal fentről lefelé rövid érvelésként olvasható: főcím, amely kimondja az értéket, bizonyíték, hogy igaz, a fő funkciók egy-egy képpel, válaszok a gyakori ellenvetésekre, és egy ismételt cselekvésre hívás. Minden szakasznak egy feladata, bőséges térköze és egyértelmű címe van.',
  ),
  ...c('design', 'https://m3.material.io/',
    'Design tokens turn decisions into data: names such as color-primary, space-4, radius-lg and shadow-2 hold the actual values. Designers use the same tokens in their tools that developers use as CSS variables or theme objects, so a change in one place updates the whole product and the design files never drift away from the code.',
    'A design tokenek adattá alakítják a döntéseket: az olyan nevek, mint a color-primary, space-4, radius-lg és shadow-2, tartalmazzák a tényleges értékeket. A tervezők ugyanazokat a tokeneket használják az eszközeikben, mint a fejlesztők CSS-változóként vagy témaobjektumként, így egy helyen végzett változtatás az egész terméket frissíti, és a tervfájlok sosem csúsznak el a kódtól.',
  ),
  ...c('design', 'https://lawsofux.com/',
    'Usability heuristics are quick checks for any screen: show the system status, speak the user’s language, let people undo, stay consistent, prevent errors before they happen, prefer recognition over recall, offer shortcuts to experts, keep the design minimal, write helpful error messages and provide help where it is needed.',
    'A használhatósági heurisztikák gyors ellenőrzések bármely képernyőhöz: mutasd a rendszer állapotát, beszéld a felhasználó nyelvét, engedj visszavonást, légy következetes, előzd meg a hibákat, a felismerést részesítsd előnyben az emlékezéssel szemben, adj gyorsbillentyűket a haladóknak, tartsd minimálisan a dizájnt, írj segítőkész hibaüzeneteket, és adj segítséget, ahol kell.',
  ),
];
