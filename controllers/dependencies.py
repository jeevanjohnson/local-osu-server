from enum import Enum
from typing import Awaitable, Callable

from fastapi import Depends

import usecases.profiles
import usecases.sessions
import usecases.server_settings
from models.database.profiles import CurrentProfile as Profile
from models.database.sessions import CurrentSession as Session
from models.domain.errors import ProfileNotFoundError, SessionNotFoundError
from models.database.server_settings import CurrentServerSettings as ServerSettings


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
    status_code: int = 200,
) -> Callable[[], Awaitable[Session]]:
    encoded_error_response = _encode_error_response(error_response)

    async def _retrieve_session() -> Session:
        try:
            session = await usecases.sessions.require_current_session()
        except SessionNotFoundError:
            raise ClientResponseException(
                encoded_error_response, status_code=status_code
            )

        return session

    return _retrieve_session


def retrieve_profile(
    error_response: OsuErrors | str | bytes | None = None,
    error_response_message: str = "Session has no associated profile, please relog.",
    relog_on_failure: bool = True,
    status_code: int = 200,
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
            raise ClientResponseException(
                encoded_error_response, status_code=status_code
            )

        return profile

    return _retrieve_profile

async def retrieve_server_settings() -> ServerSettings:
    server_settings = await usecases.server_settings.get_server_settings()
    return server_settings