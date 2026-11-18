#!/usr/bin/env python3
"""
THE WORLD TODAY -- a one-page broadsheet for Tuesday 17 November 2026.

This module paints a 1024 x 1024 navy-on-cream front page with PIL.
The page is assembled from the copy deck further down plus five
engraved plates that live beside this file (art_*.png).  No network
access is needed and repeated runs produce identical bytes.

Layout is planned in "units" (one unit = one output pixel) while the
canvas is rasterised at twice that size and shrunk at the end, which
keeps the small serif type crisp at thumbnail scale.
"""

import os

from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ ink
PAPER = (247, 242, 223)        # warm cream of the sheet itself
PAPER_HI = (250, 246, 230)     # brightest tone inside a plate
NAVY = (22, 41, 77)            # headline navy
INK = (17, 34, 66)             # slightly deeper navy for running text
NAVY_DEEP = (10, 22, 45)       # shadow tone inside a plate
NAVY_HALF = (86, 108, 150)     # halftone mid inside a plate

# ------------------------------------------------------------------ type
NOTO = "/usr/share/fonts/truetype/noto"
F_DISPLAY = os.path.join(NOTO, "NotoSerifDisplay-Black.ttf")
F_BLACK = os.path.join(NOTO, "NotoSerif-Black.ttf")
F_SERIF = os.path.join(NOTO, "NotoSerif-Regular.ttf")
F_SERIF_IT = os.path.join(NOTO, "NotoSerif-Italic.ttf")
F_SANS_B = os.path.join(NOTO, "NotoSans-Bold.ttf")

PAGE = 1024                    # final square edge, pixels
SS = 2                         # supersampling factor while drawing

_cache = {}


def face(path, size_units):
    """Cached TrueType face at a size given in page units."""
    px = max(4, int(round(size_units * SS)))
    key = (path, px)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(path, px)
    return _cache[key]


class Press:
    """A drawing surface that speaks in page units, not raw pixels."""

    def __init__(self):
        self.sheet = Image.new("RGB", (PAGE * SS, PAGE * SS), PAPER)
        self.pen = ImageDraw.Draw(self.sheet)

    @staticmethod
    def px(v):
        return int(round(v * SS))

    # ---------------------------------------------------------- rules
    def hline(self, x0, x1, y, weight=1.2, tone=NAVY):
        self.pen.line([self.px(x0), self.px(y), self.px(x1), self.px(y)],
                      fill=tone, width=max(1, self.px(weight)))

    def vline(self, x, y0, y1, weight=1.0, tone=NAVY):
        self.pen.line([self.px(x), self.px(y0), self.px(x), self.px(y1)],
                      fill=tone, width=max(1, self.px(weight)))

    def frame(self, x, y, w, h, weight=1.4, tone=NAVY):
        self.pen.rectangle([self.px(x), self.px(y), self.px(x + w),
                            self.px(y + h)], outline=tone,
                           width=max(1, self.px(weight)))

    def slab(self, x, y, w, h, tone=NAVY):
        self.pen.rectangle([self.px(x), self.px(y), self.px(x + w),
                            self.px(y + h)], fill=tone)

    # ---------------------------------------------------------- words
    def width_of(self, s, fnt, tracking=0.0):
        w = self.pen.textlength(s, font=fnt) / SS
        if tracking and len(s) > 1:
            w += tracking * (len(s) - 1)
        return w

    def put(self, x, y, s, fnt, tone=INK, tracking=0.0):
        """Draw one line; returns the advance width in units."""
        if not tracking:
            self.pen.text((self.px(x), self.px(y)), s, font=fnt, fill=tone)
            return self.width_of(s, fnt)
        cx = x
        for ch in s:
            self.pen.text((self.px(cx), self.px(y)), ch, font=fnt, fill=tone)
            cx += self.pen.textlength(ch, font=fnt) / SS + tracking
        return cx - x - tracking

    def put_centred(self, cx, y, s, fnt, tone=INK, tracking=0.0):
        return self.put(cx - self.width_of(s, fnt, tracking) / 2.0,
                        y, s, fnt, tone, tracking)

    def wrap(self, s, fnt, max_w):
        """Greedy word wrap measured against max_w units."""
        lines, cur = [], ""
        for word in s.split():
            trial = word if not cur else cur + " " + word
            if not cur or self.width_of(trial, fnt) <= max_w:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def paragraph(self, x, y, s, fnt, max_w, leading, tone=INK):
        """Draw wrapped text; returns the y just past its last line."""
        lines = self.wrap(s, fnt, max_w)
        for i, ln in enumerate(lines):
            self.put(x, y + i * leading, ln, fnt, tone)
        return y + len(lines) * leading

    def paste(self, img, x, y):
        self.sheet.paste(img, (self.px(x), self.px(y)))

    def finish(self):
        return self.sheet.resize((PAGE, PAGE), Image.LANCZOS)


def shrink_to_fit(press, s, path, want, floor, max_w, tracking=0.0):
    """Largest size <= want at which s still fits max_w on one line."""
    size = want
    while size > floor:
        fnt = face(path, size)
        if press.width_of(s, fnt, tracking) <= max_w:
            return size, fnt
        size -= 0.5
    return floor, face(path, floor)


def plate(filename, w_units, h_units, focus=0.5):
    """Crop an engraving to its slot and grade it to a navy duotone.

    Luminance is squeezed through a short tonal ladder first, which
    gives the pictures a printed, letterpress feel and keeps the
    five plates reading as one family on the sheet.
    """
    src = Image.open(os.path.join(HERE, filename)).convert("L")
    tw, th = Press.px(w_units), Press.px(h_units)
    scale = max(tw / src.width, th / src.height)
    src = src.resize((round(src.width * scale), round(src.height * scale)),
                     Image.LANCZOS)
    left = max(0, (src.width - tw) // 2)
    top = min(max(0, int((src.height - th) * focus)), src.height - th)
    src = src.crop((left, top, left + tw, top + th))
    src = ImageOps.autocontrast(src, cutoff=1)
    rungs = 44
    ladder = [int(round(round(v / 255.0 * (rungs - 1)) / (rungs - 1) * 255))
              for v in range(256)]
    src = src.point(ladder)
    return ImageOps.colorize(src, black=NAVY_DEEP, mid=NAVY_HALF,
                             white=PAPER_HI)


# ------------------------------------------------------------------ copy
MASTHEAD = "THE WORLD TODAY"
INFOBAR = "VOL. 1 · NO. 323 • TUESDAY, 17 NOVEMBER 2026 • ONE DAY · ONE PAGE"
BANNER = "BREAKING NEWS"

LEAD = {
    "kicker": "LEAD STORY — SHENZHEN, CHINA",
    "headline": "THREE LEADERS, ONE TABLE",
    "body": (
        "Beijing has made it official: on Thursday, Xi Jinping hosts "
        "Donald Trump and Vladimir Putin in Shenzhen — the first time "
        "the leaders of America, China and Russia have ever met in one "
        "room. Washington and Moscow had already said yes; China's word "
        "ends the suspense. Nuclear arms top the agenda."
    ),
    "quote": "“The beginning of a dialogue that we hope will be "
             "productive in the future.”",
    "attribution": "A U.S. OFFICIAL, ON THURSDAY'S TALKS",
    "art": "art_summit.png",
    "caption": (
        "Shenzhen hosts APEC's 21 economies this week — and on "
        "Thursday the world's three biggest nuclear powers take "
        "their seats at one table."
    ),
}

COLUMNS = [
    {
        "art": "art_bridge.png",
        "focus": 0.40,
        "headline": "UKRAINE DROPS PUTIN'S CRIMEA BRIDGE",
        "body": (
            "The seventh stage of the operation did it: Ukrainian "
            "drones smashed the road section of the Kerch Bridge "
            "while Neptune missiles hit the rail line, dropping an "
            "arch and its span into the strait's only shipping "
            "channel. Moscow answered with seven ballistic missiles "
            "on Kyiv's two river bridges, killing at least two people."
        ),
    },
    {
        "art": "art_hormuz.png",
        "focus": 0.45,
        "headline": "TANKERS BURN IN THE STRAIT OF HORMUZ",
        "body": (
            "Iran's Revolutionary Guards sent drones at a US radar "
            "at Bahrain's Sheikh Isa air base; Manama and Washington "
            "say all were intercepted, with no damage done. US jets "
            "answered by striking a Guards missile site "
            "on Qeshm Island. At sea, a supertanker and a gas carrier "
            "burned after striking mines; one seafarer is missing."
        ),
    },
    {
        "art": "art_gaza.png",
        "focus": 0.55,
        "headline": "WEST TO ISRAEL: OPEN GAZA'S GATES",
        "body": (
            "Four governments spoke as one: Britain, Australia, "
            "Canada and Italy urged Israel to stop the delays and "
            "open Gaza's crossings to aid at once. Some 150,000 tents "
            "sit held at the border while the first winter storm has "
            "swept away tens of thousands of shelters. The ministers "
            "called the misery catastrophic — and reversible."
        ),
    },
    {
        "art": "art_yemen.png",
        "focus": 0.45,
        "headline": "YEMEN'S ARMY FALLS BACK ON ADEN",
        "body": (
            "A second front is moving. Yemen's government has pulled "
            "its forces off the Red Sea coast and the Bab el-Mandeb "
            "shore to defend Aden, after Houthi fighters seized "
            "ground in Lahj, some 60 kilometres away. Saudi jets "
            "struck near Saada and Sanaa — but the coast is slipping "
            "from the government's grip."
        ),
    },
]

ALSO_TODAY = (
    "ALSO TODAY — Japan scrambles jets over a Russian airspace "
    "violation · 146,000 march in France's living-cost protests · "
    "COP31 ministers take over in Antalya, draft deal under fire"
)


# ------------------------------------------------------------------ bands
def story_column(p, x, w, top, bottom, item):
    """One news column: plate strip, headline, then fitted body copy."""
    p.paste(plate(item["art"], w, 46, focus=item.get("focus", 0.45)),
            x, top)
    p.frame(x, top, w, 46, weight=1.3)

    y = top + 46 + 7
    size = 20.5
    lines = []
    while size > 14.0:
        fnt = face(F_BLACK, size)
        lines = p.wrap(item["headline"], fnt, w)
        if len(lines) <= 3:
            break
        size -= 0.5
    step = size * 1.13
    for i, ln in enumerate(lines):
        p.put(x, y + i * step, ln, fnt, NAVY)
    y += len(lines) * step + 7

    size = 15.0
    while size > 12.0:
        fnt = face(F_SERIF, size)
        lines = p.wrap(item["body"], fnt, w)
        if y + len(lines) * size * 1.20 <= bottom:
            break
        size -= 0.5
    step = size * 1.20
    if lines and y + len(lines) * step > bottom:
        step = (bottom - y) / len(lines)
    for i, ln in enumerate(lines):
        p.put(x, y + i * step, ln, fnt, INK)
    return y + len(lines) * step


def lead_block(p, x, y, w_text, art_x, art_w):
    """The lead story: text column left, framed plate right."""
    p.put(x, y, LEAD["kicker"], face(F_SANS_B, 15), NAVY, tracking=1.6)

    hy = y + 25
    size = 43.0
    while size > 30.0:
        fnt = face(F_BLACK, size)
        lines = p.wrap(LEAD["headline"], fnt, w_text)
        if len(lines) <= 2:
            break
        size -= 0.5
    step = size * 1.05
    for i, ln in enumerate(lines):
        p.put(x, hy + i * step, ln, fnt, NAVY)

    by = hy + len(lines) * step + 9
    body_end = p.paragraph(x, by, LEAD["body"], face(F_SERIF, 18),
                           w_text, 22.5, INK)

    qy = body_end + 7
    qf = face(F_SERIF_IT, 16.5)
    qlines = p.wrap(LEAD["quote"], qf, w_text - 26)
    qh = 10 + len(qlines) * 21.5 + 18
    p.frame(x, qy, w_text, qh, weight=1.6)
    for i, ln in enumerate(qlines):
        p.put(x + 13, qy + 9 + i * 21.5, ln, qf, INK)
    p.put(x + 13, qy + qh - 17, LEAD["attribution"],
          face(F_SANS_B, 10.5), NAVY, tracking=1.0)

    art_h = 258
    p.paste(plate(LEAD["art"], art_w, art_h, focus=0.42), art_x, y)
    p.frame(art_x, y, art_w, art_h, weight=2.2)
    p.paragraph(art_x, y + art_h + 9, LEAD["caption"],
                face(F_SERIF_IT, 14.5), art_w, 19.5, INK)
    return qy + qh


def build_front_page():
    p = Press()
    M = 26.0
    W = PAGE - 2 * M
    cx = PAGE / 2.0

    # -- masthead ------------------------------------------------------
    msize, mfnt = shrink_to_fit(p, MASTHEAD, F_DISPLAY, 122, 60, W)
    p.put_centred(cx, 4, MASTHEAD, mfnt, NAVY)
    y = 4 + msize * 1.05
    p.hline(M, PAGE - M, y, 4.2)
    p.hline(M, PAGE - M, y + 6.5, 1.4)
    y += 14

    # -- info bar ------------------------------------------------------
    p.put_centred(cx, y, INFOBAR, face(F_SANS_B, 15.5), NAVY,
                  tracking=1.1)
    y += 25
    p.hline(M, PAGE - M, y, 1.4)
    p.hline(M, PAGE - M, y + 5, 4.2)
    y += 11

    # -- banner --------------------------------------------------------
    bsize, bfnt = shrink_to_fit(p, BANNER, F_DISPLAY, 118, 60, W)
    p.put_centred(cx, y, BANNER, bfnt, NAVY)
    y += bsize * 1.05 + 3
    p.hline(M, PAGE - M, y, 4.2)
    p.hline(M, PAGE - M, y + 6.5, 1.4)
    y += 15

    # -- lead ----------------------------------------------------------
    lead_end = lead_block(p, M, y, 444, M + 462, PAGE - M - (M + 462))
    y = max(lead_end, y + 300) + 12
    p.hline(M, PAGE - M, y, 2.0)
    y += 12

    # -- four columns --------------------------------------------------
    col_bottom = 946
    gap = 14
    cw = (W - 3 * gap) / 4.0
    for i, item in enumerate(COLUMNS):
        x = M + i * (cw + gap)
        if i:
            p.vline(x - gap / 2.0, y, col_bottom, weight=0.9)
        story_column(p, x, cw, y, col_bottom, item)

    # -- also today strip ----------------------------------------------
    sy, sh = 958, 44
    p.slab(M, sy, W, sh)
    sfnt = face(F_SANS_B, 14.5)
    lines = p.wrap(ALSO_TODAY, sfnt, W - 36)
    step = 16.5
    ty = sy + (sh - ((len(lines) - 1) * step + 15)) / 2.0
    for i, ln in enumerate(lines):
        p.put_centred(cx, ty + i * step, ln, sfnt, PAPER)

    return p.finish()


if __name__ == "__main__":
    img = build_front_page()
    out = os.path.join(HERE, "entry.png")
    img.save(out)
    print("wrote", out, img.size, os.path.getsize(out), "bytes")
