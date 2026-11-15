"""Command line for the scaffold: show the stage list, check config, prepare a session folder."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from throwlog import __version__
from throwlog.config import DEFAULT_CONFIG, load_config
from throwlog.paths import MANIFESTS, ensure_session
from throwlog.pipeline import next_unimplemented, stage_names


def _cmd_stages() -> int:
    config = load_config()
    names = stage_names()
    pending = next_unimplemented(Path("."), config)
    pending_at = names.index(pending) if pending else len(names)
    for index, name in enumerate(names):
        if index < pending_at:
            mark = "ready"
        elif index == pending_at:
            mark = "next"
        else:
            mark = "later"
        print(f"{name}\t{mark}")
    return 0


def _cmd_check() -> int:
    config = load_config()
    print(f"throwlog {__version__}")
    print(f"config {DEFAULT_CONFIG}")
    print(f"pose model {config.pose.model} on {config.pose.device}")
    if config.throws.wrist_speed_min is None:
        print("throw threshold: not set")
    manifest = MANIFESTS / "img_0138.yaml"
    if manifest.exists():
        info = yaml.safe_load(manifest.read_text())
        container = info["container"]
        print(
            f"local clip {info['clip_id']}: "
            f"{container['display_width']}x{container['display_height']} "
            f"at {container['nominal_fps']} fps, {container['duration_s']} s, gitignored"
        )
    return 0


def _cmd_session(session_id: str) -> int:
    path = ensure_session(session_id)
    print(path)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="throwlog")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("stages", help="List pipeline stages")
    sub.add_parser("check", help="Load config and report the local clip")
    session = sub.add_parser("session", help="Create a session working folder")
    session.add_argument("session_id")
    args = parser.parse_args()
    if args.command == "stages":
        raise SystemExit(_cmd_stages())
    if args.command == "check":
        raise SystemExit(_cmd_check())
    if args.command == "session":
        raise SystemExit(_cmd_session(args.session_id))
    raise SystemExit(2)


if __name__ == "__main__":
    main()
