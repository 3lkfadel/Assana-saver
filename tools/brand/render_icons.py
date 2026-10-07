#!/usr/bin/env python3
"""Render the Infinity Planning raster assets (icons, favicons, social image) from the symbol geometry.

The geometry mirrors docs/brand/logo/symbole-*.svg (viewBox 0 0 347 182).
Usage:
    python3 tools/brand/render_icons.py <out_dir>          # icon set only
    python3 tools/brand/render_icons.py --apps [--font F]  # write every asset of apps/web, admin, space

`--font` points at an Inter TTF (variable font accepted); it is needed for the social image only.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 347, 182
BAND = [(0, 110), (347, 0), (347, 71), (0, 182)]
LEFT = [(0, 0), (172, 56), (0, 140)]
RIGHT = [(347, 182), (175, 126), (347, 40)]
BACKGROUND = (42, 45, 47, 255)  # anthracite #2A2D2F
SYMBOL = (245, 249, 250)  # frost white #F5F9FA
CARMINE = (220, 20, 60)  # #DC143C


def symbol_mask(scale):
    """Alpha mask of the symbol, with the two triangles fading towards the centre."""
    w, h = round(W * scale), round(H * scale)
    pts = lambda poly: [(x * scale, y * scale) for x, y in poly]
    solid = Image.new("L", (w, h), 0)
    ImageDraw.Draw(solid).polygon(pts(BAND), fill=255)
    for poly, start, end in ((LEFT, 0, 172), (RIGHT, 347, 175)):
        tri = Image.new("L", (w, h), 0)
        ImageDraw.Draw(tri).polygon(pts(poly), fill=255)
        ramp = Image.new("L", (w, h), 0)
        for x in range(w):
            t = (x / scale - start) / (end - start)
            v = 255 if t <= 0.27 else max(0, round(255 * (1 - (t - 0.27) / 0.73)))
            ramp.paste(v, (x, 0, x + 1, h))
        solid.paste(255, mask=Image.composite(ramp, Image.new("L", (w, h), 0), tri))
    return solid


def icon(size, padding=0.16, radius=0.22):
    ss = 4  # supersampling
    big = size * ss
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle((0, 0, big - 1, big - 1), radius=round(big * radius), fill=BACKGROUND)
    scale = big * (1 - 2 * padding) / W
    mask = symbol_mask(scale)
    x = (big - mask.width) // 2
    y = (big - mask.height) // 2
    img.paste(Image.new("RGBA", mask.size, SYMBOL + (255,)), (x, y), mask)
    return img.resize((size, size), Image.LANCZOS)


def symbol(width, color):
    """The symbol alone on a transparent background, `width` pixels wide."""
    ss = 4
    mask = symbol_mask(width * ss / W)
    img = Image.new("RGBA", mask.size, color + (0,))
    img.putalpha(mask)
    return img.resize((width, round(width * H / W)), Image.LANCZOS)


def inter(path, size, weight):
    font = ImageFont.truetype(path, size)
    try:
        font.set_variation_by_axes([32, weight])
    except (OSError, ValueError):
        pass  # static font: weight is fixed
    return font


def social_image(font_path, size=(1200, 630)):
    """Open Graph image: carmine symbol and the two-line wordmark on anthracite."""
    img = Image.new("RGBA", size, BACKGROUND)
    mark = symbol(300, CARMINE)
    img.alpha_composite(mark, (150, (size[1] - mark.height) // 2))
    draw = ImageDraw.Draw(img)
    draw.text((500, 315), "Infinity", font=inter(font_path, 96, 700), fill=SYMBOL, anchor="ls")
    draw.text((500, 425), "Planning", font=inter(font_path, 96, 400), fill=SYMBOL, anchor="ls")
    return img


def icon_set(out):
    os.makedirs(out, exist_ok=True)
    for name, size in {
        "favicon-16x16.png": 16,
        "favicon-32x32.png": 32,
        "apple-touch-icon.png": 180,
        "icon-180x180.png": 180,
        "android-chrome-192x192.png": 192,
        "android-chrome-512x512.png": 512,
        "icon-512x512.png": 512,
    }.items():
        icon(size).save(os.path.join(out, name))
    icon(64).save(os.path.join(out, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])


def app_assets(font_path):
    for app in ("web", "admin", "space"):
        fav = f"apps/{app}/app/assets/favicon"
        for name, size in (("favicon-16x16.png", 16), ("favicon-32x32.png", 32), ("apple-touch-icon.png", 180)):
            icon(size).save(os.path.join(fav, name))
        icon(48).save(os.path.join(fav, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
        for size in (192, 512):
            icon(size).save(f"apps/{app}/public/favicon/android-chrome-{size}x{size}.png")
    for size in (180, 512):
        icon(size).save(f"apps/web/app/assets/icons/icon-{size}x{size}.png")
    for size in (192, 348, 512):
        icon(size).save(f"apps/web/public/icons/icon-{size}x{size}.png")
    # Instance "not ready" screen: the symbol alone, then centred on a wider transparent canvas.
    symbol(561, CARMINE).save("apps/web/app/assets/auth/gradient-logo.webp")
    bg = Image.new("RGBA", (1080, 672), (0, 0, 0, 0))
    mark = symbol(640, CARMINE)
    bg.alpha_composite(mark, ((bg.width - mark.width) // 2, (bg.height - mark.height) // 2))
    bg.save("apps/web/app/assets/auth/gradient-bg-logo.webp")
    if font_path:
        social_image(font_path).save("apps/web/app/assets/og-image.png")


def main(argv):
    if argv and argv[0] == "--apps":
        font = argv[argv.index("--font") + 1] if "--font" in argv else None
        app_assets(font)
    else:
        icon_set(argv[0] if argv else "docs/brand/icons")


if __name__ == "__main__":
    main(sys.argv[1:])
