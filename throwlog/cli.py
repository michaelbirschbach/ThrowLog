"""Command line for the scaffold: show the stage list, check config, prepare a session folder."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from throwlog import __version__
from throwlog.config import DEFAULT_CONFIG, load_config
from throwlog.identity import run as run_identity
from throwlog.ingest import run as run_ingest
from throwlog.paths import MANIFESTS, ensure_session
from throwlog.pipeline import next_unimplemented, stage_names
from throwlog.pose import run as run_pose
from throwlog.throws import run as run_throws
from throwlog.track import run as run_track


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


def _cmd_ingest(session_id: str) -> int:
    folder = ensure_session(session_id)
    run_ingest(folder, load_config())
    print(folder / "ingest.json")
    return 0


def _cmd_run(session_id: str) -> int:
    folder = ensure_session(session_id)
    config = load_config()
    if not (folder / "ingest.json").is_file():
        run_ingest(folder, config)
    run_track(folder, config)
    run_pose(folder, config)
    run_throws(folder, config)
    run_identity(folder, config)
    _print_counts(folder)
    return 0


def _print_counts(folder) -> None:
    import json

    tracks = json.loads((folder / "tracks" / "detections.json").read_text())
    throws = json.loads((folder / "throws" / "candidates.json").read_text())
    print(f"tracks {tracks['track_ids']} detections {tracks['detections']} in {tracks['elapsed_s']}s")
    print(f"throw candidates {throws['candidate_count']}")
    players = folder / "identity" / "players.json"
    if players.is_file():
        for player in json.loads(players.read_text())["players"]:
            times = ", ".join(f"{throw['timestamp_s']}s" for throw in player["throws"]) or "none"
            print(
                f"player {player['player_id']} tracks {player['track_ids']} "
                f"throws {player['throw_count']}: {times}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(prog="throwlog")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("stages", help="List pipeline stages")
    sub.add_parser("check", help="Load config and report the local clip")
    session = sub.add_parser("session", help="Create a session working folder")
    session.add_argument("session_id")
    ingest = sub.add_parser("ingest", help="Decode a session video and write ingest.json")
    ingest.add_argument("session_id")
    run = sub.add_parser("run", help="Track, pose, and count throw candidates")
    run.add_argument("session_id")
    args = parser.parse_args()
    if args.command == "stages":
        raise SystemExit(_cmd_stages())
    if args.command == "check":
        raise SystemExit(_cmd_check())
    if args.command == "session":
        raise SystemExit(_cmd_session(args.session_id))
    if args.command == "ingest":
        raise SystemExit(_cmd_ingest(args.session_id))
    if args.command == "run":
        raise SystemExit(_cmd_run(args.session_id))
    raise SystemExit(2)


if __name__ == "__main__":
    main()
