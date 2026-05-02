import hashlib
from jays_tools.architecture import Service


class OsuFileService(Service):

    def get_md5(self, raw_osu_file: bytes) -> str:
        return hashlib.md5(raw_osu_file).hexdigest()

    def get_beatmap_set_id(self, beatmap_folder_name: str) -> int | None:
        try:
            beatmap_set_id, _ = beatmap_folder_name.split(" ", maxsplit=1)
            return int(beatmap_set_id)
        except ValueError:
            return None

    def get_beatmap_id(self, raw_osu_file: bytes) -> int | None:
        for line in raw_osu_file.decode("utf-8-sig").splitlines()[:50]:
            line = line.strip()

            if line.startswith("BeatmapID"):
                return int(line.split(":")[1].strip())

        return None
