"""
Purpose/Domain/Concept:
- This file contains the repository (database interactions) related sessions.json file.
"""

from database.jsonfile import JsonFile
from models.database.sessions import Session

class SessionsRepository:
    def __init__(self, path):
        self.sessions = JsonFile[Session](path)

    def get_current_session(self) -> Session | None:
        with self.sessions as sessions:
            if not sessions:
                return None
            
            return sessions

    def create_session(self, session: Session) -> None:
        with self.sessions as sessions:
            sessions.update(session)

    def delete_current_session(self) -> None:
        with self.sessions as sessions:
            sessions.update(Session(
                profile_name=None,
                loaded_beatmap_md5=None,
                loaded_replay_id=None,
                current_game_mode=None,
                packet_queue=None,
                loaded_beatmap_id=None,
                loaded_beatmap_set_id=None,
                client_opened=False
            ))
    
    def update_current_session(self, session: Session) -> None:
        with self.sessions as sessions:
            sessions.update(session)