from enum import Enum
from typing import Awaitable, Callable

from fastapi import Depends

import usecases.profiles
import usecases.sessions
from models.domain.errors import ProfileNotFoundError, SessionNotFoundError
from models.database.profiles import CurrentProfile as Profile
from models.database.sessions import CurrentSession as Session


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
) -> Callable[[], Awaitable[Session]]:
    encoded_error_response = _encode_error_response(error_response)

    async def _retrieve_session() -> Session:
        try:
            session = await usecases.sessions.require_current_session()
        except SessionNotFoundError:
            raise ClientResponseException(encoded_error_response)

        return session

    return _retrieve_session


def retrieve_profile(
    error_response: OsuErrors | str | bytes | None = None,
    error_response_message: str = "Session has no associated profile, please relog.",
    relog_on_failure: bool = True,
) -> Callable[[], Awaitable[Profile]]:
    encoded_error_response = _encode_error_response(error_response)

    async def _retrieve_profile(
        session: Session = Depends(retrieve_session(error_response)),
    ) -> Profile:
        try:
            profile = await usecases.profiles.require_profile(session.profile_name)
        except ProfileNotFoundError:
            if relog_on_failure:
                await usecases.sessions.restart_client(error_response_message)
            raise ClientResponseException(encoded_error_response)

        return profile

    return _retrieve_profile


# Backward-compatible aliases for existing imports.
retrive_session = retrieve_session
retrive_profile = retrieve_profile
