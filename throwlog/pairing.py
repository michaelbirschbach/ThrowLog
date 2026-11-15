"""Assign a thrower, a receiver, and catch or wall.

Not implemented. The module is here so the stage order and the session folder
are fixed before model code is written.
"""

from __future__ import annotations

from pathlib import Path

from throwlog.config import AppConfig
from throwlog.stage import not_ready


def run(session_dir: Path, config: AppConfig) -> None:
    """Pair each throw with a receiver or mark a wall drill."""
    del session_dir, config
    not_ready("pairing")
