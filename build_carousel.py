#!/usr/bin/env python3
"""
Vasco Yaps daily AI carousel renderer (news + tutorials).
Reads content.json and renders 1080x1350 PNG slides.

Theme: set env CAROUSEL_THEME = "dark" (default) or "warm".
"""
import os, sys, json, math, importlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------- fonts ----------
def _font_files(pkg):
    d = os.path.dirname(importlib.import_module(pkg).__file__)
    sub = os.path.join(d, "files")
    return sub if os.path.isdir(sub) else d
SSP = _font_files("font_source_sans_pro")
def f_black(s): return ImageFont.truetype(os.path.join(SSP, "SourceSansPro-Black.ttf"), s)
def f_bold(s):  return ImageFont.truetype(os.path.join(SSP, "SourceSansPro-Bold.ttf"), s)
def f_semi(s):  return ImageFont.truetype(os.path.join(SSP, "SourceSansPro-Semibold.ttf"), s)
def f_reg(s):   return ImageFont.truetype(os.path.join(SSP, "SourceSansPro-Regular.ttf"), s)

def _brands_path():
    import fontawesomefree as fa
    return os.path.join(os.path.dirname(fa.__file__),
                        "static/fontawesomefree/webfonts/fa-brands-400.ttf")
BRANDS = _brands_path()
def f_brand(s): return ImageFont.truetype(BRANDS, s)

SOCIALS = [
    ("instagram", "", "@vascoyaps"),
    ("tiktok",    "", "@vascoyaps"),
    ("youtube",   "", "@vascoyaps"),
    ("substack",  None,     "@vascoyaps"),
]

# ---------- themes ----------
THEMES = {
    "dark": {
        "bg_top": (10, 12, 20), "bg_bot": (16, 20, 31),
        "ink": (255, 255, 255), "body": (214, 221, 230), "mute": (150, 161, 178),
        "accent": (31, 224, 200),
        "grad_bar": ((31, 224, 200), (31, 224, 200)),
        "grad_key": ((31, 224, 200), (31, 224, 200)),
        "ghost": ((31, 224, 200), 20), "dot_off": (60, 68, 82),
        "pill_grad": ((31, 224, 200), (31, 224, 200)), "pill_text": (8, 12, 20),
        "icon": (255, 255, 255),
        "cover_glows": [(0.18, 0.20, 520, (124, 92, 255), 70), (0.92, 0.30, 460, (59, 130, 246), 60), (0.70, 0.86, 520, (31, 224, 200), 55)],
        "cover_waves": [(0.86, 46, (31, 224, 200), 5, 55, 2.0, 0.4), (0.89, 38, (124, 92, 255), 4, 42, 2.4, 1.6)],
        "content_glows": [(0.90, 0.08, 420, (59, 130, 246), 42), (0.05, 0.96, 460, (124, 92, 255), 40)],
        "content_wave": (0.945, 26, (31, 224, 200), 4, 70, 2.2, 0.6),
    },
    "warm": {
        "bg_top": (250, 246, 238), "bg_bot": (243, 235, 222),
        "ink": (33, 28, 22), "body": (74, 66, 55), "mute": (122, 112, 99),
        "accent": (205, 88, 44),
        "grad_bar": ((205, 88, 44), (205, 88, 44)),
        "grad_key": ((205, 88, 44), (205, 88, 44)),
        "ghost": ((205, 88, 44), 34), "dot_off": (216, 205, 186),
        "pill_grad": ((205, 88, 44), (205, 88, 44)), "pill_text": (74, 27, 12),
        "icon": (33, 28, 22),
        "cover_glows": [(0.15, 0.18, 560, (232, 160, 107), 34), (0.92, 0.30, 460, (124, 138, 107), 26), (0.72, 0.88, 560, (218, 117, 72), 30)],
        "cover_waves": [(0.86, 46, (124, 138, 107), 5, 60, 2.0, 0.4), (0.89, 38, (218, 117, 72), 4, 60, 2.4, 1.6)],
        "content_glows": [(0.90, 0.08, 420, (232, 160, 107), 26), (0.05, 0.96, 460, (124, 138, 107), 24)],
        "content_wave": (0.945, 26, (218, 117, 72), 4, 80, 2.2, 0.6),
    },
}
T = THEMES.get(os.environ.get("CAROUSEL_THEME", "warm"), THEMES["warm"])

W, H = 1080, 1350
MARGIN = 96

def lerp(a, b, t): return tuple(int(a[i] + (b[i]-a[i])*t) for i in range(3))

def vgrad(top, bot):
    g = Image.new("RGB", (1, H))
    for y in range(H): g.putpixel((0, y), lerp(top, bot, y/(H-1)))
    return g.resize((W, H))

def grad_h(w, h, c1, c2):
    g = Image.new("RGB", (max(1, w), 1))
    for x in range(max(1, w)): g.putpixel((x, 0), lerp(c1, c2, x/max(1, w-1)))
    return g.resize((max(1, w), h))

def grad_text(img, xy, text, font, c1, c2):
    """Draw gradient-filled text without clipping descenders (g, p, y, q, j)."""
    asc, desc = font.getmetrics()
    th = asc + desc + 8
    tw = max(1, int(ImageDraw.Draw(img).textlength(text, font=font)))
    mask = Image.new("L", (tw, th), 0)
    ImageDraw.Draw(mask).text((0, 0), text, font=font, fill=255)
    img.paste(grad_h(tw, th, c1, c2), (int(xy[0]), int(xy[1])), mask)
    return tw

def glow(img, xy, r, color, alpha):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse([xy[0]-r, xy[1]-r, xy[0]+r, xy[1]+r], fill=color+(alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(r*0.55))
    base = img.convert("RGBA"); base.alpha_composite(layer)
    return base.convert("RGB")

def wave(img, y0, amp, color, width, alpha, periods=2.2, phase=0.0):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pts = [(x, y0 + amp*math.sin((x/W)*periods*2*math.pi + phase)) for x in range(-20, W+20, 4)]
    ImageDraw.Draw(layer).line(pts, fill=color+(alpha,), width=width, joint="curve")
    layer = layer.filter(ImageFilter.GaussianBlur(1))
    base = img.convert("RGBA"); base.alpha_composite(layer)
    return base.convert("RGB")

# ---------- text ----------
def tracked(draw, xy, text, font, fill, tracking=0):
    x, y = xy
    for c in text:
        draw.text((x, y), c, font=font, fill=fill)
        x += draw.textlength(c, font=font) + tracking

def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def fit_headline(draw, text, max_w, max_h, start=92, lh=1.04, mins=56):
    s = start
    while s >= mins:
        fnt = f_black(s); lines = wrap(draw, text, fnt, max_w)
        if len(lines)*s*lh <= max_h: return fnt, lines, s*lh
        s -= 2
    fnt = f_black(mins); return fnt, wrap(draw, text, fnt, max_w), mins*lh

# ---------- furniture ----------
def background(cover=False):
    img = vgrad(T["bg_top"], T["bg_bot"])
    glows = T["cover_glows"] if cover else T["content_glows"]
    for rx, ry, r, col, a in glows:
        img = glow(img, (W*rx, H*ry), r, col, a)
    if cover:
        for y0r, amp, col, wd, a, per, ph in T["cover_waves"]:
            img = wave(img, H*y0r, amp, col, wd, a, per, ph)
    else:
        y0r, amp, col, wd, a, per, ph = T["content_wave"]
        img = wave(img, H*y0r, amp, col, wd, a, per, ph)
    return img

def kicker(draw, text, y):
    bar = grad_h(54, 8, *T["grad_bar"])
    draw._image.paste(bar, (MARGIN, y+10))
    tracked(draw, (MARGIN+78, y-6), text.upper(), f_bold(31), T["accent"], tracking=4)

def ghost_index(img, n):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer); fnt = f_black(300)
    w = d.textlength(str(n), font=fnt)
    d.text((W-MARGIN-w+30, 70), str(n), font=fnt, fill=T["ghost"][0]+(T["ghost"][1],))
    base = img.convert("RGBA"); base.alpha_composite(layer)
    return base.convert("RGB")

def footer(draw, page=None, total=8, swipe=False):
    y = H-86
    draw.text((MARGIN, y), "@vascoyaps", font=f_bold(34), fill=T["mute"])
    if swipe:
        f = f_bold(32); wsw = draw.textlength("swipe", font=f)
        draw.text((W-MARGIN-wsw-44, y+1), "swipe", font=f, fill=T["mute"])
        ax = W-MARGIN-30
        draw.line([(ax-14, y+18), (ax+8, y+18)], fill=T["accent"], width=4)
        draw.line([(ax-2, y+8), (ax+10, y+18)], fill=T["accent"], width=4)
        draw.line([(ax-2, y+28), (ax+10, y+18)], fill=T["accent"], width=4)
    elif page:
        n, dot, gap = total, 12, 18
        tot = n*dot+(n-1)*gap; x0 = W-MARGIN-tot; cy = y+22
        for i in range(n):
            on = (i == page-1); col = T["accent"] if on else T["dot_off"]
            r = dot//2 + (2 if on else 0); cx = x0+i*(dot+gap)+dot//2
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=col)

def _bullets_height(draw, items, max_w, fsize, gap):
    f = f_reg(fsize); total = 0
    for it in items:
        n = max(1, len(wrap(draw, it, f, max_w-46)))
        total += n*int(fsize*1.28) + gap
    return total

def fit_bullets(draw, items, max_w, avail_h):
    for fsize in range(39, 25, -1):
        gap = max(18, int(fsize*0.80))
        if _bullets_height(draw, items, max_w, fsize, gap) <= avail_h:
            return fsize, gap
    return 26, 18

def bullets(draw, items, x, y, max_w, fsize=39, gap=34):
    f = f_reg(fsize)
    for it in items:
        draw.ellipse([x, y+fsize*0.46, x+14, y+fsize*0.46+14], fill=T["accent"])
        ty = y
        for ln in wrap(draw, it, f, max_w-46):
            draw.text((x+46, ty), ln, font=f, fill=T["body"]); ty += int(fsize*1.28)
        y = ty + gap
    return y

def draw_substack(d, x, y, s, fill):
    bar = s * 0.205
    d.rectangle([x, y, x + s, y + bar], fill=fill)
    d.rectangle([x, y + bar * 1.55, x + s, y + bar * 2.55], fill=fill)
    d.polygon([(x, y + bar * 3.1), (x + s, y + bar * 3.1), (x + s / 2, y + s)], fill=fill)

# ---------- slides ----------
def cover(c):
    img = background(cover=True); d = ImageDraw.Draw(img)
    kicker(d, c["kicker"], 150)
    maxw = W - 2 * MARGIN
    hs = 120
    while hs > 56 and max(d.textlength(ln, font=f_black(hs)) for ln in c["title_lines"]) > maxw:
        hs -= 2
    f = f_black(hs); lh = int(hs * 1.02); y = 300
    for ln in c["title_lines"][:-1]:
        d.text((MARGIN, y), ln, font=f, fill=T["ink"]); y += lh
    grad_text(img, (MARGIN, y), c["title_lines"][-1], f, *T["grad_key"]); y += lh + 40
    sf = f_semi(40)
    for ln in wrap(d, c["subtitle"], sf, W-2*MARGIN-40):
        d.text((MARGIN, y), ln, font=sf, fill=T["mute"]); y += int(40*1.36)
    footer(d, swipe=True); return img

def content(card, page, total=8):
    img = background(); img = ghost_index(img, card["index"]); d = ImageDraw.Draw(img)
    kicker(d, card["label"], 150)
    fnt, lines, lh = fit_headline(d, card["headline"], W-2*MARGIN, 360)
    y = 250
    for ln in lines: d.text((MARGIN, y), ln, font=fnt, fill=T["ink"]); y += int(lh)
    y += 38; img.paste(grad_h(180, 6, *T["grad_bar"]), (MARGIN, y)); d = ImageDraw.Draw(img); y += 46
    avail = (H - 150) - y
    fsize, gap = fit_bullets(d, card["bullets"], W-2*MARGIN, avail)
    bullets(d, card["bullets"], MARGIN, y, W-2*MARGIN, fsize=fsize, gap=gap)
    footer(d, page=page, total=total); return img

def cta(c):
    img = background(cover=True); d = ImageDraw.Draw(img)
    kicker(d, c.get("kicker", "THAT'S TODAY IN AI"), 150)
    y = 250
    d.text((MARGIN, y), c.get("line1", "Follow"), font=f_black(104), fill=T["ink"])
    key = c.get("handle", "@vascoyaps"); f = f_black(104)
    grad_text(img, (MARGIN, y + 104), key, f, *T["grad_key"]); d = ImageDraw.Draw(img)
    y += 104 + 130
    d.text((MARGIN, y), "AI news, decoded daily.", font=f_reg(40), fill=T["mute"])
    y += 92
    isz = 50; row = 92; tx = MARGIN + 78; fh = f_semi(40)
    glyphs = {"instagram": "", "tiktok": "", "youtube": ""}
    for plat, _ic, handle in SOCIALS:
        cy = y + 24
        if plat == "substack":
            draw_substack(d, MARGIN + 2, cy - (isz - 4) / 2, isz - 4, T["icon"])
        else:
            d.text((MARGIN, cy), glyphs[plat], font=f_brand(isz), fill=T["icon"], anchor="lm")
        d.text((tx, cy), handle, font=fh, fill=T["body"], anchor="lm")
        y += row
    y += 20
    pill = "  " + c.get("pill", "Save this  ·  Send it to a friend") + "  "
    fp = f_bold(36); pw = int(d.textlength(pill, font=fp)) + 20; ph = 84
    rad = Image.new("L", (pw, ph), 0); ImageDraw.Draw(rad).rounded_rectangle([0, 0, pw, ph], ph//2, fill=255)
    img.paste(grad_h(pw, ph, *T["pill_grad"]), (MARGIN, y), rad); d = ImageDraw.Draw(img)
    d.text((MARGIN + pw/2, y + ph/2), pill.strip(), font=fp, fill=T["pill_text"], anchor="mm")
    footer(d); return img

def main():
    content_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "content.json")
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "output")
    os.makedirs(out_dir, exist_ok=True)
    data = json.load(open(content_path))
    total = 2 + len(data["cards"])
    cover(data["cover"]).save(os.path.join(out_dir, "slide_01.png"))
    page = 2
    for card in data["cards"]:
        content(card, page, total).save(os.path.join(out_dir, f"slide_{page:02d}.png")); page += 1
    cta(data["cta"]).save(os.path.join(out_dir, f"slide_{page:02d}.png"))
    print(f"Rendered {page} slides to {out_dir} (theme={os.environ.get('CAROUSEL_THEME','warm')})")

if __name__ == "__main__":
    main()
