# Solidity
<!-- tech: solidity -->
<!-- aliases: ethereum, evm, smart contract -->

A Solidity statikusan típusos, kontraktus-orientált nyelv okosszerződések (smart contract) írására az
Ethereum Virtual Machine-re (EVM) és a kompatibilis láncokra (L2-k, sidechainek). A lefordított bytecode
a blokkláncon fut, minden művelet gas-ba kerül, az állapot (storage) írása különösen drága, a telepített
kód pedig alapból megváltoztathatatlan. Fő elemei: állapotváltozók, függvények láthatósággal,
modifierek, események, öröklődés, interfészek és egyedi hibák; 0.8-tól az aritmetika alapból
túlcsordulás-ellenőrzött. Pénzügyi logikánál a biztonság az elsődleges: reentrancy, hozzáférés-kezelés,
oracle-manipuláció és frissíthetőség a tipikus kockázatok, ezért auditált könyvtárakra (OpenZeppelin)
és alapos tesztelésre (Foundry, fuzzing) kell építeni. Nagy számításra vagy titkos adatra nem való:
minden adat publikus és minden lépés fizetős.

## Szerződés felépítése, láthatóság és egyedi hibák
<!-- q: Hogyan épül fel egy Solidity szerződés, és mit jelentenek a láthatósági és mutability kulcsszavak? -->
<!-- tags: contract, visibility, external, public, internal, private, view, pure, payable, immutable, custom errors -->

Egy szerződés állapotváltozókból (a láncon tárolt storage), konstruktorból, függvényekből, eseményekből
és hibatípusokból áll. A láthatóság: external (csak kívülről), public (kívülről és belülről, állapotváltozónál
automatikus getter), internal (a szerződés és leszármazottai), private (csak a szerződés, de a láncon
ettől még mindenki olvashatja az értéket!). A view csak olvas, a pure semmit nem ér el az állapotból, a
payable fogadhat ETH-t; az immutable a konstruktorban egyszer állítható és a bytecode-ba kerül, a constant
fordítási időben ismert. Az egyedi hibák (error) olcsóbbak a revert stringnél, és paramétert is hordoznak.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title Letéti (escrow) szerződés: a vevő letétbe helyez, majd kiadja vagy visszakéri
contract Escrow {
    address public immutable buyer;           // konstruktorban beállítva, bytecode-ba égetve
    address public immutable seller;
    uint256 public constant TIMEOUT = 7 days; // fordítási idejű konstans, nincs storage
    uint256 public deadline;

    enum State { AwaitingPayment, Funded, Released, Refunded }
    State public state;                       // public -> automatikus getter

    error InvalidState(State expected, State actual);
    error Unauthorized(address caller);
    error TooEarly(uint256 deadline);
    error ZeroDeposit();

    constructor(address seller_) {
        buyer = msg.sender;
        seller = seller_;
    }

    // external + payable: kívülről hívható és ETH-t fogad
    function deposit() external payable {
        if (msg.sender != buyer) revert Unauthorized(msg.sender);
        if (state != State.AwaitingPayment) revert InvalidState(State.AwaitingPayment, state);
        if (msg.value == 0) revert ZeroDeposit();
        state = State.Funded;
        deadline = block.timestamp + TIMEOUT;
    }

    function release() external {
        if (msg.sender != buyer) revert Unauthorized(msg.sender);
        _settle(State.Released, seller);
    }

    function refund() external {
        if (msg.sender != buyer) revert Unauthorized(msg.sender);
        if (block.timestamp < deadline) revert TooEarly(deadline);
        _settle(State.Refunded, buyer);
    }

    // view: csak olvas
    function balance() external view returns (uint256) {
        return address(this).balance;
    }

    // private: csak ez a szerződés hívhatja (de az adatok a láncon publikusak!)
    function _settle(State next, address to) private {
        if (state != State.Funded) revert InvalidState(State.Funded, state);
        state = next;                                         // előbb az állapot (CEI)
        (bool ok, ) = payable(to).call{value: address(this).balance}("");
        require(ok, "ETH transfer failed");
    }
}
```

## Adattárolási helyek: storage, memory, calldata
<!-- q: Mi a különbség a storage, memory és calldata között Solidityben, és miért nem mentődik a módosításom? -->
<!-- tags: storage, memory, calldata, data location, reference types, struct, mapping, transient storage -->

A referenciatípusoknál (tömb, struct, string, bytes) mindig meg kell adni az adat helyét: a storage a
szerződés tartós állapota a láncon (írása 20 000 gas körül is lehet), a memory ideiglenes, a hívás végén
eltűnik, a calldata pedig a bemeneti adat csak olvasható, másolás nélküli nézete, ezért external
paraméterekhez a legolcsóbb. Egy storage változót storage referenciába téve az írás a láncon marad,
memory változóba másolva viszont a módosítás csak a másolaton történik, ami gyakori, csendes hiba. A
storage-olvasást (SLOAD) ciklus előtt érdemes lokális változóba gyűjteni. A 0.8.28-tól a transient
kulcsszó a tranzakció végéig élő, olcsó tárolást ad (például reentrancy-zárhoz).

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract DataLocations {
    struct Order {
        address owner;     // 20 bájt
        uint96 amount;     // 12 bájt -> a kettő együtt egy 32 bájtos slot
        uint64[] items;    // dinamikus tömb: külön slotokban
    }

    mapping(uint256 => Order) private orders;

    // calldata: csak olvasható, nincs másolás -> legolcsóbb external paraméter
    function create(uint256 id, uint64[] calldata items) external {
        Order storage o = orders[id];   // storage REFERENCIA: minden írás a láncra kerül
        o.owner = msg.sender;
        o.amount = uint96(items.length);
        o.items = items;                // calldata -> storage másolás (elemenként írás)
    }

    // memory: teljes másolat; a módosítás nem érinti a storage-ot
    function preview(uint256 id) external view returns (Order memory copy) {
        copy = orders[id];              // storage -> memory másolás (nagy tömbnél drága)
        copy.amount = 0;                // csak a visszaadott másolat változik
    }

    // BUKTATÓ: memory másolaton végzett módosítás elvész
    function buggyBump(uint256 id) external {
        Order memory o = orders[id];
        o.amount += 1;                  // HATÁSTALAN a tárolt adatra!
    }

    function bump(uint256 id) external {
        Order storage o = orders[id];
        o.amount += 1;                  // ez valóban ír
    }

    // Storage-olvasás cache-elése: a hossz egyszer kerül beolvasásra
    function total(uint256 id) external view returns (uint256 sum) {
        uint64[] storage items = orders[id].items;
        uint256 len = items.length;
        for (uint256 i; i < len; ++i) {
            sum += items[i];
        }
    }
}
```

## Gas-optimalizálás
<!-- q: Hogyan csökkentsem egy Solidity szerződés gas-költségét? -->
<!-- tags: gas optimization, storage packing, immutable, constant, unchecked, sload, sstore, calldata -->

A gas-költség döntő része a storage-ból jön: egy hideg SLOAD 2100, egy új érték írása (SSTORE nulláról)
kb. 22 100 gas, míg egy aritmetikai művelet 3-5. Ezért a legfontosabb minták: kis típusok egy 32 bájtos
slotba pakolása, immutable/constant használata, storage-értékek cache-elése lokális változóba, és a
ciklusban felhalmozott eredmény egyszeri visszaírása. Az unchecked blokk kikapcsolja a túlcsordulás-
ellenőrzést, de csak akkor használd, ha egy korábbi feltétel bizonyítja, hogy nem csordulhat túl; a
0.8.22-es fordítótól az egyszerű ciklusváltozó-növelés ezt magától megkapja. Az olvashatóságot és a
biztonságot soha ne áldozd fel néhány gas kedvéért, és mindig mérj (forge snapshot).

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract GasPatterns {
    // 1) Slot-pakolás: 16 + 8 + 4 + 1 = 29 bájt -> egyetlen 32 bájtos slot
    struct Position {
        uint128 size;
        uint64 openedAt;
        uint32 leverage;
        bool isLong;
    }
    mapping(address => Position) public positions;

    // 2) immutable / constant: nincs SLOAD, az érték a bytecode-ban van
    address public immutable treasury;
    uint256 public constant FEE_BPS = 30;

    uint256 public totalVolume;

    constructor(address treasury_) {
        treasury = treasury_;
    }

    // 3) Egy struct literál = egyetlen slot írása, nem négy külön SSTORE
    function open(uint128 size, uint32 leverage, bool isLong) external {
        positions[msg.sender] = Position(size, uint64(block.timestamp), leverage, isLong);
        totalVolume += size;
    }

    // 4) Felhalmozás lokális változóban: 1 SLOAD + 1 SSTORE a ciklusonkénti írás helyett
    function addMany(uint128[] calldata sizes) external {
        uint256 acc = totalVolume;
        uint256 len = sizes.length;
        for (uint256 i; i < len; ++i) {     // 0.8.22+: a ++i ellenőrzése automatikusan elmarad
            acc += sizes[i];
        }
        totalVolume = acc;
    }

    // 5) unchecked csak bizonyítottan biztonságos helyen
    function fee(uint256 amount) public pure returns (uint256 net, uint256 cut) {
        cut = amount * FEE_BPS / 10_000;    // cut <= amount mindig igaz
        unchecked { net = amount - cut; }   // ezért alulcsordulás nem lehetséges
    }

    // 6) Nullázás: gas-visszatérítést (refund) ad
    function close() external {
        delete positions[msg.sender];
    }
}
```

## Események (events) és indexelt mezők
<!-- q: Mire valók az események Solidityben, és mikor tegyek egy mezőt indexed-dé? -->
<!-- tags: events, emit, indexed, logs, topics, off-chain indexing, the graph -->

Az esemény a tranzakció logjába írt adat: sokkal olcsóbb a storage-nál, de szerződésből nem olvasható
vissza, kizárólag a láncon kívüli világ (dApp frontend, indexer, The Graph, monitoring) számára készül.
Legfeljebb három paraméter lehet indexed: ezek topicként kerülnek a logba, így hatékonyan szűrhetők
(például "minden listázás egy adott eladótól"), a többi a data részbe kerül ABI-kódolva. Minden
állapotváltozást érdemes eseménnyel jelezni, mert az off-chain rendszerek ebből építik fel az előzményeket.
Az indexelőnek kezelnie kell a lánc-átrendeződést (reorg): csak megfelelő számú megerősítés után tekintse
véglegesnek az eseményt.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract Marketplace {
    // indexed (max. 3): topicként szűrhető; a price a data részbe kerül
    event Listed(uint256 indexed listingId, address indexed seller, address indexed token, uint256 price);
    event PriceChanged(uint256 indexed listingId, uint256 oldPrice, uint256 newPrice);
    event Cancelled(uint256 indexed listingId);

    struct Listing {
        address seller;
        address token;
        uint256 price;
        bool active;
    }
    mapping(uint256 => Listing) public listings;
    uint256 public nextId;

    error NotSeller();
    error Inactive();

    function list(address token, uint256 price) external returns (uint256 id) {
        id = nextId++;
        listings[id] = Listing(msg.sender, token, price, true);
        emit Listed(id, msg.sender, token, price);
    }

    function changePrice(uint256 id, uint256 newPrice) external {
        Listing storage l = listings[id];
        if (l.seller != msg.sender) revert NotSeller();
        if (!l.active) revert Inactive();
        emit PriceChanged(id, l.price, newPrice);   // a régi értéket az írás előtt naplózzuk
        l.price = newPrice;
    }

    function cancel(uint256 id) external {
        Listing storage l = listings[id];
        if (l.seller != msg.sender) revert NotSeller();
        l.active = false;
        emit Cancelled(id);
    }
}
```

## Modifierek és hibakezelés
<!-- q: Hogyan használjak modifiereket és egyedi hibákat a függvények előfeltételeinek ellenőrzésére? -->
<!-- tags: modifier, revert, require, custom error, onlyOwner, whenNotPaused, error handling -->

A modifier a függvénytörzs köré illesztett újrahasznosítható kód: a _ jelöli, hol fut a függvény, így
előfeltételek (jogosultság, szüneteltetés, paraméter-ellenőrzés) deklaratívan írhatók. Több modifier
balról jobbra fut, és paramétert is kaphat. A modifier kódja minden függvénybe beíródik, ezért nagy
modifier sok helyen használva felfújja a bytecode-ot (24 KiB-os limit); ilyenkor a modifier csak egy
internal függvényt hívjon. Hibajelzésre egyedi error-t használj revert-tel (0.8.26-tól require-rel is),
mert olcsóbb és a kliens dekódolni tudja a paramétereit.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract Vault {
    error NotOwner();
    error Paused();
    error ZeroAmount();
    error Insufficient(uint256 available, uint256 requested);
    error TransferFailed();

    address public owner;
    bool public paused;
    mapping(address => uint256) public balanceOf;

    constructor() {
        owner = msg.sender;
    }

    // A modifier egy internal függvényt hív -> kisebb bytecode sok használatnál
    modifier onlyOwner() {
        _checkOwner();
        _;                               // ide kerül a függvénytörzs
    }
    modifier whenNotPaused() {
        if (paused) revert Paused();
        _;
    }
    modifier nonZero(uint256 amount) {   // paraméteres modifier
        if (amount == 0) revert ZeroAmount();
        _;
    }

    function _checkOwner() internal view {
        if (msg.sender != owner) revert NotOwner();
    }

    function setPaused(bool p) external onlyOwner {
        paused = p;
    }

    function deposit() external payable whenNotPaused nonZero(msg.value) {
        balanceOf[msg.sender] += msg.value;
    }

    // A modifierek balról jobbra futnak
    function withdraw(uint256 amount) external whenNotPaused nonZero(amount) {
        uint256 bal = balanceOf[msg.sender];
        if (bal < amount) revert Insufficient(bal, amount);
        balanceOf[msg.sender] = bal - amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        if (!ok) revert TransferFailed();
    }
}
```

## Öröklődés, interfészek és absztrakt szerződések
<!-- q: Hogyan működik a többszörös öröklődés, a virtual/override és a super Solidityben? -->
<!-- tags: inheritance, interface, abstract contract, virtual, override, super, c3 linearization -->

A Solidity többszörös öröklődést támogat C3 linearizációval: az is után a szülőket a "legalapabbtól" a
"leszármazottabb" felé kell felsorolni, és a super a linearizációban következő szerződést hívja, nem
feltétlenül a közvetlen őst. A felülírható függvény virtual, a felülíró override; ha több ős is definiálja
ugyanazt a függvényt, override(A, B) formában mindet meg kell nevezni. Az interface csak külső
függvény-deklarációkat tartalmaz (más szerződések hívására), az abstract contract részben megvalósított,
nem telepíthető alap. Az ős konstruktorának paramétereit a leszármazott konstruktor fejlécében kell átadni.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IPriceFeed {
    function latestPrice() external view returns (uint256);
}

abstract contract OwnedBase {
    address public owner;
    constructor(address owner_) { owner = owner_; }
    modifier onlyOwner() { require(msg.sender == owner, "not owner"); _; }
}

abstract contract Pausable {
    bool public paused;
    function _pause() internal virtual { paused = true; }
    function describe() public virtual returns (string memory) { return "Pausable"; }
}

abstract contract Logging {
    event Note(string what);
    function describe() public virtual returns (string memory) {
        emit Note("Logging");
        return "Logging";
    }
}

// Linearizáció: Oracle -> Logging -> Pausable -> OwnedBase -> IPriceFeed
contract Oracle is IPriceFeed, OwnedBase, Pausable, Logging {
    uint256 private price;

    constructor(address owner_) OwnedBase(owner_) {}   // ős konstruktor paramétere

    function latestPrice() external view returns (uint256) {
        require(!paused, "paused");
        return price;
    }

    function setPrice(uint256 p) external onlyOwner { price = p; }

    function pause() external onlyOwner { _pause(); }

    // Két ős azonos függvénye: mindkettőt meg kell nevezni
    function describe() public override(Pausable, Logging) returns (string memory) {
        return super.describe();   // a linearizációban következő: Logging.describe
    }

    function _pause() internal override {
        super._pause();            // Pausable._pause
        emit Note("paused");
    }
}
```

## ERC-20 token minta
<!-- q: Hogyan működik egy ERC-20 token, és mire figyeljek az approve/transferFrom mintánál? -->
<!-- tags: erc-20, token, transfer, approve, allowance, transferFrom, decimals, safeerc20 -->

Az ERC-20 a helyettesíthető (fungible) tokenek szabványos interfésze: egyenleg, átutalás, valamint az
approve/transferFrom páros, amellyel egy harmadik fél (például DEX vagy letéti szerződés) a tulajdonos
jóváhagyásával költhet. A decimals csak megjelenítési konvenció, a szerződés mindig a legkisebb egységgel
(10^18-on) számol. Buktatók: a jóváhagyás módosításánál front-running lehetséges, egyes régi tokenek
(például USDT) nem adnak vissza bool-t, mások átutaláskor díjat vonnak le, ezért idegen tokenek kezelésére
az OpenZeppelin SafeERC20 való. Élesben saját implementáció helyett az auditált OpenZeppelin ERC20-at használd;
az alábbi minimális változat a működést mutatja.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// Minimális, oktatási ERC-20 (élesben: OpenZeppelin ERC20)
contract SimpleToken {
    string public constant name = "Example Token";
    string public constant symbol = "EXT";
    uint8 public constant decimals = 18;         // 1 token = 10**18 legkisebb egység
    uint256 public totalSupply;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    error InsufficientBalance(uint256 balance, uint256 needed);
    error InsufficientAllowance(uint256 allowance, uint256 needed);
    error ZeroAddress();

    constructor(uint256 initialSupply) {
        _mint(msg.sender, initialSupply);
    }

    function transfer(address to, uint256 value) external returns (bool) {
        _transfer(msg.sender, to, value);
        return true;
    }

    function approve(address spender, uint256 value) external returns (bool) {
        allowance[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
        return true;
    }

    function transferFrom(address from, address to, uint256 value) external returns (bool) {
        uint256 allowed = allowance[from][msg.sender];
        if (allowed != type(uint256).max) {      // "végtelen" jóváhagyást nem csökkentünk
            if (allowed < value) revert InsufficientAllowance(allowed, value);
            allowance[from][msg.sender] = allowed - value;
        }
        _transfer(from, to, value);
        return true;
    }

    function _transfer(address from, address to, uint256 value) internal {
        if (to == address(0)) revert ZeroAddress();
        uint256 bal = balanceOf[from];
        if (bal < value) revert InsufficientBalance(bal, value);
        unchecked {
            balanceOf[from] = bal - value;       // a fenti ellenőrzés miatt nem csordul alul
            balanceOf[to] += value;              // az összeg <= totalSupply, nem csordul túl
        }
        emit Transfer(from, to, value);
    }

    function _mint(address to, uint256 value) internal {
        if (to == address(0)) revert ZeroAddress();
        totalSupply += value;                    // ellenőrzött: túlcsordulásnál revert
        unchecked { balanceOf[to] += value; }
        emit Transfer(address(0), to, value);
    }
}
```

## ERC-721 NFT minta OpenZeppelinnel
<!-- q: Hogyan készítsek ERC-721 NFT szerződést korlátozott kínálattal és mintelési árral? -->
<!-- tags: erc-721, nft, openzeppelin, safeMint, tokenURI, metadata, onERC721Received -->

Az ERC-721 egyedi, nem helyettesíthető tokeneket ír le: minden tokenId-nak egy tulajdonosa van, és a
metaadat (név, kép, attribútumok) jellemzően láncon kívül, IPFS-en él, a tokenURI ezt a JSON-t címzi. Az
OpenZeppelin ERC721 alaposztálya adja az átutalást, jóváhagyást és a biztonságos átvételi ellenőrzést; a
saját szerződésnek csak a mintelési szabályokat kell megírnia. A _safeMint szerződés címzettnél meghívja
az onERC721Received függvényt, ami reentrancy-pont, ezért minden állapotváltozásnak előtte kell
megtörténnie. A pénzt pull-mintával, külön withdraw függvénnyel vedd ki, ne a mint közben továbbíts.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// Jegy NFT-k: legfeljebb 1000 darab, fix áron mintelhető
contract Tickets is ERC721, Ownable {
    uint256 public constant MAX_SUPPLY = 1000;
    uint256 public constant PRICE = 0.01 ether;
    uint256 private _nextId = 1;
    string private _baseTokenURI;

    error SoldOut();
    error WrongPayment(uint256 sent);
    error WithdrawFailed();

    constructor(string memory baseURI, address initialOwner)
        ERC721("Concert Tickets", "TIX")
        Ownable(initialOwner)
    {
        _baseTokenURI = baseURI;                 // pl. "ipfs://<CID>/"
    }

    function mint() external payable returns (uint256 id) {
        if (msg.value != PRICE) revert WrongPayment(msg.value);
        id = _nextId;
        if (id > MAX_SUPPLY) revert SoldOut();
        _nextId = id + 1;                        // állapot frissítése a külső hívás ELŐTT
        // _safeMint: szerződés címzettnél onERC721Received hívás -> reentrancy-pont
        _safeMint(msg.sender, id);
    }

    // tokenURI = _baseURI() + tokenId (az OpenZeppelin alapimplementációja)
    function _baseURI() internal view override returns (string memory) {
        return _baseTokenURI;
    }

    // Pull-minta: a bevételt a tulajdonos külön veszi ki
    function withdraw(address payable to) external onlyOwner {
        (bool ok, ) = to.call{value: address(this).balance}("");
        if (!ok) revert WithdrawFailed();
    }
}
```

## Reentrancy és a checks-effects-interactions minta
<!-- q: Mi a reentrancy támadás, és hogyan védekezzek ellene Solidityben? -->
<!-- tags: reentrancy, checks-effects-interactions, nonReentrant, reentrancyguard, security, external call -->

Reentrancy akkor történik, ha a szerződés külső hívást indít (ETH küldése, token-hook, idegen szerződés
hívása), mielőtt a saját állapotát frissítené: a hívott fél visszahívhat ugyanabba vagy egy másik
függvénybe, és a még régi állapotot használja ki, például többször kivesz ugyanabból az egyenlegből. A
védekezés alapja a checks-effects-interactions sorrend: előbb ellenőrzés, aztán állapotváltozás, a külső
hívás legutoljára; mélységi védelemként jön a nonReentrant zár. Figyelj a függvények közötti és a
read-only reentrancyre is (egy view függvény átmenetileg hibás értéket ad egy másik protokollnak), és ne
támaszkodj a transfer() 2300 gas-os limitjére, mert a gas-árazás változhat.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

// SEBEZHETŐ: a külső hívás az állapotfrissítés ELŐTT történik
contract VulnerableBank {
    mapping(address => uint256) public balances;

    function deposit() external payable { balances[msg.sender] += msg.value; }

    function withdraw() external {
        uint256 amount = balances[msg.sender];
        (bool ok, ) = msg.sender.call{value: amount}("");  // a támadó itt visszahív
        require(ok, "transfer failed");
        balances[msg.sender] = 0;                          // túl késő
    }
}

// Támadó: a receive() újra meghívja a withdraw-t, amíg van pénz a bankban
contract Attacker {
    VulnerableBank public immutable bank;

    constructor(VulnerableBank b) { bank = b; }

    function attack() external payable {
        bank.deposit{value: msg.value}();
        bank.withdraw();
    }

    receive() external payable {
        if (address(bank).balance >= msg.value) bank.withdraw();
    }
}

// JAVÍTOTT: checks-effects-interactions + ReentrancyGuard
contract SafeBank is ReentrancyGuard {
    mapping(address => uint256) public balances;

    error NothingToWithdraw();
    error TransferFailed();

    function deposit() external payable { balances[msg.sender] += msg.value; }

    function withdraw() external nonReentrant {
        uint256 amount = balances[msg.sender];
        if (amount == 0) revert NothingToWithdraw();        // 1) CHECKS
        balances[msg.sender] = 0;                           // 2) EFFECTS
        (bool ok, ) = msg.sender.call{value: amount}("");   // 3) INTERACTIONS
        if (!ok) revert TransferFailed();
    }
}
```

## Hozzáférés-kezelés: Ownable2Step és AccessControl
<!-- q: Hogyan korlátozzam, ki hívhatja a szerződés adminisztratív függvényeit? -->
<!-- tags: access control, ownable, ownable2step, accesscontrol, roles, multisig, timelock, tx.origin -->

Egyszerű esetben egyetlen tulajdonos (Ownable) elég; a kétlépéses változat (Ownable2Step) esetén az új
tulajdonosnak el kell fogadnia az átadást, így egy elgépelt címre nem vész el a jogosultság. Több
szereplőnél az AccessControl szerepköröket (bytes32 azonosító) és szerepenként több címet kezel, a
DEFAULT_ADMIN_ROLE pedig a szerepek kiosztását végzi, ezért ezt ideálisan multisig vagy timelock birtokolja.
Az admin függvények paramétereit is korlátozd (például maximális díj), hogy egy kompromittált kulcs se
okozhasson korlátlan kárt. Jogosultságot soha ne a tx.origin alapján ellenőrizz, mert egy köztes
(adathalász) szerződésen át megkerülhető.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";

// Szerepkör-alapú hozzáférés
contract Treasury is AccessControl {
    bytes32 public constant PAYER_ROLE = keccak256("PAYER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bool public paused;

    event Paid(address indexed to, uint256 amount);
    error IsPaused();
    error TransferFailed();

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);   // ideálisan multisig vagy timelock
    }

    function pay(address payable to, uint256 amount) external onlyRole(PAYER_ROLE) {
        if (paused) revert IsPaused();
        (bool ok, ) = to.call{value: amount}("");
        if (!ok) revert TransferFailed();
        emit Paid(to, amount);
    }

    function setPaused(bool p) external onlyRole(PAUSER_ROLE) {
        paused = p;
    }

    receive() external payable {}
}

// Egy tulajdonos kétlépéses átadással: transferOwnership(új) -> az új hívja: acceptOwnership()
contract FeeConfig is Ownable2Step {
    uint256 public feeBps;
    error FeeTooHigh(uint256 bps);

    constructor(address owner_) Ownable(owner_) {}

    function setFee(uint256 bps) external onlyOwner {
        if (bps > 1_000) revert FeeTooHigh(bps);   // max. 10%: korlátozza a kulcsvesztés kárát
        feeBps = bps;
    }
    // SOHA: require(tx.origin == owner()); -> köztes szerződéssel megkerülhető
}
```

## Frissíthető szerződések: UUPS proxy
<!-- q: Hogyan tegyem frissíthetővé egy telepített okosszerződés logikáját proxy mintával? -->
<!-- tags: upgradeable, proxy, uups, erc1967, delegatecall, initializer, storage layout, reinitializer -->

A telepített kód nem módosítható, ezért a frissíthetőséget proxy adja: a felhasználók egy állandó című
proxyval beszélnek, amely delegatecall-lal a mindenkori implementáció kódját futtatja a saját storage-án.
Mivel a konstruktor az implementáció storage-ában futna, inicializáló függvény (initializer) kell, az
implementáció konstruktorában pedig _disableInitializers() akadályozza meg, hogy bárki átvegye. UUPS
mintánál a frissítési jogot az implementáció _authorizeUpgrade függvénye ellenőrzi, ha ezt nyitva hagyod,
bárki lecserélheti a logikát. Új verzióban a meglévő állapotváltozók sorrendje és típusa nem változhat,
csak a végére lehet újakat felvenni (az OpenZeppelin 5 ERC-7201 névtérrel csökkenti az ütközés kockázatát).

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Initializable} from "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import {UUPSUpgradeable} from "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import {OwnableUpgradeable} from "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";

/// V1 implementáció. Telepítés: new ERC1967Proxy(address(impl),
///   abi.encodeCall(CounterV1.initialize, (owner)))  -> az inicializálás atomi a telepítéssel
contract CounterV1 is Initializable, OwnableUpgradeable, UUPSUpgradeable {
    uint256 public count;

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();          // az implementációt magát senki ne inicializálhassa
    }

    function initialize(address owner_) external initializer {
        __Ownable_init(owner_);
    }

    function increment() external {
        count += 1;
    }

    // Csak a tulajdonos frissíthet; üresen hagyott jogosultság = bárki frissíthet!
    function _authorizeUpgrade(address) internal override onlyOwner {}
}

/// V2: új állapotváltozó CSAK a meglévők után; a régiek sorrendje és típusa érintetlen
contract CounterV2 is CounterV1 {
    uint256 public step;

    // Frissítés: proxy.upgradeToAndCall(address(new CounterV2()),
    //                                   abi.encodeCall(CounterV2.initializeV2, (5)))
    function initializeV2(uint256 step_) external reinitializer(2) {
        step = step_;
    }

    function incrementBy() external {
        count += step;
    }
}
```

## Tesztelés Foundryval
<!-- q: Hogyan teszteljem a Solidity szerződéseimet Foundryval, fuzz tesztekkel és cheatcode-okkal? -->
<!-- tags: foundry, forge, testing, fuzz testing, cheatcodes, vm.prank, expectRevert, invariant -->

A Foundry (forge) Solidityben írt teszteket futtat gyorsan, helyi EVM-en: a test előtagú függvények
egységtesztek, a paraméteres testFuzz függvényeket a forge sok véletlen bemenettel hívja, az invariáns
tesztek pedig véletlen hívássorozatok után ellenőrzik, hogy egy állítás mindig igaz marad. A vm
cheatcode-okkal manipulálható a környezet: vm.prank a hívót, vm.deal az egyenleget, vm.warp az időt, a
vm.expectRevert pedig a várt hibát. A makeAddr determinisztikus tesztcímet ad, így valódi kulcs vagy
pénzes cím soha nem kell a tesztekbe. Érdemes a támadási forgatókönyveket (például reentrancy) is
tesztként rögzíteni, és a gas-változást forge snapshot-tal követni.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {SafeBank, VulnerableBank, Attacker} from "../src/Banks.sol";

contract BankTest is Test {
    SafeBank bank;
    address alice = makeAddr("alice");        // determinisztikus tesztcím

    function setUp() public {
        bank = new SafeBank();
        vm.deal(alice, 10 ether);              // tesztegyenleg
    }

    function test_DepositAndWithdraw() public {
        vm.startPrank(alice);                  // a következő hívások küldője alice
        bank.deposit{value: 1 ether}();
        bank.withdraw();
        vm.stopPrank();
        assertEq(alice.balance, 10 ether);
        assertEq(bank.balances(alice), 0);
    }

    function test_RevertWhen_NothingToWithdraw() public {
        vm.prank(alice);
        vm.expectRevert(SafeBank.NothingToWithdraw.selector);
        bank.withdraw();
    }

    // Fuzz teszt: a forge sok véletlen amount értékkel futtatja
    function testFuzz_WithdrawReturnsDeposit(uint96 amount) public {
        vm.assume(amount > 0);
        vm.deal(alice, amount);
        vm.startPrank(alice);
        bank.deposit{value: amount}();
        bank.withdraw();
        vm.stopPrank();
        assertEq(alice.balance, amount);
    }

    // A támadás tesztként dokumentálva: a sebezhető bank kiüríthető
    function test_ReentrancyDrainsVulnerableBank() public {
        VulnerableBank vb = new VulnerableBank();
        vm.deal(address(vb), 5 ether);         // mások betéteit szimuláljuk
        Attacker atk = new Attacker(vb);
        vm.deal(address(this), 1 ether);
        atk.attack{value: 1 ether}();
        assertEq(address(vb).balance, 0);
        assertEq(address(atk).balance, 6 ether);
    }
}
```

```bash
forge test -vvv
forge test --match-test testFuzz --fuzz-runs 10000
forge snapshot
forge coverage
```
