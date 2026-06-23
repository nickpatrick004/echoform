# Echoform

Echoform is an open-source audio visualizer engine.

Input:

```text
MP3 / WAV / M4A
```

Output:

```text
YouTube-ready MP4 video
```

Echoform analyzes audio, generates a circular spectrum visualizer, renders frames, and builds the final video using FFmpeg.

---

## First-Time Setup (macOS)

### 1. Install FFmpeg

```bash
brew install ffmpeg
```

Verify:

```bash
ffmpeg -version
```

---

### 2. Install Python 3.12

```bash
brew install python@3.12
```

Verify:

```bash
python3.12 --version
```

Expected:

```text
Python 3.12.x
```

---

### 3. Clone the Repository

```bash
git clone https://github.com/nickpatrick004/echoform.git
cd echoform
```

---

### 4. Create a Virtual Environment

```bash
python3.12 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Verify:

```bash
python --version
```

Expected:

```text
Python 3.12.x
```

---

### 5. Install Echoform

```bash
pip install --upgrade pip
pip install -e .
```

The `-e` means **editable install**.

This creates the `echoform` command while still allowing you to edit the source code.

---

### 6. Verify Installation

```bash
echoform --help
```

If you see help text, Echoform is installed correctly.

---

## Your First Render

### 1. Copy a Music File

Place an audio file in the project directory:

```text
echoform/
├── song.mp3
├── config.txt
└── ...
```

---

### 2. Create a Config File

Create or edit `config.txt`:

```text
audio = song.mp3

title = My Song
artist = MTLT

background = assets/themes/default/background.png

output = output/my_song.mp4
```

---

### 3. Render a Preview

```bash
echoform --config config.txt --preview
```

Output:

```text
output/echoform_preview.mp4
```

Preview renders only a short segment and is intended for visual tuning.

---

### 4. Render the Full Video

```bash
echoform --config config.txt
```

Output:

```text
output/my_song.mp4
```

---

## Common Problems

### Package requires Python >= 3.10

You are using an older Python version.

Check:

```bash
python --version
```

Install Python 3.12:

```bash
brew install python@3.12
```

Then recreate the virtual environment:

```bash
rm -rf .venv
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

---

### ffmpeg not found

Install FFmpeg:

```bash
brew install ffmpeg
```

Then verify:

```bash
ffmpeg -version
```

---

### echoform command not found

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Then reinstall Echoform:

```bash
pip install -e .
```

Verify:

```bash
echoform --help
```

---

## Configuration

Echoform currently uses a simple `key = value` config file.

Common options:

```text
audio = song.mp3
background = assets/themes/default/background.png
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

---

## Visual Tuning

If the visualizer starts too aggressively:

```text
sensitivity = 0.30
gain = 0.45
bar_min = 1
```

If the bars do not have enough room to grow:

```text
bar_max = 240
bar_min = 1
```

If the movement is too jumpy:

```text
smoothing = 0.92
attack = 0.25
release = 0.05
```

If you want the center geometry locked:

```text
stationary_inner_ring = 1
draw_inner_dots = 0
```

---

## Audio Notes

Echoform decodes the source audio to temporary WAV files, then encodes the final MP4 audio as AAC.

Default:

```text
audio_bitrate = 320k
```

This avoids unreliable MP3-in-MP4 behavior and keeps preview/full renders on the same audio path.

For best quality, use WAV as the source when available. High-bitrate MP3 is acceptable, but artifacts already present in the MP3 cannot be removed by the renderer.

---

## Project Layout

```text
echoform/
├── assets/
│   └── themes/
│       └── default/
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

---

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

---

## Open-Source Engine / Proprietary App Model

The rendering engine is Apache-2.0 licensed. That allows open-source use, commercial use, and integration into a proprietary app.

A future app could keep its user interface, App Store integration, cloud features, or paid workflow tools proprietary while continuing to use and contribute to the open Echoform engine.

---

## License

Licensed under the Apache License, Version 2.0. See `LICENSE`.
