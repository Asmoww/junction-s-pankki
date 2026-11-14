// Design E v2: the future as a graph. Code draws every number; the AI annotates the line and turns
// "what if…" sentences into scenarios that redraw the future. Loaded after app.js on /e.
const ES = {
  en: { euOn: "AI in Finland", euOff: "AI: Claude", euToast: (l) => `AI now runs on ${l}, an open model hosted in Finland. Numbers still come from code.`, claudeToast: "AI now runs on Claude.", pl: { card: "Play your next two weeks", cardB: "Can you reach payday above zero?", go: "Play", title: "Your next two weeks",
      onPayday: (d) => `On payday, ${d}`, usual: (v) => `At your usual pace: ${v}`, goal: "Reach payday above zero", rules: "Your likely days, one card at a time. The three baskets are the rules:",
      r1: "Fixed must-pays can't be skipped. Rent can be moved.", r2: "The surprise buffer stays: surprises come anyway.", r3: "Everyday extras are your choice: keep or skip.",
      tryTip: (v) => `Try the coach's plan (${v})`, start: (n) => `Play it myself · ${n} cards`, groceries: "Groceries and commuting", surprises: "Surprise buffer",
      rent: "Rent", bills: "Bills", rest: "Everything else, small buys", wholePeriod: "Until payday", hours: (h) => `= ${h} h of your work`,
      ruleExtra: "An everyday extra: your choice. Swipe or tap.", ruleBuffer: "The dentist, a broken phone: surprises come anyway, so this stays.",
      ruleFixed: "A fixed must-pay: it can't be skipped.", ruleRent: "You can't skip rent, but you can ask to pay it after payday.",
      skip: "Skip", keep: "Keep", move: "Pay after payday", payOnTime: "Pay on time", ok: "OK", win: "You made it to payday", lose: "Still short on payday",
      skipped: "Extras skipped", rentMoved: "Rent moved", yes: "Yes", no: "No", showGraph: "Show on my graph", again: "Play again", altLine: (p, src) => `An HSL 30-day ticket costs ${p} today (${src})`, swapBtn: (p) => `Swap parking and taxis for an HSL ticket, ${p}`, swapNote: (d, src) => `30 days, until ${d} · price read live from ${src}`, swappedT: "Swapped to a ticket", planLabel: "Your two-week plan" },
    so: { card: "Your three baskets", cardB: "Where does your money really go?", go: "Sort yours with the AI", loading: "Finding the spending only you can sort…",
      none: "Nothing unclear to sort right now.", title: "Sort your money", intro: "Everything you spend lands in one of three baskets. We sorted most of it; a few things only you can sort.",
      start: (n) => `Start · ${n} questions`, habit: (n, t) => `${n} times · ${t} in 12 months`, now: (b) => `Counted now as: ${b}`, next: "Next",
      see: "See what changed", working: "Re-sorting your money…", resultT: "Your money, re-sorted", year: "Last 12 months", week: "Safe this week",
      payday: "Safe until payday", everywhere: "Your answers now count everywhere: the graph, safe-to-spend and the coach.", done: "Done", ask: "Ask the coach",
      askQ: "What do my three baskets say about my money now?", undo: "Undo my answers" },
    wr: { card: "Your money year", open: "Watch", title: (n) => `${n}, your money year`, inOut: (i, o) => `Money in ${i} · out ${o}`,
      baskets: "Where it went", habit: "Your number-one habit", meals: "meals out", hours: (h) => `= ${h} hours of your work`,
      bigDay: "Your biggest day", best: "Best month", tough: "Toughest month", leftOver: (a) => `${a} left over`, lowest: (a) => `lowest ${a}`,
      noSpend: "no-spend days", streak: (d) => `longest streak ${d} days`, payday: "more on extras the week after payday",
      twins: (n) => `${n} people like you never went below zero`, youX: "You", themX: "Them", extrasMonth: "Extras a month",
      visits: (a, b) => `Eating out: they ${b}, you ${a} times a month`, score: "Rahakunto", next: "One thing for next year",
      share: "Share image", done: "Done", shareText: (f) => `My money year: ${f.no_spend_days} no-spend days, a ${f.longest_no_spend_streak_days}-day streak and ${f.eat_out.visits} meals out. #MoneyWrapped`,
      tap: "Tap to continue", scoreWhat: "Your money fitness out of 100, from four habits.", sumK: "Your year in one picture", posterTitle: "My money\nyear", posterTag: "#MoneyWrapped", pTop: "Top extra", pNoSpend: "No-spend days", pStreak: "Longest streak", pDays: (d) => `${d} days`, pPlus: "Months in plus", pMeals: "Meals out", pType: "Money type", pBest: "Best month", twinsHead: (a) => `people aged ${a} with pay like yours never went below zero`, youBelow: (d) => d ? `You were below zero on ${d} days.` : "Neither did you.", eatTimes: "Meals out a month", eatEur: "Eating out a month", ateK: "Eating out cost you", workDays: "working days", ateSub: (n, e, h) => `${n} meals · ${e} · ${h} hours of your pay`, plusMonths: "months ended with money left over", guessK: "Quick guess", guessQ: "Which extra cost you the most this year?", right: "Spot on.",
      wrong: (x, n) => `It was ${x}: ${n} times.`, inL: "In", outL: "Out", monthsK: "What was left each month", bestIn: (m) => `Best: ${m}`,
      otherWeeks: "Other weeks", paydayWeek: "Payday week" },
    hk: { name: "Rahakunto", tiers: { vulnerable: "Vulnerable", coping: "Coping", healthy: "Healthy" },
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
    capShort: "Loan cap", euriborShort: "Euribor 12 m",
    since: (a) => `${a} since payday`, today: "Today", pay: "Payday", forecast: "forecast", extras: "your extras",
    payResult: (d) => `On payday, ${d}`, whatIf: "What if…", whatIfPh: "e.g. concert tickets 150 € on Friday",
    pause: "Pause extras", eatLess: "Eat out −50 %", rentLater: "Rent after payday", ask: (d) => `Ask about ${d}`,
    askQ: (d) => `What did I spend on ${d}, and was it a lot for me?`, thinking: "Reading your words…",
    aiNote: "Notes written by AI from your numbers", noAmount: "Tell me an amount, e.g. 150 €.", failed: "Couldn't do that one. Try again.",
    bills: { Housing: "Rent", Utilities: "Bills" }, nothing: "No spending",
    cards: { safe: "Safe this week", month: (m) => m, payday: "After payday", pot: "Surprises", fin: "vs Finland", psd2: "Other bank" },
    perMonth: "a month", vsFin: (a) => `${a} in Finland`, moved: "moved away" },
  fi: { euOn: "Tekoäly Suomessa", euOff: "Tekoäly: Claude", euToast: (l) => `Tekoäly toimii nyt mallilla ${l}, avoin malli Suomessa. Luvut tulevat yhä koodista.`, claudeToast: "Tekoäly toimii nyt Claudella.", pl: { card: "Pelaa kaksi seuraavaa viikkoa", cardB: "Pääsetkö palkkapäivään plussalla?", go: "Pelaa", title: "Kaksi seuraavaa viikkoasi",
      onPayday: (d) => `Palkkapäivänä ${d}`, usual: (v) => `Tavallisella tahdilla: ${v}`, goal: "Pääse palkkapäivään plussalla", rules: "Todennäköiset päiväsi kortti kerrallaan. Kolme koria ovat säännöt:",
      r1: "Kiinteitä pakollisia ei voi ohittaa. Vuokran voi siirtää.", r2: "Yllätyspuskuri pysyy: yllätyksiä tulee joka tapauksessa.", r3: "Arjen extrat ovat sinun valintasi: pidä tai ohita.",
      tryTip: (v) => `Kokeile valmentajan suunnitelmaa (${v})`, start: (n) => `Pelaan itse · ${n} korttia`, groceries: "Ruoka ja työmatkat", surprises: "Yllätyspuskuri",
      rent: "Vuokra", bills: "Laskut", rest: "Kaikki muu, pienet ostot", wholePeriod: "Palkkapäivään asti", hours: (h) => `= ${h} h työtäsi`,
      ruleExtra: "Arjen extra: sinun valintasi. Pyyhkäise tai napauta.", ruleBuffer: "Hammaslääkäri, rikkinäinen puhelin: yllätyksiä tulee joka tapauksessa, joten tämä pysyy.",
      ruleFixed: "Kiinteä pakollinen: sitä ei voi ohittaa.", ruleRent: "Vuokraa ei voi ohittaa, mutta sen maksua voi pyytää siirtämään palkkapäivän jälkeen.",
      skip: "Ohita", keep: "Pidä", move: "Maksa palkan jälkeen", payOnTime: "Maksa ajallaan", ok: "OK", win: "Pääsit palkkapäivään", lose: "Palkkapäivänä yhä miinuksella",
      skipped: "Ohitetut extrat", rentMoved: "Vuokra siirretty", yes: "Kyllä", no: "Ei", showGraph: "Näytä kuvaajassa", again: "Pelaa uudelleen", altLine: (p, src) => `HSL:n 30 päivän lippu maksaa tänään ${p} (${src})`, swapBtn: (p) => `Vaihda pysäköinti ja taksit HSL-lippuun, ${p}`, swapNote: (d, src) => `30 päivää, ${d} asti · hinta luettu suoraan: ${src}`, swappedT: "Vaihdettu lippuun", planLabel: "Kahden viikon suunnitelmasi" },
    so: { card: "Kolme koriasi", cardB: "Mihin rahasi oikeasti menevät?", go: "Lajittele omasi tekoälyn kanssa", loading: "Etsitään menoja, jotka vain sinä voit lajitella…",
      none: "Ei nyt mitään epäselvää lajiteltavaa.", title: "Lajittele rahasi", intro: "Jokainen menosi päätyy yhteen kolmesta korista. Lajittelimme suurimman osan; muutaman asian voit lajitella vain sinä.",
      start: (n) => `Aloita · ${n} kysymystä`, habit: (n, t) => `${n} kertaa · ${t} 12 kuukaudessa`, now: (b) => `Nyt laskettu: ${b}`, next: "Seuraava",
      see: "Katso mikä muuttui", working: "Lajitellaan rahojasi uudelleen…", resultT: "Rahasi uudelleen lajiteltuna", year: "Viimeiset 12 kuukautta", week: "Turvallista tällä viikolla",
      payday: "Turvallista palkkapäivään", everywhere: "Vastauksesi näkyvät nyt kaikkialla: kuvaajassa, turvallisessa summassa ja valmentajassa.", done: "Valmis", ask: "Kysy valmentajalta",
      askQ: "Mitä kolme koriani kertovat rahoistani nyt?", undo: "Peru vastaukseni" },
    wr: { card: "Rahavuotesi", open: "Katso", title: (n) => `${n}, rahavuotesi`, inOut: (i, o) => `Rahaa tuli ${i} · meni ${o}`,
      baskets: "Mihin se meni", habit: "Ykköstapasi", meals: "kertaa ulkona syömässä", hours: (h) => `= ${h} tuntia työtäsi`,
      bigDay: "Suurin päiväsi", best: "Paras kuukausi", tough: "Tiukin kuukausi", leftOver: (a) => `${a} jäi yli`, lowest: (a) => `alimmillaan ${a}`,
      noSpend: "päivää ilman ostoja", streak: (d) => `pisin putki ${d} päivää`, payday: "enemmän extroihin palkkaviikolla",
      twins: (n) => `${n} kaltaistasi ei käynyt kertaakaan miinuksella`, youX: "Sinä", themX: "He", extrasMonth: "Extrat kuussa",
      visits: (a, b) => `Ulkona syöminen: he ${b}, sinä ${a} kertaa kuussa`, score: "Rahakunto", next: "Yksi asia ensi vuodelle",
      share: "Jaa kuva", done: "Valmis", shareText: (f) => `Rahavuoteni: ${f.no_spend_days} päivää ilman ostoja, ${f.longest_no_spend_streak_days} päivän putki ja ${f.eat_out.visits} kertaa ulkona syömässä. #Rahavuosi`,
      tap: "Napauta jatkaaksesi", scoreWhat: "Raha-asioidesi kunto asteikolla 0–100, neljästä tavasta.", sumK: "Vuotesi yhdessä kuvassa", posterTitle: "Minun\nrahavuoteni", posterTag: "#Rahavuosi", pTop: "Ykkösextra", pNoSpend: "Päivää ilman ostoja", pStreak: "Pisin putki", pDays: (d) => `${d} päivää`, pPlus: "Kuukautta plussalla", pMeals: "Kertaa ulkona syömässä", pType: "Rahatyyppi", pBest: "Paras kuukausi", twinsHead: (a) => `${a}-vuotiasta kaltaisellasi palkalla ei käynyt kertaakaan miinuksella`, youBelow: (d) => d ? `Sinä olit miinuksella ${d} päivänä.` : "Et sinäkään.", eatTimes: "Kertaa ulkona kuussa", eatEur: "Ulkona syöminen kuussa", ateK: "Ulkona syöminen maksoi sinulle", workDays: "työpäivää", ateSub: (n, e, h) => `${n} kertaa · ${e} · ${h} tuntia palkkaasi`, plusMonths: "kuukautta päättyi plussalle", guessK: "Arvaa", guessQ: "Mikä extra maksoi sinulle eniten tänä vuonna?", right: "Juuri niin.",
      wrong: (x, n) => `Se oli ${x}: ${n} kertaa.`, inL: "Tuli", outL: "Meni", monthsK: "Mitä jäi kuukausittain", bestIn: (m) => `Paras: ${m}`,
      otherWeeks: "Muut viikot", paydayWeek: "Palkkaviikko" },
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
    capShort: "Lainakatto", euriborShort: "Euribor 12 kk",
    since: (a) => `${a} palkkapäivästä`, today: "Tänään", pay: "Palkka", forecast: "ennuste", extras: "extrasi",
    payResult: (d) => `Palkkapäivänä ${d}`, whatIf: "Entä jos…", whatIfPh: "esim. konserttiliput 150 € perjantaina",
    pause: "Tauko extroille", eatLess: "Ulkona syöminen −50 %", rentLater: "Vuokra palkan jälkeen", ask: (d) => `Kysy päivästä ${d}`,
    askQ: (d) => `Mihin käytin rahaa ${d}, ja oliko se minulle paljon?`, thinking: "Luen pyyntöäsi…",
    aiNote: "Tekoälyn muistiinpanot lukujesi pohjalta", noAmount: "Kerro summa, esim. 150 €.", failed: "Tämä ei onnistunut. Yritä uudelleen.",
    bills: { Housing: "Vuokra", Utilities: "Laskut" }, nothing: "Ei ostoja",
    cards: { safe: "Turvallisesti", month: (m) => m, payday: "Palkan jälkeen", pot: "Yllätykset", fin: "vs Suomi", psd2: "Toinen pankki" },
    perMonth: "kuussa", vsFin: (a) => `Suomessa ${a}`, moved: "siirtyi pois" },
  sv: { euOn: "AI i Finland", euOff: "AI: Claude", euToast: (l) => `AI körs nu på ${l}, en öppen modell i Finland. Siffrorna kommer fortfarande från koden.`, claudeToast: "AI körs nu på Claude.", pl: { card: "Spela dina två nästa veckor", cardB: "Klarar du lönedagen på plus?", go: "Spela", title: "Dina två nästa veckor",
      onPayday: (d) => `På lönedagen ${d}`, usual: (v) => `I din vanliga takt: ${v}`, goal: "Nå lönedagen på plus", rules: "Dina troliga dagar, ett kort i taget. De tre korgarna är reglerna:",
      r1: "Fasta måsten kan inte hoppas över. Hyran kan flyttas.", r2: "Bufferten för överraskningar stannar: de kommer ändå.", r3: "Vardagsextra är ditt val: behåll eller hoppa över.",
      tryTip: (v) => `Prova coachens plan (${v})`, start: (n) => `Spela själv · ${n} kort`, groceries: "Mat och pendling", surprises: "Buffert för överraskningar",
      rent: "Hyra", bills: "Räkningar", rest: "Allt annat, små köp", wholePeriod: "Till lönen", hours: (h) => `= ${h} h av ditt arbete`,
      ruleExtra: "Ett vardagsextra: ditt val. Svep eller tryck.", ruleBuffer: "Tandläkaren, en trasig telefon: överraskningar kommer ändå, så den stannar.",
      ruleFixed: "Ett fast måste: kan inte hoppas över.", ruleRent: "Hyran kan inte hoppas över, men du kan be att få betala efter lönen.",
      skip: "Hoppa över", keep: "Behåll", move: "Betala efter lönen", payOnTime: "Betala i tid", ok: "OK", win: "Du klarade lönedagen", lose: "Fortfarande minus på lönedagen",
      skipped: "Överhoppade extra", rentMoved: "Hyran flyttad", yes: "Ja", no: "Nej", showGraph: "Visa i grafen", again: "Spela igen", altLine: (p, src) => `Ett HSL-kort för 30 dagar kostar ${p} i dag (${src})`, swapBtn: (p) => `Byt parkering och taxi mot ett HSL-kort, ${p}`, swapNote: (d, src) => `30 dagar, till ${d} · priset läst direkt från ${src}`, swappedT: "Bytt till ett kort", planLabel: "Din tvåveckorsplan" },
    so: { card: "Dina tre korgar", cardB: "Vart går dina pengar egentligen?", go: "Sortera dina med AI:n", loading: "Letar efter utgifter som bara du kan sortera…",
      none: "Inget oklart att sortera just nu.", title: "Sortera dina pengar", intro: "Allt du spenderar hamnar i en av tre korgar. Vi sorterade det mesta; några saker kan bara du sortera.",
      start: (n) => `Börja · ${n} frågor`, habit: (n, t) => `${n} gånger · ${t} på 12 månader`, now: (b) => `Räknas nu som: ${b}`, next: "Nästa",
      see: "Se vad som ändrades", working: "Sorterar om dina pengar…", resultT: "Dina pengar, omsorterade", year: "Senaste 12 månaderna", week: "Säkert denna vecka",
      payday: "Säkert till lönen", everywhere: "Dina svar räknas nu överallt: grafen, säkert att spendera och coachen.", done: "Klar", ask: "Fråga coachen",
      askQ: "Vad säger mina tre korgar om mina pengar nu?", undo: "Ångra mina svar" },
    wr: { card: "Ditt pengaår", open: "Titta", title: (n) => `${n}, ditt pengaår`, inOut: (i, o) => `In ${i} · ut ${o}`,
      baskets: "Vart det tog vägen", habit: "Din största vana", meals: "gånger äta ute", hours: (h) => `= ${h} timmar av ditt arbete`,
      bigDay: "Din största dag", best: "Bästa månaden", tough: "Tuffaste månaden", leftOver: (a) => `${a} över`, lowest: (a) => `lägst ${a}`,
      noSpend: "dagar utan köp", streak: (d) => `längsta svit ${d} dagar`, payday: "mer på extra veckan efter lönen",
      twins: (n) => `${n} som du gick aldrig under noll`, youX: "Du", themX: "De", extrasMonth: "Extra i månaden",
      visits: (a, b) => `Äta ute: de ${b}, du ${a} gånger i månaden`, score: "Pengakondition", next: "En sak för nästa år",
      share: "Dela bilden", done: "Klar", shareText: (f) => `Mitt pengaår: ${f.no_spend_days} dagar utan köp, en svit på ${f.longest_no_spend_streak_days} dagar och ${f.eat_out.visits} gånger ute och åt. #Pengaåret`,
      tap: "Tryck för att fortsätta", scoreWhat: "Din pengakondition på 0–100, från fyra vanor.", sumK: "Ditt år i en bild", posterTitle: "Mitt\npengaår", posterTag: "#Pengaåret", pTop: "Största extra", pNoSpend: "Dagar utan köp", pStreak: "Längsta svit", pDays: (d) => `${d} dagar`, pPlus: "Månader på plus", pMeals: "Gånger ute och åt", pType: "Pengatyp", pBest: "Bästa månaden", twinsHead: (a) => `personer i åldern ${a} med lön som din gick aldrig under noll`, youBelow: (d) => d ? `Du var under noll ${d} dagar.` : "Det gjorde inte du heller.", eatTimes: "Gånger ute i månaden", eatEur: "Äta ute i månaden", ateK: "Att äta ute kostade dig", workDays: "arbetsdagar", ateSub: (n, e, h) => `${n} gånger · ${e} · ${h} timmar av din lön`, plusMonths: "månader slutade med pengar kvar", guessK: "Gissa", guessQ: "Vilken extra kostade dig mest i år?", right: "Helt rätt.",
      wrong: (x, n) => `Det var ${x}: ${n} gånger.`, inL: "In", outL: "Ut", monthsK: "Vad som blev över varje månad", bestIn: (m) => `Bäst: ${m}`,
      otherWeeks: "Andra veckor", paydayWeek: "Löneveckan" },
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
    capShort: "Lånetak", euriborShort: "Euribor 12 m",
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
  // Zero is always on the scale, so the line's height means real money: a big balance sits high and flat, a shortfall
  // dips into the red zone. Gridlines carry euro labels.
  let lo = Math.min(0, ...all), hi = Math.max(0, ...all);
  const pad = Math.max(hi - lo, 1) * 0.08; lo -= lo < 0 ? pad : 0; hi += pad;
  const step = (() => { const raw = (hi - lo) / 3, m = 10 ** Math.floor(Math.log10(raw)), f = raw / m; return (f < 1.5 ? 1 : f < 3.5 ? 2 : f < 7.5 ? 5 : 10) * m; })();
  const n = past.length + base.length - 1, iT = past.length - 1;
  const X = (i) => px + (i * (W - 2 * px)) / n, Y = (v) => top + ((hi - v) / (hi - lo)) * (H - top - bot);
  const P = (arr, off) => arr.map((p, k) => [X(off + k), Y(p.balance_eur)]);
  const pPast = P(past, 0), todayPt = pPast[iT];
  const pBase = [todayPt, ...P(base, iT + 1)], pNo = [todayPt, ...P(noext, iT + 1)];
  const neg = fut.base.runs_out, zeroY = Y(0);
  const grid = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) {
    if (Math.abs(v) < step / 2) continue;
    const lab = Math.abs(Y(v) - Y(past[0].balance_eur)) > 16;
    grid.push(`<line class="grid" x1="${px}" x2="${W - px}" y1="${Y(v)}" y2="${Y(v)}"/>${lab ? `<text class="ylab" x="${px + 14}" y="${Y(v) - 4}">${v < 0 ? "−" : ""}${eur0(Math.abs(v))}</text>` : ""}`);
  }
  const band = smooth(pNo) + " L" + [...pBase].reverse().map((q) => q.map((v) => v.toFixed(1)).join(",")).join(" L") + " Z";
  const ticks = [];
  for (let i = 0; i <= n; i += 7) ticks.push(`<text x="${X(i)}" y="${H - 14}" text-anchor="middle" class="tick">${day((past[i] || base[i - past.length]).date)}</text>`);
  const marks = [];
  marks.push(`<g class="mk pay" transform="translate(${pPast[0][0]},${pPast[0][1]})"><circle r="9"/><path d="M0 4V-4M-3.5 -0.5L0 -4 3.5 -0.5"/></g>`);
  // Bills within a few days of each other share one marker and one label ("Rent + bills 1,356 €"), so they never pile up.
  const groups = [];
  for (const b of [...fut.bills].filter((b) => b.date !== fut.next_payday).sort((a, b) => a.date.localeCompare(b.date))) {
    const g = groups.at(-1);
    if (g && (new Date(b.date) - new Date(g.date)) / 864e5 <= 4) { g.names.push(E().bills[b.bill] || b.bill); g.eur += b.eur; }
    else groups.push({ date: b.date, names: [E().bills[b.bill] || b.bill], eur: b.eur });
  }
  for (const g of groups) {
    const i = base.findIndex((q) => q.date === g.date); if (i < 0) continue;
    const [x, y] = pBase[i + 1], neg = base[i].balance_eur < 0, txt = `${g.names.join(" + ")} ${eur0(g.eur)}`;
    const left = x - 8 + txt.length * 7 > W - px;  // under the marker; right-aligned to it near the right edge
    marks.push(`<g class="mk bill ${neg ? "neg" : ""}" transform="translate(${x},${y})"><rect x="-8" y="-8" width="16" height="16" rx="5"/><path d="M-3.5 1.5V-1.5L0 -4 3.5 -1.5V3.5H-3.5Z"/></g>
      <text class="mlab ${neg ? "neg" : ""}" x="${left ? x + 8 : x - 8}" y="${y + 26}" text-anchor="${left ? "end" : "start"}">${esc(txt)}</text>`);
  }
  const end = pBase[pBase.length - 1];
  marks.push(`<g class="mk pay" transform="translate(${end[0]},${end[1]})"><circle r="9"/><path d="M0 4V-4M-3.5 -0.5L0 -4 3.5 -0.5"/></g>`);
  const endV = (sc || base).at(-1).balance_eur, endY = sc ? Y(endV) : end[1];
  marks.push(`<text class="endlab ${endV < 0 ? "neg" : ""}" x="${end[0] + 8}" y="${endY - 16}" text-anchor="end">${endV < 0 ? "−" : ""}${eur0(Math.abs(endV))}</text>`);
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
    ${zeroY < H - bot ? `<rect class="redzone" x="${px}" y="${zeroY}" width="${W - 2 * px}" height="${H - bot - zeroY}"/>` : ""}
    ${grid.join("")}<line class="zero" x1="${px}" x2="${W - px}" y1="${zeroY}" y2="${zeroY}"/><text class="ylab z" x="${px}" y="${zeroY - 4}">0 €</text>
    <path d="${smooth(pPast)} L${todayPt[0]},${zeroY} L${pPast[0][0]},${zeroY} Z" fill="url(#ga)"/>
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

// Money year card: the whole year as a tiny calendar, one dot per day, no-spend days lit (a teaser for Wrapped)
function wrapCard() {
  const y = home.year || { start: "2025-10-01", days: "" }, d0 = new Date(y.start + "T12:00:00");
  let rows = "", k = 0;
  for (let mo = 0; mo < 12 && k < y.days.length; mo++) {
    const n = new Date(d0.getFullYear(), d0.getMonth() + mo + 1, 0).getDate();
    let dots = "";
    for (let dd = 0; dd < n && k < y.days.length; dd++, k++) dots += y.days[k] === "1" ? `<i class="on" style="--d:${k * 2}ms"></i>` : "<i></i>";
    rows += `<span>${dots}</span>`;
  }
  const yr = `${d0.getFullYear()}–${String(d0.getFullYear() + 1).slice(2)}`;
  return `<button class="mini wrapcard" data-wrapped><span class="wtxt"><span class="t">${E().wr.card}</span><b>${yr}</b>
    <span class="go">▶ ${E().wr.open}</span></span><span class="ycal" aria-hidden="true">${rows}</span></button>`;
}

function strip() {
  // Five cards, in order of what helps decide: play the next two weeks, what's safe, surprises, the three baskets, the year.
  // Persona-specific extras only where they belong (PSD2 for the customer whose salary moves away, live rules for the home buyer).
  const o = home.overview, s = o.safe_to_spend, pot = home.pot;
  const cards = [playCard()];
  const days = s.days_until_payday;
  const shortE = s.safe_until_payday_eur < 0;
  cards.push(`<button class="mini ${shortE ? "neg" : ""}" data-ask="${esc(T().suggestions[0])}"><span class="t">${E().cards.safe}</span>
    <b>${shortE ? "−" + eur0(-s.safe_until_payday_eur) : eur0(s.safe_this_week_eur)}</b>
    <span class="s">${shortE ? E().shortBy(day(s.next_payday)) : eur0(s.safe_per_day_eur) + "/" + (lang === "en" ? "day" : lang === "fi" ? "pv" : "dag")}</span>
    <div class="dots">${Array.from({ length: Math.min(days, 15) }, (_, i) => `<i class="${shortE ? "short" : i < 7 ? "wk" : ""}"></i>`).join("")}</div></button>`);
  const mx = Math.max(...pot.months.slice(-12).map((x) => x.eur), 1);
  cards.push(`<button class="mini" data-act="pot"><span class="t">${E().cards.pot}</span><b>${eur0(pot.average_per_month_last_12_eur)}</b><span class="s">${E().perMonth}</span>
    <div class="spark12">${pot.months.slice(-12).map((x) => `<i style="height:${Math.max(4, (x.eur / mx) * 100)}%"></i>`).join("")}<u style="bottom:${(pot.average_per_month_last_12_eur / mx) * 100}%"></u></div></button>`);
  cards.push(sortCard());
  cards.push(wrapCard());
  const psd2 = home.cards.find((c) => c.id === "psd2");
  if (psd2) cards.push(`<button class="mini" data-act="psd2"><span class="t">${E().cards.psd2}</span><b>${eur0(psd2.numbers.moved_to_other_bank_eur)}</b><span class="s">${E().moved}</span>
    <div class="flow"><i style="width:${Math.round(psd2.numbers.share_of_income * 100)}%"></i></div></button>`);
  const homeBuyer = cid === "CUST04138";
  if (liveSt && homeBuyer) {
    const cap = liveSt.rules.loan_cap_general, eu = liveSt.rules.euribor_12m;
    const v = (r) => (r && r.status === "confirmed" ? `${nf(r.unit === "%" ? 3 : 0).format(r.value).replace(/[.,]?0+$/, "")} %` : E().unknown);
    cards.push(`<button class="mini rules" data-rules><span class="t">${E().rules}</span>
      <span class="rl"><span>${E().capShort}</span><b>${v(cap)}</b></span><span class="rl"><span>${E().euriborShort}</span><b>${v(eu)}</b></span>
      <span class="s">${cap && cap.source_url ? esc(host(cap.source_url)) : E().unknown}</span></button>`);
  }
  const lc = homeBuyer && liveSt && liveSt.cards && liveSt.cards[0];
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
const EMOJI = { "Amusement parks": "🎢", "Attractions & museums": "🏛️", "Bars & pubs": "🍺", Books: "📚", "Car rental": "🚗", Cinema: "🎬",
  Clothing: "👕", Electronics: "📱", Fashion: "👗", "Fast food & cafes": "☕", Flights: "✈️", Furniture: "🛋️", Hardware: "🔨", "Home supplies": "🏠",
  Hotels: "🏨", "Kiosks & convenience stores": "🏪", "Other entertainment": "🎟️", "Other home & tech": "🔌", "Other lifestyle": "✨",
  "Other restaurants": "🍽️", "Other shopping": "🛍️", "Other travel": "🧳", Parking: "🅿️", "Recreation & sports": "🏸", Restaurants: "🍽️",
  "Software & apps": "💾", "Sports gear": "👟", Taxis: "🚕", "Theatre & concerts": "🎭", "Toys & games": "🧸", "Travel agencies": "🌴" };
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
  const io = Math.max(f.money_in_eur, f.money_out_eur, 1);
  const hbar = (lbl, v, w, cls = "") => `<div class="wrow"><span>${lbl}</span><div class="wtrack"><i class="${cls}" style="--w:${w}%"></i></div><b>${eur0(v)}</b></div>`;
  // Guess game: the four extras that cost the most, in random order; tapping one reveals the amounts
  const top = f.top_extras || [], opts = [...top].sort(() => Math.random() - 0.5);
  const guess = top.length >= 2 ? `<div class="wk">${W.guessK}</div><h2>${W.guessQ}</h2>
    <div class="wguess">${opts.map((o) => `<button class="wopt" data-sub="${esc(o.merchant_type)}"><span><em>${EMOJI[o.merchant_type] || "🛍️"}</em>${esc(label(o.merchant_type))}</span>
      <i style="--w:${(o.total_eur / top[0].total_eur) * 100}%"></i><b>${eur0(o.total_eur)}</b></button>`).join("")}</div>
    <p class="wres"></p><div class="wlater">${cap("guess")}</div>` : null;
  // Baskets as a ring; the extras basket is the bright one
  const b1 = (f.baskets_eur["1"] / tot) * 100, b2 = b1 + (f.baskets_eur["2"] / tot) * 100;
  const ring = `<div class="wk">${W.baskets}</div><div class="wdonut" style="--a:${b1}%;--b:${b2}%"><span><b>${Math.round(100 - b2)} %</b>${esc(T().baskets[3][0])}</span></div>
    <ul class="wleg">${[1, 2, 3].map((b) => `<li><i class="k${b}"></i>${esc(T().baskets[b][0])}<b>${eur0(f.baskets_eur[b])}</b></li>`).join("")}</ul>${cap("baskets")}`;
  // Eating out, as the work it cost: one block per working day (8 h), the last one partly filled
  const hrs = f.eat_out.hours_of_work, wd = hrs ? hrs / 8 : 0;
  const meals = hrs ? `<div class="wk">${W.ateK}</div><div class="wbig">${Math.round(wd)}</div><p class="wsub strong">${W.workDays}</p>
    <div class="wdays">${Array.from({ length: Math.ceil(wd) }, (_, k) => `<i style="--f:${Math.min(1, wd - k) * 100}%;--d:${k * 40}ms"></i>`).join("")}</div>
    <p class="wsub">${esc(W.ateSub(f.eat_out.visits, eur0(f.eat_out.total_eur), hrs))}</p>${cap("habit")}`
    : `<div class="wk">${W.habit}</div><div class="wbig">${f.eat_out.visits}</div><p class="wsub">${W.meals} · ${eur0(f.eat_out.total_eur)}</p>${cap("habit")}`;
  // Month by month: how many months ended with money left, then the bars (zero placed where the data needs it)
  const ms = f.months || [], pos = Math.max(0, ...ms.map((m) => m.left_over_eur)), neg = Math.max(0, ...ms.map((m) => -m.left_over_eur));
  const span = pos + neg || 1, zero = (pos / span) * 100, plus = ms.filter((m) => m.left_over_eur > 0).length;
  const best = ms.reduce((a, m) => (m.left_over_eur > a.left_over_eur ? m : a), ms[0] || { left_over_eur: 0 });
  const months = ms.length ? `<div class="wbig">${plus}<small>/${ms.length}</small></div><p class="wsub strong">${W.plusMonths}</p>
    <div class="wcols2" style="--z:${zero}%">${ms.map((m) => {
      const h = (Math.abs(m.left_over_eur) / span) * 100, ng = m.left_over_eur < 0;
      return `<div class="wc${m === best ? " best" : ""}${ng ? " ng" : ""}" style="--h:${h}%">${m === best ? `<em>${eur0(m.left_over_eur)}</em>` : ""}<i></i></div>`; }).join("")}</div>
    <div class="wmon">${ms.map((m) => `<span>${esc(new Date(m.month + "-15T12:00:00").toLocaleDateString(T().locale, { month: "narrow" }))}</span>`).join("")}</div>
    <p class="wsub">${esc(W.bestIn(mon(best.month)))}</p>${cap("months")}` : null;
  // Calendar: one row per month, a lit dot for every day without spending
  const cal = f._calendar || "", d0 = new Date(f.period.start + "T12:00:00");
  let st0 = -1, stL = 0;  // the longest run of no-spend days, highlighted on the calendar
  for (let k = 0, run = 0; k < cal.length; k++) { run = cal[k] === "1" ? run + 1 : 0; if (run > stL) { stL = run; st0 = k - run + 1; } }
  let rows = "", k = 0;
  for (let mo = 0; mo < 12 && k < cal.length; mo++) {
    const dt = new Date(d0.getFullYear(), d0.getMonth() + mo, 1, 12), n = new Date(dt.getFullYear(), dt.getMonth() + 1, 0).getDate();
    let dots = "";
    for (let dd = 0; dd < n && k < cal.length; dd++, k++) dots += cal[k] === "1" ? `<i class="on${k >= st0 && k < st0 + stL ? " st" : ""}" style="--d:${k * 3}ms"></i>` : "<i></i>";
    rows += `<div class="wcal-r"><span>${esc(dt.toLocaleDateString(T().locale, { month: "narrow" }))}</span>${dots}</div>`;
  }
  const nospend = `<div class="wbig">${f.no_spend_days}</div><p class="wsub">${W.noSpend}</p><div class="wcal">${rows}</div>
    <p class="wsub"><span class="stkey"></span>${esc(W.streak(f.longest_no_spend_streak_days))}</p>${cap("no_spend")}`;
  // Payday week vs the other weeks, as two bars
  const pp = f.payday_week_change_percent, pmx = Math.max(100, 100 + (pp || 0));
  const payday = pp != null && pp >= 10 ? `<div class="wbig">+${pp} %</div><p class="wsub">${W.payday}</p>
    <div class="wvs"><div><i style="--h:${(100 / pmx) * 100}%"></i><span>${W.otherWeeks}</span></div><div><i class="hi" style="--h:${((100 + pp) / pmx) * 100}%"></i><span>${W.paydayWeek}</span></div></div>${cap("payday")}` : null;
  // Twins: people like you who never went below zero, compared on three habits
  const twins = f.twins ? (() => { const t = f.twins;
    const row = (em, l, me, them, fmt) => { const mx = Math.max(me, them, 1);
      return `<div class="wcmp"><div class="wcl"><em>${em}</em>${l}</div>
        <div class="wrow"><span>${W.youX}</span><div class="wtrack"><i style="--w:${(me / mx) * 100}%"></i></div><b>${fmt(me)}</b></div>
        <div class="wrow"><span>${W.themX}</span><div class="wtrack"><i class="th" style="--w:${(them / mx) * 100}%"></i></div><b>${fmt(them)}</b></div></div>`; };
    const n1 = (x) => nf(1).format(x);
    return `<div class="wbig">${t.twins_who_never_went_below_zero}</div><p class="wsub strong">${esc(W.twinsHead(t.age_group))}</p>
      <p class="wsub">${esc(W.youBelow(t.your_days_below_zero))}</p>
      ${row("🛍️", W.extrasMonth, t.your_extras_per_month_eur, t.their_extras_per_month_eur, eur0)}
      ${row("🍽️", W.eatTimes, t.your_eat_out_visits_per_month, t.their_eat_out_visits_per_month, n1)}
      ${row("💶", W.eatEur, t.your_eat_out_eur_per_month, t.their_eat_out_eur_per_month, eur0)}${cap("twins")}`; })() : null;
  const poster = await drawPoster(f, W, { top: top[0], best: (f.months || []).reduce((a, m) => (!a || m.left_over_eur > a.left_over_eur ? m : a), null)?.month, plus: (f.months || []).filter((m) => m.left_over_eur > 0).length, months: (f.months || []).length });
  const slides = [
    `<div class="wk">${esc(day(f.period.start))} – ${esc(day(f.period.end))}</div><h1>${esc(W.title(f.name || ""))}</h1>
     <div class="wtw">${hbar(W.inL, f.money_in_eur, (f.money_in_eur / io) * 100)}${hbar(W.outL, f.money_out_eur, (f.money_out_eur / io) * 100, "th")}</div>${cap("year")}`,
    guess, ring, meals, months, nospend, payday, twins,
    `<div class="wk">${W.score}</div>
     <div class="whk"><div class="ring big w" style="background:conic-gradient(var(--fg) ${f.rahakunto.score * 3.6}deg, var(--soft) 0)"><span>${f.rahakunto.score}</span></div>
       <div><b>${esc(E().hk.tiers[f.rahakunto.tier])}</b><p>${W.scoreWhat}</p></div></div>
     <ul class="wparts">${Object.entries(f.rahakunto.parts || {}).map(([k, v]) => `<li><span>${esc(E().hk.parts[k])}</span>
       <div class="wtrack"><i style="--w:${v ?? 0}%"></i></div><b>${v ?? "?"}</b></li>`).join("")}</ul>
     ${f.next_step ? `<div class="wgoal"><em>🎯</em><div><span>${W.next}</span><b>${esc(stepText(f.next_step))}</b></div></div>` : ""}${cap("next")}`,
    `<div class="wk">${W.sumK}</div><img class="wposter" alt="${esc(W.sumK)}" src="${poster.url}">
     <div class="wact"><button class="wshare">${W.share}</button><button class="wdone">${W.done}</button></div>`,
  ].filter(Boolean);
  let i = 0;
  const bars = root.querySelector(".wbars"), sl = root.querySelector(".wslide");
  const show = () => {
    root.classList.toggle("light", i % 2 === 1);
    bars.innerHTML = slides.map((_, k) => `<i class="${k <= i ? "on" : ""}"></i>`).join("");
    sl.innerHTML = slides[i] + (i < slides.length - 1 ? `<p class="wtap">${W.tap}</p>` : "");
    sl.classList.remove("in"); void sl.offsetWidth; sl.classList.add("in");
    const sh = sl.querySelector(".wshare");
    if (sh) sh.onclick = async (e) => { e.stopPropagation(); const text = W.shareText(f);
      const file = new File([poster.blob], "money-year.png", { type: "image/png" });
      try {
        if (navigator.canShare && navigator.canShare({ files: [file] })) await navigator.share({ files: [file], text });
        else { const a = document.createElement("a"); a.href = poster.url; a.download = "money-year.png"; a.click(); toast("✓"); }
      } catch {} };
    const dn = sl.querySelector(".wdone"); if (dn) dn.onclick = (e) => { e.stopPropagation(); root.remove(); };
  };
  sl.onclick = (e) => {
    const x = e.clientX / window.innerWidth, g = sl.querySelector(".wguess");
    const opt = e.target.closest(".wopt");
    if (g && !g.classList.contains("shown")) {  // the guess slide waits for a guess before moving on
      if (opt) {
        const right = opt.dataset.sub === top[0].merchant_type;
        g.classList.add("shown"); opt.classList.add(right ? "right" : "wrong");
        g.querySelector(`[data-sub="${CSS.escape(top[0].merchant_type)}"]`).classList.add("right");
        sl.querySelector(".wres").textContent = right ? W.right : W.wrong(label(top[0].merchant_type), top[0].times);
        sl.querySelector(".wlater").classList.add("on");
        return;
      }
      if (x >= 0.3) return;
    }
    i = x < 0.3 ? Math.max(0, i - 1) : Math.min(slides.length - 1, i + 1); show();
  };
  show();
}

// The shareable summary: a story-size image with the year's highlights and no amounts (nothing private in a share)
async function drawPoster(f, W, x) {
  await Promise.all(["700 100px Geologica", "500 40px Geologica"].map((q) => document.fonts.load(q).catch(() => null)));
  const c = document.createElement("canvas"); c.width = 1080; c.height = 1920;
  const g = c.getContext("2d"), G = "#00843d", D = "#003d25";
  g.fillStyle = G; g.fillRect(0, 0, 1080, 1920);
  g.fillStyle = "#ffffff"; g.globalAlpha = 0.08; g.beginPath(); g.arc(980, 180, 300, 0, 7); g.fill(); g.globalAlpha = 1;
  g.fillStyle = "#c9f0d8"; g.font = "500 42px Geologica"; g.fillText(`${day(f.period.start)} – ${day(f.period.end)}`, 90, 190);
  g.fillStyle = "#fff"; g.font = "700 118px Geologica";
  W.posterTitle.split("\n").forEach((ln, k) => g.fillText(ln, 84, 340 + k * 124));
  g.beginPath(); g.roundRect(60, 590, 960, 1110, 56); g.fill();
  const rows = [
    ["🏆", W.pTop, x.top ? label(x.top.merchant_type) : "–"],
    ["🌱", W.pNoSpend, String(f.no_spend_days)],
    ["🔥", W.pStreak, W.pDays(f.longest_no_spend_streak_days)],
    ["📈", W.pPlus, `${x.plus}/${x.months}`],
    ["🍽️", W.pMeals, String(f.eat_out.visits)],
    ["🧭", W.pType, (T().types[f.spender_type] || [f.spender_type || "–"])[0]],
    ["☀️", W.pBest, x.best ? new Date(x.best + "-15T12:00:00").toLocaleDateString(T().locale, { month: "long" }) : "–"],
  ];
  rows.forEach(([em, l, v], k) => {
    const y = 600 + k * 155;
    if (k) { g.fillStyle = "#e3f1e8"; g.fillRect(110, y, 860, 3); }
    g.font = "64px sans-serif"; g.textBaseline = "middle"; g.fillText(em, 110, y + 78);
    g.fillStyle = "#5d7a68"; g.font = "500 34px Geologica"; g.fillText(l, 220, y + 52);
    g.fillStyle = D; g.font = "700 52px Geologica"; g.fillText(v, 220, y + 106); g.textBaseline = "alphabetic";
  });
  g.fillStyle = "#fff"; g.font = "700 46px Geologica"; g.fillText(W.posterTag, 90, 1810);
  const blob = await new Promise((r) => c.toBlob(r, "image/png"));
  return { blob, url: URL.createObjectURL(blob) };
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

// EU mode switch in the header: shown only when an EU-hosted open model is configured on the server
async function aiSwitch() {
  if (!window.aiInfo) { try { window.aiInfo = await api("/api/ai"); } catch { window.aiInfo = { eu: { configured: false }, voice: false }; } }
  const eu = window.aiInfo.eu, head = $("#lang").parentElement;
  if (!eu.configured || head.querySelector("#aichip")) return;
  const b = document.createElement("button"); b.id = "aichip"; b.className = "aichip";
  const paint = () => { const on = aiProvider() === "eu"; b.classList.toggle("on", on); b.textContent = on ? `🇪🇺 ${E().euOn}` : E().euOff; };
  b.onclick = () => {
    localStorage.setItem("ai", aiProvider() === "eu" ? "claude" : "eu"); paint();
    toast(esc(aiProvider() === "eu" ? E().euToast(eu.label) : E().claudeToast), 5000);
    fut = null; load();
  };
  head.insertBefore(b, $("#lang")); paint();
}

window.renderHomeE = async function () {
  aiSwitch();
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
  $("#view-home").querySelectorAll("[data-sort]").forEach((b) => b.addEventListener("click", openSort));
  $("#view-home").querySelectorAll("[data-play]").forEach((b) => b.addEventListener("click", openPlay));
  const fc = home.cards.find((c) => c.id === "forecast");
  if (fc && !notifShown[cid]) { notifShown[cid] = true; showNotif(fc); }
  const want = `${cid}:${lang}`;
  api(`/api/notes/${cid}?lang=${lang}`).then((n) => { if (`${cid}:${lang}` === want) { notes = n; redraw(); } }).catch(() => {});
};

// ---------------------------------------------------------------- Sort with the AI (the three baskets, your own spending)
function sortCard() {
  const S = E().so;
  return `<button class="mini sortcard" data-sort><span class="t">${S.card}</span><b>${S.cardB}</b>
    ${home && home.overview ? (() => { const m = home.overview.month, t = m.total_spending_eur || 1;
      return `<span class="seg big">${m.baskets.map((b) => `<i style="flex:${b.total_eur / t};background:${BASKET_COLORS[b.basket]}"></i>`).join("")}</span>`; })() : ""}
    <span class="b3">${[1, 2, 3].map((b) => `<span><i style="background:${BASKET_COLORS[b]}"></i>${esc(T().baskets[b][0])}</span>`).join("")}</span>
    <span class="go">${SPARK}${S.go} ›</span></button>`;
}

async function openSort() {
  const S = E().so, wait = (t) => `<div class="swait"><span class="typing"><i></i><i></i><i></i></span><p class="sub">${t}</p></div>`;
  const s = sheet(`<div class="sort">${wait(S.loading)}</div>`), box = s.querySelector(".sort");
  let d; try { d = await api(`/api/sort/${cid}?lang=${lang}`); } catch { d = { cards: [] }; }
  if (!d.cards.length) { box.innerHTML = `<p class="lead">${S.none}</p>`; return; }
  const ans = {}, cards = d.cards;
  let i = 0;
  const meta = (c) => (c.kind === "habit" ? S.habit(c.times, eur0(c.total_eur)) : `${eur0(c.amount_eur)} · ${esc(day(c.date))}`);
  const intro = () => {
    box.innerHTML = `<h2>${S.title}</h2><p class="lead">${S.intro}</p>
      <ul class="b3l">${[1, 2, 3].map((b) => `<li><i style="background:${BASKET_COLORS[b]}"></i><div><b>${esc(T().baskets[b][0])}</b><span>${esc(T().baskets[b][1])}</span></div></li>`).join("")}</ul>
      <button class="btn" data-go>${S.start(cards.length)}</button>`;
    box.querySelector("[data-go]").onclick = card;
  };
  const card = () => {
    const c = cards[i], last = i === cards.length - 1;
    box.innerHTML = `<div class="sdots">${cards.map((_, k) => `<i class="${k < i ? "done" : k === i ? "on" : ""}"></i>`).join("")}</div>
      <div class="smeta"><b>${esc(label(c.merchant_type))}</b><span>${meta(c)}</span></div>
      <p class="snow">${esc(S.now(T().baskets[c.data_basket][0]))}</p>
      ${c.live_alternative ? `<p class="salt">🚌 ${esc(E().pl.altLine(eur(c.live_alternative.price_eur), host(c.live_alternative.source_url)))}</p>` : ""}
      <p class="sq">${SPARK}<span>${esc(c.question)}</span></p>
      <div class="sans">${[1, 2, 3].map((b) => `<button data-b="${b}"><i style="background:${BASKET_COLORS[b]}"></i><span>${esc(c.answers[b])}<small>${esc(T().baskets[b][0])}</small></span></button>`).join("")}</div>
      <div class="slesson"></div>`;
    box.querySelectorAll("[data-b]").forEach((btn) => btn.addEventListener("click", () => {
      if (ans[c.id]) return;
      ans[c.id] = +btn.dataset.b;
      box.querySelector(".sans").classList.add("picked"); btn.classList.add("on");
      box.querySelector(".slesson").innerHTML = `<p class="sq les">${SPARK}<span>${esc(c.lesson)}</span></p><button class="btn" data-next>${last ? S.see : S.next}</button>`;
      box.querySelector("[data-next]").onclick = () => { if (last) submit(); else { i++; card(); } };
    }));
  };
  const submit = async () => {
    box.innerHTML = wait(S.working);
    let r;
    try { r = await api(`/api/sort/${cid}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ answers: ans, lang }) }); }
    catch { box.innerHTML = `<p class="lead">${T().wentWrong}</p>`; return; }
    result(r);
  };
  const refresh = async () => { closeSheet(); fut = null; await load(); };
  const result = (r) => {
    const mx = Math.max(...[1, 2, 3].flatMap((b) => [r.before.baskets_eur[b], r.after.baskets_eur[b]]), 1);
    const rows = [1, 2, 3].map((b) => {
      const a = r.before.baskets_eur[b], z = r.after.baskets_eur[b], dl = z - a;
      return `<li><div class="rh"><span><i style="background:${BASKET_COLORS[b]}"></i>${esc(T().baskets[b][0])}</span>
        <b>${eur0(z)}${Math.abs(dl) >= 1 ? ` <em>${dl > 0 ? "+" : "−"}${eur0(Math.abs(dl))}</em>` : ""}</b></div>
        <div class="rb"><i class="was" style="width:${(a / mx) * 100}%"></i><i class="now" style="width:${(z / mx) * 100}%;background:${BASKET_COLORS[b]}"></i></div></li>`;
    }).join("");
    const chg = (k, l) => `<div><span>${l}</span><b>${r.before[k] === r.after[k] ? eur0(r.after[k]) : `${eur0(r.before[k])} → ${eur0(r.after[k])}`}</b></div>`;
    box.innerHTML = `<h2>${S.resultT}</h2>${r.takeaway ? `<p class="sq">${SPARK}<span>${esc(r.takeaway)}</span></p>` : ""}
      <div class="label">${S.year}</div><ul class="sres">${rows}</ul>
      <div class="sch">${chg("safe_this_week_eur", S.week)}${chg("safe_until_payday_eur", S.payday)}</div>
      <p class="note left">${S.everywhere}</p>
      <div class="actions"><button class="btn" data-done>${S.done}</button><button class="btn ghost" data-ask>${S.ask}</button></div>
      <button class="sundo" data-undo>${S.undo}</button>`;
    box.querySelector("[data-done]").onclick = refresh;
    box.querySelector("[data-ask]").onclick = async () => { await refresh(); ask(S.askQ); };
    box.querySelector("[data-undo]").onclick = async () => { await fetch(`/api/sort/${cid}`, { method: "DELETE" }); await refresh(); };
  };
  intro();
}
window.openSort = openSort;

// ---------------------------------------------------------------- Play your next two weeks (the three baskets as rules)
function playCard() {
  const S = E().pl;
  return `<button class="mini playcard" data-play><span class="t">${S.card}</span><b>${S.cardB}</b>
    <span class="pfan"><i>🍽️</i><i>🏠</i><i>☕</i></span><span class="go">${S.go} ›</span></button>`;
}

async function openPlay() {
  const S = E().pl, root = document.createElement("div");
  root.className = "play";
  root.innerHTML = `<div class="ptop"><b>${S.title}</b><button class="wx" aria-label="Close">×</button></div>
    <div class="pchart"></div><div class="pbody"><div class="swait"><span class="typing"><i></i><i></i><i></i></span></div></div>`;
  document.body.appendChild(root);
  root.querySelector(".wx").onclick = () => root.remove();
  let d; try { d = await api(`/api/play/${cid}?lang=${lang}`); } catch { root.remove(); return; }
  const cards = d.cards, extras = cards.filter((c) => c.kind === "extra"), rent = cards.find((c) => c.movable);
  const skip = new Set(), sw = d.swap; let moveRent = false, swapped = false, i = 0;
  const NAMES = { groceries: [S.groceries, "🛒"], surprises: [S.surprises, "🧰"], Housing: [S.rent, "🏠"], Utilities: [S.bills, "💡"], everything_else: [S.rest, "🧾"] };
  const nameOf = (c) => (NAMES[c.label] || [label(c.label), EMOJI[c.label] || "🛍️"]);
  const wday = (iso) => new Date(iso + "T12:00:00").toLocaleDateString(T().locale, { weekday: "short", day: "numeric", month: "short" });
  // The line: the engine's no-extras line, minus the extras kept, plus rent if it moves past payday (same as the server)
  const line = () => d.no_extras_path.map((p, k) => {
    let v = p.balance_eur;
    if (swapped) v -= sw.price_eur;  // the ticket is bought tomorrow, the first day on the line
    for (const c of extras) {
      if (skip.has(c.id) || (swapped && sw.replaces.includes(c.id))) continue;
      if (c.id === "rest") v -= (c.amount_eur / d.days) * (k + 1); else if (c.date <= p.date) v -= c.amount_eur;
    }
    if (moveRent && rent && rent.date <= p.date) v += rent.amount_eur;
    return { x: p.date, v };
  });
  const chart = () => {
    const pts = [{ x: d.today, v: d.balance_eur }, ...line()], end = pts.at(-1).v;
    const lo = Math.min(0, ...pts.map((p) => p.v)), hi = Math.max(0, ...pts.map((p) => p.v)), W = 340, H = 120;
    const X = (k) => 8 + (k / (pts.length - 1)) * (W - 16), Y = (v) => 10 + ((hi - v) / (hi - lo || 1)) * (H - 20);
    const path = pts.map((p, k) => `${k ? "L" : "M"}${X(k).toFixed(1)},${Y(p.v).toFixed(1)}`).join("");
    root.querySelector(".pchart").innerHTML = `<div class="pend ${end >= 0 ? "ok" : "neg"}"><span>${S.onPayday(day(d.next_payday))}</span><b>${end < 0 ? "−" : "+"}${eur0(Math.abs(end))}</b></div>
      <svg viewBox="0 0 ${W} ${H}" class="${end >= 0 ? "ok" : "neg"}"><line x1="0" x2="${W}" y1="${Y(0)}" y2="${Y(0)}" class="z"/>
      <path d="${path}L${X(pts.length - 1)},${Y(0)}L${X(0)},${Y(0)}Z" class="a"/><path d="${path}" class="l"/>
      <circle cx="${X(pts.length - 1)}" cy="${Y(end)}" r="5"/></svg>
      <p class="pusual">${S.usual(eur0(d.keep_all_end_eur))}</p>`;
  };
  const body = root.querySelector(".pbody");
  const intro = () => {
    const t = d.tip;
    body.innerHTML = `<h2>${S.goal}</h2><p class="lead">${S.rules}</p>
      <ul class="prules"><li><i class="b1"></i>${S.r1}</li><li><i class="b2"></i>${S.r2}</li><li><i class="b3"></i>${S.r3}</li></ul>
      ${t ? `<div class="ptip"><p>${SPARK}<span>${esc(t.tip)}</span></p><button class="btn ghost" data-tip>${S.tryTip(`${t.end_eur < 0 ? "−" : "+"}${eur0(Math.abs(t.end_eur))}`)}</button></div>` : ""}
      <button class="btn" data-start>${S.start(cards.length)}</button>`;
    body.querySelector("[data-start]").onclick = () => { i = 0; card(); };
    const tb = body.querySelector("[data-tip]");
    if (tb) tb.onclick = () => { skip.clear(); t.skip.forEach((s) => skip.add(s)); moveRent = t.move_rent; swapped = !!t.swap; chart(); end(); };
  };
  const next = () => {
    i++; chart();
    while (i < cards.length && swapped && sw.replaces.includes(cards[i].id)) i++;  // covered by the ticket
    if (i < cards.length) card(); else end();
  };
  const card = () => {
    const c = cards[i], [nm, em] = nameOf(c);
    const rule = c.kind === "extra" ? S.ruleExtra : c.kind === "buffer" ? S.ruleBuffer : c.movable ? S.ruleRent : S.ruleFixed;
    const btns = c.kind === "extra" ? `<button class="pno" data-a="skip">✕ ${S.skip}</button><button class="pyes" data-a="keep">✓ ${S.keep}</button>`
      : c.movable ? `<button class="pno" data-a="move">${S.move}</button><button class="pyes" data-a="ok">${S.payOnTime}</button>`
      : `<button class="pyes wide" data-a="ok">${S.ok}</button>`;
    const offerSwap = sw && !swapped && sw.replaces[0] === c.id;
    body.innerHTML = `<div class="pprog">${i + 1}/${cards.length}</div>
      <div class="pcard k${c.basket}"><span class="pchip"><i></i>${esc(T().baskets[c.basket][0])}</span><span class="pem">${em}</span>
        <b class="plabel">${esc(nm)}</b><span class="pdate">${c.date ? esc(wday(c.date)) : S.wholePeriod}</span>
        <span class="pamt">${eur0(c.amount_eur)}</span>${c.hours_of_work ? `<span class="phrs">${esc(S.hours(nf(1).format(c.hours_of_work)))}</span>` : ""}
        <p class="prule">${rule}</p></div>
      <div class="pbtns">${btns}</div>
      ${offerSwap ? `<button class="pswap" data-a="swap"><span>🚌 ${S.swapBtn(eur(sw.price_eur))}</span>
        <small>${esc(S.swapNote(day(sw.covers_until), host(sw.source_url)))}</small></button>` : ""}`;
    const el = body.querySelector(".pcard");
    const act = (a) => {
      if (a === "skip") skip.add(c.id); if (a === "keep") skip.delete(c.id); if (a === "move") moveRent = true; if (a === "ok" && c.movable) moveRent = false;
      if (a === "swap") { swapped = true; sw.replaces.forEach((r) => skip.delete(r)); }
      el.classList.add(a === "skip" || a === "move" ? "out-l" : "out-r"); setTimeout(next, 220);
    };
    body.querySelectorAll("[data-a]").forEach((b) => (b.onclick = () => act(b.dataset.a)));
    if (c.kind === "extra") {  // swipe: right keeps, left skips
      let x0 = null;
      el.onpointerdown = (e) => { x0 = e.clientX; el.setPointerCapture(e.pointerId); };
      el.onpointermove = (e) => { if (x0 !== null) el.style.transform = `translateX(${e.clientX - x0}px) rotate(${(e.clientX - x0) / 20}deg)`; };
      el.onpointerup = (e) => { const dx = e.clientX - x0; x0 = null; if (Math.abs(dx) > 80) act(dx > 0 ? "keep" : "skip"); else el.style.transform = ""; };
    }
  };
  const end = async () => {
    const kept = extras.filter((c) => !skip.has(c.id)).map((c) => c.id);
    body.innerHTML = `<div class="swait"><span class="typing"><i></i><i></i><i></i></span></div>`;
    let r; try { r = await api(`/api/play/${cid}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ kept, move_rent: moveRent, swap: swapped, lang }) }); }
    catch { body.innerHTML = `<p class="lead">${T().wentWrong}</p>`; return; }
    const ok = r.end_eur >= 0;
    body.innerHTML = `<h2 class="${ok ? "win" : "lose"}">${ok ? S.win : S.lose}</h2>
      ${r.summary ? `<p class="sq">${SPARK}<span>${esc(r.summary)}</span></p>${listenBtn(r.summary)}` : ""}
      <div class="sch"><div><span>${S.skipped}</span><b>${eur0(r.extras_skipped_eur)}</b></div><div><span>${S.rentMoved}</span><b>${r.rent_moved_after_payday ? S.yes : S.no}</b></div>
      ${r.swapped_to_ticket ? `<div class="wide"><span>🚌 ${S.swappedT}</span><b>${eur(r.swapped_to_ticket.ticket_eur)} · ${esc(r.swapped_to_ticket.source)}</b></div>` : ""}</div>
      <div class="actions"><button class="btn" data-graph>${S.showGraph}</button><button class="btn ghost" data-again>${S.again}</button></div>`;
    body.querySelector("[data-again]").onclick = () => { skip.clear(); moveRent = false; swapped = false; chart(); intro(); };
    body.querySelector("[data-graph]").onclick = async () => {
      const f = await api("/api/scenario", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ customer_id: cid, scenario: r.scenario }) });
      scen = { ...f, parsed: { label: S.planLabel } }; active = "ai"; root.remove(); setTab("home"); redraw();
    };
  };
  chart(); intro();
}
window.openPlay = openPlay;
