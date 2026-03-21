"""
Purpose/Domain/Concept:
- This file contains the repository (database interactions) related sessions.json file.
"""

from models.database.sessions import CurrentSession as Session
from jays_tools.json_database import JsonDatabase

class SessionRepository:
    def __init__(self, path):
        self.session = JsonDatabase(path, models=Session)

    def get_current_session(self) -> Session | None:
        with self.session as current_session:
            if not current_session.loaded:
                return None
            
            return current_session

    def create_session(self, profile_name: str) -> None:
        with self.session as current_session:
            if current_session.loaded:
                raise ValueError("Session already exists.")

            current_session = Session(
                loaded=True,
                profile_name=profile_name
            )

            self.session.set(current_session)

    def delete_current_session(self) -> None:
        with self.session as current_session:
            if not current_session.loaded:
                raise ValueError("No session to delete.")

            deleted_session = current_session.default()

            self.session.set(deleted_session)

    def update_current_session(self, updated_session: Session) -> None:
        with self.session as current_session:
            if not current_session.loaded:
                raise ValueError("No session to update.")

            current_session = updated_session

            self.session.set(current_session)