"""S-Pankki pitch deck, editorial version (Pyry's Claude, 15 Nov): less text, bold statements, real examples.
Follows the v4 editorial studies and HANDOFF-SLIDES.md by Rasmus's Claude (review/rasmus-slides, cbd213a): three
families only (statement, product hero, proof with an emerald ring), 0.7 in margins, footer at 7.0 in, at most one
sentence per slide, real app screens only (no generated UI), Geologica. Same story and numbers as the film.
Headlines are DRAFTS for Rasmus (his rule: no AI-written slide text without his OK). Tagline: TAGLINE below.
Run: python docs/slides/build_editorial.py  ->  docs/slides/S-Pankki-editorial.pptx (export to PDF from any office app)
"""
import os
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt
from lxml import etree

FOREST, EMERALD, LEAF, MINT, PALE, BG = "003D25", "00703C", "2E9C5E", "8FD0A8", "D7EFE0", "EEF8F2"
INK, MUTED, RED, WHITE = "0F2219", "66786E", "C2402F", "FFFFFF"
FONT = "Geologica"  # the app font (install it before exporting the PDF)
HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "shots-final")  # final build, 15 Nov 03:30, Emma, EN, 390x844 @2x
CROPS = os.path.join(HERE, "crops"); os.makedirs(CROPS, exist_ok=True)

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
rgb = RGBColor.from_string


def bg(s, c):
    f = s.background.fill; f.solid(); f.fore_color.rgb = rgb(c)


def text(s, x, y, w, h, paras, size=20, color=INK, bold=False, spacing=0.92, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, name=None):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, para in enumerate(paras if isinstance(paras, list) else [paras]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = spacing; p.alignment = align
        for t, o in (para if isinstance(para, list) else [(para, {})]):
            r = p.add_run(); r.text = t; f = r.font
            f.name = FONT; f.size = Pt(o.get("size", size)); f.bold = o.get("bold", bold)
            f.color.rgb = rgb(o.get("color", color))
    return tb


def footer(s, t, dark=False):
    text(s, 0.7, 7.0, 7.4, 0.3, t, size=11, color=MINT if dark else MUTED, name="Footer")


def shadow(pic):
    sp = pic._element.spPr
    eff = etree.SubElement(sp, qn("a:effectLst"))
    sh = etree.SubElement(eff, qn("a:outerShdw"), blurRad="380000", dist="120000", dir="5400000", algn="t", rotWithShape="0")
    c = etree.SubElement(sh, qn("a:srgbClr"), val=FOREST)
    etree.SubElement(c, qn("a:alpha"), val="22000")


def rounded(pic, val=3500):
    g = pic._element.spPr.find(qn("a:prstGeom")); g.set("prst", "roundRect")
    av = g.find(qn("a:avLst"))
    if av is None:
        av = etree.SubElement(g, qn("a:avLst"))
    gd = etree.SubElement(av, qn("a:gd")); gd.set("name", "adj"); gd.set("fmla", f"val {val}")


class Placed:
    """A real screenshot crop on a slide; .at(px, py) maps a pixel of the ORIGINAL screenshot to slide inches."""
    def __init__(self, s, img, box, x, y, h=None, w=None, name="Screen", shade=True, radius=3500):
        im = Image.open(os.path.join(SHOTS, img))
        box = box or (0, 0, im.width, im.height)
        crop = im.crop(box); path = os.path.join(CROPS, f"{name}.png"); crop.save(path)
        if h:
            w = h * crop.width / crop.height
        else:
            h = w * crop.height / crop.width
        self.pic = s.shapes.add_picture(path, Inches(x), Inches(y), Inches(w), Inches(h)); self.pic.name = name
        rounded(self.pic, radius)
        if shade:
            shadow(self.pic)
        self.x, self.y, self.k, self.box = x, y, w / crop.width, box

    def at(self, px, py):
        return self.x + (px - self.box[0]) * self.k, self.y + (py - self.box[1]) * self.k


def ring(s, placed, box_px, name="Ring"):
    """A thin emerald ring on the exact thing the slide talks about."""
    x0, y0 = placed.at(box_px[0], box_px[1]); x1, y1 = placed.at(box_px[2], box_px[3])
    o = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x0 - 0.08), Inches(y0 - 0.06), Inches(x1 - x0 + 0.16), Inches(y1 - y0 + 0.12))
    o.fill.background(); o.line.color.rgb = rgb(EMERALD); o.line.width = Pt(3); o.shadow.inherit = False; o.name = name


def pill(s, x, y, t, size=20, fill=EMERALD, color=WHITE, name="Question"):
    """A question bubble in the app's own style (the user's green bubble)."""
    w = 0.42 + len(t) * size * 0.0076
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(size / 72 * 1.3 + 0.26))
    b.adjustments[0] = 0.5; b.fill.solid(); b.fill.fore_color.rgb = rgb(fill); b.line.fill.background(); b.shadow.inherit = False
    b.name = name
    tf = b.text_frame; tf.margin_left = tf.margin_right = Inches(0.21); tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE; tf.word_wrap = False
    p = tf.paragraphs[0]; r = p.add_run(); r.text = t
    r.font.name = FONT; r.font.size = Pt(size); r.font.bold = True; r.font.color.rgb = rgb(color)
    return w


def notes(s, t):
    s.notes_slide.notes_text_frame.text = t



DRAFT = "DRAFT HEADLINE for Rasmus to approve. "
DATA = "Real app screens, final build, 15 Nov. Emma is a synthetic customer from the S-Pankki challenge data."
M = 0.7  # margin and shared top line
TAGLINE = "Ask your money. It answers with receipts."  # chosen by Pyry, 15 Nov; also in docs/PITCH.md

# 1 Cover (statement + screen entering from the right edge, bleeding off the bottom) ------------------------------
s = prs.slides.add_slide(BLANK); bg(s, BG)
text(s, M, M, 7.6, 4.8, "Will her money last until payday?", size=78, bold=True, color=FOREST, spacing=0.86, name="Statement")
text(s, M, 6.0, 7.0, 0.5, "Emma has 699.85 € today.", size=24, color=INK, name="One sentence")
Placed(s, "home.png", (0, 0, 780, 1520), 8.9, M, h=7.5 - M + 0.4, name="Emma's Home (bleeds off the bottom)", radius=2200)
footer(s, "S-Pankki challenge  |  Junction 2026")
notes(s, DRAFT + "★ Stage. The film's question. 699.85 € = balance on 30 Sep 2026 (money.customer).")

# 2 Forecast (product hero: the real chart, bleeding off the right edge) -------------------------------------------
s = prs.slides.add_slide(BLANK); bg(s, WHITE)
text(s, M, M, 5.6, 0.4, "Payday, 15 October", size=20, color=MUTED, name="Kicker")
text(s, M, 1.25, 5.8, 1.8, "−997 €", size=112, bold=True, color=RED, name="Statement number")
text(s, M, 3.2, 5.2, 1.2, "Rent leaves on 3 October.", size=22,
     color=INK, spacing=1.05, name="One sentence")
p = Placed(s, "home.png", (0, 560, 780, 1292), 7.0, M, w=6.6, name="Forecast chart (bleeds right)",
           shade=False, radius=1200)
ring(s, p, (480, 985, 740, 1030), name="Ring on rent")
notes(s, DRAFT + "★ Stage. -997.24 € at her usual pace (future.future); rent 762.79 € on 3 Oct (insights.ribbon). "
      "The ring marks the rent step on the real chart.")

# 3 Statement: the data ----------------------------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK); bg(s, BG)
text(s, M, M, 11.9, 2.6, "45 %", size=190, bold=True, color=RED, name="Statement number")
text(s, M, 3.5, 11.0, 1.2, "of overdrafts start in the last week before payday.", size=40, bold=True, color=FOREST,
     spacing=1.0, name="Statement")
text(s, M, 5.0, 10.5, 0.6, "Purchases under 10 € are 1 % of spending on extras.", size=22, color=INK,
     name="One sentence")
footer(s, "Source: S-Pankki challenge data, our analysis.")
notes(s, DRAFT + "Deck. RECOMPUTED 15 Nov: 45.5 % of overdraft moments (first purchase that takes the balance below zero) "
      "fall within 7 days of the next salary; median 8 days. The older '1 in 2' overstated it. Purchases under 10 € are "
      "15 % of extra purchases by count but 1.3 % of the money spent on extras.")

# 4 Proof: every amount opens its payments -------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK); bg(s, WHITE)
text(s, M, M, 4.9, 2.6, "Tap an amount, see the payments", size=38, bold=True, color=FOREST,
     spacing=0.95, name="Title")
text(s, M, 3.6, 4.6, 1.2, "508.37 € on eating out = 10 payments.", size=22, color=INK,
     spacing=1.05, name="One sentence")
a = Placed(s, "eat.png", (0, 0, 780, 1688), 5.85, M, h=7.0 - M - 0.25, name="Answer", radius=2200)
ring(s, a, (462, 570, 590, 608), name="Ring on 508.37")
b = Placed(s, "payments.png", (0, 0, 780, 1688), 9.45, M, h=7.0 - M - 0.25, name="The 10 payments", radius=2200)
ring(s, b, (600, 1566, 772, 1606), name="Ring on the total")
notes(s, DRAFT + "★ Stage. get_spending category Restaurants, 1 Jul-30 Sep: 508.37 €, 10 payments (169.46 € a month). "
      "Green = from her data; numbers are matched to the calculations on her data (never 'guaranteed').")

# 5 Pause (product hero) -------------------------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK); bg(s, BG)
text(s, M, M, 6.6, 0.4, "Pause every extra until payday", size=20, color=MUTED, name="Kicker")
text(s, M, 1.2, 7.0, 1.2, [[("−997 €", {"color": MUTED}), (" → ", {"color": MINT}), ("−676 €", {"color": RED})]],
     size=60, bold=True, name="Statement numbers")
text(s, M, 2.55, 6.6, 1.0, "Better. Still short.", size=54, bold=True, color=FOREST, name="Statement")
p = Placed(s, "pause.png", (0, 10, 780, 1250), 8.0, M, h=7.5 - M + 0.4, name="Pause answer (bleeds off the bottom)", radius=2200)
notes(s, DRAFT + "★ Stage (film: 'Better. Still short, though.'). -997.24 € usual pace, -675.72 € with extras paused "
      "(forecast_with_events). Never present moving rent as a fix.")

# 6 Statement: the year (dark) ---------------------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK); bg(s, FOREST)
text(s, M, M, 11.9, 2.7, "−2,468 €", size=190, bold=True, color=WHITE, name="Statement number")
text(s, M, 3.65, 10.5, 1.2, "more spent than earned in a year", size=34, bold=True,
     color=PALE, spacing=1.05, name="One sentence")
footer(s, "In 25,855 €, out 28,323 €, Oct 2025 to Sep 2026.", dark=True)
notes(s, DRAFT + "★ Stage (film: 'she's been spending more than she earns'). 25,855.24 in, 28,323.07 out = 2,467.83 "
      "(about 206 € a month). The honest ending: a two-week cut can't close it; she now knows which basket to work on.")

# 7 Proof: play, then check -----------------------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK); bg(s, WHITE)
text(s, M, M, 4.9, 2.6, "Play the next two weeks. Then check.", size=36, bold=True,
     color=FOREST, spacing=0.95, name="Title")
text(s, M, 3.7, 4.6, 1.2, "Her guess: under 20 % on extras. Her data: 32 %.", size=22, color=INK,
     spacing=1.05, name="One sentence")
Placed(s, "card_extra.png", (0, 0, 780, 1688), 5.85, M, h=7.0 - M - 0.25, name="Play: a 40 € extra", radius=2200)
q = Placed(s, "quest_reveal.png", (0, 0, 780, 1688), 9.45, M, h=7.0 - M - 0.25, name="Quest: guess, then her data", radius=2200)
ring(s, q, (128, 1408, 252, 1472), name="Ring on 32 %")
notes(s, DRAFT + "Deck (stage if time). Film: 'Skip a forty-euro extra' and 'check what she's learned'. The card: "
      "Fast food & cafes, Fri 2 Oct, 40 € = 3.0 h of her work. Quest: guess < 20 %, actual 32 % (learning.facts_from_data "
      "everyday_share 0.324, 699 € a month). Curiosity progress is engagement, not measured learning.")

# 8 Statement: trust (dark) ----------------------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK); bg(s, FOREST)
text(s, M, M, 11.9, 2.4, "25 / 25", size=170, bold=True, color=WHITE, name="Statement number")
text(s, M, 3.4, 11.0, 1.4, "trick questions passed", size=34,
     bold=True, color=PALE, spacing=1.05, name="One sentence")
footer(s, "Run on the live coach, Gemma 4 in Finland.", dark=True)
notes(s, DRAFT + "★ Stage. scripts/run_traps.py --eu on build 8af1606: 25/25 passed, 51/51 numbers matched. The cases "
      "(tests/traps/cases.py) include wrong 'last month', invented merchants, prompt injection for another customer's "
      "data, quick loans, made-up projections, unsourced statistics and a hateful request.")

# 9 Proof: S-mobiili ------------------------------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK); bg(s, BG)
text(s, M, M, 7.6, 1.6, "Built for S-mobiili", size=40, bold=True, color=FOREST, spacing=0.95,
     name="Title")
for i, (big, lab) in enumerate([("3.5 million", "S-Bank customers"), ("1 in 3", "Finnish adults use S-mobiili every week")]):
    text(s, M, 2.55 + i * 1.75, 7.5, 1.0, big, size=66, bold=True, color=EMERALD, name=f"Reach {i+1}")
    text(s, M, 3.55 + i * 1.75, 7.5, 0.5, lab, size=22, color=INK, name=f"Reach {i+1} label")
Placed(s, "home.png", (0, 0, 780, 1688), 9.45, M, h=7.0 - M - 0.25, name="The app, whole screen", radius=2200)
footer(s, "Source: S-Pankki challenge brief.")
notes(s, DRAFT + "★ Stage. Mobile web app in English, Finnish and Swedish; the model runs in Finland and sees totals only. "
      "PSD2 consent flow exists with demo data for the other bank.")

# 10 Close ------------------------------------------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK); bg(s, FOREST)
text(s, M, 1.6, 11.9, 2.2, [TAGLINE.split(". ", 1)[0] + ".", TAGLINE.split(". ", 1)[1]], size=66, bold=True, color=WHITE, spacing=0.95, name="Tagline")
text(s, M, 4.0, 11.9, 0.6, "spankki.psavela.com", size=30, color=MINT, name="URL")
text(s, M, 5.1, 11.9, 0.6, "[Team names and roles]", size=22, color=PALE, name="Team")
footer(s, "Synthetic data from the S-Pankki challenge.", dark=True)
notes(s, "★ Stage. Tagline chosen by Pyry on 15 Nov (Rasmus may still swap it; edit TAGLINE at the top). Team names and roles: Rasmus.")

STAGE = [1, 2, 4, 5, 6, 8, 10]  # the 3-minute version (7 slides); live demo after slide 4 or in place of it
out = os.path.join(HERE, "S-Pankki-editorial.pptx"); prs.save(out)
stage = Presentation(out)
ids = stage.slides._sldIdLst
for i, sid in reversed(list(enumerate(list(ids), start=1))):
    if i not in STAGE:
        stage.part.drop_rel(sid.get(qn("r:id"))); ids.remove(sid)
stage.save(os.path.join(HERE, "S-Pankki-editorial-stage.pptx"))
print("saved full + stage")
