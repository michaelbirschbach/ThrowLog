"""Output contract for one throw and for a player's session summary."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class DrillType(str, Enum):
    catch = "catch"
    wall = "wall"


class ComponentConfidence(BaseModel):
    detection: float = Field(ge=0, le=1)
    identity: float = Field(ge=0, le=1)
    ball_type: float = Field(ge=0, le=1)
    distance: float = Field(ge=0, le=1)
    velocity: float = Field(ge=0, le=1)


class ThrowRecord(BaseModel):
    session_id: str = Field(min_length=1)
    throw_id: int = Field(ge=1)
    timestamp_s: float = Field(ge=0)
    frame: int = Field(ge=0)
    player_id: str = Field(min_length=1)
    partner_id: Optional[str] = None
    drill_type: DrillType
    ball_type: str = Field(min_length=1)
    distance_ft: float = Field(ge=0)
    velocity_mph: float = Field(ge=0)
    velocity_low_mph: float = Field(ge=0)
    velocity_high_mph: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    component_conf: ComponentConfidence
    needs_review: bool
    clip_path: str = Field(min_length=1)

    @model_validator(mode="after")
    def check_relationships(self) -> "ThrowRecord":
        if self.velocity_low_mph > self.velocity_mph:
            raise ValueError("velocity_low_mph cannot exceed velocity_mph")
        if self.velocity_high_mph < self.velocity_mph:
            raise ValueError("velocity_high_mph cannot be below velocity_mph")
        if self.drill_type is DrillType.wall and self.partner_id is not None:
            raise ValueError("a wall drill has no receiving partner")
        if self.drill_type is DrillType.catch and not self.partner_id:
            raise ValueError("a catch throw needs a partner_id")
        return self


class PlayerSessionSummary(BaseModel):
    session_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    total_throws: int = Field(ge=0)
    throws_by_drill: dict[str, int]
    throws_by_ball: dict[str, int]
    distance_min_ft: Optional[float] = Field(default=None, ge=0)
    distance_max_ft: Optional[float] = Field(default=None, ge=0)
    velocity_mean_mph: Optional[float] = Field(default=None, ge=0)
    velocity_max_mph: Optional[float] = Field(default=None, ge=0)
    flagged_throws: int = Field(ge=0)
    first_throw_s: Optional[float] = Field(default=None, ge=0)
    last_throw_s: Optional[float] = Field(default=None, ge=0)
