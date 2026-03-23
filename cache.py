from datetime import datetime, timedelta
from typing import Generic, TypeVar

KEY = TypeVar("KEY")
VALUE = TypeVar("VALUE")


class Cache(Generic[KEY, VALUE]):
    def __init__(self, time_to_live: timedelta):
        self.time_to_live = time_to_live
        self.store: dict[KEY, tuple[VALUE, datetime]] = {}

    def get(self, key: KEY) -> VALUE | None:
        if key not in self.store:
            return None

        value, time_set = self.store[key]
        current_time = datetime.now()
        if current_time - time_set > self.time_to_live:
            del self.store[key]
            return None

        return value

    def set(self, key: KEY, value: VALUE) -> None:
        self.store[key] = (value, datetime.now())

    def clear(self) -> None:
        self.store.clear()

    def remove(self, key: KEY) -> None:
        if key in self.store:
            del self.store[key]


from pathlib import Path

from models.bancho.scores import Score, Scores
from models.database.beatmaps import CurrentBeatmap as Beatmap

MD5 = str
SET_ID = int
FILE_NAME = str
beatmap = Cache[MD5, Beatmap](time_to_live=timedelta(minutes=30))
osu_file_path_by_md5 = Cache[MD5, Path](time_to_live=timedelta(minutes=30))
osu_files_by_set_id_and_filename = Cache[tuple[SET_ID, FILE_NAME], Path](
    time_to_live=timedelta(minutes=30)
)
osu_file_path_by_beatmap_id_and_set_id = Cache[tuple[int, int], Path](
    time_to_live=timedelta(minutes=30)
)
beatmap_by_md5 = Cache[MD5, Beatmap](time_to_live=timedelta(minutes=30))
osu_file_path_by_file_name = Cache[FILE_NAME, Path](time_to_live=timedelta(minutes=30))
beatmap_by_id = Cache[int, Beatmap](time_to_live=timedelta(minutes=30))
osu_file_path_by_set_id_and_md5 = Cache[tuple[SET_ID, MD5], Path](
    time_to_live=timedelta(minutes=30)
)
score_for_user_on_beatmap_by_md5 = Cache[MD5, Score](time_to_live=timedelta(minutes=5))
friends_scores_for_beatmap_by_md5 = Cache[MD5, Scores](
    time_to_live=timedelta(minutes=5)
)
any_scores_by_beatmap_md5 = Cache[MD5, Scores](time_to_live=timedelta(minutes=5))
