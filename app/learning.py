"""Money Detective: short quests that check understanding, and a private progress record (gamified retention).

Design (Codex for Rasmus, docs/GAMIFIED-LEARNING-RESEARCH.md on review/rasmus-research-coach), built small:
- Three quests, one concept each, 60-90 s: predict from your own data -> see the evidence -> explain why -> feedback.
  Q1 Follow the money (what counts as spending), Q2 Balance isn't spending room, Q3 Plan for the irregular.
- Progress per concept: not explored -> explored -> explained -> revisited. "Explained" records first try vs after
  feedback separately. "Revisited" = a different, equivalent question at least 3 days later (transfer, not recall).
- Retention without pressure: a weekly goal the person picks (1-3 quests), counted per ISO week; a missed week resets
  nothing. Private milestones at 1/2/3 concepts explained. Points exist but are hidden unless the person turns them on.
- Never rewards money outcomes, products, more data sharing or advice-following; never touches the money-fitness
  score. Hide rewards / pause prompts / reset / practice data are always available.
- Idempotent: every answer carries an event_id; a replayed or out-of-order event awards nothing twice.

Code owns the numbers and the right answers; the AI is not involved here. The core is pure: facts in, state in,
state out, so it is unit-tested without the database. `facts_from_data` and the JSON store are the only I/O.
"""
from __future__ import annotations

import json
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

VERSION = 1
POINTS = {"explored": 5, "explained": 10, "revisited": 5}
REVISIT_AFTER_DAYS = 3
MILESTONES = [(1, "first_insight"), (2, "pattern_explorer"), (3, "thoughtful_planner")]

T = {  # every customer-facing string, EN / FI / SV
    "en": {
        "q1": "Follow the money", "q2": "Balance isn't spending room", "q3": "Plan for the irregular",
        "q1_predict": "Guess: what share of your spending in the last 3 months went to everyday extras?",
        "q1_reveal": "It was {share} %: {per_month} € a month on extras, from your own transactions (three baskets).",
        "q1_check": "You move 200 € to your own savings account. Is that spending?",
        "q1_opts": ["Yes, an everyday extra", "No, it's still your money, just moved", "Yes, a must-pay"],
        "q1_ok": "Right. Moving money to your own savings isn't consumption, so the app leaves it out of spending.",
        "q1_no": "Not quite: the money is still yours, only in another place. Spending is money that leaves you for good.",
        "q1_rev": "Which of these is an everyday extra?", "q1_rev_opts": ["Rent", "A dentist visit", "A takeaway dinner"],
        "q2_predict": "Your balance is {balance} €. Guess how much of it is free for extras until payday.",
        "q2_reveal": "About {safe} €. From {balance} €: savings kept apart {savings} €, bills still due {bills} €, "
                     "groceries and commuting {essentials} €, surprise buffer {buffer} €.",
        "q2_check": "Why is the free amount smaller than your balance?",
        "q2_opts": ["The bank holds some of it back", "Bills, essentials and a surprise buffer are still coming, "
                    "and savings are kept apart", "The graph is wrong"],
        "q2_ok": "Exactly. Your balance includes money that already has a job before payday.",
        "q2_no": "Not that one. Nothing is held back: the money is yours, but bills and essentials are still due.",
        "q2_rev": "Payday is in 10 days. Balance 900 €, rent 600 € not yet paid, groceries about 150 €. Roughly how much is free?",
        "q2_rev_opts": ["About 900 €", "About 150 €", "Nothing at all"],
        "q3_predict": "Guess: in how many of your last {n} months did a surprise must-pay (health, repairs) hit?",
        "q3_reveal": "{hit} of {n} months. The biggest was {big} €. Putting aside {pot} € a month would have covered them.",
        "q3_check": "Why put aside {pot} € every month for costs that don't come every month?",
        "q3_opts": ["So a big month doesn't land on one pay cheque", "Because the bank requires it", "Surprises are optional"],
        "q3_ok": "Yes. A small monthly pot turns one painful month into many easy ones.",
        "q3_no": "Not quite. Surprises do come; a monthly pot spreads them so one month doesn't take the hit.",
        "q3_rev": "Your phone screen breaks about once every two years and costs 240 €. What's a fair monthly pot for it?",
        "q3_rev_opts": ["10 €", "120 €", "0 €, it may not happen"],
        "rev_ok": "Right, and on a new example. That's the skill, not just the answer.",
        "rev_no": "Close. Look again at what the money has to cover and when.",
        "first_insight": "First insight", "pattern_explorer": "Pattern explorer", "thoughtful_planner": "Thoughtful planner",
    },
    "fi": {
        "q1": "Seuraa rahaa", "q2": "Saldo ei ole käyttövaraa", "q3": "Varaudu epäsäännölliseen",
        "q1_predict": "Arvaa: kuinka suuri osa kulutuksestasi viimeisen 3 kuukauden aikana meni arjen ylimääräisiin?",
        "q1_reveal": "Se oli {share} %: {per_month} € kuukaudessa, omista tapahtumistasi (kolme koria).",
        "q1_check": "Siirrät 200 € omalle säästötilillesi. Onko se kulutusta?",
        "q1_opts": ["Kyllä, arjen ylimääräinen", "Ei, raha on yhä sinun, vain siirretty", "Kyllä, pakollinen meno"],
        "q1_ok": "Oikein. Siirto omille säästöille ei ole kulutusta, joten sovellus jättää sen pois.",
        "q1_no": "Ei aivan: raha on yhä sinun, vain eri paikassa. Kulutus on rahaa, joka lähtee pysyvästi.",
        "q1_rev": "Mikä näistä on arjen ylimääräinen?", "q1_rev_opts": ["Vuokra", "Hammaslääkäri", "Noutoruoka-illallinen"],
        "q2_predict": "Saldosi on {balance} €. Arvaa, kuinka paljon siitä on vapaata ylimääräisiin palkkapäivään asti.",
        "q2_reveal": "Noin {safe} €. Saldosta {balance} €: säästöt erillään {savings} €, laskuja tulossa {bills} €, "
                     "ruoka ja työmatkat {essentials} €, puskuri yllätyksille {buffer} €.",
        "q2_check": "Miksi vapaa summa on saldoa pienempi?",
        "q2_opts": ["Pankki pidättää osan", "Laskut, välttämättömät ja yllätyspuskuri ovat vielä tulossa, "
                    "ja säästöt pidetään erillään", "Kaavio on väärin"],
        "q2_ok": "Juuri niin. Saldossa on rahaa, jolla on jo tehtävä ennen palkkapäivää.",
        "q2_no": "Ei se. Mitään ei pidätetä: raha on sinun, mutta laskut ja välttämättömät ovat vielä edessä.",
        "q2_rev": "Palkkapäivään 10 päivää. Saldo 900 €, vuokra 600 € maksamatta, ruoka noin 150 €. Paljonko on vapaata?",
        "q2_rev_opts": ["Noin 900 €", "Noin 150 €", "Ei mitään"],
        "q3_predict": "Arvaa: kuinka monena viimeisestä {n} kuukaudesta osui yllättävä pakollinen meno (terveys, korjaukset)?",
        "q3_reveal": "{hit}/{n} kuukautena. Suurin oli {big} €. {pot} € kuukaudessa sivuun olisi kattanut ne.",
        "q3_check": "Miksi laittaa {pot} € sivuun joka kuukausi menoihin, jotka eivät tule joka kuukausi?",
        "q3_opts": ["Ettei iso kuukausi osu yhteen palkkaan", "Koska pankki vaatii", "Yllätykset ovat vapaaehtoisia"],
        "q3_ok": "Kyllä. Pieni kuukausipotti tekee yhdestä raskaasta kuukaudesta monta kevyttä.",
        "q3_no": "Ei aivan. Yllätyksiä tulee; kuukausipotti jakaa ne, ettei yksi kuukausi ota iskua.",
        "q3_rev": "Puhelimesi näyttö hajoaa noin kahden vuoden välein ja maksaa 240 €. Mikä on reilu kuukausipotti?",
        "q3_rev_opts": ["10 €", "120 €", "0 €, ehkei käy"],
        "rev_ok": "Oikein, ja uudessa esimerkissä. Se on taito, ei vain vastaus.",
        "rev_no": "Lähellä. Katso uudelleen, mitä rahan pitää kattaa ja milloin.",
        "first_insight": "Ensimmäinen oivallus", "pattern_explorer": "Kuvioiden tutkija", "thoughtful_planner": "Harkitseva suunnittelija",
    },
    "sv": {
        "q1": "Följ pengarna", "q2": "Saldo är inte utrymme", "q3": "Planera för det oregelbundna",
        "q1_predict": "Gissa: hur stor del av dina utgifter de senaste 3 månaderna gick till vardagens extra?",
        "q1_reveal": "Det var {share} %: {per_month} € i månaden, från dina egna transaktioner (tre korgar).",
        "q1_check": "Du flyttar 200 € till ditt eget sparkonto. Är det en utgift?",
        "q1_opts": ["Ja, vardagens extra", "Nej, pengarna är fortfarande dina, bara flyttade", "Ja, en nödvändig utgift"],
        "q1_ok": "Rätt. En flytt till eget sparande är ingen konsumtion, så appen räknar inte med den.",
        "q1_no": "Inte riktigt: pengarna är fortfarande dina, bara på ett annat ställe.",
        "q1_rev": "Vilken av dessa är vardagens extra?", "q1_rev_opts": ["Hyra", "Tandläkarbesök", "Hämtmat till middag"],
        "q2_predict": "Ditt saldo är {balance} €. Gissa hur mycket som är fritt för extra fram till lönedagen.",
        "q2_reveal": "Cirka {safe} €. Av {balance} €: sparande hålls separat {savings} €, räkningar kvar {bills} €, "
                     "mat och resor {essentials} €, buffert för överraskningar {buffer} €.",
        "q2_check": "Varför är det fria beloppet mindre än saldot?",
        "q2_opts": ["Banken håller inne en del", "Räkningar, nödvändigheter och en buffert återstår, och "
                    "sparandet hålls separat", "Grafen är fel"],
        "q2_ok": "Precis. Saldot innehåller pengar som redan har en uppgift före lönedagen.",
        "q2_no": "Inte det. Inget hålls inne: pengarna är dina, men räkningar återstår.",
        "q2_rev": "Lön om 10 dagar. Saldo 900 €, hyra 600 € obetald, mat cirka 150 €. Ungefär hur mycket är fritt?",
        "q2_rev_opts": ["Cirka 900 €", "Cirka 150 €", "Ingenting"],
        "q3_predict": "Gissa: hur många av dina senaste {n} månader kom en oväntad nödvändig utgift (hälsa, reparationer)?",
        "q3_reveal": "{hit} av {n} månader. Den största var {big} €. {pot} € i månaden undan hade täckt dem.",
        "q3_check": "Varför lägga undan {pot} € varje månad för kostnader som inte kommer varje månad?",
        "q3_opts": ["Så att en stor månad inte landar på en lön", "Banken kräver det", "Överraskningar är frivilliga"],
        "q3_ok": "Ja. En liten månadspott gör en tung månad till många lätta.",
        "q3_no": "Inte riktigt. Överraskningar kommer; en månadspott sprider ut dem.",
        "q3_rev": "Telefonskärmen går sönder ungefär vartannat år och kostar 240 €. Vad är en rimlig månadspott?",
        "q3_rev_opts": ["10 €", "120 €", "0 €, det kanske inte händer"],
        "rev_ok": "Rätt, och på ett nytt exempel. Det är färdigheten, inte bara svaret.",
        "rev_no": "Nära. Titta igen på vad pengarna ska täcka och när.",
        "first_insight": "Första insikten", "pattern_explorer": "Mönsterutforskare", "thoughtful_planner": "Eftertänksam planerare",
    },
}
CORRECT = {"q1": 1, "q2": 1, "q3": 0}
REVISIT_CORRECT = {"q1": 2, "q2": 1, "q3": 0}
QUESTS = ["q1", "q2", "q3"]
PRACTICE_FACTS = {"everyday_share": 0.38, "everyday_per_month": 310.0, "balance": 1450.0, "safe": 240.0, "savings": 500.0,
                  "bills": 420.0, "essentials": 210.0, "buffer": 80.0, "months": 12, "surprise_months": 5,
                  "biggest_surprise": 610.0, "pot": 95.0}


def _t(lang: str) -> dict:
    return T.get(lang, T["en"])


def _fmt(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ")


def _bands(true: float, edges: list[float], labels: list[str]) -> tuple[list[str], int]:
    """Prediction choices as bands; returns labels and the index of the band containing the true value."""
    idx = next((i for i, e in enumerate(edges) if true < e), len(edges))
    return labels, idx


# ---------- quests (pure) ----------

def quest(qid: str, facts: dict, lang: str = "en", revisit: bool = False) -> dict:
    """The steps of one quest for this person's facts. Right answers and evidence are computed here, not by an AI."""
    t = _t(lang)
    if qid not in QUESTS:
        raise ValueError(f"unknown quest {qid}")
    f = facts
    if revisit:
        return {"quest": qid, "title": t[qid], "version": VERSION, "revisit": True,
                "check": {"question": t[f"{qid}_rev"], "options": t[f"{qid}_rev_opts"]}}
    if qid == "q1":
        share = f["everyday_share"] * 100
        opts, right = _bands(share, [20, 40, 60], ["< 20 %", "20-40 %", "40-60 %", "> 60 %"])
        predict = {"question": t["q1_predict"], "options": opts, "closest": right}
        reveal = t["q1_reveal"].format(share=round(share), per_month=_fmt(f["everyday_per_month"]))
        evidence = {"tool": "get_three_baskets", "period": "last_3_months"}
        check = {"question": t["q1_check"], "options": t["q1_opts"]}
    elif qid == "q2":
        b, s = f["balance"], max(f["safe"], 0.0)
        cands = sorted({round(b, -1), round(b / 2, -1), round(s, -1), 0.0}, reverse=True)
        opts = [f"{_fmt(c)} €" for c in cands]
        right = min(range(len(cands)), key=lambda i: abs(cands[i] - s))
        predict = {"question": t["q2_predict"].format(balance=_fmt(b)), "options": opts, "closest": right}
        reveal = t["q2_reveal"].format(safe=_fmt(s), balance=_fmt(b), savings=_fmt(f["savings"]), bills=_fmt(f["bills"]),
                                       essentials=_fmt(f["essentials"]), buffer=_fmt(f["buffer"]))
        evidence = {"tool": "get_safe_to_spend", "steps": True}
        check = {"question": t["q2_check"], "options": t["q2_opts"]}
    else:
        n, hit = f["months"], f["surprise_months"]
        edges = [n * 0.25, n * 0.5, n * 0.75]
        labels = [f"0-{int(edges[0])}", f"{int(edges[0]) + 1}-{int(edges[1])}", f"{int(edges[1]) + 1}-{int(edges[2])}",
                  f"{int(edges[2]) + 1}-{n}"]
        opts, right = _bands(hit, [e + 0.5 for e in edges], labels)
        predict = {"question": t["q3_predict"].format(n=n), "options": opts, "closest": right}
        reveal = t["q3_reveal"].format(hit=hit, n=n, big=_fmt(f["biggest_surprise"]), pot=_fmt(f["pot"]))
        evidence = {"tool": "surprise_pot"}
        check = {"question": t["q3_check"].format(pot=_fmt(f["pot"])), "options": t["q3_opts"]}
    return {"quest": qid, "title": t[qid], "version": VERSION, "revisit": False, "predict": predict,
            "reveal": reveal, "evidence": evidence, "check": check,
            "note": "A guess is never wrong here: it's compared with your data, not scored."}


# ---------- progress (pure) ----------

def new_state() -> dict:
    return {"concepts": {q: {"status": "not_explored", "first_try": None, "explained_at": None, "revisited_at": None,
                             "attempts": 0} for q in QUESTS},
            "events": [], "awards": [], "weekly_goal": 2, "settings": {"show_points": False, "hide_rewards": False,
                                                                       "pause_prompts": False}}


def _week(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _award(state: dict, qid: str, kind: str, now: datetime) -> bool:
    key = f"{qid}:v{VERSION}:{kind}"
    if any(a["key"] == key for a in state["awards"]):
        return False
    state["awards"].append({"key": key, "quest": qid, "kind": kind, "points": POINTS[kind], "at": now.isoformat(),
                            "week": _week(now.date())})
    return True


def record(state: dict, *, event_id: str, qid: str, step: str, choice: int, now: datetime) -> dict:
    """Apply one learning event. step: 'predict' (any guess), 'check' (concept question), 'revisit'.
    Returns feedback; the state is updated in place. Replayed event_ids change nothing."""
    if qid not in QUESTS or step not in ("predict", "check", "revisit"):
        return {"ok": False, "error": "unknown quest or step"}
    if any(e["id"] == event_id for e in state["events"]):
        return {"ok": True, "duplicate": True, "concept": state["concepts"][qid]}
    c = state["concepts"][qid]
    state["events"].append({"id": event_id, "quest": qid, "step": step, "choice": int(choice), "at": now.isoformat()})
    out = {"ok": True, "duplicate": False}
    if step == "predict":
        if c["status"] == "not_explored":
            c["status"] = "explored"
        out["awarded"] = _award(state, qid, "explored", now)
    elif step == "check":
        if c["status"] == "not_explored":
            return {"ok": False, "error": "make a guess and see your evidence first"}
        c["attempts"] += 1
        right = int(choice) == CORRECT[qid]
        out["correct"] = right
        if right and c["status"] == "explored":
            c["status"], c["explained_at"] = "explained", now.isoformat()
            c["first_try"] = c["attempts"] == 1
            out["awarded"] = _award(state, qid, "explained", now)
    else:  # revisit
        if c["status"] not in ("explained", "revisited"):
            return {"ok": False, "error": "explain the concept first"}
        due = datetime.fromisoformat(c["explained_at"]) + timedelta(days=REVISIT_AFTER_DAYS)
        if now < due:
            return {"ok": False, "error": "revisit opens later", "opens": due.date().isoformat()}
        right = int(choice) == REVISIT_CORRECT[qid]
        out["correct"] = right
        if right and c["status"] == "explained":
            c["status"], c["revisited_at"] = "revisited", now.isoformat()
            out["awarded"] = _award(state, qid, "revisited", now)
    out["concept"] = c
    return out


def summary(state: dict, now: datetime, lang: str = "en") -> dict:
    """Private progress. Separate from money: no balance, score or product appears here."""
    t = _t(lang)
    week = _week(now.date())
    done_week = len({a["quest"] for a in state["awards"] if a["week"] == week})
    explained = sum(1 for c in state["concepts"].values() if c["status"] in ("explained", "revisited"))
    revisits_due = [q for q, c in state["concepts"].items() if c["status"] == "explained"
                    and now >= datetime.fromisoformat(c["explained_at"]) + timedelta(days=REVISIT_AFTER_DAYS)]
    hide = state["settings"]["hide_rewards"]
    out = {"concepts": [{"quest": q, "title": t[q], **state["concepts"][q]} for q in QUESTS],
           "weekly_goal": state["weekly_goal"], "quests_this_week": done_week,
           "weekly_note": "Missed weeks don't reset anything.",
           "revisits_due": [] if state["settings"]["pause_prompts"] else revisits_due,
           "settings": state["settings"]}
    if not hide:
        out["milestones"] = [{"key": k, "title": t[k], "reached": explained >= n} for n, k in MILESTONES]
        if state["settings"]["show_points"]:
            out["points"] = sum(a["points"] for a in state["awards"])
    return out


def set_settings(state: dict, **kw) -> dict:
    for k in ("show_points", "hide_rewards", "pause_prompts"):
        if k in kw and kw[k] is not None:
            state["settings"][k] = bool(kw[k])
    if kw.get("weekly_goal") is not None:
        state["weekly_goal"] = max(1, min(3, int(kw["weekly_goal"])))
    return state


# ---------- I/O (app only) ----------

STORE = Path(__file__).resolve().parents[1] / "state" / "learning.json"
_lock = threading.Lock()


def _key(device: str, cid: str) -> str:
    """Progress is per device and persona (the demo has one shared login), never global."""
    return f"{(device or 'anon')[:64]}:{cid}"


def load(device: str, cid: str) -> dict:
    with _lock:
        data = json.loads(STORE.read_text()) if STORE.exists() else {}
    return data.get(_key(device, cid)) or new_state()


def save(device: str, cid: str, state: dict) -> None:
    with _lock:
        data = json.loads(STORE.read_text()) if STORE.exists() else {}
        data[_key(device, cid)] = state
        STORE.parent.mkdir(exist_ok=True)
        tmp = STORE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data))
        tmp.replace(STORE)


def reset(device: str, cid: str) -> None:
    with _lock:
        data = json.loads(STORE.read_text()) if STORE.exists() else {}
        data.pop(_key(device, cid), None)
        STORE.parent.mkdir(exist_ok=True)
        STORE.write_text(json.dumps(data))


def facts_from_data(cid: str) -> dict:
    """The numbers the quests use, from the same tools as the rest of the app."""
    from . import insights, money

    b = money.get_three_baskets(cid, "last_3_months")
    b3 = next((x for x in b["baskets"] if x["basket"] == 3), {"share_of_spending": 0, "per_month_eur": 0})
    s = money.get_safe_to_spend(cid)
    steps = {i: abs(x["eur"]) for i, x in enumerate(s["steps"])}
    p = insights.surprise_pot(cid)
    last = p["months"][-12:]
    return {"everyday_share": float(b3["share_of_spending"] or 0), "everyday_per_month": float(b3["per_month_eur"] or 0),
            "balance": steps.get(0, 0.0), "savings": steps.get(1, 0.0), "bills": steps.get(2, 0.0),
            "essentials": steps.get(3, 0.0), "buffer": steps.get(4, 0.0), "safe": float(s["safe_until_payday_eur"]),
            "months": len(last), "surprise_months": sum(1 for m in last if (m["eur"] or 0) > 0),
            "biggest_surprise": max([m["eur"] or 0 for m in last] or [0]),
            "pot": float(p["suggested_monthly_pot_eur"] or 0)}
