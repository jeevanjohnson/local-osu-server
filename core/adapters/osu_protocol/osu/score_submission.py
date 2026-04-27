from base64 import b64decode
from datetime import UTC, datetime
from core.adapters.osu_protocol.domain.enums import (
    osuMods,
    osuGameMode
)

from fastapi.datastructures import FormData
from py3rijndael import Pkcs7Padding, RijndaelCbc
from dataclasses import dataclass
from starlette.datastructures import UploadFile as StarletteUploadFile
from typing import TypedDict

class ParseFormDataResult(TypedDict):
    score_data_b64: bytes
    score_replay_file: StarletteUploadFile

def parse_form_data(form_data: FormData) -> ParseFormDataResult | None:
    try:
        score_parts = form_data.getlist("score")
        assert len(score_parts) == 2, "Expected exactly 2 score parts"

        score_data_b64 = score_parts[0]
        assert isinstance(score_data_b64, str), "Expected score data to be a string"

        score_replay_file = score_parts[1]
        assert isinstance(score_replay_file, StarletteUploadFile), (
            "Expected score replay file to be an UploadFile"
        )

        return {
            "score_data_b64": score_data_b64.encode(), 
            "score_replay_file": score_replay_file
        }
    except (AssertionError, IndexError):
        return None


@dataclass
class RawScoreData:
    beatmap_md5: str
    username: str
    online_checksum: str
    count_300: int
    count_100: int
    count_50: int
    count_geki: int
    count_katu: int
    count_miss: int
    total_score: int
    max_combo: int
    perfect: bool
    grade: str
    mods: osuMods
    passed: bool
    game_mode: osuGameMode
    play_time: datetime
    # Ignore client flags & version since we don't have a use for them
    # Although not parsing could cause issues?

class DecryptScoreAESDataResult(TypedDict):
    score_data: RawScoreData
    client_hash_decoded: str

def decrypt_score_aes_data(
    # to decode
    score_data_b64: bytes,
    client_hash_b64: bytes,
    # used for decoding
    iv_b64: bytes,
    osu_version: str,
) -> DecryptScoreAESDataResult:
    """Decrypt the base64'ed score data."""

    # attempt to decrypt score data
    aes = RijndaelCbc(
        key=f"osu!-scoreburgr---------{osu_version}".encode(),
        iv=b64decode(iv_b64),
        padding=Pkcs7Padding(32),
        block_size=32,
    )

    score_data = aes.decrypt(b64decode(score_data_b64)).decode().split(":")
    client_hash_decoded = aes.decrypt(b64decode(client_hash_b64)).decode()

    parsed_score_data = RawScoreData(
        beatmap_md5=score_data[0],
        username=score_data[1].strip(),
        online_checksum=score_data[2],
        count_300=int(score_data[3]),
        count_100=int(score_data[4]),
        count_50=int(score_data[5]),
        count_geki=int(score_data[6]),
        count_katu=int(score_data[7]),
        count_miss=int(score_data[8]),
        total_score=int(score_data[9]),
        max_combo=int(score_data[10]),
        perfect=score_data[11] == "True",
        grade=score_data[12].upper(),
        mods=osuMods(int(score_data[13])),
        passed=score_data[14] == "True",
        game_mode=osuGameMode(int(score_data[15])),
        # Score submission timestamp is UTC; keep it timezone-aware so epoch conversion is stable.
        play_time=datetime.strptime(score_data[16], "%y%m%d%H%M%S").replace(tzinfo=UTC),
    )

    # score data is delimited by colons (:).
    return {
        "score_data": parsed_score_data,
        "client_hash_decoded": client_hash_decoded
    }

@dataclass
class ScoreData(RawScoreData):
    replay_frames: bytes

def decrypt_score_submission_attempt(
    raw_score_parameters: FormData,
    client_hash_b64: bytes,
    iv_b64: bytes,
    osu_version: str,
) -> ScoreData:
    score_parameters = parse_form_data(raw_score_parameters)
    
    if score_parameters is None:
        raise ValueError("Invalid form data: missing or malformed 'score' fields")

    decrypt_score_result = decrypt_score_aes_data(
        score_data_b64=score_parameters["score_data_b64"],
        client_hash_b64=client_hash_b64,
        iv_b64=iv_b64,
        osu_version=osu_version,
    )

    score_data = decrypt_score_result["score_data"]
    replay = score_parameters["score_replay_file"]

    return ScoreData(
        beatmap_md5=score_data.beatmap_md5,
        username=score_data.username,
        online_checksum=score_data.online_checksum,
        count_300=score_data.count_300,
        count_100=score_data.count_100,
        count_50=score_data.count_50,
        count_geki=score_data.count_geki,
        count_katu=score_data.count_katu,
        count_miss=score_data.count_miss,
        total_score=score_data.total_score,
        max_combo=score_data.max_combo,
        perfect=score_data.perfect,
        grade=score_data.grade,
        mods=score_data.mods,
        passed=score_data.passed,
        game_mode=score_data.game_mode,
        play_time=score_data.play_time,
        replay_frames=replay.file.read(),
    )

@dataclass
class Achievement:
    image_url: str
    title: str
    description: str

    def serialize(self) -> str:
        return f"{self.image_url}+{self.title}+{self.description}"

class Achievements(list[Achievement]):
    def serialize(self) -> str:
        return "/".join(achievement.serialize() for achievement in self)

@dataclass
class ChartColumn:
    name: str
    before: float | None = None
    after: float | None = None

    def serialize(self) -> str:
        return (
            f"{self.name}Before:{self.before or ''}|{self.name}After:{self.after or ''}"
        )

@dataclass
class Rank(ChartColumn):
    name: str = "rank"


@dataclass
class RankedScore(ChartColumn):
    name: str = "rankedScore"


@dataclass
class TotalScore(ChartColumn):
    name: str = "totalScore"


@dataclass
class MaxCombo(ChartColumn):
    name: str = "maxCombo"


@dataclass
class Accuracy(ChartColumn):
    name: str = "accuracy"


@dataclass
class PerformancePoints(ChartColumn):
    name: str = "pp"


@dataclass
class Chart:
    rank: Rank
    ranked_score: RankedScore
    total_score: TotalScore
    max_combo: MaxCombo
    accuracy: Accuracy
    pp: PerformancePoints

    def serialize(self) -> list[str]:
        return [
            self.rank.serialize(),
            self.ranked_score.serialize(),
            self.total_score.serialize(),
            self.max_combo.serialize(),
            self.accuracy.serialize(),
            self.pp.serialize(),
        ]


class BeatmapChart(Chart):
    pass


class OverallRankingChart(Chart):
    pass


@dataclass
class SubmissionCharts:
    beatmap_id: int
    beatmap_set_id: int
    beatmap_playcount: int
    beatmap_passcount: int
    last_updated: datetime
    score_id: int
    beatmap_chart: BeatmapChart
    overall_ranking_chart: OverallRankingChart
    achievements: Achievements

    @property
    def beatmap_url(self) -> str:
        return f"https://osu.ppy.sh/b/{self.beatmap_id}"

    @property
    def chart_url(self) -> str:
        # TODO: Redirect to GUI?
        return "https://osu.ppy.sh/u/2"

    def serialize(self) -> bytes:
        submission_charts = [
            f"beatmapId:{self.beatmap_id}",
            f"beatmapSetId:{self.beatmap_set_id}",
            f"beatmapPlaycount:{self.beatmap_playcount}",
            f"beatmapPasscount:{self.beatmap_passcount}",
            f"approvedDate:{self.last_updated}",
            "\n",
            # beatmap ranking chart
            "chartId:beatmap",
            f"chartUrl:{self.beatmap_url}",
            "chartName:Beatmap Ranking",
            *self.beatmap_chart.serialize(),
            f"onlineScoreId:{self.score_id}",
            "\n",
            # overall ranking chart
            "chartId:overall",
            f"chartUrl:{self.chart_url}",
            "chartName:Overall Ranking",
            *self.overall_ranking_chart.serialize(),
            f"achievements-new:{self.achievements.serialize()}",
        ]

        return "|".join(submission_charts).encode()

def empty_charts(
    previous_personal_best_total_score: int | None = None,
    new_personal_best_total_score: int | None = None,
    previous_total_score: int | None = None,
    new_total_score: int | None = None,
) -> SubmissionCharts:
    return SubmissionCharts(
        beatmap_id=0,
        beatmap_set_id=0,
        beatmap_playcount=0,
        beatmap_passcount=0,
        last_updated=datetime.now(),
    score_id=0,
    beatmap_chart=BeatmapChart(
        rank=Rank(name="rank"),
        ranked_score=RankedScore(name="rankedScore"),
        total_score=TotalScore(
            name="totalScore", 
            before=previous_personal_best_total_score, 
            after=new_personal_best_total_score
        ),
        max_combo=MaxCombo(name="maxCombo"),
        accuracy=Accuracy(name="accuracy"),
        pp=PerformancePoints(name="pp"),
    ),
    overall_ranking_chart=OverallRankingChart(
        rank=Rank(name="rank"),
        ranked_score=RankedScore(name="rankedScore"),
        total_score=TotalScore(
            name="totalScore", 
            before=previous_total_score, 
            after=new_total_score
        ),
        max_combo=MaxCombo(name="maxCombo"),
        accuracy=Accuracy(name="accuracy"),
        pp=PerformancePoints(name="pp"),
    ),
    achievements=Achievements(),
)