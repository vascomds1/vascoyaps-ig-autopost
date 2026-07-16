#!/usr/bin/env python3
"""
Vasco Yaps daily AI carousel renderer (news + tutorials).
Reads content.json and renders 1080x1350 PNG slides.

Theme: set env CAROUSEL_THEME = "grid" (default), "brand", "dark", or "warm".
"grid" = dark brand cover for the hook, light editorial grid body/outro slides
(high-contrast ink on off-white, white bullet card, teal wave signature mark).
The other themes keep one palette across all slides.
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

def _solid_path():
    import fontawesomefree as fa
    return os.path.join(os.path.dirname(fa.__file__),
                        "static/fontawesomefree/webfonts/fa-solid-900.ttf")
def f_solid(s): return ImageFont.truetype(_solid_path(), s)

# Anton = the brand "punch" display face (tall heavy condensed, ALL-CAPS).
# Matches the PUNCH captions in the Vasco Yaps videos (STYLE.md: punch words in accent, connectors neutral).
# Auto-downloaded on first run if not vendored in fonts/.
FONTS_DIR = os.path.join(HERE, "fonts")
ANTON_PATH = os.path.join(FONTS_DIR, "Anton-Regular.ttf")
ANTON_URL = "https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf"
def _ensure_anton():
    # Use the vendored font if present; otherwise fetch it once (CI has network access).
    if not os.path.exists(ANTON_PATH):
        os.makedirs(FONTS_DIR, exist_ok=True)
        import urllib.request
        urllib.request.urlretrieve(ANTON_URL, ANTON_PATH)
    return ANTON_PATH
def f_anton(s): return ImageFont.truetype(_ensure_anton(), s)

# Connectors stay neutral (white); everything else is a "punch" word rendered in the accent.
CONNECTORS = {"A", "AN", "THE", "AND", "OR", "BUT", "OF", "TO", "IN", "ON", "AT", "BY",
              "FOR", "FROM", "WITH", "AS", "IS", "ARE", "WAS", "WERE", "BE", "IT", "ITS",
              "THAT", "THIS", "THESE", "THOSE", "JUST", "NOW", "SO", "NO", "NOT",
              "YOUR", "MY", "OUR", "WE", "I", "YOU", "ON"}
def _alnum(w): return "".join(ch for ch in w.upper() if ch.isalnum())
def is_punch(w):
    a = _alnum(w)
    return bool(a) and a not in CONNECTORS

def _wrap_words(draw, words, font, max_w):
    lines, cur, w_cur = [], [], 0
    sp = draw.textlength(" ", font=font)
    for w in words:
        ww = draw.textlength(w, font=font)
        add = ww if not cur else w_cur + sp + ww
        if cur and add > max_w:
            lines.append(cur); cur, w_cur = [w], ww
        else:
            cur.append(w); w_cur = add
    if cur: lines.append(cur)
    return lines

def punch_headline(img, x, y, text, max_w, accent, ink, start=130, lh=0.95, mins=58, color=True):
    """Draw an ALL-CAPS Anton headline, wrapped, with punch words in `accent`."""
    d = ImageDraw.Draw(img)
    words = text.upper().split()
    s = start
    while s > mins:
        fnt = f_anton(s)
        if max(d.textlength(w, font=fnt) for w in words) <= max_w:
            break
        s -= 2
    fnt = f_anton(max(s, mins)); sp = d.textlength(" ", font=fnt)
    for line in _wrap_words(d, words, fnt, max_w):
        cx = x
        for w in line:
            col = accent if (color and is_punch(w)) else ink
            d.text((cx, y), w, font=fnt, fill=col)
            cx += d.textlength(w, font=fnt) + sp
        y += int(fnt.size * lh)
    return y

SOCIALS = ["instagram", "tiktok", "youtube", "x-twitter", "substack"]

# ---------- themes ----------
# Brand palette (BRAND.md "wave-*" teal tokens):
#   wave-950 #041E28 (4,30,40)   wave-900 #062A38 (6,42,56)    wave-800 #0A4D68 (10,77,104)
#   wave-700 #0C5D7D (12,93,125) wave-600 #088395 (8,131,149)  wave-500 #05BFDB (5,191,219) accent
#   wave-400 #3DD0E5 (61,208,229) wave-300 #7AE1EF (122,225,239) wave-100 #E0F9FC (224,249,252)
THEMES = {
    "brand": {
        "bg_top": (4, 30, 40), "bg_bot": (8, 58, 78),          # wave-950 -> deep teal
        "ink": (255, 255, 255), "body": (201, 230, 238), "mute": (118, 165, 181),
        "accent": (5, 191, 219),                                # wave-500
        "grad_bar": ((5, 191, 219), (61, 208, 229)),            # wave-500 -> wave-400
        "grad_key": ((61, 208, 229), (5, 191, 219)),            # wave-400 -> wave-500
        "ghost": ((5, 191, 219), 20), "dot_off": (28, 70, 88),
        "pill_grad": ((5, 191, 219), (61, 208, 229)), "pill_text": (4, 30, 40),
        "icon": (255, 255, 255),
        "cover_glows": [(0.18, 0.20, 520, (8, 131, 149), 62), (0.92, 0.30, 460, (5, 191, 219), 46), (0.70, 0.86, 520, (12, 93, 125), 58)],
        "cover_waves": [(0.86, 46, (5, 191, 219), 5, 55, 2.0, 0.4), (0.89, 38, (61, 208, 229), 4, 42, 2.4, 1.6)],
        "content_glows": [(0.90, 0.08, 420, (8, 131, 149), 44), (0.05, 0.96, 460, (12, 93, 125), 40)],
        "content_wave": (0.945, 26, (5, 191, 219), 4, 70, 2.2, 0.6),
    },
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
    # Light editorial body used by the "grid" mode (cover stays on "brand").
    # Ink on off-white for contrast; accent shifts to wave-600 so type stays readable on light.
    "grid_light": {
        "grid": True, "card": True,
        "bg_top": (250, 253, 254), "bg_bot": (228, 244, 248),   # white -> wave-100 tint
        "ink": (4, 24, 32), "body": (43, 72, 84), "mute": (108, 138, 150),
        "accent": (8, 131, 149),                                # wave-600 (readable on light)
        "grad_bar": ((8, 131, 149), (5, 191, 219)),
        "grad_key": ((8, 131, 149), (5, 191, 219)),
        "ghost": ((5, 191, 219), 34), "dot_off": (198, 224, 231),
        "pill_grad": ((5, 191, 219), (61, 208, 229)), "pill_text": (4, 30, 40),
        "icon": (4, 24, 32),
        "grid_line": ((8, 131, 149), 13),
        "content_glows": [(0.88, 0.10, 430, (122, 225, 239), 44), (0.08, 0.94, 470, (61, 208, 229), 26)],
        "cover_glows": [(0.88, 0.10, 430, (122, 225, 239), 44), (0.08, 0.94, 470, (61, 208, 229), 26)],
    },
}

MODE = os.environ.get("CAROUSEL_THEME", "grid")
def _pal(kind):
    """Palette for a slide kind ("cover" or "content"). In grid mode the cover
    keeps the dark brand hook while body/outro slides go light."""
    if MODE == "grid":
        return THEMES["brand"] if kind == "cover" else THEMES["grid_light"]
    return THEMES.get(MODE, THEMES["brand"])
T = _pal("content")

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
def grid_lines(img, step=90):
    col, a = T["grid_line"]
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x in range(step, W, step):
        d.line([(x, 0), (x, H)], fill=col+(a,), width=1)
    for y in range(step, H, step):
        d.line([(0, y), (W, y)], fill=col+(a,), width=1)
    base = img.convert("RGBA"); base.alpha_composite(layer)
    return base.convert("RGB")

def background(cover=False):
    img = vgrad(T["bg_top"], T["bg_bot"])
    glows = T["cover_glows"] if cover else T["content_glows"]
    for rx, ry, r, col, a in glows:
        img = glow(img, (W*rx, H*ry), r, col, a)
    if T.get("grid"):
        return grid_lines(img)
    if cover:
        for y0r, amp, col, wd, a, per, ph in T["cover_waves"]:
            img = wave(img, H*y0r, amp, col, wd, a, per, ph)
    else:
        y0r, amp, col, wd, a, per, ph = T["content_wave"]
        img = wave(img, H*y0r, amp, col, wd, a, per, ph)
    return img

def wavemark(draw, x, y, w=58, amp=8, color=None, width=5, periods=1.5):
    """The Vasco Yaps signature mark: a small teal wave squiggle. Rendered in the
    same spot on EVERY slide (via the kicker) so the profile grid reads as one brand."""
    color = color or T["accent"]
    pts = [(x+i, y + amp*math.sin((i/w)*periods*2*math.pi)) for i in range(0, w+1, 2)]
    draw.line(pts, fill=color, width=width, joint="curve")

def kicker(draw, text, y):
    wavemark(draw, MARGIN, y+14)
    tracked(draw, (MARGIN+78, y-6), text.upper(), f_bold(31), T["accent"], tracking=4)

def panel(img, x0, y0, x1, y1, r=28):
    """White card with a soft shadow and a faint teal border (light slides only)."""
    base = img.convert("RGBA")
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x0+4, y0+12, x1+4, y1+12], r, fill=(8, 60, 76, 40))
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    ly = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ly).rounded_rectangle([x0, y0, x1, y1], r, fill=(255, 255, 255, 255),
                                         outline=(5, 191, 219, 110), width=2)
    base.alpha_composite(ly)
    return base.convert("RGB")

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

# ---------- repo cards (7-repo roundup format) ----------
# GitHub linguist colors for the language bar; anything unknown gets slate.
LANG_COLORS = {
    "Python": "3572A5", "TypeScript": "3178c6", "JavaScript": "f1e05a", "Go": "00ADD8",
    "Rust": "dea584", "C++": "f34b7d", "C": "555555", "C#": "178600", "Shell": "89e051",
    "HTML": "e34c26", "CSS": "663399", "Jupyter Notebook": "DA5B0B", "Ruby": "701516",
    "Java": "b07219", "Kotlin": "A97BFF", "Swift": "F05138", "Dart": "00B4AB",
    "Lua": "000080", "Vue": "41b883", "Svelte": "ff3e00", "PHP": "4F5D95",
    "Dockerfile": "384d54", "Makefile": "427819", "PowerShell": "012456",
    "Markdown": "94a3b8", "MDX": "94a3b8", "Zig": "ec915c", "Elixir": "6e4a7e",
}
def _hexrgb(h): return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def lang_color(name): return _hexrgb(LANG_COLORS.get(name, "94a3b8"))

def fmt_count(n):
    if n >= 1_000_000: s = f"{n/1_000_000:.1f}M"
    elif n >= 1_000:   s = f"{n/1_000:.1f}K"
    else:              return str(n)
    return s.replace(".0", "")

def _circle_avatar(path, size):
    try:
        av = Image.open(path).convert("RGB").resize((size, size))
    except Exception:
        av = Image.new("RGB", (size, size), T["accent"])
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size, size], fill=255)
    return av, mask

def gh_card(img, repo, x0, y0, x1):
    """A clean white GitHub card: avatar, owner/repo, stars + forks, description,
    and a language bar. All numbers come from the GitHub API, never the model."""
    pad, av_sz = 44, 104
    inner = (x1 - pad) - (x0 + pad)
    d0 = ImageDraw.Draw(img)
    fd = f_reg(33)
    desc_lines = wrap(d0, repo.get("desc", ""), fd, inner)[:3]
    desc_h = len(desc_lines) * int(33*1.32)
    langs = repo.get("langs", [])[:4]
    lang_h = (16 + 14 + 34) if langs else 0
    y1 = y0 + pad + av_sz + (26 + desc_h if desc_lines else 0) + (24 + lang_h if langs else 0) + pad
    img = panel(img, x0, y0, x1, y1)
    d = ImageDraw.Draw(img)
    ax, ay = x0 + pad, y0 + pad
    av, mask = _circle_avatar(repo.get("avatar", ""), av_sz)
    img.paste(av, (ax, ay), mask)
    tx = ax + av_sz + 30
    name = repo["full_name"]
    size = 46
    while size > 28 and d.textlength(name, font=f_bold(size)) > (x1 - pad) - tx:
        size -= 2
    d.text((tx, ay + 2), name, font=f_bold(size), fill=T["ink"])
    sy = ay + size + 22
    d.text((tx, sy), "", font=f_solid(30), fill=T["accent"])
    sx = tx + 44
    stars = fmt_count(repo.get("stars", 0))
    d.text((sx, sy - 3), stars, font=f_semi(34), fill=T["ink"])
    fx = sx + d.textlength(stars, font=f_semi(34)) + 44
    d.text((fx, sy), "", font=f_solid(30), fill=T["mute"])
    d.text((fx + 40, sy - 3), fmt_count(repo.get("forks", 0)), font=f_semi(34), fill=T["body"])
    y = ay + av_sz + 26
    for ln in desc_lines:
        d.text((x0 + pad, y), ln, font=fd, fill=T["body"]); y += int(33*1.32)
    if langs:
        y += 24
        bar = Image.new("RGB", (inner, 16), T["dot_off"])
        bx = 0
        for i, (lname, frac) in enumerate(langs):
            wseg = inner - bx if i == len(langs) - 1 else int(inner * frac)
            ImageDraw.Draw(bar).rectangle([bx, 0, bx + wseg, 16], fill=lang_color(lname))
            bx += wseg
        bmask = Image.new("L", (inner, 16), 0)
        ImageDraw.Draw(bmask).rounded_rectangle([0, 0, inner, 16], 8, fill=255)
        img.paste(bar, (x0 + pad, y), bmask)
        y += 16 + 14
        lx = x0 + pad
        fl = f_semi(27)
        for lname, frac in langs:
            d.ellipse([lx, y + 6, lx + 14, y + 20], fill=lang_color(lname))
            label = f"{lname} {int(round(frac*100))}%"
            d.text((lx + 24, y), label, font=fl, fill=T["body"])
            lx += 24 + d.textlength(label, font=fl) + 34
    return img, y1

def repo_slide(card, page, total):
    global T; T = _pal("content")
    img = background(); img = ghost_index(img, card["index"]); d = ImageDraw.Draw(img)
    kicker(d, card["label"], 150)
    y = punch_headline(img, MARGIN, 250, card["headline"], W-2*MARGIN, T["accent"], T["ink"], start=104, lh=0.95, mins=58)
    y += 38; d = ImageDraw.Draw(img)
    fj = f_semi(40)
    for ln in wrap(d, card.get("use", ""), fj, W-2*MARGIN):
        d.text((MARGIN, y), ln, font=fj, fill=T["body"]); y += int(40*1.32)
    y += 40
    img, _ = gh_card(img, card["repo"], MARGIN-28, y, W-MARGIN+28)
    d = ImageDraw.Draw(img)
    footer(d, page=page, total=total); return img

def draw_substack(d, x, y, s, fill):
    bar = s * 0.205
    d.rectangle([x, y, x + s, y + bar], fill=fill)
    d.rectangle([x, y + bar * 1.55, x + s, y + bar * 2.55], fill=fill)
    d.polygon([(x, y + bar * 3.1), (x + s, y + bar * 3.1), (x + s / 2, y + s)], fill=fill)

# ---------- slides ----------
def cover(c):
    global T; T = _pal("cover")
    img = background(cover=True); d = ImageDraw.Draw(img)
    kicker(d, c["kicker"], 150)
    title = " ".join(c["title_lines"])
    y = punch_headline(img, MARGIN, 300, title, W-2*MARGIN, T["accent"], T["ink"], start=140, lh=0.95, mins=72)
    y += 46
    d = ImageDraw.Draw(img); sf = f_semi(40)
    for ln in wrap(d, c["subtitle"], sf, W-2*MARGIN-40):
        d.text((MARGIN, y), ln, font=sf, fill=T["mute"]); y += int(40*1.36)
    footer(d, swipe=True); return img

def content(card, page, total=8):
    global T; T = _pal("content")
    img = background(); img = ghost_index(img, card["index"]); d = ImageDraw.Draw(img)
    kicker(d, card["label"], 150)
    y = punch_headline(img, MARGIN, 250, card["headline"], W-2*MARGIN, T["accent"], T["ink"], start=104, lh=0.95, mins=58)
    y += 56; d = ImageDraw.Draw(img)
    if T.get("card"):
        pad = 46
        avail = (H - 170) - y - 2*pad
        max_w = W - 2*MARGIN
        fsize, gap = fit_bullets(d, card["bullets"], max_w, avail)
        hgt = _bullets_height(d, card["bullets"], max_w, fsize, gap) - gap
        img = panel(img, MARGIN-28, y, W-MARGIN+28, y + hgt + 2*pad)
        d = ImageDraw.Draw(img)
        bullets(d, card["bullets"], MARGIN+18, y+pad, max_w-36, fsize=fsize, gap=gap)
    else:
        avail = (H - 150) - y
        fsize, gap = fit_bullets(d, card["bullets"], W-2*MARGIN, avail)
        bullets(d, card["bullets"], MARGIN, y, W-2*MARGIN, fsize=fsize, gap=gap)
    footer(d, page=page, total=total); return img

def cta(c):
    global T; T = _pal("content")
    img = background(cover=True); d = ImageDraw.Draw(img)
    kicker(d, c.get("kicker", "THAT'S TODAY IN AI"), 150)
    # Save-first outro: big save line, then a question that invites a choice.
    line1 = c.get("line1", "Save this").upper()
    line2 = (c.get("line2") or c.get("handle", "@vascoyaps")).upper()
    size = 118
    while size > 64 and max(d.textlength(ln, font=f_anton(size)) for ln in (line1, line2)) > W-2*MARGIN:
        size -= 4
    fa = f_anton(size); lh = int(size * 0.95)
    y = 250
    d.text((MARGIN, y), line1, font=fa, fill=T["ink"]); y += lh
    d.text((MARGIN, y), line2, font=fa, fill=T["accent"]); y += lh + 48
    sub = c.get("subtitle", "AI news, decoded daily.")
    fs = f_reg(40)
    for ln in wrap(d, sub, fs, W-2*MARGIN):
        d.text((MARGIN, y), ln, font=fs, fill=T["mute"]); y += int(40*1.36)
    y += 26
    q = c.get("question")
    if q:
        fq = f_semi(46)
        for ln in wrap(d, q, fq, W-2*MARGIN):
            d.text((MARGIN, y), ln, font=fq, fill=T["ink"]); y += int(46*1.3)
        y += 44
    else:
        y += 24
    isz = 64; cell = 150; cy = y + isz / 2
    glyphs = {"instagram": "\uf16d", "tiktok": "\ue07b", "youtube": "\uf16a", "x-twitter": "\ue61b"}
    for i, plat in enumerate(SOCIALS):
        cx = MARGIN + i * cell
        if plat == "substack":
            s = isz - 8
            draw_substack(d, cx + (isz - s) / 2, cy - s / 2, s, T["icon"])
        else:
            d.text((cx + isz / 2, cy), glyphs[plat], font=f_brand(isz), fill=T["icon"], anchor="mm")
    y += isz + 56
    pill = "  " + c.get("pill", "Follow @vascoyaps") + "  "
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
    cover(data["cover"]).save(os.path.join(out_dir, "slide_01.jpg"), quality=92, subsampling=0)
    page = 2
    for card in data["cards"]:
        slide_fn = repo_slide if "repo" in card else content
        slide_fn(card, page, total).save(os.path.join(out_dir, f"slide_{page:02d}.jpg"), quality=92, subsampling=0); page += 1
    cta(data["cta"]).save(os.path.join(out_dir, f"slide_{page:02d}.jpg"), quality=92, subsampling=0)
    print(f"Rendered {page} slides to {out_dir} (theme={MODE})")

if __name__ == "__main__":
    main()
