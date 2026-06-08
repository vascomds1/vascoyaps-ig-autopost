#!/usr/bin/env python3
"""
Vasco Yaps daily AI-news Instagram carousel renderer.
Reads content.json (produced by generate_copy.py) and renders 1080x1350 PNG slides.
Repo-relative; runs on a GitHub Actions runner.
"""
import os, sys, json, math, importlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------- locate fonts (pip: font-source-sans-pro, font-roboto) ----------
def _font_files(pkg):
    d = os.path.dirname(importlib.import_module(pkg).__file__)
    sub = os.path.join(d, "files")
    return sub if os.path.isdir(sub) else d
SSP = _font_files("font_source_sans_pro")
RBT = _font_files("font_roboto")
def f_black(s): return ImageFont.truetype(os.path.join(SSP, "SourceSansPro-Black.ttf"), s)
def f_bold(s):  return ImageFont.truetype(os.path.join(SSP, "SourceSansPro-Bold.ttf"), s)
def f_semi(s):  return ImageFont.truetype(os.path.join(SSP, "SourceSansPro-Semibold.ttf"), s)
def f_reg(s):   return ImageFont.truetype(os.path.join(SSP, "SourceSansPro-Regular.ttf"), s)

# Font Awesome brand glyphs (pip: fontawesomefree)
def _brands_path():
    import fontawesomefree as fa
    return os.path.join(os.path.dirname(fa.__file__),
                        "static/fontawesomefree/webfonts/fa-brands-400.ttf")
BRANDS = _brands_path()
def f_brand(s): return ImageFont.truetype(BRANDS, s)

# Social handles shown on the final slide. Edit handles here.
SOCIALS = [
    ("instagram", "", "@vascoyaps"),
    ("tiktok",    "", "@vascoyaps"),
    ("youtube",   "", "@vascoyaps"),
    ("substack",  None,     "@vascoyaps"),  # drawn manually (not in FA free)
]

def draw_substack(d, x, y, s, fill=(255, 255, 255)):
    """Draw the Substack mark inside an s-by-s box at (x, y)."""
    bar = s * 0.205
    d.rectangle([x, y, x + s, y + bar], fill=fill)
    d.rectangle([x, y + bar * 1.55, x + s, y + bar * 2.55], fill=fill)
    d.polygon([(x, y + bar * 3.1), (x + s, y + bar * 3.1), (x + s / 2, y + s)], fill=fill)

# ---------- canvas / palette ----------
W, H = 1080, 1350
MARGIN = 96
INK_TOP, INK_BOT = (10, 12, 20), (16, 20, 31)
WHITE, MUTE = (255, 255, 255), (150, 161, 178)
AQUA, BLUE, VIOLET = (31, 224, 200), (59, 130, 246), (124, 92, 255)

def lerp(a, b, t): return tuple(int(a[i] + (b[i]-a[i])*t) for i in range(3))

def vgrad(top, bot):
    g = Image.new("RGB", (1, H))
    for y in range(H): g.putpixel((0, y), lerp(top, bot, y/(H-1)))
    return g.resize((W, H))

def grad_h(w, h, c1, c2):
    g = Image.new("RGB", (max(1, w), 1))
    for x in range(max(1, w)): g.putpixel((x, 0), lerp(c1, c2, x/max(1, w-1)))
    return g.resize((max(1, w), h))

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

# ---------- text helpers ----------
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
    img = vgrad(INK_TOP, INK_BOT)
    if cover:
        img = glow(img, (W*0.18, H*0.20), 520, VIOLET, 70)
        img = glow(img, (W*0.92, H*0.30), 460, BLUE, 60)
        img = glow(img, (W*0.70, H*0.86), 520, AQUA, 55)
        img = wave(img, H*0.86, 46, AQUA, 5, 55, periods=2.0, phase=0.4)
        img = wave(img, H*0.89, 38, VIOLET, 4, 42, periods=2.4, phase=1.6)
    else:
        img = glow(img, (W*0.90, H*0.08), 420, BLUE, 42)
        img = glow(img, (W*0.05, H*0.96), 460, VIOLET, 40)
        img = wave(img, H*0.945, 26, AQUA, 4, 70, periods=2.2, phase=0.6)
    return img

def kicker(draw, text, y):
    bar = grad_h(54, 8, AQUA, BLUE)
    draw._image.paste(bar, (MARGIN, y+10))
    tracked(draw, (MARGIN+78, y-6), text.upper(), f_bold(31), AQUA, tracking=4)

def ghost_index(img, n):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer); fnt = f_black(300)
    w = d.textlength(str(n), font=fnt)
    d.text((W-MARGIN-w+30, 70), str(n), font=fnt, fill=AQUA+(20,))
    base = img.convert("RGBA"); base.alpha_composite(layer)
    return base.convert("RGB")

def footer(draw, page=None, total=8, swipe=False):
    y = H-86
    draw.text((MARGIN, y), "@vascoyaps", font=f_bold(34), fill=MUTE)
    if swipe:
        f = f_bold(32); wsw = draw.textlength("swipe", font=f)
        draw.text((W-MARGIN-wsw-44, y+1), "swipe", font=f, fill=MUTE)
        ax = W-MARGIN-30
        draw.line([(ax-14, y+18), (ax+8, y+18)], fill=AQUA, width=4)
        draw.line([(ax-2, y+8), (ax+10, y+18)], fill=AQUA, width=4)
        draw.line([(ax-2, y+28), (ax+10, y+18)], fill=AQUA, width=4)
    elif page:
        n, dot, gap = total, 12, 18
        tot = n*dot+(n-1)*gap; x0 = W-MARGIN-tot; cy = y+22
        for i in range(n):
            on = (i == page-1); col = AQUA if on else (60, 68, 82)
            r = dot//2 + (2 if on else 0); cx = x0+i*(dot+gap)+dot//2
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=col)

def _bullets_height(draw, items, max_w, fsize, gap):
    f = f_reg(fsize); total = 0
    for it in items:
        n = max(1, len(wrap(draw, it, f, max_w-46)))
        total += n*int(fsize*1.28) + gap
    return total

def fit_bullets(draw, items, max_w, avail_h):
    """Largest font/gap so all bullets fit in avail_h. Never overflows."""
    for fsize in range(39, 25, -1):
        gap = max(18, int(fsize*0.80))
        if _bullets_height(draw, items, max_w, fsize, gap) <= avail_h:
            return fsize, gap
    return 26, 18

def bullets(draw, items, x, y, max_w, fsize=39, gap=34):
    f = f_reg(fsize)
    for it in items:
        draw.ellipse([x, y+fsize*0.46, x+14, y+fsize*0.46+14], fill=AQUA)
        ty = y
        for ln in wrap(draw, it, f, max_w-46):
            draw.text((x+46, ty), ln, font=f, fill=(214, 221, 230)); ty += int(fsize*1.28)
        y = ty + gap
    return y

# ---------- slides ----------
def cover(c):
    img = background(cover=True); d = ImageDraw.Draw(img)
    kicker(d, c["kicker"], 150)
    f = f_black(120); y = 300
    for ln in c["title_lines"][:-1]:
        d.text((MARGIN, y), ln, font=f, fill=WHITE); y += int(120*1.0)
    key = c["title_lines"][-1]
    kw = int(d.textlength(key, font=f)); gimg = grad_h(kw, 130, AQUA, VIOLET)
    mask = Image.new("L", (kw, 130), 0); ImageDraw.Draw(mask).text((0, -8), key, font=f, fill=255)
    img.paste(gimg, (MARGIN, y+4), mask); y += int(120*1.0)+40
    fs = f_semi(40)
    for ln in wrap(d, c["subtitle"], fs, W-2*MARGIN-40):
        d.text((MARGIN, y), ln, font=fs, fill=(229, 234, 242)); y += int(40*1.36)
    footer(d, swipe=True); return img

def content(card, page):
    img = background(); img = ghost_index(img, card["index"]); d = ImageDraw.Draw(img)
    kicker(d, card["label"], 150)
    fnt, lines, lh = fit_headline(d, card["headline"], W-2*MARGIN, 360)
    y = 250
    for ln in lines: d.text((MARGIN, y), ln, font=fnt, fill=WHITE); y += int(lh)
    y += 38; img.paste(grad_h(180, 6, AQUA, BLUE), (MARGIN, y)); d = ImageDraw.Draw(img); y += 46
    avail = (H - 150) - y  # keep clear of the footer/handle at H-86
    fsize, gap = fit_bullets(d, card["bullets"], W-2*MARGIN, avail)
    bullets(d, card["bullets"], MARGIN, y, W-2*MARGIN, fsize=fsize, gap=gap)
    footer(d, page=page); return img

def cta(c):
    img = background(cover=True); d = ImageDraw.Draw(img)
    kicker(d, c.get("kicker", "THAT'S TODAY IN AI"), 150)
    y = 250
    d.text((MARGIN, y), c.get("line1", "Follow"), font=f_black(104), fill=WHITE)
    key = c.get("handle", "@vascoyaps"); f = f_black(104); kw = int(d.textlength(key, font=f))
    gimg = grad_h(kw, 120, AQUA, VIOLET); mask = Image.new("L", (kw, 120), 0)
    ImageDraw.Draw(mask).text((0, -8), key, font=f, fill=255)
    img.paste(gimg, (MARGIN, y + 104), mask); d = ImageDraw.Draw(img)
    y += 104 + 130
    fs = f_reg(40)
    d.text((MARGIN, y), "AI news, decoded daily.", font=fs, fill=MUTE)
    y += 92

    # social handles, one row each: icon + @handle
    isz = 50; row = 92; tx = MARGIN + 78
    fh = f_semi(40)
    glyphs = {"instagram": "", "tiktok": "", "youtube": ""}
    for plat, _ic, handle in SOCIALS:
        cy = y + 24  # shared centerline for icon + handle
        if plat == "substack":
            draw_substack(d, MARGIN + 2, cy - (isz - 4) / 2, isz - 4)
        else:
            d.text((MARGIN, cy), glyphs[plat], font=f_brand(isz), fill=WHITE, anchor="lm")
        d.text((tx, cy), handle, font=fh, fill=(214, 221, 230), anchor="lm")
        y += row

    y += 20
    pill = "  " + c.get("pill", "Save this  ·  Send it to a friend") + "  "
    fp = f_bold(36); pw = int(d.textlength(pill, font=fp)) + 20; ph = 84
    rad = Image.new("L", (pw, ph), 0); ImageDraw.Draw(rad).rounded_rectangle([0, 0, pw, ph], ph//2, fill=255)
    img.paste(grad_h(pw, ph, AQUA, BLUE), (MARGIN, y), rad); d = ImageDraw.Draw(img)
    d.text((MARGIN + pw/2, y + ph/2), pill.strip(), font=fp, fill=(8, 12, 20), anchor="mm")
    footer(d); return img

def main():
    content_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "content.json")
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "output")
    os.makedirs(out_dir, exist_ok=True)
    data = json.load(open(content_path))
    cover(data["cover"]).save(os.path.join(out_dir, "slide_01.png"))
    page = 2
    for card in data["cards"]:
        content(card, page).save(os.path.join(out_dir, f"slide_{page:02d}.png")); page += 1
    cta(data["cta"]).save(os.path.join(out_dir, f"slide_{page:02d}.png"))
    print(f"Rendered {page} slides to {out_dir}")

if __name__ == "__main__":
    main()
