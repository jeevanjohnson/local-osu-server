from pydantic import Field

from jays_tools import MigratableModel


class InterfaceStateV1(MigratableModel):
    subprocess_pid: int | None = Field(default=None)
    current_profile: str | None = Field(default=None)


InterfaceState = InterfaceStateV1
