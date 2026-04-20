from jays_tools import MigratableModel
from pydantic import Field

class PortStateV1(MigratableModel):
    ports_in_uses: dict[str, int] = Field(default_factory=dict)

PortState = PortStateV1