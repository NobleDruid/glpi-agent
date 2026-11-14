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

Coordinates below are for abundantlogic-logo.png (1024x559). The bottom-right corner of that
image has a watermark sparkle, which is deliberately never cropped in.
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
PREV = os.path.join(HERE, "preview")
os.makedirs(PREV, exist_ok=True)

SRC = Image.open(os.path.join(HERE, "abundantlogic-logo.png")).convert("RGB")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

CUBE_BOX = (375, 74, 648, 351)          # bright circuit lines of the cube
TEXT_COLOR = (179, 249, 255)             # wordmark cyan
BG_TOP, BG_BOTTOM = (26, 84, 168), (22, 30, 100)   # logo background gradient
WORD_ABUNDANT = (243, 412, 584, 457)
WORD_LOGIC = (604, 412, 781, 457)


def vgradient(w, h, top, bottom):
    g = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(g)
    for y in range(h):
        t = y / max(h - 1, 1)
        d.line([(0, y), (w, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    return g


def cube_square(pad=0.10):
    """Square crop centred on the cube, including its dark faces."""
    x0, y0, x1, y1 = CUBE_BOX
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + 8   # dark lower face extends a bit below the lines
    side = max(x1 - x0, y1 - y0) * (1 + 2 * pad)
    return SRC.crop((round(cx - side / 2), round(cy - side / 2), round(cx + side / 2), round(cy + side / 2)))


def feather_mask(size, border):
    """Opaque centre fading to transparent edges, so a crop blends into a new background."""
    w, h = size
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle([border, border, w - 1 - border, h - 1 - border], radius=border * 2, fill=255)
    return m.filter(ImageFilter.GaussianBlur(border / 2))


def word_layer(box, height):
    """Extract a word as a clean alpha mask (text brighter than background), recoloured, scaled."""
    crop = SRC.crop(box)
    w, h = crop.size
    alpha = Image.new("L", crop.size)
    cp, ap = crop.load(), alpha.load()
    for y in range(h):
        for x in range(w):
            g = cp[x, y][1]
            ap[x, y] = max(0, min(255, round((g - 70) * 255 / (249 - 70))))
    bb = alpha.getbbox()
    alpha = alpha.crop(bb)
    layer = Image.new("RGBA", alpha.size, TEXT_COLOR + (0,))
    layer.putalpha(alpha)
    scale = height / layer.height
    return layer.resize((max(1, round(layer.width * scale)), height), Image.LANCZOS)


def spaced_text(text, size, color, spacing):
    font = ImageFont.truetype(FONT, size)
    widths = [font.getbbox(c)[2] - font.getbbox(c)[0] for c in text]
    total = sum(widths) + spacing * (len(text) - 1)
    asc, desc = font.getmetrics()
    img = Image.new("RGBA", (total + 2, asc + desc), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 0
    for c, wc in zip(text, widths):
        d.text((x - font.getbbox(c)[0], 0), c, font=font, fill=color)
        x += wc + spacing
    return img.crop(img.getbbox())


# ---------------------------------------------------------------- icons
def icon_image(size):
    tile = cube_square(pad=0.10 if size >= 48 else 0.04).resize((size, size), Image.LANCZOS)
    if size <= 32:   # small sizes: lift contrast so the circuit lines survive downscaling
        from PIL import ImageEnhance
        tile = ImageEnhance.Contrast(tile).enhance(1.25)
        tile = ImageEnhance.Brightness(tile).enhance(1.15)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=max(2, round(size * 0.18)), fill=255)
    out = tile.convert("RGBA")
    out.putalpha(mask)
    return out


def write_ico(path, sizes):
    imgs = [icon_image(s) for s in sorted(sizes, reverse=True)]
    imgs[0].save(path, format="ICO", sizes=[(s, s) for s in sorted(sizes, reverse=True)], append_images=imgs[1:], bitmap_format="bmp")


write_ico(os.path.join(OUT, "glpi-agent.ico"), [16, 24, 32, 48, 96, 256])
write_ico(os.path.join(OUT, "agentexe.ico"), [16, 32, 48, 256])
icon_image(256).save(os.path.join(PREV, "icon-256.png"))
strip = Image.new("RGBA", (16 + 24 + 32 + 48 + 96 + 6 * 10, 96), (255, 255, 255, 255))
x = 5
for s in (16, 24, 32, 48, 96):
    strip.alpha_composite(icon_image(s), (x, 96 - s))
    x += s + 10
strip.save(os.path.join(PREV, "icon-sizes.png"))

# ---------------------------------------------------------------- dialog 493x312
PANEL = 164   # WiX text starts ~180px in; keep the panel left of that
dialog = Image.new("RGB", (493, 312), (255, 255, 255))
panel = vgradient(PANEL, 312, BG_TOP, BG_BOTTOM).convert("RGBA")
cube = cube_square(pad=0.18).resize((150, 150), Image.LANCZOS).convert("RGBA")
cube.putalpha(feather_mask(cube.size, 12))
panel.alpha_composite(cube, ((PANEL - 150) // 2, 22))
abundant = word_layer(WORD_ABUNDANT, 16)
logic = word_layer(WORD_LOGIC, 16)
panel.alpha_composite(abundant, ((PANEL - abundant.width) // 2, 198))
panel.alpha_composite(logic, ((PANEL - logic.width) // 2, 221))
agent = spaced_text("AGENT", 12, (255, 255, 255, 230), 5)
panel.alpha_composite(agent, ((PANEL - agent.width) // 2, 252))
dialog.paste(panel.convert("RGB"), (0, 0))
dialog.save(os.path.join(OUT, "GLPI-Agent_Dialog.bmp"))

# ---------------------------------------------------------------- banner 493x58
banner = Image.new("RGB", (493, 58), (255, 255, 255))
fade_start, fade_end = 300, 420
d = ImageDraw.Draw(banner)
for x in range(fade_start, 493):
    t = min(1.0, (x - fade_start) / (fade_end - fade_start))
    t = t * t * (3 - 2 * t)   # smoothstep
    col = tuple(round(255 + (c - 255) * t) for c in (24, 60, 140))
    d.line([(x, 0), (x, 57)], fill=col)
bcube = cube_square(pad=0.14).resize((54, 54), Image.LANCZOS).convert("RGBA")
bcube.putalpha(feather_mask(bcube.size, 5))
banner_rgba = banner.convert("RGBA")
banner_rgba.alpha_composite(bcube, (493 - 54 - 6, 2))
banner = banner_rgba.convert("RGB")
banner.save(os.path.join(OUT, "GLPI-Agent_Banner.bmp"))

# ---------------------------------------------------------------- previews (with mock installer text)
f_title = ImageFont.truetype(FONT.replace("-Bold", "-Bold"), 15)
f_body = ImageFont.truetype(FONT.replace("-Bold", ""), 11)
m = dialog.copy()
md = ImageDraw.Draw(m)
md.text((180, 20), "Welcome to the Abundant Logic\nAgent 1.21 Setup Wizard", font=f_title, fill=(0, 0, 0))
md.text((180, 80), "The Setup Wizard will install\nAbundant Logic Agent on your computer.", font=f_body, fill=(0, 0, 0))
m.save(os.path.join(PREV, "dialog-mockup.png"))
b = banner.copy()
bd = ImageDraw.Draw(b)
bd.text((14, 8), "Choose Setup Type", font=ImageFont.truetype(FONT, 12), fill=(0, 0, 0))
bd.text((22, 30), "Choose the setup type that best suits your needs", font=f_body, fill=(0, 0, 0))
b.save(os.path.join(PREV, "banner-mockup.png"))
print("generated:", ", ".join(["glpi-agent.ico", "agentexe.ico", "GLPI-Agent_Dialog.bmp", "GLPI-Agent_Banner.bmp"]))
