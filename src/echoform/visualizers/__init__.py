"""Visualizer plugin registry for Echoform.

Visualizer modules expose two functions:

- build_state(cfg) -> object
- draw_frame(base, values, frame_idx, total_frames, duration, cfg, state) -> PIL.Image

The engine calls visualizers by name. This keeps the renderer core separate from
visual styles so desktop apps can list/select visualizers without changing the
render pipeline.
"""
from __future__ import annotations

from importlib import import_module
from types import ModuleType

_BUILTINS = {
    "radial_spectrum": "echoform.visualizers.radial_spectrum",
    "radial": "echoform.visualizers.radial_spectrum",
}


def available_visualizers() -> list[str]:
    return sorted(_BUILTINS)


def get_visualizer(name: str) -> ModuleType:
    key = (name or "radial_spectrum").strip().lower()
    module_name = _BUILTINS.get(key)
    if module_name is None:
        raise ValueError(
            f"Unknown visualizer '{name}'. Available visualizers: {', '.join(available_visualizers())}"
        )
    return import_module(module_name)
