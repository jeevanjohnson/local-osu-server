import base64

from jays_tools import MigratableModel
from pydantic import ConfigDict, Field, field_serializer, field_validator

from usecases.adapters.osu_file import OsuFile


class OsuFileEntryV1(MigratableModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    md5: str
    file: OsuFile

    @field_serializer("file")
    def osu_file_to_json(self, value: OsuFile) -> str:
        assert value.raw_file is not None, "OsuFile must have raw_file to be serialized"

        # Persist only map data; audio payloads make cache writes extremely large.
        compressed_osu_file = value.compress(include_audio=False)

        return base64.b64encode(compressed_osu_file).decode("ascii")

    @field_validator("file", mode="before")
    @classmethod
    def json_to_osu_file(cls, value: object) -> OsuFile:
        if isinstance(value, OsuFile):
            return value

        assert isinstance(value, str), "Expected base64 string for osu file"

        compressed_osu_file = base64.b64decode(value.encode("ascii"))

        return OsuFile.decompress(compressed_osu_file)


OsuFileEntry = OsuFileEntryV1

MD5 = str


class OsuFileBackupV1(MigratableModel):
    all: dict[MD5, OsuFileEntry] = Field(default_factory=dict)


OsuFileBackup = OsuFileBackupV1
