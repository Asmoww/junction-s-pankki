// Money coach mobile UI. Numbers on screen come from /api (deterministic queries); the coach explains them.
const $ = (s) => document.querySelector(s);
const nf = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const nf0 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const eur = (x) => `${nf.format(x)} €`;
const eur0 = (x) => `${nf0.format(Math.round(x))} €`;
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const BASKET_COLORS = { 1: "var(--b1)", 2: "var(--b2)", 3: "var(--b3)" };
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const fmtDate = (iso) => { const d = new Date(iso + "T12:00:00"); return `${d.getDate()} ${MONTHS[d.getMonth()].slice(0, 3)}`; };

const SUGGESTIONS = [
  "What is safe for me to spend this week?",
  "How much did I spend on taxis last month?",
  "What kind of spender am I?",
  "How much could I save if I reduced dining out by 20%?",
  "Where did my money go in September?",
  "What were my biggest purchases this year?",
];

let personas = [];
let cid = localStorage.getItem("cid");
let history = [];
let busy = false;

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (r.status === 401) { location.href = "/login"; throw new Error("login"); }
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

function persona() { return personas.find((p) => p.id === cid) || { name: cid, tagline: "" }; }

function showPicker() {
  const root = $("#sheet-root");
  root.innerHTML = `<div class="sheet-bg"><div class="sheet" role="dialog" aria-label="Choose a customer">
    <h2>Whose money?</h2>
    <p class="sub">Pick a demo customer. Their transactions are synthetic data modelled on S-Bank data.</p>
    ${personas.map((p) => `<button class="persona" data-id="${p.id}"><span class="avatar">${esc(p.name[0])}</span>
      <span><b>${esc(p.name)}</b><br><span class="t">${esc(p.tagline)}</span></span></button>`).join("")}
    <p class="note">Names are invented for the demo.</p></div></div>`;
  root.querySelectorAll(".persona").forEach((b) => b.addEventListener("click", () => {
    cid = b.dataset.id; localStorage.setItem("cid", cid); root.innerHTML = ""; history = [];
    $("#thread").innerHTML = ""; load();
  }));
  root.querySelector(".sheet-bg").addEventListener("click", (e) => { if (e.target === e.currentTarget && cid) root.innerHTML = ""; });
}

function renderSafe(s) {
  const el = $("#safe");
  const short = s.safe_until_payday_eur < 0;
  el.className = "card" + (short ? " warn" : "");
  const steps = s.steps.map((st) => `<li><span>${esc(st.step)}</span><span class="amt">${eur(st.eur)}</span></li>`).join("");
  el.innerHTML = `
    <div class="label">Safe to spend this week</div>
    <div class="big">${eur0(s.safe_this_week_eur)}</div>
    <div class="sub">${short
      ? `You are about <b>${eur0(-s.safe_until_payday_eur)}</b> short before payday on ${fmtDate(s.next_payday)}.`
      : `${eur0(s.safe_per_day_eur)} a day until payday on ${fmtDate(s.next_payday)}. You usually spend ${eur0(s.your_usual_extras_per_week_eur)} a week on extras.`}</div>
    <details class="how"><summary>How is this calculated?</summary>
      <ul class="steps">${steps}<li><span>Safe until payday (${s.days_until_payday} days)</span><span class="amt">${eur(s.safe_until_payday_eur)}</span></li></ul>
    </details>`;
}

function renderBaskets(o) {
  const m = o.month;
  const total = m.total_spending_eur || 1;
  const monthName = MONTHS[new Date(m.period.start + "T12:00:00").getMonth()];
  const bar = m.baskets.map((b) => `<span style="width:${(b.total_eur / total) * 100}%;background:${BASKET_COLORS[b.basket]}"></span>`).join("");
  const rows = m.baskets.map((b) => {
    const avg = o.six_month_avg_eur[b.basket];
    const d = b.total_eur - avg;
    const pending = b.basket === 1 && o.not_yet_charged_this_month.length;
    const delta = pending ? `<div class="delta">${esc(o.not_yet_charged_this_month.join(" & ").replace("Housing", "Rent"))} not charged yet</div>`
      : avg > 0 && Math.abs(d) >= 5
      ? `<div class="delta ${d > 0 ? "up" : "down"}">${d > 0 ? "+" : "−"}${eur0(Math.abs(d))} vs usual</div>` : `<div class="delta">about usual</div>`;
    return `<button class="basket" data-name="${esc(b.name)}">
      <span class="dot" style="background:${BASKET_COLORS[b.basket]}"></span>
      <span><div class="name">${esc(b.name)}</div><div class="meaning">${esc(b.meaning)}</div></span>
      <span class="right"><div class="amount">${eur0(b.total_eur)}</div>${delta}</span><span class="chev">›</span></button>`;
  }).join("");
  $("#baskets").innerHTML = `<div class="label">${monthName} in three baskets</div>
    <div class="big">${eur0(m.total_spending_eur)}</div><div class="sub">spent in ${monthName} · "usual" = average of the 6 months before</div>
    <div class="bar">${bar}</div>${rows}`;
  $("#baskets").querySelectorAll(".basket").forEach((b) => b.addEventListener("click", () => ask(`What's in my ${b.dataset.name.toLowerCase()} this month?`)));
}

async function load() {
  const p = persona();
  $("#who-initial").textContent = p.name[0];
  $("#who-name").textContent = p.name;
  $("#greet").textContent = `Hi ${p.name} · balance on 30 Sep 2026`;
  try {
    const o = await api(`/api/overview/${cid}`);
    $("#balance").innerHTML = `${eur(o.customer.balance)}`;
    renderSafe(o.safe_to_spend);
    renderBaskets(o);
  } catch (e) {
    if (e.message !== "login") $("#safe").innerHTML = `<div class="sub">Could not load your data. Pull to refresh.</div>`;
  }
}

function md(text) {
  const lines = esc(text).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").split("\n");
  let html = "", list = false, para = [];
  const flush = () => { if (para.length) { html += `<p>${para.join("<br>")}</p>`; para = []; } };
  for (const raw of lines) {
    const l = raw.trim();
    const li = l.match(/^([-•*]|\d+\.)\s+(.*)/);
    if (li) { flush(); if (!list) { html += "<ul>"; list = true; } html += `<li>${li[2]}</li>`; continue; }
    if (list) { html += "</ul>"; list = false; }
    if (!l) flush(); else para.push(l.replace(/^#+\s*/, ""));
  }
  flush(); if (list) html += "</ul>";
  return html;
}

const TOOL_LABEL = {
  get_spending: "Added up your spending", list_transactions: "Listed transactions", get_cashflow: "Checked money in and out",
  get_three_baskets: "Split spending into the three baskets", get_safe_to_spend: "Calculated safe-to-spend",
  simulate_cut: "Simulated the cut", get_spender_profile: "Compared your habits with your age group",
};

function traceLine(t) {
  const r = t.result || {}, i = t.input || {};
  if (t.error) return `<li><b>${TOOL_LABEL[t.tool] || t.tool}</b>: retried (${esc(r.error || "error")})</li>`;
  const per = r.period || r.based_on;
  const when = per ? ` · ${fmtDate(per.start)} – ${fmtDate(per.end)} ${per.end.slice(0, 4)}` : "";
  const what = [i.category, i.subcategory, i.basket && `basket ${i.basket}`].filter(Boolean).join(", ");
  let val = "";
  if (t.tool === "get_spending") val = `${eur(r.total_eur)} in ${r.transactions} purchases` + (r.not_classifiable ? `; ${eur(r.not_classifiable.total_eur)} had no merchant type` : "");
  if (t.tool === "simulate_cut") val = `${eur(r.now_per_month_eur)}/month now → saves ${eur(r.saving_per_month_eur)}/month`;
  if (t.tool === "get_safe_to_spend") val = `${eur(r.safe_this_week_eur)} this week`;
  if (t.tool === "get_cashflow") val = `in ${eur(r.income_eur.total)}, out ${eur(r.spending_eur.total)}`;
  if (t.tool === "get_three_baskets") val = r.baskets.map((b) => `${b.name} ${eur0(b.total_eur)}`).join(", ");
  if (t.tool === "list_transactions") val = `${r.transactions.length} transactions`;
  if (t.tool === "get_spender_profile") val = `extras ${Math.round(r.you.extras_share_of_spending * 100)}% of spending vs ${Math.round(r.peers_same_age_group.median_extras_share * 100)}% for ages ${r.peers_same_age_group.age_group}`;
  return `<li><b>${TOOL_LABEL[t.tool] || t.tool}</b>${what ? ` · ${esc(what)}` : ""}${when}${val ? `<br>→ ${esc(val)}` : ""}</li>`;
}

function addMsg(role, html, cls = "") {
  const d = document.createElement("div");
  d.className = `msg ${role} ${cls}`;
  d.innerHTML = html;
  $("#thread").appendChild(d);
  d.scrollIntoView({ behavior: "smooth", block: "end" });
  return d;
}

async function ask(text) {
  text = text.trim();
  if (!text || busy || !cid) return;
  busy = true; $("#send").disabled = true; $("#q").value = "";
  addMsg("user", esc(text));
  history.push({ role: "user", text });
  const pending = addMsg("bot", `<span class="typing"><i></i><i></i><i></i></span>`);
  try {
    const r = await api("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ customer_id: cid, history }) });
    const how = r.trace.length ? `<details class="how"><summary>How I worked this out</summary><ul class="trace">${r.trace.map(traceLine).join("")}</ul></details>` : "";
    pending.innerHTML = md(r.answer) + how;
    if (r.error) { pending.classList.add("err"); history.pop(); }
    else history.push({ role: "assistant", text: r.answer });
  } catch (e) {
    pending.classList.add("err"); pending.textContent = "Something went wrong. Please try again."; history.pop();
  }
  pending.scrollIntoView({ behavior: "smooth", block: "end" });
  busy = false; $("#send").disabled = false;
}

$("#ask").addEventListener("submit", (e) => { e.preventDefault(); ask($("#q").value); });
$("#who").addEventListener("click", showPicker);
$("#chips").innerHTML = SUGGESTIONS.map((s) => `<button class="chip">${esc(s)}</button>`).join("");
$("#chips").querySelectorAll(".chip").forEach((c) => c.addEventListener("click", () => ask(c.textContent)));

(async () => {
  personas = await api("/api/personas");
  if (!cid || !personas.some((p) => p.id === cid)) showPicker(); else load();
})();
