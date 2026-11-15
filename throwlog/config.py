"""Load config/default.yaml into a checked object. Thresholds are not hard-coded."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "default.yaml"


class IngestConfig(BaseModel):
    sample_every_n_frames: int = Field(ge=1)
    full_rate_window_frames: int = Field(ge=0)


class PoseConfig(BaseModel):
    model: str
    device: str
    tracker: str


class ThrowConfig(BaseModel):
    wrist_speed_min: Optional[float] = None
    min_gap_frames: int = Field(ge=1)


class ReviewConfig(BaseModel):
    confidence_threshold: float = Field(ge=0, le=1)


class AppConfig(BaseModel):
    ingest: IngestConfig
    pose: PoseConfig
    throws: ThrowConfig
    review: ReviewConfig
    ball_colors: dict[str, str] = Field(default_factory=dict)


def load_config(path: Path = DEFAULT_CONFIG) -> AppConfig:
    with path.open() as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError(f"{path} did not contain a mapping")
    return AppConfig.model_validate(raw)
