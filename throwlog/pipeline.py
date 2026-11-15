"""Run the stages in order. Each stage is imported from its own module."""

from __future__ import annotations

from pathlib import Path

from throwlog import (
    ball,
    confidence,
    export,
    geometry,
    identity,
    ingest,
    pairing,
    pose,
    throws,
    track,
    velocity,
)
from throwlog.config import AppConfig
from throwlog.stage import StageNotReady

# export is a writer, not a detection stage. It stays out of this list until records exist.
STAGES: list[tuple[str, object]] = [
    ("ingest", ingest.run),
    ("track", track.run),
    ("pose", pose.run),
    ("throws", throws.run),
    ("ball", ball.run),
    ("pairing", pairing.run),
    ("identity", identity.run),
    ("geometry", geometry.run),
    ("velocity", velocity.run),
    ("confidence", confidence.run),
]


def stage_names() -> list[str]:
    return [name for name, _run in STAGES]


def run_session(session_dir: Path, config: AppConfig, through: str | None = None) -> str:
    """Run stages until `through`, inclusive. Returns the last stage that finished.

    The first unfinished stage raises StageNotReady and leaves earlier outputs in place.
    """
    if through is not None and through not in stage_names():
        raise ValueError(f"unknown stage: {through}")
    last = ""
    for name, run in STAGES:
        run(session_dir, config)
        last = name
        if name == through:
            break
    return last


def next_unimplemented(session_dir: Path, config: AppConfig) -> str:
    """Return the name of the first stage that is not implemented.

    This does not run the stage. Implemented stages stay marked on the module.
    """
    del session_dir, config
    modules = {
        "ingest": ingest,
        "track": track,
        "pose": pose,
        "throws": throws,
        "ball": ball,
        "pairing": pairing,
        "identity": identity,
        "geometry": geometry,
        "velocity": velocity,
        "confidence": confidence,
    }
    for name, _run in STAGES:
        if not getattr(modules[name], "IMPLEMENTED", False):
            return name
    return ""


# Re-exported so callers can find the writer without importing a detection stage.
write_exports = export
