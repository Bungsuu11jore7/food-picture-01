#!/usr/bin/env python3
"""food-picture-01 entry: "The Golden Melt Burger".

A program that paints one mouth-watering cheeseburger, pixel by pixel,
with the Python standard library only, and writes it to /output/entry.png.

The picture: a tall juicy cheeseburger as the hero - glossy golden sesame
top bun, melted orange cheese dripping down the sides, a thick seared
patty, fresh wavy lettuce and a glossy tomato slice - sitting on a warm
wooden board, with a small red carton of golden fries behind it for
diner colour and depth, all in warm glowing light on a dark wooden table.

Deterministic: every shape comes from fixed coordinates and integer
math; there is no randomness, no clock, no network. The PNG encoder is
pure stdlib (zlib + struct), so two runs write byte-identical files.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
# Backdrop and table.
GLOW_TOP = (255, 214, 148)
GLOW_MID = (238, 168, 96)
GLOW_LOW = (150, 88, 48)
TABLE = (96, 60, 32)
TABLE_DARK = (70, 44, 22)
TABLE_LINE = (58, 36, 18)
BOARD = (182, 128, 68)
BOARD_LIGHT = (204, 152, 88)
BOARD_RIM = (138, 92, 46)
SHADOW = (40, 20, 8)
# Fries carton.
CARTON = (198, 42, 34)
CARTON_DARK = (160, 30, 24)
CARTON_BAND = (250, 240, 225)
FRY = (246, 198, 88)
FRY_EDGE = (214, 158, 54)
FRY_TIP = (232, 172, 66)
# Burger.
BUN_TOP = (242, 178, 88)
BUN_MID = (216, 146, 58)
BUN_LOW = (190, 122, 44)
BUN_BOTTOM = (222, 156, 66)
SEED = (252, 228, 158)
BUN_SHINE = (255, 226, 160)
LETTUCE = (96, 172, 62)
LETTUCE_LIGHT = (132, 198, 86)
LETTUCE_DARK = (62, 128, 42)
TOMATO = (216, 54, 40)
TOMATO_LIGHT = (242, 96, 64)
CHEESE = (255, 158, 26)
CHEESE_LIGHT = (255, 192, 64)
CHEESE_DARK = (232, 128, 14)
PATTY = (96, 54, 28)
PATTY_DARK = (68, 38, 18)
PATTY_LIGHT = (146, 88, 46)
SEAR = (52, 28, 14)
STEAM = (255, 244, 224)


def mix(a, b, t):
    """Blend two RGB colours; t=0 gives a, t=1 gives b."""
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


class Surface:
    """An RGB picture backed by one bytearray; every shape clips to it."""

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def run(self, y, x0, x1, rgb, alpha=1.0):
        """Paint one horizontal run on row y (clipped to the picture)."""
        if y < 0 or y >= self.h:
            return
        x0 = max(0, x0)
        x1 = min(self.w - 1, x1)
        if x1 < x0:
            return
        base = (y * self.w + x0) * 3
        n = x1 - x0 + 1
        r, g, b = rgb
        if alpha >= 1.0:
            self.px[base:base + n * 3] = bytes((r, g, b)) * n
        else:
            inv = 1.0 - alpha
            for i in range(n):
                o = base + i * 3
                self.px[o] = int(r * alpha + self.px[o] * inv)
                self.px[o + 1] = int(g * alpha + self.px[o + 1] * inv)
                self.px[o + 2] = int(b * alpha + self.px[o + 2] * inv)

    def v_grad(self, y0, y1, top, bottom):
        """Vertical linear gradient between two colours."""
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            t = (y - y0) / max(1, y1 - y0)
            self.run(y, 0, self.w - 1, mix(top, bottom, t))

    def disc(self, cx, cy, r, rgb, alpha=1.0):
        """A filled circle."""
        for y in range(cy - r, cy + r + 1):
            dy = y - cy
            rest = r * r - dy * dy
            if rest < 0:
                continue
            dx = int(math.sqrt(rest))
            self.run(y, cx - dx, cx + dx, rgb, alpha)

    def oval(self, cx, cy, rx, ry, rgb, alpha=1.0):
        """A filled ellipse."""
        for y in range(cy - ry, cy + ry + 1):
            dy = (y - cy) / ry
            rest = 1.0 - dy * dy
            if rest < 0:
                continue
            dx = int(rx * math.sqrt(rest))
            self.run(y, cx - dx, cx + dx, rgb, alpha)

    def dome(self, cx, cy, rx, ry, top, bottom):
        """The upper half of an ellipse, shaded top-to-bottom."""
        for y in range(cy - ry, cy + 1):
            dy = (y - cy) / ry
            rest = 1.0 - dy * dy
            if rest < 0:
                continue
            dx = int(rx * math.sqrt(rest))
            t = (y - (cy - ry)) / max(1, ry)
            self.run(y, cx - dx, cx + dx, mix(top, bottom, t))

    def bowl(self, cx, cy, rx, ry, top, bottom):
        """The lower half of an ellipse, shaded top-to-bottom."""
        for y in range(cy, cy + ry + 1):
            dy = (y - cy) / ry
            rest = 1.0 - dy * dy
            if rest < 0:
                continue
            dx = int(rx * math.sqrt(rest))
            t = (y - cy) / max(1, ry)
            self.run(y, cx - dx, cx + dx, mix(top, bottom, t))

    def tilted_oval(self, cx, cy, rx, ry, deg, rgb, alpha=1.0, steps=28):
        """An ellipse rotated by deg degrees, filled via a polygon."""
        pts = []
        a = math.radians(deg)
        ca, sa = math.cos(a), math.sin(a)
        for i in range(steps):
            t = 2 * math.pi * i / steps
            x = rx * math.cos(t)
            y = ry * math.sin(t)
            pts.append((cx + int(x * ca - y * sa),
                        cy + int(x * sa + y * ca)))
        self.poly(pts, rgb, alpha)

    def poly(self, pts, rgb, alpha=1.0):
        """Scanline fill of a simple polygon."""
        if not pts:
            return
        ys = [p[1] for p in pts]
        y0 = max(0, min(ys))
        y1 = min(self.h - 1, max(ys))
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x0, yy0 = pts[i]
                x1, yy1 = pts[(i + 1) % n]
                if (yy0 <= y < yy1) or (yy1 <= y < yy0):
                    if yy1 != yy0:
                        xs.append(x0 + (y - yy0) * (x1 - x0) / (yy1 - yy0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.run(y, int(math.ceil(xs[i])),
                         int(math.floor(xs[i + 1])), rgb, alpha)

    def seg(self, x0, y0, x1, y1, width, rgb, alpha=1.0):
        """A thick segment, drawn as discs along its length."""
        length = math.hypot(x1 - x0, y1 - y0)
        steps = max(1, int(length / max(1, width // 3)))
        r = width // 2
        for i in range(steps + 1):
            t = i / steps
            self.disc(int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t),
                      r, rgb, alpha)

    def stick(self, x, y0, y1, w, rgb, edge):
        """A vertical rounded stick (a fry): edge outline, bright core."""
        r = w // 2
        for y in range(y0, y1 + 1):
            self.run(y, x - r, x + r, edge)
            self.run(y, x - r + 3, x + r - 3, rgb)
        self.disc(x, y0 + r, r, edge)
        self.disc(x, y0 + r, r - 3, FRY_TIP)

    def radial_glow(self, cx, cy, r, rgb, peak):
        """A soft pool of light with a smooth radial falloff (no hard edge)."""
        r2 = r * r
        for y in range(max(0, cy - r), min(self.h, cy + r + 1)):
            dy = y - cy
            dy2 = dy * dy
            if dy2 >= r2:
                continue
            dx = int(math.sqrt(r2 - dy2))
            x0 = max(0, cx - dx)
            x1 = min(self.w - 1, cx + dx)
            base = (y * self.w + x0) * 3
            for x in range(x0, x1 + 1):
                ddx = x - cx
                a = peak * (1.0 - (ddx * ddx + dy2) / r2)
                if a <= 0.004:
                    continue
                o = base + (x - x0) * 3
                inv = 1.0 - a
                self.px[o] = int(rgb[0] * a + self.px[o] * inv)
                self.px[o + 1] = int(rgb[1] * a + self.px[o + 1] * inv)
                self.px[o + 2] = int(rgb[2] * a + self.px[o + 2] * inv)

    def vignette(self, strength=0.26):
        """Darken the corners smoothly; strength 0 leaves the centre alone."""
        cx, cy = self.w // 2, self.h // 2
        maxd = float(cx * cx + cy * cy)
        for y in range(self.h):
            dy = y - cy
            row = y * self.w * 3
            for x in range(self.w):
                ddx = x - cx
                d2 = (ddx * ddx + dy * dy) / maxd
                if d2 > 0.42:
                    a = strength * (d2 - 0.42) / 0.58
                    o = row + x * 3
                    inv = 1.0 - a
                    self.px[o] = int(self.px[o] * inv)
                    self.px[o + 1] = int(self.px[o + 1] * inv)
                    self.px[o + 2] = int(self.px[o + 2] * inv)

    def drip(self, x, y0, y1, w, rgb):
        """A cheese drip hanging down: a rounded column with a bulb tip."""
        r = w // 2
        for y in range(y0, y1 + 1):
            self.run(y, x - r, x + r, rgb)
        self.disc(x, y1, r + 1, rgb)
        self.disc(x, y1 + 1, r - 3, CHEESE_LIGHT)


# ---------------------------------------------------------------- scene
def paint_backdrop(s):
    """Warm glowing wall behind the food, fading to deep amber."""
    s.v_grad(0, 560, GLOW_TOP, GLOW_MID)
    s.v_grad(560, 1023, GLOW_MID, GLOW_LOW)
    # Soft pools of light: one big warm halo behind the burger, one
    # smaller glow upper left so the light feels like a diner lamp.
    s.radial_glow(512, 430, 340, (255, 236, 190), 0.30)
    s.radial_glow(180, 180, 170, (255, 238, 195), 0.22)
    # A faint diagonal sunbeam across the upper right.
    s.poly([(700, 0), (830, 0), (1024, 420), (1024, 620)],
           (255, 240, 190), alpha=0.07)


def paint_table(s):
    """Dark wooden table along the bottom of the frame."""
    s.v_grad(800, 1023, TABLE, TABLE_DARK)
    # Plank seams and a few grain streaks.
    for y in (852, 912, 972):
        s.run(y, 0, 1023, TABLE_LINE)
        s.run(y + 1, 0, 1023, TABLE_LINE)
    for (gx, gy, glen) in [(120, 830, 220), (700, 880, 260), (300, 940, 200),
                           (820, 990, 180), (60, 1000, 150), (560, 830, 130)]:
        s.run(gy, gx, gx + glen, TABLE_DARK)
    # Warm light catching the table's top edge.
    s.run(800, 0, 1023, (150, 100, 56))
    s.run(801, 0, 1023, (128, 84, 46))


def paint_board(s):
    """Round wooden serving board the burger sits on."""
    # Soft contact shadow first, then the board itself.
    s.oval(512, 906, 430, 46, SHADOW, alpha=0.35)
    s.oval(512, 862, 412, 80, BOARD_RIM)
    s.oval(512, 858, 396, 70, BOARD)
    s.oval(512, 854, 368, 58, BOARD_LIGHT)
    # One faint grain ring so the board reads as wood, not a plate.
    s.oval(512, 852, 300, 44, BOARD, alpha=0.28)


def paint_fries(s):
    """Red carton of golden fries peeking out behind the burger."""
    # Fries first: tall golden sticks fanning slightly.
    fries = [(668, 168, 26), (700, 138, 26), (734, 152, 26),
             (768, 128, 28), (800, 148, 26), (832, 132, 26),
             (862, 160, 24), (892, 182, 24)]
    for (fx, top, w) in fries:
        s.stick(fx, top, 330, w, FRY, FRY_EDGE)
        # A darker edge on the leaning side so sticks separate.
        s.run(top + 40, fx - w // 2, fx - w // 2 + 2, FRY_EDGE)
    # Carton: a trapezoid, wider at the top, with a white band.
    s.poly([(640, 252), (912, 252), (884, 452), (668, 452)], CARTON)
    s.poly([(640, 252), (912, 252), (906, 296), (646, 296)], CARTON_DARK)
    s.poly([(652, 306), (900, 306), (894, 330), (658, 330)], CARTON_BAND)
    # Carton shading: darker on the right fold.
    s.poly([(860, 252), (912, 252), (884, 452), (838, 452)],
           CARTON_DARK, alpha=0.45)
    # A few fries leaning out of the carton front, for depth.
    s.stick(700, 300, 400, 22, FRY, FRY_EDGE)
    s.stick(836, 296, 392, 22, FRY, FRY_EDGE)


def paint_burger(s):
    """The hero: a tall cheeseburger, bottom bun to sesame top bun."""
    # ---- bottom bun (golden, sitting on the board) ----
    s.bowl(512, 742, 292, 92, BUN_BOTTOM, (172, 106, 38))
    s.oval(512, 742, 292, 14, BUN_BOTTOM)
    # Toasted darker crescent along the bun's lower edge; its top colour
    # matches the bun's own shade at that height so no hard line shows.
    s.bowl(512, 762, 272, 62, (206, 140, 56), (148, 86, 28))

    # ---- patty: thick, dark, seared, slightly wider than the buns ----
    s.oval(512, 700, 318, 52, PATTY)
    s.oval(512, 692, 318, 40, PATTY)
    # Charred top edge catching the light.
    s.oval(512, 688, 306, 30, PATTY_LIGHT, alpha=0.55)
    s.oval(512, 700, 318, 52, PATTY_DARK, alpha=0.25)
    # Sear speckles, fixed positions.
    for (sx, sy, sr) in [(300, 690, 7), (380, 712, 6), (470, 686, 8),
                         (560, 716, 6), (650, 690, 7), (730, 708, 6),
                         (420, 726, 5), (610, 728, 5), (340, 722, 5)]:
        s.disc(sx, sy, sr, SEAR)

    # ---- cheese: molten orange, dripping over the patty ----
    s.oval(512, 648, 306, 40, CHEESE)
    s.oval(512, 640, 300, 30, CHEESE_LIGHT, alpha=0.6)
    # Drips of different lengths down the patty's front, slimmer now so
    # they read as melted cheese, not yellow bars.
    for (dx, dy, dw) in [(252, 738, 28), (352, 718, 26), (470, 746, 30),
                         (592, 722, 26), (700, 736, 28), (786, 708, 24)]:
        s.drip(dx, 660, dy, dw, CHEESE)
    # A glossy highlight stripe across the cheese layer.
    s.seg(300, 632, 720, 632, 7, CHEESE_LIGHT, alpha=0.5)

    # ---- tomato: glossy red slice peeking out ----
    s.oval(512, 614, 284, 34, TOMATO)
    s.oval(512, 608, 278, 26, TOMATO_LIGHT, alpha=0.5)
    s.seg(280, 602, 420, 598, 6, (255, 150, 120), alpha=0.5)

    # ---- lettuce: fresh wavy green leaves ----
    # Dark under-layer first, then bright frilly edge on top.
    for k in range(15):
        x = 216 + k * 43
        wave = int(14 * math.sin(k * 1.1))
        s.disc(x, 588 + wave, 34, LETTUCE_DARK)
    for k in range(15):
        x = 216 + k * 43
        wave = int(14 * math.sin(k * 1.1))
        s.disc(x, 578 + wave, 30, LETTUCE)
        s.disc(x, 572 + wave, 15, LETTUCE_LIGHT, alpha=0.45)
    # A leaf tip curling out on the left and right.
    s.tilted_oval(196, 596, 46, 16, -28, LETTUCE_LIGHT)
    s.tilted_oval(828, 592, 46, 16, 24, LETTUCE)

    # ---- top bun: tall golden dome with sesame seeds ----
    # A slightly larger, lighter dome drawn first, offset up-right, so a
    # thin warm rim of light stays visible along the top-right edge.
    s.dome(516, 574, 314, 206, (255, 208, 128), (240, 180, 100))
    s.dome(512, 578, 312, 204, BUN_TOP, BUN_LOW)
    # Warm light pooling on the dome's upper left, soft-edged.
    s.radial_glow(410, 448, 175, BUN_SHINE, 0.36)
    # Soft shadow where the dome meets the lettuce.
    s.oval(512, 574, 300, 18, (120, 66, 22), alpha=0.35)
    # Sesame seeds, scattered on the dome, tilted every which way.
    seeds = [(380, 440, -18), (470, 408, 12), (560, 420, -8),
             (640, 452, 20), (340, 500, 8), (430, 480, -24),
             (520, 468, 6), (610, 496, -14), (700, 508, 16),
             (390, 540, -10), (480, 532, 18), (580, 540, -6),
             (660, 556, 10), (300, 552, 22), (730, 556, -20)]
    for (sx, sy, ang) in seeds:
        s.tilted_oval(sx, sy, 13, 7, ang, SEED)
        s.tilted_oval(sx, sy - 1, 10, 5, ang, (255, 240, 185))

    # ---- steam: two faint wisps rising off the hot bun ----
    for bx, phase in [(430, 0.0), (600, 1.4)]:
        prev = None
        for i in range(24):
            t = i / 23
            x = bx + int(16 * math.sin(t * 5.2 + phase))
            y = 372 - int(t * 92)
            if prev is not None:
                s.seg(prev[0], prev[1], x, y, 9, STEAM, alpha=0.14)
            prev = (x, y)

    # ---- crumbs and seeds scattered on the board ----
    for (cx, cy, cr, col) in [(250, 880, 4, SEED), (790, 892, 4, SEED),
                              (300, 912, 3, BUN_LOW), (740, 918, 3, BUN_LOW),
                              (180, 900, 3, LETTUCE), (850, 884, 3, TOMATO)]:
        s.disc(cx, cy, cr, col)


def paint_vignette(s):
    """Darken the corners smoothly so the eye stays on the burger."""
    s.vignette(0.26)


def draw():
    s = Surface(W, H)
    paint_backdrop(s)
    paint_table(s)
    paint_board(s)
    paint_fries(s)
    paint_burger(s)
    paint_vignette(s)
    return s


# ---------------------------------------------------------------- PNG out
def encode_png(path, surf):
    """Write the surface as an RGB PNG (filter none, zlib level 6)."""
    w, h = surf.w, surf.h
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)  # filter type: none
        raw += surf.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 6)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", comp) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out_dir = (os.environ.get("MAKEFUN_OUTPUT_DIR")
               or os.environ.get("OUTPUT_DIR") or "/output")
    os.makedirs(out_dir, exist_ok=True)
    surf = draw()
    path = os.path.join(out_dir, "entry.png")
    size = encode_png(path, surf)
    if size > 1024 * 1024:
        raise SystemExit(f"entry.png too large: {size} bytes (limit 1048576)")
    print(f"Wrote {path} ({size} bytes, {W}x{H})")


if __name__ == "__main__":
    main()
