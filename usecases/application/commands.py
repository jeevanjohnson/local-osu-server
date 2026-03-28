from typing import Any, Callable, Coroutine

import usecases.adapters.cache
import usecases.domain.cache_control
import usecases.domain.calculator.performance
import usecases.domain.calculator.rank
import usecases.adapters.ossapi
import usecases.application.beatmaps
import usecases.application.client
import usecases.application.client.update
import usecases.domain.bancho.users
import usecases.domain.beatmaps
import usecases.domain.chats
import usecases.domain.profiles
import usecases.domain.scores
import usecases.domain.server_settings
from models.database.beatmaps import CurrentBeatmap as Beatmap
from models.database.client.state import ClientState
from models.database.profiles import CurrentProfile as Profile
from models.domain.gameplay import Mods
from osu_protocol.osu.types import osuMapStatus
from pprint import pformat
import usecases.domain.server
import asyncio

CommandFunc = Callable[[ClientState, Profile, str], Coroutine[Any, Any, str]]

ALL_COMMANDS: dict[str, CommandFunc] = {}


def register_command(
    command_name: str | list[str],
) -> Callable[[CommandFunc], CommandFunc]:
    def decorator(func: CommandFunc) -> CommandFunc:
        if isinstance(command_name, list):
            for name in command_name:
                ALL_COMMANDS[name] = func
        else:
            ALL_COMMANDS[command_name] = func
        return func

    return decorator

async def change_beatmap_status(
    beatmap_md5: str,
    profile_name: str,
    new_status: osuMapStatus,
) -> Beatmap | None:
    beatmap = await usecases.domain.beatmaps.change_beatmap_status(
        beatmap_md5=beatmap_md5,
        profile_name=profile_name,
        new_status=new_status,
    )

    if beatmap is None:
        return

    usecases.domain.cache_control.clear_beatmaps_cache()
    usecases.domain.cache_control.clear_scores_cache()
    usecases.domain.cache_control.clear_leaderboard_cache()

    return beatmap


@register_command(["rank"])
async def rank_command(client_state: ClientState, profile: Profile, none: str) -> str:
    if not client_state.beatmap.md5:
        return "No beatmap currently loaded. Cannot perform calculations without a beatmap."

    api_client = await usecases.adapters.ossapi.get()
    if api_client is None:
        return "API client not available. Cannot rank beatmap."

    beatmaps = await usecases.domain.beatmaps.change_beatmapset_status(
        beatmap_md5=client_state.beatmap.md5,
        profile_name=client_state.profile_name,
        new_status=osuMapStatus.RANKED,
        api_client=api_client,
    )

    if not beatmaps:
        return "Beatmap not found. Cannot change status without a beatmap."

    # Clear caches since beatmap status changed
    usecases.domain.cache_control.clear_beatmaps_cache()
    usecases.domain.cache_control.clear_leaderboard_cache()

    primary = beatmaps[0]
    count = len(beatmaps)
    if count == 1:
        return f"Beatmap {primary.artist} - {primary.title} [{primary.difficulty_name}] is now ranked."
    else:
        return f"Ranked beatmapset ({count} difficulties): {primary.artist} - {primary.title}"


@register_command(["love", "l"])
async def love_command(client_state: ClientState, profile: Profile, none: str) -> str:
    if not client_state.beatmap.md5:
        return "No beatmap currently loaded. Cannot perform calculations without a beatmap."

    api_client = await usecases.adapters.ossapi.get()
    if api_client is None:
        return "API client not available. Cannot love beatmap."

    beatmaps = await usecases.domain.beatmaps.change_beatmapset_status(
        beatmap_md5=client_state.beatmap.md5,
        profile_name=client_state.profile_name,
        new_status=osuMapStatus.LOVED,
        api_client=api_client,
    )

    if not beatmaps:
        return "Beatmap not found. Cannot change status without a beatmap."

    primary = beatmaps[0]
    count = len(beatmaps)
    if count == 1:
        return f"Beatmap {primary.artist} - {primary.title} [{primary.difficulty_name}] is now loved."
    else:
        return f"Loved beatmapset ({count} difficulties): {primary.artist} - {primary.title}"


@register_command(["approved", "a"])
async def approved_command(
    client_state: ClientState, profile: Profile, none: str
) -> str:
    if not client_state.beatmap.md5:
        return "No beatmap currently loaded. Cannot perform calculations without a beatmap."

    api_client = await usecases.adapters.ossapi.get()
    if api_client is None:
        return "API client not available. Cannot approve beatmap."

    beatmaps = await usecases.domain.beatmaps.change_beatmapset_status(
        beatmap_md5=client_state.beatmap.md5,
        profile_name=client_state.profile_name,
        new_status=osuMapStatus.APPROVED,
        api_client=api_client,
    )

    if not beatmaps:
        return "Beatmap not found. Cannot change status without a beatmap."

    primary = beatmaps[0]
    count = len(beatmaps)
    if count == 1:
        return f"Beatmap {primary.artist} - {primary.title} [{primary.difficulty_name}] is now approved."
    else:
        return f"Approved beatmapset ({count} difficulties): {primary.artist} - {primary.title}"


@register_command(["unrank", "ur"])
async def unrank_command(client_state: ClientState, profile: Profile, none: str) -> str:
    if not client_state.beatmap.md5:
        return "No beatmap currently loaded. Cannot perform calculations without a beatmap."

    beatmap = await usecases.domain.beatmaps.from_db(client_state.beatmap.md5)
    if beatmap is None:
        return "Beatmap not found in database. Cannot change status without a beatmap."

    api_client = await usecases.adapters.ossapi.get()
    if api_client is None:
        return "API client not available. Cannot change status without API access."

    beatmap = await usecases.domain.beatmaps.refresh_beatmapset_status_from_api(
        api_client=api_client, profile_name=client_state.profile_name, beatmap=beatmap
    )

    if beatmap is None:
        return "Beatmap not found. Cannot change status without a beatmap."

    refreshed_status = beatmap.status[client_state.profile_name]
    return f"Beatmap {beatmap.artist} - {beatmap.title} [{beatmap.difficulty_name}] is back to {refreshed_status}."


@register_command("add")
async def add_friend_command(
    client_state: ClientState, profile: Profile, friend_name: str
) -> str:
    if not friend_name:
        return "Please provide a username to add as a friend. Usage: !add <username>"

    api_client = await usecases.adapters.ossapi.get()
    if api_client is None:
        return "API client not available. Cannot add friend without API access."

    friend = await usecases.domain.bancho.users.get(
        api_client=api_client, user_identifiers=friend_name
    )

    if friend is None:
        return f"User '{friend_name}' not found. Cannot add friend."

    updated_profile = await usecases.domain.profiles.add_friend(
        profile_name=client_state.profile_name, friend_user_id=friend.id
    )

    if updated_profile is None:
        return "Profile not found after adding friend. Please relog to run commands."

    await usecases.application.client.update.friends(
        user_ids=updated_profile.friend_ids,
        game_mode=client_state.game_mode,
    )

    usecases.domain.cache_control.clear_profiles_cache()

    return f"User '{friend_name}' has been added as a friend."


@register_command("remove")
async def remove_friend_command(
    client_state: ClientState, profile: Profile, friend_name: str
) -> str:
    if not friend_name:
        return "Please provide a username to remove from friends. Usage: !remove <username>"

    api_client = await usecases.adapters.ossapi.get()
    if api_client is None:
        return "API client not available. Cannot remove friend without API access."

    friend = await usecases.domain.bancho.users.get(
        api_client=api_client, user_identifiers=friend_name
    )

    if friend is None:
        return f"User '{friend_name}' not found. Cannot remove friend."

    await usecases.domain.profiles.remove_friend_from_profile(
        profile_name=client_state.profile_name, friend_user_id=friend.id
    )

    await usecases.application.client.update.friend_remove(
        user_id=friend.id,
    )

    usecases.domain.cache_control.clear_profiles_cache()

    return f"User '{friend_name}' has been removed from friends."


@register_command(["with", "w"])
async def with_command(
    client_state: ClientState, profile: Profile, mods_str: str
) -> str:
    if client_state.beatmap.md5 is None:
        return "No beatmap currently loaded. Cannot perform calculations without a beatmap."

    try:
        mods = Mods.from_stable_string(mods_str)
    except ValueError:
        return f"Invalid mods: {mods_str}. Please provide a valid mods string (e.g. HR, DT, HDHR)."

    return await usecases.domain.chats.pp_for(
        beatmap_md5=client_state.beatmap.md5,
        game_mode=client_state.game_mode,
        mods=mods,
    )


@register_command(["help", "h"])
async def help_command(client_state: ClientState, profile: Profile, none: str) -> str:
    msg = "Available commands:\n"
    for command_name, func in ALL_COMMANDS.items():
        func_parameter_name = list(func.__annotations__.keys())[1]

        if func_parameter_name != "none":
            msg += f"!{command_name} - args: {func_parameter_name}\n"
        else:
            msg += f"!{command_name}\n"

    return msg


@register_command(["delete"])
async def delete_score_command(
    client_state: ClientState, profile: Profile, none: str
) -> str:
    if not client_state.loaded_score_id:
        return "No score currently loaded. Cannot delete score without a score."

    # Delete the score
    await usecases.domain.scores.delete(score_id=client_state.loaded_score_id)

    client_state.loaded_score_id = 0

    # Recalculate the profile stats without a specific max combo (it's deleted)
    await usecases.domain.profiles.recalculate_stats(
        profile_name=client_state.profile_name,
        game_mode=client_state.game_mode,
    )

    usecases.domain.cache_control.clear_scores_cache()
    usecases.domain.cache_control.clear_leaderboard_cache()

    return "Score deleted successfully and stats recalculated."


@register_command(["rank_for", "rf"])
async def rank_for_command(
    client_state: ClientState, profile: Profile, pp_str: str
) -> str:
    try:
        pp = int(pp_str)
    except ValueError:
        return f"Invalid pp value: {pp_str}. Please provide a valid number."

    rank = await usecases.domain.calculator.rank.rank_for_pp(pp, game_mode=client_state.game_mode)

    return (
        f"For {pp}pp in {client_state.game_mode.name}, the estimated rank is #{rank}."
    )


@register_command(["pp_for", "pf"])
async def pp_for_command(
    client_state: ClientState, profile: Profile, rank_str: str
) -> str:
    try:
        rank = int(rank_str)
    except ValueError:
        return f"Invalid rank value: {rank_str}. Please provide a valid number."

    pp = await usecases.domain.calculator.rank.pp_for_rank(rank, game_mode=client_state.game_mode)

    return f"For rank #{rank} in {client_state.game_mode.name}, the estimated pp is {pp}pp."

@register_command(["py"])
async def python_command(
    client_state: ClientState, profile: Profile, code: str
) -> str:
    """DEVELOPER-ONLY COMMAND. Use with extreme caution. Executes arbitrary Python code and returns the result."""
    try:
        # Use the module’s actual globals (including all imports and functions)
        exec_globals = globals().copy()  # start with a copy to avoid accidental pollution
        exec_globals.update({
            "client_state": client_state,
            "profile": profile,
            "usecases": usecases,
            "__builtins__": __builtins__,  # ensure built-ins are available
        })

        # Local variables for the executed function
        local_vars = {}

        exec(f"async def __temp_func():\n    return {code}", exec_globals, local_vars)
        result = await local_vars["__temp_func"]()
        return f"Result: {pformat(result)}"
    except Exception as e:
        return f"Error executing code: {e}"

@register_command("latency")
async def latency_command(
    client_state: ClientState, profile: Profile, none: str
) -> str:
    """DEVELOPER-ONLY COMMAND. Use with extreme caution. Measures latency of various operations."""
    latency = await usecases.adapters.ossapi.latency()

    return f"API latency: {latency}"

@register_command("update")
async def update_command(
    client_state: ClientState, profile: Profile, none: str
) -> str:
    """Checks for updates to the server and provides instructions to update if an update is available."""
    async def perform_update():
        msg = await usecases.domain.server.update()

        await usecases.application.client.update.notify(msg)

    asyncio.create_task(perform_update())

    return "Update process started. You will receive a notification in the client when it is complete."

@register_command("refresh_cache")
async def refresh_cache_command(
    client_state: ClientState, profile: Profile, none: str
) -> str:
    """DEVELOPER-ONLY COMMAND. Use with extreme caution. Refreshes all caches."""
    usecases.domain.cache_control.clear_all_domain_caches()
    return "All caches have been cleared and will be refreshed on next access."

async def handle_command(
    client_state: ClientState, profile: Profile, message: str
) -> str | None:
    split_message = message.removeprefix("!").split(" ", maxsplit=1)

    if len(split_message) > 2 or len(split_message) == 0:
        return "Invalid command format. Use !command_name arguments"

    if len(split_message) == 1:
        command_name = split_message[0]
        arguments = ""
    else:
        command_name, arguments = split_message

    command_func = ALL_COMMANDS.get(command_name)
    if command_func is None:
        return f"Unknown command: {command_name}"

    return await command_func(client_state, profile, arguments)
