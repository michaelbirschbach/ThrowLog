"""Find the ball after release and label its color.

Not implemented. The module is here so the stage order and the session folder
are fixed before model code is written.
"""

from __future__ import annotations

from pathlib import Path

from throwlog.config import AppConfig
from throwlog.stage import not_ready


def run(session_dir: Path, config: AppConfig) -> None:
    """Detect the ball and assign a color label."""
    del session_dir, config
    not_ready("ball")
