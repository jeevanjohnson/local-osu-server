from jays_tools import MigratableModel
from datetime import datetime
from pydantic import Field

class SnapShotV1(MigratableModel):
    osu: list[tuple[int, int]] = Field(default_factory=list)  # list of (pp, rank)
    taiko: list[tuple[int, int]] = Field(default_factory=list) # list of (pp, rank)
    catch: list[tuple[int, int]] = Field(default_factory=list) # list of (pp, rank)
    mania: list[tuple[int, int]] = Field(default_factory=list) # list of (pp, rank)

SnapShot = SnapShotV1

class OsuScraperStateV1(MigratableModel):
    snapshots: dict[datetime, SnapShot] = Field(default_factory=dict)

OsuScraperState = OsuScraperStateV1