
# TODO implement base configuration and aggregator HERE
from sqlmodel import Field, SQLModel, create_engine
import settings

class Accounts(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(default=None)
    password: str = Field(default=None)
    performance_points: int = Field(default=0)
    country: str | None = Field(default=None)



class Sessions(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    secret_name: str
    age: int | None = None


assert settings.SQLLITE_FILE_NAME.endswith(".db")


sqlite_file_name = f"{settings.SQLLITE_FILE_NAME}.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)

SQLModel.metadata.create_all(engine)
