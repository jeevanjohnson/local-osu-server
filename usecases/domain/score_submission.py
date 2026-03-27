from starlette.datastructures import FormData, UploadFile

from osuProtocol.client_web import ScoreData, decrypt_score_aes_data, parse_form_data


async def decrypt(
    raw_score_parameters: FormData,
    client_hash_b64: bytes,
    iv_b64: bytes,
    osu_version: str,
) -> tuple[ScoreData, str, UploadFile]:
    """
    Parse and decrypt score submission data.
    Raises ScoreSubmissionError if parsing/decryption fails.
    """
    score_parameters = parse_form_data(raw_score_parameters)

    if score_parameters is None:
        raise Exception("Invalid score form data")

    score_data_b64, replay_file = score_parameters

    score_data, client_hash_decoded = decrypt_score_aes_data(
        score_data_b64=score_data_b64,
        client_hash_b64=client_hash_b64,
        iv_b64=iv_b64,
        osu_version=osu_version,
    )

    return score_data, client_hash_decoded, replay_file


import calculator.performance
from adapters import OsuFile
from models.database.scores import CurrentScore as Score
from osuProtocol.client_web import ScoreData
from repositories.scores import ScoresRepository


async def submit(
    score_id: int,
    map_file: OsuFile,
    score_data: ScoreData,
    beatmap_md5: str,
    replay_frames: bytes,
    beatmap_max_combo: int,
    calc_pp: bool = True,
):
    scores_repo = ScoresRepository()

    if calc_pp:
        pp = calculator.performance.pp(
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

    score = Score.from_score_submission(
        score_id=score_id,
        score_data=score_data,
        beatmap_md5=beatmap_md5,
        replay_frames=replay_frames,
        beatmap_max_combo=beatmap_max_combo,
        pp=pp,
    )

    await scores_repo.save_score(score, profile_name=score_data.username)

    return score
