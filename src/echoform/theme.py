"""Theme loading helpers for Echoform.

Themes are intentionally data-only. A theme may define background, colors, text
colors, and visual defaults, while visualizers define how audio is drawn.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_theme_file(theme_path: Path) -> dict[str, Any]:
    if not theme_path.exists():
        raise FileNotFoundError(f"Theme file not found: {theme_path}")
    if theme_path.suffix.lower() != ".json":
        raise ValueError(f"Theme file must be JSON: {theme_path}")
    data = json.loads(theme_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Theme file must contain a JSON object: {theme_path}")
    config = data.get("config", data)
    if not isinstance(config, dict):
        raise ValueError(f"Theme config must be a JSON object: {theme_path}")
    return dict(config)


def resolve_theme_path(base_dir: Path, theme: str) -> Path:
    path = Path(theme)
    if path.is_absolute():
        return path
    candidate = base_dir / path
    if candidate.exists():
        return candidate.resolve()
    # Useful when configs are stored in project folders outside the repo and
    # refer to repo-relative assets through ECHOFORM_HOME.
    # Example: ECHOFORM_HOME=/path/to/echoform theme=assets/themes/default/theme.json
    import os

    home = os.environ.get("ECHOFORM_HOME")
    if home:
        home_candidate = Path(home) / path
        if home_candidate.exists():
            return home_candidate.resolve()
    return candidate.resolve()


def normalize_theme_config(theme_path: Path, config: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in config.items():
        if value is None:
            continue
        text = str(value)
        if key == "background" and text and not Path(text).is_absolute():
            text = str((theme_path.parent / text).resolve())
        normalized[str(key)] = text
    return normalized
