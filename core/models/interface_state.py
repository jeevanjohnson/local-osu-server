from pydantic import Field

from jays_tools import MigratableModel


class InterfaceStateV1(MigratableModel):
    port_in_use: int | None = Field(default=None)
    subprocess_pid: int | None = Field(default=None)

    current_profile: str | None = Field(default=None)


InterfaceState = InterfaceStateV1
