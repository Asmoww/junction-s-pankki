// Design E v2: the future as a graph. Code draws every number; the AI annotates the line and turns
// "what if…" sentences into scenarios that redraw the future. Loaded after app.js on /e.
const ES = {
  en: { wr: { card: "Your money year", open: "Watch", title: (n) => `${n}, your money year`, inOut: (i, o) => `Money in ${i} · out ${o}`,
      baskets: "Where it went", habit: "Your number-one habit", meals: "meals out", hours: (h) => `= ${h} hours of your work`,
      bigDay: "Your biggest day", best: "Best month", tough: "Toughest month", leftOver: (a) => `${a} left over`, lowest: (a) => `lowest ${a}`,
      noSpend: "no-spend days", streak: (d) => `longest streak ${d} days`, payday: "more on extras the week after payday",
      twins: (n) => `${n} people like you never went below zero`, youX: "You", themX: "Them", extrasMonth: "extras a month",
      visits: (a, b) => `Eating out: they ${b}, you ${a} times a month`, score: "Money fitness", next: "One thing for next year",
      share: "Share (no amounts)", done: "Done", shareText: (f) => `My money year: ${f.no_spend_days} no-spend days, a ${f.longest_no_spend_streak_days}-day streak and ${f.eat_out.visits} meals out. #MoneyWrapped`,
      tap: "Tap to continue" },
    hk: { name: "Money fitness", tiers: { vulnerable: "Vulnerable", coping: "Coping", healthy: "Healthy" },
      tones: { comfort: "A tight year, and it can get better. One thing first.", encourage: (t) => `Up ${t} points in three months. Keep going.`,
        reassure: (t) => `Down ${t} points: surprise costs did that, and your buffer handled them.`, steady: "Steady. One thing could lift it.",
        gentle_warning: (t) => `Down ${t} points. Here's what slipped.`, celebrate: "Strong. Keep the habit." },
      parts: { spend: "Spend less than you earn", on_time: "No days below zero", buffer: "Buffer before payday", long_term: "Long-term saving" },
      steps: { break_even: (g) => `Spend ${g} a month less to break even`, keep_10_percent: (g) => `Keep 10 % of income: ${g} a month less spending`,
        on_time: (g) => `Keep ${g} more on your account before payday`, buffer: (g, m) => `Build your buffer to ${m} months of must-pays: ${g} more`,
        long_term: (g) => `Put ${g} a month into long-term saving` },
      points: (p) => `+${p} points`, next: "What would lift it", unknown: (n) => `${n} measured; debt, credit, insurance and planning aren't in your account data`,
      method: "Based on the Spend and Save pillars of the Financial Health Network framework. Never compared with other people.", askQ: (s) => `Help me with this step: ${s}.` },
    aiNotes: "AI notes", shortBy: (d) => `short by payday ${d}`, buy: "Check a purchase", buyPh: "e.g. iPhone 17 256 GB", checking: "Checking shop pages…",
    checked: (m) => `price read from the shop page${m != null ? `, ${m} min old` : ""}`, claimDiff: (c) => `Search said ${c}; the page says otherwise`,
    notConf: (n) => `${n} shop${n === 1 ? "" : "s"} couldn't be confirmed`, noneConf: "No price could be confirmed, so it stays unknown.",
    own: "Use my own estimate", ownPh: "your estimate, €", ownLabel: "your estimate", notConnected: "Live prices aren't connected yet.",
    rules: "Live rules", rulesTitle: "Rules from official sources", unknown: "unknown", asOf: (d) => `as of ${d}`, fetchedAt: (d) => `checked ${d}`,
    effUnknown: "effective date not confirmed", recheck: "Re-check rules now", demo: "Demo controls", runMon: (n) => `Run monitor now: ${n}`,
    setupMon: "Set up monitors", ruleChanged: "A rule changed", sourceOnly: "Only the item name or rule is sent, never your data.",
    capShort: "Loan cap", euriborShort: "Euribor 12 m", homeCard: "Buying a home?", homeSub: "Today's rules and sources",
    since: (a) => `${a} since payday`, today: "Today", pay: "Payday", forecast: "forecast", extras: "your extras",
    payResult: (d) => `On payday, ${d}`, whatIf: "What if…", whatIfPh: "e.g. concert tickets 150 € on Friday",
    pause: "Pause extras", eatLess: "Eat out −50 %", rentLater: "Rent after payday", ask: (d) => `Ask about ${d}`,
    askQ: (d) => `What did I spend on ${d}, and was it a lot for me?`, thinking: "Reading your words…",
    aiNote: "Notes written by AI from your numbers", noAmount: "Tell me an amount, e.g. 150 €.", failed: "Couldn't do that one. Try again.",
    bills: { Housing: "Rent", Utilities: "Bills" }, nothing: "No spending",
    cards: { safe: "Safe this week", month: (m) => m, payday: "After payday", pot: "Surprises", fin: "vs Finland", psd2: "Other bank" },
    perMonth: "a month", vsFin: (a) => `${a} in Finland`, moved: "moved away" },
  fi: { wr: { card: "Rahavuotesi", open: "Katso", title: (n) => `${n}, rahavuotesi`, inOut: (i, o) => `Rahaa tuli ${i} · meni ${o}`,
      baskets: "Mihin se meni", habit: "Ykköstapasi", meals: "kertaa ulkona syömässä", hours: (h) => `= ${h} tuntia työtäsi`,
      bigDay: "Suurin päiväsi", best: "Paras kuukausi", tough: "Tiukin kuukausi", leftOver: (a) => `${a} jäi yli`, lowest: (a) => `alimmillaan ${a}`,
      noSpend: "päivää ilman ostoja", streak: (d) => `pisin putki ${d} päivää`, payday: "enemmän extroihin palkkaviikolla",
      twins: (n) => `${n} kaltaistasi ei käynyt kertaakaan miinuksella`, youX: "Sinä", themX: "He", extrasMonth: "extroihin kuussa",
      visits: (a, b) => `Ulkona syöminen: he ${b}, sinä ${a} kertaa kuussa`, score: "Rahakunto", next: "Yksi asia ensi vuodelle",
      share: "Jaa (ilman summia)", done: "Valmis", shareText: (f) => `Rahavuoteni: ${f.no_spend_days} päivää ilman ostoja, ${f.longest_no_spend_streak_days} päivän putki ja ${f.eat_out.visits} kertaa ulkona syömässä. #Rahavuosi`,
      tap: "Napauta jatkaaksesi" },
    hk: { name: "Rahakunto", tiers: { vulnerable: "Haavoittuva", coping: "Pärjäävä", healthy: "Hyvä" },
      tones: { comfort: "Tiukka vuosi, ja se voi parantua. Yksi asia ensin.", encourage: (t) => `${t} pistettä ylös kolmessa kuussa. Hyvä suunta.`,
        reassure: (t) => `${t} pistettä alas: yllättävät menot tekivät sen, ja puskurisi kesti ne.`, steady: "Vakaa. Yksi asia voisi nostaa sitä.",
        gentle_warning: (t) => `${t} pistettä alas. Tässä mikä lipsui.`, celebrate: "Vahva. Jatka samaan malliin." },
      parts: { spend: "Kuluta vähemmän kuin ansaitset", on_time: "Ei miinuspäiviä", buffer: "Puskuri ennen palkkaa", long_term: "Pitkäaikainen säästäminen" },
      steps: { break_even: (g) => `Kuluta ${g} vähemmän kuussa, niin tulot riittävät`, keep_10_percent: (g) => `Säästä 10 % tuloista: ${g} vähemmän kuussa`,
        on_time: (g) => `Pidä tilillä ${g} enemmän ennen palkkapäivää`, buffer: (g, m) => `Kasvata puskuri ${m} kuukauden pakollisiin menoihin: ${g} lisää`,
        long_term: (g) => `Laita ${g} kuussa pitkäaikaiseen säästöön` },
      points: (p) => `+${p} pistettä`, next: "Mikä nostaisi sitä", unknown: (n) => `${n} mitattu; velka, luotto, vakuutukset ja suunnitelmat eivät näy tilitiedoista`,
      method: "Perustuu Financial Health Networkin Spend- ja Save-pilareihin. Sinua ei verrata muihin.", askQ: (s) => `Auta minua tässä: ${s}.` },
    aiNotes: "Tekoälyn huomiot", shortBy: (d) => `vajetta palkkapäivään ${d}`, buy: "Tarkista ostos", buyPh: "esim. iPhone 17 256 Gt", checking: "Tarkistan kauppojen sivuja…",
    checked: (m) => `hinta luettu kaupan sivulta${m != null ? `, ${m} min vanha` : ""}`, claimDiff: (c) => `Haku sanoi ${c}; sivu sanoo toisin`,
    notConf: (n) => `${n} kauppaa ei voitu vahvistaa`, noneConf: "Hintaa ei voitu vahvistaa, joten se on tuntematon.",
    own: "Käytä omaa arviotani", ownPh: "oma arvio, €", ownLabel: "oma arvio", notConnected: "Live-hinnat eivät ole vielä käytössä.",
    rules: "Säännöt nyt", rulesTitle: "Säännöt virallisista lähteistä", unknown: "tuntematon", asOf: (d) => `tilanne ${d}`, fetchedAt: (d) => `tarkistettu ${d}`,
    effUnknown: "voimaantulopäivä vahvistamatta", recheck: "Tarkista säännöt nyt", demo: "Demo-ohjaimet", runMon: (n) => `Aja seuranta nyt: ${n}`,
    setupMon: "Ota seuranta käyttöön", ruleChanged: "Sääntö muuttui", sourceOnly: "Vain tuotteen nimi tai sääntö lähtee, ei koskaan tietojasi.",
    capShort: "Lainakatto", euriborShort: "Euribor 12 kk", homeCard: "Asunnon osto?", homeSub: "Säännöt nyt ja lähteet",
    since: (a) => `${a} palkkapäivästä`, today: "Tänään", pay: "Palkka", forecast: "ennuste", extras: "extrasi",
    payResult: (d) => `Palkkapäivänä ${d}`, whatIf: "Entä jos…", whatIfPh: "esim. konserttiliput 150 € perjantaina",
    pause: "Tauko extroille", eatLess: "Ulkona syöminen −50 %", rentLater: "Vuokra palkan jälkeen", ask: (d) => `Kysy päivästä ${d}`,
    askQ: (d) => `Mihin käytin rahaa ${d}, ja oliko se minulle paljon?`, thinking: "Luen pyyntöäsi…",
    aiNote: "Tekoälyn muistiinpanot lukujesi pohjalta", noAmount: "Kerro summa, esim. 150 €.", failed: "Tämä ei onnistunut. Yritä uudelleen.",
    bills: { Housing: "Vuokra", Utilities: "Laskut" }, nothing: "Ei ostoja",
    cards: { safe: "Turvallisesti", month: (m) => m, payday: "Palkan jälkeen", pot: "Yllätykset", fin: "vs Suomi", psd2: "Toinen pankki" },
    perMonth: "kuussa", vsFin: (a) => `Suomessa ${a}`, moved: "siirtyi pois" },
  sv: { wr: { card: "Ditt pengaår", open: "Titta", title: (n) => `${n}, ditt pengaår`, inOut: (i, o) => `In ${i} · ut ${o}`,
      baskets: "Vart det tog vägen", habit: "Din största vana", meals: "gånger äta ute", hours: (h) => `= ${h} timmar av ditt arbete`,
      bigDay: "Din största dag", best: "Bästa månaden", tough: "Tuffaste månaden", leftOver: (a) => `${a} över`, lowest: (a) => `lägst ${a}`,
      noSpend: "dagar utan köp", streak: (d) => `längsta svit ${d} dagar`, payday: "mer på extra veckan efter lönen",
      twins: (n) => `${n} som du gick aldrig under noll`, youX: "Du", themX: "De", extrasMonth: "extra i månaden",
      visits: (a, b) => `Äta ute: de ${b}, du ${a} gånger i månaden`, score: "Pengakondition", next: "En sak för nästa år",
      share: "Dela (utan belopp)", done: "Klar", shareText: (f) => `Mitt pengaår: ${f.no_spend_days} dagar utan köp, en svit på ${f.longest_no_spend_streak_days} dagar och ${f.eat_out.visits} gånger ute och åt. #Pengaåret`,
      tap: "Tryck för att fortsätta" },
    hk: { name: "Pengakondition", tiers: { vulnerable: "Sårbar", coping: "Klarar sig", healthy: "Bra" },
      tones: { comfort: "Ett tufft år, och det kan bli bättre. En sak först.", encourage: (t) => `Upp ${t} poäng på tre månader. Fortsätt så.`,
        reassure: (t) => `Ner ${t} poäng: oväntade kostnader gjorde det, och din buffert klarade dem.`, steady: "Stabilt. En sak kunde lyfta det.",
        gentle_warning: (t) => `Ner ${t} poäng. Här är vad som halkade.`, celebrate: "Starkt. Fortsätt så." },
      parts: { spend: "Spendera mindre än du tjänar", on_time: "Inga dagar under noll", buffer: "Buffert före lön", long_term: "Långsiktigt sparande" },
      steps: { break_even: (g) => `Spendera ${g} mindre i månaden för att gå jämnt ut`, keep_10_percent: (g) => `Spara 10 % av inkomsten: ${g} mindre i månaden`,
        on_time: (g) => `Ha ${g} mer på kontot före lönedagen`, buffer: (g, m) => `Bygg bufferten till ${m} månaders måsten: ${g} till`,
        long_term: (g) => `Sätt ${g} i månaden i långsiktigt sparande` },
      points: (p) => `+${p} poäng`, next: "Vad skulle lyfta det", unknown: (n) => `${n} mätta; skulder, kredit, försäkringar och planering syns inte i kontodata`,
      method: "Baserat på Spend- och Save-pelarna i Financial Health Networks ramverk. Jämförs aldrig med andra.", askQ: (s) => `Hjälp mig med detta: ${s}.` },
    aiNotes: "AI-anteckningar", shortBy: (d) => `saknas till lönedagen ${d}`, buy: "Kolla ett köp", buyPh: "t.ex. iPhone 17 256 GB", checking: "Kollar butikernas sidor…",
    checked: (m) => `pris läst från butikens sida${m != null ? `, ${m} min gammalt` : ""}`, claimDiff: (c) => `Sökningen sa ${c}; sidan säger annat`,
    notConf: (n) => `${n} butiker kunde inte bekräftas`, noneConf: "Inget pris kunde bekräftas, så det är okänt.",
    own: "Använd min egen uppskattning", ownPh: "din uppskattning, €", ownLabel: "egen uppskattning", notConnected: "Livepriser är inte anslutna än.",
    rules: "Regler nu", rulesTitle: "Regler från officiella källor", unknown: "okänt", asOf: (d) => `per ${d}`, fetchedAt: (d) => `kollat ${d}`,
    effUnknown: "ikraftträdande inte bekräftat", recheck: "Kolla reglerna nu", demo: "Demokontroller", runMon: (n) => `Kör bevakning nu: ${n}`,
    setupMon: "Sätt upp bevakning", ruleChanged: "En regel ändrades", sourceOnly: "Bara varans namn eller regeln skickas, aldrig dina data.",
    capShort: "Lånetak", euriborShort: "Euribor 12 m", homeCard: "Köpa bostad?", homeSub: "Dagens regler och källor",
    since: (a) => `${a} sedan lönedagen`, today: "I dag", pay: "Lön", forecast: "prognos", extras: "dina extra",
    payResult: (d) => `På lönedagen ${d}`, whatIf: "Tänk om…", whatIfPh: "t.ex. konsertbiljetter 150 € på fredag",
    pause: "Pausa extra", eatLess: "Äta ute −50 %", rentLater: "Hyran efter lön", ask: (d) => `Fråga om ${d}`,
    askQ: (d) => `Vad spenderade jag den ${d}, och var det mycket för mig?`, thinking: "Läser det du skrev…",
    aiNote: "Anteckningar skrivna av AI utifrån dina siffror", noAmount: "Ange ett belopp, t.ex. 150 €.", failed: "Det gick inte. Försök igen.",
    bills: { Housing: "Hyra", Utilities: "Räkningar" }, nothing: "Inga köp",
    cards: { safe: "Tryggt nu", month: (m) => m, payday: "Efter lön", pot: "Överraskningar", fin: "vs Finland", psd2: "Annan bank" },
    perMonth: "i månaden", vsFin: (a) => `${a} i Finland`, moved: "flyttades" },
};
const E = () => ES[lang] || ES.en;
const SPARK = `<svg class="spark" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0c.6 4.2 3.8 7.4 8 8-4.2.6-7.4 3.8-8 8-.6-4.2-3.8-7.4-8-8 4.2-.6 7.4-3.8 8-8z"/></svg>`;
let fut = null, notes = null, active = null, scen = null, picked = null, liveSt = null, buyRes = null;
const CART = `<svg class="spark" viewBox="0 0 16 16" aria-hidden="true"><path d="M1 2h2l1.6 7.2a1 1 0 0 0 1 .8h6.2a1 1 0 0 0 1-.8L14 5H4.2" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><circle cx="6.5" cy="13" r="1.2"/><circle cx="12" cy="13" r="1.2"/></svg>`;
const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return ""; } };
const when = (iso) => iso ? new Date(iso).toLocaleString(T().locale, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "";

// Smooth line through points (Catmull-Rom → cubic Bézier), never overshooting much.
function smooth(p) {
  if (p.length < 2) return "";
  let d = `M${p[0][0].toFixed(1)},${p[0][1].toFixed(1)}`;
  for (let i = 0; i < p.length - 1; i++) {
    const a = p[i - 1] || p[i], b = p[i], c = p[i + 1], e = p[i + 2] || c, t = 0.18;
    d += ` C${(b[0] + (c[0] - a[0]) * t).toFixed(1)},${(b[1] + (c[1] - a[1]) * t).toFixed(1)} ${(c[0] - (e[0] - b[0]) * t).toFixed(1)},${(c[1] - (e[1] - b[1]) * t).toFixed(1)} ${c[0].toFixed(1)},${c[1].toFixed(1)}`;
  }
  return d;
}

function graph() {
  const r = home.ribbon, W = Math.min(window.innerWidth, 480), H = 396, px = 20, top = 112, bot = 44;
  const past = r.past, base = fut.base.path, noext = fut.no_extras.path, sc = scen && scen.scenario ? scen.scenario.path : null;
  const all = [...past, ...base, ...noext, ...(sc || [])].map((p) => p.balance_eur);
  let lo = Math.min(...all), hi = Math.max(...all);
  if (lo > 0 && lo < 0.35 * hi) lo = 0;
  const pad = Math.max(hi - lo, 1) * 0.08; lo -= pad; hi += pad;
  const n = past.length + base.length - 1, iT = past.length - 1;
  const X = (i) => px + (i * (W - 2 * px)) / n, Y = (v) => top + ((hi - v) / (hi - lo)) * (H - top - bot);
  const P = (arr, off) => arr.map((p, k) => [X(off + k), Y(p.balance_eur)]);
  const pPast = P(past, 0), todayPt = pPast[iT];
  const pBase = [todayPt, ...P(base, iT + 1)], pNo = [todayPt, ...P(noext, iT + 1)];
  const neg = fut.base.runs_out, zeroY = lo < 0 && hi > 0 ? Y(0) : null;
  const band = smooth(pNo) + " L" + [...pBase].reverse().map((q) => q.map((v) => v.toFixed(1)).join(",")).join(" L") + " Z";
  const ticks = [];
  for (let i = 0; i <= n; i += 7) ticks.push(`<text x="${X(i)}" y="${H - 14}" text-anchor="middle" class="tick">${day((past[i] || base[i - past.length]).date)}</text>`);
  const marks = [];
  marks.push(`<g class="mk pay" transform="translate(${pPast[0][0]},${pPast[0][1]})"><circle r="9"/><path d="M0 4V-4M-3.5 -0.5L0 -4 3.5 -0.5"/></g>`);
  for (const b of fut.bills) {
    const i = base.findIndex((q) => q.date === b.date); if (i < 0 || b.date === fut.next_payday) continue;
    const [x, y] = pBase[i + 1];
    marks.push(`<g class="mk bill ${base[i].balance_eur < 0 ? "neg" : ""}" transform="translate(${x},${y})"><rect x="-8" y="-8" width="16" height="16" rx="5"/><path d="M-3.5 1.5V-1.5L0 -4 3.5 -1.5V3.5H-3.5Z"/></g>
      <text class="mlab ${base[i].balance_eur < 0 ? "neg" : ""}" x="${x + 13}" y="${y + 4}">${esc((E().bills[b.bill] || b.bill))} ${eur0(b.eur)}</text>`);
  }
  const end = pBase[pBase.length - 1];
  marks.push(`<g class="mk pay" transform="translate(${end[0]},${end[1]})"><circle r="9"/><path d="M0 4V-4M-3.5 -0.5L0 -4 3.5 -0.5"/></g>`);
  // AI notes: laid out after render in lanes above the line (layoutNotes), with a leader to the point.
  const nl = [];
  (notes ? notes.notes : []).forEach((nt) => {
    let i = past.findIndex((q) => q.date === nt.date), pt;
    if (i >= 0) pt = pPast[i]; else { i = base.findIndex((q) => q.date === nt.date); if (i < 0) return; pt = pBase[i + 1]; }
    nl.push(`<div class="note" data-x="${pt[0].toFixed(1)}" data-y="${pt[1].toFixed(1)}">${SPARK}<span>${esc(nt.text).replace(/ (€|%)/g, "\u00a0$1")}</span></div>
      <span class="ndot" style="left:${pt[0]}px;top:${pt[1]}px"></span>`);
  });
  const scLine = sc ? `<path class="scen" d="${smooth([todayPt, ...P(sc, iT + 1)])}"/>` : "";
  const svg = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
    <defs><linearGradient id="ga" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#2e9c5e" stop-opacity=".22"/><stop offset="1" stop-color="#2e9c5e" stop-opacity="0"/></linearGradient></defs>
    ${zeroY !== null ? `<line class="zero" x1="${px}" x2="${W - px}" y1="${zeroY}" y2="${zeroY}"/><text class="tick" x="${W - px}" y="${zeroY - 6}" text-anchor="end">0 €</text>` : ""}
    <path d="${smooth(pPast)} L${todayPt[0]},${H - bot} L${pPast[0][0]},${H - bot} Z" fill="url(#ga)"/>
    <path class="band ${neg ? "neg" : ""}" d="${band}"/>
    <path class="base ${neg ? "neg" : ""} ${sc ? "dim" : ""}" d="${smooth(pBase)}"/>
    ${scLine}
    <path class="past" d="${smooth(pPast)}"/>
    ${ticks.join("")}${marks.join("")}
    <line class="guide" x1="0" x2="0" y1="${top - 20}" y2="${H - bot + 6}"/>
    <circle class="today" cx="${todayPt[0]}" cy="${todayPt[1]}" r="8"/>
    <circle class="cursor" cx="${todayPt[0]}" cy="${todayPt[1]}" r="7"/></svg>`;
  const bandMid = pBase[Math.floor(pBase.length * 0.6)], noMid = pNo[Math.floor(pNo.length * 0.6)];
  const bandLab = Math.abs(bandMid[1] - noMid[1]) > 22 ? `<div class="bandlab" style="left:${bandMid[0]}px;top:${(bandMid[1] + noMid[1]) / 2}px">${E().extras}</div>` : "";
  const credit = nl.length ? `<div class="credit">${SPARK}${E().aiNotes}</div>` : "";
  return { html: `<div class="g" id="g">${svg}<svg class="leaders" width="${W}" height="${H}"></svg>${nl.join("")}${bandLab}${credit}<div class="tip" hidden></div></div>`, X, Y, W, n, iT, px, past, base, sc };
}

function layoutNotes() {
  const g = $("#g"); if (!g) return;
  const W = g.clientWidth, lanes = [[], []], lead = g.querySelector(".leaders"), gap = 8;
  let lines = "";
  [...g.querySelectorAll(".note")].sort((a, b) => a.dataset.x - b.dataset.x).forEach((el) => {
    const x = +el.dataset.x, y = +el.dataset.y, w = el.offsetWidth;
    const want = Math.max(10, Math.min(W - 10 - w, x - w / 2));
    let best = null;
    lanes.forEach((ln, li) => {
      const cands = [want, ...ln.map(([, r]) => r + gap), ...ln.map(([l]) => l - gap - w)];
      for (const c of cands) {
        if (c < 10 || c + w > W - 10 || ln.some(([l, r]) => c < r + gap && c + w > l - gap)) continue;
        const cost = Math.abs(c - want) + li * 40;
        if (!best || cost < best.cost) best = { c, li, cost };
      }
    });
    if (!best) best = { c: want, li: 1 };
    lanes[best.li].push([best.c, best.c + w]);
    const top = 26 + best.li * 44;
    el.style.left = `${best.c}px`; el.style.top = `${top}px`;
    const ax = Math.max(best.c + 14, Math.min(best.c + w - 14, x));
    lines += `<path d="M${ax},${top + el.offsetHeight} L${x},${y - 6}" />`;
  });
  lead.innerHTML = lines;
}

function resultRow() {
  const b = fut.base.end_eur, s = scen && scen.scenario;
  const cls = (v) => (v < 0 ? "neg" : "pos");
  return `<div class="result"><span>${E().payResult(day(fut.next_payday))}</span>
    <span class="vals">${s ? `<s class="${cls(b)}">${eur0(b)}</s><b class="${cls(s.end_eur)}">${eur0(s.end_eur)}</b>
      <i class="${s.delta_at_payday_eur >= 0 ? "up" : "down"}">${s.delta_at_payday_eur >= 0 ? "+" : "−"}${eur0(Math.abs(s.delta_at_payday_eur))}</i>`
      : `<b class="${cls(b)}">${eur0(b)}</b>`}</span></div>`;
}

function dock() {
  const chips = [];
  if (picked !== null) chips.push(`<button class="chip ask" data-pick>${SPARK}${esc(E().ask(day(picked)))}</button>`);
  chips.push(`<button class="chip ai ${active === "ai" ? "on" : ""}" data-whatif>${SPARK}${active === "ai" && scen ? esc(scen.parsed.label) + ` <span class="x">×</span>` : E().whatIf}</button>`);
  chips.push(`<button class="chip buy ${active === "buy" ? "on" : ""}" data-buy>${CART}${active === "buy" && scen ? esc(scen.label) + ` <span class="x">×</span>` : E().buy}</button>`);
  chips.push(`<button class="chip ${active === "pause" ? "on" : ""}" data-sc="pause">${E().pause}</button>`);
  if ((fut.extras_by_category_until_payday || {}).Restaurants) chips.push(`<button class="chip ${active === "eat" ? "on" : ""}" data-sc="eat">${E().eatLess}</button>`);
  if (fut.bills.some((b) => b.bill === "Housing" && b.date !== fut.next_payday)) chips.push(`<button class="chip ${active === "rent" ? "on" : ""}" data-sc="rent">${E().rentLater}</button>`);
  return `<div class="dock"><div class="chips">${chips.join("")}</div>
    <form class="wi" hidden><span>${SPARK}</span><input maxlength="200" placeholder="${esc(E().whatIfPh)}"><button class="go" aria-label="Go">→</button></form>
    <div class="wimsg" hidden></div>
    <form class="wi buyf" hidden><span>${CART}</span><input maxlength="100" placeholder="${esc(E().buyPh)}"><button class="go" aria-label="Go">→</button></form>
    <div class="offers" ${buyRes ? "" : "hidden"}>${buyRes ? offersHtml(buyRes) : ""}</div></div>`;
}

function offersHtml(r) {
  if (r.error) return `<p class="omsg">${esc(r.error)}</p>`;
  const rows = r.confirmed.map((o) => `<button class="offer" data-url="${esc(o.url)}"><span><b>${eur(o.price_eur)}</b>
      <span class="src">${esc(o.domain)} · ${esc(E().checked(o.page_age_minutes))}</span>
      ${o.claim_differed ? `<span class="diff">${esc(E().claimDiff(eur0(o.claimed_price_eur)))}</span>` : ""}</span>
      <span class="nm">${esc(o.name || "")}</span></button>`).join("");
  const none = r.confirmed.length ? "" : `<p class="omsg">${E().noneConf}</p><form class="own"><input inputmode="decimal" placeholder="${esc(E().ownPh)}"><button>${E().own}</button></form>`;
  const nc = r.not_confirmed.length ? `<p class="omsg small">${E().notConf(r.not_confirmed.length)}</p>` : "";
  return rows + none + nc + `<p class="omsg small">${E().sourceOnly}</p>`;
}

function strip() {
  const o = home.overview, s = o.safe_to_spend, m = o.month, pot = home.pot, pp = home.cards.find((c) => c.id === "payday");
  const cards = [];
  const psd2 = home.cards.find((c) => c.id === "psd2");
  if (psd2) cards.push(`<button class="mini" data-act="psd2"><span class="t">${E().cards.psd2}</span><b>${eur0(psd2.numbers.moved_to_other_bank_eur)}</b><span class="s">${E().moved}</span>
    <div class="flow"><i style="width:${Math.round(psd2.numbers.share_of_income * 100)}%"></i></div></button>`);
  const days = s.days_until_payday;
  const shortE = s.safe_until_payday_eur < 0;
  cards.push(`<button class="mini ${shortE ? "neg" : ""}" data-ask="${esc(T().suggestions[0])}"><span class="t">${E().cards.safe}</span>
    <b>${shortE ? "−" + eur0(-s.safe_until_payday_eur) : eur0(s.safe_this_week_eur)}</b>
    <span class="s">${shortE ? E().shortBy(day(s.next_payday)) : eur0(s.safe_per_day_eur) + "/" + (lang === "en" ? "day" : lang === "fi" ? "pv" : "dag")}</span>
    <div class="dots">${Array.from({ length: Math.min(days, 15) }, (_, i) => `<i class="${shortE ? "short" : i < 7 ? "wk" : ""}"></i>`).join("")}</div></button>`);
  const tot = m.total_spending_eur || 1;
  cards.push(`<button class="mini" data-ask="${esc(T().suggestions[4])}"><span class="t">${E().cards.month(monthName(m.period.start))}</span><b>${eur0(m.total_spending_eur)}</b>
    <div class="seg">${m.baskets.map((b) => `<i style="flex:${b.total_eur / tot};background:${BASKET_COLORS[b.basket]}"></i>`).join("")}</div></button>`);
  if (pp) {
    const n = pp.numbers, mx = Math.max(n.extras_per_day_week_after_payday_eur, n.extras_per_day_week_before_payday_eur, 1);
    cards.push(`<button class="mini" data-ask="${esc(T().cards.payday[2])}"><span class="t">${E().cards.payday}</span><b>+${n.payday_week_change_percent} %</b>
      <div class="bars2"><i style="height:${(n.extras_per_day_week_before_payday_eur / mx) * 100}%"></i><i class="hi" style="height:${(n.extras_per_day_week_after_payday_eur / mx) * 100}%"></i></div></button>`);
  }
  if (pot.average_per_month_last_12_eur >= 20) {
    const mx = Math.max(...pot.months.slice(-12).map((x) => x.eur), 1);
    cards.push(`<button class="mini" data-act="pot"><span class="t">${E().cards.pot}</span><b>${eur0(pot.average_per_month_last_12_eur)}</b><span class="s">${E().perMonth}</span>
      <div class="spark12">${pot.months.slice(-12).map((x) => `<i style="height:${Math.max(4, (x.eur / mx) * 100)}%"></i>`).join("")}<u style="bottom:${(pot.average_per_month_last_12_eur / mx) * 100}%"></u></div></button>`);
  }
  const big = home.benchmark.areas.filter((a) => a.finland_same_age_per_month_eur > 0)
    .sort((a, b) => b.you_per_month_eur / b.finland_same_age_per_month_eur - a.you_per_month_eur / a.finland_same_age_per_month_eur)[0];
  if (big) {
    const mx = Math.max(big.you_per_month_eur, big.finland_same_age_per_month_eur, 1);
    cards.push(`<button class="mini" data-ask="${esc(T().suggestions[5])}"><span class="t">${esc(label(big.area))} ${E().cards.fin}</span><b>${eur0(big.you_per_month_eur)}</b>
      <span class="s">${esc(E().vsFin(eur0(big.finland_same_age_per_month_eur)))}</span>
      <div class="pair"><i style="width:${(big.you_per_month_eur / mx) * 100}%"></i><i class="fi" style="width:${(big.finland_same_age_per_month_eur / mx) * 100}%"></i></div></button>`);
  }
  cards.unshift(`<button class="mini wrapcard" data-wrapped><span class="t">${E().wr.card}</span><b>${esc(day("2025-10-01"))} – ${esc(day(home.overview.customer.as_of))}</b><span class="go">${E().wr.open} ›</span></button>`);
  const hk = home.health;
  if (hk) {
    const ring = `conic-gradient(var(--g700) ${hk.score * 3.6}deg, var(--g100) 0)`;
    cards.splice(psd2 ? 2 : 1, 0, `<button class="mini health" data-health><span class="t">${E().hk.name}</span>
      <div class="ring" style="background:${ring}"><span>${hk.score}</span></div><span class="s">${E().hk.tiers[hk.tier]}</span></button>`);
  }
  if (liveSt) {
    // Not a headline on Home (TRACKER A1/A2): a small entry for people buying a home. The sheet shows each rule with
    // its own source and date (Euribor is Suomen Pankki's, the loan cap FIN-FSA's), never one source for both.
    cards.push(`<button class="mini rules" data-rules><span class="t">${E().homeCard}</span>
      <span class="s">${E().homeSub} ›</span></button>`);
  }
  const lc = liveSt && liveSt.cards && liveSt.cards[0];
  const top = lc ? `<button class="rulecard" data-rules>${SPARK}<span><b>${E().ruleChanged}</b> ${esc(lc.rule.replace(/_/g, " "))}: ${lc.before ?? "?"} → ${lc.after ?? "?"} · ${esc(host(lc.source_url))}</span></button>` : "";
  return top + `<div class="strip">${cards.join("")}</div>`;
}

function bindGraph(G) {
  const el = $("#g"); if (!el) return;
  const svg = el.querySelector("svg"), cur = svg.querySelector(".cursor"), guide = svg.querySelector(".guide"), tip = el.querySelector(".tip");
  const valAt = (i) => (i <= G.iT ? G.past[i] : (G.sc || G.base)[i - G.iT - 1]);
  const show = (cx) => {
    const x = cx - el.getBoundingClientRect().left;
    const i = Math.max(0, Math.min(G.n, Math.round(((x - G.px) / (G.W - 2 * G.px)) * G.n)));
    const p = valAt(i), X = G.X(i), Y = G.Y(p.balance_eur);
    cur.setAttribute("cx", X); cur.setAttribute("cy", Y); cur.classList.add("on");
    guide.setAttribute("x1", X); guide.setAttribute("x2", X); guide.classList.add("on");
    const items = i <= G.iT ? (p.items || []) : fut.bills.filter((b) => b.date === p.date).map((b) => ({ what: E().bills[b.bill] || b.bill, eur: b.eur }));
    tip.hidden = false; tip.style.left = `${Math.max(84, Math.min(G.W - 84, X))}px`;
    tip.innerHTML = `<div class="th"><span>${day(p.date)}${i > G.iT ? ` · ${E().forecast}` : ""}</span><b class="${p.balance_eur < 0 ? "neg" : ""}">${eur(p.balance_eur)}</b></div>` +
      (i <= G.iT && !items.length ? `<div class="ti muted">${E().nothing}</div>` : items.map((t) => `<div class="ti"><span>${esc(label(t.what))}</span><span>−${eur(t.eur)}</span></div>`).join(""));
    return { i, p };
  };
  let last = null;
  el.addEventListener("pointerdown", (e) => { el.setPointerCapture(e.pointerId); last = show(e.clientX); });
  el.addEventListener("pointermove", (e) => { if (e.buttons || e.pointerType === "mouse") last = show(e.clientX); });
  const hide = () => { tip.hidden = true; cur.classList.remove("on"); guide.classList.remove("on"); };
  el.addEventListener("pointerleave", hide);
  el.addEventListener("pointercancel", hide);
  el.addEventListener("pointerup", (e) => {
    if (e.pointerType !== "mouse") hide();  // touch: the card goes away when the finger lifts
    if (last && last.i <= G.iT && last.i > 0) { picked = last.p.date; $(".dock").outerHTML = dock(); bindDock(); }
  });
}

function bindDock() {
  const d = $(".dock"); if (!d) return;
  d.querySelectorAll("[data-sc]").forEach((b) => b.addEventListener("click", () => runPreset(b.dataset.sc)));
  const pk = d.querySelector("[data-pick]"); if (pk) pk.addEventListener("click", () => ask(E().askQ(day(picked))));
  const form = d.querySelector(".wi:not(.buyf)"), msg = d.querySelector(".wimsg");
  const bf = d.querySelector(".buyf"), offers = d.querySelector(".offers");
  d.querySelector("[data-buy]").addEventListener("click", (e) => {
    if (active === "buy" && e.target.classList.contains("x")) { active = null; scen = null; return redraw(); }
    bf.hidden = !bf.hidden; if (!bf.hidden) bf.querySelector("input").focus();
  });
  bf.addEventListener("submit", async (e) => {
    e.preventDefault();
    const item = bf.querySelector("input").value.trim(); if (!item) return;
    offers.hidden = false; offers.innerHTML = `<p class="omsg"><span class="typing"><i></i><i></i><i></i></span> ${E().checking}</p>`;
    try {
      const r = await fetch("/api/live/purchase", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ item }) });
      buyRes = r.ok ? await r.json() : { error: r.status === 503 ? E().notConnected : E().failed };
    } catch { buyRes = { error: E().failed }; }
    offers.innerHTML = offersHtml(buyRes); bindOffers();
  });
  bindOffers();
  d.querySelector("[data-whatif]").addEventListener("click", (e) => {
    if (active === "ai" && e.target.classList.contains("x")) { active = null; scen = null; return redraw(); }
    form.hidden = !form.hidden; if (!form.hidden) form.querySelector("input").focus();
  });
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = form.querySelector("input").value.trim(); if (!text) return;
    msg.hidden = false; msg.innerHTML = `<span class="typing"><i></i><i></i><i></i></span> ${E().thinking}`;
    try {
      const r = await api("/api/whatif", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ customer_id: cid, text, lang }) });
      const p = r.parsed;
      if (p.unsupported && !p.one_offs.length && !p.income.length && !p.cuts.length && !p.move_bills.length && !p.pause_extras) {
        msg.textContent = p.unsupported || E().noAmount; return;
      }
      scen = r; active = "ai"; redraw();
    } catch { msg.textContent = E().failed; }
  });
}

function bindOffers() {
  const o = $(".dock .offers"); if (!o || !buyRes || buyRes.error) return;
  o.querySelectorAll(".offer").forEach((b) => b.addEventListener("click", async () => {
    const r = await api("/api/live/purchase/apply", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ customer_id: cid, item: buyRes.item, url: b.dataset.url }) });
    scen = { ...r, label: r.label }; active = "buy"; buyRes = null; redraw();
  }));
  const own = o.querySelector(".own");
  if (own) own.addEventListener("submit", async (e) => {
    e.preventDefault();
    const v = parseFloat(own.querySelector("input").value.replace(",", "."));
    if (!(v > 0)) return;
    const t = new Date(); t.setDate(t.getDate() + 1);
    const r = await api("/api/scenario", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ customer_id: cid, scenario: { one_offs: [{ label: buyRes.item, amount: v, date: home.ribbon.past.at(-1).date }] } }) });
    scen = { ...r, label: `${buyRes.item} ${eur0(v)} (${E().ownLabel})` }; active = "buy"; buyRes = null; redraw();
  });
}

async function runPreset(k) {
  if (active === k) { active = null; scen = null; return redraw(); }
  const sc = { pause: { pause_extras: true }, eat: { cuts: [{ category: "Restaurants", percent: 50 }] },
    rent: { move_bills: [{ bill: "Housing", date: (() => { const d = new Date(fut.next_payday + "T12:00:00"); d.setDate(d.getDate() + 1); return d.toISOString().slice(0, 10); })() }] } }[k];
  scen = await api("/api/scenario", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ customer_id: cid, scenario: sc }) });
  active = k; redraw();
}

function redraw() {
  const G = graph();
  $("#hero").innerHTML = G.html + resultRow() + dock();
  layoutNotes(); bindGraph(G); bindDock();
}

// ---------------------------------------------------------------- Money Wrapped (story slides)
async function openWrapped() {
  const root = document.createElement("div");
  root.className = "wrap"; root.innerHTML = `<div class="wtop"><div class="wbars"></div><button class="wx" aria-label="Close">×</button></div><div class="wslide"><span class="typing"><i></i><i></i><i></i></span></div>`;
  document.body.appendChild(root);
  root.querySelector(".wx").onclick = () => root.remove();
  let w;
  try { w = await api(`/api/wrapped/${cid}?lang=${lang}`); } catch { root.remove(); return; }
  const f = w.facts, cap = (k) => (w.captions && w.captions[k] ? `<p class="wcap">${SPARK}${esc(w.captions[k])}</p>` : "");
  const W = E().wr, mon = (ym) => new Date(ym + "-15T12:00:00").toLocaleDateString(T().locale, { month: "long" });
  const tot = (f.baskets_eur["1"] + f.baskets_eur["2"] + f.baskets_eur["3"]) || 1;
  const slides = [
    `<div class="wk">${esc(day(f.period.start))} – ${esc(day(f.period.end))}</div><h1>${esc(W.title(f.name || ""))}</h1><p class="wsub">${esc(W.inOut(eur0(f.money_in_eur), eur0(f.money_out_eur)))}</p>${cap("year")}`,
    `<div class="wk">${W.baskets}</div>${[1, 2, 3].map((b) => `<div class="wb"><span>${esc(T().baskets[b][0])}</span><div><i style="width:${(f.baskets_eur[b] / tot) * 100}%;background:${["", "#fff", "#8fd0a8", "#d7efe0"][b]}"></i></div><b>${eur0(f.baskets_eur[b])}</b></div>`).join("")}${cap("baskets")}`,
    `<div class="wk">${W.habit}</div><div class="wbig">${f.eat_out.visits}</div><p class="wsub">${W.meals} · ${eur0(f.eat_out.total_eur)}</p>${f.eat_out.hours_of_work ? `<p class="wsub">${esc(W.hours(f.eat_out.hours_of_work))}</p>` : ""}${cap("habit")}`,
    f.biggest_day ? `<div class="wk">${W.bigDay}</div><div class="wbig sm">${esc(day(f.biggest_day.date))}</div><p class="wsub">${eur0(f.biggest_day.total_eur)} · ${esc(f.biggest_day.what.map(label).join(", "))}</p>${cap("big_day")}` : null,
    `<div class="wk">${W.best}</div><div class="wbig sm">${esc(mon(f.best_month.month))}</div><p class="wsub">${esc(W.leftOver(eur0(f.best_month.left_over_eur)))}</p>
     <div class="wk" style="margin-top:28px">${W.tough}</div><div class="wbig sm">${esc(mon(f.toughest_month.month))}</div><p class="wsub">${esc(W.lowest(eur0(f.toughest_month.lowest_balance_eur)))}</p>${cap("months")}`,
    `<div class="wbig">${f.no_spend_days}</div><p class="wsub">${W.noSpend}</p><p class="wsub">${esc(W.streak(f.longest_no_spend_streak_days))}</p>${cap("no_spend")}`,
    f.payday_week_change_percent != null ? `<div class="wbig">${f.payday_week_change_percent > 0 ? "+" : ""}${f.payday_week_change_percent} %</div><p class="wsub">${W.payday}</p>${cap("payday")}` : null,
    f.twins ? (() => { const t = f.twins, me = t.your_extras_per_month_eur, them = t.their_extras_per_month_eur, mx = Math.max(me, them, 1);
      return `<div class="wk">${esc(W.twins(t.twins_who_never_went_below_zero))}</div>
      <div class="wtw"><div><span>${W.youX}</span><i style="width:${(me / mx) * 100}%"></i><b>${eur0(me)}</b></div>
      <div><span>${W.themX}</span><i class="th" style="width:${(them / mx) * 100}%"></i><b>${eur0(them)}</b></div></div>
      <p class="wsub">${W.extrasMonth}</p><p class="wsub">${esc(W.visits(t.your_eat_out_visits_per_month, t.their_eat_out_visits_per_month))}</p>${cap("twins")}`; })() : null,
    `<div class="wk">${W.score}</div><div class="ring big w" style="background:conic-gradient(#fff ${f.rahakunto.score * 3.6}deg, rgba(255,255,255,.2) 0)"><span>${f.rahakunto.score}</span></div>
     <p class="wsub">${esc(E().hk.tiers[f.rahakunto.tier])}</p>`,
    `<div class="wk">${W.next}</div>${f.next_step ? `<h2>${esc(stepText(f.next_step))}</h2>` : ""}${cap("next")}
     <div class="wact"><button class="wshare">${W.share}</button><button class="wdone">${W.done}</button></div>`,
  ].filter(Boolean);
  let i = 0;
  const bars = root.querySelector(".wbars"), sl = root.querySelector(".wslide");
  const show = () => {
    bars.innerHTML = slides.map((_, k) => `<i class="${k <= i ? "on" : ""}"></i>`).join("");
    sl.innerHTML = slides[i] + (i < slides.length - 1 ? `<p class="wtap">${W.tap}</p>` : "");
    sl.classList.remove("in"); void sl.offsetWidth; sl.classList.add("in");
    const sh = sl.querySelector(".wshare");
    if (sh) sh.onclick = async (e) => { e.stopPropagation(); const text = W.shareText(f);
      try { if (navigator.share) await navigator.share({ text }); else { await navigator.clipboard.writeText(text); toast("✓"); } } catch {} };
    const dn = sl.querySelector(".wdone"); if (dn) dn.onclick = (e) => { e.stopPropagation(); root.remove(); };
  };
  sl.onclick = (e) => { const x = e.clientX / window.innerWidth; i = x < 0.3 ? Math.max(0, i - 1) : Math.min(slides.length - 1, i + 1); show(); };
  show();
}

function stepText(st) {
  const h = E().hk.steps;
  if (st.part === "spend") return h[st.target](eur0(st.gap_eur_month));
  if (st.part === "on_time") return h.on_time(eur0(st.gap_eur));
  if (st.part === "buffer") return h.buffer(eur0(st.gap_eur), st.target_months);
  return h.long_term(eur0(st.gap_eur_month));
}

function healthSheet() {
  const hk = home.health, H = E().hk, t = Math.abs(Math.round(hk.trend_points));
  const tone = typeof H.tones[hk.tone] === "function" ? H.tones[hk.tone](t) : H.tones[hk.tone];
  const bars = Object.entries(hk.parts).map(([k, v]) => `<li><span>${esc(H.parts[k])}</span>${v === null
    ? `<div class="hb unk"><i></i></div><b>?</b>` : `<div class="hb"><i style="width:${v}%"></i></div><b>${v}</b>`}</li>`).join("");
  const steps = hk.steps.map((st) => { const tx = stepText(st);
    return `<button class="hstep" data-ask="${esc(H.askQ(tx))}"><span>${esc(tx)}</span><b>${H.points(Math.round(st.points))}</b></button>`; }).join("");
  const s = sheet(`<div class="hhead"><div class="ring big" style="background:conic-gradient(var(--g700) ${hk.score * 3.6}deg, var(--g100) 0)"><span>${hk.score}</span></div>
    <div><h2>${H.name}</h2><div class="sub">${H.tiers[hk.tier]} · ${hk.trend_points >= 0 ? "+" : "−"}${t}</div></div></div>
    <p class="lead">${esc(tone)}</p><ul class="hbars">${bars}</ul>
    ${steps ? `<div class="label" style="margin:14px 2px 8px">${H.next}</div>${steps}` : ""}
    <p class="note left">${esc(H.unknown(hk.coverage))}. ${esc(H.method)}</p>`);
  s.querySelectorAll("[data-ask]").forEach((b) => b.addEventListener("click", () => { closeSheet(); ask(b.dataset.ask); }));
}

function rulesSheet() {
  const rows = Object.values(liveSt.rules).map((r) => `<li><div class="rh"><b>${esc(r.label)}</b><span>${r.status === "confirmed" ? `${r.value} ${esc(r.unit)}` : E().unknown}</span></div>
    <div class="rs">${r.source_url ? `<a href="${esc(r.source_url)}" target="_blank" rel="noopener">${esc(host(r.source_url))}</a>` : ""}
    ${r.source_date ? ` · ${esc(E().asOf(r.source_date))}` : ""}${r.fetched_at ? ` · ${esc(E().fetchedAt(when(r.fetched_at)))}` : ""}
    ${r.key === "loan_cap_general" && r.status === "confirmed" && !r.effective_from ? ` · <i>${E().effUnknown}</i>` : ""}</div></li>`).join("");
  const mons = Object.entries(liveSt.monitors || {});
  const s = sheet(`<h2>${E().rulesTitle}</h2><ul class="rules">${rows}</ul><p class="note left">${E().sourceOnly}</p>
    <div class="label" style="margin:14px 4px 8px">${E().demo}</div>
    <div class="actions"><button class="btn ghost" data-re>${E().recheck}</button>
    ${mons.length ? mons.map(([k, m]) => `<button class="btn ghost" data-run="${esc(k)}">${E().runMon(esc(k.replace("_", " ")))}</button>`).join("")
      : `<button class="btn ghost" data-setup>${E().setupMon}</button>`}</div><p class="omsg" data-out></p>`);
  const out = s.querySelector("[data-out]");
  const call = async (url, msg) => {
    out.innerHTML = `<span class="typing"><i></i><i></i><i></i></span>`;
    const r = await fetch(url, { method: "POST" });
    if (!r.ok) { out.textContent = r.status === 503 ? E().notConnected : E().failed; return; }
    const j = await r.json(); out.textContent = msg(j);
    liveSt = await api("/api/live/status"); window.renderHomeE();
  };
  s.querySelector("[data-re]").addEventListener("click", () => call("/api/live/rules/refresh", () => "✓"));
  s.querySelectorAll("[data-run]").forEach((b) => b.addEventListener("click", () => call(`/api/live/monitors/${b.dataset.run}/run`,
    (j) => `${j.status}${j.change_detected ? ` · ${j.before ?? "?"} → ${j.after ?? "?"}` : ""}`)));
  const st = s.querySelector("[data-setup]"); if (st) st.addEventListener("click", () => call("/api/live/monitors/setup", () => "✓"));
}

window.renderHomeE = async function () {
  const o = home.overview, r = home.ribbon;
  $("#greet").textContent = `${persona().name} · ${day(o.customer.as_of)}`;
  const [whole, dec] = nf(2).format(o.customer.balance).split(/[.,](?=\d{2}$)/);
  const ch = o.customer.balance - r.past[0].balance_eur;
  $("#balance").innerHTML = `${esc(whole)}<small>${lang === "en" ? "." : ","}${esc(dec)} €</small><span class="delta">${esc(E().since(`${ch < 0 ? "−" : "+"}${eur0(Math.abs(ch))}`))}</span>`;
  if (!fut || fut.cid !== cid) { fut = await api(`/api/future/${cid}`); fut.cid = cid; active = null; scen = null; picked = null; buyRes = null; }
  if (!liveSt) { try { liveSt = await api("/api/live/status"); } catch { liveSt = null; } }
  notes = null;
  $("#view-home").innerHTML = `<section id="hero"></section>` + strip();
  redraw();
  bindAsks($("#view-home"));
  $("#view-home").querySelectorAll("[data-act=pot]").forEach((b) => b.addEventListener("click", potSheet));
  $("#view-home").querySelectorAll("[data-act=psd2]").forEach((b) => b.addEventListener("click", psd2Sheet));
  $("#view-home").querySelectorAll("[data-rules]").forEach((b) => b.addEventListener("click", rulesSheet));
  $("#view-home").querySelectorAll("[data-health]").forEach((b) => b.addEventListener("click", healthSheet));
  $("#view-home").querySelectorAll("[data-wrapped]").forEach((b) => b.addEventListener("click", openWrapped));
  const fc = home.cards.find((c) => c.id === "forecast");
  if (fc && !notifShown[cid]) { notifShown[cid] = true; showNotif(fc); }
  const want = `${cid}:${lang}`;
  api(`/api/notes/${cid}?lang=${lang}`).then((n) => { if (`${cid}:${lang}` === want) { notes = n; redraw(); } }).catch(() => {});
};
