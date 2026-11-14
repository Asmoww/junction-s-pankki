"""Home, led by the AI without a chat box: a one-line briefing and three questions about your own money.

Same split as everywhere else in the app:
- Code computes the findings (findings()): each is a fact about this person's money with its numbers, a concept from
  the Money Detective map, and a question in plain words, written from a phrase table in all three languages.
- The AI (one cached call) picks the three questions that matter most this week, preferring concepts the person has not
  explored yet, orders the Home cards, and writes one sentence that sums up where the money stands.
- Every € and % in that sentence is checked against the findings (verify.check). If one doesn't match, or the AI is
  unreachable, Home shows a sentence and picks made by code instead, marked as such.
Tapping a question runs the normal coach with it, so the answer has the same tools, checks and charts.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import date
from pathlib import Path

from . import drains, eu, future, insights, money, psd2, saving, style, verify
from .money import TODAY

log = logging.getLogger("brief")
CACHE = Path(__file__).resolve().parent.parent / "state" / "brief.json"
_lock = threading.Lock()
CARDS = ["play", "safe", "save", "pot", "drains", "sort", "wrap"]
LANG_NAMES = {"en": "English", "fi": "Finnish (suomi)", "sv": "Swedish (svenska)"}

# Questions in the person's own words. Placeholders are names, never amounts, so a question never states a number
# the coach then has to defend; the answer brings the numbers, checked.
Q = {
    "en": {"short_payday": "Why will I run short before payday?", "rent_after": "What if my rent came after payday?",
           "month_up": "Why did {m1} cost more than {m0}?", "month_down": "Why was {m1} cheaper than {m0}?",
           "payday_week": "Why do I spend more right after payday?", "habit": "Is {h} a must or a habit for me?",
           "cut": "How much could I save if I ate out 20 % less?", "surprises": "How much should I keep aside for surprises?",
           "safe_week": "What is safe for me to spend this week?", "compare": "How does my spending on {a} compare with people my age?",
           "type": "What kind of spender am I?", "save": "How much can I safely save this payday?",
           "start_saving": "What would it take for me to start saving?", "drains": "What do my monthly drains cost me in a year?",
           "other_bank": "How much of my money moves to my other bank?"},
    "fi": {"short_payday": "Miksi rahani loppuvat ennen palkkapäivää?", "rent_after": "Entä jos vuokra menisi vasta palkkapäivän jälkeen?",
           "month_up": "Miksi {m1} maksoi enemmän kuin {m0}?", "month_down": "Miksi {m1} oli halvempi kuin {m0}?",
           "payday_week": "Miksi kulutan enemmän heti palkkapäivän jälkeen?", "habit": "{H} – pakko vai tapa minulle?",
           "cut": "Paljonko säästäisin, jos söisin ulkona 20 % vähemmän?", "surprises": "Paljonko minun kannattaisi varata yllätyksiin?",
           "safe_week": "Paljonko voin turvallisesti käyttää tällä viikolla?", "compare": "Miten kulutukseni vertautuu ikäisiini: {a}?",
           "type": "Millainen kuluttaja olen?", "save": "Paljonko voin turvallisesti säästää tänä palkkapäivänä?",
           "start_saving": "Mitä tarvitsisin, jotta voisin alkaa säästää?", "drains": "Paljonko kuukausittaiset vuotoni maksavat vuodessa?",
           "other_bank": "Paljonko rahoistani siirtyy toiseen pankkiini?"},
    "sv": {"short_payday": "Varför tar pengarna slut före lönen?", "rent_after": "Tänk om hyran gick först efter lönen?",
           "month_up": "Varför kostade {m1} mer än {m0}?", "month_down": "Varför var {m1} billigare än {m0}?",
           "payday_week": "Varför spenderar jag mer direkt efter lönen?", "habit": "{H} – ett måste eller en vana för mig?",
           "cut": "Hur mycket kunde jag spara om jag åt ute 20 % mindre?", "surprises": "Hur mycket borde jag lägga undan för överraskningar?",
           "safe_week": "Vad är säkert för mig att spendera den här veckan?", "compare": "Hur står sig mina utgifter mot andra i min ålder: {a}?",
           "type": "Vilken sorts spenderare är jag?", "save": "Hur mycket kan jag spara säkert den här lönen?",
           "start_saving": "Vad skulle krävas för att jag ska börja spara?", "drains": "Vad kostar mina månatliga läckor på ett år?",
           "other_bank": "Hur mycket av mina pengar flyttar till min andra bank?"},
}
HABITS = {"en": {"eating_out": "eating out", "kiosks": "kiosk shopping", "taxis_parking": "taxis and parking"},
          "fi": {"eating_out": "ulkona syöminen", "kiosks": "kioskiostokset", "taxis_parking": "taksit ja pysäköinti"},
          "sv": {"eating_out": "att äta ute", "kiosks": "kioskköp", "taxis_parking": "taxi och parkering"}}
AREAS = {"en": {}, "fi": {"Groceries": "ruoka", "Restaurants & cafes": "ravintolat ja kahvilat", "Transport": "liikenne",
                          "Housing": "asuminen", "Recreation & culture": "vapaa-aika ja kulttuuri", "Clothing": "vaatteet"},
         "sv": {"Groceries": "mat", "Restaurants & cafes": "restauranger och kaféer", "Transport": "transport",
                "Housing": "boende", "Recreation & culture": "fritid och kultur", "Clothing": "kläder"}}
MONTHS = {"en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
          "fi": ["tammikuu", "helmikuu", "maaliskuu", "huhtikuu", "toukokuu", "kesäkuu", "heinäkuu", "elokuu", "syyskuu", "lokakuu", "marraskuu", "joulukuu"],
          "sv": ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]}
FALLBACK = {
    "en": {"short": "At your usual pace you'll be {gap} short on payday, mostly because {bills} in bills fall due before it.",
           "ok": "At your usual pace you'll have {end} left on payday."},
    "fi": {"short": "Tavallisella tahdilla sinulta puuttuu palkkapäivänä {gap}, lähinnä koska ennen sitä erääntyy laskuja {bills}.",
           "ok": "Tavallisella tahdilla sinulle jää palkkapäivänä {end}."},
    "sv": {"short": "I din vanliga takt saknas {gap} på lönedagen, mest för att räkningar på {bills} förfaller före den.",
           "ok": "I din vanliga takt har du {end} kvar på lönedagen."},
}


def _eur(x: float, lang: str) -> str:
    s = f"{round(x):,}"
    return (s if lang == "en" else s.replace(",", " ")) + " €"


def findings(cid: str, lang: str = "en") -> dict:
    """Facts about this person's money right now (all from code) and the questions they lead to."""
    q, out = Q.get(lang, Q["en"]), []
    rib, sts = insights.ribbon(cid), money.get_safe_to_spend(cid)
    end = rib["balance_at_payday_eur"]
    bills = round(sum(b["eur"] for b in rib["bills_ahead"]), 2)
    rent = next((b for b in rib["bills_ahead"] if b["bill"] == "Housing"), None)
    facts = {"balance_now_eur": money.customer(cid)["balance"], "next_payday": rib["next_payday"],
             "balance_at_payday_usual_pace_eur": end, "bills_before_payday_eur": bills,
             "goes_below_zero_on": rib["runs_out_around"]}

    def add(fid, concept, weight, text, **f):
        out.append({"id": fid, "concept": concept, "weight": weight, "question": text, "facts": f})

    if end < 0:
        add("short_payday", "forecast", 10, q["short_payday"], balance_at_payday_eur=end, bills_before_payday_eur=bills)
        if rent:
            add("rent_after", "what_if", 9, q["rent_after"], rent_eur=rent["eur"], rent_due=rent["date"])
    months = money.get_spending(cid, period="last_3_months", group_by="month")["breakdown"]
    if len(months) >= 2:
        m0, m1 = months[-2], months[-1]
        change = (m1["total_eur"] - m0["total_eur"]) / max(m0["total_eur"], 1)
        if abs(change) >= 0.15:
            names = MONTHS.get(lang, MONTHS["en"])
            n0, n1 = names[int(m0["key"][5:]) - 1], names[int(m1["key"][5:]) - 1]
            add("month_up" if change > 0 else "month_down", "where_money_goes", 6 + min(abs(change) * 4, 3),
                q["month_up" if change > 0 else "month_down"].format(m0=n0, m1=n1),
                **{f"spent_{m0['key']}_eur": m0["total_eur"], f"spent_{m1['key']}_eur": m1["total_eur"]})
    pp = insights.payday_pattern(cid)
    if (pp.get("payday_week_change_percent") or 0) >= 50:
        add("payday_week", "forecast", 7, q["payday_week"], extras_change_week_after_payday_percent=pp["payday_week_change_percent"])
    dr = drains.drains(cid)
    habits = sorted(dr.get("habits", []), key=lambda h: -h["eur_month"])
    if habits:
        h = habits[0]
        name = HABITS.get(lang, HABITS["en"]).get(h["habit"], h["habit"])
        add("habit", "baskets", 8, q["habit"].format(h=name, H=name[:1].upper() + name[1:]), habit_eur_month=h["eur_month"], times_month=h["times_month"])
        if h["habit"] == "eating_out":
            add("cut", "what_if", 6, q["cut"], habit_eur_month=h["eur_month"])
        add("drains", "where_money_goes", 5, q["drains"], top_habit_eur_year=h["eur_year"])
    pot = insights.surprise_pot(cid)
    add("surprises", "irregular", 5, q["surprises"], surprises_avg_month_eur=pot["average_per_month_last_12_eur"])
    add("safe_week", "spending_room", 7 if end >= 0 else 4, q["safe_week"], safe_this_week_eur=sts.get("safe_this_week_eur"))
    bench = insights.benchmark(cid)
    areas = [a for a in bench.get("areas", []) if a.get("finland_same_age_per_month_eur")]
    if areas:
        a = max(areas, key=lambda a: a["you_per_month_eur"] / a["finland_same_age_per_month_eur"])
        ratio = a["you_per_month_eur"] / a["finland_same_age_per_month_eur"]
        if ratio >= 1.3 or ratio <= 0.7:
            area = AREAS.get(lang, {}).get(a["area"], a["area"].lower() if lang == "en" else a["area"])
            add("compare", "compare", 6, q["compare"].format(a=area), you_per_month_eur=a["you_per_month_eur"],
                finland_same_age_per_month_eur=a["finland_same_age_per_month_eur"])
    add("type", "compare", 4, q["type"])
    sv = saving.get_safe_to_save(cid)
    if (sv.get("safe_to_save_on_payday_eur") or 0) > 0:
        add("save", "saving", 7, q["save"], safe_to_save_eur=sv["safe_to_save_on_payday_eur"])
    else:
        add("start_saving", "saving", 5, q["start_saving"])
    ps = psd2.status(cid)
    if ps and ps.get("relevant") and not ps.get("connected"):
        add("other_bank", "where_money_goes", 9, q["other_bank"], moved_per_month_eur=ps["flows"]["typical_month_eur"])
        facts["moved_to_other_bank_per_month_eur"] = ps["flows"]["typical_month_eur"]
    if rent:
        facts["rent_eur"] = rent["eur"]
    if habits:
        facts["top_habit"] = habits[0]["habit"]
        facts["top_habit_eur_month"] = habits[0]["eur_month"]
    facts["surprises_avg_month_eur"] = pot["average_per_month_last_12_eur"]
    facts["safe_this_week_eur"] = sts.get("safe_this_week_eur")
    facts["extras_change_week_after_payday_percent"] = pp.get("payday_week_change_percent")
    return {"facts": facts, "findings": out}


def _fallback(f: dict, explored: set[str], lang: str) -> dict:
    t, fa = FALLBACK.get(lang, FALLBACK["en"]), f["facts"]
    end = fa["balance_at_payday_usual_pace_eur"]
    head = (t["short"].format(gap=_eur(-end, lang), bills=_eur(fa["bills_before_payday_eur"], lang)) if end < 0
            else t["ok"].format(end=_eur(end, lang)))
    ranked = sorted(f["findings"], key=lambda x: -(x["weight"] + (3 if x["concept"] not in explored else 0)))
    return {"headline": head, "picks": _spread(ranked, [])}


def _spread(ranked: list[dict], first: list[str]) -> list[str]:
    """Three question ids, the given ones first, then the best of the rest, no two on the same concept if avoidable."""
    out, concepts, byid = [], set(), {x["id"]: x for x in ranked}
    for fid in first:
        if fid in byid and fid not in out and len(out) < 3:
            out.append(fid); concepts.add(byid[fid]["concept"])
    for x in ranked:
        if len(out) < 3 and x["id"] not in out and x["concept"] not in concepts:
            out.append(x["id"]); concepts.add(x["concept"])
    for x in ranked:
        if len(out) < 3 and x["id"] not in out:
            out.append(x["id"])
    return out


SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["headline", "questions", "cards"],
    "properties": {
        "headline": {"type": "string", "description": "One sentence, max 22 words, in the app language."},
        "questions": {"type": "array", "items": {"type": "string"}, "description": "Exactly 3 finding ids, most useful first."},
        "cards": {"type": "array", "items": {"type": "string", "enum": CARDS}, "description": "All Home cards, most useful first."},
    },
}
SYSTEM = (
    "You lead the home screen of a bank's money coach for a young adult in Finland. You get facts computed from their "
    "own transactions and a list of findings, each a question they could ask about their money. Three jobs:\n"
    "1. headline: ONE plain sentence (max 22 words) on where their money stands right now and the main reason, in "
    "{lang}. Use at most two amounts, copied exactly from amounts_as_written (already in whole euros and the right number format; a negative balance_at_payday is written without its minus sign, so phrase it as money missing, in {lang}). Write every word in {lang}. No dates as "
    "numbers, no advice lists, no greeting, no emojis. Name the real cause (e.g. bill timing vs. small extras). The balance is shown in large type right above your "
    "sentence: never restate it; say what it means or where it is heading.\n"
    "2. questions: the ids of the 3 findings most worth asking this week. importance (1-10) is how much code thinks a "
    "finding explains their situation; start from the most important, then favour concepts in not_explored_yet and "
    "mix kinds (not three about the same thing). Pick what is specific to this person, not generic advice.\n"
    "3. cards: order these Home cards, most useful for this person now first: play (practise the next two weeks), "
    "safe (safe to spend this week), save (safe to save on payday), pot (surprise costs), drains (monthly habits and "
    "bills), sort (sort your spending into the three baskets), wrap (money year story)."
)


def brief(cid: str, lang: str = "en", explored: list[str] | None = None) -> dict:
    lang = lang if lang in Q else "en"
    seen = sorted(set(explored or []))
    key = f"{cid}:{lang}:{','.join(seen)}{eu.cache_tag()}"
    with _lock:
        cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    if key in cache and cache[key].get("day") == TODAY.isoformat():
        return cache[key]
    f = findings(cid, lang)
    byid = {x["id"]: x for x in f["findings"]}
    fb = _fallback(f, set(seen), lang)
    written = {k.removesuffix("_eur"): _eur(abs(v), lang) for k, v in f["facts"].items() if k.endswith("_eur") and isinstance(v, (int, float))}
    user = {"facts": f["facts"], "amounts_as_written": written, "not_explored_yet": [c for c in {x["concept"] for x in f["findings"]} if c not in seen],
            "findings": [{"id": x["id"], "concept": x["concept"], "importance": round(x["weight"]), "question": x["question"], "facts": x["facts"]}
                         for x in f["findings"]]}
    source, cards = "ai", None
    try:
        system = SYSTEM.format(lang=LANG_NAMES[lang]) + ("\n" + style.STYLE[lang] if lang in style.STYLE else "")
        r = future._json_call(system, json.dumps(user, default=str), SCHEMA, max_tokens=600)
        head = " ".join(str(r.get("headline", "")).split())
        nums = verify.check(head, [{"tool": "facts", "result": user}], [], lang)
        if not head or len(head) > 220 or any(n["status"] == "unverified" for n in nums):
            log.warning("brief headline rejected (%s): %r", [n["text"] for n in nums if n["status"] == "unverified"], head)
            head, source = fb["headline"], "rules"
        if source == "ai" and lang in style.STYLE:  # native copy edit; it keeps every number exactly as written
            head = style.proofread({"h": head}, lang)["h"]
        ranked = sorted(f["findings"], key=lambda x: -x["weight"])
        picks = _spread(ranked, [p for p in r.get("questions", []) if p in byid])
        cards = [c for c in dict.fromkeys(r.get("cards", [])) if c in CARDS]
        cards += [c for c in CARDS if c not in cards]
    except Exception as e:  # noqa: BLE001  AI unreachable or refused: code picks, clearly marked
        log.warning("brief fallback: %s", e)
        head, picks, source = fb["headline"], fb["picks"], "rules"
    out = {"day": TODAY.isoformat(), "headline": head, "source": source, "model": eu.label() if eu.active() else future.MODEL,
           "questions": [{"id": p, "concept": byid[p]["concept"], "text": byid[p]["question"]} for p in picks],
           "more": [{"id": x["id"], "concept": x["concept"], "text": x["question"]}
                    for x in sorted(f["findings"], key=lambda x: -(x["weight"] + (3 if x["concept"] not in seen else 0))) if x["id"] not in picks],
           "cards": cards or CARDS, "cards_by": "ai" if cards else "rules"}
    with _lock:
        cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
        cache[key] = out
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False))
    return out
