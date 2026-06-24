"""Metadata helpers for Echoform batch renders.

This module intentionally avoids the YouTube API. It writes sidecar files that a
future uploader, desktop app, or manual upload workflow can consume.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .engine import Config


def safe_stem(value: str) -> str:
    """Return a filesystem-safe stem while preserving readability."""
    value = value.strip() or "echoform_visualizer"
    value = re.sub(r"[^A-Za-z0-9._ -]+", "", value)
    value = re.sub(r"\s+", "_", value)
    return value.strip("._-") or "echoform_visualizer"


def split_tags(tags: str | Iterable[str]) -> list[str]:
    if isinstance(tags, str):
        raw = re.split(r"[,\n]", tags)
    else:
        raw = list(tags)
    seen: set[str] = set()
    out: list[str] = []
    for item in raw:
        tag = str(item).strip()
        if not tag:
            continue
        key = tag.lower()
        if key not in seen:
            seen.add(key)
            out.append(tag)
    return out


def build_youtube_title(cfg: Config) -> str:
    if cfg.youtube_title.strip():
        return cfg.youtube_title.strip()
    title = cfg.title.strip() or "Untitled Track"
    artist = cfg.artist.strip()
    if artist and artist.lower() not in {"unknown", "unknown artist"}:
        return f"{title} - {artist}"
    return title


def build_youtube_description(cfg: Config) -> str:
    if cfg.youtube_description.strip():
        return cfg.youtube_description.strip()

    lines = [
        f"{cfg.title}",
        f"Artist: {cfg.artist}",
        "",
        f"Visualizer created with Echoform.",
    ]
    if cfg.channel_name.strip():
        lines.append(f"Channel: {cfg.channel_name}")
    lines.extend([
        "",
        "#music #visualizer #echoform",
    ])
    return "\n".join(lines).strip() + "\n"


def write_youtube_sidecars(cfg: Config, config_path: Path, video_path: Path, preview: bool = False) -> dict:
    """Write upload metadata next to the rendered video and return the JSON object."""
    output_dir = video_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = video_path.stem

    title = build_youtube_title(cfg)
    description = build_youtube_description(cfg)
    tags = split_tags(cfg.youtube_tags)

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "preview": bool(preview),
        "source_config": str(config_path),
        "video_file": str(video_path),
        "thumbnail_file": str(output_dir / f"{stem}.thumbnail.png"),
        "title": title,
        "description": description,
        "tags": tags,
        "category": cfg.youtube_category,
        "privacy": cfg.youtube_privacy,
        "made_for_kids": bool(cfg.youtube_made_for_kids),
        "echoform_config": asdict(cfg),
    }

    (output_dir / f"{stem}.youtube_title.txt").write_text(title + "\n", encoding="utf-8")
    (output_dir / f"{stem}.youtube_description.txt").write_text(description, encoding="utf-8")
    (output_dir / f"{stem}.youtube_tags.txt").write_text("\n".join(tags) + "\n", encoding="utf-8")
    (output_dir / f"{stem}.upload.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload
