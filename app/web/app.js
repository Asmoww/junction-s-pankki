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

async function api(path, opts) {
  const r = await fetch(path, opts);
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

function potSheet() {
  const pot = home.pot, payday = home.overview.safe_to_spend.next_payday;
  const s = sheet(`<h2>${T().potTitle}</h2><p class="sub">${T().potSheet(eur0(pot.suggested_monthly_pot_eur), day(payday))}</p>
    ${potChart(pot.months.slice(-12), pot.average_per_month_last_12_eur)}<p class="note">${T().demoNote}</p>
    <button class="btn wide" data-close>${T().ok}</button>`);
  s.querySelector("[data-close]").addEventListener("click", closeSheet);
}

function psd2Sheet() {
  const s = sheet(`<h2>${T().psd2Title}</h2><p class="sub">${T().psd2Body}</p>
    <ul class="checks">${T().psd2Scope.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
    <div class="label" style="margin:14px 4px 8px">${T().chooseBank}</div>
    <div class="banks">${BANKS.map((b, i) => `<label><input type="radio" name="bank" value="${b}" ${i ? "" : "checked"}><span>${b}</span></label>`).join("")}</div>
    <p class="note">${T().demoNote}</p><button class="btn wide" data-allow>${T().psd2Allow}</button>`);
  s.querySelector("[data-allow]").addEventListener("click", () => {
    const bank = s.querySelector("input[name=bank]:checked").value;
    localStorage.setItem(psd2Key(), bank); closeSheet(); toast(esc(T().psd2Done(bank)), 5000); renderHome();
  });
}

/* ---------- learn ---------- */
let game = null;
function renderLearn() {
  if (!home) return;
  const t = home.type, [tname, tsum] = T().types[t.type] || [t.type, t.summary];
  const fmtSig = (k, v) => (v === null || v === undefined ? "–" : k.includes("percent") ? `${v > 0 ? "+" : ""}${v} %`
    : k === "transactions_while_overdrawn" ? v : `${Math.round(v * 100)} %`);
  const sig = Object.entries(t.signals).map(([k, v]) => `<li><span>${esc(T().signals[k] || k)}</span><span class="amt">${fmtSig(k, v)}</span></li>`).join("");
  $("#view-learn").innerHTML = `
    <section class="card typecard"><div class="label">${T().typeTitle}</div><div class="type">${esc(tname)}</div><p class="lead">${esc(tsum)}</p>
      <details class="how"><summary>${T().typeSignals}</summary><ul class="steps">${sig}</ul></details></section>
    <section class="card" id="game"></section>
    <section class="card" id="trust"><div class="label">${T().trustTitle}</div><div class="skeleton"></div></section>`;
  renderGame();
  renderTrust();
}

function renderGame() {
  const el = $("#game"); if (!el) return;
  if (!game) {
    el.innerHTML = `<div class="label">${T().gameTitle}</div><p class="lead">${T().gameIntro}</p><button class="btn" id="g-start">${T().gameStart}</button>`;
    $("#g-start").onclick = async () => { const g = await api(`/api/game/${cid}?seed=${Date.now() % 100000}`); game = { items: g.items, i: 0, score: 0, answered: false }; renderGame(); };
    return;
  }
  if (game.i >= game.items.length) {
    el.innerHTML = `<div class="label">${T().gameTitle}</div><div class="big">${T().gameScore(game.score, game.items.length)}</div><button class="btn" id="g-again">${T().gameAgain}</button>`;
    $("#g-again").onclick = () => { game = null; renderGame(); $("#g-start").click(); };
    return;
  }
  const it = game.items[game.i];
  el.innerHTML = `<div class="label">${T().gameTitle} · ${game.i + 1}/${game.items.length}</div>
    <div class="tx"><div><b>${esc(label(it.merchant_type))}</b><div class="sub">${day(it.date)}</div></div><div class="amount">${eur(it.amount_eur)}</div></div>
    <div class="choices">${[1, 2, 3].map((b) => `<button class="choice" data-b="${b}"><i style="background:${BASKET_COLORS[b]}"></i>${esc(T().baskets[b][0])}</button>`).join("")}</div>
    <div class="feedback"></div>`;
  el.querySelectorAll(".choice").forEach((c) => c.addEventListener("click", () => {
    if (game.answered) return; game.answered = true;
    const b = +c.dataset.b, right = b === it.basket;
    if (right) game.score++;
    el.querySelectorAll(".choice").forEach((x) => { if (+x.dataset.b === it.basket) x.classList.add("right"); else if (x === c) x.classList.add("wrong"); });
    el.querySelector(".feedback").innerHTML = `<p><b>${right ? T().gameRight : esc(T().gameWrong(T().baskets[it.basket][0]))}</b> ${esc(it.why)}</p><button class="btn" id="g-next">${T().gameNext}</button>`;
    $("#g-next").onclick = () => { game.i++; game.answered = false; renderGame(); };
  }));
}

async function renderTrust() {
  const el = $("#trust"); if (!el) return;
  let d; try { d = await api("/api/traps"); } catch { return; }
  const run = d.runs && d.runs[0];
  if (!run) { el.innerHTML = `<div class="label">${T().trustTitle}</div><p class="sub">${T().trustNone}</p>`; return; }
  el.innerHTML = `<div class="label">${T().trustTitle}</div><div class="big">${T().passed(run.passed, run.total)}</div>
    <p class="sub">${T().trustSub}</p><p class="note left">${esc(run.at)} · ${esc(run.model)} · ${T().verified(run.numbers_verified, run.numbers_total)}</p>
    <ul class="traps">${run.cases.map((c) => `<li class="${c.ok ? "ok" : "bad"}"><span class="mark">${c.ok ? "✓" : "✗"}</span><span><b>${esc(c.trap)}</b><br>
      <span class="sub">“${esc(c.question)}”</span>${c.ok ? "" : `<br><span class="why">${esc(c.failed.join("; "))}</span>`}</span></li>`).join("")}</ul>`;
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

function markNumbers(html, numbers) {
  let pos = 0;
  for (const n of numbers || []) {
    const t = esc(n.text), i = html.indexOf(t, pos);
    if (i < 0) continue;
    const span = `<span class="num ${n.status}" data-status="${n.status}" data-src="${esc(n.source || "")}">${t}</span>`;
    html = html.slice(0, i) + span + html.slice(i + t.length); pos = i + span.length;
  }
  return html;
}

const TOOL_LABEL = {
  get_spending: "Added up your spending", list_transactions: "Listed transactions", get_cashflow: "Checked money in and out",
  get_three_baskets: "Split spending into the three baskets", get_safe_to_spend: "Calculated safe-to-spend", simulate_cut: "Simulated the cut",
  get_spender_profile: "Compared your habits with your age group", get_surprise_pot: "Looked at surprise costs month by month",
  get_payday_pattern: "Compared spending before and after payday", get_payday_forecast: "Projected your balance to payday",
  get_benchmark: "Compared with Statistics Finland", get_spender_type: "Worked out your spender type", calculate: "Calculated",
  show_chart: "Drew a chart from your transactions", forecast_with_events: "Put your planned costs on their dates",
  check_purchase: "Checked live prices on shop pages", plan_home: "Planned a home purchase with live rules", money_health: "Worked out your money fitness score",
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
  const nums = (r.numbers || []).filter((n) => n.status !== "suggestion" && n.status !== "yours"), v = nums.filter((n) => n.status !== "unverified").length;
  const badge = nums.length ? `<div class="vbadge ${v === nums.length ? "all" : "some"}">${v === nums.length ? "✓" : "!"} ${T().verified(v, nums.length)}</div>` : "";
  const att = (r.attachments || []).map((a) => `<div class="att">${renderAttachment(a)}</div>`).join("");
  const u = r.usage || {}, pv = r.privacy || {};
  const how = r.trace && r.trace.length ? `<details class="how"><summary>${T().howWorked}</summary><ul class="trace">${r.trace.map(traceLine).join("")}</ul></details>` : "";
  const saw = u.model ? `<details class="how"><summary>${T().whatAiSaw}</summary><ul class="trace">
    <li><b>${T().model}</b>: ${esc(u.model)} · ${u.calls} × · ${nf(0).format(u.input_tokens + u.cache_read_tokens + u.cache_write_tokens)} / ${nf(0).format(u.output_tokens)} ${T().tokens}</li>
    <li><b>${T().cost}</b>: $${u.cost_usd.toFixed(3)}</li><li><b>${T().sent}</b>: ${esc(pv.sent)}</li><li><b>${T().neverSent}</b>: ${esc(pv.never_sent)}</li></ul></details>` : "";
  return markNumbers(md(r.answer), nums) + att + badge + how + saw;
}

function addMsg(role, html, cls = "") {
  const d = document.createElement("div");
  d.className = `msg ${role} ${cls}`; d.innerHTML = html;
  $("#thread").appendChild(d); d.scrollIntoView({ behavior: "smooth", block: "end" });
  return d;
}

async function ask(text) {
  text = (text || "").trim();
  if (!text || busy || !cid) return;
  setTab("coach");
  busy = true; $("#send").disabled = true; $("#q").value = "";
  addMsg("user", esc(text));
  history.push({ role: "user", text });
  const pending = addMsg("bot", `<span class="typing"><i></i><i></i><i></i></span> <span class="sub">${T().thinking}</span>`);
  try {
    const r = await api("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ customer_id: cid, history, lang }) });
    pending.innerHTML = answerHtml(r);
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
    history = []; game = null; $("#thread").innerHTML = ""; load();
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
$("#thread").addEventListener("click", (e) => {
  const n = e.target.closest(".num"); if (!n) return;
  const st = n.dataset.status;
  toast(st === "unverified" ? `<b>${T().numUnverified}</b>` : st === "yours" ? `<b>${T().numYours}</b>`
    : `<b>${st === "verified" ? T().numVerified : st === "derived" ? T().numDerived : T().numRounded}</b><br><code>${esc(n.dataset.src)}</code>`);
});

(async () => {
  personas = await api("/api/personas");
  renderStatic();
  if (!cid || !personas.some((p) => p.id === cid)) showPicker(); else load();
})();
