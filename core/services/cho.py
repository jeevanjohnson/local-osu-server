import core.osu_protocol.cho.client as cho_client
from core.usecases.domain.player import Player
import core.osu_protocol.cho.server as cho_server
import core.osu_protocol.cho.enums as cho_enums
from datetime import datetime

async def login(
    player: Player,
    login_data: cho_client.LoginData,
) -> cho_server.Packets:
    profile = player.get_profile()
    client_state = player.get_client_state()
    performance = profile.performance[client_state.game_mode]

    utc_offset = login_data.utc_offset
    friend_ids = profile.friend_ids
    rank = performance.rank
    ranked_score = performance.ranked_score
    accuracy = performance.accuracy
    play_count = performance.playcount
    total_score = performance.total_score
    performance_points = performance.performance_points

    packets = cho_server.Packets()

    packets += cho_server.UserID(2)
    packets += cho_server.ProtocolVersion(19)

    packets += cho_server.UserPrivileges(cho_enums.ALL_PRIVILEGES)

    packets += cho_server.Notification(f"Welcome to LOS!, {player.name} ʕ•̫͡•ʔ")

    for channel in ["#osu", "#nothing"]:
        packets += cho_server.ChannelInfo(
            name=channel, topic=f"Welcome to {channel}!", player_count=1
        )

    packets += cho_server.ReOrderChannels()

    packets += cho_server.MainMenuIcon(
        icon_url="https://a.ppy.sh/13028687.png",
        on_click_url="https://github.com/jeevanjohnson/local-osu-server",
    )

    packets += cho_server.UserFriendList(friend_ids)

    packets += cho_server.PlayerPresence(
        user_id=2,
        username=player.name,
        utc_offset=utc_offset,
        country_code=profile.country_code,
        user_privileges=cho_enums.ALL_PRIVILEGES,
        game_mode=client_state.game_mode,
        longitude=0.0,
        latitude=0.0,
        rank=rank,
    )

    packets += cho_server.PlayerStats(
        user_id=2,
        action=client_state.status,
        info_text="",
        beatmap_md5="",
        mods=client_state.mods.to_stable_mods(),
        game_mode=client_state.game_mode,
        beatmap_id=0,
        ranked_score=ranked_score,
        accuracy=accuracy,
        play_count=play_count,
        total_score=total_score,
        rank=rank,
        performance_points=performance_points,
    )

    packets += cho_server.bancho_bot()

    # TODO: friends presence 

    client_state.in_game = True
    client_state.in_game_at = datetime.now()

    player.update_client_state(client_state)

    return packets