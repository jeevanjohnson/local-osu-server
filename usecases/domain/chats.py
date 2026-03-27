import re
from enum import Enum

import usecases.domain.calculator.performance
from constants.network import OSU_CLIENT_REQUEST_URL
from models.domain.gameplay import Mods
from osu_protocol.cho.server import osuGameMode
from repositories.osufiles.songs_folder import OsuFileRepository

BEATMAP_SET_BASE_URL = f"https://osu.{OSU_CLIENT_REQUEST_URL}/beatmapsets/"
NP_REGEX = re.compile(r"/beatmapsets/\d+#/(\d+)")
URL_LINK = f"https://osu.{OSU_CLIENT_REQUEST_URL}/beatmapsets/" + "{set_id}#/{id}"


class OsuScheme(Enum):
    # osu! set scheme
    SET_ID = "s"
    MAP_ID = "b"


def chat_button(text: str, url: str) -> str:
    return f"[{url} {text}]"


def osu_scheme_button(overlay: str, scheme: OsuScheme, id: int) -> str:
    return chat_button(overlay, f"osu://{scheme.value}/{id}")


# @cached_forever
def is_np(text: str) -> bool:
    if BEATMAP_SET_BASE_URL not in text:
        return False

    return NP_REGEX.search(text) is not None


# @cached_forever
def get_beatmap_id_from_np(text: str) -> int | None:
    np_match = NP_REGEX.search(text)

    if np_match is None:
        return None

    return int(np_match.group(1))


# @cached_for_10_minutes
async def pp_for(
    beatmap_md5: str,
    game_mode: osuGameMode,
    mods: Mods = Mods([]),
    accuracy: float | None = None,
    misses: int | None = None,
    combo: int | None = None,
) -> str:
    osu_file_repo = OsuFileRepository()

    osu_file = await osu_file_repo.from_md5(beatmap_md5)
    if osu_file is None:
        return "Couldn't find beatmap file :("

    message = []

    button = chat_button(
        text=osu_file.file_name.removesuffix(".osu"),
        url=URL_LINK.format(set_id=osu_file.beatmap_set_id, id=osu_file.beatmap_id),
    )

    message.append("pp for " + button + f" +{mods}")

    for acc in [100, 99, 98, 97, 95]:
        kwargs = {
            "map_file": osu_file,
            "game_mode": game_mode,
            "mods": mods,
            "accuracy": acc,
        }

        if misses is not None:
            kwargs["misses"] = misses

        if combo is not None:
            kwargs["combo"] = combo

        if accuracy is not None:
            kwargs["accuracy"] = accuracy

        pp = usecases.domain.calculator.performance.pp_for_acc(**kwargs)

        message.append(f"{acc}%: {pp:.2f}pp")

    return "\n".join(message)
