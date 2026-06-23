# Echoform

Echoform is an open-source audio visualizer rendering engine. It analyzes a music file, renders a circular spectrum visualizer over a themed background, and exports a YouTube-ready MP4 through FFmpeg.

The engine is intentionally CLI-first. A desktop or mobile app can sit on top of it later without changing the rendering core.

## Status

Early engine prototype. The current renderer is built around a neon circular spectrum theme and a reliable MP4 export path. Expect API and config changes before a stable 1.0 release.

## Features

- MP3, WAV, M4A, and MP4 audio input through FFmpeg
- Circular FFT spectrum renderer
- Stationary inner ring by default
- Configurable bar count, radius, gain, smoothing, colors, and text
- Particle/glow layer
- PNG frame rendering to avoid intermediate JPEG artifacts
- Final H.264 + AAC MP4 output suitable for YouTube
- Preview mode for faster iteration
- Apache-2.0 licensed core

## Requirements

- Python 3.10+
- FFmpeg available on your PATH
- Python packages listed in `requirements.txt`

macOS with Homebrew:

```bash
brew install ffmpeg python
```

Python setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e .
```

## Quick start

1. Copy the example config:

```bash
cp config.example.txt config.txt
```

2. Put your music file in the repo folder.

Example:

```text
song.mp3
```

3. Edit `config.txt`:

```txt
audio = song.mp3
title = Back To Basics
artist = MTLT
brand = MTLT
channel_name = Music To Listen To
```

4. Render a preview:

```bash
echoform --config config.txt --preview
```

5. Render the full video:

```bash
echoform --config config.txt
```

The output defaults to:

```text
output/echoform_visualizer.mp4
```

## Configuration

Echoform currently uses a simple `key = value` config file.

Common options:

```txt
audio = song.mp3
background = assets/themes/neon_valley/background.png
output = output/echoform_visualizer.mp4

brand = Echoform
channel_name = Audio Visualizer Engine
title = Your Track Title
artist = Your Artist Name

inner_radius = 205
bar_min = 2
bar_max = 210
bars = 144

stationary_inner_ring = 1
draw_inner_dots = 0

sensitivity = 0.38
gain = 0.55
smoothing = 0.90
bass_boost = 0.75
```

### Visual tuning

If the visualizer starts too aggressively:

```txt
sensitivity = 0.30
gain = 0.45
bar_min = 1
```

If the bars do not have enough room to grow:

```txt
bar_max = 240
bar_min = 1
```

If the movement is too jumpy:

```txt
smoothing = 0.92
attack = 0.25
release = 0.05
```

If you want the center geometry locked:

```txt
stationary_inner_ring = 1
draw_inner_dots = 0
```

## Audio notes

Echoform decodes the source audio to temporary WAV files, then encodes the final MP4 audio as AAC.

Default:

```txt
audio_bitrate = 320k
```

This avoids unreliable MP3-in-MP4 behavior and keeps preview/full renders on the same audio path.

For best quality, use WAV as the source when available. High-bitrate MP3 is acceptable, but artifacts already present in the MP3 cannot be removed by the renderer.

## Project layout

```text
Echoform/
├── assets/
│   └── themes/
│       └── neon_valley/
│           └── background.png
├── examples/
│   └── config.example.txt
├── scripts/
│   ├── run_preview.sh
│   ├── run_full.sh
│   ├── run_preview.bat
│   └── run_full.bat
├── src/
│   └── echoform/
│       ├── __init__.py
│       ├── __main__.py
│       └── engine.py
├── config.example.txt
├── LICENSE
├── NOTICE
├── pyproject.toml
├── README.md
└── requirements.txt
```

## Roadmap

Near-term:

- Split audio analysis from frame rendering
- Save reusable `analysis.json`
- Add a formal theme system
- Add metadata providers for public song pages
- Add batch rendering
- Add thumbnail generation

Later:

- GPU renderer
- Lyrics overlays
- Beat detection
- Multiple visualizer modes
- GUI wrapper for macOS
- YouTube upload helper

## Open-source engine / proprietary app model

The rendering engine is Apache-2.0 licensed. That allows open-source use, commercial use, and integration into a proprietary app.

A future app could keep its user interface, app-store integration, cloud features, or paid workflow tools proprietary while continuing to use and contribute to the open Echoform engine.

## License

Licensed under the Apache License, Version 2.0. See `LICENSE`.
