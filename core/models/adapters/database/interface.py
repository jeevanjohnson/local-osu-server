from jays_tools.sql_database import MigratableSQLModel
from jays_tools.architecture import AdapterModel
from pydantic import Field


class InterfaceStateV1(MigratableSQLModel, AdapterModel, table=True):
    profile_name: str = Field(default="")


InterfaceState = InterfaceStateV1
