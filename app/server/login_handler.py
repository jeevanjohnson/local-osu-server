from typing import TypedDict, cast


class LoginData(TypedDict):
    username: str
    password_md5: str
    client_version: str
    utc_time_offset: int
    show_city: bool
    pm_private: bool
    osu_path_md5: str
    adapters_string: str
    adapters_md5: str
    uninstall_md5: str
    disk_signature_md5: str



def parse_login(data: bytes) -> LoginData:
    username, password_md5, remainder = data.decode().split(maxsplit=3)


    return cast(LoginData, login_data)
    ...
