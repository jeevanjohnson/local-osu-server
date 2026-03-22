from base64 import b64decode
from datetime import UTC, datetime

from fastapi.datastructures import FormData
from py3rijndael import Pkcs7Padding, RijndaelCbc
from pydantic import BaseModel, ConfigDict
from starlette.datastructures import UploadFile as StarletteUploadFile

from adapters.osu_file import OsuFile
from models.domain.gameplay import Mods, osuGameMode
from models.database.scores import (
    CurrentScore as Score
)
import calculator
from repositories.scores import ScoresRepository
from constants import SCORES_FILE
from adapters.app_logger import app_logger

def parse_form_data(form_data: FormData) -> tuple[bytes, StarletteUploadFile] | None:
    try:
        score_parts = form_data.getlist("score")
        assert len(score_parts) == 2, "Expected exactly 2 score parts"

        score_data_b64 = score_parts[0]
        assert isinstance(score_data_b64, str), "Expected score data to be a string"

        score_replay_file = score_parts[1]
        assert isinstance(score_replay_file, StarletteUploadFile), (
            "Expected score replay file to be an UploadFile"
        )

        return score_data_b64.encode(), score_replay_file
    except (AssertionError, IndexError):
        return None


class ScoreData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

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
    mods: Mods
    passed: bool
    game_mode: osuGameMode
    play_time: datetime
    # Ignore client flags & version since we don't have a use for them
    # Although not parsing could cause issues?

    # @field_serializer("mods")
    # def serialize_mods(self, value: Mods) -> list[str]:
    #     return list(value)

    # @field_validator("mods", mode="before")
    # @classmethod
    # def deserialize_mods(cls, value: list[str]) -> Mods:
    #     return Mods(value)


def decrypt_score_aes_data(
    # to decode
    score_data_b64: bytes,
    client_hash_b64: bytes,
    # used for decoding
    iv_b64: bytes,
    osu_version: str,
) -> tuple[ScoreData, str]:
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

    parsed_score_data = ScoreData(
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
        mods=Mods.from_score_submission(int(score_data[13])),
        passed=score_data[14] == "True",
        game_mode=osuGameMode(int(score_data[15])),
        # Score submission timestamp is UTC; keep it timezone-aware so epoch conversion is stable.
        play_time=datetime.strptime(score_data[16], "%y%m%d%H%M%S").replace(tzinfo=UTC),
    )

    # score data is delimited by colons (:).
    return parsed_score_data, client_hash_decoded

@app_logger.log(msg="building score")
async def build_score(
    score_id: int,
    map_file: OsuFile,
    score_data: ScoreData,
    beatmap_md5: str,
    replay_frames: bytes,
    beatmap_max_combo: int,
    calc_pp: bool = True,
) -> Score:
    if calc_pp:
        pp = calculator.pp(
            map_file=map_file,
            game_mode=score_data.game_mode,
            mods=score_data.mods,
            combo=score_data.max_combo,
            n300=score_data.count_300,
            n100=score_data.count_100,
            n50=score_data.count_50,
            nmiss=score_data.count_miss,
        )
    else:
        pp = None

    return Score.from_score_submission(
        score_id=score_id,
        score_data=score_data,
        beatmap_md5=beatmap_md5,
        replay_frames=replay_frames,
        beatmap_max_combo=beatmap_max_combo,
        pp=pp,
    )

@app_logger.log(msg="submitting score")
async def submit_score(
    score_id: int,
    map_file: OsuFile,
    score_data: ScoreData,
    beatmap_md5: str,
    replay_frames: bytes,
    beatmap_max_combo: int,
    calc_pp: bool = True,
) -> Score:
    score_repo = ScoresRepository(path=SCORES_FILE)

    score = await build_score(
        score_id=score_id,
        map_file=map_file,
        score_data=score_data,
        beatmap_md5=beatmap_md5,
        replay_frames=replay_frames,
        beatmap_max_combo=beatmap_max_combo,
        calc_pp=calc_pp,
    )

    await score_repo.save_score(score, profile_name=score_data.username)

    return score



