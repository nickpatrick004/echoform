# Echoform

Echoform is an open-source audio visualizer engine.

It takes an audio file, renders a circular spectrum visualizer over a themed background, and exports a YouTube-ready MP4 using FFmpeg.

Echoform is intentionally CLI-first. The renderer can be used directly today, and the same engine can later be wrapped by a macOS app, Windows app, or other GUI without rewriting the rendering core.

## What Echoform Does

Input:

```text
MP3 / WAV / M4A / MP4 audio
```

Output:

```text
H.264 + AAC MP4 video
YouTube upload metadata files
```

Core workflow:

```text
Audio file
  -> Echoform config
  -> audio analysis
  -> frame rendering
  -> FFmpeg video export
  -> YouTube sidecar metadata
```

## Features

- Single-song rendering from a config file
- Batch queue rendering from a folder of song configs
- Circular FFT spectrum visualizer
- Stationary inner ring by default
- Configurable bar count, radius, gain, smoothing, colors, and text
- PNG frame rendering to avoid intermediate JPEG artifacts
- H.264 video output
- AAC 320 kbps audio output by default
- Preview mode for faster visual tuning
- YouTube-ready sidecar metadata files
- Apache-2.0 licensed engine

## First-Time Setup on macOS

### 1. Install FFmpeg

```bash
brew install ffmpeg
```

Verify:

```bash
ffmpeg -version
```

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

### 3. Clone the Repository

```bash
git clone https://github.com/nickpatrick004/echoform.git
cd echoform
```

### 4. Create a Virtual Environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Verify that the active environment is using Python 3.12:

```bash
python --version
```

Expected:

```text
Python 3.12.x
```

### 5. Install Echoform

```bash
pip install --upgrade pip
pip install -e .
```

The `-e` means editable install. It creates the `echoform` and `echoform-queue` commands while still allowing you to edit the source code.

### 6. Verify Installation

```bash
echoform --help
echoform-queue --help
```

If both commands show help text, setup is complete.

## Single-Song Render

Use this when you want to render one track.

### 1. Copy the Example Config

```bash
cp config.example.txt config.txt
```

### 2. Put an Audio File in the Repo

Example:

```text
echoform/
├── song.mp3
├── config.txt
└── ...
```

### 3. Edit `config.txt`

Minimum useful config:

```text
audio = song.mp3
background = assets/themes/blue_gradient/blue_gradient_background.png
output = output/my_song.mp4

title = My Song
artist = MTLT
brand = Echoform
channel_name = Audio Visualizer Engine
```

### 4. Render a Preview

```bash
echoform --config config.txt --preview
```

Preview output:

```text
output/my_song_preview.mp4
```

### 5. Render the Full Video

```bash
echoform --config config.txt
```

Full output:

```text
output/my_song.mp4
```

## Batch Queue Rendering

Use this when you want Echoform to process several songs overnight.

The queue system does not replace the engine. It sits above the engine and runs one normal Echoform config at a time.

Recommended folder layout:

```text
batch/
├── Back_To_Basics/
│   ├── Back To Basics.mp3
│   └── config.txt
├── Gonna_Get_It/
│   ├── Gonna Get It.mp3
│   └── config.txt
└── Another_Song/
    ├── Another Song.mp3
    └── config.txt
```

Each song has its own `config.txt`.

Example song config:

```text
audio = Gonna Get It.mp3
background = ../../../assets/themes/blue_gradient/blue_gradient_background.png
output = output/gonna_get_it.mp4

title = Gonna Get It
artist = MTLT
brand = Echoform
channel_name = Music To Listen To

youtube_tags = MTLT,music,visualizer,electronic,echoform
youtube_privacy = private
youtube_made_for_kids = 0
```

### Preview Every Song in a Folder

```bash
echoform-queue --folder batch --preview
```

### Render Every Song in a Folder

```bash
echoform-queue --folder batch
```

### Dry Run Without Rendering

```bash
echoform-queue --folder batch --dry-run
```

### Re-render Existing Outputs

```bash
echoform-queue --folder batch --force
```

### Stop on the First Failure

```bash
echoform-queue --folder batch --stop-on-error
```

By default, the queue keeps going if one song fails. That is useful for overnight renders.

## Batch Output

For each rendered video, Echoform writes YouTube sidecar files next to the MP4.

Example:

```text
Back_To_Basics/output/
├── back_to_basics.mp4
├── back_to_basics.youtube_title.txt
├── back_to_basics.youtube_description.txt
├── back_to_basics.youtube_tags.txt
└── back_to_basics.upload.json
```

The `.upload.json` file is designed for future automation.

Example shape:

```json
{
  "title": "Gonna Get It - MTLT",
  "description": "...",
  "tags": ["MTLT", "music", "visualizer"],
  "category": "Music",
  "privacy": "private",
  "made_for_kids": false,
  "video_file": "output/gonna_get_it.mp4",
  "thumbnail_file": "output/gonna_get_it.thumbnail.png"
}
```

Echoform does not upload directly to YouTube yet. It prepares the files a future uploader, desktop app, or manual upload process can use.

## YouTube Metadata Config Keys

These keys are optional:

```text
youtube_title = 
youtube_description = 
youtube_tags = music,visualizer,echoform
youtube_category = Music
youtube_privacy = private
youtube_made_for_kids = 0
```

If `youtube_title` is empty, Echoform uses:

```text
Title - Artist
```

If `youtube_description` is empty, Echoform generates a simple description from the song title, artist, and channel name.

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

## Audio Notes

Echoform decodes the source audio to temporary WAV files, then encodes the final MP4 audio as AAC.

Default:

```text
audio_bitrate = 320k
```

This avoids unreliable MP3-in-MP4 behavior and keeps preview and full renders on the same audio path.

For best quality, use WAV as the source when available. High-bitrate MP3 is acceptable, but artifacts already present in the MP3 cannot be removed by the renderer.

## Common Problems

### Package requires Python >= 3.10

Check your Python version:

```bash
python --version
```

Create the virtual environment with Python 3.12:

```bash
rm -rf .venv
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

### ffmpeg not found

Install FFmpeg:

```bash
brew install ffmpeg
```

Verify:

```bash
ffmpeg -version
```

### echoform command not found

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Then reinstall:

```bash
pip install -e .
```

Verify:

```bash
echoform --help
```

### echoform-queue found no jobs

Make sure each song folder has a config file named one of:

```text
config.txt
echoform.txt
echoform.config.txt
```

Or specify the config filename:

```bash
echoform-queue --folder batch --config-name my-song-config.txt
```

## Project Layout

```text
echoform/
├── assets/
│   └── themes/
│       └── blue_gradient/
│           └── blue_gradient_background.png
├── examples/
│   ├── config.example.txt
│   └── batch/
│       ├── Back_To_Basics/
│       │   └── config.txt
│       └── Gonna_Get_It/
│           └── config.txt
├── scripts/
├── src/
│   └── echoform/
│       ├── __init__.py
│       ├── __main__.py
│       ├── engine.py
│       ├── metadata.py
│       └── queue.py
├── config.example.txt
├── LICENSE
├── NOTICE
├── pyproject.toml
├── README.md
└── requirements.txt
```

## App Wrapper Direction

The current design keeps the renderer and queue usable from a future GUI.

A macOS app can call the same engine functions or invoke the CLI commands:

```text
SwiftUI App
  -> Echoform queue/job model
  -> Echoform engine
  -> FFmpeg
  -> output files
```

A later Windows app can use the same model.

The key rule is that the engine renders one config. The queue schedules many configs. The app should sit above both.

## Roadmap

Near-term:

- Save reusable `analysis.json`
- Add thumbnail generation
- Add public metadata providers for song pages
- Add lyrics sidecar files
- Improve theme packaging

Later:

- GUI wrapper for macOS
- Windows GUI wrapper
- YouTube upload helper
- Beat detection
- Multiple visualizer modes
- GPU renderer

## License

Licensed under the Apache License, Version 2.0. See `LICENSE`.
