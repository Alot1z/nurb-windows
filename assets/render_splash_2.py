"""
Render the nurb-windows port mobile splash (assets/nurb-windows-splash-2.png)
and its PDF (assets/nurb-windows-splash-2.pdf) from the Anodized Fillet
philosophy.

A 9:16 vertical composition, not a crop of logo.png. The NURB ribbon flows
down the canvas instead of across it, the mark stacks instead of sitting on
one baseline, and the spec block lands beneath the mark where a phone
thumbnail reads it. Same palette, same two type voices, same fiducial
vocabulary: the brand system is the thing shared, not the layout.

The spec metadata is read from pyproject.toml and git at render time, exactly
as render_logo.py does, so neither mark can advertise a stale release.
"""

import subprocess
import tomllib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def package_version() -> str:
    root = Path(__file__).resolve().parents[1]
    with open(root / "pyproject.toml", "rb") as fh:
        return tomllib.load(fh)["project"]["version"]


def build_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], text=True
    ).strip()

# ---------- canvas ---------------------------------------------------------

W, H = 1080, 1920                             # 9:16 phone canvas
OUT_PNG = Path(__file__).parent / "nurb-windows-splash-2.png"
OUT_PDF = Path(__file__).parent / "nurb-windows-splash-2.pdf"

# ---------- palette (Anodized Fillet, unchanged) ---------------------------

GRAPHITE        = (16, 19, 24)
GRAPHITE_HI     = (28, 34, 42)
DEEP_ANODIZE    = (10, 26, 48)
DEEP_ANODIZE_HI = (22, 48, 84)
MANGANESE       = (224, 96, 32)
MANGANESE_GLOW  = (255, 188, 132)
HAIRLINE        = (130, 158, 192)
HAIRLINE_DIM    = (60, 78, 100)
TYPOGRAPHY      = (220, 226, 234)
TYPOGRAPHY_DIM  = (148, 158, 170)

FONT_DIR = Path(r"C:\Users\jacob\.agents\skills\canvas-design\canvas-fonts")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


# ---------- background -----------------------------------------------------

def build_background() -> Image.Image:
    img = Image.new("RGB", (W, H), GRAPHITE)
    rows = np.linspace(0, 1, H, dtype=np.float64).reshape(H, 1, 1)
    top  = np.array(GRAPHITE_HI,    dtype=np.float64)
    bot  = np.array(DEEP_ANODIZE,   dtype=np.float64)
    mid  = np.array(DEEP_ANODIZE_HI, dtype=np.float64)
    # anodized band sits under the mark zone (upper two thirds of the canvas)
    band = np.exp(-((np.linspace(0, 1, H) - 0.42) ** 2) / 0.05)
    grad = top * (1 - rows) + bot * rows
    grad = grad * (1 - band[..., None]) + mid * band[..., None]
    img.paste(Image.fromarray(grad.astype(np.uint8)))

    d = ImageDraw.Draw(img, "RGBA")
    for x in range(0, W, 24):
        alpha = 24 if (x // 24) % 5 else 70
        d.line([(x, 0), (x, H)], fill=HAIRLINE + (alpha,), width=1)
    for y in range(0, H, 24):
        alpha = 24 if (y // 24) % 5 else 70
        d.line([(0, y), (W, y)], fill=HAIRLINE + (alpha,), width=1)
    # tolerance guide rules bracketing the mark zone
    d.line([(0, 360), (W, 360)], fill=HAIRLINE + (60,), width=1)
    d.line([(0, 1440), (W, 1440)], fill=HAIRLINE + (60,), width=1)
    # fiducials in each corner
    f_size = 26
    for (cx, cy) in [(40, 40), (W - 40, 40), (40, H - 40), (W - 40, H - 40)]:
        d.line([(cx - f_size, cy), (cx + f_size, cy)], fill=HAIRLINE + (180,), width=1)
        d.line([(cx, cy - f_size), (cx, cy + f_size)], fill=HAIRLINE + (180,), width=1)
        d.ellipse([(cx - 4, cy - 4), (cx + 4, cy + 4)], outline=HAIRLINE + (220,), width=1)
    return img


# ---------- the mark: vertical NURB ribbon ---------------------------------

def bezier(t: np.ndarray, p0, p1, p2, p3) -> tuple[np.ndarray, np.ndarray]:
    one = 1 - t
    x = (one**3) * p0[0] + 3 * (one**2) * t * p1[0] + 3 * one * (t**2) * p2[0] + (t**3) * p3[0]
    y = (one**3) * p0[1] + 3 * (one**2) * t * p1[1] + 3 * one * (t**2) * p2[1] + (t**3) * p3[1]
    return x, y


def draw_vertical_ribbon(canvas: Image.Image) -> Image.Image:
    """
    The same NURB ribbon, re-cast for the 9:16 frame: it flows top to bottom
    with a single slow S, wider in the middle where the mark sits, tapering
    toward both ends like an extrusion seen edge-on.
    """
    cx = W / 2
    amp = 210
    # control points run down the canvas, swaying left/right
    p0 = (cx + amp, 300)
    p1 = (cx - amp, 660)
    p2 = (cx + amp, 1050)
    p3 = (cx - amp, 1420)
    off = 84

    t = np.linspace(0, 1, 800)
    ux, uy = bezier(t, p0, p1, p2, p3)
    taper = 0.35 + 0.65 * np.sin(np.pi * t) ** 1.2
    # offset perpendicular to the curve direction so thickness stays even
    dx = np.gradient(ux)
    dy = np.gradient(uy)
    nrm = np.sqrt(dx**2 + dy**2)
    nx = -dy / nrm
    ny = dx / nrm
    lx = ux + nx * off * taper
    ly = uy + ny * off * taper

    polygon = list(zip(np.rint(ux).astype(int), np.rint(uy).astype(int)))
    polygon += list(zip(np.rint(lx[::-1]).astype(int), np.rint(ly[::-1]).astype(int)))

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.polygon(polygon, fill=(34, 58, 96, 255))

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.polygon(polygon, fill=(0, 0, 0, 200))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    canvas.alpha_composite(shadow)

    # bevel along the left edge (the light side)
    bevel = list(zip(np.rint(ux).astype(int) - 16, np.rint(uy).astype(int))) + \
            list(zip(np.rint(ux[::-1]).astype(int) - 2, np.rint(uy[::-1]).astype(int)))
    od.polygon(bevel, fill=(140, 178, 226, 200))

    # manganese calibration point at the lower inflection, like the logo's P2
    idx = int(0.72 * len(t))
    ax, ay = ux[idx], uy[idx]
    od.ellipse([(ax - 8, ay - 8), (ax + 8, ay + 8)], fill=MANGANESE + (255,))
    od.line([(ax, ay), (ax + 120, ay + 70)], fill=MANGANESE + (220,), width=2)
    od.line([(ax + 108, ay + 66), (ax + 138, ay + 78)], fill=MANGANESE + (220,), width=2)

    canvas.alpha_composite(overlay)

    tiny = font("JetBrainsMono-Bold.ttf", 16)
    d = ImageDraw.Draw(canvas, "RGBA")
    for (px, py, label) in [(cx + amp + 40, 292, "P0"), (cx - amp - 70, 1042, "P2"),
                            (cx + amp + 40, 1412, "P3")]:
        d.text((px, py), label, font=tiny, fill=TYPOGRAPHY_DIM + (200,))
    return canvas


# ---------- typography -----------------------------------------------------

def render_typography(canvas: Image.Image) -> Image.Image:
    mark_font = font("BricolageGrotesque-Bold.ttf", 150)
    sub_font  = font("BricolageGrotesque-Bold.ttf", 112)
    mono_font = font("JetBrainsMono-Regular.ttf", 24)
    mono_bold = font("JetBrainsMono-Bold.ttf", 18)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    def textbox(text, fnt):
        bb = d.textbbox((0, 0), text, font=fnt)
        return bb[2] - bb[0], bb[3] - bb[1], bb[0], bb[1]

    # stacked: "nurb-windows" over "port" — the vertical reading
    mw, mh, _, _ = textbox("nurb-windows", mark_font)
    sw, sh, _, _ = textbox("port", sub_font)

    mark_x = (W - mw) // 2
    sub_x  = (W - sw) // 2
    top = 1580                                   # below the ribbon's lower end
    mark_y = top
    sub_y = mark_y + mh + 26

    # shadow pass
    shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_layer)
    sd.text((mark_x + 5, mark_y + 7), "nurb-windows", font=mark_font, fill=(0, 0, 0, 180))
    sd.text((sub_x + 5, sub_y + 7), "port", font=sub_font, fill=(0, 0, 0, 180))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(7))
    canvas.alpha_composite(shadow_layer)

    d.text((mark_x, mark_y), "nurb-windows", font=mark_font, fill=TYPOGRAPHY + (255,))
    d.text((sub_x, sub_y), "port", font=sub_font, fill=MANGANESE + (255,))

    # spec block beneath the mark, mono, centered
    spec_lines = [
        "agentic cad for 3d printing",
        "occt-backed · windows 10/11 x64",
        "signed auto-updates · nsis installer",
    ]
    for i, line in enumerate(spec_lines):
        lw, lh, _, _ = textbox(line, mono_font)
        d.text(((W - lw) // 2, sub_y + sh + 46 + i * (lh + 12)), line,
               font=mono_font, fill=TYPOGRAPHY_DIM + (220,))

    # corner region labels, fiducial style
    d.text((W - 420, H - 44), f"build · {build_sha()} · strict gate ✓",
           font=mono_bold, fill=TYPOGRAPHY_DIM + (190,))
    d.text((40, H - 44), f"channel · nurb-windows · v{package_version()}",
           font=mono_bold, fill=TYPOGRAPHY_DIM + (190,))

    canvas.alpha_composite(overlay)
    return canvas


# ---------- main -----------------------------------------------------------

def main() -> tuple[Path, Path]:
    canvas = build_background().convert("RGBA")
    canvas = draw_vertical_ribbon(canvas)
    canvas = render_typography(canvas)

    vignette = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vignette)
    vd.ellipse([-250, -250, W + 250, H + 250], fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(220))
    darken = Image.new("RGBA", (W, H), (0, 0, 0, 220))
    canvas = Image.composite(canvas, darken, vignette)

    rgb = canvas.convert("RGB")
    rgb.save(OUT_PNG, optimize=True)
    rgb.save(OUT_PDF, "PDF", resolution=144.0)
    return OUT_PNG, OUT_PDF


if __name__ == "__main__":
    png, pdf = main()
    print(f"wrote {png}  ({png.stat().st_size // 1024} KiB)")
    print(f"wrote {pdf}  ({pdf.stat().st_size // 1024} KiB)")
