# Echoform

Echoform is an open-source audio visualizer engine. It analyzes a music file, renders a visualizer over a theme background, and exports a YouTube-ready MP4 through FFmpeg.

Echoform is intentionally CLI-first. A macOS or Windows app can later wrap the same engine without changing the rendering core.

## Current Status

Early engine prototype.

The current release includes:

- Single-song rendering through `echoform`
- Batch rendering through `echoform-queue`
- YouTube upload sidecar metadata generation
- A data-only theme system
- A basic visualizer plugin registry
- One built-in visualizer: `radial_spectrum`

Expect API/config changes before a stable 1.0 release.

---

# First-Time Setup

## macOS

Install FFmpeg and Python:

```bash
brew install ffmpeg python@3.12
```

Clone the repo:

```bash
git clone https://github.com/nickpatrick004/echoform.git
cd echoform
```

Run setup:

```bash
./scripts/setup_macos.sh
```

Activate later with:

```bash
source .venv/bin/activate
```

Verify:

```bash
echoform --help
echoform-queue --help
```

## Windows

Install FFmpeg:

```powershell
winget install Gyan.FFmpeg
```

Install Python 3.12 from python.org or through winget.

Clone the repo:

```powershell
git clone https://github.com/nickpatrick004/echoform.git
cd echoform
```

Run setup:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```

Activate later with:

```powershell
.\.venv\Scripts\Activate.ps1
```

Verify:

```powershell
echoform --help
echoform-queue --help
```

---

# Recommended Working Layout

Keep the Echoform source repo separate from your music projects.

```text
Echoform/                 # Git repo: source code only
├── src/
├── assets/
├── scripts/
└── README.md

EchoformProjects/         # User projects: not in Git
├── Back_To_Basics/
├── Gonna_Get_It/
└── ...
```

This keeps `git pull` safe and avoids accidentally committing songs, renders, thumbnails, or private themes.

---

# Single-Song Render

Copy the example config:

```bash
cp config.example.txt config.txt
```

Edit `config.txt`:

```ini
audio = song.mp3
theme = assets/themes/blue_gradient/theme.json
output = output/my_song.mp4

title = My Song
artist = MTLT
brand = Echoform
channel_name = Audio Visualizer Engine
```

Render a preview:

```bash
echoform --config config.txt --preview
```

Render the full video:

```bash
echoform --config config.txt
```

---

# Batch Rendering

A batch folder contains one folder per song. Each song folder has its own `config.txt`.

```text
EchoformProjects/
├── Back_To_Basics/
│   ├── song.mp3
│   └── config.txt
└── Gonna_Get_It/
    ├── song.mp3
    └── config.txt
```

Example song config:

```ini
audio = song.mp3
theme = /absolute/path/to/Echoform/assets/themes/blue_gradient/theme.json
output = output/Back_To_Basics.mp4

title = Back To Basics
artist = MTLT
brand = MTLT
channel_name = Music To Listen To
```

Preview all jobs:

```bash
echoform-queue --folder ~/EchoformProjects --preview
```

Render all jobs:

```bash
echoform-queue --folder ~/EchoformProjects
```

Skip behavior:

- Existing outputs are skipped by default.
- Use `--force` to re-render.
- Use `--dry-run` to list jobs without rendering.
- Use `--stop-on-error` to halt on the first failed job.

```bash
echoform-queue --folder ~/EchoformProjects --dry-run
echoform-queue --folder ~/EchoformProjects --force
```

---

# YouTube Sidecar Output

After each render, Echoform writes upload-ready metadata next to the video:

```text
output/
├── My_Song.mp4
├── My_Song.youtube_title.txt
├── My_Song.youtube_description.txt
├── My_Song.youtube_tags.txt
└── My_Song.upload.json
```

The JSON file is designed for a future YouTube uploader or desktop app.

---

# Theme System

Themes are data-only. They define default visual settings such as background, colors, and text colors.

Example:

```text
assets/themes/blue_gradient/
├── theme.json
└── blue_gradient_background.png
```

Example `theme.json`:

```json
{
  "name": "Blue Gradient",
  "description": "A simple neutral default theme for Echoform.",
  "config": {
    "background": "blue_gradient_background.png",
    "visualizer": "radial_spectrum",
    "color_left": "#5cc8ff",
    "color_mid": "#7a5cff",
    "color_right": "#c45cff",
    "text_color": "#ffffff",
    "subtext_color": "#7fd8ff",
    "stationary_inner_ring": "1",
    "draw_inner_dots": "0"
  }
}
```

A song config can use a theme:

```ini
theme = assets/themes/blue_gradient/theme.json
```

Song configs override theme defaults. This lets users pick a theme, then tune a single render without editing the theme.

Private channel themes should live outside the public repo.

---

# Visualizer Plugins

Visualizer plugins define how audio analysis is drawn.

Built-in visualizers:

```text
radial_spectrum
radial
```

Select one in config:

```ini
visualizer = radial_spectrum
```

The engine loads visualizers through `src/echoform/visualizers/__init__.py`.

A visualizer module provides:

```python
def build_state(cfg):
    ...


def draw_frame(base, values, frame_idx, total_frames, duration, cfg, state):
    ...
```

This separation allows future visualizers without rewriting the audio pipeline or batch queue.

Possible future visualizers:

- radial spectrum
- horizontal bars
- waveform tunnel
- oscilloscope
- lyric-reactive visualizer
- particle field
- album-art ring

---

# Configuration Reference

Common options:

```ini
audio = song.mp3
theme = assets/themes/blue_gradient/theme.json
visualizer = radial_spectrum
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

# Audio Notes

Echoform decodes source audio to temporary WAV files, then encodes the final MP4 audio as AAC.

Default:

```ini
audio_bitrate = 320k
```

WAV is best when available. High-bitrate MP3 is acceptable, but artifacts already present in the MP3 cannot be removed by Echoform.

---

# Git Hygiene

Do not commit generated files or local project data.

Recommended `.gitignore` entries:

```gitignore
.venv/
.DS_Store
output/
frames/
batch/
analysis/
renders/
thumbnails/
*.wav
*.mp3
*.m4a
*.mp4
*.mov
```

---

# Roadmap

Near-term:

- Keep user projects outside the repo
- Expand theme schema
- Add more visualizer plugins
- Save reusable `analysis.json`
- Add thumbnail generation
- Add metadata providers for public song pages
- Improve queue resume/reporting

Later:

- macOS GUI wrapper
- Windows GUI wrapper
- YouTube upload helper
- Lyrics overlays
- Beat detection
- GPU renderer

---

# License

Licensed under the Apache License, Version 2.0. See `LICENSE`.
