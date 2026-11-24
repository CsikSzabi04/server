// knowledge.ts — a broad, bilingual GENERAL-KNOWLEDGE base so the local brain can
// hold a real conversation about "anything" and answer in CLEAN, whole sentences,
// offline and with no API key. Two jobs:
//   1) findKnowledge(query, lang) → a ready, well-formed answer in EN or HU (the
//      answering layer prefers this over raw Markov, which only babbles).
//   2) KNOWLEDGE_TEXT → fed to the learner so the vocabulary + association graph
//      grow dense (more nodes/edges = the "looks like a brain" map).
//
// Every entry is original, factual and short. Keywords are lowercase stems matched at
// the START of a word, so Hungarian suffixed forms (Földről, vízben, vulkánokról) hit,
// but a stem buried inside another word does not ("vagy" ≠ "agy", "brain" ≠ "rain").
// An entry only answers when the query really ASKS ABOUT its topic (a definition /
// "tell me about" question, a bare topic, or an exact phrase) — never for a task that
// merely mentions it ("írj egy python függvényt…") — see findKnowledge().
import { LANG_KNOWLEDGE } from './languages';
import { DESIGN_KNOWLEDGE } from './design';
import { expandTechAliases } from './techAlias';
import { coversQuery } from '../relevance';

export interface KnowledgeEntry {
  topic: string;
  keywords: string[];
  en: string;
  hu: string;
}

export const KNOWLEDGE: KnowledgeEntry[] = [
  // ── Auri itself (identity questions must never fall into a random topic) ───────
  { topic: 'auri', keywords: ['ki vagy', 'mi vagy', 'mutatkozz be', 'bemutatkoz', 'mi a neved', 'hogy hívnak', 'hogy hivnak', 'who are you', 'what are you', 'introduce yourself', 'your name'], en: 'I’m Auri, your own AI assistant. I help most with programming and technical questions, and I remember what we discuss in my BRAIN so I can answer better next time.', hu: 'Auri vagyok, a saját AI-asszisztensed. Leginkább programozásban és technikai kérdésekben segítek, és amit megbeszélünk, azt a BRAIN-emben megjegyzem, hogy legközelebb jobban válaszoljak.' },
  // ── science: space & earth ───────────────────────────────────────────────────
  { topic: 'sun', keywords: ['sun', 'nap ', ' nap', 'napunk', 'naprol'], en: 'The Sun is the star at the centre of our solar system. It is a huge ball of hot gas that gives the Earth light and warmth.', hu: 'A Nap a Naprendszerünk középpontjában lévő csillag. Hatalmas, forró gázgömb, amely fényt és meleget ad a Földnek.' },
  { topic: 'moon', keywords: ['moon', 'hold'], en: 'The Moon is the Earth’s only natural satellite. It orbits the Earth about once a month and reflects the Sun’s light at night.', hu: 'A Hold a Föld egyetlen természetes holdja. Körülbelül havonta egyszer kerüli meg a Földet, és éjjel a Nap fényét veri vissza.' },
  { topic: 'earth', keywords: ['earth', 'föld', 'fold', 'föld bolygó', 'planet earth'], en: 'The Earth is the third planet from the Sun and the only one known to support life. It is round and travels around the Sun once a year.', hu: 'A Föld a Naptól számított harmadik bolygó, és az egyetlen ismert, ahol van élet. Gömbölyű, és egy év alatt kerüli meg a Napot.' },
  { topic: 'stars', keywords: ['star', 'csillag', 'galaxy', 'galaxis', 'univerzum', 'universe'], en: 'Stars are giant balls of burning gas far out in space. Our galaxy, the Milky Way, holds billions of them.', hu: 'A csillagok hatalmas, égő gázgömbök a világűrben. A galaxisunk, a Tejútrendszer, milliárdnyit tartalmaz belőlük.' },
  { topic: 'gravity', keywords: ['gravity', 'gravitáció', 'gravitacio', 'gravitaci'], en: 'Gravity is the force that pulls objects toward each other. It is why things fall down and why planets orbit the Sun.', hu: 'A gravitáció az az erő, amely a testeket egymás felé húzza. Ezért esnek le a dolgok, és ezért keringenek a bolygók a Nap körül.' },
  // ── science: physical world ───────────────────────────────────────────────────
  { topic: 'water', keywords: ['water', 'víz', 'viz', 'vízbol', 'vizbol'], en: 'Water is a clear liquid made of hydrogen and oxygen. It covers most of the Earth and every living thing needs it.', hu: 'A víz tiszta folyadék, amely hidrogénből és oxigénből áll. A Föld nagy részét borítja, és minden élőlénynek szüksége van rá.' },
  { topic: 'air', keywords: ['air ', ' air', 'levegő', 'levego', 'oxigén', 'oxygen'], en: 'Air is the mix of gases around us, mostly nitrogen and oxygen. We breathe its oxygen to live.', hu: 'A levegő a körülöttünk lévő gázok keveréke, főleg nitrogén és oxigén. Az oxigénjét belélegezve élünk.' },
  { topic: 'fire', keywords: ['fire', 'tűz', 'tuz', 'égés', 'eges'], en: 'Fire is the heat and light released when something burns. It needs fuel, oxygen and heat to start.', hu: 'A tűz az a hő és fény, ami égéskor szabadul fel. Tüzelőanyag, oxigén és hő kell az elindulásához.' },
  { topic: 'energy', keywords: ['energy', 'energia', 'power '], en: 'Energy is the ability to do work, such as moving or heating things. It can change form but is never lost.', hu: 'Az energia a munkavégzés képessége, például mozgatni vagy melegíteni. Átalakulhat, de sosem vész el.' },
  { topic: 'weather', keywords: ['weather', 'időjárás', 'idojaras', 'rain', 'eső', 'eso', 'wind', 'szél', 'szel'], en: 'Weather is the state of the air outside: sunshine, clouds, rain, wind and temperature, which change from day to day.', hu: 'Az időjárás a külső levegő állapota: napsütés, felhők, eső, szél és hőmérséklet, amelyek napról napra változnak.' },
  // ── life & nature ─────────────────────────────────────────────────────────────
  { topic: 'plants', keywords: ['plant', 'növény', 'noveny', 'tree', 'fa ', 'flower', 'virág', 'virag'], en: 'Plants are living things that grow in soil and make their own food from sunlight, water and air through photosynthesis.', hu: 'A növények élőlények, amelyek a talajban nőnek, és a fotoszintézis révén napfényből, vízből és levegőből készítenek táplálékot.' },
  { topic: 'animals', keywords: ['animal', 'állat', 'allat', 'dog', 'kutya', 'cat', 'macska'], en: 'Animals are living things that move and feed on plants or other animals. They range from tiny insects to huge whales.', hu: 'Az állatok mozgó élőlények, amelyek növényekkel vagy más állatokkal táplálkoznak. A pici rovaroktól a hatalmas bálnákig terjednek.' },
  { topic: 'human-body', keywords: ['body', 'test ', 'human', 'ember', 'heart', 'szív', 'sziv', 'brain', 'agy'], en: 'The human body is built from cells, organs and systems. The heart pumps blood, the lungs take in air and the brain controls it all.', hu: 'Az emberi test sejtekből, szervekből és rendszerekből épül fel. A szív vért pumpál, a tüdő levegőt vesz, az agy pedig mindezt irányítja.' },
  { topic: 'food', keywords: ['food', 'étel', 'etel', 'eat', 'eszik', 'táplál', 'taplal'], en: 'Food gives the body energy and the materials it needs to grow and stay healthy. A balanced diet mixes many kinds of food.', hu: 'Az étel energiát és építőanyagot ad a testnek a növekedéshez és az egészséghez. A kiegyensúlyozott étrend sokféle ételt vegyít.' },
  { topic: 'health', keywords: ['health', 'egészség', 'egeszseg', 'healthy', 'exercise', 'mozgás', 'mozgas'], en: 'Good health comes from eating well, sleeping enough, moving your body and managing stress. Small daily habits matter most.', hu: 'A jó egészség a megfelelő táplálkozásból, elég alvásból, mozgásból és a stressz kezeléséből fakad. A kis napi szokások számítanak a legtöbbet.' },
  // ── geography ─────────────────────────────────────────────────────────────────
  { topic: 'continents', keywords: ['continent', 'kontinens', 'földrész', 'foldresz'], en: 'There are seven continents: Africa, Antarctica, Asia, Europe, North America, South America and Australia.', hu: 'Hét kontinens van: Afrika, Antarktisz, Ázsia, Európa, Észak-Amerika, Dél-Amerika és Ausztrália.' },
  { topic: 'oceans', keywords: ['ocean', 'óceán', 'ocean', 'sea ', 'tenger'], en: 'There are five oceans: the Pacific, the Atlantic, the Indian, the Southern and the Arctic. They cover most of the planet.', hu: 'Öt óceán van: a Csendes-, az Atlanti-, az Indiai-, a Déli- és a Jeges-tenger. A bolygó nagy részét borítják.' },
  { topic: 'hungary', keywords: ['hungary', 'magyarország', 'magyarorszag', 'budapest'], en: 'Hungary is a country in Central Europe. Its capital is Budapest and its language is Hungarian.', hu: 'Magyarország egy közép-európai ország. A fővárosa Budapest, a nyelve pedig a magyar.' },
  { topic: 'europe', keywords: ['europe', 'európa', 'europa'], en: 'Europe is a continent of many countries, such as France, Germany, Italy and Hungary. Most use the shared currency, the euro.', hu: 'Európa sok országból álló kontinens, például Franciaország, Németország, Olaszország és Magyarország. A legtöbb a közös pénznemet, az eurót használja.' },
  { topic: 'mountains', keywords: ['mountain', 'hegy', 'river', 'folyó', 'folyo'], en: 'Mountains are high parts of the land, and rivers are flowing streams of water that run from the hills to the sea.', hu: 'A hegyek a szárazföld magas részei, a folyók pedig áramló vizek, amelyek a dombok felől a tenger felé folynak.' },
  // ── time, numbers, math ───────────────────────────────────────────────────────
  { topic: 'time', keywords: ['time', 'idő', 'ido', 'óra', 'ora', 'clock', 'hour'], en: 'Time is measured in seconds, minutes and hours. There are 60 seconds in a minute, 60 minutes in an hour and 24 hours in a day.', hu: 'Az időt másodpercben, percben és órában mérjük. Egy perc 60 másodperc, egy óra 60 perc, egy nap pedig 24 óra.' },
  { topic: 'calendar', keywords: ['week', 'hét', 'het', 'month', 'hónap', 'honap', 'year', 'év ', 'season', 'évszak', 'evszak'], en: 'A week has seven days and a year has twelve months and four seasons: spring, summer, autumn and winter.', hu: 'Egy hét hét napból áll, egy év pedig tizenkét hónapból és négy évszakból: tavasz, nyár, ősz és tél.' },
  { topic: 'math', keywords: ['math', 'matek', 'matematik', 'number', 'szám', 'szam', 'count', 'számol', 'szamol'], en: 'Mathematics is the study of numbers, shapes and patterns. Its basic operations are adding, subtracting, multiplying and dividing.', hu: 'A matematika a számok, alakzatok és mintázatok tudománya. Alapműveletei az összeadás, kivonás, szorzás és osztás.' },
  { topic: 'geometry', keywords: ['geometry', 'geometria', 'shape', 'alakzat', 'circle', 'kör ', 'square', 'négyzet', 'negyzet'], en: 'Geometry studies shapes: a circle is round, a square has four equal sides, and a triangle has three sides.', hu: 'A geometria az alakzatokat vizsgálja: a kör gömbölyű, a négyzetnek négy egyenlő oldala van, a háromszögnek pedig három.' },
  // ── technology ────────────────────────────────────────────────────────────────
  { topic: 'computer', keywords: ['computer', 'számítógép', 'szamitogep', 'gép ', 'pc '], en: 'A computer is a machine that stores information and follows instructions called programs. It works with the binary numbers 0 and 1.', hu: 'A számítógép olyan gép, amely adatokat tárol, és programoknak nevezett utasításokat követ. A kettes számrendszer 0 és 1 jegyeivel dolgozik.' },
  { topic: 'internet', keywords: ['internet', 'web ', 'website', 'online', 'hálózat', 'halozat'], en: 'The internet is a global network that connects computers so people can share information, send messages and visit websites.', hu: 'Az internet egy globális hálózat, amely összeköti a számítógépeket, hogy az emberek információt osszanak meg, üzenjenek és weboldalakat látogassanak.' },
  { topic: 'ai', keywords: ['artificial intelligence', 'ai ', 'mesterséges', 'mesterseges', 'robot'], en: 'Artificial intelligence is software that learns patterns from data to answer questions, recognise things or make decisions.', hu: 'A mesterséges intelligencia olyan szoftver, amely adatokból mintázatokat tanul, hogy kérdésekre válaszoljon, dolgokat felismerjen vagy döntsön.' },
  { topic: 'phone', keywords: ['phone', 'telefon', 'mobil', 'smartphone'], en: 'A smartphone is a small computer you carry. It makes calls, runs apps, takes photos and connects to the internet.', hu: 'Az okostelefon egy kis, hordozható számítógép. Hív, alkalmazásokat futtat, fényképez és internetre csatlakozik.' },
  { topic: 'programming', keywords: ['programming', 'programozás', 'programozas', 'code ', 'kód', 'kod', 'coding'], en: 'Programming is writing clear, step-by-step instructions that a computer can follow. Popular languages include JavaScript, Python and Java.', hu: 'A programozás világos, lépésről lépésre megírt utasítások készítése, amelyeket a számítógép követni tud. Népszerű nyelvek a JavaScript, a Python és a Java.' },
  // ── language & communication ──────────────────────────────────────────────────
  { topic: 'language', keywords: ['language', 'nyelv', 'beszéd', 'beszed', 'word ', 'szó ', 'speak'], en: 'A language is a shared system of words and grammar that lets people share ideas by speaking or writing.', hu: 'A nyelv a szavak és a nyelvtan közös rendszere, amely lehetővé teszi, hogy az emberek beszéddel vagy írással osszák meg a gondolataikat.' },
  { topic: 'reading', keywords: ['read', 'olvas', 'book', 'könyv', 'konyv', 'write', 'ír ', 'írás', 'iras'], en: 'Reading turns written words into meaning, and writing turns ideas into words. Both grow with practice.', hu: 'Az olvasás a leírt szavakat jelentéssé alakítja, az írás pedig a gondolatokat szavakká. Mindkettő gyakorlással fejlődik.' },
  // ── daily life ────────────────────────────────────────────────────────────────
  { topic: 'money', keywords: ['money', 'pénz', 'penz', 'buy', 'vásárol', 'vasarol', 'price', 'ár '], en: 'Money is what we use to buy goods and services. Saving a little regularly helps you afford bigger things later.', hu: 'A pénz az, amivel árukat és szolgáltatásokat veszünk. Ha rendszeresen félreteszünk egy keveset, később nagyobb dolgokra is futja.' },
  { topic: 'work', keywords: ['munka', 'job ', 'állás', 'allas', 'career', 'workplace'], en: 'Work is the activity you do to earn a living or reach a goal. Clear priorities and short breaks keep it productive.', hu: 'A munka az a tevékenység, amellyel megélhetést keresel vagy célt érsz el. A világos sorrend és a rövid szünetek hatékonnyá teszik.' },
  { topic: 'school', keywords: ['school', 'iskola', 'learn', 'tanul', 'study', 'oktatás', 'oktatas'], en: 'School is where people learn to read, write, count and understand the world. Learning continues throughout life.', hu: 'Az iskola az a hely, ahol az emberek megtanulnak olvasni, írni, számolni és megérteni a világot. A tanulás egész életen át tart.' },
  { topic: 'travel', keywords: ['travel', 'utazás', 'utazas', 'trip', 'journey', 'út '], en: 'Travel means going from one place to another to see new things or meet people. A little planning makes any trip smoother.', hu: 'Az utazás azt jelenti, hogy egyik helyről a másikra megyünk, hogy újat lássunk vagy embereket találjunk. Egy kis tervezés gördülékenyebbé tesz minden utat.' },
  { topic: 'family', keywords: ['family', 'család', 'csalad', 'friend', 'barát', 'barat'], en: 'A family is the close group of people you grow up with, and friends are those you choose to share life with.', hu: 'A család az a közeli csoport, amelyben felnövünk, a barátok pedig azok, akikkel megosztjuk az életünket.' },
  // ── feelings & advice ─────────────────────────────────────────────────────────
  { topic: 'happiness', keywords: ['happy', 'boldog', 'happiness', 'öröm', 'orom'], en: 'Happiness often comes from small things: good relationships, meaningful work, rest, and being kind to yourself and others.', hu: 'A boldogság gyakran kis dolgokból fakad: jó kapcsolatokból, értelmes munkából, pihenésből, és abból, ha kedves vagy magaddal és másokkal.' },
  { topic: 'stress', keywords: ['stress', 'stressz', 'worry', 'aggód', 'aggod', 'anxious', 'feszült', 'feszult'], en: 'When you feel stressed, slow your breathing, break the problem into small steps, and take a short break. It usually helps.', hu: 'Amikor stresszesnek érzed magad, lassíts a légzéseden, bontsd a problémát kis lépésekre, és tarts egy rövid szünetet. Általában segít.' },
  { topic: 'motivation', keywords: ['motivat', 'motivác', 'motivac', 'goal', 'cél ', 'celom', 'give up', 'feladni'], en: 'To stay motivated, set one small clear goal, start with the easiest step, and notice your progress. Done beats perfect.', hu: 'A motiváció megtartásához tűzz ki egy kis, világos célt, kezdd a legkönnyebb lépéssel, és vedd észre a haladásod. A kész jobb, mint a tökéletes.' },

  // ── deeper science ────────────────────────────────────────────────────────────
  { topic: 'electricity', keywords: ['electric', 'elektromos', 'áram', 'aram', 'current', 'feszültség', 'feszultseg'], en: 'Electricity is the flow of tiny charged particles called electrons through a wire. It powers lights, motors and computers.', hu: 'Az elektromosság apró, töltött részecskék, az elektronok áramlása egy vezetékben. Ez működteti a lámpákat, a motorokat és a számítógépeket.' },
  { topic: 'light', keywords: ['light ', 'fény', 'feny', 'color', 'szín', 'szin', 'rainbow', 'szivárvány'], en: 'Light is a form of energy that travels in waves and lets us see. White light splits into the colours of the rainbow.', hu: 'A fény hullámokban terjedő energia, amely lehetővé teszi a látást. A fehér fény a szivárvány színeire bomlik.' },
  { topic: 'sound', keywords: ['sound', 'hang ', 'hangok', 'noise', 'zaj', 'echo', 'visszhang'], en: 'Sound is a vibration that travels through the air to our ears. Faster vibrations make higher sounds.', hu: 'A hang egy rezgés, amely a levegőn át a fülünkhöz ér. A gyorsabb rezgés magasabb hangot ad.' },
  { topic: 'atom', keywords: ['atom', 'molecule', 'molekula', 'matter', 'anyag'], en: 'Everything is made of tiny building blocks called atoms. Atoms join into molecules, which form all the matter around us.', hu: 'Minden apró építőkockákból, atomokból áll. Az atomok molekulákká kapcsolódnak, és ezek alkotják a körülöttünk lévő anyagot.' },
  { topic: 'evolution', keywords: ['evolution', 'evolúció', 'evolucio', 'species', 'faj '], en: 'Evolution is the slow change of living things over many generations, as the traits that help survival become more common.', hu: 'Az evolúció az élőlények lassú változása sok nemzedéken át, ahogy a túlélést segítő tulajdonságok egyre gyakoribbá válnak.' },
  { topic: 'seasons-why', keywords: ['why season', 'miért van', 'tilt', 'tengely', 'axis', 'évszakok oka'], en: 'We have seasons because the Earth is tilted on its axis, so different parts get more direct sunlight at different times of the year.', hu: 'Azért vannak évszakok, mert a Föld megdőlt a tengelyén, így az év különböző szakaszaiban más-más rész kap több közvetlen napfényt.' },
  { topic: 'climate', keywords: ['climate', 'éghajlat', 'eghajlat', 'global warming', 'klíma', 'klima'], en: 'Climate is the usual weather of a place over many years. Burning fuels adds gases that slowly warm the planet.', hu: 'Az éghajlat egy hely sok éven át jellemző időjárása. A tüzelőanyagok égetése olyan gázokat juttat a levegőbe, amelyek lassan melegítik a bolygót.' },
  { topic: 'volcano', keywords: ['volcano', 'vulkán', 'vulkan', 'earthquake', 'földrengés', 'foldrenges', 'lava'], en: 'A volcano is an opening in the Earth where hot melted rock erupts. Earthquakes happen when the ground’s plates suddenly shift.', hu: 'A vulkán a Föld nyílása, ahol forró, olvadt kőzet tör fel. A földrengés akkor van, amikor a talaj lemezei hirtelen elmozdulnak.' },
  // ── history & society ─────────────────────────────────────────────────────────
  { topic: 'history', keywords: ['history', 'történelem', 'tortenelem', 'past', 'múlt', 'mult', 'ancient'], en: 'History is the study of the past: what people did, built and learned. It helps us understand how today’s world came to be.', hu: 'A történelem a múlt tanulmányozása: mit tettek, építettek és tanultak az emberek. Segít megérteni, hogyan lett a mai világ.' },
  { topic: 'democracy', keywords: ['democracy', 'demokrácia', 'demokracia', 'vote', 'szavaz', 'election', 'választás', 'valasztas'], en: 'Democracy is a system where people choose their leaders by voting, and power is limited by laws that apply to everyone.', hu: 'A demokrácia olyan rendszer, amelyben az emberek szavazással választják a vezetőiket, és a hatalmat mindenkire vonatkozó törvények korlátozzák.' },
  { topic: 'economy', keywords: ['economy', 'gazdaság', 'gazdasag', 'market', 'piac', 'trade', 'kereskedelem'], en: 'The economy is how a society produces, shares and uses goods and services. Prices rise and fall with supply and demand.', hu: 'A gazdaság az, ahogyan egy társadalom árukat és szolgáltatásokat előállít, eloszt és felhasznál. Az árak a kereslet és kínálat szerint mozognak.' },
  { topic: 'law', keywords: ['law ', 'törvény', 'torveny', 'rule', 'szabály', 'szabaly', 'justice', 'jog '], en: 'Laws are the shared rules a society agrees to live by. They protect people’s rights and settle disputes fairly.', hu: 'A törvények azok a közös szabályok, amelyek szerint egy társadalom élni akar. Védik az emberek jogait, és igazságosan rendezik a vitákat.' },
  // ── arts & culture ────────────────────────────────────────────────────────────
  { topic: 'music', keywords: ['music', 'zene', 'song', 'dal ', 'instrument', 'hangszer'], en: 'Music is sound organised in time through melody, rhythm and harmony. It can express feelings words cannot.', hu: 'A zene időben rendezett hang, dallamból, ritmusból és harmóniából. Olyan érzéseket fejez ki, amiket szavak nem tudnak.' },
  { topic: 'art', keywords: ['art ', 'művészet', 'muveszet', 'paint', 'festészet', 'draw', 'rajz'], en: 'Art is the making of things for their beauty or meaning, such as painting, drawing and sculpture. It shares a personal view of the world.', hu: 'A művészet a szépségükért vagy jelentésükért alkotott dolgok, például festészet, rajz és szobrászat. Egy személyes világlátást oszt meg.' },
  { topic: 'film', keywords: ['film', 'movie', 'mozi', 'cinema'], en: 'A film tells a story with moving pictures and sound. It blends writing, acting, music and camera work into one experience.', hu: 'A film mozgóképpel és hanggal mesél el egy történetet. Az írást, a színészetet, a zenét és a kameramunkát egyetlen élménnyé fűzi.' },
  { topic: 'sport', keywords: ['sport', 'football', 'foci', 'game ', 'játék', 'jatek', 'exercise'], en: 'Sport is physical activity played by rules, alone or in teams. It builds health, skill and a sense of fair play.', hu: 'A sport szabályok szerint, egyénileg vagy csapatban űzött testmozgás. Egészséget, ügyességet és sportszerűséget fejleszt.' },
  // ── practical life ────────────────────────────────────────────────────────────
  { topic: 'cooking', keywords: ['cook', 'főz', 'foz', 'recipe ', 'recept', 'kitchen', 'konyha'], en: 'Cooking turns raw ingredients into a meal with heat and seasoning. Start simple: read the recipe through, prepare everything, then cook.', hu: 'A főzés hővel és fűszerezéssel alakít nyersanyagokat étellé. Kezdd egyszerűen: olvasd át a receptet, készíts elő mindent, aztán főzz.' },
  { topic: 'budgeting', keywords: ['budget', 'költségvetés', 'koltsegvetes', 'save money', 'megtakar', 'spend'], en: 'A budget is a simple plan for your money: list income, list spending, and keep a little aside for savings each month.', hu: 'A költségvetés egy egyszerű terv a pénzedre: írd össze a bevételt, írd össze a kiadást, és minden hónapban tegyél félre egy keveset.' },
  { topic: 'sleep', keywords: ['sleep', 'alvás', 'alvas', 'tired', 'fáradt', 'faradt', 'rest', 'pihen'], en: 'Most adults need about seven to nine hours of sleep. A regular bedtime and less screen light before bed help you rest well.', hu: 'A legtöbb felnőttnek nagyjából hét-kilenc óra alvás kell. A rendszeres lefekvés és a kevesebb képernyőfény segít a jó pihenésben.' },
  { topic: 'learning-tips', keywords: ['learn faster', 'hogyan tanul', 'study tip', 'memorize', 'memoriz', 'tanulási'], en: 'You learn faster in short, focused sessions, by testing yourself, and by spacing practice over days rather than cramming.', hu: 'Gyorsabban tanulsz rövid, fókuszált blokkokban, ha kikérdezed magad, és ha napokra elosztod a gyakorlást a magolás helyett.' },
  { topic: 'communication', keywords: ['communicat', 'kommunik', 'listen', 'figyel', 'conversation', 'beszélget'], en: 'Good communication means listening fully, speaking clearly and simply, and checking that the other person understood you.', hu: 'A jó kommunikáció azt jelenti, hogy végighallgatsz, világosan és egyszerűen beszélsz, és ellenőrzöd, hogy a másik megértett-e.' },
  // ── everyday "what is" ────────────────────────────────────────────────────────
  { topic: 'book', keywords: ['book', 'könyv', 'konyv', 'story', 'történet', 'tortenet'], en: 'A book is a set of written pages bound together. It can tell a story, share knowledge or record ideas to keep and pass on.', hu: 'A könyv összefűzött, megírt lapok együttese. Mesélhet történetet, tudást oszthat meg, vagy gondolatokat őrizhet meg és adhat tovább.' },
  { topic: 'city', keywords: ['city', 'város', 'varos', 'town', 'falu', 'village'], en: 'A city is a large place where many people live and work close together, with homes, shops, roads and services.', hu: 'A város egy nagy hely, ahol sokan élnek és dolgoznak közel egymáshoz, otthonokkal, boltokkal, utakkal és szolgáltatásokkal.' },
  { topic: 'car', keywords: ['car ', 'autó', 'auto', 'vehicle', 'jármű', 'jarmu', 'engine', 'motor'], en: 'A car is a road vehicle with an engine that carries a few people. Most run on petrol or, increasingly, on electricity.', hu: 'Az autó motorral hajtott közúti jármű, amely néhány embert szállít. A legtöbb benzinnel, egyre inkább pedig árammal megy.' },
  { topic: 'weather-now', keywords: ['hot ', 'cold ', 'meleg', 'hideg', 'temperature', 'hőmérséklet', 'homerseklet'], en: 'Temperature tells how hot or cold something is. Water freezes at zero degrees Celsius and boils at one hundred.', hu: 'A hőmérséklet azt mondja meg, mennyire meleg vagy hideg valami. A víz nulla Celsius-fokon fagy meg, és száz fokon forr.' },

  // ── more science ──────────────────────────────────────────────────────────────
  { topic: 'solar-system', keywords: ['solar system', 'naprendszer', 'planets', 'bolygók', 'bolygok'], en: 'The solar system has eight planets orbiting the Sun: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus and Neptune.', hu: 'A Naprendszerben nyolc bolygó kering a Nap körül: Merkúr, Vénusz, Föld, Mars, Jupiter, Szaturnusz, Uránusz és Neptunusz.' },
  { topic: 'cell', keywords: ['cell ', 'sejt', 'dna ', 'gene', 'gén '], en: 'All living things are made of cells, the smallest unit of life. Inside each cell, DNA carries the instructions that shape the organism.', hu: 'Minden élőlény sejtekből áll, az élet legkisebb egységéből. Minden sejtben a DNS hordozza az utasításokat, amelyek meghatározzák a szervezetet.' },
  { topic: 'photosynthesis', keywords: ['photosynthesis', 'fotoszintézis', 'fotoszintezis'], en: 'Photosynthesis is how green plants make food: they use sunlight to turn water and carbon dioxide into sugar and release oxygen.', hu: 'A fotoszintézis az, ahogy a zöld növények táplálékot készítenek: napfénnyel vízből és szén-dioxidból cukrot állítanak elő, és oxigént engednek ki.' },
  { topic: 'magnet', keywords: ['magnet', 'mágnes', 'magnes', 'magnetic'], en: 'A magnet pulls iron and steel toward it and has a north and a south pole. The Earth itself acts like a giant magnet, which is why a compass works.', hu: 'A mágnes magához vonzza a vasat és az acélt, és van északi és déli pólusa. Maga a Föld is óriási mágnesként viselkedik, ezért működik az iránytű.' },
  { topic: 'environment', keywords: ['environment', 'környezet', 'kornyezet', 'recycl', 'újrahaszn', 'ujrahaszn', 'pollution', 'szennyez'], en: 'Protecting the environment means using less, reusing what we can, recycling materials and cutting pollution so nature stays healthy.', hu: 'A környezet védelme azt jelenti, hogy kevesebbet használunk, újrahasználjuk, amit lehet, újrahasznosítjuk az anyagokat, és csökkentjük a szennyezést, hogy a természet egészséges maradjon.' },
  // ── more geography ────────────────────────────────────────────────────────────
  { topic: 'desert', keywords: ['desert', 'sivatag', 'sahara', 'szahara'], en: 'A desert is a very dry region that gets little rain. The Sahara in Africa is the largest hot desert on Earth.', hu: 'A sivatag nagyon száraz vidék, ahol kevés eső esik. Az afrikai Szahara a Föld legnagyobb forró sivataga.' },
  { topic: 'forest', keywords: ['forest', 'erdő', 'erdo', 'rainforest', 'esőerdő', 'jungle', 'dzsungel'], en: 'Forests are large areas covered with trees. Rainforests, like the Amazon, hold a huge share of the world’s plants and animals.', hu: 'Az erdők fákkal borított nagy területek. Az esőerdők, mint az Amazonas, a világ növényeinek és állatainak hatalmas részét őrzik.' },
  { topic: 'poles', keywords: ['north pole', 'south pole', 'északi sark', 'eszaki sark', 'antarctica', 'antarktisz', 'arctic'], en: 'The North and South Poles are the coldest places on Earth, covered in ice. Antarctica, around the South Pole, is a frozen continent.', hu: 'Az Északi- és a Déli-sark a Föld leghidegebb helyei, jéggel borítva. Az Antarktisz a Déli-sark körül egy fagyott kontinens.' },
  { topic: 'danube', keywords: ['danube', 'duna', 'tisza'], en: 'The Danube is the second longest river in Europe and flows through Budapest. The Tisza is the other great river of Hungary.', hu: 'A Duna Európa második leghosszabb folyója, és átfolyik Budapesten. A másik nagy magyar folyó a Tisza.' },
  // ── more history ──────────────────────────────────────────────────────────────
  { topic: 'ancient-egypt', keywords: ['ancient egypt', 'egypt', 'egyiptom', 'pyramid', 'piramis', 'pharaoh', 'fáraó', 'farao'], en: 'Ancient Egypt was a civilisation along the Nile thousands of years ago, famous for its pharaohs, pyramids and early writing.', hu: 'Az ókori Egyiptom a Nílus mentén virágzó civilizáció volt évezredekkel ezelőtt, híres a fáraóiról, a piramisairól és a korai írásáról.' },
  { topic: 'ancient-rome', keywords: ['ancient rome', 'rome', 'róma', 'roma ', 'roman empire', 'római', 'romai'], en: 'Ancient Rome grew from a city into a vast empire around the Mediterranean, shaping law, language, roads and architecture for centuries.', hu: 'Az ókori Róma egy városból hatalmas birodalommá nőtt a Földközi-tenger körül, és évszázadokra meghatározta a jogot, a nyelvet, az utakat és az építészetet.' },
  { topic: 'industrial-revolution', keywords: ['industrial revolution', 'ipari forradalom', 'steam engine', 'gőzgép', 'gozgep', 'factory', 'gyár'], en: 'The Industrial Revolution, from the 1700s, replaced handwork with machines and factories, changing how people lived and worked.', hu: 'Az ipari forradalom az 1700-as évektől gépekkel és gyárakkal váltotta fel a kézi munkát, és megváltoztatta, hogyan élnek és dolgoznak az emberek.' },
  // ── language & thinking ───────────────────────────────────────────────────────
  { topic: 'grammar', keywords: ['grammar', 'nyelvtan', 'sentence', 'mondat', 'verb', 'ige ', 'noun', 'főnév', 'fonev'], en: 'Grammar is the set of rules for building sentences: a noun names a thing, a verb shows an action, and word order ties them together.', hu: 'A nyelvtan a mondatépítés szabályainak összessége: a főnév megnevez valamit, az ige cselekvést fejez ki, a szórend pedig összefűzi őket.' },
  { topic: 'translation', keywords: ['translate', 'fordít', 'fordit', 'translation', 'fordítás', 'forditas'], en: 'Translation carries meaning from one language to another. Good translation keeps the sense, not just the words, in the target language.', hu: 'A fordítás egyik nyelvből a másikba viszi át a jelentést. A jó fordítás az értelmet őrzi meg a célnyelven, nem csak a szavakat.' },
  { topic: 'logic', keywords: ['logic', 'logika', 'reason', 'gondolkod', 'problem solv', 'problémamegold'], en: 'Logic is clear, step-by-step reasoning. To solve a problem, break it into smaller parts, handle each in turn, then check the result.', hu: 'A logika világos, lépésről lépésre haladó gondolkodás. Egy probléma megoldásához bontsd kisebb részekre, oldd meg egyenként, majd ellenőrizd az eredményt.' },

  // ── countries ─────────────────────────────────────────────────────────────────
  { topic: 'usa', keywords: ['united states', 'america', 'amerika', 'usa', 'egyesült államok'], en: 'The United States is a large country in North America with fifty states; its capital is Washington, D.C. and its language is mostly English.', hu: 'Az Egyesült Államok egy nagy észak-amerikai ország ötven állammal; fővárosa Washington, és nyelve főként az angol.' },
  { topic: 'china', keywords: ['china', 'kína', 'kina', 'beijing', 'peking'], en: 'China is the most populous country in Asia, with its capital in Beijing and Mandarin Chinese as the main language.', hu: 'Kína Ázsia legnépesebb országa, fővárosa Peking, fő nyelve a mandarin kínai.' },
  { topic: 'germany', keywords: ['germany', 'németország', 'nemetorszag', 'berlin', 'german '], en: 'Germany is a country in Central Europe; its capital is Berlin, its language is German, and it has a strong industrial economy.', hu: 'Németország egy közép-európai ország; fővárosa Berlin, nyelve a német, és erős ipari gazdasága van.' },
  { topic: 'france', keywords: ['france', 'franciaország', 'franciaorszag', 'paris', 'párizs'], en: 'France is a country in Western Europe; its capital is Paris and its language is French.', hu: 'Franciaország egy nyugat-európai ország; fővárosa Párizs, nyelve a francia.' },
  { topic: 'japan', keywords: ['japan', 'japán', 'japan ', 'tokyo', 'tokió'], en: 'Japan is an island country in East Asia; its capital is Tokyo and its language is Japanese.', hu: 'Japán egy kelet-ázsiai szigetország; fővárosa Tokió, nyelve a japán.' },
  { topic: 'uk', keywords: ['united kingdom', 'britain', 'anglia', 'england', 'london'], en: 'The United Kingdom is a country in Western Europe made of England, Scotland, Wales and Northern Ireland; its capital is London.', hu: 'Az Egyesült Királyság egy nyugat-európai ország, amelyet Anglia, Skócia, Wales és Észak-Írország alkot; fővárosa London.' },
  // ── world records / geography facts ─────────────────────────────────────────
  { topic: 'everest', keywords: ['everest', 'tallest mountain', 'legmagasabb hegy', 'highest mountain'], en: 'Mount Everest is the tallest mountain on Earth, about 8,849 metres high, on the border of Nepal and Tibet.', hu: 'A Mount Everest a Föld legmagasabb hegye, körülbelül 8 849 méter, Nepál és Tibet határán.' },
  { topic: 'longest-river', keywords: ['longest river', 'leghosszabb folyó', 'nile', 'nílus', 'amazon'], en: 'The Nile and the Amazon are the longest rivers on Earth, each over 6,500 kilometres long.', hu: 'A Nílus és az Amazonas a Föld leghosszabb folyói, mindkettő több mint 6 500 kilométer hosszú.' },
  { topic: 'biggest-animal', keywords: ['biggest animal', 'largest animal', 'legnagyobb állat', 'blue whale', 'bálna'], en: 'The blue whale is the largest animal that has ever lived, growing up to about 30 metres long.', hu: 'A kék bálna a valaha élt legnagyobb állat, akár 30 méter hosszúra is megnő.' },
  { topic: 'fastest-animal', keywords: ['fastest animal', 'leggyorsabb állat', 'cheetah', 'gepárd', 'gepard'], en: 'The cheetah is the fastest land animal, able to run about 100 kilometres per hour in short bursts.', hu: 'A gepárd a leggyorsabb szárazföldi állat, rövid távon körülbelül 100 kilométer per órával fut.' },
  { topic: 'population', keywords: ['population', 'népesség', 'nepesseg', 'how many people', 'mennyi ember', 'hány ember', 'ember él'], en: 'There are over eight billion people living on Earth today, spread across about two hundred countries.', hu: 'Ma több mint nyolcmilliárd ember él a Földön, mintegy kétszáz országban elosztva.' },
  // ── more science ──────────────────────────────────────────────────────────────
  { topic: 'sky-blue', keywords: ['sky blue', 'why is the sky', 'miért kék az ég', 'kék az ég'], en: 'The sky looks blue because air scatters the Sun’s blue light more than the other colours, spreading it across the sky.', hu: 'Az ég azért kék, mert a levegő a Nap kék fényét szórja szét legjobban, így az terül szét az égen.' },
  { topic: 'virus', keywords: ['virus', 'vírus', 'virus ', 'fertőz', 'infection'], en: 'A virus is a tiny particle that can only multiply inside a living cell, sometimes causing illness; vaccines train the body to fight it.', hu: 'A vírus egy apró részecske, amely csak élő sejtben tud szaporodni, és olykor betegséget okoz; az oltások felkészítik a testet ellene.' },
  { topic: 'brain-organ', keywords: ['the brain', 'human brain', 'az agy', 'agyunk', 'neuron'], en: 'The brain is the control centre of the body. It is made of billions of neurons that pass signals to think, feel, move and remember.', hu: 'Az agy a test vezérlőközpontja. Több milliárd neuronból áll, amelyek jeleket adnak át a gondolkodáshoz, érzéshez, mozgáshoz és emlékezéshez.' },
  { topic: 'rain-cause', keywords: ['why does it rain', 'how does rain', 'miért esik', 'hogyan keletkezik az eső', 'water cycle', 'vízkörforgás'], en: 'Rain forms when the Sun evaporates water, the vapour rises and cools into clouds, and the droplets grow heavy enough to fall.', hu: 'Az eső úgy keletkezik, hogy a Nap elpárologtatja a vizet, a pára felszáll és felhővé hűl, a cseppek pedig elég nehézzé válnak, hogy lehulljanak.' },
  { topic: 'pi', keywords: ['what is pi', 'mi a pi', 'pi szám', 'circle ratio'], en: 'Pi is the ratio of a circle’s circumference to its diameter, about 3.14159 — the same for every circle.', hu: 'A pi egy kör kerületének és átmérőjének aránya, körülbelül 3,14159 — minden körnél ugyanaz.' },
  // ── everyday technology ─────────────────────────────────────────────────────
  { topic: 'wifi', keywords: ['wifi', 'wi-fi', 'wireless', 'vezeték nélküli'], en: 'Wi-Fi connects devices to the internet using radio waves, so they can go online without cables.', hu: 'A Wi-Fi rádióhullámokkal köti az eszközöket az internethez, így kábel nélkül lehetnek online.' },
  { topic: 'bluetooth', keywords: ['bluetooth'], en: 'Bluetooth is a short-range wireless link that connects nearby devices, like headphones to a phone.', hu: 'A Bluetooth egy rövid hatótávú vezeték nélküli kapcsolat, amely közeli eszközöket köt össze, például fülhallgatót a telefonnal.' },
  { topic: 'browser', keywords: ['browser', 'böngésző', 'bongeszo', 'chrome', 'firefox'], en: 'A web browser is an app that loads and shows websites, such as Chrome, Firefox, Safari or Edge.', hu: 'A webböngésző egy alkalmazás, amely weboldalakat tölt be és jelenít meg, például a Chrome, a Firefox, a Safari vagy az Edge.' },
  { topic: 'cloud', keywords: ['cloud computing', 'felhő', 'felho', 'the cloud'], en: 'The cloud means storing data and running programs on remote servers over the internet, instead of only on your own device.', hu: 'A felhő azt jelenti, hogy az adatokat távoli szervereken tároljuk és a programokat ott futtatjuk az interneten át, nem csak a saját eszközünkön.' },
  { topic: 'database', keywords: ['database', 'adatbázis', 'adatbazis'], en: 'A database stores information in an organised way so programs can quickly find, add and update it; SQL is a common query language.', hu: 'Az adatbázis rendezetten tárolja az adatokat, hogy a programok gyorsan megtalálják, hozzáadják és frissítsék; az SQL gyakori lekérdező nyelv.' },
  // ── practical how-to ──────────────────────────────────────────────────────────
  { topic: 'learn-language', keywords: ['learn a language', 'nyelvet tanul', 'how to learn english', 'angolul tanul'], en: 'To learn a language, practise a little every day, learn the most common words first, and use it by listening, reading and speaking.', hu: 'Egy nyelv tanulásához gyakorolj naponta egy keveset, előbb a leggyakoribb szavakat tanuld, és használd hallgatással, olvasással és beszéddel.' },
  { topic: 'lose-weight', keywords: ['lose weight', 'fogyni', 'fogyás', 'diet', 'diéta'], en: 'Healthy weight loss comes from eating a bit less, choosing whole foods, moving more, and being patient — slow and steady lasts.', hu: 'Az egészséges fogyás abból fakad, hogy kicsit kevesebbet eszel, teljes értékű ételt választasz, többet mozogsz, és türelmes vagy — a lassú, kitartó út marad meg.' },

  // ── programming technologies (the ones the user wants Auri to know) ──────────
  { topic: 'python', keywords: ['python', 'pythont', 'pip ', 'django', 'flask'], en: 'Python is a popular, readable programming language used for scripting, web backends, data science and AI. You run code with the python command and install packages with pip; Django and Flask are common web frameworks.', hu: 'A Python népszerű, jól olvasható programozási nyelv, amit szkriptelésre, webes backendre, adattudományra és MI-re használnak. A python paranccsal futtatod, csomagokat pip-pel telepítesz; a Django és a Flask gyakori webes keretrendszer.' },
  { topic: 'java-lang', keywords: ['java ', 'javat', 'jdk', 'jvm', 'spring boot'], en: 'Java is an object-oriented language that runs on the JVM, used for enterprise backends and Android. Code lives in classes; Maven or Gradle build it, and Spring is the most popular framework.', hu: 'A Java objektumorientált nyelv, amely a JVM-en fut; vállalati backendekhez és Androidhoz használják. A kód osztályokban él; a Maven vagy a Gradle építi, és a Spring a legnépszerűbb keretrendszer.' },
  { topic: 'kotlin', keywords: ['kotlin', 'kotlint', 'jetbrains'], en: 'Kotlin is a modern language from JetBrains that runs on the JVM and is the preferred language for Android apps. It is concise, null-safe and fully interoperable with Java.', hu: 'A Kotlin a JetBrains modern nyelve, amely a JVM-en fut, és az Android-appok elsődleges nyelve. Tömör, null-biztos, és teljesen együttműködik a Javával.' },
  { topic: 'php', keywords: ['php', 'php-t', 'laravel', 'composer'], en: 'PHP is a server-side language that powers much of the web, including WordPress. It runs on the server to build pages and APIs; Laravel is a popular modern framework and Composer manages packages.', hu: 'A PHP szerveroldali nyelv, amely a web nagy részét hajtja, például a WordPress-t. A szerveren fut, oldalakat és API-kat épít; a Laravel népszerű modern keretrendszer, a Composer kezeli a csomagokat.' },
  { topic: 'phpmyadmin', keywords: ['phpmyadmin', 'php my admin'], en: 'phpMyAdmin is a free web tool, written in PHP, for managing MySQL or MariaDB databases in the browser: you can run SQL, browse tables, and edit rows without the command line.', hu: 'A phpMyAdmin egy ingyenes, PHP-ban írt webes eszköz MySQL vagy MariaDB adatbázisok böngészőből való kezelésére: SQL-t futtathatsz, táblákat böngészhetsz és sorokat szerkeszthetsz parancssor nélkül.' },
  { topic: 'mysql', keywords: ['mysql', 'mariadb'], en: 'MySQL is a widely used open-source relational database. You define tables, then query them with SQL using SELECT, INSERT, UPDATE and DELETE; MariaDB is a compatible fork.', hu: 'A MySQL elterjedt, nyílt forráskódú relációs adatbázis. Táblákat definiálsz, majd SQL-lel kérdezed őket SELECT, INSERT, UPDATE és DELETE utasításokkal; a MariaDB kompatibilis változata.' },
  { topic: 'oracle', keywords: ['oracle', 'oracle db', 'plsql', 'pl/sql'], en: 'Oracle Database is a powerful commercial relational database used by large enterprises. It speaks SQL and adds PL/SQL, a procedural language for stored procedures and triggers.', hu: 'Az Oracle Database erős, kereskedelmi relációs adatbázis, amit nagyvállalatok használnak. SQL-t beszél, és kiegészíti a PL/SQL-lel, egy eljárás-nyelvvel a tárolt eljárásokhoz és triggerekhez.' },
  { topic: 'sql-lang', keywords: ['what is sql', 'mi az sql', 'select from', 'query language'], en: 'SQL is the language for relational databases. SELECT reads rows, INSERT adds them, UPDATE changes them, DELETE removes them, and JOIN combines tables.', hu: 'Az SQL a relációs adatbázisok nyelve. A SELECT sorokat olvas, az INSERT hozzáad, az UPDATE módosít, a DELETE töröl, a JOIN pedig táblákat kapcsol össze.' },
  { topic: 'vite', keywords: ['vite', 'vitejs', 'vite-t'], en: 'Vite is a fast build tool and dev server for modern web apps. It starts instantly, updates the page live as you edit (hot reload), and bundles the app for production with Rollup.', hu: 'A Vite gyors build-eszköz és dev-szerver modern webappokhoz. Azonnal indul, élőben frissíti az oldalt szerkesztés közben (hot reload), és élesre a Rollup-pal csomagolja az appot.' },
  { topic: 'meta', keywords: ['meta company', 'facebook', 'mi az a meta'], en: 'Meta is the company behind Facebook, Instagram and WhatsApp, and the maker of major developer tools like React, React Native and the PyTorch AI library.', hu: 'A Meta a Facebook, az Instagram és a WhatsApp mögött álló cég, és olyan fejlesztői eszközök készítője, mint a React, a React Native és a PyTorch MI-könyvtár.' },
  { topic: 'nodejs', keywords: ['node', 'nodejs', 'node.js', 'node-ot'], en: 'Node.js runs JavaScript outside the browser, on the server. It is event-driven and non-blocking, great for APIs and tools; npm installs its packages.', hu: 'A Node.js a böngészőn kívül, a szerveren futtat JavaScriptet. Eseményvezérelt és nem-blokkoló, kiváló API-khoz és eszközökhöz; az npm telepíti a csomagjait.' },
  { topic: 'react-lib', keywords: ['react', 'reactot', 'jsx ', 'react hook'], en: 'React is a JavaScript library for building user interfaces from reusable components. State lives in hooks like useState, and the UI updates automatically when the state changes.', hu: 'A React egy JavaScript-könyvtár felhasználói felületek építéséhez újrahasználható komponensekből. Az állapot hookokban él (pl. useState), és a felület magától frissül, ha az állapot változik.' },
  { topic: 'javascript-lang', keywords: ['javascript', 'js nyelv', 'mi az a js', 'ecmascript'], en: 'JavaScript is the programming language of the web. It runs in every browser to make pages interactive, and on servers via Node.js. Variables use let and const, and async/await handles waiting.', hu: 'A JavaScript a web programozási nyelve. Minden böngészőben fut, hogy interaktívvá tegye az oldalakat, és a Node.js-en keresztül szervereken is. A változók let és const, az async/await pedig a várakozást kezeli.' },

  // ── what goes with what (combinations / stacks) ──────────────────────────────
  { topic: 'react-stack', keywords: ['works with react', 'react stack', 'react ecosystem', 'mi megy a react', 'react mellé'], en: 'React works with JSX and hooks for the UI, React Router for pages, Redux or Zustand for shared state, Vite to build it, and a Node backend with an API.', hu: 'A React JSX-szel és hookokkal építi a felületet, React Routerrel az oldalakhoz, Redux vagy Zustand a közös állapothoz, Vite-tal épül, és egy Node backend ad hozzá API-t.' },
  { topic: 'node-stack', keywords: ['works with node', 'use with node', 'node stack', 'mi megy a node', 'node mellé'], en: 'Node.js works with Express for routes, npm for packages, JWT for auth, and a database like MySQL or PostgreSQL through an ORM such as Prisma or Sequelize.', hu: 'A Node.js az Express-szel megy az útvonalakhoz, az npm a csomagokhoz, a JWT a hitelesítéshez, és egy adatbázis (MySQL, PostgreSQL) egy ORM-en (Prisma, Sequelize) keresztül.' },
  { topic: 'php-stack', keywords: ['works with php', 'php stack', 'database for php', 'with php', 'php and mysql', 'php mellé', 'php adatbázis'], en: 'PHP works with MySQL or MariaDB through PDO, Laravel as the framework, Composer for packages, and phpMyAdmin to manage the database.', hu: 'A PHP MySQL-lel vagy MariaDB-vel megy PDO-n át, a Laravel a keretrendszere, a Composer a csomagokhoz, a phpMyAdmin pedig az adatbázis kezeléséhez.' },
  { topic: 'python-stack', keywords: ['works with python', 'python stack', 'mi megy a python', 'python mellé'], en: 'Python works with pip for packages, Django or Flask for web, pandas and NumPy for data, and PyTorch or TensorFlow for AI.', hu: 'A Python pip-pel megy a csomagokhoz, Django vagy Flask a webhez, pandas és NumPy az adathoz, PyTorch vagy TensorFlow az MI-hez.' },
  { topic: 'web-stack', keywords: ['web stack', 'full stack', 'stack for a web', 'what stack', 'milyen stack', 'webalkalmazás stack'], en: 'A full-stack web app has a frontend (HTML, CSS, JavaScript, React), a backend (Node, PHP, Python or Java) and a database (MySQL, PostgreSQL or Oracle).', hu: 'Egy full-stack webapp frontendből (HTML, CSS, JavaScript, React), backendből (Node, PHP, Python, Java) és adatbázisból (MySQL, PostgreSQL, Oracle) áll.' },
  { topic: 'mern-lamp', keywords: ['mern', 'lamp stack', 'lamp ', 'mern stack'], en: 'The MERN stack is MongoDB, Express, React and Node. The LAMP stack is Linux, Apache, MySQL and PHP.', hu: 'A MERN stack: MongoDB, Express, React, Node. A LAMP stack: Linux, Apache, MySQL, PHP.' },
  { topic: 'java-stack', keywords: ['works with java', 'java stack', 'spring stack', 'java mellé'], en: 'Java runs on the JVM, builds with Maven or Gradle, uses Spring as the framework, and connects to databases with JPA or Hibernate.', hu: 'A Java a JVM-en fut, Maven vagy Gradle építi, a Spring a keretrendszere, és JPA vagy Hibernate köti az adatbázishoz.' },
  { topic: 'orm', keywords: ['what is an orm', 'orm ', 'prisma', 'sequelize', 'hibernate', 'mi az orm'], en: 'An ORM (like Prisma, Sequelize, Hibernate or JPA) maps database tables to objects, so your code queries data without writing raw SQL.', hu: 'Az ORM (pl. Prisma, Sequelize, Hibernate, JPA) az adatbázis-táblákat objektumokká képezi le, így a kód nyers SQL nélkül kérdezi le az adatot.' },

  // ── DevOps / tooling ─────────────────────────────────────────────────────────
  { topic: 'docker', keywords: ['docker', 'dockert', 'container ', 'konténer', 'kontener'], en: 'Docker packages an app and its dependencies into a container — a lightweight, portable box that runs the same on any machine. A Dockerfile builds the image.', hu: 'A Docker egy konténerbe csomagolja az appot és a függőségeit — könnyű, hordozható dobozba, ami minden gépen ugyanúgy fut. A Dockerfile építi az image-et.' },
  { topic: 'kubernetes', keywords: ['kubernetes', 'k8s', 'orchestrat'], en: 'Kubernetes runs and scales many containers across a cluster of machines, restarting failed ones and balancing load automatically.', hu: 'A Kubernetes konténerek sokaságát futtatja és skálázza gépek fürtjén, újraindítja a hibásakat, és automatikusan elosztja a terhelést.' },
  { topic: 'git-vcs', keywords: ['git ', 'github', 'commit', 'merge', 'branch', 'verziókezel'], en: 'Git is a version-control system that tracks code changes as commits on branches; you push to a remote like GitHub and merge branches with pull requests.', hu: 'A Git verziókövető rendszer, amely commitokként követi a kód változásait ágakon; egy távolira (pl. GitHub) pusholsz, és pull requesttel olvasztod össze az ágakat.' },
  { topic: 'cicd', keywords: ['ci/cd', 'cicd', 'continuous integration', 'pipeline', 'deployment'], en: 'CI/CD automates building, testing and deploying code: every push runs the tests (CI) and, if they pass, ships the app (CD) to the server.', hu: 'A CI/CD automatizálja a build-et, tesztet és telepítést: minden push lefuttatja a teszteket (CI), és ha átmennek, kiszállítja az appot (CD) a szerverre.' },
  // ── mobile ────────────────────────────────────────────────────────────────────
  { topic: 'android', keywords: ['android', 'androidot', 'android studio'], en: 'Android is Google’s mobile operating system. Apps are written in Kotlin or Java in Android Studio, or cross-platform with React Native or Flutter.', hu: 'Az Android a Google mobil operációs rendszere. Az appok Kotlinban vagy Javában készülnek az Android Studióban, vagy több platformra React Native-tal/Flutterrel.' },
  { topic: 'ios', keywords: ['ios ', 'iphone', 'swift', 'swiftui'], en: 'iOS is Apple’s mobile system. Native apps are written in Swift with SwiftUI or UIKit in Xcode; React Native and Flutter also target iOS.', hu: 'Az iOS az Apple mobil rendszere. A natív appok Swiftben készülnek SwiftUI-jal vagy UIKittel az Xcode-ban; a React Native és a Flutter is céloz iOS-t.' },
  { topic: 'flutter', keywords: ['flutter', 'dart '], en: 'Flutter is Google’s toolkit for building Android and iOS apps from one codebase, written in the Dart language with its own fast UI rendering.', hu: 'A Flutter a Google eszközkészlete Android- és iOS-appok egy kódbázisból való építéséhez, Dart nyelven, saját gyors UI-megjelenítéssel.' },
  // ── AI / ML ─────────────────────────────────────────────────────────────────
  { topic: 'machine-learning', keywords: ['machine learning', 'gépi tanulás', 'gepi tanulas', 'ml '], en: 'Machine learning is software that learns patterns from data instead of being explicitly programmed. You train a model on examples, then use it to predict.', hu: 'A gépi tanulás olyan szoftver, amely adatból tanul mintázatokat, ahelyett hogy explicit programoznák. Egy modellt példákon tanítasz, majd jóslásra használod.' },
  { topic: 'neural-network', keywords: ['neural network', 'neurális háló', 'neuralis halo', 'deep learning', 'mély tanulás'], en: 'A neural network is layers of simple units (neurons) with weighted connections. Training adjusts the weights so the network maps inputs to the right outputs.', hu: 'A neurális háló egyszerű egységek (neuronok) rétegeiből áll, súlyozott kapcsolatokkal. A tanítás úgy állítja a súlyokat, hogy a háló a bemenetet a helyes kimenetre képezze.' },
  { topic: 'llm', keywords: ['large language model', 'llm', 'gpt', 'chatgpt', 'nyelvi modell'], en: 'A large language model (LLM) like GPT is a neural network trained on huge amounts of text to predict the next word, which lets it answer and write fluently.', hu: 'A nagy nyelvi modell (LLM), mint a GPT, hatalmas szövegen tanított neurális háló, amely a következő szót jósolja, így folyékonyan válaszol és ír.' },
  // ── networking ────────────────────────────────────────────────────────────────
  { topic: 'http', keywords: ['http ', 'https', 'request response', 'get post'], en: 'HTTP is the protocol browsers use to talk to servers: the client sends a request (GET, POST…) and the server returns a response with a status code. HTTPS encrypts it.', hu: 'A HTTP az a protokoll, amivel a böngészők a szerverekkel beszélnek: a kliens kérést küld (GET, POST…), a szerver pedig választ ad státuszkóddal. A HTTPS titkosítja.' },
  { topic: 'dns', keywords: ['dns', 'domain name', 'domain név'], en: 'DNS is the internet’s phone book: it turns a human domain name like example.com into the numeric IP address of the server.', hu: 'A DNS az internet telefonkönyve: egy ember által olvasható domain nevet (pl. example.com) a szerver számszerű IP-címévé alakít.' },
  { topic: 'rest-api', keywords: ['rest api', 'restful', 'web api', 'endpoint'], en: 'A REST API exposes data over HTTP at URLs (endpoints): GET reads, POST creates, PUT updates and DELETE removes, usually exchanging JSON.', hu: 'A REST API HTTP-n keresztül tesz elérhetővé adatot URL-eken (végpontokon): GET olvas, POST létrehoz, PUT módosít, DELETE töröl, általában JSON-t cserélve.' },
  // ── security ────────────────────────────────────────────────────────────────
  { topic: 'encryption', keywords: ['encryption', 'titkosítás', 'titkositas', 'encrypt'], en: 'Encryption scrambles data with a key so only someone with the right key can read it. HTTPS uses it to protect data sent over the internet.', hu: 'A titkosítás kulccsal kódolja az adatot, így csak a megfelelő kulccsal rendelkező olvashatja. A HTTPS ezzel védi az interneten küldött adatot.' },
  { topic: 'authentication', keywords: ['authentication', 'hitelesítés', 'hitelesites', 'login', 'jelszó', 'jelszo', 'password'], en: 'Authentication proves who a user is, usually with a password (stored hashed, never plain) and often a token like JWT issued at login and checked on each request.', hu: 'A hitelesítés igazolja, ki a felhasználó, általában jelszóval (hash-elve tárolva, sosem nyersen) és gyakran egy tokennel (pl. JWT), amit belépéskor ad ki és minden kérésnél ellenőriz.' },
  // ── data formats ──────────────────────────────────────────────────────────────
  { topic: 'json', keywords: ['json', 'mi az a json'], en: 'JSON is a simple text format for data, made of key–value pairs and lists. It is how web APIs usually send data between a server and the browser.', hu: 'A JSON egyszerű szöveges adatformátum kulcs–érték párokból és listákból. A webes API-k általában így küldenek adatot a szerver és a böngésző között.' },
  { topic: 'regex', keywords: ['regex', 'regular expression', 'reguláris kifejezés'], en: 'A regular expression (regex) is a pattern for matching text — for example to validate an email or find all numbers in a string.', hu: 'A reguláris kifejezés (regex) szövegmintázat illesztésre — például email-cím ellenőrzésére vagy az összes szám megtalálására egy szövegben.' },
  // ── programming-languages pack (seed v17): basics, HTML/CSS, TS, C, C++, C#, .NET 10,
  //    WPF, MAUI, MUI, Go, Rust, Linux, Bash, Windows, PowerShell, WSL, VPN, WPS ──────
  ...LANG_KNOWLEDGE,
  // ── CSS + visual design pack (seed v18): layout, modern CSS, typography, colour,
  //    accessibility, UI patterns, design systems, effects ──────────────────────
  ...DESIGN_KNOWLEDGE,
];

/** Lowercase + strip diacritics so accented/suffixed HU forms still match. */
const fold = (s: string): string => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');

const isWordChar = (c: string | undefined): boolean => c !== undefined && /[a-z0-9]/.test(c);

/**
 * Score one folded keyword against the space-padded, folded query (0 = no valid hit).
 * The keyword must START a word ("vagy" never hits "agy", "brain" never hits "rain"),
 * but may take a Hungarian suffix ("víz" → "vízben", "vulkán" → "vulkánokról"). Short
 * stems (≤ 4 letters) take at most a 3-letter suffix ("kód" → "kódot", not "kódommal"),
 * and a phrase ending in a short word must end exactly ("ki vagy" ≠ "ki vagyok").
 */
function keywordScore(q: string, kf: string): number {
  const t = kf.trim();
  if (!t) return 0;
  const phrase = t.includes(' ');
  const lastWordLen = t.length - t.lastIndexOf(' ') - 1;
  for (let i = q.indexOf(kf); i >= 0; i = q.indexOf(kf, i + 1)) {
    if (isWordChar(kf[0]) && isWordChar(q[i - 1])) continue; // buried mid-word → not a hit
    if (isWordChar(kf[kf.length - 1]) && lastWordLen <= 4) {
      let rest = 0;
      while (isWordChar(q[i + kf.length + rest])) rest++;
      if (rest > (phrase ? 0 : 3)) continue;
    }
    // phrases > long specific words > content words > fragments
    return phrase ? 4 : t.length >= 6 ? 3 : t.length >= 3 ? 2 : 1;
  }
  return 0;
}

// Words that carry no topic (HU + EN function and question words) — ignored when we
// check whether a bare query is entirely about one topic.
const NO_TOPIC = new Set(
  (
    'a az egy es is de hogy nem mi mit mik ki kik ez ezt azt ezek azok en te o ti ok van vannak volt ' +
    'vagy vagyok vagyunk vagytok lesz meg mar csak tud tudsz tudod jo jol kerlek szia nekem neked ' +
    'miert hogyan mikor hol milyen melyik mennyi hany ' +
    'the an are was were be of to in on at for and or but not it this that do does did can you your ' +
    'me my we they please so why how what who where which when'
  ).split(/\s+/),
);

// Tasks, comparisons, troubleshooting and real-time questions need a model (or live
// data) — a canned definition would be a wrong answer there.
const NEEDS_MODEL =
  /\b(irj|irjal|ird|keszits|keszitsd|csinalj|csinald|generalj|javits|javitsd|segits|oldd meg|refaktor\w*|kulonbseg\w*|osszehasonlit\w*|vs|versus|hiba\w*|baj|nem mukodik|nem megy|ma|mai|most|holnap|tegnap|write|create|build|make|fix|debug|implement|generate|refactor|difference|compare|error|bug|broken|today|now|tomorrow|yesterday|latest)\b/;

// A definition / "tell me about X" question — what this knowledge base actually answers.
const ASKS_ABOUT =
  /^(mi|mik|ki|kik|mit|melyik|milyen|hol|hany|mennyi|mikor|what|who|where|which|when)\b|\b(mi az|mi a|mit jelent|mit tudsz|meselj|magyarazd|ismertesd|hogyan mukodik|hogy mukodik|mire valo|tell me about|explain|define|describe|what is|what are|how does .{1,40} work)\b/;

/** Is the (folded) query really asking ABOUT this entry's topic? */
function asksAbout(fq: string, e: KnowledgeEntry): boolean {
  if (NEEDS_MODEL.test(fq)) return false;
  if (ASKS_ABOUT.test(fq)) return true;
  // A bare topic ("víz?", "python", "a Föld"): every content word must belong to the topic.
  const words = (fq.match(/[a-z0-9]+/g) ?? []).filter((w) => w.length >= 2 && !NO_TOPIC.has(w));
  return (
    words.length > 0 &&
    words.length <= 3 &&
    words.every((w) => e.keywords.some((k) => keywordScore(` ${w} `, fold(k)) > 0))
  );
}

/**
 * Find the best clean answer for a query in the given language (fallback: EN).
 * Returns null unless the match is real (word-start keywords) AND the query asks about
 * the topic — so the caller falls through to recall / web / the model instead of
 * answering "ki vagy?" with the human body or "…brain…" with the weather.
 */
export function findKnowledge(query: string, lang: 'hu' | 'en' | 'de' | 'unknown' = 'en'): string | null {
  // "C#" → csharp, "C++" → cpp, ".NET" → dotnet BEFORE scoring (symbols would be lost);
  // matching itself stays word-start only (keywordScore).
  const fq = fold(expandTechAliases(query));
  // A task / comparison / error / real-time question never gets a canned definition —
  // not even on an exact phrase hit ("írj egy reszponzív css grid oldalt" → the model).
  if (NEEDS_MODEL.test(fq)) return null;
  const q = ` ${fq} `;
  const scored: { e: KnowledgeEntry; score: number; hasPhrase: boolean }[] = [];
  for (const e of KNOWLEDGE) {
    let score = 0;
    let hasPhrase = false;
    // Dedupe folded keywords so redundant accented/unaccented variants don't double-count.
    for (const kf of new Set(e.keywords.map(fold))) {
      const s = keywordScore(q, kf);
      score += s;
      if (s > 0 && kf.trim().includes(' ')) hasPhrase = true;
    }
    if (score >= 2) scored.push({ e, score, hasPhrase });
  }
  // Best first (stable: on a tie the earlier entry wins, as before) — and the first
  // candidate that really answers the question wins, so a rejected look-alike
  // ("fordító" = translator) gives way to the right one ("fordítóprogram" = compiler).
  scored.sort((a, b) => b.score - a.score);
  for (const { e, hasPhrase } of scored) {
    // An exact phrase ("miért kék az ég", "ki vagy") is strong enough on its own.
    if (!hasPhrase && !asksAbout(fq, e)) continue;
    // RELEVANCE GATE: the entry must be about EVERY topic of the question — "who is the
    // president of france" is not answered by the France definition, nor "what is a
    // closure in rust" by the Rust intro (→ the model answers instead).
    if (!coversQuery(query, e.topic.replace(/-/g, ' '), e.keywords.join(' '), e.en, e.hu)) continue;
    return lang === 'hu' ? e.hu : e.en;
  }
  return null;
}

/** All answer sentences (both languages) for seeding the learner's vocab/graph. */
export const KNOWLEDGE_TEXT: string[] = KNOWLEDGE.flatMap((e) => [e.en, e.hu]);

/** Representative Q→A turns (EN) so the Answering region also learns the mapping. */
export const KNOWLEDGE_QA: [string, string][] = KNOWLEDGE.map((e) => [`what is ${e.topic.replace(/-/g, ' ')}`, e.en]);
