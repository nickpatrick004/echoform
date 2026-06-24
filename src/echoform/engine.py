#!/usr/bin/env python3
"""
Echoform Engine
Python renders the circular spectrum, particles, progress UI, and text.
FFmpeg decodes input audio and encodes the final YouTube-ready MP4.

Usage:
  echoform --config examples/config.example.txt
  echoform --config examples/config.example.txt --preview
  echoform --ask
"""
from __future__ import annotations

import argparse
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, List

from .theme import load_theme_file, normalize_theme_config, resolve_theme_path
from .visualizers import get_visualizer

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance
from tqdm import tqdm


@dataclass
class Config:
    audio: str = "song.wav"
    background: str = "background.png"
    theme: str = ""
    visualizer: str = "radial_spectrum"
    output: str = "output/echoform_visualizer.mp4"
    brand: str = "Echoform"
    channel_name: str = "Audio Visualizer Engine"
    title: str = "Your Track Title"
    artist: str = "Unknown Artist"
    width: int = 1920
    height: int = 1080
    fps: int = 30
    preview_seconds: int = 25
    center_x: int = 960
    center_y: int = 485
    inner_radius: int = 220
    bar_min: int = 3
    bar_max: int = 205
    bars: int = 144
    rotation_degrees: float = -90.0
    color_left: str = "#ff1493"
    color_mid: str = "#b000ff"
    color_right: str = "#00a7ff"
    text_color: str = "#ffffff"
    subtext_color: str = "#ff4fc3"
    sensitivity: float = 0.78
    gain: float = 0.65
    smoothing: float = 0.88
    bass_boost: float = 0.85
    noise_floor: float = 0.04
    attack: float = 0.38
    release: float = 0.08
    particle_count: int = 120
    background_dim: float = 0.08
    video_crf: int = 18
    audio_bitrate: str = "320k"
    audio_mode: str = "aac_high"  # Always AAC-encodes final MP4 audio for reliable playback/YouTube compatibility

    # YouTube/export metadata. These do not affect rendering. They are used by
    # echoform-queue to generate upload-ready sidecar files.
    youtube_title: str = ""
    youtube_description: str = ""
    youtube_tags: str = "music,visualizer,echoform"
    youtube_category: str = "Music"
    youtube_privacy: str = "private"
    youtube_made_for_kids: int = 0

    stationary_inner_ring: int = 1
    draw_inner_dots: int = 0
    frame_format: str = "png"


def parse_config(path: Path) -> Config:
    cfg = Config()
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    raw: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        raw[k.strip()] = v.strip().strip('"').strip("'")

    aliases = {
        "base_radius": "inner_radius",
        "bar_min_height": "bar_min",
        "bar_max_height": "bar_max",
    }

    def apply_value(key: str, value: str, *, source: str) -> None:
        key = aliases.get(key, key)
        if not hasattr(cfg, key):
            print(f"Warning: unknown config key ignored from {source}: {key}")
            return
        old = getattr(cfg, key)
        try:
            if isinstance(old, int):
                setattr(cfg, key, int(value))
            elif isinstance(old, float):
                setattr(cfg, key, float(value))
            else:
                setattr(cfg, key, value)
        except ValueError as exc:
            raise ValueError(f"Invalid value for {key}: {value}") from exc

    # Theme defaults are applied first. The song config then overrides them.
    # This lets a future GUI choose a theme, then tune a single job without
    # modifying the theme file.
    theme_value = raw.get("theme", "").strip()
    if theme_value:
        theme_path = resolve_theme_path(path.parent, theme_value)
        theme_config = normalize_theme_config(theme_path, load_theme_file(theme_path))
        cfg.theme = str(theme_path)
        for key, value in theme_config.items():
            apply_value(key, value, source=f"theme {theme_path}")

    for key, value in raw.items():
        apply_value(key, value, source=str(path))

    return cfg


def ask_config() -> Config:
    cfg = Config()
    print("Echoform setup. Press Enter to keep defaults.")
    for field in ["audio", "background", "output", "brand", "channel_name", "title", "artist"]:
        current = getattr(cfg, field)
        value = input(f"{field} [{current}]: ").strip()
        if value:
            setattr(cfg, field, value)
    return cfg


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("FFmpeg is not installed or not in PATH. Install FFmpeg first.")


def log(message: str) -> None:
    print(message, flush=True)


def run(cmd: List[str]) -> None:
    """Run a subprocess while streaming output promptly to the GUI/terminal."""
    log("$ " + " ".join(str(part) for part in cmd))
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="", flush=True)
    rc = process.wait()
    if rc != 0:
        raise subprocess.CalledProcessError(rc, cmd)


def echoform_home() -> Path:
    """Return the active Echoform root without relying only on GUI env vars.

    The GUI sets ECHOFORM_HOME, but copied commands and direct terminal runs may
    omit it. In that case infer the repo/app root from this installed module:
    <root>/src/echoform/engine.py.
    """
    env_home = os.environ.get("ECHOFORM_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def _asset_suffix(path: Path) -> Path | None:
    parts = path.parts
    if "assets" not in parts:
        return None
    idx = parts.index("assets")
    return Path(*parts[idx:])


def _legacy_asset_fallback(suffix: Path) -> Path | None:
    """Compatibility for old batch configs that refer to removed/renamed themes.

    Early Echoform jobs often point at assets/themes/neon_valley/background.png.
    The GUI starter bundle currently ships only the default blue_gradient theme.
    Rather than fail, map the old background to the bundled default background.
    """
    normalized = suffix.as_posix()
    home = echoform_home()
    fallback_map = {
        "assets/themes/neon_valley/background.png": "assets/themes/blue_gradient/blue_gradient_background.png",
        "assets/themes/neon_valley/theme.json": "assets/themes/blue_gradient/theme.json",
    }
    mapped = fallback_map.get(normalized)
    if mapped:
        candidate = (home / mapped).resolve()
        if candidate.exists():
            return candidate
    return None


def resolve(base: Path, p: str) -> Path:
    """Resolve user/config paths with repo/app-aware fallbacks."""
    path = Path(p).expanduser()
    home = echoform_home()

    if not path.is_absolute():
        candidate = (base / path).resolve()
        if candidate.exists():
            return candidate

        home_candidate = (home / path).resolve()
        if home_candidate.exists():
            return home_candidate

        suffix = _asset_suffix(path)
        if suffix:
            fallback = _legacy_asset_fallback(suffix)
            if fallback:
                return fallback
        return candidate

    if path.exists():
        return path

    suffix = _asset_suffix(path)
    if suffix:
        home_candidate = (home / suffix).resolve()
        if home_candidate.exists():
            return home_candidate
        fallback = _legacy_asset_fallback(suffix)
        if fallback:
            return fallback

    return path


def decode_audio_to_wav(audio_path: Path, wav_path: Path, channels: int = 1, duration: float | None = None) -> None:
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y"]
    if duration is not None:
        cmd += ["-t", f"{duration:.3f}"]
    cmd += ["-i", str(audio_path)]
    cmd += [
        "-vn", "-ac", str(channels), "-ar", "48000", "-sample_fmt", "s16",
        "-af", "aresample=async=1:first_pts=0",
        str(wav_path),
    ]
    run(cmd)


def load_wav_mono(wav_path: Path) -> Tuple[np.ndarray, int]:
    with wave.open(str(wav_path), "rb") as wf:
        sr = wf.getframerate()
        n = wf.getnframes()
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        data = wf.readframes(n)
    if sampwidth != 2:
        raise ValueError("Internal decoded WAV must be 16-bit PCM.")
    audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return audio, sr


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


def build_bins(bars: int, fft_size: int, sr: int) -> List[Tuple[int, int, float]]:
    freqs = np.fft.rfftfreq(fft_size, d=1.0 / sr)
    lo, hi = 35.0, min(16000.0, sr / 2)
    edges = np.geomspace(lo, hi, bars + 1)
    bins = []
    for i in range(bars):
        a = int(np.searchsorted(freqs, edges[i], side="left"))
        b = int(np.searchsorted(freqs, edges[i + 1], side="right"))
        if b <= a:
            b = a + 1
        center_freq = math.sqrt(edges[i] * edges[i+1])
        bins.append((a, min(b, len(freqs)), center_freq))
    return bins


def analyze_frame(audio: np.ndarray, sr: int, frame_idx: int, fps: int, fft_size: int, bins, cfg: Config, norm: float = 1.0) -> np.ndarray:
    center = int(frame_idx * sr / fps)
    start = center - fft_size // 2
    end = start + fft_size
    chunk = np.zeros(fft_size, dtype=np.float32)
    src_start = max(0, start)
    src_end = min(len(audio), end)
    dst_start = src_start - start
    if src_end > src_start:
        chunk[dst_start:dst_start + (src_end - src_start)] = audio[src_start:src_end]
    window = np.hanning(fft_size).astype(np.float32)
    spec = np.abs(np.fft.rfft(chunk * window))
    vals = []
    for a, b, f in bins:
        v = float(np.mean(spec[a:b]))
        # bass emphasis; tapers out by ~200 Hz
        if f < 200:
            v *= cfg.bass_boost
        vals.append(v)
    arr = np.array(vals, dtype=np.float32)
    arr = np.log1p(arr * 120.0)
    arr = arr / max(1e-6, norm)
    arr = (arr - cfg.noise_floor) / max(1e-6, 1.0 - cfg.noise_floor)
    arr = np.clip(arr * cfg.gain * cfg.sensitivity, 0, 1.35)
    return arr


def estimate_normalization(audio: np.ndarray, sr: int, fps: int, fft_size: int, bins, cfg: Config, total_frames: int) -> float:
    sample_count = min(240, max(20, total_frames // 3))
    frame_ids = np.linspace(0, max(0, total_frames - 1), sample_count, dtype=int)
    peaks = []
    for frame_idx in frame_ids:
        center = int(frame_idx * sr / fps)
        start = center - fft_size // 2
        end = start + fft_size
        chunk = np.zeros(fft_size, dtype=np.float32)
        src_start = max(0, start)
        src_end = min(len(audio), end)
        dst_start = src_start - start
        if src_end > src_start:
            chunk[dst_start:dst_start + (src_end - src_start)] = audio[src_start:src_end]
        spec = np.abs(np.fft.rfft(chunk * np.hanning(fft_size).astype(np.float32)))
        vals = []
        for a, b, f in bins:
            v = float(np.mean(spec[a:b]))
            if f < 200:
                v *= cfg.bass_boost
            vals.append(v)
        arr = np.log1p(np.array(vals, dtype=np.float32) * 120.0)
        peaks.append(np.percentile(arr, 95))
    return float(max(1e-6, np.percentile(peaks, 85)))


def draw_visualizer(base: Image.Image, values: np.ndarray, frame_idx: int, total_frames: int, duration: float, cfg: Config, particles) -> Image.Image:
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

    # Optional dotted inner ring. Default is off for a cleaner center.
    if cfg.draw_inner_dots:
        for i in range(n):
            angle = math.radians(cfg.rotation_degrees + 360 * i / n)
            col = palette(i, n, left, mid, right)
            r = ring_r - 18
            x = cx + math.cos(angle) * r
            y = cy + math.sin(angle) * r
            d.ellipse([x-2, y-2, x+2, y+2], fill=(*col, 210))

    # Spectrum bars.
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

    # Particles drifting over the scene.
    t = frame_idx / cfg.fps
    for p in particles:
        x = (p[0] + p[2] * t) % cfg.width
        y = (p[1] + p[3] * t) % cfg.height
        tw = 0.45 + 0.55 * math.sin(t * p[5] + p[4])
        col = palette(int((x / cfg.width) * (n - 1)), n, left, mid, right)
        a = int(70 + 110 * tw)
        s = p[6]
        d.ellipse([x-s, y-s, x+s, y+s], fill=(*col, a))

    # Blurred glow pass.
    glow = glow.filter(ImageFilter.GaussianBlur(11))
    frame.alpha_composite(glow)
    frame.alpha_composite(overlay)

    # UI/text layer.
    ui = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    ud = ImageDraw.Draw(ui)
    white = hex_to_rgb(cfg.text_color)
    sub = hex_to_rgb(cfg.subtext_color)
    text_center(ud, (cx, cy - 42), cfg.brand, font(72, True), (*white, 245))
    text_center(ud, (cx, cy + 36), cfg.channel_name.upper(), font(29, False), (*sub, 230))
    text_center(ud, (cx, 855), cfg.title, font(46, True), (*white, 245))
    text_center(ud, (cx, 912), cfg.artist, font(30, False), (*sub, 235))

    # Progress bar and times.
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


def fmt_time(seconds: float) -> str:
    seconds = max(0, int(seconds + 0.5))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def prepare_background(path: Path, cfg: Config) -> Image.Image:
    img = Image.open(path).convert("RGB")
    img_ratio = img.width / img.height
    target_ratio = cfg.width / cfg.height
    if img_ratio > target_ratio:
        new_h = cfg.height
        new_w = int(new_h * img_ratio)
    else:
        new_w = cfg.width
        new_h = int(new_w / img_ratio)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - cfg.width) // 2
    top = (new_h - cfg.height) // 2
    img = img.crop((left, top, left + cfg.width, top + cfg.height))
    if cfg.background_dim > 0:
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(max(0.1, 1.0 - cfg.background_dim))
    return img


def build_particles(cfg: Config):
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
    return particles


def render(cfg: Config, base_dir: Path, preview: bool) -> Path:
    require_ffmpeg()
    audio_path = resolve(base_dir, cfg.audio)
    bg_path = resolve(base_dir, cfg.background)
    out_path = resolve(base_dir, cfg.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    if not bg_path.exists():
        raise FileNotFoundError(f"Background image not found: {bg_path}")

    with tempfile.TemporaryDirectory(prefix="echoform_") as tmp:
        tmp_path = Path(tmp)
        if preview:
            out_path = out_path.with_name(out_path.stem + "_preview" + out_path.suffix)

        log(f"Resolved audio: {audio_path}")
        log(f"Resolved background: {bg_path}")
        log(f"Output target: {out_path}")
        wav_path = tmp_path / "audio_48k_mono.wav"
        analysis_duration = float(cfg.preview_seconds) if preview else None
        log("Decoding analysis audio...")
        decode_audio_to_wav(audio_path, wav_path, channels=1, duration=analysis_duration)
        log("Loading decoded audio...")
        audio, sr = load_wav_mono(wav_path)
        full_duration = len(audio) / sr
        duration = min(full_duration, float(cfg.preview_seconds)) if preview else full_duration
        total_frames = max(1, int(duration * cfg.fps))
        mux_audio_path = tmp_path / "mux_audio_48k_stereo.wav"
        log("Decoding mux audio...")
        decode_audio_to_wav(audio_path, mux_audio_path, channels=2, duration=duration)

        log(f"Audio duration: {full_duration:.2f}s | Rendering: {duration:.2f}s | Frames: {total_frames}")
        log("Preparing background...")
        base = prepare_background(bg_path, cfg)
        visualizer = get_visualizer(cfg.visualizer)
        visualizer_state = visualizer.build_state(cfg)
        fft_size = 4096
        bins = build_bins(cfg.bars, fft_size, sr)
        log("Estimating visualizer normalization...")
        norm = estimate_normalization(audio, sr, cfg.fps, fft_size, bins, cfg, total_frames)
        log(f"Visualizer normalization: {norm:.4f}")
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()
        smooth = np.zeros(cfg.bars, dtype=np.float32)

        log("Rendering frames...")
        for i in tqdm(range(total_frames), desc="Rendering frames", file=sys.stdout, mininterval=0.5):
            vals = analyze_frame(audio, sr, i, cfg.fps, fft_size, bins, cfg, norm)
            # Separate attack/release makes quiet sections calm while loud hits can still grow.
            coeff = np.where(vals > smooth, cfg.attack, cfg.release).astype(np.float32)
            smooth = smooth + coeff * (vals - smooth)
            smooth = cfg.smoothing * smooth + (1.0 - cfg.smoothing) * vals
            frame = visualizer.draw_frame(base, smooth, i, total_frames, duration, cfg, visualizer_state)
            if cfg.frame_format.lower() == "png":
                frame.save(frames_dir / f"frame_{i:06d}.png", compress_level=3)
            else:
                frame.save(frames_dir / f"frame_{i:06d}.jpg", quality=96, subsampling=0)

        # Always mux from a freshly decoded stereo WAV and encode to AAC.
        # This avoids MP3-in-MP4 compatibility problems and fixes the silent preview/full bug from v4.
        frame_pattern = "frame_%06d.png" if cfg.frame_format.lower() == "png" else "frame_%06d.jpg"
        cmd = [
            "ffmpeg", "-hide_banner", "-nostdin", "-y",
            "-framerate", str(cfg.fps), "-i", str(frames_dir / frame_pattern),
            "-i", str(mux_audio_path),
            "-t", f"{duration:.3f}",
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "slow", "-crf", str(cfg.video_crf),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", cfg.audio_bitrate, "-ar", "48000",
            "-af", "aresample=async=1:first_pts=0",
            "-shortest", "-movflags", "+faststart",
            str(out_path),
        ]
        log("Encoding final video...")
        run(cmd)
        log(f"Created: {out_path}")
        return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Echoform audio visualizer videos.")
    parser.add_argument("--config", default="config.txt", help="Path to config.txt")
    parser.add_argument("--preview", action="store_true", help="Render only preview_seconds")
    parser.add_argument("--ask", action="store_true", help="Prompt for the main values instead of config file")
    args = parser.parse_args()

    try:
        if args.ask:
            cfg = ask_config()
            base_dir = Path.cwd()
        else:
            config_path = Path(args.config).resolve()
            cfg = parse_config(config_path)
            base_dir = config_path.parent
        render(cfg, base_dir, args.preview)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
