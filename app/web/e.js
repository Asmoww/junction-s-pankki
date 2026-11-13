// Design E v2: the future as a graph. Code draws every number; the AI annotates the line and turns
// "what if…" sentences into scenarios that redraw the future. Loaded after app.js on /e.
const ES = {
  en: { since: (a) => `${a} since payday`, today: "Today", pay: "Payday", forecast: "forecast", extras: "your extras",
    payResult: (d) => `On payday, ${d}`, whatIf: "What if…", whatIfPh: "e.g. concert tickets 150 € on Friday",
    pause: "Pause extras", eatLess: "Eat out −50 %", rentLater: "Rent after payday", ask: (d) => `Ask about ${d}`,
    askQ: (d) => `What did I spend on ${d}, and was it a lot for me?`, thinking: "Reading your words…",
    aiNote: "Notes written by AI from your numbers", noAmount: "Tell me an amount, e.g. 150 €.", failed: "Couldn't do that one. Try again.",
    bills: { Housing: "Rent", Utilities: "Bills" }, nothing: "No spending",
    cards: { safe: "Safe this week", month: (m) => m, payday: "After payday", pot: "Surprises", fin: "vs Finland", psd2: "Other bank" },
    perMonth: "a month", vsFin: (a) => `${a} in Finland`, moved: "moved away" },
  fi: { since: (a) => `${a} palkkapäivästä`, today: "Tänään", pay: "Palkka", forecast: "ennuste", extras: "extrasi",
    payResult: (d) => `Palkkapäivänä ${d}`, whatIf: "Entä jos…", whatIfPh: "esim. konserttiliput 150 € perjantaina",
    pause: "Tauko extroille", eatLess: "Ulkona syöminen −50 %", rentLater: "Vuokra palkan jälkeen", ask: (d) => `Kysy päivästä ${d}`,
    askQ: (d) => `Mihin käytin rahaa ${d}, ja oliko se minulle paljon?`, thinking: "Luen pyyntöäsi…",
    aiNote: "Tekoälyn muistiinpanot lukujesi pohjalta", noAmount: "Kerro summa, esim. 150 €.", failed: "Tämä ei onnistunut. Yritä uudelleen.",
    bills: { Housing: "Vuokra", Utilities: "Laskut" }, nothing: "Ei ostoja",
    cards: { safe: "Turvallisesti", month: (m) => m, payday: "Palkan jälkeen", pot: "Yllätykset", fin: "vs Suomi", psd2: "Toinen pankki" },
    perMonth: "kuussa", vsFin: (a) => `Suomessa ${a}`, moved: "siirtyi pois" },
  sv: { since: (a) => `${a} sedan lönedagen`, today: "I dag", pay: "Lön", forecast: "prognos", extras: "dina extra",
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
let fut = null, notes = null, active = null, scen = null, picked = null;

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
  const r = home.ribbon, W = Math.min(window.innerWidth, 480), H = 380, px = 20, top = 96, bot = 44;
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
  const credit = nl.length ? `<div class="credit">${SPARK}AI</div>` : "";
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
    const top = 6 + best.li * 46;
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
  chips.push(`<button class="chip ${active === "pause" ? "on" : ""}" data-sc="pause">${E().pause}</button>`);
  if ((fut.extras_by_category_until_payday || {}).Restaurants) chips.push(`<button class="chip ${active === "eat" ? "on" : ""}" data-sc="eat">${E().eatLess}</button>`);
  if (fut.bills.some((b) => b.bill === "Housing" && b.date !== fut.next_payday)) chips.push(`<button class="chip ${active === "rent" ? "on" : ""}" data-sc="rent">${E().rentLater}</button>`);
  return `<div class="dock"><div class="chips">${chips.join("")}</div>
    <form class="wi" hidden><span>${SPARK}</span><input maxlength="200" placeholder="${esc(E().whatIfPh)}"><button class="go" aria-label="Go">→</button></form>
    <div class="wimsg" hidden></div></div>`;
}

function strip() {
  const o = home.overview, s = o.safe_to_spend, m = o.month, pot = home.pot, pp = home.cards.find((c) => c.id === "payday");
  const cards = [];
  const psd2 = home.cards.find((c) => c.id === "psd2");
  if (psd2) cards.push(`<button class="mini" data-act="psd2"><span class="t">${E().cards.psd2}</span><b>${eur0(psd2.numbers.moved_to_other_bank_eur)}</b><span class="s">${E().moved}</span>
    <div class="flow"><i style="width:${Math.round(psd2.numbers.share_of_income * 100)}%"></i></div></button>`);
  const days = s.days_until_payday;
  cards.push(`<button class="mini ${s.safe_until_payday_eur < 0 ? "neg" : ""}" data-ask="${esc(T().suggestions[0])}"><span class="t">${E().cards.safe}</span><b>${eur0(s.safe_this_week_eur)}</b>
    <span class="s">${s.safe_until_payday_eur < 0 ? "−" + eur0(-s.safe_until_payday_eur) : eur0(s.safe_per_day_eur) + "/" + (lang === "en" ? "day" : lang === "fi" ? "pv" : "dag")}</span>
    <div class="dots">${Array.from({ length: Math.min(days, 15) }, (_, i) => `<i class="${s.safe_until_payday_eur < 0 ? "r" : i < 7 ? "g" : ""}"></i>`).join("")}</div></button>`);
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
  return `<div class="strip">${cards.join("")}</div>`;
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
  el.addEventListener("pointerup", () => {
    if (last && last.i <= G.iT && last.i > 0) { picked = last.p.date; $(".dock").outerHTML = dock(); bindDock(); }
  });
}

function bindDock() {
  const d = $(".dock"); if (!d) return;
  d.querySelectorAll("[data-sc]").forEach((b) => b.addEventListener("click", () => runPreset(b.dataset.sc)));
  const pk = d.querySelector("[data-pick]"); if (pk) pk.addEventListener("click", () => ask(E().askQ(day(picked))));
  const form = d.querySelector(".wi"), msg = d.querySelector(".wimsg");
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

window.renderHomeE = async function () {
  const o = home.overview, r = home.ribbon;
  $("#greet").textContent = `${persona().name} · ${day(o.customer.as_of)}`;
  const [whole, dec] = nf(2).format(o.customer.balance).split(/[.,](?=\d{2}$)/);
  const ch = o.customer.balance - r.past[0].balance_eur;
  $("#balance").innerHTML = `${esc(whole)}<small>${lang === "en" ? "." : ","}${esc(dec)} €</small><span class="delta">${esc(E().since(`${ch < 0 ? "−" : "+"}${eur0(Math.abs(ch))}`))}</span>`;
  if (!fut || fut.cid !== cid) { fut = await api(`/api/future/${cid}`); fut.cid = cid; active = null; scen = null; picked = null; }
  notes = null;
  $("#view-home").innerHTML = `<section id="hero"></section>` + strip() + `<p class="ainote">${SPARK}${E().aiNote}</p>`;
  redraw();
  bindAsks($("#view-home"));
  $("#view-home").querySelectorAll("[data-act=pot]").forEach((b) => b.addEventListener("click", potSheet));
  $("#view-home").querySelectorAll("[data-act=psd2]").forEach((b) => b.addEventListener("click", psd2Sheet));
  const fc = home.cards.find((c) => c.id === "forecast");
  if (fc && !notifShown[cid]) { notifShown[cid] = true; showNotif(fc); }
  const want = `${cid}:${lang}`;
  api(`/api/notes/${cid}?lang=${lang}`).then((n) => { if (`${cid}:${lang}` === want) { notes = n; redraw(); } }).catch(() => {});
};
