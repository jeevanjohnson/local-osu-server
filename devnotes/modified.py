from typing import Optional, Union

from ext import glob
from objects.beatmap import Beatmap
from objects.modifiedbeatmap import ModifiedBeatmap
from objects.modifiedfinder import ModifiedFinder
from objects.mods import Mods
from objects.score import Score
from utils import log_error

from constants import ParsedParams

ONLINE_PLAYS = dict[str, list[dict]]
OSU_API_BASE = "https://osu.ppy.sh/api"

status_to_db = {1: "ranked", 2: "approved", 3: "qualified", 4: "loved"}

"""Map ranking types"""
NOTSUBMITTED = -1
PENDING = 0
UPDATEAVALIABLE = 1
RANKED = 2
APPROVED = 3
QUALIFIED = 4
LOVED = 5

"""Leaderboard types"""
LOCAL = 0
TOP = 1
MODS = 2
FRIENDS = 3
COUNTRY = 4

FROM_API_TO_SERVER_STATUS = {
    4: LOVED,
    3: QUALIFIED,
    2: APPROVED,
    1: RANKED,
    0: PENDING,
    -1: PENDING,  # wip
    -2: PENDING,  # graveyard
}

STARTING_LB_FORMAT = (
    "{rankedstatus}|false|{mapid}|{setid}|{num_of_scores}\n0\n"
    "[bold:0,size:20]{artist_unicode}|{title_unicode}\n10.0\n"
)
SCORE_FORMAT = (
    "{score_id}|{username}|{score}|"
    "{maxcombo}|{count50}|{count100}|"
    "{count300}|{countmiss}|{countkatu}|"
    "{countgeki}|{perfect}|{enabled_mods}|{user_id}|"
    "{num_on_lb}|{time}|{replay_available}"
)
VALID_LB_STATUESES = (LOVED, QUALIFIED, RANKED, APPROVED)

BMAPID_OR_MD5 = Union[int, str]
BEATMAP = Union[Beatmap, ModifiedBeatmap]


class ModifiedLeaderboard:
    def __init__(self) -> None:
        self.scores: list[Score] = []
        self.bmap: Optional[BEATMAP] = None
        self.personal_score: Optional[Score] = None

    @property
    def lb_base_fmt(self) -> Optional[bytes]:
        if not self.bmap:
            return

        return STARTING_LB_FORMAT.format(
            rankedstatus=FROM_API_TO_SERVER_STATUS[self.bmap.approved],
            mapid=self.bmap.beatmap_id,
            setid=self.bmap.beatmapset_id,
            num_of_scores=len(self.scores),
            artist_unicode=self.bmap.artist_unicode or self.bmap.artist,
            title_unicode=self.bmap.title_unicode or self.bmap.title,
        ).encode()

    @property
    def as_binary(self) -> bytes:
        if not self.bmap:
            return b"0|false"

        r = FROM_API_TO_SERVER_STATUS[self.bmap.approved]
        if r not in VALID_LB_STATUESES:
            return f"{r}|false".encode()

        if not self.lb_base_fmt:
            return f"{r}|false".encode()

        buffer = bytearray()
        buffer += self.lb_base_fmt

        if self.personal_score:
            if self.personal_score not in self.scores:
                num_on_lb = 1
            else:
                num_on_lb = self.scores.index(self.personal_score) + 1

            buffer += SCORE_FORMAT.format(
                **self.personal_score.as_leaderboard_score, num_on_lb=num_on_lb
            ).encode()
            buffer += b"\n"
        else:
            buffer += b"\n"

        len_scores = len(self.scores)
        enabled = None
        for idx, s in enumerate(self.scores):
            idx += 1

            if idx == 1:
                if glob.config.show_pp_for_personal_best:
                    enabled = True
                    glob.config.show_pp_for_personal_best = False
                else:
                    enabled = False

            s.name = f"({idx}) {s.name}"
            buffer += SCORE_FORMAT.format(
                **s.as_leaderboard_score, num_on_lb=idx
            ).encode()
            if idx != len_scores:
                buffer += b"\n"

        if enabled:
            glob.config.show_pp_for_personal_best = True

        return bytes(buffer)

    @classmethod
    async def from_client(cls, params: ParsedParams) -> "ModifiedLeaderboard":
        lb = cls()

        if params["md5"] not in glob.modified_beatmaps:
            finder = ModifiedFinder(
                params["md5"], params["filename"], params["set_id"], params["name_data"]
            )

            md5_or_id: Optional[BMAPID_OR_MD5] = None
            funorange_map = await finder.modified_txt_search()
            if funorange_map:
                md5_or_id = finder.get_bmap_id()

            if not funorange_map or not md5_or_id:
                md5_or_id = finder.get_original_md5()
                funorange_map = finder.funorange_map_path

            if not funorange_map or not md5_or_id:
                lb.scores = lb.scores[: glob.config.amount_of_scores_on_lb]
                return lb

            if isinstance(md5_or_id, int):
                bmap = await Beatmap.from_id(md5_or_id)
            else:
                bmap = await Beatmap.from_md5(md5_or_id)

            if not bmap:
                lb.scores = lb.scores[: glob.config.amount_of_scores_on_lb]
                return lb

            similarity = await finder.origin_edited_similarity(bmap)

            # TODO: find a better percentages
            # checks if they aren't similar or
            # they are the same map
            if similarity < 94.5 or similarity > 99.975:
                log_error(
                    (
                        f"when comparing, similarity was under 94.5% or above 99.975% ({similarity}%)\n"
                        "if you believe this was a mistake or an error, please report it to\n"
                        "cover on discord!"
                    )
                )
                lb.scores = lb.scores[: glob.config.amount_of_scores_on_lb]
                return lb

            if not finder.same_circles():
                log_error("circles in the maps are different!")
                lb.scores = lb.scores[: glob.config.amount_of_scores_on_lb]
                return lb

            lb.bmap = bmap = ModifiedBeatmap.add_to_db(
                bmap, params, funorange_map, return_modified=True
            )

            if not bmap:
                lb.scores = lb.scores[: glob.config.amount_of_scores_on_lb]
                return lb

        else:
            lb.bmap = bmap = await ModifiedBeatmap.from_md5(params["md5"])
            if not bmap:
                lb.scores = lb.scores[: glob.config.amount_of_scores_on_lb]
                return lb

        ranked_status = FROM_API_TO_SERVER_STATUS[bmap.approved]
        if ranked_status not in VALID_LB_STATUESES:
            lb.scores = lb.scores[: glob.config.amount_of_scores_on_lb]
            return lb

        if not glob.player or not glob.current_profile:
            lb.scores = lb.scores[: glob.config.amount_of_scores_on_lb]
            return lb

        key = f"{status_to_db[bmap.approved]}_plays"

        _player_scores: Optional[ONLINE_PLAYS] = glob.current_profile["plays"][key]

        if not _player_scores:
            lb.scores = lb.scores[: glob.config.amount_of_scores_on_lb]
            return lb

        if bmap.file_md5 not in _player_scores:
            lb.scores = lb.scores[: glob.config.amount_of_scores_on_lb]
            return lb

        player_scores = _player_scores[bmap.file_md5]

        if glob.mode:
            player_scores = [x for x in player_scores if x["mods"] & glob.mode]
        else:
            player_scores = [
                x
                for x in player_scores
                if not x["mods"] & (Mods.RELAX | Mods.AUTOPILOT)
            ]

        if not player_scores:
            lb.scores = lb.scores[: glob.config.amount_of_scores_on_lb]
            return lb

        if glob.config.pp_leaderboard or glob.mode:
            player_scores.sort(key=lambda s: s["pp"], reverse=True)
        else:
            player_scores.sort(key=lambda s: s["score"], reverse=True)

        if params["rank_type"] == MODS:
            player_scores = [x for x in player_scores if x["mods"] == params["mods"]]
            if not player_scores:
                lb.scores = lb.scores[: glob.config.amount_of_scores_on_lb]
                return lb

        lb.personal_score = Score.from_dict(player_scores[0])
        lb.scores = [Score.from_dict(x) for x in player_scores]
        lb.scores = lb.scores[: glob.config.amount_of_scores_on_lb]
        return lb

    import re


import hashlib
import os
import urllib.parse as urlparse
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional, Union

import utils
from objects.beatmap import Beatmap

# TODO: for right now the finder
# is pretty good for how it is
# however if I wanted it to be really good
# would probably need to check each individual circle
# in the map and see if they are out of place to determine
# if it is actually a speed up or only attribute edits
# although speed now becomes more of an issue
# so I may or may not write that check (probably wll)
# but if I want it good I should write this in like c++, c, cython
# or any other fast language so speed won't be a problem

MD5 = str
BMAPID = int
FUNORANGE_MAP = Path
MD5_OR_BMAPID = Union[MD5, BMAPID]


class ModifiedFinder:
    """Used to find data for funorange maps"""

    def __init__(
        self, md5: str, filename: str, set_id: int, name_data: Optional[re.Match] = None
    ) -> None:
        self.md5 = md5
        self.set_id = set_id
        self.filename = filename
        self.name_data = name_data

        self.raw_original_map: Optional[str] = None
        self.raw_funorange_map: Optional[str] = None
        self.original_bmap: Optional[Beatmap] = None
        self.original_map_path: Optional[Path] = None
        self.funorange_map_path: Optional[FUNORANGE_MAP] = None
        self.original_md5_or_bmapid: Optional[MD5_OR_BMAPID] = None

    def same_circles(
        self,
        raw_original_map: Optional[str] = None,
        raw_funorange_map: Optional[str] = None,
    ) -> bool:
        # checks if all the circles in
        # both maps are placed in the same way

        if not raw_original_map and self.raw_original_map:
            raw_original_map = self.raw_original_map
        elif not self.raw_original_map and raw_original_map:
            self.raw_original_map = raw_original_map
        elif self.original_map_path:
            self.raw_original_map = raw_original_map = self.original_map_path.read_text(
                errors="ignore"
            )

        if not raw_funorange_map and self.raw_funorange_map:
            raw_funorange_map = self.raw_funorange_map
        elif not self.raw_funorange_map and raw_funorange_map:
            self.raw_funorange_map = raw_funorange_map
        elif self.funorange_map_path:
            self.raw_funorange_map = raw_funorange_map = (
                self.funorange_map_path.read_text(errors="ignore")
            )

        if not raw_funorange_map or not raw_original_map:
            log_error("couldn't find either funorange or original map!")
            return False

        split_origin = raw_original_map.splitlines()
        split_funorange = raw_funorange_map.splitlines()

        origin_hitobjects = split_origin[split_origin.index("[HitObjects]") + 1 :]
        funorange_hitobjects = split_funorange[
            split_funorange.index("[HitObjects]") + 1 :
        ]

        if len(origin_hitobjects) != len(funorange_hitobjects):
            log_error("not the same amount of hitobjects!")
            return False

        for origin_obj, fun_obj in zip(origin_hitobjects, funorange_hitobjects):
            if origin_obj == fun_obj:
                continue

            fun_x, fun_y, *_ = fun_obj.split(",")
            origin_x, origin_y, *_ = origin_obj.split(",")

            if fun_x != origin_x or fun_y != origin_y:
                return False

        return True

    async def origin_edited_similarity(
        self, original_bmap: Optional[Beatmap] = None
    ) -> float:
        # returns a percentage of how similar the
        # funorange and original map is 0-100%
        origin = ""
        edited = ""

        if not self.funorange_map_path:
            return 0.0
        else:
            self.raw_funorange_map = edited = self.funorange_map_path.read_text(
                errors="ignore"
            )

        if self.original_map_path:
            self.raw_original_map = origin = self.original_map_path.read_text(
                errors="ignore"
            )
        elif original_bmap:
            self.raw_original_map = origin = await original_bmap.get_file()
        elif self.original_md5_or_bmapid:
            if isinstance(self.original_md5_or_bmapid, int):
                bmap_id = self.original_md5_or_bmapid
                origin_bmap = await Beatmap.from_id(bmap_id)
            else:
                md5 = self.original_md5_or_bmapid
                origin_bmap = await Beatmap.from_md5(md5)

            if not origin_bmap:
                return 0.0

            self.original_bmap = origin_bmap
            self.raw_original_map = origin = await origin_bmap.get_file()

        if not origin:
            return 0.0

        match = SequenceMatcher(None, origin, edited)
        ratio = match.real_quick_ratio() * 100

        tags = []
        split_edited = edited.lower().splitlines()
        start_index = split_edited.index("[metadata]") + 1
        end_index = split_edited.index("", start_index)
        for line in split_edited[start_index:end_index]:
            if not line.startswith("tags"):
                continue

            tags = line.lstrip().removeprefix("tags:").split()

        if "osutrainer" in tags:
            # TODO: why is this here
            if ratio > 99.75:
                while ratio > 99.75:
                    ratio -= 0.01
            elif ratio < 94.5:
                while ratio < 94.5:
                    ratio += 0.01

        return ratio

    def get_original_md5(self) -> Optional[MD5]:
        md5 = None

        path_exists = self.funorange_map_path and self.funorange_map_path.exists()

        if not path_exists and glob.songs_folder:
            if self.set_id > 0:
                pattern = f"{self.set_id}*"
                folders = glob.songs_folder.glob(pattern)
            elif self.name_data:
                pattern = (
                    f"* {self.name_data['artist']} - {self.name_data['song_name']}*"
                )
                folders = glob.songs_folder.glob(pattern)
            else:
                folders = []
        elif self.funorange_map_path:
            folders = (self.funorange_map_path.parent,)
        else:
            folders = []

        lower_filename = urlparse.unquote_plus(self.filename.lower())

        for map_set_folder in folders:
            for map_file in os.listdir(str(map_set_folder)):
                if self.original_md5_or_bmapid and self.funorange_map_path:
                    break

                if not map_file.endswith(".osu"):
                    continue

                map_file_unquote = urlparse.unquote_plus(map_file)
                lower_map_file_unquote = map_file_unquote.lower()

                if lower_filename == lower_map_file_unquote:
                    self.funorange_map_path = map_set_folder / map_file
                    continue

                if (
                    lower_map_file_unquote[:-5] in lower_filename
                    and lower_filename != lower_map_file_unquote
                ):
                    self.original_map_path = orignal_bmap_file = (
                        map_set_folder / map_file
                    )
                    self.original_md5_or_bmapid = md5 = hashlib.md5(
                        orignal_bmap_file.read_bytes()
                    ).hexdigest()

            if self.original_md5_or_bmapid and self.funorange_map_path:
                break

        path_exists = self.funorange_map_path and self.funorange_map_path.exists()

        if not self.original_md5_or_bmapid or not path_exists:
            return md5

        return md5

    def get_bmap_id(self) -> Optional[BMAPID]:
        if not self.funorange_map_path or not self.funorange_map_path.exists():
            return

        file_content = (
            self.funorange_map_path.read_text(errors="ignore").lower().splitlines()
        )

        for line in file_content:
            try:
                k, v = line.strip().split(": ", 1)
                if k != "beatmapid":
                    continue

                bmap_id = int(v)
                if bmap_id > 0:
                    self.original_md5_or_bmapid = bmap_id
                    return bmap_id  # type: ignore
            except:
                continue

    async def modified_txt_search(self) -> Optional[FUNORANGE_MAP]:
        if not glob.modified_txt.exists():
            return

        modified_maps = tuple(glob.modified_txt.read_text().splitlines())

        for modified_map_str in modified_maps:
            split = modified_map_str.split(".mp3 | ", 1)
            if len(split) < 2:
                continue

            audio, file_path = split

            file_path = Path(file_path)

            if glob.using_wsl:
                funorange_filename_from_txt = file_path.name.split("\\")[-1]
            else:
                funorange_filename_from_txt = file_path.parts[-1]

            funorange_filename_from_txt_unquote = urlparse.unquote_plus(
                funorange_filename_from_txt
            )

            if self.filename == funorange_filename_from_txt_unquote:
                self.funorange_map_path = file_path

                if glob.using_wsl:
                    self.funorange_map_path = await utils.async_str_to_wslpath(
                        path=str(file_path)
                    )

                break

        return self.funorange_map_path

    import os


import asyncio
import re
from typing import Union

import aiohttp
import orjson
import packets
import pyperclip
import regex
from objects import (
    DirectResponse,
    Leaderboard,
    LeaderboardTypes,
    ModifiedLeaderboard,
    Mods,
    NotSupported,
)
from utils import Color, log, log_success

from constants import InvalidMods, ParsedParams
from server import Alias, Query, Response, Router

web = Router(
    (
        "/osu/web",
        "/osu",  # type: ignore
    )
)


async def DEFAULT_RESPONSE_FUNC() -> Response:
    return Response()


# unusable or unused handlers
for hand in [
    "/lastfm.php",
    "/osu-rate.php",
    "/osu-error.php",
    "/osu-session.php",
    "/difficulty-rating",
    "/osu-markasread.php",
    "/osu-getfriends.php",
    "/osu-getbeatmapinfo.php",
]:
    web.get(hand)(DEFAULT_RESPONSE_FUNC)

OSU_API_BASE = "https://osu.ppy.sh/api"


@web.get(re.compile(r"\/ss\/(?P<link>.*)"))
async def get_ss(link: str) -> Response:
    return Response(code=301, headers={"Location": link})


@web.get(re.compile(r"(?P<full_path>\/(beatmaps|beatmapsets)\/.*)"))
async def bmap_web(full_path: str) -> Response:
    return Response(code=301, headers={"Location": f"https://osu.ppy.sh/{full_path}"})


@web.get(re.compile(r"/d/(?P<setid>[-0-9]*)"))
async def get_osz(setid: int) -> Response:
    if setid == -1 and glob.current_cmd:
        cmd = glob.current_cmd
        await cmd.func(*cmd.args)
        cmd.args = []
        glob.current_cmd = None
        return Response()

    if setid == -1:
        return Response()

    return Response(code=301, headers={"Location": f"https://osu.gatari.pw/d/{setid}"})


@web.get("/osu-screenshot.php")
async def osu_screenshots() -> Response:
    if not glob.screenshot_folder:
        return Response(b"error: no")

    latest_screenshot = glob.screenshot_folder / max(
        glob.screenshot_folder.glob("*"), key=os.path.getctime
    )

    if not glob.imgur:
        return Response(str(latest_screenshot))

    uploaded_image = glob.imgur.upload_image(
        path=str(latest_screenshot), title="from local server"
    )

    pyperclip.copy(uploaded_image.link)
    return Response(uploaded_image.link.encode())


REMINDER = None
DEFAULT_CHARTS = "\n".join(
    [
        "beatmapId:0|beatmapSetId:0|beatmapPlaycount:0|beatmapPasscount:0|approvedDate:0",
        "chartId:beatmap|chartUrl:https://osu.ppy.sh/b/0|chartName:Beatmap Ranking|rankBefore:|rankAfter:0|maxComboBefore:|maxComboAfter:0|accuracyBefore:|accuracyAfter:0|rankedScoreBefore:|rankedScoreAfter:0|ppBefore:|ppAfter:0|onlineScoreId:0",
        "chartId:overall|chartUrl:https://osu.ppy.sh/u/2|chartName:Overall Ranking|rankBefore:0|rankAfter:0|rankedScoreBefore:0|rankedScoreAfter:0|totalScoreBefore:0|totalScoreAfter:0|maxComboBefore:0|maxComboAfter:0|accuracyBefore:0|accuracyAfter:0|ppBefore:0|ppAfter:0|achievements-new:|onlineScoreId:0",
    ]
).encode()


@web.get("/osu-submit-modular-selector.php")
async def score_sub() -> Response:
    global REMINDER
    if not glob.player:
        return Response(code=404)

    if REMINDER is None:
        glob.player.queue += packets.notification(
            ("To submit a play be sure to save the replay of the play!")
        )
        REMINDER = 0
    elif REMINDER == 50:
        glob.player.queue += packets.notification(
            (
                "Just a reminder\n"
                "To submit a play be sure to save the replay of the play!"
            )
        )
        REMINDER = 0

    REMINDER += 1

    if "playcount" in glob.current_profile:
        glob.current_profile["playcount"] += 1
    else:
        glob.current_profile["playcount"] = 1

    utils.update_files()

    glob.player.queue += packets.userStats(glob.player)

    log_success(f"{glob.player.name}'s playcount increased!")
    return Response(DEFAULT_CHARTS)


@web.get("/osu-getseasonal.php")
async def get_bgs() -> Response:
    if not glob.config.seasonal_bgs:
        bgs = b'[""]'
    else:
        bgs = orjson.dumps(glob.config.seasonal_bgs)

    return Response(bgs)


@web.get("/osu-getreplay.php")
async def get_replay(scoreid: int = Alias("c"), mode: int = Alias("m")) -> Response:
    if scoreid > 0:
        params = {"k": glob.config.osu_api_key, "s": scoreid, "m": mode}
        async with glob.http.get(
            url=f"{OSU_API_BASE}/get_replay", params=params
        ) as resp:
            if not resp or resp.status != 200:
                return Response(b"error: no")

            json = await resp.json()

        replay_frames = utils.string_to_bytes(json["content"])
        log("bancho replay handled", color=Color.LIGHTGREEN_EX)
        return Response(replay_frames)

    elif glob.player and glob.current_profile:
        real_id = abs(scoreid) - 1
        play = glob.current_profile["plays"]["all_plays"][real_id].copy()

        if "replay_frames" not in play or play["replay_frames"] is None:
            log_error(f"no replay frames were found for scoreid: {real_id}")
            return Response(b"error: no")
        else:
            log(f"{glob.player.name}'s replay was handled", color=Color.LIGHTGREEN_EX)

            if "b'" == play["replay_frames"][:2]:
                replay: bytes = eval(play["replay_frames"])
            else:
                replay = utils.string_to_bytes(play["replay_frames"])

            return Response(replay)
    else:
        log_error("error handling replay")
        return Response(b"error: no")


NOT_SUPPORTED = bytes(NotSupported())


@web.get("/osu-osz2-getscores.php")
async def leaderboard(
    mods: Mods,
    mode: int = Alias("m"),
    rank_type: LeaderboardTypes = Alias("v"),
    filename: str = Query(urlparse.unquote_plus, Alias("f")),
    setid: int = Alias("i"),
    md5: str = Alias("c"),
) -> Response:
    if not glob.player:
        return Response(code=404)

    valid_rank_types = (
        LeaderboardTypes.LOCAL,
        LeaderboardTypes.TOP,
        LeaderboardTypes.MODS,
    )

    supported = mode == 0 and rank_type in valid_rank_types

    if not supported:
        return Response(NOT_SUPPORTED)

    parsed_params = ParsedParams(
        filename=filename,
        mods=mods,
        mode=mode,
        rank_type=rank_type,
        set_id=setid,
        md5=md5,
        name_data=None,
    )

    if mods & Mods.RELAX and glob.mode != Mods.RELAX:
        glob.mode = Mods.RELAX
        glob.invalid_mods = InvalidMods.Relax
        glob.player.queue += packets.notification("Mode was switched to rx!")
        asyncio.create_task(glob.player.update(glob.mode))
    elif mods & Mods.AUTOPILOT and glob.mode != Mods.AUTOPILOT:
        glob.mode = Mods.AUTOPILOT
        glob.invalid_mods = InvalidMods.AutoPilot
        glob.player.queue += packets.notification("Mode was switched to ap!")
        asyncio.create_task(glob.player.update(glob.mode))
    elif not mods & (Mods.RELAX | Mods.AUTOPILOT) and glob.mode is not None:
        glob.mode = None
        glob.invalid_mods = InvalidMods.Standard
        glob.player.queue += packets.notification("Mode was switched to vanilla!")
        asyncio.create_task(glob.player.update(glob.mode))

    if glob.config.osu_api_key:
        lb = await Leaderboard.from_bancho(parsed_params)
    else:
        lb = await Leaderboard.from_offline(parsed_params)

    valid_bmap = lb.bmap and lb.bmap.approved in (1, 2, 3, 4)
    if not valid_bmap and not glob.config.disable_funorange_maps:
        regex_results = [r.search(filename) for r in regex.modified_regexes]

        name_data = regex.filename_parser.search(filename)
        if name_data and (diff_name := name_data["diff_name"]):
            regex_results.extend([r.search(diff_name) for r in regex.attribute_edits])

            parsed_params["name_data"] = name_data

        if any(regex_results):
            lb = await ModifiedLeaderboard.from_client(parsed_params)
            log_success(f"handled funorange map of {filename}")
        else:
            log_success(f"handled bancho(?) map of {filename}")
    else:
        log_success(f"handled map of setid: {setid}")

    return Response(lb.as_binary)


DIRECT_TO_API_STATUS = {
    0: "ranked",
    2: "unranked",
    3: "qualified",
    4: "all",
    5: "unranked",
    7: "ranked",
    8: "loved",
}

DIRECT_TO_MIRROR_MODE = {-1: "", 0: "std", 1: "taiko", 2: "ctb", 3: "mania"}

COMMAND_NOT_FOUND = DirectResponse.from_str("command not found!").as_binary

convert_param_mode_to_api = lambda x: DIRECT_TO_MIRROR_MODE[x]
convert_param_rankstatus_to_api = lambda x: DIRECT_TO_API_STATUS[x]


@web.get("/osu-search.php")
async def direct(
    query: str = Query(urlparse.unquote_plus, Alias("q")),
    mode: int = Alias("m"),
    ranking_status: int = Alias("r"),
) -> Response:
    if query.startswith(glob.config.command_prefix):
        query_no_prefix = query.removeprefix(glob.config.command_prefix)
        split = query_no_prefix.split()

        if not split or split[0] not in glob.commands:
            return Response(COMMAND_NOT_FOUND)

        cmd, *args = split

        command = glob.commands[cmd]

        if command.confirm_with_user:
            command.args = args
            glob.current_cmd = command

            msg = (
                "click me to execute!\n"
                f"loaded command: {command.name}\n"
                f"following args: {args}"
            )

            execute_button = DirectResponse.from_str(msg, start_id=-1).as_binary

            return Response(execute_button)
        else:
            resp = await command.func(*args)

            return Response(bytes(resp) if resp else b"0")

    if not glob.config.osu_username or not glob.config.osu_password:
        utils.add_to_player_queue(
            packets.notification("No username/password provided for direct!")
        )
        return Response(b"0")

    args: dict[str, Union[int, str]] = {
        "u": glob.config.osu_username,
        "h": glob.config.osu_password,
    }

    if query not in ("Newest", "Top Rated", "Most Played"):
        args["q"] = query

    if mode != -1:
        args["m"] = mode

    args["r"] = ranking_status

    try:
        async with glob.http.get(
            url="https://osu.ppy.sh/web/osu-search.php", params=args
        ) as resp:
            ret = await resp.read()
    except aiohttp.ClientConnectorError:
        log_error("mirror currently down")
        return Response(b"0")

    log_success(f"maps loaded for query: `{query}` !")
    return Response(ret)
