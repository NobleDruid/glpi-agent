#!/usr/bin/env python3
"""Generate Abundant Logic Agent installer artwork from the source logo.

Usage (from repo root):  python3 contrib/windows/packaging/branding/make-branding.py
Needs Pillow (Ubuntu: apt install python3-pil).

Writes, in contrib/windows/packaging/ (same filenames the upstream build expects):
  glpi-agent.ico         MSI / Add-Remove Programs icon
  agentexe.ico           icon embedded in glpi-agent.exe
  GLPI-Agent_Banner.bmp  493x58  top banner on installer pages (left side must stay light: black text)
  GLPI-Agent_Dialog.bmp  493x312 welcome/finish page (right side must stay light: black text)
and previews in branding/preview/.

Source: abundantlogic-logo.png (1024x559) = blue circuit cube + black "ABUNDANT LOGIC" on an
off-white background. The cube and wordmark are cut out with real transparency, so they can be
placed on any background. The bottom-right corner of the source has a watermark sparkle, which is
deliberately never cropped in.
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
PREV = os.path.join(HERE, "preview")
os.makedirs(PREV, exist_ok=True)

SRC = Image.open(os.path.join(HERE, "abundantlogic-logo.png")).convert("RGB")
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

CUBE_BOX = (372, 55, 653, 383)        # whole cube incl. anti-aliased edge (measured 375,58-649,379)
WORD_ABUNDANT = (240, 410, 586, 459)
WORD_LOGIC = (602, 410, 784, 459)
BG = (244, 244, 244)                  # source background
BRAND_BLUE = (19, 90, 200)            # for the "AGENT" label
TEXT_DARK = (22, 24, 32)


def cut_out(box, mode):
    """Return an RGBA crop with the off-white background removed.

    mode 'colour': alpha from colour distance to the background, colour un-mixed from it (cube).
    mode 'dark':   alpha from darkness, painted in TEXT_DARK (wordmark).
    """
    crop = SRC.crop(box)
    w, h = crop.size
    out = Image.new("RGBA", crop.size)
    cp, op = crop.load(), out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = cp[x, y]
            if mode == "dark":
                lum = (r * 299 + g * 587 + b * 114) / 1000
                a = max(0.0, min(1.0, (236 - lum) / 200))
                op[x, y] = TEXT_DARK + (round(a * 255),)
            else:
                dist = ((r - BG[0]) ** 2 + (g - BG[1]) ** 2 + (b - BG[2]) ** 2) ** 0.5
                a = max(0.0, min(1.0, (dist - 14) / 70))
                if a <= 0:
                    op[x, y] = (0, 0, 0, 0)
                    continue
                # un-premultiply against the background so edges don't keep a white fringe
                col = tuple(max(0, min(255, round((c - (1 - a) * bc) / a))) for c, bc in zip((r, g, b), BG))
                op[x, y] = col + (round(a * 255),)
    return out.crop(out.getbbox())


CUBE = cut_out(CUBE_BOX, "colour")
ABUNDANT = cut_out(WORD_ABUNDANT, "dark")
LOGIC = cut_out(WORD_LOGIC, "dark")


def fit(img, max_w, max_h):
    s = min(max_w / img.width, max_h / img.height)
    return img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)


def height(img, h):
    return img.resize((max(1, round(img.width * h / img.height)), h), Image.LANCZOS)


def gradient(w, h, top, bottom):
    g = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(g)
    for y in range(h):
        t = y / max(h - 1, 1)
        d.line([(0, y), (w, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    return g


def spaced_text(text, size, color, spacing, font=FONT_BOLD):
    f = ImageFont.truetype(font, size)
    widths = [f.getbbox(c)[2] - f.getbbox(c)[0] for c in text]
    asc, desc = f.getmetrics()
    img = Image.new("RGBA", (sum(widths) + spacing * (len(text) - 1) + 2, asc + desc), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 0
    for c, wc in zip(text, widths):
        d.text((x - f.getbbox(c)[0], 0), c, font=f, fill=color)
        x += wc + spacing
    return img.crop(img.getbbox())


# ---------------------------------------------------------------- icons (transparent background)
def icon_image(size):
    margin = 0 if size <= 24 else max(1, round(size * 0.04))
    cube = fit(CUBE, size - 2 * margin, size - 2 * margin)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(cube, ((size - cube.width) // 2, (size - cube.height) // 2))
    return canvas


def write_ico(path, sizes):
    sizes = sorted(sizes, reverse=True)
    imgs = [icon_image(s) for s in sizes]
    imgs[0].save(path, format="ICO", sizes=[(s, s) for s in sizes], append_images=imgs[1:], bitmap_format="bmp")


write_ico(os.path.join(OUT, "glpi-agent.ico"), [16, 24, 32, 48, 96, 256])
write_ico(os.path.join(OUT, "agentexe.ico"), [16, 32, 48, 256])
icon_image(256).save(os.path.join(PREV, "icon-256.png"))
# preview icons on both a light and a dark background (Windows dark mode)
sizes = (16, 24, 32, 48, 96)
strip = Image.new("RGBA", (sum(sizes) + 10 * (len(sizes) + 1), 2 * 106), (255, 255, 255, 255))
ImageDraw.Draw(strip).rectangle([0, 106, strip.width, 2 * 106], fill=(32, 32, 32, 255))
x = 10
for s in sizes:
    strip.alpha_composite(icon_image(s), (x, 5 + 96 - s))
    strip.alpha_composite(icon_image(s), (x, 106 + 5 + 96 - s))
    x += s + 10
strip.save(os.path.join(PREV, "icon-sizes.png"))

# ---------------------------------------------------------------- dialog 493x312
PANEL = 164   # WiX page text starts ~180px in; keep the panel left of that
dialog = Image.new("RGB", (493, 312), (255, 255, 255))
panel = gradient(PANEL, 312, (247, 249, 253), (226, 234, 248)).convert("RGBA")
cube = fit(CUBE, 120, 138)
panel.alpha_composite(cube, ((PANEL - cube.width) // 2, 34))
ab = height(ABUNDANT, 15)
lo = height(LOGIC, 15)
panel.alpha_composite(ab, ((PANEL - ab.width) // 2, 196))
panel.alpha_composite(lo, ((PANEL - lo.width) // 2, 218))
agent = spaced_text("AGENT", 11, BRAND_BLUE + (255,), 5)
panel.alpha_composite(agent, ((PANEL - agent.width) // 2, 248))
dialog.paste(panel.convert("RGB"), (0, 0))
ImageDraw.Draw(dialog).line([(PANEL, 0), (PANEL, 311)], fill=(205, 214, 230))   # separates panel from page
dialog.save(os.path.join(OUT, "GLPI-Agent_Dialog.bmp"))

# ---------------------------------------------------------------- banner 493x58
banner = Image.new("RGB", (493, 58), (255, 255, 255))
d = ImageDraw.Draw(banner)
fade_start, fade_end, tint = 330, 470, (228, 236, 250)
for x in range(fade_start, 493):
    t = min(1.0, (x - fade_start) / (fade_end - fade_start))
    t = t * t * (3 - 2 * t)
    d.line([(x, 0), (x, 57)], fill=tuple(round(255 + (c - 255) * t) for c in tint))
b = banner.convert("RGBA")
bc = fit(CUBE, 48, 50)
b.alpha_composite(bc, (493 - bc.width - 10, (58 - bc.height) // 2))
banner = b.convert("RGB")
banner.save(os.path.join(OUT, "GLPI-Agent_Banner.bmp"))

# ---------------------------------------------------------------- previews with mock installer text
m = dialog.copy()
md = ImageDraw.Draw(m)
md.text((180, 20), "Welcome to the Abundant Logic\nAgent 1.21 Setup Wizard", font=ImageFont.truetype(FONT_BOLD, 15), fill=(0, 0, 0))
md.text((180, 80), "The Setup Wizard will install\nAbundant Logic Agent on your computer.", font=ImageFont.truetype(FONT, 11), fill=(0, 0, 0))
m.save(os.path.join(PREV, "dialog-mockup.png"))
bm = banner.copy()
bd = ImageDraw.Draw(bm)
bd.text((14, 8), "Choose Setup Type", font=ImageFont.truetype(FONT_BOLD, 12), fill=(0, 0, 0))
bd.text((22, 30), "Choose the setup type that best suits your needs", font=ImageFont.truetype(FONT, 11), fill=(0, 0, 0))
bm.save(os.path.join(PREV, "banner-mockup.png"))
print("generated: glpi-agent.ico, agentexe.ico, GLPI-Agent_Dialog.bmp, GLPI-Agent_Banner.bmp")
