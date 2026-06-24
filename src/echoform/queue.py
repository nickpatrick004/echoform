"""Batch queue runner for Echoform.

The queue layer intentionally sits above the renderer. Each song keeps its own
config file. The queue discovers those configs, runs the existing engine one job
at a time, and writes YouTube-ready sidecar metadata.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .engine import parse_config, render, resolve
from .metadata import write_youtube_sidecars


DEFAULT_CONFIG_NAMES = ("config.txt", "echoform.txt", "echoform.config.txt")


def discover_configs(folder: Path, config_name: str | None = None) -> list[Path]:
    folder = folder.resolve()
    if not folder.exists():
        raise FileNotFoundError(f"Queue folder not found: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Queue path is not a folder: {folder}")

    if config_name:
        configs = sorted(folder.rglob(config_name))
    else:
        configs = []
        for name in DEFAULT_CONFIG_NAMES:
            configs.extend(folder.rglob(name))
        configs = sorted(set(configs))

    ignored_parts = {".git", ".venv", "venv", "env", "__pycache__", "output", "renders", "frames"}
    return [p for p in configs if not any(part in ignored_parts for part in p.parts)]


def expected_output_path(config_path: Path, preview: bool) -> Path:
    cfg = parse_config(config_path)
    base_dir = config_path.parent
    out = resolve(base_dir, cfg.output)
    if preview:
        out = out.with_name(out.stem + "_preview" + out.suffix)
    return out


def run_queue(
    folder: Path,
    *,
    config_name: str | None = None,
    preview: bool = False,
    force: bool = False,
    dry_run: bool = False,
    stop_on_error: bool = False,
) -> int:
    configs = discover_configs(folder, config_name)
    if not configs:
        print(f"No config files found in {folder}")
        return 1

    report: dict = {
        "schema_version": 1,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "folder": str(folder.resolve()),
        "preview": preview,
        "force": force,
        "dry_run": dry_run,
        "jobs": [],
    }

    failures = 0
    print(f"Found {len(configs)} Echoform job(s).")

    for idx, config_path in enumerate(configs, start=1):
        print(f"\n[{idx}/{len(configs)}] {config_path}")
        job = {
            "config": str(config_path),
            "status": "pending",
            "video_file": None,
            "error": None,
        }
        try:
            cfg = parse_config(config_path)
            out_path = expected_output_path(config_path, preview)
            job["video_file"] = str(out_path)

            if out_path.exists() and not force:
                print(f"Skipping existing output: {out_path}")
                job["status"] = "skipped_existing"
                write_youtube_sidecars(cfg, config_path, out_path, preview=preview)
            elif dry_run:
                print(f"Would render: {out_path}")
                job["status"] = "dry_run"
            else:
                video_path = render(cfg, config_path.parent, preview)
                write_youtube_sidecars(cfg, config_path, video_path, preview=preview)
                job["status"] = "completed"
                job["video_file"] = str(video_path)
        except Exception as exc:
            failures += 1
            job["status"] = "failed"
            job["error"] = str(exc)
            print(f"FAILED: {exc}", file=sys.stderr)
            if stop_on_error:
                report["jobs"].append(job)
                break
        report["jobs"].append(job)

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["failures"] = failures
    report_path = folder.resolve() / "echoform_queue_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nQueue report: {report_path}")
    return 1 if failures else 0


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render every Echoform config in a folder.")
    parser.add_argument("--folder", required=True, help="Folder containing one or more song folders/config files")
    parser.add_argument("--config-name", default=None, help="Only process configs with this filename, e.g. config.txt")
    parser.add_argument("--preview", action="store_true", help="Render previews for every job")
    parser.add_argument("--force", action="store_true", help="Re-render even if output already exists")
    parser.add_argument("--dry-run", action="store_true", help="List discovered jobs without rendering")
    parser.add_argument("--stop-on-error", action="store_true", help="Stop the queue when a job fails")
    args = parser.parse_args(list(argv) if argv is not None else None)

    return run_queue(
        Path(args.folder),
        config_name=args.config_name,
        preview=args.preview,
        force=args.force,
        dry_run=args.dry_run,
        stop_on_error=args.stop_on_error,
    )


if __name__ == "__main__":
    raise SystemExit(main())
