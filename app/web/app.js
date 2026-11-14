// Money coach mobile UI. Numbers on screen come from /api (deterministic queries); the coach explains them.
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const BASKET_COLORS = { 1: "var(--b1)", 2: "var(--b2)", 3: "var(--b3)" };
const BANKS = ["OP", "Nordea", "Danske Bank", "Aktia", "Säästöpankki"];

let lang = localStorage.getItem("lang") || "en";
let cid = localStorage.getItem("cid");
let personas = [], home = null, history = [], busy = false, tab = "home", notifShown = {};
const T = () => I18N[lang];
const label = (s) => (LABELS[lang] && LABELS[lang][s]) || s;
const nf = (d) => new Intl.NumberFormat(T().locale, { minimumFractionDigits: d, maximumFractionDigits: d });
const eur = (x) => `${nf(2).format(x)} €`;
const eur0 = (x) => `${nf(0).format(Math.round(x))} €`;
const day = (iso) => new Date(iso + "T12:00:00").toLocaleDateString(T().locale, { day: "numeric", month: "short" }).replace(/\.$/, "");
const monthName = (iso) => new Date(iso + "T12:00:00").toLocaleDateString(T().locale, { month: "long" });
const monthShort = (ym) => new Date(ym + "-15T12:00:00").toLocaleDateString(T().locale, { month: "narrow" });
const psd2Key = () => `psd2-${cid}`;

// Every API call says which AI to use: Claude, or the open model hosted in the EU (the header switch, EU mode)
const aiProvider = () => (localStorage.getItem("ai") === "eu" ? "eu" : "claude");
async function api(path, opts = {}) {
  const r = await fetch(path, { ...opts, headers: { ...(opts.headers || {}), "X-AI-Provider": aiProvider() } });
  if (r.status === 401) { location.href = "/login"; throw new Error("login"); }
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

function toast(html, ms = 3500) {
  const t = $("#toast"); t.innerHTML = html; t.hidden = false;
  clearTimeout(toast.h); toast.h = setTimeout(() => (t.hidden = true), ms);
}

function sheet(html) {
  const root = $("#sheet-root");
  root.innerHTML = `<div class="sheet-bg"><div class="sheet" role="dialog">${html}</div></div>`;
  root.querySelector(".sheet-bg").addEventListener("click", (e) => { if (e.target === e.currentTarget && cid) root.innerHTML = ""; });
  return root.querySelector(".sheet");
}
const closeSheet = () => ($("#sheet-root").innerHTML = "");

/* ---------- charts (HTML, from tool results) ---------- */
function barsChart(a) {
  const max = Math.max(...a.items.map((i) => i.value), 1);
  if (a.vertical) {
    return `<div class="vbars">${a.items.map((i) => `<div class="vbar"><div class="vval">${eur0(i.value)}</div>
      <div class="vcol"><span style="height:${(i.value / max) * 100}%"></span></div><div class="vlab">${esc(label(i.label))}</div></div>`).join("")}</div>`;
  }
  return `<div class="hbars">${a.items.map((i) => `<div class="hrow"><div class="hlab">${esc(label(i.label))}</div>
    <div class="htrack"><span style="width:${(i.value / max) * 100}%"></span></div><div class="hval">${eur0(i.value)}</div></div>`).join("")}</div>`;
}
function basketsChart(items) {
  const total = items.reduce((s, i) => s + i.value, 0) || 1;
  return `<div class="bar">${items.map((b) => `<span style="width:${(b.value / total) * 100}%;background:${BASKET_COLORS[b.basket]}"></span>`).join("")}</div>
    <div class="legend">${items.map((b) => `<span><i style="background:${BASKET_COLORS[b.basket]}"></i>${esc(T().baskets[b.basket][0])} ${eur0(b.value)}</span>`).join("")}</div>`;
}
function potChart(months, avg) {
  const max = Math.max(...months.map((m) => m.eur), avg, 1);
  return `<div class="pot"><div class="pot-cols">${months.map((m) => `<div class="pot-col" title="${esc(m.month)}: ${eur0(m.eur)}"><span style="height:${(m.eur / max) * 100}%"></span><em>${monthShort(m.month)}</em></div>`).join("")}
    <div class="pot-line" style="bottom:${18 + (avg / max) * 122}px"><b>${T().potAvg} ${eur0(avg)}</b></div></div></div>`;
}
function compareChart(a) {
  const max = Math.max(...a.items.flatMap((i) => [i.you, i.finland]), 1);
  return `<div class="cmp">${a.items.map((i) => `<div class="cmp-row"><div class="hlab">${esc(label(i.label))}</div>
    <div class="cmp-bars"><div class="htrack you"><span style="width:${(i.you / max) * 100}%"></span><em>${eur0(i.you)}</em></div>
    <div class="htrack fi"><span style="width:${(i.finland / max) * 100}%"></span><em>${eur0(i.finland)}</em></div></div></div>`).join("")}
    <div class="legend"><span><i class="you"></i>${T().you}</span><span><i class="fi"></i>${T().finland}</span></div></div>`;
}
function sliderWidget(a) {
  const id = "s" + Math.random().toString(36).slice(2, 8);
  setTimeout(() => {
    const el = document.getElementById(id); if (!el) return;
    const upd = () => {
      const pct = +el.querySelector("input").value, m = (a.now_per_month_eur * pct) / 100;
      el.querySelector(".pct").textContent = `${pct} %`;
      el.querySelector(".save").innerHTML = T().sliderSave(eur0(m), eur0(m * 12));
    };
    el.querySelector("input").addEventListener("input", upd); upd();
  });
  return `<div class="slider" id="${id}"><div>${T().slider(esc(label(a.area)))} <b class="pct"></b></div>
    <input type="range" min="5" max="${a.cut_percent > 60 ? 100 : 60}" step="5" value="${a.cut_percent}"><div class="save"></div></div>`;
}
// Chart specs come from the show_chart tool (code computes every point); drawn as inline SVG.
function chartSvg(spec) {
  const W = 300, H = 150, L = 6, R = 6, TP = 14, B = 22;
  const mk = (pts) => pts.map((p) => p.v);
  let all = [];
  const runway = spec.kind === "month_runway";
  const lines = runway ? [["past", spec.past || []], ["future", spec.future || []], ["scenario", spec.scenario || []]] : spec.series.map((s) => [s.label, s.points]);
  lines.forEach(([, pts]) => (all = all.concat(mk(pts))));
  let lo = Math.min(0, ...all), hi = Math.max(...all, 1); const pad = (hi - lo) * 0.08; lo -= pad; hi += pad;
  const Y = (v) => TP + ((hi - v) / (hi - lo)) * (H - TP - B);
  const zero = lo < 0 ? `<line x1="${L}" x2="${W - R}" y1="${Y(0)}" y2="${Y(0)}" stroke="#d7efe0" stroke-width="1.5"/>` : "";
  if (runway) {
    const pts = [...(spec.past || []), ...(spec.future || [])], n = Math.max(pts.length - 1, 1), idx = {};
    pts.forEach((p, i) => (idx[p.x] = i));
    const X = (i) => L + (i * (W - L - R)) / n;
    const path = (arr) => arr.map((p) => `${X(idx[p.x] ?? 0).toFixed(1)},${Y(p.v).toFixed(1)}`).join(" ");
    const neg = (spec.future || []).some((p) => p.v < 0);
    return `<svg viewBox="0 0 ${W} ${H}" class="cht" role="img" aria-label="${esc(spec.title || "")}">${zero}
      ${spec.past && spec.past.length ? `<polyline points="${path(spec.past)}" fill="none" stroke="#00703c" stroke-width="3" stroke-linejoin="round"/>` : ""}
      <polyline points="${path(spec.future)}" fill="none" stroke="${neg ? "#c2402f" : "#2e9c5e"}" stroke-width="2.5" stroke-dasharray="1 6" stroke-linecap="round" opacity="${spec.scenario && spec.scenario.length ? 0.5 : 1}"/>
      ${spec.scenario && spec.scenario.length ? `<polyline points="${path(spec.scenario)}" fill="none" stroke="#003d25" stroke-width="2.5"/>` : ""}
      <text x="${L}" y="${H - 6}" class="ctk">${pts.length ? day(pts[0].x) : ""}</text><text x="${W - R}" y="${H - 6}" class="ctk" text-anchor="end">${pts.length ? day(pts[pts.length - 1].x) : ""}</text></svg>`;
  }
  const ms = spec.series[0].points.map((p) => p.x), n = ms.length, bw = (W - L - R) / n;
  const X = (i) => L + bw * i + bw / 2;
  const mon = (ym) => new Date(ym + "-15T12:00:00").toLocaleDateString(T().locale, { month: "narrow" });
  let body = "";
  if (spec.series.length === 1) {
    body = spec.series[0].points.map((p, i) => `<rect x="${(X(i) - bw * 0.32).toFixed(1)}" y="${Y(p.v).toFixed(1)}" width="${(bw * 0.64).toFixed(1)}" height="${Math.max(1, Y(0) - Y(p.v)).toFixed(1)}" rx="2" fill="#2e9c5e"/>`).join("");
    if (spec.spending_trend_eur_per_month != null) {
      const avg = spec.average_per_month_eur, k = spec.spending_trend_eur_per_month, mid = (n - 1) / 2;
      body += `<line x1="${X(0)}" x2="${X(n - 1)}" y1="${Y(avg - k * mid)}" y2="${Y(avg + k * mid)}" stroke="#003d25" stroke-width="1.5" stroke-dasharray="4 3"/>`;
    }
  } else {
    const col = ["#003d25", "#8fd0a8"];
    body = spec.series.map((s, j) => `<polyline points="${s.points.map((p, i) => `${X(i).toFixed(1)},${Y(p.v).toFixed(1)}`).join(" ")}" fill="none" stroke="${col[j]}" stroke-width="2.5" stroke-linejoin="round"/>`).join("");
  }
  const ticks = ms.map((m, i) => `<text x="${X(i)}" y="${H - 6}" class="ctk" text-anchor="middle">${mon(m)}</text>`).join("");
  const legend = spec.series.length > 1 ? `<div class="legend"><span><i style="background:#003d25"></i>${esc(spec.series[0].label)}</span><span><i style="background:#8fd0a8"></i>${esc(spec.series[1].label)}</span></div>` : "";
  return `<svg viewBox="0 0 ${W} ${H}" class="cht" role="img" aria-label="${esc(spec.title || "")}">${zero}${body}${ticks}</svg>${legend}`;
}

function renderAttachment(a) {
  if (a.type === "chart") return `${a.spec.title ? `<div class="chart-title">${esc(a.spec.title)}</div>` : ""}${chartSvg(a.spec)}`;
  if (a.type === "bars") return barsChart(a);
  if (a.type === "baskets") return basketsChart(a.items);
  if (a.type === "pot") return `<div class="chart-title">${T().potChart}</div>${potChart(a.months, a.average)}`;
  if (a.type === "compare") return compareChart(a);
  if (a.type === "slider") return sliderWidget(a);
  return "";
}

/* ---------- home ---------- */
function cardNumbers(c) {
  const n = c.numbers;
  if (c.id === "forecast") return { short: eur0(-n.balance_at_payday_at_usual_pace_eur), payday: day(n.next_payday), out: n.runs_out_around ? day(n.runs_out_around) : "–" };
  if (c.id === "psd2") return { moved: eur0(n.moved_to_other_bank_eur), salary: eur0(n.salary_eur) };
  if (c.id === "payday") return { pct: n.payday_week_change_percent };
  if (c.id === "pot") return { min: eur0(n.smallest_month_eur), max: eur0(n.biggest_month_eur), avg: eur0(n.average_per_month_last_12_eur) };
  return {};
}

function insightCard(c) {
  const [title, body, q] = T().cards[c.id];
  const text = body(cardNumbers(c));
  let extra = "";
  if (c.id === "pot") {
    extra = potChart(c.numbers.months.slice(-12), c.numbers.average_per_month_last_12_eur) +
      `<p class="sub">${T().potBody(eur0(c.numbers.suggested_monthly_pot_eur))}</p>
       <div class="actions"><button class="btn" data-act="pot">${T().potAction}</button><button class="btn ghost" data-ask="${esc(q)}">${T().askCoach}</button></div>`;
  } else if (c.id === "psd2") {
    const bank = localStorage.getItem(psd2Key());
    extra = bank ? `<div class="pill ok">${esc(T().connected(bank))}</div>` : `<div class="actions"><button class="btn" data-act="psd2">${T().connect}</button></div>`;
  } else if (q) {
    extra = `<div class="actions"><button class="btn ghost" data-ask="${esc(q)}">${T().askCoach}</button></div>`;
  }
  return `<section class="card insight ${c.kind}"><div class="label">${esc(title)}</div><p class="lead">${esc(text)}</p>${extra}</section>`;
}

function safeCard(s) {
  const short = s.safe_until_payday_eur < 0;
  const steps = s.steps.map((st) => `<li><span>${esc(st.step)}</span><span class="amt">${eur(st.eur)}</span></li>`).join("");
  return `<section class="card ${short ? "warn" : ""}"><div class="label">${T().safeWeek}</div>
    <div class="big">${short ? "−" + eur0(-s.safe_until_payday_eur) : eur0(s.safe_this_week_eur)}</div>
    <div class="sub">${short ? T().short(eur0(-s.safe_until_payday_eur), day(s.next_payday))
      : T().perDay(eur0(s.safe_per_day_eur), day(s.next_payday), eur0(s.your_usual_extras_per_week_eur))}</div>
    <details class="how"><summary>${T().howCalc}</summary><ul class="steps">${steps}
      <li><span>${T().safeUntil(s.days_until_payday)}</span><span class="amt">${eur(s.safe_until_payday_eur)}</span></li></ul></details></section>`;
}

function basketsCard(o) {
  const m = o.month, mn = monthName(m.period.start);
  const items = m.baskets.map((b) => ({ basket: b.basket, value: b.total_eur }));
  const rows = m.baskets.map((b) => {
    const avg = o.six_month_avg_eur[b.basket], d = b.total_eur - avg;
    const pending = b.basket === 1 && o.not_yet_charged_this_month.length;
    const names = o.not_yet_charged_this_month.map((x) => (x === "Housing" ? T().rent : T().utilities)).join(" & ");
    const delta = pending ? `<div class="delta">${esc(T().notCharged(names))}</div>`
      : avg > 0 && Math.abs(d) >= 5 ? `<div class="delta ${d > 0 ? "up" : "down"}">${T().vsUsual(`${d > 0 ? "+" : "−"}${eur0(Math.abs(d))}`)}</div>`
      : `<div class="delta">${T().aboutUsual}</div>`;
    const [name, meaning] = T().baskets[b.basket];
    return `<button class="basket" data-ask="${esc(T().basketAsk(name, mn))}">
      <span class="dot" style="background:${BASKET_COLORS[b.basket]}"></span>
      <span><div class="name">${esc(name)}</div><div class="meaning">${esc(meaning)}</div></span>
      <span class="right"><div class="amount">${eur0(b.total_eur)}</div>${delta}</span><span class="chev">›</span></button>`;
  }).join("");
  return `<section class="card"><div class="label">${T().monthBaskets(mn)}</div>
    <div class="big">${eur0(m.total_spending_eur)}</div><div class="sub">${T().spentIn(mn)}</div>
    <div class="bar">${items.map((b) => `<span style="width:${(b.value / (m.total_spending_eur || 1)) * 100}%;background:${BASKET_COLORS[b.basket]}"></span>`).join("")}</div>${rows}</section>`;
}

function benchCard(b) {
  const items = b.areas.map((a) => ({ label: a.area, you: a.you_per_month_eur, finland: a.finland_same_age_per_month_eur }));
  return `<section class="card"><div class="label">${T().benchTitle}</div><div class="sub">${T().benchSub(b.age_group)}</div>
    ${compareChart({ items })}<p class="note left">${T().benchNote}</p></section>`;
}

function renderHome() {
  if (!home) return;
  const o = home.overview, p = persona();
  if (window.UI === "e" && window.renderHomeE) return window.renderHomeE();
  $("#greet").textContent = T().balanceOn(p.name);
  $("#balance").textContent = eur(o.customer.balance);
  const cards = home.cards;
  const top = cards.filter((c) => c.id === "forecast" || c.id === "psd2");
  const rest = cards.filter((c) => c.id === "payday" || c.id === "pot");
  $("#view-home").innerHTML = top.map(insightCard).join("") + safeCard(o.safe_to_spend) + basketsCard(o) +
    rest.map(insightCard).join("") + benchCard(home.benchmark);
  bindAsks($("#view-home"));
  $("#view-home").querySelectorAll("[data-act=pot]").forEach((b) => b.addEventListener("click", potSheet));
  $("#view-home").querySelectorAll("[data-act=psd2]").forEach((b) => b.addEventListener("click", psd2Sheet));
  const fc = cards.find((c) => c.id === "forecast");
  if (fc && !notifShown[cid]) { notifShown[cid] = true; showNotif(fc); }
}

function showNotif(c) {
  const [title, body, q] = T().cards[c.id];
  const n = $("#notif");
  n.innerHTML = `<div class="notif-app"><span class="brand-mark sm">S</span>${T().notif}</div><b>${esc(title)}</b><div>${esc(body(cardNumbers(c)))}</div>`;
  n.hidden = false; n.classList.add("in");
  n.onclick = () => { n.hidden = true; ask(q); };
  setTimeout(() => { n.classList.remove("in"); setTimeout(() => (n.hidden = true), 400); }, 6500);
}

// Basket 2 made concrete with a live price (Context.dev): what one washing machine costs today, vs the surprise pot
function washBlock() {
  const ex = home.surprise_example, avg = home.pot.average_per_month_last_12_eur;
  if (!ex || !(avg > 0)) return "";
  return `<div class="liveex"><span class="em">🧺</span><div><b>${esc(T().liveWash(eur0(ex.low_eur)))}</b><span>${esc(T().liveWashSrc(ex.shops.join(", ")))}</span>
    <p>${esc(T().liveWashEvery(eur0(avg), (ex.low_eur / avg >= 2 ? nf(0) : nf(1)).format(ex.low_eur / avg)))}</p></div></div>`;
}

function potSheet() {
  const pot = home.pot, payday = home.overview.safe_to_spend.next_payday, wq = window.whyQ ? window.whyQ("surprises") : "";
  const s = sheet(`<h2>${T().potTitle}</h2><p class="sub">${T().potSheet(eur0(pot.suggested_monthly_pot_eur), day(payday))}</p>
    ${potChart(pot.months.slice(-12), pot.average_per_month_last_12_eur)}${washBlock()}<p class="note">${T().demoNote}</p>
    ${wq ? `<button class="btn ghost wide" data-why>${esc(wq)}</button>` : ""}<button class="btn wide" data-close>${T().ok}</button>`);
  s.querySelector("[data-close]").addEventListener("click", closeSheet);
  const w = s.querySelector("[data-why]"); if (w) w.onclick = () => { closeSheet(); window.askHere(wq); };
}

function psd2Sheet() {
  const s = sheet(`<h2>${T().psd2Title}</h2><p class="sub">${T().psd2Body}</p>
    <ul class="checks">${T().psd2Scope.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
    <div class="label" style="margin:14px 4px 8px">${T().chooseBank}</div>
    <div class="banks">${BANKS.map((b, i) => `<label><input type="radio" name="bank" value="${b}" ${i ? "" : "checked"}><span>${b}</span></label>`).join("")}</div>
    <p class="note">${T().demoNote}</p><button class="btn wide" data-allow>${T().psd2Allow}</button>`);
  s.querySelector("[data-allow]").addEventListener("click", async () => {
    const bank = s.querySelector("input[name=bank]:checked").value;
    try { await api(`/api/psd2/${cid}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ bank }) }); }
    catch { toast(T().wentWrong); return; }
    closeSheet(); toast(esc(T().psd2Done(bank)), 5000); fut = null; load();  // the full picture now appears on Home
  });
}

/* ---------- learn ---------- */
function renderLearn() {
  if (!home) return;
  const t = home.type, [tname, tsum] = T().types[t.type] || [t.type, t.summary];
  const fmtSig = (k, v) => (v === null || v === undefined ? "–" : k.includes("percent") ? `${v > 0 ? "+" : ""}${v} %`
    : k === "transactions_while_overdrawn" ? v : `${Math.round(v * 100)} %`);
  const sig = Object.entries(t.signals).map(([k, v]) => `<li><span>${esc(T().signals[k] || k)}</span><span class="amt">${fmtSig(k, v)}</span></li>`).join("");
  $("#view-learn").innerHTML = `
    ${window.openSort ? sortCard().replace("mini sortcard", "card sortcard learn") : ""}
    ${window.learnCard ? window.learnCard() : ""}
    ${window.healthCard ? window.healthCard() : ""}
    <section class="card typecard"><div class="label">${T().typeTitle}</div><div class="type">${esc(tname)}</div><p class="lead">${esc(tsum)}</p>
      <details class="how"><summary>${T().typeSignals}</summary><ul class="steps">${sig}</ul></details></section>
    <section class="card" id="trust"><div class="label">${T().trustTitle}</div><div class="skeleton"></div></section>`;
  $("#view-learn").querySelectorAll("[data-sort]").forEach((b) => b.addEventListener("click", window.openSort));
  $("#view-learn").querySelectorAll("[data-health]").forEach((b) => b.addEventListener("click", window.healthSheet));
  if (window.renderDetective) window.renderDetective();
  renderTrust();
}

async function renderTrust() {
  const el = $("#trust"); if (!el) return;
  let d; try { d = await api("/api/traps"); } catch { return; }
  const run = d.runs && d.runs[0];
  if (!run) { el.innerHTML = `<div class="label">${T().trustTitle}</div><p class="sub">${T().trustNone}</p>`; return; }
  // One compact card; the full question list (test evidence, not customer content) opens only on tap
  el.innerHTML = `<div class="label">${T().trustTitle}</div><div class="big">${T().passed(run.passed, run.total)}</div>
    <p class="sub">${T().trustSub}</p>${(() => { const e = d.eu_runs && d.eu_runs[0];
      return e ? `<p class="euline">🇪🇺 ${esc(e.model)}: <b>${T().passed(e.passed, e.total)}</b>, ${T().verified(e.numbers_verified, e.numbers_total)}</p>` : ""; })()}
    <button class="link" id="trust-see">${T().trustSee} ›</button>`;
  $("#trust-see").onclick = () => sheet(`<h2>${T().trustTitle}</h2><p class="note left">${esc(run.at)} · ${T().verified(run.numbers_verified, run.numbers_total)}</p>
    <ul class="traps">${run.cases.map((c) => `<li class="${c.ok ? "ok" : "bad"}"><span class="mark">${c.ok ? "✓" : "✗"}</span><span><b>${esc(c.trap)}</b><br>
      <span class="sub">“${esc(c.question)}”</span>${c.ok ? "" : `<br><span class="why">${esc(c.failed.join("; "))}</span>`}</span></li>`).join("")}</ul>`);
}

/* ---------- coach ---------- */
function md(text) {
  const lines = esc(text).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/(^|\s)\*(\S.*?)\*(?=\s|$|[.,])/g, "$1<i>$2</i>").split("\n");
  let html = "", list = false, para = [];
  const flush = () => { if (para.length) { html += `<p>${para.join("<br>")}</p>`; para = []; } };
  for (const raw of lines) {
    const l = raw.trim(), li = l.match(/^([-•*]|\d+\.)\s+(.*)/);
    if (li) { flush(); if (!list) { html += "<ul>"; list = true; } html += `<li>${li[2]}</li>`; continue; }
    if (list) { html += "</ul>"; list = false; }
    if (!l) flush(); else para.push(l.replace(/^#+\s*/, ""));
  }
  flush(); if (list) html += "</ul>";
  return html;
}

// Where a number comes from: green = your data, grey = your number, blue = assumption / calculation / rule of thumb,
// amber = couldn't check. The colour comes from app/verify.py (code); the coach's note only explains, never recolours.
const NUM_KIND = { verified: "data", rounded: "data", derived: "data", yours: "yours", assumption: "assumption",
  calculated: "calculated", rule: "rule", earlier: "earlier", unverified: "unverified" };
const NUM_SPARK = `<svg class="nspark" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0c.6 4.2 3.8 7.4 8 8-4.2.6-7.4 3.8-8 8-.6-4.2-3.8-7.4-8-8 4.2-.6 7.4-3.8 8-8z"/></svg>`;
const ANSWERS = [];  // rendered answers, so a tapped number can read its tool result from the answer's trace
// Developer mode (open the app with ?dev once): number popups also show the tool call behind a number.
const DEV = (() => { try { if (new URLSearchParams(location.search).has("dev")) localStorage.setItem("dev", "1"); return localStorage.getItem("dev") === "1"; } catch { return false; } })();
function markNumbers(html, numbers, aid = -1) {
  let pos = 0;
  for (const [k, n] of (numbers || []).entries()) {
    const t = esc(n.text), i = html.indexOf(t, pos);
    if (i < 0) continue;
    const span = `<span class="num ${n.status}" role="button" tabindex="0" data-a="${aid}" data-i="${k}" data-status="${n.status}" data-src="${esc(n.source || "")}" data-note="${esc(n.note || "")}">${t}</span>`;
    html = html.slice(0, i) + span + html.slice(i + t.length); pos = i + span.length;
  }
  return html;
}
function numberBadges(nums) {
  const S = T().ns, k = nums.map((n) => NUM_KIND[n.status] || "unverified");
  const d = k.filter((x) => x === "data").length, a = k.filter((x) => ["assumption", "calculated", "rule"].includes(x)).length,
    u = k.filter((x) => x === "unverified").length;
  if (!d && !a && !u) return "";
  let legend = "";
  if (a || k.includes("yours")) {
    let seen = false;
    try { seen = localStorage.getItem("numLegend") === "1"; localStorage.setItem("numLegend", "1"); } catch { seen = false; }
    if (!seen) legend = `<div class="nlegend">${S.legend.map((l, i) => `<span>${i < 3 ? `<i class="l${i}"></i>` : ""}${esc(l)}</span>`).join("")}</div>`;
  }
  return `<div class="nbadges">${d ? `<span class="nb data">${S.bData(d)}</span>` : ""}${a ? `<span class="nb asm">${S.bAsm(a)}</span>` : ""}${u ? `<span class="nb unch">${S.bUnch(u)}</span>` : ""}</div>${legend}`;
}
// "From your data", in plain words: what the number is, the period, how many payments, and the payments behind it.
// Built by code from the tool's own inputs and results (never by the AI), so it can't misdescribe a number.
const SHIELD = `<svg class="nshield" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1 2 3.5v4C2 11 4.6 14 8 15c3.4-1 6-4 6-7.5v-4L8 1zm-1 10L4.3 8.3l1-1L7 9l3.7-3.7 1 1L7 11z"/></svg>`;
const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
function periodText(p) {
  if (!p || !p.start) return "";
  const s = new Date(p.start + "T12:00:00"), e = new Date(p.end + "T12:00:00");
  const last = new Date(e.getFullYear(), e.getMonth() + 1, 0).getDate();
  if (s.getDate() === 1 && s.getMonth() === e.getMonth() && s.getFullYear() === e.getFullYear() && e.getDate() === last)
    return s.toLocaleDateString(T().locale, { month: "long", year: "numeric" });
  return `${day(p.start)} ${s.getFullYear() !== e.getFullYear() ? s.getFullYear() + " " : ""}– ${day(p.end)} ${e.getFullYear()}`;
}
function monthRange(ym, p) {
  const [y, m] = ym.split("-").map(Number), a = `${ym}-01`, b = new Date(y, m, 0), z = `${ym}-${String(b.getDate()).padStart(2, "0")}`;
  return { start: p && p.start > a ? p.start : a, end: p && p.end < z ? p.end : z };
}
const basketNo = (name) => [1, 2, 3].find((b) => I18N.en.baskets[b][0] === name || T().baskets[b][0] === name);
const humanKey = (k) => { const w = String(k).replace(/\[\d+\]/g, "").split(".").pop().replace(/_eur$/, "").replace(/_/g, " "); return w.charAt(0).toUpperCase() + w.slice(1); };
function describeSource(n, trace) {
  const D = T().ds;
  if (n.ti === undefined || n.ti === null || !trace || !trace[n.ti]) {
    if (/^customer\.balance/.test(n.source || "")) return { what: D.balance, meta: [day("2026-09-30") + " 2026"] };
    return { what: n.expression ? D.fromData : D.acct, meta: [] };
  }
  const t = trace[n.ti], inp = t.input || {}, res = t.result || {}, path = n.path || "", per = res.period;
  const filt = { category: inp.category, subcategory: inp.subcategory, basket: inp.basket };
  const flabel = inp.subcategory ? label(inp.subcategory) : inp.category ? label(inp.category) : inp.basket ? T().baskets[inp.basket][0] : D.all;
  const list = (extra = {}, p = per) => (p ? { ...filt, ...extra, start: p.start, end: p.end } : null);
  if (t.tool === "get_spending") {
    if (path === "total_eur") return { what: flabel, meta: [periodText(per), D.pays(res.transactions)], list: list(), count: res.transactions };
    if (path === "average_per_month_eur") return { what: `${D.avg}: ${flabel}`, meta: [periodText(per), D.pays(res.transactions)], list: list(), count: res.transactions,
      avg: { total: res.total_eur, months: per.months_with_data || per.months } };
    if (path.startsWith("one_off_large_purchases")) return { what: D.oneoff, meta: [periodText(per), D.pays(res.one_off_large_purchases.count)] };
    if (path.startsWith("not_classifiable")) return { what: D.nomcc, meta: [periodText(per), D.pays(res.not_classifiable.count)] };
    const m = path.match(/^breakdown\[(\d+)\]/);
    if (m && res.breakdown && res.breakdown[+m[1]]) {
      const row = res.breakdown[+m[1]], gb = inp.group_by, pays = D.pays(row.transactions), count = row.transactions;
      if (gb === "month") { const p = monthRange(row.key, per); return { what: flabel, meta: [periodText(p), pays], list: list({}, p), count }; }
      if (gb === "category") return { what: label(row.key), meta: [periodText(per), pays], list: list({ category: row.key }), count };
      if (gb === "subcategory") return { what: label(row.key), meta: [periodText(per), pays], list: list({ subcategory: row.key }), count };
      if (gb === "basket") { const b = basketNo(row.key); return { what: b ? T().baskets[b][0] : row.key, meta: [periodText(per), pays], list: b ? list({ basket: b }) : null, count }; }
      if (gb === "weekday") {
        const w = WEEKDAYS.indexOf(row.key), wd = w >= 0 ? new Date(2026, 0, 5 + w).toLocaleDateString(T().locale, { weekday: "long" }) : row.key;
        return { what: `${flabel}, ${D.onDays(wd)}`, meta: [periodText(per), pays] };
      }
    }
  }
  if (t.tool === "get_cashflow") {
    const map = { "income_eur.salary": D.salary, "income_eur.other_income": D.otherIncome, "income_eur.total": D.moneyIn, "spending_eur.total": D.all,
      "income_minus_spending_eur": D.net, "balance_eur.start": D.balStart, "balance_eur.end": D.balEnd, "balance_eur.change": D.balChange };
    const b = path.startsWith("spending_eur.") && basketNo(path.slice(13));
    const what = map[path] || (b ? T().baskets[b][0] : path.startsWith("moved_to_own") ? D.saved : humanKey(path));
    return { what, meta: [periodText(per)] };
  }
  if (t.tool === "get_three_baskets") {
    const m = path.match(/^baskets\[(\d+)\](?:\.top\[(\d+)\])?/), bk = m && res.baskets && res.baskets[+m[1]];
    if (bk) {
      if (m[2] !== undefined && bk.top[+m[2]]) return { what: label(bk.top[+m[2]].merchant_type), meta: [periodText(per), D.pays(bk.top[+m[2]].transactions)] };
      const avg = path.includes("per_month") ? { total: bk.total_eur, months: per.months_with_data || per.months } : null;
      return { what: (avg ? `${D.avg}: ` : "") + T().baskets[bk.basket][0], meta: [periodText(per), D.pays(bk.transactions)], avg };
    }
  }
  if (t.tool === "get_safe_to_spend") {
    const m = path.match(/^steps\[(\d+)\]/);
    if (m && res.steps && res.steps[+m[1]]) return { what: res.steps[+m[1]].step, meta: [] };
  }
  if (t.tool === "list_transactions") {
    const m = path.match(/^transactions\[(\d+)\]/), tx = m && res.transactions && res.transactions[+m[1]];
    if (tx) return { what: label(tx.merchant_type || tx.category), meta: [day(tx.time.slice(0, 10)) + " " + tx.time.slice(0, 4)] };
  }
  return { what: humanKey(path), meta: per ? [periodText(per)] : [] };
}
function techLine(n, trace) {
  if (n.expression) return n.expression;
  const t = trace && n.ti !== undefined && n.ti !== null ? trace[n.ti] : null;
  if (!t) return n.source || "";
  const args = Object.entries(t.input || {}).map(([k, v]) => `${k}: ${v}`).join(", ");
  return `${t.tool}(${args}) → ${n.path || ""}`;
}
function dataSheet(n, trace) {
  const D = T().ds, d = describeSource(n, trace);
  const partRows = [];
  if (n.rounded_from !== undefined) partRows.push(`<div><span>${D.rounded}</span><span>${eur(n.rounded_from)}</span></div>`);
  if (d.avg && d.avg.months) partRows.push(`<div><span>${D.avgTotal}</span><span>${eur(d.avg.total)}</span></div>`,
    `<div><span></span><span>${esc(D.div(d.avg.months))}</span></div>`, `<div class="sum"><span>${D.perMonth}</span><span>${eur(n.rounded_from ?? n.value)}</span></div>`);
  if (n.parts && n.parts.length) {
    for (const p of n.parts) {
      const pd = describeSource({ ...p, source: "" }, trace);
      partRows.push(`<div><span>${p.op ? `${p.op} ` : ""}${esc(pd.what)}${pd.meta.filter(Boolean).length ? `<small>${esc(pd.meta.filter(Boolean).join(" · "))}</small>` : ""}</span><span>${eur(p.value)}</span></div>`);
    }
    partRows.push(`<div class="sum"><span>${D.together}</span><span>${eur(n.value)}</span></div>`);
  }
  const see = d.list && d.count && n.status !== "derived" ? `<button class="nsee" type="button">${D.see(d.count)}</button>` : "";
  return { html: `<span class="nkind data">${SHIELD}${D.acct}</span><div class="nval">${esc(n.text)}</div><p class="nwhat">${esc(d.what)}</p>
    ${d.meta.filter(Boolean).length ? `<p class="nfact">${esc(d.meta.filter(Boolean).join(" · "))}</p>` : ""}
    ${partRows.length ? `<div class="nparts">${partRows.join("")}</div>` : ""}${see}
    ${DEV ? `<details class="ntech"><summary>${D.details}</summary><code>${esc(techLine(n, trace))}</code></details>` : ""}`, list: d.list };
}
async function paymentsSheet(n, trace, el) {
  const D = T().ds, d = describeSource(n, trace), q = new URLSearchParams();
  for (const [k, v] of Object.entries(d.list)) if (v !== undefined && v !== null && v !== "") q.set(k, v);
  const s = sheet(`<div class="nsheet"><button class="nback" type="button">${D.back}</button><h2>${esc(d.what)}</h2><p class="nfact">${esc(d.meta.filter(Boolean).join(" · "))}</p><div class="swait"><span class="typing"><i></i><i></i><i></i></span></div></div>`);
  s.querySelector(".nback").onclick = () => numberSheet(el);
  let r;
  try { r = await api(`/api/payments/${cid}?${q}`); } catch { s.querySelector(".swait").innerHTML = `<p class="sub">${T().failed || "Error"}</p>`; return; }
  const rows = r.transactions.map((x) => { const dt = new Date(x.date + "T12:00:00");
    return `<div class="nrow"><span class="nd"><b>${dt.getDate()}</b>${esc(dt.toLocaleDateString(T().locale, { weekday: "short" }))}</span>
      <span class="nt">${esc(label(x.merchant_type || x.category))}<small>${esc(T().baskets[x.basket] ? T().baskets[x.basket][0] : D.card)}</small></span><span class="na">−${eur(x.amount_eur)}</span></div>`; }).join("");
  const avg = n.path === "average_per_month_eur" ? `<div class="ntotal"><span>${D.avg}</span><span>${eur(n.value)}</span></div>` : "";
  s.querySelector(".swait").outerHTML = `${rows}<div class="ntotal"><span>${D.total}</span><span>${eur(r.total_eur)}</span></div>${avg}
    <p class="nfine">${D.noShop}${r.shown < r.count ? " " + D.shown(r.shown, r.count) : ""}</p>`;
}
function numberSheet(el) {
  const r = ANSWERS[+el.dataset.a], n = r && r._nums ? r._nums[+el.dataset.i] : null;
  const st = el.dataset.status, k = NUM_KIND[st] || "unverified", S = T().ns, src = el.dataset.src, note = el.dataset.note;
  const nt = note ? `<div class="nnote"><span class="nh">${NUM_SPARK}${S.note}</span>${esc(note)}</div>` : "";
  if (k === "data" && n) {
    const ds = dataSheet(n, r.trace), s = sheet(`<div class="nsheet">${ds.html}${nt}</div>`);
    const btn = s.querySelector(".nsee");
    if (btn) btn.onclick = () => paymentsSheet(n, r.trace, el);
    return;
  }
  const fact = k === "data" ? (st === "rounded" ? T().numRounded : st === "derived" ? T().numDerived : T().numVerified) : S["f" + k];
  const work = src && k !== "yours" ? `<div class="nwork"><span>${S.how}</span><code>${esc(src)}</code></div>` : "";
  const s = sheet(`<div class="nsheet"><span class="nkind ${k}">${S[k]}</span><div class="nval">${el.innerHTML}</div><p class="nfact">${esc(fact)}</p>${nt}${work}</div>`);
  s.querySelector(".nsheet").addEventListener("click", closeSheet);
}

const TOOL_LABEL = {
  get_spending: "Added up your spending", list_transactions: "Listed transactions", get_cashflow: "Checked money in and out",
  get_three_baskets: "Split spending into the three baskets", get_safe_to_spend: "Calculated safe-to-spend", simulate_cut: "Simulated the cut",
  get_spender_profile: "Compared your habits with your age group", get_surprise_pot: "Looked at surprise costs month by month",
  get_payday_pattern: "Compared spending before and after payday", get_payday_forecast: "Projected your balance to payday",
  get_benchmark: "Compared with Statistics Finland", get_spender_type: "Worked out your spender type", calculate: "Calculated",
  show_chart: "Drew a chart from your transactions", forecast_with_events: "Put your planned costs on their dates",
  check_purchase: "Checked live prices on shop pages", plan_home: "Planned a home purchase with live rules", money_health: "Worked out your money fitness score", get_safe_to_save: "Worked out what is safe to save", get_monthly_drains: "Found what drains your account monthly", get_other_accounts: "Read your other bank (PSD2, demo)",
};
function traceLine(t) {
  const r = t.result || {}, i = t.input || {};
  if (t.error) return `<li><b>${TOOL_LABEL[t.tool] || t.tool}</b>: retried (${esc(r.error || "error")})</li>`;
  const per = r.period || r.based_on;
  const when = per ? ` · ${day(per.start)} – ${day(per.end)} ${per.end.slice(0, 4)}` : "";
  if (t.tool === "calculate") return `<li><b>${TOOL_LABEL.calculate}</b> · ${esc(i.what || "")}: ${esc(i.expression)} = ${esc(r.result)}</li>`;
  const what = [i.category, i.subcategory && label(i.subcategory), i.basket && T().baskets[i.basket][0]].filter(Boolean).join(", ");
  return `<li><b>${TOOL_LABEL[t.tool] || t.tool}</b>${what ? ` · ${esc(what)}` : ""}${when}</li>`;
}

function answerHtml(r) {
  const nums = (r.numbers || []).filter((n) => n.status !== "suggestion");
  const badge = numberBadges(nums);
  r._nums = nums; const aid = ANSWERS.push(r) - 1; if (aid >= 60) delete ANSWERS[aid - 60];
  const att = (r.attachments || []).map((a) => `<div class="att">${renderAttachment(a)}</div>`).join("");
  const u = r.usage || {}, pv = r.privacy || {};
  const how = r.trace && r.trace.length ? `<details class="how"><summary>${T().howWorked}</summary><ul class="trace">${r.trace.map(traceLine).join("")}</ul></details>` : "";
  const saw = u.model ? `<details class="how"><summary>${T().whatAiSaw}</summary><ul class="trace">
    <li><b>${T().model}</b>: ${esc(u.model)} · ${u.calls} × · ${nf(0).format(u.input_tokens + (u.cache_read_tokens || 0) + (u.cache_write_tokens || 0))} / ${nf(0).format(u.output_tokens)} ${T().tokens}</li>
    ${u.where ? `<li><b>${T().where}</b>: ${esc(u.where)}</li>` : `<li><b>${T().cost}</b>: $${(u.cost_usd || 0).toFixed(3)}</li>`}<li><b>${T().sent}</b>: ${esc(pv.sent)}</li><li><b>${T().neverSent}</b>: ${esc(pv.never_sent)}</li></ul></details>` : "";
  return markNumbers(md(r.answer), nums, aid) + listenBtn(r.answer) + att + badge + how + saw;
}

// Listen: the sentence read aloud (ElevenLabs), only when voice is connected on the server
function listenBtn(text) {
  return window.aiInfo && window.aiInfo.voice && text ? `<button class="listen" data-say="${esc(text.replace(/[*_#`]/g, "").slice(0, 400))}">🔊 ${T().listen}</button>` : "";
}
document.addEventListener("click", async (e) => {
  const b = e.target.closest("[data-say]"); if (!b || b.classList.contains("busy")) return;
  e.stopPropagation(); b.classList.add("busy");
  try {
    const r = await fetch("/api/speak", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: b.dataset.say }) });
    if (!r.ok) throw new Error(r.status);
    const a = new Audio(URL.createObjectURL(await r.blob())); a.onended = () => b.classList.remove("busy"); await a.play();
  } catch { b.classList.remove("busy"); toast(T().wentWrong); }
});

function addMsg(role, html, cls = "") {
  const d = document.createElement("div");
  d.className = `msg ${role} ${cls}`; d.innerHTML = html;
  $("#thread").appendChild(d); d.scrollIntoView({ behavior: "smooth", block: "end" });
  return d;
}

/* ---------- coach steps: what the coach is really doing while you wait (one line per tool it runs) ---------- */
const STEP_TXT = {
  en: { read: "Reading your question", get_spending: "Adding up your spending", list_transactions: "Looking through your purchases",
    get_cashflow: "Comparing money in and out", get_three_baskets: "Sorting into your three baskets", get_safe_to_spend: "Working out what's safe to spend",
    simulate_cut: "Trying the cut on your numbers", get_surprise_pot: "Sizing your surprise pot", get_payday_pattern: "Looking at your paydays",
    get_payday_forecast: "Projecting to payday", get_benchmark: "Comparing with Statistics Finland", get_spender_type: "Finding your spender type",
    get_spender_profile: "Finding your spender type", check_purchase: "Checking live prices", plan_home: "Planning the home purchase",
    show_chart: "Drawing a chart", forecast_with_events: "Running your forecast", money_health: "Checking your money fitness",
    get_safe_to_save: "Working out what's safe to save", get_monthly_drains: "Finding monthly drains", get_other_accounts: "Reading your other bank (demo)",
    calculate: "Calculating", check: "Checking every number against your data", other: "Looking at your data" },
  fi: { read: "Luen kysymyksesi", get_spending: "Lasken kulujasi yhteen", list_transactions: "Käyn läpi ostojasi",
    get_cashflow: "Vertaan tuloja ja menoja", get_three_baskets: "Jaan menot kolmeen koriin", get_safe_to_spend: "Lasken, mitä voit turvallisesti käyttää",
    simulate_cut: "Kokeilen säästöä luvuillasi", get_surprise_pot: "Mitoitan yllätyspottia", get_payday_pattern: "Katson palkkapäiviäsi",
    get_payday_forecast: "Ennustan palkkapäivään", get_benchmark: "Vertaan Tilastokeskuksen lukuihin", get_spender_type: "Etsin kuluttajatyyppiäsi",
    get_spender_profile: "Etsin kuluttajatyyppiäsi", check_purchase: "Tarkistan hintoja verkosta", plan_home: "Suunnittelen asunnon ostoa",
    show_chart: "Piirrän kuvaajan", forecast_with_events: "Lasken ennusteesi", money_health: "Tarkistan rahakuntoasi",
    get_safe_to_save: "Lasken, mitä voit turvallisesti säästää", get_monthly_drains: "Etsin kuukausittaisia vuotoja", get_other_accounts: "Luen toisen pankkisi (demo)",
    calculate: "Lasken", check: "Tarkistan jokaisen luvun tiedoistasi", other: "Katson tietojasi" },
  sv: { read: "Läser din fråga", get_spending: "Räknar ihop dina utgifter", list_transactions: "Går igenom dina köp",
    get_cashflow: "Jämför pengar in och ut", get_three_baskets: "Sorterar i dina tre korgar", get_safe_to_spend: "Räknar ut vad som är säkert att spendera",
    simulate_cut: "Testar minskningen på dina siffror", get_surprise_pot: "Räknar ut din överraskningspott", get_payday_pattern: "Tittar på dina lönedagar",
    get_payday_forecast: "Räknar fram till lönen", get_benchmark: "Jämför med Statistikcentralen", get_spender_type: "Letar efter din spendertyp",
    get_spender_profile: "Letar efter din spendertyp", check_purchase: "Kollar priser på nätet", plan_home: "Planerar bostadsköpet",
    show_chart: "Ritar ett diagram", forecast_with_events: "Kör din prognos", money_health: "Kollar din ekonomiska kondition",
    get_safe_to_save: "Räknar ut vad som är säkert att spara", get_monthly_drains: "Letar efter månatliga läckor", get_other_accounts: "Läser din andra bank (demo)",
    calculate: "Räknar", check: "Kollar varje siffra mot dina data", other: "Tittar på dina data" },
};
function coachStepText(st) {
  const S = STEP_TXT[lang] || STEP_TXT.en, base = S[st.tool] || S.other;
  const on = st.subcategory ? label(st.subcategory) : st.category ? label(st.category) : st.basket ? T().baskets[st.basket][0] : st.item || "";
  return on ? `${base}: ${on}` : base;
}
function addStep(msg, st) {
  const ol = msg.querySelector(".csteps ol"); if (!ol) return;
  const txt = coachStepText(st), last = ol.lastElementChild;
  if (last && last.dataset.t === txt) return;        // the same tool twice in a row is one step
  if (last) last.classList.add("done");
  const li = document.createElement("li"); li.dataset.t = txt; li.textContent = txt;
  ol.appendChild(li);
}
// The answer with live steps (NDJSON from /api/chat/stream); falls back to the plain endpoint if streaming fails.
async function chatStream(body, onStep) {
  let r;
  try {
    r = await fetch("/api/chat/stream", { method: "POST", body, headers: { "Content-Type": "application/json", "X-AI-Provider": aiProvider() } });
  } catch { r = null; }
  if (r && r.status === 401) { location.href = "/login"; throw new Error("login"); }
  if (r && r.ok && r.body) {
    const rd = r.body.getReader(), dec = new TextDecoder(); let buf = "";
    for (;;) {
      const { value, done } = await rd.read();
      buf += dec.decode(value || new Uint8Array(), { stream: !done });
      let nl;
      while ((nl = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, nl).trim(); buf = buf.slice(nl + 1);
        if (!line) continue;
        const ev = JSON.parse(line);
        if (ev.step) onStep(ev.step); else if (ev.done) return ev.done;
      }
      if (done) break;
    }
  }
  return api("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body });
}

async function ask(text) {
  text = (text || "").trim();
  if (!text || busy || !cid) return;
  setTab("coach");
  busy = true; $("#send").disabled = true; $("#q").value = "";
  addMsg("user", esc(text));
  history.push({ role: "user", text });
  const pending = addMsg("bot", `<div class="csteps" role="status" aria-label="${esc(T().thinking)}"><ol></ol></div>`, "working");
  addStep(pending, { tool: "read" });
  try {
    const r = await chatStream(JSON.stringify({ customer_id: cid, history, lang }), (st) => addStep(pending, st));
    pending.classList.remove("working");
    pending.innerHTML = answerHtml(r);
    if (window.learnAfterAnswer) window.learnAfterAnswer(r, pending);  // Money Detective: a new question lights up the map
    if (r.error) { pending.classList.add("err"); history.pop(); } else if (r.refused) { history.pop(); } else history.push({ role: "assistant", text: r.answer });
  } catch (e) {
    pending.classList.add("err"); pending.textContent = T().wentWrong; history.pop();
  }
  pending.scrollIntoView({ behavior: "smooth", block: "start" });
  busy = false; $("#send").disabled = false;
}

/* ---------- shell ---------- */
function persona() { return personas.find((p) => p.id === cid) || { name: "?", tagline: "" }; }
function bindAsks(root) { root.querySelectorAll("[data-ask]").forEach((b) => b.addEventListener("click", () => ask(b.dataset.ask))); }

function setTab(t) {
  tab = t;
  for (const v of ["home", "coach", "learn"]) $(`#view-${v}`).hidden = v !== t;
  $("#composer").hidden = t !== "coach";
  document.querySelectorAll("#tabbar button").forEach((b) => b.classList.toggle("on", b.dataset.tab === t));
  document.body.dataset.tab = t;
  if (t !== "coach") window.scrollTo({ top: 0 });
}

function renderStatic() {
  document.documentElement.lang = lang;
  $("#lang").textContent = lang.toUpperCase();
  document.querySelectorAll("#tabbar span").forEach((s, i) => (s.textContent = T().tabs[i]));
  $("#ask-title").textContent = T().ask;
  $("#q").placeholder = T().placeholder;
  $("#chips").innerHTML = T().suggestions.map((s) => `<button class="chip" data-ask="${esc(s)}">${esc(s)}</button>`).join("");
  bindAsks($("#chips"));
  const p = persona();
  $("#who-initial").textContent = p.name[0]; $("#who-name").textContent = p.name;
}

function showPicker() {
  const s = sheet(`<h2>${T().whoseMoney}</h2><p class="sub">${T().pickNote}</p>
    ${personas.map((p) => `<button class="persona" data-id="${p.id}"><span class="avatar">${esc(p.name[0])}</span>
      <span><b>${esc(p.name)}</b><br><span class="t">${esc(p.tagline)}</span></span></button>`).join("")}
    <p class="note">${T().namesNote}</p>`);
  s.querySelectorAll(".persona").forEach((b) => b.addEventListener("click", () => {
    cid = b.dataset.id; localStorage.setItem("cid", cid); closeSheet();
    history = []; $("#thread").innerHTML = ""; load();
  }));
}

async function load() {
  renderStatic(); setTab("home");
  try { home = await api(`/api/home/${cid}`); } catch (e) { return; }
  renderHome(); renderLearn();
}

$("#ask").addEventListener("submit", (e) => { e.preventDefault(); ask($("#q").value); });
$("#who").addEventListener("click", showPicker);
$("#lang").addEventListener("click", () => {
  lang = { en: "fi", fi: "sv", sv: "en" }[lang]; localStorage.setItem("lang", lang);
  renderStatic(); renderHome(); renderLearn();
});
document.querySelectorAll("#tabbar button").forEach((b) => b.addEventListener("click", () => setTab(b.dataset.tab)));
document.addEventListener("click", (e) => {
  const n = e.target.closest("#thread .num, #asks .num"); if (n) numberSheet(n);
});
document.addEventListener("keydown", (e) => {
  const n = e.target.closest && e.target.closest("#thread .num, #asks .num"); if (n && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); numberSheet(n); }
});

(async () => {
  personas = await api("/api/personas");
  renderStatic();
  if (!cid || !personas.some((p) => p.id === cid)) showPicker(); else load();
})();
