"""S-Pankki pitch deck (Junction 2026): editable .pptx built with python-pptx. Real app screenshots from the live
build (Emma, 14 Nov). Headlines are DRAFTS for Rasmus to approve or replace (his rule: no AI-written slide text
without his OK); each slide's notes say so."""
import copy
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from lxml import etree

G900, G700, G500, G300, G100, G50 = "003D25", "00703C", "2E9C5E", "8FD0A8", "D7EFE0", "EEF8F2"
INK, MUTED, NEG, NEGL, WHITE, LINE = "0F2219", "66786E", "C2402F", "FBE9E6", "FFFFFF", "E3F1E8"
BLUE, AMBER, GREY = "1F4F86", "7A4D0B", "47554D"
FONT = "Arial"
S = __import__("os").path.join(__import__("os").path.dirname(__file__), "shots") + "/"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def rgb(h):
    return RGBColor.from_string(h)


def bg(slide, color):
    f = slide.background.fill
    f.solid(); f.fore_color.rgb = rgb(color)


def text(slide, x, y, w, h, runs, size=18, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         name=None, spacing=1.1):
    """runs: str, or list of paragraphs; a paragraph is a str or a list of (text, {size,color,bold}) runs."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    paras = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        parts = para if isinstance(para, list) else [(para, {})]
        for t, o in parts:
            r = p.add_run()
            r.text = t
            r.font.name = FONT
            r.font.size = Pt(o.get("size", size))
            r.font.bold = o.get("bold", bold)
            r.font.color.rgb = rgb(o.get("color", color))
        if isinstance(para, list) and para and para[0][1].get("after"):
            p.space_after = Pt(para[0][1]["after"])
    return tb


def box(slide, x, y, w, h, fill=WHITE, line=None, radius=0.12, name=None):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.adjustments[0] = radius
    s.fill.solid(); s.fill.fore_color.rgb = rgb(fill)
    if line:
        s.line.color.rgb = rgb(line); s.line.width = Pt(1)
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    if name:
        s.name = name
    return s


def phone(slide, img, x, y, h, name=None):
    """A real app screenshot (390x844 at 2x), rounded like the app's cards, with a hairline frame."""
    w = h * 390 / 844
    pic = slide.shapes.add_picture(S + img, Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        pic.name = name
    geom = pic._element.spPr.find(qn("a:prstGeom"))
    geom.set("prst", "roundRect")
    av = geom.find(qn("a:avLst"))
    if av is None:
        av = etree.SubElement(geom, qn("a:avLst"))
    gd = etree.SubElement(av, qn("a:gd")); gd.set("name", "adj"); gd.set("fmla", "val 6000")
    pic.line.color.rgb = rgb(G100); pic.line.width = Pt(1.25)
    return pic


def dot(slide, x, y, d, color):
    s = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    s.fill.solid(); s.fill.fore_color.rgb = rgb(color); s.line.fill.background(); s.shadow.inherit = False
    return s


def mark(slide, dark=False):
    """The app's brand mark, top left (rounded square with S)."""
    s = box(slide, 0.6, 0.45, 0.42, 0.42, fill=WHITE if dark else G700, radius=0.3, name="Brand mark")
    tf = s.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = "S"; r.font.name = FONT; r.font.bold = True; r.font.size = Pt(16)
    r.font.color.rgb = rgb(G700 if dark else WHITE)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE


def title(slide, t, dark=False, size=34):
    text(slide, 0.6, 1.1, 12.1, 1.0, t, size=size, bold=True, color=WHITE if dark else G900, name="Title")


def notes(slide, t):
    slide.notes_slide.notes_text_frame.text = t


DRAFT = "DRAFT HEADLINE: Rasmus to approve or replace (his rule: no AI-written slide text without his OK).\n"

# 1 ---------------------------------------------------------------- Hook (dark)
s = prs.slides.add_slide(BLANK); bg(s, G900); mark(s, dark=True)
text(s, 0.6, 1.6, 7.4, 2.6, [[("Emma has ", {}), ("699.85\u00a0€", {"color": G300})],
                              [("On payday she'll be", {})], [("997\u00a0€ short", {"color": "F2A79C"})]],
     size=42, bold=True, color=WHITE, name="Hook", spacing=1.05)
text(s, 0.6, 4.55, 6.8, 1.3, "She thinks it's the coffee. Her own money can tell her what's really going on, "
     "and what would change it.", size=20, color=G100, name="Hook line")
text(s, 0.6, 6.55, 7, 0.4, "S-Pankki challenge  |  Junction 2026", size=13, color=G300, name="Event")
phone(s, "home.png", 8.55, 0.55, 6.4, name="Emma's Home screen")
notes(s, DRAFT + "★ Stage slide. 0:00-0:15. Open on Emma's moment; no names, no team intro.\n"
      "Numbers: balance 699.85 €, forecast -997.24 € on payday 15 Oct (live build, Emma = synthetic customer CUST01610 "
      "from the challenge data). Screenshot: the real Home screen, 14 Nov.")

# 2 ---------------------------------------------------------------- Problem (mint)
s = prs.slides.add_slide(BLANK); bg(s, G50); mark(s)
title(s, "Bank apps show what happened. Not what's coming, or what to do")
for i, (big, lab) in enumerate([("1 in 2", "overdraft moments in the data happen in the last 7 days before payday"),
                                 ("15 %", "of everyday extras are small purchases under 10 €: it's rarely the coffee")]):
    x = 0.6 + i * 4.15
    box(s, x, 2.55, 3.85, 3.3, name=f"Stat card {i+1}")
    text(s, x + 0.35, 2.9, 3.2, 1.2, big, size=60, bold=True, color=G700 if i else NEG, name=f"Stat {i+1}")
    text(s, x + 0.35, 4.2, 3.2, 1.5, lab, size=17, color=INK, name=f"Stat {i+1} label")
box(s, 9.0, 2.55, 3.75, 3.3, fill=G900, name="Question card")
text(s, 9.35, 2.9, 3.1, 2.7, [[("The question people actually have:", {"size": 15, "color": G300})],
                              [("“Will my money last to payday, and what should I change?”", {"size": 22, "bold": True, "color": WHITE})]],
     name="The question")
text(s, 0.6, 6.35, 12, 0.6, "Source: our analysis of the S-Pankki challenge dataset (synthetic transactions modelled on real "
     "S-Bank data). Recheck on the final build before use.", size=12, color=MUTED, name="Source")
notes(s, DRAFT + "★ Stage slide. 0:15-0:35. One sourced fact, then the question.\n"
      "Both figures come from docs/DEMO.md ('The one story'): half of all overdraft moments are in the last 7 days "
      "before payday; purchases under 10 € are 15 % of extras. They are from the challenge dataset, not national "
      "statistics; say so. A national Finnish literacy figure would need a real citation (Rasmus's plan, open item).")

# 3 ---------------------------------------------------------------- What we built
s = prs.slides.add_slide(BLANK); bg(s, WHITE); mark(s)
title(s, "Her money talks first: no chat box needed")
phone(s, "home.png", 0.75, 2.05, 5.1, name="Home: sentence and line")
phone(s, "home2.png", 3.35, 2.05, 5.1, name="Home: questions picked for her")
rows = [("One sentence from her numbers", "Written by the AI, every amount checked against the data; code writes it if one doesn't match."),
        ("The line to payday", "Real balance since payday, the forecast to the next one, bills shown where they hit."),
        ("Questions picked for her", "From her own data and what she hasn't explored yet. One tap opens the answer in the coach.")]
for i, (h, b) in enumerate(rows):
    y = 2.2 + i * 1.55
    dot(s, 6.35, y + 0.05, 0.42, G100)
    text(s, 6.35, y + 0.05, 0.42, 0.42, str(i + 1), size=16, bold=True, color=G700, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE, name=f"Step {i+1}")
    text(s, 7.05, y, 5.7, 0.45, h, size=21, bold=True, color=G900, name=f"Feature {i+1}")
    text(s, 7.05, y + 0.5, 5.7, 0.9, b, size=15, color=INK, name=f"Feature {i+1} text")
notes(s, DRAFT + "★ Stage slide. 0:35-0:50. The one-liner, then switch to the live demo.\n"
      "Matches the brief: 'chat with your own money' and 'explore freely rather than fixed charts'. "
      "The sentence: app/brief.py (verify.check on its numbers; fallback written by code).")

# 4 ---------------------------------------------------------------- Every number is a receipt
s = prs.slides.add_slide(BLANK); bg(s, G50); mark(s)
title(s, "Every number is a receipt")
phone(s, "answer2.png", 0.75, 2.05, 5.1, name="Coach answer with coloured numbers")
phone(s, "sheet.png", 3.35, 2.05, 5.1, name="Tapped number: from your S-Bank account")
phone(s, "payments.png", 5.95, 2.05, 5.1, name="The payments behind the number")
legend = [(G500, "Green", "from her data; tap to see the payments"), (GREY, "Grey", "her own number"),
          (BLUE, "Blue", "an assumption or a calculation"), (AMBER, "Amber", "couldn't check, shown as such")]
for i, (c, h, b) in enumerate(legend):
    y = 2.2 + i * 0.95
    dot(s, 8.85, y + 0.08, 0.28, c)
    text(s, 9.3, y, 3.6, 0.85, [[(h + "  ", {"bold": True, "color": G900}), (b, {})]], size=16, name=f"Legend {h}")
text(s, 8.85, 6.1, 4.0, 1.0, "The AI explains; code computes every amount from her transactions.", size=15,
     bold=True, color=G700, name="Principle")
notes(s, DRAFT + "★ Stage slide (or shown live in the demo). The strongest thing we have: no other team can show the "
      "payments behind each number.\n"
      "Screens: 'How much did I spend on eating out in the last 3 months?' 508.37 € → From your S-Bank account, "
      "1 Jul-30 Sep, 10 payments, 508.37 € ÷ 3 months = 169.46 € a month → the 10 payments.\n"
      "Say 'matched to the calculations on her data', never 'guaranteed correct'. app/verify.py, /api/payments.")

# 5 ---------------------------------------------------------------- Test a change, honestly
s = prs.slides.add_slide(BLANK); bg(s, WHITE); mark(s)
title(s, "Test a change. See honestly what it fixes")
phone(s, "pause.png", 0.75, 2.05, 5.1, name="What if I paused all my extras")
phone(s, "play_intro.png", 3.35, 2.05, 5.1, name="Play your next two weeks")
box(s, 6.3, 2.15, 6.4, 2.15, fill=G50, name="Pause result card")
text(s, 6.65, 2.35, 6.0, 0.5, "Pause every extra until payday", size=16, color=MUTED, name="Pause label")
text(s, 6.65, 2.85, 6.0, 1.0, [[("−997 €", {"color": NEG}), ("  →  ", {"color": MUTED}), ("−676 €", {"color": NEG})]],
     size=44, bold=True, name="Pause numbers")
text(s, 6.65, 3.75, 6.0, 0.45, "Better. Still short.", size=18, bold=True, color=G900, name="Pause verdict")
box(s, 6.3, 4.55, 6.4, 2.6, fill=WHITE, line=G100, name="Gap card")
text(s, 6.65, 4.8, 5.8, 2.2, [[("Her months run about ", {}), ("206 €", {"bold": True, "color": NEG}),
                               (" short on average.", {})],
                              [("Play your next two weeks uses the three baskets as rules: rent can't be skipped (moving it "
                                "needs the landlord's OK and it's still owed), surprises come anyway, extras are her choice. "
                                "The app says plainly when a trick only buys time.", {"size": 15})]],
     size=18, color=INK, name="Gap text", spacing=1.15)
notes(s, DRAFT + "★ Part of the live demo. Numbers (live, 14 Nov): usual pace -997.24 €, all extras paused -675.72 € "
      "(forecast_with_events, pause_extras); monthly gap 205.66 € (play._monthly_gap, 12-month average).\n"
      "Never present moving rent as a fix; the +87 € plan only works if the landlord agrees and the rent is still owed. "
      "(Codex review f858b77.)")

# 6 ---------------------------------------------------------------- Learning by doing
s = prs.slides.add_slide(BLANK); bg(s, G50); mark(s)
title(s, "Learning by doing, with her own money")
phone(s, "learn.png", 0.75, 2.05, 5.1, name="Learn: Money Detective")
cards = [("The three baskets as rules", "Fixed must-pays, surprise must-pays and everyday extras decide what she can "
          "skip in Play, and Sort with the AI asks about the purchases only she can classify."),
         ("Guess first, then her data", "A quest asks her to guess before revealing: she guessed under 20 % of her "
          "spending goes on extras. Her data says 32 %."),
         ("Curiosity, not grades", "Every new corner of her money she explores lights up the map. That's engagement; "
          "we haven't measured learning outcomes, and we say so.")]
for i, (h, b) in enumerate(cards):
    y = 2.05 + i * 1.72
    box(s, 3.75, y, 9.0, 1.55, name=f"Learning card {i+1}")
    text(s, 4.1, y + 0.2, 8.4, 0.45, h, size=19, bold=True, color=G900, name=f"Learning {i+1}")
    text(s, 4.1, y + 0.68, 8.4, 0.8, b, size=15, color=INK, name=f"Learning {i+1} text")
notes(s, DRAFT + "Deck only (not in the 3-minute stage version). Pedagogical angle of the brief: the three baskets.\n"
      "32 % / 'under 20 %' are from the recorded quest take (Claude video revision, 14 Nov); recheck on the final build. "
      "Curiosity progress is not demonstrated learning (Codex review).")

# 7 ---------------------------------------------------------------- How it works / trust
s = prs.slides.add_slide(BLANK); bg(s, WHITE); mark(s)
title(s, "How it works: the AI explains, code computes")
steps = [("Her question", "in her own words, EN / FI / SV", G50, G900),
         ("AI picks the tools", "Gemma 4, hosted in Finland", G100, G900),
         ("Code calculates", "Python + DuckDB on her transactions", G700, WHITE),
         ("Every number checked", "matched to the tool results", G100, G900),
         ("Answer with receipts", "colours, steps, payments", G50, G900)]
for i, (h, b, f, c) in enumerate(steps):
    x = 0.6 + i * 2.5
    box(s, x, 2.4, 2.2, 1.85, fill=f, line=G100 if f == WHITE else None, name=f"Flow {i+1}")
    text(s, x + 0.2, 2.6, 1.8, 0.8, h, size=17, bold=True, color=c, name=f"Flow {i+1} title")
    text(s, x + 0.2, 3.35, 1.8, 0.8, b, size=13, color=c, name=f"Flow {i+1} text")
    if i < 4:
        a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x + 2.24), Inches(3.18), Inches(0.22), Inches(0.3))
        a.fill.solid(); a.fill.fore_color.rgb = rgb(G300); a.line.fill.background(); a.name = f"Arrow {i+1}"
stats = [("23 / 25", "trick questions passed on the live coach (latest run, Gemma)"), ("51 / 51", "numbers in those answers matched to her data"),
         ("Totals only", "leave the database: never her name, customer id or account number")]
for i, (big, lab) in enumerate(stats):
    x = 0.6 + i * 4.15
    text(s, x, 4.85, 3.9, 0.8, big, size=34, bold=True, color=G700, name=f"Proof {i+1}")
    text(s, x, 5.65, 3.6, 1.0, lab, size=15, color=INK, name=f"Proof {i+1} text")
notes(s, DRAFT + "★ Stage slide. 2:00-2:25. Tech stack as one graph (Rasmus's Walkthrough note).\n"
      "Trap suite: scripts/run_traps.py --eu, 25 questions where money coaches typically fail; RERUN on the final build "
      "and update '23 / 25' and '51 / 51' (a run on the current build is in progress). Number check: app/verify.py. "
      "Model: Gemma 4 31B via vLLM on a Verda GPU in Finland (docs/VERDA.md). The Claude path exists but is switched off.")

# 8 ---------------------------------------------------------------- Compared with what exists
s = prs.slides.add_slide(BLANK); bg(s, G50); mark(s)
title(s, "Compared with what people use today")
cols = ["", "Bank app history", "Budgeting apps", "General AI chat", "Our coach"]
rows = [("Uses her own transactions", ["yes", "manual setup", "no", "yes"]),
        ("Looks ahead to payday", ["no", "partly", "no", "yes"]),
        ("Tests a change on her numbers", ["no", "partly", "guesses", "yes"]),
        ("Shows proof for every number", ["no", "no", "no", "yes"])]
tbl = s.shapes.add_table(len(rows) + 1, len(cols), Inches(0.6), Inches(2.2), Inches(12.1), Inches(3.8)).table
widths = [3.5, 2.15, 2.15, 2.15, 2.15]
for j, w in enumerate(widths):
    tbl.columns[j].width = Inches(w)
def cell(r, c, t, bold=False, color=INK, fill=WHITE, size=16):
    ce = tbl.cell(r, c); ce.fill.solid(); ce.fill.fore_color.rgb = rgb(fill)
    ce.margin_left = ce.margin_right = Inches(0.15)
    tf = ce.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.LEFT if c == 0 else PP_ALIGN.CENTER
    r_ = p.add_run(); r_.text = t; r_.font.name = FONT; r_.font.size = Pt(size); r_.font.bold = bold; r_.font.color.rgb = rgb(color)
    ce.vertical_anchor = MSO_ANCHOR.MIDDLE
for j, c in enumerate(cols):
    cell(0, j, c, bold=True, color=WHITE if j == 4 else G900, fill=G700 if j == 4 else G100, size=15)
for i, (lab, vals) in enumerate(rows, start=1):
    cell(i, 0, lab, bold=True, color=G900)
    for j, v in enumerate(vals, start=1):
        cell(i, j, v, bold=(j == 4), color=G700 if v == "yes" else MUTED, fill=G50 if j == 4 else WHITE)
text(s, 0.6, 6.35, 12, 0.5, "Observations of typical tools, not claims about any named product.", size=12, color=MUTED, name="Note")
notes(s, DRAFT + "Deck only. Compare to what people already use (Rasmus's LoreDash note), stated as observations, "
      "no named competitors.")

# 9 ---------------------------------------------------------------- Fits S-mobiili
s = prs.slides.add_slide(BLANK); bg(s, WHITE); mark(s)
title(s, "Built to sit inside S-mobiili")
cards = [("A mobile web view", "Runs in the phone's browser today; drops into S-mobiili as a web view. English, Finnish and Swedish."),
         ("The AI stays in Finland", "Gemma 4 on a GPU we host in Finland. Only computed totals reach the model."),
         ("The full picture, with consent", "A PSD2 consent flow brings in other banks' accounts (demo data for the other bank in this prototype).")]
for i, (h, b) in enumerate(cards):
    x = 0.6 + i * 4.15
    box(s, x, 2.25, 3.85, 2.75, fill=G50, name=f"Fit card {i+1}")
    text(s, x + 0.35, 2.55, 3.2, 0.9, h, size=21, bold=True, color=G900, name=f"Fit {i+1}")
    text(s, x + 0.35, 3.45, 3.2, 1.5, b, size=15, color=INK, name=f"Fit {i+1} text")
text(s, 0.6, 5.45, 12.1, 0.9, [[("3.5 million", {"bold": True, "color": G700}), (" S-Bank customers; S-mobiili is used weekly by ", {}),
                               ("1 in 3", {"bold": True, "color": G700}), (" Finnish adults. A reason to open the app before payday, not after the overdraft.", {})]],
     size=19, color=INK, name="Who it serves")
text(s, 0.6, 6.55, 12, 0.4, "Source: S-Pankki challenge brief, Junction 2026. Prototype on synthetic data; not integrated with S-Bank systems.",
     size=12, color=MUTED, name="Source")
notes(s, DRAFT + "★ Stage slide. 2:25-2:45. Business case in one line (Rasmus's note: don't waste demo time on it).\n"
      "No claims of real S-mobiili integration or real PSD2 balances (the other bank is demo data).")

# 10 --------------------------------------------------------------- Close (dark)
s = prs.slides.add_slide(BLANK); bg(s, G900); mark(s, dark=True)
text(s, 0.6, 2.0, 12.1, 0.9, "See your money's future, and change it.", size=40, bold=True, color=WHITE, name="Tagline")
text(s, 0.6, 3.25, 12, 0.6, "Try it: spankki.psavela.com  (password from the team)", size=22, color=G300, name="Try it")
text(s, 0.6, 5.3, 12, 1.0, "[Team names and roles]", size=18, color=G100, name="Team")
text(s, 0.6, 6.55, 12, 0.4, "Prototype on the S-Pankki challenge's synthetic data.", size=13, color=G300, name="Disclaimer")
notes(s, "★ Stage slide. 2:45-2:50. Tagline is Rasmus's ('See your money's future, and change it').\n"
      "Team names and roles: Rasmus to fill in. Names go on the last slide only (hook first).\n\n"
      "STAGE VERSION (3:00, Rasmus's plan v1): slides 1, 2, 3, then live demo (fallback: the video clip), 7, 9, 10. "
      "Deck PDF for the submission: all 10.")

prs.save(__import__("os").path.join(__import__("os").path.dirname(__file__), "S-Pankki-pitch.pptx"))
print("saved")
