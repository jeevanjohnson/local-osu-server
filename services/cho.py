from datetime import datetime
from typing import TypedDict

import usecases.adapters.ossapi
import usecases.application.client.state
import usecases.application.client.update
import usecases.application.commands
from osuProtocol.client_packets import parse_login_data
import usecases.domain.bancho.users
import usecases.domain.chats
import usecases.domain.profiles
import usecases.domain.interface
from models.database.client.state import ClientState
from models.database.profiles import CurrentProfile as Profile
from models.domain.gameplay import Mods
from osuProtocol.client_packets import ChangeAction
from osuProtocol.server_packets import Login, LoginAuthFailed, osuAction, osuGameMode


class LoginResponse(TypedDict):
    client_response: bytes
    status: str


async def login(
    client_state: ClientState,
    raw_login_data: bytes,
) -> LoginResponse:

    if not await usecases.domain.interface.logged_in():
        content = LoginAuthFailed(
            "You must be logged in through the GUI to use the osu! client."
        ).build()

        return {
            "client_response": content,
            "status": "not-logged-in-gui",
        }

    profile = await usecases.domain.profiles.get_profile(client_state.profile_name)

    if profile is None:
        content = LoginAuthFailed(
            f"Profile '{client_state.profile_name}' not found. Please create a profile to use the osu! client."
        ).build()

        return {
            "client_response": content,
            "status": "profile-not-found",
        }

    api_client = await usecases.adapters.ossapi.get()

    if not api_client:
        content = LoginAuthFailed(
            "Credentials for osu! API not found/valid. Please log in through the GUI to set up your credentials correctly."
        ).build()

        return {
            "client_response": content,
            "status": "osu-api-credentials-not-found",
        }

    login_data = parse_login_data(raw_login_data)
    utc_offset = login_data["utc_offset"]

    login_message = f"Welcome to LOS!, {client_state.profile_name} ʕ•̫͡•ʔ"

    api_latency = await usecases.adapters.ossapi.latency()
    login_message += f" \n(Bancho API latency: {api_latency})"

    rank = profile.performance[client_state.game_mode].rank
    ranked_score = profile.performance[client_state.game_mode].ranked_score
    accuracy = profile.performance[client_state.game_mode].accuracy
    play_count = profile.performance[client_state.game_mode].playcount
    total_score = profile.performance[client_state.game_mode].total_score
    performance_points = profile.performance[client_state.game_mode].performance_points

    login_response = Login(
        username=client_state.profile_name,
        friend_ids=profile.friend_ids,
        utc_offset=utc_offset,
        country_code=profile.country_code,
        game_mode=client_state.game_mode,
        longitude=0.0,
        latitude=0.0,
        rank=rank,
        ranked_score=ranked_score,
        accuracy=accuracy,
        play_count=play_count,
        total_score=total_score,
        performance_points=performance_points,
        login_message=login_message,
        latency=api_latency,
    )

    login_response += await usecases.domain.bancho.users.get_presences_and_stats(
        api_client=api_client,
        user_ids=profile.friend_ids,
        game_mode=client_state.game_mode,
    )

    client_state.in_game = True
    client_state.in_game_at = datetime.now()

    await usecases.application.client.state.update(client_state)

    return {
        "client_response": login_response.build(),
        "status": f"login-successful-for-{client_state.profile_name}",
    }


async def process_action_change(
    packet: ChangeAction, client_state: ClientState, profile: Profile
) -> None:
    print(
        f"Processing action change: action={packet.action.value}, info_text='{packet.info_text.value}'"
    )

    client_state.status = osuAction(packet.action.value)
    if client_state.status != osuAction.OsuDirect:
        client_state.direct_reference.cursor_string = None

    client_state.status_message = packet.info_text.value
    client_state.in_game = True

    client_state.game_mode = osuGameMode(packet.current_game_mode.value)

    client_state.mods = Mods.from_stable_int(packet.current_mods.value)

    print(
        f"Calling stats_with_state_and_profile with status={client_state.status.name}"
    )

    await usecases.application.client.update.stats_with_state_and_profile(
        client_state=client_state, profile=profile
    )


async def process_logout(client_state: ClientState, profile: Profile) -> None:
    # osu! client logs out as soon as the user logs in
    # just ensure that this packet is a valid logout
    if datetime.now().timestamp() - client_state.in_game_at.timestamp() < 1:
        return

    client_state.in_game = False
    client_state.status = osuAction.Idle
    client_state.status_message = ""
    client_state.beatmap.md5 = ""
    client_state.beatmap.id = 0
    client_state.game_mode = osuGameMode.STANDARD
    client_state.mods = Mods()
    client_state.direct_reference.cursor_string = None

    await usecases.application.client.state.update(client_state)

    await usecases.application.client.update.stats_with_state_and_profile(
        client_state=client_state, profile=profile
    )


async def process_user_stats_request(
    user_ids: list[int], client_state: ClientState, profile: Profile
) -> None:

    if 3 in user_ids:
        await usecases.application.client.update.stats_and_presence_for_bancho_bot()
        user_ids.remove(3)

    if 2 in user_ids:
        # await usecases.application.client.update.stats_and_presence_for_player(
        #     client_state=client_state,
        #     profile=profile
        # )
        user_ids.remove(2)

    api_client = await usecases.adapters.ossapi.get()

    if not api_client:
        await usecases.application.client.update.restart_client()
        return

    await usecases.application.client.update.friends(
        user_ids=user_ids,
        game_mode=client_state.game_mode,
    )


async def process_friend_remove(
    friend_user_id: int, client_state: ClientState, profile: Profile
) -> None:
    await usecases.domain.profiles.remove_friend_from_profile(
        profile_name=client_state.profile_name, friend_user_id=friend_user_id
    )

    await usecases.application.client.update.friend_remove(friend_user_id)


async def process_message(
    client_state: ClientState,
    profile: Profile,
    text: str,
    recipient: str,
) -> None:
    if text.startswith("!"):
        response_text = await usecases.application.commands.handle_command(
            client_state=client_state, profile=profile, message=text
        )
        if response_text:
            await usecases.application.client.update.message(
                recipient=recipient,
                sender="BanchoBot",
                message=response_text,
                sender_id=3,
            )

    if not usecases.domain.chats.is_np(text):
        # not a /np, so we don't care
        return

    message = await usecases.domain.chats.pp_for(
        client_state.beatmap.md5, client_state.game_mode, client_state.mods
    )

    if message:
        await usecases.application.client.update.message_from_bancho_bot(
            recipient=recipient, msg=message
        )
