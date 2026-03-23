"""
Purpose/Domain/Concept:
- This file contains the repository (database interactions) related sessions.json file.
"""

from jays_tools.json_database import JsonDatabase

from models.database.sessions import CurrentSession as Session
from models.domain.errors import SessionAlreadyExistsError, SessionNotFoundError


class SessionRepository:
    def __init__(self, path):
        self.session = JsonDatabase(path, models=Session)

    # @log_time
    async def require_current_session(self) -> Session:
        async with self.session as current_session:
            if not current_session.loaded:
                raise SessionNotFoundError("No active session.")

            return current_session

    # @log_time
    async def maybe_get_current_session(self) -> Session | None:
        try:
            return await self.require_current_session()
        except SessionNotFoundError:
            return None

    # @log_time
    async def create_session(self, profile_name: str) -> None:
        async with self.session as current_session:
            if current_session.loaded:
                raise SessionAlreadyExistsError("Session already exists.")

            current_session = Session(loaded=True, profile_name=profile_name)

            self.session.set(current_session)

    # @log_time
    async def delete_current_session(self) -> None:
        async with self.session as current_session:
            if not current_session.loaded:
                raise SessionNotFoundError("No session to delete.")

            deleted_session = current_session.default()

            self.session.set(deleted_session)

    # @log_time
    async def update_current_session(self, updated_session: Session) -> None:
        async with self.session as current_session:
            if not current_session.loaded:
                raise SessionNotFoundError("No session to update.")

            current_session = updated_session

            self.session.set(current_session)
