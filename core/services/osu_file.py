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
        for line in raw_osu_file.decode("utf-8-sig").splitlines():
            line = line.strip()

            if line.startswith("BeatmapID"):
                return int(line.split(":")[1].strip())

            if line.startswith("[Difficulty]"):
                break

        return None

    def get_hp(self, raw_osu_file: bytes) -> float | None:
        for line in raw_osu_file.decode("utf-8-sig").splitlines():
            line = line.strip()

            if line.startswith("HPDrainRate"):
                return float(line.split(":")[1].strip())

            if line.startswith("[Events]"):
                break

        return None

    def get_cs(self, raw_osu_file: bytes) -> float | None:
        for line in raw_osu_file.decode("utf-8-sig").splitlines():
            line = line.strip()

            if line.startswith("CircleSize"):
                return float(line.split(":")[1].strip())

            if line.startswith("[Events]"):
                break

        return None

    def get_od(self, raw_osu_file: bytes) -> float | None:
        for line in raw_osu_file.decode("utf-8-sig").splitlines():
            line = line.strip()

            if line.startswith("OverallDifficulty"):
                return float(line.split(":")[1].strip())

            if line.startswith("[Events]"):
                break

        return None

    def get_ar(self, raw_osu_file: bytes) -> float | None:
        for line in raw_osu_file.decode("utf-8-sig").splitlines():
            line = line.strip()

            if line.startswith("ApproachRate"):
                return float(line.split(":")[1].strip())

            if line.startswith("[Events]"):
                break

        return None
