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


def _echoform_home() -> Path:
    import os

    env_home = os.environ.get("ECHOFORM_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def _asset_suffix(path: Path) -> Path | None:
    parts = path.parts
    if "assets" not in parts:
        return None
    return Path(*parts[parts.index("assets"):])


def _legacy_theme_fallback(suffix: Path) -> Path | None:
    fallback_map = {
        "assets/themes/neon_valley/theme.json": "assets/themes/blue_gradient/theme.json",
        "assets/themes/neon_valley/background.png": "assets/themes/blue_gradient/blue_gradient_background.png",
    }
    mapped = fallback_map.get(suffix.as_posix())
    if not mapped:
        return None
    candidate = (_echoform_home() / mapped).resolve()
    return candidate if candidate.exists() else None


def resolve_theme_path(base_dir: Path, theme: str) -> Path:
    path = Path(theme).expanduser()
    home = _echoform_home()

    if path.is_absolute():
        if path.exists():
            return path
        suffix = _asset_suffix(path)
        if suffix:
            candidate = (home / suffix).resolve()
            if candidate.exists():
                return candidate
            fallback = _legacy_theme_fallback(suffix)
            if fallback:
                return fallback
        return path

    candidate = base_dir / path
    if candidate.exists():
        return candidate.resolve()

    home_candidate = home / path
    if home_candidate.exists():
        return home_candidate.resolve()

    suffix = _asset_suffix(path)
    if suffix:
        fallback = _legacy_theme_fallback(suffix)
        if fallback:
            return fallback

    return candidate.resolve()


def normalize_theme_config(theme_path: Path, config: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in config.items():
        if value is None:
            continue
        text = str(value)
        if key == "background" and text:
            value_path = Path(text).expanduser()
            if not value_path.is_absolute():
                text = str((theme_path.parent / value_path).resolve())
            elif not value_path.exists():
                # Allow moved repo/app bundles to repair stale absolute asset paths
                # when the GUI sets ECHOFORM_HOME to the active engine root.
                suffix = _asset_suffix(value_path)
                if suffix:
                    candidate = (_echoform_home() / suffix).resolve()
                    if candidate.exists():
                        text = str(candidate)
                    else:
                        fallback = _legacy_theme_fallback(suffix)
                        if fallback:
                            text = str(fallback)
        normalized[str(key)] = text
    return normalized
