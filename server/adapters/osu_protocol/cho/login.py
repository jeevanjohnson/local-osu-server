from dataclasses import dataclass
from jays_tools.architecture import AdapterModel


@dataclass
class LoginRequest(AdapterModel):
    username: str
    password_md5: bytes
    osu_version: str
    utc_offset: int
    display_city: bool
    pm_private: bool
    osu_path_md5: str
    adapters_str: str
    adapters_md5: str
    uninstall_md5: str
    disk_signature_md5: str

    @classmethod
    def deserialize(cls, buffer: bytes) -> "LoginRequest":
        (
            username,
            password_md5,
            remainder,
        ) = buffer.decode().split("\n", maxsplit=2)

        (
            osu_version,
            utc_offset,
            display_city,
            client_hashes,
            pm_private,
        ) = remainder.split("|", maxsplit=4)

        (
            osu_path_md5,
            adapters_str,
            adapters_md5,
            uninstall_md5,
            disk_signature_md5,
        ) = client_hashes[:-1].split(":", maxsplit=4)

        return cls(
            username=username,
            password_md5=password_md5.encode(),
            osu_version=osu_version,
            utc_offset=int(utc_offset),
            display_city=display_city == "1",
            pm_private=pm_private == "1",
            osu_path_md5=osu_path_md5,
            adapters_str=adapters_str,
            adapters_md5=adapters_md5,
            uninstall_md5=uninstall_md5,
            disk_signature_md5=disk_signature_md5,
        )
