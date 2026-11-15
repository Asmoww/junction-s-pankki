"""Language quality for AI-written text in Finnish and Swedish.

- STYLE: a short style guide and glossary added to every AI prompt in that language, so the app's own terms are used
  (ostoton päivä, menopäivä, miinuksella, arjen extrat…) and anglicisms are avoided.
- proofread(): a second, short pass by a native-speaker copy editor persona that fixes grammar, case endings and
  unnatural phrasing. The result is kept only if every number is unchanged and the length stays close.
English needs neither.
"""
from __future__ import annotations

import json
import logging
import re

log = logging.getLogger("style")

GLOSSARY = {
    "fi": ("Käytä sovelluksen termejä: arjen extrat (everyday extras), kiinteät pakolliset menot, yllättävät pakolliset "
           "menot, ostoton päivä (no-spend day), menopäivä (spending day), palkkapäivä, palkkaviikko, saldo / tililläsi on (balance; ei 'kassa'), miinuksella / "
           "miinukselle (below zero), puskuri, kaltaisesi tai ikätoverisi (people like you), ulkona syöminen. Vältä "
           "anglismeja ja slangia (skippaus, shoppailu, kaksoset ihmisistä) ja suoria käännöksiä englannista."),
    "sv": ("Använd appens termer: vardagsextra (everyday extras), fasta måsten, oväntade måsten, köpfri dag (no-spend "
           "day), lönedag, löneveckan, på minus (below zero), buffert, personer som du (people like you), äta ute. "
           "Undvik anglicismer och ordagranna översättningar från engelska."),
}
STYLE = {
    "fi": ("Write natural, idiomatic Finnish as a native Finnish copywriter at a Finnish bank would: correct case "
           "endings, everyday words, short sentences, no word-for-word translations from English. " + GLOSSARY["fi"]),
    "sv": ("Write natural, idiomatic Finland-Swedish/Swedish as a native copywriter at a Nordic bank would: correct "
           "grammar, everyday words, short sentences, no word-for-word translations from English. " + GLOSSARY["sv"]),
}


def guide(lang: str) -> str:
    """Text to append to a system prompt ('' for English)."""
    return (" " + STYLE[lang]) if lang in STYLE else ""


_num = re.compile(r"\d+(?:[ ., ]\d+)*")


def _numbers(s: str) -> list[str]:
    return [re.sub(r"[ ., ]", "", n) for n in _num.findall(s or "")]


def proofread(texts: dict[str, str], lang: str, max_growth: float = 1.25) -> dict[str, str]:
    """Native-speaker copy edit of short texts (keys kept). A line falls back to the original if its numbers changed,
    it grew too long, or the call failed."""
    texts = {k: v for k, v in texts.items() if isinstance(v, str) and v.strip()}
    if lang not in STYLE or not texts:
        return texts
    from .future import _json_call  # late import: future imports this module
    lname = {"fi": "Finnish", "sv": "Swedish"}[lang]
    schema = {"type": "object", "additionalProperties": False, "required": list(texts),
              "properties": {k: {"type": "string"} for k in texts}}
    system = (f"You are a native {lname} copy editor at a Nordic bank. Fix grammar, case endings, word choice and any "
              f"unnatural or translated-sounding phrasing in each line so it reads like natural {lname} written by a "
              "native copywriter. Keep the meaning, the friendly tone, roughly the same length, and every number exactly "
              f"as written. If a line is already natural, return it unchanged. {GLOSSARY[lang]}")
    try:
        out = _json_call(system, json.dumps(texts, ensure_ascii=False), schema, max_tokens=1500)
    except Exception as e:  # noqa: BLE001
        log.warning("proofread failed: %s", e)
        return texts
    fixed = {}
    for k, v in texts.items():
        w = out.get(k)
        ok = isinstance(w, str) and w.strip() and _numbers(w) == _numbers(v) and len(w) <= max(len(v) * max_growth, len(v) + 12)
        fixed[k] = w.strip() if ok else v
    return fixed
