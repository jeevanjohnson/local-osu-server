from jays_tools.sql_database import SQLDatabase
from core.models.adapters.database import ALL_TABLES
from constants import Paths

def SQLDatabaseInstance() -> SQLDatabase:
    return SQLDatabase(
        sqlite_database_path=Paths.DATABASE,
        tables=ALL_TABLES
    )