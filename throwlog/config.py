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
    imgsz: int = Field(ge=32)
    confidence: float = Field(ge=0, le=1)
    keypoint_confidence: float = Field(ge=0, le=1)
    track_every_n_frames: int = Field(ge=1)


class ThrowConfig(BaseModel):
    wrist_speed_min: Optional[float] = None
    min_gap_frames: int = Field(ge=1)
    smooth_frames: int = Field(ge=1)
    peak_factor: float = Field(gt=0)
    min_track_frames: int = Field(ge=1)


class IdentityConfig(BaseModel):
    height_ratio_max: float = Field(gt=1)
    overlap_iou_min: float = Field(ge=0, le=1)
    max_gap_frames: int = Field(ge=0)


class BallConfig(BaseModel):
    detect_width: int = Field(ge=32)
    sat_max: int = Field(ge=0, le=255)
    value_min: int = Field(ge=0, le=255)
    background_value_max: int = Field(ge=0, le=255)
    contrast_min: int = Field(ge=0)
    area_min: int = Field(ge=1)
    area_max: int = Field(ge=1)
    close_sat_max: int = Field(ge=0, le=255)
    close_value_min: int = Field(ge=0, le=255)
    close_area_min: int = Field(ge=1)
    close_area_max: int = Field(ge=1)
    max_jump_px: float = Field(gt=0)
    max_gap_frames: int = Field(ge=0)
    min_track_frames: int = Field(ge=1)
    min_travel_px: float = Field(ge=0)
    min_straightness: float = Field(ge=0, le=1)
    static_cell_px: int = Field(ge=1)
    static_cell_hits: int = Field(ge=1)
    confirm_window_frames: int = Field(ge=0)


class PairingConfig(BaseModel):
    presence_frames: int = Field(ge=0)
    approach_px: float = Field(ge=0)


class ReviewConfig(BaseModel):
    confidence_threshold: float = Field(ge=0, le=1)


class AppConfig(BaseModel):
    ingest: IngestConfig
    pose: PoseConfig
    throws: ThrowConfig
    identity: IdentityConfig
    ball: BallConfig
    pairing: PairingConfig
    review: ReviewConfig
    ball_colors: dict[str, str] = Field(default_factory=dict)


def load_config(path: Path = DEFAULT_CONFIG) -> AppConfig:
    with path.open() as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError(f"{path} did not contain a mapping")
    return AppConfig.model_validate(raw)
