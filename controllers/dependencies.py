from fastapi import Depends

import usecases.application.client.state
import usecases.application.client.update
import usecases.domain.profiles
import usecases.domain.server_settings
from models.database.client.state import ClientState
from models.database.profiles import CurrentProfile as Profile
from models.database.server_settings import CurrentServerSettings as ServerSettings


async def client_state() -> ClientState:
    return await usecases.application.client.state.get()


async def profile(client_state: ClientState = Depends(client_state)) -> Profile | None:
    return await usecases.domain.profiles.get_profile(client_state.profile_name)


async def retrieve_server_settings() -> ServerSettings:
    server_settings = await usecases.domain.server_settings.get_server_settings()
    return server_settings
