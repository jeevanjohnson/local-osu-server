from pydantic import Field

from jays_tools import MigratableModel


class StateV1(MigratableModel):
    port_in_use: int | None = Field(default=None)
    subprocess_pid: int | None = Field(default=None)


State = StateV1
