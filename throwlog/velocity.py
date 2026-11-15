"""Estimate speed in miles per hour from the measured subset.

Not implemented. The module is here so the stage order and the session folder
are fixed before model code is written.
"""

from __future__ import annotations

from pathlib import Path

from throwlog.config import AppConfig
from throwlog.stage import not_ready


def run(session_dir: Path, config: AppConfig) -> None:
    """Build velocity features and calibrate them."""
    del session_dir, config
    not_ready("velocity")
