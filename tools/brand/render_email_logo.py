#!/usr/bin/env python3
"""Render the Infinity Planning lockup (symbol + two-line wordmark) as PNG for e-mails.

E-mail clients do not render SVG, so the API templates use these PNGs.
Needs Pillow, plus fontTools and brotli when reading the Inter woff2 shipped with
@fontsource-variable/inter (pass --font to use an Inter TTF instead).
Usage: python3 tools/brand/render_email_logo.py [--font Inter.ttf] [--out apps/api/plane/static/emails]
"""

import argparse
import glob
import io
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_icons import symbol_mask  # noqa: E402

SYMBOL_HEIGHT = 182  # height of the symbol's viewBox (docs/brand/logo/symbole-*.svg)
ANTHRACITE = (42, 45, 47)
CARMINE = (220, 20, 60)
FROST_WHITE = (245, 249, 250)
INTER_WOFF2 = "node_modules/.pnpm/@fontsource-variable+inter@*/node_modules/@fontsource-variable/inter/files/inter-latin-wght-normal.woff2"


def font_source(path):
    if path:
        return path
    paths = sorted(glob.glob(INTER_WOFF2))
    if not paths:
        sys.exit("Inter introuvable : lancez `pnpm install` à la racine du dépôt ou passez --font.")
    from fontTools.ttLib import TTFont

    font = TTFont(paths[-1])
    font.flavor = None
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


def inter(source, size, weight):
    font = ImageFont.truetype(io.BytesIO(source) if isinstance(source, bytes) else source, size)
    axes = [a["name"] if isinstance(a["name"], str) else a["name"].decode() for a in font.get_variation_axes()]
    # Optical size at its maximum (display), weight as asked.
    font.set_variation_by_axes([32 if "opsz" in name.lower() or "optical" in name.lower() else weight for name in axes])
    return font


def lockup(source, text_color, symbol_color, height=112):
    """A transparent PNG `height` px tall: the symbol, then "Infinity" (bold) over "Planning" (regular)."""
    pad = round(height * 0.08)
    mask = symbol_mask((height - 2 * pad) * 0.62 / SYMBOL_HEIGHT)
    size = round(height * 0.36)
    bold, regular = inter(source, size, 700), inter(source, size, 400)
    gap = round(height * 0.18)
    text_w = round(max(bold.getlength("Infinity"), regular.getlength("Planning")))
    width = pad + mask.width + gap + text_w + pad
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    img.paste(Image.new("RGBA", mask.size, symbol_color + (255,)), (pad, (height - mask.height) // 2), mask)
    draw = ImageDraw.Draw(img)
    x = pad + mask.width + gap
    draw.text((x, height * 0.47), "Infinity", font=bold, fill=text_color + (255,), anchor="ls")
    draw.text((x, height * 0.86), "Planning", font=regular, fill=text_color + (255,), anchor="ls")
    return img


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--font", help="Inter TTF (variable); default: the woff2 from node_modules")
    parser.add_argument("--out", default="apps/api/plane/static/emails")
    args = parser.parse_args()
    source = font_source(args.font)
    os.makedirs(args.out, exist_ok=True)
    # Rendered at 2x the displayed size for high-density screens.
    lockup(source, ANTHRACITE, CARMINE).save(os.path.join(args.out, "infinity-planning-logo.png"), optimize=True)
    lockup(source, FROST_WHITE, CARMINE).save(os.path.join(args.out, "infinity-planning-logo-white.png"), optimize=True)


if __name__ == "__main__":
    main()
