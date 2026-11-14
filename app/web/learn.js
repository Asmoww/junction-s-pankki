// Money Detective: rewards wanting to learn about your own money. Backend: app/learning.py, /api/learn.
// What counts: looking into a new corner of your money (asked, opened the steps, tried a what-if, corrected a basket,
// guessed first). Each (concept, kind) counts once, so repeating a question earns nothing. Never rewarded: spending
// less, earning more, buying a product, sharing more data. Nothing here has euros in it and nothing ever resets.
(() => {
  const L10N = {
    en: {
      title: "Money Detective", explored: (n, t) => `${n} of ${t}`, exploredSub: "corners of your own money explored",
      kinds: ["asked", "opened the steps", "tried a what-if", "corrected", "guessed first"],
      legend: "Each dot is a different way of looking: asking, opening the steps, trying a what-if, correcting, guessing first. Each counts once, so only new questions light it up.",
      tapHint: "Tap a corner to ask about it.",
      week: (n, g) => `This week: ${Math.min(n, g)} of ${g}${n >= g ? " ✓" : ""}. A missed week resets nothing.`,
      sharper: (a, b) => `Your guesses: earlier off by ${a} %, lately off by ${b} %.`,
      sharperWait: (n) => `Guess before you look. After 4 guesses you'll see if your sense of your money gets sharper (${n} so far).`,
      checkTitle: "Check yourself", status: { not_explored: "Not started", explored: "Guessed", explained: "Understood ✓", revisited: "Still knew it ✓✓" },
      firstTry: "first try", due: "Ready to revisit", newLit: (c) => `New on your money map: ${c}`, deeper: (c, k, n) => `${c}: ${k} (${n} of 5)`,
      you: "You guessed", next: "Next", done: "Done", again: "Try again", hide: "Hide rewards", show: "Show rewards", reset: "Start over",
      resetQ: "Clear your Money Detective progress for this person on this device?", openMap: "See map",
      private: "Only you see this. It has no money in it and doesn't affect anything else in the app.",
      noGuessWrong: "A guess is never wrong here. It's compared with your data, not scored.",
      ask: {
        where_money_goes: "Where did my money go last month?", baskets: "Split my spending into the three baskets",
        spending_room: "What is safe for me to spend this week?", irregular: "How often do surprise costs hit me?",
        what_if: "How much could I save if I cut dining out by 20 %?", forecast: "Why am I always short before payday?",
        compare: "How do I compare with people my age?", big_decisions: "When could I afford a 250,000 € home?",
        saving: "How much is safe for me to save this month?",
      },
    },
    fi: {
      title: "Rahaetsivä", explored: (n, t) => `${n}/${t}`, exploredSub: "oman rahasi kulmaa tutkittu",
      kinds: ["kysyit", "avasit laskun", "kokeilit entä jos", "korjasit", "arvasit ensin"],
      legend: "Jokainen piste on eri tapa katsoa: kysyä, avata lasku, kokeilla entä jos, korjata, arvata ensin. Kukin lasketaan kerran, joten vain uudet kysymykset sytyttävät sen.",
      tapHint: "Napauta kulmaa kysyäksesi siitä.",
      week: (n, g) => `Tällä viikolla: ${Math.min(n, g)}/${g}${n >= g ? " ✓" : ""}. Väliin jäänyt viikko ei nollaa mitään.`,
      sharper: (a, b) => `Arvauksesi: aiemmin ${a} % pielessä, viime aikoina ${b} %.`,
      sharperWait: (n) => `Arvaa ennen kuin katsot. Neljän arvauksen jälkeen näet, tarkentuuko tuntumasi omaan rahaasi (${n} tähän mennessä).`,
      checkTitle: "Testaa itsesi", status: { not_explored: "Aloittamatta", explored: "Arvattu", explained: "Ymmärretty ✓", revisited: "Muistit yhä ✓✓" },
      firstTry: "ensi yrittämällä", due: "Valmis kertaukseen", newLit: (c) => `Uusi rahakartallasi: ${c}`, deeper: (c, k, n) => `${c}: ${k} (${n}/5)`,
      you: "Arvasit", next: "Seuraava", done: "Valmis", again: "Yritä uudelleen", hide: "Piilota palkinnot", show: "Näytä palkinnot", reset: "Aloita alusta",
      resetQ: "Tyhjennetäänkö tämän henkilön Rahaetsivä-edistyminen tällä laitteella?", openMap: "Näytä kartta",
      private: "Vain sinä näet tämän. Siinä ei ole rahasummia, eikä se vaikuta mihinkään muuhun sovelluksessa.",
      noGuessWrong: "Arvaus ei ole koskaan väärin. Sitä verrataan dataasi, ei pisteytetä.",
      ask: {
        where_money_goes: "Mihin rahani meni viime kuussa?", baskets: "Jaa kulutukseni kolmeen koriin",
        spending_room: "Paljonko voin turvallisesti käyttää tällä viikolla?", irregular: "Kuinka usein yllättävät menot osuvat minuun?",
        what_if: "Paljonko säästäisin, jos vähentäisin ulkona syömistä 20 %?", forecast: "Miksi rahat loppuvat aina ennen palkkapäivää?",
        compare: "Miten vertaudun ikäisiini?", big_decisions: "Milloin minulla olisi varaa 250 000 €:n asuntoon?",
        saving: "Paljonko voin turvallisesti säästää tässä kuussa?",
      },
    },
    sv: {
      title: "Pengadetektiven", explored: (n, t) => `${n} av ${t}`, exploredSub: "hörn av dina egna pengar utforskade",
      kinds: ["frågade", "öppnade stegen", "provade tänk om", "rättade", "gissade först"],
      legend: "Varje prick är ett nytt sätt att titta: fråga, öppna stegen, pröva tänk om, rätta, gissa först. Var och en räknas en gång, så bara nya frågor tänder den.",
      tapHint: "Tryck på ett hörn för att fråga om det.",
      week: (n, g) => `Den här veckan: ${Math.min(n, g)} av ${g}${n >= g ? " ✓" : ""}. En missad vecka nollställer ingenting.`,
      sharper: (a, b) => `Dina gissningar: tidigare ${a} % fel, på sistone ${b} %.`,
      sharperWait: (n) => `Gissa innan du tittar. Efter 4 gissningar ser du om din känsla för dina pengar blir skarpare (${n} hittills).`,
      checkTitle: "Testa dig själv", status: { not_explored: "Inte börjat", explored: "Gissat", explained: "Förstått ✓", revisited: "Kom ihåg det ✓✓" },
      firstTry: "första försöket", due: "Redo att repetera", newLit: (c) => `Nytt på din pengakarta: ${c}`, deeper: (c, k, n) => `${c}: ${k} (${n} av 5)`,
      you: "Du gissade", next: "Nästa", done: "Klart", again: "Försök igen", hide: "Dölj belöningar", show: "Visa belöningar", reset: "Börja om",
      resetQ: "Rensa Pengadetektivens framsteg för den här personen på den här enheten?", openMap: "Visa kartan",
      private: "Bara du ser det här. Det innehåller inga belopp och påverkar inget annat i appen.",
      noGuessWrong: "En gissning är aldrig fel här. Den jämförs med dina data, den poängsätts inte.",
      ask: {
        where_money_goes: "Vart gick mina pengar förra månaden?", baskets: "Dela upp mina utgifter i de tre korgarna",
        spending_room: "Hur mycket kan jag tryggt spendera den här veckan?", irregular: "Hur ofta drabbas jag av oväntade kostnader?",
        what_if: "Hur mycket kunde jag spara om jag åt ute 20 % mindre?", forecast: "Varför är det alltid tunt före lönedagen?",
        compare: "Hur står jag mig mot andra i min ålder?", big_decisions: "När har jag råd med en bostad för 250 000 €?",
        saving: "Hur mycket kan jag tryggt spara den här månaden?",
      },
    },
  };
  const KINDS = ["asked", "opened_steps", "tried_whatif", "corrected", "guessed"];
  const QUEST_CONCEPT = { q1: "baskets", q2: "spending_room", q3: "irregular" };
  const X = () => L10N[lang] || L10N.en;
  const device = localStorage.getItem("device") || (() => {
    const d = (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2)).slice(0, 36);
    localStorage.setItem("device", d); return d;
  })();
  const eid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  const post = (path, body) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ device, event_id: eid(), ...body }) });
  let st = null;
  const conceptName = (c) => (st && st.curiosity.map.find((m) => m.concept === c) || {}).name || c;

  async function refresh() {
    if (!cid) return;
    try { st = await api(`/api/learn/${cid}?device=${encodeURIComponent(device)}&lang=${lang}`); } catch { st = null; }
    paint();
  }

  // Record one kind of curiosity for each concept; show a small note under the answer (or a toast) only when it's new.
  async function learnNote(concepts, kind, el) {
    if (!cid || !concepts || !concepts.length) return;
    const rs = await Promise.all(concepts.map((c) => post(`/api/learn/${cid}/curiosity`, { concept: c, kind }).catch(() => null)));
    const fresh = rs.filter((r) => r && r.new);
    if (!fresh.length) return;
    if (!st) await refresh(); else refresh();
    if (st && st.settings && st.settings.hide_rewards) return;
    const r = fresh[0], name = conceptName(r.concept);
    const text = r.kinds_seen.length === 1 ? X().newLit(name) : X().deeper(name, X().kinds[KINDS.indexOf(kind)], r.kinds_seen.length);
    if (el) {
      const b = document.createElement("button");
      b.className = "lnote"; b.innerHTML = `<span class="spark">✦</span> ${esc(text)} <span class="go">${X().openMap} ›</span>`;
      b.onclick = () => setTab("learn"); el.appendChild(b);
    } else toast(`✦ ${esc(text)}`, 3000);
  }

  function learnAfterAnswer(r, el) {
    const cs = r.concepts || []; if (!cs.length || r.error) return;
    learnNote(cs, "asked", el);
    el.querySelectorAll("details.how").forEach((d) => {
      if (d.querySelector("summary").textContent !== T().howWorked) return;
      d.addEventListener("toggle", () => { if (d.open && !d.dataset.counted) { d.dataset.counted = "1"; learnNote(cs, "opened_steps", el); } });
    });
  }

  function cardHtml() { return `<section class="card detective" id="detective"><div class="label">${X().title}</div><div class="skeleton"></div></section>`; }

  function paint() {
    const el = $("#detective"); if (!el) return;
    if (!st) { el.innerHTML = `<div class="label">${X().title}</div><p class="sub">${T().wentWrong}</p>`; return; }
    const cu = st.curiosity, hide = st.settings.hide_rewards;
    const tiles = cu.map.map((m) => `<button class="ltile ${m.lit ? "lit" : ""}" data-concept="${m.concept}">
      <span class="lname">${esc(m.name)}</span><span class="pips">${KINDS.map((k, i) => `<i class="${m.kinds_seen.includes(k) ? "on" : ""}" title="${esc(X().kinds[i])}"></i>`).join("")}</span></button>`).join("");
    const guess = cu.sharper ? X().sharper(cu.sharper.earlier_off_by_pct, cu.sharper.lately_off_by_pct) : X().sharperWait(cu.guesses);
    const quests = st.concepts.map((q) => {
      const due = (st.revisits_due || []).includes(q.quest);
      return `<button class="lquest ${q.status}" data-quest="${q.quest}" data-revisit="${due ? 1 : ""}"><span><b>${esc(q.title)}</b>
        ${q.first_try ? `<em>${X().firstTry}</em>` : ""}</span><span class="lst">${due ? X().due : X().status[q.status]}</span><span class="chev">›</span></button>`;
    }).join("");
    const ms = !hide && st.milestones ? `<div class="lms">${st.milestones.map((m) => `<span class="${m.reached ? "on" : ""}">${m.reached ? "🏅" : "○"} ${esc(m.title)}</span>`).join("")}</div>` : "";
    el.innerHTML = `<div class="label">${X().title}</div>
      ${hide ? "" : `<div class="big">${X().explored(cu.concepts_explored, cu.concepts_total)}</div><div class="sub">${X().exploredSub}</div>`}
      <div class="lmap">${tiles}</div><p class="note left">${X().tapHint} ${X().legend}</p>
      ${hide ? "" : `<p class="lline">🗓️ ${esc(X().week(st.this_week, st.weekly_goal))}</p>`}
      <p class="lline">🎯 ${esc(guess)}</p>
      <div class="label" style="margin-top:14px">${X().checkTitle}</div><div class="lquests">${quests}</div>${ms}
      <p class="note left">${X().private}</p>
      <div class="lfoot"><button class="link" data-hide>${hide ? X().show : X().hide}</button><button class="link" data-reset>${X().reset}</button></div>`;
    el.querySelectorAll("[data-concept]").forEach((b) => b.onclick = () => ask(X().ask[b.dataset.concept]));
    el.querySelectorAll("[data-quest]").forEach((b) => b.onclick = () => openQuest(b.dataset.quest, !!b.dataset.revisit));
    el.querySelector("[data-hide]").onclick = async () => {
      try { await api(`/api/learn/${cid}/settings`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ device, hide_rewards: !hide }) }); } catch {}
      refresh();
    };
    el.querySelector("[data-reset]").onclick = async () => {
      if (!confirm(X().resetQ)) return;
      try { await fetch(`/api/learn/${cid}?device=${encodeURIComponent(device)}`, { method: "DELETE" }); } catch {}
      refresh();
    };
  }

  // A quest: guess from your own data -> see the evidence -> explain why -> feedback. Right answers come from code.
  async function openQuest(qid, revisit) {
    let q; try { q = await api(`/api/learn/${cid}/quest/${qid}?lang=${lang}${revisit ? "&revisit=true" : ""}`); } catch { toast(T().wentWrong); return; }
    const s = sheet(`<h2>${esc(q.title)}</h2><div class="lq"></div>`), box = s.querySelector(".lq");
    const opts = (o) => `<div class="lopts">${o.map((x, i) => `<button class="btn ghost" data-i="${i}">${esc(x)}</button>`).join("")}</div>`;
    const answer = (step, choice) => api(`/api/learn/${cid}`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device, event_id: eid(), quest: qid, step, choice, lang }) });
    const check = (step) => {
      box.innerHTML = `<p class="lead">${esc(q.check.question)}</p>${opts(q.check.options)}<p class="lfb"></p>`;
      box.querySelectorAll("[data-i]").forEach((b) => b.onclick = async () => {
        let r; try { r = await answer(step, +b.dataset.i); } catch { toast(T().wentWrong); return; }
        box.querySelectorAll("[data-i]").forEach((x) => (x.disabled = true));
        b.classList.add(r.correct ? "right" : "wrong");
        box.querySelector(".lfb").innerHTML = `${esc(r.feedback || r.error || "")}<div class="actions">${r.correct
          ? `<button class="btn" data-done>${X().done}</button>` : `<button class="btn" data-again>${X().again}</button>`}</div>`;
        const d = box.querySelector("[data-done]"); if (d) d.onclick = () => { closeSheet(); refresh(); };
        const a = box.querySelector("[data-again]"); if (a) a.onclick = () => check(step);
      });
    };
    if (revisit) return check("revisit");
    const p = q.predict;
    box.innerHTML = `<p class="lead">${esc(p.question)}</p>${opts(p.options)}<p class="note left">${X().noGuessWrong}</p>`;
    box.querySelectorAll("[data-i]").forEach((b) => b.onclick = async () => {
      const i = +b.dataset.i;
      try { await answer("predict", i); } catch { toast(T().wentWrong); return; }
      post(`/api/learn/${cid}/curiosity`, { metric: p.metric, guess: p.values[i], actual: p.actual }).catch(() => {});
      learnNote([QUEST_CONCEPT[qid]], "guessed");
      box.innerHTML = `<p class="sub">${X().you}: <b>${esc(p.options[i])}</b></p><p class="lead lreveal">${esc(q.reveal)}</p>
        <div class="actions"><button class="btn" data-next>${X().next}</button></div>`;
      box.querySelector("[data-next]").onclick = () => check("check");
    });
  }

  Object.assign(window, { learnNote, learnAfterAnswer, learnCard: cardHtml, renderDetective: refresh });
})();
