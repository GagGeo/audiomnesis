"""Rebuild the app icon and header mark from the brand SVG.

Usage (needs pillow in the venv: .venv/bin/pip install pillow):
    1. Render the SVG full-bleed — qlmanage honors the svg width/height
       attributes, so they must be bumped to 1024 first:
         sed 's/width="128" height="128"/width="1024" height="1024"/' \
             assets/audiomnesis-mark-sage.svg > /tmp/mark1024.svg
         qlmanage -t -s 1024 -o /tmp /tmp/mark1024.svg
    2. .venv/bin/python app_src/make_icon.py /tmp/mark1024.svg.png
    3. iconutil -c icns /tmp/A.iconset -o Audiomnesis.app/Contents/Resources/Audiomnesis.icns
       cp /tmp/mark.png assets/mark.png
       codesign --force --deep -s - Audiomnesis.app

qlmanage paints white behind the tile's rounded corners; this script cuts
them back to transparency (the tile radius is rx=26 on a 100-unit viewBox).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def main(src_png: str) -> None:
    src = Path(src_png)
    img = Image.open(src).convert("RGBA")
    w, h = img.size
    radius = round(26 / 100 * w)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1],
                                           radius=radius, fill=255)
    img.putalpha(mask)

    out = src.parent
    iconset = out / "A.iconset"
    iconset.mkdir(exist_ok=True)
    for s in (16, 32, 128, 256, 512):
        img.resize((s, s), Image.LANCZOS).save(iconset / f"icon_{s}x{s}.png")
        img.resize((s * 2, s * 2), Image.LANCZOS).save(
            iconset / f"icon_{s}x{s}@2x.png")
    img.resize((112, 112), Image.LANCZOS).save(out / "mark.png")
    print(f"wrote {iconset} and {out / 'mark.png'}")


if __name__ == "__main__":
    main(sys.argv[1])
