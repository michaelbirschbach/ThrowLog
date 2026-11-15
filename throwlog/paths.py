"""Per-session working folder. Stages read and write files here so any stage can be rerun alone."""

from __future__ import annotations

from pathlib import Path

from throwlog.config import ROOT

DATA = ROOT / "data"
RAW = DATA / "raw"
SESSIONS = DATA / "sessions"
LABELS = DATA / "labels"
MANIFESTS = DATA / "manifests"


def session_dir(session_id: str) -> Path:
    if not session_id or "/" in session_id or session_id.startswith("."):
        raise ValueError(f"invalid session id: {session_id!r}")
    return SESSIONS / session_id


def ensure_session(session_id: str) -> Path:
    root = session_dir(session_id)
    for name in ("frames", "tracks", "poses", "throws", "export"):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root
