"""
Render the nurb-windows port logo (assets/logo.png) from the Anodized Fillet
philosophy.

The output mirrors the existing ASCII block at the top of README.md in visual
weight: a centered horizontal strip measured to roughly the same on-screen
footprint, with the same chrome around it (badge row, figure row). No element
is decorative; every component is load-bearing.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------- canvas ---------------------------------------------------------

W, H = 1600, 480                              # horizontal hero strip
OUT = Path(__file__).parent / "logo.png"

# ---------- palette (Anodized Fillet) --------------------------------------

GRAPHITE       = (16, 19, 24)                # near-black machined feel
GRAPHITE_HI    = (28, 34, 42)                # top of gradient
DEEP_ANODIZE   = (10, 26, 48)                # recess of die-cast chassis
DEEP_ANODIZE_HI= (22, 48, 84)                # highlight tint (still dark)
MANGANESE      = (224, 96, 32)               # single accent (calibration sticker)
MANGANESE_GLOW = (255, 188, 132)             # accent in highlight state
HAIRLINE       = (130, 158, 192)             # reference grid
HAIRLINE_DIM   = (60, 78, 100)               # grid farther from focal point
TYPOGRAPHY     = (220, 226, 234)             # primary type
TYPOGRAPHY_DIM = (148, 158, 170)             # secondary type

FONT_DIR       = Path(r"C:\Users\jacob\.agents\skills\canvas-design\canvas-fonts")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


# ---------- background: graphite -> deep anodize gradient + grid -----------

def build_background() -> Image.Image:
    img = Image.new("RGB", (W, H), GRAPHITE)
    # vertical gradient via numpy
    rows = np.linspace(0, 1, H, dtype=np.float64).reshape(H, 1, 1)
    top  = np.array(GRAPHITE_HI,    dtype=np.float64)
    bot  = np.array(DEEP_ANODIZE,   dtype=np.float64)
    mid  = np.array(DEEP_ANODIZE_HI,dtype=np.float64)
    # bend the gradient slightly to put the anodized color under the mark
    band = np.exp(-((np.linspace(0, 1, H) - 0.65) ** 2) / 0.04)
    grad = top * (1 - rows) + bot * rows
    grad = grad * (1 - band[..., None]) + mid * band[..., None]
    img.paste(Image.fromarray(grad.astype(np.uint8)))

    # horizontal CAD reference grid
    d = ImageDraw.Draw(img, "RGBA")
    for x in range(0, W, 24):
        alpha = 24 if (x // 24) % 5 else 70
        d.line([(x, 0), (x, H)], fill=HAIRLINE + (alpha,), width=1)
    for y in range(0, H, 24):
        alpha = 24 if (y // 24) % 5 else 70
        d.line([(0, y), (W, y)], fill=HAIRLINE + (alpha,), width=1)
    # focus-band horizontal guide rules, the way a CAD plate denotes tolerance
    d.line([(0, H // 2 - 84), (W, H // 2 - 84)], fill=HAIRLINE + (60,), width=1)
    d.line([(0, H // 2 + 84), (W, H // 2 + 84)], fill=HAIRLINE + (60,), width=1)
    # fiducials in each corner (registration marks)
    f_size = 22
    for (cx, cy) in [(40, 40), (W - 40, 40), (40, H - 40), (W - 40, H - 40)]:
        d.line([(cx - f_size, cy), (cx + f_size, cy)], fill=HAIRLINE + (180,), width=1)
        d.line([(cx, cy - f_size), (cx, cy + f_size)], fill=HAIRLINE + (180,), width=1)
        d.ellipse([(cx - 4, cy - 4), (cx + 4, cy + 4)], outline=HAIRLINE + (220,), width=1)

    return img


# ---------- the mark: a NURB ribbon, drawn procedurally with a bevel -------

def bezier(t: np.ndarray, p0, p1, p2, p3) -> tuple[np.ndarray, np.ndarray]:
    """Cubic bezier in 2D."""
    one = 1 - t
    x = (one**3) * p0[0] + 3 * (one**2) * t * p1[0] + 3 * one * (t**2) * p2[0] + (t**3) * p3[0]
    y = (one**3) * p0[1] + 3 * (one**2) * t * p1[1] + 3 * one * (t**2) * p2[1] + (t**3) * p3[1]
    return x, y


def draw_nurb_ribbon(canvas: Image.Image) -> Image.Image:
    """
    Draw a NURB-style ribbon: two offset cubic bes flowing right to left,
    filled with an anodized gradient, beveled by an outer shadow and an
    inner specular highlight.
    """
    # two parallel bezier curves forming a ribbon
    cy = H / 2
    amp = 110
    p0  = (160, cy + amp)
    p1  = (560, cy - amp)
    p2  = (1040, cy + amp)
    p3  = (1440, cy - amp)
    off = 70  # ribbon thickness

    t = np.linspace(0, 1, 800)
    # upper edge
    ux, uy = bezier(t, p0, p1, p2, p3)
    # lower edge = translate upper edge downward by `off` in canvas Y, with a
    # slight parametric taper toward both ends so the ribbon reads as
    # extruded, not as a flat ribbon between two curves
    taper = 0.35 + 0.65 * np.sin(np.pi * t) ** 1.2
    lx, ly = ux, uy + off * taper

    # build a fillable polygon and tint it via mask
    polygon = list(zip(np.rint(ux).astype(int), np.rint(np.minimum(uy, ly)).astype(int)))
    polygon += list(zip(np.rint(lx[::-1]).astype(int), np.rint(np.maximum(uy[::-1], ly[::-1]).astype(int))))

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    # base body — deep anodized
    od.polygon(polygon, fill=(34, 58, 96, 255))

    # outer drop shadow (GaussianBlur) — render to dedicated layer
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.polygon(polygon, fill=(0, 0, 0, 200))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    canvas.alpha_composite(shadow)

    # bevel highlights along the top edge — narrower polygon 14 px above
    bevel_top = list(zip(np.rint(ux).astype(int), (np.rint(uy) - 14).astype(int))) + \
                list(zip(np.rint(ux[::-1]).astype(int), (np.rint(uy[::-1]) - 2).astype(int)))
    od.polygon(bevel_top, fill=(140, 178, 226, 210))

    # accent callout: a tiny MANGANESE reference point on the apex of the curve
    apex_x, apex_y = 800, cy - amp + 6
    od.ellipse([(apex_x - 6, apex_y - 6), (apex_x + 6, apex_y + 6)], fill=MANGANESE + (255,))
    od.line([(apex_x, apex_y), (apex_x + 90, apex_y - 60)], fill=MANGANESE + (220,), width=1)
    od.line([(apex_x + 80, apex_y - 55), (apex_x + 110, apex_y - 65)],
            fill=MANGANESE + (220,), width=1)

    canvas.alpha_composite(overlay)

    # tiny mono tick labels along the curve — engineering-ese, sparse
    tiny = font("JetBrainsMono-Bold.ttf", 14)
    d = ImageDraw.Draw(canvas, "RGBA")
    for (px, py, label) in [(280, cy + amp + 38, "P0"), (800, cy - amp - 22, "P2"),
                            (1320, cy + amp + 38, "P3")]:
        d.text((px, py), label, font=tiny, fill=TYPOGRAPHY_DIM + (200,))
    return canvas


# ---------- typography -----------------------------------------------------

def render_typography(canvas: Image.Image) -> Image.Image:
    # mark: nurb-windows port
    mark_font  = font("BricolageGrotesque-Bold.ttf", 132)
    sub_font   = font("BricolageGrotesque-Bold.ttf", 30)
    mono_font  = font("JetBrainsMono-Regular.ttf", 18)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    # We render type with a hand-built soft drop-shadow via two passes.
    # The text sits cleanly above the ribbon's apex (which is y ≈ cy - amp).
    mark = "nurb-windows"
    sub  = "port"
    # measure
    def textbox(text, fnt):
        bb = d.textbbox((0, 0), text, font=fnt)
        return bb[2] - bb[0], bb[3] - bb[1], bb[0], bb[1]

    mw, mh, _, _ = textbox(mark, mark_font)
    sw, sh, _, _ = textbox(sub,  font("BricolageGrotesque-Bold.ttf", 96))

    # Total mark block width:
    gap = 36
    block_w = mw + gap + sw
    x0 = (W - block_w) // 2
    y0 = (H - max(mh, sh)) // 2 - 6  # nudge slightly above the rule lines
    mark_y = y0 + (sh - mh) // 2
    sub_x  = x0 + mw + gap
    sub_y  = y0

    # shadow pass (slight downward offset, blurred)
    shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_layer)
    sd.text((x0 + 4, mark_y + 6), mark, font=mark_font, fill=(0, 0, 0, 180))
    sd.text((sub_x + 4, sub_y + 6), sub,  font=font("BricolageGrotesque-Bold.ttf", 96),
            fill=(0, 0, 0, 180))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(6))
    canvas.alpha_composite(shadow_layer)

    # mark: white with a manganese accent period / slash
    d.text((x0, mark_y), mark, font=mark_font, fill=TYPOGRAPHY + (255,))
    d.text((sub_x, sub_y), sub,
           font=font("BricolageGrotesque-Bold.ttf", 96),
           fill=MANGANESE + (255,))

    # tiny spec line, mono, centered below the mark block, dim
    spec_line = "agentic cad · occt-backed · windows 10/11 x64 · v0.20.1"
    sw_spec, sh_spec, _, _ = textbox(spec_line, mono_font)
    sx = (W - sw_spec) // 2
    sy = y0 + max(mh, sh) + 26
    d.text((sx, sy), spec_line, font=mono_font, fill=TYPOGRAPHY_DIM + (220,))

    # right-corner region label (fiducial-style)
    mono_small = font("JetBrainsMono-Bold.ttf", 13)
    d.text((W - 360, H - 28), "build · 240b736 · strict gate ✓",
           font=mono_small, fill=TYPOGRAPHY_DIM + (190,))
    d.text((40, H - 28), "channel · nurb-windows · signed",
           font=mono_small, fill=TYPOGRAPHY_DIM + (190,))

    canvas.alpha_composite(overlay)
    return canvas


# ---------- main -----------------------------------------------------------

def main() -> Path:
    canvas = build_background().convert("RGBA")
    canvas = draw_nurb_ribbon(canvas)
    canvas = render_typography(canvas)

    # final pass: faint vignette to seat everything
    vignette = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vignette)
    vd.ellipse([-200, -200, W + 200, H + 200], fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(180))
    darken = Image.new("RGBA", (W, H), (0, 0, 0, 220))
    canvas = Image.composite(canvas, darken, vignette)

    canvas.convert("RGB").save(OUT, optimize=True)
    return OUT


if __name__ == "__main__":
    p = main()
    print(f"wrote {p}  ({p.stat().st_size // 1024} KiB)")
