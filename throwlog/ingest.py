"""Decode the session video and record frame rate, size, and rotation.

Not implemented. The module is here so the stage order and the session folder
are fixed before model code is written.
"""

from __future__ import annotations

from pathlib import Path

from throwlog.config import AppConfig
from throwlog.stage import not_ready


def run(session_dir: Path, config: AppConfig) -> None:
    """Decode video, sample frames, and write ingest metadata."""
    del session_dir, config
    not_ready("ingest")
