"""
Purpose/Domain/Concept:
- This file contains the logic related to sessions.
"""

from models.bancho.scores import Scores, StableScore
from models.database.client.state import ClientState
from models.domain.gameplay import Mods, osuGameMode
from repositories.client.state import ClientStateRepository


async def get() -> ClientState:
    client_state_repo = ClientStateRepository()
    return await client_state_repo.get_client_state()


async def delete() -> None:
    client_state_repo = ClientStateRepository()
    await client_state_repo.delete_client_state()

    return None


async def create(profile_name: str) -> None:
    client_state_repo = ClientStateRepository()
    await client_state_repo.start_client_state(profile_name)

    return None


async def profile_name() -> str:
    client_state = await get()
    return client_state.profile_name


async def logout() -> None:
    client_state_repo = ClientStateRepository()
    client_state = await client_state_repo.get_client_state()

    client_state.logged_in = False
    await client_state_repo.update_client_state(client_state)

    return None


async def login(profile_name: str) -> None:
    client_state_repo = ClientStateRepository()
    client_state = await client_state_repo.get_client_state()

    client_state.logged_in = True
    client_state.profile_name = profile_name
    await client_state_repo.update_client_state(client_state)

    return None


async def is_logged_in() -> bool:
    client_state = await get()

    return client_state.logged_in


async def update(client_state: ClientState) -> None:
    print(
        f"DEBUG state.update() - storing cursor: {client_state.direct_reference.cursor_string}"
    )
    client_state_repo = ClientStateRepository()
    await client_state_repo.update_client_state(client_state)
    print(f"DEBUG state.update() - cursor persisted")

    return None


async def beatmap_watchable_replays(replay_ids: list[int]) -> None:
    client_state_repo = ClientStateRepository()
    client_state = await client_state_repo.get_client_state()

    client_state.beatmap.watchable_replays.clear()
    client_state.beatmap.watchable_replays = replay_ids

    await client_state_repo.update_client_state(client_state)

    return


async def update_avaliable_stable_replay_ids_from_scores(scores: Scores) -> None:
    await beatmap_watchable_replays(
        [
            score.score_id
            for score in scores.scores
            if isinstance(score, StableScore) and score.replay_available
        ]
    )


async def get_direct_cursor_string() -> str | None:
    client_state = await get()
    cursor = client_state.direct_reference.cursor_string
    print(f"DEBUG get_direct_cursor_string() - retrieved cursor: {cursor}")
    return cursor


async def update_game_mode_and_mods(game_mode: osuGameMode, mods: Mods) -> None:
    client_state_repo = ClientStateRepository()
    client_state = await client_state_repo.get_client_state()

    client_state.game_mode = game_mode
    client_state.mods = mods
    await client_state_repo.update_client_state(client_state)

    return None
