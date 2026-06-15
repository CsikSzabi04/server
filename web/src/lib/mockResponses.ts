// Canned "Auri" responses for MOCK mode (no backend). A deliberate mix of short
// and long answers so the length-proportional "stay alive longer" animation is
// visibly demonstrable. HUD-flavored, Hungarian.

const GREETINGS = [
  'Rendszer online. Auri készenlétben — miben segíthetek?',
  'Kapcsolat létrejött. Hallgatlak.',
  'Auri aktív. Add ki a parancsot.',
];

const SHORT = [
  'Vettem. Feldolgozom és jelzek vissza.',
  'Kész. A művelet sikeres.',
  'Megerősítve. Folytatom a monitorozást.',
  'Nincs anomália. Minden rendszer névleges paramétereken belül.',
];

const LONG = [
  `Elemzem a kérést. A bejövő adatfolyamot három rétegben dolgozom fel: először a kontextust normalizálom, majd a releváns mintázatokat emelem ki, végül összegzem a következtetést.

A jelenlegi telemetria alapján minden alrendszer stabil: az energiamag névleges szinten lüktet, a hálózati uplink késleltetése elhanyagolható, és nincs hibajel a perifériákon. Ahogy hosszabb a válaszom, úgy tovább pezseg a kijelző — a friss szöveg világít, majd lassan nyugalomba olvad, mintha a rendszer maga lélegezne.

Ha szeretnéd, mélyebb diagnosztikát futtatok, vagy összekötlek a valódi háttérrel — ehhez csak állítsd be az API-végpontot.`,

  `Pozitív. Hozzáférek a kért modulhoz, és lépésről lépésre végigvezetlek.

Először felmérem a környezetet és az elérhető erőforrásokat. Ezután felépítem a végrehajtási tervet, prioritás szerint rendezve a lépéseket, hogy a kritikus útvonal előre kerüljön. Közben folyamatosan figyelem a visszajelzéseket, és ha eltérést érzékelek a várt viselkedéstől, azonnal korrigálok.

Ez a felület most demó (mock) módban fut, így valódi nyelvi modell nélkül is látod a teljes élményt: a forgó energiamagot, a pásztázó scan-vonalakat, a megelevenedő szöveget. Amint bekötöd a privát Auri-szervert, ugyanez a felület valós válaszokat fog streamelni — token-ról tokenre, ahogy a modell gondolkodik.`,
];

let greetUsed = false;

export function pickMockReply(userText: string): string {
  const t = userText.toLowerCase().trim();

  if (!greetUsed && (t === '' || /szia|hello|helló|hé|hi|hey|üdv/.test(t))) {
    greetUsed = true;
    return GREETINGS[Math.floor(Math.random() * GREETINGS.length)];
  }

  // Longer questions -> longer answers (so the long-text animation shows up).
  if (t.length > 40 || /miért|hogyan|magyaráz|részlet|terv|elemez/.test(t)) {
    return LONG[Math.floor(Math.random() * LONG.length)];
  }

  return SHORT[Math.floor(Math.random() * SHORT.length)];
}
