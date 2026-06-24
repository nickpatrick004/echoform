"""Built-in radial spectrum visualizer.

This module is the first Echoform visualizer plugin. It draws the circular FFT
bars, stationary inner ring, particles, progress bar, and text.
"""
from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Any, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def hex_to_rgb(s: str) -> Tuple[int, int, int]:
    s = s.strip().lstrip("#")
    if len(s) != 6:
        raise ValueError(f"Expected hex color like #ff1493, got {s}")
    return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))  # type: ignore


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_color(a: Tuple[int, int, int], b: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    return tuple(int(lerp(a[i], b[i], t)) for i in range(3))  # type: ignore


def palette(i: int, n: int, left, mid, right) -> Tuple[int, int, int]:
    t = i / max(1, n - 1)
    if t < 0.5:
        return lerp_color(left, mid, t * 2)
    return lerp_color(mid, right, (t - 0.5) * 2)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for p in candidates:
        if p and Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def text_center(draw: ImageDraw.ImageDraw, xy: Tuple[int, int], text: str, fnt, fill, spacing: int = 0) -> None:
    x, y = xy
    bbox = draw.textbbox((0, 0), text, font=fnt, spacing=spacing)
    w = bbox[2] - bbox[0]
    draw.text((x - w / 2, y), text, font=fnt, fill=fill)


def fmt_time(seconds: float) -> str:
    seconds = max(0, int(seconds + 0.5))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def build_state(cfg: Any) -> dict[str, Any]:
    random.seed(1337)
    particles = []
    for _ in range(cfg.particle_count):
        particles.append((
            random.uniform(0, cfg.width),
            random.uniform(0, cfg.height * 0.78),
            random.uniform(-4, 4),
            random.uniform(-1.5, 1.5),
            random.uniform(0, math.tau),
            random.uniform(0.8, 2.2),
            random.uniform(1.0, 3.0),
        ))
    return {"particles": particles}


def draw_frame(base: Image.Image, values: np.ndarray, frame_idx: int, total_frames: int, duration: float, cfg: Any, state: dict[str, Any]) -> Image.Image:
    frame = base.copy().convert("RGBA")
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    glow = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    gd = ImageDraw.Draw(glow)

    left, mid, right = map(hex_to_rgb, [cfg.color_left, cfg.color_mid, cfg.color_right])
    cx, cy = cfg.center_x, cfg.center_y
    n = cfg.bars
    pulse = float(np.mean(values[:max(4, n // 8)]))
    ring_r = float(cfg.inner_radius) if cfg.stationary_inner_ring else float(cfg.inner_radius + pulse * 10)

    # Inner translucent disc for contrast.
    disc = [cx - ring_r + 5, cy - ring_r + 5, cx + ring_r - 5, cy + ring_r - 5]
    d.ellipse(disc, fill=(5, 2, 20, 92), outline=(*mid, 110), width=2)

    if cfg.draw_inner_dots:
        for i in range(n):
            angle = math.radians(cfg.rotation_degrees + 360 * i / n)
            col = palette(i, n, left, mid, right)
            r = ring_r - 18
            x = cx + math.cos(angle) * r
            y = cy + math.sin(angle) * r
            d.ellipse([x-2, y-2, x+2, y+2], fill=(*col, 210))

    for i, v in enumerate(values):
        angle = math.radians(cfg.rotation_degrees + 360 * i / n)
        col = palette(i, n, left, mid, right)
        length = cfg.bar_min + min(1.25, float(v)) * cfg.bar_max
        r0 = ring_r + 8
        r1 = r0 + length
        x0 = cx + math.cos(angle) * r0
        y0 = cy + math.sin(angle) * r0
        x1 = cx + math.cos(angle) * r1
        y1 = cy + math.sin(angle) * r1
        width = 6 if n <= 160 else 4
        gd.line([x0, y0, x1, y1], fill=(*col, 170), width=width + 8)
        d.line([x0, y0, x1, y1], fill=(*col, 235), width=width)

    t = frame_idx / cfg.fps
    for p in state["particles"]:
        x = (p[0] + p[2] * t) % cfg.width
        y = (p[1] + p[3] * t) % cfg.height
        tw = 0.45 + 0.55 * math.sin(t * p[5] + p[4])
        col = palette(int((x / cfg.width) * (n - 1)), n, left, mid, right)
        a = int(70 + 110 * tw)
        s = p[6]
        d.ellipse([x-s, y-s, x+s, y+s], fill=(*col, a))

    glow = glow.filter(ImageFilter.GaussianBlur(11))
    frame.alpha_composite(glow)
    frame.alpha_composite(overlay)

    ui = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    ud = ImageDraw.Draw(ui)
    white = hex_to_rgb(cfg.text_color)
    sub = hex_to_rgb(cfg.subtext_color)
    text_center(ud, (cx, cy - 42), cfg.brand, font(72, True), (*white, 245))
    text_center(ud, (cx, cy + 36), cfg.channel_name.upper(), font(29, False), (*sub, 230))
    text_center(ud, (cx, 855), cfg.title, font(46, True), (*white, 245))
    text_center(ud, (cx, 912), cfg.artist, font(30, False), (*sub, 235))

    progress = frame_idx / max(1, total_frames - 1)
    x0, x1, y = 520, 1400, 970
    ud.line([x0, y, x1, y], fill=(255, 255, 255, 55), width=6)
    ud.line([x0, y, x0 + (x1 - x0) * progress, y], fill=(*sub, 210), width=6)
    knob_x = x0 + (x1 - x0) * progress
    ud.ellipse([knob_x-11, y-11, knob_x+11, y+11], fill=(*sub, 235))
    elapsed = duration * progress
    text_center(ud, (440, y - 16), fmt_time(elapsed), font(24, False), (*white, 220))
    text_center(ud, (1480, y - 16), fmt_time(duration), font(24, False), (*white, 220))

    ui = ui.filter(ImageFilter.GaussianBlur(0.15))
    frame.alpha_composite(ui)
    return frame.convert("RGB")
