from enum import Enum
from typing import Callable

from fastapi import Depends

import usecases.profiles
import usecases.sessions
from models.database.profiles import CurrentProfile as Profile
from models.database.sessions import CurrentSession as Session
from osuProtocol.server_packets import client_relog_response


class OsuErrors(Enum):
    NON = "error: no"
    BEATMAP = "error: beatmap"
    BAN = "error: ban"


class ClientResponseException(Exception):
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code
        super().__init__(content)


def _encode_error_response(error_response: OsuErrors | str | bytes | None) -> bytes:
    if error_response is None:
        return b""

    if isinstance(error_response, OsuErrors):
        return error_response.value.encode()

    if isinstance(error_response, (bytes, bytearray, memoryview)):
        return bytes(error_response)

    if isinstance(error_response, str):
        return error_response.encode()

    return b""


def retrieve_session(
    error_response: OsuErrors | str | bytes | None = None,
) -> Callable[[], Session]:
    encoded_error_response = _encode_error_response(error_response)

    def _retrieve_session() -> Session:
        session = usecases.sessions.get_current_session()
        if session is None:
            raise ClientResponseException(encoded_error_response)

        return session

    return _retrieve_session


def retrieve_profile(
    error_response: OsuErrors | str | bytes | None = None,
    error_response_message: str = "Session has no associated profile, please relog.",
    relog_on_failure: bool = True,
) -> Callable[[], Profile]:
    encoded_error_response = _encode_error_response(error_response)

    def _retrieve_profile(
        session: Session = Depends(retrieve_session(error_response)),
    ) -> Profile:
        profile = usecases.profiles.get_profile(session.profile_name)
        if profile is None:
            if relog_on_failure:
                usecases.sessions.enqueue_packets_to_current_session(
                    client_relog_response(message=error_response_message),
                )

            raise ClientResponseException(encoded_error_response)

        return profile

    return _retrieve_profile


# Backward-compatible aliases for existing imports.
retrive_session = retrieve_session
retrive_profile = retrieve_profile
